"""storyboard 워커 — Redis 큐(wm:q:storyboard) 소비. `python -m winmate_storyboard.worker`.

잡 종류(02-storyboard.md §7.1) — 모두 LangGraph(`run_graph`, thread_id = job_id):
sb.prepare · sb.direction · sb.messages · sb.outline · sb.space.questions · sb.space.compose · sb.revise · sb.rq_sync ·
sb.trace.apply · sb.trace.refresh · sb.export
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import StateGraph
from winmate_common.graph import run_graph
from winmate_common.jobs import JobContext, run_worker

from . import graphs, repo, service

log = logging.getLogger("winmate.storyboard.worker")


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


def _handler(build: Callable[[], StateGraph], keys: tuple[str, ...] = (), ref_kind: str = "storyboard",
             ref_key: str | None = None) -> Callable[[JobContext], Any]:
    async def run(ctx: JobContext) -> dict[str, Any]:
        p = ctx.payload
        sb_id = p["sb_id"]
        init: dict[str, Any] = {"sb_id": sb_id, **{k: p.get(k) for k in keys}}
        try:
            final = await run_graph(ctx, build(), init)
        except Exception:
            # 실패해도 화면이 멈추지 않게 진행 표시를 푼다
            if ref_kind == "space" and p.get("space_id"):
                await _clear_space(sb_id, p["space_id"])
            if ref_kind == "revision" and p.get("revision_id"):
                rev = await repo.get_revision(p["revision_id"])
                if rev is not None and rev.get("status") == "running":
                    rev["status"] = "failed"
                    await repo.put_revision(rev["id"], rev)
            if ref_kind == "sync_preview" and p.get("preview_id"):
                pv = await repo.get_preview(p["preview_id"])
                if pv is not None:
                    pv["status"] = "failed"
                    await repo.put_preview(pv["id"], pv)
            raise
        finally:
            await service.finish_job(sb_id, ctx.job.id)
        ref_id = p.get(ref_key) if ref_key else sb_id
        out: dict[str, Any] = {"ref": {"kind": ref_kind, "id": ref_id or sb_id}}
        if final and final.get("result"):
            out.update(final["result"])
        return out

    return run


async def _clear_space(sb_id: str, spc: str) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        for sp in (d.get("outline") or {}).get("spaces") or []:
            if sp["id"] == spc:
                sp["composing"] = False
                sp["compose_job"] = None
                sp["questions_job"] = None
                return d
        return None
    try:
        await service.mutate(sb_id, fn, content=False)
    except Exception:  # noqa: BLE001
        log.warning("공간 표시 풀기 실패 %s/%s", sb_id, spc)


async def _rq_sync(ctx: JobContext) -> dict[str, Any]:
    kind = "sync_preview" if ctx.payload.get("dry_run") else "storyboard"
    return await _handler(graphs.build_rq_sync, ("requirement_id", "to_version", "reply_id", "dry_run", "preview_id"), kind,
                          "preview_id" if kind == "sync_preview" else None)(ctx)


HANDLERS = {
    "noop": _noop,
    "sb.prepare": _handler(graphs.build_prepare),
    "sb.direction": _handler(graphs.build_direction),
    "sb.messages": _handler(graphs.build_messages),
    "sb.outline": _handler(graphs.build_outline, ("retry",)),
    "sb.space.questions": _handler(graphs.build_space_questions, ("space_id",), "space", "space_id"),
    "sb.space.compose": _handler(graphs.build_space_compose, ("space_id",), "space", "space_id"),
    "sb.revise": _handler(graphs.build_revise, ("revision_id",), "revision", "revision_id"),
    "sb.rq_sync": _rq_sync,
    "sb.trace.apply": _handler(graphs.build_trace_apply, ("rq_item_id", "option_id")),
    "sb.trace.refresh": _handler(graphs.build_trace_refresh),
    "sb.export": _handler(graphs.build_export, ("format", "options", "version")),
}


def main() -> None:
    run_worker("storyboard", HANDLERS)


if __name__ == "__main__":
    main()
