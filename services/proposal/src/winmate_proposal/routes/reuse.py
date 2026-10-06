"""§6.13 기존 제안서 활용(PR1C → PRU2 → PRU2F → PRU3A|PRU3B → PRU4|PRU4B → PRU5)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from .. import models as M
from ..ops import reuse as U

router = APIRouter(prefix="/v1", tags=["reuse"])


@router.get("/proposals/{proposal_id}/reuse/candidates", response_model=M.ReuseCandidates)
async def candidates(proposal_id: str) -> M.ReuseCandidates:
    return await U.candidates(proposal_id)


@router.post("/proposals/{proposal_id}/reuse", response_model=M.JobAccepted, status_code=202)
async def start_reuse(proposal_id: str, body: M.ReuseStart) -> M.JobAccepted:
    return await U.start(proposal_id, body)


@router.delete("/proposals/{proposal_id}/reuse", response_model=M.Ok)
async def delete_reuse(proposal_id: str) -> M.Ok:
    return await U.delete_reuse(proposal_id)


@router.get("/proposals/{proposal_id}/reuse", response_model=M.ReuseView)
async def get_reuse(proposal_id: str) -> M.ReuseView:
    return await U.get_view(proposal_id)


@router.get("/proposals/{proposal_id}/reuse/criteria/{no}", response_model=M.CriterionDetail)
async def get_criterion(proposal_id: str, no: int) -> M.CriterionDetail:
    return await U.get_criterion(proposal_id, no)


@router.put("/proposals/{proposal_id}/reuse/criteria/{no}", response_model=M.ReuseView)
async def put_criterion(proposal_id: str, no: int, body: M.CriterionPut) -> M.ReuseView:
    return await U.put_criterion(proposal_id, no, body)


@router.put("/proposals/{proposal_id}/reuse/pages/{no}/role", response_model=M.ReuseView)
async def put_page_role(proposal_id: str, no: int, body: M.RolePut) -> M.ReuseView:
    return await U.put_page_role(proposal_id, no, body)


@router.post("/proposals/{proposal_id}/reuse:reanalyze", response_model=M.ReuseConfirmOut)
async def reanalyze(proposal_id: str) -> M.ReuseConfirmOut:
    return await U.reanalyze(proposal_id)


@router.post("/proposals/{proposal_id}/reuse:confirm-analysis", response_model=M.ReuseConfirmOut)
async def confirm_analysis(proposal_id: str) -> M.ReuseConfirmOut:
    return await U.confirm_analysis(proposal_id)


@router.put("/proposals/{proposal_id}/reuse/mode", response_model=M.ReuseView)
async def put_mode(proposal_id: str, body: M.ModePut) -> M.ReuseView:
    return await U.put_mode(proposal_id, body)


@router.put("/proposals/{proposal_id}/reuse/plan/rows/{row_id}", response_model=M.ReuseView)
async def put_verdict(proposal_id: str, row_id: str, body: M.VerdictPut) -> M.ReuseView:
    return await U.put_verdict(proposal_id, row_id, body)


@router.post("/proposals/{proposal_id}/reuse/plan:confirm", response_model=M.ReuseConfirmOut)
async def confirm_plan(proposal_id: str, body: M.PlanConfirm | None = None) -> M.ReuseConfirmOut:
    return await U.confirm_plan(proposal_id, body or M.PlanConfirm())


@router.get("/proposals/{proposal_id}/sections/{key}/reuse-view", response_model=M.ReuseSectionView)
async def reuse_section_view(proposal_id: str, key: str, sheet_id: str | None = None,
                             view: Literal["compare", "guide", "new_only"] | None = None) -> M.ReuseSectionView:
    return await U.section_view(proposal_id, key, sheet_id, view)


@router.post("/proposals/{proposal_id}/sheets/{sheet_id}/reuse:pull-lines", response_model=M.Sheet)
async def pull_lines(proposal_id: str, sheet_id: str, body: M.PullLines | None = None) -> M.Sheet:
    return await U.pull_lines(proposal_id, sheet_id, body or M.PullLines())


@router.get("/proposals/{proposal_id}/reuse/summary", response_model=M.ReuseSummary)
async def reuse_summary(proposal_id: str) -> M.ReuseSummary:
    return await U.summary(proposal_id)
