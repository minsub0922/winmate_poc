"""조감도(birdseye) 호출 — 08-birdseye §6.1 · §6.7 · §8 handoff 를 따른다(계약 `contracts/birdseye.json`).

birdseye 는 다른 세션이 지금 만드는 중이라 계약에 경로가 아직 없을 수 있다. 계약에 그 경로가 있으면 기본 검증(dev = strict)을,
없으면 검증 없이(경고 로그) 부른다 — 계약이 채워지면 자동으로 엄격 검증으로 바뀐다. 호출이 실패하면 빈 값으로 내려가
화면이 멈추지 않게 한다(「조감도 작업 0개」 · 알림 없음).
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.contracts import load_contract

log = logging.getLogger("winmate.scenario.birdseye")

_version_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}
VERSION_TTL = 60.0


def _client(method: str, path: str) -> ServiceClient:
    contract = load_contract("birdseye")
    known = contract is not None and contract.find(method, path) is not None
    if not known:
        log.debug("birdseye 계약에 %s %s 없음 — 검증 없이 호출", method, path)
    return ServiceClient("birdseye", timeout=20, validation=None if known else "off")


async def _call(method: str, path: str, **kw: Any) -> Any:
    c = _client(method, path)
    return await c.request(method, path, **kw)


async def list_birdseyes() -> tuple[list[dict[str, Any]], bool]:
    """내 조감도 · 팀 공유 조감도 → ([{id, title, zone_count, version}], 쓸 수 있음)."""
    try:
        res = await _call("GET", "/v1/birdseyes", params={"limit": 50})
    except Exception as exc:  # noqa: BLE001
        log.info("birdseye 목록 실패: %s", exc)
        return [], False
    out = []
    for row in (res or {}).get("items") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        zc = row.get("zone_count")
        if zc is None:
            zc = row.get("zones") if isinstance(row.get("zones"), int) else len(row.get("zones") or [])
        out.append({"id": row["id"], "title": row.get("title") or "조감도", "zone_count": int(zc or 0),
                    "version": row.get("version")})
    return out, True


async def handoff(birdseye_id: str) -> dict[str, Any] | None:
    try:
        return await _call("GET", f"/v1/birdseyes/{birdseye_id}/handoff")
    except Exception as exc:  # noqa: BLE001
        log.info("birdseye handoff 실패 %s: %s", birdseye_id, exc)
        return None


async def version(birdseye_id: str, *, fresh: bool = False) -> dict[str, Any] | None:
    """`GET /birdseyes/{id}/version` — 60초 캐시(SC0 조회마다 확인, R10)."""
    hit = _version_cache.get(birdseye_id)
    if hit and not fresh and time.time() - hit[0] < VERSION_TTL:
        return hit[1]
    try:
        res = await _call("GET", f"/v1/birdseyes/{birdseye_id}/version")
    except Exception as exc:  # noqa: BLE001
        log.info("birdseye version 실패 %s: %s", birdseye_id, exc)
        res = None
    _version_cache[birdseye_id] = (time.time(), res)
    return res


def clear_cache() -> None:
    _version_cache.clear()


async def create(title: str, description: str, products: list[str], origin_ref: str, project_id: str | None) -> dict[str, Any] | None:
    body: dict[str, Any] = {"title": title, "description": description, "prefill": {"products": products},
                            "origin": {"service": "scenario", "ref": origin_ref, "label": "공간 시나리오",
                                       "return_to": f"/scenario/{origin_ref}/result"}}
    if project_id:
        body["project_id"] = project_id
    try:
        return await _call("POST", "/v1/birdseyes", json_body=body)
    except Exception as exc:  # noqa: BLE001
        log.info("birdseye 만들기 실패: %s", exc)
        return None


async def register_usage(birdseye_id: str, ref: str, label: str, version_: int | None) -> bool:
    body = {"service": "scenario", "ref": ref, "label": label, "version": version_}
    try:
        await _call("POST", f"/v1/birdseyes/{birdseye_id}/usages", json_body=body)
        return True
    except Exception as exc:  # noqa: BLE001
        log.info("birdseye 사용 등록 실패 %s: %s", birdseye_id, exc)
        return False


# ── handoff 해석 ──────────────────────────────────────────

def _product_of(p: dict[str, Any]) -> dict[str, Any]:
    label = p.get("label") or p.get("name") or p.get("display_name") or p.get("short") or ""
    short = p.get("short") or p.get("display_name") or label
    return {"family_id": p.get("family_id"), "model_code": p.get("model_code"), "label": label, "short": short,
            "qty": p.get("qty")}


def zones_of(h: dict[str, Any]) -> list[dict[str, Any]]:
    """handoff → 존 목록 [{id, n, name, short_name, text, products[], furniture[], path_order, u, v}]."""
    zones = h.get("zones") or {}
    points = zones.get("points") if isinstance(zones, dict) else zones
    out = []
    for i, p in enumerate(points or []):
        if not isinstance(p, dict):
            continue
        prods = [_product_of(x) for x in p.get("products") or [] if isinstance(x, dict)]
        if not prods:
            # links 의 제품 칩(「OH55C ×3」)만 있으면 라벨만 쓴다(family 없음)
            for lk in p.get("links") or []:
                if isinstance(lk, dict) and lk.get("kind") == "product" and lk.get("label"):
                    lab = str(lk["label"])
                    qty = None
                    if "×" in lab:
                        base, _, q = lab.partition("×")
                        lab = base.strip()
                        qty = int(q.strip()) if q.strip().isdigit() else None
                    prods.append({"family_id": lk.get("ref"), "model_code": None, "label": lab, "short": lab, "qty": qty})
        furn = [x for x in p.get("furniture") or [] if isinstance(x, dict)]
        name = p.get("name") or f"존 {p.get('n') or i + 1}"
        out.append({
            "id": p.get("zone_id") or p.get("id") or f"zone_{p.get('n') or i + 1}", "n": int(p.get("n") or i + 1), "name": name,
            "short_name": p.get("short_name") or name.split(" · ")[0], "text": p.get("text") or "",
            "products": prods, "furniture": furn, "has_furniture": bool(furn) or bool(p.get("has_furniture")) or p.get("kind") == "furniture",
            "kind": p.get("kind"), "subtitle": p.get("subtitle") or "",
            "path_order": p.get("path_order"), "u": p.get("u"), "v": p.get("v"),
        })
    return out


def zone_state(z: dict[str, Any]) -> str:
    kind = z.get("kind")
    if z.get("products") or kind == "product":
        return "products"
    if z.get("has_furniture") or kind == "furniture":
        return "furniture"
    return "empty"


def product_line(products: list[dict[str, Any]]) -> str:
    parts = []
    for p in products:
        lab = p.get("short") or p.get("label") or ""
        parts.append(f"{lab} ×{p['qty']}" if p.get("qty") and int(p["qty"]) > 1 else lab)
    return " · ".join(x for x in parts if x)


def zone_sub(z: dict[str, Any]) -> str:
    st = zone_state(z)
    if st == "products":
        if z.get("subtitle"):
            return z["subtitle"]
        meaning = z.get("text") or ""
        return " · ".join(x for x in [product_line(z["products"]), meaning] if x)
    if st == "furniture":
        return "가구만 배치 · 제품은 다음 단계에서 추천"
    return "배치 제품 없음 · 랩핑 포인트만 지정"


def zone_snapshot(zones: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """연결 시점의 존 모양(이름 · 제품) — 변경 반영(SC1B)은 이것과 지금 handoff 를 비교한다(장면에 사용자가 더한 제품은 비교하지 않음)."""
    return {z["id"]: {"name": z["name"], "n": z["n"], "products": [product_sig(p) for p in z["products"]]} for z in zones}


def product_sig(p: dict[str, Any]) -> str:
    return f"{p.get('family_id') or p.get('model_code') or p.get('label') or p.get('short')}×{p.get('qty') or ''}"


def zones_hash(zones: list[dict[str, Any]]) -> str:
    raw = json.dumps([[z["id"], z["name"], [[p.get("family_id"), p.get("label"), p.get("qty")] for p in z["products"]]]
                      for z in zones], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def plan_preview(h: dict[str, Any], zones: list[dict[str, Any]]) -> dict[str, Any]:
    pp = dict(h.get("plan_preview") or {})
    space = h.get("space") or {}
    pp.setdefault("zone_count", len(zones))
    if "area_pyeong" not in pp and space.get("area_pyeong") is not None:
        pp["area_pyeong"] = space.get("area_pyeong")
    if "ceiling_h_m" not in pp and space.get("ceiling_h_m") is not None:
        pp["ceiling_h_m"] = space.get("ceiling_h_m")
    if "window_label" not in pp:
        feats = space.get("features") or []
        win = next((f.get("label") for f in feats if isinstance(f, dict) and "창" in (f.get("label") or "")), None)
        if win:
            pp["window_label"] = win
    pts = pp.get("zones") or [{"id": z["id"], "n": z["n"], "x": z.get("u"), "y": z.get("v")} for z in zones]
    pp["zones"] = pts
    return pp
