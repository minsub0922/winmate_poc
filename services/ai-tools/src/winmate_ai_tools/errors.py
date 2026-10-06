"""ai-tools 오류 — 공통 형식(winmate_common ApiError)으로 나간다.

| 상태 | 코드 | 언제 |
|---|---|---|
| 400 | INVALID_ARGUMENT · TOO_MANY_IMAGES · BAD_IMAGE | 요청 값 오류 |
| 403 | POLICY_CONFIDENTIAL | confidential=true 인데 `<CAP>_ALLOW_CONFIDENTIAL=false` |
| 404 | CASSETTE_MISS | MODEL_MODE=replay 인데 카세트가 없음(REPLAY_FALLBACK=mock 이 아니면) |
| 413 | CONTEXT_TOO_LONG | 메시지 토큰 추정치 > LLM_MAX_INPUT_TOKENS |
| 422 | SCHEMA_MISMATCH | 수리 재시도 후에도 스키마에 맞는 JSON 을 못 만듦 |
| 429 | RATE_LIMITED · DAILY_LIMIT_EXCEEDED | 분당 · 하루 한도 초과(제공자 429 포함) |
| 501 | NOT_CONFIGURED · EDIT_UNSUPPORTED · EMBEDDING_DISABLED | 설정 없음 · 지원 안 함 |
| 502 | PROVIDER_ERROR · FILES_UNAVAILABLE | 제공자 · files 서비스 오류 |
| 504 | TIMEOUT | 제한 시간 초과 |
"""
from __future__ import annotations

from typing import Any

from winmate_common.errors import ApiError


class ProviderError(ApiError):
    """제공자 호출 오류. retryable 이면 runtime 이 백오프 후 다시 시도한다(최대 2회)."""

    def __init__(self, status: int, code: str, message: str, details: dict[str, Any] | None = None,
                 *, retryable: bool = False):
        super().__init__(status, code, message, details)
        self.retryable = retryable


def policy_confidential(cap: str) -> ApiError:
    key = f"{cap.upper()}_ALLOW_CONFIDENTIAL"
    return ApiError(403, "POLICY_CONFIDENTIAL",
                    f"기밀 데이터는 지금 설정된 {cap} 제공자로 보낼 수 없습니다({key}=false)",
                    {"capability": cap, "env": key})


def not_configured(what: str, **details: Any) -> ApiError:
    return ApiError(501, "NOT_CONFIGURED", f"{what} 설정이 없습니다", details)


def unsupported(code: str, message: str, **details: Any) -> ApiError:
    return ApiError(501, code, message, details)


def invalid(message: str, code: str = "INVALID_ARGUMENT", **details: Any) -> ApiError:
    return ApiError(400, code, message, details)


def timeout(cap: str, seconds: float) -> ApiError:
    return ApiError(504, "TIMEOUT", f"{cap} 호출이 {seconds:g}초 안에 끝나지 않았습니다", {"capability": cap, "timeout_s": seconds})


def provider_error(provider: str, message: str, *, status: int | None = None, retryable: bool = False,
                   **details: Any) -> ProviderError:
    """제공자 HTTP 상태를 우리 오류로 바꾼다: 429 → 429 RATE_LIMITED, 408/504 → 504 TIMEOUT, 나머지 → 502."""
    d = {"provider": provider, "upstream_status": status, **details}
    if status == 429:
        return ProviderError(429, "RATE_LIMITED", f"제공자({provider}) 호출 한도에 걸렸습니다: {message}", d, retryable=True)
    if status in (408, 504):
        return ProviderError(504, "TIMEOUT", f"제공자({provider}) 응답 시간 초과: {message}", d, retryable=False)
    retry = retryable or (status is not None and status >= 500)
    return ProviderError(502, "PROVIDER_ERROR", f"제공자({provider}) 오류: {message}", d, retryable=retry)


def schema_mismatch(errors: list[str], raw: str, **details: Any) -> ApiError:
    return ApiError(422, "SCHEMA_MISMATCH", "스키마에 맞는 JSON 을 만들지 못했습니다",
                    {"errors": errors[:20], "raw": raw[:2000], **details})


def files_unavailable(message: str, **details: Any) -> ApiError:
    return ApiError(502, "FILES_UNAVAILABLE", f"files 서비스 호출 실패: {message}", details)
