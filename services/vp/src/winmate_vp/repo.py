"""저장소 — DocStore.for_service("vp") (data/vp/vp.sqlite) 위의 얇은 층.

컬렉션(05-vp.md §5.1 의 표를 문서 하나에 모았다)
- vps            작업 문서(vp_ …) — sources · attachments · materials · fixes · questions · decisions · plan · sheets · variants ·
                 image_slots · checks · layout_requests · pack_offers 가 모두 이 문서 안에 있다(vp_source … vp_pack_offer 표)
- vp_versions    저장 지점 스냅숏(`{vp_id}:v{n}`, 불변) — vp_version 표
- handoffs       넘김(vho_ …) — vp_handoff 표
- exports        내보내기(vex_ …) — vp_export 표
- asset_usage    이미지 사용 이력(`{asset_key}`) — vp_asset_usage 표
- industry_packs 업종판 상태(문서 하나 `state`) — industry_pack 표

REST 와 워커가 같은 문서를 고치므로 쓰기는 `update(vp_id, fn)`(낙관적 잠금 + 재시도)로만 한다.
"""
from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable
from typing import Any

from winmate_common.env import settings
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.store import DocStore, VersionConflict

VPS = "vps"
VERSIONS = "vp_versions"
HANDOFFS = "handoffs"
EXPORTS = "exports"
USAGE = "asset_usage"
PACKS = "industry_packs"

_stores: dict[str, DocStore] = {}


def store() -> DocStore:
    path = settings().service_data_dir("vp") / "vp.sqlite"
    key = str(path)
    st = _stores.get(key)
    if st is None:
        st = DocStore(path)
        for f in ("owner_id", "archived", "status", "customer_name"):
            st.index(VPS, f)
        st.index(VERSIONS, "vp_id")
        st.index(HANDOFFS, "vp_id")
        st.index(EXPORTS, "vp_id")
        _stores[key] = st
    return st


def not_found(what: str, ident: str) -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what}을(를) 찾을 수 없어요: {ident}", {"resource": what, "id": ident})


async def get(collection: str, doc_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(store().get, collection, doc_id)


async def put(collection: str, doc_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(store().put, collection, doc_id, data, keep_history=False)


async def get_vp(vp_id: str) -> dict[str, Any] | None:
    if not vp_id.startswith("vp_"):
        return None
    return await get(VPS, vp_id)


async def require_vp(vp_id: str) -> dict[str, Any]:
    doc = await get_vp(vp_id)
    if doc is None:
        raise not_found("가치 제안", vp_id)
    return doc


async def create_vp(vp_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return await asyncio.to_thread(store().put, VPS, vp_id, data, keep_history=False)


async def update(vp_id: str, fn: Callable[[dict[str, Any]], dict[str, Any] | None], *, retries: int = 16) -> dict[str, Any]:
    """읽고-고치고-쓰기(낙관적 잠금). fn 은 사본을 고쳐 돌려준다(None 이면 쓰지 않음). fn 이 ApiError 를 던지면 그대로 올라간다."""
    st = store()
    for attempt in range(retries):
        cur = await asyncio.to_thread(st.get, VPS, vp_id)
        if cur is None:
            raise not_found("가치 제안", vp_id)
        new = fn(copy.deepcopy(cur))
        if new is None:
            return cur
        try:
            return await asyncio.to_thread(st.put, VPS, vp_id, new, expected_version=cur["version"], keep_history=False)
        except VersionConflict:
            await asyncio.sleep(0.02 * (attempt + 1))
    raise ApiError(409, "CONFLICT", "다른 작업과 겹쳐 저장하지 못했어요. 다시 시도해 주세요.")


async def list_vps(where: dict[str, Any], limit: int = 1000) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, VPS, where=where, limit=limit)
    return items


# ── 저장 지점 ──────────────────────────────────────────────

def version_id(vp_id: str, n: int) -> str:
    return f"{vp_id}:v{n}"


async def put_version(vp_id: str, n: int, snapshot: dict[str, Any], reason: str) -> None:
    body = {"vp_id": vp_id, "n": n, "reason": reason, "doc": snapshot, "saved_at": now_iso()}
    await put(VERSIONS, version_id(vp_id, n), body)


async def get_version(vp_id: str, n: int) -> dict[str, Any] | None:
    return await get(VERSIONS, version_id(vp_id, n))


async def list_versions(vp_id: str) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, VERSIONS, where={"vp_id": vp_id}, order_by="created_at", limit=1000)
    return sorted(items, key=lambda d: int(d.get("n") or 0))


# ── 넘김 · 내보내기 · 사용 이력 · 업종판 ─────────────────────

async def get_handoff(vho: str) -> dict[str, Any] | None:
    return await get(HANDOFFS, vho) if vho.startswith("vho_") else None


async def put_handoff(vho: str, data: dict[str, Any]) -> dict[str, Any]:
    return await put(HANDOFFS, vho, data)


async def list_handoffs(vp_id: str) -> list[dict[str, Any]]:
    items, _ = await asyncio.to_thread(store().list, HANDOFFS, where={"vp_id": vp_id}, limit=200)
    return items


async def put_export(vex: str, data: dict[str, Any]) -> dict[str, Any]:
    return await put(EXPORTS, vex, data)


async def get_export(vex: str) -> dict[str, Any] | None:
    return await get(EXPORTS, vex)


async def usage_count(asset_key: str) -> int:
    doc = await get(USAGE, asset_key)
    return int((doc or {}).get("count") or 0)


async def add_usage(asset_key: str, vp_id: str, handoff_id: str | None) -> int:
    def fn() -> int:
        st = store()
        for _ in range(8):
            cur = st.get(USAGE, asset_key)
            uses = list((cur or {}).get("uses") or [])
            if any(u.get("handoff_id") == handoff_id and u.get("vp_id") == vp_id for u in uses) and handoff_id:
                return len({u.get("handoff_id") for u in uses})
            uses.append({"vp_id": vp_id, "handoff_id": handoff_id, "used_at": now_iso()})
            body = {"asset_key": asset_key, "uses": uses, "count": len({u.get("handoff_id") or u.get("used_at") for u in uses})}
            try:
                st.put(USAGE, asset_key, body, expected_version=(cur or {}).get("version") or 0, keep_history=False)
                return int(body["count"])
            except VersionConflict:
                continue
        return 0
    return await asyncio.to_thread(fn)


async def pack_state() -> dict[str, dict[str, Any]]:
    doc = await get(PACKS, "state")
    return dict((doc or {}).get("packs") or {})


async def pack_status_map() -> dict[str, str]:
    return {k: str(v.get("status", "in_production")) for k, v in (await pack_state()).items()}


async def set_pack(code: str, status: str) -> dict[str, dict[str, Any]]:
    def fn() -> dict[str, dict[str, Any]]:
        st = store()
        for _ in range(8):
            cur = st.get(PACKS, "state")
            packs = dict((cur or {}).get("packs") or {})
            packs[code] = {"status": status, "released_at": now_iso() if status == "ready" else None}
            try:
                st.put(PACKS, "state", {"packs": packs}, expected_version=(cur or {}).get("version") or 0, keep_history=False)
                return packs
            except VersionConflict:
                continue
        return packs
    return await asyncio.to_thread(fn)
