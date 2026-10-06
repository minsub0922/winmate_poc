from __future__ import annotations

import pytest

from winmate_common import testing
from winmate_common.jobs import jobs


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="jobs"):
        testing.use_fake_redis()
        yield


async def test_job_lifecycle_api(env):
    from winmate_jobs.main import app

    job = await jobs().enqueue("requirements", "extract", {"a": 1}, title="추출")
    async with testing.api_client(app) as c:
        r = await c.get(f"/v1/jobs/{job.id}")
        assert r.status_code == 200 and r.json()["status"] == "queued" and r.json()["queue_position"] == 1
        r = await c.get("/v1/jobs", params={"owner": "all"})
        assert any(j["id"] == job.id for j in r.json()["items"])
        r = await c.post(f"/v1/jobs/{job.id}/memos", json={"text": "표지는 빼줘"})
        assert r.status_code == 201
        r = await c.post(f"/v1/jobs/{job.id}/cancel")
        assert r.json()["status"] == "canceled"
        r = await c.get(f"/v1/jobs/{job.id}/events/list")
        types = [e["type"] for e in r.json()["items"]]
        assert types[-1] == "done"
        r = await c.get("/v1/notifications")
        # 소유자(system)가 아닌 테스터에게는 알림이 없다
        assert r.status_code == 200


async def test_sse_stream_finishes(env):
    from winmate_jobs.main import app

    job = await jobs().enqueue("requirements", "extract", {})
    await jobs().cancel(job.id)
    async with testing.api_client(app) as c:
        async with c.stream("GET", f"/v1/jobs/{job.id}/events") as resp:
            assert resp.status_code == 200
            body = ""
            async for chunk in resp.aiter_text():
                body += chunk
                if "event: done" in body:
                    break
    assert "event: status" in body and "event: done" in body


async def test_schedule_api(env):
    from winmate_jobs.main import app

    async with testing.api_client(app) as c:
        r = await c.post("/v1/schedules", json={"service": "competitor", "kind": "recheck", "delay_s": 0, "ref": "ca_1"})
        assert r.status_code == 201
        sid = r.json()["id"]
        r = await c.get("/v1/schedules", params={"ref": "ca_1"})
        assert [s["id"] for s in r.json()["items"]] == [sid]
    started = await jobs().run_due_schedules()
    assert len(started) == 1
