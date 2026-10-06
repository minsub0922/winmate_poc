"""배치 검증(08-birdseye §7.6.1) — 시야각 · 시청 거리 · 동선 · 전원 · 설치 높이 + 결정적 수정안 · 자동 조정.

validate(space, layout, base=…) → {warnings, overlays}
- 경고마다 rule_id · expr · params · param_status · tooltip(「pr_warn_power_distance · distance_to_power_m > 3.0 (draft)」).
- key = 종류 + 대상(같은 경고를 다시 알아봄) — 세션의 상태(fixed · ignored · memo)를 이어 붙인다.
"""
from __future__ import annotations

import copy
import math
from collections import deque
from typing import Any

from PIL import Image, ImageDraw
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import nearest_points, unary_union

from .. import text as T
from .core import INCH, group_bbox, items_by_group, main_entrance, normalize, seat_distance, seat_points, tiny_of
from .geometry import (
    angle_between, back_center, facing_vec, front_center, item_poly, r2, rect_poly, room_union, wall_geoms, width_vec,
)

KIND_TITLE = {"viewing_angle": "시야각", "viewing_distance": "시청 거리", "walkway": "동선", "power": "전원", "mount_height": "설치 높이", "unplaced": "배치"}


def _tooltip(rule_id: str, expr: str, params: dict[str, Any], status: str) -> str:
    try:
        e = expr.format(**params)
    except (KeyError, IndexError, ValueError):
        e = expr
    return f"{rule_id} · {e} ({status})"


def _warn(kind: str, rule: dict[str, Any], params: dict[str, Any], message: str, subjects: list[str], key: str, *,
          fixes: list[dict[str, Any]] | None = None, actions: list[str] | None = None, marker: list[float] | None = None,
          value: float | None = None) -> dict[str, Any]:
    status = rule.get("param_status", "draft")
    return {
        "id": "", "n": 0, "kind": kind, "title_ko": KIND_TITLE[kind], "rule_id": rule["rule_id"], "expr": rule["expr"],
        "params": params, "param_status": status, "tooltip": _tooltip(rule["rule_id"], rule["expr"], params, status),
        "message_ko": message, "subjects": subjects, "fixes": fixes or [], "actions": actions or [], "status": "open", "key": key,
        "marker": [r2(marker[0]), r2(marker[1])] if marker else None, "value": None if value is None else r2(value),
    }


# ── 장애물 ───────────────────────────────────────────────

class Scene:
    def __init__(self, space: dict[str, Any], layout: dict[str, Any], params: dict[str, Any]):
        self.space = space
        self.layout = layout
        self.p = params
        self.room = room_union(space)
        self.walls = wall_geoms(space)
        self.items = [it for it in layout.get("items", []) if not it.get("unplaced")]
        self.by_id = {it["id"]: it for it in layout.get("items", [])}
        self.groups = {g["id"]: g for g in layout.get("groups", [])}
        self.by_group = items_by_group(layout)
        self.entrance = main_entrance(space, self.walls)
        obs: list[dict[str, Any]] = []
        for w in self.walls:
            poly = w.polygon()
            for o in space.get("openings", []):
                if o.get("wall_id") != w.id or o.get("kind") != "door" or o.get("door_type") == "wall":
                    continue
                s0, s1 = o["offset"], o["offset"] + o["width"]
                k = w.t / 2 + 0.05
                cut = Polygon([(w.ax + w.ux * s0 + w.nx * k, w.ay + w.uy * s0 + w.ny * k), (w.ax + w.ux * s1 + w.nx * k, w.ay + w.uy * s1 + w.ny * k),
                               (w.ax + w.ux * s1 - w.nx * k, w.ay + w.uy * s1 - w.ny * k), (w.ax + w.ux * s0 - w.nx * k, w.ay + w.uy * s0 - w.ny * k)])
                poly = poly.difference(cut)
            obs.append({"id": f"wall:{w.id}", "name": "벽", "kind": "wall", "poly": poly, "movable": 0, "group": None})
        for c in space.get("columns", []):
            obs.append({"id": f"col:{c['id']}", "name": "기둥", "kind": "column",
                        "poly": rect_poly(c["center"][0], c["center"][1], c["w"], c["d"], 0.0), "movable": 0, "group": None})
        for k in space.get("cores", []):
            if len(k.get("polygon", [])) >= 3:
                kinds = k.get("kinds") or []
                name = " · ".join({"ev": "EV", "stairs": "계단", "toilet": "화장실", "shaft": "샤프트"}.get(x, x) for x in kinds) or "코어"
                obs.append({"id": f"core:{k['id']}", "name": name, "kind": "core", "poly": Polygon(k["polygon"]).buffer(0),
                            "movable": 0, "group": None})
        wrapped_cols = set()
        for it in self.items:
            g = self.groups.get(it["group_id"], {})
            if it["kind"] == "column_wrap":
                wrapped_cols.add((it.get("anchor") or {}).get("target"))
            movable = 2 if it["kind"] == "furniture" else (1 if it["kind"] == "product" else 0)
            nm = it.get("short") or g.get("short") or it.get("label") or "항목"
            if it["kind"] == "column_wrap":
                nm = "기둥"
            obs.append({"id": it["id"], "name": nm, "kind": it["kind"], "poly": item_poly(it), "movable": movable,
                        "group": it["group_id"], "tiny": it.get("tiny") or g.get("tiny") or nm})
        # 랩핑된 기둥은 랩핑이 대신한다(이름은 「기둥」)
        self.obstacles = [o for o in obs if not (o["kind"] == "column" and o["id"][4:] in wrapped_cols)]


# ── 시야각 · 시청 거리 ───────────────────────────────────

def _side_word(disp: dict[str, Any], seats: list[list[float]]) -> str:
    """좌석들이 디스플레이 기준 화면 왼쪽/오른쪽(앞뒤 벽 디스플레이) · 위쪽/아래쪽(옆 벽)."""
    fx, fy = facing_vec(disp["rot_deg"])
    if abs(fy) >= abs(fx):
        mean = sum(s[0] for s in seats) / len(seats)
        return "왼쪽" if mean < disp["x"] else "오른쪽"
    mean = sum(s[1] for s in seats) / len(seats)
    return "위쪽" if mean < disp["y"] else "아래쪽"


def _seats_out(disp: dict[str, Any], seat_items: list[dict[str, Any]], max_deg: float, dx: float = 0.0, dy: float = 0.0
               ) -> list[list[float]]:
    fx, fy = facing_vec(disp["rot_deg"])
    cx, cy = disp["x"], disp["y"]
    out = []
    for it in seat_items:
        for sx, sy in it.get("seat_points") or []:
            vx, vy = sx + dx - cx, sy + dy - cy
            if math.hypot(vx, vy) < 1e-6:
                continue
            th = angle_between(fx, fy, vx, vy)
            if abs(th) > max_deg + 1e-9:
                out.append([sx, sy])
    return out


def _move_ops(items: list[dict[str, Any]], dx: float, dy: float) -> list[dict[str, Any]]:
    return [{"op": "move", "item": it["id"], "dx": r2(dx), "dy": r2(dy)} for it in items]


def _check_viewing(sc: Scene, base: dict[str, Any] | None) -> list[dict[str, Any]]:
    rule_a = sc.p["viewing_angle"]
    rule_d = sc.p["viewing_distance"]
    max_deg = float(rule_a["max_angle_deg"])
    base_by = {it["id"]: it for it in (base or {}).get("items", [])}
    out: list[dict[str, Any]] = []
    for gid, g in sorted(sc.groups.items(), key=lambda kv: int(kv[0][1:]) if kv[0][1:].isdigit() else 0):
        seat_items = [it for it in sc.by_group.get(gid, []) if it.get("faces") and it.get("seat_points") and not it.get("unplaced")]
        if not seat_items:
            continue
        disp = sc.by_id.get(seat_items[0]["faces"])
        if not disp or disp.get("unplaced"):
            continue
        dname = disp.get("tiny") or disp.get("short") or "디스플레이"
        gname = g.get("short") or seat_items[0].get("short") or "좌석"
        gtiny = g.get("tiny") or seat_items[0].get("tiny") or gname
        # 시야각
        bad = _seats_out(disp, seat_items, max_deg)
        if bad:
            side = _side_word(disp, bad)
            k = len(bad)
            bd = base_by.get(disp["id"])
            cause_dx = cause_dy = 0.0
            own_dx = own_dy = 0.0
            if bd is not None:
                own_dx, own_dy = disp["x"] - bd["x"], disp["y"] - bd["y"]
                rel_dx, rel_dy = own_dx, own_dy
                s0 = seat_items[0]
                b0 = base_by.get(s0["id"])
                if b0 is not None:
                    # 좌석도 움직였다면 상대 변위 — 그중 화면 가로축 성분(어긋남)만 「함께 옮기기」로 맞춘다(사용자가 당긴 깊이는 그대로)
                    rel_dx -= s0["x"] - b0["x"]
                    rel_dy -= s0["y"] - b0["y"]
                wx, wy = width_vec(disp["rot_deg"])
                lat = rel_dx * wx + rel_dy * wy
                cause_dx, cause_dy = lat * wx, lat * wy
            moved = math.hypot(own_dx, own_dy) >= 0.05 and math.hypot(cause_dx, cause_dy) >= 0.05
            fixes: list[dict[str, Any]] = []
            if moved:
                msg = (f"{T.jo(dname, '을/를')} {T.move_label(own_dx, own_dy)} 옮겨 "
                       f"{gname} {side} {k}석이 시야각 밖이에요")
                fx_ops = _seat_fix(sc, disp, seat_items, max_deg, cause_dx, cause_dy)
                if fx_ops is not None:
                    fixes.append({"id": "f1", "label_ko": f"{gtiny} 함께 옮기기", "ops": fx_ops})
            else:
                msg = f"{gname} {side} {k}석이 {dname} 시야각 밖이에요"
                fx_ops = _seat_fix(sc, disp, seat_items, max_deg, 0.0, 0.0, search_only=True)
                if fx_ops is not None:
                    ddx, ddy = fx_ops[0]["dx"], fx_ops[0]["dy"]
                    fixes.append({"id": "f1", "label_ko": f"{gtiny} {T.move_label(ddx, ddy)}", "ops": fx_ops})
            bx = sum(s["x"] for s in seat_items) / len(seat_items)
            by = sum(s["y"] for s in seat_items) / len(seat_items)
            out.append(_warn("viewing_angle", rule_a, {"max_angle_deg": max_deg}, msg, [disp["id"]] + [s["id"] for s in seat_items],
                             f"viewing_angle:{disp['group_id']}:{gid}", fixes=fixes, actions=(["fix"] if fixes else []) + ["ignore"],
                             marker=[bx, by], value=float(k)))
            continue
        # 시청 거리(가장 가까운 열 · 가장 먼 열)
        inch = disp.get("diag_inch")
        if not inch:
            continue
        a = inch / float(rule_d["inch_per_m_max"])
        b = inch / float(rule_d["inch_per_m_min"])
        dists = [math.hypot(s["x"] - disp["x"], s["y"] - disp["y"]) for s in seat_items]
        dmin, dmax = min(dists), max(dists)
        if dmin < a - 0.05 or dmax > b + 0.05:
            off = dmin if dmin < a - 0.05 else dmax
            msg = f"{T.jo(gname, '이/가')} {dname}에서 {T.m(off)} m · 권장 {T.m(a)}~{T.m(b)} m"
            fx, fy = facing_vec(disp["rot_deg"])
            if dmin < a - 0.05:
                delta = T.ceil_step(a - dmin, 0.1)
            else:
                delta = -T.ceil_step(dmax - b, 0.1)
            ops = _move_ops(seat_items, fx * delta, fy * delta)
            fixes = [{"id": "f1", "label_ko": f"{gtiny} {T.move_label(fx * delta, fy * delta)}", "ops": ops}]
            bx = sum(s["x"] for s in seat_items) / len(seat_items)
            by = sum(s["y"] for s in seat_items) / len(seat_items)
            rule = {**rule_d}
            out.append(_warn("viewing_distance", rule, {"inch_per_m_min": rule_d["inch_per_m_min"], "inch_per_m_max": rule_d["inch_per_m_max"]},
                             msg, [disp["id"]] + [s["id"] for s in seat_items], f"viewing_distance:{disp['group_id']}:{gid}",
                             fixes=fixes, actions=["fix", "ignore"], marker=[bx, by], value=off))
    return out


def _seat_fix(sc: Scene, disp: dict[str, Any], seat_items: list[dict[str, Any]], max_deg: float, dx: float, dy: float,
              search_only: bool = False) -> list[dict[str, Any]] | None:
    """같은 변위 → 막히면 근처 0.1 m 탐색으로 모든 좌석이 다시 범위 안에 드는 가장 가까운 자세."""
    ids = {it["id"] for it in seat_items}
    others = [o["poly"] for o in sc.obstacles if o["id"] not in ids and o["kind"] in ("wall", "column", "core", "furniture", "product", "column_wrap")]
    other_u = unary_union(others) if others else Polygon()
    room_in = sc.room.buffer(1e-4)

    def ok(ddx: float, ddy: float) -> bool:
        if _seats_out(disp, seat_items, max_deg, ddx, ddy):
            return False
        for it in seat_items:
            poly = rect_poly(it["x"] + ddx, it["y"] + ddy, it["w"], it["d"], it["rot_deg"]).buffer(-0.005)
            if not room_in.contains(poly) or poly.intersects(other_u):
                return False
        return True

    if not search_only and ok(dx, dy):
        return _move_ops(seat_items, dx, dy)
    step, max_m = 0.1, 3.0
    n = int(max_m / step)
    cands = []
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            ox, oy = dx + i * step, dy + j * step
            cands.append((round(math.hypot(i * step, j * step), 4), round(ox, 3), round(oy, 3)))
    cands.sort()
    for _d, ox, oy in cands:
        if abs(ox) < 1e-9 and abs(oy) < 1e-9:
            continue
        if ok(ox, oy):
            return _move_ops(seat_items, ox, oy)
    return None


# ── 동선 ─────────────────────────────────────────────────

GRID = 0.2


def _raster(sc: Scene, inflate: float) -> tuple[Any, float, float, int, int]:
    import numpy as np

    minx, miny, maxx, maxy = sc.room.bounds
    W = int(math.ceil((maxx - minx) / GRID)) + 1
    H = int(math.ceil((maxy - miny) / GRID)) + 1
    img = Image.new("L", (W, H), 255)
    dr = ImageDraw.Draw(img)

    def draw(poly: Any, fill: int) -> None:
        for g in getattr(poly, "geoms", [poly]):
            if g.is_empty or not hasattr(g, "exterior"):
                continue
            pts = [((x - minx) / GRID, (y - miny) / GRID) for x, y in g.exterior.coords]
            if len(pts) >= 3:
                dr.polygon(pts, fill=fill)

    draw(sc.room.buffer(-inflate), 0)          # 방 안(사람 중심이 설 수 있는 곳)
    for o in sc.obstacles:
        draw(o["poly"].buffer(inflate), 255)
    arr = np.array(img) == 0                    # True = 지나갈 수 있음
    return arr, minx, miny, W, H


def _bfs(free: Any, start: tuple[int, int]) -> tuple[Any, Any]:
    import numpy as np

    H, W = free.shape
    dist = np.full((H, W), -1, dtype=np.int32)
    parent = np.full((H, W), -1, dtype=np.int32)
    sx, sy = start
    if not (0 <= sx < W and 0 <= sy < H) or not free[sy, sx]:
        return dist, parent
    dist[sy, sx] = 0
    q = deque([(sx, sy)])
    nb = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1))
    fl = free.tolist()
    dl = dist.tolist()
    pl = parent.tolist()
    while q:
        x, y = q.popleft()
        d0 = dl[y][x] + 1
        for ddx, ddy in nb:
            nx, ny = x + ddx, y + ddy
            if 0 <= nx < W and 0 <= ny < H and fl[ny][nx] and dl[ny][nx] < 0:
                if ddx and ddy and not (fl[y][nx] and fl[ny][x]):
                    continue
                dl[ny][nx] = d0
                pl[ny][nx] = y * W + x
                q.append((nx, ny))
    return np.array(dl, dtype=np.int32), np.array(pl, dtype=np.int32)


def _nearest_free(free: Any, cx: int, cy: int, max_r: int = 10) -> tuple[int, int] | None:
    H, W = free.shape
    for r in range(0, max_r + 1):
        best = None
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < H and free[y, x]:
                    key = (dx * dx + dy * dy, x, y)
                    if best is None or key < best:
                        best = key
        if best is not None:
            return best[1], best[2]
    return None


def _clusters_for_walk(sc: Scene) -> list[tuple[str, list[dict[str, Any]]]]:
    """동선 목적지: 묶음(좌석은 바라보는 디스플레이 묶음과 함께), 기둥 랩핑 제외."""
    out = []
    for gid in sorted(sc.by_group, key=lambda k: int(k[1:]) if k[1:].isdigit() else 0):
        items = [it for it in sc.by_group[gid] if not it.get("unplaced")]
        if not items or items[0]["kind"] == "column_wrap":
            continue
        out.append((gid, items))
    return out


def _check_walkway(sc: Scene) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    import numpy as np

    rule = sc.p["walkway"]
    min_m = float(rule["min_m"])
    half = float(rule.get("person_half_m", 0.25))
    if sc.entrance is None:
        return [], [], []
    free, minx, miny, W, H = _raster(sc, half)
    ex, ey = sc.entrance["inside"]
    st = _nearest_free(free, int(round((ex - minx) / GRID)), int(round((ey - miny) / GRID)))
    if st is None:
        return [], [], []
    dist, parent = _bfs(free, st)
    paths: list[dict[str, Any]] = []
    path_pts_all: list[tuple[float, float, str]] = []
    for gid, items in _clusters_for_walk(sc):
        u = unary_union([item_poly(it) for it in items])
        ring = u.buffer(half + 0.35)
        x0, y0, x1, y1 = ring.bounds
        best = None
        for gx in range(max(0, int((x0 - minx) / GRID)), min(W, int((x1 - minx) / GRID) + 2)):
            for gy in range(max(0, int((y0 - miny) / GRID)), min(H, int((y1 - miny) / GRID) + 2)):
                if not free[gy, gx] or dist[gy, gx] < 0:
                    continue
                px, py = minx + gx * GRID, miny + gy * GRID
                if not ring.contains(Point(px, py)):
                    continue
                key = (int(dist[gy, gx]), gx, gy)
                if best is None or key < best:
                    best = key
        if best is None:
            continue
        _, gx, gy = best
        pts = []
        cur = gy * W + gx
        guard = 0
        while cur >= 0 and guard < W * H:
            cy, cx = divmod(cur, W)
            pts.append((round(minx + cx * GRID, 2), round(miny + cy * GRID, 2)))
            cur = int(parent[cy, cx])
            guard += 1
        pts.reverse()
        paths.append({"target": gid, "points": [[a, b] for a, b in _simplify(pts)]})
        for a, b in pts:
            path_pts_all.append((a, b, gid))
    # 병목: 경로가 지나가는 두 장애물 사이 틈(같은 묶음끼리 · 벽에 붙은 것은 뺀다)
    if not path_pts_all:
        return [], paths, []
    lines = [LineString(pp["points"]) if len(pp["points"]) >= 2 else Point(pp["points"][0]) for pp in paths if pp["points"]]
    near_band = unary_union([ln.buffer(min_m) for ln in lines]) if lines else None
    obs = [o for o in sc.obstacles if near_band is None or o["poly"].intersects(near_band)]
    found: dict[tuple[str, str], dict[str, Any]] = {}
    for i in range(len(obs)):
        for j in range(i + 1, len(obs)):
            A, B = obs[i], obs[j]
            if A["group"] and A["group"] == B["group"]:
                continue
            if A["movable"] == 0 and B["movable"] == 0:
                continue
            gap = A["poly"].distance(B["poly"])
            if gap <= 0.02 or gap >= min_m - 1e-9:
                continue
            pa, pb = nearest_points(A["poly"], B["poly"])
            mx, my = (pa.x + pb.x) / 2, (pa.y + pb.y) / 2
            tol = gap / 2 + 0.25
            through = any(math.hypot(px - mx, py - my) <= tol for px, py, _g in path_pts_all)
            if not through:
                continue
            key = tuple(sorted((A["group"] or A["id"], B["group"] or B["id"])))
            prev = found.get(key)
            if prev is None or gap < prev["gap"] - 1e-9:
                found[key] = {"A": A, "B": B, "gap": gap, "mid": (mx, my), "pa": (pa.x, pa.y), "pb": (pb.x, pb.y)}
    warnings = []
    bottlenecks = []
    for key in sorted(found):
        f = found[key]
        A, B = f["A"], f["B"]
        na = len(sc.by_group.get(A["group"], [])) if A["group"] else 99
        nb = len(sc.by_group.get(B["group"], [])) if B["group"] else 99
        if B["movable"] > A["movable"] or (B["movable"] == A["movable"] and (nb, B["id"]) < (na, A["id"])):
            A, B = B, A
            pa, pb = f["pb"], f["pa"]
        else:
            pa, pb = f["pa"], f["pb"]
        w = round(f["gap"], 1)
        a_name = A["name"]
        b_name = B["name"]
        w_show = math.floor(w * 10 + 1e-6) / 10      # 기준 미만 폭은 내림 표기(1.16 → 「1.1 m」, 「권장 1.2 m 이상」과 겹치지 않게)
        msg = f"{a_name}{T.josa(a_name, '과/와')} {b_name} 사이 통로 {T.m(w_show)} m · 권장 {T.m(min_m)} m 이상"
        fixes: list[dict[str, Any]] = []
        if A["movable"] > 0:
            nx, ny = pa[0] - pb[0], pa[1] - pb[1]
            if abs(nx) >= abs(ny):
                ux, uy = (1.0 if nx > 0 else -1.0), 0.0
            else:
                ux, uy = 0.0, (1.0 if ny > 0 else -1.0)
            delta = T.ceil_step(min_m - f["gap"], 0.1)
            items = sc.by_group.get(A["group"], []) if A["group"] else []
            ops = _move_ops(items or [sc.by_id[A["id"]]], ux * delta, uy * delta)
            tiny = A.get("tiny") or a_name
            fixes.append({"id": "f1", "label_ko": f"{tiny} {T.dir_word(ux, uy)} {T.m(delta)} m", "ops": ops})
        subjects = sorted({x for x in (A["id"], B["id"])})
        warnings.append(_warn("walkway", rule, {"min_m": min_m}, msg, subjects, f"walkway:{key[0]}|{key[1]}", fixes=fixes,
                              actions=(["fix"] if fixes else []) + ["ignore"], marker=list(f["mid"]), value=w))
        bottlenecks.append({"pos": [r2(f["mid"][0]), r2(f["mid"][1])], "width": w, "a": A["id"], "b": B["id"]})
    return warnings, paths, bottlenecks


def _simplify(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(pts) <= 2:
        return pts
    line = LineString(pts)
    simp = line.simplify(0.15)
    return [(round(x, 2), round(y, 2)) for x, y in simp.coords]


# ── 전원 ─────────────────────────────────────────────────

def _check_power(sc: Scene) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rule = sc.p["power"]
    max_m = float(rule["max_m"])
    pts = sc.layout.get("power_points") or sc.space.get("power_points") or []
    out: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for gid in sorted(sc.by_group, key=lambda k: int(k[1:]) if k[1:].isdigit() else 0):
        g = sc.groups.get(gid) or {}
        items = [it for it in sc.by_group[gid] if it["kind"] == "product" and not it.get("unplaced")]
        if not items:
            continue
        # 묶음의 전원 입구 = 뒷면 중앙(묶음 가운데)
        backs = [back_center(it) for it in items]
        bx = sum(b[0] for b in backs) / len(backs)
        by = sum(b[1] for b in backs) / len(backs)
        label = g.get("label") or items[0].get("label") or "제품"
        if not pts:
            msg = f"{label} 근처 전원 위치를 몰라요"
            out.append(_warn("power", rule, {"max_m": max_m}, msg, [it["id"] for it in items], f"power:{gid}",
                             actions=["add_power", "memo"], marker=[bx, by]))
            links.append({"group_id": gid, "a": [r2(bx), r2(by)], "b": None, "d": None})
            continue
        best = min(pts, key=lambda p: (round(math.hypot(p["pos"][0] - bx, p["pos"][1] - by), 4), p["id"]))
        d = math.hypot(best["pos"][0] - bx, best["pos"][1] - by)
        links.append({"group_id": gid, "a": [r2(bx), r2(by)], "b": [r2(best["pos"][0]), r2(best["pos"][1])], "d": r2(d)})
        if d > max_m + 1e-9:
            msg = f"{label}에서 가까운 콘센트까지 {T.m(d)} m · {rule.get('memo_text', '바닥 배선 필요')}"
            out.append(_warn("power", rule, {"max_m": max_m}, msg, [it["id"] for it in items], f"power:{gid}",
                             actions=["add_power", "memo"], marker=[bx, by], value=d))
    return out, links


def _check_mount(sc: Scene) -> list[dict[str, Any]]:
    rule = sc.p["mount_height"]
    if not rule.get("show", False):
        return []
    lo, hi = float(rule["min_m"]), float(rule["max_m"])
    out = []
    for it in sc.items:
        if it["kind"] != "product" or it.get("mount") not in ("wall", "window_facing"):
            continue
        z = float(it.get("z") or 0)
        if z < lo or z > hi:
            msg = f"{it.get('short') or '디스플레이'} 아래 모서리 높이 {T.m(z)} m · 권장 {T.m(lo)}~{T.m(hi)} m"
            out.append(_warn("mount_height", rule, {"min_m": lo, "max_m": hi}, msg, [it["id"]], f"mount:{it['id']}",
                             actions=["ignore"], marker=[it["x"], it["y"]], value=z))
    return out


def _fans(sc: Scene) -> list[dict[str, Any]]:
    rule_a = sc.p["viewing_angle"]
    rule_d = sc.p["viewing_distance"]
    out = []
    seen = set()
    for it in sc.items:
        if it["kind"] != "product" or it.get("role") not in ("led_wall", "display", "interactive", "window_signage"):
            continue
        if it.get("mount") == "window_facing":
            continue
        if it["group_id"] in seen:
            continue
        seen.add(it["group_id"])
        inch = it.get("diag_inch") or 55.0
        fx, fy = facing_vec(it["rot_deg"])
        ax, ay = front_center(it)
        out.append({"item_id": it["id"], "apex": [r2(ax), r2(ay)], "dir_deg": round(math.degrees(math.atan2(fy, fx)), 1),
                    "half_angle_deg": float(rule_a["max_angle_deg"]), "min_d": r2(inch / float(rule_d["inch_per_m_max"])),
                    "max_d": r2(inch / float(rule_d["inch_per_m_min"]))})
    return out


# ── 공개 ─────────────────────────────────────────────────

def validate(space: dict[str, Any], layout: dict[str, Any], *, params: dict[str, Any], base: dict[str, Any] | None = None,
             statuses: dict[str, str] | None = None, walkway: bool = True) -> dict[str, Any]:
    sc = Scene(space, layout, params)
    warnings: list[dict[str, Any]] = []
    warnings += _check_viewing(sc, base)
    paths: list[dict[str, Any]] = []
    bottlenecks: list[dict[str, Any]] = []
    if walkway:
        ww, paths, bottlenecks = _check_walkway(sc)
        warnings += ww
    pw, links = _check_power(sc)
    warnings += pw
    warnings += _check_mount(sc)
    for it in layout.get("items", []):
        if it.get("unplaced"):
            name = it.get("short") or it.get("label") or "항목"
            rule = {"rule_id": "be_unplaced", "expr": "no_free_pose_within({max_m} m)", "param_status": "draft"}
            warnings.append(_warn("unplaced", rule, {"max_m": params["collision"]["max_m"]}, f"{T.jo(name, '을/를')} 놓을 자리가 없어요",
                                  [it["id"]], f"unplaced:{it['id']}", actions=["ignore"], marker=[it["x"], it["y"]]))
    statuses = statuses or {}
    for w in warnings:
        st = statuses.get(w["key"])
        if st in ("ignored", "memo"):
            w["status"] = st
    _assign_ids(warnings)
    overlays = {"fans": _fans(sc), "paths": paths, "bottlenecks": bottlenecks, "power_links": links,
                "entrance": sc.entrance["inside"] if sc.entrance else None}
    return {"warnings": warnings, "overlays": overlays}


def _assign_ids(warnings: list[dict[str, Any]]) -> None:
    order = {"viewing_angle": 0, "viewing_distance": 1, "walkway": 2, "power": 3, "mount_height": 4, "unplaced": 5}
    warnings.sort(key=lambda w: (0 if w.get("status", "open") == "open" else 1, order.get(w["kind"], 9), w["key"]))
    n = 0
    for i, w in enumerate(warnings, start=1):
        w["id"] = f"w{i}"
        if w.get("status", "open") == "open":
            n += 1
            w["n"] = n
        else:
            w["n"] = 0


def autofix(space: dict[str, Any], layout: dict[str, Any], *, params: dict[str, Any], base: dict[str, Any] | None = None,
            statuses: dict[str, str] | None = None, include_power: bool = True) -> tuple[dict[str, Any], dict[str, str]]:
    """시야각 · 동선 경고는 첫 수정안을 차례로(적용 뒤 새 경고가 생기면 건너뜀), 전원 경고는 「메모로 남기기」."""
    from .ops import apply_ops

    statuses = dict(statuses or {})
    cur = copy.deepcopy(layout)
    res = validate(space, cur, params=params, base=base, statuses=statuses)
    for _round in range(6):
        changed = False
        before_keys = {w["key"] for w in res["warnings"] if w["status"] == "open"}
        for w in res["warnings"]:
            if w["status"] != "open" or w["kind"] not in ("viewing_angle", "viewing_distance", "walkway") or not w["fixes"]:
                continue
            trial = apply_ops(space, cur, w["fixes"][0]["ops"], params=params)
            tres = validate(space, trial, params=params, base=base, statuses=statuses)
            after_keys = {x["key"] for x in tres["warnings"] if x["status"] == "open"}
            # 같은 디스플레이 · 좌석 쌍의 시청 거리 경고는 시야각에 가려 있던 것이라 「새 경고」로 보지 않는다
            pair = w["key"].split(":", 1)[1] if w["kind"] in ("viewing_angle", "viewing_distance") else None
            new = {k for k in after_keys - before_keys if not (pair and k.split(":", 1)[-1] == pair and k.startswith("viewing_"))}
            if new:
                continue
            if w["key"] in after_keys:
                continue
            cur = trial
            statuses[w["key"]] = "fixed"
            res = tres
            changed = True
            break
        if not changed:
            break
    if include_power:
        for w in res["warnings"]:
            if w["kind"] == "power" and w["status"] == "open":
                statuses[w["key"]] = "memo"
                memo = f"{_power_subject(w)} · {params['power'].get('memo_text', '바닥 배선 필요')}"
                if memo not in cur.setdefault("memos", []):
                    cur["memos"].append(memo)
        res = validate(space, cur, params=params, base=base, statuses=statuses)
    cur["warnings"] = merge_fixed(res["warnings"], layout.get("warnings", []), statuses)
    return normalize(cur), statuses


def _power_subject(w: dict[str, Any]) -> str:
    msg = w.get("message_ko", "")
    for sep in ("에서 가까운", " 근처 전원"):
        if sep in msg:
            return msg.split(sep)[0]
    return msg


def merge_fixed(current: list[dict[str, Any]], previous: list[dict[str, Any]], statuses: dict[str, str]) -> list[dict[str, Any]]:
    """지금 경고 + 고쳐서 사라진 경고(status=fixed, 기록용)."""
    keys = {w["key"] for w in current}
    out = [dict(w) for w in current]
    for w in previous:
        if w.get("key") in keys:
            continue
        if statuses.get(w.get("key", "")) == "fixed":
            x = dict(w)
            x["status"] = "fixed"
            out.append(x)
    _assign_ids(out)
    return out


def refresh_seats(layout: dict[str, Any]) -> None:
    for it in layout.get("items", []):
        if it.get("seats"):
            it["seat_points"] = seat_points(it)


__all__ = ["validate", "autofix", "merge_fixed", "refresh_seats", "INCH", "seat_distance", "tiny_of", "group_bbox", "front_center"]
