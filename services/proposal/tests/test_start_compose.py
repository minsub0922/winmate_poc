"""PR0 · PR1 · PR2 · PR3 · PR3I — 만들기 · 고객 정보 · 유형 · 시트 구성 · 업종 레이아웃."""
from __future__ import annotations

from typing import Any


async def make(client: Any, **body: Any) -> dict[str, Any]:
    r = await client.post("/v1/proposals", json={"start_mode": "blank", **body})
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_blank_and_patch(client: Any) -> None:
    p = await make(client)
    assert p["title_display"] == "새 제안서"
    assert p["language"] == "ko"
    assert p["stage"] == "customer" and p["stepper"]["current"] == 1 and p["stepper"]["one_click"] is True
    assert p["route"] == f"/proposal/{p['id']}/customer"
    r = await client.patch(f"/v1/proposals/{p['id']}", json={"title": "전국 매장 디지털 메뉴보드 전환",
                                                             "customer": {"name": "A 커피 프랜차이즈", "scale_text": "320개 매장"},
                                                             "schedule": {"submit_due": "2026-10-08"}})
    assert r.status_code == 200, r.text
    p2 = r.json()
    assert p2["customer"]["name"] == "A 커피 프랜차이즈"
    assert p2["rev"] > p["rev"]
    # 오래된 If-Match → 409
    r = await client.patch(f"/v1/proposals/{p['id']}", json={"title": "x"}, headers={"If-Match": str(p["rev"])})
    assert r.status_code == 409 and r.json()["error"]["code"] == "REV_CONFLICT"
    # 새로고침해도 유지(AC-020)
    r = await client.get(f"/v1/proposals/{p['id']}")
    assert r.json()["title"] == "전국 매장 디지털 메뉴보드 전환"
    # 업종: 커피 단서로 외식 · 카페 감지
    assert r.json()["industry_layout"]["detected"]["code"] == "FB"


async def test_type_composition_industry(client: Any) -> None:
    p = await make(client, title="전국 매장 디지털 메뉴보드 전환", customer={"name": "A 커피 프랜차이즈", "scale_text": "320개 매장"},
                   rq_ref={"rq_id": "rq_acoffee", "version": 1})
    pid = p["id"]
    r = await client.get(f"/v1/proposals/{pid}/type-options")
    assert r.status_code == 200, r.text
    to = r.json()
    assert to["recommended"]["type"] == "standard"
    assert "표준 제안서를 추천합니다." in to["intro"]
    r = await client.put(f"/v1/proposals/{pid}/type", json={"type": "quickwin"})
    assert r.status_code == 200, r.text
    r = await client.get(f"/v1/proposals/{pid}/composition")
    comp = r.json()
    assert [s["key"] for s in comp["sections"]] == ["vp", "spaceProducts", "solution", "cases", "spec"]
    assert comp["open_key"] == "spaceProducts"
    assert [s["key"] for s in comp["sections"] if s["optional"]] == ["solution"]
    r = await client.put(f"/v1/proposals/{pid}/type", json={"type": "standard"})
    comp = (await client.get(f"/v1/proposals/{pid}/composition")).json()
    assert comp["section_count"] == 8
    assert comp["header_label"].startswith("시트 구성 · 표준 제안서 · 섹션 8 · 시트 ")
    r = await client.post(f"/v1/proposals/{pid}/composition:start")
    assert r.status_code == 200, r.text
    assert r.json()["next"]["target"] == "industry"
    iv = (await client.get(f"/v1/proposals/{pid}/industry")).json()
    assert iv["detected"]["code"] == "FB"
    assert iv["detected"]["mode_label"] in ("자동 감지", "확인 권장")
    assert len(iv["options"]) == 16
    r = await client.put(f"/v1/proposals/{pid}/industry", json={"decided": True})
    assert r.status_code == 200, r.text
    view = r.json()
    assert view["next"]["target"] == "sections"
    sheets = (await client.get(f"/v1/proposals/{pid}")).json()["sheets"]
    ms = next(s for s in sheets if s["role"] == "MS")
    assert ms["template_code"] == "MI-FB-A", ms
    cp = next(s for s in sheets if s["role"] == "CP")
    assert cp["template_code"] == "CP-A"
