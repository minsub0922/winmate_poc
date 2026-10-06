"""분석 실행(mi.analyze) — AC-MI-19 · 23 · 24 · 25 · 26 · 27 · 76 · 79 · 80 · 81 · 82 · 83 · 87."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from mi_scenario import A_REQ, add_qm55c, create, design, full_fb, run, setup_fb, user_claims

from winmate_common.jobs import jobs

CONFIDENTIAL_TASKS = ("mi.classify_file", "mi.extract_requirements", "mi.classify_segment", "mi.decide_scope", "mi.title_topic", "mi.plan",
                      "mi.extract_claims_market", "mi.extract_claims_customer", "mi.extract_claims_user", "mi.compare_cells", "mi.verdicts",
                      "mi.strengths", "mi.implications", "mi.revise_interpret", "mi.answer", "mi.fix_match", "mi.fix_parse", "mi.customer_question")


async def _prepared(env: Any) -> str:
    setup_fb(env)
    aid = (await create(env))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    return aid


async def test_ac19_progress_events(env):
    aid = await _prepared(env)
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    jid = r.json()["job_id"]
    await env.drain()
    ev = await env.events(jid)
    stages = [e["data"]["stage"] for e in ev if e["type"] == "step" and "stage" in e["data"]]
    order = []
    for s in stages:
        if not order or order[-1] != s:
            order.append(s)
    assert order == ["search", "organize", "write"]
    pcts = [e["data"]["progress"] for e in ev if e["type"] == "progress"]
    assert pcts == sorted(pcts) and pcts[-1] == 100
    seen: dict[str, list[str]] = {}
    for e in ev:
        if e["type"] == "step" and "areas" in e["data"]:
            for a in e["data"]["areas"]:
                lst = seen.setdefault(a["area"], [])
                if not lst or lst[-1] != a["status"]:
                    lst.append(a["status"])
    for a in ("market", "customer", "user"):
        assert seen[a][0] == "wait" and seen[a][-1] == "done" and "run" in seen[a], (a, seen[a])
    res = next(e for e in ev if e["type"] == "result")
    assert res["data"]["version"] == 1
    assert ev[-1]["type"] == "done" and ev[-1]["data"]["status"] == "succeeded"
    prog = (await env.c.get(f"/v1/analyses/{aid}/progress")).json()
    assert prog["summary_chip"] == "분석 시작 · 4개 영역 · 경쟁사 A · B · C · 비교 기준 4개"
    assert prog["card_title"] == "시장 · 경쟁사 분석 중" and prog["card_sub"] == "4개 영역 · 경쟁사 3"


async def test_ac23_memo_during_run(env):
    aid = await _prepared(env)
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    jid = r.json()["job_id"]
    await jobs().add_memo(jid, "경쟁사 C는 클라우드 CMS 위주로")
    await env.drain()
    plan_calls = env.ai.llm_calls("mi.plan")
    assert plan_calls and "경쟁사 C는 클라우드 CMS 위주로" in plan_calls[-1]["prompt"]
    assert any("경쟁사 C는 클라우드 CMS 위주로" in c["prompt"] for c in env.ai.llm_calls("mi.extract_claims_*"))
    logs = [e["data"].get("message", "") for e in await env.events(jid) if e["type"] == "log"]
    assert any(m.startswith("메모를 반영했어요 · 경쟁사 C는") for m in logs)


async def test_ac24_cancel_and_resume(env):
    aid = await _prepared(env)
    holder: dict[str, str] = {}

    async def user_then_cancel(body: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.6)
        await jobs().cancel(holder["jid"])
        return user_claims(body)

    env.ai.llm["mi.extract_claims_user"] = user_then_cancel
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    holder["jid"] = r.json()["job_id"]
    await env.drain()
    assert (await env.job(holder["jid"])).status == "canceled"
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "stopped" and a["route"].endswith("/competitors")
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert res["stopped"] is True
    assert {t["area"]: t["status"] for t in res["tabs"]} == {"market": "done", "customer": "done", "user": "wait", "competitor": "wait"}
    # 이어서(resume) — 나머지 두 영역만 검색
    env.ai.llm["mi.extract_claims_user"] = user_claims
    env.ai.reset_calls()
    await run(env, aid, mode="resume")
    tasks = {c["task"] for c in env.ai.web_calls()}
    assert "mi.web_market" not in tasks and "mi.web_customer" not in tasks and "mi.web_user" in tasks and "mi.web_competitor" in tasks
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "done" and a["version"] == 2
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert all(t["status"] == "done" for t in res["tabs"])


async def test_ac25_user_area_fails_then_rerun(env):
    aid = await _prepared(env)
    env.ai.llm["mi.extract_claims_user"] = {"blocks": "깨진 응답", "claims": 3}
    jid = await run(env, aid)
    assert (await env.job(jid)).status == "succeeded"
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert res["failed_areas"] == ["user"] and {t["area"]: t["status"] for t in res["tabs"]}["user"] == "failed"
    assert len(env.ai.llm_calls("mi.extract_claims_user")) == 2          # 스키마 오류 → 1회 재시도
    env.ai.llm["mi.extract_claims_user"] = user_claims
    env.ai.reset_calls()
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"areas": ["user"]})
    assert r.status_code == 202
    await env.drain()
    assert {c["task"] for c in env.ai.web_calls()} == {"mi.web_user"}
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert res["failed_areas"] == [] and res["version"] == 2


async def test_ac26_websearch_unavailable(env):
    setup_fb(env)
    env.ai.web.clear()
    env.ai.web["mi.web_*"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "웹 검색 장애"}}
    aid = (await create(env))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    jid = await run(env, aid)
    assert (await env.job(jid)).status == "succeeded"
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert res["web_unavailable"] is True and res["tabs"]


async def test_ac27_weights_only_rewrites(env):
    aid = await full_fb(env)
    crit = (await env.c.get(f"/v1/analyses/{aid}/criteria")).json()["items"]
    before = [r["criterion_id"] for r in (await env.c.get(f"/v1/analyses/{aid}/result")).json()["competitor"]["table"]["rows"]]
    items = [{"id": c["id"], "name": c["name"], "weight": (1 if i == 0 else c["weight"]), "order": c["order"], "enabled": True, "source": c["source"]}
             for i, c in enumerate(crit)]
    r = await env.c.put(f"/v1/analyses/{aid}/criteria", json={"items": items})
    assert r.status_code == 200
    env.ai.reset_calls()
    await run(env, aid, mode="auto")
    assert env.ai.web_calls() == [] and env.ai.fetch_calls() == []
    assert env.ai.llm_calls("mi.strengths") and not env.ai.llm_calls("mi.extract_claims_*")
    after = [r["criterion_id"] for r in (await env.c.get(f"/v1/analyses/{aid}/result")).json()["competitor"]["table"]["rows"]]
    assert after != before and after[-1] == before[0]


async def test_ac76_recheck_schedule_replaced(env):
    aid = await full_fb(env)
    s1 = await jobs().schedules(service="mi", ref=aid)
    assert len(s1) == 1 and s1[0]["kind"] == "mi.recheck"
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    from winmate_mi import rules

    analyzed = rules.parse_iso(a["analyzed_at"]).timestamp()
    assert abs(s1[0]["run_at"] - (analyzed + 30 * 86400)) < 5
    await run(env, aid, mode="full")
    s2 = await jobs().schedules(service="mi", ref=aid)
    assert len(s2) == 1 and s2[0]["run_at"] >= s1[0]["run_at"]


async def test_ac79_changed_only_and_old_version(env):
    aid = await full_fb(env)
    env.ai.reset_calls()
    await run(env, aid, mode="changed_only", areas=["competitor"])
    tasks = {c["task"] for c in env.ai.web_calls()}
    assert tasks == {"mi.web_competitor"}
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["version"] == 2
    old = (await env.c.get(f"/v1/analyses/{aid}?version=1")).json()
    assert old["result"]["version"] == 1 and old["result"]["is_latest"] is False


async def test_ac80_restore_and_ac81_duplicate(env):
    aid = await full_fb(env)
    v1 = (await env.c.get(f"/v1/analyses/{aid}/result?version=1")).json()
    await run(env, aid, mode="changed_only", areas=["market"])
    r = await env.c.post(f"/v1/analyses/{aid}/versions/1/restore")
    assert r.status_code == 200 and r.json()["version"] == 3
    v3 = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert v3["kind"] == "restore"
    for k in ("market", "customer", "user", "competitor"):
        assert v3[k] == v1[k]
    vl = (await env.c.get(f"/v1/analyses/{aid}/versions")).json()["items"]
    assert [v["n"] for v in vl] == [3, 2, 1] and vl[0]["current"]
    d = await env.c.post(f"/v1/analyses/{aid}/duplicate", json={"keep_scope": True})
    assert d.status_code == 201
    dup = d.json()
    src = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert dup["status"] == "draft" and dup["version"] == 0
    assert dup["scope"]["areas"] == src["scope"]["areas"] and dup["segment"]["code"] == src["segment"]["code"]
    assert [c["real_name"] for c in dup["competitors"]] == [c["real_name"] for c in src["competitors"]]
    assert [c["name"] for c in dup["criteria"]] == [c["name"] for c in src["criteria"]]
    assert (await env.c.get(f"/v1/analyses/{dup['id']}/result")).status_code == 404


async def test_ac82_ac83_confidential_and_query_guard(env):
    aid = await full_fb(env)
    for c in env.ai.llm_calls():
        if c["task"] in CONFIDENTIAL_TASKS:
            assert c["confidential"], c["task"]
    sens = A_REQ
    shingles = {sens[i:i + 20] for i in range(len(sens) - 19)}
    for c in env.ai.web_calls():
        assert not any(s in c["query"] for s in shingles), c["query"]
        assert c["confidential"] is False
    assert aid


async def test_ac87_topbar_product_reruns_competitor_only(env):
    aid = await full_fb(env)
    r = await env.c.post(f"/v1/analyses/{aid}/additions", json={"kind": "product", "ids": ["kb:model:mdl_LH13EMDIBGBXKR"]})
    assert r.status_code == 200 and r.json()["added"]
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert len(a["samsung_products"]) == 2 and a["samsung_products"][0]["name"] == "QM55C"
    env.ai.reset_calls()
    await run(env, aid, mode="auto")
    assert {c["task"] for c in env.ai.web_calls()} == {"mi.web_competitor"}
    assert not env.ai.llm_calls("mi.extract_claims_*")


async def test_result_shapes(env):
    aid = await full_fb(env)
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    cp = res["competitor"]
    assert [c["label"] for c in cp["table"]["columns"]] == ["경쟁사 A", "경쟁사 B", "경쟁사 C", "삼성"]
    sam = {r["name"]: r["cells"]["samsung"]["text"] for r in cp["table"]["rows"]}
    assert sam["저전력 운영"] == "QM55C 소비전력 154 W"
    energy = next(x for x in cp["strengths"] if x["title"] == "에너지 절감")
    assert "154 W" in energy["note"] and energy["claims"][0]["status"] == "matched"
    assert 2 <= len(cp["strengths"]) <= 3 and cp["strengths"][0]["title"] == "본사 원격 통합 관리"   # 삼성 칸이 비면(KB 없음) 강점 후보가 아니다
    assert res["footers"]["market"]["text"].startswith("출처 ")
    t0 = time.time()
    lst = (await env.c.get("/v1/analyses")).json()
    assert lst["items"][0]["id"] == aid and lst["items"][0]["action"]["label"] in ("수치 확정", "열기") and time.time() - t0 < 5
