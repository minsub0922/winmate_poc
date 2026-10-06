"""image 테스트 공용 — 임시 DATA_DIR · fakeredis · 플랫폼 실제 앱(in-process: ai-tools mock · kb 실데이터 · files · jobs · workspace · export).

ai-tools 앞에 `AiTap` 을 두어 호출(경로 · task · 본문)을 기록하고, task 별로 응답을 바꾸거나(오류 흉내 · QC 순서) 늦출 수 있다.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from winmate_common import testing

sys.path.insert(0, str(Path(__file__).parent))  # img_helpers

from img_helpers import USER, AiTap, Env  # noqa: E402

@pytest.fixture(scope="session")
def platform() -> dict[str, Any]:
    return testing.platform_apps()


@pytest.fixture
def env(tmp_path, platform, monkeypatch):
    extra = {"IMAGE_RETRY_DELAYS": "0,0", "IMAGE_PREFILL_TIMEOUT_S": "10", "KB_WARMUP": "0"}
    with testing.environment(tmp_path, service="image", **extra):
        testing.use_fake_redis()
        from winmate_image import caps, policy

        caps.reset()
        policy.dictionary.cache_clear()
        tap = AiTap(platform["ai-tools"])
        with testing.inprocess({**platform, "ai-tools": tap}):
            yield Env(tap, platform)
        caps.reset()


@pytest.fixture
def app(env):
    from winmate_image.main import app as image_app

    return image_app


@pytest.fixture
async def client(app):
    async with testing.api_client(app, user_id=USER, user_name="테스터") as c:
        yield c
