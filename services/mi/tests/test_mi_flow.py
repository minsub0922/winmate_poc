"""새 MI 흐름(웹앱 ① v58 — 보드 MI2_Loading · MI2 · MI3 · MI_Done) — `/v1/mi-flows*` + Storyboard 허브 연동.

만들기(사전 작업 DSS 확인) → Storyboard 분석 잡(mi.flow_analyze.v1 · 기밀) → 검색어 · 조건 고치기 → 웹 검색 잡(검색어 보호 · 비기밀)
→ 정제(담기 · 빼기 · 문장 고치기) → 저장(허브 stages.mi · 요약본 · 카드) → 고쳐 저장(v2 · prevVer · 담은 정보 유지).
"""
from __future__ import annotations

from typing import Any

import pytest
from winmate_common import testing

RQ_VALUE = {
    "customer": "E 자산운용", "title": "용산 AI Ready 오피스", "target": "용산 업무시설 재개발",
    "goals": ["에너지 절감", "AI Ready"],
    "requirements": [{"id": "R1", "text": "로비에 회사의 AI 비전을 보여 주는 대형 미디어월을 설치하고 방문객 안내를 자동화한다", "status": "ok", "by": "manual"},
                     {"id": "R2", "text": "건물 전체 에너지 사용량을 20% 절감한다", "status": "ok", "by": "manual"}],
}
DSS_VALUE = {
    "industry": {"value": "오피스 · 업무시설", "by": "manual"},
    "spaces": [{"name": "로비", "products": [{"name": "The Wall IAB 146\"", "kind": "product", "qty": 1}]},
               {"name": "회의실", "products": [{"name": "Flip Pro WA75D", "kind": "product", "qty": 4}]},
               {"name": "임원실", "products": []}],
    "solutions": [{"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo"}],
}
ANALYZE = {
    "customer": "E 자산운용", "industry": "오피스 · 업무시설", "spaces": ["로비", "회의실", "옥상정원"], "needs": ["에너지 절감", "AI Ready"],
    "queries": {"market": ["프라임 오피스 스마트 빌딩 도입", "서울 도심 신축 오피스 임대 동향"],
                "customer": ["E 자산운용 용산 재개발", "E 자산운용 ESG 에너지 목표"],
                "user": ["하이브리드 근무 회의실 수요"]},
}
WEB = {
    "프라임 오피스": "부동산 리서치 2026-08 리포트에 따르면 프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다. "
                 "건축 매체 2026-05 보도에 따르면 오피스 로비를 브랜드 공간으로 바꾸는 사례가 늘고 있다.",
    "임대 동향": "경제지 2026-09 보도에 따르면 서울 도심 신축 오피스의 공실률이 3년 만에 가장 높다. "
             "업계 2020-01 자료에 따르면 오래된 임대 시장 전망이 나왔다.",
    "용산 재개발": "경제지 2026-05 보도에 따르면 E 자산운용이 용산 재개발 사업을 추진하고 있다.",
    "ESG": "지속가능경영보고서 2026-04 공시에 따르면 E 자산운용은 보유 오피스의 에너지 사용을 2030년까지 [00]% 줄이는 목표를 세웠다.",
    "회의실 수요": "리서치 기관 2026-06 조사에 따르면 하이브리드 근무 확산 뒤 소규모 회의실 수요가 늘었다.",
}


def _web(body: dict[str, Any]) -> dict[str, Any]:
    q = body["query"]
    for k, v in WEB.items():
        if k in q:
            return {"summary": v, "sources": [{"url": f"https://news.example.com/{len(k)}", "title": f"{k} 기사 2026-08"}]}
    return {"summary": ""}


@pytest.fixture
async def flow_env(env):
    env.apps["storyboard"] = testing.load_service_app("storyboard")
    env.ai.llm["mi.flow_analyze.v1"] = ANALYZE
    env.ai.web["mi.flow_search.v1"] = _web
    async with testing.api_client(env.apps["storyboard"]) as sb:
        env.sb = sb
        yield env


async def _storyboard(sb, *, dss: bool = True) -> str:
    f = (await sb.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용",
                                          "rq": {"ref": "RQ-01", "ver": 1, "value": RQ_VALUE, "md": "- 요구 2"}})).json()
    if dss:
        r = await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-01", "value": DSS_VALUE, "md": "- 공간 3"})
        assert r.status_code == 200, r.text
    return f["id"]


async def _ready(env, sb_id: str) -> dict[str, Any]:
    r = await env.c.post("/v1/mi-flows", json={"sb_id": sb_id})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["phase"] == "analyzing" and [s["label"] for s in d["progress"]["steps"]][0] == f"Storyboard {sb_id} 읽기"
    await env.drain()
    return (await env.c.get(f"/v1/mi-flows/{d['id']}")).json()


async def test_create_needs_dss_and_storyboard(flow_env):
    env = flow_env
    assert (await env.c.post("/v1/mi-flows", json={"sb_id": "SB-99"})).status_code == 404
    sb = await _storyboard(env.sb, dss=False)
    r = await env.c.post("/v1/mi-flows", json={"sb_id": sb})
    assert r.status_code == 422 and r.json()["error"]["code"] == "PREREQUISITE_MISSING"


async def test_analyze_validates_model_answer(flow_env):
    env = flow_env
    sb = await _storyboard(env.sb)
    d = await _ready(env, sb)
    assert d["phase"] == "search" and d["analysis_mode"] == "llm" and d["code"].startswith("MI-")
    assert d["title"] == "용산 AI Ready 오피스 시장 분석"
    assert [s["state"] for s in d["progress"]["steps"]] == ["done", "done", "done"]
    assert d["progress"]["steps"][1]["note"] == "E 자산운용 · 오피스 · 공간 2"       # DSS 에 없는 '옥상정원'은 버림
    assert {b["k"]: b["v"] for b in d["basis"]} == {"고객사": "E 자산운용", "업종": "오피스 · 업무시설", "공간": "로비 외 1", "요구": "에너지 절감 · AI Ready"}
    assert [q["text"] for q in d["queries"]["market"]] == ANALYZE["queries"]["market"] and d["counts"]["queries"] == 5
    call = env.ai.llm_calls("mi.flow_analyze.v1")[0]
    assert call["confidential"] is True and "로비에 회사의 AI 비전" in call["prompt"]


async def test_rule_fallback_without_model(flow_env):
    env = flow_env
    env.ai.llm["mi.flow_analyze.v1"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "모델 장애"}}
    d = await _ready(env, await _storyboard(env.sb))
    assert d["phase"] == "search" and d["analysis_mode"] == "rule"
    assert [q["text"] for q in d["queries"]["customer"]] == ["E 자산운용 사업 현황", "E 자산운용 투자 계획", "E 자산운용 ESG"]
    assert [q["text"] for q in d["queries"]["user"]] == ["오피스 로비 이용자 경험", "오피스 회의실 이용자 경험", "오피스 임원실 이용자 경험"]
    assert all(q["by"] == "rule" for q in d["queries"]["market"]) and d["warnings"]
    assert [q["text"] for q in d["queries"]["market"]] == ["오피스 시장 동향", "오피스 디지털 전환 사례", "오피스 에너지 절감", "오피스 AI Ready"]


def test_rule_need_query_drops_plan_numbers():
    from winmate_mi import miflow as F
    assert F.need_query("오피스", "에너지 20% 절감") == "오피스 에너지 절감"           # 고객 계획 수치는 검색어에 넣지 않는다
    assert F.need_query("오피스", "최초 AI Ready 오피스") == "오피스 최초 AI Ready"      # 업종 낱말은 한 번만
    assert F.need_query("오피스", "20%") is None


async def test_search_refine_finish_and_edit(flow_env):
    env = flow_env
    sb = await _storyboard(env.sb)
    d = await _ready(env, sb)
    fid = d["id"]
    # 검색어 고치기: 하나 빼고 · 고객 요구 원문(20자 넘게)을 그대로 넣은 검색어 · 조건(최근 1년 · 정부 통계 빼기 그대로)
    qs = d["queries"]
    qs["user"].append({"text": "로비에 회사의 AI 비전을 보여 주는 대형 미디어월", "on": True, "by": "manual"})
    qs["market"].append({"text": "건물 에너지 효율 규제", "on": False, "by": "manual"})
    r = await env.c.patch(f"/v1/mi-flows/{fid}", json={"queries": qs, "expected_version": 1})
    assert r.status_code == 409
    r = await env.c.patch(f"/v1/mi-flows/{fid}", json={"queries": qs, "filters": {"period": "최근 1년", "sourceTypes": ["뉴스", "공시 · IR", "리포트"]},
                                                       "expected_version": d["version"]})
    assert r.status_code == 200 and r.json()["counts"]["queries"] == 6
    r = await env.c.post(f"/v1/mi-flows/{fid}:search")
    assert r.json()["phase"] == "searching" and [s["key"] for s in r.json()["progress"]["steps"]] == ["market", "customer", "user", "organize"]
    await env.drain()
    d = (await env.c.get(f"/v1/mi-flows/{fid}")).json()
    assert d["phase"] == "refine"
    webs = env.ai.web_calls("mi.flow_search.v1")
    assert webs and all(c["confidential"] is False for c in webs)
    assert not any("로비에 회사의 AI 비전을" in c["query"] for c in webs)                     # 검색어 보호(고객 원문 20자)
    assert "건물 에너지 효율 규제" not in [c["query"] for c in webs]                          # 뺀 검색어
    items = {x["summary"]: x for x in d["items"]}
    first = items["프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다."]
    assert first["source"] == {"type": "리포트", "name": "부동산 리서치", "date": "2026-08", "url": None}   # 요약형 검색 → URL 없음
    assert first["group"] == "시장" and first["addedIn"] == "v1" and first["numberCheck"] is None
    vac = items["서울 도심 신축 오피스의 공실률이 3년 만에 가장 높다."]
    assert vac["source"]["type"] == "뉴스" and vac["numberCheck"]["values"] == ["3년"]
    esg = next(x for x in d["items"] if x["group"] == "고객사" and "에너지" in x["summary"])
    assert esg["source"]["type"] == "공시 · IR" and esg["numberCheck"]["values"] == ["[00]"]
    assert not any("오래된 임대 시장" in x["summary"] for x in d["items"])                     # 기간 조건(최근 1년) 밖
    assert any("조건에 맞지 않는 1개" in w for w in d["warnings"])
    assert d["counts"]["found"] == 6 and d["counts"]["numberCheck"] == 2
    # 정제: 하나 빼고 · 문장 고치기
    lobby = items["오피스 로비를 브랜드 공간으로 바꾸는 사례가 늘고 있다."]
    r = await env.c.patch(f"/v1/mi-flows/{fid}/items/{lobby['id']}", json={"kept": False})
    assert r.json()["counts"]["kept"] == 5
    r = await env.c.patch(f"/v1/mi-flows/{fid}/items/{first['id']}", json={"summary": "프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석"})
    assert next(x for x in r.json()["items"] if x["id"] == first["id"])["edited"] is True
    # 저장 → 허브
    out = (await env.c.post(f"/v1/mi-flows/{fid}:finish")).json()
    st = out["stage"]
    assert st["ref"] == d["code"] and st["ver"] == 1 and st["prevVer"] is None
    assert st["counts"] == {"found": 6, "kept": 5, "numberCheck": 2} and len(st["items"]) == 5
    assert st["filters"] == {"period": "최근 1년", "sourceTypes": ["뉴스", "공시 · IR", "리포트"]}
    assert "건물 에너지 효율 규제" not in st["queries"]["market"]
    assert out["flow_sync"]["md_added"].startswith(f"## MI · {d['code']} v1\n- 시장 2 · 고객사 2 · 사용자 1")
    assert out["summary_md"].split("\n")[1:] == ["- 시장 2 · 고객사 2 · 사용자 1", "- 출처 5 · 확인 필요 수치 2"]   # 보드 MI_Done 요약 줄
    flow = (await env.sb.get(f"/v1/flows/{sb}")).json()
    mi = flow["stages"]["mi"]
    assert mi["ref"] == d["code"] and mi["items"][0]["summary"] == "프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석"
    assert set(mi["items"][0]) == {"id", "group", "summary", "source", "kept", "addedIn", "numberCheck"}
    cell = next(c for c in flow["cells"] if c["key"] == "mi")
    assert cell["state"] == "done" and cell["route"] == f"/mi/flow/{fid}"
    assert flow["cards"]["mi"]["facts"][0] == ["담은 정보", "5"]
    lst = (await env.sb.get("/v1/flows/contents/mi")).json()["items"]
    assert lst[0]["route"] == f"/mi/flow/{fid}" and lst[0]["title"] == "용산 AI Ready 오피스 시장 분석"

    # 고쳐 저장(Gate 「수정」): 다시 분석 → 이전 검색어 유지 + 담은 정보 유지 · 새로 찾은 것만 더하기 → v2 · prevVer 1
    WEB["임대 동향"] += " 부동산 리서치 2026-09 리포트에 따르면 신축 오피스 임차인은 친환경 인증을 우선한다."
    d = (await env.c.post(f"/v1/mi-flows/{fid}:analyze")).json()
    assert d["editing"] is True and d["phase"] == "analyzing"
    await env.drain()
    d = (await env.c.get(f"/v1/mi-flows/{fid}")).json()
    assert [q["by"] for q in d["queries"]["market"]][:2] == ["ai", "ai"] and d["queries"]["market"][2] == {"text": "건물 에너지 효율 규제", "on": False, "by": "manual"}
    await env.c.post(f"/v1/mi-flows/{fid}:search")
    await env.drain()
    d = (await env.c.get(f"/v1/mi-flows/{fid}")).json()
    tags = {x["summary"]: x["addedIn"] for x in d["items"]}
    assert tags["프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석"] == "v1"
    assert tags["신축 오피스 임차인은 친환경 인증을 우선한다."] == "v2"
    assert "오피스 로비를 브랜드 공간으로 바꾸는 사례가 늘고 있다." in tags    # 지난번 뺀 것도 다시 찾음(새로 찾음)
    market = [(x["summary"][:8], x["addedIn"]) for x in d["items"] if x["group"] == "시장"]
    assert market == [("프라임 오피스에", "v1"), ("오피스 로비를 ", "v2"), ("서울 도심 신축", "v1"), ("신축 오피스 임", "v2")]   # 찾은 순서(유지 · 새로 찾음 섞임)
    out = (await env.c.post(f"/v1/mi-flows/{fid}:finish")).json()
    assert out["stage"]["ver"] == 2 and out["stage"]["prevVer"] == 1
    assert "(+2)" in out["summary_md"].split("\n")[1]
    flow = (await env.sb.get(f"/v1/flows/{sb}")).json()
    assert flow["stages"]["mi"]["ver"] == 2 and flow["stages"]["mi"]["prevVer"] == 1


async def test_sources_mode_uses_returned_urls(flow_env):
    env = flow_env
    env.ai.return_sources = True
    from winmate_mi import aix
    aix.reset_caps()
    d = await _ready(env, await _storyboard(env.sb))
    await env.c.post(f"/v1/mi-flows/{d['id']}:search")
    await env.drain()
    d = (await env.c.get(f"/v1/mi-flows/{d['id']}")).json()
    assert d["items"] and all(x["source"]["url"].startswith("https://news.example.com/") for x in d["items"])
    assert all(x["source"]["name"] == "news.example.com" and x["source"]["type"] == "뉴스" for x in d["items"])
    # 담은 게 없으면 저장 못 함
    for x in d["items"]:
        await env.c.patch(f"/v1/mi-flows/{d['id']}/items/{x['id']}", json={"kept": False})
    r = await env.c.post(f"/v1/mi-flows/{d['id']}:finish")
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_ITEMS"


async def test_list_and_branch_gets_new_code(flow_env):
    env = flow_env
    sb = await _storyboard(env.sb)
    a = await _ready(env, sb)
    b = (await env.sb.post(f"/v1/flows/{sb}:branch", json={"stage": "mi"})).json()
    c = await _ready(env, b["id"])
    assert a["code"] != c["code"] and c["sb_id"] == b["id"]
    items = (await env.c.get("/v1/mi-flows")).json()["items"]
    assert {i["id"] for i in items} >= {a["id"], c["id"]}
