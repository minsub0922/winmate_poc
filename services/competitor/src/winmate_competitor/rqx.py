"""requirements 서비스 호출 — 정의서 스냅숏 읽기 · 사용 링크 등록(01-requirements.md §8.3 · §6).

정의서 → 4칸(§4.10): 고객사 = form.customer_name · 업종 = context.vertical(KR 업종) · 장소 = 지역 + context.spaces ·
제품 = context.products + context.solutions. `form.author_note`(제작자 의견, internal)는 문맥에만 쓰고 칸 값에 쓰지 않는다.
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.client import ServiceClient

log = logging.getLogger("winmate.competitor.rq")


async def snapshot(rq_id: str, version: int | None = None) -> dict[str, Any] | None:
    try:
        return await ServiceClient("requirements", timeout=30).get(f"/v1/requirements/{rq_id}/versions/{version or 'latest'}")
    except Exception as exc:  # noqa: BLE001 — 정의서 서비스가 없거나 계약 밖이어도 경쟁사 분석은 계속
        log.warning("정의서 스냅숏 실패 %s: %s", rq_id, exc)
        return None


async def register_link(rq_id: str, ca_id: str, *, title: str, route: str, rq_version: int, item_ids: list[str]) -> bool:
    body = {"title": (title or "경쟁사 분석")[:200], "route": route, "rq_version": int(rq_version or 0),
            "depends_on": [{"target": {"kind": "item", "id": i}, "places": [{"code": "CA", "label": "비교 기준 요구"}]} for i in item_ids[:200]]}
    try:
        await ServiceClient("requirements", timeout=30).put(f"/v1/requirements/{rq_id}/links/competitor/{ca_id}", json=body)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("정의서 링크 등록 실패 %s/%s: %s", rq_id, ca_id, exc)
        return False


def _val(field: Any) -> str | None:
    if isinstance(field, dict):
        v = field.get("value")
        return str(v).strip() if v else None
    return str(field).strip() if field else None


def read(snap: dict[str, Any]) -> dict[str, Any]:
    """스냅숏 → {customer, vertical{top2, ask}, spaces[], products[], solutions[], items[{id, code, text, weight}], project_name, author_note, scale_text}."""
    s = snap.get("snapshot") or {}
    form = s.get("form") or {}
    ctx = s.get("context") or {}
    customer = snap.get("customer_name") or _val(form.get("customer_name"))
    note = _val((s.get("author_note") or {})) or _val(form.get("author_note"))
    items = [{"id": it.get("id"), "code": it.get("code"), "text": it.get("text") or "", "weight": it.get("keyman_weight"),
              "short": it.get("short")} for it in s.get("items_flat") or []]
    return {
        "customer": customer,
        "project_name": snap.get("project_name") or _val(form.get("project_name")) or snap.get("title"),
        "title": snap.get("title"),
        "vertical": ctx.get("vertical") or None,
        "spaces": [x.get("name") for x in ctx.get("spaces") or [] if x.get("name")],
        "products": [x.get("name") for x in ctx.get("products") or [] if x.get("name")],
        "solutions": [x.get("name") for x in ctx.get("solutions") or [] if x.get("name")],
        "scale_text": ctx.get("scale_text"),
        "items": items,
        "author_note": note,
        "version": snap.get("version"),
        "project_id": snap.get("project_id"),
    }
