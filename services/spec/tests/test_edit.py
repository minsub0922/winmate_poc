"""§9.10 편집(SP3E) · §9.11 내보내기 · 제안서(SP4) — 79번 편집 세션 → 85~93."""
from __future__ import annotations

from typing import Any

from sp_helpers import QM55C, QB55C
from winmate_common.jobs import jobs

MEMO = "창가 매장은 오후 직사광이 들어 QM55C 권장 — 고객 미팅에서 언급"


async def sheet_79(ctx, client) -> tuple[str, dict[str, Any]]:
    """50번 시트에서 1번은 미루고 2번은 카탈로그 3년으로 답한 결과."""
    ctx.use_cat_fix(version="2026-09")
    r = await client.post("/v1/sheets", json={"start": "model", "products": [QM55C, QB55C], "customer_name": "A 커피 프랜차이즈",
                                              "target_proposal": {"id": "prp_A", "title": "A 커피 프랜차이즈 메뉴보드 제안", "type": "standard",
                                                                  "section_no": "08", "subtitle": "디지털 메뉴보드 제안"}})
    sid = r.json()["id"]
    await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid}/generate", json={})
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    c2 = s["checks"]["items"][1]
    r = await client.post(f"/v1/sheets/{sid}/checks:apply", json={"answers": [{"check_id": c2["id"], "option_key": "catalog"}]})
    return sid, r.json()["sheet"]


def row_id(s: dict[str, Any], label: str) -> str:
    return next(r["id"] for r in (s.get("table") or s)["rows"] if r["label"] == label)


async def edit_79(client, sid: str, s: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    r = await client.post(f"/v1/sheets/{sid}/edit-sessions")
    assert r.status_code == 201, r.text
    ses = r.json()["id"]
    assert r.json()["view"]["summary_text"] == "시트 편집 · 변경 없음"
    ops = [{"op": "move_row", "row_id": row_id(s, "운영 시간"), "to_index": 1},
           {"op": "highlight_row", "row_id": row_id(s, "운영 시간")},
           {"op": "set_memo", "row_id": row_id(s, "밝기 · 명암비"), "text": MEMO, "mode": "footnote"},
           {"op": "hide_row", "row_id": row_id(s, "내장 플레이어 · OS")},
           {"op": "add_rows", "row_keys": ["dimensions"]}]
    r = await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}/ops", json={"ops": ops})
    assert r.status_code == 200, r.text
    return ses, r.json()


async def test_edit_session_board(ctx, client):
    sid, s = await sheet_79(ctx, client)
    ses, v = await edit_79(client, sid, s)
    tags = {r["label"]: r["tags"] for r in v["rows"]}
    # 79: 태그 · 도크 · 보이는 행 · 빠진 항목 · 숨긴 행 수
    assert tags["운영 시간"] == ["강조", "↑ 1칸"]
    assert tags["내장 플레이어 · OS"] == ["숨김"]
    assert tags["크기 (W×H×D)"] == ["추가됨"]
    assert [r["label"] for r in v["rows"]][:3] == ["화면 크기 · 해상도", "운영 시간", "밝기 · 명암비"]
    assert v["summary_text"] == "시트 편집 · 변경 5건 — 이동 1 · 강조 1 · 메모 1 · 숨김 1 · 추가 1"
    assert (v["visible"], v["total"], v["hidden_count"]) == (7, 8, 1)
    assert [m["label"] for m in v["missing_items"]] == ["입출력 단자", "베젤", "인증", "액세서리"]
    dims = next(r for r in v["rows"] if r["label"] == "크기 (W×H×D)")
    assert dims["cells"][0]["text"] == "1,237.9×708.8×28.5 mm"
    # 80: 실행 취소 두 번 → 다시 실행 한 번 → 5 → 4 → 3 → 4, 모두 되돌리기 → 변경 없음
    totals = []
    for act in ("undo", "undo", "redo"):
        v = (await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}:{act}")).json()
        totals.append(v["summary"]["total"])
    assert totals == [4, 3, 4]
    v = (await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}:reset")).json()
    assert v["summary_text"] == "시트 편집 · 변경 없음" and v["can_undo"] is False
    # 81: 말로 고치기 → 조작 2개가 세션에 · 시트 버전 그대로
    ver = s["version"]
    r = await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}/messages", json={"text": "소비전력 행을 맨 아래로, 보증도 강조"})
    assert r.status_code == 202
    await ctx.run_jobs()
    v = (await client.get(f"/v1/sheets/{sid}/edit-sessions/{ses}")).json()
    assert v["summary"]["total"] == 2 and v["summary"]["move"] == 1 and v["summary"]["highlight"] == 1
    assert v["rows"][-1]["label"] == "소비전력 (일반 · 최대)"
    assert (await client.get(f"/v1/sheets/{sid}")).json()["version"] == ver
    # 82: 취소 → 시트 그대로
    r = await client.delete(f"/v1/sheets/{sid}/edit-sessions/{ses}")
    assert r.status_code == 204
    s2 = (await client.get(f"/v1/sheets/{sid}")).json()
    assert [r["label"] for r in s2["table"]["rows"]] == [r["label"] for r in s["table"]["rows"]]


async def test_commit_and_conflict(ctx, client):
    sid, s = await sheet_79(ctx, client)
    ses, _ = await edit_79(client, sid, s)
    # 83: 세션 중 다른 곳에서 version 이 오름 → 409 → rebase 로 반영
    await client.post(f"/v1/sheets/{sid}:save")
    r = await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}:commit", json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_CONFLICT"
    cur = (await client.get(f"/v1/sheets/{sid}")).json()["version"]
    assert r.json()["error"]["details"]["current_version"] == cur
    r = await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}:commit", json={"rebase": True})
    assert r.status_code == 200, r.text
    s = r.json()
    # 82: version +1 · 순서 · 숨김 · 강조 · 각주
    assert s["version"] == cur + 1
    rows = s["table"]["rows"]
    assert [r["label"] for r in rows] == ["화면 크기 · 해상도", "운영 시간", "밝기 · 명암비", "소비전력 (일반 · 최대)", "내장 플레이어 · OS",
                                          "MagicINFO 호환", "보증", "크기 (W×H×D)"]
    assert rows[1]["highlighted"] and rows[4]["hidden"] and rows[2]["footnote_mark"] == "*"
    assert s["table"]["footnotes"][0]["text"] == f"밝기 · 명암비 — {MEMO}"
    assert s["table"]["visible_rows"] == 7
    assert next(i for i in s["items"] if i["key"] == "size_weight")["checked"] is True


async def test_export_and_handoff_package(ctx, client):
    sid, s = await sheet_79(ctx, client)
    ses, _ = await edit_79(client, sid, s)
    s = (await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}:commit", json={})).json()
    # 85: 파일명 기본값
    assert s["agent"]["filename_default"] == "A커피_QM55C-QB55C_스펙비교"
    # 86: Excel 다운로드 — 보이는 7행(편집 순서) · 각주 · 숨긴 행 없음 · [확정 필요] 1칸
    r = await client.post(f"/v1/sheets/{sid}/exports", json={"format": "xlsx", "options": {"drop_hidden": True, "memo_footnotes": True,
                                                                                           "keep_pending_marks": True}})
    eid = r.json()["export_id"]
    await ctx.run_jobs()
    from winmate_spec import repo
    rec = await repo.aget("exports", eid)
    assert rec["status"] == "done", rec.get("error")
    assert rec["filename"] == "A커피_QM55C-QB55C_스펙비교.xlsx"
    summ = rec["summary"]
    assert summ["visible_rows"] == 7 and summ["pending_cells"] == 1
    # 87 · 89: 넘김 묶음
    r = await client.post(f"/v1/sheets/{sid}/handoffs", json={"proposal_id": "prp_A", "proposal_type": "standard", "templates": ["SC-A"],
                                                               "mode": "replace"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["open_route"] == f"/proposal/prp_A/sections/spec?handoff={body['id']}"
    h = (await client.get(f"/v1/handoffs/{body['id']}")).json()
    pkg = h["package"]
    sc = pkg["sheets"][0]
    assert sc["template"] == "SC-A" and sc["data"]["title"] == "QM55C vs QB55C 사양 비교"
    assert len(sc["data"]["rows"]) == 7
    assert sc["data"]["rows"][2]["label"] == "밝기 · 명암비 *"
    assert sc["data"]["footnotes"][0]["text"].startswith("밝기 · 명암비 — 창가 매장은")
    assert pkg["carry"] == {"visible_rows": 7, "hidden_rows_dropped": 1, "win_cells": 2, "footnote_memos": 1, "pending_cells": 1}
    assert len(pkg["fact_check"]) == 1 and pkg["fact_check"][0]["text"].startswith("QB55C 소비전력")
    assert pkg["lines"] == ["보이는 행 7개 — 숨긴 1행은 빠져요", "우위 강조 2칸 · 각주 메모 1건 그대로", "[확정 필요] 1칸 → 제안서 '사실 확인 필요'로",
                            "시트와 연결 유지 — 값이 바뀌면 제안서에 알림"]
    # 84: 내부 메모는 어디에도 없다
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    ses2 = (await client.post(f"/v1/sheets/{sid}/edit-sessions")).json()["id"]
    await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses2}/ops", json={"ops": [
        {"op": "set_memo", "row_id": row_id(s, "보증"), "text": "내부 전용 메모 — 단가 협상 중", "mode": "internal"}]})
    await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses2}:commit", json={})
    pkg = (await client.get(f"/v1/sheets/{sid}/package", params={"templates": "SC-A,SD-A"})).json()
    import json as _json
    assert "단가 협상" not in _json.dumps(pkg, ensure_ascii=False)
    # 90: :ack → 연결 · in_sync · SP0 연결된 제안서
    r = await client.post(f"/v1/handoffs/{body['id']}:ack", json={"result": "applied", "proposal_id": "prp_A",
                                                                  "proposal_title": "A 커피 프랜차이즈 메뉴보드 제안", "section_no": "08",
                                                                  "section_name": "제품 스펙", "proposal_sheet_ids": ["psh_1"]})
    assert r.json()["status"] == "acked"
    links = (await client.get("/v1/links", params={"proposal_id": "prp_A"})).json()["items"]
    assert len(links) == 1
    lst = (await client.get("/v1/sheets", params={"q": "QM55C"})).json()["items"]
    assert next(i for i in lst if i["id"] == sid)["proposal_label"] == "A 커피 프랜차이즈 메뉴보드 제안"


async def test_link_changed_after_edit(ctx, client):
    sid, s = await sheet_79(ctx, client)
    r = await client.post(f"/v1/sheets/{sid}/handoffs", json={"proposal_id": "prp_B", "proposal_type": "standard", "templates": ["SC-A"]})
    sho = r.json()["id"]
    await client.post(f"/v1/handoffs/{sho}:ack", json={"result": "applied", "proposal_id": "prp_B", "proposal_title": "B 제안",
                                                       "section_no": "08", "section_name": "제품 스펙"})
    assert (await client.get("/v1/links", params={"proposal_id": "prp_B"})).json()["items"][0]["status"] == "in_sync"
    # 95: 값이 바뀌어 version 이 오름 → sheet_changed + diff_cells + route, 알림
    row = next(r for r in s["table"]["rows"] if r["label"] == "보증")
    qm = next(p["id"] for p in s["products"] if p["display_name"] == "QM55C")
    await client.patch(f"/v1/sheets/{sid}/cells/{row['id']}/{qm}", json={"value_text": "2년"})
    await client.post(f"/v1/sheets/{sid}:save")
    lk = (await client.get("/v1/links", params={"proposal_id": "prp_B"})).json()["items"][0]
    assert lk["status"] == "sheet_changed"
    assert lk["diff_cells"] == [{"row_label": "보증", "product_label": "QM55C", "sent_text": "3년", "current_text": "2년"}]
    assert lk["route"].startswith(f"/spec/{sid}/warnings?w=swn_")
    from winmate_spec import repo
    owner = (await repo.aget("sheets", sid))["owner_id"]
    notes = [d for _, d in await jobs().notifications(owner)]
    hit = [n for n in notes if n.get("type") == "spec_link_changed"]
    assert hit, notes
    assert hit[0]["route"] == "/proposal/prp_B/sections/spec" and hit[0]["proposal_id"] == "prp_B" and hit[0]["ref"] == sid
    assert hit[0]["title"] == "'B 제안' 제안서의 제품 스펙이 시트와 달라졌어요"


async def test_sca_split_and_solution(ctx, client):
    # 91: 제품 6개 → SC-A 3열 · 3열 두 장 (1/2) · (2/2)
    models = ["LH43QMCEBGCXKR", "LH50QMCEBGCXKR", QM55C, "LH65QMCEBGCXKR", QB55C, "LH55QHCEBGCXKR"]
    r = await client.post("/v1/sheets", json={"start": "model", "products": models})
    sid = r.json()["id"]
    assert len(r.json()["products"]) == 6
    await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid}/generate", json={"auto_answer": True})
    await ctx.run_jobs()
    pkg = (await client.get(f"/v1/sheets/{sid}/package", params={"templates": "SC-A"})).json()
    assert [len(x["data"]["columns"]) for x in pkg["sheets"]] == [3, 3]
    assert pkg["sheets"][0]["data"]["title"].endswith(" (1/2)") and pkg["sheets"][1]["data"]["title"].endswith(" (2/2)")
    # 92: 새 제안서로 시작 · Solution형 422
    r = await client.post(f"/v1/sheets/{sid}/handoffs", json={"proposal_id": None, "templates": ["SC-A"]})
    assert r.json()["open_route"].startswith("/proposal/new?handoff=sho_")
    r = await client.post(f"/v1/sheets/{sid}/handoffs", json={"proposal_id": "prp_S", "proposal_type": "solution", "templates": ["SC-A"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_SPEC_SECTION"
    assert r.json()["error"]["message"] == "Solution형 제안서에는 '제품 스펙' 섹션이 없어요."
    # 93: 링크로 공유
    r = await client.post(f"/v1/sheets/{sid}/share")
    assert r.status_code == 200 and r.json()["share_url"].startswith("/share/")
    # P1: ProposalHandoff v1
    ph = (await client.get(f"/v1/sheets/{sid}/proposal-handoff", params={"type": "standard", "section": "spec"})).json()
    assert ph["source"]["feature"] == "SP" and ph["live_link"] is True and ph["items"][0]["template_hint"]["code"] == "SC-A"
