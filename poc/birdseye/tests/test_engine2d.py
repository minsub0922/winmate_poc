"""2D 엔진 — 룰 · 권장 수량 · 배치 · 검증(F4) · 자동 조정 · 동선 · 존."""
import copy
import unittest

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E402 — python -m unittest tests.x 로도 돌게
from _util import catalog

from birdseye import samples
from birdseye.layout2d import layout_lines, recommend_all
from birdseye.rules import Rules
from birdseye.validate import apply_ops, autofix, validate
from birdseye.zones import order_zones, route_flow


class RulesTest(unittest.TestCase):
    def test_seed_rules_have_ids_and_expressions(self):
        rs = Rules().all()
        self.assertGreaterEqual(len(rs), 18)
        for r in rs:
            self.assertTrue(r["id"].startswith("pr_"))
            self.assertIn(r["kind"], ("size", "quantity", "capacity", "position", "warning"))
            self.assertTrue(r["expression"])
            self.assertTrue(r["explanation_ko"])

    def test_override_param_and_render(self):
        r = Rules({"pr_window_signage_qty": {"min_gap_mm": 2400}})
        self.assertEqual(r.p("pr_window_signage_qty", "min_gap_mm"), 2400)
        self.assertIn("2,400", r.render("pr_window_signage_qty"))
        self.assertEqual(r.rule("pr_window_signage_qty")["overridden"], ["min_gap_mm"])


class RecommendTest(unittest.TestCase):
    def setUp(self):
        self.cat = catalog()
        self.lobby = samples.build_lobby_2d(self.cat)

    def test_window_and_pillar_counts_follow_formula(self):
        recs = recommend_all(self.lobby, self.cat, Rules())
        # 유리창 10.2 m 두 곳, OM55B 폭 1,253 → floor((10200 − 1200 + 3000) / (1253 + 3000)) = 2 씩
        self.assertEqual(recs["L1"]["qty_rec"], 4)
        self.assertIn("pr_window_signage_qty", recs["L1"]["rule_ids"])
        # 기둥 2개 × 앞 · 뒤
        self.assertEqual(recs["L2"]["qty_rec"], 4)
        self.assertEqual(recs["L3"]["qty_rec"], 1)

    def test_layout_keeps_confirmed_qty(self):
        p = copy.deepcopy(self.lobby)
        p["lines"][0]["qty"] = 2
        layout_lines(p, self.cat, Rules(), {"L1"})
        self.assertEqual(sum(1 for pl in p["placements"] if pl["line"] == "L1"), 2)
        # 다른 줄은 그대로
        self.assertEqual(sum(1 for pl in p["placements"] if pl["line"] == "L2"), 4)


class ValidateTest(unittest.TestCase):
    def setUp(self):
        self.cat = catalog()

    def test_lobby_sample_is_clean_with_power_memos(self):
        v = validate(samples.build_lobby_2d(self.cat), self.cat, Rules())
        self.assertEqual(v["summary"]["warnings"], 0)
        self.assertEqual(v["summary"]["memos"], 2)
        for w in v["warnings"]:
            self.assertTrue(w["rule_id"].startswith("pr_warn_") or w["rule_id"].startswith("pr_"), w)
        self.assertIn("geom", v)
        self.assertEqual(len(v["geom"]["placements"]), 9)

    def test_hospital_sample_warnings_each_fix_resolves(self):
        p = samples.build_hospital_2d(self.cat)
        v = validate(p, self.cat, Rules())
        active = [w for w in v["warnings"] if w["level"] in ("warn", "error")]
        self.assertEqual(len(active), 2)
        self.assertEqual({w["kind"] for w in active}, {"traffic", "viewing_angle"})
        for w in active:
            q = copy.deepcopy(p)
            apply_ops(q, w["fix"]["ops"])
            v2 = validate(q, self.cat, Rules())
            self.assertNotIn(w["id"], [x["id"] for x in v2["warnings"]], f"고친 뒤에도 남음: {w['id']}")

    def test_autofix_clears_hospital(self):
        p, log = autofix(samples.build_hospital_2d(self.cat), self.cat, Rules())
        self.assertTrue(log)
        self.assertEqual(validate(p, self.cat, Rules())["summary"]["warnings"], 0)

    def test_ignored_warning_not_counted(self):
        p = samples.build_hospital_2d(self.cat)
        v = validate(p, self.cat, Rules())
        p["ignored"] = [v["warnings"][0]["id"]]
        self.assertEqual(validate(p, self.cat, Rules())["summary"]["warnings"], 1)


class FlowTest(unittest.TestCase):
    def test_flow_starts_at_entrance_and_visits_zones(self):
        cat = catalog()
        p = samples.build_lobby_2d(cat)
        f = route_flow(p, cat, p["zones"])
        self.assertTrue(f["ok"])
        x0, y0 = f["path"][0]
        e = next(o for o in p["space"]["openings"] if o["kind"] == "entrance")
        self.assertTrue(e["start"] <= x0 <= e["start"] + e["length"])
        self.assertLess(y0, 800)
        self.assertEqual(len(f["waypoints"]), len(p["zones"]) + 1)

    def test_order_zones_numbers_from_entrance(self):
        cat = catalog()
        p = samples.build_lobby_2d(cat)
        zs = order_zones(p, list(reversed(copy.deepcopy(p["zones"]))))
        self.assertEqual([z["no"] for z in zs], list(range(1, len(zs) + 1)))
        self.assertEqual(zs[0]["key"], "window")


if __name__ == "__main__":
    unittest.main()
