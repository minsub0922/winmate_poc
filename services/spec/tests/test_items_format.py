"""§9.5 항목 · 형식(SP2) · §9.6 출력 형식 · 언어 · 단위(SP2L) · §9.13 비기능 일부."""
from __future__ import annotations

from typing import Any

from sp_helpers import QB55C, QM55C, XLSX, upload
from sp_samples import template_xlsx


async def _sheet(client, models=(QM55C, QB55C)) -> str:
    r = await client.post("/v1/sheets", json={"start": "model", "products": list(models)})
    sid = r.json()["id"]
    await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    return sid


def grid_rows(pv: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {r["cells"][0]["text"]: r["cells"][1:] for r in pv["grid"]["rows"][2:]}


async def test_items_and_diff(ctx, client):
    sid = await _sheet(client)
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    # 38: 켬 칩 7개 · 비교표 · 한국어 · 우위 하이라이트
    assert len([i for i in s["items"] if i["checked"]]) == 7
    assert (s["kind"], s["format"]["language"], s["options"]["highlight_wins"]) == ("compare", "ko", True)
    # 39: 차이 있는 항목만
    diff = (await client.get(f"/v1/sheets/{sid}/diff-items")).json()["different"]
    assert {"brightness_contrast", "operation_hours", "io_ports"} <= set(diff)
    assert not ({"size_resolution", "size_weight", "bezel", "power", "warranty"} & set(diff))
    # 우위 하이라이트 끄기 · 제품별 개별 시트
    s = (await client.put(f"/v1/sheets/{sid}/items", json={"highlight_wins": False, "layout": "per_product"})).json()
    assert s["options"]["highlight_wins"] is False and s["layout"] == "per_product"


async def test_format_preview_units(ctx, client):
    sid = await _sheet(client)
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    items = [{"key": i["key"], "checked": i["checked"] or i["key"] == "size_weight"} for i in s["items"]]
    await client.put(f"/v1/sheets/{sid}/items", json={"items": items})
    body = {"formats": ["xlsx", "pdf"], "language": "en", "length_unit": "inch", "weight_unit": "lb", "paper": "a4_landscape",
            "number_format": "1,234.5", "filename_base": None, "tab": "xlsx"}
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json=body)).json()
    rows = grid_rows(pv)
    # 42
    assert [c["text"] for c in rows["Dimensions (W × H × D)"]] == ["48.7 × 27.9 × 1.1 in"] * 2
    assert [c["text"] for c in rows["Weight (Set / Package)"]] == ["34.6 lb / 43.9 lb"] * 2
    assert all(c["converted"] for c in rows["Dimensions (W × H × D)"] + rows["Weight (Set / Package)"])
    assert pv["converted_cells"] == 4
    assert pv["note_line"] == "단위 바뀐 셀 4개 · 소수점 첫째 자리 반올림 · mm 원래 값은 셀 메모에 보관"
    assert pv["chip_label"] == "English · inch · lb" and pv["sheet_tabs"] == ["Comparison", "Notes & Sources"]
    assert pv["grid"]["rows"][0]["cells"][0]["text"] == 'Samsung Smart Signage 55" Comparison'
    # 45: 파일명 · 확장자
    assert pv["filename_default"] == "Samsung_Signage_55_Comparison_EN" and pv["ext_line"] == ".xlsx · .pdf"
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json={**body, "formats": ["pptx"]})).json()
    assert pv["ext_line"] == ".pptx"
    # 43
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json={**body, "language": "ko", "length_unit": "mm"})).json()
    assert pv["note_line"] == "단위 바뀐 셀 2개 · 소수점 첫째 자리 반올림 · kg 원래 값은 셀 메모에 보관"
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json={**body, "language": "ko", "weight_unit": "kg"})).json()
    assert pv["note_line"] == "단위 바뀐 셀 2개 · 소수점 첫째 자리 반올림 · mm 원래 값은 셀 메모에 보관"
    # 44: 숫자 형식
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json={**body, "number_format": "1.234,5"})).json()
    assert grid_rows(pv)["Dimensions (W × H × D)"][0]["text"] == "48,7 × 27,9 × 1,1 in"
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json={**body, "language": "ko", "length_unit": "mm", "weight_unit": "kg",
                                                                      "number_format": "1.234,5"})).json()
    assert grid_rows(pv)["크기 (W×H×D)"][0]["text"] == "1.237,9×708,8×28,5 mm"
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json={**body, "language": "ko", "length_unit": "both", "weight_unit": "kg"})).json()
    assert grid_rows(pv)["크기 (W×H×D)"][0]["text"] == "1,237.9×708.8×28.5 mm (48.7 × 27.9 × 1.1 in)"
    # 47: Letter 탭 이름
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json={**body, "paper": "letter", "tab": "pdf"})).json()
    assert pv["tab_labels"]["pdf"] == "PDF · Letter"


async def test_preferences_default(ctx, client):
    fmt = {"formats": ["xlsx", "pdf"], "language": "en", "length_unit": "inch", "weight_unit": "lb", "paper": "letter", "number_format": "1,234.5"}
    # 46: 내 기본값 → 새 작업 SP2 언어 English
    r = await client.put("/v1/preferences", json=fmt)
    assert r.status_code == 200 and r.json()["is_custom"] is True
    sid = await _sheet(client)
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["format"]["language"] == "en" and s["format"]["paper"] == "letter"
    assert (await client.get("/v1/preferences")).json()["format"]["length_unit"] == "inch"


async def test_letter_pdf_export(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await _sheet(client)
    await client.put(f"/v1/sheets/{sid}/format", json={"formats": ["pdf"], "language": "ko", "length_unit": "mm", "weight_unit": "kg",
                                                       "paper": "letter", "number_format": "1,234.5"})
    await client.post(f"/v1/sheets/{sid}/generate", json={"auto_answer": True})
    await ctx.run_jobs()
    r = await client.post(f"/v1/sheets/{sid}/exports", json={"format": "pdf"})
    eid = r.json()["export_id"]
    await ctx.run_jobs()
    from winmate_spec import repo
    rec = await repo.aget("exports", eid)
    # 47: export 요청의 쪽 크기 Letter
    from winmate_spec.rules.package import export_document
    s = await repo.aget("sheets", sid)
    doc, _ = export_document(s, "pdf", overrides=None, options=None)
    assert doc["page_size"] == "Letter"
    assert rec["status"] in ("done", "failed")
    if rec["status"] == "failed":
        assert "PDF" in (rec.get("error") or "")


async def test_customer_template(ctx, client):
    sid = await _sheet(client)
    f = await upload("고객사_스펙양식.xlsx", template_xlsx(), XLSX)
    r = await client.post(f"/v1/sheets/{sid}/templates", json={"file_id": f["id"]})
    assert r.status_code == 202, r.text
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["template"]["status"] == "done" and s["template"]["name"] == "고객사_스펙양식.xlsx"
    body = {"formats": ["xlsx"], "language": "ko", "length_unit": "mm", "weight_unit": "kg", "paper": "a4_landscape",
            "number_format": "1,234.5", "tab": "xlsx"}
    pv = (await client.post(f"/v1/sheets/{sid}/format:preview", json=body)).json()
    labels = [r["cells"][0]["text"] for r in pv["grid"]["rows"][2:]]
    # 48: 양식 순서 · 이름, Remarks [확정 필요], 시트에만 있는 행은 아래(추가 항목)
    assert labels[:4] == ["Screen", "Brightness (cd/m2)", "Power", "Remarks"]
    assert set(labels[4:]) == {"운영 시간", "내장 플레이어 · OS", "MagicINFO 호환", "보증"}
    assert all(c["text"] == "[확정 필요]" for c in pv["grid"]["rows"][5]["cells"][1:])
    calls = ctx.ai.calls_of("sp.template_map")
    assert calls and calls[0]["confidential"] is True
    ctx.use_cat_fix(version="2026-09")
    await client.post(f"/v1/sheets/{sid}/generate", json={})
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    remarks = [c for c in s["checks"]["items"] if c["title"] == "Remarks"]
    assert len(remarks) == 1 and remarks[0]["body"] == "고객사 양식에 있는 항목이에요. 값을 넣어 주세요."
    rows = [r["label"] for r in s["table"]["rows"]]
    assert rows[:4] == ["Screen", "Brightness (cd/m2)", "Power", "Remarks"]
    # 양식 해제 → 원래 이름 · 순서
    r = await client.delete(f"/v1/sheets/{sid}/templates/{s['template']['id']}")
    assert r.status_code == 204
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["template"] is None and s["table"]["rows"][0]["label"] == "화면 크기 · 해상도"


async def test_set_value_is_rejected(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await _sheet(client)
    await client.post(f"/v1/sheets/{sid}/generate", json={"auto_answer": True})
    await ctx.run_jobs()
    v0 = (await client.get(f"/v1/sheets/{sid}")).json()["version"]
    ctx.ai.on("sp.interpret_request", {"json": {"ops": [{"op": "set_value", "args": {"row": "밝기", "name": "QM55C", "value": "900 nit"}}]}},
              when="900")
    r = await client.post(f"/v1/sheets/{sid}/messages", json={"text": "QM55C 밝기를 900 nit 로 바꿔줘", "context": "result"})
    await ctx.run_jobs()
    from winmate_common.jobs import jobs
    job = await jobs().get(r.json()["job_id"])
    # 97: 셀 값을 정하는 조작은 거절 → needs_clarification, 값 · 버전 그대로
    assert job.result["applied_ops"] == [] and "셀" in job.result["needs_clarification"]
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["version"] == v0
    assert next(r for r in s["table"]["rows"] if r["label"] == "밝기 · 명암비")["cells"][0]["text"].startswith("500 nit")


async def test_ai_unavailable_is_reported(ctx, client):
    ctx.ai.on("sp.parse_conditions", {"error": {"status": 504, "code": "TIMEOUT", "message": "늦음"}})
    r = await client.post("/v1/sheets", json={"start": "find"})
    sid = r.json()["id"]
    await client.post(f"/v1/sheets/{sid}/finder:parse", json={"text": "55인치 벽걸이"})
    await ctx.run_jobs()
    st = (await client.get(f"/v1/sheets/{sid}")).json()["finder"]
    assert st["status"] == "failed" and st["error"] == "AI 응답이 늦어 멈췄어요. 잠시 뒤 다시 시도해 주세요."
