"""가치 맵 API(/v1/value-maps) — 새 VP 흐름(보드 webapp1 VP2 · VpDetail · VP2_Pick). 처리 본체는 valuemap.py."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from . import valuemap as vm

router = APIRouter(prefix="/v1", tags=["value-maps"])


@router.get("/value-maps", response_model=vm.VMList)
async def list_value_maps(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    return await vm.list_maps(limit, cursor)


@router.post("/value-maps", response_model=vm.VMDoc, status_code=201)
async def create_value_map(body: vm.VMCreate) -> dict[str, Any]:
    """새 가치 맵. candidates(DSS 제품 · 솔루션)를 주거나, context_text(요구 문장)로 KB 에서 공간별 후보를 찾는다."""
    return await vm.create(body)


@router.get("/value-maps/{map_id}", response_model=vm.VMDoc)
async def get_value_map(map_id: str) -> dict[str, Any]:
    return vm.to_api(await vm.load(map_id))


@router.put("/value-maps/{map_id}/items", response_model=vm.VMDoc)
async def set_value_map_items(map_id: str, body: vm.VMSetItems) -> dict[str, Any]:
    """VP 에 넣을 제품 · 솔루션 고르기(제품 · 솔루션 고르기 팝업). 하나 이상."""
    return await vm.set_items(map_id, body)


@router.post("/value-maps/{map_id}/items/{item_key}/values", response_model=vm.VMDoc, status_code=201)
async def add_value(map_id: str, item_key: str, body: vm.VMAddValue) -> dict[str, Any]:
    return await vm.add_value(map_id, item_key, body)


@router.patch("/value-maps/{map_id}/values/{value_id}", response_model=vm.VMDoc)
async def patch_value(map_id: str, value_id: str, body: vm.VMPatchValue) -> dict[str, Any]:
    """가치 고치기 · 니즈 쓰기(빈 문자열이면 지움) · AI 후보 수락(accept) · AI 니즈 수락(accept_need)."""
    return await vm.patch_value(map_id, value_id, body)


@router.delete("/value-maps/{map_id}/values/{value_id}", response_model=vm.VMDoc)
async def delete_value(map_id: str, value_id: str) -> dict[str, Any]:
    """가치 지우기 — AI 후보 '빼기'도 이것."""
    return await vm.delete_value(map_id, value_id)


@router.post("/value-maps/{map_id}:accept-all", response_model=vm.VMDoc)
async def accept_all(map_id: str) -> dict[str, Any]:
    return await vm.accept_all(map_id)


@router.post("/value-maps/{map_id}:suggest", response_model=vm.VMSuggestResult)
async def suggest(map_id: str, body: vm.VMSuggestBody | None = None) -> dict[str, Any]:
    """AI 가치 매칭 추천 — KB 원문 메시지 + 요구 → 가치 후보(니즈 포함, 제품마다 최대 2) · 빈 니즈 추론. 모두 ai-pending."""
    return await vm.suggest(map_id, body or vm.VMSuggestBody())


@router.post("/value-maps/{map_id}/values/{value_id}:infer-need", response_model=vm.VMInferNeedResult)
async def infer_need(map_id: str, value_id: str) -> dict[str, Any]:
    """AI 니즈 추론(가치 하나). 모델이 없으면 need=null · reason."""
    return await vm.infer_need(map_id, value_id)


@router.get("/value-maps/{map_id}/items/{item_key}/linked", response_model=vm.VMLinked)
async def linked_values(map_id: str, item_key: str) -> dict[str, Any]:
    """연결된 가치 전체 — 이 제안 · 같은 제품을 쓴 다른 제안 · KB 공식 메시지."""
    return await vm.linked(map_id, item_key)


@router.post("/value-maps/{map_id}/items/{item_key}/values:import", response_model=vm.VMDoc)
async def import_value(map_id: str, item_key: str, body: vm.VMImportValue) -> dict[str, Any]:
    """다른 제안의 가치를 이 제안에 가져오기(복사)."""
    return await vm.import_value(map_id, item_key, body)


@router.post("/value-maps/{map_id}:finish", response_model=vm.VMStageOut)
async def finish(map_id: str) -> dict[str, Any]:
    """저장 — status=done, Storyboard flow.json 의 stages.vp 와 요약 md 를 돌려준다."""
    return await vm.finish(map_id)


@router.get("/value-maps/{map_id}/stage", response_model=vm.VMStageOut)
async def get_stage(map_id: str) -> dict[str, Any]:
    return await vm.get_stage(map_id)
