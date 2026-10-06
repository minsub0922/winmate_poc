"""IMG1 · IMG2 · IMG2R — 작업 · prefill · 참조(AC 2–12) · 작업 API."""
from __future__ import annotations

import time

from img_helpers import DESC, KB_CASE_IMAGES, b64_image, file_image, i2t_json, llm_json, new_work, png, prefilled, start_run

from winmate_common.jobs import jobs


# ── 작업 · prefill ───────────────────────────────────────

async def test_create_defaults_and_patch_conflict(env, client):
    w = await new_work(client, desc="")
    assert w["kind"] == "space" and w["conditions"] == {"products": [], "style": "photo", "aspect": "16:9", "count": 4,
                                                         "no_products": False}
    assert w["badge"]["label"] == "작성 중" and w["route"] == f"/image/new?work={w['id']}"
    r = await client.patch(f"/v1/works/{w['id']}", json={"description": DESC, "if_version": w["version"]})
    assert r.status_code == 200 and r.json()["description"] == DESC and r.json()["echo"] == f"공간 · {DESC}"
    r = await client.patch(f"/v1/works/{w['id']}", json={"kind": "background", "if_version": w["version"]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_CONFLICT"
    cur = (await client.get(f"/v1/works/{w['id']}")).json()
    r = await client.patch(f"/v1/works/{w['id']}", json={"kind": "background", "if_version": cur["version"]})
    assert r.status_code == 200 and r.json()["conditions"]["no_products"] is True
    r = await client.post("/v1/works", json={"description": "x" * 501})
    assert r.status_code == 422


async def test_prefill_ac2(env, client):
    """AC2 — 칩 「Smart Signage QM55C ×3」, 실사 렌더 · 16:9 · 4장."""
    w = await prefilled(client)
    p = w["conditions"]["products"]
    assert [(x["name"], x["short"], x["qty"], x["source"]) for x in p] == [("Smart Signage QM55C", "QM55C", 3, "prefill")]
    assert w["conditions"]["style"] == "photo" and w["conditions"]["aspect"] == "16:9" and w["conditions"]["count"] == 4
    assert w["title"] == "카페 매장 메뉴보드 시안" and w["subject_short"] == "메뉴보드"
    assert w["prefill"]["search_query"] == "카페 메뉴보드" and w["prefill"]["industry_chips"][0] == "외식 · 카페"
    assert len(w["prefill"]["industry_chips"]) == 4
    # 설명에 없는 고객사는 넣지 않는다(지어내지 않음)
    assert w["customer_name"] is None


async def test_count_two_ac3(env, client):
    """AC3 — 「2장」이면 run 의 시안이 2개."""
    w = await prefilled(client)
    acc = await start_run(client, w["id"], count=2)
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    assert run["total"] == 2 and len(run["shots"]) == 2
    w2 = (await client.get(f"/v1/works/{w['id']}")).json()
    assert w2["conditions"]["count"] == 2
    r = await client.post(f"/v1/works/{w['id']}/runs", json={"kind": "initial"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "RUN_IN_PROGRESS"


async def test_prefill_timeout_ac5(env, client, monkeypatch):
    """AC5 — LLM 이 제한을 넘기면 KB 결과만(제한 안에 돌아온다)."""
    monkeypatch.setenv("IMAGE_PREFILL_TIMEOUT_S", "1.5")
    monkeypatch.setenv("IMAGE_LLM_TIMEOUT_S", "1.0")
    env.tap.delays["img.prefill"] = 5
    w = await new_work(client, desc="카페 카운터 위 QM55C 메뉴보드가 걸린 장면")
    t0 = time.monotonic()
    r = await client.post(f"/v1/works/{w['id']}:prefill")
    took = time.monotonic() - t0
    assert r.status_code == 200 and took < 3.0
    body = r.json()
    assert body["timed_out"] is True
    assert [(p["short"], p["qty"]) for p in body["products"]] == [("QM55C", 1)]


async def test_prefill_no_products_message(env, client):
    env.tap.override("img.prefill", lambda b, n: llm_json({"title": "로비 장면", "subject_short": "로비", "products": [],
                                                           "search_query": "로비"}))
    w = await new_work(client, desc="넓은 로비 장면")
    body = (await client.post(f"/v1/works/{w['id']}:prefill")).json()
    assert body["products"] == [] and body["message"] == "제품을 찾지 못했어요. 제품명을 입력해 주세요"


async def test_add_products_from_shell_refs(env, client):
    """셸 「현재 작업에 추가」(제품) — kb:model · kb:family 참조를 KB 제품으로 풀어 조건에 더한다."""
    w = await new_work(client)
    r = await client.post(f"/v1/works/{w['id']}/products", json={"refs": ["kb:model:mdl_LH55QMCEBGCXKR", "kb:family:fam_G000182632"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["added"] == ["kb:model:mdl_LH55QMCEBGCXKR", "kb:family:fam_G000182632"]
    prods = body["work"]["conditions"]["products"]
    assert prods[0]["model_code"] == "LH55QMCEBGCXKR" and prods[0]["short"] == "QM55C" and prods[0]["name"] == "Smart Signage QM55C"
    assert prods[1]["family_id"] == "fam_G000182632" and prods[1]["model_code"] is None and prods[1]["name"]
    # 같은 제품은 두 번 넣지 않는다 · 모르는 참조는 422
    r = await client.post(f"/v1/works/{w['id']}/products", json={"refs": ["kb:model:mdl_LH55QMCEBGCXKR"]})
    assert len(r.json()["work"]["conditions"]["products"]) == 2
    r = await client.post(f"/v1/works/{w['id']}/products", json={"refs": ["kb:model:mdl_NOPE0000"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


async def test_delete_and_list(env, client):
    a = await new_work(client)
    b = await new_work(client, desc="병원 로비 배경", kind="background")
    lst = (await client.get("/v1/works")).json()
    ids = [x["id"] for x in lst["items"]]
    assert ids[:2] == [b["id"], a["id"]] and lst["totals"]["works"] == 2
    assert lst["items"][0]["meta"] == "배경 · 4장" and lst["items"][0]["time"] == "방금"
    assert (await client.get("/v1/works", params={"q": "병원"})).json()["items"][0]["id"] == b["id"]
    assert (await client.delete(f"/v1/works/{a['id']}")).status_code == 204
    assert (await client.get(f"/v1/works/{a['id']}")).status_code == 404
    assert (await client.get("/v1/works")).json()["totals"]["works"] == 1


# ── 참조(IMG2R) ─────────────────────────────────────────

async def test_topbar_refs_notice_ac4(env, client):
    """AC4 — 상단 이미지 검색에서 2장 「현재 작업에 추가」 → 썸네일 2 + 안내."""
    w = await prefilled(client)
    for ref in KB_CASE_IMAGES[:2]:
        r = await client.post(f"/v1/works/{w['id']}/references", json={"source_kind": "topbar", "source_ref": f"kb:image:{ref}"})
        assert r.status_code == 201, r.text
    w = (await client.get(f"/v1/works/{w['id']}")).json()
    assert len(w["references"]) == 2 and all(r["thumb_url"] for r in w["references"])
    assert w["ref_notice"] == "이미지 검색에서 선택한 2장이 참조로 들어갔습니다"
    assert w["references"][0]["rights"] == "customer_case" and w["references"][0]["aspects"] == ["composition"]


async def test_reference_search_ac6(env, client):
    """AC6 — 사내 자산 탭: 검색어 기본 = prefill 검색어, 「{n} 개 · 검수 완료」, 권리 official · customer_case 만."""
    w = await prefilled(client)
    r = await client.get("/v1/reference-search", params={"tab": "kb", "work_id": w["id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"] == "카페 메뉴보드"
    assert body["head"] == f"{body['total']} 개 · 검수 완료" and body["total"] > 0
    assert len(body["items"]) <= 8
    assert all(i["rights"] in ("official", "customer_case") for i in body["items"])
    page2 = (await client.get("/v1/reference-search", params={"tab": "kb", "work_id": w["id"], "cursor": body["next_cursor"]})).json() \
        if body["next_cursor"] else {"items": []}
    assert not {i["source_ref"] for i in page2["items"]} & {i["source_ref"] for i in body["items"]}
    mine = (await client.get("/v1/reference-search", params={"tab": "mine", "work_id": w["id"]})).json()
    assert mine["head"] == f"{mine['total']} 개"
    cases = (await client.get("/v1/reference-search", params={"tab": "cases", "work_id": w["id"]})).json()
    assert all(i["source_label"] == "유관 사례 · 도입사례 사진" for i in cases["items"])


async def test_apply_two_refs_ac7(env, client):
    """AC7 — 2장 · 요소 · 강도가 그대로 저장."""
    w = await prefilled(client)
    r = await client.put(f"/v1/works/{w['id']}/references", json={"items": [
        {"source_kind": "kb_asset", "source_ref": KB_CASE_IMAGES[0], "aspects": ["composition", "placement"], "strength": "mid"},
        {"source_kind": "kb_asset", "source_ref": KB_CASE_IMAGES[1], "aspects": ["color_light", "material"], "strength": "high"}]})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert [(i["aspects"], i["strength"], i["order"]) for i in items] == [(["composition", "placement"], "mid", 1),
                                                                            (["color_light", "material"], "high", 2)]
    assert items[0]["role_label"] == "구도 · 제품 배치" and items[1]["source_label"].startswith("사내 자산 · ")
    # 빼고 다시 적용(취소 = 서버 변경 없음 → 화면이 버림)
    r = await client.put(f"/v1/works/{w['id']}/references", json={"items": [
        {"source_kind": "kb_asset", "source_ref": KB_CASE_IMAGES[1], "aspects": ["color_light"], "strength": "low"}]})
    assert [(i["source_ref"], i["strength"]) for i in r.json()["items"]] == [(KB_CASE_IMAGES[1], "low")]


async def test_start_from_references_fills_description(env, client):
    """「참조 이미지로 시작」 — 설명 없이 적용하면 참조 캡션(분석 전이면 라벨)으로 장면 설명을 채워 메아리에 보인다(§4.4)."""
    r = await client.post("/v1/works", json={"start": "references"})
    w = r.json()
    assert w["description"] == "" and w["route"] == f"/image/w/{w['id']}/references"
    r = await client.put(f"/v1/works/{w['id']}/references", json={"items": [
        {"source_kind": "kb_asset", "source_ref": KB_CASE_IMAGES[0], "aspects": ["composition"], "strength": "mid"}]})
    label = r.json()["items"][0]["label"]
    w = (await client.get(f"/v1/works/{w['id']}")).json()
    assert w["description"] and len(w["description"]) >= 2 and w["echo"].startswith("공간 · ")
    assert w["description"] in (label, w["references"][0]["analysis"] and w["references"][0]["analysis"].get("caption"))
    # 이미 설명이 있으면 그대로 · 409 는 진행 중 run id 를 알려 준다
    acc = (await client.post(f"/v1/works/{w['id']}/runs", json={"kind": "initial", "count": 2})).json()
    r = await client.post(f"/v1/works/{w['id']}/runs", json={"kind": "initial", "count": 2})
    assert r.status_code == 409 and r.json()["error"]["details"]["run_id"] == acc["run_id"]


async def test_upload_strength_ac8_and_limit_ac9(env, client):
    w = await prefilled(client)
    fid = await env.upload(png(), "ref.png")
    r = await client.post(f"/v1/works/{w['id']}/references", json={"source_kind": "upload", "file_id": fid})
    assert r.status_code == 201 and r.json()["strong_allowed"] is False and r.json()["aspects"] == ["color_light"]
    rid = r.json()["id"]
    r = await client.patch(f"/v1/works/{w['id']}/references/{rid}", json={"strength": "high"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "STRENGTH_NOT_ALLOWED"
    assert r.json()["error"]["message"] == "올린 사진은 ‘중’까지 따를 수 있어요"
    for ref in KB_CASE_IMAGES[:2]:
        assert (await client.post(f"/v1/works/{w['id']}/references", json={"source_kind": "kb_asset", "source_ref": ref})).status_code == 201
    r = await client.post(f"/v1/works/{w['id']}/references", json={"source_kind": "kb_asset", "source_ref": KB_CASE_IMAGES[2]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "REFERENCE_LIMIT"
    assert r.json()["error"]["message"] == "참조는 3장까지 고를 수 있어요"


FACE = (0.25, 0.25, 0.55, 0.65)


async def _face_ref_run(env, client):
    w = await prefilled(client)
    data = png(320, 200, face=(80, 50, 176, 130))
    fid = await env.upload(data, "face.png")
    env.tap.override("img.ref_analyze", lambda b, n: i2t_json({"faces": [list(FACE)], "logos": [], "displays": [], "style": "photo",
                                                                "caption": "사람이 있는 카페"}))
    r = await client.post(f"/v1/works/{w['id']}/references", json={"source_kind": "upload", "file_id": fid, "strength": "mid"})
    assert r.status_code == 201
    await env.drain()        # 참조 분석 잡
    acc = await start_run(client, w["id"], count=2)
    await env.drain()
    return w, fid, r.json()["id"], acc


async def test_face_blur_ac10(env, client):
    """AC10 — bbox 지원: 흐린 사본을 보내고(원본은 안 보냄) 얼굴 영역 분산 ≤ 원본의 10%."""
    w, fid, rid, acc = await _face_ref_run(env, client)
    ref = (await client.get(f"/v1/works/{w['id']}/references")).json()["items"][0]
    assert ref["send_mode"] == "image" and ref["sanitized_file_id"]
    gens = env.tap.by("/v1/t2i/generate", "img.generate")
    sent = [r["file_id"] for g in gens for r in (g["body"].get("reference_images") or [])]
    assert ref["sanitized_file_id"] in sent and fid not in sent
    from winmate_image import imaging

    orig = await file_image(fid)
    blur = await file_image(ref["sanitized_file_id"])
    assert imaging.region_variance(blur, FACE) <= 0.1 * imaging.region_variance(orig, FACE)


async def test_face_text_fallback_ac10(env, client, monkeypatch):
    """AC10 — bbox 미지원: 그 참조는 이미지로 보내지 않고 send_mode=text_fallback."""
    monkeypatch.setenv("I2T_SUPPORTS_BBOX", "false")
    w, fid, rid, acc = await _face_ref_run(env, client)
    ref = (await client.get(f"/v1/works/{w['id']}/references")).json()["items"][0]
    assert ref["send_mode"] == "text_fallback"
    gens = env.tap.by("/v1/t2i/generate", "img.generate")
    sent = [r["file_id"] for g in gens for r in (g["body"].get("reference_images") or [])]
    assert fid not in sent
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    img = (await client.get(f"/v1/images/{run['shots'][0]['image_id']}")).json()
    assert "reference:sanitize_text" in img["current"]["generation"]["fallbacks"]


async def test_reference_budget_ac11(env, client, monkeypatch):
    """AC11 — 예산 3: [QM55C 단독컷, QB55C 단독컷, 강도 「강」 참조], 「중」 참조는 글(팔레트 5색)."""
    monkeypatch.setenv("T2I_MAX_REFERENCE_IMAGES", "3")
    w = await prefilled(client)
    cond = {**w["conditions"], "products": [*w["conditions"]["products"],
                                           {"family_id": "fam_G000182632", "model_code": "LH55QBCEBGCXKR", "name": "Smart Signage QB55C",
                                            "short": "QB55C", "qty": 1, "source": "user"}]}
    assert (await client.patch(f"/v1/works/{w['id']}", json={"conditions": cond})).status_code == 200
    r = await client.put(f"/v1/works/{w['id']}/references", json={"items": [
        {"source_kind": "kb_asset", "source_ref": KB_CASE_IMAGES[0], "aspects": ["color_light"], "strength": "mid"},
        {"source_kind": "kb_asset", "source_ref": KB_CASE_IMAGES[1], "aspects": ["composition"], "strength": "high"}]})
    strong = r.json()["items"][1]
    await env.drain()
    await start_run(client, w["id"], count=2)
    await env.drain()
    g = env.tap.by("/v1/t2i/generate", "img.generate")[0]["body"]
    refs = g["reference_images"]
    assert [x["role"] for x in refs] == ["product", "product", "composition"]
    assert refs[2]["file_id"] == strong["file_id"] and refs[2]["strength"] == "high"
    from winmate_image.store import repo

    shots = {d.get("file_id") for d in await repo().all("kbfiles")}
    assert refs[0]["file_id"] in shots and refs[1]["file_id"] in shots and refs[0]["file_id"] != refs[1]["file_id"]
    import re

    assert "Reference 4" in g["prompt"] and len(re.findall(r"#[0-9a-f]{6}", g["prompt"])) >= 5


async def test_no_reference_support_ac12(env, client, monkeypatch):
    """AC12 — 참조 미지원: 이미지 인자 없음, 프롬프트에 제품 화면비 · 참조 묘사, fallbacks 에 reference:text_fallback."""
    monkeypatch.setenv("T2I_SUPPORTS_REFERENCE_IMAGES", "false")
    w = await prefilled(client)
    await client.post(f"/v1/works/{w['id']}/references", json={"source_kind": "kb_asset", "source_ref": KB_CASE_IMAGES[0]})
    await env.drain()
    acc = await start_run(client, w["id"], count=2)
    await env.drain()
    g = env.tap.by("/v1/t2i/generate", "img.generate")[0]["body"]
    assert not g.get("reference_images")
    assert "16:9 landscape panel, thin black bezel" in g["prompt"] and "Reference 1" in g["prompt"]
    run = (await client.get(f"/v1/runs/{acc['run_id']}")).json()
    img = (await client.get(f"/v1/images/{run['shots'][0]['image_id']}")).json()
    assert "reference:text_fallback" in img["current"]["generation"]["fallbacks"]


async def test_capabilities(env, client, monkeypatch):
    body = (await client.get("/v1/capabilities")).json()
    assert body["features"]["object_select"] is True and body["upscaler"] == "none" and body["features"]["upscale_4x"] is False
    monkeypatch.setenv("I2T_SUPPORTS_BBOX", "false")
    from winmate_image import caps

    caps.reset()
    body = (await client.get("/v1/capabilities")).json()
    assert body["features"]["object_select"] is False


async def test_requires_internal_token(env):
    import httpx
    from winmate_image.main import app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/v1/works")
        assert r.status_code == 401


_ = (b64_image, jobs)
