"""작업 목록(CA0) · 30일 재확인 · 다시 분석 — AC-CA-48 ~ 50."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any

from ca_scenario import NAMES, SIGNALS, analyze, find, use_a_coffee, use_facts
from winmate_common.jobs import jobs
from winmate_competitor import store as R


def news(env, *, who: str | None, date: str = "2026-09-02") -> None:
    """재확인 — who 의 신제품 소식(분석일 뒤), 나머지는 소식 없음."""
    def web(body: dict[str, Any]) -> dict[str, Any]:
        q = body["query"]
        name = next((n for n in NAMES if n in q), "기타")
        url = f"https://example.com/news/{abs(hash(name)) % 10**6}"
        text = f"{name} 는 {date} 실외형 고휘도 사이니지 신제품을 출시했다." if name == who else f"{name} 관련 새 소식 없음."
        env.ai.pages[url] = {"text": text, "title": f"{name} 소식", "published_at": date}
        return {"summary": text, "sources": [{"url": url, "title": f"{name} 소식"}]}

    def llm(body: dict[str, Any]) -> dict[str, Any]:
        if who and f"'{who}'" in body["prompt"]:
            return {"items": [{"product": f"{who} 실외형 고휘도 사이니지", "date": date, "summary": f"{who} 가 실외형 고휘도 사이니지를 출시",
                               "quote": "실외형 고휘도 사이니지 신제품을 출시했다"}]}
        return {"items": []}

    env.ai.web["ca.web_recheck"] = web
    env.ai.llm["ca.recheck_news"] = llm


async def done_at(env, monkeypatch, day: str, *, title: str | None = None) -> str:
    monkeypatch.setenv("CA_TODAY", day)
    use_a_coffee(env)
    if title:
        env.ai.llm["ca.title"] = {"title": title}
    aid = await find(env)
    use_facts(env)
    a = await analyze(env, aid)
    assert a["status"] == "done"
    return aid


# ── AC-CA-49 예약 · 재확인 ───────────────────────────────
async def test_ac49_schedule_and_recheck(env, monkeypatch):
    aid = await done_at(env, monkeypatch, "2026-08-20")
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    sch = await jobs().schedules(service="competitor", ref=aid)
    assert len(sch) == 1 and sch[0]["kind"] == "ca.recheck" and sch[0]["payload"] == {"analysis_id": aid}
    analyzed = datetime.fromisoformat(a["analyzed_at"].replace("Z", "+00:00"))
    assert abs(sch[0]["run_at"] - (analyzed + timedelta(days=30)).timestamp()) < 1
    assert a["next_recheck_at"].startswith("2026-09-19")
    # 소식 0건 → done 유지 · 30일 뒤 다시 예약
    monkeypatch.setenv("CA_TODAY", "2026-09-19")
    news(env, who=None)
    assert (await env.c.post(f"/v1/analyses/{aid}/recheck")).status_code == 202
    await env.drain()
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "done" and a["next_recheck_at"].startswith("2026-10-19")
    sch = await jobs().schedules(service="competitor", ref=aid)
    assert len(sch) == 1 and datetime.fromtimestamp(sch[0]["run_at"]).date().isoformat() >= "2026-10-18"
    # 분석일보다 앞선 소식은 바뀜이 아니다
    news(env, who=NAMES[1], date="2026-08-01")
    await env.c.post(f"/v1/analyses/{aid}/recheck")
    await env.drain()
    assert (await env.c.get(f"/v1/analyses/{aid}")).json()["status"] == "done"
    # 분석일 뒤 신제품 1건 → upd
    news(env, who=NAMES[1])
    await env.c.post(f"/v1/analyses/{aid}/recheck")
    await env.drain()
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["status"] == "upd"
    ch = (await env.c.get(f"/v1/analyses/{aid}/changes")).json()
    assert len(ch["items"]) == 1 and ch["items"][0]["letter"] == "B" and ch["items"][0]["date"] == "2026-09-02"
    assert ch["items"][0]["verification"] == "matched"
    assert NAMES[1] not in json.dumps(ch, ensure_ascii=False)                 # 요약 · 제품 이름에도 실명 대신 글자
    # 알림 문장에 실명 없음(AC-CA-47)
    doc = await R.call(R.get_analysis, aid)
    notes = [d for _, d in await jobs().notifications(doc["owner_id"])]
    mine = [n for n in notes if n.get("ref") == aid and n.get("type") == "ca_update"]
    assert mine and mine[0]["message"].startswith("경쟁사 B 가 2026.09 신제품을 냈어요 — ")
    assert not any(n in json.dumps(mine, ensure_ascii=False) for n in NAMES)


# ── AC-CA-48 목록 ───────────────────────────────────────
async def test_ac48_list_rows_and_banner(env, monkeypatch):
    x = await done_at(env, monkeypatch, "2026-08-20")
    # 확인 중: 추천 3 · 확인 필요 2 · 후보 5
    names = ["가나 디스플레이", "다라 사이니지", "마바 클라우드", "사아 키오스크", "자차 디스플레이"]
    use_a_coffee(env, names=names, signals=[SIGNALS[0], SIGNALS[1], SIGNALS[2], SIGNALS[4], SIGNALS[4]])
    y = await find(env)
    # 업데이트 필요: C 물류센터
    z = await done_at(env, monkeypatch, "2026-08-20", title="C 물류센터 관제 디스플레이 경쟁사")
    monkeypatch.setenv("CA_TODAY", "2026-09-19")
    news(env, who=NAMES[1])
    await env.c.post(f"/v1/analyses/{z}/recheck")
    await env.drain()
    lst = (await env.c.get("/v1/analyses")).json()
    assert lst["header"] == "분석 3건 · 업데이트 필요 1건 · 경쟁사는 실명 없이 A · B · C 로 표기해요"
    assert lst["counts"] == {"all": 3, "done": 2, "check": 1, "upd": 1}
    rows = {r["id"]: r for r in lst["items"]}
    rx, ry, rz = rows[x], rows[y], rows[z]
    assert re.fullmatch(r"출처 \d+ · 삼성 강점 [1-3]", rx["note"]), rx["note"]
    assert (rx["count_label"], rx["count_unit"], rx["action"]["label"], rx["status_label"]) == ("4", "곳", "결과 보기", "완료")
    assert ry["note"] == "추천 3 · 확인 필요 2"
    assert (ry["count_label"], ry["count_unit"], ry["action"]["label"], ry["status_label"]) == ("5", "후보", "이어서", "확인 중")
    assert rz["note"] == "완료 · 경쟁사 B 신제품 2026.09"
    assert (rz["count_label"], rz["count_unit"], rz["action"]["label"], rz["status_label"]) == ("4", "곳", "상세 보기", "업데이트 필요")
    b_id = next(c["competitor_id"] for c in (await env.c.get(f"/v1/analyses/{z}/changes")).json()["items"])
    assert rz["action"]["route"] == f"/competitor/{z}/competitors/{b_id}"
    assert lst["banner"]["title"] == "1건은 다시 분석을 권해요."
    assert lst["banner"]["text"] == "경쟁사 B 가 2026.09 신제품을 냈어요 — C 물류센터 관제 디스플레이 경쟁사 · 분석 30일 경과"
    assert lst["banner"]["target_id"] == z and lst["banner"]["competitor_ids"] == [b_id]
    # 필터
    done = (await env.c.get("/v1/analyses", params={"status": "done"})).json()
    assert {r["id"] for r in done["items"]} == {x, z}
    check = (await env.c.get("/v1/analyses", params={"status": "check"})).json()
    assert {r["id"] for r in check["items"]} == {y}
    found = (await env.c.get("/v1/analyses", params={"q": "물류"})).json()
    assert [r["id"] for r in found["items"]] == [z]
    assert not any(n in json.dumps(lst, ensure_ascii=False) for n in NAMES + names)


# ── AC-CA-50 배너 `다시 분석` ────────────────────────────
async def test_ac50_rerun_changed_only(env, monkeypatch):
    z = await done_at(env, monkeypatch, "2026-08-20")
    monkeypatch.setenv("CA_TODAY", "2026-09-19")
    news(env, who=NAMES[1])
    await env.c.post(f"/v1/analyses/{z}/recheck")
    await env.drain()
    lst = (await env.c.get("/v1/analyses")).json()
    ids = lst["banner"]["competitor_ids"]
    n = len(env.ai.web_calls("ca.web_facts"))
    r = await env.c.post(f"/v1/analyses/{z}/runs", json={"mode": "changed_only", "competitor_ids": ids})
    assert r.status_code == 202
    a = (await env.c.get(f"/v1/analyses/{z}")).json()
    assert a["status"] == "analyzing" and a["route"] == f"/competitor/{z}/run"
    await env.drain()
    qs = [c["query"] for c in env.ai.web_calls("ca.web_facts")[n:]]
    assert qs and all(NAMES[1] in q for q in qs), qs
    a = (await env.c.get(f"/v1/analyses/{z}")).json()
    assert a["status"] == "done" and a["version"] == 2
    assert (await env.c.get(f"/v1/analyses/{z}/changes")).json()["items"] == []
    vers = (await env.c.get(f"/v1/analyses/{z}/versions")).json()["items"]
    assert vers[0]["kind"] == "changed_only"


async def test_delete_and_owner(env, monkeypatch):
    use_a_coffee(env)
    aid = await find(env)
    r = await env.c.delete(f"/v1/analyses/{aid}")
    assert r.status_code == 204
    assert (await env.c.get(f"/v1/analyses/{aid}")).status_code == 404
