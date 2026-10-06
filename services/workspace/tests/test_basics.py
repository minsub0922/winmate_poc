from __future__ import annotations

import pytest

from winmate_common import testing


@pytest.fixture
def env(tmp_path):
    from winmate_workspace import db

    with testing.environment(tmp_path, service="workspace"):
        db.reset_store()
        testing.use_fake_redis()
        yield
        db.reset_store()


async def test_me_and_items(env):
    from winmate_workspace.main import app

    async with testing.api_client(app, user_id="u_dev", user_name="최민섭") as c:
        me = (await c.get("/v1/me")).json()
        assert me["initial"] == "최" and me["given_name"] == "민섭"
        r = await c.put("/v1/items/rq_1", json={"feature": "RQ", "title": "E 자산운용 용산", "status": "draft", "route": "/requirements/rq_1"})
        assert r.status_code == 200 and r.json()["owner"] == "u_dev"
        await c.put("/v1/items/sb_1", json={"feature": "SB", "title": "기획", "status": "draft", "route": "/storyboard/sb_1"})
        items = (await c.get("/v1/items", params={"feature": "RQ"})).json()["items"]
        assert [i["item_id"] for i in items] == ["rq_1"]
        counts = {x["feature"]: x["count"] for x in (await c.get("/v1/items/counts")).json()["items"]}
        assert counts["RQ"] == 1 and counts["SB"] == 1 and counts["PR"] == 0
        recent = (await c.get("/v1/items", params={"limit": 3})).json()["items"]
        assert recent[0]["item_id"] == "sb_1"


async def test_reviews(env):
    from winmate_workspace.main import app

    async with testing.api_client(app, user_id="u_a", user_name="가나다") as a:
        r = await a.post("/v1/reviews", json={"target": "proposal:pr_1:v1", "title": "제안서 검토", "route": "/proposal/pr_1",
                                               "reviewers": ["u_b", "u_c"], "required_approvals": 2})
        rid = r.json()["id"]
    async with testing.api_client(app, user_id="u_b", user_name="라마바") as b:
        mine = (await b.get("/v1/reviews", params={"mine": "to_review"})).json()["items"]
        assert [x["id"] for x in mine] == [rid]
        r = await b.post(f"/v1/reviews/{rid}/decision", json={"decision": "approve"})
        assert r.json()["approvals"] == 1 and r.json()["status"] == "pending"
    async with testing.api_client(app, user_id="u_c", user_name="사아자") as cc:
        r = await cc.post(f"/v1/reviews/{rid}/decision", json={"decision": "approve"})
        assert r.json()["status"] == "approved"


async def test_comments_and_usage(env):
    from winmate_workspace.main import app

    async with testing.api_client(app) as c:
        r = await c.post("/v1/comments", json={"target": "proposal:pr_1:sheet:s1", "body": "수치 확인"})
        assert r.status_code == 201
        lst = (await c.get("/v1/comments", params={"target": "proposal:pr_1*"})).json()["items"]
        assert len(lst) == 1
        assert (await c.put("/v1/asset-usage/kb:image:img_1", json={"proposal_id": "pr_1", "sheet_id": "s1"})).status_code == 204
        u = (await c.get("/v1/asset-usage", params={"refs": "kb:image:img_1,kb:image:img_2"})).json()["items"]
        assert u[0]["proposals"] == 1 and u[1]["proposals"] == 0
