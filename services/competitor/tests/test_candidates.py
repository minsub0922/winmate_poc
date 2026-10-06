"""후보 확인(CA2) — AC-CA-18 ~ 26 · 신뢰 · 배지 · 상한 · 고정 · 직접 추가."""
from __future__ import annotations

from typing import Any

import pytest
from ca_scenario import CONF, NAMES, find, slots_json, use_a_coffee
from winmate_competitor import rules
from winmate_competitor import store as R


async def cands(env, aid: str) -> dict[str, Any]:
    return (await env.c.get(f"/v1/analyses/{aid}/candidates")).json()


def by_name(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {c["real_name"]: c for c in items}


# ── AC-CA-18 배지 · 글자 · 문장 ──────────────────────────
async def test_ac18_badges_letters_header(env):
    use_a_coffee(env)
    aid = await find(env)
    out = await cands(env, aid)
    items = out["items"]
    assert [c["letter"] for c in items] == ["A", "B", "C", "D", "E", "F"]
    assert [c["real_name"] for c in items] == NAMES
    assert [c["confidence"] for c in items] == CONF
    assert [c["confidence_label"] for c in items] == ["0.91", "0.86", "0.78", "0.74", "0.52", "0.31"]
    assert [c["status_label"] for c in items] == ["추천", "추천", "추천", "추천", "확인 필요", "제외 제안"]
    assert [c["on"] for c in items] == [True, True, True, True, False, False]
    assert [c["display"] for c in items] == [f"경쟁사 {x}" for x in "ABCDEF"]
    assert items[0]["switch_label"] == "경쟁사 A 빼기" and items[4]["switch_label"] == "경쟁사 E 넣기"
    assert out["counts"]["on"] == 4 and out["counts"]["rec"] == 4 and out["counts"]["check"] == 1 and out["counts"]["drop"] == 1
    assert out["header"]["desc"] == "입력에서 읽은 4가지로 후보 6곳을 찾았어요. 추천 4곳은 켜 두었고, 빼거나 더할 수 있어요."
    assert out["header"]["title"] == "이 경쟁사들로 분석할까요?"
    # 근거 칩(신호 ≥ 0.5) — 업종 · 장소 · 제품 · 고객사 순
    assert items[0]["chips"] == ["업종", "장소", "제품"]


# ── AC-CA-19 경계 ────────────────────────────────────────
@pytest.mark.parametrize("conf,status", [(0.70, "rec"), (0.69, "check"), (0.50, "check"), (0.49, "drop"), (0.695, "rec"), (0.4949, "drop")])
def test_ac19_boundaries(conf, status):
    assert rules.status_for(conf) == status


def test_confidence_formula():
    sig = {"industry": {"s": 1.0}, "product": {"s": 1.0}, "place": {"s": 0.95}, "customer": {"s": 0.45}}
    assert rules.confidence(sig, ["industry", "product", "place", "customer"]) == 0.91
    # 없는 신호는 가중치에서 뺀다(Σ w·s / Σ w)
    assert rules.confidence({"industry": {"s": 0.6}, "product": {"s": 0.9}}, ["industry", "product"]) == round((0.18 + 0.36) / 0.7, 2)


# ── AC-CA-20 더 보기 ────────────────────────────────────
async def test_ac20_more_than_page(env):
    names = [f"{c}{c} 사이니지" for c in "가나다라마바사아자"]
    sig = [(0.9, 0.9, 0, 0, False)] * 6 + [(0.2, 0.2, 0, 0, False)] * 3
    use_a_coffee(env, names=names, signals=sig, slots=slots_json(customer=None, place=None, region=None), segment={"FB": 0.8, "RT": 0.4})
    aid = await find(env, "카페 메뉴보드 55인치 사이니지")
    out = await cands(env, aid)
    assert out["total"] == 9 and out["page_size"] == 6
    assert len(out["items"]) == 9                                            # 웹이 6행 + `후보 3곳 더 보기`


# ── AC-CA-21 상한 ───────────────────────────────────────
async def test_ac21_caps_all_signals(env):
    names = [f"{c}{c} 디스플레이" for c in "가나다라마바사아자차카타"]
    sig = [(0.9, 0.9, 0.9, 0.9, False)] * 7 + [(0.2, 0.2, 0.2, 0.2, False)] * 5
    use_a_coffee(env, names=names, signals=sig)
    aid = await find(env)
    items = (await cands(env, aid))["items"]
    assert sum(1 for c in items if c["status"] in ("rec", "check")) == 5
    assert sum(1 for c in items if c["status"] == "drop") == 3


async def test_ac21_caps_industry_only(env):
    names = [f"{c}{c} 디스플레이" for c in "가나다라마바사아자차카타파하"]
    sig = [(0.9, 0.9, 0, 0, False)] * 14
    use_a_coffee(env, names=names, signals=sig, slots=slots_json(customer=None, place=None, region=None, product=None),
                 segment={"FB": 0.8, "RT": 0.4})
    aid = await find(env, "카페 프랜차이즈 경쟁사 알아보기")
    a = (await env.c.get(f"/v1/analyses/{aid}")).json()
    assert a["slots"]["product"]["origin"] == "inferred"
    items = (await cands(env, aid))["items"]
    assert sum(1 for c in items if c["status"] in ("rec", "check")) == 12


# ── AC-CA-22 · 23 신호 상한 ──────────────────────────────
async def test_ac22_summary_only_cap(env):
    sig = [(0.9, 0.9, 0.9, 0.9, False)] + [(0.9, 0.7, 0.5, 0.2, False)] * 5
    use_a_coffee(env, signals=sig, sources_mode=False)
    aid = await find(env)
    doc = await R.call(R.get_analysis, aid)
    zz = next(c for c in doc["competitors"] if c["real_name"] == "ZZ 사이니지")
    # 업종 신호가 사내 사례 DB(K1) 근거 없이 웹 검색 요약(E1)뿐 → 0.9 → 0.7
    assert zz["signals"]["industry"]["s"] == 0.7
    assert zz["signals"]["product"]["s"] == 0.7
    assert zz["confidence"] == 0.7


async def test_ac22_kb_evidence_not_capped(env):
    use_a_coffee(env, sources_mode=False)
    sc = env.ai.llm["ca.score_signals"]
    sc["candidates"][0]["signals"]["industry"]["source_ids"] = ["K1"]
    aid = await find(env)
    doc = await R.call(R.get_analysis, aid)
    zz = next(c for c in doc["competitors"] if c["real_name"] == "ZZ 사이니지")
    assert zz["signals"]["industry"]["s"] == 1.0


async def test_ac23_partial_product(env):
    use_a_coffee(env)
    aid = await find(env)
    items = by_name((await cands(env, aid))["items"])
    vv = items["VV 클라우드"]
    assert vv["why"].endswith("(제품 일부 겹침)")
    doc = await R.call(R.get_analysis, aid)
    raw = next(c for c in doc["competitors"] if c["real_name"] == "VV 클라우드")
    assert raw["signals"]["product"]["s"] <= 0.6 and raw["signals"]["product"]["partial"] is True


async def test_signal_without_evidence_is_zero(env):
    use_a_coffee(env)
    env.ai.llm["ca.score_signals"]["candidates"][1]["signals"]["place"]["source_ids"] = ["E99"]
    aid = await find(env)
    doc = await R.call(R.get_analysis, aid)
    ww = next(c for c in doc["competitors"] if c["real_name"] == "WW 디스플레이")
    assert ww["signals"]["place"]["s"] == 0


# ── AC-CA-24 다시 찾기에도 고정 ──────────────────────────
async def test_ac24_pins_survive_refind(env):
    use_a_coffee(env)
    aid = await find(env)
    items = by_name((await cands(env, aid))["items"])
    e, b = items["TT 디스플레이"], items["WW 디스플레이"]
    r = await env.c.patch(f"/v1/analyses/{aid}/candidates/{e['id']}", json={"on": True})
    assert r.status_code == 200 and r.json()["on"] and r.json()["pinned"]
    r = await env.c.patch(f"/v1/analyses/{aid}/candidates/{b['id']}", json={"on": False})
    assert r.status_code == 200 and not r.json()["on"]
    letters = {c["real_name"]: c["letter"] for c in (await cands(env, aid))["items"]}
    r = await env.c.post(f"/v1/analyses/{aid}/find")
    assert r.status_code == 202
    await env.drain()
    after = by_name((await cands(env, aid))["items"])
    assert after["TT 디스플레이"]["on"] is True and after["TT 디스플레이"]["pinned"]
    assert after["WW 디스플레이"]["on"] is False and after["WW 디스플레이"]["pinned"]
    assert {n: c["letter"] for n, c in after.items()} == letters


# ── AC-CA-25 직접 추가 ──────────────────────────────────
async def test_ac25_add_and_duplicate(env):
    use_a_coffee(env, names=NAMES[1:])
    aid = await find(env)
    before = (await cands(env, aid))["items"]
    assert [c["letter"] for c in before] == ["A", "B", "C", "D", "E"]
    url = "https://example.com/zz"
    env.ai.pages[url] = {"text": "ZZ 사이니지(ZZ Signage)는 실내외 상업용 사이니지를 제조하고 원격 관리 소프트웨어를 판다.", "title": "ZZ 사이니지"}
    env.ai.web["ca.web_profile"] = {"summary": "ZZ 사이니지(ZZ Signage)는 실내외 상업용 사이니지를 제조한다.", "sources": [{"url": url, "title": "ZZ"}]}
    env.ai.llm["ca.candidate_profile"] = {"kind_label": "실내외 상업용 사이니지 제조", "why": "원격 관리 소프트웨어 함께 판매", "evidence_id": "E1",
                                          "evidence_quote": "실내외 상업용 사이니지를 제조하고", "aliases": ["ZZ Signage", "지어낸 별칭"]}
    r = await env.c.post(f"/v1/analyses/{aid}/candidates", json={"name": "ZZ 사이니지"})
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["job_id"] and body["competitor_id"]
    items = by_name((await cands(env, aid))["items"])
    zz = items["ZZ 사이니지"]
    assert zz["letter"] == "F" and zz["on"] and zz["pinned"] and zz["origin"] == "user"
    assert zz["status_label"] == "직접 추가" and zz["add_state"] == "pending"
    await env.drain()
    zz = by_name((await cands(env, aid))["items"])["ZZ 사이니지"]
    assert zz["add_state"] == "done" and zz["kind_label"] == "실내외 상업용 사이니지 제조"
    assert zz["aliases"] == ["ZZ Signage"]                                   # 근거에 없는 별칭은 버린다
    for dup in ("ZZ사이니지", "(주)ZZ 사이니지", "ZZ Signage"):
        r = await env.c.post(f"/v1/analyses/{aid}/candidates", json={"name": dup})
        assert r.status_code == 409, dup
        assert r.json()["error"]["code"] == "DUPLICATE_COMPETITOR"
        assert r.json()["error"]["message"] == "이미 있는 경쟁사예요"


async def test_add_profile_failure_keeps_row(env):
    use_a_coffee(env)
    aid = await find(env)
    env.ai.web["ca.web_profile"] = {"error": {"status": 503, "code": "UPSTREAM_UNAVAILABLE", "message": "장애"}}
    r = await env.c.post(f"/v1/analyses/{aid}/candidates", json={"name": "QQ 미디어"})
    assert r.status_code == 202
    await env.drain()
    qq = by_name((await cands(env, aid))["items"])["QQ 미디어"]
    assert qq["on"] and qq["add_state"] in ("done", "failed")


async def test_remove_and_restore_candidate(env):
    use_a_coffee(env)
    aid = await find(env)
    items = by_name((await cands(env, aid))["items"])
    r = await env.c.patch(f"/v1/analyses/{aid}/candidates/{items['SS 미디어']['id']}", json={"on": True})
    assert r.status_code == 200 and r.json()["on"]
    r = await env.c.patch(f"/v1/analyses/{aid}/candidates/cmp_none", json={"on": True})
    assert r.status_code == 404


# ── AC-CA-26 켜진 후보 0 ─────────────────────────────────
async def test_ac26_no_competitors(env):
    use_a_coffee(env)
    aid = await find(env)
    for c in (await cands(env, aid))["items"]:
        if c["on"]:
            await env.c.patch(f"/v1/analyses/{aid}/candidates/{c['id']}", json={"on": False})
    out = await cands(env, aid)
    assert out["counts"]["on"] == 0
    r = await env.c.post(f"/v1/analyses/{aid}/runs", json={"mode": "full"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_COMPETITORS"
