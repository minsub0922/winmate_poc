"""테스트 도우미.

    from winmate_common import testing

    @pytest.fixture
    async def env(tmp_path):
        with testing.environment(tmp_path, service="requirements"):
            yield

    async def test_x(env):
        fake = testing.use_fake_redis()                      # 잡 큐를 fakeredis 로
        with testing.inprocess({"kb": kb_stub, "ai-tools": testing.load_service_app("ai-tools")}):
            async with testing.api_client(app) as c:          # 내부 토큰을 붙인 클라이언트
                r = await c.post("/v1/specs", json={...})

- `inprocess`: ServiceClient 가 게이트웨이 대신 주어진 ASGI 앱으로 보낸다(계약 검증은 그대로 한다).
- `load_service_app(name)`: 다른 서비스의 실제 앱을 테스트에서만 불러온다(운영 코드에서 다른 서비스 import 금지).
- `platform_apps(...)`: 플랫폼 서비스(ai-tools · kb · files · jobs · workspace · export) 실제 앱 묶음 — `inprocess({**platform_apps(), ...})`.
  ai-tools 는 mock 모드(결정적 가짜 응답), kb 는 winmate-kb 실제 데이터(읽기 전용)를 쓴다.
- `load_service_worker(name)`: 그 서비스 워커의 처리기(HANDLERS) — `drain_jobs(name, load_service_worker(name))`(예: export 렌더).
- `stub_app(service)`: 가짜 서비스용 FastAPI 앱(내부 토큰 검사 없음).
"""
from __future__ import annotations

import importlib
import os
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI

from . import client as _client
from . import env as _env
from . import jobs as _jobs
from .contracts import reload_contracts
from .registry import module_name


@contextmanager
def environment(tmp_path: Path, *, service: str | None = None, **extra: str) -> Iterator[None]:
    """DATA_DIR 를 임시 폴더로, 모델 모드를 mock 으로, 계약 검증을 strict 로."""
    keys = {
        "DATA_DIR": str(tmp_path / "data"),
        "MODEL_MODE": "mock",
        "CONTRACT_VALIDATION": "strict",
        "INTERNAL_TOKEN": "test-internal-token",
        "WINMATE_ENV": "dev",
        **({"WINMATE_SERVICE": service} if service else {}),
        **extra,
    }
    old = {k: os.environ.get(k) for k in keys}
    os.environ.update(keys)
    _env.reset_caches()
    reload_contracts()
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        _env.reset_caches()
        _client.set_transport_factory(None)
        _jobs.set_redis_factory(None)
        _jobs._jobs = None


def use_fake_redis() -> Any:
    import fakeredis

    server = fakeredis.FakeServer()

    def factory() -> Any:
        return fakeredis.FakeAsyncRedis(server=server, decode_responses=True)

    _jobs.set_redis_factory(factory)
    _jobs._jobs = None
    return server


@contextmanager
def inprocess(apps: dict[str, Any]) -> Iterator[None]:
    prev = _client._transport_factory

    def factory(target: str) -> httpx.AsyncBaseTransport | None:
        app = apps.get(target)
        return httpx.ASGITransport(app=app) if app is not None else None

    _client.set_transport_factory(factory)
    try:
        yield
    finally:
        _client.set_transport_factory(prev)


def load_service_app(service: str) -> FastAPI:
    mod = importlib.import_module(f"{module_name(service)}.main")
    return mod.app  # type: ignore[no-any-return]


PLATFORM_SERVICES = ("ai-tools", "kb", "files", "jobs", "workspace", "export")


def platform_apps(*names: str) -> dict[str, FastAPI]:
    """플랫폼 서비스의 실제 앱(테스트 전용). 이름을 주지 않으면 전부."""
    return {n: load_service_app(n) for n in (names or PLATFORM_SERVICES)}


def load_service_worker(service: str) -> dict[str, Any]:
    mod = importlib.import_module(f"{module_name(service)}.worker")
    return mod.HANDLERS  # type: ignore[no-any-return]


def stub_app(service: str) -> FastAPI:
    app = FastAPI(title=f"stub {service}")
    app.state.service = service
    return app


@asynccontextmanager
async def api_client(app: Any, *, user_id: str = "u_test", user_name: str = "테스터") -> AsyncIterator[httpx.AsyncClient]:
    from urllib.parse import quote

    headers = {
        "X-Internal-Token": _env.settings().internal_token,
        "X-User-Id": user_id,
        "X-User-Name": quote(user_name),
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers, timeout=60) as c:
        yield c


async def drain_jobs(service: str, handlers: dict[str, Any], *, max_jobs: int = 50) -> int:
    """테스트용: 큐에 쌓인 잡을 지금 처리한다(워커 프로세스 없이)."""
    worker = _jobs.Worker(service, handlers, concurrency=1)
    await worker._ensure_group()
    done = 0
    while done < max_jobs:
        res = await worker.jobs.r.xreadgroup(worker.group, worker.consumer, {worker.stream: ">"}, count=1, block=None)
        if not res:
            break
        for _stream, entries in res:
            for entry_id, fields in entries:
                await worker.process(entry_id, fields)
                done += 1
    return done
