"""§9.1 수용 기준 17–23 — 공간 질의 · 모름 → 고객 질문 · 다듬기 · 수정 요청 · 경합 · 저장 · 비교 · 되돌리기."""
from __future__ import annotations

from sb_flow import drain, section_key, space_named, to_outline
from sb_world import RQ


async def _questions(client, sb, name):
    sp = space_named(sb, name)
    r = await client.post(f"/v1/storyboards/{sb['id']}/spaces/{sp['id']}/questions")
    if r.status_code == 202:
        assert r.json()["ref"] == {"kind": "space", "id": sp["id"]}
        await drain()
        r = await client.post(f"/v1/storyboards/{sb['id']}/spaces/{sp['id']}/questions")
    assert r.status_code == 200, r.text
    return sp, r.json()["questions"]


async def test_space_questions_only_empty(client, world):
    sb = await to_outline(client)
    lobby, lq = await _questions(client, sb, "로비")
    assert lobby["filled_count"] == 0 and [q["slot"] for q in lq] == ["action", "trigger", "response", "exception", "metric"]
    meet, mq = await _questions(client, sb, "회의실")
    assert meet["filled_count"] == 3 and [q["slot"] for q in mq] == ["exception", "metric"]
    for q in lq + mq:
        assert 2 <= len(q["options"]) <= 4 and q["select"] == "multi_ordered" and q["allow_custom"]
    exc = next(q for q in lq if q["slot"] == "exception")
    assert exc["text"] == "로비에서 막히는 경우는 어떻게 할까요?"
    assert exc["info"] == "예외가 있어야 실제 운영 장면이 돼요. 고른 순서대로 들어가요."


async def test_unknown_slot_customer_question_idempotent(client, world):
    sb = await to_outline(client)
    lobby, _ = await _questions(client, sb, "로비")
    url = f"/v1/storyboards/{sb['id']}/spaces/{lobby['id']}/slots/exception"
    r = await client.put(url, json={"unknown": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["slots"]["exception"]["state"] == "unknown"
    assert "[확인 필요]" in "".join(s["text"] for s in body["slots"]["exception"]["segments"])
    assert body["customer_question_id"]
    posts = world.rq.calls_of("POST", "/customer-questions")
    assert len(posts) == 1
    origin = posts[0][2]["origin"]
    assert origin["kind"] == "storyboard" and origin["place_label"] == "Part 2 로비" and origin["ref_id"] == sb["id"]
    r2 = await client.put(url, json={"unknown": True})
    assert r2.json()["customer_question_id"] == body["customer_question_id"]
    assert len(world.rq.questions) == 1
    r3 = await client.put(url, json={})
    assert r3.status_code == 422


async def test_compose(client, world):
    sb = await to_outline(client)
    lobby, qs = await _questions(client, sb, "로비")
    for q in qs:
        r = await client.put(f"/v1/storyboards/{sb['id']}/spaces/{lobby['id']}/slots/{q['slot']}",
                             json={"selected_option_ids": [o["id"] for o in q["options"][:2]]})
        assert r.status_code == 200, r.text
    r = await client.post(f"/v1/storyboards/{sb['id']}/spaces/{lobby['id']}/compose")
    assert r.status_code == 202
    mid = (await client.get(f"/v1/storyboards/{sb['id']}/spaces/{lobby['id']}")).json()
    assert mid["composing"] is True
    await drain()
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    sp = space_named(sb2, "로비")
    assert sp["status"] == "supplemented" and sp["filled_count"] == 5 and sp["composing"] is False
    assert all(sp["slots"][k]["state"] == "filled" for k in sp["slots"])
    assert any(seg.get("ai_added") for k in sp["slots"] for seg in sp["slots"][k]["segments"])
    metric = "".join(s["text"] for s in sp["slots"]["metric"]["segments"])
    assert metric == "대기 시간 [00]분 · 안내 문의 [00]% 감소"
    assert [a["short_label"] for a in sp["added_questions"]] == ["출근 혼잡 시간대", "지금 로비 운영 데이터"]
    assert len(world.rq.calls_of("POST", "/customer-questions")) == 2
    names = [p["name"] for p in sp["products"]]
    assert names[:2] == ["QMC 사이니지", "안내 로봇"] and "AI CCTV" in names
    assert sum(1 for p in sp["products"] if p["is_extension"]) == 2
    chg = [c for c in sb2["changes"] if c["cause"]["kind"] == "space_questions"]
    assert chg and chg[0]["tags"] == ["author_supplemented"] and chg[0]["place_label"] == "Part 2 · 로비"
    assert chg[0]["before_summary"] == "배경 + 기술 후보"
    assert chg[0]["after_summary"] == "시나리오 5칸 — 행위 → 트리거 → 반응 → 예외 → 지표"
    assert sb2["sub_line"] == "라운지 시나리오가 비어 있어요"


async def test_revision_rows_apply_discard(client, world):
    sb = await to_outline(client)
    p12 = section_key(sb, "p1_2")
    r = await client.post(f"/v1/storyboards/{sb['id']}/revisions", json={
        "target": {"kind": "section", "id": p12["id"]}, "scope": "target", "instruction": "경영진용으로 짧게", "chips": ["비교표로"]})
    assert r.status_code == 202, r.text
    rev_id = r.json()["ref"]["id"]
    await drain()
    rev = (await client.get(f"/v1/storyboards/{sb['id']}/revisions/{rev_id}")).json()
    assert rev["status"] == "ready"
    kinds = [row["kind"] for row in rev["rows"]]
    assert kinds == ["changed", "changed", "changed", "added", "kept"]
    assert rev["changed_count"] == 4
    kept = rev["rows"][-1]
    assert kept["before"] == "성과 수치 [확인 필요]" and kept["after"] == "그대로 — 추정값을 넣지 않아요"
    assert rev["target"]["label"] == "Part 1-2 Tech Ready 모델의 성과"
    r = await client.post(f"/v1/storyboards/{sb['id']}/revisions/{rev_id}/apply")
    assert r.status_code == 200, r.text
    after = section_key(r.json(), "p1_2")
    assert after["lines"][0]["text"] == "운영 · 인증 · 자산가치 3가지 성과를 한 장 비교표로"
    assert any("[확인 필요]" in ln["text"] for ln in after["lines"])
    assert any(c["cause"]["kind"] == "revision" for c in r.json()["changes"])
    await drain()   # 추적 다시 계산
    # 버리기 — 작업본 그대로
    r = await client.post(f"/v1/storyboards/{sb['id']}/revisions", json={
        "target": {"kind": "section", "id": p12["id"]}, "scope": "target", "instruction": "", "chips": ["더 짧게"]})
    rev2 = r.json()["ref"]["id"]
    await drain()
    before = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    r = await client.post(f"/v1/storyboards/{sb['id']}/revisions/{rev2}/discard")
    assert r.status_code == 200 and r.json()["status"] == "discarded"
    after2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert section_key(after2, "p1_2")["lines"] == section_key(before, "p1_2")["lines"]
    r = await client.post(f"/v1/storyboards/{sb['id']}/revisions", json={"target": {"kind": "section", "id": p12["id"]},
                                                                         "instruction": "", "chips": []})
    assert r.status_code == 422


async def test_revision_stale(client, world):
    sb = await to_outline(client)
    p12 = section_key(sb, "p1_2")
    r = await client.post(f"/v1/storyboards/{sb['id']}/revisions", json={
        "target": {"kind": "section", "id": p12["id"]}, "scope": "target", "instruction": "짧게", "chips": []})
    rev_id = r.json()["ref"]["id"]
    await drain()
    # 그 사이 같은 섹션이 바뀐다(정의서 동기화를 흉내 — 다른 수정 요청 적용)
    from winmate_storyboard import service

    def bump(d):
        sec = next(s for s in d["outline"]["sections"] if s["id"] == p12["id"])
        sec["lines"][0]["text"] = "정의서 v3 반영 — 성수 성과 근거 바뀜"
        return d

    await service.mutate(sb["id"], bump)
    r = await client.post(f"/v1/storyboards/{sb['id']}/revisions/{rev_id}/apply")
    assert r.status_code == 409 and r.json()["error"]["code"] == "REVISION_STALE"


async def test_group_scope_revision(client, world):
    sb = await to_outline(client)
    intro = section_key(sb, "intro")
    r = await client.post(f"/v1/storyboards/{sb['id']}/revisions", json={
        "target": {"kind": "section", "id": intro["id"]}, "scope": "group", "instruction": "시작을 짧게", "chips": []})
    rev_id = r.json()["ref"]["id"]
    await drain()
    rev = (await client.get(f"/v1/storyboards/{sb['id']}/revisions/{rev_id}")).json()
    assert rev["scope_label"] == "시작 전체" and rev["status"] == "ready"


async def test_save_versions_compare_revert(client, world):
    sb = await to_outline(client)
    sid = sb["id"]
    r = await client.post(f"/v1/storyboards/{sid}/save", json={})
    assert r.status_code == 201 and r.json() == {"version": 1, "created": True}
    sb1 = (await client.get(f"/v1/storyboards/{sid}")).json()
    assert sb1["status"] == "done" and sb1["step"] == 5 and sb1["version"] == 1
    assert sb1["draft_label"] == "v1" and sb1["has_unsaved_changes"] is False
    assert sb1["route"] == f"/storyboard/{sid}/saved?v=1" and sb1["sub_line"] == "v1 저장"
    r = await client.post(f"/v1/storyboards/{sid}/save", json={})
    assert r.status_code == 200 and r.json() == {"version": 1, "created": False}
    # 변경 3개(유지 1 포함): 수정 요청 적용(바뀜) + 메시지 수정 + 동기화 유지 흉내
    p12 = section_key(sb1, "p1_2")
    r = await client.post(f"/v1/storyboards/{sid}/revisions", json={"target": {"kind": "section", "id": p12["id"]},
                                                                     "instruction": "짧게", "chips": []})
    await drain()
    await client.post(f"/v1/storyboards/{sid}/revisions/{r.json()['ref']['id']}/apply")
    await drain()
    m = sb1["direction"]["key_messages"][2]
    await client.patch(f"/v1/storyboards/{sid}/key-messages/{m['id']}", json={"text": "공간이 먼저 알아본다."})
    from winmate_storyboard import changes, service

    def keep(d):
        changes.record(d, place_label="Part 1-3", aspect="Galaxy XR", kind="kept", cause={"kind": "rq_sync", "label": "요구사항 정의서 v3"},
                       before_summary="검토 중", after_summary="검토 중 그대로 — 회의에서 언급, 확정 아님", revertible=False)
        return d

    await service.mutate(sid, keep)
    sb2 = (await client.get(f"/v1/storyboards/{sid}")).json()
    assert sb2["draft_label"] == "v2 초안" and sb2["has_unsaved_changes"] is True
    cmp = (await client.get(f"/v1/storyboards/{sid}/compare", params={"from": 1, "to": "draft"})).json()
    assert len(cmp["rows"]) == 3 and cmp["count"] == 2
    assert cmp["from"]["version"] == 1 and cmp["to"]["version_label"] == "v2" and cmp["revertible"] is True
    kept = next(x for x in cmp["rows"] if x["kind"] == "kept")
    assert kept["revertible"] is False
    assert cmp["causes"][0] == "요구사항 정의서 v3"
    rev_row = next(x for x in cmp["rows"] if x["cause"]["kind"] == "revision")
    r = await client.post(f"/v1/storyboards/{sid}/changes/{rev_row['id']}/revert")
    assert r.status_code == 200, r.text
    assert section_key(r.json(), "p1_2")["lines"] == p12["lines"]
    cmp2 = (await client.get(f"/v1/storyboards/{sid}/compare")).json()
    assert len(cmp2["rows"]) == 2 and cmp2["count"] == 1
    r = await client.post(f"/v1/storyboards/{sid}/changes/{kept['id']}/revert")
    assert r.status_code == 409 and r.json()["error"]["code"] == "NOT_REVERTIBLE"
    # v2 저장 → 버전 목록 · 저장 버전끼리 비교(되돌리기 없음) · 되살리기
    r = await client.post(f"/v1/storyboards/{sid}/save", json={"note": "회의 전"})
    assert r.json() == {"version": 2, "created": True}
    vers = (await client.get(f"/v1/storyboards/{sid}/versions")).json()["items"]
    assert [v["version"] for v in vers] == [2, 1] and vers[0]["note"] == "회의 전"
    cmp3 = (await client.get(f"/v1/storyboards/{sid}/compare", params={"from": 1, "to": "2"})).json()
    assert cmp3["revertible"] is False and all(not x["revertible"] for x in cmp3["rows"])
    v1 = (await client.get(f"/v1/storyboards/{sid}/versions/1")).json()
    assert v1["version"] == 1 and "outline" in v1["snapshot"]
    r = await client.post(f"/v1/storyboards/{sid}/versions/1/restore")
    assert r.status_code == 201 and r.json()["version"] == 3
    sb3 = (await client.get(f"/v1/storyboards/{sid}")).json()
    assert sb3["direction"]["key_messages"][2]["text"] == m["text"]
    r = await client.get(f"/v1/storyboards/{sid}/versions/9")
    assert r.status_code == 404 and r.json()["error"]["code"] == "VERSION_NOT_FOUND"
