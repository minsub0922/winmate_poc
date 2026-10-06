"""spec API (/v1). 이 파일이 묶는 엔드포인트가 contracts/spec.json 이 된다(make contracts)."""
from __future__ import annotations

from fastapi import APIRouter

from .models import ServiceInfo
from .routes import compliance, edit, find, generate, handoff, sheets, warnings

router = APIRouter()
meta = APIRouter(prefix="/v1")


@meta.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="spec", title="Spec 시트 — 조건으로 모델 찾기 · 고객 스펙 대응표 · 단종·불일치 경고 · 단위 변환", version="1.0.0")


router.include_router(meta)
for r in (sheets.router, find.router, compliance.router, generate.router, edit.router, warnings.router, handoff.router):
    router.include_router(r)
