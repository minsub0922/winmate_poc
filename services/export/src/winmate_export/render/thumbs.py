"""템플릿 썸네일 — 카탈로그 상자(boxes)로 Pillow 와이어프레임을 그린다(기본 120 × 68, ?w= 로 크게).

글은 회색 막대, 이미지는 자리 색 + 산 모양, 수치는 포인트 색 굵은 막대로 줄여 그린다.
작은 크기에서도 모양이 보이도록 3배(큰 크기는 2배)로 그린 뒤 줄인다. 결과는 메모리 LRU 에 둔다.
"""
from __future__ import annotations

import io
import math
from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw

from .pptx_render import CARDS, CELL_FILLS, TEXT_STYLES
from .theme import Theme, rgb

MIN_W, MAX_W, DEFAULT_W = 60, 1280, 120

INK_BAR = "#3d4452"
GRAY_BAR = "#b8bec8"
LIGHT_BAR = "#d5d9e0"
IMG_FILL = "#cfd6e0"
IMG_HILL = "#b3bdcb"
PANEL = "#eef0f3"       # 썸네일은 작아서 캔버스 패널(#f5f6f8)보다 조금 진하게


def thumb_size(w: int | None) -> tuple[int, int]:
    w = DEFAULT_W if not w else max(MIN_W, min(MAX_W, int(w)))
    return w, int(round(w * 9 / 16))


class _Painter:
    def __init__(self, width: int, theme: Theme):
        self.out_w, self.out_h = thumb_size(width)
        self.ss = 3 if self.out_w < 400 else 2
        self.W, self.H = self.out_w * self.ss, self.out_h * self.ss
        self.k = self.W / 1280.0
        self.theme = theme
        self.im = Image.new("RGBA", (self.W, self.H), (255, 255, 255, 255))
        self.d = ImageDraw.Draw(self.im)

    # ── 기본 도형 ────────────────────────────────────
    def c(self, key: str, alpha: int = 255) -> tuple[int, int, int, int]:
        return (*rgb(self.theme.c(key)), alpha)

    def box(self, x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
        k = self.k
        return x * k, y * k, (x + w) * k, (y + h) * k

    def rect(self, x: float, y: float, w: float, h: float, fill: str | None = None, line: str | None = None,
             radius: float = 0, alpha: int = 255, line_w: float = 1.0) -> None:
        if w <= 0 or h <= 0:
            return
        x0, y0, x1, y1 = self.box(x, y, w, h)
        r = max(0.0, min(radius * self.k, (x1 - x0) / 2, (y1 - y0) / 2))
        lw = max(1, int(round(line_w * self.k * 1.5))) if line else 0
        if alpha < 255 and fill:
            layer = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).rounded_rectangle((x0, y0, x1, y1), radius=r, fill=self.c(fill, alpha))
            self.im.alpha_composite(layer)
            self.d = ImageDraw.Draw(self.im)
            return
        self.d.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=self.c(fill) if fill else None,
                                 outline=self.c(line) if line else None, width=lw)

    def ellipse(self, x: float, y: float, w: float, h: float, fill: str | None = None, line: str | None = None) -> None:
        x0, y0, x1, y1 = self.box(x, y, w, h)
        self.d.ellipse((x0, y0, x1, y1), fill=self.c(fill) if fill else None, outline=self.c(line) if line else None,
                       width=max(1, int(self.k * 1.5)) if line else 0)

    def poly(self, pts: list[tuple[float, float]], fill: str) -> None:
        self.d.polygon([(px * self.k, py * self.k) for px, py in pts], fill=self.c(fill))

    def line(self, pts: list[tuple[float, float]], col: str, width: float = 1.5) -> None:
        self.d.line([(px * self.k, py * self.k) for px, py in pts], fill=self.c(col), width=max(1, int(round(width * self.k * 1.5))))

    def bars(self, x: float, y: float, w: float, h: float, *, size: float, line: float = 1.3, col: str = GRAY_BAR,
             max_lines: int = 3, widths: tuple[float, ...] = (0.92, 0.7, 0.5), align: str = "left") -> None:
        """글줄을 막대로."""
        lh = size * line
        n = max(1, min(max_lines, int(h // lh) if lh > 0 else 1))
        th = max(size * 0.5, 2.2 / self.k)
        for i in range(n):
            bw = w * widths[min(i, len(widths) - 1)]
            bx = x if align == "left" else (x + (w - bw) / 2 if align == "center" else x + w - bw)
            by = y + i * lh + (lh - th) / 2
            if by + th > y + h + 0.5 and i:
                break
            self.rect(bx, by, bw, th, fill=col, radius=th / 2)

    def image(self, x: float, y: float, w: float, h: float, radius: float = 10) -> None:
        self.rect(x, y, w, h, fill=IMG_FILL, radius=radius)
        if w > 30 and h > 30:
            # 산 두 개 + 해
            base = y + h
            self.poly([(x + w * 0.08, base - h * 0.12), (x + w * 0.38, y + h * 0.42), (x + w * 0.62, base - h * 0.12)], IMG_HILL)
            self.poly([(x + w * 0.42, base - h * 0.12), (x + w * 0.66, y + h * 0.56), (x + w * 0.92, base - h * 0.12)], IMG_HILL)
            d = min(w, h) * 0.14
            self.ellipse(x + w * 0.72, y + h * 0.18, d, d, fill=IMG_HILL)

    def png(self) -> bytes:
        out = self.im.convert("RGB").resize((self.out_w, self.out_h), Image.LANCZOS)
        buf = io.BytesIO()
        out.save(buf, "PNG", optimize=True)
        return buf.getvalue()


def _fields(t: dict[str, Any], slot: str) -> set[str]:
    sd = next((s for s in t["slots"] if s["key"] == slot), None) or {}
    return {f["key"] for f in sd.get("fields", [])}


def _slot_type(t: dict[str, Any], slot: str) -> str:
    sd = next((s for s in t["slots"] if s["key"] == slot), None) or {}
    return sd.get("type", "text")


def _draw_deco(p: _Painter, st: str, x: float, y: float, w: float, h: float) -> None:
    if st == "panel":
        p.rect(x, y, w, h, fill=PANEL, radius=14)
    elif st == "panel_tint":
        p.rect(x, y, w, h, fill="tint", radius=12)
    elif st == "panel_brand":
        p.rect(x, y, w, h, fill="brand", radius=0 if (w >= 1279 and h >= 719) else 16)
    elif st == "panel_dark":
        p.rect(x, y, w, h, fill="ink", radius=14)
    elif st == "panel_dark_alpha":
        p.rect(x, y, w, h, fill="ink", alpha=205)
    elif st == "panel_line":
        p.rect(x, y, w, h, fill="white", line="line2", radius=14)
    elif st in ("rule", "connector_h", "connector_v", "track", "track_v"):
        p.rect(x, y, max(w, 2), max(h, 2), fill=LIGHT_BAR)
    elif st == "rule_brand":
        p.rect(x, y, w, max(h, 3), fill="brand")
    elif st in ("arrow", "chevron", "chevron_small"):
        col = "brand" if st == "arrow" else GRAY_BAR
        p.poly([(x, y + h * 0.2), (x + w * 0.55, y + h * 0.2), (x + w * 0.55, y), (x + w, y + h / 2),
                (x + w * 0.55, y + h), (x + w * 0.55, y + h * 0.8), (x, y + h * 0.8)], col)
    elif st == "arrow_down":
        p.poly([(x, y), (x + w, y), (x + w / 2, y + h)], "mid")
    elif st.startswith("circle_arrow"):
        p.ellipse(x, y, w, h, fill="brand" if st != "circle_arrow" else "white", line=None if st != "circle_arrow" else "line2")
    elif st == "marker":
        p.ellipse(x, y, w, h, fill="brand")
    elif st == "ring":
        p.ellipse(x, y, w, h, fill="tint2", line="line")
    elif st == "plus":
        p.rect(x + w * 0.3, y + h * 0.47, w * 0.4, h * 0.06 + 2, fill="mid")
        p.rect(x + w * 0.47, y + h * 0.3, w * 0.06 + 2, h * 0.4, fill="mid")
    elif st == "funnel":
        p.poly([(x, y), (x + w, y + 80), (x + w, y + h - 80), (x, y + h)], PANEL)
    elif st == "fan":
        for sy in (y + 100, y + 330):
            for py in (y + 64, y + 236, y + 408):
                p.line([(x, sy), (x + w / 2 - 80, py)], "soft", 1.5)


def _draw_card(p: _Painter, t: dict[str, Any], box: dict[str, Any], x: float, y: float, w: float, h: float) -> None:
    st = box["style"]
    spec = CARDS.get(st, CARDS["card"])
    fields = _fields(t, box["slot"])
    fill = PANEL if spec.fill == "panel" else spec.fill
    if st == "circle_card_brand":
        p.ellipse(x, y, w, h, fill="brand")
    elif fill or spec.line:
        p.rect(x, y, w, h, fill=fill, line=spec.line, radius=spec.radius)
    inv = spec.inv
    pad = spec.pad
    ix, iy, iw, ih = x + pad, y + pad, w - 2 * pad, h - 2 * pad
    if st in ("contact", "contact_row", "legend_row", "toc_row"):
        ix, iy, iw, ih = x, y, w, h
    if ih <= 4 or iw <= 4:
        return
    if spec.image == "top" and "image" in fields:
        ihh = ih * spec.image_frac
        p.image(ix, iy, iw, ihh, radius=8)
        iy += ihh + 10
        ih -= ihh + 10
    elif spec.image == "left" and "image" in fields:
        iww = min(ih * 1.15, iw * 0.4)
        p.image(ix, iy, iww, ih, radius=8)
        ix += iww + 14
        iw -= iww + 14
    if spec.layout == "row" and spec.badge:
        dd = min(28.0, ih * 0.8)
        p.ellipse(ix, iy + (ih - dd) / 2 if st in ("card_space_row", "legend_row") else iy, dd, dd, fill="brand")
        ix += dd + 10
        iw -= dd + 10
    if st == "toc_row":
        p.rect(ix, iy + ih * 0.25, 40, ih * 0.5, fill="brand", radius=4)
        ix += 70
        iw -= 70
    title_col = "white" if inv else INK_BAR
    body_col = "on_brand_sub" if inv else GRAY_BAR
    kpi_h = 0.0
    if "kpi" in fields and spec.layout != "row" and ih > 60:
        kpi_h = min(ih * 0.3, spec.kpi_size * 0.9)
        p.rect(ix, iy + ih - kpi_h, min(iw * 0.4, kpi_h * 2.2), kpi_h * 0.7, fill="white" if inv else "brand", radius=3)
        ih -= kpi_h + 8
    if ih <= 4:
        return
    p.bars(ix, iy, iw * (0.75 if spec.layout == "row" and "kpi" in fields else 1.0), min(ih, spec.title * 1.3 * 2),
           size=spec.title, col=title_col, max_lines=1 if ih < spec.title * 3 else 2, widths=(0.85, 0.55))
    used = min(ih, spec.title * 1.3 * (1 if ih < spec.title * 3 else 2)) + 6
    if ih - used > spec.body * 1.4 and ("body" in fields or "bullets" in fields):
        p.bars(ix, iy + used, iw, ih - used, size=spec.body * 0.9, col=body_col, max_lines=4, widths=(0.95, 0.9, 0.8, 0.55))
    if spec.layout == "row" and "kpi" in fields:
        p.rect(ix + iw * 0.8, iy + ih * 0.3, iw * 0.18, ih * 0.4, fill="brand", radius=3)


def _draw_slot(p: _Painter, t: dict[str, Any], box: dict[str, Any]) -> None:
    x, y, w, h = box["x"] * 1280, box["y"] * 720, box["w"] * 1280, box["h"] * 720
    st = box["style"]
    slot = box["slot"]
    stype = _slot_type(t, slot)
    if "part" in box:
        stype = "text"
    if st in ("hidden",):
        return
    if slot == "sources" or st == "source":
        p.bars(x, y, min(w, 260), h, size=9, col=LIGHT_BAR, max_lines=1, widths=(1.0,))
        return
    if st in ("logo", "logo_plate") or stype == "logo":
        p.rect(x, y + h * 0.15, w * 0.8, h * 0.7, fill=INK_BAR, radius=2)
        return
    if st in ("plot", "plot_quad"):
        p.rect(x, y, 3, h, fill=GRAY_BAR)
        p.rect(x, y + h - 3, w, 3, fill=GRAY_BAR)
        if st == "plot_quad":
            p.rect(x + w / 2, y, 2, h, fill=LIGHT_BAR)
            p.rect(x, y + h / 2, w, 2, fill=LIGHT_BAR)
        for i, (px, py, d) in enumerate(((0.25, 0.6, 40), (0.5, 0.35, 56), (0.72, 0.5, 30), (0.4, 0.75, 24))):
            p.ellipse(x + w * px, y + h * py, d, d, fill="brand" if i == 1 else "soft")
        return
    if st == "pins":
        for px, py in ((0.25, 0.3), (0.6, 0.45), (0.4, 0.7)):
            p.ellipse(x + w * px - 14, y + h * py - 14, 28, 28, fill="brand", line="white")
        return
    if st == "emotion_curve":
        pts = [(x + w * (i + 0.5) / 5, y + h * (0.5 - 0.35 * math.sin(i * 1.3))) for i in range(5)]
        p.line(pts, "brand", 3)
        return
    if st == "swimlane":
        lanes = 3
        lh = h / lanes
        for i in range(lanes):
            p.rect(x, y + i * lh + 4, 150, lh - 8, fill=PANEL, radius=10)
            for j in range(4):
                p.rect(x + 170 + j * (w - 170) / 4, y + i * lh + 10, (w - 170) / 4 - 12, lh - 20, fill="white", line="line2", radius=8)
        return
    if st == "gantt":
        for i in range(4):
            p.bars(x, y + 40 + i * (h - 50) / 4, 200, 20, size=14, col=INK_BAR, max_lines=1, widths=(0.8,))
            p.rect(x + 230 + i * (w - 230) * 0.2, y + 40 + i * (h - 50) / 4, (w - 230) * 0.35, 30,
                   fill="brand" if i % 2 == 0 else "mid", radius=6)
        return
    if st == "region_tiles":
        for i in range(6):
            r, c = divmod(i, 3)
            p.rect(x + c * w / 3 + 4, y + r * h / 2 + 4, w / 3 - 8, h / 2 - 8, fill=["brand", "mid", "soft"][min(2, i // 2)], radius=10)
        return
    if stype == "card" and "part" not in box:
        _draw_card(p, t, box, x, y, w, h)
        return
    if st.startswith("image") or stype == "image":
        if st == "image_contain_soft":
            p.rect(x, y, w, h, fill=PANEL, radius=14)
            p.image(x + w * 0.15, y + h * 0.15, w * 0.7, h * 0.7, radius=6)
        else:
            p.image(x, y, w, h, radius=0 if st in ("image_full",) else 10)
        return
    if st.startswith("kpi") or stype == "kpi":
        if st == "kpi_circle":
            i = box.get("index", 0)
            p.ellipse(x, y, w, h, fill=["tint2", "tint", "brand"][min(i, 2)], line="soft" if i < 2 else None)
            return
        if st in ("kpi_card", "kpi_tile_line", "kpi_tile", "kpi_cell", "kpi_brand", "kpi_cell_brand", "kpi_big_card"):
            p.rect(x, y, w, h, fill={"kpi_brand": "brand", "kpi_cell_brand": "tint", "kpi_tile": "white",
                                     "kpi_tile_line": "white"}.get(st, PANEL),
                   line="line2" if st == "kpi_tile_line" else None, radius=12)
        inv = st in ("kpi_brand", "kpi_inv")
        nh = min(h * 0.42, 40)
        nx = x + (w * 0.08 if st not in ("kpi", "kpi_inline", "kpi_big", "kpi_bar", "kpi_bar_brand") else 0)
        p.rect(nx, y + h - nh - h * 0.18, min(w * 0.5, nh * 2.4), nh, fill="white" if inv else "brand", radius=4)
        if st in ("kpi_bar", "kpi_bar_brand"):
            p.rect(x, y + h - 10, w, 6, fill=LIGHT_BAR, radius=3)
            p.rect(x, y + h - 10, w * 0.6, 6, fill="brand" if st == "kpi_bar_brand" else GRAY_BAR, radius=3)
        return
    if st.startswith("table") or st == "matrix" or stype == "table":
        rows = 5
        p.rect(x, y, w, max(4.0, h * 0.08), fill="ink" if st == "matrix" else INK_BAR)
        rh = (h - h * 0.08) / rows
        for i in range(1, rows + 1):
            p.rect(x, y + h * 0.08 + i * rh - 1, w, 2, fill=LIGHT_BAR)
        for cpos in (0.3, 0.55, 0.78):
            p.bars(x + w * cpos, y + h * 0.08 + rh * 0.3, w * 0.15, rh * 0.5, size=9, col=GRAY_BAR, max_lines=1, widths=(1.0,))
        if st in ("table_hl",):
            p.rect(x + w * 0.78, y, w * 0.22, h, fill="tint", alpha=160)
        return
    if st == "chart" or stype == "chart":
        p.rect(x, y, w, h, fill=PANEL, radius=12)
        n = 5
        bw = w * 0.6 / n
        for i in range(n):
            bh = h * (0.25 + 0.12 * i)
            p.rect(x + w * 0.12 + i * (bw + w * 0.3 / n), y + h * 0.88 - bh, bw, bh, fill="brand" if i == n - 1 else GRAY_BAR, radius=2)
        return
    if st in ("chips", "chips_inv", "chips_white", "chips_right") or (stype == "bullets" and st.startswith("chips")):
        cw = min(110.0, w / 3.2)
        n = max(1, min(4, int(w // (cw + 8))))
        sx = x + w - n * (cw + 8) if st == "chips_right" else x
        for i in range(n):
            p.rect(sx + i * (cw + 8), y, cw, min(h, 28), fill="white" if st != "chips_right" else PANEL,
                   line="line2" if st == "chips" else None, radius=min(h, 28) / 2)
        return
    if stype == "bullets" or st in ("bullets", "list", "list_inv"):
        p.bars(x, y, w, h, size=15, line=1.6, col="white" if st.endswith("_inv") else GRAY_BAR, max_lines=6,
               widths=(0.9, 0.82, 0.88, 0.7, 0.8, 0.6))
        return
    if st in CELL_FILLS:
        fill, line = CELL_FILLS[st]
        fill = PANEL if fill == "panel" else fill
        if fill or line:
            p.rect(x, y, w, h, fill=fill, line=line, radius=10)
        pad = 14 if (fill or line) else 2
        p.bars(x + pad, y + pad * 0.7, w - 2 * pad, h - pad * 1.4, size=14, col=INK_BAR if st in ("cell_head", "cell_strong", "cell_tint_strong") else GRAY_BAR,
               max_lines=2)
        return
    if st in ("chip_brand", "chip_dark", "pill_gray", "pill_brand", "pill_brand_left", "pill_tint", "label_chip"):
        fill = {"chip_brand": "brand", "pill_brand": "brand", "pill_brand_left": "brand", "chip_dark": "ink",
                "pill_tint": "tint", "pill_gray": LIGHT_BAR, "label_chip": "white"}[st]
        pw = w if st == "pill_brand" else min(w, max(h * 3, 120))
        p.rect(x, y, pw, h, fill=fill, line="line2" if st == "label_chip" else None, radius=h / 2)
        return
    if st == "circle_brand":
        p.ellipse(x, y, w, h, fill="brand")
        return
    if st == "axis_v":
        p.rect(x, y, w, h, line="line2", radius=10)
        return
    if st == "swatch":
        p.rect(x, y, h, h, fill="brand", radius=3)
        p.bars(x + h + 6, y, w - h - 6, h, size=12, col=GRAY_BAR, max_lines=1)
        return
    spec = TEXT_STYLES.get(st, TEXT_STYLES["body"])
    size = float(spec["size"])
    col_key = spec["color"]
    if st.startswith("divider_no"):
        p.rect(x, y + h * 0.1, min(w, size * 1.3), h * 0.8, fill="on_brand_sub" if st == "divider_no" else ("brand" if st == "divider_no_brand" else "white"), radius=6)
        return
    if col_key in ("white", "on_brand_sub"):
        col = "white" if col_key == "white" else "on_brand_sub"
    elif col_key in ("eyebrow", "brand_text"):
        col = "brand"
    elif spec.get("bold") and size >= 16:
        col = INK_BAR
    else:
        col = GRAY_BAR
    if st in ("eyebrow", "eyebrow_inv"):
        p.bars(x, y, w * 0.35, h, size=size, col=col, max_lines=1, widths=(1.0,))
        return
    if st == "footer":
        p.bars(x, y, w * 0.4, h, size=size, col=LIGHT_BAR, max_lines=1, widths=(1.0,))
        return
    p.bars(x, y, w, h, size=size, line=spec.get("line", 1.3), col=col, max_lines=4 if size < 20 else 3,
           align=box.get("align", "left"))


def render_thumbnail(t: dict[str, Any], width: int | None = DEFAULT_W, design: dict[str, Any] | None = None) -> bytes:
    p = _Painter(width or DEFAULT_W, Theme.from_design(design or {}))
    for box in t["boxes"]:
        x, y, w, h = box["x"] * 1280, box["y"] * 720, box["w"] * 1280, box["h"] * 720
        if box.get("slot") is None:
            _draw_deco(p, box["style"], x, y, w, h)
        else:
            _draw_slot(p, t, box)
    if any(b.get("slot") == "footer" for b in t["boxes"]):
        p.rect(64, 667, 1152, 2, fill=LIGHT_BAR)
    return p.png()


@lru_cache(maxsize=2048)
def cached_thumbnail(code: str, width: int, version: str, brand: str = "") -> bytes:
    from ..templates.catalog import catalog

    t = catalog().get(code)
    if t is None:
        raise KeyError(code)
    return render_thumbnail(t, width, {"brand_hex": brand} if brand else None)
