"""Spec 시트 새 흐름(보드 webapp1 SP0 · SP1 · SP2 · SP_Done) — `/v1/spec-flows*`. 본체: spec_flow.py."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Response

from .. import spec_flow as F
from ..spec_flow import SFCreate, SFDoc, SFList, SFModelOptions, SFPatch, SFRowPatch, SFStageOut

router = APIRouter(prefix="/v1", tags=["spec-flows"])


@router.get("/spec-flows", response_model=SFList)
async def list_spec_flows(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    """새 흐름 Spec 시트 목록(보드 SP0 의 작성 중 초안)."""
    return await F.list_flows(limit, cursor)


@router.post("/spec-flows", response_model=SFDoc, status_code=201,
             responses={200: {"model": SFDoc, "description": "같은 Storyboard 의 저장 전 초안이 이미 있으면 그 초안(새로 만들지 않음)"}})
async def create_spec_flow(body: SFCreate, response: Response) -> dict[str, Any]:
    """Storyboard(DSS 까지 된 것)의 DSS 제품으로 시트를 만든다 — 행마다 KB 모델을 맞추고 카탈로그 값을 채운다.
    같은 Storyboard 의 저장 전 초안이 있으면 그것을 200 으로 돌려준다(Gate 에서 다시 시작해도 초안이 둘이 되지 않게).
    Storyboard 가 없으면 404 `STORYBOARD_NOT_FOUND`, DSS 가 없으면 422 `PREREQUISITE_MISSING`."""
    doc, created = await F.create(body)
    if not created:
        response.status_code = 200
    return doc


@router.get("/spec-flows/{flow_id}", response_model=SFDoc)
async def get_spec_flow(flow_id: str) -> dict[str, Any]:
    """시트 하나 + `dss_changed`(Storyboard 의 DSS 가 시트를 만든 뒤 바뀌었으면 그 차이, 아니면 null)."""
    return await F.get_with_status(flow_id)


@router.delete("/spec-flows/{flow_id}", status_code=204)
async def delete_spec_flow(flow_id: str) -> Response:
    """저장 전 초안 지우기(workspace 색인도 지운다). 한 번이라도 저장한 시트는 Storyboard 에 연결돼 있어 409 `SAVED_CONTENT`."""
    await F.delete(flow_id)
    return Response(status_code=204)


@router.patch("/spec-flows/{flow_id}", response_model=SFDoc)
async def patch_spec_flow(flow_id: str, body: SFPatch) -> dict[str, Any]:
    """형식(비교표 · 제품별 1장) · 항목 칩 · 표기(한국어 · mm / 영문 · inch) · 제목. expected_version 이 다르면 409."""
    return await F.patch(flow_id, body)


@router.post("/spec-flows/{flow_id}:resync-dss", response_model=SFDoc)
async def resync_spec_flow_dss(flow_id: str) -> dict[str, Any]:
    """DSS 다시 가져오기 — 허브의 지금 stages.dss 로 행을 맞춘다(새 제품은 행 추가 · 빠진 제품은 남기고 경고 「DSS에서 빠짐」 ·
    수량은 사람이 고치지 않은 행만). 결과는 `last_resync`. Storyboard 없음 404 · DSS 없음 422."""
    return await F.resync(flow_id)


@router.patch("/spec-flows/{flow_id}/rows/{row_key}", response_model=SFDoc)
async def patch_spec_flow_row(flow_id: str, row_key: str, body: SFRowPatch) -> dict[str, Any]:
    """행 넣기 · 빼기 · 수량 · 다른 모델 고르기(카탈로그에 없는 모델이면 422 `MODEL_NOT_IN_CATALOG`) · 모델 비우기."""
    return await F.patch_row(flow_id, row_key, body)


@router.delete("/spec-flows/{flow_id}/rows/{row_key}", response_model=SFDoc)
async def delete_spec_flow_row(flow_id: str, row_key: str) -> dict[str, Any]:
    """DSS 에서 빠진 행 지우기(경고 「DSS에서 빠짐」). DSS 에 있는 제품 행이면 422 `ROW_IN_DSS`(체크를 빼서 시트에서 뺀다)."""
    return await F.delete_row(flow_id, row_key)


@router.get("/spec-flows/{flow_id}/rows/{row_key}/models", response_model=SFModelOptions)
async def spec_flow_row_models(flow_id: str, row_key: str, q: str | None = Query(None, max_length=80)) -> dict[str, Any]:
    """이 행에 고를 수 있는 모델 — q 가 없으면 같은 제품군 모델, 있으면 카탈로그 검색."""
    return await F.model_options(flow_id, row_key, q)


@router.post("/spec-flows/{flow_id}:finish", response_model=SFStageOut)
async def finish_spec_flow(flow_id: str) -> dict[str, Any]:
    """저장(시트 만들기) → Storyboard flow.json stages.sp · 요약본 · 팝업 카드. 넣은 제품이 없으면 422 `NO_MODELS`, 항목이 없으면 422 `NO_COLUMNS`."""
    return await F.finish(flow_id)


@router.get("/spec-flows/{flow_id}/stage", response_model=SFStageOut)
async def spec_flow_stage(flow_id: str) -> dict[str, Any]:
    """지금 값으로 만든 stages.sp(저장하지 않음)."""
    return await F.get_stage(flow_id)
