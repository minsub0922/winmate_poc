"""공간(직사각형 방) 모델 도우미 — 벽·개구부·기둥·콘센트·장애물."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import geometry as G
from .catalog import Catalog, footprint_depth, native_portrait, screen_size

WALLS = ("front", "back", "left", "right")
WALL_NAMES = {"front": "정면", "back": "후면", "left": "왼쪽 측벽", "right": "오른쪽 측벽"}
OPENING_NAMES = {"window": "유리창", "entrance": "출입구", "door": "문"}
OPPOSITE = {"front": "back", "back": "front", "left": "right", "right": "left"}
# 벽에 붙여 방 안쪽을 보게 설치할 때의 rot / 창 밖(도로)을 보게 할 때의 rot
INWARD_ROT = {"front": 180.0, "back": 0.0, "left": 90.0, "right": 270.0}
OUTWARD_ROT = {"front": 0.0, "back": 180.0, "left": 270.0, "right": 90.0}


def wall_length(space: dict, wall: str) -> float:
    return space["width"] if wall in ("front", "back") else space["depth"]


def wall_point(space: dict, wall: str, t: float, inset: float = 0.0) -> G.Pt:
    """벽을 따라 좌표 t(정면·후면은 x, 측벽은 y), 벽에서 안쪽으로 inset 떨어진 점."""
    W, D = space["width"], space["depth"]
    if wall == "front":
        return (t, inset)
    if wall == "back":
        return (t, D - inset)
    if wall == "left":
        return (inset, t)
    return (W - inset, t)


def wall_of_point(space: dict, p: G.Pt, tol: float = 400.0) -> str | None:
    W, D = space["width"], space["depth"]
    x, y = p
    cands = [("front", y), ("back", D - y), ("left", x), ("right", W - x)]
    w, d = min(cands, key=lambda c: c[1])
    return w if d <= tol else None


def openings(space: dict, wall: str | None = None, kinds=None) -> list[dict]:
    out = []
    for o in space.get("openings", []):
        if wall and o["wall"] != wall:
            continue
        if kinds and o["kind"] not in kinds:
            continue
        out.append(o)
    return out


def entrance_wall(space: dict) -> str:
    for kind in ("entrance", "door"):
        for o in space.get("openings", []):
            if o["kind"] == kind:
                return o["wall"]
    return "front"


def main_entrance(space: dict) -> dict | None:
    for kind in ("entrance", "door"):
        for o in space.get("openings", []):
            if o["kind"] == kind:
                return o
    return None


def opening_mid(space: dict, o: dict, inset: float = 0.0) -> G.Pt:
    return wall_point(space, o["wall"], o["start"] + o["length"] / 2.0, inset)


def free_spans(space: dict, wall: str, clear: float = 0.0, blocks: list[tuple[float, float]] | None = None) -> list[tuple[float, float]]:
    """벽을 따라 개구부(±clear)·모서리(clear)·추가 구간을 뺀 빈 구간들."""
    L = wall_length(space, wall)
    spans = [(clear, L - clear)]
    cuts = [(o["start"] - clear, o["start"] + o["length"] + clear) for o in openings(space, wall)]
    cuts += list(blocks or [])
    for a, b in cuts:
        nxt = []
        for s, e in spans:
            if b <= s or a >= e:
                nxt.append((s, e))
                continue
            if a > s:
                nxt.append((s, a))
            if b < e:
                nxt.append((b, e))
        spans = nxt
    return [(s, e) for s, e in spans if e - s > 1.0]


def pillar_poly(p: dict) -> G.Poly:
    return G.rect_poly(p["x"] - p["w"] / 2, p["y"] - p["d"] / 2, p["x"] + p["w"] / 2, p["y"] + p["d"] / 2)


def room_poly(space: dict) -> G.Poly:
    return G.rect_poly(0, 0, space["width"], space["depth"])


def outlet_wall(space: dict, o: dict) -> str | None:
    on = o.get("on") or ""
    if on.startswith("wall:"):
        return on.split(":", 1)[1]
    if on.startswith("pillar:"):
        return None
    return wall_of_point(space, (o["x"], o["y"]), tol=300)


# ── 제품 배치 기하 ──

def placement_dims(pl: dict, prod: dict) -> tuple[float, float, float]:
    """(바닥 점유 가로, 바닥 점유 깊이, 화면 세로) — 설치 방향·방식 반영."""
    portrait = pl.get("portrait")
    if portrait is None:
        portrait = native_portrait(prod)
    sw, sh = screen_size(prod, portrait)
    fd = footprint_depth(prod, pl.get("mount") or prod["default_mount"])
    if prod["category"] == "hvac_cassette":
        return prod["w"], prod["d"], prod["h"]
    return sw, fd, sh


def placement_poly(pl: dict, prod: dict) -> G.Poly:
    fw, fd, _ = placement_dims(pl, prod)
    return G.rot_rect(pl["x"], pl["y"], fw, fd, pl.get("rot", 0.0))


def placement_band(pl: dict, prod: dict, space: dict) -> tuple[float, float]:
    """제품이 차지하는 높이 구간(mm). 바닥에 서는 방식은 0부터."""
    _, _, sh = placement_dims(pl, prod)
    mount = pl.get("mount") or prod["default_mount"]
    bottom = float(pl.get("bottom", 0.0))
    if prod["category"] == "hvac_cassette" or mount == "ceiling":
        return space["height"] - prod["h"] - 300, space["height"]
    if mount in ("floor_stand", "stand", "floor_lean"):
        return 0.0, bottom + sh
    return bottom, bottom + sh


def is_floor_obstacle(pl: dict, prod: dict) -> bool:
    mount = pl.get("mount") or prod["default_mount"]
    return mount in ("floor_stand", "stand", "floor_lean")


def fixture_poly(f: dict) -> G.Poly:
    return G.rot_rect(f["x"], f["y"], f["w"], f["d"], f.get("rot", 0.0))


@dataclass
class Obstacle:
    id: str
    kind: str  # pillar | product | fixture
    label: str
    poly: G.Poly
    z0: float
    z1: float
    movable: bool
    ref: dict = field(default_factory=dict)

    @property
    def floor(self) -> bool:
        return self.z0 < 1200  # 사람이 부딪히는 높이대


def obstacles(project: dict, catalog: Catalog) -> list[Obstacle]:
    space = project["space"]
    obs: list[Obstacle] = []
    for p in space.get("pillars", []):
        obs.append(Obstacle(p["id"], "pillar", p.get("label") or f"기둥 {p['id']}", pillar_poly(p), 0, space["height"], False, p))
    for pl in project.get("placements", []):
        prod = catalog.get(pl["product"])
        if not prod:
            continue
        z0, z1 = placement_band(pl, prod, space)
        obs.append(Obstacle(pl["id"], "product", prod["short"], placement_poly(pl, prod), z0, z1, False, pl))
    for f in project.get("fixtures", []):
        obs.append(Obstacle(f["id"], "fixture", f.get("label") or f["type"], fixture_poly(f), 0, f.get("h", 900), True, f))
    return obs


def door_zone(space: dict, o: dict, depth: float) -> G.Poly:
    a, b = o["start"], o["start"] + o["length"]
    W, D = space["width"], space["depth"]
    if o["wall"] == "front":
        return G.rect_poly(a, 0, b, depth)
    if o["wall"] == "back":
        return G.rect_poly(a, D - depth, b, D)
    if o["wall"] == "left":
        return G.rect_poly(0, a, depth, b)
    return G.rect_poly(W - depth, a, W, b)


def area_m2(space: dict) -> float:
    return space["width"] * space["depth"] / 1e6


def pyeong(m2: float) -> float:
    return m2 / 3.3058


def letter_labels(space: dict) -> dict[str, str]:
    """유리창 A·B… 처럼 같은 종류 개구부에 붙일 라벨."""
    out, counters = {}, {}
    for o in space.get("openings", []):
        if o.get("label"):
            out[o["id"]] = o["label"]
            continue
        k = o["kind"]
        counters[k] = counters.get(k, 0) + 1
        out[o["id"]] = f"{OPENING_NAMES.get(k, k)} {chr(64 + counters[k])}" if k == "window" else f"{OPENING_NAMES.get(k, k)} {counters[k]}"
    return out


def angle_between(a: float, b: float) -> float:
    d = abs((a - b) % 360.0)
    return min(d, 360.0 - d)


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def nearest_outlet(space: dict, p: G.Pt) -> tuple[dict | None, float]:
    best, bd = None, math.inf
    for o in space.get("outlets", []):
        d = G.manhattan(p, (o["x"], o["y"]))
        if d < bd:
            best, bd = o, d
    return best, bd
