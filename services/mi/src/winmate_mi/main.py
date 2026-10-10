"""mi 서비스 앱 — `uvicorn winmate_mi.main:app --port 5103`."""
from __future__ import annotations

from winmate_common.app import create_app

from .api import router
from .api_flow import router as flow_router
from .api_more import router as more_router
from .api_results import router as results_router

app = create_app("mi")
app.include_router(router)
app.include_router(results_router)
app.include_router(more_router)
app.include_router(flow_router)
