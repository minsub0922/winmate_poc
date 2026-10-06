"""files 서비스 설정(환경 변수). 공통 설정(DATA_DIR · UPLOAD_MAX_MB)은 winmate_common.env.settings()."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from winmate_common import env
from winmate_common.env import settings

PARSER_VERSION = "1"

_MAC_SOFFICE = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
_OFF = {"off", "none", "no", "false", "0", "disabled"}


@dataclass(frozen=True)
class FilesSettings:
    data_dir: Path            # <DATA_DIR>/files
    upload_max_bytes: int
    parse_concurrency: int
    pdf_layout_max_pages: int  # pdfplumber(단어 · 표)로 읽는 최대 쪽 수. 넘는 쪽은 pypdfium2 줄 블록
    max_children: int          # 문서 하나에서 뽑는 자식 파일(이미지 · 첨부) 상한
    soffice_timeout_s: int

    @property
    def blobs_dir(self) -> Path:
        return self.data_dir / "blobs"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


def files_settings() -> FilesSettings:
    s = settings()
    return FilesSettings(
        data_dir=s.service_data_dir("files"),
        upload_max_bytes=max(1, s.upload_max_mb) * 1024 * 1024,
        parse_concurrency=max(1, env.get_int("FILES_PARSE_CONCURRENCY", 2)),
        pdf_layout_max_pages=max(0, env.get_int("FILES_PDF_LAYOUT_MAX_PAGES", 300)),
        max_children=max(0, env.get_int("FILES_MAX_CHILDREN", 300)),
        soffice_timeout_s=max(10, env.get_int("SOFFICE_TIMEOUT_S", 180)),
    )


def soffice_path() -> str | None:
    """LibreOffice 실행 파일. SOFFICE_PATH=경로 | off. 없으면 PATH · macOS 기본 위치에서 찾는다."""
    raw = os.environ.get("SOFFICE_PATH")
    if raw is None:
        raw = env.get("SOFFICE_PATH")
    if raw is not None and raw.strip():
        value = raw.strip()
        if value.lower() in _OFF:
            return None
        p = Path(value).expanduser()
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
        found = shutil.which(value)
        return found
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    if Path(_MAC_SOFFICE).is_file():
        return _MAC_SOFFICE
    return None
