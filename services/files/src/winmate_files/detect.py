"""파일 종류 판별(매직 바이트 + 확장자)과 이름 정리."""
from __future__ import annotations

import io
import mimetypes
import re
import unicodedata
import zipfile
from dataclasses import dataclass

from . import cfb

MIME = {
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "potx": "application/vnd.openxmlformats-officedocument.presentationml.template",
    "ppsx": "application/vnd.openxmlformats-officedocument.presentationml.slideshow",
    "pptm": "application/vnd.ms-powerpoint.presentation.macroEnabled.12",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "dotx": "application/vnd.openxmlformats-officedocument.wordprocessingml.template",
    "docm": "application/vnd.ms-word.document.macroEnabled.12",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xltx": "application/vnd.openxmlformats-officedocument.spreadsheetml.template",
    "xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    "msg": "application/vnd.ms-outlook",
    "eml": "message/rfc822",
    "doc": "application/msword",
    "xls": "application/vnd.ms-excel",
    "ppt": "application/vnd.ms-powerpoint",
    "hwp": "application/x-hwp",
    "hwpx": "application/hwp+zip",
    "odt": "application/vnd.oasis.opendocument.text",
    "odp": "application/vnd.oasis.opendocument.presentation",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "rtf": "application/rtf",
    "zip": "application/zip",
    "svg": "image/svg+xml",
    "png": "image/png",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "bmp": "image/bmp",
    "tiff": "image/tiff",
    "heic": "image/heic",
    "heif": "image/heif",
    "avif": "image/avif",
    "ico": "image/x-icon",
    "txt": "text/plain",
    "md": "text/markdown",
    "csv": "text/csv",
    "tsv": "text/tab-separated-values",
    "json": "application/json",
    "xml": "application/xml",
    "html": "text/html",
    "yaml": "application/yaml",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
}

TEXT_EXTS = {
    "txt": "txt", "text": "txt", "log": "txt", "md": "md", "markdown": "md", "csv": "csv", "tsv": "tsv",
    "json": "json", "xml": "xml", "html": "html", "htm": "html", "yaml": "yaml", "yml": "yaml", "ini": "txt",
}
IMAGE_EXT = {"jpg": "jpeg", "jpeg": "jpeg", "jpe": "jpeg", "png": "png", "gif": "gif", "webp": "webp", "bmp": "bmp",
             "tif": "tiff", "tiff": "tiff", "heic": "heic", "heif": "heif", "avif": "avif", "ico": "ico"}
OOXML_FAMILY = {"pptx": ("pptx", "potx", "ppsx", "pptm", "potm", "ppsm"),
                "docx": ("docx", "dotx", "docm", "dotm"),
                "xlsx": ("xlsx", "xltx", "xlsm", "xltm")}
# LibreOffice 로 OOXML/PDF 로 바꿔 읽을 수 있는 형식(kind=other)
SOFFICE_CONVERTIBLE = {"doc": "docx", "rtf": "docx", "odt": "docx", "ppt": "pptx", "odp": "pptx",
                       "xls": "xlsx", "ods": "xlsx", "hwp": "pdf"}
_HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"hevm", b"hevs"}
_HEADER_RE = re.compile(rb"^(from|to|subject|date|mime-version|received|message-id|return-path|content-type|cc|reply-to|x-[a-z0-9-]+):",
                        re.I)


@dataclass
class Detected:
    kind: str     # pdf|pptx|docx|xlsx|image|text|email|svg|zip|other
    mime: str
    fmt: str      # 세부 형식: pdf, pptx, potx, jpeg, heic, eml, msg, csv, hwpx, doc …
    confident: bool = True   # 매직 바이트로 확정했는가(텍스트류는 False)


def ext_of(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    if "." not in base:
        return ""
    return base.rsplit(".", 1)[-1].lower()


def sanitize_name(name: str | None, fallback: str = "file") -> str:
    """경로 제거 · NFC 정규화(맥 한글 자모 분리 방지) · 제어 문자 제거 · 길이 제한(확장자 보존)."""
    s = unicodedata.normalize("NFC", name or "")
    s = s.replace("\\", "/").split("/")[-1]
    s = "".join(ch for ch in s if ch >= " " and ch != "\x7f" and unicodedata.category(ch) not in ("Cc", "Cf"))
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(". ") if s.strip(". ") else ""
    if not s:
        s = fallback
    if len(s) > 200:
        ext = ext_of(s)
        stem = s[: -(len(ext) + 1)] if ext and len(ext) <= 10 else s
        s = stem[: 200 - (len(ext) + 1 if ext and len(ext) <= 10 else 0)].rstrip() + (f".{ext}" if ext and len(ext) <= 10 else "")
    return s


def _zip_kind(data: bytes, ext: str) -> Detected | None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = set(zf.namelist())
    except (zipfile.BadZipFile, OSError, ValueError, NotImplementedError):
        return None
    for kind, marker in (("pptx", "ppt/presentation.xml"), ("docx", "word/document.xml"), ("xlsx", "xl/workbook.xml")):
        if marker in names:
            fmt = ext if ext in OOXML_FAMILY[kind] else kind
            return Detected(kind, MIME.get(fmt, MIME[kind]), fmt)
    if "mimetype" in names:
        try:
            mt = zf.read("mimetype")[:100].decode("ascii", "replace").strip()
        except (KeyError, OSError, zipfile.BadZipFile):
            mt = ""
        if mt == "application/hwp+zip":
            return Detected("other", MIME["hwpx"], "hwpx")
        for fmt in ("odt", "odp", "ods"):
            if mt == MIME[fmt]:
                return Detected("other", mt, fmt)
        if mt:
            return Detected("zip", mt, ext or "zip")
    return Detected("zip", MIME["zip"], "zip")


def _image_kind(data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    if data[:2] == b"BM" and len(data) > 26:
        return "bmp"
    if data[:4] == b"\x00\x00\x01\x00" and len(data) > 22:
        return "ico"
    if data[4:8] == b"ftyp":
        major = data[8:12]
        box_len = int.from_bytes(data[0:4], "big") if len(data) >= 4 else 0
        compat = {data[i:i + 4] for i in range(16, min(max(box_len, 16), 64), 4)}
        brands = {major} | compat
        if b"avif" in brands or b"avis" in brands:
            return "avif"
        if brands & _HEIF_BRANDS:
            return "heic"
        if major in (b"mif1", b"msf1"):
            return "heif"
    return None


def _looks_like_email(data: bytes) -> bool:
    head = data[:4096].replace(b"\r\n", b"\n")
    lines = head.split(b"\n")
    hits = 0
    for line in lines[:40]:
        if not line.strip():
            break
        if line[:1] in (b" ", b"\t"):
            continue
        if _HEADER_RE.match(line):
            hits += 1
        elif b":" not in line[:80]:
            return False
    return hits >= 2


def looks_like_text(data: bytes) -> bool:
    sample = data[:8192]
    if not sample:
        return False
    if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return True
    if b"\x00" in sample:
        return False
    for enc in ("utf-8", "cp949"):
        try:
            sample.decode(enc)
            return True
        except UnicodeDecodeError as exc:
            if exc.start >= len(sample) - 4:  # 잘린 멀티바이트
                return True
    ctrl = sum(1 for b in sample if b < 9 or 13 < b < 32)
    return ctrl / len(sample) < 0.01


def detect(data: bytes, name: str, declared_mime: str | None = None) -> Detected:
    ext = ext_of(name)
    head = data[:2048]
    if b"%PDF-" in data[:1024]:
        return Detected("pdf", MIME["pdf"], "pdf")
    img = _image_kind(data)
    if img:
        return Detected("image", MIME[img], img)
    if data[:4] == b"PK\x03\x04" or (data[:4] in (b"PK\x05\x06", b"PK\x07\x08") and ext == "zip"):
        z = _zip_kind(data, ext)
        if z:
            return z
    if cfb.is_cfb(data):
        sub = cfb.classify(data) or (ext if ext in ("msg", "doc", "xls", "ppt", "hwp") else None)
        if sub == "msg":
            return Detected("email", MIME["msg"], "msg")
        if sub:
            return Detected("other", MIME[sub], sub)
        return Detected("other", "application/x-ole-storage", "ole")
    if data[4:8] == b"ftyp":
        return Detected("other", MIME["mov"] if data[8:10] == b"qt" else MIME["mp4"], "mp4", True)
    if data[:5] == b"{\\rtf":
        return Detected("other", MIME["rtf"], "rtf")
    # 텍스트류
    if looks_like_text(data):
        lowered = head.lstrip(b"\xef\xbb\xbf").lstrip().lower()
        if ext == "svg" or (b"<svg" in lowered[:2048] and (lowered.startswith(b"<?xml") or lowered.startswith(b"<svg")
                                                           or lowered.startswith(b"<!--") or lowered.startswith(b"<!doctype svg"))):
            return Detected("svg", MIME["svg"], "svg")
        if ext == "eml" or (ext in ("", "msg", "mht", "mhtml") and _looks_like_email(data)):
            return Detected("email", MIME["eml"], "eml", ext == "eml")
        fmt = TEXT_EXTS.get(ext)
        if fmt is None:
            if declared_mime and declared_mime.startswith("text/html"):
                fmt = "html"
            elif declared_mime == "application/json":
                fmt = "json"
            elif lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html"):
                fmt = "html"
            else:
                fmt = "txt"
        mime = MIME.get(fmt, "text/plain")
        if declared_mime and fmt == "txt" and (declared_mime.startswith("text/") or declared_mime in ("application/json",)):
            mime = declared_mime.split(";")[0].strip()
        return Detected("text", mime, fmt, False)
    if ext in IMAGE_EXT:  # 손상된 이미지 등
        return Detected("other", declared_mime or MIME.get(IMAGE_EXT[ext], "application/octet-stream"), IMAGE_EXT[ext], False)
    guessed = mimetypes.guess_type(f"x.{ext}")[0] if ext else None
    mime = (declared_mime if declared_mime and declared_mime != "application/octet-stream" else None) or guessed \
        or "application/octet-stream"
    return Detected("other", mime.split(";")[0].strip(), ext or "bin", False)


def kind_label(kind: str, fmt: str) -> str:
    """사람이 읽는 형식 배지(PDF · PPTX · DOCX · XLSX · TXT · 메일 · 이미지 …)."""
    if kind == "email":
        return "메일"
    if kind == "image":
        return {"jpeg": "JPG"}.get(fmt, fmt.upper())
    if kind == "text":
        return {"txt": "TXT", "md": "MD"}.get(fmt, fmt.upper())
    if kind in ("pdf", "pptx", "docx", "xlsx", "svg", "zip"):
        return kind.upper()
    return (fmt or "FILE").upper()[:5]
