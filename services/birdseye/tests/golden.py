"""골든 입력(08-birdseye §5.2 예 공간 · 제품 3종 · 가구 4종 · 의도 픽스처) — 엔진 · 초안 렌더 · 존 테스트가 함께 쓴다."""
from __future__ import annotations

import copy
from typing import Any

from winmate_birdseye.engine import computed_dims


def space() -> dict[str, Any]:
    return copy.deepcopy({
        "rooms": [{"id": "r1", "label": "1층 로비", "space_types": ["lobby", "sales_floor"],
                   "outline": [[0, 0], [24.0, 0], [24.0, 16.5], [0, 16.5]]}],
        "walls": [
            {"id": "w1", "a": [0, 0], "b": [24.0, 0], "thickness": 0.2, "kind": "exterior", "label": "정면", "dim_known": True},
            {"id": "w2", "a": [24.0, 0], "b": [24.0, 16.5], "thickness": 0.2, "kind": "exterior", "label": "오른쪽", "dim_known": False},
            {"id": "w3", "a": [24.0, 16.5], "b": [0, 16.5], "thickness": 0.2, "kind": "exterior", "label": "후면", "dim_known": False},
            {"id": "w4", "a": [0, 16.5], "b": [0, 0], "thickness": 0.2, "kind": "exterior", "label": "왼쪽", "dim_known": False},
        ],
        "openings": [
            {"id": "o1", "kind": "window", "wall_id": "w1", "offset": 1.0, "width": 10.0, "label": "전면 유리창 (도로측)", "faces_outdoor": True},
            {"id": "o2", "kind": "window", "wall_id": "w1", "offset": 13.0, "width": 10.0, "label": "전면 유리창 (도로측)", "faces_outdoor": True},
            {"id": "o3", "kind": "door", "wall_id": "w1", "offset": 11.0, "width": 2.0, "label": "주출입구", "door_type": "main",
             "is_main": True, "confidence": 0.9},
            {"id": "o4", "kind": "door", "wall_id": "w3", "offset": 2.0, "width": 0.9, "label": "뒤쪽 문", "door_type": "unknown",
             "confidence": 0.4},
        ],
        "columns": [{"id": "c1", "center": [8.2, 8.0], "w": 0.6, "d": 0.6}, {"id": "c2", "center": [15.8, 8.0], "w": 0.6, "d": 0.6}],
        "cores": [{"id": "k1", "polygon": [[0, 12.5], [4.0, 12.5], [4.0, 16.5], [0, 16.5]], "kinds": ["ev", "stairs"]}],
        "power_points": [{"id": "p1", "pos": [0.2, 2.0], "source": "plan"}, {"id": "p2", "pos": [12.5, 16.3], "source": "plan"},
                         {"id": "p3", "pos": [23.8, 8.0], "source": "plan"}],
        "ceiling_h": {"value": 4.5, "estimated": False},
        "scale": {"ratio": 100, "source": "pdf_text", "correction": 1.0},
        "dims": [{"id": "d1", "label": "정면 폭", "wall_id": "w1", "annotated_m": 24.0, "computed_m": 24.0, "choice": "annotated"}],
        "area_m2": 396.0,
        "features": [{"kind": "storefront_window", "label": "전면 유리창", "hint_cap": "cap_sunlight_readable", "cap_label": "고휘도 권장"},
                     {"kind": "columns", "label": "중앙 기둥", "count": 2}],
        "assumptions": [], "questions": [], "facts": [], "estimated": False, "source": "plan", "meta_paths": [],
    })


def products() -> list[dict[str, Any]]:
    iab = {s: computed_dims(float(s.rstrip('"'))) for s in ('110"', '146"')}
    return copy.deepcopy([
        {"id": "bpi_OH55C", "family_id": "fam_OH", "model_code": "LH55OHCEBGCXKR", "ref": "kb:model:mdl_LH55OHCEBGCXKR",
         "display_name": "Outdoor Signage OH55C", "short": "OH55C", "size_options": ['55"'], "chosen_size": None,
         "dims_m": {"w": 1.24, "h": 0.73, "d": 0.08}, "dims_by_size": {'55"': {"w": 1.24, "h": 0.73, "d": 0.08}},
         "dims_source": "spec", "diag_inch": 55, "category": "LCD 사이니지", "role": "window_signage", "mount_default": "window_facing",
         "order": 0, "models_by_size": {'55"': "LH55OHCEBGCXKR"}},
        {"id": "bpi_WA75D", "family_id": "fam_FLIP", "model_code": "LH75WADWLGCXKR", "ref": "kb:model:mdl_LH75WADWLGCXKR",
         "display_name": "Flip Pro WA75D", "short": "Flip Pro WA75D", "size_options": ['75"'], "chosen_size": None,
         "dims_m": {"w": 1.72, "h": 1.03, "d": 0.08}, "dims_by_size": {'75"': {"w": 1.72, "h": 1.03, "d": 0.08}},
         "dims_source": "spec", "diag_inch": 75, "category": "전자칠판", "role": "interactive", "mount_default": "wall", "order": 1,
         "models_by_size": {'75"': "LH75WADWLGCXKR"}},
        {"id": "bpi_IAB", "family_id": "fam_IAB", "model_code": None, "ref": "kb:family:fam_IAB",
         "display_name": "The Wall All-in-One IAB", "short": "The Wall IAB", "size_options": ['110"', '146"'], "chosen_size": None,
         "dims_m": None, "dims_by_size": iab, "dims_source": "computed", "diag_inch": None, "category": "LED 사이니지",
         "role": "led_wall", "mount_default": "wall", "order": 2, "models_by_size": {}},
    ])


def furniture() -> list[dict[str, Any]]:
    return copy.deepcopy([
        {"id": "bfi_sofa", "catalog_code": "lounge_sofa_set", "name": "라운지 소파 세트", "short": "라운지 소파", "tiny": "소파",
         "qty": 1, "rows": None, "anchor": "window_area", "zone": "라운지", "dims_m": {"w": 2.4, "d": 1.9, "h": 0.8},
         "parts": [{"w": 2.4, "d": 0.9, "h": 0.8, "x": 0.0, "y": -0.5, "kind": "sofa"}, {"w": 1.0, "d": 0.6, "h": 0.4, "x": 0.0, "y": 0.65, "kind": "table"}],
         "selected": True, "source": "recommended", "order": 0},
        {"id": "bfi_wrap", "catalog_code": "column_wrap_frame", "name": "기둥 랩핑 프레임", "short": "기둥 랩핑", "tiny": "랩핑",
         "qty": 2, "rows": None, "anchor": "column", "zone": None, "dims_m": {"w": 0.8, "d": 0.8, "h": 4.2}, "wrap_margin_m": 0.1,
         "selected": True, "source": "recommended", "order": 1},
        {"id": "bfi_bench", "catalog_code": "viewing_bench", "name": "관람 벤치 (3열)", "short": "관람 벤치", "tiny": "벤치",
         "qty": 1, "rows": 3, "anchor": "faces_display", "zone": "관람", "dims_m": {"w": 2.4, "d": 0.45, "h": 0.45},
         "selected": True, "source": "recommended", "order": 2},
        {"id": "bfi_desk", "catalog_code": "info_desk", "name": "안내 데스크", "short": "안내 데스크", "tiny": "데스크",
         "qty": 1, "rows": None, "anchor": "entrance", "zone": "안내", "dims_m": {"w": 2.0, "d": 0.8, "h": 1.05},
         "selected": True, "source": "user", "order": 3},
    ])


def intents() -> list[dict[str, Any]]:
    """의도 LLM 픽스처(be.layout_intent) — OH55C 3대 · 위치 라벨."""
    return [
        {"item": "bpi_OH55C", "anchor": "window:o1", "qty": 3, "at_label": "쇼윈도 창면"},
        {"item": "bpi_IAB", "anchor": "wall:w3", "at_label": "후면 벽"},
        {"item": "bpi_WA75D", "anchor": "wall:w2", "at_label": "측벽 · 상담"},
    ]
