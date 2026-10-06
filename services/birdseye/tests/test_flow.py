"""BE2 · BE3 · BE4 · BE4E — API 흐름(AC 23–28 · 30–38). 골든 공간 · 제품은 저장소에 바로(kb 에 OH55C · WA75D · IAB 가 없다)."""
from __future__ import annotations

import golden
from be_kit import create, drain, seed_golden


async def test_ac23_product_search(client):
    r = await client.get("/v1/product-search", params={"q": "the w", "limit": 5})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "kb 실데이터에 The Wall 이 있어야 한다"
    first = items[0]
    s, e = first["name_match"]
    assert first["name"][s:e].lower() == "the w"
    assert first["subline"] and first["ref"].startswith("kb:")


async def test_ac24_ac25_ac27_furniture(client):
    b = await create(client, description="강남 플래그십 스토어 1층 로비")
    await seed_golden(b["id"], furniture=False)
    r = await client.post(f"/v1/birdseyes/{b['id']}/furniture:recommend", json={})
    assert r.status_code == 202
    await drain()
    fv = (await client.get(f"/v1/birdseyes/{b['id']}/furniture")).json()
    assert [c["code"] for c in fv["cards"]] == ["lounge_sofa_set", "column_wrap_frame", "viewing_bench", "experience_counter"]
    assert [c["selected"] for c in fv["cards"]] == [True, True, True, False]
    reasons = {c["code"]: c["reason"] for c in fv["cards"]}
    assert reasons["viewing_bench"] == "The Wall 정면 · 시청 거리 6m"
    assert reasons["lounge_sofa_set"] == "유리창 앞 · 외부 시선 유도"
    assert reasons["column_wrap_frame"] == "기둥 2개 · 사이니지 매립"
    chips = [f["chip_label"] for f in fv["selected"]]
    assert "기둥 랩핑 프레임 ×2" in chips
    assert fv["w_message"].startswith("공간 특징과 제품 배치를 살리는 가구를 추천합니다.")
    assert fv["echo"].startswith("제품 3개 · Outdoor Signage OH55C")
    # 다른 가구 추천 — 보인 것 제외 다음 4개
    r = await client.post(f"/v1/birdseyes/{b['id']}/furniture:recommend", json={"exclude": fv["shown_codes"]})
    await drain()
    fv2 = (await client.get(f"/v1/birdseyes/{b['id']}/furniture")).json()
    assert not set(fv2["shown_codes"]) & set(fv["shown_codes"])
    # 직접 입력(카탈로그에 없음)
    keep = [{"id": f["id"], "selected": True} for f in fv["selected"]]
    r = await client.put(f"/v1/birdseyes/{b['id']}/furniture", json={"items": keep + [{"name": "안내 로봇"}], "replace": True})
    assert r.status_code == 200, r.text
    robot = next(f for f in r.json() if f["name"] == "안내 로봇")
    assert robot["dims_m"] == {"w": 1.0, "h": 0.8, "d": 0.6} and robot["dims_estimated"] is True
    assert robot["chip_label"] == "안내 로봇 · 치수 추정"
    # 제품 0개면 가구 추천 불가(웹 버튼 비활성과 같은 규칙)
    b2 = await create(client)
    r = await client.post(f"/v1/birdseyes/{b2['id']}/furniture:recommend", json={})
    assert r.status_code == 409


async def test_ac26_no_furniture(client):
    b = await create(client)
    await seed_golden(b["id"])
    r = await client.post(f"/v1/birdseyes/{b['id']}/layout:generate", json={"none": True})
    assert r.status_code == 202
    await drain()
    lv = (await client.get(f"/v1/birdseyes/{b['id']}/layout")).json()
    kinds = {it["kind"] for it in lv["layout"]["items"]}
    assert kinds == {"product"}


async def test_ac28_ac30_ac31_layout(client):
    b = await create(client, description="강남 플래그십 스토어 1층 로비")
    await seed_golden(b["id"])
    r = await client.post(f"/v1/birdseyes/{b['id']}/layout:generate", json={})
    assert r.status_code == 202
    lv0 = (await client.get(f"/v1/birdseyes/{b['id']}/layout")).json()
    assert lv0["running"] is True and lv0["w_message"] == "배치안을 만들고 있어요"
    await drain()
    lv = (await client.get(f"/v1/birdseyes/{b['id']}/layout")).json()
    lay = lv["layout"]
    assert lay["version"] == 1 and not lv["running"]
    assert {g["plan_label"] for g in lay["groups"]} >= {"OH55C ×3 (창면)", 'The Wall IAB 146" (후면 벽)', "Flip Pro WA75D (측벽)",
                                                        "기둥 랩핑 ×2"}
    # 의도 목(p1 · p2 · p3) = 골든 의도 → 엔진 결과가 골든과 같은 좌표
    gold = {it["id"]: (it["x"], it["y"], it["rot_deg"]) for it in __import__("json").load(open(__import__("pathlib").Path(__file__).parent / "golden_layout.json"))["items"]}
    assert {it["id"]: (it["x"], it["y"], it["rot_deg"]) for it in lay["items"]} == gold
    assert lv["tone"] == "warm_wood" and lv["default_view"] == "aerial45"
    assert lv["plan"]["area_label"] == "120평 · 4.5m" and lv["plan"]["window_label"] == "전면 유리창 (도로측)"
    assert lv["w_message"].startswith("배치안입니다.")
    assert any(a["text_ko"].startswith("도면에 후면 벽 폭이 없어") and a["action"] == "BE1D" for a in lay["assumptions"])   # AC 47 근거
    bb = (await client.get(f"/v1/birdseyes/{b['id']}")).json()
    assert bb["step"] == 4 and bb["route"].endswith("/layout")
    # AC 31 배치 수정 요청
    r = await client.post(f"/v1/birdseyes/{b['id']}/layout:nl-edit", json={"text": "관람 벤치를 2열로 줄이고 The Wall 쪽으로 붙여줘"})
    assert r.status_code == 202
    await drain()
    lay2 = (await client.get(f"/v1/birdseyes/{b['id']}/layout")).json()["layout"]
    assert lay2["version"] == 2 and lay2["created_by"] == "nl_edit" and lay2["parent_version"] == 1
    bench = next(g for g in lay2["groups"] if g["ref"] == "bfi_bench")
    assert bench["qty"] == 2 and bench["label"] == "관람 벤치 2열"
    assert any(w["kind"] == "power" for w in lay2["warnings"])


async def test_ac32_to_ac38_session(client):
    b = await create(client, description="강남 플래그십 스토어 1층 로비")
    await seed_golden(b["id"], layout=True)
    be_id = b["id"]
    r = await client.post(f"/v1/birdseyes/{be_id}/layout-sessions")
    assert r.status_code == 201
    sid = r.json()["session_id"]
    assert r.json()["base_version"] == 1
    # 벤치를 디스플레이 가까이(보드 상황) → The Wall 오른쪽 3.0 m
    v = (await client.post(f"/v1/layout-sessions/{sid}/ops", json={"ops": [{"op": "move", "item": "g5", "dx": 0, "dy": 2.9}]})).json()
    v = (await client.post(f"/v1/layout-sessions/{sid}/ops", json={"ops": [{"op": "move", "item": "li1", "dx": 3.0, "dy": 0}]})).json()
    assert v["changes_count"] == 2 and v["can_undo"]
    w = next(x for x in v["warnings"] if x["kind"] == "viewing_angle")
    assert w["message_ko"] == "The Wall을 오른쪽으로 3.0 m 옮겨 관람 벤치 왼쪽 2석이 시야각 밖이에요"
    mv = next(m for m in v["moves"] if m["item_id"] == "li1")
    assert mv["label_ko"] == "오른쪽으로 3.0 m" and mv["from_x"] == 12.55
    # 소파 병목 · 전원
    v = (await client.post(f"/v1/layout-sessions/{sid}/ops", json={"ops": [{"op": "set_pos", "item": "li12", "pos": [7.1, 9.95]}]})).json()
    walk = next(x for x in v["warnings"] if x["kind"] == "walkway")
    assert walk["message_ko"] == "라운지 소파와 기둥 사이 통로 0.6 m · 권장 1.2 m 이상"
    assert any(x["kind"] == "power" and x["message_ko"] == "OH55C ×3에서 가까운 콘센트까지 6.0 m · 바닥 배선 필요" for x in v["warnings"])
    # 되돌리기 · 다시 실행
    v = (await client.post(f"/v1/layout-sessions/{sid}/ops", json={"undo": True})).json()
    assert v["changes_count"] == 2 and v["can_redo"]
    v = (await client.post(f"/v1/layout-sessions/{sid}/ops", json={"redo": True})).json()
    assert v["changes_count"] == 3
    # 경고 모두 자동 조정(AC 36)
    v = (await client.post(f"/v1/layout-sessions/{sid}:autofix")).json()
    st = {}
    for x in v["warnings"]:
        st.setdefault(x["kind"], x["status"])
    assert st.get("viewing_angle") == "fixed" and st.get("walkway") == "fixed"
    assert all(x["status"] == "memo" for x in v["warnings"] if x["kind"] == "power")
    assert v["changes_count"] == 4
    r = await client.post(f"/v1/layout-sessions/{sid}:commit")
    assert r.json() == {"layout_version": 2, "changes_count": 4}
    q = (await client.get(f"/v1/birdseyes/{be_id}/quantities")).json()
    assert any("바닥 배선 필요" in (row.get("memo") or "") for row in q["rows"])
    # AC 38 — 취소하면 버전 그대로
    sid2 = (await client.post(f"/v1/birdseyes/{be_id}/layout-sessions")).json()["session_id"]
    await client.post(f"/v1/layout-sessions/{sid2}/ops", json={"ops": [{"op": "move", "item": "li11", "dx": 0.5, "dy": 0}]})
    assert (await client.post(f"/v1/layout-sessions/{sid2}:discard")).json()["layout_version"] == 2
    assert (await client.get(f"/v1/birdseyes/{be_id}/layout")).json()["layout"]["version"] == 2
    # 경고 수정안 · 전원 위치 추가(AC 33 · 35)
    sid3 = (await client.post(f"/v1/birdseyes/{be_id}/layout-sessions")).json()["session_id"]
    v = (await client.get(f"/v1/layout-sessions/{sid3}")).json()
    pw = next(x for x in v["warnings"] if x["kind"] == "power" and "OH55C" in x["message_ko"])
    v = (await client.post(f"/v1/layout-sessions/{sid3}/warnings/{pw['id']}", json={"action": "add_power", "pos": [6.0, 2.5]})).json()
    assert not any(x["kind"] == "power" and "OH55C" in x["message_ko"] and x["status"] == "open" for x in v["warnings"])
    # 동기 검증(저장 안 함)
    r = await client.post(f"/v1/birdseyes/{be_id}/layout:validate", json={"base_version": 2, "ops": [{"op": "move", "item": "li11", "dx": 0.3, "dy": 0}]})
    assert r.status_code == 200 and r.json()["elapsed_ms"] < 2000
    _ = golden
