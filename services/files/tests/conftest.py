from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest

from winmate_common import testing

sys.path.insert(0, str(Path(__file__).parent))  # files_samples


@pytest.fixture
def soffice_off() -> dict[str, str]:
    """LibreOffice 없는 환경을 흉내 낸다."""
    return {"SOFFICE_PATH": "off"}


def _env(tmp_path: Path, **extra: str) -> Iterator[None]:
    with testing.environment(tmp_path, service="files", **extra):
        yield


@pytest.fixture
def env(tmp_path: Path) -> Iterator[None]:
    yield from _env(tmp_path, SOFFICE_PATH="off")


@pytest.fixture
def env_lo(tmp_path: Path) -> Iterator[None]:
    """LibreOffice 를 쓰는 환경(설치돼 있지 않으면 건너뛴다)."""
    from winmate_files.settings import soffice_path

    with testing.environment(tmp_path, service="files", SOFFICE_TIMEOUT_S="60"):
        if not soffice_path():
            pytest.skip("LibreOffice(soffice) 없음 — SOFFICE_PATH 로 지정")
        yield


@pytest.fixture
def env_small(tmp_path: Path) -> Iterator[None]:
    yield from _env(tmp_path, SOFFICE_PATH="off", UPLOAD_MAX_MB="1")


async def _client(user_id: str = "u_test", user_name: str = "테스터") -> AsyncIterator:
    from winmate_files.main import app
    from winmate_files.service import service

    async with testing.api_client(app, user_id=user_id, user_name=user_name) as c:
        yield c
    # 백그라운드 파싱을 끝까지 기다린다(멈추면 오래 매달리지 않고 실패)
    await asyncio.wait_for(service().wait_idle(), timeout=60)


@pytest.fixture
async def client(env: None) -> AsyncIterator:
    async for c in _client():
        yield c


@pytest.fixture
async def client_lo(env_lo: None) -> AsyncIterator:
    async for c in _client():
        yield c


@pytest.fixture
async def client_small(env_small: None) -> AsyncIterator:
    async for c in _client():
        yield c


async def upload(c, name: str, data: bytes, **form: str) -> dict:  # noqa: ANN001
    r = await c.post("/v1/files", files={"file": (name, data)}, data=form)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def up():
    return upload
