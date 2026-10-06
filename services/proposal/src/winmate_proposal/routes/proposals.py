"""§6.2 제안서 — 목록(PR0) · 만들기 · 읽기 · 고치기 · 제출 표시."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Header, Query, Response

from .. import models as M
from ..ops import proposals as P

router = APIRouter(prefix="/v1", tags=["proposals"])


@router.get("/proposals", response_model=M.ProposalList)
async def list_proposals(
    tab: str = Query("all", description="all | draft | review | done (쉼표로 여러 개: draft,review)"),
    q: str | None = Query(None, description="제안서 · 고객사 검색"),
    owner: str = Query("all", description="me | all | <user id>"),
    type: str | None = Query(None, description="standard · quickwin · solution"),  # noqa: A002
    sort: Literal["due_asc", "updated_desc"] = "due_asc",
    project_id: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> M.ProposalList:
    return await P.list_proposals(tab=tab, q=q, owner=owner, type_=type, sort=sort, project_id=project_id, limit=limit, cursor=cursor)


@router.post("/proposals", response_model=M.Proposal, status_code=201)
async def create_proposal(body: M.ProposalCreate, response: Response) -> M.Proposal:
    out = await P.create_proposal(body)
    response.headers["ETag"] = str(out.rev)
    return out


@router.get("/proposals/{proposal_id}", response_model=M.Proposal)
async def get_proposal(proposal_id: str, response: Response) -> M.Proposal:
    out = await P.get_proposal(proposal_id)
    response.headers["ETag"] = str(out.rev)
    return out


@router.patch("/proposals/{proposal_id}", response_model=M.Proposal)
async def patch_proposal(proposal_id: str, body: M.ProposalPatch, response: Response,
                         if_match: str | None = Header(None, alias="If-Match")) -> M.Proposal:
    out = await P.patch_proposal(proposal_id, body, if_match)
    response.headers["ETag"] = str(out.rev)
    return out


@router.delete("/proposals/{proposal_id}", status_code=204)
async def delete_proposal(proposal_id: str) -> Response:
    await P.delete_proposal(proposal_id)
    return Response(status_code=204)


@router.post("/proposals/{proposal_id}:mark-submitted", response_model=M.Proposal)
async def mark_submitted(proposal_id: str, body: M.MarkSubmitted | None = None) -> M.Proposal:
    return await P.mark_submitted(proposal_id, body or M.MarkSubmitted())
