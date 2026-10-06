"""birdseye 서비스 앱 — `uvicorn winmate_birdseye.main:app --port 5108`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("birdseye")
app.include_router(router)
