"""BE1 · BE1D · BE1P — 공간 입력 · 첨부 분류 · 도면 인식(벡터 · 래스터 · 기밀 차단) · 현장 사진 · QR 토큰(AC 6–21)."""
from __future__ import annotations

import pytest
from be_kit import create, drain, png, raster_plan, upload
from plan_fixture import lobby_plan

DESC = "강남 플래그십 스토어 1층 로비. 약 120평, 층고 4.5m, 정면이 전면 유리창이라 낮에는 밝고 저녁엔 외부에서 내부가 잘 보임. 중앙에 기둥 2개."


async def test_ac6_ac7_create_defaults_and_area(client):
    b = await create(client)
    assert b["space_chip"] == "store_lobby" and b["step"] == 1 and b["route"].endswith("/space")
    assert b["title"].startswith("새 조감도")
    # 설명 · 파일이 없으면 분석 불가(웹 버튼 비활성과 같은 규칙)
    r = await client.post(f"/v1/birdseyes/{b['id']}/space:analyze")
    assert r.status_code == 400 and r.json()["error"]["code"] == "INPUT_REQUIRED"
    r = await client.patch(f"/v1/birdseyes/{b['id']}", json={"area_pyeong": 120, "description": "매장 로비"})
    assert r.status_code == 200
    r = await client.post(f"/v1/birdseyes/{b['id']}/space:analyze")
    assert r.status_code == 202
    await drain()
    sv = (await client.get(f"/v1/birdseyes/{b['id']}/space")).json()
    assert sv["model"]["area_m2"] == 396.69
    assert sv["summary_chips"][0]["label"].startswith("120평 · 층고 3m")
    bb = (await client.get(f"/v1/birdseyes/{b['id']}")).json()
    assert bb["step"] == 2 and bb["route"].endswith("/products")


async def test_ac9_two_rooms_side_by_side(client):
    b = await create(client, description="1층 로비 약 60평, 층고 4m\n2층 라운지 약 30평")
    assert (await client.post(f"/v1/birdseyes/{b['id']}/space:analyze")).status_code == 202
    await drain()
    m = (await client.get(f"/v1/birdseyes/{b['id']}/space")).json()["model"]
    assert len(m["rooms"]) == 2
    r1, r2 = m["rooms"]
    assert r1["label"] == "1층 로비" and r2["label"] == "2층 라운지"
    x1 = max(p[0] for p in r1["outline"])
    x2 = min(p[0] for p in r2["outline"])
    assert round(x2 - x1, 2) == 0.2
    inner = [w for w in m["walls"] if w["kind"] == "interior"]
    assert len(inner) == 1
    links = [o for o in m["openings"] if o["kind"] == "door" and o["wall_id"] == inner[0]["id"]]
    assert len(links) == 1


async def test_ac22_space_parse_and_w(client):
    b = await create(client, description=DESC)
    await client.post(f"/v1/birdseyes/{b['id']}/space:analyze")
    await drain()
    sv = (await client.get(f"/v1/birdseyes/{b['id']}/space")).json()
    labels = [c["label"] for c in sv["summary_chips"]]
    assert labels[0] == "120평 · 층고 4.5m"
    assert "중앙 기둥 2개" in labels
    assert any(lab.startswith("전면 유리창") for lab in labels)
    assert sv["w_message"].startswith("로비 공간을 파악했습니다.")
    assert sv["w_message"].endswith("이 공간에 배치할 삼성 제품을 입력해 주세요.")


async def test_ac8_attachment_routing(client):
    b = await create(client)
    pdf = await upload("lobby_plan_1F.pdf", lobby_plan(), "application/pdf")
    r = await client.post(f"/v1/birdseyes/{b['id']}/attachments", json={"file_ids": [pdf]})
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["kind"] == "plan" and "/space/plan" in r.json()["route"]

    b2 = await create(client)
    jpgs = [await upload(f"site_{i}.jpg", png(pattern="noise"), "image/png") for i in range(3)]
    r = await client.post(f"/v1/birdseyes/{b2['id']}/attachments", json={"file_ids": jpgs})
    assert [i["kind"] for i in r.json()["items"]] == ["photo"] * 3
    assert r.json()["route"].endswith("/space/photos")

    b3 = await create(client)
    scan = await upload("store_plan_scan.png", raster_plan(), "image/png")
    r = await client.post(f"/v1/birdseyes/{b3['id']}/attachments", json={"file_ids": [scan]})
    assert r.json()["items"][0]["kind"] == "plan" and "/space/plan" in r.json()["route"]
    await drain()
    pv = (await client.get(f"/v1/birdseyes/{b3['id']}/plans")).json()["items"][0]
    assert pv["status"] == "recognized" and pv["kind"] == "raster"
    assert pv["model"]["columns"] and len(pv["model"]["columns"]) == 2


async def _plan(client, pdf_bytes: bytes, description: str = "") -> tuple[str, dict]:
    b = await create(client, description=description) if description else await create(client)
    fid = await upload("lobby_plan_1F.pdf", pdf_bytes, "application/pdf")
    r = await client.post(f"/v1/birdseyes/{b['id']}/plans", json={"file_id": fid})
    assert r.status_code == 202, r.text
    await drain()
    pv = (await client.get(f"/v1/birdseyes/{b['id']}/plans/{r.json()['plan_id']}")).json()
    return b["id"], pv


async def test_ac10_vector_plan(client):
    be_id, pv = await _plan(client, lobby_plan())
    assert pv["status"] == "recognized" and pv["kind"] == "vector_pdf"
    assert pv["scale_label"] == "축척 1:100 감지 · 면적 396 ㎡ (약 120평)"
    summ = {e["key"]: e["summary"] for e in pv["elements"]}
    assert summ == {"wall": "외벽 4면", "window": "전면 유리창 2구간", "door": "주출입구 1 · 뒤쪽 문 1", "column": "2개 · 600 × 600 mm",
                    "core": "EV · 계단 · 배치 제외"}
    assert pv["head"] == "5종 · 확인 2"
    q1, q2 = pv["questions"]
    assert (q1["n"], q1["title"], q1["answer"]) == (1, "치수 보정 · 정면 폭", "annotated")
    assert q1["options"][0]["label"] == "표기값 24.0 m"
    assert (q2["n"], q2["title"]) == (2, "뒤쪽 문은 어떤 문인가요?")
    assert [o["label"] for o in q2["options"]] == ["비상구", "백오피스 출입", "벽으로 처리"]
    assert pv["w_message"] == ("도면에서 공간 구조를 읽었습니다. 벽 · 창 · 문 · 기둥이 표시한 대로 맞는지 보시고, "
                               "확인이 필요한 두 곳(정면 폭 치수, 뒤쪽 문)을 정해 주세요.")
    assert pv["file_name"] == "lobby_plan_1F.pdf" and pv["file_meta"].startswith("1쪽 · ")


async def test_ac11_small_mismatch_no_question(client):
    _be, pv = await _plan(client, lobby_plan(drawn_m=23.88))
    assert all(q["kind"] != "dim" for q in pv["questions"])


async def test_ac12_ac13_answers(client):
    be_id, pv = await _plan(client, lobby_plan())
    w0 = next(w for w in pv["model"]["walls"] if w["label"] == "정면")
    assert w0["b"][0] == 24.0  # 표기값(기본) = 24.0 / 23.6 배율
    r = await client.post(f"/v1/birdseyes/{be_id}/space/answers", json={"dim_id": "d1", "choice": "computed"})
    assert r.status_code == 200, r.text
    m = r.json()
    assert next(w for w in m["walls"] if w["label"] == "정면")["b"][0] == 23.6
    assert m["area_m2"] < 396
    door_q = next(q for q in pv["questions"] if q["kind"] == "door")
    r = await client.post(f"/v1/birdseyes/{be_id}/space/answers", json={"question_id": door_q["id"], "option": "wall"})
    m = r.json()
    assert sum(1 for o in m["openings"] if o["kind"] == "door") == 1
    pv2 = (await client.get(f"/v1/birdseyes/{be_id}/plans/{pv['id']}")).json()
    assert next(e for e in pv2["elements"] if e["key"] == "door")["summary"] == "주출입구 1"


async def test_ac14_continue_with_defaults(client):
    be_id, pv = await _plan(client, lobby_plan(), description=DESC)
    r = await client.post(f"/v1/birdseyes/{be_id}/space:analyze")
    assert r.status_code == 202
    await drain()
    m = (await client.get(f"/v1/birdseyes/{be_id}/space")).json()["model"]
    door = next(o for o in m["openings"] if o["kind"] == "door" and not o.get("is_main"))
    assert door["door_type"] == "normal" and door["assumed"] is True
    assert any(a["kind"] == "door_unknown" and "출입 가능한 문" in a["text_ko"] for a in m["assumptions"])
    assert m["source"] == "plan" and m["ceiling_h"]["value"] == 4.5
    b = (await client.get(f"/v1/birdseyes/{be_id}")).json()
    assert b["step"] == 2


@pytest.fixture
def confidential_env(env, monkeypatch):
    monkeypatch.setenv("MOCK_ENFORCE_CONFIDENTIAL", "true")
    monkeypatch.setenv("I2T_ALLOW_CONFIDENTIAL", "false")
    monkeypatch.setenv("LLM_ALLOW_CONFIDENTIAL", "false")
    from winmate_common import env as _env

    _env.reset_caches()
    yield


async def test_ac15_confidential_vector_only(confidential_env, platform, monkeypatch):
    from winmate_common import testing
    from winmate_birdseye import llm
    from winmate_birdseye.main import app

    seen: list[bool] = []
    orig = llm.vision_task

    async def spy(task, images, prompt, schema=None, *, want_bbox=False, confidential=True, timeout=None):
        seen.append(confidential)
        return await orig(task, images, prompt, schema, want_bbox=want_bbox, confidential=confidential, timeout=timeout)

    monkeypatch.setattr(llm, "vision_task", spy)
    async with testing.api_client(app) as client:
        be_id, pv = await _plan(client, lobby_plan())
    assert pv["status"] == "recognized"
    assert "고객 도면이라 외부 모델 없이 기본 인식만 했어요" in pv["notices"]
    assert "plan:vector_only" in pv["meta_paths"]
    assert seen and all(seen)
    assert next(e for e in pv["elements"] if e["key"] == "door")["summary"] == "주출입구 1 · 뒤쪽 문 1"


async def test_ac16_nl_edit_remove_column(client):
    be_id, pv = await _plan(client, lobby_plan())
    r = await client.post(f"/v1/birdseyes/{be_id}/space:nl-edit", json={"text": "오른쪽 기둥은 철거됐어"})
    assert r.status_code == 202
    await drain()
    pv2 = (await client.get(f"/v1/birdseyes/{be_id}/plans/{pv['id']}")).json()
    assert next(e for e in pv2["elements"] if e["key"] == "column")["summary"] == "1개 · 600 × 600 mm"


# ── BE1P ───────────────────────────────────────────────

async def test_ac17_ac18_photos(client):
    b = await create(client, description="관제실 리뉴얼이에요. 정면 상황판 교체가 핵심이고 운영석은 2열입니다.", space_chip="control_room")
    be_id = b["id"]
    f1 = await upload("p1.jpg", png(pattern="noise"), "image/png")
    f2 = await upload("p2.jpg", png(pattern="noise", color=(90, 90, 90)), "image/png")
    f3 = await upload("p3.jpg", png(pattern="backlit"), "image/png")
    for f in (f1, f2, f3):
        assert (await client.post(f"/v1/birdseyes/{be_id}/photos", json={"file_id": f})).status_code == 202
    await drain()
    f4 = await upload("p4.jpg", png(pattern="noise"), "image/png")
    assert (await client.post(f"/v1/birdseyes/{be_id}/photos", json={"file_id": f4})).status_code == 202
    ps = (await client.get(f"/v1/birdseyes/{be_id}/photos")).json()   # 4번은 아직 인식 중
    assert ps["head"] == "인식 완료 2 · 확인 필요 1 · 인식 중 1"
    assert ps["counts"]["total"] == 4
    assert ps["dir_label"] == "4 / 4" or ps["dir_label"] == "3 / 4"
    assert ps["ceiling_label"] == "없음 · 층고는 추정값" and ps["has_ceiling"] is False
    assert ps["basis_count"] == 2
    p3 = next(p for p in ps["items"] if p["n"] == 3)
    assert p3["status"] == "backlit" and p3["status_label"] == "역광 · 창 위치가 흐려요" and p3["needs_check"]
    p1 = next(p for p in ps["items"] if p["n"] == 1)
    assert p1["status_label"] == "인식 완료 · 벽 · 상황판"
    assert ps["w_message"].startswith("사진 4장에서 관제실 구조를")
    await drain()
    ps = (await client.get(f"/v1/birdseyes/{be_id}/photos")).json()
    assert ps["dir_label"] == "4 / 4"
    r = await client.patch(f"/v1/birdseyes/{be_id}/photos/{p3['id']}", json={"accept": True})
    assert r.status_code == 200 and r.json()["status"] == "accepted"
    ps = (await client.get(f"/v1/birdseyes/{be_id}/photos")).json()
    assert ps["basis_count"] == 4
    chips = [c["label"] for c in ps["summary_chips"]]
    assert "약 45평 추정" in chips and "층고 3.2 m 추정" in chips and "상황판 벽 폭 약 9 m" in chips


async def test_ac19_facts(client):
    b = await create(client, description="관제실 리뉴얼", space_chip="control_room")
    f1 = await upload("p1.jpg", png(), "image/png")
    await client.post(f"/v1/birdseyes/{b['id']}/photos", json={"file_id": f1})
    await drain()
    r = await client.post(f"/v1/birdseyes/{b['id']}/space/facts", json={"text": "상황판 벽 폭 9m, 운영석 2열 12석"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert "상황판 벽 폭 9 m" in out["facts"] and "운영석 2열 12석" in out["facts"]
    front = next(w for w in out["model"]["walls"] if w["id"] == "w1")
    assert round(front["b"][0] - front["a"][0], 2) == 9.0 and front["dim_known"] is True
    d1 = out["model"]["dims"][0]
    assert d1["manual_m"] == 9.0 and d1["choice"] == "manual"


async def test_ac20_upload_token(client):
    b = await create(client)
    r = await client.post(f"/v1/birdseyes/{b['id']}/upload-tokens")
    assert r.status_code == 201
    tok = r.json()
    assert tok["path"] == f"/m/upload/{tok['token']}" and tok["qr"] and len(tok["qr"]) >= 21
    info = (await client.get(f"/v1/upload-tokens/{tok['token']}")).json()
    assert info["valid"] is True
    fid = await upload("phone.jpg", png(), "image/png")
    r = await client.post(f"/v1/upload-tokens/{tok['token']}/photos", json={"file_id": fid})
    assert r.status_code == 202
    ps = (await client.get(f"/v1/birdseyes/{b['id']}/photos")).json()
    assert ps["counts"]["total"] == 1
    # 30분 지난 토큰
    from winmate_birdseye.repo import repo

    await repo().patch("tokens", tok["token"], {"expires_at": "2020-01-01T00:00:00Z"})
    r = await client.post(f"/v1/upload-tokens/{tok['token']}/photos", json={"file_id": fid})
    assert r.status_code == 410 and r.json()["error"]["code"] == "TOKEN_EXPIRED"


async def test_ac21_gif_rejected(client):
    import io

    from PIL import Image

    b = await create(client)
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, "GIF")
    fid = await upload("anim.gif", buf.getvalue(), "image/gif")
    r = await client.post(f"/v1/birdseyes/{b['id']}/photos", json={"file_id": fid})
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "FILE_TYPE_UNSUPPORTED"
    assert r.json()["error"]["message"] == "JPG · PNG · HEIC만 올릴 수 있어요"
