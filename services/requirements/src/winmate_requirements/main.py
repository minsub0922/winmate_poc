"""requirements 서비스 앱 — `uvicorn winmate_requirements.main:app --port 5101`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router
from .api_flow import router as flow_router

app = create_app("requirements")
app.include_router(router)
app.include_router(flow_router)   # 새 콘텐츠 흐름(2026-10-08) — /v1/rq-flows
