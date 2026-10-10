"""dss 서비스 앱 — `uvicorn winmate_dss.main:app --port 5111`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("dss")
app.include_router(router)
