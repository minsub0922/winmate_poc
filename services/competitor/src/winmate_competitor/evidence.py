"""근거 · 출처 · 주장(§5.7 · §7.6) — 그래프들이 함께 쓰는 도우미.

bag(작업본 · 찾기 묶음) = {"sources": {src: …}, "claims": {clm: …}, "citations": [ … ]}.
- 웹 검색 1회 → `sources` 모드: 결과 URL 을 수집(성공한 것만 `web` 출처) · `summary_only` 모드: 요약문 1개 = `websearch_summary` 출처 1개.
- LLM 이 짐작한 URL(url_guess)은 수집에 성공했을 때만 출처가 되고, 실패하면 어디에도 남지 않는다.
- 주장은 인용을 결정적으로 대조(verify)해 상태를 정하고, 인용 구절에 없는 수치는 `[00]` 으로 바꾼다. 인용이 하나도 남지 않으면 주장을 만들지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import now_iso

from . import aix, config, rules, verify
from . import store as R

log = logging.getLogger("winmate.competitor.evidence")

URL_RE = re.compile(r"https?://[^\s\)\]\}\"'<>，。、]+")
KIND_LABEL = {"web": "공개 자료", "websearch_summary": "웹 검색 요약", "kb_case": "사내 사례 DB", "kb_official": "사내 스펙", "file": "사내 자료",
              "user": "직접 입력"}
PUBLIC_KINDS = ("web", "websearch_summary", "file")
KB_KINDS = ("kb_case", "kb_official")
_TEXTS: dict[str, str] = {}


def h(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()[:16]


def host(url: str | None) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1) if m else "").removeprefix("www.")


def subtype_for(url: str, title: str) -> tuple[str, int]:
    u = (url or "").lower()
    t = title or ""
    if any(k in u for k in (".go.kr", "kostat", ".gov")):
        return "정부·통계", 1
    if any(k in u for k in ("/ir", "dart.fss", "/investor")) or "공시" in t:
        return "공시·IR", 1
    if any(k in u for k in ("news", "/article", "press")) or any(k in t for k in ("기사", "뉴스", "보도")):
        return "기사", 4
    if any(k in u for k in ("/product", "/solution", "/display", "/signage")) or "제품" in t:
        return "제품 페이지", 2
    return "기타", 5


_DATE_RES = [re.compile(r"(20\d{2})[.\-/년 ]\s*(\d{1,2})[.\-/월 ]\s*(\d{1,2})"), re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})\s*월?")]


def pub_from_text(text: str | None) -> str | None:
    if not text:
        return None
    m = _DATE_RES[0].search(text)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{mo:02d}-{d:02d}"
    m = _DATE_RES[1].search(text)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return f"{y:04d}-{mo:02d}-01"
    return None


def strip_urls(text: str) -> str:
    return re.sub(r"\s+", " ", URL_RE.sub("", text or "")).strip()


def source_text(src_id: str) -> str | None:
    if src_id in _TEXTS:
        return _TEXTS[src_id]
    text, pages = R.load_snapshot(src_id)
    if text is None and pages:
        text = "\n".join(pages)
    if text is not None:
        _TEXTS[src_id] = text
    return text


def remember_text(src_id: str, text: str, pages: list[str] | None = None) -> None:
    _TEXTS[src_id] = text
    R.save_snapshot(src_id, text, pages)


def add_source(bag: dict[str, Any], src: dict[str, Any], text: str, pages: list[str] | None = None) -> str:
    """같은 출처(최종 URL · 요약 내용 해시 · KB 키)는 하나로. → 출처 id."""
    sources = bag.setdefault("sources", {})
    key = src.get("url") or src.get("kb_key") or src.get("content_hash") or h(src.get("title"), text[:200])
    for sid, s in sources.items():
        if (s.get("url") or s.get("kb_key") or s.get("content_hash")) == key and s.get("kind") == src.get("kind"):
            if src.get("competitor_id") and src["competitor_id"] not in (s.get("competitor_ids") or []):
                s.setdefault("competitor_ids", []).append(src["competitor_id"])
            if src.get("fact_key") and src["fact_key"] not in (s.get("fact_keys") or []):
                s.setdefault("fact_keys", []).append(src["fact_key"])
            return sid
    sid = R.nid("src")
    body = {"id": sid, "state": "used", "classification": "public", "retrieved_at": now_iso(), **src}
    body["competitor_ids"] = [src["competitor_id"]] if src.get("competitor_id") else []
    body["fact_keys"] = [src["fact_key"]] if src.get("fact_key") else []
    body.setdefault("content_hash", h(text))
    sources[sid] = body
    remember_text(sid, text, pages)
    return sid


def evidence(ev: list[dict[str, Any]], *, source_id: str, kind: str, title: str, text: str, label: str = "", page: int | None = None,
             prefix: str = "E") -> str:
    eid = f"{prefix}{sum(1 for e in ev if e['id'].startswith(prefix)) + 1}"
    ev.append({"id": eid, "source_id": source_id, "kind": kind, "title": title, "text": text, "label": label or KIND_LABEL.get(kind, kind),
               "page": page})
    return eid


async def fetch_into(bag: dict[str, Any], ev: list[dict[str, Any]], budget: aix.Budget, url: str, *, title: str = "", query: str | None = None,
                     competitor_id: str | None = None, fact_key: str | None = None) -> str | None:
    """URL 하나 수집 → 성공하면 `web` 출처 · 근거. 실패하면 아무것도 남기지 않는다."""
    if budget.web_unavailable or not budget.take("fetch"):
        return None
    page = await aix.fetch(url)
    if not page:
        return None
    text = page.get("text") or "\n".join(page.get("pages") or [])
    final = page.get("final_url") or url
    sub, auth = subtype_for(final, page.get("title") or title)
    pub = page.get("published_at") or pub_from_text(text[:3000])
    src = {"kind": "web", "subtype": sub, "title": page.get("title") or title or final, "publisher": host(final), "url": final, "final_url": final,
           "published_at": pub[:10] if pub else None, "published_basis": "meta" if page.get("published_at") else ("text" if pub else "unknown"),
           "retrieved_at": page.get("fetched_at") or now_iso(), "content_hash": page.get("content_hash") or h(text), "authority": auth,
           "mode": budget.mode, "competitor_id": competitor_id, "fact_key": fact_key, "query": query}
    if src["published_at"] and rules.is_stale(src["published_at"]):
        src["state"] = "excluded"
        src["excluded_reason"] = "stale"
    sid = add_source(bag, src, text, page.get("pages"))
    if bag["sources"][sid].get("state") != "excluded":
        pages = page.get("pages") or []
        if pages:
            for i, ptxt in enumerate(pages[:10], start=1):
                evidence(ev, source_id=sid, kind="web", title=src["title"], text=ptxt, page=i, label=f"공개 자료 · {sub}")
        else:
            evidence(ev, source_id=sid, kind="web", title=src["title"], text=text, label=f"공개 자료 · {sub}")
    return sid


async def web_gather(bag: dict[str, Any], ev: list[dict[str, Any]], budget: aix.Budget, *, task: str, query: str, sensitive: list[str],
                     competitor_id: str | None = None, fact_key: str | None = None, queries_log: list[str] | None = None) -> int:
    """웹 검색 1회 → 근거 · 출처. 검색어 보호를 통과 못 하면 건너뛴다. → 새 근거 수."""
    if budget.web_unavailable:
        return 0
    q = aix.query_guard(query, sensitive)
    if not q:
        return 0
    if not budget.take("websearch"):
        return 0
    if queries_log is not None:
        queries_log.append(q)
    try:
        res = await aix.websearch(task, q)
    except ApiError as exc:
        if aix.web_down(exc):
            budget.web_unavailable = True
            return 0
        raise
    before = len(ev)
    summary = res.get("summary") or ""
    urls: list[tuple[str, str]] = []
    if budget.mode == "sources":
        if (budget.caps.get("search_api") or {}).get("available"):
            try:
                sr = await aix.search(q, limit=3)
                urls.extend((r["url"], r.get("title") or "") for r in (sr.get("results") or [])[:3] if r.get("url"))
            except ApiError:
                pass
        urls.extend((s["url"], s.get("title") or "") for s in res.get("sources") or [] if s.get("url"))
    urls.extend((u.rstrip(".,"), "") for u in URL_RE.findall(summary))
    fetched = 0
    seen: set[str] = set()
    for url, title in urls:
        if url in seen:
            continue
        seen.add(url)
        if await fetch_into(bag, ev, budget, url, title=title, query=q, competitor_id=competitor_id, fact_key=fact_key):
            fetched += 1
    if summary and (budget.mode == "summary_only" or fetched == 0):
        stext = strip_urls(summary)
        pub = pub_from_text(stext)
        src = {"kind": "websearch_summary", "subtype": "", "title": f"웹 검색 요약 · {q}", "publisher": "웹 검색 요약", "url": None,
               "published_at": pub[:10] if pub else None, "published_basis": "text" if pub else "unknown", "authority": 6, "mode": budget.mode,
               "competitor_id": competitor_id, "fact_key": fact_key, "query": q, "summary": stext, "content_hash": h("ws", q, stext)}
        sid = add_source(bag, src, stext)
        evidence(ev, source_id=sid, kind="websearch_summary", title=src["title"], text=stext, label="웹 검색 요약")
    return len(ev) - before


# ── 주장 ─────────────────────────────────────────────────
def make_claim(bag: dict[str, Any], *, text: str, cites: list[tuple[dict[str, Any], str]], competitor_id: str | None = None,
               fact_key: str | None = None, criterion_id: str | None = None, block: str = "fact", allow_numbers_from: list[str] | None = None) -> str | None:
    """인용(근거, 구절)을 대조해 주장을 만든다. 살아남은 인용이 없으면 None(그 주장은 어디에도 남지 않는다)."""
    live: list[dict[str, Any]] = []
    for e, quote in cites:
        src = (bag.get("sources") or {}).get(e["source_id"]) or {}
        res = verify.check_citation(text, quote, src, e.get("text"))
        if res["status"] == "dropped":
            continue
        live.append({"source_id": e["source_id"], "quote": verify.strip_ellipsis(quote)[:400], "page": e.get("page"), "check": res["check"],
                     "status": res["status"], "reason_code": res["reason_code"], "reason_text": res["reason_text"], "highlight": res["highlight"],
                     "verified_at": now_iso(), "source_kind": src.get("kind")})
    if not live:
        return None
    quotes = [c["quote"] for c in live] + list(allow_numbers_from or [])
    clean, removed = verify.scrub_numbers(text, quotes)
    cid = R.nid("clm")
    for c in live:
        c["claim_id"] = cid
    status = verify.claim_status(live)
    if removed and status == "matched":
        status = "needs_check"
    n_bad = sum(1 for c in live if c["status"] != "matched")
    bag.setdefault("claims", {})[cid] = {"id": cid, "text": clean, "numbers": [n.raw for n in verify.parse_numbers(clean)], "status": status,
                                         "label": verify.claim_label(status, n_bad), "competitor_id": competitor_id, "fact_key": fact_key,
                                         "criterion_id": criterion_id, "block": block, "created_by": "agent", "unsupported": removed,
                                         "reasons": [{"code": "NUMBER_UNSUPPORTED", "text": verify.reason_text("NUMBER_UNSUPPORTED")}] if removed else []}
    bag.setdefault("citations", []).extend(live)
    return cid


def claim_quotes(bag: dict[str, Any], claim_ids: list[str]) -> list[str]:
    ids = set(claim_ids)
    return [c["quote"] for c in bag.get("citations") or [] if c.get("claim_id") in ids]


def claim_sources(bag: dict[str, Any], claim_ids: list[str]) -> list[str]:
    ids = set(claim_ids)
    out: list[str] = []
    for c in bag.get("citations") or []:
        if c.get("claim_id") in ids and c["source_id"] not in out:
            out.append(c["source_id"])
    return out


def drop_competitor(bag: dict[str, Any], cmp_id: str) -> None:
    """다시 모으기 전 그 경쟁사의 주장 · 인용을 지운다(출처는 다른 곳이 쓰지 않으면 지운다)."""
    gone = {k for k, c in (bag.get("claims") or {}).items() if c.get("competitor_id") == cmp_id}
    for k in gone:
        bag["claims"].pop(k, None)
    bag["citations"] = [c for c in bag.get("citations") or [] if c.get("claim_id") not in gone]
    used = {c["source_id"] for c in bag["citations"]}
    for sid, s in list((bag.get("sources") or {}).items()):
        if cmp_id in (s.get("competitor_ids") or []):
            s["competitor_ids"] = [x for x in s["competitor_ids"] if x != cmp_id]
            if not s["competitor_ids"] and sid not in used and s.get("kind") not in KB_KINDS:
                bag["sources"].pop(sid, None)


def footer(bag: dict[str, Any], claim_ids: list[str] | None = None) -> dict[str, Any]:
    """출처 요약 — `출처 {n} · 공개 자료 {a} · 사내 사례 DB {b} · [수치는 확인 후 확정]`."""
    ids = set(claim_ids) if claim_ids is not None else set((bag.get("claims") or {}).keys())
    sids = {c["source_id"] for c in bag.get("citations") or [] if c.get("claim_id") in ids}
    srcs = [bag["sources"][s] for s in sids if s in (bag.get("sources") or {}) and bag["sources"][s].get("state", "used") != "excluded"]
    public = sum(1 for s in srcs if s.get("kind") in PUBLIC_KINDS)
    kb = sum(1 for s in srcs if s.get("kind") in KB_KINDS)
    unverified = False
    for cid in ids:
        cl = (bag.get("claims") or {}).get(cid) or {}
        if (cl.get("numbers") and cl.get("status") not in ("matched", "confirmed")) or "[00]" in (cl.get("text") or ""):
            unverified = True
            break
    return {"sources": public + kb, "public": public, "kb_case": kb, "unverified": unverified}


def footer_text(f: dict[str, Any], *, detail: bool = False) -> str:
    t = f"출처 {f.get('sources', 0)} · 공개 자료 {f.get('public', 0)} · 사내 사례 DB {f.get('kb_case', 0)}"
    if detail:
        return t + " · 수치는 공개 자료로만 채우고, 못 찾은 건 [확인 필요] 로 남겨요"
    if f.get("unverified"):
        t += " · [수치는 확인 후 확정]"
    return t
