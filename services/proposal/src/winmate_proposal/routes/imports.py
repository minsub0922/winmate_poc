"""§6.6 반입 — 드래그 앤 드롭 · 팝오버 「현재 작업에 추가」 · 다른 기능에서 보내기(handoff) · IMG4 이미지 자리."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import models as M
from ..ops import imports as I

router = APIRouter(prefix="/v1", tags=["imports"])


@router.post("/proposals/{proposal_id}/imports", response_model=M.ImportResult,
             responses={202: {"model": M.JobAccepted, "description": "사이드바 작업 · 보내기 — 추출/적용 잡"}})
async def create_import(proposal_id: str, body: M.ImportRequest):  # noqa: ANN201
    """팝업 항목(제품 · 솔루션 · 이미지 · 사례)은 **200** 바로 추가, 사이드바 작업 · 보내기(handoff)는 **202** 잡."""
    out = await I.create_import(proposal_id, body)
    if isinstance(out, M.JobAccepted):
        return JSONResponse(status_code=202, content=out.model_dump(mode="json"))
    return out


@router.get("/proposals/{proposal_id}/imports/{import_id}", response_model=M.Import)
async def get_import(proposal_id: str, import_id: str) -> M.Import:
    return await I.get_import(proposal_id, import_id)


@router.post("/proposals/{proposal_id}/imports/{import_id}:apply", response_model=M.JobAccepted, status_code=202)
async def apply_import(proposal_id: str, import_id: str, body: M.ImportApply) -> M.JobAccepted:
    return await I.apply_import(proposal_id, import_id, body)


@router.post("/proposals/{proposal_id}/imports/{import_id}:undo", response_model=M.UndoResult)
async def undo_import(proposal_id: str, import_id: str) -> M.UndoResult:
    return await I.undo_import(proposal_id, import_id)


@router.get("/proposals/{proposal_id}/image-slots", response_model=M.ImageSlots)
async def image_slots(proposal_id: str, image_ref: str | None = None, image_version: str | None = None,
                      image_id: str | None = None) -> M.ImageSlots:
    return await I.image_slots(proposal_id, image_ref=image_ref, image_version=image_version, image_id=image_id)
