"""pypdfium2 도우미. PDFium 은 스레드 안전하지 않아 모든 호출을 프로세스 전역 잠금 안에서 한다."""
from __future__ import annotations

import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from PIL import Image

LOCK = threading.RLock()
_PDF_DATE = re.compile(r"^D?:?(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz+\-])?(\d{2})?'?(\d{2})?'?")
_UNSPECIFIED = {"", "(unspecified)", "unspecified", "untitled", "anonymous"}


class EncryptedPdf(Exception):
    pass


def pdf_date(value: str | None) -> str | None:
    """PDF 날짜(D:20240901123456+09'00') → ISO 8601 UTC."""
    if not value:
        return None
    m = _PDF_DATE.match(value.strip())
    if not m:
        return None
    y, mo, d, hh, mi, ss, sign, oh, om = m.groups()
    try:
        dt = datetime(int(y), int(mo or 1), int(d or 1), int(hh or 0), int(mi or 0), int(ss or 0))
    except ValueError:
        return None
    if sign in ("+", "-") and oh:
        off = timedelta(hours=int(oh), minutes=int(om or 0))
        dt = dt.replace(tzinfo=timezone(off if sign == "+" else -off))
    else:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean(v: Any) -> str | None:
    if not isinstance(v, str):
        return None
    s = v.replace("\x00", "").strip()
    return None if s.lower() in _UNSPECIFIED else s[:500]


def props_from_metadata(md: dict[str, str]) -> dict[str, Any]:
    return {
        "title": _clean(md.get("Title")),
        "author": _clean(md.get("Author")),
        "subject": _clean(md.get("Subject")),
        "keywords": _clean(md.get("Keywords")),
        "creator": _clean(md.get("Creator")),
        "producer": _clean(md.get("Producer")),
        "created": pdf_date(md.get("CreationDate")),
        "modified": pdf_date(md.get("ModDate")),
    }


def open_pdf(src: bytes | Path | str) -> pdfium.PdfDocument:
    """잠금 안에서 부를 것."""
    try:
        return pdfium.PdfDocument(str(src) if isinstance(src, Path) else src)
    except pdfium.PdfiumError as exc:
        if "password" in str(exc).lower():
            raise EncryptedPdf(str(exc)) from exc
        raise


def quick_info(src: bytes | Path) -> dict[str, Any]:
    """쪽 수 · 문서 속성 · 첫 쪽 크기. 암호 PDF 는 {'encrypted': True}."""
    with LOCK:
        try:
            pdf = open_pdf(src)
        except EncryptedPdf:
            return {"encrypted": True}
        try:
            n = len(pdf)
            md = pdf.get_metadata_dict(skip_empty=True)
            size = list(pdf.get_page_size(0)) if n else None
        finally:
            pdf.close()
    return {"pages": n, "props": props_from_metadata(md), "page_size": size}


def page_count(src: bytes | Path) -> int:
    with LOCK:
        pdf = open_pdf(src)
        try:
            return len(pdf)
        finally:
            pdf.close()


def render_page(src: bytes | Path, n: int, w: int, *, max_ratio: float = 50.0) -> Image.Image:
    """n 쪽(1부터)을 가로 w px 로 그린다."""
    with LOCK:
        pdf = open_pdf(src)
        try:
            if n < 1 or n > len(pdf):
                raise IndexError(n)
            page = pdf[n - 1]
            try:
                pw, ph = page.get_size()
                scale = w / max(pw, 1.0)
                if ph * scale > w * max_ratio:
                    scale = (w * max_ratio) / max(ph, 1.0)
                scale = max(0.05, min(scale, 12.0))
                bitmap = page.render(scale=scale, may_draw_forms=True)
                img = bitmap.to_pil()
                img = img.copy()  # 버퍼를 PDFium 밖으로
                bitmap.close()
            finally:
                page.close()
        finally:
            pdf.close()
    if img.mode == "BGRA" or img.mode == "RGBA":
        img = img.convert("RGB")
    return img
