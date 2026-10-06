"""ai-tools 서비스 앱 — `uvicorn winmate_ai_tools.main:app --port 5010`."""
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from winmate_common.app import create_app
from winmate_common.jobs import redis

from . import calllog, config
from .api import router

log = logging.getLogger("winmate.ai_tools")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        n = await asyncio.to_thread(calllog.store().prune, config.call_log_retention_days())
        if n:
            log.info("호출 로그 %d줄 정리(보관 %d일)", n, config.call_log_retention_days())
    except Exception as exc:  # noqa: BLE001
        log.warning("호출 로그 정리 실패: %s", exc)
    llm = config.load("llm")
    log.info("MODEL_MODE=%s · LLM=%s/%s · I2T=%s · T2I=%s · WEBSEARCH=%s", config.model_mode(), llm.provider, llm.model,
             config.load("i2t").provider, config.load("t2i").provider, config.load("websearch").provider)
    yield


async def _health() -> dict[str, Any]:
    mode = config.model_mode()
    out: dict[str, Any] = {"ok": True, "mode": mode,
                           "providers": {c: config.load(c).provider for c in config.CAPS}}
    if mode in ("live", "record"):
        try:
            await asyncio.wait_for(redis().ping(), timeout=2.0)
            out["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001 — 한도 카운터 없이도 호출은 된다
            out["redis"] = f"unavailable: {type(exc).__name__}"
            out["ok"] = False
    return out


app = create_app("ai-tools", version="0.2.0", lifespan=lifespan, health_checks={"ai": _health})
app.include_router(router)
