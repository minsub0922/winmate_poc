"""mock 데모 한 바퀴 — 실제 플랫폼 앱(ai-tools mock = mocks/ai-tools/ca.*.json · kb 실데이터 · files · jobs · workspace · export).

넣기 → 찾기 → 후보 확인 → 분석 → 결과 · 상세 → 묶음 · ProposalHandoff → 리포트. mock 고정 응답이 의미 있는 데모가 되는지 본다.
"""
from __future__ import annotations

from ca_scenario import A_TEXT


async def test_demo_round(demo):
    c = demo.c
    r = await c.post("/v1/parse", json={"text": A_TEXT})
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["found_count"] == 4
    assert [p["slots"][k]["chip_text"] for k in ("customer", "industry", "place", "product")] == [
        "고객사 · A 커피 프랜차이즈", "업종 · 외식 · 카페", "장소 · 수도권 직영점", '제품 · 55" 사이니지 + 배포 솔루션']

    r = await c.post("/v1/analyses", json={"input_mode": "free", "text": A_TEXT})
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    r = await c.post(f"/v1/analyses/{aid}/find")
    assert r.status_code == 202, r.text
    await demo.drain()
    a = (await c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "confirming", a
    assert a["title"] == "A 커피 메뉴보드 경쟁사 분석"
    cands = (await c.get(f"/v1/analyses/{aid}/candidates")).json()
    rows = [(x["letter"], x["real_name"], x["status"], x["confidence_label"], x["on"]) for x in cands["items"]]
    assert [r_[0] for r_ in rows] == ["A", "B", "C", "D", "E", "F"], rows
    assert [r_[2] for r_ in rows] == ["rec", "rec", "rec", "rec", "check", "drop"], rows
    assert cands["header"]["desc"] == "입력에서 읽은 4가지로 후보 6곳을 찾았어요. 추천 4곳은 켜 두었고, 빼거나 더할 수 있어요."
    crit = (await c.get(f"/v1/analyses/{aid}/criteria")).json()
    assert crit["summary_text"] == "요구사항에서 3 · 업종 사례에서 1 · 기본 2", crit
    assert [x["name"] for x in crit["items"]] == ["본사 일괄 배포", "매장별 가격 차등", "전기료", "인건비 절감", "가격대", "레퍼런스 · AS"]

    r = await c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    assert r.status_code == 202, r.text
    await demo.drain()
    a = (await c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "done", a
    res = (await c.get(f"/v1/analyses/{aid}/result")).json()
    assert [x["letter"] for x in res["competitors"]] == ["A", "B", "C", "D"]
    a_row = res["competitors"][0]
    assert a_row["positioning"] == "자체 CMS 기반 풀 라인업 · 500매장 이상은 서버 추가"
    assert a_row["up"] >= 2
    assert len(res["strengths"]) == 3
    assert res["strengths"][0]["title"] == "서버 없는 통합 관리"
    assert len(res["cautions"]) == 2
    assert res["footer"]["sources"] > 0
    det = (await c.get(f"/v1/analyses/{aid}/competitors/{a_row['id']}")).json()
    facts = {f["key"]: f for f in det["facts"]}
    assert facts["price"]["text"] == "[확인 필요]" and facts["price"]["check"]
    assert facts["references"]["text"] == "공개 사례 6건 · 수도권 3건"

    tbl = (await c.get(f"/v1/analyses/{aid}/result", params={"view": "table"})).json()["table"]
    assert [x["label"] for x in tbl["columns"]] == ["경쟁사 A", "경쟁사 B", "경쟁사 C", "경쟁사 D", "삼성"]

    b = (await c.get(f"/v1/analyses/{aid}/bundle", params={"target": "proposal_why"})).json()
    blob = str(b)
    for name in ("가나 디스플레이", "다라 사이니지", "마바 클라우드", "사아 키오스크", "Gana Display"):
        assert name not in blob
    ph = (await c.get(f"/v1/analyses/{aid}/proposal-handoff", params={"section": "why"})).json()
    assert [i["key"] for i in ph["items"]] == ["CM", "ST"]

    r = await c.post(f"/v1/analyses/{aid}/exports", json={"format": "pdf", "audience": "internal"})
    assert r.status_code == 202
    await demo.drain()
    from winmate_common.jobs import jobs

    j = await jobs().get(r.json()["job_id"])
    assert j.status == "succeeded", j.error
    assert j.result["file_id"].startswith("file_")
    lst = (await c.get("/v1/analyses")).json()
    row = next(x for x in lst["items"] if x["id"] == aid)
    assert row["sent_label"] == "리포트"
    assert row["note"].startswith("출처 ")
