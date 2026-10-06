"""경쟁사 분석 mock 고정 응답 생성기 — A 커피 메뉴보드 시나리오(합성 회사 이름).

모든 인용 구절이 그 검색 요약 안에 글자 그대로 있는지 검사한 뒤 mocks/ai-tools/ca.*.json 으로 쓴다.
"""
import json
import sys
from pathlib import Path

# 쓰는 곳: 저장소 루트에서 `.venv/bin/python -I services/competitor/scripts/gen_mocks.py mocks/ai-tools`
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3] / "mocks" / "ai-tools"

# ── 찾기: 검색 요약(질의 키워드로 고름) ──────────────────
S_IND = "외식 · 카페 매장 디지털 메뉴보드 공급 업체로는 가나 디스플레이, 다라 사이니지, 사아 키오스크가 자주 거론된다. 카타 미디어는 매장 광고 매체를 운영한다."
S_PROD = "55인치 상업용 사이니지 제조사로는 가나 디스플레이와 다라 사이니지가 있고, 자차 디스플레이는 저가형 상업용 디스플레이를 수입해 판매한다."
S_SOL = "메뉴보드 콘텐츠 배포 솔루션은 마바 클라우드가 클라우드 CMS로 제공하며 하드웨어는 판매하지 않는다. 다라 사이니지는 3rd-party CMS 연동을 지원한다."
S_PLACE = "수도권 사이니지 설치는 사아 키오스크가 외식 매장 설치 파트너망을 운영하며, 다라 사이니지는 수도권 프랜차이즈 설치 사례가 있다."
S_CUST = "A 커피 프랜차이즈는 매장 메뉴보드 디지털 전환을 검토 중이며 일부 매장은 가나 디스플레이 제품을 쓴 것으로 알려졌다."
S_HOSP = "병원 안내 사이니지 공급 업체로는 가나 디스플레이와 하마 메디사인이 거론된다. 하마 메디사인은 병원 대기 안내 시스템을 전문으로 한다."
S_LOGI = "물류센터 관제 디스플레이는 다라 사이니지와 파타 비전이 공급하며, 파타 비전은 관제용 비디오월을 전문으로 한다."
S_NONE = "공개 자료에서 관련 공급 업체를 찾지 못했다."

web_candidates = {"responses": [
    {"when": {"contains": "의료"}, "summary": S_HOSP, "sources": [], "queries": []},
    {"when": {"contains": "병원"}, "summary": S_HOSP, "sources": [], "queries": []},
    {"when": {"contains": "안내 사이니지"}, "summary": S_HOSP, "sources": [], "queries": []},
    {"when": {"contains": "물류"}, "summary": S_LOGI, "sources": [], "queries": []},
    {"when": {"contains": "관제"}, "summary": S_LOGI, "sources": [], "queries": []},
    {"when": {"contains": "공급 업체"}, "summary": S_IND, "sources": [], "queries": []},
    {"when": {"contains": "제조사"}, "summary": S_PROD, "sources": [], "queries": []},
    {"when": {"contains": "솔루션 업체 비교"}, "summary": S_SOL, "sources": [], "queries": []},
    {"when": {"contains": "설치 업체"}, "summary": S_PLACE, "sources": [], "queries": []},
    {"when": {"contains": "도입"}, "summary": S_CUST, "sources": [], "queries": []},
    {"summary": S_NONE, "sources": [], "queries": []},
]}

# 근거 번호: 찾기에서 검색 순서 = 업종(E1) → 제품(E2) → 솔루션 비교(E3) → 장소(E4) → 고객사(E5)
CANDS = [
    ("가나 디스플레이", "국내 대형 가전 · 사이니지", "E1", "가나 디스플레이, 다라 사이니지, 사아 키오스크가 자주 거론된다"),
    ("다라 사이니지", "글로벌 사이니지 전문", "E2", "가나 디스플레이와 다라 사이니지가 있고"),
    ("마바 클라우드", "클라우드 CMS 소프트웨어", "E3", "마바 클라우드가 클라우드 CMS로 제공하며 하드웨어는 판매하지 않는다"),
    ("사아 키오스크", "키오스크 · 메뉴보드 통합 벤더", "E4", "사아 키오스크가 외식 매장 설치 파트너망을 운영하며"),
    ("자차 디스플레이", "저가형 상업용 디스플레이 수입사", "E2", "자차 디스플레이는 저가형 상업용 디스플레이를 수입해 판매한다"),
    ("카타 미디어", "오프라인 광고 매체사", "E1", "카타 미디어는 매장 광고 매체를 운영한다"),
]
summ = {"E1": S_IND, "E2": S_PROD, "E3": S_SOL, "E4": S_PLACE, "E5": S_CUST}
for n, _k, e, q in CANDS:
    assert q in summ[e], (n, q)
candidates = {"responses": [
    {"when": {"contains": "하마 메디사인"}, "json": {"candidates": [
        {"name": "가나 디스플레이", "kind_label": "국내 대형 가전 · 사이니지", "evidence_id": "E1", "evidence_quote": "가나 디스플레이와 하마 메디사인이 거론된다"},
        {"name": "하마 메디사인", "kind_label": "병원 안내 시스템 전문", "evidence_id": "E1", "evidence_quote": "하마 메디사인은 병원 대기 안내 시스템을 전문으로 한다"}]}},
    {"when": {"contains": "파타 비전"}, "json": {"candidates": [
        {"name": "다라 사이니지", "kind_label": "글로벌 사이니지 전문", "evidence_id": "E1", "evidence_quote": "다라 사이니지와 파타 비전이 공급하며"},
        {"name": "파타 비전", "kind_label": "관제 비디오월 전문", "evidence_id": "E1", "evidence_quote": "파타 비전은 관제용 비디오월을 전문으로 한다"}]}},
    {"json": {"candidates": [{"name": n, "kind_label": k, "evidence_id": e, "evidence_quote": q, "url_guess": None} for n, k, e, q in CANDS]}},
]}

resolve = {"json": {"groups": [
    {"canonical": "가나 디스플레이", "aliases": ["Gana Display"]},
    {"canonical": "다라 사이니지", "aliases": ["Dara Signage"]},
    {"canonical": "마바 클라우드", "aliases": ["Maba Cloud"]},
    {"canonical": "사아 키오스크", "aliases": []},
    {"canonical": "자차 디스플레이", "aliases": []},
    {"canonical": "카타 미디어", "aliases": []},
    {"canonical": "하마 메디사인", "aliases": []},
    {"canonical": "파타 비전", "aliases": []},
    {"canonical": "ZZ 사이니지", "aliases": ["지지 사이니지"]},
]}}


def sig(s, ids, partial=False):
    return {"s": s, "partial": partial, "source_ids": ids}


# 요약만 있는 환경(summary_only)에서는 웹 근거 신호가 0.7 로 묶인다(§7.4) — 업종 신호만 사내 사례 DB(K1)를 함께 인용해 상한이 없다.
SCORES = [
    ("가나 디스플레이", "국내 대형 가전 · 사이니지", {"industry": sig(1.0, ["K1", "E1"]), "product": sig(0.9, ["E2"]), "place": sig(0.7, ["E5"]),
                                               "customer": sig(0.8, ["E5"])}, "외식 사이니지 공급 · 55\" 라인업 · 자체 CMS"),
    ("다라 사이니지", "글로벌 사이니지 전문", {"industry": sig(1.0, ["K1", "E1"]), "product": sig(0.8, ["E2", "E3"]), "place": sig(0.8, ["E4"]),
                                          "customer": sig(0.4, ["E4"])}, "수도권 프랜차이즈 설치 사례 · 3rd-party CMS 연동"),
    ("마바 클라우드", "클라우드 CMS 소프트웨어", {"industry": sig(1.0, ["K1", "E3"]), "product": sig(0.9, ["E3"], True), "place": sig(0.6, ["E3"]),
                                            "customer": sig(0.6, ["E3"])}, "메뉴보드 콘텐츠 배포 · 하드웨어 없음"),
    ("사아 키오스크", "키오스크 · 메뉴보드 통합 벤더", {"industry": sig(0.95, ["K1", "E1"]), "product": sig(0.6, ["E1"]), "place": sig(0.7, ["E4"]),
                                                 "customer": sig(0.5, ["E4"])}, "외식 특화 · 수도권 설치 파트너망"),
    ("자차 디스플레이", "저가형 상업용 디스플레이 수입사", {"industry": sig(0.4, ["E2"]), "product": sig(0.7, ["E2"]), "place": sig(0.6, ["E2"]),
                                                    "customer": sig(0.2, ["E2"])}, "가격대 겹침 · 레퍼런스 미확인"),
    ("카타 미디어", "오프라인 광고 매체사", {"industry": sig(0.6, ["E1"]), "product": sig(0.2, ["E1"]), "place": sig(0.2, ["E1"]),
                                        "customer": sig(0.1, ["E1"])}, "업종 겹침 · 제품 다름"),
    ("하마 메디사인", "병원 안내 시스템 전문", {"industry": sig(0.9, ["E1"]), "product": sig(0.7, ["E1"]), "place": sig(0, []), "customer": sig(0, [])},
     "병원 대기 안내 전문"),
    ("파타 비전", "관제 비디오월 전문", {"industry": sig(0.9, ["E1"]), "product": sig(0.7, ["E1"]), "place": sig(0, []), "customer": sig(0, [])},
     "관제용 비디오월 전문"),
    ("ZZ 사이니지", "실내외 상업용 사이니지 제조", {"industry": sig(0.6, ["E1"]), "product": sig(0.6, ["E1"]), "place": sig(0, []), "customer": sig(0, [])},
     "RFP 에 언급된 사이니지 제조사"),
]
score = {"json": {"candidates": [{"name": n, "kind_label": k, "signals": s, "why": w} for n, k, s, w in SCORES]}}

# ── 넣기 · 업종 ──────────────────────────────────────────
A_TEXT_KEY = "A 커피 프랜차이즈"
extract_slots = {"responses": [
    {"when": {"contains": ["읽을 칸", "카페 브랜드다"]}, "json": {"place": {"value": "전국 매장", "kind": "region", "region": "전국", "confidence": 0.6}}},
    # 프롬프트 예시에도 `A 커피 프랜차이즈` 가 있어 입력 머리(`[고객 · 사업 설명]` 다음 줄)로 가른다
    {"when": {"contains": ["읽을 칸", "[고객 · 사업 설명]\nA 커피"]}, "json": {
        "customer": {"value": "A 커피 프랜차이즈", "confidence": 0.95},
        "place": {"value": "수도권 직영점", "kind": "site", "region": "수도권", "confidence": 0.9},
        "product": {"value": "55\" 사이니지 + 배포 솔루션", "categories": ["스마트 사이니지", "콘텐츠 배포 솔루션"], "specific": True, "confidence": 0.9},
        "industry_hint": "카페 프랜차이즈", "competitor_mentions": [], "eval_criteria": []}},
    {"when": {"contains": ["읽을 칸", "B 병원"]}, "json": {
        "customer": {"value": "B 병원", "confidence": 0.9},
        "place": {"value": "본관 외래", "kind": "site", "region": None, "confidence": 0.8},
        "product": {"value": "안내 사이니지", "categories": ["스마트 사이니지"], "specific": False, "confidence": 0.8},
        "industry_hint": "병원", "competitor_mentions": [], "eval_criteria": []}},
    {"when": {"contains": ["읽을 칸", "C 물류센터"]}, "json": {
        "customer": {"value": "C 물류센터", "confidence": 0.9},
        "place": {"value": "경기 이천 센터", "kind": "site", "region": "경기", "confidence": 0.8},
        "product": {"value": "관제 디스플레이", "categories": ["비디오월"], "specific": False, "confidence": 0.8},
        "industry_hint": "물류센터", "competitor_mentions": [], "eval_criteria": []}},
    {"when": {"contains": ["읽을 칸", "매장 메뉴보드 사이니지"]}, "json": {
        "customer": {"value": None, "confidence": 0}, "place": {"value": None, "kind": None, "region": None, "confidence": 0},
        "product": {"value": "메뉴보드 사이니지", "categories": ["스마트 사이니지"], "specific": False, "confidence": 0.8},
        "industry_hint": "매장", "competitor_mentions": [], "eval_criteria": []}},
    {"when": {"contains": ["읽을 칸", "카페 메뉴보드 사이니지"]}, "json": {
        "customer": {"value": None, "confidence": 0}, "place": {"value": None, "kind": None, "region": None, "confidence": 0},
        "product": {"value": "메뉴보드 사이니지", "categories": ["스마트 사이니지"], "specific": False, "confidence": 0.8},
        "industry_hint": "카페", "competitor_mentions": [], "eval_criteria": []}},
    {"json": {"customer": {"value": None, "confidence": 0}, "place": {"value": None, "kind": None, "region": None, "confidence": 0},
              "product": {"value": None, "categories": [], "specific": False, "confidence": 0}, "industry_hint": None,
              "competitor_mentions": [], "eval_criteria": []}},
]}

# 업종 목록(프롬프트 안)에 `카페 · 물류` 같은 낱말이 늘 있으므로 [글] 에만 있는 낱말로 고른다
classify_segment = {"responses": [
    {"when": {"contains": ["[글]", "물류센터"]}, "json": {"segments": [{"code": "MF", "p": 0.92, "clues": ["물류센터", "관제"]}], "out_of_scope": False, "reason": ""}},
    {"when": {"contains": ["[글]", "병원"]}, "json": {"segments": [{"code": "MD", "p": 0.93, "clues": ["병원"]}], "out_of_scope": False, "reason": ""}},
    {"when": {"contains": ["[글]", "커피"]}, "json": {"segments": [{"code": "FB", "p": 0.94, "clues": ["커피", "프랜차이즈", "메뉴보드"]},
                                                              {"code": "RT", "p": 0.4, "clues": ["매장"]}], "out_of_scope": False, "reason": ""}},
    {"when": {"contains": ["[글]", "매장 메뉴보드"]}, "json": {"segments": [{"code": "FB", "p": 0.68, "clues": ["메뉴보드"]},
                                                                     {"code": "RT", "p": 0.66, "clues": ["매장"]}], "out_of_scope": False, "reason": ""}},
    {"when": {"contains": ["[글]", "카페 메뉴보드"]}, "json": {"segments": [{"code": "FB", "p": 0.9, "clues": ["카페", "메뉴보드"]},
                                                                     {"code": "RT", "p": 0.35, "clues": []}], "out_of_scope": False, "reason": ""}},
    {"json": {"segments": [], "out_of_scope": False, "reason": ""}},
]}

include_exclude = {"responses": [
    {"when": {"contains": "ZZ 사이니지"}, "json": {"include": ["ZZ 사이니지"], "exclude": ["YY 광고"], "notes": ""}},
    {"json": {"include": [], "exclude": [], "notes": ""}},
]}

make_criteria = {"responses": [
    {"when": {"contains": "일괄 배포"}, "json": {"criteria": [
        {"name": "본사 일괄 배포", "source": "free"}, {"name": "매장별 가격 차등", "source": "free"}, {"name": "전기료", "source": "free"}],
        "industry": [{"code": "R08", "name": "인건비 절감"}, {"code": "R03", "name": "원격 콘텐츠 관리"}, {"code": "R07", "name": "매장 환경 자동화"},
                     {"code": "R16", "name": "시간대 프로모션"}, {"code": "R06", "name": "에너지 관리"}, {"code": "R01", "name": "설치 속도"}]}},
    {"json": {"criteria": [], "industry": [{"code": "R08", "name": "인건비 절감"}, {"code": "R03", "name": "원격 콘텐츠 관리"},
                                            {"code": "R07", "name": "매장 환경 자동화"}, {"code": "R16", "name": "시간대 프로모션"},
                                            {"code": "R06", "name": "에너지 관리"}, {"code": "R01", "name": "설치 속도"}]}},
]}

title = {"responses": [
    {"when": {"contains": "고객사: A 커피"}, "json": {"title": "A 커피 메뉴보드 경쟁사 분석"}},
    {"when": {"contains": "고객사: B 병원"}, "json": {"title": "B 병원 안내 사이니지 경쟁사"}},
    {"when": {"contains": "고객사: C 물류센터"}, "json": {"title": "C 물류센터 관제 디스플레이 경쟁사"}},
    {"json": {"title": ""}},
]}

# ── 분석: 사실 검색 요약(경쟁사 이름 + 항목 키워드) ─────
FACTS = {
    "가나 디스플레이": {
        "라인업": "가나 디스플레이는 55인치 메뉴보드급 사이니지와 43인치 소형 사이니지, 바닥형 스탠드 모델을 판매한다.",
        "CMS": "가나 디스플레이는 자체 CMS를 제공하며 매장 500곳 이상이면 별도 서버를 추가해야 한다.",
        "도입 사례": "가나 디스플레이는 외식 프랜차이즈 메뉴보드 공개 사례 6건을 소개하며, 이 중 3건이 수도권 매장이다.",
        "가격": "가나 디스플레이 사이니지의 공개 판매 가격은 확인되지 않는다.",
        "신제품": "가나 디스플레이는 2026년 3월 55인치 메뉴보드 라인업을 교체하는 신제품을 발표했다.",
    },
    "다라 사이니지": {
        "라인업": "다라 사이니지는 49·55·65인치 상업용 디스플레이와 고휘도 윈도 사이니지를 공급한다.",
        "CMS": "다라 사이니지는 3rd-party CMS 연동 방식이며 2025년 11월부터 지역 단위로 콘텐츠를 배포한다.",
        "도입 사례": "다라 사이니지는 수도권 프랜차이즈 매장 설치 사례 3건을 공개했다.",
        "가격": "다라 사이니지 55인치 모델은 조달 단가 기준 대당 180만 원대로 공개돼 있다.",
        "신제품": "다라 사이니지의 최근 12개월 신제품 발표는 확인되지 않는다.",
    },
    "마바 클라우드": {
        "라인업": "마바 클라우드는 하드웨어를 판매하지 않고 메뉴보드용 클라우드 CMS만 제공한다.",
        "CMS": "마바 클라우드는 클라우드 CMS로 본사에서 전 매장 메뉴 콘텐츠를 일괄 배포하고 매장별 가격을 따로 지정할 수 있다.",
        "도입 사례": "마바 클라우드는 카페 프랜차이즈 고객사 사례를 공개하고 있다.",
        "가격": "마바 클라우드는 매장당 월 구독 요금제를 운영하지만 공개 가격표는 없다.",
        "신제품": "마바 클라우드는 2026년 2월 메뉴보드 원격 관리 기능을 추가했다.",
    },
    "사아 키오스크": {
        "라인업": "사아 키오스크는 주문 키오스크와 32·55인치 메뉴보드를 묶어 공급한다.",
        "CMS": "사아 키오스크는 POS 연동 메뉴보드 관리 프로그램을 함께 제공한다.",
        "도입 사례": "사아 키오스크는 수도권 외식 매장 설치 파트너망을 운영하며 설치 속도를 강점으로 내세운다.",
        "가격": "사아 키오스크의 공개 가격 정보는 없다.",
        "신제품": "사아 키오스크의 최근 신제품 발표는 확인되지 않는다.",
    },
    "자차 디스플레이": {
        "라인업": "자차 디스플레이는 저가형 43·55인치 상업용 디스플레이를 수입해 판매한다.",
        "CMS": "자차 디스플레이는 별도 CMS 없이 USB 재생 방식을 쓴다.",
        "도입 사례": "자차 디스플레이의 외식 매장 공개 사례는 확인되지 않는다.",
        "가격": "자차 디스플레이 55인치 모델은 온라인 최저가 기준 대당 90만 원대에 판매된다.",
        "신제품": "자차 디스플레이의 최근 신제품 발표는 확인되지 않는다.",
    },
    "카타 미디어": {
        "라인업": "카타 미디어는 디스플레이를 판매하지 않고 매장 광고 매체를 운영한다.",
        "CMS": "카타 미디어는 광고 편성 시스템을 자체 운영한다.",
        "도입 사례": "카타 미디어는 카페 매장 광고 매체 운영 사례를 소개한다.",
        "가격": "카타 미디어의 광고 단가는 공개돼 있지 않다.",
        "신제품": "카타 미디어의 최근 신제품 발표는 확인되지 않는다.",
    },
    "ZZ 사이니지": {
        "라인업": "ZZ 사이니지는 실내외 상업용 사이니지를 제조한다.",
        "CMS": "ZZ 사이니지는 자체 원격 관리 소프트웨어를 함께 판매한다.",
        "도입 사례": "ZZ 사이니지의 외식 매장 공개 사례는 확인되지 않는다.",
        "가격": "ZZ 사이니지의 공개 가격 정보는 없다.",
        "신제품": "ZZ 사이니지의 최근 신제품 발표는 확인되지 않는다.",
    },
}
RESEARCH = {
    ("가나 디스플레이", "가격 견적 조달"): "가나 디스플레이 55인치 메뉴보드 모델의 조달 등록 단가는 대당 210만 원이다.",
}
web_facts = {"responses": []}
web_research = {"responses": []}
for (name, kw), s in RESEARCH.items():
    web_research["responses"].append({"when": {"contains": [name, kw]}, "summary": s, "sources": [], "queries": []})
for name, d in FACTS.items():
    for kw, s in d.items():
        web_facts["responses"].append({"when": {"contains": [name, kw]}, "summary": s, "sources": [], "queries": []})
web_facts["responses"].append({"summary": "공개 자료에서 이 항목을 찾지 못했다.", "sources": [], "queries": []})
web_research["responses"].append({"summary": "공개 자료에서 이 항목을 더 찾지 못했다.", "sources": [], "queries": []})


def claim(text, eid, quote, summary):
    assert quote in summary, (text, quote)
    return {"text": text, "citations": [{"evidence_id": eid, "quote": quote}]}


def tbd():
    return {"text": "[확인 필요]", "claims": []}


F = FACTS
EXTRACT = {
    "가나 디스플레이": {
        "lineup": {"text": "55\" 메뉴보드급 · 43\" 소형 · 바닥형", "claims": [claim("55인치 메뉴보드급 · 43인치 소형 · 바닥형 스탠드", "E1",
                                                                                "55인치 메뉴보드급 사이니지와 43인치 소형 사이니지, 바닥형 스탠드 모델", F["가나 디스플레이"]["라인업"])]},
        "solution": {"text": "자체 CMS · 500매장 이상은 별도 서버", "claims": [claim("자체 CMS 제공 · 500매장 이상은 별도 서버 필요", "E2",
                                                                                  "자체 CMS를 제공하며 매장 500곳 이상이면 별도 서버를 추가해야 한다", F["가나 디스플레이"]["CMS"])]},
        "references": {"text": "공개 사례 6건 · 수도권 3건", "claims": [claim("외식 프랜차이즈 공개 사례 6건 · 수도권 3건", "E3",
                                                                       "외식 프랜차이즈 메뉴보드 공개 사례 6건을 소개하며, 이 중 3건이 수도권 매장이다", F["가나 디스플레이"]["도입 사례"])]},
        "price": tbd(),
        "recent": {"text": "2026년 3월 신제품 · 55\" 라인업 교체", "claims": [claim("2026년 3월 55인치 메뉴보드 라인업 교체 신제품 발표", "E5",
                                                                             "2026년 3월 55인치 메뉴보드 라인업을 교체하는 신제품을 발표했다", F["가나 디스플레이"]["신제품"])]},
    },
    "다라 사이니지": {
        "lineup": {"text": "49 · 55 · 65\" 상업용 · 고휘도 윈도형", "claims": [claim("49·55·65인치 상업용 디스플레이 · 고휘도 윈도 사이니지", "E1",
                                                                            "49·55·65인치 상업용 디스플레이와 고휘도 윈도 사이니지", F["다라 사이니지"]["라인업"])]},
        "solution": {"text": "3rd-party CMS 연동 · 지역 단위 배포", "claims": [claim("3rd-party CMS 연동 · 2025년 11월부터 지역 단위 배포", "E2",
                                                                              "3rd-party CMS 연동 방식이며 2025년 11월부터 지역 단위로 콘텐츠를 배포한다", F["다라 사이니지"]["CMS"])]},
        "references": {"text": "수도권 프랜차이즈 설치 사례 3건", "claims": [claim("수도권 프랜차이즈 매장 설치 사례 3건", "E3",
                                                                          "수도권 프랜차이즈 매장 설치 사례 3건을 공개했다", F["다라 사이니지"]["도입 사례"])]},
        "price": {"text": "55\" 대당 180만 원대(조달 단가)", "claims": [claim("55인치 모델 조달 단가 대당 180만 원대", "E4",
                                                                        "55인치 모델은 조달 단가 기준 대당 180만 원대로 공개돼 있다", F["다라 사이니지"]["가격"])]},
        "recent": tbd(),
    },
    "마바 클라우드": {
        "lineup": {"text": "하드웨어 없음 · 클라우드 CMS 전문", "claims": [claim("하드웨어 없이 메뉴보드용 클라우드 CMS만 제공", "E1",
                                                                          "하드웨어를 판매하지 않고 메뉴보드용 클라우드 CMS만 제공한다", F["마바 클라우드"]["라인업"])]},
        "solution": {"text": "본사 일괄 배포 · 매장별 가격 지정", "claims": [claim("본사에서 전 매장 일괄 배포 · 매장별 가격 지정", "E2",
                                                                           "본사에서 전 매장 메뉴 콘텐츠를 일괄 배포하고 매장별 가격을 따로 지정할 수 있다", F["마바 클라우드"]["CMS"])]},
        "references": {"text": "카페 프랜차이즈 고객 사례", "claims": [claim("카페 프랜차이즈 고객사 사례 공개", "E3", "카페 프랜차이즈 고객사 사례를 공개하고 있다",
                                                                       F["마바 클라우드"]["도입 사례"])]},
        "price": tbd(),
        "recent": {"text": "2026년 2월 원격 관리 기능 추가", "claims": [claim("2026년 2월 메뉴보드 원격 관리 기능 추가", "E5", "2026년 2월 메뉴보드 원격 관리 기능을 추가했다",
                                                                       F["마바 클라우드"]["신제품"])]},
    },
    "사아 키오스크": {
        "lineup": {"text": "주문 키오스크 + 32 · 55\" 메뉴보드", "claims": [claim("주문 키오스크와 32·55인치 메뉴보드 묶음 공급", "E1", "주문 키오스크와 32·55인치 메뉴보드를 묶어 공급한다",
                                                                           F["사아 키오스크"]["라인업"])]},
        "solution": {"text": "POS 연동 메뉴보드 관리", "claims": [claim("POS 연동 메뉴보드 관리 프로그램 제공", "E2", "POS 연동 메뉴보드 관리 프로그램을 함께 제공한다",
                                                                   F["사아 키오스크"]["CMS"])]},
        "references": {"text": "수도권 외식 설치 파트너망 · 설치 속도", "claims": [claim("수도권 외식 매장 설치 파트너망 · 설치 속도 강점", "E3",
                                                                                "수도권 외식 매장 설치 파트너망을 운영하며 설치 속도를 강점으로 내세운다", F["사아 키오스크"]["도입 사례"])]},
        "price": tbd(),
        "recent": tbd(),
    },
    "자차 디스플레이": {
        "lineup": {"text": "저가형 43 · 55\" 상업용 수입", "claims": [claim("저가형 43·55인치 상업용 디스플레이 수입 판매", "E1", "저가형 43·55인치 상업용 디스플레이를 수입해 판매한다",
                                                                       F["자차 디스플레이"]["라인업"])]},
        "solution": {"text": "CMS 없음 · USB 재생", "claims": [claim("별도 CMS 없이 USB 재생 방식", "E2", "별도 CMS 없이 USB 재생 방식을 쓴다", F["자차 디스플레이"]["CMS"])]},
        "references": tbd(),
        "price": {"text": "55\" 대당 90만 원대(온라인 최저가)", "claims": [claim("55인치 모델 온라인 최저가 대당 90만 원대", "E4", "55인치 모델은 온라인 최저가 기준 대당 90만 원대에 판매된다",
                                                                          F["자차 디스플레이"]["가격"])]},
        "recent": tbd(),
    },
    "카타 미디어": {
        "lineup": {"text": "디스플레이 판매 없음 · 광고 매체 운영", "claims": [claim("디스플레이 판매 없이 매장 광고 매체 운영", "E1", "디스플레이를 판매하지 않고 매장 광고 매체를 운영한다",
                                                                            F["카타 미디어"]["라인업"])]},
        "solution": {"text": "자체 광고 편성 시스템", "claims": [claim("광고 편성 시스템 자체 운영", "E2", "광고 편성 시스템을 자체 운영한다", F["카타 미디어"]["CMS"])]},
        "references": {"text": "카페 매장 광고 운영 사례", "claims": [claim("카페 매장 광고 매체 운영 사례", "E3", "카페 매장 광고 매체 운영 사례를 소개한다", F["카타 미디어"]["도입 사례"])]},
        "price": tbd(), "recent": tbd(),
    },
    "ZZ 사이니지": {
        "lineup": {"text": "실내외 상업용 사이니지 제조", "claims": [claim("실내외 상업용 사이니지 제조", "E1", "실내외 상업용 사이니지를 제조한다", F["ZZ 사이니지"]["라인업"])]},
        "solution": {"text": "자체 원격 관리 소프트웨어", "claims": [claim("자체 원격 관리 소프트웨어 판매", "E2", "자체 원격 관리 소프트웨어를 함께 판매한다", F["ZZ 사이니지"]["CMS"])]},
        "references": tbd(), "price": tbd(), "recent": tbd(),
    },
}
R_PRICE = RESEARCH[("가나 디스플레이", "가격 견적 조달")]
extract_facts = {"responses": [
    {"when": {"contains": ["가나 디스플레이", "조달 등록 단가"]}, "json": {"facts": {
        "lineup": tbd(), "solution": tbd(), "references": tbd(), "recent": tbd(),
        "price": {"text": "55\" 대당 210만 원(조달 등록 단가)", "claims": [claim("55인치 메뉴보드 모델 조달 등록 단가 대당 210만 원", "E1",
                                                                         "55인치 메뉴보드 모델의 조달 등록 단가는 대당 210만 원이다", R_PRICE)]}}}},
]}
for name, facts in EXTRACT.items():
    extract_facts["responses"].append({"when": {"contains": [f"경쟁사 '{name}'"]}, "json": {"facts": facts}})
extract_facts["responses"].append({"json": {"facts": {k: tbd() for k in ("lineup", "price", "solution", "references", "recent")}}})

positioning = {"responses": [
    {"when": {"contains": "가나 디스플레이"}, "json": {"text": "자체 CMS 기반 풀 라인업 · 500매장 이상은 서버 추가"}},
    {"when": {"contains": "다라 사이니지"}, "json": {"text": "3rd-party CMS 연동 · 수도권 설치 사례"}},
    {"when": {"contains": "마바 클라우드"}, "json": {"text": "하드웨어 없는 클라우드 CMS 전문"}},
    {"when": {"contains": "사아 키오스크"}, "json": {"text": "키오스크 · 메뉴보드 묶음 · 수도권 설치망"}},
    {"when": {"contains": "자차 디스플레이"}, "json": {"text": "저가형 수입 디스플레이 · CMS 없음"}},
    {"when": {"contains": "카타 미디어"}, "json": {"text": "매장 광고 매체 운영사"}},
    {"when": {"contains": "ZZ 사이니지"}, "json": {"text": "실내외 상업용 사이니지 제조사"}},
    {"json": {"text": ""}},
]}

C6 = ["본사 일괄 배포", "매장별 가격 차등", "전기료", "인건비 절감", "가격대", "레퍼런스 · AS"]


def vrows(vs, why):
    return [{"criterion": c, "verdict": v, "rationale": why.get(c, "")} for c, v in zip(C6, vs)]


B, S, W, U = "samsung_better", "similar", "samsung_worse", "unknown"
verdicts = {"responses": [
    {"when": {"contains": "경쟁사 '가나 디스플레이'"}, "json": {"rows": vrows([B, B, B, S, U, S], {
        "본사 일괄 배포": "경쟁사는 500매장 이상에서 별도 서버가 필요해요", "매장별 가격 차등": "삼성은 매장별 콘텐츠를 본사에서 관리해요", "전기료": "삼성 칸은 공식 소비전력 근거가 있어요"})}},
    {"when": {"contains": "경쟁사 '다라 사이니지'"}, "json": {"rows": vrows([B, S, S, S, U, W], {
        "본사 일괄 배포": "경쟁사는 3rd-party CMS 연동이라 운영 주체가 나뉘어요", "레퍼런스 · AS": "수도권 프랜차이즈 설치 사례가 공개돼 있어요"})}},
    {"when": {"contains": "경쟁사 '마바 클라우드'"}, "json": {"rows": vrows([S, W, U, S, U, S], {
        "매장별 가격 차등": "경쟁사는 매장별 가격을 따로 지정할 수 있어요"})}},
    {"when": {"contains": "경쟁사 '사아 키오스크'"}, "json": {"rows": vrows([B, S, B, S, U, W], {
        "본사 일괄 배포": "경쟁사는 POS 연동 관리 프로그램 중심이에요", "레퍼런스 · AS": "수도권 설치 파트너망 · 설치 속도가 강점이에요"})}},
    {"when": {"contains": "경쟁사 '자차 디스플레이'"}, "json": {"rows": vrows([B, B, S, B, W, B], {"가격대": "경쟁사 가격이 더 낮아요"})}},
    {"json": {"rows": [{"criterion": c, "verdict": "unknown", "rationale": ""} for c in C6]}},
]}

strengths = {"json": {
    "strengths": [
        {"criterion": "본사 일괄 배포", "title": "서버 없는 통합 관리", "note": "MagicINFO · 별도 서버 없이 전 매장 관리"},
        {"criterion": "전기료", "title": "저전력 상시 운영", "note": "공식 소비전력 근거로 전기료 비교"},
        {"criterion": "매장별 가격 차등", "title": "매장별 메뉴 운영", "note": "본사에서 매장별 콘텐츠를 한 번에"},
        {"criterion": "인건비 절감", "title": "운영 인력 절감", "note": "원격 관리로 매장 방문 줄이기"},
    ],
    "cautions": [
        {"letter": "C", "note": "매장별 가격 지정 · 소프트웨어만 비교되면 불리해요"},
        {"letter": "B", "note": "수도권 설치 사례 · 설치 레퍼런스에서 앞설 수 있어요"},
        {"letter": "D", "note": "수도권 설치 파트너망 · 설치 속도에서 앞설 수 있어요"},
    ]}}

# ── 직접 추가 · 더 찾기 · 재확인 ─────────────────────────
web_profile = {"responses": [
    {"when": {"contains": "ZZ 사이니지"}, "summary": "ZZ 사이니지는 실내외 상업용 사이니지를 제조하고 자체 원격 관리 소프트웨어를 함께 판매한다.", "sources": [], "queries": []},
    {"when": {"contains": "자차 디스플레이"}, "summary": F["자차 디스플레이"]["라인업"], "sources": [], "queries": []},
    {"summary": "공개 자료에서 이 회사를 찾지 못했다.", "sources": [], "queries": []},
]}
profile = {"responses": [
    {"when": {"contains": "ZZ 사이니지"}, "json": {"kind_label": "실내외 상업용 사이니지 제조", "why": "자체 원격 관리 소프트웨어 함께 판매", "evidence_id": "E1",
                                                   "evidence_quote": "실내외 상업용 사이니지를 제조하고"}},
    {"json": {"kind_label": "", "why": "", "evidence_id": "", "evidence_quote": ""}},
]}
web_recheck = {"responses": [
    {"when": {"contains": "다라 사이니지"}, "summary": "다라 사이니지는 2026년 11월 2일 고휘도 55인치 메뉴보드 신제품을 출시했다.", "sources": [], "queries": []},
    {"summary": "최근 신제품 출시 소식을 찾지 못했다.", "sources": [], "queries": []},
]}
recheck_news = {"responses": [
    {"when": {"contains": "'다라 사이니지'"}, "json": {"items": [{"product": "고휘도 55인치 메뉴보드", "date": "2026-11-02",
                                                                  "summary": "다라 사이니지가 고휘도 55인치 메뉴보드 신제품을 출시했어요",
                                                                  "quote": "2026년 11월 2일 고휘도 55인치 메뉴보드 신제품을 출시했다"}]}},
    {"json": {"items": []}},
]}
web_customer = {"responses": [
    {"summary": "A 커피 프랜차이즈는 전국에 매장을 운영하는 카페 브랜드다.", "sources": [], "queries": []},
]}

files = {
    "ca.web_candidates": web_candidates, "ca.candidates_from_text": candidates, "ca.resolve_entities": resolve, "ca.score_signals": score,
    "ca.extract_slots": extract_slots, "ca.classify_segment": classify_segment, "ca.include_exclude": include_exclude,
    "ca.make_criteria": make_criteria, "ca.title": title, "ca.web_facts": web_facts, "ca.web_research": web_research,
    "ca.extract_facts": extract_facts, "ca.positioning": positioning, "ca.verdicts": verdicts, "ca.strengths": strengths,
    "ca.web_profile": web_profile, "ca.candidate_profile": profile, "ca.web_recheck": web_recheck, "ca.recheck_news": recheck_news,
    "ca.web_customer": web_customer,
}
OUT.mkdir(parents=True, exist_ok=True)
for name, body in files.items():
    (OUT / f"{name}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("wrote", len(files), "files to", OUT)
