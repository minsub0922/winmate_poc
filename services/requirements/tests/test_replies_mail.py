"""메일 문구 · 고객 답변 → v2 · Storyboard 영향 · 링크 동기화(§9.1-26 · 28~30)."""
from __future__ import annotations

from rq_testkit import DEMO_REPLY, drain, pdf_bytes, upload
from test_deep import run_board_flow
from winmate_common import testing


async def _saved_board(c):
    rq, k, _sid, _last = await run_board_flow(c)
    sv = await c.post(f"/v1/requirements/{rq['id']}/save", json={"reason": "deep"})
    assert sv.json()["version"] == 1
    return rq, k


async def test_mail_draft(platform, app):
    async with testing.api_client(app) as c:
        rq, _k = await _saved_board(c)
        qs = (await c.get(f"/v1/requirements/{rq['id']}/customer-questions")).json()["items"]
        assert len(qs) == 2
        both = await c.post(f"/v1/requirements/{rq['id']}/customer-questions/mail-draft", json={"question_ids": [q["id"] for q in qs]})
        assert both.status_code == 200 and both.json()["generated_by"] == "llm"
        assert all(q["text"] in both.json()["body"] for q in qs)
        # 하나 해제 → 체크한 것만(고정 응답은 둘 다 들어 있어 템플릿으로)
        await c.patch(f"/v1/requirements/{rq['id']}/customer-questions/{qs[1]['id']}", json={"include_in_mail": False})
        one = await c.post(f"/v1/requirements/{rq['id']}/customer-questions/mail-draft", json={"question_ids": [qs[0]["id"]]})
        body = one.json()
        assert one.status_code == 200 and body["generated_by"] == "template"
        assert qs[0]["text"] in body["body"] and qs[1]["text"] not in body["body"]
        assert "스펙인" not in body["body"] and "가중치" not in body["body"] and "50%" not in body["body"]
        assert body["subject"] == "[E 자산운용] 용산 업무시설 재개발 AI Ready 오피스 관련 확인 요청"
        assert body["body"].startswith("안녕하세요, E 자산운용 담당자님.") and body["body"].endswith("감사합니다.")
        none = await c.post(f"/v1/requirements/{rq['id']}/customer-questions/mail-draft", json={"question_ids": ["cq_nope"]})
        assert none.status_code == 422


async def test_mail_template_when_llm_fails(ai, app):
    async with testing.api_client(app) as c:
        rq = (await c.post("/v1/requirements", json={"form": {"customer_name": "E 자산운용", "author_note": "설계 단계 스펙인이 목표"}})).json()
        q = (await c.post(f"/v1/requirements/{rq['id']}/customer-questions", json={"text": "회의 일정을 알려 주실 수 있을까요?",
                                                                                   "origin": {"kind": "manual"}})).json()
        ai.overrides["rq.mail_draft"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "장애"}}
        r = await c.post(f"/v1/requirements/{rq['id']}/customer-questions/mail-draft", json={"question_ids": [q["id"]]})
        assert r.json()["generated_by"] == "template" and "1. 회의 일정을 알려 주실 수 있을까요?" in r.json()["body"]
        # 제작자 의견이 섞인 LLM 문구는 버린다
        ai.overrides["rq.mail_draft"] = {"json": {"subject": "확인 요청", "body": "1. 회의 일정을 알려 주실 수 있을까요?\n설계 단계 스펙인이 목표입니다"}}
        r = await c.post(f"/v1/requirements/{rq['id']}/customer-questions/mail-draft", json={"question_ids": [q["id"]]})
        assert r.json()["generated_by"] == "template" and "스펙인" not in r.json()["body"]


async def test_reply_to_v2(platform, app):
    async with testing.api_client(app) as c:
        rq, _k = await _saved_board(c)
        rid = rq["id"]
        doc = (await c.get(f"/v1/requirements/{rid}")).json()
        platform_item = doc["form"]["keymen"][1]["items"][0]
        energy_item = doc["form"]["keymen"][0]["items"][2]
        await c.put(f"/v1/requirements/{rid}/links/storyboard/sb_01",
                    json={"title": "E 자산운용 용산 오피스 제안 기획", "route": "/storyboard/sb_01", "rq_version": 1,
                          "depends_on": [{"target": {"kind": "item", "id": platform_item["id"]},
                                          "places": [{"code": "P2-1", "label": "Part 2 로비"}, {"code": "P2-2", "label": "Part 2 라운지"}]}]})
        empty = await c.post(f"/v1/requirements/{rid}/replies", json={"text": " ", "file_ids": []})
        assert empty.status_code == 422 and empty.json()["error"]["code"] == "EMPTY_REPLY"
        pdf = await upload("성수오피스_에너지사용량_2025.pdf", pdf_bytes(), "application/pdf")
        acc = await c.post(f"/v1/requirements/{rid}/replies", json={"text": DEMO_REPLY, "file_ids": [pdf]})
        assert acc.status_code == 202 and acc.json()["ref"]["kind"] == "reply"
        rpid = acc.json()["ref"]["id"]
        assert (await c.get(f"/v1/requirements/{rid}/replies/{rpid}")).json()["status"] == "analyzing"
        await drain()
        r = (await c.get(f"/v1/requirements/{rid}/replies/{rpid}")).json()
        assert r["status"] == "ready" and r["base_version"] == 1
        rows = [(ch["label"], ch["before_display"], ch["after_display"]) for ch in r["changes"]]
        assert rows == [("공간컨텐츠실장", "업무환경 플랫폼", "입주사 앱 · 공용 공간 예약 · 방문객 안내"),
                        ("대표이사", "근거 자료 없음", "성수오피스_에너지사용량_2025.pdf"),
                        ("최종 제안대상", "대표이사", "대표이사 · 투자심의위원 2")]
        assert r["storyboard_impact"]["count"] == 2 and r["storyboard_impact"]["links"][0]["ref_id"] == "sb_01"
        ch = {c_["label"]: c_ for c_ in r["changes"]}
        # 첫째(업무환경 플랫폼) 해제 → 영향 0
        sel = [ch["대표이사"]["id"], ch["최종 제안대상"]["id"]]
        p = (await c.patch(f"/v1/requirements/{rid}/replies/{rpid}", json={"selected_change_ids": sel})).json()
        assert p["storyboard_impact"]["count"] == 0
        nothing = await c.post(f"/v1/requirements/{rid}/replies/{rpid}/apply", json={"selected_change_ids": []})
        assert nothing.status_code == 422 and nothing.json()["error"]["code"] == "NOTHING_TO_APPLY"
        ap = await c.post(f"/v1/requirements/{rid}/replies/{rpid}/apply", json={"selected_change_ids": sel, "propagate": ["storyboard"]})
        assert ap.status_code == 201, ap.text
        assert ap.json() == {"version": 2, "pending_sync_links": [{"service": "storyboard", "ref_id": "sb_01"}]}
        again = await c.post(f"/v1/requirements/{rid}/replies/{rpid}/apply", json={"selected_change_ids": sel})
        assert again.status_code == 409 and again.json()["error"]["code"] == "ALREADY_APPLIED"
        doc = (await c.get(f"/v1/requirements/{rid}")).json()
        f = doc["form"]
        assert f["final_audience"]["value"] == "대표이사 · 투자심의위원 2" and f["final_audience"]["source"]["kind"] == "reply"
        ev = next(i for i in f["keymen"][0]["items"] if i["id"] == energy_item["id"])
        assert ev["evidence"][0]["name"] == "성수오피스_에너지사용량_2025.pdf" and ev["needs_confirmation"] is False
        pi = next(i for i in f["keymen"][1]["items"] if i["id"] == platform_item["id"])
        assert pi["text"] == "오피스를 업무환경 플랫폼으로" and pi["needs_confirmation"] is True  # 해제한 변경은 반영 안 됨
        qs = {q["text"]: q for q in (await c.get(f"/v1/requirements/{rid}/customer-questions", params={"status": "all"})).json()["items"]}
        assert qs["유사 건물 에너지 사용량 자료를 받을 수 있을까요?"]["status"] == "answered"
        assert qs["'업무환경 플랫폼'에 어떤 서비스가 들어가나요?"]["status"] == "open"
        v2 = (await c.get(f"/v1/requirements/{rid}/versions/2")).json()
        assert v2["reason"] == "reply" and v2["note"] == "고객 답변 반영" and v2["final_audience"] == "대표이사 · 투자심의위원 2"
        links = (await c.get(f"/v1/requirements/{rid}/links")).json()["items"]
        assert links[0]["sync_state"] == "pending" and links[0]["pending_version"] == 2
        # 소비자가 새 버전으로 다시 등록하면 up_to_date(§9.1-30)
        up = await c.put(f"/v1/requirements/{rid}/links/storyboard/sb_01", json={"rq_version": 2, "depends_on": []})
        assert up.json()["sync_state"] == "up_to_date" and up.json()["pending_version"] is None
        assert up.json()["title"] == "E 자산운용 용산 오피스 제안 기획"
        d = (await c.get(f"/v1/requirements/{rid}/diff", params={"from": 1, "to": 2})).json()
        kinds = {(x["target"]["kind"], x["kind"]) for x in d["changes"]}
        assert ("field", "changed") in kinds and ("item", "changed") in kinds


async def test_export_docx(platform, app):
    from winmate_common.client import ServiceClient

    async with testing.api_client(app) as c:
        rq = (await c.post("/v1/requirements", json={"form": {"customer_name": "E 자산운용", "project_name": "용산 오피스",
                                                               "author_note": "내부 전략 비밀 문장"}})).json()
        await c.post(f"/v1/requirements/{rq['id']}/save", json={})
        acc = await c.post(f"/v1/requirements/{rq['id']}/exports", json={"format": "docx"})
        assert acc.status_code == 202
        await drain()
        rec = (await c.get(f"/v1/requirements/{rq['id']}/exports/{acc.json()['ref']['id']}")).json()
        assert rec["status"] == "done" and rec["file_id"], rec
        data, _ = await ServiceClient("files").get_bytes(f"/v1/files/{rec['file_id']}/content")
        import io
        import zipfile

        xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode()
        assert "E 자산운용" in xml and "내부 전략 비밀 문장" not in xml


async def test_reply_drops_changes_not_in_reply(platform, app):
    """고정 응답이 답에 없는 변경(최종 제안대상 · 근거 파일)을 내도 답변 글 · 첨부에 근거가 없으면 버린다."""
    async with testing.api_client(app) as c:
        rq, _k = await _saved_board(c)
        rid = rq["id"]
        text = "업무환경 플랫폼은 입주사 앱, 공용 공간 예약, 방문객 안내를 생각하고 있습니다."
        acc = await c.post(f"/v1/requirements/{rid}/replies", json={"text": text, "file_ids": []})
        await drain()
        r = (await c.get(f"/v1/requirements/{rid}/replies/{acc.json()['ref']['id']}")).json()
        assert r["status"] == "ready"
        assert [(ch["label"], ch["after_display"]) for ch in r["changes"]] == [("공간컨텐츠실장", "입주사 앱 · 공용 공간 예약 · 방문객 안내")]
