"""HTTP API — 샘플 설치 · 2D 계산 · 내보내기 · 3D 작업 만들기 · 파일 접근 막기. 임시 데이터 폴더에서 서버를 띄운다."""
import json
import threading
import unittest
import urllib.error
import urllib.request

import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E402 — python -m unittest tests.x 로도 돌게
from _util import temp_settings

from birdseye.app import App
from birdseye.server import install_samples, serve


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App(temp_settings({"BLENDER_PATH": "/nonexistent/blender", "BPY_PYTHON": "/nonexistent/python"}))
        install_samples(cls.app)
        cls.httpd = serve(cls.app, "127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()

    def call(self, method, path, body=None, raw=False):
        req = urllib.request.Request(self.base + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
            return (data, r.headers) if raw else json.loads(data)

    def status_of(self, method, path, body=None):
        try:
            self.call(method, path, body, raw=True)
            return 200
        except urllib.error.HTTPError as e:
            return e.code

    def test_env_and_index(self):
        env = self.call("GET", "/api/env")
        self.assertIn("llm", env)
        self.assertFalse(env["llm"]["available"])  # 키 없음 → 규칙 기반
        html, _ = self.call("GET", "/", raw=True)
        self.assertIn(b"/js/main.js", html)

    def test_samples_listed(self):
        ids = {p["id"] for p in self.call("GET", "/api/projects")["items"]}
        self.assertTrue({"2d-sample-lobby", "2d-sample-hospital", "3d-sample-lobby", "3d-sample-control"} <= ids)

    def test_2d_flow_new_project(self):
        p = self.call("POST", "/api/projects", {"kind": "2d", "title": "테스트 로비"})
        p["lines"] = [{"id": "L1", "product": "LH55QMCEBGCXKR", "mount": "wall", "qty": None},
                      {"id": "L2", "product": "LH75WMFWLGCXKR", "mount": "stand", "qty": None}]
        p["space"]["outlets"] = [{"id": "C1", "label": "C1", "x": 12000, "y": 4000, "on": "wall:right"}]
        recs = self.call("POST", "/api/2d/recommend", {"project": p})["recs"]
        self.assertEqual(set(recs), {"L1", "L2"})
        r = self.call("POST", "/api/2d/layout", {"project": p, "regenerate": None, "fixtures": "auto", "zones": "auto"})
        q = r["project"]
        self.assertGreater(len(q["placements"]), 0)
        self.assertIn("geom", r["validation"])
        saved = self.call("PUT", f"/api/projects/{q['id']}", {"project": q, "bump": True})
        self.assertEqual(saved["version"], 2)
        svg, h = self.call("GET", f"/api/projects/{q['id']}/drawing.svg?kind=plan&paper=A4", raw=True)
        self.assertTrue(svg.startswith(b"<svg"))
        z, h = self.call("POST", f"/api/projects/{q['id']}/export.zip", {"items": ["plan", "qty", "cad"]}, raw=True)
        self.assertEqual(z[:2], b"PK")
        self.assertIn("attachment", h["Content-Disposition"])
        qty = self.call("GET", f"/api/projects/{q['id']}/qty.json")
        self.assertEqual(qty["total"], len(q["placements"]))
        p3 = self.call("POST", f"/api/projects/{q['id']}/to3d")
        self.assertEqual(p3["linked_2d"], q["id"])
        self.assertEqual(set(p3["input"]["products"]), {"LH55QMCEBGCXKR", "LH75WMFWLGCXKR"})

    def test_fix_nl_zone_points(self):
        p = self.call("GET", "/api/projects/2d-sample-hospital")
        v = self.call("POST", "/api/2d/validate", {"project": p})
        w = next(x for x in v["warnings"] if x["level"] == "warn")
        r = self.call("POST", "/api/2d/fix", {"project": p, "warning_id": w["id"]})
        self.assertLess(r["validation"]["summary"]["warnings"], v["summary"]["warnings"])
        n = self.call("POST", "/api/2d/nl", {"project": p, "text": "대형 플랜터 600 위로"})
        self.assertEqual(n["source"], "rules")
        self.assertTrue(n["ops"])
        lobby = self.call("GET", "/api/projects/2d-sample-lobby")
        zp = self.call("POST", "/api/2d/zone_points", {"project": lobby, "text": "존 2 이름을 '웰컴 라운지'로"})
        self.assertEqual(next(z for z in zp["project"]["zones"] if z["no"] == 2)["name"], "웰컴 라운지")

    def test_3d_patch_and_render_needs_blender(self):
        p = self.call("POST", "/api/projects", {"kind": "3d"})
        p2 = self.call("POST", f"/api/projects/{p['id']}/patch", {"set": {"input": {"text": "밝은 회의실", "space_type": "meeting_room"}}})
        self.assertEqual(p2["input"]["space_type"], "meeting_room")
        self.assertEqual(p2["input"]["quality"], "standard")  # 나머지 입력은 유지
        self.assertEqual(self.status_of("POST", f"/api/projects/{p['id']}/patch", {"set": {"renders": []}}), 400)
        self.app.blender(refresh=True)
        self.assertEqual(self.status_of("POST", f"/api/projects/{p['id']}/render", {}), 409)  # Blender 없음

    def test_uploads_without_model_do_not_invent(self):
        img = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
        r = self.call("POST", "/api/2d/plan", {"image": img})
        self.assertFalse(r["ok"])
        self.assertTrue(r["reason"])
        r = self.call("POST", "/api/3d/photos", {"images": [img], "project_id": "3d-sample-control"})
        self.assertFalse(r["ok"])

    def test_files_are_confined(self):
        self.assertEqual(self.status_of("GET", "/files/3d-sample-lobby/project.json"), 403)
        self.assertIn(self.status_of("GET", "/files/3d-sample-lobby/renders/../../../etc/passwd"), (403, 404))
        self.assertEqual(self.status_of("GET", "/api/projects/..%2F..%2Fetc"), 404)


if __name__ == "__main__":
    unittest.main()
