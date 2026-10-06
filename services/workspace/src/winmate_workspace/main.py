"""workspace 서비스 앱 — `uvicorn winmate_workspace.main:app --port 5050`."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from winmate_common.app import create_app

from .api import bootstrap_admin, router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    bootstrap_admin()
    yield


app = create_app("workspace", lifespan=lifespan)
app.include_router(router)
