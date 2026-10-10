"""공간 시나리오 묶음 API(/v1/space-sets) — 새 흐름(보드 webapp1 SC1 · SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_Done). 처리 본체는 spaceset.py."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from . import spaceset as ss

router = APIRouter(prefix="/v1", tags=["space-sets"])


@router.get("/space-sets", response_model=ss.SSList)
async def list_space_sets(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    return await ss.list_sets(limit, cursor)


@router.post("/space-sets", response_model=ss.SSDoc, status_code=201)
async def create_space_set(body: ss.SSCreate) -> dict[str, Any]:
    """새 묶음(보드 Gate → SC2). sb_id 만 주면 Storyboard flow.json 의 DSS 공간 · 공간별 제품 · 솔루션으로 시작한다
    (Storyboard 없음 404 STORYBOARD_NOT_FOUND · DSS 전 422 PREREQUISITE_MISSING). spaces 를 직접 주거나 context_text(요구 문장)로 KB 에서 찾을 수도 있다."""
    return await ss.create(body)


@router.get("/space-sets/{set_id}", response_model=ss.SSDoc)
async def get_space_set(set_id: str) -> dict[str, Any]:
    return ss.to_api(await ss.load(set_id))


@router.put("/space-sets/{set_id}", response_model=ss.SSDoc)
async def put_space_set(set_id: str, body: ss.SSPut) -> dict[str, Any]:
    """공간 · 제품 · 시나리오 · 장면 · 항목 전체를 고쳐 저장(자동 저장). 제품이 빈 공간 · 시나리오는 issues 로 알려 준다(저장은 됨)."""
    return await ss.put(set_id, body)


@router.post("/space-sets/{set_id}/spaces/{space_id}:suggest", response_model=ss.SSSuggestOut)
async def suggest_scenarios(set_id: str, space_id: str) -> dict[str, Any]:
    """AI 시나리오 3안(이 공간) — 후보는 candidates 에 점선으로, 수락해야 시나리오가 된다."""
    return await ss.suggest(set_id, space_id)


@router.post("/space-sets/{set_id}/spaces/{space_id}/candidates/{cid}:accept", response_model=ss.SSDoc)
async def accept_candidate(set_id: str, space_id: str, cid: str) -> dict[str, Any]:
    return await ss.accept(set_id, space_id, cid)


@router.delete("/space-sets/{set_id}/spaces/{space_id}/candidates/{cid}", response_model=ss.SSDoc)
async def drop_candidate(set_id: str, space_id: str, cid: str) -> dict[str, Any]:
    return await ss.drop(set_id, space_id, cid)


@router.post("/space-sets/{set_id}:finish", response_model=ss.SSStageOut)
async def finish_space_set(set_id: str) -> dict[str, Any]:
    """저장 — 공간 · 시나리오마다 제품 · 솔루션이 하나 이상이어야 한다(아니면 422). ver(저장 횟수)가 오르고,
    Storyboard 가 있으면 허브 stages.sc · 요약본 · 팝업 카드에 반영한다(flow_sync). 응답: stages.sc · 요약 md · flow_sync."""
    return await ss.finish(set_id)


@router.get("/space-sets/{set_id}/stage", response_model=ss.SSStageOut)
async def get_space_set_stage(set_id: str) -> dict[str, Any]:
    return await ss.get_stage(set_id)
