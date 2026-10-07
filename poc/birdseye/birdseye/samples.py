"""웹앱 시나리오(② 이미지 · 조감도 · 시나리오 캔버스)의 샘플 작업을 엔진으로 만든다.

- 강남 플래그십 1층 로비 · 2D (A 커피 프랜차이즈) — 완료
- B 병원 외래 대기실 · 2D — 3/4 배치·동선, 경고 남음
- 강남 플래그십 1층 로비 · 3D — 2D 연결
- C 물류센터 관제실 · 3D — 현장 사진 추정값(사진 파일 없음), 요구사항 단계
제품은 webapp 목업의 가상 코드 대신 winmate-kb 에 있는 실제 모델로 바꿨다(OH55C→OM55B, The Wall IAB 146"→IAC 130", WA75D→Flip 75").
"""
from __future__ import annotations

import copy

from .catalog import Catalog
from .furnish import furnish
from .layout2d import layout_lines, line_strategy, recommend_all
from .rules import Rules
from .validate import autofix, validate
from .zones import suggest_zones

LOBBY_SPACE = {
    "name": "강남 플래그십 1층 로비",
    "space_type": "lobby",
    "width": 24000, "depth": 16500, "height": 4500,
    "openings": [
        {"id": "W_A", "kind": "window", "wall": "front", "start": 600, "length": 10200, "label": "유리창 A", "sill": 0, "head": 3600},
        {"id": "E1", "kind": "entrance", "wall": "front", "start": 10800, "length": 2400, "label": "주출입구", "sill": 0, "head": 2700},
        {"id": "W_B", "kind": "window", "wall": "front", "start": 13200, "length": 10200, "label": "유리창 B", "sill": 0, "head": 3600},
        {"id": "D1", "kind": "door", "wall": "back", "start": 20500, "length": 1000, "label": "뒤쪽 문", "door_type": "backoffice", "sill": 0, "head": 2100},
    ],
    "pillars": [
        {"id": "P1", "label": "기둥 1", "x": 8400, "y": 7200, "w": 600, "d": 600},
        {"id": "P2", "label": "기둥 2", "x": 15600, "y": 7200, "w": 600, "d": 600},
    ],
    "outlets": [
        {"id": "C1", "label": "C1", "x": 6000, "y": 16500, "on": "wall:back"},
        {"id": "C2", "label": "C2", "x": 18000, "y": 16500, "on": "wall:back"},
        {"id": "C3", "label": "C3", "x": 24000, "y": 4000, "on": "wall:right"},
        {"id": "C4", "label": "C4", "x": 24000, "y": 12600, "on": "wall:right"},
        {"id": "C5", "label": "C5", "x": 8100, "y": 7200, "on": "pillar:P1"},
        {"id": "C6", "label": "C6", "x": 15900, "y": 7200, "on": "pillar:P2"},
    ],
    "source": "manual",
}

LOBBY_LINES = [
    {"id": "L1", "product": "LH55OMBEBGBXKR", "mount": "ceiling_hang", "qty": 3},
    {"id": "L2", "product": "LH43QMCEBGCXKR", "mount": "pillar_wrap", "qty": 4},
    {"id": "L3", "product": "LH015IACCHS/KR", "mount": "wall", "qty": 1},
    {"id": "L4", "product": "LH75WMFWLGCXKR", "mount": "stand", "qty": 1},
]

LOBBY_ZONE_NAMES = {"window": "쇼윈도", "lounge": "라운지 · 안내", "pillar": "기둥 · 길 안내", "mediawall": "미디어월 · 관람",
                    "stand": "상담 · 시연"}

HOSPITAL_SPACE = {
    "name": "B 병원 외래 대기실",
    "space_type": "waiting_area",
    "width": 18000, "depth": 12000, "height": 2800,
    "openings": [
        {"id": "E1", "kind": "entrance", "wall": "left", "start": 4000, "length": 2000, "label": "복도 출입구", "sill": 0, "head": 2400},
        {"id": "D1", "kind": "door", "wall": "back", "start": 14000, "length": 1500, "label": "진료실 복도", "door_type": "corridor", "sill": 0, "head": 2400},
        {"id": "W_A", "kind": "window", "wall": "right", "start": 2000, "length": 8000, "label": "창 A", "sill": 900, "head": 2400},
    ],
    "pillars": [{"id": "P1", "label": "기둥 1", "x": 9000, "y": 6000, "w": 700, "d": 700}],
    "outlets": [
        {"id": "C1", "label": "C1", "x": 0, "y": 2500, "on": "wall:left"},
        {"id": "C2", "label": "C2", "x": 6000, "y": 12000, "on": "wall:back"},
        {"id": "C3", "label": "C3", "x": 12000, "y": 12000, "on": "wall:back"},
        {"id": "C4", "label": "C4", "x": 18000, "y": 11000, "on": "wall:right"},
        {"id": "C5", "label": "C5", "x": 9900, "y": 0, "on": "wall:front"},
        {"id": "C6", "label": "C6", "x": 13100, "y": 0, "on": "wall:front"},
        {"id": "C9", "label": "C9", "x": 16300, "y": 0, "on": "wall:front"},
        {"id": "C7", "label": "C7", "x": 0, "y": 7300, "on": "wall:left"},
        {"id": "C8", "label": "C8", "x": 16800, "y": 12000, "on": "wall:back"},
    ],
    "source": "manual",
}

CONTROL_SPACE = {
    "name": "C 물류센터 관제실",
    "space_type": "control_room",
    "width": 9600, "depth": 15500, "height": 3200,
    "openings": [
        {"id": "E1", "kind": "entrance", "wall": "front", "start": 1200, "length": 1200, "label": "출입문", "sill": 0, "head": 2200},
        {"id": "W_A", "kind": "window", "wall": "left", "start": 3000, "length": 9000, "label": "창 A", "sill": 1000, "head": 2500},
    ],
    "pillars": [],
    "outlets": [],
    "source": "photos",
    "estimated": True,
}


def _named(zones, names):
    for z in zones:
        z["name"] = names.get(z.get("key"), z["name"])
    return zones


def build_lobby_2d(catalog: Catalog) -> dict:
    rules = Rules()
    p = {"kind": "2d", "title": "강남 플래그십 1층 로비", "customer": "A 커피 프랜차이즈",
         "proposal": "A 커피 프랜차이즈 메뉴보드 제안", "space": copy.deepcopy(LOBBY_SPACE),
         "lines": copy.deepcopy(LOBBY_LINES), "placements": [], "fixtures": [], "zones": [], "notes": [], "ignored": [],
         "step": "done", "status": "done", "version": 3}
    recs = recommend_all(p, catalog, rules)
    for line in p["lines"]:
        line["qty_rec"] = recs[line["id"]]["qty_rec"]
    layout_lines(p, catalog, rules)
    fixtures, _ = furnish(p, catalog, rules, mode="2d", requests=[
        {"type": "bench", "count": 3, "reason": "미디어월 관람석 · 시야각 안"},
        {"type": "info_desk", "count": 1, "reason": "입구에서 바로 보이는 안내"},
        {"type": "lounge_sofa", "count": 1, "reason": "입구 쪽 라운지"},
        {"type": "coffee_table", "count": 1, "reason": "소파 앞 테이블"},
        {"type": "exp_counter", "count": 1, "reason": "상담·시연 스탠드 곁 체험 카운터"},
    ])
    p["fixtures"] = fixtures
    strategies = {l["id"]: line_strategy(p, l, catalog) for l in p["lines"]}
    p["zones"] = _named(suggest_zones(p, catalog, strategies), LOBBY_ZONE_NAMES)
    p, _ = autofix(p, catalog, rules)
    p["flow"] = {"auto": True}
    return p


def build_hospital_2d(catalog: Catalog) -> dict:
    rules = Rules()
    p = {"kind": "2d", "title": "B 병원 외래 대기실", "customer": "B 병원", "proposal": "",
         "space": copy.deepcopy(HOSPITAL_SPACE), "lines": [], "placements": [], "fixtures": [], "zones": [], "notes": [],
         "ignored": [], "step": "layout", "status": "in_progress", "version": 1}
    # 사용자가 먼저 놓은 집기: 접수 카운터 · 대기 의자 4줄(2×2) — 한 줄은 시야각 밖, 카운터는 통로를 좁힘
    p["fixtures"] = [
        {"id": "F1", "type": "reception_counter", "label": "접수 카운터", "x": 3300, "y": 8900, "w": 3600, "d": 900, "h": 1050, "rot": 90},
        {"id": "F2", "type": "waiting_chairs", "label": "대기 의자 1열", "x": 9000, "y": 3300, "w": 2200, "d": 620, "h": 800, "rot": 0, "seats": 4},
        {"id": "F3", "type": "waiting_chairs", "label": "대기 의자 1열", "x": 12400, "y": 3300, "w": 2200, "d": 620, "h": 800, "rot": 0, "seats": 4},
        {"id": "F4", "type": "waiting_chairs", "label": "대기 의자 2열", "x": 9000, "y": 4800, "w": 2200, "d": 620, "h": 800, "rot": 0, "seats": 4},
        {"id": "F5", "type": "waiting_chairs", "label": "대기 의자 2열", "x": 16400, "y": 4800, "w": 2200, "d": 620, "h": 800, "rot": 0, "seats": 4},
        {"id": "F6", "type": "waiting_chairs", "label": "대기 의자 3열", "x": 9000, "y": 8600, "w": 2200, "d": 620, "h": 800, "rot": 0, "seats": 4},
        {"id": "F7", "type": "waiting_chairs", "label": "대기 의자 3열", "x": 12400, "y": 8600, "w": 2200, "d": 620, "h": 800, "rot": 0, "seats": 4},
    ]
    p["lines"] = [
        {"id": "L1", "product": "LH55BEHHLBFXKR", "mount": "wall", "qty": None},
        {"id": "L2", "product": "LH32EMDIAGBXKR", "mount": "wall", "qty": None},
        {"id": "L3", "product": "AC060CN4FBH1", "mount": "ceiling", "qty": None},
    ]
    recs = recommend_all(p, catalog, rules)
    for line in p["lines"]:
        line["qty_rec"] = recs[line["id"]]["qty_rec"]
        line["qty"] = recs[line["id"]]["qty_rec"]
    p["lines"][0]["qty"] = 2  # 사용자가 권장 3대 대신 2대로 확정 → 맨 앞줄 끝 좌석이 시야각 밖
    layout_lines(p, catalog, rules)
    # 진료실 복도 문 앞에 둔 플랜터 → 문 여유 공간 경고
    p["fixtures"].append({"id": "F8", "type": "planter_large", "label": "대형 플랜터", "x": 14700, "y": 11300,
                          "w": 700, "d": 700, "h": 1700, "rot": 0})
    strategies = {l["id"]: line_strategy(p, l, catalog) for l in p["lines"]}
    p["zones"] = suggest_zones(p, catalog, strategies)
    p["flow"] = {"auto": True}
    return p


def build_lobby_3d(catalog: Catalog, lobby2d_id: str | None) -> dict:
    return {
        "kind": "3d", "title": "강남 플래그십 1층 로비", "customer": "A 커피 프랜차이즈",
        "proposal": "A 커피 프랜차이즈 메뉴보드 제안",
        "linked_2d": lobby2d_id,
        "input": {
            "text": "강남 플래그십 1층 로비를 고객이 브랜드를 체험하는 갤러리 같은 공간으로 보여주고 싶어요. 길에서도 창 너머 화면이 보이고, 안쪽엔 큰 미디어월이 있었으면 해요.",
            "space_type": "lobby", "moods": ["warm", "gallery"],
            "products": [l["product"] for l in LOBBY_LINES],
            "scale": {"area_pyeong": 120, "height": "high"}, "photos": [], "quality": "standard",
        },
        "space": copy.deepcopy(LOBBY_SPACE),
        "status": "draft", "step": "brief", "renders": [],
    }


def build_control_3d(catalog: Catalog) -> dict:
    return {
        "kind": "3d", "title": "C 물류센터 관제실", "customer": "C 물류센터", "proposal": "",
        "linked_2d": None,
        "input": {
            "text": "관제실 리뉴얼이에요. 정면 상황판 교체가 핵심이고 운영석은 2열입니다.",
            "space_type": "control_room", "moods": ["tech", "minimal"],
            "products": ["LH55VMCEBGBXKR"],
            "scale": {"area_pyeong": 45, "height": "normal"},
            "photos": [],
            "photo_read": {
                "basis": "현장 사진 4장 중 2장 기준(샘플: 사진 파일은 포함하지 않음)",
                "structure": ["약 45평 추정", "층고 3.2 m 추정", "상황판 벽 폭 약 9 m", "운영석 2열"],
                "mood": ["차가운 백색 조명", "회색 카펫 타일", "블랙 운영 데스크"],
                "needs": ["창 쪽 사진이 역광이라 창 위치가 흐려요", "천장 사진 없음 — 층고는 추정값"],
            },
            "quality": "standard",
        },
        "space": copy.deepcopy(CONTROL_SPACE),
        "status": "needs_check", "step": "brief", "renders": [],
    }


def check(p: dict, catalog: Catalog) -> dict:
    return validate(p, catalog, Rules(p.get("rules_override")))
