"""저장 — `DocStore.for_service("proposal")`(data/proposal/proposal.sqlite).

컬렉션(§5)
  proposals      pr_    제안서(working state). 저장 필드 `saved_version` 이 화면의 version, `rev` 는 자동 저장 리비전
  sections       sec_   섹션
  sheets         sht_   시트
  links          lnk_   연결 자료(+ 반입 스냅숏)
  imports        imp_   반입
  facts          fct_   값(사실)
  confirm_items  cfm_   확인 항목
  versions       {pr}:v{n}  버전 스냅숏
  changes        chg_   변경 기록(30일)
  messages       msg_   섹션 · 시트 대화
  exports        xpt_   내보내기 기록
  reuse          pru_   기존 제안서 분석
  suggestions    {pr}:{comment}  코멘트 수정안
  assets         kbimg:<id>  kb 이미지 → files 사본(렌더용)

DocStore 의 내부 `version` 은 동시 쓰기 검사(CAS)용이다(문서 필드 이름 version 은 쓰지 않는다).
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

from .config import now_iso
from .defs import SERVICE

T = TypeVar("T")

_store: DocStore | None = None
_store_path: str | None = None

INDEXES = (("proposals", "owner_id"), ("proposals", "status"), ("sections", "proposal_id"), ("sheets", "proposal_id"),
           ("links", "proposal_id"), ("imports", "proposal_id"), ("facts", "proposal_id"), ("confirm_items", "proposal_id"),
           ("versions", "proposal_id"), ("changes", "proposal_id"), ("messages", "proposal_id"), ("exports", "proposal_id"),
           ("reuse", "proposal_id"))


def store() -> DocStore:
    """테스트마다 DATA_DIR 가 바뀌므로 경로가 바뀌면 다시 연다."""
    global _store, _store_path
    path = str(settings().service_data_dir(SERVICE) / f"{SERVICE}.sqlite")
    if _store is None or _store_path != path:
        _store = DocStore.for_service(SERVICE)
        _store_path = path
        for coll, fld in INDEXES:
            _store.index(coll, fld)
    return _store


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in doc.items() if k not in ("version", "created_at", "updated_at")} | {
        "created_at": doc.get("created_at"), "updated_at": doc.get("updated_at"), "_cas": doc.get("version")}


def get(coll: str, doc_id: str) -> dict[str, Any] | None:
    d = store().get(coll, doc_id)
    return _strip(d) if d else None


def must(coll: str, doc_id: str, err: ApiError | None = None) -> dict[str, Any]:
    d = get(coll, doc_id)
    if d is None:
        raise err or ApiError(404, "NOT_FOUND", "찾을 수 없어요", {"resource": coll, "id": doc_id})
    return d


def _clean(data: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in data.items() if k not in ("_cas", "version", "created_at", "updated_at")}
    out.setdefault("created_iso", data.get("created_iso") or now_iso())
    out["touched_at"] = now_iso()
    return out


def put(coll: str, doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    saved = store().put(coll, doc_id, _clean(data), keep_history=False)
    return _strip(saved)


def delete(coll: str, doc_id: str) -> bool:
    return store().delete(coll, doc_id)


def list_all(coll: str, where: dict[str, Any] | None = None, *, order_by: str = "created_at", limit: int = 5000) -> list[dict[str, Any]]:
    items, _ = store().list(coll, where=where, order_by=order_by, limit=limit)
    return [_strip(i) for i in items]


def mutate(coll: str, doc_id: str, fn: Callable[[dict[str, Any]], T], *, retries: int = 16,
           err: ApiError | None = None) -> tuple[dict[str, Any], T]:
    """읽기 → fn(문서) 로 고침 → 내부 version 이 그대로일 때만 쓰기(아니면 다시). fn 의 반환값을 함께 돌려준다."""
    for i in range(retries):
        cur = store().get(coll, doc_id)
        if cur is None:
            raise err or ApiError(404, "NOT_FOUND", "찾을 수 없어요", {"resource": coll, "id": doc_id})
        cas = cur["version"]
        data = copy.deepcopy(_strip(cur))
        res = fn(data)
        try:
            saved = store().put(coll, doc_id, _clean(data), expected_version=cas, keep_history=False)
            return _strip(saved), res
        except VersionConflict:
            time.sleep(0.005 * (i + 1) + random.random() * 0.01)
    raise ApiError(409, "CONFLICT", "다른 곳에서 동시에 고치고 있어요. 다시 시도해 주세요.")


# ── async ─────────────────────────────────────────────────
async def aget(coll: str, doc_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(get, coll, doc_id)


async def amust(coll: str, doc_id: str, err: ApiError | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(must, coll, doc_id, err)


async def aput(coll: str, doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(put, coll, doc_id, data)


async def adelete(coll: str, doc_id: str) -> bool:
    return await asyncio.to_thread(delete, coll, doc_id)


async def alist(coll: str, where: dict[str, Any] | None = None, **kw: Any) -> list[dict[str, Any]]:
    return await asyncio.to_thread(list_all, coll, where, **kw)


async def amutate(coll: str, doc_id: str, fn: Callable[[dict[str, Any]], T], **kw: Any) -> tuple[dict[str, Any], T]:
    return await asyncio.to_thread(mutate, coll, doc_id, fn, **kw)
