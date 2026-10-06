#!/usr/bin/env python3
"""docs/QUERY_COOKBOOK.md 생성: 질의 패턴마다 실제 KB 에 실행한 예시와 결과 요약을 싣는다."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
from query import KB  # noqa: E402

kb = KB()
OUT = ROOT / "docs" / "QUERY_COOKBOOK.md"
L = []


def sec(code, title, purpose, cli, py, run, fmt):
    r = run()
    L.extend([f"## {code} · {title}", "", purpose, "", "```bash", cli, "```", "", "```python", py, "```", "",
              f"결과 요약(판단 `{r.get('decision_hint')}` {r.get('decision_reasons')}, {r.get('timings_ms', {}).get('total')} ms):", "", "```"])
    L.extend(fmt(r))
    L.extend(["```", ""])


L += ["# 질의 예시 모음 (Query Cookbook)", "",
      "모든 예시는 `kb/winmate_kb.sqlite` 에 실제로 실행한 결과를 줄여 옮긴 것이다(`python tests/make_cookbook.py` 로 다시 생성).",
      "질의는 LLM 없이 결정적으로 동작한다. 결과는 공통 봉투(`pattern, result, evidence_paths, tier_min, candidates, decision_hint,",
      "decision_reasons, needs_confirmation, fallback_level, modes_used, timings_ms`)로 나온다.", "",
      "```python", "import sys; sys.path.insert(0, 'build')", "from query import KB", "kb = KB()          # kb/winmate_kb.sqlite", "```", "",
      "| 코드 | 이름 | 메서드 |", "|---|---|---|",
      "| search | 하이브리드 검색(키워드 + 벡터, 원문 청크·엔티티) | `kb.search(text)` |",
      "| A1 | 엔티티 링킹(모델코드·제품·카테고리·솔루션·업종·공간·역량) | `kb.A1(text)` |",
      "| A2 | 업종 판별(top-2, 애매하면 ask) | `kb.A2(text)` |",
      "| A3 | 요구 스펙 항목 → 정규 키 | `kb.A3([{name_raw, value_raw}])` |",
      "| B1 | 업종 프리셋(공간 시퀀스·장면·추천 솔루션·사례) | `kb.B1(vertical_id)` |",
      "| B2 | 요구사항 결핍 → 확인 질문 | `kb.B2(text)` |",
      "| C1 | 공간·요구 → 역량(hard/soft) | `kb.C1(spaces, text)` |",
      "| C2 | 후보 제품군(역량 충족 + 사이트 추천 + 선례 + 문장 유사도) | `kb.C2(caps, category, space, vertical, soft, text)` |",
      "| C3 | 제품 → 적합 업종·공간·사례(역방향) | `kb.C3(family_id)` |",
      "| C4 | 제외 사유 | `kb.C4(family_id, caps, category)` |",
      "| C6 | 요구 스펙 충족 판정(pass/fail/unknown) | `kb.C6(ref, requirements)` |",
      "| D1 | 유사 사례(업종·공간·제품·문장 분해 점수) | `kb.D1(vertical, spaces, targets, text)` |",
      "| D2 | 사례 통계 | `kb.D2(vertical=…)` / `kb.D2(space=…)` |",
      "| D3 | 성과 KPI | `kb.D3(deployment_ids, target)` |",
      "| D5 | 공존 패턴(함께 쓰인 제품·솔루션) | `kb.D5(targets)` |",
      "| E1 | 메시지 계층(tagline → key message → proof point) | `kb.E1(about, vertical, space, locale)` |",
      "| E2 | 테마로 메시지 찾기 | `kb.E2(theme)` |",
      "| E3 | 요구사항 컨텍스트(업종·공간·제품·타겟고객·요구사항, 모두 선택) → 메시지 묶음 | `kb.E3(vertical, spaces, products, customer, text)` |",
      "| G1 | 공간 × 카테고리 배치 이미지(폴백 포함) | `kb.G1(space, category, vertical)` |",
      "| G2 | 제품·카테고리가 나오는 이미지(사례 사진 우선) | `kb.G2(kind, id)` |",
      "| G4 | 제품 단독컷 | `kb.G4(family_id)` |",
      "| G5 | 사례 사진 | `kb.G5(deployment_id)` |",
      "| images | 이미지 검색(alt·캡션·맥락) | `kb.image_search(text)` |",
      "| entity | 엔티티 통합 보기(흩어진 정보 모음) | `kb.entity(kind, id)` |",
      "| S1 | 요구사항 → 공간별 추천(체인: A1·A2 → 절 단위 묶기 → C1 → C2 → D1) | `kb.S1(text)` |",
      "| S2 | 업종 → 장면 구성(체인: B1 → E1 → G1 → D1) | `kb.S2(vertical, space)` |", ""]

sec("S1", "요구사항 → 공간별 제품 추천",
    "요구 문장을 절 단위로 나눠 공간·카테고리·역량을 묶고, 공간마다 후보를 낸다. hard 역량을 못 채우면 후보에서 빠진다(실외·직사광은 완화 없음).",
    'python build/query.py S1 "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"',
    'kb.S1("호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어")',
    lambda: kb.S1("호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"),
    lambda r: [f"업종: {[(v['id'], v['score']) for v in r['result']['vertical']]}"] + sum(
        [[f"[{p['space_name']}] 절={p['clauses']} 카테고리={p['category_name']} hard={p['capabilities']['hard']}"]
         + [f"  {f['name']} ({f['model']}) {f['score']} — " + " / ".join(f['reasons'][:2]) for f in p['families'][:3]]
         + [f"  솔루션: {[s['name'] for s in p['solutions'][:3]]}"] for p in r['result']['by_space']], [])
    + [f"유사 사례: {[d['title'][:30] for d in r['result']['similar_cases'][:3]]}"])

sec("A1", "엔티티 링킹", "문장 안의 모델코드·제품·카테고리·솔루션·업종 표현과 공간·요구 키워드를 찾는다.",
    'python build/query.py A1 "병원 로비 대기실에 MagicINFO로 관리하는 24시간 사이니지"',
    'kb.A1("병원 로비 대기실에 MagicINFO로 관리하는 24시간 사이니지")',
    lambda: kb.A1("병원 로비 대기실에 MagicINFO로 관리하는 24시간 사이니지"),
    lambda r: [f"{l['surface']} → {l['type']}:{l['id']} ({l.get('name')}) conf={l['conf']} [{l['method']}]" for l in r['result']['links']])

sec("A2", "업종 판별", "업종명·공간·제품 신호와 문장 유사도로 KR 업종 top-2 를 낸다. 1·2위 차가 작으면 `ask`.",
    'python build/query.py A2 "공장 생산 라인 작업자용 산업용 태블릿"', 'kb.A2("공장 생산 라인 작업자용 산업용 태블릿")',
    lambda: kb.A2("공장 생산 라인 작업자용 산업용 태블릿"),
    lambda r: [f"{c['id']} {c['score']} {c['reasons']}" for c in r['candidates'][:4]])

sec("B1", "업종 프리셋", "업종 페이지 장면 순서를 공간 시퀀스로 쓰고, 장면별 추천 항목(링크로 해소된 제품·솔루션), 히어로 문구, 추천 솔루션, 대표 사례를 낸다.",
    "python build/query.py B1 kr_hospital", 'kb.B1("kr_hospital")', lambda: kb.B1("kr_hospital"),
    lambda r: [f"공간 시퀀스: {[x['name'] for x in r['result']['space_sequence']]}"]
    + [f"- {s['title']} [{', '.join(s['space_names'])}] → {[i['target_name'] for i in s['items'][:4]]}" for s in r['result']['scenes'][:6]]
    + [f"추천: {[i['target_name'] for s in r['result']['recommended'] for i in s['items']]}"])

sec("C2", "공간 × 역량 후보", "역량(presence 규칙)과 사이트 추천을 함께 본다. 예: 교실에서 터치가 되는 제품.",
    "python build/query.py C2 --caps touch_interactive --space classroom --vertical kr_school",
    'kb.C2(["touch_interactive"], space="classroom", vertical="kr_school")',
    lambda: kb.C2(["touch_interactive"], space="classroom", vertical="kr_school"),
    lambda r: [f"{f['name']} {f['score']} — " + " / ".join(f['reasons'][:3]) for f in r['result']['families'][:5]])

fam = kb.c.execute("SELECT id FROM product_family WHERE category_id='cat_tablets' AND name_ko LIKE '%액티브5 프로%' LIMIT 1").fetchone()[0]
sec("C3", "제품 → 적합 업종·공간(역방향)", "업종 페이지 추천과 도입사례로 이 제품(또는 소속 카테고리)이 쓰이는 곳을 찾는다.",
    f"python build/query.py C3 {fam}", f'kb.C3("{fam}")', lambda: kb.C3(fam),
    lambda r: [f"{x['vertical_name']} / {x['space_name']} via {x['via']} ({x['n_sections']}개 장면)" for x in r['result']['fits'][:6]]
    + [f"사례 {r['result']['precedent_count']}건: {[d['title'][:20] for d in r['result']['deployments'][:3]]}"])

hb = kb.c.execute("SELECT family_id FROM provides WHERE capability_id='cap_sunlight_readable' LIMIT 1").fetchone()[0]
sec("C6", "요구 스펙 충족 판정", "정규 스펙 키로 pass/fail 을 판정하고, 스펙이 없으면 추정하지 않고 unknown.",
    "", f'kb.C6("{hb}", [{{"key": "brightness_nit", "op": ">=", "value": 2500}}, {{"key": "operation_hours", "op": ">=", "value": 24}}, {{"key": "weight_kg", "op": "<=", "value": 20}}, {{"key": "capacity_l", "op": ">=", "value": 100}}])',
    lambda: kb.C6(hb, [{"key": "brightness_nit", "op": ">=", "value": 2500}, {"key": "operation_hours", "op": ">=", "value": 24},
                       {"key": "weight_kg", "op": "<=", "value": 20}, {"key": "capacity_l", "op": ">=", "value": 100}]),
    lambda r: [f"{x['attr']} {x['required']} · 실제 {x['actual']} → {x['verdict']}" for x in r['result']['rows']])

sec("D1", "유사 사례", "업종·공간·제품 겹침과 문장 유사도를 분해해서 보여 준다.",
    'python build/query.py D1 --vertical kr_education --space classroom "전자칠판 수업"',
    'kb.D1(vertical="kr_education", spaces=["classroom"], targets=[("category", "cat_smart-signage__flip")], text="전자칠판 수업")',
    lambda: kb.D1(vertical="kr_education", spaces=["classroom"], targets=[("category", "cat_smart-signage__flip")], text="전자칠판 수업"),
    lambda r: [f"{d['title'][:40]} {d['score']} {d['similarity_breakdown']} KPI={d['kpis_count']} 사진={d['has_photos']}" for d in r['result']['deployments'][:5]])

sec("D5", "공존 패턴", "사례에서 대상과 함께 쓰인 제품·솔루션(support·confidence·lift).",
    "", 'kb.D5([("category", "cat_hotel-tvs")])', lambda: kb.D5([("category", "cat_hotel-tvs")]),
    lambda r: [f"기준 사례 {r['result']['base_count']}"] + [f"{x['name']} support={x['support']} conf={x['confidence']} lift={x['lift']}" for x in r['result']['co_items'][:6]])

sec("E1", "메시지 계층", "업종·공간·제품별 원문 메시지를 tagline → key message → proof point 로 묶는다.",
    "python build/query.py E1 --vertical kr_hotel", 'kb.E1(vertical="kr_hotel")', lambda: kb.E1(vertical="kr_hotel"),
    lambda r: [f"tagline: {t['text']}" for t in r['result']['tree']['taglines']]
    + [f"- {k['text']} ({k['about_name']}) → {[p['text'][:40] for p in k['proof_points']][:1]}" for k in r['result']['tree']['key_messages'][:6]])

sec("E2", "테마로 메시지 찾기", "문장과 비슷한 원문 메시지와 그 대상(제품·솔루션)을 찾는다.",
    'python build/query.py E2 "에너지 절감과 원격 제어"', 'kb.E2("에너지 절감과 원격 제어")', lambda: kb.E2("에너지 절감과 원격 제어"),
    lambda r: [f"[{m['level']}] {m['text'][:60]} — {m['about_name']}" for m in r['result']['messages'][:6]])

sec("E3", "컨텍스트 → 메시지 묶음",
    "업종·공간·제품·타겟고객·요구사항(모두 선택)으로 원문 메시지를 헤드라인 → 핵심 메시지(+근거 문장) → 제품 메시지(제품군별) → 근거 사례(인용·KPI)로 뽑는다. "
    "비워 둔 업종·공간·제품은 타겟고객·요구사항 문장에서 추론한다(A2·공간 키워드·A1, 가중치 0.5배). "
    "점수 = Σ(가중치 × 일치도) ÷ Σ(쓴 항목 가중치), 가중치는 제품 0.35 · 업종 0.25 · 공간 0.2 · 타겟고객 0.15 · 문장 유사도 0.35(0.6×LSA + 0.4×토큰 포괄도). "
    "같은 문장(여러 제품군 공통 문구)은 하나로 묶고 `dup` 에 개수를 남긴다. 결과 문장은 모두 원문 그대로다.",
    'python build/query.py E3 --vertical kr_hotel --space guest_room --customer "비즈니스호텔 체인" --text "객실 TV를 통합 관리하고 투숙객 만족도를 높이고 싶어"',
    'kb.E3(vertical="kr_hotel", spaces=["guest_room"], customer="비즈니스호텔 체인",\n      text="객실 TV를 통합 관리하고 투숙객 만족도를 높이고 싶어")',
    lambda: kb.E3(vertical="kr_hotel", spaces=["guest_room"], customer="비즈니스호텔 체인", text="객실 TV를 통합 관리하고 투숙객 만족도를 높이고 싶어"),
    lambda r: [f"가중치 {r['result']['context']['weights']} · 빠진 항목 {r['result']['context']['missing']}"]
    + [f"헤드라인: {h['text']}" for h in r['result']['headline']]
    + [f"핵심 {k['score']}: {k['text'][:50]} ({k['about_name'][:24]}) ← {' / '.join(k['reasons'][:3])}" for k in r['result']['key_messages'][:5]]
    + [f"제품 {p['score']}: {p['name']} — {p['items'][0]['text'][:40]}" for p in r['result']['products'][:3]]
    + [f"사례 {d['score']}: {d['title'][:40]} ← {' / '.join(d['reasons'][:3])}" for d in r['result']['cases'][:3]])

sec("E3", "컨텍스트 → 메시지 묶음(요구사항 문장만)",
    "업종·공간·제품을 비우면 문장에서 추론한다. 추론한 값은 `context.*.from = inferred` 와 `needs_confirmation` 으로 표시된다.",
    'python build/query.py E3 --text "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"',
    'kb.E3(text="호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어")',
    lambda: kb.E3(text="호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"),
    lambda r: [f"업종 {r['result']['context']['vertical']}", f"공간 {[(s['id'], s['surface']) for s in r['result']['context']['spaces']]}",
               f"제품 {[(p['name'], p['surface']) for p in r['result']['context']['products']]}", f"확인 {r['needs_confirmation']}"]
    + [f"핵심 {k['score']}: {k['text'][:50]} ← {' / '.join(k['reasons'][:3])}" for k in r['result']['key_messages'][:4]])

sec("G1", "공간 × 카테고리 배치 이미지", "공간 맥락이 있는 이미지를 등급(A > A?C > …) 순으로. 없으면 공간만 → 카테고리 맥락 → 제품 컷 순으로 폴백하고 `fallback_level` 을 붙인다.",
    "python build/query.py G1 guest_room --category cat_hotel-tvs", 'kb.G1("guest_room", category="cat_hotel-tvs")',
    lambda: kb.G1("guest_room", category="cat_hotel-tvs"),
    lambda r: [f"수준 {r['result']['level']}"] + [f"[{i['grade_hint']}] {i['url']} · {(i['alt'] or '')[:40]} · {i['caption_rule']} · {i['page_url'][:60]}" for i in r['result']['images'][:5]])

sec("images", "이미지 검색", "alt·캡션·섹션·맥락 엔티티로 만든 이미지 문서를 검색한다.",
    'python build/query.py images "사무실 천장 무풍 시스템에어컨"', 'kb.image_search("사무실 천장 무풍 시스템에어컨")',
    lambda: kb.image_search("사무실 천장 무풍 시스템에어컨"),
    lambda r: [f"[{i['grade_hint']}] {(i['alt'] or i['caption'] or '')[:60]} · {i['space_name']}" for i in r['result']['images'][:5]])

sec("search", "하이브리드 검색", "trigram BM25 + 2글자 토큰 부분일치 + LSA 벡터를 RRF 로 합치고 토큰 포괄도로 재정렬한다. 결과마다 원문 URL·섹션.",
    'python build/query.py search "병상 태블릿 환자 소통"', 'kb.search("병상 태블릿 환자 소통")', lambda: kb.search("병상 태블릿 환자 소통"),
    lambda r: [f"{h['coverage']} {h['page_type']} · {h['section']} · {h['text'][:50]}" for h in r['result']['chunks'][:5]]
    + [f"엔티티: {[e['name'] for e in r['result']['entities'][:5]]}"])

sec("entity", "엔티티 통합 보기", "흩어진 정보(언급 문서, 메시지, 그래프 엣지)를 한 엔티티에 모은다.",
    "python build/query.py entity solution sol_magicinfo", 'kb.entity("solution", "sol_magicinfo")', lambda: kb.entity("solution", "sol_magicinfo"),
    lambda r: [f"out: {{k: len(v) for k, v in r['result']['edges_out'].items()}} = {({k: len(v) for k, v in r['result']['edges_out'].items()})}",
               f"in: {({k: len(v) for k, v in r['result']['edges_in'].items()})}"]
    + [f"- {m['page_type']} · {(m['title'] or '')[:40]} · {m['n']}회" for m in r['result']['mentions_by_source'][:6]])

OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("written", OUT)
