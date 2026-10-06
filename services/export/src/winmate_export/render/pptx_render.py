"""PPTX 렌더러 — 카탈로그 템플릿(칸 · 상자) + 칸 값 → 슬라이드.

    deck = DeckRenderer(theme=Theme.from_design(design), lang="ko", assets=assets, design=design)
    data = deck.render({"title": ..., "cover": {...}, "slides": [{"template_code": "MS-B", "slots": {...}}]})

- 상자마다 스타일(style)로 그린다. 장식 상자(slot=None)는 패널 · 화살표 · 선.
- 글은 상자 크기에 맞춰 글자 크기를 단계적으로 줄이고, 그래도 넘치면 말줄임으로 자른다.
- `[확인 필요]` · `[00]` 같은 자리표시는 노란 형광 + 굵게. 영어(en)는 `[TBD]` 로 바꾼다.
- 이미지 메타가 AI 생성이면 이미지 왼쪽 아래에 「AI 생성 이미지」 칩을 붙인다(끌 수 없음).
- design.master_file_id(.potx/.pptx)가 있으면 그 파일을 열어 빈(또는 첫) 레이아웃에 슬라이드를 더한다.
"""
from __future__ import annotations

import io
import logging
import math
import re
import zipfile
from dataclasses import dataclass, field
from typing import Any, Protocol

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu

from ..templates.catalog import Catalog, catalog
from . import textfit
from .pptx_draw import Canvas, P, Run
from .theme import Theme
from .values import (
    MARKER,
    TBD_LABEL,
    as_bullets,
    as_card,
    as_kpi,
    as_list,
    as_sources,
    as_table,
    cell_text,
    col_label,
    has_marker,
    image_ref,
    label,
    localize,
    to_text,
)

log = logging.getLogger("winmate.export.pptx")

SLIDE_W, SLIDE_H = 12192000, 6858000
EN_FACTOR = 1.8          # 영어는 칸 글자 수를 넉넉히(라틴 글자가 좁다)
COVER_ROLES = {"COVER", "TOC", "DIVIDER", "CLOSING"}


class RenderError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass
class Asset:
    data: bytes
    mime: str = "application/octet-stream"
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def ai_generated(self) -> bool:
        return is_ai_generated(self.meta)


def is_ai_generated(meta: Any, depth: int = 0) -> bool:
    """파일 메타(files FileMeta.meta · image 생성 메타 generation)에 AI 생성 표시가 있는가.

    image 서비스 생성 메타: {is_generated: true, rights: "generated", caption_rule: "생성 이미지"} (07-image §5.2).
    """
    if not isinstance(meta, dict) or depth > 3:
        return False
    if meta.get("ai_generated") is True or meta.get("is_generated") is True or meta.get("rights") == "generated":
        return True
    if str(meta.get("origin") or "").lower() in ("gen", "ai", "t2i") or str(meta.get("kind") or "").lower() in ("generated", "ai_generated"):
        return True
    return any(is_ai_generated(meta.get(k), depth + 1) for k in ("meta", "generation", "image", "provenance"))


class Assets(Protocol):
    def get(self, file_id: str) -> Asset | None: ...


class DictAssets:
    def __init__(self, items: dict[str, Asset] | None = None):
        self.items = dict(items or {})

    def get(self, file_id: str) -> Asset | None:
        return self.items.get(file_id)


# ── 카드 스타일 ─────────────────────────────────────────────

@dataclass
class CardSpec:
    fill: str | None = "panel"
    line: str | None = None
    line_w: float = 1.0
    radius: float = 16
    pad: float = 22
    title: float = 18
    body: float = 14
    no_big: bool = False
    inv: bool = False
    image: str | None = None       # top | left
    image_frac: float = 0.52
    image_bg: str | None = None    # 제품 컷 바탕
    layout: str = "stack"          # stack | row
    badge: bool = False            # row 형 번호 원
    kpi_size: float = 32
    kpi_first: bool = False
    title_color: str = "ink"
    tag_brand: bool = False
    anchor: str = "top"


CARDS: dict[str, CardSpec] = {
    "card": CardSpec(),
    "card_pillar": CardSpec(no_big=True, title=21, body=15, pad=28),
    "card_white": CardSpec(fill="white", line="line", radius=14, pad=20, title=16.5, body=13.5),
    "card_white_row": CardSpec(fill="white", line="line", radius=14, pad=16, title=15.5, body=12.5, layout="row", badge=False),
    "card_white_node": CardSpec(fill="white", line="line2", radius=12, pad=14, title=15, body=12, anchor="middle"),
    "card_tint": CardSpec(fill="tint", radius=14, pad=20, title=16, body=13.5),
    "card_brand": CardSpec(fill="brand", radius=16, pad=26, title=22, body=14, inv=True),
    "card_dark": CardSpec(fill="ink", radius=16, pad=26, title=20, body=14, inv=True),
    "card_outline": CardSpec(fill="white", line="brand", line_w=2, radius=16, pad=20),
    "card_outline_ink": CardSpec(fill="white", line="ink", line_w=1.5, radius=12, pad=16, title=15, body=12.5, badge=True),
    "card_person": CardSpec(fill="panel", radius=16, pad=24, title=19, body=14, tag_brand=True),
    "card_challenge": CardSpec(fill="panel", radius=16, pad=28, title=21, body=15, no_big=True),
    "card_img": CardSpec(fill="white", line="line", radius=14, pad=16, title=16, body=13, image="top", image_frac=0.5),
    "card_img_tall": CardSpec(fill="panel", radius=16, pad=18, title=17, body=13, image="top", image_frac=0.52, image_bg="white"),
    "card_img_tall_tint": CardSpec(fill="tint", radius=16, pad=18, title=17, body=13, image="top", image_frac=0.5, image_bg="white"),
    "card_img_tall_dark": CardSpec(fill="ink", radius=16, pad=22, title=22, body=14, image="top", image_frac=0.55, inv=True, image_bg="#2a2f38"),
    "card_img_tall_main": CardSpec(fill="panel", radius=16, pad=22, title=22, body=14, image="top", image_frac=0.6, image_bg="white"),
    "card_img_plain": CardSpec(fill=None, radius=0, pad=4, title=15, body=12, image="top", image_frac=0.7),
    "card_img_small": CardSpec(fill="white", line="line", radius=12, pad=8, title=12.5, body=11, image="top", image_frac=0.68),
    "card_img_row": CardSpec(fill="panel", radius=14, pad=16, title=17, body=13, image="left"),
    "card_img_row_dark": CardSpec(fill="ink", radius=14, pad=18, title=19, body=13.5, image="left", inv=True, image_bg="#2a2f38"),
    "card_img_row_kpis": CardSpec(fill="panel", radius=14, pad=16, title=17, body=13, image="left"),
    "card_row_img": CardSpec(fill="white", line="line", radius=12, pad=12, title=15, body=12.5, image="left", image_bg="panel"),
    "card_row_text": CardSpec(fill="white", line="line", radius=12, pad=16, title=15.5, body=12.5, layout="row", badge=True),
    "card_product": CardSpec(fill="panel", radius=14, pad=12, title=14.5, body=12, image="top", image_frac=0.48, image_bg="white"),
    "card_product_small": CardSpec(fill="panel", radius=12, pad=12, title=14, body=11.5, image="top", image_frac=0.5, image_bg="white"),
    "card_kpi": CardSpec(fill="panel", radius=14, pad=22, title=16, body=13, kpi_first=True, kpi_size=36),
    "card_kpi_big": CardSpec(fill="panel", radius=16, pad=26, title=19, body=14, kpi_size=48),
    "card_pin": CardSpec(fill="white", line="line", radius=12, pad=14, title=15, body=12.5, layout="row", badge=True),
    "card_pin_col": CardSpec(fill="panel", radius=12, pad=14, title=14.5, body=12, badge=True),
    "card_space_row": CardSpec(fill="white", line="line", radius=10, pad=10, title=14, body=11.5, layout="row", badge=True),
    "card_step": CardSpec(fill="panel", radius=14, pad=18, title=17, body=12.5),
    "card_finding": CardSpec(fill="white", line="line", radius=14, pad=16, title=14.5, body=12.5, layout="row"),
    "card_swot": CardSpec(fill="panel", radius=14, pad=22, title=18, body=14.5),
    "card_swot_tint": CardSpec(fill="tint2", radius=14, pad=22, title=18, body=14.5),
    "card_time": CardSpec(fill="panel", radius=14, pad=16, title=16, body=13),
    "card_option": CardSpec(fill="white", line="line", radius=16, pad=18, title=17, body=13, image="top", image_frac=0.42),
    "card_type": CardSpec(fill="white", line="line", radius=16, pad=20, title=18, body=13),
    "card_text_plain": CardSpec(fill=None, radius=0, pad=4, title=17, body=14),
    "card_white_node_b": CardSpec(fill="white", line="line", radius=12, pad=12, title=14, body=12),
    "tile": CardSpec(fill="white", radius=10, pad=12, title=12.5, body=11, kpi_size=24),
    "tile_dark": CardSpec(fill="#000000", radius=10, pad=12, title=14, body=12, inv=True),
    "contact": CardSpec(fill=None, line=None, radius=0, pad=0, title=16, body=13),
    "contact_row": CardSpec(fill=None, radius=0, pad=0, title=15, body=12.5, layout="row"),
    "toc_row": CardSpec(fill=None, radius=0, pad=6, title=20, body=13, layout="row", badge=False),
    "logo_tile": CardSpec(fill="panel", radius=12, pad=12, title=12.5, body=11, image="top", image_frac=0.6, image_bg="white"),
    "floor_row": CardSpec(fill="panel", radius=10, pad=10, title=15, body=12, layout="row"),
    "legend_row": CardSpec(fill=None, radius=0, pad=0, title=14, body=12.5, layout="row", badge=True),
    "card_img_tall_b": CardSpec(),
    "circle_card_brand": CardSpec(fill="brand", radius=999, pad=30, title=20, body=13, inv=True, anchor="middle"),
}
CELL_FILLS = {
    "cell": (None, None), "cell_head": ("panel", None), "cell_tint": ("tint", None), "cell_outline": ("white", "line"),
    "cell_gray": ("panel", None), "cell_tint_strong": ("tint", None), "cell_strong": (None, None), "cell_num": (None, None),
    "cell_left_card": ("panel", None), "cell_mid": (None, None), "cell_value": ("tint", None), "cell_gray_titled": ("panel", None),
    "cell_title_body": (None, None),
}
TEXT_STYLES: dict[str, dict[str, Any]] = {
    "eyebrow": dict(size=13, bold=True, color="eyebrow"),
    "eyebrow_inv": dict(size=13, bold=True, color="white"),
    "title": dict(size=30, bold=True, color="ink", line=1.2, min_scale=0.62),
    "cover_title": dict(size=44, bold=True, color="ink", line=1.15, min_scale=0.55),
    "cover_title_xl": dict(size=58, bold=True, color="ink", line=1.1, min_scale=0.5),
    "cover_title_inv": dict(size=40, bold=True, color="white", line=1.15, min_scale=0.55),
    "subtitle": dict(size=15, color="gray"),
    "subtitle_inv": dict(size=15, color="on_brand_sub"),
    "heading": dict(size=18, bold=True, color="ink"),
    "heading_sm": dict(size=15, bold=True, color="ink"),
    "heading_lg": dict(size=24, bold=True, color="ink", line=1.3),
    "heading_xl": dict(size=34, bold=True, color="ink", line=1.15),
    "heading_inv": dict(size=21, bold=True, color="white", line=1.3),
    "label": dict(size=13, bold=True, color="gray"),
    "label_brand": dict(size=13, bold=True, color="brand_text"),
    "body": dict(size=15, color="ink2", line=1.45),
    "body_strong": dict(size=15, bold=True, color="ink", line=1.4),
    "body_inv": dict(size=14, color="on_brand_sub", line=1.5),
    "small": dict(size=13, color="gray"),
    "caption": dict(size=11.5, color="gray2"),
    "caption_inv": dict(size=11, color="white"),
    "footer": dict(size=11, color="gray2"),
    "statement": dict(size=36, bold=True, color="ink", line=1.25, min_scale=0.55),
    "quote": dict(size=22, bold=True, color="ink", line=1.4),
    "band_text": dict(size=16, bold=True, color="ink", anchor="middle"),
    "divider_no": dict(size=170, bold=True, color="on_brand_sub", number=True, line=1.0),
    "divider_no_brand": dict(size=96, bold=True, color="brand_text", number=True, line=1.0),
    "divider_no_small": dict(size=40, bold=True, color="white", number=True, line=1.0),
    "divider_title": dict(size=44, bold=True, color="white", line=1.15),
    "divider_title_ink": dict(size=40, bold=True, color="ink", line=1.15),
    "row_label": dict(size=13, bold=True, color="gray", anchor="middle"),
    "row_label_strong": dict(size=16, bold=True, color="ink", anchor="middle"),
    "cell_strong": dict(size=15, bold=True, color="ink", anchor="middle"),
}


@dataclass
class Ctx:
    template: dict[str, Any]
    values: dict[str, Any]
    slot_defs: dict[str, dict[str, Any]]
    lang: str
    slide_no: int
    warnings: list[str]


class DeckRenderer:
    def __init__(self, *, theme: Theme, lang: str = "ko", assets: Assets | None = None, design: dict[str, Any] | None = None,
                 confidential: bool = False, cat: Catalog | None = None, placeholders: bool = True,
                 bilingual: str = "inline", tbd_mode: str = "keep", tbd_label: str | None = None):
        self.theme = theme
        self.lang = lang
        self.assets = assets or DictAssets()
        self.design = design or {}
        self.confidential = confidential
        self.cat = cat or catalog()
        self.placeholders = placeholders
        self.bilingual = bilingual
        self.tbd_mode = tbd_mode            # keep: 칸에 표시 남김 · notes: 칸은 「—」, 문장은 발표자 노트로
        self.tbd_label = tbd_label
        self.warnings: list[str] = []
        self.template_codes: list[str] = []
        self.slide_count = 0

    # ── 문서 → 슬라이드 목록 ────────────────────────────────
    def plan(self, document: dict[str, Any]) -> list[dict[str, Any]]:
        slides = [dict(s) for s in document.get("slides") or []]
        kinds = {(s.get("kind") or "").lower() for s in slides}
        cover = document.get("cover")
        has_cover = "cover" in kinds or any(self._resolve_code(s).startswith("C0") and self._role(s) == "COVER" for s in slides if s.get("template_code"))
        if cover and not has_cover:
            slots = {k: v for k, v in cover.items() if k in ("title", "subtitle", "customer", "date", "presenter", "eyebrow", "image")}
            slides.insert(0, {"kind": "cover", "template_code": self._cover_code(slots), "slots": slots})
        out = []
        for s in slides:
            if not s.get("template_code"):
                kind = (s.get("kind") or "sheet").lower()
                slots = s.get("slots") if isinstance(s.get("slots"), dict) else (s.get("content") or {})
                default = {"cover": self._cover_code(slots), "toc": "C04", "divider": "C05", "closing": "C07",
                           "appendix": "AX-B"}.get(kind)
                if not default:
                    raise RenderError("TEMPLATE_REQUIRED", "슬라이드에 template_code 가 없습니다", {"slide": s.get("title")})
                s["template_code"] = default
            if self.lang == "both" and self.bilingual == "slides":
                out.append({**s, "_lang": "ko"})
                out.append({**s, "_lang": "en"})
            else:
                out.append({**s, "_lang": self.lang})
        return out

    def _cover_code(self, slots: dict[str, Any] | None) -> str:
        """표지 템플릿: 디자인 지정 > (리테일 마스터 + 그림) C02 > 그림 있으면 C01 > 글자 표지 C03."""
        if self.design.get("cover_template"):
            return str(self.design["cover_template"])
        has_img = bool(self.design.get("cover_image_file_id") or (slots or {}).get("image"))
        if has_img:
            return "C02" if self.theme.master_id == "retail_fnb" else "C01"
        return "C03"

    def _resolve_code(self, s: dict[str, Any]) -> str:
        t = self.cat.get(str(s.get("template_code") or ""), s.get("slots") or s.get("content"))
        return t["code"] if t else ""

    def _role(self, s: dict[str, Any]) -> str:
        t = self.cat.get(str(s.get("template_code") or ""), s.get("slots") or s.get("content"))
        return t["sheet_role"] if t else ""

    # ── 렌더 ────────────────────────────────────────────
    def render(self, document: dict[str, Any]) -> bytes:
        token = TBD_LABEL.set(self.tbd_label) if self.tbd_label else None
        try:
            return self._render(document)
        finally:
            if token is not None:
                TBD_LABEL.reset(token)

    def _render(self, document: dict[str, Any]) -> bytes:
        plan = self.plan(document)
        prs, layout = self._open()
        W, H = prs.slide_width, prs.slide_height
        footer_default = document.get("footer") or self._footer_from(document)
        for i, s in enumerate(plan, start=1):
            code = str(s.get("template_code"))
            slots_in = s.get("slots") if s.get("slots") is not None else (s.get("content") or {})
            t = self.cat.get(code, slots_in)
            if t is None:
                raise RenderError("TEMPLATE_NOT_FOUND", f"템플릿을 찾을 수 없습니다: {code}", {"template_code": code, "slide": i})
            self.template_codes.append(t["code"])
            slide = prs.slides.add_slide(layout)
            for ph in list(slide.placeholders):
                ph._element.getparent().remove(ph._element)
            lang = s.get("_lang") or self.lang
            self._check_slots(t, slots_in, i)
            moved: list[str] = []
            values = self._values(t, s, slots_in, lang, footer_default)
            if self.tbd_mode == "notes":
                values = {k: (v if k in ("sources", "logo") else _move_marks(v, moved, lang)) for k, v in values.items()}
            ctx = Ctx(template=t, values=values, slot_defs={d["key"]: d for d in t["slots"]},
                      lang=lang, slide_no=i, warnings=self.warnings)
            cv = Canvas(slide, W, H, self.theme, lang)
            self._draw_slide(cv, ctx)
            # 출처 상자가 없는 템플릿(표지 · 간지 등)은 출처를 발표자 노트로 옮긴다
            has_src_box = any(b.get("slot") == "sources" for b in t["boxes"])
            self._notes(slide, s, lang, [] if has_src_box else as_sources(ctx.values.get("sources"), lang), moved)
        self.slide_count = len(plan)
        buf = io.BytesIO()
        prs.save(buf)
        return buf.getvalue()

    def _footer_from(self, document: dict[str, Any]) -> str:
        cover = document.get("cover") or {}
        parts = [to_text(cover.get("customer"), self.lang), to_text(cover.get("title") or document.get("title"), self.lang)]
        return " · ".join(p for p in parts if p)

    def _open(self) -> tuple[Any, Any]:
        master = self.design.get("_master_bytes")
        if master:
            prs = open_master(master)
        else:
            prs = Presentation()
            prs.slide_width, prs.slide_height = Emu(SLIDE_W), Emu(SLIDE_H)
        return prs, pick_layout(prs)

    def _values(self, t: dict[str, Any], s: dict[str, Any], slots_in: dict[str, Any], lang: str, footer_default: str) -> dict[str, Any]:
        vals: dict[str, Any] = {}
        for d in t["slots"]:
            k = d["key"]
            v = slots_in.get(k) if isinstance(slots_in, dict) else None
            if v in (None, "", []) and d.get("default") is not None:
                v = d.get("default_en") if (lang == "en" and d.get("default_en") is not None) else d.get("default")
            vals[k] = v
        if vals.get("footer") in (None, "") and footer_default:
            vals["footer"] = footer_default
        if vals.get("logo") in (None, "") and self.design.get("logo_file_id"):
            vals["logo"] = self.design["logo_file_id"]
        if t["sheet_role"] in COVER_ROLES and "image" in vals and vals.get("image") in (None, "") and self.design.get("cover_image_file_id"):
            vals["image"] = self.design["cover_image_file_id"]
        extra = as_sources(s.get("sources") or s.get("footnotes"), lang)
        if extra:
            vals["sources"] = as_sources(vals.get("sources"), lang) + extra
        return vals

    def _check_slots(self, t: dict[str, Any], slots_in: Any, slide_no: int) -> None:
        if not isinstance(slots_in, dict):
            return
        keys = {d["key"] for d in t["slots"]}
        unknown = sorted(k for k in slots_in if k not in keys and not k.startswith("_"))
        if unknown:
            self.warnings.append(f"{t['code']} #{slide_no}: 템플릿에 없는 칸 {', '.join(unknown[:8])}")
        missing = [d["key"] for d in t["slots"] if d.get("required") and slots_in.get(d["key"]) in (None, "", [], {})]
        if missing:
            self.warnings.append(f"{t['code']} #{slide_no}: 필수 칸이 비어 있음 {', '.join(missing)}")

    def _notes(self, slide: Any, s: dict[str, Any], lang: str, sources: list[dict[str, str]] | None = None,
               moved: list[str] | None = None) -> None:
        lines = []
        if s.get("notes"):
            lines.append(to_text(s["notes"], lang))
        for c in as_list(s.get("confirm")) + list(moved or []):
            lines.append(f"{label('confirm', lang)} {to_text(c, lang)}")
        if sources:
            lines.append(f"{label('source', lang)}: " + " · ".join(
                f"{x['label']} ({x['url']})" if x.get("url") else x["label"] for x in sources))
        if lines:
            slide.notes_slide.notes_text_frame.text = "\n".join(lines)

    # ── 슬라이드 하나 ─────────────────────────────────────
    def _draw_slide(self, cv: Canvas, ctx: Ctx) -> None:
        boxes = ctx.template["boxes"]
        has_footer = any(b.get("slot") == "footer" for b in boxes)
        for box in boxes:
            try:
                self._draw_box(cv, ctx, box)
            except Exception as exc:  # noqa: BLE001
                msg = f"{ctx.template['code']} #{ctx.slide_no} {box.get('slot')}/{box.get('style')}: {type(exc).__name__}: {exc}"
                log.warning("box failed %s", msg, exc_info=True)
                ctx.warnings.append(msg)
        if has_footer:
            fx = min((b["x"] * 1280 for b in boxes if b.get("slot") in ("footer", "logo") and b["y"] * 720 > 640), default=64.0)
            cv.rect(fx, 668, 1216 - fx, 1, fill="line")
            if self.design.get("page_numbers", True):
                txt = f"{label('confidential', ctx.lang)} · {ctx.slide_no}" if self.confidential else str(ctx.slide_no)
                cv.fit_text(1016, 683, 200, 16, [(txt, 11, False, "gray2")], align="right", number_first=True)

    # ── 상자 ─────────────────────────────────────────────
    def _geom(self, box: dict[str, Any]) -> tuple[float, float, float, float]:
        return box["x"] * 1280, box["y"] * 720, box["w"] * 1280, box["h"] * 720

    def _value(self, ctx: Ctx, box: dict[str, Any]) -> tuple[Any, str, dict[str, Any]]:
        slot = box["slot"]
        sd = ctx.slot_defs.get(slot, {"type": "text"})
        v = ctx.values.get(slot)
        if "index" in box:
            lst = v if isinstance(v, list) else ([] if v is None else [v] if box["index"] == 0 else [])
            v = lst[box["index"]] if box["index"] < len(lst) else None
        t = sd.get("type", "text")
        meta = sd
        if "part" in box:
            item = localize(v, ctx.lang)
            v = item.get(box["part"]) if isinstance(item, dict) else None
            fd = next((f for f in sd.get("fields", []) if f["key"] == box["part"]), {"type": "text"})
            t, meta = fd.get("type", "text"), fd
        return v, t, meta

    def _draw_box(self, cv: Canvas, ctx: Ctx, box: dict[str, Any]) -> None:
        x, y, w, h = self._geom(box)
        st = box["style"]
        if box.get("slot") is None:
            self._deco(cv, st, x, y, w, h)
            return
        slot = box["slot"]
        if st == "hidden":
            return
        if box.get("unless") and _filled(ctx.values.get(box["unless"])):
            return          # 대안 상자(예: 지도 그림이 있으면 지역 타일은 그리지 않는다)
        if slot == "sources":
            self._draw_sources(cv, ctx, x, y, w, h, inv=st.endswith("_inv"))
            return
        if st in ("logo", "logo_plate") or ctx.slot_defs.get(slot, {}).get("type") == "logo":
            self._logo(cv, ctx, ctx.values.get(slot), x, y, w, h, plate=st == "logo_plate")
            return
        # 한 칸 전체를 쓰는 합성 스타일
        if st in ("plot", "plot_quad"):
            return self._plot(cv, ctx, box, x, y, w, h)
        if st in ("pins",):
            return self._pins(cv, ctx, box, x, y, w, h)
        if st == "emotion_curve":
            return self._emotion(cv, ctx, box, x, y, w, h)
        if st == "swimlane":
            return self._swimlane(cv, ctx, ctx.values.get(slot), x, y, w, h)
        if st == "gantt":
            return self._gantt(cv, ctx, box, x, y, w, h)
        if st == "region_tiles":
            return self._region_tiles(cv, ctx, ctx.values.get(slot), x, y, w, h)
        v, t, meta = self._value(ctx, box)
        if t == "card" and "part" not in box:
            return self._card(cv, ctx, box, as_card(v, ctx.lang), meta, x, y, w, h)
        if t == "kpi" or st.startswith("kpi"):
            return self._kpi(cv, ctx, st, as_kpi(v, ctx.lang), x, y, w, h, index=box.get("index", 0))
        if t in ("image", "logo") or st.startswith("image"):
            off = bool(box.get("placeholder_unless") and _filled(ctx.values.get(box["placeholder_unless"])))
            return self._image(cv, ctx, v, st, x, y, w, h, meta=meta, alt=self._alt_label(ctx, box), placeholder_off=off)
        if t == "table" or st.startswith("table") or st == "matrix":
            return self._table(cv, ctx, st, as_table(v, ctx.lang), x, y, w, h)
        if t == "chart" or st == "chart":
            return self._chart(cv, ctx, v, x, y, w, h)
        if t == "bullets" or st in ("bullets", "list", "list_inv", "chips", "chips_inv", "chips_white", "chips_right"):
            return self._bullets(cv, ctx, st, as_bullets(v, ctx.lang), x, y, w, h)
        text = self._clip(to_text(v, ctx.lang), meta, ctx.lang)
        if st in CELL_FILLS and "part" in box:
            return self._cell(cv, ctx, box, st, text, x, y, w, h)
        return self._text(cv, ctx, st, text, x, y, w, h, box)

    def _clip(self, text: str, meta: dict[str, Any], lang: str) -> str:
        if not text:
            return text
        mc = meta.get("max_chars")
        if lang == "both" and "\n" in text:
            ko, _, en = text.partition("\n")
            return textfit.clip_chars(ko, mc) + "\n" + textfit.clip_chars(en, mc, EN_FACTOR)
        return textfit.clip_chars(text, mc, EN_FACTOR if lang == "en" else 1.0)

    def _alt_label(self, ctx: Ctx, box: dict[str, Any]) -> str:
        sd = ctx.slot_defs.get(box["slot"], {})
        if "index" in box:
            item = ctx.values.get(box["slot"])
            if isinstance(item, list) and box["index"] < len(item):
                it = localize(item[box["index"]], ctx.lang)
                if isinstance(it, dict) and it.get("title"):
                    return to_text(it.get("title"), ctx.lang)
        lbl = sd.get("label", label("image", ctx.lang))
        return re.split(r"[(—]", lbl)[0].strip() if ctx.lang != "en" else label("image", "en")

    # ── 글 ─────────────────────────────────────────────
    def _text(self, cv: Canvas, ctx: Ctx, st: str, text: str, x: float, y: float, w: float, h: float,
              box: dict[str, Any]) -> None:
        if not text:
            return
        align = box.get("align", "left")
        if st in ("chip_brand", "chip_dark", "pill_gray", "pill_brand", "pill_brand_left", "pill_tint", "label_chip"):
            return self._pill(cv, st, text, x, y, w, h, align=align)
        if st == "circle_brand":
            cv.ellipse(x, y, w, h, fill="brand")
            cv.fit_text(x + w * 0.14, y + h * 0.18, w * 0.72, h * 0.64, [(text, 19, True, "on_brand")], align="center", anchor="middle")
            return
        if st == "axis_v":
            cv.rect(x, y, w, h, fill=None, line="line", radius=10)
            cv.fit_text(x + 4, y + 8, w - 8, h - 16, [(text, 14, True, "ink2")], align="center", anchor="middle")
            return
        if st == "swatch":
            m = re.search(r"#[0-9a-fA-F]{6}", text)
            if m:
                cv.rect(x, y + 2, h - 4, h - 4, fill=m.group(0), line="line", radius=4)
                text = text.replace(m.group(0), "").strip(" ·")
                x += h + 4
                w -= h + 4
            cv.fit_text(x, y, w, h, [(text, 12.5, False, "ink2")], anchor="middle")
            return
        spec = TEXT_STYLES.get(st, TEXT_STYLES["body"])
        line = spec.get("line", 1.3)
        items = [(text, spec["size"], spec.get("bold", False), spec["color"])]
        if ctx.lang == "both" and "\n" in text:
            # 한 칸에 두 언어 — 영어는 작게 · 연하게 둘째 줄로
            ko, _, en = text.partition("\n")
            sub_col = "on_brand_sub" if spec["color"] in ("white", "on_brand_sub") else "gray"
            items = [(ko, spec["size"], spec.get("bold", False), spec["color"]), (en, max(10.0, spec["size"] * 0.62), False, sub_col)]
        cv.fit_text(x, y, w, h, items, align=align, anchor=spec.get("anchor", "top"), line=line,
                    number_first=spec.get("number", False), min_scale=min(0.6, spec.get("min_scale", 0.66)) if len(items) > 1 else spec.get("min_scale", 0.66))

    def _pill(self, cv: Canvas, st: str, text: str, x: float, y: float, w: float, h: float, align: str = "left") -> None:
        fills = {"chip_brand": ("brand", "on_brand"), "chip_dark": ("ink", "white"), "pill_gray": ("#e2e5ea", "ink2"),
                 "pill_brand": ("brand", "on_brand"), "pill_brand_left": ("brand", "on_brand"), "pill_tint": ("tint", "brand_text"),
                 "label_chip": ("white", "ink2")}
        fill, col = fills.get(st, ("panel", "ink2"))
        size = min(14.0, h * 0.5)
        tw = textfit.text_width(text, size, True) / textfit.SLACK + 30
        pw = min(w, max(h, tw)) if st not in ("pill_brand",) else w
        px = x if align == "left" else (x + (w - pw) / 2 if align == "center" else x + w - pw)
        cv.rect(px, y, pw, h, fill=fill, radius=h / 2)
        cv.fit_text(px + 10, y, pw - 20, h, [(text, size, True, col)], align="center", anchor="middle")

    def _bullets(self, cv: Canvas, ctx: Ctx, st: str, items: list[str], x: float, y: float, w: float, h: float) -> None:
        if not items:
            return
        if st.startswith("chips"):
            fill, col, line = {"chips": ("white", "ink2", "line2"), "chips_inv": ("#ffffff", "ink", None),
                               "chips_white": ("white", "ink", None), "chips_right": ("panel", "ink2", "line")}.get(st, ("white", "ink2", "line2"))
            size = 12.5
            ch = min(h, 28)
            xs = x if st != "chips_right" else None
            widths = [min(w, textfit.text_width(t, size, True) / textfit.SLACK + 26) for t in items]
            if st == "chips_right":
                xs = x + w - (sum(widths) + 8 * (len(widths) - 1))
                xs = max(x, xs)
            cx, cy = xs, y
            for t, cw in zip(items, widths):
                if cx + cw > x + w + 0.5 and cx > (xs or x):
                    cx = xs or x
                    cy += ch + 6
                    if cy + ch > y + h + 0.5:
                        break
                cv.rect(cx, cy, cw, ch, fill=fill, line=line, radius=ch / 2)
                cv.fit_text(cx + 8, cy, cw - 16, ch, [(t, size, True, col)], align="center", anchor="middle")
                cx += cw + 8
            return
        inv = st.endswith("_inv")
        col = "white" if inv else "ink2"
        if st.startswith("list"):
            paras = [textfit.Para(f"{i + 1:02d}  {t}", 16, False, 1.35, space_before=(10 if i else 0), color=col)
                     for i, t in enumerate(items)]
        else:
            paras = [textfit.Para(f"•  {t}", 15, False, 1.4, space_before=(6 if i else 0), color=col) for i, t in enumerate(items)]
        cv.fit_paras(x, y, w, h, paras)

    def _draw_sources(self, cv: Canvas, ctx: Ctx, x: float, y: float, w: float, h: float, inv: bool = False) -> None:
        srcs = as_sources(ctx.values.get("sources"), ctx.lang)
        if not srcs:
            return
        col = "#c9ced6" if inv else "gray2"
        runs = [Run(f"{label('source', ctx.lang)}: ", 10.5, True, col)]
        for i, s in enumerate(srcs):
            if i:
                runs.append(Run(" · ", 10.5, False, col))
            runs.append(Run(s["label"], 10.5, False, col, url=s.get("url") or None))
        total = "".join(r.text for r in runs)
        if textfit.text_width(total, 10.5) > w * textfit.SLACK:
            # 한 줄에 맞게 뒤를 줄인다(링크는 생략)
            keep = textfit.truncate_to(textfit.Para(total, 10.5), w, 1, 1.0)
            runs = [Run(keep, 10.5, False, col)]
        cv.text(x, y, w, h, [P(runs)], anchor="top")

    def _logo(self, cv: Canvas, ctx: Ctx, v: Any, x: float, y: float, w: float, h: float, plate: bool = False) -> None:
        ref = image_ref(v)
        if not ref:
            return
        a = self.assets.get(ref["file_id"])
        if a is None:
            ctx.warnings.append(f"logo missing {ref['file_id']}")
            return
        if "svg" in (a.mime or "") or a.data[:200].lstrip().startswith((b"<svg", b"<?xml")):
            ctx.warnings.append("SVG 로고는 PNG 로 바꿔 올려 주세요(래스터 변환기 없음)")
            return
        if plate:
            cv.rect(x - 8, y - 6, w + 16, h + 12, fill="white", radius=6, alpha=0.85)
        cv.picture(a.data, x, y, w, h, fit="contain")

    # ── 칸 조각(part) ────────────────────────────────────
    def _cell(self, cv: Canvas, ctx: Ctx, box: dict[str, Any], st: str, text: str, x: float, y: float, w: float, h: float) -> None:
        fill, line = CELL_FILLS.get(st, (None, None))
        if fill or line:
            cv.rect(x, y, w, h, fill=fill, line=line, radius=10)
        item = self._item(ctx, box)
        pad = 16 if (fill or line) else 2
        if st == "cell_title_body":
            body = to_text(item.get("body"), ctx.lang)
            cv.fit_text(x, y + 6, w, h - 12, [(text, 16, True, "ink"), (body, 12.5, False, "gray2")], anchor="middle", gap=3)
            return
        if st == "cell_gray_titled":
            ttl = to_text(item.get("label"), ctx.lang)
            cv.fit_text(x + pad, y + 10, w - 2 * pad, h - 20, [(ttl, 15.5, True, "ink"), (text, 13, False, "gray")], gap=4)
            return
        if st == "cell_left_card":
            sub = to_text(item.get("left_sub"), ctx.lang)
            cv.fit_text(x + pad, y + 12, w - 2 * pad, h - 24, [(text, 16, True, "ink"), (sub, 12.5, False, "gray")], gap=4, anchor="middle")
            return
        if st == "cell_mid":
            chips = as_bullets(item.get("chips"), ctx.lang)
            cv.fit_text(x + 4, y + 8, w - 8, h - (44 if chips else 16), [(text, 16, True, "ink")], anchor="middle")
            if chips:
                self._bullets(cv, ctx, "chips", chips, x + 4, y + h - 34, w - 8, 26)
            return
        if st == "cell_value":
            kpi = as_kpi(item.get("kpi"), ctx.lang)
            kpi_h = 48 if kpi else 0
            cv.fit_text(x + pad, y + 12, w - 2 * pad, h - 24 - kpi_h, [(text, 16, True, "ink")], anchor="middle")
            if kpi:
                self._kpi_runs(cv, kpi, x + pad, y + h - kpi_h - 8, w - 2 * pad, kpi_h, size=24, color="brand_text")
            return
        styles = {
            "cell": (13.5, False, "ink2", "top"), "cell_head": (14, True, "ink", "middle"), "cell_tint": (13.5, False, "ink", "top"),
            "cell_outline": (13.5, False, "ink2", "top"), "cell_gray": (15, False, "gray", "middle"),
            "cell_tint_strong": (15.5, True, "ink", "middle"), "cell_strong": (15, True, "ink", "middle"),
            "cell_num": (17, True, "brand_text", "middle"),
        }
        size, bold, col, anchor = styles.get(st, (13.5, False, "ink2", "top"))
        cv.fit_text(x + pad, y + (10 if anchor == "top" else 6), w - 2 * pad, h - (20 if anchor == "top" else 12),
                    [(text, size, bold, col)], anchor=anchor, number_first=st == "cell_num")

    def _item(self, ctx: Ctx, box: dict[str, Any]) -> dict[str, Any]:
        v = ctx.values.get(box["slot"])
        if "index" in box:
            v = v[box["index"]] if isinstance(v, list) and box["index"] < len(v) else None
        v = localize(v, ctx.lang)
        return v if isinstance(v, dict) else {}

    # ── 카드 ─────────────────────────────────────────────
    def _card(self, cv: Canvas, ctx: Ctx, box: dict[str, Any], item: dict[str, Any], meta: dict[str, Any],
              x: float, y: float, w: float, h: float) -> None:
        st = box["style"]
        spec = CARDS.get(st, CARDS["card"])
        lang = ctx.lang
        index = box.get("index", 0)
        if not item and not self.placeholders:
            return
        recommended = False
        if st == "card_option":
            try:
                recommended = int(to_text(ctx.values.get(box.get("recommended", "recommended")) or 0, lang) or 0) == index + 1
            except ValueError:
                recommended = False
        fill, line, lw = spec.fill, spec.line, spec.line_w
        if recommended:
            line, lw = "brand", 2.0
        if st == "circle_card_brand":
            cv.ellipse(x, y, w, h, fill="brand")
        elif fill or line:
            cv.rect(x, y, w, h, fill=fill, line=line, line_w=lw, radius=spec.radius,
                    alpha=0.55 if st == "tile_dark" else None)
        if not item:
            return
        inv = spec.inv
        c_title = "white" if inv else spec.title_color
        c_body = "on_brand_sub" if inv and fill == "brand" else ("#c9ced6" if inv else "ink2")
        c_sub = "on_brand_sub" if inv else "gray"
        pad = spec.pad
        ix, iy, iw, ih = x + pad, y + pad, w - 2 * pad, h - 2 * pad
        if st in ("contact", "contact_row", "legend_row", "toc_row"):
            ix, iy, iw, ih = x, y, w, h
        if st == "toc_row":
            cv.rect(x, y + h - 1, w, 1, fill="line")
        if recommended:
            self._pill(cv, "chip_brand", "추천" if lang != "en" else "Recommended", x + w - 92, y - 13, 80, 26, align="center")
        # 이미지
        img = item.get("image")
        if spec.image == "top" and (img or self.placeholders) and "image" in {f["key"] for f in meta.get("fields", [])}:
            ih_img = ih * spec.image_frac
            if spec.image_bg:
                cv.rect(ix, iy, iw, ih_img, fill=spec.image_bg, radius=10)
            self._image(cv, ctx, img, "image_contain" if self._grade(meta) in ("C", "E") else "image", ix, iy, iw, ih_img,
                        meta=self._field(meta, "image"), alt=to_text(item.get("title"), lang))
            iy += ih_img + 12
            ih -= ih_img + 12
        elif spec.image == "left" and "image" in {f["key"] for f in meta.get("fields", [])}:
            iw_img = min(ih * 1.15, iw * 0.4)
            if spec.image_bg:
                cv.rect(ix, iy, iw_img, ih, fill=spec.image_bg, radius=10)
            self._image(cv, ctx, img, "image_contain" if self._grade(meta) in ("C", "E") else "image", ix, iy, iw_img, ih,
                        meta=self._field(meta, "image"), alt=to_text(item.get("title"), lang))
            ix += iw_img + 16
            iw -= iw_img + 16
        # 행형 번호 원
        no = to_text(item.get("no") or item.get("letter"), lang)
        if spec.layout == "row" and spec.badge:
            d = min(32.0, ih * 0.9 if ih > 0 else 32.0)
            if st == "legend_row" or no or st in ("card_pin", "card_space_row", "card_row_text"):
                badge = no or f"{index + 1}"
                fill_b = "ink" if (st == "legend_row" and badge.upper() == "S") else "brand"
                cy = iy + (ih - d) / 2 if st in ("card_space_row", "legend_row") else iy
                cv.ellipse(ix, cy, d, d, fill=fill_b)
                cv.fit_text(ix, cy, d, d, [(badge, 13, True, "on_brand")], align="center", anchor="middle", number_first=True)
                ix += d + 12
                iw -= d + 12
        elif spec.badge and spec.layout != "row":
            d = 26.0
            badge = no or f"{index + 1}"
            cv.ellipse(ix, iy, d, d, fill="brand")
            cv.fit_text(ix, iy, d, d, [(badge, 12, True, "on_brand")], align="center", anchor="middle", number_first=True)
            iy += d + 8
            ih -= d + 8
        if st == "toc_row":
            cv.fit_text(ix, iy, 64, ih, [(no or f"{index + 1:02d}", 30, True, "brand_text")], anchor="middle", number_first=True)
            ix += 76
            iw -= 76
        if st == "floor_row":
            tag = to_text(item.get("tag"), lang)
            cv.rect(x, y, 96, h, fill="ink", radius=10)
            cv.fit_text(x + 8, y, 80, h, [(tag, 16, True, "white")], align="center", anchor="middle", number_first=True)
            ix, iw = x + 112, w - 120
        # 아래쪽: 수치 · 메모 · 칩
        kpi = as_kpi(item.get("kpi"), lang)
        note = to_text(item.get("note") or item.get("who"), lang) if st not in ("card_person",) else to_text(item.get("who"), lang)
        chips = as_bullets(item.get("chips"), lang)
        bottom = iy + ih
        kpi_h = 0.0
        right_w = 0.0
        if kpi and spec.layout == "row":
            right_w = min(150.0, iw * 0.3)
            self._kpi_runs(cv, kpi, ix + iw - right_w, iy, right_w, ih, size=min(28, spec.kpi_size), color="white" if inv else "brand_text",
                           align="right", anchor="middle", inv=inv)
            iw -= right_w + 12
        elif kpi and not spec.kpi_first:
            need = spec.kpi_size * 1.25 + (18 if kpi.get("label") else 0) + 6
            kpi_h = min(ih * 0.45, need)
            ks = max(0.4, kpi_h / need)          # 좁은 카드는 수치도 함께 줄인다(글과 겹치지 않게)
            if st == "card_challenge":
                cv.rect(ix, bottom - kpi_h - 14, iw, 1, fill="line3")
            self._kpi_runs(cv, kpi, ix, bottom - kpi_h, iw, kpi_h, size=spec.kpi_size * ks, color="white" if inv else "brand_text",
                           inv=inv, label_top=st in ("card_challenge",), scale=ks)
            bottom -= kpi_h + (20 if st == "card_challenge" else 10) * ks
        if chips and spec.layout != "row":
            ch_h = 28 if len(chips) <= 3 else 62
            self._bullets(cv, ctx, "chips_inv" if inv else "chips", chips, ix, bottom - ch_h, iw, ch_h)
            bottom -= ch_h + 8
        if note and spec.layout != "row" and st not in ("contact",):
            cv.fit_text(ix, bottom - 18, iw, 18, [(note, 11.5, False, c_sub)])
            bottom -= 24
        if st == "card_step":
            owner, days = to_text(item.get("owner"), lang), to_text(item.get("days"), lang)
            if owner or days:
                cv.rect(ix, bottom - 50, iw, 1, fill="line")
                cv.fit_text(ix, bottom - 42, iw, 18, [(owner, 13, False, "ink2")])
                cv.fit_text(ix, bottom - 22, iw, 22, [(days, 18, True, "ink")], number_first=True)
                bottom -= 58
        # 위쪽 줄: 번호 · 태그
        tag = to_text(item.get("tag") or item.get("role") or item.get("when") or item.get("time") or item.get("label"), lang)
        if st == "floor_row":
            tag = ""
        if st == "card_step" and not tag:
            tag = f"STEP {no or index + 1:0>2}" if isinstance(no, str) else f"STEP {index + 1:02d}"
            no = ""
        if spec.no_big and no:
            cv.fit_text(ix, iy, iw * 0.5, 36, [(no, 30, True, "line2" if not inv else "on_brand_sub")], number_first=True)
            if tag:
                self._pill(cv, "label_chip" if not spec.tag_brand else "pill_tint", tag, ix + iw * 0.5, iy + 4, iw * 0.5, 26, align="right")
            iy += 50
        elif tag and st in ("card_challenge", "card_person", "card_finding", "card_swot", "card_swot_tint") and spec.layout != "row":
            self._pill(cv, "pill_tint" if spec.tag_brand else "label_chip", tag, ix, iy, iw, 26)
            iy += 36
            tag = ""
        bullets = as_bullets(item.get("bullets"), lang)
        quote = to_text(item.get("quote"), lang)
        title = to_text(item.get("title") or item.get("name"), lang)
        if st in ("card_swot", "card_swot_tint"):
            letter = to_text(item.get("letter"), lang)
            if letter:
                cv.fit_text(ix, iy, 48, 46, [(letter, 40, True, "brand_text" if st == "card_swot_tint" else "ink")], number_first=True)
                cv.fit_text(ix + 56, iy + 8, iw - 56, 32, [(title, spec.title, True, "ink")], anchor="middle")
                iy += 56
                title = ""
        if st == "card_person":
            name = to_text(item.get("name"), lang)
            if name and item.get("title"):
                title = name
                bullets = [to_text(item.get("title"), lang)] + bullets
        sub = " · ".join(p for p in (to_text(item.get("model"), lang),
                                      (("×" + to_text(item.get("qty"), lang)) if item.get("qty") not in (None, "") else "")) if p)
        body = to_text(item.get("body"), lang)
        if st in ("card_white_row", "card_finding") and no and spec.layout == "row":
            title = f"{no}  {title}" if title else no
        paras: list[textfit.Para] = []
        if tag and not spec.no_big:
            paras.append(textfit.Para(tag, 12.5, True, 1.2, color="on_brand_sub" if inv else "brand_text", shrink=False, cut=False))
        elif no and not spec.no_big and spec.layout != "row" and not spec.badge and st not in ("card_white_row", "card_finding"):
            paras.append(textfit.Para(no, 13, True, 1.2, color="on_brand_sub" if inv else "brand_text", number=True, shrink=False, cut=False))
        if title:
            paras.append(textfit.Para(title, spec.title, True, 1.3, space_before=4, color=c_title, cut=True))
        if sub:
            paras.append(textfit.Para(sub, max(11.5, spec.body - 1), True, 1.3, space_before=2, color=c_sub, number=True))
        if body:
            paras.append(textfit.Para(body, spec.body, False, 1.5, space_before=8, color=c_body))
        for i, b in enumerate(bullets):
            paras.append(textfit.Para(f"•  {b}", spec.body, False, 1.4, space_before=(8 if i == 0 else 3), color=c_body))
        if quote:
            paras.append(textfit.Para(f"“{quote}”", spec.body - 0.5, False, 1.45, space_before=10, color=c_sub))
        if spec.kpi_first and kpi:
            kh = spec.kpi_size * 1.25 + (16 if kpi.get("label") else 0)
            self._kpi_runs(cv, kpi, ix, iy, iw, kh, size=spec.kpi_size, color="white" if inv else "brand_text", inv=inv)
            iy += kh + 8
        avail = bottom - iy
        if st == "contact_row" or (spec.layout == "row" and spec.anchor == "top" and st not in ("card_pin", "card_space_row")):
            anchor = "middle"
        else:
            anchor = spec.anchor
        if avail > 8 and paras:
            cv.fit_paras(ix, iy, iw, avail, paras, anchor=anchor)

    def _grade(self, meta: dict[str, Any]) -> str:
        f = self._field(meta, "image")
        return (f or {}).get("image_grade") or "A"

    @staticmethod
    def _field(meta: dict[str, Any], key: str) -> dict[str, Any]:
        return next((f for f in meta.get("fields", []) if f["key"] == key), {})

    # ── 수치 ─────────────────────────────────────────────
    def _kpi_runs(self, cv: Canvas, kpi: dict[str, str], x: float, y: float, w: float, h: float, *, size: float = 32,
                  color: str = "brand_text", align: str = "left", anchor: str = "bottom", inv: bool = False,
                  label_top: bool = False, scale: float = 1.0) -> None:
        if not kpi:
            return
        ls = max(0.72, min(1.0, scale))     # 라벨 · 보조 글 크기 배율
        value, unit, pre = kpi.get("value", ""), kpi.get("unit", ""), kpi.get("pre", "")
        lab = kpi.get("label", "")
        sub = kpi.get("sub", "") or kpi.get("delta", "")
        lab_col = "on_brand_sub" if inv else "gray"
        line_runs: list[Run] = []
        # 한 줄에 맞도록 값 크기 조정
        total_w = textfit.text_width(value, size, True) + textfit.text_width(f" {unit}", size * 0.45, True) + textfit.text_width(f"{pre} ", size * 0.42, True)
        sc = min(1.0, (w * 0.96) / total_w) if total_w > 0 else 1.0
        sc = max(sc, 0.45)
        if pre:
            line_runs.append(Run(f"{pre} ", size * 0.42 * sc, True, color if not inv else "white"))
        line_runs.append(Run(value, size * sc, True, color, number=True))
        if unit:
            line_runs.append(Run(f" {unit}", max(11.0, size * 0.45 * sc), True, color))
        paras: list[P] = []
        if lab and label_top:
            paras.append(P([Run(lab, 12.5 * ls, True, lab_col)], align=align, line=1.2))
        paras.append(P(line_runs, align=align, line=1.0, space_before=4 * ls if paras else 0))
        if lab and not label_top:
            paras.append(P([Run(lab, 12.5 * ls, False, lab_col)], align=align, line=1.2, space_before=4 * ls))
        if sub and h >= size * 1.0 + (16 if lab else 0) + 14:
            paras.append(P([Run(sub, 11.5 * ls, False, lab_col)], align=align, line=1.2, space_before=2))
        cv.text(x, y, w, h, paras, anchor=anchor)

    def _kpi(self, cv: Canvas, ctx: Ctx, st: str, kpi: dict[str, str], x: float, y: float, w: float, h: float,
             index: int = 0) -> None:
        if st == "kpi_circle":
            fills = [("tint2", "soft"), ("tint", "mid"), ("brand", None)]
            fill, line = fills[min(index, 2)]
            cv.ellipse(x, y, w, h, fill=fill, line=line, line_w=1.5)
            if not kpi:
                return
            inv = fill == "brand"
            if index < 2:
                ty, th = y + h * 0.07, h * 0.2
            else:
                ty, th = y + h * 0.22, h * 0.56
            cv.text(x + w * 0.15, ty, w * 0.7, th, [
                P([Run(kpi.get("label", ""), 13, True, "on_brand_sub" if inv else "gray")], align="center", line=1.1),
                P([Run(kpi.get("value", ""), 30 if index < 2 else 32, True, "white" if inv else "brand_text", number=True),
                   Run(f" {kpi.get('unit', '')}" if kpi.get("unit") else "", 14, True, "white" if inv else "brand_text")],
                  align="center", line=1.0, space_before=2)], anchor="middle")
            return
        if st == "kpi_multiplier":
            cv.text(x, y, w, h, [P([Run("×", 30, True, "mid", number=True)], align="center", line=1.0),
                                 P([Run(kpi.get("value", ""), 56, True, "brand_text", number=True)], align="center", line=1.0),
                                 P([Run(kpi.get("unit", ""), 15, True, "brand_text")], align="center"),
                                 P([Run(kpi.get("sub", "") or kpi.get("label", ""), 12.5, False, "gray")], align="center", space_before=8)],
                    anchor="middle")
            return
        if st in ("kpi_bar", "kpi_bar_brand"):
            if not kpi:
                return
            brand = st == "kpi_bar_brand"
            col = "brand_text" if brand else "ink"
            self._kpi_runs(cv, {k: v for k, v in kpi.items() if k in ("value", "unit", "pre")}, x, y, w, h - 22, size=30,
                           color=col, anchor="bottom")
            bar = float(kpi.get("bar") or (100 if not brand else 0) or 0)
            cv.rect(x, y + h - 14, w, 10, fill="panel", radius=5)
            if bar > 0:
                cv.rect(x, y + h - 14, w * bar / 100.0, 10, fill="brand" if brand else "line2", radius=5)
            return
        boxes = {
            "kpi_card": ("panel", None, 24, 40), "kpi_tile": ("white", None, 12, 20), "kpi_tile_line": ("white", "line", 14, 26),
            "kpi_inv": (None, None, 0, 44), "kpi_brand": ("brand", None, 22, 40), "kpi_big": (None, None, 0, 52),
            "kpi_big_card": ("panel", None, 26, 64), "kpi_inline": (None, None, 0, 24), "kpi": (None, None, 0, 36),
            "kpi_cell": ("panel", None, 16, 26), "kpi_cell_brand": ("tint", None, 16, 26),
        }
        fill, line, pad, size = boxes.get(st, (None, None, 0, 36))
        if fill or line:
            cv.rect(x, y, w, h, fill=fill, line=line, radius=12 if st not in ("kpi_tile",) else 10)
        if not kpi:
            return
        inv = st in ("kpi_inv", "kpi_brand")
        col = "white" if inv else "brand_text"
        if st == "kpi_inline":
            runs = [Run(kpi.get("label", "") + "  ", 13, False, "gray"), Run(kpi.get("value", ""), 24, True, "ink", number=True),
                    Run(f" {kpi.get('unit', '')}" if kpi.get("unit") else "", 14, True, "ink")]
            cv.text(x, y, w, h, [P(runs)], anchor="middle")
            return
        lab = kpi.get("label", "")
        if st in ("kpi_card", "kpi_tile", "kpi_tile_line", "kpi_brand", "kpi_inv", "kpi_cell", "kpi_cell_brand"):
            # 낮은 타일은 여백 · 글자를 함께 줄여 넘치지 않게 한다
            pad = min(pad, max(6.0, h * 0.15)) if pad else 0
            ix, iy, iw, ih = x + pad, y + pad, w - 2 * pad, h - 2 * pad
            lab_h = (20 if size < 30 else 22) if lab else 0
            gap = (4 if size < 30 else 8) if lab else 0
            need = lab_h + gap + size * 1.2 + (16 if kpi.get("sub") or kpi.get("delta") else 0)
            sc = max(0.5, min(1.0, ih / need)) if need > 0 else 1.0
            if lab:
                ls = max(0.8, sc)
                cv.fit_text(ix, iy, iw, lab_h * ls, [(lab, (12.5 if size < 30 else 14) * ls, True, "on_brand_sub" if inv else "gray")])
                iy += (lab_h + gap) * ls
                ih -= (lab_h + gap) * ls
            self._kpi_runs(cv, {k: v for k, v in kpi.items() if k != "label"}, ix, iy, iw, ih, size=size * sc, color=col, inv=inv,
                           anchor="top" if st in ("kpi_tile", "kpi_tile_line") else "bottom", scale=sc)
            return
        ix, iy, iw, ih = x + pad, y + pad, w - 2 * pad, h - 2 * pad
        self._kpi_runs(cv, kpi, ix, iy, iw, ih, size=size, color=col, inv=inv, align="center" if st == "kpi_big_card" else "left",
                       anchor="middle" if st in ("kpi_big_card", "kpi_big") else "top")

    # ── 그림 ─────────────────────────────────────────────
    def _image(self, cv: Canvas, ctx: Ctx, v: Any, st: str, x: float, y: float, w: float, h: float, *,
               meta: dict[str, Any] | None = None, alt: str = "", placeholder_off: bool = False) -> None:
        ref = image_ref(localize(v, ctx.lang))
        radius = 0 if st in ("image_full", "image_tile_full") else 12
        soft = st in ("image_contain_soft",)
        if soft:
            cv.rect(x, y, w, h, fill="panel", radius=14)
        a = self.assets.get(ref["file_id"]) if ref else None
        if a is None:
            if ref:
                ctx.warnings.append(f"image missing {ref['file_id']}")
            if self.placeholders and st != "image_contain_plain" and not placeholder_off:
                self._placeholder(cv, x, y, w, h, alt or label("image", ctx.lang), radius=radius, soft=soft)
            return
        grade = (meta or {}).get("image_grade")
        fit = (ref.get("fit") or ("contain" if st.startswith("image_contain") or grade in ("C", "E") else "cover"))
        pad = 0.06 * min(w, h) if (fit == "contain" and soft) else 0
        focus = ref.get("focus") or (0.5, 0.5)
        if isinstance(focus, (list, tuple)) and len(focus) == 2:
            focus = (float(focus[0]), float(focus[1]))
        else:
            focus = (0.5, 0.5)
        pic = cv.picture(a.data, x + pad, y + pad, w - 2 * pad, h - 2 * pad, fit=fit, radius=radius if fit == "cover" else 0, focus=focus)
        if pic is None:
            ctx.warnings.append(f"image unreadable {ref['file_id']}")
            if self.placeholders:
                self._placeholder(cv, x, y, w, h, alt or label("image", ctx.lang), radius=radius)
            return
        chip_parts = []
        if a.ai_generated or ref.get("ai_generated"):
            chip_parts.append(label("ai", ctx.lang))
        credit = to_text(ref.get("credit") or ref.get("caption"), ctx.lang)
        if credit:
            chip_parts.append(credit)
        if chip_parts and w > 80 and h > 40:
            txt = " · ".join(chip_parts)
            # 오른쪽 아래 — 왼쪽 아래는 캡션 · 위쪽은 태그 · 범례가 자주 놓인다
            cw = min(w - 16, textfit.text_width(txt, 10.5, True) / textfit.SLACK + 20)
            fill = "brand" if (a.ai_generated or ref.get("ai_generated")) else "ink"
            cx = x + w - 8 - cw
            cv.rect(cx, y + h - 26, cw, 18, fill=fill, radius=9, alpha=0.86)
            cv.fit_text(cx + 6, y + h - 26, cw - 12, 18, [(txt, 10.5, True, "white")], align="center", anchor="middle")

    def _placeholder(self, cv: Canvas, x: float, y: float, w: float, h: float, text: str, radius: float = 12,
                     soft: bool = False) -> None:
        if not soft:
            cv.rect(x, y, w, h, fill="placeholder", radius=radius)
        if w > 60 and h > 30:
            cv.fit_text(x + 8, y + 4, w - 16, h - 8, [(text, 13, False, "gray2")], align="center", anchor="middle")

    # ── 표 ──────────────────────────────────────────────
    def _table(self, cv: Canvas, ctx: Ctx, st: str, tbl: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
        cols = tbl.get("columns") or []
        rows = tbl.get("rows") or []
        if not cols and not rows:
            if self.placeholders:
                cv.rect(x, y, w, min(h, 120), fill=None, line="line", radius=10, dash=True)
            return
        n_cols = max(len(cols), max((len(r) for r in rows), default=0))
        if n_cols == 0:
            return
        lang = ctx.lang
        header = [col_label(c, lang) for c in cols] + [""] * (n_cols - len(cols))
        n_rows = len(rows) + (1 if cols else 0)
        # 열 폭
        weights = tbl.get("col_widths")
        if not (isinstance(weights, list) and len(weights) == n_cols):
            weights = [1.4] + [1.0] * (n_cols - 1) if n_cols > 2 else [1.0] * n_cols
            if st == "table_images":
                weights = [0.55] + [1.0] * (n_cols - 1)
        tot = float(sum(weights))
        col_w = [w * wt / tot for wt in weights]
        size = 13.5 if n_rows <= 6 else (12.5 if n_rows <= 9 else (11.5 if n_rows <= 13 else 10.5))
        head_h = 38.0 if cols else 0.0
        body_h = max(20.0, (h - head_h) / max(1, len(rows)))
        body_h = min(body_h, 72.0 if st not in ("table_images",) else 60.0)
        row_h = ([head_h] if cols else []) + [body_h] * len(rows)
        total_h = sum(row_h)
        t = cv.table(x, y, w, total_h, n_rows, n_cols, col_w, row_h)
        hl_col = tbl.get("highlight_col")
        if hl_col is None and st in ("table_hl",):
            hl_col = n_cols - 1
        if isinstance(hl_col, int) and hl_col < 0:
            hl_col = n_cols + hl_col
        hl_rows = set(tbl.get("highlight_rows") or [])
        if st == "table_totals" and rows:
            hl_rows.add(len(rows) - 1)
        group_rows = set(tbl.get("group_rows") or [])
        matrix = st == "matrix"
        r0 = 0
        if cols:
            for c in range(n_cols):
                fill = "ink" if matrix else (None if st != "table_spec_cols" else None)
                col = "white" if matrix else ("brand_text" if c == hl_col else "gray")
                bold = True
                align = "left" if c == 0 else ("center" if st in ("table_vs", "table_check", "table_spec_cols", "table_lineup", "table_totals", "matrix") else "left")
                if c == hl_col and not matrix:
                    fill = "tint"
                cv.cell(t.cell(0, c), [Run(textfit.clip_chars(header[c], 40), size + 0.5, bold, col)], fill=fill, align=align,
                        borders={"B": ("ink", 2.0)} if not matrix else {})
            r0 = 1
        max_lines = max(1, int(body_h // (size * 1.3)))
        for ri, row in enumerate(rows):
            is_hl = ri in hl_rows
            is_group = ri in group_rows or (isinstance(row, list) and len(row) >= 1 and isinstance(row[0], dict) and row[0].get("group"))
            for c in range(n_cols):
                raw = row[c] if c < len(row) else ""
                txt = cell_text(raw, lang)
                if st == "table_images" and c == 0 and _image_cell(raw):
                    txt = ""
                cw = col_w[c] - 16
                txt = textfit.truncate_to(textfit.Para(txt, size, c == 0), cw, max_lines, 1.0) if txt else ""
                fill = None
                col = "ink2"
                bold = c == 0 and st not in ("table_list",)
                if matrix and c == 0:
                    fill, col, bold = "panel", "ink", True
                if c == hl_col:
                    fill, col, bold = "tint", "brand_text", True
                if is_hl:
                    fill, col, bold = "tint", "brand_text", True
                if is_group:
                    fill, col, bold = "panel", "ink", True
                if isinstance(raw, dict):
                    if raw.get("fill"):
                        fill = raw["fill"]
                    if raw.get("bold"):
                        bold = True
                    if raw.get("color"):
                        col = raw["color"]
                if st == "table_check" and txt in ("●", "◐", "○", "✓", "✕", "O", "X", "△"):
                    col = {"●": "brand_text", "✓": "brand_text", "O": "brand_text", "◐": "mid", "△": "mid"}.get(txt, "gray2")
                align = "left" if c == 0 else ("center" if st in ("table_vs", "table_check", "table_spec_cols", "table_lineup", "table_totals", "matrix") else "left")
                borders = {"B": ("line", 1.0)}
                if matrix:
                    borders = {"B": ("line", 1.0), "R": ("line", 1.0)}
                cv.cell(t.cell(r0 + ri, c), [Run(txt, size, bold, col, number=bool(re.fullmatch(r"[\d,.\s%~+×x\-\[\]]+", txt or "-")))],
                        fill=fill, align=align, anchor="middle" if body_h < 56 else "top", borders=borders)
        if st == "table_images":
            yy = y + head_h
            for ri, row in enumerate(rows):
                ref = _image_cell(row[0] if row else None)
                pad = 4
                if ref:
                    self._image(cv, ctx, ref, "image", x + pad, yy + pad, col_w[0] - 2 * pad, body_h - 2 * pad)
                yy += body_h

    # ── 차트 ─────────────────────────────────────────────
    def _chart(self, cv: Canvas, ctx: Ctx, v: Any, x: float, y: float, w: float, h: float) -> None:
        spec = localize(v, ctx.lang)
        if not isinstance(spec, dict) or not spec.get("series"):
            if self.placeholders:
                self._placeholder(cv, x, y, w, h, "차트 데이터" if ctx.lang != "en" else "Chart data", soft=True)
            return
        spec = dict(spec)
        spec["categories"] = [to_text(c, ctx.lang) for c in spec.get("categories") or spec.get("labels") or []]
        series = []
        for s in spec.get("series") or []:
            if isinstance(s, dict):
                series.append({**s, "name": to_text(s.get("name"), ctx.lang)})
        spec["series"] = series
        cv.chart(spec, x, y, w, h)

    # ── 합성 스타일 ───────────────────────────────────────
    def _items(self, ctx: Ctx, slot: str) -> list[dict[str, Any]]:
        out = []
        for v in as_list(ctx.values.get(slot)):
            v = localize(v, ctx.lang)
            out.append(v if isinstance(v, dict) else {"title": v})
        return out

    @staticmethod
    def _num(v: Any) -> float | None:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def _plot(self, cv: Canvas, ctx: Ctx, box: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
        items = self._items(ctx, box["slot"])
        cv.line(x, y, x, y + h, col="line2", width=2)
        cv.line(x, y + h, x + w, y + h, col="line2", width=2)
        if box["style"] == "plot_quad":
            cv.line(x + w / 2, y, x + w / 2, y + h, col="line2", width=1, dash=True)
            cv.line(x, y + h / 2, x + w, y + h / 2, col="line2", width=1, dash=True)
            quads = [to_text(q, ctx.lang) for q in as_list(ctx.values.get(box.get("quadrants") or "quadrants"))]
            spots = [(x + 10, y + 8, "left"), (x + w / 2 + 10, y + 8, "left"), (x + 10, y + h / 2 + 8, "left"), (x + w / 2 + 10, y + h / 2 + 8, "left")]
            for q, (qx, qy, al) in zip(quads, spots):
                cv.fit_text(qx, qy, w / 2 - 20, 20, [(q, 12.5, True, "gray")], align=al)
        for i, it in enumerate(items):
            px_, py_ = self._num(it.get("x")), self._num(it.get("y"))
            if px_ is None or py_ is None:
                cols = max(1, math.ceil(math.sqrt(len(items))))
                px_, py_ = 15 + (i % cols) * 70 / max(1, cols - 1 or 1), 80 - (i // cols) * 30
            size = self._num(it.get("size"))
            d = 18 if size is None else 18 + max(0.0, min(100.0, size)) * 0.9
            cx, cy = x + w * px_ / 100.0, y + h * (1 - py_ / 100.0)
            hl = bool(it.get("highlight")) or str(it.get("tag") or "").lower() in ("samsung", "삼성", "ours", "고객")
            cv.ellipse(cx - d / 2, cy - d / 2, d, d, fill="brand" if hl else ("ink" if size is None else "soft"), line="white", line_w=2)
            lbl = to_text(it.get("title"), ctx.lang)
            if lbl:
                cv.fit_text(cx + d / 2 + 6, cy - 10, min(200, x + w - cx - d / 2 - 6), 20, [(lbl, 12.5, True, "ink")])

    def _pins(self, cv: Canvas, ctx: Ctx, box: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
        for i, it in enumerate(self._items(ctx, box["slot"])):
            px_, py_ = self._num(it.get("x")), self._num(it.get("y"))
            if px_ is None or py_ is None:
                continue
            d = 34
            cx, cy = x + w * px_ / 100.0, y + h * py_ / 100.0
            no = to_text(it.get("no"), ctx.lang) or str(i + 1)
            cv.ellipse(cx - d / 2, cy - d / 2, d, d, fill="brand", line="white", line_w=3)
            cv.fit_text(cx - d / 2, cy - d / 2, d, d, [(no, 13, True, "on_brand")], align="center", anchor="middle", number_first=True)

    def _emotion(self, cv: Canvas, ctx: Ctx, box: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
        items = self._items(ctx, box["slot"])
        n = len(items) or (ctx.slot_defs.get(box["slot"], {}).get("count") or 5)
        cv.rect(x, y + h / 2, w, 1, fill="line")
        pts = []
        for i, it in enumerate(items):
            e = self._num(it.get("emotion"))
            if e is None:
                continue
            e = max(-2.0, min(2.0, e))
            pts.append((x + (i + 0.5) * w / n, y + h / 2 - e / 2 * (h / 2 - 10)))
        if len(pts) >= 2:
            cv.polygon(pts, fill=None, line="brand", closed=False, width=2.5)
        for px_, py_ in pts:
            cv.ellipse(px_ - 6, py_ - 6, 12, 12, fill="brand", line="white", line_w=2)

    def _swimlane(self, cv: Canvas, ctx: Ctx, v: Any, x: float, y: float, w: float, h: float) -> None:
        tbl = as_table(v, ctx.lang)
        cols, rows = tbl.get("columns") or [], tbl.get("rows") or []
        if not rows:
            if self.placeholders:
                cv.rect(x, y, w, h, fill=None, line="line", radius=12, dash=True)
            return
        n_c = max(len(cols), max(len(r) for r in rows)) - 1
        if n_c <= 0:
            return
        lane_w = 168.0
        head_h = 34.0 if cols else 0.0
        cw = (w - lane_w - 12) / n_c
        if cols:
            cv.fit_text(x, y, lane_w, head_h, [(col_label(cols[0], ctx.lang), 12.5, True, "gray")], anchor="middle")
            for c in range(n_c):
                lbl = col_label(cols[c + 1], ctx.lang) if c + 1 < len(cols) else ""
                cv.fit_text(x + lane_w + 12 + c * cw, y, cw, head_h, [(lbl, 15, True, "ink")], align="center", anchor="middle", number_first=True)
            cv.rect(x + lane_w + 12, y + head_h - 2, w - lane_w - 12, 2, fill="line3")
        lane_h = (h - head_h - 8 * len(rows)) / len(rows)
        for r, row in enumerate(rows):
            ry = y + head_h + 8 + r * (lane_h + 8)
            cv.rect(x, ry, lane_w, lane_h, fill="panel", radius=12)
            cv.fit_text(x + 14, ry + 8, lane_w - 28, lane_h - 16, [(cell_text(row[0], ctx.lang), 15, True, "ink")], anchor="middle")
            for c in range(n_c):
                raw = row[c + 1] if c + 1 < len(row) else None
                if raw in (None, "", {}):
                    continue
                item = raw if isinstance(raw, dict) else {"title": raw}
                cx = x + lane_w + 12 + c * cw + 4
                cv.rect(cx, ry + 6, cw - 8, lane_h - 12, fill="white", line="line3", radius=10)
                tag = to_text(item.get("tag"), ctx.lang)
                paras = []
                if tag:
                    paras.append(textfit.Para(tag, 11, True, 1.2, color="brand_text", shrink=False))
                paras.append(textfit.Para(to_text(item.get("title") or item.get("text"), ctx.lang), 13.5, True, 1.3, space_before=2, color="ink"))
                body = to_text(item.get("body"), ctx.lang)
                if body:
                    paras.append(textfit.Para(body, 11.5, False, 1.35, space_before=3, color="gray"))
                cv.fit_paras(cx + 10, ry + 12, cw - 28, lane_h - 24, paras)

    def _gantt(self, cv: Canvas, ctx: Ctx, box: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
        phases = self._items(ctx, box["slot"])
        periods = [to_text(p, ctx.lang) for p in as_list(ctx.values.get(box.get("periods") or "periods"))]
        miles = self._items(ctx, box.get("milestones") or "milestones")
        lab_w = 230.0
        tx, tw = x + lab_w + 12, w - lab_w - 12
        head_h = 34.0
        if periods:
            pw = tw / len(periods)
            for i, p in enumerate(periods):
                cv.fit_text(tx + i * pw, y, pw, head_h, [(p, 13, True, "gray")], align="center", anchor="middle", number_first=True)
                cv.rect(tx + i * pw, y + head_h, 1, h - head_h, fill="line")
        cv.rect(tx, y + head_h - 2, tw, 2, fill="line3")
        n = max(1, len(phases))
        rh = min(84.0, (h - head_h - 10 - (40 if miles else 0)) / n)
        for i, ph in enumerate(phases):
            ry = y + head_h + 10 + i * rh
            cv.fit_text(x, ry + 4, lab_w, rh - 8, [(to_text(ph.get("title"), ctx.lang), 15, True, "ink"),
                                                   (to_text(ph.get("owner"), ctx.lang), 12, False, "gray")], anchor="middle", gap=2)
            s, e = self._num(ph.get("start")), self._num(ph.get("end"))
            if s is None or e is None:
                s, e = i * 100.0 / n, (i + 1) * 100.0 / n
            s, e = max(0.0, min(100.0, s)), max(0.0, min(100.0, e))
            bx, bw = tx + tw * s / 100.0, max(8.0, tw * (e - s) / 100.0)
            cv.rect(bx, ry + rh * 0.22, bw, rh * 0.56, fill="brand" if i % 2 == 0 else "mid", radius=8)
            body = to_text(ph.get("body"), ctx.lang)
            if body and bw > 80:
                cv.fit_text(bx + 10, ry + rh * 0.22, bw - 20, rh * 0.56, [(body, 12, True, "white")], anchor="middle")
        for m in miles:
            mx = self._num(m.get("x"))
            if mx is None:
                continue
            cx = tx + tw * max(0.0, min(100.0, mx)) / 100.0
            cv.rect(cx - 8, y + h - 34, 16, 16, fill="ink", shape=MSO_SHAPE.DIAMOND)
            cv.fit_text(cx + 12, y + h - 36, 220, 20, [(to_text(m.get("title"), ctx.lang), 12.5, True, "ink")])

    def _region_tiles(self, cv: Canvas, ctx: Ctx, v: Any, x: float, y: float, w: float, h: float) -> None:
        items = self._items(ctx, "regions") if v is not None else []
        if not items:
            return
        cols = 3
        rows_n = math.ceil(len(items) / cols)
        tw, th = (w - 8 * (cols - 1)) / cols, (h - 8 * (rows_n - 1)) / rows_n
        for i, it in enumerate(items):
            r, c = divmod(i, cols)
            tx, ty = x + c * (tw + 8), y + r * (th + 8)
            k = as_kpi(it.get("kpi"), ctx.lang)
            fill = ["brand", "mid", "soft"][min(2, i // max(1, len(items) // 3))]
            cv.rect(tx, ty, tw, th, fill=fill, radius=12)
            col = "white" if fill != "soft" else "ink"
            cv.fit_text(tx + 12, ty + 10, tw - 24, 20, [(to_text(it.get("title"), ctx.lang), 13, True, col)])
            if k:
                self._kpi_runs(cv, k, tx + 12, ty + th - 40, tw - 24, 32, size=22, color=col)

    # ── 장식 ─────────────────────────────────────────────
    def _deco(self, cv: Canvas, st: str, x: float, y: float, w: float, h: float) -> None:
        if st == "panel":
            cv.rect(x, y, w, h, fill="panel", radius=14)
        elif st == "panel_tint":
            cv.rect(x, y, w, h, fill="tint", radius=12)
        elif st == "panel_brand":
            cv.rect(x, y, w, h, fill="brand", radius=0 if (w >= 1279 and h >= 719) else 16)
        elif st == "panel_dark":
            cv.rect(x, y, w, h, fill="ink", radius=14)
        elif st == "panel_dark_alpha":
            cv.rect(x, y, w, h, fill="ink", alpha=0.82)
        elif st == "panel_line":
            cv.rect(x, y, w, h, fill="white", line="line", radius=14)
        elif st == "rule":
            cv.rect(x, y, w, max(1.0, h), fill="line")
        elif st == "rule_brand":
            cv.rect(x, y, w, h, fill="brand")
        elif st in ("connector_h", "connector_v", "track", "track_v"):
            cv.rect(x, y, max(1.0, w), max(1.0, h), fill="line2" if st.startswith("connector") else "line3")
        elif st == "arrow":
            cv.rect(x, y, w, h, fill="brand", shape=MSO_SHAPE.RIGHT_ARROW)
        elif st == "arrow_down":
            cv.rect(x, y, w, h, fill="mid", shape=MSO_SHAPE.DOWN_ARROW)
        elif st in ("chevron", "chevron_small"):
            cv.rect(x, y, w, h, fill="line2", shape=MSO_SHAPE.CHEVRON)
        elif st in ("circle_arrow", "circle_arrow_brand", "circle_arrow_big"):
            brand = st != "circle_arrow"
            cv.ellipse(x, y, w, h, fill="brand" if brand else "white", line="white" if brand else "line2", line_w=2.5 if brand else 1.5)
            cv.rect(x + w * 0.28, y + h * 0.32, w * 0.44, h * 0.36, fill="white" if brand else "ink", shape=MSO_SHAPE.RIGHT_ARROW)
        elif st == "plus":
            cv.fit_text(x, y, w, h, [("+", 30, True, "mid")], align="center", anchor="middle")
        elif st == "marker":
            cv.ellipse(x, y, w, h, fill="brand", line="white", line_w=3)
        elif st == "ring":
            cv.ellipse(x, y, w, h, fill="tint2", line="line", line_w=1.0)
        elif st == "funnel":
            cv.polygon([(x, y), (x + 56, y + 40), (x + w - 56, y + 40), (x + w, y + 80), (x + w, y + h - 80),
                        (x + w - 56, y + h - 40), (x + 56, y + h - 40), (x, y + h)], fill="panel")
        elif st == "fan":
            # 솔루션 2 → 제품 3 → 가치 2 연결(장식)
            sx, ex = x, x + w
            mid = x + w / 2
            for sy in (y + 100, y + 330):
                for py in (y + 64, y + 236, y + 408):
                    cv.line(sx, sy, mid - 80, py, col="soft", width=1.5)
            for py in (y + 64, y + 236, y + 408):
                for vy in (y + 100, y + 330):
                    cv.line(mid + 80, py, ex, vy, col="line2", width=1.5)


FILE_ID = re.compile(r"^[a-z][a-z0-9]{1,7}_[0-9A-Za-z]{8,}$")
NO_MOVE_KEYS = {"file_id", "image", "url", "x", "y", "size", "start", "end", "emotion", "fit", "focus"}


def _move_marks(v: Any, moved: list[str], lang: str, depth: int = 0) -> Any:
    """tbd_mode=notes — 자리표시가 든 글은 「—」 로 바꾸고 원문은 노트로 보낸다(10-proposal §7.12)."""
    if depth > 6:
        return v
    if isinstance(v, str):
        if has_marker(v):
            moved.append(MARKER.sub("", v).strip(" ·,") or v)
            return "—"
        return v
    if isinstance(v, list):
        return [_move_marks(x, moved, lang, depth + 1) for x in v]
    if isinstance(v, dict):
        if ("ko" in v or "en" in v) and set(v) <= {"ko", "en"}:
            txt = to_text(v, lang)
            if has_marker(txt):
                moved.append(MARKER.sub("", txt).strip(" ·,") or txt)
                return "—"
            return v
        return {k: (x if k in NO_MOVE_KEYS else _move_marks(x, moved, lang, depth + 1)) for k, x in v.items()}
    return v


def _filled(v: Any) -> bool:
    return v not in (None, "", [], {})


def _image_cell(raw: Any) -> dict[str, Any] | None:
    """표 칸 값이 그림 참조(file_id)일 때만 참조를 돌려준다(일반 글은 None)."""
    if isinstance(raw, dict) and (raw.get("file_id") or raw.get("image")):
        return image_ref(raw.get("image") or raw)
    if isinstance(raw, str) and FILE_ID.match(raw.strip()):
        return {"file_id": raw.strip()}
    return None


# ── 마스터 ────────────────────────────────────────────────

TEMPLATE_CT = "application/vnd.openxmlformats-officedocument.presentationml.template.main+xml"
PRES_CT = "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"


def open_master(data: bytes) -> Any:
    """.potx 는 콘텐츠 형식을 바꿔 열고, 기존 슬라이드는 지운다(레이아웃 · 마스터만 쓴다)."""
    try:
        zin = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise RenderError("INVALID_MASTER", "마스터 파일이 PPTX/POTX 형식이 아닙니다") from exc
    if "ppt/presentation.xml" not in zin.namelist():
        raise RenderError("INVALID_MASTER", "마스터 파일에 ppt/presentation.xml 이 없습니다")
    ct = zin.read("[Content_Types].xml").decode("utf-8")
    if TEMPLATE_CT in ct:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                buf = zin.read(item.filename)
                if item.filename == "[Content_Types].xml":
                    buf = ct.replace(TEMPLATE_CT, PRES_CT).encode("utf-8")
                zout.writestr(item, buf)
        data = out.getvalue()
    prs = Presentation(io.BytesIO(data))
    sld_ids = prs.slides._sldIdLst
    for sld in list(sld_ids):
        prs.part.drop_rel(sld.rId)
        sld_ids.remove(sld)
    return prs


def pick_layout(prs: Any) -> Any:
    layouts = list(prs.slide_layouts)
    for lay in layouts:
        name = (lay.name or "").lower()
        if "blank" in name or "빈" in name or "empty" in name:
            return lay
    for lay in layouts:
        if len(lay.placeholders) == 0:
            return lay
    return layouts[0]
