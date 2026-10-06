#!/usr/bin/env python3
"""서비스 골격 만들기: `uv run python scripts/new_service.py <name>` (config/services.yaml 에 먼저 등록).

이미 있는 파일은 건드리지 않는다(--force 로 덮어쓰기).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

SCENARIO = {
    "requirements": "01-requirements.md", "storyboard": "02-storyboard.md", "mi": "03-mi.md",
    "competitor": "04-competitor.md", "vp": "05-vp.md", "spec": "06-spec.md", "image": "07-image.md",
    "birdseye": "08-birdseye.md", "scenario": "09-scenario.md", "proposal": "10-proposal.md",
}

PYPROJECT = """[project]
name = "winmate-{name}"
version = "0.1.0"
description = "{title}"
requires-python = ">=3.11"
dependencies = ["winmate-common"]

[tool.uv.sources]
winmate-common = {{ workspace = true }}

[build-system]
requires = ["hatchling>=1.32"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{module}"]
"""

MAIN = '''"""{name} 서비스 앱 — `uvicorn {module}.main:app --port {port}`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("{name}")
app.include_router(router)
'''

API = '''"""{name} API (/v1). 이 파일의 엔드포인트가 contracts/{name}.json 이 된다(make contracts)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1")


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="{name}", title="{title}", version="0.1.0")
'''

WORKER = '''"""{name} 워커 — Redis 큐(wm:q:{name}) 소비. `python -m {module}.worker`."""
from __future__ import annotations

from winmate_common.jobs import JobContext, run_worker


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {{"ok": True}}


HANDLERS = {{"noop": _noop}}


def main() -> None:
    run_worker("{name}", HANDLERS)


if __name__ == "__main__":
    main()
'''

TEST = '''from __future__ import annotations

import pytest

from winmate_common import testing


@pytest.fixture
def env(tmp_path):
    with testing.environment(tmp_path, service="{name}"):
        yield


async def test_info(env):
    from {module}.main import app

    async with testing.api_client(app) as c:
        r = await c.get("/v1/info")
        assert r.status_code == 200
        assert r.json()["service"] == "{name}"


async def test_requires_internal_token(env):
    import httpx
    from {module}.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/v1/info")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHENTICATED"
'''

AGENTS = """# {name} 서비스 — 개발 세션 규칙

{title}

- 포트: **{port}** · 게이트웨이 경로: `/api/{name}/v1/...` · 파이썬 모듈: `{module}`
- 고칠 수 있는 경로(owns): {owns}
- 호출할 수 있는 서비스(consumes): {consumes}
{scenario_line}
## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE={name}          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE={name}         # 이 서비스 테스트
make contracts SERVICE={name}    # contracts/{name}.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("{name}", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("{name}")`(data/{name}/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE={name}` 를 돌리고 `contracts/{name}.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태
- 골격만 있음(`GET /v1/info`).
"""


def scaffold(name: str, force: bool = False) -> None:
    reg = yaml.safe_load((ROOT / "config" / "services.yaml").read_text(encoding="utf-8"))["services"]
    if name not in reg:
        sys.exit(f"config/services.yaml 에 {name} 가 없다")
    spec = reg[name]
    module = "winmate_" + name.replace("-", "_")
    base = ROOT / "services" / name
    scenario = SCENARIO.get(name)
    ctx = dict(
        name=name, module=module, port=spec["port"], title=spec.get("title", name),
        owns=", ".join(f"`{p}`" for p in spec.get("owns", [])) or "-",
        consumes=", ".join(f"`{c}`" for c in spec.get("consumes", [])) or "없음",
        scenario_line=(f"- 화면 수용 기준: `docs/scenarios/{scenario}` · 원본 보드: `docs/screens/` (INDEX.md)\n" if scenario else ""),
    )
    files = {
        base / "pyproject.toml": PYPROJECT.format(**ctx),
        base / "src" / module / "__init__.py": f'"""{ctx["title"]}"""\n',
        base / "src" / module / "main.py": MAIN.format(**ctx),
        base / "src" / module / "api.py": API.format(**ctx),
        base / "tests" / "test_basics.py": TEST.format(**ctx),
        base / "AGENTS.md": AGENTS.format(**ctx),
        base / "CLAUDE.md": "@AGENTS.md\n",
    }
    if spec.get("worker"):
        files[base / "src" / module / "worker.py"] = WORKER.format(**ctx)
    for path, content in files.items():
        if path.exists() and not force:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"scaffolded services/{name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    for n in a.names:
        scaffold(n, a.force)
