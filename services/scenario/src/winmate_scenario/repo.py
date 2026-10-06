"""저장소 — DocStore.for_service("scenario") 위의 얇은 층(`${DATA_DIR}/scenario/scenario.sqlite`).

컬렉션
- scenarios          시나리오 작업본 하나 = 문서 하나(시간대 · 역할 · 장면 · 고른 솔루션/제품 · 추천 · 편집 기록 · 사용 등록)
- scene_versions     장면 버전 스냅숏 `{scene_id}:v{n}`(불변) — 「v{k} · {이유}」 · 되돌리기 · 바뀐 곳
- scenario_versions  시나리오 저장 버전 `{sc_id}:v{n}`(불변) — :save · 생성 완료 · handoff(version)
- exports            내보내기 기록 `sce_…`

API 와 워커가 같은 문서를 고치므로 쓰기는 `update(sc_id, fn)`(낙관적 잠금 + 재시도)로만 한다.
"""
from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable
from typing import Any

from winmate_common.env import settings
from winmate_common.errors import ApiError
from winmate_common.store import DocStore, VersionConflict

SC = "scenarios"
SCENE_VERSIONS = "scene_versions"
VERSIONS = "scenario_versions"
EXPORTS = "exports"
SCENE_INDEX = "scene_index"

_stores: dict[str, DocStore] = {}


def store() -> DocStore:
    path = settings().service_data_dir("scenario") / "scenario.sqlite"
    key = str(path)
    st = _stores.get(key)
    if st is None:
        st = DocStore(path)
        for field in ("owner", "status", "start_mode"):
            st.index(SC, field)
        st.index(SCENE_VERSIONS, "scene_id")
        st.index(VERSIONS, "scenario_id")
        st.index(EXPORTS, "scenario_id")
        _stores[key] = st
    return st


def not_found(what: str, ident: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요: {ident}", {"resource": what, "id": ident})


async def get(collection: str, doc_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(store().get, collection, doc_id)


async def put(collection: str, doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(store().put, collection, doc_id, data, keep_history=False)


async def get_sc(sc_id: str) -> dict[str, Any] | None:
    return await get(SC, sc_id) if sc_id.startswith("sc_") else None


async def require_sc(sc_id: str) -> dict[str, Any]:
    doc = await get_sc(sc_id)
    if doc is None or doc.get("deleted_at"):
        raise not_found("시나리오", sc_id)
    return doc


async def create_sc(sc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    stored = await asyncio.to_thread(store().put, SC, sc_id, data, keep_history=False)
    await _index_scenes(sc_id, stored, None)
    return stored


async def _index_scenes(sc_id: str, new: dict[str, Any], old: dict[str, Any] | None) -> None:
    """장면 id → 시나리오 id 색인(`GET /v1/scenes/{sid}` 처럼 시나리오 id 없이 오는 요청용). 새로 생긴 장면만."""
    before = {s["id"] for s in (old or {}).get("scenes") or []}
    for s in new.get("scenes") or []:
        if s["id"] not in before:
            await asyncio.to_thread(store().put, SCENE_INDEX, s["id"], {"scenario_id": sc_id}, keep_history=False)


async def scenario_of_scene(scene_id: str) -> str | None:
    doc = await get(SCENE_INDEX, scene_id)
    return (doc or {}).get("scenario_id")


async def update(sc_id: str, fn: Callable[[dict[str, Any]], dict[str, Any] | None], *, retries: int = 15,
                 expected_rev: int | None = None) -> dict[str, Any]:
    """읽고-고치고-쓰기(낙관적 잠금). fn 은 사본을 고쳐 돌려준다(None 이면 쓰지 않음). fn 이 ApiError 를 던지면 그대로 올라간다."""
    st = store()
    for attempt in range(retries):
        cur = await asyncio.to_thread(st.get, SC, sc_id)
        if cur is None or cur.get("deleted_at"):
            raise not_found("시나리오", sc_id)
        if expected_rev is not None and cur["version"] != expected_rev:
            raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 시도해 주세요.",
                           {"rev": cur["version"]})
        new = fn(copy.deepcopy(cur))
        if new is None:
            return cur
        try:
            stored = await asyncio.to_thread(st.put, SC, sc_id, new, expected_version=cur["version"], keep_history=False)
        except VersionConflict:
            await asyncio.sleep(0.02 * (attempt + 1))
            continue
        await _index_scenes(sc_id, stored, cur)
        return stored
    raise ApiError(409, "CONFLICT", "다른 작업과 겹쳐 저장하지 못했어요. 다시 시도해 주세요.")


async def list_sc(where: dict[str, Any], limit: int = 500) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, SC, where=where, limit=limit)
    return [i for i in items if not i.get("deleted_at")]


# ── 장면 버전 ──────────────────────────────────────────────

def scene_version_id(scene_id: str, n: int) -> str:
    return f"{scene_id}:v{n}"


async def put_scene_version(scene_id: str, n: int, snapshot: dict[str, Any], reason: str, *, scenario_id: str) -> None:
    await put(SCENE_VERSIONS, scene_version_id(scene_id, n),
              {"scene_id": scene_id, "scenario_id": scenario_id, "n": n, "reason": reason, "scene": snapshot})


async def get_scene_version(scene_id: str, n: int) -> dict[str, Any] | None:
    return await get(SCENE_VERSIONS, scene_version_id(scene_id, n))


async def list_scene_versions(scene_id: str) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, SCENE_VERSIONS, where={"scene_id": scene_id}, order_by="created_at",
                                       limit=500)
    return sorted(items, key=lambda d: d.get("n", 0))


# ── 시나리오 저장 버전 ───────────────────────────────────────

def version_id(sc_id: str, n: int) -> str:
    return f"{sc_id}:v{n}"


async def put_version(sc_id: str, n: int, snapshot: dict[str, Any], note: str, author: str | None) -> dict[str, Any]:
    return await put(VERSIONS, version_id(sc_id, n), {"scenario_id": sc_id, "n": n, "note": note, "author": author,
                                                      "snapshot": snapshot})


async def get_version(sc_id: str, n: int) -> dict[str, Any] | None:
    return await get(VERSIONS, version_id(sc_id, n))


async def list_versions(sc_id: str) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, VERSIONS, where={"scenario_id": sc_id}, order_by="created_at", limit=500)
    return sorted(items, key=lambda d: d.get("n", 0))


# ── 내보내기 ──────────────────────────────────────────────

async def put_export(export_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await put(EXPORTS, export_id, data)


async def get_export(export_id: str) -> dict[str, Any] | None:
    return await get(EXPORTS, export_id)
