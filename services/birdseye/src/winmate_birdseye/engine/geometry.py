"""엔진 기하 도우미 — 순수 함수(모델 호출 없음). 좌표는 m, 화면 기준(x → 오른쪽, y → 아래).

항목 = 회전된 사각형: 중심 (x, y), 폭 w(폭 축 = (cos θ, sin θ)), 깊이 d(앞 = 화면 면 = (−sin θ, cos θ)).
rot_deg = 0 이면 앞이 +y(아래), 180 이면 −y(위·정면 창 쪽).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union


def r2(v: float) -> float:
    out = round(float(v) + 0.0, 2)
    return 0.0 if out == 0 else out


def r1(v: float) -> float:
    out = round(float(v) + 0.0, 1)
    return 0.0 if out == 0 else out


def rdeg(v: float) -> float:
    out = round(float(v) % 360.0, 1)
    return 0.0 if out in (0.0, 360.0) else out


def facing_vec(rot: float) -> tuple[float, float]:
    t = math.radians(rot)
    return (-math.sin(t), math.cos(t))


def width_vec(rot: float) -> tuple[float, float]:
    t = math.radians(rot)
    return (math.cos(t), math.sin(t))


def rot_for_facing(fx: float, fy: float) -> float:
    return rdeg(math.degrees(math.atan2(-fx, fy)))


def rect_corners(x: float, y: float, w: float, d: float, rot: float) -> list[tuple[float, float]]:
    ux, uy = width_vec(rot)
    fx, fy = facing_vec(rot)
    hw, hd = w / 2.0, d / 2.0
    return [
        (x - ux * hw - fx * hd, y - uy * hw - fy * hd),
        (x + ux * hw - fx * hd, y + uy * hw - fy * hd),
        (x + ux * hw + fx * hd, y + uy * hw + fy * hd),
        (x - ux * hw + fx * hd, y - uy * hw + fy * hd),
    ]


def rect_poly(x: float, y: float, w: float, d: float, rot: float) -> Polygon:
    return Polygon(rect_corners(x, y, w, d, rot))


def item_poly(it: dict[str, Any]) -> Polygon:
    return rect_poly(it["x"], it["y"], it["w"], it["d"], it.get("rot_deg", 0.0))


def front_center(it: dict[str, Any]) -> tuple[float, float]:
    fx, fy = facing_vec(it.get("rot_deg", 0.0))
    return (it["x"] + fx * it["d"] / 2.0, it["y"] + fy * it["d"] / 2.0)


def back_center(it: dict[str, Any]) -> tuple[float, float]:
    fx, fy = facing_vec(it.get("rot_deg", 0.0))
    return (it["x"] - fx * it["d"] / 2.0, it["y"] - fy * it["d"] / 2.0)


@dataclass
class WallGeom:
    id: str
    ax: float
    ay: float
    bx: float
    by: float
    t: float
    label: str
    kind: str
    dim_known: bool
    length: float
    ux: float
    uy: float
    nx: float
    ny: float

    def point(self, s: float) -> tuple[float, float]:
        return (self.ax + self.ux * s, self.ay + self.uy * s)

    def inner(self, s: float, off: float) -> tuple[float, float]:
        """벽 안쪽 면에서 off 만큼 방 안으로."""
        px, py = self.point(s)
        k = self.t / 2.0 + off
        return (px + self.nx * k, py + self.ny * k)

    def project(self, x: float, y: float) -> tuple[float, float]:
        """점 → (벽 따라 s, 벽 선에서 안쪽으로 거리)."""
        dx, dy = x - self.ax, y - self.ay
        return (dx * self.ux + dy * self.uy, dx * self.nx + dy * self.ny)

    @property
    def facing_rot(self) -> float:
        return rot_for_facing(self.nx, self.ny)

    def polygon(self) -> Polygon:
        return LineString([(self.ax, self.ay), (self.bx, self.by)]).buffer(self.t / 2.0, cap_style=2)


def room_union(space: dict[str, Any]) -> Polygon | MultiPolygon:
    """방 외곽들의 합 + 공간 사이 벽의 문(통로)."""
    polys = [Polygon(r["outline"]).buffer(0) for r in space.get("rooms", []) if len(r.get("outline", [])) >= 3]
    if not polys:
        return Polygon([(0, 0), (10, 0), (10, 8), (0, 8)])
    walls = {w["id"]: w for w in space.get("walls", [])}
    for o in space.get("openings", []):
        w = walls.get(o.get("wall_id"))
        if o.get("kind") != "door" or not w or w.get("kind") != "interior":
            continue
        ax, ay = w["a"]
        bx, by = w["b"]
        L = math.hypot(bx - ax, by - ay)
        if L < 1e-6:
            continue
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = -uy, ux
        half = float(w.get("thickness", 0.2)) / 2 + 0.2
        s0, s1 = o["offset"], o["offset"] + o["width"]
        pts = [(ax + ux * s0 + nx * half, ay + uy * s0 + ny * half), (ax + ux * s1 + nx * half, ay + uy * s1 + ny * half),
               (ax + ux * s1 - nx * half, ay + uy * s1 - ny * half), (ax + ux * s0 - nx * half, ay + uy * s0 - ny * half)]
        polys.append(Polygon(pts))
    u = unary_union(polys)
    return u


def bbox(space: dict[str, Any]) -> tuple[float, float, float, float]:
    u = room_union(space)
    minx, miny, maxx, maxy = u.bounds
    return (minx, miny, maxx, maxy)


def wall_geoms(space: dict[str, Any]) -> list[WallGeom]:
    room = room_union(space)
    out: list[WallGeom] = []
    for w in space.get("walls", []):
        ax, ay = w["a"]
        bx, by = w["b"]
        L = math.hypot(bx - ax, by - ay)
        if L < 1e-6:
            continue
        ux, uy = (bx - ax) / L, (by - ay) / L
        nx, ny = -uy, ux
        t = float(w.get("thickness", 0.2) or 0.2)
        mx, my = (ax + bx) / 2.0, (ay + by) / 2.0
        probe = Point(mx + nx * (t / 2.0 + 0.3), my + ny * (t / 2.0 + 0.3))
        if not room.contains(probe):
            nx, ny = -nx, -ny
        out.append(WallGeom(w["id"], ax, ay, bx, by, t, w.get("label", ""), w.get("kind", "exterior"),
                            bool(w.get("dim_known", False)), L, ux, uy, nx, ny))
    return out


def intervals_subtract(base: tuple[float, float], cuts: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    segs = [base]
    for c0, c1 in sorted(cuts):
        nxt: list[tuple[float, float]] = []
        for s0, s1 in segs:
            if c1 <= s0 or c0 >= s1:
                nxt.append((s0, s1))
                continue
            if c0 > s0:
                nxt.append((s0, c0))
            if c1 < s1:
                nxt.append((c1, s1))
        segs = nxt
    return [(a, b) for a, b in segs if b - a > 1e-6]


def ray_depth(room: Polygon | MultiPolygon, x: float, y: float, fx: float, fy: float, limit: float = 200.0) -> float:
    """(x, y) 에서 앞 방향으로 방 경계까지 거리."""
    line = LineString([(x, y), (x + fx * limit, y + fy * limit)])
    inter = line.intersection(room.boundary)
    best = limit
    for g in getattr(inter, "geoms", [inter]):
        if g.is_empty:
            continue
        for px, py in getattr(g, "coords", []):
            dist = math.hypot(px - x, py - y)
            if dist > 1e-6:
                best = min(best, dist)
    return best


def angle_between(ax: float, ay: float, bx: float, by: float) -> float:
    """두 벡터 사이 부호 있는 수평각(도)."""
    cross = ax * by - ay * bx
    dot = ax * bx + ay * by
    return math.degrees(math.atan2(cross, dot))
