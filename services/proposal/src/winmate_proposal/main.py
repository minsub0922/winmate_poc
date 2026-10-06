"""proposal 서비스 앱 — `uvicorn winmate_proposal.main:app --port 5110`."""
from __future__ import annotations

from winmate_common.app import create_app

from .routes import ROUTERS

app = create_app("proposal", version="0.2.0",
                 description="B2B 제안서(PR) — 시작 방식 · 섹션 작성 · 템플릿 · 딸깍 · 검토/승인 · 버전 · 기존 제안서 활용(PRU). 10-proposal.md §6")
for _r in ROUTERS:
    app.include_router(_r)
