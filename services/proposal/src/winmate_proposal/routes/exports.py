"""§6.12 내보내기(PR7X) · 고객사 마스터(.potx)."""
from __future__ import annotations

from fastapi import APIRouter

from .. import models as M
from ..ops import exports as X

router = APIRouter(prefix="/v1", tags=["exports"])


@router.get("/proposals/{proposal_id}/export-options", response_model=M.ExportOptions)
async def export_options(proposal_id: str, version: int | None = None, lang: str | None = None) -> M.ExportOptions:
    return await X.export_options(proposal_id, version, lang)


@router.post("/proposals/{proposal_id}/exports", response_model=M.JobAccepted, status_code=202)
async def create_export(proposal_id: str, body: M.ExportRequest) -> M.JobAccepted:
    return await X.create_export(proposal_id, body)


@router.get("/proposals/{proposal_id}/exports/{export_id}", response_model=M.ExportRecord)
async def get_export(proposal_id: str, export_id: str) -> M.ExportRecord:
    return await X.get_export(proposal_id, export_id)


@router.post("/proposals/{proposal_id}/masters", response_model=M.MasterCreated, status_code=201)
async def upload_master(proposal_id: str, body: M.MasterUpload) -> M.MasterCreated:
    return await X.upload_master(proposal_id, body)
