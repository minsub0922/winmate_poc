"""요약형 웹 검색 · 검색 API · 웹 수집."""
from __future__ import annotations

import httpx
import pytest
import respx


# ── 요약형 웹 검색 ──────────────────────────────────────────

async def test_websearch_mock_hides_sources(client, monkeypatch):
    r = await client.post("/v1/websearch", json={"task": "mi.ws", "query": "호텔 키오스크 도입 사례"})
    body = r.json()
    assert r.status_code == 200 and "호텔 키오스크 도입 사례" in body["summary"]
    assert body["sources"] == [] and body["returned_sources"] is False and body["queries"] == ["호텔 키오스크 도입 사례"]
    monkeypatch.setenv("WEBSEARCH_RETURN_SOURCES", "true")
    body = (await client.post("/v1/websearch", json={"task": "mi.ws", "query": "호텔 키오스크", "max_sources": 2})).json()
    assert body["returned_sources"] is True and len(body["sources"]) == 2
    assert body["sources"][0]["url"].startswith("https://example.com/mock/")


async def test_websearch_fixture_and_policy(client, mocks_dir, h, monkeypatch):
    h.write_fixture(mocks_dir, "ca.find", {"summary": "경쟁사 A 와 B 가 있다", "sources": [{"url": "https://a.example", "title": "A"}]})
    body = (await client.post("/v1/websearch", json={"task": "ca.find", "query": "q"})).json()
    assert body["summary"] == "경쟁사 A 와 B 가 있다" and body["sources"] == []
    monkeypatch.setenv("WEBSEARCH_RETURN_SOURCES", "true")
    body = (await client.post("/v1/websearch", json={"task": "ca.find", "query": "q"})).json()
    assert body["sources"] == [{"url": "https://a.example", "title": "A", "snippet": None}]
    r = await client.post("/v1/websearch", json={"task": "ca.find", "query": "고객 내부 자료", "confidential": True})
    assert r.status_code == 403 and r.json()["error"]["code"] == "POLICY_CONFIDENTIAL"


# ── 검색 API ───────────────────────────────────────────────

async def test_search_none(client):
    r = await client.post("/v1/search", json={"query": "x", "locale": "ko-KR", "limit": 5})
    assert r.status_code == 200 and r.json() == {"available": False, "provider": "none", "results": []}


async def test_search_mock_mode(client, monkeypatch):
    monkeypatch.setenv("SEARCH_API_PROVIDER", "brave")
    body = (await client.post("/v1/search", json={"query": "사이니지", "limit": 3})).json()
    assert body["available"] is True and body["provider"] == "brave" and len(body["results"]) == 3


@pytest.fixture
def live_search(env, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("SEARCH_API_KEY", "key-1")
    with respx.mock(assert_all_called=True) as router:
        yield router


async def test_search_brave(client, live_search, monkeypatch):
    monkeypatch.setenv("SEARCH_API_PROVIDER", "brave")
    route = live_search.get("https://api.search.brave.com/res/v1/web/search").respond(json={"web": {"results": [
        {"url": "https://a.kr/1", "title": "A", "description": "설명", "page_age": "2026-09-30T10:00:00"}]}})
    body = (await client.post("/v1/search", json={"query": "디스플레이", "locale": "ko-KR", "limit": 5})).json()
    assert body["results"] == [{"url": "https://a.kr/1", "title": "A", "snippet": "설명", "published_at": "2026-09-30T10:00:00"}]
    req = route.calls[0].request
    assert req.headers["x-subscription-token"] == "key-1"
    assert req.url.params["q"] == "디스플레이" and req.url.params["search_lang"] == "ko" and req.url.params["country"] == "KR"


async def test_search_tavily_serper(client, live_search, monkeypatch):
    import json as _json

    monkeypatch.setenv("SEARCH_API_PROVIDER", "tavily")
    t = live_search.post("https://api.tavily.com/search").respond(json={"results": [
        {"url": "https://t.example/1", "title": "T", "content": "본문", "published_date": "2026-10-01"}]})
    body = (await client.post("/v1/search", json={"query": "q", "limit": 2})).json()
    assert body["results"][0]["url"] == "https://t.example/1" and body["results"][0]["published_at"].startswith("2026-10-01")
    assert _json.loads(t.calls[0].request.content) == {"query": "q", "max_results": 2, "search_depth": "basic"}
    assert t.calls[0].request.headers["authorization"] == "Bearer key-1"

    monkeypatch.setenv("SEARCH_API_PROVIDER", "serper")
    s = live_search.post("https://google.serper.dev/search").respond(json={"organic": [
        {"link": "https://s.example/1", "title": "S", "snippet": "스니펫", "date": "3 days ago"}]})
    body = (await client.post("/v1/search", json={"query": "q", "limit": 4})).json()
    assert body["results"] == [{"url": "https://s.example/1", "title": "S", "snippet": "스니펫", "published_at": "3 days ago"}]
    assert _json.loads(s.calls[0].request.content) == {"q": "q", "num": 4, "gl": "kr", "hl": "ko"}
    assert s.calls[0].request.headers["x-api-key"] == "key-1"


async def test_search_google_cse_searxng_internal(client, live_search, monkeypatch):
    monkeypatch.setenv("SEARCH_API_PROVIDER", "google_cse")
    r = await client.post("/v1/search", json={"query": "q"})
    assert r.status_code == 501   # cx 없음
    monkeypatch.setenv("SEARCH_API_CX", "cx-1")
    g = live_search.get("https://www.googleapis.com/customsearch/v1").respond(json={"items": [
        {"link": "https://g.example/1", "title": "G", "snippet": "s",
         "pagemap": {"metatags": [{"article:published_time": "2026-08-01T00:00:00Z"}]}}]})
    body = (await client.post("/v1/search", json={"query": "q", "limit": 20})).json()
    assert body["results"][0]["published_at"] == "2026-08-01T00:00:00+00:00"
    assert g.calls[0].request.url.params["num"] == "10" and g.calls[0].request.url.params["cx"] == "cx-1"

    monkeypatch.setenv("SEARCH_API_PROVIDER", "searxng")
    monkeypatch.setenv("SEARCH_API_BASE_URL", "http://searx.local")
    sx = live_search.get("http://searx.local/search").respond(json={"results": [{"url": "https://x.example", "title": "X", "content": "c"}]})
    body = (await client.post("/v1/search", json={"query": "q"})).json()
    assert body["results"][0]["url"] == "https://x.example" and sx.calls[0].request.url.params["format"] == "json"

    monkeypatch.setenv("SEARCH_API_PROVIDER", "internal")
    monkeypatch.setenv("SEARCH_API_BASE_URL", "http://search.intra/api/search")
    live_search.post("http://search.intra/api/search").respond(json={"items": [{"link": "https://i.example", "title": "I", "description": "d"}]})
    body = (await client.post("/v1/search", json={"query": "q"})).json()
    assert body["results"] == [{"url": "https://i.example", "title": "I", "snippet": "d", "published_at": None}]


async def test_search_upstream_error(client, live_search, monkeypatch):
    monkeypatch.setenv("SEARCH_API_PROVIDER", "brave")
    live_search.get("https://api.search.brave.com/res/v1/web/search").respond(401, json={"error": "bad key"})
    r = await client.post("/v1/search", json={"query": "q"})
    assert r.status_code == 502 and r.json()["error"]["details"]["upstream_status"] == 401


# ── 웹 수집 ────────────────────────────────────────────────

HTML = """<html><head><title>사이니지 시장 보고서</title><meta property="article:published_time" content="2026-09-15"></head>
<body><nav>메뉴</nav><article><h1>사이니지 시장</h1><p>2026년 국내 디지털 사이니지 시장은 크게 성장했다. 호텔과 리테일에서 도입이 늘었다.</p>
<p>특히 키오스크와 결합한 솔루션의 수요가 많다. 이 문단은 본문 추출이 잘 되도록 충분히 길게 쓴 문장이다.</p></article>
<script>var x = 1;</script></body></html>"""


@pytest.fixture
def web(env, monkeypatch):
    monkeypatch.setenv("WEB_FETCH_RATE_LIMIT_RPS", "0")
    with respx.mock(assert_all_called=False) as router:
        yield router


async def test_fetch_disabled(client, monkeypatch):
    monkeypatch.setenv("WEB_FETCH_ENABLED", "false")
    body = (await client.post("/v1/fetch", json={"url": "https://news.example.com/a"})).json()
    assert body["allowed"] is False and body["reason"] == "disabled" and body["text"] == ""


async def test_fetch_html_and_cache(client, web):
    web.get("https://news.example.com/robots.txt").respond(200, text="User-agent: *\nAllow: /\n")
    page = web.get("https://news.example.com/a").respond(200, html=HTML)
    body = (await client.post("/v1/fetch", json={"url": "https://news.example.com/a", "max_chars": 30})).json()
    assert body["allowed"] is True and body["status"] == 200 and body["from_cache"] is False
    assert "사이니지 시장" in body["title"] and "사이니지" in body["text"]   # trafilatura 는 h1 을 제목으로 고르기도 한다
    assert len(body["text"]) == 30 and body["truncated"] is True and body["content_hash"]
    assert body["published_at"] == "2026-09-15" and body["final_url"] == "https://news.example.com/a"
    assert "var x" not in body["text"]
    again = (await client.post("/v1/fetch", json={"url": "https://news.example.com/a"})).json()
    assert again["from_cache"] is True and page.call_count == 1 and "키오스크" in again["text"]


async def test_fetch_robots_disallow_and_domains(client, web, monkeypatch):
    web.get("https://blocked.example.com/robots.txt").respond(200, text="User-agent: WinmateBot\nDisallow: /private\n")
    web.get("https://blocked.example.com/public").respond(200, text="공개", headers={"content-type": "text/plain; charset=utf-8"})
    body = (await client.post("/v1/fetch", json={"url": "https://blocked.example.com/private/x"})).json()
    assert body["allowed"] is False and body["reason"] == "robots_disallow"
    body = (await client.post("/v1/fetch", json={"url": "https://blocked.example.com/public"})).json()
    assert body["allowed"] is True and body["text"] == "공개"

    web.get("https://down.example.com/robots.txt").respond(503)
    body = (await client.post("/v1/fetch", json={"url": "https://down.example.com/a"})).json()
    assert body["reason"] == "robots_unreachable"

    monkeypatch.setenv("WEB_FETCH_RESPECT_ROBOTS", "false")
    monkeypatch.setenv("WEB_FETCH_ALLOWED_DOMAINS", "samsung.com, example.org")
    body = (await client.post("/v1/fetch", json={"url": "https://news.example.com/a"})).json()
    assert body["allowed"] is False and body["reason"] == "domain_not_allowed"
    web.get("https://www.samsung.com/x").respond(200, html="<html><head><title>T</title></head><body><p>삼성</p></body></html>")
    body = (await client.post("/v1/fetch", json={"url": "https://www.samsung.com/x"})).json()
    assert body["allowed"] is True and body["title"] == "T"


async def test_fetch_blocked_and_invalid(client):
    assert (await client.post("/v1/fetch", json={"url": "http://127.0.0.1:5000/api/x"})).json()["reason"] == "blocked_host"
    assert (await client.post("/v1/fetch", json={"url": "ftp://example.com/a"})).json()["reason"] == "invalid_url"


async def test_fetch_http_error_and_timeout(client, web, monkeypatch):
    monkeypatch.setenv("WEB_FETCH_RESPECT_ROBOTS", "false")
    web.get("https://e.example.com/404").respond(404, text="없음")
    body = (await client.post("/v1/fetch", json={"url": "https://e.example.com/404"})).json()
    assert body["allowed"] is True and body["status"] == 404 and body["reason"] == "http_error"
    web.get("https://e.example.com/slow").mock(side_effect=httpx.ReadTimeout("slow"))
    r = await client.post("/v1/fetch", json={"url": "https://e.example.com/slow"})
    assert r.status_code == 504 and r.json()["error"]["code"] == "TIMEOUT"


async def test_fetch_rate_limit(env, monkeypatch):
    import time

    from winmate_ai_tools import fetch

    t0 = time.monotonic()
    await fetch.rate_limit("rl.example.com", 20.0)
    await fetch.rate_limit("rl.example.com", 20.0)
    await fetch.rate_limit("rl.example.com", 20.0)
    assert time.monotonic() - t0 >= 0.09   # 같은 호스트는 1/20초 간격
    t1 = time.monotonic()
    await fetch.rate_limit("other.example.com", 20.0)
    assert time.monotonic() - t1 < 0.04
