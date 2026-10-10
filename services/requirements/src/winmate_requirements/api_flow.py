"""고객 요구사항 새 흐름 API(/v1/rq-flows) — 보드 webapp1 RQ0 · RQ1 · RQ1_AI · RQ_Done. 처리 본체는 rqflow.py."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from . import rqflow as rf
from .models import JobAccepted

router = APIRouter(prefix="/v1", tags=["rq-flows"])


@router.get("/rq-flows", response_model=rf.RFList)
async def list_rq_flows(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    """새 흐름 요구사항 목록(최근 수정 순) — 목록 화면의 '작성 중' 줄."""
    return await rf.list_flows(limit, cursor)


@router.post("/rq-flows", response_model=rf.RFDoc, status_code=201)
async def create_rq_flow(body: rf.RFCreate | None = None) -> dict[str, Any]:
    """새 요구사항(코드 RQ-NN). 키맨을 주지 않으면 빈 키맨 하나(가중치 100)."""
    return await rf.create(body or rf.RFCreate())


@router.get("/rq-flows/{flow_id}", response_model=rf.RFDoc)
async def get_rq_flow(flow_id: str) -> dict[str, Any]:
    """id(rqf_…) 또는 코드(RQ-NN)."""
    return rf.to_api(await rf.load(flow_id))


@router.put("/rq-flows/{flow_id}", response_model=rf.RFDoc)
async def put_rq_flow(flow_id: str, body: rf.RFUpdate) -> dict[str, Any]:
    """폼 전체 고치기(자동 저장). expected_version 이 다르면 409 VERSION_CONFLICT, 파일로 채우는 중이면 409 FILLING."""
    return await rf.put_form(flow_id, body)


@router.post("/rq-flows/{flow_id}:fill", response_model=JobAccepted, status_code=202)
async def fill_rq_flow(flow_id: str, body: rf.RFFillIn) -> dict[str, Any]:
    """파일로 폼 채우기(잡 rq.flow.fill) — 빈 칸만 채운다. 끝나면 sources 에 파일이 붙는다."""
    return await rf.start_fill(flow_id, body)


@router.post("/rq-flows/{flow_id}/deep-questions", response_model=rf.RFDeepOut)
async def deep_questions(flow_id: str) -> dict[str, Any]:
    """AI 심층 질의 — 부족한 곳을 찾아 질문(ai-pending)을 만든다(`rq.deep_questions.v1`, 실패하면 규칙 문장)."""
    return await rf.deep_questions(flow_id)


@router.post("/rq-flows/{flow_id}/deep-questions/{question_id}:answer", response_model=rf.RFDoc)
async def answer_question(flow_id: str, question_id: str, body: rf.RFAnswer) -> dict[str, Any]:
    """답(보기 · 직접 입력)을 폼에 반영(ai-accepted) — later=true 면 고객에게 확인으로 남긴다."""
    return await rf.answer(flow_id, question_id, body)


@router.post("/rq-flows/{flow_id}/deep-questions:close", response_model=rf.RFDoc)
async def close_questions(flow_id: str) -> dict[str, Any]:
    """질의 닫기 — 답하지 않은 질문은 버린다."""
    return await rf.close_deep(flow_id)


@router.post("/rq-flows/{flow_id}:finish", response_model=rf.RFStageOut)
async def finish_rq_flow(flow_id: str) -> dict[str, Any]:
    """저장 — 처음이면 Storyboard 자동 생성(create_flow), 다음부터는 stages.rq 반영(push_stage). ver = 저장 횟수."""
    return await rf.finish(flow_id)
