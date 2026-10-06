"""§6.8 디자인 템플릿(PR6) · PPTX 생성(PR7) · 미리보기 레일(PR7P) · 렌더."""
from __future__ import annotations

from fastapi import APIRouter

from .. import models as M
from ..ops import design as D

router = APIRouter(prefix="/v1", tags=["design"])


@router.get("/proposals/{proposal_id}/design", response_model=M.DesignView)
async def get_design(proposal_id: str) -> M.DesignView:
    return await D.get_design(proposal_id)


@router.put("/proposals/{proposal_id}/design", response_model=M.DesignView)
async def put_design(proposal_id: str, body: M.DesignPatch) -> M.DesignView:
    return await D.put_design(proposal_id, body)


@router.post("/proposals/{proposal_id}/design/logo", response_model=M.DesignView)
async def put_logo(proposal_id: str, body: M.LogoIn) -> M.DesignView:
    return await D.put_logo(proposal_id, body)


@router.post("/proposals/{proposal_id}:generate", response_model=M.JobAccepted, status_code=202)
async def generate(proposal_id: str, body: M.GenerateIn | None = None) -> M.JobAccepted:
    return await D.generate(proposal_id, body or M.GenerateIn())


@router.get("/proposals/{proposal_id}/result", response_model=M.ResultView)
async def get_result(proposal_id: str) -> M.ResultView:
    return await D.get_result(proposal_id)


@router.get("/proposals/{proposal_id}/slides", response_model=M.SlidesView)
async def get_slides(proposal_id: str, filter: str | None = None) -> M.SlidesView:  # noqa: A002
    return await D.get_slides(proposal_id, filter)


@router.post("/proposals/{proposal_id}/renders", response_model=M.JobAccepted, status_code=202)
async def create_render(proposal_id: str, body: M.RenderIn | None = None) -> M.JobAccepted:
    return await D.create_render(proposal_id, body or M.RenderIn())
