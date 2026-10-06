from __future__ import annotations

import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from winmate_common import testing

sys.path.insert(0, str(Path(__file__).parent))

from sc_world import World


@pytest.fixture
def env(tmp_path: Any) -> Iterator[None]:
    with testing.environment(tmp_path, service="scenario", SC_LLM_RETRY_DELAYS="0,0", SC_PACE_S="0", MOCK_ENFORCE_CONFIDENTIAL="false"):
        testing.use_fake_redis()
        from winmate_ai_tools import (
            fixtures as aifix,  # 고정 응답 순번 초기화(시험끼리 섞이지 않게)
        )
        aifix.reset()
        from winmate_scenario import birdseye as be
        from winmate_scenario import kbq
        be.clear_cache()
        kbq._cache.clear()
        yield


@pytest.fixture
def world(env: None) -> Iterator[World]:
    w = World()
    with testing.inprocess(w.apps):
        yield w


@pytest.fixture
async def client(world: World) -> AsyncIterator[Any]:
    from winmate_scenario.main import app
    async with testing.api_client(app) as c:
        yield c
