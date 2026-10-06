"""export 워커 — Redis 큐(wm:q:export) 소비. `python -m winmate_export.worker`.

잡 종류
- export: 느린 내보내기(LibreOffice PDF · 큰 덱 · 큰 ZIP · 옛 형식 고객사 양식 · async=true). payload {export_id}
  → 결과 {export_id, file_id, filename, files, warnings, form_fill?(고객사 양식 — cells 뺀 보고)}
- render: 슬라이드 PNG(LibreOffice · PDF 는 바로). payload {render_id} → 결과 {render_id, pages}
"""
from __future__ import annotations

import asyncio
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.jobs import JobContext, run_worker

from . import service


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


async def export_job(ctx: JobContext) -> dict[str, Any]:
    export_id = ctx.payload.get("export_id")
    st = service.store()
    rec = await asyncio.to_thread(st.get, "exports", export_id)
    if rec is None:
        raise ApiError(404, "NOT_FOUND", f"내보내기를 찾을 수 없습니다: {export_id}")
    if rec.get("status") == "done":
        return {"export_id": export_id, "file_id": (rec.get("file") or {}).get("id"), "files": rec.get("files") or []}
    plan = service.plan_from_record(rec)
    await asyncio.to_thread(st.patch, "exports", export_id, {"status": "running", "job_id": ctx.job.id})
    try:
        result = await service.execute(plan, progress=ctx.progress)
    except Exception as exc:  # noqa: BLE001
        err = service.to_api_error(exc)
        await asyncio.to_thread(st.patch, "exports", export_id, {"status": "failed", "error": {"code": err.code, "message": err.message}})
        raise err from exc
    await asyncio.to_thread(st.patch, "exports", export_id, {"status": "done", **result})
    file = result.get("file") or {}
    out = {"export_id": export_id, "file_id": file.get("id"), "filename": file.get("name"), "files": result["files"],
           "warnings": result.get("warnings", [])[:20]}
    if result.get("form_fill"):   # 고객사 양식 — 칸 목록은 빼고(전체는 GET /v1/exports/{id})
        out["form_fill"] = {k: v for k, v in result["form_fill"].items() if k != "cells"}
    return out


async def render_job(ctx: JobContext) -> dict[str, Any]:
    render_id = ctx.payload.get("render_id")
    st = service.store()
    rec = await asyncio.to_thread(st.get, "renders", render_id)
    if rec is None:
        raise ApiError(404, "NOT_FOUND", f"렌더를 찾을 수 없습니다: {render_id}")
    await asyncio.to_thread(st.patch, "renders", render_id, {"status": "running", "job_id": ctx.job.id})
    try:
        result = await service.execute_render(render_id, rec, progress=ctx.progress)
    except Exception as exc:  # noqa: BLE001
        err = service.to_api_error(exc)
        await asyncio.to_thread(st.patch, "renders", render_id, {"status": "failed", "error": {"code": err.code, "message": err.message}})
        raise err from exc
    await asyncio.to_thread(st.patch, "renders", render_id, {"status": "done", **result})
    return {"render_id": render_id, "pages": result["pages"]}


HANDLERS = {"noop": _noop, "export": export_job, "render": render_job}


def main() -> None:
    run_worker("export", HANDLERS)


if __name__ == "__main__":
    main()
