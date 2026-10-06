"""검색 API(원문 URL 목록) — POST /v1/search.

SEARCH_API_PROVIDER: none(기본 → available=false, results=[], HTTP 200) · brave · tavily · serper · google_cse · searxng · internal · mock
- 주소는 SEARCH_API_BASE_URL 로 바꿀 수 있다(프록시 · 자체 호스팅). 키는 SEARCH_API_KEY, google_cse 는 SEARCH_API_CX 도.
- MODEL_MODE=mock 이면(제공자가 none 이 아닐 때) 네트워크 없이 example.com 결과, record/replay 는 카세트.

요청 모양(공급사 문서 기준)
- brave      GET  https://api.search.brave.com/res/v1/web/search?q=&count=&search_lang=&country=   헤더 X-Subscription-Token
- tavily     POST https://api.tavily.com/search {query, max_results, search_depth}                  헤더 Authorization: Bearer
- serper     POST https://google.serper.dev/search {q, num, gl, hl}                                 헤더 X-API-KEY
- google_cse GET  https://www.googleapis.com/customsearch/v1?key=&cx=&q=&num(≤10)=&hl=&gl=
- searxng    GET  <BASE_URL>/search?q=&format=json&language=
- internal   POST <BASE_URL> {query, locale, limit} → {results|items: [{url|link, title, snippet|content, published_at|date}]}
"""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

import httpx

from . import config
from .errors import ProviderError, not_configured, provider_error
from .runtime import track, with_retries
from .schemas import SearchRequest

Adapter = Callable[[config.SearchConfig, SearchRequest], Awaitable[list[dict[str, Any]]]]


def _lang(locale: str) -> tuple[str, str]:
    """ko-KR → (ko, KR)"""
    parts = re.split(r"[-_]", locale or "ko-KR")
    lang = (parts[0] or "ko").lower()
    country = (parts[1] if len(parts) > 1 else ("KR" if lang == "ko" else "US")).upper()
    return lang, country


def _date(v: Any) -> str | None:
    if not v or not isinstance(v, str):
        return None
    s = v.strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return s[:40]


def _item(url: Any, title: Any, snippet: Any, published: Any = None) -> dict[str, Any] | None:
    if not url:
        return None
    return {"url": str(url), "title": str(title or ""), "snippet": str(snippet or ""), "published_at": _date(published)}


async def _http(method: str, url: str, sc: config.SearchConfig, *, params: dict[str, Any] | None = None,
                json: Any = None, headers: dict[str, str] | None = None) -> Any:
    try:
        async with httpx.AsyncClient(timeout=sc.timeout_s, follow_redirects=True) as c:
            resp = await c.request(method, url, params=params, json=json, headers={"Accept": "application/json", **(headers or {})})
    except httpx.TimeoutException as exc:
        raise ProviderError(504, "TIMEOUT", f"검색 API({sc.provider}) 응답 시간 초과", {"provider": sc.provider}) from exc
    except httpx.HTTPError as exc:
        raise provider_error(sc.provider, f"연결 실패: {exc}", retryable=True) from exc
    if resp.status_code >= 400:
        raise provider_error(sc.provider, resp.text[:300], status=resp.status_code)
    try:
        return resp.json()
    except ValueError as exc:
        raise provider_error(sc.provider, "JSON 이 아닌 응답") from exc


def _need_key(sc: config.SearchConfig) -> str:
    if not sc.api_key:
        raise not_configured("SEARCH_API_KEY", provider=sc.provider)
    return sc.api_key


async def brave(sc: config.SearchConfig, req: SearchRequest) -> list[dict[str, Any]]:
    lang, country = _lang(req.locale)
    data = await _http("GET", (sc.base_url or "https://api.search.brave.com/res/v1").rstrip("/") + "/web/search", sc,
                       params={"q": req.query, "count": min(req.limit, 20), "search_lang": lang, "country": country},
                       headers={"X-Subscription-Token": _need_key(sc)})
    rows = ((data or {}).get("web") or {}).get("results") or []
    return [x for r in rows if (x := _item(r.get("url"), r.get("title"), r.get("description"), r.get("page_age")))]


async def tavily(sc: config.SearchConfig, req: SearchRequest) -> list[dict[str, Any]]:
    data = await _http("POST", (sc.base_url or "https://api.tavily.com").rstrip("/") + "/search", sc,
                       json={"query": req.query, "max_results": min(req.limit, 20), "search_depth": "basic"},
                       headers={"Authorization": f"Bearer {_need_key(sc)}"})
    rows = (data or {}).get("results") or []
    return [x for r in rows if (x := _item(r.get("url"), r.get("title"), r.get("content"), r.get("published_date")))]


async def serper(sc: config.SearchConfig, req: SearchRequest) -> list[dict[str, Any]]:
    lang, country = _lang(req.locale)
    data = await _http("POST", (sc.base_url or "https://google.serper.dev").rstrip("/") + "/search", sc,
                       json={"q": req.query, "num": req.limit, "gl": country.lower(), "hl": lang},
                       headers={"X-API-KEY": _need_key(sc)})
    rows = (data or {}).get("organic") or []
    return [x for r in rows if (x := _item(r.get("link"), r.get("title"), r.get("snippet"), r.get("date")))]


async def google_cse(sc: config.SearchConfig, req: SearchRequest) -> list[dict[str, Any]]:
    if not sc.cx:
        raise not_configured("SEARCH_API_CX(Google 프로그래머블 검색 엔진 ID)", provider=sc.provider)
    lang, country = _lang(req.locale)
    data = await _http("GET", sc.base_url or "https://www.googleapis.com/customsearch/v1", sc,
                       params={"key": _need_key(sc), "cx": sc.cx, "q": req.query, "num": min(req.limit, 10),
                               "hl": lang, "gl": country.lower()})
    out = []
    for r in (data or {}).get("items") or []:
        meta = ((r.get("pagemap") or {}).get("metatags") or [{}])[0]
        x = _item(r.get("link"), r.get("title"), r.get("snippet"), meta.get("article:published_time"))
        if x:
            out.append(x)
    return out


async def searxng(sc: config.SearchConfig, req: SearchRequest) -> list[dict[str, Any]]:
    if not sc.base_url:
        raise not_configured("SEARCH_API_BASE_URL(SearXNG 주소)", provider=sc.provider)
    headers = {"Authorization": f"Bearer {sc.api_key}"} if sc.api_key else None
    data = await _http("GET", sc.base_url.rstrip("/") + "/search", sc,
                       params={"q": req.query, "format": "json", "language": req.locale}, headers=headers)
    rows = (data or {}).get("results") or []
    return [x for r in rows if (x := _item(r.get("url"), r.get("title"), r.get("content"), r.get("publishedDate")))]


async def internal(sc: config.SearchConfig, req: SearchRequest) -> list[dict[str, Any]]:
    """사내 검색 API(가정한 모양). 실제 모양이 다르면 이 함수만 고친다."""
    if not sc.base_url:
        raise not_configured("SEARCH_API_BASE_URL(사내 검색 API 주소)", provider=sc.provider)
    headers = {"Authorization": f"Bearer {sc.api_key}"} if sc.api_key else None
    data = await _http("POST", sc.base_url, sc, json={"query": req.query, "locale": req.locale, "limit": req.limit}, headers=headers)
    rows = (data or {}).get("results") or (data or {}).get("items") or []
    return [x for r in rows if isinstance(r, dict) and (x := _item(
        r.get("url") or r.get("link"), r.get("title"), r.get("snippet") or r.get("content") or r.get("description"),
        r.get("published_at") or r.get("date")))]


def mock_results(req: SearchRequest) -> list[dict[str, Any]]:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", req.query).strip("-")[:40] or "query"
    return [{"url": f"https://example.com/mock/search/{slug}/{i}", "title": f"[mock] {req.query} 결과 {i}",
             "snippet": f"[mock] '{req.query}' 검색 결과 {i}", "published_at": "2026-10-01"}
            for i in range(1, min(req.limit, 5) + 1)]


ADAPTERS: dict[str, Adapter] = {"brave": brave, "tavily": tavily, "serper": serper, "google_cse": google_cse,
                                "searxng": searxng, "internal": internal}


def available(sc: config.SearchConfig | None = None) -> bool:
    sc = sc or config.search_config()
    if sc.provider in ("none", ""):
        return False
    if sc.provider == "mock" or config.model_mode() == "mock":
        return True
    if sc.provider in ("searxng", "internal"):
        return bool(sc.base_url)
    if sc.provider == "google_cse":
        return bool(sc.api_key and sc.cx)
    return sc.provider in ADAPTERS and bool(sc.api_key)


async def search(req: SearchRequest) -> dict[str, Any]:
    sc = config.search_config()
    if sc.provider in ("none", ""):
        return {"available": False, "provider": "none", "results": []}
    async with track("search", "search", request=req.model_dump()) as call:
        call.provider_name, call.model = sc.provider, None
        kp = {"query": req.query, "locale": req.locale, "limit": req.limit}
        hit = await call.replay(kp)
        if hit is not None:
            call.response = dict(hit["response"])
            return call.response
        if call.effective == "mock" or sc.provider == "mock":
            results = mock_results(req)
        else:
            adapter = ADAPTERS.get(sc.provider)
            if adapter is None:
                raise not_configured(f"알 수 없는 SEARCH_API_PROVIDER '{sc.provider}'", known=sorted(ADAPTERS))
            results = await with_retries(lambda: adapter(sc, req), cap="search", timeout_s=sc.timeout_s + 5, call=call)
        out = {"available": True, "provider": sc.provider, "results": results[: req.limit]}
        call.record(kp, out)
        call.response = out
        return out
