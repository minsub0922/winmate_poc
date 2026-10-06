"""분석(ca.analyze · ca.research) — AC-CA-32 ~ 41 (CA3 · CA4 · CA4D · 근거 패널)."""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from ca_scenario import NAMES, analyze, find, use_a_coffee, use_facts
from winmate_common.jobs import jobs


async def result(env, aid: str, **params: Any) -> dict[str, Any]:
    return (await env.c.get(f"/v1/analyses/{aid}/result", params=params)).json()


async def ready(env, **facts: Any) -> str:
    use_a_coffee(env)
    aid = await find(env)
    use_facts(env, **facts)
    return aid


def gate_on(env, names: list[str], n_block: int) -> tuple[asyncio.Event, asyncio.Event]:
    """names 중 한 곳의 첫 사실 검색이 오면 멈춘다 — n_block 곳이 멈추면 reached."""
    orig = env.ai.web["ca.web_facts"]
    reached, gate = asyncio.Event(), asyncio.Event()
    blocked: set[str] = set()

    async def web(body: dict[str, Any]) -> dict[str, Any]:
        hit = next((n for n in names if n in body["query"]), None)
        if hit and not gate.is_set():
            blocked.add(hit)
            if len(blocked) >= n_block:
                reached.set()
            await gate.wait()
        return orig(body)

    env.ai.web["ca.web_facts"] = web
    return reached, gate


# ── AC-CA-32 동시 2곳 · 진행 문장 · 자동 이동 ─────────────
async def test_ac32_concurrency_and_lines(env):
    aid = await ready(env)
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    job_id = r.json()["job_id"]
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "analyzing" and a["route"] == f"/competitor/{aid}/run"
    assert [c["state"] for c in a["run"]["competitors"]] == ["wait"] * 4
    await env.drain()
    ev = await env.events(job_id)
    snaps = [e["data"]["competitors"] for e in ev if e["type"] == "step" and e["data"].get("step") == "competitors"]
    assert snaps
    assert max(sum(1 for c in s if c["state"] == "run") for s in snaps) == 2
    texts = {c["text"] for s in snaps for c in s}
    assert "경쟁사 A — 제품 · 솔루션 · 레퍼런스 완료, 가격대 찾는 중" in texts
    assert "경쟁사 A — 제품 찾는 중" in texts
    assert not any("판정 중" in t and "찾는 중" in t for t in texts)
    prog = [e["data"]["progress"] for e in ev if e["type"] == "progress"]
    assert prog == sorted(prog) or max(prog) == 100
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "done" and a["route"] == f"/competitor/{aid}/result"
    assert a["version"] == 1 and a["analyzed_count"] in (0, 4)
    p = (await env.c.get(f"/v1/analyses/{aid}/progress")).json()
    assert p["status"] == "done"


async def test_run_conflict(env):
    aid = await ready(env)
    assert (await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})).status_code == 202
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "RUN_IN_PROGRESS"


async def test_provisional_result_while_running(env):
    aid = await ready(env)
    reached, gate = gate_on(env, [NAMES[2], NAMES[3]], 2)
    await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    task = asyncio.create_task(env.drain())
    await asyncio.wait_for(reached.wait(), 60)
    res = await result(env, aid)
    assert res["status"] == "analyzing" and res["partial"]["analyzing"]
    assert [x["letter"] for x in res["competitors"] if x["state"] == "done"] == ["A", "B"]
    assert {x["letter"]: x["state_label"] for x in res["competitors"] if x["state"] != "done"} == {"C": "분석 중", "D": "분석 중"}
    gate.set()
    await asyncio.wait_for(task, 120)


# ── AC-CA-33 중지 · 이어서 ───────────────────────────────
async def test_ac33_stop_and_resume(env):
    aid = await ready(env)
    reached, gate = gate_on(env, [NAMES[2], NAMES[3]], 2)
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    job_id = r.json()["job_id"]
    task = asyncio.create_task(env.drain())
    await asyncio.wait_for(reached.wait(), 60)
    await jobs().cancel(job_id)                                     # CA3 `중지`
    gate.set()
    await asyncio.wait_for(task, 120)
    assert (await env.job(job_id)).status == "canceled"
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "stopped" and a["route"] == f"/competitor/{aid}/result"
    res = await result(env, aid)
    assert [(x["letter"], x["state"]) for x in res["competitors"]] == [("A", "done"), ("B", "done"), ("C", "skipped"), ("D", "skipped")]
    assert [x["state_label"] for x in res["competitors"][2:]] == ["분석 안 함", "분석 안 함"]
    assert res["partial"]["stopped"] and res["partial"]["text"] == "분석을 멈췄어요 · 2곳만 결과가 있어요"
    vers = (await env.c.get(f"/v1/analyses/{aid}/versions")).json()["items"]
    assert vers[0]["stopped"] is True
    lst = (await env.c.get("/v1/analyses")).json()
    row = next(x for x in lst["items"] if x["id"] == aid)
    assert row["action"]["label"] == "이어서" and row["action"]["route"] == f"/competitor/{aid}/result"
    assert row["status_label"] == "확인 중" and row["note"] == "중지됨 · 2곳 분석" and row["count_label"] == "2" and row["count_unit"] == "곳"
    # 이어서 분석 → 나머지 2곳만 수집
    env.ai.web["ca.web_facts"] = env.ai.web["ca.web_research"]
    n = len(env.ai.web_calls("ca.web_facts"))
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "resume"})
    assert r.status_code == 202
    await env.drain()
    qs = [c["query"] for c in env.ai.web_calls("ca.web_facts")[n:]]
    assert qs and all(NAMES[2] in q or NAMES[3] in q for q in qs), qs
    res = await result(env, aid)
    assert res["status"] == "done" and [x["letter"] for x in res["competitors"]] == ["A", "B", "C", "D"]
    assert not res["partial"]["stopped"]


async def test_cancel_before_any_done_returns_to_candidates(env):
    aid = await ready(env)
    reached, gate = gate_on(env, [NAMES[0], NAMES[1]], 2)
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    task = asyncio.create_task(env.drain())
    await asyncio.wait_for(reached.wait(), 60)
    await jobs().cancel(r.json()["job_id"])
    gate.set()
    await asyncio.wait_for(task, 120)
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "confirming" and a["version"] == 0


# ── AC-CA-34 지어낸 수치 ─────────────────────────────────
async def test_ac34_fabricated_price_removed(env):
    aid = await ready(env, price_text="월 3만 원")
    env.ai.llm["ca.positioning"] = lambda body: {"text": "월 3만 원 저가 구독형 라인업"}
    await analyze(env, aid)
    res = await result(env, aid)
    a = res["competitors"][0]
    det = (await env.c.get(f"/v1/analyses/{aid}/competitors/{a['id']}")).json()
    price = next(f for f in det["facts"] if f["key"] == "price")
    assert price["text"] == "[확인 필요]" and price["check"] and price["tbd"]
    blobs = [res, det, await result(env, aid, view="table"), (await env.c.get(f"/v1/analyses/{aid}/claims")).json(),
             (await env.c.get(f"/v1/analyses/{aid}/bundle", params={"target": "mi"})).json()]
    for b in blobs:
        assert "3만" not in json.dumps(b, ensure_ascii=False)
    assert a["positioning"] == '55" 메뉴보드 라인업 · 자체 CMS · 공개 사례 6건'          # 근거 없는 수치가 든 한 줄 → 사실로 만든 한 줄


async def test_price_with_evidence_kept(env):
    aid = await ready(env, price_text="조달 등록 단가 210만 원", price_quote="조달 등록 단가 210만 원")
    await analyze(env, aid)
    res = await result(env, aid)
    det = (await env.c.get(f"/v1/analyses/{aid}/competitors/{res['competitors'][0]['id']}")).json()
    price = next(f for f in det["facts"] if f["key"] == "price")
    assert price["text"] == "조달 등록 단가 210만 원" and not price["check"]


# ── AC-CA-35 · 36 칩 · 강점 · 주의할 점 ─────────────────
async def test_ac35_counts_and_chips(env):
    aid = await ready(env)
    await analyze(env, aid)
    res = await result(env, aid)
    a = res["competitors"][0]
    assert (a["up"], a["eq"], a["dn"], a["unknown"]) == (3, 2, 0, 1)
    assert a["up"] + a["eq"] + a["dn"] <= res["criteria_count"]
    det = (await env.c.get(f"/v1/analyses/{aid}/competitors/{a['id']}")).json()
    labels = [c["label"] for c in det["vs_labels"]]
    assert labels[0].startswith("우위 3") and not any(x.startswith("열위") for x in labels)
    assert any(x.startswith("비슷 2") for x in labels)
    assert any(c["label"].startswith("확인 필요 ") for c in res["chips"])


async def test_ac36_strengths_cautions(env):
    aid = await ready(env)
    env.ai.llm["ca.strengths"] = {"strengths": [], "cautions": []}
    await analyze(env, aid)
    res = await result(env, aid)
    assert 1 <= len(res["strengths"]) <= 3
    assert len(res["cautions"]) <= 2
    assert res["strengths"][0]["criterion_names"][0] == "본사 일괄 배포"          # 중요도 5 × 이긴 3곳
    for c in res["cautions"]:
        assert c["display"] == f"경쟁사 {c['letter']}"
    # 레퍼런스 · AS 에서 삼성이 진 B · D(중요도 2) — 주의할 점
    assert {c["letter"] for c in res["cautions"]} <= {"B", "C", "D"}
    assert "C" in {c["letter"] for c in res["cautions"]}                     # 매장별 가격 차등(중요도 4) 열위


# ── AC-CA-37 삼성 칸 ─────────────────────────────────────
async def test_ac37_samsung_power_cell(env):
    aid = await ready(env)
    await analyze(env, aid)
    crit = (await env.c.get(f"/v1/analyses/{aid}/criteria")).json()["items"]
    power = next(c for c in crit if c["name"] == "전기료")
    claims = (await env.c.get(f"/v1/analyses/{aid}/claims")).json()["items"]
    mine = [c for c in claims if c["block"] == "samsung" and c["criterion_id"] == power["id"]]
    assert mine, "전기료 삼성 칸 주장이 없다"
    titles = []
    for cl in mine:
        det = (await env.c.get(f"/v1/analyses/{aid}/claims/{cl['id']}")).json()
        for card in det["cards"]:
            assert card["kind"] == "kb_official" and card["status"] == "matched", card
            titles.append(card["title"])
        assert cl["status"] == "matched"
    assert any(t.endswith("스펙") for t in titles), titles                    # KB 스펙(소비전력)
    srcs = {s["title"]: s for s in (await env.c.get(f"/v1/analyses/{aid}/sources", params={"kind": "kb_official"})).json()["items"]}
    assert any(s["subtype"] == "스펙" for s in srcs.values())


# ── AC-CA-38 요약만 ─────────────────────────────────────
async def test_ac38_summary_only(env):
    aid = await ready(env)
    env.ai.return_sources = False
    from winmate_competitor import aix

    aix.reset_caps()
    # 후보 A 의 공식 사이트 짐작 URL — 수집 실패 → 어디에도 없다
    from winmate_competitor import store as R

    await R.call(R.update_analysis, aid, lambda d: d["competitors"][0].update(url_guess="https://guess.example.com/zz"))
    await analyze(env, aid)
    res = await result(env, aid)
    cid = res["competitors"][0]["id"]
    det = (await env.c.get(f"/v1/analyses/{aid}/competitors/{cid}")).json()
    lineup = next(f for f in det["facts"] if f["key"] == "lineup")
    assert lineup["check"] is True
    claims = (await env.c.get(f"/v1/analyses/{aid}/claims", params={"competitor": cid})).json()["items"]
    assert claims and all(c["status"] == "needs_check" for c in claims)
    card = (await env.c.get(f"/v1/analyses/{aid}/claims/{claims[0]['id']}")).json()["cards"][0]
    assert card["kind"] == "websearch_summary" and card["kind_label"] == "웹 검색 요약"
    assert "open" not in card["actions"] and card["url"] is None
    for b in (res, det, (await env.c.get(f"/v1/analyses/{aid}/sources")).json(), (await env.c.get(f"/v1/analyses/{aid}/claims")).json()):
        assert "guess.example.com" not in json.dumps(b, ensure_ascii=False)
    assert res["footer"]["text"].endswith("[수치는 확인 후 확정]")


# ── AC-CA-39 출처 요약 ───────────────────────────────────
async def test_ac39_footer(env):
    aid = await ready(env)
    await analyze(env, aid)
    f = (await result(env, aid))["footer"]
    assert f["sources"] == f["public"] + f["kb_case"]
    base = f"출처 {f['sources']} · 공개 자료 {f['public']} · 사내 사례 DB {f['kb_case']}"
    assert f["text"] in (base, base + " · [수치는 확인 후 확정]")
    assert f["text"].endswith("[수치는 확인 후 확정]") == f["unverified"]
    srcs = (await env.c.get(f"/v1/analyses/{aid}/sources")).json()["items"]
    assert len(srcs) >= f["sources"]


def test_ac39_footer_text_unit():
    from winmate_competitor import evidence as E

    assert E.footer_text({"sources": 16, "public": 12, "kb_case": 4, "unverified": True}) == "출처 16 · 공개 자료 12 · 사내 사례 DB 4 · [수치는 확인 후 확정]"
    assert E.footer_text({"sources": 16, "public": 12, "kb_case": 4, "unverified": False}) == "출처 16 · 공개 자료 12 · 사내 사례 DB 4"


# ── AC-CA-40 이 경쟁사 더 찾기 ───────────────────────────
async def test_ac40_research_one(env):
    aid = await ready(env)
    await analyze(env, aid)
    res = await result(env, aid)
    a = res["competitors"][0]
    n = len(env.ai.web_calls())
    r = await env.c.post(f"/v1/analyses/{aid}/competitors/{a['id']}/research", json={})
    assert r.status_code == 202
    r2 = await env.c.post(f"/v1/analyses/{aid}/competitors/{a['id']}/research", json={})
    assert r2.status_code == 409
    await env.drain()
    qs = [c["query"] for c in env.ai.web_calls()[n:]]
    assert qs and all(NAMES[0] in q for q in qs), qs                         # 다른 경쟁사 검색 0회
    vers = (await env.c.get(f"/v1/analyses/{aid}/versions")).json()["items"]
    assert vers[0]["kind"] == "research" and vers[0]["n"] == 2
    a2 = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a2["version"] == 2 and a2["status"] == "done"


async def test_research_finds_price(env):
    aid = await ready(env)
    await analyze(env, aid)
    a = (await result(env, aid))["competitors"][0]
    use_facts(env, price_text="조달 등록 단가 210만 원", price_quote="조달 등록 단가 210만 원")
    r = await env.c.post(f"/v1/analyses/{aid}/competitors/{a['id']}/research", json={"facts": ["price"]})
    assert r.status_code == 202
    await env.drain()
    det = (await env.c.get(f"/v1/analyses/{aid}/competitors/{a['id']}")).json()
    price = next(f for f in det["facts"] if f["key"] == "price")
    assert price["text"] == "조달 등록 단가 210만 원"
    lineup = next(f for f in det["facts"] if f["key"] == "lineup")
    assert lineup["text"] != "[확인 필요]"                                     # 다른 항목은 그대로


# ── AC-CA-41 비교표 ─────────────────────────────────────
async def test_ac41_table(env):
    aid = await ready(env)
    await analyze(env, aid)
    crit = (await env.c.get(f"/v1/analyses/{aid}/criteria")).json()["items"]
    t = (await result(env, aid, view="table"))["table"]
    assert [c["name"] for c in t["criteria"]] == [c["name"] for c in crit if c["enabled"]]
    assert [c["label"] for c in t["columns"]] == ["경쟁사 A", "경쟁사 B", "경쟁사 C", "경쟁사 D", "삼성"]
    assert t["columns"][-1]["samsung"] is True
    assert len(t["cells"]) == len(t["criteria"]) and all(len(r) == 5 for r in t["cells"])
    price_row = t["cells"][[c["name"] for c in t["criteria"]].index("가격대")]
    assert all(cell["text"] == "[확인 필요]" and cell["tbd"] for cell in price_row[:4])
    for row in t["cells"]:
        for cell in row:
            assert cell["text"].strip()


async def test_changed_only_and_versions(env):
    aid = await ready(env)
    await analyze(env, aid)
    a = (await result(env, aid))["competitors"][1]
    n = len(env.ai.web_calls())
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "changed_only", "competitor_ids": [a["id"]]})
    assert r.status_code == 202
    await env.drain()
    qs = [c["query"] for c in env.ai.web_calls()[n:]]
    assert qs and all(NAMES[1] in q for q in qs)
    vers = (await env.c.get(f"/v1/analyses/{aid}/versions")).json()["items"]
    assert [v["n"] for v in vers] == [2, 1] and vers[0]["kind"] == "changed_only"
    # 버전 1 보기 · 되돌리기
    old = await result(env, aid, version=1)
    assert old["version"] == 1
    r = await env.c.post(f"/v1/analyses/{aid}/versions/1/restore")
    assert r.status_code == 200
    assert (await env.c.get(f"/v1/analyses/{aid}")).json()["version"] == 3


def test_number_parse_and_scrub_unit():
    from winmate_competitor import verify

    text, removed = verify.scrub_numbers("월 3만 원 · QM55C · 공개 사례 6건", ["공개 사례 6건"])
    assert "3만" not in text and "[00]" in text and "QM55C" in text and "6건" in text and removed
    assert re.search(r"\[00\]", text)
