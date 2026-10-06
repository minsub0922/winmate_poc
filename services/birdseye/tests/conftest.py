"""birdseye 테스트 공용 — 임시 DATA_DIR · fakeredis · in-process 플랫폼(ai-tools mock · kb 실데이터 · files · jobs · workspace · export) + image."""
from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path
from typing import Any

import pytest

from winmate_common import testing

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def _release_memory():
    """시험마다 큰 그림(렌더 3840×2160)을 만들어 메모리가 쌓인다 — 공유 장비(2 CPU · 7 GB)라 시험이 끝날 때마다 돌려준다."""
    yield
    import ctypes
    import gc

    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        pass


@pytest.fixture
def env(tmp_path):
    # 렌더는 기본 fhd(메모리) — 3840×2160 경로는 test_ac40 이 BE_RENDER_TARGET=uhd 로 본다
    with testing.environment(tmp_path, service="birdseye", BE_RETRY_DELAYS="0", BE_RENDER_POLL_S="0.05", AUTO_EXTRA_CUTS="true",
                             BE_RENDER_TARGET="fhd"):
        testing.use_fake_redis()
        yield tmp_path


@pytest.fixture
def platform(env):
    """in-process 플랫폼 + image(렌더 API) — ServiceClient 가 이 앱들로 보낸다."""
    apps = {**testing.platform_apps(), "image": testing.load_service_app("image")}
    with testing.inprocess(apps):
        yield apps


@pytest.fixture
async def client(platform):
    from winmate_birdseye.main import app

    async with testing.api_client(app) as c:
        yield c


from be_kit import create, drain, handlers, png, raster_plan, seed_golden, upload  # noqa: E402,F401  (예전 import 경로)
