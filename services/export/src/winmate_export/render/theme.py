"""색 · 글꼴 · 마스터 프리셋.

'Winmate PPT' 캔버스 색을 그대로 쓴다. 포인트 색(brand)은 디자인의 brand_hex 로 바꿀 수 있고,
연한 틴트(#eaeefb 등)는 포인트 색과 흰색을 섞어 만든다(삼성 블루일 때 캔버스 값과 같아진다).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

DEFAULT_BRAND = "#1428a0"
FONT = "Noto Sans KR"          # 없으면 PowerPoint 가 맑은 고딕 등으로 대체한다(AGENTS.md 참고)
NUMBER_FONT = "Noto Sans KR"   # 캔버스는 Manrope — 사내 PC 에 없을 수 있어 같은 글꼴로 통일

INK = "#121417"
INK2 = "#3d4452"
GRAY = "#596170"
GRAY2 = "#8a91a0"
LINE = "#e2e5ea"
LINE2 = "#b8bec8"
LINE3 = "#d5d9e0"
PANEL = "#f5f6f8"
PLACEHOLDER = "#dfe3ea"
WHITE = "#ffffff"
MARK_FILL = "#fff2a8"          # [확인 필요] · [TBD] 강조 바탕
MARK_TEXT = "#9a3412"

HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")


def norm_hex(v: str | None, default: str = DEFAULT_BRAND) -> str:
    m = HEX.match((v or "").strip())
    return ("#" + m.group(1).lower()) if m else default


def rgb(hex_: str) -> tuple[int, int, int]:
    h = norm_hex(hex_, "#000000")[1:]
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(a: str, b: str, t: float) -> str:
    """a 와 b 를 섞는다(t=0 → a, t=1 → b)."""
    ra, ga, ba = rgb(a)
    rb, gb, bb = rgb(b)
    return "#%02x%02x%02x" % (round(ra + (rb - ra) * t), round(ga + (gb - ga) * t), round(ba + (bb - ba) * t))


def luminance(hex_: str) -> float:
    r, g, b = (c / 255 for c in rgb(hex_))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


MASTERS: dict[str, dict[str, Any]] = {
    "samsung_b2b": {"name": "삼성 B2B 표준", "desc": "화이트 + 삼성 블루 · 16:9 · 사내 표준 마스터", "accent_ink": False},
    "retail_fnb": {"name": "리테일 · F&B 변형", "desc": "이미지 비중 큰 레이아웃 · 매장 사진 강조", "accent_ink": False,
                   "cover": "C02"},
    "simple_white": {"name": "심플 화이트", "desc": "텍스트 중심 · 경영진 보고용", "accent_ink": True, "cover": "C03"},
}


@dataclass
class Theme:
    brand: str = DEFAULT_BRAND
    master_id: str = "samsung_b2b"
    font: str = FONT
    number_font: str = NUMBER_FONT
    colors: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_design(cls, design: dict[str, Any] | None) -> "Theme":
        design = design or {}
        brand = norm_hex(design.get("brand_hex"))
        master_id = design.get("master_id") if design.get("master_id") in MASTERS else "samsung_b2b"
        t = cls(brand=brand, master_id=master_id)
        t.colors = t._palette()
        return t

    def _palette(self) -> dict[str, str]:
        b = self.brand
        # 너무 밝은 포인트 색이면 글자색은 진하게 보정
        text_brand = b if luminance(b) < 0.55 else mix(b, INK, 0.55)
        eyebrow = INK2 if MASTERS[self.master_id].get("accent_ink") else text_brand
        return {
            "brand": b, "brand_text": text_brand, "eyebrow": eyebrow,
            "tint": mix(b, WHITE, 0.91), "tint2": mix(b, WHITE, 0.955), "soft": mix(b, WHITE, 0.70),
            "mid": mix(b, WHITE, 0.39), "on_brand": WHITE if luminance(b) < 0.6 else INK,
            "on_brand_sub": mix(b, WHITE, 0.77) if luminance(b) < 0.6 else INK2,
            "ink": INK, "ink2": INK2, "gray": GRAY, "gray2": GRAY2, "line": LINE, "line2": LINE2, "line3": LINE3,
            "panel": PANEL, "placeholder": PLACEHOLDER, "white": WHITE, "mark_fill": MARK_FILL, "mark_text": MARK_TEXT,
        }

    def c(self, key: str) -> str:
        if key.startswith("#"):
            return key
        return self.colors.get(key, key)
