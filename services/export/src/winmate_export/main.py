"""export 서비스 앱 — `uvicorn winmate_export.main:app --port 5060`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("export")
app.include_router(router)
