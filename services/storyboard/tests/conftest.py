from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from winmate_common import testing

sys.path.insert(0, str(Path(__file__).parent))

from sb_world import World  # noqa: E402


@pytest.fixture
def env(tmp_path: Any) -> Iterator[None]:
    with testing.environment(tmp_path, service="storyboard", SB_PACE_S="0"):
        testing.use_fake_redis()
        from winmate_ai_tools import fixtures as aifix  # 고정 응답 순번 초기화(시험끼리 섞이지 않게)
        aifix.reset()
        yield


@pytest.fixture
def world(env: None) -> Iterator[World]:
    w = World()
    with testing.inprocess(w.apps):
        yield w


@pytest.fixture
async def client(world: World) -> AsyncIterator[Any]:
    from winmate_storyboard.main import app
    async with testing.api_client(app) as c:
        yield c
