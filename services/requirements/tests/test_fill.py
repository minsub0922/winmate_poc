"""파일 → 폼(rq.fill) — SSE 이벤트 · 출처 · 사람 값 보호 · 지원 형식 · 파일 빼기 · 채우는 중 막기(§9.1-6~10)."""
from __future__ import annotations

from rq_testkit import DEMO_MEMO, PPTX_MIME, drain, pptx_bytes, upload
from winmate_common import testing
from winmate_common.jobs import jobs


async def _fill(c, rq_id, *file_ids):
    r = await c.post(f"/v1/requirements/{rq_id}/files", json={"file_ids": list(file_ids)})
    assert r.status_code == 202, r.text
    return r.json()


async def _two_files():
    p = await upload("제안지원요청서_용산 업무시설 재개발.pptx", pptx_bytes(), PPTX_MIME)
    t = await upload("고객 미팅 메모_11월 4일.txt", DEMO_MEMO.encode(), "text/plain")
    return p, t


async def test_fill_two_files(platform, app):
    async with testing.api_client(app) as c:
        rq = (await c.post("/v1/requirements", json={})).json()
        p, t = await _two_files()
        acc = await _fill(c, rq["id"], p, t)
        assert acc["ref"] == {"kind": "requirement", "id": rq["id"]}
        mid = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert mid["list_state"] == "filling" and mid["active_job"]["kind"] == "rq.fill"
        assert [f["status"] for f in mid["files"]] == ["reading", "reading"]
        assert mid["files"][0]["type_label"] == "PPTX" and mid["files"][1]["type_label"] == "TXT"
        # 채우는 중에는 심층 작성 · 저장 막기(§9.1-10)
        d = await c.post(f"/v1/requirements/{rq['id']}/deep-sessions")
        assert d.status_code == 409 and d.json()["error"]["code"] == "JOB_RUNNING"
        s = await c.post(f"/v1/requirements/{rq['id']}/save", json={})
        assert s.status_code == 409 and s.json()["error"]["code"] == "JOB_RUNNING"
        assert await drain() >= 1
        ev = await jobs().events(acc["job_id"])
        types = [e["type"] for _, e in ev]
        assert types[-1] == "done" and "result" in types
        steps = [e["data"] for _, e in ev if e["type"] == "step" and str(e["data"].get("key", "")).startswith("file:")]
        for fid in (p, t):
            st = [x["state"] for x in steps if x["key"] == f"file:{fid}"]
            assert st == ["reading", "done"], st
        prog = [e["data"] for _, e in ev if e["type"] == "progress" and "filled" in e["data"]]
        filled = [x["filled"] for x in prog]
        assert filled == sorted(filled) and prog[-1]["filled"] == prog[-1]["total"] > 0
        assert all(x["total"] >= x["filled"] for x in prog)
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        f = doc["form"]
        assert f["project_name"]["value"] == "용산 업무시설 재개발 AI Ready 오피스"
        assert f["project_name"]["source"]["kind"] == "file" and f["project_name"]["source"]["file_label"] == "PPTX"
        assert f["customer_name"]["source"]["file_label"] == "PPTX"
        assert f["author_note"]["source"]["file_label"] == "TXT" and "스펙인" in f["author_note"]["value"]
        assert f["final_audience"]["value"] is None
        names = [k["name"] for k in f["keymen"]]
        assert names == ["대표이사", "공간컨텐츠실장", "개발사업팀장"]
        assert [len(k["items"]) for k in f["keymen"]] == [3, 3, 1]
        assert [k["weight"] for k in f["keymen"]] == [34, 33, 33] and f["weights_mode"] == "equal_default"
        assert f["keymen"][0]["items"][2]["source"]["file_label"] == "TXT"
        assert f["keymen"][0]["items"][0]["source"]["locator"] == "슬라이드 3"
        assert [x["status"] for x in doc["files"]] == ["done", "done"] and doc["files"][0]["doc_kind"] == "rfp"
        assert doc["files"][1]["doc_kind"] == "meeting_memo"
        assert doc["active_job"] is None and doc["list_state"] == "input"
        assert doc["title"] == "E 자산운용 용산 AI Ready 오피스"  # short_title(mock)
        assert doc["context"]["vertical"]["top2"][0]["id"]
        assert all(it["short"] for k in f["keymen"] for it in k["items"])
    # 기밀: ai-tools 요청은 전부 confidential=true(§9.1-32)
    chats = platform["ai-tools"].find("POST", "/v1/")
    assert chats and all(x["json"].get("confidential") is True for x in chats)


async def test_user_value_protected_and_rollback(platform, app):
    async with testing.api_client(app) as c:
        rq = (await c.post("/v1/requirements", json={})).json()
        r = await c.patch(f"/v1/requirements/{rq['id']}/draft",
                          json={"ops": [{"op": "set_field", "field": "project_name", "value": "직접 입력"}]})
        assert r.status_code == 200
        p, t = await _two_files()
        await _fill(c, rq["id"], p)
        await drain()
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        pn = doc["form"]["project_name"]
        assert pn["value"] == "직접 입력" and pn["source"]["kind"] == "user"
        assert pn["alternatives"][0]["value"] == "용산 업무시설 재개발 AI Ready 오피스"
        # 메모 파일을 더 넣으면 기존 값에 합친다
        await _fill(c, rq["id"], t)
        await drain()
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        ceo = doc["form"]["keymen"][0]
        assert ceo["name"] == "대표이사" and len(ceo["items"]) == 3
        # 파일 A(PPTX)에서 온 대표이사 항목 2개 중 1개를 사람이 고친다
        a_items = [it for it in ceo["items"] if it["source"]["file_id"] == p]
        assert len(a_items) == 2
        r = await c.patch(f"/v1/requirements/{rq['id']}/draft",
                          json={"ops": [{"op": "update_item", "item_id": a_items[0]["id"], "text": "사람이 고친 항목"}]})
        assert r.status_code == 200
        rm = await c.delete(f"/v1/requirements/{rq['id']}/files/{p}", params={"rollback": "true"})
        assert rm.status_code == 200
        after = rm.json()
        texts = [it["text"] for k in after["form"]["keymen"] for it in k["items"]]
        assert "사람이 고친 항목" in texts and "'최초 AI Ready' 공간으로 알리기" not in texts
        assert "오피스를 업무환경 플랫폼으로" not in texts
        assert [f["file_id"] for f in after["files"]] == [t]
        assert after["form"]["customer_name"]["value"] is None  # PPTX 에서만 온 값
        assert after["form"]["project_name"]["value"] == "직접 입력"
        assert sum(k["weight"] for k in after["form"]["keymen"]) == 100
        # 되돌리기(재추출 없이)
        back = await c.post(f"/v1/requirements/{rq['id']}/files/{p}/restore")
        assert back.status_code == 200
        texts = [it["text"] for k in back.json()["form"]["keymen"] for it in k["items"]]
        assert "'최초 AI Ready' 공간으로 알리기" in texts and back.json()["form"]["customer_name"]["value"] == "E 자산운용"


async def test_rollback_removes_empty_keyman(platform, app):
    async with testing.api_client(app) as c:
        rq = (await c.post("/v1/requirements", json={})).json()
        p, t = await _two_files()
        await _fill(c, rq["id"], p, t)
        await drain()
        rm = await c.delete(f"/v1/requirements/{rq['id']}/files/{t}", params={"rollback": "true"})
        ks = rm.json()["form"]["keymen"]
        assert [k["name"] for k in ks] == ["대표이사", "공간컨텐츠실장"]  # 메모에서만 온 개발사업팀장은 빠짐
        assert [k["weight"] for k in ks] == [50, 50] and rm.json()["form"]["author_note"]["value"] is None


async def test_unsupported_type(platform, app):
    async with testing.api_client(app) as c:
        rq = (await c.post("/v1/requirements", json={})).json()
        x = await upload("예산.xlsx", b"PK\x03\x04not-really", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        r = await c.post(f"/v1/requirements/{rq['id']}/files", json={"file_ids": [x]})
        assert r.status_code == 422 and r.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
        r = await c.post(f"/v1/requirements/{rq['id']}/files", json={"file_ids": ["file_01J0000000000000000000000Z"]})
        assert r.status_code == 404 and r.json()["error"]["code"] == "FILE_NOT_FOUND"


async def test_queue_second_fill(platform, app):
    async with testing.api_client(app) as c:
        rq = (await c.post("/v1/requirements", json={})).json()
        p, t = await _two_files()
        a = await _fill(c, rq["id"], p)
        b = await _fill(c, rq["id"], t)
        mid = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert mid["active_job"]["job_id"] == a["job_id"] and [j["job_id"] for j in mid["queued_jobs"]] == [b["job_id"]]
        await drain()
        doc = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert doc["active_job"] is None and doc["queued_jobs"] == [] and len(doc["form"]["keymen"]) == 3


async def test_from_files(platform, app):
    async with testing.api_client(app) as c:
        p, _ = await _two_files()
        r = await c.post("/v1/requirements/from-files", json={"file_ids": [p], "customer_hint": "이 자산운용"})
        assert r.status_code == 202
        rq_id = r.json()["ref"]["id"]
        await drain()
        doc = (await c.get(f"/v1/requirements/{rq_id}")).json()
        assert doc["form"]["customer_name"]["value"] == "E 자산운용"  # 파일 값이 힌트보다 우선
        assert doc["form"]["project_name"]["value"]


async def test_snapshot_items_carry_file_quote(platform, app):
    """제안서(R2 · R3)가 쓰는 항목 근거 — 스냅숏 items_flat[].source 에 file_id · locator(쪽) · quote."""
    async with testing.api_client(app) as c:
        p, _ = await _two_files()
        r = await c.post("/v1/requirements/from-files", json={"file_ids": [p]})
        rq_id = r.json()["ref"]["id"]
        await drain()
        assert (await c.post(f"/v1/requirements/{rq_id}/save", json={})).status_code == 201
        v = (await c.get(f"/v1/requirements/{rq_id}/versions/latest")).json()
        flat = v["snapshot"]["items_flat"]
        assert flat and all(i["source"]["kind"] == "file" and i["source"]["file_id"] == p for i in flat)
        first = next(i for i in flat if i["text"] == "사용자를 인식하고 반응하는 'AI Ready' 오피스")
        assert first["source"]["locator"] == "슬라이드 3" and "AI Ready" in first["source"]["quote"]
