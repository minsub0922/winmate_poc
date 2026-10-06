"""mi 저장소 — DocStore.for_service("mi") (data/mi/mi.sqlite) 위의 얇은 저장 계층.

컬렉션
- analyses   mi_…            작업(§5.1) + 설계 결정(decisions) · 경쟁사 · 기준 · 삼성 비교 제품
- versions   mi_…:{n}         결과 버전(§5.3) — document · claims · sources · citations · fix_items · slides · counts
- drafts     mi_…             실행 중 작업본 {work(버전 문서) · evidence · budget · progress} — 미리 보기 · 중지 시 부분 결과
                              (DocStore 가 `version` 키를 쓰므로 작업본 버전은 `work`)
- revisions  rev_…            부분 재분석 안(§5.9) + changes
- handoffs   hof_…            넘김 기록(§5.11)
- rechecks   chk_…            30일 재확인(§5.10)
- onepagers  mi_…             한 장 요약 결과

DocStore 는 문서마다 자기 `version`(쓰기 횟수)을 붙이므로, 작업의 결과 버전은 `result_version` 필드에 둔다(API 에서는 `version`).
모든 메서드는 동기 — async 코드는 `await R.call(fn, …)` 또는 `aR.<메서드>` 로 스레드에서 부른다.
"""
from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar

from winmate_common.ids import new_id, now_iso
from winmate_common.store import DocStore

from . import config

T = TypeVar("T")
_RMW = threading.RLock()   # 읽고-고치고-쓰기(update_*)를 한 프로세스 안에서 차례로

A = "analyses"
V = "versions"
D = "drafts"
REV = "revisions"
HOF = "handoffs"
CHK = "rechecks"
ONE = "onepagers"


@lru_cache(maxsize=4)
def _store_for(path: str) -> DocStore:
    st = DocStore(Path(path))
    for field in ("owner_id", "status", "analysis_id"):
        try:
            st.index(A if field != "analysis_id" else V, field)
        except Exception:  # noqa: BLE001
            pass
    for coll in (REV, HOF, CHK):
        try:
            st.index(coll, "analysis_id")
        except Exception:  # noqa: BLE001
            pass
    return st


def store() -> DocStore:
    from winmate_common.env import settings

    return _store_for(str(settings().service_data_dir("mi") / "mi.sqlite"))


def _clean(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is None:
        return None
    doc = dict(doc)
    doc.pop("version", None)
    return doc


# ── 작업 ─────────────────────────────────────────────────
def get_analysis(aid: str) -> dict[str, Any] | None:
    doc = _clean(store().get(A, aid))
    if doc is not None:
        doc["id"] = aid
    return doc


def put_analysis(doc: dict[str, Any]) -> dict[str, Any]:
    aid = doc["id"]
    doc = dict(doc)
    doc["updated_at"] = now_iso()
    saved = store().put(A, aid, doc, keep_history=False)
    out = _clean(saved) or {}
    out["id"] = aid
    return out


def patch_analysis(aid: str, changes: dict[str, Any]) -> dict[str, Any]:
    cur = get_analysis(aid)
    if cur is None:
        raise KeyError(aid)
    cur.update(changes)
    return put_analysis(cur)


def update_analysis(aid: str, fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    """읽고 → fn 으로 고치고 → 저장(같은 프로세스 안에서 순서대로)."""
    with _RMW:
        cur = get_analysis(aid)
        if cur is None:
            raise KeyError(aid)
        fn(cur)
        return put_analysis(cur)


def delete_analysis(aid: str) -> bool:
    return store().delete(A, aid)


def list_analyses(owner_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    where = {"owner_id": owner_id} if owner_id else None
    items, _ = store().list(A, where=where, limit=limit)
    out = []
    for it in items:
        it = _clean(it) or {}
        out.append(it)
    return out


# ── 결과 버전 ────────────────────────────────────────────
def version_key(aid: str, n: int) -> str:
    return f"{aid}:{n}"


def get_version(aid: str, n: int) -> dict[str, Any] | None:
    if not n:
        return None
    return _clean(store().get(V, version_key(aid, n)))


def put_version(aid: str, n: int, doc: dict[str, Any]) -> dict[str, Any]:
    doc = dict(doc)
    doc["analysis_id"] = aid
    doc["n"] = n
    return _clean(store().put(V, version_key(aid, n), doc, keep_history=False)) or {}


def list_versions(aid: str) -> list[dict[str, Any]]:
    items, _ = store().list(V, where={"analysis_id": aid}, order_by="-created_at", limit=500)
    out = [_clean(i) or {} for i in items]
    return sorted(out, key=lambda v: -int(v.get("n") or 0))


def update_version(aid: str, n: int, fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    with _RMW:
        cur = get_version(aid, n)
        if cur is None:
            raise KeyError(version_key(aid, n))
        fn(cur)
        return put_version(aid, n, cur)


# ── 작업본(실행 중) ──────────────────────────────────────
def get_draft(aid: str) -> dict[str, Any] | None:
    return _clean(store().get(D, aid))


def put_draft(aid: str, doc: dict[str, Any]) -> dict[str, Any]:
    return _clean(store().put(D, aid, doc, keep_history=False)) or {}


def update_draft(aid: str, fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    with _RMW:
        cur = get_draft(aid) or {}
        fn(cur)
        return put_draft(aid, cur)


def delete_draft(aid: str) -> None:
    store().delete(D, aid)


# ── 재분석 안 · 넘김 · 재확인 · 한 장 요약 ──────────────
# 이 문서들의 `version`(결과 버전)은 DocStore 의 쓰기 횟수 `version` 과 겹치므로 `_rv` 로 저장하고 읽을 때 되돌린다.
def _rv_in(doc: dict[str, Any]) -> dict[str, Any]:
    if "version" in doc:
        doc = dict(doc)
        doc["_rv"] = doc.pop("version")
    return doc


def _rv_out(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is not None and "_rv" in doc:
        doc["version"] = doc.pop("_rv")
    return doc


def get_doc(coll: str, did: str) -> dict[str, Any] | None:
    doc = _rv_out(_clean(store().get(coll, did)))
    if doc is not None:
        doc["id"] = did
    return doc


def put_doc(coll: str, did: str, doc: dict[str, Any]) -> dict[str, Any]:
    doc = _rv_in(dict(doc))
    doc["updated_at"] = now_iso()
    out = _rv_out(_clean(store().put(coll, did, doc, keep_history=False))) or {}
    out["id"] = did
    return out


def update_doc(coll: str, did: str, fn: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    with _RMW:
        cur = get_doc(coll, did)
        if cur is None:
            raise KeyError(did)
        fn(cur)
        return put_doc(coll, did, cur)


def list_docs(coll: str, analysis_id: str, limit: int = 200) -> list[dict[str, Any]]:
    items, _ = store().list(coll, where={"analysis_id": analysis_id}, order_by="-created_at", limit=limit)
    out = []
    for i in items:
        d = _rv_out(_clean(i)) or {}
        out.append(d)
    return out


# ── 수집 텍스트 스냅숏 ───────────────────────────────────
def save_snapshot(src_id: str, text: str, pages: list[str] | None = None) -> str:
    d = config.snapshots_dir()
    (d / f"{src_id}.txt").write_text(text or "", encoding="utf-8")
    if pages:
        (d / f"{src_id}.pages.json").write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return f"snapshots/{src_id}.txt"


def load_snapshot(src_id: str) -> tuple[str | None, list[str] | None]:
    d = config.snapshots_dir()
    p = d / f"{src_id}.txt"
    if not p.is_file():
        return None, None
    pages = None
    pp = d / f"{src_id}.pages.json"
    if pp.is_file():
        try:
            pages = json.loads(pp.read_text(encoding="utf-8"))
        except ValueError:
            pages = None
    return p.read_text(encoding="utf-8"), pages


# ── async 도우미 ─────────────────────────────────────────
async def call(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    return await asyncio.to_thread(fn, *args, **kwargs)


def nid(prefix: str) -> str:
    return new_id(prefix)
