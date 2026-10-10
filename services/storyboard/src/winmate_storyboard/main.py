"""storyboard 서비스 앱 — `uvicorn winmate_storyboard.main:app --port 5102`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router
from .api_flows import router as flows_router

app = create_app("storyboard")
app.include_router(router)
app.include_router(flows_router)
