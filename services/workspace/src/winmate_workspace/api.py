"""workspace API — 사용자 · 프로젝트 · 작업물 색인 · 코멘트 · 검토/승인 · 공유 링크 · 자산 사용 이력 · 작업물 알림.

- 작업물 색인(items)은 기능 서비스가 자원을 만들거나 바꿀 때 올린다(PUT, internal). 홈 최근 작업과 사이드바 이력이 읽는다.
- 사용자 · 로그인 확인 · 관리자 계정: users.py(AUTH_MODE=none 은 개발 사용자 자동 프로필, local 은 /v1/auth/verify).
- 검토/승인(마감일 · 대상 확인 · 다시 요청 라운드): reviews.py · 작업물 알림(사이드바 배지): notify.py.
"""
from __future__ import annotations

import hashlib
import secrets
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from winmate_common.context import current_user
from winmate_common.errors import not_found
from winmate_common.ids import new_id

from . import notify, reviews, users
from .db import FEATURES, Feature, store
from .users import bootstrap_admin, hash_password, verify_password

router = APIRouter(prefix="/v1")
router.include_router(users.router)

__all__ = ["router", "store", "bootstrap_admin", "hash_password", "verify_password", "FEATURES", "Feature"]


# ── 프로젝트 ─────────────────────────────────────────────

class ProjectBody(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    customer: str | None = None
    industry: str | None = None
    note: str | None = None


class Project(ProjectBody):
    id: str
    owner: str
    created_at: str
    updated_at: str


class ProjectList(BaseModel):
    items: list[Project]
    next_cursor: str | None = None


@router.post("/projects", response_model=Project, status_code=201, tags=["projects"])
async def create_project(body: ProjectBody) -> Project:
    pid = new_id("prj")
    d = store().put("projects", pid, {**body.model_dump(), "owner": current_user().id})
    return Project(**d)


@router.get("/projects", response_model=ProjectList, tags=["projects"])
async def list_projects(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> ProjectList:
    items, nxt = store().list("projects", limit=limit, cursor=cursor)
    return ProjectList(items=[Project(**i) for i in items], next_cursor=nxt)


@router.get("/projects/{project_id}", response_model=Project, tags=["projects"])
async def get_project(project_id: str) -> Project:
    d = store().get("projects", project_id)
    if not d:
        raise not_found("프로젝트", project_id)
    return Project(**d)


@router.patch("/projects/{project_id}", response_model=Project, tags=["projects"])
async def patch_project(project_id: str, body: ProjectBody) -> Project:
    if not store().get("projects", project_id):
        raise not_found("프로젝트", project_id)
    return Project(**store().patch("projects", project_id, body.model_dump(exclude_unset=True)))


# ── 작업물 색인 ──────────────────────────────────────────

class ItemBody(BaseModel):
    feature: Feature
    title: str = Field(min_length=1, max_length=200)
    status: str = Field(description="기능별 상태(draft · generating · done · …)")
    route: str = Field(description="웹 경로(예: /requirements/rq_…)")
    summary: str | None = None
    project_id: str | None = None
    meta: dict[str, Any] | None = None


class Item(BaseModel):
    item_id: str
    feature: Feature
    title: str
    status: str
    route: str
    summary: str | None = None
    project_id: str | None = None
    meta: dict[str, Any] | None = None
    owner: str
    owner_name: str = ""
    created_at: str
    updated_at: str


class ItemList(BaseModel):
    items: list[Item]
    next_cursor: str | None = None


class FeatureCount(BaseModel):
    feature: Feature
    count: int


class ItemCounts(BaseModel):
    items: list[FeatureCount]


def _item_out(d: dict[str, Any]) -> Item:
    return Item(item_id=d["id"], **{k: d.get(k) for k in ("feature", "title", "status", "route", "summary", "project_id", "meta")},
                owner=d.get("owner") or "system", owner_name=d.get("owner_name") or "", created_at=d["created_at"], updated_at=d["updated_at"])


@router.put("/items/{item_id}", response_model=Item, tags=["internal"])
async def upsert_item(item_id: str, body: ItemBody) -> Item:
    cur = store().get("items", item_id)
    u = current_user()
    owner = (cur or {}).get("owner") or u.id
    owner_name = (cur or {}).get("owner_name") or u.name
    d = store().put("items", item_id, {**body.model_dump(), "owner": owner, "owner_name": owner_name}, keep_history=False)
    return _item_out(d)


@router.delete("/items/{item_id}", status_code=204, tags=["internal"])
async def delete_item(item_id: str) -> None:
    store().delete("items", item_id)


@router.get("/items", response_model=ItemList, tags=["items"])
async def list_items(
    feature: Feature | None = None,
    project_id: str | None = None,
    owner: str = Query("me", description="me | all | <user id>"),
    q: str | None = Query(None, description="제목 포함 검색"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> ItemList:
    where: dict[str, Any] = {}
    if feature:
        where["feature"] = feature
    if project_id:
        where["project_id"] = project_id
    if owner != "all":
        where["owner"] = current_user().id if owner == "me" else owner
    if q:
        items, _ = store().list("items", where=where, limit=500)
        items = [i for i in items if q.lower() in (i.get("title") or "").lower()]
        return ItemList(items=[_item_out(i) for i in items[:limit]])
    items, nxt = store().list("items", where=where, limit=limit, cursor=cursor)
    return ItemList(items=[_item_out(i) for i in items], next_cursor=nxt)


@router.get("/items/counts", response_model=ItemCounts, tags=["items"])
async def item_counts(owner: str = Query("me")) -> ItemCounts:
    who = current_user().id if owner == "me" else owner
    out = []
    for f in FEATURES:
        where: dict[str, Any] = {"feature": f}
        if owner != "all":
            where["owner"] = who
        out.append(FeatureCount(feature=f, count=store().count("items", where=where)))  # type: ignore[arg-type]
    return ItemCounts(items=out)


@router.get("/items/{item_id}", response_model=Item, tags=["items"])
async def get_item(item_id: str) -> Item:
    d = store().get("items", item_id)
    if not d:
        raise not_found("작업물", item_id)
    return _item_out(d)


# ── 코멘트 ───────────────────────────────────────────────

class CommentBody(BaseModel):
    target: str = Field(description="대상 참조(예: proposal:pr_…:sheet:sh_…)")
    body: str = Field(min_length=1, max_length=4000)
    anchor: dict[str, Any] | None = Field(default=None, description="화면 위치 등 기능별 앵커")
    parent_id: str | None = None


class Comment(BaseModel):
    id: str
    target: str
    body: str
    anchor: dict[str, Any] | None = None
    parent_id: str | None = None
    author: str
    author_name: str
    resolved: bool = False
    created_at: str
    updated_at: str


class CommentList(BaseModel):
    items: list[Comment]


class CommentPatch(BaseModel):
    body: str | None = None
    resolved: bool | None = None


@router.post("/comments", response_model=Comment, status_code=201, tags=["comments"])
async def add_comment(body: CommentBody) -> Comment:
    u = current_user()
    d = store().put("comments", new_id("cmt"), {**body.model_dump(), "author": u.id, "author_name": u.name, "resolved": False})
    return Comment(**d)


@router.get("/comments", response_model=CommentList, tags=["comments"])
async def list_comments(target: str = Query(..., description="대상 참조(접두 일치: target* 는 하위 전부)")) -> CommentList:
    if target.endswith("*"):
        items, _ = store().list("comments", limit=1000, order_by="created_at")
        items = [c for c in items if (c.get("target") or "").startswith(target[:-1])]
    else:
        items, _ = store().list("comments", where={"target": target}, limit=1000, order_by="created_at")
    return CommentList(items=[Comment(**c) for c in items])


@router.patch("/comments/{comment_id}", response_model=Comment, tags=["comments"])
async def patch_comment(comment_id: str, body: CommentPatch) -> Comment:
    if not store().get("comments", comment_id):
        raise not_found("코멘트", comment_id)
    return Comment(**store().patch("comments", comment_id, body.model_dump(exclude_none=True)))


@router.delete("/comments/{comment_id}", status_code=204, tags=["comments"])
async def delete_comment(comment_id: str) -> None:
    if not store().delete("comments", comment_id):
        raise not_found("코멘트", comment_id)


# ── 공유 링크(보기 전용) ─────────────────────────────────

class ShareBody(BaseModel):
    target: str
    route: str = Field(description="보기 전용 화면 웹 경로")
    title: str = ""
    expires_days: int | None = Field(default=30, ge=1, le=365)


class ShareLink(BaseModel):
    id: str
    token: str
    target: str
    route: str
    title: str = ""
    url: str = Field(description="게이트웨이 기준 상대 경로(/share/<token>)")
    created_by: str
    expires_at: str | None = None
    created_at: str


@router.post("/share-links", response_model=ShareLink, status_code=201, tags=["share"])
async def create_share(body: ShareBody) -> ShareLink:
    from datetime import datetime, timedelta, timezone

    token = secrets.token_urlsafe(12)
    expires = (datetime.now(timezone.utc) + timedelta(days=body.expires_days)).isoformat() if body.expires_days else None
    d = store().put("share_links", new_id("shr"), {**body.model_dump(exclude={"expires_days"}), "token": token,
                                                   "created_by": current_user().id, "expires_at": expires, "url": f"/share/{token}"})
    return ShareLink(**d)


@router.get("/share-links/{token}", response_model=ShareLink, tags=["share"])
async def resolve_share(token: str) -> ShareLink:
    items, _ = store().list("share_links", where={"token": token}, limit=1)
    if not items:
        raise not_found("공유 링크", token)
    return ShareLink(**items[0])


# ── 자산 사용 이력 ───────────────────────────────────────

class AssetUseBody(BaseModel):
    proposal_id: str
    sheet_id: str | None = None


class AssetUsage(BaseModel):
    ref: str
    proposals: int
    uses: list[AssetUseBody] = Field(default_factory=list)


class AssetUsageList(BaseModel):
    items: list[AssetUsage]


@router.put("/asset-usage/{ref:path}", status_code=204, tags=["internal"])
async def record_asset_use(ref: str, body: AssetUseBody) -> None:
    key = hashlib.sha1(ref.encode()).hexdigest()[:20]
    cur = store().get("asset_usage", key) or {"ref": ref, "uses": []}
    if not any(u["proposal_id"] == body.proposal_id and u.get("sheet_id") == body.sheet_id for u in cur["uses"]):
        cur["uses"].append(body.model_dump())
    store().put("asset_usage", key, cur, keep_history=False)


@router.get("/asset-usage", response_model=AssetUsageList, tags=["items"])
async def asset_usage(refs: str = Query(..., description="쉼표로 구분한 참조 목록")) -> AssetUsageList:
    out = []
    for ref in [r for r in refs.split(",") if r]:
        d = store().get("asset_usage", hashlib.sha1(ref.encode()).hexdigest()[:20])
        uses = (d or {}).get("uses", [])
        out.append(AssetUsage(ref=ref, proposals=len({u["proposal_id"] for u in uses}), uses=[AssetUseBody(**u) for u in uses]))
    return AssetUsageList(items=out)



# 검토 · 알림(별도 모듈) — 위 경로 뒤에 붙인다(경로가 겹치지 않음)
router.include_router(reviews.router)
router.include_router(notify.router)
