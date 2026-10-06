"""IMG2P · 현장 사진 합성(AC 45–48) — 인식 · 축척 · 결정적 합성 → t2i.edit · 기밀 차단 로컬 경로."""
from __future__ import annotations

import io
import re

from img_helpers import i2t_json
from PIL import Image

QM55C = {"family_id": "fam_G000182628", "model_code": "LH55QMCEBGCXKR", "name": "Smart Signage QM55C", "short": "QM55C", "qty": 3,
         "source": "user"}


def photo_png(w: int = 1125, h: int = 844, gray: int = 170) -> bytes:
    im = Image.new("RGB", (w, h), (gray, gray - 6, gray - 14))
    from PIL import ImageDraw

    d = ImageDraw.Draw(im)
    d.rectangle([int(w * 0.1), int(h * 0.56), int(w * 0.9), int(h * 0.88)], fill=(max(0, gray - 60), max(0, gray - 80), max(0, gray - 100)))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


async def composite_work(env, client, data: bytes | None = None) -> tuple[dict, dict]:
    r = await client.post("/v1/works", json={"start": "composite"})
    assert r.status_code == 201, r.text
    w = r.json()
    assert w["kind"] == "composite" and w["route"] == f"/image/w/{w['id']}/composite" and w["badge"]["label"] == "제품 위치 지정 중"
    w = (await client.patch(f"/v1/works/{w['id']}", json={"conditions": {**w["conditions"], "products": [QM55C]}})).json()
    fid = await env.upload(data or photo_png(), "site.png", confidential=True)
    r = await client.post(f"/v1/works/{w['id']}/site-photos", json={"file_id": fid})
    assert r.status_code == 202, r.text
    assert r.json()["photo"]["status"] == "recognizing" and r.json()["photo"]["status_label"] == "인식 중"
    await env.drain()
    photos = (await client.get(f"/v1/works/{w['id']}/site-photos")).json()["items"]
    return (await client.get(f"/v1/works/{w['id']}")).json(), photos[0]


async def test_recognize_and_default_placement(env, client):
    w, p = await composite_work(env, client)
    assert p["status"] == "recognized" and p["status_label"] == "벽면 인식 완료" and p["label"] == "카운터 벽면"
    assert p["message"].startswith("카운터 위 흰 벽면을 설치 가능한 면으로 인식하고 QM55C 3대를 올려두었습니다.")
    comp = w["composite"]
    assert comp["active_photo_id"] == p["id"] and len(comp["groups"]) == 1
    g = comp["groups"][0]
    assert g["arrangement"] == "row3" and g["qty"] == 3 and len(g["quad"]) == 4
    assert w["title"] == "카운터 벽면 합성"
    assert comp["measures"][0]["label_text"].startswith("가로 약 3,730 mm · 바닥에서 ")
    # 기밀 호출: 인식 i2t 는 confidential=true
    assert all(c["body"]["confidential"] for c in env.tap.by("/v1/i2t/analyze", "img.recognize_photo"))


async def test_dark_photo_ac45(env, client):
    w, p = await composite_work(env, client, photo_png(gray=40))
    assert p["quality"]["luma_mean"] < 0.22
    assert p["status"] == "low_light" and p["status_label"] == "어두워 인식 어려움 · 다시 촬영 권장"


async def test_scale_from_counter_ac46(env, client):
    w, p = await composite_work(env, client)
    g = w["composite"]["groups"][0]
    r = await client.put(f"/v1/works/{w['id']}/placements", json={"photo_id": p["id"], "groups": [g],
                                                                    "ref_dims": {"counter_width_mm": 3600}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scale"]["method"] == "ref_dim" and abs(body["scale"]["mm_per_px"] - 4.0) < 1e-6
    m = body["groups"][0]
    assert m["width_mm"] == 3730 and re.fullmatch(r"가로 약 3,730 mm · 바닥에서 [\d,]+ mm", m["label_text"]), m
    assert m["fit_quad"] and len(m["fit_quad"]) == 4
    # 설치 높이를 주면 그대로
    r = await client.put(f"/v1/works/{w['id']}/placements", json={"photo_id": p["id"], "groups": [g],
                                                                    "ref_dims": {"counter_width_mm": 3600, "install_height_mm": 1800}})
    assert r.json()["groups"][0]["label_text"] == "가로 약 3,730 mm · 바닥에서 1,800 mm"


async def test_scale_unknown_keeps_placeholder_ac46(env, client):
    env.tap.override("img.recognize_photo", lambda b, n: i2t_json({"label": "매장 안쪽", "surfaces": [
        {"label": "안쪽 벽", "kind": "wall", "quad": [[0.2, 0.1], [0.8, 0.1], [0.8, 0.6], [0.2, 0.6]], "installable": True}],
        "objects": [], "floor_line": None}))
    w, p = await composite_work(env, client)
    g = w["composite"]["groups"][0]
    body = (await client.put(f"/v1/works/{w['id']}/placements", json={"photo_id": p["id"], "groups": [g]})).json()
    assert body["scale"]["method"] == "none" and body["groups"][0]["label_text"] == "가로 약 [00] mm · 바닥에서 [00] mm"


async def test_composite_run_edit_then_check_ac47(env, client):
    w, p = await composite_work(env, client)
    r = await client.post(f"/v1/works/{w['id']}/runs", json={"kind": "composite"})
    assert r.status_code == 202, r.text
    acc = r.json()
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    assert run["total"] == 4 and run["kind"] == "composite"
    await env.drain()
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    assert run["status"] == "succeeded" and run["done"] == 4
    edits = env.tap.by("/v1/t2i/edit", "img.composite")
    assert len(edits) == 4 and all(c["body"]["confidential"] for c in edits)
    for s in run["shots"]:
        gen = (await client.get(f"/v1/images/{s['image_id']}")).json()["current"]["generation"]
        assert gen["draft_file_id"] in {c["body"]["image"]["file_id"] for c in edits}
        assert gen["call"] == "t2i.edit" or "composite:local_only" in gen["fallbacks"]
        assert gen["confidential"] is True


async def test_confidential_blocked_local_path_ac48(env, client, monkeypatch):
    for k, v in {"MOCK_ENFORCE_CONFIDENTIAL": "true", "T2I_ALLOW_CONFIDENTIAL": "false", "I2T_ALLOW_CONFIDENTIAL": "false",
                 "LLM_ALLOW_CONFIDENTIAL": "false"}.items():
        monkeypatch.setenv(k, v)
    w, p = await composite_work(env, client)
    assert p["status"] == "manual" and p["status_label"] == "면을 직접 맞춰 주세요"
    r = await client.post(f"/v1/works/{w['id']}/runs", json={"kind": "composite"})
    assert r.status_code == 202
    await env.drain()
    run = (await client.get(f"/v1/runs/{r.json()['run_id']}")).json()
    assert run["status"] == "succeeded" and run["done"] == 4
    for s in run["shots"]:
        gen = (await client.get(f"/v1/images/{s['image_id']}")).json()["current"]["generation"]
        assert gen["call"] == "local" and "composite:local_only" in gen["fallbacks"] and "screen:template" in gen["fallbacks"]
    bodies = [c["body"] for c in env.tap.calls if isinstance(c["body"], dict) and "confidential" in c["body"]]
    assert bodies and all(b["confidential"] is True for b in bodies)


async def test_add_product_creates_group(env, client):
    """IMG2P 「제품 추가」(셸 현재 작업에 추가) — 인식된 사진이 있으면 배치 그룹이 하나 더 생긴다."""
    w, p = await composite_work(env, client)
    r = await client.post(f"/v1/works/{w['id']}/products", json={"refs": ["kb:model:mdl_LH55QBCEBGCXKR"]})
    assert r.status_code == 200, r.text
    comp = r.json()["work"]["composite"]
    assert [g["label"] for g in comp["groups"]] == ["QM55C", "QB55C"]
    assert len(comp["measures"]) == 2 and all(len(g["quad"]) == 4 for g in comp["groups"])
