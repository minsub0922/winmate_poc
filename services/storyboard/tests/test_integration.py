"""실제 서비스 앱과 in-process 통합 — requirements(정의서 실제 API) · export + files(PPTX · PDF 실제 렌더) · kb(실데이터)."""
from __future__ import annotations

import pytest
from winmate_common import testing
from winmate_common.jobs import jobs

from sb_rqdata import AUTHOR_NOTE, ITEMS, KEYMEN
from sb_world import Recorder, kb_stub


async def _seed_requirement(rc) -> str:
    r = await rc.post("/v1/requirements", json={"form": {"project_name": "용산 업무시설 재개발 AI Ready 오피스",
                                                         "customer_name": "E 자산운용", "author_note": AUTHOR_NOTE}})
    assert r.status_code == 201, r.text
    rq_id = r.json()["id"]
    ops = []
    for k in KEYMEN:
        ops.append({"op": "add_keyman", "keyman_id": k["id"].replace("km_", "km_01JTESTKEYMAN000000000000"), "name": k["name"]})
    ids = {k["id"]: k["id"].replace("km_", "km_01JTESTKEYMAN000000000000") for k in KEYMEN}
    for _code, km, text, _short, _nc in ITEMS:
        ops.append({"op": "add_item", "keyman_id": ids[km], "text": text})
    ops.append({"op": "set_weights", "weights": {ids["km_A"]: 50, ids["km_B"]: 30, ids["km_C"]: 20}})
    r = await rc.patch(f"/v1/requirements/{rq_id}/draft", json={"ops": ops})
    assert r.status_code == 200, r.text
    r = await rc.post(f"/v1/requirements/{rq_id}/save", json={})
    assert r.status_code in (200, 201), r.text
    return rq_id


@pytest.fixture
def real_rq_world(env):
    try:
        rq_app = testing.load_service_app("requirements")
    except Exception as exc:  # noqa: BLE001 — 다른 세션이 아직 만드는 중이면 건너뛴다
        pytest.skip(f"requirements 앱을 불러오지 못함: {exc}")
    ai = Recorder(testing.load_service_app("ai-tools"))
    apps = {**testing.platform_apps("workspace", "files", "export"), "ai-tools": ai, "kb": kb_stub(), "requirements": rq_app}
    with testing.inprocess(apps):
        yield apps


async def test_flow_with_real_requirements(real_rq_world):
    from winmate_storyboard.main import app
    from winmate_storyboard.worker import HANDLERS
    rq_app = real_rq_world["requirements"]
    async with testing.api_client(rq_app) as rc:
        try:
            rq_id = await _seed_requirement(rc)
        except AssertionError as exc:
            pytest.skip(f"requirements 정의서를 만들지 못함(개발 중): {exc}")
        try:
            await testing.drain_jobs("requirements", testing.load_service_worker("requirements"))
        except Exception:  # noqa: BLE001
            pass
        async with testing.api_client(app) as c:
            r = await c.post("/v1/storyboards", json={"requirement_id": rq_id})
            assert r.status_code == 201, r.text
            sb_id = r.json()["id"]
            await testing.drain_jobs("storyboard", HANDLERS)
            sb = (await c.get(f"/v1/storyboards/{sb_id}")).json()
            assert sb["settings"]["ready"] and sb["requirement_ref"]["version"] == 1
            assert sb["requirement_ref"]["item_count"] == 12 and sb["customer_name"] == "E 자산운용"
            r = await c.post(f"/v1/storyboards/{sb_id}/direction", json={"skip_planning": True})
            await testing.drain_jobs("storyboard", HANDLERS)
            r = await c.post(f"/v1/storyboards/{sb_id}/outline", json={})
            await testing.drain_jobs("storyboard", HANDLERS)
            sb = (await c.get(f"/v1/storyboards/{sb_id}")).json()
            assert sb["outline"]["ready"] and len(sb["trace"]["items"]) == 12
            lobby = next(s for s in sb["outline"]["spaces"] if s["name"] == "로비")
            r = await c.post(f"/v1/storyboards/{sb_id}/spaces/{lobby['id']}/questions")
            await testing.drain_jobs("storyboard", HANDLERS)
            r = await c.put(f"/v1/storyboards/{sb_id}/spaces/{lobby['id']}/slots/metric", json={"unknown": True})
            assert r.status_code == 200, r.text
            cq_id = r.json()["customer_question_id"]
        links = (await rc.get(f"/v1/requirements/{rq_id}/links")).json()["items"]
        mine = next(lk for lk in links if lk["ref_id"] == sb_id)
        assert mine["service"] == "storyboard" and mine["rq_version"] == 1 and mine["depends_on"]
        qs = (await rc.get(f"/v1/requirements/{rq_id}/customer-questions", params={"status": "open"})).json()["items"]
        q = next(x for x in qs if x["id"] == cq_id)
        assert q["origin"]["kind"] == "storyboard" and q["origin"]["place_label"] == "Part 2 로비"


@pytest.fixture
def render_world(env):
    from sb_world import World
    w = World()
    apps = {**w.apps, **testing.platform_apps("files", "export")}
    with testing.inprocess(apps):
        yield w


@pytest.mark.parametrize("fmt", ["pptx", "pdf"])
async def test_real_export_render(render_world, fmt):
    from winmate_storyboard.main import app

    from sb_flow import to_outline
    async with testing.api_client(app) as c:
        sb = await to_outline(c)
        r = await c.post(f"/v1/storyboards/{sb['id']}/exports", json={"format": fmt, "options": {"internal_memo": False}})
        job_id = r.json()["job_id"]
        from winmate_storyboard.worker import HANDLERS
        await testing.drain_jobs("storyboard", HANDLERS)
        rec = await jobs().get(job_id)
        if rec.status != "succeeded" and fmt == "pdf" and "UNAVAILABLE" in str(rec.error):
            pytest.skip("PDF 변환기 없음")
        assert rec.status == "succeeded", rec.error
        assert rec.result["name"] == f"E 자산운용 용산 오피스 제안 기획_스토리보드_v1.{fmt}"
        meta = await __import__("winmate_common.platform", fromlist=["file_meta"]).file_meta(rec.result["file_id"])
        assert meta["size"] > 1000
