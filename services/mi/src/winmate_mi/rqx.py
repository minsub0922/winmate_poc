"""requirements 서비스 호출 — 정의서 스냅숏 읽기 · 사용 링크 등록(01-requirements.md §5.8 · §5.9 · §6.5 · §6.8)."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.client import ServiceClient

log = logging.getLogger("winmate.mi.rq")


async def snapshot(rq_id: str, version: int | None = None) -> dict[str, Any] | None:
    """GET /v1/requirements/{rq}/versions/{n|latest}. 못 읽으면 None(연결은 남기고 계속)."""
    try:
        return await ServiceClient("requirements", timeout=30).get(f"/v1/requirements/{rq_id}/versions/{version or 'latest'}")
    except Exception as exc:  # noqa: BLE001 — 정의서 서비스가 없거나 계약 밖이어도 MI 는 계속
        log.warning("정의서 스냅숏 실패 %s: %s", rq_id, exc)
        return None


async def register_link(rq_id: str, mi_id: str, *, title: str, route: str, rq_version: int, item_ids: list[str]) -> bool:
    body = {"title": title[:200] or "Market Intelligence", "route": route, "rq_version": int(rq_version or 0),
            "depends_on": [{"target": {"kind": "item", "id": i}, "places": [{"code": "MI", "label": "분석 기준 요구"}]} for i in item_ids[:200]]}
    try:
        await ServiceClient("requirements", timeout=30).put(f"/v1/requirements/{rq_id}/links/mi/{mi_id}", json=body)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("정의서 링크 등록 실패 %s/%s: %s", rq_id, mi_id, exc)
        return False


def fill_from_snapshot(doc: dict[str, Any], snap: dict[str, Any]) -> None:
    """정의서 스냅숏 → 고객사 · 요구사항(가중치 포함) · 내부 메모(작성자 의견은 요구사항 칸에 넣지 않음) · 업종 맥락."""
    s = snap.get("snapshot") or {}
    form = s.get("form") or {}
    cust = snap.get("customer_name") or ((form.get("customer_name") or {}).get("value"))
    if cust and not doc.get("customer_name"):
        doc["customer_name"] = cust[:60]
    reqs = [r for r in doc.get("requirements") or [] if r.get("origin") != "definition"]
    for it in s.get("items_flat") or []:
        reqs.append({"id": it.get("id"), "text": it.get("text", ""), "weight": it.get("keyman_weight"), "origin": "definition",
                     "label": it.get("short"), "code": it.get("code")})
    doc["requirements"] = reqs
    if not (doc.get("requirements_text") or "").strip():
        doc["requirements_text"] = "\n".join(f"{it.get('code', '')} {it.get('text', '')}".strip() for it in s.get("items_flat") or [])[:4000]
    ext = doc.setdefault("extracted", {})
    note = (s.get("author_note") or {}).get("value") or ((form.get("author_note") or {}).get("value"))
    if note:
        ext["author_note"] = note           # 내부용 — 분석 문맥에만
    ext["rq_context"] = s.get("context") or {}
    ext["rq_title"] = snap.get("title")
    links = doc.setdefault("links", {})
    links["rq_version"] = snap.get("version")
    if snap.get("project_id") and not doc.get("project_id"):
        doc["project_id"] = snap.get("project_id")
