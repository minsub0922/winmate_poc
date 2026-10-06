"""LangGraph 워크플로를 잡으로 돌리는 도우미.

    builder = StateGraph(State); builder.add_node(...); ...
    async def handle_analyze(ctx: JobContext):
        final = await run_graph(ctx, builder, {"report_id": ctx.payload["report_id"]})
        if final is None:       # 사람 입력 대기(interrupt) — 워커가 awaiting_input 으로 표시함
            return None
        return {"report_id": final["report_id"]}

- thread_id = job_id, 체크포인트는 서비스별 SQLite(`data/<service>/checkpoints.sqlite`)
- 노드가 끝날 때마다 step 이벤트를 내고 취소 플래그를 확인한다
- 노드 안에서 `interrupt({...})` 를 부르면 잡은 awaiting_input 이 되고,
  jobs API 로 답이 들어오면 같은 thread 로 `Command(resume=답)` 이어서 실행된다
- 노드 안에서 진행률·메모가 필요하면 `current_job()` 을 쓴다
"""
from __future__ import annotations

from typing import Any

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph
from langgraph.types import Command

from .env import settings
from .jobs import AwaitingInput, JobContext


def checkpoint_path(service: str) -> str:
    return str(settings().service_data_dir(service) / "checkpoints.sqlite")


async def run_graph(
    ctx: JobContext,
    builder: StateGraph,
    initial_state: dict[str, Any],
    *,
    recursion_limit: int = 100,
    step_labels: dict[str, str] | None = None,
    progress_map: dict[str, int] | None = None,
) -> dict[str, Any] | None:
    """그래프를 실행해 최종 상태를 돌려준다. 사람 입력을 기다리게 되면 AwaitingInput 을 던진다(워커가 처리)."""
    service = ctx.job.service
    config = {"configurable": {"thread_id": ctx.job.id}, "recursion_limit": recursion_limit}
    async with AsyncSqliteSaver.from_conn_string(checkpoint_path(service)) as saver:
        graph = builder.compile(checkpointer=saver)
        inp: Any = Command(resume=ctx.resume_value) if ctx.is_resume else initial_state
        async for chunk in graph.astream(inp, config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    interrupts = update if isinstance(update, (list, tuple)) else [update]
                    value = getattr(interrupts[0], "value", interrupts[0]) if interrupts else {}
                    request = value if isinstance(value, dict) else {"question": value}
                    raise AwaitingInput(request)
                label = (step_labels or {}).get(node, node)
                await ctx.step(node, "done", label=label)
                if progress_map and node in progress_map:
                    await ctx.progress(progress_map[node], label)
            await ctx.check_cancel()
        state = await graph.aget_state(config)
        return dict(state.values)
