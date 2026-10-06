from __future__ import annotations

from pathlib import Path

import pytest

from winmate_common import testing
from winmate_common.env import repo_root

WKB = repo_root() / "winmate-kb"


@pytest.fixture
def env(tmp_path: Path):
    """실제 KB 파일(winmate-kb/kb/winmate_kb.sqlite)로 돈다. 로컬 이미지 폴더는 임시 폴더."""
    with testing.environment(tmp_path, service="kb", WKB_ROOT=str(WKB), WKB_KB=str(WKB / "kb"),
                             WKB_IMAGE_DIR=str(tmp_path / "images"), KB_WARMUP="0"):
        yield tmp_path


@pytest.fixture
async def client(env):
    from winmate_kb.main import app

    async with testing.api_client(app) as c:
        yield c


@pytest.fixture(scope="session")
def contract():
    """코드에서 바로 만든 계약(응답이 계약 스키마와 맞는지 검사용)."""
    from winmate_common.contracts import Contract
    from winmate_kb.main import app

    return Contract("kb", app.openapi())


@pytest.fixture
def ok(contract):
    """상태 200 + 계약 스키마 검증 후 JSON."""

    def _ok(r, method: str = "GET") -> dict:
        assert r.status_code == 200, r.text[:800]
        body = r.json()
        contract.validate_response(method, r.request.url.path, r.status_code, body, r.headers.get("content-type", ""))
        return body

    return _ok
