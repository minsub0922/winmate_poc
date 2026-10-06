"""kb 질의(contracts/kb.json `POST /v1/query/{code}`) — 근거 · 후보 맥락. 실패해도 작업은 계속한다(빈 결과)."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.client import ServiceClient

log = logging.getLogger("winmate.storyboard.kb")


async def query(code: str, body: dict[str, Any]) -> dict[str, Any] | None:
    try:
        env = await ServiceClient("kb", timeout=60).post(f"/v1/query/{code}", json=body)
    except Exception as exc:  # noqa: BLE001
        log.warning("kb %s 실패: %s", code, exc)
        return None
    res = (env or {}).get("result")
    return res if isinstance(res, dict) else None


async def vertical_for(text: str) -> tuple[str | None, str | None]:
    """A2 업종 판별 → (KR 업종 id, 이름). 애매하면(ask) None."""
    if not text.strip():
        return None, None
    res = await query("A2", {"text": text[:2000]})
    if not res or res.get("ask"):
        return None, None
    top = res.get("top2") or []
    if top and isinstance(top[0], dict):
        return top[0].get("id"), top[0].get("name")
    return None, None


async def preset(vertical_id: str) -> dict[str, Any]:
    """B1 업종 프리셋 — 공간 시퀀스 · 장면 · 추천 솔루션."""
    return await query("B1", {"vertical_id": vertical_id}) or {}


def preset_spaces(preset_result: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    for s in preset_result.get("space_sequence") or []:
        if isinstance(s, dict) and s.get("name"):
            out.append({"key": s.get("space_type") or "", "name": s["name"]})
    return out


def scene_lines(preset_result: dict[str, Any], limit: int = 8) -> list[str]:
    out = []
    for sc in (preset_result.get("scenes") or [])[:limit]:
        if isinstance(sc, dict) and sc.get("title"):
            desc = sc.get("description") or ""
            out.append(f"{sc['title']}: {desc}"[:200])
    return out


async def recommend(text: str, limit: int = 6) -> list[dict[str, Any]]:
    """S1 요구 → 공간별 추천 — [{space, space_name, families[{name}], solutions[{name}]}]."""
    res = await query("S1", {"text": text[:2000], "limit": limit}) or {}
    out = []
    for b in res.get("by_space") or []:
        if not isinstance(b, dict):
            continue
        out.append({
            "space": b.get("space"), "space_name": b.get("space_name"),
            "families": [{"id": f.get("id"), "name": f.get("name")} for f in (b.get("families") or [])[:4] if isinstance(f, dict)],
            "solutions": [{"id": s.get("id"), "name": s.get("name")} for s in (b.get("solutions") or [])[:3] if isinstance(s, dict)],
        })
    return out


async def messages_for(vertical: str | None, spaces: list[str], text: str, limit: int = 6) -> list[str]:
    """E3 맥락 → 원문 메시지 후보(헤드라인 · 핵심 메시지)."""
    body: dict[str, Any] = {"spaces": spaces[:6], "text": text[:1500], "limit": limit}
    if vertical:
        body["vertical"] = vertical
    res = await query("E3", body) or {}
    out = []
    for key in ("headline", "key_messages"):
        for m in res.get(key) or []:
            if isinstance(m, dict) and m.get("text"):
                out.append(m["text"])
    return out[: limit * 2]


async def theme_messages(theme: str, limit: int = 5) -> list[str]:
    res = await query("E2", {"theme": theme[:300], "limit": limit}) or {}
    out = []
    for key in ("messages", "items", "results"):
        for m in res.get(key) or []:
            if isinstance(m, dict) and m.get("text"):
                out.append(m["text"])
    return out[:limit]


async def scene(vertical: str | None, space_key: str | None) -> list[str]:
    """S2 업종 → 장면 구성(이 공간)."""
    if not vertical:
        return []
    body: dict[str, Any] = {"vertical": vertical}
    if space_key:
        body["space"] = space_key
    res = await query("S2", body) or {}
    out = []
    for sc in res.get("scenes") or []:
        if isinstance(sc, dict):
            title = sc.get("title") or ""
            items = ", ".join(i.get("name", "") for i in (sc.get("items") or []) if isinstance(i, dict))
            if title:
                out.append(f"{title}{' — ' + items if items else ''}"[:200])
    return out[:6]


async def similar_cases(vertical: str | None, spaces: list[str], text: str, limit: int = 5) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"spaces": spaces[:5], "text": text[:1500], "limit": limit}
    if vertical:
        body["vertical"] = vertical
    res = await query("D1", body) or {}
    out = []
    for c in res.get("cases") or res.get("items") or []:
        if isinstance(c, dict):
            out.append({"id": c.get("id") or c.get("case_id"), "title": c.get("title") or c.get("name")})
    return out[:limit]
