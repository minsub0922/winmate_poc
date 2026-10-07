"""평면 기하 — 단위 mm, 좌표계는 도면과 같다.

원점 (0,0) = 정면(도로측) 왼쪽 모서리, X 는 오른쪽, Y 는 안쪽(도면 아래쪽). SVG 좌표와 같다.
회전 rot(도)는 화면에서 시계 방향. rot=0 인 제품은 −Y(정면·도로측)를 바라본다.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

Pt = tuple[float, float]
Poly = list[Pt]

EPS = 1e-6


def facing(rot: float) -> Pt:
    """rot 에서 화면(앞면)이 바라보는 단위 벡터. rot=0 → (0,-1), 90 → (1,0)."""
    r = math.radians(rot)
    return (math.sin(r), -math.cos(r))


def lateral(rot: float) -> Pt:
    """바라보는 방향 기준 오른쪽(화면 가로 방향) 단위 벡터."""
    r = math.radians(rot)
    return (math.cos(r), math.sin(r))


def rot_rect(cx: float, cy: float, w: float, d: float, rot: float = 0.0) -> Poly:
    """중심 (cx,cy), 가로 w(로컬 x), 깊이 d(로컬 y) 사각형을 rot 만큼 돌린 꼭짓점 4개."""
    r = math.radians(rot)
    c, s = math.cos(r), math.sin(r)
    hw, hd = w / 2.0, d / 2.0
    pts = []
    for lx, ly in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd)):
        pts.append((cx + lx * c - ly * s, cy + lx * s + ly * c))
    return pts


def rect_poly(x0: float, y0: float, x1: float, y1: float) -> Poly:
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def bbox(poly: Iterable[Pt]) -> tuple[float, float, float, float]:
    xs, ys = zip(*poly)
    return min(xs), min(ys), max(xs), max(ys)


def area(poly: Sequence[Pt]) -> float:
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def centroid(poly: Sequence[Pt]) -> Pt:
    xs, ys = zip(*poly)
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _axes(poly: Sequence[Pt]):
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        ln = math.hypot(ex, ey)
        if ln > EPS:
            yield (-ey / ln, ex / ln)


def _project(poly: Sequence[Pt], ax: Pt) -> tuple[float, float]:
    ds = [p[0] * ax[0] + p[1] * ax[1] for p in poly]
    return min(ds), max(ds)


def overlap_depth(a: Sequence[Pt], b: Sequence[Pt]) -> tuple[float, Pt]:
    """볼록 다각형 SAT. 겹치면 (최소 침투 깊이, 밀어낼 축 — a 를 이 방향으로 옮기면 빠짐), 아니면 (0, (0,0))."""
    best, best_ax = math.inf, (0.0, 0.0)
    for ax in list(_axes(a)) + list(_axes(b)):
        a0, a1 = _project(a, ax)
        b0, b1 = _project(b, ax)
        o = min(a1, b1) - max(a0, b0)
        if o <= EPS:
            return 0.0, (0.0, 0.0)
        # 빠져나오는 거리 — 한쪽이 다른 쪽 안에 들어 있으면 겹친 길이보다 더 옮겨야 한다
        push_pos, push_neg = b1 - a0, a1 - b0
        d, axv = (push_pos, ax) if push_pos <= push_neg else (push_neg, (-ax[0], -ax[1]))
        if d < best:
            best, best_ax = d, axv
    return best, best_ax


def intersects(a: Sequence[Pt], b: Sequence[Pt], tol: float = 1.0) -> bool:
    """겹침 깊이가 tol(mm)보다 크면 True — 맞닿은 것은 겹침이 아니다."""
    d, _ = overlap_depth(a, b)
    return d > tol


def seg_point_dist(p: Pt, a: Pt, b: Pt) -> float:
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    ln2 = dx * dx + dy * dy
    if ln2 < EPS:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ln2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def seg_seg_intersect(p1: Pt, p2: Pt, p3: Pt, p4: Pt) -> bool:
    def orient(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1 = orient(p3, p4, p1)
    d2 = orient(p3, p4, p2)
    d3 = orient(p1, p2, p3)
    d4 = orient(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def poly_distance(a: Sequence[Pt], b: Sequence[Pt]) -> float:
    """두 볼록 다각형 사이 최단 거리(겹치면 0)."""
    if intersects(a, b, tol=0.0):
        return 0.0
    best = math.inf
    for poly1, poly2 in ((a, b), (b, a)):
        n = len(poly2)
        for p in poly1:
            for i in range(n):
                best = min(best, seg_point_dist(p, poly2[i], poly2[(i + 1) % n]))
    return best


def point_in_poly(p: Pt, poly: Sequence[Pt]) -> bool:
    x, y = p
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xin:
                inside = not inside
    return inside


def point_poly_dist(p: Pt, poly: Sequence[Pt]) -> float:
    if point_in_poly(p, poly):
        return 0.0
    n = len(poly)
    return min(seg_point_dist(p, poly[i], poly[(i + 1) % n]) for i in range(n))


def ray_poly_hit(o: Pt, d: Pt, poly: Sequence[Pt], max_t: float) -> float | None:
    """반직선 o + t·d (|d|=1) 가 다각형 경계에 처음 닿는 t. 없으면 None."""
    best = None
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        den = d[0] * ey - d[1] * ex
        if abs(den) < EPS:
            continue
        t = ((ax - o[0]) * ey - (ay - o[1]) * ex) / den
        u = ((ax - o[0]) * d[1] - (ay - o[1]) * d[0]) / den
        if t >= 0 and 0 <= u <= 1 and t <= max_t:
            if best is None or t < best:
                best = t
    return best


def translate(poly: Sequence[Pt], dx: float, dy: float) -> Poly:
    return [(x + dx, y + dy) for x, y in poly]


def inflate_rect(poly: Sequence[Pt], m: float) -> Poly:
    """축 정렬 bbox 를 m 만큼 키운 사각형(빠른 근사)."""
    x0, y0, x1, y1 = bbox(poly)
    return rect_poly(x0 - m, y0 - m, x1 + m, y1 + m)


def snap(v: float, step: float) -> float:
    return round(v / step) * step


def snap_up(v: float, step: float) -> float:
    """0에서 멀어지는 방향으로 step 단위 올림."""
    if v >= 0:
        return math.ceil(v / step - 1e-9) * step
    return -math.ceil(-v / step - 1e-9) * step


def dist(a: Pt, b: Pt) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def manhattan(a: Pt, b: Pt) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def angle_off_axis(display_pos: Pt, rot: float, viewer: Pt) -> tuple[float, float, float]:
    """(수평 시야각°, 정면 거리, 좌우 오프셋). 시야각은 화면 법선 기준."""
    f = facing(rot)
    l = lateral(rot)
    vx, vy = viewer[0] - display_pos[0], viewer[1] - display_pos[1]
    fwd = vx * f[0] + vy * f[1]
    lat = vx * l[0] + vy * l[1]
    ang = math.degrees(math.atan2(abs(lat), fwd)) if (abs(fwd) > EPS or abs(lat) > EPS) else 0.0
    return ang, fwd, lat


def norm_rot(r: float) -> float:
    r = r % 360.0
    return 0.0 if abs(r - 360.0) < 1e-6 else r
