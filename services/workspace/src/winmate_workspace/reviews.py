"""검토 · 승인 — 요청 · 결정 · 검토자별 대상 확인 · 마감일 · 다시 요청(라운드) · 알림.

- `POST /v1/reviews` (마감일 `due_date` 선택) → 검토자에게 `review_requested` 알림
- `POST /v1/reviews/{id}/decision` → 요청자에게 `review_decided`(`decision`) 알림
- `PUT /v1/reviews/{id}/checks/{target_ref}` — 검토자가 대상(시트 등)마다 `ok | need` 확인(PR7C 「확인됨」 점 · 「검토자 2명 중 1명 확인」)
- `POST /v1/reviews/{id}/resubmit` — 변경 요청 뒤 같은 검토를 다시 요청: `round` +1, 결정 · 확인 초기화, 지난 라운드는 `rounds[]` 에 남김
  → 검토자에게 `review_resubmitted` 알림
- 알림의 `item` 은 `item_id`(없으면 target 두 번째 조각 `proposal:<id>:…` 이 색인에 있으면 그것) — 셸 사이드바 그 항목 배지.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from winmate_common.context import current_user
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso

from .db import store
from .notify import item_ref, notify

log = logging.getLogger("winmate.workspace.reviews")
router = APIRouter()

DATE = r"^\d{4}-\d{2}-\d{2}$"


class ReviewBody(BaseModel):
    target: str = Field(description="검토 대상(예: proposal:pr_…:v3)")
    title: str
    route: str = Field(description="검토 화면 웹 경로")
    reviewers: list[str] = Field(min_length=1, description="검토자 user id")
    required_approvals: int = Field(default=1, ge=1)
    message: str | None = None
    due_date: str | None = Field(default=None, pattern=DATE, description="마감일 YYYY-MM-DD(선택) — 「마감 10월 8일 (목)」 · 알림 D-n")
    item_id: str | None = Field(default=None, description="작업물 색인 id(없으면 target 두 번째 조각이 색인에 있으면 그것) — 알림이 붙는 항목")
    version_label: str | None = Field(default=None, max_length=40, description="검토하는 판(예: v3) — 라운드 기록에 남김")


class ReviewDecisionBody(BaseModel):
    decision: Literal["approve", "request_changes"]
    comment: str | None = None


class ReviewerState(BaseModel):
    user_id: str
    name: str = ""
    decision: Literal["pending", "approve", "request_changes"] = "pending"
    comment: str | None = None
    decided_at: str | None = None


class ReviewCheck(BaseModel):
    user_id: str
    name: str = ""
    target_ref: str = Field(description="확인한 대상(예: 시트 id)")
    state: Literal["ok", "need"]
    comment: str | None = None
    round: int = 1
    at: str


class ReviewRound(BaseModel):
    round: int
    message: str | None = None
    version_label: str | None = None
    requested_at: str | None = None
    status: str = Field(description="다시 요청할 때의 상태(changes_requested 등)")
    reviewers: list[ReviewerState] = Field(default_factory=list)
    checks: list[ReviewCheck] = Field(default_factory=list)


class Review(BaseModel):
    id: str
    target: str
    title: str
    route: str
    requester: str
    requester_name: str
    reviewers: list[ReviewerState]
    required_approvals: int
    approvals: int
    status: Literal["pending", "approved", "changes_requested", "canceled"]
    message: str | None = None
    created_at: str
    updated_at: str
    due_date: str | None = None
    item_id: str | None = None
    round: int = 1
    version_label: str | None = None
    requested_at: str | None = Field(default=None, description="이번 라운드 요청 시각")
    checks: list[ReviewCheck] = Field(default_factory=list, description="이번 라운드의 검토자별 대상 확인")
    rounds: list[ReviewRound] = Field(default_factory=list, description="지난 라운드 기록(오래된 것부터)")


class ReviewList(BaseModel):
    items: list[Review]


class ReviewCheckBody(BaseModel):
    state: Literal["ok", "need"]
    comment: str | None = Field(default=None, max_length=2000)


class ResubmitBody(BaseModel):
    message: str | None = None
    version_label: str | None = Field(default=None, max_length=40)
    due_date: str | None = Field(default=None, pattern=DATE, description="새 마감일(없으면 그대로)")


class ReviewPatch(BaseModel):
    title: str | None = None
    message: str | None = None
    due_date: str | None = Field(default=None, pattern=DATE)
    clear_due_date: bool = Field(default=False, description="마감일 지우기")


def _review_status(d: dict[str, Any]) -> dict[str, Any]:
    approvals = sum(1 for r in d["reviewers"] if r["decision"] == "approve")
    d["approvals"] = approvals
    if d.get("status") == "canceled":
        return d
    if any(r["decision"] == "request_changes" for r in d["reviewers"]):
        d["status"] = "changes_requested"
    elif approvals >= d["required_approvals"]:
        d["status"] = "approved"
    else:
        d["status"] = "pending"
    return d


def _name_of(uid: str) -> str:
    p = store().get("users", uid)
    return (p or {}).get("name") or uid


def _get(review_id: str) -> dict[str, Any]:
    d = store().get("reviews", review_id)
    if not d:
        raise not_found("검토", review_id)
    return d


def _item_of(d: dict[str, Any]) -> dict[str, Any] | None:
    _, item = item_ref(d.get("item_id"), target=d.get("target"))
    return item


async def _notify_review(d: dict[str, Any], recipients: list[str], type_: str, title: str, **extra: Any) -> None:
    try:
        await notify([r for r in recipients if r != current_user().id], type=type_, title=title, route=d["route"], ref=d["target"],
                     service="workspace", item=_item_of(d),
                     data={"review_id": d["id"], "round": d.get("round", 1), "due_date": d.get("due_date"), **extra})
    except Exception as exc:  # noqa: BLE001 — 알림 실패가 검토를 막지 않는다
        log.warning("검토 알림 실패 %s: %s", d.get("id"), exc)


@router.post("/reviews", response_model=Review, status_code=201, tags=["reviews"])
async def request_review(body: ReviewBody) -> Review:
    u = current_user()
    rid = new_id("rvw")
    doc, item = item_ref(body.item_id, target=body.target)
    now = now_iso()
    d = {
        "target": body.target, "title": body.title, "route": body.route, "requester": u.id, "requester_name": u.name,
        "reviewers": [{"user_id": r, "name": _name_of(r), "decision": "pending", "comment": None, "decided_at": None} for r in body.reviewers],
        "required_approvals": min(body.required_approvals, len(body.reviewers)), "message": body.message, "status": "pending",
        "due_date": body.due_date, "item_id": (item or {}).get("id"), "round": 1, "version_label": body.version_label,
        "requested_at": now, "checks": [], "rounds": [],
    }
    d = store().put("reviews", rid, _review_status(d))
    await _notify_review(d, body.reviewers, "review_requested", body.title, by=u.name)
    return Review(**d)


@router.get("/reviews", response_model=ReviewList, tags=["reviews"])
async def list_reviews(
    target: str | None = None,
    mine: Literal["to_review", "requested", "all"] = "all",
    status: str | None = None,
    item_id: str | None = Query(None, description="이 작업물의 검토만"),
) -> ReviewList:
    where: dict[str, Any] = {}
    if target:
        where["target"] = target
    if item_id:
        where["item_id"] = item_id
    items, _ = store().list("reviews", where=where or None, limit=500)
    uid = current_user().id
    if mine == "to_review":
        items = [r for r in items if any(x["user_id"] == uid and x["decision"] == "pending" for x in r["reviewers"]) and r["status"] == "pending"]
    elif mine == "requested":
        items = [r for r in items if r["requester"] == uid]
    if status:
        items = [r for r in items if r["status"] == status]
    return ReviewList(items=[Review(**r) for r in items])


@router.get("/reviews/{review_id}", response_model=Review, tags=["reviews"])
async def get_review(review_id: str) -> Review:
    return Review(**_get(review_id))


@router.patch("/reviews/{review_id}", response_model=Review, tags=["reviews"])
async def patch_review(review_id: str, body: ReviewPatch) -> Review:
    d = _get(review_id)
    if d["requester"] != current_user().id:
        raise ApiError(403, "NOT_REQUESTER", "검토를 요청한 사람만 고칠 수 있습니다")
    changes = {k: v for k, v in body.model_dump(exclude={"clear_due_date"}).items() if v is not None}
    if body.clear_due_date:
        changes["due_date"] = None
    d.update(changes)
    return Review(**store().put("reviews", review_id, d))


@router.post("/reviews/{review_id}/decision", response_model=Review, tags=["reviews"])
async def decide(review_id: str, body: ReviewDecisionBody) -> Review:
    d = _get(review_id)
    uid = current_user().id
    for r in d["reviewers"]:
        if r["user_id"] == uid:
            r.update(decision=body.decision, comment=body.comment, decided_at=now_iso())
            break
    else:
        raise ApiError(403, "NOT_A_REVIEWER", "이 검토의 검토자가 아닙니다")
    d = store().put("reviews", review_id, _review_status(d))
    await _notify_review(d, [d["requester"]], "review_decided", d["title"], decision=body.decision, status=d["status"],
                         by=current_user().name)
    return Review(**d)


@router.put("/reviews/{review_id}/checks/{target_ref:path}", response_model=Review, tags=["reviews"])
async def put_check(review_id: str, target_ref: str, body: ReviewCheckBody) -> Review:
    """검토자가 대상(시트 등) 하나를 확인했다(`ok`) · 고칠 게 있다(`need`). 같은 검토자 · 대상이면 바꾼다."""
    d = _get(review_id)
    if d.get("status") == "canceled":
        raise ApiError(409, "REVIEW_CANCELED", "취소된 검토입니다")
    u = current_user()
    if not any(r["user_id"] == u.id for r in d["reviewers"]):
        raise ApiError(403, "NOT_A_REVIEWER", "이 검토의 검토자가 아닙니다")
    checks = [c for c in d.get("checks") or [] if not (c["user_id"] == u.id and c["target_ref"] == target_ref)]
    name = _name_of(u.id)
    checks.append({"user_id": u.id, "name": u.name if name == u.id else name, "target_ref": target_ref,
                   "state": body.state, "comment": body.comment, "round": d.get("round", 1), "at": now_iso()})
    d["checks"] = checks
    return Review(**store().put("reviews", review_id, d))


@router.delete("/reviews/{review_id}/checks/{target_ref:path}", response_model=Review, tags=["reviews"])
async def delete_check(review_id: str, target_ref: str) -> Review:
    """내 확인 지우기."""
    d = _get(review_id)
    uid = current_user().id
    d["checks"] = [c for c in d.get("checks") or [] if not (c["user_id"] == uid and c["target_ref"] == target_ref)]
    return Review(**store().put("reviews", review_id, d))


@router.post("/reviews/{review_id}/resubmit", response_model=Review, tags=["reviews"])
async def resubmit(review_id: str, body: ResubmitBody) -> Review:
    """다시 요청 — 같은 검토의 라운드 +1, 결정 · 확인 초기화(지난 라운드는 rounds[] 에)."""
    d = _get(review_id)
    u = current_user()
    if d["requester"] != u.id:
        raise ApiError(403, "NOT_REQUESTER", "검토를 요청한 사람만 다시 요청할 수 있습니다")
    if d.get("status") == "canceled":
        raise ApiError(409, "REVIEW_CANCELED", "취소된 검토는 다시 요청할 수 없습니다")
    cur_round = int(d.get("round") or 1)
    rounds = list(d.get("rounds") or [])
    rounds.append({"round": cur_round, "message": d.get("message"), "version_label": d.get("version_label"),
                   "requested_at": d.get("requested_at") or d.get("created_at"), "status": d["status"],
                   "reviewers": [dict(r) for r in d["reviewers"]], "checks": list(d.get("checks") or [])})
    d.update(
        rounds=rounds, round=cur_round + 1, checks=[], requested_at=now_iso(), status="pending",
        message=body.message if body.message is not None else d.get("message"),
        version_label=body.version_label if body.version_label is not None else d.get("version_label"),
        due_date=body.due_date or d.get("due_date"),
        reviewers=[{**r, "decision": "pending", "comment": None, "decided_at": None} for r in d["reviewers"]],
    )
    d = store().put("reviews", review_id, _review_status(d))
    await _notify_review(d, [r["user_id"] for r in d["reviewers"]], "review_resubmitted", d["title"], by=u.name,
                         version_label=d.get("version_label"))
    return Review(**d)


@router.post("/reviews/{review_id}/cancel", response_model=Review, tags=["reviews"])
async def cancel_review(review_id: str) -> Review:
    d = _get(review_id)
    d["status"] = "canceled"
    return Review(**store().put("reviews", review_id, d))
