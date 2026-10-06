"""공통 오류 형식: HTTP 상태 + {"error": {"code", "message", "details"}}."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(description="UPPER_SNAKE 오류 코드")
    message: str = Field(description="사람이 읽는 한국어 메시지")
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetail


class ApiError(Exception):
    """서비스 코드에서 던지면 공통 오류 형식으로 응답된다. 다른 서비스 호출이 실패해도 이 예외로 올라온다."""

    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(f"{status} {code}: {message}")
        self.status = status
        self.code = code
        self.message = message
        self.details = details or {}

    def to_body(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, "details": self.details}}


def not_found(what: str, ident: str | None = None) -> ApiError:
    msg = f"{what}을(를) 찾을 수 없습니다" + (f": {ident}" if ident else "")
    return ApiError(404, "NOT_FOUND", msg, {"resource": what, "id": ident})


def bad_request(message: str, **details: Any) -> ApiError:
    return ApiError(400, "INVALID_ARGUMENT", message, details)


def conflict(message: str, **details: Any) -> ApiError:
    return ApiError(409, "CONFLICT", message, details)


def forbidden(message: str, code: str = "FORBIDDEN", **details: Any) -> ApiError:
    return ApiError(403, code, message, details)


def unavailable(message: str, **details: Any) -> ApiError:
    return ApiError(503, "UPSTREAM_UNAVAILABLE", message, details)


STATUS_CODES = {
    400: "INVALID_ARGUMENT",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL",
    501: "NOT_IMPLEMENTED",
    502: "BAD_GATEWAY",
    503: "UPSTREAM_UNAVAILABLE",
    504: "TIMEOUT",
}


# OpenAPI 에 공통 오류 응답을 싣기 위한 조각
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    "4XX": {"model": ErrorResponse, "description": "요청 오류"},
    "5XX": {"model": ErrorResponse, "description": "서버 오류"},
}
