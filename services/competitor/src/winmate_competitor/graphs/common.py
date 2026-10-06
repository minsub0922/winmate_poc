"""그래프 공용 — 직선 그래프 · 작업 저장 · 잡 맥락."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.graph import run_graph
from winmate_common.jobs import JobCanceled, JobContext, current_job, jobs

from .. import service
from .. import store as R

log = logging.getLogger("winmate.competitor.graph")


class S(TypedDict, total=False):
    analysis_id: str
    job_id: str
    p: dict[str, Any]
    result: dict[str, Any]


Node = Callable[[S], Awaitable[dict[str, Any]]]


def linear(steps: list[tuple[str, Node]], state_type: Any = S) -> StateGraph:
    g = StateGraph(state_type)
    prev = START
    for name, fn in steps:
        g.add_node(name, fn)
        g.add_edge(prev, name)
        prev = name
    g.add_edge(prev, END)
    return g


async def run_linear(ctx: JobContext, steps: list[tuple[str, Node]], labels: dict[str, str]) -> dict[str, Any]:
    final = await run_graph(ctx, linear(steps), {"analysis_id": ctx.payload.get("analysis_id", ""), "job_id": ctx.job.id, "p": dict(ctx.payload),
                                                 "result": {}}, step_labels=labels)
    return dict((final or {}).get("result") or {})


async def doc_of(aid: str) -> dict[str, Any]:
    doc = await R.call(R.get_analysis, aid)
    if doc is None:
        raise RuntimeError(f"작업이 없어요: {aid}")
    return doc


async def save(aid: str, fn: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    return await R.call(R.update_analysis, aid, fn)


async def register(doc: dict[str, Any]) -> None:
    try:
        await service.register(doc)
    except Exception:  # noqa: BLE001
        log.exception("색인 실패")


async def check_cancel() -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.check_cancel()


async def step(name: str, status: str = "done", **data: Any) -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.step(name, status, **data)


async def progress(pct: int, message: str | None = None, **data: Any) -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.progress(pct, message, **data)


async def wait_job_end(job_id: str | None, timeout_s: float = 60.0) -> None:
    """앞 잡(취소 요청됨)이 끝날 때까지 기다린다 — 같은 작업본을 두 잡이 함께 고치지 않게."""
    if not job_id:
        return
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    while loop.time() - t0 < timeout_s:
        j = await jobs().get(job_id)
        if j is None or j.status in ("succeeded", "failed", "canceled"):
            return
        await asyncio.sleep(0.25)


def unwrap_cancel(exc: BaseException) -> BaseException:
    """TaskGroup 의 ExceptionGroup 안에 취소가 있으면 그것을 꺼낸다."""
    if isinstance(exc, BaseExceptionGroup):
        for e in exc.exceptions:
            if isinstance(e, JobCanceled):
                return e
        return exc.exceptions[0] if exc.exceptions else exc
    return exc
