"""플랫폼 서비스(workspace · files · jobs) 자주 쓰는 호출 도우미.

기능 서비스가 자원을 만들거나 바꾸면 `await register_item(...)` 로 workspace 색인에 올린다
(홈 최근 작업, 사이드바 이력). 실패해도 본 작업은 계속한다(경고 로그).
"""
from __future__ import annotations

import base64
import logging
from typing import Any

from .client import ServiceClient
from .errors import ApiError

log = logging.getLogger("winmate.platform")


async def register_item(
    *,
    feature: str,
    item_id: str,
    title: str,
    status: str,
    route: str,
    summary: str | None = None,
    project_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    body: dict[str, Any] = {"feature": feature, "title": title, "status": status, "route": route}
    if summary is not None:
        body["summary"] = summary
    if project_id is not None:
        body["project_id"] = project_id
    if meta is not None:
        body["meta"] = meta
    try:
        await ServiceClient("workspace").put(f"/v1/items/{item_id}", json=body)
    except (ApiError, Exception) as exc:  # noqa: BLE001 — 색인 실패가 본 작업을 막지 않는다
        log.warning("workspace 색인 실패 %s: %s", item_id, exc)


async def unregister_item(item_id: str) -> None:
    try:
        await ServiceClient("workspace").delete(f"/v1/items/{item_id}")
    except Exception as exc:  # noqa: BLE001
        log.warning("workspace 색인 삭제 실패 %s: %s", item_id, exc)


async def save_file(
    name: str,
    data: bytes,
    mime: str,
    *,
    source: str = "generated",
    confidential: bool = False,
    project_id: str | None = None,
    meta: dict[str, Any] | None = None,
    parent_id: str | None = None,
    purpose: str | None = None,
    folder: str | None = None,
) -> dict[str, Any]:
    """바이트를 files 서비스에 저장하고 FileMeta 를 돌려준다.

    parent_id 를 주면 원본 파일의 confidential · project_id 를 files 가 이어받는다(렌디션 · 추출물 · 생성물).
    """
    body: dict[str, Any] = {
        "name": name, "mime": mime, "data_b64": base64.b64encode(data).decode(), "source": source,
        "confidential": confidential,
    }
    for key, value in (("project_id", project_id), ("meta", meta), ("parent_id", parent_id), ("purpose", purpose),
                       ("folder", folder)):
        if value:
            body[key] = value
    return await ServiceClient("files").post("/v1/files/bytes", json=body)


async def file_meta(file_id: str) -> dict[str, Any]:
    return await ServiceClient("files").get(f"/v1/files/{file_id}")


async def file_bytes(file_id: str) -> tuple[bytes, str]:
    return await ServiceClient("files").get_bytes(f"/v1/files/{file_id}/content")


async def parsed_document(file_id: str) -> dict[str, Any]:
    return await ServiceClient("files").get(f"/v1/files/{file_id}/parsed")
