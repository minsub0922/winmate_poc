"""T2I — mock 생성(정확한 비율 · files 저장 · 메타), 편집 대체 경로(잘라 붙이기 · 고유 마스크 · 바깥 채우기 · 생성으로 편집)."""
from __future__ import annotations

import io

import numpy as np
import pytest
from fastapi import Response
from PIL import Image

from winmate_common import testing
from winmate_ai_tools import providers
from winmate_ai_tools.providers.base import GenImage, Provider, T2IResult


def arr(data: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(data)).convert("RGB"))


def box_mask(shape: tuple[int, int], box: list[float]) -> np.ndarray:
    h, w = shape
    m = np.zeros((h, w), dtype=bool)
    x0, y0, x1, y1 = int(np.floor(box[0] * w)), int(np.floor(box[1] * h)), int(np.ceil(box[2] * w)), int(np.ceil(box[3] * h))
    m[y0:y1, x0:x1] = True
    return m


# ── 생성 ───────────────────────────────────────────────────

async def test_generate_mock_saved_with_meta(client, files):
    req = {"task": "img.generate", "prompt": "카페 메뉴보드가 있는 매장 내부", "aspect": "16:9", "n": 1,
           "metadata": {"project_id": "prj_1", "shot": 2}}
    r = await client.post("/v1/t2i/generate", json=req)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "mock" and body["fallbacks"] == [] and body["call_id"].startswith("call_")
    img = body["images"][0]
    assert (img["width"], img["height"], img["mime"]) == (1024, 576, "image/png")
    f = files.files[img["file_id"]]
    assert f["source"] == "generated" and f["mime"] == "image/png"
    meta = f["meta"]
    assert meta["task"] == "img.generate" and meta["prompt"] == req["prompt"] and meta["aspect"] == "16:9"
    assert meta["provider"] == "mock" and meta["model"] == "gemini-3.1-flash-lite-image" and meta["ai_generated"] is True
    assert meta["references"] == [] and meta["project_id"] == "prj_1" and meta["shot"] == 2
    assert Image.open(io.BytesIO(f["data"])).size == (1024, 576)


@pytest.mark.parametrize("aspect,size", [("1:1", (1024, 1024)), ("9:16", (576, 1024)), ("21:9", (1024, 439)), ("4:3", (1024, 768))])
async def test_generate_aspects(client, files, aspect, size):
    body = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "p", "aspect": aspect})).json()
    assert (body["images"][0]["width"], body["images"][0]["height"]) == size


async def test_generate_default_aspect_and_bad_aspect(client, files, monkeypatch):
    monkeypatch.setenv("T2I_DEFAULT_ASPECT", "4:3")
    body = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "p"})).json()
    assert (body["images"][0]["width"], body["images"][0]["height"]) == (1024, 768)
    r = await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "p", "aspect": "wide"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_ARGUMENT"


class CountingT2I(Provider):
    name = "fake"

    def __init__(self, size=(1344, 768)):
        self.calls = []
        self.size = size

    async def generate(self, cfg, call):
        self.calls.append(call)
        out = []
        for i in range(call.n):
            buf = io.BytesIO()
            Image.new("RGB", self.size, (10 * i, 50, 90)).save(buf, "PNG")
            out.append(GenImage(buf.getvalue(), "image/png"))
        return T2IResult(images=out, model="fake-img")


@pytest.fixture
def live_t2i(env, monkeypatch):
    testing.use_fake_redis()
    monkeypatch.setenv("MODEL_MODE", "live")
    monkeypatch.setenv("T2I_PROVIDER", "fake")

    def install(p):
        monkeypatch.setitem(providers.REGISTRY, "fake", lambda: p)
        providers.reset()
        return p

    return install


async def test_generate_loops_images_per_call(client, files, live_t2i, monkeypatch):
    p = live_t2i(CountingT2I(size=(1344, 768)))
    body = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "p", "n": 3, "seed": 7})).json()
    assert len(body["images"]) == 3 and [c.n for c in p.calls] == [1, 1, 1]
    assert [c.seed for c in p.calls] == [7, 8, 9] and body["model"] == "fake-img"
    monkeypatch.setenv("T2I_IMAGES_PER_CALL", "2")
    p.calls.clear()
    body = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "p", "n": 3})).json()
    assert len(body["images"]) == 3 and [c.n for c in p.calls] == [2, 1]


async def test_generate_crops_wrong_aspect(client, files, live_t2i):
    live_t2i(CountingT2I(size=(1024, 1024)))   # 제공자가 정사각형을 줬다
    body = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "p", "aspect": "16:9"})).json()
    assert body["fallbacks"] == ["aspect_cropped"]
    img = body["images"][0]
    assert abs(img["width"] / img["height"] - 16 / 9) < 0.01


async def test_references_dropped_and_truncated(client, files, monkeypatch, h, live_t2i):
    p = live_t2i(CountingT2I(size=(1344, 768)))
    refs = [{"file_id": files.add(h.png_bytes((20, 20), (i * 40, 0, 0))), "role": "product", "strength": "high"} for i in range(6)]
    body = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "제품 컷", "reference_images": refs})).json()
    assert body["fallbacks"] == [] and any("references_truncated" in w for w in body["warnings"])
    assert len(p.calls[0].refs) == 4 and "Image 1: product reference" in p.calls[0].prompt
    meta = files.files[body["images"][0]["file_id"]]["meta"]
    assert len(meta["references"]) == 6 and meta["references"][0]["role"] == "product"

    monkeypatch.setenv("T2I_SUPPORTS_REFERENCE_IMAGES", "false")
    p.calls.clear()
    body = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "제품 컷", "reference_images": refs[:1]})).json()
    assert body["fallbacks"] == ["references_dropped"] and p.calls[0].refs == []


async def test_gemini_unsupported_aspect_maps_and_crops(client, files, live_t2i):
    class GeminiLike(CountingT2I):
        name = "gemini"

    p = live_t2i(GeminiLike(size=(1344, 768)))
    body = (await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "p", "aspect": "2:1"})).json()
    assert p.calls[0].aspect == "16:9" and body["fallbacks"] == ["aspect_cropped"]
    img = body["images"][0]
    assert abs(img["width"] / img["height"] - 2.0) < 0.01


async def test_files_service_error_502(client, env):
    stub = testing.stub_app("files")

    @stub.post("/v1/files/bytes")
    async def boom() -> Response:
        return Response('{"error": {"code": "INTERNAL", "message": "디스크 가득", "details": {}}}', status_code=500,
                        media_type="application/json")

    with testing.inprocess({"files": stub}):
        r = await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "p"})
    assert r.status_code == 502 and r.json()["error"]["code"] == "FILES_UNAVAILABLE"


async def test_policy_t2i(client, files):
    r = await client.post("/v1/t2i/generate", json={"task": "img.g", "prompt": "고객 매장", "confidential": True})
    assert r.status_code == 403 and r.json()["error"]["details"]["env"] == "T2I_ALLOW_CONFIDENTIAL"


# ── 편집 ───────────────────────────────────────────────────

async def test_edit_mask_box_crop_paste_identity(client, files, h):
    src = h.noise_png((300, 200), seed=3)
    fid = files.add(src)
    box = [0.4, 0.4, 0.6, 0.7]
    r = await client.post("/v1/t2i/edit", json={"task": "img.edit", "image": {"file_id": fid}, "prompt": "메뉴보드 화면을 바꿔줘",
                                                "mask": {"box": box}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fallbacks"] == ["mask_crop_paste"]
    out = files.files[body["images"][0]["file_id"]]
    assert out["mime"] == "image/png" and out["meta"]["operation"] == "edit" and out["meta"]["source_file_id"] == fid
    a, b = arr(src), arr(out["data"])
    assert a.shape == b.shape
    inside = box_mask(a.shape[:2], box)
    assert np.array_equal(a[~inside], b[~inside]), "마스크 밖 픽셀은 바이트 단위로 같아야 한다"
    assert (a[inside] != b[inside]).any(axis=-1).mean() > 0.9


async def test_edit_mask_image_and_alpha_convention(client, files, h):
    src = h.noise_png((120, 90), seed=5)
    fid = files.add(src)
    m = Image.new("L", (120, 90), 0)
    m.paste(255, (10, 10, 50, 40))                  # 흰색 = 수정
    buf = io.BytesIO()
    m.save(buf, "PNG")
    body = (await client.post("/v1/t2i/edit", json={"task": "img.edit", "image": {"file_id": fid}, "prompt": "x",
                                                     "mask": {"data_b64": h.b64(buf.getvalue()), "mime": "image/png"}})).json()
    a, b = arr(src), arr(files.files[body["images"][0]["file_id"]]["data"])
    inside = np.zeros(a.shape[:2], dtype=bool)
    inside[10:40, 10:50] = True
    assert np.array_equal(a[~inside], b[~inside]) and (a[inside] != b[inside]).any()

    rgba = Image.new("RGBA", (120, 90), (0, 0, 0, 255))
    rgba.paste((0, 0, 0, 0), (60, 20, 100, 70))      # 투명 = 수정(OpenAI 방식)
    buf = io.BytesIO()
    rgba.save(buf, "PNG")
    body = (await client.post("/v1/t2i/edit", json={"task": "img.edit", "image": {"file_id": fid}, "prompt": "y",
                                                     "mask": {"data_b64": h.b64(buf.getvalue())}})).json()
    b = arr(files.files[body["images"][0]["file_id"]]["data"])
    inside = np.zeros(a.shape[:2], dtype=bool)
    inside[20:70, 60:100] = True
    assert np.array_equal(a[~inside], b[~inside]) and (a[inside] != b[inside]).any()


async def test_edit_native_mask(client, files, h, monkeypatch):
    monkeypatch.setenv("T2I_SUPPORTS_MASK", "true")   # mock 은 고유 마스크를 지원한다
    src = h.noise_png((200, 150), seed=9)
    fid = files.add(src)
    box = [0.1, 0.2, 0.5, 0.6]
    body = (await client.post("/v1/t2i/edit", json={"task": "img.edit", "image": {"file_id": fid}, "prompt": "z",
                                                     "mask": {"box": box}})).json()
    assert "mask_crop_paste" not in body["fallbacks"]
    a, b = arr(src), arr(files.files[body["images"][0]["file_id"]]["data"])
    inside = box_mask(a.shape[:2], box)
    assert np.array_equal(a[~inside], b[~inside]) and (a[inside] != b[inside]).any()


async def test_edit_outpaint_keeps_original(client, files, h):
    src = h.noise_png((200, 200), seed=11)
    fid = files.add(src)
    body = (await client.post("/v1/t2i/edit", json={"task": "img.reframe", "image": {"file_id": fid}, "prompt": "",
                                                     "aspect": "16:9"})).json()
    assert body["fallbacks"] == ["outpaint_extend"]
    img = body["images"][0]
    assert abs(img["width"] / img["height"] - 16 / 9) < 0.01 and img["height"] == 200
    out = arr(files.files[img["file_id"]]["data"])
    x0 = (img["width"] - 200) // 2
    assert np.array_equal(out[:, x0:x0 + 200], arr(src)), "원래 영역은 원본 픽셀 그대로"
    assert (out[:, :x0] != 0).any()   # 바깥은 채워졌다


async def test_edit_global_and_n(client, files, h):
    fid = files.add(h.noise_png((160, 120), seed=2))
    body = (await client.post("/v1/t2i/edit", json={"task": "img.var", "image": {"file_id": fid}, "prompt": "밤 장면으로", "n": 2})).json()
    assert len(body["images"]) == 2 and body["fallbacks"] == []
    d1, d2 = (files.files[i["file_id"]]["data"] for i in body["images"])
    assert d1 != d2 and Image.open(io.BytesIO(d1)).size == (160, 120)


async def test_edit_unsupported_paths(client, files, h, monkeypatch):
    fid = files.add(h.noise_png((100, 80), seed=4))
    monkeypatch.setenv("T2I_SUPPORTS_EDIT", "false")
    body = (await client.post("/v1/t2i/edit", json={"task": "img.var", "image": {"file_id": fid}, "prompt": "변형"})).json()
    assert body["fallbacks"] == ["edit_as_generate"]
    monkeypatch.setenv("T2I_SUPPORTS_REFERENCE_IMAGES", "false")
    r = await client.post("/v1/t2i/edit", json={"task": "img.var", "image": {"file_id": fid}, "prompt": "변형"})
    assert r.status_code == 501 and r.json()["error"]["code"] == "EDIT_UNSUPPORTED"


async def test_edit_empty_mask(client, files, h):
    fid = files.add(h.noise_png((50, 50)))
    r = await client.post("/v1/t2i/edit", json={"task": "img.e", "image": {"file_id": fid}, "prompt": "p",
                                                "mask": {"box": [0.5, 0.5, 0.5, 0.9]}})
    assert r.status_code == 400 and r.json()["error"]["code"] == "EMPTY_MASK"


async def test_crop_box_for_mask_rules():
    from winmate_ai_tools import imaging

    m = Image.new("L", (2000, 1000), 0)
    m.paste(255, (1000, 400, 1100, 500))     # 100x100
    x0, y0, x1, y1 = imaging.crop_box_for_mask(m)
    w, h = x1 - x0, y1 - y0
    assert x0 <= 1000 - 64 and y0 <= 400 - 64 and x1 >= 1100 + 64 and y1 >= 500 + 64   # 여백 ≥ 64px
    assert abs(w / h - 1.0) < 0.02                                                     # 가장 가까운 비율(1:1)로
    assert imaging.send_size(w, h)[0] == 512 or max(imaging.send_size(w, h)) == 512     # 작은 크롭은 512 로 키움
    assert imaging.send_size(3000, 1500) == (1024, 512)
