"""모델 호출(ai-tools 경유, task = `be.<동작>`) — 제한 시간 · 일시 오류 재시도 · 오류 구분(08-birdseye §7.1 · §7.2).

- 고객 도면 · 현장 사진 · 고객 설명이 든 호출은 `confidential=True`.
- 403 `POLICY_CONFIDENTIAL` → `ModelBlocked`(호출한 쪽이 §7.2 로컬 대체 경로로 내려간다. 다른 모델로 몰래 바꾸지 않는다).
- 502 · 503 · 504 · 429 · 연결 오류 → 다시(BE_RETRY_DELAYS, 기본 2초 · 6초). 그래도 안 되면 `ModelFailed`.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel

from winmate_common.ai import ai
from winmate_common.errors import ApiError

from . import config

log = logging.getLogger("winmate.birdseye.llm")
T = TypeVar("T")


class ModelBlocked(Exception):
    """ai-tools 가 기밀 전송을 막았다(403 POLICY_CONFIDENTIAL)."""


class ModelFailed(Exception):
    def __init__(self, code: str, message: str, status: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


TRANSIENT = {502, 503, 504}


def classify(exc: Exception) -> Exception:
    if isinstance(exc, ApiError):
        if exc.code == "POLICY_CONFIDENTIAL" or (exc.status == 403 and "CONFIDENTIAL" in exc.code):
            return ModelBlocked(exc.message)
        return ModelFailed(exc.code, exc.message, exc.status)
    if isinstance(exc, asyncio.TimeoutError):
        return ModelFailed("TIMEOUT", "모델 응답이 늦어 기본 규칙으로 처리했어요", 504)
    return exc


def _transient(exc: Exception) -> bool:
    if isinstance(exc, ApiError):
        return exc.status in TRANSIENT or exc.code == "RATE_LIMITED"
    return isinstance(exc, (OSError,)) or type(exc).__name__ in ("ConnectError", "ReadTimeout", "RemoteProtocolError")


async def call(fn: Callable[[], Awaitable[T]], *, retries: bool = True, timeout: float | None = None) -> T:
    delays = config.retry_delays() if retries else []
    attempt = 0
    while True:
        try:
            if timeout:
                return await asyncio.wait_for(fn(), timeout)
            return await fn()
        except Exception as exc:  # noqa: BLE001
            if _transient(exc) and attempt < len(delays):
                await asyncio.sleep(delays[attempt])
                attempt += 1
                continue
            raise classify(exc) from exc


async def json_task(task: str, prompt: str, schema: type[BaseModel] | dict[str, Any], *, system: str | None = None,
                    confidential: bool = False, timeout: float | None = None) -> dict[str, Any] | None:
    """LLM JSON — 실패(시간 초과 · 스키마 · 제공자)면 None. 기밀 차단은 ModelBlocked 로 올린다."""
    async def run() -> dict[str, Any]:
        res = await ai().json(task, prompt, schema if isinstance(schema, dict) else schema.model_json_schema(), system=system,
                              confidential=confidential)
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            return schema.model_validate(res or {}).model_dump()
        return res or {}

    try:
        return await call(run, timeout=timeout or config.llm_timeout_s())
    except ModelBlocked:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("%s 실패 → 대체 경로: %s", task, exc)
        return None


async def vision_task(task: str, images: list[Any], prompt: str, schema: type[BaseModel] | dict[str, Any] | None = None, *,
                      want_bbox: bool = False, confidential: bool = True, timeout: float | None = None) -> dict[str, Any] | None:
    """I2T — {json, boxes, content}. 실패면 None, 기밀 차단은 ModelBlocked."""
    async def run() -> dict[str, Any]:
        return await ai().vision(task, images, prompt, schema=schema, want_bbox=want_bbox, confidential=confidential)

    try:
        res = await call(run, timeout=timeout or config.llm_timeout_s())
    except ModelBlocked:
        raise
    except Exception as exc:  # noqa: BLE001
        log.warning("%s 실패 → 대체 경로: %s", task, exc)
        return None
    data = res.get("json")
    if isinstance(schema, type) and issubclass(schema, BaseModel) and isinstance(data, dict):
        try:
            res["json"] = schema.model_validate(data).model_dump()
        except Exception:  # noqa: BLE001
            res["json"] = None
    return res


async def caps() -> dict[str, Any]:
    """ai-tools 능력(30초 캐시) — 실패하면 빈 dict."""
    try:
        return await ai().capabilities()
    except Exception as exc:  # noqa: BLE001
        log.warning("capabilities 실패: %s", exc)
        return {}
