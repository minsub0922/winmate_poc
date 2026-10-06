"""서비스 앱 팩토리.

모든 서비스는 `create_app("<서비스 이름>")` 으로 FastAPI 앱을 만든다. 이 팩토리가 붙여 주는 것:
- 요청 맥락(X-Request-ID · X-User-Id · X-User-Name · X-Caller-Service) → contextvars
- 내부 토큰 검사: 게이트웨이를 거치지 않은 요청(X-Internal-Token 불일치)은 401. `/healthz` 만 예외
- 공통 오류 형식과 예외 처리
- `/healthz`
- OpenAPI: servers=/api/<service>, operationId=함수 이름, 공통 4XX/5XX 응답
"""
from __future__ import annotations

import logging
import secrets
import sys
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import context
from .env import settings
from .errors import ERROR_RESPONSES, STATUS_CODES, ApiError
from .registry import get_service

log = logging.getLogger("winmate")

HealthCheck = Callable[[], Awaitable[dict[str, Any]] | dict[str, Any]]


def setup_logging(service: str) -> None:
    level = settings().log_level
    root = logging.getLogger()
    if any(getattr(h, "_winmate", False) for h in root.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler._winmate = True  # type: ignore[attr-defined]

    class _Fmt(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            record.rid = context.request_id_var.get() or "-"
            return super().format(record)

    handler.setFormatter(_Fmt(f"%(asctime)s %(levelname)s [{service}] [%(rid)s] %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class RequestContextMiddleware:
    """순수 ASGI 미들웨어(스트리밍 응답을 막지 않는다)."""

    def __init__(self, app: ASGIApp, *, service: str, require_internal: bool, open_paths: set[str]):
        self.app = app
        self.service = service
        self.require_internal = require_internal
        self.open_paths = open_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("utf-8", "replace") for k, v in scope.get("headers", [])}
        rid = headers.get("x-request-id") or context.new_request_id()
        context.request_id_var.set(rid)
        context.user_id_var.set(headers.get("x-user-id"))
        context.user_name_var.set(_decode_header(headers.get("x-user-name")))
        context.caller_var.set(headers.get("x-caller-service"))

        path = scope.get("path", "")
        if self.require_internal and path not in self.open_paths:
            token = headers.get("x-internal-token", "")
            if not secrets.compare_digest(token, settings().internal_token):
                body = ApiError(401, "UNAUTHENTICATED", "게이트웨이를 거친 요청만 받습니다").to_body()
                resp = JSONResponse(body, status_code=401, headers={"X-Request-ID": rid})
                await resp(scope, receive, send)
                return

        async def send_with_rid(message: Message) -> None:
            if message["type"] == "http.response.start":
                hdrs = list(message.get("headers", []))
                hdrs.append((b"x-request-id", rid.encode()))
                message["headers"] = hdrs
            await send(message)

        await self.app(scope, receive, send_with_rid)


def _decode_header(value: str | None) -> str | None:
    """사용자 이름은 게이트웨이가 퍼센트 인코딩해 보낸다(한글 헤더)."""
    if not value:
        return value
    from urllib.parse import unquote

    return unquote(value)


def _operation_id(route: APIRoute) -> str:
    return route.name


def create_app(
    service: str,
    *,
    version: str = "0.1.0",
    description: str | None = None,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
    health_checks: dict[str, HealthCheck] | None = None,
    require_internal: bool = True,
) -> FastAPI:
    info = get_service(service)
    setup_logging(service)
    app = FastAPI(
        title=f"winmate {service}",
        version=version,
        description=description or info.title,
        servers=[{"url": f"/api/{service}"}],
        generate_unique_id_function=_operation_id,
        responses=ERROR_RESPONSES,  # type: ignore[arg-type]
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )
    app.state.service = service
    app.state.health_checks = dict(health_checks or {})

    open_paths = {"/healthz", "/openapi.json", "/docs", "/docs/oauth2-redirect"}
    app.add_middleware(
        RequestContextMiddleware, service=service, require_internal=require_internal, open_paths=open_paths
    )

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(exc.to_body(), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()
        ]
        body = ApiError(422, "VALIDATION_ERROR", "요청 형식이 올바르지 않습니다", {"errors": errors}).to_body()
        return JSONResponse(body, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = STATUS_CODES.get(exc.status_code, "ERROR")
        message = exc.detail if isinstance(exc.detail, str) else code
        return JSONResponse(ApiError(exc.status_code, code, message).to_body(), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error: %s", exc)
        body = ApiError(500, "INTERNAL", "서버 내부 오류", {"type": type(exc).__name__}).to_body()
        return JSONResponse(body, status_code=500)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, Any]:
        checks: dict[str, Any] = {}
        ok = True
        for name, fn in app.state.health_checks.items():
            try:
                res = fn()
                if hasattr(res, "__await__"):
                    res = await res  # type: ignore[misc]
                checks[name] = res
                if isinstance(res, dict) and res.get("ok") is False:
                    ok = False
            except Exception as exc:  # noqa: BLE001
                checks[name] = {"ok": False, "error": str(exc)}
                ok = False
        return {"service": service, "status": "ok" if ok else "degraded", "version": version, "checks": checks}

    return app
