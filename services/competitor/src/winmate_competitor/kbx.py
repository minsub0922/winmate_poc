"""kb 서비스 호출(게이트웨이 경유 · 계약 검증) — 업종 목록 · 인사이트 · 판별 근거 · 질의 패턴(A1 · S1 · E2 · search) · 스펙 표 · 솔루션.

모든 도우미는 실패하면 빈 값(경쟁사 분석은 KB 없이도 계속 — 삼성 칸은 `[확인 필요]`).
"""
from __future__ import annotations

import logging
import time
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.competitor.kb")

_cache: dict[str, tuple[float, Any]] = {}
TTL = 600.0


def _kb() -> ServiceClient:
    return ServiceClient("kb", timeout=60)


async def _cached(key: str, fn: Any) -> Any:
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    val = await fn()
    _cache[key] = (time.time(), val)
    return val


def clear_cache() -> None:
    _cache.clear()


async def segments() -> dict[str, Any]:
    try:
        return await _cached("segments", lambda: _kb().get("/v1/segments"))
    except ApiError as exc:
        log.warning("kb segments 실패: %s", exc)
        return {"items": [], "total_cases": 0}


async def insights(code: str) -> dict[str, Any]:
    if not code or code == "GEN":
        return {"cases": 0, "req_types": [], "products": [], "solutions": [], "case_ids": []}
    try:
        return await _cached(f"ins:{code}", lambda: _kb().get(f"/v1/segments/{code}/insights"))
    except ApiError as exc:
        log.warning("kb insights %s 실패: %s", code, exc)
        return {"cases": 0, "req_types": [], "products": [], "solutions": [], "case_ids": []}


async def classify(text: str) -> dict[str, Any] | None:
    try:
        return await _kb().post("/v1/segments/classify", json={"text": (text or "-")[:6000]})
    except ApiError as exc:
        log.warning("kb classify 실패: %s", exc)
        return None


async def query(pattern: str, body: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return await _kb().post(f"/v1/query/{pattern}", json=body)
    except ApiError as exc:
        log.warning("kb %s 실패: %s", pattern, exc)
        return None


async def a1(text: str) -> list[dict[str, Any]]:
    """A1 — 문장 → 카테고리 · 제품군 · 모델 · 솔루션 · 공간 링크."""
    res = await query("A1", {"text": (text or "-")[:1500]})
    return list(((res or {}).get("result") or {}).get("links") or [])


async def s1(text: str, limit: int = 3) -> dict[str, Any]:
    res = await query("S1", {"text": (text or "-")[:600], "limit": limit})
    return dict((res or {}).get("result") or {})


async def e2(theme: str, limit: int = 5) -> list[dict[str, Any]]:
    res = await query("E2", {"theme": (theme or "-")[:80], "limit": limit})
    return list(((res or {}).get("result") or {}).get("messages") or [])


async def search(text: str, k: int = 4) -> list[dict[str, Any]]:
    res = await query("search", {"text": (text or "-")[:400], "k": k})
    return list(((res or {}).get("result") or {}).get("chunks") or [])


async def spec_table(models: list[str]) -> dict[str, Any] | None:
    if not models:
        return None
    try:
        return await _cached("spec:" + ",".join(models), lambda: _kb().post("/v1/spec/table", json={"models": models[:10]}))
    except ApiError as exc:
        log.warning("kb spec table 실패: %s", exc)
        return None


async def solution(sol_id: str) -> dict[str, Any] | None:
    sid = sol_id.removeprefix("sol_")
    try:
        return await _cached(f"sol:{sid}", lambda: _kb().get(f"/v1/solutions/{sid}"))
    except ApiError:
        return None


async def model(code: str) -> dict[str, Any] | None:
    try:
        return await _cached(f"model:{code}", lambda: _kb().get(f"/v1/models/{code}"))
    except ApiError:
        return None


async def case(case_id: str) -> dict[str, Any] | None:
    try:
        return await _cached(f"case:{case_id}", lambda: _kb().get(f"/v1/cases/{case_id}"))
    except ApiError:
        return None


async def product_search(q: str, limit: int = 3) -> list[dict[str, Any]]:
    try:
        res = await _kb().get("/v1/products/search", params={"q": q, "limit": limit})
        return list(res.get("items") or [])
    except ApiError:
        return []


def req_type_name(rt: dict[str, Any], used: set[str]) -> str:
    """kb 요구 태그 이름표(label)가 없으면(KB 갭 — R01~R24 이름표 없음) 그 태그 사례 문장 중 안 쓴 첫 문장을 이름으로 쓴다."""
    label = rt.get("label")
    if label:
        return str(label)
    for e in rt.get("examples") or []:
        if e not in used:
            return str(e)
    return str(rt.get("code") or "")
