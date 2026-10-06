"""기본 흐름(05-vp.md §3.1) — 만들기 → 첨부 → 재료 잡 → (되묻기) → 구조 → 생성 → 결과 → 넘김 · 내보내기."""
from __future__ import annotations

from vp_helpers import RFP_TEXT, run_jobs, upload


async def make_vp(client, **body):
    r = await client.post("/v1/vps", json={"start": "direct", **body})
    assert r.status_code == 201, r.text
    return r.json()


async def test_direct_flow_end_to_end(client):
    doc = await make_vp(client, customer_name="A 커피 프랜차이즈", note="메뉴 교체 비용 절감이 1순위")
    vid = doc["id"]
    assert doc["status"] == "draft" and doc["ui_status"] == "draft"
    assert doc["resume_route"] == f"/vp/{vid}/materials"
    assert [c["axis"] for c in doc["coverage"]] == ["challenge", "value", "evidence", "stakeholder"]

    fid = await upload("A커피_디지털메뉴보드_RFP.txt", RFP_TEXT)
    r = await client.post(f"/v1/vps/{vid}/attachments", json={"file_id": fid})
    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "rfp"

    r = await client.post(f"/v1/vps/{vid}/materials:collect", json={})
    assert r.status_code == 202, r.text
    job = r.json()["job_id"]
    running = (await client.get(f"/v1/vps/{vid}")).json()
    assert running["ui_status"] == "run" and running["status"] == "collecting"
    await run_jobs()

    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["materials_ready"] is True, doc.get("last_error")
    att = doc["attachments"][0]
    assert att["status"] == "read" and att["summary"].startswith("RFP")
    axes = {m["axis"] for m in doc["materials"] if not m["excluded"]}
    assert "challenge" in axes
    assert doc["plan"] and doc["plan"]["sheets"], doc["plan"]
    assert doc["industry"]["code"] in ("FB", "GEN", "RT")
    assert all(d["job_id"] == job for d in doc["decisions"] if d.get("job_id"))

    if [q for q in doc["questions"] if q["status"] == "open"]:
        r = await client.post(f"/v1/vps/{vid}/questions:answer", json={"answers": [], "proceed": True})
        assert r.status_code == 200, r.text
        await run_jobs()
        doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert not [q for q in doc["questions"] if q["status"] == "open"]
    assert doc["resume_route"] in (f"/vp/{vid}/structure", f"/vp/{vid}/materials/review")

    plan = (await client.get(f"/v1/vps/{vid}/plan")).json()
    assert plan["cta_label"].endswith("분)")
    assert [r_["key"] for r_ in plan["decisions"]] == ["업종", "업종 레이아웃", "이해관계자형", "시트 수", "추정 값", "이미지", "톤"]

    r = await client.post(f"/v1/vps/{vid}/generate", json={})
    assert r.status_code == 202, r.text
    gen = r.json()["job_id"]
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["resume_route"] == f"/vp/{vid}/generating?job={gen}"
    await run_jobs()

    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["generated"] is True, doc.get("last_error")
    assert doc["status"] in ("done", "ask", "check")
    sheets = [s for s in doc["sheets"] if s["kind"] == "main"]
    assert len(sheets) == len(plan["sheets"])
    for s in sheets:
        assert s["status"] == "done" and s["title"], s
        assert s["meta_label"].startswith("근거")
    assert doc["intros"]["result"].startswith(f"가치 제안 {len(sheets)}장을 만들었어요")
    assert doc["version"] >= 2

    vps = (await client.get("/v1/vps")).json()
    row = next(i for i in vps["items"] if i["id"] == vid)
    assert row["layout_chips"] and row["action_label"] in ("열기", "확인", "답하기")

    vp_sheet = next(s for s in sheets if s["role"] == "VP")
    lo = (await client.get(f"/v1/vps/{vid}/sheets/{vp_sheet['id']}/layout-options")).json()
    assert lo["candidates"][0]["state"] == "cur"
    assert lo["other_sheets_label"].startswith("· 가치 제안")

    slots = (await client.get(f"/v1/vps/{vid}/image-slots")).json()
    assert slots["counts"]["slots"] == len(slots["items"])

    pk = (await client.get(f"/v1/vps/{vid}/packages")).json()
    assert [t["proposal_type"] for t in pk["types"]] == ["standard", "quickwin", "solution"]
    assert pk["dock"].startswith("표준 · 보낼 시트")

    txt = (await client.get(f"/v1/vps/{vid}/copy-text")).json()["text"]
    assert vp_sheet["title"] in txt

    r = await client.post(f"/v1/vps/{vid}/handoffs", json={"proposal_id": None, "proposal_type": "standard",
                                                           "interview_numbers_confirmed": False})
    assert r.status_code == 201, r.text
    ho = r.json()
    assert ho["open_route"] == f"/proposal/new?handoff={ho['id']}"
    got = (await client.get(f"/v1/handoffs/{ho['id']}")).json()
    assert got["vp_id"] == vid and got["package"]["sheets"]

    ph = (await client.get(f"/v1/value-props/{vid}/proposal-handoff", params={"type": "standard"})).json()
    assert ph["source"]["feature"] == "VP" and ph["items"]

    vers = (await client.get(f"/v1/vps/{vid}/versions")).json()["items"]
    reasons = [v["reason"] for v in vers]
    assert "재료 완료" in reasons and "생성 완료" in reasons and "넘김" in reasons
