"""로컬 초안 렌더 `be-draft`(08-birdseye §7.7) — 결정적, CPU(numpy 투영 + 화가 알고리즘 + 평면 음영 + 윤곽선, Pillow 1024×576).

- 3D 구성: 바닥 다각형, 벽을 층고까지 돌출(창 = 반투명 유리, 문 = 틈), 기둥 상자, 제품 = 상자 + 화면 면, 가구 = 카탈로그 덩어리,
  코어 = 회색 덩어리. 조감 · 탑뷰는 카메라 쪽 벽을 낮게 잘라(컷어웨이) 안을 보인다.
- 카메라 프리셋: aerial45(주출입구 쪽에서 45° 회전 · 앙각 45° · bbox 8% 여백 · FOV 40°) · entrance(눈높이 1.6 m, 입구 안쪽 0.5 m,
  방 중심을 봄, FOV 60°) · product_front(눈높이 1.6 m, 대상 디스플레이 법선 위 시청 거리, FOV 50°) · top(직교) · custom(LLM JSON 제한).
- draft_v0 = 구조 + 제품(「마감재 적용 전」), draft_v1 = + 가구 + 톤. 도입 전 = 제품 · 가구 · 랩핑을 뺀 draft_v1.
- 카메라를 컷에 저장한다(존 포인트 투영 · QC 상자 힌트 · 클릭 역투영).
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from . import config
from .engine.core import main_entrance, seat_distance
from .engine.geometry import facing_vec, rect_corners, room_union, wall_geoms

W_IMG, H_IMG = 1024, 576
NEUTRAL = {"floor": "#e4e6ea", "wall": "#f3f4f6", "accent": "#c9ced6"}
SCREEN = (24, 28, 36)
BODY = (58, 62, 70)
GLASS = (170, 205, 235)
COLUMN = (205, 208, 214)
CORE = (176, 180, 188)
WRAP = (36, 40, 48)


def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (int(a[0] * (1 - t) + b[0] * t), int(a[1] * (1 - t) + b[1] * t), int(a[2] * (1 - t) + b[2] * t))


# ── 카메라 ───────────────────────────────────────────────

@dataclass
class Cam:
    eye: np.ndarray
    target: np.ndarray
    fov: float
    ortho: bool = False
    ortho_w: float = 0.0
    up: np.ndarray | None = None

    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        f = self.target - self.eye
        f = f / (np.linalg.norm(f) + 1e-12)
        up = self.up if self.up is not None else np.array([0.0, 0.0, 1.0])
        r = np.cross(f, up)
        if np.linalg.norm(r) < 1e-6:
            up = np.array([0.0, -1.0, 0.0])
            r = np.cross(f, up)
        r = r / (np.linalg.norm(r) + 1e-12)
        u = np.cross(r, f)
        return r, u, f

    def to_cam(self, pts: np.ndarray) -> np.ndarray:
        r, u, f = self.basis()
        d = pts - self.eye
        return np.stack([d @ r, d @ u, d @ f], axis=-1)

    def focal(self) -> float:
        return (W_IMG / 2) / math.tan(math.radians(self.fov) / 2)

    def project_cam(self, pc: np.ndarray) -> np.ndarray:
        if self.ortho:
            s = W_IMG / max(self.ortho_w, 1e-6)
            return np.stack([W_IMG / 2 + pc[:, 0] * s, H_IMG / 2 - pc[:, 1] * s], axis=-1)
        fpx = self.focal()
        z = np.maximum(pc[:, 2], 1e-6)
        return np.stack([W_IMG / 2 + fpx * pc[:, 0] / z, H_IMG / 2 - fpx * pc[:, 1] / z], axis=-1)

    def project(self, x: float, y: float, z: float) -> tuple[float, float] | None:
        pc = self.to_cam(np.array([[x, y, z]], dtype=float))
        if not self.ortho and pc[0, 2] <= 0.05:
            return None
        p = self.project_cam(pc)[0]
        return float(p[0]), float(p[1])

    def record(self) -> dict[str, Any]:
        return {"pos": [round(float(v), 3) for v in self.eye], "target": [round(float(v), 3) for v in self.target],
                "fov_deg": round(self.fov, 2), "ortho": self.ortho, "ortho_w": round(self.ortho_w, 3) if self.ortho else None}

    @staticmethod
    def from_record(rec: dict[str, Any]) -> "Cam":
        up = np.array([0.0, -1.0, 0.0]) if rec.get("ortho") else None
        return Cam(np.array(rec["pos"], dtype=float), np.array(rec["target"], dtype=float), float(rec.get("fov_deg") or 40),
                   bool(rec.get("ortho")), float(rec.get("ortho_w") or 0.0), up)

    def unproject_floor(self, u: float, v: float) -> tuple[float, float] | None:
        """정규 (u, v) → 바닥(z = 0) 점."""
        r, up, f = self.basis()
        px, py = u * W_IMG - W_IMG / 2, H_IMG / 2 - v * H_IMG
        if self.ortho:
            s = W_IMG / max(self.ortho_w, 1e-6)
            origin = self.eye + r * (px / s) + up * (py / s)
            d = f
        else:
            fpx = self.focal()
            d = f + r * (px / fpx) + up * (py / fpx)
            origin = self.eye
        if abs(d[2]) < 1e-9:
            return None
        t = -origin[2] / d[2]
        if t <= 0:
            return None
        p = origin + d * t
        return float(p[0]), float(p[1])


def _bbox3(space: dict[str, Any]) -> tuple[float, float, float, float, float]:
    minx, miny, maxx, maxy = room_union(space).bounds
    h = float((space.get("ceiling_h") or {}).get("value") or 3.0)
    return minx, miny, maxx, maxy, h


def _fit_distance(target: np.ndarray, direction: np.ndarray, corners: np.ndarray, fov: float, margin: float = 0.08) -> float:
    lo, hi = 1.0, 400.0
    for _ in range(40):
        mid = (lo + hi) / 2
        cam = Cam(target + direction * mid, target, fov)
        pc = cam.to_cam(corners)
        if np.any(pc[:, 2] <= 0.1):
            lo = mid
            continue
        p = cam.project_cam(pc)
        mx, my = W_IMG * margin, H_IMG * margin
        ok = np.all((p[:, 0] >= mx) & (p[:, 0] <= W_IMG - mx) & (p[:, 1] >= my) & (p[:, 1] <= H_IMG - my))
        if ok:
            hi = mid
        else:
            lo = mid
    return hi


def camera_for(space: dict[str, Any], layout: dict[str, Any] | None, view: dict[str, Any]) -> tuple[Cam, str | None]:
    """프리셋 → 카메라(+ 대체 경로 메모)."""
    minx, miny, maxx, maxy, H = _bbox3(space)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    walls = wall_geoms(space)
    ent = main_entrance(space, walls)
    nx, ny = (ent["nx"], ent["ny"]) if ent else (0.0, 1.0)
    preset = view.get("preset") or "aerial45"
    if preset == "top":
        w = (maxx - minx) * 1.08
        h = (maxy - miny) * 1.08
        ow = max(w, h * W_IMG / H_IMG)
        return Cam(np.array([cx, cy, 60.0]), np.array([cx, cy, 0.0]), 40.0, True, ow, np.array([0.0, -1.0, 0.0])), None
    if preset == "entrance" and ent:
        ix, iy = ent["inside"]
        eye = np.array([ix + nx * 0.0, iy + ny * 0.0, 1.6])
        return Cam(eye, np.array([cx, cy, 1.0]), 60.0), None
    if preset == "product_front" and layout:
        tgt = next((it for it in layout.get("items", []) if it["id"] == view.get("target_item_id")), None)
        if tgt is None:
            tgt = _largest_display(layout)
        if tgt is not None:
            fx, fy = facing_vec(tgt["rot_deg"])
            d = seat_distance(tgt.get("diag_inch") or 75, config.rules())
            room = room_union(space)
            from shapely.geometry import Point

            dd = d
            while dd > 1.5 and not room.buffer(-0.3).contains(Point(tgt["x"] + fx * dd, tgt["y"] + fy * dd)):
                dd -= 0.5
            eye = np.array([tgt["x"] + fx * dd, tgt["y"] + fy * dd, 1.6])
            return Cam(eye, np.array([tgt["x"], tgt["y"], float(tgt.get("z") or 1.0) + float(tgt.get("h") or 1.0) / 2]), 50.0), None
    if preset == "custom" and view.get("camera"):
        rec = view["camera"]
        return Cam(np.array(rec["pos"], dtype=float), np.array(rec["target"], dtype=float), float(rec.get("fov_deg") or 50)), None
    # aerial45: 주출입구 쪽(방 밖)에서 45° 돌리고 앙각 45°
    ox, oy = -nx, -ny
    t = math.radians(45)
    hx, hy = ox * math.cos(t) - oy * math.sin(t), ox * math.sin(t) + oy * math.cos(t)
    el = math.radians(45)
    direction = np.array([hx * math.cos(el), hy * math.cos(el), math.sin(el)])
    target = np.array([cx, cy, 0.0])
    corners = np.array([[x, y, z] for x in (minx, maxx) for y in (miny, maxy) for z in (0.0, H)], dtype=float)
    dist = _fit_distance(target, direction, corners, 40.0)
    return Cam(target + direction * dist, target, 40.0), None


def _largest_display(layout: dict[str, Any]) -> dict[str, Any] | None:
    disp = [it for it in layout.get("items", []) if it["kind"] == "product" and it.get("mount") != "window_facing"]
    if not disp:
        disp = [it for it in layout.get("items", []) if it["kind"] == "product"]
    if not disp:
        return None
    return max(disp, key=lambda it: (it["w"] * it["h"], -int(it["id"][2:]) if it["id"][2:].isdigit() else 0))


def clamp_custom(space: dict[str, Any], rec: dict[str, Any]) -> dict[str, Any]:
    """LLM 카메라 JSON 을 방 bbox(±2 m) · 높이(안 ≤ 층고 − 0.2 m, 밖 ≤ 30 m)로 제한."""
    minx, miny, maxx, maxy, H = _bbox3(space)
    x, y, z = (float(v) for v in (rec.get("pos") or [(minx + maxx) / 2, maxy, 1.6])[:3])
    x = min(max(x, minx - 2), maxx + 2)
    y = min(max(y, miny - 2), maxy + 2)
    inside = minx <= x <= maxx and miny <= y <= maxy
    z = min(max(z, 0.3), H - 0.2 if inside else 30.0)
    tx, ty, tz = (float(v) for v in (rec.get("target") or [(minx + maxx) / 2, (miny + maxy) / 2, 0.0])[:3])
    tx = min(max(tx, minx - 2), maxx + 2)
    ty = min(max(ty, miny - 2), maxy + 2)
    tz = min(max(tz, 0.0), H)
    fov = min(max(float(rec.get("fov_deg") or 50), 20.0), 90.0)
    return {"pos": [round(x, 3), round(y, 3), round(z, 3)], "target": [round(tx, 3), round(ty, 3), round(tz, 3)], "fov_deg": fov,
            "ortho": False}


def rules_camera(space: dict[str, Any], text: str) -> dict[str, Any]:
    """camera:rules — 「위에서/내려다」 → 높이 ↑, 「입구」 → entrance."""
    minx, miny, maxx, maxy, H = _bbox3(space)
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    walls = wall_geoms(space)
    ent = main_entrance(space, walls)
    ix, iy = ent["inside"] if ent else (cx, maxy)
    z = 1.6
    if any(k in text for k in ("위에서", "내려다", "난간", "2층", "높은")):
        z = H - 0.2
    return clamp_custom(space, {"pos": [ix, iy, z], "target": [cx, cy, 0.0], "fov_deg": 55})


# ── 장면 ─────────────────────────────────────────────────

@dataclass
class Face:
    pts: np.ndarray            # (n, 3) world
    color: tuple[int, int, int]
    normal: np.ndarray
    kind: str = "solid"        # solid · glass · screen · floor · line
    alpha: float = 1.0
    outline: bool = True
    layer: int = 2             # 0 바닥 · 1 먼 벽 · 2 나머지(깊이 순)


def _box(x: float, y: float, w: float, d: float, rot: float, z0: float, z1: float, color: tuple[int, int, int], *,
         screen_front: bool = False, kind: str = "solid") -> list[Face]:
    cs = rect_corners(x, y, w, d, rot)          # 0: 뒤-왼 1: 뒤-오 2: 앞-오 3: 앞-왼 (앞 = facing)
    bottom = [np.array([px, py, z0]) for px, py in cs]
    top = [np.array([px, py, z1]) for px, py in cs]
    faces = []
    fx, fy = facing_vec(rot)
    side_idx = [(0, 1), (1, 2), (2, 3), (3, 0)]
    for a, b in side_idx:
        quad = np.array([bottom[a], bottom[b], top[b], top[a]])
        mid = (bottom[a] + bottom[b]) / 2
        cxy = np.array([x, y, mid[2]])
        n = mid - cxy
        n[2] = 0
        n = n / (np.linalg.norm(n) + 1e-9)
        is_front = (a, b) == (2, 3)
        col = SCREEN if (screen_front and is_front) else color
        faces.append(Face(quad, col, n, "screen" if (screen_front and is_front) else kind))
    faces.append(Face(np.array(top), color, np.array([0.0, 0.0, 1.0]), kind))
    return faces


def build_scene(space: dict[str, Any], layout: dict[str, Any] | None, *, cam: Cam, tone: str | None, furniture: bool,
                products: bool, neutral: bool, cutaway: bool) -> list[Face]:
    tone_c = NEUTRAL if neutral else config.tone_info(tone)
    floor_c = _hex(tone_c["floor"])
    wall_c = _hex(tone_c["wall"])
    accent_c = _hex(tone_c["accent"])
    H = float((space.get("ceiling_h") or {}).get("value") or 3.0)
    faces: list[Face] = []
    for r in space.get("rooms", []):
        pts = np.array([[p[0], p[1], 0.0] for p in r["outline"]], dtype=float)
        faces.append(Face(pts, floor_c, np.array([0.0, 0.0, 1.0]), "floor", outline=False, layer=0))
    # 벽(개구부 자르기)
    eye = cam.eye
    for w in wall_geoms(space):
        ops = sorted([o for o in space.get("openings", []) if o.get("wall_id") == w.id], key=lambda o: o["offset"])
        mid = np.array([(w.ax + w.bx) / 2, (w.ay + w.by) / 2])
        to_cam = np.array([eye[0], eye[1]]) - mid
        near = cutaway and (to_cam[0] * (-w.nx) + to_cam[1] * (-w.ny)) > 0
        hh = 0.35 if near else H
        segs: list[tuple[float, float, str]] = []
        cur = 0.0
        for o in ops:
            if o["offset"] > cur:
                segs.append((cur, o["offset"], "wall"))
            segs.append((o["offset"], o["offset"] + o["width"], o["kind"]))
            cur = max(cur, o["offset"] + o["width"])
        if cur < w.length:
            segs.append((cur, w.length, "wall"))
        for s0, s1, kind in segs:
            if s1 - s0 < 1e-3:
                continue
            cxw = w.ax + w.ux * (s0 + s1) / 2
            cyw = w.ay + w.uy * (s0 + s1) / 2
            rot = math.degrees(math.atan2(w.uy, w.ux))
            seg_len = s1 - s0
            layer = 2 if near else 1
            seg_faces: list[Face] = []
            if kind == "wall":
                seg_faces += _box(cxw, cyw, seg_len, w.t, rot, 0.0, hh, wall_c)
            elif kind == "window":
                sill = 0.0 if near else 0.15
                head = min(hh, H - 0.3) if not near else hh
                if not near:
                    seg_faces += _box(cxw, cyw, seg_len, w.t, rot, head, hh if hh > head else head + 0.01, wall_c)
                seg_faces += _box(cxw, cyw, seg_len, 0.04, rot, sill, head, GLASS, kind="glass")
            else:  # door · opening — 위 인방
                if not near and H > 2.4:
                    seg_faces += _box(cxw, cyw, seg_len, w.t, rot, 2.4, H, wall_c)
            for sf in seg_faces:
                sf.layer = layer
            faces += seg_faces
    for c in space.get("columns", []):
        faces += _box(c["center"][0], c["center"][1], c["w"], c["d"], 0.0, 0.0, H, COLUMN)
    for k in space.get("cores", []):
        poly = k.get("polygon") or []
        if len(poly) >= 3:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            faces += _box((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys), 0.0, 0.0, H * 0.98, CORE)
    for it in (layout or {}).get("items", []):
        if it.get("unplaced"):
            continue
        if it["kind"] == "product" and products:
            z0 = float(it.get("z") or 0.0)
            faces += _box(it["x"], it["y"], it["w"], max(it["d"], 0.05), it["rot_deg"], z0, z0 + it["h"], BODY, screen_front=True)
            if it.get("mount") == "window_facing" or it.get("role") == "interactive":
                faces += _box(it["x"], it["y"], 0.08, 0.3, it["rot_deg"], 0.0, z0, BODY)
        elif it["kind"] == "column_wrap" and products:
            faces += _wrap(it, H)
        elif it["kind"] == "furniture" and furniture:
            parts = it.get("parts") or []
            col = _mix(accent_c, (120, 112, 104), 0.25) if not neutral else (190, 192, 198)
            if parts:
                fx, fy = facing_vec(it["rot_deg"])
                ux, uy = math.cos(math.radians(it["rot_deg"])), math.sin(math.radians(it["rot_deg"]))
                for p in parts:
                    px = it["x"] + ux * float(p.get("x", 0)) + fx * float(p.get("y", 0))
                    py = it["y"] + uy * float(p.get("x", 0)) + fy * float(p.get("y", 0))
                    pc = col if p.get("kind") != "table" else _mix(col, (255, 255, 255), 0.25)
                    faces += _box(px, py, float(p["w"]), float(p["d"]), it["rot_deg"], 0.0, float(p["h"]), pc)
            else:
                faces += _box(it["x"], it["y"], it["w"], it["d"], it["rot_deg"], 0.0, max(it["h"], 0.3), col)
    return faces


def _wrap(it: dict[str, Any], H: float) -> list[Face]:
    """기둥 랩핑 프레임: 밝은 프레임 + 네 면 화면 띠(1.0~2.6 m)."""
    top = min(it["h"], H - 0.05)
    out = _box(it["x"], it["y"], it["w"], it["d"], 0.0, 0.0, top, (214, 216, 222))
    band = _box(it["x"], it["y"], it["w"] + 0.02, it["d"] + 0.02, 0.0, 1.0, min(2.6, top - 0.1), SCREEN)
    for f in band:
        if abs(f.normal[2]) < 0.5:
            f.kind = "screen"
            out.append(f)
    return out


# ── 그리기 ───────────────────────────────────────────────

def _clip_near(pc: np.ndarray, near: float = 0.08) -> np.ndarray:
    out = []
    n = len(pc)
    for i in range(n):
        a, b = pc[i], pc[(i + 1) % n]
        ain, bin_ = a[2] >= near, b[2] >= near
        if ain:
            out.append(a)
        if ain != bin_:
            t = (near - a[2]) / (b[2] - a[2])
            out.append(a + (b - a) * t)
    return np.array(out) if out else np.zeros((0, 3))


def render(space: dict[str, Any], layout: dict[str, Any] | None, *, view: dict[str, Any], tone: str | None, light: str = "day",
           stage: str = "v1", before: bool = False) -> tuple[bytes, dict[str, Any]]:
    """stage v0 = 구조 + 제품(중립 색) · v1 = + 가구 + 톤. 반환 (PNG, 카메라 기록)."""
    cam, _ = camera_for(space, layout, view)
    neutral = stage == "v0"
    cutaway = view.get("preset") in ("aerial45", "top", None)
    faces = build_scene(space, layout, cam=cam, tone=tone, furniture=(stage == "v1" and not before), products=not before,
                        neutral=neutral, cutaway=cutaway)
    sky = (238, 240, 244) if light == "day" else ((236, 214, 196) if light == "evening" else (26, 30, 42))
    img = Image.new("RGB", (W_IMG, H_IMG), sky)
    draw = ImageDraw.Draw(img, "RGBA")
    light_dir = np.array([-0.35, -0.55, 0.76])
    light_dir = light_dir / np.linalg.norm(light_dir)
    items: list[tuple[float, np.ndarray, Face]] = []
    for f in faces:
        pc = cam.to_cam(f.pts)
        if not cam.ortho:
            pc = _clip_near(pc)
            if len(pc) < 3:
                continue
        depth = float(pc[:, 2].mean()) if not cam.ortho else float(-(f.pts[:, 2].mean()) * 0.01 + pc[:, 2].mean())
        p2 = cam.project_cam(pc)
        items.append((depth, p2, f))
    items.sort(key=lambda t: (t[2].layer, -t[0]))
    for depth, p2, f in items:
        shade = 0.62 + 0.38 * max(0.0, float(f.normal @ light_dir))
        col = f.color
        if f.kind == "screen":
            col = (70, 130, 235) if light == "night" else ((40, 52, 78) if light == "evening" else SCREEN)
            shade = 1.0 if light == "night" else 0.95
        r, g, b = (int(min(255, c * shade)) for c in col)
        if light == "evening" and f.kind != "screen":
            r, g, b = _mix((r, g, b), (255, 170, 90), 0.15)
        if light == "night" and f.kind != "screen":
            r, g, b = (int(c * 0.42) for c in (r, g, b))
            if f.kind == "floor":
                r, g, b = _mix((r, g, b), (255, 214, 150), 0.12)
        alpha = 255
        if f.kind == "glass":
            alpha = 120 if light != "night" else 160
        pts = [(float(x), float(y)) for x, y in p2]
        draw.polygon(pts, fill=(r, g, b, alpha))
        if f.outline:
            oc = (int(r * 0.7), int(g * 0.7), int(b * 0.7), 255 if f.kind != "glass" else 140)
            draw.line(pts + [pts[0]], fill=oc, width=1)
        if f.kind == "floor":
            _floor_grid(draw, cam, f, (r, g, b))
    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue(), cam.record()


def _floor_grid(draw: ImageDraw.ImageDraw, cam: Cam, f: Face, col: tuple[int, int, int]) -> None:
    xs = f.pts[:, 0]
    ys = f.pts[:, 1]
    lc = (int(col[0] * 0.9), int(col[1] * 0.9), int(col[2] * 0.9), 110)
    for gx in np.arange(math.ceil(xs.min()), math.floor(xs.max()) + 1, 1.0):
        a = cam.project(float(gx), float(ys.min()), 0.0)
        b = cam.project(float(gx), float(ys.max()), 0.0)
        if a and b:
            draw.line([a, b], fill=lc, width=1)
    for gy in np.arange(math.ceil(ys.min()), math.floor(ys.max()) + 1, 1.0):
        a = cam.project(float(xs.min()), float(gy), 0.0)
        b = cam.project(float(xs.max()), float(gy), 0.0)
        if a and b:
            draw.line([a, b], fill=lc, width=1)


def project_norm(cam_rec: dict[str, Any], x: float, y: float, z: float) -> list[float] | None:
    cam = Cam.from_record(cam_rec)
    p = cam.project(x, y, z)
    if p is None:
        return None
    return [round(p[0] / W_IMG, 4), round(p[1] / H_IMG, 4)]


def unproject_norm(cam_rec: dict[str, Any], u: float, v: float) -> tuple[float, float] | None:
    return Cam.from_record(cam_rec).unproject_floor(u, v)


def product_boxes(cam_rec: dict[str, Any], layout: dict[str, Any]) -> list[dict[str, Any]]:
    """QC 상자 힌트 — 제품 묶음별 투영 상자 [x0, y0, x1, y1] 0..1."""
    cam = Cam.from_record(cam_rec)
    out = []
    groups: dict[str, list[dict[str, Any]]] = {}
    for it in layout.get("items", []):
        if it["kind"] == "product" and not it.get("unplaced"):
            groups.setdefault(it["group_id"], []).append(it)
    for gid, items in groups.items():
        pts = []
        for it in items:
            z0 = float(it.get("z") or 0.0)
            for px, py in rect_corners(it["x"], it["y"], it["w"], it["d"], it["rot_deg"]):
                for z in (z0, z0 + it["h"]):
                    p = cam.project(px, py, z)
                    if p:
                        pts.append(p)
        if not pts:
            continue
        xs = [p[0] / W_IMG for p in pts]
        ys = [p[1] / H_IMG for p in pts]
        out.append({"group_id": gid, "box": [round(max(0.0, min(xs)), 4), round(max(0.0, min(ys)), 4),
                                             round(min(1.0, max(xs)), 4), round(min(1.0, max(ys)), 4)]})
    return out


def tint_png(png: bytes, tone: str | None, light: str) -> bytes:
    """T2I 없음 — 초안을 톤 색으로 칠한 이미지를 컷으로(「초안 렌더」)."""
    im = Image.open(io.BytesIO(png)).convert("RGB")
    tc = _hex(config.tone_info(tone)["swatch"])
    overlay = Image.new("RGB", im.size, tc)
    im = Image.blend(im, overlay, 0.12)
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()
