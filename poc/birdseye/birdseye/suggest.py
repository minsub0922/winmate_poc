"""BP2 '추천' — 지금 표에 없는 제품군 중 이 공간 유형에 흔히 함께 쓰는 것을 하나씩 권한다(규칙 기반, 근거 문장 포함)."""
from __future__ import annotations

from .layout2d import recommend_all
from .rules import Rules

# 공간 유형 → (제품군, 모델, 설치, 이유) 우선순위
BY_SPACE = {
    "lobby": [("epaper", "LH32EMDIAGBXKR", "wall", "출입구 옆 길 안내 · 화면 전환할 때만 전력을 써요"),
              ("hvac_cassette", "AC060CN4FBH1", "ceiling", "면적 기준 냉난방 용량 — 천장 매립이라 동선에 영향 없어요")],
    "sales_floor": [("signage", "LH55QMCEBGCXKR", "wall", "진열 벽 위 가격 · 프로모션 안내"),
                    ("epaper", "LH13EMDIBGBXKR", "wall", "진열대 가격표 · 전력 거의 없음")],
    "exhibition_showroom": [("spatial", "LH85SMHPBGCXKR", "floor_lean", "작품처럼 세워 두는 스페이셜 사이니지"),
                            ("epaper", "LH32EMDIAGBXKR", "wall", "작품 설명 · 길 안내")],
    "meeting_room": [("flip", "LH65WMFWBGCXKR", "stand", "회의 중 판서 · 화면 공유"),
                     ("hvac_cassette", "AC060CN4FBH1", "ceiling", "면적 기준 냉난방 용량")],
    "open_office": [("flip", "LH75WMFWLGCXKR", "stand", "협업 공간 판서 · 화면 공유"),
                    ("epaper", "LH32EMDIAGBXKR", "wall", "회의실 예약 · 층 안내")],
    "classroom": [("flip", "LH75WMFWLGCXKR", "stand", "교탁 옆 전자칠판"),
                  ("hvac_cassette", "AC060CN4FBH1", "ceiling", "면적 기준 냉난방 용량")],
    "waiting_area": [("epaper", "LH32EMDIAGBXKR", "wall", "진료실 문 옆 대기 순서 · 안내"),
                     ("signage", "LH55BEHHLBFXKR", "wall", "대기석 정보 · 호출 화면")],
    "hospital_reception": [("signage", "LH43BEHHLBFXKR", "wall", "접수 순서 호출 화면"),
                           ("epaper", "LH32EMDIAGBXKR", "wall", "진료 안내 · 길 안내")],
    "control_room": [("videowall", "LH55VMCEBGBXKR", "wall", "정면 상황판 비디오월"),
                     ("hvac_cassette", "AC060CN6PBH1", "ceiling", "장비 발열을 고려한 냉방")],
    "dining_hall": [("window_signage", "LH55OMNDSGBXKR", "ceiling_hang", "창면 메뉴 · 길에서도 보이는 양면 화면"),
                    ("signage", "LH55QMCEBGCXKR", "wall", "카운터 위 메뉴보드")],
    "lounge": [("spatial", "LH32SMHPBGCXKR", "floor_lean", "분위기를 해치지 않는 아트 화면"),
               ("hvac_cassette", "AC060CN4FBH1", "ceiling", "면적 기준 냉난방 용량")],
    "guest_room": [("hvac_cassette", "AC060CN4FBH1", "ceiling", "객실 냉난방")],
}


def suggest_products(project: dict, catalog, rules: Rules | None = None, skip: list[str] | None = None, limit: int = 1) -> list[dict]:
    rules = rules or Rules(project.get("rules_override"))
    st = (project.get("space") or {}).get("space_type") or "lobby"
    have_cats = set()
    for l in project.get("lines", []):
        p = catalog.get(l["product"])
        if p:
            have_cats.add(p["category"])
    out = []
    for cat_, code, mount, why in BY_SPACE.get(st, BY_SPACE["lobby"]):
        if cat_ in have_cats or code in (skip or []):
            continue
        prod = catalog.get(code)
        if not prod:
            continue
        line = {"id": "S1", "product": code, "mount": mount, "qty": None}
        try:
            rec = recommend_all({**project, "lines": [line]}, catalog, rules)["S1"]
        except Exception:  # noqa: BLE001
            continue
        if not rec.get("qty_rec"):
            continue
        out.append({"product": code, "short": prod["short"], "name": prod["name"], "mount": mount, "qty_rec": rec["qty_rec"],
                    "reason": why, "explain": rec.get("explain"), "rule_ids": rec.get("rule_ids", []), "source": "rules"})
        if len(out) >= limit:
            break
    return out
