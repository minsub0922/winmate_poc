"""내보내기 · 넘기기(08-birdseye §4.13 · §6.7 · §7.11 · §8) — 제품 수량표 · 이미지 목록 · 제안서 매핑 · handoff ·
ProposalHandoff v1 · export 그래프(합성 → 수량표.xlsx → ZIP)."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import math
import os
import re
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import file_bytes, save_file

from . import config
from . import service as svc
from . import space as S
from . import text as T
from .repo import repo

log = logging.getLogger("winmate.birdseye.export")

ZP_NAME = {"ZP-A": "번호 콜아웃", "ZP-B": "존 확대 컷", "ZP-C": "고객 동선 따라가기"}


# ── 수량표 ───────────────────────────────────────────────

async def quantities(be_id: str) -> dict[str, Any]:
    from .layouts import get_layout

    lay = await get_layout(be_id) or {"groups": [], "items": [], "memos": []}
    prods = {p["id"]: p for p in await svc.products(be_id)}
    zs = await svc.zones(be_id)
    zone_of: dict[str, int] = {}
    for z in zs:
        for g in z.get("cluster_groups") or []:
            zone_of.setdefault(g, int(z.get("n") or 99))
    memos = lay.get("memos") or []
    rows = []
    for g in lay.get("groups", []):
        if g.get("kind") != "product":
            continue
        p = prods.get(g.get("ref") or "", {})
        name = p.get("display_name") or g.get("label") or "제품"
        if g.get("size") and len(p.get("size_options") or []) > 1:
            name = f"{name} {g['size']}"
        memo = next((m.split(" · ", 1)[1] for m in memos if m.startswith(f"{g.get('label')} · ")), None)
        rows.append({"family_id": g.get("family_id") or p.get("family_id"), "model_code": g.get("model_code") or p.get("model_code"),
                     "name": name, "at": g.get("at_label") or g.get("anchor_label") or "", "qty": int(g.get("qty") or 1),
                     "qty_source": g.get("qty_source") or "default", "rule_id": g.get("rule_id"), "memo": memo,
                     "confirm": (g.get("qty_source") or "") == "suggested", "source_url": None,
                     "_order": (zone_of.get(g["id"], 99), p.get("order", 0))})
    rows.sort(key=lambda r: r.pop("_order"))
    furn = await svc.furniture(be_id, selected_only=True)
    b = await svc.get(be_id)
    if b.get("furniture_none"):
        furn = []
    details = []
    zones_short: list[str] = []
    total = 0
    for f in furn:
        units = int(f.get("qty") or 1) * int(f.get("rows") or 1)
        total += units
        z = f.get("zone")
        if z and z not in zones_short:
            zones_short.append(z)
        d = f.get("dims_m") or {}
        details.append({"name": f.get("name") or "", "at": z or "", "qty": units,
                        "dims": f"{T.num(d.get('w'))}×{T.num(d.get('d'))}×{T.num(d.get('h'))} m" if d else "",
                        "estimated": bool(f.get("dims_estimated"))})
    kinds = len({f.get("catalog_code") or f.get("name") for f in furn})
    frow = {"label": f"가구 {kinds}종 (참고)", "at": " · ".join(zones_short), "qty": total} if furn else None
    return {"rows": rows, "furniture_row": frow, "furniture": details, "memos": memos}


# ── BE6 목록 · 매핑 ──────────────────────────────────────

def filename_default(title: str, version: int) -> str:
    toks = [t for t in re.split(r"\s+", (title or "조감도").strip()) if t]
    out = ""
    for i, t in enumerate(toks):
        t = re.sub(r"[\\/:*?\"<>|]", "", t)
        if i and t[:1].isdigit():
            out += "_" + t
        else:
            out += t
    return f"{out}_조감도_v{version}"


def _done(c: dict[str, Any]) -> bool:
    return c["status"] in ("done", "check", "draft") and not c.get("stale")


async def _cut_sets(be_id: str) -> dict[str, Any]:
    b = await svc.get(be_id)
    cs = [c for c in await svc.cuts(be_id) if _done(c)]
    primary = next((c for c in cs if c["id"] == b.get("primary_cut_id")), None) or next((c for c in cs if not c.get("before")), None)
    pkey = (primary or {}).get("view", {}).get("preset"), (primary or {}).get("view", {}).get("target_item_id"), (primary or {}).get("view", {}).get("custom_text")

    def vkey(c: dict[str, Any]) -> tuple[Any, Any, Any]:
        return c["view"].get("preset"), c["view"].get("target_item_id"), c["view"].get("custom_text")

    same_view = [c for c in cs if primary and c["id"] != primary["id"] and vkey(c) == pkey and not c.get("before")]
    before = next((c for c in cs if c.get("before") and primary and vkey(c) == pkey), None)
    others = [c for c in cs if primary and vkey(c) != pkey and not c.get("before")]
    night = next((c for c in same_view if c.get("light") == "night"), None)
    return {"b": b, "primary": primary, "same_view": same_view, "before": before, "others": others, "night": night}


def _res_label(c: dict[str, Any]) -> str:
    return c.get("resolution") or "3840×2160"


async def export_options(be_id: str) -> dict[str, Any]:
    s = await _cut_sets(be_id)
    b = s["b"]
    p = s["primary"]
    images = []
    if p:
        images.append({"kind": "cut", "ref": p["id"], "name": svc.cut_label(p), "sub": f"원본 · {_res_label(p)}", "selected": True,
                       "thumb_url": _thumb(p)})
        for c in s["same_view"]:
            images.append({"kind": "cut", "ref": c["id"], "name": svc.cut_label(c), "sub": _res_label(c), "selected": True, "thumb_url": _thumb(c)})
        if s["before"]:
            images.append({"kind": "before_after", "ref": f"{s['before']['id']}|{p['id']}", "name": "도입 전 / 후 비교",
                           "sub": "2컷 · 나란히 한 장", "selected": True, "thumb_url": _thumb(p)})
    zs = await svc.zones(be_id)
    if zs and p:
        images.append({"kind": "zones_callout", "ref": p["id"], "name": "존 포인트 콜아웃", "sub": f"번호 {len(zs)}곳 · 범례 포함",
                       "selected": True, "thumb_url": _thumb(p)})
    for c in s["others"]:
        images.append({"kind": "cut", "ref": c["id"], "name": svc.cut_label(c), "sub": _res_label(c), "selected": False, "thumb_url": _thumb(c)})
    prods = await svc.products(be_id)
    return {"images": images, "filename_default": filename_default(b["title"], int(b.get("save_version") or 1)),
            "mapping": await sheet_map(be_id), "products_count": len(prods), "zones_count": len(zs), "title": b["title"],
            "version": int(b.get("save_version") or 1), "family_ids": [p2["family_id"] for p2 in prods if p2.get("family_id")],
            "spec_products": [{"family_id": p2.get("family_id"), "model_code": p2.get("model_code"), "ref": p2.get("ref"),
                               "label": p2.get("display_name")} for p2 in prods]}


def _thumb(c: dict[str, Any]) -> str | None:
    fid = c.get("thumb_file_id") or c.get("image_file_id") or c.get("draft_v1_file_id")
    return f"/api/files/v1/files/{fid}/thumbnail?w=240" if fid else None


async def sheet_map(be_id: str) -> list[dict[str, Any]]:
    s = await _cut_sets(be_id)
    b = s["b"]
    p = s["primary"]
    out = []
    if p:
        out.append({"from": svc.cut_label(p), "to": "조감도 · 공간 전경", "code": "BV-A", "ref": p["id"], "kind": "cut"})
        if s["before"]:
            out.append({"from": "도입 전 / 후", "to": "공간 전경 · 두 시점 비교", "code": "BV-B", "ref": f"{s['before']['id']}|{p['id']}",
                        "kind": "before_after"})
        elif s["night"]:
            out.append({"from": "주간 / 야간", "to": "공간 전경 · 두 시점 비교", "code": "BV-B", "ref": f"{p['id']}|{s['night']['id']}",
                        "kind": "day_night"})
    zs = await svc.zones(be_id)
    if zs:
        code = b.get("zone_layout") or "ZP-A"
        out.append({"from": f"존 포인트 {len(zs)}곳", "to": "조감도 · 존별 포인트", "code": code, "ref": p["id"] if p else None, "kind": "zones"})
    if await svc.products(be_id):
        out.append({"from": "제품 수량표", "to": "공간별 제품 · 수량표", "code": "SM-B", "ref": None, "kind": "quantities"})
    return out


# ── handoff ─────────────────────────────────────────────

async def plan_preview(be_id: str) -> dict[str, Any] | None:
    from .layouts import get_layout

    model = await svc.space_model(be_id)
    if not model:
        return None
    lay = await get_layout(be_id) or {"items": []}
    minx, miny, maxx, maxy = S.bbox_of(model)
    zs = await svc.zones(be_id)
    items = [{"kind": it["kind"], "label": it.get("label") or "", "x": it["x"], "y": it["y"], "w": it["w"], "d": it["d"],
              "rot_deg": it.get("rot_deg", 0)} for it in lay.get("items", []) if not it.get("unplaced")]
    ch = (model.get("ceiling_h") or {}).get("value")
    return {"width_m": round(maxx - minx, 2), "height_m": round(maxy - miny, 2), "outline": (model.get("rooms") or [{}])[0].get("outline", []),
            "rooms": model.get("rooms", []), "walls": model.get("walls", []), "openings": model.get("openings", []),
            "columns": model.get("columns", []), "items": items,
            "zones": [{"id": z["id"], "n": int(z.get("n") or 0), "x": (z.get("anchor_m") or [0, 0])[0], "y": (z.get("anchor_m") or [0, 0])[1],
                       "name": z.get("name") or ""} for z in zs],
            "zone_count": len(zs), "area_pyeong": float(round(T.m2_to_pyeong(model.get("area_m2") or 0))) if model.get("area_m2") else None,
            "ceiling_h_m": ch, "area_label": f"{T.pyeong_label(model.get('area_m2'))} · 층고 {T.num(ch)}m", "window_label": S.window_label(model),
            "file_id": None}


def _handoff_cut(c: dict[str, Any], primary_id: str | None) -> dict[str, Any]:
    fid = c.get("image_file_id") or c.get("draft_v1_file_id")
    return {"cut_id": c["id"], "label": svc.cut_label(c), "view": c["view"].get("label") or "", "light": c.get("light") or "day",
            "before": bool(c.get("before")), "is_primary": c["id"] == primary_id, "stale": bool(c.get("stale")), "image_id": c.get("image_id"),
            "image_version_id": c.get("version_id"), "renditions": c.get("renditions") or [], "generation": c.get("generation") or {},
            "file_id": fid, "url": f"/api/files/v1/files/{fid}/content" if fid else None, "draft_only": c.get("render_path") == "render:draft_only"}


async def handoff(be_id: str, version: int | None = None) -> dict[str, Any]:
    from .zones import _cut_for, zone_view

    b = await svc.get(be_id)
    model = await svc.space_model(be_id) or {}
    cs = [c for c in await svc.cuts(be_id) if _done(c)]
    s = await _cut_sets(be_id)
    p = s["primary"]
    comps = []
    if p and s["before"]:
        comps.append({"kind": "before_after", "left": s["before"]["id"], "right": p["id"], "composite_file_id": s["before"].get("composite_file_id")})
    if p and s["night"]:
        comps.append({"kind": "day_night", "left": p["id"], "right": s["night"]["id"], "composite_file_id": None})
    cut = await _cut_for(be_id, None)
    zpoints = []
    for z in await svc.zones(be_id):
        zv = zone_view(z, cut)
        prods = z.get("products") or []
        meaning = z.get("text") or ""
        if prods:
            subtitle = f"{prods[0].get('group_label') or prods[0].get('short') or prods[0].get('label')} · {meaning}"
        elif z.get("furniture"):
            subtitle = "가구만 배치 · 제품은 다음 단계에서 추천"
        else:
            subtitle = "배치 제품 없음 · 랩핑 포인트만 지정"
        zpoints.append({"id": z["id"], "zone_id": z["id"], "n": zv["n"], "name": zv["name"], "short_name": z.get("short_name") or "",
                        "text": meaning, "links": zv["links"], "u": zv["u"], "v": zv["v"], "x": (z.get("anchor_m") or [None])[0],
                        "y": (z.get("anchor_m") or [None, None])[1], "kind": z.get("kind") or "product", "products": prods,
                        "furniture": z.get("furniture") or [], "subtitle": subtitle, "path_order": z.get("path_order")})
    q = await quantities(be_id)
    feats = model.get("features", [])
    ch = (model.get("ceiling_h") or {}).get("value")
    prods_all = [{"family_id": p2.get("family_id"), "model_code": p2.get("model_code"), "label": p2.get("display_name") or "",
                  "short": p2.get("short") or "", "qty": 1, "group_label": ""} for p2 in await svc.products(be_id)]
    return {
        "birdseye_id": be_id, "version": int(b.get("save_version") or 1), "layout_version": int(b.get("layout_version") or 0),
        "title": b["title"], "customer": b.get("customer_name"), "project_id": b.get("project_id"),
        "route": f"/birdseye/{be_id}/result", "updated_at": b["updated_at"],
        "space": {"label": (model.get("rooms") or [{}])[0].get("label") or b.get("space_label", ""), "space_types": b.get("space_types") or [],
                  "area_m2": model.get("area_m2"), "area_pyeong": float(round(T.m2_to_pyeong(model["area_m2"]))) if model.get("area_m2") else None,
                  "ceiling_h_m": ch, "features": feats, "estimated": bool(model.get("estimated", True)),
                  "summary": f"{T.pyeong_label(model.get('area_m2'))} · 층고 {T.num(ch)}m" if model else ""},
        "plan_preview": await plan_preview(be_id),
        "cuts": [_handoff_cut(c, b.get("primary_cut_id")) for c in cs], "comparisons": comps,
        "zones": {"layout": b.get("zone_layout") or "ZP-A", "cut_id": cut["id"] if cut else None, "points": zpoints},
        "quantities": q["rows"], "furniture": q["furniture"], "memos": q["memos"], "sheet_map": await sheet_map(be_id),
        "products": prods_all,
    }


async def proposal_handoff(be_id: str, ptype: str, section: str) -> dict[str, Any]:
    h = await handoff(be_id)
    b = await svc.get(be_id)
    items = []
    assets = []
    facts = []
    src = {"kind": "birdseye", "ref": be_id, "label": h["title"]}
    primary = next((c for c in h["cuts"] if c["is_primary"]), None)
    if section in ("birdseye", "spaceScenario") and primary:
        items.append({"key": "BV-A", "label": primary["label"], "from_label": "3D 조감도", "sheet_role": "BV",
                      "sheet_title": "조감도 · 공간 전경", "template_hint": {"code": "BV-A", "name": "풀폭 전경"},
                      "status": "warn" if primary["draft_only"] else "ok",
                      "status_label": "[확정 필요] 초안 렌더" if primary["draft_only"] else "그대로 들어가요", "include_default": True,
                      "content": {"image": {"file_id": primary["file_id"], "image_version_id": primary["image_version_id"]},
                                  "caption": f"{h['space']['label']} · {primary['label']} (생성 이미지)"}, "sources": [src]})
        assets.append({"kind": "image", "file_id": primary["file_id"], "rights": "generated", "caption_rule": "생성 이미지",
                       "image_version_id": primary["image_version_id"]})
        comp = h["comparisons"][0] if h["comparisons"] else None
        if comp:
            items.append({"key": "BV-B", "label": "도입 전 / 후" if comp["kind"] == "before_after" else "주간 / 야간",
                          "from_label": "시점 · 조명", "sheet_role": "BV", "sheet_title": "공간 전경 · 두 시점 비교",
                          "template_hint": {"code": "BV-B", "name": "두 시점 비교"}, "status": "ok", "status_label": "그대로 들어가요",
                          "include_default": ptype != "quickwin", "content": {"left_cut": comp["left"], "right_cut": comp["right"], "kind": comp["kind"]},
                          "sources": [src]})
        if h["zones"]["points"]:
            code = h["zones"]["layout"]
            items.append({"key": code, "label": f"존 포인트 {len(h['zones']['points'])}곳", "from_label": "존 포인트",
                          "sheet_role": "ZP", "sheet_title": "조감도 · 존별 포인트", "template_hint": {"code": code, "name": ZP_NAME.get(code, "")},
                          "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
                          "content": {"cut_id": h["zones"]["cut_id"], "points": [{k: z[k] for k in ("n", "name", "text", "u", "v")} for z in h["zones"]["points"]]},
                          "sources": [src]})
    if section in ("spaceProducts", "birdseye") and h["quantities"]:
        warn = any(r["confirm"] for r in h["quantities"])
        items.append({"key": "SM-B", "label": "제품 수량표", "from_label": "배치안", "sheet_role": "SM", "sheet_title": "공간별 제품 · 수량표",
                      "template_hint": {"code": "SM-B", "name": "공간별 제품 · 수량표"}, "status": "warn" if warn else "ok",
                      "status_label": f"[확정 필요] {sum(1 for r in h['quantities'] if r['confirm'])}건" if warn else "그대로 들어가요",
                      "include_default": section == "spaceProducts", "content": {"rows": h["quantities"], "memos": h["memos"]}, "sources": [src]})
        for r in h["quantities"]:
            facts.append({"key": f"qty:{r['model_code'] or r['family_id']}", "label": f"{r['name']} 수량", "value": str(r["qty"]), "unit": "대",
                          "status": "unconfirmed" if r["confirm"] else "confirmed", "placeholder": None, "source": {"kind": "birdseye", "ref": be_id}})
    if section == "spaceScenario" and h["zones"]["points"]:
        items.append({"key": "VM-C", "label": "조감도 위 솔루션 핀", "from_label": "존 포인트", "sheet_role": "VM", "sheet_title": "공간 × 솔루션 맵",
                      "template_hint": {"code": "VM-C", "name": "조감도 위 솔루션 핀"}, "status": "ok", "status_label": "그대로 들어가요",
                      "include_default": True, "content": {"cut_id": h["zones"]["cut_id"], "pins": [{"n": z["n"], "u": z["u"], "v": z["v"], "label": z["name"]}
                                                                                                   for z in h["zones"]["points"]]},
                      "sources": [src]})
    sp = h["space"]
    if sp.get("area_m2"):
        facts.append({"key": "area", "label": "면적", "value": f"{int(round(sp['area_m2']))}", "unit": "㎡",
                      "status": "unconfirmed" if sp.get("estimated") else "confirmed", "placeholder": None, "source": {"kind": "birdseye", "ref": be_id}})
    if sp.get("ceiling_h_m"):
        facts.append({"key": "ceiling", "label": "층고", "value": T.num(sp["ceiling_h_m"]), "unit": "m", "status": "confirmed",
                      "placeholder": None, "source": {"kind": "birdseye", "ref": be_id}})
    return {"source": {"feature": "birdseye", "ref_id": be_id, "version": h["version"], "title": h["title"], "updated_at": h["updated_at"],
                       "route": h["route"]},
            "target": {"proposal_type": ptype, "section_key": section},
            "customer": {"name": b.get("customer_name")} if b.get("customer_name") else None,
            "items": items, "facts": facts, "assets": assets, "live_link": False}


# ── 합성(Pillow) ─────────────────────────────────────────

_FONT_PATHS = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
               "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def _font(size: int) -> Any:
    from PIL import ImageFont

    for p in [os.environ.get("BE_FONT_PATH") or ""] + _FONT_PATHS:
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover
        return ImageFont.load_default()


def compose_before_after(before_png: bytes, after_png: bytes, out_w: int, out_h: int) -> bytes:
    from PIL import Image, ImageDraw

    a = Image.open(io.BytesIO(before_png)).convert("RGB")
    b = Image.open(io.BytesIO(after_png)).convert("RGB")
    canvas = Image.new("RGB", (out_w, out_h), (245, 246, 248))
    half = out_w // 2
    for i, im in enumerate((a, b)):
        scale = min(half / im.width, out_h / im.height)
        im2 = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))))
        x = i * half + (half - im2.width) // 2
        y = (out_h - im2.height) // 2
        canvas.paste(im2, (x, y))
    d = ImageDraw.Draw(canvas)
    f = _font(max(18, out_h // 30))
    pad = out_h // 40
    for i, lab in enumerate(("도입 전", "도입 후")):
        x = i * half + pad
        tw = d.textlength(lab, font=f)
        d.rounded_rectangle([x, pad, x + tw + pad * 2, pad + f.size + pad], radius=pad // 2, fill=(20, 40, 160) if i else (255, 255, 255))
        d.text((x + pad, pad + pad // 3), lab, font=f, fill=(255, 255, 255) if i else (18, 20, 23))
    out = io.BytesIO()
    canvas.save(out, format="PNG")
    return out.getvalue()


def compose_callout(png: bytes, points: list[dict[str, Any]], out_w: int, out_h: int) -> bytes:
    """번호 원(짧은 변 3%, #1428a0, 흰 글자) + 범례 패널."""
    from PIL import Image, ImageDraw

    im = Image.open(io.BytesIO(png)).convert("RGB").resize((out_w, out_h))
    d = ImageDraw.Draw(im, "RGBA")
    r = int(min(out_w, out_h) * float(config.rules()["zones"]["callout_ratio"]) / 2) or 8
    color = tuple(int(config.rules()["zones"]["callout_color"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    f = _font(int(r * 1.1))
    for p in points:
        if p.get("u") is None or p.get("v") is None:
            continue
        cx, cy = p["u"] * out_w, p["v"] * out_h
        d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=(255, 255, 255, 230))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
        t = str(p["n"])
        tw = d.textlength(t, font=f)
        d.text((cx - tw / 2, cy - f.size * 0.62), t, font=f, fill=(255, 255, 255))
    # 범례
    lf = _font(max(14, out_h // 45))
    pad = out_h // 40
    lines = [f"{p['n']}  {p.get('name') or ''}" for p in points]
    if lines:
        w = int(max(d.textlength(x, font=lf) for x in lines) + pad * 2)
        h = int(len(lines) * (lf.size + pad // 2) + pad * 1.5)
        x0, y0 = out_w - w - pad, out_h - h - pad
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=pad // 2, fill=(255, 255, 255, 235))
        for i, line in enumerate(lines):
            d.text((x0 + pad, y0 + pad // 2 + i * (lf.size + pad // 2)), line, font=lf, fill=(18, 20, 23))
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


def _convert(png: bytes, fmt: str, size: tuple[int, int] | None) -> bytes:
    from PIL import Image

    im = Image.open(io.BytesIO(png)).convert("RGB")
    if size and im.size != size:
        im = im.resize(size)
    out = io.BytesIO()
    if fmt == "jpg":
        im.save(out, format="JPEG", quality=92)
    else:
        im.save(out, format="PNG")
    return out.getvalue()


def _table_page(rows: list[list[str]], title: str, size: tuple[int, int]) -> bytes:
    from PIL import Image, ImageDraw

    im = Image.new("RGB", size, (255, 255, 255))
    d = ImageDraw.Draw(im)
    tf = _font(size[1] // 22)
    f = _font(size[1] // 36)
    pad = size[1] // 18
    d.text((pad, pad), title, font=tf, fill=(18, 20, 23))
    y = pad * 2 + tf.size
    colw = [0.45, 0.25, 0.1, 0.2]
    for r_i, row in enumerate(rows):
        x = pad
        for c_i, cell in enumerate(row):
            d.text((x, y), str(cell), font=f, fill=(18, 20, 23) if r_i else (89, 97, 112))
            x += int((size[0] - pad * 2) * colw[c_i % len(colw)])
        y += int(f.size * 1.8)
        d.line([(pad, y - f.size * 0.4), (size[0] - pad, y - f.size * 0.4)], fill=(226, 229, 234), width=1)
    out = io.BytesIO()
    im.save(out, format="PNG")
    return out.getvalue()


# ── export 잡 ───────────────────────────────────────────

async def create_export(be_id: str, body: dict[str, Any]) -> dict[str, Any]:
    from winmate_common.jobs import jobs

    b = await svc.get(be_id)
    opts = await export_options(be_id)
    items = body.get("items")
    if items is None:
        items = [{"kind": i["kind"], "ref": i["ref"]} for i in opts["images"] if i["selected"]]
    xid = new_id("bex")
    filename = (body.get("filename") or opts["filename_default"]).strip()
    filename = re.sub(r"[\\/:*?\"<>|]", "", filename).removesuffix(".zip") or opts["filename_default"]
    job_id = new_id("job")
    doc = {"birdseye_id": be_id, "items": items, "format": body.get("format") or "png", "size": body.get("size") or "original",
           "include_furniture": bool(body.get("include_furniture", True)), "filename": filename, "job_id": job_id, "file_id": None,
           "status": "queued", "error": None}
    await repo().put("exports", xid, doc)
    await jobs().enqueue("birdseye", "export", {"export_id": xid, "birdseye_id": be_id}, title=f"{b['title']} · 내보내기", ref=be_id,
                         project_id=b.get("project_id"), job_id=job_id)
    return {"job_id": job_id, "export_id": xid}


def export_view(x: dict[str, Any]) -> dict[str, Any]:
    fid = x.get("file_id")
    return {"id": x["id"], "birdseye_id": x["birdseye_id"], "status": x.get("status") or "queued", "format": x.get("format") or "png",
            "size": x.get("size") or "original", "filename": x.get("filename") or "", "include_furniture": bool(x.get("include_furniture", True)),
            "items": x.get("items") or [], "job_id": x.get("job_id"), "file_id": fid,
            "url": f"/api/files/v1/files/{fid}/content" if fid else None,
            "download_url": f"/api/files/v1/files/{fid}/content?download=1" if fid else None, "error": x.get("error"),
            "created_at": x["created_at"]}


async def _image_bytes(c: dict[str, Any], size: str) -> tuple[bytes, tuple[int, int]]:
    rend = c.get("renditions") or []
    want = "fhd" if size == "fhd" else "uhd"
    r = next((x for x in rend if x.get("kind") == want), None)
    target = (1920, 1080) if size == "fhd" else (3840, 2160)
    if r is None:
        r = next((x for x in rend if x.get("kind") == "uhd"), None) or next((x for x in rend if x.get("kind") == "native"), None)
    fid = (r or {}).get("file_id") or c.get("image_file_id") or c.get("draft_v1_file_id")
    if not fid:
        raise ApiError(409, "CUT_NOT_READY", "이미지가 아직 없어요")
    data, _ = await file_bytes(fid)
    if c.get("render_path") == "render:draft_only" or r is None:
        target = (1920, 1080) if size == "fhd" else (3840, 2160)
    return data, target


async def run_export(export_id: str, progress: Any = None) -> dict[str, Any]:
    from .zones import _cut_for, zone_view

    x = await repo().get("exports", export_id)
    if x is None:
        raise ApiError(404, "NOT_FOUND", "내보내기를 찾을 수 없어요")
    be_id = x["birdseye_id"]
    b = await svc.get(be_id)
    await repo().patch("exports", export_id, {"status": "running"})
    fmt = x.get("format") or "png"
    size = x.get("size") or "original"
    ext = "jpg" if fmt == "jpg" else "png"
    entries: list[dict[str, Any]] = []
    pages: list[bytes] = []
    sources: dict[str, Any] = {"birdseye_id": be_id, "title": b["title"], "version": int(b.get("save_version") or 1),
                               "layout_version": int(b.get("layout_version") or 0), "created_at": now_iso(), "cuts": []}
    conf = bool((b.get("inputs") or {}).get("plan_file_ids") or (b.get("inputs") or {}).get("photo_count") or (b.get("inputs") or {}).get("description"))
    n_img = 0
    items = x.get("items") or []
    for i, it in enumerate(items, start=1):
        kind = it.get("kind")
        if progress:
            await progress(10 + 60 * i / max(1, len(items)), "이미지 모으는 중")
        if kind == "cut":
            c = await repo().get("cuts", it.get("ref") or "")
            if not c:
                continue
            data, target = await _image_bytes(c, size)
            out = await asyncio.to_thread(_convert, data, ext, target)
            name = f"{i:02d}_{_safe(svc.cut_label(c))}.{ext}"
            sources["cuts"].append({"cut_id": c["id"], "label": svc.cut_label(c), "render_path": c.get("render_path"), "image_id": c.get("image_id"),
                                    "version_id": c.get("version_id"), "generation": c.get("generation") or {}, "prompt": c.get("prompt"),
                                    "ai_generated": c.get("render_path") != "render:draft_only"})
        elif kind == "before_after":
            ids = (it.get("ref") or "").split("|")
            if len(ids) != 2:
                continue
            c1, c2 = await repo().get("cuts", ids[0]), await repo().get("cuts", ids[1])
            if not c1 or not c2:
                continue
            d1, target = await _image_bytes(c1, size)
            d2, _ = await _image_bytes(c2, size)
            comp = await asyncio.to_thread(compose_before_after, d1, d2, target[0], target[1])
            out = await asyncio.to_thread(_convert, comp, ext, None)
            name = f"{i:02d}_도입전후_비교.{ext}"
        elif kind == "zones_callout":
            c = await repo().get("cuts", it.get("ref") or "") or await _cut_for(be_id, None)
            if not c:
                continue
            d1, target = await _image_bytes(c, size)
            pts = [zone_view(z, c) for z in await svc.zones(be_id)]
            comp = await asyncio.to_thread(compose_callout, d1, pts, target[0], target[1])
            out = await asyncio.to_thread(_convert, comp, ext, None)
            name = f"{i:02d}_존포인트_콜아웃.{ext}"
        else:
            continue
        n_img += 1
        if fmt == "pdf":
            pages.append(out)
            continue
        meta = await save_file(name, out, "image/jpeg" if ext == "jpg" else "image/png", source="export", confidential=conf,
                               project_id=b.get("project_id"), purpose="birdseye.export")
        entries.append({"file_id": meta["id"], "path": name})
    # 수량표.xlsx
    if progress:
        await progress(75, "수량표 만드는 중")
    q = await quantities(be_id)
    space_label = b.get("space_label") or ""
    sheets = [{"name": "제품", "columns": [{"key": "space", "label": "공간"}, {"key": "name", "label": "제품명"}, {"key": "model", "label": "모델코드"},
                                         {"key": "at", "label": "위치"}, {"key": "qty", "label": "수량"}, {"key": "basis", "label": "수량 근거"},
                                         {"key": "memo", "label": "메모"}, {"key": "url", "label": "출처 URL"}],
               "rows": [{"space": space_label, "name": r["name"], "model": r.get("model_code") or "[확인 필요]", "at": r["at"], "qty": r["qty"],
                         "basis": _basis(r), "memo": r.get("memo") or "", "url": r.get("source_url") or ""} for r in q["rows"]]}]
    if x.get("include_furniture", True) and q["furniture"]:
        sheets.append({"name": "가구(참고)", "columns": [{"key": "name", "label": "가구"}, {"key": "at", "label": "위치"}, {"key": "qty", "label": "수량"},
                                                       {"key": "dims", "label": "치수(w×d×h)"}, {"key": "note", "label": "비고"}],
                       "rows": [{"name": f["name"], "at": f["at"], "qty": f["qty"], "dims": f["dims"], "note": "치수 추정" if f["estimated"] else ""}
                                for f in q["furniture"]]})
    ex = ServiceClient("export", timeout=180)
    xl = await ex.post("/v1/exports", json={"format": "xlsx", "filename": "수량표", "document": {"sheets": sheets}, "confidential": conf,
                                            "project_id": b.get("project_id"), "source_ref": f"birdseye:{be_id}"})
    xl = await _await_export(ex, xl)
    entries.append({"file_id": xl["file"]["id"], "path": "수량표.xlsx"})
    if fmt == "pdf":
        rows = [["제품", "위치", "수량", "수량 근거"]] + [[r["name"], r["at"], str(r["qty"]), _basis(r)] for r in q["rows"]]
        if q["furniture_row"]:
            fr = q["furniture_row"]
            rows.append([fr["label"], fr["at"], str(fr["qty"]), "참고"])
        tsize = (1920, 1080) if size == "fhd" else (3840, 2160)
        pages.append(await asyncio.to_thread(_table_page, rows, f"{b['title']} · 제품 수량표", tsize))
        pdf = await asyncio.to_thread(_pdf, pages)
        meta = await save_file(f"{x['filename']}.pdf", pdf, "application/pdf", source="export", confidential=conf, project_id=b.get("project_id"))
        entries.insert(0, {"file_id": meta["id"], "path": f"{x['filename']}.pdf"})
    entries.append({"path": "sources.json", "json": sources})
    if progress:
        await progress(88, "ZIP 묶는 중")
    z = await ex.post("/v1/exports", json={"format": "zip", "filename": x["filename"], "document": {"entries": entries}, "confidential": conf,
                                           "project_id": b.get("project_id"), "source_ref": f"birdseye:{be_id}"})
    z = await _await_export(ex, z)
    fid = z["file"]["id"]
    await repo().patch("exports", export_id, {"status": "done", "file_id": fid, "images": n_img})
    return {"export_id": export_id, "file_id": fid, "images": n_img}


def _basis(r: dict[str, Any]) -> str:
    src = r.get("qty_source")
    if src == "rule":
        return "규칙"
    if src == "user":
        return "사용자"
    return "확인 필요"


def _safe(s: str) -> str:
    return re.sub(r"[\\/:*?\"<>| ·°]+", "_", s).strip("_")


def _pdf(pages: list[bytes]) -> bytes:
    from PIL import Image

    ims = [Image.open(io.BytesIO(p)).convert("RGB") for p in pages]
    out = io.BytesIO()
    ims[0].save(out, format="PDF", save_all=True, append_images=ims[1:], resolution=150)
    return out.getvalue()


async def _await_export(ex: ServiceClient, res: dict[str, Any]) -> dict[str, Any]:
    if res.get("status") == "done" and res.get("file"):
        return res
    xid = res.get("export_id")
    for _ in range(600):
        await asyncio.sleep(0.5)
        r = await ex.get(f"/v1/exports/{xid}")
        if r.get("status") == "done" and r.get("file"):
            return r
        if r.get("status") == "failed":
            raise ApiError(502, (r.get("error") or {}).get("code") or "EXPORT_FAILED", (r.get("error") or {}).get("message") or "내보내기 실패")
    raise ApiError(504, "TIMEOUT", "내보내기가 너무 오래 걸려요")


_ = (math, json)
