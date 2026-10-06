"""spec 서비스 앱 — `uvicorn winmate_spec.main:app --port 5106`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router

app = create_app("spec")
app.include_router(router)
