"""2D 조감도 도면(SVG) — 종이 mm 단위로 그려 100% 인쇄하면 축척이 맞는다.

종류: plan(배치 도면) · zones(존 구획도) · flow(동선도)
레이어: dims(치수) · zones(존 번호) · flow(동선) · power(전원) · fixtures(집기) · warnings(경고, 편집 화면용)
"""
from __future__ import annotations

import datetime as dt
import math
from xml.sax.saxutils import escape

from . import geometry as G
from . import space as S
from .catalog import MOUNT_NAMES, Catalog

PAPERS = {"A3": (420.0, 297.0), "A4": (297.0, 210.0)}
SCALES = [50, 75, 100, 125, 150, 200, 250, 300, 400, 500]
FONT = "Pretendard, 'Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', 'Noto Sans CJK KR', sans-serif"
NUMFONT = "'SF Mono', Menlo, Consolas, 'Noto Sans Mono', monospace"

C = {
    "ink": "#1f2430", "muted": "#596170", "faint": "#8a91a0", "line": "#b8bec8", "wall": "#4a505c",
    "pillar": "#3d4452", "brand": "#1428a0", "brand_soft": "#dfe4f6", "fixture": "#8a91a0", "zone": "#1428a0",
    "warn": "#c2410c", "glass": "#5b8def", "paper": "#ffffff", "outlet": "#596170",
}
ALL_LAYERS = ("dims", "zones", "flow", "power", "fixtures", "labels")


def _t(x, y, s, size=2.4, anchor="start", weight=500, fill=None, family=FONT, rot=None, extra=""):
    tr = f' transform="rotate({rot:.2f} {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{family}" font-size="{size:.2f}" font-weight="{weight}" '
            f'fill="{fill or C["ink"]}" text-anchor="{anchor}"{tr}{extra}>{escape(str(s))}</text>')


def _line(x1, y1, x2, y2, stroke=None, w=0.2, dash=None, extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{stroke or C["ink"]}" stroke-width="{w:.3f}"{d}{extra}/>'


def _poly(pts, fill="none", stroke=None, w=0.2, dash=None, opacity=None, extra=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    o = f' fill-opacity="{opacity}"' if opacity is not None else ""
    pp = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    st = f' stroke="{stroke}" stroke-width="{w:.3f}"' if stroke else ' stroke="none"'
    return f'<polygon points="{pp}" fill="{fill}"{o}{st}{d}{extra}/>'


def _text_w(s: str, size: float) -> float:
    w = 0.0
    for ch in str(s):
        if "가" <= ch <= "힣" or ord(ch) > 0x3000:
            w += size * 0.98
        elif ch in " ·":
            w += size * 0.32
        else:
            w += size * 0.58
    return w


class Sheet:
    def __init__(self, project: dict, catalog: Catalog, paper: str = "A3", kind: str = "plan",
                 layers=None, validation: dict | None = None, today: str | None = None):
        self.p = project
        self.cat = catalog
        self.sp = project["space"]
        self.kind = kind
        self.layers = set(layers if layers is not None else ALL_LAYERS)
        self.val = validation or {}
        self.pw, self.ph = PAPERS.get(paper, PAPERS["A3"])
        self.paper = paper
        self.today = today or dt.date.today().isoformat()
        self.margin = 10.0
        self.col_w = 104.0 if paper == "A3" else 82.0
        area_w = self.pw - 2 * self.margin - self.col_w - 6 - 34
        area_h = self.ph - 2 * self.margin - 34
        W, D = self.sp["width"], self.sp["depth"]
        self.scale = next((s for s in SCALES if W / s <= area_w and D / s <= area_h), SCALES[-1])
        rw, rd = W / self.scale, D / self.scale
        self.ox = self.margin + 22 + (area_w - rw) / 2
        self.oy = self.margin + 20 + (area_h - rd) / 2
        self.out: list[str] = []
        self.labels: list[tuple[float, float, float, float]] = []

    # 좌표
    def X(self, x):
        return self.ox + x / self.scale

    def Y(self, y):
        return self.oy + y / self.scale

    def P(self, pt):
        return (self.X(pt[0]), self.Y(pt[1]))

    def mm(self, v):
        return v / self.scale

    def add(self, s):
        self.out.append(s)

    # ── 치수 ──
    def tick(self, x, y):
        return _line(x - 0.8, y + 0.8, x + 0.8, y - 0.8, C["muted"], 0.25)

    def dim_h(self, xs: list[float], y_paper: float, ext_from: float | None = None, size=2.1, fmt=None):
        parts = []
        X = [self.X(x) for x in xs]
        parts.append(_line(X[0], y_paper, X[-1], y_paper, C["muted"], 0.18))
        for x in X:
            if ext_from is not None:
                parts.append(_line(x, ext_from, x, y_paper + (1.2 if y_paper > ext_from else -1.2), C["line"], 0.12))
            parts.append(self.tick(x, y_paper))
        for a, b, xa, xb in zip(xs, xs[1:], X, X[1:]):
            v = b - a
            if v < 1:
                continue
            txt = fmt(v) if fmt else f"{v:,.0f}"
            tw = _text_w(txt, size)
            if xb - xa >= tw + 1:
                parts.append(_t((xa + xb) / 2, y_paper - 0.9, txt, size, "middle", 600, C["ink"], NUMFONT))
            else:
                parts.append(_t((xa + xb) / 2, y_paper - 0.9 - (size + 0.4), txt, size * 0.85, "middle", 600, C["muted"], NUMFONT))
        return "".join(parts)

    def dim_v(self, ys: list[float], x_paper: float, ext_from: float | None = None, size=2.1, left=True):
        parts = []
        Yp = [self.Y(y) for y in ys]
        parts.append(_line(x_paper, Yp[0], x_paper, Yp[-1], C["muted"], 0.18))
        for y in Yp:
            if ext_from is not None:
                parts.append(_line(ext_from, y, x_paper + (-1.2 if x_paper < ext_from else 1.2), y, C["line"], 0.12))
            parts.append(_line(x_paper - 0.8, y + 0.8, x_paper + 0.8, y - 0.8, C["muted"], 0.25))
        for a, b, ya, yb in zip(ys, ys[1:], Yp, Yp[1:]):
            v = b - a
            if v < 1:
                continue
            txt = f"{v:,.0f}"
            tx = x_paper - 0.9 if left else x_paper + 0.9 + size * 0.9
            parts.append(_t(tx, (ya + yb) / 2, txt, size, "middle", 600, C["ink"], NUMFONT, rot=-90))
        return "".join(parts)

    # ── 요소 ──
    def walls(self):
        sp = self.sp
        W, D = sp["width"], sp["depth"]
        t = max(150.0, 2.0 * self.scale)  # 종이에서 최소 2 mm
        out = []
        labels = S.letter_labels(sp)
        for wall in S.WALLS:
            L = S.wall_length(sp, wall)
            ops = sorted(S.openings(sp, wall), key=lambda o: o["start"])
            cur = -t
            segs = []
            for o in ops:
                segs.append((cur, o["start"]))
                cur = o["start"] + o["length"]
            segs.append((cur, L + t))
            for a, b in segs:
                if b - a <= 0:
                    continue
                if wall == "front":
                    r = G.rect_poly(a, -t, b, 0)
                elif wall == "back":
                    r = G.rect_poly(a, D, b, D + t)
                elif wall == "left":
                    r = G.rect_poly(-t, a, 0, b)
                else:
                    r = G.rect_poly(W, a, W + t, b)
                out.append(_poly([self.P(q) for q in r], C["wall"]))
            for o in ops:
                a, b = o["start"], o["start"] + o["length"]
                p0 = S.wall_point(sp, wall, a, 0)
                p1 = S.wall_point(sp, wall, b, 0)
                if o["kind"] == "window":
                    for k in (-t * 0.3, -t * 0.7):
                        a0 = self.P(S.wall_point(sp, wall, a, k))
                        a1 = self.P(S.wall_point(sp, wall, b, k))
                        out.append(_line(*a0, *a1, C["glass"], 0.25))
                    for pt in (a, b):
                        e0 = self.P(S.wall_point(sp, wall, pt, 0))
                        e1 = self.P(S.wall_point(sp, wall, pt, -t))
                        out.append(_line(*e0, *e1, C["wall"], 0.35))
                elif o["kind"] == "door":
                    # 문짝 + 여닫는 호(점선)
                    r = o["length"]
                    hinge = self.P(p0)
                    leaf_end = self.P(S.wall_point(sp, wall, a, r))
                    arc_end = self.P(p1)
                    rr = self.mm(r)
                    out.append(_line(*hinge, *leaf_end, C["ink"], 0.3))
                    sweep = 1 if wall in ("front", "right") else 0
                    out.append(f'<path d="M{leaf_end[0]:.2f} {leaf_end[1]:.2f} A{rr:.2f} {rr:.2f} 0 0 {sweep} {arc_end[0]:.2f} {arc_end[1]:.2f}" '
                               f'fill="none" stroke="{C["faint"]}" stroke-width="0.15" stroke-dasharray="0.8 0.6"/>')
                elif o["kind"] == "entrance":
                    for pt in (a, b):
                        e0 = self.P(S.wall_point(sp, wall, pt, 0))
                        e1 = self.P(S.wall_point(sp, wall, pt, -t))
                        out.append(_line(*e0, *e1, C["ink"], 0.35))
                    m0 = self.P(S.wall_point(sp, wall, (a + b) / 2, -t * 2.4))
                    m1 = self.P(S.wall_point(sp, wall, (a + b) / 2, t * 1.2))
                    out.append(_line(*m0, *m1, C["brand"], 0.3, extra=' marker-end="url(#arr)"'))
                lab = labels.get(o["id"], "")
                if o["kind"] != "window" or True:
                    lp = self.P(S.wall_point(sp, wall, (a + b) / 2, -t - 3.2 * self.scale if wall in ("front", "back") else t * 1.0))
                    rot = -90 if wall in ("left", "right") else None
                    if wall in ("left", "right"):
                        lp = self.P(S.wall_point(sp, wall, (a + b) / 2, -t - 2.4 * self.scale))
                    if wall == "back":
                        lp = (lp[0], self.Y(D) + self.mm(t) + 3.6)
                    if wall == "front":
                        lp = (lp[0], self.Y(0) - self.mm(t) - 1.4)
                    out.append(_t(lp[0], lp[1], f"{lab} · {o['length']:,.0f}" if o["kind"] == "door" else lab, 2.1, "middle", 600,
                                  C["muted"], rot=rot))
        self.add("".join(out))

    def pillars(self):
        out = []
        for p in self.sp.get("pillars", []):
            out.append(_poly([self.P(q) for q in S.pillar_poly(p)], C["pillar"]))
        self.add("".join(out))

    def outlets(self):
        if "power" not in self.layers:
            return
        out = []
        for o in self.sp.get("outlets", []):
            x, y = self.P((o["x"], o["y"]))
            # 벽 안쪽으로 살짝
            w = S.outlet_wall(self.sp, o)
            dx, dy = {"front": (0, 1.3), "back": (0, -1.3), "left": (1.3, 0), "right": (-1.3, 0)}.get(w, (0, 0))
            x, y = x + dx, y + dy
            out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.9" fill="#fff" stroke="{C["outlet"]}" stroke-width="0.25"/>'
                       f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.25" fill="{C["outlet"]}"/>')
            lx = x + (2.2 if w != "right" else -2.2)
            out.append(_t(lx, y + 0.8, o.get("label") or o["id"], 1.9, "start" if w != "right" else "end", 700, C["faint"], NUMFONT))
        self.add("".join(out))

    def zones(self, emphasize=False):
        if "zones" not in self.layers:
            return
        out = []
        for z in self.p.get("zones", []):
            x0, y0, x1, y1 = self.X(z["x0"]), self.Y(z["y0"]), self.X(z["x1"]), self.Y(z["y1"])
            fill_op = 0.07 if emphasize else 0.035
            out.append(f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{x1 - x0:.2f}" height="{y1 - y0:.2f}" rx="0.8" fill="{C["zone"]}" '
                       f'fill-opacity="{fill_op}" stroke="{C["zone"]}" stroke-opacity="0.45" stroke-width="0.22" stroke-dasharray="1.2 0.8"/>')
            name = z.get("name") or ""
            lw = 5.5 + _text_w(name, 2.2)
            # 네 모서리 중 집기·제품과 안 겹치는 곳
            corners = [(x0 + 3.2, y0 + 3.2), (x1 - lw + 2.3, y0 + 3.2), (x0 + 3.2, y1 - 3.2), (x1 - lw + 2.3, y1 - 3.2)]
            cx, cy = corners[0]
            for qx, qy in corners:
                r = (qx - 2.3, qy - 2.3, qx - 2.3 + lw, qy + 2.3)
                if not any(not (r[2] < b[0] or b[2] < r[0] or r[3] < b[1] or b[3] < r[1]) for b in self._item_boxes()):
                    cx, cy = qx, qy
                    break
            out.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="2.3" fill="{C["zone"]}"/>')
            out.append(_t(cx, cy + 0.85, z["no"], 2.4, "middle", 800, "#fff", NUMFONT))
            out.append(_t(cx + 3.2, cy + 0.85, name, 2.2, "start", 700, C["zone"]))
            self.labels.append((cx - 2.3, cy - 2.3, cx + 3.2 + _text_w(name, 2.2), cy + 2.3))
            if emphasize:
                a = (z["x1"] - z["x0"]) * (z["y1"] - z["y0"]) / 1e6
                out.append(_t((x0 + x1) / 2, (y0 + y1) / 2 + 1, f"{a:.1f} ㎡", 2.4, "middle", 700, C["zone"], NUMFONT))
        self.add("".join(out))

    def _item_boxes(self):
        if getattr(self, "_boxes", None) is None:
            boxes = []
            for f in self.p.get("fixtures", []):
                boxes.append(G.bbox([self.P(q) for q in S.fixture_poly(f)]))
            for pl in self.p.get("placements", []):
                prod = self.cat.get(pl["product"])
                if prod and prod["category"] != "hvac_cassette":
                    boxes.append(G.bbox([self.P(q) for q in S.placement_poly(pl, prod)]))
            for pp in self.sp.get("pillars", []):
                boxes.append(G.bbox([self.P(q) for q in S.pillar_poly(pp)]))
            self._boxes = boxes
        return self._boxes

    def fixtures(self):
        if "fixtures" not in self.layers:
            return
        out = []
        groups: dict[str, list] = {}
        for f in self.p.get("fixtures", []):
            poly = [self.P(q) for q in S.fixture_poly(f)]
            out.append(_poly(poly, "#ffffff", C["fixture"], 0.25, "1 0.7"))
            groups.setdefault(f.get("group") or f["id"], []).append(f)
        self.add("".join(out))
        for key, fs in groups.items():
            base = fs[0].get("label") or fs[0]["type"]
            if len(fs) > 1 and base.endswith("열"):
                base = base.rsplit(" ", 1)[0] + f" {len(fs)}열"
            elif len(fs) > 1:
                base = f"{base} ×{len(fs)}" if all(f["type"] == fs[0]["type"] for f in fs) else base
            bb = G.bbox([self.P(q) for f in fs for q in S.fixture_poly(f)])
            self._label(base, bb, 2.0, C["muted"], 500)

    def products(self):
        out = []
        clusters: dict[tuple, list] = {}
        for pl in self.p.get("placements", []):
            prod = self.cat.get(pl["product"])
            if not prod:
                continue
            mount = pl.get("mount") or prod["default_mount"]
            poly = [self.P(q) for q in S.placement_poly(pl, prod)]
            if prod["category"] == "hvac_cassette" or mount == "ceiling":
                out.append(_poly(poly, "none", C["brand"], 0.22, "0.9 0.6"))
                out.append(_line(*poly[0], *poly[2], C["brand"], 0.15) + _line(*poly[1], *poly[3], C["brand"], 0.15))
            elif mount == "ceiling_hang":
                out.append(_poly(poly, C["brand"], C["brand"], 0.2, "0.9 0.5", opacity=0.55))
            else:
                out.append(_poly(poly, C["brand"]))
            # 화면 면 표시(앞쪽 변을 굵게)
            if prod["category"] != "hvac_cassette":
                fw, fd, _ = S.placement_dims(pl, prod)
                f = G.facing(pl.get("rot", 0))
                l = G.lateral(pl.get("rot", 0))
                cx, cy = pl["x"] + f[0] * fd / 2, pl["y"] + f[1] * fd / 2
                a = self.P((cx - l[0] * fw / 2, cy - l[1] * fw / 2))
                b = self.P((cx + l[0] * fw / 2, cy + l[1] * fw / 2))
                out.append(_line(*a, *b, "#ffffff" if mount not in ("ceiling_hang",) else C["brand"], 0.18))
            anchor = pl.get("anchor") or ""
            key_anchor = ":".join(anchor.split(":")[:2]) if anchor.startswith(("pillar", "window", "wall", "grid", "outlet", "door")) else pl["id"]
            if anchor.startswith("ceiling"):
                key_anchor = "ceiling"
            clusters.setdefault((pl.get("line"), key_anchor), []).append((pl, prod))
        self.add("".join(out))
        self._clusters = clusters
        if "labels" not in self.layers:
            return
        for (lid, key), items in clusters.items():
            prod = items[0][1]
            n = len(items)
            txt = prod["short"] + (f" ×{n}" if n > 1 else "")
            polys = [self.P(q) for pl, pr in items for q in S.placement_poly(pl, pr)]
            bb = G.bbox(polys)
            self._label(txt, bb, 2.2, "#ffffff", 700, chip=True)

    def _label(self, txt, bb, size, color, weight, chip=False):
        """bb(종이 좌표) 주변에서 다른 라벨과 겹치지 않는 자리에 라벨."""
        tw = _text_w(txt, size) + (2.2 if chip else 0)
        th = size + (1.6 if chip else 0.4)
        x0, y0, x1, y1 = bb
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cands = [(cx - tw / 2, y1 + 1.0), (cx - tw / 2, y0 - 1.0 - th), (x1 + 1.0, cy - th / 2), (x0 - 1.0 - tw, cy - th / 2),
                 (cx - tw / 2, cy - th / 2), (cx - tw / 2, y1 + 1.0 + th + 0.6), (cx - tw / 2, y0 - 2.0 - 2 * th)]
        room = (self.X(0), self.Y(0), self.X(self.sp["width"]), self.Y(self.sp["depth"]))
        pick = None
        for lx, ly in cands:
            r = (lx, ly, lx + tw, ly + th)
            inside = r[0] >= room[0] + 0.5 and r[1] >= room[1] + 0.5 and r[2] <= room[2] - 0.5 and r[3] <= room[3] - 0.5
            clash = any(not (r[2] < q[0] or q[2] < r[0] or r[3] < q[1] or q[3] < r[1]) for q in self.labels)
            if inside and not clash:
                pick = r
                break
        if not pick:
            lx, ly = cands[0]
            pick = (lx, ly, lx + tw, ly + th)
        self.labels.append(pick)
        if chip:
            self.add(f'<rect x="{pick[0]:.2f}" y="{pick[1]:.2f}" width="{tw:.2f}" height="{th:.2f}" rx="0.7" fill="{C["brand"]}"/>')
            self.add(_t(pick[0] + tw / 2, pick[1] + th / 2 + size * 0.36, txt, size, "middle", weight, color))
        else:
            self.add(_t(pick[0] + tw / 2, pick[1] + th * 0.78, txt, size, "middle", weight, color))

    def flow(self, emphasize=False):
        if "flow" not in self.layers:
            return
        fl = (self.val or {}).get("flow") or {}
        path = fl.get("path") or []
        if len(path) < 2:
            return
        pts = [self.P(p) for p in path]
        d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in pts)
        w = 0.45 if emphasize else 0.3
        self.add(f'<path d="{d}" fill="none" stroke="{C["brand"]}" stroke-width="{w}" stroke-dasharray="1.6 0.9" '
                 f'stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arr)"/>')
        self.add(f'<circle cx="{pts[0][0]:.2f}" cy="{pts[0][1]:.2f}" r="0.9" fill="{C["brand"]}"/>')
        for a, b in zip(pts, pts[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 14:
                continue
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            self.add(f'<path d="M-1 -0.9 L0.4 0 L-1 0.9" transform="translate({mx:.2f} {my:.2f}) rotate({ang:.1f})" fill="none" '
                     f'stroke="{C["brand"]}" stroke-width="0.35" stroke-linecap="round"/>')
        if emphasize:
            m = (self.val.get("metrics") or {}).get("flow") or {}
            if m:
                self.add(_t(pts[0][0] + 2, pts[0][1] + 4, f"동선 {m.get('length_mm', 0) / 1000:.1f} m · 최소 폭 {m.get('min_width_mm', 0):,.0f}",
                            2.1, "start", 700, C["brand"]))

    def notes_markers(self):
        out = []
        for i, n in enumerate(self.p.get("notes", [])):
            if not n.get("at"):
                continue
            x, y = self.P(n["at"])
            y = y + 3.2
            out.append(f'<rect x="{x - 2.6:.2f}" y="{y - 1.8:.2f}" width="5.2" height="3.4" rx="0.6" fill="#fff" stroke="{C["ink"]}" stroke-width="0.22"/>')
            out.append(_t(x, y + 0.7, f"메모{i + 1}", 1.8, "middle", 700))
        self.add("".join(out))

    def warnings(self):
        if "warnings" not in self.layers:
            return
        out = []
        for w in (self.val or {}).get("warnings", []):
            if w["level"] not in ("warn", "error") or w.get("ignored"):
                continue
            x, y = self.P(w["at"])
            out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.1" fill="{C["warn"]}" stroke="#fff" stroke-width="0.3"/>')
            out.append(_t(x, y + 0.8, w["no"], 2.2, "middle", 800, "#fff", NUMFONT))
        self.add("".join(out))

    def dims(self):
        if "dims" not in self.layers:
            return
        sp = self.sp
        W, D = sp["width"], sp["depth"]
        t = self.mm(max(150.0, 2.0 * self.scale))
        top = self.Y(0) - t
        # 1) 정면 벽 구간 + 전체 폭
        fr = sorted({0.0, W} | {o["start"] for o in S.openings(sp, "front")} | {o["start"] + o["length"] for o in S.openings(sp, "front")})
        if len(fr) > 2:
            self.add(self.dim_h(fr, top - 6.0, top))
        self.add(self.dim_h([0.0, W], top - 12.0, top))
        # 2) 전체 깊이(왼쪽) + 왼쪽 벽 구간
        left = self.X(0) - t
        lf = sorted({0.0, D} | {o["start"] for o in S.openings(sp, "left")} | {o["start"] + o["length"] for o in S.openings(sp, "left")})
        if len(lf) > 2:
            self.add(self.dim_v(lf, left - 6.0, left))
        self.add(self.dim_v([0.0, D], left - 12.0, left))
        # 3) 오른쪽: 기둥 줄 위치 + 오른쪽 벽 개구부
        right = self.X(W) + t
        ys = sorted({0.0, D} | {p["y"] for p in sp.get("pillars", [])} | {o["start"] for o in S.openings(sp, "right")} |
                    {o["start"] + o["length"] for o in S.openings(sp, "right")})
        if len(ys) > 2:
            self.add(self.dim_v(ys, right + 6.0, right, left=False))
        # 4) 아래: 후면 벽 구간 + 후면 벽 제품 가장자리
        bot = self.Y(D) + t
        xs = {0.0, W} | {o["start"] for o in S.openings(sp, "back")} | {o["start"] + o["length"] for o in S.openings(sp, "back")}
        for pl in self.p.get("placements", []):
            prod = self.cat.get(pl["product"])
            if not prod or S.wall_of_point(sp, (pl["x"], pl["y"]), 600) != "back":
                continue
            fw, _, _ = S.placement_dims(pl, prod)
            xs |= {pl["x"] - fw / 2, pl["x"] + fw / 2}
        xs = sorted(x for x in xs if 0 <= x <= W)
        if len(xs) > 2:
            self.add(self.dim_h(xs, bot + 7.5, bot))
        # 5) 기둥 X 위치(기둥 줄 위)
        ps = sp.get("pillars", [])
        if ps:
            py = min(p["y"] - p["d"] / 2 for p in ps)
            pxs = sorted({0.0, W} | {p["x"] for p in ps})
            self.add(f'<g opacity="0.75">{self.dim_h(pxs, self.Y(py) - 2.6, None, size=1.9)}</g>')
        # 6) 창면 사이니지 간격
        for (lid, key), items in getattr(self, "_clusters", {}).items():
            if not key.startswith("window") or len(items) < 2:
                continue
            items = sorted(items, key=lambda it: (it[0]["x"], it[0]["y"]))
            prod = items[0][1]
            fw, fd, _ = S.placement_dims(items[0][0], prod)
            if S.wall_of_point(sp, (items[0][0]["x"], items[0][0]["y"]), 1500) in ("front", "back"):
                edges = []
                for pl, _ in items:
                    edges += [pl["x"] - fw / 2, pl["x"] + fw / 2]
                gaps = [edges[i] for i in range(1, len(edges) - 1)]
                yv = items[0][0]["y"] + fd / 2 + 450
                self.add(self.dim_h(gaps, self.Y(yv), None, size=1.9))
        # 7) 화면 ↔ 첫 관람석 거리
        aud = [f for f in self.p.get("fixtures", []) if f["type"] in ("bench", "waiting_chairs", "operator_desk")]
        for (lid, key), items in getattr(self, "_clusters", {}).items():
            if not key.startswith(("wall", "grid")):
                continue
            pl, prod = items[0]
            f = G.facing(pl.get("rot", 0))
            best = None
            for a in aud:
                ang, fwd, lat = G.angle_off_axis((pl["x"], pl["y"]), pl.get("rot", 0), (a["x"], a["y"]))
                if fwd > 0 and ang < 30 and (best is None or fwd < best[0]):
                    best = (fwd, a)
            if not best:
                continue
            fwd, a = best
            _, fd, _ = S.placement_dims(pl, prod)
            front = (pl["x"] + f[0] * fd / 2, pl["y"] + f[1] * fd / 2)
            seat_edge = fwd - fd / 2 - a["d"] / 2
            end = (front[0] + f[0] * seat_edge, front[1] + f[1] * seat_edge)
            l = G.lateral(pl.get("rot", 0))
            fw, _, _ = S.placement_dims(pl, prod)
            off = fw / 2 + 300
            p0 = self.P((front[0] + l[0] * off, front[1] + l[1] * off))
            p1 = self.P((end[0] + l[0] * off, end[1] + l[1] * off))
            self.add(_line(*p0, *p1, C["muted"], 0.18) + self.tick(*p0) + self.tick(*p1))
            mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            vert = abs(p1[1] - p0[1]) > abs(p1[0] - p0[0])
            self.add(_t(mx + (1.0 if vert else 0), my + (0.8 if vert else -0.8), f"{seat_edge:,.0f}", 1.9,
                        "start" if vert else "middle", 600, C["ink"], NUMFONT))

    def origin(self):
        x, y = self.X(0), self.Y(0)
        self.add(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="0.7" fill="{C["warn"]}"/>')
        self.add(_t(x - 1.2, y + 4.2, "원점 (0,0)", 1.8, "end", 600, C["warn"]))
        # 도로측 표시
        self.add(_t(self.X(0) - 2, self.Y(0) - self.mm(max(150.0, 2.0 * self.scale)) - 13.0 + 0.8,
                    f"{S.WALL_NAMES.get(S.entrance_wall(self.sp), '정면')}(입구 쪽)", 1.9, "end", 600, C["faint"]))

    def scalebar(self, x, y):
        L = 2000.0 if self.scale <= 150 else 5000.0
        w = self.mm(L)
        out = [f'<rect x="{x:.2f}" y="{y:.2f}" width="{w / 2:.2f}" height="1" fill="{C["ink"]}"/>',
               f'<rect x="{x + w / 2:.2f}" y="{y:.2f}" width="{w / 2:.2f}" height="1" fill="#fff" stroke="{C["ink"]}" stroke-width="0.2"/>',
               _t(x, y - 0.8, "0", 1.8, "middle", 600, C["muted"], NUMFONT),
               _t(x + w, y - 0.8, f"{L / 1000:g} m", 1.8, "middle", 600, C["muted"], NUMFONT)]
        self.add("".join(out))

    # ── 오른쪽 칸 ──
    def side_column(self):
        x0 = self.pw - self.margin - self.col_w
        y = self.margin + 4
        out = []
        out.append(_t(x0, y + 4, {"plan": "배치 도면", "zones": "존 구획도", "flow": "동선도"}[self.kind], 4.6, "start", 800))
        sp = self.sp
        a = S.area_m2(sp)
        out.append(_t(x0, y + 10, f"{sp['width']:,.0f} × {sp['depth']:,.0f} mm · {a:.0f} ㎡ (약 {S.pyeong(a):.0f}평) · 층고 {sp['height']:,.0f}",
                      2.2, "start", 500, C["muted"]))
        y += 16
        if self.kind == "zones":
            y = self._zone_table(x0, y, out)
        else:
            y = self._qty_table(x0, y, out)
        y = self._review(x0, y + 4, out)
        self._legend(x0, y + 4, out)
        self.add("".join(out))

    def _qty_table(self, x0, y, out):
        out.append(_t(x0, y + 3, "제품 수량", 2.8, "start", 800))
        out.append(_t(x0 + self.col_w, y + 3, f"도면 v{self.p.get('version', 1)} 기준 · 단가 미포함", 1.9, "end", 500, C["faint"]))
        y += 6
        cols = (x0, x0 + self.col_w * 0.52, x0 + self.col_w * 0.76, x0 + self.col_w)
        for txt, cx, anc in (("제품", cols[0], "start"), ("설치 · 존", cols[1], "start"), ("수량", cols[3], "end")):
            out.append(_t(cx, y + 2.6, txt, 1.9, anc, 700, C["faint"]))
        y += 4
        out.append(_line(x0, y, x0 + self.col_w, y, C["line"], 0.2))
        zone_of = self._zone_lookup()
        total = 0
        kinds = 0
        for line in self.p.get("lines", []):
            q = len([pl for pl in self.p.get("placements", []) if pl.get("line") == line["id"]])
            if q <= 0:
                continue
            prod = self.cat.get(line["product"])
            if not prod:
                continue
            kinds += 1
            total += q
            zs = sorted({zone_of(pl) for pl in self.p.get("placements", []) if pl.get("line") == line["id"]} - {None})
            mount = MOUNT_NAMES.get(line.get("mount") or prod["default_mount"], "")
            out.append(_t(x0, y + 3.3, prod["short"], 2.3, "start", 700))
            out.append(_t(x0, y + 6.3, prod["code"], 1.7, "start", 500, C["faint"], NUMFONT))
            out.append(_t(cols[1], y + 3.3, mount, 2.0, "start", 500, C["muted"]))
            if zs:
                out.append(_t(cols[1], y + 6.3, "존 " + " · ".join(str(z) for z in zs), 1.8, "start", 600, C["zone"]))
            out.append(_t(cols[3], y + 4.2, f"{q} 대", 2.6, "end", 800, C["ink"], NUMFONT))
            y += 8
            out.append(_line(x0, y, x0 + self.col_w, y, "#e4e7ec", 0.15))
        out.append(_t(x0, y + 4, f"합계 · {kinds}종", 2.3, "start", 800))
        out.append(_t(cols[3], y + 4, f"{total} 대", 2.8, "end", 800, C["brand"], NUMFONT))
        y += 7
        fx = self.p.get("fixtures", [])
        if fx:
            kinds_f = len({f["type"] for f in fx})
            out.append(_t(x0, y + 2.5, f"집기 {kinds_f}종 {len(fx)}개 (동선 검토용 · 참고)", 1.9, "start", 500, C["faint"]))
            y += 5
        return y

    def _zone_lookup(self):
        zones = self.p.get("zones", [])

        def f(pl):
            for z in zones:
                if z["x0"] <= pl["x"] <= z["x1"] and z["y0"] <= pl["y"] <= z["y1"]:
                    return z["no"]
            return None
        return f

    def _zone_table(self, x0, y, out):
        out.append(_t(x0, y + 3, "존 구획 · 동선 순서", 2.8, "start", 800))
        y += 7
        zone_of = self._zone_lookup()
        for z in self.p.get("zones", []):
            a = (z["x1"] - z["x0"]) * (z["y1"] - z["y0"]) / 1e6
            items = {}
            for pl in self.p.get("placements", []):
                if zone_of(pl) == z["no"]:
                    pr = self.cat.get(pl["product"])
                    if pr:
                        items[pr["short"]] = items.get(pr["short"], 0) + 1
            out.append(f'<circle cx="{x0 + 2.2:.2f}" cy="{y + 2.2:.2f}" r="2.1" fill="{C["zone"]}"/>')
            out.append(_t(x0 + 2.2, y + 3.0, z["no"], 2.2, "middle", 800, "#fff", NUMFONT))
            out.append(_t(x0 + 6, y + 3.0, z.get("name") or "", 2.4, "start", 700))
            out.append(_t(x0 + self.col_w, y + 3.0, f"약 {a:.0f} ㎡", 2.0, "end", 600, C["muted"], NUMFONT))
            desc = " · ".join(f"{k} ×{v}" for k, v in items.items()) or "제품 없음"
            out.append(_t(x0 + 6, y + 6.2, desc, 1.9, "start", 500, C["muted"]))
            y += 9
        return y

    def _review(self, x0, y, out):
        summ = (self.val or {}).get("summary") or {}
        notes = self.p.get("notes", [])
        out.append(_t(x0, y + 3, "검토", 2.8, "start", 800))
        out.append(_t(x0 + 12, y + 3, f"경고 {summ.get('warnings', 0)} · 메모 {len(notes)}", 2.1, "start", 600,
                      C["warn"] if summ.get("warnings") else C["muted"]))
        y += 6
        for i, n in enumerate(notes):
            txt = f"메모{i + 1}  {n['text']}"
            out.append(_t(x0, y + 2.6, txt, 1.9, "start", 500, C["ink"]))
            y += 4
        return y

    def _legend(self, x0, y, out):
        items = [("brand", "삼성 제품"), ("hang", "천장 행잉·천장형"), ("fixture", "집기 블록"), ("pillar", "기둥"),
                 ("outlet", "콘센트"), ("flow", "동선"), ("zone", "존 구획"), ("dim", "치수 (mm)")]
        out.append(_t(x0, y + 3, "범례", 2.4, "start", 800))
        y += 5
        colw = self.col_w / 2
        for i, (k, label) in enumerate(items):
            cx = x0 + (i % 2) * colw
            cy = y + (i // 2) * 4.2
            if k == "brand":
                out.append(f'<rect x="{cx:.2f}" y="{cy:.2f}" width="5" height="2.2" fill="{C["brand"]}"/>')
            elif k == "hang":
                out.append(f'<rect x="{cx:.2f}" y="{cy:.2f}" width="5" height="2.2" fill="{C["brand"]}" fill-opacity="0.55" stroke="{C["brand"]}" stroke-width="0.2" stroke-dasharray="0.9 0.5"/>')
            elif k == "fixture":
                out.append(f'<rect x="{cx:.2f}" y="{cy:.2f}" width="5" height="2.2" fill="#fff" stroke="{C["fixture"]}" stroke-width="0.25" stroke-dasharray="1 0.7"/>')
            elif k == "pillar":
                out.append(f'<rect x="{cx + 1.4:.2f}" y="{cy:.2f}" width="2.2" height="2.2" fill="{C["pillar"]}"/>')
            elif k == "outlet":
                out.append(f'<circle cx="{cx + 2.5:.2f}" cy="{cy + 1.1:.2f}" r="0.9" fill="#fff" stroke="{C["outlet"]}" stroke-width="0.25"/>')
            elif k == "flow":
                out.append(_line(cx, cy + 1.1, cx + 5, cy + 1.1, C["brand"], 0.3, "1.6 0.9"))
            elif k == "zone":
                out.append(f'<rect x="{cx:.2f}" y="{cy:.2f}" width="5" height="2.2" rx="0.5" fill="{C["zone"]}" fill-opacity="0.06" stroke="{C["zone"]}" stroke-opacity="0.5" stroke-width="0.2" stroke-dasharray="1.2 0.8"/>')
            elif k == "dim":
                out.append(_line(cx, cy + 1.1, cx + 5, cy + 1.1, C["muted"], 0.18) + self.tick(cx, cy + 1.1) + self.tick(cx + 5, cy + 1.1))
            out.append(_t(cx + 6.5, cy + 1.9, label, 1.9, "start", 500, C["muted"]))
        return y + 18

    def title_block(self):
        w = self.col_w
        h = 30.0
        x0 = self.pw - self.margin - w
        y0 = self.ph - self.margin - h
        rows = [("프로젝트", self.p.get("proposal") or self.p.get("customer") or "-"),
                ("공간", f"{self.sp.get('name') or self.p.get('title')} · {S.area_m2(self.sp):.0f} ㎡"),
                ("축척", f"1:{self.scale} ({self.paper})"), ("단위", "mm · 원점 = 정면 왼쪽 모서리"),
                ("작성", self.today), ("버전", f"v{self.p.get('version', 1)} · Winmate 2D 조감도 PoC")]
        out = [f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#fff" stroke="{C["ink"]}" stroke-width="0.3"/>']
        rh = h / len(rows)
        for i, (k, v) in enumerate(rows):
            yy = y0 + i * rh
            if i:
                out.append(_line(x0, yy, x0 + w, yy, C["line"], 0.15))
            out.append(_t(x0 + 2, yy + rh * 0.68, k, 1.9, "start", 700, C["muted"]))
            out.append(_t(x0 + 18, yy + rh * 0.68, v, 2.0, "start", 600, C["ink"]))
        out.append(_line(x0 + 16, y0, x0 + 16, y0 + h, C["line"], 0.15))
        self.add("".join(out))

    def render(self) -> str:
        pw, ph = self.pw, self.ph
        self.add(f'<rect x="{self.margin / 2:.2f}" y="{self.margin / 2:.2f}" width="{pw - self.margin:.2f}" height="{ph - self.margin:.2f}" '
                 f'fill="none" stroke="{C["ink"]}" stroke-width="0.35"/>')
        W, D = self.sp["width"], self.sp["depth"]
        self.add(f'<rect x="{self.X(0):.2f}" y="{self.Y(0):.2f}" width="{self.mm(W):.2f}" height="{self.mm(D):.2f}" fill="#fbfbfc"/>')
        emph = self.kind
        self.zones(emphasize=(emph == "zones"))
        self.walls()
        self.pillars()
        self.fixtures()
        self.products()
        self.outlets()
        self.flow(emphasize=(emph == "flow"))
        self.dims()
        self.notes_markers()
        self.warnings()
        self.origin()
        self.scalebar(self.X(0), self.ph - self.margin - 4)
        self.side_column()
        self.title_block()
        defs = (f'<defs><marker id="arr" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="3.2" markerHeight="3.2" orient="auto-start-reverse">'
                f'<path d="M0 0 L6 3 L0 6 z" fill="{C["brand"]}"/></marker></defs>')
        title = escape(f"{self.sp.get('name', '')} 2D 조감도 — {self.kind}")
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{pw}mm" height="{ph}mm" viewBox="0 0 {pw} {ph}" '
                f'font-family="{FONT}" role="img" aria-label="{title}"><title>{title}</title>{defs}'
                f'<rect width="{pw}" height="{ph}" fill="#ffffff"/>' + "".join(self.out) + "</svg>")


def plan_svg(project: dict, catalog: Catalog, kind: str = "plan", paper: str = "A3", layers=None,
             validation: dict | None = None, today: str | None = None) -> str:
    if kind == "zones":
        layers = layers if layers is not None else ("zones", "fixtures", "labels", "power")
    elif kind == "flow":
        layers = layers if layers is not None else ("flow", "zones", "fixtures", "labels")
    return Sheet(project, catalog, paper, kind, layers, validation, today).render()
