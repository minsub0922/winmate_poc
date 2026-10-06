"""실제 Gemini 로 검증한 요청 · 응답(fixtures/gemini_live_*.json)으로 어댑터를 고정한다.

- 2026-10-06 맥의 Claude 앱 내장 브라우저에서 ai-tools 가 만든 REST 본문을 그대로 Gemini 에 보내 받은 응답이다
  (이미지 바이트는 SHA-256 으로 같은 것을 확인하고 보냈다).
- 요청: 같은 입력을 넣으면 지금 코드도 Gemini 가 받아 준 본문과 똑같이 보내는지(모양이 바뀌면 실제로 다시 확인할 것).
- 응답: 실제 응답 모양(생각 서명 · `call_44988` 같은 Gemini id · box_2d · grounding)을 우리 형식으로 바르게 바꾸는지.
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image, ImageDraw

FIX = Path(__file__).parent / "fixtures"
LIVE: dict[str, Any] = json.loads((FIX / "gemini_live_responses.json").read_text(encoding="utf-8"))
RECORDED: dict[str, dict[str, Any]] = {r["name"]: r for r in json.loads((FIX / "gemini_live_requests.json").read_text(encoding="utf-8"))}


def drawn_png(w: int = 320, h: int = 180, color: tuple[int, int, int] = (20, 40, 160)) -> str:
    """기록할 때 쓴 그림(Pillow 기본 PNG) — 같은 바이트가 나와야 요청 본문이 같다."""
    im = Image.new("RGB", (w, h), (245, 246, 248))
    d = ImageDraw.Draw(im)
    d.rectangle([w * 0.25, h * 0.2, w * 0.75, h * 0.8], fill=color)
    d.rectangle([w * 0.45, h * 0.8, w * 0.55, h * 0.95], fill=(80, 80, 80))
    b = io.BytesIO()
    im.save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


def image_reply(w: int = 1344, h: int = 768) -> dict[str, Any]:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 190, 170)).save(buf, "JPEG")
    return {"candidates": [{"content": {"role": "model", "parts": [
        {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}}]}, "finishReason": "STOP"}],
        "modelVersion": "gemini-3.1-flash-lite-image"}


FORM_SCHEMA = {"type": "object", "properties": {
    "project_name": {"type": "string"}, "customer": {"type": "string"},
    "keymen": {"type": "array", "items": {"type": "object", "properties": {
        "role": {"type": "string"}, "requirements": {"type": "array", "items": {"type": "string"}},
        "weight": {"type": "number", "minimum": 0, "maximum": 1}}, "required": ["role", "requirements"]}}},
    "required": ["project_name", "customer", "keymen"]}
TOOLS = [{"name": "search_products", "description": "삼성 B2B 제품을 검색한다",
          "parameters": {"type": "object", "properties": {"query": {"type": "string"},
                                                          "category": {"type": "string", "enum": ["signage", "hvac", "tv"]}},
                         "required": ["query"]}}]
EMAIL = ("다음 메일에서 프로젝트명, 고객사, 키맨별 요구사항을 뽑아라.\n\n안녕하세요, E 자산운용 김부장입니다. 용산 AI Ready 오피스 프로젝트 관련해 "
         "로비 미디어월과 회의실 전자칠판을 검토 중입니다. 대표이사님은 에너지 절감을 가장 중요하게 보십니다.")

# 기록할 때 ai-tools API 에 넣은 입력
CALLS: dict[str, tuple[str, dict[str, Any]]] = {
    "llm_text": ("/v1/llm/chat", {"task": "rq.email", "max_tokens": 512, "messages": [
        {"role": "system", "content": "너는 삼성 B2B 영업 담당자를 돕는 비서다. 짧게 답한다."},
        {"role": "user", "content": "호텔 로비에 대형 사이니지를 제안할 때 고객에게 물어볼 질문 3가지를 한 줄씩 써줘."}]}),
    "llm_json": ("/v1/llm/chat", {"task": "rq.extract_form", "messages": [{"role": "user", "content": EMAIL}],
                                  "json_schema": FORM_SCHEMA, "schema_name": "Form"}),
    "llm_tools": ("/v1/llm/chat", {"task": "pr.agent", "tools": TOOLS, "tool_choice": "auto",
                                   "messages": [{"role": "user", "content": "카페 매장 메뉴보드에 맞는 삼성 사이니지 제품을 찾아줘."}]}),
    "i2t_bbox": ("/v1/i2t/analyze", {"task": "be.floorplan", "images": [{"data_b64": drawn_png(), "mime": "image/png"}],
                                     "prompt": "이 그림에서 보이는 사각형 물체를 찾아 설명하라.", "want_bbox": True,
                                     "json_schema": {"type": "object", "properties": {
                                         "summary": {"type": "string"},
                                         "objects": {"type": "array", "items": {"type": "object", "properties": {"label": {"type": "string"}},
                                                                                "required": ["label"]}}},
                                         "required": ["summary", "objects"]}}),
    "t2i_generate": ("/v1/t2i/generate", {
        "task": "img.generate", "prompt": "밝은 카페 매장 카운터 위 벽에 가로형 디지털 메뉴보드 3대가 나란히 설치된 실사 사진, 따뜻한 조명",
        "aspect": "16:9", "n": 1,
        "reference_images": [{"data_b64": drawn_png(240, 240, (30, 30, 30)), "mime": "image/png", "role": "product", "strength": "high"}]}),
    "websearch": ("/v1/websearch", {"task": "mi.area_market", "query": "2026년 국내 디지털 사이니지 시장 규모와 성장률",
                                    "locale": "ko-KR", "max_sources": 6}),
}


def reply_for(name: str) -> dict[str, Any]:
    return image_reply() if name == "t2i_generate" else LIVE[name]


@pytest.mark.parametrize("name", list(CALLS))
async def test_request_body_matches_what_gemini_accepted(client, gem, files, name):
    path, body = CALLS[name]
    gem.reply(reply_for(name))
    r = await client.post(path, json=body)
    assert r.status_code == 200, r.text
    rec = RECORDED[name]
    assert gem.urls[0].endswith(rec["path"].removeprefix("/v1beta")), gem.urls[0]
    assert gem.requests[0] == rec["body"]   # 기록 때와 같은 기본값(conftest AI_ENV)


async def test_live_text(client, gem):
    gem.reply(LIVE["llm_text"])
    out = (await client.post(CALLS["llm_text"][0], json=CALLS["llm_text"][1])).json()
    assert out["content"].startswith("1. 로비를 방문하는 고객에게") and out["content"].count("\n\n") == 2
    assert out["finish_reason"] == "stop" and out["tool_calls"] == []
    assert out["usage"] == {"input_tokens": 53, "output_tokens": 80 + 119}   # 생각 토큰 포함
    assert out["model"] == "gemini-3.1-flash-lite" and out["provider"] == "gemini"


async def test_live_json(client, gem):
    gem.reply(LIVE["llm_json"])
    out = (await client.post(CALLS["llm_json"][0], json=CALLS["llm_json"][1])).json()
    assert out["json"] == {"project_name": "용산 AI Ready 오피스 프로젝트", "customer": "E 자산운용",
                           "keymen": [{"role": "대표이사", "requirements": ["에너지 절감"], "weight": 1}]}
    assert len(gem.requests) == 1   # 수리 재시도 없음


async def test_live_tool_call_keeps_gemini_id_and_signature(client, gem):
    gem.reply(LIVE["llm_tools"])
    path, body = CALLS["llm_tools"]
    out = (await client.post(path, json=body)).json()
    assert out["finish_reason"] == "tool_calls"
    tc = out["tool_calls"][0]
    assert tc == {"id": "call_44988", "name": "search_products", "arguments": {"category": "signage", "query": "카페 메뉴보드 사이니지"}}

    # 다음 턴: Gemini 가 준 id 와 실제 생각 서명을 그대로 돌려보낸다(실측: 서명이 없으면 400)
    gem.reply({"candidates": [{"content": {"role": "model", "parts": [{"text": "QM 시리즈를 추천합니다."}]}, "finishReason": "STOP"}],
               "modelVersion": "gemini-3.1-flash-lite"})
    msgs = [*body["messages"], {"role": "assistant", "content": "", "tool_calls": [tc]},
            {"role": "tool", "tool_call_id": tc["id"], "content": json.dumps({"items": [{"code": "QM55C", "name": "QMC 55형"}]})}]
    out2 = (await client.post(path, json={**body, "messages": msgs})).json()
    assert out2["content"] == "QM 시리즈를 추천합니다."
    contents = gem.requests[1]["contents"]
    call_part = contents[1]["parts"][0]
    live_sig = LIVE["llm_tools"]["candidates"][0]["content"]["parts"][0]["thoughtSignature"]
    assert call_part["functionCall"]["id"] == "call_44988"
    # SDK 는 bytes 를 URL-safe base64 로 보낸다(proto JSON 은 둘 다 받는다) — 바이트가 같으면 된다
    assert base64.urlsafe_b64decode(call_part["thoughtSignature"]) == base64.b64decode(live_sig)
    assert contents[2]["parts"][0]["functionResponse"]["id"] == "call_44988"
    assert contents[2]["parts"][0]["functionResponse"]["response"] == {"items": [{"code": "QM55C", "name": "QMC 55형"}]}


def test_our_ids_are_not_sent_but_gemini_ids_are():
    from winmate_common.ids import new_id
    from winmate_ai_tools.providers.gemini import _gemini_id

    assert _gemini_id(new_id("call")) is None
    assert _gemini_id("call_44988") == "call_44988" and _gemini_id("gfc-7") == "gfc-7"
    assert _gemini_id(None) is None and _gemini_id("") is None


async def test_live_i2t_boxes(client, gem):
    gem.reply(LIVE["i2t_bbox"])
    out = (await client.post(CALLS["i2t_bbox"][0], json=CALLS["i2t_bbox"][1])).json()
    assert out["json"]["objects"] == [{"label": "blue rectangle"}, {"label": "grey rectangle"}]
    boxes = {b["label"]: b for b in out["boxes"]}
    # box_2d = [ymin, xmin, ymax, xmax] (0..1000) → box = [x0, y0, x1, y1] (0..1)
    assert boxes["blue rectangle"]["box"] == pytest.approx([0.249, 0.198, 0.753, 0.805])
    assert boxes["grey rectangle"]["box"] == pytest.approx([0.449, 0.801, 0.553, 0.956])
    # 그린 그림과 맞는지(320x180, 파란 사각형 x 25~75% · y 20~80%)
    assert boxes["blue rectangle"]["box"] == pytest.approx([0.25, 0.2, 0.75, 0.8], abs=0.01)


async def test_live_websearch(client, gem, monkeypatch):
    gem.reply(LIVE["websearch"])
    gem.reply(LIVE["websearch"])
    path, body = CALLS["websearch"]
    out = (await client.post(path, json=body)).json()
    text = LIVE["websearch"]["candidates"][0]["content"]["parts"][0]["text"]
    gm = LIVE["websearch"]["candidates"][0]["groundingMetadata"]
    assert out["summary"] == text and out["queries"] == gm["webSearchQueries"]
    assert out["sources"] == [] and out["returned_sources"] is False   # 사내 웹 검색 API 흉내(기본)

    monkeypatch.setenv("WEBSEARCH_RETURN_SOURCES", "true")
    out = (await client.post(path, json=body)).json()
    titles = [s["title"] for s in out["sources"]]
    assert titles == [c["web"]["title"] for c in gm["groundingChunks"]]
    assert all(s["url"].startswith("https://vertexaisearch.cloud.google.com/grounding-api-redirect/") for s in out["sources"])
    cited = {i for sup in gm["groundingSupports"] for i in sup["groundingChunkIndices"]}
    assert {i for i, s in enumerate(out["sources"]) if s["snippet"]} == cited
