"""files 서비스 앱 — `uvicorn winmate_files.main:app --port 5030`."""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from winmate_common.app import create_app
from winmate_common.env import settings

from .api import router

log = logging.getLogger("winmate.files")


class UploadLimitMiddleware:
    """Content-Length 가 한도를 넘는 업로드는 본문을 버리며 읽고 413 으로 답한다(메모리 · 디스크에 쌓지 않음)."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST" or scope.get("path") not in ("/v1/files", "/v1/files/bytes"):
            await self.app(scope, receive, send)
            return
        limit = settings().upload_max_mb * 1024 * 1024
        allowed = limit + 2 * 1024 * 1024 if scope["path"] == "/v1/files" else int(limit * 1.37) + 2 * 1024 * 1024
        length = None
        for k, v in scope.get("headers", []):
            if k == b"content-length":
                try:
                    length = int(v)
                except ValueError:
                    length = None
                break
        if length is None or length <= allowed:
            await self.app(scope, receive, send)
            return
        more = True
        while more:  # 프록시(게이트웨이)가 끊김으로 오해하지 않게 본문을 끝까지 받는다
            msg: Message = await receive()
            if msg["type"] != "http.request":
                break
            more = msg.get("more_body", False)
        body = json.dumps({"error": {"code": "PAYLOAD_TOO_LARGE",
                                     "message": f"파일당 {settings().upload_max_mb}MB까지 올릴 수 있어요",
                                     "details": {"size": length, "limit": limit}}}, ensure_ascii=False).encode("utf-8")
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    from .service import service

    svc = service()
    log.info("files 시작 — 데이터 %s · LibreOffice %s", svc.data_dir, svc.soffice.path or "없음")
    yield
    # 끝나지 않은 파싱은 멈춘다(상태가 parsing 으로 남아도 다음 조회 · 파싱 요청 때 다시 시작한다)
    tasks = [t for t in list(svc._bg) + list(svc._record_inflight.values()) if not t.done()]
    for t in tasks:
        t.cancel()
    if tasks:
        await asyncio.wait(tasks, timeout=10)


def _health() -> dict[str, Any]:
    from .service import service

    svc = service()
    return {"ok": True, "soffice": bool(svc.soffice.path)}


app = create_app("files", lifespan=lifespan, health_checks={"storage": _health})
app.add_middleware(UploadLimitMiddleware)
app.include_router(router)
