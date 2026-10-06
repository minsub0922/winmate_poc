"""그래프 `image.recognize_photo`(현장 사진) — 07-image §7.8.

quality(휘도 평균 · 라플라시안 분산 · 포화 비율) → i2t.analyze(confidential:true, json+bbox?: surfaces · objects · floor_line) →
status → default_placement(조건의 제품, qty=3 → 가로 3연, 면 가운데 위쪽, 실제 크기 — 축척이 있으면).
bbox 미지원 · 기밀 차단: 면은 '사진 전체 가운데 60%', 상태는 「면을 직접 맞춰 주세요」.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .. import caps, imaging, kbapi, llm, photos
from ..filestore import load_image
from ..service import refresh_work
from ..store import repo

log = logging.getLogger("winmate.image.recognize")

PROMPT = ("고객 매장 현장 사진이다. 디스플레이를 설치할 수 있는 면(surfaces: 이름 · 종류(wall|counter|ceiling|floor) · 네 꼭짓점 quad 또는 "
          "박스 · 설치 가능 여부), 크기 기준이 되는 물체(objects: counter · door · A4 등 · 박스), 바닥선(floor_line, 0..1 y), 사진 위치 이름"
          "(label, 예 카운터 벽면 · 매장 안쪽)을 돌려줘.")
CENTER60 = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]


class RecState(TypedDict, total=False):
    photo_id: str
    quality: dict[str, Any]
    result: dict[str, Any]


async def quality(state: RecState) -> dict[str, Any]:
    p = await repo().get("photos", state["photo_id"]) or {}
    im = await load_image(p["file_id"])
    q = await asyncio.to_thread(imaging.quality, im)
    await repo().patch("photos", state["photo_id"], {"quality": q, "width": im.width, "height": im.height, "status": "recognizing"})
    return {"quality": q}


def _quad_from(s: dict[str, Any]) -> list[list[float]] | None:
    q = s.get("quad")
    if q and len(q) == 4:
        return [[float(x), float(y)] for x, y in q]
    b = s.get("bbox")
    if b and len(b) == 4:
        return [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]]
    return None


async def analyze(state: RecState) -> dict[str, Any]:
    p = await repo().get("photos", state["photo_id"]) or {}
    f = await caps.flags()
    out: dict[str, Any] = {"label": "현장 사진", "surfaces": [], "objects": [], "floor_line": None, "mode": "model"}
    try:
        res = await llm.vision_task("img.recognize_photo", [p["file_id"]], PROMPT, llm.PhotoOut, want_bbox=f.bbox, confidential=True,
                                    timeout=60)
    except llm.ModelBlocked:
        res = None
        out["mode"] = "blocked"
    if res is None:
        if out["mode"] != "blocked":
            out["mode"] = "failed"
        return {"result": out}
    j = res["json"]
    surfaces = []
    for s in j.get("surfaces") or []:
        q = _quad_from(s)
        if q is None:
            continue
        surfaces.append({"label": s.get("label") or "벽면", "kind": s.get("kind") or "wall", "quad": q,
                         "installable": bool(s.get("installable", True))})
    objects = [{"label": o.get("label") or "object", "bbox": o["bbox"]} for o in j.get("objects") or [] if o.get("bbox") and len(o["bbox"]) == 4]
    for b in res.get("boxes") or []:
        lab = str(b.get("label") or "")
        if any(k in lab.lower() for k in ("counter", "door", "a4", "카운터", "문")) and not any(o["bbox"] == b["box"] for o in objects):
            objects.append({"label": lab, "bbox": b["box"]})
    if not f.bbox:
        out["mode"] = "manual"
    out.update({"label": j.get("label") or "현장 사진", "surfaces": surfaces, "objects": objects, "floor_line": j.get("floor_line")})
    return {"result": out}


async def place(state: RecState) -> dict[str, Any]:
    pid = state["photo_id"]
    p = await repo().get("photos", pid) or {}
    work = await repo().get("works", p["work_id"]) or {}
    r = state.get("result") or {}
    q = state.get("quality") or {}
    mode = r.get("mode")
    surfaces = r.get("surfaces") or []
    if mode in ("manual", "blocked"):
        surfaces = [{"label": "사진 가운데", "kind": "wall", "quad": CENTER60, "installable": True}]
    has_surface = any(s.get("installable") for s in surfaces) and mode not in ("manual", "blocked")
    if photos.is_dark(q, has_surface):
        status = "low_light"
    elif mode in ("manual", "blocked"):
        status = "manual"
    elif mode == "failed" or not has_surface:
        status = "failed"
    else:
        status = "recognized"
    photo = {**p, "label": r.get("label") or p.get("label"), "surfaces": surfaces, "objects": r.get("objects") or [],
             "floor_line": r.get("floor_line"), "status": status}
    comp = work.get("composite") or {}
    group = None
    measures: list[dict[str, Any]] = []
    scale = {"mm_per_px": None, "method": "none"}
    if not comp.get("groups") and comp.get("active_photo_id") in (None, pid):
        prods = (work.get("conditions") or {}).get("products") or []
        if prods:
            dims = await kbapi.spec_dims([x.get("model_code") for x in prods if x.get("model_code")])
            scale = photos.compute_scale(photo, comp.get("ref_dims") or {}, [])
            group = photos.default_group(photo, prods[0], dims.get(prods[0].get("model_code") or ""), scale)
            measures, scale = photos.measure(photo, [group], comp.get("ref_dims") or {}, dims)
    msg = photos.recognition_message(photo, group) if status in ("recognized", "low_light") else (
        "설치할 면을 찾지 못했어요. 제품을 끌어 원하는 위치에 놓아 주세요." if status != "manual" else
        "자동으로 면을 찾지 못했어요. 제품을 끌어 원하는 위치에 놓고 모서리로 크기를 맞춰 주세요.")
    await repo().patch("photos", pid, {"label": photo["label"], "surfaces": surfaces, "objects": photo["objects"],
                                       "floor_line": photo["floor_line"], "status": status, "message": msg})

    def fn(w: dict[str, Any]) -> None:
        c = w.get("composite") or {}
        if c.get("active_photo_id") in (None, pid):
            c["active_photo_id"] = pid
            if group is not None and not c.get("groups"):
                c["groups"] = [group]
                c["measures"] = measures
                c["scale"] = scale
        w["composite"] = c
        if w.get("title_source") in (None, "default", "auto"):
            w["title"] = photos.composite_title(w, photo["label"] or "현장 사진")
            w["title_source"] = "auto"

    await repo().mutate("works", p["work_id"], fn)
    await refresh_work(p["work_id"])
    return {}


def build() -> StateGraph:
    g = StateGraph(RecState)
    g.add_node("quality", quality)
    g.add_node("analyze", analyze)
    g.add_node("place", place)
    g.add_edge(START, "quality")
    g.add_edge("quality", "analyze")
    g.add_edge("analyze", "place")
    g.add_edge("place", END)
    return g
