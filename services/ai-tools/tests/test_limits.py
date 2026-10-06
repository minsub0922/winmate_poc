"""한도: Redis(fakeredis) 분당 · 하루 카운터 → 429, 실패한 호출은 되돌림, mock 모드는 한도 없음."""
from __future__ import annotations

import pytest

from winmate_common import testing
from winmate_ai_tools import providers
from winmate_ai_tools.errors import provider_error
from winmate_ai_tools.providers.base import LLMResult, Provider


class Flaky(Provider):
    name = "fake"

    def __init__(self, fail_times: int = 0, status: int = 503):
        self.fail_times = fail_times
        self.status = status
        self.n = 0

    async def chat(self, cfg, call):
        self.n += 1
        if self.n <= self.fail_times:
            raise provider_error("fake", "busy", status=self.status)
        return LLMResult(text="ok")


@pytest.fixture
def live(env, monkeypatch):
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    def install(p: Provider) -> Provider:
        monkeypatch.setitem(providers.REGISTRY, "fake", lambda: p)
        providers.reset()
        return p

    return install


def body(task: str = "rq.limit") -> dict:
    return {"task": task, "messages": [{"role": "user", "content": "hi"}]}


async def test_rpm_429(client, live, monkeypatch):
    live(Flaky())
    monkeypatch.setenv("LLM_RPM", "2")
    assert (await client.post("/v1/llm/chat", json=body())).status_code == 200
    assert (await client.post("/v1/llm/chat", json=body())).status_code == 200
    r = await client.post("/v1/llm/chat", json=body())
    assert r.status_code == 429
    err = r.json()["error"]
    assert err["code"] == "RATE_LIMITED" and err["details"]["limit"] == 2 and err["details"]["window"] == "minute"
    usage = (await client.get("/v1/usage")).json()["usage"]["llm"]
    assert usage["today"] == 2 and usage["this_minute"] == 2 and usage["remaining"] == 1998


async def test_daily_429_and_refund(client, live, monkeypatch):
    p = live(Flaky(fail_times=3, status=400))   # 400 은 재시도하지 않는다 → 실패 → 하루 카운터 되돌림
    monkeypatch.setenv("LLM_DAILY_LIMIT", "2")
    r = await client.post("/v1/llm/chat", json=body())
    assert r.status_code == 502 and r.json()["error"]["code"] == "PROVIDER_ERROR"
    assert (await client.get("/v1/capabilities")).json()["usage_today"]["llm"] == 0
    p.fail_times = 0
    assert (await client.post("/v1/llm/chat", json=body())).status_code == 200
    assert (await client.post("/v1/llm/chat", json=body())).status_code == 200
    r = await client.post("/v1/llm/chat", json=body())
    assert r.status_code == 429 and r.json()["error"]["code"] == "DAILY_LIMIT_EXCEEDED"
    assert (await client.get("/v1/capabilities")).json()["usage_today"]["llm"] == 2


async def test_t2i_daily_counts_images(client, live, monkeypatch, files):
    monkeypatch.setenv("T2I_PROVIDER", "mock")
    monkeypatch.setenv("T2I_DAILY_LIMIT", "3")
    req = {"task": "img.gen", "prompt": "매장", "n": 2}
    assert (await client.post("/v1/t2i/generate", json=req)).status_code == 200
    r = await client.post("/v1/t2i/generate", json=req)
    assert r.status_code == 429 and r.json()["error"]["details"]["requested"] == 2
    assert (await client.post("/v1/t2i/generate", json={**req, "n": 1})).status_code == 200


async def test_retry_on_5xx_then_ok(client, live):
    p = live(Flaky(fail_times=2, status=503))
    r = await client.post("/v1/llm/chat", json=body())
    assert r.status_code == 200 and p.n == 3
    rec = (await client.get("/v1/calls", params={"capability": "llm"})).json()["items"][0]
    assert rec["attempts"] == 3


async def test_retry_exhausted_upstream_429(client, live):
    p = live(Flaky(fail_times=5, status=429))
    r = await client.post("/v1/llm/chat", json=body())
    assert r.status_code == 429 and r.json()["error"]["code"] == "RATE_LIMITED" and p.n == 3
    assert r.json()["error"]["details"]["upstream_status"] == 429


async def test_timeout_504(client, live, monkeypatch):
    import asyncio

    class Slow(Provider):
        name = "fake"

        async def chat(self, cfg, call):
            await asyncio.sleep(5)
            return LLMResult(text="late")

    live(Slow())
    monkeypatch.setenv("LLM_TIMEOUT_S", "0.05")
    r = await client.post("/v1/llm/chat", json=body())
    assert r.status_code == 504 and r.json()["error"]["code"] == "TIMEOUT"


async def test_concurrency_semaphore(client, live, monkeypatch):
    import asyncio

    state = {"now": 0, "max": 0}

    class Counting(Provider):
        name = "fake"

        async def chat(self, cfg, call):
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
            await asyncio.sleep(0.02)
            state["now"] -= 1
            return LLMResult(text="ok")

    live(Counting())
    monkeypatch.setenv("LLM_MAX_CONCURRENCY", "2")
    monkeypatch.setenv("LLM_RPM", "0")
    rs = await asyncio.gather(*(client.post("/v1/llm/chat", json=body()) for _ in range(6)))
    assert all(r.status_code == 200 for r in rs) and state["max"] == 2


async def test_mock_mode_has_no_limits(client, monkeypatch):
    monkeypatch.setenv("LLM_RPM", "1")
    for _ in range(3):
        assert (await client.post("/v1/llm/chat", json=body())).status_code == 200

