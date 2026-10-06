"""올릴 때 바로 채우는 메타(쪽 수 · 가로세로 · 문서 속성). 무거운 파싱은 하지 않는다."""
from __future__ import annotations

import io
import logging
import re
import zipfile
from datetime import datetime, timezone
from typing import Any

from lxml import etree

from . import pdfium
from .detect import Detected
from .imaging import image_info
from .textutil import decode_text

log = logging.getLogger("winmate.files.props")

NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
}
_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False, recover=True)


def xml(data: bytes) -> etree._Element | None:
    try:
        return etree.fromstring(data, _PARSER)
    except (etree.XMLSyntaxError, ValueError):
        return None


def w3c_date(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(v, fmt)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return None


def _text(root: etree._Element | None, path: str) -> str | None:
    if root is None:
        return None
    el = root.find(path, NS)
    if el is None or el.text is None:
        return None
    s = el.text.strip()
    return s[:500] or None


def ooxml_props(zf: zipfile.ZipFile) -> dict[str, Any]:
    names = set(zf.namelist())
    core = xml(zf.read("docProps/core.xml")) if "docProps/core.xml" in names else None
    app = xml(zf.read("docProps/app.xml")) if "docProps/app.xml" in names else None
    props: dict[str, Any] = {
        "title": _text(core, "dc:title"),
        "subject": _text(core, "dc:subject"),
        "author": _text(core, "dc:creator"),
        "keywords": _text(core, "cp:keywords"),
        "last_modified_by": _text(core, "cp:lastModifiedBy"),
        "revision": _text(core, "cp:revision"),
        "created": w3c_date(_text(core, "dcterms:created")),
        "modified": w3c_date(_text(core, "dcterms:modified")),
        "producer": _text(app, "ep:Application"),
        "company": _text(app, "ep:Company"),
    }
    for key, tag in (("app_pages", "ep:Pages"), ("app_slides", "ep:Slides"), ("app_words", "ep:Words")):
        v = _text(app, tag)
        if v and v.isdigit():
            props[key] = int(v)
    return props


def slide_size(cx: int, cy: int) -> dict[str, Any]:
    ratio = cx / cy if cy else 0
    aspect = "custom"
    for name, r in (("16:9", 16 / 9), ("4:3", 4 / 3), ("16:10", 16 / 10), ("A4", 297 / 210), ("1:1", 1.0), ("9:16", 9 / 16)):
        if ratio and abs(ratio - r) / r < 0.02:
            aspect = name
            break
    return {"width_emu": cx, "height_emu": cy, "width_mm": round(cx / 36000, 1), "height_mm": round(cy / 36000, 1), "aspect": aspect}


def pptx_quick(zf: zipfile.ZipFile) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        root = xml(zf.read("ppt/presentation.xml"))
    except KeyError:
        return out
    if root is None:
        return out
    ids = root.findall("p:sldIdLst/p:sldId", NS)
    out["pages"] = len(ids)
    sz = root.find("p:sldSz", NS)
    if sz is not None and sz.get("cx") and sz.get("cy"):
        out["slide_size"] = slide_size(int(sz.get("cx")), int(sz.get("cy")))
    return out


def xlsx_sheets(zf: zipfile.ZipFile) -> list[dict[str, Any]]:
    try:
        root = xml(zf.read("xl/workbook.xml"))
    except KeyError:
        return []
    if root is None:
        return []
    out = []
    for el in root.findall("s:sheets/s:sheet", NS):
        out.append({"name": el.get("name") or "", "state": el.get("state") or "visible",
                    "rid": el.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")})
    return out


def _clean_props(props: dict[str, Any]) -> dict[str, Any] | None:
    keep = {k: v for k, v in props.items() if v not in (None, "", [])}
    return keep or None


def quick_meta(data: bytes, det: Detected) -> dict[str, Any]:
    """{pages, width, height, doc_props, meta} — 실패해도 예외를 내지 않는다."""
    out: dict[str, Any] = {"pages": None, "width": None, "height": None, "doc_props": None, "meta": {}}
    try:
        if det.kind == "pdf":
            info = pdfium.quick_info(data)
            if info.get("encrypted"):
                out["meta"]["encrypted"] = True
            else:
                out["pages"] = info.get("pages")
                out["doc_props"] = _clean_props(info.get("props") or {})
                if info.get("page_size"):
                    out["meta"]["page_size_pt"] = [round(v, 2) for v in info["page_size"]]
        elif det.kind in ("pptx", "docx", "xlsx"):
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                props = ooxml_props(zf)
                if det.kind == "pptx":
                    q = pptx_quick(zf)
                    out["pages"] = q.get("pages")
                    if q.get("slide_size"):
                        out["meta"]["slide_size"] = q["slide_size"]
                elif det.kind == "xlsx":
                    sheets = xlsx_sheets(zf)
                    out["pages"] = len(sheets) or None
                    out["meta"]["sheet_names"] = [s["name"] for s in sheets][:50]
                else:
                    out["pages"] = props.get("app_pages")
                for k in ("app_pages", "app_slides", "app_words", "revision", "keywords"):
                    props.pop(k, None)
                out["doc_props"] = _clean_props(props)
            if det.fmt not in ("pptx", "docx", "xlsx"):
                out["meta"]["format"] = det.fmt
        elif det.kind == "image":
            info = image_info(data)
            out["width"], out["height"] = info.get("width"), info.get("height")
            if info.get("frames"):
                out["pages"] = info["frames"]
                out["meta"]["frames"] = info["frames"]
            if info.get("exif"):
                out["meta"]["exif"] = info["exif"]
                ex = info["exif"]
                out["doc_props"] = _clean_props({"created": ex.get("taken_at"), "author": ex.get("artist"),
                                                 "producer": " ".join(x for x in (ex.get("make"), ex.get("model")) if x) or None})
        elif det.kind == "svg":
            w, h = svg_size(data)
            out["width"], out["height"] = w, h
        elif det.kind == "text":
            text, enc = decode_text(data[:2_000_000])
            out["meta"]["encoding"] = enc
            out["meta"]["lines"] = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
            if det.fmt != "txt":
                out["meta"]["format"] = det.fmt
        elif det.kind == "email":
            from .parsers.email_parse import quick_headers

            hdr = quick_headers(data, det.fmt)
            out["doc_props"] = _clean_props({"title": hdr.get("subject"), "author": hdr.get("from"), "created": hdr.get("date")})
            out["meta"]["format"] = det.fmt
        elif det.kind == "zip":
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                infos = zf.infolist()
                out["meta"]["entries"] = len(infos)
        else:
            out["meta"]["format"] = det.fmt
    except Exception as exc:  # noqa: BLE001 — 메타는 부가 정보
        log.info("quick meta 실패(%s): %s", det.kind, exc)
        out["meta"]["props_error"] = type(exc).__name__
    return out


_NUM = re.compile(r"^\s*([0-9.]+)\s*(px|pt|mm|cm|in)?\s*$")


def _svg_len(v: str | None) -> float | None:
    if not v:
        return None
    m = _NUM.match(v)
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2) or "px"
    return n * {"px": 1, "pt": 4 / 3, "mm": 3.7795, "cm": 37.795, "in": 96}[unit]


def svg_size(data: bytes) -> tuple[int | None, int | None]:
    root = xml(data)
    if root is None:
        return None, None
    w, h = _svg_len(root.get("width")), _svg_len(root.get("height"))
    if (w is None or h is None) and root.get("viewBox"):
        parts = re.split(r"[\s,]+", root.get("viewBox").strip())
        if len(parts) == 4:
            try:
                vw, vh = float(parts[2]), float(parts[3])
                if w is None and h is None:
                    w, h = vw, vh
                elif w is None and h:
                    w = h * vw / vh
                elif h is None and w:
                    h = w * vh / vw
            except (ValueError, ZeroDivisionError):
                pass
    return (round(w) if w else None), (round(h) if h else None)
