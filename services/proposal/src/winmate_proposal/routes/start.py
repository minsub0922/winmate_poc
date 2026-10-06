"""§6.3 시작 방식 — RFP(PR1F) · 기존 작업(PR1L) · 연결 자료."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from .. import models as M
from ..ops import start as S

router = APIRouter(prefix="/v1", tags=["start"])


@router.post("/proposals/{proposal_id}/rfp", response_model=M.JobAccepted, status_code=202)
async def start_rfp(proposal_id: str, body: M.RfpStart) -> M.JobAccepted:
    return await S.start_rfp(proposal_id, body)


@router.get("/proposals/{proposal_id}/rfp", response_model=M.RfpView)
async def get_rfp(proposal_id: str) -> M.RfpView:
    return await S.get_rfp(proposal_id)


@router.put("/proposals/{proposal_id}/rfp/fields/{key}", response_model=M.RfpView)
async def put_rfp_field(proposal_id: str, key: str, body: M.RfpFieldPut) -> M.RfpView:
    return await S.put_rfp_field(proposal_id, key, body)


@router.post("/proposals/{proposal_id}/rfp:confirm", response_model=M.Proposal)
async def confirm_rfp(proposal_id: str) -> M.Proposal:
    return await S.confirm_rfp(proposal_id)


@router.get("/proposals/{proposal_id}/related-works", response_model=M.RelatedWorks)
async def related_works(proposal_id: str, scope: Literal["customer", "all"] = "customer", q: str | None = None) -> M.RelatedWorks:
    return await S.related_works(proposal_id, scope=scope, q=q)


@router.get("/proposals/{proposal_id}/links", response_model=M.LinksOut)
async def list_links(proposal_id: str, section_key: str | None = Query(None)) -> M.LinksOut:
    return await S.list_links(proposal_id, section_key)


@router.put("/proposals/{proposal_id}/links", response_model=M.LinksOut)
async def put_links(proposal_id: str, body: M.LinksPut) -> M.LinksOut:
    return await S.put_links(proposal_id, body)


@router.post("/proposals/{proposal_id}/links:apply", response_model=M.JobAccepted, status_code=202)
async def apply_links(proposal_id: str) -> M.JobAccepted:
    return await S.apply_links(proposal_id)


@router.delete("/proposals/{proposal_id}/links/{link_id}", response_model=M.LinkRemoved)
async def delete_link(proposal_id: str, link_id: str) -> M.LinkRemoved:
    return await S.delete_link(proposal_id, link_id)


@router.post("/proposals/{proposal_id}/links/{link_id}:restore", response_model=M.LinkedSource)
async def restore_link(proposal_id: str, link_id: str) -> M.LinkedSource:
    return await S.restore_link(proposal_id, link_id)


@router.post("/proposals/{proposal_id}/links/{link_id}:refresh", response_model=M.JobAccepted, status_code=202)
async def refresh_link(proposal_id: str, link_id: str) -> M.JobAccepted:
    return await S.refresh_link(proposal_id, link_id)
