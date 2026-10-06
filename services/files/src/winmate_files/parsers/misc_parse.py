"""이미지 · SVG · ZIP · HWPX · 그 밖(LibreOffice 변환) 파서."""
from __future__ import annotations

import io
import re
import zipfile
from typing import Any

from lxml import etree

from ..docprops import svg_size, xml
from ..imaging import image_info
from ..textutil import clean
from .common import Doc, ParseContext, ParseError, Unsupported


def parse_image(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    doc = Doc("image", ctx)
    info = image_info(data)
    if not info:
        raise ParseError("PARSE_FAILED", "이미지를 열 수 없어요")
    page = doc.page(1, size=[info.get("width"), info.get("height")] if info.get("width") else None)
    page["blocks"] = [{"type": "image", "text": "", "bbox": [0.0, 0.0, 1.0, 1.0]}]
    doc.meta.update({"width": info.get("width"), "height": info.get("height"), "format": info.get("format"),
                     "frames": info.get("frames")})
    ex = info.get("exif") or {}
    if ex:
        doc.meta["exif"] = ex
        doc.meta["created"] = ex.get("taken_at")
        doc.meta["author"] = ex.get("artist")
    return doc.finish()


def parse_svg(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    doc = Doc("svg", ctx)
    root = xml(data)
    if root is None:
        raise ParseError("PARSE_FAILED", "SVG 를 읽을 수 없어요")
    w, h = svg_size(data)
    title = None
    texts: list[str] = []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        local = etree.QName(el).localname
        if local == "title" and title is None:
            title = clean("".join(el.itertext())) or None
        elif local == "text":
            t = clean(" ".join(x.strip() for x in el.itertext() if x.strip()))
            if t:
                texts.append(t)
    page = doc.page(1, text="\n".join(texts), size=[w, h] if w and h else None)
    blocks: list[dict[str, Any]] = []
    if title:
        blocks.append({"type": "title", "text": title, "level": 1})
    blocks.extend({"type": "body", "text": t} for t in texts[:500])
    blocks.append({"type": "image", "text": "", "bbox": [0.0, 0.0, 1.0, 1.0]})
    page["blocks"] = blocks
    doc.title = title
    doc.meta.update({"width": w, "height": h})
    return doc.finish()


def parse_zip(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    doc = Doc("zip", ctx)
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        infos = zf.infolist()
    except (zipfile.BadZipFile, OSError) as exc:
        raise ParseError("PARSE_FAILED", f"ZIP 을 열 수 없어요: {exc}") from exc
    lines = []
    for info in infos[:2000]:
        name = info.filename
        if info.flag_bits & 0x800 == 0:  # UTF-8 표시가 없으면 cp437 로 읽힌 이름 → cp949 로 다시
            try:
                name = name.encode("cp437").decode("cp949")
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
        if not name.endswith("/"):
            lines.append(f"{name}\t{info.file_size}")
    page = doc.page(1, text="\n".join(lines))
    page["blocks"] = [{"type": "list", "text": "\n".join(lines[:500])}] if lines else []
    doc.meta["entries"] = len(infos)
    if len(infos) > 2000:
        doc.warn("entries_truncated:2000")
    doc.warn("zip_not_extracted")
    return doc.finish()


_HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"


def parse_hwpx(data: bytes, ctx: ParseContext) -> dict[str, Any]:
    """한글(HWPX) — Contents/section*.xml 의 문단 글자(hp:t)만. 표 칸은 문단으로 이어 붙는다."""
    doc = Doc("other", ctx)
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        sections = sorted((n for n in zf.namelist() if re.match(r"Contents/section\d+\.xml$", n)),
                          key=lambda n: int(re.findall(r"\d+", n)[-1]))
    except (zipfile.BadZipFile, OSError) as exc:
        raise ParseError("PARSE_FAILED", f"HWPX 를 열 수 없어요: {exc}") from exc
    blocks: list[dict[str, Any]] = []
    for name in sections:
        root = xml(zf.read(name))
        if root is None:
            continue
        for p in root.iter(f"{{{_HP}}}p"):
            # 안쪽 문단(표 칸)은 따로 돈다 — 바깥 문단은 자기 run 의 글자만
            texts = []
            for run in p.findall(f"{{{_HP}}}run"):
                for t in run.findall(f"{{{_HP}}}t"):
                    texts.append("".join(t.itertext()))
            s = clean("".join(texts))
            if s:
                blocks.append({"type": "body", "text": s})
    page = doc.page(1, text="\n".join(b["text"] for b in blocks))
    page["blocks"] = blocks
    doc.meta["format"] = "hwpx"
    doc.title = blocks[0]["text"][:120] if blocks else None
    return doc.finish()


def parse_converted(data: bytes, ctx: ParseContext, target: str) -> dict[str, Any]:
    """LibreOffice 로 바꾼 뒤 그 형식 파서로 읽는다(.doc .ppt .xls .odt .odp .ods .rtf .hwp)."""
    if ctx.convert is None:
        raise Unsupported(f"{ctx.fmt} 는 LibreOffice 가 있어야 읽을 수 있어요")
    converted = ctx.convert(data, ctx.name, target)
    if not converted:
        raise ParseError("CONVERSION_FAILED", f"{ctx.fmt.upper()} 를 {target.upper()} 로 바꾸지 못했어요")
    from . import parse_kind

    sub = ParseContext(name=ctx.name, fmt=target, extract_children=ctx.extract_children, max_children=ctx.max_children,
                       pdf_layout_max_pages=ctx.pdf_layout_max_pages, src_path=None, convert=None)
    out = parse_kind(target, converted, sub)
    out["kind"] = "other"
    out["meta"]["format"] = ctx.fmt
    out["meta"]["parsed_as"] = target
    out["warnings"] = [f"converted_from:{ctx.fmt}"] + list(out.get("warnings") or [])
    return out
