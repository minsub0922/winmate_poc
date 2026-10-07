"""Blender 재질 라이브러리 — 텍스처 파일 없이 노드로만 만든다(사내망·오프라인에서 그대로 동작)."""
from __future__ import annotations

import bpy

_CACHE: dict[str, bpy.types.Material] = {}


def _s(sockets, *names):
    """버전마다 다른 소켓 이름(Fac ↔ Factor 등)을 흡수한다."""
    for n in names:
        if n in sockets:
            return sockets[n]
    raise KeyError(names)


def FAC_OUT(node):
    return _s(node.outputs, "Factor", "Fac")


def FAC_IN(node):
    return _s(node.inputs, "Factor", "Fac")



def _new(name: str):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:  # noqa: BLE001 — 6.0 이후 항상 노드
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (600, 0)
    return m, nt, out


def _bsdf(nt, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0):
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return b


def _link(nt, a, b):
    nt.links.new(a, b)


def _coord(nt, scale=(1, 1, 1), rot=(0, 0, 0), kind="Object"):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    mp.inputs["Rotation"].default_value = rot
    _link(nt, tc.outputs[kind], mp.inputs["Vector"])
    return mp.outputs["Vector"]


def cached(key, fn):
    if key not in _CACHE or _CACHE[key].name not in bpy.data.materials:
        _CACHE[key] = fn()
    return _CACHE[key]


def principled(name, color, rough=0.5, metal=0.0, sheen=0.0, coat=0.0, sss=0.0, spec=0.5):
    def make():
        m, nt, out = _new(name)
        b = _bsdf(nt, color, rough, metal)
        b.inputs["Sheen Weight"].default_value = sheen
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Specular IOR Level"].default_value = spec
        _link(nt, b.outputs[0], out.inputs["Surface"])
        m.diffuse_color = (*color, 1.0)
        return m
    return cached(f"p:{name}:{color}:{rough}:{metal}:{sheen}", make)


def paint(color, rough=0.88):
    return principled(f"paint_{color}", tuple(color), rough)


def metal(color, rough=0.35):
    return principled(f"metal_{color}", tuple(color), rough, metal=1.0)


def fabric(color):
    return principled(f"fabric_{color}", tuple(color), 0.92, sheen=0.6)


def leather(color):
    return principled(f"leather_{color}", tuple(color), 0.42, coat=0.15)


def plastic_dark():
    return principled("bezel", (0.012, 0.012, 0.014), 0.35, spec=0.6)


def white_plastic():
    return principled("white_plastic", (0.82, 0.82, 0.8), 0.45)


def wood_planks(name, base, base2, rough=0.42, plank=(0.19, 1.4), vertical=False):
    def make():
        m, nt, out = _new(name)
        b = _bsdf(nt, base, rough)
        pw, pl = plank
        vec = _coord(nt, scale=(1.0 / pl, 1.0 / pw, 1.0) if not vertical else (1.0 / pw, 1.0 / pl, 1.0),
                     rot=(0, 0, 0) if not vertical else (1.5708, 0, 0))
        br = nt.nodes.new("ShaderNodeTexBrick")
        br.offset = 0.5
        br.squash = 1.0
        br.inputs["Color1"].default_value = (*base, 1)
        br.inputs["Color2"].default_value = (*base2, 1)
        br.inputs["Mortar"].default_value = (base[0] * 0.45, base[1] * 0.45, base[2] * 0.45, 1)
        br.inputs["Scale"].default_value = 1.0
        br.inputs["Mortar Size"].default_value = 0.004
        br.inputs["Bias"].default_value = 0.0
        br.inputs["Brick Width"].default_value = 1.0
        br.inputs["Row Height"].default_value = 1.0
        _link(nt, vec, br.inputs["Vector"])
        # 나뭇결
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X" if not vertical else "Y"
        wave.inputs["Scale"].default_value = 18.0
        wave.inputs["Distortion"].default_value = 6.0
        wave.inputs["Detail"].default_value = 3.0
        _link(nt, vec, wave.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 0.18
        _link(nt, br.outputs["Color"], mix.inputs[6])
        _link(nt, wave.outputs["Color"], mix.inputs[7])
        _link(nt, mix.outputs[2], b.inputs["Base Color"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.25
        bump.inputs["Distance"].default_value = 0.002
        _link(nt, FAC_OUT(br), bump.inputs["Height"])
        _link(nt, bump.outputs["Normal"], b.inputs["Normal"])
        _link(nt, b.outputs[0], out.inputs["Surface"])
        m.diffuse_color = (*base, 1)
        return m
    return cached(f"wood:{name}:{base}:{vertical}", make)


def concrete(name, base, base2, rough=0.35):
    def make():
        m, nt, out = _new(name)
        b = _bsdf(nt, base, rough)
        vec = _coord(nt, scale=(1, 1, 1))
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 2.5
        n.inputs["Detail"].default_value = 10.0
        n.inputs["Roughness"].default_value = 0.6
        _link(nt, vec, n.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*base, 1)
        ramp.color_ramp.elements[1].color = (*base2, 1)
        _link(nt, FAC_OUT(n), FAC_IN(ramp))
        _link(nt, ramp.outputs["Color"], b.inputs["Base Color"])
        r2 = nt.nodes.new("ShaderNodeMapRange")
        r2.inputs["To Min"].default_value = rough * 0.8
        r2.inputs["To Max"].default_value = min(1.0, rough * 1.4)
        _link(nt, FAC_OUT(n), r2.inputs["Value"])
        _link(nt, r2.outputs["Result"], b.inputs["Roughness"])
        _link(nt, b.outputs[0], out.inputs["Surface"])
        m.diffuse_color = (*base, 1)
        return m
    return cached(f"conc:{name}:{base}", make)


def terrazzo(name, base, chip, rough=0.28):
    def make():
        m, nt, out = _new(name)
        b = _bsdf(nt, base, rough)
        vec = _coord(nt, scale=(1, 1, 1))
        v = nt.nodes.new("ShaderNodeTexVoronoi")
        v.inputs["Scale"].default_value = 26.0
        _link(nt, vec, v.inputs["Vector"])
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 60.0
        _link(nt, vec, n.inputs["Vector"])
        mask = nt.nodes.new("ShaderNodeMath")
        mask.operation = "GREATER_THAN"
        mask.inputs[1].default_value = 0.62
        _link(nt, FAC_OUT(n), mask.inputs[0])
        cmix = nt.nodes.new("ShaderNodeMix")
        cmix.data_type = "RGBA"
        cmix.inputs[6].default_value = (*chip, 1)
        _link(nt, v.outputs["Color"], cmix.inputs[7])
        cmix.inputs["Factor"].default_value = 0.35
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[6].default_value = (*base, 1)
        _link(nt, cmix.outputs[2], mix.inputs[7])
        _link(nt, mask.outputs[0], mix.inputs["Factor"])
        _link(nt, mix.outputs[2], b.inputs["Base Color"])
        _link(nt, b.outputs[0], out.inputs["Surface"])
        m.diffuse_color = (*base, 1)
        return m
    return cached(f"terr:{name}:{base}", make)


def carpet(name, base, base2, tile=0.5):
    def make():
        m, nt, out = _new(name)
        b = _bsdf(nt, base, 0.97)
        b.inputs["Sheen Weight"].default_value = 0.4
        vec = _coord(nt, scale=(1.0 / tile, 1.0 / tile, 1))
        ch = nt.nodes.new("ShaderNodeTexChecker")
        ch.inputs["Color1"].default_value = (*base, 1)
        ch.inputs["Color2"].default_value = (*base2, 1)
        ch.inputs["Scale"].default_value = 1.0
        _link(nt, vec, ch.inputs["Vector"])
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 400.0
        _link(nt, vec, n.inputs["Vector"])
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.blend_type = "OVERLAY"
        mix.inputs["Factor"].default_value = 0.25
        _link(nt, ch.outputs["Color"], mix.inputs[6])
        _link(nt, n.outputs["Color"], mix.inputs[7])
        _link(nt, mix.outputs[2], b.inputs["Base Color"])
        _link(nt, b.outputs[0], out.inputs["Surface"])
        m.diffuse_color = (*base, 1)
        return m
    return cached(f"carpet:{name}:{base}", make)


def marble(name, base, vein, rough=0.14):
    def make():
        m, nt, out = _new(name)
        b = _bsdf(nt, base, rough)
        b.inputs["Coat Weight"].default_value = 0.3
        vec = _coord(nt, scale=(0.6, 0.6, 0.6))
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"
        w.inputs["Scale"].default_value = 2.0
        w.inputs["Distortion"].default_value = 12.0
        w.inputs["Detail"].default_value = 8.0
        _link(nt, vec, w.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (*vein, 1)
        ramp.color_ramp.elements[1].position = 0.18
        ramp.color_ramp.elements[1].color = (*base, 1)
        _link(nt, FAC_OUT(w), FAC_IN(ramp))
        _link(nt, ramp.outputs["Color"], b.inputs["Base Color"])
        _link(nt, b.outputs[0], out.inputs["Surface"])
        m.diffuse_color = (*base, 1)
        return m
    return cached(f"marble:{name}:{base}", make)


def glass():
    def make():
        m, nt, out = _new("glass")
        b = _bsdf(nt, (0.9, 0.95, 0.97), 0.03)
        b.inputs["Transmission Weight"].default_value = 1.0
        b.inputs["IOR"].default_value = 1.45
        _link(nt, b.outputs[0], out.inputs["Surface"])
        m.diffuse_color = (0.7, 0.85, 0.9, 0.3)
        return m
    return cached("glass", make)


def emission(name, color, strength):
    def make():
        m, nt, out = _new(name)
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (*color, 1)
        e.inputs["Strength"].default_value = strength
        _link(nt, e.outputs[0], out.inputs["Surface"])
        return m
    return cached(f"emit:{name}:{color}:{strength}", make)


def blackbody_emission(name, kelvin, strength):
    def make():
        m, nt, out = _new(name)
        e = nt.nodes.new("ShaderNodeEmission")
        bb = nt.nodes.new("ShaderNodeBlackbody")
        bb.inputs["Temperature"].default_value = kelvin
        _link(nt, bb.outputs[0], e.inputs["Color"])
        e.inputs["Strength"].default_value = strength
        _link(nt, e.outputs[0], out.inputs["Surface"])
        return m
    return cached(f"bb:{name}:{kelvin}:{strength}", make)


def clay():
    return principled("clay", (0.78, 0.77, 0.75), 0.8)


def stamp_bg():
    def make():
        m, nt, out = _new("stamp_bg")
        e = nt.nodes.new("ShaderNodeEmission")
        e.inputs["Color"].default_value = (0.02, 0.025, 0.06, 1)
        e.inputs["Strength"].default_value = 1.0
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs[0].default_value = 0.72
        _link(nt, tr.outputs[0], mix.inputs[1])
        _link(nt, e.outputs[0], mix.inputs[2])
        _link(nt, mix.outputs[0], out.inputs["Surface"])
        return m
    return cached("stamp_bg", make)


# ── 화면 콘텐츠(발광) ──

def _emit_from(nt, out, color_socket, strength):
    e = nt.nodes.new("ShaderNodeEmission")
    _link(nt, color_socket, e.inputs["Color"])
    e.inputs["Strength"].default_value = strength
    # 화면 유리 반사를 약하게 섞는다
    gl = nt.nodes.new("ShaderNodeBsdfPrincipled")
    gl.inputs["Base Color"].default_value = (0.0, 0.0, 0.0, 1)
    gl.inputs["Roughness"].default_value = 0.08
    add = nt.nodes.new("ShaderNodeAddShader")
    _link(nt, e.outputs[0], add.inputs[0])
    _link(nt, gl.outputs[0], add.inputs[1])
    _link(nt, add.outputs[0], out.inputs["Surface"])


def _ramp(nt, fac_socket, stops):
    r = nt.nodes.new("ShaderNodeValToRGB")
    cr = r.color_ramp
    while len(cr.elements) < len(stops):
        cr.elements.new(0.5)
    for el, (pos, col) in zip(cr.elements, stops):
        el.position = pos
        el.color = (*col, 1)
    _link(nt, fac_socket, FAC_IN(r))
    return r.outputs["Color"]


def screen(content: str, strength: float = 4.0, seed: float = 0.0):
    """content: brand · menu · info · dashboard · art · board · epaper. UV = Generated(0..1)."""
    def make():
        m, nt, out = _new(f"screen_{content}")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        uv = tc.outputs["Generated"]
        if content == "epaper":
            b = _bsdf(nt, (0.72, 0.72, 0.70), 0.7)
            br = nt.nodes.new("ShaderNodeTexBrick")
            br.inputs["Scale"].default_value = 9.0
            br.inputs["Mortar Size"].default_value = 0.0
            br.inputs["Brick Width"].default_value = 1.8
            br.inputs["Row Height"].default_value = 0.12
            br.inputs["Color1"].default_value = (0.08, 0.08, 0.08, 1)
            br.inputs["Color2"].default_value = (0.70, 0.70, 0.68, 1)
            br.inputs["Mortar"].default_value = (0.72, 0.72, 0.70, 1)
            br.offset_frequency = 1
            _link(nt, uv, br.inputs["Vector"])
            _link(nt, br.outputs["Color"], b.inputs["Base Color"])
            _link(nt, b.outputs[0], out.inputs["Surface"])
            return m
        if content == "menu":
            br = nt.nodes.new("ShaderNodeTexBrick")
            br.inputs["Scale"].default_value = 3.0
            br.inputs["Mortar Size"].default_value = 0.03
            br.inputs["Brick Width"].default_value = 0.66
            br.inputs["Row Height"].default_value = 0.5
            br.offset = 0.0
            br.inputs["Color1"].default_value = (0.95, 0.55, 0.18, 1)
            br.inputs["Color2"].default_value = (0.98, 0.86, 0.62, 1)
            br.inputs["Mortar"].default_value = (0.12, 0.05, 0.02, 1)
            _link(nt, uv, br.inputs["Vector"])
            _emit_from(nt, out, br.outputs["Color"], strength * 0.8)
            return m
        if content == "dashboard":
            br = nt.nodes.new("ShaderNodeTexBrick")
            br.inputs["Scale"].default_value = 6.0
            br.inputs["Mortar Size"].default_value = 0.012
            br.inputs["Brick Width"].default_value = 0.9
            br.inputs["Row Height"].default_value = 0.5
            br.offset = 0.0
            br.inputs["Color1"].default_value = (0.02, 0.06, 0.14, 1)
            br.inputs["Color2"].default_value = (0.03, 0.10, 0.20, 1)
            br.inputs["Mortar"].default_value = (0.10, 0.55, 0.85, 1)
            _link(nt, uv, br.inputs["Vector"])
            n = nt.nodes.new("ShaderNodeTexNoise")
            n.noise_dimensions = "4D"  # W 입력은 4D 일 때만 생긴다(Blender 5.x)
            n.inputs["Scale"].default_value = 7.0
            n.inputs["W"].default_value = seed
            _link(nt, uv, n.inputs["Vector"])
            hot = _ramp(nt, FAC_OUT(n), [(0.55, (0, 0, 0)), (0.7, (0.95, 0.45, 0.10)), (0.8, (0.1, 0.85, 0.55))])
            add = nt.nodes.new("ShaderNodeMix")
            add.data_type = "RGBA"
            add.blend_type = "ADD"
            add.inputs["Factor"].default_value = 0.7
            _link(nt, br.outputs["Color"], add.inputs[6])
            _link(nt, hot, add.inputs[7])
            _emit_from(nt, out, add.outputs[2], strength)
            return m
        if content == "art":
            v = nt.nodes.new("ShaderNodeTexVoronoi")
            v.inputs["Scale"].default_value = 3.5
            v.voronoi_dimensions = "4D"
            v.inputs["W"].default_value = seed
            n = nt.nodes.new("ShaderNodeTexNoise")
            n.inputs["Scale"].default_value = 2.0
            _link(nt, uv, n.inputs["Vector"])
            mixv = nt.nodes.new("ShaderNodeMix")
            mixv.data_type = "VECTOR"
            mixv.inputs["Factor"].default_value = 0.35
            _link(nt, uv, mixv.inputs[4])
            _link(nt, n.outputs["Color"], mixv.inputs[5])
            _link(nt, mixv.outputs[1], v.inputs["Vector"])
            col = _ramp(nt, v.outputs["Distance"], [(0.0, (0.95, 0.70, 0.35)), (0.35, (0.80, 0.25, 0.20)),
                                                   (0.7, (0.10, 0.25, 0.45))])
            _emit_from(nt, out, col, strength * 0.7)
            return m
        if content == "board":
            w = nt.nodes.new("ShaderNodeTexWave")
            w.wave_type = "BANDS"
            w.bands_direction = "Y"
            w.inputs["Scale"].default_value = 9.0
            w.inputs["Distortion"].default_value = 3.0
            _link(nt, uv, w.inputs["Vector"])
            col = _ramp(nt, FAC_OUT(w), [(0.0, (0.95, 0.96, 0.98)), (0.93, (0.95, 0.96, 0.98)), (0.97, (0.10, 0.25, 0.70))])
            _emit_from(nt, out, col, strength * 0.55)
            return m
        if content == "info":
            sep = nt.nodes.new("ShaderNodeSeparateXYZ")
            _link(nt, uv, sep.inputs[0])
            col = _ramp(nt, sep.outputs["Y"], [(0.0, (0.86, 0.92, 0.98)), (0.78, (0.80, 0.88, 0.97)), (0.8, (0.05, 0.25, 0.65))])
            br = nt.nodes.new("ShaderNodeTexBrick")
            br.inputs["Scale"].default_value = 5.0
            br.inputs["Mortar Size"].default_value = 0.02
            br.inputs["Row Height"].default_value = 0.25
            br.inputs["Brick Width"].default_value = 1.6
            br.inputs["Color1"].default_value = (1, 1, 1, 1)
            br.inputs["Color2"].default_value = (0.92, 0.95, 1, 1)
            br.inputs["Mortar"].default_value = (0.75, 0.82, 0.92, 1)
            _link(nt, uv, br.inputs["Vector"])
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            _link(nt, col, mix.inputs[6])
            _link(nt, br.outputs["Color"], mix.inputs[7])
            _emit_from(nt, out, mix.outputs[2], strength * 0.6)
            return m
        # brand (기본) — 그라데이션 + 빛줄기
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        _link(nt, uv, sep.inputs[0])
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "BANDS"
        w.inputs["Scale"].default_value = 2.2
        w.inputs["Distortion"].default_value = 4.0
        w.inputs["Phase Offset"].default_value = seed
        _link(nt, uv, w.inputs["Vector"])
        mixf = nt.nodes.new("ShaderNodeMath")
        mixf.operation = "MULTIPLY_ADD"
        mixf.inputs[1].default_value = 0.35
        _link(nt, FAC_OUT(w), mixf.inputs[0])
        _link(nt, sep.outputs["X"], mixf.inputs[2])
        col = _ramp(nt, mixf.outputs[0], [(0.0, (0.008, 0.015, 0.10)), (0.35, (0.02, 0.08, 0.50)), (0.62, (0.22, 0.04, 0.50)),
                                         (0.9, (0.0, 0.45, 0.80)), (1.0, (0.55, 0.85, 1.0))])
        _emit_from(nt, out, col, strength * 0.7)
        return m
    return cached(f"screen:{content}:{strength}:{seed}", make)


def leaf():
    return principled("leaf", (0.035, 0.12, 0.03), 0.55, sss=0.15)


def soil():
    return principled("soil", (0.06, 0.04, 0.03), 0.95)


def ground():
    return concrete("ground", (0.22, 0.22, 0.22), (0.30, 0.30, 0.29), 0.85)


def build_palette(lib: dict, brief: dict) -> dict:
    """브리프 키 → 실제 재질."""
    fl = lib["floors"][brief["floor"]]
    wl = lib["walls"][brief["wall"]]
    ac = lib["accents"][brief["accent"]]
    fb = lib["fabrics"][brief["fabric"]]

    def floor_mat():
        k = fl["kind"]
        if k == "wood_planks":
            return wood_planks("floor", tuple(fl["base"]), tuple(fl["base2"]), fl.get("rough", 0.42), tuple(fl.get("plank", (0.19, 1.4))))
        if k == "concrete":
            return concrete("floor", tuple(fl["base"]), tuple(fl["base2"]), fl.get("rough", 0.35))
        if k == "terrazzo":
            return terrazzo("floor", tuple(fl["base"]), tuple(fl["base2"]), fl.get("rough", 0.28))
        if k == "carpet":
            return carpet("floor", tuple(fl["base"]), tuple(fl["base2"]), fl.get("tile", 0.5))
        if k == "marble":
            return marble("floor", tuple(fl["base"]), tuple(fl["base2"]), fl.get("rough", 0.14))
        return principled("floor_plain", tuple(fl["base"]), fl.get("rough", 0.5))

    def wall_mat():
        k = wl["kind"]
        if k == "concrete":
            return concrete("wall", tuple(wl["base"]), tuple(c * 1.15 for c in wl["base"]), 0.8)
        if k == "wood_slat":
            return wood_planks("wall_slat", tuple(wl["base"]), tuple(c * 1.2 for c in wl["base"]), 0.55, (0.06, 3.0), vertical=True)
        return paint(tuple(wl["base"]))

    def accent_mat():
        k = ac["kind"]
        if k == "metal":
            return metal(tuple(ac["base"]), ac.get("rough", 0.35))
        if k == "wood":
            return wood_planks("accent_wood", tuple(ac["base"]), tuple(c * 1.15 for c in ac["base"]), 0.45, (0.12, 0.9))
        return paint(tuple(ac["base"]), ac.get("rough", 0.4))

    def fabric_mat():
        if fb["kind"] == "leather":
            return leather(tuple(fb["base"]))
        return fabric(tuple(fb["base"]))

    wood_acc = ac if ac["kind"] == "wood" else {"base": [0.45, 0.30, 0.17]}
    return {
        "floor": floor_mat(), "wall": wall_mat(), "accent": accent_mat(), "fabric": fabric_mat(),
        "wood": wood_planks("furn_wood", tuple(wood_acc["base"]), tuple(c * 1.15 for c in wood_acc["base"]), 0.45, (0.15, 1.0)),
        "ceiling": paint((0.86, 0.86, 0.85), 0.9), "baseboard": paint((0.12, 0.12, 0.12), 0.6),
        "white": paint((0.80, 0.80, 0.78), 0.5), "glass": glass(), "frame": metal((0.03, 0.03, 0.03), 0.4),
        "pot": principled("pot", (0.72, 0.70, 0.66), 0.6), "bezel": plastic_dark(), "leaf": leaf(), "soil": soil(),
        "ground": ground(), "pillar": wall_mat(),
    }
