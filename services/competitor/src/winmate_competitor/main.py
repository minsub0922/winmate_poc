"""competitor 서비스 앱 — `uvicorn winmate_competitor.main:app --port 5104`."""
from __future__ import annotations

from winmate_common.app import create_app

from . import api, api_results

app = create_app("competitor", version="1.0.0")
app.include_router(api.router)
app.include_router(api_results.router)
