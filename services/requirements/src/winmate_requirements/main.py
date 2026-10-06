"""requirements 서비스 앱 — `uvicorn winmate_requirements.main:app --port 5101`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("requirements")
app.include_router(router)
