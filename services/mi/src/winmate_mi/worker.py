"""mi 워커 — Redis 큐(wm:q:mi) 소비. `python -m winmate_mi.worker`.

잡 종류(§7.1): mi.design · mi.analyze · mi.revise · mi.fixscan · mi.layout · mi.source_add · mi.competitor_add · mi.onepager · mi.export ·
mi.recheck · mi.import_ca · mi.facts_research. 모두 LangGraph(winmate_common.graph.run_graph) 로 돈다.
"""
from __future__ import annotations

from winmate_common.jobs import JobContext, run_worker

from .graphs import analyze, design, misc, revise


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


HANDLERS = {
    "noop": _noop,
    "mi.design": design.handle,
    "mi.analyze": analyze.handle,
    "mi.revise": revise.handle,
    "mi.fixscan": misc.handle_fixscan,
    "mi.layout": misc.handle_layout,
    "mi.source_add": misc.handle_source_add,
    "mi.competitor_add": misc.handle_competitor_add,
    "mi.onepager": misc.handle_onepager,
    "mi.export": misc.handle_export,
    "mi.recheck": misc.handle_recheck,
    "mi.import_ca": misc.handle_import_ca,
    "mi.facts_research": misc.handle_facts_research,
}


def main() -> None:
    run_worker("mi", HANDLERS)


if __name__ == "__main__":
    main()
