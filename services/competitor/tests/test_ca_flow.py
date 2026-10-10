"""경쟁사 리스트업(새 CA 흐름, 2026-10-08) — 보드 webapp1 CA2 · CA2_Info · CA2_Pc · CA2_AI · CA_DoneJson.

허브 연동: Storyboard(rq → dss) → 만들기(DSS 비교 기준) → 직접 추가(위키) → 비교 쌍 고치기 → AI 후보 웹 탐색 → 수락 → 저장 → flow.json stages.ca.
"""
from __future__ import annotations

import pytest
from conftest import FakeAI
from winmate_common import testing

DSS = {
    "industry": {"value": "오피스 · 업무시설", "by": "manual"},
    "spaces": [
        {"name": "로비", "products": [{"name": "The Wall IAB 146\"", "kind": "product", "qty": 1}, {"name": "Smart Signage QM55C", "kind": "product", "qty": 2}]},
        {"name": "라운지", "products": [{"name": "Smart Signage QB43C", "kind": "product", "qty": 2}]},
        {"name": "회의실", "products": [{"name": "Flip Pro WA75D", "kind": "product", "qty": 4}, {"name": "Smart Signage QB55C", "kind": "product", "qty": 4}]},
        {"name": "중앙관제실", "products": [{"name": "비디오월 VM55B", "kind": "product", "qty": 9}]},
        {"name": "공용공간", "products": [{"name": "Smart Signage QM43C", "kind": "product", "qty": 3}, {"name": "Smart Signage QH55C", "kind": "product", "qty": 2}]},
        {"name": "엘리베이터 홀", "products": [{"name": "Smart Signage OM46B", "kind": "product", "qty": 2}]},
    ],
    "solutions": [{"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo"}, {"name": "SmartThings Pro", "ref": "kb:solution:sol_smartthings_pro"},
                  {"name": "b.IoT", "ref": "kb:solution:sol_biot"}],
}


@pytest.fixture
async def hub(tmp_path):
    """플랫폼 실제 앱(ai-tools mock = mocks/ai-tools/ca.flow_*.json) + 실제 storyboard 허브."""
    with testing.environment(tmp_path, service="competitor", WEB_FETCH_ENABLED="false"):
        testing.use_fake_redis()
        from winmate_competitor import aix

        aix.reset_caps()
        apps = {**testing.platform_apps(), "storyboard": testing.load_service_app("storyboard")}
        with testing.inprocess(apps):
            from winmate_competitor.main import app

            async with testing.api_client(app) as c, testing.api_client(apps["storyboard"]) as sb:
                yield c, sb


async def _storyboard(sb, dss: bool = True) -> str:
    f = (await sb.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용",
                                          "rq": {"ref": "RQ-01", "ver": 1, "value": {"customer": "E 자산운용"}, "md": "- 요구 12"}})).json()
    if dss:
        r = await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-01", "value": DSS, "md": "- 공간 6"})
        assert r.status_code == 200, r.text
    return f["id"]


async def test_create_requires_dss_and_fills_basis(hub):
    c, sb = hub
    assert (await c.post("/v1/ca-flows", json={"sb_id": "SB-99"})).status_code == 404
    sid = await _storyboard(sb, dss=False)
    r = await c.post("/v1/ca-flows", json={"sb_id": sid})
    assert r.status_code == 422 and r.json()["error"]["code"] == "PREREQUISITE_MISSING"
    sid = await _storyboard(sb)
    r = await c.post("/v1/ca-flows", json={"sb_id": sid})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["code"].startswith("CA-") and d["title"] == "용산 AI Ready 오피스 경쟁사" and d["customer"] == "E 자산운용"
    # 보드 CA2: 비교 기준 · DSS-01 · 사이니지 6 · LED 1 · 협업 디스플레이 1 · 비디오월 1 · IoT · 솔루션 3
    assert d["basis"]["from"] == "DSS-01"
    assert d["basis"]["categories"] == ["사이니지", "LED", "협업 디스플레이", "비디오월", "IoT · 솔루션"]
    assert d["basis"]["counts"] == {"사이니지": 6, "LED": 1, "협업 디스플레이": 1, "비디오월": 1, "IoT · 솔루션": 3}
    qm = next(i for i in d["dss_items"] if i["name"] == "Smart Signage QM55C")
    assert qm["spaces"] == ["로비"] and qm["category"] == "사이니지"
    lst = (await c.get("/v1/ca-flows")).json()
    assert lst["items"][0]["id"] == d["id"] and lst["items"][0]["status"] == "draft"


async def test_flow_end_to_end_pushes_stage(hub):
    c, sb = hub
    sid = await _storyboard(sb)
    d = (await c.post("/v1/ca-flows", json={"sb_id": sid})).json()
    fid = d["id"]
    # 직접 추가 — 위키(웹 검색 요약 · 근거 구절이 있는 값만) · 겹치는 제품군의 DSS 제품으로 비교 쌍
    r = await c.post(f"/v1/ca-flows/{fid}/competitors", json={"name": "경쟁사 A"})
    assert r.status_code == 201, r.text
    a = r.json()["competitors"][0]
    assert a["id"] == "A" and a["by"] == "manual"
    assert a["wiki"]["hq"] == "국내" and a["wiki"]["mainBusiness"] == "상업용 디스플레이 · LED 월" and a["wiki"]["b2bOffice"] == "국내 납품 다수"
    assert a["wiki"]["revenue"] == "[위키 값]" and a["wiki"]["employees"] == "[위키 값]"     # 근거 없는 수치는 지어내지 않는다
    assert a["categories"] == ["사이니지", "LED"] and a["why"].startswith("사이니지 · LED 겹침 · 로비")
    crit = {x["k"]: x for x in a["criteria"]}
    assert crit["고객 접점"] == {"k": "고객 접점", "v": "E 자산운용 거래 이력", "status": "check"}
    assert crit["제품군"]["v"].startswith("사이니지 · LED — DSS-01 로비")
    assert [m["ours"] for m in a["matches"]] == ["The Wall IAB 146\"", "Smart Signage QM55C"]
    assert all(m["dims"]["spec"] == {"verdict": "no-data", "note": "자료 없음"} and m["theirs"] == "[확인 필요]" for m in a["matches"])
    # 이름이 같으면 409
    assert (await c.post(f"/v1/ca-flows/{fid}/competitors", json={"name": "경쟁사 a"})).json()["error"]["code"] == "DUPLICATE_COMPETITOR"
    # 위키 결과가 없는 회사 → 모두 자리표시
    b = (await c.post(f"/v1/ca-flows/{fid}/competitors", json={"name": "모르는 회사"})).json()["competitors"][1]
    assert b["wiki"]["hq"] == "[확인 필요]" and b["matches"] == [] and b["criteria"][0]["status"] == "check"
    v = (await c.get(f"/v1/ca-flows/{fid}")).json()["version"]
    # 비교 쌍 고치기 · 판정 · 메모 · expected_version 409
    m0 = a["matches"][0]
    r = await c.patch(f"/v1/ca-flows/{fid}/competitors/A/matches/{m0['id']}", json={
        "space": "로비 미디어월", "theirs": "올인원 LED 월 · 동급 크기", "expected_version": v,
        "dims": {"spec": {"verdict": "similar", "note": "해상도 동급 · 밝기 수치 확인"}, "price": {"verdict": "ours-worse", "note": "가격 이점 없음 · 초기가 낮음 [견적 확인]"},
                 "cases": {"verdict": "ours-better", "note": "국내 AI 오피스 로비 사례"}}})
    assert r.status_code == 200, r.text
    assert (await c.patch(f"/v1/ca-flows/{fid}/competitors/A/matches/{m0['id']}", json={"theirs": "x", "expected_version": v})).status_code == 409
    # DSS 밖 제품은 비교 쌍이 안 된다 · 묶음 이름은 된다
    assert (await c.post(f"/v1/ca-flows/{fid}/competitors/A/matches", json={"ours": "갤럭시 탭"})).json()["error"]["code"] == "NOT_IN_DSS"
    r = await c.post(f"/v1/ca-flows/{fid}/competitors/A/matches", json={"ours": "MagicINFO", "theirs": "자사 CMS"})
    assert r.status_code == 201 and r.json()["competitors"][0]["matches"][-1]["space"] == "전체"
    # 장단점 · 주장 · 기본 정보 고치기
    r = await c.patch(f"/v1/ca-flows/{fid}/competitors/A", json={
        "pros": ["초기 도입가가 낮음 [견적 확인]", " "], "cons": ["AI 오피스 레퍼런스가 적음"],
        "claims": [{"axis": "통합", "text": "MagicINFO · SmartThings Pro · b.IoT 하나의 플랫폼으로 공간을 묶음", "supports": "RQ-01"}],
        "wiki": {"employees": "", "size": "대기업 · 매출 [위키 값]"}})
    a = r.json()["competitors"][0]
    assert a["pros"] == ["초기 도입가가 낮음 [견적 확인]"] and a["claims"][0]["supports"] == "RQ-01" and a["wiki"]["employees"] == "[위키 값]"
    assert a["size"] == "대기업"
    # 모르는 회사는 빼기
    assert len((await c.delete(f"/v1/ca-flows/{fid}/competitors/B")).json()["competitors"]) == 1

    # AI 경쟁사 후보군 웹 탐색 — 점선(ai-pending), 근거 출처 · 구절
    r = await c.post(f"/v1/ca-flows/{fid}:candidates")
    body = r.json()
    assert r.status_code == 200 and body["mode"] == "web" and body["added"] == 3, body
    cands = [x for x in body["flow"]["competitors"] if x["by"] == "ai-pending"]
    assert [x["name"] for x in cands] == ["경쟁사 C", "경쟁사 D", "경쟁사 E"] and [x["id"] for x in cands] == ["B", "C", "D"]
    cc = cands[0]
    assert cc["candidateEvidence"]["source"] == "업계 뉴스" and cc["candidateEvidence"]["date"] == "2026-08"
    assert cc["wiki"]["revenue"] == "[위키 값]" and cc["why"] == "비디오월 · IoT · 솔루션 겹침 · 중앙관제실"
    assert cc["matches"][0]["ours"] == "비디오월 VM55B" and cc["matches"][0]["dims"]["price"]["verdict"] == "ours-worse"
    assert next(x for x in cands if x["name"] == "경쟁사 E")["matches"][0]["ours"] == "QM55C + MagicINFO"
    assert body["flow"]["counts"]["competitors"] == 1 and body["flow"]["counts"]["candidates"] == 3
    # 다시 돌려도 같은 후보를 또 넣지 않는다
    assert (await c.post(f"/v1/ca-flows/{fid}:candidates")).json()["added"] == 0
    # 후보 수락(목록에 추가) 2곳 · 1곳 빼기
    await c.patch(f"/v1/ca-flows/{fid}/competitors/B", json={"accept": True})
    await c.patch(f"/v1/ca-flows/{fid}/competitors/D", json={"accept": True})
    d = (await c.delete(f"/v1/ca-flows/{fid}/competitors/C")).json()
    assert d["counts"]["competitors"] == 3 and d["counts"]["candidates"] == 0

    # 저장 → Storyboard stages.ca(§6 ca 모양) · 요약 · 카드
    out = (await c.post(f"/v1/ca-flows/{fid}:finish")).json()
    st = out["stage"]
    assert st["ref"] == d["code"] and st["ver"] == 1 and st["basis"]["from"] == "DSS-01"
    assert st["dimensions"] == ["스펙", "가격", "유관 사례", "ESG", "브랜드 평판"]
    assert [x["by"] for x in st["competitors"]] == ["manual", "ai-web", "ai-web"]
    assert set(st["competitors"][0]) == {"id", "name", "by", "wiki", "criteria", "matches", "pros", "cons", "claims", "candidateEvidence"}
    assert st["competitors"][0]["wiki"]["source"]["type"] == "웹 검색 요약"
    vc = st["counts"]["verdicts"]
    assert st["counts"]["matches"] == 3 + 2 + 1 and sum(vc.values()) == st["counts"]["matches"] * 5
    assert vc["oursBetter"] == 1 + 4 + 2 and vc["oursWorse"] == 1 + 1 + 1
    assert out["flow_sync"]["md_added"].startswith("## 경쟁사 · CA-")
    assert "- 경쟁사 3 (직접 1 · AI 웹 탐색 2) · 비교 쌍 6" in out["flow_sync"]["md_added"]
    flow = (await sb.get(f"/v1/flows/{d['sb_id']}")).json()
    sca = flow["stages"]["ca"]
    assert sca["ref"] == d["code"] and sca["ver"] == 1 and sca["competitors"][1]["candidateEvidence"]["quote"].startswith("빌딩 관제 납품")
    cell = next(x for x in flow["cells"] if x["key"] == "ca")
    assert cell["state"] == "done" and cell["route"] == f"/competitor/flow/{fid}"
    assert flow["cards"]["ca"]["facts"][0] == ["경쟁사", "3"]
    contents = (await sb.get("/v1/flows/contents/ca")).json()
    assert contents["items"][0]["route"] == f"/competitor/flow/{fid}"
    # 다시 저장하면 ver 2
    again = (await c.post(f"/v1/ca-flows/{fid}:finish")).json()
    assert again["stage"]["ver"] == 2 and (await c.get(f"/v1/ca-flows/{fid}")).json()["status"] == "done"


async def test_finish_needs_competitor(hub):
    c, sb = hub
    sid = await _storyboard(sb)
    d = (await c.post("/v1/ca-flows", json={"sb_id": sid})).json()
    assert (await c.post(f"/v1/ca-flows/{d['id']}:finish")).json()["error"]["code"] == "NO_COMPETITORS"
    await c.post(f"/v1/ca-flows/{d['id']}:candidates")
    # AI 후보(점선)만 있으면 아직 저장할 수 없다
    assert (await c.post(f"/v1/ca-flows/{d['id']}:finish")).status_code == 422


@pytest.fixture
async def fake(tmp_path):
    """가짜 ai-tools(응답 · 호출 기록) + 실제 storyboard — 대체 경로 · 근거 검사."""
    with testing.environment(tmp_path, service="competitor"):
        testing.use_fake_redis()
        from winmate_competitor import aix

        aix.reset_caps()
        ai = FakeAI()
        apps = {"ai-tools": ai.app, "storyboard": testing.load_service_app("storyboard"), **testing.platform_apps("workspace")}
        with testing.inprocess(apps):
            from winmate_competitor.main import app

            async with testing.api_client(app) as c, testing.api_client(apps["storyboard"]) as sb:
                yield c, sb, ai


async def test_candidates_fallback_and_grounding(fake):
    c, sb, ai = fake
    sid = await _storyboard(sb)
    fid = (await c.post("/v1/ca-flows", json={"sb_id": sid})).json()["id"]
    # 웹 검색 장애 → 후보 0 · mode none(지어내지 않는다)
    ai.web["ca.flow_candidates_web.v1"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE"}}
    body = (await c.post(f"/v1/ca-flows/{fid}:candidates")).json()
    assert body["mode"] == "none" and body["added"] == 0 and "직접 추가" in body["reason"]
    # 요약에 없는 회사 · 근거 구절은 버리고, 요약에 없는 수치는 [00]
    ai.web["ca.flow_candidates_web.v1"] = {"summary": "관제 비디오월은 가람 비전이 공급하며 구축 묶음가는 3억 수준이다."}
    ai.llm["ca.flow_candidates.v1"] = {"candidates": [
        {"name": "가람 비전", "industry": "관제", "categories": ["비디오월", "없는 제품군"], "evidence_quote": "관제 비디오월은 가람 비전이 공급하며",
         "matches": [{"ours": "비디오월 VM55B", "theirs": "관제 비디오월", "price": {"verdict": "ours-worse", "note": "묶음가 3억 vs 5억"}},
                     {"ours": "없는 제품", "theirs": "x"}], "pros": ["시공 경험 12년"]},
        {"name": "지어낸 회사", "industry": "x", "evidence_quote": "관제 비디오월은 가람 비전이 공급하며"},
        {"name": "가람 비전 2", "industry": "x", "evidence_quote": "요약에 없는 구절"}]}
    body = (await c.post(f"/v1/ca-flows/{fid}:candidates")).json()
    assert body["added"] == 1, body
    g = body["flow"]["competitors"][0]
    assert g["name"] == "가람 비전" and g["categories"] == ["비디오월"] and len(g["matches"]) == 1
    assert g["matches"][0]["dims"]["price"]["note"] == "묶음가 3억 vs [00]억" and g["pros"] == ["시공 경험 [00]년"]
    assert g["matches"][0]["dims"]["spec"] == {"verdict": "no-data", "note": "자료 없음"}
    assert all(call["confidential"] for call in ai.llm_calls("ca.flow_candidates.v1"))
    # 위키: 근거 구절이 요약에 없거나 숫자가 구절에 없으면 자리표시
    ai.web["ca.flow_wiki_web.v1"] = {"summary": "나래 디스플레이는 국내 기업이며 임직원은 1,200명이다."}
    ai.llm["ca.flow_wiki.v1"] = {"hq": {"value": "국내", "quote": "나래 디스플레이는 국내 기업이며"},
                                 "employees": {"value": "1,500명", "quote": "임직원은 1,200명이다"},
                                 "revenue": {"value": "3조", "quote": "매출은 3조"}, "categories": ["사이니지"]}
    n = (await c.post(f"/v1/ca-flows/{fid}/competitors", json={"name": "나래 디스플레이"})).json()["competitors"][-1]
    assert n["wiki"]["hq"] == "국내" and n["wiki"]["employees"] == "[위키 값]" and n["wiki"]["revenue"] == "[위키 값]"
    assert n["by"] == "manual" and n["categories"] == ["사이니지"] and len(n["matches"]) == 1
    # 모델 장애 → 자리표시만
    ai.llm["ca.flow_wiki.v1"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE"}}
    m = (await c.post(f"/v1/ca-flows/{fid}/competitors", json={"name": "다온 사이니지"})).json()["competitors"][-1]
    assert m["wiki"]["hq"] == "[확인 필요]" and m["matches"] == []


def test_md_lines_short_claims():
    """요약 줄의 주장은 낱말 경계에서 자르고 … 를 붙인다(보드 CA_Done 요약본 한 줄)."""
    from winmate_competitor import caflow as cf

    assert cf._short("하나의 플랫폼", 32) == "하나의 플랫폼"
    long = "MagicINFO · SmartThings Pro · b.IoT 하나의 플랫폼으로 공간 7개를 묶음"
    s = cf._short(long, 32)
    assert s.endswith("…") and len(s) <= 33 and long.startswith(s[:-1]) and s[:-1] in ("MagicINFO · SmartThings Pro", "MagicINFO · SmartThings Pro · b.IoT")
    d = {"code": "CA-01", "competitors": [{"id": "A", "name": "경쟁사 A", "by": "manual", "matches": [],
                                           "claims": [{"axis": "통합", "text": long}, {"axis": "사례", "text": "국내 AI 오피스 로비 도입사례"}]}]}
    lines = cf.md_lines(d)
    assert lines[0] == "- 경쟁사 1 (직접 1 · AI 웹 탐색 0) · 비교 쌍 0"
    assert lines[-1].startswith("- 주장: 통합 — MagicINFO · SmartThings Pro") and "… · 사례 — 국내 AI 오피스 로비 도입사례" in lines[-1]
