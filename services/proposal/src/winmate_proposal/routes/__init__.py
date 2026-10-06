"""proposal API 라우터 — 영역별(§6.2–§6.13). main.py 가 모두 붙인다."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from . import compose, confirm, design, exports, imports, oneclick, proposals, reuse, review, sections, start, versions

meta = APIRouter(prefix="/v1")


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


@meta.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="proposal", title="B2B 제안서 — 시작 방식 · 섹션 작성 · 템플릿 · 딸깍 · 검토/승인 · 버전 · 기존 제안서 활용",
                       version="0.2.0")


ROUTERS = [meta, proposals.router, start.router, compose.router, sections.router, imports.router, oneclick.router, design.router,
           confirm.router, review.router, versions.router, exports.router, reuse.router]
