from __future__ import annotations

import json
from typing import Any

import pytest

from winmate_common import testing
from winmate_ai_tools import providers
from winmate_ai_tools.providers.base import LLMCall, LLMResult, Provider

FORM = {"type": "object", "properties": {"customer": {"type": "string", "minLength": 2},
                                         "count": {"type": "integer", "minimum": 1}},
        "required": ["customer", "count"]}


class Scripted(Provider):
    """정해 둔 결과를 차례로 돌려주는 가짜 제공자(live 모드 테스트용)."""

    name = "fake"

    def __init__(self, outputs: list[Any]):
        self.outputs = list(outputs)
        self.calls: list[LLMCall] = []

    async def chat(self, cfg, call):
        self.calls.append(call)
        out = self.outputs.pop(0)
        return out(call) if callable(out) else out


@pytest.fixture
def live(env, monkeypatch):
    """MODEL_MODE=live + 가짜 제공자 + fakeredis."""
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    def install(outputs: list[Any]) -> Scripted:
        fake = Scripted(outputs)
        monkeypatch.setitem(providers.REGISTRY, "fake", lambda: fake)
        providers.reset()
        return fake

    return install


def chat_body(text: str = "고객사는 삼성 호텔입니다", **kw: Any) -> dict[str, Any]:
    return {"task": kw.pop("task", "rq.test"), "messages": [{"role": "user", "content": text}], **kw}


def sse_events(text: str) -> list[tuple[str, Any]]:
    events, ev = [], {}
    for line in text.splitlines():
        if not line.strip():
            if ev:
                events.append((ev.get("event", "message"), json.loads(ev["data"]) if "data" in ev else None))
                ev = {}
            continue
        if line.startswith(":"):
            continue
        k, _, v = line.partition(":")
        ev[k] = v[1:] if v.startswith(" ") else v
    if ev:
        events.append((ev.get("event", "message"), json.loads(ev["data"]) if "data" in ev else None))
    return events


# ── mock ────────────────────────────────────────────────────

async def test_mock_text(client):
    r = await client.post("/v1/llm/chat", json=chat_body("이번 제안서의 핵심 메시지를 한 줄로 써 주세요"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "mock" and body["model"] == "gemini-3.1-flash-lite"
    assert body["content"] == "[mock:rq.test] 이번 제안서의 핵심 메시지를 한 줄로 써 주세요"
    assert body["json"] is None and body["tool_calls"] == [] and body["fallback"] == "none"
    assert body["call_id"].startswith("call_") and body["usage"]["input_tokens"] > 0


async def test_mock_json_schema(client):
    r = await client.post("/v1/llm/chat", json=chat_body(json_schema=FORM, schema_name="Form"))
    body = r.json()
    assert body["json"] == {"customer": "[mock] 고객사", "count": 1}
    assert json.loads(body["content"]) == body["json"]


async def test_fixture_json_content_and_cycle(client, mocks_dir, h):
    h.write_fixture(mocks_dir, "rq.extract_form", {"json": {"customer": "가나다 호텔", "count": 3}})
    r = await client.post("/v1/llm/chat", json=chat_body(task="rq.extract_form", json_schema=FORM))
    assert r.json()["json"] == {"customer": "가나다 호텔", "count": 3}

    h.write_fixture(mocks_dir, "rq.cycle", {"responses": [{"content": "첫째"}, {"content": "둘째"}]})
    got = [(await client.post("/v1/llm/chat", json=chat_body(task="rq.cycle"))).json()["content"] for _ in range(3)]
    assert got == ["첫째", "둘째", "첫째"]


async def test_fixture_tool_calls_and_error(client, mocks_dir, h):
    h.write_fixture(mocks_dir, "sb.agent", {"tool_calls": [{"name": "lookup", "arguments": {"q": "QMC"}}]})
    tools = [{"name": "lookup", "description": "KB 검색", "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}}]
    body = (await client.post("/v1/llm/chat", json=chat_body(task="sb.agent", tools=tools))).json()
    assert body["finish_reason"] == "tool_calls"
    assert body["tool_calls"][0]["name"] == "lookup" and body["tool_calls"][0]["arguments"] == {"q": "QMC"}
    # 도구 없이 부르면 tool_calls 고정 응답은 쓰지 않는다
    body = (await client.post("/v1/llm/chat", json=chat_body(task="sb.agent"))).json()
    assert body["tool_calls"] == []

    h.write_fixture(mocks_dir, "mi.fail", {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "웹 검색 장애"}})
    r = await client.post("/v1/llm/chat", json=chat_body(task="mi.fail"))
    assert r.status_code == 503 and r.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"


async def test_mock_tools_without_fixture_no_call(client):
    tools = [{"name": "lookup", "parameters": {"type": "object"}}]
    body = (await client.post("/v1/llm/chat", json=chat_body(tools=tools))).json()
    assert body["tool_calls"] == [] and body["content"].startswith("[mock:rq.test]")


# ── 정책 · 길이 ─────────────────────────────────────────────

async def test_policy_confidential_403(client, monkeypatch):
    r = await client.post("/v1/llm/chat", json=chat_body(confidential=True))
    assert r.status_code == 403
    err = r.json()["error"]
    assert err["code"] == "POLICY_CONFIDENTIAL" and err["details"]["env"] == "LLM_ALLOW_CONFIDENTIAL"
    monkeypatch.setenv("LLM_ALLOW_CONFIDENTIAL", "true")
    r = await client.post("/v1/llm/chat", json=chat_body(confidential=True))
    assert r.status_code == 200


async def test_mock_does_not_block_confidential_by_default(client, monkeypatch):
    # mock 은 밖으로 나가는 것이 없다 → 기능 서비스 테스트 · 시나리오 E2E 가 기밀 흐름을 끝까지 돈다
    monkeypatch.setenv("MOCK_ENFORCE_CONFIDENTIAL", "false")
    r = await client.post("/v1/llm/chat", json=chat_body(confidential=True))
    assert r.status_code == 200
    monkeypatch.setenv("MODEL_MODE", "live")   # live 는 여전히 막는다(키가 없어도 정책이 먼저)
    r = await client.post("/v1/llm/chat", json=chat_body(confidential=True))
    assert r.status_code == 403 and r.json()["error"]["code"] == "POLICY_CONFIDENTIAL"


async def test_context_too_long_413(client, monkeypatch):
    monkeypatch.setenv("LLM_MAX_INPUT_TOKENS", "50")
    r = await client.post("/v1/llm/chat", json=chat_body("가" * 200))
    assert r.status_code == 413
    err = r.json()["error"]
    assert err["code"] == "CONTEXT_TOO_LONG" and err["details"]["estimated_tokens"] > 50


# ── JSON 대체 경로(live + 가짜 제공자) ───────────────────────

async def test_native_json_ok(client, live):
    fake = live([LLMResult(text='{"customer": "삼성 호텔", "count": 2}', model="fake-1")])
    body = (await client.post("/v1/llm/chat", json=chat_body(json_schema=FORM, schema_name="Form"))).json()
    assert body["json"] == {"customer": "삼성 호텔", "count": 2}
    assert body["fallback"] == "none" and body["provider"] == "fake" and body["model"] == "fake-1"
    call = fake.calls[0]
    assert call.json_schema == FORM and call.schema_name == "Form" and call.system is None
    assert call.temperature == 0.2 and call.max_tokens == 4096


async def test_json_repair_then_ok(client, live):
    fake = live([
        LLMResult(text='{"customer": "A"}', usage={"input_tokens": 10, "output_tokens": 5}),
        LLMResult(text='{"customer": "삼성 호텔", "count": 2}', usage={"input_tokens": 20, "output_tokens": 6}),
    ])
    body = (await client.post("/v1/llm/chat", json=chat_body(json_schema=FORM))).json()
    assert body["fallback"] == "json_repair" and body["json"]["count"] == 2
    assert body["usage"] == {"input_tokens": 30, "output_tokens": 11}
    second = fake.calls[1]
    assert second.messages[-2].role == "assistant" and second.messages[-2].text() == '{"customer": "A"}'
    repair = second.messages[-1].text()
    assert "count" in repair and "customer" in repair   # 오류 위치를 알려 준다


async def test_json_schema_mismatch_422(client, live):
    live([LLMResult(text="모르겠어요")] * 3)
    r = await client.post("/v1/llm/chat", json=chat_body(json_schema=FORM))
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "SCHEMA_MISMATCH" and err["details"]["attempts"] == 3 and err["details"]["raw"] == "모르겠어요"


async def test_prompt_json_fallback(client, live, monkeypatch):
    monkeypatch.setenv("LLM_SUPPORTS_JSON_SCHEMA", "false")
    fake = live([LLMResult(text='네, 결과입니다.\n```json\n{"customer": "삼성 호텔", "count": 4,}\n```')])
    body = (await client.post("/v1/llm/chat", json=chat_body(json_schema=FORM))).json()
    assert body["fallback"] == "json_parse" and body["json"] == {"customer": "삼성 호텔", "count": 4}
    call = fake.calls[0]
    assert call.json_schema is None and '"customer"' in (call.system or "") and "JSON Schema" in call.system


async def test_system_messages_joined(client, live):
    fake = live([LLMResult(text="ok")])
    body = {"task": "rq.t", "messages": [{"role": "system", "content": "너는 제안서 작가다"},
                                         {"role": "system", "content": "한국어로 답한다"},
                                         {"role": "user", "content": "안녕"}]}
    await client.post("/v1/llm/chat", json=body)
    assert fake.calls[0].system == "너는 제안서 작가다\n\n한국어로 답한다"
    assert [m.role for m in fake.calls[0].messages] == ["user"]


# ── 도구 ────────────────────────────────────────────────────

TOOLS = [{"name": "get_weather", "description": "도시 날씨", "parameters": {"type": "object", "properties": {"city": {"type": "string"}},
                                                                         "required": ["city"]}}]


async def test_native_tools(client, live):
    fake = live([LLMResult(text="", tool_calls=[{"id": "call_x", "name": "get_weather", "arguments": {"city": "서울"}}],
                           finish_reason="tool_calls")])
    body = (await client.post("/v1/llm/chat", json=chat_body("서울 날씨?", tools=TOOLS, tool_choice="required"))).json()
    assert body["tool_calls"] == [{"id": "call_x", "name": "get_weather", "arguments": {"city": "서울"}}]
    assert body["finish_reason"] == "tool_calls" and body["fallback"] == "none"
    assert fake.calls[0].tools[0]["name"] == "get_weather" and fake.calls[0].tool_choice == "required"


async def test_react_tools_fallback(client, live, monkeypatch):
    monkeypatch.setenv("LLM_SUPPORTS_TOOLS", "false")
    fake = live([
        LLMResult(text='Thought: 날씨를 봐야 한다\nAction: get_weather\nAction Input: {"city": "서울"}'),
        LLMResult(text="Final Answer: 서울은 맑음입니다"),
    ])
    body = (await client.post("/v1/llm/chat", json=chat_body("서울 날씨?", tools=TOOLS, tool_choice="get_weather"))).json()
    assert body["fallback"] == "react" and body["finish_reason"] == "tool_calls"
    tc = body["tool_calls"][0]
    assert tc["name"] == "get_weather" and tc["arguments"] == {"city": "서울"} and tc["id"].startswith("call_")
    assert body["content"] == "날씨를 봐야 한다"
    first = fake.calls[0]
    assert first.tools is None and "Action Input" in first.system and "MUST call the tool `get_weather`" in first.system

    # 두 번째 턴: 앞선 tool_calls · 결과가 텍스트로 바뀌어 들어간다
    msgs = [{"role": "user", "content": "서울 날씨?"},
            {"role": "assistant", "content": "", "tool_calls": [tc]},
            {"role": "tool", "tool_call_id": tc["id"], "content": '{"weather": "맑음"}'}]
    body = (await client.post("/v1/llm/chat", json={"task": "rq.test", "messages": msgs, "tools": TOOLS})).json()
    assert body["content"] == "서울은 맑음입니다" and body["tool_calls"] == []
    second = fake.calls[1]
    assert [m.role for m in second.messages] == ["user", "assistant", "user"]
    assert 'Action: get_weather\nAction Input: {"city":"서울"}' in second.messages[1].text()
    assert second.messages[2].text().startswith("Observation [get_weather id=")


# ── 이미지 조각 ─────────────────────────────────────────────

async def test_image_parts(client, live, files, h):
    fake = live([LLMResult(text="빨간 사각형")])
    fid = files.add(h.png_bytes((3000, 1000)), "image/png")
    msg = {"role": "user", "content": [{"type": "text", "text": "무엇이 보이나요?"}, {"type": "image", "file_id": fid},
                                       {"type": "image", "data_b64": h.b64(h.png_bytes((10, 10))), "mime": "image/png"}]}
    body = (await client.post("/v1/llm/chat", json={"task": "img.caption", "messages": [msg]})).json()
    assert body["content"] == "빨간 사각형"
    imgs = fake.calls[0].messages[0].images()
    assert len(imgs) == 2 and max(imgs[0].width, imgs[0].height) == 1536   # I2T_MAX_IMAGE_SIDE_PX 로 축소
    assert (imgs[1].width, imgs[1].height) == (10, 10)


async def test_missing_file_404(client, files):
    msg = {"role": "user", "content": [{"type": "image", "file_id": "file_nope"}]}
    r = await client.post("/v1/llm/chat", json={"task": "img.caption", "messages": [msg]})
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"


# ── 스트리밍 ────────────────────────────────────────────────

async def test_stream_mock(client):
    r = await client.post("/v1/llm/stream", json=chat_body("스트리밍 테스트 문장입니다"))
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    events = sse_events(r.text)
    deltas = [d["text"] for e, d in events if e == "delta"]
    assert len(deltas) >= 2
    kind, done = events[-1]
    assert kind == "done" and done["content"] == "".join(deltas) == "[mock:rq.test] 스트리밍 테스트 문장입니다"
    assert done["call_id"].startswith("call_") and done["usage"]["output_tokens"] > 0


async def test_stream_json_single_delta(client):
    r = await client.post("/v1/llm/stream", json=chat_body(json_schema=FORM))
    events = sse_events(r.text)
    assert [e for e, _ in events] == ["delta", "done"]
    assert events[1][1]["json"] == {"customer": "[mock] 고객사", "count": 1}


async def test_stream_errors(client, monkeypatch, mocks_dir, h):
    r = await client.post("/v1/llm/stream", json=chat_body(confidential=True))
    assert r.status_code == 403   # 시작 전 오류는 HTTP 오류
    h.write_fixture(mocks_dir, "rq.boom", {"error": {"status": 502, "code": "PROVIDER_ERROR", "message": "터짐"}})
    r = await client.post("/v1/llm/stream", json=chat_body(task="rq.boom"))
    events = sse_events(r.text)
    assert events[-1][0] == "error" and events[-1][1]["code"] == "PROVIDER_ERROR"


async def test_stream_unsupported_one_delta(client, monkeypatch):
    monkeypatch.setenv("LLM_SUPPORTS_STREAMING", "false")
    events = sse_events((await client.post("/v1/llm/stream", json=chat_body("하나로"))).text)
    assert [e for e, _ in events] == ["delta", "done"]


# ── 호출 로그 ───────────────────────────────────────────────

async def test_call_log(client):
    body = (await client.post("/v1/llm/chat", json=chat_body("로그 남기기", task="rq.log"))).json()
    await client.post("/v1/llm/chat", json=chat_body(confidential=True, task="rq.log"))
    r = await client.get("/v1/calls", params={"capability": "llm", "task": "rq.log"})
    items = r.json()["items"]
    assert len(items) == 2
    err, ok = items
    assert err["status"] == "error" and err["error"]["code"] == "POLICY_CONFIDENTIAL" and err["confidential"] is True
    assert ok["id"] == body["call_id"] and ok["status"] == "ok" and ok["provider"] == "mock" and ok["mode"] == "mock"
    assert ok["request"]["messages"][0]["content"] == "로그 남기기" and ok["response"]["content"] == body["content"]
    one = (await client.get(f"/v1/calls/{body['call_id']}")).json()
    assert one["id"] == body["call_id"] and one["usage"]["output_tokens"] > 0
    assert (await client.get("/v1/calls/call_nope")).status_code == 404


async def test_stream_timeout_emits_error(client, env, monkeypatch):
    import asyncio

    class SlowStream(Provider):
        name = "fake"

        async def stream(self, cfg, call):
            yield "앞부분"
            await asyncio.sleep(5)
            yield LLMResult(text="앞부분 늦음")

    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("LLM_TIMEOUT_S", "0.2")
    monkeypatch.setitem(providers.REGISTRY, "fake", SlowStream)
    providers.reset()
    r = await client.post("/v1/llm/stream", json=chat_body("느린 스트림"))
    events = sse_events(r.text)
    assert events[0] == ("delta", {"text": "앞부분"})
    assert events[-1][0] == "error" and events[-1][1]["code"] == "TIMEOUT"
    rec = (await client.get("/v1/calls", params={"capability": "llm"})).json()["items"][0]
    assert rec["status"] == "error" and rec["error"]["code"] == "TIMEOUT"


async def test_fixture_when_picks_by_input(client, mocks_dir, h):
    """`responses[].when.contains` 로 입력에 맞는 응답을 고르고, 맞는 게 없으면 when 없는 항목을 돌린다."""
    h.write_fixture(mocks_dir, "sp.pick", {"responses": [
        {"when": {"contains": "QM55R"}, "content": "QM55R 추가"},
        {"when": {"contains": ["전기료", "연간"], "not_contains": "QM55R"}, "content": "연간 전기료 행"},
        {"content": "기본 1"},
        {"content": "기본 2"},
    ]})
    ask = lambda text: client.post("/v1/llm/chat", json={"task": "sp.pick", "messages": [{"role": "user", "content": text}]})
    assert (await ask("연간 전기료 행을 넣어 줘")).json()["content"] == "연간 전기료 행"
    assert (await ask("QM55R 도 비교에 넣어 줘(연간 전기료 포함)")).json()["content"] == "QM55R 추가"
    assert (await ask("아무 말")).json()["content"] == "기본 1"
    assert (await ask("또 아무 말")).json()["content"] == "기본 2"
    assert (await ask("QM55R")).json()["content"] == "QM55R 추가"      # 조건 항목은 순번을 쓰지 않는다
    assert (await ask("세 번째 아무 말")).json()["content"] == "기본 1"
