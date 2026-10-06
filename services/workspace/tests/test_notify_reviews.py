"""작업물 알림(spec 요청) · 검토 마감일 · 대상 확인 · 다시 요청 라운드(proposal 요청)."""
from __future__ import annotations

import pytest

from winmate_common import testing


@pytest.fixture
def env(tmp_path):
    from winmate_workspace import db

    with testing.environment(tmp_path, service="workspace"):
        db.reset_store()
        fake = testing.use_fake_redis()
        yield fake
        db.reset_store()


async def _jobs_notifications(owner: str):
    from winmate_common.jobs import jobs

    return [d for _, d in await jobs().notifications(owner)]


async def test_item_notifications(env):
    from winmate_workspace.main import app

    async with testing.api_client(app, user_id="u_owner", user_name="주인") as owner:
        await owner.put("/v1/items/pr_1", json={"feature": "PR", "title": "A 커피 제안", "status": "draft", "route": "/proposal/pr_1"})
    # spec 서비스(다른 사용자 맥락)가 제안서 항목으로 알림
    async with testing.api_client(app, user_id="u_spec", user_name="스펙담당") as spec:
        r = await spec.post("/v1/notifications", json={"item_id": "pr_1", "type": "spec_link_changed", "title": "Spec 시트 값이 바뀌었어요",
                                                         "route": "/proposal/pr_1/sections/spec", "ref": "sp_9", "service": "spec"})
        assert r.status_code == 201, r.text
        made = r.json()["items"]
        assert [n["recipient"] for n in made] == ["u_owner"]
        assert made[0]["item"] == {"feature": "PR", "id": "pr_1"} and made[0]["by_name"] == "스펙담당"
        # 항목이 없고 받는 사람도 없으면 404, 받는 사람을 주면 항목 없이도 만든다
        assert (await spec.post("/v1/notifications", json={"item_id": "pr_missing", "title": "x"})).status_code == 404
        r = await spec.post("/v1/notifications", json={"item_id": "pr_missing", "title": "x", "recipients": ["u_other"]})
        assert r.status_code == 201 and r.json()["items"][0]["item"] == {"feature": None, "id": "pr_missing"}
        # route 가 없으면 항목 route
        r = await spec.post("/v1/notifications", json={"item_id": "pr_1", "title": "두 번째"})
        assert r.json()["items"][0]["route"] == "/proposal/pr_1"
    # jobs 알림 흐름에도 들어간다
    pushed = await _jobs_notifications("u_owner")
    assert any(p["type"] == "spec_link_changed" and p["item"]["id"] == "pr_1" for p in pushed)

    async with testing.api_client(app, user_id="u_owner", user_name="주인") as owner:
        lst = (await owner.get("/v1/notifications")).json()
        assert lst["unread"] == 2 and sorted(n["title"] for n in lst["items"]) == ["Spec 시트 값이 바뀌었어요", "두 번째"]
        counts = (await owner.get("/v1/notifications/counts")).json()
        assert counts == {"unread": 2, "items": [{"item_id": "pr_1", "feature": "PR", "unread": 2}]}
        first = next(n["id"] for n in lst["items"] if n["title"].startswith("Spec"))
        assert (await owner.post("/v1/notifications/read", json={"ids": [first]})).json() == {"updated": 1}
        assert (await owner.get("/v1/notifications/counts")).json()["unread"] == 1
        assert (await owner.post("/v1/notifications/read", json={"item_id": "pr_1"})).json() == {"updated": 1}
        assert (await owner.get("/v1/notifications", params={"unread_only": True})).json()["items"] == []
        assert (await owner.get("/v1/notifications", params={"item_id": "pr_1"})).json()["unread"] == 0
    async with testing.api_client(app, user_id="u_other", user_name="다른") as other:
        assert (await other.get("/v1/notifications/counts")).json()["unread"] == 1
        assert (await other.post("/v1/notifications/read", json={})).json() == {"updated": 1}


async def test_notification_exclude_actor(env):
    from winmate_workspace.main import app

    async with testing.api_client(app, user_id="u_owner", user_name="주인") as owner:
        await owner.put("/v1/items/pr_2", json={"feature": "PR", "title": "B", "status": "draft", "route": "/proposal/pr_2"})
        r = await owner.post("/v1/notifications", json={"item_id": "pr_2", "title": "내가 바꿈", "exclude_actor": True})
        assert r.status_code == 201 and r.json()["items"] == []
        r = await owner.post("/v1/notifications", json={"item_id": "pr_2", "title": "나에게도"})
        assert len(r.json()["items"]) == 1


async def test_review_due_checks_and_rounds(env):
    from winmate_workspace.main import app

    async with testing.api_client(app, user_id="u_a", user_name="가나다") as a:
        await a.put("/v1/items/pr_9", json={"feature": "PR", "title": "제안서", "status": "draft", "route": "/proposal/pr_9"})
        r = await a.post("/v1/reviews", json={"target": "proposal:pr_9:v1", "title": "제안서 검토", "route": "/proposal/pr_9/review",
                                               "reviewers": ["u_b", "u_c"], "required_approvals": 2, "due_date": "2026-10-08",
                                               "version_label": "v1"})
        assert r.status_code == 201, r.text
        rv = r.json()
        rid = rv["id"]
        assert rv["due_date"] == "2026-10-08" and rv["round"] == 1 and rv["item_id"] == "pr_9" and rv["checks"] == [] and rv["rounds"] == []
        assert (await a.post("/v1/reviews", json={"target": "x", "title": "t", "route": "/", "reviewers": ["u_b"], "due_date": "10/8"})).status_code == 422
    # 검토자에게 알림(항목 = 제안서)
    async with testing.api_client(app, user_id="u_b", user_name="라마바") as b:
        n = (await b.get("/v1/notifications")).json()["items"]
        assert n[0]["type"] == "review_requested" and n[0]["item"] == {"feature": "PR", "id": "pr_9"}
        assert n[0]["data"]["review_id"] == rid and n[0]["data"]["due_date"] == "2026-10-08"
        r = await b.put(f"/v1/reviews/{rid}/checks/sheet:sh_1", json={"state": "ok"})
        assert r.status_code == 200
        r = await b.put(f"/v1/reviews/{rid}/checks/sheet:sh_2", json={"state": "need", "comment": "수치 확인"})
        r = await b.put(f"/v1/reviews/{rid}/checks/sheet:sh_1", json={"state": "need"})  # 같은 대상은 바꾼다
        checks = {(c["user_id"], c["target_ref"]): c["state"] for c in r.json()["checks"]}
        assert checks == {("u_b", "sheet:sh_1"): "need", ("u_b", "sheet:sh_2"): "need"}
        r = await b.delete(f"/v1/reviews/{rid}/checks/sheet:sh_1")
        assert [c["target_ref"] for c in r.json()["checks"]] == ["sheet:sh_2"]
        r = await b.post(f"/v1/reviews/{rid}/decision", json={"decision": "request_changes", "comment": "고쳐 주세요"})
        assert r.json()["status"] == "changes_requested"
    async with testing.api_client(app, user_id="u_x", user_name="남") as x:
        assert (await x.put(f"/v1/reviews/{rid}/checks/sh_1", json={"state": "ok"})).status_code == 403
        assert (await x.post(f"/v1/reviews/{rid}/resubmit", json={})).status_code == 403
    async with testing.api_client(app, user_id="u_a", user_name="가나다") as a:
        n = (await a.get("/v1/notifications")).json()["items"]
        assert n[0]["type"] == "review_decided" and n[0]["data"]["decision"] == "request_changes"
        r = await a.post(f"/v1/reviews/{rid}/resubmit", json={"message": "반영했어요", "version_label": "v2"})
        assert r.status_code == 200, r.text
        rv = r.json()
        assert rv["round"] == 2 and rv["status"] == "pending" and rv["checks"] == [] and rv["version_label"] == "v2"
        assert all(x["decision"] == "pending" for x in rv["reviewers"]) and rv["due_date"] == "2026-10-08"
        old = rv["rounds"][0]
        assert old["round"] == 1 and old["status"] == "changes_requested" and old["version_label"] == "v1"
        assert [c["target_ref"] for c in old["checks"]] == ["sheet:sh_2"]
        assert any(x["decision"] == "request_changes" for x in old["reviewers"])
        r = await a.patch(f"/v1/reviews/{rid}", json={"due_date": "2026-10-10"})
        assert r.json()["due_date"] == "2026-10-10"
        assert (await a.patch(f"/v1/reviews/{rid}", json={"clear_due_date": True})).json()["due_date"] is None
        by_item = (await a.get("/v1/reviews", params={"item_id": "pr_9"})).json()["items"]
        assert [x["id"] for x in by_item] == [rid]
    async with testing.api_client(app, user_id="u_c", user_name="사아자") as c:
        mine = (await c.get("/v1/reviews", params={"mine": "to_review"})).json()["items"]
        assert [x["id"] for x in mine] == [rid]
        types = [x["type"] for x in (await c.get("/v1/notifications")).json()["items"]]
        assert types[:2] == ["review_resubmitted", "review_requested"]
        await c.post(f"/v1/reviews/{rid}/decision", json={"decision": "approve"})
    async with testing.api_client(app, user_id="u_b", user_name="라마바") as b:
        r = await b.post(f"/v1/reviews/{rid}/decision", json={"decision": "approve"})
        assert r.json()["status"] == "approved" and r.json()["approvals"] == 2
    async with testing.api_client(app, user_id="u_a", user_name="가나다") as a:
        await a.post(f"/v1/reviews/{rid}/cancel")
        assert (await a.post(f"/v1/reviews/{rid}/resubmit", json={})).status_code == 409


async def test_review_without_item_still_works(env):
    """색인에 없는 대상이면 item 없이 알림(예전 동작과 같음)."""
    from winmate_workspace.main import app

    async with testing.api_client(app, user_id="u_a", user_name="가나다") as a:
        r = await a.post("/v1/reviews", json={"target": "storyboard:sb_1", "title": "SB 검토", "route": "/storyboard/sb_1", "reviewers": ["u_b"]})
        assert r.status_code == 201 and r.json()["item_id"] is None
    async with testing.api_client(app, user_id="u_b", user_name="라마바") as b:
        n = (await b.get("/v1/notifications")).json()["items"]
        assert n[0]["item"] is None and n[0]["route"] == "/storyboard/sb_1"
        assert (await b.get("/v1/notifications/counts")).json() == {"unread": 1, "items": []}
