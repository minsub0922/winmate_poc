"""새 MI 흐름 API `/v1/mi-flows*`(웹앱 ① v58 — 보드 MI2_Loading · MI2 · MI3 · MI_Done). 본체는 `miflow.py`, 잡은 `graphs/flow.py`.

| 경로 | 하는 일 |
|---|---|
| `POST /v1/mi-flows` | Storyboard(최소 DSS)로 만들기 → 바로 Storyboard 분석 잡(mi.flow_analyze). 없으면 404 · DSS 전이면 422 PREREQUISITE_MISSING. 같은 Storyboard 의 저장 전 초안이 있으면 그 초안(200) |
| `GET /v1/mi-flows` · `GET /v1/mi-flows/{id}` | 목록(초안) · 문서(진행 `progress.steps` 포함 — 화면이 폴링) |
| `DELETE /v1/mi-flows/{id}` | 저장 전 초안 지우기(204 · 잡 취소 · 색인 지움). 저장한 MI 는 409 SAVED_CONTENT |
| `PATCH /v1/mi-flows/{id}` | 검색어 · 조건 · 기존 판 유지 · 단계(검색어 고치기) — expected_version 이 다르면 409 |
| `POST /v1/mi-flows/{id}:analyze` | Storyboard 다시 분석(저장한 MI 를 고칠 때) |
| `POST /v1/mi-flows/{id}:search` | 웹 검색 잡(mi.flow_search) → 정제 |
| `PATCH /v1/mi-flows/{id}/items/{item_id}` | 담기 · 빼기 · 문장 고치기 |
| `POST /v1/mi-flows/{id}:finish` | 저장 → Storyboard stages.mi · 요약본 |
| `GET /v1/mi-flows/{id}/stage` | 지금 값으로 만든 stages.mi 미리 보기 |
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Response

from . import miflow as F
from .miflow import MFCreate, MFDoc, MFItemPatch, MFList, MFPatch, MFStageOut

router = APIRouter(prefix="/v1", tags=["mi-flows"])


@router.post("/mi-flows", response_model=MFDoc, status_code=201,
             responses={200: {"model": MFDoc, "description": "이 Storyboard 의 저장 전 초안이 이미 있음 — 그 초안(새로 만들지 않고 분석도 다시 돌리지 않음)"}})
async def create_mi_flow(body: MFCreate, response: Response) -> dict[str, Any]:
    """Gate 에서 고른 Storyboard 로 MI 를 만들고 Storyboard 분석을 시작한다(CF-08 예외 — MI 는 분석 로딩이 먼저).
    같은 Storyboard 의 저장 전 초안이 있으면 그것을 200 으로 돌려준다(「‹ Storyboard」 → Gate → 다시 시작해도 초안이 늘지 않음)."""
    doc, created = await F.create(body)
    if not created:
        response.status_code = 200
    return doc


@router.get("/mi-flows", response_model=MFList)
async def list_mi_flows(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    return await F.list_flows(limit, cursor)


@router.get("/mi-flows/{flow_id}", response_model=MFDoc)
async def get_mi_flow(flow_id: str) -> dict[str, Any]:
    return F.to_api(await F.load(flow_id))


@router.delete("/mi-flows/{flow_id}", status_code=204, response_class=Response)
async def delete_mi_flow(flow_id: str, expected_version: int | None = Query(None, description="주면 지금 판과 다를 때 409 CONFLICT")) -> Response:
    """저장 전 초안 지우기(목록 줄 ×, 소프트 삭제 · 작업물 색인도 지움 · 돌고 있는 분석/검색 잡 취소) — 한 번도 저장하지 않은 것만.
    저장한 MI 는 Storyboard 에 연결돼 있어 409 SAVED_CONTENT, 없으면 404 NOT_FOUND."""
    await F.delete(flow_id, expected_version)
    return Response(status_code=204)


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
