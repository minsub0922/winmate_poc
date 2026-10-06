"""정적 정의 — 10-proposal.md 부록 A–E · §3.3 · §3.8 · §4.4 · §10.7 원문을 옮긴 표.

화면 문구(「…」)는 원문 그대로 둔다. 바꾸려면 시나리오 문서를 먼저 고친다.
"""
from __future__ import annotations

import re
from typing import Any

SERVICE = "proposal"
FEATURE = "PR"
ROUTE_BASE = "/proposal"   # 웹 기능 키(셸이 /<key> 아래에 라우트를 단다). 시나리오 §2 의 /proposals 와 같은 화면

STEP_NAMES = ["고객 · 프로젝트", "제안서 유형", "시트 구성", "섹션 작성", "디자인 템플릿", "PPTX 생성"]
STAGE_NO = {"customer": 1, "type": 2, "compose": 3, "industry": 3, "sections": 4, "design": 5, "result": 6}
STAGE_ORDER = ["customer", "type", "compose", "industry", "sections", "design", "result"]
STATUS_LABEL = {"draft": "작성 중", "review": "검토 중", "done": "완료"}
LANGS = ("ko", "en")

# ── 유형(§3.3 · 부록 D) ─────────────────────────────────────
TYPES: dict[str, dict[str, Any]] = {
    "standard": {
        "name": "표준 제안서", "label": "표준", "short": "표준",
        "desc": "시장 분석부터 공간·제품·솔루션·스펙까지 전 과정을 담는 기본형",
        "sections": ["mi", "vp", "birdseye", "spaceProducts", "solution", "cases", "why", "spec"],
        "optional": ["mi", "solution"], "open": "mi", "prefix": "PRS",
    },
    "quickwin": {
        "name": "퀵윈(제품) 제안서", "label": "퀵윈(제품)", "short": "퀵윈",
        "desc": "제품 중심으로 빠르게 결정을 끌어내는 간결형",
        "sections": ["vp", "spaceProducts", "solution", "cases", "spec"],
        "optional": ["solution"], "open": "spaceProducts", "prefix": "PRQ",
    },
    "solution": {
        "name": "Solution형 제안서", "label": "Solution형", "short": "Solution형",
        "desc": "대규모 MI와 공간별 가치 제공 시나리오로 설득하는 솔루션 중심형",
        "sections": ["bigMi", "vp", "spaceScenario", "cases", "why"],
        "optional": ["vp"], "open": "spaceScenario", "prefix": "PRX",
    },
}
TYPE_KEYS = tuple(TYPES)

# ── 섹션(부록 D) ─────────────────────────────────────────────
# sidebar = 사이드바에서 받는 기능(서비스 이름), items = 팝업 항목 종류, sidebar_label = 부록 D 「…」 원문
SECTIONS: dict[str, dict[str, Any]] = {
    "mi": {
        "name": "Market Intelligence", "short": "MI",
        "intro": "Market Intelligence 섹션입니다. 사이드바의 MI 작업을 끌어 놓으면 필요한 내용만 뽑아 시트에 넣고, 시트마다 데이터 모양에 맞는 템플릿을 골라 둡니다.",
        "sidebar": ["mi"], "sidebar_label": "MI 작업", "items": ["case"],
        "quick": ["수치 근거 보강", "더 간결하게", "템플릿 바꾸기"],
        "infer": "연결된 MI 작업 + 요구사항 기반 조사", "family": "MI",
    },
    "bigMi": {
        "name": "대규모 MI", "short": "대규모 MI",
        "intro": "Solution형 제안서의 출발점인 대규모 Market Intelligence입니다. 산업·고객사·사용자·경쟁 구도를 넓게 다루며, 사이드바의 MI 작업 여러 개를 끌어 놓아 합칠 수 있습니다.",
        "sidebar": ["mi"], "sidebar_label": "MI 작업", "items": ["case"],
        "quick": ["조사 범위 넓히기", "출처 보기", "템플릿 바꾸기"],
        "infer": "연결된 MI 2건 + 산업·경쟁 추가 조사", "family": "MI",
    },
    "vp": {
        "name": "Value Props", "short": "Value Props",
        "intro": "고객에게 줄 핵심 가치를 정리합니다. Storyboard의 Key Message와 제안 전략을 가져와 고객 과제 → 가치 제안 흐름의 시트로 만들었습니다.",
        "sidebar": ["storyboard", "vp"], "sidebar_label": "Storyboard 작업", "items": ["image"],
        "quick": ["가치 하나 추가", "경영진 톤으로", "템플릿 바꾸기"],
        "infer": "Storyboard Key Message · 전략으로 작성", "family": "VP",
    },
    "birdseye": {
        "name": "조감도", "short": "조감도",
        "intro": "공간 특징이 드러나는 조감도 시트입니다. 공간 조감도 작업의 결과를 연결했고, 다른 조감도 작업이나 이미지를 끌어 놓아 바꿀 수 있습니다.",
        "sidebar": ["birdseye"], "sidebar_label": "조감도 작업", "items": ["image"],
        "quick": ["시점 추가", "조감도 새로 만들기", "템플릿 바꾸기"],
        "infer": "연결된 조감도 작업으로 완성", "family": None,
    },
    "spaceProducts": {
        "name": "공간별 제품", "short": "공간별 제품",
        "intro": "공간마다 어떤 제품이 어디에 놓이는지 보여줍니다. 조감도 배치안에서 공간 3곳과 제품을 가져왔고, 제품 탐색에서 끌어 놓아 더할 수 있습니다.",
        "sidebar": ["birdseye", "spec"], "sidebar_label": "조감도 · Spec 시트 작업", "items": ["product", "image"],
        "quick": ["공간 추가", "수량 조정", "템플릿 바꾸기"],
        "infer": "조감도 배치안 · 요구사항에서 제품 추론", "family": "SS",
    },
    "solution": {
        "name": "솔루션 제안", "short": "솔루션 제안",
        "intro": "제품과 함께 쓸 솔루션을 제안합니다. 솔루션마다 전용 템플릿(소개 · 구성도 · 공간 시나리오)으로 그 솔루션의 특징대로 보여주고, 두 개 이상이면 통합 구성도를 더합니다.",
        "sidebar": ["scenario"], "sidebar_label": "공간 시나리오 작업", "items": ["solution", "product"],
        "quick": ["통합 운영 시나리오 추가", "운영 비용 추가", "템플릿 바꾸기"],
        "infer": "연결된 솔루션 2개 · 시나리오로 작성", "family": None,
    },
    "cases": {
        "name": "유관 사례", "short": "유관 사례",
        "intro": "비슷한 고객의 도입 사례로 설득력을 더합니다. 유사도가 높은 사례 2건을 골라 두었고, 유관 사례 검색에서 끌어 놓아 바꾸거나 더할 수 있습니다.",
        "sidebar": [], "sidebar_label": "", "items": ["case", "image"],
        "quick": ["성과 수치 강조", "사례 한 장으로 모으기", "템플릿 바꾸기"],
        "infer": "유사도 상위 사례 자동 선택", "family": None,
    },
    "why": {
        "name": "Why Samsung", "short": "Why Samsung",
        "intro": "경쟁사 대비 삼성의 강점을 정리합니다. MI의 경쟁사 분석에서 비교 항목과 강점 3개를 가져왔습니다. 수치는 검증 전이라 [확정 필요]로 표시해 두었습니다.",
        "sidebar": ["mi", "competitor"], "sidebar_label": "MI 작업", "items": ["case"],
        "quick": ["비교 항목 추가", "레퍼런스 강조", "템플릿 바꾸기"],
        "infer": "MI 경쟁사 분석으로 비교 작성", "family": None,
    },
    "spec": {
        "name": "제품 스펙", "short": "제품 스펙",
        "intro": "제안한 제품의 스펙을 정리합니다. 공간별 제품에 들어간 모델로 비교표를 만들었고, Spec 시트 작업이나 제품 탐색에서 끌어 놓아 더할 수 있습니다.",
        "sidebar": ["spec"], "sidebar_label": "Spec 시트 작업", "items": ["product"],
        "quick": ["제품별로 나누기", "영문 스펙", "템플릿 바꾸기"],
        "infer": "공간별 제품 모델로 비교표 생성", "family": None,
    },
    "spaceScenario": {
        "name": "공간별 가치 제공 시나리오", "short": "공간별 가치 시나리오",
        "intro": "어떤 솔루션이 어느 공간에서, 어떤 제품과 함께, 어떻게 쓰이는지를 시나리오로 보여줍니다. 공간 시나리오 작업을 가져와 공간 3곳 × 솔루션 2개로 구성했습니다.",
        "sidebar": ["scenario", "birdseye"], "sidebar_label": "공간 시나리오 · 조감도 작업", "items": ["solution", "product", "image"],
        "quick": ["공간 추가", "솔루션 추가", "템플릿 바꾸기"],
        "infer": "시나리오 작업 + 공간별 솔루션 매핑 추론", "family": "SS",
    },
}
SECTION_KEYS = tuple(SECTIONS)
ITEM_LABEL = {"product": "제품", "solution": "솔루션", "image": "이미지", "case": "유관 사례"}

# ── 기능(사이드바 · 연결 자료) ────────────────────────────────
# 서비스 이름 ↔ 기능 코드, 화면 라벨
FEATURE_CODE = {"requirements": "RQ", "storyboard": "SB", "mi": "MI", "competitor": "CA", "vp": "VP", "spec": "SP",
                "image": "IMG", "birdseye": "BE", "scenario": "SC", "proposal": "PR"}
CODE_FEATURE = {v: k for k, v in FEATURE_CODE.items()}
FEATURE_LABEL = {
    "requirements": "고객 요구사항", "storyboard": "Storyboard", "mi": "Market Intelligence", "competitor": "경쟁사 분석",
    "vp": "Value Props", "spec": "Spec 시트", "image": "이미지 생성", "birdseye": "공간 조감도", "scenario": "공간 시나리오",
    "kb_product": "제품", "kb_solution": "솔루션", "kb_case": "유관 사례", "kb_image": "이미지", "file": "파일",
}
FEATURE_SHORT = {  # 연결 자료 칩 앞 글자 · 「{{기능 짧은 이름}} 작업 업데이트됨」
    "requirements": "요구사항", "storyboard": "Storyboard", "mi": "MI", "competitor": "경쟁사", "vp": "VP", "spec": "Spec 시트",
    "image": "이미지", "birdseye": "조감도", "scenario": "시나리오", "kb_product": "제품", "kb_solution": "솔루션",
    "kb_case": "유관 사례", "kb_image": "이미지", "file": "파일",
}
ITEM_FEATURE = {"product": "kb_product", "solution": "kb_solution", "case": "kb_case", "image": "kb_image"}
WORK_FEATURES = ("requirements", "storyboard", "mi", "competitor", "vp", "spec", "image", "birdseye", "scenario")


def norm_feature(value: str | None) -> str | None:
    """기능 코드(MI) · 서비스 이름(mi) · 대소문자 섞임을 서비스 이름으로."""
    if not value:
        return None
    v = value.strip()
    if v.upper() in CODE_FEATURE:
        return CODE_FEATURE[v.upper()]
    low = v.lower()
    if low in FEATURE_CODE or low in FEATURE_LABEL:
        return low
    alias = {"market": "mi", "sb": "storyboard", "rq": "requirements", "ca": "competitor", "sp": "spec", "img": "image",
             "be": "birdseye", "sc": "scenario", "kb:product": "kb_product", "kb:solution": "kb_solution", "kb:case": "kb_case",
             "kb:image": "kb_image", "product": "kb_product", "solution": "kb_solution", "case": "kb_case"}
    return alias.get(low, low)


# 작업 id 접두사 → 기능(통합 규칙: 넘김 id 는 기능마다 겹칠 수 있다 — mi · competitor 둘 다 hof_ — 그래서 작업 id 가 기능을 정한다)
ID_PREFIX_FEATURE = {"rq": "requirements", "sb": "storyboard", "mi": "mi", "ca": "competitor", "vp": "vp", "sp": "spec",
                     "img": "image", "imv": "image", "be": "birdseye", "sc": "scenario"}


def feature_for_ref(feature: str | None, ref_id: str | None) -> str | None:
    """작업 id 접두사가 다른 기능을 가리키면 그 기능으로 바로잡는다(예: hof_ 넘김에 feature=mi · ref_id=ca_… → competitor)."""
    pre = (ref_id or "").split("_", 1)[0].lower() if ref_id and "_" in ref_id else ""
    by_id = ID_PREFIX_FEATURE.get(pre)
    if by_id and (feature is None or feature in WORK_FEATURES) and by_id != feature:
        return by_id
    return feature


# PR1L 「넣을 곳」(§4.9 원문 + 제안) — 기능 → (라벨, 유형별 섹션)
WORK_TARGETS: dict[str, dict[str, Any]] = {
    "storyboard": {"label": "고객 정보 · Value Props", "standard": ["vp"], "quickwin": ["vp"], "solution": ["vp"], "customer": True},
    "mi": {"label": "MI · Why Samsung", "standard": ["mi", "why"], "quickwin": ["vp"], "solution": ["bigMi", "why"]},
    "birdseye": {"label": "조감도 · 공간별 제품", "standard": ["birdseye", "spaceProducts"], "quickwin": ["spaceProducts"], "solution": ["spaceScenario"]},
    "scenario": {"label": "솔루션 제안", "standard": ["solution"], "quickwin": ["solution"], "solution": ["spaceScenario"]},
    "image": {"label": "공간별 제품 이미지", "standard": ["spaceProducts"], "quickwin": ["spaceProducts"], "solution": ["spaceScenario"]},
    "spec": {"label": "제품 스펙", "standard": ["spec"], "quickwin": ["spec"], "solution": []},
    "vp": {"label": "Value Props", "standard": ["vp"], "quickwin": ["vp"], "solution": ["vp"]},
    "competitor": {"label": "Why Samsung", "standard": ["why"], "quickwin": [], "solution": ["why"]},
    "requirements": {"label": "고객 정보", "standard": [], "quickwin": [], "solution": [], "customer": True},
}
# 기본 체크(§10.8): 섹션을 「채움」으로 만드는 기능은 켬, 일부 재료(이미지 · 스펙)는 끔
WORK_DEFAULT_ON = {"storyboard", "mi", "birdseye", "scenario", "vp", "competitor", "requirements"}

# 반입 섹션의 연결 짧은 출처 글자(§10.8)
FILL_SOURCE_LABEL = {"mi": "MI 작업", "storyboard": "Storyboard", "birdseye": "조감도", "birdseye_layout": "조감도 배치안",
                     "scenario": "시나리오", "mi_competitor": "MI 경쟁사", "spec": "Spec 시트", "image": "이미지",
                     "vp": "Value Props", "competitor": "경쟁사 분석"}

# ── 역할(부록 A) ─────────────────────────────────────────────
# code: (이름, 말하는 것, PR3 이름, PR3 말하는 것, 템플릿 [(코드, 이름, 언제 쓰나)], 기본 템플릿(§10.5 기본값))
ROLES: dict[str, dict[str, Any]] = {
    "MS": {"name": "시장 규모 · 성장", "msg": "이 시장은 크고, 커지고 있다", "default": "MS-E", "templates": [
        ("MS-A", "핵심 수치 4", "지표는 여럿인데 연도별 추이는 없을 때"), ("MS-B", "성장 추이", "연도별 시장 규모 데이터가 있을 때"),
        ("MS-C", "TAM · SAM · SOM", "전체 중 노릴 수 있는 몫을 말할 때"), ("MS-D", "세그먼트 규모 × 성장률", "어디가 크고 빠른지, 고객 위치를 찍을 때"),
        ("MS-E", "성장 동인 → 전망", "수치는 적어도 왜 커지는지 설득할 때")]},
    "TR": {"name": "산업 트렌드", "msg": "업계가 이렇게 바뀐다", "default": "TR-B", "templates": [
        ("TR-A", "흐름 타임라인", "과거에서 다음으로 가는 방향을 보여줄 때"), ("TR-B", "트렌드 → 고객 시사점", "트렌드마다 '그래서 A 커피는'을 붙일 때"),
        ("TR-C", "영향도 × 시급성", "트렌드가 많아 우선순위가 필요할 때")]},
    "CB": {"name": "고객사 비즈니스", "msg": "고객을 제대로 이해했다", "default": "CB-A", "templates": [
        ("CB-A", "한 줄 요약 + 3단", "공개 자료로 현황을 요약할 때"), ("CB-B", "전략 목표 → 과제", "고객 전략과 이번 제안을 연결할 때"),
        ("CB-C", "운영 흐름 속 문제", "업무 단계마다 문제가 있을 때"), ("CB-D", "SWOT", "내부 · 외부 상황을 균형 있게 볼 때")]},
    "US": {"name": "사용자 분석", "msg": "고객의 손님과 직원을 안다", "default": "US-A", "templates": [
        ("US-A", "페르소나 3", "사용자 유형이 뚜렷이 나뉠 때"), ("US-B", "고객 여정 맵", "경험 흐름 속 개입 지점을 보여줄 때"),
        ("US-C", "사용자 구성 + 니즈", "방문객 구성 비율 데이터가 있을 때")]},
    "CP": {"name": "경쟁 환경", "msg": "시장 판도는 이렇다", "default": "CP-A", "templates": [
        ("CP-A", "비교표", "공급사를 항목별로 따져볼 때"), ("CP-B", "포지셔닝 맵", "구도와 빈자리를 한눈에 보여줄 때"),
        ("CP-C", "점유율 + 추이", "점유율 데이터가 있을 때")]},
    "IM": {"name": "MI 시사점", "msg": "그래서 이번 제안은", "default": "IM-A", "templates": [
        ("IM-A", "발견 → 시사점 → 방향", "MI를 제안 방향 하나로 좁힐 때"), ("IM-B", "4분면 요약 + 결론", "경영진용 한 장 요약")]},
    "CH": {"name": "고객 과제", "msg": "지금 이런 문제가 있다", "default": "CH-A", "templates": [
        ("CH-A", "과제 3 + 영향", "문제와 그 비용을 함께 보여줄 때"), ("CH-B", "지금 → 바라는 모습", "고객이 원하는 상태가 분명할 때"),
        ("CH-C", "문제 → 근본 원인", "원인을 짚어 제안의 필요성을 만들 때")]},
    "VP": {"name": "가치 제안", "msg": "우리는 이런 가치를 준다", "default": "VP-B", "templates": [
        ("VP-A", "과제 ↔ 해결 1:1", "과제마다 해법을 짝지을 때"), ("VP-B", "가치 기둥 2 · 3 · 4", "Key Message 수만큼 기둥으로 세울 때"),
        ("VP-C", "한 문장 + 근거 3", "메시지 하나를 강하게 말할 때"), ("VP-D", "이해관계자별 가치", "의사결정자가 여럿일 때")]},
    "EF": {"name": "기대 효과", "msg": "도입하면 이만큼 좋아진다", "default": "EF-C", "templates": [
        ("EF-A", "KPI 전 → 후", "개선 수치(전/후)가 있을 때"), ("EF-B", "투자 회수", "재무 관점으로 설득해야 할 때"),
        ("EF-C", "정량 + 정성 효과", "수치와 체감 효과를 함께 말할 때")]},
    "BV": {"name": "공간 전경", "msg": "완성된 공간을 미리 본다", "default": "BV-A", "templates": [
        ("BV-A", "풀폭 전경", "조감도 한 장으로 충분할 때"), ("BV-B", "두 시점 비교", "주간/야간, 도입 전/후를 비교할 때"),
        ("BV-C", "전경 + 한 장 요약", "경영진에게 제안 전체를 요약할 때")]},
    "ZP": {"name": "존별 포인트", "msg": "공간마다 무엇이 달라지나", "default": "ZP-A", "templates": [
        ("ZP-A", "번호 콜아웃", "조감도 한 장 위에 포인트를 찍을 때"), ("ZP-B", "존 확대 컷", "존마다 디테일 이미지가 있을 때"),
        ("ZP-C", "고객 동선 따라가기", "손님 동선 순서로 설명할 때")]},
    "SM": {"name": "공간 맵", "msg": "어디에 무엇을", "default": "SM-A", "templates": [
        ("SM-A", "존 맵 + 목록", "공간이 3곳 안팎일 때"), ("SM-B", "공간 × 제품 수량표", "공간 · 제품이 많아 교차표가 필요할 때")]},
    "PI": {"name": "공간 제품 소개", "msg": "이 공간에는 이 제품", "default": "P{n}-A", "templates": [
        ("P{n}-A", "제품 이미지 중심", "제품 사진이 좋을 때 (기본)"), ("P{n}-B", "공간 · 설치 중심", "설치 모습 · 조감도가 연결됐을 때"),
        ("P{n}-C", "스펙 · 비교 중심", "수치 비교 · 라인업이 핵심일 때"), ("P{n}-D", "강조형", "주력 제품을 지정했을 때")]},
    "BM": {"name": "구성 · 수량", "msg": "무엇을 몇 대", "default": "BM-A", "templates": [
        ("BM-A", "전체 구성표", "견적 전에 전체 물량을 확정할 때"), ("BM-B", "매장 유형별 구성", "매장 규모가 여러 가지일 때")]},
    "SA": {"name": "솔루션 구성도", "msg": "어떻게 연결되나", "pr3_name": "통합 구성도", "pr3_msg": "여러 솔루션이 어떻게 이어지나",
           "default": "SA-A", "templates": [
               ("SA-A", "계층형", "본사 → 클라우드 → 매장 구조일 때"), ("SA-B", "허브형", "솔루션 하나가 여러 기기를 묶을 때"),
               ("SA-C", "레이어 스택", "제공 범위(누가 무엇을)를 보여줄 때")]},
    "OP": {"name": "운영 시나리오", "msg": "어떻게 쓰이나", "pr3_name": "통합 운영 시나리오", "pr3_msg": "솔루션들이 함께 어떻게 쓰이나",
           "default": "OP-A", "templates": [
               ("OP-A", "단계 타임라인", "하루 · 이벤트 흐름을 따라갈 때"), ("OP-B", "역할별 스윔레인", "여러 역할이 한 흐름에 관여할 때"),
               ("OP-C", "도입 전 → 후 업무", "업무가 얼마나 줄어드는지 보여줄 때")]},
    "SF": {"name": "솔루션 상세", "msg": "이 솔루션은 무엇을 하나", "default": "SF-A", "templates": [
        ("SF-A", "솔루션 + 함께 쓰는 제품", "솔루션 하나를 소개할 때"), ("SF-B", "기능 → 고객 효과", "기능을 고객의 언어로 옮길 때")]},
    "SXI": {"name": "솔루션 소개", "msg": "이 솔루션은 무엇이고, 언제 쓰나", "default": None, "templates": [
        ("SF-A", "솔루션 + 함께 쓰는 제품", "솔루션 하나를 소개할 때"), ("SF-B", "기능 → 고객 효과", "기능을 고객의 언어로 옮길 때")]},
    "SXD": {"name": "솔루션 구성도", "msg": "어떻게 연결되고 움직이나", "default": None, "templates": [
        ("SA-A", "계층형", "본사 → 클라우드 → 매장 구조일 때"), ("SA-B", "허브형", "솔루션 하나가 여러 기기를 묶을 때"),
        ("SA-C", "레이어 스택", "제공 범위(누가 무엇을)를 보여줄 때")]},
    "SXS": {"name": "솔루션 공간 시나리오", "msg": "고객의 공간에서 언제 · 어디서 일하나", "default": None, "templates": [
        ("OP-A", "단계 타임라인", "하루 · 이벤트 흐름을 따라갈 때"), ("OP-B", "역할별 스윔레인", "여러 역할이 한 흐름에 관여할 때"),
        ("SS-A", "한 공간의 장면 3", "시간대별 장면이 있을 때")]},
    "VM": {"name": "공간 × 솔루션 전체 맵", "msg": "공간마다 어떤 솔루션이", "pr3_name": "공간 × 솔루션 맵", "pr3_msg": "공간마다 어떤 솔루션이",
           "default": "VM-A", "templates": [
               ("VM-A", "공간 × 솔루션 매트릭스", "공간과 솔루션이 격자로 맞을 때"), ("VM-B", "공간 3개 한 장", "공간이 3곳이라 나란히 볼 때"),
               ("VM-C", "조감도 위 솔루션 핀", "조감도가 있어 위치로 보여줄 때"), ("VM-D", "하루 타임라인 × 공간", "시간에 따라 공간을 넘나들 때")]},
    "SS": {"name": "공간 시나리오", "msg": "이 공간에서 이렇게 가치가 생긴다", "default": "SS-B", "templates": [
        ("SS-A", "한 공간의 장면 3", "시간대별 장면이 있을 때"), ("SS-B", "솔루션 → 제품 → 가치", "인과(무엇이 · 무엇으로 · 어떤 가치)를 보일 때"),
        ("SS-C", "이 공간 전 → 후", "변화가 눈에 보이는 공간일 때")]},
    "CD": {"name": "사례 상세", "msg": "비슷한 고객이 이렇게 성공했다", "default": "CD-A", "templates": [
        ("CD-A", "과제 · 해결 · 성과", "사례를 이야기로 풀 때"), ("CD-B", "도입 전 → 후 사진", "전후 사진이 있을 때"),
        ("CD-C", "성과 수치 + 코멘트", "공개된 성과 수치가 강할 때")]},
    "CL": {"name": "사례 모음", "msg": "이미 여러 곳에서 검증됐다", "default": "CL-A", "templates": [
        ("CL-A", "2건 비교", "비슷한 사례 두 건을 나란히"), ("CL-B", "3건 요약", "업종이 다른 사례 세 건"), ("CL-C", "레퍼런스 월", "사례 수 자체가 메시지일 때")]},
    "CM": {"name": "경쟁 비교", "msg": "경쟁사보다 낫다", "default": "CM-A", "templates": [
        ("CM-A", "비교표 (삼성 강조)", "항목별로 우위를 보일 때"), ("CM-B", "요구사항별 충족도", "고객 요구사항을 기준으로 비교할 때"),
        ("CM-C", "레이더 종합 비교", "여러 기준을 한 번에 종합할 때")]},
    "ST": {"name": "삼성 강점", "msg": "삼성이어야 하는 이유", "default": "ST-A", "templates": [
        ("ST-A", "강점 3", "강점이 3개로 정리될 때"), ("ST-B", "요구 ↔ 강점 2×2", "요구사항 4개에 하나씩 답할 때"), ("ST-C", "강점 + 증거 수치", "검증된 수치가 있을 때")]},
    "SV": {"name": "지원 체계", "msg": "도입 후에도 책임진다", "default": "SV-A", "templates": [
        ("SV-A", "도입 로드맵", "일정 · 단계 · 책임을 제시할 때"), ("SV-B", "서비스 커버리지 + SLA", "매장이 전국에 흩어져 있을 때")]},
    "SC": {"name": "스펙 비교", "msg": "제품별 사양 차이", "default": "SC-A", "templates": [
        ("SC-A", "사양 비교표 2~5개", "제품 간 사양 차이를 볼 때"), ("SC-B", "요구사항 대응표", "요구사항 충족을 증명해야 할 때")]},
    "SD": {"name": "제품 상세", "msg": "한 제품의 모든 것", "default": "SD-A", "templates": [
        ("SD-A", "그룹별 상세 사양", "사양 전체를 정리할 때"), ("SD-B", "치수 · 설치 정보", "설치 검토가 필요할 때")]},
}
ROLE_SECTION_HINT = {  # 역할이 보통 들어가는 섹션(반입 「섹션에 없는 시트」 판정 · 새 시트 위치)
    "MS": "mi", "TR": "mi", "CB": "mi", "US": "mi", "CP": "mi", "IM": "mi", "CH": "vp", "VP": "vp", "EF": "vp",
    "BV": "birdseye", "ZP": "birdseye", "SM": "spaceProducts", "PI": "spaceProducts", "BM": "spaceProducts",
    "SA": "solution", "OP": "solution", "SF": "solution", "SXI": "solution", "SXD": "solution", "SXS": "solution",
    "VM": "spaceScenario", "SS": "spaceScenario", "CD": "cases", "CL": "cases", "CM": "why", "ST": "why", "SV": "why",
    "SC": "spec", "SD": "spec",
}
PI_VARIANTS = {"A": ("제품 이미지 중심", "제품 사진이 좋을 때 (기본)"), "B": ("공간 · 설치 중심", "설치 모습 · 조감도가 연결됐을 때"),
               "C": ("스펙 · 비교 중심", "수치 비교 · 라인업이 핵심일 때"), "D": ("강조형", "주력 제품을 지정했을 때")}

# ── 솔루션(부록 B) ───────────────────────────────────────────
SOLUTIONS: dict[str, dict[str, Any]] = {
    "MGI": {"name": "MagicINFO", "desc": "설치형 사이니지 CMS", "I": "서버 · 보안 요건과 데이터 연동을 앞세울 때", "D": "사내 서버 · 방화벽 안에서 도는 구조",
            "S": "가격이 바뀌면 매장까지 몇 분 — 데이터 연동 흐름", "ind": ["RT", "HT"], "kb": "sol_magicinfo",
            "kw": ["magicinfo", "매직인포", "사내 서버", "콘텐츠 관리", "cms", "메뉴보드", "콘텐츠 일괄", "일괄 배포", "pos"]},
    "VXT": {"name": "Samsung VXT", "desc": "클라우드 사이니지 CMS", "I": "설치 없이 바로 쓰는 구독형임을 강조할 때", "D": "매장엔 화면만, 나머지는 클라우드",
            "S": "점장이 휴대폰으로 3분 만에 교체", "ind": ["RT", "GF"], "kb": "sol_vxt", "kw": ["vxt", "클라우드 cms", "클라우드 사이니지"]},
    "STP": {"name": "SmartThings Pro", "desc": "여러 사업장 IoT · 에너지", "I": "여러 매장의 기기 · 에너지를 한 화면에", "D": "기기는 매장에, 판단은 클라우드에",
            "S": "매장의 하루 — 에너지 자동화", "ind": ["OF", "HT", "GF"], "kb": "sol_smartthings_pro",
            "kw": ["smartthings", "스마트싱스", "에너지", "iot", "영업시간"]},
    "BIT": {"name": "b.IoT", "desc": "공조 중심 빌딩 관리 · b.IoT / Lite 비교", "I": "공조 중심 빌딩 관리 · b.IoT / Lite 비교", "D": "층별 설비 → 게이트웨이 → 관리 화면",
            "S": "층 × 시간 — 쓰는 층만 쾌적하게", "ind": ["HT", "RT"], "kb": "sol_biot", "kw": ["b.iot", "빌딩 관리", "공조 관리"]},
    "LYN": {"name": "LYNK Cloud", "desc": "투숙객 · 호텔 양쪽의 가치", "I": "투숙객 · 호텔 양쪽의 가치", "D": "PMS ↔ LYNK Cloud ↔ 객실 TV",
            "S": "체크인부터 체크아웃까지 객실 TV", "ind": ["HT"], "kb": "sol_lynk_cloud", "kw": ["lynk", "객실 tv", "호텔 tv"]},
    "KNX": {"name": "Knox Suite", "desc": "업무용 갤럭시 관리 · 보안", "I": "받는 날부터 회수까지 — 기기 수명주기", "D": "콘솔 하나 · 기기 속 업무 영역",
            "S": "새 태블릿이 매장에서 바로 일하기까지", "ind": ["AC", "FD"], "kb": "sol_knox", "kw": ["knox", "녹스", "태블릿", "단말 관리", "mdm"]},
    "KCP": {"name": "Knox Capture", "desc": "전용 스캐너 + 단말 → 갤럭시 1대", "I": "전용 스캐너 + 단말 → 갤럭시 1대", "D": "스캔 값이 기존 앱까지 가는 길",
            "S": "입고부터 계산대까지 한 대로", "ind": ["LG"], "kb": None, "kw": ["knox capture", "바코드", "스캐너"]},
    "DEX": {"name": "Samsung DeX", "desc": "휴대폰 하나로 PC 업무까지", "I": "휴대폰 하나로 PC 업무까지", "D": "연결 방식 · 업무 자원 · 보안",
            "S": "영업 사원의 하루, 기기는 하나", "ind": ["OF", "FD"], "kb": None, "kw": ["dex", "덱스"]},
    "CCH": {"name": "삼성 콜드체인", "desc": "냉장 · 냉동 + 에어컨 통합 관리", "I": "성능 · 설치 · 관리 · 서비스 4 UP", "D": "실외기 → 쇼케이스 · 저장고 → b.IoT Cloud",
            "S": "한여름 오후 · 새벽에도 보관 온도 유지", "ind": ["RT", "WH"], "kb": None, "kw": ["콜드체인", "냉장", "냉동", "쇼케이스"]},
    "HVC": {"name": "삼성 통합공조", "desc": "개별 + 중앙공조 + b.IoT", "I": "개별 + 중앙공조 = b.IoT 하나로", "D": "열원 → 냉수 → AHU · FCU, 개별 DVM",
            "S": "건물마다 다른 운전 시간을 한 화면에", "ind": ["OF", "HT"], "kb": None, "kw": ["통합공조", "중앙공조", "공조"]},
    "SAC": {"name": "SAC 제어 시스템", "desc": "시스템에어컨 제어 · 전력량 분배", "I": "리모컨부터 BMS 연동까지 제어 단계", "D": "DMS · R1/R2 · F1/F2 통신 구조",
            "S": "임대 호실별 제어 · 전력량 분배", "ind": ["AC", "GF"], "kb": "sol_dms", "kw": ["시스템에어컨 제어", "dms", "전력량 분배"]},
}
SOLUTION_INDUSTRY_NAME = {"OF": "오피스", "HT": "비즈니스 호텔", "RT": "매장", "GF": "스크린골프장", "AC": "학원", "LG": "물류센터",
                          "FD": "제조 현장", "WH": "저온 저장시설"}
# 고객 업종(16) → 솔루션 업종 코드(부록 B 제안 대응, ⚠Q21)
CUSTOMER_TO_SOL_IND = {"FB": "RT", "RT": "RT", "SV": "RT", "HT": "HT", "OF": "OF", "ED": "AC", "MF": "FD"}
KB_SOLUTION_TO_CODE = {v["kb"]: k for k, v in SOLUTIONS.items() if v.get("kb")}
KB_SOLUTION_TO_CODE.update({"sol_vxt": "VXT", "sol_knox": "KNX", "sol_magicinfo": "MGI", "sol_smartthings_pro": "STP", "sol_smartthings": "STP",
                            "magicinfo": "MGI", "vxt": "VXT", "smartthings_pro": "STP", "knox": "KNX", "biot": "BIT", "lynk_cloud": "LYN"})


def solution_code_of(ref: str | None, label: str | None = None) -> str | None:
    """kb 솔루션 id · 카탈로그 id · 코드 · 이름 → 부록 B 코드."""
    for cand in (ref, label):
        if not cand:
            continue
        c = str(cand).strip()
        if c.upper() in SOLUTIONS:
            return c.upper()
        if c in KB_SOLUTION_TO_CODE:
            return KB_SOLUTION_TO_CODE[c]
        low = c.lower()
        for code, s in SOLUTIONS.items():
            if low == s["name"].lower() or low.replace(" ", "") == s["name"].lower().replace(" ", ""):
                return code
        for code, s in SOLUTIONS.items():
            if s["name"].lower() in low:
                return code
    return None


# ── 16업종(부록 C) ───────────────────────────────────────────
INDUSTRIES: dict[str, dict[str, Any]] = {
    "FB": {"name": "외식 · 카페", "full": "외식 · 카페 프랜차이즈", "wm": "wm_fnb_cafe", "kr": ["kr_fnb"]},
    "RT": {"name": "리테일 · 플래그십", "full": "리테일 · 브랜드 플래그십", "wm": "wm_retail", "kr": ["kr_retail"]},
    "SV": {"name": "생활 편의 · 무인 매장", "full": "생활 편의 · 무인 매장", "wm": "wm_convenience_unmanned", "kr": []},
    "HT": {"name": "호텔 · 리조트", "full": "호텔 · 리조트", "wm": "wm_hotel_resort", "kr": ["kr_hotel"]},
    "TP": {"name": "테마파크 · 전시", "full": "테마파크 · 관광 · 전시", "wm": "wm_theme_park", "kr": []},
    "VN": {"name": "공연장 · 경기장", "full": "공연장 · 경기장", "wm": "wm_venue", "kr": []},
    "AD": {"name": "옥외 광고", "full": "옥외 광고", "wm": "wm_ooh", "kr": []},
    "OF": {"name": "오피스", "full": "오피스", "wm": "wm_office", "kr": ["kr_office", "kr_small_office"]},
    "RS": {"name": "주거 분양", "full": "주거 분양", "wm": "wm_residential_sales", "kr": ["kr_home", "kr_officetel"]},
    "ID": {"name": "인테리어 · 빌트인", "full": "인테리어 · 빌트인", "wm": "wm_interior_partner", "kr": []},
    "ED": {"name": "교육 · 캠퍼스", "full": "교육 · 캠퍼스", "wm": "wm_education", "kr": ["kr_school", "kr_academy"]},
    "PB": {"name": "공공 · 교통", "full": "공공 · 교통", "wm": "wm_public", "kr": ["kr_public_agency", "kr_military"]},
    "MD": {"name": "의료 · 요양", "full": "의료 · 요양", "wm": "wm_medical_care", "kr": ["kr_hospital", "kr_clinic"]},
    "MF": {"name": "제조 · 물류 · 현장", "full": "제조 · 물류 · 현장", "wm": "wm_manufacturing_logistics", "kr": ["kr_manufacturing", "kr_transport"]},
    "FN": {"name": "금융", "full": "금융", "wm": "wm_finance", "kr": ["kr_finance"]},
    "OE": {"name": "파트너 전용 단말", "full": "파트너 전용 단말", "wm": "wm_partner_device", "kr": []},
}
INDUSTRY_CODES = tuple(INDUSTRIES)
WM_TO_CODE = {v["wm"]: k for k, v in INDUSTRIES.items()}
KR_TO_CODES: dict[str, list[str]] = {}
for _c, _v in INDUSTRIES.items():
    for _kr in _v["kr"]:
        KR_TO_CODES.setdefault(_kr, []).append(_c)
KR_TO_CODES.setdefault("kr_retail_fnb", ["FB"])
# PR1 업종 칩(넓은 묶음 → 16코드 후보, ⚠Q9)
INDUSTRY_CHIPS = {"리테일 · F&B": ["FB", "RT", "SV"], "호스피탈리티": ["HT", "TP", "VN"], "교육": ["ED"], "헬스케어": ["MD"]}
INDUSTRY_GROUP_LABEL = {"FB": "리테일/F&B", "RT": "리테일/F&B", "SV": "리테일/F&B", "HT": "호스피탈리티", "TP": "호스피탈리티",
                        "VN": "호스피탈리티", "ED": "교육", "MD": "헬스케어"}


def industry_code_of(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    if v.upper() in INDUSTRIES:
        return v.upper()
    if v in WM_TO_CODE:
        return WM_TO_CODE[v]
    if v in KR_TO_CODES and len(KR_TO_CODES[v]) >= 1:
        return KR_TO_CODES[v][0]
    for code, ind in INDUSTRIES.items():
        if v in (ind["name"], ind["full"]) or v.replace(" ", "") == ind["name"].replace(" ", ""):
            return code
    keywords = {"카페": "FB", "커피": "FB", "외식": "FB", "프랜차이즈": "FB", "베이커리": "FB", "병원": "MD", "의료": "MD", "요양": "MD",
                "호텔": "HT", "리조트": "HT", "대학": "ED", "학교": "ED", "학원": "ED", "물류": "MF", "제조": "MF", "공장": "MF",
                "오피스": "OF", "사무": "OF", "금융": "FN", "은행": "FN", "리테일": "RT", "매장": "RT", "편의점": "SV", "무인": "SV"}
    for kw, code in keywords.items():
        if kw in v:
            return code
    return None


# 업종 레이아웃 변형(IROLE 원문)
IROLE: dict[str, dict[str, tuple[str, str, str]]] = {
    "MI": {"A": ("시장 · 트렌드", "barline", "업종 시장 규모 · 동인 → 그래서 고객에게"),
           "B": ("고객 비즈니스 · 운영 과제", "process", "업종 사업 구조 · KPI · 운영 과제"),
           "C": ("사용자 여정", "journey", "사용자 · 이해관계자 여정과 개입 지점")},
    "VP": {"A": ("과제 → 해법 → 효과", "indVP", "업종 핵심 과제마다 삼성 해법과 효과"),
           "B": ("이해관계자별 가치", "persona", "업종의 결정권자 · 이용자별 가치"),
           "C": ("기대 효과", "hbars", "업종 KPI 전 → 후 · 투자 효과")},
    "SS": {"A": ("공간 맵", "indMap", "업종 공간 전체 × 제품 · 솔루션 · 가치"),
           "B": ("대표 공간 장면", "scenes", "업종의 핵심 공간 한 곳의 장면"),
           "C": ("하루 · 동선", "indDay", "하루 · 동선 · 역할별 스윔레인")},
}
FAMILY_NAME = {"MI": "Market Intelligence", "VP": "Value Props", "SS": "공간 시나리오"}
# 역할 → 업종 레이아웃(IND_FOR 원문) — 고르기 목록 맨 앞
IND_FOR = {"MS": ("MI", "A"), "TR": ("MI", "A"), "CB": ("MI", "B"), "CP": ("MI", "B"), "IM": ("MI", "B"), "US": ("MI", "C"),
           "CH": ("VP", "A"), "VP": ("VP", "A"), "EF": ("VP", "C"), "VM": ("SS", "A"), "SM": ("SS", "A"), "SS": ("SS", "B"), "OP": ("SS", "C")}

# ── 시트 구성 기본값(부록 E) ─────────────────────────────────
# (코드, 기본 상태, 반복 종류|None, 기본 반복 수, 자료 원문)
COMPOSITION: dict[str, list[tuple[str, str, str | None, int, str]]] = {
    "mi": [("MS", "on", None, 1, "MI 작업에서"), ("CB", "on", None, 1, "MI 작업에서"), ("CP", "on", None, 1, "MI 작업에서"),
           ("TR", "off", None, 1, "새로 조사"), ("US", "off", None, 1, "새로 조사"), ("IM", "rec", None, 1, "MI 내용을 요약")],
    "bigMi": [("MS", "on", None, 1, "MI 작업 2건"), ("TR", "on", None, 1, "MI 작업 2건"), ("CB", "on", None, 1, "MI 작업에서"),
              ("US", "on", None, 1, "인터뷰 자료"), ("CP", "on", None, 1, "MI 작업에서"), ("IM", "rec", None, 1, "MI 내용을 요약")],
    "vp": [("CH", "on", None, 1, "Storyboard에서"), ("VP", "on", None, 1, "Storyboard에서"), ("EF", "rec", None, 1, "유사 사례로 추정")],
    "birdseye": [("BV", "on", None, 1, "조감도 작업에서"), ("ZP", "on", None, 1, "조감도 작업에서")],
    "spaceProducts": [("SM", "on", None, 1, "조감도 배치안"), ("PI", "on", "space", 3, "공간마다 1장 · 배치안 {n}곳"),
                      ("BM", "off", None, 1, "제품 목록으로 계산")],
    # 솔루션 행은 연결 · 추천에 따라 만든다(build_solution_rows). SA · OP 만 고정
    "solution": [("SA", "on", None, 1, "솔루션이 2개 이상일 때"), ("OP", "off", None, 1, "시나리오 작업에서")],
    "cases": [("CD", "on", "case", 2, "사례마다 1장 · 추천 {n}건"), ("CL", "off", None, 1, "사례 검색")],
    "why": [("CM", "on", None, 1, "MI 경쟁사 분석"), ("ST", "on", None, 1, "MI 경쟁사 분석"), ("SV", "rec", None, 1, "서비스 표준 자료")],
    "spec": [("SC", "on", None, 1, "Spec 시트 작업"), ("SD", "on", "product", 1, "주력 제품마다 1장")],
    "spaceScenario": [("VM", "on", None, 1, "시나리오 · 조감도"), ("SS", "on", "space", 3, "공간마다 1장 · {n}곳")],
}
SOLUTION_SRC_ON = "연결된 솔루션"
SOLUTION_SRC_REC = "요구사항에 {why}"
SOLUTION_SRC_OFF = "솔루션 탐색에서 추가"
TEMPLATE_COUNT_PR3 = {"MS": 5, "TR": 3, "CB": 4, "US": 3, "CP": 3, "IM": 2, "CH": 3, "VP": 4, "EF": 3, "BV": 3, "ZP": 3, "SM": 2, "PI": 20,
                      "BM": 2, "SA": 3, "OP": 3, "SF": 2, "VM": 4, "SS": 3, "CD": 3, "CL": 3, "CM": 3, "ST": 3, "SV": 2, "SC": 2, "SD": 2}

# ── 빠른 요청 칩 → 요청 문장(§7.4 제안) ─────────────────────
QUICK_ACTIONS: dict[str, dict[str, Any]] = {
    "수치 근거 보강": {"text": "이 섹션 수치마다 출처를 찾아 붙이고 없으면 확정 필요로", "job": True},
    "더 간결하게": {"text": "이 섹션 시트 문장을 더 간결하게 다듬어 줘", "job": True},
    "조사 범위 넓히기": {"text": "MI 조사 범위를 넓혀 산업 · 경쟁 내용을 보강해 줘", "job": True, "generate": "mi"},
    "출처 보기": {"job": False, "panel": "sources"},
    "가치 하나 추가": {"text": "가치 제안 기둥을 하나 더 추가해 줘", "job": True},
    "경영진 톤으로": {"text": "경영진이 읽기 좋게 결론부터 쓰는 톤으로 바꿔 줘", "job": True},
    "시점 추가": {"job": False, "navigate": "/birdseye/new"},
    "조감도 새로 만들기": {"job": False, "navigate": "/birdseye/new"},
    "공간 추가": {"text": "공간을 하나 더 추가해 줘", "job": True},
    "수량 조정": {"job": False, "prefill": "수량 조정: "},
    "통합 운영 시나리오 추가": {"text": "통합 운영 시나리오 시트를 추가해 작성해 줘", "job": True, "add_role": "OP"},
    "운영 비용 추가": {"text": "솔루션 운영 비용 항목을 추가해 줘", "job": True},
    "성과 수치 강조": {"text": "사례의 성과 수치를 강조해 줘", "job": True},
    "사례 한 장으로 모으기": {"text": "사례를 한 장으로 모아 줘", "job": True, "add_role": "CL"},
    "비교 항목 추가": {"text": "경쟁 비교표에 비교 항목을 하나 추가해 줘", "job": True},
    "레퍼런스 강조": {"text": "삼성 도입 레퍼런스를 강조해 줘", "job": True},
    "제품별로 나누기": {"text": "제품 상세 시트를 제품마다 나눠 줘", "job": True},
    "영문 스펙": {"text": "스펙 표에 영문을 병기해 줘", "job": True},
    "솔루션 추가": {"text": "공간별 가치 시나리오에 솔루션을 하나 추가해 줘", "job": True},
    "템플릿 바꾸기": {"job": False, "panel": "template"},
}

# ── 플레이스홀더 · 확인 항목(§10.1 · §5.8) ──────────────────
PLACEHOLDER_RE = re.compile(r"\[0{1,2}\]\s?(%|일|명|개|시간|억 원|만 원|nit|대|곳)?")
CONFIRM_MARK_RE = re.compile(r"\[(확정 필요|확인 필요|수치 확정 필요|TBD)\]")
FACT_TOKEN_RE = re.compile(r"\{\{fact:(fct_[A-Za-z0-9]+)\}\}")
CONFIRM_TAGS = ("수치", "고객 확인", "공개 여부", "값 불일치", "단종 치환", "정책", "값 전파", "수량 가정", "경쟁사 실명", "검토 코멘트", "claim")
CONFIRM_STATUS_LABEL = {"open": "남음", "confirmed": "확정", "moved_to_note": "노트로 옮김", "dismissed": "닫음"}
CLAIM_WORDS = ("최초", "유일", "최고", "1위", "독보적", "보장", "100%")
NONCOPY_KEYWORDS = ("가격", "견적", "단가", "할인", "VAT", "부가세", "계약", "일정", "납기", "매출", "영업이익", "원가")

# ── 디자인(§3.10 · §5.9) ─────────────────────────────────────
MASTERS = [
    {"id": "samsung_b2b", "name": "삼성 B2B 표준", "desc": "화이트 + 삼성 블루 · 16:9 · 사내 표준 마스터"},
    {"id": "retail_fnb", "name": "리테일 · F&B 변형", "desc": "이미지 비중 큰 레이아웃 · 매장 사진 강조"},
    {"id": "simple_white", "name": "심플 화이트", "desc": "텍스트 중심 · 경영진 보고용"},
]
DEFAULT_MASTER = "samsung_b2b"
BRAND_BLUE = "#1428A0"
BRAND_DARK = "#121417"
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# ── 기존 제안서 활용(§10.9) ─────────────────────────────────
CRITERIA = [
    (1, "structure", "문서 구조", False, "auto"),
    (2, "flow", "논리 흐름", True, "check"),
    (3, "messages", "핵심 메시지", False, "auto"),
    (4, "context", "고객 · 프로젝트 맥락", True, "ask"),
    (5, "products", "제품 · 솔루션", False, "auto"),
    (6, "numbers", "데이터 · 수치", False, "auto"),
    (7, "images", "이미지 · 자산", False, "auto"),
    (8, "design", "디자인 · 템플릿", False, "check"),
    (9, "noncopy", "비복제 · 민감 항목", True, "auto"),
]
MUST_CRITERIA = (2, 4, 9)
CRITERION_STATE_LABEL = {"ok": "확인됨", "need": "확인 필요", "edited": "수정함"}
VERDICT_LABEL = {"keep": "유지", "update": "갱신", "rewrite": "재작성", "new": "신규", "drop": "제외", "auto": "자동"}
FLOW_ROLES = ["표지", "문제 제기", "시장 변화", "고객 과제", "가치 제안", "솔루션 구성", "도입 사례", "제품 스펙", "견적 · 일정", "공간 시나리오",
              "Why Samsung · 경쟁 비교"]
# 흐름 단계 → 이번 제안서 섹션(§10.9 표)
FLOW_TO_SECTION = {"문제 제기": None, "시장 변화": "mi", "고객 과제": "vp", "가치 제안": "vp", "솔루션 구성": "solution",
                   "공간 시나리오": "spaceScenario", "도입 사례": "cases", "제품 스펙": "spec", "견적 · 일정": None,
                   "Why Samsung · 경쟁 비교": "why", "표지": None}
FILE_MAX_MB = 50
REUSE_FORMATS = {"pptx", "pdf"}
RFP_FORMATS = {"pdf", "docx", "pptx", "txt", "eml", "hwpx"}

# ── 진행 라벨 · 목록(§10.11) ────────────────────────────────
ROW_ACTIONS = ("검토 보기", "버전 보기", "확인할 곳", "이어서 작성", "복제해서 시작")
DUE_URGENT_DAYS = 7
DUE_SOON_DAYS = 14
CHANGE_TTL_DAYS = 30
ONE_CLICK_ETA = "약 1–2분"
