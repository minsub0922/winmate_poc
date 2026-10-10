"""kb 질의 — 계약(contracts/kb.json)대로 `ServiceClient("kb")` 로만. 실패하면 빈 결과(작업은 계속).

DSS 가 쓰는 것
- A2 업종 판별(KR 업종 top-2 · ask) · S1 요구 문장 → 공간별 후보 제품군 · 솔루션
- /v1/space-types?vertical_id= 업종 기본 공간 · /v1/products/search 모델 · 제품군 검색
- /v1/solutions(카탈로그) · /v1/solutions/{id}(지원 기기 제품군 · 분류) — 솔루션 상세는 프로세스 안에 잠깐 기억한다
"""
from __future__ import annotations

import logging
import time
from typing import Any

from winmate_common.client import ServiceClient

log = logging.getLogger("winmate.dss.kb")

_TTL = 300.0
_cache: dict[str, tuple[float, Any]] = {}


def _kb() -> ServiceClient:
    return ServiceClient("kb", timeout=60)


async def query(code: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        res = await _kb().post(f"/v1/query/{code}", json=body)
        return res or {}
    except Exception as exc:  # noqa: BLE001 — kb 장애가 작업을 막지 않는다
        log.warning("kb %s 실패: %s", code, exc)
        return {}


async def result(code: str, body: dict[str, Any]) -> dict[str, Any]:
    r = (await query(code, body)).get("result")
    return r if isinstance(r, dict) else {}


async def get(path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        return await _kb().get(path, params=params)
    except Exception as exc:  # noqa: BLE001
        log.warning("kb GET %s 실패: %s", path, exc)
        return None


async def _cached(key: str, fn: Any) -> Any:
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < _TTL:
        return hit[1]
    val = await fn()
    if val:
        _cache[key] = (time.monotonic(), val)
    return val


async def industry(text: str) -> dict[str, Any]:
    """A2 응답 전체 — result{top2[{id, name, score, signals}], ask} · candidates[{id, score, reasons}](정규화 점수 상위)."""
    if not text.strip():
        return {}
    return await query("A2", {"text": text[:4000]})


async def spaces_products(text: str, limit: int = 6) -> dict[str, Any]:
    """S1 — {vertical[], by_space[{space, space_name, clauses, category_name, families[], solutions[]}], …}."""
    if not text.strip():
        return {}
    return await result("S1", {"text": text[:4000], "limit": limit})


async def space_types(vertical_id: str | None) -> list[dict[str, Any]]:
    if not vertical_id:
        return []
    d = await _cached(f"st:{vertical_id}", lambda: get("/v1/space-types", {"vertical_id": vertical_id}))
    return list((d or {}).get("items") or [])


async def product_search(q: str, limit: int = 5) -> list[dict[str, Any]]:
    d = await get("/v1/products/search", {"q": q, "limit": limit})
    return list((d or {}).get("items") or [])


async def solutions() -> list[dict[str, Any]]:
    """솔루션 카탈로그(id · name · domain · desc · kb_id · industries)."""
    d = await _cached("solutions", lambda: get("/v1/solutions", {"limit": 100}))
    return list((d or {}).get("items") or [])


async def solution_detail(sol_id: str) -> dict[str, Any] | None:
    d = await _cached(f"sol:{sol_id}", lambda: get(f"/v1/solutions/{sol_id}"))
    return d if isinstance(d, dict) else None
