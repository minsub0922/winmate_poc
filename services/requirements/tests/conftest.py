"""requirements 테스트 공용 픽스처 — 임시 DATA_DIR · fakeredis · 플랫폼 실제 앱(in-process) · 호출 기록."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from winmate_common import testing

sys.path.insert(0, str(Path(__file__).parent))

from rq_testkit import AiStub, Recorder


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="requirements", RQ_FILL_SLOT_DELAY_MS="0"):
        testing.use_fake_redis()
        yield


@pytest.fixture
def platform(env):
    """플랫폼 실제 앱(ai-tools mock · kb 실데이터 · files · jobs · workspace · export), 호출 기록 포함."""
    apps = testing.platform_apps()
    rec = {name: Recorder(app, name) for name, app in apps.items()}
    with testing.inprocess(rec):
        yield rec


@pytest.fixture
def ai(env):
    """ai-tools 만 바꿔 끼울 수 있는 대역 + 나머지는 실제 앱."""
    stub = AiStub()
    apps = testing.platform_apps("kb", "files", "jobs", "workspace", "export")
    rec = {name: Recorder(app, name) for name, app in apps.items()}
    rec["ai-tools"] = Recorder(stub.app, "ai-tools")
    with testing.inprocess(rec):
        stub.rec = rec  # type: ignore[attr-defined]
        yield stub


@pytest.fixture
def app(env):
    from winmate_requirements.main import app as rq_app

    return rq_app


