"""공간 → 시나리오 → 장면(새 흐름, 2026-10-08) — 보드 webapp1 SC2 · SC2_AI · SC2_Pick · SC2_Empty · SC_DoneJson."""
from __future__ import annotations

SPACES = [
    {"name": "로비", "products": [{"name": "The Wall IAB 146\"", "kind": "product"}, {"name": "Smart Signage QM55C", "kind": "product"},
                                {"name": "삼성 키오스크", "kind": "product"}, {"name": "MagicINFO", "kind": "solution", "ref": "kb:solution:sol_magicinfo"}]},
    {"name": "주차장", "products": [{"name": "옥외형 사이니지 OHC55", "kind": "product"}]},
]


async def _new(client):
    r = await client.post("/v1/space-sets", json={"title": "용산 AI Ready 오피스", "sb_id": "SB-01", "spaces": SPACES})
    assert r.status_code == 201, r.text
    return r.json()


async def test_scenarios_per_space_free_form_and_products(client):
    d = await _new(client)
    assert d["counts"] == {"spaces": 2, "scenarios": 0, "spaces_without_scenario": 2, "spaces_without_product": 0}
    lobby = d["spaces"][0]
    lobby["scenarios"] = [
        {"id": "scn_a", "title": "예약 방문객의 첫 5분", "user": "사전 예약한 외부 방문객", "products": ["The Wall IAB 146\"", "없는 제품"],
         "steps": [{"text": "QR 로 게이트 통과", "product": None}, {"text": "The Wall 환영", "product": "The Wall IAB 146\""},
                   {"text": "안내 사이니지", "product": "Smart Signage QM55C"}],   # 시나리오 제품이 아니면 지운다
         "fields": [{"k": "시간대", "v": "오전 10시"}, {"k": "내가 만든 항목", "v": "자유"}]},
        {"id": "scn_b", "title": "출근 혼잡", "user": "임직원", "products": ["MagicINFO"], "steps": [], "fields": []},
    ]
    r = await client.put(f"/v1/space-sets/{d['id']}", json={"expected_version": d["version"], "spaces": d["spaces"]})
    assert r.status_code == 200, r.text
    d = r.json()
    a = d["spaces"][0]["scenarios"][0]
    assert a["products"] == ["The Wall IAB 146\""] and a["steps"][2]["product"] is None
    assert [f["k"] for f in a["fields"]] == ["시간대", "내가 만든 항목"]
    assert d["counts"]["scenarios"] == 2 and d["issues"] == []
    # 낙관적 잠금
    assert (await client.put(f"/v1/space-sets/{d['id']}", json={"expected_version": 1, "spaces": d["spaces"]})).status_code == 409


async def test_space_without_product_blocks_finish(client):
    d = await _new(client)
    d["spaces"][1]["products"] = []
    d = (await client.put(f"/v1/space-sets/{d['id']}", json={"spaces": d["spaces"]})).json()
    assert d["issues"][0]["code"] == "SPACE_WITHOUT_PRODUCT" and d["counts"]["spaces_without_product"] == 1
    r = await client.post(f"/v1/space-sets/{d['id']}:finish")
    assert r.status_code == 422 and r.json()["error"]["code"] == "SPACE_WITHOUT_PRODUCT"
    # AI 3안도 제품 없는 공간에서는 막힌다
    r = await client.post(f"/v1/space-sets/{d['id']}/spaces/{d['spaces'][1]['id']}:suggest")
    assert r.status_code == 422


async def test_ai_three_candidates_accept_and_finish(client):
    d = await _new(client)
    lobby = d["spaces"][0]
    r = await client.post(f"/v1/space-sets/{d['id']}/spaces/{lobby['id']}:suggest")
    assert r.status_code == 200, r.text
    body = r.json()
    cands = body["set"]["spaces"][0]["candidates"]
    assert body["mode"] == "llm" and [c["cid"] for c in cands] == ["A", "B", "C"]
    assert cands[0]["title"] == "미등록 방문객 응대" and all(p in [x["name"] for x in SPACES[0]["products"]] for c in cands for p in c["products"])
    assert body["set"]["counts"]["scenarios"] == 0                        # 수락 전에는 시나리오가 아니다
    d = (await client.post(f"/v1/space-sets/{d['id']}/spaces/{lobby['id']}/candidates/A:accept")).json()
    sc = d["spaces"][0]["scenarios"][0]
    assert sc["by"] == "ai-candidate-A" and len(d["spaces"][0]["candidates"]) == 2
    d = (await client.delete(f"/v1/space-sets/{d['id']}/spaces/{lobby['id']}/candidates/B")).json()
    assert [c["cid"] for c in d["spaces"][0]["candidates"]] == ["C"]
    # 주차장: 3안(LLM 고정 응답 없음 → KB 사례 참고 · [확인 필요])
    park = d["spaces"][1]
    body = (await client.post(f"/v1/space-sets/{d['id']}/spaces/{park['id']}:suggest")).json()
    assert body["mode"] == "kb_only" and len(body["set"]["spaces"][1]["candidates"]) == 3
    assert all("[확인 필요]" in (c["steps"][0]["text"] + c["user"]) for c in body["set"]["spaces"][1]["candidates"])
    st = (await client.post(f"/v1/space-sets/{d['id']}:finish")).json()
    assert st["stage"]["from"] == "SB-01" and st["stage"]["counts"] == {"spaces": 2, "scenarios": 1, "spacesWithoutScenario": 1}
    assert st["stage"]["spaces"][0]["scenarios"][0]["steps"][0]["product"] == "삼성 키오스크"
    assert st["summary_md"].startswith("## 시나리오 ·")


async def test_candidate_edit_before_accept(client):
    """보드 SC2_AI — 수락 전 점선 후보도 고칠 수 있다(같은 id · cid 만 반영, 목록은 서버 기준)."""
    d = await _new(client)
    lobby = d["spaces"][0]
    d = (await client.post(f"/v1/space-sets/{d['id']}/spaces/{lobby['id']}:suggest")).json()["set"]
    c = d["spaces"][0]["candidates"]
    c[0]["title"] = "고친 후보 이름"
    c[0]["steps"].append({"text": "새 단계", "product": None})
    c.append({**c[1], "id": "fake", "cid": "B", "title": "가짜"})          # 서버에 없는 후보는 들어가지 않는다
    d = (await client.put(f"/v1/space-sets/{d['id']}", json={"spaces": d["spaces"]})).json()
    cs = d["spaces"][0]["candidates"]
    assert len(cs) == 3 and cs[0]["title"] == "고친 후보 이름" and cs[0]["steps"][-1]["text"] == "새 단계"
    d = (await client.post(f"/v1/space-sets/{d['id']}/spaces/{lobby['id']}/candidates/A:accept")).json()
    assert d["spaces"][0]["scenarios"][0]["title"] == "고친 후보 이름"
