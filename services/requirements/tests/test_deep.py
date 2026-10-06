"""심층 작성 — 보강할 곳 분석 · 상한 · 세션 하나 · 값/문장 답 · 숫자 가드 · 모름 · 건너뛰기 · 폼에서 해결 · 끝내기(§9.1-11~21, 34)."""
from __future__ import annotations

from rq_testkit import drain
from winmate_common import testing
from winmate_common.ids import new_id

ITEMS = [["사용자를 인식하고 반응하는 'AI Ready' 오피스", "'최초 AI Ready' 공간으로 알리기", "에너지 절감 · 정량 데이터 확보"],
         ["오피스를 업무환경 플랫폼으로", "예측 · 반응형 공간 (Connecting-AI)", "건물 가치 · 임대 선호도 제고"],
         ["AI 인프라를 설계 단계에 미리 반영"]]
NAMES = ["대표이사", "공간컨텐츠실장", "개발사업팀장"]


async def demo(c, *, final_audience: str | None = None, customer: str | None = "E 자산운용"):
    rq = (await c.post("/v1/requirements", json={})).json()
    k = [new_id("km") for _ in NAMES]
    ops = [{"op": "set_field", "field": "project_name", "value": "용산 업무시설 재개발 AI Ready 오피스"},
           {"op": "set_field", "field": "author_note", "value": "설계 단계 스펙인이 목표. 성수 오피스 대비 '최초 AI Ready'를 강조."}]
    if customer:
        ops.append({"op": "set_field", "field": "customer_name", "value": customer})
    if final_audience:
        ops.append({"op": "set_field", "field": "final_audience", "value": final_audience})
    ops += [{"op": "add_keyman", "keyman_id": kid, "name": n} for kid, n in zip(k, NAMES, strict=True)]
    for kid, texts in zip(k, ITEMS, strict=True):
        ops += [{"op": "add_item", "keyman_id": kid, "text": t} for t in texts]
    r = await c.patch(f"/v1/requirements/{rq['id']}/draft", json={"ops": ops})
    assert r.status_code == 200, r.text
    return r.json(), k


async def analyze(c, rq_id):
    r = await c.post(f"/v1/requirements/{rq_id}/deep-sessions")
    assert r.status_code == 202, r.text
    sid = r.json()["ref"]["id"]
    assert r.json()["ref"]["kind"] == "deep_session"
    await drain()
    s = (await c.get(f"/v1/requirements/{rq_id}/deep-sessions/{sid}")).json()
    return s


async def answer(c, rq_id, s, **body):
    gid = body.pop("gap_id", None) or s["current_gap_id"]
    r = await c.post(f"/v1/requirements/{rq_id}/deep-sessions/{s['id']}/answers", json={"gap_id": gid, **body})
    return r


async def run_board_flow(c):
    """보드 흐름: 최종 제안대상 칩 → 가중치 배분안 → 에너지 문장(반영 + 부수 효과) → 개발사업팀장 추가 → 모름."""
    rq, k = await demo(c)
    s = await analyze(c, rq["id"])
    rid = rq["id"]
    st = (await c.post(f"/v1/requirements/{rid}/deep-sessions/{s['id']}/start")).json()
    g1 = next(g for g in st["gaps"] if g["id"] == st["current_gap_id"])
    r = await answer(c, rid, st, kind="option", option_id=g1["question"]["options"][0]["id"])
    st = r.json()["session"]
    g2 = next(g for g in st["gaps"] if g["id"] == st["current_gap_id"])
    r = await answer(c, rid, st, kind="option", option_id=g2["question"]["options"][0]["id"])
    st = r.json()["session"]
    r = await answer(c, rid, st, kind="text", text="유사 건물 대비 20%. 실측 데이터로 보여 주길 원해요")
    p = r.json()["proposal"]
    acc = await c.post(f"/v1/requirements/{rid}/deep-sessions/{s['id']}/proposals/{p['id']}/accept",
                       json={"side_effects": [{"id": se["id"], "checked": True} for se in p["side_effects"]]})
    st = acc.json()["session"]
    r = await answer(c, rid, st, kind="text", text="시공하고 운영할 때 유지보수 부담이 적었으면 해요")
    p = r.json()["proposal"]
    acc = await c.post(f"/v1/requirements/{rid}/deep-sessions/{s['id']}/proposals/{p['id']}/accept", json={})
    st = acc.json()["session"]
    r = await answer(c, rid, st, kind="unknown")
    return rq, k, s["id"], r.json()


async def test_analysis_board(platform, app):
    async with testing.api_client(app) as c:
        rq, k = await demo(c)
        s = await analyze(c, rq["id"])
        assert s["status"] == "ready"
        kinds = [(g["kind"], g["chip_label"]) for g in s["gaps"]]
        assert kinds == [("empty_field", "최종 제안대상"), ("default_weights", "가중치"), ("unquantified", "대표이사"),
                         ("too_few_items", "개발사업팀장"), ("vague_scope", "공간컨텐츠실장")], kinds
        assert [g["problem"] for g in s["gaps"]] == ["비어 있음", "균등 기본값", "'에너지 절감' 목표 수치 없음", "요구사항 1개",
                                                     "'업무환경 플랫폼' 범위 불명확"]
        assert all(len(g["problem"]) <= 24 for g in s["gaps"])
        assert 0 <= s["completeness"] <= 100 and s["completeness_before"] == s["completeness"]
        assert set(s["selected_gap_ids"]) == {g["id"] for g in s["gaps"]}
        q1 = s["gaps"][0]["question"]
        assert q1["text"] == "최종 제안은 누구에게 하나요?" and q1["answer_type"] == "value"
        assert [o["label"] for o in q1["options"]] == ["대표이사", "공간컨텐츠실장", "개발사업팀장"]
        assert s["gaps"][1]["question"]["options"][-1]["label"] == "균등 유지"
        assert s["gaps"][1]["question"]["options"][0]["label"] == "대표이사 50 · 공간컨텐츠실장 30 · 개발사업팀장 20"
        assert s["gaps"][2]["question"]["text"] == "'에너지 절감'의 목표 수치가 있나요?"
        assert s["gaps"][2]["chip_keyman_id"] == k[0]
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert doc["list_state"] == "deepening" and doc["state_label"] == "심층 작성 1 / 5"
        assert doc["route"] == f"/requirements/{rq['id']}/deep/{s['id']}"
        # 세션 하나(§9.1-13)
        r = await c.post(f"/v1/requirements/{rq['id']}/deep-sessions")
        assert r.status_code == 409 and r.json()["error"]["code"] == "SESSION_ACTIVE"
        assert r.json()["error"]["details"]["session_id"] == s["id"]
        # 선택 · 시작
        sel = [g["id"] for g in s["gaps"] if g["kind"] != "too_few_items"]
        p = await c.patch(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}", json={"selected_gap_ids": []})
        assert p.json()["selected_gap_ids"] == []
        none = await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/start")
        assert none.status_code == 422 and none.json()["error"]["code"] == "NOTHING_SELECTED"
        await c.patch(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}", json={"selected_gap_ids": sel})
        st = (await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/start")).json()
        assert st["status"] == "asking" and st["total"] == 4 and st["current_index"] == 1
        assert st["current_gap_id"] == s["gaps"][0]["id"]
        assert any(g["status"] == "deselected" for g in st["gaps"])
    last = platform["workspace"].find("PUT", f"/v1/items/{rq['id']}")[-1]["json"]
    assert last["route"] == f"/requirements/{rq['id']}/deep/{s['id']}/q" and last["status"] == "deepening"


async def test_board_flow_end_to_end(platform, app):
    async with testing.api_client(app) as c:
        rq, k, _sid, last = await run_board_flow(c)
        rid = rq["id"]
        assert last["outcome"] == "deferred"
        cq = last["customer_question"]
        assert cq["status"] == "open" and cq["keyman_id"] == k[1] and cq["target"]["kind"] == "item"
        assert cq["text"] == "'업무환경 플랫폼'에 어떤 서비스가 들어가나요?" and cq["origin"]["kind"] == "deep_unknown"
        s = last["session"]
        assert s["status"] == "finished"  # 마지막 질문 뒤 자동 끝내기
        res = s["result"]
        assert res["reinforced_count"] == 4 and len(res["customer_question_ids"]) == 2
        assert [q["short_label"] for q in res["customer_questions"]] == ["유사 건물 사용량 자료", "'업무환경 플랫폼' 범위"]
        assert s["completeness_after"] >= s["completeness_before"]
        labels = [(ch["label"], ch["before_display"], ch.get("after_short") or ch["after_display"], ch["is_addition"])
                  for ch in res["changes"]]
        assert labels == [("최종 제안대상", None, "대표이사", False), ("가중치", "34 · 33 · 33", "50 · 30 · 20", False),
                          ("대표이사", "에너지 절감 · 정량 데이터 확보", "에너지 사용량 20% 절감 · 실측 증빙", False),
                          ("개발사업팀장", None, "시공 · 운영 유지보수 부담 최소화", True)]
        doc = (await c.get(f"/v1/requirements/{rid}")).json()
        f = doc["form"]
        assert f["final_audience"]["value"] == "대표이사" and f["final_audience"]["source"]["kind"] == "deep"
        assert [x["weight"] for x in f["keymen"]] == [50, 30, 20] and f["weights_mode"] == "custom"
        assert f["keymen"][0]["items"][2]["text"] == "에너지 사용량 20% 절감 (유사 건물 대비) · 실측 데이터로 증빙"
        assert f["keymen"][2]["items"][1]["text"] == "시공 · 운영 단계 유지보수 부담 최소화"
        assert f["keymen"][1]["items"][0]["needs_confirmation"] is True
        assert doc["open_question_count"] == 2 and doc["list_state"] == "input" and doc["active_deep_session_id"] is None
        sv = await c.post(f"/v1/requirements/{rid}/save", json={"reason": "deep"})
        assert sv.status_code == 201 and sv.json()["version"] == 1
        v1 = (await c.get(f"/v1/requirements/{rid}/versions/1")).json()
        assert v1["reason"] == "deep" and v1["open_question_count"] == 2
        flat = {i["text"]: i for i in v1["snapshot"]["items_flat"]}
        assert flat["오피스를 업무환경 플랫폼으로"]["needs_confirmation"] is True
        assert flat["시공 · 운영 단계 유지보수 부담 최소화"]["code"] == "RQ-08"
    puts = platform["workspace"].find("PUT", f"/v1/items/{rid}")
    assert puts[-1]["json"]["route"] == f"/requirements/{rid}"
    chats = platform["ai-tools"].find("POST", "/v1/llm/chat")
    assert chats and all(x["json"]["confidential"] is True for x in chats)


async def test_value_answer_and_pending(platform, app):
    async with testing.api_client(app) as c:
        rq, k = await demo(c)
        s = await analyze(c, rq["id"])
        st = (await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/start")).json()
        before = (await c.get(f"/v1/requirements/{rq['id']}")).json()["revision"]
        r = await answer(c, rq["id"], st, kind="option", option_id=st["gaps"][0]["question"]["options"][0]["id"])
        body = r.json()
        assert r.status_code == 200 and body["outcome"] == "applied"
        assert body["log_entry"] == {"gap_id": st["gaps"][0]["id"], "kind": "applied", "label": "최종 제안대상", "value_display": "대표이사"}
        assert body["session"]["current_index"] == 2 and body["requirement_revision"] > before
        # 지금 질문이 아닌 곳에 답하면 409
        wrong = await answer(c, rq["id"], body["session"], gap_id=st["gaps"][3]["id"], kind="skip")
        assert wrong.status_code == 409 and wrong.json()["error"]["code"] == "GAP_NOT_CURRENT"
        # 가중치 — 직접 조정
        st = body["session"]
        r = await answer(c, rq["id"], st, kind="weights", weights={k[0]: 40, k[1]: 40, k[2]: 20})
        assert r.json()["log_entry"]["value_display"] == "40 · 40 · 20"
        st = r.json()["session"]
        # 문장 답 → 제안, 작업본은 그대로
        rev = (await c.get(f"/v1/requirements/{rq['id']}")).json()["revision"]
        r = await answer(c, rq["id"], st, kind="text", text="유사 건물 대비 20%. 실측 데이터로 보여 주길 원해요")
        p = r.json()["proposal"]
        assert r.json()["outcome"] == "proposal" and p["before_text"] == "에너지 절감 · 정량 데이터 확보"
        assert p["kind"] == "replace_item" and p["side_effects"][0]["label"] == "유사 건물 사용량 자료"
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert doc["revision"] == rev and doc["form"]["keymen"][0]["items"][2]["text"] == "에너지 절감 · 정량 데이터 확보"
        st = r.json()["session"]
        nxt = next(g for g in st["gaps"] if g["status"] == "pending")
        pend = await answer(c, rq["id"], st, gap_id=nxt["id"], kind="skip")
        assert pend.status_code == 409 and pend.json()["error"]["code"] == "PROPOSAL_PENDING"
        # 고치기(edited_text) 로 반영, 부수 효과 해제
        acc = await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/proposals/{p['id']}/accept",
                           json={"edited_text": "에너지 사용량 20% 절감 · 실측 증빙", "side_effects": [{"id": p["side_effects"][0]["id"], "checked": False}]})
        assert acc.status_code == 200 and acc.json()["created_question_ids"] == []
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert doc["form"]["keymen"][0]["items"][2]["text"] == "에너지 사용량 20% 절감 · 실측 증빙"
        # 건너뛰기는 작업본 revision 을 바꾸지 않는다(§9.1-19)
        st = acc.json()["session"]
        rev = doc["revision"]
        r = await answer(c, rq["id"], st, kind="skip")
        assert r.json()["outcome"] == "skipped" and r.json()["requirement_revision"] == rev
        g = next(g for g in r.json()["session"]["gaps"] if g["id"] == st["current_gap_id"])
        assert g["status"] == "skipped"
        # 끝내기
        fin = (await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/finish")).json()
        assert fin["status"] == "finished" and fin["result"]["reinforced_count"] == 3
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert doc["active_deep_session_id"] is None and doc["last_deep_session_id"] == s["id"]


async def test_unknown_on_item(platform, app):
    async with testing.api_client(app) as c:
        rq, k = await demo(c, final_audience="대표이사")
        s = await analyze(c, rq["id"])
        vague = next(g for g in s["gaps"] if g["kind"] == "vague_scope")
        await c.patch(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}", json={"selected_gap_ids": [vague["id"]]})
        st = (await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/start")).json()
        before = (await c.get(f"/v1/requirements/{rq['id']}")).json()["open_question_count"]
        r = await answer(c, rq["id"], st, kind="unknown")
        body = r.json()
        assert body["outcome"] == "deferred"
        q = body["customer_question"]
        item_id = vague["target"]["item_id"]
        assert q["status"] == "open" and q["keyman_id"] == k[1] and q["target"] == {"kind": "item", "id": item_id}
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert doc["open_question_count"] == before + 1
        assert next(i for kk in doc["form"]["keymen"] for i in kk["items"] if i["id"] == item_id)["needs_confirmation"] is True


async def test_resolved_by_form(platform, app):
    async with testing.api_client(app) as c:
        rq, _ = await demo(c, customer=None)
        s = await analyze(c, rq["id"])
        cust = next(g for g in s["gaps"] if g["kind"] == "empty_field" and g["target"]["field"] == "customer_name")
        st = (await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/start")).json()
        assert st["current_gap_id"] != cust["id"]
        await c.patch(f"/v1/requirements/{rq['id']}/draft",
                      json={"ops": [{"op": "set_field", "field": "customer_name", "value": "E 자산운용"}]})
        got = (await c.get(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}")).json()
        assert next(g for g in got["gaps"] if g["id"] == cust["id"])["status"] == "resolved_by_form"


async def test_cap_numeric_guard_and_errors(ai, app):
    async with testing.api_client(app) as c:
        rq, _k = await demo(c, final_audience="대표이사")
        # LLM 이 보강할 곳 12개 → 7개 이하(§9.1-12)
        targets = [(NAMES[i], t) for i, texts in enumerate(ITEMS) for t in texts]
        ai.overrides["rq.gaps"] = {"json": {"gaps": [
            {"target": {"kind": "item", "keyman_name": n, "item_text": t}, "kind": "ambiguous", "problem": f"문제 {j}", "impact": 2}
            for j, (n, t) in enumerate(targets)] + [
            {"target": {"kind": "keyman", "keyman_name": n}, "kind": "missing_perspective", "problem": "관점 빠짐", "impact": 1}
            for n in NAMES] + [{"target": {"kind": "item", "keyman_name": "대표이사", "item_text": "없는 항목"}, "kind": "conflict",
                                "problem": "x", "impact": 3}, {"target": {"kind": "item", "keyman_name": "대표이사",
                                "item_text": ITEMS[0][0]}, "kind": "unquantified", "problem": "중복", "impact": 1}]}}
        s = await analyze(c, rq["id"])
        assert len(s["gaps"]) <= 7
        items = [g["target"].get("item_id") for g in s["gaps"] if g["target"]["kind"] == "item"]
        assert len(items) == len(set(items))
        await c.delete(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}")
        # 숫자 가드(§9.1-17): 답에 없는 30% 를 넣은 재작성
        ai.overrides["rq.gaps"] = None
        ai.overrides["rq.rewrite_item"] = {"json": {"kind": "replace_item", "after_text": "에너지 사용량 30% 절감 · 실측 데이터로 증빙",
                                                    "after_short": "에너지 30% 절감", "side_effects": []}}
        s = await analyze(c, rq["id"])
        energy = next(g for g in s["gaps"] if g["kind"] == "unquantified")
        await c.patch(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}", json={"selected_gap_ids": [energy["id"]]})
        st = (await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/start")).json()
        r = await answer(c, rq["id"], st, kind="text", text="실측 데이터로 절감 효과를 보여 주면 좋겠어요")
        p = r.json()["proposal"]
        assert "30" not in p["after_text"] and "30" not in (p["after_short"] or "")
        assert "절감" in p["after_text"]
        assert ai.tasks().count("rq.rewrite_item") == 2  # 1회 재시도
        await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/proposals/{p['id']}/revise", json={"instruction": "더 짧게"})
        # 모델 사용 불가 → 503 LLM_UNAVAILABLE · 403 POLICY_CONFIDENTIAL(한국어)
        ai.overrides["rq.rewrite_item"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "장애"}}
        await c.delete(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}")
        s = await analyze(c, rq["id"])
        energy = next(g for g in s["gaps"] if g["kind"] == "unquantified")
        await c.patch(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}", json={"selected_gap_ids": [energy["id"]]})
        st = (await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/start")).json()
        r = await answer(c, rq["id"], st, kind="text", text="20% 정도")
        assert r.status_code == 503 and r.json()["error"]["code"] == "LLM_UNAVAILABLE"
        assert r.json()["error"]["message"] == "지금은 AI를 쓸 수 없어요. 직접 입력은 계속할 수 있어요."
        ai.overrides["rq.rewrite_item"] = {"error": {"status": 403, "code": "POLICY_CONFIDENTIAL", "message": "기밀"}}
        r = await answer(c, rq["id"], st, kind="text", text="20% 정도")
        assert r.status_code == 403 and r.json()["error"]["code"] == "POLICY_CONFIDENTIAL"
        # 모름은 LLM 없이도 템플릿으로
        ai.overrides["rq.customer_question"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "장애"}}
        r = await answer(c, rq["id"], st, kind="unknown")
        assert r.json()["customer_question"]["text"] == "'에너지 절감'의 목표 수치가 있을까요?"


async def test_analysis_without_llm(ai, app):
    async with testing.api_client(app) as c:
        rq, _ = await demo(c)
        ai.overrides["rq.gaps"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "장애"}}
        ai.overrides["rq.questions"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "장애"}}
        s = await analyze(c, rq["id"])
        assert s["status"] == "ready"
        assert [g["kind"] for g in s["gaps"]] == ["empty_field", "default_weights", "too_few_items"]
        assert s["gaps"][1]["question"]["options"][-1]["label"] == "균등 유지"


async def test_empty_form_interview(platform, app):
    async with testing.api_client(app) as c:
        rq = (await c.post("/v1/requirements", json={})).json()
        s = await analyze(c, rq["id"])
        assert [g["kind"] for g in s["gaps"]] == ["empty_field", "empty_field", "empty_field", "no_keyman"]
        st = (await c.post(f"/v1/requirements/{rq['id']}/deep-sessions/{s['id']}/start")).json()
        for v in ("대표이사", "E 자산운용", "용산 오피스"):
            st = (await answer(c, rq["id"], st, kind="text", text=v)).json()["session"]
        r = await answer(c, rq["id"], st, kind="text", text="대표이사")
        assert r.json()["outcome"] == "applied" and r.json()["session"]["status"] == "finished"
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert doc["form"]["keymen"][0]["name"] == "대표이사" and doc["title"] == "E 자산운용 용산 오피스"
