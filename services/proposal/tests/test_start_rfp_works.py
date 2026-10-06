"""PR1F(RFP로 시작) · PR1L(기존 작업에서 시작) · 연결 자료 해제 · 되살리기."""
from __future__ import annotations

from typing import Any

RFP_TEXT = """A 커피 프랜차이즈 제안요청서
사업명: 전국 매장 디지털 메뉴보드 전환
발주처: A 커피 프랜차이즈
당사는 전국 320개 매장을 운영하는 커피 전문점 브랜드입니다.
요구사항
1. 본사 콘텐츠 일괄 배포
2. 프로모션 교체 주기 단축
3. 매장별 메뉴 가격 차등
4. 320개 매장 단계 도입
5. 기존 POS 연동
제안서 제출 마감: 2026-10-08
제안 설명회: 2026-10-22 · 발표 20분
"""


async def make(client: Any, **body: Any) -> dict[str, Any]:
    r = await client.post("/v1/proposals", json={"start_mode": "blank", **body})
    assert r.status_code == 201, r.text
    return r.json()


async def test_rfp_extract_and_confirm(client: Any, ctx: Any) -> None:
    from winmate_common.platform import save_file
    meta = await save_file("A커피_디지털메뉴보드_RFP.txt", RFP_TEXT.encode(), "text/plain", source="upload", confidential=True)
    p = await make(client)
    pid = p["id"]
    r = await client.post(f"/v1/proposals/{pid}/rfp", json={"file_ids": [meta["id"]]})
    assert r.status_code == 202, r.text
    job = r.json()["job_id"]
    v = (await client.get(f"/v1/proposals/{pid}/rfp")).json()
    assert v["status"] == "running" and [x["label"] for x in v["phases"]] == ["읽기", "항목 찾기", "채우기"]
    await ctx.run_jobs()
    from winmate_common.jobs import jobs
    j = await jobs().get(job)
    assert j.status == "succeeded", (j.error, j.result)
    steps = [e["data"].get("step") for _, e in await jobs().events(job) if e.get("type") == "step"]
    assert [s for s in steps if s in ("read", "locate", "fill")] == ["read", "locate", "fill"]      # AC-022 순서
    v = (await client.get(f"/v1/proposals/{pid}/rfp")).json()
    assert v["status"] == "done", v
    assert v["tally"] == {"found": 6, "guess": 1, "empty": 2}, v["fields"]
    assert v["found_count"] == 7
    assert v["intro"].endswith("원문에 없는 2개 항목은 비워 두었어요.")
    ind = next(f for f in v["fields"] if f["key"] == "industry")
    assert ind["state"] == "guess" and ind["state_label"] == "추정"
    bud = next(f for f in v["fields"] if f["key"] == "budget")
    assert bud["value"] == "원문에 없음" and bud["source_label"] == "—"
    rq = next(f for f in v["fields"] if f["key"] == "requirements")
    assert rq["value"] == "5건 · 본사 콘텐츠 일괄 배포 외 4"
    assert v["excerpts"] and any(pt.get("field_no") for pt in v["excerpts"][0]["parts"])
    # RFP 호출은 기밀(AC-024)
    calls = [c for c in ctx.stubs.ai_calls if c.get("task") == "pr.rfp_fields"]
    assert calls and all(c.get("confidential") is True for c in calls)
    # requirements from-files 호출(AC-025)
    assert any(c.get("op") == "from_files" for c in ctx.stubs.calls.get("requirements", []))
    r = await client.put(f"/v1/proposals/{pid}/rfp/fields/decision_makers", json={"value": "운영본부장, 마케팅팀장"})
    assert r.status_code == 200
    r = await client.post(f"/v1/proposals/{pid}/rfp:confirm")
    assert r.status_code == 200, r.text
    pv = r.json()
    assert pv["customer"]["name"] == "A 커피 프랜차이즈"
    assert pv["title"] == "전국 매장 디지털 메뉴보드 전환"
    assert pv["schedule"]["submit_due"] == "2026-10-08"
    assert pv["customer"]["decision_makers"] == "운영본부장, 마케팅팀장"
    assert pv["stage"] == "type" and pv["rq_ref"]["rq_id"]


async def test_works_preview_apply_and_unlink(client: Any, ctx: Any) -> None:
    p = await make(client, start_mode="works", customer={"name": "A 커피 프랜차이즈"})
    pid = p["id"]
    r = await client.put(f"/v1/proposals/{pid}/links", json={"links": [
        {"feature": "storyboard", "ref_id": "sb_acoffee", "on": True}, {"feature": "mi", "ref_id": "mi_acoffee", "on": True},
        {"feature": "birdseye", "ref_id": "be_lobby", "on": True}, {"feature": "scenario", "ref_id": "sc_day", "on": True}]})
    assert r.status_code == 200, r.text
    out = r.json()
    pv = out["preview"]
    assert pv["counts_label"] == "채움 3 · 일부 3 · 새로 작성 2", pv
    assert pv["recommended_type"]["type"] == "standard"
    assert pv["recommended_type"]["reason"] == "조감도 · 시나리오가 있어 공간 섹션까지 채울 수 있어요."
    assert pv["customer_from"]["label"] == "고객 · 프로젝트 · Storyboard에서"
    assert [s["source_label"] for s in pv["sections"]] == ["MI 작업", "Storyboard", "조감도", "조감도 배치안", "시나리오", "새로 찾기", "MI 경쟁사", "새로 작성"]
    r = await client.post(f"/v1/proposals/{pid}/links:apply")
    assert r.status_code == 202
    await ctx.run_jobs()
    pr = (await client.get(f"/v1/proposals/{pid}")).json()
    assert pr["stage"] == "type"
    assert pr["link_count"] == 4
    lo = (await client.get(f"/v1/proposals/{pid}/links")).json()
    assert {x["feature"] for x in lo["links"]} == {"storyboard", "mi", "birdseye", "scenario"}
    assert all(x["status"] == "linked" for x in lo["links"])
    # 섹션 초안은 아직 없음(AC-027)
    await client.put(f"/v1/proposals/{pid}/type", json={"type": "standard"})
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    assert all(s["status"] == "need" for s in sv["sheets"])
    await client.post(f"/v1/proposals/{pid}/sections/mi:fill", json={})
    await ctx.run_jobs()
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    assert sv["status"] == "ready"
    mi_link = sv["sources"][0]["id"]
    r = await client.delete(f"/v1/proposals/{pid}/links/{mi_link}")
    assert r.status_code == 200 and r.json()["toast"] == "연결 해제됨"
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    assert sv["status"] == "stale"                      # AC-066
    r = await client.post(f"/v1/proposals/{pid}/links/{mi_link}:restore")
    assert r.status_code == 200 and r.json()["status"] == "linked"
