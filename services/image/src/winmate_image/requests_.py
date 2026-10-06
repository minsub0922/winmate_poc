"""다른 기능의 이미지 요청(§6.8) — 공간 시나리오 장면 · 제안서 표지 배경 등.

요청자는 `POST /v1/requests`(서비스 간)로 만들고, 결과는 `GET /v1/requests/{id}` 의 `result_version_id` 로 읽는다.
이미지 서비스는 요청자를 호출하지 않는다.
"""
from __future__ import annotations

from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso

from . import service, views
from .store import repo


def request_view(r: dict[str, Any]) -> dict[str, Any]:
    return {"id": r["id"], "from_service": r.get("from_service") or "", "from_ref": r.get("from_ref") or "",
            "from_label": r.get("from_label") or "", "title": r.get("title") or "", "prefill": r.get("prefill") or {},
            "status": r.get("status") or "open", "work_id": r.get("work_id"), "result_version_id": r.get("result_version_id"),
            "result_image_id": r.get("result_image_id"), "project_id": r.get("project_id"), "created_by": r.get("created_by") or "",
            "created_at": r.get("created_at") or "", "updated_at": r.get("updated_at") or ""}


async def create_request(body: dict[str, Any]) -> dict[str, Any]:
    user = current_user()
    rid = new_id("irq")
    doc = {"from_service": body["from_service"], "from_ref": body["from_ref"], "from_label": body["from_label"],
           "title": body["title"], "prefill": body.get("prefill") or {}, "status": "open", "work_id": None,
           "result_version_id": None, "result_image_id": None, "project_id": body.get("project_id"),
           "created_by": user.id, "owner": user.id, "created_at": now_iso()}
    return await repo().put("requests", rid, doc)


async def list_requests(*, owner: str, statuses: list[str] | None, from_service: str | None, from_ref: str | None) -> list[dict[str, Any]]:
    where: dict[str, Any] = {}
    if from_ref:
        where["from_ref"] = from_ref
    else:
        where["owner"] = owner
    items = await repo().all("requests", where=where, order_by="-created_at")
    out = []
    for r in items:
        if from_service and r.get("from_service") != from_service:
            continue
        if statuses and r.get("status") not in statuses:
            continue
        out.append(r)
    return out


async def get_request(request_id: str) -> dict[str, Any]:
    r = await repo().get("requests", request_id)
    if r is None:
        raise not_found("이미지 요청", request_id)
    return r


async def start_request(request_id: str) -> dict[str, Any]:
    r = await get_request(request_id)
    if r.get("status") in ("fulfilled", "dismissed"):
        raise ApiError(409, "REQUEST_CLOSED", "이미 끝난 요청이에요")
    work = None
    if r.get("work_id"):
        work = await repo().get("works", r["work_id"])
        if work and work.get("deleted_at"):
            work = None
    if work is None:
        work = await service.create_work(kind=(r.get("prefill") or {}).get("kind"), description=None, project_id=r.get("project_id"),
                                         customer_name=None, request_id=request_id, start="type", title=None)
    r = await repo().patch("requests", request_id, {"status": "in_progress", "work_id": work["id"]}) or r
    return {"work_id": work["id"], "route": views.route_type(work["id"]), "conditions_route": views.route_conditions(work["id"]),
            "request": request_view(r)}


async def fulfill_request(request_id: str, version_id: str) -> dict[str, Any]:
    r = await get_request(request_id)
    ver = await repo().get("versions", version_id)
    if ver is None:
        raise not_found("버전", version_id)
    return await repo().patch("requests", request_id, {"status": "fulfilled", "result_version_id": version_id,
                                                       "result_image_id": ver.get("image_id"), "fulfilled_at": now_iso()}) or r


async def dismiss_request(request_id: str) -> dict[str, Any]:
    r = await get_request(request_id)
    return await repo().patch("requests", request_id, {"status": "dismissed"}) or r


async def request_for_work(work_id: str) -> dict[str, Any] | None:
    work = await repo().get("works", work_id)
    rid = ((work or {}).get("origin") or {}).get("request_id")
    return await repo().get("requests", rid) if rid else None
