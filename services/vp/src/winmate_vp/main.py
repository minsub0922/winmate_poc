"""vp 서비스 앱 — `uvicorn winmate_vp.main:app --port 5105`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("vp")
app.include_router(router)
