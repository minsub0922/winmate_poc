"""dss API (/v1). 이 파일의 엔드포인트가 contracts/dss.json 이 된다(make contracts). 처리 본체는 dss.py."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel

from . import dss as ds

router = APIRouter(prefix="/v1")


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="dss", title="공간별 제품 매칭 DSS — 업종 · 공간 · 공간별 제품 · 솔루션(새 콘텐츠 흐름, Storyboard 사전 작업)", version="0.1.0")


T = ["dss"]


@router.get("/dss", response_model=ds.DSList, tags=T)
async def list_dss(limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    """DSS 목록(최근 수정 순) — 보드 List 의 초안 줄."""
    return await ds.list_docs(limit, cursor)


@router.post("/dss", response_model=ds.DSDoc, status_code=201, tags=T,
             responses={200: {"model": ds.DSDoc, "description": "이 Storyboard 의 저장 전 초안이 이미 있음 — 그 초안(새로 만들지 않음)"}})
async def create_dss(body: ds.DSCreate, response: Response) -> dict[str, Any]:
    """새 DSS — 고른 Storyboard 의 고객 요구사항(rq)을 문맥으로 가져온다. Storyboard 없으면 404, rq 없으면 422 PREREQUISITE_MISSING.
    같은 Storyboard 의 저장 전 초안이 있으면 그것을 200 으로 돌려준다(Gate 를 다시 거쳐도 초안이 늘지 않음)."""
    doc, created = await ds.create(body)
    if not created:
        response.status_code = 200
    return doc


@router.get("/dss/{dss_id}", response_model=ds.DSDoc, tags=T)
async def get_dss(dss_id: str) -> dict[str, Any]:
    """DSS 한 건. 허브에만 있는 DSS(id = DSS-nn)는 그 stages.dss 값으로 편집본을 만들어 돌려준다."""
    return ds.to_api(await ds.load(dss_id))


@router.delete("/dss/{dss_id}", status_code=204, response_class=Response, tags=T)
async def delete_dss(dss_id: str, expected_version: int | None = Query(None, description="주면 지금 판과 다를 때 409 VERSION_CONFLICT")) -> Response:
    """저장 전 초안 지우기(목록 줄 ×, 소프트 삭제 · 작업물 색인도 지움) — 한 번도 저장하지 않은 것만.
    저장한 DSS 는 Storyboard 에 연결돼 있어 409 SAVED_CONTENT, 없으면 404 NOT_FOUND."""
    await ds.delete(dss_id, expected_version)
    return Response(status_code=204)


@router.put("/dss/{dss_id}/industry", response_model=ds.DSDoc, tags=T)
async def set_industry(dss_id: str, body: ds.DSSetIndustry) -> dict[str, Any]:
    """업종 고르기(value) · AI 업종 추론 적용(accept_ai)."""
    return await ds.set_industry(dss_id, body)


@router.post("/dss/{dss_id}/spaces", response_model=ds.DSDoc, status_code=201, tags=T)
async def add_space(dss_id: str, body: ds.DSAddSpace) -> dict[str, Any]:
    """공간 추가 — AI 공간 추천에 있던 이름이면 ai-accepted(근거 유지). 같은 이름이 있으면 409 SPACE_EXISTS."""
    return await ds.add_space(dss_id, body)


@router.patch("/dss/{dss_id}/spaces/{space_key}", response_model=ds.DSDoc, tags=T)
async def rename_space(dss_id: str, space_key: str, body: ds.DSPatchSpace) -> dict[str, Any]:
    return await ds.rename_space(dss_id, space_key, body)


@router.delete("/dss/{dss_id}/spaces/{space_key}", response_model=ds.DSDoc, tags=T)
async def delete_space(dss_id: str, space_key: str, expected_version: int | None = None) -> dict[str, Any]:
    return await ds.delete_space(dss_id, space_key, expected_version)


@router.get("/dss/{dss_id}/spaces/{space_key}/candidates", response_model=ds.DSCandidates, tags=T)
async def space_candidates(dss_id: str, space_key: str) -> dict[str, Any]:
    """이 공간의 KB 후보 제품군(S1, 그 공간 관련 요구 문장으로) — 제품 고르기 팝업의 'KB 추천' 묶음."""
    return await ds.space_candidates(dss_id, space_key)


@router.post("/dss/{dss_id}/spaces/{space_key}/products", response_model=ds.DSDoc, status_code=201, tags=T)
async def add_product(dss_id: str, space_key: str, body: ds.DSAddProduct) -> dict[str, Any]:
    """공간에 제품 넣기(직접). 이미 있는 제품이면 그대로(AI 추천이었으면 수락)."""
    return await ds.add_product(dss_id, space_key, body)


@router.patch("/dss/{dss_id}/products/{product_id}", response_model=ds.DSDoc, tags=T)
async def patch_product(dss_id: str, product_id: str, body: ds.DSPatchProduct) -> dict[str, Any]:
    """수량 고치기(빈 문자열이면 [확인 필요]) · AI 추천 수락(accept)."""
    return await ds.patch_product(dss_id, product_id, body)


@router.delete("/dss/{dss_id}/products/{product_id}", response_model=ds.DSDoc, tags=T)
async def delete_product(dss_id: str, product_id: str, expected_version: int | None = None) -> dict[str, Any]:
    """제품 빼기 — AI 추천 거절도 이것."""
    return await ds.delete_product(dss_id, product_id, expected_version)


@router.post("/dss/{dss_id}:accept-all", response_model=ds.DSDoc, tags=T)
async def accept_all(dss_id: str) -> dict[str, Any]:
    """공간별 제품 AI 추천 모두 수락."""
    return await ds.accept_all(dss_id)


@router.put("/dss/{dss_id}/solutions", response_model=ds.DSDoc, tags=T)
async def set_solutions(dss_id: str, body: ds.DSSetSolutions) -> dict[str, Any]:
    """고른 솔루션(0개 이상, 카탈로그 id). AI 추천이던 것은 ai-accepted. 함께 쓰는 제품은 서비스가 다시 계산한다."""
    return await ds.set_solutions(dss_id, body)


@router.get("/dss/{dss_id}/solution-options", response_model=ds.DSSolutionOptions, tags=T)
async def solution_options(dss_id: str) -> dict[str, Any]:
    """솔루션 고르기 카드 — 카탈로그 전체(관련 높은 순) · 함께 쓰는 제품 · 고름 · AI 추천 · 겹침 안내."""
    return await ds.solution_options(dss_id)


@router.post("/dss/{dss_id}:suggest", response_model=ds.DSSuggestResult, tags=T)
async def suggest(dss_id: str, body: ds.DSSuggestBody) -> dict[str, Any]:
    """AI 추가기능(점선 → 수락) — industry: 업종 추론 · spaces: 공간 추천 · products: 공간별 제품 자동 매칭(`ds.industry_spaces.v1`) ·
    solutions: 솔루션 추천(`ds.solutions.v1`). 모델이 없으면 KB 로 결정적 추천(mode=kb_only)."""
    return await ds.suggest(dss_id, body)


@router.post("/dss/{dss_id}:finish", response_model=ds.DSStageOut, tags=T)
async def finish(dss_id: str) -> dict[str, Any]:
    """저장 → Storyboard flow.json stages.dss · 요약본 · 팝업 카드(허브 push_stage). 공간 · 제품이 없으면 422."""
    return await ds.finish(dss_id)


@router.get("/dss/{dss_id}/stage", response_model=ds.DSStageOut, tags=T)
async def get_stage(dss_id: str) -> dict[str, Any]:
    """지금 값으로 만든 stages.dss · 요약 줄(저장하지 않음)."""
    return await ds.get_stage(dss_id)
