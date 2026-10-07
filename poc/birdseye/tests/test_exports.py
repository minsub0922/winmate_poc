"""내보내기 — 수량표(xlsx · csv) · CAD(DXF R12) · 도면 SVG · 제안서 데이터 · ZIP."""
import io
import json
import unittest
import zipfile

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E402 — python -m unittest tests.x 로도 돌게
from _util import catalog

from birdseye import exporters as EX
from birdseye import samples
from birdseye.drawing import plan_svg
from birdseye.rules import Rules
from birdseye.validate import validate


class ExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = catalog()
        cls.p = samples.build_lobby_2d(cls.cat)
        cls.v = validate(cls.p, cls.cat, Rules())

    def test_qty_rows_match_placements(self):
        rows = EX.qty_rows(self.p, self.cat)
        self.assertEqual(len(rows), 4)
        self.assertEqual(sum(r["qty"] for r in rows), len(self.p["placements"]))
        om = next(r for r in rows if r["short"] == "OM55B")
        self.assertEqual(om["qty"], 3)
        self.assertEqual(om["qty_rec"], 4)  # 사용자가 3대로 확정 — 권장값과 다르게 남는다
        self.assertIn("pr_window_signage_qty", om["rule_ids"])
        self.assertTrue(om["source"].startswith("https://"))

    def test_xlsx_has_five_sheets(self):
        data = EX.qty_workbook(self.p, self.cat, self.v, True, "2026-10-06")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            self.assertIn("xl/workbook.xml", names)
            wb = z.read("xl/workbook.xml").decode("utf-8")
        for t in ("제품 수량표", "배치 좌표", "집기", "존", "검토"):
            self.assertIn(t, wb)

    def test_csv_utf8_bom(self):
        data = EX.qty_csv(self.p, self.cat)
        self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
        self.assertIn("OM55B", data.decode("utf-8-sig"))

    def test_dxf_r12_layers(self):
        data = EX.to_dxf(self.p, self.cat, self.v)
        text = data.decode("cp949")
        self.assertIn("AC1009", text)
        for layer in ("WALL", "PRODUCT", "FIXTURE", "ZONE", "DIM"):
            self.assertIn(layer, text)
        self.assertTrue(text.rstrip().endswith("EOF"))

    def test_svg_sheets(self):
        for kind in ("plan", "zones", "flow"):
            svg = plan_svg(self.p, self.cat, kind, "A3", validation=self.v, today="2026-10-06")
            self.assertTrue(svg.startswith("<svg"))
            self.assertRegex(svg[:200], r'width="420(\.0)?mm" height="297(\.0)?mm"')
            self.assertIn("1:", svg)  # 표제란 축척

    def test_payload_and_bundle(self):
        pl = EX.proposal_payload(self.p, self.cat, self.v)
        self.assertEqual(set(pl["sheets"]), {"SM-A", "SM-B", "ZP-A"})
        data = EX.bundle_zip(self.p, self.cat, ["plan", "zones", "flow", "qty", "cad"], "A3", True, self.v, "2026-10-06")
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = set(z.namelist())
            self.assertTrue({"plan.svg", "zones.svg", "flow.svg", "qty.xlsx", "qty.csv", "layout.dxf", "proposal_payload.json", "README.txt"} <= names)
            json.loads(z.read("project.json"))


if __name__ == "__main__":
    unittest.main()
