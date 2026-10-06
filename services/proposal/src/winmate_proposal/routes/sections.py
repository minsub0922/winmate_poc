"""§6.5 섹션(SectionStep) · 시트 · 템플릿 고르기 · 값 · 수정 요청."""
from __future__ import annotations

from fastapi import APIRouter, Header, Query, Response

from .. import models as M
from ..ops import sections as S

router = APIRouter(prefix="/v1", tags=["sections"])


@router.get("/proposals/{proposal_id}/sections/{key}", response_model=M.SectionView)
async def get_section(proposal_id: str, key: str) -> M.SectionView:
    return await S.get_section(proposal_id, key)


@router.post("/proposals/{proposal_id}/sections/{key}:fill", response_model=M.JobAccepted, status_code=202)
async def fill_section(proposal_id: str, key: str, body: M.SectionFill | None = None) -> M.JobAccepted:
    return await S.fill_section(proposal_id, key, body or M.SectionFill())


@router.post("/proposals/{proposal_id}/sections/{key}/requests", response_model=M.JobAccepted, status_code=202)
async def section_request(proposal_id: str, key: str, body: M.TextRequest) -> M.JobAccepted:
    return await S.section_request(proposal_id, key, body)


@router.post("/proposals/{proposal_id}/sections/{key}:confirm", response_model=M.SectionConfirmResult)
async def confirm_section(proposal_id: str, key: str) -> M.SectionConfirmResult:
    return await S.confirm_section(proposal_id, key)


@router.post("/proposals/{proposal_id}/sections/{key}/templates:auto", response_model=M.SectionView)
async def section_templates_auto(proposal_id: str, key: str, body: M.TemplatesAuto | None = None) -> M.SectionView:
    return await S.section_templates_auto(proposal_id, key, body or M.TemplatesAuto())


@router.get("/proposals/{proposal_id}/sheets/{sheet_id}", response_model=M.Sheet)
async def get_sheet(proposal_id: str, sheet_id: str, response: Response) -> M.Sheet:
    out = await S.get_sheet(proposal_id, sheet_id)
    response.headers["ETag"] = str(out.rev)
    return out


@router.patch("/proposals/{proposal_id}/sheets/{sheet_id}", response_model=M.SheetPatchResult)
async def patch_sheet(proposal_id: str, sheet_id: str, body: M.SheetPatch, response: Response,
                      if_match: str | None = Header(None, alias="If-Match")) -> M.SheetPatchResult:
    out = await S.patch_sheet(proposal_id, sheet_id, body, if_match)
    response.headers["ETag"] = str(out.rev)
    return out


@router.get("/proposals/{proposal_id}/sheets/{sheet_id}/template-options", response_model=M.TemplateOptions)
async def template_options(proposal_id: str, sheet_id: str, product_count: int | None = Query(None)) -> M.TemplateOptions:
    return await S.template_options(proposal_id, sheet_id, product_count)


@router.put("/proposals/{proposal_id}/sheets/{sheet_id}/template", response_model=M.TemplateApplyResult)
async def put_template(proposal_id: str, sheet_id: str, body: M.TemplatePut) -> M.TemplateApplyResult:
    return await S.put_template(proposal_id, sheet_id, body)


@router.post("/proposals/{proposal_id}/sheets/{sheet_id}:rewrite", response_model=M.JobAccepted, status_code=202)
async def rewrite_sheet(proposal_id: str, sheet_id: str, body: M.SheetRewrite | None = None) -> M.JobAccepted:
    return await S.rewrite_sheet(proposal_id, sheet_id, body or M.SheetRewrite())


@router.get("/proposals/{proposal_id}/sheets/{sheet_id}/messages", response_model=M.MessageList)
async def sheet_messages(proposal_id: str, sheet_id: str) -> M.MessageList:
    return await S.messages(proposal_id, scope="sheet", scope_ref=sheet_id)


@router.get("/proposals/{proposal_id}/messages", response_model=M.MessageList)
async def proposal_messages(proposal_id: str, scope: str | None = None, scope_ref: str | None = None) -> M.MessageList:
    return await S.messages(proposal_id, scope=scope, scope_ref=scope_ref)


@router.get("/proposals/{proposal_id}/facts", response_model=M.FactList)
async def list_facts(proposal_id: str) -> M.FactList:
    return await S.list_facts(proposal_id)


@router.put("/proposals/{proposal_id}/facts/{fact_id}", response_model=M.FactUpdateResult)
async def put_fact(proposal_id: str, fact_id: str, body: M.FactPut) -> M.FactUpdateResult:
    return await S.put_fact(proposal_id, fact_id, body)


@router.post("/proposals/{proposal_id}/requests", response_model=M.JobAccepted, status_code=202)
async def proposal_request(proposal_id: str, body: M.TextRequest) -> M.JobAccepted:
    return await S.proposal_request(proposal_id, body)


@router.post("/proposals/{proposal_id}/notes:generate", response_model=M.JobAccepted, status_code=202)
async def notes_generate(proposal_id: str, body: M.NotesGenerate | None = None) -> M.JobAccepted:
    return await S.notes_generate(proposal_id, body or M.NotesGenerate())
