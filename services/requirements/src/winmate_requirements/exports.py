"""정의서 내보내기(§6.9, 제안) — export 서비스로 DOCX · PDF. 제작자 의견 · 내부 메모는 항상 뺀다.

잡 `rq.export` → export `POST /v1/exports {format, document}`(201 바로 · 202 면 기다림) → 결과 file_id.
"""
from __future__ import annotations

import asyncio
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import JobContext, jobs

from . import domain, repo, service


async def create(rq_id: str, fmt: str, version: int | None) -> dict[str, Any]:
    doc = await repo.require_doc(rq_id)
    n = version or doc.get("saved_version", 0)
    if n < 1:
        raise ApiError(422, "VERSION_NOT_FOUND", "저장된 버전이 있어야 내보낼 수 있어요")
    await service.get_version(rq_id, n)
    eid, job_id = new_id("rqx"), new_id("job")
    now = now_iso()
    rec = {"id": eid, "requirement_id": rq_id, "format": fmt, "version": n, "status": "queued", "file_id": None,
           "file_name": None, "job_id": job_id, "error": None, "created_at": now, "updated_at": now}
    await repo.put("exports", eid, rec)
    await jobs().enqueue("requirements", "rq.export", {"requirement_id": rq_id, "export_id": eid},
                         title=f"{domain.title_of(doc) or '요구사항'} · 정의서 내보내기", ref=rq_id,
                         project_id=doc.get("project_id"), job_id=job_id)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "export", "id": eid}}


async def get(rq_id: str, export_id: str) -> dict[str, Any]:
    rec = await repo.get("exports", export_id)
    if rec is None or rec.get("requirement_id") != rq_id:
        raise repo.not_found("내보내기", export_id)
    return rec


def report(v: dict[str, Any]) -> dict[str, Any]:
    """고객용 보고서 문서(제작자 의견 · 가중치 근거 메모 제외)."""
    snap = v["snapshot"]
    form = snap["form"]
    ks = snap.get("keymen") or []
    items = {i["id"]: i for i in snap.get("items_flat") or []}
    sections: list[dict[str, Any]] = [{
        "heading": "개요",
        "table": {"columns": ["항목", "내용"], "rows": [
            ["프로젝트명", (form.get("project_name") or {}).get("value") or "—"],
            ["고객사", (form.get("customer_name") or {}).get("value") or "—"],
            ["최종 제안대상", (form.get("final_audience") or {}).get("value") or "—"],
        ]},
    }]
    for k in ks:
        head = k["name"] + (f" ({k['weight']}%)" if len(ks) > 1 and k.get("weight") is not None else "")
        numbered = []
        for iid in k.get("item_ids") or []:
            it = items.get(iid)
            if it:
                numbered.append(f"{it['code']} {it['text']}" + (" [확인 필요]" if it.get("needs_confirmation") else ""))
        sections.append({"heading": head, "numbered": numbered or ["—"]})
    open_q = [q for q in snap.get("customer_questions") or [] if q.get("status") == "open"]
    if open_q:
        sections.append({"heading": "확인이 필요한 것", "bullets": [q["text"] for q in open_q]})
    return {"title": v.get("title") or "요구사항 정의서", "subtitle": f"요구사항 정의서 v{v['version']}",
            "meta": {"버전": f"v{v['version']}", "저장": (v.get("created_at") or "")[:10]}, "sections": sections}


async def handle_export(ctx: JobContext) -> dict[str, Any]:
    rq_id, eid = ctx.payload["requirement_id"], ctx.payload["export_id"]
    rec = await repo.get("exports", eid)
    if rec is None:
        raise ApiError(404, "NOT_FOUND", "내보내기를 찾을 수 없어요")
    rec.update({"status": "running", "updated_at": now_iso()})
    await repo.put("exports", eid, rec)
    try:
        v = await service.get_version(rq_id, rec["version"])
        doc = await repo.require_doc(rq_id)
        body = {"format": rec["format"], "document": report(v), "filename": f"{v.get('title') or '요구사항 정의서'}_v{v['version']}",
                "confidential": True, "project_id": doc.get("project_id"), "source_ref": f"requirements:{rq_id}"}
        res = await ServiceClient("export", timeout=300).post("/v1/exports", json=body)
        await ctx.progress(60, "파일 만드는 중")
        for _ in range(300):
            if res.get("status") == "done" and res.get("file"):
                break
            if res.get("status") == "failed":
                raise ApiError(502, "EXPORT_FAILED", "파일을 만들지 못했어요")
            await asyncio.sleep(1.0)
            res = await ServiceClient("export").get(f"/v1/exports/{res['export_id']}")
        f = res.get("file") or {}
        rec.update({"status": "done", "file_id": f.get("id"), "file_name": f.get("name"), "updated_at": now_iso()})
        await repo.put("exports", eid, rec)
        return {"export_id": eid, "file_id": f.get("id"), "filename": f.get("name")}
    except BaseException as exc:
        rec.update({"status": "failed", "error": {"code": getattr(exc, "code", "EXPORT_FAILED"),
                                                   "message": getattr(exc, "message", None) or "파일을 만들지 못했어요"},
                    "updated_at": now_iso()})
        await repo.put("exports", eid, rec)
        raise
