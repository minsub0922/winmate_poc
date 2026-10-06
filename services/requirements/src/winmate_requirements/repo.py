"""저장소 — DocStore.for_service("requirements") 위의 얇은 층.

컬렉션
- requirements  정의서 작업본(+ 고객 질문 inline). DocStore version = 작업본 revision(쓰기마다 +1, 기록은 남기지 않는다)
- versions      저장 스냅숏(불변). id = "{rq_id}:{n:06d}"
- sessions      심층 작성 세션(ds_)
- replies       고객 답변 분석(rp_)
- links         쓰는 곳 링크. id = "{rq_id}|{service}|{ref_id}"
- exports       정의서 내보내기(제안)
- indexcache    workspace 색인에 마지막으로 올린 값(revision 을 올리지 않으려고 따로 둔다)

API 프로세스와 워커가 같은 작업본을 함께 쓰므로 쓰기는 `mutate()`(낙관적 동시성 + 재시도)로만 한다.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from winmate_common.env import settings
from winmate_common.errors import ApiError
from winmate_common.store import DocStore, VersionConflict

T = TypeVar("T")
_stores: dict[Path, DocStore] = {}


def store() -> DocStore:
    path = settings().service_data_dir("requirements") / "requirements.sqlite"
    st = _stores.get(path)
    if st is None:
        st = DocStore(path)
        for coll, field in (("requirements", "owner_id"), ("versions", "requirement_id"), ("sessions", "requirement_id"),
                            ("replies", "requirement_id"), ("links", "requirement_id"), ("exports", "requirement_id")):
            st.index(coll, field)
        _stores[path] = st
    return st


def not_found(what: str = "요구사항 정의서", ident: str | None = None) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요", {"resource": what, "id": ident})


# ── 정의서 ───────────────────────────────────────────────

def get_doc_sync(rq_id: str) -> dict[str, Any] | None:
    return store().get("requirements", rq_id)


async def get_doc(rq_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(get_doc_sync, rq_id)


async def require_doc(rq_id: str) -> dict[str, Any]:
    doc = await get_doc(rq_id)
    if doc is None:
        raise not_found(ident=rq_id)
    return doc


async def create_doc(rq_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(store().put, "requirements", rq_id, doc, keep_history=False)


def _mutate_sync(rq_id: str, fn: Callable[[dict[str, Any], int], T], retries: int) -> tuple[dict[str, Any], T]:
    st = store()
    last: Exception | None = None
    for _ in range(retries):
        doc = st.get("requirements", rq_id)
        if doc is None:
            raise not_found(ident=rq_id)
        rev = int(doc["version"]) + 1
        result = fn(doc, rev)
        try:
            saved = st.put("requirements", rq_id, doc, expected_version=int(doc["version"]), keep_history=False)
        except VersionConflict as exc:
            last = exc
            continue
        return saved, result
    raise ApiError(409, "REVISION_CONFLICT", "다른 곳에서 동시에 고치고 있어요. 다시 시도해 주세요", {"error": str(last)})


async def mutate(rq_id: str, fn: Callable[[dict[str, Any], int], T], *, retries: int = 12) -> tuple[dict[str, Any], T]:
    """작업본을 읽고 fn(doc, 새 revision) 으로 고친 뒤 저장한다. 다른 쓰기와 겹치면 처음부터 다시(fn 은 다시 실행돼도 안전해야 한다)."""
    return await asyncio.to_thread(_mutate_sync, rq_id, fn, retries)


async def list_docs(owner_id: str | None, *, limit: int = 2000) -> list[dict[str, Any]]:
    where = {"owner_id": owner_id} if owner_id else None
    items, _ = await asyncio.to_thread(store().list, "requirements", where=where, limit=limit)
    return items


# ── 버전 ─────────────────────────────────────────────────

def version_key(rq_id: str, n: int) -> str:
    return f"{rq_id}:{n:06d}"


def put_version_sync(rq_id: str, n: int, body: dict[str, Any]) -> None:
    store().put("versions", version_key(rq_id, n), {**body, "requirement_id": rq_id, "n": n}, keep_history=False)


async def get_version(rq_id: str, n: int) -> dict[str, Any] | None:
    return await asyncio.to_thread(store().get, "versions", version_key(rq_id, n))


async def list_versions(rq_id: str) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, "versions", where={"requirement_id": rq_id}, order_by="-n", limit=1000)
    return items


# ── 일반 컬렉션 ──────────────────────────────────────────

async def get(coll: str, doc_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(store().get, coll, doc_id)


async def put(coll: str, doc_id: str, body: dict[str, Any], *, expected_version: int | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(store().put, coll, doc_id, body, expected_version=expected_version, keep_history=False)


async def delete(coll: str, doc_id: str) -> bool:
    return await asyncio.to_thread(store().delete, coll, doc_id)


async def find(coll: str, where: dict[str, Any], *, order_by: str = "-updated_at", limit: int = 500) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, coll, where=where, order_by=order_by, limit=limit)
    return items


def link_key(rq_id: str, service: str, ref_id: str) -> str:
    return f"{rq_id}|{service}|{ref_id}"


# ── 세션 잠금(같은 API 프로세스 안에서 같은 세션 답을 한 번에 하나씩) ──────────

_locks: dict[tuple[int, str], asyncio.Lock] = {}


def lock_for(key: str) -> asyncio.Lock:
    k = (id(asyncio.get_running_loop()), key)
    lk = _locks.get(k)
    if lk is None:
        if len(_locks) > 5000:
            _locks.clear()
        lk = asyncio.Lock()
        _locks[k] = lk
    return lk
