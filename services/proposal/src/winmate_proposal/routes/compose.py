"""§6.4 유형(PR2) · 시트 구성(PR3) · 업종 레이아웃(PR3I)."""
from __future__ import annotations

from fastapi import APIRouter

from .. import models as M
from ..ops import compose as C

router = APIRouter(prefix="/v1", tags=["compose"])


@router.get("/proposals/{proposal_id}/type-options", response_model=M.TypeOptions)
async def type_options(proposal_id: str) -> M.TypeOptions:
    return await C.type_options(proposal_id)


@router.put("/proposals/{proposal_id}/type", response_model=M.Proposal)
async def put_type(proposal_id: str, body: M.TypePut) -> M.Proposal:
    return await C.put_type(proposal_id, body)


@router.get("/proposals/{proposal_id}/composition", response_model=M.Composition)
async def get_composition(proposal_id: str, open: str | None = None) -> M.Composition:  # noqa: A002
    return await C.get_composition(proposal_id, open)


@router.put("/proposals/{proposal_id}/composition", response_model=M.Composition)
async def put_composition(proposal_id: str, body: M.CompositionPut) -> M.Composition:
    return await C.put_composition(proposal_id, body)


@router.post("/proposals/{proposal_id}/composition:start", response_model=M.StartSections)
async def start_sections(proposal_id: str) -> M.StartSections:
    """「섹션 작성 시작」 — 업종 레이아웃 미결정 + 업종 감지 + MI/VP/SS 계열 시트가 있으면 PR3I, 아니면 첫 섹션."""
    return await C.start_sections(proposal_id)


@router.get("/proposals/{proposal_id}/industry", response_model=M.IndustryView)
async def get_industry(proposal_id: str, code: str | None = None) -> M.IndustryView:
    return await C.get_industry(proposal_id, code)


@router.put("/proposals/{proposal_id}/industry", response_model=M.IndustryView)
async def put_industry(proposal_id: str, body: M.IndustryPut) -> M.IndustryView:
    return await C.put_industry(proposal_id, body)
