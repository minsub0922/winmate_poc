"""OOXML 공통 — 서식 파일(.potx · .dotx · .ppsx …)을 python-pptx/python-docx 가 여는 형식으로 바꾸기, 속성 읽기."""
from __future__ import annotations

import io
import zipfile
from typing import Any

from ..docprops import ooxml_props

_MAIN_CT = {
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
}
_ALT_CT = {
    "pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.template.main+xml",
        "application/vnd.openxmlformats-officedocument.presentationml.slideshow.main+xml",
        "application/vnd.ms-powerpoint.template.macroEnabled.main+xml",
        "application/vnd.ms-powerpoint.slideshow.macroEnabled.main+xml",
    ),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml",
        "application/vnd.ms-word.template.macroEnabledTemplate.main+xml",
    ),
}


def as_main_package(data: bytes, family: str) -> bytes:
    """[Content_Types].xml 의 서식 · 쇼 형식 주 문서 형식을 일반 문서로 바꾼 사본(메모리)."""
    src = zipfile.ZipFile(io.BytesIO(data))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            blob = src.read(info.filename)
            if info.filename == "[Content_Types].xml":
                text = blob.decode("utf-8")
                for ct in _ALT_CT[family]:
                    text = text.replace(ct, _MAIN_CT[family])
                blob = text.encode("utf-8")
            dst.writestr(info, blob)
    return out.getvalue()


def props(data: bytes) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            p = ooxml_props(zf)
    except (zipfile.BadZipFile, KeyError, OSError):
        return {}
    return {
        "author": p.get("author"), "title": p.get("title"), "subject": p.get("subject"),
        "created": p.get("created"), "modified": p.get("modified"), "producer": p.get("producer"),
        "last_modified_by": p.get("last_modified_by"), "company": p.get("company"), "keywords": p.get("keywords"),
        "revision": p.get("revision"),
    }


SKIP_IMAGE_TYPES = {"image/x-emf", "image/x-wmf", "image/emf", "image/wmf", "image/x-pict"}
EXT_BY_CT = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/bmp": "bmp", "image/tiff": "tif",
             "image/webp": "webp", "image/svg+xml": "svg", "image/x-png": "png", "image/jpg": "jpg"}


def image_ext(content_type: str, partname: str) -> str:
    ext = EXT_BY_CT.get(content_type)
    if ext:
        return ext
    tail = partname.rsplit(".", 1)[-1].lower() if "." in partname else "bin"
    return "jpg" if tail == "jpeg" else tail
