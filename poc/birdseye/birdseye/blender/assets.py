"""절차적 가구·제품 모델 — 외부 에셋 없이 상자·원기둥·구로 만든다.

좌표: 미터. 각 모델의 원점 = 바닥 점유 중심(바닥 높이), 가로 = 로컬 X, 깊이 = 로컬 Y, 앞면 = +Y.
(도면 rot=0 은 −y(정면)를 보고, Blender 에서는 Y = −y 이므로 +Y 를 본다.)
"""
from __future__ import annotations

import math
import random

import bmesh
import bpy

try:
    from . import materials as M
except ImportError:  # Blender 에서 스크립트 폴더를 sys.path 에 넣고 불러올 때
    import materials as M

COLL: bpy.types.Collection | None = None


def _link(ob, parent=None):
    (COLL or bpy.context.scene.collection).objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def empty(name, loc=(0, 0, 0), rot_z=0.0, parent=None):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = 0.2
    ob.location = loc
    ob.rotation_euler.z = rot_z
    return _link(ob, parent)


def _smooth(me):
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))


def box(name, sx, sy, sz, mat, loc=(0, 0, 0), parent=None, bevel=0.0, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(max(sx, 1e-4), max(sy, 1e-4), max(sz, 1e-4)), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    if mat is not None:
        me.materials.append(mat)
    if bevel > 0:
        mod = ob.modifiers.new("bevel", "BEVEL")
        mod.width = min(bevel, sx / 2.2, sy / 2.2, sz / 2.2)
        mod.segments = 2
        mod.limit_method = "ANGLE"
        _smooth(me)
        try:
            ob.modifiers.new("wn", "WEIGHTED_NORMAL")
        except Exception:  # noqa: BLE001
            pass
    return _link(ob, parent)


def cyl(name, r, h, mat, loc=(0, 0, 0), parent=None, r2=None, seg=24, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r if r2 is None else r2, depth=h)
    bm.to_mesh(me)
    bm.free()
    _smooth(me)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    if mat is not None:
        me.materials.append(mat)
    return _link(ob, parent)


def sphere(name, r, mat, loc=(0, 0, 0), parent=None, sub=2, scale=(1, 1, 1)):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    bm.to_mesh(me)
    bm.free()
    _smooth(me)
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.scale = scale
    if mat is not None:
        me.materials.append(mat)
    return _link(ob, parent)


def plane(name, sx, sy, mat, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    bmesh.ops.scale(bm, vec=(sx, sy, 1), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ob.rotation_euler = rot
    if mat is not None:
        me.materials.append(mat)
    return _link(ob, parent)


# ── 가구 ──

def _legs(root, w, d, h, mat, r=0.018, inset=0.06):
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl("leg", r, h, mat, (sx * (w / 2 - inset), sy * (d / 2 - inset), h / 2), root, seg=12)


def chair(root, x, y, rot_z, P, seat_mat=None):
    c = empty("chair", (x, y, 0), rot_z, root)
    box("seat", 0.44, 0.44, 0.05, seat_mat or P["fabric"], (0, 0.02, 0.45), c, bevel=0.015)
    box("back", 0.44, 0.05, 0.40, seat_mat or P["fabric"], (0, -0.2, 0.69), c, bevel=0.015, rot=(-0.12, 0, 0))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl("leg", 0.012, 0.44, P["frame"], (sx * 0.19, sy * 0.18 + 0.02, 0.22), c, seg=8)
    return c


def sofa(root, w, d, h, P):
    arm = 0.17
    _legs(root, w, d, 0.1, P["accent"], 0.02, 0.1)
    box("base", w, d, 0.18, P["fabric"], (0, 0, 0.19), root, bevel=0.02)
    n = max(2, round((w - 2 * arm) / 0.75))
    cw = (w - 2 * arm) / n
    sd = d - 0.22
    for i in range(n):
        x = -w / 2 + arm + cw * (i + 0.5)
        box("cushion", cw - 0.012, sd, 0.14, P["fabric"], (x, 0.22 / 2 - 0.0, 0.35), root, bevel=0.035)
        box("backcush", cw - 0.02, 0.16, 0.36, P["fabric"], (x, -d / 2 + 0.2, 0.58), root, bevel=0.05, rot=(-0.15, 0, 0))
    box("back", w - 2 * arm + 0.02, 0.16, h - 0.28, P["fabric"], (0, -d / 2 + 0.08, 0.28 + (h - 0.28) / 2), root, bevel=0.03)
    for sx in (-1, 1):
        box("arm", arm, d, 0.36, P["fabric"], (sx * (w / 2 - arm / 2), 0, 0.28 + 0.18), root, bevel=0.04)


def armchair(root, w, d, h, P):
    sofa(root, w, d, h, P)


def bench(root, w, d, h, P, style="wood"):
    top = P["wood"] if style == "wood" else P["fabric"]
    box("top", w, d, 0.06, top, (0, 0, h - 0.03), root, bevel=0.008)
    if style != "wood":
        box("pad", w - 0.04, d - 0.04, 0.05, P["fabric"], (0, 0, h + 0.02), root, bevel=0.02)
    xs = [-w / 2 + 0.25, w / 2 - 0.25] + ([0.0] if w > 2.6 else [])
    for x in xs:
        box("frame", 0.05, d - 0.06, h - 0.06, P["accent"], (x, 0, (h - 0.06) / 2), root)


def beam_chairs(root, w, d, h, P, seats=4):
    box("beam", w, 0.06, 0.05, P["frame"], (0, -0.06, 0.36), root)
    for sx in (-1, 1):
        box("leg", 0.05, d - 0.1, 0.36, P["frame"], (sx * (w / 2 - 0.1), 0, 0.18), root)
    sw = w / seats
    for i in range(seats):
        x = -w / 2 + sw * (i + 0.5)
        box("seat", sw - 0.05, 0.46, 0.05, P["fabric"], (x, 0.04, 0.44), root, bevel=0.015)
        box("back", sw - 0.05, 0.04, 0.42, P["fabric"], (x, -d / 2 + 0.1, 0.70), root, bevel=0.015, rot=(-0.15, 0, 0))


def desk_counter(root, w, d, h, P):
    box("body", w, d - 0.04, h - 0.04, P["white"], (0, -0.02, (h - 0.04) / 2), root, bevel=0.01)
    box("front", w + 0.01, 0.03, h - 0.08, P["accent"], (0, d / 2 - 0.035, (h - 0.08) / 2 + 0.02), root, bevel=0.005)
    box("top", w + 0.04, d + 0.02, 0.04, P["wood"], (0, 0, h - 0.02), root, bevel=0.006)
    box("monitor", 0.5, 0.03, 0.3, P["bezel"], (w * 0.2, -d / 2 + 0.2, h + 0.18), root)
    box("toe", w - 0.06, d - 0.1, 0.08, P["baseboard"], (0, -0.04, 0.04), root)


def high_counter(root, w, d, h, P):
    box("top", w, d, 0.05, P["white"], (0, 0, h - 0.025), root, bevel=0.008)
    box("base", w - 0.25, d - 0.25, h - 0.05, P["accent"], (0, 0, (h - 0.05) / 2), root, bevel=0.01)
    dev = M.screen("info", 2.0)
    for i, x in enumerate((-w / 4, w / 4)):
        box(f"tablet{i}", 0.26, 0.18, 0.012, P["bezel"], (x, 0, h + 0.008), root, rot=(0.3, 0, 0))
        plane(f"tabscr{i}", 0.24, 0.16, dev, (x, 0.003, h + 0.016), rot=(0.3, 0, 0), parent=root)
    for x in (-w / 3, 0, w / 3):
        st = empty("stool", (x, d / 2 + 0.38, 0), 0, root)
        cyl("seat", 0.17, 0.05, P["fabric"], (0, 0, 0.66), st)
        cyl("pole", 0.02, 0.64, P["frame"], (0, 0, 0.32), st, seg=10)
        cyl("foot", 0.2, 0.02, P["frame"], (0, 0, 0.01), st)


def coffee_table(root, w, d, h, P):
    box("top", w, d, 0.04, P["wood"], (0, 0, h - 0.02), root, bevel=0.01)
    box("base", w * 0.6, d * 0.6, h - 0.04, P["accent"], (0, 0, (h - 0.04) / 2), root)


def table_set(root, w, d, h, P, seats=2):
    tw = 0.7 if seats <= 2 else 0.9
    box("top", tw, tw, 0.04, P["wood"], (0, 0, 0.73), root, bevel=0.008)
    cyl("pole", 0.04, 0.71, P["frame"], (0, 0, 0.355), root, seg=12)
    cyl("foot", 0.25, 0.02, P["frame"], (0, 0, 0.01), root)
    pos = [(-(tw / 2 + 0.25), 0, -math.pi / 2), ((tw / 2 + 0.25), 0, math.pi / 2)]
    if seats > 2:
        pos += [(0, tw / 2 + 0.25, 0.0), (0, -(tw / 2 + 0.25), math.pi)]
    for x, y, r in pos:
        chair(root, x, y, r + math.pi, P)


def meeting_set(root, w, d, h, P):
    tw, td = w - 0.6, d - 1.2
    box("top", tw, td, 0.05, P["wood"], (0, 0, 0.74), root, bevel=0.01)
    for sx in (-1, 1):
        box("ped", 0.12, td * 0.5, 0.72, P["accent"], (sx * tw * 0.33, 0, 0.36), root)
    n = 3
    for i in range(n):
        x = -tw / 2 + tw * (i + 0.5) / n
        chair(root, x, td / 2 + 0.3, math.pi, P)
        chair(root, x, -td / 2 - 0.3, 0.0, P)
    chair(root, -tw / 2 - 0.35, 0, -math.pi / 2, P)
    chair(root, tw / 2 + 0.35, 0, math.pi / 2, P)


def operator_desk(root, w, d, h, P):
    # 앞(+Y)이 상황판 쪽. 책상은 앞쪽, 의자는 뒤쪽.
    dd = 0.8
    y0 = d / 2 - dd / 2
    box("top", w - 0.04, dd, 0.04, P["white"], (0, y0, 0.74), root, bevel=0.006)
    for sx in (-1, 1):
        box("side", 0.04, dd - 0.06, 0.72, P["accent"], (sx * (w / 2 - 0.06), y0, 0.36), root)
    box("modesty", w - 0.16, 0.03, 0.45, P["accent"], (0, y0 + dd / 2 - 0.05, 0.47), root)
    scr = M.screen("dashboard", 1.6, seed=1.7)
    for i, x in enumerate((-0.33, 0.33)):
        tilt = -0.18 if x > 0 else 0.18  # 두 모니터를 운영자 쪽으로 살짝 모은다
        box(f"mon{i}", 0.6, 0.03, 0.36, P["bezel"], (x, y0 + 0.22, 1.03), root, rot=(0, 0, tilt))
        plane(f"monscr{i}", 0.57, 0.33, scr, (x, y0 + 0.22 - 0.017, 1.03), rot=(math.pi / 2, 0, tilt), parent=root)
        cyl(f"arm{i}", 0.015, 0.25, P["frame"], (x, y0 + 0.24, 0.86), root, seg=8)
    ch = empty("opchair", (0, -d / 2 + 0.38, 0), 0.0, root)
    box("seat", 0.5, 0.48, 0.07, P["fabric"], (0, 0.02, 0.47), ch, bevel=0.02)
    box("back", 0.48, 0.06, 0.55, P["fabric"], (0, -0.22, 0.8), ch, bevel=0.02, rot=(-0.1, 0, 0))
    cyl("gas", 0.025, 0.4, P["frame"], (0, 0, 0.24), ch, seg=10)
    cyl("base", 0.3, 0.03, P["frame"], (0, 0, 0.05), ch, seg=5)


def desk_pair(root, w, d, h, P):
    dd = min(0.6, d * 0.5)
    y0 = d / 2 - dd / 2
    box("top", w, dd, 0.03, P["wood"], (0, y0, 0.73), root, bevel=0.005)
    for sx in (-1, 1):
        box("leg", 0.04, dd - 0.06, 0.72, P["frame"], (sx * (w / 2 - 0.05), y0, 0.36), root)
    n = 2 if w >= 1.1 else 1
    for i in range(n):
        x = -w / 2 + w * (i + 0.5) / n
        chair(root, x, -d / 2 + 0.25, 0.0, P)


def plinth(root, w, d, h, P, k=0):
    box("block", w, d, h, P["white"], (0, 0, h / 2), root, bevel=0.006)
    rnd = random.Random(k)
    if rnd.random() < 0.5:
        sphere("obj", 0.12, P["accent"], (0, 0, h + 0.12), root, sub=3)
    else:
        cyl("vase", 0.08, 0.32, P["pot"], (0, 0, h + 0.16), root, r2=0.05)


def planter(root, w, d, h, P, k=0):
    rnd = random.Random(1000 + k)
    big = h > 1.2
    pr = w / 2 * 0.86
    ph = 0.48 if big else 0.36
    cyl("pot", pr, ph, P["pot"], (0, 0, ph / 2), root, r2=pr * 0.82, seg=28)
    cyl("soil", pr * 0.92, 0.02, P["soil"], (0, 0, ph - 0.03), root, seg=24)
    if big:
        cyl("trunk", 0.022, h * 0.62, P["wood"], (0, 0, ph + h * 0.31 - 0.05), root, seg=8)
        n = 9
        for i in range(n):
            a = rnd.uniform(0, 2 * math.pi)
            rr = rnd.uniform(0.05, pr * 0.9)
            z = rnd.uniform(h * 0.55, h * 0.93)
            s = rnd.uniform(0.16, 0.26)
            sphere(f"leaf{i}", s, P["leaf"], (math.cos(a) * rr, math.sin(a) * rr, z), root, sub=1,
                   scale=(1.0, rnd.uniform(0.7, 1.0), rnd.uniform(0.55, 0.8)))
    else:
        for i in range(6):
            a = rnd.uniform(0, 2 * math.pi)
            rr = rnd.uniform(0.0, pr * 0.6)
            sphere(f"leaf{i}", rnd.uniform(0.11, 0.17), P["leaf"], (math.cos(a) * rr, math.sin(a) * rr, ph + rnd.uniform(0.12, h - ph - 0.1)),
                   root, sub=1, scale=(1, 1, 0.75))


def shelf(root, w, d, h, P, k=0):
    rnd = random.Random(200 + k)
    for sx in (-1, 1):
        box("side", 0.03, d, h, P["white"], (sx * (w / 2 - 0.015), 0, h / 2), root)
    for i in range(5):
        z = 0.05 + i * (h - 0.1) / 4
        box(f"shelf{i}", w - 0.06, d, 0.025, P["white"], (0, 0, z), root)
        if i < 4:
            x = -w / 2 + 0.12
            while x < w / 2 - 0.2:
                bw = rnd.uniform(0.12, 0.3)
                bh = rnd.uniform(0.12, 0.3)
                col = M.principled(f"goods{rnd.randint(0, 5)}", (rnd.uniform(0.2, 0.9), rnd.uniform(0.2, 0.8), rnd.uniform(0.2, 0.9)), 0.5)
                box("goods", bw, d * 0.6, bh, col, (x + bw / 2, 0, z + 0.0125 + bh / 2), root)
                x += bw + rnd.uniform(0.03, 0.1)


def cabinet(root, w, d, h, P):
    box("body", w, d, h, P["white"], (0, 0, h / 2), root, bevel=0.006)
    box("top", w + 0.01, d + 0.01, 0.025, P["wood"], (0, 0, h + 0.012), root)
    n = max(1, round(w / 0.6))
    for i in range(1, n):
        x = -w / 2 + w * i / n
        box("seam", 0.004, 0.004, h - 0.06, P["baseboard"], (x, d / 2, h / 2), root)


def rug(root, w, d, h, P):
    col = tuple(min(1.0, c * 1.25 + 0.05) for c in P["fabric"].diffuse_color[:3])
    box("rug", w, d, 0.012, M.fabric(col), (0, 0, 0.006), root, bevel=0.004)


def bed(root, w, d, h, P):
    box("base", w, d - 0.1, 0.32, P["fabric"], (0, 0.05, 0.16), root, bevel=0.02)
    box("mattress", w - 0.04, d - 0.18, 0.22, P["white"], (0, 0.06, 0.43), root, bevel=0.04)
    box("duvet", w + 0.02, (d - 0.2) * 0.62, 0.06, M.fabric((0.85, 0.83, 0.8)), (0, d * 0.18, 0.56), root, bevel=0.03)
    for sx in (-1, 1):
        box("pillow", w * 0.4, 0.4, 0.14, P["white"], (sx * w * 0.22, -d / 2 + 0.38, 0.6), root, bevel=0.06)
    box("head", w + 0.12, 0.08, h, P["accent"], (0, -d / 2 + 0.04, h / 2), root, bevel=0.01)


def partition(root, w, d, h, P):
    box("panel", w, d, h, P["fabric"], (0, 0, h / 2 + 0.05), root, bevel=0.01)
    for sx in (-1, 1):
        box("foot", 0.05, 0.4, 0.05, P["frame"], (sx * (w / 2 - 0.1), 0, 0.025), root)


BUILDERS = {
    "sofa": sofa, "armchair": armchair, "bench": bench, "beam_chairs": beam_chairs, "desk_counter": desk_counter,
    "high_counter": high_counter, "coffee_table": coffee_table, "table_set": table_set, "meeting_set": meeting_set,
    "operator_desk": operator_desk, "desk_pair": desk_pair, "plinth": plinth, "planter": planter, "shelf": shelf,
    "cabinet": cabinet, "rug": rug, "bed": bed, "partition": partition,
}


def build_furniture(f: dict, P: dict, k: int = 0):
    """f: {type, builder, x,y(m), rot_z(rad), w,d,h(m), seats, style}."""
    root = empty(f"F_{f['id']}", (f["X"], f["Y"], 0.0), f["rot_z"])
    root["bid"] = f["id"]
    root["kind"] = "furniture"
    b = f["builder"]
    fn = BUILDERS.get(b, cabinet)
    w, d, h = f["w"], f["d"], f["h"]
    if b == "bench":
        fn(root, w, d, h, P, style=f.get("style", "wood"))
    elif b == "beam_chairs":
        fn(root, w, d, h, P, seats=int(f.get("seats", 4)))
    elif b == "table_set":
        fn(root, w, d, h, P, seats=int(f.get("seats", 2)))
    elif b in ("plinth", "planter", "shelf"):
        fn(root, w, d, h, P, k=k)
    else:
        fn(root, w, d, h, P)
    return root


# ── 제품 ──

def display(pr: dict, P: dict, H: float):
    """pr: {id, X, Y, rot_z, sw, sh, depth, bottom, mount, bezel, content, double, category, label, fd}."""
    root = empty(f"P_{pr['id']}", (pr["X"], pr["Y"], 0.0), pr["rot_z"])
    root["bid"] = pr["id"]
    root["kind"] = "product"
    sw, sh, dp, b = pr["sw"], pr["sh"], pr["depth"], pr["bottom"]
    fd = pr.get("fd", dp)
    zc = b + sh / 2
    cat = pr["category"]
    mount = pr["mount"]
    if cat == "hvac_cassette":
        z = H - sh / 2
        body = box("panel", sw, pr["fd"], sh, P["white"], (0, 0, z), root, bevel=0.004)
        box("grille", sw * 0.52, pr["fd"] * 0.52, 0.004, M.principled("grille", (0.6, 0.6, 0.6), 0.6), (0, 0, z - sh / 2 - 0.002), root)
        for sx, sy, ww, dd in ((0, 1, 0.62, 0.04), (0, -1, 0.62, 0.04), (1, 0, 0.04, 0.62), (-1, 0, 0.04, 0.62)):
            box("vent", sw * ww, pr["fd"] * dd, 0.004, P["bezel"], (sx * sw * 0.36, sy * pr["fd"] * 0.36, z - sh / 2 - 0.002), root)
        body["bid"] = pr["id"]
        body["part"] = "body"
        root["ceiling"] = True
        return root
    # 화면이 바닥 점유 앞쪽에 오도록(스탠드형은 깊이가 크다)
    y_body = fd / 2 - dp / 2
    bezel_mat = P["white"] if cat == "epaper" else P["bezel"]
    body = box("body", sw, dp, sh, bezel_mat, (0, y_body, zc), root, bevel=0.004)
    body["bid"] = pr["id"]
    body["part"] = "body"
    bz = pr["bezel"]
    scr_mat = M.screen(pr["content"], pr.get("strength", 4.0), seed=pr.get("seed", 0.0))
    scr = plane("screen", max(0.01, sw - 2 * bz), max(0.01, sh - 2 * bz), scr_mat, (0, y_body + dp / 2 + 0.0015, zc),
                rot=(math.pi / 2, 0, math.pi), parent=root)
    scr["bid"] = pr["id"]
    scr["part"] = "screen"
    if pr.get("double"):
        s2 = plane("screen_b", max(0.01, sw - 2 * bz), max(0.01, sh - 2 * bz), scr_mat, (0, y_body - dp / 2 - 0.0015, zc),
                   rot=(math.pi / 2, 0, 0), parent=root)
        s2["bid"] = pr["id"]
        s2["part"] = "screen"
    top = b + sh
    if mount == "ceiling_hang":
        for sx in (-1, 1):
            cyl("rod", 0.011, max(0.05, H - top), P["frame"], (sx * sw * 0.3, y_body, top + (H - top) / 2), root, seg=8)
    elif mount == "stand":
        for sx in (-1, 1):
            box("foot", 0.07, fd, 0.04, P["frame"], (sx * (sw / 2 - 0.25), 0, 0.06), root)
            box("post", 0.06, 0.06, b + sh * 0.75, P["frame"], (sx * (sw / 2 - 0.25), y_body - dp / 2 - 0.035, (b + sh * 0.75) / 2), root)
            for sy in (-1, 1):
                cyl("caster", 0.035, 0.03, P["bezel"], (sx * (sw / 2 - 0.25), sy * (fd / 2 - 0.06), 0.035), root, rot=(0, math.pi / 2, 0), seg=10)
        box("tray", sw * 0.5, 0.12, 0.03, P["frame"], (0, y_body + dp / 2 + 0.05, b - 0.05), root)
    elif mount == "floor_stand":
        box("column", min(0.3, sw * 0.4), 0.12, b, P["frame"], (0, y_body - dp / 2 - 0.06, b / 2), root)
        box("baseplate", min(0.8, sw * 0.8), max(0.45, fd), 0.03, P["frame"], (0, 0, 0.015), root)
    elif mount == "floor_lean":
        box("foot", sw * 0.9, fd * 0.8, 0.03, P["frame"], (0, 0, 0.015), root)
        box("back_leg", 0.05, 0.05, sh * 0.8, P["frame"], (0, y_body - dp / 2 - 0.05, sh * 0.4), root)
    return root


def stamp(cam_ob, text: str, font_path: str | None, res: tuple[int, int], ortho: bool):
    """카메라에 붙여 화면 왼쪽 아래에 'AI 생성 · 개략' 표시를 굽는다(카메라에만 보임)."""
    cam = cam_ob.data
    rx, ry = res
    asp = ry / rx
    if ortho:
        dz = 1.0
        half_w = cam.ortho_scale / 2
    else:
        dz = max(cam.clip_start * 3, 0.05)
        half_w = dz * (cam.sensor_width / 2) / cam.lens
    half_h = half_w * asp
    size = half_w * 2 * 0.021
    cu = bpy.data.curves.new("stamp_txt", "FONT")
    cu.body = text
    if font_path:
        try:
            cu.font = bpy.data.fonts.load(font_path, check_existing=True)
        except Exception:  # noqa: BLE001
            pass
    cu.size = size
    cu.align_x = "LEFT"
    cu.align_y = "BOTTOM"
    tob = bpy.data.objects.new("stamp_txt", cu)
    tob.data.materials.append(M.emission("stamp_ink", (1.0, 1.0, 1.0), 1.6))
    _link(tob, cam_ob)
    mx = half_w * 2 * 0.018
    tob.location = (-half_w + mx + size * 0.5, -half_h + mx + size * 0.45, -dz)
    bpy.context.view_layer.update()
    tw = tob.dimensions.x if tob.dimensions.x > 0 else size * 0.75 * len(text)
    bw, bh = tw + size * 1.0, size * 1.75
    bg = plane("stamp_bg", bw, bh, M.stamp_bg(), (-half_w + mx + bw / 2, -half_h + mx + bh / 2, -dz - 1e-4), parent=cam_ob)
    for ob in (tob, bg):
        for attr in ("visible_shadow", "visible_diffuse", "visible_glossy", "visible_transmission", "visible_volume_scatter"):
            if hasattr(ob, attr):
                setattr(ob, attr, False)
    return tob, bg
