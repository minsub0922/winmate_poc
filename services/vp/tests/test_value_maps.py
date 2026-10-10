"""가치 맵(새 VP 흐름, 2026-10-08) — 보드 webapp1 VP2 · VP2_AI · VP2_Pick · VP2_Detail · VP_DoneJson."""
from __future__ import annotations

CANDS = [
    {"name": "The Wall IAB 146\"", "kind": "product", "spaces": ["로비"]},
    {"name": "Flip Pro WA75D", "kind": "product", "spaces": ["회의실"]},
    {"name": "MagicINFO", "kind": "solution", "ref": "kb:solution:sol_magicinfo", "spaces": []},
    {"name": "Smart Signage QB43C", "kind": "product", "spaces": ["공용공간"]},
]


async def _new(client, **kw):
    r = await client.post("/v1/value-maps", json={"title": "용산 AI Ready 오피스", "sb_id": "SB-01", "candidates": CANDS,
                                                  "context_text": "에너지 20% 절감 · 최초 AI Ready 오피스", **kw})
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_select_and_values(client):
    d = await _new(client)
    assert [i["name"] for i in d["items"]] == [c["name"] for c in CANDS]
    # 고르기: QB43C 빼고 카탈로그 밖 VXT 더하기
    sel = [c for c in CANDS if c["name"] != "Smart Signage QB43C"] + [{"name": "VXT", "kind": "solution"}]
    r = await client.put(f"/v1/value-maps/{d['id']}/items", json={"items": sel})
    d = r.json()
    assert [i["name"] for i in d["items"]][-1] == "VXT" and d["items"][-1]["from_dss"] is False
    assert (await client.put(f"/v1/value-maps/{d['id']}/items", json={"items": []})).status_code == 422
    wall = d["items"][0]["key"]
    # 가치 여러 개 + 니즈(직접 · 빈칸)
    r = await client.post(f"/v1/value-maps/{d['id']}/items/{wall}/values",
                          json={"space": "로비", "message": "들어서는 순간 회사의 AI 비전을 보여 줌", "need": "방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요", "req": "RQ-01 최초 AI Ready"})
    assert r.status_code == 201
    r = await client.post(f"/v1/value-maps/{d['id']}/items/{wall}/values", json={"space": "로비", "message": "사내 행사 때 로비를 무대로 바꿈"})
    d = r.json()
    vals = d["items"][0]["values"]
    assert len(vals) == 2 and vals[0]["need"]["by"] == "manual" and vals[1]["need"] is None
    assert d["counts"] == {"items": 4, "values": 2, "needs": 1, "needs_missing": 1, "pending": 0}
    # AI 니즈 추론(mock: '행사' → 고정 문장) → ai-pending → 수락
    r = await client.post(f"/v1/value-maps/{d['id']}/values/{vals[1]['id']}:infer-need")
    body = r.json()
    assert body["need"] == {"text": "행사 때마다 외부 장소를 빌리지 않았으면 해요", "by": "ai-pending"}
    assert body["map"]["counts"]["pending"] == 1
    r = await client.patch(f"/v1/value-maps/{d['id']}/values/{vals[1]['id']}", json={"accept_need": True})
    assert r.json()["counts"]["needs"] == 2


async def test_suggest_without_llm_uses_kb_messages(client):
    d = await _new(client)
    r = await client.post(f"/v1/value-maps/{d['id']}:suggest", json={})
    body = r.json()
    assert r.status_code == 200 and body["mode"] == "kb_only"
    magic = next(i for i in body["map"]["items"] if i["name"] == "MagicINFO")
    assert magic["values"] and all(v["by"] == "ai-pending" and v["need"] is None for v in magic["values"])
    assert all("KB 원문" in (v["basis"] or "") for v in magic["values"])
    assert body["map"]["counts"]["values"] == 0 and body["map"]["counts"]["pending"] == body["added_values"]
    # 모두 수락
    r = await client.post(f"/v1/value-maps/{d['id']}:accept-all")
    assert r.json()["counts"]["pending"] == 0 and r.json()["counts"]["values"] == body["added_values"]


async def test_linked_other_maps_import_and_finish(client):
    a = await _new(client)
    b = await _new(client, title="판교 스타트업 단지", sb_id="SB-05")
    key = next(i["key"] for i in b["items"] if i["name"] == "MagicINFO")
    await client.post(f"/v1/value-maps/{b['id']}/items/{key}/values", json={"space": "로비", "message": "입주사 안내를 한 화면에서", "need": "방문객이 입주사 위치를 바로 찾았으면 해요"})
    r = await client.get(f"/v1/value-maps/{a['id']}/items/{key}/linked")
    ln = r.json()
    assert ln["here"] == [] and ln["other"][0]["map_title"] == "판교 스타트업 단지" and ln["official"]
    r = await client.post(f"/v1/value-maps/{a['id']}/items/{key}/values:import", json={"from_map": b["id"], "value_id": ln["other"][0]["value_id"]})
    v = next(i for i in r.json()["items"] if i["key"] == key)["values"][0]
    assert v["message"] == "입주사 안내를 한 화면에서" and v["need"]["text"].startswith("방문객이")
    r = await client.post(f"/v1/value-maps/{a['id']}:finish")
    st = r.json()
    assert st["stage"]["from"] == "SB-01" and st["stage"]["counts"]["values"] == 1
    assert st["stage"]["selection"]["fromDss"] == 4 and st["summary_md"].startswith("## VP ·")
    empty = await _new(client)
    assert (await client.post(f"/v1/value-maps/{empty['id']}:finish")).status_code == 422


async def test_value_map_from_storyboard_dss_and_finish_pushes_stage(client, apps):
    """새 흐름: Gate 에서 고른 Storyboard 의 DSS 제품 · 솔루션으로 시작 → 저장하면 flow.json stages.vp · 요약본에 들어간다."""
    from winmate_common import testing
    async with testing.api_client(apps["storyboard"]) as sb:
        f = (await sb.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용",
                                               "rq": {"ref": "RQ-01", "ver": 1, "value": {}, "md": "- 요구 12"}})).json()
        # DSS 전에는 시작 못 함
        r = await client.post("/v1/value-maps", json={"sb_id": f["id"]})
        assert r.status_code == 422 and r.json()["error"]["code"] == "PREREQUISITE_MISSING"
        await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-01", "value": {
            "industry": {"value": "오피스 · 업무시설", "by": "manual"},
            "spaces": [{"name": "로비", "products": [{"name": "The Wall IAB 146\"", "kind": "product", "qty": 1}, {"name": "Smart Signage QM55C", "kind": "product", "qty": 2}]},
                       {"name": "회의실", "products": [{"name": "Smart Signage QM55C", "kind": "product", "qty": 1}]}],
            "solutions": [{"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo"}]}, "md": "- 공간 2"})
        d = (await client.post("/v1/value-maps", json={"sb_id": f["id"]})).json()
        assert d["title"] == "용산 AI Ready 오피스"
        names = {it["name"]: it for it in d["items"]}
        assert names["Smart Signage QM55C"]["spaces"] == ["로비", "회의실"] and names["MagicINFO"]["kind"] == "solution"
        wall = names["The Wall IAB 146\""]["key"]
        await client.post(f"/v1/value-maps/{d['id']}/items/{wall}/values", json={"space": "로비", "message": "들어서는 순간 AI 비전을 보여 줌", "need": "첫인상으로 각인시키고 싶어요"})
        out = (await client.post(f"/v1/value-maps/{d['id']}:finish")).json()
        assert out["flow_sync"]["md_added"].startswith("## VP · VP-")
        flow = (await sb.get(f"/v1/flows/{f['id']}")).json()
        assert flow["stages"]["vp"]["items"][0]["values"][0]["need"]["text"] == "첫인상으로 각인시키고 싶어요"
        assert flow["cells"][4]["route"] == f"/vp/values/{d['id']}" and flow["cards"]["vp"]["facts"][1] == ["가치", "1"]
        assert (await client.get(f"/v1/value-maps/{d['id']}")).json()["ver"] == 1
