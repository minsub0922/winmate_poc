"""존 구획 제안 · 동선 순서 · 동선 경로(A*) · 통로 폭 측정."""
from __future__ import annotations

import heapq
import math

from . import geometry as G
from . import space as S
from .catalog import Catalog, screen_size

ZONE_DEFAULT_NAMES = {
    "window": "쇼윈도", "pillar": "기둥 · 길 안내", "mediawall": "미디어월 · 관람", "ledgrid": "미디어월 · 관람",
    "videowall": "상황판 · 운영석", "stand": "상담 · 시연", "wall_seats": "대기", "rhythm": "갤러리 월",
    "lounge": "라운지 · 안내", "retail": "진열", "dining": "좌석", "meeting": "회의", "class": "수업",
    "bed": "객실", "reception": "접수",
}
# 같은 장소를 두 존이 덮으면 앞쪽(우선) 존을 남긴다
ZONE_PRIORITY = ["window", "videowall", "mediawall", "ledgrid", "stand", "pillar", "reception", "lounge", "wall_seats",
                 "rhythm", "retail", "dining", "meeting", "class", "bed"]

LOUNGE_TYPES = {"lounge_sofa", "armchair", "coffee_table", "rug", "info_desk"}
RETAIL_TYPES = {"display_shelf", "plinth"}
DINING_TYPES = {"table_set_2", "table_set_4"}
MEETING_TYPES = {"meeting_set"}
CLASS_TYPES = {"desk_pair_set", "teacher_desk"}
BED_TYPES = {"bed", "nightstand"}
RECEPTION_TYPES = {"reception_counter"}


def _clip(r, sp):
    x0, y0, x1, y1 = r
    return (max(0.0, x0), max(0.0, y0), min(sp["width"], x1), min(sp["depth"], y1))


def _rect_area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _union(rects):
    xs0, ys0, xs1, ys1 = zip(*rects)
    return (min(xs0), min(ys0), max(xs1), max(ys1))


def suggest_zones(project: dict, catalog: Catalog, strategies: dict[str, str]) -> list[dict]:
    """제품 그룹·집기 묶음으로 존을 제안한다. strategies: line_id → strategy."""
    sp = project["space"]
    groups: dict[str, list] = {}
    for pl in project.get("placements", []):
        st = strategies.get(pl.get("line"), "manual")
        if st in ("hvac", "wayfinding", "manual"):
            continue
        prod = catalog.get(pl["product"])
        if not prod:
            continue
        groups.setdefault(st, []).append((pl, prod))
    rects: list[tuple[str, tuple]] = []
    D, W = sp["depth"], sp["width"]
    fixtures = project.get("fixtures", [])

    for st, items in groups.items():
        polys = [S.placement_poly(pl, prod) for pl, prod in items]
        bb = _union([G.bbox(p) for p in polys])
        if st == "window":
            by_wall: dict[str, list] = {}
            for pl, prod in items:
                oid = (pl.get("anchor") or "").split(":")[-1]
                o = next((o for o in sp.get("openings", []) if o["id"] == oid), None)
                if o:
                    by_wall.setdefault(o["wall"], []).append(o)
            for wall, ops in by_wall.items():
                a = min(o["start"] for o in S.openings(sp, wall, kinds=["window"]))
                b = max(o["start"] + o["length"] for o in S.openings(sp, wall, kinds=["window"]))
                depth = 1800.0
                p0 = S.wall_point(sp, wall, a, 0)
                p1 = S.wall_point(sp, wall, b, depth)
                rects.append(("window", (min(p0[0], p1[0]), min(p0[1], p1[1]), max(p0[0], p1[0]), max(p0[1], p1[1]))))
        elif st == "pillar":
            ps = sp.get("pillars", [])
            if ps:
                rects.append(("pillar", (min(p["x"] for p in ps) - 1200, min(p["y"] for p in ps) - 1200,
                                         max(p["x"] for p in ps) + 1200, max(p["y"] for p in ps) + 1200)))
        elif st in ("mediawall", "ledgrid", "videowall"):
            pl0, prod0 = items[0]
            wall = S.wall_of_point(sp, (pl0["x"], pl0["y"]), tol=1500) or "back"
            seat_types = {"bench", "lounge_sofa", "armchair", "waiting_chairs"} if st != "videowall" else {"operator_desk"}
            seats = [f for f in fixtures if f["type"] in seat_types and _faces(f, pl0)]
            seat_bb = None
            if seats:
                seat_bb = _union([G.bbox(S.fixture_poly(f)) for f in seats])
            half = max((bb[2] - bb[0]) / 2 + 1500, 3000) if wall in ("front", "back") else max((bb[3] - bb[1]) / 2 + 1500, 3000)
            depth = 4500.0
            if seat_bb:
                if wall == "back":
                    depth = max(depth, D - seat_bb[1] + 600)
                elif wall == "front":
                    depth = max(depth, seat_bb[3] + 600)
                elif wall == "left":
                    depth = max(depth, seat_bb[2] + 600)
                else:
                    depth = max(depth, W - seat_bb[0] + 600)
            depth = min(depth, (D if wall in ("front", "back") else W) * 0.6)
            cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
            if seat_bb and wall in ("front", "back"):
                half = max(half, (seat_bb[2] - seat_bb[0]) / 2 + 600)
            if seat_bb and wall in ("left", "right"):
                half = max(half, (seat_bb[3] - seat_bb[1]) / 2 + 600)
            if wall == "back":
                r = (cx - half, D - depth, cx + half, D)
            elif wall == "front":
                r = (cx - half, 0, cx + half, depth)
            elif wall == "left":
                r = (0, cy - half, depth, cy + half)
            else:
                r = (W - depth, cy - half, W, cy + half)
            rects.append((st, r))
        elif st == "stand":
            for pl, prod in items:
                wall = S.wall_of_point(sp, (pl["x"], pl["y"]), tol=1500)
                sw, _ = screen_size(prod, bool(pl.get("portrait")))
                pb = G.bbox(S.placement_poly(pl, prod))
                near = [f for f in fixtures if f["type"] in ("exp_counter",) and G.dist((f["x"], f["y"]), (pl["x"], pl["y"])) < 4000]
                bbs = [pb] + [G.bbox(S.fixture_poly(f)) for f in near]
                ub = _union(bbs)
                m = 1200.0
                r = (ub[0] - m, ub[1] - m, ub[2] + m, ub[3] + m)
                if wall == "right":
                    r = (min(r[0], W - 2600), r[1], W, r[3])
                elif wall == "left":
                    r = (0, r[1], max(r[2], 2600), r[3])
                elif wall == "back":
                    r = (r[0], min(r[1], D - 2600), r[2], D)
                elif wall == "front":
                    r = (r[0], 0, r[2], max(r[3], 2600))
                rects.append(("stand", r))
        elif st == "wall_seats":
            seats = [f for f in fixtures if f["type"] in ("waiting_chairs", "bench", "lounge_sofa", "armchair")]
            if seats:
                ub = _union([G.bbox(S.fixture_poly(f)) for f in seats])
                rects.append(("wall_seats", (ub[0] - 600, ub[1] - 600, ub[2] + 600, ub[3] + 600)))
        elif st == "rhythm":
            m = 1500.0
            rects.append(("rhythm", (bb[0] - m, bb[1] - m, bb[2] + m, bb[3] + m)))

    def cluster(types, key):
        fs = [f for f in fixtures if f["type"] in types]
        if fs:
            ub = _union([G.bbox(S.fixture_poly(f)) for f in fs])
            rects.append((key, (ub[0] - 600, ub[1] - 600, ub[2] + 600, ub[3] + 600)))

    cluster(LOUNGE_TYPES, "lounge")
    cluster(RETAIL_TYPES, "retail")
    cluster(DINING_TYPES, "dining")
    cluster(MEETING_TYPES, "meeting")
    cluster(CLASS_TYPES, "class")
    cluster(BED_TYPES, "bed")
    cluster(RECEPTION_TYPES, "reception")

    # 우선순위대로 겹침 정리 — 뒤에 오는 존을 한 축으로 잘라 낸다
    rects = [(k, _clip(r, sp)) for k, r in rects]
    rects.sort(key=lambda kr: ZONE_PRIORITY.index(kr[0]) if kr[0] in ZONE_PRIORITY else 99)
    kept: list[tuple[str, tuple]] = []
    for k, r in rects:
        for _, q in kept:
            r = _cut(r, q)
            if not r:
                break
        if r and _rect_area(r) > 2.0e6:  # 2 ㎡ 미만은 버림
            kept.append((k, r))
    zones = []
    for i, (k, r) in enumerate(kept):
        zones.append({"id": f"Z{i + 1}", "no": i + 1, "key": k, "name": ZONE_DEFAULT_NAMES.get(k, "존"),
                      "x0": round(r[0]), "y0": round(r[1]), "x1": round(r[2]), "y1": round(r[3]), "point": ""})
    return order_zones(project, zones)


def _faces(f: dict, pl: dict, tol_deg: float = 50.0, max_d: float = 12000.0) -> bool:
    """좌석 f 가 화면 pl 을 바라보고 그 화면 앞에 있는가."""
    ff = G.facing(f.get("rot", 0))
    tx, ty = pl["x"] - f["x"], pl["y"] - f["y"]
    d = math.hypot(tx, ty)
    if d < 1 or d > max_d:
        return False
    if (ff[0] * tx + ff[1] * ty) / d < math.cos(math.radians(tol_deg)):
        return False
    ang, fwd, _ = G.angle_off_axis((pl["x"], pl["y"]), pl.get("rot", 0), (f["x"], f["y"]))
    return fwd > 0 and ang < 65


def _cut(r, q):
    """r 에서 q 와 겹치는 부분을 잘라 낸다(가장 적게 잃는 한 방향)."""
    x0, y0, x1, y1 = r
    a0, b0, a1, b1 = q
    if x1 <= a0 or a1 <= x0 or y1 <= b0 or b1 <= y0:
        return r
    cands = [(x0, y0, a0, y1), (a1, y0, x1, y1), (x0, y0, x1, b0), (x0, b1, x1, y1)]
    cands = [c for c in cands if c[2] - c[0] > 600 and c[3] - c[1] > 600]
    if not cands:
        return None
    return max(cands, key=_rect_area)


def zone_center(z: dict) -> G.Pt:
    return ((z["x0"] + z["x1"]) / 2, (z["y0"] + z["y1"]) / 2)


def entrance_point(sp: dict, inset: float = 600.0) -> G.Pt:
    e = S.main_entrance(sp)
    if not e:
        return (sp["width"] / 2, inset)
    return S.opening_mid(sp, e, inset)


def order_zones(project: dict, zones: list[dict]) -> list[dict]:
    """입구에서 가까운 존부터 잇는 순서(최근접 이웃)로 번호를 매긴다."""
    if not zones:
        return zones
    sp = project["space"]
    cur = entrance_point(sp)
    left = list(zones)
    out = []
    while left:
        def d(z):
            x0, y0, x1, y1 = z["x0"], z["y0"], z["x1"], z["y1"]
            px = S.clamp(cur[0], x0, x1)
            py = S.clamp(cur[1], y0, y1)
            return G.manhattan(cur, (px, py)) + 0.25 * G.manhattan(cur, zone_center(z))
        nxt = min(left, key=d)
        left.remove(nxt)
        out.append(nxt)
        cur = zone_center(nxt)
    for i, z in enumerate(out):
        z["no"] = i + 1
        z["id"] = f"Z{i + 1}"
    return out


# ── 동선 경로 ──

class Grid:
    def __init__(self, sp: dict, blockers: list[G.Poly], cell: float = 200.0, inflate: float = 350.0):
        self.sp = sp
        self.cell = cell
        self.nx = max(1, int(math.ceil(sp["width"] / cell)))
        self.ny = max(1, int(math.ceil(sp["depth"] / cell)))
        self.block = bytearray(self.nx * self.ny)
        wall_m = max(inflate * 0.7, 250.0)
        for j in range(self.ny):
            for i in range(self.nx):
                x, y = (i + 0.5) * cell, (j + 0.5) * cell
                if x < wall_m or y < wall_m or x > sp["width"] - wall_m or y > sp["depth"] - wall_m:
                    self.block[j * self.nx + i] = 1
        for poly in blockers:
            x0, y0, x1, y1 = G.bbox(poly)
            i0 = max(0, int((x0 - inflate) / cell))
            i1 = min(self.nx - 1, int((x1 + inflate) / cell))
            j0 = max(0, int((y0 - inflate) / cell))
            j1 = min(self.ny - 1, int((y1 + inflate) / cell))
            for j in range(j0, j1 + 1):
                for i in range(i0, i1 + 1):
                    if self.block[j * self.nx + i]:
                        continue
                    p = ((i + 0.5) * cell, (j + 0.5) * cell)
                    if G.point_poly_dist(p, poly) < inflate:
                        self.block[j * self.nx + i] = 1

    def cell_of(self, p: G.Pt) -> tuple[int, int]:
        return (min(self.nx - 1, max(0, int(p[0] / self.cell))), min(self.ny - 1, max(0, int(p[1] / self.cell))))

    def center(self, c) -> G.Pt:
        return ((c[0] + 0.5) * self.cell, (c[1] + 0.5) * self.cell)

    def free(self, c) -> bool:
        return not self.block[c[1] * self.nx + c[0]]

    def nearest_free(self, c, max_r: int = 60):
        if self.free(c):
            return c
        for r in range(1, max_r):
            best = None
            for di in range(-r, r + 1):
                for dj in (-r, r) if abs(di) != r else range(-r, r + 1):
                    cc = (c[0] + di, c[1] + dj)
                    if 0 <= cc[0] < self.nx and 0 <= cc[1] < self.ny and self.free(cc):
                        d = abs(di) + abs(dj)
                        if best is None or d < best[0]:
                            best = (d, cc)
            if best:
                return best[1]
        return None

    def clearance(self):
        """칸마다 가장 가까운 막힌 칸까지 거리(칸 수) — 다중 시작 BFS."""
        if getattr(self, "_dist", None) is not None:
            return self._dist
        from collections import deque
        INF = 10 ** 6
        dist = [INF] * (self.nx * self.ny)
        q = deque()
        for idx, b in enumerate(self.block):
            if b:
                dist[idx] = 0
                q.append(idx)
        while q:
            idx = q.popleft()
            i, j = idx % self.nx, idx // self.nx
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                if 0 <= ni < self.nx and 0 <= nj < self.ny:
                    nidx = nj * self.nx + ni
                    if dist[nidx] > dist[idx] + 1:
                        dist[nidx] = dist[idx] + 1
                        q.append(nidx)
        self._dist = dist
        return dist

    def astar(self, a, b, clear_cells: int = 4, clear_w: float = 0.8):
        """4방향 A* — 꺾임에 벌점, 장애물 가까이는 비용을 더해 넓은 곳으로 가는 직각 동선."""
        if a == b:
            return [a]
        dist = self.clearance()
        turn_pen = 3.0
        start = (a, -1)
        openq = [(0.0, 0.0, a, -1)]
        best = {start: 0.0}
        came = {}
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
        while openq:
            f, g, c, d = heapq.heappop(openq)
            if c == b:
                path = [c]
                key = (c, d)
                while key in came:
                    key = came[key]
                    path.append(key[0])
                return path[::-1]
            if g > best.get((c, d), math.inf) + 1e-9:
                continue
            for k, (di, dj) in enumerate(dirs):
                nc = (c[0] + di, c[1] + dj)
                if not (0 <= nc[0] < self.nx and 0 <= nc[1] < self.ny) or not self.free(nc):
                    continue
                cd = dist[nc[1] * self.nx + nc[0]]
                ng = g + 1.0 + (turn_pen if d not in (-1, k) else 0.0) + max(0, clear_cells - cd) * clear_w
                key = (nc, k)
                if ng < best.get(key, math.inf):
                    best[key] = ng
                    came[key] = (c, d)
                    h = abs(nc[0] - b[0]) + abs(nc[1] - b[1])
                    heapq.heappush(openq, (ng + h, ng, nc, k))
        return None


def _dejog(pts: list[G.Pt], min_seg: float = 450.0) -> list[G.Pt]:
    """직각 경로에서 짧은 꺾임(계단)을 펴서 큰 직각만 남긴다."""
    pts = [tuple(p) for p in pts]
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(1, len(pts) - 2):
            a, b, c, d = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
            if G.dist(b, c) >= min_seg:
                continue
            if abs(b[0] - c[0]) < 1:  # 짧은 세로 구간 → 앞뒤 가로 구간을 한 줄로
                y = a[1] if G.dist(a, b) >= G.dist(c, d) else d[1]
                pts[i - 1] = (a[0], y) if abs(a[1] - b[1]) < 1 else a
                pts[i + 2] = (d[0], y) if abs(c[1] - d[1]) < 1 else d
            else:
                x = a[0] if G.dist(a, b) >= G.dist(c, d) else d[0]
                pts[i - 1] = (x, a[1]) if abs(a[0] - b[0]) < 1 else a
                pts[i + 2] = (x, d[1]) if abs(c[0] - d[0]) < 1 else d
            del pts[i:i + 2]
            changed = True
            break
    return pts


def _simplify(pts: list[G.Pt]) -> list[G.Pt]:
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = out[-1], pts[i], pts[i + 1]
        if abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) > 1e-6:
            out.append(b)
    out.append(pts[-1])
    return out


def floor_blockers(project: dict, catalog: Catalog, include_fixtures: bool = True) -> list[tuple[str, str, G.Poly]]:
    """사람이 지나갈 수 없는 바닥 장애물 (id, 라벨, 다각형)."""
    out = []
    for o in S.obstacles(project, catalog):
        if o.kind == "fixture" and not include_fixtures:
            continue
        if o.kind == "fixture" and o.ref.get("type") == "rug":
            continue
        if o.floor:
            out.append((o.id, o.label, o.poly))
    return out


def visit_point(z: dict, frm: G.Pt) -> G.Pt:
    """존의 네 변 가운데점(600 mm 안쪽) 중 이전 지점에서 가장 가까운 곳 — 좌석 사이로 파고들지 않는다."""
    x0, y0, x1, y1 = z["x0"], z["y0"], z["x1"], z["y1"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ins = min(600.0, (x1 - x0) / 2, (y1 - y0) / 2)
    mids = [(cx, y0 + ins), (cx, y1 - ins), (x0 + ins, cy), (x1 - ins, cy)]
    return min(mids, key=lambda m: G.manhattan(frm, m))


def edge_point(z: dict, frm: G.Pt, out: float = 300.0) -> G.Pt:
    """존 경계 바깥 out 만큼 떨어진, frm 에서 가장 가까운 점(가구 배치 전 임시 동선용)."""
    x = S.clamp(frm[0], z["x0"] - out, z["x1"] + out)
    y = S.clamp(frm[1], z["y0"] - out, z["y1"] + out)
    return (x, y)


def route_flow(project: dict, catalog: Catalog, zones: list[dict] | None = None, include_fixtures: bool = True,
               inflate: float = 250.0, to_edges: bool = False) -> dict:
    sp = project["space"]
    zones = zones if zones is not None else project.get("zones", [])
    blockers = [poly for _, _, poly in floor_blockers(project, catalog, include_fixtures)]
    grid = Grid(sp, blockers, inflate=inflate)
    pts = [entrance_point(sp, 300)]
    cur = pts[0]
    for z in sorted(zones, key=lambda z: z["no"]):
        vp = edge_point(z, cur) if to_edges else visit_point(z, cur)
        pts.append(vp)
        cur = vp
    path: list[G.Pt] = []
    ok = True
    for a, b in zip(pts, pts[1:]):
        ca = grid.nearest_free(grid.cell_of(a))
        cb = grid.nearest_free(grid.cell_of(b))
        seg = grid.astar(ca, cb) if ca and cb else None
        if not seg:
            ok = False
            seg_pts = [a, b]
        else:
            seg_pts = [grid.center(c) for c in seg]
        if path and seg_pts and G.dist(path[-1], seg_pts[0]) < 1:
            seg_pts = seg_pts[1:]
        path.extend(seg_pts)
    if path and S.main_entrance(sp):
        w = S.main_entrance(sp)["wall"]
        x0, y0 = path[0]
        edge = {"front": (x0, 0.0), "back": (x0, sp["depth"]), "left": (0.0, y0), "right": (sp["width"], y0)}[w]
        path = [edge] + path
    simp = _simplify([(round(x), round(y)) for x, y in path])
    simp = _simplify(_dejog(simp))
    return {"path": simp, "waypoints": [(round(x), round(y)) for x, y in pts], "ok": ok,
            "length_mm": sum(G.dist(a, b) for a, b in zip(simp, simp[1:]))}


def clear_widths(project: dict, catalog: Catalog, path: list[G.Pt], step: float = 200.0, max_cast: float = 3000.0) -> list[dict]:
    """동선 위 표본점마다 좌우 장애물까지 폭. [{at, width, left:(id,label), right:(id,label), dir}]"""
    sp = project["space"]
    blockers = floor_blockers(project, catalog, True)
    W, D = sp["width"], sp["depth"]
    out = []
    for a, b in zip(path, path[1:]):
        L = G.dist(a, b)
        if L < 1:
            continue
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        nx_, ny_ = -uy, ux
        n = max(1, int(L / step))
        for k in range(n + 1):
            t = min(L, k * step)
            p = (a[0] + ux * t, a[1] + uy * t)
            res = {}
            for side, (dx, dy) in (("left", (nx_, ny_)), ("right", (-nx_, -ny_))):
                best_t, who = max_cast, None
                # 벽
                for tw, wl in ((((0 - p[0]) / dx) if dx < -1e-9 else None, "벽"), (((W - p[0]) / dx) if dx > 1e-9 else None, "벽"),
                               (((0 - p[1]) / dy) if dy < -1e-9 else None, "벽"), (((D - p[1]) / dy) if dy > 1e-9 else None, "벽")):
                    if tw is not None and 0 <= tw < best_t:
                        best_t, who = tw, ("wall", "벽")
                for oid, label, poly in blockers:
                    if G.point_in_poly(p, poly):
                        best_t, who = 0.0, (oid, label)
                        break
                    hit = G.ray_poly_hit(p, (dx, dy), poly, best_t)
                    if hit is not None and hit < best_t:
                        best_t, who = hit, (oid, label)
                res[side] = (best_t, who)
            width = res["left"][0] + res["right"][0]
            out.append({"at": (round(p[0]), round(p[1])), "width": width, "left": res["left"][1], "right": res["right"][1],
                        "dir": (ux, uy), "lt": res["left"][0], "rt": res["right"][0]})
    return out
