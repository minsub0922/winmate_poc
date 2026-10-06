"""저장소 — DocStore.for_service("storyboard") 위의 얇은 층.

컬렉션
- storyboards     작업본(스토리보드 하나 = 문서 하나)
- sb_versions     저장 버전 스냅숏(`{sb_id}:v{n}`, 불변)
- revisions       수정 요청(rev_…)
- sync_previews   정의서 동기화 미리 보기(syp_…)
- rq_snapshots    정의서 버전 스냅숏 캐시(`{rq_id}@{n}` — 정의서 버전은 불변이라 캐시만 한다, 작업본에 섞지 않음)

REST 와 워커가 같은 문서를 고치므로 쓰기는 `update(sb_id, fn)`(낙관적 잠금 + 재시도)로만 한다.
"""
from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable
from typing import Any

from winmate_common.env import settings
from winmate_common.errors import ApiError
from winmate_common.store import DocStore, VersionConflict

SB = "storyboards"
VERSIONS = "sb_versions"
REVISIONS = "revisions"
PREVIEWS = "sync_previews"
RQ_CACHE = "rq_snapshots"

_stores: dict[str, DocStore] = {}


def store() -> DocStore:
    path = settings().service_data_dir("storyboard") / "storyboard.sqlite"
    key = str(path)
    st = _stores.get(key)
    if st is None:
        st = DocStore(path)
        for field in ("owner_id", "started", "status", "requirement_id"):
            st.index(SB, field)
        st.index(VERSIONS, "storyboard_id")
        _stores[key] = st
    return st


def _not_found(what: str, ident: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요: {ident}", {"resource": what, "id": ident})


async def get(collection: str, doc_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(store().get, collection, doc_id)


async def put(collection: str, doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(store().put, collection, doc_id, data, keep_history=False)


async def get_sb(sb_id: str) -> dict[str, Any] | None:
    return await get(SB, sb_id)


async def require_sb(sb_id: str) -> dict[str, Any]:
    doc = await get_sb(sb_id) if sb_id.startswith("sb_") else None
    if doc is None:
        raise _not_found("스토리보드", sb_id)
    return doc


async def update(sb_id: str, fn: Callable[[dict[str, Any]], dict[str, Any] | None], *, retries: int = 12) -> dict[str, Any]:
    """읽고-고치고-쓰기(낙관적 잠금). fn 은 사본을 고쳐 돌려준다(None 이면 쓰지 않음). fn 이 ApiError 를 던지면 그대로 올라간다."""
    st = store()
    for attempt in range(retries):
        cur = await asyncio.to_thread(st.get, SB, sb_id)
        if cur is None:
            raise _not_found("스토리보드", sb_id)
        new = fn(copy.deepcopy(cur))
        if new is None:
            return cur
        try:
            return await asyncio.to_thread(st.put, SB, sb_id, new, expected_version=cur["version"], keep_history=False)
        except VersionConflict:
            await asyncio.sleep(0.02 * (attempt + 1))
    raise ApiError(409, "CONFLICT", "다른 작업과 겹쳐 저장하지 못했어요. 다시 시도해 주세요.")


async def create_sb(sb_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(store().put, SB, sb_id, data, keep_history=False)


async def delete_sb(sb_id: str) -> bool:
    return await asyncio.to_thread(store().delete, SB, sb_id)


async def list_sb(where: dict[str, Any], limit: int = 500) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, SB, where=where, limit=limit)
    return items


# ── 버전 ──────────────────────────────────────────────────

def version_id(sb_id: str, n: int) -> str:
    return f"{sb_id}:v{n}"


async def get_version(sb_id: str, n: int) -> dict[str, Any] | None:
    doc = await get(VERSIONS, version_id(sb_id, n))
    if doc is not None:
        doc["version"] = doc.get("n", n)
    return doc


async def put_version(sb_id: str, n: int, data: dict[str, Any]) -> dict[str, Any]:
    body = {**data, "storyboard_id": sb_id, "n": n}
    return await put(VERSIONS, version_id(sb_id, n), body)


async def list_versions(sb_id: str) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, VERSIONS, where={"storyboard_id": sb_id}, order_by="created_at", limit=500)
    for it in items:
        it["version"] = it.get("n")
    return sorted(items, key=lambda d: d.get("n", 0))


# ── 수정 요청 · 동기화 미리 보기 ───────────────────────────────

async def get_revision(rev_id: str) -> dict[str, Any] | None:
    return await get(REVISIONS, rev_id)


async def put_revision(rev_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await put(REVISIONS, rev_id, data)


async def get_preview(syp_id: str) -> dict[str, Any] | None:
    return await get(PREVIEWS, syp_id)


async def put_preview(syp_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await put(PREVIEWS, syp_id, data)


# ── 정의서 스냅숏 캐시 ──────────────────────────────────────

async def cached_snapshot(rq_id: str, version: int) -> dict[str, Any] | None:
    doc = await get(RQ_CACHE, f"{rq_id}@{version}")
    return (doc or {}).get("raw")


async def cache_snapshot(rq_id: str, version: int, raw: dict[str, Any]) -> None:
    await put(RQ_CACHE, f"{rq_id}@{version}", {"raw": raw})
