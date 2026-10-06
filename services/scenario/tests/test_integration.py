"""in-process 통합 — 실제 birdseye 앱(계약 엄격 검증) · Storyboard 계약 모양(SB4 → `?sb=`) · 실제 image 앱(test_scenes)."""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from sc_flow import get, parse, pick
from sc_world import SB_ID, World
from winmate_common import testing


@pytest.fixture
def be_world(env: None) -> Iterator[World]:
    w = World(real_birdseye=True)
    with testing.inprocess(w.apps):
        yield w


@pytest.fixture
async def be_client(be_world: World) -> AsyncIterator[Any]:
    from winmate_scenario.main import app
    async with testing.api_client(app) as c:
        yield c


async def test_real_birdseye_aerial_draft_options_and_import(be_client: Any, be_world: World) -> None:
    client = be_client
    r = await client.post("/v1/scenarios", json={"type": "with", "aerial": {"enabled": True, "source": "new"}})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    await parse(client, sid)
    await pick(client, sid, ["magicinfo"])
    r = await client.post(f"/v1/scenarios/{sid}:route-generate")
    assert r.status_code == 200, r.text
    bid = r.json()["aerial_birdseye_id"]
    assert bid, "실제 birdseye 가 조감도 초안을 만들었다"
    creates = [b for p, b in be_world.birdseye.requests if p == "/v1/birdseyes" and b]
    assert len(creates) == 1 and creates[0]["origin"] == {"service": "scenario", "ref": sid, "label": "공간 시나리오",
                                                           "return_to": f"/scenario/{sid}/result"}
    async with testing.api_client(be_world.apps["birdseye"]) as bec:
        r = await bec.get(f"/v1/birdseyes/{bid}")
        assert r.status_code == 200, r.text
        assert r.json()["title"].endswith("조감도")
    assert (await get(client, sid))["aerial"]["birdseye_id"] == bid
    # SC1 「기존 조감도 연결」 목록에 나온다(계약대로 읽힌다)
    r = await client.get("/v1/birdseye-options")
    opts = r.json()
    assert opts["available"] is True and any(o["id"] == bid for o in opts["items"])
    # 존이 아직 없는 조감도 미리보기 · 끌어오기 — 멈추지 않고 빈 값
    r = await client.get(f"/v1/birdseye-options/{bid}")
    assert r.status_code == 200, r.text
    assert r.json()["zones"] == []
    r = await client.post(f"/v1/scenarios/{sid}/imports", json={"feature": "BE", "ref": f"birdseye:{bid}"})
    assert r.status_code == 200, r.text
    assert r.json()["birdseye_link"]["birdseye_id"] == bid
    # 존 없는 조감도로는 시나리오를 시작할 수 없다
    r = await client.post("/v1/scenarios:from-birdseye", json={"birdseye_id": bid, "zone_ids": [], "order": [], "axis": "방문객 동선",
                                                               "keep_link": True, "type": "with"})
    assert r.status_code in (400, 422)


async def test_storyboard_prefill_and_drop(client: Any, world: Any) -> None:
    r = await client.post("/v1/scenarios", json={"type": "with", "storyboard_id": SB_ID})
    assert r.status_code == 201, r.text
    sc = r.json()
    assert sc["customer_name"] == "A 커피" and sc["space_label"] == "매장 카운터"
    assert sc["raw_text"] == "[공간] 매장 카운터 — 주문 · 픽업 대기 줄이기\n[공간] 본사 운영실 — 전국 매장 콘텐츠 배포"
    # SC2 사이드바에서 Storyboard 를 끌어오면 고객 · 공간 줄을 붙인다
    r = await client.post("/v1/scenarios", json={"type": "with"})
    sid = r.json()["id"]
    r = await client.post(f"/v1/scenarios/{sid}/imports", json={"feature": "SB", "ref": f"storyboard:{SB_ID}"})
    assert r.status_code == 200, r.text
    assert r.json()["append_text"].splitlines() == ["[고객] A 커피", "[공간] 매장 카운터 — 주문 · 픽업 대기 줄이기",
                                                    "[공간] 본사 운영실 — 전국 매장 콘텐츠 배포"]
    assert (await get(client, sid))["customer_name"] == "A 커피"
    # 없는 Storyboard 는 조용히 빈 값(화면이 멈추지 않는다)
    r = await client.post("/v1/scenarios", json={"type": "with", "storyboard_id": "sb_missing"})
    assert r.status_code == 201 and r.json()["raw_text"] == ""
    # MI4 · VP4 에서 넘어온 고객사(프로젝트 · Storyboard 고객이 없을 때) — 통합
    r = await client.post("/v1/scenarios", json={"type": "with", "customer_name": " E 자산운용 "})
    assert r.status_code == 201 and r.json()["customer_name"] == "E 자산운용"
    r = await client.post("/v1/scenarios", json={"type": "with", "storyboard_id": SB_ID, "customer_name": "다른 고객"})
    assert r.json()["customer_name"] == "A 커피"
