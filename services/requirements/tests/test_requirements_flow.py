"""새 콘텐츠 흐름(/v1/rq-flows · 보드 webapp1 RQ1 · RQ1_AI · RQ_Done) — 폼 · AI 심층 질의 · 파일 첨부 · 저장 → Storyboard 허브(stages.rq)."""
from __future__ import annotations

import pytest
from rq_testkit import AiStub, Recorder, drain, upload
from winmate_common import testing

K_MEMO = """K 리츠 미팅 회의록 — 성수 플래그십 리테일 리뉴얼
참석: 자산관리팀장, 마케팅 리드
- 자산관리팀장: 1층 파사드 미디어로 집객, 테넌트별 콘텐츠 운영, 시설 원격 관리
- 마케팅 리드: 시즌 캠페인 빠른 교체, 방문객 데이터 활용
"""

BOARD_FORM = {
    "title": "성수 플래그십 리테일 리뉴얼", "customer": "K 리츠", "target": "", "note": "설계 단계 스펙인이 목표",
    "keymen": [
        {"role": "자산관리팀장", "weight": 60, "reqs": [{"text": "1층 파사드 미디어로 집객"}, {"text": "테넌트별 콘텐츠 운영"}, {"text": "시설 원격 관리"}]},
        {"role": "마케팅 리드", "weight": 40, "reqs": [{"text": "시즌 캠페인 빠른 교체"}, {"text": "방문객 데이터 활용", "flag": "vague"}]},
    ],
}


@pytest.fixture
def hub(env):
    """ai-tools 대역 + 플랫폼 실제 앱 + storyboard 실제 앱(허브)."""
    stub = AiStub()
    apps = testing.platform_apps("kb", "files", "jobs", "workspace", "export")
    rec = {name: Recorder(app, name) for name, app in apps.items()}
    rec["ai-tools"] = Recorder(stub.app, "ai-tools")
    rec["storyboard"] = Recorder(testing.load_service_app("storyboard"), "storyboard")
    with testing.inprocess(rec):
        stub.rec = rec  # type: ignore[attr-defined]
        yield stub


async def _new(c, **form):
    r = await c.post("/v1/rq-flows", json=form or None)
    assert r.status_code == 201, r.text
    return r.json()


async def _put(c, d, body):
    r = await c.put(f"/v1/rq-flows/{d['id']}", json={**body, "expected_version": d["version"]})
    assert r.status_code == 200, r.text
    return r.json()


async def test_create_edit_conflict_and_list(hub, app):
    async with testing.api_client(app) as c:
        d = await _new(c)
        assert d["code"].startswith("RQ-") and d["status"] == "draft" and d["ver"] == 0 and d["sb_ids"] == []
        assert len(d["keymen"]) == 1 and d["keymen"][0]["weight"] == 100 and d["keymen"][0]["role"] == ""
        d2 = await _put(c, d, BOARD_FORM)
        assert [k["role"] for k in d2["keymen"]] == ["자산관리팀장", "마케팅 리드"]
        vague = d2["keymen"][1]["reqs"][1]
        assert vague["flag"] == "vague" and vague["status"] == "check" and vague["by"] == "manual"
        assert d2["counts"] == {"keymen": 2, "reqs": 5, "check": 1, "weight_sum": 100, "pending": 0}
        # 같은 id 로 보내면 요구 id 가 유지되고, 문장을 고치면 manual
        km = d2["keymen"][0]
        body = {**BOARD_FORM, "keymen": [{**km, "reqs": [{**km["reqs"][0], "text": "1층 파사드 미디어로 집객 · 야간 포함"}]}]}
        d3 = await _put(c, d2, body)
        assert d3["keymen"][0]["reqs"][0]["id"] == km["reqs"][0]["id"] and len(d3["keymen"]) == 1
        # 옛 버전으로 고치면 409
        r = await c.put(f"/v1/rq-flows/{d['id']}", json={**BOARD_FORM, "expected_version": d["version"]})
        assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_CONFLICT"
        # 코드로도 읽힌다(허브 라우트가 ref 로 올 때)
        assert (await c.get(f"/v1/rq-flows/{d['code']}")).json()["id"] == d["id"]
        lst = (await c.get("/v1/rq-flows")).json()
        assert lst["items"][0]["id"] == d["id"] and lst["items"][0]["title"] == "K 리츠 · 성수 플래그십 리테일 리뉴얼"
        # 두 번째는 다음 번호
        e = await _new(c, customer="F 시행사")
        assert int(e["code"][3:]) == int(d["code"][3:]) + 1
        # workspace 색인
        ws = hub.rec["workspace"].find("PUT", f"/v1/items/{d['id']}")
        assert ws and ws[-1]["json"]["route"] == f"/requirements/flow/{d['id']}" and ws[-1]["json"]["feature"] == "RQ"


async def test_deep_questions_apply_and_ask(hub, app):
    async with testing.api_client(app) as c:
        d = await _put(c, await _new(c), BOARD_FORM)
        r = await c.post(f"/v1/rq-flows/{d['id']}/deep-questions")
        assert r.status_code == 200, r.text
        out = r.json()
        assert out["mode"] == "llm" and out["found"] == 3
        qs = out["doc"]["deep"]["questions"]
        assert [q["tag"] for q in qs] == ["최종 제안대상", "마케팅 리드 · 요구 2", "가중치"]
        assert all(q["status"] == "pending" and q["by"] == "ai-pending" for q in qs)
        assert [o["label"] for o in qs[0]["options"]] == ["대표이사", "자산관리본부장", "투자심의위원회"]
        assert qs[1]["text"] == "‘방문객 데이터 활용’은 어디까지인가요?"
        assert [o["label"] for o in qs[2]["options"]] == ["맞아요 · 60 : 40", "50 : 50", "70 : 30"]
        assert out["doc"]["deep"]["current"] == 0 and out["doc"]["counts"]["pending"] == 3
        # 제작자 의견(내부)은 모델에 가지 않는다 · 기밀 표시
        call = next(x for x in hub.calls if x.get("task") == "rq.deep_questions.v1")
        assert "설계 단계" not in str(call) and call.get("confidential") is True
        # 1) 보기 고르기 → 폼에 반영(ai-accepted)
        doc = (await c.post(f"/v1/rq-flows/{d['id']}/deep-questions/{qs[0]['id']}:answer", json={"option": 1})).json()
        assert doc["target"] == "자산관리본부장" and doc["target_by"] == "ai-accepted" and doc["deep"]["current"] == 1
        # 2) 고객에게 확인으로 남기기 → 요구는 확인 필요(ask)
        doc = (await c.post(f"/v1/rq-flows/{d['id']}/deep-questions/{qs[1]['id']}:answer", json={"later": True})).json()
        req = doc["keymen"][1]["reqs"][1]
        assert req["flag"] == "ask" and req["status"] == "check" and doc["deep"]["asked"] == 1
        # 3) 가중치 직접 입력(합이 100 이 아니면 422) → 50 : 50
        r = await c.post(f"/v1/rq-flows/{d['id']}/deep-questions/{qs[2]['id']}:answer", json={"text": "50 : 40"})
        assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_WEIGHTS"
        doc = (await c.post(f"/v1/rq-flows/{d['id']}/deep-questions/{qs[2]['id']}:answer", json={"option": 1})).json()
        assert [k["weight"] for k in doc["keymen"]] == [50, 50] and doc["keymen"][0]["weight_by"] == "ai-accepted"
        assert doc["deep"]["current"] is None and doc["deep"]["applied"] == 2 and doc["counts"]["pending"] == 0
        r = await c.post(f"/v1/rq-flows/{d['id']}/deep-questions/{qs[2]['id']}:answer", json={"option": 0})
        assert r.status_code == 409
        # 요구 질문에 답하면 문장 뒤에 범위가 붙고 확인 필요가 풀린다
        hub.overrides["rq.deep_questions.v1"] = {"json": {"questions": []}}
        d2 = (await c.get(f"/v1/rq-flows/{d['id']}")).json()
        km = d2["keymen"]
        body = {**BOARD_FORM, "target": "자산관리본부장", "keymen": [km[0], {**km[1], "reqs": [{**km[1]["reqs"][1], "flag": "vague", "status": "check"}]}]}
        d3 = await _put(c, d2, body)
        out = (await c.post(f"/v1/rq-flows/{d['id']}/deep-questions")).json()
        assert out["mode"] == "rule" and [q["tag"] for q in out["doc"]["deep"]["questions"]] == ["마케팅 리드 · 요구 1"]
        q = out["doc"]["deep"]["questions"][0]
        assert q["text"] == "‘방문객 데이터 활용’의 범위는 어디까지인가요?" and q["options"] == []
        doc = (await c.post(f"/v1/rq-flows/{d3['id']}/deep-questions/{q['id']}:answer", json={"text": "익명 통계만 · 개인 식별 없음"})).json()
        r1 = doc["keymen"][1]["reqs"][0]
        assert r1["text"] == "방문객 데이터 활용 — 익명 통계만 · 개인 식별 없음" and r1["status"] == "ok" and r1["by"] == "ai-accepted"


async def test_deep_questions_fallback_and_confidential(hub, app):
    async with testing.api_client(app) as c:
        d = await _new(c)
        hub.overrides["rq.deep_questions.v1"] = {"error": {"status": 503, "code": "LLM_UNAVAILABLE"}}
        out = (await c.post(f"/v1/rq-flows/{d['id']}/deep-questions")).json()
        assert out["mode"] == "rule" and [q["target"]["kind"] for q in out["doc"]["deep"]["questions"]] == ["target", "customer", "title"]
        # 빈 답은 422 · 닫으면 답하지 않은 질문은 버린다
        q0 = out["doc"]["deep"]["questions"][0]
        r = await c.post(f"/v1/rq-flows/{d['id']}/deep-questions/{q0['id']}:answer", json={})
        assert r.status_code == 422 and r.json()["error"]["code"] == "NOTHING_SELECTED"
        doc = (await c.post(f"/v1/rq-flows/{d['id']}/deep-questions:close")).json()
        assert doc["deep"]["questions"] == [] and doc["counts"]["pending"] == 0
        hub.overrides["rq.deep_questions.v1"] = {"error": {"status": 403, "code": "POLICY_CONFIDENTIAL"}}
        r = await c.post(f"/v1/rq-flows/{d['id']}/deep-questions")
        assert r.status_code == 403 and r.json()["error"]["code"] == "POLICY_CONFIDENTIAL"


async def test_fill_from_file_keeps_human_values(hub, app):
    async with testing.api_client(app) as c:
        d = await _put(c, await _new(c), {"title": "", "customer": "K 리츠(직접)", "target": "", "note": "", "keymen": [{"role": "", "weight": 100, "reqs": []}]})
        fid = await upload("회의록_K리츠.txt", K_MEMO.encode(), "text/plain")
        r = await c.post(f"/v1/rq-flows/{d['id']}:fill", json={"file_ids": [fid]})
        assert r.status_code == 202, r.text
        assert r.json()["ref"] == {"kind": "rq_flow", "id": d["id"]}
        busy = (await c.get(f"/v1/rq-flows/{d['id']}")).json()
        assert busy["fill_job"] == r.json()["job_id"]
        r2 = await c.put(f"/v1/rq-flows/{d['id']}", json={**BOARD_FORM})
        assert r2.status_code == 409 and r2.json()["error"]["code"] == "FILLING"
        assert await drain() >= 1
        doc = (await c.get(f"/v1/rq-flows/{d['id']}")).json()
        assert doc["fill_job"] is None
        assert doc["title"] == "성수 플래그십 리테일 리뉴얼" and doc["title_by"] == "file"
        assert doc["customer"] == "K 리츠(직접)"                    # 사람 값 보호
        assert [(k["role"], k["weight"]) for k in doc["keymen"]] == [("자산관리팀장", 60), ("마케팅 리드", 40)]
        v = doc["keymen"][1]["reqs"][1]
        assert v["text"] == "방문객 데이터 활용" and v["flag"] == "vague" and v["by"] == "file"
        assert doc["sources"][0]["name"] == "회의록_K리츠.txt" and doc["sources"][0]["filled"] == 8
        assert "rq.flow_extract.v1" in hub.tasks()
        # 숫자 가드: 문서에 없는 숫자가 섞인 요구는 버린다
        from winmate_requirements.rqflow import merge_extraction
        dd = {"keymen": []}
        merge_extraction(dd, {"keymen": [{"role": "대표이사", "reqs": [{"text": "에너지 30% 절감"}, {"text": "에너지 절감"}]}]}, {"text": "대표이사 에너지 절감"})
        assert [r["text"] for r in dd["keymen"][0]["reqs"]] == ["에너지 절감"] and dd["keymen"][0]["weight"] == 100


async def test_finish_creates_storyboard_then_pushes_stage(hub, app):
    """처음 저장 → Storyboard 자동 생성(stages.rq §6) · 다시 저장 → push_stage(ver 2) · 분기 Storyboard 도 함께 반영."""
    async with testing.api_client(app) as c, testing.api_client(hub.rec["storyboard"].app) as sb:
        empty = await _new(c, keymen=[])
        r = await c.post(f"/v1/rq-flows/{empty['id']}:finish")
        assert r.status_code == 422 and r.json()["error"]["code"] == "EMPTY_FORM"

        d = await _put(c, await _new(c), {**BOARD_FORM, "keymen": [{**BOARD_FORM["keymen"][0], "weight": 30}, {**BOARD_FORM["keymen"][1], "weight": 20}]})
        out = (await c.post(f"/v1/rq-flows/{d['id']}:finish")).json()
        assert out["created"] is True and out["sb_name"] == "성수 플래그십 리테일"
        sb_id = out["sb_id"]
        st = out["stage"]
        assert st["customer"] == "K 리츠" and st["title"] == "성수 플래그십 리테일 리뉴얼" and st["target"] == ""
        assert st["keymen"][0] == {"role": "자산관리팀장", "weight": 60, "needs": ["1층 파사드 미디어로 집객", "테넌트별 콘텐츠 운영", "시설 원격 관리"]}
        assert st["keymen"][1]["weight"] == 40                     # 30 : 20 → 합 100 으로 맞춤
        assert st["requirements"][4] | {"id": "x"} == {"id": "x", "text": "방문객 데이터 활용", "status": "check", "by": "manual", "keyman": "마케팅 리드"}
        assert st["counts"] == {"keymen": 2, "reqs": 5, "check": 1}
        assert st["goals"] == ["1층 파사드 미디어로 집객", "테넌트별 콘텐츠 운영", "시설 원격 관리"]
        assert "스펙인" not in str(st) and "note" not in st          # 제작자 의견은 빠진다
        assert out["summary_md"].splitlines() == ["- 최종 제안대상 [확인 필요]",
                                                  "- 자산관리팀장(60%): 1층 파사드 미디어로 집객 · 테넌트별 콘텐츠 운영 · 시설 원격 관리",
                                                  "- 마케팅 리드(40%): 시즌 캠페인 빠른 교체 · 방문객 데이터 활용 [확인 필요]"]
        assert out["flow_sync"]["md_added"].startswith(f"## 요구사항 · {d['code']} v1")
        assert out["doc"]["sb_ids"] == [sb_id] and out["doc"]["ver"] == 1 and out["doc"]["status"] == "done"

        flow = (await sb.get(f"/v1/flows/{sb_id}")).json()
        assert flow["name"] == "성수 플래그십 리테일" and flow["customer"] == "K 리츠"
        rq = flow["stages"]["rq"]
        assert rq["ref"] == d["code"] and rq["ver"] == 1 and rq["requirements"][4]["status"] == "check"
        assert flow["cells"][0]["route"] == f"/requirements/flow/{d['id']}"
        assert flow["cards"]["rq"]["facts"] == [["고객사", "K 리츠"], ["최종 제안대상", "[확인 필요]"], ["요구", "5 · 확인 필요 1"]]
        assert flow["cards"]["rq"]["groups"][1]["lines"][1] == {"t": "방문객 데이터 활용", "note": "확인 필요"}
        assert "- 마케팅 리드(40%)" in flow["summary_md"]
        lst = (await sb.get("/v1/flows/contents/rq")).json()["items"]
        assert any(it["ref"] == d["code"] and it["route"] == f"/requirements/flow/{d['id']}" for it in lst)

        # 분기(복제본) — 사전 작업 rq 를 공유
        br = (await sb.post(f"/v1/flows/{sb_id}:branch", json={"stage": "dss"})).json()
        # 고쳐서 다시 저장 → 같은 Storyboard 에 push(ver 2), 분기도 함께
        d2 = (await c.get(f"/v1/rq-flows/{d['id']}")).json()
        d3 = await _put(c, d2, {**BOARD_FORM, "target": "자산관리본부장", "keymen": d2["keymen"]})
        out2 = (await c.post(f"/v1/rq-flows/{d3['id']}:finish")).json()
        assert out2["created"] is False and out2["sb_id"] == sb_id and out2["doc"]["ver"] == 2
        assert out2["flow_sync"]["synced"] == [br["id"]] and out2["flow_sync"]["md_added"].startswith(f"## 요구사항 · {d['code']} v2")
        flow = (await sb.get(f"/v1/flows/{sb_id}")).json()
        assert flow["stages"]["rq"]["ver"] == 2 and flow["stages"]["rq"]["target"] == "자산관리본부장"
        assert (await sb.get(f"/v1/flows/{br['id']}")).json()["stages"]["rq"]["ver"] == 2
        assert len((await sb.get("/v1/flows")).json()["items"]) == 2   # 새 Storyboard 를 또 만들지 않음
        assert out2["doc"]["sb_ids"] == [sb_id]


async def test_delete_draft_only(hub, app):
    """저장 전 초안만 지운다(204 · 목록 · 색인에서 빠짐) — 낡은 판 409 VERSION_CONFLICT · 없으면 404 · 저장한 것은 409 SAVED_CONTENT."""
    async with testing.api_client(app) as c, testing.api_client(hub.rec["storyboard"].app) as sb:
        d = await _put(c, await _new(c), BOARD_FORM)
        r = await c.delete(f"/v1/rq-flows/{d['id']}", params={"expected_version": 1})
        assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_CONFLICT"
        r = await c.delete(f"/v1/rq-flows/{d['id']}", params={"expected_version": d["version"]})
        assert r.status_code == 204 and r.content == b""
        assert (await c.get(f"/v1/rq-flows/{d['id']}")).status_code == 404
        assert d["id"] not in {i["id"] for i in (await c.get("/v1/rq-flows")).json()["items"]}
        assert hub.rec["workspace"].find("DELETE", f"/v1/items/{d['id']}")
        assert (await c.delete(f"/v1/rq-flows/{d['id']}")).status_code == 404
        assert (await c.delete("/v1/rq-flows/rqf_nope")).status_code == 404

        # 저장한 요구사항(Storyboard 자동 생성 · 연결)은 지울 수 없다
        s = await _put(c, await _new(c), BOARD_FORM)
        out = (await c.post(f"/v1/rq-flows/{s['id']}:finish")).json()
        r = await c.delete(f"/v1/rq-flows/{s['id']}")
        err = r.json()["error"]
        assert r.status_code == 409 and err["code"] == "SAVED_CONTENT" and err["message"] == "저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요"
        assert err["details"]["sb_ids"] == [out["sb_id"]] and err["details"]["ver"] == 1
        assert (await c.get(f"/v1/rq-flows/{s['id']}")).json()["status"] == "done"
        assert (await sb.get(f"/v1/flows/{out['sb_id']}")).json()["stages"]["rq"]["ref"] == s["code"]
        # 지운 초안의 번호는 다시 쓰지 않는다(카운터)
        e = await _new(c)
        assert int(e["code"][3:]) > int(s["code"][3:]) > int(d["code"][3:])


async def test_delete_cancels_fill_job(hub, app):
    """파일로 채우는 중에 초안을 지우면 잡을 취소하고, 지운 문서를 되살리지 않는다."""
    from winmate_common.jobs import jobs

    async with testing.api_client(app) as c:
        d = await _new(c, customer="K 리츠")
        fid = await upload("회의록_K리츠.txt", K_MEMO.encode(), "text/plain")
        job_id = (await c.post(f"/v1/rq-flows/{d['id']}:fill", json={"file_ids": [fid]})).json()["job_id"]
        assert (await c.delete(f"/v1/rq-flows/{d['id']}")).status_code == 204
        await drain()
        assert (await jobs().get(job_id)).status == "canceled"
        assert (await c.get(f"/v1/rq-flows/{d['id']}")).status_code == 404
        # 잡이 문서를 쓰려는 때 이미 지워져 있으면(취소 표시 없이) 되살리지 않고 취소로 끝낸다
        from winmate_requirements import rqflow

        d2 = await _new(c, customer="K 리츠")
        job2 = (await c.post(f"/v1/rq-flows/{d2['id']}:fill", json={"file_ids": [fid]})).json()["job_id"]
        rqflow._store().delete(rqflow.COLL, d2["id"])
        await drain()
        assert (await jobs().get(job2)).status == "canceled"
        assert rqflow._store().get(rqflow.COLL, d2["id"]) is None


async def test_finish_without_hub_keeps_saving(ai, app):
    """허브가 없으면(storyboard 연결 실패) 저장은 되고 flow_sync=null · 다음 저장에서 다시 만든다."""
    async with testing.api_client(app) as c:
        d = await _put(c, await _new(c), BOARD_FORM)
        out = (await c.post(f"/v1/rq-flows/{d['id']}:finish")).json()
        assert out["flow_sync"] is None and out["sb_id"] is None and out["doc"]["status"] == "done" and out["doc"]["sb_ids"] == []
