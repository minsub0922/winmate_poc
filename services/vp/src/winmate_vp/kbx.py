"""kb 질의 — 계약(contracts/kb.json)대로 `ServiceClient("kb")` 로만. 실패하면 빈 결과(작업은 계속)."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.client import ServiceClient

log = logging.getLogger("winmate.vp.kb")


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


async def link_entities(text: str) -> list[dict[str, Any]]:
    """A1 — 제품 · 솔루션 · 분류 링크([{type, id, name, surface}])."""
    if not text.strip():
        return []
    r = await result("A1", {"text": text[:2000]})
    return [x for x in r.get("links") or [] if x.get("type") in ("family", "model", "solution", "category", "space_type")]


async def similar_cases(*, vertical: str | None, text: str, targets: list[dict[str, str]] | None = None, limit: int = 5) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"text": text[:1500] or None, "limit": limit}
    if vertical:
        body["vertical"] = vertical
    if targets:
        body["targets"] = targets
    r = await result("D1", body)
    return list(r.get("deployments") or [])


async def case_stats(vertical: str) -> dict[str, Any]:
    return await result("D2", {"vertical": vertical})


async def case_kpis(deployment_ids: list[str]) -> list[dict[str, Any]]:
    if not deployment_ids:
        return []
    r = await result("D3", {"deployment_ids": deployment_ids[:20]})
    return list(r.get("kpis") or [])


async def case_detail(dep_id: str) -> dict[str, Any] | None:
    d = await get(f"/v1/cases/{dep_id}")
    return d if isinstance(d, dict) else None


async def messages(*, vertical: str | None, products: list[dict[str, str]] | None, customer: str | None, text: str) -> dict[str, Any]:
    body: dict[str, Any] = {"text": text[:1500] or None, "customer": customer, "limit": 8}
    if vertical:
        body["vertical"] = vertical
    if products:
        body["products"] = products
    return await result("E3", body)


async def theme_messages(theme: str) -> list[dict[str, Any]]:
    r = await result("E2", {"theme": theme[:300], "limit": 6})
    return list(r.get("messages") or r.get("items") or [])


async def product_images(family_id: str, limit: int = 6) -> list[dict[str, Any]]:
    r = await result("G4", {"family_id": family_id, "limit": limit})
    return list(r.get("images") or [])


async def subject_images(kind: str, ident: str, limit: int = 8) -> list[dict[str, Any]]:
    r = await result("G2", {"kind": kind, "ident": ident, "limit": limit})
    return list(r.get("images") or [])


async def space_images(space: str, *, category: str | None = None, vertical: str | None = None, limit: int = 6) -> tuple[list[dict[str, Any]], str | None]:
    q = await query("G1", {"space": space, "category": category, "vertical": vertical, "limit": limit})
    r = q.get("result") if isinstance(q.get("result"), dict) else {}
    return list((r or {}).get("images") or []), (q.get("fallback_level") or (r or {}).get("level"))


async def case_images(deployment_id: str, limit: int = 6) -> list[dict[str, Any]]:
    r = await result("G5", {"deployment_id": deployment_id, "limit": limit})
    return list(r.get("images") or [])


async def solution_images(solution_catalog_id: str) -> list[dict[str, Any]]:
    d = await get(f"/v1/solutions/{solution_catalog_id}/images")
    out: list[dict[str, Any]] = []
    for g in (d or {}).get("groups") or []:
        for it in g.get("items") or []:
            out.append({**it, "group": g.get("key")})
    return out


async def image_meta(image_id: str) -> dict[str, Any] | None:
    d = await get(f"/v1/images/{image_id}")
    return d if isinstance(d, dict) else None


async def solutions_index() -> dict[str, dict[str, Any]]:
    """kb_id(sol_magicinfo) → {catalog id(magicinfo), name}."""
    d = await get("/v1/solutions", {"limit": 100})
    out: dict[str, dict[str, Any]] = {}
    for s in (d or {}).get("items") or []:
        if s.get("kb_id"):
            out[s["kb_id"]] = {"id": s["id"], "name": s.get("name") or s["id"]}
    return out


async def product_search(q: str, limit: int = 3) -> list[dict[str, Any]]:
    d = await get("/v1/products/search", {"q": q, "limit": limit})
    return list((d or {}).get("items") or [])


async def segments_classify(text: str) -> list[dict[str, Any]]:
    """MI 판별기를 못 부를 때의 대체(빠른 경로 `0.6 × kb + 0.4 × 단서`)."""
    try:
        d = await _kb().post("/v1/segments/classify", json={"text": text[:4000]})
    except Exception as exc:  # noqa: BLE001
        log.warning("kb segments/classify 실패: %s", exc)
        return []
    out = []
    for it in (d or {}).get("items") or []:
        conf = round(0.6 * float(it.get("kb_score") or 0) + 0.4 * float(it.get("clue_score") or 0), 2)
        out.append({"code": it["code"], "confidence": conf, "clues": [c.get("text") for c in it.get("clues") or []]})
    return sorted(out, key=lambda x: -x["confidence"])
