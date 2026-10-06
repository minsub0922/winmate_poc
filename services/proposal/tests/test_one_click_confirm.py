"""딸깍(§4.17 · AC-110~119) · 확정 필요(PR7Q · AC-143~148)."""
from __future__ import annotations

from typing import Any


async def setup(client: Any, *, links: list[dict[str, Any]] | None = None) -> str:
    r = await client.post("/v1/proposals", json={"start_mode": "blank", "title": "전국 매장 디지털 메뉴보드 전환",
                                                  "customer": {"name": "A 커피 프랜차이즈", "scale_text": "320개 매장"},
                                                  "rq_ref": {"rq_id": "rq_acoffee", "version": 1}, "links": links or []})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_one_click_early_plan(client: Any, ctx: Any) -> None:
    pid = await setup(client)
    await client.patch(f"/v1/proposals/{pid}", json={"stage": "type"})
    r = await client.get(f"/v1/proposals/{pid}/one-click/plan", params={"from": "type"})
    assert r.status_code == 200, r.text
    pl = r.json()
    assert pl["confirmed"] == ["고객 · 프로젝트"]
    assert [x["label"] for x in pl["rows"]] == ["제안서 유형", "시트 구성", "섹션 작성", "디자인 템플릿", "PPTX 생성"]
    assert pl["rows"][0]["note"] == "표준 제안서 (요구사항 기반 추천)"
    assert pl["rows"][3]["note"] == "삼성 B2B 표준 (기본값)"
    assert pl["summary"].startswith("남은 5단계 · 약 ")


async def test_one_click_from_birdseye_runs_to_pptx(client: Any, ctx: Any) -> None:
    pid = await setup(client, links=[{"feature": "mi", "ref_id": "mi_acoffee"}, {"feature": "storyboard", "ref_id": "sb_acoffee"},
                                     {"feature": "birdseye", "ref_id": "be_lobby"}])
    await client.put(f"/v1/proposals/{pid}/type", json={"type": "standard"})
    await client.put(f"/v1/proposals/{pid}/industry", json={"keep_default": True})
    for key in ("mi", "vp"):
        await client.post(f"/v1/proposals/{pid}/sections/{key}:fill", json={})
        await ctx.run_jobs()
        r = await client.post(f"/v1/proposals/{pid}/sections/{key}:confirm")
        assert r.status_code == 200, r.text
    before = {s["id"]: s for s in (await client.get(f"/v1/proposals/{pid}")).json()["sheets"] if s["section_key"] in ("mi", "vp")}
    mi_sheet = next(iter(before))
    mi_before = (await client.get(f"/v1/proposals/{pid}/sheets/{mi_sheet}")).json()["content"]
    r = await client.get(f"/v1/proposals/{pid}/one-click/plan", params={"from": "sections", "section": "birdseye"})
    pl = r.json()
    assert pl["confirmed"] == ["고객 · 프로젝트", "표준 제안서", "시트 구성", "MI", "Value Props"], pl
    assert pl["rows"][0]["label"] == "조감도 (작성 중)"
    assert pl["rows"][0]["note"].startswith("입력한 내용 반영 · ")
    assert [x["label"] for x in pl["rows"]][-2:] == ["디자인 템플릿", "PPTX 생성"]
    assert pl["summary"].startswith("섹션 6 · 시트 ")
    r = await client.post(f"/v1/proposals/{pid}/one-click", json={"options": {"mark_inferred": True, "collect_reviews": True},
                                                                 "from_stage": "sections", "from_section_key": "birdseye"})
    assert r.status_code == 202, r.text
    job = r.json()["job_id"]
    p = (await client.get(f"/v1/proposals/{pid}")).json()
    assert p["progress_label"] == "딸깍 진행 중 · 0%"
    assert p["route"].endswith(f"/one-click/{job}")
    from winmate_common.jobs import jobs
    await jobs().add_memo(job, "Why Samsung은 비용 중심으로")
    await ctx.run_jobs()
    j = await jobs().get(job)
    assert j.status == "succeeded", (j.error, j.result)
    evs = [e for _, e in await jobs().events(job)]
    assert not any(e["type"] == "awaiting_input" for e in evs)                          # AC-117
    v = (await client.get(f"/v1/proposals/{pid}/one-click/{job}")).json()
    assert v["status"] == "succeeded", v
    assert v["header"] == "· 조감도부터 나머지 자동 완성"
    assert [s["status"] for s in v["steps"] if s["key"] in ("mi", "vp")] == ["confirmed", "confirmed"]
    assert all(s["status"] in ("inferred_done", "confirmed", "skipped") for s in v["steps"]), v["steps"]
    assert v["counts_label"][0].startswith("확정 ") and v["counts_label"][2].startswith("검토 필요 ")
    assert v["done_intro"].startswith("딸깍으로 제안서를 완성했습니다.")
    assert v["file"] and v["file"]["pptx_file_id"]
    assert v["review_header"].startswith("검토가 필요한 곳 ")
    assert v["memos"] and v["memos"][0]["text"] == "Why Samsung은 비용 중심으로"
    # 메모가 why 초안 호출 문맥에(AC-113)
    why_calls = [c for c in ctx.stubs.ai_calls if c.get("task") == "pr.section_draft" and "섹션: why" in str(c)]
    assert why_calls and "Why Samsung은 비용 중심으로" in str(why_calls[-1])
    # 확정 섹션 시트 내용은 그대로(AC-116)
    assert (await client.get(f"/v1/proposals/{pid}/sheets/{mi_sheet}")).json()["content"] == mi_before
    p = (await client.get(f"/v1/proposals/{pid}")).json()
    assert p["version"] == 1 and p["stepper"]["complete"] is True and p["stepper"]["auto_from"] == 4


async def test_one_click_cancel_returns(client: Any, ctx: Any) -> None:
    pid = await setup(client)
    await client.put(f"/v1/proposals/{pid}/type", json={"type": "quickwin"})
    await client.put(f"/v1/proposals/{pid}/industry", json={"keep_default": True})
    await client.get(f"/v1/proposals/{pid}/sections/spaceProducts")
    r = await client.post(f"/v1/proposals/{pid}/one-click", json={"from_stage": "sections", "from_section_key": "spaceProducts"})
    job = r.json()["job_id"]
    from winmate_common.jobs import jobs
    await jobs().cancel(job)
    await ctx.run_jobs()
    assert (await jobs().get(job)).status == "canceled"
    p = (await client.get(f"/v1/proposals/{pid}")).json()
    assert p["stage"] == "sections" and p["current_section_key"] == "spaceProducts"


async def test_confirm_items_flow(client: Any, ctx: Any) -> None:
    pid = await setup(client, links=[{"feature": "mi", "ref_id": "mi_acoffee"}, {"feature": "birdseye", "ref_id": "be_lobby"}])
    await client.put(f"/v1/proposals/{pid}/type", json={"type": "standard"})
    await client.put(f"/v1/proposals/{pid}/industry", json={"keep_default": True})
    await client.post(f"/v1/proposals/{pid}/sections/mi:fill", json={})
    await client.post(f"/v1/proposals/{pid}/sections/spaceProducts:fill", json={})
    await ctx.run_jobs()
    # 제품 놓기 → 수량 = 매장 수 × 1(파생 값) + 「수량 가정」
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "spaceProducts", "via": "drag_item",
                                                               "source": {"kind": "product", "ref": {"kb_kind": "model", "id": "QM65C"}, "label": "QM65C"}})
    assert r.status_code == 200, r.text
    await ctx.run_jobs()
    cl = (await client.get(f"/v1/proposals/{pid}/confirm-items", params={"status": "open"})).json()
    assert cl["header_label"].startswith("확정 필요 ")
    assert cl["intro"].startswith("제안서 ")
    tags = {it["tag"] for it in cl["items"]}
    assert "수치" in tags and "수량 가정" in tags, tags
    # MI 경쟁 비교의 [확인 필요] 칸 → 값 넣고 확정
    cp = next(it for it in cl["items"] if it["tag"] == "수치" and it["fact_id"])
    r = await client.post(f"/v1/proposals/{pid}/confirm-items/{cp['id']}:resolve",
                          json={"value": "지원", "evidence": {"kind": "url", "ref": "https://example.com/a"}})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["item"]["status"] == "confirmed" and res["changed_sheet_ids"]
    sh = (await client.get(f"/v1/proposals/{pid}/sheets/{res['changed_sheet_ids'][0]}")).json()
    assert "지원" in str(sh["display"])
    # 매장 수 확정 → 파생 수량이 함께(AC-144 축소판)
    facts = (await client.get(f"/v1/proposals/{pid}/facts")).json()["items"]
    store = next(f for f in facts if f["key"] == "store_count")
    qty = next(f for f in facts if f["key"].startswith("qty_qm65c"))
    assert qty["formula_label"] == "QM65C 수량 = 매장 수 × 1대"
    r = await client.put(f"/v1/proposals/{pid}/facts/{store['id']}", json={"value": "330"})
    assert r.status_code == 200, r.text
    facts = (await client.get(f"/v1/proposals/{pid}/facts")).json()["items"]
    assert next(f for f in facts if f["key"].startswith("qty_qm65c"))["display"] == "330대"
    # 노트로 옮기기(AC-145) → 생성 문서에서 「—」 + 노트
    other = next(it for it in (await client.get(f"/v1/proposals/{pid}/confirm-items", params={"status": "open"})).json()["items"]
                 if it["fact_id"] and it["tag"] == "수치")
    r = await client.post(f"/v1/proposals/{pid}/confirm-items/{other['id']}:move-to-note")
    assert r.status_code == 200 and r.json()["status"] == "moved_to_note"
    from winmate_proposal import render_doc
    built = await render_doc.build(pid)
    slide = next(s for s in built["document"]["slides"] if s.get("sheet_id") == other["sheet_id"])
    assert "—" in str(slide["slots"]) and "[" in slide["notes"]
    # 고객에게 물을 문장
    q = next(it for it in (await client.get(f"/v1/proposals/{pid}/confirm-items", params={"status": "open"})).json()["items"])
    r = await client.post(f"/v1/proposals/{pid}/confirm-items/{q['id']}:question", json={"push_to_rq": True})
    assert r.status_code == 200 and r.json()["text"]
    # 다시 찾기 — 웹 질의에 고객사명 없음(AC-147)
    r = await client.post(f"/v1/proposals/{pid}/confirm-items:research", json={})
    assert r.status_code == 202
    await ctx.run_jobs()
    web = [c for c in ctx.stubs.ai_calls if "websearch" in (c.get("path") or "")]
    assert all("A 커피" not in (c.get("query") or "") and "커피 프랜차이즈" not in (c.get("query") or "") for c in web)
    cl = (await client.get(f"/v1/proposals/{pid}/confirm-items", params={"status": "open"})).json()
    assert all(it["status"] == "open" for it in cl["items"])
    assert any(it["candidates"] for it in cl["items"]), [it["candidates"] for it in cl["items"]]
