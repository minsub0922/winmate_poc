"""ai-tools API (/v1). 이 파일의 엔드포인트가 contracts/ai-tools.json 이 된다(make contracts).

모델을 부르는 API 는 서비스 간 호출 전용(tags=["internal"] — 게이트웨이가 브라우저 호출을 막는다).
capabilities · usage 는 웹도 읽는다.
"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from winmate_common.errors import not_found
from winmate_common.sse import sse_response

from . import calllog, capabilities, embed, fetch, i2t, llm, search, t2i, websearch
from .schemas import (
    CallList,
    CallRecord,
    Capabilities,
    ChatRequest,
    ChatResponse,
    EmbedRequest,
    EmbedResponse,
    FetchRequest,
    FetchResponse,
    I2TRequest,
    I2TResponse,
    SearchRequest,
    SearchResponse,
    T2IEditRequest,
    T2IGenerateRequest,
    T2IResponse,
    UsageResponse,
    WebSearchRequest,
    WebSearchResponse,
)

router = APIRouter(prefix="/v1")
INTERNAL: list[str | Any] = ["internal"]

TITLE = "AI Tools — LLM · I2T · T2I · 웹 검색 · 웹 수집 · 임베딩 (외부 모델 호출의 유일한 통로)"


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="ai-tools", title=TITLE, version="0.2.0")


# ── 설정 · 사용량 ───────────────────────────────────────────

@router.get("/capabilities", response_model=Capabilities, tags=["meta"],
            summary="지금 제공자 · 모델 · 지원 기능 · 한도 · 오늘 사용량")
async def get_capabilities() -> dict[str, Any]:
    return await capabilities.capabilities()


@router.get("/usage", response_model=UsageResponse, tags=["meta"], summary="오늘 사용량 대 한도")
async def get_usage() -> dict[str, Any]:
    return await capabilities.usage()


# ── LLM ───────────────────────────────────────────────────

@router.post("/llm/chat", response_model=ChatResponse, tags=INTERNAL,
             summary="LLM 대화(JSON 스키마 · 도구 호출 · 기밀 정책 · 대체 경로)")
async def llm_chat(req: ChatRequest) -> dict[str, Any]:
    return await llm.chat(req)


@router.post(
    "/llm/stream", tags=INTERNAL, response_class=EventSourceResponse,
    summary="LLM 스트리밍(SSE)",
    description="SSE 이벤트: `delta` {text} 여러 번 → `done` {content, usage, call_id, …}. 오류는 `error` {code, message}. "
                "스트리밍을 지원하지 않는 설정이거나 json_schema · tools 가 있으면 delta 한 번.",
    responses={200: {"description": "text/event-stream", "content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def llm_stream(req: ChatRequest) -> EventSourceResponse:
    events = await llm.stream(req)
    return sse_response(events)


# ── I2T · T2I ─────────────────────────────────────────────

@router.post("/i2t/analyze", response_model=I2TResponse, tags=INTERNAL, summary="이미지 분석(글 · JSON · 박스)")
async def i2t_analyze(req: I2TRequest) -> dict[str, Any]:
    return await i2t.analyze(req)


@router.post("/t2i/generate", response_model=T2IResponse, tags=INTERNAL, summary="이미지 생성(files 서비스에 저장)")
async def t2i_generate(req: T2IGenerateRequest) -> dict[str, Any]:
    return await t2i.generate(req)


@router.post("/t2i/edit", response_model=T2IResponse, tags=INTERNAL,
             summary="이미지 편집(마스크 · 바깥 채우기 · 참조, 대체 경로 포함)")
async def t2i_edit(req: T2IEditRequest) -> dict[str, Any]:
    return await t2i.edit(req)


# ── 웹 ────────────────────────────────────────────────────

@router.post("/websearch", response_model=WebSearchResponse, tags=INTERNAL, summary="요약형 웹 검색")
async def websearch_summary(req: WebSearchRequest) -> dict[str, Any]:
    return await websearch.search(req)


@router.post("/search", response_model=SearchResponse, tags=INTERNAL, summary="검색 API(원문 URL 목록)")
async def search_api(req: SearchRequest) -> dict[str, Any]:
    return await search.search(req)


@router.post("/fetch", response_model=FetchResponse, tags=INTERNAL, summary="웹 페이지 수집(robots · 속도 제한 · 캐시)")
async def fetch_page(req: FetchRequest) -> dict[str, Any]:
    return await fetch.fetch(req)


@router.post("/embed", response_model=EmbedResponse, tags=INTERNAL, summary="임베딩")
async def embed_texts(req: EmbedRequest) -> dict[str, Any]:
    return await embed.embed(req)


# ── 호출 로그 ──────────────────────────────────────────────

@router.get("/calls", response_model=CallList, tags=INTERNAL, summary="모델 호출 로그(최신순)")
async def list_calls(capability: str | None = None, task: str | None = None,
                     limit: int = Query(50, ge=1, le=200), cursor: str | None = None) -> dict[str, Any]:
    items, next_cursor = await asyncio.to_thread(calllog.store().list, capability=capability, task=task, limit=limit, cursor=cursor)
    return {"items": items, "next_cursor": next_cursor}


@router.get("/calls/{call_id}", response_model=CallRecord, tags=INTERNAL, summary="호출 로그 하나")
async def get_call(call_id: str) -> dict[str, Any]:
    rec = await asyncio.to_thread(calllog.store().get, call_id)
    if rec is None:
        raise not_found("호출 로그", call_id)
    return rec
