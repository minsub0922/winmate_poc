"""부분 재분석(MI3R) — AC-MI-52 · 53 · 54 · 55 · 56 · 57 · 58."""
from __future__ import annotations

import json
import re
from typing import Any

from mi_scenario import compare_cells, full_fb, strengths

from winmate_mi import store as R


def setup_revise(env: Any) -> None:
    env.ai.llm["mi.revise_interpret"] = {"operations": [{"op": "add_row", "target": "유지보수 · AS", "detail": ""},
                                                        {"op": "edit_cell", "target": "경쟁사 B 저전력 운영", "detail": "공개 자료로"},
                                                        {"op": "edit_strength", "target": "에너지 절감", "detail": "더 구체적으로"}],
                                         "needs_search": True, "quick_suggestion": None}
    env.ai.web["mi.web_revise"] = lambda body: ({"summary": "다라 사이니지 55형 메뉴보드 소비전력은 200 W이다."} if "다라 사이니지" in body["query"]
                                                else {"summary": ""})

    def cells(body: dict[str, Any]) -> dict[str, Any]:
        out = compare_cells(body)
        prompt = body["messages"][-1]["content"]
        m = re.search(r'"id": "(cmp_[A-Z0-9]+)", "name": "다라 사이니지"', prompt)
        for c in out["cells"]:
            if m and c["competitor_id"] == m.group(1) and "전력" in prompt.split("경쟁사:")[0]:
                c["text"] = "55형 소비전력 200 W"
                c["citations"] = [{"evidence_id": "E1", "quote": "다라 사이니지 55형 메뉴보드 소비전력은 200 W이다"}]
        return out

    env.ai.llm["mi.compare_cells"] = cells

    def strengths2(body: dict[str, Any]) -> dict[str, Any]:
        out = strengths(body)
        if "요청:" in body["messages"][-1]["content"]:
            for s in out["strengths"]:
                if s["title"] == "에너지 절감":
                    s["note"] = "QM55C 소비전력 154 W · 전원 스케줄로 절감"
        return out

    env.ai.llm["mi.strengths"] = strengths2


async def _revision(env: Any, aid: str, instruction: str = "경쟁사 비교에 유지보수 · AS를 넣고, 경쟁사 B 전력은 공개 자료로 다시") -> dict[str, Any]:
    r = await env.c.post(f"/v1/analyses/{aid}/revisions", json={"scope": {"kind": "area", "area": "competitor"}, "instruction": instruction})
    assert r.status_code == 202, r.text
    rev = r.json()["revision_id"]
    await env.drain()
    return (await env.c.get(f"/v1/analyses/{aid}/revisions/{rev}")).json()


def _area_dump(v: dict[str, Any], area: str) -> str:
    claims = {k: c for k, c in (v.get("claims") or {}).items() if c.get("area") == area}
    cits = [c for c in v.get("citations") or [] if c.get("claim_id") in claims]
    srcs = {c["source_id"]: v["sources"][c["source_id"]] for c in cits}
    return json.dumps({"doc": (v.get("document") or {}).get(area), "claims": claims, "cits": cits, "srcs": srcs}, ensure_ascii=False, sort_keys=True)


async def test_ac52_ac53_ac54_apply_scope(env):
    aid = await full_fb(env)
    setup_revise(env)
    view = await _revision(env, aid)
    assert view["revision"]["status"] == "proposed"
    assert view["chips"] == {"row_add": 1, "value_edit": 1, "strength_edit": 1} and view["changed_count"] == 3
    assert view["agent_text"] == "경쟁사 탭만 다시 분석했습니다. 다른 3개 탭은 그대로이고, 바뀐 곳은 파란 표시로 남겨 두었어요."
    assert view["quick_suggestions"][0] == "더 간결하게" and len(view["quick_suggestions"]) == 2
    assert view["footer"].startswith("출처 ") and "(+" in view["footer"]
    labels = sorted(c["label"] for c in view["changes"])
    assert labels == sorted(["강점 수정", "값 수정", "행 추가"])
    # AC-MI-54 — 값 수정 되돌리기
    vedit = next(c for c in view["changes"] if c["kind"] == "value_edit")
    assert vedit["before"] == "[확인 필요]" and vedit["after"] == "55형 소비전력 200 W"
    r = await env.c.patch(f"/v1/analyses/{aid}/revisions/{view['revision']['id']}/changes/{vedit['id']}", json={"reverted": True})
    assert r.status_code == 200 and r.json()["reverted"]
    view2 = (await env.c.get(f"/v1/analyses/{aid}/revisions/{view['revision']['id']}")).json()
    assert view2["changed_count"] == 2
    base = await R.call(R.get_version, aid, 1)
    r = await env.c.post(f"/v1/analyses/{aid}/revisions/{view['revision']['id']}/apply")
    assert r.status_code == 200 and r.json()["version"] == 2
    new = await R.call(R.get_version, aid, 2)
    assert new["kind"] == "revision"
    for area in ("market", "customer", "user"):
        assert _area_dump(new, area) == _area_dump(base, area), area
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    rows = {r["name"]: r for r in res["competitor"]["table"]["rows"]}
    assert "유지보수 · AS" in rows
    col_b = next(c["key"] for c in res["competitor"]["table"]["columns"] if c["label"] == "경쟁사 B")
    assert rows["저전력 운영"]["cells"][col_b]["text"] == "[확인 필요]"          # 되돌린 값 수정은 반영 안 됨
    assert any(s["note"].startswith("QM55C 소비전력 154 W · 전원") for s in res["competitor"]["strengths"])
    crit = (await env.c.get(f"/v1/analyses/{aid}/criteria")).json()["items"]
    assert any(c["name"] == "유지보수 · AS" for c in crit)


async def test_ac55_ac56_revert_all_and_discard(env):
    aid = await full_fb(env)
    setup_revise(env)
    view = await _revision(env, aid)
    rid = view["revision"]["id"]
    v = (await env.c.post(f"/v1/analyses/{aid}/revisions/{rid}/revert-all")).json()
    assert v["changed_count"] == 0
    r = await env.c.post(f"/v1/analyses/{aid}/revisions/{rid}/apply")
    assert r.status_code == 422
    r = await env.c.post(f"/v1/analyses/{aid}/revisions/{rid}/discard")
    assert r.status_code == 204
    view = (await env.c.get(f"/v1/analyses/{aid}/revisions/{rid}")).json()
    assert view["revision"]["status"] == "discarded"
    assert (await env.c.get(f"/v1/analyses/{aid}")).json()["version"] == 1


async def test_ac57_version_conflict(env):
    aid = await full_fb(env)
    setup_revise(env)
    view = await _revision(env, aid)
    await env.c.post(f"/v1/analyses/{aid}/fix-items/apply", json={"carry_remaining": True})
    r = await env.c.post(f"/v1/analyses/{aid}/revisions/{view['revision']['id']}/apply")
    assert r.status_code == 409 and r.json()["error"]["code"] == "VERSION_CONFLICT"


async def test_rounds_accumulate(env):
    aid = await full_fb(env)
    setup_revise(env)
    view = await _revision(env, aid)
    rid = view["revision"]["id"]
    env.ai.llm["mi.revise_interpret"] = {"operations": [{"op": "remove_competitor", "target": "경쟁사 C", "detail": ""}]}
    r = await env.c.post(f"/v1/analyses/{aid}/revisions/{rid}/rounds", json={"instruction": "경쟁사 C 빼기"})
    assert r.status_code == 202
    await env.drain()
    view = (await env.c.get(f"/v1/analyses/{aid}/revisions/{rid}")).json()
    assert view["changed_count"] == 4 and view["chips"].get("row_remove") == 1
    assert len(view["revision"]["rounds"]) == 2


async def test_ac58_followups(env):
    aid = await full_fb(env)
    env.ai.reset_calls()
    env.ai.llm["mi.followup_intent"] = {"intent": "question"}
    env.ai.llm["mi.answer"] = {"answer_md": "가맹점주는 메뉴 교체 부담을 장벽으로 봐요 [1].", "citations": [1, 9], "answerable": True}
    r = await env.c.post(f"/v1/analyses/{aid}/followups", json={"text": "가맹점주 입장에서의 도입 장벽은?", "tab": "user"})
    out = r.json()
    assert out["intent"] == "question" and out["answer_md"] and [c["n"] for c in out["citations"]] == [1]
    assert env.ai.web_calls() == []
    env.ai.llm["mi.followup_intent"] = {"intent": "revision", "area": "competitor", "instruction": "경쟁사 B 빼줘"}
    env.ai.llm["mi.revise_interpret"] = {"operations": [{"op": "remove_competitor", "target": "경쟁사 B", "detail": ""}]}
    r = await env.c.post(f"/v1/analyses/{aid}/followups", json={"text": "경쟁사 B 빼줘", "tab": "competitor"})
    out = r.json()
    assert out["intent"] == "revision" and out["revision_id"] and out["scope"] == {"kind": "area", "area": "competitor"}
    await env.drain()
    view = (await env.c.get(f"/v1/analyses/{aid}/revisions/{out['revision_id']}")).json()
    assert view["chips"] == {"row_remove": 1}
    r = await env.c.post(f"/v1/analyses/{aid}/revisions/{out['revision_id']}/apply")
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert [c["label"] for c in res["competitor"]["table"]["columns"]] == ["경쟁사 A", "경쟁사 C", "삼성"]
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert next(c for c in a["competitors"] if c["letter"] == "B")["removed"] is True
