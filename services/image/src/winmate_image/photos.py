"""현장 사진 합성(IMG2P · §4.5 · §6.4 · §7.8) — 사진 등록 · 인식 잡 · 배치 저장(축척 · 실제 크기 계산)."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import jobs

from . import config, kbapi, texts
from .filestore import content_url, thumb_url
from .service import get_work, refresh_work
from .store import repo

log = logging.getLogger("winmate.image.photos")

STATUS_LABEL = {
    "recognizing": "인식 중",
    "recognized": "벽면 인식 완료",
    "low_light": "어두워 인식 어려움 · 다시 촬영 권장",
    "failed": "인식하지 못했어요 · 다시 인식",
    "manual": "면을 직접 맞춰 주세요",
}
STD_MM = {"door": 2100.0, "문": 2100.0, "counter": 1050.0, "카운터": 1050.0, "a4": 297.0}
ARR_LABEL = {"row3": "가로 {n}연", "col3": "세로 {n}연", "separate": "따로 배치", "single": "1대"}


def photo_view(p: dict[str, Any]) -> dict[str, Any]:
    st = p.get("status") or "recognizing"
    return {
        "id": p["id"], "work_id": p["work_id"], "file_id": p["file_id"], "url": content_url(p["file_id"]) or "",
        "thumb_url": thumb_url(p["file_id"], 320) or "", "label": p.get("label") or "현장 사진", "status": st,
        "status_label": STATUS_LABEL.get(st, ""), "quality": p.get("quality"), "surfaces": p.get("surfaces") or [],
        "objects": p.get("objects") or [], "floor_line": p.get("floor_line"), "width": p.get("width"), "height": p.get("height"),
        "job_id": p.get("job_id"), "message": p.get("message"), "created_at": p.get("created_at") or "",
    }


async def add_photo(work_id: str, file_id: str) -> dict[str, Any]:
    work = await get_work(work_id)
    if work.get("kind") != "composite":
        raise ApiError(409, "NOT_COMPOSITE", "현장 사진 합성 작업에서만 사진을 올릴 수 있어요")
    from .filestore import meta as fmeta

    fm = await fmeta(file_id)
    if fm is None:
        raise not_found("파일", file_id)
    if not str(fm.get("mime") or "").startswith("image/"):
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "JPG · PNG · HEIC 이미지만 올릴 수 있어요")
    if int(fm.get("size") or 0) > 20 * 1024 * 1024:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "20MB 이하 이미지만 올릴 수 있어요")
    pid = new_id("imp")
    doc = {"work_id": work_id, "file_id": file_id, "label": "현장 사진", "status": "recognizing", "quality": None,
           "surfaces": [], "objects": [], "floor_line": None, "scale": None, "width": fm.get("width"), "height": fm.get("height"),
           "job_id": None, "message": None, "created_at": now_iso()}
    await repo().put("photos", pid, doc)
    job = await jobs().enqueue("image", "recognize_photo", {"photo_id": pid}, title="현장 사진 인식", ref=pid,
                               project_id=work.get("project_id"))
    saved = await repo().patch("photos", pid, {"job_id": job.id})

    def fn(w: dict[str, Any]) -> None:
        comp = w.get("composite") or {}
        if not comp.get("active_photo_id"):
            comp["active_photo_id"] = pid
        w["composite"] = comp

    await repo().mutate("works", work_id, fn)
    await refresh_work(work_id)
    return {"job_id": job.id, "photo": saved}


async def recognize_again(work_id: str, photo_id: str) -> dict[str, Any]:
    p = await repo().get("photos", photo_id)
    if p is None or p.get("work_id") != work_id:
        raise not_found("현장 사진", photo_id)
    work = await get_work(work_id)
    job = await jobs().enqueue("image", "recognize_photo", {"photo_id": photo_id}, title="현장 사진 다시 인식", ref=photo_id,
                               project_id=work.get("project_id"))
    saved = await repo().patch("photos", photo_id, {"status": "recognizing", "job_id": job.id})
    return {"job_id": job.id, "photo": saved}


async def delete_photo(work_id: str, photo_id: str) -> None:
    p = await repo().get("photos", photo_id)
    if p is None or p.get("work_id") != work_id:
        raise not_found("현장 사진", photo_id)
    await repo().delete("photos", photo_id)

    def fn(w: dict[str, Any]) -> None:
        comp = w.get("composite") or {}
        if comp.get("active_photo_id") == photo_id:
            comp["active_photo_id"] = None
            comp["groups"] = []
        w["composite"] = comp

    await repo().mutate("works", work_id, fn)


# ── 축척 · 실제 크기(결정적) ─────────────────────────────

def _px_len(box: list[float], size: tuple[int, int], axis: str) -> float:
    w, h = size
    return (box[2] - box[0]) * w if axis == "x" else (box[3] - box[1]) * h


def compute_scale(photo: dict[str, Any], ref_dims: dict[str, Any], groups: list[dict[str, Any]]) -> dict[str, Any]:
    """mm_per_px — (1) 기준 치수(카운터 폭 ÷ 카운터 박스 가로 px) (2) 설치 높이(바닥선) (3) 표준 크기 힌트(문 · 카운터 높이) (4) 없음."""
    size = (int(photo.get("width") or 0), int(photo.get("height") or 0))
    if not size[0] or not size[1]:
        return {"mm_per_px": None, "method": "none"}
    objs = photo.get("objects") or []
    counter = next((o for o in objs if any(k in (o.get("label") or "").lower() for k in ("counter", "카운터"))), None)
    cw = ref_dims.get("counter_width_mm")
    if cw and counter and counter.get("bbox"):
        px = _px_len(counter["bbox"], size, "x")
        if px > 1:
            return {"mm_per_px": float(cw) / px, "method": "ref_dim"}
    ih = ref_dims.get("install_height_mm")
    floor = photo.get("floor_line")
    if ih and floor is not None and groups and groups[0].get("quad"):
        bottom = max(p[1] for p in groups[0]["quad"])
        px = (float(floor) - bottom) * size[1]
        if px > 1:
            return {"mm_per_px": float(ih) / px, "method": "ref_dim"}
    for o in objs:
        lab = (o.get("label") or "").lower()
        for k, mm in STD_MM.items():
            if k in lab and o.get("bbox"):
                px = _px_len(o["bbox"], size, "y")
                if px > 1:
                    return {"mm_per_px": mm / px, "method": "std_object"}
    return {"mm_per_px": None, "method": "none"}


def _round10(v: float) -> int:
    return int(round(v / 10.0) * 10)


def group_size_mm(group: dict[str, Any], dims: dict[str, Any] | None) -> tuple[float | None, float | None, bool]:
    if not dims:
        return None, None, False
    w, h = float(dims["w_mm"]), float(dims["h_mm"])
    n = int(group.get("qty") or 1)
    gap = float(group.get("gap_mm") or 10)
    arr = group.get("arrangement") or "row3"
    if n <= 1 or arr in ("separate", "single"):
        return w, h, bool(dims.get("estimated"))
    if arr == "col3":
        return w, n * h + (n - 1) * gap, bool(dims.get("estimated"))
    return n * w + (n - 1) * gap, h, bool(dims.get("estimated"))


def fmt_mm(v: int | None) -> str:
    return f"{v:,}" if v is not None else "[00]"


def measure(photo: dict[str, Any], groups: list[dict[str, Any]], ref_dims: dict[str, Any], dims: dict[str, dict[str, Any]]
            ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scale = compute_scale(photo, ref_dims, groups)
    mpp = scale.get("mm_per_px")
    size = (int(photo.get("width") or 0), int(photo.get("height") or 0))
    out = []
    for g in groups:
        gw, gh, est_dims = group_size_mm(g, dims.get(g.get("model_code") or "") if g.get("model_code") else None)
        width_mm = height_mm = bottom_mm = None
        fit = None
        if mpp and gw:
            width_mm = _round10(gw)
            height_mm = _round10(gh or 0) if gh else None
            # 실제 크기로 맞춘 쿼드(가운데 기준 같은 비율로 키우거나 줄임)
            q = g.get("quad") or []
            if len(q) == 4 and size[0]:
                cur_w = (max(p[0] for p in q) - min(p[0] for p in q)) * size[0]
                if cur_w > 1:
                    f = (gw / mpp) / cur_w
                    cx = sum(p[0] for p in q) / 4
                    cy = sum(p[1] for p in q) / 4
                    fit = [[cx + (p[0] - cx) * f, cy + (p[1] - cy) * f] for p in q]
        if ref_dims.get("install_height_mm"):
            bottom_mm = _round10(float(ref_dims["install_height_mm"]))
        elif mpp and photo.get("floor_line") is not None and g.get("quad"):
            bottom = max(p[1] for p in g["quad"])
            px = (float(photo["floor_line"]) - bottom) * size[1]
            if px > 0:
                bottom_mm = _round10(px * mpp)
        estimated = scale.get("method") == "std_object" or est_dims
        label = f"가로 약 {fmt_mm(width_mm)} mm · 바닥에서 {fmt_mm(bottom_mm)} mm"
        out.append({"id": g["id"], "width_mm": width_mm, "height_mm": height_mm, "bottom_mm": bottom_mm,
                    "estimated": bool(estimated), "label_text": label, "fit_quad": fit})
    return out, scale


def group_label(g: dict[str, Any]) -> str:
    """「QM55C ×3 · 가로 3연」"""
    n = int(g.get("qty") or 1)
    arr = ARR_LABEL.get(g.get("arrangement") or "row3", "").format(n=n)
    head = f"{g.get('label') or g.get('name') or '제품'} ×{n}" if n > 1 else (g.get("label") or g.get("name") or "제품")
    return f"{head} · {arr}" if n > 1 else head


async def save_placements(work_id: str, body: dict[str, Any]) -> dict[str, Any]:
    work = await get_work(work_id)
    photo = await repo().get("photos", body["photo_id"])
    if photo is None or photo.get("work_id") != work_id:
        raise not_found("현장 사진", body["photo_id"])
    groups = [dict(g) for g in body.get("groups") or []]
    for g in groups:
        q = g.get("quad") or []
        if q and len(q) != 4:
            raise ApiError(422, "VALIDATION_ERROR", "쿼드는 점 4개여야 합니다", {"group": g.get("id")})
    codes = [g.get("model_code") for g in groups if g.get("model_code")]
    dims = await kbapi.spec_dims(codes) if codes else {}
    ref_dims = dict(body.get("ref_dims") or {})
    measures, scale = measure(photo, groups, ref_dims, dims)
    options = dict(body.get("options") or {})

    def fn(w: dict[str, Any]) -> None:
        comp = w.get("composite") or {}
        comp.update({"active_photo_id": body["photo_id"], "groups": groups, "ref_dims": ref_dims,
                     "options": {"perspective_light_match": bool(options.get("perspective_light_match", True)),
                                 "screen_menu": bool(options.get("screen_menu", True))},
                     "scale": scale, "measures": measures})
        w["composite"] = comp
        # 조건의 제품도 맞춘다(생성 · 메타에 씀)
        prods = []
        for g in groups:
            if g.get("name") or g.get("label"):
                prods.append({"family_id": g.get("family_id"), "model_code": g.get("model_code"), "name": g.get("name") or g.get("label"),
                              "short": g.get("label") or g.get("name"), "qty": int(g.get("qty") or 1), "source": "user"})
        cond = w.get("conditions") or {}
        cond["products"] = prods
        w["conditions"] = cond

    saved = await repo().mutate("works", work_id, fn)
    await refresh_work(work_id, register=False)
    return {"groups": measures, "scale": scale, "composite": (saved or work).get("composite")}


def default_group(photo: dict[str, Any], product: dict[str, Any], dims: dict[str, Any] | None, scale: dict[str, Any]) -> dict[str, Any]:
    """인식 뒤 기본 배치: 조건의 제품(qty=3 → 가로 3연), 면 가운데 위쪽, 실제 크기(축척이 있으면)."""
    surfaces = [s for s in photo.get("surfaces") or [] if s.get("installable")]
    surf = surfaces[0] if surfaces else {"quad": [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]}
    xs = [p[0] for p in surf["quad"]]
    ys = [p[1] for p in surf["quad"]]
    sx0, sx1, sy0, sy1 = min(xs), max(xs), min(ys), max(ys)
    qty = int(product.get("qty") or 1)
    arr = "row3" if qty > 1 else "single"
    g = {"id": new_id("grp")[:16], "family_id": product.get("family_id"), "model_code": product.get("model_code"),
         "label": product.get("short") or product.get("name") or "제품", "name": product.get("name") or product.get("short") or "제품",
         "qty": qty, "arrangement": arr, "mount": "wall", "gap_mm": 10, "quad": []}
    gw_mm, gh_mm, _ = group_size_mm(g, dims)
    W, H = int(photo.get("width") or 1000), int(photo.get("height") or 750)
    mpp = scale.get("mm_per_px")
    if mpp and gw_mm and gh_mm:
        wn = min(0.9, (gw_mm / mpp) / W)
        hn = min(0.6, (gh_mm / mpp) / H)
    else:
        wn = (sx1 - sx0) * 0.7
        ratio = (gh_mm / gw_mm) if (gw_mm and gh_mm) else (9 / 16 / max(1, qty))
        hn = min((sy1 - sy0) * 0.6, wn * W * ratio / H)
    cx = (sx0 + sx1) / 2
    top = sy0 + (sy1 - sy0) * 0.12
    g["quad"] = [[cx - wn / 2, top], [cx + wn / 2, top], [cx + wn / 2, top + hn], [cx - wn / 2, top + hn]]
    return g


def recognition_message(photo: dict[str, Any], group: dict[str, Any] | None) -> str:
    surfaces = [s for s in photo.get("surfaces") or [] if s.get("installable")]
    if not surfaces or group is None:
        return "설치할 면을 찾지 못했어요. 제품을 끌어 원하는 위치에 놓아 주세요."
    lab = surfaces[0].get("label") or "벽면"
    qty = int(group.get("qty") or 1)
    short = group.get("label") or "제품"
    return (f"{lab}{texts.josa(lab, '을/를')} 설치 가능한 면으로 인식하고 {short} {qty}대를 올려두었습니다. 끌어서 위치를, "
            "모서리로 크기를 맞춰 주세요. 실제 치수를 하나 알려주시면 비율을 정확히 맞춥니다.")


def composite_title(work: dict[str, Any], photo_label: str) -> str:
    cs = work.get("customer_short")
    base = photo_label if photo_label.endswith(("벽면", "면")) else f"{photo_label}"
    return (f"{cs} {base} 합성" if cs else f"{base} 합성")[:24]


def is_dark(q: dict[str, Any] | None, has_surface: bool) -> bool:
    if not q:
        return False
    lm = float(q.get("luma_mean") or 0)
    return lm < config.dark_luma() or (not has_surface and lm < 0.30)
