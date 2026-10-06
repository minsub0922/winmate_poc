from __future__ import annotations

from sc_flow import board, by_no, get, scenes


async def test_board_flow_end_to_end(client, world):
    sc = await board(client)
    assert sc["status"] == "done", sc
    assert sc["version"] == 1
    items = await scenes(client, sc["id"])
    assert len(items) == 4
    s1 = by_no(items, 1)
    assert s1["title"].startswith("오픈 — ")
    assert "MagicINFO · 전원 스케줄" in s1["solution_chips"]
    assert any(p["short"] == "QM55C" for p in s1["products"])
    s3 = by_no(items, 3)
    assert "320개" in s3["story"] and "[00]분" in s3["story"]
    r = await client.get(f"/v1/scenarios/{sc['id']}/sheet-plan")
    assert r.status_code == 200, r.text
    plan = r.json()
    assert [s["code"] for s in plan["sheets"]] == ["VM-A", "SS-A", "SS-B"], plan
    sc2 = await get(client, sc["id"])
    assert sc2["route"].endswith("/result")
