"""그래프 공용 — 모델 호출(기밀 정책 §10.13 · 오류 §6.15) · 조종 메모 · 잡 기록 · 그래프 실행."""
from __future__ import annotations

import json
import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from winmate_common.ai import ai
from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.jobs import JobContext, current_job, jobs

from .. import config, core, repo
from ..errors import CONFIDENTIAL_MESSAGE

log = logging.getLogger("winmate.proposal.graph")


class ModelUnavailable(Exception):
    pass


async def llm_json(task: str, *, system: str, user: str, schema: dict[str, Any], confidential: bool,
                   allow_fallback: bool = True) -> dict[str, Any] | None:
    """ai-tools LLM(JSON). 기밀 차단(403) → 잡 실패(문구 고정, 다른 모델로 바꾸지 않음).
    503 · 504 · 429 · 연결 실패 → allow_fallback 이면 None(호출자가 연결 자료 그대로 채움), 아니면 502."""
    try:
        res = await ai().json(task, user, schema, system=system, confidential=confidential)
        return res if isinstance(res, dict) else None
    except ApiError as exc:
        if exc.status == 403 or exc.code == "POLICY_CONFIDENTIAL":
            raise ApiError(403, "POLICY_CONFIDENTIAL", CONFIDENTIAL_MESSAGE) from exc
        if exc.status in (429, 502, 503, 504) or exc.code in ("UPSTREAM_UNAVAILABLE", "TIMEOUT", "RATE_LIMITED"):
            if allow_fallback:
                log.warning("%s 모델 연결 실패(%s) — 연결 자료 그대로", task, exc.code)
                return None
            raise ApiError(502, "UPSTREAM_UNAVAILABLE", "모델 서비스에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요", {"service": "ai-tools"}) from exc
        raise


async def llm_text(task: str, *, system: str, user: str, confidential: bool) -> str | None:
    try:
        return await ai().text(task, user, system=system, confidential=confidential)
    except ApiError as exc:
        if exc.status == 403 or exc.code == "POLICY_CONFIDENTIAL":
            raise ApiError(403, "POLICY_CONFIDENTIAL", CONFIDENTIAL_MESSAGE) from exc
        if exc.status in (429, 502, 503, 504):
            return None
        raise


async def new_memos() -> list[str]:
    ctx = current_job()
    if ctx is None:
        return []
    return [m.get("text") or "" for m in await ctx.new_memos() if m.get("text")]


async def step(name: str, status: str = "done", **data: Any) -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.step(name, status, **data)


async def progress(pct: float, message: str | None = None, **data: Any) -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.progress(pct, message, **data)


async def partial(data: dict[str, Any]) -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.partial(data)


async def check_cancel() -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.check_cancel()


def job_id() -> str | None:
    ctx = current_job()
    return ctx.job.id if ctx else None


async def enqueue(kind: str, payload: dict[str, Any], *, title: str, ref: str, project_id: str | None = None) -> str:
    job = await jobs().enqueue("proposal", kind, payload, title=title, ref=ref, project_id=project_id)
    return job.id


async def running(job_id_: str | None) -> bool:
    if not job_id_:
        return False
    j = await jobs().get(job_id_)
    return bool(j and j.status in ("queued", "running", "awaiting_input"))


def merging(fn: Any) -> Any:
    """dict 상태 그래프는 노드 반환값이 상태 전체를 바꾼다 → 노드 반환을 기존 상태에 합친다.
    노드 경계마다 조종 메모를 꺼내 상태 `memos` 에 쌓는다(§7.0-5)."""
    async def node(state: dict[str, Any]) -> dict[str, Any]:
        memos = await new_memos()
        if memos:
            # 재개(resume)하면 메모를 처음부터 다시 읽는다 → 중복은 뺀다
            state = {**state, "memos": list(dict.fromkeys([*(state.get("memos") or []), *memos]))}
        upd = await fn(state)
        return {**state, **(upd or {})}
    node.__name__ = getattr(fn, "__name__", "node")
    return node


def single(name: str, fn: Any, state_type: Any = dict) -> StateGraph:
    """노드 하나짜리 그래프(작은 잡) — 단계 이벤트 · 취소 · 체크포인트는 run_graph 가 맡는다."""
    g = StateGraph(state_type)
    g.add_node(name, merging(fn))
    g.add_edge(START, name)
    g.add_edge(name, END)
    return g


def chain(nodes: list[tuple[str, Any]], state_type: Any = dict) -> StateGraph:
    g = StateGraph(state_type)
    prev = START
    for name, fn in nodes:
        g.add_node(name, merging(fn))
        g.add_edge(prev, name)
        prev = name
    g.add_edge(prev, END)
    return g


async def run(ctx: JobContext, graph: StateGraph, state: dict[str, Any], *, labels: dict[str, str] | None = None,
              progress_map: dict[str, int] | None = None) -> dict[str, Any] | None:
    return await run_graph(ctx, graph, state, step_labels=labels, progress_map=progress_map)


def dumps(obj: Any, limit: int = 12000) -> str:
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "…"


def customer_conf() -> bool:
    return config.customer_text_confidential()


async def save_message(pid: str, *, scope: str, scope_ref: str | None, role: str, text: str, change_ids: list[str] | None = None,
                       job: str | None = None) -> None:
    from winmate_common.ids import new_id
    mid = new_id("msg")
    await repo.aput("messages", mid, {"id": mid, "proposal_id": pid, "scope": scope, "scope_ref": scope_ref, "role": role, "text": text,
                                      "change_ids": change_ids or [], "job_id": job, "created_iso": config.now_iso()})


async def clear_job(pid: str, key: str, job: str | None) -> None:
    def fn(p: dict[str, Any]) -> None:
        if (p.get("jobs") or {}).get(key) == job:
            core.set_job(p, key, None)
    try:
        await repo.amutate("proposals", pid, fn)
    except Exception:  # noqa: BLE001
        pass
