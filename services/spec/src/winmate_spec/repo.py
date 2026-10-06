"""저장 — `DocStore.for_service("spec")`(data/spec/spec.sqlite).

컬렉션
  sheets        sp_   시트 작업(제품 · 항목 · 행 · 칸 · 값 확인 · 경고 · 찾기 · 대응표 · 데이터시트 · 양식 · 형식)
  snapshots     {sp}.v{n}  저장된 판(버전 · 되살리기)
  edit_sessions ses_  편집 세션
  exports       sex_  내보내기
  handoffs      sho_  제안서 넘김
  links         slk_  제안서 연결
  preferences   <user_id>  내 기본값
  lifecycle     <model_key>  생애주기 표
  catalog_state <adapter>    카탈로그 버전 감지
  translations  <sha1>       번역 캐시

시트 문서의 `doc_version` 이 화면 · 계약의 `version`(의미 있는 판)이다. DocStore 의 내부 version 은 동시 쓰기 검사(CAS)용.
"""
from __future__ import annotations

import asyncio
import copy
import random
import time
from collections.abc import Callable
from typing import Any, TypeVar

from winmate_common.env import settings
from winmate_common.errors import ApiError
from winmate_common.store import DocStore, VersionConflict

from .config import SERVICE

T = TypeVar("T")

_store: DocStore | None = None
_store_path: str | None = None


def store() -> DocStore:
    """테스트마다 DATA_DIR 가 바뀌므로 경로가 바뀌면 다시 연다."""
    global _store, _store_path
    path = str(settings().service_data_dir(SERVICE) / f"{SERVICE}.sqlite")
    if _store is None or _store_path != path:
        _store = DocStore.for_service(SERVICE)
        _store_path = path
        for coll, fld in (("sheets", "owner_id"), ("sheets", "archived"), ("edit_sessions", "sheet_id"), ("handoffs", "sheet_id"),
                          ("links", "sheet_id"), ("links", "proposal_id"), ("exports", "sheet_id")):
            _store.index(coll, fld)
    return _store


async def run(fn: Callable[..., T], *args: Any, **kw: Any) -> T:
    return await asyncio.to_thread(fn, *args, **kw)


def get(coll: str, doc_id: str) -> dict[str, Any] | None:
    return store().get(coll, doc_id)


def must(coll: str, doc_id: str, what: str = "시트") -> dict[str, Any]:
    d = store().get(coll, doc_id)
    if d is None:
        raise ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요: {doc_id}", {"resource": coll, "id": doc_id})
    return d


TOUCHED = {"sheets", "links", "handoffs", "exports", "edit_sessions"}


def _touch(coll: str, data: dict[str, Any]) -> None:
    """앱 시계(config.now — 테스트 고정 시계)로 마지막 변경 시각. 화면 · 목록 시각은 이것을 쓴다."""
    if coll in TOUCHED:
        from .config import now_iso
        data["touched_at"] = now_iso()
        data.setdefault("created_at_app", data["touched_at"])


def put(coll: str, doc_id: str, data: dict[str, Any], *, history: bool = False) -> dict[str, Any]:
    _touch(coll, data)
    return store().put(coll, doc_id, data, keep_history=history)


def delete(coll: str, doc_id: str) -> bool:
    return store().delete(coll, doc_id)


def list_all(coll: str, where: dict[str, Any] | None = None, limit: int = 2000) -> list[dict[str, Any]]:
    items, _ = store().list(coll, where=where, limit=limit)
    return items


def mutate(coll: str, doc_id: str, fn: Callable[[dict[str, Any]], T], *, retries: int = 12, what: str = "시트") -> tuple[dict[str, Any], T]:
    """읽기 → fn(문서) 로 고침 → 내부 version 이 그대로일 때만 쓰기(아니면 다시). fn 의 반환값을 함께 돌려준다."""
    for i in range(retries):
        cur = store().get(coll, doc_id)
        if cur is None:
            raise ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요: {doc_id}", {"resource": coll, "id": doc_id})
        internal = cur["version"]
        data = copy.deepcopy(cur)
        res = fn(data)
        _touch(coll, data)
        try:
            saved = store().put(coll, doc_id, data, expected_version=internal, keep_history=False)
            saved["_internal_version"] = saved["version"]
            return saved, res
        except VersionConflict:
            time.sleep(0.01 * (i + 1) + random.random() * 0.01)
    raise ApiError(409, "CONFLICT", "다른 곳에서 동시에 고치고 있어요. 다시 시도해 주세요.")


async def amutate(coll: str, doc_id: str, fn: Callable[[dict[str, Any]], T], **kw: Any) -> tuple[dict[str, Any], T]:
    return await asyncio.to_thread(mutate, coll, doc_id, fn, **kw)


async def aget(coll: str, doc_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(get, coll, doc_id)


async def amust(coll: str, doc_id: str, what: str = "시트") -> dict[str, Any]:
    return await asyncio.to_thread(must, coll, doc_id, what)


async def aput(coll: str, doc_id: str, data: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return await asyncio.to_thread(put, coll, doc_id, data, **kw)


async def alist(coll: str, where: dict[str, Any] | None = None, limit: int = 2000) -> list[dict[str, Any]]:
    return await asyncio.to_thread(list_all, coll, where, limit)
