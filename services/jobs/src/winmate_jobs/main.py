"""jobs 서비스 앱 — `uvicorn winmate_jobs.main:app --port 5040`."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from winmate_common.app import create_app
from winmate_common.jobs import redis

from .api import router, scheduler_loop


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    stop = asyncio.Event()
    task = None
    if os.environ.get("WINMATE_CONTRACT_EXPORT") != "1" and os.environ.get("JOBS_SCHEDULER", "1") != "0":
        task = asyncio.create_task(scheduler_loop(stop))
    yield
    stop.set()
    if task:
        await asyncio.wait([task], timeout=5)


async def _redis_check() -> dict:
    try:
        await redis().ping()
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


app = create_app("jobs", lifespan=lifespan, health_checks={"redis": _redis_check})
app.include_router(router)
