"""§6.7 딸깍 — 계획(팝오버) · 시작 · 실행 보기(OneClickGen · OneClickDone). 메모 · 중지는 웹이 jobs 를 직접 부른다."""
from __future__ import annotations

from fastapi import APIRouter, Query

from .. import models as M
from ..ops import oneclick as O

router = APIRouter(prefix="/v1", tags=["one-click"])


@router.get("/proposals/{proposal_id}/one-click/plan", response_model=M.OneClickPlan)
async def one_click_plan(proposal_id: str, from_: str | None = Query(None, alias="from", description="누른 단계(stage)"),
                         section: str | None = None) -> M.OneClickPlan:
    return await O.plan(proposal_id, from_stage=from_, section_key=section)


@router.post("/proposals/{proposal_id}/one-click", response_model=M.JobAccepted, status_code=202)
async def start_one_click(proposal_id: str, body: M.OneClickStart | None = None) -> M.JobAccepted:
    return await O.start(proposal_id, body or M.OneClickStart())


@router.get("/proposals/{proposal_id}/one-click/{job_id}", response_model=M.OneClickView)
async def get_one_click(proposal_id: str, job_id: str) -> M.OneClickView:
    return await O.view(proposal_id, job_id)
