"""ai-tools 테스트 공통 — 네트워크 없이(MODEL_MODE=mock 기본), `.env` 값이 새어 들지 않게 모든 키를 기본값으로 고정한다."""
from __future__ import annotations

import base64
import io
import itertools
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from fastapi import Request, Response
from PIL import Image

from winmate_common import testing

# .env.example 과 같은 기본값(테스트는 여기서 출발해 필요한 것만 바꾼다)
AI_ENV: dict[str, str] = {
    "GEMINI_API_KEY": "", "GEMINI_BASE_URL": "https://generativelanguage.googleapis.com", "GEMINI_THINKING_LEVEL": "low",
    "MODEL_MODE": "mock", "LIVE_TESTS": "0", "REPLAY_FALLBACK": "",
    "LLM_PROVIDER": "gemini", "LLM_BASE_URL": "", "LLM_API_KEY": "", "LLM_MODEL": "gemini-3.1-flash-lite",
    "LLM_MAX_INPUT_TOKENS": "32000", "LLM_MAX_OUTPUT_TOKENS": "4096", "LLM_TEMPERATURE": "0.2",
    "LLM_SUPPORTS_JSON_SCHEMA": "true", "LLM_SUPPORTS_TOOLS": "true", "LLM_SUPPORTS_STREAMING": "true",
    "LLM_TIMEOUT_S": "90", "LLM_MAX_CONCURRENCY": "4", "LLM_RPM": "30", "LLM_DAILY_LIMIT": "2000",
    "I2T_PROVIDER": "gemini", "I2T_BASE_URL": "", "I2T_API_KEY": "", "I2T_MODEL": "gemini-3.1-flash-lite",
    "I2T_MAX_IMAGES_PER_CALL": "4", "I2T_MAX_IMAGE_SIDE_PX": "1536", "I2T_SUPPORTS_JSON_SCHEMA": "true",
    "I2T_SUPPORTS_BBOX": "true", "I2T_TIMEOUT_S": "90", "I2T_MAX_CONCURRENCY": "4", "I2T_RPM": "30", "I2T_DAILY_LIMIT": "3000",
    "I2T_BBOX_FORMAT": "",
    "T2I_PROVIDER": "gemini", "T2I_BASE_URL": "", "T2I_API_KEY": "", "T2I_MODEL": "gemini-3.1-flash-lite-image",
    "T2I_DEFAULT_ASPECT": "16:9", "T2I_MAX_SIDE_PX": "1024", "T2I_SUPPORTS_REFERENCE_IMAGES": "true",
    "T2I_MAX_REFERENCE_IMAGES": "4", "T2I_SUPPORTS_EDIT": "true", "T2I_SUPPORTS_MASK": "false", "T2I_IMAGES_PER_CALL": "1",
    "T2I_TIMEOUT_S": "120", "T2I_MAX_CONCURRENCY": "2", "T2I_DAILY_LIMIT": "100", "T2I_RPM": "",
    "T2I_RESPONSE_FORMAT": "", "T2I_SIZE": "",
    "WEBSEARCH_PROVIDER": "gemini_grounding", "WEBSEARCH_BASE_URL": "", "WEBSEARCH_API_KEY": "",
    "WEBSEARCH_MODEL": "gemini-3.5-flash-lite", "WEBSEARCH_RETURN_SOURCES": "false", "WEBSEARCH_TIMEOUT_S": "60",
    "WEBSEARCH_DAILY_LIMIT": "150", "WEBSEARCH_RPM": "", "WEBSEARCH_MAX_CONCURRENCY": "",
    "SEARCH_API_PROVIDER": "none", "SEARCH_API_BASE_URL": "", "SEARCH_API_KEY": "", "SEARCH_API_CX": "",
    "WEB_FETCH_ENABLED": "true", "WEB_FETCH_USER_AGENT": "WinmateBot/0.1", "WEB_FETCH_RESPECT_ROBOTS": "true",
    "WEB_FETCH_RATE_LIMIT_RPS": "0.5", "WEB_FETCH_TIMEOUT_S": "20", "WEB_FETCH_CACHE_TTL_HOURS": "168",
    "WEB_FETCH_ALLOWED_DOMAINS": "", "WEB_FETCH_MAX_BYTES": "",
    "EMBEDDING_PROVIDER": "lsa", "EMBEDDING_MODEL": "BAAI/bge-m3", "EMBEDDING_MODEL_PATH": "./models/bge-m3",
    "EMBEDDING_BASE_URL": "", "EMBEDDING_API_KEY": "", "EMBEDDING_DIM": "", "RERANKER_PROVIDER": "none",
    "LOCAL_MODEL_DEVICE": "cpu", "HF_HUB_OFFLINE": "0",
    "LLM_ALLOW_CONFIDENTIAL": "false", "I2T_ALLOW_CONFIDENTIAL": "false", "T2I_ALLOW_CONFIDENTIAL": "false",
    "WEBSEARCH_ALLOW_CONFIDENTIAL": "false", "MODEL_CALL_LOG": "full", "MODEL_CALL_LOG_RETENTION_DAYS": "30",
    # 기본은 mock 에서 기밀을 막지 않지만, 이 서비스 테스트는 차단 경로를 mock 으로 시험한다
    "MOCK_ENFORCE_CONFIDENTIAL": "true",
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """임시 DATA_DIR · mock 모드 · 계약 검증 끔(files 계약이 아직 없어도 스텁으로 테스트) · 모든 ai-tools 키 고정."""
    from winmate_ai_tools import fixtures, providers, runtime

    with testing.environment(tmp_path, service="ai-tools", CONTRACT_VALIDATION="off"):
        for k, v in AI_ENV.items():
            monkeypatch.setenv(k, v)
        monkeypatch.setenv("MODEL_CASSETTE_DIR", str(tmp_path / "cassettes"))
        monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
        mocks = tmp_path / "mocks"
        mocks.mkdir()
        monkeypatch.setenv("AI_TOOLS_MOCKS_DIR", str(mocks))
        monkeypatch.setattr(runtime, "RETRY_BASE_S", 0.0)
        fixtures.reset()
        providers.reset()
        yield tmp_path
        providers.reset()


@pytest.fixture
def mocks_dir(env) -> Path:
    return env / "mocks"


def write_fixture(mocks: Path, task: str, data: Any) -> None:
    (mocks / f"{task}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ── files 서비스 스텁 ───────────────────────────────────────

class FilesStub:
    """POST /v1/files/bytes · GET /v1/files/{id}/content 만 흉내 낸다."""

    def __init__(self) -> None:
        self.files: dict[str, dict[str, Any]] = {}
        self._ids = itertools.count(1)
        self.app = testing.stub_app("files")

        @self.app.post("/v1/files/bytes")
        async def save(request: Request) -> dict[str, Any]:
            body = await request.json()
            fid = f"file_{next(self._ids):04d}"
            data = base64.b64decode(body["data_b64"])
            self.files[fid] = {"data": data, "mime": body.get("mime"), "name": body.get("name"),
                               "meta": body.get("meta") or {}, "source": body.get("source"),
                               "confidential": body.get("confidential")}
            return {"id": fid, "name": body.get("name"), "mime": body.get("mime"), "size": len(data)}

        @self.app.get("/v1/files/{file_id}/content")
        async def content(file_id: str) -> Response:
            f = self.files.get(file_id)
            if f is None:
                return Response(json.dumps({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}),
                                status_code=404, media_type="application/json")
            return Response(f["data"], media_type=f["mime"] or "application/octet-stream")

    def add(self, data: bytes, mime: str = "image/png") -> str:
        fid = f"file_{next(self._ids):04d}"
        self.files[fid] = {"data": data, "mime": mime, "name": fid, "meta": {}}
        return fid


@pytest.fixture
def files(env):
    stub = FilesStub()
    with testing.inprocess({"files": stub.app}):
        yield stub


# ── 이미지 도우미 ───────────────────────────────────────────

def png_bytes(size: tuple[int, int] = (64, 48), color: tuple[int, int, int] = (200, 30, 30), mode: str = "RGB") -> bytes:
    im = Image.new(mode, size, color if mode != "RGBA" else (*color, 255))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def noise_png(size: tuple[int, int], seed: int = 1) -> bytes:
    import numpy as np

    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(size[1], size[0], 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return buf.getvalue()


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


@pytest.fixture
async def client(env):
    from winmate_ai_tools.main import app

    async with testing.api_client(app) as c:
        yield c


@pytest.fixture
def h():
    """테스트 도우미 묶음(importlib 모드라 conftest 를 직접 import 할 수 없어서 fixture 로 넘긴다)."""
    import types

    return types.SimpleNamespace(write_fixture=write_fixture, png_bytes=png_bytes, noise_png=noise_png, b64=b64,
                                 FilesStub=FilesStub, AI_ENV=AI_ENV)


# ── Gemini REST 흉내(respx) — 실제 google-genai SDK 가 보내는 요청을 받는다 ─────────────

GEMINI_URL = r"https://gemini\.test/v1beta/models/(?P<model>[^:]+):(?P<op>generateContent|streamGenerateContent)"


class Gemini:
    """respx 라우트: 요청을 모으고 차례로 정해 둔 응답을 돌려준다."""

    def __init__(self, router: respx.Router):
        self.requests: list[dict[str, Any]] = []
        self.urls: list[str] = []
        self.headers: list[httpx.Headers] = []
        self.queue: list[httpx.Response] = []
        router.post(url__regex=GEMINI_URL).mock(side_effect=self._handle)

    def _handle(self, request: httpx.Request, **_: Any) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        self.urls.append(str(request.url))
        self.headers.append(request.headers)
        return self.queue.pop(0)

    def reply(self, body: dict[str, Any] | None = None, *, status: int = 200) -> None:
        if status >= 400:
            self.queue.append(httpx.Response(status, json={"error": {"code": status, "message": "upstream says no", "status": "X"}}))
        else:
            self.queue.append(httpx.Response(200, json=body))

    def reply_stream(self, chunks: list[dict[str, Any]]) -> None:
        text = "".join(f"data: {json.dumps(c, ensure_ascii=False)}\r\n\r\n" for c in chunks)
        self.queue.append(httpx.Response(200, text=text, headers={"content-type": "text/event-stream"}))


@pytest.fixture
def gem(env, monkeypatch):
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_BASE_URL", "https://gemini.test")
    with respx.mock(assert_all_called=False) as router:
        yield Gemini(router)
