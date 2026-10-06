"""그래프 공통 — 맥락 불러오기 · 제품 외형(KB 스펙) · 참조 예산 배정(§10.3) · 결정적 합성 초안(현장 사진)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from PIL import Image, ImageChops

from .. import caps, config, imaging, kbapi, prompts
from ..refs import kb_file
from ..store import repo

log = logging.getLogger("winmate.image.graphs")

STRENGTH_RANK = {"high": 3, "mid": 2, "low": 1}
ROLE_OF_ASPECT = {"composition": "composition", "placement": "composition", "color_light": "style", "material": "style"}


def flags_dict(f: caps.Flags) -> dict[str, Any]:
    return {"ref_images": f.ref_images, "edit": f.edit, "mask": f.mask, "bbox": f.bbox, "max_refs": f.max_refs,
            "provider": f.t2i_provider, "model": f.t2i_model, "upscaler": f.upscaler}


async def product_facts(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    codes = [p.get("model_code") for p in products if p.get("model_code")]
    return await kbapi.spec_dims(codes) if codes else {}


async def product_shots(products: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """제품별 단독컷(KB G4 정면 · C 등급 우선) → {family_or_code: {kb_image_id, file_id, alt}}."""
    out: dict[str, dict[str, Any]] = {}
    for p in products:
        key = p.get("family_id") or p.get("model_code") or ""
        if not key or key in out:
            continue
        shot = await kbapi.product_front_shot(p.get("family_id"))
        if shot is None:
            continue
        fid = await kb_file(shot["id"], alt=shot.get("alt"))
        if fid:
            out[key] = {"kb_image_id": shot["id"], "file_id": fid, "alt": shot.get("alt"), "source_url": shot.get("page_url")}
    return out


def allocate_references(*, products: list[dict[str, Any]], shots: dict[str, dict[str, Any]], refs: list[dict[str, Any]],
                        flags: dict[str, Any], structure: dict[str, Any] | None = None) -> dict[str, Any]:
    """참조 예산 배정(결정적): (0) structure_ref (1) 제품 단독컷 — 서로 다른 제품마다 1장, 수량 큰 순, 최대 PRODUCT_REF_MAX
    (2) 사용자 참조 — 강 > 중 > 약, 같으면 고른 순서 (3) 남는 참조는 텍스트 대체."""
    max_refs = int(flags.get("max_refs") or 3)
    send: list[dict[str, Any]] = []
    text_refs: list[dict[str, Any]] = []
    fallbacks: list[str] = []
    supports = bool(flags.get("ref_images"))
    if structure is not None:
        if supports:
            send.append({"kind": "structure", "file_id": structure["file_id"], "role": "composition", "strength": "high"})
    ordered = sorted([p for p in products if (p.get("family_id") or p.get("model_code")) in shots],
                     key=lambda p: -int(p.get("qty") or 1))[: config.product_ref_max()]
    for p in ordered:
        s = shots[p.get("family_id") or p.get("model_code")]
        if supports and len(send) < max_refs:
            send.append({"kind": "product", "file_id": s["file_id"], "role": "product", "strength": "high",
                         "family_id": p.get("family_id"), "name": p.get("short") or p.get("name"), "kb_image_id": s["kb_image_id"]})
    users = sorted(refs, key=lambda r: (-STRENGTH_RANK.get(r.get("strength") or "mid", 2), int(r.get("order") or 0)))
    for r in users:
        mode = r.get("send_mode")
        fid = r.get("sanitized_file_id") or r.get("file_id")
        if supports and mode != "text_fallback" and fid and len(send) < max_refs:
            role = ROLE_OF_ASPECT.get((r.get("aspects") or ["composition"])[0], "style")
            send.append({"kind": "user", "file_id": fid, "role": role, "strength": r.get("strength") or "mid", "ref_id": r["id"],
                         "confidential": bool(r.get("confidential"))})
        else:
            text_refs.append(r)
            if not supports:
                fallbacks.append("reference:text_fallback")
            elif mode == "text_fallback":
                fallbacks.append("reference:sanitize_text" if (r.get("analysis") or {}).get("faces") or (r.get("analysis") or {}).get("logos")
                                 else "reference:text_fallback")
            else:
                fallbacks.append("reference:text_fallback")
    if not supports and ordered:
        fallbacks.append("reference:text_fallback")
    return {"send": send, "text_refs": [r["id"] for r in text_refs], "fallbacks": list(dict.fromkeys(fallbacks))}


def ref_lines(plan: dict[str, Any], refs: list[dict[str, Any]]) -> list[str]:
    by_id = {r["id"]: r for r in refs}
    lines = []
    i = 0
    for s in plan.get("send") or []:
        i += 1
        if s["kind"] == "structure":
            lines.append(f"Reference image {i}: follow this composition and product placement exactly (structure reference).")
        elif s["kind"] == "product":
            lines.append(f"Reference image {i}: product reference for {s.get('name')} — keep its exact shape, proportions and bezel.")
        else:
            r = by_id.get(s.get("ref_id") or "")
            if r:
                lines.append(prompts.reference_text(i, r, sent_as_image=True))
    for rid in plan.get("text_refs") or []:
        r = by_id.get(rid)
        if r:
            i += 1
            lines.append(prompts.reference_text(i, r, sent_as_image=False))
    return lines


def references_meta(plan: dict[str, Any], refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sent = {s.get("ref_id") for s in plan.get("send") or [] if s.get("ref_id")}
    out = []
    for r in refs:
        out.append({"reference_id": r["id"], "source_kind": r.get("origin_kind") or r.get("source_kind"),
                    "source_url": r.get("source_url"), "source_label": r.get("source_label"), "rights": r.get("rights"),
                    "send_mode": "image" if r["id"] in sent else "text_fallback", "aspects": r.get("aspects") or [],
                    "strength": r.get("strength") or "mid"})
    return out


def t2i_refs(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"file_id": s["file_id"], "role": s["role"], "strength": s["strength"]} for s in plan.get("send") or []]


def products_meta(products: list[dict[str, Any]], shots: dict[str, dict[str, Any]], identity: dict[str, Any] | None) -> list[dict[str, Any]]:
    out = []
    for p in products:
        s = shots.get(p.get("family_id") or p.get("model_code") or "") or {}
        out.append({"family_id": p.get("family_id"), "model_code": p.get("model_code"), "name": p.get("name"),
                    "qty": int(p.get("qty") or 1), "ref_asset": s.get("kb_image_id"), "identity": "model"})
    if identity:
        if identity.get("mode") == "model":
            out.append({"family_id": identity.get("family_id"), "model_code": identity.get("model_code"),
                        "name": identity.get("name") or identity.get("short"), "qty": 1, "ref_asset": None, "identity": "model"})
        else:
            out.append({"family_id": None, "name": "참조 사진 속 디스플레이", "qty": 1, "ref_asset": None, "identity": "generic"})
    return out


def identity_line(identity: dict[str, Any] | None) -> str | None:
    if not identity:
        return None
    if identity.get("mode") == "model":
        return (f"The display seen in the reference photo is Samsung {identity.get('name') or identity.get('short')}; "
                "draw it with that product's real shape and proportions.")
    return "For the display seen in the reference photo, follow only its general appearance (product identity unknown)."


# ── 현장 사진 결정적 합성 ───────────────────────────────

def build_composite(photo: Image.Image, groups: list[dict[str, Any]], dims: dict[str, dict[str, Any]], *, screen_menu: bool,
                    variant: int = 0) -> tuple[Image.Image, Image.Image, list[float] | None]:
    """디스플레이 대역을 그룹 쿼드(배열대로 나눈 칸)에 원근 워프 → (초안, 제품 마스크, 그룹 bbox 0..1)."""
    out = photo.convert("RGB").copy()
    mask = Image.new("L", photo.size, 0)
    boxes: list[list[float]] = []
    for g in groups:
        q = g.get("quad") or []
        if len(q) != 4:
            continue
        n = int(g.get("qty") or 1)
        arr = g.get("arrangement") or "row3"
        d = dims.get(g.get("model_code") or "") or {}
        gw = None
        if d.get("w_mm"):
            gw = float(d["w_mm"]) * (n if arr == "row3" else 1) + 10 * (n - 1)
        gap = (float(g.get("gap_mm") or 10) / gw) if gw else 0.01
        if n <= 1 or arr == "single":
            cells = [q]
        elif arr == "separate":
            cells = imaging.split_quad(q, n, vertical=False, gap_ratio=0.12)
        else:
            cells = imaging.split_quad(q, n, vertical=arr == "col3", gap_ratio=gap)
        bezel = (float(d.get("bezel_mm")) / float(d["w_mm"])) if d.get("bezel_mm") and d.get("w_mm") else 0.012
        for j, cell in enumerate(cells):
            px = imaging.quad_px(cell, photo.size)
            cw = max(8, int(abs(px[1][0] - px[0][0])))
            ch = max(8, int(abs(px[3][1] - px[0][1])))
            screen = imaging.menu_template(cw * 2, ch * 2, variant + j) if screen_menu else None
            proxy = imaging.display_proxy(cw * 2, ch * 2, bezel_ratio=bezel, screen=screen, ceiling=g.get("mount") == "ceiling")
            out, m = imaging.warp_into(out, proxy, px)
            mask = ImageChops.lighter(mask, m.convert("L"))
        boxes.append(imaging.quad_bbox(q))
    bbox = None
    if boxes:
        bbox = [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]
    return out, mask, bbox


async def load_photo_working(file_id: str, max_side: int = 1600) -> Image.Image:
    from ..filestore import load_image

    im = await load_image(file_id)
    if max(im.size) > max_side:
        im = im.copy()
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return im


async def gather_limited(n: int, coros: list[Any]) -> list[Any]:
    sem = asyncio.Semaphore(max(1, n))

    async def run(c: Any) -> Any:
        async with sem:
            return await c

    return list(await asyncio.gather(*(run(c) for c in coros), return_exceptions=True))


async def work_refs(work_id: str) -> list[dict[str, Any]]:
    refs = await repo().all("refs", where={"work_id": work_id}, order_by="created_at")
    return sorted(refs, key=lambda r: (int(r.get("order") or 0), r.get("created_at") or ""))
