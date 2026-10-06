"""vp 테스트 공용 — 임시 DATA_DIR · fakeredis · in-process 서비스(플랫폼 + requirements · storyboard · mi 실제 앱)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from winmate_common import testing

FIX = Path(__file__).parent / "fixtures"
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="vp"):
        testing.use_fake_redis()
        yield


@pytest.fixture
def apps(env) -> dict[str, Any]:
    from winmate_vp.main import app

    out: dict[str, Any] = {**testing.platform_apps(), "vp": app}
    for svc in ("requirements", "storyboard", "mi"):
        out[svc] = testing.load_service_app(svc)
    with testing.inprocess(out):
        yield out


@pytest.fixture
async def client(apps):
    async with testing.api_client(apps["vp"]) as c:
        yield c
