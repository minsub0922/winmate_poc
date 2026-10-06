#!/usr/bin/env python3
"""시나리오 테스트: docs/00_PURPOSE_SCENARIOS 의 수용 기준을 실제 KB 에 대한 질의로 확인한다.

python tests/test_scenarios.py            # docs/SCENARIO_TEST_REPORT.md 를 쓴다
기대값은 사이트에서 직접 확인한 사실(예: 호텔 업종 페이지의 객실 장면에 호텔TV가 추천됨)만 쓴다.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
from query import KB  # noqa: E402

REPORT = Path(os.environ.get("WKB_TEST_REPORT", ROOT / "docs" / "SCENARIO_TEST_REPORT.md"))
kb = KB()
c = sqlite3.connect(kb.c.execute("PRAGMA database_list").fetchone()[2])
RESULTS = []


def fam_cats(fid):
    return kb._family_cats(fid)


def nz(s):
    return re.sub(r"\s+", "", s or "")


def case(scenario, name, query, check, show):
    """check(result) -> (ok, detail); show(result) -> 사람이 읽을 요약 줄 목록."""
    try:
        r = query()
        ok, detail = check(r)
        lines = show(r)
    except Exception as e:  # noqa: BLE001
        ok, detail, lines, r = False, f"예외: {e!r}", [], None
    RESULTS.append({"scenario": scenario, "name": name, "pass": bool(ok), "detail": detail, "lines": lines,
                    "decision": (r or {}).get("decision_hint") if isinstance(r, dict) else None,
                    "reasons": (r or {}).get("decision_reasons") if isinstance(r, dict) else None})


# ── S1 요구사항 → 제품 ──────────────────────────────────────
def s1(text, expect_space, expect_cat=None, expect_cap=None, top=3):
    def q():
        return kb.S1(text)

    def check(r):
        ps = [p for p in r["result"]["by_space"] if p["space"] == expect_space]
        if not ps:
            return False, f"공간 {expect_space} 미검출: {[p['space'] for p in r['result']['by_space']]}"
        p = ps[0]
        fams = p["families"]
        if not fams:
            return False, "후보 없음"
        if expect_cap:
            bad = [f["name"] for f in fams if ("cap_" + expect_cap) not in f["satisfies"]]
            if bad:
                return False, f"hard 역량 미충족 후보: {bad[:3]}"
        if expect_cat:
            sub = kb._cat_subtree(expect_cat)
            hit = [f for f in fams[:top] if fam_cats(f["id"]) & sub]
            if not hit:
                return False, f"상위 {top}에 {expect_cat} 없음: {[f['name'] for f in fams[:top]]}"
        if any(not f["reasons"] for f in fams):
            return False, "근거 없는 후보"
        return True, f"후보 {len(fams)}, 상위: {fams[0]['name']}"

    def show(r):
        out = [f"업종 판별: {[(v['id'], v['score']) for v in r['result']['vertical']]} · 판단 {r['decision_hint']} {r['decision_reasons']}"]
        for p in r["result"]["by_space"]:
            out.append(f"공간 {p['space_name']}({p['space']}) · 카테고리 {p['category_name']} · hard {p['capabilities']['hard']} · soft {p['capabilities']['soft']}")
            for f in p["families"][:3]:
                out.append(f"  - {f['name']} [{f['model']}] {f['score']} · " + " / ".join(f["reasons"][:3]))
            if p["solutions"]:
                out.append("  솔루션: " + ", ".join(f"{s['name']}({s['via']})" for s in p["solutions"][:4]))
        return out
    case("S1", f"요구사항: {text}", q, check, show)


s1("호텔 객실 TV를 통합 관리하고 싶어", "guest_room", "cat_hotel-tvs", "hospitality_tv_mgmt")
s1("매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지", "storefront_window", "top_display", "sunlight_readable")
s1("주차장 입구 옥외에 설치할 실외 사이니지", "entrance", "top_display", "weatherproof")
s1("학교 교실에 판서가 되는 전자칠판", "classroom", "cat_smart-signage__flip", "touch_interactive")
s1("물류센터 현장 작업자가 쓸 내구성 좋은 태블릿", "warehouse", "cat_tablets__galaxy-tab-active", "rugged_mobile")
s1("사무실 회의실에 직바람 없는 무풍 냉방", "meeting_room", "top_hvac", "draft_free_cooling")
s1("병원 입원실 환자용 태블릿", "patient_room", "cat_tablets")
s1("호텔 로비에 대형 비디오월", "lobby", "cat_smart-signage__videowall")


# ── S2 업종·공간 → 장면 ─────────────────────────────────────
def s2(vertical, must_spaces):
    def check(r):
        sc = r["result"]["scenes"]
        sp = {x for s in sc for x in s["space_types"]}
        miss = [m for m in must_spaces if m not in sp]
        empty = [s["title"] for s in sc if not s["items"] and not s["description"] and not s["space_types"]]
        no_vp = [s["title"] for s in sc if not (s["value_props"]["key_messages"])]
        ok = not miss and not empty and not no_vp and r["result"]["hero"]
        return ok, f"장면 {len(sc)}, 공간 {sorted(sp)}, 누락 {miss}, 빈 장면 {empty[:2]}, 메시지 없는 장면 {no_vp[:2]}"

    def show(r):
        out = [f"히어로: {[(h['title']) for h in r['result']['hero']]}"]
        for s in r["result"]["scenes"][:8]:
            items = ", ".join(f"{i['name']}→{i['target_name'] or '미해소'}" for i in s["items"][:4])
            out.append(f"- [{', '.join(s['space_names']) or '공간 없음'}] {s['title']} · {items} · 이미지 {len(s['images'])}")
        out.append(f"유사 사례: {[d['title'][:25] for d in r['result']['similar_cases'][:3]]}")
        return out
    case("S2", f"업종 장면: {vertical}", lambda: kb.S2(vertical), check, show)


s2("kr_hotel", ["guest_room", "banquet_hall", "fitness", "front_desk"])
s2("kr_hospital", ["patient_room", "exam_room", "waiting_area", "operating_room"])
s2("kr_school", ["classroom", "teachers_office", "cafeteria"])
s2("kr_manufacturing", ["research_lab", "factory_floor", "warehouse", "sales_floor"])
s2("kr_fnb", ["order_counter", "dining_hall", "entrance"])


# ── S3 공간 → 제품 리스트 ──────────────────────────────────
def s3(space, vertical, expect_cats):
    def check(r):
        fams = r["result"]["families"]
        got = set()
        for f in fams:
            got |= fam_cats(f["id"])
        miss = [e for e in expect_cats if e not in got]
        return not miss and fams, f"제품군 {len(fams)}, 솔루션 {[s['name'] for s in r['result']['solutions'][:3]]}, 누락 카테고리 {miss}"

    def show(r):
        return [f"- {f['name']} · {f['category']} · " + " / ".join(f["reasons"][:2]) for f in r["result"]["families"][:6]]
    case("S3", f"공간별 제품: {space} @ {vertical}", lambda: kb.C2([], space=space, vertical=vertical, limit=40), check, show)


s3("guest_room", "kr_hotel", ["cat_hotel-tvs", "cat_airdresser"])
s3("classroom", "kr_school", ["cat_smart-signage__flip"])
s3("meeting_room", "kr_office", ["cat_smart-signage__flip"])


# ── S4 메시지 ─────────────────────────────────────────────
def verbatim_ok(items):
    bad = []
    for it in items:
        row = c.execute("""SELECT b.text FROM value_prop v JOIN occurrence o ON o.id=v.source_occurrence_id
                           JOIN document_block b ON b.id=o.block_id WHERE v.id=?""", (it["id"],)).fetchone()
        if row and nz(it["text"]) not in nz(row[0]) and nz(row[0]) not in nz(it["text"]):
            bad.append(it["text"][:30])
    return bad


fam_flip = c.execute("SELECT id FROM product_family WHERE name_ko LIKE 'Flip Pro%' LIMIT 1").fetchone()
if fam_flip:
    def chk_e1(r):
        km = r["result"]["tree"]["key_messages"]
        bad = verbatim_ok(km + [p for k in km for p in k.get("proof_points", [])])
        return km and any(k["proof_points"] for k in km) and not bad, f"key {len(km)}, usp {len(r['result']['tree']['usps'])}, 원문 불일치 {bad[:2]}"
    case("S4", "제품 메시지 계층(Flip Pro)", lambda: kb.E1(about=[("family", fam_flip[0])]), chk_e1,
         lambda r: [f"- {k['text']} → {[p['text'][:50] for p in k['proof_points']][:1]}" for k in r["result"]["tree"]["key_messages"][:5]])

case("S4", "업종 메시지 계층(호텔)", lambda: kb.E1(vertical="kr_hotel"),
     lambda r: (r["result"]["tree"]["taglines"] and len(r["result"]["tree"]["key_messages"]) >= 5
                and not verbatim_ok(r["result"]["tree"]["key_messages"]), f"tagline {len(r['result']['tree']['taglines'])}, key {len(r['result']['tree']['key_messages'])}"),
     lambda r: [f"tagline: {t['text']}" for t in r["result"]["tree"]["taglines"]] + [f"- {k['text']} ({k['about_name']})" for k in r["result"]["tree"]["key_messages"][:6]])
case("S4", "테마 검색: 에너지 절감", lambda: kb.E2("에너지 절감"),
     lambda r: (sum("에너지" in m["text"] for m in r["result"]["messages"][:10]) >= 6, f"상위 10 중 '에너지' 포함 {sum('에너지' in m['text'] for m in r['result']['messages'][:10])}"),
     lambda r: [f"- [{m['level']}] {m['text'][:60]} ({m['about_name']})" for m in r["result"]["messages"][:6]])


def e3_all(res):
    out = list(res["headline"]) + list(res["ranked"])
    for k in res["key_messages"]:
        out += [k] + k["proof_points"]
    for p in res["products"]:
        out += p["items"]
    for d in res["cases"]:
        out += d["quotes"]
    return out


def e3_show(r):
    res = r["result"]
    c = res["context"]
    head = [f"컨텍스트: 업종 {(c['vertical'] or {}).get('id')}({(c['vertical'] or {}).get('from')}) · 공간 {[s['id'] for s in c['spaces']]} · "
            f"제품 {[p['name'] for p in c['products']]} · 빠짐 {c['missing']}"]
    return (head + [f"헤드라인: {h['text']}" for h in res["headline"]]
            + [f"- {k['text'][:50]} ({k['about_name'][:20]}) {k['score']} · {' / '.join(k['reasons'][:3])}" for k in res["key_messages"][:5]]
            + [f"제품: {p['name']} {p['score']} — {p['items'][0]['text'][:40]}" for p in res["products"][:3]]
            + [f"사례: {d['title'][:40]} {d['score']} · {' / '.join(d['reasons'][:3])}" for d in res["cases"][:3]])


def chk_e3_full(r):
    res = r["result"]
    c = res["context"]
    bad = verbatim_ok(e3_all(res))
    hotel_tv = any("호텔 TV" in p["name"] for p in res["products"][:3])
    cust = any(d["signals"].get("customer") for d in res["cases"])
    ok = (all(x["from"] == "input" for x in [c["vertical"]] + c["spaces"]) and res["headline"] and len(res["key_messages"]) >= 5
          and hotel_tv and cust and not bad)
    return ok, f"헤드라인 {len(res['headline'])}, 핵심 {len(res['key_messages'])}, 제품 상위3 호텔 TV {hotel_tv}, 고객 일치 사례 {cust}, 원문 불일치 {bad[:2]}"


def chk_e3_infer(r):
    res = r["result"]
    c = res["context"]
    sp = {s["id"] for s in c["spaces"]}
    ok = ((c["vertical"] or {}).get("id") == "kr_hotel" and (c["vertical"] or {}).get("from") == "inferred" and {"guest_room", "lobby"} <= sp
          and any(p["id"] == "cat_smart-signage__videowall" for p in c["products"]) and any("추론" in n for n in r["needs_confirmation"])
          and not verbatim_ok(e3_all(res)))
    return ok, f"업종 {c['vertical']}, 공간 {sorted(sp)}, 제품 {[p['id'] for p in c['products']]}"


case("S4", "컨텍스트→메시지: 호텔·객실·비즈니스호텔 체인·요구사항(모두 입력)",
     lambda: kb.E3(vertical="kr_hotel", spaces=["guest_room"], customer="비즈니스호텔 체인", text="객실 TV를 통합 관리하고 투숙객 만족도를 높이고 싶어"),
     chk_e3_full, e3_show)
case("S4", "컨텍스트→메시지: 요구사항 문장만(업종·공간·제품 추론)",
     lambda: kb.E3(text="호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"), chk_e3_infer, e3_show)
case("S4", "컨텍스트→메시지: 제품만(비디오월 분류 + 로비)",
     lambda: kb.E3(products=[("category", "cat_smart-signage__videowall")], spaces=["lobby"]),
     lambda r: (r["result"]["products"] and all("비디오월" in p["name"] for p in r["result"]["products"][:3]) and not verbatim_ok(e3_all(r["result"])),
                f"제품 상위 {[p['name'] for p in r['result']['products'][:3]]}"), e3_show)
case("S4", "컨텍스트→메시지: 빈 컨텍스트 → 질문", lambda: kb.E3(),
     lambda r: (r["decision_hint"] == "ask" and not r["result"]["ranked"], f"hint {r['decision_hint']}"), lambda r: [])


# ── S5 이미지 ─────────────────────────────────────────────
def chk_g1(space):
    def f(r):
        imgs = r["result"]["images"]
        ok = imgs and all(i["sp"] == space and i["page_url"] and i["caption_rule"] for i in imgs) and r["fallback_level"] is None
        return ok, f"{len(imgs)}장, 등급 {sorted({i['grade_hint'] for i in imgs})}, 폴백 {r['fallback_level']}"
    return f


def show_imgs(r):
    return [f"- [{i['grade_hint']}] {i['url']} · {(i['alt'] or i['caption'] or '')[:50]} · {i['space_name']} · {i['caption_rule']}" for i in r["result"]["images"][:5]]


case("S5", "공간×카테고리 배치 이미지: 객실 × 호텔TV", lambda: kb.G1("guest_room", category="cat_hotel-tvs"),
     lambda r: (r["result"]["images"] and r["result"]["level"] in ("space+category",), f"{len(r['result']['images'])}장, 수준 {r['result']['level']}"), show_imgs)
case("S5", "공간 이미지: 회의실", lambda: kb.G1("meeting_room"), chk_g1("meeting_room"), show_imgs)
case("S5", "공간 이미지 폴백: 수술실 × 공기청정기", lambda: kb.G1("operating_room", category="cat_air-cleaners"),
     lambda r: (r["result"]["images"] and (r["fallback_level"] is None or r["fallback_level"]), f"수준 {r['result']['level']}, 폴백 {r['fallback_level']}"), show_imgs)
case("S5", "제품 설치 사진: 호텔TV", lambda: kb.G2("category", "cat_hotel-tvs"),
     lambda r: (any(i["rights"] == "customer_case" for i in r["result"]["images"]), f"{r['result']['n_total']}장, 사례 경유 {r['result']['via_deployments']}"), show_imgs)
case("S5", "이미지 검색: 카페 천장 시스템에어컨", lambda: kb.image_search("카페 천장에 설치된 시스템에어컨"),
     lambda r: (sum(1 for i in r["result"]["images"][:5] if re.search("카페|천장|시스템에어컨", (i["alt"] or "") + (i["caption"] or ""))) >= 3, "상위 5 중 관련 alt 3 이상"), show_imgs)


# ── S6 통합 엔티티 ─────────────────────────────────────────
case("S6", "솔루션 통합 보기: 링크 클라우드", lambda: kb.entity("solution", "sol_lynk_cloud"),
     lambda r: ("SOLD_AS" in r["result"]["edges_out"] and "DESCRIBED_BY" in r["result"]["edges_out"]
                and ("FEATURED_BY_SITE" in r["result"]["edges_in"] or "RECOMMENDED_BY_SITE" in r["result"]["edges_in"]),
                f"out {sorted(r['result']['edges_out'])}, in {sorted(r['result']['edges_in'])}, 언급 문서 {len(r['result']['mentions_by_source'])}"),
     lambda r: [f"- {m['page_type']} · {m['title'][:40]} · {m['n']}회" for m in r["result"]["mentions_by_source"][:6]])
fam_ht = c.execute("SELECT id FROM product_family WHERE category_id='cat_hotel-tvs' LIMIT 1").fetchone()
case("S6", "제품군 통합 보기: 호텔TV", lambda: kb.entity("family", fam_ht[0]),
     lambda r: (r["result"]["models"] and r["result"]["key_specs"] and r["result"]["value_props"],
                f"모델 {len(r['result']['models'])}, 핵심 스펙 {len(r['result']['key_specs'])}, 메시지 {len(r['result']['value_props'])}, 역량 {[p['capability_id'] for p in r['result']['provides']]}"),
     lambda r: [f"- {s['attr_name']}: {s['value_raw']}" for s in r["result"]["key_specs"][:6]])


# ── S7 스펙 판정 ───────────────────────────────────────────
out_fam = c.execute("""SELECT p.family_id FROM provides p WHERE p.capability_id='cap_sunlight_readable' LIMIT 1""").fetchone()
if out_fam:
    case("S7", "요구 스펙 대응표(고휘도 사이니지)", lambda: kb.C6(out_fam[0], [{"key": "brightness_nit", "op": ">=", "value": 2500},
                                                                     {"key": "operation_hours", "op": ">=", "value": 24},
                                                                     {"key": "pixel_pitch_mm", "op": "<=", "value": 1},
                                                                     {"key": "capacity_l", "op": ">=", "value": 100}]),
         lambda r: ({x["verdict"] for x in r["result"]["rows"]} <= {"pass", "fail", "unknown"} and r["result"]["rows"][3]["verdict"] == "unknown",
                    json.dumps([(x["attr"], x["actual"], x["verdict"]) for x in r["result"]["rows"]], ensure_ascii=False)),
         lambda r: [f"- {x['attr']} {x['required']} · 실제 {x['actual']} → {x['verdict']}" for x in r["result"]["rows"]])


# ── S8 유사 사례 ───────────────────────────────────────────
case("S8", "유사 사례: 호텔 객실 TV", lambda: kb.D1(vertical="kr_hotel", spaces=["guest_room"], targets=[("category", "cat_hotel-tvs")], text="호텔 객실 TV"),
     lambda r: (r["result"]["deployments"] and r["result"]["deployments"][0]["similarity_breakdown"]["vertical"] == 1.0,
                f"상위 {[d['title'][:20] for d in r['result']['deployments'][:3]]}"),
     lambda r: [f"- {d['title'][:45]} · {d['score']} · {d['similarity_breakdown']} · KPI {d['kpis_count']} · 사진 {d['has_photos']}" for d in r["result"]["deployments"][:5]])
case("S8", "성과 KPI: 호텔TV 사용 사례", lambda: kb.D3(target=("category", "cat_hotel-tvs")),
     lambda r: (r["result"]["count"] > 0 and all("claim_flag" in k for k in r["result"]["kpis"]), f"KPI {r['result']['count']}"),
     lambda r: [f"- {k['text'][:70]} ({k['title'][:20]})" for k in r["result"]["kpis"][:4]])
case("S8", "사례 통계: 교육", lambda: kb.D2(vertical="kr_education"),
     lambda r: (r["result"]["n"] > 0 and r["result"]["top_items"], f"사례 {r['result']['n']}"),
     lambda r: [f"- {t['name']} {t['n']}" for t in r["result"]["top_items"][:6]])


# ── S9 업종 판별 ───────────────────────────────────────────
GOLD = [("병원 입원실 환자용 태블릿", "kr_medical"), ("학교 교실 전자칠판", "kr_education"), ("호텔 객실 TV", "kr_hotel"),
        ("공장 물류센터 산업용 태블릿", "kr_manufacturing"), ("은행 지점 VIP 공간", "kr_finance"), ("아파트 커뮤니티 공간과 거실", "kr_construction"),
        ("매장 주문 공간 키오스크", "kr_retail_fnb"), ("병영 생활관 무풍 에어컨", "kr_public"), ("공항 라운지 사이니지", "kr_transport"),
        ("민원실 대기 공간 안내", "kr_public")]


def a2_top(text):
    r = kb.A2(text)
    tops = []
    for x in r["result"]["top2"]:
        p = c.execute("SELECT parent_id FROM vertical WHERE id=?", (x["id"],)).fetchone()
        tops.append(p[0] if p and p[0] else x["id"])
    return tops, r


def chk_a2(r):
    ok = sum(1 for t, g in GOLD if g in a2_top(t)[0][:2])
    return ok >= 8, f"top-2 정답 {ok}/{len(GOLD)}"


case("S9", "업종 판별 정확도(10문장)", lambda: None, lambda r: chk_a2(r),
     lambda r: [f"- {t} → {a2_top(t)[0]} (정답 {g})" for t, g in GOLD])


# ── S10 솔루션 구성(부분) ───────────────────────────────────
case("S10", "업종 추천 솔루션: 호텔", lambda: kb.B1("kr_hotel"),
     lambda r: ({"sol_lynk_cloud", "sol_biot"} <= {i["target"][1] for s in r["result"]["recommended"] for i in s["items"]},
                f"추천 {[i['target_name'] for s in r['result']['recommended'] for i in s['items']]}"),
     lambda r: [f"- {i['name']} → {i['target_name']}" for s in r["result"]["recommended"] for i in s["items"]])


# ── S13 검색 근거 ───────────────────────────────────────────
for qtext, must in [("객실 TV 원격 관리", "객실"), ("전자칠판 필기 공유", "필기"), ("무풍 냉방 직바람", "무풍"),
                    ("실외 사이니지 밝기", "밝기"), ("급식실 영양 정보 사이니지", "급식")]:
    case("S13", f"하이브리드 검색: {qtext}", lambda q=qtext: kb.search(q),
         lambda r, m=must: (any(m in ((h["section"] or "") + h["text"]) or h["coverage"] >= 0.99 for h in r["result"]["chunks"][:3])
                            and sum(h["coverage"] >= 0.5 for h in r["result"]["chunks"][:5]) >= 3 and all(h["url"] for h in r["result"]["chunks"]),
                            f"상위 3에 '{m}' · 상위 5 포괄도 {[h['coverage'] for h in r['result']['chunks'][:5]]}"),
         lambda r: [f"- {h['page_type']} · {h['section']} · {h['text'][:60]}" for h in r["result"]["chunks"][:4]])


# ── 리포트 ─────────────────────────────────────────────────
npass = sum(r["pass"] for r in RESULTS)
L = ["# 시나리오 테스트 결과", "", f"- 테스트 {len(RESULTS)}건 · 통과 {npass} · 실패 {len(RESULTS) - npass}",
     "- 실행: `python tests/test_scenarios.py` (LLM 없이 결정적 질의 패턴만 사용)", "",
     "| 시나리오 | 테스트 | 결과 | 상세 | 판단 |", "|---|---|---|---|---|"]
for r in RESULTS:
    L.append(f"| {r['scenario']} | {r['name']} | {'pass' if r['pass'] else 'FAIL'} | {r['detail'].replace('|', '/')} | {r['decision'] or ''} {r['reasons'] or ''} |")
L += ["", "## 결과 예시", ""]
for r in RESULTS:
    L += [f"### {r['scenario']} · {r['name']} — {'pass' if r['pass'] else 'FAIL'}", ""] + [x for x in r["lines"]] + [""]
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(L), encoding="utf-8")
if os.environ.get("WKB_TEST_JSON"):   # 대시보드용 결과(JSON)
    Path(os.environ["WKB_TEST_JSON"]).write_text(json.dumps(RESULTS, ensure_ascii=False, default=str), encoding="utf-8")
print(f"{npass}/{len(RESULTS)} pass")
for r in RESULTS:
    if not r["pass"]:
        print("FAIL", r["scenario"], r["name"], "::", r["detail"])
