"""birdseye 워커 — Redis 큐(wm:q:birdseye) 소비. `python -m winmate_birdseye.worker`.

잡 종류 → LangGraph(run_graph: thread_id = job_id, 노드 경계 취소 확인 · step 이벤트):
  space_analyze · plan_recognize · photo_recognize · space_nl_edit · furniture_recommend · layout_generate · layout_nl_edit ·
  render_cut · result_edit · zones_auto · zones_rewrite · export
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.graph import run_graph
from winmate_common.jobs import JobCanceled, JobContext, run_worker

log = logging.getLogger("winmate.birdseye.worker")


class OneState(TypedDict, total=False):
    payload: dict[str, Any]
    result: dict[str, Any]


def one(name: str, fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any] | None]]) -> StateGraph:
    """노드 하나짜리 그래프(짧은 일도 같은 길 — step 이벤트 · 취소 · 체크포인트)."""
    g = StateGraph(OneState)

    async def node(state: OneState) -> dict[str, Any]:
        return {"result": (await fn(state.get("payload") or {})) or {}}

    g.add_node(name, node)
    g.add_edge(START, name)
    g.add_edge(name, END)
    return g


def _msg(exc: Exception) -> str:
    return str(getattr(exc, "message", None) or exc) or type(exc).__name__


async def _space_analyze(ctx: JobContext) -> dict[str, Any] | None:
    from . import inputs

    be_id = ctx.payload["birdseye_id"]
    try:
        final = await run_graph(ctx, inputs.space_graph(), {"birdseye_id": be_id},
                                step_labels={"load_inputs": "입력 불러오기", "parse_description": "설명 해석", "merge": "공간 모델",
                                             "capability_hints": "역량 힌트", "save": "저장"})
    except Exception:
        from .repo import repo

        await repo().patch("birdseyes", be_id, {"analyzing_job_id": None})
        raise
    if final is None:
        return None
    return {"birdseye_id": be_id, "version": final.get("version"), "route": f"/birdseye/{be_id}/products"}


async def _plan_recognize(ctx: JobContext) -> dict[str, Any] | None:
    from . import inputs

    pid = ctx.payload["plan_id"]
    be_id = ctx.payload["birdseye_id"]
    try:
        final = await run_graph(ctx, inputs.plan_graph(), {"plan_id": pid, "birdseye_id": be_id},
                                step_labels={"fetch": "도면 불러오기", "i2t": "요소 읽기", "geometry": "벽 · 치수", "model": "정리"})
    except JobCanceled:
        await inputs.plan_failed(pid, "인식을 멈췄어요")
        raise
    except Exception as exc:
        await inputs.plan_failed(pid, f"도면을 읽지 못했어요. {_msg(exc)}")
        raise
    if final is None:
        return None
    return {"plan_id": pid, "route": f"/birdseye/{be_id}/space/plan?plan={pid}"}


async def _photo_recognize(ctx: JobContext) -> dict[str, Any] | None:
    from . import inputs

    phid = ctx.payload["photo_id"]
    try:
        final = await run_graph(ctx, inputs.photo_graph(), {"photo_id": phid, "birdseye_id": ctx.payload["birdseye_id"]},
                                step_labels={"quality": "밝기 확인", "i2t": "벽 · 요소 찾기", "save": "저장"})
    except JobCanceled:
        raise
    except Exception as exc:
        await inputs.photo_failed(phid, _msg(exc))
        raise
    if final is None:
        return None
    return {"photo_id": phid}


async def _space_nl_edit(ctx: JobContext) -> dict[str, Any] | None:
    from . import inputs

    async def run(p: dict[str, Any]) -> dict[str, Any]:
        return await inputs.space_nl_edit(p["birdseye_id"], p["text"])

    final = await run_graph(ctx, one("space_ops", run), {"payload": dict(ctx.payload)})
    return (final or {}).get("result")


async def _furniture_recommend(ctx: JobContext) -> dict[str, Any] | None:
    from . import furniture as F
    from .repo import repo

    async def run(p: dict[str, Any]) -> dict[str, Any]:
        recs = await F.recommend(p["birdseye_id"], list(p.get("exclude") or []))
        return {"shown": recs.get("shown"), "path": recs.get("path")}

    try:
        final = await run_graph(ctx, one("recommend", run), {"payload": dict(ctx.payload)}, step_labels={"recommend": "가구 추천"})
    finally:
        await repo().patch("birdseyes", ctx.payload["birdseye_id"], {"furniture_job_id": None})
    res = (final or {}).get("result") or {}
    return {**res, "route": f"/birdseye/{ctx.payload['birdseye_id']}/furniture"}


async def _layout_generate(ctx: JobContext) -> dict[str, Any] | None:
    from . import layouts as L
    from .repo import repo

    async def run(p: dict[str, Any]) -> dict[str, Any]:
        lay = await L.generate_layout(p["birdseye_id"], none=bool(p.get("none")))
        return {"layout_version": lay["version"], "warnings": sum(1 for w in lay.get("warnings", []) if w.get("status") == "open")}

    try:
        final = await run_graph(ctx, one("layout", run), {"payload": dict(ctx.payload)}, step_labels={"layout": "배치안"})
    finally:
        await repo().patch("birdseyes", ctx.payload["birdseye_id"], {"layout_job_id": None})
    res = (final or {}).get("result") or {}
    return {**res, "route": f"/birdseye/{ctx.payload['birdseye_id']}/layout"}


async def _layout_nl_edit(ctx: JobContext) -> dict[str, Any] | None:
    from . import layouts as L

    async def run(p: dict[str, Any]) -> dict[str, Any]:
        return await L.nl_edit(p["birdseye_id"], p["text"], p.get("session_id"))

    final = await run_graph(ctx, one("layout_ops", run), {"payload": dict(ctx.payload)}, step_labels={"layout_ops": "배치 수정"})
    return (final or {}).get("result")


async def _render_cut(ctx: JobContext) -> dict[str, Any] | None:
    from . import cuts as C
    from . import render as R
    from . import service as svc

    cut_id = ctx.payload["cut_id"]
    be_id = ctx.payload["birdseye_id"]
    try:
        final = await run_graph(ctx, R.build(), {"cut_id": cut_id, "birdseye_id": be_id}, step_labels=R.LABELS)
    except JobCanceled:
        await R.on_cancel(cut_id)
        raise
    except Exception as exc:
        await R.on_fail(cut_id, _msg(exc))
        raise
    finally:
        try:
            await C.pump(be_id)
            await svc.index(be_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("컷 대기열 이어 넣기 실패: %s", exc)
    if final is None:
        return None
    c = await C.get_cut(cut_id)
    return {"cut_id": cut_id, "status": c.get("status"), "version_id": c.get("version_id"),
            "route": f"/birdseye/{be_id}/result?cut={cut_id}"}


async def _result_edit(ctx: JobContext) -> dict[str, Any] | None:
    from . import edits
    from .repo import repo

    async def run(p: dict[str, Any]) -> dict[str, Any]:
        return await edits.run_render_edit(p)

    try:
        final = await run_graph(ctx, one("render_edit", run), {"payload": dict(ctx.payload)}, step_labels={"render_edit": "수정 렌더"})
    except Exception:
        await repo().patch("cuts", ctx.payload["cut_id"], {"edit_job_id": None})
        raise
    return {**((final or {}).get("result") or {}), "route": f"/birdseye/{ctx.payload['birdseye_id']}/result?cut={ctx.payload['cut_id']}"}


async def _zones_auto(ctx: JobContext) -> dict[str, Any] | None:
    from . import zones as Z
    from .repo import repo

    async def run(p: dict[str, Any]) -> dict[str, Any]:
        v = await Z.auto(p["birdseye_id"], p.get("cut_id"))
        return {"count": len(v["points"]), "suggestions": len(v["suggestions"])}

    try:
        final = await run_graph(ctx, one("zones", run), {"payload": dict(ctx.payload)}, step_labels={"zones": "존 포인트"})
    finally:
        await repo().patch("birdseyes", ctx.payload["birdseye_id"], {"zones_job_id": None})
    return {**((final or {}).get("result") or {}), "route": f"/birdseye/{ctx.payload['birdseye_id']}/zones"}


async def _zones_rewrite(ctx: JobContext) -> dict[str, Any] | None:
    from . import zones as Z

    async def run(p: dict[str, Any]) -> dict[str, Any]:
        return {"rewritten": await Z.rewrite(p["birdseye_id"], p["text"], p.get("zone_ids"))}

    final = await run_graph(ctx, one("rewrite", run), {"payload": dict(ctx.payload)}, step_labels={"rewrite": "문구 다듬기"})
    return (final or {}).get("result")


async def _export(ctx: JobContext) -> dict[str, Any] | None:
    from . import exporting as X
    from .repo import repo

    async def run(p: dict[str, Any]) -> dict[str, Any]:
        return await X.run_export(p["export_id"], progress=ctx.progress)

    try:
        final = await run_graph(ctx, one("export", run), {"payload": dict(ctx.payload)}, step_labels={"export": "내보내기"})
    except Exception as exc:
        await repo().patch("exports", ctx.payload["export_id"], {"status": "failed", "error": _msg(exc)})
        raise
    return (final or {}).get("result")


async def _noop(ctx: JobContext) -> dict[str, Any]:
    await ctx.progress(100, "완료")
    return {"ok": True}


HANDLERS = {
    "space_analyze": _space_analyze,
    "plan_recognize": _plan_recognize,
    "photo_recognize": _photo_recognize,
    "space_nl_edit": _space_nl_edit,
    "furniture_recommend": _furniture_recommend,
    "layout_generate": _layout_generate,
    "layout_nl_edit": _layout_nl_edit,
    "render_cut": _render_cut,
    "result_edit": _result_edit,
    "zones_auto": _zones_auto,
    "zones_rewrite": _zones_rewrite,
    "export": _export,
    "noop": _noop,
}


def main() -> None:
    run_worker("birdseye", HANDLERS)


if __name__ == "__main__":
    main()
