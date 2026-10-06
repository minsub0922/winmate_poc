"""kb 서비스 앱 — `uvicorn winmate_kb.main:app --port 5020`.

시작할 때 지식 DB 를 열고(읽기 전용) 무거운 캐시(LSA 모델 · 벡터 · 메시지 벡터 · 썸네일 색인)를 백그라운드에서 데운다.
테스트(httpx ASGITransport)는 lifespan 을 돌리지 않으므로 첫 요청 때 필요한 것만 만든다(engine · index 는 지연 생성).
"""
from __future__ import annotations

import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from winmate_common.app import create_app

from . import config
from .api import router
from .patterns import router as patterns_router

log = logging.getLogger("winmate.kb")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if config.warmup_enabled():
        def _warm() -> None:
            try:
                from .engine import engine

                engine().warmup()
            except Exception:  # noqa: BLE001 — 데우기 실패는 요청 때 다시 시도
                log.exception("kb warmup thread failed")

        threading.Thread(target=_warm, name="kb-warmup", daemon=True).start()
    yield


def _health() -> dict[str, Any]:
    from .engine import _engine

    db = config.db_path()
    out: dict[str, Any] = {"ok": db.is_file(), "db": str(db)}
    if _engine is not None:
        out.update({"warm": _engine.warm, "warm_seconds": _engine.warm_seconds, "warm_error": _engine.warm_error})
    return out


app = create_app("kb", lifespan=lifespan, health_checks={"kb": _health})
app.include_router(router)
app.include_router(patterns_router)
