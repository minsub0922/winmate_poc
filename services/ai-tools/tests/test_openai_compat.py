"""OpenAI 호환 제공자(사내망 이전용) — respx 로 /chat/completions · /images · /embeddings 를 흉내 낸다."""
from __future__ import annotations

import base64
import io
import json
from typing import Any

import httpx
import numpy as np
import pytest
import respx
from PIL import Image

from winmate_common import testing

BASE = "http://llm.internal/v1"


def completion(content: str | None = "ok", *, tool_calls: list[dict] | None = None, finish: str = "stop",
               usage=(11, 7), annotations: list | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    if annotations:
        msg["annotations"] = annotations
    return {"id": "cmpl-1", "object": "chat.completion", "created": 1, "model": "internal-llm-7b",
            "choices": [{"index": 0, "message": msg, "finish_reason": finish}],
            "usage": {"prompt_tokens": usage[0], "completion_tokens": usage[1], "total_tokens": sum(usage)}}


class Upstream:
    def __init__(self, router: respx.Router):
        self.calls: list[tuple[str, httpx.Request]] = []
        self.queue: dict[str, list[httpx.Response]] = {"chat": [], "gen": [], "edit": [], "emb": []}
        for name, path in (("chat", "/chat/completions"), ("gen", "/images/generations"), ("edit", "/images/edits"),
                           ("emb", "/embeddings")):
            router.post(BASE + path).mock(side_effect=self._mk(name))

    def _mk(self, name: str):
        def handler(request: httpx.Request) -> httpx.Response:
            self.calls.append((name, request))
            return self.queue[name].pop(0)

        return handler

    def push(self, name: str, body: Any = None, status: int = 200, **kw: Any) -> None:
        if status >= 400:
            self.queue[name].append(httpx.Response(status, json={"error": {"message": f"bad {status}", "type": "x"}}))
        elif "text" in kw:
            self.queue[name].append(httpx.Response(200, text=kw["text"], headers={"content-type": "text/event-stream"}))
        else:
            self.queue[name].append(httpx.Response(200, json=body))

    def body(self, i: int) -> dict[str, Any]:
        return json.loads(self.calls[i][1].content)


@pytest.fixture
def oai(env, monkeypatch):
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    for cap in ("LLM", "I2T", "T2I", "WEBSEARCH"):
        monkeypatch.setenv(f"{cap}_PROVIDER", "openai_compat")
        monkeypatch.setenv(f"{cap}_BASE_URL", BASE)
        monkeypatch.setenv(f"{cap}_API_KEY", "sk-internal")
        monkeypatch.setenv(f"{cap}_MODEL", f"internal-{cap.lower()}")
    with respx.mock(assert_all_called=False) as router:
        yield Upstream(router)


async def test_chat_json_schema(client, oai):
    from pydantic import BaseModel

    class Out(BaseModel):
        name: str

    oai.push("chat", completion('{"name": "삼성"}'))
    r = await client.post("/v1/llm/chat", json={"task": "rq.x", "messages": [{"role": "system", "content": "S"},
                                                                           {"role": "user", "content": "U"}],
                                                "json_schema": Out.model_json_schema(), "schema_name": "출력 Out", "max_tokens": 100})
    out = r.json()
    assert r.status_code == 200 and out["json"] == {"name": "삼성"} and out["provider"] == "openai_compat"
    assert out["model"] == "internal-llm-7b" and out["usage"] == {"input_tokens": 11, "output_tokens": 7}
    name, req = oai.calls[0]
    assert req.headers["authorization"] == "Bearer sk-internal"
    body = oai.body(0)
    assert body["model"] == "internal-llm" and body["max_tokens"] == 100 and body["temperature"] == 0.2
    assert body["messages"] == [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
    rf = body["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["name"] == "Out" and rf["json_schema"]["strict"] is False

    strict = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"], "additionalProperties": False}
    oai.push("chat", completion('{"a": "x"}'))
    await client.post("/v1/llm/chat", json={"task": "rq.x", "messages": [{"role": "user", "content": "U"}], "json_schema": strict})
    assert oai.body(1)["response_format"]["json_schema"]["strict"] is True


async def test_chat_tools_and_images(client, oai, h):
    oai.push("chat", completion(None, finish="tool_calls", tool_calls=[
        {"id": "tc_1", "type": "function", "function": {"name": "lookup", "arguments": '{"q": "QMC"}'}}]))
    tools = [{"name": "lookup", "description": "KB", "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}}]
    msg = {"role": "user", "content": [{"type": "text", "text": "이 제품?"},
                                       {"type": "image", "data_b64": h.b64(h.png_bytes((8, 8))), "mime": "image/png"}]}
    out = (await client.post("/v1/llm/chat", json={"task": "sp.find", "messages": [msg], "tools": tools, "tool_choice": "lookup"})).json()
    assert out["tool_calls"] == [{"id": "tc_1", "name": "lookup", "arguments": {"q": "QMC"}}] and out["finish_reason"] == "tool_calls"
    body = oai.body(0)
    assert body["tools"] == [{"type": "function", "function": {"name": "lookup", "description": "KB", "parameters": tools[0]["parameters"]}}]
    assert body["tool_choice"] == {"type": "function", "function": {"name": "lookup"}}
    parts = body["messages"][0]["content"]
    assert parts[0] == {"type": "text", "text": "이 제품?"} and parts[1]["image_url"]["url"].startswith("data:image/png;base64,")

    # 다음 턴: assistant tool_calls · tool 결과 형식
    oai.push("chat", completion("QMC 는 사이니지입니다"))
    msgs = [{"role": "user", "content": "이 제품?"},
            {"role": "assistant", "content": "", "tool_calls": out["tool_calls"]},
            {"role": "tool", "tool_call_id": "tc_1", "name": "lookup", "content": "사이니지"}]
    await client.post("/v1/llm/chat", json={"task": "sp.find", "messages": msgs, "tools": tools})
    sent = oai.body(1)["messages"]
    assert sent[1] == {"role": "assistant", "content": None, "tool_calls": [
        {"id": "tc_1", "type": "function", "function": {"name": "lookup", "arguments": '{"q": "QMC"}'}}]}
    assert sent[2] == {"role": "tool", "tool_call_id": "tc_1", "content": "사이니지", "name": "lookup"}


async def test_stream(client, oai):
    chunks = [{"id": "c", "object": "chat.completion.chunk", "created": 1, "model": "internal-llm-7b",
               "choices": [{"index": 0, "delta": {"content": t}, "finish_reason": None}]} for t in ("안", "녕")]
    chunks.append({"id": "c", "object": "chat.completion.chunk", "created": 1, "model": "internal-llm-7b",
                   "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
    oai.push("chat", text="".join(f"data: {json.dumps(c)}\n\n" for c in chunks) + "data: [DONE]\n\n")
    r = await client.post("/v1/llm/stream", json={"task": "x.s", "messages": [{"role": "user", "content": "hi"}]})
    data = [json.loads(ln[5:]) for ln in r.text.splitlines() if ln.startswith("data:")]
    assert [d.get("text") for d in data[:-1]] == ["안", "녕"] and data[-1]["content"] == "안녕"
    assert oai.body(0)["stream"] is True


async def test_errors(client, oai):
    oai.push("chat", status=429)
    oai.push("chat", status=500)
    oai.push("chat", completion("살았다"))
    out = (await client.post("/v1/llm/chat", json={"task": "x.e", "messages": [{"role": "user", "content": "q"}]})).json()
    assert out["content"] == "살았다" and len(oai.calls) == 3
    oai.push("chat", status=400)
    r = await client.post("/v1/llm/chat", json={"task": "x.e", "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 502 and "bad 400" in r.json()["error"]["message"]


async def test_not_configured(client, env, monkeypatch):
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "openai_compat")
    r = await client.post("/v1/llm/chat", json={"task": "x.e", "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 501 and r.json()["error"]["details"]["env"] == "LLM_BASE_URL"


async def test_i2t_and_websearch(client, oai, h, monkeypatch):
    oai.push("chat", completion('{"caption": "매장"}'))
    out = (await client.post("/v1/i2t/analyze", json={"task": "img.c", "images": [{"data_b64": h.b64(h.png_bytes())}],
                                                       "prompt": "설명", "json_schema": {"type": "object", "properties": {
                                                           "caption": {"type": "string"}}, "required": ["caption"]}})).json()
    assert out["json"] == {"caption": "매장"}
    content = oai.body(0)["messages"][0]["content"]
    assert content[0]["type"] == "image_url" and content[1] == {"type": "text", "text": "설명"}

    monkeypatch.setenv("WEBSEARCH_RETURN_SOURCES", "true")
    oai.push("chat", completion("요약입니다", annotations=[{"type": "url_citation", "url_citation": {
        "url": "https://news.example.com/a", "title": "기사", "start_index": 0, "end_index": 3}}]))
    ws = (await client.post("/v1/websearch", json={"task": "mi.ws", "query": "사이니지"})).json()
    assert ws["summary"] == "요약입니다" and ws["sources"][0]["url"] == "https://news.example.com/a"


def png_b64(size, color=(9, 9, 9)) -> str:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


async def test_images_generate_and_native_mask_edit(client, oai, files, h, monkeypatch):
    oai.push("gen", {"created": 1, "data": [{"b64_json": png_b64((1024, 576))}]})
    out = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "로비", "aspect": "16:9"})).json()
    assert out["images"][0]["width"] == 1024 and out["provider"] == "openai_compat"
    body = oai.body(0)
    assert body["size"] == "1024x576" and body["response_format"] == "b64_json" and body["n"] == 1 and body["model"] == "internal-t2i"

    monkeypatch.setenv("T2I_SUPPORTS_MASK", "true")
    src = h.noise_png((200, 100), seed=1)
    fid = files.add(src)
    oai.push("edit", {"created": 1, "data": [{"b64_json": png_b64((200, 100), (255, 255, 255))}]})
    out = (await client.post("/v1/t2i/edit", json={"task": "img.e", "image": {"file_id": fid}, "prompt": "흰색으로",
                                                    "mask": {"box": [0.0, 0.0, 0.5, 1.0]}})).json()
    assert out["fallbacks"] == []
    name, req = oai.calls[1]
    assert name == "edit" and b'name="mask"' in req.content and b'name="image"' in req.content
    res = np.asarray(Image.open(io.BytesIO(files.files[out["images"][0]["file_id"]]["data"])).convert("RGB"))
    orig = np.asarray(Image.open(io.BytesIO(src)).convert("RGB"))
    assert np.array_equal(res[:, 100:], orig[:, 100:])         # 마스크 밖은 원본 그대로
    assert (res[:, 10:90] == 255).all()                         # 안쪽은 제공자 결과


async def test_embeddings(client, oai, monkeypatch):
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai_compat")
    monkeypatch.setenv("EMBEDDING_BASE_URL", BASE)
    monkeypatch.setenv("EMBEDDING_MODEL", "bge-m3")
    oai.push("emb", {"object": "list", "model": "bge-m3", "data": [
        {"object": "embedding", "index": 1, "embedding": [0.0, 1.0]}, {"object": "embedding", "index": 0, "embedding": [1.0, 0.0]}],
        "usage": {"prompt_tokens": 2, "total_tokens": 2}})
    out = (await client.post("/v1/embed", json={"texts": ["가", "나"], "kind": "query"})).json()
    assert out == {"provider": "openai_compat", "model": "bge-m3", "dim": 2, "vectors": [[1.0, 0.0], [0.0, 1.0]]}
    assert oai.body(0)["input"] == ["가", "나"] and oai.body(0)["encoding_format"] == "float"
