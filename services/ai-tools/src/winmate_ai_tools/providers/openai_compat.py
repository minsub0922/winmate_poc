"""OpenAI 호환 제공자 — openai SDK(AsyncOpenAI(base_url=<CAP>_BASE_URL, api_key=<CAP>_API_KEY)).

사내 vLLM · TGI · LiteLLM · Ollama 처럼 OpenAI 호환 API 를 내는 서버를 `.env` 만 바꿔 붙인다.

- LLM: chat.completions — response_format json_schema(스키마가 strict 조건을 만족하면 strict=true) · tools · tool_choice · 스트리밍
- I2T: chat.completions 에 image_url(data URI)
- T2I: images.generate(b64_json) · 참조 이미지가 있으면 images.edit(image=[참조…]) · 편집 images.edit(+mask: 투명=수정)
  - T2I_RESPONSE_FORMAT(기본 b64_json, 비우면 보내지 않음 — gpt-image 계열) · T2I_SIZE(예 1024x1024, 없으면 비율로 계산)
- 웹 검색: chat.completions 로 요약(annotations 의 url_citation 이 있으면 출처)
- 임베딩: embeddings.create
- HTTP 는 httpx.AsyncClient 를 넘겨 쓴다(프록시 · 사내 인증서 설정을 다른 서비스와 같게, 테스트는 respx).
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

import httpx
import openai
from openai import AsyncOpenAI
from PIL import Image, ImageOps

from winmate_common import env
from winmate_common.ids import new_id

from ..config import PREFIX, CapConfig
from ..errors import ProviderError, not_configured, provider_error
from ..imaging import Img, download
from ..jsonfix import openai_strict_ok, schema_name
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

T = TypeVar("T")
_clients: dict[tuple[Any, ...], AsyncOpenAI] = {}


def make_client(base_url: str | None, api_key: str | None, timeout_s: float, *, what: str) -> AsyncOpenAI:
    if not base_url:
        raise not_configured(f"{what}_BASE_URL", env=f"{what}_BASE_URL")
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = 0
    key = (base_url, api_key, timeout_s, loop_id)
    c = _clients.get(key)
    if c is None:
        if len(_clients) > 16:
            _clients.clear()
        http = httpx.AsyncClient(timeout=timeout_s, follow_redirects=True)
        c = _clients[key] = AsyncOpenAI(base_url=base_url, api_key=api_key or "not-needed", max_retries=0,
                                        timeout=timeout_s, http_client=http)
    return c


async def call_api(fn: Callable[[], Awaitable[T]], provider: str = "openai_compat") -> T:
    try:
        return await fn()
    except openai.APITimeoutError as exc:
        raise ProviderError(504, "TIMEOUT", f"{provider} 응답 시간 초과", {"provider": provider}) from exc
    except openai.APIStatusError as exc:
        raise provider_error(provider, _status_message(exc), status=exc.status_code) from exc
    except openai.APIConnectionError as exc:
        raise provider_error(provider, f"연결 실패: {exc}", retryable=True) from exc
    except openai.OpenAIError as exc:
        raise provider_error(provider, f"{type(exc).__name__}: {exc}") from exc


def _status_message(exc: openai.APIStatusError) -> str:
    body = exc.body
    if isinstance(body, dict):
        err = body.get("error", body)
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])[:500]
    return (exc.message or str(exc))[:500]


def _data_uri(img: Img) -> str:
    return f"data:{img.mime};base64,{base64.b64encode(img.data).decode()}"


def messages_from(system: str | None, messages: list[Msg]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if system:
        out.append({"role": "system", "content": system})
    for m in messages:
        if m.role == "user":
            if m.images():
                parts: list[dict[str, Any]] = []
                for p in m.parts:
                    if isinstance(p, str):
                        parts.append({"type": "text", "text": p})
                    else:
                        parts.append({"type": "image_url", "image_url": {"url": _data_uri(p)}})
                out.append({"role": "user", "content": parts})
            else:
                out.append({"role": "user", "content": m.text()})
        elif m.role == "assistant":
            msg: dict[str, Any] = {"role": "assistant", "content": m.text() or None}
            if m.tool_calls:
                msg["tool_calls"] = [{"id": tc["id"], "type": "function",
                                      "function": {"name": tc["name"], "arguments": json.dumps(tc.get("arguments") or {}, ensure_ascii=False)}}
                                     for tc in m.tool_calls]
            out.append(msg)
        elif m.role == "tool":
            msg = {"role": "tool", "tool_call_id": m.tool_call_id or "", "content": m.text()}
            if m.name:
                msg["name"] = m.name
            out.append(msg)
    return out


def _args(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        v = json.loads(raw or "{}")
    except (ValueError, TypeError):
        return {"_raw": raw}
    return v if isinstance(v, dict) else {"input": v}


def _usage(u: Any) -> dict[str, int]:
    if u is None:
        return {"input_tokens": 0, "output_tokens": 0}
    return {"input_tokens": int(getattr(u, "prompt_tokens", 0) or 0), "output_tokens": int(getattr(u, "completion_tokens", 0) or 0)}


class OpenAICompatProvider(Provider):
    name = "openai_compat"
    native_mask = True

    def available(self, cfg: CapConfig) -> bool:
        return bool(cfg.base_url)

    def client(self, cfg: CapConfig) -> AsyncOpenAI:
        return make_client(cfg.base_url, cfg.api_key, cfg.timeout_s, what=PREFIX[cfg.cap])

    # ── LLM ────────────────────────────────────────────
    def _chat_kwargs(self, cfg: CapConfig, call: LLMCall) -> dict[str, Any]:
        kw: dict[str, Any] = {
            "model": cfg.model,
            "messages": messages_from(call.system, call.messages),
            "temperature": call.temperature,
            "max_tokens": call.max_tokens,
        }
        if call.json_schema is not None:
            kw["response_format"] = {"type": "json_schema", "json_schema": {
                "name": schema_name(call.schema_name), "schema": call.json_schema, "strict": openai_strict_ok(call.json_schema)}}
        if call.tools:
            kw["tools"] = [{"type": "function", "function": {"name": t["name"], "description": t.get("description") or "",
                                                             "parameters": t.get("parameters") or {"type": "object", "properties": {}}}}
                           for t in call.tools]
            tc = call.tool_choice
            if tc in (None, "auto", "none", "required"):
                if tc:
                    kw["tool_choice"] = tc
            elif tc == "any":
                kw["tool_choice"] = "required"
            else:
                kw["tool_choice"] = {"type": "function", "function": {"name": tc}}
        return kw

    async def chat(self, cfg: CapConfig, call: LLMCall) -> LLMResult:
        client = self.client(cfg)
        kw = self._chat_kwargs(cfg, call)
        resp = await call_api(lambda: client.chat.completions.create(**kw))
        if not resp.choices:
            raise provider_error(self.name, "응답에 choices 가 없습니다")
        choice = resp.choices[0]
        msg = choice.message
        calls = [{"id": tc.id or new_id("call"), "name": tc.function.name, "arguments": _args(tc.function.arguments)}
                 for tc in (msg.tool_calls or []) if getattr(tc, "function", None) is not None]
        finish = choice.finish_reason or "stop"
        if calls:
            finish = "tool_calls"
        return LLMResult(text=msg.content or "", tool_calls=calls, finish_reason=finish, usage=_usage(resp.usage),
                         model=resp.model or cfg.model)

    async def stream(self, cfg: CapConfig, call: LLMCall) -> AsyncIterator[str | LLMResult]:
        client = self.client(cfg)
        kw = self._chat_kwargs(cfg, call)
        s = await call_api(lambda: client.chat.completions.create(**kw, stream=True))
        texts: list[str] = []
        usage = {"input_tokens": 0, "output_tokens": 0}
        finish, model = "stop", cfg.model
        try:
            async for chunk in s:
                model = getattr(chunk, "model", None) or model
                if getattr(chunk, "usage", None):
                    usage = _usage(chunk.usage)
                if not chunk.choices:
                    continue
                ch = chunk.choices[0]
                if ch.delta and ch.delta.content:
                    texts.append(ch.delta.content)
                    yield ch.delta.content
                if ch.finish_reason:
                    finish = ch.finish_reason
        except openai.APIError as exc:
            raise provider_error(self.name, str(exc)) from exc
        yield LLMResult(text="".join(texts), finish_reason=finish, usage=usage, model=model)

    # ── I2T ────────────────────────────────────────────
    async def analyze(self, cfg: CapConfig, call: I2TCall) -> LLMResult:
        msgs = [Msg(role="user", parts=[*call.images, call.prompt])]
        for role, text in call.turns:
            msgs.append(Msg(role="assistant" if role == "assistant" else "user", parts=[text]))
        llm = LLMCall(task=call.task, system=call.system, messages=msgs, temperature=call.temperature,
                      max_tokens=call.max_tokens, json_schema=call.json_schema, schema_name=call.schema_name)
        return await self.chat(cfg, llm)

    # ── T2I ────────────────────────────────────────────
    @staticmethod
    def _size(call_size: tuple[int, int]) -> str:
        return env.get("T2I_SIZE") or f"{call_size[0]}x{call_size[1]}"

    @staticmethod
    def _fmt_kw() -> dict[str, Any]:
        fmt = env.get("T2I_RESPONSE_FORMAT", "b64_json")
        return {"response_format": fmt} if fmt and fmt.lower() not in ("none", "omit") else {}

    async def _collect(self, resp: Any) -> list[GenImage]:
        out: list[GenImage] = []
        for d in resp.data or []:
            if getattr(d, "b64_json", None):
                out.append(GenImage(data=base64.b64decode(d.b64_json), mime="image/png"))
            elif getattr(d, "url", None):
                data, mime = await download(d.url)
                out.append(GenImage(data=data, mime=(mime or "image/png").split(";")[0]))
        if not out:
            raise provider_error(self.name, "이미지가 생성되지 않았습니다")
        return out

    async def generate(self, cfg: CapConfig, call: T2ICall) -> T2IResult:
        client = self.client(cfg)
        kw: dict[str, Any] = {"model": cfg.model, "prompt": call.prompt, "n": call.n, "size": self._size(call.size), **self._fmt_kw()}
        if call.refs:
            files = [(f"ref{i}.{r.img.ext}", r.img.data, r.img.mime) for i, r in enumerate(call.refs)]
            resp = await call_api(lambda: client.images.edit(image=files, **kw))
        else:
            resp = await call_api(lambda: client.images.generate(**kw))
        return T2IResult(images=await self._collect(resp), model=cfg.model)

    async def edit(self, cfg: CapConfig, call: EditCall) -> T2IResult:
        client = self.client(cfg)
        images = [("image." + call.image.ext, call.image.data, call.image.mime)]
        images += [(f"ref{i}.{r.img.ext}", r.img.data, r.img.mime) for i, r in enumerate(call.refs)]
        kw: dict[str, Any] = {"model": cfg.model, "prompt": call.prompt, "n": call.n, "size": self._size(call.size), **self._fmt_kw()}
        if call.mask is not None:
            kw["mask"] = ("mask.png", _openai_mask(call.mask), "image/png")
        image_arg: Any = images if len(images) > 1 else images[0]
        resp = await call_api(lambda: client.images.edit(image=image_arg, **kw))
        return T2IResult(images=await self._collect(resp), model=cfg.model)

    # ── 웹 검색 ─────────────────────────────────────────
    async def websearch(self, cfg: CapConfig, call: WebSearchCall) -> WebSearchResult:
        client = self.client(cfg)
        lang = "한국어" if call.locale.lower().startswith("ko") else call.locale
        messages = [
            {"role": "system", "content": f"웹 검색 결과를 바탕으로 {lang}로 사실 위주로 요약한다. 확인되지 않은 내용은 쓰지 않는다."},
            {"role": "user", "content": call.query},
        ]
        resp = await call_api(lambda: client.chat.completions.create(model=cfg.model, messages=messages,
                                                                     temperature=call.temperature, max_tokens=call.max_tokens))
        if not resp.choices:
            raise provider_error(self.name, "응답에 choices 가 없습니다")
        msg = resp.choices[0].message
        sources: list[dict[str, Any]] = []
        for ann in getattr(msg, "annotations", None) or []:
            cit = getattr(ann, "url_citation", None)
            if cit is not None and getattr(cit, "url", None):
                sources.append({"url": cit.url, "title": getattr(cit, "title", "") or ""})
        return WebSearchResult(summary=msg.content or "", sources=sources[: call.max_sources], usage=_usage(resp.usage),
                               model=resp.model or cfg.model)


def _openai_mask(mask: Img) -> bytes:
    """우리 마스크(L, 255=수정) → OpenAI 마스크(RGBA, 알파 0=수정)."""
    m = Image.open(io.BytesIO(mask.data)).convert("L")
    rgba = Image.new("RGBA", m.size, (0, 0, 0, 255))
    rgba.putalpha(ImageOps.invert(m))
    buf = io.BytesIO()
    rgba.save(buf, "PNG")
    return buf.getvalue()


async def embed(base_url: str | None, api_key: str | None, model: str, texts: list[str], timeout_s: float) -> list[list[float]]:
    client = make_client(base_url, api_key, timeout_s, what="EMBEDDING")
    resp = await call_api(lambda: client.embeddings.create(model=model, input=texts, encoding_format="float"))
    data = sorted(resp.data, key=lambda d: d.index)
    return [list(d.embedding) for d in data]
