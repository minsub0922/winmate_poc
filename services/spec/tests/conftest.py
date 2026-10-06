"""spec 테스트 공용 fixture — 도우미는 sp_helpers.py."""
from __future__ import annotations

import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from winmate_common import testing

sys.path.insert(0, str(Path(__file__).parent))  # sp_helpers

from sp_helpers import FIXED_NOW, AIStub, RQStub, cat_fix  # noqa: E402,F401


# ── 환경 ─────────────────────────────────────────────────

class Ctx:
    def __init__(self, tmp_path: Path, ai: AIStub, rq: RQStub, apps: dict[str, Any]):
        self.tmp = tmp_path
        self.ai = ai
        self.rq = rq
        self.apps = apps
        self.fix_path = tmp_path / "cat_fix.json"

    def use_cat_fix(self, **kw: Any) -> None:
        import os

        from winmate_common import env
        self.fix_path.write_text(json.dumps(cat_fix(**kw), ensure_ascii=False), encoding="utf-8")
        os.environ["SPEC_CATALOG_ADAPTER"] = "fixture"
        os.environ["SPEC_CATALOG_FIXTURE"] = str(self.fix_path)
        env.reset_caches()

    def use_kb(self) -> None:
        import os

        from winmate_common import env
        os.environ["SPEC_CATALOG_ADAPTER"] = "kb"
        env.reset_caches()

    def set_now(self, iso: str) -> None:
        import os

        from winmate_common import env
        os.environ["SPEC_FIXED_NOW"] = iso
        env.reset_caches()

    async def run_jobs(self, max_jobs: int = 50) -> int:
        from winmate_spec.worker import HANDLERS
        return await testing.drain_jobs("spec", HANDLERS, max_jobs=max_jobs)


@pytest.fixture
def ai_stub() -> AIStub:
    return AIStub()


@pytest.fixture
def rq_stub() -> RQStub:
    return RQStub()


@pytest.fixture
async def ctx(tmp_path: Path, ai_stub: AIStub, rq_stub: RQStub) -> AsyncIterator[Ctx]:
    import os
    with testing.environment(tmp_path, service="spec", SPEC_FIXED_NOW=FIXED_NOW, SPEC_CATALOG_ADAPTER="kb", SPEC_CATALOG_FIXTURE="",
                             KB_WARMUP="0", SPEC_ELECTRICITY_KRW_PER_KWH=""):
        testing.use_fake_redis()
        from winmate_spec import api_support, catalog
        catalog.reset_catalog()
        api_support._scheduled = False
        apps = {**testing.platform_apps("kb", "files", "jobs", "workspace", "export"), "ai-tools": ai_stub.app, "requirements": rq_stub.app}
        with testing.inprocess(apps):
            c = Ctx(tmp_path, ai_stub, rq_stub, apps)
            yield c
        catalog.reset_catalog()
        for k in ("SPEC_CATALOG_ADAPTER", "SPEC_CATALOG_FIXTURE"):
            os.environ.pop(k, None)


@pytest.fixture
async def client(ctx: Ctx) -> AsyncIterator[Any]:
    from winmate_spec.main import app
    async with testing.api_client(app) as c:
        yield c

