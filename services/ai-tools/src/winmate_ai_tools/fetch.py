"""웹 수집 — POST /v1/fetch (모델 호출이 아니라 MODEL_MODE 와 무관).

- WEB_FETCH_ENABLED=false → allowed=false, reason "disabled"
- http(s) 만, localhost · 링크로컬 주소는 막음(blocked_host). WEB_FETCH_ALLOWED_DOMAINS(쉼표, 비우면 전부) 밖 → domain_not_allowed
- robots.txt 존중(WEB_FETCH_RESPECT_ROBOTS, RFC 9309: 4xx → 모두 허용, 5xx · 연결 실패 → 모두 금지) → robots_disallow · robots_unreachable
- 호스트별 속도 제한 WEB_FETCH_RATE_LIMIT_RPS(0.5 → 같은 호스트 2초 간격), 제한 시간 WEB_FETCH_TIMEOUT_S
- 본문 추출: trafilatura(표 포함) → 실패하면 BeautifulSoup 텍스트. PDF 는 pypdfium2 가 있으면 페이지별 텍스트(pages)
- 디스크 캐시 CACHE_DIR/fetch/<sha256(url)>.json, 유효 시간 WEB_FETCH_CACHE_TTL_HOURS
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from winmate_common.ids import now_iso

from . import config
from .errors import ProviderError, provider_error
from .imaging import blocked_host
from .runtime import track
from .schemas import FetchRequest

log = logging.getLogger("winmate.ai_tools.fetch")

CACHE_TEXT_MAX = 500_000
ROBOTS_TTL_S = 24 * 3600
_robots: dict[str, tuple[float, str, RobotFileParser | None]] = {}
_next_ok: dict[str, float] = {}
_locks: dict[tuple[int, str], asyncio.Lock] = {}


def domain_allowed(host: str, allowed: tuple[str, ...]) -> bool:
    if not allowed:
        return True
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in allowed)


# ── 캐시 ───────────────────────────────────────────────────

def _cache_path(url: str) -> Any:
    return config.cache_dir() / "fetch" / f"{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"


def cache_get(url: str, ttl_hours: float) -> dict[str, Any] | None:
    if ttl_hours <= 0:
        return None
    p = _cache_path(url)
    try:
        if not p.is_file() or time.time() - p.stat().st_mtime > ttl_hours * 3600:
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def cache_put(url: str, doc: dict[str, Any]) -> None:
    p = _cache_path(url)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)
    except OSError as exc:
        log.warning("수집 캐시 저장 실패: %s", exc)


# ── robots · 속도 ───────────────────────────────────────────

async def robots_allowed(url: str, fc: config.FetchConfig) -> tuple[bool, str | None]:
    u = urlparse(url)
    origin = f"{u.scheme}://{u.netloc}"
    cached = _robots.get(origin)
    if cached is None or cached[0] < time.time():
        kind, rp = "allow_all", None
        try:
            async with httpx.AsyncClient(timeout=min(10.0, fc.timeout_s), follow_redirects=True,
                                         headers={"User-Agent": fc.user_agent}) as c:
                resp = await c.get(origin + "/robots.txt")
            if resp.status_code >= 500:
                kind = "unreachable"
            elif resp.status_code < 400:
                rp = RobotFileParser()
                rp.parse(resp.text.splitlines())
                kind = "rules"
        except httpx.HTTPError:
            kind = "unreachable"
        _robots[origin] = (time.time() + ROBOTS_TTL_S, kind, rp)
        if len(_robots) > 2000:
            _robots.clear()
        cached = _robots.get(origin) or (0.0, kind, rp)
    _, kind, rp = cached
    if kind == "unreachable":
        return False, "robots_unreachable"
    if kind == "rules" and rp is not None and not rp.can_fetch(fc.user_agent, url):
        return False, "robots_disallow"
    return True, None


async def rate_limit(host: str, rps: float) -> None:
    if rps <= 0:
        return
    key = (id(asyncio.get_running_loop()), host)
    lock = _locks.get(key)
    if lock is None:
        if len(_locks) > 2000:
            _locks.clear()
        lock = _locks[key] = asyncio.Lock()
    async with lock:
        wait = _next_ok.get(host, 0.0) - time.monotonic()
        if wait > 0:
            await asyncio.sleep(min(wait, 60.0))
        _next_ok[host] = time.monotonic() + 1.0 / rps


# ── 본문 ───────────────────────────────────────────────────

def extract_html(body: bytes, url: str) -> tuple[str, str, str | None]:
    """(제목, 본문 텍스트, 발행일)"""
    import trafilatura

    title, date, text = "", None, None
    try:
        meta = trafilatura.extract_metadata(body, default_url=url)
        if meta is not None:
            title = meta.title or ""
            date = meta.date or None
    except Exception:  # noqa: BLE001
        pass
    try:
        text = trafilatura.extract(body, url=url, output_format="txt", include_comments=False, include_tables=True,
                                   favor_recall=True)
    except Exception:  # noqa: BLE001
        text = None
    if not text or not title:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(body, "lxml")
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not text:
            for tag in soup(["script", "style", "noscript", "template", "svg"]):
                tag.decompose()
            text = soup.get_text("\n", strip=True)
    return title, text or "", date


def extract_pdf(body: bytes) -> list[str] | None:
    try:
        import pypdfium2 as pdfium  # files 서비스와 같은 가상환경에 있다(선택)
    except ImportError:
        return None
    pages: list[str] = []
    pdf = pdfium.PdfDocument(body)
    try:
        for i in range(min(len(pdf), 200)):
            page = pdf[i]
            tp = page.get_textpage()
            pages.append(tp.get_text_range().strip())
            tp.close()
            page.close()
    finally:
        pdf.close()
    return pages


async def download(url: str, fc: config.FetchConfig) -> tuple[int, str, str, bytes, bool]:
    """(상태, 최종 URL, content-type, 본문, 잘렸는지)"""
    headers = {"User-Agent": fc.user_agent, "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
               "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.7"}
    try:
        async with httpx.AsyncClient(timeout=fc.timeout_s, follow_redirects=True, headers=headers) as c:
            async with c.stream("GET", url) as resp:
                buf = bytearray()
                truncated = False
                async for chunk in resp.aiter_bytes():
                    buf += chunk
                    if len(buf) >= fc.max_bytes:
                        truncated = True
                        break
                return resp.status_code, str(resp.url), resp.headers.get("content-type", ""), bytes(buf[: fc.max_bytes]), truncated
    except httpx.TimeoutException as exc:
        raise ProviderError(504, "TIMEOUT", f"수집 시간 초과({fc.timeout_s:g}초): {url[:200]}", {"url": url}) from exc
    except httpx.HTTPError as exc:
        raise provider_error("web", f"{type(exc).__name__}: {exc}", url=url) from exc


def _kind(ctype: str, body: bytes) -> str:
    c = ctype.lower()
    if "pdf" in c or body[:5] == b"%PDF-":
        return "pdf"
    if "html" in c or "xml" in c:
        return "html"
    if c.startswith("text/") or "json" in c:
        return "text"
    if not c:
        head = body[:512].lstrip().lower()
        return "html" if head.startswith(b"<") else "text"
    return "other"


def _decode(body: bytes, ctype: str) -> str:
    charset = None
    for part in ctype.split(";"):
        if part.strip().lower().startswith("charset="):
            charset = part.split("=", 1)[1].strip().strip("\"'")
    for enc in (charset, "utf-8", "cp949"):
        if not enc:
            continue
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", "replace")


def _result(req: FetchRequest, doc: dict[str, Any], *, from_cache: bool) -> dict[str, Any]:
    text = doc.get("text") or ""
    out = {
        "url": req.url, "final_url": doc.get("final_url"), "status": int(doc.get("status") or 0), "allowed": True,
        "reason": doc.get("reason"), "title": doc.get("title") or "", "text": text[: req.max_chars],
        "published_at": doc.get("published_at"), "fetched_at": doc.get("fetched_at") or now_iso(), "from_cache": from_cache,
        "content_type": doc.get("content_type"), "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
        "truncated": len(text) > req.max_chars or bool(doc.get("truncated")),
    }
    if doc.get("pages") is not None:
        out["pages"] = doc["pages"]
    return out


def _denied(req: FetchRequest, reason: str) -> dict[str, Any]:
    return {"url": req.url, "final_url": None, "status": 0, "allowed": False, "reason": reason, "title": "", "text": "",
            "published_at": None, "fetched_at": now_iso(), "from_cache": False}


async def fetch(req: FetchRequest) -> dict[str, Any]:
    fc = config.fetch_config()
    if not fc.enabled:
        return _denied(req, "disabled")
    async with track("fetch", "fetch", request=req.model_dump()) as call:
        call.provider_name, call.model = "web", None
        u = urlparse(req.url)
        host = (u.hostname or "").lower()
        if u.scheme not in ("http", "https") or not host:
            out = _denied(req, "invalid_url")
        elif blocked_host(host):
            out = _denied(req, "blocked_host")
        elif not domain_allowed(host, fc.allowed_domains):
            out = _denied(req, "domain_not_allowed")
        elif (cached := cache_get(req.url, fc.cache_ttl_hours)) is not None:
            out = _result(req, cached, from_cache=True)
        else:
            ok, why = (await robots_allowed(req.url, fc)) if fc.respect_robots else (True, None)
            if not ok:
                out = _denied(req, why or "robots_disallow")
            else:
                await rate_limit(host, fc.rate_limit_rps)
                status, final_url, ctype, body, truncated = await download(req.url, fc)
                final_host = (urlparse(final_url).hostname or "").lower()
                doc: dict[str, Any] = {"final_url": final_url, "status": status, "content_type": ctype.split(";")[0].strip() or None,
                                       "fetched_at": now_iso(), "truncated": truncated, "title": "", "text": "", "published_at": None}
                if not domain_allowed(final_host, fc.allowed_domains) or blocked_host(final_host):
                    out = _denied(req, "redirect_domain_not_allowed")
                    out.update({"final_url": final_url, "status": status})
                    call.response = out
                    return out
                if status >= 400:
                    doc["reason"] = "http_error"
                else:
                    kind = _kind(ctype, body)
                    if kind == "html":
                        title, text, date = await asyncio.to_thread(extract_html, body, final_url)
                        doc.update(title=title, text=text, published_at=date)
                    elif kind == "text":
                        doc["text"] = _decode(body, ctype)
                    elif kind == "pdf":
                        pages = await asyncio.to_thread(extract_pdf, body)
                        if pages is None:
                            doc["reason"] = "unsupported_content_type"
                        else:
                            doc.update(pages=pages, text="\n\n".join(pages))
                    else:
                        doc["reason"] = "unsupported_content_type"
                    doc["text"] = (doc.get("text") or "")[:CACHE_TEXT_MAX]
                    if not doc.get("reason"):
                        cache_put(req.url, doc)
                out = _result(req, doc, from_cache=False)
        call.response = out
        return out
