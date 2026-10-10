"""Storyboard 흐름 API(/v1/flows) — flow.json · summary.md · stage 반영 · 분기 · Key message. 본체는 flows.py."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from . import flows as fl

router = APIRouter(prefix="/v1", tags=["flows"])


@router.get("/flows", response_model=fl.FlowList)
async def list_flows(limit: int = Query(100, ge=1, le=200), content: fl.StageKey | None = None, q: str | None = None) -> dict[str, Any]:
    """Storyboard 목록(SB0) · 사전 작업 고르기(Gate). content= 를 주면 eligible · need · existing 을 채우고 고를 수 있는 것을 위로."""
    return await fl.list_flows(limit, content, q)


@router.get("/flows/contents/{key}", response_model=fl.FlowContentList)
async def list_flow_contents(key: fl.StageKey) -> dict[str, Any]:
    """콘텐츠 목록(보드 List) — 저장된 콘텐츠마다 연결된 Storyboard 들. 아직 저장 전 초안은 각 서비스 목록에 있다."""
    return await fl.list_contents(key)


@router.post("/flows", response_model=fl.FlowDoc, status_code=201, tags=["internal"])
async def create_flow(body: fl.FlowCreate) -> dict[str, Any]:
    """고객 요구사항을 저장하면 requirements 가 부른다(Storyboard 자동 생성)."""
    return await fl.create(body)


@router.get("/flows/{flow_id}", response_model=fl.FlowDoc)
async def get_flow(flow_id: str) -> dict[str, Any]:
    return await fl.get_api(flow_id)


@router.patch("/flows/{flow_id}", response_model=fl.FlowDoc)
async def patch_flow(flow_id: str, body: fl.FlowPatch) -> dict[str, Any]:
    """이름 · Key message · 요약본 고침(사람이 더한 문장은 절마다 남겨 ✎ 표시)."""
    return await fl.patch(flow_id, body)


@router.put("/flows/{flow_id}/stages/{key}", response_model=fl.FlowStageOut, tags=["internal"])
async def put_flow_stage(flow_id: str, key: fl.StageKey, body: fl.FlowStageIn) -> dict[str, Any]:
    """콘텐츠를 저장하면 그 서비스가 부른다 — stages.<key> 실제 값 · 요약본 줄 · 팝업 카드. 같은 ref 의 다른 Storyboard 도 함께 바뀐다."""
    return await fl.put_stage(flow_id, key, body)


@router.post("/flows/{flow_id}:branch", response_model=fl.FlowDoc, status_code=201)
async def branch_flow(flow_id: str, body: fl.FlowBranch) -> dict[str, Any]:
    """복제본 만들기 — Storyboard 를 분기하고 앞 단계(사전 작업)는 공유한다. 그 콘텐츠는 새 Storyboard 에서 새로 만든다."""
    return await fl.branch(flow_id, body)


@router.post("/flows/{flow_id}/key-message:suggest", response_model=fl.KeyMessageOut)
async def suggest_key_message(flow_id: str) -> dict[str, Any]:
    """전략 수립 팝업의 AI 후보 3안(sb.key_message.v1, 모델이 없으면 연결 콘텐츠 문장으로 규칙 후보)."""
    return await fl.key_message_candidates(flow_id)
