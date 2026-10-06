"""요청 맥락(요청 ID · 사용자 · 호출 서비스). 서비스 간 호출 때 공통 클라이언트가 그대로 전달한다."""
from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)
user_name_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_name", default=None)
caller_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("caller_service", default=None)


@dataclass(frozen=True)
class User:
    id: str
    name: str


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def current_request_id() -> str:
    rid = request_id_var.get()
    if not rid:
        rid = new_request_id()
        request_id_var.set(rid)
    return rid


def current_user() -> User:
    """게이트웨이가 넘긴 사용자. 없으면(워커·테스트) 시스템 사용자."""
    return User(id=user_id_var.get() or "system", name=user_name_var.get() or "시스템")


def set_user(user_id: str | None, user_name: str | None) -> None:
    user_id_var.set(user_id)
    user_name_var.set(user_name)
