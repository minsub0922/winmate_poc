"""집기·가구 배치 솔버 — 2D 집기 블록 추천과 3D 가구 배치에 같이 쓴다.

규칙:
- 제품 위치는 바꾸지 않는다(2D 확정값 또는 F2 결과).
- 입구·문 안쪽, 임시 주 동선(폭 1.4 m), 화면 앞 작업 공간은 비운다.
- 관람석은 화면 시야각(룰 pr_warn_viewing_angle) 안에 들어오도록 폭을 정한다.
- 못 놓은 가구는 이유와 함께 건너뛴다(조용히 사라지지 않음).
"""
from __future__ import annotations

import math

from . import geometry as G
from . import space as S
from .catalog import Catalog, screen_size
from .layout2d import line_strategy
from .rules import Rules
from .zones import route_flow, suggest_zones

DECOR_TYPES = {"plinth", "planter_large", "planter_small", "rug"}
FUNCTIONAL_ORDER = ["bench", "operator_desk", "waiting_chairs", "meeting_set", "desk_pair_set", "teacher_desk", "bed",
                    "reception_counter", "info_desk", "lounge_sofa", "armchair", "coffee_table", "exp_counter",
                    "table_set_4", "table_set_2", "display_shelf", "work_desk", "low_cabinet", "nightstand", "partition",
                    "plinth", "planter_large", "planter_small", "rug", "block"]


class FCtx:
    def __init__(self, project: dict, catalog: Catalog, rules: Rules):
        self.project = project
        self.sp = project["space"]
        self.catalog = catalog
        self.rules = rules
        self.W, self.D, self.H = self.sp["width"], self.sp["depth"], self.sp["height"]
        self.fixed: list[tuple[G.Poly, float, float]] = []  # (poly, z0, z1)
        for p in self.sp.get("pillars", []):
            self.fixed.append((S.pillar_poly(p), 0, self.H))
        self.displays = []
        for pl in project.get("placements", []):
            prod = catalog.get(pl["product"])
            if not prod:
                continue
            z0, z1 = S.placement_band(pl, prod, self.sp)
            self.fixed.append((S.placement_poly(pl, prod), z0, z1))
            if prod["category"] not in ("hvac_cassette",):
                self.displays.append((pl, prod))
        self.keepouts: list[tuple[str, G.Poly]] = []
        depth = 1500.0
        for o in S.openings(self.sp, kinds=["entrance", "door"]):
            if o.get("door_type") == "wall":
                continue
            self.keepouts.append(("door", S.door_zone(self.sp, o, depth)))
        for pl, prod in self.displays:
            mount = pl.get("mount") or prod["default_mount"]
            if (pl.get("anchor") or "").startswith("window:") or mount in ("ceiling", "ceiling_hang"):
                continue
            fw, fd, _ = S.placement_dims(pl, prod)
            f = G.facing(pl.get("rot", 0))
            front = 1500.0 if mount == "stand" else 900.0
            cx = pl["x"] + f[0] * (fd / 2 + front / 2)
            cy = pl["y"] + f[1] * (fd / 2 + front / 2)
            self.keepouts.append(("screen", G.rot_rect(cx, cy, fw + 400, front, pl.get("rot", 0))))
        for o in S.openings(self.sp, kinds=["window"]):
            if o.get("sill", 900) < 600:  # 바닥까지 유리인 창 앞은 비운다(플랜터만 예외)
                self.keepouts.append(("glass", S.door_zone(self.sp, o, 1200)))
        self.placed: list[dict] = []
        self.skipped: list[dict] = []
        self.corridor: list[G.Poly] = []
        self.n = 0

    def add_corridor(self, path: list[G.Pt], half: float = 700.0):
        for a, b in zip(path, path[1:]):
            x0, y0 = min(a[0], b[0]) - half, min(a[1], b[1]) - half
            x1, y1 = max(a[0], b[0]) + half, max(a[1], b[1]) + half
            self.keepouts.append(("corridor", G.rect_poly(x0, y0, x1, y1)))

    def fits(self, poly: G.Poly, h: float, gap: float = 450.0, wall_margin: float = 80.0, allow=(), ignore_ids=()) -> bool:
        x0, y0, x1, y1 = G.bbox(poly)
        if x0 < wall_margin - 1 or y0 < wall_margin - 1 or x1 > self.W - wall_margin + 1 or y1 > self.D - wall_margin + 1:
            return False
        for q, z0, z1 in self.fixed:
            if z0 < h and 0 < z1 and G.intersects(poly, q, 2):
                return False
        for kind, q in self.keepouts:
            if kind in allow:
                continue
            if G.intersects(poly, q, 2):
                return False
        for f in self.placed:
            if f["id"] in ignore_ids or f["type"] == "rug":
                continue
            fp = S.fixture_poly(f)
            if G.intersects(poly, fp, 2):
                return False
            if gap > 0 and G.poly_distance(poly, fp) < gap - 1:
                return False
        return True

    def put(self, t: str, x: float, y: float, rot: float, reason: str, w=None, d=None, group=None, label=None, seats=None):
        ft = self.catalog.furniture_type(t)
        self.n += 1
        f = {"id": f"F{self.n}", "type": t, "label": label or ft["label"], "x": round(x), "y": round(y),
             "w": round(w or ft["w"]), "d": round(d or ft["d"]), "h": ft["h"], "rot": G.norm_rot(rot), "reason": reason}
        if group:
            f["group"] = group
        if seats is not None:
            f["seats"] = seats
        elif ft.get("seats"):
            f["seats"] = ft["seats"] if not ft.get("variable_width") else max(1, round((w or ft["w"]) / 600))
        self.placed.append(f)
        return f

    def try_put(self, t, cands, reason, gap=450.0, allow=(), **kw) -> dict | None:
        ft = self.catalog.furniture_type(t)
        for c in cands:
            x, y, rot = c[:3]
            w = c[3] if len(c) > 3 and c[3] else (kw.get("w") or ft["w"])
            d = kw.get("d") or ft["d"]
            poly = G.rot_rect(x, y, w, d, rot)
            if self.fits(poly, ft["h"], gap=gap, allow=allow, wall_margin=kw.get("wall_margin", 80.0)):
                return self.put(t, x, y, rot, reason, w=w, d=d, group=kw.get("group"), label=kw.get("label"))
        return None

    def skip(self, t, why):
        try:
            label = self.catalog.furniture_type(t)["label"]
        except KeyError:
            label = t
        self.skipped.append({"type": t, "label": label, "reason": why})


# ── 패턴 ──

def _focal_display(fc: FCtx, kinds=("mediawall", "ledgrid", "videowall", "wall_seats", "rhythm")):
    """관람석이 바라볼 화면 그룹(가장 넓은 화면 그룹)."""
    groups: dict[str, list] = {}
    for pl, prod in fc.displays:
        line = next((l for l in fc.project.get("lines", []) if l["id"] == pl.get("line")), None)
        st = line_strategy(fc.project, line, fc.catalog) if line else "manual"
        if st in kinds:
            groups.setdefault(pl.get("line") or pl["id"], []).append((pl, prod, st))
    best = None
    for lid, items in groups.items():
        xs = [it[0]["x"] for it in items]
        ys = [it[0]["y"] for it in items]
        sw = sum(screen_size(it[1], bool(it[0].get("portrait")))[0] for it in items)
        if not best or sw > best[0]:
            pl0, prod0, st = items[0]
            sh = max(screen_size(it[1], bool(it[0].get("portrait")))[1] + float(it[0].get("bottom", 0)) for it in items)
            best = (sw, {"x": sum(xs) / len(xs), "y": sum(ys) / len(ys), "rot": pl0.get("rot", 0), "st": st,
                         "width": max(xs) - min(xs) + screen_size(prod0, bool(pl0.get("portrait")))[0] if (max(xs) - min(xs)) > 1 else screen_size(prod0, bool(pl0.get("portrait")))[0],
                         "top": sh, "h": screen_size(prod0, bool(pl0.get("portrait")))[1], "line": lid, "short": prod0["short"]})
    return best[1] if best else None


def rows_facing(fc: FCtx, t: str, focal: dict, rows: int, reason: str, start: float | None = None, spacing: float | None = None,
                per_row: int | None = None) -> int:
    ft = fc.catalog.furniture_type(t)
    f = G.facing(focal["rot"])
    l = G.lateral(focal["rot"])
    max_ang = fc.rules.p("pr_warn_viewing_angle", "max_angle_deg")
    tan = math.tan(math.radians(max_ang - 4))
    if start is None:
        start = max(3000.0, math.ceil(2.5 * focal["h"] / 100) * 100)
        if t == "operator_desk":
            start = max(3000.0, math.ceil(1.4 * focal["top"] / 100) * 100)
        if t == "waiting_chairs":
            start = 2600.0
    if spacing is None:
        spacing = {"bench": 1400.0, "operator_desk": 2100.0, "waiting_chairs": 1500.0, "desk_pair_set": 1700.0}.get(t, ft["d"] + 900)
    rot = G.norm_rot(focal["rot"] + 180.0)
    placed = 0
    for r in range(rows):
        dist = start + r * spacing
        ok_row = False
        for back in (0, 200, 400, 600, 900, 1200):
            dd = dist + back
            cx = focal["x"] + f[0] * dd
            cy = focal["y"] + f[1] * dd
            cone = 2 * dd * tan
            if ft.get("variable_width"):
                for w in [min(ft["w"], cone - 200)] + [min(ft["w"], cone - 200) - k * 600 for k in range(1, 6)]:
                    if w < 1200:
                        break
                    w = math.floor(w / 100) * 100
                    if fc.try_put(t, [(cx, cy, rot, w)], reason, gap=300, group=f"{t}_rows", allow=("corridor",),
                                  label=f"{ft['label']} {r + 1}열") is not None:
                        ok_row = True
                        placed += 1
                        break
            else:
                unit = ft["w"]
                gapu = 0.0 if t == "operator_desk" else 600.0
                avail = min(cone - 200, (fc.W if focal["rot"] in (0, 180) else fc.D) - 1200)
                n = per_row or max(1, int((avail + gapu) // (unit + gapu)))
                for k in range(n, 0, -1):
                    total = k * unit + (k - 1) * gapu
                    xs = [-total / 2 + unit / 2 + j * (unit + gapu) for j in range(k)]
                    trial = []
                    for off in xs:
                        trial.append((cx + l[0] * off, cy + l[1] * off))
                    polys = [G.rot_rect(x, y, unit, ft["d"], rot) for x, y in trial]
                    if all(fc.fits(p, ft["h"], gap=0 if t == "operator_desk" else 300, allow=("corridor",)) for p in polys):
                        # 서로 겹치지 않는지
                        if any(G.intersects(polys[i], polys[j], 2) for i in range(len(polys)) for j in range(i + 1, len(polys))):
                            continue
                        for x, y in trial:
                            fc.put(t, x, y, rot, reason, group=f"{t}_rows")
                            placed += 1
                        ok_row = True
                        break
            if ok_row:
                break
        if not ok_row and r == 0:
            fc.skip(t, f"{focal['short']} 앞에 줄을 놓을 자리가 없어요")
            break
    return placed


def near_entrance(fc: FCtx, t: str, reason: str) -> dict | None:
    sp = fc.sp
    e = S.main_entrance(sp)
    ft = fc.catalog.furniture_type(t)
    if not e:
        return fc.try_put(t, [(fc.W / 2, 2500, 0)], reason)
    wall = e["wall"]
    rot = S.OUTWARD_ROT[wall]  # 들어오는 사람을 마주 본다
    mid = e["start"] + e["length"] / 2
    L = S.wall_length(sp, wall)
    cands = []
    for depth in (2600, 3000, 3500, 4200, 5000):
        for side in (-1, 1):
            for extra in (1500, 2200, 3000, 4000):
                c = mid + side * (e["length"] / 2 + extra + ft["w"] / 2)
                if not (ft["w"] / 2 + 300 < c < L - ft["w"] / 2 - 300):
                    continue
                x, y = S.wall_point(sp, wall, c, depth)
                cands.append((x, y, rot))
    return fc.try_put(t, cands, reason)


def _entrance_lane(fc: FCtx, depth: float = 6000.0, extra: float = 1200.0) -> G.Poly | None:
    e = S.main_entrance(fc.sp)
    if not e:
        return None
    o = dict(e, start=e["start"] - extra, length=e["length"] + 2 * extra)
    return S.door_zone(fc.sp, o, depth)


def lounge_set(fc: FCtx, sofas: int, tables: int, chairs: int, reason: str, rug: bool = False) -> int:
    """소파(+테이블·체어) 묶음 — 입구에서 4~9 m, 입구 진입로·통유리 바로 뒤·화면 앞은 피하고 벽이나 기둥을 등지는 자리."""
    e = S.main_entrance(fc.sp)
    ep = S.opening_mid(fc.sp, e, 0) if e else (fc.W / 2, 0)
    sofa = fc.catalog.furniture_type("lounge_sofa")
    tab = fc.catalog.furniture_type("coffee_table")
    arm = fc.catalog.furniture_type("armchair")
    lane = _entrance_lane(fc)
    glass = [S.door_zone(fc.sp, o, 2000) for o in S.openings(fc.sp, kinds=["window"]) if o.get("sill", 0) < 600]
    backs = [S.pillar_poly(p) for p in fc.sp.get("pillars", [])]
    desk = next((f for f in fc.placed if f["type"] in ("info_desk", "reception_counter")), None)
    made = 0
    for s_i in range(sofas):
        best = None
        step = 300
        for rot in (0.0, 90.0, 180.0, 270.0):
            f = G.facing(rot)
            for y in range(int(sofa["d"]), int(fc.D - sofa["d"]), step):
                for x in range(int(sofa["d"]), int(fc.W - sofa["d"]), step):
                    poly = G.rot_rect(x, y, sofa["w"], sofa["d"], rot)
                    off = sofa["d"] / 2 + 450 + tab["d"] / 2
                    tx, ty = x + f[0] * off, y + f[1] * off
                    tpoly = G.rot_rect(tx, ty, tab["w"], tab["d"], rot)
                    de = G.dist((x, y), ep)
                    score = abs(de - 6000) / 1000.0
                    if lane and (G.intersects(poly, lane, 1) or (tables and G.intersects(tpoly, lane, 1))):
                        score += 6.0
                    if any(G.intersects(poly, q, 1) for q in glass):
                        score += 8.0
                    for kind, q in fc.keepouts:
                        if kind == "screen" and G.poly_distance(poly, q) < 1500:
                            score += 4.0
                    if desk:  # 라운지 · 안내는 같은 편에
                        score += G.dist((x, y), (desk["x"], desk["y"])) / 2500.0
                        if e and e["wall"] in ("front", "back") and (x - ep[0]) * (desk["x"] - ep[0]) < 0:
                            score += 3.0
                        if e and e["wall"] in ("left", "right") and (y - ep[1]) * (desk["y"] - ep[1]) < 0:
                            score += 3.0
                    # 등받이 뒤에 벽·기둥이 가까우면 가산점
                    bx, by = x - f[0] * (sofa["d"] / 2 + 400), y - f[1] * (sofa["d"] / 2 + 400)
                    if bx < 600 or by < 600 or bx > fc.W - 600 or by > fc.D - 600 or any(G.point_poly_dist((bx, by), q) < 400 for q in backs):
                        score -= 1.5
                    if best and score >= best[0]:
                        continue
                    if not fc.fits(poly, sofa["h"], gap=600):
                        continue
                    if tables and not fc.fits(tpoly, tab["h"], gap=0):
                        continue
                    best = (score, x, y, rot, tx, ty)
        if not best:
            fc.skip("lounge_sofa", "소파를 둘 자리가 없어요")
            break
        _, x, y, rot, tx, ty = best
        grp = f"lounge{s_i + 1}"
        fc.put("lounge_sofa", x, y, rot, reason, group=grp)
        made += 1
        if tables > s_i:
            fc.put("coffee_table", tx, ty, rot, "소파 앞 · 간격 450", group=grp)
        if chairs > s_i:
            f = G.facing(rot)
            l = G.lateral(rot)
            for sgn in (-1, 1):
                ax = tx + f[0] * (tab["d"] / 2 + 450 + arm["d"] / 2) + l[0] * sgn * 500
                ay = ty + f[1] * (tab["d"] / 2 + 450 + arm["d"] / 2) + l[1] * sgn * 500
                fc.try_put("armchair", [(ax, ay, rot + 180)], "소파 맞은편", gap=200, group=grp)
        if rug:
            fc.put("rug", (x + tx) / 2, (y + ty) / 2, rot, "라운지 묶음 아래", group=grp)
    return made


def beside_display(fc: FCtx, t: str, kinds: tuple, reason: str) -> dict | None:
    ft = fc.catalog.furniture_type(t)
    for pl, prod in fc.displays:
        line = next((l for l in fc.project.get("lines", []) if l["id"] == pl.get("line")), None)
        st = line_strategy(fc.project, line, fc.catalog) if line else "manual"
        if st not in kinds:
            continue
        f = G.facing(pl.get("rot", 0))
        l = G.lateral(pl.get("rot", 0))
        sw, _ = screen_size(prod, bool(pl.get("portrait")))
        cands = []
        for dist in (2000, 2400, 2800, 1700, 3300):
            for off in (sw / 2 + ft["w"] / 2 + 400, -(sw / 2 + ft["w"] / 2 + 400), 0):
                cands.append((pl["x"] + f[0] * dist + l[0] * off, pl["y"] + f[1] * dist + l[1] * off, pl.get("rot", 0)))
        r = fc.try_put(t, cands, reason, gap=300)
        if r:
            return r
    fc.skip(t, "곁에 둘 화면(스탠드형)이 없거나 자리가 없어요")
    return None


def along_walls(fc: FCtx, t: str, count: int, reason: str, spacing: float = 2200.0, walls=None, inset_extra: float = 300.0) -> int:
    ft = fc.catalog.furniture_type(t)
    ew = S.entrance_wall(fc.sp)
    order = walls or [w for w in ("left", "right", "back", "front") if w != ew] + [ew]
    made = 0
    for wall in order:
        L = S.wall_length(fc.sp, wall)
        rot = S.INWARD_ROT[wall]
        t0 = ft["w"] / 2 + 900
        x = t0
        while x < L - ft["w"] / 2 - 900 and made < count:
            px, py = S.wall_point(fc.sp, wall, x, ft["d"] / 2 + inset_extra)
            if fc.try_put(t, [(px, py, rot)], reason, gap=600):
                made += 1
                x += ft["w"] + spacing
            else:
                x += 300
        if made >= count:
            break
    if made < count:
        fc.skip(t, f"{count}개 중 {made}개만 놓을 벽이 있었어요")
    return made


def planters(fc: FCtx, t: str, count: int, reason: str) -> int:
    ft = fc.catalog.furniture_type(t)
    m = ft["w"] / 2 + 250
    cands = [(m, m, 0), (fc.W - m, m, 0), (m, fc.D - m, 0), (fc.W - m, fc.D - m, 0)]
    e = S.main_entrance(fc.sp)
    if e:
        for sgn in (-1, 1):
            c = e["start"] + e["length"] / 2 + sgn * (e["length"] / 2 + 500 + ft["w"] / 2)
            cands.insert(0, (*S.wall_point(fc.sp, e["wall"], c, ft["d"] / 2 + 300), 0))
    for p in fc.sp.get("pillars", []):
        for dx, dy in ((p["w"] / 2 + m + 150, 0), (-(p["w"] / 2 + m + 150), 0)):
            cands.append((p["x"] + dx, p["y"] + dy, 0))
    for wall in ("left", "right", "back"):
        L = S.wall_length(fc.sp, wall)
        for k in range(1, 6):
            cands.append((*S.wall_point(fc.sp, wall, L * k / 6, m), 0))
    made = 0
    for c in cands:
        if made >= count:
            break
        if fc.try_put(t, [c], reason, gap=500, allow=("glass",), wall_margin=150):
            made += 1
    if made < count:
        fc.skip(t, f"{count}개 중 {made}개만 놓았어요")
    return made


def grid_fill(fc: FCtx, t: str, count: int, reason: str, focal: dict | None = None) -> int:
    ft = fc.catalog.furniture_type(t)
    sx, sy = ft["w"] + 900, ft["d"] + 900
    e = S.main_entrance(fc.sp)
    ep = S.opening_mid(fc.sp, e, 0) if e else (fc.W / 2, 0)
    rot = G.norm_rot(focal["rot"] + 180) if focal else 0.0
    cands = []
    y = 900 + ft["d"] / 2
    while y < fc.D - ft["d"] / 2 - 600:
        x = 900 + ft["w"] / 2
        while x < fc.W - ft["w"] / 2 - 600:
            cands.append((x, y, rot))
            x += sx
        y += sy
    if focal:
        cands.sort(key=lambda c: G.dist((c[0], c[1]), (focal["x"], focal["y"])))
    else:
        cands.sort(key=lambda c: -G.dist((c[0], c[1]), ep))
    made = 0
    for c in cands:
        if made >= count:
            break
        if fc.try_put(t, [c], reason, gap=600):
            made += 1
    if made < count:
        fc.skip(t, f"{count}개 중 {made}개만 놓았어요")
    return made


def centered(fc: FCtx, t: str, reason: str, focal: dict | None = None) -> dict | None:
    ft = fc.catalog.furniture_type(t)
    rot = 0.0
    if focal:
        rot = G.norm_rot(focal["rot"] + 180)
        f = G.facing(focal["rot"])
        base = (focal["x"] + f[0] * (2600 + ft["d"] / 2), focal["y"] + f[1] * (2600 + ft["d"] / 2))
        rot = G.norm_rot(focal["rot"] + 90)  # 테이블 긴 변이 화면을 향하도록
    else:
        base = (fc.W / 2, fc.D / 2)
    cands = []
    for r in range(0, 12):
        for dx, dy in ((0, 0), (r * 300, 0), (-r * 300, 0), (0, r * 300), (0, -r * 300)):
            cands.append((base[0] + dx, base[1] + dy, rot))
    return fc.try_put(t, cands, reason, gap=600)


def bed_set(fc: FCtx, reason: str) -> int:
    bed = fc.catalog.furniture_type("bed")
    ew = S.entrance_wall(fc.sp)
    made = 0
    for wall in [w for w in ("left", "right", "back", "front") if w != ew]:
        L = S.wall_length(fc.sp, wall)
        rot = S.INWARD_ROT[wall]
        for t in (L / 2, L * 0.4, L * 0.6):
            x, y = S.wall_point(fc.sp, wall, t, bed["d"] / 2 + 30)
            if fc.try_put("bed", [(x, y, rot)], reason, gap=600, wall_margin=20):
                made = 1
                ns = fc.catalog.furniture_type("nightstand")
                for sgn in (-1, 1):
                    off = bed["w"] / 2 + 100 + ns["w"] / 2
                    nx, ny = S.wall_point(fc.sp, wall, t + sgn * off, ns["d"] / 2 + 30)
                    fc.try_put("nightstand", [(nx, ny, rot)], "침대 양옆", gap=0, wall_margin=20)
                return made
    fc.skip("bed", "침대를 붙일 벽이 없어요")
    return made


def _default_requests(project: dict, catalog: Catalog, mode: str) -> list[dict]:
    """공간 유형 템플릿 + 제품 구성에서 가구 요청을 만든다(규칙 기반)."""
    sp = project["space"]
    st_code = sp.get("space_type") or "lobby"
    tmpl = next((s for s in catalog.furniture["space_types"] if s["code"] == st_code), catalog.furniture["space_types"][0])
    reqs = [{"type": t, "count": n, "reason": f"{tmpl['label']} 기본 구성"} for t, n in tmpl["furniture"]]
    strategies = {l["id"]: line_strategy(project, l, catalog) for l in project.get("lines", [])}
    sts = set(strategies.values())
    if sts & {"mediawall", "ledgrid"} and not any(r["type"] == "bench" for r in reqs):
        reqs.insert(0, {"type": "bench", "count": 3, "reason": "미디어월 관람석 · 시야각 안"})
    if "stand" in sts and not any(r["type"] == "exp_counter" for r in reqs):
        reqs.append({"type": "exp_counter", "count": 1, "reason": "상담·시연 스탠드 곁"})
    if mode == "2d":
        reqs = [r for r in reqs if r["type"] not in DECOR_TYPES]
    return reqs


def furnish(project: dict, catalog: Catalog, rules: Rules | None = None, requests: list[dict] | None = None,
            mode: str = "2d", reserve_flow: bool = True, existing: list[dict] | None = None) -> tuple[list[dict], dict]:
    """가구 배치 결과(fixtures)와 로그({placed, skipped}). existing 은 그대로 두고 그 위에 더한다(2D 집기 블록 → 3D)."""
    rules = rules or Rules(project.get("rules_override"))
    base = dict(project, fixtures=[])
    fc = FCtx(base, catalog, rules)
    if existing:
        for f in existing:
            fc.placed.append(dict(f))
        fc.n = len(existing) + 100
    if reserve_flow:
        strategies = {l["id"]: line_strategy(base, l, catalog) for l in base.get("lines", [])}
        pz = suggest_zones(base, catalog, strategies)
        flow = route_flow(base, catalog, pz, include_fixtures=False, inflate=400.0, to_edges=True)
        fc.add_corridor(flow["path"])
    reqs = requests if requests is not None else _default_requests(project, catalog, mode)
    if existing:
        have = {f["type"] for f in existing}
        reqs = [r for r in reqs if r["type"] not in have]
    reqs = sorted(reqs, key=lambda r: FUNCTIONAL_ORDER.index(r["type"]) if r["type"] in FUNCTIONAL_ORDER else 99)
    focal = _focal_display(fc)
    focal_ops = _focal_display(fc, kinds=("videowall",)) or focal
    by_type = {r["type"]: r for r in reqs}
    for r in reqs:
        t, n, why = r["type"], int(r.get("count", 1)), r.get("reason", "")
        if n <= 0:
            continue
        if t == "bench":
            if focal:
                rows_facing(fc, "bench", focal, n, why or "관람석")
            else:
                along_walls(fc, "bench", n, why)
        elif t == "operator_desk":
            if focal_ops:
                rows = 2 if n > 3 else 1
                rows_facing(fc, "operator_desk", focal_ops, rows, why or "상황판을 보는 운영석", per_row=math.ceil(n / rows))
            else:
                grid_fill(fc, t, n, why)
        elif t == "waiting_chairs":
            if focal:
                rows = max(1, math.ceil(n / 2))
                rows_facing(fc, "waiting_chairs", focal, rows, why or "안내 화면을 보는 대기석", per_row=2)
            else:
                grid_fill(fc, t, n, why)
        elif t == "desk_pair_set":
            if focal:
                rows = max(1, math.ceil(n / 3))
                rows_facing(fc, "desk_pair_set", focal, rows, why or "앞 화면을 보는 책상", per_row=3)
            else:
                grid_fill(fc, t, n, why)
        elif t in ("info_desk", "reception_counter"):
            for _ in range(n):
                if not near_entrance(fc, t, why or "입구에서 바로 보이는 자리"):
                    fc.skip(t, "입구 근처에 자리가 없어요")
        elif t == "lounge_sofa":
            tables = int(by_type.get("coffee_table", {}).get("count", 0))
            chairs = int(by_type.get("armchair", {}).get("count", 0))
            lounge_set(fc, n, tables, chairs, why or "입구 쪽 라운지", rug=("rug" in by_type))
        elif t in ("coffee_table", "armchair") and "lounge_sofa" in by_type:
            continue
        elif t == "coffee_table" and any(f["type"] == "lounge_sofa" for f in fc.placed):
            tab = fc.catalog.furniture_type("coffee_table")
            for sf in [f for f in fc.placed if f["type"] == "lounge_sofa"][:n]:
                ff = G.facing(sf.get("rot", 0))
                off = sf["d"] / 2 + 450 + tab["d"] / 2
                fc.try_put("coffee_table", [(sf["x"] + ff[0] * off, sf["y"] + ff[1] * off, sf.get("rot", 0))], "소파 앞 · 간격 450",
                           gap=0, group=sf.get("group")) or fc.skip("coffee_table", "소파 앞에 자리가 없어요")
        elif t == "rug" and "lounge_sofa" in by_type:
            continue
        elif t == "exp_counter":
            for _ in range(n):
                beside_display(fc, t, ("stand",), why or "스탠드 화면 곁 체험 카운터") or grid_fill(fc, t, 1, why)
        elif t in ("table_set_2", "table_set_4"):
            grid_fill(fc, t, n, why)
        elif t in ("display_shelf", "low_cabinet", "partition"):
            along_walls(fc, t, n, why, spacing=600 if t == "display_shelf" else 1200, inset_extra=60)
        elif t == "plinth":
            along_walls(fc, t, n, why or "벽을 따라 진열", spacing=1800)
        elif t in ("planter_large", "planter_small"):
            planters(fc, t, n, why or "모서리·입구 양옆")
        elif t in ("meeting_set",):
            for _ in range(n):
                centered(fc, t, why, focal) or fc.skip(t, "가운데 자리가 없어요")
        elif t == "bed":
            bed_set(fc, why)
        elif t == "nightstand" and "bed" in by_type:
            continue
        elif t in ("teacher_desk",):
            if focal:
                f = G.facing(focal["rot"])
                fc.try_put(t, [(focal["x"] + f[0] * 1500, focal["y"] + f[1] * 1500 + 0, G.norm_rot(focal["rot"] + 180))], why) or fc.skip(t, "자리 없음")
            else:
                near_entrance(fc, t, why)
        elif t in ("work_desk",):
            grid_fill(fc, t, n, why, focal=None)
        elif t == "rug":
            centered(fc, t, why)
        else:
            grid_fill(fc, t, n, why)
    log = {"placed": [{"id": f["id"], "type": f["type"], "label": f["label"], "reason": f.get("reason")} for f in fc.placed],
           "skipped": fc.skipped}
    return fc.placed, log
