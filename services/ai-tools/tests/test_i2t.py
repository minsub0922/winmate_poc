"""I2T — 이미지 준비(HEIC · 축소 · EXIF), 장수 제한, JSON · 박스(감싼 스키마 → 0..1 좌표), 대체 경로."""
from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from winmate_common import testing
from winmate_ai_tools import imaging, providers
from winmate_ai_tools.i2t import convert_boxes, wrap_schema
from winmate_ai_tools.providers.base import I2TCall, LLMResult, Provider

SCHEMA = {"type": "object", "properties": {"caption": {"type": "string"}, "objects": {"type": "array", "items": {"type": "string"}}},
          "required": ["caption", "objects"]}


def heic_bytes(size=(4000, 3000)) -> bytes:
    im = Image.new("RGB", size, (10, 200, 30))
    buf = io.BytesIO()
    im.save(buf, format="HEIF", quality=50)
    return buf.getvalue()


async def test_mock_text_and_json_and_boxes(client, h):
    img = {"data_b64": h.b64(h.png_bytes()), "mime": "image/png"}
    body = (await client.post("/v1/i2t/analyze", json={"task": "rq.scan", "images": [img], "prompt": "글자를 받아 써라"})).json()
    assert body["content"] == "[mock:rq.scan] 이미지 1장: 글자를 받아 써라" and body["json"] is None and body["boxes"] == []

    body = (await client.post("/v1/i2t/analyze", json={"task": "img.qc", "images": [img, img], "prompt": "검사",
                                                        "json_schema": SCHEMA, "want_bbox": True})).json()
    assert body["json"] == {"caption": "[mock] 캡션", "objects": ["[mock] 객체", "[mock] 객체 2"]}
    assert len(body["boxes"]) == 2 and body["boxes"][0]["box"] == [0.1, 0.12, 0.45, 0.62] and body["warnings"] == []


async def test_fixture_with_boxes(client, mocks_dir, h):
    h.write_fixture(mocks_dir, "be.detect", {"json": {"caption": "카운터", "objects": ["counter"]},
                                             "boxes": [{"label": "counter", "box": [0.2, 0.5, 0.8, 0.9], "score": 0.7}]})
    img = {"data_b64": h.b64(h.png_bytes())}
    body = (await client.post("/v1/i2t/analyze", json={"task": "be.detect", "images": [img], "prompt": "면 찾기",
                                                        "json_schema": SCHEMA, "want_bbox": True})).json()
    assert body["json"]["caption"] == "카운터"
    assert body["boxes"] == [{"label": "counter", "box": [0.2, 0.5, 0.8, 0.9], "score": 0.7, "image_index": 0}]


async def test_bbox_unsupported_warning(client, h, monkeypatch):
    monkeypatch.setenv("I2T_SUPPORTS_BBOX", "false")
    body = (await client.post("/v1/i2t/analyze", json={"task": "img.qc", "images": [{"data_b64": h.b64(h.png_bytes())}],
                                                        "prompt": "x", "want_bbox": True})).json()
    assert body["boxes"] == [] and body["warnings"] and body["warnings"][0].startswith("bbox_unsupported")


async def test_too_many_images_400(client, h):
    img = {"data_b64": h.b64(h.png_bytes())}
    r = await client.post("/v1/i2t/analyze", json={"task": "x.y", "images": [img] * 5, "prompt": "x"})
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "TOO_MANY_IMAGES" and err["details"] == {"max": 4, "given": 5}


async def test_bad_image_400(client):
    r = await client.post("/v1/i2t/analyze", json={"task": "x.y", "images": [{"data_b64": "aGVsbG8="}], "prompt": "x"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "BAD_IMAGE"


def test_prepare_heic_and_downscale():
    img = imaging.prepare(heic_bytes(), 1536)
    assert img.mime == "image/jpeg" and (img.width, img.height) == (1536, 1152)
    assert Image.open(io.BytesIO(img.data)).format == "JPEG"
    small = Image.new("RGB", (100, 50))
    buf = io.BytesIO()
    small.save(buf, "PNG")
    same = imaging.prepare(buf.getvalue(), 1536)
    assert same.data == buf.getvalue() and same.mime == "image/png"   # 손댈 필요 없으면 원본 그대로


def test_prepare_exif_rotation():
    im = Image.new("RGB", (200, 100), (255, 0, 0))
    exif = Image.Exif()
    exif[274] = 6   # 90° 회전
    buf = io.BytesIO()
    im.save(buf, "JPEG", exif=exif)
    out = imaging.prepare(buf.getvalue(), 1536)
    assert (out.width, out.height) == (100, 200)


# ── 실제 제공자 경로(가짜 제공자) ────────────────────────────

class FakeVision(Provider):
    name = "fake"

    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls: list[I2TCall] = []

    async def analyze(self, cfg, call):
        self.calls.append(call)
        return self.outputs.pop(0)


@pytest.fixture
def live(env, monkeypatch):
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("I2T_PROVIDER", "fake")

    def install(outputs):
        p = FakeVision(outputs)
        monkeypatch.setitem(providers.REGISTRY, "fake", lambda: p)
        providers.reset()
        return p

    return install


async def test_bbox_wrapped_schema_and_conversion(client, live, files, h):
    raw = {"result": {"caption": "매장", "objects": ["screen"]},
           "boxes": [{"label": "screen", "box_2d": [100, 200, 500, 900]}, {"label": "bad", "box_2d": [1, 2, 3]}]}
    p = live([LLMResult(text=json.dumps(raw))])
    fid = files.add(heic_bytes((800, 600)), "image/heic")
    body = (await client.post("/v1/i2t/analyze", json={"task": "img.detect", "images": [{"file_id": fid}], "prompt": "화면을 찾아라",
                                                        "json_schema": SCHEMA, "want_bbox": True})).json()
    assert body["json"] == {"caption": "매장", "objects": ["screen"]}
    assert body["boxes"] == [{"label": "screen", "box": [0.2, 0.1, 0.9, 0.5], "score": None, "image_index": 0}]
    call = p.calls[0]
    assert call.images[0].mime == "image/jpeg"                       # HEIC → JPEG
    assert call.json_schema["required"] == ["result", "boxes"]       # 감싼 스키마를 고유 JSON 모드로
    assert call.json_schema["properties"]["result"] == SCHEMA and "box_2d = [ymin, xmin, ymax, xmax]" in call.prompt


async def test_prompt_mode_repair(client, live, h, monkeypatch):
    monkeypatch.setenv("I2T_SUPPORTS_JSON_SCHEMA", "false")
    p = live([LLMResult(text="캡션은 매장입니다"), LLMResult(text='{"caption": "매장", "objects": []}')])
    body = (await client.post("/v1/i2t/analyze", json={"task": "img.c", "images": [{"data_b64": h.b64(h.png_bytes())}],
                                                        "prompt": "설명", "json_schema": SCHEMA})).json()
    assert body["json"] == {"caption": "매장", "objects": []} and body["fallback"] == "json_repair"
    assert p.calls[0].json_schema is None and "JSON Schema" in p.calls[0].system
    assert [r for r, _ in p.calls[1].turns] == ["assistant", "user"]


async def test_text_bbox_without_schema(client, live, h):
    p = live([LLMResult(text=json.dumps({"result": "사람 두 명", "boxes": [{"label": "person", "box_2d": [0, 0, 1000, 500]}]}))])
    body = (await client.post("/v1/i2t/analyze", json={"task": "img.p", "images": [{"data_b64": h.b64(h.png_bytes())}],
                                                        "prompt": "사람?", "want_bbox": True})).json()
    assert body["content"] == "사람 두 명" and body["json"] is None
    assert body["boxes"][0]["box"] == [0.0, 0.0, 0.5, 1.0]
    assert p.calls[0].json_schema["properties"]["result"]["type"] == "string"


def test_wrap_schema_hoists_defs():
    from pydantic import BaseModel

    class Obj(BaseModel):
        label: str

    class Out(BaseModel):
        items: list[Obj]

    s = Out.model_json_schema()
    w = wrap_schema(s)
    assert "$defs" in w and "$defs" not in w["properties"]["result"]
    from jsonschema import Draft202012Validator

    assert Draft202012Validator(w).is_valid({"result": {"items": [{"label": "a"}]}, "boxes": []})
    assert not Draft202012Validator(w).is_valid({"result": {"items": [{"x": 1}]}, "boxes": []})


def test_convert_box_formats():
    imgs = [imaging.Img(b"", "image/png", 200, 100)]
    raw = [{"label": "a", "box_2d": [10, 20, 110, 70], "image_index": 0, "confidence": 0.5}]
    assert convert_boxes(raw, "xyxy_px", imgs)[0]["box"] == [0.05, 0.2, 0.55, 0.7]
    assert convert_boxes(raw, "xyxy_1000", imgs)[0]["box"] == [0.01, 0.02, 0.11, 0.07]
    assert convert_boxes([{"label": "n", "box_2d": [0.9, 0.1, 0.2, 0.4]}], "xyxy_norm", imgs)[0]["box"] == [0.2, 0.1, 0.9, 0.4]
    assert convert_boxes(raw, "xyxy_px", imgs)[0]["score"] == 0.5
