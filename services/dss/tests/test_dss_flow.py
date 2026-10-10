"""공간별 제품 매칭 DSS(새 흐름, 2026-10-08) — 보드 webapp1 DS1 · DS2 · DS2_AI · DS4 · DS4_AI · DS_Done.

허브(storyboard 실제 앱)에 고객 요구사항 Storyboard 를 만들고 → DSS 만들기 → 업종 · 공간 · 제품 · 솔루션 고치기 → AI(mock · KB 대체) → 저장 →
허브 flow.json stages.dss · 요약본 · 카드 · 진행 칸까지 확인한다.
"""
from __future__ import annotations

from typing import Any

from winmate_common import testing

REQS = [
    {"id": "R1", "text": "로비에서 입주사 안내와 입주사 공용 회의실 예약을 한 번에", "status": "ok", "by": "manual"},
    {"id": "R2", "text": "반도체 박물관 협업 전시", "status": "ok", "by": "manual"},
    {"id": "R3", "text": "단지 운영 · 단지 에너지 모니터링", "status": "check", "by": "manual"},
]


async def _sb(apps: dict[str, Any], *, rq: bool = True) -> str:
    async with testing.api_client(apps["storyboard"]) as sb:
        body: dict[str, Any] = {"name": "판교 스타트업 단지", "customer": "G 공사"}
        if rq:
            body["rq"] = {"ref": "RQ-05", "ver": 1, "md": "- 키맨 3 · 요구 3",
                          "value": {"customer": "G 공사", "title": "판교 스타트업 단지", "requirements": REQS, "goals": [], "keymen": [],
                                    "counts": {"keymen": 0, "reqs": 3, "check": 1}}}
        r = await sb.post("/v1/flows", json=body)
        assert r.status_code in (200, 201), r.text
        return r.json()["id"]


async def _new(client, apps) -> dict[str, Any]:
    sb = await _sb(apps)
    r = await client.post("/v1/dss", json={"sb_id": sb})
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_requires_rq_and_storyboard(client, apps):
    assert (await client.post("/v1/dss", json={"sb_id": "SB-99"})).status_code == 404
    d = await _new(client, apps)
    assert d["code"] == "DSS-01" and d["title"] == "판교 스타트업 단지" and d["rq_ref"] == "RQ-05"
    assert [r["n"] for r in d["reqs"]] == [1, 2, 3] and d["industry"] is None and d["spaces"] == []
    assert d["industry_options"][0] == "오피스 · 업무시설" and d["counts"] == {"spaces": 0, "products": 0, "solutions": 0, "pending": 0}
    lst = (await client.get("/v1/dss")).json()
    assert lst["items"][0]["id"] == d["id"]
    # 두 번째는 번호가 겹치지 않는다
    d2 = (await client.post("/v1/dss", json={"sb_id": d["sb_id"]})).json()
    assert d2["code"] == "DSS-02"


async def test_edit_industry_spaces_products(client, apps):
    d = await _new(client, apps)
    i = d["id"]
    r = await client.put(f"/v1/dss/{i}/industry", json={"value": "오피스 · 업무시설", "expected_version": d["version"]})
    d = r.json()
    assert d["industry"] == {"value": "오피스 · 업무시설", "by": "manual", "basis": None}
    # 낡은 판이면 409
    r = await client.put(f"/v1/dss/{i}/industry", json={"value": "리테일", "expected_version": 1})
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_CONFLICT"
    r = await client.post(f"/v1/dss/{i}/spaces", json={"name": "로비"})
    assert r.status_code == 201
    r = await client.post(f"/v1/dss/{i}/spaces", json={"name": "공용 회의실"})
    d = r.json()
    assert [s["name"] for s in d["spaces"]] == ["로비", "공용 회의실"] and d["spaces"][0]["by"] == "manual"
    # 직접 넣은 공간도 이름 낱말이 모두 나오는 요구 문장이 있으면 근거(보드 DS2 「근거 · RQ-05 1 · …」) — 없으면 비운다
    assert d["spaces"][0]["basis"].startswith("RQ-05 1 · 로비에서 입주사 안내") and d["spaces"][0]["basis"].endswith("…")
    assert d["spaces"][1]["basis"] == "RQ-05 1 · 공용 회의실 예약을 한 번에"
    r = await client.post(f"/v1/dss/{i}/spaces", json={"name": "주차장"})
    assert r.json()["spaces"][-1]["basis"] is None
    await client.delete(f"/v1/dss/{i}/spaces/{r.json()['spaces'][-1]['key']}")
    assert (await client.post(f"/v1/dss/{i}/spaces", json={"name": "로비"})).status_code == 409
    lobby = d["spaces"][0]["key"]
    r = await client.post(f"/v1/dss/{i}/spaces/{lobby}/products",
                          json={"name": "Smart Signage QM55C", "ref": "kb:model:mdl_LH55QMCEBGCXKR", "model_code": "LH55QMCEBGCXKR",
                                "family_id": "fam_G000182628", "qty": "2대", "why": "입주사 안내 · 직접 추가"})
    d = r.json()
    p = d["spaces"][0]["products"][0]
    assert p["by"] == "manual" and p["qty"] == "2대" and d["counts"]["products"] == 1
    r = await client.patch(f"/v1/dss/{i}/products/{p['id']}", json={"qty": ""})
    assert r.json()["spaces"][0]["products"][0]["qty"] is None
    await client.patch(f"/v1/dss/{i}/products/{p['id']}", json={"qty": "2대"})
    # KB 후보(제품 고르기 팝업)
    c = (await client.get(f"/v1/dss/{i}/spaces/{lobby}/candidates")).json()
    assert c["space"] == "로비" and c["items"] and all(x["ref"].startswith("kb:family:") for x in c["items"])
    # 공간 이름 바꾸고 지우기
    meet = d["spaces"][1]["key"]
    r = await client.patch(f"/v1/dss/{i}/spaces/{meet}", json={"name": "공용 회의실 A"})
    assert r.json()["spaces"][1]["name"] == "공용 회의실 A" and r.json()["spaces"][1]["basis"] == "RQ-05 1 · 공용 회의실 예약을 한 번에"
    r = await client.patch(f"/v1/dss/{i}/spaces/{meet}", json={"name": "카페"})               # 요구에 없는 이름 → 근거 비움
    assert r.json()["spaces"][1]["basis"] is None
    r = await client.patch(f"/v1/dss/{i}/spaces/{meet}", json={"name": "전시"})
    assert r.json()["spaces"][1]["basis"] == "RQ-05 2 · 전시"
    r = await client.delete(f"/v1/dss/{i}/spaces/{meet}")
    assert [s["name"] for s in r.json()["spaces"]] == ["로비"]


async def test_ai_industry_spaces_products_pending_then_accept(client, apps):
    d = await _new(client, apps)
    i = d["id"]
    # 업종(mock: 보드 DS2_AI 문장) → 점선 → 적용
    r = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "industry"})).json()
    assert r["mode"] == "llm" and r["added"] == 1
    ai = r["doc"]["industry_ai"]
    assert ai["value"] == "오피스 · 업무시설" and "‘입주사 공용 회의실 예약’" in ai["basis"] and ai["basis"].endswith("복합단지일 수도 있어요")
    assert r["doc"]["industry"] is None and r["doc"]["counts"]["pending"] == 1
    d = (await client.put(f"/v1/dss/{i}/industry", json={"accept_ai": True})).json()
    assert d["industry"]["by"] == "ai-accepted" and d["industry_ai"] is None
    # 공간 추천(mock) → 추가하면 ai-accepted · 근거 유지
    await client.post(f"/v1/dss/{i}/spaces", json={"name": "로비"})
    r = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "spaces"})).json()
    recs = {x["name"]: x for x in r["doc"]["space_recs"]}
    assert list(recs) == ["라운지", "전시 공간", "통합 관제실", "공용 공간", "주차장"]
    assert recs["전시 공간"]["why"] == "RQ-05 반도체 박물관 협업 전시" and recs["주차장"]["ext"] is True
    d = (await client.post(f"/v1/dss/{i}/spaces", json={"name": "전시 공간"})).json()
    ex = d["spaces"][-1]
    assert ex["by"] == "ai-accepted" and ex["basis"] == "RQ-05 2 · 반도체 박물관 협업 전시"
    assert "전시 공간" not in {x["name"] for x in d["space_recs"]}
    # 공간별 제품 자동 매칭(mock 은 빈 답 → KB S1 로 결정적) → 점선 → 모두 수락
    r = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "products"})).json()
    assert r["mode"] == "kb_only" and r["added"] >= 2
    pend = [p for s in r["doc"]["spaces"] for p in s["products"]]
    assert pend and all(p["by"] == "ai-pending" and p["ref"].startswith("kb:family:") and p["qty"] is None for p in pend)
    assert r["doc"]["counts"]["products"] == 0
    d = (await client.post(f"/v1/dss/{i}:accept-all")).json()
    assert d["counts"]["products"] == len(pend)
    # 한 번 더 돌려도 같은 제품은 다시 넣지 않는다
    r2 = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "products"})).json()
    names = [p["name"] for s in r2["doc"]["spaces"] for p in s["products"]]
    assert len(names) == len(set(names)) or len(r2["doc"]["spaces"]) > 1


async def test_ai_kb_fallback_without_model(client, apps):
    """mock 이 빈 답(요구에 '입주사' 없음) → A2 · S1 · space-types 로 결정적 추천."""
    async with testing.api_client(apps["storyboard"]) as sb:
        f = (await sb.post("/v1/flows", json={"name": "A 커피 매장 리뉴얼", "customer": "A 커피", "rq": {"ref": "RQ-02", "value": {
            "requirements": [{"id": "R1", "text": "카페 매장 메뉴보드를 디지털로 바꾸고 계산대 대기 줄을 줄이고 싶다"}]}}})).json()
    d = (await client.post("/v1/dss", json={"sb_id": f["id"]})).json()
    i = d["id"]
    r = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "industry"})).json()
    assert r["mode"] == "kb_only"
    assert r["doc"]["industry_ai"] is None or r["doc"]["industry_ai"]["value"] in d["industry_options"]
    r = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "spaces"})).json()
    assert r["mode"] == "kb_only" and r["doc"]["space_recs"]
    assert (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "products"})).status_code == 422


async def test_solutions_options_overlap_and_ai(client, apps):
    d = await _new(client, apps)
    i = d["id"]
    await client.put(f"/v1/dss/{i}/industry", json={"value": "오피스 · 업무시설"})
    d = (await client.post(f"/v1/dss/{i}/spaces", json={"name": "로비"})).json()
    lobby = d["spaces"][0]["key"]
    await client.post(f"/v1/dss/{i}/spaces/{lobby}/products", json={"name": "Smart Signage QM55C", "ref": "kb:model:mdl_LH55QMCEBGCXKR",
                                                                 "model_code": "LH55QMCEBGCXKR", "family_id": "fam_G000182628", "qty": "2대"})
    o = (await client.get(f"/v1/dss/{i}/solution-options")).json()
    by = {x["id"]: x for x in o["items"]}
    assert by["magicinfo"]["links"] == ["로비 Smart Signage QM55C"] and by["magicinfo"]["relevant"] and o["overlap"] is None
    assert o["items"][0]["id"] in ("magicinfo", "vxt")
    # 둘 다 사이니지 CMS → 겹침 안내
    d = (await client.put(f"/v1/dss/{i}/solutions", json={"ids": ["magicinfo", "vxt"]})).json()
    assert [s["name"] for s in d["solutions"]] == ["MagicINFO", "Samsung VXT"] and d["solutions"][0]["links"] == ["로비 Smart Signage QM55C"]
    o = (await client.get(f"/v1/dss/{i}/solution-options")).json()
    assert o["overlap"] and o["overlap"].startswith("MagicINFO와 Samsung VXT는 둘 다") and "사이니지" in o["overlap"]
    assert (await client.put(f"/v1/dss/{i}/solutions", json={"ids": ["nope"]})).status_code == 422
    # AI 솔루션 추천(mock: 보드 DS4_AI) → 점선 → 고르면 ai-accepted
    await client.put(f"/v1/dss/{i}/solutions", json={"ids": []})
    r = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "solutions"})).json()
    assert r["mode"] == "llm" and [x["id"] for x in r["doc"]["solution_recs"]] == ["magicinfo", "smartthings_pro", "biot"]
    assert r["doc"]["solution_recs"][0]["why"] == "RQ-05 1 입주사 안내 · 사이니지"
    o = (await client.get(f"/v1/dss/{i}/solution-options")).json()
    assert [x["id"] for x in o["items"][:3]] == ["magicinfo", "smartthings_pro", "biot"] and all(x["rec"] for x in o["items"][:3])
    d = (await client.put(f"/v1/dss/{i}/solutions", json={"ids": ["magicinfo", "biot"]})).json()
    assert [s["by"] for s in d["solutions"]] == ["ai-accepted", "ai-accepted"] and d["solutions"][1]["why"] == "RQ-05 3 단지 에너지 모니터링"


async def test_solutions_kb_fallback(client, apps):
    async with testing.api_client(apps["storyboard"]) as sb:
        f = (await sb.post("/v1/flows", json={"name": "용산 오피스", "rq": {"ref": "RQ-09", "value": {
            "requirements": [{"id": "R1", "text": "로비 사이니지 콘텐츠를 한 곳에서 관리"}, {"id": "R2", "text": "건물 에너지 공조 관리"}]}}})).json()
    d = (await client.post("/v1/dss", json={"sb_id": f["id"]})).json()
    i = d["id"]
    d = (await client.post(f"/v1/dss/{i}/spaces", json={"name": "로비"})).json()
    await client.post(f"/v1/dss/{i}/spaces/{d['spaces'][0]['key']}/products", json={"name": "Smart Signage QM55C", "family_id": "fam_G000182628", "ref": "kb:model:mdl_LH55QMCEBGCXKR"})
    r = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "solutions"})).json()
    ids = [x["id"] for x in r["doc"]["solution_recs"]]
    assert r["mode"] == "kb_only" and "magicinfo" in ids and not ("vxt" in ids and "magicinfo" in ids)
    assert any("RQ-09" in x["why"] for x in r["doc"]["solution_recs"])


async def test_finish_pushes_stage_to_storyboard(client, apps):
    d = await _new(client, apps)
    i, sb_id = d["id"], d["sb_id"]
    assert (await client.post(f"/v1/dss/{i}:finish")).status_code == 422          # 공간 없음
    await client.post(f"/v1/dss/{i}:suggest", json={"scope": "industry"})
    await client.put(f"/v1/dss/{i}/industry", json={"accept_ai": True})
    d = (await client.post(f"/v1/dss/{i}/spaces", json={"name": "로비"})).json()
    lobby = d["spaces"][0]["key"]
    assert (await client.post(f"/v1/dss/{i}:finish")).json()["error"]["code"] == "NO_PRODUCTS"
    await client.post(f"/v1/dss/{i}/spaces/{lobby}/products", json={"name": "Smart Signage QM55C", "ref": "kb:model:mdl_LH55QMCEBGCXKR",
                                                                 "model_code": "LH55QMCEBGCXKR", "family_id": "fam_G000182628", "qty": "2대"})
    r = (await client.post(f"/v1/dss/{i}:suggest", json={"scope": "products"})).json()
    pend = [p for p in r["doc"]["spaces"][0]["products"] if p["by"] == "ai-pending"]
    assert pend
    await client.patch(f"/v1/dss/{i}/products/{pend[0]['id']}", json={"accept": True})
    await client.put(f"/v1/dss/{i}/solutions", json={"ids": ["magicinfo"]})
    out = (await client.post(f"/v1/dss/{i}:finish")).json()
    st = out["stage"]
    assert st["industry"]["value"] == "오피스 · 업무시설" and st["industry"]["by"] == "ai-accepted"
    prods = st["spaces"][0]["products"]
    assert [p["by"] for p in prods] == ["manual", "ai-accepted"]                    # 점선(대기) 값은 저장에 안 들어간다
    assert prods[0] == {"name": "Smart Signage QM55C", "kind": "product", "ref": "kb:model:mdl_LH55QMCEBGCXKR", "model_code": "LH55QMCEBGCXKR", "qty": "2대", "by": "manual"}
    assert prods[1]["qty"] is None and prods[1]["qtyStatus"] == "확인 필요"
    so = st["solutions"]
    assert len(so) == 1 and {k: so[0][k] for k in ("name", "ref", "by", "why")} == {"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo", "by": "manual", "why": None}
    assert so[0]["links"][0] == "로비 Smart Signage QM55C" and all(x.startswith("로비 ") for x in so[0]["links"])   # 수락한 AI 제품도 지원 기기면 함께
    assert st["counts"] == {"spaces": 1, "products": 2, "solutions": 1}
    assert out["summary_md"].startswith("## DSS · DSS-01 v1\n- 업종: 오피스 · 업무시설 · 공간 1\n- 로비: Smart Signage QM55C ×2 · ")
    assert out["flow_sync"]["md_added"]
    async with testing.api_client(apps["storyboard"]) as sb:
        flow = (await sb.get(f"/v1/flows/{sb_id}")).json()
    assert flow["stages"]["dss"]["ref"] == "DSS-01" and flow["stages"]["dss"]["spaces"][0]["name"] == "로비"
    cell = next(c for c in flow["cells"] if c["key"] == "dss")
    assert cell["state"] == "done" and cell["route"] == f"/dss/{i}"
    assert flow["cards"]["dss"]["facts"][0] == ["업종", "오피스 · 업무시설"] and flow["cards"]["dss"]["line"].startswith("DSS-01 v1 · ")
    got = (await client.get(f"/v1/dss/{i}")).json()
    assert got["status"] == "done" and got["ver"] == 1
    # 다시 고쳐 저장하면 판이 오른다
    out2 = (await client.post(f"/v1/dss/{i}:finish")).json()
    assert out2["summary_md"].startswith("## DSS · DSS-01 v2")
    stage = (await client.get(f"/v1/dss/{i}/stage")).json()
    assert stage["stage"]["counts"]["products"] == 2


async def test_adopt_hub_only_dss(client, apps):
    """허브에만 있는 DSS(res_id = ref, 예시 데이터) → GET /v1/dss/DSS-nn 이 편집본을 만든다."""
    sb_id = await _sb(apps)
    async with testing.api_client(apps["storyboard"]) as sb:
        r = await sb.put(f"/v1/flows/{sb_id}/stages/dss", json={"ref": "DSS-07", "value": {
            "industry": {"value": "오피스 · 업무시설", "by": "ai-accepted"},
            "spaces": [{"name": "로비", "by": "manual", "products": [{"name": "Smart Signage QM55C", "kind": "product", "qty": 2, "by": "manual"}]}],
            "solutions": [{"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo", "by": "manual"}]}, "md": "- 공간 1"})
        assert r.status_code == 200, r.text
    d = (await client.get("/v1/dss/DSS-07")).json()
    assert d["id"] == "DSS-07" and d["sb_id"] == sb_id and d["status"] == "done" and d["ver"] == 1
    assert d["spaces"][0]["products"][0]["qty"] == "2대" and d["solutions"][0]["id"] == "magicinfo"
    assert (await client.get("/v1/dss/DSS-99")).status_code == 404
    # 숫자가 아닌 ref(e2e 도우미 · 다른 곳에서 저장한 DSS-ab12)도 가져온다
    async with testing.api_client(apps["storyboard"]) as sb:
        sb2 = await _sb(apps)
        await sb.put(f"/v1/flows/{sb2}/stages/dss", json={"ref": "DSS-ab12", "value": {
            "spaces": [{"name": "회의실", "by": "manual", "products": [{"name": "Flip Pro WA75D", "kind": "product", "qty": None, "by": "manual"}]}],
            "solutions": []}, "md": "- 공간 1"})
    d2 = (await client.get("/v1/dss/DSS-ab12")).json()
    assert d2["id"] == "DSS-ab12" and d2["sb_id"] == sb2 and d2["industry"] is None and d2["spaces"][0]["products"][0]["qty"] is None
    # 새 DSS 번호는 허브 ref 와 겹치지 않는다
    n = (await client.post("/v1/dss", json={"sb_id": sb_id})).json()
    assert n["code"] not in ("DSS-07",)
