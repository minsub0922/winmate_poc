"""KB 질의(kb 서비스 계약 `contracts/kb.json`) — 실패하면 빈 값으로 내려간다(화면 · 잡이 멈추지 않게).

A1 문장 → 제품 · 솔루션 · 공간 · 역량, A2 업종 판별, B1 업종 장면, C2 공간 후보 제품군, D1 유사 사례(사례 수), D5 솔루션 공존 제품,
E1 솔루션 메시지(근거). 경로 `/v1/query/<패턴>` 은 internal(서비스 간)이다.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from winmate_common.client import ServiceClient

log = logging.getLogger("winmate.scenario.kb")

_cache: dict[str, tuple[float, Any]] = {}
TTL = 300.0


def _kb() -> ServiceClient:
    return ServiceClient("kb", timeout=20)


async def query(code: str, body: dict[str, Any]) -> dict[str, Any]:
    try:
        res = await _kb().post(f"/v1/query/{code}", json=body)
        return (res or {}).get("result") or {}
    except Exception as exc:  # noqa: BLE001
        log.info("kb %s 실패: %s", code, exc)
        return {}


async def a1(text: str) -> list[dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return []
    res = await query("A1", {"text": t[:2000]})
    return list(res.get("links") or [])


async def a2(text: str) -> list[dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return []
    try:
        res = await _kb().post("/v1/query/A2", json={"text": t[:2000]})
    except Exception as exc:  # noqa: BLE001
        log.info("kb A2 실패: %s", exc)
        return []
    result = (res or {}).get("result") or {}
    cands = result.get("candidates") or (res or {}).get("candidates") or result.get("top") or []
    return [c for c in cands if isinstance(c, dict)]


async def b1(vertical: str) -> dict[str, Any]:
    return await query("B1", {"vertical_id": vertical})


async def c2(*, space: str | None = None, vertical: str | None = None, category: str | None = None, text: str | None = None,
             limit: int = 15) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"capabilities": [], "limit": limit}
    if space:
        body["space"] = space
    if vertical:
        body["vertical"] = vertical
    if category:
        body["category"] = category
    if text:
        body["text"] = text[:500]
    res = await query("C2", body)
    return list(res.get("families") or [])


async def d1(*, vertical: str | None, targets: list[list[str]], limit: int = 50) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"targets": targets, "limit": limit}
    if vertical:
        body["vertical"] = vertical
    res = await query("D1", body)
    return list(res.get("deployments") or [])


async def case_count(vertical: str | None, solution_kb_id: str | None) -> int | None:
    """D1(vertical, targets=[('solution', id)]) 중 그 솔루션이 실제로 나온 사례 수. 셀 수 없으면 None(화면은 「[00]」)."""
    if not vertical or not solution_kb_id:
        return None
    deps = await d1(vertical=vertical, targets=[["solution", solution_kb_id]])
    n = sum(1 for d in deps if ((d.get("similarity_breakdown") or {}).get("product") or 0) > 0
            and ((d.get("similarity_breakdown") or {}).get("vertical") or 0) > 0)
    return n or None


async def d5(targets: list[list[str]]) -> list[dict[str, Any]]:
    if not targets:
        return []
    res = await query("D5", {"targets": targets})
    return list(res.get("co_items") or [])


async def e1(solution_kb_id: str, vertical: str | None = None) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"about": [["solution", solution_kb_id]]}
    if vertical:
        body["vertical"] = vertical
    res = await query("E1", body)
    msgs = res.get("messages") or res.get("items") or []
    return [m for m in msgs if isinstance(m, dict)]


async def products_search(q: str, limit: int = 5) -> list[dict[str, Any]]:
    if not (q or "").strip():
        return []
    try:
        res = await _kb().get("/v1/products/search", params={"q": q.strip()[:80], "limit": limit})
        return list((res or {}).get("items") or [])
    except Exception as exc:  # noqa: BLE001
        log.info("kb 제품 검색 실패: %s", exc)
        return []


async def model_detail(key: str) -> dict[str, Any] | None:
    """`/v1/models/{model_code}` — 모델코드 · mdl_ · fam_(대표 모델) 모두 받는다(셸 참조만 온 제품의 이름 찾기)."""
    if not key:
        return None
    hit = _cache.get(f"model:{key}")
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    try:
        res = await _kb().get(f"/v1/models/{key}")
    except Exception as exc:  # noqa: BLE001
        log.info("kb 모델 읽기 실패 %s: %s", key, exc)
        return None
    if isinstance(res, dict):
        _cache[f"model:{key}"] = (time.time(), res)
        return res
    return None


async def solutions_catalog() -> list[dict[str, Any]]:
    hit = _cache.get("solutions")
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    try:
        res = await _kb().get("/v1/solutions", params={"limit": 50})
        items = list((res or {}).get("items") or [])
    except Exception as exc:  # noqa: BLE001
        log.info("kb 솔루션 목록 실패: %s", exc)
        items = []
    if items:
        _cache["solutions"] = (time.time(), items)
    return items
