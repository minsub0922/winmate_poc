"""실제 ai-tools mock(mocks/ai-tools/mi.*.json) + 실제 kb · files · workspace · export 로 한 바퀴 — 개발 · e2e 데모 결과가 말이 되는지."""
from __future__ import annotations

from winmate_common import testing


async def test_mock_fixtures_demo_flow(tmp_path):
    with testing.environment(tmp_path, service="mi", MI_TODAY="2026-10-06"):
        testing.use_fake_redis()
        from winmate_mi import aix, kbx

        kbx.clear_cache()
        aix.reset_caps()
        apps = testing.platform_apps("ai-tools", "kb", "files", "workspace", "export")
        with testing.inprocess(apps):
            from winmate_mi.main import app
            from winmate_mi.worker import HANDLERS

            async with testing.api_client(app) as c:
                r = await c.post("/v1/analyses", json={"customer_name": "A 커피", "requirements_text": "A 커피 프랜차이즈 매장 메뉴보드 교체 제안 — 경쟁사 비교 위주로"})
                assert r.status_code == 201, r.text
                aid = r.json()["id"]
                r = await c.post(f"/v1/analyses/{aid}/design")
                assert r.status_code == 202, r.text
                await testing.drain_jobs("mi", HANDLERS)
                a = (await c.get(f"/v1/analyses/{aid}")).json()
                assert a["segment"]["code"] == "FB", a["segment"]
                assert a["status"] in ("designed", "ask"), a["status"]
                comps = (await c.get(f"/v1/analyses/{aid}/competitors")).json()["items"]
                assert len(comps) == 3, comps
                r = await c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
                assert r.status_code == 202, r.text
                await testing.drain_jobs("mi", HANDLERS)
                a = (await c.get(f"/v1/analyses/{aid}")).json()
                assert a["status"] == "done", a
                res = (await c.get(f"/v1/analyses/{aid}/result")).json()
                assert [t["area"] for t in res["tabs"]] == ["market", "customer", "user", "competitor"]
                assert all(t["status"] == "done" for t in res["tabs"]), res["tabs"]
                table = res["competitor"]["table"]
                assert [c["label"] for c in table["columns"]] == ["경쟁사 A", "경쟁사 B", "경쟁사 C", "삼성"]
                assert len(table["rows"]) >= 3
                cells = [c for row in table["rows"] for c in row["cells"].values()]
                assert sum(not c["placeholder"] for c in cells) >= 6, cells
                statuses = {c["status"] for c in cells if c["status"]}
                assert {"matched", "needs_check"} <= statuses, statuses
                assert res["competitor"]["strengths"], res["competitor"]
                assert res["market"]["size_series"] and res["customer"]["summary"] and res["user"]["personas"]
                src = (await c.get(f"/v1/analyses/{aid}/sources")).json()
                assert src["items"], src
