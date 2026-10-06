"""비교 기준(CA3 · CA3C) — AC-CA-27 ~ 31."""
from __future__ import annotations

import asyncio
from typing import Any

from ca_scenario import NAMES, find, use_a_coffee, use_facts
from winmate_competitor import rules


async def crit(env, aid: str) -> dict[str, Any]:
    return (await env.c.get(f"/v1/analyses/{aid}/criteria")).json()


def as_in(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{k: c[k] for k in ("id", "name", "source", "source_count", "importance", "order", "enabled")} for c in items]


# ── AC-CA-27 자동 6 ──────────────────────────────────────
async def test_ac27_auto_six(env):
    use_a_coffee(env)
    aid = await find(env)
    out = await crit(env, aid)
    items = out["items"]
    assert [c["name"] for c in items] == ["본사 일괄 배포", "매장별 가격 차등", "전기료", "인건비 절감", "가격대", "레퍼런스 · AS"]
    assert [c["importance"] for c in items] == [5, 4, 4, 3, 3, 2]
    assert [c["source"] for c in items] == ["requirements", "requirements", "requirements", "industry_cases", "default", "default"]
    assert items[3]["source_label"].startswith("업종 사례 ") and items[3]["source_label"].endswith("건")
    assert out["summary_text"] == "요구사항에서 3 · 업종 사례에서 1 · 기본 2"
    assert out["mode"] == "auto" and out["on"] == 6 and out["total"] == 6
    assert not any(c["pinned"] for c in items)


# ── AC-CA-28 요구 1개 ────────────────────────────────────
async def test_ac28_one_requirement_fills_with_industry(env):
    use_a_coffee(env)
    env.ai.llm["ca.make_criteria"] = {"criteria": [{"name": "본사 일괄 배포", "source": "free"}],
                                      "industry": [{"code": "R08", "name": "인건비 절감"}, {"code": "R03", "name": "원격 콘텐츠"},
                                                   {"code": "R07", "name": "설치 속도"}, {"code": "R16", "name": "시간대 프로모션"}]}
    aid = await find(env)
    out = await crit(env, aid)
    assert out["total"] == 6
    assert out["summary"]["requirements"] == 1 and out["summary"]["default"] == 2 and out["summary"]["industry_cases"] == 3
    assert out["items"][0]["name"] == "본사 일괄 배포" and out["items"][0]["importance"] == 5


def test_compose_rules_unit():
    ind = [{"name": "인건비 절감", "n": 12}, {"name": "원격 콘텐츠", "n": 9}, {"name": "설치 속도", "n": 7}]
    out = rules.compose_criteria([{"name": "본사 일괄 배포"}, {"name": "매장별 가격 차등"}, {"name": "전기료"}, {"name": "넷째"}], ind)
    assert [c["name"] for c in out] == ["본사 일괄 배포", "매장별 가격 차등", "전기료", "인건비 절감", "가격대", "레퍼런스 · AS"]
    assert out[3]["source_count"] == 12
    # 기본 기준과 같은 이름의 요구는 기본 하나로 · 업종 사례가 모자라면 채우려고 지어내지 않는다(3 + 기본 2 = 5)
    out = rules.compose_criteria([{"name": "가격대"}], ind)
    assert [c["name"] for c in out].count("가격대") == 1 and len(out) == 5


# ── AC-CA-29 끄기 ───────────────────────────────────────
async def test_ac29_disable(env):
    use_a_coffee(env)
    aid = await find(env)
    items = as_in((await crit(env, aid))["items"])
    items[2]["enabled"] = False
    r = await env.c.put(f"/v1/analyses/{aid}/criteria", json={"items": items})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["on"] == 5 and out["total"] == 6 and out["mode"] == "pin" and out["job_id"] is None
    assert all(c["pinned"] for c in out["items"])
    for c in items:
        c["enabled"] = False
    r = await env.c.put(f"/v1/analyses/{aid}/criteria", json={"items": items})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_CRITERIA"


async def test_reorder_and_importance(env):
    use_a_coffee(env)
    aid = await find(env)
    items = as_in((await crit(env, aid))["items"])
    items[0]["order"], items[5]["order"] = 5, 0
    items[0]["importance"] = 2
    r = await env.c.put(f"/v1/analyses/{aid}/criteria", json={"items": items})
    out = r.json()
    assert out["items"][0]["name"] == "레퍼런스 · AS" and out["items"][-1]["name"] == "본사 일괄 배포"
    assert out["items"][-1]["importance"] == 2
    # 다시 찾기 해도 고정 기준은 그대로
    assert (await env.c.post(f"/v1/analyses/{aid}/find")).status_code == 202
    await env.drain()
    again = await crit(env, aid)
    assert [c["name"] for c in again["items"]] == [c["name"] for c in out["items"]] and again["mode"] == "pin"


# ── AC-CA-30 분석 중 기준 바꾸기 ─────────────────────────
async def test_ac30_change_during_analysis_reuses_facts(env):
    use_a_coffee(env)
    aid = await find(env)
    use_facts(env)
    orig = env.ai.web["ca.web_facts"]
    reached, gate = asyncio.Event(), asyncio.Event()

    async def web(body: dict[str, Any]) -> dict[str, Any]:
        if NAMES[3] in body["query"] and not reached.is_set():       # 경쟁사 D 가 시작될 때 = A · B 는 끝남
            reached.set()
            await gate.wait()
        return orig(body)

    env.ai.web["ca.web_facts"] = web
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    assert r.status_code == 202
    first_job = r.json()["job_id"]
    task = asyncio.create_task(env.drain())
    await asyncio.wait_for(reached.wait(), 60)
    n_before = len(env.ai.web_calls("ca.web_facts"))
    items = as_in((await crit(env, aid))["items"])
    items[2]["enabled"] = False
    r = await env.c.put(f"/v1/analyses/{aid}/criteria", json={"items": items})
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["job_id"] and body["job_id"] != first_job
    assert body["mode"] == "pin" and all(c["pinned"] for c in body["items"])
    gate.set()
    await asyncio.wait_for(task, 120)
    assert (await env.job(first_job)).status == "canceled"
    assert (await env.job(body["job_id"])).status == "succeeded", (await env.job(body["job_id"])).error
    after = [c["query"] for c in env.ai.web_calls("ca.web_facts")[n_before:]]
    assert not any(NAMES[0] in q or NAMES[1] in q for q in after), after   # 이미 모은 A · B 사실은 다시 찾지 않는다
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "done"
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert [c["letter"] for c in res["competitors"]] == ["A", "B", "C", "D"]
    assert res["criteria_count"] == 5
    vers = (await env.c.get(f"/v1/analyses/{aid}/versions")).json()["items"]
    assert vers[0]["kind"] == "rejudge"


async def test_rejudge_after_done_uses_no_web(env):
    use_a_coffee(env)
    aid = await find(env)
    use_facts(env)
    assert (await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})).status_code == 202
    await env.drain()
    items = as_in((await crit(env, aid))["items"])
    items[0]["importance"] = 1
    r = await env.c.put(f"/v1/analyses/{aid}/criteria", json={"items": items})
    assert r.status_code == 200 and r.json()["job_id"] is None
    n = len(env.ai.web_calls()) + len(env.ai.fetch_calls())
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "rejudge"})
    assert r.status_code == 202
    await env.drain()
    assert len(env.ai.web_calls()) + len(env.ai.fetch_calls()) == n
    assert (await env.c.get(f"/v1/analyses/{aid}")).json()["version"] == 2


# ── AC-CA-31 추천 기준 더하기 ────────────────────────────
async def test_ac31_add_suggestion(env):
    use_a_coffee(env)
    aid = await find(env)
    out = await crit(env, aid)
    assert out["suggestions"], "업종 사례 추천 기준이 없다"
    s = out["suggestions"][0]
    assert s["name"] not in [c["name"] for c in out["items"]]
    items = as_in(out["items"]) + [{"name": s["name"], "source": "industry_cases", "source_count": s["n"], "importance": 3, "order": 6,
                                     "enabled": True}]
    r = await env.c.put(f"/v1/analyses/{aid}/criteria", json={"items": items})
    assert r.status_code == 200
    added = r.json()["items"][-1]
    assert added["name"] == s["name"] and added["source_label"] == f"업종 사례 {s['n']}건"
    assert r.json()["total"] == 7
