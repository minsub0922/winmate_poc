"""PR7C 검토(workspace 파사드) · PR7V 버전 · PR7X 내보내기(AC-160~173)."""
from __future__ import annotations

from typing import Any

from winmate_common import testing


async def generated(client: Any, ctx: Any) -> str:
    r = await client.post("/v1/proposals", json={"start_mode": "blank", "title": "전국 매장 디지털 메뉴보드 전환",
                                                  "customer": {"name": "A 커피 프랜차이즈", "scale_text": "320개 매장"},
                                                  "rq_ref": {"rq_id": "rq_acoffee", "version": 1},
                                                  "links": [{"feature": "mi", "ref_id": "mi_acoffee"}, {"feature": "competitor", "ref_id": "ca_acoffee"}]})
    pid = r.json()["id"]
    await client.put(f"/v1/proposals/{pid}/type", json={"type": "quickwin"})
    await client.put(f"/v1/proposals/{pid}/industry", json={"keep_default": True})
    await client.post(f"/v1/proposals/{pid}/sections/vp:fill", json={})
    await ctx.run_jobs()
    r = await client.post(f"/v1/proposals/{pid}:generate", json={"scope": "all", "infer_empty": True})
    assert r.status_code == 202
    await ctx.run_jobs()
    assert (await client.get(f"/v1/proposals/{pid}")).json()["version"] == 1
    return pid


async def test_versions_compare_restore_revert(client: Any, ctx: Any) -> None:
    pid = await generated(client, ctx)
    p = (await client.get(f"/v1/proposals/{pid}")).json()
    sid = p["sheets"][0]["id"]
    sh = (await client.get(f"/v1/proposals/{pid}/sheets/{sid}")).json()
    old_title = sh["content"]["title"]
    r = await client.patch(f"/v1/proposals/{pid}/sheets/{sid}", json={"ops": [{"op": "set", "path": "/title", "value": "새 제목입니다"}]})
    assert r.status_code == 200, r.text
    assert r.json()["edits_since_version"] == 1
    sl = (await client.get(f"/v1/proposals/{pid}/slides")).json()
    assert sl["version_label"] == "v1 · 수정 1"                                      # AC-140
    assert any(s["edited"] for sec in sl["sections"] for s in sec["sheets"])
    vv = (await client.get(f"/v1/proposals/{pid}/versions")).json()
    assert vv["next_save_label"] == "지금 상태를 v2로 저장"
    assert vv["versions"][0]["author_label"] == "W" and vv["versions"][0]["desc"].endswith("시트 처음 생성")
    assert vv["pending_changes"]
    r = await client.post(f"/v1/proposals/{pid}/versions", json={"desc": "제목 다듬기"})
    assert r.status_code == 201 and r.json()["n"] == 2
    cv = (await client.get(f"/v1/proposals/{pid}/versions/compare", params={"a": 1, "b": 2})).json()
    assert cv["header_label"].startswith("바뀐 시트 1 · 바뀐 곳 ")
    d = cv["diffs"][0]
    assert d["where"] == "제목" and d["to"] == "새 제목입니다"
    assert cv["a"]["sheet_id"] == sid and cv["a"]["display"]["title"] == old_title and cv["b"]["display"]["title"] == "새 제목입니다"
    # 바뀐 곳 되돌리기(AC-167)
    r = await client.post(f"/v1/proposals/{pid}/changes/{d['change_id']}:revert")
    assert r.status_code == 200, r.text
    assert (await client.get(f"/v1/proposals/{pid}/sheets/{sid}")).json()["content"]["title"] == old_title
    # v1 전체로 되돌리기 → v3(kind restore)(AC-168)
    r = await client.post(f"/v1/proposals/{pid}/versions/1/restore", json={"scope": "all"})
    assert r.status_code == 200 and r.json()["new_version"] == 3
    vv = (await client.get(f"/v1/proposals/{pid}/versions")).json()
    assert [v["n"] for v in vv["versions"]] == [3, 2, 1] and vv["versions"][0]["desc"] == "v1 전체로 되돌림"
    # 이 시트만 v2로(새 버전 없음)
    r = await client.post(f"/v1/proposals/{pid}/versions/2/restore", json={"scope": "sheet", "sheet_id": sid})
    assert r.status_code == 200 and r.json()["new_version"] is None
    assert (await client.get(f"/v1/proposals/{pid}/sheets/{sid}")).json()["content"]["title"] == "새 제목입니다"


async def test_review_facade(client: Any, ctx: Any) -> None:
    pid = await generated(client, ctx)
    # 검토자 계정
    from winmate_proposal.main import app
    sid = (await client.get(f"/v1/proposals/{pid}")).json()["sheets"][0]["id"]
    await client.patch(f"/v1/proposals/{pid}/sheets/{sid}", json={"ops": [{"op": "set", "path": "/title", "value": "수정 1"}]})
    r = await client.post(f"/v1/proposals/{pid}/review-requests", json={"reviewer_ids": ["u_park", "u_kim"], "due_date": "2026-10-08",
                                                                        "message": "1차 제출본입니다."})
    assert r.status_code == 201, r.text
    rv = r.json()
    assert rv["review"]["version"] == 2                                              # 수정이 있으면 먼저 v2(AC-160)
    assert rv["approvals"]["label"] == "승인 0 / 2"
    assert rv["review"]["sent_label"].endswith("마감 10월 8일 (목)") or "마감 10월 8일" in rv["review"]["sent_label"]
    p = (await client.get(f"/v1/proposals/{pid}")).json()
    assert p["status"] == "review" and p["progress_label"] == "PPTX v2 · 승인 대기"
    # 검토자 결정 — 검토자 본인으로
    async with testing.api_client(app, user_id="u_park", user_name="박준호") as park:
        r = await park.get(f"/v1/proposals/{pid}/review")
        assert r.json()["my_turn"] is True
        r = await park.post(f"/v1/proposals/{pid}/review/decision", json={"decision": "approve"})
        assert r.status_code == 200, r.text
        assert r.json()["approvals"]["label"] == "승인 1 / 2"
        r = await park.put(f"/v1/proposals/{pid}/review/checks/{sid}", json={"state": "ok"})
        assert r.status_code == 200
    p = (await client.get(f"/v1/proposals/{pid}")).json()
    assert p["progress_label"] == "PPTX v2 · 검토 요청 1/2 승인"
    # 코멘트(웹이 workspace 에 직접) → 수정안 → 적용
    from winmate_common.client import ServiceClient
    c = await ServiceClient("workspace").post("/v1/comments", json={
        "target": f"proposal:{pid}:sheet:{sid}", "body": "제목을 결론부터 써 주세요.", "anchor": {"sheet_id": sid, "point": {"x": 0.2, "y": 0.1}}})
    rv = (await client.get(f"/v1/proposals/{pid}/review")).json()
    assert rv["comments_open"] == 1 and rv["comment_sheets"][0]["sheet_id"] == sid
    r = await client.post(f"/v1/proposals/{pid}/comments/{c['id']}:suggest")
    assert r.status_code == 202
    await ctx.run_jobs()
    sg = (await client.get(f"/v1/proposals/{pid}/comments/{c['id']}/suggestion")).json()
    assert sg["status"] == "done" and sg["patch"], sg
    # 수정안 만들기 → 새 버전(kind comments_applied)(AC-164)
    r = await client.post(f"/v1/proposals/{pid}/review:apply-comments", json={})
    assert r.status_code == 202
    await ctx.run_jobs()
    vv = (await client.get(f"/v1/proposals/{pid}/versions")).json()
    assert vv["versions"][0]["kind"] == "comments_applied" and vv["versions"][0]["desc"] == "검토 코멘트 반영"
    # 확정 필요로 보내기(AC-163)
    r = await client.post(f"/v1/proposals/{pid}/confirm-items", json={"sheet_id": sid, "text": "출처 확인", "from_comment_id": c["id"]})
    assert r.status_code == 201 and r.json()["tag"] == "검토 코멘트"
    r = await client.post(f"/v1/proposals/{pid}/share-link", json={"permission": "team_comment"})
    assert r.status_code == 200 and r.json()["permission_label"] == "팀 내부 · 코멘트 가능"


async def test_export_options_and_run(client: Any, ctx: Any) -> None:
    pid = await generated(client, ctx)
    eo = (await client.get(f"/v1/proposals/{pid}/export-options", params={"lang": "ko_en"})).json()
    assert eo["preview_files"] == [f"A커피_디지털메뉴보드_제안서_v1_KO.pptx", "A커피_디지털메뉴보드_제안서_v1_KO.pdf",
                                   "A커피_디지털메뉴보드_제안서_v1_EN.pptx", "A커피_디지털메뉴보드_제안서_v1_EN.pdf"]
    r = await client.post(f"/v1/proposals/{pid}/exports", json={"formats": ["pptx"], "lang": "ko",
                                                               "scope": {"kind": "sheets", "range": "07–01"}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_SHEET_RANGE"      # AC-172
    r = await client.post(f"/v1/proposals/{pid}/exports", json={"formats": ["pptx", "pdf"], "lang": "ko_en", "tbd_mode": "move_to_notes",
                                                               "scope": {"kind": "sheets", "range": "01–02"},
                                                               "team_folder": {"enabled": True}})
    assert r.status_code == 202, r.text
    xid = r.json()["export_id"]
    await ctx.run_jobs()
    x = (await client.get(f"/v1/proposals/{pid}/exports/{xid}")).json()
    assert x["status"] == "done", x
    names = [f["name"] for f in x["files"]]
    assert any(n.endswith("_KO.pptx") for n in names) and any(n.endswith("_EN.pptx") for n in names), names
    assert x["team_folder_files"]
