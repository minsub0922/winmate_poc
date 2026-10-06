"""큐레이션 사전 · 결정적 파서 (사람이 검수하는 영역).

build_kb.py 가 `import curation as C` 로 쓴다. 여기 있는 것은 전부 "사실"이 아니라
사이트 원문을 DB 구조로 옮기기 위한 규칙·사전이다. 사실(제품명·수치·문구)은 항상 원문에서 온다.

- 공간 라벨 사전: 업종 페이지에 실제로 쓰인 공간 표현 → space_type 코드
- 자동 역량 규칙(AUTO_RULES): 사이트 필터·스펙·문구에 '있다/없다'만 보는 presence 규칙(임계값 판단 없음)
- 업종 페이지 파서: h2 장면 → 설명 → 공간 라벨 → h3 항목 + '자세히 보기' 링크 + 이미지
- 이미지 등급 힌트: 페이지 유형·파일명으로 정한 1차 힌트(VLM 판정 전)
"""
from __future__ import annotations

import re

# ── 업종 ────────────────────────────────────────────────
US_VERTICAL_SLUGS = {
    "finance": "us_finance", "government": "us_government", "healthcare": "us_healthcare",
    "hospitality": "us_hospitality", "manufacturing": "us_manufacturing", "public-safety": "us_public_safety",
    "retail": "us_retail", "education": "us_education", "transportation": "us_transportation",
    "corporate": "us_corporate", "live-events-sports": "us_live_events_sports",
    "quick-service-restaurant": "us_qsr", "cinema": "us_cinema",
}

KR_CASE_INDUSTRY = {
    "공공": "kr_public", "제조": "kr_manufacturing", "금융": "kr_finance", "교육": "kr_education",
    "건설": "kr_construction", "유통/요식": "kr_retail_fnb", "운송": "kr_transport", "의료": "kr_medical",
    "호텔/서비스": "kr_hotel", "통신": "kr_telecom",
}

RESIDENTIAL_VERTICALS = {"kr_construction", "kr_home", "kr_officetel"}
COMMERCIAL_KITCHEN_VERTICALS = {"kr_fnb", "kr_retail_fnb", "kr_hotel", "kr_hospital", "kr_medical", "kr_military",
                                "kr_public", "kr_school", "kr_education", "us_qsr", "us_hospitality"}

# ── 공간 ────────────────────────────────────────────────
# 시드(space_types.yaml)에 없지만 KR 업종 페이지에서 실제 라벨로 관측된 공간
EXTRA_SPACE_TYPES = [
    ("research_lab", "연구실"),
    ("teachers_office", "교무실"),
    ("consultation_room", "상담실"),
    ("training_room", "교육장·연수실"),
    ("multipurpose_room", "다목적실"),
    ("barracks", "병영 생활관"),
    ("cafeteria", "구내식당·급식실"),
    ("vip_lounge", "VIP 공간"),
    ("lounge", "라운지"),
    ("fitness", "피트니스·체육 공간"),
    ("operating_room", "수술실"),
    ("dress_room", "드레스룸"),
    ("common_area", "공용부"),
    ("vehicle", "차량 내부"),
    ("laundry_room", "세탁실"),
    ("restroom", "화장실"),
]


def _k(s: str) -> str:
    return re.sub(r"[\s()\[\]·∙/\-_*]+", "", (s or "")).lower()


# 업종 페이지 라벨(정확 일치, 공백·괄호 무시) → space_type
LABEL_KO = {
    "객실": "guest_room", "객실내부": "guest_room", "호텔리셉션": "front_desk", "호텔라운지": "lounge",
    "연회장": "banquet_hall", "휘트니스공간": "fitness", "피트니스": "fitness",
    "로비": "lobby", "병원로비": "lobby", "사무실": "open_office", "업무공간": "open_office",
    "민원실": "civil_service_counter", "다목적실": "multipurpose_room",
    "병영생활관": "barracks", "병영식당": "cafeteria", "교육장": "training_room",
    "연구실": "research_lab", "공장": "factory_floor", "물류센터": "warehouse",
    "매장": "sales_floor", "대형매장": "sales_floor", "중소형매장": "sales_floor",
    "지점공간": "bank_branch", "vip공간": "vip_lounge", "대기공간": "waiting_area",
    "교실": "classroom", "강의실": "classroom", "교무실": "teachers_office", "급식실": "cafeteria",
    "학원입구": "entrance", "학원인포데스크": "front_desk", "상담실": "consultation_room",
    "침실": "residential_bedroom", "거실": "residential_living", "침실거실": "residential_bedroom",
    "드레스룸": "dress_room", "커뮤니티공간": "apartment_common", "공용부": "common_area",
    "회의실": "meeting_room", "대강당컨퍼런스룸": "lecture_hall", "라운지": "lounge",
    "drivethrough": "drive_thru", "드라이브스루": "drive_thru",
    "매장입구": "entrance", "주문공간": "order_counter", "결제공간": "order_counter",
    "식음공간": "dining_hall", "관리공간": "back_of_house",
    "공항라운지": "lounge", "공항탑승대기실": "transit_concourse", "지하철": "transit_concourse",
    "택시": "vehicle", "통합원무과": "hospital_reception", "진료대기실": "waiting_area",
    "입원실": "patient_room", "간이조리실": "pantry_lounge", "진료실": "exam_room",
    "수술실": "operating_room", "세미나실": "meeting_room",
}
MULTI_LABEL_KO = {"침실거실": ["residential_bedroom", "residential_living"]}

# 부분 일치(제목·도입사례 공간 문자열용). 긴 것부터 검사한다.
KW_KO = [
    ("디지털 상황실", "control_room"), ("상황실", "control_room"), ("관제", "control_room"), ("통제실", "control_room"),
    ("컨퍼런스", "meeting_room"), ("회의실", "meeting_room"), ("세미나실", "meeting_room"),
    ("대강당", "lecture_hall"), ("강당", "lecture_hall"), ("강의실", "classroom"), ("교실", "classroom"),
    ("도서관", "library"), ("체육관", "fitness"), ("피트니스", "fitness"), ("휘트니스", "fitness"),
    ("급식", "cafeteria"), ("구내식당", "cafeteria"), ("병영 식당", "cafeteria"),
    ("객실", "guest_room"), ("연회", "banquet_hall"), ("로비", "lobby"), ("리셉션", "front_desk"),
    ("프런트", "front_desk"), ("인포데스크", "front_desk"), ("안내데스크", "front_desk"),
    ("라운지", "lounge"), ("대기실", "waiting_area"), ("대기 공간", "waiting_area"),
    ("병실", "patient_room"), ("입원실", "patient_room"), ("진료실", "exam_room"), ("수술실", "operating_room"),
    ("간호", "nurse_station"), ("약국", "pharmacy"), ("원무", "hospital_reception"),
    ("민원", "civil_service_counter"), ("영업점", "bank_branch"), ("지점", "bank_branch"), ("ATM", "atm_area"),
    ("모델하우스", "model_house"), ("견본주택", "model_house"), ("쇼룸", "exhibition_showroom"),
    ("전시", "exhibition_showroom"), ("영화관", "cinema"), ("상영관", "cinema"),
    ("경기장", "stadium_arena"), ("공연장", "stadium_arena"), ("스타디움", "stadium_arena"), ("야구장", "stadium_arena"),
    ("테마파크", "theme_park_attraction"), ("공항", "transit_concourse"), ("터미널", "transit_concourse"),
    ("지하철", "transit_concourse"), ("기차역", "transit_concourse"),
    ("물류", "warehouse"), ("창고", "warehouse"), ("냉동", "cold_storage"), ("공장", "factory_floor"),
    ("생산 라인", "factory_floor"), ("생산라인", "factory_floor"),
    ("주차", "parking"), ("외벽", "outdoor_facade"), ("옥외", "outdoor_facade"), ("외관", "outdoor_facade"),
    ("쇼윈도", "storefront_window"), ("엘리베이터", "elevator_hall"), ("복도", "corridor_wayfinding"),
    ("드라이브", "drive_thru"), ("카운터", "order_counter"), ("매장", "sales_floor"),
    ("카페", "dining_hall"), ("레스토랑", "dining_hall"), ("식당", "dining_hall"), ("사무 공간", "open_office"),
    ("임원", "executive_office"), ("탕비", "pantry_lounge"), ("사무실", "open_office"), ("오피스", "open_office"),
    ("거실", "residential_living"), ("침실", "residential_bedroom"), ("드레스룸", "dress_room"),
    ("커뮤니티", "apartment_common"), ("공용부", "common_area"), ("연구실", "research_lab"),
    ("생활관", "barracks"), ("교무실", "teachers_office"), ("상담실", "consultation_room"),
    ("입구", "entrance"),
    ("휴게", "pantry_lounge"), ("미팅룸", "meeting_room"), ("객장", "bank_branch"), ("세탁실", "laundry_room"),
    ("세탁 공간", "laundry_room"), ("현관", "entrance"), ("기계실", "server_room"), ("서버실", "server_room"),
    ("조정실", "control_room"), ("컨벤션", "banquet_hall"), ("체력단련", "fitness"), ("화장실", "restroom"),
    ("체험존", "exhibition_showroom"), ("전시관", "exhibition_showroom"), ("홍보관", "exhibition_showroom"),
    ("데모존", "exhibition_showroom"), ("웰컴존", "lobby"), ("병동", "patient_room"), ("응급실", "exam_room"),
    ("오피스텔", ""), ("실외기", ""), ("실내기", ""), ("역사적", ""),   # 함정 표현: 공간이 아님(구간만 소비)
]
KW_KO.sort(key=lambda x: len(x[0]), reverse=True)

KW_EN = [
    ("conference room", "meeting_room"), ("meeting room", "meeting_room"), ("huddle", "meeting_room"),
    ("boardroom", "meeting_room"), ("classroom", "classroom"), ("lecture", "lecture_hall"),
    ("guest room", "guest_room"), ("in-room", "guest_room"), ("connected room", "guest_room"), ("accommodation", "guest_room"),
    ("lobby", "lobby"), ("entrance", "entrance"), ("wayfinding", "corridor_wayfinding"),
    ("drive-thru", "drive_thru"), ("drive thru", "drive_thru"), ("menu board", "menu_board_zone"),
    ("kiosk", "order_counter"), ("point of sale", "order_counter"), ("checkout", "order_counter"),
    ("casino", "casino_floor"), ("sportsbook", "casino_floor"), ("stadium", "stadium_arena"), ("arena", "stadium_arena"),
    ("concourse", "transit_concourse"), ("airport", "transit_concourse"),
    ("control room", "control_room"), ("command center", "control_room"), ("command centre", "control_room"),
    ("patient room", "patient_room"), ("bedside", "patient_room"), ("nurse", "nurse_station"),
    ("operating room", "operating_room"), ("warehouse", "warehouse"), ("factory", "factory_floor"),
    ("window", "storefront_window"), ("outdoor", "outdoor_facade"), ("in-store", "sales_floor"),
    ("dining", "dining_hall"), ("tableside", "dining_hall"), ("back-of-house", "back_of_house"),
    ("cinema", "cinema"), ("movie theater", "cinema"), ("bank branch", "bank_branch"),
]
KW_EN.sort(key=lambda x: len(x[0]), reverse=True)

SPACE_SUFFIX = re.compile(r"(실|공간|장|관|센터|매장|로비|라운지|공용부|입구|데스크|룸|홀|식당|원무과|생활관|Through)$", re.I)


def _kitchen(vertical):
    if vertical in RESIDENTIAL_VERTICALS:
        return "residential_kitchen"
    if vertical in COMMERCIAL_KITCHEN_VERTICALS:
        return "commercial_kitchen"
    return None


def spaces_for_label(text: str, lang: str = "ko", vertical: str | None = None) -> list[str]:
    """라벨 하나 → 공간 코드 목록(정확 일치 우선, 없으면 부분 일치 1개)."""
    if not text:
        return []
    if lang == "en":
        t = text.lower()
        for kw, code in KW_EN:
            if kw in t:
                return [code]
        return []
    k = _k(text)
    if k in MULTI_LABEL_KO:
        return list(MULTI_LABEL_KO[k])
    if k == "주방":
        sp = _kitchen(vertical)
        return [sp] if sp else []
    if k in LABEL_KO:
        return [LABEL_KO[k]]
    if "주방" in text and _kitchen(vertical):
        return [_kitchen(vertical)]
    sp = spaces_in_text(text, "ko", vertical)
    return [sp[0][0]] if sp else []


def space_for_label(text: str, lang: str = "ko", vertical: str | None = None) -> str | None:
    s = spaces_for_label(text, lang, vertical)
    return s[0] if s else None


def is_space_like(label: str) -> bool:
    k = _k(label)
    return k in LABEL_KO or k in MULTI_LABEL_KO or k == "주방" or bool(SPACE_SUFFIX.search(label.strip()))


# ── 제품 분류 ────────────────────────────────────────────
CATEGORY_TOP = {
    "top_hvac": "시스템에어컨·공조", "top_kitchen": "주방가전", "top_living": "리빙가전",
    "top_display": "사이니지", "top_tv_audio": "TV/음향", "top_mobile": "모바일",
    "top_it": "IT·PC·프린팅", "top_solution": "솔루션", "top_service": "서비스",
}
_TOP_OF = {
    "top_hvac": ["dvms", "cooling-single", "cooling-for-residential", "heat-pump-boilers", "ventilations",
                 "central-air-conditionings", "Cold_Chain_System", "dvms-indoor", "dvms-outdoor"],
    "top_kitchen": ["refrigerator", "kimchi-refrigerators", "dish-washer", "electric-range", "micro-wave-ovens",
                    "qooker", "water-purifier", "hood", "accessories", "built-in-appliances", "bespoke-kitchen"],
    "top_living": ["washing-machines", "dryers", "airdresser", "shoedresser", "air-conditioners", "air-cleaners",
                   "vacuum-cleaners", "led-lights"],
    "top_display": ["smart-signage", "led-signage"],
    "top_tv_audio": ["hotel-tvs", "tvs", "harman"],
    "top_mobile": ["smartphones", "tablets", "watches", "buds", "rings", "mobile-accessories", "xr", "wearables"],
    "top_it": ["digital-multifunction-printers", "general-multifunction-printers", "multifunction-printers-supplies",
               "notebook", "desktop", "monitors", "chromebooks"],
    "top_solution": ["display-solution", "mobile-solution", "printing-solution", "printing-solutions", "sac-solution",
                     "tv-vd-solution"],
    "top_service": ["ac-clean", "air-conditioners-care-service"],
}
CATEGORY_PARENT = {root: top for top, roots in _TOP_OF.items() for root in roots}

# 사이트 하위 분류 slug(dlgtDispClsfEnNm/compDispClsfEnNm) → 표시명.
# 사이트 목록 필터 라벨(wkb_filter_meta.json)에서 같은 slug 를 찾으면 그쪽(공식 라벨)이 우선한다.
SUBCAT_LABEL = {
    "dvms-indoor": "시스템에어컨 실내기", "dvms-outdoor": "시스템에어컨 실외기",
    "cassette-wind-free": "무풍 카세트", "ceiling-duct": "천장형 덕트", "floor": "바닥 스탠드",
    "dvm-s": "DVM S 실외기", "ghp": "GHP", "dvm-s-geo-water": "DVM S 지열·수냉",
    "cooling-single-indoor": "실내기", "cooling-single-outdoor": "실외기", "cooling-single-other": "기타",
    "cooling-for-residential-indoor": "실내기", "cooling-for-residential-outdoor": "실외기",
    "cooling-for-residential-other": "기타", "system-dehumidifiers": "시스템 제습기",
    "flip": "전자칠판", "e-paper": "E Paper", "outdoor-dual": "실외용(창문형)",
    "the-wall": "The Wall", "galaxy-tab-active": "갤럭시 탭 액티브",
    "magicinfo": "MagicINFO", "vxtcms": "VXT CMS", "lynk-cloud": "LYNK Cloud", "b-iot": "b.IoT",
    "dms2-5": "DMS 2.5", "touch-central-controller": "터치 중앙제어기", "wi-fi-kit": "Wi-Fi Kit",
    "mps": "통합출력관리(MPS)", "pss": "인증·출력보안(PSS)", "knox-solutions": "Knox 솔루션",
    "samsunghealth": "Samsung Health", "Knox-Classroom": "Knox Classroom",
    "smartthings-pro-for-safety": "SmartThings Pro for Safety",
}

# 사이트 필터 그룹명(공식) → 정규화한 태그 종류
FILTER_GROUP_KIND = {
    "유형": "type", "타입": "type", "제품유형": "type", "제품 유형": "type", "종류": "type", "형태": "type",
    "사이즈": "size_range", "화면크기": "size_range", "화면 크기": "size_range", "크기": "size_range",
    "해상도": "resolution", "밝기": "brightness_range", "픽셀피치": "pixel_pitch_range", "픽셀 피치": "pixel_pitch_range",
    "용량": "capacity_range", "냉방능력": "capacity_range", "세탁용량": "load_range", "건조용량": "load_range",
    "전원": "power_supply", "전원방식": "power_supply", "시리즈": "product_line", "라인업": "product_line",
    "기능": "feature", "주요기능": "feature", "부가기능": "feature", "색상": "color", "인쇄속도": "speed_range",
    "속도": "speed_range", "저장용량": "storage", "네트워크": "connectivity", "용도": "use_segment",
    "설치": "installation", "설치유형": "installation", "설치 유형": "installation", "냉난방": "hvac_mode",
}


def classify_filter(flt: str, group: str | None = None) -> tuple[str, str]:
    """사이트 목록 필터 값 → (tag_kind, tag_value). group(공식 그룹명)이 있으면 그걸 우선한다."""
    f = (flt or "").strip()
    if group:
        g = re.sub(r"\s+", " ", group).strip()
        kind = FILTER_GROUP_KIND.get(g) or FILTER_GROUP_KIND.get(g.replace(" ", ""))
        if kind:
            return kind, f
    fl = f.lower()
    if re.search(r"(cm|㎝|inch)", fl):
        return "size_range", f
    if "nits" in fl:
        return "brightness_range", f
    if re.fullmatch(r"\d{3,4}-x-\d{3,4}", fl):
        return "resolution", f
    if re.search(r"\d(\.\d)?-?mm", fl):
        return "pixel_pitch_range", f
    if re.search(r"\dl\b|l ~|l-over|l-under", fl):
        return "capacity_range", f
    if re.search(r"\dkg", fl):
        return "load_range", f
    if re.search(r"\d-gb", fl):
        return "storage", f
    if "ppm" in fl:
        return "speed_range", f
    if re.search(r"\d{3}v-", fl):
        return "power_supply", f
    if fl in ("outdoor", "outdoor-dual", "indoor"):
        return "environment", f
    if fl in ("commercial", "industrial", "residential", "sports", "housing", "premium-housing", "apartment",
              "general-housing", "complex-building", "business-refrigerator", "b2b"):
        return "use_segment", f
    if fl in ("cool-only", "cool-heat"):
        return "hvac_mode", f
    if fl in ("built-in-wifi", "wireless-charging", "ingress-protection", "samsung-pay", "5g-lte", "lte", "bluetooth",
              "two-sided-print", "two-sided-scan", "smart-tv", "mobile-mirroring", "iot", "biorhythms", "slim-edge",
              "cleansing", "all-in-one-control"):
        return "feature", f
    if fl.startswith(("galaxy-", "bespoke", "neo-qled", "qled", "oled", "uhd", "micro-rgb", "the-", "dvm-s", "grande",
                      "infinite", "zett", "ai-")):
        return "product_line", f
    return "type", f


# ── 페이지 유형 ──────────────────────────────────────────
def page_type_of(u: str, kind: str | None) -> str:
    if kind == "case_kr":
        return "case_study"
    if kind == "industry_kr":
        return "industry"
    if kind == "solution_service_kr":
        if re.search(r"(ac-clean|care-service|careplus|care-plus)", u):
            return "service"
        return "solution"
    if kind == "landing_kr":
        return "case_list" if "/insights/case-study/" in u else "landing"
    if u.startswith("/us/"):
        if re.search(r"/industries/(smartthings-pro|biot)/|lynk-cloud", u):
            return "us_solution"
        if re.search(r"/solutions/industries/[a-z\-]+/", u):
            return "us_vertical"
        return "us_landing"
    return kind or "web_page"


# ── 이미지 ──────────────────────────────────────────────
_MOBILE_MARKERS = [
    (re.compile(r"/mo/", re.I), "/"), (re.compile(r"/pc/", re.I), "/"),
    (re.compile(r"/mo_", re.I), "/"), (re.compile(r"/pc_", re.I), "/"),
    (re.compile(r"[_-]mo(?=[._])", re.I), ""), (re.compile(r"[_-]pc(?=[._])", re.I), ""),
    (re.compile(r"[_-]mobile(?=[._])", re.I), ""), (re.compile(r"_m(?=\.(jpe?g|png|gif|webp)$)", re.I), ""),
]
_IS_MOBILE = re.compile(r"(/mo/|/mo_|[_-]mo[._]|[_-]mobile[._]|_m\.(jpe?g|png|gif|webp)$)", re.I)


def img_base(src: str | None) -> str | None:
    if not src:
        return None
    u = src.strip()
    if u.startswith("//"):
        u = "https:" + u
    if u.startswith("/"):
        u = "https://www.samsung.com" + u
    u = re.sub(r"\?\$[A-Z0-9_]+\$$", "", u)
    u = re.sub(r"[?&](imwidth|imheight|w|h)=\d+.*$", "", u)
    return u


def img_key(src: str | None) -> str | None:
    """PC/MO 변형을 같은 키로 모은 정규 키."""
    u = img_base(src)
    if not u:
        return None
    k = u
    for pat, rep in _MOBILE_MARKERS:
        k = pat.sub(rep, k)
    return k.lower()


def is_mobile_img(src: str | None) -> bool:
    return bool(src and _IS_MOBILE.search(img_base(src) or ""))


CAPTION_STOP = {"비즈니스 정보 열람/구독 신청", "관련 제품", "SOLUTION", "고객 도입사례", "비즈니스 우수 파트너사 찾기", "신청하기", "더 보기",
                "모바일", "시스템에어컨", "사이니지", "TV/음향시스템", "프린팅/IT", "주방가전", "리빙가전", "Knox 솔루션", "모바일 솔루션",
                "프린팅 솔루션", "디스플레이 솔루션", "시스템에어컨 솔루션", "IoT 솔루션", "유지관리", "SW/콘텐츠", "Video Alternative Text"}

GRADE_PRIORITY = {"A": 0, "A?C": 1, "B": 2, "C": 3, "D": 4, "E": 5}

_ICON = re.compile(r"(icon|ico_|_ico|logo|btn_|_btn|arrow|bullet|badge|sprite|blank|spacer|thumb_play)", re.I)
_DIAGRAM = re.compile(r"(diagram|structure|flow|chart|infographic|process|system_map|architecture|_ui|screen)", re.I)


def grade_hint_for(page_type: str, block: dict, caption: str | None):
    """(grade_hint, 이유, rights). A=공간+제품 현장/연출, A?C=공간 연출 또는 제품 컷(미판정),
    B=공간 위주, C=제품 단독 컷, D=도식·UI, E=아이콘·로고."""
    src = (block.get("src") or "")
    low = src.lower()
    if low.endswith(".svg") or _ICON.search(low):
        return "E", "파일명이 아이콘·로고 패턴", "official"
    if page_type == "case_study":
        if re.search(r"/img_\d+\.(png|jpg)", low):
            return "C", "도입사례 '관련 제품' 썸네일", "official"
        return "A", "도입사례 현장 사진(실제 설치 공간)" + (" · 캡션 있음" if caption else ""), "customer_case"
    if page_type in ("industry", "us_vertical"):
        if "/case-study/" in low or "customer" in low:
            return "A", "업종 페이지 '고객 도입사례' 썸네일", "customer_case"
        if _DIAGRAM.search(low):
            return "D", "파일명이 도식·UI 패턴", "official"
        return "A?C", "업종 페이지 장면 항목 비주얼(공간 연출 또는 제품 컷)", "official"
    if page_type in ("solution", "service", "us_solution"):
        if _DIAGRAM.search(low):
            return "D", "솔루션 페이지 도식", "official"
        return "A?C", "솔루션·서비스 페이지 비주얼", "official"
    if page_type in ("landing", "us_landing", "case_list"):
        return "A?C", "랜딩 페이지 비주얼", "official"
    return None, None, "official"


# ── 업종 페이지 파서 ─────────────────────────────────────
NAV_KO = {"특장점", "추천 솔루션 / 서비스", "고객 도입사례", "견적문의", "자세히 보기", "더 보기", "자세히보기",
          "구매하기", "문의하기", "신청하기", "Learn more", "Learn More"}
SKIP_LINK = re.compile(r"(contactus|sales-enquiries|/support/|^tel:|^mailto:|email-form|javascript:|#$)", re.I)
US_SKIP_SECTION = re.compile(r"^(contact|stay in the know|get product support|chat with|speak to|meet our|"
                             r".*resources$|.*insights$|partners$)", re.I)
US_SKIP_LINK = re.compile(r"(short-form|email-form|/shop/offer|insights\.samsung|/support/|/subscribe|/newsletter|#)", re.I)
US_GENERIC_NAMES = {"the blog", "the guide", "subscribe", "contact sales", "contact us", "watch case study", "read case study",
                    "learn more", "shop now", "more", "here", "get started", "sign up", "sign me up", "education", "finance",
                    "government", "healthcare", "retail", "hospitality", "manufacturing", "transportation", "public safety"}
US_PATH_MAP = [   # US 링크 경로 → KR 카탈로그 대응(같은 제품 라인만, 신뢰도 낮게)
    ("direct-view-led/the-wall", "category", "cat_led-signage__the-wall"), ("direct-view-led", "category", "cat_led-signage"),
    ("lcd-videowalls", "category", "cat_smart-signage__videowall"), ("outdoor-and-window", "category", "cat_smart-signage__outdoor"),
    ("samsung-flip", "category", "cat_smart-signage__flip"), ("interactive-display", "category", "cat_smart-signage__flip"),
    ("e-paper", "category", "cat_smart-signage__e-paper"), ("vxt", "solution", "sol_vxt"), ("magicinfo", "solution", "sol_magicinfo"),
    ("lynk-cloud", "solution", "sol_lynk_cloud"), ("smartthings-pro", "solution", "sol_smartthings_pro"), ("/biot", "solution", "sol_biot"),
    ("samsungknox.com", "solution", "sol_knox"), ("/knox", "solution", "sol_knox"), ("galaxy-tab-active", "category", "cat_tablets__galaxy-tab-active"),
    ("/tablets", "category", "cat_tablets"), ("/smartphones", "category", "cat_smartphones"), ("/monitors", "category", "cat_monitors"),
    ("chromebook", "category", "cat_chromebooks"), ("/watches", "category", "cat_watches"), ("/hvac", "category", "top_hvac"),
]
LEGACY_PATH_MAP = [   # KR 사이트 옛 경로·랜딩 → 현재 분류
    ("/sec/business/bespoke-kitchen/", "category", "top_kitchen"), ("/sec/business/built-in-appliances/", "category", "top_kitchen"),
    ("/sec/business/wearables/", "category", "cat_watches"), ("/sec/business/monitor/smart-monitor/", "category", "cat_monitors__smart-monitor"),
    ("/sec/business/mobile-solutions/knox", "solution", "sol_knox"), ("/sec/business/cooling-dvms/", "category", "cat_dvms-indoor"),
    ("/sec/business/smart-led-signage/", "category", "cat_led-signage"), ("/sec/business/harman-audio/", "category", "cat_harman"),
    ("/sec/business/printers/", "category", "top_it"), ("/sec/business/pc/", "category", "cat_notebook"),
    ("/sec/business/refrigerators/", "category", "cat_refrigerator"), ("/sec/business/system-air-conditioner-solutions/dms", "solution", "sol_dms"),
    ("/sec/business/display-solutions/magicinfo", "solution", "sol_magicinfo"), ("/sec/business/printing-solutions/secuthru", "solution", "sol_secuthru"),
    ("/sec/business/printing-solutions/counthru", "solution", "sol_counthru"),
]
US_LINK_VERB = re.compile(r"^(explore|shop|learn more|learn|see|discover|read|get|download|view|find)\b\s*", re.I)


def _t(b) -> str:
    return re.sub(r"\s+", " ", (b.get("x") or "")).strip()


def _dedupe_repeat(s: str) -> str:
    """'Maximize efficiency Maximize efficiency' → 'Maximize efficiency'."""
    w = s.split(" ")
    n = len(w)
    if n % 2 == 0 and n >= 2 and w[: n // 2] == w[n // 2:]:
        return " ".join(w[: n // 2])
    return s


def _is_note(t: str) -> bool:
    """면책·안내 문장(태그라인이 아님): '*…', '…입니다.', '…옵션입니다' 등."""
    t = (t or "").strip()
    return t.startswith("*") or t.startswith("※") or bool(re.search(r"(니다|습니다|입니다)\.?$", t)) or "옵션입니다" in t


def _is_item_link(b) -> bool:
    if b.get("t") != "a":
        return False
    h = b.get("href") or ""
    if not h or SKIP_LINK.search(h):
        return False
    return True


def _hero(blocks, end, locale):
    nav_texts = {_t(b) for b in blocks[:end] if b.get("t") == "a"}
    for i in range(end):
        b = blocks[i]
        if b.get("t") == "h" and int(b.get("l") or 0) in (1, 2, 3):
            x = _t(b)
            if not x or x in NAV_KO or x == "고객 도입사례":
                continue
            tag = None
            j = i - 1
            if j >= 0 and blocks[j].get("t") == "p":
                y = _t(blocks[j])
                if y and y not in NAV_KO and y not in nav_texts and not y.endswith("활성화") and len(y) <= 40:
                    tag = y
            return {"kind": "hero", "title": x, "tagline": tag, "description": None, "space_label": None,
                    "labels": [], "chips": [], "start": i, "end": end, "items": []}
    return None


def _hero_from_h2(blocks, h2_idx):
    """머리 영역에 제목이 없고 첫 h2 바로 앞에 수식 문구(p)가 있으면 첫 h2 가 히어로다(유통·요식 페이지 구조)."""
    if h2_idx <= 0 or blocks[h2_idx - 1].get("t") != "p":
        return None
    nav_texts = {_t(b) for b in blocks[:h2_idx] if b.get("t") == "a"}
    y = _t(blocks[h2_idx - 1])
    if not y or y in NAV_KO or y in nav_texts or y.endswith("활성화") or len(y) > 40:
        return None
    return {"kind": "hero", "title": _t(blocks[h2_idx]), "tagline": y, "description": None, "space_label": None,
            "labels": [], "chips": [], "start": h2_idx, "end": h2_idx + 1, "items": []}


def _section_head(blocks, s, e, want_idx=False):
    """h2 다음 p 들: 설명(긴 문장 1개) + 짧은 라벨들."""
    desc = None
    desc_idx = None
    labels, chips = [], []
    j = s + 1
    while j < e and blocks[j].get("t") == "p":
        x = _t(blocks[j])
        j += 1
        if not x or x in NAV_KO:
            continue
        if desc is None and not labels and len(x) >= 15:
            desc, desc_idx = x, j - 1
            continue
        if len(x) <= 20:
            (labels if is_space_like(x) else chips).append(x)
        else:
            break
    if want_idx:
        return desc, labels, chips, desc_idx
    return desc, labels, chips


def _items_kr(blocks, s, e, kind):
    links = [j for j in range(s + 1, e) if _is_item_link(blocks[j])]
    items = []
    if links:
        first_img = next((j for j in range(s + 1, e) if blocks[j].get("t") == "img"), None)
        first_h3 = next((j for j in range(s + 1, e) if blocks[j].get("t") == "h" and blocks[j].get("l") == 3), None)
        imgs_before = first_img is not None and (first_h3 is None or first_img < first_h3) and kind != "scene" \
            or (kind in ("recommend", "cases"))
        prev = s + 1
        for n, j in enumerate(links):
            win = range(prev, j)
            h3s = [i for i in win if blocks[i].get("t") == "h" and blocks[i].get("l") == 3 and _t(blocks[i]) not in NAV_KO]
            name_idx = h3s[0] if h3s else None
            name = _t(blocks[name_idx]) if name_idx is not None else None
            if name is None:
                cands = [i for i in win if blocks[i].get("t") in ("p", "h") and _t(blocks[i]) and _t(blocks[i]) not in NAV_KO
                         and len(_t(blocks[i])) <= 60]
                if cands:
                    name_idx = cands[-1]
                    name = _t(blocks[name_idx])
            if name is None:
                name = _t(blocks[j]) if _t(blocks[j]) not in NAV_KO else None
                name_idx = j
            # 태그라인: 이름 앞 짧은 p 또는 이름 뒤 첫 p, 여분 h3
            tagline = None
            tagline_idx = None
            if name_idx is not None:
                k = name_idx - 1
                if k >= prev and blocks[k].get("t") == "p":
                    y = _t(blocks[k])
                    if y and y not in NAV_KO and len(y) <= 30 and not is_space_like(y) and not _is_note(y):
                        tagline, tagline_idx = y, k
                if tagline is None:
                    for k in range(name_idx + 1, j):
                        if blocks[k].get("t") == "p" and _t(blocks[k]) and _t(blocks[k]) not in NAV_KO:
                            if len(_t(blocks[k])) <= 80 and not _is_note(_t(blocks[k])):
                                tagline, tagline_idx = _t(blocks[k]), k
                            break
                extra = [i for i in h3s[1:]]
                if extra and not tagline:
                    tagline, tagline_idx = _t(blocks[extra[0]]), extra[0]
            # 이미지
            if imgs_before:
                imgs = [i for i in win if blocks[i].get("t") == "img"]
            else:
                nxt = links[n + 1] if n + 1 < len(links) else e
                stop = next((i for i in range(j + 1, nxt) if blocks[i].get("t") == "h" and int(blocks[i].get("l") or 9) <= 3), nxt)
                imgs = [i for i in range(j + 1, stop) if blocks[i].get("t") == "img"]
            items.append({"name": name, "tagline": tagline, "tagline_idx": tagline_idx, "href": blocks[j].get("href"), "idx": name_idx if name_idx is not None else j,
                          "imgs": imgs, "item_kind": {"recommend": "recommended", "cases": "case_link"}.get(kind, "link_item")})
            prev = j + 1
    else:
        hs = [i for i in range(s + 1, e) if blocks[i].get("t") == "h" and blocks[i].get("l") == 3 and _t(blocks[i]) not in NAV_KO]
        if not hs:
            hs = [i for i in range(s + 1, e) if blocks[i].get("t") == "h" and blocks[i].get("l") == 4
                  and 2 <= len(_t(blocks[i])) <= 20]
        for n, i in enumerate(hs):
            nxt = hs[n + 1] if n + 1 < len(hs) else e
            imgs = [k for k in range(i + 1, nxt) if blocks[k].get("t") == "img"]
            items.append({"name": _t(blocks[i]), "tagline": None, "href": None, "idx": i, "imgs": imgs,
                          "item_kind": "listed_item", "product_cue": bool(PRODUCT_CUE.search(_t(blocks[i])))})
    return items


PRODUCT_CUE = re.compile(r"([A-Za-z]{2,}|\d|스피커|TV|모니터|태블릿|에어컨|냉장고|사이니지|조명|공기청정기|청소기|세탁기|건조기|프린터|"
                         r"복합기|노트북|키트|솔루션|에어드레서|슈드레서|정수기|식기세척기|레인지|오븐|워치|스마트폰|폰|환기|청정기|칠판|키오스크)")


def _same_item(a, b) -> bool:
    if a.get("href") and b.get("href"):
        return a["href"].split("?")[0] == b["href"].split("?")[0] and _k(a.get("name")) == _k(b.get("name")) \
            or a["href"] == b["href"]
    return _k(a.get("name")) == _k(b.get("name"))


def parse_industry_blocks(blocks: list[dict], dup_seq: set, locale: str = "ko") -> list[dict]:
    if locale == "en":
        return _parse_us(blocks)
    h2 = [i for i, b in enumerate(blocks) if b.get("t") == "h" and b.get("l") == 2]
    secs: list[dict] = []
    hero = _hero(blocks, h2[0] if h2 else len(blocks), locale)
    skip_first = False
    if not hero and h2:
        hero = _hero_from_h2(blocks, h2[0])
        skip_first = bool(hero)
    if hero:
        secs.append(hero)
    canon: dict[str, dict] = {}
    for n, s in enumerate(h2):
        if skip_first and n == 0:
            continue
        e = h2[n + 1] if n + 1 < len(h2) else len(blocks)
        if (s + 1) in dup_seq:
            continue
        title = _t(blocks[s])
        kind = "recommend" if title.startswith("추천 솔루션") else "cases" if title == "고객 도입사례" else "scene"
        desc, labels, chips, desc_idx = _section_head(blocks, s, e, want_idx=True)
        items = _items_kr(blocks, s, e, kind)
        key = title
        if key in canon and kind == "scene":
            base = canon[key]
            single = labels[0] if len(labels) == 1 else None
            for it in items:
                if it["item_kind"] == "listed_item" and not it.get("href"):
                    # 모바일 분할본의 무링크 항목은 기존에 같은 이름이 있을 때만 라벨 보강
                    pass
                hit = next((x for x in base["items"] if _same_item(x, it)), None)
                if hit:
                    if single and len(base["labels"]) > 1 and not hit.get("space_label"):
                        hit["space_label"] = single
                    hit["imgs"] = sorted(set(hit["imgs"]) | set(it["imgs"]))
                elif it.get("href"):
                    if single and len(base["labels"]) > 1:
                        it["space_label"] = single
                    base["items"].append(it)
            for lb in labels:
                if lb not in base["labels"]:
                    base["labels"].append(lb)
            base["end"] = max(base["end"], e)
            base.setdefault("dup_ranges", []).append([s, e])
            continue
        sec = {"kind": kind, "title": title, "description": desc, "desc_idx": desc_idx, "labels": labels, "chips": chips,
               "space_label": " · ".join(labels) if labels else None, "tagline": None,
               "start": s, "end": e, "items": items}
        if kind == "scene":
            canon[key] = sec
        secs.append(sec)
    for sec in secs:
        if sec.get("labels"):
            sec["space_label"] = " · ".join(sec["labels"])
    return secs


def _parse_us(blocks):
    h2 = [i for i, b in enumerate(blocks) if b.get("t") == "h" and int(b.get("l") or 0) in (1, 2)]
    secs = []
    seen = set()
    for n, s in enumerate(h2):
        e = h2[n + 1] if n + 1 < len(h2) else len(blocks)
        title = _dedupe_repeat(_t(blocks[s]).replace("​", "").strip())
        if not title or US_SKIP_SECTION.search(title):
            continue
        desc = desc_idx = None
        for j in range(s + 1, e):
            if blocks[j].get("t") == "p" and len(_t(blocks[j])) >= 30:
                desc, desc_idx = _t(blocks[j]), j
                break
        items = []
        names_seen = {}
        for j in range(s + 1, e):
            b = blocks[j]
            if not _is_item_link(b):
                continue
            h = b.get("href") or ""
            if US_SKIP_LINK.search(h) or (h.startswith("http") and "samsung.com/us/business" not in h and "samsungknox.com" not in h):
                continue
            txt = _t(b)
            h3 = next((_t(blocks[i]) for i in range(s + 1, j) if blocks[i].get("t") == "h" and blocks[i].get("l") == 3), None)
            name = US_LINK_VERB.sub("", txt).strip() if txt else ""
            if not name or name.lower() in ("now", "more", "now!", "us", "article", "case study", "white paper", "infographic"):
                name = h3 or title
            if name.lower() in US_GENERIC_NAMES:
                continue
            names_seen[name] = names_seen.get(name, 0) + 1
            items.append({"name": name, "tagline": None, "href": b.get("href"), "idx": j,
                          "imgs": [i for i in range(s + 1, e) if blocks[i].get("t") == "img"][:4], "item_kind": "link_item"})
        items = [it for it in items if names_seen[it["name"]] <= 3]   # 메가 메뉴(같은 이름 반복) 제거
        sig = (title, tuple(i["href"] for i in items))
        if sig in seen:
            continue
        seen.add(sig)
        if not desc and not items:
            continue
        secs.append({"kind": "scene", "title": title, "description": desc, "desc_idx": desc_idx, "labels": [], "chips": [],
                     "space_label": None, "tagline": None, "start": s, "end": e, "items": items})
    return secs


# ── 별칭·해소 ────────────────────────────────────────────
KIND_PRIORITY = {"model": 0, "solution": 1, "service": 2, "family": 3, "category": 4, "deployment": 5}
LEVEL_OF = {"model": "model", "family": "family", "category": "category", "solution": "solution",
            "service": "service", "deployment": "deployment"}

# (표면형, 대상 종류, 대상 id) — 업종 페이지·도입사례에서 쓰는 통칭 → 사이트 분류.
# 대상 id 는 빌드가 만드는 id 규칙(cat_<목록 slug>, cat_<목록>__<하위 slug>, top_*)을 따른다.
CURATED_ALIASES = [
    ("시스템에어컨", "category", "top_hvac"), ("시스템 에어컨", "category", "top_hvac"),
    ("무풍 시스템에어컨", "category", "cat_dvms-indoor"), ("시스템에어컨 360", "category", "cat_dvms-indoor"),
    ("시스템에어컨 실내기", "category", "cat_dvms-indoor"), ("시스템에어컨 실외기", "category", "cat_dvms-outdoor"),
    ("중대형 에어컨", "category", "cat_air-conditioners"), ("에어컨", "category", "cat_air-conditioners"),
    ("중앙공조", "category", "cat_central-air-conditionings"), ("콜드체인", "category", "cat_Cold_Chain_System"),
    ("환기 시스템", "category", "cat_ventilations"), ("시스템 청정환기", "category", "cat_ventilations"),
    ("에어모니터 플러스", "category", "cat_cooling-for-residential"), ("에어 모니터 플러스", "category", "cat_cooling-for-residential"),
    ("사이니지", "category", "top_display"), ("스마트 사이니지", "category", "cat_smart-signage"),
    ("LCD 사이니지", "category", "cat_smart-signage"), ("LED 사이니지", "category", "cat_led-signage"),
    ("LED 사이니지(실내용)", "category", "cat_led-signage"), ("비디오월", "category", "cat_smart-signage__videowall"),
    ("전자칠판", "category", "cat_smart-signage__flip"), ("플립", "category", "cat_smart-signage__flip"),
    ("Samsung Flip", "category", "cat_smart-signage__flip"), ("삼성 플립", "category", "cat_smart-signage__flip"),
    ("실외용 사이니지", "category", "cat_smart-signage__outdoor"), ("산업용 사이니지", "category", "cat_smart-signage"),
    ("E Paper", "category", "cat_smart-signage__e-paper"), ("스페이셜 사이니지", "category", "cat_smart-signage__spatial-signage"),
    ("비즈니스 TV", "category", "cat_smart-signage__business-tv"), ("The Wall", "category", "cat_led-signage__the-wall"),
    ("호텔 TV", "category", "cat_hotel-tvs"), ("호텔TV", "category", "cat_hotel-tvs"), ("호텔 맞춤형 TV", "category", "cat_hotel-tvs"),
    ("The Frame", "category", "cat_tvs"), ("프레임 TV", "category", "cat_tvs"),
    ("하만 프로 오디오", "category", "cat_harman"), ("하만", "category", "cat_harman"), ("프리미엄 오디오 솔루션", "category", "cat_harman"),
    ("갤럭시 탭", "category", "cat_tablets"), ("태블릿", "category", "cat_tablets"), ("산업용 태블릿", "category", "cat_tablets"),
    ("갤럭시 탭 액티브", "category", "cat_tablets__galaxy-tab-active"),
    ("스마트폰", "category", "cat_smartphones"), ("갤럭시 워치", "category", "cat_watches"), ("갤럭시 버즈", "category", "cat_buds"),
    ("갤럭시 링", "category", "cat_rings"), ("갤럭시 XR", "category", "cat_xr"),
    ("갤럭시 북", "category", "cat_notebook"), ("노트북", "category", "cat_notebook"), ("크롬북", "category", "cat_chromebooks"),
    ("모니터", "category", "cat_monitors"), ("커브드 모니터", "category", "cat_monitors"), ("스마트 모니터", "category", "cat_monitors"),
    ("디지털 복합기", "category", "cat_digital-multifunction-printers"), ("디지털복합기", "category", "cat_digital-multifunction-printers"),
    ("에어드레서", "category", "cat_airdresser"), ("BESPOKE 에어드레서", "category", "cat_airdresser"),
    ("슈드레서", "category", "cat_shoedresser"), ("공기청정기", "category", "cat_air-cleaners"),
    ("BESPOKE 큐브 Air", "category", "cat_air-cleaners"), ("BESPOKE 큐브™ Air", "category", "cat_air-cleaners"),
    ("LED 조명", "category", "cat_led-lights"), ("LED조명", "category", "cat_led-lights"), ("산업용 LED조명", "category", "cat_led-lights"),
    ("냉장고", "category", "cat_refrigerator"), ("김치냉장고", "category", "cat_kimchi-refrigerators"),
    ("식기세척기", "category", "cat_dish-washer"), ("전기레인지", "category", "cat_electric-range"),
    ("정수기", "category", "cat_water-purifier"), ("세탁기", "category", "cat_washing-machines"), ("건조기", "category", "cat_dryers"),
    ("청소기", "category", "cat_vacuum-cleaners"), ("비스포크 슬림", "category", "cat_vacuum-cleaners__bespoke-slim"),
    ("비스포크 AI 스팀", "category", "cat_vacuum-cleaners__bespoke-ai-steam"), ("비스포크 큐브 Air", "category", "cat_air-cleaners"),
    ("QLED TV", "category", "cat_tvs"), ("Knox", "solution", "sol_knox"), ("JBL", "category", "cat_harman"),
    ("컬러 이페이퍼", "category", "cat_smart-signage__e-paper"), ("이페이퍼", "category", "cat_smart-signage__e-paper"),
    ("오디세이", "category", "cat_monitors__gaming"), ("전기오븐", "category", "cat_qooker"), ("갤럭시 탭 액티브5", "category", "cat_tablets__galaxy-tab-active"), ("후드", "category", "cat_hood"), ("전자레인지", "category", "cat_micro-wave-ovens"),
]


# ── 자동 역량 규칙(presence 기반, 임계값 판단 없음) ─────────────
# ctx = {category, sub, name, tags(set of site filters), specs[(norm_key, raw, n1, unit, attr)], text}
NEG_VALUE = re.compile(r"^(없음|미지원|미적용|해당\s*없음|no|n/?a|x|-|—|불가)$", re.I)
SIGNAGE = ("cat_smart-signage", "cat_led-signage")
HVAC = ("cat_dvms", "cat_cooling-single", "cat_cooling-for-residential", "cat_central-air-conditionings",
        "cat_air-conditioners", "cat_heat-pump-boilers", "cat_ventilations", "cat_dvms-indoor", "cat_dvms-outdoor")
MOBILE = ("cat_smartphones", "cat_tablets", "cat_watches", "cat_notebook", "cat_chromebooks", "cat_desktop", "cat_xr")


def _pos(raw: str) -> bool:
    return bool(raw) and not NEG_VALUE.match(raw.strip())


def _spec(ctx, pat, val_pat=None):
    for key, raw, n1, unit, attr in ctx["specs"]:
        if re.search(pat, attr, re.I) or (key and re.fullmatch(pat, key)):
            if _pos(raw) and (val_pat is None or re.search(val_pat, raw, re.I)):
                return f"스펙 '{attr}' = {raw[:60]}"
    return None


def _tag(ctx, *flts):
    for f in flts:
        if f in ctx["tags"]:
            return f"사이트 목록 필터 '{f}'"
    return None


def _text(ctx, pat):
    m = re.search(pat, ctx["text"], re.I)
    if m:
        s = max(0, m.start() - 30)
        return "문구 '…" + re.sub(r"\s+", " ", ctx["text"][s:m.end() + 30]).strip() + "…'"
    return None


def _r_weatherproof(c):
    if c["category"] not in SIGNAGE:
        return None
    ev = _tag(c, "outdoor", "outdoor-dual") or (f"사이트 하위 분류 '{c['sub']}'" if c["sub"] in ("outdoor", "outdoor-dual") else None)
    if ev:
        return ev
    for key, raw, n1, unit, attr in c["specs"]:
        if key == "ip_rating" and unit and re.match(r"IP[5-6][4-9]", unit):   # 두 번째 자리(방수)가 숫자 4 이상
            return f"스펙 '{attr}' = {raw[:40]}"
    return None


def _r_sunlight(c):
    if c["category"] not in SIGNAGE:
        return None
    return _tag(c, "3000nits-over")


def _r_continuous(c):
    for key, raw, n1, unit, attr in c["specs"]:
        if key == "operation_hours" and n1 == 24:
            return f"스펙 '{attr}' = {raw}"
    return None


def _r_touch(c):
    if c["category"] not in SIGNAGE + ("cat_monitors", "cat_hotel-tvs", "cat_tvs"):
        return None
    return (_tag(c, "electronic-board", "flip") or (f"사이트 하위 분류 '{c['sub']}'" if c["sub"] == "flip" else None)
            or _spec(c, r"^터치|touch", r"있음|지원|yes|point|정전|IR|적외선"))


def _r_tiling(c):
    if c["category"] == "cat_led-signage":
        return "사이트 분류 'LED 사이니지'(모듈 연결형)"
    return _tag(c, "videowall") or (f"사이트 하위 분류 '{c['sub']}'" if c["sub"] == "videowall" else None)


def _r_epaper(c):
    return _tag(c, "a-paper") or (f"사이트 하위 분류 '{c['sub']}'" if c["sub"] == "e-paper" else None)


def _r_remote_content(c):
    if c["category"] not in SIGNAGE + ("cat_hotel-tvs",):
        return None
    return _spec(c, r"MagicINFO|VXT|매직인포") or _text(c, r"MagicINFO|매직인포|VXT")


def _r_draft_free(c):
    if c["category"] not in HVAC:
        return None
    if "wind-free" in c["sub"]:
        return f"사이트 하위 분류 '{c['sub']}'"
    t = next((t for t in c["tags"] if "wind-free" in t), None)
    if t:
        return f"사이트 목록 필터 '{t}'"
    return _text(c, r"무풍|WindFree|Wind-Free")


def _r_large_space(c):
    if c["category"] in ("cat_dvms", "cat_central-air-conditionings"):
        return "사이트 분류 '대형건물용' 또는 '중앙공조'"
    return None


def _r_hotel_tv(c):
    if c["category"] == "cat_hotel-tvs":
        return _spec(c, r"LYNK|링크") or "사이트 분류 '호텔TV'"
    return _spec(c, r"LYNK") if c["category"] in ("cat_tvs", "cat_smart-signage") else None


def _r_rugged(c):
    if c["category"] not in MOBILE:
        return None
    if "galaxy-tab-active" in c["tags"] or c["sub"] == "galaxy-tab-active":
        return "사이트 분류 '갤럭시 탭 액티브'"
    if re.search(r"XCover|엑스커버|Active", c["name"], re.I):
        return f"제품명 '{c['name']}'"
    return _spec(c, r"MIL-STD|밀리터리|군사\s*표준") or _text(c, r"MIL-STD[- ]?810")


def _r_knox(c):
    if c["category"] not in MOBILE + ("cat_monitors",):
        return None
    return _spec(c, r"Knox|녹스") or _text(c, r"Samsung Knox|삼성 녹스|Knox")


def _r_bms(c):
    if c["category"] in ("cat_sac-solution",) and re.search(r"b-iot|dms", c["sub"], re.I):
        return f"사이트 분류 '{c['sub']}'"
    if c["category"] in HVAC:
        return _spec(c, r"BACnet|b\.IoT|DMS|LonWorks|Modbus") or _text(c, r"BACnet|b\.IoT|빌딩\s*통합|BMS")
    return None


AUTO_RULES = [
    {"id": "auto_weatherproof_signage", "cap": "weatherproof", "category": "signage",
     "expression": "site_filter in {outdoor, outdoor-dual} or ip_rating >= IP55", "fn": _r_weatherproof,
     "explain": "사이트가 '실외용'으로 분류했거나 스펙에 IP5x 이상 방수·방진 등급이 있음"},
    {"id": "auto_sunlight_filter", "cap": "sunlight_readable", "category": "signage",
     "expression": "site_filter == '3000nits-over'", "fn": _r_sunlight,
     "explain": "사이트 밝기 필터 '3000nits 이상'에 속함(임계값은 사이트 구간을 그대로 사용)"},
    {"id": "auto_continuous_247", "cap": "continuous_operation", "category": "*",
     "expression": "operation_hours == 24/7", "fn": _r_continuous, "explain": "스펙 '제품 사용 시간'이 24/7"},
    {"id": "auto_touch", "cap": "touch_interactive", "category": "signage|monitor|tv",
     "expression": "site_filter == electronic-board or spec 터치 = 있음", "fn": _r_touch,
     "explain": "전자칠판 분류이거나 스펙에 터치 지원이 있음"},
    {"id": "auto_tiling", "cap": "bezel_less_tiling", "category": "signage",
     "expression": "category == led-signage or site_filter == videowall", "fn": _r_tiling,
     "explain": "LED 사이니지(모듈 연결형) 또는 비디오월 분류"},
    {"id": "auto_epaper", "cap": "low_power_static", "category": "signage",
     "expression": "site_filter == a-paper", "fn": _r_epaper, "explain": "E Paper 분류"},
    {"id": "auto_remote_content", "cap": "remote_content_mgmt", "category": "signage|hotel_tv",
     "expression": "spec/문구에 MagicINFO 또는 VXT", "fn": _r_remote_content,
     "explain": "스펙(예: VXT Player Support=있음)이나 특장점 문구에 CMS 연동 언급"},
    {"id": "auto_draft_free", "cap": "draft_free_cooling", "category": "hvac",
     "expression": "sub == cassette-wind-free or 문구 '무풍'", "fn": _r_draft_free, "explain": "무풍 분류 또는 무풍 문구"},
    {"id": "auto_large_space", "cap": "large_space_cooling", "category": "hvac",
     "expression": "category in {대형건물용, 중앙공조}", "fn": _r_large_space, "explain": "사이트 분류가 대형건물용·중앙공조"},
    {"id": "auto_hotel_tv", "cap": "hospitality_tv_mgmt", "category": "tv",
     "expression": "category == hotel-tvs or spec LYNK", "fn": _r_hotel_tv, "explain": "호텔TV 분류 또는 LYNK 스펙"},
    {"id": "auto_rugged", "cap": "rugged_mobile", "category": "mobile",
     "expression": "galaxy-tab-active or name ~ XCover/Active or MIL-STD", "fn": _r_rugged,
     "explain": "액티브·엑스커버 라인업 또는 MIL-STD 언급"},
    {"id": "auto_knox", "cap": "device_security_mgmt", "category": "mobile|pc",
     "expression": "spec/문구에 Knox", "fn": _r_knox, "explain": "Knox 보안 플랫폼 언급"},
    {"id": "auto_bms", "cap": "building_integration", "category": "hvac|sac_solution",
     "expression": "b.IoT/DMS 분류 또는 BACnet·b.IoT 언급", "fn": _r_bms, "explain": "빌딩 통합 제어 연동 근거"},
]


# ── 요구사항 문장 → 역량(질의 해석용 키워드 사전) ─────────────────
REQ_CAP_KEYWORDS = {   # 정규식(부분 문자열 함정 방지: '운영하는'의 '영하', '실외기'의 '실외')
    "weatherproof": [r"옥외", r"야외", r"실외(?!기)", r"외부\s?설치", r"방수", r"우천", r"outdoor"],
    "sunlight_readable": [r"직사광", r"햇빛", r"햇볕", r"창가", r"쇼윈도", r"고휘도", r"밝은\s?곳", r"sunlight", r"window-facing"],
    "continuous_operation": [r"24\s?시간", r"24/7", r"상시\s?(운영|구동)", r"연중\s?무휴", r"장시간\s?구동"],
    "touch_interactive": [r"터치", r"인터랙티브", r"판서", r"전자칠판", r"키오스크", r"interactive", r"touch"],
    "bezel_less_tiling": [r"비디오\s?월", r"초대형\s?화면", r"대형\s?화면", r"이음매", r"베젤", r"미디어\s?월", r"LED\s?월", r"video\s?wall"],
    "remote_content_mgmt": [r"원격", r"콘텐츠\s?관리", r"스케줄", r"CMS", r"중앙\s?관리", r"다점포", r"여러\s?지점", r"content management"],
    "low_power_static": [r"저전력", r"전자\s?종이", r"E\s?Paper", r"e-paper", r"전원\s?없는"],
    "draft_free_cooling": [r"무풍", r"직바람", r"바람\s?없는", r"찬\s?바람"],
    "large_space_cooling": [r"대공간", r"대형\s?건물", r"넓은\s?공간", r"대형\s?공간"],
    "building_integration": [r"빌딩\s?통합", r"BMS", r"에너지\s?절감", r"에너지\s?관리", r"통합\s?제어", r"중앙\s?제어", r"building management"],
    "hospitality_tv_mgmt": [r"객실\s?TV", r"호텔\s?TV", r"투숙객", r"객실\s?관리", r"LYNK"],
    "rugged_mobile": [r"현장\s?작업", r"내구성", r"러기드", r"낙하", r"산업용\s?태블릿", r"물류\s?현장", r"rugged"],
    "device_security_mgmt": [r"보안", r"MDM", r"기기\s?관리", r"Knox", r"녹스", r"분실"],
    "residential_quiet": [r"저소음", r"소음", r"조용한"],
    "wide_temp_operation": [r"혹한", r"혹서", r"영하\s?\d", r"영하(권|의|에서|로)", r"고온\s?환경", r"저온\s?환경"],
}
_REQ_RE = {cap: [re.compile(p, re.I) for p in pats] for cap, pats in REQ_CAP_KEYWORDS.items()}


def caps_from_text(text: str) -> list[tuple[str, str]]:
    """문장에서 역량 코드와 근거 키워드를 찾는다."""
    out = []
    for cap, pats in _REQ_RE.items():
        for p in pats:
            m = p.search(text or "")
            if m:
                out.append((cap, m.group(0)))
                break
    return out


def spaces_in_text(text: str, lang: str = "ko", vertical: str | None = None) -> list[tuple[str, str]]:
    """문장 안의 공간 표현 → (space_type, 키워드) 목록. 긴 키워드 우선, 겹치면 건너뜀."""
    out, used = [], []
    table = KW_EN if lang == "en" else KW_KO
    src = (text or "").lower() if lang == "en" else (text or "")
    for kw, code in table:
        start = 0
        while True:
            i = src.find(kw, start)
            if i < 0:
                break
            if not any(a <= i < b for a, b in used):
                used.append((i, i + len(kw)))
                if code and code not in [c for c, _ in out]:
                    out.append((code, kw))
            start = i + len(kw)
    for kw in ("주방", "키친"):
        if kw in (text or "") and _kitchen(vertical) and _kitchen(vertical) not in [c for c, _ in out]:
            out.append((_kitchen(vertical), kw))
    if "창구" in (text or ""):
        sp = "bank_branch" if vertical in ("kr_finance", "us_finance") else "civil_service_counter"
        if sp not in [c for c, _ in out]:
            out.append((sp, "창구"))
    return out


# ── 이미지 alt 문장 → 장면 판정(VLM 전 1차 메타) ─────────────────
ALT_INSTALL = re.compile(r"(설치되어|설치된|설치돼|설치되|놓여|배치되어|배치된|걸려|부착된|부착되어|비치된|매립된|장착된|벽에 걸린)")
ALT_USE = re.compile(r"(사용하는 모습|사용 중인|사용하고 있|이용하는 모습|이용하고 있|시청하는|보고 있는|앉아)")
ALT_INTERIOR = re.compile(r"(천장|벽면|벽에|바닥|창문|창가|인테리어|공간|실내|테이블|책상|소파|거실|방 안)")
ALT_UI_STRONG = re.compile(r"(화면 UI|UI 화면|앱 화면|그래프|도표|다이어그램|구성도|인포그래픽|표가 있|아이콘들?이 나열|순서도|흐름도|띠배너|배너|설명이 적혀|안내 문구|비교표|스펙 표)")
ALT_UI_WEAK = re.compile(r"(아이콘|텍스트가 (적혀|쓰여)|문구가 (적혀|쓰여))")
ALT_PRODUCT_ONLY = re.compile(r"(제품 (정면|측면|후면|단독)|정면 모습|측면 모습|제품 이미지입니다|흰 배경|배경 없이|클로즈업|확대한|확대된|위에서 바라본|내부 구조|부품)")


def grade_from_alt(alt: str | None, vertical: str | None = None):
    """(grade_hint, reason, space_type) — alt 원문에 기대는 결정적 규칙. 판정 못 하면 (None, None, space)."""
    if not alt or len(alt) < 8:
        return None, None, None
    sp = spaces_in_text(alt, "ko", vertical)
    space = sp[0][0] if sp else None
    if ALT_UI_STRONG.search(alt):
        return "D", "alt 문장이 UI·도식을 서술", space
    if ALT_PRODUCT_ONLY.search(alt) and not (space and ALT_INSTALL.search(alt)):
        return "C", "alt 문장이 제품 단독·근접 컷을 서술", space
    if space and (ALT_INSTALL.search(alt) or ALT_USE.search(alt)):
        return "A", f"alt 문장이 공간('{sp[0][1]}') 속 설치·사용 장면을 서술", space
    if ALT_INSTALL.search(alt) and ALT_INTERIOR.search(alt):
        return "A", "alt 문장이 실내 공간 속 설치 장면을 서술(공간 유형 미상)", None
    if ALT_UI_WEAK.search(alt) and not ALT_INSTALL.search(alt):
        return "D", "alt 문장이 문구·아이콘 위주 이미지를 서술", space
    return None, None, space
