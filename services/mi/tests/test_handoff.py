"""넘김 · 내보내기 · 익명화 · 제안서 계약 — AC-MI-65 · 66 · 67 · 68 · 69 · 70 · 71 · 72 · 73 · 74 · 90 · 91 · 92 · 94."""
from __future__ import annotations

import json
from typing import Any

from mi_scenario import COMP, add_qm55c, create, customer_claims, design, full_fb, run, setup_fb

from winmate_common import testing
from winmate_mi import bundle as B
from winmate_mi import store as R

REAL = list(COMP.keys())


def _has_real(obj: Any, names: list[str] | None = None) -> list[str]:
    s = json.dumps(obj, ensure_ascii=False)
    return [n for n in (names or ["가나 디스플레이", "다라 사이니지", "마바 미디어"]) if n in s]


async def _confirm_all(env: Any, aid: str, tabs: tuple[str, ...]) -> None:
    items = (await env.c.get(f"/v1/analyses/{aid}/fix-items")).json()["items"]
    for f in items:
        if f["tab"] in tabs and f["status"] == "warn":
            val = "6 : 4" if f["input_kind"] == "ratio" else ("1" if f["input_kind"] == "number" else "확인함")
            r = await env.c.patch(f"/v1/analyses/{aid}/fix-items/{f['id']}", json={"value": val})
            assert r.status_code == 200, r.text
    await env.c.post(f"/v1/analyses/{aid}/fix-items/apply", json={"carry_remaining": True})


async def test_ac65_handoff_delivered_and_no_target(env):
    aid = await full_fb(env)
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi"})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["status"] == "prepared" and out["target_id"] == "prp_test1" and out["bundle_url"].endswith(f"handoff_id={out['handoff_id']}")
    r = await env.c.patch(f"/v1/analyses/{aid}/handoffs/{out['handoff_id']}", json={"status": "delivered", "target_title": "A 커피 메뉴보드"})
    assert r.json()["status"] == "delivered"
    lst = (await env.c.get("/v1/analyses")).json()["items"]
    assert next(i for i in lst if i["id"] == aid)["proposal_title"] == "A 커피 메뉴보드"
    a2 = (await create(env, links={}))["id"]
    await design(env, a2)
    await run(env, a2)
    r = await env.c.post(f"/v1/analyses/{a2}/handoffs", json={"target": "proposal_mi"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_TARGET"


async def test_ac66_ac92_real_names(env):
    aid = await full_fb(env)
    await env.c.patch(f"/v1/analyses/{aid}", json={"anonymize": False})
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi"})
    assert r.status_code == 409 and r.json()["error"]["details"]["asks"][0]["kind"] == "real_names"
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi", "confirm": {"real_names": False}})
    hof = r.json()["handoff_id"]
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle?target=proposal_mi&handoff_id={hof}")).json()
    assert not _has_real(b) and "경쟁사 A" in json.dumps(b, ensure_ascii=False)
    # AC-MI-92 — named=true 는 실명 확인 기록이 있어야
    r = await env.c.get(f"/v1/analyses/{aid}/proposal-handoff?handoff_id={hof}&named=true")
    assert r.status_code == 409 and r.json()["error"]["code"] == "ASK_REQUIRED"
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi", "confirm": {"real_names": True}})
    hof2 = r.json()["handoff_id"]
    ph = (await env.c.get(f"/v1/analyses/{aid}/proposal-handoff?handoff_id={hof2}&named=true")).json()
    assert _has_real(ph)
    rec = await R.call(R.get_doc, R.HOF, hof2)
    assert len(rec["served_named_at"]) == 1
    anon = (await env.c.get(f"/v1/analyses/{aid}/proposal-handoff?handoff_id={hof2}")).json()
    assert not _has_real(anon)


async def test_ac67_no_real_names_anywhere(env):
    aid = await full_fb(env)
    doc = await R.call(R.get_analysis, aid)
    for c in doc["competitors"]:
        c["aliases"] = [c["real_name"].split()[0] + "디스"] if c["letter"] == "A" else []
    await R.call(R.put_analysis, doc)
    outs = [(await env.c.get(f"/v1/analyses/{aid}/bundle?target={t}")).json() for t in ("proposal_mi", "proposal_why", "vp", "storyboard", "scenario")]
    outs.append((await env.c.get(f"/v1/analyses/{aid}/proposal-handoff")).json())
    outs.append((await env.c.get(f"/v1/analyses/{aid}/shared-view")).json())
    outs.append((await env.c.get(f"/v1/analyses/{aid}/table-text")).json())
    outs.append((await env.c.get(f"/v1/analyses/{aid}/evidence")).json())
    doc = await R.call(R.get_analysis, aid)
    v = await R.call(R.get_version, aid, int(doc["result_version"]))
    for fmt in ("pdf_report", "pptx_onepager", "xlsx_table"):
        outs.append(B.export_document(doc, v, fmt, "customer", {"quadrants": {"competitor": "가나 디스플레이 대비 강점"}, "conclusion": "결론"}))
    aliases = [a for c in doc["competitors"] for a in c.get("aliases") or []]
    for o in outs:
        assert not _has_real(o, REAL + aliases), _has_real(o, REAL + aliases)
    sv = outs[6]
    assert [c["label"] for c in sv["competitor"]["table"]["columns"]] == ["경쟁사 A", "경쟁사 B", "경쟁사 C", "삼성"]
    assert all(c["sub"] == "" for c in sv["competitor"]["table"]["columns"])
    assert outs[7]["text"].splitlines()[0] == "요구사항 항목\t경쟁사 A\t경쟁사 B\t경쟁사 C\t삼성"
    # 사내용 내보내기는 실명(AC-MI-71)
    internal = B.export_document(doc, v, "pdf_report", "internal")
    assert _has_real(internal)


async def test_ac68_relabel_after_removal(env):
    aid = await full_fb(env)
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    b = next(c for c in a["competitors"] if c["letter"] == "B")
    await env.c.patch(f"/v1/analyses/{aid}/competitors/{b['id']}", json={"removed": True})
    tt = (await env.c.get(f"/v1/analyses/{aid}/table-text")).json()
    assert tt["columns"] == ["경쟁사 A", "경쟁사 B", "삼성"]
    assert "다라 사이니지" not in tt["text"]
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi"})
    rec = await R.call(R.get_doc, R.HOF, r.json()["handoff_id"])
    cmap = {c["letter"]: c["id"] for c in a["competitors"]}
    assert rec["anonymization_map"] == {cmap["A"]: "경쟁사 A", cmap["C"]: "경쟁사 B"}


async def test_ac69_type_naming(env):
    setup_fb(env)
    env.ai.llm["mi.competitor_candidates"]["items"][1]["kind_label"] = "국내 대형 가전 · 사이니지"
    aid = (await create(env))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    await run(env, aid)
    await env.c.patch(f"/v1/analyses/{aid}", json={"naming_mode": "type"})
    tt = (await env.c.get(f"/v1/analyses/{aid}/table-text")).json()
    assert tt["columns"] == ["국내 대형 가전 · 사이니지 1", "국내 대형 가전 · 사이니지 2", "국내 CMS · 솔루션", "삼성"]
    lst = (await env.c.get(f"/v1/analyses/{aid}/competitors")).json()["items"]
    assert [c["export_display"] for c in lst][:2] == ["국내 대형 가전 · 사이니지 1", "국내 대형 가전 · 사이니지 2"]


async def test_ac70_confidential_ask_and_exclude(env):
    setup_fb(env)
    fid = env.files.add("내부 매출 자료.pdf", ["A 커피 직영점 매출은 2025년 1,200억 원이다."], confidential=True)
    env.ai.llm["mi.classify_file"] = {"doc_kind": "internal_research", "classification": "confidential", "title": "내부 매출"}

    def cust(body: dict[str, Any]) -> dict[str, Any]:
        out = customer_claims(body)
        out["claims"].append({"local_id": "k9", "text": "직영점 매출은 2025년 1,200억 원이에요.", "metric_key": "store_sales", "metric_label": "직영점 매출",
                              "citations": [{"evidence_id": "E1", "quote": "A 커피 직영점 매출은 2025년 1,200억 원이다"}]})
        out["blocks"]["strategy"].append("k9")
        return out

    env.ai.llm["mi.extract_claims_customer"] = cust
    aid = (await create(env, file_ids=[fid]))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    await env.c.patch(f"/v1/analyses/{aid}", json={"internal": {"included_file_ids": [fid], "excluded_file_ids": []}})
    await run(env, aid)
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi"})
    assert r.status_code == 409
    asks = r.json()["error"]["details"]["asks"]
    assert asks[0]["kind"] == "confidential" and asks[0]["default"] == "exclude"
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi", "confirm": {"confidential": "exclude"}})
    hof = r.json()["handoff_id"]
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle?target=proposal_mi&handoff_id={hof}")).json()
    cb = next(s for s in b["sheets"] if s["sheet_type"] == "CB")
    assert "직영점 매출은 2025년 [00]억 원이에요." in cb["content"]["strategy"]
    assert any(f["reason"] == "대외비 자료라 뺐어요" for f in cb["fact_check"])
    assert "1,200억" not in json.dumps(b, ensure_ascii=False)


async def test_ac71_export_job_xlsx(env):
    aid = await full_fb(env)
    r = await env.c.post(f"/v1/analyses/{aid}/exports", json={"format": "xlsx_table", "audience": "customer"})
    assert r.status_code == 202
    jid = r.json()["job_id"]
    await env.drain()
    job = await env.job(jid)
    assert job.status == "succeeded", job.error
    assert job.result["file_id"] and job.result["format"] == "xlsx_table"


async def test_ac72_options(env):
    aid = await full_fb(env)
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi", "options": {"cite_sources": False, "fix_notes": False, "link_why": True}})
    hof = r.json()["handoff_id"]
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle?target=proposal_mi&handoff_id={hof}")).json()
    assert all(s["footnotes"] == [] for s in b["sheets"]) and all(s["fact_check"] == [] for s in b["sheets"])
    assert "[확정 필요]" not in json.dumps([s.get("why") for s in b["sheets"]], ensure_ascii=False)
    ph = (await env.c.get(f"/v1/analyses/{aid}/proposal-handoff?handoff_id={hof}")).json()
    sts = {f["status"] for f in ph["facts"]}
    assert {"confirmed", "unconfirmed", "placeholder"} <= sts           # AC-MI-91


async def test_ac73_workspace_items_no_real_names(env):
    aid = await full_fb(env)
    async with testing.api_client(env.apps["workspace"]) as wc:
        items = (await wc.get("/v1/items", params={"feature": "MI", "owner": "all", "limit": 50})).json()["items"]
    mine = [i for i in items if i["item_id"] == aid]
    assert mine and not _has_real(mine)
    assert mine[0]["status"] == "완료" and mine[0]["summary"].startswith("외식 · 카페 · 시장 · 고객 · 사용자 · 경쟁 · 출처 ")


async def test_ac74_vp_bundle(env):
    aid = await full_fb(env)
    b = (await env.c.get(f"/v1/analyses/{aid}/bundle?target=vp")).json()
    assert b["customer"]["segment"] == "FB"
    nums = b["vp_materials"]["numbers"]
    assert nums and all({"as_of", "source_age_months", "status", "footnote"} <= set(n) for n in nums)


async def test_ac90_proposal_handoff_items(env):
    aid = await full_fb(env)
    await _confirm_all(env, aid, ("customer", "competitor"))
    ph = (await env.c.get(f"/v1/analyses/{aid}/proposal-handoff?type=standard&section=mi")).json()
    items = ph["items"]
    assert [i["sheet_role"] for i in items] == ["MS", "CB", "CP", "US"]
    assert [i["status"] for i in items] == ["warn", "ok", "ok", "add"]
    assert items[0]["status_label"].startswith("[확정 필요] ") and items[1]["status_label"] == "그대로 들어가요"
    assert items[3]["status_label"] == "섹션에 없는 시트 · 추가" and items[3]["include_default"] is False
    assert all(i["include_default"] for i in items[:3])
    assert ph["source"]["feature"] == "MI" and ph["customer"]["industry_code"] == "FB"
    why = (await env.c.get(f"/v1/analyses/{aid}/proposal-handoff?section=why")).json()
    assert [i["key"] for i in why["items"]] == ["CM", "ST"]


async def test_ac94_facts_lookup(env):
    setup_fb(env)
    fid = env.files.add("A 커피 IR.pdf", ["A 커피 매장은 320곳이다."])
    env.ai.llm["mi.classify_file"] = {"doc_kind": "ir", "classification": "public", "title": "IR"}

    def cust(body: dict[str, Any]) -> dict[str, Any]:
        out = customer_claims(body)
        out["claims"].append({"local_id": "k8", "text": "A 커피 매장은 320곳이에요.", "metric_key": "store_count", "metric_label": "매장 수",
                              "citations": [{"evidence_id": "E1", "quote": "A 커피 매장은 320곳이다"}]})
        out["blocks"]["expansion"].append("k8")
        return out

    env.ai.llm["mi.extract_claims_customer"] = cust
    aid = (await create(env, file_ids=[fid]))["id"]
    await add_qm55c(env, aid)
    await design(env, aid)
    await run(env, aid)
    env.ai.reset_calls()
    r = await env.c.post(f"/v1/analyses/{aid}/facts:lookup", json={"questions": [{"key": "q1", "label": "매장 수", "unit": "곳"}]})
    out = r.json()
    cands = out["items"][0]["candidates"]
    assert cands[0]["value"] == "320" and cands[0]["status"] == "matched"
    assert env.ai.web_calls() == []


async def test_storyboard_evidence_snapshot(env):
    """MI4 `Key Message에 근거로 붙이기` — storyboard 묶음과 같은 익명 규칙 · 자리표시 수치 제외 · PostEvidence.source 그대로(02-storyboard §8.3)."""
    aid = await full_fb(env)
    r = await env.c.patch(f"/v1/analyses/{aid}", json={"links": {"storyboard_id": "sb_test1", "storyboard_title": "A 커피 기획"}})
    assert r.status_code == 200, r.text
    ev = (await env.c.get(f"/v1/analyses/{aid}/evidence")).json()
    assert ev["source"] == {"service": "mi", "ref_id": aid, "title": ev["source"]["title"], "route": f"/mi/{aid}/result"} and ev["source"]["title"]
    assert ev["storyboard_id"] == "sb_test1" and ev["storyboard_title"] == "A 커피 기획"
    kinds = [i["kind"] for i in ev["items"]]
    assert kinds and kinds[0] == "strength" and set(kinds) <= {"strength", "number", "challenge"}
    assert all(i["default_on"] == (i["kind"] == "strength") for i in ev["items"])
    assert not any("[00]" in i["text"] for i in ev["items"])
    assert all(1 <= len(i["text"]) <= 2000 for i in ev["items"])
    assert all(i["status"] in ("원문 일치", "확인 필요") for i in ev["items"] if i["kind"] == "number")
    assert not _has_real(ev)
    r = await env.c.get(f"/v1/analyses/{(await create(env))['id']}/evidence")
    assert r.status_code == 404


async def test_proposal_handoff_keeps_market_sheet_id_when_replanned(env):
    """리포트(쓰임 none)로 분석한 뒤 표준 제안서로 넘기면 시트를 다시 짠다 — 시장 시트(MS ↔ MS+TR)가 같은 id 를 이어
    넘김 `sheets`(MI4 에서 고른 id)로 걸러도 빠지지 않는다(통합: 제안서 MI 섹션 MS 가 늘 비어 있던 것)."""
    aid = await full_fb(env)
    doc = await R.call(R.get_analysis, aid)
    doc["usage"] = {**(doc.get("usage") or {}), "value": "none"}
    await R.call(R.put_analysis, doc)
    ev = (await env.c.get(f"/v1/analyses/{aid}/export-view")).json()
    ids = [r["id"] for r in ev["rows"] if r["included"]]
    r = await env.c.post(f"/v1/analyses/{aid}/handoffs", json={"target": "proposal_mi", "sheets": ids})
    assert r.status_code == 200, r.text
    hof = r.json()["handoff_id"]
    a = (await env.c.get(f"/v1/analyses/{aid}/proposal-handoff?type=standard&handoff_id={hof}")).json()
    b = (await env.c.get(f"/v1/analyses/{aid}/proposal-handoff?type=standard&handoff_id={hof}")).json()
    keys = [i["key"] for i in a["items"]]
    assert keys == [i["key"] for i in b["items"]]
    assert "MS" in [i["sheet_role"] for i in a["items"]]
    assert all(i["key"] in ids for i in a["items"] if i["include_default"]), (keys, ids)


async def test_sheet_plan_market_id_survives_ms_mstr_switch(env):
    """시장 시트는 업종 틀이 있으면 MS+TR, 없으면 MS 로 저장된다 — 다시 짤 때 이름이 바뀌어도 같은 id(넘김 고른 시트와 맞도록)."""
    from winmate_mi import layout as LY
    aid = await full_fb(env)
    doc = await R.call(R.get_analysis, aid)
    v = await R.call(R.get_version, aid, int(doc["result_version"]))
    prev = [dict(s) for s in v.get("slides") or []]
    mk = next(s for s in prev if s["sheet_type"] in ("MS", "MS+TR"))
    for flip in ("MS", "MS+TR"):
        mk["sheet_type"] = flip
        plan = LY.sheet_plan(doc, v, previous=prev, usage="standard")
        assert next(r for r in plan if r["sheet_type"] in ("MS", "MS+TR"))["id"] == mk["id"], flip
