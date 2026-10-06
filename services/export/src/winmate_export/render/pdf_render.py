"""PDF 보고서 — reportlab(외부 변환기 없이). 문서 모양은 DOCX 와 같다({title, subtitle?, meta?, sections[...]}).

글꼴: reportlab 내장 CID 글꼴 'HYGothic-Medium'(고딕) · 'HYSMyeongJo-Medium'(명조, font="serif").
CID 글꼴은 파일에 넣지 않는다(뷰어의 한글 글꼴을 쓴다). 사내 PC 에서 글꼴을 넣어야 하면
EXPORT_PDF_TTF(예: NanumGothic.ttf 경로)를 주면 그 TTF 를 넣어 쓴다.
"""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .pptx_render import Assets, DictAssets
from .theme import Theme
from .values import (
    as_bullets,
    as_list,
    as_sources,
    as_table,
    cell_text,
    col_label,
    image_ref,
    label,
    localize,
    split_markers,
    to_text,
)

SANS_CID = "HYGothic-Medium"
SERIF_CID = "HYSMyeongJo-Medium"
PAGES = {"A4": A4, "LETTER": LETTER}


class PdfError(ValueError):
    pass


@lru_cache(maxsize=4)
def _fonts(ttf_path: str | None) -> tuple[str, str]:
    """(본문, 제목) 글꼴 이름."""
    if ttf_path and Path(ttf_path).is_file():
        try:
            pdfmetrics.registerFont(TTFont("WMSans", ttf_path))
            return "WMSans", "WMSans"
        except Exception:  # noqa: BLE001
            pass
    for name in (SANS_CID, SERIF_CID):
        try:
            pdfmetrics.getFont(name)
        except KeyError:
            pdfmetrics.registerFont(UnicodeCIDFont(name))
    return SANS_CID, SANS_CID


def _markup(text: str) -> str:
    """자리표시 강조 + XML 이스케이프 + 줄바꿈."""
    out = []
    for seg, marked in split_markers(text):
        if not seg:
            continue
        s = escape(seg).replace("\n", "<br/>")
        out.append(f'<font backColor="#fff2a8" color="#9a3412"><b>{s}</b></font>' if marked else s)
    return "".join(out)


class _NumberedCanvas(rl_canvas.Canvas):
    """쪽 번호 'n / N' 과 머리글을 마지막에 그린다."""

    header_text = ""
    font_name = SANS_CID

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved)
        for state in self._saved:
            self.__dict__.update(state)
            self._decorate(total)
            super().showPage()
        super().save()

    def _decorate(self, total: int) -> None:
        w, h = self._pagesize
        self.setFont(self.font_name, 8)
        self.setFillColor(colors.HexColor("#8a91a0"))
        self.drawCentredString(w / 2, 10 * mm, f"{self._pageNumber} / {total}")
        if self.header_text:
            self.drawRightString(w - 18 * mm, h - 11 * mm, self.header_text)


def build_pdf(document: dict[str, Any], *, design: dict[str, Any] | None = None, lang: str = "ko",
              assets: Assets | None = None, confidential: bool = False, ttf_path: str | None = None) -> tuple[bytes, list[str]]:
    report = document.get("report") if isinstance(document.get("report"), dict) else document
    sections = report.get("sections")
    if not isinstance(sections, list):
        raise PdfError("report.sections 가 필요합니다")
    theme = Theme.from_design(design)
    assets = assets or DictAssets()
    warnings: list[str] = []
    body_font, head_font = _fonts(ttf_path)
    if str(report.get("font") or document.get("font") or "").lower() == "serif" and body_font == SANS_CID:
        body_font = SERIF_CID
    size_name = str(document.get("page_size") or report.get("page_size") or "A4").upper()
    page = PAGES.get(size_name, A4)
    if str(document.get("orientation") or report.get("orientation") or "").lower() == "landscape":
        page = landscape(page)
    brand_text = colors.HexColor(theme.c("brand_text"))
    st = {
        "title": ParagraphStyle("t", fontName=head_font, fontSize=20, leading=26, textColor=brand_text, spaceAfter=4),
        "subtitle": ParagraphStyle("s", fontName=body_font, fontSize=11.5, leading=16, textColor=colors.HexColor("#596170")),
        "meta": ParagraphStyle("m", fontName=body_font, fontSize=9, leading=13, textColor=colors.HexColor("#8a91a0"), spaceAfter=10),
        "h1": ParagraphStyle("h1", fontName=head_font, fontSize=14, leading=19, textColor=brand_text, spaceBefore=12, spaceAfter=5),
        "h2": ParagraphStyle("h2", fontName=head_font, fontSize=12, leading=16, textColor=colors.HexColor("#121417"), spaceBefore=9, spaceAfter=4),
        "h3": ParagraphStyle("h3", fontName=head_font, fontSize=10.5, leading=14, textColor=colors.HexColor("#121417"), spaceBefore=7, spaceAfter=3),
        "body": ParagraphStyle("b", fontName=body_font, fontSize=10, leading=15, textColor=colors.HexColor("#3d4452"), spaceAfter=4),
        "cell": ParagraphStyle("c", fontName=body_font, fontSize=8.8, leading=12, textColor=colors.HexColor("#121417")),
        "cell_head": ParagraphStyle("ch", fontName=head_font, fontSize=8.8, leading=12,
                                    textColor=colors.white if theme.c("on_brand") == "#ffffff" else colors.HexColor("#121417")),
        "caption": ParagraphStyle("cap", fontName=body_font, fontSize=8.5, leading=11, alignment=TA_CENTER,
                                  textColor=colors.HexColor("#596170"), spaceAfter=6),
        "source": ParagraphStyle("src", fontName=body_font, fontSize=8, leading=11, textColor=colors.HexColor("#8a91a0"), spaceAfter=6),
    }
    title = to_text(report.get("title") or document.get("title"), lang)
    story: list[Any] = []
    if title:
        story.append(Paragraph(_markup(title), st["title"]))
    sub = to_text(report.get("subtitle"), lang)
    if sub:
        story.append(Paragraph(_markup(sub), st["subtitle"]))
    meta = [to_text(m, lang) for m in as_list(report.get("meta"))]
    if any(meta):
        story.append(Paragraph(_markup(" · ".join(m for m in meta if m)), st["meta"]))
    if title or sub:
        story.append(Spacer(1, 6))
    doc_w = page[0] - 36 * mm
    for si, s in enumerate(sections):
        if not isinstance(s, dict):
            raise PdfError(f"sections[{si}] 형식이 잘못되었습니다")
        if s.get("page_break"):
            story.append(PageBreak())
        heading = to_text(s.get("heading") or s.get("title"), lang)
        level = max(1, min(3, int(s.get("level") or 1)))
        block: list[Any] = []
        if heading:
            block.append(Paragraph(_markup(heading), st[f"h{level}"]))
        for para in as_list(localize(s.get("paragraphs"), lang)):
            txt = to_text(para.get("text") if isinstance(para, dict) and "text" in para else para, lang)
            if txt:
                m = _markup(txt)
                if isinstance(para, dict) and para.get("bold"):
                    m = f"<b>{m}</b>"
                block.append(Paragraph(m, st["body"]))
        bl = as_bullets(s.get("bullets"), lang)
        if bl:
            block.append(ListFlowable([ListItem(Paragraph(_markup(b), st["body"]), leftIndent=12) for b in bl],
                                      bulletType="bullet", start="•", leftIndent=12, bulletFontName=body_font))
        nl = as_bullets(s.get("numbered"), lang)
        if nl:
            block.append(ListFlowable([ListItem(Paragraph(_markup(b), st["body"]), leftIndent=14) for b in nl],
                                      bulletType="1", leftIndent=14, bulletFontName=body_font))
        # 제목이 쪽 끝에 홀로 남지 않게 첫 덩어리와 묶는다
        if block:
            story.append(KeepTogether(block[:2]))
            story.extend(block[2:])
        if s.get("table"):
            t = _table(s["table"], lang, theme, st, doc_w)
            if t is not None:
                story.append(t)
                cap = to_text((s["table"] or {}).get("caption") if isinstance(s["table"], dict) else None, lang)
                if cap:
                    story.append(Paragraph(_markup(cap), st["caption"]))
                story.append(Spacer(1, 6))
        captions = as_list(s.get("captions"))
        for ii, img in enumerate(as_list(s.get("images"))):
            ref = image_ref(localize(img, lang))
            if not ref:
                continue
            a = assets.get(ref["file_id"])
            if a is None:
                warnings.append(f"image missing {ref['file_id']}")
                continue
            try:
                pil = PILImage.open(io.BytesIO(a.data))
                iw, ih = pil.size
                if (pil.format or "").upper() not in ("PNG", "JPEG", "GIF") or max(iw, ih) > 2400:
                    pil.thumbnail((2400, 2400))
                    buf = io.BytesIO()
                    pil.convert("RGB").save(buf, "JPEG", quality=88)
                    data = buf.getvalue()
                    iw, ih = pil.size
                else:
                    data = a.data
            except Exception:  # noqa: BLE001
                warnings.append(f"image unreadable {ref['file_id']}")
                continue
            w = min(doc_w, float(ref.get("width_mm") or 0) * mm or doc_w * 0.9)
            h = w * ih / iw
            max_h = page[1] * 0.55
            if h > max_h:
                w, h = w * max_h / h, max_h
            story.append(Image(io.BytesIO(data), width=w, height=h))
            cap = to_text(ref.get("caption") or (captions[ii] if ii < len(captions) else ""), lang)
            if a.ai_generated or ref.get("ai_generated"):
                cap = f"{cap} · {label('ai', lang)}" if cap else label("ai", lang)
            story.append(Paragraph(_markup(cap), st["caption"]) if cap else Spacer(1, 6))
        srcs = as_sources(s.get("sources") or s.get("footnotes"), lang)
        if srcs:
            parts = [f'<link href="{escape(x["url"])}">{escape(x["label"])}</link>' if x.get("url") else escape(x["label"]) for x in srcs]
            story.append(Paragraph(f"{label('source', lang)}: " + " · ".join(parts), st["source"]))
    if not story:
        story.append(Spacer(1, 1))

    header_bits = [title[:60] if title else "", label("confidential", lang) if confidential else ""]

    class _Canvas(_NumberedCanvas):
        header_text = " · ".join(b for b in header_bits if b)
        font_name = body_font

    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=page, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm, title=title or "Winmate", author="Winmate")
    doc.build(story, canvasmaker=_Canvas)
    return out.getvalue(), warnings


def _table(spec: Any, lang: str, theme: Theme, st: dict[str, ParagraphStyle], doc_w: float) -> Table | None:
    tbl = as_table(spec, lang)
    cols, rows = tbl.get("columns") or [], tbl.get("rows") or []
    n_cols = max(len(cols), max((len(r) for r in rows), default=0))
    if n_cols == 0:
        return None
    data: list[list[Any]] = []
    if cols:
        data.append([Paragraph(_markup(col_label(cols[c], lang) if c < len(cols) else ""), st["cell_head"]) for c in range(n_cols)])
    for r in rows:
        data.append([Paragraph(_markup(cell_text(r[c] if c < len(r) else "", lang)), st["cell"]) for c in range(n_cols)])
    weights = tbl.get("col_widths")
    if not (isinstance(weights, list) and len(weights) == n_cols):
        weights = [1.4] + [1.0] * (n_cols - 1) if n_cols > 2 else [1.0] * n_cols
    tot = float(sum(weights))
    t = Table(data, colWidths=[doc_w * w / tot for w in weights], repeatRows=1 if cols else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#d5d9e0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if cols:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(theme.c("brand"))))
    off = 1 if cols else 0
    for ri in tbl.get("highlight_rows") or []:
        if isinstance(ri, int) and 0 <= ri < len(rows):
            style.append(("BACKGROUND", (0, ri + off), (-1, ri + off), colors.HexColor(theme.c("tint"))))
    t.setStyle(TableStyle(style))
    return t
