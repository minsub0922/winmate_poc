"""§9.4 요구 대응표(SP1R) — 4쪽 PDF · 요구 12개 · 실제 kb(QM55C) · 인용 검증 · 대안 · 시트로."""
from __future__ import annotations

from sp_helpers import PDF, QM55C, upload
from sp_samples import requirement_pdf

NOTE = "이 규격서 기준으로 QM55C 대응표를 만들어 주세요"


async def _analyzed(ctx, client):
    r = await client.post("/v1/sheets", json={"start": "requirements"})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    f = await upload("B병원_로비디스플레이_요구규격서.pdf", requirement_pdf(), PDF)
    r = await client.post(f"/v1/sheets/{sid}/requirement-docs", json={"file_id": f["id"], "note": NOTE})
    assert r.status_code == 202, r.text
    await ctx.run_jobs()
    return sid


async def test_compliance_table_from_pdf(ctx, client):
    sid = await _analyzed(ctx, client)
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    comp = s["compliance"]
    assert comp["status"] == "done", comp
    doc = comp["docs"][0]
    assert (doc["format"], doc["pages"], doc["recognized"]) == ("PDF", 4, 12)       # 29: PDF · 4쪽 · 요구 항목 12개 인식
    assert s["title"] == "B 병원 로비 요구 스펙 대응표"
    assert comp["target_label"] == "QM55C"
    assert s["products"][0]["model_code"] == QM55C
    rows = {r["item"]: r for r in comp["rows"]}
    # 30: 판정
    assert (rows["화면 크기"]["value_text"], rows["화면 크기"]["verdict"]) == ('55"', "pass")
    assert (rows["해상도"]["value_text"], rows["해상도"]["verdict"]) == ("UHD", "pass")
    assert (rows["밝기"]["value_text"], rows["밝기"]["verdict"]) == ("500 nit", "pass")
    assert (rows["연속 운영"]["value_text"], rows["연속 운영"]["verdict"]) == ("24/7", "pass")
    assert (rows["원격 콘텐츠 관리"]["value_text"], rows["원격 콘텐츠 관리"]["verdict"]) == ("MagicINFO", "pass")
    w = rows["대기실 화면 크기"]
    assert (w["value_text"], w["verdict"]) == ('55"', "fail")
    assert w["alternative"]["label"] == "QM65C"
    assert (rows["소비전력"]["value_text"], rows["소비전력"]["verdict"], rows["소비전력"]["note"]) == ("—", "unknown", "On Mode 154 W만 있음")
    assert (rows["설치 인증"]["value_text"], rows["설치 인증"]["verdict"], rows["설치 인증"]["note"]) == ("—", "unknown", "담당 부서 확인")
    assert rows["무게"]["verdict"] == "pass" and rows["동작 온도"]["verdict"] == "pass" and rows["Wi-Fi"]["verdict"] == "pass"
    assert rows["보증"]["verdict"] == "unknown"
    # 31: 요약 · 에이전트 · 접힘
    assert comp["counts"] == {"pass": 8, "fail": 1, "unknown": 3}
    assert comp["agent_text"] == ("규격서에서 요구 항목 12개를 찾아 QM55C 스펙과 맞춰 봤습니다. 충족 8 · 미충족 1 · 확인 필요 3입니다. "
                                  "미충족 항목에는 대안 모델을 함께 붙였어요.")
    assert comp["folded_line"] == "4개 더 · 충족 3 · 확인 필요 1"
    assert [r["item"] for r in comp["rows"][:8]] == ["화면 크기", "해상도", "밝기", "연속 운영", "원격 콘텐츠 관리", "대기실 화면 크기", "소비전력", "설치 인증"]
    # 36: 고객 자료 호출은 모두 confidential, 상태 `확인 필요 3`(→ SP1R)
    calls = [c for c in ctx.ai.calls if c["task"].startswith("sp.")]
    assert calls and all(c["confidential"] for c in calls)
    assert (s["ui_status"], s["status_text"], s["resume_route"]) == ("check", "확인 필요 3", f"/spec/{sid}/requirements")
    # 32: 원문 쪽 — 인용이 쪽 텍스트 안에 그대로
    r = await client.get(f"/v1/sheets/{sid}/requirement-docs/{doc['id']}/pages/3")
    pv = r.json()
    assert pv["quotes"] and all(q["text"].replace(" ", "") in pv["text"].replace(" ", "") for q in pv["quotes"])
    assert pv["image_url"].endswith("/pages/3/image?w=900")


async def test_quote_not_in_page_is_unknown(ctx, client):
    import json

    from sp_helpers import MOCKS
    data = json.loads((MOCKS / "sp.extract_requirements.json").read_text(encoding="utf-8"))
    data["json"]["items"][0]["quote"] = "2.1 화면 크기는 75인치 이상으로 한다."      # 쪽 글에 없는 인용
    data["json"]["items"][0]["requirement"] = "75인치 이상"
    ctx.ai.on("sp.extract_requirements", data)
    sid = await _analyzed(ctx, client)
    comp = (await client.get(f"/v1/sheets/{sid}/compliance")).json()
    first = comp["rows"][0]
    assert first["verdict"] == "unknown" and first["note"] == "원문 확인 필요"


async def test_alternatives_and_to_items(ctx, client):
    sid = await _analyzed(ctx, client)
    comp = (await client.get(f"/v1/sheets/{sid}/compliance")).json()
    row = next(r for r in comp["rows"] if r["item"] == "대기실 화면 크기")
    # 33: 대안 보기 → SP1C(65" 켬, QM65C 선택), 대안 모델 찾기 → 65" · 75" 이상 + 필수 24시간 운영
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"preset": f"row:{row['id']}"})).json()
    assert st["conditions"]["sizes"] == ["65"]
    assert any(c["display_name"] == "QM65C" and c["selected"] for c in st["candidates"])
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"preset": "alternatives"})).json()
    assert st["conditions"]["sizes"] == ["65", "75+"]
    assert st["conditions"]["required"] == ["continuous_operation"]
    # 34: 칩 기본값 · 대안 켜면 alternative 제품
    assert comp["include"] == {"table": True, "spec": True, "page_refs": True, "alternative": False}
    r = await client.patch(f"/v1/sheets/{sid}/compliance", json={"include": {"alternative": True}})
    assert r.status_code == 200 and r.json()["include"]["alternative"] is True
    r = await client.patch(f"/v1/sheets/{sid}/compliance", json={"include": {"table": False, "spec": False}})
    assert r.status_code == 422
    # 35: 대응표로 시트 만들기 → SP2, 미리 체크 = 기본 7 ∪ 입출력 단자 · 크기 · 무게
    r = await client.post(f"/v1/sheets/{sid}/compliance:to-items")
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["step"] == 2 and s["title_confirmed"]
    checked = [i["key"] for i in s["items"] if i["checked"]]
    assert checked == ["size_resolution", "brightness_contrast", "operation_hours", "power", "player_os", "magicinfo", "warranty",
                       "io_ports", "size_weight"]
    assert {i["key"] for i in s["items"] if i["prechecked_by"] == "requirement"} == {"io_ports", "size_weight"}
    assert s["agent"]["sp2"].endswith(" 고객 요구사항과 관련된 항목을 미리 체크해 두었습니다.")
    roles = {p["display_name"]: p["role"] for p in s["products"]}
    assert roles == {"QM55C": "proposed", "QM65C": "alternative"}
    assert s["kind"] == "req"


async def test_ask_draft_and_override(ctx, client):
    sid = await _analyzed(ctx, client)
    d = (await client.get(f"/v1/sheets/{sid}/compliance/ask-draft")).json()
    assert d["count"] == 3 and "소비전력 — 200 W 이하 (원문 p.3)" in d["text"] and d["mailto"].startswith("mailto:?subject=")
    comp = (await client.get(f"/v1/sheets/{sid}/compliance")).json()
    cert = next(r for r in comp["rows"] if r["item"] == "설치 인증")
    r = await client.patch(f"/v1/sheets/{sid}/compliance/rows/{cert['id']}", json={"verdict_override": "pass", "note": "담당 부서 확인 완료"})
    assert r.status_code == 200 and r.json()["verdict"] == "pass" and r.json()["overridden"] is True
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["status_text"] == "확인 필요 2"


async def test_policy_confidential_error(ctx, client):
    ctx.ai.on("sp.extract_requirements", {"error": {"status": 403, "code": "POLICY_CONFIDENTIAL", "message": "blocked"}})
    r = await client.post("/v1/sheets", json={"start": "requirements"})
    sid = r.json()["id"]
    f = await upload("B병원_로비디스플레이_요구규격서.pdf", requirement_pdf(), PDF)
    await client.post(f"/v1/sheets/{sid}/requirement-docs", json={"file_id": f["id"]})
    await ctx.run_jobs()
    comp = (await client.get(f"/v1/sheets/{sid}/compliance")).json()
    assert comp["status"] == "failed"
    assert "보안 정책" in comp["error"]


async def test_unsupported_file(ctx, client):
    r = await client.post("/v1/sheets", json={"start": "requirements"})
    sid = r.json()["id"]
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("a.bin", b"\x00\x01" * 50)
    f = await upload("a.zip", buf.getvalue(), "application/zip")
    r = await client.post(f"/v1/sheets/{sid}/requirement-docs", json={"file_id": f["id"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "UNSUPPORTED_FILE"
