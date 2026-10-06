"""찾기(ca.find) — AC-CA-07 ~ 17 · 51 · 52 (CA1G · CA2Q · 빈 칸 처리 · 명시 후보 · 검색어 보호 · 자기 회사 제외)."""
from __future__ import annotations

from typing import Any

from ca_scenario import A_TEXT, KINDS, NAMES, slots_json, use_a_coffee, use_facts

NO_SLOTS = slots_json(customer=None, place=None, region=None, product="메뉴보드 사이니지", specific=False)


async def start(env, text: str = A_TEXT, **create: Any) -> tuple[str, str]:
    r = await env.c.post("/v1/analyses", json={"input_mode": "free", "text": text, **create})
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    r = await env.c.post(f"/v1/analyses/{aid}/find")
    assert r.status_code == 202, r.text
    return aid, r.json()["job_id"]


async def doc(env, aid: str) -> dict[str, Any]:
    return (await env.c.get(f"/v1/analyses/{aid}")).json()


async def cands(env, aid: str) -> list[dict[str, Any]]:
    return (await env.c.get(f"/v1/analyses/{aid}/candidates")).json()["items"]


def chip_labels(a: dict[str, Any]) -> list[str]:
    return [c["label"] for c in a["chips"]]


def substrings(text: str, n: int = 20) -> set[str]:
    t = " ".join((text or "").split())
    return {t[i:i + n] for i in range(0, max(0, len(t) - n + 1))}


# ── AC-CA-07 작업 줄 · 자동 이동 ─────────────────────────
async def test_ac07_lines_and_auto_move(env):
    use_a_coffee(env)
    aid, job_id = await start(env)
    await env.drain()
    ev = await env.events(job_id)
    assert not any(e["type"] == "awaiting_input" for e in ev)
    line_ev = [e["data"] for e in ev if e["type"] == "step" and e["data"].get("step") == "lines"]
    assert line_ev, "작업 줄 이벤트가 없다"
    seqs = [[ln["state"] for ln in d["lines"]] for d in line_ev]
    assert seqs[0] == ["active", "wait", "wait", "wait"]
    assert ["done", "active", "wait", "wait"] in seqs
    assert ["done", "done", "active", "wait"] in seqs
    assert ["done", "done", "done", "active"] in seqs
    assert seqs[-1] == ["done", "done", "done", "done"]
    texts = [ln["text"] for ln in line_ev[-1]["lines"]]
    assert texts[0] == "입력 읽기 — 고객사 · 업종 · 장소 · 제품"
    assert texts[1].startswith("같은 업종 도입사례 ") and texts[1].endswith("건의 제품군으로 후보 찾기")
    assert texts[2] == "수도권 · 55\" 사이니지 공개 자료 검색"
    assert texts[3] == "후보 정리 · 근거 붙이기"
    assert line_ev[-1]["candidates_so_far"] == 6
    a = await doc(env, aid)
    assert a["status"] == "confirming"
    assert a["route"] == f"/competitor/{aid}/candidates"
    assert (await env.job(job_id)).status == "succeeded"


# ── AC-CA-08 · 11 · 12 묻기 1 ─────────────────────────────
async def test_ac08_ask_when_ambiguous(env):
    use_a_coffee(env, slots=NO_SLOTS, segment={"FB": 0.62, "RT": 0.59})
    aid, job_id = await start(env, "카페 메뉴보드 사이니지")
    await env.drain()
    j = await env.job(job_id)
    assert j.status == "awaiting_input"
    req = j.input_request
    assert req["kind"] == "slots" and req["missing"] == ["customer", "place"]
    assert req["desc"] == "입력에서 업종(외식 · 카페)과 제품(메뉴보드 사이니지)은 읽었지만 고객사와 장소가 없어요. 알려 주면 지역 경쟁사까지 찾아요."
    assert req["industry"]["ambiguous"] is True
    a = await doc(env, aid)
    assert a["status"] == "ask" and a["route"] == f"/competitor/{aid}/ask"
    assert a["ask"]["missing"] == ["customer", "place"]
    lst = (await env.c.get("/v1/analyses")).json()
    assert next(x for x in lst["items"] if x["id"] == aid)["note"] == "고객사 · 장소 확인 대기"


async def test_ac11_answer_customer(env):
    use_a_coffee(env, slots=NO_SLOTS, segment={"FB": 0.62, "RT": 0.59})
    aid, job_id = await start(env, "카페 메뉴보드 사이니지")
    await env.drain()
    n_cls = len(env.ai.llm_calls("ca.classify_segment"))
    await env.answer(job_id, {"customer": "A 커피 프랜차이즈"})
    await env.drain()
    assert (await env.job(job_id)).status == "succeeded"
    a = await doc(env, aid)
    assert a["status"] == "confirming"
    assert a["slots"]["customer"]["value"] == "A 커피 프랜차이즈" and a["slots"]["customer"]["origin"] == "answer"
    assert len(env.ai.llm_calls("ca.classify_segment")) == n_cls + 1        # 업종 다시 판별
    # 고객사로 공개 자료 검색(고객사 이름은 검색어에 쓸 수 있다)
    assert any("A 커피 프랜차이즈" in c["query"] for c in env.ai.web_calls("ca.web_candidates"))


async def test_ac11_answer_wrapped_value(env):
    """jobs 입력이 `{value: {...}}` 로 와도 받는다."""
    use_a_coffee(env, slots=NO_SLOTS, segment={"FB": 0.62, "RT": 0.59})
    aid, job_id = await start(env, "카페 메뉴보드 사이니지")
    await env.drain()
    await env.answer(job_id, {"value": {"customer": "", "place": "부산 해운대"}})
    await env.drain()
    a = await doc(env, aid)
    assert a["slots"]["place"]["value"] == "부산 해운대" and a["slots"]["place"]["origin"] == "answer"
    assert "지역 미반영" not in chip_labels(a)


async def test_ac12_skip(env):
    use_a_coffee(env, slots=NO_SLOTS, segment={"FB": 0.62, "RT": 0.59})
    aid, job_id = await start(env, "카페 메뉴보드 사이니지")
    await env.drain()
    await env.answer(job_id, {"skip": True})
    await env.drain()
    a = await doc(env, aid)
    assert a["status"] == "confirming"
    assert chip_labels(a)[:2] == ["업종 기준", "업종 확인"]
    assert a["segment"]["code"] == "FB"                                     # 1위 업종으로 찾기
    assert a["slots"]["customer"]["found"] == "empty"


async def test_ask_cancel_back_to_input(env):
    """CA2Q `뒤로` → 잡 취소 → CA1(draft)."""
    use_a_coffee(env, slots=NO_SLOTS, segment={"FB": 0.62, "RT": 0.59})
    aid, job_id = await start(env, "카페 메뉴보드 사이니지")
    await env.drain()
    r = await env.c.patch(f"/v1/analyses/{aid}", json={"text": "카페 메뉴보드 사이니지 교체"})
    assert r.status_code == 200
    from winmate_common.jobs import jobs

    await jobs().cancel(job_id)
    a = await doc(env, aid)
    assert a["status"] == "draft" and a["current_job_id"] is None and a["ask"] is None
    assert a["route"] == f"/competitor/{aid}/input"
    assert a["text"] == "카페 메뉴보드 사이니지 교체"


# ── AC-CA-09 · 10 업종이 분명할 때 ────────────────────────
async def test_ac09_no_ask_when_industry_clear(env):
    names = [f"{c}{c} 사이니지" for c in "가나다라마바사아자차"]
    sig = [(0.9, 0.9, 0.0, 0.0, False)] * 10
    use_a_coffee(env, names=names, signals=sig, slots=NO_SLOTS, segment={"FB": 0.80, "RT": 0.40})
    env.ai.llm["ca.candidates_from_text"] = {"candidates": [{"name": n, "kind_label": "사이니지", "evidence_id": "E1", "evidence_quote": n} for n in names]}
    aid, job_id = await start(env, "카페 메뉴보드 사이니지")
    await env.drain()
    j = await env.job(job_id)
    assert j.status == "succeeded"
    a = await doc(env, aid)
    assert "업종 기준" in chip_labels(a)
    items = await cands(env, aid)
    kept = [c for c in items if c["status"] in ("rec", "check")]
    assert len(kept) == 8                                                    # 업종 + 제품 단 상한
    assert a["slots"]["customer"]["found"] == "empty"


async def test_ac10_ask_even_if_clear_when_configured(env, monkeypatch):
    monkeypatch.setenv("CA_ASK_SLOTS_REQUIRE_AMBIGUOUS_INDUSTRY", "false")
    use_a_coffee(env, slots=NO_SLOTS, segment={"FB": 0.80, "RT": 0.40})
    aid, job_id = await start(env, "카페 메뉴보드 사이니지")
    await env.drain()
    j = await env.job(job_id)
    assert j.status == "awaiting_input"
    assert j.input_request["industry"]["ambiguous"] is False


# ── AC-CA-13 · 14 · 15 빈 칸 처리 ─────────────────────────
async def test_ac13_place_missing(env):
    use_a_coffee(env, slots=slots_json(place=None, region=None))
    aid, job_id = await start(env, "A 커피 프랜차이즈 메뉴보드 55인치 사이니지")
    await env.drain()
    assert (await env.job(job_id)).status == "succeeded"
    a = await doc(env, aid)
    assert chip_labels(a) == ["지역 미반영"]
    qs = [c["query"] for c in env.ai.web_calls()]
    assert not any(q.endswith("설치 업체") for q in qs), qs                 # 장소 신호 검색 없음
    assert a["find"]["lines"][2]["text"] == "55\" 사이니지 공개 자료 검색"


async def test_ac14_product_inferred(env):
    use_a_coffee(env, slots=slots_json(product=None))
    aid, job_id = await start(env, "A 커피 프랜차이즈 수도권 직영점 경쟁사")
    await env.drain()
    assert (await env.job(job_id)).status == "succeeded"
    a = await doc(env, aid)
    p = a["slots"]["product"]
    assert p["value"] and p["origin"] == "inferred"
    assert chip_labels(a) == []                                              # 칩 없음(자동)


async def test_ac15_customer_only(env):
    use_a_coffee(env, slots=slots_json(place=None, region=None, product=None), segment={"RT": 0.30, "FB": 0.20})
    summary = "B 마트는 전국 대형마트 체인으로 수도권 매장이 많다."
    env.ai.web["ca.web_customer"] = {"summary": summary, "sources": []}
    env.ai.return_sources = False
    env.ai.llm["ca.extract_slots"] = [slots_json(customer="B 마트", place=None, region=None, product=None),
                                      {"place": {"value": "수도권 매장", "kind": "site", "region": "수도권", "confidence": 0.7}}]
    env.ai.llm["ca.classify_segment"] = lambda body: {"segments": [{"code": "RT", "p": 1.0 if "대형마트" in body["prompt"] else 0.3, "clues": []}]}
    aid, job_id = await start(env, "B 마트")
    await env.drain()
    assert (await env.job(job_id)).status == "succeeded", (await env.job(job_id)).error
    a = await doc(env, aid)
    assert chip_labels(a) == ["장소 추정", "업종 추정"]
    assert all(c["mode"] == "check" for c in a["chips"])
    assert a["slots"]["place"]["origin"] == "inferred" and a["slots"]["place"]["value"] == "수도권 매장"
    assert a["slots"]["industry"]["origin"] == "inferred" and a["segment"]["code"] == "RT"
    assert any(c["task"] == "ca.web_customer" and "B 마트" in c["query"] for c in env.ai.web_calls())


# ── AC-CA-16 · 17 명시 후보 ──────────────────────────────
async def test_ac16_rfp_mention_and_eval_first(env):
    use_a_coffee(env, names=NAMES[1:])
    fid = env.files.add("rfp.pdf", "평가 기준: 유지보수 응답 시간. 기존 공급사 ZZ 사이니지 대비 개선안을 제시할 것.")
    env.ai.llm["ca.extract_slots"] = {**slots_json(), "competitor_mentions": ["ZZ 사이니지"], "eval_criteria": ["유지보수 응답 시간"]}
    env.ai.llm["ca.make_criteria"] = {"criteria": [{"name": "본사 일괄 배포", "source": "free"}, {"name": "유지보수 응답", "source": "rfp"},
                                                   {"name": "전기료", "source": "free"}],
                                      "industry": [{"code": "R08", "name": "인건비 절감"}]}
    aid, job_id = await start(env, A_TEXT, file_ids=[fid])
    await env.drain()
    assert (await env.job(job_id)).status == "succeeded"
    items = await cands(env, aid)
    zz = next(c for c in items if c["real_name"] == "ZZ 사이니지")
    assert zz["origin"] == "rfp" and zz["on"] and zz["pinned"]
    crit = (await env.c.get(f"/v1/analyses/{aid}/criteria")).json()["items"]
    assert crit[0]["name"] == "유지보수 응답"
    prompt = env.ai.llm_calls("ca.make_criteria")[-1]["prompt"]
    assert prompt.index("(rfp) 유지보수 응답 시간") < prompt.index("(free)")


async def test_ac17_mi_bundle_start(env):
    use_a_coffee(env)
    bundle = {"analysis_id": "mi_01TEST", "version": 2, "target": "competitor", "customer": {"name": "A 커피 프랜차이즈"}, "segment": "FB",
              "requirements": [{"id": "r1", "text": "본사에서 전 매장 메뉴 콘텐츠를 일괄 배포", "weight": 5}],
              "competitors": [{"real_name": n, "aliases": [], "kind_label": k, "desc": ""} for n, k in zip(NAMES[:3], KINDS[:3])]}
    r = await env.c.post("/v1/analyses", json={"input_mode": "mi", "mi_bundle": bundle})
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["status"] == "finding" and a["current_job_id"]
    assert a["mi_ref"]["analysis_id"] == "mi_01TEST"
    await env.drain()
    j = await env.job(a["current_job_id"])
    assert j.status == "succeeded", j.error
    a = await doc(env, a["id"])
    assert a["slots"]["customer"]["origin"] == "mi"
    items = await cands(env, a["id"])
    mi = [c for c in items if c["origin"] == "mi"]
    assert sorted(c["real_name"] for c in mi) == sorted(NAMES[:3])
    assert all(c["on"] and c["pinned"] for c in mi)
    assert any(c["origin"] == "auto" for c in items)                         # 추가 후보도 찾는다


# ── AC-CA-51 검색어 보호 ─────────────────────────────────
async def test_ac51_queries_have_no_customer_text(env):
    use_a_coffee(env)
    rq = "rq_01SAFE"
    items = ["본사에서 전국 매장 메뉴 콘텐츠를 한 번에 일괄 배포해야 한다", "매장별로 가격을 다르게 표시할 수 있어야 한다"]
    env.rq.add(rq, customer="A 커피 프랜차이즈", items=items, vertical={"top2": [{"id": "kr_fnb", "name": "요식", "score": 0.9}], "ask": False},
               spaces=["직영점"], products=["스마트 LCD 사이니지"], solutions=["MagicINFO"])
    rfp = "제안 요청: 본사에서 콘텐츠를 일괄 배포하는 솔루션과 55인치 사이니지 320대를 2027년 3월까지 설치."
    fid = env.files.add("rfp.pdf", rfp)
    # 모델이 고객 원문을 그대로 제품 값으로 돌려줘도 검색어에는 들어가지 않는다
    env.ai.llm["ca.extract_slots"] = {**slots_json(product="본사에서 콘텐츠를 일괄 배포하는 솔루션"), "competitor_mentions": [], "eval_criteria": []}
    r = await env.c.post("/v1/analyses", json={"input_mode": "requirements", "requirements_id": rq, "file_ids": [fid],
                                                "extra_text": "본사 콘텐츠 일괄 배포가 가장 중요한 평가 항목이라고 들었다"})
    aid = r.json()["id"]
    assert (await env.c.post(f"/v1/analyses/{aid}/find")).status_code == 202
    await env.drain()
    use_facts(env)
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    assert r.status_code == 202, r.text
    await env.drain()
    banned = set()
    for t in [rfp, *items, "본사 콘텐츠 일괄 배포가 가장 중요한 평가 항목이라고 들었다"]:
        banned |= substrings(t)
    qs = [c["query"] for c in env.ai.web_calls()]
    assert qs
    for q in qs:
        qn = " ".join(q.split())
        assert not any(s in qn for s in banned), q
        assert "2027" not in qn and "320대" not in qn
    assert any("A 커피 프랜차이즈" in q for q in qs)                          # 고객사 이름은 쓸 수 있다
    assert any(n in q for q in qs for n in NAMES)                             # 경쟁사 이름도


# ── AC-CA-52 자기 회사 · 고객사 제외 ─────────────────────
async def test_ac52_self_and_customer_excluded(env):
    names = NAMES[:4] + ["삼성전자", "A 커피 프랜차이즈"]
    use_a_coffee(env, names=names)
    aid, job_id = await start(env)
    await env.drain()
    items = await cands(env, aid)
    got = {c["real_name"] for c in items}
    assert "삼성전자" not in got and "A 커피 프랜차이즈" not in got
    assert set(NAMES[:4]) <= got
    # 직접 추가로도 넣을 수 없다
    r = await env.c.post(f"/v1/analyses/{aid}/candidates", json={"name": "Samsung Electronics"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "SELF_ENTITY"


# ── 찾기 실패 · 지어낸 후보 방지 ─────────────────────────
async def test_find_nothing_fails(env):
    use_a_coffee(env)
    env.ai.llm["ca.candidates_from_text"] = {"candidates": []}
    aid, job_id = await start(env)
    await env.drain()
    j = await env.job(job_id)
    assert j.status == "failed"
    a = await doc(env, aid)
    assert a["status"] == "failed"
    assert a["find"]["error"] == "경쟁사를 찾지 못했어요"
    assert a["route"] == f"/competitor/{aid}/input"


async def test_find_drops_names_not_in_evidence(env):
    use_a_coffee(env)
    cs = env.ai.llm["ca.candidates_from_text"]["candidates"] + [{"name": "QQ 가짜", "kind_label": "x", "evidence_id": "E1", "evidence_quote": "QQ"}]
    env.ai.llm["ca.candidates_from_text"] = {"candidates": cs}
    aid, _ = await start(env)
    await env.drain()
    assert "QQ 가짜" not in {c["real_name"] for c in await cands(env, aid)}


async def test_find_while_analyzing_conflict(env):
    use_a_coffee(env)
    aid, _ = await start(env)
    await env.drain()
    use_facts(env)
    assert (await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})).status_code == 202
    r = await env.c.post(f"/v1/analyses/{aid}/find")
    assert r.status_code == 409
