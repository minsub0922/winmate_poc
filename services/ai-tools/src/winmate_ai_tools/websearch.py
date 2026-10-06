"""요약형 웹 검색 — POST /v1/websearch.

사내 검색 API 는 LLM 요약만 돌려준다. 이를 흉내 내기 위해 WEBSEARCH_RETURN_SOURCES=false(기본)면
Gemini grounding 이 URL 을 줘도 sources=[] · returned_sources=false 로 내보낸다.
"""
from __future__ import annotations

from typing import Any

from . import config
from .providers.base import WebSearchCall
from .runtime import track
from .schemas import WebSearchRequest


async def search(req: WebSearchRequest) -> dict[str, Any]:
    cfg = config.load("websearch")
    async with track("websearch", req.task, request=req.model_dump(exclude_none=True), confidential=req.confidential, cfg=cfg) as call:
        call.check_policy()
        kp = {"query": req.query, "locale": req.locale, "max_sources": req.max_sources}
        hit = await call.replay(kp)
        if hit is not None:
            resp = dict(hit["response"])
            if not cfg.return_sources:
                resp["sources"], resp["returned_sources"] = [], False
            return call.done(resp)
        await call.acquire()
        provider = call.provider()
        res = await call.invoke(provider.websearch, cfg, WebSearchCall(
            task=req.task, query=req.query, locale=req.locale, max_sources=req.max_sources,
            temperature=cfg.temperature, max_tokens=cfg.max_output_tokens))
        call.add_usage(res.usage)
        call.model = res.model or cfg.model
        sources = [{"url": s["url"], "title": s.get("title") or "", "snippet": s.get("snippet")}
                   for s in res.sources if s.get("url")][: req.max_sources]
        full = {"provider": call.provider_name, "model": call.model, "summary": res.summary,
                "sources": sources, "queries": res.queries, "returned_sources": bool(sources)}
        # 카세트에는 출처까지 남긴다(재생하는 쪽 설정으로 다시 가린다)
        call.record(kp, dict(full))
        out = dict(full)
        if not cfg.return_sources:
            out["sources"], out["returned_sources"] = [], False
        return call.done(out)
