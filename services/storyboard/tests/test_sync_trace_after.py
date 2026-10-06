"""§9.1 수용 기준 24–33 + 오류 경로 — 정의서 동기화 · 요구 정리 · 일정 · 내보내기 · 넘기기 · 기밀 · 모델 오류."""
from __future__ import annotations

import json

from winmate_common.jobs import jobs

from sb_flow import create, drain, section_key, space_named, to_outline
from sb_rqdata import reply
from sb_world import RQ


async def test_sync_dry_run_preview(client, world):
    sb = await to_outline(client)
    world.rq.replies["rp_1"] = reply(RQ, "rp_1")
    links_before = len(world.rq.calls_of("PUT", "/links/"))
    rev_before = sb["revision"]
    r = await client.post(f"/v1/storyboards/{sb['id']}/requirement-sync",
                          json={"requirement_id": RQ, "reply_id": "rp_1", "dry_run": True})
    assert r.status_code == 202, r.text
    ref = r.json()["ref"]
    assert ref["kind"] == "sync_preview"
    await drain()
    p = (await client.get(f"/v1/storyboards/{sb['id']}/sync-previews/{ref['id']}")).json()
    assert p["status"] == "ready" and p["rows"] and p["count"] >= 1
    places = [row["place_label"] for row in p["rows"]]
    assert "Overview" in places and "Part 1-2" in places
    assert all(not row["revertible"] for row in p["rows"])
    assert p["causes"][0].startswith("요구사항 정의서 v3")
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb2["revision"] == rev_before and sb2["outline"]["sections"] == sb["outline"]["sections"]
    assert len(world.rq.calls_of("PUT", "/links/")) == links_before


async def test_sync_apply_only_affected(client, world):
    sb = await to_outline(client)
    world.rq.add_version(RQ, 3, diff=[
        {"target": {"kind": "item", "id": "ri_02"}, "kind": "changed", "label": "공간컨텐츠실장", "before": "업무환경 플랫폼",
         "after": "입주사 앱 · 공용 공간 예약 · 방문객 안내"},
        {"target": {"kind": "field", "id": "final_audience"}, "kind": "changed", "label": "최종 제안대상", "before": None,
         "after": "대표이사 · 투자심의위원 2"}], note="11/11 회의 반영", final_audience="대표이사 · 투자심의위원 2")
    r = await client.post(f"/v1/storyboards/{sb['id']}/requirement-sync", json={"requirement_id": RQ, "to_version": 3})
    assert r.status_code == 202 and r.json()["ref"]["kind"] == "storyboard"
    await drain()
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb2["requirement_ref"]["version"] == 3
    before = {s["key"]: s["lines"] for s in sb["outline"]["sections"]}
    after = {s["key"]: s["lines"] for s in sb2["outline"]["sections"]}
    changed = {k for k in before if before[k] != after[k]}
    assert changed == {"overview", "p1_2"}
    assert any("대표이사" in ln["text"] for ln in after["overview"])
    rows = [c for c in sb2["changes"] if c["cause"]["kind"] == "rq_sync"]
    assert {c["cause"]["label"] for c in rows} == {"요구사항 정의서 v3 · 11/11 회의 반영"}
    kept = next(c for c in rows if c["kind"] == "kept")
    assert kept["place_label"] == "Part 1-3" and kept["aspect"] == "Galaxy XR"
    link = world.rq.links[(RQ, sb["id"])]
    assert link["rq_version"] == 3
    # 비교 화면 · 되돌리기
    cmp = (await client.get(f"/v1/storyboards/{sb['id']}/compare")).json()
    assert cmp["to"]["version_label"] == "v1" and cmp["causes"] == ["요구사항 정의서 v3 · 11/11 회의 반영"]
    ov = next(c for c in cmp["rows"] if c["place_label"] == "Overview")
    assert ov["aspect"] == "청중" and ov["revertible"]
    r = await client.post(f"/v1/storyboards/{sb['id']}/changes/{ov['id']}/revert")
    assert section_key(r.json(), "overview")["lines"] == before["overview"]


async def test_auto_sync_on_open(client, world, monkeypatch):
    from winmate_storyboard import ops_core
    monkeypatch.setattr(ops_core, "_RQ_CHECK_S", 0)
    sb = await to_outline(client)
    world.rq.add_version(RQ, 3, diff=[])
    world.rq.mark_pending(RQ, sb["id"], 3)
    r = await client.get(f"/v1/storyboards/{sb['id']}")
    assert r.json()["active_job"]["kind"] == "sb.rq_sync"
    await drain()
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb2["requirement_ref"]["version"] == 3 and world.rq.links[(RQ, sb["id"])]["sync_state"] == "up_to_date"


async def test_new_rq_version_band(client, world, monkeypatch):
    from winmate_storyboard import ops_core
    monkeypatch.setattr(ops_core, "_RQ_CHECK_S", 0)
    sb = await to_outline(client)
    world.rq.add_version(RQ, 3, diff=[])
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb2["rq_update"] == {"version": 3, "note": None}
    # 띠 한 줄 — 지금 쓰는 버전 뒤 저장된 버전들의 변경 수 합 · 최근 저장 메모(통합)
    world.rq.add_version(RQ, 4, diff=[])
    world.rq.version_meta[(RQ, 3)] = {"change_count": 2, "note": "11/11 회의 반영"}
    world.rq.version_meta[(RQ, 4)] = {"change_count": 1, "note": None}
    sb3 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb3["rq_update"] == {"version": 4, "note": "변경 3건 · 11/11 회의 반영"}


async def test_resolution_place(client, world):
    sb = await to_outline(client)
    it = next(i for i in sb["trace"]["items"] if i["code"] == "RQ-11")
    opt = it["question"]["options"][0]
    assert opt["kind"] == "place" and opt["target"]["label"] == "Part 2 중앙관제실"
    r = await client.put(f"/v1/storyboards/{sb['id']}/trace/items/{it['rq_item_id']}/resolution",
                         json={"kind": "place", "option_id": opt["id"]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["item"]["state"] == "resolved" and "direct" in body["item"]["link_types"] and body["apply_job_id"]
    assert body["item"]["resolution"]["result_label"] == "Part 2 중앙관제실 · 로비에 넣음"
    await drain()
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    cr = space_named(sb2, "중앙관제실")
    assert "Digital Twin" in "".join(s["text"] for s in cr["slots"]["exception"]["segments"])
    assert any(c["cause"]["kind"] == "trace" for c in sb2["changes"])
    it2 = next(i for i in sb2["trace"]["items"] if i["code"] == "RQ-11")
    assert it2["places_label"] == "Part 2 로비 · 중앙관제실"
    dt = next(d for d in sb2["outline"]["discussions"] if d["label"] == "Digital Twin · BLE 위치")
    assert dt["state"] == "resolved"
    rq03 = next(i for i in sb2["trace"]["items"] if i["code"] == "RQ-03")
    r = await client.put(f"/v1/storyboards/{sb['id']}/trace/items/{rq03['rq_item_id']}/resolution",
                         json={"kind": "place", "option_id": rq03["question"]["options"][0]["id"]})
    await drain()
    sb3 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    it3 = next(i for i in sb3["trace"]["items"] if i["code"] == "RQ-03")
    assert it3["resolution"]["result_label"] == "Part 3에 '설계 반영 체크리스트' 추가"
    assert any("설계 반영 체크리스트" in ln["text"] for ln in section_key(sb3, "p3_1")["lines"])


async def test_resolution_ask_exclude(client, world):
    sb = await to_outline(client)
    rq07 = next(i for i in sb["trace"]["items"] if i["code"] == "RQ-07")
    r = await client.put(f"/v1/storyboards/{sb['id']}/trace/items/{rq07['rq_item_id']}/resolution", json={"kind": "ask_customer"})
    body = r.json()
    assert r.status_code == 200 and body["item"]["state"] == "resolved" and "unconfirmed" in body["item"]["link_types"]
    assert body["item"]["resolution"]["result_label"] == "고객에게 묻기" and body["apply_job_id"] is None
    post = world.rq.calls_of("POST", "/customer-questions")[-1][2]
    assert post["target"] == {"kind": "item", "id": rq07["rq_item_id"]} and post["origin"]["kind"] == "storyboard"
    rq05 = next(i for i in sb["trace"]["items"] if i["code"] == "RQ-05")
    url = f"/v1/storyboards/{sb['id']}/trace/items/{rq05['rq_item_id']}/resolution"
    r = await client.put(url, json={"kind": "exclude"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "REASON_REQUIRED"
    r = await client.put(url, json={"kind": "exclude", "reason": "본제안 범위 밖"})
    assert r.json()["item"]["state"] == "resolved" and r.json()["item"]["resolution"]["result_label"] == "제외 — 본제안 범위 밖"
    tr = (await client.get(f"/v1/storyboards/{sb['id']}/trace")).json()
    assert len(tr["items"]) == 12
    r = await client.post(f"/v1/storyboards/{sb['id']}/trace/extensions/acknowledge")
    assert r.status_code == 200
    tr = (await client.get(f"/v1/storyboards/{sb['id']}/trace")).json()
    assert tr["extensions_acknowledged"] and all(e["acknowledged"] for e in tr["extensions"])
    assert not world.rq.calls_of("PATCH", "/draft")


async def test_schedule(client, world):
    sb = await to_outline(client)
    sch = (await client.get(f"/v1/storyboards/{sb['id']}/schedule")).json()
    ph = sch["phases"]
    assert [p["name"] for p in ph] == ["리서치 · 리뷰", "스토리보드 공유 · 확정", "DSS 자료 수급", "분담 작성", "취합 · 디자인 · 교정", "검수 · 납품"]
    assert all(p["d_from"] >= p["d_to"] for p in ph) and sum(p["current"] for p in ph) == 1
    assert ph[0]["current"] and ph[0]["badges"] == ["지금"]
    assert ph[1]["badges"] == ["고객 확인 4"] and (ph[0]["d_from"], ph[0]["d_to"]) == (21, 17)
    assert ph[3]["owner"] == "Part 1 영업 기획 · Part 2 솔루션 · Part 3 관계사 협업"
    await client.patch(f"/v1/storyboards/{sb['id']}/settings", json={"volume": 30})
    ph30 = (await client.get(f"/v1/storyboards/{sb['id']}/schedule")).json()["phases"]
    assert (ph30[0]["d_from"], ph30[0]["d_to"]) == (27, 22)
    await client.post(f"/v1/storyboards/{sb['id']}/save", json={})
    ph_s = (await client.get(f"/v1/storyboards/{sb['id']}/schedule")).json()["phases"]
    assert ph_s[1]["current"] and "지금" in ph_s[1]["badges"]


async def test_export_options(client, world):
    sb = await to_outline(client)
    r = await client.post(f"/v1/storyboards/{sb['id']}/exports", json={"format": "pptx", "options": {"internal_memo": False}})
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    await drain()
    sb1 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb1["version"] == 1 and sb1["status"] == "shared" and sb1["sub_line"] == "내보냈어요"
    rec = await jobs().get(job_id)
    assert rec.status == "succeeded" and rec.result["file_id"] and rec.result["name"].endswith(".pptx")
    payload = world.export.payloads[-1]
    text = json.dumps(payload, ensure_ascii=False)
    assert payload["filename"] == "E 자산운용 용산 오피스 제안 기획_스토리보드_v1" and payload["confidential"] is True
    assert "스펙인" not in text and "제작자 의견" not in text and "internal_memos" not in text
    assert "[00]" in text and "[확인 필요]" in text and "TBD" in text
    r = await client.post(f"/v1/storyboards/{sb['id']}/exports", json={"format": "pdf", "options": {"internal_memo": True}})
    await drain()
    payload = world.export.payloads[-1]
    text = json.dumps(payload, ensure_ascii=False)
    assert payload["filename"].endswith("_v1_내부검토") and payload["format"] == "pdf"
    assert "설계 단계 삼성 스펙인" in text and "제작자 의견" in text
    # 작업본이 바뀌면 먼저 저장(버전 +1)
    m = sb1["direction"]["key_messages"][2]
    await client.patch(f"/v1/storyboards/{sb['id']}/key-messages/{m['id']}", json={"text": "공간이 먼저 알아본다."})
    await client.post(f"/v1/storyboards/{sb['id']}/exports", json={"format": "pptx", "options": {}})
    await drain()
    assert (await client.get(f"/v1/storyboards/{sb['id']}")).json()["version"] == 2
    assert world.export.payloads[-1]["filename"].endswith("_v2")


async def test_handoff_and_review(client, world):
    sb = await to_outline(client)
    await client.post(f"/v1/storyboards/{sb['id']}/save", json={})
    cards = (await client.get(f"/v1/storyboards/{sb['id']}/handoffs")).json()["items"]
    assert [c["title"] for c in cards] == ["B2B 제안서", "Market Intelligence", "공간 시나리오"]
    assert cards[0]["description"] == "Part 1 → MI · VP · Part 2 → 공간 시나리오 7장 · Part 3 → Why Samsung"
    assert cards[1]["description"] == "Part 1-1 · 1-2 근거 — 성수 성과 수치의 출처 찾기"
    assert cards[2]["description"] == "Part 2의 7개 공간을 시트로"
    r = await client.post(f"/v1/storyboards/{sb['id']}/handoffs/proposal")
    assert r.status_code == 200 and r.json()["route"].startswith(f"/proposal/new?sb={sb['id']}")
    sb2 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb2["status"] == "shared" and "제안서" in sb2["sub_line"] and sb2["sub_line"] == "제안서로 넘겼어요"
    await client.post(f"/v1/storyboards/{sb['id']}/handoffs/mi")
    sb3 = (await client.get(f"/v1/storyboards/{sb['id']}")).json()
    assert sb3["sub_line"] == "제안서 · MI로 넘겼어요"
    lst = (await client.get("/v1/storyboards", params={"tab": "done"})).json()["items"]
    assert lst[0]["status_label"] == "완료 · 공유됨" and lst[0]["cta"] == "open"
    r = await client.post(f"/v1/storyboards/{sb['id']}/review-requests", json={"note": "검토 부탁드려요"})
    assert r.status_code == 201, r.text
    ph = (await client.get(f"/v1/storyboards/{sb['id']}/proposal-handoff", params={"section": "vp"})).json()
    assert ph["source"]["ref_id"] == sb["id"] and ph["items"][0]["template_hint"]["code"] == "VP-B"
    assert len(ph["key_messages"]) == 3 and ph["customer"]["name"] == "E 자산운용"
    assert any(f["placeholder"] == "[00]" for f in ph["facts"])


async def test_confidential_and_no_websearch(client, world):
    await to_outline(client)
    llm_calls = [b for p, b in world.ai.requests if p == "/v1/llm/chat"]
    assert llm_calls and all(b["confidential"] is True for b in llm_calls)
    assert not [p for p, _ in world.ai.requests if p in ("/v1/websearch", "/v1/search", "/v1/fetch")]
    assert {b["task"] for b in llm_calls} >= {"sb.prepare_settings", "sb.direction" if False else "sb.axes", "sb.trace",
                                              "sb.section.p1_2", "sb.spaces"}


async def test_policy_confidential(client, world, monkeypatch):
    monkeypatch.setenv("MOCK_ENFORCE_CONFIDENTIAL", "true")
    monkeypatch.setenv("LLM_ALLOW_CONFIDENTIAL", "false")
    r = await client.post("/v1/storyboards", json={"requirement_id": RQ})
    job_id = r.json()["prepare_job_id"]
    await drain()
    rec = await jobs().get(job_id)
    assert rec.status == "failed" and rec.error["code"] == "POLICY_CONFIDENTIAL"
    sb = (await client.get(f"/v1/storyboards/{r.json()['id']}")).json()
    assert sb["active_job"] is None and sb["settings"]["ready"] is False


async def test_llm_unavailable(client, world, monkeypatch, tmp_path):
    d = tmp_path / "mocks"
    d.mkdir()
    (d / "sb.prepare_settings.json").write_text(json.dumps({"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE",
                                                                      "message": "장애"}}), encoding="utf-8")
    monkeypatch.setenv("AI_TOOLS_MOCKS_DIR", str(d))
    r = await client.post("/v1/storyboards", json={"requirement_id": RQ})
    await drain()
    rec = await jobs().get(r.json()["prepare_job_id"])
    assert rec.status == "failed" and rec.error["code"] == "LLM_UNAVAILABLE"
    assert rec.error["message"] == "지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요."


async def test_agenda_and_patch_step(client, world):
    sb = await to_outline(client)
    r = await client.post(f"/v1/storyboards/{sb['id']}/discussions/agenda")
    text = r.json()["text"]
    assert text.startswith("E 자산운용 용산 오피스 제안 기획 회의 안건") and "1. Intro 문구 — 관련: Intro · Outro" in text
    r = await client.patch(f"/v1/storyboards/{sb['id']}", json={"step": 4})
    assert r.json()["step"] == 4 and r.json()["sub_line"] == "정리할 요구 4개 · 로봇 · Digital Twin · BLE · 안면인식"
    assert r.json()["route"].endswith("/trace")


async def test_competitor_import(client, world):
    sb = await create(client)
    r = await client.post(f"/v1/storyboards/{sb['id']}/imports/competitor", json={
        "criteria": [{"name": "가격", "importance": "높음"}, {"name": "레퍼런스"}], "competitors": ["경쟁사 A", "경쟁사 B"]})
    q = r.json()["question"]
    opt = next(o for o in q["options"] if o["label"] == "경쟁사 제안")
    assert opt["evidence"] == "비교 기준 가격 · 레퍼런스 (경쟁사 A · 경쟁사 B)" and opt["recommended"] is True
