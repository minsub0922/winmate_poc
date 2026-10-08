"""vp 서비스 앱 — `uvicorn winmate_vp.main:app --port 5105`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router
from .api_values import router as values_router

app = create_app("vp")
app.include_router(router)
app.include_router(values_router)   # 가치 맵(새 흐름, 2026-10-08) — /v1/value-maps
