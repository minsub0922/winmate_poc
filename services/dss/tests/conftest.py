"""dss 테스트 공용 — 임시 DATA_DIR · fakeredis · in-process 서비스(플랫폼 + storyboard 허브 실제 앱)."""
from __future__ import annotations

from typing import Any

import pytest

from winmate_common import testing


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="dss"):
        testing.use_fake_redis()
        yield


@pytest.fixture
def apps(env) -> dict[str, Any]:
    from winmate_dss.main import app

    out: dict[str, Any] = {**testing.platform_apps(), "dss": app, "storyboard": testing.load_service_app("storyboard")}
    with testing.inprocess(out):
        yield out


@pytest.fixture
async def client(apps):
    async with testing.api_client(apps["dss"]) as c:
        yield c
