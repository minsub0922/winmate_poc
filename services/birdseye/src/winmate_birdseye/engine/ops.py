"""레이아웃 연산(08-birdseye §5.3) — 엔진에서 결정적으로 적용한다.

{op:'move', item, dx, dy} · {op:'set_pos', item, pos:[x,y]} · {op:'rotate', item, deg} · {op:'add', spec} · {op:'remove', item} ·
{op:'set_qty', group, qty} · {op:'add_power', pos} · {op:'set_size', product|group, size}
item 자리에 묶음 id(g…)를 주면 묶음 전체에 적용한다.
"""
from __future__ import annotations

import copy
import math
from typing import Any

from .core import computed_dims, group_label, normalize, seat_points, size_inch
from .geometry import facing_vec, r2, rdeg, width_vec


def _targets(layout: dict[str, Any], ref: str | None) -> list[dict[str, Any]]:
    if not ref:
        return []
    items = layout.get("items", [])
    direct = [it for it in items if it["id"] == ref]
    if direct:
        return direct
    grp = [it for it in items if it["group_id"] == ref]
    if grp:
        return grp
    return [it for it in items if it.get("ref") == ref]


def _group(layout: dict[str, Any], gid: str | None) -> dict[str, Any] | None:
    for g in layout.get("groups", []):
        if g["id"] == gid:
            return g
    if gid:
        for g in layout.get("groups", []):
            if g.get("ref") == gid:
                return g
    return None


def _next_item_id(layout: dict[str, Any]) -> str:
    n = 0
    for it in layout.get("items", []):
        tail = it["id"][2:]
        if tail.isdigit():
            n = max(n, int(tail))
    return f"li{n + 1}"


def _next_group_id(layout: dict[str, Any]) -> str:
    n = 0
    for g in layout.get("groups", []):
        tail = g["id"][1:]
        if tail.isdigit():
            n = max(n, int(tail))
    return f"g{n + 1}"


def _snap_rot(rot: float) -> float:
    """15° 단위 · 벽과 평행(0 · 90 · 180 · 270)에 가까우면 붙인다."""
    r = round(rot / 15.0) * 15.0
    for k in (0, 90, 180, 270, 360):
        if abs(r - k) < 7.5:
            r = k
    return rdeg(r)


def apply_ops(space: dict[str, Any], layout: dict[str, Any], ops: list[dict[str, Any]], *, params: dict[str, Any] | None = None
              ) -> dict[str, Any]:
    params = params or {}
    out = copy.deepcopy(layout)
    for op in ops:
        o = op if isinstance(op, dict) else op.model_dump(exclude_none=True)
        kind = o.get("op")
        if kind == "move":
            for it in _targets(out, o.get("item") or o.get("group")):
                if it.get("locked"):
                    continue
                it["x"] = r2(it["x"] + float(o.get("dx") or 0))
                it["y"] = r2(it["y"] + float(o.get("dy") or 0))
                it["unplaced"] = False
        elif kind == "set_pos":
            tg = _targets(out, o.get("item"))
            pos = o.get("pos") or []
            if tg and len(pos) == 2:
                cx = sum(t["x"] for t in tg) / len(tg)
                cy = sum(t["y"] for t in tg) / len(tg)
                for it in tg:
                    it["x"] = r2(it["x"] + pos[0] - cx)
                    it["y"] = r2(it["y"] + pos[1] - cy)
                    it["unplaced"] = False
        elif kind == "rotate":
            tg = _targets(out, o.get("item") or o.get("group"))
            if tg:
                deg = float(o.get("deg") or 0)
                cx = sum(t["x"] for t in tg) / len(tg)
                cy = sum(t["y"] for t in tg) / len(tg)
                th = math.radians(deg)
                for it in tg:
                    dx, dy = it["x"] - cx, it["y"] - cy
                    it["x"] = r2(cx + dx * math.cos(th) - dy * math.sin(th))
                    it["y"] = r2(cy + dx * math.sin(th) + dy * math.cos(th))
                    it["rot_deg"] = _snap_rot(it.get("rot_deg", 0.0) + deg)
        elif kind == "remove":
            ids = {it["id"] for it in _targets(out, o.get("item") or o.get("group"))}
            out["items"] = [it for it in out["items"] if it["id"] not in ids]
            for g in out["groups"]:
                g["item_ids"] = [i for i in g["item_ids"] if i not in ids]
            out["groups"] = [g for g in out["groups"] if g["item_ids"]]
            for g in out["groups"]:
                _relabel(out, g)
        elif kind == "add":
            spec = dict(o.get("spec") or {})
            gid = spec.pop("group_id", None)
            g = _group(out, gid) if gid else None
            if g is None:
                g = {"id": _next_group_id(out), "kind": spec.get("kind", "furniture"), "ref": spec.get("ref", ""),
                     "label": spec.get("label", "항목"), "plan_label": spec.get("label", "항목"), "at_label": spec.get("at_label", ""),
                     "anchor_label": "", "family_id": spec.get("family_id"), "model_code": spec.get("model_code"), "qty": 0,
                     "qty_source": "user", "rule_id": None, "item_ids": [], "short": spec.get("short", spec.get("label", "")),
                     "tiny": spec.get("tiny", spec.get("short", spec.get("label", ""))), "size": None}
                out["groups"].append(g)
            it = {
                "id": _next_item_id(out), "kind": spec.get("kind", "furniture"), "ref": spec.get("ref", ""), "group_id": g["id"],
                "label": g["label"], "short": spec.get("short", g.get("short", "")), "tiny": spec.get("tiny", g.get("tiny", "")),
                "x": r2(float(spec.get("x", 0))), "y": r2(float(spec.get("y", 0))), "rot_deg": rdeg(float(spec.get("rot_deg", 0))),
                "w": r2(float(spec.get("w", 1.0))), "d": r2(float(spec.get("d", 0.6))), "h": r2(float(spec.get("h", 0.8))),
                "z": r2(float(spec.get("z", 0))), "mount": spec.get("mount", "floor"),
                "anchor": spec.get("anchor") or {"type": "free", "target": None, "label": ""}, "qty_in_group": 1,
                "qty_source": "user", "rule_id": None, "faces": spec.get("faces"), "seats": int(spec.get("seats", 0)),
                "seat_points": [], "locked": False, "unplaced": False, "role": spec.get("role"), "diag_inch": spec.get("diag_inch"),
                "parts": spec.get("parts") or [],
            }
            out["items"].append(it)
            g["item_ids"].append(it["id"])
            g["qty"] = len(g["item_ids"]) if g["kind"] != "furniture" or not g.get("rows") else g["qty"]
            _relabel(out, g)
        elif kind == "set_qty":
            g = _group(out, o.get("group") or o.get("item"))
            if g is not None and o.get("qty"):
                _set_qty(out, g, max(1, int(o["qty"])), params)
        elif kind == "add_power":
            pos = o.get("pos") or []
            if len(pos) == 2:
                pts = out.setdefault("power_points", [])
                n = 0
                for p in pts:
                    tail = str(p.get("id", ""))[1:]
                    if tail.isdigit():
                        n = max(n, int(tail))
                pts.append({"id": f"p{n + 1}", "pos": [r2(pos[0]), r2(pos[1])], "source": "user"})
        elif kind == "set_size":
            g = _group(out, o.get("group") or o.get("product") or o.get("item"))
            size = o.get("size")
            if g is not None and size:
                _set_size(out, g, str(size))
    for it in out["items"]:
        if it.get("seats"):
            it["seat_points"] = seat_points(it)
    return normalize(out)


def _relabel(layout: dict[str, Any], g: dict[str, Any]) -> None:
    items = [it for it in layout["items"] if it["group_id"] == g["id"]]
    n = len(items)
    if g["kind"] == "furniture" and any(it.get("faces") for it in items):
        g["qty"] = n
        g["label"] = f"{g.get('label_core') or g.get('short') or g['label']} {n}열" if n > 0 else g["label"]
        g["plan_label"] = g["label"]
    elif g["kind"] == "column_wrap":
        g["qty"] = n
        g["label"] = "기둥 랩핑" + (f" ×{n}" if n > 1 else "")
        g["plan_label"] = g["label"]
    else:
        g["qty"] = n
        core = g.get("label_core") or g.get("short") or g["label"]
        g["label"] = group_label(core, n)
        g["plan_label"] = f"{g['label']} ({g['anchor_label']})" if g.get("anchor_label") else g["label"]
    for it in items:
        it["label"] = g["label"]
        it["qty_in_group"] = g["qty"]


def _set_qty(layout: dict[str, Any], g: dict[str, Any], qty: int, params: dict[str, Any]) -> None:
    items = [it for it in layout["items"] if it["group_id"] == g["id"]]
    if not items:
        return
    if len(items) == qty:
        g["qty_source"] = "user"
        return
    faces = items[0].get("faces")
    if faces:
        disp = next((it for it in layout["items"] if it["id"] == faces), None)
        if disp is not None:
            items.sort(key=lambda it: (round(math.hypot(it["x"] - disp["x"], it["y"] - disp["y"]), 3), it["id"]))
            fx, fy = facing_vec(disp["rot_deg"])
        else:
            fx, fy = facing_vec(items[0]["rot_deg"] + 180)
        pitch = float(params.get("row_pitch_m", 0.9))
        if qty < len(items):
            drop = {it["id"] for it in items[qty:]}
            layout["items"] = [it for it in layout["items"] if it["id"] not in drop]
            g["item_ids"] = [i for i in g["item_ids"] if i not in drop]
        else:
            last = items[-1]
            for k in range(1, qty - len(items) + 1):
                it = copy.deepcopy(last)
                it["id"] = _next_item_id(layout)
                it["x"] = r2(last["x"] + fx * pitch * k)
                it["y"] = r2(last["y"] + fy * pitch * k)
                layout["items"].append(it)
                g["item_ids"].append(it["id"])
        g["qty_source"] = "user"
        _relabel(layout, g)
        return
    if g["kind"] == "column_wrap":
        if qty < len(items):
            drop = {it["id"] for it in sorted(items, key=lambda it: it["id"])[qty:]}
            layout["items"] = [it for it in layout["items"] if it["id"] not in drop]
            g["item_ids"] = [i for i in g["item_ids"] if i not in drop]
        g["qty_source"] = "user"
        _relabel(layout, g)
        return
    # 제품 · 가구 줄: 지금 묶음 가운데를 기준으로 폭 축을 따라 다시 벌린다
    first = items[0]
    ux, uy = width_vec(first["rot_deg"])
    gap = float(params.get("group_gap_m", 0.1)) if first.get("mount") == "window_facing" else float(params.get("wall_item_gap_m", 0.3))
    if first["kind"] == "furniture":
        gap = 0.6
    cx = sum(it["x"] for it in items) / len(items)
    cy = sum(it["y"] for it in items) / len(items)
    span = qty * first["w"] + (qty - 1) * gap
    keep = sorted(items, key=lambda it: it["id"])
    new_items: list[dict[str, Any]] = []
    for i in range(qty):
        off = -span / 2 + first["w"] / 2 + i * (first["w"] + gap)
        if i < len(keep):
            it = keep[i]
        else:
            it = copy.deepcopy(first)
            it["id"] = _next_item_id({"items": layout["items"] + new_items})
            g["item_ids"].append(it["id"])
            new_items.append(it)
        it["x"] = r2(cx + ux * off)
        it["y"] = r2(cy + uy * off)
    drop = {it["id"] for it in keep[qty:]}
    layout["items"] = [it for it in layout["items"] if it["id"] not in drop] + new_items
    g["item_ids"] = [i for i in g["item_ids"] if i not in drop]
    g["qty_source"] = "user"
    _relabel(layout, g)


def _set_size(layout: dict[str, Any], g: dict[str, Any], size: str) -> None:
    by = g.get("dims_by_size") or {}
    dims = by.get(size)
    if dims is None:
        inch = size_inch(size)
        if not inch:
            return
        dims = computed_dims(inch)
    for it in layout["items"]:
        if it["group_id"] != g["id"]:
            continue
        old_d = it["d"]
        it["w"], it["h"], it["d"] = r2(dims["w"]), r2(dims["h"]), r2(dims["d"])
        # 벽 면은 그대로(깊이 차이만큼 중심 이동)
        fx, fy = facing_vec(it["rot_deg"])
        dd = (it["d"] - old_d) / 2
        it["x"] = r2(it["x"] + fx * dd)
        it["y"] = r2(it["y"] + fy * dd)
        it["diag_inch"] = size_inch(size)
    g["size"] = size
    if (g.get("models_by_size") or {}).get(size):
        g["model_code"] = g["models_by_size"][size]
    if len(g.get("size_options") or []) > 1:
        g["label_core"] = f"{g.get('short') or ''} {size}".strip()
    _relabel(layout, g)
