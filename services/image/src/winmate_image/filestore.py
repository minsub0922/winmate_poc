"""files 서비스 도우미 — 이미지 바이너리는 files 만 저장한다(ARCHITECTURE §5).

- 렌디션 · 마스크 · 초안 · 내보내기 파일은 `save_file(..., parent_id=)` 로 원본에 묶어 기밀 · 프로젝트를 이어받는다.
- 화면 주소는 게이트웨이 경로(`/api/files/v1/files/{id}/content` · `/thumbnail?w=`).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from PIL import Image

from winmate_common.platform import file_bytes, file_meta, save_file

from . import imaging

log = logging.getLogger("winmate.image.files")


def content_url(file_id: str | None) -> str | None:
    return f"/api/files/v1/files/{file_id}/content" if file_id else None


def download_url(file_id: str | None) -> str | None:
    return f"/api/files/v1/files/{file_id}/content?download=1" if file_id else None


def thumb_url(file_id: str | None, w: int = 320) -> str | None:
    return f"/api/files/v1/files/{file_id}/thumbnail?w={w}" if file_id else None


async def save_image(im: Image.Image, name: str, *, fmt: str = "PNG", embed: dict[str, Any] | None = None,
                     meta: dict[str, Any] | None = None, confidential: bool = False, project_id: str | None = None,
                     parent_id: str | None = None, source: str = "generated", purpose: str | None = None,
                     quality: int = 90) -> dict[str, Any]:
    data, mime = await asyncio.to_thread(imaging.encode, im, fmt, meta=embed, quality=quality)
    return await save_file(name, data, mime, source=source, confidential=confidential, project_id=project_id,
                           meta=meta, parent_id=parent_id, purpose=purpose)


async def save_bytes(name: str, data: bytes, mime: str, **kw: Any) -> dict[str, Any]:
    return await save_file(name, data, mime, **kw)


async def load_bytes(file_id: str) -> bytes:
    data, _ = await file_bytes(file_id)
    return data


async def load_image(file_id: str) -> Image.Image:
    data = await load_bytes(file_id)
    return await asyncio.to_thread(imaging.open_rgb, data)


async def meta(file_id: str) -> dict[str, Any] | None:
    try:
        return await file_meta(file_id)
    except Exception as exc:  # noqa: BLE001
        log.info("파일 메타를 읽지 못했습니다 %s: %s", file_id, exc)
        return None
