"""SC0 목록(AC1–4) · SC1 조감도 추가(AC7) · SC1T 업종 템플릿(AC8–10) · SC1B 조감도에서 이어 만들기(AC11–14)."""
from __future__ import annotations

from typing import Any

from sc_flow import (
    QM55C,
    board,
    create,
    drain,
    generate,
    get,
    parse,
    pick,
    scenes,
    timeline,
)
from sc_world import GANGNAM, LOGISTICS


async def _update(sid: str, **fields: Any) -> None:
    from winmate_scenario import repo

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d.update(fields)
        return d
    await repo.update(sid, fn)


# ── SC0 ─────────────────────────────────────────────────

async def test_ac1_ac2_ac4_list_rows_counts_and_start_labels(client: Any, world: Any) -> None:
    done_used = await board(client)
    await client.post(f"/v1/scenarios/{done_used['id']}/usages", json={"service": "proposal", "ref": "pr_x", "label": "A 커피 제안", "version": 1})
    done_fresh = await board(client)
    draft3 = await create(client)
    await parse(client, draft3["id"])
    await pick(client, draft3["id"], ["magicinfo"])
    gen = await create(client)
    await parse(client, gen["id"])
    await pick(client, gen["id"], ["magicinfo"])
    await client.post(f"/v1/scenarios/{gen['id']}:route-generate")
    r = await client.post(f"/v1/scenarios/{gen['id']}/generate", json={"scope": "all"})
    assert r.status_code == 202  # 잡은 아직 돌리지 않는다 → 생성 중
    be_draft = await create(client)
    await _update(be_draft["id"], start_mode="birdseye", birdseye_link={"birdseye_id": LOGISTICS, "title": "C 물류센터 관제실", "linked_version": 2,
                                                                        "keep_link": True, "changed": None, "zone_ids": [], "order": []})
    await _update(draft3["id"], start_mode="template", template={"industry": "MD", "preset_index": 1}, vertical_code="MD")
    world.be.bump(LOGISTICS, at="2026-09-30T02:00:00Z")

    r = await client.get("/v1/scenarios", params={"limit": 50})
    data = r.json()
    rows = {x["id"]: x for x in data["items"]}
    c = data["counts"]
    assert (c["all"], c["draft"], c["generating"], c["done"]) == (5, 2, 1, 2)
    assert (rows[done_used["id"]]["status_label"], rows[done_used["id"]]["status_sub"]) == ("완료", "제안서에 사용 중")
    assert (rows[done_fresh["id"]]["status_label"], rows[done_fresh["id"]]["status_sub"]) == ("완료", "제안서에 아직 안 넣음")
    assert (rows[draft3["id"]]["status_label"], rows[draft3["id"]]["status_sub"]) == ("작성 중", "3 / 4 · 솔루션 · 제품 입력")
    assert (rows[gen["id"]]["status_label"], rows[gen["id"]]["status_sub"]) == ("생성 중", "장면 1 / 4 작성 중")
    assert (rows[be_draft["id"]]["status_label"], rows[be_draft["id"]]["status_sub"]) == ("작성 중", "조감도가 바뀌었어요")
    assert rows[be_draft["id"]]["birdseye_changed"] is True
    assert data["total"] == 5
    # AC2: 보내기 아이콘(완료 행) — 행 상태 · route 로 판단
    assert rows[done_used["id"]]["route"].endswith("/result") and rows[gen["id"]]["route"].split("/")[-2] == "generate"
    # AC4: 시작 방식
    assert rows[done_used["id"]]["start_label"] == "직접 입력"
    assert rows[draft3["id"]]["start_label"] == "업종 템플릿 · 의료"
    assert rows[be_draft["id"]]["start_label"] == "조감도 · C 물류센터 관제실"
    # 필터 · 검색
    r = await client.get("/v1/scenarios", params={"status": "done"})
    assert {x["id"] for x in r.json()["items"]} == {done_used["id"], done_fresh["id"]}
    r = await client.get("/v1/scenarios", params={"start_mode": "template"})
    assert [x["id"] for x in r.json()["items"]] == [draft3["id"]]


async def test_ac3_birdseye_alert_dismiss_and_keep_link(client: Any, world: Any) -> None:
    a = await create(client)
    await _update(a["id"], start_mode="birdseye", birdseye_link={"birdseye_id": LOGISTICS, "title": "C 물류센터 관제실", "linked_version": 2,
                                                                 "keep_link": True, "changed": None, "zone_ids": [], "order": []})
    b = await create(client)
    await _update(b["id"], start_mode="birdseye", birdseye_link={"birdseye_id": GANGNAM, "title": "강남 플래그십 1층 로비", "linked_version": 3,
                                                                 "keep_link": False, "changed": None, "zone_ids": [], "order": []})
    r = await client.get("/v1/scenarios")
    assert r.json()["alert"] is None
    world.be.bump(LOGISTICS, at="2026-09-30T02:00:00Z")
    world.be.bump(GANGNAM, at="2026-09-30T02:00:00Z")  # keep_link=false → 알림 없음
    from winmate_scenario import birdseye as be
    be.clear_cache()
    alert = (await client.get("/v1/scenarios")).json()["alert"]
    assert alert["title"] == "C 물류센터 관제실" and alert["changed_label"] == "9월 30일" and alert["scenario_ids"] == [a["id"]]
    r = await client.post(f"/v1/scenarios/{a['id']}/alerts:dismiss")
    assert r.status_code == 204
    assert (await client.get("/v1/scenarios")).json()["alert"] is None
    # 같은 변경으로는 다시 보이지 않지만 행 상태는 남는다
    rows = {x["id"]: x for x in (await client.get("/v1/scenarios")).json()["items"]}
    assert rows[a["id"]]["status_sub"] == "조감도가 바뀌었어요" and rows[b["id"]]["birdseye_changed"] is False


async def test_clone_delete_and_image_return_unknown(client: Any, world: Any) -> None:
    sc = await board(client)
    r = await client.post(f"/v1/scenarios/{sc['id']}:clone")
    assert r.status_code == 201
    clone = await get(client, r.json()["id"])
    assert clone["title"].endswith("(복제)") or clone["title"] != sc["title"] or clone["id"] != sc["id"]
    assert len(await scenes(client, clone["id"])) == 4
    r = await client.delete(f"/v1/scenarios/{clone['id']}")
    assert r.status_code == 204
    assert (await client.get(f"/v1/scenarios/{clone['id']}")).status_code == 404
    r = await client.post("/v1/image-returns", json={"request_id": "irq_nope", "image_version_id": "imv_x"})
    assert r.status_code == 404


# ── SC1 조감도 추가 ───────────────────────────────────────

async def test_ac7_aerial_new_creates_birdseye_once(client: Any, world: Any) -> None:
    r = await client.post("/v1/scenarios", json={"type": "with", "aerial": {"enabled": True, "source": "new"}})
    sid = r.json()["id"]
    await parse(client, sid)
    await pick(client, sid, ["magicinfo"])
    r = await client.post(f"/v1/scenarios/{sid}:route-generate")
    assert r.status_code == 200 and r.json()["aerial_birdseye_id"]
    assert len(world.be.created) == 1
    body = world.be.created[0]
    assert body["origin"]["service"] == "scenario" and body["origin"]["ref"] == sid
    assert "fam_G000182628" in body["prefill"]["products"]
    doc = await get(client, sid)
    assert doc["aerial"]["birdseye_id"] == r.json()["aerial_birdseye_id"]
    await client.post(f"/v1/scenarios/{sid}:route-generate")  # 두 번째는 다시 만들지 않는다
    assert len(world.be.created) == 1
    # 꺼져 있으면 호출이 없다
    off = await create(client)
    await parse(client, off["id"])
    await pick(client, off["id"], ["magicinfo"])
    await client.post(f"/v1/scenarios/{off['id']}:route-generate")
    assert len(world.be.created) == 1


async def test_aerial_existing_link_and_options(client: Any, world: Any) -> None:
    r = await client.get("/v1/birdseye-options")
    opts = r.json()
    assert opts["count"] == 2 and opts["items"][0]["label"].endswith("· 존 5")
    r = await client.post("/v1/scenarios", json={"type": "with", "aerial": {"enabled": True, "source": "existing", "birdseye_id": GANGNAM}})
    doc = r.json()
    assert doc["birdseye_link"]["birdseye_id"] == GANGNAM and doc["birdseye_link"]["keep_link"] is False
    assert doc["aerial"]["title"] == "강남 플래그십 1층 로비"


# ── SC1T ────────────────────────────────────────────────

async def test_ac8_ac9_industries(client: Any, world: Any) -> None:
    r = await client.get("/v1/industries")
    data = r.json()
    items = data["items"]
    assert len(items) == 16 and [x["code"] for x in items][:3] == ["FB", "RT", "SV"]
    assert data["default_code"] == "FB"
    fb = items[0]
    assert fb["name"] == "외식 · 카페 프랜차이즈"
    p1 = fb["presets"][0]
    assert (p1["t"], p1["n"], p1["f"], p1["r"]) == ("매장 하루", "장면 4", "오픈 → 점심 피크 → 본사 배포 → 마감", "점장 · 손님 · 본사 담당자")
    assert len(fb["spaces"]) == 5 and len(fb["needs"]) == 4
    assert fb["used_line"] == "시스템에어컨 · LCD 사이니지 · 갤럭시 탭 · 파트너 앱 · 주문 결제 · MagicINFO"
    # AC9: 「병실」은 의료 타일만(웹 거르기 규칙 = 이름 · 대표 공간 부분 일치)
    hits = [x["name"] for x in items if any("병실" in s for s in [x["name"], *x["spaces"]])]
    assert hits == ["의료 · 요양 · 케어"]


async def test_ac10_from_template_with_and_without(client: Any, world: Any) -> None:
    r = await client.post("/v1/scenarios:from-template", json={"industry": "FB", "preset_index": 1, "type": "with"})
    assert r.status_code == 202
    sid = r.json()["scenario_id"]
    await drain()
    doc = await get(client, sid)
    assert doc["route"].endswith("/timeline") and doc["start_mode"] == "template"
    t = await timeline(client, sid)
    assert [s["label"] for s in t["slots"]] == ["오픈", "점심 피크", "본사 배포", "마감"]
    assert [r_["name"] for r_ in t["roles"]] == ["점장", "손님", "본사 담당자"]
    assert len(t["scenes"]) == 4
    assert [p["name"] for p in doc["solution_picks"]] == ["MagicINFO"]
    assert doc["needs"] == ["디자인 조화", "고객 경험", "쾌적 · 공기질", "업무 효율"]
    r = await client.post("/v1/scenarios:from-template", json={"industry": "FB", "preset_index": 1, "type": "without"})
    await drain()
    doc2 = await get(client, r.json()["scenario_id"])
    assert doc2["type"] == "without" and doc2["solution_picks"] == []


# ── SC1B ────────────────────────────────────────────────

async def test_ac11_birdseye_preview(client: Any, world: Any) -> None:
    r = await client.get(f"/v1/birdseye-options/{GANGNAM}")
    assert r.status_code == 200, r.text
    p = r.json()
    zones = p["zones"]
    assert len(zones) == 5 and sum(1 for z in zones if z["included"]) == 4
    z5 = zones[4]
    assert (z5["state"], z5["included"], z5["sub"]) == ("empty", False, "배치 제품 없음 · 랩핑 포인트만 지정")
    assert zones[3]["sub"] == "가구만 배치 · 제품은 다음 단계에서 추천"
    assert zones[0]["sub"] == "OH55C ×3 · 거리에서 보이는 첫인상"
    assert p["axes"][0] == "방문객 동선" and len(p["axes"]) == 3
    assert p["order"] == ["bez_1", "bez_2", "bez_3", "bez_4"]
    assert p["plan"]["area_pyeong"] == 120 and p["plan"]["zone_count"] == 5


async def test_ac12_ac13_from_birdseye_order_and_usage(client: Any, world: Any) -> None:
    order = ["bez_1", "bez_3", "bez_2", "bez_4"]  # 2 · 3 을 바꿈(AC13)
    r = await client.post("/v1/scenarios:from-birdseye", json={"birdseye_id": GANGNAM, "zone_ids": order, "axis": "방문객 동선", "order": order,
                                                               "keep_link": True, "type": "with"})
    assert r.status_code == 202, r.text
    sid = r.json()["scenario_id"]
    await drain()
    items = await scenes(client, sid)
    assert len(items) == 4
    assert [s["place"] for s in items] == ["쇼윈도 · 전면 유리창", "체험 · 시연 존", "후면 미디어월", "라운지 · 안내 데스크"]
    assert items[0]["products"][0]["short"] == "OH55C" and items[0]["products"][0]["qty"] == 3
    assert all(s["time"] is None for s in items)
    assert [b for b, _ in world.be.usages] == [GANGNAM]
    doc = await get(client, sid)
    assert doc["birdseye_link"]["keep_link"] is True and doc["birdseye_link"]["linked_version"] == 3


async def test_ac14_resync_updates_products_only(client: Any, world: Any) -> None:
    order = ["bez_1", "bez_2", "bez_3", "bez_4"]
    r = await client.post("/v1/scenarios:from-birdseye", json={"birdseye_id": GANGNAM, "zone_ids": order, "axis": "방문객 동선", "order": order,
                                                               "keep_link": True, "type": "with"})
    sid = r.json()["scenario_id"]
    await drain()
    await pick(client, sid, ["magicinfo"], [QM55C])
    await client.post(f"/v1/scenarios/{sid}:route-generate")
    await generate(client, sid)
    before = await scenes(client, sid)
    # 장면 1 에 이미지가 있다고 치고(조건 스냅숏) 존 1 제품이 바뀐다
    from winmate_scenario import repo

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = d["scenes"][0]
        s["image"] = {"image_id": "img_x", "version_id": "imv_x", "aspect": "16:9", "source": "picked", "url": None, "thumb_url": None,
                      "snapshot": {"products": [p.get("short") for p in s.get("products") or []], "characters": [], "solutions": []}}
        return d
    await repo.update(sid, fn)
    world.be.bump(GANGNAM)
    r = await client.post(f"/v1/scenarios/{sid}/birdseye:resync", json={"apply": False})
    diff = r.json()
    assert diff["summary"] == "존 1개 바뀜 · 제품 1개 바뀜", diff
    assert [z["change"] for z in diff["zones"] if z["change"] != "same"] == ["changed"]
    r = await client.post(f"/v1/scenarios/{sid}/birdseye:resync", json={"apply": True})
    assert r.json()["applied"] is True
    after = await scenes(client, sid)
    assert after[0]["products"][0]["qty"] == 4
    assert after[0]["story"] == before[0]["story"]
    assert after[0]["story_check"] is True and after[0]["image_stale"]
    assert after[1]["products"] == before[1]["products"]
