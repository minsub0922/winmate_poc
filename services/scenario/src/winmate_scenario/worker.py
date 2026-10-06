"""scenario 워커 — Redis 큐(wm:q:scenario) 소비. `python -m winmate_scenario.worker`.

잡 종류(09-scenario §7) — 모두 LangGraph(`run_graph`, thread_id = job_id):
sc.parse_input · sc.skeleton · sc.timeline_edit · sc.lane_rewrite · sc.recommend · sc.generate · sc.rewrite_scene · sc.edit ·
sc.shorten · sc.images_batch · sc.export
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from langgraph.graph import StateGraph
from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.jobs import JobCanceled, JobContext, run_worker

from . import graphs, repo, service

log = logging.getLogger("winmate.scenario.worker")

LABELS = {
    "regex_split": "줄 나누기", "llm_json": "타임라인 나누기", "validate": "확인", "save": "저장",
    "load": "불러오기", "split_scenes": "장면 나누기", "write_scene": "장면별 이야기 쓰기", "link": "솔루션 동작 · 제품 연결",
    "mark_confirm": "확인 필요 표시", "finalize": "마무리", "match": "장면별 추천", "evidence": "근거 확인",
}


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


def _handler(build: Callable[[], StateGraph], *, on_fail: Callable[[str, Exception], Any] | None = None) -> Callable[[JobContext], Any]:
    async def run(ctx: JobContext) -> dict[str, Any]:
        sc_id = ctx.payload["scenario_id"]
        init: dict[str, Any] = {"scenario_id": sc_id, "payload": dict(ctx.payload)}
        try:
            final = await run_graph(ctx, build(), init, recursion_limit=200, step_labels=LABELS)
        except JobCanceled:
            if on_fail is not None:
                await on_fail(sc_id, JobCanceled())
            raise
        except Exception as exc:
            if on_fail is not None:
                try:
                    await on_fail(sc_id, exc)
                except Exception:
                    log.exception("실패 정리 실패 %s", sc_id)
            raise
        finally:
            await service.clear_active(sc_id, ctx.job.id)
        out: dict[str, Any] = {"ref": {"kind": "scenario", "id": sc_id}}
        if final and final.get("result"):
            out.update(final["result"])
        return out

    return run


async def _gen_fail(sc_id: str, exc: Exception) -> None:
    if isinstance(exc, JobCanceled):
        await graphs.mark_generation_stopped(sc_id, canceled=True)
        return
    msg = exc.message if isinstance(exc, ApiError) else "잠시 후 다시 시도해 주세요."
    await graphs.mark_generation_stopped(sc_id, failed_reason=msg)


async def _parse_fail(sc_id: str, exc: Exception) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.set_active(d, None)
        return d
    try:
        await repo.update(sc_id, fn)
    except ApiError:
        pass


async def _recommend_fail(sc_id: str, exc: Exception) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        rec = d.get("recommendation") or {}
        rec["status"] = "failed"
        d["recommendation"] = rec
        service.set_active(d, None)
        return d
    try:
        await repo.update(sc_id, fn)
    except ApiError:
        pass


async def _images_fail(sc_id: str, exc: Exception) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["images_job"] = None
        for s in d.get("scenes") or []:
            if (s.get("image_job") or {}).get("status") in ("queued", "running"):
                s["image_job"] = {"status": "failed", "error": "이미지를 만들지 못했어요"}
        service.set_active(d, None)
        return d
    try:
        await repo.update(sc_id, fn)
    except ApiError:
        pass


async def _skeleton(ctx: JobContext) -> dict[str, Any]:
    build = graphs.build_skeleton_birdseye if ctx.payload.get("mode") == "birdseye" else graphs.build_skeleton_template
    return await _handler(build, on_fail=_parse_fail)(ctx)


HANDLERS = {
    "noop": _noop,
    "sc.parse_input": _handler(graphs.build_parse, on_fail=_parse_fail),
    "sc.skeleton": _skeleton,
    "sc.timeline_edit": _handler(graphs.build_timeline_edit, on_fail=_parse_fail),
    "sc.lane_rewrite": _handler(graphs.build_lane_rewrite, on_fail=_parse_fail),
    "sc.recommend": _handler(graphs.build_recommend, on_fail=_recommend_fail),
    "sc.generate": _handler(graphs.build_generate, on_fail=_gen_fail),
    "sc.rewrite_scene": _handler(graphs.build_rewrite),
    "sc.edit": _handler(graphs.build_edit),
    "sc.shorten": _handler(graphs.build_shorten),
    "sc.images_batch": _handler(graphs.build_images, on_fail=_images_fail),
    "sc.export": _handler(graphs.build_export),
}


def main() -> None:
    run_worker("scenario", HANDLERS)


if __name__ == "__main__":
    main()
