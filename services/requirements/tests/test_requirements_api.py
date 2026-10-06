"""정의서 API — 생성 · 자동 저장 · 가중치 · 저장/버전 · 되돌리기 · code · 목록/탭 · 오류 · 링크 · 고객 질문(§9.1)."""
from __future__ import annotations

import re

from winmate_common import testing
from winmate_common.ids import new_id
from winmate_requirements import domain

RQ_ID = re.compile(r"^rq_[0-9A-HJKMNP-TV-Z]{26}$")


async def _create(c, **form):
    r = await c.post("/v1/requirements", json={"form": form} if form else {})
    assert r.status_code == 201, r.text
    return r.json()


async def _patch(c, rq, ops, base=None):
    r = await c.patch(f"/v1/requirements/{rq['id']}/draft", json={"base_revision": base, "ops": ops})
    return r


async def _demo(c):
    """보드 예시 정의서(키맨 3명 · 항목 7)."""
    rq = await _create(c)
    k = [new_id("km") for _ in range(3)]
    ops = [{"op": "set_field", "field": "project_name", "value": "용산 업무시설 재개발 AI Ready 오피스"},
           {"op": "set_field", "field": "customer_name", "value": "E 자산운용"},
           {"op": "set_field", "field": "author_note", "value": "설계 단계 스펙인이 목표. 성수 오피스 대비 '최초 AI Ready'를 강조."},
           {"op": "add_keyman", "keyman_id": k[0], "name": "대표이사"},
           {"op": "add_keyman", "keyman_id": k[1], "name": "공간컨텐츠실장"},
           {"op": "add_keyman", "keyman_id": k[2], "name": "개발사업팀장"}]
    for kid, texts in zip(k, [["사용자를 인식하고 반응하는 'AI Ready' 오피스", "'최초 AI Ready' 공간으로 알리기", "에너지 절감 · 정량 데이터 확보"],
                              ["오피스를 업무환경 플랫폼으로", "예측 · 반응형 공간 (Connecting-AI)", "건물 가치 · 임대 선호도 제고"],
                              ["AI 인프라를 설계 단계에 미리 반영"]], strict=True):
        ops += [{"op": "add_item", "keyman_id": kid, "text": t} for t in texts]
    r = await _patch(c, rq, ops)
    assert r.status_code == 200, r.text
    return r.json(), k


async def test_create(platform, app):
    async with testing.api_client(app) as c:
        rq = await _create(c)
        assert RQ_ID.match(rq["id"])
        assert rq["version"] == 0 and rq["list_state"] == "input" and rq["state_label"] == "입력 중"
        assert all(rq["form"][f]["value"] is None for f in domain.FIELDS) and rq["form"]["keymen"] == []
        assert rq["route"] == f"/requirements/{rq['id']}/form" and rq["title"] is None
    puts = platform["workspace"].find("PUT", f"/v1/items/{rq['id']}")
    assert len(puts) == 1
    assert puts[0]["json"]["feature"] == "RQ" and puts[0]["json"]["route"] == f"/requirements/{rq['id']}/form"


async def test_autosave_and_conflict(platform, app):
    async with testing.api_client(app) as c:
        rq = await _create(c)
        r = await _patch(c, rq, [{"op": "set_field", "field": "project_name", "value": "A"}], base=rq["revision"])
        assert r.status_code == 200
        body = r.json()
        assert body["revision"] == rq["revision"] + 1
        assert body["form"]["project_name"]["value"] == "A" and body["form"]["project_name"]["source"]["kind"] == "user"
        # 다른 쓰기가 같은 칸을 먼저 바꿨으면 409 + current
        r2 = await _patch(c, rq, [{"op": "set_field", "field": "project_name", "value": "B"}], base=rq["revision"])
        assert r2.status_code == 409 and r2.json()["error"]["code"] == "REVISION_CONFLICT"
        assert r2.json()["error"]["details"]["current"]["form"]["project_name"]["value"] == "A"
        # 다른 칸이면 충돌 아님
        r3 = await _patch(c, rq, [{"op": "set_field", "field": "customer_name", "value": "E 자산운용"}], base=rq["revision"])
        assert r3.status_code == 200
        # 없는 대상은 건너뜀
        r4 = await _patch(c, rq, [{"op": "update_item", "item_id": new_id("ri"), "text": "x"}])
        assert r4.status_code == 200 and r4.json()["skipped_ops"][0]["op"] == "update_item"
        # 길이 상한
        r5 = await _patch(c, rq, [{"op": "set_field", "field": "customer_name", "value": "가" * 81}])
        assert r5.status_code == 422 and r5.json()["error"]["code"] == "VALIDATION_FAILED"
        # 새로 읽어도 그대로
        g = await c.get(f"/v1/requirements/{rq['id']}")
        assert g.json()["form"]["customer_name"]["value"] == "E 자산운용"
        assert g.json()["title"] == "E 자산운용 A"


async def test_equal_weights(platform, app):
    async with testing.api_client(app) as c:
        rq = await _create(c)
        k = [new_id("km") for _ in range(3)]
        r = await _patch(c, rq, [{"op": "add_keyman", "keyman_id": k[0], "name": "대표이사"},
                                 {"op": "add_keyman", "keyman_id": k[1], "name": "공간컨텐츠실장"}])
        ks = r.json()["form"]["keymen"]
        assert [x["weight"] for x in ks] == [50, 50] and r.json()["form"]["weights_mode"] == "equal_default"
        r = await _patch(c, rq, [{"op": "add_keyman", "keyman_id": k[2], "name": "개발사업팀장"}])
        assert [x["weight"] for x in r.json()["form"]["keymen"]] == [34, 33, 33]
        r = await _patch(c, rq, [{"op": "remove_keyman", "keyman_id": k[1]}, {"op": "remove_keyman", "keyman_id": k[2]}])
        assert [x["weight"] for x in r.json()["form"]["keymen"]] == [100]
        # 색 번호는 추가 순서(삭제해도 남은 키맨 색 그대로)
        assert r.json()["form"]["keymen"][0]["color_index"] == 0


async def test_weight_validation_and_stepper(platform, app):
    async with testing.api_client(app) as c:
        rq, k = await _demo(c)
        bad = await _patch(c, rq, [{"op": "set_weights", "weights": {k[0]: 33, k[1]: 33, k[2]: 33}}])
        assert bad.status_code == 422 and bad.json()["error"]["code"] == "WEIGHTS_SUM_INVALID"
        bad = await _patch(c, rq, [{"op": "set_weights", "weights": {k[0]: 3, k[1]: 48, k[2]: 49}}])
        assert bad.status_code == 422 and bad.json()["error"]["code"] == "WEIGHT_MIN"
        ok = await _patch(c, rq, [{"op": "set_weights", "weights": {k[0]: 34, k[1]: 33, k[2]: 33}}])
        assert ok.status_code == 200 and ok.json()["form"]["weights_mode"] == "custom"
        # 웹 규칙(−/+, 5 단위) 그대로: 34 → 35, 나머지 비율대로
        stepped = domain.step_weights([34, 33, 33], 0, +1)
        assert stepped[0] == 35 and sum(stepped) == 100 and min(stepped) >= 5
        ok = await _patch(c, rq, [{"op": "set_weights", "weights": dict(zip(k, stepped, strict=True))}])
        assert [x["weight"] for x in ok.json()["form"]["keymen"]] == stepped
        assert domain.step_weights([35, 33, 32], 0, +1)[0] == 40
        assert domain.step_weights([34, 33, 33], 0, -1)[0] == 30
        assert domain.step_weights([90, 5, 5], 0, +1) == [90, 5, 5]
        # 커스텀에서 키맨을 지우면 남은 키맨에 비율대로
        r = await _patch(c, rq, [{"op": "remove_keyman", "keyman_id": k[2]}])
        ws = [x["weight"] for x in r.json()["form"]["keymen"]]
        assert sum(ws) == 100 and len(ws) == 2


async def test_save_versions_restore(platform, app):
    async with testing.api_client(app) as c:
        rq = await _create(c)
        empty = await c.post(f"/v1/requirements/{rq['id']}/save", json={})
        assert empty.status_code == 422 and empty.json()["error"]["code"] == "EMPTY_FORM"
        rq, _k = await _demo(c)
        s1 = await c.post(f"/v1/requirements/{rq['id']}/save", json={})
        assert s1.status_code == 201, s1.text
        assert s1.json()["version"] == 1 and s1.json()["created"] is True
        assert s1.json()["requirement"]["list_state"] == "saved" and s1.json()["requirement"]["state_label"] == "저장됨 · v1"
        again = await c.post(f"/v1/requirements/{rq['id']}/save", json={})
        assert again.status_code == 200 and again.json() == {"version": 1, "created": False, "requirement": None}
        r = await _patch(c, rq, [{"op": "set_field", "field": "final_audience", "value": "대표이사"}])
        assert r.json()["list_state"] == "editing" and r.json()["state_label"] == "고치는 중 · v1"
        s2 = await c.post(f"/v1/requirements/{rq['id']}/save", json={})
        assert s2.json()["version"] == 2
        v1 = (await c.get(f"/v1/requirements/{rq['id']}/versions/1")).json()
        assert v1["snapshot"]["form"]["final_audience"]["value"] is None and v1["reason"] == "direct"
        assert v1["summary"] == "키맨 3 · 요구사항 7" and len(v1["snapshot"]["items_flat"]) == 7
        assert v1["snapshot"]["author_note"]["internal"] is True and v1["customer_name"] == "E 자산운용"
        latest = (await c.get(f"/v1/requirements/{rq['id']}/versions/latest")).json()
        assert latest["version"] == 2 and latest["reason"] == "edit" and latest["latest_version"] == 2
        assert (await c.get(f"/v1/requirements/{rq['id']}/versions/9")).json()["error"]["code"] == "VERSION_NOT_FOUND"
        rs = await c.post(f"/v1/requirements/{rq['id']}/versions/1/restore")
        assert rs.status_code == 201 and rs.json() == {"version": 3}
        v3 = (await c.get(f"/v1/requirements/{rq['id']}/versions/3")).json()
        assert v3["snapshot"]["form"]["final_audience"]["value"] is None and v3["reason"] == "restore"
        cur = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert cur["form"]["final_audience"]["value"] is None and cur["version"] == 3 and cur["has_unsaved_changes"] is False
        # 되돌리기 뒤에도 v1 스냅숏은 그대로
        assert (await c.get(f"/v1/requirements/{rq['id']}/versions/1")).json()["snapshot"] == v1["snapshot"]
        vl = (await c.get(f"/v1/requirements/{rq['id']}/versions")).json()["items"]
        assert [v["version"] for v in vl] == [3, 2, 1]
        d = (await c.get(f"/v1/requirements/{rq['id']}/diff", params={"from": 1, "to": 2})).json()
        assert any(ch["target"] == {"kind": "field", "id": "final_audience"} and ch["kind"] == "added" for ch in d["changes"])
    # 저장 뒤 작업물 경로 = 정의서 보기, 첫 저장에 프로젝트 생성
    last = platform["workspace"].find("PUT", f"/v1/items/{rq['id']}")[-1]["json"]
    assert last["route"] == f"/requirements/{rq['id']}" and last["status"] == "saved" and last["project_id"]
    assert len(platform["workspace"].find("POST", "/v1/projects")) == 1


async def test_item_codes_not_reused(platform, app):
    async with testing.api_client(app) as c:
        rq = await _create(c)
        kid = new_id("km")
        r = await _patch(c, rq, [{"op": "add_keyman", "keyman_id": kid, "name": "대표이사"}]
                         + [{"op": "add_item", "keyman_id": kid, "text": f"항목 {i}"} for i in range(3)])
        items = r.json()["form"]["keymen"][0]["items"]
        assert [i["code"] for i in items] == ["RQ-01", "RQ-02", "RQ-03"]
        r = await _patch(c, rq, [{"op": "remove_item", "item_id": items[1]["id"]},
                                 {"op": "add_item", "keyman_id": kid, "text": "새 항목"}])
        assert [i["code"] for i in r.json()["form"]["keymen"][0]["items"]] == ["RQ-01", "RQ-03", "RQ-04"]


async def test_list_tabs_counts(platform, app):
    from winmate_requirements import repo

    async with testing.api_client(app) as c:
        a, _ = await _demo(c)
        await c.post(f"/v1/requirements/{a['id']}/save", json={})
        b = await _create(c, customer_name="F 리테일", project_name="강남 플래그십")
        await c.post(f"/v1/requirements/{b['id']}/save", json={})
        d = await _create(c, customer_name="G 병원")
        e = await _create(c, customer_name="E 자산운용 2", project_name="판교 사옥")

        def deep(doc, rev):
            doc["deep"] = {"session_id": new_id("ds"), "status": "asking"}

        await repo.mutate(e["id"], deep)
        counts = (await c.get("/v1/requirements/counts")).json()
        assert counts == {"all": 4, "in_progress": 2, "saved": 2}
        ip = (await c.get("/v1/requirements", params={"tab": "in_progress"})).json()["items"]
        assert [x["id"] for x in ip] == [e["id"], d["id"]]
        assert ip[0]["list_state"] == "deepening" and ip[1]["state_label"] == "입력 중"
        q = (await c.get("/v1/requirements", params={"q": "E 자산"})).json()["items"]
        assert {x["id"] for x in q} == {a["id"], e["id"]}
        hv = (await c.get("/v1/requirements", params={"has_version": "true"})).json()["items"]
        assert {x["id"] for x in hv} == {a["id"], b["id"]}
        assert all(x["version"] >= 1 for x in hv) and hv[0]["saved_at"]
        page = (await c.get("/v1/requirements", params={"limit": 3})).json()
        assert len(page["items"]) == 3 and page["next_cursor"]
        rest = (await c.get("/v1/requirements", params={"limit": 3, "cursor": page["next_cursor"]})).json()
        assert len(rest["items"]) == 1 and rest["next_cursor"] is None
        assert (await c.get("/v1/requirements", params={"customer": "F 리"})).json()["items"][0]["id"] == b["id"]


async def test_not_found_error_shape(platform, app):
    async with testing.api_client(app) as c:
        r = await c.get(f"/v1/requirements/{new_id('rq')}")
        assert r.status_code == 404
        err = r.json()["error"]
        assert err["code"] == "NOT_FOUND" and re.search(r"[가-힣]", err["message"])


async def test_links_and_questions(platform, app):
    async with testing.api_client(app) as c:
        rq, k = await _demo(c)
        await c.post(f"/v1/requirements/{rq['id']}/save", json={})
        item = rq["form"]["keymen"][1]["items"][0]
        body = {"text": "출근 혼잡 시간대를 알려 주실 수 있을까요?", "short_label": "출근 혼잡 시간대", "target": {"kind": "item", "id": item["id"]},
                "origin": {"kind": "storyboard", "service": "storyboard", "ref_id": "sb_X", "place_label": "Part 2 로비"}}
        r1 = await c.post(f"/v1/requirements/{rq['id']}/customer-questions", json=body)
        assert r1.status_code == 201 and r1.json()["keyman_id"] == k[1] and r1.json()["origin"]["place_label"] == "Part 2 로비"
        r2 = await c.post(f"/v1/requirements/{rq['id']}/customer-questions", json=body)
        assert r2.status_code == 200 and r2.json()["id"] == r1.json()["id"]
        qs = (await c.get(f"/v1/requirements/{rq['id']}/customer-questions")).json()["items"]
        assert len(qs) == 1
        cur = (await c.get(f"/v1/requirements/{rq['id']}")).json()
        assert cur["open_question_count"] == 1 and cur["form"]["keymen"][1]["items"][0]["needs_confirmation"] is True
        # 질문 추가는 내용 변경이 아니다(저장됨 그대로)
        assert cur["list_state"] == "saved"
        p = await c.patch(f"/v1/requirements/{rq['id']}/customer-questions/{r1.json()['id']}", json={"include_in_mail": False})
        assert p.json()["include_in_mail"] is False
        # 제안서(R4) 모양 — origin.feature
        r3 = await c.post(f"/v1/requirements/{rq['id']}/customer-questions",
                          json={"text": "예산 범위를 알려 주실 수 있을까요?", "origin": {"feature": "PR", "ref_id": "prp_1", "confirm_item_id": "R5"}})
        assert r3.status_code == 201 and r3.json()["origin"]["kind"] == "proposal"
        # 링크
        lk = await c.put(f"/v1/requirements/{rq['id']}/links/storyboard/sb_X",
                         json={"title": "E 자산운용 용산 오피스 제안 기획", "route": "/storyboard/sb_X", "rq_version": 1,
                               "depends_on": [{"target": {"kind": "item", "id": item["id"]},
                                               "places": [{"code": "P2-1", "label": "Part 2 로비"}]}]})
        assert lk.status_code == 200 and lk.json()["sync_state"] == "up_to_date"
        links = (await c.get(f"/v1/requirements/{rq['id']}/links")).json()["items"]
        assert links[0]["service"] == "storyboard" and links[0]["depends_on"][0]["places"][0]["label"] == "Part 2 로비"
        assert (await c.delete(f"/v1/requirements/{rq['id']}/links/storyboard/sb_X")).status_code == 204
        assert (await c.get(f"/v1/requirements/{rq['id']}/links")).json()["items"] == []
