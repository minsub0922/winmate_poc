"""파서 모음 — kind(+세부 형식)에 따라 고른다. 결과는 레코드와 무관한 dict(+ `_children`)."""
from __future__ import annotations

from typing import Any

from ..detect import SOFFICE_CONVERTIBLE
from .common import Child, ParseContext, ParseError, Unsupported

__all__ = ["Child", "ParseContext", "ParseError", "Unsupported", "parse_kind", "parseable"]


def parseable(kind: str, fmt: str, *, soffice: bool) -> bool:
    if kind in ("pdf", "pptx", "docx", "xlsx", "text", "email", "image", "svg", "zip"):
        return True
    if kind == "other":
        if fmt == "hwpx":
            return True
        return soffice and fmt in SOFFICE_CONVERTIBLE
    return False


MAX_UNZIPPED = 400 * 1024 * 1024  # 압축 해제 합계 상한(압축 폭탄 · 메모리 보호)


def _zip_guard(data: bytes) -> None:
    import io
    import zipfile

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            total = sum(i.file_size for i in zf.infolist())
    except (zipfile.BadZipFile, OSError, ValueError):
        return  # 각 파서가 깨진 파일로 처리한다
    if total > MAX_UNZIPPED:
        raise ParseError("FILE_TOO_COMPLEX", f"압축을 풀면 {total // (1024 * 1024)}MB 라 읽지 않아요(최대 {MAX_UNZIPPED // (1024 * 1024)}MB)")


def parse_kind(kind: str, data: bytes, ctx: ParseContext) -> dict[str, Any]:
    if kind in ("pptx", "docx", "xlsx") or (kind == "other" and ctx.fmt == "hwpx"):
        _zip_guard(data)
    if kind == "pdf":
        from .pdf import parse_pdf

        return parse_pdf(data, ctx)
    if kind == "pptx":
        from .pptx_parse import parse_pptx

        return parse_pptx(data, ctx)
    if kind == "docx":
        from .docx_parse import parse_docx

        return parse_docx(data, ctx)
    if kind == "xlsx":
        from .xlsx_parse import parse_xlsx

        return parse_xlsx(data, ctx)
    if kind == "text":
        from .text_parse import parse_text

        return parse_text(data, ctx)
    if kind == "email":
        from .email_parse import parse_email

        return parse_email(data, ctx)
    from . import misc_parse

    if kind == "image":
        return misc_parse.parse_image(data, ctx)
    if kind == "svg":
        return misc_parse.parse_svg(data, ctx)
    if kind == "zip":
        return misc_parse.parse_zip(data, ctx)
    if kind == "other":
        if ctx.fmt == "hwpx":
            return misc_parse.parse_hwpx(data, ctx)
        target = SOFFICE_CONVERTIBLE.get(ctx.fmt)
        if target:
            return misc_parse.parse_converted(data, ctx, target)
    raise Unsupported(f"이 형식({ctx.fmt or kind})은 읽을 수 없어요")
