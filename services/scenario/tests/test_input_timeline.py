"""SC2 입력 · 라우팅(AC15–19) · SC2E 타임라인 · 페르소나(AC20–27)."""
from __future__ import annotations

from typing import Any

from sc_flow import CHARS, RAW, create, drain, get, ops, parse, timeline


def beat_of(t: dict[str, Any], text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    for sc in t["scenes"]:
        for b in sc["beats"]:
            if b["text"] == text:
                return sc, b
    raise AssertionError(f"비트 없음: {text}")


def slot_of(t: dict[str, Any], label: str) -> dict[str, Any]:
    return next(s for s in t["slots"] if s["label"] == label)


def role_of(t: dict[str, Any], name: str) -> dict[str, Any]:
    return next(r for r in t["roles"] if r["name"] == name)


# ── SC2 ─────────────────────────────────────────────────

async def test_ac15_skeletons(client: Any, world: Any) -> None:
    r = await client.get("/v1/skeletons")
    assert [x["title"] for x in r.json()["items"]] == ["매장 하루", "신메뉴 출시일", "장애 발생 상황"]
    new_menu = r.json()["items"][1]["text"]
    assert new_menu.startswith("전날 본사가 신메뉴 콘텐츠를 예약한다.")
    r = await client.get("/v1/skeletons", params={"industry": "MD"})
    titles = [x["title"] for x in r.json()["items"]]
    assert titles == ["외래 환자 동선", "입원 하루", "장애 발생 상황"]
    assert r.json()["items"][0]["text"].splitlines()[0].startswith("접수.")


async def test_ac16_characters_extract_and_exclude(client: Any, world: Any) -> None:
    sc = await create(client)
    r = await client.post(f"/v1/scenarios/{sc['id']}/characters:extract", json={"raw_text": RAW})
    assert r.status_code == 200, r.text
    assert r.json()["characters"] == CHARS
    # 사용자가 지운 역할은 다시 넣지 않는다(요청 exclude · 저장된 removed_characters 모두)
    r = await client.post(f"/v1/scenarios/{sc['id']}/characters:extract", json={"raw_text": RAW, "exclude": ["손님"]})
    assert "손님" not in r.json()["characters"]
    await client.patch(f"/v1/scenarios/{sc['id']}", json={"removed_characters": ["점장"]})
    r = await client.post(f"/v1/scenarios/{sc['id']}/characters:extract", json={"raw_text": RAW})
    assert "점장" not in r.json()["characters"]


async def test_ac17_routing_sc3_and_sc2e(client: Any, world: Any) -> None:
    sc = await create(client)
    doc = await parse(client, sc["id"])
    assert doc["parse"]["next"] == "SC3", doc["parse"]
    assert doc["scene_count"] == 4
    assert doc["route"].endswith("/solutions")  # R2 → SC3
    # 시각 있는 8줄 → 장면 8 → SC2E + 합치기 권유
    eight = "\n".join(f"{h:02d}:00 점장이 {h}시 업무를 한다." for h in range(8, 16))
    sc2 = await create(client)
    doc2 = await parse(client, sc2["id"], raw=eight, characters=["점장"])
    assert doc2["parse"]["next"] == "SC2E"
    assert doc2["notices"]["too_many"] == 8
    assert doc2["route"].endswith("/timeline")


async def test_ac18_regex_fallback_when_llm_down(client: Any, world: Any) -> None:
    sc = await create(client)
    raw = RAW + " #mock:llm-down"
    doc = await parse(client, sc["id"], raw=raw)
    t = await timeline(client, sc["id"])
    assert [s["time"] for s in t["slots"]] == ["07:00", "11:30", "14:00", "21:00"]
    beats = [b for s in t["scenes"] for b in s["beats"]]
    assert len(beats) == 4
    assert doc["scene_count"] == 4
    # 문장 주어 = 등장인물 칩과 일치하는 역할
    assert {r["name"] for r in t["roles"]} >= {"점장"}


async def test_ac19_real_person_names_become_roles(client: Any, world: Any) -> None:
    sc = await create(client)
    raw = "10:00 점장이 매장을 연다.\n15:00 배우 김민수가 방문해 신메뉴를 소개한다.\n21:00 점장이 마감한다."
    doc = await parse(client, sc["id"], raw=raw, characters=["점장", "손님"])
    assert doc["notices"]["real_names"] is True
    t = await timeline(client, sc["id"])
    texts = " ".join(b["text"] for s in t["scenes"] for b in s["beats"])
    assert "김민수" not in texts and "배우" in texts
    # LLM 요청에도 이름이 가지 않는다
    assert all("김민수" not in p for p in world.ai.prompts("sc.parse_input"))


# ── SC2E ────────────────────────────────────────────────

async def test_ac20_timeline_head_and_new_slot(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    t = await timeline(client, sc["id"])
    # 추천 장면이 붙은 18:00 「저녁 퇴근길」 새 시간대
    assert [(s["time"], s["label"]) for s in t["slots"]] == [("07:00", "오픈"), ("11:30", "점심 피크"), ("14:00", "본사 배포"),
                                                               ("18:00", "저녁 퇴근길"), ("21:00", "마감")]
    assert slot_of(t, "저녁 퇴근길")["is_new"] is True
    assert [r["initial"] for r in t["roles"]] == ["점", "손", "본"]
    # 점장 레인에 「태블릿으로 재고 확인」 새 장면을 넣으면 장면 5
    jang = role_of(t, "점장")
    t = await ops(client, sc["id"], {"op": "add_beat", "slot_id": slot_of(t, "본사 배포")["id"], "role_id": jang["id"],
                                     "text": "태블릿으로 재고 확인", "place": "창고 · 카운터"})
    assert (len(t["slots"]), len(t["roles"]), len(t["scenes"])) == (5, 3, 5)
    _, b = beat_of(t, "태블릿으로 재고 확인")
    assert b["label"] == "새 장면"
    assert t["suggestions"]["roles"] == ["바리스타", "배달 라이더"]


async def test_ac21_move_beat_renumber_and_undo(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    t = await timeline(client, sc["id"])
    jang = role_of(t, "점장")
    t = await ops(client, sc["id"], {"op": "add_beat", "slot_id": slot_of(t, "본사 배포")["id"], "role_id": jang["id"], "text": "태블릿으로 재고 확인"})
    before = t
    n0 = t["changes_count"]
    _, b = beat_of(t, "태블릿으로 재고 확인")
    t = await ops(client, sc["id"], {"op": "move_beat", "beat_id": b["id"], "to_slot_id": slot_of(t, "점심 피크")["id"], "to_role_id": jang["id"]})
    scene, moved = beat_of(t, "태블릿으로 재고 확인")
    assert scene["no"] == 2 and moved["label"] == "장면 2 · 점장 시점"
    assert len(t["scenes"]) == 4  # 비어 버린 새 장면은 지워지고 번호가 다시 매겨진다
    assert t["changes_count"] == n0 + 1
    r = await client.post(f"/v1/scenarios/{sc['id']}/timeline/ops", json={"undo": True})
    t2 = r.json()
    assert t2["changes_count"] == n0
    assert [s["id"] for s in t2["scenes"]] == [s["id"] for s in before["scenes"]]
    _, b2 = beat_of(t2, "태블릿으로 재고 확인")
    assert b2["label"] == "새 장면"
    assert t2["can_redo"] is True


async def test_ac22_merge_prune_split(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    t = await timeline(client, sc["id"])
    jang = role_of(t, "점장")
    # 같은 시간대에 장면을 하나 더 → 합치기
    t = await ops(client, sc["id"], {"op": "add_beat", "slot_id": slot_of(t, "오픈")["id"], "role_id": jang["id"], "text": "재고 확인"})
    assert sum(1 for s in t["scenes"] if s["slot_id"] == slot_of(t, "오픈")["id"]) == 2
    t = await ops(client, sc["id"], {"op": "merge_same_time"})
    per: dict[str, int] = {}
    for s in t["scenes"]:
        per[s["slot_id"]] = per.get(s["slot_id"], 0) + 1
    assert set(per.values()) == {1}
    # 빈 시간대(18:00) 정리
    t = await ops(client, sc["id"], {"op": "prune_empty_slots"})
    assert "저녁 퇴근길" not in [s["label"] for s in t["slots"]]
    # 장면 나누기: 비트 2개인 「오픈」 장면 → 같은 시간대 두 장면
    open_scene = next(s for s in t["scenes"] if s["slot_id"] == slot_of(t, "오픈")["id"])
    assert len(open_scene["beats"]) == 2
    t = await ops(client, sc["id"], {"op": "split_scene", "scene_id": open_scene["id"]})
    assert sum(1 for s in t["scenes"] if s["slot_id"] == slot_of(t, "오픈")["id"]) == 2
    r = await client.post(f"/v1/scenarios/{sc['id']}/timeline/ops", json={"ops": [{"op": "split_scene", "scene_id": None}]})
    assert r.status_code == 400 and r.json()["error"]["code"] == "SCENE_REQUIRED"


async def test_ac23_suggestion_accept_and_dismiss(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    t = await timeline(client, sc["id"])
    sug = t["suggestions"]["scene"]
    assert sug["text"] == "퇴근길 모바일 주문 픽업"
    assert sug["slot_id"] == slot_of(t, "저녁 퇴근길")["id"] and sug["role_id"] == role_of(t, "손님")["id"]
    t = await ops(client, sc["id"], {"op": "accept_suggestion"})
    scene, b = beat_of(t, "퇴근길 모바일 주문 픽업")
    assert scene["slot_id"] == slot_of(t, "저녁 퇴근길")["id"] and b["role_id"] == role_of(t, "손님")["id"]
    assert t["suggestions"]["scene"] is None
    # 닫기: 다른 시나리오에서 닫으면 다시 나오지 않는다(다시 파싱해도)
    sc2 = await create(client)
    await parse(client, sc2["id"])
    t2 = await ops(client, sc2["id"], {"op": "dismiss_suggestion"})
    assert t2["suggestions"]["scene"] is None
    await parse(client, sc2["id"])
    t3 = await timeline(client, sc2["id"])
    assert t3["suggestions"]["scene"] is None


async def test_ac24_add_suggested_role(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    t = await ops(client, sc["id"], {"op": "add_role", "name": "바리스타", "suggested": True})
    assert len(t["roles"]) == 4 and t["roles"][-1]["name"] == "바리스타"
    assert "바리스타" not in t["suggestions"]["roles"]
    r = await client.post(f"/v1/scenarios/{sc['id']}/timeline/ops", json={"ops": [{"op": "add_role", "name": "바리스타"}]})
    assert r.status_code == 409


async def test_ac25_persona_change_rewrites_only_that_lane(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    t = await timeline(client, sc["id"])
    jang = role_of(t, "점장")
    others_before = {b["id"]: b["text"] for s in t["scenes"] for b in s["beats"] if b["role_id"] != jang["id"]}
    jang_before = {b["id"]: b["text"] for s in t["scenes"] for b in s["beats"] if b["role_id"] == jang["id"]}
    n_calls = len(world.ai.calls("sc.lane_rewrite"))
    r = await client.patch(f"/v1/scenarios/{sc['id']}/roles/{jang['id']}", json={"pains": [*jang["pains"], "품절 표시 늦음"]})
    assert r.status_code == 200, r.text
    tl_ = r.json()
    assert tl_["job_id"] and jang["id"] in tl_["rewriting_role_ids"]
    await drain()
    assert len(world.ai.calls("sc.lane_rewrite")) == n_calls + 1
    t2 = await timeline(client, sc["id"])
    assert t2["rewriting_role_ids"] == []
    others_after = {b["id"]: b["text"] for s in t2["scenes"] for b in s["beats"] if b["role_id"] != jang["id"]}
    jang_after = {b["id"]: b["text"] for s in t2["scenes"] for b in s["beats"] if b["role_id"] == jang["id"]}
    assert others_after == others_before
    assert jang_after != jang_before
    assert "품절 표시 늦음" in role_of(t2, "점장")["pains"]
    # 이름만 바꾸면 잡이 없다
    r = await client.patch(f"/v1/scenarios/{sc['id']}/roles/{jang['id']}", json={"name": "매장 점장"})
    assert r.json()["job_id"] is None


async def test_ac26_nl_edit_adds_beat(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    r = await client.post(f"/v1/scenarios/{sc['id']}/timeline:nl-edit", json={"text": "손님 레인 18:00에 퇴근길 픽업 장면 추가"})
    assert r.status_code == 202
    await drain()
    t = await timeline(client, sc["id"])
    scene, b = beat_of(t, "퇴근길 모바일 주문 픽업")
    assert slot_of(t, "저녁 퇴근길")["id"] == scene["slot_id"] and b["role_id"] == role_of(t, "손님")["id"]
    assert t["changes_count"] >= 1
    doc = await get(client, sc["id"])
    assert doc["active_job"] is None


async def test_ac27_timeline_text(client: Any, world: Any) -> None:
    sc = await create(client)
    await parse(client, sc["id"])
    r = await client.get(f"/v1/scenarios/{sc['id']}/timeline:text")
    lines = r.json()["raw_text"].splitlines()
    assert lines[0].startswith("07:00 오픈. 점장: 아침 메뉴로 켜진 메뉴보드 확인(카운터).")
    assert lines[-1].startswith("21:00 마감.")
