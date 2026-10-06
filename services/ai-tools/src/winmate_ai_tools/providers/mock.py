"""mock 제공자 — 네트워크 없이 결정적인 응답(MODEL_MODE=mock, 또는 `<CAP>_PROVIDER=mock`).

- `mocks/ai-tools/<task>.json` 이 있으면 그 내용(fixtures.py), 없으면
  - LLM + json_schema → 스키마 가짜 값(faker.py), 텍스트 → "[mock:<task>] <마지막 사용자 메시지 앞부분>"
  - 도구 → 고정 응답에 tool_calls 가 있을 때만 호출
  - I2T → 스키마 가짜 값 또는 텍스트, want_bbox 면 박스 2개
  - T2I → Pillow 로 그린 PNG(정확한 비율, 긴 변 T2I_MAX_SIDE_PX), 편집 → 색 반전 + 지시문 글자
  - 웹 검색 → 질의를 담은 요약 + example.com 출처(WEBSEARCH_RETURN_SOURCES=true 일 때만 밖으로 나간다)
"""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Any

from winmate_common.ai import estimate_tokens
from winmate_common.ids import new_id

from .. import faker, fixtures, imaging
from ..config import CapConfig
from .base import (
    NOTSET,
    EditCall,
    GenImage,
    I2TCall,
    LLMCall,
    LLMResult,
    Msg,
    Provider,
    T2ICall,
    T2IResult,
    WebSearchCall,
    WebSearchResult,
)

DEFAULT_BOXES = [
    {"label": "[mock] 객체 1", "box": [0.1, 0.12, 0.45, 0.62], "score": 0.9, "image_index": 0},
    {"label": "[mock] 객체 2", "box": [0.55, 0.3, 0.92, 0.88], "score": 0.8, "image_index": 0},
]


def _snippet(text: str, n: int = 60) -> str:
    s = re.sub(r"\s+", " ", text or "").strip()
    return s if len(s) <= n else s[:n] + "…"


def mock_text(task: str, messages: list[Msg]) -> str:
    last = next((m.text() for m in reversed(messages) if m.role == "user" and m.text()), "")
    return f"[mock:{task}] {_snippet(last) or '응답'}"


def _usage(prompt: str, out: str) -> dict[str, int]:
    return {"input_tokens": estimate_tokens(prompt), "output_tokens": estimate_tokens(out)}


def _box(b: dict[str, Any]) -> dict[str, Any]:
    box = [float(x) for x in (b.get("box") or [0, 0, 1, 1])][:4]
    return {"label": str(b.get("label", "")), "box": box, "score": b.get("score"), "image_index": int(b.get("image_index", 0))}


class MockProvider(Provider):
    name = "mock"
    native_mask = True

    # ── LLM ────────────────────────────────────────────
    async def chat(self, cfg: CapConfig, call: LLMCall) -> LLMResult:
        prompt = "\n".join([call.system or "", *(m.text() for m in call.messages)])
        fx = fixtures.next_response(call.task, prompt)
        if fx is not None:
            if fx.get("tool_calls") and (call.tools or call.react_tools):
                calls = [{"id": tc.get("id") or new_id("call"), "name": tc["name"], "arguments": tc.get("arguments") or {}}
                         for tc in fx["tool_calls"] if isinstance(tc, dict) and tc.get("name")]
                content = str(fx.get("content") or "")
                return LLMResult(text=content, tool_calls=calls, finish_reason="tool_calls", usage=_usage(prompt, content),
                                 model=cfg.model, authoritative=True)
            if "json" in fx:
                text = json.dumps(fx["json"], ensure_ascii=False)
                return LLMResult(text=text, json_value=fx["json"] if call.want_json else NOTSET, usage=_usage(prompt, text),
                                 model=cfg.model, authoritative=True)
            if "content" in fx:
                text = str(fx["content"])
                return LLMResult(text=text, usage=_usage(prompt, text), model=cfg.model, authoritative=True)
        if call.want_json and call.user_schema is not None:
            value = faker.fake(call.user_schema)
            text = json.dumps(value, ensure_ascii=False)
            return LLMResult(text=text, json_value=value, usage=_usage(prompt, text), model=cfg.model, authoritative=True)
        text = mock_text(call.task, call.messages)
        return LLMResult(text=text, usage=_usage(prompt, text), model=cfg.model)

    async def stream(self, cfg: CapConfig, call: LLMCall) -> AsyncIterator[str | LLMResult]:
        res = await self.chat(cfg, call)
        text = res.text
        step = max(1, len(text) // 3)
        for i in range(0, len(text), step):
            yield text[i:i + step]
        yield res

    # ── I2T ────────────────────────────────────────────
    async def analyze(self, cfg: CapConfig, call: I2TCall) -> LLMResult:
        prompt = call.user_prompt or call.prompt
        fx = fixtures.next_response(call.task, "\n".join([call.system or "", call.prompt]))
        value: Any = NOTSET
        text: str | None = None
        boxes = None
        if fx is not None:
            if call.want_bbox and isinstance(fx.get("boxes"), list):
                boxes = [_box(b) for b in fx["boxes"] if isinstance(b, dict)]
            if "json" in fx:
                value = fx["json"]
                text = json.dumps(value, ensure_ascii=False)
            elif "content" in fx:
                text = str(fx["content"])
        if text is None:
            if call.user_schema is not None:
                value = faker.fake(call.user_schema)
                text = json.dumps(value, ensure_ascii=False)
            else:
                text = f"[mock:{call.task}] 이미지 {len(call.images)}장: {_snippet(prompt)}"
        if call.want_bbox and boxes is None:
            boxes = [dict(b) for b in DEFAULT_BOXES]
        return LLMResult(text=text, json_value=value if call.user_schema is not None else NOTSET,
                         boxes=boxes if call.want_bbox else None, usage=_usage(prompt, text), model=cfg.model,
                         authoritative=True)

    # ── T2I ────────────────────────────────────────────
    async def generate(self, cfg: CapConfig, call: T2ICall) -> T2IResult:
        fixtures.next_response(call.task, call.prompt)   # 오류 흉내({"error": …})만 쓴다
        refs = [r.img.pil() for r in call.refs]
        out = []
        for i in range(call.n):
            im = await asyncio.to_thread(imaging.mock_generate, call.prompt, call.ratio, max(call.size),
                                         seed=f"{call.task}|{call.prompt}|{call.seed}|{i}", refs=refs)
            data, mime = await asyncio.to_thread(imaging.encode, im, "PNG")
            out.append(GenImage(data=data, mime=mime))
        return T2IResult(images=out, model=cfg.model)

    async def edit(self, cfg: CapConfig, call: EditCall) -> T2IResult:
        fixtures.next_response(call.task, call.prompt)
        base = call.image.pil()
        out = []
        for i in range(call.n):
            im = await asyncio.to_thread(imaging.mock_edit, base, call.prompt + (f" #{i + 1}" if i else ""))
            data, mime = await asyncio.to_thread(imaging.encode, im, "PNG")
            out.append(GenImage(data=data, mime=mime))
        return T2IResult(images=out, model=cfg.model)

    # ── 웹 검색 ─────────────────────────────────────────
    async def websearch(self, cfg: CapConfig, call: WebSearchCall) -> WebSearchResult:
        fx = fixtures.next_response(call.task, call.query)
        if fx is not None and ("summary" in fx or "content" in fx):
            summary = str(fx.get("summary") or fx.get("content") or "")
            sources = [s for s in fx.get("sources") or [] if isinstance(s, dict) and s.get("url")]
            queries = [str(q) for q in fx.get("queries") or [call.query]]
        else:
            slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", call.query).strip("-")[:40] or "query"
            summary = f"[mock:{call.task}] '{call.query}' 에 대한 웹 검색 요약입니다(mock — 실제 검색 결과가 아님)."
            sources = [{"url": f"https://example.com/mock/{slug}/{i}", "title": f"[mock] {call.query} 출처 {i}",
                        "snippet": f"[mock] {call.query} 관련 내용 {i}"} for i in range(1, 4)]
            queries = [call.query]
        return WebSearchResult(summary=summary, sources=sources[: call.max_sources], queries=queries,
                               usage=_usage(call.query, summary), model=cfg.model)
