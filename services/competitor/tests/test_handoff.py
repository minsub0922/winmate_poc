"""보내기(CA5) · 묶음 · ProposalHandoff · 자동 실행 — AC-CA-42 ~ 47 · 53 ~ 55."""
from __future__ import annotations

import json
from typing import Any

from ca_scenario import NAMES, SIGNALS, analyze, find, use_a_coffee, use_facts
from winmate_common import testing
from winmate_competitor import bundle
from winmate_competitor import store as R


def blob(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False)


async def done_analysis(env, *, swap: bool = False) -> str:
    """후보 A~F, 켜진 4곳 분석 완료. swap=True 면 B 끄고 E 켬(켜진 곳 A · C · D · E)."""
    use_a_coffee(env)
    aid = await find(env)
    if swap:
        items = {c["letter"]: c for c in (await env.c.get(f"/v1/analyses/{aid}/candidates")).json()["items"]}
        await env.c.patch(f"/v1/analyses/{aid}/candidates/{items['B']['id']}", json={"on": False})
        await env.c.patch(f"/v1/analyses/{aid}/candidates/{items['E']['id']}", json={"on": True})
    use_facts(env)
    a = await analyze(env, aid)
    assert a["status"] == "done", a
    return aid


def real_names_in(text: str, extra: list[str] | None = None) -> list[str]:
    return [n for n in NAMES + (extra or []) if n in text]


# ── AC-CA-42 MI 로 합치기(경쟁사 쪽) ─────────────────────
async def test_ac42_mi_handoff_record(env):
    aid = await done_analysis(env)
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "mi", "target_id": "mi_01X", "target_title": "A 커피 MI"})
    assert r.status_code == 200, r.text
    h = r.json()
    assert h["named"] is True and h["status"] == "prepared" and h["handoff_id"]
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle", params={"target": "mi", "handoff_id": h["handoff_id"]})).json()
    assert set(real_names_in(blob(b))) == set(NAMES[:4])                    # MI 묶음은 실명 포함
    r = await env.c.patch(f"/v1/analyses/{aid}/handoffs/{h['handoff_id']}", json={"status": "delivered", "target_id": "mi_01X"})
    assert r.status_code == 200 and r.json()["status"] == "delivered"
    lst = (await env.c.get("/v1/analyses")).json()
    assert next(x for x in lst["items"] if x["id"] == aid)["sent_label"] == "MI 작업"
    hs = (await env.c.get(f"/v1/analyses/{aid}/handoffs")).json()["items"]
    assert [x["target"] for x in hs] == ["mi"]


async def test_handoff_before_result_404(env):
    use_a_coffee(env)
    aid = await find(env)
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "mi"})
    assert r.status_code == 404
    r = await env.c.get(f"/v1/analyses/{aid}/bundle", params={"target": "proposal_why"})
    assert r.status_code == 404


# ── AC-CA-43 익명 묶음 ──────────────────────────────────
async def test_ac43_proposal_bundle_anonymous(env):
    aid = await done_analysis(env, swap=True)
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["letters_on"] == ["A", "C", "D", "E"]
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle", params={"target": "proposal_why"})).json()
    text = blob(b)
    assert real_names_in(text) == []
    assert "cautions" not in b or not b["cautions"]
    assert "real_name" not in text and "aliases" not in text
    assert b["comparison"]["columns"] == ["경쟁사 A", "경쟁사 B", "경쟁사 C", "경쟁사 D", "삼성"]       # 켜진 A · C · D · E → 연속 글자
    assert b["named"] is False and b["strengths"]


# ── AC-CA-44 실명 · 묻기 2 ──────────────────────────────
async def test_ac44_real_names_ask(env):
    aid = await done_analysis(env)
    r = await env.c.patch(f"/v1/analyses/{aid}", json={"anonymize": False})
    assert r.status_code == 200 and r.json()["anonymize"] is False
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_why", "target_id": "prp_1"})
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "ASK_REQUIRED" and err["details"]["kind"] == "real_names"
    assert err["details"]["asks"][0]["options"] == ["익명으로 보내기", "실명으로 보내기"]
    # 익명으로 보내기
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_why", "target_id": "prp_1", "confirm": {"real_names": False}})
    h = r.json()
    assert r.status_code == 200 and h["named"] is False
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle", params={"target": "proposal_why", "handoff_id": h["handoff_id"]})).json()
    assert real_names_in(blob(b)) == []
    # 실명으로 보내기
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_why", "target_id": "prp_1", "confirm": {"real_names": True}})
    h2 = r.json()
    assert h2["named"] is True
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle", params={"target": "proposal_why", "handoff_id": h2["handoff_id"]})).json()
    assert set(real_names_in(blob(b))) == set(NAMES[:4])
    # 익명이 켜져 있으면 묻지 않는다
    await env.c.patch(f"/v1/analyses/{aid}", json={"anonymize": True})
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_why", "dry_run": True})
    assert r.status_code == 200 and r.json()["named"] is False and r.json()["handoff_id"] is None


# ── AC-CA-45 Storyboard ─────────────────────────────────
async def test_ac45_storyboard_bundle(env):
    aid = await done_analysis(env)
    crit = (await env.c.get(f"/v1/analyses/{aid}/criteria")).json()["items"]
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle", params={"target": "storyboard"})).json()
    assert [(c["name"], c["importance"]) for c in b["criteria"]] == [(c["name"], c["importance"]) for c in crit if c["enabled"]]
    assert b["competitors"] == ["경쟁사 A", "경쟁사 B", "경쟁사 C", "경쟁사 D"]
    assert real_names_in(blob(b)) == []


# ── AC-CA-46 리포트(사내용 실명) ─────────────────────────
async def test_ac46_report_document_has_real_names(env):
    aid = await done_analysis(env)
    doc = await R.call(R.get_analysis, aid)
    v = await R.call(R.get_version, aid, int(doc["result_version"]))
    rep = bundle.report_document(doc, v, audience="internal")
    text = blob(rep)
    assert set(real_names_in(text)) == set(NAMES[:4])
    assert "사내용 · 고객 제출 금지" in text
    cust = bundle.report_document(doc, v, audience="customer")
    assert real_names_in(blob(cust)) == []


async def test_export_validation(env):
    aid = await done_analysis(env)
    r = await env.c.post(f"/v1/analyses/{aid}/exports", json={"format": "pdf", "audience": "internal"})
    assert r.status_code == 202 and r.json()["job_id"]


# ── AC-CA-47 실명이 없는 곳 ─────────────────────────────
async def test_ac47_no_real_names_in_index_list_banner(env):
    aid = await done_analysis(env)
    lst = (await env.c.get("/v1/analyses")).json()
    assert real_names_in(blob(lst)) == []
    async with testing.api_client(env.apps["workspace"]) as ws:
        items = (await ws.get("/v1/items", params={"feature": "CA", "limit": 50})).json()["items"]
    mine = [x for x in items if aid in blob(x)]
    assert mine, items
    assert real_names_in(blob(mine)) == []
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert real_names_in(a["title"]) == []


# ── AC-CA-53 ProposalHandoff ────────────────────────────
async def test_ac53_proposal_handoff_anonymous(env):
    aid = await done_analysis(env, swap=True)
    ph = (await env.c.get(f"/v1/analyses/{aid}/proposal-handoff", params={"section": "why"})).json()
    assert [i["key"] for i in ph["items"]] == ["CM", "ST"]
    cm = ph["items"][0]
    assert cm["content"]["columns"] == ["경쟁사 A", "경쟁사 B", "경쟁사 C", "경쟁사 D", "삼성"]
    text = blob(ph)
    assert real_names_in(text) == [] and "cautions" not in text and "aliases" not in text
    assert ph["source"]["feature"] == "CA" and ph["source"]["route"] == f"/competitor/{aid}/result"
    assert ph["target"] == {"proposal_type": "standard", "section_key": "why"}
    assert ph["named"] is False
    # 사실 목록: 확인 안 된 값은 placeholder
    assert all(f["status"] in ("confirmed", "unconfirmed", "placeholder") for f in ph["facts"])


# ── AC-CA-54 실명 ProposalHandoff ───────────────────────
async def test_ac54_named_requires_confirmation(env):
    aid = await done_analysis(env)
    r = await env.c.get(f"/v1/analyses/{aid}/proposal-handoff", params={"named": "true"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "ASK_REQUIRED"
    assert r.json()["error"]["details"]["kind"] == "real_names"
    await env.c.patch(f"/v1/analyses/{aid}", json={"anonymize": False})
    h = (await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_why", "confirm": {"real_names": True}})).json()
    r = await env.c.get(f"/v1/analyses/{aid}/proposal-handoff", params={"named": "true", "handoff_id": h["handoff_id"]})
    assert r.status_code == 200
    assert set(real_names_in(blob(r.json()))) == set(NAMES[:4]) and r.json()["named"] is True
    hs = (await env.c.get(f"/v1/analyses/{aid}/handoffs")).json()["items"]
    rec = next(x for x in hs if x["id"] == h["handoff_id"])
    assert len(rec["served_named_at"]) == 1


# ── AC-CA-55 자동 실행 ──────────────────────────────────
async def test_ac55_auto_run(env):
    names = NAMES[:3]
    use_a_coffee(env, names=names, signals=[SIGNALS[0], SIGNALS[3], SIGNALS[4]])
    env.rq.add("rq_01AUTO", customer="A 커피 프랜차이즈", items=["본사에서 전 매장 메뉴 콘텐츠를 일괄 배포", "매장별 가격 표시", "전기료 절감"],
               vertical={"top2": [{"id": "kr_fnb", "name": "요식", "score": 0.9}], "ask": False}, spaces=["직영점"], products=["스마트 LCD 사이니지"])
    use_facts(env)
    r = await env.c.post("/v1/analyses", json={"auto_run": True, "requirements_id": "rq_01AUTO"})
    assert r.status_code == 202, r.text
    body = r.json()
    aid, job_id = body["analysis_id"], body["job_id"]
    await env.drain()
    ev = await env.events(job_id)
    assert not any(e["type"] == "awaiting_input" for e in ev)
    j = await env.job(job_id)
    assert j.status == "succeeded" and j.result["next_job_id"]
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "done", a
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert [x["real_name"] for x in res["competitors"]] == names[:2]
    assert "후보 자동 확정" in [c["label"] for c in res["chips"]]


async def test_auto_run_requires_input(env):
    r = await env.c.post("/v1/analyses", json={"auto_run": True})
    assert r.status_code == 422 and r.json()["error"]["code"] == "EMPTY_INPUT"
