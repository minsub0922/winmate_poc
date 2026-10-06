"""vp 워커 — Redis 큐(wm:q:vp) 소비. `python -m winmate_vp.worker`.

잡 종류(05-vp.md §7): vp.materials · vp.generate · vp.revise · vp.images · vp.export · vp.pack_offer — 처리기는 workflows.HANDLERS.
"""
from __future__ import annotations

from winmate_common.jobs import JobContext, run_worker

from .workflows import HANDLERS as _FLOW


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


HANDLERS = {"noop": _noop, **_FLOW}


def main() -> None:
    run_worker("vp", HANDLERS)


if __name__ == "__main__":
    main()
