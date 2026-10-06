"""§9.7 생성 · 값 확인(SP3G) · §9.8 결과(SP3) — CAT_FIX 2026-09, QM55C · QB55C, 기본 7항목."""
from __future__ import annotations

from typing import Any

from sp_helpers import PDF, QB55C, QM55C, upload
from sp_samples import datasheet_pdf
from winmate_common.jobs import jobs


async def make_sheet(client, models=(QM55C, QB55C), **extra: Any) -> str:
    r = await client.post("/v1/sheets", json={"start": "model", "products": list(models), **extra})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    r = await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    assert r.status_code == 200, r.text
    return sid


async def generate(ctx, client, sid: str, **body: Any) -> str:
    r = await client.post(f"/v1/sheets/{sid}/generate", json=body)
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    await ctx.run_jobs()
    return job_id


async def step_notes(job_id: str) -> list[tuple[str, str, str | None]]:
    evs = await jobs().events(job_id)
    return [(e["data"].get("step"), e["data"].get("status"), e["data"].get("note")) for _, e in evs if e["type"] == "step"
            and e["data"].get("step") in ("resolve_models", "fetch_specs", "verify", "mark_wins", "compose")]


def cell(s: dict[str, Any], label: str, model: str) -> dict[str, Any]:
    row = next(r for r in s["table"]["rows"] if r["label"] == label)
    pid = next(p["id"] for p in s["products"] if p["display_name"] == model)
    return next(c for c in row["cells"] if c["product_id"] == pid)


async def test_generate_checks_and_answers(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await make_sheet(client)
    job_id = await generate(ctx, client, sid)
    notes = [n for st, status, n in await step_notes(job_id) if status == "done"]
    # 50: 단계 메모
    assert notes[:3] == ["사내 카탈로그 매칭 2 / 2", "14칸 중 12칸 채움", "2곳 확인 필요"]
    run_notes = [n for st, status, n in await step_notes(job_id) if st == "verify" and status == "run"]
    assert "출처 대조 중 · 2곳 확인 필요" in run_notes
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    # 51: 값 확인 카드
    checks = s["checks"]["items"]
    assert s["checks"]["open"] == 2
    c1, c2 = checks
    assert (c1["n"], c1["title"], c1["kind"]) == (1, "소비전력 (일반 · 최대) · QB55C", "missing")
    assert c1["body"] == "사내 카탈로그에 값이 없어요. 데이터시트가 있으면 읽어서 채울게요."
    assert (c1["placeholder"], c1["input_label"]) == ("값 입력 · W", "소비전력 값 입력")
    assert [a["label"] for a in c1["alt_measures"]] == ["On Mode", "Sleep Mode"]
    assert (c2["n"], c2["title"], c2["kind"]) == (2, "보증 · QM55C", "conflict")
    assert c2["body"] == "카탈로그와 국내 보증 정책 문서의 값이 서로 달라요."
    assert [(o["label"], o["value_text"], o["preselected"]) for o in c2["options"]] == [("카탈로그", "3년", True), ("보증 정책 문서", "2년", False)]
    # 53: 답 없이 끝 → 두 칸 [확정 필요], 상태 check
    assert cell(s, "소비전력 (일반 · 최대)", "QB55C")["text"] == "[확정 필요]"
    assert cell(s, "소비전력 (일반 · 최대)", "QB55C")["check_n"] == 1
    assert cell(s, "보증", "QM55C")["text"] == "[확정 필요]" and cell(s, "보증", "QM55C")["check_n"] == 2
    assert (s["ui_status"], s["status_text"]) == ("check", "값 확인 필요 2")
    assert s["resume_route"] == f"/spec/{sid}/generating?job={job_id}"
    # 55: 단위 틀림
    r = await client.post(f"/v1/sheets/{sid}/checks/{c1['id']}:answer", json={"value_text": "100 kWh"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "INVALID_VALUE" and r.json()["error"]["details"]["expected_unit"] == "W"
    assert r.json()["error"]["message"] == "W 단위로 넣어 주세요."
    r = await client.post(f"/v1/sheets/{sid}/checks/{c1['id']}:answer", json={"value_text": "100 / 150"})
    assert r.status_code == 200 and r.json()["answer"]["value_text"] == "100 / 150"
    # 54: 답 반영하고 완성
    v0 = s["version"]
    r = await client.post(f"/v1/sheets/{sid}/checks:apply", json={"answers": [{"check_id": c1["id"], "value_text": "100 / 150"}]})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["next_route"] == f"/spec/{sid}" and res["pending_until_job_done"] is False
    s = res["sheet"]
    assert s["version"] == v0 + 1
    pw = cell(s, "소비전력 (일반 · 최대)", "QB55C")
    assert (pw["text"], pw["state"], pw["sources"][0]["label"]) == ("100 W · 150 W", "edited", "직접 입력")
    assert cell(s, "보증", "QM55C")["text"] == "3년"
    assert (s["ui_status"], s["status_text"]) == ("done", "완료")
    # 62: 우위 3 · 출처 줄
    wins = {r["label"]: [c["win"] for c in r["cells"]] for r in s["table"]["rows"]}
    assert wins["밝기 · 명암비"] == [True, False] and wins["운영 시간"] == [True, False] and wins["소비전력 (일반 · 최대)"] == [False, True]
    assert s["table"]["win_rows"] == 3
    assert s["table"]["source_line"] == "출처: 사내 제품 카탈로그 2026-09 · 직접 입력 1칸"
    # 64: 제목 · 에이전트 · 명암비 숫자 형식
    assert s["table"]["title"] == 'Smart Signage 55" 비교 — QM55C vs QB55C'
    assert s["agent"]["sp3"] == ("비교표가 완성되었습니다. 파란 셀은 우위 항목입니다. 셀을 클릭하면 값을 직접 고칠 수 있고, "
                                 "출처는 사내 카탈로그 2026-09 기준입니다.")
    assert "4,000:1" in cell(s, "밝기 · 명암비", "QM55C")["text"]
    # 65: 셀 고침 → edited, 우위 그대로
    row = next(r for r in s["table"]["rows"] if r["label"] == "밝기 · 명암비")
    qm = next(p["id"] for p in s["products"] if p["display_name"] == "QM55C")
    r = await client.patch(f"/v1/sheets/{sid}/cells/{row['id']}/{qm}", json={"value_text": "450 nit"})
    assert r.status_code == 200, r.text
    assert r.json()["cell"]["state"] == "edited" and r.json()["cell"]["win"] is True and r.json()["cell"]["text"].startswith("450 nit")
    r = await client.patch(f"/v1/sheets/{sid}/cells/{row['id']}/{qm}", json={"value_text": "450 kg"})
    assert r.status_code == 422 and r.json()["error"]["details"]["expected_unit"] == "nit"
    # 68: 저장
    v1 = (await client.get(f"/v1/sheets/{sid}")).json()["version"]
    r = await client.post(f"/v1/sheets/{sid}:save")
    assert r.json()["version"] == v1 + 1 and r.json()["saved_at"]
    vs = (await client.get(f"/v1/sheets/{sid}/versions")).json()["items"]
    assert vs[0]["reason"] == "save"


async def test_defer_all(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await make_sheet(client)
    await generate(ctx, client, sid)
    r = await client.post(f"/v1/sheets/{sid}/checks:defer-all")
    res = r.json()
    s = res["sheet"]
    # 56: 둘 다 deferred, [확정 필요], done → SP3
    assert [c["status"] for c in s["checks"]["items"]] == ["deferred", "deferred"]
    assert cell(s, "소비전력 (일반 · 최대)", "QB55C")["text"] == "[확정 필요]"
    assert s["ui_status"] == "done" and res["next_route"] == f"/spec/{sid}"
    # 63: 소비전력 우위 없음 → 우위 2
    assert s["table"]["win_rows"] == 2
    r = await client.post(f"/v1/sheets/{sid}/checks:apply", json={"answers": []})
    assert r.json()["next_route"] == f"/spec/{sid}"


async def test_auto_answer(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await make_sheet(client)
    await generate(ctx, client, sid, auto_answer=True)
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    # 61: 값 확인 없이 바로 deferred · [확정 필요] · done
    assert s["checks"]["open"] == 0 and all(c["status"] == "deferred" for c in s["checks"]["items"])
    assert s["ui_status"] == "done"


async def test_datasheet_fills_missing(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await make_sheet(client)
    await generate(ctx, client, sid)
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    qb = next(p["id"] for p in s["products"] if p["display_name"] == "QB55C")
    f = await upload("ds_QB55C.pdf", datasheet_pdf(), PDF)
    r = await client.post(f"/v1/sheets/{sid}/datasheets", json={"file_id": f["id"], "product_id": qb})
    assert r.status_code == 202, r.text
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    # 57: 1번 해결, 셀 출처 데이터시트
    c1 = s["checks"]["items"][0]
    assert c1["status"] == "answered"
    pw = cell(s, "소비전력 (일반 · 최대)", "QB55C")
    assert pw["text"] == "100 W · 150 W" and pw["sources"][0]["kind"] == "datasheet"
    assert s["datasheets"][0]["status"] == "done"
    # 생성 뒤 다른 값(밝기 350 vs 400) → 값 불일치 경고(카탈로그 칩 눌림)
    ws = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    w = next(w for w in ws["items"] if w["kind"] == "value_mismatch_source")
    assert w["title"] == "밝기 · QB55C"
    assert [o["label"] for o in w["options"]] == ["카탈로그 · 350 nit", "데이터시트 · 400 nit"]
    assert w["decision"]["option_key"] == "catalog"


async def test_datasheet_value_not_in_text_is_ignored(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    ctx.ai.on("sp.datasheet_extract", {"json": {"model_codes": [QB55C], "rows": [
        {"group": "전원", "name_raw": "소비전력 (Typical)", "value_raw": "95 W", "page": 1}]}})
    sid = await make_sheet(client)
    await generate(ctx, client, sid)
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    qb = next(p["id"] for p in s["products"] if p["display_name"] == "QB55C")
    f = await upload("ds_QB55C.pdf", datasheet_pdf(), PDF)
    await client.post(f"/v1/sheets/{sid}/datasheets", json={"file_id": f["id"], "product_id": qb})
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["checks"]["items"][0]["status"] == "open"
    assert cell(s, "소비전력 (일반 · 최대)", "QB55C")["text"] == "[확정 필요]"


async def test_cancel_returns_to_items(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await make_sheet(client)
    r = await client.post(f"/v1/sheets/{sid}/generate", json={})
    job_id = r.json()["job_id"]
    await jobs().cancel(job_id)
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    # 58: step 2 · draft `작성 중 2/3`
    assert (s["step"], s["ui_status"], s["status_text"]) == (2, "draft", "작성 중 2/3")
    assert s["active_job"] is None and s["table"] is None


async def test_memo_during_generation_adds_derived_row(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await make_sheet(client)
    r = await client.post(f"/v1/sheets/{sid}/generate", json={})
    job_id = r.json()["job_id"]
    r = await client.post(f"/v1/sheets/{sid}/messages", json={"text": "소비전력은 연간 전기료로도 보여줘", "context": "generating"})
    # 59: 조종 메모(200 queued)
    assert r.status_code == 200 and r.json() == {"queued": True, "job_id": job_id, "memo": True}
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    row = next(r for r in s["table"]["rows"] if r["label"] == "연간 전기료 (추정)")
    assert all(c["text"] == "[확정 필요]" for c in row["cells"])
    chk = next(c for c in s["checks"]["items"] if c["title"] == "연간 전기료 (추정) · 계산 기준")
    assert chk["status"] == "open" and chk["unit"] == "원/kWh"
    calls = ctx.ai.calls_of("sp.interpret_request_memo")
    assert calls and calls[0]["confidential"] is False
    # 단가를 넣으면 계산(일반 소비전력 × 하루 시간 × 365 ÷ 1000 × 단가)
    r = await client.post(f"/v1/sheets/{sid}/checks:apply", json={"answers": [{"check_id": chk["id"], "value_text": "150원"}]})
    s = r.json()["sheet"]
    row = next(r for r in s["table"]["rows"] if r["label"] == "연간 전기료 (추정)")
    qm = cell(s, "연간 전기료 (추정)", "QM55C")
    assert qm["state"] == "derived"
    assert "157,680" in qm["text"]                          # 120 W × 24 h × 365 ÷ 1000 × 150원 = 157,680원
    assert any(f["text"].startswith("계산 기준: 하루 24시간 · 365일 · 1kWh당 150원") for f in s["table"]["footnotes"])


async def test_revise_adds_row_and_export(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await make_sheet(client)
    await generate(ctx, client, sid)
    await client.post(f"/v1/sheets/{sid}/checks:defer-all")
    v0 = (await client.get(f"/v1/sheets/{sid}")).json()["version"]
    # 67: 수정 요청 → 202 spec_revise → 행 추가 · version +1
    r = await client.post(f"/v1/sheets/{sid}/messages", json={"text": "소비전력을 연간 전기료로 환산한 행 추가", "context": "result"})
    assert r.status_code == 202 and r.json()["memo"] is False
    rev_job = r.json()["job_id"]
    await ctx.run_jobs()
    job = await jobs().get(rev_job)
    assert job.status == "succeeded", job.error
    assert job.result["applied_ops"] == ["add_derived_row"]
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["version"] == v0 + 1
    assert s["table"]["rows"][-1]["label"] == "연간 전기료 (추정)"
    # 66: XLSX 빠른 내보내기 → 202 → file_id
    r = await client.post(f"/v1/sheets/{sid}/exports", json={"format": "xlsx"})
    assert r.status_code == 202, r.text
    eid = r.json()["export_id"]
    await ctx.run_jobs()
    rec = (await client.get(f"/v1/sheets/{sid}/exports/{eid}")).json()
    assert rec["status"] == "done", rec
    assert rec["file_id"] and rec["filename"].endswith(".xlsx")


async def test_rerender_does_not_refetch_kb(ctx, client, monkeypatch):
    ctx.use_cat_fix(version="2026-09")
    sid = await make_sheet(client)
    await generate(ctx, client, sid)
    from winmate_spec.catalog import catalog
    cat = catalog()
    calls = {"n": 0}
    orig = cat.specs

    async def counting(codes):
        calls["n"] += 1
        return await orig(codes)

    monkeypatch.setattr(cat, "specs", counting)
    r = await client.put(f"/v1/sheets/{sid}/format", json={"formats": ["xlsx"], "language": "en", "length_unit": "inch", "weight_unit": "lb"})
    assert r.status_code == 200
    # 49: rerender → kb 스펙 재조회 0회
    await generate(ctx, client, sid, mode="rerender")
    assert calls["n"] == 0
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["format"]["language"] == "en" and s["table"]["title_en"] == 'Samsung Smart Signage 55" Comparison'


async def test_same_input_same_table(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    a = await make_sheet(client)
    await generate(ctx, client, a, auto_answer=True)
    b = await make_sheet(client)
    await generate(ctx, client, b, auto_answer=True)
    ta = (await client.get(f"/v1/sheets/{a}")).json()["table"]
    tb = (await client.get(f"/v1/sheets/{b}")).json()["table"]

    def norm(t):
        return [(r["label"], [(c["text"], c["win"], c["state"]) for c in r["cells"]]) for r in t["rows"]]

    # 100: 같은 입력이면 같은 표
    assert norm(ta) == norm(tb)


async def test_generate_preconditions(ctx, client):
    r = await client.post("/v1/sheets", json={"start": "model"})
    sid = r.json()["id"]
    r = await client.post(f"/v1/sheets/{sid}/generate", json={})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_PRODUCTS"
    await client.post(f"/v1/sheets/{sid}/products", json={"refs": [QM55C]})
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    await client.put(f"/v1/sheets/{sid}/items", json={"items": [{"key": i["key"], "checked": False} for i in s["items"]]})
    r = await client.post(f"/v1/sheets/{sid}/generate", json={})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_ITEMS"
