"""템플릿 기하 빌더 — 1280 × 720 캔버스(PPT 디자인 캔버스와 같은 단위)에서 칸(slot)과 상자(box)를 만든다.

카탈로그(catalog.json)에는 상자 좌표를 슬라이드 기준 상대값(0..1)으로 저장한다.
렌더러는 상대값 × 슬라이드 크기로 그리므로 마스터(.potx)의 슬라이드 크기가 달라도 그대로 맞는다.

용어
- slot  : 소비 서비스가 채우는 칸. `{key, type, label, required, count?, max_chars?, image_grade?, fields?, default?}`
- box   : 칸(또는 칸의 i번째 항목 · 항목의 한 필드)을 그릴 사각형과 스타일. `slot=None` 이면 장식(패널 · 화살표 · 선)
- field : `card` 형 항목의 하위 값(title · body · kpi · image …). 상자는 `part` 로 필드 하나만 그릴 수 있다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

W, H = 1280, 720
X0, X1 = 64, 1216
CW = X1 - X0           # 1152 — 본문 폭
Y0, Y0_SUB, Y1 = 136, 160, 648   # 본문 시작(부제 없음 / 있음), 본문 끝
GAP = 24

SLOT_TYPES = ("text", "bullets", "number", "kpi", "image", "table", "chart", "logo", "caption", "source", "card")


def rel(v: float, total: int) -> float:
    return round(v / total, 4)


@dataclass
class Builder:
    slots: list[dict[str, Any]] = field(default_factory=list)
    boxes: list[dict[str, Any]] = field(default_factory=list)

    # ── 칸 ─────────────────────────────────────────────
    def slot(
        self,
        key: str,
        type: str,
        label: str,
        *,
        required: bool = False,
        count: int | None = None,
        max_chars: int | None = None,
        image_grade: str | None = None,
        fields: list[dict[str, Any]] | None = None,
        default: Any = None,
        default_en: Any = None,
        hint: str | None = None,
    ) -> str:
        assert type in SLOT_TYPES, type
        for s in self.slots:
            if s["key"] == key:
                if count and (s.get("count") or 0) < count:
                    s["count"] = count
                return key
        d: dict[str, Any] = {"key": key, "type": type, "label": label, "required": required}
        if count is not None:
            d["count"] = count
        if max_chars is not None:
            d["max_chars"] = max_chars
        if image_grade is not None:
            d["image_grade"] = image_grade
        if fields:
            d["fields"] = fields
        if default is not None:
            d["default"] = default
        if default_en is not None:
            d["default_en"] = default_en
        if hint:
            d["hint"] = hint
        self.slots.append(d)
        return key

    # ── 상자 ───────────────────────────────────────────
    def box(self, slot: str | None, x: float, y: float, w: float, h: float, style: str, *,
            index: int | None = None, part: str | None = None, **opts: Any) -> None:
        b: dict[str, Any] = {"slot": slot, "x": rel(x, W), "y": rel(y, H), "w": rel(w, W), "h": rel(h, H), "style": style}
        if index is not None:
            b["index"] = index
        if part is not None:
            b["part"] = part
        for k, v in opts.items():
            if v is not None:
                b[k] = v
        self.boxes.append(b)

    def deco(self, style: str, x: float, y: float, w: float, h: float, **opts: Any) -> None:
        self.box(None, x, y, w, h, style, **opts)


# ── 필드 정의 도우미 ────────────────────────────────────

def f(key: str, type: str, label: str, max_chars: int | None = None, **kw: Any) -> dict[str, Any]:
    d: dict[str, Any] = {"key": key, "type": type, "label": label}
    if max_chars is not None:
        d["max_chars"] = max_chars
    d.update({k: v for k, v in kw.items() if v is not None})
    return d


def cols(n: int, x: float = X0, w: float = CW, gap: float = GAP) -> list[tuple[float, float]]:
    cw = (w - gap * (n - 1)) / n
    return [(x + i * (cw + gap), cw) for i in range(n)]


def rows(n: int, y: float, h: float, gap: float = 16) -> list[tuple[float, float]]:
    rh = (h - gap * (n - 1)) / n
    return [(y + i * (rh + gap), rh) for i in range(n)]


# ── 공통 틀(머리 · 바닥) ─────────────────────────────────

SECTION_EYEBROW = {
    "mi": ("MARKET INTELLIGENCE", "MARKET INTELLIGENCE"),
    "vp": ("VALUE PROPS", "VALUE PROPS"),
    "birdseye": ("조감도", "BIRD'S-EYE VIEW"),
    "space_products": ("공간별 제품", "PRODUCTS BY SPACE"),
    "solution": ("솔루션 제안", "SOLUTIONS"),
    "space_scenario": ("공간별 가치 제공 시나리오", "SPACE SCENARIOS"),
    "cases": ("유관 사례", "CASE STUDIES"),
    "why": ("WHY SAMSUNG", "WHY SAMSUNG"),
    "spec": ("제품 스펙", "PRODUCT SPECS"),
    "appendix": ("부록", "APPENDIX"),
    "common": ("", ""),
}


def frame(b: Builder, section: str, *, sub: bool = False, title_chars: int = 46, sub_w: int = 1060) -> float:
    """머리(눈썹 · 제목 · 부제) + 바닥(로고 · 바닥글 · 출처). 본문 시작 y 를 돌려준다."""
    ko, en = SECTION_EYEBROW.get(section, ("", ""))
    b.slot("eyebrow", "text", "섹션 라벨(예: 01 · MARKET INTELLIGENCE)", max_chars=40, default=ko or None, default_en=en or None)
    b.slot("title", "text", "제목 — 이 장의 핵심 메시지 한 문장", required=True, max_chars=title_chars)
    if sub:
        b.slot("subtitle", "text", "부제 — 기준 · 범위 · 출처 요약", max_chars=80)
    b.slot("sources", "source", "출처 · 각주(장 하단 한 줄)")
    b.slot("footer", "text", "바닥글(고객사 · 제안명) — 비우면 문서 값", max_chars=70)
    b.slot("logo", "logo", "고객사 로고 — 비우면 디자인 로고")
    b.box("eyebrow", 64, 44, 1060, 20, "eyebrow")
    b.box("title", 64, 66, 1060, 42, "title")
    if sub:
        b.box("subtitle", 64, 112, sub_w, 22, "subtitle")
    b.box("sources", 64, 651, 1152, 15, "source")
    b.box("logo", 64, 680, 72, 20, "logo")
    b.box("footer", 148, 680, 860, 20, "footer")
    return Y0_SUB if sub else Y0
