"""결정적 배치 엔진 `be-engine` (08-birdseye §7.6) — 모델 호출 없음, 순수 함수.

generate(space, products, furniture, intents, params) → Layout dict
- 고정 요소 마스크(벽 · 기둥 · 코어 · 문 앞 여유 · 외곽 밖) → 크기 선택 → 수량 → 배치 순서(벽 · 창 제품 큰 순 → 기둥 랩핑 →
  정면 좌석 → 근접 가구 → 자유 가구) → 앵커 해석 → 충돌 해소(0.1 m 나선, 최대 3.0 m) → 좌석 → 검증 → 자동 조정.
- 같은 입력이면 출력 JSON 이 바이트 단위로 같다(0.01 m · 0.1° 반올림, 정렬 고정, id = 배치 순서).
"""
from __future__ import annotations

import copy
import math
from collections import defaultdict
from functools import lru_cache
from typing import Any

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from .. import text as T
from .geometry import (
    WallGeom, facing_vec, intervals_subtract, item_poly, r2, ray_depth, rdeg, rect_poly, room_union, wall_geoms, width_vec,
)

INCH = 0.0254
DISPLAY_ROLES = ("led_wall", "display", "interactive")


# ── 파라미터 ─────────────────────────────────────────────

def merged_params(base: dict[str, Any], kb_rules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """rules.yaml + KB placement_rule(active 이고 숫자 params 면 우선)."""
    p = copy.deepcopy(base)
    key_by_rule = {
        "pr_warn_viewing_angle": "viewing_angle", "pr_signage_size_by_distance": "viewing_distance",
        "pr_warn_power_distance": "power", "pr_warn_mount_height": "mount_height",
    }
    for r in kb_rules or []:
        if not r.get("active"):
            continue
        key = key_by_rule.get(r.get("id", ""))
        if not key:
            continue
        for k, v in (r.get("params") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                p[key][k] = v
                p[key]["param_status"] = r.get("status") or "active"
    return p


# ── 이름 ─────────────────────────────────────────────────

def tiny_of(short: str) -> str:
    """「The Wall IAB」 → 「The Wall」, 「Flip Pro WA75D」 → 「Flip Pro」, 「OH55C」 → 「OH55C」."""
    toks = (short or "").split()
    if len(toks) >= 2:
        last = toks[-1]
        if any(c.isdigit() for c in last) or (last.isupper() and len(last) <= 4 and last.isalpha()):
            return " ".join(toks[:-1])
    return short


def anchor_label_for_wall(w: WallGeom | None) -> str:
    if w is None:
        return ""
    lab = (w.label or "").strip()
    if lab in ("정면", "전면", "앞"):
        return "정면 벽"
    if lab in ("후면", "뒤", "뒤쪽"):
        return "후면 벽"
    if lab in ("왼쪽", "오른쪽", "좌측", "우측", "측면"):
        return "측벽"
    if not lab:
        return "벽"
    return lab if lab.endswith("벽") else f"{lab} 벽"


def wall_name(w: WallGeom) -> str:
    lab = (w.label or "").strip() or "벽"
    return lab if lab.endswith("벽") else f"{lab} 벽"


# ── 배치기 ───────────────────────────────────────────────

@lru_cache(maxsize=4)
def _floor_offsets(step: float, max_m: float) -> tuple[tuple[float, float, float], ...]:
    n = int(round(max_m / step))
    out = []
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            dx, dy = round(i * step, 4), round(j * step, 4)
            dist = math.hypot(dx, dy)
            if 0 < dist <= max_m + 1e-9:
                out.append((round(dist, 4), dx, dy))
    out.sort()
    return tuple(out)


class Placer:
    def __init__(self, space: dict[str, Any], params: dict[str, Any]):
        self.space = space
        self.p = params
        self.room = room_union(space)
        self.room_in = self.room.buffer(1e-4)
        self.walls = wall_geoms(space)
        self.wall_by = {w.id: w for w in self.walls}
        self.openings = sorted(space.get("openings", []), key=lambda o: o["id"])
        self.columns = sorted(space.get("columns", []), key=lambda c: c["id"])
        self.cores = sorted(space.get("cores", []), key=lambda c: c["id"])
        self.ceiling = float((space.get("ceiling_h") or {}).get("value") or 3.0)
        fixed: list[Polygon] = [w.polygon() for w in self.walls]
        for c in self.columns:
            fixed.append(rect_poly(c["center"][0], c["center"][1], c["w"], c["d"], 0.0))
        for k in self.cores:
            if len(k.get("polygon", [])) >= 3:
                fixed.append(Polygon(k["polygon"]).buffer(0))
        self.door_zones: list[Polygon] = []
        for o in self.openings:
            if o["kind"] != "door":
                continue
            w = self.wall_by.get(o["wall_id"])
            if w is None:
                continue
            depth = float(self.p.get("door_clear_depth_m", 1.2))
            s0, s1 = o["offset"], o["offset"] + o["width"]
            pts = [w.inner(s0, 0), w.inner(s1, 0), w.inner(s1, depth), w.inner(s0, depth)]
            self.door_zones.append(Polygon(pts))
        self.fixed_union = unary_union(fixed + self.door_zones) if (fixed or self.door_zones) else Polygon()
        self.placed: list[tuple[str, Polygon]] = []
        self.wall_occ: dict[str, list[tuple[float, float]]] = defaultdict(list)
        self.window_occ: dict[str, list[tuple[float, float]]] = defaultdict(list)
        self.items: list[dict[str, Any]] = []
        self.groups: list[dict[str, Any]] = []
        self.assumptions: list[dict[str, Any]] = []
        self.warnings_extra: list[dict[str, Any]] = []
        self.n_item = 0
        self.n_group = 0
        self.entrance = main_entrance(space, self.walls)

    # ── 충돌 ─────────────────────────────────────────
    def blocked(self, poly: Polygon, ignore: frozenset[str] = frozenset(), *, ignore_fixed: bool = False) -> bool:
        if not self.room_in.contains(poly):
            return True
        shr = poly.buffer(-0.005)
        if shr.is_empty:
            shr = poly
        if not ignore_fixed and shr.intersects(self.fixed_union):
            return True
        for iid, p in self.placed:
            if iid not in ignore and shr.intersects(p):
                return True
        return False

    def search_floor(self, x: float, y: float, w: float, d: float, rot: float, ignore: frozenset[str] = frozenset()
                     ) -> tuple[float, float, float] | None:
        if not self.blocked(rect_poly(x, y, w, d, rot), ignore):
            return (x, y, rot)
        step = float(self.p["collision"]["step_m"])
        max_m = float(self.p["collision"]["max_m"])
        for rot_try in (rot, rdeg(rot + 90), rdeg(rot + 270)):
            cands = []
            for dist, dx, dy in _floor_offsets(step, max_m):
                cands.append((dist, r2(x + dx), r2(y + dy)))
            for _dist, cx, cy in cands:
                if not self.blocked(rect_poly(cx, cy, w, d, rot_try), ignore):
                    return (cx, cy, rot_try)
        return None

    def search_wall(self, wall: WallGeom, s: float, off: float, w: float, d: float, rot: float,
                    ignore: frozenset[str] = frozenset()) -> tuple[float, float, float] | None:
        step = float(self.p["collision"]["step_m"])
        n = int(round(float(self.p["collision"]["max_m"]) / step))
        for k in [0] + [v for i in range(1, n + 1) for v in (i, -i)]:
            s2 = s + k * step
            if s2 - w / 2 < -1e-6 or s2 + w / 2 > wall.length + 1e-6:
                continue
            x, y = wall.inner(s2, off)
            if not self.blocked(rect_poly(x, y, w, d, rot), ignore):
                return (r2(x), r2(y), s2)
        return None

    # ── 벽 빈 구간 ──────────────────────────────────
    def wall_free(self, wall: WallGeom) -> list[tuple[float, float]]:
        cuts: list[tuple[float, float]] = []
        for o in self.openings:
            if o["wall_id"] == wall.id:
                cuts.append((o["offset"] - 0.1, o["offset"] + o["width"] + 0.1))
        line = LineString([(wall.ax, wall.ay), (wall.bx, wall.by)])
        near = float(self.p.get("wall_near_block_m", 1.0))
        blocks: list[Polygon] = [rect_poly(c["center"][0], c["center"][1], c["w"], c["d"], 0.0) for c in self.columns]
        blocks += [Polygon(k["polygon"]).buffer(0) for k in self.cores if len(k.get("polygon", [])) >= 3]
        for poly in blocks:
            if poly.distance(line) <= near:
                ss = [wall.project(px, py)[0] for px, py in poly.exterior.coords]
                cuts.append((min(ss) - 0.1, max(ss) + 0.1))
        for other in self.walls:
            if other.id == wall.id:
                continue
            for px, py in ((other.ax, other.ay), (other.bx, other.by)):
                s, dist = wall.project(px, py)
                if abs(dist) <= wall.t and -0.01 <= s <= wall.length + 0.01:
                    cuts.append((s - other.t / 2 - 0.01, s + other.t / 2 + 0.01))
        cuts += self.wall_occ.get(wall.id, [])
        return intervals_subtract((0.0, wall.length), cuts)

    def longest_free(self, exclude_walls: set[str] | None = None, min_len: float = 0.0) -> tuple[WallGeom, tuple[float, float]] | None:
        best: tuple[float, str, WallGeom, tuple[float, float]] | None = None
        for wall in self.walls:
            if exclude_walls and wall.id in exclude_walls:
                continue
            for seg in self.wall_free(wall):
                L = seg[1] - seg[0]
                if L < min_len:
                    continue
                key = (round(L, 4), wall.id)
                if best is None or key[0] > best[0] + 1e-9 or (abs(key[0] - best[0]) <= 1e-9 and wall.id < best[1]):
                    best = (key[0], wall.id, wall, seg)
        if best is None:
            return None
        return best[2], best[3]

    # ── 항목 · 묶음 ─────────────────────────────────
    def new_group(self, **kw: Any) -> dict[str, Any]:
        self.n_group += 1
        g = {"id": f"g{self.n_group}", "item_ids": [], **kw}
        self.groups.append(g)
        return g

    def add_item(self, group: dict[str, Any], **kw: Any) -> dict[str, Any]:
        self.n_item += 1
        it = {"id": f"li{self.n_item}", "group_id": group["id"], **kw}
        for k in ("x", "y", "w", "d", "h", "z"):
            if k in it and it[k] is not None:
                it[k] = r2(it[k])
        it["rot_deg"] = rdeg(it.get("rot_deg", 0.0))
        self.items.append(it)
        group["item_ids"].append(it["id"])
        self.placed.append((it["id"], item_poly(it)))
        return it


def main_entrance(space: dict[str, Any], walls: list[WallGeom]) -> dict[str, Any] | None:
    """주출입구: is_main · door_type=main → 정면 벽의 가장 넓은 문 → 가장 넓은 문 → 정면 벽 가운데(가상)."""
    wall_by = {w.id: w for w in walls}
    doors = [o for o in space.get("openings", []) if o["kind"] == "door" and o.get("door_type") != "wall" and o["wall_id"] in wall_by]
    pick = None
    mains = sorted([o for o in doors if o.get("is_main") or o.get("door_type") == "main"], key=lambda o: o["id"])
    if mains:
        pick = mains[0]
    else:
        front = [o for o in doors if (wall_by[o["wall_id"]].label or "") in ("정면", "전면")]
        cand = front or doors
        if cand:
            pick = sorted(cand, key=lambda o: (-o["width"], o["id"]))[0]
    if pick is not None:
        w = wall_by[pick["wall_id"]]
        s = pick["offset"] + pick["width"] / 2
        ix, iy = w.inner(s, 0.5)
        return {"opening_id": pick["id"], "wall_id": w.id, "s": s, "width": pick["width"], "inside": [r2(ix), r2(iy)],
                "nx": w.nx, "ny": w.ny, "virtual": False}
    if not walls:
        return None
    w = next((x for x in walls if (x.label or "") in ("정면", "전면")), walls[0])
    s = w.length / 2
    ix, iy = w.inner(s, 0.5)
    return {"opening_id": None, "wall_id": w.id, "s": s, "width": 1.0, "inside": [r2(ix), r2(iy)], "nx": w.nx, "ny": w.ny,
            "virtual": True}


# ── 제품 치수 · 크기 ─────────────────────────────────────

def dims_for(product: dict[str, Any], size: str | None) -> dict[str, float]:
    by = product.get("dims_by_size") or {}
    if size and size in by:
        return by[size]
    if product.get("dims_m"):
        return product["dims_m"]
    inch = size_inch(size) or product.get("diag_inch")
    if inch:
        return computed_dims(inch)
    return {"w": 1.2, "h": 0.7, "d": 0.08}


def size_inch(size: str | None) -> float | None:
    if not size:
        return None
    digits = "".join(ch for ch in str(size) if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def computed_dims(inch: float) -> dict[str, float]:
    """screen_size_inch · 16:9 · 베젤 3% · 깊이 0.08 m(§7.6)."""
    diag = inch * INCH
    k = math.sqrt(16 ** 2 + 9 ** 2)
    return {"w": round(diag * 16 / k * 1.03, 3), "h": round(diag * 9 / k * 1.03, 3), "d": 0.08}


def mount_z(role: str, h: float, mount: str) -> float:
    if mount == "window_facing":
        return 1.2
    if mount == "floor":
        return 0.0
    if role == "interactive":
        return 0.9
    if h >= 1.5:
        return 0.9
    return max(0.8, 1.5 - h / 2)


# ── 의도(앵커) ───────────────────────────────────────────

def _first_outdoor_window(space: dict[str, Any]) -> dict[str, Any] | None:
    wins = [o for o in space.get("openings", []) if o["kind"] == "window"]
    if not wins:
        return None
    outdoor = [o for o in wins if o.get("faces_outdoor")]
    pool = outdoor or wins
    return sorted(pool, key=lambda o: (-o["width"] if not outdoor else 0, o["id"]))[0]


def rule_intents(space: dict[str, Any], products: list[dict[str, Any]], furniture: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """intent:rules — 디스플레이 큰 순 → 가장 긴 빈 벽, 창 사이니지 → 창, 랩핑 → 기둥, 좌석 → 가장 큰 디스플레이 정면,
    나머지 → 창 쪽 빈 영역 · 입구 · 빈 벽."""
    out: dict[str, dict[str, Any]] = {}
    win = _first_outdoor_window(space)
    for p in products:
        role = p.get("role") or "display"
        if role == "window_signage":
            out[p["id"]] = {"anchor": f"window:{win['id']}" if win else "wall"}
        elif role == "kiosk":
            out[p["id"]] = {"anchor": "entrance"}
        else:
            out[p["id"]] = {"anchor": "wall"}
    displays = [p for p in products if (p.get("role") or "display") in DISPLAY_ROLES]
    largest = max(displays, key=lambda p: (p.get("diag_inch") or _max_size(p) or 0, -p.get("order", 0)), default=None)
    interactive = next((p for p in sorted(products, key=lambda p: p.get("order", 0)) if p.get("role") == "interactive"), None)
    for f in furniture:
        a = f.get("anchor") or "free"
        if a == "column":
            out[f["id"]] = {"anchor": "column"}
        elif a == "faces_display":
            out[f["id"]] = {"anchor": f"faces:{largest['id']}" if largest else "free"}
        elif a == "near_display":
            tgt = interactive or (min(displays, key=lambda p: (p.get("diag_inch") or 0, p.get("order", 0))) if displays else None)
            out[f["id"]] = {"anchor": f"near:{tgt['id']}" if tgt else "free"}
        elif a == "entrance":
            out[f["id"]] = {"anchor": "entrance"}
        elif a == "window_area":
            out[f["id"]] = {"anchor": f"window_area:{win['id']}" if win else "free"}
        elif a == "wall":
            out[f["id"]] = {"anchor": "wall"}
        else:
            out[f["id"]] = {"anchor": "free"}
    return out


def _max_size(p: dict[str, Any]) -> float | None:
    sizes = [size_inch(s) for s in p.get("size_options") or []]
    sizes = [s for s in sizes if s]
    return max(sizes) if sizes else None


def resolve_intents(space: dict[str, Any], products: list[dict[str, Any]], furniture: list[dict[str, Any]],
                    intents: list[dict[str, Any]] | None) -> tuple[dict[str, dict[str, Any]], str]:
    """LLM 의도(닫힌 어휘)를 검증해 규칙 기본값 위에 덮는다. 맞지 않는 항목은 규칙."""
    base = rule_intents(space, products, furniture)
    if not intents:
        return base, "intent:rules"
    keys: dict[str, str] = {}
    for i, p in enumerate(sorted(products, key=lambda p: p.get("order", 0)), start=1):
        keys[f"p{i}"] = p["id"]
        keys[p["id"]] = p["id"]
        keys.setdefault(f"role:{p.get('role') or 'display'}", p["id"])      # 닫힌 어휘 — 역할로 가리켜도 된다
    for i, f in enumerate(furniture, start=1):
        keys[f"f{i}"] = f["id"]
        keys[f["id"]] = f["id"]
    wall_ids = {w["id"] for w in space.get("walls", [])}
    win_ids = {o["id"] for o in space.get("openings", []) if o["kind"] == "window"}
    col_ids = {c["id"] for c in space.get("columns", [])}
    pids = {p["id"] for p in products}
    used = False
    for it in intents:
        iid = keys.get(str(it.get("item") or ""))
        if not iid:
            continue
        a = str(it.get("anchor") or "")
        kind, _, tgt = a.partition(":")
        if tgt and tgt in keys:
            tgt = keys[tgt]
        ok = (
            (kind == "wall" and (not tgt or tgt in wall_ids))
            or (kind == "window" and (not tgt or tgt in win_ids))
            or (kind == "window_area" and (not tgt or tgt in win_ids))
            or (kind == "column" and (not tgt or tgt in col_ids))
            or (kind in ("faces", "near") and tgt in pids)
            or kind in ("entrance", "free")
        )
        entry = dict(base.get(iid, {}))
        if ok:
            entry["anchor"] = f"{kind}:{tgt}" if tgt else kind
        # 앵커가 맞지 않으면 앵커는 규칙 그대로 두고 수량 · 위치 라벨만 받는다
        if isinstance(it.get("qty"), int) and 1 <= it["qty"] <= 50:
            entry["qty"] = it["qty"]
        if it.get("at_label"):
            entry["at_label"] = T.clip(str(it["at_label"]), 10)
        base[iid] = entry
        used = True
    return base, ("intent:llm" if used else "intent:rules")


# ── 생성 ─────────────────────────────────────────────────

def generate(space: dict[str, Any], products: list[dict[str, Any]], furniture: list[dict[str, Any]], *,
             intents: list[dict[str, Any]] | None = None, params: dict[str, Any], version: int = 1,
             autofix_initial: bool = True) -> dict[str, Any]:
    from .validate import autofix, validate

    products = sorted(products, key=lambda p: (p.get("order", 0), p["id"]))
    furniture = sorted([f for f in furniture if f.get("selected", True)], key=lambda f: (f.get("order", 0), f["id"]))
    plan, path = resolve_intents(space, products, furniture, intents)
    pl = Placer(space, params)

    # 1) 벽 · 창 부착 제품(큰 순) → 바닥 제품
    def size_key(p: dict[str, Any]) -> float:
        return p.get("diag_inch") or _max_size(p) or 0.0

    wall_products = [p for p in products if not plan[p["id"]]["anchor"].startswith("entrance")]
    wall_products.sort(key=lambda p: (-size_key(p), p.get("order", 0), p["id"]))
    for p in wall_products:
        _place_product(pl, p, plan[p["id"]])
    for p in products:
        if plan[p["id"]]["anchor"].startswith("entrance"):
            _place_product(pl, p, plan[p["id"]])

    # 2) 기둥 랩핑 → 3) 정면 좌석 → 4) 근접 가구 → 5) 자유 가구
    stage = {"column": 2, "faces": 3, "near": 4, "entrance": 4}
    furn_sorted = sorted(furniture, key=lambda f: (stage.get(plan[f["id"]]["anchor"].split(":")[0], 5), f.get("order", 0), f["id"]))
    for f in furn_sorted:
        _place_furniture(pl, f, plan[f["id"]], products)

    layout = {
        "version": version,
        "items": pl.items,
        "groups": pl.groups,
        "warnings": [],
        "assumptions": _dedupe(pl.assumptions),
        "memos": [],
        "power_points": copy.deepcopy(space.get("power_points", [])),
        "engine_version": params.get("engine_version", "be-engine/1"),
        "created_by": "engine",
        "parent_version": None,
        "meta_paths": [path],
    }
    res = validate(space, layout, params=params)
    layout["warnings"] = res["warnings"] + pl.warnings_extra
    _number(layout["warnings"])
    if autofix_initial:
        layout, _ = autofix(space, layout, params=params, include_power=False)
    return normalize(layout)


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for a in items:
        k = (a.get("kind"), a.get("ref"), a.get("text_ko"))
        if k in seen:
            continue
        seen.add(k)
        out.append(a)
    return out


def _number(warnings: list[dict[str, Any]]) -> None:
    order = {"viewing_angle": 0, "viewing_distance": 1, "walkway": 2, "power": 3, "mount_height": 4, "unplaced": 5}
    warnings.sort(key=lambda w: (0 if w.get("status", "open") == "open" else 1, order.get(w["kind"], 9), w.get("key", "")))
    n = 0
    for w in warnings:
        if w.get("status", "open") == "open":
            n += 1
            w["n"] = n
        else:
            w["n"] = 0


def normalize(layout: dict[str, Any]) -> dict[str, Any]:
    """반올림 · 정렬 고정(바이트 단위로 같은 출력)."""
    for it in layout.get("items", []):
        for k in ("x", "y", "w", "d", "h", "z"):
            if it.get(k) is not None:
                it[k] = r2(it[k])
        it["rot_deg"] = rdeg(it.get("rot_deg", 0.0))
        it["seat_points"] = [[r2(a), r2(b)] for a, b in it.get("seat_points", [])]
    layout["items"].sort(key=lambda it: int(it["id"][2:]) if it["id"][2:].isdigit() else 10 ** 6)
    layout["groups"].sort(key=lambda g: int(g["id"][1:]) if g["id"][1:].isdigit() else 10 ** 6)
    return layout


# ── 제품 배치 ────────────────────────────────────────────

def _product_base(p: dict[str, Any], size: str | None, qty: int, qty_source: str) -> dict[str, Any]:
    short = p.get("short") or p.get("display_name") or "제품"
    label_core = f"{short} {size}" if size and len(p.get("size_options") or []) > 1 else short
    return {"label_core": label_core, "short": short, "tiny": tiny_of(short), "qty": qty, "qty_source": qty_source}


def group_label(label_core: str, qty: int) -> str:
    return f"{label_core} ×{qty}" if qty > 1 else label_core


def _pextra(p: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    return {"label_core": base["label_core"], "size_options": list(p.get("size_options") or []),
            "dims_by_size": copy.deepcopy(p.get("dims_by_size") or {}), "models_by_size": dict(p.get("models_by_size") or {})}


def _place_product(pl: Placer, p: dict[str, Any], intent: dict[str, Any]) -> None:
    role = p.get("role") or "display"
    anchor = intent.get("anchor") or "wall"
    kind, _, target = anchor.partition(":")
    qty = int(intent.get("qty") or p.get("qty") or 1)
    qty_source = "user" if p.get("qty_user") else "suggested"
    if p.get("qty_user"):
        qty = int(p["qty_user"])
    size = p.get("chosen_size")
    if kind == "window":
        win = next((o for o in pl.openings if o["id"] == target), None) if target else _first_outdoor_window(pl.space)
        if win is None:
            kind = "wall"
        else:
            if not size and p.get("size_options"):
                size = sorted(p["size_options"], key=lambda s: size_inch(s) or 0)[-1] if len(p["size_options"]) == 1 else _pick_window_size(p, win)
            dims = dims_for(p, size)
            _place_window_group(pl, p, win, dims, size, qty, qty_source, intent, role)
            return
    if kind == "entrance":
        dims = dims_for(p, size or (p.get("size_options") or [None])[0])
        base = _product_base(p, size, qty, qty_source)
        g = pl.new_group(kind="product", ref=p["id"], label=group_label(base["label_core"], qty), family_id=p.get("family_id"),
                         model_code=_model_for(p, size), qty=qty, qty_source=qty_source, rule_id=None, short=base["short"],
                         tiny=base["tiny"], size=size, anchor_label="입구", at_label=intent.get("at_label") or "입구", **_pextra(p, base))
        g["plan_label"] = f"{g['label']} (입구)"
        for i in range(qty):
            pos = _entrance_pos(pl, dims["w"], dims["d"], i)
            _add_floor_item(pl, g, kind="product", ref=p["id"], label=g["label"], short=base["short"], tiny=base["tiny"],
                            x=pos[0], y=pos[1], rot=pos[2], w=dims["w"], d=dims["d"], h=dims["h"], z=0.0, mount="floor",
                            anchor={"type": "entrance", "target": pl.entrance["opening_id"] if pl.entrance else None, "label": "입구"},
                            role=role, qty=qty, qty_source=qty_source, diag=p.get("diag_inch"))
        return
    # 벽걸이
    wall_choice = None
    if target and target in pl.wall_by:
        w = pl.wall_by[target]
        segs = pl.wall_free(w)
        if segs:
            seg = max(segs, key=lambda s: (round(s[1] - s[0], 4), -s[0]))
            wall_choice = (w, seg)
    if wall_choice is None:
        wall_choice = pl.longest_free()
    if wall_choice is None:
        _unplaced(pl, p, qty, qty_source, role, size)
        return
    wall, seg = wall_choice
    if not size and p.get("size_options"):
        size = _select_size(pl, p, wall, seg)
    dims = dims_for(p, size)
    base = _product_base(p, size, qty, qty_source)
    alabel = anchor_label_for_wall(wall)
    g = pl.new_group(kind="product", ref=p["id"], label=group_label(base["label_core"], qty), family_id=p.get("family_id"),
                     model_code=_model_for(p, size), qty=qty, qty_source=qty_source, rule_id=None, short=base["short"],
                     tiny=base["tiny"], size=size, anchor_label=alabel, at_label=intent.get("at_label") or alabel, **_pextra(p, base))
    g["plan_label"] = f"{g['label']} ({alabel})"
    gap = float(pl.p.get("wall_item_gap_m", 0.3))
    span = qty * dims["w"] + (qty - 1) * gap
    center = (seg[0] + seg[1]) / 2.0
    rot = wall.facing_rot
    z = mount_z(role, dims["h"], "wall")
    for i in range(qty):
        s_i = center - span / 2 + dims["w"] / 2 + i * (dims["w"] + gap)
        found = pl.search_wall(wall, s_i, dims["d"] / 2, dims["w"], dims["d"], rot)
        unplaced = found is None
        if found is None:
            x, y = wall.inner(s_i, dims["d"] / 2)
            s_used = s_i
        else:
            x, y, s_used = found
        it = pl.add_item(g, kind="product", ref=p["id"], label=g["label"], short=base["short"], tiny=base["tiny"],
                         x=x, y=y, rot_deg=rot, w=dims["w"], d=dims["d"], h=dims["h"], z=z, mount="wall",
                         anchor={"type": "wall", "target": wall.id, "label": alabel}, qty_in_group=qty, qty_source=qty_source,
                         rule_id=None, faces=None, seats=0, seat_points=[], locked=False, unplaced=unplaced, role=role,
                         diag_inch=size_inch(size) or p.get("diag_inch"), parts=[])
        pl.wall_occ[wall.id].append((s_used - dims["w"] / 2 - gap, s_used + dims["w"] / 2 + gap))
        if unplaced:
            _unplaced_warning(pl, it)


def _model_for(p: dict[str, Any], size: str | None) -> str | None:
    if size and (p.get("models_by_size") or {}).get(size):
        return p["models_by_size"][size]
    return p.get("model_code")


def _pick_window_size(p: dict[str, Any], win: dict[str, Any]) -> str:
    opts = sorted(p["size_options"], key=lambda s: size_inch(s) or 0)
    fit = [s for s in opts if dims_for(p, s)["w"] <= win["width"]]
    return (fit or opts)[-1]


def _select_size(pl: Placer, p: dict[str, Any], wall: WallGeom, seg: tuple[float, float]) -> str:
    """앵커 벽 빈 구간 L − 양옆 0.5 m 에 들어가는 가장 큰 옵션, 최소 시청 거리 > 정면 깊이면 한 단계 작게.
    벽 폭을 모르면 가장 큰 옵션 + 가정."""
    opts = sorted(p["size_options"], key=lambda s: size_inch(s) or 0)
    if len(opts) == 1:
        return opts[0]
    if not wall.dim_known:
        size = opts[-1]
        tiny = tiny_of(p.get("short") or p.get("display_name") or "")
        pl.assumptions.append({
            "kind": "dims_missing", "ref": wall.id, "action": "BE1D",
            "text_ko": f"도면에 {wall_name(wall)} 폭이 없어 {tiny} 크기는 {size} 비율로 맞췄어요.",
        })
        return size
    margin = float(pl.p.get("wall_side_margin_m", 0.5))
    usable = (seg[1] - seg[0]) - 2 * margin
    fit = [s for s in opts if dims_for(p, s)["w"] <= usable + 1e-9]
    idx = opts.index(fit[-1]) if fit else 0
    cx, cy = wall.inner((seg[0] + seg[1]) / 2.0, 0.0)
    depth = ray_depth(pl.room, cx, cy, wall.nx, wall.ny)
    factor = float(pl.p.get("min_view_factor", 1.5))
    inch = size_inch(opts[idx]) or 0
    if inch * INCH * factor > depth and idx > 0:
        idx -= 1
    return opts[idx]


def _place_window_group(pl: Placer, p: dict[str, Any], win: dict[str, Any], dims: dict[str, float], size: str | None,
                        qty: int, qty_source: str, intent: dict[str, Any], role: str) -> None:
    wall = pl.wall_by[win["wall_id"]]
    base = _product_base(p, size, qty, qty_source)
    alabel = "창면"
    g = pl.new_group(kind="product", ref=p["id"], label=group_label(base["label_core"], qty), family_id=p.get("family_id"),
                     model_code=_model_for(p, size), qty=qty, qty_source=qty_source, rule_id=None, short=base["short"],
                     tiny=base["tiny"], size=size, anchor_label=alabel, at_label=intent.get("at_label") or alabel, **_pextra(p, base))
    g["plan_label"] = f"{g['label']} ({alabel})"
    gap = float(pl.p.get("group_gap_m", 0.1))
    span = qty * dims["w"] + (qty - 1) * gap
    s_c = win["offset"] + win["width"] / 2.0
    standoff = float(pl.p.get("window_standoff_m", 0.4))
    rot = rdeg(wall.facing_rot + 180) if win.get("faces_outdoor") else wall.facing_rot
    for i in range(qty):
        s_i = s_c - span / 2 + dims["w"] / 2 + i * (dims["w"] + gap)
        found = pl.search_wall(wall, s_i, standoff, dims["w"], dims["d"], rot)
        unplaced = found is None
        if found is None:
            x, y = wall.inner(s_i, standoff)
            s_used = s_i
        else:
            x, y, s_used = found
        it = pl.add_item(g, kind="product", ref=p["id"], label=g["label"], short=base["short"], tiny=base["tiny"],
                         x=x, y=y, rot_deg=rot, w=dims["w"], d=dims["d"], h=dims["h"], z=1.2, mount="window_facing",
                         anchor={"type": "window", "target": win["id"], "label": alabel}, qty_in_group=qty, qty_source=qty_source,
                         rule_id=None, faces=None, seats=0, seat_points=[], locked=False, unplaced=unplaced, role=role,
                         diag_inch=size_inch(size) or p.get("diag_inch"), parts=[])
        pl.window_occ[win["id"]].append((s_used - dims["w"] / 2, s_used + dims["w"] / 2))
        if unplaced:
            _unplaced_warning(pl, it)


def _unplaced(pl: Placer, p: dict[str, Any], qty: int, qty_source: str, role: str, size: str | None) -> None:
    dims = dims_for(p, size)
    base = _product_base(p, size, qty, qty_source)
    g = pl.new_group(kind="product", ref=p["id"], label=group_label(base["label_core"], qty), family_id=p.get("family_id"),
                     model_code=_model_for(p, size), qty=qty, qty_source=qty_source, rule_id=None, short=base["short"],
                     tiny=base["tiny"], size=size, anchor_label="", at_label="", **_pextra(p, base))
    g["plan_label"] = g["label"]
    minx, miny, maxx, maxy = pl.room.bounds
    it = pl.add_item(g, kind="product", ref=p["id"], label=g["label"], short=base["short"], tiny=base["tiny"],
                     x=(minx + maxx) / 2, y=(miny + maxy) / 2, rot_deg=0, w=dims["w"], d=dims["d"], h=dims["h"], z=0,
                     mount="floor", anchor={"type": "free", "target": None, "label": ""}, qty_in_group=qty, qty_source=qty_source,
                     rule_id=None, faces=None, seats=0, seat_points=[], locked=False, unplaced=True, role=role,
                     diag_inch=size_inch(size) or p.get("diag_inch"), parts=[])
    _unplaced_warning(pl, it)


def _unplaced_warning(pl: Placer, it: dict[str, Any]) -> None:
    name = it.get("short") or it.get("label") or "항목"
    pl.warnings_extra.append({
        "id": f"wu_{it['id']}", "n": 0, "kind": "unplaced", "title_ko": "배치", "rule_id": "be_unplaced",
        "expr": "no_free_pose_within(3.0 m)", "params": {"max_m": pl.p["collision"]["max_m"]}, "param_status": "draft",
        "tooltip": f"be_unplaced · no_free_pose_within({pl.p['collision']['max_m']} m) (draft)",
        "message_ko": f"{T.jo(name, '을/를')} 놓을 자리가 없어요", "subjects": [it["id"]], "fixes": [], "actions": ["ignore"],
        "status": "open", "key": f"unplaced:{it['id']}", "marker": [it["x"], it["y"]], "value": None,
    })


# ── 가구 배치 ────────────────────────────────────────────

def _furn_names(f: dict[str, Any]) -> tuple[str, str, str]:
    name = f.get("name") or "가구"
    short = f.get("short") or name
    tiny = f.get("tiny") or short
    return name, short, tiny


def _add_floor_item(pl: Placer, g: dict[str, Any], *, kind: str, ref: str, label: str, short: str, tiny: str, x: float, y: float,
                    rot: float, w: float, d: float, h: float, z: float, mount: str, anchor: dict[str, Any], role: str | None,
                    qty: int, qty_source: str, diag: float | None = None, faces: str | None = None, parts: list | None = None,
                    seats: int = 0, ignore: frozenset[str] = frozenset()) -> dict[str, Any]:
    found = pl.search_floor(x, y, w, d, rot, ignore)
    unplaced = found is None
    if found is not None:
        x, y, rot = found
    it = pl.add_item(g, kind=kind, ref=ref, label=label, short=short, tiny=tiny, x=x, y=y, rot_deg=rot, w=w, d=d, h=h, z=z,
                     mount=mount, anchor=anchor, qty_in_group=qty, qty_source=qty_source, rule_id=None, faces=faces,
                     seats=seats, seat_points=[], locked=False, unplaced=unplaced, role=role, diag_inch=diag,
                     parts=parts or [])
    if seats:
        it["seat_points"] = seat_points(it)
    if unplaced:
        _unplaced_warning(pl, it)
    return it


def seat_points(it: dict[str, Any]) -> list[list[float]]:
    n = int(it.get("seats") or 0)
    if n <= 0:
        return []
    ux, uy = width_vec(it.get("rot_deg", 0.0))
    pitch = it["w"] / n
    out = []
    for i in range(n):
        off = -it["w"] / 2 + pitch * (i + 0.5)
        out.append([r2(it["x"] + ux * off), r2(it["y"] + uy * off)])
    return out


def _place_furniture(pl: Placer, f: dict[str, Any], intent: dict[str, Any], products: list[dict[str, Any]]) -> None:
    anchor = intent.get("anchor") or "free"
    kind, _, target = anchor.partition(":")
    name, short, tiny = _furn_names(f)
    dims = f.get("dims_m") or {"w": 1.0, "d": 0.6, "h": 0.8}
    qty = int(f.get("qty") or 1)
    rows = int(f.get("rows") or 1)
    code = f.get("catalog_code")
    parts = f.get("parts") or []
    if kind == "column" or code == "column_wrap_frame":
        _place_column_wraps(pl, f, qty)
        return
    if kind == "faces":
        _place_faces(pl, f, target, rows if f.get("rows") else qty, products)
        return
    label = name if not f.get("rows") else f"{short} {rows}열"
    g = pl.new_group(kind="furniture", ref=f["id"], label_core=label, label=group_label(label, qty) if not f.get("rows") else label,
                     family_id=None, model_code=None, qty=qty if not f.get("rows") else rows, qty_source="user" if f.get("source") != "recommended" else "default",
                     rule_id=None, short=short, tiny=tiny, size=None, anchor_label="", at_label=f.get("zone") or "")
    g["plan_label"] = g["label"]
    for i in range(qty):
        if kind == "near":
            x, y, rot, alab = _near_pos(pl, target, dims, i)
            anc = {"type": "near", "target": target, "label": alab}
        elif kind == "entrance":
            x, y, rot = _entrance_pos(pl, dims["w"], dims["d"], i)
            anc = {"type": "entrance", "target": pl.entrance["opening_id"] if pl.entrance else None, "label": "입구"}
        elif kind == "window_area":
            x, y, rot = _window_area_pos(pl, target, dims, i)
            anc = {"type": "area", "target": target or None, "label": "창 쪽"}
        elif kind == "wall":
            choice = pl.longest_free(min_len=dims["w"] + 0.2)
            if choice:
                wall, seg = choice
                s = (seg[0] + seg[1]) / 2
                x, y = wall.inner(s, dims["d"] / 2)
                rot = wall.facing_rot
                pl.wall_occ[wall.id].append((s - dims["w"] / 2 - 0.3, s + dims["w"] / 2 + 0.3))
                anc = {"type": "wall", "target": wall.id, "label": anchor_label_for_wall(wall)}
            else:
                x, y, rot = _free_pos(pl, dims, i)
                anc = {"type": "free", "target": None, "label": ""}
        else:
            x, y, rot = _free_pos(pl, dims, i)
            anc = {"type": "free", "target": None, "label": ""}
        _add_floor_item(pl, g, kind="furniture", ref=f["id"], label=g["label"], short=short, tiny=tiny, x=x, y=y, rot=rot,
                        w=dims["w"], d=dims["d"], h=dims["h"], z=0.0, mount="floor", anchor=anc, role=code, qty=qty,
                        qty_source=g["qty_source"], parts=parts)


def _place_column_wraps(pl: Placer, f: dict[str, Any], qty: int) -> None:
    cols = pl.columns[: max(0, qty)] if qty else pl.columns
    if not cols:
        return
    margin = float(f.get("wrap_margin_m") or 0.1)
    h = max(0.5, pl.ceiling - 0.3)
    n = len(cols)
    label = "기둥 랩핑" + (f" ×{n}" if n > 1 else "")
    g = pl.new_group(kind="column_wrap", ref=f["id"], label_core="기둥 랩핑", label=label, family_id=None, model_code=None, qty=n, qty_source="rule",
                     rule_id=None, short="기둥 랩핑", tiny="랩핑", size=None, anchor_label="기둥", at_label="기둥")
    g["plan_label"] = label
    for c in cols:
        it = pl.add_item(g, kind="column_wrap", ref=f["id"], label=label, short="기둥 랩핑", tiny="랩핑",
                         x=c["center"][0], y=c["center"][1], rot_deg=0, w=c["w"] + 2 * margin, d=c["d"] + 2 * margin, h=h, z=0,
                         mount="column", anchor={"type": "column", "target": c["id"], "label": "기둥"}, qty_in_group=n,
                         qty_source="rule", rule_id=None, faces=None, seats=0, seat_points=[], locked=False, unplaced=False,
                         role="column_wrap_frame", diag_inch=None, parts=[])
        # 랩핑은 기둥과 겹치는 것이 정상 — 다른 항목 충돌 판정에서는 그대로 장애물


def _display_items(pl: Placer, product_id: str) -> list[dict[str, Any]]:
    return [it for it in pl.items if it["ref"] == product_id and it["kind"] == "product"]


def seat_distance(diag_inch: float | None, params: dict[str, Any]) -> float:
    if not diag_inch:
        return 3.0
    return T.ceil_step(diag_inch * INCH * float(params.get("seat_distance_factor", 1.5)), 0.5)


def _place_faces(pl: Placer, f: dict[str, Any], target: str, rows: int, products: list[dict[str, Any]]) -> None:
    name, short, tiny = _furn_names(f)
    dims = f.get("dims_m") or {"w": 2.4, "d": 0.45, "h": 0.45}
    disp = _display_items(pl, target)
    seats_flag = f.get("catalog_code") in ("viewing_bench", "operator_desk") or bool(f.get("seats"))
    label = f"{short} {rows}열" if f.get("rows") else (group_label(name, rows) if rows > 1 else name)
    g = pl.new_group(kind="furniture", ref=f["id"], label_core=short, label=label, family_id=None, model_code=None, qty=rows,
                     qty_source="user" if f.get("source") != "recommended" else "default", rule_id=None, short=short, tiny=tiny,
                     size=None, anchor_label="", at_label=f.get("zone") or "")
    g["plan_label"] = label
    if not disp:
        for i in range(rows):
            x, y, rot = _free_pos(pl, dims, i)
            _add_floor_item(pl, g, kind="furniture", ref=f["id"], label=label, short=short, tiny=tiny, x=x, y=y, rot=rot,
                            w=dims["w"], d=dims["d"], h=dims["h"], z=0.0, mount="floor", anchor={"type": "free", "target": None, "label": ""},
                            role=f.get("catalog_code"), qty=rows, qty_source=g["qty_source"], parts=f.get("parts") or [],
                            seats=int(dims["w"] / float(pl.p.get("seat_pitch_m", 0.6)) + 1e-9) if seats_flag else 0)
        return
    # 묶음 중심 디스플레이
    xs = [d["x"] for d in disp]
    ys = [d["y"] for d in disp]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    rot_d = disp[0]["rot_deg"]
    fx, fy = facing_vec(rot_d)
    diag = disp[0].get("diag_inch")
    dist0 = seat_distance(diag, pl.p)
    pitch = float(pl.p.get("row_pitch_m", 0.9))
    rot = rdeg(rot_d + 180)
    disp_group = disp[0]["group_id"]
    for k in range(rows):
        dist = dist0 + k * pitch
        x, y = cx + fx * dist, cy + fy * dist
        n_seats = int(dims["w"] / float(pl.p.get("seat_pitch_m", 0.6)) + 1e-9) if seats_flag else 0
        _add_floor_item(pl, g, kind="furniture", ref=f["id"], label=label, short=short, tiny=tiny, x=x, y=y, rot=rot,
                        w=dims["w"], d=dims["d"], h=dims["h"], z=0.0, mount="floor",
                        anchor={"type": "faces", "target": disp[0]["id"], "label": f"{disp[0].get('tiny') or ''} 정면".strip()},
                        role=f.get("catalog_code"), qty=rows, qty_source=g["qty_source"], faces=disp[0]["id"],
                        parts=f.get("parts") or [], seats=n_seats)
    g["faces_group"] = disp_group


def _near_pos(pl: Placer, target: str, dims: dict[str, float], i: int) -> tuple[float, float, float, str]:
    disp = _display_items(pl, target)
    if not disp:
        x, y, rot = _free_pos(pl, dims, i)
        return x, y, rot, ""
    d0 = disp[0]
    fx, fy = facing_vec(d0["rot_deg"])
    gap = float(pl.p.get("near_gap_m", 1.0))
    dist = d0["d"] / 2 + gap + dims["d"] / 2 + i * (dims["d"] + 0.6)
    return d0["x"] + fx * dist, d0["y"] + fy * dist, rdeg(d0["rot_deg"] + 180), f"{d0.get('tiny') or ''} 앞".strip()


def _entrance_pos(pl: Placer, w: float, d: float, i: int) -> tuple[float, float, float]:
    ent = pl.entrance
    if not ent:
        return (*_free_pos(pl, {"w": w, "d": d, "h": 1.0}, i)[:2], 0.0)
    wall = pl.wall_by[ent["wall_id"]]
    depth = float(pl.p.get("entrance_depth_m", 2.0))
    side = float(pl.p.get("side_gap_m", 0.6))
    lateral = ent["width"] / 2 + side + w / 2 + i * (w + 0.6)
    rot = rdeg(wall.facing_rot + 180)
    cands = [ent["s"] - lateral, ent["s"] + lateral]
    for s in cands:
        x, y = wall.inner(s, depth + d / 2)
        if not pl.blocked(rect_poly(x, y, w, d, rot)):
            return (x, y, rot)
    x, y = wall.inner(cands[0], depth + d / 2)
    return (x, y, rot)


def _window_area_pos(pl: Placer, target: str, dims: dict[str, float], i: int) -> tuple[float, float, float]:
    win = next((o for o in pl.openings if o["id"] == target), None) if target else _first_outdoor_window(pl.space)
    if win is None:
        return _free_pos(pl, dims, i)
    wall = pl.wall_by[win["wall_id"]]
    gap = float(pl.p.get("window_area_gap_m", 3.2))
    rot = rdeg(wall.facing_rot + 180)
    occ = pl.window_occ.get(win["id"], [])
    free = intervals_subtract((win["offset"], win["offset"] + win["width"]), occ)
    fits = [s for s in free if s[1] - s[0] >= dims["w"]]
    if fits:
        seg = fits[min(i, len(fits) - 1)]
        s = (seg[0] + seg[1]) / 2
    else:
        s = win["offset"] + win["width"] / 2 + i * (dims["w"] + 0.6)
    x, y = wall.inner(s, gap + dims["d"] / 2)
    return (x, y, rot)


def _free_pos(pl: Placer, dims: dict[str, float], i: int) -> tuple[float, float, float]:
    """빈 영역 — 방 모서리에서 안쪽으로(주출입구에서 먼 모서리부터)."""
    minx, miny, maxx, maxy = pl.room.bounds
    m = 0.6
    corners = [(minx + m + dims["w"] / 2, maxy - m - dims["d"] / 2), (maxx - m - dims["w"] / 2, maxy - m - dims["d"] / 2),
               (minx + m + dims["w"] / 2, miny + m + dims["d"] / 2), (maxx - m - dims["w"] / 2, miny + m + dims["d"] / 2)]
    if pl.entrance:
        ex, ey = pl.entrance["inside"]
        corners.sort(key=lambda c: (-round(math.hypot(c[0] - ex, c[1] - ey), 3), c[0], c[1]))
    x, y = corners[i % len(corners)]
    return (x, y, 0.0)


# ── 공개 도우미 ─────────────────────────────────────────

def items_by_group(layout: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for it in layout.get("items", []):
        out[it["group_id"]].append(it)
    return out


def group_bbox(items: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    polys = [item_poly(it) for it in items]
    u = unary_union(polys)
    return u.bounds


def point_in_room(space: dict[str, Any], x: float, y: float) -> bool:
    return room_union(space).buffer(1e-4).contains(Point(x, y))
