"""requirements 실제 앱(in-process) 통합 — 01-requirements §5.8(GET 목록 · 버전 스냅숏) · §5.9(쓰는 곳 링크 PUT).

정의서(프로젝트 prj_RQ)에 `24시간 운영` 항목을 저장해 두고, 같은 프로젝트의 Spec 시트를 생성하면
QB55C(16/7) 는 `요구 미충족` 경고를 받고, 정의서 `쓰는 곳` 에 spec 링크가 생긴다.
"""
from __future__ import annotations

import pytest
from sp_helpers import QB55C, QM55C
from winmate_common import testing
from winmate_common.client import ServiceClient


@pytest.fixture
def real_rq(ctx):
    try:
        app = testing.load_service_app("requirements")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"requirements 앱을 불러오지 못함: {exc}")
    apps = {**ctx.apps, "requirements": app}
    with testing.inprocess(apps):
        yield app


async def test_requirements_definition_to_spec(ctx, client, real_rq):
    rq = ServiceClient("requirements", timeout=60)
    created = await rq.post("/v1/requirements", json={"project_id": "prj_RQ", "form": {"customer_name": "C 물류센터", "project_name": "관제실"}})
    rq_id = created["id"]
    from winmate_common.ids import new_id
    km = new_id("km")
    upd = await rq.patch(f"/v1/requirements/{rq_id}/draft", json={"ops": [
        {"op": "add_keyman", "keyman_id": km, "name": "시설팀장"},
        {"op": "add_item", "keyman_id": km, "text": "관제실 디스플레이는 24시간 운영되어야 함"}]})
    assert upd["item_count"] >= 1
    await rq.post(f"/v1/requirements/{rq_id}/save", json={})
    await testing.drain_jobs("requirements", testing.load_service_worker("requirements"))

    ctx.use_cat_fix(version="2026-09")
    r = await client.post("/v1/sheets", json={"start": "model", "products": [QM55C, QB55C], "project_id": "prj_RQ"})
    assert r.status_code == 201, r.text
    s = r.json()
    sid = s["id"]
    await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid}/generate", json={"auto_answer": True})
    await ctx.run_jobs()
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    unmet = [w for w in v["items"] if w["kind"] == "requirement_unmet"]
    assert [w["title"] for w in unmet] == ["운영 시간 · QB55C"]
    assert unmet[0]["body"].startswith("고객 ")
    links = await rq.get(f"/v1/requirements/{rq_id}/links")
    items = links.get("items") if isinstance(links, dict) else links
    assert any(lk.get("service") == "spec" and lk.get("ref_id") == sid for lk in items or [])
