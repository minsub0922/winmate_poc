"""다른 서비스와 실제로 이어 보기(in-process) — requirements(정의서 → 네 칸 · 사용 링크) · mi(MI 묶음 → imports/competitor).

플랫폼 앱(ai-tools mock · kb · files · jobs · workspace · export) + 실제 requirements · mi.
"""
from __future__ import annotations

import json

from ca_scenario import A_TEXT
from winmate_common import testing
from winmate_common.ids import new_id

NAMES = ["가나 디스플레이", "다라 사이니지", "마바 클라우드", "사아 키오스크"]


async def make_definition(rq) -> str:
    r = await rq.post("/v1/requirements", json={"form": {"project_name": "A 커피 메뉴보드 교체", "customer_name": "A 커피 프랜차이즈",
                                                         "author_note": "담당자는 가격에 민감하다는 내부 메모"}})
    assert r.status_code == 201, r.text
    rq_id = r.json()["id"]
    km = new_id("km")
    ops = [{"op": "add_keyman", "keyman_id": km, "name": "본사 IT"}]
    for t in ("본사에서 전 매장 메뉴 콘텐츠를 일괄 배포", "매장별로 가격을 다르게 표시", "전기료 절감"):
        ops.append({"op": "add_item", "keyman_id": km, "text": t})
    r = await rq.patch(f"/v1/requirements/{rq_id}/draft", json={"ops": ops})
    assert r.status_code == 200, r.text
    r = await rq.post(f"/v1/requirements/{rq_id}/save", json={"reason": "direct"})
    assert r.status_code in (200, 201), r.text
    return rq_id


async def test_definition_to_find_and_link(demo):
    c = demo.c
    async with testing.api_client(demo.apps["requirements"]) as rq:
        rq_id = await make_definition(rq)
        p = (await c.post("/v1/parse", json={"requirements_id": rq_id})).json()
        assert p["slots"]["customer"]["value"] == "A 커피 프랜차이즈" and p["slots"]["customer"]["origin"] == "definition"
        for k in ("customer", "industry", "place", "product"):
            assert "내부 메모" not in (p["slots"][k]["value"] or "")
        r = await c.post("/v1/analyses", json={"input_mode": "requirements", "requirements_id": rq_id})
        assert r.status_code == 201, r.text
        aid = r.json()["id"]
        assert r.json()["input_label"] == "요구사항에서"
        assert (await c.post(f"/v1/analyses/{aid}/find")).status_code == 202
        await demo.drain()
        a = (await c.get(f"/v1/analyses/{aid}")).json()
        assert a["status"] == "confirming", a
        assert a["rq_version"] == 1
        links = (await rq.get(f"/v1/requirements/{rq_id}/links")).json()
        items = links["items"] if isinstance(links, dict) else links
        mine = [x for x in items if x.get("service") in ("competitor", "CA") and x.get("ref_id") == aid]
        assert mine, links
        assert mine[0]["route"].startswith(f"/competitor/{aid}")
        # 정의서 요구가 비교 기준 앞자리(요구 → 기준 이름)
        crit = (await c.get(f"/v1/analyses/{aid}/criteria")).json()
        assert crit["summary"]["requirements"] >= 1


async def test_mi_bundle_import(demo):
    c = demo.c
    r = await c.post("/v1/analyses", json={"input_mode": "free", "text": A_TEXT})
    aid = r.json()["id"]
    await c.post(f"/v1/analyses/{aid}/find")
    await demo.drain()
    r = await c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    assert r.status_code == 202
    await demo.drain()
    assert (await c.get(f"/v1/analyses/{aid}")).json()["status"] == "done"
    h = (await c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "mi"})).json()
    b = (await c.get(f"/v1/analyses/{aid}/bundle", params={"target": "mi", "handoff_id": h["handoff_id"]})).json()
    assert {x["real_name"] for x in b["competitors"]} == set(NAMES)
    async with testing.api_client(demo.apps["mi"]) as mi:
        r = await mi.post("/v1/imports/competitor", json={"customer_name": "A 커피 프랜차이즈", "ca_bundle": b})
        assert r.status_code == 202, r.text
        mi_aid = r.json()["analysis_id"]
        await demo.drain("mi")
        comps = (await mi.get(f"/v1/analyses/{mi_aid}/competitors")).json()
        names = {x["real_name"] for x in comps["items"]}
        assert set(NAMES) <= names, comps
        assert all(x["origin"] == "ca_import" for x in comps["items"] if x["real_name"] in NAMES)
    r = await c.patch(f"/v1/analyses/{aid}/handoffs/{h['handoff_id']}", json={"status": "delivered", "target_id": mi_aid})
    assert r.status_code == 200
    lst = (await c.get("/v1/analyses")).json()
    row = next(x for x in lst["items"] if x["id"] == aid)
    assert row["sent_label"] == "MI 작업"
    assert not any(n in json.dumps(lst, ensure_ascii=False) for n in NAMES)
