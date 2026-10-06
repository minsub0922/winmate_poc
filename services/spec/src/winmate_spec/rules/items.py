"""스펙 항목 카탈로그(06-spec §4.14) — config/items/<분류>.yaml."""
from __future__ import annotations

from typing import Any

from .. import config

DERIVED_ROWS = {
    "derived:annual_energy_cost": {"label_ko": "연간 전기료 (추정)", "en_lines": ["Annual Energy Cost (Est.)"], "item_key": None},
}

# 요구 → 항목 대응(결정적, §4.7.2)
REQ_KEY_TO_ITEM = {
    "screen_size_cm": "size_resolution", "screen_size_inch": "size_resolution", "resolution": "size_resolution",
    "brightness_nit": "brightness_contrast", "operation_hours": "operation_hours", "power_consumption": "power",
    "cap_remote_content_mgmt": "magicinfo", "magicinfo": "magicinfo", "warranty_years": "warranty", "warranty": "warranty",
    "wifi": "io_ports", "io_ports": "io_ports", "hdmi": "io_ports", "weight_kg": "size_weight", "dimensions": "size_weight",
    "bezel_mm": "bezel", "bezel": "bezel", "kc": "certification", "safety": "certification", "emc": "certification",
    "certification": "certification", "mount": "accessories", "stand": "accessories", "cap_continuous_operation": "operation_hours",
}

SHORT_NAMES = {
    "size_resolution": "화면 크기", "brightness_contrast": "밝기", "operation_hours": "운영 시간", "power": "소비전력",
    "player_os": "OS", "magicinfo": "MagicINFO", "warranty": "보증", "io_ports": "입출력 단자", "size_weight": "크기 · 무게",
    "bezel": "베젤", "certification": "인증", "accessories": "액세서리",
}

ROW_SHORT = {"power": "소비전력", "warranty": "보증", "brightness_contrast": "밝기", "dimensions": "크기", "weight": "무게",
             "bezel": "베젤", "operation_hours": "운영 시간", "size_resolution": "화면 크기", "magicinfo": "MagicINFO",
             "player_os": "OS", "io_ports": "입출력 단자", "certification": "인증", "accessories": "액세서리",
             "derived:annual_energy_cost": "전기 단가"}


def catalog(category: str = "signage") -> dict[str, Any]:
    return config.items_config(category)


def item_list(category: str = "signage") -> list[dict[str, Any]]:
    return list(catalog(category).get("items") or [])


def item_keys(category: str = "signage") -> list[str]:
    return [it["key"] for it in item_list(category)]


def item(key: str, category: str = "signage") -> dict[str, Any] | None:
    return next((it for it in item_list(category) if it["key"] == key), None)


def item_label(key: str) -> str:
    it = item(key)
    return it["label"] if it else key


def default_keys(category: str = "signage") -> list[str]:
    return [it["key"] for it in item_list(category) if it.get("default")]


def rows_of_item(key: str) -> list[dict[str, Any]]:
    it = item(key)
    return list(it.get("rows") or []) if it else []


def row_meta(row_key: str) -> dict[str, Any]:
    """row_key → {label_ko, en_lines, item_key}."""
    if row_key in DERIVED_ROWS:
        return dict(DERIVED_ROWS[row_key])
    for it in item_list():
        for r in it.get("rows") or []:
            if r["row_key"] == row_key:
                return {"label_ko": r["label_ko"], "en_lines": list(r.get("en_lines") or []), "item_key": it["key"]}
    return {"label_ko": row_key, "en_lines": [row_key], "item_key": None}


def all_row_keys() -> list[str]:
    return [r["row_key"] for it in item_list() for r in it.get("rows") or []]


def group_of(item_key: str | None) -> str:
    it = item(item_key) if item_key else None
    return (it or {}).get("group") or "기타"


def groups() -> list[str]:
    return list(catalog().get("groups") or [])
