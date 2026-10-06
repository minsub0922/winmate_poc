"""proposal 테스트 공용 — 임시 DATA_DIR · fakeredis · 플랫폼 실제 앱(in-process) · 시각 고정(§9.0)."""
from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from winmate_common import testing

sys.path.insert(0, str(Path(__file__).parent))

from pr_stubs import Stubs  # noqa: E402

FIXED_NOW = "2026-10-01T09:00:00+09:00"


class Ctx:
    def __init__(self, tmp: Path, apps: dict[str, Any], stubs: Stubs):
        self.tmp = tmp
        self.apps = apps
        self.stubs = stubs

    async def run_jobs(self, max_jobs: int = 60) -> int:
        from winmate_proposal.worker import HANDLERS
        total = 0
        for _ in range(6):
            n = await testing.drain_jobs("proposal", HANDLERS, max_jobs=max_jobs)
            m = 0
            if "export" in self.apps:
                m = await testing.drain_jobs("export", testing.load_service_worker("export"), max_jobs=max_jobs)
            total += n + m
            if not n and not m:
                break
        return total


@pytest.fixture
def stubs() -> Stubs:
    return Stubs()


@pytest.fixture
async def ctx(tmp_path: Path, stubs: Stubs) -> AsyncIterator[Ctx]:
    with testing.environment(tmp_path, service="proposal", PROPOSAL_FIXED_NOW=FIXED_NOW, PROPOSAL_PACE_S="0", KB_WARMUP="0",
                             PROPOSAL_EXPORT_WAIT_S="2", SOFFICE_PATH="off"):
        testing.use_fake_redis()
        from winmate_proposal import clients
        clients.clear_cache()
        apps = {**testing.platform_apps(), **stubs.apps()}
        with testing.inprocess(apps):
            yield Ctx(tmp_path, apps, stubs)
        clients.clear_cache()


@pytest.fixture
async def client(ctx: Ctx) -> AsyncIterator[Any]:
    from winmate_proposal.main import app
    async with testing.api_client(app, user_id="u_choi", user_name="최민섭") as c:
        yield c
