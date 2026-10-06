from __future__ import annotations

import pytest

from winmate_common import testing


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="competitor"):
        yield


async def test_info(env):
    from winmate_competitor.main import app

    async with testing.api_client(app) as c:
        r = await c.get("/v1/info")
        assert r.status_code == 200
        assert r.json()["service"] == "competitor"


async def test_requires_internal_token(env):
    import httpx
    from winmate_competitor.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/v1/info")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHENTICATED"
