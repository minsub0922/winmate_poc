#!/usr/bin/env python3
"""브라우저 엔진 이식 검증용 기준 출력(Python query.py) 생성 → dashboard/build/golden.json"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "build"))
from query import KB  # noqa: E402

S1Q = [
    "호텔 객실 TV를 통합 관리하고 싶어", "매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지", "주차장 입구 옥외에 설치할 실외 사이니지",
    "학교 교실에 판서가 되는 전자칠판", "물류센터 현장 작업자가 쓸 내구성 좋은 태블릿", "사무실 회의실에 직바람 없는 무풍 냉방",
    "병원 입원실 환자용 태블릿", "호텔 로비에 대형 비디오월", "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어",
    "카페 주문 공간에 메뉴보드와 키오스크", "은행 지점 대기공간에 순번 안내 디스플레이", "대학교 강의실 전자칠판과 회의실 화상회의",
    "아파트 거실과 침실에 조용한 시스템에어컨", "공장 생산 라인 작업자용 산업용 태블릿", "병원 로비 대기실 안내 사이니지와 진료실 모니터",
    "식당 주방 냉장고와 홀 에어컨", "관제 상황실 24시간 비디오월", "매장 여러 지점의 콘텐츠를 원격으로 중앙 관리",
    "군 병영 생활관 냉난방", "전시관 체험존 인터랙티브 터치 디스플레이", "영하 20도 냉동 창고에서 쓰는 태블릿",
    "오피스텔 실외기 소음", "호텔 연회장 대형 LED 월", "드라이브스루 옥외 메뉴보드 햇빛", "약국 카운터 전자가격표시기",
    "기업 보안 Knox 기기 관리 스마트폰", "LH85WMBWLGCXKR 전자칠판 85형", "학원 입구 안내 사이니지와 상담실 노트북",
    "공항 탑승대기실 안내 디스플레이", "대형 건물 에너지 절감 빌딩 통합 제어",
]
SEARCHQ = ["병상 태블릿 환자 소통", "호텔 객실 TV 원격 관리", "무풍 시스템에어컨 사무실", "전자칠판 판서 공유", "옥외 사이니지 고휘도",
           "냉장고 업소용", "비디오월 베젤", "키오스크 주문", "Knox 보안", "LED 사이니지 극장", "학교 교실 디스플레이", "매직인포 콘텐츠 스케줄"]
IMGQ = ["카페 천장에 설치된 시스템에어컨", "사무실 천장 무풍 시스템에어컨", "호텔 객실 TV", "매장 쇼윈도 사이니지", "교실 전자칠판",
        "병원 로비", "회의실 화상회의", "로비 비디오월"]
E3Q = [
    {"vertical": "kr_hotel"},
    {"vertical": "kr_hotel", "spaces": ["guest_room"]},
    {"text": "호텔 객실 TV를 통합 관리하고 로비에 대형 비디오월을 설치하고 싶어"},
    {"customer": "비즈니스호텔 체인", "text": "객실 TV 원격 관리"},
    {"products": [["category", "cat_smart-signage__videowall"]], "spaces": ["lobby"]},
    {"customer": "대학교"},
    {"text": "에너지 절감"},
    {"vertical": "kr_hospital", "products": [["category", "cat_tablets"]], "text": "병상에서 환자가 쓰는 태블릿"},
    {"vertical": "kr_school", "spaces": ["classroom"], "customer": "초등학교", "text": "전자칠판 판서 공유"},
    {"products": [["family", "fam_G000181564"]]},
    {"vertical": "kr_retail_fnb", "text": "매장 메뉴보드와 키오스크로 주문 대기를 줄이고 싶어"},
    {"customer": "프랜차이즈 카페 본사", "text": "여러 매장의 콘텐츠를 원격으로 중앙 관리"},
    {"vertical": "kr_office", "spaces": ["meeting_room"], "text": "직바람 없는 무풍 냉방과 화상회의"},
    {"products": [["solution", "sol_biot"]], "text": "빌딩 에너지 절감"},
    {"spaces": ["patient_room", "nurse_station"]},
    {},
]
A2Q = ["공장 생산 라인 작업자용 산업용 태블릿", "호텔 객실 TV", "병원 진료 대기실", "학교 교실", "은행 창구", "카페 주문", "아파트 거실 에어컨"]

kb = KB()
out = {"S1": [], "search": [], "image_search": [], "A2": [], "E3": []}
for q in S1Q:
    r = kb.S1(q)
    out["S1"].append({"q": q, "vertical": [(v["id"], v["score"]) for v in r["result"]["vertical"]],
                      "by_space": [{"space": p["space"], "category": p["category"], "hard": p["capabilities"]["hard"], "soft": p["capabilities"]["soft"],
                                    "fams": [(f["id"], f["score"]) for f in p["families"]], "sols": [s["id"] for s in p["solutions"]],
                                    "reasons": p["decision_reasons"]} for p in r["result"]["by_space"]],
                      "cases": [(d["id"], d["score"]) for d in r["result"]["similar_cases"]], "hint": r["decision_hint"],
                      "reasons": r["decision_reasons"]})
for q in SEARCHQ:
    r = kb.search(q, k=10)
    out["search"].append({"q": q, "tokens": r["result"]["tokens"], "chunks": [h["chunk_id"] for h in r["result"]["chunks"]],
                          "ents": [e["ref"] for e in r["result"]["entities"]],
                          "kw": [cid for cid, _ in kb.kw_search(" ".join(t for t in r["result"]["tokens"] if len(t) >= 3) or q, k=30)],
                          "vec": [ref for ref, _ in kb.vec_search(q, "chunk", 30)]})
for q in IMGQ:
    r = kb.image_search(q, limit=20)
    out["image_search"].append({"q": q, "ids": [i["id"] for i in r["result"]["images"]]})
for q in A2Q:
    r = kb.A2(q)
    out["A2"].append({"q": q, "cands": [(c["id"], c["score"]) for c in r["candidates"]], "hint": r["decision_hint"]})
for cx in E3Q:
    r = kb.E3(**{k: v for k, v in cx.items()})
    res = r["result"]
    c = res["context"]
    out["E3"].append({"ctx": cx, "vertical": c["vertical"], "spaces": [[s["id"], s["from"]] for s in c["spaces"]],
                      "products": [[p["kind"], p["id"], p["from"]] for p in c["products"]], "caps": [x["id"] for x in c["capabilities"]],
                      "missing": c["missing"], "weights": c["weights"],
                      "cust": [d["id"] for d in (c.get("customer") or {}).get("deployments", [])],
                      "headline": [h["id"] for h in res["headline"]], "km": [[k["id"], k["score"]] for k in res["key_messages"]],
                      "km_pp": [[p["id"] for p in k["proof_points"]] for k in res["key_messages"]],
                      "prods": [[p["id"], [i["id"] for i in p["items"]]] for p in res["products"]], "cases": [[d["id"], d["score"]] for d in res["cases"]],
                      "ranked": [[x["id"], x["score"], x["dup"]] for x in res["ranked"]], "n_scored": res["n_scored"], "n_candidates": res["n_candidates"],
                      "hint": r["decision_hint"], "reasons": r["decision_reasons"], "needs": r["needs_confirmation"]})
p = ROOT / "dashboard" / "build" / "golden.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=0))
print(p, {k: len(v) for k, v in out.items()})
