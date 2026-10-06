"""§6.11 버전 · 변경 이력(PR7V)."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter

from .. import models as M
from ..ops import versions as V

router = APIRouter(prefix="/v1", tags=["versions"])


@router.get("/proposals/{proposal_id}/versions", response_model=M.VersionsView)
async def list_versions(proposal_id: str, include: str = "changes,events") -> M.VersionsView:
    return await V.list_versions(proposal_id, include)


@router.post("/proposals/{proposal_id}/versions", response_model=M.VersionCreated, status_code=201)
async def save_version(proposal_id: str, body: M.VersionCreate | None = None) -> M.VersionCreated:
    return await V.save_version(proposal_id, body or M.VersionCreate())


@router.get("/proposals/{proposal_id}/versions/compare", response_model=M.CompareView)
async def compare(proposal_id: str, a: int | None = None, b: int | None = None, mode: Literal["side", "changes"] = "side",
                  sheet: str | None = None) -> M.CompareView:
    return await V.compare(proposal_id, a, b, mode, sheet)


@router.post("/proposals/{proposal_id}/versions/{n}/restore", response_model=M.RestoreResult)
async def restore(proposal_id: str, n: int, body: M.RestoreIn | None = None) -> M.RestoreResult:
    return await V.restore(proposal_id, n, body or M.RestoreIn())


@router.post("/proposals/{proposal_id}/changes/{change_id}:revert", response_model=M.RevertResult)
async def revert_change(proposal_id: str, change_id: str) -> M.RevertResult:
    return await V.revert_change(proposal_id, change_id)
