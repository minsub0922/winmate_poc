"""API 표면 — 참조 데이터 · 작업 CRUD · 오류 형식 · 결과 다듬기 엔드포인트(05-vp.md §5)."""
from __future__ import annotations

from vp_helpers import RFP_TEXT, ready_vp, run_jobs, upload


def err_code(r) -> str:
    return r.json()["error"]["code"]


async def test_reference_endpoints(client):
    rules = (await client.get("/v1/routing-rules")).json()
    assert rules["title"] == "구조와 레이아웃은 스스로 고르고, 다섯 경우만 묻습니다"
    assert [x["mode"] for x in rules["legend"]] == ["auto", "check", "ask", "pin"]
    assert [s["title"] for s in rules["stages"]] == ["재료 판별", "업종 · 업종판", "메시지 구조", "시트 수"]
    assert len(rules["band"]) == 5 and len(rules["asks"]) == 5 and len(rules["gaps"]) == 4
    assert rules["packs"]["total"] == 16 and len(rules["packs"]["cells"]) == 16

    sc = (await client.get("/v1/routing-rules/scenarios")).json()
    assert [r["no"] for r in sc["rows"]] == list(range(1, 13))
    assert [s["n"] for s in sc["stats"]] == ["5/12", "2/12", "17종", "0/16"]

    lay = (await client.get("/v1/layouts")).json()
    codes = {i["code"] for i in lay["items"]}
    assert {"CH-A", "CH-B", "VP-F3", "VP-G", "VP-H", "EF-A", "EF-B", "EF-C"} <= codes
    assert lay["counts"]["업종판"] == len([i for i in lay["items"] if i["industry_code"]])

    packs = (await client.get("/v1/industry-packs")).json()
    assert packs["total"] == 16 and packs["ready"] == 0
    assert packs["items"][0]["name"] == "외식 · 카페"
    assert packs["banner"] == "Value Props 업종 레이아웃 16종은 제작 중이에요."


async def test_work_crud_versions_clone_archive_and_errors(client):
    r = await client.get("/v1/vps/vp_nope")
    assert r.status_code == 404 and err_code(r) == "NOT_FOUND"
    assert "찾을 수 없" in r.json()["error"]["message"]

    r = await client.post("/v1/vps", json={"start": "bogus"})
    assert r.status_code == 422

    r = await client.post("/v1/vps", json={"start": "direct"})
    assert r.status_code == 201
    empty = r.json()
    assert empty["title"] == "새 가치 제안"
    r = await client.post(f"/v1/vps/{empty['id']}/materials:collect", json={})
    assert r.status_code == 422 and err_code(r) == "NOTHING_TO_COLLECT"

    vid = await ready_vp(client)
    doc = (await client.get(f"/v1/vps/{vid}")).json()

    r = await client.patch(f"/v1/vps/{vid}", json={"title": "A 커피 메뉴보드 가치 제안"})
    assert r.status_code == 200 and r.json()["title"] == "A 커피 메뉴보드 가치 제안"

    r = await client.post(f"/v1/vps/{vid}/versions", json={"reason": "검토 전"})
    assert r.status_code == 201
    vers = (await client.get(f"/v1/vps/{vid}/versions")).json()["items"]
    assert vers[0]["reason"] == "검토 전" or any(v["reason"] == "검토 전" for v in vers)
    first = min(v["version"] for v in vers)
    r = await client.post(f"/v1/vps/{vid}/versions/{first}/restore")
    assert r.status_code == 200
    restored = r.json()
    assert restored["generated"] is False  # 첫 저장 지점은 '재료 완료' — 생성 전으로 돌아간다
    r = await client.post(f"/v1/vps/{vid}/versions/999/restore")
    assert r.status_code == 404

    # 다시 생성해 두고 복제
    r = await client.post(f"/v1/vps/{vid}/generate", json={})
    assert r.status_code == 202
    r2 = await client.post(f"/v1/vps/{vid}/generate", json={})
    assert r2.status_code == 409 and err_code(r2) == "JOB_RUNNING"
    await run_jobs()

    vp_sheet = next(s for s in (await client.get(f"/v1/vps/{vid}")).json()["sheets"] if s["role"] == "VP")
    r = await client.post(f"/v1/vps/{vid}/sheets/{vp_sheet['id']}/layout", json={"pin": True})
    assert r.status_code == 200, r.text
    r = await client.post(f"/v1/vps/{vid}:clone", json={"customer_name": "K 베이커리"})
    assert r.status_code == 201, r.text
    clone = r.json()
    assert clone["customer_name"] == "K 베이커리" and clone["id"] != vid
    assert clone["resume_route"] == f"/vp/{clone['id']}/structure"
    assert clone["industry"]["code"] == doc["industry"]["code"]
    pinned = next(s for s in clone["plan"]["sheets"] if s["role"] == "VP")
    assert pinned["mode"] == "pin" and pinned["chip"].endswith("고정"), pinned

    r = await client.post(f"/v1/vps/{clone['id']}:archive")
    assert r.status_code == 204
    ids = [i["id"] for i in (await client.get("/v1/vps")).json()["items"]]
    assert clone["id"] not in ids and vid in ids


async def test_materials_endpoints(client):
    r = await client.post("/v1/vps", json={"start": "direct", "customer_name": "A 커피 프랜차이즈"})
    vid = r.json()["id"]
    fid = await upload("A커피_RFP.txt", RFP_TEXT)
    att = (await client.post(f"/v1/vps/{vid}/attachments", json={"file_id": fid})).json()
    other = await upload("메모.txt", "아무 내용")
    att2 = (await client.post(f"/v1/vps/{vid}/attachments", json={"file_id": other, "kind": "other"})).json()
    r = await client.delete(f"/v1/vps/{vid}/attachments/{att2['id']}")
    assert r.status_code == 204
    r = await client.delete(f"/v1/vps/{vid}/attachments/{att2['id']}")
    assert r.status_code == 404
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert [a["id"] for a in doc["attachments"]] == [att["id"]]

    cands = (await client.get(f"/v1/vps/{vid}/source-candidates")).json()
    assert "found_label" in cands

    await client.post(f"/v1/vps/{vid}/materials:collect", json={})
    await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["materials_ready"]
    # RFP 문장은 칩 길이로 줄여 쓰고, 원문 사실만 쓴다
    chs = [m["text"] for m in doc["materials"] if m["axis"] == "challenge" and not m["excluded"]]
    assert "인쇄 · 배송 비용 부담" in chs, chs
    assert any(m["approver"] for m in doc["materials"] if m["axis"] == "stakeholder")
    # 근거 수치에서 규모(매장 320곳)는 지표가 아니다
    assert not any("320" in (m.get("label") or "") for m in doc.get("metrics_preview") or [])

    for fx in doc["fixes"]:
        r = await client.post(f"/v1/vps/{vid}/fixes/{fx['id']}:decide", json={"decision": "revert"})
        assert r.status_code == 200
        assert next(f for f in r.json()["fixes"] if f["id"] == fx["id"])["decision"] == "revert"
    r = await client.post(f"/v1/vps/{vid}/fixes/vfx_nope:decide", json={"decision": "accept"})
    assert r.status_code == 404

    plan = (await client.post(f"/v1/vps/{vid}/plan:refresh")).json()
    assert plan["sheets"] and plan["flow_label"]
    # 견적 없이 EF-B 로 바꾸면 견적을 먼저 달라고 한다
    r = await client.patch(f"/v1/vps/{vid}/plan", json={"override": {"EF": "EF-B"}})
    assert r.status_code == 409 and err_code(r) == "PREREQUISITE_MISSING"
    r = await client.patch(f"/v1/vps/{vid}/plan", json={"override": {"VP": "VP-G"}})
    assert r.status_code == 200
    assert next(s for s in r.json()["sheets"] if s["role"] == "VP")["layout"]["code"] == "VP-G"
    r = await client.patch(f"/v1/vps/{vid}/plan", json={"override": {"clear": True}})
    assert next(s for s in r.json()["sheets"] if s["role"] == "VP")["layout"]["code"] != "VP-G"


async def test_result_refinement_endpoints(client):
    vid = await ready_vp(client)
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    sheets = {s["role"]: s for s in doc["sheets"] if s["kind"] == "main"}

    # 시트 직접 고치기
    r = await client.patch(f"/v1/vps/{vid}/sheets/{sheets['VP']['id']}", json={"title": "A 커피가 얻는 세 가지 가치", "speaker_notes": "발표 메모"})
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "A 커피가 얻는 세 가지 가치"

    # 레이아웃 후보 · 직접 바꾸기(이미지 없이 쌍둥이)
    lo = (await client.get(f"/v1/vps/{vid}/sheets/{sheets['VP']['id']}/layout-options", params={"pillars": 3})).json()
    twin = next(c for c in lo["candidates"] if c["code"].startswith("VP-B"))
    r = await client.post(f"/v1/vps/{vid}/sheets/{sheets['VP']['id']}/layout", json={"layout_code": twin["code"], "pin": False})
    assert r.status_code in (200, 202), r.text
    if r.status_code == 202:
        await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert next(s for s in doc["sheets"] if s["id"] == sheets["VP"]["id"])["layout"]["code"] == twin["code"]

    # 수치 보강
    ef = sheets["EF"]
    mv = (await client.get(f"/v1/vps/{vid}/sheets/{ef['id']}/metrics")).json()
    assert mv["rule"]["text"] and mv["counts"]["total"] == len(mv["metrics"])
    draft = (await client.get(f"/v1/vps/{vid}/data-request-draft", params={"sheet": ef["id"]})).json()
    assert draft["text"].endswith("바꿔 드리겠습니다.") and draft["mailto"].startswith("mailto:")
    if mv["metrics"]:
        m0 = mv["metrics"][0]
        r = await client.patch(f"/v1/vps/{vid}/metrics/{m0['id']}", json={"handling": "exclude"})
        assert r.status_code == 200, r.text
        assert next(m for m in r.json()["metrics"] if m["id"] == m0["id"])["handling"] == "exclude"
    r = await client.post(f"/v1/vps/{vid}/sheets/{ef['id']}/metrics:apply")
    assert r.status_code in (200, 202), r.text
    if r.status_code == 202:
        await run_jobs()

    # 이미지 칸 · 후보 · 바꾸기 · 일러스트로 통일
    slots = (await client.get(f"/v1/vps/{vid}/image-slots")).json()
    assert slots["items"] and slots["intro"].startswith("이미지 칸")
    s0 = slots["items"][0]
    cands = (await client.get(f"/v1/vps/{vid}/image-slots/{s0['id']}/candidates")).json()
    kb = next((c for c in cands["items"] if c.get("asset") and c["asset"]["source"] == "kb" and not c["current"]), None)
    if kb:
        r = await client.put(f"/v1/vps/{vid}/image-slots/{s0['id']}", json={"asset": kb["asset"]})
        assert r.status_code == 200, r.text
        assert r.json()["mode"] == "pin"
    r = await client.post(f"/v1/vps/{vid}/images:restyle", json={"style": "illustration"})
    assert r.status_code == 202
    await run_jobs()
    slots = (await client.get(f"/v1/vps/{vid}/image-slots")).json()
    main_slots = [s for s in slots["items"] if not s["code"].startswith("추가 제안")]
    assert main_slots and all(s["tier"] == "illust" for s in main_slots), slots["items"]

    # 결과 활용 — 유형별 묶음 · 메시지 복사
    pk = (await client.get(f"/v1/vps/{vid}/packages", params={"selected": "quickwin"})).json()
    assert pk["selected"] == "quickwin"
    q = next(t for t in pk["types"] if t["proposal_type"] == "quickwin")
    assert q["rows"][0]["code"] in ("VP-G", "VP-C")
    one = (await client.get(f"/v1/vps/{vid}/package", params={"proposal_type": "solution"})).json()
    assert one["proposal_type"] == "solution"
    text = (await client.get(f"/v1/vps/{vid}/copy-text")).json()["text"]
    assert "A 커피" in text


async def test_export_and_handoff_contract(client):
    vid = await ready_vp(client)
    r = await client.post(f"/v1/vps/{vid}/exports", json={"format": "pptx"})
    assert r.status_code == 202, r.text
    vex = r.json()["ref"]["id"]
    await run_jobs()
    ex = (await client.get(f"/v1/vps/{vid}/exports/{vex}")).json()
    assert ex["status"] == "done", ex
    assert ex["file_id"] and ex["filename"].endswith(".pptx")

    r = await client.post(f"/v1/vps/{vid}/handoffs", json={"proposal_id": "prp_test", "proposal_type": "standard",
                                                           "proposal_title": "A 커피 메뉴보드 제안"})
    assert r.status_code == 201, r.text
    ho = r.json()
    assert ho["open_route"].startswith("/proposal/prp_test")
    r = await client.post(f"/v1/handoffs/{ho['id']}:ack", json={"result": "applied", "applied_sheet_ids": ["x"],
                                                                 "proposal_id": "prp_test", "proposal_title": "A 커피 메뉴보드 제안"})
    assert r.status_code == 200, r.text
    got = (await client.get(f"/v1/handoffs/{ho['id']}")).json()
    assert got["status"] == "applied"
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert doc["linked_proposal"]["id"] == "prp_test"
    lst = (await client.get("/v1/vps")).json()
    row = next(i for i in lst["items"] if i["id"] == vid)
    assert row["linked_proposal"]["title"] == "A 커피 메뉴보드 제안"

    # 제안서를 지우면 proposal 이 「연결된 제안서」를 거둔다(통합) — 다른 제안서 연결은 그대로, 한 번 더 불러도 그대로
    r = await client.post(f"/v1/vps/{vid}:release-proposal", json={"proposal_id": "prp_other"})
    assert r.status_code == 200 and r.json()["released"] is False and r.json()["linked_proposal"]["id"] == "prp_test"
    r = await client.post(f"/v1/vps/{vid}:release-proposal", json={"proposal_id": "prp_test"})
    assert r.status_code == 200, r.text
    assert r.json()["released"] is True and r.json()["linked_proposal"] is None
    assert (await client.get(f"/v1/vps/{vid}")).json()["linked_proposal"] is None
    assert next(i for i in (await client.get("/v1/vps")).json()["items"] if i["id"] == vid)["linked_proposal"] is None

    r = await client.get("/v1/handoffs/vho_nope")
    assert r.status_code == 404

    # proposal 이 부르는 V2 초안 — 작업 없이 재료 → 생성까지
    r = await client.post("/v1/value-props:draft", json={"customer_name": "D 리테일", "proposal_type": "standard",
                                                         "sheet_roles": ["VP"], "proposal_title": "D 리테일 플래그십"})
    assert r.status_code == 202, r.text
    did = r.json()["value_prop_id"]
    await run_jobs()
    d = (await client.get(f"/v1/vps/{did}")).json()
    assert d["generated"] is True, d.get("last_error")
    ph = (await client.get(f"/v1/vps/{did}/proposal-handoff", params={"type": "standard"})).json()
    assert ph["items"] and ph["source"]["feature"] == "VP"


async def test_industry_pack_release_offers_swap(client):
    vid = await ready_vp(client)
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    code = doc["industry"]["code"]
    if code == "GEN":
        r = await client.patch(f"/v1/vps/{vid}", json={"industry": {"code": "FB"}})
        assert r.status_code == 200
        r = await client.post(f"/v1/vps/{vid}/generate", json={"retry": False})
        await run_jobs()
        code = "FB"
    r = await client.post(f"/v1/industry-packs/{code}:release")
    assert r.status_code == 202, r.text
    await run_jobs()
    packs = (await client.get("/v1/industry-packs")).json()
    assert packs["ready"] == 1
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    offers = [o for o in doc["pack_offers"] if o["status"] == "open"]
    assert offers, doc["pack_offers"]
    assert any(c["tag"] == "알림" for c in doc["checks"])
    r = await client.post(f"/v1/vps/{vid}/pack-offers/{offers[0]['id']}:decide", json={"decision": "apply"})
    assert r.status_code in (200, 202), r.text
    if r.status_code == 202:
        await run_jobs()
    doc = (await client.get(f"/v1/vps/{vid}")).json()
    assert any(s["layout"]["code"].startswith("VP-") and s["layout"].get("industry_code") for s in doc["sheets"]) or \
        any("FB" in s["layout"]["code"] for s in doc["sheets"]), [s["layout"] for s in doc["sheets"]]
