"""competitor 워커 — Redis 큐(wm:q:competitor) 소비. `python -m winmate_competitor.worker`.

잡 종류(§7.1): ca.find · ca.analyze · ca.research · ca.candidate_add · ca.export · ca.recheck · ca.source_add.
"""
from __future__ import annotations

from winmate_common.jobs import JobContext, run_worker

from .graphs import analyze, find, misc


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


HANDLERS = {
    "ca.find": find.handle,
    "ca.analyze": analyze.handle,
    "ca.research": misc.handle_research,
    "ca.candidate_add": misc.handle_candidate_add,
    "ca.export": misc.handle_export,
    "ca.recheck": misc.handle_recheck,
    "ca.source_add": misc.handle_source_add,
    "noop": _noop,
}


def main() -> None:
    run_worker("competitor", HANDLERS)


if __name__ == "__main__":
    main()
