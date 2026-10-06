"""Gemini 제공자 — google-genai SDK(`client.aio.models.generate_content`).

- 키: `<CAP>_API_KEY` 가 있으면 그것, 없으면 GEMINI_API_KEY. 주소: GEMINI_BASE_URL(사내 프록시 등).
- LLM: system_instruction · temperature · max_output_tokens · response_mime_type + response_json_schema(Gemini 부분 집합으로 다듬음) ·
  function_declarations(parameters_json_schema) + tool_config · thinking_config(thinking_level=GEMINI_THINKING_LEVEL).
- Gemini 3 는 함수 호출 기록을 돌려보낼 때 thought_signature 가 필요하다. 응답의 서명을 tool_call id 로 기억해 두었다가
  다음 요청의 같은 호출에 붙이고, 모르면(재시작 등) 문서화된 대체 서명을 붙인다.
- I2T: 이미지 inline_data + 프롬프트. T2I: response_modalities=[TEXT, IMAGE] + image_config.aspect_ratio, 참조 이미지는 inline_data.
- 함수 호출 id: Gemini 가 준 id(`call_44988` 꼴)는 그대로 돌려보내고, 우리가 만든 `call_<ULID>` 만 뺀다.
- 웹 검색: tools=[google_search] → 요약 = 응답 글, 출처 = grounding_chunks.web, 검색어 = web_search_queries.
- SDK 오류 → 429 RATE_LIMITED(재시도) · 5xx PROVIDER_ERROR(재시도) · 4xx PROVIDER_ERROR · 시간 초과 504.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from winmate_common.ids import new_id

from ..config import CapConfig, gemini_thinking_level
from ..errors import ProviderError, not_configured, provider_error
from ..jsonfix import gemini_schema
from .base import (
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

log = logging.getLogger("winmate.ai_tools.gemini")

T = TypeVar("T")
DUMMY_SIGNATURE = b"skip_thought_signature_validator"
_THINKING_LEVELS = {"minimal", "low", "medium", "high"}
_FINISH = {
    "STOP": "stop", "MAX_TOKENS": "length", "SAFETY": "content_filter", "RECITATION": "content_filter",
    "BLOCKLIST": "content_filter", "PROHIBITED_CONTENT": "content_filter", "SPII": "content_filter",
    "IMAGE_SAFETY": "content_filter", "IMAGE_PROHIBITED_CONTENT": "content_filter", "MALFORMED_FUNCTION_CALL": "error",
}

_signatures: OrderedDict[str, bytes] = OrderedDict()



def remember_signature(call_id: str, sig: bytes | None) -> None:
    if not sig:
        return
    _signatures[call_id] = sig
    _signatures.move_to_end(call_id)
    while len(_signatures) > 5000:
        _signatures.popitem(last=False)


def _finish(reason: Any) -> str:
    if reason is None:
        return "stop"
    name = getattr(reason, "name", None) or str(reason)
    name = name.split(".")[-1].upper()
    return _FINISH.get(name, name.lower())


def _blob(img: Any) -> types.Part:
    return types.Part(inline_data=types.Blob(data=img.data, mime_type=img.mime))



def _tool_response(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return {"result": text}
    return value if isinstance(value, dict) else {"result": value}


_OUR_CALL_ID = re.compile(r"^call_[0-9A-HJKMNP-TV-Z]{26}$")   # winmate_common.ids.new_id("call")


def _gemini_id(call_id: str | None) -> str | None:
    """우리가 만든 id(call_<ULID>)는 Gemini 가 모르므로 빼고(이름 · 순서로 짝지음), 그 밖의 id 는 그대로 돌려보낸다.

    Gemini 도 `call_44988` 같은 id 를 주므로(실측) 접두사만으로 거르면 안 된다.
    """
    return None if not call_id or _OUR_CALL_ID.match(call_id) else call_id


def contents_from(messages: list[Msg]) -> list[types.Content]:
    contents: list[types.Content] = []
    names: dict[str, str] = {}

    def add(role: str, parts: list[types.Part]) -> None:
        if not parts:
            return
        if contents and contents[-1].role == role:
            contents[-1].parts = [*(contents[-1].parts or []), *parts]
        else:
            contents.append(types.Content(role=role, parts=parts))

    for m in messages:
        if m.role == "user":
            add("user", [types.Part(text=p) if isinstance(p, str) else _blob(p) for p in m.parts if p != ""])
        elif m.role == "assistant":
            parts: list[types.Part] = []
            if m.text():
                parts.append(types.Part(text=m.text()))
            for i, tc in enumerate(m.tool_calls or []):
                names[tc["id"]] = tc["name"]
                sig = _signatures.get(tc["id"])
                if sig is None and i == 0:
                    sig = DUMMY_SIGNATURE
                parts.append(types.Part(function_call=types.FunctionCall(name=tc["name"], args=tc.get("arguments") or {},
                                                                         id=_gemini_id(tc["id"])), thought_signature=sig))
            add("model", parts)
        elif m.role == "tool":
            name = m.name or names.get(m.tool_call_id or "") or "tool"
            add("user", [types.Part(function_response=types.FunctionResponse(
                name=name, response=_tool_response(m.text()), id=_gemini_id(m.tool_call_id)))])
    return contents


class GeminiProvider(Provider):
    name = "gemini"
    native_mask = False

    def __init__(self) -> None:
        self._clients: dict[tuple[Any, ...], genai.Client] = {}

    # ── 클라이언트 ─────────────────────────────────────
    def available(self, cfg: CapConfig) -> bool:
        return bool(cfg.gemini_key())

    def client(self, cfg: CapConfig) -> genai.Client:
        key = cfg.gemini_key()
        if not key:
            raise not_configured("GEMINI_API_KEY", capability=cfg.cap, env=f"{cfg.cap.upper()}_API_KEY 또는 GEMINI_API_KEY")
        try:
            loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            loop_id = 0
        ck = (key, cfg.gemini_base_url(), int(cfg.timeout_s * 1000), loop_id)
        c = self._clients.get(ck)
        if c is None:
            if len(self._clients) > 16:
                self._clients.clear()
            opts = types.HttpOptions(base_url=cfg.gemini_base_url(), timeout=int(cfg.timeout_s * 1000))
            c = self._clients[ck] = genai.Client(api_key=key, http_options=opts)
        return c

    async def _call(self, fn: Callable[[], Awaitable[T]]) -> T:
        try:
            return await fn()
        except genai_errors.APIError as exc:
            raise provider_error("gemini", exc.message or str(exc), status=exc.code, upstream=exc.status) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError(504, "TIMEOUT", f"Gemini 응답 시간 초과: {exc}", {"provider": "gemini"}) from exc
        except httpx.HTTPError as exc:
            raise provider_error("gemini", f"{type(exc).__name__}: {exc}", retryable=True) from exc
        except ProviderError:
            raise
        except (ValueError, TypeError) as exc:  # SDK 의 요청 검증 오류
            raise provider_error("gemini", f"{type(exc).__name__}: {exc}") from exc

    # ── 설정 ───────────────────────────────────────────
    @staticmethod
    def _thinking() -> types.ThinkingConfig | None:
        level = gemini_thinking_level()
        if not level:
            return None
        if level not in _THINKING_LEVELS:
            log.warning("GEMINI_THINKING_LEVEL=%s 는 지원하지 않습니다(minimal|low|medium|high) — 생략", level)
            return None
        return types.ThinkingConfig(thinking_level=level.upper())  # type: ignore[arg-type]

    def text_config(self, *, system: str | None, temperature: float, max_tokens: int,
                    json_schema: dict[str, Any] | None = None, tools: list[dict[str, Any]] | None = None,
                    tool_choice: str | None = None, thinking: bool = True) -> types.GenerateContentConfig:
        kw: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        }
        if system:
            kw["system_instruction"] = system
        if json_schema is not None:
            kw["response_mime_type"] = "application/json"
            kw["response_json_schema"] = gemini_schema(json_schema)
        if tools:
            decls = [types.FunctionDeclaration(name=t["name"], description=t.get("description") or None,
                                               parameters_json_schema=gemini_schema(t.get("parameters") or {"type": "object", "properties": {}}))
                     for t in tools]
            kw["tools"] = [types.Tool(function_declarations=decls)]
            mode, allowed = "AUTO", None
            if tool_choice == "none":
                mode = "NONE"
            elif tool_choice in ("required", "any"):
                mode = "ANY"
            elif tool_choice and tool_choice != "auto":
                mode, allowed = "ANY", [tool_choice]
            kw["tool_config"] = types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
                mode=mode, allowed_function_names=allowed))  # type: ignore[arg-type]
        if thinking:
            tc = self._thinking()
            if tc is not None:
                kw["thinking_config"] = tc
        return types.GenerateContentConfig(**kw)

    # ── 응답 ───────────────────────────────────────────
    @staticmethod
    def to_result(resp: types.GenerateContentResponse, model: str) -> LLMResult:
        cand = resp.candidates[0] if resp.candidates else None
        texts: list[str] = []
        calls: list[dict[str, Any]] = []
        if cand is not None and cand.content is not None:
            for p in cand.content.parts or []:
                if p.thought:
                    continue
                if p.function_call is not None:
                    cid = p.function_call.id or new_id("call")
                    remember_signature(cid, p.thought_signature)
                    calls.append({"id": cid, "name": p.function_call.name or "", "arguments": dict(p.function_call.args or {})})
                elif p.text:
                    texts.append(p.text)
        if cand is None:
            finish = "content_filter" if (resp.prompt_feedback and resp.prompt_feedback.block_reason) else "stop"
        else:
            finish = _finish(cand.finish_reason)
        if calls:
            finish = "tool_calls"
        um = resp.usage_metadata
        usage = {
            "input_tokens": int((um.prompt_token_count or 0) if um else 0),
            "output_tokens": int(((um.candidates_token_count or 0) + (um.thoughts_token_count or 0)) if um else 0),
        }
        return LLMResult(text="".join(texts), tool_calls=calls, finish_reason=finish, usage=usage,
                         model=resp.model_version or model)

    # ── LLM ────────────────────────────────────────────
    def _llm_config(self, call: LLMCall) -> types.GenerateContentConfig:
        return self.text_config(system=call.system, temperature=call.temperature, max_tokens=call.max_tokens,
                                json_schema=call.json_schema, tools=call.tools, tool_choice=call.tool_choice)

    async def chat(self, cfg: CapConfig, call: LLMCall) -> LLMResult:
        client = self.client(cfg)
        contents = contents_from(call.messages)
        config = self._llm_config(call)
        resp = await self._call(lambda: client.aio.models.generate_content(model=cfg.model, contents=contents, config=config))
        return self.to_result(resp, cfg.model)

    async def stream(self, cfg: CapConfig, call: LLMCall) -> AsyncIterator[str | LLMResult]:
        client = self.client(cfg)
        contents = contents_from(call.messages)
        config = self._llm_config(call)
        it = await self._call(lambda: client.aio.models.generate_content_stream(model=cfg.model, contents=contents, config=config))
        texts: list[str] = []
        calls: list[dict[str, Any]] = []
        usage = {"input_tokens": 0, "output_tokens": 0}
        finish, model = "stop", cfg.model
        try:
            async for chunk in it:
                r = self.to_result(chunk, cfg.model)
                if r.text:
                    texts.append(r.text)
                    yield r.text
                calls += r.tool_calls
                if r.usage["input_tokens"] or r.usage["output_tokens"]:
                    usage = r.usage
                if chunk.candidates and chunk.candidates[0].finish_reason is not None:
                    finish = r.finish_reason
                model = r.model or model
        except genai_errors.APIError as exc:
            raise provider_error("gemini", exc.message or str(exc), status=exc.code) from exc
        except httpx.TimeoutException as exc:
            raise ProviderError(504, "TIMEOUT", f"Gemini 응답 시간 초과: {exc}", {"provider": "gemini"}) from exc
        except httpx.HTTPError as exc:
            raise provider_error("gemini", f"{type(exc).__name__}: {exc}") from exc
        yield LLMResult(text="".join(texts), tool_calls=calls, finish_reason="tool_calls" if calls else finish,
                        usage=usage, model=model)

    # ── I2T ────────────────────────────────────────────
    async def analyze(self, cfg: CapConfig, call: I2TCall) -> LLMResult:
        client = self.client(cfg)
        contents = [types.Content(role="user", parts=[*(_blob(i) for i in call.images), types.Part(text=call.prompt)])]
        for role, text in call.turns:
            contents.append(types.Content(role="model" if role == "assistant" else "user", parts=[types.Part(text=text)]))
        config = self.text_config(system=call.system, temperature=call.temperature, max_tokens=call.max_tokens,
                                  json_schema=call.json_schema)
        resp = await self._call(lambda: client.aio.models.generate_content(model=cfg.model, contents=contents, config=config))
        return self.to_result(resp, cfg.model)

    # ── T2I ────────────────────────────────────────────
    def _image_config(self, aspect: str, seed: int | None) -> types.GenerateContentConfig:
        kw: dict[str, Any] = {
            "response_modalities": ["TEXT", "IMAGE"],
            "image_config": types.ImageConfig(aspect_ratio=aspect),
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        }
        if seed is not None:
            kw["seed"] = seed
        return types.GenerateContentConfig(**kw)

    async def _images(self, cfg: CapConfig, parts: list[types.Part], aspect: str, seed: int | None, n: int) -> T2IResult:
        client = self.client(cfg)
        out: list[GenImage] = []
        texts: list[str] = []
        model = cfg.model
        for i in range(n):
            config = self._image_config(aspect, None if seed is None else seed + i)
            contents = [types.Content(role="user", parts=parts)]
            resp = await self._call(lambda: client.aio.models.generate_content(model=cfg.model, contents=contents, config=config))
            model = resp.model_version or model
            cand = resp.candidates[0] if resp.candidates else None
            got = 0
            for p in (cand.content.parts if cand and cand.content else None) or []:
                if p.inline_data is not None and p.inline_data.data:
                    out.append(GenImage(data=p.inline_data.data, mime=p.inline_data.mime_type or "image/png"))
                    got += 1
                elif p.text and not p.thought:
                    texts.append(p.text)
            if not got:
                reason = _finish(cand.finish_reason) if cand else "blocked"
                raise provider_error("gemini", f"이미지가 생성되지 않았습니다({reason})", text=" ".join(texts)[:500],
                                     finish_reason=reason)
        return T2IResult(images=out, text=" ".join(texts), model=model)

    async def generate(self, cfg: CapConfig, call: T2ICall) -> T2IResult:
        parts = [*(_blob(r.img) for r in call.refs), types.Part(text=call.prompt)]
        return await self._images(cfg, parts, call.aspect, call.seed, call.n)

    async def edit(self, cfg: CapConfig, call: EditCall) -> T2IResult:
        parts = [_blob(call.image), *(_blob(r.img) for r in call.refs), types.Part(text=call.prompt)]
        return await self._images(cfg, parts, call.aspect, None, call.n)

    # ── 웹 검색 ─────────────────────────────────────────
    async def websearch(self, cfg: CapConfig, call: WebSearchCall) -> WebSearchResult:
        client = self.client(cfg)
        lang = "한국어" if call.locale.lower().startswith("ko") else call.locale
        prompt = (
            f"다음 질문에 대해 Google 검색으로 최신 공개 정보를 찾아 {lang}로 사실 위주로 요약하라. "
            "수치 · 날짜 · 회사명은 검색 결과에 있는 그대로 쓰고, 확인되지 않은 내용은 쓰지 마라.\n\n"
            f"질문: {call.query}"
        )
        kw: dict[str, Any] = {
            "tools": [types.Tool(google_search=types.GoogleSearch())],
            "temperature": call.temperature,
            "max_output_tokens": call.max_tokens,
        }
        tc = self._thinking()
        if tc is not None:
            kw["thinking_config"] = tc
        config = types.GenerateContentConfig(**kw)
        resp = await self._call(lambda: client.aio.models.generate_content(model=cfg.model, contents=prompt, config=config))
        r = self.to_result(resp, cfg.model)
        cand = resp.candidates[0] if resp.candidates else None
        gm = cand.grounding_metadata if cand else None
        sources: list[dict[str, Any]] = []
        queries: list[str] = list(gm.web_search_queries or []) if gm else []
        if gm and gm.grounding_chunks:
            snippets: dict[int, str] = {}
            for sup in gm.grounding_supports or []:
                text = (sup.segment.text if sup.segment else None) or ""
                for idx in sup.grounding_chunk_indices or []:
                    if text and idx not in snippets:
                        snippets[idx] = text[:300]
            seen: set[str] = set()
            for i, ch in enumerate(gm.grounding_chunks):
                web = ch.web
                if web is None or not web.uri or web.uri in seen:
                    continue
                seen.add(web.uri)
                sources.append({"url": web.uri, "title": web.title or web.domain or "", "snippet": snippets.get(i)})
        return WebSearchResult(summary=r.text, sources=sources[: call.max_sources], queries=queries, usage=r.usage, model=r.model)
