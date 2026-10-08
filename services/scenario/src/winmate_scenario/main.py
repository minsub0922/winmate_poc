"""scenario 서비스 앱 — `uvicorn winmate_scenario.main:app --port 5109`."""
from __future__ import annotations

from winmate_common.app import create_app

from . import api, api_flow, api_scenes, api_send, api_spaces

app = create_app("scenario", version="0.2.0")
app.include_router(api.router)
app.include_router(api_flow.router)
app.include_router(api_scenes.router)
app.include_router(api_send.router)
app.include_router(api_spaces.router)   # 공간 → 시나리오 → 장면(새 흐름, 2026-10-08)
