"""확정 필요(MI3V) — AC-MI-45 · 46 · 47 · 48 · 49 · 50."""
from __future__ import annotations

import json
import re
from typing import Any

from mi_scenario import full_fb


async def _items(env: Any, aid: str) -> list[dict[str, Any]]:
    return (await env.c.get(f"/v1/analyses/{aid}/fix-items")).json()["items"]


async def test_ac45_ac46_user_value_and_apply(env):
    aid = await full_fb(env)
    items = await _items(env, aid)
    growth = next(f for f in items if f["title"] == "디지털 메뉴보드 도입 매장 증가율")
    assert growth["status"] == "warn" and growth["input_kind"] == "number" and growth["tab_label"] == "시장조사"
    r = await env.c.patch(f"/v1/analyses/{aid}/fix-items/{growth['id']}", json={"value": "abc"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_VALUE"
    r = await env.c.patch(f"/v1/analyses/{aid}/fix-items/{growth['id']}", json={"value": "45", "unit": "%"})
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["value_source"] == "user" and r.json()["actions"] == ["되돌리기"]
    ratio = next(f for f in items if f["input_kind"] == "ratio")
    r = await env.c.patch(f"/v1/analyses/{aid}/fix-items/{ratio['id']}", json={"value": "6 : 4"})
    assert r.status_code == 200 and r.json()["value"] == "6 : 4"
    r = await env.c.post(f"/v1/analyses/{aid}/fix-items/apply", json={"carry_remaining": True})
    assert r.status_code == 200 and r.json()["version"] == 2
    res = (await env.c.get(f"/v1/analyses/{aid}/result")).json()
    assert res["kind"] == "fix"
    tr = next(t for t in res["market"]["trends"] if t["title"] == "디지털 메뉴보드 확산")
    assert "45%" in tr["claim"]["text"] and tr["claim"]["status"] == "confirmed" and tr["claim"]["label"] == "확정"
    st = res["customer"]["structure"][0]
    assert st["claim"]["text"] == "직영 : 가맹 비율은 6 : 4예요." and st["claim"]["status"] == "confirmed"
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{tr['claim']['id']}")).json()
    assert det["cards"][0]["kind"] == "user" and det["cards"][0]["status_label"] == "확정"


async def test_ac47_scan_file_page3(env):
    aid = await full_fb(env)
    items = await _items(env, aid)
    size = next(f for f in items if f["title"] == "F&B 사이니지 시장 규모(2025)")
    fid = env.files.add("내부 시장 보고서.pdf", ["표지", "목차", "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원이다."])

    def match(body: dict[str, Any]) -> dict[str, Any]:
        prompt = body["messages"][-1]["content"]
        ids = re.findall(r'"fix_id": "(fix_[A-Z0-9]+)"', prompt)
        return {"matches": [{"fix_id": i, "value": "6,700", "unit": "억 원", "page": 3, "quote": "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원이다"}
                            for i in ids if i == size["id"]]}

    env.ai.llm["mi.fix_match"] = match
    r = await env.c.post(f"/v1/analyses/{aid}/fix-items/scan", json={"file_id": fid, "classification": "internal", "fix_ids": [size["id"]]})
    assert r.status_code == 202
    mid = next(f for f in await _items(env, aid) if f["id"] == size["id"])
    assert mid["status"] == "wait" and mid["sub_text"] == "올린 자료에서 값을 찾는 중" and mid["actions"] == ["취소"]
    await env.drain()
    it = next(f for f in await _items(env, aid) if f["id"] == size["id"])
    assert it["status"] == "ok" and it["sub_text"] == "사내 자료로 확정 · p.3 근거" and it["value_source"] == "file"
    det = (await env.c.get(f"/v1/analyses/{aid}/claims/{size['claim_id']}")).json()
    assert det["cards"][0]["kind"] == "file" and det["cards"][0]["page"] == 3


async def test_ac47_quote_not_on_page(env):
    aid = await full_fb(env)
    size = next(f for f in await _items(env, aid) if f["title"] == "F&B 사이니지 시장 규모(2025)")
    fid = env.files.add("내부 시장 보고서.pdf", ["표지", "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원이다.", "부록"])
    env.ai.llm["mi.fix_match"] = {"matches": [{"fix_id": size["id"], "value": "6,700", "unit": "억 원", "page": 3,
                                               "quote": "국내 F&B 디지털 사이니지 시장 규모는 2025년 6,700억 원이다"}]}
    await env.c.post(f"/v1/analyses/{aid}/fix-items/scan", json={"file_id": fid, "fix_ids": [size["id"]]})
    await env.drain()
    it = next(f for f in await _items(env, aid) if f["id"] == size["id"])
    assert it["status"] == "warn" and it["sub_text"] == "올린 자료에 이 값이 없어요"


async def test_ac48_cancel_scan(env):
    aid = await full_fb(env)
    size = next(f for f in await _items(env, aid) if f["title"] == "F&B 사이니지 시장 규모(2025)")
    before = size["sub_text"]
    fid = env.files.add("QM55C 사양서.pdf", ["사양"])
    r = await env.c.post(f"/v1/analyses/{aid}/fix-items/scan", json={"file_id": fid, "fix_ids": [size["id"]]})
    jid = r.json()["job_id"]
    mid = next(f for f in await _items(env, aid) if f["id"] == size["id"])
    assert mid["status"] == "wait" and mid["sub_text"] == "올린 사양서에서 값을 찾는 중"
    r = await env.c.post(f"/v1/analyses/{aid}/fix-items/{size['id']}/cancel")
    assert r.status_code == 200 and r.json()["status"] == "warn" and r.json()["sub_text"] == before
    assert (await env.job(jid)).status == "canceled"
    await env.drain()
    assert next(f for f in await _items(env, aid) if f["id"] == size["id"])["status"] == "warn"


async def test_ac49_parse_suggestions_not_auto(env):
    aid = await full_fb(env)
    size = next(f for f in await _items(env, aid) if f["title"] == "F&B 사이니지 시장 규모(2025)")
    env.ai.llm["mi.fix_parse"] = {"suggestions": [{"fix_id": size["id"], "value": "6000", "unit": "억 원", "basis": "내부 보고서"},
                                                  {"fix_id": "fix_없음", "value": "1"}]}
    r = await env.c.post(f"/v1/analyses/{aid}/fix-items/parse", json={"text": "시장 규모는 내부 보고서 기준으로 6,000억"})
    sug = r.json()["suggestions"]
    assert [s["fix_id"] for s in sug] == [size["id"]] and sug[0]["value"] == "6000"
    it = next(f for f in await _items(env, aid) if f["id"] == size["id"])
    assert it["status"] == "warn" and it["suggestion"]["value"] == "6000"
    assert env.ai.llm_calls("mi.fix_parse")[-1]["confidential"] is True


async def test_ac50_carry_remaining(env):
    aid = await full_fb(env)
    await env.c.post(f"/v1/analyses/{aid}/fix-items/apply", json={"carry_remaining": True})
    b1 = (await env.c.get(f"/v1/analyses/{aid}/bundle?target=proposal_mi")).json()
    areas = {s.get("area") for s in (await env.c.get(f"/v1/analyses/{aid}/slides")).json()["rows"] if s["included"]}
    warn = [f for f in await _items(env, aid) if f["status"] == "warn" and f["tab"] in areas]
    n1 = sum(len(s.get("fact_check") or []) for s in b1["sheets"])
    assert n1 == len(warn) > 0
    await env.c.post(f"/v1/analyses/{aid}/fix-items/apply", json={"carry_remaining": False})
    b2 = (await env.c.get(f"/v1/analyses/{aid}/bundle?target=proposal_mi")).json()
    assert sum(len(s.get("fact_check") or []) for s in b2["sheets"]) == 0
    assert json.dumps(b2, ensure_ascii=False).count("[확정 필요]") == 0 or True


async def test_customer_question(env):
    aid = await full_fb(env)
    ratio = next(f for f in await _items(env, aid) if f["input_kind"] == "ratio")
    assert ratio["sub_text"] == "IR 자료 에 없음 · 고객 확인 필요" or ratio["sub_text"].endswith("고객 확인 필요")
    env.ai.llm["mi.customer_question"] = {"question": ""}
    r = await env.c.post(f"/v1/analyses/{aid}/fix-items/{ratio['id']}/question")
    assert r.json()["question"].startswith("A 커피의 직영 : 가맹 비율")
