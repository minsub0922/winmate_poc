"""F2 배치·수량·크기 산정 — 제품 줄(line)마다 권장 수량과 위치를 룰로 계산한다.

결과에는 항상 쓴 룰 ID, 숫자를 채운 식, 입력값이 붙는다(kickoff S11 수용 기준).
"""
from __future__ import annotations

import math
from typing import Callable

from . import geometry as G
from . import space as S
from .catalog import CATEGORY_NAMES, Catalog, footprint_depth, native_portrait, screen_size
from .rules import Rules

STRATEGY_NAMES = {
    "window": "창면 사이니지", "pillar": "기둥 랩핑", "mediawall": "미디어월", "stand": "상담·시연 스탠드",
    "videowall": "비디오월", "ledgrid": "LED 월", "wall_seats": "벽부 안내 화면", "rhythm": "갤러리 월",
    "wayfinding": "출입구 안내판", "hvac": "천장 냉난방", "manual": "직접 배치",
}
# 줄을 배치하는 순서(벽·창을 먼저 잡고 스탠드형을 마지막에)
STRATEGY_ORDER = ["window", "pillar", "videowall", "mediawall", "ledgrid", "rhythm", "wall_seats", "wayfinding", "stand", "hvac", "manual"]


def strategy_for(prod: dict, mount: str, space: dict) -> str:
    cat = prod["category"]
    if cat == "hvac_cassette":
        return "hvac"
    if mount == "pillar_wrap":
        return "pillar" if space.get("pillars") else "manual"
    if cat == "window_signage":
        return "window" if S.openings(space, kinds=["window"]) else "manual"
    if cat == "flip":
        return "stand"
    if cat == "videowall":
        return "videowall"
    if cat == "led_cabinet":
        return "ledgrid"
    if cat in ("led_allinone", "signage_large"):
        return "mediawall"
    if cat == "spatial":
        return "rhythm"
    if cat == "epaper":
        return "wayfinding"
    if cat == "signage":
        if mount == "ceiling_hang":
            return "window" if S.openings(space, kinds=["window"]) else "manual"
        if mount == "wall":
            return "wall_seats"
        if mount == "floor_stand":
            return "stand"
    return "manual"


class Ctx:
    def __init__(self, project: dict, catalog: Catalog, rules: Rules, line: dict):
        self.project = project
        self.space = project["space"]
        self.catalog = catalog
        self.rules = rules
        self.line = line
        self.taken: list[G.Poly] = []  # 앞서 배치한 다른 줄의 바닥 점유

    def p(self, rid, key):
        return self.rules.p(rid, key)


def _res(qty_rec, positions, rule_ids, formula, anchor, explain, inputs=None, notes=None, group_label=None):
    return {"qty_rec": qty_rec, "positions": positions, "rule_ids": rule_ids, "formula": formula,
            "anchor_desc": anchor, "explain": explain, "inputs": inputs or {}, "notes": notes or [],
            "group_label": group_label}


def _fmt(v: float) -> str:
    return f"{v:,.0f}"


def _allocate(caps: list[int], lengths: list[float], n: int) -> tuple[list[int], bool]:
    alloc = [0] * len(caps)
    overflow = False
    for _ in range(n):
        rem = [c - a for c, a in zip(caps, alloc)]
        if max(rem) > 0:
            i = rem.index(max(rem))
        else:
            overflow = True
            i = max(range(len(caps)), key=lambda k: lengths[k] / (alloc[k] + 1))
        alloc[i] += 1
    return alloc, overflow


# ── 전략들 ──

def s_window(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_window_signage_qty"
    m, g = ctx.p(R, "edge_margin_mm"), ctx.p(R, "min_gap_mm")
    off, bottom = ctx.p(R, "glass_offset_mm"), ctx.p(R, "bottom_mm")
    sp = ctx.space
    portrait = native_portrait(prod)
    sw, sh = screen_size(prod, portrait)
    fd = footprint_depth(prod, mount)
    wins = S.openings(sp, kinds=["window"])
    labels = S.letter_labels(sp)
    caps = [max(0, math.floor((o["length"] - 2 * m + g) / (sw + g))) for o in wins]
    rec = sum(caps)
    k_total = rec if n is None else n
    alloc, overflow = _allocate(caps, [o["length"] for o in wins], k_total) if wins else ([], False)
    H = sp["height"]
    b = min(bottom, H - sh - 100) if mount == "ceiling_hang" else 0.0
    positions, parts, notes = [], [], []
    for o, k, cap in zip(wins, alloc, caps):
        if k == 0:
            continue
        L = o["length"]
        avail = L - 2 * m
        gap = g
        if k > 1 and k * sw + (k - 1) * g > avail:
            gap = max(0.0, (avail - k * sw) / (k - 1))
            notes.append(f"{labels[o['id']]}: {k}대는 최소 간격 {_fmt(g)}를 지킬 수 없어 간격 {_fmt(gap)}로 줄였어요")
        width = k * sw + (k - 1) * gap
        start = o["start"] + (L - width) / 2.0
        for j in range(k):
            c = start + sw / 2.0 + j * (sw + gap)
            x, y = S.wall_point(sp, o["wall"], c, off + fd / 2.0)
            positions.append({"x": x, "y": y, "rot": S.OUTWARD_ROT[o["wall"]], "bottom": b, "portrait": portrait,
                              "mount": mount, "anchor": f"window:{o['id']}"})
        parts.append(f"{labels[o['id']].replace('유리창 ', '')} {k}")
    form = " · ".join(
        f"{labels[o['id']]}: floor(({_fmt(o['length'])} − 2×{_fmt(m)} + {_fmt(g)}) / ({_fmt(sw)} + {_fmt(g)})) = {c}"
        for o, c in zip(wins, caps)) + f" → 권장 {rec}대"
    ex = ""
    if wins:
        o0 = wins[0]
        ex = f"{labels[o0['id']]} {o0['length'] / 1000:.1f} m에 {caps[0]}대(간격 {g / 1000:.1f} m)"
    if overflow:
        notes.append("창마다 들어갈 수 있는 대수를 넘었어요")
    return _res(rec, positions, [R], form, "유리창 " + " · ".join(parts) if parts else "유리창 없음", ex,
                {"windows": [{"id": o["id"], "L": o["length"]} for o in wins], "w": sw, "edge_margin_mm": m, "min_gap_mm": g},
                notes)


PILLAR_FACES = ("front", "back", "left", "right")
FACE_NAMES = {"front": "앞", "back": "뒤", "left": "왼쪽", "right": "오른쪽"}


def _pillar_slot(p: dict, face: str, fd: float):
    if face == "front":
        return p["x"], p["y"] - p["d"] / 2 - fd / 2, 0.0, p["w"]
    if face == "back":
        return p["x"], p["y"] + p["d"] / 2 + fd / 2, 180.0, p["w"]
    if face == "left":
        return p["x"] - p["w"] / 2 - fd / 2, p["y"], 270.0, p["d"]
    return p["x"] + p["w"] / 2 + fd / 2, p["y"], 90.0, p["d"]


def s_pillar(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_pillar_wrap_qty"
    faces = list(ctx.p(R, "faces"))
    bottom = ctx.p(R, "bottom_mm")
    sp = ctx.space
    sw, sh = screen_size(prod, True)
    fd = prod["d"]
    pillars = sp.get("pillars", [])
    primary, extra, skipped = [], [], []
    for p in pillars:
        for face in PILLAR_FACES:
            x, y, rot, fw = _pillar_slot(p, face, fd)
            slot = {"x": x, "y": y, "rot": rot, "bottom": bottom, "portrait": True, "mount": mount,
                    "anchor": f"pillar:{p['id']}:{face}"}
            if fw + 1 < sw:
                if face in faces:
                    skipped.append(f"{p.get('label') or p['id']} {FACE_NAMES[face]}면 폭 {_fmt(fw)} < 화면 폭 {_fmt(sw)}")
                continue
            (primary if face in faces else extra).append(slot)
    rec = len(primary)
    k = rec if n is None else n
    chosen = (primary + extra)[:k]
    notes = list(skipped)
    if k > len(primary) + len(extra):
        notes.append(f"기둥 면이 모자라 {k - len(primary) - len(extra)}대는 배치하지 못했어요")
    face_txt = "·".join(FACE_NAMES[f] for f in faces)
    form = f"기둥 {len(pillars)}개 × 면 {len(faces)}({face_txt}) = {rec} — 면 폭 ≥ 화면 폭 {_fmt(sw)}(세로형)"
    names = " · ".join(str(i + 1) for i in range(len(pillars)))
    anchor = f"기둥 {names} {face_txt}" if pillars else "기둥 없음"
    ex = f"기둥 {len(pillars)}개 × {face_txt} = {rec}대"
    return _res(rec, chosen, [R], form, anchor, ex, {"pillars": len(pillars), "faces": faces, "w_portrait": sw}, notes)


def _media_wall(sp: dict) -> str:
    return S.OPPOSITE[S.entrance_wall(sp)]


def _pick_span(spans, need: float, mid: float):
    fit = [s for s in spans if s[1] - s[0] >= need - 1]
    if not fit:
        return None
    for s in fit:
        if s[0] <= mid <= s[1] and min(mid - s[0], s[1] - mid) >= need / 2 - 1:
            return s
    return max(fit, key=lambda s: s[1] - s[0])


def s_mediawall(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_mediawall_position"
    bottom, top_clear = ctx.p(R, "bottom_mm"), ctx.p(R, "top_clear_mm")
    side_clear, off = ctx.p(R, "side_clear_mm"), ctx.p(R, "wall_offset_mm")
    sp = ctx.space
    portrait = native_portrait(prod)
    sw, sh = screen_size(prod, portrait)
    fd = footprint_depth(prod, mount)
    H = sp["height"]
    wall = _media_wall(sp)
    tried = [wall] + [w for w in ("back", "left", "right", "front") if w != wall]
    span = None
    for w in tried:
        span = _pick_span(S.free_spans(sp, w, side_clear), sw, S.wall_length(sp, w) / 2)
        if span:
            wall = w
            break
    if not span:
        return s_manual(ctx, prod, mount, n, note="미디어월을 둘 만큼 빈 벽이 없어요")
    L = S.wall_length(sp, wall)
    mid = S.clamp(L / 2, span[0] + sw / 2, span[1] - sw / 2)
    b = min(bottom, H - sh - top_clear)
    notes = []
    if b < 0:
        notes.append(f"높이 {_fmt(sh)}가 층고 {_fmt(H)}에 들어가지 않아요")
        b = 0.0
    if mount == "floor_stand":
        b = max(b, 300.0)
    k = 1 if n is None else n
    gap = 1000.0
    width = k * sw + (k - 1) * gap
    start = S.clamp(mid - width / 2, span[0], max(span[0], span[1] - width))
    positions = []
    for j in range(k):
        c = start + sw / 2 + j * (sw + gap)
        x, y = S.wall_point(sp, wall, c, off + fd / 2)
        positions.append({"x": x, "y": y, "rot": S.INWARD_ROT[wall], "bottom": b, "portrait": portrait, "mount": mount,
                          "anchor": f"wall:{wall}"})
    form = (f"{S.WALL_NAMES[wall]} 빈 구간 {_fmt(span[0])}–{_fmt(span[1])} 가운데 · "
            f"하단 {_fmt(b)} + 높이 {_fmt(sh)} = {_fmt(b + sh)} ≤ 층고 {_fmt(H)} − {_fmt(top_clear)}")
    ex = f"하단 {_fmt(b)} · 층고 {_fmt(H)} 안에 맞음" if b + sh <= H - top_clear else "층고 초과"
    return _res(1, positions, [R], form, f"{S.WALL_NAMES[wall]} 중앙", ex,
                {"wall": wall, "span": span, "w": sw, "h": sh, "ceiling": H}, notes)


def s_stand(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_stand_display_qty"
    per_zone, side, off = ctx.p(R, "per_zone"), ctx.p(R, "outlet_side_mm"), ctx.p(R, "wall_offset_mm")
    sp = ctx.space
    portrait = native_portrait(prod)
    sw, sh = screen_size(prod, portrait)
    fd = footprint_depth(prod, mount if mount in ("stand", "floor_stand") else "wall")
    ew = S.entrance_wall(sp)
    media = S.OPPOSITE[ew]
    pillars = [S.pillar_poly(p) for p in sp.get("pillars", [])]
    cands = []
    for o in sp.get("outlets", []):
        w = S.outlet_wall(sp, o)
        if not w:
            continue
        t = o["x"] if w in ("front", "back") else o["y"]
        spans = S.free_spans(sp, w, 400)
        for sgn in (1, -1):
            c = t + sgn * (side + sw / 2)
            if not any(a <= c - sw / 2 and c + sw / 2 <= bb for a, bb in spans):
                continue
            x, y = S.wall_point(sp, w, c, off + fd / 2)
            rot = S.INWARD_ROT[w]
            poly = G.rot_rect(x, y, sw, fd, rot)
            if any(G.intersects(poly, q) for q in pillars + ctx.taken):
                continue
            score = (2.0 if w not in (ew, media) else 0.0) + (1.0 if w != ew else 0.0)
            score -= G.manhattan((x, y), (o["x"], o["y"])) / 10000.0
            cands.append((score, x, y, rot, w, o))
    cands.sort(key=lambda c: -c[0])
    rec = per_zone
    k = rec if n is None else n
    positions, used = [], []
    b = 800.0 if mount in ("stand", "floor_stand") else 900.0
    for _, x, y, rot, w, o in cands:
        poly = G.rot_rect(x, y, sw, fd, rot)
        if any(G.intersects(poly, q) for q in used):
            continue
        used.append(poly)
        positions.append({"x": x, "y": y, "rot": rot, "bottom": b, "portrait": portrait, "mount": mount,
                          "anchor": f"outlet:{o['id']}", "_wall": w, "_outlet": o.get("label") or o["id"]})
        if len(positions) >= k:
            break
    notes = []
    if len(positions) < k:
        more = s_manual(ctx, prod, mount, k - len(positions), note="콘센트 옆 빈 벽이 모자라요")
        positions += more["positions"]
        notes += more["notes"]
    if positions and positions[0].get("_wall"):
        w0, o0 = positions[0]["_wall"], positions[0]["_outlet"]
        anchor = f"{S.WALL_NAMES[w0]} · 콘센트 {o0} 옆"
    else:
        anchor = "콘센트 없음 · 직접 배치"
    for p in positions:
        p.pop("_wall", None)
        p.pop("_outlet", None)
    form = f"상담·시연 존 1곳 × {per_zone}대 · 위치 = 콘센트가 가까운 벽, 콘센트 옆 {_fmt(side)}"
    return _res(rec, positions, [R], form, anchor, f"상담석 1곳 · {anchor}", {"outlets": len(sp.get('outlets', []))}, notes)


def _grid_shape(k: int, max_rows: int, max_cols: int, sw: float, sh: float) -> tuple[int, int]:
    best, best_d = (1, k), math.inf
    for r in range(1, max(1, max_rows) + 1):
        c = math.ceil(k / r)
        if c > max_cols:
            continue
        aspect = (c * sw) / (r * sh)
        d = abs(math.log(aspect / (16 / 9)))
        if d < best_d:
            best, best_d = (r, c), d
    return best


def _wall_grid(ctx, prod, mount, k, rows_max, cols_max, bottom, wall, span, rid, top_clear):
    sp = ctx.space
    sw, sh = screen_size(prod, False)
    fd = prod["d"]
    r, c = _grid_shape(k, rows_max, max(cols_max, 1), sw, sh)
    mid = (span[0] + span[1]) / 2
    positions = []
    placed = 0
    for i in range(r):
        cnt = min(c, k - placed)
        if cnt <= 0:
            break
        x0 = mid - cnt * sw / 2
        for j in range(cnt):
            x, y = S.wall_point(sp, wall, x0 + sw / 2 + j * sw, 30 + fd / 2)
            positions.append({"x": x, "y": y, "rot": S.INWARD_ROT[wall], "bottom": bottom + i * sh, "portrait": False,
                              "mount": mount, "anchor": f"grid:{wall}:{i}:{j}"})
            placed += 1
    return positions, r, c


def s_videowall(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_videowall_grid"
    side, max_rows = ctx.p(R, "side_margin_mm"), ctx.p(R, "max_rows")
    bottom, top_clear, max_cols = ctx.p(R, "bottom_mm"), ctx.p(R, "top_clear_mm"), ctx.p(R, "max_cols")
    sp = ctx.space
    H = sp["height"]
    sw, sh = screen_size(prod, False)
    wall = _media_wall(sp)
    spans = S.free_spans(sp, wall, 0)
    if not spans:
        return s_manual(ctx, prod, mount, n, note="비디오월을 둘 빈 벽이 없어요")
    span = max(spans, key=lambda s: s[1] - s[0])
    free = span[1] - span[0]
    cols = max(0, min(max_cols, math.floor((free - 2 * side) / sw)))
    rows = max(0, min(max_rows, math.floor((H - bottom - top_clear) / sh)))
    rec = cols * rows
    k = rec if n is None else n
    notes = []
    if k > rec and rec:
        notes.append(f"벽에 들어가는 최대 {cols}×{rows}={rec}장을 넘었어요")
    positions, r, c = _wall_grid(ctx, prod, mount, k, max(rows, 1), max(cols, k), bottom, wall, span, R, top_clear)
    form = (f"cols = floor(({_fmt(free)} − 2×{_fmt(side)}) / {_fmt(sw)}) = {cols} · "
            f"rows = min({max_rows}, floor(({_fmt(H)} − {_fmt(bottom)} − {_fmt(top_clear)}) / {_fmt(sh)})) = {rows} → {rec}장")
    return _res(rec, positions, [R], form, f"{S.WALL_NAMES[wall]} · {c}×{r}", f"{S.WALL_NAMES[wall]} 빈 폭 {free / 1000:.1f} m에 {cols}×{rows}",
                {"wall": wall, "free": free, "cols": cols, "rows": rows}, notes, group_label=f"{c}×{r}")


def s_ledgrid(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_led_cabinet_grid"
    fill, bottom, top_clear = ctx.p(R, "fill_ratio"), ctx.p(R, "bottom_mm"), ctx.p(R, "top_clear_mm")
    sp = ctx.space
    H = sp["height"]
    sw, sh = screen_size(prod, False)
    wall = _media_wall(sp)
    spans = S.free_spans(sp, wall, 600)
    if not spans:
        return s_manual(ctx, prod, mount, n, note="LED 월을 둘 빈 벽이 없어요")
    span = max(spans, key=lambda s: s[1] - s[0])
    free = span[1] - span[0]
    cols = max(1, math.floor(free * fill / sw))
    rows = max(1, min(math.floor((H - bottom - top_clear) / sh), round(cols * 9 / 16 * sw / sh)))
    rec = cols * rows
    k = rec if n is None else n
    positions, r, c = _wall_grid(ctx, prod, mount, k, rows, max(cols, math.ceil(k / rows)), bottom, wall, span, R, top_clear)
    form = (f"cols = floor({_fmt(free)} × {fill} / {_fmt(sw)}) = {cols} · rows = min(floor(({_fmt(H)} − {_fmt(bottom)} − {_fmt(top_clear)}) / {_fmt(sh)}), "
            f"round({cols} × 9/16 × {sw / sh:.2f})) = {rows} → {rec}개 ({cols * sw / 1000:.2f} × {rows * sh / 1000:.2f} m)")
    return _res(rec, positions, [R], form, f"{S.WALL_NAMES[wall]} · {c}×{r}", f"캐비닛 {c}×{r} = {c * sw / 1000:.2f} × {r * sh / 1000:.2f} m",
                {"wall": wall, "free": free}, [], group_label=f"{c}×{r}")


def _audience_seats(ctx: Ctx) -> tuple[int, list[dict]]:
    seats, aud = 0, []
    for f in ctx.project.get("fixtures", []):
        try:
            t = ctx.catalog.furniture_type(f["type"])
        except KeyError:
            continue
        if t.get("audience") and t["role"] == "seating":
            seats += int(f.get("seats") or t.get("seats", 1))
            aud.append(f)
    return seats, aud


def s_wall_seats(ctx: Ctx, prod: dict, mount: str, n: int | None):
    """좌석 수(F2)와 시야각(F4)을 함께 본다 — 좌석 폭이 한 화면의 시야각 범위를 넘으면 한 대 더."""
    R = "pr_wall_display_by_seats"
    RV = "pr_warn_viewing_angle"
    per, m2per, bottom, off = ctx.p(R, "seats_per_display"), ctx.p(R, "m2_per_display"), ctx.p(R, "bottom_mm"), ctx.p(R, "wall_offset_mm")
    max_ang = ctx.p(RV, "max_angle_deg")
    sp = ctx.space
    sw, sh = screen_size(prod, False)
    fd = prod["d"]
    seats, aud = _audience_seats(ctx)
    seg = None
    if seats:
        fx = sum(G.facing(f.get("rot", 0))[0] for f in aud)
        fy = sum(G.facing(f.get("rot", 0))[1] for f in aud)
        if abs(fx) > abs(fy):
            wall = "right" if fx > 0 else "left"
        else:
            wall = "back" if fy > 0 else "front"
        along = (lambda q: q[0]) if wall in ("front", "back") else (lambda q: q[1])
        across = {"front": lambda q: q[1], "back": lambda q: sp["depth"] - q[1],
                  "left": lambda q: q[0], "right": lambda q: sp["width"] - q[0]}[wall]
        lo = min(along(c) for f in aud for c in S.fixture_poly(f))
        hi = max(along(c) for f in aud for c in S.fixture_poly(f))
        near = min(across(c) for f in aud for c in S.fixture_poly(f))
        cone = 2 * near * math.tan(math.radians(max_ang - 2))
        by_seats = max(1, math.ceil(seats / per))
        by_width = max(1, math.ceil((hi - lo) / max(cone, 1)))
        rec = max(by_seats, by_width)
        seg = (lo, hi)
        form = (f"max(ceil(좌석 {seats} / {per}) = {by_seats}, ceil(좌석 폭 {_fmt(hi - lo)} / 시야각 폭 {_fmt(cone)}) = {by_width}) = {rec}"
                f" — 시야각 폭 = 2 × 첫 줄 거리 {_fmt(near)} × tan({max_ang - 2:g}°)")
    else:
        a = S.area_m2(sp)
        rec = max(1, math.ceil(a / m2per))
        form = f"좌석 없음 → qty = max(1, ceil(면적 {a:.0f} ㎡ / {m2per})) = {rec}"
        wall = _media_wall(sp)
    k = rec if n is None else n
    spans = S.free_spans(sp, wall, 600)
    if not spans:
        return s_manual(ctx, prod, mount, n, note="안내 화면을 둘 빈 벽이 없어요")
    b = min(bottom, sp["height"] - sh - 100)
    positions = []
    for j in range(k):
        if seg:
            c = seg[0] + (j + 0.5) * (seg[1] - seg[0]) / k
        else:
            span = max(spans, key=lambda s_: s_[1] - s_[0])
            c = span[0] + (j + 0.5) * (span[1] - span[0]) / k
        span = min(spans, key=lambda s_: 0 if s_[0] + sw / 2 <= c <= s_[1] - sw / 2 else min(abs(c - s_[0]), abs(c - s_[1])))
        c = S.clamp(c, span[0] + sw / 2, span[1] - sw / 2)
        x, y = S.wall_point(sp, wall, c, off + fd / 2)
        positions.append({"x": x, "y": y, "rot": S.INWARD_ROT[wall], "bottom": b, "portrait": False, "mount": mount,
                          "anchor": f"wall:{wall}"})
    return _res(rec, positions, [R, RV] if seats else [R], form, f"{S.WALL_NAMES[wall]} · 좌석 앞", f"좌석 {seats}석 기준" if seats else "면적 기준",
                {"seats": seats, "wall": wall}, [])


def s_rhythm(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_wall_rhythm_qty"
    side, gap, off = ctx.p(R, "side_clear_mm"), ctx.p(R, "gap_mm"), ctx.p(R, "wall_offset_mm")
    sp = ctx.space
    portrait = native_portrait(prod)
    sw, sh = screen_size(prod, portrait)
    fd = footprint_depth(prod, mount)
    ew = S.entrance_wall(sp)
    sides = ("left", "right") if ew in ("front", "back") else ("front", "back")
    best = None
    for w in sides:
        for s in S.free_spans(sp, w, side):
            if not best or s[1] - s[0] > best[1][1] - best[1][0]:
                best = (w, s)
    if not best:
        return s_manual(ctx, prod, mount, n, note="세워 둘 옆벽이 없어요")
    wall, span = best
    free = span[1] - span[0]
    rec = max(0, math.floor((free + gap) / (sw + gap)))
    k = rec if n is None else n
    width = k * sw + max(0, k - 1) * gap
    g2 = gap
    if width > free and k > 1:
        g2 = max(0.0, (free - k * sw) / (k - 1))
        width = k * sw + (k - 1) * g2
    start = (span[0] + span[1]) / 2 - width / 2
    positions = []
    for j in range(k):
        x, y = S.wall_point(sp, wall, start + sw / 2 + j * (sw + g2), off + fd / 2)
        positions.append({"x": x, "y": y, "rot": S.INWARD_ROT[wall], "bottom": 50.0, "portrait": portrait, "mount": mount,
                          "anchor": f"wall:{wall}"})
    form = f"floor(({_fmt(free)} + {_fmt(gap)}) / ({_fmt(sw)} + {_fmt(gap)})) = {rec}"
    return _res(rec, positions, [R], form, f"{S.WALL_NAMES[wall]} · 간격 {gap / 1000:.1f} m", f"{S.WALL_NAMES[wall]} {free / 1000:.1f} m",
                {"wall": wall, "free": free}, [])


def s_wayfinding(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_epaper_wayfinding"
    side, bottom = ctx.p(R, "door_side_mm"), ctx.p(R, "bottom_mm")
    sp = ctx.space
    sw, sh = screen_size(prod, native_portrait(prod))
    fd = prod["d"]
    doors = S.openings(sp, kinds=["entrance", "door"])
    rec = len(doors)
    k = rec if n is None else n
    labels = S.letter_labels(sp)
    positions = []
    for o in doors:
        L = S.wall_length(sp, o["wall"])
        spans = S.free_spans(sp, o["wall"], 100)
        for c in (o["start"] + o["length"] + side + sw / 2, o["start"] - side - sw / 2):
            if any(a <= c - sw / 2 and c + sw / 2 <= b for a, b in spans) and 0 < c < L:
                x, y = S.wall_point(sp, o["wall"], c, 20 + fd / 2)
                positions.append({"x": x, "y": y, "rot": S.INWARD_ROT[o["wall"]], "bottom": bottom, "portrait": native_portrait(prod),
                                  "mount": mount, "anchor": f"door:{o['id']}"})
                break
    positions = positions[:k]
    notes = []
    if k > len(positions):
        more = s_manual(ctx, prod, mount, k - len(positions))
        positions += more["positions"]
    form = f"출입구·문 {rec}곳 × 1대"
    return _res(rec, positions, [R], form, " · ".join(labels[o["id"]] for o in doors) + " 옆", f"드나드는 곳 {rec}곳",
                {"doors": rec}, notes)


def s_hvac(ctx: Ctx, prod: dict, mount: str, n: int | None):
    R = "pr_hvac_capacity_by_area"
    kw, uf = ctx.p(R, "kw_per_m2"), ctx.p(R, "usage_factor")
    sp = ctx.space
    W, D, H = sp["width"], sp["depth"], sp["height"]
    unit = prod.get("cooling_kw")
    if not unit:
        return s_manual(ctx, prod, mount, n, note="정격 냉방 용량이 KB에 없어 수량을 계산하지 못했어요")
    a = S.area_m2(sp)
    req = a * kw * uf
    rec = max(1, math.ceil(req / unit - 1e-9))
    k = rec if n is None else n
    cols = max(1, round(math.sqrt(k * W / D)))
    rows = math.ceil(k / cols)
    pillars = sp.get("pillars", [])
    positions, placed = [], 0
    for r in range(rows):
        cnt = min(cols, k - placed)
        y = (r + 0.5) * D / rows
        for c in range(cnt):
            x = (c + 0.5) * W / cnt
            for p in pillars:
                if abs(x - p["x"]) < p["w"] / 2 + prod["w"] / 2 + 600 and abs(y - p["y"]) < p["d"] / 2 + prod["d"] / 2 + 600:
                    shift = p["w"] / 2 + prod["w"] / 2 + 700
                    x = p["x"] + shift if x >= p["x"] and p["x"] + shift < W - prod["w"] / 2 else p["x"] - shift
            positions.append({"x": x, "y": y, "rot": 0.0, "bottom": H - prod["h"], "portrait": False, "mount": "ceiling",
                              "anchor": "ceiling:grid"})
            placed += 1
    form = (f"필요 용량 = {a:.1f} ㎡ × {kw} kW/㎡ × {uf} = {req:.1f} kW → {req:.1f} ÷ {unit} kW(정격 냉방, KB) = "
            f"{req / unit:.2f} → {rec}대")
    return _res(rec, positions, [R], form, f"천장 {cols}열 고르게", f"{req:.1f} kW 필요 · 대당 {unit} kW",
                {"area_m2": a, "required_kw": req, "unit_kw": unit}, ["계수(kW/㎡)는 PoC 임시값 — 설계 부하 계산이 아님"])


def s_manual(ctx: Ctx, prod: dict, mount: str, n: int | None, note: str | None = None):
    sp = ctx.space
    portrait = native_portrait(prod)
    sw, sh = screen_size(prod, portrait)
    fd = footprint_depth(prod, mount)
    k = 1 if n is None else n
    W, D = sp["width"], sp["depth"]
    pillars = [S.pillar_poly(p) for p in sp.get("pillars", [])]
    taken = list(ctx.taken)
    positions = []
    step = 300.0
    cx, cy = W / 2, D / 2
    rings = int(max(W, D) / step) + 2
    for i in range(k):
        found = None
        for ring in range(rings):
            for dx in range(-ring, ring + 1):
                for dy in (-ring, ring) if abs(dx) != ring else range(-ring, ring + 1):
                    x, y = cx + dx * step, cy + dy * step
                    poly = G.rot_rect(x, y, sw, fd, 0)
                    x0, y0, x1, y1 = G.bbox(poly)
                    if x0 < 300 or y0 < 300 or x1 > W - 300 or y1 > D - 300:
                        continue
                    if any(G.intersects(poly, G.inflate_rect(q, 400)) for q in pillars + taken):
                        continue
                    found = (x, y, poly)
                    break
                if found:
                    break
            if found:
                break
        if not found:
            found = (cx, cy, G.rot_rect(cx, cy, sw, fd, 0))
        taken.append(found[2])
        b = 0.0 if mount in ("floor_stand", "stand", "floor_lean") else 900.0
        positions.append({"x": found[0], "y": found[1], "rot": 0.0, "bottom": b, "portrait": portrait, "mount": mount,
                          "anchor": "manual"})
    notes = [note] if note else ["배치 룰이 없는 제품이라 빈 자리에 두었어요 — 직접 옮겨 주세요"]
    return _res(None, positions, [], "배치 룰 없음 — 직접 배치", "직접 배치", notes[0], {}, notes)


STRATEGIES: dict[str, Callable] = {
    "window": s_window, "pillar": s_pillar, "mediawall": s_mediawall, "stand": s_stand, "videowall": s_videowall,
    "ledgrid": s_ledgrid, "wall_seats": s_wall_seats, "rhythm": s_rhythm, "wayfinding": s_wayfinding,
    "hvac": s_hvac, "manual": s_manual,
}


def line_strategy(project: dict, line: dict, catalog: Catalog) -> str:
    prod = catalog.require(line["product"])
    mount = line.get("mount") or prod["default_mount"]
    return strategy_for(prod, mount, project["space"])


def _ordered_lines(project: dict, catalog: Catalog) -> list[dict]:
    def key(line):
        st = line_strategy(project, line, catalog)
        return STRATEGY_ORDER.index(st) if st in STRATEGY_ORDER else 99
    return sorted(project.get("lines", []), key=key)


def recommend_all(project: dict, catalog: Catalog, rules: Rules) -> dict[str, dict]:
    """줄마다 권장 수량·근거. 위치는 권장 수량 기준."""
    out = {}
    taken: list[G.Poly] = []
    for line in _ordered_lines(project, catalog):
        prod = catalog.require(line["product"])
        mount = line.get("mount") or prod["default_mount"]
        st = strategy_for(prod, mount, project["space"])
        ctx = Ctx(project, catalog, rules, line)
        ctx.taken = list(taken)
        res = STRATEGIES[st](ctx, prod, mount, None)
        res["strategy"] = st
        res["strategy_name"] = STRATEGY_NAMES[st]
        res["mount"] = mount
        out[line["id"]] = res
        for pos in res["positions"]:
            pl = dict(pos, product=prod["code"])
            if S.is_floor_obstacle(pl, prod):
                taken.append(S.placement_poly(pl, prod))
    return out


def layout_lines(project: dict, catalog: Catalog, rules: Rules, regenerate: set[str] | None = None) -> dict:
    """줄 수량대로 제품을 배치한다. regenerate 에 없는 줄은 기존 배치(수량이 같으면)를 유지한다."""
    existing: dict[str, list[dict]] = {}
    for pl in project.get("placements", []):
        existing.setdefault(pl.get("line"), []).append(pl)
    placements: list[dict] = []
    taken: list[G.Poly] = []
    for line in _ordered_lines(project, catalog):
        prod = catalog.require(line["product"])
        mount = line.get("mount") or prod["default_mount"]
        qty = int(line.get("qty") if line.get("qty") is not None else 0)
        old = existing.get(line["id"], [])
        keep = (regenerate is not None and line["id"] not in regenerate and len(old) == qty
                and all(p.get("mount", mount) == mount for p in old))
        if keep:
            chosen = old
        else:
            st = strategy_for(prod, mount, project["space"])
            ctx = Ctx(project, catalog, rules, line)
            ctx.taken = list(taken)
            res = STRATEGIES[st](ctx, prod, mount, qty)
            chosen = []
            for i, pos in enumerate(res["positions"][:qty]):
                pl = {"id": f"{line['id']}-{i + 1}", "line": line["id"], "product": prod["code"]}
                pl.update({k: v for k, v in pos.items()})
                chosen.append(pl)
        for pl in chosen:
            placements.append(pl)
            if S.is_floor_obstacle(pl, prod):
                taken.append(S.placement_poly(pl, prod))
    project["placements"] = placements
    return project


def line_summary(project: dict, catalog: Catalog) -> dict:
    kinds = 0
    total = 0
    for line in project.get("lines", []):
        q = int(line.get("qty") or 0)
        if q > 0:
            kinds += 1
            total += q
    return {"kinds": kinds, "total": total}


def category_label(prod: dict) -> str:
    return CATEGORY_NAMES.get(prod["category"], prod["category"])
