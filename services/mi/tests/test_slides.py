"""시트 구성 · 레이아웃(MI3P · MI3L) — AC-MI-13 · 59 · 60 · 61 · 62 · 63 · 64."""
from __future__ import annotations

import re
from typing import Any

from mi_scenario import NEW_COMPS, add_qm55c, create, design, full_fb, run, setup_fb


async def _slides(env: Any, aid: str) -> dict[str, Any]:
    return (await env.c.get(f"/v1/analyses/{aid}/slides")).json()


async def test_ac64_standard_four_areas(env):
    aid = await full_fb(env)
    sv = await _slides(env, aid)
    rows = {r["sheet_type"]: r for r in sv["rows"]}
    assert rows["MS+TR"]["sheet_name"] == "시장 · 트렌드" and rows["MS+TR"]["template_code"] == "MI-FB-A" and rows["MS+TR"]["included"]
    assert rows["CB"]["template_code"] == "MI-FB-B" and rows["CB"]["included"] and rows["CB"]["include_mode"] == "auto"
    assert rows["CP"]["template_code"].startswith("CP-") and rows["CP"]["included"] and not rows["CP"]["industry_layout"]
    assert rows["US"]["included"] is False and rows["US"]["include_mode"] == "check" and rows["US"]["why"].startswith("섹션엔 없지만")
    assert rows["IM"]["included"] is False and rows["IM"]["include_mode"] == "auto"
    assert rows["IM"]["why"] == "표준은 3시트라 뺐어요 · Solution형이거나 경영진 보고면 자동으로 넣어요"
    assert sv["header"]["title"] == "표준 MI 섹션 3시트 + 넣으면 좋은 시트 1"
    assert rows["CP"]["why"].startswith("업종 틀엔 경쟁 장이 없어 범용 · 경쟁사 3곳 × 요구 기준 4개라")
    assert rows["MS+TR"]["why"].startswith("업종 레이아웃 우선 · ")


async def test_ac59_industry_layout_with_six_years(env):
    setup_fb(env)
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    vals = ["3,100", "3,600", "4,200", "5,000", "5,800", "6,700"]
    env.ai.web["mi.web_market"] = {"summary": "국내 F&B 디지털 사이니지 시장 규모는 " + ", ".join(f"{y}년 {v}억 원" for y, v in zip(years, vals)) + "이다. 2026년 3월 자료."}
    claims = [{"local_id": f"y{y}", "text": f"{y}년 시장 규모는 {v}억 원이에요.", "metric_key": f"size_{y}", "citations": [{"evidence_id": "E1", "quote": f"{y}년 {v}억 원"}]}
              for y, v in zip(years, vals)]
    claims += [{"local_id": f"t{i}", "text": f"트렌드 {i}", "citations": []} for i in range(4)]
    env.ai.llm["mi.extract_claims_market"] = lambda _b: {"blocks": {"size_label": "시장", "size_unit": "억 원", "size_series": [{"year": y, "claim": f"y{y}"} for y in years],
                                                                    "trends": [{"title": f"트렌드 {i}", "when": f"202{i}", "claim": f"t{i}"} for i in range(4)],
                                                                    "regulations": []}, "claims": claims}
    aid = (await create(env))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    await run(env, aid)
    rows = {r["sheet_type"]: r for r in (await _slides(env, aid))["rows"]}
    ms = rows["MS+TR"]
    assert ms["template_code"] == "MI-FB-A" and ms["industry_layout"] and ms["fit"] >= 0
    assert rows["CP"]["template_code"].startswith("CP-") and not rows["CP"]["industry_layout"]


async def test_ac60_gen_ms_e(env):
    setup_fb(env)
    env.kb.set_conf({"FB": 0.2, "RT": 0.1})
    env.ai.llm["mi.classify_segment"] = {"segments": [{"code": "FB", "p": 0.2}], "out_of_scope": True}
    env.ai.web["mi.web_market"] = {"summary": "스크린골프장은 가족 단위 이용이 늘고 있다. 무인 운영 매장이 확산되고 있다."}
    env.ai.llm["mi.extract_claims_market"] = lambda _b: {
        "blocks": {"size_label": "", "size_unit": "억 원", "size_series": [], "trends": [{"title": "가족 단위 이용", "claim": "a"}, {"title": "무인 운영", "claim": "b"}],
                   "regulations": []},
        "claims": [{"local_id": "a", "text": "가족 단위 이용이 늘고 있어요.", "citations": [{"evidence_id": "E1", "quote": "가족 단위 이용이 늘고 있다"}]},
                   {"local_id": "b", "text": "무인 운영 매장이 확산되고 있어요.", "citations": [{"evidence_id": "E1", "quote": "무인 운영 매장이 확산되고 있다"}]}]}
    aid = (await create(env, customer_name="J 스크린골프", requirements_text="스크린골프장 체인 매장 사이니지", links={}))["id"]
    await env.c.patch(f"/v1/analyses/{aid}", json={"scope": {"areas": ["market", "user"]}})
    await design(env, aid)
    env.ai.reset_calls()
    await run(env, aid)
    assert env.ai.web_calls("mi.web_layout")                  # 그 데이터만 1회 추가 검색
    ms = next(r for r in (await _slides(env, aid))["rows"] if r["area"] == "market")
    assert ms["template_code"] == "MS-E" and ms["why"]
    fx = (await env.c.get(f"/v1/analyses/{aid}/fix-items")).json()["items"]
    assert any(f["metric_key"] == "market_size" and f["status"] == "warn" for f in fx)


async def test_ac61_ac62_layout_candidates_and_option_a(env):
    aid = await full_fb(env)
    cp = next(r for r in (await _slides(env, aid))["rows"] if r["sheet_type"] == "CP")
    assert cp["template_code"] == "CP-A" and cp["fit"] >= 85
    cv = (await env.c.get(f"/v1/analyses/{aid}/slides/{cp['id']}/candidates?requested=CP-B")).json()
    t = {x["code"]: x for x in cv["templates"]}
    assert t["CP-A"]["fit"] >= 85 and t["CP-A"]["tag"] == "사용 중"
    assert 0 <= t["CP-B"]["fit"] < 85 and t["CP-B"]["tag"] == "요청"
    assert t["CP-C"]["fit"] == -1 and t["CP-C"]["fit_label"] == "점유율 자료가 있으면 열려요" and t["CP-C"]["tag"] == "고를 수 없음"
    opts = {o["key"]: o for o in cv["options"]}
    assert opts["A"]["recommended"] and opts["A"]["predicted_fit"] >= 85 and opts["A"]["title"] == "공급사 3곳 더 찾아 6곳으로 → CP-B"
    assert opts["B"]["title"] == "3곳 그대로 CP-B" and opts["C"]["title"] == "비교표 CP-A 유지"
    assert cv["head"] == "경쟁 환경 · 고를 수 있는 레이아웃 · 업종 틀엔 경쟁 장이 없어 범용 3종"
    # AC-MI-62 — 선택지 A: 공급사를 6곳으로 늘리고 CP-B 로
    env.ai.web["mi.web_layout"] = {"summary": "그 밖의 메뉴보드 공급사로 " + ", ".join(NEW_COMPS) + "가 있다."}
    pool = list(NEW_COMPS) + ["가나 디스플레이"]

    def cands(body: dict[str, Any]) -> dict[str, Any]:
        prompt = body["messages"][-1]["content"]
        return {"items": [{"name": n, "aliases": [], "kind_label": "사이니지", "desc": "", "confidence": 0.7, "quote": ""} for n in pool if n in prompt]}

    env.ai.llm["mi.competitor_candidates"] = cands
    r = await env.c.post(f"/v1/analyses/{aid}/slides/{cp['id']}/layout", json={"option": "A", "template": "CP-B", "pin": False})
    assert r.status_code == 202
    await env.drain()
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["version"] == 2 and len([c for c in a["competitors"] if not c["removed"]]) == 6 and a["status"] == "done"
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert res["kind"] == "layout" and len(res["competitor"]["table"]["columns"]) == 7
    cp2 = next(r for r in (await _slides(env, aid))["rows"] if r["sheet_type"] == "CP")
    assert cp2["template_code"] == "CP-B" and cp2["fit"] >= 85


async def test_ac63_pinned_sheet_kept_and_ask(env):
    aid = await full_fb(env)
    cb = next(r for r in (await _slides(env, aid))["rows"] if r["sheet_type"] == "CB")
    r = await env.c.patch(f"/v1/analyses/{aid}/slides/{cb['id']}", json={"template_code": "CB-A"})
    assert r.status_code == 200 and r.json()["pinned"] and r.json()["template_code"] == "CB-A"
    await run(env, aid, mode="full")
    cb2 = next(r for r in (await _slides(env, aid))["rows"] if r["sheet_type"] == "CB")
    assert cb2["template_code"] == "CB-A" and cb2["pinned"] and cb2["why"] == "고정한 시트라 다시 고르지 않았어요"
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi", "target_pinned_sheets": ["CP"]})
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "ASK_REQUIRED" and any(a["kind"] == "overwrite_pinned" for a in err["details"]["asks"])


async def test_ac13_reduced_customer_cb_a(env):
    setup_fb(env)
    env.ai.llm["mi.public_docs"] = {"documents": ["2025 사업보고서", "2026년 IR 자료"]}
    aid = (await create(env))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    await run(env, aid)
    cb = next(r for r in (await _slides(env, aid))["rows"] if r["sheet_type"] == "CB")
    assert cb["template_code"] == "CB-A" and cb["why"] == "고객 공개 자료가 2건이라 한 줄 요약 + 3단으로 고정했어요"


async def test_slide_request_routes_layout(env):
    aid = await full_fb(env)
    env.ai.llm["mi.slide_request"] = {"kind": "layout", "sheet_type": "CP", "template": "CP-B", "include": [], "exclude": []}
    r = await env.c.post(f"/v1/analyses/{aid}/slides/requests", json={"text": "경쟁 환경은 포지셔닝 맵으로"})
    out = r.json()
    assert out["kind"] == "layout" and out["requested"] == "CP-B" and re.match(r"sht_", out["sheet_id"])
