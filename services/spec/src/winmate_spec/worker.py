"""spec 워커 — Redis 큐(wm:q:spec) 소비. `python -m winmate_spec.worker`.

잡 종류(06-spec §7)
- spec_generate   {sheet_id, mode: full|rerender|columns, product_ids?, auto_answer?}  시트 생성(5단계)
- spec_find       {sheet_id, text}                    조건 문장 해석 → 후보
- spec_compliance {sheet_id, doc_id, file_id, note?} · {sheet_id, reevaluate: true}   요구 규격서 → 대응표
- spec_datasheet  {sheet_id, datasheet_id}             데이터시트로 빈 칸 채우기 · 대조
- spec_revise     {sheet_id, text, context, session_id?}  말로 수정
- spec_template   {sheet_id, template_id}              고객사 양식 맞추기
- spec_recheck    {sheet_id} · {all: true, owner?, reschedule?}  재확인(카탈로그 · 생애주기 · 연결 · 요구)
- spec_export     {sheet_id, export_id}                XLSX · PDF · PPTX
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.jobs import JobCanceled, JobContext, run_worker

from . import ops, repo
from . import sheet as S
from .graphs import build_compliance, build_datasheet, build_export, build_find, build_generate, build_recheck, build_template
from .graphs.revise import build_revise

log = logging.getLogger("winmate.spec.worker")


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


async def _clear_job(sid: str, job_id: str, **extra: Any) -> None:
    def fn(s: dict[str, Any]) -> None:
        if (s.get("active_job") or {}).get("id") == job_id:
            s["active_job"] = None
        for k, v in extra.items():
            if k == "finder_status" and s.get("finder"):
                s["finder"]["status"] = v
                s["finder"]["error"] = extra.get("error")
            elif k == "compliance_status" and s.get("compliance"):
                s["compliance"]["status"] = v
                s["compliance"]["error"] = extra.get("error")
            elif k not in ("error",):
                s[k] = v
        S.refresh_status(s, s["id"])

    try:
        saved, _ = await repo.amutate("sheets", sid, fn)
        await ops.publish(saved)
    except ApiError:
        pass


def _msg(exc: Exception) -> str:
    return getattr(exc, "message", None) or str(exc) or type(exc).__name__


async def spec_generate(ctx: JobContext) -> dict[str, Any]:
    p = ctx.payload
    sid = p["sheet_id"]
    try:
        final = await run_graph(ctx, build_generate(), {"sheet_id": sid, "mode": p.get("mode") or "full", "product_ids": p.get("product_ids"),
                                                         "auto_answer": bool(p.get("auto_answer")), "notes": {}})
    except JobCanceled:
        def cancel(s: dict[str, Any]) -> None:
            ops.restore_backup(s)
            s.pop("gen", None)
            s.pop("gen_auto_defer", None)
            s["pending_answers"] = None
            s["step"] = 2
            s["active_job"] = None
            S.refresh_status(s, s["id"])

        saved, _ = await repo.amutate("sheets", sid, cancel)
        await ops.publish(saved)
        raise
    except Exception as exc:
        def fail(s: dict[str, Any]) -> None:
            ops.restore_backup(s)
            s.pop("gen", None)
            s.pop("gen_auto_defer", None)
            s["pending_answers"] = None
            s["last_error"] = _msg(exc)
            if (s.get("active_job") or {}).get("id") == ctx.job.id:
                s["active_job"] = None
            S.refresh_status(s, s["id"])

        try:
            saved, _ = await repo.amutate("sheets", sid, fail)
            await ops.publish(saved)
        except ApiError:
            pass
        raise
    return (final or {}).get("result") or {"sheet_id": sid}


async def spec_find(ctx: JobContext) -> dict[str, Any]:
    p = ctx.payload
    try:
        final = await run_graph(ctx, build_find(), {"sheet_id": p["sheet_id"], "text": p["text"]})
    except Exception as exc:
        await _clear_job(p["sheet_id"], ctx.job.id, finder_status="failed", error=_msg(exc))
        raise
    return (final or {}).get("result") or {}


async def spec_compliance(ctx: JobContext) -> dict[str, Any]:
    p = ctx.payload
    try:
        final = await run_graph(ctx, build_compliance(), {"sheet_id": p["sheet_id"], "doc_id": p.get("doc_id"), "file_id": p.get("file_id"),
                                                           "note": p.get("note"), "reevaluate": bool(p.get("reevaluate"))})
    except Exception as exc:
        await _clear_job(p["sheet_id"], ctx.job.id, compliance_status="failed", error=_msg(exc))
        raise
    return (final or {}).get("result") or {}


async def spec_datasheet(ctx: JobContext) -> dict[str, Any]:
    p = ctx.payload
    try:
        final = await run_graph(ctx, build_datasheet(), {"sheet_id": p["sheet_id"], "ref": p["datasheet_id"]})
    except Exception as exc:
        def fail(s: dict[str, Any]) -> None:
            for d in s.get("datasheets") or []:
                if d["id"] == p["datasheet_id"]:
                    d["status"] = "failed"
                    d["error"] = _msg(exc)

        try:
            await repo.amutate("sheets", p["sheet_id"], fail)
        except ApiError:
            pass
        raise
    return (final or {}).get("result") or {}


async def spec_revise(ctx: JobContext) -> dict[str, Any]:
    p = ctx.payload
    try:
        final = await run_graph(ctx, build_revise(), {"sheet_id": p["sheet_id"], "text": p["text"], "context": p.get("context") or "result",
                                                       "session_id": p.get("session_id")})
    except Exception:
        await _clear_job(p["sheet_id"], ctx.job.id)
        raise
    return (final or {}).get("result") or {}


async def spec_template(ctx: JobContext) -> dict[str, Any]:
    p = ctx.payload
    try:
        final = await run_graph(ctx, build_template(), {"sheet_id": p["sheet_id"], "ref": p["template_id"]})
    except Exception as exc:
        def fail(s: dict[str, Any]) -> None:
            if (s.get("template") or {}).get("id") == p["template_id"]:
                s["template"]["status"] = "failed"
                s["template"]["error"] = _msg(exc)

        try:
            await repo.amutate("sheets", p["sheet_id"], fail)
        except ApiError:
            pass
        raise
    return (final or {}).get("result") or {}


async def spec_recheck(ctx: JobContext) -> dict[str, Any]:
    p = ctx.payload
    final = await run_graph(ctx, build_recheck(), {"sheet_id": p.get("sheet_id"), "all": bool(p.get("all")), "owner": p.get("owner")})
    if p.get("reschedule"):
        from .api_support import ensure_daily_schedule
        await ensure_daily_schedule(force=True)
    return (final or {}).get("result") or {}


async def spec_export(ctx: JobContext) -> dict[str, Any]:
    p = ctx.payload
    final = await run_graph(ctx, build_export(), {"sheet_id": p["sheet_id"], "ref": p["export_id"]})
    return (final or {}).get("result") or {}


HANDLERS = {"noop": _noop, "spec_generate": spec_generate, "spec_find": spec_find, "spec_compliance": spec_compliance,
            "spec_datasheet": spec_datasheet, "spec_revise": spec_revise, "spec_template": spec_template, "spec_recheck": spec_recheck,
            "spec_export": spec_export}


def main() -> None:
    run_worker("spec", HANDLERS)


if __name__ == "__main__":
    main()
