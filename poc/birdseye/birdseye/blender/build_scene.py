"""Blender 씬 생성 · 렌더 · 품질 확인 — 3D 조감도 파이프라인의 ③~⑥ 단계.

실행(둘 중 하나):
  blender -b --factory-startup -P build_scene.py -- scene.json out_dir
  python build_scene.py scene.json out_dir            # bpy 모듈(pip install bpy)이 있는 파이썬

진행 상황은 표준 출력에 '@@BIRDSEYE {json}' 줄로 알린다.
좌표: 도면(mm, x 오른쪽, y 아래=안쪽) → Blender(m) X = x/1000, Y = −y/1000, Z 위.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import assets as A  # noqa: E402
import materials as M  # noqa: E402

T0 = time.time()


def emit(kind, **kw):
    kw["kind"] = kind
    kw["t"] = round(time.time() - T0, 2)
    print("@@BIRDSEYE " + json.dumps(kw, ensure_ascii=False), flush=True)


def mm(v):
    return v / 1000.0


def XY(x, y):
    return (x / 1000.0, -y / 1000.0)


def coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def tag(ob, group):
    ob["cut"] = group
    for ch in ob.children_recursive:
        ch["cut"] = group


# ── 렌더 설정 ──

def setup_render(spec):
    sc = bpy.context.scene
    r = spec["render"]
    eng = r.get("engine", "CYCLES").upper()
    if eng.startswith("EEVEE"):
        for name in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                sc.render.engine = name
                break
            except TypeError:
                continue
    else:
        sc.render.engine = "CYCLES"
    device_used = "CPU"
    if sc.render.engine == "CYCLES":
        cy = sc.cycles
        cy.samples = int(r.get("samples", 64))
        cy.use_denoising = True
        try:
            cy.denoiser = "OPENIMAGEDENOISE"
        except TypeError:
            pass
        cy.max_bounces = 6
        cy.diffuse_bounces = 3
        cy.glossy_bounces = 3
        cy.transmission_bounces = 6
        cy.caustics_reflective = False
        cy.caustics_refractive = False
        cy.use_adaptive_sampling = True
        cy.adaptive_threshold = 0.03
        want = (r.get("device") or "auto").lower()
        if want in ("auto", "gpu"):
            try:
                prefs = bpy.context.preferences.addons["cycles"].preferences
                for kind in ("METAL", "OPTIX", "CUDA", "HIP", "ONEAPI"):
                    try:
                        prefs.compute_device_type = kind
                    except TypeError:
                        continue
                    try:
                        prefs.get_devices()
                    except Exception:  # noqa: BLE001
                        pass
                    devs = [d for d in prefs.devices if d.type == kind]
                    if devs:
                        for d in prefs.devices:
                            d.use = d.type == kind
                        cy.device = "GPU"
                        device_used = f"GPU ({kind})"
                        break
            except Exception:  # noqa: BLE001
                pass
        thr = int(r.get("threads") or 0)
        if thr > 0:
            sc.render.threads_mode = "FIXED"
            sc.render.threads = thr
    sc.render.resolution_x, sc.render.resolution_y = r["res"]
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.film_transparent = False
    try:
        sc.view_settings.view_transform = "AgX"
    except TypeError:
        sc.view_settings.view_transform = "Filmic"
    sc.view_settings.exposure = 0.0
    return device_used


# ── 방 ──

def build_room(spec, P):
    room = spec["room"]
    W, D, H = room["width"], room["depth"], room["height"]
    t = room.get("wall_t", 200)
    A.COLL = coll("room")
    # 바닥(방 안) + 바깥 바닥
    fl = A.box("floor", mm(W), mm(D), 0.05, P["floor"], (mm(W) / 2, -mm(D) / 2, -0.025))
    tag(fl, "floor")
    g = A.box("ground", mm(W) + 60, mm(D) + 60, 0.02, P["ground"], (mm(W) / 2, -mm(D) / 2, -0.06))
    tag(g, "ground")
    walk = A.box("sidewalk", mm(W) + 8, 4.0, 0.03, M.concrete("sidewalk", (0.48, 0.47, 0.45), (0.56, 0.55, 0.53), 0.8),
                 (mm(W) / 2, 2.0 + mm(t), -0.035))
    tag(walk, "ground")

    def wall_seg(wall, a, b, z0, z1, mat, name="wall"):
        if b - a < 1 or z1 - z0 < 1:
            return None
        L = b - a
        if wall == "front":
            ob = A.box(name, mm(L), mm(t), mm(z1 - z0), mat, (mm(a + L / 2), mm(t) / 2, mm((z0 + z1) / 2)))
        elif wall == "back":
            ob = A.box(name, mm(L), mm(t), mm(z1 - z0), mat, (mm(a + L / 2), -mm(D) - mm(t) / 2, mm((z0 + z1) / 2)))
        elif wall == "left":
            ob = A.box(name, mm(t), mm(L), mm(z1 - z0), mat, (-mm(t) / 2, -mm(a + L / 2), mm((z0 + z1) / 2)))
        else:
            ob = A.box(name, mm(t), mm(L), mm(z1 - z0), mat, (mm(W) + mm(t) / 2, -mm(a + L / 2), mm((z0 + z1) / 2)))
        tag(ob, f"wall_{wall}")
        return ob

    def pane(wall, a, b, z0, z1, mat, thick=20, name="glass", inset=0.5):
        L = b - a
        off = mm(t) * inset
        if wall == "front":
            ob = A.box(name, mm(L), mm(thick), mm(z1 - z0), mat, (mm(a + L / 2), off, mm((z0 + z1) / 2)))
        elif wall == "back":
            ob = A.box(name, mm(L), mm(thick), mm(z1 - z0), mat, (mm(a + L / 2), -mm(D) - off, mm((z0 + z1) / 2)))
        elif wall == "left":
            ob = A.box(name, mm(thick), mm(L), mm(z1 - z0), mat, (-off, -mm(a + L / 2), mm((z0 + z1) / 2)))
        else:
            ob = A.box(name, mm(thick), mm(L), mm(z1 - z0), mat, (mm(W) + off, -mm(a + L / 2), mm((z0 + z1) / 2)))
        tag(ob, f"wall_{wall}")
        return ob

    for wall in ("front", "back", "left", "right"):
        L = W if wall in ("front", "back") else D
        ops = sorted([o for o in room["openings"] if o["wall"] == wall], key=lambda o: o["start"])
        cur = -t
        for o in ops:
            wall_seg(wall, cur, o["start"], 0, H, P["wall"])
            a, b = o["start"], o["start"] + o["length"]
            sill = o.get("sill", 0 if o["kind"] != "window" else 900)
            head = min(H, o.get("head", 2400 if o["kind"] != "window" else 2400))
            wall_seg(wall, a, b, head, H, P["wall"], "lintel")
            if sill > 0:
                wall_seg(wall, a, b, 0, sill, P["wall"], "sill")
            if o["kind"] == "window":
                pane(wall, a, b, sill, head, P["glass"])
                n = max(1, round((b - a) / 1800))
                for i in range(n + 1):
                    mx = a + (b - a) * i / n
                    pane(wall, mx - 25, mx + 25, sill, head, P["frame"], thick=60, name="mullion")
                pane(wall, a, b, head - 40, head, P["frame"], thick=60, name="transom")
                if sill > 0:
                    pane(wall, a, b, sill, sill + 40, P["frame"], thick=60, name="sillframe")
            elif o["kind"] == "entrance":
                mid = (a + b) / 2
                for aa, bb in ((a, mid - 10), (mid + 10, b)):
                    pane(wall, aa, bb, 0, head, P["glass"], name="door_glass")
                for mx in (a, mid, b):
                    pane(wall, mx - 25, mx + 25, 0, head, P["frame"], thick=60, name="door_frame")
                pane(wall, a, b, head - 50, head, P["frame"], thick=60, name="door_head")
            else:  # 문
                leaf = P["accent"] if o.get("door_type") != "emergency" else M.paint((0.35, 0.36, 0.38), 0.5)
                pane(wall, a + 20, b - 20, 0, head - 20, leaf, thick=45, name="door_leaf", inset=0.3)
            cur = b
        wall_seg(wall, cur, L + t, 0, H, P["wall"])
        # 걸레받이
        for o_a, o_b in _solid_spans(ops, L):
            if wall == "front":
                ob = A.box("base", mm(o_b - o_a), 0.012, 0.08, P["baseboard"], (mm(o_a + (o_b - o_a) / 2), -0.006, 0.04))
            elif wall == "back":
                ob = A.box("base", mm(o_b - o_a), 0.012, 0.08, P["baseboard"], (mm(o_a + (o_b - o_a) / 2), -mm(D) + 0.006, 0.04))
            elif wall == "left":
                ob = A.box("base", 0.012, mm(o_b - o_a), 0.08, P["baseboard"], (0.006, -mm(o_a + (o_b - o_a) / 2), 0.04))
            else:
                ob = A.box("base", 0.012, mm(o_b - o_a), 0.08, P["baseboard"], (mm(W) - 0.006, -mm(o_a + (o_b - o_a) / 2), 0.04))
            tag(ob, f"wall_{wall}")
    for p in room.get("pillars", []):
        x, y = XY(p["x"], p["y"])
        ob = A.box(f"pillar_{p['id']}", mm(p["w"]), mm(p["d"]), mm(H), P["pillar"], (x, y, mm(H) / 2), bevel=0.004)
        tag(ob, "pillar")
    # 천장 + 라인 조명(보이는 발광 띠)
    A.COLL = coll("ceiling")
    c = A.box("ceiling", mm(W) + 2 * mm(t), mm(D) + 2 * mm(t), 0.06, P["ceiling"], (mm(W) / 2, -mm(D) / 2, mm(H) + 0.03))
    tag(c, "ceiling")
    return W, D, H


def _solid_spans(ops, L):
    spans, cur = [], 0.0
    for o in ops:
        if o["start"] > cur:
            spans.append((cur, o["start"]))
        cur = o["start"] + o["length"]
    if cur < L:
        spans.append((cur, L))
    return spans


# ── 조명 ──

def light_grid(W, D, H, k, spec):
    """천장 라인 조명: 보이는 발광 띠(천장 컷용) + 실제 면광원(카메라에는 안 보임)."""
    A.COLL = coll("ceiling_lights")
    pitch = 3000.0
    nx = max(1, round(W / pitch))
    ny = max(1, round(D / pitch))
    lamps = []
    strip = M.blackbody_emission("strip", k, 6.0)
    for i in range(nx):
        for j in range(ny):
            x = (i + 0.5) * W / nx
            y = (j + 0.5) * D / ny
            X, Y = XY(x, y)
            s = A.box("linelight", 1.6, 0.06, 0.02, strip, (X, Y, mm(H) - 0.012))
            s["cut"] = "ceiling"
            ld = bpy.data.lights.new("area", "AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = 1.8, 0.4
            try:
                ld.use_temperature = True
                ld.temperature = k
            except AttributeError:
                ld.color = _kelvin_rgb(k)
            ob = bpy.data.objects.new("area", ld)
            ob.location = (X, Y, mm(H) - 0.05)
            coll("lights").objects.link(ob)
            if hasattr(ob, "visible_camera"):
                ob.visible_camera = False
            lamps.append(ob)
    return lamps


def _kelvin_rgb(k):
    t = k / 100.0
    r = 1.0 if t <= 66 else min(1.0, 1.292936186 * ((t - 60) ** -0.1332047592))
    g = (0.39008157 * math.log(t) - 0.63184144) if t <= 66 else 1.129890861 * ((t - 60) ** -0.0755148492)
    b = 1.0 if t >= 66 else (0.0 if t <= 19 else 0.543206789 * math.log(t - 10) - 1.19625408)
    return (max(0, min(1, r)), max(0, min(1, g)), max(0, min(1, b)))


def setup_world(preset):
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("World")
    sc.world = w
    try:
        w.use_nodes = True
    except Exception:  # noqa: BLE001
        pass
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    col, st = {"day": ((0.62, 0.72, 0.88), 0.42), "evening": ((0.50, 0.36, 0.40), 0.16),
               "night": ((0.010, 0.014, 0.032), 1.0)}[preset]
    bg.inputs["Color"].default_value = (*col, 1)
    bg.inputs["Strength"].default_value = st
    nt.links.new(bg.outputs[0], out.inputs[0])


def setup_sun(preset, W, D):
    sun = bpy.data.objects.get("sun")
    if not sun:
        ld = bpy.data.lights.new("sun", "SUN")
        sun = bpy.data.objects.new("sun", ld)
        coll("lights").objects.link(sun)
    ld = sun.data
    if preset == "night":
        ld.energy = 0.0
        return sun
    # 도로(정면, +Y) 쪽 왼쪽 위에서 비춘다
    elev = math.radians(38 if preset == "day" else 6)
    az = math.radians(-35)
    d = Vector((math.sin(az) * math.cos(elev), math.cos(az) * math.cos(elev), math.sin(elev)))
    sun.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
    ld.energy = 2.4 if preset == "day" else 1.6
    ld.angle = math.radians(1.2)
    ld.color = (1.0, 0.97, 0.92) if preset == "day" else (1.0, 0.55, 0.30)
    return sun


LIGHT_GAIN = {"day": 1.0, "evening": 1.7, "night": 1.8}
SCREEN_GAIN = {"day": 1.0, "evening": 1.05, "night": 1.15}


EXPOSURE = {"day": -0.55, "evening": -0.4, "night": -0.3}


def apply_lighting(preset, lamps, base_w, W, D, light_k=3000, interior=False):
    setup_world(preset)
    setup_sun(preset, W, D)
    for ob in lamps:
        ob.data.energy = base_w * LIGHT_GAIN[preset]
    vs = bpy.context.scene.view_settings
    vs.exposure = EXPOSURE[preset] + (-0.15 if interior else 0.0)
    # 화이트 밸런스 — 따뜻한 조명이 화면 전체를 주황으로 물들이지 않게(분위기는 조금 남김).
    # 천장을 걷어낸 조감 컷은 하늘빛이, 실내 컷은 천장 조명이 주광원이다.
    if hasattr(vs, "use_white_balance"):
        vs.use_white_balance = True
        if interior:
            wb = light_k + {"day": 1500, "evening": 900, "night": 700}[preset]  # 바닥 반사로 번지는 주황기를 조금 더 덜어냄
        else:
            wb = {"day": 5600, "evening": 4500}.get(preset, light_k + 800)
        vs.white_balance_temperature = max(3200, min(7000, wb))


# ── 카메라 ──

def _look(cam_ob, target):
    d = Vector(target) - cam_ob.location
    cam_ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def _fits(cam_ob, pts, margin=0.05):
    sc = bpy.context.scene
    bpy.context.view_layer.update()
    for p in pts:
        v = world_to_camera_view(sc, cam_ob, Vector(p))
        if v.z <= 0 or v.x < margin or v.x > 1 - margin or v.y < margin or v.y > 1 - margin:
            return False
    return True


def setup_camera(preset, W, D, H, spec):
    sc = bpy.context.scene
    cam_ob = bpy.data.objects.get("cam")
    if cam_ob:
        for ch in list(cam_ob.children):
            bpy.data.objects.remove(ch, do_unlink=True)
    else:
        cd = bpy.data.cameras.new("cam")
        cam_ob = bpy.data.objects.new("cam", cd)
        sc.collection.objects.link(cam_ob)
    sc.camera = cam_ob
    cam = cam_ob.data
    cam.type = "PERSP"
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = 36
    cam.clip_start = 0.05
    cam.clip_end = 500
    Wm, Dm, Hm = mm(W), mm(D), mm(H)
    t = mm(spec["room"].get("wall_t", 200))
    corners = [(x, y, z) for x in (-t, Wm + t) for y in (t, -Dm - t) for z in (0, Hm)]
    center = (Wm / 2, -Dm / 2, 0.0)
    hidden = set()
    if preset == "top":
        cam.type = "ORTHO"
        rx, ry = sc.render.resolution_x, sc.render.resolution_y
        cam.ortho_scale = max(Wm + 2 * t, (Dm + 2 * t) * rx / ry) * 1.06
        cam_ob.location = (Wm / 2, -Dm / 2, Hm + 20)
        cam_ob.rotation_euler = (0, 0, 0)
        hidden = {"ceiling"}
    elif preset == "aerial45":
        cam.lens = 30
        e = spec.get("entrance") or {}
        # 입구 쪽(보통 정면=도로측)에서 오른쪽 위로 비스듬히
        dirs = {"front": Vector((0.42, 0.95, 1.05)), "back": Vector((-0.42, -0.95, 1.05)),
                "left": Vector((-0.95, -0.42, 1.05)), "right": Vector((0.95, 0.42, 1.05))}
        dv = dirs.get(e.get("wall", "front"), dirs["front"]).normalized()
        tgt = Vector((Wm / 2, -Dm / 2, Hm * 0.12))
        lo, hi = 2.0, 400.0
        for _ in range(28):
            mid = (lo + hi) / 2
            cam_ob.location = tgt + dv * mid
            _look(cam_ob, tgt)
            if _fits(cam_ob, corners, 0.025):
                hi = mid
            else:
                lo = mid
        cam_ob.location = tgt + dv * hi
        _look(cam_ob, tgt)
        near = {"front": "wall_front", "back": "wall_back", "left": "wall_left", "right": "wall_right"}
        hidden = {"ceiling", near[e.get("wall", "front")]}
        side = "wall_right" if dv.x > 0 else "wall_left"
        if e.get("wall") in ("left", "right"):
            side = "wall_back" if dv.y < 0 else "wall_front"
        hidden.add(side)
    elif preset in ("entrance", "eye"):
        cam.lens = 18 if preset == "entrance" else 16
        e = spec.get("entrance") or {"wall": "front", "x": W / 2, "y": 0}
        if preset == "entrance":
            ex, ey = e["x"], e["y"]
            inward = {"front": (0, 1), "back": (0, -1), "left": (1, 0), "right": (-1, 0)}[e["wall"]]
            px, py = ex + inward[0] * 700, ey + inward[1] * 700
            X, Y = XY(px, py)
            cam_ob.location = (X, Y, 1.55)
            tx, ty = XY(px + inward[0] * 10000, py + inward[1] * 10000)
            _look(cam_ob, (tx, ty, 1.15))
        else:
            X, Y = XY(900, 900)
            cam_ob.location = (X, Y, 1.6)
            tx, ty = XY(W * 0.62, D * 0.7)
            _look(cam_ob, (tx, ty, 1.0))
        hidden = set()
    return cam_ob, hidden


def set_cutaway(hidden):
    for ob in bpy.data.objects:
        g = ob.get("cut")
        if g is None:
            continue
        if g == "ceiling" or g == "ceiling_item":
            ob.hide_render = "ceiling" in hidden
            continue
        if hasattr(ob, "visible_camera"):
            ob.visible_camera = g not in hidden


def set_variant(variant):
    for ob in bpy.data.objects:
        k = ob.get("kind")
        if k in ("product", "furniture"):
            hide = variant == "before"
            ob.hide_render = hide
            for ch in ob.children_recursive:
                ch.hide_render = hide


# ── 품질 확인 ──

def _bvh(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    obe = ob.evaluated_get(dg)
    me = obe.to_mesh()
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    obe.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys) if polys else None


def geometry_qc(spec):
    """제품 치수가 스펙(KB)과 같은지, 가구·제품이 서로 파고들지 않는지."""
    bpy.context.view_layer.update()
    out = {"product_dims": [], "overlaps": []}
    specs = {p["id"]: p for p in spec["products"]}
    for ob in bpy.data.objects:
        if ob.get("part") == "body" and ob.get("bid") in specs:
            p = specs[ob["bid"]]
            dims = ob.dimensions
            if p["category"] == "hvac_cassette":
                want = (mm(p["sw"]), mm(p["fd"]), mm(p["sh"]))
            else:
                want = (mm(p["sw"]), mm(p["depth"]), mm(p["sh"]))
            err = max(abs(a - b) for a, b in zip(dims, want)) * 1000
            out["product_dims"].append({"id": p["id"], "label": p.get("label"), "err_mm": round(err, 2)})
    roots = [ob for ob in bpy.data.objects if ob.get("kind") in ("product", "furniture") and not ob.get("ceiling")]
    trees = {}
    for r in roots:
        parts = [r] + [c for c in r.children_recursive if c.type == "MESH"]
        ts = [t for t in (_bvh(c) for c in parts if c.type == "MESH") if t]
        trees[r.name] = (r, ts)
    names = list(trees)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            ra, ta = trees[names[i]]
            rb, tb = trees[names[j]]
            if (ra.location - rb.location).length > 6:
                continue
            hit = any(a.overlap(b) for a in ta for b in tb)
            if hit:
                out["overlaps"].append([ra.get("bid"), rb.get("bid")])
    return out


def _cam_visible(ob) -> bool:
    if ob is None:
        return False
    cur = ob
    while cur is not None:
        if cur.hide_render or (hasattr(cur, "visible_camera") and not cur.visible_camera):
            return False
        cur = cur.parent
    return True


def ray_visible(sc, dg, origin, direction, distance):
    """카메라에 보이는 물체만 맞히는 광선 — 잘라 낸 벽 · 천장(렌더에서 숨김)은 통과한다."""
    o = origin.copy()
    remaining = distance
    for _ in range(24):
        hit, loc, nrm, idx, hob, mat = sc.ray_cast(dg, o, direction, distance=remaining)
        if not hit:
            return False, None, None
        if _cam_visible(hob):
            return True, loc, hob
        step = (loc - o).length + 2e-3
        o = loc + direction * 2e-3
        remaining -= step
        if remaining <= 0:
            return False, None, None
    return False, None, None


def project_points(cam_ob, zones, preset):
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    res = []
    z = 0.05 if preset in ("aerial45", "top") else 0.9
    for zz in zones:
        X, Y = XY(zz["x"], zz["y"])
        p = Vector((X, Y, z))
        v = world_to_camera_view(sc, cam_ob, p)
        inside = 0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0
        vis = False
        if inside:
            o = cam_ob.matrix_world.translation
            d = (p - o)
            dist = d.length
            hit, loc, _ = ray_visible(sc, dg, o, d.normalized(), dist - 0.05)
            vis = not hit
        res.append({"no": zz["no"], "name": zz.get("name", ""), "u": round(v.x, 4), "v": round(1 - v.y, 4),
                    "in_frame": inside, "visible": vis})
    return res


def product_visibility(cam_ob, spec):
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    o = cam_ob.matrix_world.translation
    screens = [ob for ob in bpy.data.objects if ob.get("part") == "screen" and not ob.hide_render]
    by = {}
    for s in screens:
        by.setdefault(s["bid"], []).append(s)
    for p in spec["products"]:
        ss = by.get(p["id"])
        if not ss:
            continue
        s = ss[0]
        hx, hy = s.dimensions.x / 2 * 0.8, s.dimensions.y / 2 * 0.8
        samples = [(0, 0), (hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]
        seen = 0
        inside = 0
        for sx, sy in samples:
            wp = s.matrix_world @ Vector((sx / max(s.scale.x, 1e-6), sy / max(s.scale.y, 1e-6), 0))
            v = world_to_camera_view(sc, cam_ob, wp)
            if not (0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0):
                continue
            inside += 1
            d = wp - o
            hit, loc, hob = ray_visible(sc, dg, o, d.normalized(), d.length + 0.01)
            if hit and (hob.get("bid") == p["id"] or (loc - wp).length < 0.03):
                seen += 1
        out.append({"id": p["id"], "label": p.get("label"), "in_frame": inside / len(samples), "visible": seen / len(samples)})
    return out


# ── 렌더 ──

_progress = {"cut": None, "last": 0}


def _stats_handler(scene, *args):
    s = args[0] if args else ""
    if not isinstance(s, str):
        return
    import re
    m = re.search(r"Sample (\d+)/(\d+)", s)
    if m and _progress["cut"]:
        a, b = int(m.group(1)), int(m.group(2))
        pct = round(100 * a / max(1, b))
        if pct - _progress["last"] >= 10 or a == b:
            _progress["last"] = pct
            emit("render", cut=_progress["cut"], pct=pct)


def render_to(path, cut_id):
    _progress["cut"] = cut_id
    _progress["last"] = 0
    sc = bpy.context.scene
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return round(time.time() - t, 2)


def main(spec_path, out_dir):
    spec = json.load(open(spec_path, encoding="utf-8"))
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    emit("stage", step=3, status="run", msg="Blender 씬 준비")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        bpy.app.handlers.render_stats.append(_stats_handler)
    except Exception:  # noqa: BLE001
        pass
    device = setup_render(spec)
    lib = spec["materials_lib"]
    P = M.build_palette(lib, spec["palette"])
    W, D, H = build_room(spec, P)
    emit("stage", step=3, status="done", msg=f"공간 모델링 — 벽·바닥·창·기둥 {len(spec['room'].get('pillars', []))}개", device=device)

    emit("stage", step=4, status="run", msg="가구 · 제품 배치")
    A.COLL = coll("furniture")
    for k, f in enumerate(spec["furniture"]):
        X, Y = XY(f["x"], f["y"])
        ff = dict(f, X=X, Y=Y, rot_z=-math.radians(f.get("rot", 0)), w=mm(f["w"]), d=mm(f["d"]), h=mm(f["h"]))
        A.build_furniture(ff, P, k)
    A.COLL = coll("products")
    for k, p in enumerate(spec["products"]):
        X, Y = XY(p["x"], p["y"])
        pp = dict(p, X=X, Y=Y, rot_z=-math.radians(p.get("rot", 0)), sw=mm(p["sw"]), sh=mm(p["sh"]), depth=mm(p["depth"]),
                  fd=mm(p.get("fd", p["depth"])), bottom=mm(p.get("bottom", 0)), bezel=mm(p.get("bezel", 12)), seed=k * 0.37)
        root = A.display(pp, P, mm(H))
        if p["category"] == "hvac_cassette":
            for ob in [root] + list(root.children_recursive):
                ob["cut"] = "ceiling_item"
    qc = geometry_qc(spec)
    emit("stage", step=4, status="done", msg=f"가구 {len(spec['furniture'])}개 · 제품 {len(spec['products'])}대 · 겹침 {len(qc['overlaps'])}")

    k = spec["palette"].get("light_k", 3000)
    lamps = light_grid(W, D, H, k, spec)
    base_w = spec["render"].get("lamp_w", 70.0)
    cuts_out = []
    total = len(spec["cuts"])
    emit("stage", step=5, status="run", msg="재질 · 조명 · 렌더링")
    pv = spec["render"].get("preview")
    for i, cut in enumerate(spec["cuts"]):
        cam_ob, hidden = setup_camera(cut["camera"], W, D, H, spec)
        set_cutaway(hidden)
        set_variant(cut.get("variant", "after"))
        apply_lighting(cut.get("lighting", "day"), lamps, base_w, W, D, k, interior=cut["camera"] in ("entrance", "eye"))
        bpy.context.view_layer.update()
        stamp_text = spec.get("stamp", {}).get("text", "AI 생성 · 개략")
        if pv and i == 0:
            sc = bpy.context.scene
            rx, ry = sc.render.resolution_x, sc.render.resolution_y
            s0 = sc.cycles.samples if sc.render.engine == "CYCLES" else None
            sc.render.resolution_x, sc.render.resolution_y = pv["res"]
            if s0:
                sc.cycles.samples = pv.get("samples", 8)
            ev = sc.view_settings.exposure
            sc.view_settings.exposure = ev - 0.9
            bpy.context.view_layer.material_override = M.clay()
            pth = os.path.join(out_dir, "preview_clay.png")
            render_to(pth, "preview")
            bpy.context.view_layer.material_override = None
            sc.view_settings.exposure = ev
            emit("preview", file="preview_clay.png")
            sc.render.resolution_x, sc.render.resolution_y = rx, ry
            if s0:
                sc.cycles.samples = s0
            for ch in list(cam_ob.children):
                bpy.data.objects.remove(ch, do_unlink=True)
        A.COLL = None
        sc = bpy.context.scene
        A.stamp(cam_ob, stamp_text, spec.get("stamp", {}).get("font"), (sc.render.resolution_x, sc.render.resolution_y),
                cam_ob.data.type == "ORTHO")
        emit("cut_start", cut=cut["id"], index=i, total=total)
        path = os.path.join(out_dir, cut["file"])
        secs = render_to(path, cut["id"])
        zones = project_points(cam_ob, spec.get("zones", []), cut["camera"])
        vis = product_visibility(cam_ob, spec) if cut.get("variant", "after") == "after" else []
        cuts_out.append({"id": cut["id"], "file": cut["file"], "camera": cut["camera"], "lighting": cut.get("lighting", "day"),
                         "variant": cut.get("variant", "after"), "seconds": secs, "zones": zones, "visibility": vis,
                         "res": [sc.render.resolution_x, sc.render.resolution_y]})
        emit("cut_done", cut=cut["id"], file=cut["file"], index=i, total=total, seconds=secs)
    emit("stage", step=5, status="done", msg=f"{total}컷 렌더 완료")
    emit("stage", step=6, status="run", msg="품질 확인")
    manifest = {"blender": bpy.app.version_string, "engine": bpy.context.scene.render.engine, "device": device,
                "samples": spec["render"].get("samples"), "res": spec["render"]["res"], "cuts": cuts_out, "qc": qc,
                "seconds": round(time.time() - T0, 1)}
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    emit("done", manifest="manifest.json")


if __name__ == "__main__":
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
    try:
        main(args[0], args[1])
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        emit("error", msg=f"{type(e).__name__}: {e}")
        sys.exit(1)
