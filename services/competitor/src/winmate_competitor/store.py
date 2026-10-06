"""competitor 저장소 — DocStore.for_service("competitor") (data/competitor/competitor.sqlite) 위의 얇은 계층.

컬렉션
- analyses   ca_…          작업(§5.1) + 칸 · 업종 · 칩 · 경쟁사(§5.3) · 기준(§5.4) · 찾기/실행 진행
- versions   ca_…:{n}       결과 버전(§5.5 · §5.6) — facts · positioning · samsung_cells · verdicts · counts · strengths · cautions ·
                            footer + 주장 · 인용 · 출처(§5.7)
- work       ca_…           실행 중 작업본(경쟁사별로 모은 사실 · 주장 · 출처 · 판정) — 부분 결과 · 중지 · 다시 판정에 재사용
- handoffs   hof_…          넘김 기록(§5.8)
- rechecks   chk_…          30일 재확인(§5.8)

DocStore 는 문서마다 쓰기 횟수 `version` 을 붙이므로 결과 버전은 `result_version`(작업) · `n`(버전) · `_rv`(넘김) 에 둔다.
수집 텍스트 스냅숏은 `${DATA_DIR}/competitor/snapshots/{src}.txt`.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar

from winmate_common.ids import new_id, now_iso
from winmate_common.store import DocStore, VersionConflict

from . import config

T = TypeVar("T")
_RMW = threading.RLock()
_TRIES = 12

A = "analyses"
V = "versions"
W = "work"
HOF = "handoffs"
CHK = "rechecks"


@lru_cache(maxsize=4)
def _store_for(path: str) -> DocStore:
    st = DocStore(Path(path))
    for coll, field in ((A, "owner_id"), (A, "status"), (V, "analysis_id"), (HOF, "analysis_id"), (CHK, "analysis_id")):
        try:
            st.index(coll, field)
        except Exception:  # noqa: BLE001
            pass
    return st


def store() -> DocStore:
    from winmate_common.env import settings

    return _store_for(str(settings().service_data_dir(config.SERVICE) / "competitor.sqlite"))


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
    body = dict(doc)
    body["updated_at"] = now_iso()
    saved = _clean(store().put(A, aid, body, keep_history=False)) or {}
    saved["id"] = aid
    return saved


def _rmw(coll: str, did: str, fn: Callable[[dict[str, Any]], Any], prep: Callable[[dict[str, Any] | None], dict[str, Any] | None],
         finish: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
    """읽고 · 고치고 · 쓰기 — API 와 워커(다른 프로세스)가 같은 문서를 고쳐도 잃지 않게 쓰기 횟수(version)로 비교 후 쓴다(낙관적 잠금).
    부딪치면 새로 읽어 fn 을 다시 적용한다(fn 은 문서만 고치는 함수여야 한다)."""
    with _RMW:
        for i in range(_TRIES):
            raw = store().get(coll, did)
            cur = prep(raw)
            if cur is None:
                raise KeyError(did)
            fn(cur)
            try:
                return store().put(coll, did, finish(cur), keep_history=False, expected_version=int(raw["version"]) if raw else 0)
            except VersionConflict:
                time.sleep(0.005 * (i + 1))
        raise VersionConflict(f"{coll}/{did} 동시 수정이 계속 부딪혀요")


def update_analysis(aid: str, fn: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    def prep(raw: dict[str, Any] | None) -> dict[str, Any] | None:
        doc = _clean(raw)
        if doc is not None:
            doc["id"] = aid
        return doc

    def finish(doc: dict[str, Any]) -> dict[str, Any]:
        body = dict(doc)
        body["updated_at"] = now_iso()
        return body

    saved = _clean(_rmw(A, aid, fn, prep, finish)) or {}
    saved["id"] = aid
    return saved


def delete_analysis(aid: str) -> bool:
    return store().delete(A, aid)


def list_analyses(owner_id: str | None = None, limit: int = 1000) -> list[dict[str, Any]]:
    where = {"owner_id": owner_id} if owner_id else None
    items, _ = store().list(A, where=where, limit=limit)
    out = []
    for it in items:
        c = _clean(it) or {}
        out.append(c)
    return out


# ── 결과 버전 ────────────────────────────────────────────
def vkey(aid: str, n: int) -> str:
    return f"{aid}:{n}"


def get_version(aid: str, n: int | None) -> dict[str, Any] | None:
    if not n:
        return None
    return _clean(store().get(V, vkey(aid, int(n))))


def put_version(aid: str, n: int, doc: dict[str, Any]) -> dict[str, Any]:
    body = dict(doc)
    body["analysis_id"] = aid
    body["n"] = n
    body.setdefault("created_at", now_iso())
    return _clean(store().put(V, vkey(aid, n), body, keep_history=False)) or {}


def update_version(aid: str, n: int, fn: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    def finish(doc: dict[str, Any]) -> dict[str, Any]:
        body = dict(doc)
        body["analysis_id"] = aid
        body["n"] = n
        return body

    return _clean(_rmw(V, vkey(aid, n), fn, _clean, finish)) or {}


def list_versions(aid: str) -> list[dict[str, Any]]:
    items, _ = store().list(V, where={"analysis_id": aid}, limit=500)
    return sorted([_clean(i) or {} for i in items], key=lambda v: -int(v.get("n") or 0))


# ── 작업본 ───────────────────────────────────────────────
def get_work(aid: str) -> dict[str, Any]:
    return _work_defaults(_clean(store().get(W, aid)) or {})


def put_work(aid: str, doc: dict[str, Any]) -> dict[str, Any]:
    return _clean(store().put(W, aid, doc, keep_history=False)) or {}


def _work_defaults(doc: dict[str, Any]) -> dict[str, Any]:
    doc.setdefault("competitors", {})
    doc.setdefault("claims", {})
    doc.setdefault("citations", [])
    doc.setdefault("sources", {})
    return doc


def update_work(aid: str, fn: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    return _clean(_rmw(W, aid, fn, lambda raw: _work_defaults(_clean(raw) or {}), dict)) or {}


# ── 넘김 · 재확인 ────────────────────────────────────────
def _rv_in(doc: dict[str, Any]) -> dict[str, Any]:
    doc = dict(doc)
    if "version" in doc:
        doc["_rv"] = doc.pop("version")
    return doc


def _rv_out(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if doc is not None and "_rv" in doc:
        doc["version"] = doc.pop("_rv")
    return doc


def get_doc(coll: str, did: str) -> dict[str, Any] | None:
    raw = store().get(coll, did)
    if raw is None:
        return None
    meta_updated = raw.get("updated_at")
    doc = _rv_out(_clean(raw))
    if doc is not None:
        doc["id"] = did
        doc.setdefault("updated_at", meta_updated)
    return doc


def put_doc(coll: str, did: str, doc: dict[str, Any]) -> dict[str, Any]:
    body = _rv_in(doc)
    body.setdefault("created_at", now_iso())
    out = _rv_out(_clean(store().put(coll, did, body, keep_history=False))) or {}
    out["id"] = did
    return out


def update_doc(coll: str, did: str, fn: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    def prep(raw: dict[str, Any] | None) -> dict[str, Any] | None:
        if raw is None:
            return None
        meta_updated = raw.get("updated_at")
        doc = _rv_out(_clean(raw)) or {}
        doc["id"] = did
        doc.setdefault("updated_at", meta_updated)
        return doc

    def finish(doc: dict[str, Any]) -> dict[str, Any]:
        body = _rv_in(doc)
        body.setdefault("created_at", now_iso())
        return body

    out = _rv_out(_clean(_rmw(coll, did, fn, prep, finish))) or {}
    out["id"] = did
    return out


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
