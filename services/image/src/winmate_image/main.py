"""image 서비스 앱 — `uvicorn winmate_image.main:app --port 5107`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("image")
app.include_router(router)
