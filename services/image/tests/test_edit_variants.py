"""IMG3 · IMG3E · IMG3V — 보정 · 부분 수정 · 변형 · 비율/해상도 · 버전(AC 29–44, 57)."""
from __future__ import annotations

import numpy as np
from img_helpers import b64_image, done_run, file_image, i2t_json

from winmate_image import config, imaging

R_FREE = [0.10, 0.50, 0.40, 0.80]           # 제품 박스와 겹치지 않는 영역
CENTER_QC = {"product_count": 3, "products": [{"box": [0.32, 0.30, 0.42, 0.48], "kind": "display"},
                                              {"box": [0.45, 0.30, 0.55, 0.48], "kind": "display"},
                                              {"box": [0.58, 0.30, 0.68, 0.48], "kind": "display"}],
             "logo_visible": False, "brand_text": False, "identifiable_faces": 0, "gibberish_text": False}


async def first_image(env, client, count: int = 2) -> tuple[dict, dict, dict]:
    w, run = await done_run(env, client, count=count)
    img = (await client.get(f"/v1/images/{run['shots'][0]['image_id']}")).json()
    return w, run, img


async def master(version: dict):
    return await file_image(version["master_file_id"])


def luma_mean(im) -> float:
    return float(imaging.luma(im).mean())


async def test_result_labels_ac29(env, client):
    w, run, img = await first_image(env, client)
    assert run["shots"][0]["label"] == "시안 1" and img["aspect"] == "16:9" and img["style"] == "photo"
    assert config.STYLE_SHORT[img["style"]] == "실사"
    assert img["rights"] == "generated" and img["caption_rule"] == "생성 이미지" and img["file_id"]
    assert img["scene"]["products"] == ["Smart Signage QM55C"] and img["prompt"]


async def test_brighten_ac30(env, client):
    w, run, img = await first_image(env, client)
    calls = len(env.tap.calls)
    r = await client.post(f"/v1/images/{img['id']}/adjust", json={"preset": "brighten"})
    assert r.status_code == 200, r.text
    v = r.json()
    assert v["op"] == "adjust" and v["n"] == 2 and v["label"] == "보정 1" and v["is_current"] is True
    assert luma_mean(await master(v)) > luma_mean(await master(img["current"]))
    assert len(env.tap.calls) == calls          # 모델 호출 0회


async def test_info_rows(env, client):
    w, run, img = await first_image(env, client)
    info = (await client.get(f"/v1/images/{img['id']}/info")).json()
    rows = {r["k"]: r for r in info["rows"]}
    assert rows["원본"]["v"].startswith("1024×576 · PNG · ") and "생성 " in rows["원본"]["v"]
    assert rows["저장본"]["v"] == "1920×1080 · 업스케일(lanczos3+unsharp)"
    assert rows["사용 조건"]["v"] == "“AI 생성 이미지” 표기 권장 · 대외 사용 범위 확인 필요"
    assert rows["사용 이력"]["v"] == "Winmate 제안서 0건" and rows["출처 페이지"]["href"].startswith(f"/image/w/{w['id']}/result")


# ── 부분 수정 ───────────────────────────────────────────

async def _apply_rect(client, env, img_id: str, rect, instruction="계절 음료 사진 3장으로 바꾸고 글자는 빼줘"):
    r = await client.post(f"/v1/images/{img_id}/regions", json={"shape": "rect", "rect": rect, "instruction": instruction})
    assert r.status_code == 201, r.text
    region = r.json()["region"]
    r = await client.post(f"/v1/images/{img_id}/edits", json={"region_ids": [region["id"]], "mode": "region"})
    assert r.status_code == 202, r.text
    await env.drain()
    return region, r.json()


async def test_region_crop_paste_ac32(env, client, monkeypatch):
    monkeypatch.setenv("T2I_SUPPORTS_MASK", "false")
    env.tap.override("img.region_name", lambda b, n: i2t_json({"name": "가운데 메뉴보드 화면"}))
    w, run, img = await first_image(env, client)
    region, acc = await _apply_rect(client, env, img["id"], R_FREE)
    detail = (await client.get(f"/v1/images/{img['id']}")).json()
    cur = detail["current"]
    assert cur["n"] == 2 and cur["label"] == "수정 1 · 영역 1" and cur["short_label"] == "수정 1"
    assert detail["versions"][0]["short_label"] == "원본"
    reg = (await client.get(f"/v1/images/{img['id']}/regions")).json()["items"][0]
    assert reg["status"] == "applied" and reg["status_label"] == "적용됨 · 비교 중" and reg["result_version_id"] == cur["id"]
    assert reg["label"] == "가운데 메뉴보드 화면"
    base, new = await master(img["current"]), await master(cur)
    mask = imaging.rect_mask(base.size, R_FREE)
    assert imaging.verify_outside(base, new, mask, 8)
    x0, y0, x1, y1 = (int(R_FREE[0] * 1920) + 12, int(R_FREE[1] * 1080) + 12, int(R_FREE[2] * 1920) - 12, int(R_FREE[3] * 1080) - 12)
    diff = np.abs(np.asarray(base.crop((x0, y0, x1, y1)), np.float32) - np.asarray(new.crop((x0, y0, x1, y1)), np.float32)).mean()
    assert diff > 5
    assert "mask:crop_paste" in cur["generation"]["fallbacks"]
    edit_calls = env.tap.by("/v1/t2i/edit", "img.edit")
    assert len(edit_calls) == 1 and edit_calls[0]["body"]["mask"]["data_b64"]


async def test_region_native_mask_ac33(env, client, monkeypatch):
    monkeypatch.setenv("T2I_SUPPORTS_MASK", "true")
    w, run, img = await first_image(env, client)
    await _apply_rect(client, env, img["id"], R_FREE)
    calls = env.tap.by("/v1/t2i/edit", "img.edit")
    assert len(calls) == 1 and calls[0]["body"]["image"]["file_id"] == img["current"]["master_file_id"] and calls[0]["body"]["mask"]
    cur = (await client.get(f"/v1/images/{img['id']}")).json()["current"]
    assert "mask:crop_paste" not in cur["generation"]["fallbacks"]
    base, new = await master(img["current"]), await master(cur)
    assert imaging.verify_outside(base, new, imaging.rect_mask(base.size, R_FREE), 8)


async def test_no_bbox_chips_ac34(env, client, monkeypatch):
    monkeypatch.setenv("I2T_SUPPORTS_BBOX", "false")
    w, run, img = await first_image(env, client)
    caps_ = (await client.get("/v1/capabilities")).json()
    assert caps_["features"]["object_select"] is False
    r = await client.post(f"/v1/images/{img['id']}/regions", json={"preset": "erase_text"})
    body = r.json()
    assert r.status_code == 201 and body["region"] is None and body["note"] == "자동 영역 인식이 없어 전체 이미지에 적용해요"
    assert body["global_instruction"] == "글자를 지우고 주변과 자연스럽게 채워줘"
    r = await client.post(f"/v1/images/{img['id']}/regions", json={"shape": "object", "detection_id": "det_1"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "CAPABILITY_UNSUPPORTED"
    r = await client.post(f"/v1/images/{img['id']}/detections", json={"kinds": ["text"]})
    assert r.status_code == 422


async def test_object_select_and_presets(env, client):
    w, run, img = await first_image(env, client)
    det = (await client.post(f"/v1/images/{img['id']}/detections", json={"kinds": ["screen", "text", "person"]})).json()
    assert det["supported"] and any(b["kind"] == "screen" for b in det["boxes"])
    screen = next(b for b in det["boxes"] if b["kind"] == "screen")
    r = await client.post(f"/v1/images/{img['id']}/regions", json={"shape": "object", "detection_id": screen["id"]})
    assert r.status_code == 201 and r.json()["region"]["rect"] == screen["box"]
    r = await client.post(f"/v1/images/{img['id']}/regions", json={"preset": "erase_people"})
    reg = r.json()["region"]
    assert reg["instruction"] == "사람을 지우고 배경을 자연스럽게 채워줘" and reg["label"] == "손님"
    r = await client.post(f"/v1/images/{img['id']}/regions", json={"preset": "screen_content"})
    assert r.json()["region"]["instruction"] == "계절 음료 사진 3장으로 화면을 채우고 글자는 빼줘"


async def test_protect_products_band_ac35(env, client):
    w, run, img = await first_image(env, client)
    box = [0.40, 0.12, 0.60, 0.32]           # QC 픽스처 제품 박스(가운데)
    rect = [0.35, 0.05, 0.65, 0.45]
    await _apply_rect(client, env, img["id"], rect, instruction="벽 색을 바꿔줘")
    cur = (await client.get(f"/v1/images/{img['id']}")).json()["current"]
    base, new = await master(img["current"]), await master(cur)
    W, H = base.size
    band = np.zeros((H, W), bool)
    x0, y0, x1, y1 = int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)
    band[y0 + 2:y1 - 2, x0 + 2:x1 - 2] = True          # 경계 래스터 오차 2px 를 빼고 띠 안쪽만 본다
    ix, iy = (x1 - x0) * 0.03, (y1 - y0) * 0.03
    band[int(y0 + iy) - 2:int(y1 - iy) + 3, int(x0 + ix) - 2:int(x1 - ix) + 3] = False
    a, b = np.asarray(base), np.asarray(new)
    assert np.array_equal(a[band], b[band])
    assert not np.array_equal(a, b)


async def test_revert_region_ac36(env, client):
    w, run, img = await first_image(env, client)
    region, _ = await _apply_rect(client, env, img["id"], R_FREE)
    r = await client.post(f"/v1/images/{img['id']}/regions/{region['id']}:revert")
    assert r.status_code == 200 and r.json()["current_version_id"] == img["current"]["id"]
    assert r.json()["region"]["status"] == "reverted"
    detail = (await client.get(f"/v1/images/{img['id']}")).json()
    assert detail["current"]["label"] == "원본" and [v["label"] for v in detail["versions"]] == ["원본", "수정 1 · 영역 1"]


async def test_two_regions_sequential_ac37(env, client):
    env.tap.sequence("img.region_name", [i2t_json({"name": "가운데 메뉴보드 화면"}), i2t_json({"name": "오른쪽 카운터 소품"})])
    w, run, img = await first_image(env, client)
    a = (await client.post(f"/v1/images/{img['id']}/regions", json={"shape": "rect", "rect": [0.05, 0.5, 0.3, 0.8],
                                                                     "instruction": "화분을 넣어줘"})).json()["region"]
    b = (await client.post(f"/v1/images/{img['id']}/regions", json={"shape": "rect", "rect": [0.7, 0.55, 0.95, 0.85],
                                                                     "instruction": "원두 보관통 지우기"})).json()["region"]
    assert (a["n"], b["n"]) == (1, 2) and b["label"] == "오른쪽 카운터 소품"
    r = await client.post(f"/v1/images/{img['id']}/edits", json={"mode": "region"})
    assert r.status_code == 202
    await env.drain()
    detail = (await client.get(f"/v1/images/{img['id']}")).json()
    assert [v["n"] for v in detail["versions"]] == [1, 2, 3]
    regs = {x["id"]: x for x in (await client.get(f"/v1/images/{img['id']}/regions")).json()["items"]}
    v2 = next(v for v in detail["versions"] if v["n"] == 2)
    v3 = next(v for v in detail["versions"] if v["n"] == 3)
    assert regs[a["id"]]["result_version_id"] == v2["id"] and regs[b["id"]]["result_version_id"] == v3["id"]
    assert v3["parent_version_id"] == v2["id"] and v3["label"] == "수정 2 · 영역 2"


async def test_restore_version_ac57(env, client):
    w, run, img = await first_image(env, client)
    await client.post(f"/v1/images/{img['id']}/adjust", json={"preset": "brighten"})
    await client.post(f"/v1/images/{img['id']}/adjust", json={"brightness": -0.1})
    r = await client.post(f"/v1/images/{img['id']}/versions/1/restore")
    assert r.status_code == 200
    v = r.json()
    assert v["n"] == 4 and v["master_file_id"] == img["current"]["master_file_id"] and v["is_current"]
    assert [x["n"] for x in (await client.get(f"/v1/images/{img['id']}/versions")).json()["items"]] == [1, 2, 3, 4]


# ── 변형 ────────────────────────────────────────────────

async def _variants(env, client, img_id: str, **body):
    r = await client.post(f"/v1/images/{img_id}/variants", json={"count": 4, **body})
    assert r.status_code == 202, r.text
    await env.drain()
    return (await client.get(f"/v1/runs/{r.json()['run_id']}")).json()


async def test_variants_edit_ac38(env, client):
    w, run, img = await first_image(env, client)
    vr = await _variants(env, client, img["id"])
    assert vr["status"] == "succeeded" and vr["kind"] == "variants" and vr["base_image_id"] == img["id"]
    assert [s["label"] for s in vr["shots"]] == ["A · 오후 자연광", "B · 저녁 조명", "C · 측면 시점", "D · 메뉴보드 근접"]
    calls = env.tap.by("/v1/t2i/edit", "img.variant")
    assert len(calls) == 4 and all(c["body"]["image"]["file_id"] == img["current"]["master_file_id"] for c in calls)
    work = (await client.get(f"/v1/works/{w['id']}")).json()
    assert work["route"] == f"/image/w/{w['id']}/result"
    more = await _variants(env, client, img["id"])
    assert [s["letter"] for s in more["shots"]] == ["E", "F", "G", "H"]


async def test_variants_ref_and_text_ac39(env, client, monkeypatch):
    w, run, img = await first_image(env, client)
    monkeypatch.setenv("T2I_SUPPORTS_EDIT", "false")
    from winmate_image import caps

    caps.reset()
    vr = await _variants(env, client, img["id"])
    gens = env.tap.by("/v1/t2i/generate", "img.variant")
    assert len(gens) == 4 and gens[0]["body"]["reference_images"][0]["role"] == "base"
    assert all(s["layout_note"] is None for s in vr["shots"])
    monkeypatch.setenv("T2I_SUPPORTS_REFERENCE_IMAGES", "false")
    caps.reset()
    vr = await _variants(env, client, img["id"])
    assert all(s["layout_note"] == "배치가 조금 달라질 수 있어요" for s in vr["shots"])
    v = (await client.get(f"/v1/images/{vr['shots'][0]['image_id']}")).json()
    assert "variant:text" in v["current"]["generation"]["fallbacks"]


# ── 비율 · 해상도 ───────────────────────────────────────

def test_resolution_ladder_ac40():
    assert [config.size_for(a, "uhd") for a in ("16:9", "4:3", "1:1", "9:16")] == [(3840, 2160), (2880, 2160), (2160, 2160), (2160, 3840)]
    assert [config.size_for(a, "fhd") for a in ("16:9", "4:3", "1:1", "9:16")] == [(1920, 1080), (1440, 1080), (1080, 1080), (1080, 1920)]
    assert [config.size_for(a, "uhd8k") for a in ("16:9", "9:16")] == [(7680, 4320), (4320, 7680)]
    assert [config.size_for(a, "native") for a in ("16:9", "4:3", "1:1", "9:16")] == [(1024, 576), (1024, 768), (1024, 1024), (576, 1024)]


async def test_upscale_4x_disabled_ac40(env, client):
    w, run, img = await first_image(env, client)
    r = await client.post(f"/v1/images/{img['id']}/renditions", json={"aspects": ["16:9"], "fit": "crop", "upscale": "4x"})
    assert r.status_code == 422 and r.json()["error"]["message"] == "×4는 업스케일 모델이 있어야 해요"


async def _renditions(env, client, img_id: str, **body):
    r = await client.post(f"/v1/images/{img_id}/renditions", json=body)
    assert r.status_code == 202, r.text
    await env.drain()
    return (await client.get(f"/v1/runs/{r.json()['run_id']}")).json()


async def test_recompose_two_aspects_ac41(env, client):
    w, run, img = await first_image(env, client)
    gens0, edits0 = len(env.tap.by("/v1/t2i/generate")), len(env.tap.by("/v1/t2i/edit"))
    rr = await _renditions(env, client, img["id"], aspects=["16:9", "9:16"], fit="recompose", upscale="2x")
    assert rr["status"] == "succeeded" and [s["label"] for s in rr["shots"]] == ["시안 1 · 16:9", "시안 1 · 9:16"]
    assert len(env.tap.by("/v1/t2i/generate")) - gens0 == 1 and len(env.tap.by("/v1/t2i/edit")) == edits0
    for s, size in zip(rr["shots"], [(3840, 2160), (2160, 3840)]):
        d = (await client.get(f"/v1/images/{s['image_id']}")).json()
        assert d["base_image_id"] == img["id"]
        uhd = next(r for r in d["current"]["renditions"] if r["kind"] == "uhd")
        assert (uhd["w"], uhd["h"]) == size and uhd["method"] == "lanczos3+unsharp"


async def test_crop_contains_products_ac42(env, client):
    env.tap.override("img.qc", lambda b, n: i2t_json(CENTER_QC))
    w, run, img = await first_image(env, client)
    before = len(env.tap.by("/v1/t2i/generate")) + len(env.tap.by("/v1/t2i/edit"))
    rr = await _renditions(env, client, img["id"], aspects=["1:1"], fit="crop", upscale="1x")
    assert len(env.tap.by("/v1/t2i/generate")) + len(env.tap.by("/v1/t2i/edit")) == before
    d = (await client.get(f"/v1/images/{rr['shots'][0]['image_id']}")).json()
    assert (d["current"]["width"], d["current"]["height"]) == (1080, 1080)
    win = imaging.crop_window(1920, 1080, 1.0, [p["box"] for p in CENTER_QC["products"]])
    for p in CENTER_QC["products"]:
        b = p["box"]
        assert win[0] <= b[0] * 1920 and win[2] >= b[2] * 1920 and win[1] <= b[1] * 1080 and win[3] >= b[3] * 1080


async def test_outpaint_canvas_ac43(env, client):
    w, run, img = await first_image(env, client)
    rr = await _renditions(env, client, img["id"], aspects=["9:16"], fit="outpaint", upscale="1x")
    call = env.tap.by("/v1/t2i/edit", "img.outpaint")[0]
    assert b64_image(call["body"]["image"]["data_b64"]).size == (576, 1024)
    d = (await client.get(f"/v1/images/{rr['shots'][0]['image_id']}")).json()
    mad = next(c for c in d["current"]["qc"]["checks"] if c["key"] == "original_area_mad")
    assert mad["value"] < 1 and (d["current"]["width"], d["current"]["height"]) == (1080, 1920)


async def test_upscale_method_info_ac44(env, client):
    w, run, img = await first_image(env, client)
    rr = await _renditions(env, client, img["id"], aspects=["16:9"], fit="crop", upscale="2x")
    sid = rr["shots"][0]["image_id"]
    d = (await client.get(f"/v1/images/{sid}")).json()
    uhd = next(r for r in d["current"]["renditions"] if r["kind"] == "uhd")
    assert uhd["method"] == "lanczos3+unsharp"
    info = (await client.get(f"/v1/images/{sid}/info")).json()
    row = next(r for r in info["rows"] if r["k"] == "저장본")
    assert row["v"] == "3840×2160 · 업스케일(lanczos3+unsharp)"
