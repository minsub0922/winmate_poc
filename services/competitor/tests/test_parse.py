"""넣기 · 읽기 — AC-CA-01 ~ 06 (CA1 · CA1R)."""
from __future__ import annotations

from ca_scenario import A_TEXT, NAMES, slots_json, use_a_coffee


def chips(p: dict) -> list[str]:
    return [p["slots"][k]["chip_text"] for k in ("customer", "industry", "place", "product")]


async def test_ac01_four_slots(env):
    use_a_coffee(env)
    r = await env.c.post("/v1/parse", json={"text": A_TEXT})
    assert r.status_code == 200, r.text
    p = r.json()
    assert chips(p) == ["고객사 · A 커피 프랜차이즈", "업종 · 외식 · 카페", "장소 · 수도권 직영점", '제품 · 55" 사이니지 + 배포 솔루션']
    assert all(p["slots"][k]["found"] == "found" for k in ("customer", "industry", "place", "product"))
    assert p["found_count"] == 4
    assert p["segment"]["code"] == "FB"
    # 고객 자료가 든 모델 호출은 기밀
    assert all(c["confidential"] for c in env.ai.llm_calls("ca.extract_slots"))
    assert all(c["confidential"] for c in env.ai.llm_calls("ca.classify_segment"))


async def test_ac02_partial_and_empty(env):
    use_a_coffee(env, slots=slots_json(customer=None, place=None, region=None, product="메뉴보드 사이니지", specific=False))
    p = (await env.c.post("/v1/parse", json={"text": "카페 메뉴보드 사이니지"})).json()
    assert p["slots"]["customer"]["found"] == "empty" and p["slots"]["customer"]["chip_text"] == "고객사 · 비어 있음"
    assert p["slots"]["place"]["found"] == "empty" and p["slots"]["place"]["chip_text"] == "장소 · 비어 있음"
    assert p["slots"]["product"]["found"] == "partial" and p["slots"]["product"]["partial"] is True
    assert p["slots"]["industry"]["found"] == "found"
    assert p["found_count"] == 2


async def test_ac03_llm_failure_kb_only(env):
    use_a_coffee(env)
    env.ai.llm["ca.extract_slots"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "장애"}}
    r = await env.c.post("/v1/parse", json={"text": "카페 메뉴보드 사이니지 바꾸기"})
    assert r.status_code == 200
    p = r.json()
    assert p["degraded"] is True
    assert p["slots"]["customer"]["found"] == "empty" and p["slots"]["place"]["found"] == "empty"
    assert p["slots"]["industry"]["value"] == "외식 · 카페"
    assert p["slots"]["product"]["value"]           # KB A1 이 읽은 제품군


async def test_ac03_confidential_blocked_falls_back(env):
    use_a_coffee(env)
    env.ai.llm["ca.extract_slots"] = {"error": {"status": 403, "code": "POLICY_CONFIDENTIAL", "message": "기밀 차단"}}
    env.ai.llm["ca.classify_segment"] = {"error": {"status": 403, "code": "POLICY_CONFIDENTIAL", "message": "기밀 차단"}}
    p = (await env.c.post("/v1/parse", json={"text": "카페 메뉴보드 사이니지"})).json()
    assert p["degraded"] is True
    assert p["slots"]["industry"]["value"]          # kb 근거만으로(0.6 kb + 0.4 단서)


async def test_ac04_find_needs_input(env):
    r = await env.c.post("/v1/analyses", json={"input_mode": "free", "text": ""})
    aid = r.json()["id"]
    r = await env.c.post(f"/v1/analyses/{aid}/find")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "EMPTY_INPUT"


def definition(env, rq_id="rq_01TESTDEF", author_note="경쟁사 YY 광고는 지난번 입찰에서 우리를 이겼다"):
    env.rq.add(rq_id, customer="A 커피 프랜차이즈", items=["본사에서 전 매장 메뉴 콘텐츠를 일괄 배포", "매장별 가격을 다르게 표시", "전기료 절감"],
               author_note=author_note, vertical={"top2": [{"id": "kr_fnb", "name": "요식", "score": 0.9}], "ask": False},
               spaces=["직영점"], products=["스마트 LCD 사이니지"], solutions=["MagicINFO"])
    return rq_id


async def test_ac05_definition_chips(env):
    use_a_coffee(env)
    rq = definition(env)
    env.ai.llm["ca.extract_slots"] = {"customer": {"value": None, "confidence": 0}, "place": {"value": None, "kind": "region", "region": "수도권",
                                                                                            "confidence": 0.8},
                                      "product": {"value": None, "categories": [], "specific": False, "confidence": 0}}
    p = (await env.c.post("/v1/parse", json={"requirements_id": rq})).json()
    assert chips(p) == ["고객사 · A 커피 프랜차이즈", "업종 · 외식 · 카페", "장소 · 수도권 직영점", "제품 · 스마트 LCD 사이니지 + MagicINFO"]
    assert p["slots"]["customer"]["origin"] == "definition"
    assert p["slots"]["industry"]["origin"] == "definition"       # kr_fnb → FB 하나에 대응 · ask=false → 상속
    assert p["found_count"] == 4


async def test_ac05_definition_without_region_is_partial(env):
    use_a_coffee(env)
    rq = definition(env)
    env.ai.llm["ca.extract_slots"] = {}
    p = (await env.c.post("/v1/parse", json={"requirements_id": rq})).json()
    assert p["slots"]["place"]["value"] == "직영점"
    assert p["slots"]["place"]["found"] == "partial"


async def test_ac05_include_exclude_in_find(env):
    use_a_coffee(env, names=["WW 디스플레이", "VV 클라우드", "UU 키오스크", "TT 디스플레이", "SS 미디어", "YY 광고"])
    rq = definition(env)
    env.ai.llm["ca.include_exclude"] = {"include": ["ZZ 사이니지"], "exclude": ["YY 광고"], "notes": ""}
    r = await env.c.post("/v1/analyses", json={"input_mode": "requirements", "requirements_id": rq,
                                                "extra_text": "ZZ 사이니지는 꼭 넣고 YY 광고는 빼"})
    assert r.status_code == 201
    aid = r.json()["id"]
    assert (await env.c.post(f"/v1/analyses/{aid}/find")).status_code == 202
    await env.drain()
    cands = (await env.c.get(f"/v1/analyses/{aid}/candidates")).json()["items"]
    zz = next(c for c in cands if c["real_name"] == "ZZ 사이니지")
    assert zz["on"] and zz["pinned"] and zz["origin"] == "include"
    assert not any(c["real_name"] == "YY 광고" for c in cands)
    # 정의서 사용 링크 등록
    assert any(l["service"] == "competitor" and l["ref_id"] == aid for l in env.rq.links)


async def test_ac06_author_note_not_in_chips_and_confidential(env):
    use_a_coffee(env)
    note = "A 커피 프랜차이즈 담당자는 가격에 민감하다"
    rq = definition(env, author_note=note)
    env.ai.llm["ca.extract_slots"] = slots_json(customer=None, place=None, region="수도권", product=None)
    p = (await env.c.post("/v1/parse", json={"requirements_id": rq})).json()
    for k in ("customer", "industry", "place", "product"):
        assert note not in (p["slots"][k]["value"] or "")
    calls = env.ai.llm_calls()
    assert calls and all(c["confidential"] for c in calls if c["task"] in ("ca.extract_slots", "ca.classify_segment", "ca.include_exclude"))
    # 제작자 의견은 LLM 칸 읽기 문맥에도 넣지 않는다
    assert not any(note in c["prompt"] for c in env.ai.llm_calls("ca.extract_slots"))


async def test_parse_rfp_file_mentions(env):
    use_a_coffee(env)
    fid = env.files.add("rfp.pdf", "평가 기준: 본사 일괄 배포, 유지보수 응답 시간. 기존 공급사 ZZ 사이니지 대비 개선안을 제시할 것.")
    env.ai.llm["ca.extract_slots"] = {**slots_json(), "competitor_mentions": ["ZZ 사이니지"], "eval_criteria": ["유지보수 응답 시간"]}
    p = (await env.c.post("/v1/parse", json={"text": A_TEXT, "file_ids": [fid]})).json()
    assert p["rfp"]["competitor_mentions"] == ["ZZ 사이니지"]
    assert p["rfp"]["eval_criteria"] == ["유지보수 응답 시간"]
    assert "ZZ 사이니지" not in NAMES[:0]
