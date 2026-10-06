"""proposal 워커 — Redis 큐(wm:q:proposal) 소비. `python -m winmate_proposal.worker`.

잡 종류(§6.14) → 처리기. 처리기는 LangGraph(run_graph)로 돈다(thread_id = job_id, 취소 · 메모 · interrupt).
"""
from __future__ import annotations

from typing import Any

from winmate_common.jobs import JobContext, run_worker


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


def _lazy(module: str, fn: str) -> Any:
    async def handler(ctx: JobContext) -> dict[str, Any] | None:
        import importlib
        mod = importlib.import_module(f"winmate_proposal.graphs.{module}")
        return await getattr(mod, fn)(ctx)
    handler.__name__ = f"{module}.{fn}"
    return handler


HANDLERS = {
    "noop": _noop,
    "proposal.section_fill": _lazy("section_fill", "handle"),
    "proposal.sheet_rewrite": _lazy("edit", "handle_rewrite"),
    "proposal.request": _lazy("edit", "handle_request"),
    "proposal.notes_generate": _lazy("edit", "handle_notes"),
    "proposal.generate": _lazy("generate", "handle_generate"),
    "proposal.render": _lazy("generate", "handle_render"),
    "proposal.rfp_extract": _lazy("start", "handle_rfp"),
    "proposal.links_apply": _lazy("start", "handle_links_apply"),
    "proposal.import_extract": _lazy("imports", "handle_extract"),
    "proposal.import_apply": _lazy("imports", "handle_apply"),
    "proposal.one_click": _lazy("one_click", "handle"),
    "proposal.confirm_research": _lazy("confirm", "handle_research"),
    "proposal.comment_suggest": _lazy("review", "handle_suggest"),
    "proposal.review_apply": _lazy("review", "handle_apply"),
    "proposal.export": _lazy("export", "handle"),
    "proposal.reuse": _lazy("reuse", "handle"),
}


def main() -> None:
    run_worker("proposal", HANDLERS)


if __name__ == "__main__":
    main()
