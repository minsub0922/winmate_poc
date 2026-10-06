"""Gemini 어댑터 — 실제 google-genai SDK 가 보내는 REST 요청을 respx 로 받아 확인하고, REST 응답을 우리 형식으로 바꾸는지 본다."""
from __future__ import annotations

import base64
import io
import json
from typing import Any

from PIL import Image

from winmate_common import testing
from winmate_ai_tools.providers import gemini as gem_mod


def b64s(b: bytes) -> str:
    return base64.b64encode(b).decode()


def resp(parts: list[dict[str, Any]], *, finish: str = "STOP", usage=(12, 7, 3), grounding: dict | None = None,
         model: str = "gemini-3.1-flash-lite-001") -> dict[str, Any]:
    cand: dict[str, Any] = {"content": {"role": "model", "parts": parts}, "finishReason": finish}
    if grounding:
        cand["groundingMetadata"] = grounding
    return {"candidates": [cand], "modelVersion": model,
            "usageMetadata": {"promptTokenCount": usage[0], "candidatesTokenCount": usage[1], "thoughtsTokenCount": usage[2]}}


async def test_json_schema_request_mapping(client, gem):
    from pydantic import BaseModel, Field

    class Contact(BaseModel):
        name: str = Field(description="담당자")

    class Form(BaseModel):
        customer: str = Field(min_length=2, description="고객사")
        contact: Contact = Field(description="연락처")
        kind: str = Field(json_schema_extra={"const": "rfp"})

    gem.reply(resp([{"text": "생각 중…", "thought": True},
                    {"text": json.dumps({"customer": "삼성 호텔", "contact": {"name": "김"}, "kind": "rfp"}, ensure_ascii=False)}]))
    body = {"task": "rq.extract", "messages": [{"role": "system", "content": "추출기"}, {"role": "user", "content": "본문"}],
            "json_schema": Form.model_json_schema(), "schema_name": "Form"}
    r = await client.post("/v1/llm/chat", json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["json"]["customer"] == "삼성 호텔" and "생각" not in out["content"]
    assert out["provider"] == "gemini" and out["model"] == "gemini-3.1-flash-lite-001"
    assert out["usage"] == {"input_tokens": 12, "output_tokens": 10}   # 생각 토큰 포함
    req = gem.requests[0]
    assert gem.urls[0].endswith("/models/gemini-3.1-flash-lite:generateContent")
    assert gem.headers[0]["x-goog-api-key"] == "test-key"
    assert req["systemInstruction"]["parts"][0]["text"] == "추출기"
    assert req["contents"] == [{"role": "user", "parts": [{"text": "본문"}]}]
    gc = req["generationConfig"]
    assert gc["responseMimeType"] == "application/json" and gc["temperature"] == 0.2 and gc["maxOutputTokens"] == 4096
    assert gc["thinkingConfig"] == {"thinking_level": "LOW"} or gc["thinkingConfig"] == {"thinkingLevel": "LOW"}
    schema = gc["responseJsonSchema"]
    # Gemini 부분 집합: $ref 옆 키 제거, const → enum, minLength 제거
    assert schema["properties"]["contact"] == {"$ref": "#/$defs/Contact"}
    assert schema["properties"]["kind"]["enum"] == ["rfp"] and "minLength" not in schema["properties"]["customer"]


async def test_tools_and_thought_signature_roundtrip(client, gem):
    tools = [{"name": "get_weather", "description": "날씨", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}]
    gem.reply(resp([{"functionCall": {"name": "get_weather", "args": {"city": "서울"}}, "thoughtSignature": b64s(b"sig-1")}],
                   finish="STOP"))
    r = await client.post("/v1/llm/chat", json={"task": "sb.agent", "messages": [{"role": "user", "content": "서울 날씨"}],
                                                "tools": tools, "tool_choice": "get_weather"})
    out = r.json()
    tc = out["tool_calls"][0]
    assert out["finish_reason"] == "tool_calls" and tc["name"] == "get_weather" and tc["arguments"] == {"city": "서울"}
    req = gem.requests[0]
    decl = req["tools"][0]["functionDeclarations"][0]
    assert decl["name"] == "get_weather"
    params = decl.get("parametersJsonSchema") or decl.get("parameters_json_schema")
    assert params["properties"]["city"] == {"type": "string"}
    assert req["toolConfig"]["functionCallingConfig"] == {"mode": "ANY", "allowedFunctionNames": ["get_weather"]}

    # 두 번째 턴: 서명을 기억해 붙이고, 모르는 호출에는 대체 서명
    gem.reply(resp([{"text": "서울은 맑아요"}]))
    msgs = [{"role": "user", "content": "서울 날씨"},
            {"role": "assistant", "content": "", "tool_calls": [tc, {"id": "call_other", "name": "get_weather", "arguments": {"city": "부산"}}]},
            {"role": "tool", "tool_call_id": tc["id"], "content": '{"weather": "맑음"}'},
            {"role": "tool", "tool_call_id": "call_other", "name": "get_weather", "content": "비"}]
    out = (await client.post("/v1/llm/chat", json={"task": "sb.agent", "messages": msgs, "tools": tools})).json()
    assert out["content"] == "서울은 맑아요"
    contents = gem.requests[1]["contents"]
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    fc0, fc1 = contents[1]["parts"]
    assert fc0["functionCall"] == {"name": "get_weather", "args": {"city": "서울"}}   # 우리가 만든 id 는 보내지 않는다
    assert fc0["thoughtSignature"] == b64s(b"sig-1") and "thoughtSignature" not in fc1
    fr = contents[2]["parts"]
    assert fr[0]["functionResponse"] == {"name": "get_weather", "response": {"weather": "맑음"}}
    assert fr[1]["functionResponse"]["response"] == {"result": "비"}


async def test_gemini_issued_ids_roundtrip(client, gem):
    gem.reply(resp([{"functionCall": {"id": "gfc-7", "name": "f", "args": {}}}]))
    out = (await client.post("/v1/llm/chat", json={"task": "x.y", "messages": [{"role": "user", "content": "q"}],
                                                   "tools": [{"name": "f", "parameters": {"type": "object"}}]})).json()
    assert out["tool_calls"][0]["id"] == "gfc-7"
    gem.reply(resp([{"text": "ok"}]))
    msgs = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "", "tool_calls": out["tool_calls"]},
            {"role": "tool", "tool_call_id": "gfc-7", "content": "r"}]
    await client.post("/v1/llm/chat", json={"task": "x.y", "messages": msgs, "tools": [{"name": "f", "parameters": {"type": "object"}}]})
    contents = gem.requests[1]["contents"]
    assert contents[1]["parts"][0]["functionCall"]["id"] == "gfc-7" and contents[2]["parts"][0]["functionResponse"]["id"] == "gfc-7"


async def test_unknown_signature_uses_dummy(client, gem):
    gem.reply(resp([{"text": "ok"}]))
    msgs = [{"role": "user", "content": "q"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "call_restarted", "name": "f", "arguments": {}}]},
            {"role": "tool", "tool_call_id": "call_restarted", "content": "r"}]
    await client.post("/v1/llm/chat", json={"task": "x.y", "messages": msgs, "tools": [{"name": "f", "parameters": {"type": "object"}}]})
    part = gem.requests[0]["contents"][1]["parts"][0]
    assert base64.b64decode(part["thoughtSignature"]) == gem_mod.DUMMY_SIGNATURE


async def test_websearch_grounding(client, gem, monkeypatch):
    grounding = {"webSearchQueries": ["키오스크 시장 2026"],
                 "groundingChunks": [{"web": {"uri": "https://vertexaisearch.example/r1", "title": "news.example.com"}},
                                     {"web": {"uri": "https://vertexaisearch.example/r2", "title": "blog.example.com"}}],
                 "groundingSupports": [{"segment": {"text": "시장이 커졌다"}, "groundingChunkIndices": [0]}]}
    for _ in range(2):
        gem.reply(resp([{"text": "키오스크 시장은 성장 중이다."}], grounding=grounding, model="gemini-3.5-flash-lite"))
    req = {"task": "mi.ws", "query": "키오스크 시장", "max_sources": 5}
    out = (await client.post("/v1/websearch", json=req)).json()
    assert out["summary"] == "키오스크 시장은 성장 중이다." and out["queries"] == ["키오스크 시장 2026"]
    assert out["sources"] == [] and out["returned_sources"] is False   # 사내 API 흉내(기본)
    sent = gem.requests[0]
    assert gem.urls[0].endswith("/models/gemini-3.5-flash-lite:generateContent")
    assert sent["tools"] == [{"googleSearch": {}}] and "키오스크 시장" in sent["contents"][0]["parts"][0]["text"]

    monkeypatch.setenv("WEBSEARCH_RETURN_SOURCES", "true")
    out = (await client.post("/v1/websearch", json=req)).json()
    assert out["returned_sources"] is True
    assert out["sources"] == [{"url": "https://vertexaisearch.example/r1", "title": "news.example.com", "snippet": "시장이 커졌다"},
                              {"url": "https://vertexaisearch.example/r2", "title": "blog.example.com", "snippet": None}]


async def test_t2i_generate_request_and_save(client, gem, files, h):
    buf = io.BytesIO()
    Image.new("RGB", (1344, 768), (1, 2, 3)).save(buf, "PNG")
    gem.reply(resp([{"text": "여기 이미지"}, {"inlineData": {"mimeType": "image/png", "data": b64s(buf.getvalue())}}],
                   model="gemini-3.1-flash-lite-image"))
    ref = files.add(h.png_bytes((30, 30)))
    r = await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "호텔 로비", "aspect": "16:9", "seed": 5,
                                                    "reference_images": [{"file_id": ref, "role": "style", "strength": "low"}]})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["provider"] == "gemini" and out["model"] == "gemini-3.1-flash-lite-image" and out["fallbacks"] == []
    img = out["images"][0]
    assert abs(img["width"] / img["height"] - 16 / 9) < 0.006   # 1344x768 → 정확한 16:9 로 살짝 자름
    req = gem.requests[0]
    gc = req["generationConfig"]
    assert gc["responseModalities"] == ["TEXT", "IMAGE"] and gc["imageConfig"] == {"aspectRatio": "16:9"} and gc["seed"] == 5
    assert "thinkingConfig" not in gc
    parts = req["contents"][0]["parts"]
    assert "inlineData" in parts[0] and "style reference" in parts[1]["text"] and parts[1]["text"].startswith("호텔 로비")


async def test_i2t_inline_images(client, gem, h):
    gem.reply(resp([{"text": json.dumps({"result": "화면 1개", "boxes": [{"label": "screen", "box_2d": [0, 0, 500, 1000]}]})}]))
    out = (await client.post("/v1/i2t/analyze", json={"task": "img.d", "images": [{"data_b64": h.b64(h.png_bytes())}],
                                                       "prompt": "화면?", "want_bbox": True})).json()
    assert out["content"] == "화면 1개" and out["boxes"][0]["box"] == [0.0, 0.0, 1.0, 0.5]
    parts = gem.requests[0]["contents"][0]["parts"]
    assert parts[0]["inlineData"]["mime_type" if "mime_type" in parts[0]["inlineData"] else "mimeType"] == "image/png"
    assert gem.requests[0]["generationConfig"]["responseJsonSchema"]["required"] == ["result", "boxes"]


async def test_errors_and_retries(client, gem):
    gem.reply(status=429)
    gem.reply(status=503)
    gem.reply(resp([{"text": "드디어"}]))
    out = (await client.post("/v1/llm/chat", json={"task": "x.y", "messages": [{"role": "user", "content": "q"}]})).json()
    assert out["content"] == "드디어" and len(gem.requests) == 3

    gem.reply(status=400)
    r = await client.post("/v1/llm/chat", json={"task": "x.y", "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 502 and r.json()["error"]["code"] == "PROVIDER_ERROR" and len(gem.requests) == 4
    assert r.json()["error"]["details"]["upstream_status"] == 400


async def test_stream(client, gem):
    gem.reply_stream([{"candidates": [{"content": {"role": "model", "parts": [{"text": "안녕"}]}}]},
                      resp([{"text": "하세요"}], usage=(5, 4, 0))])
    r = await client.post("/v1/llm/stream", json={"task": "x.s", "messages": [{"role": "user", "content": "인사"}]})
    lines = [ln for ln in r.text.splitlines() if ln.startswith("data:")]
    data = [json.loads(ln[5:]) for ln in lines]
    assert [d.get("text") for d in data[:-1]] == ["안녕", "하세요"]
    assert data[-1]["content"] == "안녕하세요" and data[-1]["usage"] == {"input_tokens": 5, "output_tokens": 4}
    assert ":streamGenerateContent" in gem.urls[0]


async def test_no_key_501(client, env, monkeypatch):
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    r = await client.post("/v1/llm/chat", json={"task": "x.y", "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 501 and r.json()["error"]["code"] == "NOT_CONFIGURED"


def test_contents_merge_and_tool_names():
    from winmate_ai_tools.providers.base import Msg

    msgs = [Msg("user", ["a"]), Msg("user", ["b"]),
            Msg("assistant", [""], tool_calls=[{"id": "c1", "name": "f", "arguments": {"x": 1}}]),
            Msg("tool", ["[1,2]"], tool_call_id="c1"), Msg("user", ["다음"])]
    contents = gem_mod.contents_from(msgs)
    assert [c.role for c in contents] == ["user", "model", "user"]
    assert [p.text for p in contents[0].parts] == ["a", "b"]
    fr = contents[2].parts[0].function_response
    assert fr.name == "f" and fr.response == {"result": [1, 2]} and contents[2].parts[1].text == "다음"


async def test_fake_client_config_objects(client, env, monkeypatch):
    """SDK 클라이언트를 가짜로 바꿔 GenerateContentConfig 객체 자체를 확인한다."""
    from google.genai import types

    seen: dict[str, Any] = {}

    class Models:
        async def generate_content(self, *, model, contents, config):
            seen.update(model=model, contents=contents, config=config)
            return types.GenerateContentResponse(
                candidates=[types.Candidate(content=types.Content(role="model", parts=[
                    types.Part(text='{"ok": true}')]), finish_reason=types.FinishReason.MAX_TOKENS)],
                usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=3, candidates_token_count=2))

    class Fake:
        class aio:  # noqa: N801
            models = Models()

    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("GEMINI_THINKING_LEVEL", "minimal")
    monkeypatch.setattr(gem_mod.GeminiProvider, "client", lambda self, cfg: Fake())
    schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"]}
    tools = [{"name": "f", "description": "d", "parameters": {"type": "object", "properties": {"x": {"type": "integer", "default": 1}}}}]
    out = (await client.post("/v1/llm/chat", json={"task": "x.f", "temperature": 0.7, "max_tokens": 64, "json_schema": schema,
                                                   "tools": tools, "tool_choice": "auto",
                                                   "messages": [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"}]})).json()
    assert out["json"] == {"ok": True} and out["finish_reason"] == "length" and out["usage"] == {"input_tokens": 3, "output_tokens": 2}
    cfg = seen["config"]
    assert seen["model"] == "gemini-3.1-flash-lite"
    assert cfg.system_instruction == "sys" and cfg.temperature == 0.7 and cfg.max_output_tokens == 64
    assert cfg.response_mime_type == "application/json" and cfg.response_json_schema == schema
    decl = cfg.tools[0].function_declarations[0]
    assert decl.name == "f" and decl.parameters_json_schema == {"type": "object", "properties": {"x": {"type": "integer"}}}
    assert cfg.tool_config.function_calling_config.mode == types.FunctionCallingConfigMode.AUTO
    assert cfg.thinking_config.thinking_level == types.ThinkingLevel.MINIMAL
    assert cfg.automatic_function_calling.disable is True
