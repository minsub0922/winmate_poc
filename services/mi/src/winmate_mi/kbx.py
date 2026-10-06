"""kb 서비스 호출(게이트웨이 경유 · 계약 검증). 업종 목록 · 인사이트 · 분류 · 질의 패턴 · 스펙 표 · 사례."""
from __future__ import annotations

import logging
import time
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.mi.kb")

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
    return await _cached("segments", lambda: _kb().get("/v1/segments"))


async def insights(code: str) -> dict[str, Any]:
    return await _cached(f"ins:{code}", lambda: _kb().get(f"/v1/segments/{code}/insights"))


async def classify(text: str) -> dict[str, Any]:
    return await _kb().post("/v1/segments/classify", json={"text": text[:6000] or "-"})


async def meta() -> dict[str, Any]:
    return await _cached("meta", lambda: _kb().get("/v1/meta"))


async def kb_version() -> str:
    try:
        return str((await meta()).get("kb_version") or "")
    except ApiError:
        return ""


async def query(pattern: str, body: dict[str, Any]) -> dict[str, Any]:
    return await _kb().post(f"/v1/query/{pattern}", json=body)


async def safe_query(pattern: str, body: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return await query(pattern, body)
    except ApiError as exc:
        log.warning("kb %s 실패: %s", pattern, exc)
        return None


async def spec_table(models: list[str]) -> dict[str, Any] | None:
    try:
        return await _kb().post("/v1/spec/table", json={"models": models[:20]})
    except ApiError as exc:
        log.warning("kb spec table 실패: %s", exc)
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


async def solution(sol_id: str) -> dict[str, Any] | None:
    try:
        return await _kb().get(f"/v1/solutions/{sol_id}")
    except ApiError:
        return None


async def model(code: str) -> dict[str, Any] | None:
    try:
        return await _cached(f"model:{code}", lambda: _kb().get(f"/v1/models/{code}"))
    except ApiError:
        return None


# ── 화면 · 그래프 공용 모양 ──────────────────────────────
def req_labels(req_types: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """kb 요구 태그 이름표(label)가 없으면(§11 Q2) 그 태그 사례 문장 중 아직 안 쓴 첫 문장을 이름으로 쓴다."""
    used: set[str] = set()
    out = []
    for rt in req_types:
        label = rt.get("label")
        basis = "kb"
        if not label:
            basis = "example"
            label = next((e for e in rt.get("examples") or [] if e not in used), None) or rt.get("code", "")
        used.add(label)
        out.append({"code": rt.get("code", ""), "label": label, "n": int(rt.get("n") or 0), "examples": rt.get("examples") or [],
                    "label_basis": basis})
    return out


async def insights_view(code: str) -> dict[str, Any]:
    """MI1I · MI2C · 설계가 함께 쓰는 업종 인사이트(요구 상위 6 · 제품 4 · 솔루션 4 · 업종 레이아웃 3)."""
    from . import config

    s = config.segment(code)
    try:
        ins = await insights(code)
    except ApiError:
        ins = {"cases": 0, "req_types": [], "products": [], "solutions": [], "gaps": ["kb 서비스에 닿지 못했어요"]}
    return {"code": code, "full": s["full"], "short": s["short"], "cases": int(ins.get("cases") or 0),
            "case_ids": list(ins.get("case_ids") or []),
            "req_types": req_labels(list(ins.get("req_types") or [])[:6]),
            "products": [{"name": p["name"], "n": int(p.get("n") or 0), "id": p.get("id"), "kind": p.get("kind")} for p in (ins.get("products") or [])[:4]],
            "solutions": [{"name": p["name"], "n": int(p.get("n") or 0), "id": p.get("id"), "kind": p.get("kind")} for p in (ins.get("solutions") or [])[:4]],
            "layouts": [f"MI-{code}-A", f"MI-{code}-B", f"MI-{code}-C"], "gaps": list(ins.get("gaps") or [])}


# ── 질의 패턴 도우미(실패하면 빈 값) ─────────────────────
async def similar_cases(text: str, *, vertical: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """D1 — 요구 문장 · 업종 → 유사 사례(dep_…)."""
    body: dict[str, Any] = {"text": (text or "-")[:600], "limit": limit}
    if vertical:
        body["vertical"] = vertical
    res = await safe_query("D1", body)
    return list(((res or {}).get("result") or {}).get("deployments") or [])[:limit]


async def vertical_stats(vertical: str) -> dict[str, Any]:
    """D2 — KR 업종 → 사례 수 · 많이 쓴 제품 · 공간 · 요구 태그."""
    res = await safe_query("D2", {"vertical": vertical})
    return dict((res or {}).get("result") or {})


async def recommend(text: str, limit: int = 3) -> dict[str, Any]:
    """S1 — 요구 → 공간별 추천 제품군."""
    res = await safe_query("S1", {"text": (text or "-")[:600], "limit": limit})
    return dict((res or {}).get("result") or {})


async def messages(theme: str, limit: int = 5) -> list[dict[str, Any]]:
    """E2 — 테마 → 삼성 메시지 · proof point."""
    res = await safe_query("E2", {"theme": theme[:80] or "-", "limit": limit})
    return list(((res or {}).get("result") or {}).get("messages") or [])
