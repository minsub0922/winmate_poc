"""storyboard 서비스 앱 — `uvicorn winmate_storyboard.main:app --port 5102`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("storyboard")
app.include_router(router)
