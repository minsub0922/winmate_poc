"""SC4 결과 · SC4E 장면 편집(AC40–48) · 장면 이미지(요청 · 일괄 렌더 · 고르기)."""
from __future__ import annotations

from typing import Any

import pytest
from sc_flow import board, by_no, drain, get, scenes
from winmate_common import testing


async def scene(client: Any, sid: str) -> dict[str, Any]:
    r = await client.get(f"/v1/scenes/{sid}")
    assert r.status_code == 200, r.text
    return r.json()


async def drain_image() -> int:
    return await testing.drain_jobs("image", testing.load_service_worker("image"))


@pytest.fixture
def image_wait(world: Any) -> Any:
    """일괄 렌더: image 워커를 그 자리에서 돌린 뒤 렌더 결과를 읽게 한다(실제 image 앱 · mock T2I)."""
    from winmate_scenario import imaging
    old = imaging.wait_render

    async def wait(render_id: str) -> dict[str, Any]:
        for _ in range(5):
            await drain_image()
            r = await imaging.get_render(render_id)
            if r.get("status") in ("succeeded", "failed", "canceled"):
                return r
        return r
    imaging.wait_render = wait
    yield
    imaging.wait_render = old


async def test_ac40_scene_cards(client: Any, world: Any) -> None:
    sc = await board(client)
    items = await scenes(client, sc["id"])
    for s in items:
        assert s["title"].startswith(f"{s['label']} — ")
        assert s["story"] and s["status"] == "done" and s["version"] == 1
    s1 = by_no(items, 1)
    assert s1["solution_chips"] == ["MagicINFO · 전원 스케줄"]
    assert [p["short"] for p in s1["products"]] == ["QM55C"] and s1["products"][0]["qty"] == 3
    assert by_no(items, 3)["solution_chips"] == ["MagicINFO · 원격 배포 · 장애 알림"]
    assert by_no(items, 1)["image"] is None


async def test_ac41_image_request_then_fulfilled_attaches(client: Any, world: Any, image_wait: Any) -> None:
    sc = await board(client)
    s1 = by_no(await scenes(client, sc["id"]), 1)
    r = await client.post(f"/v1/scenes/{s1['id']}/image-request")
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["image_route"].startswith("/image/w/") and out["request_id"].startswith("irq_")
    req_body = next(b for p, b in world.image.requests if p == "/v1/requests" and b)
    pf = req_body["prefill"]
    assert (pf["kind"], pf["aspect"]) == ("scenario", "16:9")
    assert any(p.get("short") == "QM55C" for p in pf["products"]) and pf["space_label"]
    assert any(p.endswith(":start") for p, _ in world.image.requests)
    # 다른 장면을 일괄 렌더로 만들어 버전을 얻고, 그 버전으로 요청을 충족한다(IMG4 「공간 시나리오 장면으로」 흉내)
    r = await client.post(f"/v1/scenarios/{sc['id']}/images:generate-missing")
    await drain()
    s2 = by_no(await scenes(client, sc["id"]), 2)
    assert s2["image"] and s2["image"]["version_id"]
    async with testing.api_client(world.image) as img:
        r = await img.post(f"/v1/requests/{out['request_id']}:fulfill", json={"version_id": s2["image"]["version_id"]})
        assert r.status_code == 200, r.text
    r = await client.post(f"/v1/scenarios/{sc['id']}/images:sync")
    assert s1["id"] in r.json()["attached"]
    s1b = await scene(client, s1["id"])
    assert s1b["image"]["version_id"] == s2["image"]["version_id"] and s1b["image"]["source"] == "image_flow"
    # IMG4 → /scenario?image_version=&request= 경로도 같은 장면을 찾는다
    r = await client.post("/v1/image-returns", json={"request_id": out["request_id"], "image_version_id": s2["image"]["version_id"]})
    assert r.json()["route"] == f"/scenario/{sc['id']}/scenes/{s1['id']}"


async def test_ac42_generate_missing_renders_each_once(client: Any, world: Any, image_wait: Any) -> None:
    sc = await board(client)
    r = await client.post(f"/v1/scenarios/{sc['id']}/images:generate-missing")
    assert r.status_code == 202
    await drain()
    renders = [b for p, b in world.image.requests if p == "/v1/renders" and b]
    assert len(renders) == 4
    assert [b["origin"]["ref"] for b in renders] == [s["id"] for s in await scenes(client, sc["id"])]
    assert all(b["aspect"] == "16:9" and b["target"] == "fhd" and b["kind"] == "scene" for b in renders)
    items = await scenes(client, sc["id"])
    assert all(s["image"] and s["image"]["source"] == "image_render" for s in items)
    assert all(s["image_job"] is None for s in items)
    # 사용 등록(image usages)
    usages = [p for p, _ in world.image.requests if p.endswith("/usages")]
    assert len(usages) == 4
    r = await client.post(f"/v1/scenarios/{sc['id']}/images:generate-missing")
    assert r.status_code == 400 and r.json()["error"]["code"] == "NOTHING_TO_GENERATE"


async def test_ac43_ac44_edit_request_new_version_and_stale(client: Any, world: Any) -> None:
    sc = await board(client)
    s2 = by_no(await scenes(client, sc["id"]), 2)
    # 이미지 스냅숏(제품 KM24C · QM55C)이 있다고 친다
    from winmate_scenario import repo

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = next(x for x in d["scenes"] if x["id"] == s2["id"])
        s["image"] = {"image_id": "img_x", "version_id": "imv_x", "aspect": "16:9", "source": "image_flow", "n": 1, "created_at": "2026-10-06T01:00:00Z",
                      "snapshot": {"products": ["KM24C", "QM55C"]}}
        return d
    await repo.update(sc["id"], fn)
    r = await client.post(f"/v1/scenarios/{sc['id']}:edit", json={"text": "장면 2에 점장이 태블릿으로 재고 확인하는 장면 추가"})
    assert r.status_code == 202
    doc = await get(client, sc["id"])
    assert doc["active_job"]["kind"] == "edit"
    await drain()
    items = await scenes(client, sc["id"])
    s2b = by_no(items, 2)
    assert s2b["version"] == 2 and s2b["reason"] == "방금 수정 요청 반영"
    assert all(by_no(items, n)["version"] == 1 for n in (1, 3, 4))  # 장면 2 만 다시 썼다
    new_chars = [c["name"] for c in s2b["characters"] if c["is_new"]]
    new_prods = [p["short"] for p in s2b["products"] if p["is_new"]]
    new_sols = [x["label"] for x in s2b["solutions"] if x["is_new"]]
    assert new_chars == ["점장"] and new_prods == ["Galaxy Tab Active5"] and new_sols == ["MagicINFO · 즉시 변경"]
    # 「바뀐 곳 1」은 SC4E(장면 하나 GET)에서 직전 버전과 비교한다
    one = await scene(client, s2["id"])
    assert one["changed_sentences"] == ["점장은 Galaxy Tab Active5로 재고를 확인하고, 품절 메뉴를 메뉴보드에서 바로 내린다."]
    # AC44 stale: 새로 생긴 제품(갤럭시 탭 → 태블릿)
    assert s2b["image_stale"] == {"missing": ["태블릿"]}
    r = await client.get(f"/v1/scenes/{s2['id']}/image-prefill")
    pf = r.json()
    assert pf["product_line"] == "KM24C · QM55C · Tab Active5" and pf["aspect_label"] == "16:9 · 제안서 시트용"
    # 스냅숏에 인물이 있으면 새 인물도 빠진 요소다(§4.11 「태블릿 · 점장」)
    from winmate_scenario import service
    doc = await repo.get_sc(sc["id"])
    raw = next(x for x in doc["scenes"] if x["id"] == s2["id"])
    raw["image"]["snapshot"] = {"products": ["KM24C", "QM55C"], "characters": ["손님"]}
    assert service.stale_of(doc, raw) == {"missing": ["태블릿", "점장"]}


async def test_ac45_restore_creates_new_version(client: Any, world: Any) -> None:
    sc = await board(client)
    s2 = by_no(await scenes(client, sc["id"]), 2)
    await client.post(f"/v1/scenarios/{sc['id']}:edit", json={"text": "장면 2에 점장이 태블릿으로 재고 확인하는 장면 추가"})
    await drain()
    v2 = await scene(client, s2["id"])
    r = await client.post(f"/v1/scenes/{s2['id']}/versions/1/restore")
    assert r.status_code == 200, r.text
    v3 = r.json()
    assert v3["version"] == 3 and v3["story"] == s2["story"] and v3["story"] != v2["story"]
    vs = (await client.get(f"/v1/scenes/{s2['id']}/versions")).json()["items"]
    assert [v["n"] for v in vs] == [1, 2, 3]


async def test_ac46_locked_scene_skipped_on_regenerate(client: Any, world: Any) -> None:
    sc = await board(client)
    s2 = by_no(await scenes(client, sc["id"]), 2)
    r = await client.patch(f"/v1/scenes/{s2['id']}", json={"title": "점심 피크 — 직접 고친 제목", "if_version": s2["version"]})
    assert r.status_code == 200, r.text
    assert r.json()["locked"] is True and r.json()["version"] == 2
    lst = (await client.get(f"/v1/scenarios/{sc['id']}/scenes")).json()
    assert lst["locked_nos"] == [2]
    # 겹침 확인(if_version)
    r = await client.patch(f"/v1/scenes/{s2['id']}", json={"title": "x", "if_version": 1})
    assert r.status_code == 409
    n_before = sum(1 for p in world.ai.prompts("sc.write_scene") if "장면 라벨: 점심 피크" in p)
    r = await client.post(f"/v1/scenarios/{sc['id']}/generate", json={"scope": "unlocked"})
    assert r.status_code == 202
    await drain()
    n_after = sum(1 for p in world.ai.prompts("sc.write_scene") if "장면 라벨: 점심 피크" in p)
    assert n_after == n_before
    assert (await scene(client, s2["id"]))["title"] == "점심 피크 — 직접 고친 제목"


async def test_ac47_pov_rewrite_only_this_scene(client: Any, world: Any) -> None:
    sc = await board(client)
    items = await scenes(client, sc["id"])
    s2 = by_no(items, 2)
    jang = next(r for r in (await client.get(f"/v1/scenarios/{sc['id']}/timeline")).json()["roles"] if r["name"] == "점장")
    r = await client.post(f"/v1/scenes/{s2['id']}:rewrite", json={"preset": "pov", "pov_role_id": jang["id"]})
    assert r.status_code == 202
    await drain()
    last = world.ai.prompts("sc.rewrite_scene")[-1]
    assert "수정 지시: 점장 시점으로" in last
    after = await scenes(client, sc["id"])
    assert by_no(after, 2)["title"] == "점심 피크 — 점장이 키오스크 덕분에 주문 줄을 덜어 낸다"
    assert by_no(after, 2)["version"] == 2
    for n in (1, 3, 4):
        assert by_no(after, n)["story"] == by_no(items, n)["story"]


async def test_ac48_delete_renumbers_and_replans(client: Any, world: Any) -> None:
    sc = await board(client)
    items = await scenes(client, sc["id"])
    s3, s4 = by_no(items, 3), by_no(items, 4)
    r = await client.delete(f"/v1/scenes/{s3['id']}")
    assert r.status_code == 204
    after = await scenes(client, sc["id"])
    assert len(after) == 3 and by_no(after, 3)["id"] == s4["id"]
    plan = (await client.get(f"/v1/scenarios/{sc['id']}/sheet-plan")).json()
    assert [s["code"] for s in plan["sheets"]] == ["SS-A"]  # 본사 운영실 장면이 사라져 공간 1 → 맵 시트 없음
    assert plan["sheets"][0]["scene_nos"] == [1, 2, 3]


async def test_add_scene_and_pick_kb_image(client: Any, world: Any) -> None:
    sc = await board(client)
    s1 = by_no(await scenes(client, sc["id"]), 1)
    r = await client.post(f"/v1/scenarios/{sc['id']}/scenes", json={"after_scene_id": s1["id"]})
    assert r.status_code == 201, r.text
    new = r.json()
    assert new["no"] == 2 and new["status"] in ("waiting", "done")
    r = await client.post(f"/v1/scenes/{s1['id']}/image:attach", json={"image_ref": "kb:image:img_abc", "source": "picked"})
    assert r.status_code == 200, r.text
    img = r.json()["image"]
    assert img["thumb_url"] == "/api/kb/v1/images/img_abc/thumb" and "사내 자산" in img["label"]
    r = await client.post(f"/v1/scenes/{s1['id']}/image:attach", json={"source": "picked"})
    assert r.status_code == 400
