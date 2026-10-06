"""LLM — POST /v1/llm/chat · /v1/llm/stream.

흐름: 기밀 정책(403) → 문맥 길이(413) → 이미지 불러오기 → [replay] 카세트 → 한도(429) → 제공자 호출 → JSON 검증/수리 → [record]

대체 경로(fallback 값)
- json_schema + LLM_SUPPORTS_JSON_SCHEMA=true  → 제공자 JSON 모드("none"). 결과는 원래 스키마로 다시 검증
- json_schema + LLM_SUPPORTS_JSON_SCHEMA=false → 스키마를 시스템 지시에 넣고 본문에서 JSON 을 꺼냄("json_parse")
- 검증 실패 → 오류를 알려 주고 최대 2번 다시 받음("json_repair"), 그래도 실패 → 422 SCHEMA_MISMATCH
- tools + LLM_SUPPORTS_TOOLS=false → ReAct 텍스트 규약으로 tool_calls 를 만듦("react")
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import replace
from typing import Any

from winmate_common.ai import estimate_tokens
from winmate_common.errors import ApiError

from . import config, imaging, jsonfix, limits, react
from .errors import schema_mismatch
from .providers.base import LLMCall, LLMResult, Msg
from .runtime import Call, finish_call, track
from .schemas import ChatMessage, ChatRequest, ImagePart

log = logging.getLogger("winmate.ai_tools.llm")

MAX_REPAIRS = 2


# ── 준비 ───────────────────────────────────────────────────

def check_context(cfg: config.CapConfig, req: ChatRequest) -> None:
    texts: list[str] = []
    for m in req.messages:
        if isinstance(m.content, str):
            texts.append(m.content)
        else:
            texts += [p.text for p in m.content if getattr(p, "type", None) == "text"]
        for tc in m.tool_calls or []:
            texts.append(json.dumps(tc.arguments, ensure_ascii=False))
    n = estimate_tokens("\n".join(texts))
    if n > cfg.max_input_tokens:
        raise ApiError(413, "CONTEXT_TOO_LONG",
                       f"입력이 너무 깁니다(추정 {n:,} 토큰 > 한도 {cfg.max_input_tokens:,}). 자료를 나누거나 줄여 주세요",
                       {"estimated_tokens": n, "max_input_tokens": cfg.max_input_tokens})


async def _image(part: ImagePart, max_side: int) -> imaging.Img:
    raw, _ = await imaging.load_raw(part.model_dump(exclude_none=True))
    return await asyncio.to_thread(imaging.prepare, raw, max_side)


async def resolve_messages(messages: list[ChatMessage], max_side: int) -> tuple[list[str], list[Msg]]:
    """시스템 지시와 대화로 나누고, 이미지 조각을 불러온다."""
    systems: list[str] = []
    msgs: list[Msg] = []
    for m in messages:
        parts: list[str | imaging.Img] = []
        if isinstance(m.content, str):
            if m.content:
                parts.append(m.content)
        else:
            for p in m.content:
                if isinstance(p, ImagePart):
                    parts.append(await _image(p, max_side))
                elif p.text:
                    parts.append(p.text)
        if m.role == "system":
            systems.append("\n".join(x for x in parts if isinstance(x, str)))
            continue
        msgs.append(Msg(role=m.role, parts=parts,
                        tool_calls=[tc.model_dump() for tc in m.tool_calls] if m.tool_calls else None,
                        tool_call_id=m.tool_call_id, name=m.name))
    return systems, msgs


def key_payload(req: ChatRequest, systems: list[str], msgs: list[Msg]) -> dict[str, Any]:
    """카세트 키: 메시지(이미지는 내용 해시, tool_call id 는 순번) + 결과에 영향을 주는 옵션."""
    ids: dict[str, str] = {}

    def norm_id(x: str | None) -> str | None:
        if x is None:
            return None
        if x not in ids:
            ids[x] = f"tc{len(ids)}"
        return ids[x]

    conv: list[dict[str, Any]] = [{"role": "system", "content": [s]} for s in systems]
    for m in msgs:
        conv.append({
            "role": m.role,
            "content": [p if isinstance(p, str) else {"image": p.sha256} for p in m.parts],
            "tool_calls": [{"id": norm_id(tc["id"]), "name": tc["name"], "arguments": tc.get("arguments")}
                           for tc in m.tool_calls] if m.tool_calls else None,
            "tool_call_id": norm_id(m.tool_call_id), "name": m.name,
        })
    return {"messages": conv, "json_schema": req.json_schema,
            "tools": [t.model_dump() for t in req.tools] if req.tools else None,
            "tool_choice": req.tool_choice, "temperature": req.temperature, "max_tokens": req.max_tokens}


def react_history(msgs: list[Msg]) -> list[Msg]:
    """앞선 tool_calls · tool 결과를 ReAct 텍스트로(도구를 지원하지 않는 모델용)."""
    out: list[Msg] = []
    names: dict[str, str] = {}
    for m in msgs:
        if m.role == "assistant" and m.tool_calls:
            for tc in m.tool_calls:
                names[tc["id"]] = tc["name"]
            text = "\n".join([m.text(), *(react.render_call(tc["name"], tc.get("arguments") or {}) for tc in m.tool_calls)]).strip()
            out.append(Msg(role="assistant", parts=[text]))
        elif m.role == "tool":
            obs = react.render_observation(m.name or names.get(m.tool_call_id or ""), m.tool_call_id, m.text())
            if out and out[-1].role == "user" and out[-1].text().startswith("Observation"):
                out[-1].parts.append(obs)
            else:
                out.append(Msg(role="user", parts=[obs]))
        else:
            out.append(m)
    return out


def build_call(cfg: config.CapConfig, req: ChatRequest, systems: list[str], msgs: list[Msg]) -> tuple[LLMCall, str]:
    schema = req.json_schema
    want_json = schema is not None
    native_json = want_json and cfg.supports_json_schema
    tools = [t.model_dump() for t in req.tools or []]
    native_tools = bool(tools) and cfg.supports_tools
    react_mode = bool(tools) and not native_tools
    system_parts = [s for s in systems if s]
    conv = msgs
    if react_mode:
        conv = react_history(msgs)
        if req.tool_choice != "none":
            system_parts.append(react.system_prompt(tools, req.tool_choice))
    if want_json and not native_json:
        system_parts.append(jsonfix.schema_instruction(schema or {}, req.schema_name))
    if not conv and system_parts:
        # 시스템 지시만 있는 요청: 대화가 비면 받지 않는 제공자가 있어 사용자 메시지로 보낸다
        conv = [Msg(role="user", parts=["\n\n".join(system_parts)])]
        system_parts = []
    max_tokens = min(req.max_tokens, cfg.max_output_tokens) if req.max_tokens else cfg.max_output_tokens
    call = LLMCall(
        task=req.task, system="\n\n".join(system_parts) or None, messages=conv,
        temperature=req.temperature if req.temperature is not None else cfg.temperature, max_tokens=max_tokens,
        json_schema=schema if native_json else None, schema_name=req.schema_name or "Output",
        tools=tools if native_tools else None, tool_choice=req.tool_choice if native_tools else None,
        want_json=want_json, user_schema=schema, react_tools=tools if react_mode else None,
    )
    fallback = "react" if react_mode else ("json_parse" if want_json and not native_json else "none")
    return call, fallback


# ── 실행 ───────────────────────────────────────────────────

async def run(call: Call, cfg: config.CapConfig, provider: Any, req: ChatRequest, llm_call: LLMCall,
              first: LLMResult | None = None) -> dict[str, Any]:
    """제공자 호출 + ReAct 해석 + JSON 검증/수리 → API 응답 dict(call_id · latency 제외)."""
    res = first if first is not None else await call.invoke(provider.chat, cfg, llm_call)
    call.add_usage(res.usage)
    call.model = res.model or cfg.model
    names = {t["name"] for t in (llm_call.react_tools or [])}
    content, tool_calls = res.text, res.tool_calls
    if llm_call.react_tools and not tool_calls:
        parsed = react.parse(res.text, names)
        content, tool_calls = parsed.content, parsed.tool_calls
    json_value: Any = None
    schema = req.json_schema
    if schema is not None and not tool_calls:
        value, errors = jsonfix.parse_and_validate(content, schema, pre=res.json_value)
        cur = llm_call
        repairs = 0
        while errors and not res.authoritative and repairs < MAX_REPAIRS:
            repairs += 1
            call.set_fallback("json_repair")
            cur = replace(cur, messages=[*cur.messages, Msg(role="assistant", parts=[res.text or "(빈 응답)"]),
                                         Msg(role="user", parts=[jsonfix.repair_message(errors)])])
            res = await call.invoke(provider.chat, cfg, cur)
            call.add_usage(res.usage)
            content = res.text
            if llm_call.react_tools:
                content = react.parse(res.text, names).content or res.text
            value, errors = jsonfix.parse_and_validate(content, schema, pre=res.json_value)
        if errors:
            if res.authoritative and value is not None:
                log.warning("mock 고정 응답이 스키마와 맞지 않습니다(%s): %s", req.task, errors[:3])
            else:
                raise schema_mismatch(errors, res.text, attempts=repairs + 1, finish_reason=res.finish_reason)
        json_value = value
    return {
        "provider": call.provider_name, "model": call.model, "content": content, "json": json_value,
        "tool_calls": tool_calls, "finish_reason": "tool_calls" if tool_calls else res.finish_reason,
        "usage": dict(call.usage), "fallback": call.fallback or "none",
    }


async def chat(req: ChatRequest) -> dict[str, Any]:
    cfg = config.load("llm")
    async with track("llm", req.task, request=req.model_dump(exclude_none=True), confidential=req.confidential, cfg=cfg) as call:
        call.check_policy()
        check_context(cfg, req)
        systems, msgs = await resolve_messages(req.messages, config.load("i2t").max_image_side_px)
        kp = key_payload(req, systems, msgs)
        hit = await call.replay(kp)
        if hit is not None:
            return call.done(dict(hit["response"]))
        await call.acquire()
        provider = call.provider()
        llm_call, fallback = build_call(cfg, req, systems, msgs)
        call.set_fallback(fallback)
        out = await run(call, cfg, provider, req, llm_call)
        call.record(kp, out)
        return call.done(out)


# ── 스트리밍 ────────────────────────────────────────────────

async def stream(req: ChatRequest) -> AsyncIterator[dict[str, Any]]:
    """사전 검사(정책 · 길이 · 한도)는 여기서 바로 하고(오류는 HTTP 오류), SSE 이벤트 생성기를 돌려준다."""
    cfg = config.load("llm")
    call = Call("llm", req.task, request=req.model_dump(exclude_none=True), confidential=req.confidential, cfg=cfg, units=1)
    try:
        call.check_policy()
        check_context(cfg, req)
        systems, msgs = await resolve_messages(req.messages, config.load("i2t").max_image_side_px)
        kp = key_payload(req, systems, msgs)
        hit = await call.replay(kp)
        if hit is None:
            await call.acquire()
        provider = call.provider() if hit is None else None
    except ApiError as exc:
        await finish_call(call, "error", {"status": exc.status, "code": exc.code, "message": exc.message})
        raise
    llm_call, fallback = build_call(cfg, req, systems, msgs)
    call.set_fallback(fallback)
    native_stream = hit is None and cfg.supports_streaming and not req.json_schema and not req.tools
    return _events(call, cfg, provider, req, llm_call, kp, hit, native_stream)


async def _events(call: Call, cfg: config.CapConfig, provider: Any, req: ChatRequest, llm_call: LLMCall,
                  kp: dict[str, Any], hit: dict[str, Any] | None, native_stream: bool) -> AsyncIterator[dict[str, Any]]:
    status, error = "ok", None
    try:
        if hit is not None:
            out = call.done(dict(hit["response"]))
            if out.get("content"):
                yield {"event": "delta", "data": {"text": out["content"]}}
        elif not native_stream:
            out = await run(call, cfg, provider, req, llm_call)
            call.record(kp, out)
            out = call.done(out)
            if out.get("content"):
                yield {"event": "delta", "data": {"text": out["content"]}}
        else:
            final: LLMResult | None = None
            call.attempts += 1
            loop = asyncio.get_running_loop()
            deadline = loop.time() + cfg.timeout_s
            agen = provider.stream(cfg, llm_call).__aiter__()
            try:
                async with limits.semaphore(cfg):
                    while True:
                        remaining = deadline - loop.time()
                        if remaining <= 0:
                            raise TimeoutError
                        try:
                            # yield 를 제한 시간 범위 밖에 두려고 조각마다 wait_for
                            item = await asyncio.wait_for(agen.__anext__(), timeout=remaining)
                        except StopAsyncIteration:
                            break
                        if isinstance(item, LLMResult):
                            final = item
                        elif item:
                            yield {"event": "delta", "data": {"text": item}}
            finally:
                await agen.aclose()
            final = final or LLMResult()
            out = await run(call, cfg, provider, req, llm_call, first=final)
            call.record(kp, out)
            out = call.done(out)
        done = {"content": out.get("content", ""), "usage": out.get("usage"), "call_id": call.id,
                "provider": out.get("provider"), "model": out.get("model"), "finish_reason": out.get("finish_reason"),
                "latency_ms": out.get("latency_ms")}
        if out.get("json") is not None:
            done["json"] = out["json"]
        if out.get("tool_calls"):
            done["tool_calls"] = out["tool_calls"]
        yield {"event": "done", "data": done}
    except ApiError as exc:
        status, error = "error", {"status": exc.status, "code": exc.code, "message": exc.message}
        yield {"event": "error", "data": exc.to_body()["error"]}
    except TimeoutError:
        status, error = "error", {"status": 504, "code": "TIMEOUT", "message": "스트리밍 시간 초과"}
        yield {"event": "error", "data": {"code": "TIMEOUT", "message": f"llm 스트리밍이 {cfg.timeout_s:g}초 안에 끝나지 않았습니다", "details": {}}}
    except (asyncio.CancelledError, GeneratorExit):
        status = "canceled"
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("스트리밍 오류")
        status, error = "error", {"status": 500, "code": "INTERNAL", "message": f"{type(exc).__name__}: {exc}"}
        yield {"event": "error", "data": {"code": "INTERNAL", "message": "서버 내부 오류", "details": {"type": type(exc).__name__}}}
    finally:
        await finish_call(call, status, error)
