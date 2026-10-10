"""새 MI 흐름 API `/v1/mi-flows*`(웹앱 ① v58 — 보드 MI2_Loading · MI2 · MI3 · MI_Done). 본체는 `miflow.py`, 잡은 `graphs/flow.py`.

| 경로 | 하는 일 |
|---|---|
| `POST /v1/mi-flows` | Storyboard(최소 DSS)로 만들기 → 바로 Storyboard 분석 잡(mi.flow_analyze). 없으면 404 · DSS 전이면 422 PREREQUISITE_MISSING |
| `GET /v1/mi-flows` · `GET /v1/mi-flows/{id}` | 목록(초안) · 문서(진행 `progress.steps` 포함 — 화면이 폴링) |
| `PATCH /v1/mi-flows/{id}` | 검색어 · 조건 · 기존 판 유지 · 단계(검색어 고치기) — expected_version 이 다르면 409 |
| `POST /v1/mi-flows/{id}:analyze` | Storyboard 다시 분석(저장한 MI 를 고칠 때) |
| `POST /v1/mi-flows/{id}:search` | 웹 검색 잡(mi.flow_search) → 정제 |
| `PATCH /v1/mi-flows/{id}/items/{item_id}` | 담기 · 빼기 · 문장 고치기 |
| `POST /v1/mi-flows/{id}:finish` | 저장 → Storyboard stages.mi · 요약본 |
| `GET /v1/mi-flows/{id}/stage` | 지금 값으로 만든 stages.mi 미리 보기 |
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from . import miflow as F
from .miflow import MFCreate, MFDoc, MFItemPatch, MFList, MFPatch, MFStageOut

router = APIRouter(prefix="/v1", tags=["mi-flows"])


@router.post("/mi-flows", response_model=MFDoc, status_code=201)
async def create_mi_flow(body: MFCreate) -> dict[str, Any]:
    """Gate 에서 고른 Storyboard 로 MI 를 만들고 Storyboard 분석을 시작한다(CF-08 예외 — MI 는 분석 로딩이 먼저)."""
    return await F.create(body)


@router.get("/mi-flows", response_model=MFList)
async def list_mi_flows(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    return await F.list_flows(limit, cursor)


@router.get("/mi-flows/{flow_id}", response_model=MFDoc)
async def get_mi_flow(flow_id: str) -> dict[str, Any]:
    return F.to_api(await F.load(flow_id))


@router.patch("/mi-flows/{flow_id}", response_model=MFDoc)
async def patch_mi_flow(flow_id: str, body: MFPatch) -> dict[str, Any]:
    return await F.patch(flow_id, body)


@router.post("/mi-flows/{flow_id}:analyze", response_model=MFDoc)
async def analyze_mi_flow(flow_id: str) -> dict[str, Any]:
    return await F.analyze(flow_id)


@router.post("/mi-flows/{flow_id}:search", response_model=MFDoc)
async def search_mi_flow(flow_id: str) -> dict[str, Any]:
    return await F.start_search(flow_id)


@router.patch("/mi-flows/{flow_id}/items/{item_id}", response_model=MFDoc)
async def patch_mi_flow_item(flow_id: str, item_id: str, body: MFItemPatch) -> dict[str, Any]:
    return await F.patch_item(flow_id, item_id, body)


@router.post("/mi-flows/{flow_id}:finish", response_model=MFStageOut)
async def finish_mi_flow(flow_id: str) -> dict[str, Any]:
    return await F.finish(flow_id)


@router.get("/mi-flows/{flow_id}/stage", response_model=MFStageOut)
async def get_mi_flow_stage(flow_id: str) -> dict[str, Any]:
    return await F.get_stage(flow_id)
