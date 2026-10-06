from __future__ import annotations

import json
import operator
from typing import Annotated, TypedDict

import pytest
from fastapi import APIRouter
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel

from winmate_common import testing
from winmate_common.app import create_app
from winmate_common.client import ServiceClient
from winmate_common.contracts import Contract, ContractViolation
from winmate_common.errors import ApiError, not_found
from winmate_common.graph import run_graph
from winmate_common.jobs import JobContext, jobs
from winmate_common.store import DocStore


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="requirements"):
        yield tmp_path


def test_store_versions(env):
    s = DocStore(env / "t.sqlite")
    a = s.put("specs", "rq_1", {"title": "A", "project_id": "p1"})
    assert a["version"] == 1
    b = s.patch("specs", "rq_1", {"title": "B"})
    assert b["version"] == 2 and b["title"] == "B"
    s.put("specs", "rq_2", {"title": "C", "project_id": "p2"})
    items, cur = s.list("specs", where={"project_id": "p1"})
    assert [i["id"] for i in items] == ["rq_1"] and cur is None
    assert [v["version"] for v in s.versions("specs", "rq_1")] == [2, 1]
    r = s.restore("specs", "rq_1", 1)
    assert r["title"] == "A" and r["version"] == 3
    items, cur = s.list("specs", limit=1)
    assert len(items) == 1 and cur is not None
    items2, _ = s.list("specs", limit=1, cursor=cur)
    assert items2[0]["id"] != items[0]["id"]


def _kb_app():
    app = create_app("kb")
    router = APIRouter(prefix="/v1")

    class Item(BaseModel):
        id: str
        name: str

    @router.get("/things/{thing_id}", response_model=Item)
    async def get_thing(thing_id: str) -> Item:
        if thing_id == "missing":
            raise not_found("thing", thing_id)
        return Item(id=thing_id, name="이름")

    app.include_router(router)
    return app


async def test_client_inprocess_and_contract(env, monkeypatch):
    kb = _kb_app()
    spec = kb.openapi()
    contract = Contract("kb", spec)
    monkeypatch.setattr("winmate_common.client.load_contract", lambda s: contract if s == "kb" else None)
    with testing.inprocess({"kb": kb}):
        c = ServiceClient("kb")
        res = await c.get("/v1/things/abc")
        assert res == {"id": "abc", "name": "이름"}
        with pytest.raises(ApiError) as ei:
            await c.get("/v1/things/missing")
        assert ei.value.status == 404 and ei.value.code == "NOT_FOUND"
        with pytest.raises(ContractViolation):
            await c.get("/v1/unknown")


def test_consumes_rule(env):
    # requirements 는 proposal 을 호출할 수 없다(consumes 에 없음)
    with pytest.raises(RuntimeError):
        ServiceClient("proposal")
    ServiceClient("kb")


class S(TypedDict, total=False):
    steps: Annotated[list[str], operator.add]
    answer: str


def _builder() -> StateGraph:
    def a(state: S) -> S:
        return {"steps": ["a"]}

    def ask(state: S) -> S:
        ans = interrupt({"question": "이름은?", "kind": "text"})
        return {"steps": ["ask"], "answer": ans}

    def b(state: S) -> S:
        return {"steps": ["b"]}

    g = StateGraph(S)
    g.add_node("a", a)
    g.add_node("ask", ask)
    g.add_node("b", b)
    g.add_edge(START, "a")
    g.add_edge("a", "ask")
    g.add_edge("ask", "b")
    g.add_edge("b", END)
    return g


async def test_jobs_with_graph_interrupt(env):
    testing.use_fake_redis()
    seen: dict = {}

    async def handler(ctx: JobContext):
        final = await run_graph(ctx, _builder(), {"steps": []})
        seen["final"] = final
        return {"answer": final["answer"], "steps": final["steps"]}

    job = await jobs().enqueue("requirements", "demo", {"x": 1}, title="데모")
    assert job.status == "queued"
    n = await testing.drain_jobs("requirements", {"demo": handler})
    assert n == 1
    j = await jobs().get(job.id)
    assert j.status == "awaiting_input"
    assert j.input_request == {"question": "이름은?", "kind": "text"}

    await jobs().provide_input(job.id, "민섭")
    await testing.drain_jobs("requirements", {"demo": handler})
    j = await jobs().get(job.id)
    assert j.status == "succeeded", j.error
    assert j.result == {"answer": "민섭", "steps": ["a", "ask", "b"]}
    evs = await jobs().events(job.id)
    types = [e["type"] for _, e in evs]
    assert "awaiting_input" in types and types[-1] == "done"
    notes = await jobs().notifications(j.owner)
    assert any(n["status"] == "succeeded" for _, n in notes)


async def test_job_cancel(env):
    testing.use_fake_redis()
    job = await jobs().enqueue("requirements", "slow", {})
    await jobs().cancel(job.id)
    j = await jobs().get(job.id)
    assert j.status == "canceled"

    async def handler(ctx):
        raise AssertionError("should not run")

    await testing.drain_jobs("requirements", {"slow": handler})
    assert (await jobs().get(job.id)).status == "canceled"


async def test_schedule(env):
    testing.use_fake_redis()
    sid = await jobs().schedule("requirements", "recheck", {"a": 1}, run_at=1.0, title="재확인")
    assert any(s["id"] == sid for s in await jobs().schedules())
    started = await jobs().run_due_schedules(now=2.0)
    assert len(started) == 1
    j = await jobs().get(started[0])
    assert j.kind == "recheck" and j.payload["a"] == 1


async def test_platform_apps_inprocess(tmp_path):
    """기능 서비스 테스트가 플랫폼 실제 앱을 in-process 로 부를 수 있다(계약 검증 포함)."""
    from winmate_common.client import ServiceClient

    with testing.environment(tmp_path, service="requirements"):
        testing.use_fake_redis()
        apps = testing.platform_apps()
        assert set(apps) == set(testing.PLATFORM_SERVICES)
        with testing.inprocess(apps):
            caps = await ServiceClient("ai-tools").get("/v1/capabilities")
            assert caps["mode"] == "mock"
            out = await ServiceClient("ai-tools").post("/v1/llm/chat", json={
                "task": "rq.smoke", "messages": [{"role": "user", "content": "안녕"}], "confidential": True})
            assert out["content"]   # mock 은 기밀도 막지 않는다
        assert "HANDLERS" not in apps and isinstance(testing.load_service_worker("export"), dict)
