"""F4 배치 검증 — 경고마다 룰 ID·근거 수치·고치는 방법을 붙인다. 자동 조정도 여기서."""
from __future__ import annotations

import copy
import math

from . import geometry as G
from . import space as S
from .catalog import Catalog
from .layout2d import line_strategy
from .rules import Rules
from .text import josa
from .zones import clear_widths, route_flow

LEVEL_ORDER = {"error": 0, "warn": 1, "info": 2, "memo": 3}


def _fmt(v):
    return f"{v:,.0f}"


def _find(project: dict, oid: str):
    for coll in ("fixtures", "placements"):
        for it in project.get(coll, []):
            if it["id"] == oid:
                return coll, it
    return None, None


def _label_of(project: dict, catalog: Catalog, oid: str) -> str:
    coll, it = _find(project, oid)
    if coll == "fixtures":
        return it.get("label") or it["type"]
    if coll == "placements":
        p = catalog.get(it["product"])
        return p["short"] if p else it["product"]
    for p in project["space"].get("pillars", []):
        if p["id"] == oid:
            return p.get("label") or f"기둥 {oid}"
    return "벽" if oid == "wall" else oid


def _move_ok(project, catalog, oid, dx, dy, ignore=()):
    """oid 를 (dx,dy) 옮겼을 때 다른 바닥 장애물·벽과 겹치지 않는가."""
    sp = project["space"]
    coll, it = _find(project, oid)
    if not it:
        return False
    moved = dict(it, x=it["x"] + dx, y=it["y"] + dy)
    if coll == "fixtures":
        poly = S.fixture_poly(moved)
        band = (0, moved.get("h", 900))
    else:
        prod = catalog.get(it["product"])
        poly = S.placement_poly(moved, prod)
        band = S.placement_band(moved, prod, sp)
    x0, y0, x1, y1 = G.bbox(poly)
    if x0 < -1 or y0 < -1 or x1 > sp["width"] + 1 or y1 > sp["depth"] + 1:
        return False
    for o in S.obstacles(project, catalog):
        if o.id == oid or o.id in ignore:
            continue
        if o.kind == "fixture" and o.ref.get("type") == "rug":
            continue
        if not (o.z0 < band[1] and band[0] < o.z1):
            continue
        if G.intersects(poly, o.poly, 5):
            return False
    return True


def _best_move(project, catalog, oid, ux, uy, need, step=100.0, extra=8, ignore=()):
    """방향 (ux,uy)로 need 이상 옮기되 겹침이 없는 가장 짧은 거리(스냅)."""
    d0 = G.snap_up(need, step)
    for k in range(extra + 1):
        d = d0 + k * step
        dx, dy = round(ux * d), round(uy * d)
        if _move_ok(project, catalog, oid, dx, dy, ignore):
            return dx, dy
    return None


def _dir_word(dx, dy, rot_hint=None):
    if abs(dx) >= abs(dy):
        return "오른쪽" if dx > 0 else "왼쪽"
    return "아래쪽" if dy > 0 else "위쪽"


def _seat_points(f: dict, catalog: Catalog) -> list[G.Pt]:
    try:
        ft = catalog.furniture_type(f["type"])
    except KeyError:
        ft = {}
    seats = int(f.get("seats") or ft.get("seats") or max(1, round(f["w"] / 600)))
    seats = max(1, seats)
    l = G.lateral(f.get("rot", 0))
    pts = []
    pitch = f["w"] / seats
    for i in range(seats):
        off = -f["w"] / 2 + pitch * (i + 0.5)
        pts.append((f["x"] + l[0] * off, f["y"] + l[1] * off))
    return pts


def _is_audience(f: dict, catalog: Catalog) -> bool:
    try:
        ft = catalog.furniture_type(f["type"])
    except KeyError:
        return False
    return bool(ft.get("audience"))


def validate(project: dict, catalog: Catalog, rules: Rules | None = None, with_flow: bool = True) -> dict:
    rules = rules or Rules(project.get("rules_override"))
    sp = project["space"]
    H = sp["height"]
    warnings: list[dict] = []
    metrics: dict = {"placements": {}}
    placements = project.get("placements", [])
    fixtures = project.get("fixtures", [])
    notes = project.get("notes", [])
    noted = {n.get("ref") for n in notes if n.get("ref")}
    prods = {pl["id"]: catalog.get(pl["product"]) for pl in placements}
    strategies = {}
    for line in project.get("lines", []):
        try:
            strategies[line["id"]] = line_strategy(project, line, catalog)
        except KeyError:
            pass

    def add(w):
        if w["id"] in noted and w.get("memo_ok"):
            w["level"] = "memo"
        warnings.append(w)

    obs = S.obstacles(project, catalog)
    floor_obs = [o for o in obs if not (o.kind == "fixture" and o.ref.get("type") == "rug")]

    # ── 겹침 · 벽 밖 ──
    R = "pr_warn_overlap"
    tol = rules.p(R, "tol_mm")
    W, D = sp["width"], sp["depth"]
    for o in floor_obs:
        x0, y0, x1, y1 = G.bbox(o.poly)
        if x0 < -tol or y0 < -tol or x1 > W + tol or y1 > D + tol:
            dx = (-x0 if x0 < 0 else 0) + (W - x1 if x1 > W else 0)
            dy = (-y0 if y0 < 0 else 0) + (D - y1 if y1 > D else 0)
            fix = None
            if o.kind == "fixture":
                fix = {"label": "벽 안으로", "ops": [{"op": "move", "id": o.id, "dx": G.snap_up(dx, 100), "dy": G.snap_up(dy, 100)}]}
            add({"id": f"ov:{o.id}:wall", "rule_id": R, "kind": "overlap", "level": "error", "title": f"{o.label} · 벽 밖",
                 "detail": "벽 밖으로 나가 있어요", "targets": [o.id], "at": G.centroid(o.poly), "fix": fix})
    for i in range(len(floor_obs)):
        for j in range(i + 1, len(floor_obs)):
            a, b = floor_obs[i], floor_obs[j]
            if not (a.z0 < b.z1 and b.z0 < a.z1):
                continue
            if a.kind == "pillar" and b.kind == "pillar":
                continue
            depth, ax = G.overlap_depth(a.poly, b.poly)
            if depth <= tol:
                continue
            fix = None
            mov = b if b.movable else (a if a.movable else None)
            if mov:
                other = a if mov is b else b
                d2, ax2 = G.overlap_depth(mov.poly, other.poly)
                mv = _best_move(project, catalog, mov.id, ax2[0], ax2[1], d2 + 50)
                if mv:
                    fix = {"label": f"{mov.label} {_fmt(math.hypot(*mv))} mm {_dir_word(*mv)}으로",
                           "ops": [{"op": "move", "id": mov.id, "dx": mv[0], "dy": mv[1]}]}
            add({"id": f"ov:{a.id}:{b.id}", "rule_id": R, "kind": "overlap", "level": "error",
                 "title": f"{a.label} ↔ {b.label}", "detail": f"바닥 점유가 {_fmt(depth)} mm 겹쳐요",
                 "targets": [a.id, b.id], "at": G.centroid(b.poly), "fix": fix})

    # ── 설치 높이 ──
    R = "pr_warn_mount_height"
    mins = rules.p(R, "min_m")
    top_clear = rules.p(R, "top_clear_m") * 1000
    for pl in placements:
        prod = prods.get(pl["id"])
        if not prod or prod["category"] == "hvac_cassette":
            continue
        mount = pl.get("mount") or prod["default_mount"]
        _, _, sh = S.placement_dims(pl, prod)
        b = float(pl.get("bottom", 0))
        mn = (mins.get(mount, 0.0) if isinstance(mins, dict) else float(mins)) * 1000
        top = b + sh
        if b < mn - 1:
            add({"id": f"ht:{pl['id']}", "rule_id": R, "kind": "height", "level": "warn", "title": f"{prod['short']} · 높이",
                 "detail": f"하단 {_fmt(b)} < 기준 {_fmt(mn)} ({S.clamp(mn, 0, 9e9) / 1000:.1f} m)", "targets": [pl["id"]],
                 "at": (pl["x"], pl["y"]), "fix": {"label": f"하단 {_fmt(mn)}로", "ops": [{"op": "set", "id": pl["id"], "key": "bottom", "value": mn}]}})
        elif top > H - top_clear + 1:
            nb = max(0.0, H - top_clear - sh)
            add({"id": f"ht:{pl['id']}", "rule_id": R, "kind": "height", "level": "warn", "title": f"{prod['short']} · 높이",
                 "detail": f"상단 {_fmt(top)} > 층고 {_fmt(H)} − {_fmt(top_clear)}", "targets": [pl["id"]],
                 "at": (pl["x"], pl["y"]), "fix": {"label": f"하단 {_fmt(nb)}로", "ops": [{"op": "set", "id": pl["id"], "key": "bottom", "value": nb}]}})

    # ── 설치 면 ──
    R = "pr_warn_mount_support"
    max_gap = rules.p(R, "max_gap_mm")
    win_max = rules.p(R, "window_max_mm")
    pillar_polys = {p["id"]: S.pillar_poly(p) for p in sp.get("pillars", [])}
    for pl in placements:
        prod = prods.get(pl["id"])
        if not prod:
            continue
        mount = pl.get("mount") or prod["default_mount"]
        fw, fd, _ = S.placement_dims(pl, prod)
        f = G.facing(pl.get("rot", 0))
        back = (pl["x"] - f[0] * fd / 2, pl["y"] - f[1] * fd / 2)
        if mount in ("wall", "pillar_wrap"):
            dw = min(back[0], W - back[0], back[1], D - back[1])
            dp = min([G.point_poly_dist(back, q) for q in pillar_polys.values()] or [math.inf])
            gap = min(dw, dp) if mount == "wall" else dp
            if gap > max_gap:
                add({"id": f"ms:{pl['id']}", "rule_id": R, "kind": "support", "level": "warn",
                     "title": f"{prod['short']} · 설치 면", "detail": f"{'벽' if mount == 'wall' else '기둥'} 면에서 {_fmt(gap)} mm 떨어져 있어요",
                     "targets": [pl["id"]], "at": (pl["x"], pl["y"]), "fix": None})
        anchor = pl.get("anchor") or ""
        if anchor.startswith("window:") and mount == "ceiling_hang":
            front = (pl["x"] + f[0] * fd / 2, pl["y"] + f[1] * fd / 2)
            wins = S.openings(sp, kinds=["window"])
            best = math.inf
            for o in wins:
                a = S.wall_point(sp, o["wall"], o["start"])
                b = S.wall_point(sp, o["wall"], o["start"] + o["length"])
                best = min(best, G.seg_point_dist(front, a, b))
            if best > win_max:
                add({"id": f"ms:{pl['id']}", "rule_id": R, "kind": "support", "level": "warn",
                     "title": f"{prod['short']} · 창면", "detail": f"유리에서 {_fmt(best)} mm 떨어져 있어요 (기준 {_fmt(win_max)})",
                     "targets": [pl["id"]], "at": (pl["x"], pl["y"]), "fix": None})

    # ── 전원 거리 ──
    R = "pr_warn_power_distance"
    max_m = rules.p(R, "max_m")
    per_line: dict[str, list] = {}
    for pl in placements:
        prod = prods.get(pl["id"])
        if not prod or prod["category"] == "hvac_cassette":
            continue
        o, d = S.nearest_outlet(sp, (pl["x"], pl["y"]))
        metrics["placements"].setdefault(pl["id"], {})["power"] = {"outlet": (o or {}).get("label") or (o or {}).get("id"), "mm": None if o is None else round(d)}
        if o is None or d > max_m * 1000:
            per_line.setdefault(pl.get("line") or pl["id"], []).append((pl, prod, o, d))
    for lid, items in per_line.items():
        pl0, prod0, o0, d0 = min(items, key=lambda t: t[3])
        n = len(items)
        mount = pl0.get("mount") or prod0["default_mount"]
        route = "천장 배선" if mount in ("ceiling_hang", "ceiling") else ("벽체 배선" if mount in ("wall", "pillar_wrap") else "바닥 배선")
        if o0 is None:
            detail = "콘센트가 없어요 — 전원 위치를 추가해 주세요"
            ol = "콘센트"
        else:
            ol = o0.get("label") or o0["id"]
            far = max(t[3] for t in items)
            rng = f"{d0 / 1000:.1f} m" if n == 1 else f"{d0 / 1000:.1f}–{far / 1000:.1f} m"
            detail = f"가장 가까운 {ol}까지 {rng} · {route} 필요"
        title = f"{prod0['short']} ×{n}" if n > 1 else prod0["short"]
        wid = f"pw:{lid}"
        add_x = pl0["x"]
        add_y = pl0["y"]
        wall = S.wall_of_point(sp, (add_x, add_y), tol=2500)
        fixes = [{"label": "메모로 남기기", "ops": [{"op": "note", "ref": wid, "rule_id": R, "at": [pl0["x"], pl0["y"]],
                                                 "text": f"{title} {route} 필요 ({ol}까지 {d0 / 1000:.1f} m)" if o0 else f"{title} 전원 위치 필요"}]}]
        if wall:
            wx, wy = {"front": (pl0["x"], 0), "back": (pl0["x"], D), "left": (0, pl0["y"]), "right": (W, pl0["y"])}[wall]
            fixes.append({"label": "옆 벽에 콘센트 추가", "ops": [{"op": "add_outlet", "x": round(wx), "y": round(wy), "on": f"wall:{wall}"}]})
        add({"id": wid, "rule_id": R, "kind": "power", "level": "warn", "title": title, "detail": detail,
             "targets": [t[0]["id"] for t in items], "at": (pl0["x"], pl0["y"]), "fix": fixes[0], "alt_fixes": fixes[1:],
             "memo_ok": True})

    # ── 시야각 ──
    R = "pr_warn_viewing_angle"
    max_ang = rules.p(R, "max_angle_deg")
    max_view = rules.p(R, "max_view_m") * 1000
    tan = math.tan(math.radians(max_ang))
    displays = []
    for pl in placements:
        prod = prods.get(pl["id"])
        if not prod or prod["category"] in ("hvac_cassette", "epaper"):
            continue
        if (pl.get("anchor") or "").startswith("window:"):
            continue  # 창면 사이니지는 바깥(도로)을 본다
        displays.append((pl, prod))
    audience = [f for f in fixtures if _is_audience(f, catalog)]
    for f in audience:
        fpos = (f["x"], f["y"])
        # 이 좌석이 보는 화면 = 앞쪽에 있고 가장 큰(가까운) 화면
        cands = []
        ff = G.facing(f.get("rot", 0))
        for pl, prod in displays:
            ang, fwd, lat = G.angle_off_axis((pl["x"], pl["y"]), pl.get("rot", 0), fpos)
            if fwd <= 0 or fwd > max_view:
                continue
            tox, toy = pl["x"] - f["x"], pl["y"] - f["y"]
            dl = math.hypot(tox, toy) or 1
            if (ff[0] * tox + ff[1] * toy) / dl < math.cos(math.radians(50)):
                continue  # 좌석이 그 화면을 향하지 않음
            if ang > 70:
                continue  # 화면 옆쪽 멀리 — 그 화면의 관람석이 아님
            cands.append((ang, fwd, pl, prod))
        if not cands:
            continue
        _, _, pl, prod = min(cands, key=lambda c: (round(c[0]), c[1]))  # 가장 정면으로 보이는 화면
        pos = (pl["x"], pl["y"])
        rot = pl.get("rot", 0)
        seats = _seat_points(f, catalog)
        bad = []
        lo, hi = -math.inf, math.inf
        for s in seats:
            ang, fwd, lat = G.angle_off_axis(pos, rot, s)
            lim = fwd * tan
            lo, hi = max(lo, -lim - lat), min(hi, lim - lat)
            if ang > max_ang + 0.05:
                bad.append((s, ang, lat))
        m = metrics["placements"].setdefault(pl["id"], {})
        _, fwd_c, _ = G.angle_off_axis(pos, rot, fpos)
        m["view_mm"] = min(m.get("view_mm", math.inf), round(fwd_c))
        if not bad:
            continue
        mx = sum(b[0][0] for b in bad) / len(bad) - f["x"]
        my = sum(b[0][1] for b in bad) / len(bad) - f["y"]
        side = ("오른쪽" if mx > 0 else "왼쪽") if abs(mx) >= abs(my) else ("아래쪽" if my > 0 else "위쪽")
        worst = max(b[1] for b in bad)
        l = G.lateral(rot)
        fix = None
        if lo <= hi:
            delta = lo if abs(lo) < abs(hi) else hi
            if lo <= 0 <= hi:
                delta = 0
            need = abs(delta)
            sgn = 1 if delta > 0 else -1
            mv = _best_move(project, catalog, f["id"], l[0] * sgn, l[1] * sgn, need + 1)
            if mv:
                fix = {"label": f"{f.get('label') or f['type']} {_fmt(math.hypot(*mv))} mm {_dir_word(*mv)}으로",
                       "ops": [{"op": "move", "id": f["id"], "dx": mv[0], "dy": mv[1]}]}
        add({"id": f"va:{f['id']}:{pl['id']}", "rule_id": R, "kind": "viewing_angle", "level": "warn",
             "title": f"{f.get('label') or f['type']}", "detail": f"도면 {side} {len(bad)}석이 {prod['short']} 시야각(±{max_ang:g}°) 밖이에요 (최대 {worst:.0f}°)",
             "targets": [f["id"], pl["id"]], "at": bad[0][0], "fix": fix})

    # ── 화면 크기 ↔ 시청거리 (참고) ──
    R = "pr_signage_size_by_distance"
    kmin, kmax = rules.p(R, "inch_per_m_min"), rules.p(R, "inch_per_m_max")
    for pl, prod in displays:
        m = metrics["placements"].get(pl["id"], {})
        vd = m.get("view_mm")
        if not vd or vd == math.inf:
            continue
        diag_in = (prod.get("diag_cm") / 2.54) if prod.get("diag_cm") else math.hypot(prod["w"], prod["h"]) / 25.4
        lo_in, hi_in = vd / 1000 * kmin, vd / 1000 * kmax
        m["diag_in"] = round(diag_in)
        m["diag_range"] = [round(lo_in), round(hi_in)]
        if not (lo_in <= diag_in <= hi_in):
            add({"id": f"sz:{pl['id']}", "rule_id": R, "kind": "size", "level": "info", "title": f"{prod['short']} · 화면 크기",
                 "detail": f"시청거리 {vd / 1000:.1f} m에 권장 {lo_in:.0f}–{hi_in:.0f}\" · 현재 {diag_in:.0f}\"",
                 "targets": [pl["id"]], "at": (pl["x"], pl["y"]), "fix": None})

    # ── 출입구 여유 ──
    R = "pr_warn_door_clearance"
    depth = rules.p(R, "depth_mm")
    labels = S.letter_labels(sp)
    for o in S.openings(sp, kinds=["entrance", "door"]):
        if o.get("door_type") == "wall":
            continue
        zone = S.door_zone(sp, o, depth)
        for ob in floor_obs:
            if ob.kind == "pillar":
                continue
            if G.intersects(zone, ob.poly, 5):
                fix = None
                if ob.movable:
                    d2, ax2 = G.overlap_depth(ob.poly, zone)
                    mv = _best_move(project, catalog, ob.id, ax2[0], ax2[1], d2 + 50)
                    if mv:
                        fix = {"label": f"{ob.label} {_fmt(math.hypot(*mv))} mm {_dir_word(*mv)}으로",
                               "ops": [{"op": "move", "id": ob.id, "dx": mv[0], "dy": mv[1]}]}
                add({"id": f"dr:{o['id']}:{ob.id}", "rule_id": R, "kind": "traffic", "level": "warn",
                     "title": f"{labels[o['id']]} 앞", "detail": f"{josa(ob.label, '이/가')} 문 안쪽 {_fmt(depth)} mm 여유 공간을 막아요",
                     "targets": [ob.id], "at": G.centroid(ob.poly), "fix": fix})

    # ── 동선 폭 ──
    flow = None
    if with_flow:
        R = "pr_warn_aisle_width"
        min_w = rules.p(R, "min_mm")
        zones = project.get("zones") or []
        flow = route_flow(project, catalog, zones)
        samples = clear_widths(project, catalog, flow["path"])
        metrics["flow"] = {"length_mm": round(flow["length_mm"]), "ok": flow["ok"],
                           "min_width_mm": round(min((s["width"] for s in samples), default=0))}
        if not flow["ok"]:
            add({"id": "tr:blocked", "rule_id": R, "kind": "traffic", "level": "error", "title": "동선 막힘",
                 "detail": "입구에서 일부 존까지 지나갈 길이 없어요", "targets": [], "at": flow["waypoints"][0], "fix": None})
        # 입구 문턱(첫 600 mm)은 제외, 좁은 구간을 장애물 쌍으로 묶는다
        start = flow["path"][0] if flow["path"] else (0, 0)
        groups: dict[tuple, dict] = {}
        for s in samples:
            if G.dist(s["at"], start) < 600 or s["width"] >= min_w:
                continue
            lid = s["left"][0] if s["left"] else "none"
            rid = s["right"][0] if s["right"] else "none"
            if lid == "wall" and rid == "wall":
                continue
            key = tuple(sorted((lid, rid)))
            g = groups.get(key)
            if not g or s["width"] < g["width"]:
                groups[key] = s
        for key, s in groups.items():
            lft, rgt = s["left"], s["right"]
            names = [x[1] if x else "벽" for x in (lft, rgt)]
            fix = None
            nx_, ny_ = -s["dir"][1], s["dir"][0]
            for side, who, sgn in (("left", lft, 1), ("right", rgt, -1)):
                if not who or who[0] in ("wall",):
                    continue
                coll, it = _find(project, who[0])
                if coll != "fixtures":
                    continue
                need = min_w - s["width"] + 50
                mv = _best_move(project, catalog, who[0], nx_ * sgn, ny_ * sgn, need)
                if mv:
                    fix = {"label": f"{who[1]} {_fmt(math.hypot(*mv))} mm {_dir_word(*mv)}으로",
                           "ops": [{"op": "move", "id": who[0], "dx": mv[0], "dy": mv[1]}]}
                    break
            add({"id": f"tr:{key[0]}:{key[1]}", "rule_id": R, "kind": "traffic", "level": "warn",
                 "title": f"{names[0]} ↔ {names[1]}", "detail": f"통로 {_fmt(s['width'])} mm · 권장 {_fmt(min_w)} mm 이상",
                 "targets": [x[0] for x in (lft, rgt) if x and x[0] != "wall"], "at": s["at"], "fix": fix})

    ignored = set(project.get("ignored", []))
    for w in warnings:
        if w["id"] in ignored and w["level"] in ("warn", "info"):
            w["ignored"] = True
    warnings.sort(key=lambda w: (LEVEL_ORDER.get(w["level"], 9), w["kind"]))
    for i, w in enumerate(warnings):
        w["no"] = i + 1
        w["at"] = [round(w["at"][0]), round(w["at"][1])]
    active = [w for w in warnings if w["level"] in ("error", "warn") and not w.get("ignored")]
    summary = {
        "warnings": len(active),
        "errors": sum(1 for w in active if w["level"] == "error"),
        "memos": sum(1 for w in warnings if w["level"] == "memo"),
        "infos": sum(1 for w in warnings if w["level"] == "info"),
        "ignored": sum(1 for w in warnings if w.get("ignored")),
    }
    return {"warnings": warnings, "summary": summary, "metrics": metrics, "flow": flow, "geom": geom(project, catalog, rules)}


def geom(project: dict, catalog: Catalog, rules: Rules | None = None) -> dict:
    """화면(편집기)이 엔진과 똑같은 모양을 그리도록 — 제품·집기의 바닥 점유 다각형, 높이 구간, 시야각 부채꼴."""
    from .catalog import MOUNT_NAMES
    rules = rules or Rules(project.get("rules_override"))
    sp = project["space"]
    zones = project.get("zones", [])
    max_ang = rules.p("pr_warn_viewing_angle", "max_angle_deg")
    max_view = rules.p("pr_warn_viewing_angle", "max_view_m") * 1000

    def zone_of(x, y):
        for z in zones:
            if min(z["x0"], z["x1"]) <= x <= max(z["x0"], z["x1"]) and min(z["y0"], z["y1"]) <= y <= max(z["y0"], z["y1"]):
                return z.get("no")
        return None

    def r(pts):
        return [[round(x, 1), round(y, 1)] for x, y in pts]

    out = {"placements": {}, "fixtures": {}, "view": {"max_angle_deg": max_ang, "max_view_mm": max_view}}
    for pl in project.get("placements", []):
        prod = catalog.get(pl["product"])
        if not prod:
            continue
        fw, fd, sh = S.placement_dims(pl, prod)
        z0, z1 = S.placement_band(pl, prod, sp)
        mount = pl.get("mount") or prod["default_mount"]
        rot = pl.get("rot", 0.0)
        viewed = prod["category"] not in ("hvac_cassette", "epaper") and not (pl.get("anchor") or "").startswith("window:")
        g = {"fw": round(fw, 1), "fd": round(fd, 1), "sh": round(sh, 1), "z0": round(z0), "z1": round(z1),
             "poly": r(S.placement_poly(pl, prod)), "short": prod["short"], "name": prod["name"], "mount": mount,
             "mount_name": MOUNT_NAMES.get(mount, mount), "category": prod["category"], "zone": zone_of(pl["x"], pl["y"]),
             "front": [round(v, 4) for v in G.facing(rot)], "viewed": viewed, "spec": {"w": prod["w"], "h": prod["h"], "d": prod["d"]}}
        if viewed:
            fx, fy = G.facing(rot)
            lx, ly = G.lateral(rot)
            ax, ay = pl["x"] + fx * fd / 2, pl["y"] + fy * fd / 2
            t = math.tan(math.radians(max_ang))
            L = max_view
            g["cone"] = r([(ax, ay), (ax + fx * L + lx * L * t, ay + fy * L + ly * L * t), (ax + fx * L - lx * L * t, ay + fy * L - ly * L * t)])
        out["placements"][pl["id"]] = g
    for f in project.get("fixtures", []):
        try:
            ft = catalog.furniture_type(f["type"])
        except KeyError:
            ft = {}
        out["fixtures"][f["id"]] = {"poly": r(S.fixture_poly(f)), "role": ft.get("role"), "audience": bool(ft.get("audience")),
                                    "type_label": ft.get("label"), "zone": zone_of(f["x"], f["y"])}
    return out


def apply_ops(project: dict, ops: list[dict]) -> list[str]:
    log = []
    sp = project["space"]
    for op in ops:
        k = op["op"]
        if k == "move":
            coll, it = _find(project, op["id"])
            if it:
                it["x"] = round(it["x"] + op["dx"])
                it["y"] = round(it["y"] + op["dy"])
                log.append(f"move {op['id']} ({op['dx']:+.0f}, {op['dy']:+.0f})")
        elif k == "set":
            coll, it = _find(project, op["id"])
            if it:
                it[op["key"]] = op["value"]
                log.append(f"set {op['id']}.{op['key']}={op['value']}")
        elif k == "note":
            notes = project.setdefault("notes", [])
            if not any(n.get("ref") == op["ref"] for n in notes):
                notes.append({"id": f"N{len(notes) + 1}", "text": op["text"], "at": op.get("at"), "ref": op["ref"],
                              "rule_id": op.get("rule_id")})
                log.append(f"note {op['ref']}")
        elif k == "add_outlet":
            outs = sp.setdefault("outlets", [])
            n = 1 + max([int(''.join(ch for ch in (o.get('label') or o['id']) if ch.isdigit()) or 0) for o in outs] or [0])
            outs.append({"id": f"C{n}", "label": f"C{n}", "x": op["x"], "y": op["y"], "on": op.get("on", "")})
            log.append(f"outlet C{n}")
    return log


def autofix(project: dict, catalog: Catalog, rules: Rules | None = None, ids: list[str] | None = None,
            max_iter: int = 12) -> tuple[dict, list[dict]]:
    """경고를 하나씩 고치고 다시 검증한다(진동 방지: 같은 경고를 두 번 이상 고치지 않음)."""
    project = copy.deepcopy(project)
    done: dict[str, int] = {}
    log = []
    for _ in range(max_iter):
        res = validate(project, catalog, rules)
        targets = [w for w in res["warnings"]
                   if w["level"] in ("warn", "error") and not w.get("ignored") and w.get("fix")
                   and (ids is None or w["id"] in ids) and done.get(w["id"], 0) < 2]
        if not targets:
            break
        w = targets[0]
        ops_log = apply_ops(project, w["fix"]["ops"])
        done[w["id"]] = done.get(w["id"], 0) + 1
        log.append({"warning": w["id"], "rule_id": w["rule_id"], "title": w["title"], "fix": w["fix"]["label"], "ops": ops_log})
    return project, log
