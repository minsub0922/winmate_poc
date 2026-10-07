"""3D 씬 — 2D 연결 배치 · 씬 명세(제품 치수 = KB 스펙) · (선택) Blender 실제 렌더.

Blender 렌더 테스트는 느려서 기본으로 건너뛴다: BIRDSEYE_TEST_BLENDER=1 python3 -m unittest tests.test_scene3d
"""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E402 — python -m unittest tests.x 로도 돌게
from _util import catalog, temp_settings

from birdseye import blender_runner, samples
from birdseye.analyze3d import rule_brief
from birdseye.catalog import native_portrait, screen_size
from birdseye.rules import Rules
from birdseye.scene3d import build_layout, estimate_space, layout_info, make_cuts, scene_spec


class SceneTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = catalog()
        cls.p2 = samples.build_lobby_2d(cls.cat)
        cls.p3 = samples.build_lobby_3d(cls.cat, "x")
        cls.info = layout_info(cls.p3, cls.p2, cls.cat, Rules())
        cls.brief = rule_brief(cls.p3, cls.info)
        cls.lay = build_layout(cls.p3, cls.info, cls.brief, cls.p2, cls.cat, Rules())

    def test_linked_layout_keeps_2d_products(self):
        a = sorted((p["id"], p["x"], p["y"]) for p in self.lay["placements"])
        b = sorted((p["id"], p["x"], p["y"]) for p in self.p2["placements"])
        self.assertEqual(a, b)
        types = {f["type"] for f in self.lay["fixtures"]}
        self.assertIn("bench", types)
        self.assertTrue(types & {"plinth", "planter_large"})  # 갤러리 · 식물은 AI(규칙)가 더함

    def test_spec_products_use_spec_dimensions(self):
        spec = scene_spec(self.lay, self.brief, self.cat, make_cuts([("aerial45", "day", "after"), ("aerial45", "day", "before")]), "draft", "t")
        self.assertEqual(spec["stamp"]["text"], "AI 생성 · 개략")
        self.assertTrue(spec["stamp"]["font"] and Path(spec["stamp"]["font"]).exists())
        for sp in spec["products"]:
            pl = next(p for p in self.lay["placements"] if p["id"] == sp["id"])
            prod = self.cat.get(pl["product"])
            if prod["category"] == "hvac_cassette":
                continue
            portrait = pl.get("portrait")
            sw, sh = screen_size(prod, native_portrait(prod) if portrait is None else portrait)
            self.assertAlmostEqual(sp["sw"] * sp["sh"], sw * sh, delta=1.0)
        self.assertEqual([c["variant"] for c in spec["cuts"]], ["after", "before"])

    def test_estimate_space_from_scale(self):
        sp, basis = estimate_space({"space_type": "meeting_room", "scale": {"area_pyeong": 12, "height": "normal"}})
        self.assertAlmostEqual(sp["width"] * sp["depth"] / 1e6, 12 * 3.3058, delta=4)
        self.assertTrue(sp["estimated"])
        self.assertIn("추정", basis)


@unittest.skipUnless(os.environ.get("BIRDSEYE_TEST_BLENDER") == "1", "BIRDSEYE_TEST_BLENDER=1 일 때만(느림)")
class BlenderRenderTest(unittest.TestCase):
    def test_tiny_render(self):
        s = temp_settings({k: os.environ[k] for k in ("BLENDER_PATH", "BPY_PYTHON") if os.environ.get(k)})
        loc = blender_runner.locate(s, refresh=True)
        if not loc.get("kind"):
            self.skipTest(loc.get("note"))
        cat = catalog()
        p2 = samples.build_lobby_2d(cat)
        p3 = samples.build_lobby_3d(cat, "x")
        info = layout_info(p3, p2, cat, Rules())
        brief = rule_brief(p3, info)
        lay = build_layout(p3, info, brief, p2, cat, Rules())
        spec = scene_spec(lay, brief, cat, make_cuts([("aerial45", "day", "after")]), "draft", "test")
        spec["render"].update(res=[192, 108], samples=4, preview=None)
        out = Path(tempfile.mkdtemp(prefix="birdseye-render-"))
        (out / "scene.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        events = []
        man = blender_runner.run(s, out / "scene.json", out, events.append, threading.Event(), timeout=600)
        self.assertEqual(len(man["cuts"]), 1)
        self.assertTrue((out / man["cuts"][0]["file"]).exists())
        self.assertLess(max(d["err_mm"] for d in man["qc"]["product_dims"]), 1.0)
        self.assertFalse(man["qc"]["overlaps"])
        vis = man["cuts"][0]["visibility"]
        self.assertTrue(sum(1 for v in vis if v["visible"] >= 0.4) >= len(vis) // 2)
        self.assertTrue(any(e.get("kind") == "cut_done" for e in events))


if __name__ == "__main__":
    unittest.main()
