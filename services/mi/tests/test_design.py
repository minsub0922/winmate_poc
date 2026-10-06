"""설계(mi.design) — AC-MI-02 · 03 · 04 · 06 · 07 · 08 · 09 · 10 · 11 · 12 · 14 · 15 · 16 · 17 · 18 · 84 · 86 · 93."""
from __future__ import annotations

from typing import Any

from mi_scenario import A_REQ, create, design, setup_fb

from winmate_common.jobs import jobs

H_REQ = "H 호텔 로비 라운지 카페 메뉴보드 · 투숙객 대기 동선 · 경쟁사 대비 운영 효율"


def setup_ask(env: Any) -> None:
    setup_fb(env)
    env.kb.set_conf({"HT": 0.58, "FB": 0.55}, clues={"HT": ["로비", "투숙객"], "FB": ["메뉴보드"]})

    def classify(body: dict[str, Any]) -> dict[str, Any]:
        prompt = body["messages"][-1]["content"]
        if "결재는 호텔 F&B 팀장" in prompt:
            return {"segments": [{"code": "HT", "p": 0.66, "clues": ["로비"]}, {"code": "FB", "p": 0.52, "clues": ["메뉴보드"]}]}
        return {"segments": [{"code": "HT", "p": 0.58, "clues": ["로비", "투숙객"]}, {"code": "FB", "p": 0.55, "clues": ["메뉴보드"]}]}

    env.ai.llm["mi.classify_segment"] = classify


async def _design_job(env: Any, aid: str) -> str:
    r = await env.c.post(f"/v1/analyses/{aid}/design")
    assert r.status_code == 202, r.text
    jid = r.json()["job_id"]
    await env.drain()
    return jid


async def test_ac02_auto_segment(env):
    setup_fb(env)
    aid = (await create(env))["id"]
    jid = await _design_job(env, aid)
    d = (await env.c.get(f"/v1/analyses/{aid}/design")).json()
    seg = next(x for x in d["decisions"] if x["key"] == "segment")
    assert seg["display_value"] == "외식 · 카페 (FB) · 0.94" and seg["mode"] == "auto"
    assert "awaiting_input" not in [e["type"] for e in await env.events(jid)]
    assert d["status"] == "done" and len(d["decisions"]) == 7
    # 쓰임 · 표기 · 범위 근거(보드 문구)
    by = {x["key"]: x for x in d["decisions"]}
    assert by["usage"]["display_value"] == "표준 MI 섹션 · 3시트" and by["usage"]["reason"] == "표준 제안서 'A 커피 메뉴보드'에 연결됨"
    assert by["scope"]["reason"] == "요구에 '경쟁사 대비' · '주문 대기' 있음"
    assert by["naming"]["display_value"] == "익명 (경쟁사 A · B · C)" and by["naming"]["reason"] == "고객에게 내는 제안서라 기본값 익명"
    assert by["depth"]["display_value"] == "약 3분 · 출처 30곳 내외"
    assert [s["code"] for s in d["sheets_preview"]] == ["MI-FB-A", "MI-FB-B", "CP-A"]
    assert d["tally"] == {"auto": 6, "check": 1, "ask": 0}


async def test_ac03_check_segment_chip(env):
    setup_fb(env)
    env.kb.set_conf({"FB": 0.71, "RT": 0.55})
    env.ai.llm["mi.classify_segment"] = {"segments": [{"code": "FB", "p": 0.71, "clues": []}, {"code": "RT", "p": 0.55, "clues": []}]}
    aid = (await create(env))["id"]
    await design(env, aid)
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["segment"]["code"] == "FB" and a["segment"]["mode"] == "check"
    from winmate_mi import views

    chips = views.check_chips(a | {"decisions": {}}, {})
    assert chips[0]["label"] == "업종 · 외식 · 카페 0.71" and chips[0]["mode"] == "check"


async def test_ac04_ask_segment_and_ac09_answer(env):
    setup_ask(env)
    aid = (await create(env, requirements_text=H_REQ, customer_name="H 호텔"))["id"]
    jid = await _design_job(env, aid)
    job = await env.job(jid)
    assert job.status == "awaiting_input"
    req = job.input_request
    assert req["kind"] == "segment_choice" and req["diff"] == 0.03
    assert [o["key"] for o in req["options"]] == ["HT", "FB", "MIX"]
    assert req["options"][0]["recommended"] and req["options"][2]["score"] == 0.57
    assert req["options"][0]["desc"].startswith("호텔 운영 관점 — 로비 · 객실 경험, 투숙객 여정, 호텔 매출 구조.")
    assert req["default_text"] == "답이 없으면 추천(호텔 · 리조트)으로 진행하고, 결과 화면의 업종 칩에서 언제든 바꿀 수 있어요."
    assert any(d.startswith("사내 자료 · 호텔 ") and "+ 외식 " in d for d in req["done"])
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "ask" and a["route"].endswith("/design/industry") is False or a["status"] == "ask"
    d = (await env.c.get(f"/v1/analyses/{aid}/design")).json()
    assert d["status"] == "ask" and d["ask"]["kind"] == "segment_choice"
    # AC-MI-09 — FB 로 답하고 분석 시작
    await jobs().provide_input(jid, {"segment": "FB", "start_analysis": True})
    await env.drain()
    job = await env.job(jid)
    assert job.status == "succeeded" and job.result.get("next_job_id")
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["segment"]["code"] == "FB" and a["segment"]["mode"] == "pin"
    nxt = await env.job(job.result["next_job_id"])
    assert nxt.kind == "mi.analyze" and nxt.status == "succeeded"


async def test_ac10_mix(env):
    setup_ask(env)
    aid = (await create(env, requirements_text=H_REQ, customer_name="H 호텔"))["id"]
    jid = await _design_job(env, aid)
    await jobs().provide_input(jid, {"segment": "MIX"})
    await env.drain()
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["segment"]["mix"] == {"a": "HT", "b": "HT", "c": "FB"}
    d = (await env.c.get(f"/v1/analyses/{aid}/design")).json()
    assert [s["code"] for s in d["sheets_preview"]] == ["MI-HT-A", "MI-HT-B", "MI-FB-C"]
    assert d["status"] == "done"


async def test_ac11_hint_reclassifies_and_asks_again(env):
    setup_ask(env)
    aid = (await create(env, requirements_text=H_REQ, customer_name="H 호텔"))["id"]
    jid = await _design_job(env, aid)
    r = await env.c.post(f"/v1/analyses/{aid}/design/memo", json={"text": "결재는 호텔 F&B 팀장"})
    assert r.status_code == 202 and r.json()["job_id"] == jid
    await env.drain()
    job = await env.job(jid)
    assert job.status == "awaiting_input"
    assert job.input_request["options"][0]["score"] == 0.62      # 0.5 × 0.66 + 0.3 × 0.58 + 0.2 × 0.58
    calls = env.ai.llm_calls("mi.classify_segment")
    assert len(calls) == 2 and "결재는 호텔 F&B 팀장" in calls[-1]["prompt"]
    assert sum(1 for e in await env.events(jid) if e["type"] == "awaiting_input") == 2
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "ask"


async def test_ac93_auto_run_no_ask(env):
    setup_ask(env)
    r = await env.c.post("/v1/analyses", json={"customer_name": "H 호텔", "requirements_text": H_REQ, "auto_run": True,
                                                "links": {"proposal_id": "prp_x", "proposal_type": "standard", "proposal_title": "H 호텔"}})
    assert r.status_code == 202
    body = r.json()
    await env.drain()
    job = await env.job(body["job_id"])
    assert job.status == "succeeded" and job.result.get("next_job_id")
    assert "awaiting_input" not in [e["type"] for e in await env.events(body["job_id"])]
    a = (await env.c.get(f"/v1/analyses/{body['analysis_id']}")).json()
    assert a["segment"]["code"] == "HT" and a["segment"]["mode"] == "check"
    assert (await env.job(job.result["next_job_id"])).kind == "mi.analyze"


async def test_ac06_gen_segment(env):
    setup_fb(env)
    env.kb.set_conf({"FB": 0.3, "RT": 0.2})
    env.ai.llm["mi.classify_segment"] = {"segments": [{"code": "FB", "p": 0.3, "clues": []}, {"code": "RT", "p": 0.2, "clues": []}], "out_of_scope": True}
    aid = (await create(env))["id"]
    d = await design(env, aid)
    seg = next(x for x in d["decisions"] if x["key"] == "segment")
    assert seg["display_value"] == "범용 · 16개 업종 밖" and seg["mode"] == "auto"
    assert not any(s["code"].startswith("MI-") for s in d["sheets_preview"])


async def test_ac07_inherit_from_storyboard(env):
    setup_fb(env)
    aid = (await create(env, requirements_text=""))["id"]
    r = await env.c.post(f"/v1/analyses/{aid}/imports/storyboard", json={"storyboard_id": "sb_1", "title": "B 병원 안내", "segment": "MD",
                                                                         "requirements": [{"text": "병원 안내 시스템 개선"}], "key_messages": ["대기 시간 단축"]})
    assert r.status_code == 200, r.text
    d = await design(env, aid)
    assert env.ai.llm_calls("mi.classify_segment") == []
    seg = next(x for x in d["decisions"] if x["key"] == "segment")
    assert seg["mode"] == "auto" and seg["display_value"].endswith("· 상속") and seg["reason"] == "연결된 Storyboard에 업종이 있음"


async def test_ac08_preset_pin_survives_memo(env):
    setup_fb(env)
    ins = (await env.c.get("/v1/segments/FB/insights")).json()
    items = [r["label"] for r in ins["req_types"][:4]]
    r = await env.c.post("/v1/analyses", json={"customer_name": "A 커피", "preset": {"segment": "FB", "req_items": items}})
    a = r.json()
    # AC-MI-84 — 프리셋 요구 4개 · 같은 4개 기준 · 업종 고정 · MI2 로
    assert [q["origin"] for q in a["requirements"]] == ["preset"] * 4
    assert len(a["criteria"]) == 4 and all(c["source_label"].startswith("업종 사례 ") for c in a["criteria"])
    assert a["segment"]["mode"] == "pin" and a["route"].endswith("/scope")
    r = await env.c.post(f"/v1/analyses/{a['id']}/design/memo", json={"text": "업종은 호텔로 봐줘"})
    assert r.status_code == 202
    await env.drain()
    doc = (await env.c.get(f"/v1/analyses/{a['id']}")).json()
    assert doc["segment"]["code"] == "FB" and doc["segment"]["mode"] == "pin"
    d = (await env.c.get(f"/v1/analyses/{a['id']}/design")).json()
    assert next(x for x in d["decisions"] if x["key"] == "segment")["mode"] == "pin"


async def test_ac12_keywords_add_areas(env):
    setup_fb(env)
    env.ai.llm["mi.decide_scope"] = {"areas": {"market": {"include": True, "reason": "시장"}, "customer": {"include": True, "reason": "고객"},
                                               "user": {"include": False, "reason": ""}, "competitor": {"include": False, "reason": ""}}}
    aid = (await create(env, requirements_text="…경쟁사 대비… 주문 대기…"))["id"]
    await design(env, aid)
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["scope"]["areas"] == ["market", "customer", "user", "competitor"]
    d = (await env.c.get(f"/v1/analyses/{aid}/design")).json()
    assert next(x for x in d["decisions"] if x["key"] == "scope")["reason"] == "요구에 '경쟁사 대비' · '주문 대기' 있음"


async def test_ac13_customer_reduced_by_public_docs(env):
    setup_fb(env)
    env.ai.llm["mi.public_docs"] = {"documents": ["2025 사업보고서", "2026년 IR 자료"]}
    aid = (await create(env))["id"]
    await design(env, aid)
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["scope"]["reduced"] == ["customer"]
    d = (await env.c.get(f"/v1/analyses/{aid}/design")).json()
    assert [s["code"] for s in d["sheets_preview"]] == ["MI-FB-A", "CB-A", "CP-A"]


async def test_ac14_auto_competitors(env):
    setup_fb(env)
    aid = (await create(env))["id"]
    d = await design(env, aid)
    comp = next(x for x in d["decisions"] if x["key"] == "competitors")
    assert comp["mode"] == "check" and comp["reason"] == "지정 없음 → 외식 · 카페 사례 빈도 상위 3" and comp["display_value"] == "경쟁사 A · B · C"
    lst = (await env.c.get(f"/v1/analyses/{aid}/competitors")).json()
    assert [c["real_name"] for c in lst["items"]] == ["가나 디스플레이", "다라 사이니지", "마바 미디어"]   # 요약에 없는 '지어낸 전자'는 없다
    assert all(c["confidence"] >= 0.5 and c["tag"] == "자동 추천" for c in lst["items"])


async def test_ac15_ac16_usage_and_naming(env):
    setup_fb(env)
    a1 = (await create(env, links={}))["id"]
    await design(env, a1)
    doc = (await env.c.get(f"/v1/analyses/{a1}")).json()
    assert doc["usage"]["value"] == "none" and doc["anonymize"] is False
    a2 = (await create(env))["id"]
    await design(env, a2)
    assert (await env.c.get(f"/v1/analyses/{a2}")).json()["anonymize"] is True
    a3 = (await create(env, links={"proposal_id": "p3", "proposal_type": "solution", "proposal_title": "E 대학교"}))["id"]
    d3 = await design(env, a3)
    doc3 = (await env.c.get(f"/v1/analyses/{a3}")).json()
    assert doc3["usage"]["value"] == "solution" and doc3["depth"]["target_sources"] == 60 and "IM-A" in [s["code"] for s in d3["sheets_preview"]]
    a4 = (await create(env, links={"proposal_id": "p4", "proposal_type": "quickwin", "proposal_title": "U 통신사"}))["id"]
    d4 = await design(env, a4)
    assert d4["sheets_preview"] == []
    a5 = (await create(env, links={}, requirements_text=A_REQ + " · 경영진 한 장으로 보고"))["id"]
    d5 = await design(env, a5)
    doc5 = (await env.c.get(f"/v1/analyses/{a5}")).json()
    assert doc5["usage"]["value"] == "exec_onepager"
    assert [s["code"] for s in d5["sheets_preview"]] == ["IM-B", "MS-A", "CP-A"]


async def test_ac17_one_line_memo_inferred(env):
    setup_fb(env)
    env.kb.set_conf({"FB": 0.2, "RT": 0.1})
    env.ai.llm["mi.classify_segment"] = {"segments": [{"code": "FB", "p": 0.2, "clues": []}], "out_of_scope": True}
    env.ai.llm["mi.extract_requirements"] = {"requirements": []}
    r = await env.c.post("/v1/analyses", json={"requirements_text": "스크린골프장 체인 매장 사이니지"})
    aid = r.json()["id"]
    await design(env, aid)
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    inferred = [q for q in a["requirements"] if q["origin"] == "inferred"]
    assert 1 <= len(inferred) <= 3 and all(q["inferred"] for q in inferred)
    d = (await env.c.get(f"/v1/analyses/{aid}/design")).json()
    assert next(x for x in d["decisions"] if x["key"] == "scope")["mode"] == "check"
    from winmate_mi import views

    chips = views.check_chips(a, {})
    assert any(c["label"] == f"빈칸 추론 {len(inferred)}" for c in chips)


async def test_ac18_scope_pin_keeps_other_decisions(env):
    setup_fb(env)
    aid = (await create(env))["id"]
    d1 = await design(env, aid)
    by1 = {x["key"]: x for x in d1["decisions"]}
    r = await env.c.patch(f"/v1/analyses/{aid}", json={"scope": {"areas": ["market", "competitor"]}})
    assert r.status_code == 200
    d2 = (await env.c.get(f"/v1/analyses/{aid}/design")).json()
    by2 = {x["key"]: x for x in d2["decisions"]}
    assert by2["scope"]["mode"] == "pin" and by2["scope"]["display_value"] == "시장 · 경쟁"
    assert by2["segment"]["updated_at"] == by1["segment"]["updated_at"] and by2["usage"]["updated_at"] == by1["usage"]["updated_at"]
    assert [s["code"] for s in d2["sheets_preview"]] == ["MI-FB-A", "CP-A"]
    assert by2["depth"]["display_value"] == "약 2분 · 출처 30곳 내외"


async def test_ac86_customer_only_creates_draft(env):
    r = await env.c.post("/v1/analyses", json={"customer_name": "A 커피"})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    r2 = await env.c.post(f"/v1/analyses/{r.json()['id']}/design")
    assert r2.status_code == 202
    r3 = await env.c.post("/v1/analyses", json={})
    r4 = await env.c.post(f"/v1/analyses/{r3.json()['id']}/design")
    assert r4.status_code == 422
