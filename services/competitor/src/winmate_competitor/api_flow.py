"""경쟁사 리스트업 API(/v1/ca-flows) — 새 CA 흐름(보드 webapp1 CA2 · CA2_Info · CA2_Pc · CA2_AI · CA_Done). 처리 본체는 caflow.py."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from . import caflow as cf

router = APIRouter(prefix="/v1", tags=["ca-flows"])


@router.get("/ca-flows", response_model=cf.CFList)
async def list_ca_flows(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    """경쟁사 분석(새 흐름) 목록 — 보드 List 의 작성 중 초안."""
    return await cf.list_flows(limit, cursor)


@router.post("/ca-flows", response_model=cf.CFDoc, status_code=201)
async def create_ca_flow(body: cf.CFCreate) -> dict[str, Any]:
    """새 경쟁사 분석 — Storyboard 의 DSS 로 비교 기준을 채운다. 없는 Storyboard 404 · DSS 전이면 422 PREREQUISITE_MISSING."""
    return await cf.create(body)


@router.get("/ca-flows/{flow_id}", response_model=cf.CFDoc)
async def get_ca_flow(flow_id: str) -> dict[str, Any]:
    return cf.to_api(await cf.load(flow_id))


@router.patch("/ca-flows/{flow_id}", response_model=cf.CFDoc)
async def patch_ca_flow(flow_id: str, body: cf.CFPatch) -> dict[str, Any]:
    """제목 고치기(expected_version 이 다르면 409)."""
    return await cf.patch(flow_id, body)


@router.post("/ca-flows/{flow_id}/competitors", response_model=cf.CFDoc, status_code=201)
async def add_competitor(flow_id: str, body: cf.CFCompetitorAdd) -> dict[str, Any]:
    """경쟁사 직접 추가 — 웹 검색 요약에서 기본 정보(위키)를 불러오고, 겹치는 제품군의 DSS 제품으로 비교 쌍을 만든다. 근거 없는 값은 자리표시."""
    return await cf.add_competitor(flow_id, body)


@router.patch("/ca-flows/{flow_id}/competitors/{cid}", response_model=cf.CFDoc)
async def patch_competitor(flow_id: str, cid: str, body: cf.CFCompetitorPatch) -> dict[str, Any]:
    """경쟁사 고치기 — 기본 정보 · 선별 기준 · 장단점 · 주장, AI 후보 목록에 추가(accept)."""
    return await cf.patch_competitor(flow_id, cid, body)


@router.delete("/ca-flows/{flow_id}/competitors/{cid}", response_model=cf.CFDoc)
async def delete_competitor(flow_id: str, cid: str, expected_version: int | None = None) -> dict[str, Any]:
    """경쟁사 빼기(AI 후보 빼기도 이것)."""
    return await cf.delete_competitor(flow_id, cid, expected_version)


@router.post("/ca-flows/{flow_id}/competitors/{cid}/matches", response_model=cf.CFDoc, status_code=201)
async def add_match(flow_id: str, cid: str, body: cf.CFMatchAdd) -> dict[str, Any]:
    """비교 쌍 추가 — 우리 제품은 DSS 제품 · 솔루션(아니면 422 NOT_IN_DSS), 판정은 자료 없음으로 시작."""
    return await cf.add_match(flow_id, cid, body)


@router.patch("/ca-flows/{flow_id}/competitors/{cid}/matches/{mid}", response_model=cf.CFDoc)
async def patch_match(flow_id: str, cid: str, mid: str, body: cf.CFMatchPatch) -> dict[str, Any]:
    """비교 쌍 고치기 — 공간 · 경쟁 제품 · 축별 판정(ours-better · similar · ours-worse · no-data)과 메모."""
    return await cf.patch_match(flow_id, cid, mid, body)


@router.delete("/ca-flows/{flow_id}/competitors/{cid}/matches/{mid}", response_model=cf.CFDoc)
async def delete_match(flow_id: str, cid: str, mid: str, expected_version: int | None = None) -> dict[str, Any]:
    return await cf.delete_match(flow_id, cid, mid, expected_version)


@router.post("/ca-flows/{flow_id}:candidates", response_model=cf.CFCandidatesResult)
async def suggest_candidates(flow_id: str) -> dict[str, Any]:
    """AI 경쟁사 후보군 웹 탐색 — 웹 검색 요약에 이름 · 근거 구절이 있는 후보만 점선(ai-pending)으로. 웹 · 모델이 안 되면 mode=none · 후보 0."""
    return await cf.suggest_candidates(flow_id)


@router.post("/ca-flows/{flow_id}:finish", response_model=cf.CFStageOut)
async def finish(flow_id: str) -> dict[str, Any]:
    """저장 — status=done, Storyboard flow.json stages.ca · 요약 md · 팝업 카드 반영(push_stage). 경쟁사 0이면 422 NO_COMPETITORS."""
    return await cf.finish(flow_id)


@router.get("/ca-flows/{flow_id}/stage", response_model=cf.CFStageOut)
async def get_stage(flow_id: str) -> dict[str, Any]:
    return await cf.get_stage(flow_id)
