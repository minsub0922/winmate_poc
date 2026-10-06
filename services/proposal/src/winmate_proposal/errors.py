"""오류 코드(§6.15) — 한국어 문구. 모두 winmate_common.errors.ApiError 로 공통 형식이 된다."""
from __future__ import annotations

from typing import Any

from winmate_common.errors import ApiError


def proposal_not_found(pid: str) -> ApiError:
    return ApiError(404, "PROPOSAL_NOT_FOUND", "제안서를 찾을 수 없어요", {"id": pid})


def sheet_not_found(sid: str) -> ApiError:
    return ApiError(404, "SHEET_NOT_FOUND", "시트를 찾을 수 없어요", {"id": sid})


def version_not_found(n: int) -> ApiError:
    return ApiError(404, "VERSION_NOT_FOUND", "그 버전을 찾을 수 없어요", {"version": n})


def not_found(what: str, ident: str | None = None, code: str = "NOT_FOUND") -> ApiError:
    return ApiError(404, code, f"{what}을(를) 찾을 수 없어요", {"id": ident})


def rev_conflict(current: int) -> ApiError:
    return ApiError(409, "REV_CONFLICT", "다른 화면에서 바뀐 내용이 있어 새로 불러왔어요", {"current_rev": current})


def job_running(job_id: str | None) -> ApiError:
    return ApiError(409, "JOB_ALREADY_RUNNING", "이미 진행 중이에요", {"job_id": job_id})


def must_confirm_pending(missing: list[int]) -> ApiError:
    return ApiError(409, "MUST_CONFIRM_PENDING", "필수 확인을 마치면 활성화", {"missing": missing})


def undo_conflict() -> ApiError:
    return ApiError(409, "UNDO_CONFLICT", "그 뒤에 바뀐 내용이 있어 되돌릴 수 없어요. 버전 · 변경 이력에서 되돌려 주세요")


def unprocessable(code: str, message: str, **details: Any) -> ApiError:
    return ApiError(422, code, message, details)


def type_required() -> ApiError:
    return unprocessable("TYPE_REQUIRED", "제안서 유형을 먼저 골라 주세요")


def section_not_in_type(key: str) -> ApiError:
    return unprocessable("SECTION_NOT_IN_TYPE", "이 유형에는 없는 섹션이에요", key=key)


def drop_not_accepted(what: str, section: str) -> ApiError:
    return unprocessable("DROP_NOT_ACCEPTED", "이 섹션은 그 자료를 받지 않아요", kind=what, section_key=section)


def file_too_large() -> ApiError:
    return ApiError(413, "FILE_TOO_LARGE", "파일당 50MB까지 올릴 수 있어요")


def unsupported_file(message: str = "PPTX · PDF만 올릴 수 있어요") -> ApiError:
    return ApiError(415, "UNSUPPORTED_FILE_TYPE", message)


def borrow_hidden() -> ApiError:
    return ApiError(403, "BORROW_MODE_CONTENT_HIDDEN", "흐름 차용 모드에선 원본 내용을 보여주지 않아요")


CONFIDENTIAL_MESSAGE = "기밀 자료라 지금 설정된 모델로는 분석할 수 없어요"


def policy_confidential() -> ApiError:
    return ApiError(403, "POLICY_CONFIDENTIAL", CONFIDENTIAL_MESSAGE)


def upstream(service: str, message: str | None = None) -> ApiError:
    return ApiError(502, "UPSTREAM_UNAVAILABLE", message or f"{service} 서비스에 연결하지 못했어요", {"service": service})


def not_implemented(what: str) -> ApiError:
    return ApiError(501, "NOT_IMPLEMENTED", "아직 준비 중인 기능이에요", {"op": what})
