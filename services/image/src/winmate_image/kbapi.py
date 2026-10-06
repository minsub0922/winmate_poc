"""kb 서비스 호출(계약: contracts/kb.json) — 실패해도 빈 결과로(기능은 계속).

쓰는 것: A1(엔티티) · products/search · spec/table(치수 · 인치) · G4(제품 단독컷) · image_search · G1 · D1 · cases/{id}(사례 사진) ·
C2(인식 못 한 디스플레이 후보) · images/{id}(메타) · images/{id}/file(바이트) · segments(업종 16)
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.image.kb")

_seg_cache: tuple[float, list[dict[str, Any]]] | None = None

# Winmate 16 업종(code) → KR 업종 id (이미지 행의 v 로 거르기)
SEGMENT_KR = {
    "FB": ("kr_retail_fnb", "kr_fnb"), "RT": ("kr_retail", "kr_retail_fnb"), "SV": ("kr_retail",), "HT": ("kr_hotel",),
    "TP": ("kr_culture", "kr_public"), "VN": ("kr_culture",), "AD": ("kr_public",), "OF": ("kr_office", "kr_small_office", "kr_officetel"),
    "RS": ("kr_construction", "kr_home"), "ID": ("kr_home",), "ED": ("kr_education", "kr_school", "kr_academy"),
    "PB": ("kr_public", "kr_public_agency", "kr_transport", "kr_military"), "MD": ("kr_medical", "kr_hospital", "kr_clinic"),
    "MF": ("kr_manufacturing",), "FN": ("kr_finance",), "OE": (),
}
SEGMENT_CHIP = {"FB": "외식 · 카페", "RT": "리테일", "SV": "무인 매장", "HT": "호텔", "TP": "테마파크", "VN": "공연장",
                "AD": "옥외 광고", "OF": "오피스", "RS": "주거 분양", "ID": "인테리어", "ED": "교육", "PB": "공공",
                "MD": "의료", "MF": "제조 · 물류", "FN": "금융", "OE": "파트너 단말"}

MODEL_CODE_RE = re.compile(r"\b([A-Z]{1,4}\d{2,3}[A-Z]{0,4}\d?)\b")


def _kb() -> ServiceClient:
    return ServiceClient("kb", timeout=30)


async def _post(path: str, body: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return await _kb().post(path, json=body)
    except (ApiError, Exception) as exc:  # noqa: BLE001
        log.warning("kb %s 실패: %s", path, exc)
        return None


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        return await _kb().get(path, params=params)
    except (ApiError, Exception) as exc:  # noqa: BLE001
        log.info("kb %s 실패: %s", path, exc)
        return None


async def a1(text: str) -> list[dict[str, Any]]:
    res = await _post("/v1/query/A1", {"text": text[:1000]})
    return list(((res or {}).get("result") or {}).get("links") or [])


async def product_search(q: str, limit: int = 5) -> list[dict[str, Any]]:
    if not q.strip():
        return []
    res = await _get("/v1/products/search", {"q": q, "limit": limit})
    return list((res or {}).get("items") or [])


def product_from_search(item: dict[str, Any], qty: int = 1, source: str = "prefill") -> dict[str, Any]:
    short = item.get("display_name") or item.get("model_code") or item.get("label") or ""
    name = item.get("label") or short
    return {"family_id": item.get("family_id"), "model_code": item.get("model_code"), "name": name, "short": short,
            "qty": max(1, min(9, int(qty or 1))), "source": source}


async def resolve_product(mention: str) -> dict[str, Any] | None:
    """모델명 · 제품 이름 한 개 → KB 제품(모델 우선). 못 찾으면 None(지어내지 않는다)."""
    items = await product_search(mention, limit=5)
    if not items:
        return None
    m = mention.strip().lower().replace(" ", "")
    for it in items:
        names = [str(it.get(k) or "").lower().replace(" ", "") for k in ("display_name", "model_code", "label")]
        if any(m and (m == n or m in n) for n in names):
            return it
    top = items[0]
    if float(top.get("score") or 0) >= 50:
        return top
    return None


async def product_from_ref(ref: str, qty: int = 1, source: str = "user") -> dict[str, Any] | None:
    """셸 참조(`kb:model:mdl_…` · `kb:family:fam_…` · `custom:<글>`) → 조건 제품. 못 찾으면 None(지어내지 않는다)."""
    parts = (ref or "").split(":", 2)
    if len(parts) == 3 and parts[0] == "kb" and parts[1] == "model":
        code = parts[2].removeprefix("mdl_")
        for it in await product_search(code, limit=5):
            if it.get("model_code") == code or it.get("id") == parts[2]:
                return product_from_search(it, qty, source)
        return None
    if len(parts) == 3 and parts[0] == "kb" and parts[1] == "family":
        res = await _get("/v1/models", {"family_id": parts[2], "limit": 1})
        items = list((res or {}).get("items") or [])
        fam = (items[0].get("family") or {}) if items else {}
        if not fam.get("name"):
            return None
        m = re.match(r"^(.+?) Series$", str(fam.get("series_label") or ""))
        short = m.group(1) if m else str(fam["name"])
        return {"family_id": parts[2], "model_code": None, "name": str(fam["name"]), "short": short,
                "qty": max(1, min(9, int(qty or 1))), "source": source}
    if len(parts) >= 2 and parts[0] == "custom":
        hit = await resolve_product(ref.split(":", 1)[1])
        return product_from_search(hit, qty, source) if hit else None
    return None


async def spec_dims(model_codes: list[str]) -> dict[str, dict[str, Any]]:
    """모델코드 → {w_mm, h_mm, d_mm, screen_inch, bezel_mm?, estimated}. 치수가 없으면 인치 + 16:9 + 베젤로 계산(estimated)."""
    codes = [c for c in dict.fromkeys(model_codes) if c]
    if not codes:
        return {}
    res = await _post("/v1/spec/table", {"models": codes})
    out: dict[str, dict[str, Any]] = {}
    derived = (res or {}).get("derived") or {}
    rows = (res or {}).get("rows") or []
    bezel: dict[str, float] = {}
    for r in rows:
        name = str(r.get("attr_name") or "")
        if "베젤" in name:
            for code, v in (r.get("values") or {}).items():
                num = v.get("num") if isinstance(v, dict) else None
                if isinstance(num, (int, float)):
                    bezel[code] = float(num)
    for code in codes:
        d = derived.get(code) or {}
        dims = d.get("dimensions_mm") or {}
        inch = d.get("screen_size_inch")
        if dims.get("w") and dims.get("h"):
            out[code] = {"w_mm": float(dims["w"]), "h_mm": float(dims["h"]), "d_mm": dims.get("d"), "screen_inch": inch,
                         "bezel_mm": bezel.get(code), "estimated": False}
        elif inch:
            diag = float(inch) * 25.4
            w = diag * 16 / (16 ** 2 + 9 ** 2) ** 0.5
            h = diag * 9 / (16 ** 2 + 9 ** 2) ** 0.5
            b = bezel.get(code) or 12.0
            out[code] = {"w_mm": round(w + 2 * b, 1), "h_mm": round(h + 2 * b, 1), "d_mm": None, "screen_inch": inch,
                         "bezel_mm": b, "estimated": True}
    return out


async def g4(family_id: str, limit: int = 8) -> list[dict[str, Any]]:
    res = await _post("/v1/query/G4", {"family_id": family_id, "limit": limit})
    return list(((res or {}).get("result") or {}).get("images") or [])


async def product_front_shot(family_id: str | None) -> dict[str, Any] | None:
    """제품 단독컷(정면 · C 등급 우선)."""
    if not family_id:
        return None
    imgs = await g4(family_id, limit=8)
    if not imgs:
        return None

    def rank(im: dict[str, Any]) -> tuple[int, int]:
        alt = str(im.get("alt") or "")
        return (0 if "정면" in alt else 1, 0 if im.get("grade_hint") == "C" else 1)

    return sorted(imgs, key=rank)[0]


async def image_search(text: str, limit: int = 40) -> list[dict[str, Any]]:
    res = await _post("/v1/query/image_search", {"text": text or "매장", "limit": limit})
    return list(((res or {}).get("result") or {}).get("images") or [])


async def g1(space: str, category: str | None = None, vertical: str | None = None, limit: int = 12) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"space": space, "limit": limit}
    if category:
        body["category"] = category
    if vertical:
        body["vertical"] = vertical
    res = await _post("/v1/query/G1", body)
    return list(((res or {}).get("result") or {}).get("images") or [])


async def d1(*, vertical: str | None, spaces: list[str], text: str, limit: int = 6) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"spaces": spaces, "text": text or None, "limit": limit, "targets": []}
    if vertical:
        body["vertical"] = vertical
    res = await _post("/v1/query/D1", body)
    return list(((res or {}).get("result") or {}).get("deployments") or [])


async def case_photos(deployment_id: str, limit: int = 4) -> list[dict[str, Any]]:
    res = await _get(f"/v1/cases/{deployment_id}")
    items = (((res or {}).get("photos") or {}).get("items") or [])[:limit]
    title = (res or {}).get("title")
    url = (res or {}).get("url")
    return [{**it, "case_title": title, "case_url": url} for it in items]


async def c2(*, category: str | None, text: str, limit: int = 5) -> list[dict[str, Any]]:
    body: dict[str, Any] = {"capabilities": [], "text": text or None, "limit": limit}
    if category:
        body["category"] = category
    res = await _post("/v1/query/C2", body)
    result = (res or {}).get("result") or {}
    return list(result.get("candidates") or result.get("families") or (res or {}).get("candidates") or [])


async def image_meta(image_id: str) -> dict[str, Any] | None:
    res = await _get(f"/v1/images/{image_id}")
    return res if isinstance(res, dict) else None


async def image_bytes(image_id: str) -> bytes | None:
    try:
        data, _ = await _kb().get_bytes(f"/v1/images/{image_id}/file")
        return data
    except Exception as exc:  # noqa: BLE001
        log.info("kb 이미지 파일을 받지 못했습니다 %s: %s", image_id, exc)
        return None


async def segments() -> list[dict[str, Any]]:
    global _seg_cache
    if _seg_cache and time.time() - _seg_cache[0] < 600:
        return _seg_cache[1]
    res = await _get("/v1/segments")
    items = list((res or {}).get("items") or []) if isinstance(res, dict) else []
    _seg_cache = (time.time(), items)
    return items


def segment_of_vertical(v: str | None) -> str | None:
    if not v:
        return None
    for code, ks in SEGMENT_KR.items():
        if v in ks:
            return code
    return None


def segment_by_chip(label: str) -> str | None:
    for code, chip in SEGMENT_CHIP.items():
        if chip == label:
            return code
    return None


async def gather(*aws: Any) -> list[Any]:
    return list(await asyncio.gather(*aws, return_exceptions=False))
