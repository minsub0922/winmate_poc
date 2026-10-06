"""§9.1 수용 기준 1–7 · 34 — 생성 · 재사용 · 목록 · 정의서 잠금 · 기획 질의."""
from __future__ import annotations

import re

from sb_flow import answer_all, create, drain, q_by_topic
from sb_world import RQ

ID_RE = re.compile(r"^sb_[0-9A-HJKMNP-TV-Z]{26}$")


async def test_create_prepare(client, world):
    r = await client.post("/v1/storyboards", json={"requirement_id": RQ})
    assert r.status_code == 201, r.text
    body = r.json()
    assert ID_RE.match(body["id"])
    assert body["started"] is False and body["step"] == 1
    assert body["prepare_job_id"]
    assert body["active_job"]["kind"] == "sb.prepare"
    await drain()
    sb = (await client.get(f"/v1/storyboards/{body['id']}")).json()
    s = sb["settings"]
    assert s["ready"] is True
    assert {s[k]["source"] for k in ("stage", "doc_type", "volume", "language")} == {"rq"}
    assert s["summary"] == "컨셉 제안 · 고객 맞춤 제안 · 약 20장 · 한국어"
    assert s["all_from_rq"] is True
    assert s["stage"]["evidence"] == "요청서: 사업계획 · 공간 구성 단계"
    assert s["volume"]["evidence"] == "6개 공간을 담으려면 20장 이상"
    qs = sb["planning"]["questions"]
    assert 1 <= len(qs) <= 3
    assert [q["topic"] for q in qs] == ["decision", "audience", "comparison"]
    assert qs[0]["order_roles"] == ["Overview 목적", "Outro 다음 단계"]
    aud = q_by_topic(sb, "audience")
    last = aud["options"][-1]
    assert (last["label"], last["badge"], last["hint"]) == ("최종 의사결정자", "확인 필요", "누구인지 아직 몰라요")
    comp = q_by_topic(sb, "comparison")
    assert comp["select"] == "single" and comp["options"][0]["follow_up"]["label"] == "이어서 하나만"
    assert sb["name"] == "용산 오피스 제안 기획" and sb["title"] == "E 자산운용 용산 오피스 제안 기획"
    assert sb["requirement_ref"]["item_count"] == 12
    assert len(world.rq.calls_of("PUT", f"/links/storyboard/{body['id']}")) == 1
    assert sb["active_job"] is None


async def test_reuse_draft_and_list_hides(client, world):
    first = await create(client)
    r = await client.post("/v1/storyboards", json={"requirement_id": RQ})
    assert r.status_code == 200 and r.json()["id"] == first["id"]
    # 시작된 것 2개를 만든다(질의 건너뛰기 → started)
    started = []
    for _ in range(2):
        sb = first if not started else None
        if sb is None:
            from winmate_storyboard import repo
            # 초안이 시작되면 다음 POST 는 새 문서를 만든다
            r = await client.post("/v1/storyboards", json={"requirement_id": RQ})
            assert r.status_code == 201
            await drain()
            sb = (await client.get(f"/v1/storyboards/{r.json()['id']}")).json()
            assert await repo.get_sb(sb["id"])
        r = await client.post(f"/v1/storyboards/{sb['id']}/direction", json={"skip_planning": True})
        assert r.status_code == 202
        started.append(sb["id"])
    await drain()
    r = await client.post("/v1/storyboards", json={"requirement_id": RQ})   # 시작 전 초안 1
    assert r.status_code == 201
    draft_id = r.json()["id"]
    items = (await client.get("/v1/storyboards")).json()["items"]
    ids = [i["id"] for i in items]
    assert set(ids) == set(started) and draft_id not in ids
    counts = (await client.get("/v1/storyboards/counts")).json()
    assert counts == {"all": 2, "in_progress": 2, "done": 0}
    assert items[0]["step_label"] == "2/5 기획 방향" and items[0]["cta"] == "continue"
    assert items[0]["sub_line"] == "기획 방향을 고르는 중"


async def test_unsaved_requirement_422(client, world):
    world.rq.add("rq_01JTESTREQUIREMENTV0000000", 0)
    r = await client.post("/v1/storyboards", json={"requirement_id": "rq_01JTESTREQUIREMENTV0000000"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "RQ_NOT_SAVED"


async def test_stage_locked(client, world):
    sb = await create(client)
    await client.post(f"/v1/storyboards/{sb['id']}/direction", json={"skip_planning": True})
    r = await client.put(f"/v1/storyboards/{sb['id']}/requirement", json={"requirement_id": RQ})
    assert r.status_code == 409 and r.json()["error"]["code"] == "STAGE_LOCKED"


async def test_put_requirement_reprepares(client, world):
    sb = await create(client)
    world.rq.add("rq_01JTESTREQUIREMENTOTHER0001", 1)
    r = await client.put(f"/v1/storyboards/{sb['id']}/requirement", json={"requirement_id": "rq_01JTESTREQUIREMENTOTHER0001"})
    assert r.status_code == 202
    await drain()
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb2["requirement_ref"]["requirement_id"] == "rq_01JTESTREQUIREMENTOTHER0001"
    assert sb2["requirement_ref"]["version"] == 1 and sb2["settings"]["ready"]


async def test_planning_answer_order(client, world):
    sb = await create(client)
    q = q_by_topic(sb, "decision")
    a, b = q["options"][0]["id"], q["options"][1]["id"]
    r = await client.put(f"/v1/storyboards/{sb['id']}/planning/{q['id']}", json={"selected_option_ids": [b, a]})
    assert r.status_code == 200, r.text
    ans = r.json()
    assert ans["selected_option_ids"] == [b, a]
    assert ans["roles"] == {b: "Overview 목적", a: "Outro 다음 단계"}
    r = await client.put(f"/v1/storyboards/{sb['id']}/planning/{q['id']}", json={})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NOTHING_SELECTED"
    # 직접 입력은 선택지로 더해지고 마지막 순서
    r = await client.put(f"/v1/storyboards/{sb['id']}/planning/{q['id']}", json={"selected_option_ids": [a],
                                                                              "custom_text": "투자 심의 일정"})
    ans = r.json()
    assert len(ans["selected_option_ids"]) == 2 and ans["custom_text"] == "투자 심의 일정"
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb2["sub_line"] == "기획 질의 2 / 3"
    assert sb2["route"].endswith("/planning/2")


async def test_skip_planning(client, world):
    sb = await create(client)
    r = await client.post(f"/v1/storyboards/{sb['id']}/direction", json={"skip_planning": True})
    assert r.status_code == 202 and r.json()["job_id"]
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb2["started"] is True and sb2["step"] == 2
    assert all(a["unknown"] for a in sb2["planning"]["answers"])
    assert len(sb2["planning"]["answers"]) == len(sb2["planning"]["questions"])


async def test_follow_up_validation(client, world):
    sb = await create(client)
    await answer_all(client, sb)
    q = q_by_topic(sb, "comparison")
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    ans = next(a for a in sb2["planning"]["answers"] if a["question_id"] == q["id"])
    assert ans["follow_up_option_id"] == q["options"][0]["follow_up"]["options"][2]["id"]
    r = await client.put(f"/v1/storyboards/{sb['id']}/planning/{q['id']}",
                         json={"selected_option_ids": [q["options"][1]["id"]], "follow_up_option_id": "opt_nope"})
    assert r.status_code == 422


async def test_not_found(client, world):
    r = await client.get("/v1/storyboards/sb_01JTESTNOTEXIST00000000000")
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "NOT_FOUND" and err["message"]
