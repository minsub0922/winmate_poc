"""작업물 알림 — 작업물 색인 항목(예: 제안서)에 붙는 알림. 셸 사이드바 배지 · 사용자 메뉴 알림 목록이 읽는다.

- 기능 서비스: `POST /v1/notifications {item_id, title, route?, type?, message?, ref?}`(internal) — 그 항목 주인(+ recipients)에게.
  예) spec: 넘긴 Spec 시트 값이 바뀌면 `{item_id: <제안서 id>, type: 'spec_link_changed', title, route: '/proposal/{pid}/sections/spec', ref: sp_id}`.
- 검토(reviews.py)도 요청 · 결정 · 다시 요청 때 같은 알림을 만든다.
- 사용자마다 따로 저장(읽음 상태 포함)하고, jobs 알림 흐름(`wm:notify:<user>`)에도 같은 내용을 넣는다(실패해도 무시).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from winmate_common.context import caller_var, current_user
from winmate_common.errors import not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import jobs

from .db import Feature, store

log = logging.getLogger("winmate.workspace.notify")
router = APIRouter()


class NotificationBody(BaseModel):
    item_id: str | None = Field(default=None, description="작업물 색인 id(제안서 id 등) — 그 항목 주인에게 가고 사이드바 그 항목에 배지가 붙는다")
    type: str = Field(default="item_updated", min_length=1, max_length=60, description="알림 종류(예: spec_link_changed)")
    title: str = Field(min_length=1, max_length=200)
    message: str | None = Field(default=None, max_length=1000)
    route: str | None = Field(default=None, description="눌렀을 때 갈 웹 경로(없으면 항목 route)")
    ref: str | None = Field(default=None, description="원인 자원 참조(예: sp_…)")
    service: str | None = Field(default=None, description="보낸 서비스(없으면 호출 서비스)")
    recipients: list[str] = Field(default_factory=list, description="더 받을 사용자 id")
    notify_owner: bool = Field(default=True, description="항목 주인에게도 보내기")
    exclude_actor: bool = Field(default=False, description="지금 사용자(요청한 사람)는 빼기")
    data: dict[str, Any] | None = None


class NotificationItemRef(BaseModel):
    feature: Feature | None = None
    id: str


class Notification(BaseModel):
    id: str
    recipient: str
    type: str
    title: str
    message: str | None = None
    route: str | None = None
    ref: str | None = None
    service: str | None = None
    item: NotificationItemRef | None = None
    by: str | None = None
    by_name: str | None = None
    read: bool = False
    read_at: str | None = None
    data: dict[str, Any] | None = None
    created_at: str


class NotificationList(BaseModel):
    items: list[Notification]
    unread: int = 0
    next_cursor: str | None = None


class ItemUnread(BaseModel):
    item_id: str
    feature: Feature | None = None
    unread: int


class NotificationCounts(BaseModel):
    unread: int
    items: list[ItemUnread]


class ReadBody(BaseModel):
    ids: list[str] | None = Field(default=None, description="이 알림들만")
    item_id: str | None = Field(default=None, description="이 작업물의 알림 전부")


class ReadResult(BaseModel):
    updated: int


def _out(d: dict[str, Any]) -> Notification:
    item = d.get("item")
    return Notification(
        id=d["id"], recipient=d["recipient"], type=d.get("type") or "item_updated", title=d.get("title") or "", message=d.get("message"),
        route=d.get("route"), ref=d.get("ref"), service=d.get("service"), item=NotificationItemRef(**item) if item else None,
        by=d.get("by"), by_name=d.get("by_name"), read=bool(d.get("read")), read_at=d.get("read_at"), data=d.get("data"), created_at=d["created_at"],
    )


def item_ref(item_id: str | None, *, target: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """(색인 항목, {feature, id}) — item_id 가 없으면 대상 참조의 두 번째 조각(`proposal:<id>:…`)이 색인에 있으면 그것."""
    doc = None
    if item_id:
        doc = store().get("items", item_id)
        return doc, {"feature": (doc or {}).get("feature"), "id": item_id}
    if target:
        parts = target.split(":")
        if len(parts) >= 2 and parts[1]:
            doc = store().get("items", parts[1])
            if doc:
                return doc, {"feature": doc.get("feature"), "id": doc["id"]}
    return None, None


async def notify(
    recipients: list[str], *, type: str, title: str, message: str | None = None, route: str | None = None, ref: str | None = None,
    service: str | None = None, item: dict[str, Any] | None = None, data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """사용자마다 알림을 저장하고 jobs 알림 흐름에도 넣는다. 받는 사람이 겹치면 한 번만."""
    u = current_user()
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for rid in recipients:
        if not rid or rid in seen or rid == "system":
            continue
        seen.add(rid)
        doc = {
            "recipient": rid, "type": type, "title": title, "message": message, "route": route, "ref": ref, "service": service,
            "item": item, "item_id": (item or {}).get("id"), "by": u.id, "by_name": u.name, "read": False, "read_at": None, "data": data,
        }
        d = store().put("notifications", new_id("ntf"), doc, keep_history=False)
        out.append(d)
        try:
            await jobs().push_notification(rid, {
                "type": type, "title": title, "message": message, "route": route, "ref": ref, "service": service or "workspace",
                "item": item, "item_id": (item or {}).get("id"), "notification_id": d["id"], "by": u.name, **(data or {}),
            })
        except Exception as exc:  # noqa: BLE001 — 알림 흐름 실패가 본 작업을 막지 않는다
            log.debug("jobs 알림 실패 %s: %s", rid, exc)
    return out


@router.post("/notifications", response_model=NotificationList, status_code=201, tags=["internal"])
async def create_notification(body: NotificationBody) -> NotificationList:
    doc, item = item_ref(body.item_id)
    recipients = list(body.recipients)
    if body.notify_owner and doc and doc.get("owner"):
        recipients.insert(0, doc["owner"])
    if body.exclude_actor:
        recipients = [r for r in recipients if r != current_user().id]
    if body.item_id and not doc and not body.recipients:
        raise not_found("작업물", body.item_id)
    route = body.route or (doc or {}).get("route")
    made = await notify(recipients, type=body.type, title=body.title, message=body.message, route=route, ref=body.ref,
                        service=body.service or caller_var.get(), item=item, data=body.data)
    return NotificationList(items=[_out(d) for d in made], unread=len(made))


def _mine(*, item_id: str | None = None, unread_only: bool = False, limit: int = 500, cursor: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    where: dict[str, Any] = {"recipient": current_user().id}
    if item_id:
        where["item_id"] = item_id
    if unread_only:
        where["read"] = False
    return store().list("notifications", where=where, order_by="-created_at", limit=limit, cursor=cursor)


@router.get("/notifications", response_model=NotificationList, tags=["notifications"])
async def list_notifications(
    unread_only: bool = Query(False, description="읽지 않은 것만"),
    item_id: str | None = Query(None, description="이 작업물의 알림만"),
    limit: int = Query(30, ge=1, le=200),
    cursor: str | None = None,
) -> NotificationList:
    items, nxt = _mine(item_id=item_id, unread_only=unread_only, limit=limit, cursor=cursor)
    unread = store().count("notifications", where={"recipient": current_user().id, "read": False})
    return NotificationList(items=[_out(d) for d in items], unread=unread, next_cursor=nxt)


@router.get("/notifications/counts", response_model=NotificationCounts, tags=["notifications"])
async def notification_counts() -> NotificationCounts:
    """읽지 않은 알림 수 — 전체 · 작업물별(사이드바 배지)."""
    items, _ = _mine(unread_only=True, limit=1000)
    per: dict[str, ItemUnread] = {}
    for d in items:
        it = d.get("item") or {}
        iid = it.get("id")
        if not iid:
            continue
        cur = per.get(iid) or ItemUnread(item_id=iid, feature=it.get("feature"), unread=0)
        cur.unread += 1
        per[iid] = cur
    return NotificationCounts(unread=len(items), items=list(per.values()))


@router.post("/notifications/read", response_model=ReadResult, tags=["notifications"])
async def mark_read(body: ReadBody) -> ReadResult:
    """읽음 표시 — ids · item_id 가 없으면 내 알림 전부."""
    items, _ = _mine(item_id=body.item_id, unread_only=True, limit=1000)
    if body.ids is not None:
        want = set(body.ids)
        items = [d for d in items if d["id"] in want]
    at = now_iso()
    for d in items:
        store().patch("notifications", d["id"], {"read": True, "read_at": at}, keep_history=False)
    return ReadResult(updated=len(items))
