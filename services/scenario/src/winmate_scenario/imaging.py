"""장면 이미지 — image 서비스(07 §6.8 요청 · §6.9 렌더 API, 계약 `contracts/image.json`). 이 서비스는 T2I 를 직접 부르지 않는다.

- 하나(SC4 「이미지 생성」 · SC4E 「이미지 생성에서 다시 만들기」): `POST /v1/requests` + `:start` → 웹이 IMG2 로. 충족되면 SC4 · SC4E 를
  열 때 `GET /v1/requests?from_service=scenario&from_ref=` 로 확인해 붙인다(`images:sync`).
- 일괄(「장면별 이미지 모두 생성」): 이미지 없는 장면마다 `POST /v1/renders`(동시 1) → 끝나면 붙인다.
- 붙일 때 조건 스냅숏(제품 · 인물 · 솔루션)을 남긴다 → stale 판정(§4.11). 사용 등록 `POST /v1/images/{id}/usages`.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.ids import now_iso

from . import service, texts
from . import timeline as tl

log = logging.getLogger("winmate.scenario.imaging")

FORBID = ["competitor_logo", "real_person_face", "gibberish_text"]


def _img() -> ServiceClient:
    return ServiceClient("image", timeout=60)


def scene_ref(sc: dict[str, Any]) -> str:
    return sc["id"]


def prefill(doc: dict[str, Any], sc: dict[str, Any]) -> dict[str, Any]:
    """「이미지 생성으로 넘어가는 것」 표: 공간 · 장면 요약 · 제품 약칭 · 비율."""
    beats = [b.get("text") or "" for b in sc.get("beats") or []]
    label = tl.scene_label(doc, sc)
    summary = texts.clip(", ".join([label, *beats[:2]]), 60) if beats else label
    shorts = [(p.get("short") or p.get("label") or "").replace("Galaxy ", "") for p in sc.get("products") or []]
    space = texts.join([doc.get("space_label") or "", sc.get("place") or ""]) or sc.get("place") or doc.get("space_label") or ""
    return {"space": space, "scene": summary, "products": [p for p in shorts if p], "product_line": " · ".join(p for p in shorts if p),
            "aspect": "16:9", "aspect_label": "16:9 · 제안서 시트용", "kind": "scenario"}


def description(doc: dict[str, Any], sc: dict[str, Any]) -> str:
    pf = prefill(doc, sc)
    parts = [sc.get("story") or sc.get("title") or "", f"공간: {pf['space']}" if pf["space"] else "", f"제품: {pf['product_line']}" if pf["product_line"] else ""]
    return " / ".join(p for p in parts if p)


async def create_request(doc: dict[str, Any], sc: dict[str, Any]) -> dict[str, Any]:
    """image 요청 + :start → {request_id, image_route(IMG2), work_id}."""
    label = tl.scene_label(doc, sc)
    pf = prefill(doc, sc)
    body = {
        "from_service": "scenario", "from_ref": scene_ref(sc), "from_label": f"공간 시나리오 · {doc.get('title') or ''}",
        "title": texts.clip(f"장면 {sc['no']} · {label} {pf['scene'].split(', ', 1)[-1] if ', ' in pf['scene'] else ''}".strip(), 80),
        "prefill": {"kind": "scenario", "description": description(doc, sc),
                    "products": [{"model_code": p.get("model_code"), "family_id": p.get("family_id"), "name": p.get("label"),
                                  "short": p.get("short"), "qty": p.get("qty")} for p in sc.get("products") or []],
                    "aspect": "16:9", "space_label": pf["space"]},
    }
    if doc.get("project_id"):
        body["project_id"] = doc["project_id"]
    c = _img()
    req = await c.post("/v1/requests", json=body)
    started = await c.post(f"/v1/requests/{req['id']}:start")
    return {"request_id": req["id"], "image_route": started.get("conditions_route") or started.get("route"), "work_id": started.get("work_id")}


async def version_info(version_id: str) -> dict[str, Any]:
    return await _img().get(f"/v1/versions/{version_id}")


def _rendition(v: dict[str, Any], kind: str = "fhd") -> dict[str, Any] | None:
    rs = v.get("renditions") or []
    return next((r for r in rs if r.get("kind") == kind), None) or next((r for r in rs if r.get("kind") == "native"), None)


async def image_block(doc: dict[str, Any], sc: dict[str, Any], version_id: str, source: str) -> dict[str, Any]:
    v = await version_info(version_id)
    fhd = _rendition(v) or {}
    return {
        "image_id": v.get("image_id"), "version_id": version_id, "aspect": "16:9", "created_at": now_iso(), "source": source,
        "url": v.get("url"), "thumb_url": v.get("thumb_url"), "file_id": fhd.get("file_id") or v.get("master_file_id"), "n": v.get("n"),
        "renditions": v.get("renditions") or [], "generation": v.get("generation") or {},
        "snapshot": service.image_snapshot(doc, sc),
    }


async def current_version(image_id: str) -> str | None:
    """내 이미지(img:image:<id>) → 지금 버전 id."""
    d = await _img().get(f"/v1/images/{image_id}")
    return (d or {}).get("current_version_id") or ((d or {}).get("current") or {}).get("id")


def kb_block(doc: dict[str, Any], sc: dict[str, Any], kb_image_id: str) -> dict[str, Any]:
    """사내 자산(kb 이미지)을 그대로 장면 이미지로 — image 서비스 버전이 아니라 사용 등록은 없다."""
    return {
        "image_id": None, "version_id": f"kb:image:{kb_image_id}", "aspect": "16:9", "created_at": now_iso(), "source": "picked",
        "url": f"/api/kb/v1/images/{kb_image_id}/file", "thumb_url": f"/api/kb/v1/images/{kb_image_id}/thumb", "file_id": None, "n": None,
        "renditions": [], "generation": {"source": "kb"}, "snapshot": service.image_snapshot(doc, sc),
    }


async def register_usage(doc: dict[str, Any], sc: dict[str, Any], image_id: str | None, version_id: str) -> None:
    if not image_id:
        return
    try:
        await _img().post(f"/v1/images/{image_id}/usages", json={"version_id": version_id, "service": "scenario", "ref": scene_ref(sc),
                                                                  "label": f"공간 시나리오 › {doc.get('title') or ''} · 장면 {sc['no']}"})
    except Exception as exc:  # noqa: BLE001
        log.info("이미지 사용 등록 실패 %s: %s", image_id, exc)


async def remove_usage(sc: dict[str, Any]) -> None:
    img = sc.get("image") or {}
    if not img.get("image_id"):
        return
    try:
        await _img().delete(f"/v1/images/{img['image_id']}/usages/scenario/{scene_ref(sc)}")
    except Exception as exc:  # noqa: BLE001
        log.info("이미지 사용 해제 실패: %s", exc)


async def fulfilled_requests(scene_id: str) -> list[dict[str, Any]]:
    try:
        res = await _img().get("/v1/requests", params={"from_service": "scenario", "from_ref": scene_id})
    except Exception as exc:  # noqa: BLE001
        log.info("이미지 요청 조회 실패 %s: %s", scene_id, exc)
        return []
    items = [r for r in (res or {}).get("items") or [] if r.get("status") == "fulfilled" and r.get("result_version_id")]
    return sorted(items, key=lambda r: r.get("updated_at") or "")


# ── 렌더 API(일괄) ──────────────────────────────────────────

def render_body(doc: dict[str, Any], sc: dict[str, Any]) -> dict[str, Any]:
    beats = [b.get("text") or "" for b in sc.get("beats") or []]
    products = sc.get("products") or []
    refs = []
    for p in products:
        if p.get("model_code") or p.get("family_id"):
            refs.append({"model_code": p.get("model_code"), "family_id": p.get("family_id"), "qty": max(1, int(p.get("qty") or 1))})
    return {
        "origin": {"service": "scenario", "ref": scene_ref(sc)}, "kind": "scene",
        "prompt": {"subject_ko": texts.clip(sc.get("title") or tl.scene_label(doc, sc), 80),
                   "details_ko": [x for x in [sc.get("place") or "", *beats[:3],
                                              " · ".join(service.product_chip(p) for p in products)] if x],
                   "negatives": []},
        "aspect": "16:9", "target": "fhd", "product_refs": refs, "forbid": FORBID, "allow_people": "generic",
        "confidential": bool(doc.get("customer_name")), "label": f"장면 {sc['no']} · {tl.scene_label(doc, sc)}",
        **({"project_id": doc["project_id"]} if doc.get("project_id") else {}),
    }


async def start_render(doc: dict[str, Any], sc: dict[str, Any]) -> dict[str, Any]:
    return await _img().post("/v1/renders", json=render_body(doc, sc))


async def get_render(render_id: str) -> dict[str, Any]:
    return await _img().get(f"/v1/renders/{render_id}")


WaitFn = Callable[[str], Awaitable[dict[str, Any]]]


async def _default_wait(render_id: str, timeout: float = 600.0, interval: float = 1.5) -> dict[str, Any]:
    t0 = time.monotonic()
    while True:
        r = await get_render(render_id)
        if r.get("status") in ("succeeded", "failed", "canceled"):
            return r
        if time.monotonic() - t0 > timeout:
            return {**r, "status": "failed", "error": {"message": "이미지 생성이 너무 오래 걸려요"}}
        await asyncio.sleep(interval)


# 테스트에서 바꿔 끼운다(이미지 워커를 그 자리에서 돌린 뒤 결과를 읽게)
wait_render: WaitFn = _default_wait
