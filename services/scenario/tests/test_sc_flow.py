"""공간 시나리오 새 흐름 ↔ Storyboard 허브(2026-10-08 · docs/scenarios/11-content-flow.md §6 · 보드 webapp1 SC1 · SC2 · SC_Done · SC_DoneJson).

Gate 에서 고른 Storyboard 의 DSS 공간 · 공간별 제품으로 시작 → AI 3안 수락 · 직접 시나리오 → 저장하면 flow.json `stages.sc` · 요약본 · 팝업 카드 ·
편집 경로(`/scenario/spaces/{id}`)가 허브에 들어간다. 허브는 실제 storyboard 앱(in-process).
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from sc_world import World
from winmate_common import testing

# 보드 DS2 · e2e flowkit 의 DSS 값 모양(§6 dss)
DSS = {
    "industry": {"value": "오피스 · 업무시설", "by": "manual", "basis": None},
    "spaces": [
        {"name": "로비", "by": "manual", "products": [
            {"name": "The Wall IAB 146\"", "kind": "product", "ref": None, "qty": "1식", "by": "manual"},
            {"name": "Smart Signage QM55C", "kind": "product", "ref": "kb:model:mdl_LH55QMCEBGCXKR", "qty": "2대", "by": "manual"},
            {"name": "삼성 키오스크", "kind": "product", "ref": None, "qty": "1대", "by": "manual"}]},
        {"name": "회의실", "by": "manual", "products": [
            {"name": "Flip Pro WA75D", "kind": "product", "ref": None, "qty": None, "by": "manual"},
            {"name": "Smart Signage QB55C", "kind": "product", "ref": None, "qty": "실당 1대", "by": "manual"}]},
        {"name": "주차장", "by": "manual", "products": [{"name": "옥외형 사이니지 OHC55", "kind": "product", "ref": None, "qty": None, "by": "manual"}]},
    ],
    "solutions": [
        {"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo", "by": "manual", "links": ["로비 Smart Signage QM55C"], "why": None},
        {"name": "SmartThings Pro", "ref": None, "by": "manual", "links": [], "why": None},
    ],
    "counts": {"spaces": 3, "products": 6, "solutions": 2},
}


@pytest.fixture
def hub_world(env: None) -> Iterator[World]:
    w = World(real_storyboard=True)
    with testing.inprocess(w.apps):
        yield w


@pytest.fixture
async def clients(hub_world: World) -> AsyncIterator[tuple[Any, Any]]:
    from winmate_scenario.main import app
    async with testing.api_client(app) as c, testing.api_client(hub_world.apps["storyboard"]) as sb:
        yield c, sb


async def _flow(sb: Any, *, dss: bool = True) -> dict[str, Any]:
    f = (await sb.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용", "target": "대표이사",
                                         "rq": {"ref": "RQ-01", "ver": 1, "value": {"customer": "E 자산운용"}, "md": "- 요구 3"}})).json()
    if dss:
        r = await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-01", "ver": 1, "value": DSS, "md": "- 공간 3 · 제품 6"})
        assert r.status_code == 200, r.text
    return f


async def test_create_needs_storyboard_with_dss(clients: tuple[Any, Any]) -> None:
    """Gate: Storyboard 가 없으면 404, DSS 전이면 422 PREREQUISITE_MISSING."""
    c, sb = clients
    r = await c.post("/v1/space-sets", json={"sb_id": "SB-99"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "STORYBOARD_NOT_FOUND"
    f = await _flow(sb, dss=False)
    r = await c.post("/v1/space-sets", json={"sb_id": f["id"]})
    assert r.status_code == 422 and r.json()["error"]["code"] == "PREREQUISITE_MISSING"


async def test_prefill_from_dss_then_finish_pushes_stage(clients: tuple[Any, Any]) -> None:
    c, sb = clients
    f = await _flow(sb)
    r = await c.post("/v1/space-sets", json={"sb_id": f["id"]})
    assert r.status_code == 201, r.text
    d = r.json()
    # DSS 공간 · 공간별 제품 그대로 + 솔루션은 links 가 가리킨 공간에(MagicINFO → 로비), 어디도 안 가리키면 고르기 목록에만
    assert d["title"] == "용산 AI Ready 오피스" and d["dss_ref"] == "DSS-01" and d["customer"] == "E 자산운용" and d["ver"] == 0
    assert [s["name"] for s in d["spaces"]] == ["로비", "회의실", "주차장"]
    lobby = d["spaces"][0]
    assert [(p["name"], p["kind"]) for p in lobby["products"]] == [
        ("The Wall IAB 146\"", "product"), ("Smart Signage QM55C", "product"), ("삼성 키오스크", "product"), ("MagicINFO", "solution")]
    assert lobby["products"][1]["ref"] == "kb:model:mdl_LH55QMCEBGCXKR"
    assert not any(p["name"] == "SmartThings Pro" for s in d["spaces"] for p in s["products"])
    items = {i["name"]: i for i in d["dss_items"]}
    assert items["SmartThings Pro"]["kind"] == "solution" and items["SmartThings Pro"]["spaces"] == []
    assert items["MagicINFO"]["spaces"] == ["로비"] and items["Flip Pro WA75D"]["spaces"] == ["회의실"]
    assert d["counts"] == {"spaces": 3, "scenarios": 0, "spaces_without_scenario": 3, "spaces_without_product": 0}
    assert "요구 3" in (d["context_text"] or "")                               # AI 문맥 = 요약본

    # 로비 AI 3안 → A 수락 · 회의실 직접 시나리오
    s = (await c.post(f"/v1/space-sets/{d['id']}/spaces/{lobby['id']}:suggest")).json()
    assert s["mode"] == "llm" and len(s["set"]["spaces"][0]["candidates"]) == 3
    d = (await c.post(f"/v1/space-sets/{d['id']}/spaces/{lobby['id']}/candidates/A:accept")).json()
    d["spaces"][1]["scenarios"] = [{"id": "scn_meet", "title": "하이브리드 회의", "user": "프로젝트 팀", "products": ["Flip Pro WA75D"],
                                    "steps": [{"text": "[확인 필요]", "product": None}], "fields": [], "by": "manual"}]
    d = (await c.put(f"/v1/space-sets/{d['id']}", json={"expected_version": d["version"], "spaces": d["spaces"]})).json()
    assert d["issues"] == []

    out = (await c.post(f"/v1/space-sets/{d['id']}:finish")).json()
    st = out["stage"]
    assert st["ref"] == d["code"] and st["ver"] == 1 and st["from"] == "DSS-01"
    assert list(st) == ["ref", "ver", "from", "spaces", "rules", "counts"]       # 보드 SC_DoneJson 키 순서
    assert st["counts"] == {"spaces": 3, "scenarios": 2, "spacesWithoutScenario": 1}
    assert out["summary_md"].splitlines()[1] == "- 공간 3 · 시나리오 2 · 시나리오 없는 공간 1 (주차장)"
    head = out["flow_sync"]["md_added"].splitlines()[0]
    assert head.startswith("## ") and head.endswith(f"· {d['code']} v1")              # 머리 이름은 허브가 붙인다(보드: 「## 시나리오 · SC-01 v1」)
    assert "- 공간마다 제품 · 솔루션 1개 이상 확인됨" in out["flow_sync"]["md_added"]

    flow = (await sb.get(f"/v1/flows/{f['id']}")).json()
    hub = flow["stages"]["sc"]
    assert hub["ref"] == d["code"] and hub["ver"] == 1 and hub["from"] == "DSS-01"
    assert hub["spaces"][0]["scenarios"][0]["by"] == "ai-candidate-A" and hub["spaces"][0]["scenarios"][0]["title"] == "미등록 방문객 응대"
    assert hub["spaces"][0]["products"][-1] == "MagicINFO" and hub["rules"] == {"minProductsPerSpace": 1, "minProductsPerScenario": 1}
    cell = next(x for x in flow["cells"] if x["key"] == "sc")
    assert cell["state"] == "done" and cell["route"] == f"/scenario/spaces/{d['id']}"
    cardv = flow["cards"]["sc"]
    assert cardv["facts"] == [["공간", "3"], ["시나리오", "2"], ["시나리오 없는 공간", "1"]]
    assert cardv["line"] == "공간 3 · 시나리오 2 · 시나리오 없는 공간 1"
    assert cardv["groups"][1] == {"h": "회의실", "sub": "시나리오 1", "lines": [{"t": "하이브리드 회의", "note": "확인 필요"}]}
    # 보드 List(content=sc) — 저장된 공간 시나리오와 연결된 Storyboard
    lst = (await sb.get("/v1/flows/contents/sc")).json()
    row = next(x for x in lst["items"] if x["ref"] == d["code"])
    assert row["route"] == f"/scenario/spaces/{d['id']}" and row["storyboards"][0]["id"] == f["id"]

    # 다시 고쳐 저장 → ver 2(저장 횟수) · 허브도 v2
    out2 = (await c.post(f"/v1/space-sets/{d['id']}:finish")).json()
    assert out2["stage"]["ver"] == 2
    assert (await sb.get(f"/v1/flows/{f['id']}")).json()["stages"]["sc"]["ver"] == 2
    assert (await c.get(f"/v1/space-sets/{d['id']}")).json()["ver"] == 2
    items = (await c.get("/v1/space-sets")).json()["items"]
    assert next(x for x in items if x["id"] == d["id"])["ver"] == 2


async def test_branch_storyboard_gets_own_space_set(clients: tuple[Any, Any]) -> None:
    """Gate 「복제본 만들기」 — 분기 Storyboard 는 DSS 를 공유하므로 같은 공간으로 새 SC 를 시작하고, 원본 stages.sc 는 그대로."""
    c, sb = clients
    f = await _flow(sb)
    a = (await c.post("/v1/space-sets", json={"sb_id": f["id"]})).json()
    await c.post(f"/v1/space-sets/{a['id']}:finish")
    b = (await sb.post(f"/v1/flows/{f['id']}:branch", json={"stage": "sc"})).json()
    d = (await c.post("/v1/space-sets", json={"sb_id": b["id"]})).json()
    assert d["sb_id"] == b["id"] and d["dss_ref"] == "DSS-01" and [s["name"] for s in d["spaces"]] == ["로비", "회의실", "주차장"]
    out = (await c.post(f"/v1/space-sets/{d['id']}:finish")).json()
    assert out["flow_sync"] is not None and out["flow_sync"]["synced"] == []
    assert (await sb.get(f"/v1/flows/{f['id']}")).json()["stages"]["sc"]["ref"] == a["code"]
    assert (await sb.get(f"/v1/flows/{b['id']}")).json()["stages"]["sc"]["ref"] == d["code"]


# ── DSS 다시 가져오기 · 초안 지우기 · 같은 Storyboard 초안 이어 쓰기(2026-10-10) ──

def _dss_v2() -> dict[str, Any]:
    """로비: 삼성 키오스크 빠짐 · Smart Signage QH55C 새로 / 회의실: QB55C 빠짐 / 라운지 새 공간(QM55C) / 주차장 빠짐."""
    import copy
    v = copy.deepcopy(DSS)
    lobby, meet = v["spaces"][0], v["spaces"][1]
    lobby["products"] = [p for p in lobby["products"] if p["name"] != "삼성 키오스크"] + [
        {"name": "Smart Signage QH55C", "kind": "product", "ref": None, "qty": "1대", "by": "manual"}]
    meet["products"] = [p for p in meet["products"] if p["name"] != "Smart Signage QB55C"]
    v["spaces"] = [lobby, meet, {"name": "라운지", "by": "manual", "products": [
        {"name": "Smart Signage QM55C", "kind": "product", "ref": "kb:model:mdl_LH55QMCEBGCXKR", "qty": "1대", "by": "manual"}]}]
    return v


async def test_resync_dss_merges_spaces_and_keeps_scenarios(clients: tuple[Any, Any]) -> None:
    c, sb = clients
    f = await _flow(sb)
    d = (await c.post("/v1/space-sets", json={"sb_id": f["id"]})).json()
    assert d["dss_ver"] == 1 and d["dss_spaces"] == ["로비", "회의실", "주차장"]
    assert (await c.get(f"/v1/space-sets/{d['id']}")).json()["dss_changed"] is None
    # 사람: 로비에 키오스크를 쓰는 시나리오 · DSS 제품 The Wall 을 로비에서 뺌
    d["spaces"][0]["scenarios"] = [{"id": "scn_kiosk", "title": "무인 방문 접수", "user": "방문객", "products": ["삼성 키오스크", "MagicINFO"],
                                    "steps": [{"text": "키오스크에서 접수", "product": "삼성 키오스크"}], "fields": [], "by": "manual"}]
    d["spaces"][0]["products"] = [p for p in d["spaces"][0]["products"] if not p["name"].startswith("The Wall")]
    d = (await c.put(f"/v1/space-sets/{d['id']}", json={"expected_version": d["version"], "spaces": d["spaces"]})).json()
    # 사람이 고친 것은 DSS 차이가 아니다
    assert (await c.get(f"/v1/space-sets/{d['id']}")).json()["dss_changed"] is None

    r = await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-01", "ver": 2, "value": _dss_v2(), "md": "- 공간 3"})
    assert r.status_code == 200, r.text
    ch = (await c.get(f"/v1/space-sets/{d['id']}")).json()["dss_changed"]
    assert ch == {"from": "DSS-01 v1", "to": "DSS-01 v2", "ref_changed": False, "added": 1, "removed": 3, "changed": 1,
                  "spaces_added": 1, "spaces_removed": 1, "added_names": ["Smart Signage QH55C"],
                  "removed_names": ["삼성 키오스크", "Smart Signage QB55C", "옥외형 사이니지 OHC55"]}

    r = await c.post(f"/v1/space-sets/{d['id']}:resync-dss")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["dss_changed"] is None and d["dss_ver"] == 2 and d["dss_spaces"] == ["로비", "회의실", "라운지"]
    sp = {s["name"]: s for s in d["spaces"]}
    assert list(sp) == ["로비", "회의실", "라운지"]                                  # 주차장: DSS 에서 빠지고 시나리오 · 제품도 없어 뺌
    lobby = {p["name"]: p.get("dss_status") for p in sp["로비"]["products"]}
    # 키오스크는 시나리오가 써서 남김(「DSS에서 빠짐」) · QH55C 새로 · 사람이 뺀 The Wall 은 DSS 가 그대로라 다시 넣지 않음
    assert lobby == {"Smart Signage QM55C": None, "삼성 키오스크": "removed", "MagicINFO": None, "Smart Signage QH55C": "added"}
    assert [p["name"] for p in sp["회의실"]["products"]] == ["Flip Pro WA75D"]           # 쓰는 시나리오 없는 QB55C 는 뺌
    assert sp["라운지"]["dss_status"] == "added" and [(p["name"], p["dss_status"]) for p in sp["라운지"]["products"]] == [("Smart Signage QM55C", "added")]
    scn = sp["로비"]["scenarios"][0]
    assert scn["id"] == "scn_kiosk" and scn["products"] == ["삼성 키오스크", "MagicINFO"] and scn["steps"][0]["product"] == "삼성 키오스크"
    lr = d["last_resync"]
    assert lr["from"] == "DSS-01 v1" and lr["to"] == "DSS-01 v2"
    assert lr["added"] == ["로비 · Smart Signage QH55C", "라운지 · Smart Signage QM55C"]
    assert lr["removed"] == ["회의실 · Smart Signage QB55C", "주차장 · 옥외형 사이니지 OHC55"]
    assert lr["kept"] == ["로비 · 삼성 키오스크"] and lr["spaces_added"] == ["라운지"] and lr["spaces_removed"] == ["주차장"]
    assert {i["name"] for i in d["dss_items"]} == {"The Wall IAB 146\"", "Smart Signage QM55C", "Smart Signage QH55C", "Flip Pro WA75D", "MagicINFO", "SmartThings Pro"}
    assert (await c.get(f"/v1/space-sets/{d['id']}")).json()["dss_changed"] is None
    # 화면이 고쳐 저장하면 표시도 그대로 오간다 · 저장하면 허브에도 새 공간
    d = (await c.put(f"/v1/space-sets/{d['id']}", json={"expected_version": d["version"], "spaces": d["spaces"]})).json()
    assert next(s for s in d["spaces"] if s["name"] == "라운지")["dss_status"] == "added"
    out = (await c.post(f"/v1/space-sets/{d['id']}:finish")).json()
    assert [s["name"] for s in out["stage"]["spaces"]] == ["로비", "회의실", "라운지"] and out["stage"]["from"] == "DSS-01"

    # DSS 자체가 바뀜(분기 등 다른 ref) — 내용이 같아도 알리고, 다시 가져오면 from 이 새 DSS · 저장 뒤 고친 것이라 초안 상태
    await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-02", "ver": 1, "value": _dss_v2(), "md": "- 공간 3"})
    ch = (await c.get(f"/v1/space-sets/{d['id']}")).json()["dss_changed"]
    assert ch["ref_changed"] is True and ch["from"] == "DSS-01 v2" and ch["to"] == "DSS-02 v1" and ch["added"] == ch["removed"] == 0
    d = (await c.post(f"/v1/space-sets/{d['id']}:resync-dss")).json()
    assert d["dss_ref"] == "DSS-02" and d["status"] == "draft" and d["ver"] == 1
    # 다음 다시 가져오기에서는 지난번 「새로」 표시가 지워진다
    assert all(p.get("dss_status") != "added" for s in d["spaces"] for p in s["products"]) and all(s.get("dss_status") != "added" for s in d["spaces"])
    assert (await c.get(f"/v1/space-sets/{d['id']}")).json()["dss_changed"] is None


async def test_space_set_draft_delete_and_dedupe(clients: tuple[Any, Any], hub_world: World) -> None:
    c, sb = clients
    f = await _flow(sb)
    r = await c.post("/v1/space-sets", json={"sb_id": f["id"]})
    assert r.status_code == 201
    a = r.json()
    # Gate 에서 같은 Storyboard 로 다시 시작 → 저장 전 초안(200, 같은 id)
    r = await c.post("/v1/space-sets", json={"sb_id": f["id"]})
    assert r.status_code == 200 and r.json()["id"] == a["id"]
    async with testing.api_client(hub_world.apps["workspace"]) as ws:
        assert (await ws.get(f"/v1/items/{a['id']}")).status_code == 200
        assert (await c.delete(f"/v1/space-sets/{a['id']}")).status_code == 204
        assert (await ws.get(f"/v1/items/{a['id']}")).status_code == 404
    assert (await c.get(f"/v1/space-sets/{a['id']}")).status_code == 404
    assert (await c.delete(f"/v1/space-sets/{a['id']}")).status_code == 404
    # 저장한 묶음은 지울 수 없다(저장 뒤 고쳐 초안 상태여도)
    b = (await c.post("/v1/space-sets", json={"sb_id": f["id"]})).json()
    assert b["id"] != a["id"]
    assert (await c.post(f"/v1/space-sets/{b['id']}:finish")).status_code == 200
    b = (await c.put(f"/v1/space-sets/{b['id']}", json={"spaces": (await c.get(f"/v1/space-sets/{b['id']}")).json()["spaces"]})).json()
    assert b["status"] == "draft" and b["ver"] == 1
    r = await c.delete(f"/v1/space-sets/{b['id']}")
    assert r.status_code == 409 and r.json()["error"]["code"] == "SAVED_CONTENT"
    assert r.json()["error"]["message"] == "저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요"
    # 저장한 묶음만 있으면 새 초안 · 지운 초안이 있어도 코드가 겹치지 않음 · 공간을 직접 준 이전 시작은 이어 쓰지 않는다
    r = await c.post("/v1/space-sets", json={"sb_id": f["id"]})
    assert r.status_code == 201 and r.json()["id"] != b["id"] and r.json()["code"] != b["code"]
    r2 = await c.post("/v1/space-sets", json={"sb_id": f["id"], "spaces": [{"name": "로비", "products": [{"name": "MagicINFO", "kind": "solution"}]}]})
    assert r2.status_code == 201 and r2.json()["id"] != r.json()["id"]
