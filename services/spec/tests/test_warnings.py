"""§9.9 경고(SP3W) — CAT_FIX 2026-10 · QM55R(단종, 고객 기존 장비) · 데이터시트 값 불일치 · 제안서 값 불일치 · RFP 요구 미충족."""
from __future__ import annotations

from typing import Any

from sp_helpers import PDF, QM55C, upload
from sp_samples import datasheet_pdf
from winmate_common.jobs import jobs

RFP_ITEM = {"id": "ri_01RFP", "code": "RQ-01", "text": "관제실 디스플레이는 24시간 운영되어야 함", "short": "24시간 운영",
            "entities": [{"type": "capability", "id": "cap_continuous_operation", "name": "24시간 운영", "surface": "24시간"}]}
QM55R_MSG = "고객 매장 기존 장비 QM55R도 같이 비교해줘"


async def sheet_64(ctx, client) -> str:
    """64번 시트(2026-09 생성 · 1번 100 / 150 · 2번 카탈로그 3년) + QB55C 데이터시트 + 보낸 제안서 연결(보증 2년)."""
    ctx.use_cat_fix(version="2026-09")
    r = await client.post("/v1/sheets", json={"start": "model", "products": [QM55C, "QB55C"], "project_id": "prj_A",
                                              "customer_name": "A 커피 프랜차이즈"})
    sid = r.json()["id"]
    await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid}/generate", json={})
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    c1 = s["checks"]["items"][0]
    await client.post(f"/v1/sheets/{sid}/checks:apply", json={"answers": [{"check_id": c1["id"], "value_text": "100 / 150"}]})
    qb = next(p["id"] for p in s["products"] if p["display_name"] == "QB55C")
    f = await upload("ds_QB55C.pdf", datasheet_pdf(), PDF)
    await client.post(f"/v1/sheets/{sid}/datasheets", json={"file_id": f["id"], "product_id": qb})
    await ctx.run_jobs()
    # 제안서로 넘김 → 보낸 스냅숏의 QM55C 보증을 2년(이전 값)으로 → proposal :ack
    r = await client.post(f"/v1/sheets/{sid}/handoffs", json={"proposal_id": "prp_A", "proposal_type": "standard",
                                                               "proposal_title": "A 커피 프랜차이즈 메뉴보드 제안", "templates": ["SC-A"]})
    assert r.status_code == 201, r.text
    sho = r.json()["id"]
    from winmate_spec import repo
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    w_row = next(r for r in s["table"]["rows"] if r["label"] == "보증")
    qm = next(p["id"] for p in s["products"] if p["display_name"] == "QM55C")

    def old_value(h: dict[str, Any]) -> None:
        h["sent_snapshot"][f"{w_row['id']}|{qm}"] = "2년"

    await repo.amutate("handoffs", sho, old_value, what="넘김")
    r = await client.post(f"/v1/handoffs/{sho}:ack", json={"result": "applied", "proposal_id": "prp_A", "proposal_title": "A 커피 프랜차이즈 메뉴보드 제안",
                                                         "section_no": "08", "section_name": "제품 스펙", "proposal_sheet_ids": ["psh_1"]})
    assert r.status_code == 200, r.text
    return sid


async def add_qm55r(ctx, client, sid: str) -> dict[str, Any]:
    ctx.ai.on("sp.interpret_request", {"json": {"ops": [{"op": "add_product", "args": {"query": "QM55R", "role": "existing"}}]}}, when="QM55R")
    r = await client.post(f"/v1/sheets/{sid}/messages", json={"text": QM55R_MSG, "context": "result"})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    await ctx.run_jobs()
    job = await jobs().get(job_id)
    assert job.status == "succeeded", job.error
    return job.result


async def test_warnings_board_flow(ctx, client):
    sid = await sheet_64(ctx, client)
    ctx.use_cat_fix(version="2026-10")
    ctx.rq.project_id = "prj_A"
    ctx.rq.items = [RFP_ITEM]
    res = await add_qm55r(ctx, client, sid)
    # 69: navigate SP3W, QM55R 열(고객 기존 장비 · 단종 · 1), 소비전력 · 보증 [확정 필요] + 1
    assert res["navigate"] == "SP3W"
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    qm55r = next(p for p in s["products"] if p["display_name"] == "QM55R")
    assert qm55r["role"] == "existing" and qm55r["lifecycle"]["status"] == "discontinued" and qm55r["warning_ns"] == [1]
    rows = {r["label"]: r for r in s["table"]["rows"]}
    c_pw = next(c for c in rows["소비전력 (일반 · 최대)"]["cells"] if c["product_id"] == qm55r["id"])
    c_wa = next(c for c in rows["보증"]["cells"] if c["product_id"] == qm55r["id"])
    assert (c_pw["text"], c_pw["warning_ns"]) == ("[확정 필요]", [1])
    assert (c_wa["text"], c_wa["warning_ns"]) == ("[확정 필요]", [1])
    # 70: 에이전트 · 표 제목 · 바닥
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    assert v["agent_text"] == ("최신 카탈로그와 다시 대조했어요. QM55R은 단종 모델이고, 출처나 제안서와 값이 다른 곳이 2곳, "
                               "고객 요구와 맞지 않는 곳이 1곳 있어요. 오른쪽에서 하나씩 정하면 시트에 반영할게요.")
    assert v["table_title"] == 'Smart Signage 55" 비교 — 기존 장비 포함' and v["total"] == 4
    assert v["footer"] == "출처: 사내 제품 카탈로그 2026-10 대조 · 시트 생성 2026-10-06"
    assert v["user_text"] == QM55R_MSG
    # 71: 카드 4개 순서 · 문구 · 필터 · 결정
    w1, w2, w3, w4 = v["items"]
    assert (w1["n"], w1["tag"], w1["title"]) == (1, "단종", "QM55R · 고객 기존 장비")
    assert w1["body"] == "사내 카탈로그에 단종 모델로 표시돼요. 소비전력 · 보증 값이 없어 [확정 필요]로 두었어요."
    assert w1["replacement"] == {"label": "QM55C", "relation_text": '같은 55" QM 라인업', "already_in_sheet": True, "model_code": QM55C}
    assert [o["label"] for o in w1["options"] if o["kind"] == "radio"][:2] == ["'기존 장비'로 표기하고 유지 — 교체 전 ↔ 후 비교", "시트에서 빼기"]
    assert w1["decision"]["option_key"] == "keep_existing"
    assert (w2["tag"], w2["title"], w2["body"]) == ("값 불일치", "밝기 · QB55C", "카탈로그와 제품 데이터시트(PDF)의 값이 달라요.")
    assert [o["label"] for o in w2["options"]] == ["카탈로그 · 350 nit", "데이터시트 · 400 nit"] and w2["decision"]["option_key"] == "catalog"
    assert (w3["tag"], w3["title"], w3["body"]) == ("값 불일치", "보증 · QM55C · 제안서와 다름", "제안서 08 제품 스펙에는 이전 값이 들어가 있어요.")
    assert [o["label"] for o in w3["options"]] == ["제안서에도 반영", "그대로 두기"] and w3["decision"] is None
    assert (w4["tag"], w4["title"], w4["body"]) == ("요구 미충족", "운영 시간 · QB55C", "고객 RFP의 '24시간 운영' 요구와 맞지 않아요.")
    assert [o["label"] for o in w4["options"]] == ["요구사항 대응표 보기", "확인함"] and w4["decision"] is None
    assert v["counts"] == {"all": 4, "discontinued": 1, "mismatch": 2, "unmet": 1} and v["decided"] == 2
    # 72: 칸 번호 — QB55C 밝기 = 2, QM55C 보증 = 3, QB55C 운영 시간 = 4
    qb = next(p["id"] for p in s["products"] if p["display_name"] == "QB55C")
    qm = next(p["id"] for p in s["products"] if p["display_name"] == "QM55C")
    assert next(c for c in rows["밝기 · 명암비"]["cells"] if c["product_id"] == qb)["warning_ns"] == [2]
    assert next(c for c in rows["보증"]["cells"] if c["product_id"] == qm)["warning_ns"] == [3]
    assert next(c for c in rows["운영 시간"]["cells"] if c["product_id"] == qb)["warning_ns"] == [4]
    # 77: 다른 후보 찾기 → SP1C 55" 켬
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"preset": f"warning:{w1['id']}"})).json()
    assert st["conditions"]["sizes"] == ["55"]
    # 73: 기본 선택대로 반영 → QM55R 유지(우위 제외) · 밝기 그대로 · 3 · 4 열린 채 · version +1 · warn `경고 2`
    v0 = s["version"]
    r = await client.post(f"/v1/sheets/{sid}/warnings:apply")
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["version"] == v0 + 1
    assert next(p for p in s["products"] if p["display_name"] == "QM55R")["role"] == "existing"
    rows = {r["label"]: r for r in s["table"]["rows"]}
    assert next(c for c in rows["밝기 · 명암비"]["cells"] if c["product_id"] == qb)["text"].startswith("350 nit")
    assert all(not c["win"] for c in rows["밝기 · 명암비"]["cells"] if c["product_id"] == qm55r["id"])
    assert (s["ui_status"], s["status_text"]) == ("warn", "경고 2")
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    assert [w["kind"] for w in v["items"]] == ["value_mismatch_proposal", "requirement_unmet"]
    # 76: 확인함 → dismissed, 재확인해도 다시 안 생김
    w4 = v["items"][1]
    r = await client.patch(f"/v1/sheets/{sid}/warnings/{w4['id']}", json={"option_key": "ack"})
    assert r.status_code == 200 and r.json()["decision"]["option_key"] == "ack"
    await client.post(f"/v1/sheets/{sid}/warnings:apply")
    r = await client.post(f"/v1/sheets/{sid}/recheck")
    assert r.status_code == 202
    await ctx.run_jobs()
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    assert [w["kind"] for w in v["items"]] == ["value_mismatch_proposal"]
    # 75: 제안서에도 반영 → SP4 교체 넘김 → :ack(applied) 면 해결
    w3 = v["items"][0]
    r = await client.post(f"/v1/sheets/{sid}/handoffs", json={"proposal_id": "prp_A", "proposal_type": "standard", "templates": ["SC-A"],
                                                               "mode": "replace", "replace_proposal_sheet_ids": ["psh_1"]})
    sho = r.json()["id"]
    assert r.json()["open_route"] == f"/proposal/prp_A/sections/spec?handoff={sho}"
    await client.post(f"/v1/handoffs/{sho}:ack", json={"result": "applied", "proposal_id": "prp_A", "section_no": "08",
                                                       "section_name": "제품 스펙", "proposal_sheet_ids": ["psh_2"]})
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    assert v["items"] == []
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["ui_status"] == "done"
    links = (await client.get("/v1/links", params={"proposal_id": "prp_A"})).json()["items"]
    assert links[0]["status"] == "in_sync" and links[0]["diff_cells"] == []
    _ = w3


async def test_remove_discontinued_column(ctx, client):
    sid = await sheet_64(ctx, client)
    ctx.use_cat_fix(version="2026-10")
    await add_qm55r(ctx, client, sid)
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    w1 = v["items"][0]
    assert w1["kind"] == "discontinued"
    r = await client.patch(f"/v1/sheets/{sid}/warnings/{w1['id']}", json={"option_key": "remove"})
    assert r.status_code == 200
    s = (await client.post(f"/v1/sheets/{sid}/warnings:apply")).json()
    # 74: QM55R 열이 없다
    assert [p["display_name"] for p in s["products"]] == ["QM55C", "QB55C"]
    assert all(len(r["cells"]) == 2 for r in s["table"]["rows"])


async def test_not_in_catalog_with_kb_adapter(ctx, client):
    # 78: kb 어댑터(QM55R 없음) · 생애주기 표에도 없음 → not_in_catalog, 열 값 모두 [확정 필요]
    r = await client.post("/v1/sheets", json={"start": "model", "products": [QM55C, "QB55C"]})
    sid = r.json()["id"]
    await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    await client.post(f"/v1/sheets/{sid}/generate", json={"auto_answer": True})
    await ctx.run_jobs()
    res = await add_qm55r(ctx, client, sid)
    assert res["navigate"] == "SP3W"
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    w = v["items"][0]
    assert (w["kind"], w["tag"], w["title"]) == ("not_in_catalog", "카탈로그 없음", "QM55R · 고객 기존 장비")
    assert w["body"] == "사내 카탈로그에서 찾을 수 없는 모델이에요. 단종됐거나 아직 등록되지 않았을 수 있어요."
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    qm55r = next(p for p in s["products"] if p["display_name"] == "QM55R")
    assert qm55r["custom"] is True
    assert all(next(c for c in r["cells"] if c["product_id"] == qm55r["id"])["text"] == "[확정 필요]" for r in s["table"]["rows"])


async def test_rename_column_from_warnings_dock(ctx, client):
    sid = await sheet_64(ctx, client)
    ctx.use_cat_fix(version="2026-10")
    await add_qm55r(ctx, client, sid)
    r = await client.post(f"/v1/sheets/{sid}/messages", json={"text": "QM55R 열 이름을 '기존 장비'로", "context": "warnings"})
    assert r.status_code == 202
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert next(p for p in s["products"] if p["display_name"] == "QM55R")["column_label"] == "기존 장비"


async def test_release_links_when_proposal_deleted(ctx, client):
    """제안서를 지우면(proposal → `DELETE /v1/links?proposal_id=`) 연결 · `제안서와 다름` 경고 · 보낼 제안서를 거둔다(통합)."""
    sid = await sheet_64(ctx, client)
    assert len((await client.get("/v1/links", params={"proposal_id": "prp_A"})).json()["items"]) == 1
    # 다른 시트만 거두면(반입 실행 취소 — sheet_id) 이 시트 연결은 그대로
    r = await client.delete("/v1/links", params={"proposal_id": "prp_A", "sheet_id": "sp_other"})
    assert r.status_code == 200 and r.json()["deleted"] == 0
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    assert "value_mismatch_proposal" in [w["kind"] for w in v["items"]]
    r = await client.delete("/v1/links", params={"proposal_id": "prp_A"})
    assert r.status_code == 200, r.text
    assert r.json() == {"proposal_id": "prp_A", "deleted": 1, "sheet_ids": [sid]}
    assert (await client.get("/v1/links", params={"proposal_id": "prp_A"})).json()["items"] == []
    v = (await client.get(f"/v1/sheets/{sid}/warnings")).json()
    assert "value_mismatch_proposal" not in [w["kind"] for w in v["items"]]
    assert (await client.get(f"/v1/sheets/{sid}")).json().get("target_proposal") is None
    r = await client.delete("/v1/links", params={"proposal_id": "prp_A"})
    assert r.json()["deleted"] == 0
