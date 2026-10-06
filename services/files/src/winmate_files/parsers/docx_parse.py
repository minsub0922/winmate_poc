"""DOCX(.dotx · .docm 포함) — 문단(제목 수준 · 목록 · 캡션) · 표(병합 칸) · 글상자 · 그림.

쪽 나누기: 명시적 쪽 나눔(w:br type=page · pageBreakBefore · 구역 나눔)과 Word 가 마지막으로 그린 쪽 경계
(w:lastRenderedPageBreak)를 따라 pages 를 나눈다. 둘 다 없으면 1쪽. 쪽 번호는 Word 화면과 대략 맞는다.
"""
from __future__ import annotations

import io
import logging
import re
from typing import Any

from docx import Document
from lxml import etree

from ..textutil import clean, is_bullet, is_caption
from .common import Doc, ParseContext, ParseError, table_text
from .ooxml import SKIP_IMAGE_TYPES, as_main_package, image_ext, props

log = logging.getLogger("winmate.files.docx")

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {
    "w": W,
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "v": "urn:schemas-microsoft-com:vml",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
}


def q(tag: str) -> str:
    pre, local = tag.split(":")
    return f"{{{NS[pre]}}}{local}"


_HEADING = re.compile(r"^(?:heading|제목)\s*(\d)$", re.I)
_SKIP_CONTAINERS = {q("w:del"), q("w:moveFrom"), q("mc:Fallback"), q("w:rPr"), q("w:pPr"), q("w:instrText"),
                    q("w:delText"), q("w:fldData")}


def _open(data: bytes) -> Any:
    try:
        return Document(io.BytesIO(data))
    except ValueError:
        return Document(io.BytesIO(as_main_package(data, "docx")))


class _Styles:
    def __init__(self, d: Any):
        self.info: dict[str, tuple[str, int | None, bool]] = {}  # id → (이름, 개요 수준, 번호 매기기)
        try:
            styles = list(d.styles)
        except Exception:  # noqa: BLE001
            styles = []
        raw: dict[str, tuple[str, int | None, bool, str | None]] = {}
        for s in styles:
            try:
                el = s.element
                sid = el.get(q("w:styleId"))
                name = s.name or ""
                ppr = el.find("w:pPr", NS)
                lvl = None
                num = False
                if ppr is not None:
                    ol = ppr.find("w:outlineLvl", NS)
                    if ol is not None and ol.get(q("w:val"), "").isdigit():
                        lvl = int(ol.get(q("w:val")))
                    num = ppr.find("w:numPr", NS) is not None
                based = el.find("w:basedOn", NS)
                raw[sid] = (name, lvl, num, based.get(q("w:val")) if based is not None else None)
            except Exception:  # noqa: BLE001
                continue
        for sid, (name, lvl, num, based) in raw.items():
            seen = 0
            b = based
            while (lvl is None or not num) and b and b in raw and seen < 5:
                _, blvl, bnum, b2 = raw[b]
                lvl = lvl if lvl is not None else blvl
                num = num or bnum
                b = b2
                seen += 1
            self.info[sid] = (name, lvl, num)

    def get(self, sid: str | None) -> tuple[str, int | None, bool]:
        if not sid:
            return ("", None, False)
        return self.info.get(sid, (sid, None, False))


class _Walker:
    def __init__(self, d: Any, doc: Doc):
        self.d = d
        self.doc = doc
        self.styles = _Styles(d)
        self.page = doc.page(1)
        self.page_has_content = False
        self.skipped_vector = 0
        self.level_sizes: list[float] = []

    # ── 쪽 ─────────────────────────────────────────────
    def new_page(self) -> None:
        if not self.page_has_content:
            return
        self.page = self.doc.page(len(self.doc.pages) + 1)
        self.page_has_content = False

    def add_block(self, block: dict[str, Any]) -> None:
        self.page["blocks"].append(block)
        self.page_has_content = True

    # ── 그림 ───────────────────────────────────────────
    def image(self, rid: str, alt: str) -> None:
        try:
            part = self.d.part.related_parts[rid]
        except (KeyError, AttributeError):
            return
        ct = getattr(part, "content_type", "") or ""
        if not ct.startswith("image/"):
            return
        if ct in SKIP_IMAGE_TYPES:
            self.skipped_vector += 1
            return
        no = self.page["no"]
        name = f"p{no}_image{len(self.page['image_refs']) + 1}.{image_ext(ct, str(part.partname))}"
        ref = self.doc.add_child(part.blob, name, ct, {"from": "docx", "alt": alt or None}, page=no)
        blk: dict[str, Any] = {"type": "image", "text": alt}
        if ref:
            blk["ref"] = ref
            self.page["image_refs"].append(ref)
            self.page["images"].append({"ref": ref, "bbox": None})
        self.add_block(blk)

    # ── 문단 ───────────────────────────────────────────
    def paragraph(self, p: etree._Element) -> None:
        ppr = p.find("w:pPr", NS)
        style_id = None
        own_lvl = None
        has_num = False
        sect_break = False
        if ppr is not None:
            ps = ppr.find("w:pStyle", NS)
            style_id = ps.get(q("w:val")) if ps is not None else None
            ol = ppr.find("w:outlineLvl", NS)
            if ol is not None and (ol.get(q("w:val")) or "").isdigit():
                own_lvl = int(ol.get(q("w:val")))
            has_num = ppr.find("w:numPr", NS) is not None
            if ppr.find("w:pageBreakBefore", NS) is not None:
                self.new_page()
            sp = ppr.find("w:sectPr", NS)
            if sp is not None:
                t = sp.find("w:type", NS)
                kind = t.get(q("w:val")) if t is not None else "nextPage"
                sect_break = kind in ("nextPage", "oddPage", "evenPage")
        name, style_lvl, style_num = self.styles.get(style_id)
        parts: list[str] = []
        sizes: list[float] = []
        deferred: list[etree._Element] = []  # 글상자 문단

        def flush_segment() -> None:
            text = clean("".join(parts))
            parts.clear()
            if text:
                self.emit(text, name, own_lvl if own_lvl is not None else style_lvl, has_num or style_num, sizes)

        def walk(el: etree._Element) -> None:
            for ch in el:
                tag = ch.tag
                if not isinstance(tag, str) or tag in _SKIP_CONTAINERS:
                    continue
                if tag == q("w:t"):
                    parts.append(ch.text or "")
                elif tag == q("w:tab"):
                    parts.append("\t")
                elif tag in (q("w:br"), q("w:cr")):
                    if ch.get(q("w:type")) == "page":
                        flush_segment()
                        self.new_page()
                    else:
                        parts.append("\n")
                elif tag == q("w:lastRenderedPageBreak"):
                    flush_segment()
                    self.new_page()
                elif tag == q("w:noBreakHyphen"):
                    parts.append("-")
                elif tag == q("w:r"):
                    rpr = ch.find("w:rPr/w:sz", NS)
                    if rpr is not None and (rpr.get(q("w:val")) or "").isdigit():
                        sizes.append(int(rpr.get(q("w:val"))) / 2)
                    walk(ch)
                elif tag in (q("w:drawing"), q("w:pict"), q("w:object")):
                    for tx in ch.iter(q("w:txbxContent")):
                        deferred.append(tx)
                    alt = ""
                    for dp in ch.iter(q("wp:docPr")):
                        alt = clean(dp.get("descr") or "")[:300]
                        break
                    rids = [b.get(q("r:embed")) for b in ch.iter(q("a:blip")) if b.get(q("r:embed"))]
                    rids += [v.get(q("r:id")) for v in ch.iter(q("v:imagedata")) if v.get(q("r:id"))]
                    for rid in dict.fromkeys(rids):
                        flush_segment()
                        self.image(rid, alt)
                elif tag == q("mc:AlternateContent"):
                    choice = ch.find("mc:Choice", NS)
                    if choice is not None:
                        walk(choice)
                elif tag == q("w:footnoteReference") or tag == q("w:endnoteReference"):
                    continue
                else:
                    walk(ch)  # w:hyperlink · w:ins · w:smartTag · w:fldSimple · w:sdt · w:sdtContent …

        walk(p)
        flush_segment()
        for tx in deferred:
            for inner in tx:
                self.element(inner)
        if sect_break:
            self.new_page()

    def emit(self, text: str, style: str, outline: int | None, numbered: bool, sizes: list[float]) -> None:
        sname = (style or "").strip()
        low = sname.lower()
        block: dict[str, Any] = {"type": "body", "text": text}
        m = _HEADING.match(sname)
        if low in ("title", "제목") or low == "표제":
            block["type"] = "title"
            block["level"] = 1
        elif low in ("subtitle", "부제"):
            block["type"] = "heading"
        elif m:
            block["type"] = "heading"
            block["level"] = int(m.group(1))
        elif outline is not None and outline < 9:
            block["type"] = "heading"
            block["level"] = outline + 1
        elif low in ("caption", "캡션") or (is_caption(text) and len(text) <= 120):
            block["type"] = "caption"
        elif numbered or low.startswith("list") or low.startswith("목록") or is_bullet(text):
            block["type"] = "list"
        elif low in ("footnote text", "endnote text", "각주 텍스트", "미주 텍스트"):
            block["type"] = "note"
        if sizes:
            block["font_size"] = max(sizes)
        self.add_block(block)
        if block["type"] in ("title", "heading") and not self.page.get("title"):
            self.page["title"] = text[:200]

    # ── 표 ─────────────────────────────────────────────
    def table(self, tbl: etree._Element) -> None:
        rows: list[list[str]] = []
        for tr in tbl.findall("w:tr", NS):
            row: list[str] = []
            for tc in tr.findall("w:tc", NS):
                tcpr = tc.find("w:tcPr", NS)
                span = 1
                cont = False
                if tcpr is not None:
                    gs = tcpr.find("w:gridSpan", NS)
                    if gs is not None and (gs.get(q("w:val")) or "").isdigit():
                        span = max(1, int(gs.get(q("w:val"))))
                    vm = tcpr.find("w:vMerge", NS)
                    if vm is not None and vm.get(q("w:val")) in (None, "continue"):
                        cont = True
                text = "" if cont else " ".join(clean("\n".join(self._cell_text(tc))).split())
                row.append(text)
                row.extend([""] * (span - 1))
                # 칸 안 그림
                if not cont:
                    for b in tc.iter(q("a:blip")):
                        rid = b.get(q("r:embed"))
                        if rid:
                            self.image(rid, "")
            if any(row):
                rows.append(row)
        if rows:
            self.page["tables"].append(rows)
            self.add_block({"type": "table", "text": table_text(rows)})

    def _cell_text(self, el: etree._Element) -> list[str]:
        out = []
        for p in el.iter(q("w:p")):
            # 중첩 글상자 · 바뀐 내용 제외: 단순 글자만
            texts = []
            for t in p.iter(q("w:t"), q("w:tab"), q("w:br")):
                anc = t.getparent()
                skip = False
                while anc is not None and anc is not p:
                    if anc.tag in (q("w:del"), q("mc:Fallback")):
                        skip = True
                        break
                    anc = anc.getparent()
                if skip:
                    continue
                if t.tag == q("w:t"):
                    texts.append(t.text or "")
                else:
                    texts.append(" ")
            s = "".join(texts).strip()
            if s:
                out.append(s)
        return out

    # ── 본문 순회 ───────────────────────────────────────
    def element(self, el: etree._Element) -> None:
        tag = el.tag
        if tag == q("w:p"):
            self.paragraph(el)
        elif tag == q("w:tbl"):
            self.table(el)
        elif tag in (q("w:sdt"),):
            content = el.find("w:sdtContent", NS)
            if content is not None:
                for ch in content:
                    self.element(ch)
        elif tag in (q("w:customXml"), q("w:ins")):
            for ch in el:
                self.element(ch)


def parse_docx(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    doc = Doc("docx", ctx)
    try:
        d = _open(data)
    except Exception as exc:  # noqa: BLE001
        raise ParseError("PARSE_FAILED", f"DOCX 를 열 수 없어요: {exc}") from exc
    p = props(data)
    doc.meta.update({k: v for k, v in p.items() if v})
    walker = _Walker(d, doc)
    body = d.element.body
    for el in body:
        try:
            walker.element(el)
        except Exception as exc:  # noqa: BLE001
            doc.warn("element_error")
            log.info("docx element failed: %s", exc)
    # 빈 마지막 쪽 정리
    if len(doc.pages) > 1 and not doc.pages[-1]["blocks"]:
        doc.pages.pop()
    for page in doc.pages:
        page["text"] = "\n".join(b["text"] for b in page["blocks"] if b["text"] and b["type"] != "image")
    if walker.skipped_vector:
        doc.warn(f"vector_images_skipped:{walker.skipped_vector}")
    first_title = None
    for page in doc.pages:
        for b in page["blocks"]:
            if b["type"] == "title" or (b["type"] == "heading" and b.get("level") == 1):
                first_title = b["text"]
                break
        if first_title:
            break
    doc.title = doc.meta.get("title") or first_title
    return doc.finish()
