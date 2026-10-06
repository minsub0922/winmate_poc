"""로그인(AUTH_MODE=local) — 관리자 준비 · 로그인 확인 · 사용자 관리(관리자만) · 내 비밀번호."""
from __future__ import annotations

import pytest

from winmate_common import testing


@pytest.fixture
def local(tmp_path):
    from winmate_workspace import db

    with testing.environment(tmp_path, service="workspace", AUTH_MODE="local", ADMIN_USERNAME="admin", ADMIN_PASSWORD="admin-pass"):
        db.reset_store()
        testing.use_fake_redis()
        yield
        db.reset_store()


@pytest.fixture
def none_mode(tmp_path):
    from winmate_workspace import db

    with testing.environment(tmp_path, service="workspace", AUTH_MODE="none", ADMIN_PASSWORD="admin-pass"):
        db.reset_store()
        testing.use_fake_redis()
        yield
        db.reset_store()


async def _verify(c, username: str, password: str):
    return await c.post("/v1/auth/verify", json={"username": username, "password": password})


async def test_bootstrap_admin_when_users_exist_but_no_admin(local):
    """AUTH_MODE=none 으로 먼저 띄워 개발 사용자가 생겼어도 관리자를 만든다(예전: 사용자 표가 비어 있을 때만)."""
    from winmate_workspace.db import store
    from winmate_workspace.main import app
    from winmate_workspace.users import bootstrap_admin

    store().put("users", "u_dev", {"username": "u_dev", "name": "개발자", "org": "", "role": "member"})
    assert bootstrap_admin() == "u_admin"
    assert bootstrap_admin() is None  # 이미 쓸 수 있는 관리자가 있으면 그대로
    async with testing.api_client(app, user_id="gateway", user_name="게이트웨이") as c:
        r = await _verify(c, "admin", "admin-pass")
        assert r.status_code == 200 and r.json()["id"] == "u_admin"
        assert (await _verify(c, "admin", "wrong")).status_code == 401
        assert (await _verify(c, "nobody", "admin-pass")).status_code == 401
        assert (await _verify(c, "ADMIN", "admin-pass")).status_code == 200  # 대소문자만 다르면 같은 계정
    u = store().get("users", "u_admin")
    assert u["role"] == "admin" and u["last_login_at"]


async def test_bootstrap_promotes_existing_username_and_skips_without_password(tmp_path):
    from winmate_workspace import db
    from winmate_workspace.users import bootstrap_admin, verify_password

    with testing.environment(tmp_path, service="workspace", AUTH_MODE="local", ADMIN_USERNAME="boss", ADMIN_PASSWORD=""):
        db.reset_store()
        assert bootstrap_admin() is None  # 비밀번호가 없으면 만들지 않는다
    with testing.environment(tmp_path, service="workspace", AUTH_MODE="local", ADMIN_USERNAME="boss", ADMIN_PASSWORD="new-secret"):
        db.reset_store()
        db.store().put("users", "u_boss", {"username": "boss", "name": "보스", "role": "member"})
        assert bootstrap_admin() == "u_boss"
        u = db.store().get("users", "u_boss")
        assert u["role"] == "admin" and u["name"] == "보스" and verify_password("new-secret", u["password_hash"])
    db.reset_store()


async def test_bootstrap_noop_in_none_mode(none_mode):
    from winmate_workspace.db import store
    from winmate_workspace.users import bootstrap_admin

    assert bootstrap_admin() is None
    assert store().count("users") == 0


async def test_user_admin_api(local):
    from winmate_workspace.main import app
    from winmate_workspace.users import bootstrap_admin

    bootstrap_admin()
    async with testing.api_client(app, user_id="u_admin", user_name="admin") as admin:
        me = (await admin.get("/v1/me")).json()
        assert me["role"] == "admin" and me["username"] == "admin" and me["has_password"] is True
        r = await admin.post("/v1/users", json={"username": "kim", "name": "김영업", "org": "B2B영업", "password": "kim-pass1"})
        assert r.status_code == 201, r.text
        kim = r.json()
        assert kim["id"] == "u_kim" and kim["has_password"] and not kim["disabled"] and kim["role"] == "member"
        assert (await admin.post("/v1/users", json={"username": "KIM", "name": "x", "password": "123456"})).status_code == 409
        assert (await admin.post("/v1/users", json={"username": "a b", "name": "x", "password": "123456"})).status_code == 422
        users = (await admin.get("/v1/users")).json()["items"]
        assert {u["username"] for u in users} >= {"admin", "kim"}
        # 비밀번호 재설정 · 사용 중지 · 역할
        r = await admin.patch("/v1/users/u_kim", json={"password": "reset-pass", "org": "B2B영업 2팀"})
        assert r.status_code == 200 and r.json()["org"] == "B2B영업 2팀"
        # 마지막 관리자는 강등 · 사용 중지 불가
        assert (await admin.patch("/v1/users/u_admin", json={"role": "member"})).status_code == 409
        assert (await admin.patch("/v1/users/u_admin", json={"disabled": True})).status_code == 409
        assert (await admin.patch("/v1/users/u_nobody", json={"name": "x"})).status_code == 404
        verify = await admin.post("/v1/auth/verify", json={"username": "kim", "password": "reset-pass"})
        assert verify.status_code == 200
        assert (await admin.patch("/v1/users/u_kim", json={"disabled": True})).json()["disabled"] is True
        assert (await admin.post("/v1/auth/verify", json={"username": "kim", "password": "reset-pass"})).status_code == 401
        await admin.patch("/v1/users/u_kim", json={"disabled": False, "role": "admin"})
        # 관리자가 둘이면 하나는 강등할 수 있다
        assert (await admin.patch("/v1/users/u_kim", json={"role": "member"})).status_code == 200
    async with testing.api_client(app, user_id="u_kim", user_name="김영업") as kim_c:
        assert (await kim_c.post("/v1/users", json={"username": "lee", "name": "이", "password": "123456"})).status_code == 403
        assert (await kim_c.patch("/v1/users/u_admin", json={"name": "x"})).status_code == 403
        assert (await kim_c.get("/v1/users")).status_code == 200  # 검토자 고르기 등에 쓰는 목록은 누구나
        # 내 비밀번호 바꾸기
        bad = await kim_c.post("/v1/me/password", json={"current_password": "nope", "new_password": "kim-pass2"})
        assert bad.status_code == 400 and bad.json()["error"]["code"] == "INVALID_PASSWORD"
        ok = await kim_c.post("/v1/me/password", json={"current_password": "reset-pass", "new_password": "kim-pass2"})
        assert ok.status_code == 204
        assert (await kim_c.post("/v1/auth/verify", json={"username": "kim", "password": "kim-pass2"})).status_code == 200


async def test_none_mode_user_api_open(none_mode):
    """AUTH_MODE=none(개발)에서는 누구나 사용자를 만든다(예전 동작 그대로)."""
    from winmate_workspace.main import app

    async with testing.api_client(app, user_id="u_dev", user_name="개발자") as c:
        r = await c.post("/v1/users", json={"username": "park", "name": "박", "password": "123456", "role": "admin"})
        assert r.status_code == 201
        assert (await c.patch("/v1/users/u_park", json={"org": "AX"})).json()["org"] == "AX"
        me = (await c.get("/v1/me")).json()
        assert me["user_id"] == "u_dev" and me["has_password"] is False
