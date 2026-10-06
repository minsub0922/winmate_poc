"""기능 서비스용 질의 패턴 엔드포인트(POST /v1/query/{code}) — 봉투 스모크 + 원본(query.py)과 같은 결과."""
from __future__ import annotations

import pytest

ENVELOPE_KEYS = {"pattern", "result", "evidence_paths", "tier_min", "candidates", "decision_hint", "decision_reasons",
                 "needs_confirmation", "fallback_level", "modes_used", "timings_ms", "kb_version"}

BODIES = {
    "S1": {"text": "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"},
    "S2": {"vertical": "kr_hotel", "space": "guest_room"},
    "A1": {"text": "병원 로비 대기실에 MagicINFO로 관리하는 24시간 사이니지"},
    "A2": {"text": "공장 생산 라인 작업자용 산업용 태블릿"},
    "A3": {"items": [{"name_raw": "화면 크기", "value_raw": "55인치 이상"}, {"name_raw": "밝기", "value_raw": "500nit 이상"}]},
    "B1": {"vertical_id": "kr_hospital"},
    "B2": {"text": "호텔 로비에 사이니지"},
    "C1": {"spaces": ["lobby"], "text": "24시간 운영"},
    "C2": {"capabilities": ["touch_interactive"], "space": "classroom", "vertical": "kr_school"},
    "C3": {"family_id": "fam_G000183751"},
    "C4": {"family_id": "fam_G000182628", "capabilities": ["weatherproof"], "category": "cat_smart-signage"},
    "C6": {"ref": "fam_G000181132", "requirements": [{"key": "brightness_nit", "op": ">=", "value": 2500},
                                                    {"key": "capacity_l", "op": ">=", "value": 100}]},
    "D1": {"vertical": "kr_education", "spaces": ["classroom"], "targets": [["category", "cat_smart-signage__flip"]], "text": "전자칠판 수업"},
    "D2": {"vertical": "kr_retail_fnb"},
    "D3": {"deployment_ids": ["dep_1490"]},
    "D5": {"targets": [{"kind": "category", "id": "cat_hotel-tvs"}]},
    "E1": {"vertical": "kr_hotel"},
    "E2": {"theme": "에너지 절감과 원격 제어"},
    "E3": {"vertical": "kr_hotel", "spaces": ["guest_room"], "customer": "비즈니스호텔 체인", "text": "객실 TV를 통합 관리하고 투숙객 만족도를 높이고 싶어"},
    "G1": {"space": "guest_room", "category": "cat_hotel-tvs"},
    "G2": {"kind": "family", "ident": "fam_G000182628"},
    "G4": {"family_id": "fam_G000182628"},
    "G5": {"deployment_id": "dep_1490"},
    "search": {"text": "병상 태블릿 환자 소통"},
    "image_search": {"text": "사무실 천장 무풍 시스템에어컨"},
    "images": {"text": "카페 메뉴보드", "limit": 5},
    "get_entity": {"kind": "solution", "ident": "sol_magicinfo"},
    "entity": {"kind": "family", "ident": "fam_G000182628"},
}


async def test_patterns_list(client, ok):
    body = ok(await client.get("/v1/patterns"))
    codes = [p["code"] for p in body["items"]]
    assert codes == ["S1", "S2", "A1", "A2", "A3", "B1", "B2", "C1", "C2", "C3", "C4", "C6", "D1", "D2", "D3", "D5",
                     "E1", "E2", "E3", "G1", "G2", "G4", "G5", "search", "image_search", "get_entity"]
    for p in body["items"]:
        assert p["description"] and p["name"] and p["route"] == f"/v1/query/{p['code']}"
        assert p["request_schema"]["type"] == "object"
    assert set(body["envelope_fields"]) >= ENVELOPE_KEYS - {"kb_version"}


@pytest.mark.parametrize("code", list(BODIES))
async def test_pattern_envelope(client, ok, code):
    env = ok(await client.post(f"/v1/query/{code}", json=BODIES[code]), "POST")
    assert ENVELOPE_KEYS <= set(env)
    assert env["decision_hint"] in ("auto", "check", "ask")
    assert isinstance(env["result"], dict) and env["result"]
    assert env["kb_version"] == "kb_v1"
    want = {"images": "image_search", "entity": "get_entity"}.get(code, code)
    assert env["pattern"] == want


async def test_pattern_validation_error(client):
    r = await client.post("/v1/query/S1", json={"txt": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
    r = await client.post("/v1/query/C6", json={"ref": "mdl_x", "requirements": [{"key": "a", "op": "~", "value": 1}]})
    assert r.status_code == 422


async def test_pattern_results_match_query_py(client, ok):
    """서비스 결과 = winmate-kb/build/query.py 결과(봉투의 시간 · kb_version · 로컬 이미지 주소만 다르다)."""
    from winmate_kb.engine import engine

    E = engine()
    base = E.Q.KB(E.db_path)
    cases = [
        ("D1", BODIES["D1"], lambda: base.D1(vertical="kr_education", spaces=["classroom"], targets=[("category", "cat_smart-signage__flip")], text="전자칠판 수업")),
        ("B1", BODIES["B1"], lambda: base.B1("kr_hospital")),
        ("C2", BODIES["C2"], lambda: base.C2(["touch_interactive"], space="classroom", vertical="kr_school")),
        ("E2", BODIES["E2"], lambda: base.E2("에너지 절감과 원격 제어")),
        ("A1", BODIES["A1"], lambda: base.A1(BODIES["A1"]["text"])),
    ]
    for code, body, fn in cases:
        mine = ok(await client.post(f"/v1/query/{code}", json=body), "POST")
        theirs = fn()
        assert mine["result"] == theirs["result"], code
        assert mine["decision_hint"] == theirs["decision_hint"] and mine["candidates"] == theirs["candidates"], code


async def test_a2_raw_score_and_same_ranking(client, ok):
    from winmate_kb.engine import engine

    E = engine()
    base = E.Q.KB(E.db_path)
    for text in ("공장 생산 라인 작업자용 산업용 태블릿", "호텔 객실 TV 통합 관리", "카페 메뉴보드"):
        mine = ok(await client.post("/v1/query/A2", json={"text": text}), "POST")
        theirs = base.A2(text)
        assert [(c["id"], c["score"]) for c in mine["candidates"]] == [(c["id"], c["score"]) for c in theirs["candidates"]]
        assert mine["decision_hint"] == theirs["decision_hint"]
        assert all(isinstance(c["raw_score"], float) for c in mine["candidates"])
        top = mine["candidates"][0]
        assert top["raw_score"] >= top["score"] * 0 and mine["result"]["top2"][0]["raw_score"] == top["raw_score"]


async def test_a3_inch_and_c6_attr_name(client, ok):
    env = ok(await client.post("/v1/query/A3", json=BODIES["A3"]), "POST")
    size = next(m for m in env["result"]["mapped"] if m["name_raw"] == "화면 크기")
    assert size["attr"] == "screen_size_inch" and size["unit"] == "inch" and size["value"] == 55 and size["value_cm"] == 139.7
    env = ok(await client.post("/v1/query/C6", json={"ref": "mdl_LH55QMCEBGCXKR", "requirements": [
        {"key": "power_consumption", "op": "<=", "value": 1, "attr_name": "소비전력 (Sleep Mode)"},
        {"key": "power_consumption", "op": "<=", "value": 200, "attr_name": "소비전력 (On Mode)"},
        {"key": "power_consumption", "op": "<=", "value": 200, "attr_name": "소비전력 (Typical)"}]}), "POST")
    rows = env["result"]["rows"]
    assert [r["verdict"] for r in rows] == ["pass", "pass", "unknown"]
    assert rows[0]["actual"] == "0.5 W" and rows[1]["actual"] == "154 W"


async def test_image_rows_get_local_urls(client, ok):
    env = ok(await client.post("/v1/query/G4", json={"family_id": "fam_G000182628"}), "POST")
    for im in env["result"]["images"]:
        assert im["thumb_url"] == f"/api/kb/v1/images/{im['id']}/thumb"
        assert im["stored_url"] == f"/api/kb/v1/images/{im['id']}/file"
        assert im["kind"] == "product" and im["has_local"] is True
    env = ok(await client.post("/v1/query/S2", json={"vertical": "kr_hotel", "space": "guest_room"}), "POST")
    imgs = [im for s in env["result"]["scenes"] for im in s["images"]]
    assert imgs and all("thumb_url" in im for im in imgs)


async def test_entity_not_found(client, ok):
    env = ok(await client.post("/v1/query/get_entity", json={"kind": "family", "ident": "fam_nope"}), "POST")
    assert env["result"] is None and "NOT_FOUND" in env["decision_reasons"]
    r = await client.get("/v1/entities/family/fam_nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    env = ok(await client.get("/v1/entities/solution/sol_magicinfo"))
    assert env["pattern"] == "get_entity" and env["result"]["id"] == "sol_magicinfo"
