"""§6.9 확인 항목(PR7Q 확정 필요 · 검토 필요)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from .. import models as M
from ..ops import confirm as C

router = APIRouter(prefix="/v1", tags=["confirm"])


@router.get("/proposals/{proposal_id}/confirm-items", response_model=M.ConfirmList)
async def list_items(proposal_id: str, status: Literal["open", "confirmed", "all"] = "all", sheet_id: str | None = None,
                     category: Literal["fact", "review"] | None = None) -> M.ConfirmList:
    return await C.list_items(proposal_id, status=status, sheet_id=sheet_id, category=category)


@router.post("/proposals/{proposal_id}/confirm-items", response_model=M.ConfirmItem, status_code=201)
async def create_item(proposal_id: str, body: M.ConfirmCreate) -> M.ConfirmItem:
    return await C.create_item(proposal_id, body)


@router.post("/proposals/{proposal_id}/confirm-items/{item_id}:resolve", response_model=M.ConfirmResolveResult)
async def resolve_item(proposal_id: str, item_id: str, body: M.ConfirmResolve | None = None) -> M.ConfirmResolveResult:
    return await C.resolve_item(proposal_id, item_id, body or M.ConfirmResolve())


@router.post("/proposals/{proposal_id}/confirm-items/{item_id}:move-to-note", response_model=M.ConfirmItem)
async def move_to_note(proposal_id: str, item_id: str) -> M.ConfirmItem:
    return await C.move_to_note(proposal_id, item_id)


@router.post("/proposals/{proposal_id}/confirm-items/{item_id}:anonymize", response_model=M.ConfirmResolveResult)
async def anonymize(proposal_id: str, item_id: str) -> M.ConfirmResolveResult:
    return await C.anonymize(proposal_id, item_id)


@router.post("/proposals/{proposal_id}/confirm-items/{item_id}:question", response_model=M.QuestionOut)
async def question(proposal_id: str, item_id: str, body: M.QuestionIn | None = None) -> M.QuestionOut:
    return await C.question(proposal_id, item_id, body or M.QuestionIn())


@router.post("/proposals/{proposal_id}/confirm-items/{item_id}:evidence", response_model=M.ConfirmItem)
async def attach_evidence(proposal_id: str, item_id: str, body: M.EvidenceIn) -> M.ConfirmItem:
    return await C.attach_evidence(proposal_id, item_id, body)


@router.post("/proposals/{proposal_id}/confirm-items:move-to-note", response_model=M.ConfirmList)
async def move_all_to_note(proposal_id: str, body: M.BulkIds | None = None) -> M.ConfirmList:
    return await C.move_all_to_note(proposal_id, body or M.BulkIds())


@router.post("/proposals/{proposal_id}/confirm-items:research", response_model=M.JobAccepted, status_code=202)
async def research(proposal_id: str, body: M.ResearchIn | None = None) -> M.JobAccepted:
    return await C.research(proposal_id, body or M.ResearchIn())
