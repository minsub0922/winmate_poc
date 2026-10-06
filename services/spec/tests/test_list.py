"""§9.1 목록 · 진입(SP0) — SP0_ROWS 6행 · 탭 · 거르기 · 검색 · 배너 · 보관 · workspace · 넘겨받기 · 복제."""
from __future__ import annotations

from typing import Any

from sp_helpers import QB55C, QH55C, QM55C, QM65C
from winmate_common.client import ServiceClient


async def _mut(sid: str, fn) -> None:
    from winmate_spec import repo
    from winmate_spec import sheet as S

    def wrap(x: dict[str, Any]) -> None:
        fn(x)
        S.refresh_status(x, x["id"])

    await repo.amutate("sheets", sid, wrap)


async def _create(client, **body: Any) -> str:
    r = await client.post("/v1/sheets", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def sp0_rows(ctx, client) -> list[str]:
    """보드 SP0 6행(오래된 것부터 만들고, 1행이 가장 최근 — `오늘 10:24`)."""
    ids: list[str] = []
    ctx.use_cat_fix(version="2026-09")
    tp = {"id": "prp_A", "title": "A 커피 프랜차이즈 메뉴보드 제안", "type": "standard", "section_no": "08"}
    # 6 · 조건 검색 1/3 — C 물류센터 관제실 후보 비교(제품 4)
    ctx.set_now("2026-10-05T06:00:00Z")
    sid6 = await _create(client, start="find", products=[QH55C, QM55C, QM65C, QB55C], customer_name="C 물류센터")
    await _mut(sid6, lambda x: (x.update({"title": "C 물류센터 관제실 후보 비교", "title_confirmed": True})))
    # 5 · 작성 중 2/3 — WA75D(제품 1), 형식 정하지 않음
    ctx.set_now("2026-10-05T07:00:00Z")
    sid5 = await _create(client, start="model", products=["LH75WADWLGCXKR"])
    await client.patch(f"/v1/sheets/{sid5}", json={"step": 2})
    # 4 · 카탈로그 변경 1 — QB55C 단일(생성 뒤 catalog_changed 하나)
    ctx.set_now("2026-10-06T00:10:00Z")
    sid4 = await _create(client, start="model", products=[QB55C], target_proposal={**tp, "id": "prp_D", "title": "D 물류 제안"})
    await client.patch(f"/v1/sheets/{sid4}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid4}/generate", json={"auto_answer": True})
    await ctx.run_jobs()

    def add_changed(x: dict[str, Any]) -> None:
        from winmate_spec.rules import warnings as W
        r = next(r for r in x["rows"] if r["row_key"] == "brightness_contrast")
        p = x["products"][0]
        x["warnings"].append(W.catalog_changed(r, p, old={"value": {"nit": 350.0}, "value_text": "350 nit"},
                                               new={"value": {"nit": 400.0}, "value_text": "400 nit"}, new_version="2026-10"))
    await _mut(sid4, add_changed)
    # 3 · 확인 필요 3 — 규격서 대응표(QM55C)
    ctx.set_now("2026-10-06T00:20:00Z")
    from sp_helpers import PDF, upload
    from sp_samples import requirement_pdf
    sid3 = await _create(client, start="requirements", target_proposal={**tp, "id": "prp_B", "title": "B 병원 로비 제안"})
    f = await upload("B병원_로비디스플레이_요구규격서.pdf", requirement_pdf(), PDF)
    await client.post(f"/v1/sheets/{sid3}/requirement-docs", json={"file_id": f["id"], "note": "이 규격서 기준으로 QM55C 대응표를 만들어 주세요"})
    ctx.use_kb()                 # 실제 kb(소비전력 Typical · 보증 없음) → 확인 필요 3
    await ctx.run_jobs()
    ctx.use_cat_fix(version="2026-09")
    # 2 · 값 확인 필요 2 — QM65C 단일(소비전력 · 보증 값 없음)
    ctx.set_now("2026-10-06T00:30:00Z")
    sid2 = await _create(client, start="model", products=[QM65C], target_proposal={**tp, "id": "prp_C", "title": "B 병원 안내 시스템 제안"})
    await client.patch(f"/v1/sheets/{sid2}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid2}/generate", json={})
    await ctx.run_jobs()
    # 1 · 완료 — QMC vs QBC 55" 비교, 제안서 연결, 오늘 10:24
    ctx.set_now("2026-10-06T01:20:00Z")
    sid1 = await _create(client, start="model", products=[QM55C, QB55C], target_proposal=tp)
    await client.patch(f"/v1/sheets/{sid1}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid1}/generate", json={"auto_answer": True})
    await ctx.run_jobs()
    ctx.set_now("2026-10-06T01:24:00Z")
    await client.post(f"/v1/sheets/{sid1}:save")
    ctx.set_now("2026-10-06T01:30:00Z")
    ids = [sid1, sid2, sid3, sid4, sid5, sid6]
    return ids


async def test_sp0_rows(ctx, client):
    ids = await sp0_rows(ctx, client)
    lst = (await client.get("/v1/sheets")).json()
    # 1: 탭 숫자
    assert lst["counts"] == {"all": 6, "draft": 2, "check": 3, "done": 1}
    items = {i["id"]: i for i in lst["items"]}
    assert [i["id"] for i in lst["items"]] == ids
    r1, r2, r3, r4, r5, r6 = (items[i] for i in ids)
    # 2: 1행 · 5행
    assert (r1["title"], r1["sub_line"], r1["model_chips"], r1["output_label"]) == ('QMC vs QBC 55" 비교', "비교표 · 7개 항목", ["QM55C", "QB55C"],
                                                                                     "XLSX · 한국어")
    assert (r1["ui_status"], r1["status_text"], r1["proposal_label"], r1["when_label"]) == ("done", "완료", "A 커피 프랜차이즈 메뉴보드 제안",
                                                                                            "오늘 10:24")
    assert (r5["output_label"], r5["proposal_label"]) == ("정하지 않음", "연결 안 됨")
    # 3: 6행 — 제품 4개 · 칩 2 + 2 · find
    assert (r6["title"], r6["model_chips"], r6["more_models"], r6["type_icon"]) == ("C 물류센터 관제실 후보 비교", ["QH55C", "QM55C"], 2, "find")
    # 4: 이어하기 경로
    assert r1["resume_route"] == f"/spec/{ids[0]}"
    assert r2["resume_route"].startswith(f"/spec/{ids[1]}/generating?job=job_") and r2["status_text"] == "값 확인 필요 2"
    assert (r3["resume_route"], r3["status_text"]) == (f"/spec/{ids[2]}/requirements", "확인 필요 3")
    assert (r4["resume_route"], r4["status_text"]) == (f"/spec/{ids[3]}/warnings", "카탈로그 변경 1")
    assert (r5["resume_route"], r5["status_text"]) == (f"/spec/{ids[4]}/items", "작성 중 2/3")
    assert (r6["resume_route"], r6["status_text"]) == (f"/spec/{ids[5]}/find", "작성 중 1/3")
    # 5: 탭 · 연결 · 검색
    assert len((await client.get("/v1/sheets", params={"tab": "check"})).json()["items"]) == 3
    assert len((await client.get("/v1/sheets", params={"linked": True})).json()["items"]) == 4
    found = [i["id"] for i in (await client.get("/v1/sheets", params={"q": "QM55C"})).json()["items"]]
    assert found == [ids[0], ids[2], ids[5]]
    # 9: workspace 색인 = resume_route
    item = await ServiceClient("workspace").get(f"/v1/items/{ids[1]}")
    assert (item["feature"], item["status"], item["summary"], item["route"]) == ("SP", "check", "값 확인 필요 2", r2["resume_route"])


async def test_banner_and_archived(ctx, client):
    ctx.use_cat_fix(version="2026-10")
    from winmate_spec import repo
    sids = []
    for _ in range(2):
        sid = await _create(client, start="model", products=[QB55C])
        await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
        await client.post(f"/v1/sheets/{sid}/generate", json={"auto_answer": True})
        sids.append(sid)
    await ctx.run_jobs()
    lst = (await client.get("/v1/sheets")).json()
    assert lst["banner"] is None
    # 6: 열린 catalog_changed 시트 2 · 감지일 2026-10-01
    for sid in sids:
        def add_changed(x: dict[str, Any]) -> None:
            from winmate_spec.rules import warnings as W
            r = next(r for r in x["rows"] if r["row_key"] == "brightness_contrast")
            x["warnings"].append(W.catalog_changed(r, x["products"][0], old={"value": {"nit": 350.0}, "value_text": "350 nit"},
                                                   new={"value": {"nit": 400.0}, "value_text": "400 nit"}, new_version="2026-10"))
        await _mut(sid, add_changed)
    await repo.aput("catalog_state", "fixture", {"adapter": "fixture", "version": "2026-10", "detected_at": "2026-10-01T00:00:00Z",
                                                 "previous_version": "2026-09"})
    lst = (await client.get("/v1/sheets")).json()
    assert lst["banner"]["text"] == "사내 카탈로그가 10월 1일 갱신되었습니다. 저장된 시트 2개에서 값이 달라져 다시 확인이 필요해요."
    assert lst["banner"]["sheets"] == 2 and lst["banner"]["date"] == "2026-10-01"
    # 8: 보관
    for sid in sids:
        assert (await client.post(f"/v1/sheets/{sid}:archive")).status_code == 204
    lst = (await client.get("/v1/sheets")).json()
    assert lst["archived_count"] == 2 and lst["counts"]["all"] == 0 and lst["banner"] is None
    arch = (await client.get("/v1/sheets", params={"archived": True})).json()
    assert len(arch["items"]) == 2
    await client.post(f"/v1/sheets/{sids[0]}:unarchive")
    assert (await client.get("/v1/sheets")).json()["counts"]["all"] == 1


async def test_link_entry_and_family(ctx, client):
    # 10: /spec/new?models=LH55QMCEBGCXKR,mdl_LH55QBCEBGCXKR&from=vp:vp_01J…
    r = await client.post("/v1/sheets", json={"start": "link", "products": [QM55C, f"mdl_{QB55C}"], "origin": {"from": "vp", "ref": "vp_01JTEST"}})
    s = r.json()
    assert [p["bubble_label"] for p in s["products"]] == ["Smart Signage QM55C", "Smart Signage QB55C"]
    assert s["origin"] == {"from": "vp", "ref": "vp_01JTEST"}
    assert s["agent"]["from_note"] == "Value Proposition에서 넘겨받은 제품 2개를 넣어 두었어요."
    r = await client.post("/v1/sheets", json={"start": "link", "products": ["fam_G000182628"]})
    assert [p["model_code"] for p in r.json()["products"]] == [QM55C]


async def test_clone(ctx, client):
    ctx.use_cat_fix(version="2026-09")
    sid = await _create(client, start="model", products=[QM55C, QB55C], customer_name="A 커피 프랜차이즈")
    await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid}/generate", json={"auto_answer": True})
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    ses = (await client.post(f"/v1/sheets/{sid}/edit-sessions")).json()["id"]
    row = s["table"]["rows"][1]["id"]
    await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}/ops", json={"ops": [
        {"op": "highlight_row", "row_id": row}, {"op": "set_memo", "row_id": row, "text": "내부 메모", "mode": "internal"}]})
    await client.post(f"/v1/sheets/{sid}/edit-sessions/{ses}:commit", json={})
    # 11: 복제 — 제품 · 항목 · 형식 · 행 편집, 고객사 · 연결 · 경고 · 내부 메모 비움, SP1
    r = await client.post(f"/v1/sheets/{sid}:clone", json={})
    assert r.status_code == 201
    c = r.json()
    assert c["start"] == "clone" and c["title_confirmed"] is False and c["customer_name"] is None and c["step"] == 1
    assert [p["display_name"] for p in c["products"]] == ["QM55C", "QB55C"]
    assert c["warnings"]["open"] == 0 and c["links"] == [] and c["table"] is None
    assert c["resume_route"] == f"/spec/{c['id']}/products"
