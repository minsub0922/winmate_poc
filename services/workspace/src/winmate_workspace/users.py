"""사용자 · 로그인 확인 · 관리자 계정.

- AUTH_MODE=none: 게이트웨이가 넘긴 개발 사용자(X-User-Id)로 프로필을 자동으로 만든다. 사용자 관리 API 는 누구나 쓴다(개발).
- AUTH_MODE=local: 게이트웨이 `/api/_auth/login` 이 `POST /v1/auth/verify`(internal)로 아이디 · 비밀번호를 확인한다.
  관리자(role=admin · 비밀번호 있음 · 사용 중)가 하나도 없으면 시작할 때(그리고 로그인 확인 때) `.env` 의
  ADMIN_USERNAME/ADMIN_PASSWORD 로 관리자를 만든다 — 먼저 AUTH_MODE=none 으로 띄워 개발 사용자가 생겼어도 만든다.
  사용자 만들기 · 고치기(이름 · 소속 · 역할 · 비밀번호 재설정 · 사용 중지)는 관리자만.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from typing import Any, Literal

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from winmate_common import env
from winmate_common.context import current_user
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import now_iso

from .db import auth_mode, store

log = logging.getLogger("winmate.workspace.users")
router = APIRouter()

USERNAME_PATTERN = r"^[A-Za-z0-9._-]+$"


# ── 비밀번호(표준 라이브러리 scrypt) ──────────────────────

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except ValueError:
        return False


def _all_users() -> list[dict[str, Any]]:
    items, _ = store().list("users", limit=5000, order_by="name")
    return items


def _usable_admin(u: dict[str, Any]) -> bool:
    return u.get("role") == "admin" and bool(u.get("password_hash")) and not u.get("disabled")


def bootstrap_admin() -> str | None:
    """AUTH_MODE=local 이고 쓸 수 있는 관리자가 없으면 `.env` 의 관리자 계정을 만든다(이미 그 아이디가 있으면 관리자로 바꾸고 비밀번호를 정한다).

    돌려주는 값: 만들거나 바꾼 사용자 id(아무것도 안 했으면 None).
    """
    if auth_mode() != "local":
        return None
    username = (env.get("ADMIN_USERNAME", "admin") or "admin").strip()
    password = env.get("ADMIN_PASSWORD")
    if not password:
        if not any(_usable_admin(u) for u in _all_users()):
            log.warning("AUTH_MODE=local 인데 관리자가 없고 ADMIN_PASSWORD 가 비어 있어 관리자를 만들지 못했습니다")
        return None
    if any(_usable_admin(u) for u in _all_users()):
        return None
    uid = "u_" + username
    cur = store().get("users", uid)
    if cur:
        store().put("users", uid, {**cur, "username": username, "role": "admin", "disabled": False,
                                   "password_hash": hash_password(password)}, keep_history=False)
    else:
        store().put("users", uid, {"username": username, "name": username, "org": "", "role": "admin",
                                   "password_hash": hash_password(password), "disabled": False}, keep_history=False)
    log.info("관리자 계정을 준비했습니다: %s", username)
    return uid


# ── 내 프로필 ────────────────────────────────────────────

class Me(BaseModel):
    user_id: str
    name: str
    given_name: str
    initial: str
    org: str = ""
    role: str = "member"
    timezone: str = "Asia/Seoul"
    username: str | None = Field(default=None, description="로그인 아이디(AUTH_MODE=local 계정)")
    has_password: bool = Field(default=False, description="로그인 비밀번호가 있는 계정")


class MePatch(BaseModel):
    name: str | None = Field(default=None, max_length=40)
    org: str | None = Field(default=None, max_length=80)


def _split_name(name: str) -> tuple[str, str]:
    """한국어 이름이면 성 한 글자 + 이름, 아니면 첫 글자 + 전체."""
    name = name.strip() or "사용자"
    if name in {"개발자", "관리자", "사용자", "시스템", "테스터"}:
        return name[0], name
    if 2 <= len(name) <= 4 and all("가" <= ch <= "힣" for ch in name):
        return name[0], name[1:]
    return name[0].upper(), name


def _profile(uid: str, name_hint: str | None) -> dict[str, Any]:
    p = store().get("users", uid)
    if p is None:
        p = store().put("users", uid, {"username": uid, "name": name_hint or uid, "org": env.get("DEV_USER_ORG", "") or "", "role": "member"})
    return p


def _me_out(p: dict[str, Any]) -> Me:
    initial, given = _split_name(p.get("name") or p["id"])
    return Me(user_id=p["id"], name=p.get("name") or p["id"], given_name=given, initial=initial, org=p.get("org") or "",
              role=p.get("role") or "member", username=p.get("username") or None, has_password=bool(p.get("password_hash")))


@router.get("/me", response_model=Me, tags=["users"])
async def get_me() -> Me:
    u = current_user()
    return _me_out(_profile(u.id, u.name))


@router.patch("/me", response_model=Me, tags=["users"])
async def patch_me(body: MePatch) -> Me:
    u = current_user()
    p = _profile(u.id, u.name)
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    return _me_out(store().patch("users", p["id"], changes, keep_history=False) if changes else p)


class PasswordBody(BaseModel):
    current_password: str | None = Field(default=None, description="지금 비밀번호(비밀번호가 있는 계정이면 필수)")
    new_password: str = Field(min_length=6, max_length=200)


@router.post("/me/password", status_code=204, tags=["users"])
async def change_my_password(body: PasswordBody) -> Response:
    u = current_user()
    p = _profile(u.id, u.name)
    if p.get("password_hash") and not verify_password(body.current_password or "", p["password_hash"]):
        raise ApiError(400, "INVALID_PASSWORD", "지금 비밀번호가 맞지 않습니다")
    store().patch("users", p["id"], {"password_hash": hash_password(body.new_password), "password_changed_at": now_iso()}, keep_history=False)
    return Response(status_code=204)


# ── 로그인 확인(게이트웨이 전용) ─────────────────────────

class VerifyBody(BaseModel):
    username: str
    password: str


class VerifiedUser(BaseModel):
    id: str
    name: str


def _find_by_username(username: str) -> dict[str, Any] | None:
    items, _ = store().list("users", where={"username": username}, limit=1)
    if items:
        return items[0]
    low = username.strip().lower()
    same = [u for u in _all_users() if (u.get("username") or "").lower() == low]
    return same[0] if len(same) == 1 else None


@router.post("/auth/verify", response_model=VerifiedUser, tags=["internal"])
async def verify(body: VerifyBody) -> VerifiedUser:
    bootstrap_admin()
    u = _find_by_username(body.username)
    if not u or u.get("disabled") or not verify_password(body.password, u.get("password_hash", "")):
        raise ApiError(401, "INVALID_CREDENTIALS", "아이디 또는 비밀번호가 맞지 않습니다")
    store().patch("users", u["id"], {"last_login_at": now_iso()}, keep_history=False)
    return VerifiedUser(id=u["id"], name=u.get("name") or body.username)


# ── 사용자 관리 ──────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=40, pattern=USERNAME_PATTERN)
    name: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=6, max_length=200)
    org: str = Field(default="", max_length=80)
    role: Literal["admin", "member"] = "member"


class UserPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    org: str | None = Field(default=None, max_length=80)
    role: Literal["admin", "member"] | None = None
    password: str | None = Field(default=None, min_length=6, max_length=200, description="비밀번호 재설정(관리자)")
    disabled: bool | None = Field(default=None, description="사용 중지(로그인 불가)")


class UserOut(BaseModel):
    id: str
    username: str
    name: str
    org: str = ""
    role: str = "member"
    disabled: bool = False
    has_password: bool = Field(default=False, description="로그인 비밀번호가 있는 계정(AUTH_MODE=none 에서 자동으로 생긴 프로필은 없음)")
    created_at: str | None = None
    last_login_at: str | None = None


class UserList(BaseModel):
    items: list[UserOut]


def _user_out(u: dict[str, Any]) -> UserOut:
    return UserOut(id=u["id"], username=u.get("username") or u["id"], name=u.get("name") or u["id"], org=u.get("org") or "",
                   role=u.get("role") or "member", disabled=bool(u.get("disabled")), has_password=bool(u.get("password_hash")),
                   created_at=u.get("created_at"), last_login_at=u.get("last_login_at"))


class UserStatus(BaseModel):
    """게이트웨이 전용(internal) — 세션 다시 확인(사용 중지 · 비밀번호 재설정 뒤 기존 세션 끊기)."""
    id: str
    exists: bool
    disabled: bool = False
    password_changed_at: str | None = None


@router.get("/users/{user_id}/status", response_model=UserStatus, tags=["internal"])
async def user_status(user_id: str) -> UserStatus:
    u = store().get("users", user_id)
    if u is None:
        return UserStatus(id=user_id, exists=False)
    return UserStatus(id=user_id, exists=True, disabled=bool(u.get("disabled")),
                      password_changed_at=u.get("password_changed_at") or None)


def require_admin() -> dict[str, Any] | None:
    """AUTH_MODE=local 이면 관리자만. none 이면 통과(개발)."""
    me = store().get("users", current_user().id)
    if auth_mode() == "local" and not (me and me.get("role") == "admin" and not me.get("disabled")):
        raise ApiError(403, "FORBIDDEN", "관리자만 사용자를 관리할 수 있습니다")
    return me


@router.post("/users", response_model=UserOut, status_code=201, tags=["users"])
async def create_user(body: UserCreate) -> UserOut:
    if auth_mode() == "local":
        me = store().get("users", current_user().id)
        if (me or {}).get("role") != "admin" or (me or {}).get("disabled"):
            raise ApiError(403, "FORBIDDEN", "관리자만 사용자를 만들 수 있습니다")
    uid = "u_" + body.username
    if store().get("users", uid) or _find_by_username(body.username):
        raise ApiError(409, "CONFLICT", "이미 있는 아이디입니다")
    p = store().put("users", uid, {"username": body.username, "name": body.name, "org": body.org, "role": body.role, "disabled": False,
                                   "password_hash": hash_password(body.password), "created_by": current_user().id}, keep_history=False)
    return _user_out(p)


@router.get("/users", response_model=UserList, tags=["users"])
async def list_users(q: str | None = None) -> UserList:
    out = [_user_out(u) for u in _all_users()]
    if q:
        out = [u for u in out if q.lower() in (u.name + u.username).lower()]
    return UserList(items=out)


@router.patch("/users/{user_id}", response_model=UserOut, tags=["users"])
async def patch_user(user_id: str, body: UserPatch) -> UserOut:
    require_admin()
    cur = store().get("users", user_id)
    if not cur:
        raise not_found("사용자", user_id)
    changes: dict[str, Any] = {k: v for k, v in body.model_dump(exclude={"password"}).items() if v is not None}
    demote = changes.get("role") == "member" or changes.get("disabled") is True
    if demote and _usable_admin(cur) and sum(1 for u in _all_users() if _usable_admin(u)) <= 1:
        raise ApiError(409, "LAST_ADMIN", "마지막 관리자는 역할을 바꾸거나 사용 중지할 수 없습니다")
    if body.password:
        changes["password_hash"] = hash_password(body.password)
        changes["password_changed_at"] = now_iso()
    if not changes:
        return _user_out(cur)
    return _user_out(store().patch("users", user_id, changes, keep_history=False))
