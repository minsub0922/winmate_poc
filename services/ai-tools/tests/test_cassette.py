"""기록 · 재생 — mock 제공자를 'live' 대신 써서 record → replay 를 확인한다."""
from __future__ import annotations

import json

import pytest

from winmate_common import testing


@pytest.fixture
def record(env, monkeypatch):
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "record")
    for cap in ("LLM", "I2T", "T2I", "WEBSEARCH"):
        monkeypatch.setenv(f"{cap}_PROVIDER", "mock")
    monkeypatch.setenv("LLM_ALLOW_CONFIDENTIAL", "true")
    return env


def body(text: str = "제안 요약", **kw):
    return {"task": kw.pop("task", "pr.summary"), "messages": [{"role": "user", "content": text}], **kw}


async def test_record_then_replay(client, record, monkeypatch, mocks_dir, h):
    h.write_fixture(mocks_dir, "pr.summary", {"content": "기록된 답"})
    r = await client.post("/v1/llm/chat", json=body(confidential=True))
    assert r.status_code == 200 and r.json()["content"] == "기록된 답"
    files = list((record / "cassettes" / "llm" / "pr.summary").glob("*.json"))
    assert len(files) == 1
    doc = json.loads(files[0].read_text(encoding="utf-8"))
    assert doc["response"]["content"] == "기록된 답" and doc["provider"] == "mock"
    assert "confidential" not in json.dumps(doc["request"])

    # 고정 응답을 바꿔도 재생은 기록된 값을 돌려준다(기밀 표시는 키에 들어가지 않는다)
    h.write_fixture(mocks_dir, "pr.summary", {"content": "새 답"})
    monkeypatch.setenv("MODEL_MODE", "replay")
    r = await client.post("/v1/llm/chat", json=body())
    assert r.status_code == 200 and r.json()["content"] == "기록된 답"
    rec = (await client.get("/v1/calls", params={"capability": "llm"})).json()["items"][0]
    assert rec["cassette"] == "replay_hit" and rec["mode"] == "replay"


async def test_replay_miss(client, env, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "replay")
    r = await client.post("/v1/llm/chat", json=body("없는 카세트"))
    assert r.status_code == 404
    err = r.json()["error"]
    assert err["code"] == "CASSETTE_MISS" and err["details"]["path"].endswith(".json")
    monkeypatch.setenv("REPLAY_FALLBACK", "mock")
    r = await client.post("/v1/llm/chat", json=body("없는 카세트"))
    assert r.status_code == 200 and r.json()["content"].startswith("[mock:pr.summary]")
    rec = (await client.get("/v1/calls", params={"capability": "llm"})).json()["items"][0]
    assert rec["cassette"] == "replay_miss" and rec["mode"] == "replay->mock"


async def test_image_key_uses_content_hash(client, record, monkeypatch, files, h):
    png = h.png_bytes((40, 30))
    fid = files.add(png)
    req = {"task": "rq.read", "images": [{"file_id": fid}], "prompt": "읽어라"}
    first = (await client.post("/v1/i2t/analyze", json=req)).json()
    monkeypatch.setenv("MODEL_MODE", "replay")
    # 같은 그림을 data_b64 로 보내도 같은 카세트(사내망 files id 가 달라도 재생)
    second = await client.post("/v1/i2t/analyze", json={**req, "images": [{"data_b64": h.b64(png), "mime": "image/png"}]})
    assert second.status_code == 200 and second.json()["content"] == first["content"]


async def test_tool_ids_normalized(client, record, monkeypatch, mocks_dir, h):
    h.write_fixture(mocks_dir, "sb.tools", {"content": "도구 결과로 답함"})

    def convo(call_id: str):
        return {"task": "sb.tools", "tools": [{"name": "kb", "parameters": {"type": "object"}}], "messages": [
            {"role": "user", "content": "찾아줘"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": call_id, "name": "kb", "arguments": {"q": "x"}}]},
            {"role": "tool", "tool_call_id": call_id, "content": "결과"}]}

    assert (await client.post("/v1/llm/chat", json=convo("call_AAA"))).status_code == 200
    monkeypatch.setenv("MODEL_MODE", "replay")
    r = await client.post("/v1/llm/chat", json=convo("call_BBB"))
    assert r.status_code == 200 and r.json()["content"] == "도구 결과로 답함"


async def test_t2i_record_replay_resaves(client, record, monkeypatch, files):
    req = {"task": "img.gen", "prompt": "호텔 로비의 사이니지", "aspect": "4:3", "n": 1}
    first = (await client.post("/v1/t2i/generate", json=req)).json()
    fid1 = first["images"][0]["file_id"]
    blobs = list((record / "cassettes" / "t2i" / "img.gen").glob("*.png"))
    assert len(blobs) == 1
    monkeypatch.setenv("MODEL_MODE", "replay")
    second = await client.post("/v1/t2i/generate", json=req)
    assert second.status_code == 200, second.text
    fid2 = second.json()["images"][0]["file_id"]
    assert fid2 != fid1 and files.files[fid2]["data"] == files.files[fid1]["data"]
    assert files.files[fid2]["meta"]["replayed"] is True and files.files[fid2]["meta"]["ai_generated"] is True
    assert second.json()["images"][0]["width"] == first["images"][0]["width"]


async def test_websearch_replay_respects_return_sources(client, record, monkeypatch):
    monkeypatch.setenv("WEBSEARCH_RETURN_SOURCES", "true")
    req = {"task": "mi.ws", "query": "키오스크 시장"}
    first = (await client.post("/v1/websearch", json=req)).json()
    assert first["returned_sources"] is True and first["sources"]
    monkeypatch.setenv("MODEL_MODE", "replay")
    monkeypatch.setenv("WEBSEARCH_RETURN_SOURCES", "false")
    second = (await client.post("/v1/websearch", json=req)).json()
    assert second["summary"] == first["summary"] and second["sources"] == [] and second["returned_sources"] is False
