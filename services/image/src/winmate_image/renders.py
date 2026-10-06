"""렌더 API(§6.9 · §7.9) — birdseye · scenario 전용(화면 없음). 생성 이미지는 이 서비스 한 곳에서만 만든다.

결과는 image · image_version 으로 저장되고 origin.service = 요청 서비스(IMG0 기본 갤러리에는 birdseye 출처가 보이지 않는다).
"""
from __future__ import annotations

from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import not_found
from winmate_common.ids import new_id, now_iso

from . import runs, service, views
from .store import repo


async def render_work(body: dict[str, Any]) -> dict[str, Any]:
    """요청 서비스 · 대상마다 숨은 작업 하나(목록에 나오지 않음)."""
    user = current_user()
    origin = body.get("origin") or {}
    key = f"rw_{origin.get('service')}_{origin.get('ref')}_{user.id}"
    existing = await repo().all("works", where={"owner": user.id, "render_key": key}, limit=1)
    if existing:
        return existing[0]
    kind = "scenario" if body.get("kind") == "scene" else "space"
    wid = new_id("imw")
    doc = {"owner": user.id, "owner_name": user.name, "project_id": body.get("project_id"), "customer_name": None,
           "customer_short": None, "title": body.get("label") or f"{origin.get('service')} 렌더", "title_source": "user",
           "subject_short": None, "kind": kind, "description": (body.get("prompt") or {}).get("subject_ko") or "",
           "conditions": service.default_conditions(kind), "composite": None,
           "origin": {"service": origin.get("service") or "image", "ref": origin.get("ref"), "request_id": None, "label": None},
           "start": "type", "stage": "conditions", "status": "draft", "rev": 1, "internal": True, "render_key": key,
           "selected_image_id": None, "last_export": None, "prefill": None, "deleted_at": None}
    if doc["project_id"]:
        proj = await service.project_info(doc["project_id"])
        if proj and proj.get("customer"):
            doc["customer_name"] = proj["customer"]
    return await repo().put("works", wid, doc)


async def create_render(body: dict[str, Any]) -> dict[str, Any]:
    work = await render_work(body)
    rid = new_id("irn")
    origin = (body.get("origin") or {}).get("service") or "image"
    aspect = body.get("aspect") or "16:9"
    run = await runs.enqueue_run(work=work, kind="render_api", params={"render_id": rid, "aspect": aspect,
                                                                       "style": body.get("style") or "photo"},
                                 n=1, base_image_id=None, labels=[body.get("label") or "렌더"], aspect=aspect, notify=False,
                                 title=body.get("label") or "렌더", origin=origin)
    shots = await runs.shots_of(run["id"])
    doc = {**body, "status": "queued", "job_id": run["job_id"], "run_id": run["id"], "work_id": work["id"],
           "image_id": shots[0]["id"] if shots else None, "version_id": None, "error": None, "owner": work.get("owner"),
           "created_at": now_iso()}
    await repo().put("renders", rid, doc)
    return {"job_id": run["job_id"], "render_id": rid, "status": "queued"}


async def get_render(render_id: str) -> dict[str, Any]:
    r = await repo().get("renders", render_id)
    if r is None:
        raise not_found("렌더", render_id)
    run = await repo().get("runs", r.get("run_id")) or {}
    status = {"queued": "queued", "running": "running", "awaiting_input": "running", "succeeded": "succeeded",
              "failed": "failed", "canceled": "canceled"}.get(run.get("status") or "queued", "queued")
    img = await repo().get("images", r.get("image_id")) or {}
    ver = await repo().get("versions", img.get("current_version_id")) if img.get("current_version_id") else None
    if status == "succeeded" and ver is None:
        status = "failed"
    return {"id": render_id, "status": status, "origin": r.get("origin") or {}, "kind": r.get("kind") or "scene",
            "image_id": img.get("id"), "version_id": (ver or {}).get("id"),
            "renditions": [views.rendition_view(x) for x in (ver or {}).get("renditions") or []],
            "generation": (ver or {}).get("generation") or {}, "qc": (ver or {}).get("qc") or {},
            "error": run.get("error") or (img.get("error") and {"code": "RENDER_FAILED", "message": img.get("error")}),
            "job_id": r.get("job_id"), "created_at": r.get("created_at") or ""}


async def cancel_render(render_id: str) -> dict[str, Any]:
    r = await repo().get("renders", render_id)
    if r is None:
        raise not_found("렌더", render_id)
    if r.get("run_id"):
        await runs.cancel_run(r["run_id"])
    return await get_render(render_id)
