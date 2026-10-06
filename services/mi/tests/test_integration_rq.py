"""in-process 통합 — 실제 requirements 앱(01-requirements.md §5.8 · §5.9 · §6)으로 정의서 스냅숏 읽기 · 사용 링크 등록."""
from __future__ import annotations

import pytest

from mi_scenario import design, run, setup_fb

from winmate_common import testing
from winmate_common.ids import new_id


@pytest.fixture
def rq_app(env):
    try:
        app = testing.load_service_app("requirements")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"requirements 서비스를 불러오지 못함: {exc}")
    env.apps["requirements"] = app
    return app


async def _make_rq(app) -> str:
    async with testing.api_client(app) as rc:
        r = await rc.post("/v1/requirements", json={"form": {"customer_name": "A 커피", "project_name": "A 커피 메뉴보드",
                                                            "author_note": "내부 메모 · 단가는 비밀"}})
        assert r.status_code in (200, 201), r.text
        rq = r.json()
        rid = rq.get("id") or rq.get("requirement_id")
        km = new_id("km")
        ops = [{"op": "add_keyman", "keyman_id": km, "name": "본사 운영팀장"},
               {"op": "add_item", "keyman_id": km, "item_id": new_id("ri"), "text": "본사 원격 통합 관리"},
               {"op": "add_item", "keyman_id": km, "item_id": new_id("ri"), "text": "저전력 운영"}]
        r = await rc.patch(f"/v1/requirements/{rid}/draft", json={"ops": ops})
        assert r.status_code == 200, r.text
        r = await rc.post(f"/v1/requirements/{rid}/save", json={"reason": "direct"})
        assert r.status_code in (200, 201), r.text
        return rid


async def test_requirements_snapshot_and_link(env, rq_app):
    with testing.inprocess(env.apps):
        rid = await _make_rq(rq_app)
        setup_fb(env)
        r = await env.c.post("/v1/analyses", json={"links": {"requirements_id": rid}})
        assert r.status_code == 201, r.text
        a = r.json()
        assert a["customer_name"] == "A 커피"
        defs = [q for q in a["requirements"] if q["origin"] == "definition"]
        assert [q["text"] for q in defs] == ["본사 원격 통합 관리", "저전력 운영"]
        assert all("단가" not in q["text"] for q in a["requirements"])          # 제작자 의견은 요구사항 칸에 넣지 않는다
        assert a["links"]["rq_version"] == 1
        async with testing.api_client(rq_app) as rc:
            links = (await rc.get(f"/v1/requirements/{rid}/links")).json()
        items = links.get("items") if isinstance(links, dict) else links
        assert any((x.get("service_name") or x.get("service")) == "mi" and x.get("ref_id") == a["id"] for x in items), links
        # 설계 · 분석이 정의서 항목으로 이어진다(작성자 의견은 내부용 프롬프트에만)
        await design(env, a["id"])
        await run(env, a["id"])
        crit = (await env.c.get(f"/v1/analyses/{a['id']}/criteria")).json()["items"]
        assert [c["name"] for c in crit][:2] == ["본사 원격 통합 관리", "저전력 운영"]
        prompts = [c for c in env.ai.llm_calls("mi.extract_requirements")]
        assert prompts and "제작자 의견(내부용" in prompts[-1]["prompt"] and prompts[-1]["confidential"]
