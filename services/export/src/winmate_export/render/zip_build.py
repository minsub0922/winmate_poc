"""ZIP — files 의 파일 · 바로 넣는 글(JSON · 텍스트) · 함께 만드는 문서(xlsx · docx · pdf 보고서 · pptx)를 묶는다.

문서: {entries: [{file_id, path} | {path, text} | {path, json} | {path, format, document}]}
경로는 상대 경로만(절대 경로 · '..' 금지). 같은 경로가 겹치면 ' (2)' 를 붙인다.
"""
from __future__ import annotations

import io
import json
import posixpath
import re
import unicodedata
import zipfile
from collections.abc import Callable
from typing import Any

BAD = re.compile(r'[<>:"|?*\x00-\x1f]')


class ZipError(ValueError):
    pass


def safe_path(p: str) -> str:
    p = unicodedata.normalize("NFC", str(p or "").replace("\\", "/")).strip()
    if not p or p.startswith("/") or re.match(r"^[A-Za-z]:", p):
        raise ZipError(f"ZIP 경로가 잘못되었습니다: {p!r}")
    norm = posixpath.normpath(p)
    if norm.startswith("..") or "/../" in f"/{norm}/":
        raise ZipError(f"ZIP 경로에 '..' 를 쓸 수 없습니다: {p!r}")
    parts = [BAD.sub("_", seg).strip() or "_" for seg in norm.split("/")]
    return "/".join(parts)


def _dedupe(path: str, used: set[str]) -> str:
    if path.lower() not in used:
        used.add(path.lower())
        return path
    stem, ext = posixpath.splitext(path)
    n = 2
    while f"{stem} ({n}){ext}".lower() in used:
        n += 1
    out = f"{stem} ({n}){ext}"
    used.add(out.lower())
    return out


def build_zip(document: dict[str, Any], *, files: dict[str, bytes], nested: Callable[[str, dict[str, Any]], bytes] | None = None,
              names: dict[str, str] | None = None) -> bytes:
    """files: 미리 받은 file_id → 바이트. nested(format, document) → 바이트(함께 만드는 문서)."""
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ZipError("entries 가 비어 있습니다")
    out = io.BytesIO()
    used: set[str] = set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                raise ZipError(f"entries[{i}] 형식이 잘못되었습니다")
            fid = e.get("file_id")
            path = e.get("path") or (names or {}).get(fid or "") or (fid or "")
            path = _dedupe(safe_path(path), used)
            if fid:
                if fid not in files:
                    raise ZipError(f"파일을 찾을 수 없습니다: {fid}")
                data = files[fid]
                # 이미 압축된 형식은 다시 압축하지 않는다
                ctype = zipfile.ZIP_STORED if re.search(r"\.(png|jpe?g|webp|zip|pptx|docx|xlsx|mp4|pdf)$", path, re.I) else zipfile.ZIP_DEFLATED
                zf.writestr(zipfile.ZipInfo(path, date_time=(2026, 1, 1, 0, 0, 0)), data, compress_type=ctype)
            elif "json" in e:
                zf.writestr(path, json.dumps(e["json"], ensure_ascii=False, indent=2))
            elif "text" in e:
                zf.writestr(path, str(e["text"]))
            elif e.get("format") and isinstance(e.get("document"), dict):
                if nested is None:
                    raise ZipError("함께 만드는 문서를 지원하지 않습니다")
                zf.writestr(path, nested(str(e["format"]), e["document"]))
            else:
                raise ZipError(f"entries[{i}] 에 file_id · text · json · format+document 중 하나가 필요합니다")
    return out.getvalue()
