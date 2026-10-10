"""§9.1 수용 기준 8–16 — 기획 방향 · 표현 검사 · 목차 잡 · 상태 규칙 · 추적 완전성 · 링크."""
from __future__ import annotations

from winmate_common.jobs import jobs

from sb_flow import drain, section_key, space_named, to_direction, to_outline
from sb_world import RQ


async def test_direction_structure(client, world):
    sb = await to_direction(client)
    d = sb["direction"]
    assert d["ready"] is True
    kinds = [o["kind"] for o in d["options"]]
    assert kinds.count("combo") == 1 and kinds.count("axis") == 3
    combo = next(o for o in d["options"] if o["kind"] == "combo")
    assert d["recommended_option_id"] == combo["id"] == d["selected_option_id"]
    union: set[str] = set()
    for o in d["options"]:
        assert o["coverage"]["count"] <= o["coverage"]["total"] == 12
        if o["kind"] == "axis":
            union |= set(o["coverage"]["item_ids"])
            assert o["coverage"]["count"] == 4
    assert set(combo["coverage"]["item_ids"]) == union and combo["coverage"]["count"] == 12
    assert [m["place_label"] for m in combo["mapping"]] == ["Part 1 서사", "Key considerations · 1-3", "Part 2 공간"]
    assert [m["axis_label"] for m in combo["mapping"]] == ["A 진화 구도", "B 두 개의 이익", "C 하루의 공간"]
    assert combo["title"] == "AI Ready 오피스의 새로운 모델"
    assert len(d["key_messages"]) == 3 and d["internal_goal_count"] == 1
    assert sb["step"] == 2 and sb["sub_line"] == "기획 방향을 고르는 중"


async def test_expression_flags(client, world):
    sb = await to_direction(client)
    msgs = sb["direction"]["key_messages"]
    claim_msg = msgs[0]
    f = next(x for x in claim_msg["flags"] if x["kind"] == "unverified_claim")
    assert f["auto_applied"] is False and f["state"] == "open" and f["suggestion"] == "다음 단계의 AI Ready 오피스"
    assert f["span_text"] == "국내 최초 AI Ready 오피스" and "국내 최초" in claim_msg["text"]
    assert claim_msg["text"][f["span"][0]:f["span"][1]] == f["span_text"]
    goal_msg = msgs[1]
    g = next(x for x in goal_msg["flags"] if x["kind"] == "internal_goal")
    assert g["auto_applied"] is True and g["state"] == "applied"
    assert "스펙인" not in goal_msg["text"]
    assert goal_msg["text"] == "같은 센서 데이터가 임차인에게는 맞춤 서비스로, 임대인에게는 운영 데이터로."
    assert any(m["text"] == "설계 단계 삼성 스펙인" for m in sb["direction"]["internal_memos"])
    assert g["note"] == "'설계 단계 삼성 스펙인'은 삼성 영업목표라 고객 메시지에서 빼고 내부 메모로 옮겼어요"
    sid = sb["id"]
    r = await client.post(f"/v1/storyboards/{sid}/key-messages/{claim_msg['id']}/flags/{f['id']}/apply")
    assert r.status_code == 200
    assert r.json()["text"] == "성수가 Tech Ready의 표준을 만들었다면, 용산은 다음 단계의 AI Ready 오피스."
    r = await client.post(f"/v1/storyboards/{sid}/key-messages/{claim_msg['id']}/flags/{f['id']}/revert")
    assert r.json()["text"] == claim_msg["text"]
    r = await client.post(f"/v1/storyboards/{sid}/key-messages/{goal_msg['id']}/flags/{g['id']}/revert")
    body = r.json()
    assert "설계 단계 삼성 스펙인" in body["text"]
    g2 = next(x for x in body["flags"] if x["id"] == g["id"])
    assert g2["state"] == "reverted" and g2["note"] == "'설계 단계 삼성 스펙인'은 삼성 영업목표예요"
    sb2 = (await client.get(f"/v1/storyboards/{sid}")).json()
    assert not any(m.get("flag_id") == g["id"] for m in sb2["direction"]["internal_memos"])
    r = await client.post(f"/v1/storyboards/{sid}/key-messages/{goal_msg['id']}/flags/{g['id']}/apply")
    assert "스펙인" not in r.json()["text"]


async def test_message_edit_rechecks(client, world):
    sb = await to_direction(client)
    m = sb["direction"]["key_messages"][2]
    r = await client.patch(f"/v1/storyboards/{sb['id']}/key-messages/{m['id']}", json={"text": "업계 1위 플랫폼으로 출근부터 퇴근까지 잇는다."})
    assert r.status_code == 200, r.text
    flags = r.json()["flags"]
    assert any(f["kind"] == "unverified_claim" and "1위" in f["span_text"] for f in flags)
    assert r.json()["updated_by"] == "user"
    r = await client.patch(f"/v1/storyboards/{sb['id']}/key-messages/{m['id']}",
                           json={"text": "공간이 먼저 알아본다.", "source": {"service": "vp", "ref_id": "vp_1"}})
    assert r.json()["updated_by"] == "vp" and r.json()["flags"] == []
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert any(c["cause"]["kind"] == "vp" and c["cause"]["label"] == "VP 문장 반영" for c in sb2["changes"])
    items = (await client.get(f"/v1/storyboards/{sb['id']}/key-messages")).json()["items"]
    assert items[2]["text"] == "공간이 먼저 알아본다."


async def test_direction_select_axis_regenerates_messages(client, world):
    sb = await to_direction(client)
    axis = next(o for o in sb["direction"]["options"] if o["kind"] == "axis")
    r = await client.patch(f"/v1/storyboards/{sb['id']}/direction", json={"selected_option_id": axis["id"],
                                                                          "extra_direction": "Intro는 시장 변화로 열기"})
    assert r.status_code == 200 and r.json()["messages_job_id"]
    await drain()
    d = (await client.get(f"/v1/storyboards/{sb['id']}/direction")).json()
    assert d["selected_option_id"] == axis["id"] and d["extra_direction"] == "Intro는 시장 변화로 열기"
    assert all(m["axis_key"] == axis["key"] for m in d["key_messages"])


async def test_outline_events_and_structure(client, world):
    sb = await to_direction(client)
    r = await client.post(f"/v1/storyboards/{sb['id']}/outline", json={})
    job_id = r.json()["job_id"]
    r2 = await client.post(f"/v1/storyboards/{sb['id']}/outline", json={})
    assert r2.status_code == 409 and r2.json()["error"]["code"] == "JOB_RUNNING"
    mid = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert mid["active_job"]["kind"] == "sb.outline" and mid["step"] == 3
    await drain()
    evs = await jobs().events(job_id)
    steps = [e["data"] for _, e in evs if e["type"] == "step" and "key" in e["data"]]
    order: list[str] = []
    for s in steps:
        if s["key"] not in order:
            order.append(s["key"])
    assert order == ["classify", "map_axes", "write_sections", "trace"]
    ws = [s["done"] for s in steps if s["key"] == "write_sections" and s["state"] == "running"]
    assert ws == sorted(ws) and ws[-1] == 11
    assert steps[0]["label"] == "요구 12개 분류 · 내부 목표 1개 분리"
    assert [e["type"] for _, e in evs][-1] == "done"
    assert any(e["type"] == "progress" and "ratio" in e["data"] for _, e in evs)
    sb = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    ol = sb["outline"]
    assert [g["key"] for g in ol["groups"]] == ["start", "part1", "part2", "part3", "end"]
    names = {g: [s["name"] for s in ol["sections"] if s["group_key"] == g] for g in ("start", "end")}
    assert names == {"start": ["Overview", "Key considerations", "Intro"], "end": ["Outro", "Timeline"]}
    assert len(ol["sections"]) == 11
    assert all(set(sp["slots"]) == {"action", "trigger", "response", "exception", "metric"} for sp in ol["spaces"])
    assert len(ol["spaces"]) == 7 and space_named(sb, "주차장")["is_extension"] is True
    assert section_key(sb, "timeline")["direction"] == "리서치 → 공유 · 확정 → DSS 수급 → 분담 작성 → 디자인 → 납품"
    assert sb["draft_label"] == "v1 초안" and sb["active_job"] is None
    assert sb["sub_line"] == "로비 · 라운지 시나리오가 비어 있어요"


async def test_number_guard_and_status_rules(client, world):
    sb = await to_outline(client)
    p12 = section_key(sb, "p1_2")
    assert p12["lines"][2]["text"] == "임대료 프리미엄 [00]% 주장 · 원출처 [확인 필요]"
    # 문장만 본다(섹션 id 는 ULID 라 우연히 '35' 가 들어갈 수 있다)
    assert "35" not in str([ln["text"] for ln in p12["lines"]]) and p12["status"] == "needs_confirmation"
    st = {s["key"]: s["status"] for s in sb["outline"]["sections"]}
    assert st["p3_1"] == "tbd" and st["intro"] == "reviewing" and st["outro"] == "reviewing" and st["part2"] == "writing"
    assert st["overview"] == "confirmed" and st["p1_1"] == "confirmed"
    badges = {g["key"]: [b["label"] for b in g["badges"]] for g in sb["outline"]["groups"]}
    assert badges == {"start": ["검토 중 1"], "part1": ["확인 필요 1"], "part2": ["작성 중", "미완 2"], "part3": ["TBD"],
                      "end": ["검토 중 1"]}
    metas = [g["meta"] for g in sb["outline"]["groups"]]
    assert metas == ["Overview · Key considerations · Intro", "섹션 4", "공간 7", "섹션 1", "Outro · Timeline"]
    discs = sb["outline"]["discussions"]
    assert [d["label"] for d in discs] == ["Intro 문구", "Galaxy XR 적용", "Part 3 레퍼런스", "Digital Twin · BLE 위치"]
    assert [d["n"] for d in discs] == [1, 2, 3, 4]
    p2 = section_key(sb, "part2")
    assert p2["name"] == "공간 시나리오 (7)" and p2["direction"].startswith("사무실 · R&D · 로비")
    assert sb["counts"]["sections"] == 11 and sb["counts"]["tbd"] == 1


async def test_trace_completeness_and_links(client, world):
    sb = await to_outline(client)
    tr = sb["trace"]
    ids = [i["rq_item_id"] for i in tr["items"]]
    assert len(ids) == 12 and len(set(ids)) == 12
    states = [i["state"] for i in tr["items"]]
    assert set(states) <= {"ok", "to_resolve", "owner_check"}
    assert states.count("ok") + states.count("to_resolve") + states.count("owner_check") == 12
    assert states.count("ok") == 7 and states.count("to_resolve") == 4 and states.count("owner_check") == 1
    order = sorted([i for i in tr["items"] if i["state"] == "to_resolve"], key=lambda i: i["priority"])
    assert [i["code"] for i in order] == ["RQ-11", "RQ-07", "RQ-03", "RQ-05"]
    rq05 = next(i for i in tr["items"] if i["code"] == "RQ-05")
    assert rq05["question"]["options"][0]["kind"] == "keep_unconfirmed"
    assert rq05["question"]["recommended_option_id"] == rq05["question"]["options"][0]["id"]
    labels = {i["code"]: i["places_label"] for i in tr["items"]}
    assert labels["RQ-01"] == "Part 1-1 · 1-3" and labels["RQ-08"] == "Part 1-1 ~ 1-3"
    assert labels["RQ-12"] == "Part 1 → 2 → 3" and labels["RQ-11"] == "Part 2 로비"
    assert labels["RQ-10"] == "Part 1-4 · Part 2 공용공간 · 담당 확인 중"
    assert len(tr["extensions"]) == 5
    link = world.rq.links[(RQ, sb["id"])]
    assert link["rq_version"] == 2
    deps = {d["target"]["id"]: d for d in link["depends_on"]}
    for it in tr["items"]:
        if it["state"] == "ok":
            assert len(deps[it["rq_item_id"]]["places"]) >= 1
    assert not world.rq.calls_of("PATCH", "/draft")
