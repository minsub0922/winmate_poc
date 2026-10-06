from __future__ import annotations

import httpx

from winmate_common import testing
from winmate_common.ai import AI


async def test_info(client):
    r = await client.get("/v1/info")
    assert r.status_code == 200
    assert r.json()["service"] == "ai-tools"


async def test_requires_internal_token(env):
    from winmate_ai_tools.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/v1/info")
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "UNAUTHENTICATED"


async def test_capabilities_mock(client):
    r = await client.get("/v1/capabilities")
    assert r.status_code == 200, r.text
    caps = r.json()
    assert caps["mode"] == "mock"
    assert caps["llm"]["provider"] == "mock" and caps["llm"]["model"] == "gemini-3.1-flash-lite"
    assert caps["llm"]["supports"] == {"json_schema": True, "tools": True, "streaming": True}
    assert caps["llm"]["max_input_tokens"] == 32000 and caps["llm"]["allow_confidential"] is False
    assert caps["i2t"]["max_images_per_call"] == 4 and caps["i2t"]["supports"]["bbox"] is True
    assert caps["t2i"]["supports"] == {"reference_images": True, "edit": True, "mask": False}
    assert caps["t2i"]["default_aspect"] == "16:9" and caps["t2i"]["max_side_px"] == 1024
    assert caps["websearch"]["return_sources"] is False
    assert caps["search_api"] == {"provider": "none", "available": False}
    assert caps["fetch"] == {"enabled": True}
    assert caps["embedding"]["provider"] == "lsa" and caps["embedding"]["available"] is False
    assert caps["usage_today"] == {"llm": 0, "i2t": 0, "t2i": 0, "websearch": 0}
    assert caps["limits"]["enforced"] is False and caps["limits"]["llm"]["rpm"] == 30
    assert caps["limits"]["t2i"]["daily"] == 100


async def test_capabilities_live_reports_availability(client, monkeypatch):
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("T2I_PROVIDER", "openai_compat")
    monkeypatch.setenv("T2I_BASE_URL", "http://t2i.internal/v1")
    monkeypatch.setenv("T2I_SUPPORTS_MASK", "true")
    from winmate_common import testing

    testing.use_fake_redis()
    caps = (await client.get("/v1/capabilities")).json()
    assert caps["mode"] == "live" and caps["limits"]["enforced"] is True
    assert caps["llm"]["provider"] == "gemini" and caps["llm"]["available"] is False   # 키 없음
    assert caps["t2i"]["provider"] == "openai_compat" and caps["t2i"]["available"] is True
    assert caps["t2i"]["supports"]["mask"] is True
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    caps = (await client.get("/v1/capabilities")).json()
    assert caps["llm"]["available"] is True and caps["websearch"]["available"] is True


async def test_usage_endpoint(client):
    r = await client.get("/v1/usage")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "mock" and body["enforced"] is False
    assert body["usage"]["llm"] == {"today": 0, "daily_limit": 2000, "remaining": 2000, "this_minute": 0, "rpm": 30}


async def test_ai_client_contract_strict(env, files, h, monkeypatch):
    """winmate_common.ai 의 모든 메서드를 contracts/ai-tools.json 으로 엄격 검증(요청 · 응답)하며 부른다."""
    import pytest

    from winmate_common.contracts import reload_contracts
    from winmate_common.errors import ApiError
    from winmate_ai_tools.main import app

    reload_contracts()
    monkeypatch.setenv("WEBSEARCH_RETURN_SOURCES", "true")
    monkeypatch.setenv("SEARCH_API_PROVIDER", "mock")
    with testing.inprocess({"ai-tools": app, "files": files.app}):
        ai = AI()
        ai.c.validation = "strict"
        assert (await ai.capabilities())["llm"]["supports"]["json_schema"] is True
        res = await ai.chat("rq.chat", [{"role": "system", "content": "s"}, {"role": "user", "content": [
            {"type": "text", "text": "보라"}, {"type": "image", "data_b64": h.b64(h.png_bytes()), "mime": "image/png"}]}],
            tools=[{"name": "kb", "description": "검색", "parameters": {"type": "object"}}], tool_choice="auto",
            temperature=0.1, max_tokens=50)
        assert res["fallback"] == "none"
        from pydantic import BaseModel

        class Out(BaseModel):
            title: str
            score: float

        assert (await ai.json("rq.json", "제목", Out, system="시스템"))["title"] == "[mock] 제목"
        v = await ai.vision("img.v", [{"data_b64": h.b64(h.png_bytes())}], "보라", schema=Out, want_bbox=True, max_tokens=99)
        assert v["json"]["title"] == "[mock] 제목" and len(v["boxes"]) == 2
        g = await ai.generate_image("img.g", "로비", aspect="4:3", n=2, negative_prompt="사람", style="실사", seed=1,
                                    references=[{"file_id": files.add(h.png_bytes()), "role": "style", "strength": "low"}],
                                    metadata={"k": "v"})
        assert len(g["images"]) == 2
        e = await ai.edit_image("img.e", g["images"][0]["file_id"], "바꿔", mask={"box": [0.1, 0.1, 0.5, 0.5]}, aspect="16:9")
        assert e["fallbacks"] == ["outpaint_extend", "mask_crop_paste"]
        ws = await ai.websearch("mi.ws", "질의", max_sources=2)
        assert ws["returned_sources"] is True and len(ws["sources"]) == 2
        assert (await ai.search("질의", limit=2))["available"] is True
        with pytest.raises(ApiError) as ei:
            await ai.embed(["가"])
        assert ei.value.code == "EMBEDDING_DISABLED"
        monkeypatch.setenv("WEB_FETCH_ENABLED", "false")   # 네트워크 없이
        assert (await ai.fetch("https://example.com/y"))["reason"] == "disabled"
        monkeypatch.setenv("EMBEDDING_PROVIDER", "local")   # mock 모드 → 해시 벡터
        assert (await ai.embed(["가", "나"], kind="query"))["dim"] == 1024


async def test_ai_client_roundtrip(env):
    """winmate_common.ai 클라이언트가 이 API 와 그대로 맞는지(계약 검증은 contracts/ai-tools.json 기준)."""
    from winmate_common import testing
    from winmate_ai_tools.main import app

    with testing.inprocess({"ai-tools": app}):
        ai = AI()
        caps = await ai.capabilities()
        assert caps["mode"] == "mock"
        text = await ai.text("rq.hello", "안녕하세요 반갑습니다")
        assert text.startswith("[mock:rq.hello]")
        data = await ai.json("rq.form", "추출", schema={"type": "object", "properties": {"customer": {"type": "string"}},
                                                       "required": ["customer"]})
        assert data == {"customer": "[mock] 고객사"}
        ws = await ai.websearch("mi.search", "디지털 사이니지 시장")
        assert ws["returned_sources"] is False and ws["sources"] == []
