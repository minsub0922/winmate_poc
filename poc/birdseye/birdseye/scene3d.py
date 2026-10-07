"""3D 조감도 ③④ — 공간·제품·가구 배치를 정하고 Blender 씬 명세(JSON)를 만든다."""
from __future__ import annotations

import collections
import copy
import math
from pathlib import Path

from . import space as S
from .analyze3d import FURN_TYPES, LIB, SPACE_TYPES
from .catalog import Catalog, footprint_depth, native_portrait, screen_size
from .furnish import furnish
from .layout2d import layout_lines, line_strategy, recommend_all
from .rules import Rules
from .zones import suggest_zones

FONT = Path(__file__).resolve().parent / "fonts" / "WinmateStamp-Bold.otf"

QUALITY = {
    "draft": {"res": [960, 540], "samples": 24, "preview": {"res": [480, 270], "samples": 6}, "label": "빠른 미리보기 960×540"},
    "standard": {"res": [1600, 900], "samples": 64, "preview": {"res": [640, 360], "samples": 8}, "label": "기본 1600×900"},
    "high": {"res": [3840, 2160], "samples": 128, "preview": {"res": [640, 360], "samples": 8}, "label": "고해상도 3840×2160"},
}
CAMERAS = list(LIB["cameras"])
LIGHTS = list(LIB["lighting"])


def estimate_space(inp: dict) -> tuple[dict, str]:
    """2D 도 사진도 없을 때 — 공간 유형 기본값과 '대략 규모'로 직사각형 공간을 만든다."""
    st = SPACE_TYPES.get(inp.get("space_type") or "lobby", SPACE_TYPES["lobby"])
    sc = inp.get("scale") or {}
    area = float(sc.get("area_pyeong") or 0) * 3.3058 or st["area_m2"]
    H = {"low": 2600, "normal": max(2800, st["height"] - 300), "high": max(4000, st["height"])}.get(sc.get("height") or "", st["height"])
    aspect = 1.45
    W = round(math.sqrt(area * 1e6 * aspect) / 100) * 100
    D = round(area * 1e6 / W / 100) * 100
    ops = []
    if st.get("storefront"):
        mid = W / 2
        ew = 2400
        ops = [
            {"id": "W_A", "kind": "window", "wall": "front", "start": 600, "length": mid - ew / 2 - 600, "label": "유리창 A", "sill": 0, "head": min(H - 600, 3600)},
            {"id": "E1", "kind": "entrance", "wall": "front", "start": mid - ew / 2, "length": ew, "label": "주출입구", "sill": 0, "head": min(H - 300, 2700)},
            {"id": "W_B", "kind": "window", "wall": "front", "start": mid + ew / 2, "length": W - mid - ew / 2 - 600, "label": "유리창 B", "sill": 0, "head": min(H - 600, 3600)},
        ]
    else:
        ops = [
            {"id": "E1", "kind": "entrance", "wall": "front", "start": 1200, "length": 1200, "label": "출입문", "sill": 0, "head": min(H - 300, 2200)},
            {"id": "W_A", "kind": "window", "wall": "left", "start": D * 0.2, "length": D * 0.6, "label": "창 A", "sill": 900, "head": min(H - 400, 2400)},
        ]
    sp = {"name": st["label"], "space_type": st["code"], "width": W, "depth": D, "height": H, "openings": ops, "pillars": [],
          "outlets": [], "source": "estimate", "estimated": True}
    basis = f"추정 — {st['label']} 기본값" + (f" · 약 {sc['area_pyeong']}평" if sc.get("area_pyeong") else "")
    return sp, basis


def layout_info(project: dict, project2d: dict | None, catalog: Catalog, rules: Rules) -> dict:
    inp = project["input"]
    linked = project2d is not None
    if linked:
        sp = copy.deepcopy(project2d["space"])
        basis = f"2D 조감도 치수 사용 · {project2d.get('title') or sp.get('name')}"
    elif project.get("space"):
        sp = copy.deepcopy(project["space"])
        basis = "현장 사진 추정값" if sp.get("source") == "photos" else ("직접 입력" if not sp.get("estimated") else "추정값")
    else:
        sp, basis = estimate_space(inp)
    sp.setdefault("space_type", inp.get("space_type") or "lobby")
    codes = list(inp.get("products") or [])
    cats = {catalog.get(c)["category"] for c in codes if catalog.get(c)}
    info = {"linked": linked, "space": sp, "space_basis": basis, "categories": cats,
            "has_windows": bool(S.openings(sp, kinds=["window"]))}
    if linked:
        info["fixtures_2d"] = dict(collections.Counter(f["type"] for f in project2d.get("fixtures", [])))
        info["project2d_id"] = project2d.get("id")
        info["categories"] = {catalog.get(pl["product"])["category"] for pl in project2d.get("placements", []) if catalog.get(pl["product"])}
    else:
        tmp = {"space": sp, "lines": [{"id": f"L{i + 1}", "product": c, "mount": catalog.get(c)["default_mount"], "qty": None}
                                      for i, c in enumerate(codes) if catalog.get(c)], "fixtures": []}
        recs = recommend_all(tmp, catalog, rules) if tmp["lines"] else {}
        info["rec_counts"] = {catalog.get(l["product"])["short"]: (recs[l["id"]]["qty_rec"] or 1) for l in tmp["lines"]}
        info["rec_counts_by_code"] = {l["product"]: (recs[l["id"]]["qty_rec"] or 1) for l in tmp["lines"]}
    return info


def build_layout(project: dict, info: dict, brief: dict, project2d: dict | None, catalog: Catalog, rules: Rules) -> dict:
    sp = info["space"]
    log: dict = {"placed": [], "skipped": []}
    if info["linked"] and project2d:
        lines = copy.deepcopy(project2d.get("lines", []))
        placements = copy.deepcopy(project2d.get("placements", []))
        fx2d = copy.deepcopy(project2d.get("fixtures", []))
        base = {"space": sp, "lines": lines, "placements": placements, "fixtures": []}
        decor = [r for r in brief.get("furniture", []) if r["type"] not in {f["type"] for f in fx2d}]
        added, log = furnish(base, catalog, rules, requests=decor, mode="3d", existing=fx2d)
        fixtures = added
        zones = copy.deepcopy(project2d.get("zones", []))
    else:
        counts = {p["code"]: p["count"] for p in brief.get("product_counts", [])}
        lines = []
        for i, c in enumerate(project["input"].get("products", [])):
            prod = catalog.get(c)
            if not prod:
                continue
            q = counts.get(c) or info.get("rec_counts_by_code", {}).get(c) or 1
            lines.append({"id": f"L{i + 1}", "product": c, "mount": prod["default_mount"], "qty": int(q)})
        base = {"space": sp, "lines": lines, "placements": [], "fixtures": []}
        layout_lines(base, catalog, rules)
        placements = base["placements"]
        fixtures, log = furnish(base, catalog, rules, requests=brief.get("furniture", []), mode="3d")
        base["fixtures"] = fixtures
        strategies = {l["id"]: line_strategy(base, l, catalog) for l in lines}
        zones = suggest_zones(base, catalog, strategies)
    return {"space": sp, "lines": lines, "placements": placements, "fixtures": fixtures, "zones": zones, "log": log}


def _content_for(prod: dict, brief: dict) -> str:
    c = prod.get("content") or "brand"
    if c in ("brand", "info") and brief.get("screen_content") in ("brand", "menu", "info", "art"):
        return brief["screen_content"]
    return c


def scene_spec(layout: dict, brief: dict, catalog: Catalog, cuts: list[dict], quality: str = "standard",
               title: str = "", out_dir: str = "") -> dict:
    sp = layout["space"]
    q = QUALITY.get(quality, QUALITY["standard"])
    products = []
    for pl in layout["placements"]:
        prod = catalog.get(pl["product"])
        if not prod:
            continue
        mount = pl.get("mount") or prod["default_mount"]
        if prod["category"] == "hvac_cassette":
            products.append({"id": pl["id"], "category": "hvac_cassette", "sw": prod["w"], "sh": prod["h"], "depth": prod["h"],
                             "fd": prod["d"], "x": pl["x"], "y": pl["y"], "rot": pl.get("rot", 0), "bottom": sp["height"] - prod["h"],
                             "mount": "ceiling", "bezel": 0, "content": None, "double": False, "label": prod["short"]})
            continue
        portrait = pl.get("portrait")
        if portrait is None:
            portrait = native_portrait(prod)
        sw, sh = screen_size(prod, portrait)
        bezel = prod.get("bezel_mm")
        if bezel is None:
            bezel = 0 if prod["category"] in ("led_allinone", "led_cabinet") else 12
        products.append({"id": pl["id"], "category": prod["category"], "sw": sw, "sh": sh, "depth": prod["d"],
                         "fd": footprint_depth(prod, mount), "x": pl["x"], "y": pl["y"], "rot": pl.get("rot", 0),
                         "bottom": pl.get("bottom", 0), "mount": mount, "bezel": min(float(bezel), 40.0),
                         "content": _content_for(prod, brief), "double": bool(prod.get("double_sided")), "label": prod["short"],
                         "strength": 3.6 if prod.get("brightness_nit", 500) >= 2500 else 3.0})
    furniture = []
    wood_bench = brief.get("concept") in ("gallery_warm", "natural_cafe", "industrial", "premium_lounge")
    for f in layout["fixtures"]:
        ft = FURN_TYPES.get(f["type"], FURN_TYPES["block"])
        furniture.append({"id": f["id"], "type": f["type"], "builder": ft["builder"], "x": f["x"], "y": f["y"], "rot": f.get("rot", 0),
                          "w": f["w"], "d": f["d"], "h": f.get("h", ft["h"]), "seats": f.get("seats", ft.get("seats", 1)),
                          "style": "wood" if wood_bench else "fabric", "label": f.get("label")})
    e = S.main_entrance(sp)
    ent = None
    if e:
        mid = S.opening_mid(sp, e, 0)
        ent = {"wall": e["wall"], "x": mid[0], "y": mid[1]}
    zones = [{"no": z["no"], "name": z.get("name", ""), "x": (z["x0"] + z["x1"]) / 2, "y": (z["y0"] + z["y1"]) / 2}
             for z in layout.get("zones", [])]
    return {
        "version": 1, "title": title,
        "room": {"width": sp["width"], "depth": sp["depth"], "height": sp["height"], "wall_t": 200,
                 "openings": sp.get("openings", []), "pillars": sp.get("pillars", [])},
        "entrance": ent,
        "palette": {k: brief[k] for k in ("floor", "wall", "accent", "fabric")} | {"light_k": brief.get("light_k", 3000)},
        "materials_lib": LIB,
        "products": products, "furniture": furniture, "zones": zones, "cuts": cuts,
        "render": {"engine": "CYCLES", "samples": q["samples"], "res": q["res"], "preview": q["preview"], "device": "auto",
                   "lamp_w": 70.0},
        "stamp": {"text": "AI 생성 · 개략", "font": str(FONT) if FONT.exists() else None},
        "out_dir": out_dir,
    }


def cut_id(camera: str, lighting: str, variant: str) -> str:
    return f"{camera}_{lighting}_{variant}"


def make_cuts(pairs: list[tuple[str, str, str]]) -> list[dict]:
    out = []
    for cam, light, var in pairs:
        cid = cut_id(cam, light, var)
        out.append({"id": cid, "camera": cam, "lighting": light, "variant": var, "file": f"{cid}.png"})
    return out


def cut_label(camera: str, lighting: str, variant: str) -> str:
    s = f"{LIB['cameras'][camera]['label']} · {LIB['lighting'][lighting]['label']}"
    return ("도입 전 · " + s) if variant == "before" else s
