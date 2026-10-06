"""게이트웨이 — 업로드 토큰 통과(로그인 없는 휴대폰 업로드) · 멱등 요청 재시도."""
from __future__ import annotations

import json

import httpx
import pytest
from itsdangerous import URLSafeTimedSerializer

from winmate_common import testing


def jresp(obj: dict, status: int = 200) -> httpx.Response:
    """스트리밍 응답(게이트웨이는 aiter_raw 로 그대로 흘려보낸다)."""
    return httpx.Response(status, headers={"content-type": "application/json"},
                          stream=httpx.ByteStream(json.dumps(obj).encode()))


@pytest.fixture
def gw(tmp_path, monkeypatch):
    with testing.environment(tmp_path, service="gateway", AUTH_MODE="local", CONTRACT_VALIDATION="off"):
        from winmate_gateway import main

        calls: list[dict] = []
        plan: dict[str, list] = {}
        status_of: dict[str, dict] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            calls.append({"method": request.method, "port": request.url.port, "path": path,
                          "user": request.headers.get("x-user-id")})
            queued = plan.get(path)
            if queued:
                item = queued.pop(0)
                if isinstance(item, Exception):
                    raise item
                return item
            if path.startswith("/v1/users/") and path.endswith("/status"):
                uid = path.split("/")[3]
                st = status_of.get(uid, {"exists": True, "disabled": False, "password_changed_at": None})
                return jresp({"id": uid, **st})
            if path == "/v1/auth/verify":
                body = json.loads(request.content)
                if body.get("password") == "pw-ok":
                    return jresp({"id": "u_kim", "name": "김", "role": "member"})
                return jresp({"error": {"code": "INVALID_CREDENTIALS", "message": "x", "details": {}}}, 401)
            if path.endswith("/principal"):
                token = path.split("/")[-2]
                body = {"valid": token == "good-token-123", "owner": "u_owner", "owner_name": "주인"} \
                    if token == "good-token-123" else {"valid": False}
                return jresp(body)
            return jresp({"ok": True, "user": request.headers.get("x-user-id")})

        main.state.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        main.state.serializer = URLSafeTimedSerializer("test-secret", salt="winmate-session")
        main._status_cache.clear()
        main._login_failures.clear()
        main.status_of = status_of   # 시험에서 사용자 상태를 바꾸려고
        yield main, calls, plan


async def _client(main):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://gw")


async def test_upload_token_passes_as_owner_without_login(gw):
    main, calls, _ = gw
    async with await _client(main) as c:
        r = await c.get("/api/birdseye/v1/upload-tokens/good-token-123")
        assert r.status_code == 200 and r.json()["user"] == "u_owner"
        r = await c.post("/api/birdseye/v1/upload-tokens/good-token-123/photos", json={"file_id": "file_1"})
        assert r.status_code == 200 and r.json()["user"] == "u_owner"
        # 파일 올리기는 X-Upload-Token 헤더가 있어야 한다
        assert (await c.post("/api/files/v1/files", content=b"x")).status_code == 401
        r = await c.post("/api/files/v1/files", content=b"x", headers={"X-Upload-Token": "good-token-123"})
        assert r.status_code == 200 and r.json()["user"] == "u_owner"


async def test_bad_token_or_other_paths_need_login(gw):
    main, calls, _ = gw
    async with await _client(main) as c:
        assert (await c.get("/api/birdseye/v1/upload-tokens/bad-token-999")).status_code == 401
        assert (await c.get("/api/birdseye/v1/birdseyes")).status_code == 401           # 토큰 경로가 아니면 로그인
        r = await c.get("/api/files/v1/files/f_1", headers={"X-Upload-Token": "good-token-123"})
        assert r.status_code == 401                                                     # 파일 읽기는 토큰으로 못 한다
    assert not any(c["path"] == "/v1/birdseyes" for c in calls)


async def test_idempotent_retry_on_dropped_keepalive(gw, monkeypatch):
    main, calls, plan = gw
    monkeypatch.setattr(main, "session_user", lambda request: {"id": "u_1", "name": "a"})
    plan["/v1/analyses/a_1"] = [httpx.RemoteProtocolError("Server disconnected without sending a response.")]
    plan["/v1/analyses"] = [httpx.RemoteProtocolError("Server disconnected without sending a response.")]
    async with await _client(main) as c:
        r = await c.get("/api/competitor/v1/analyses/a_1")
        assert r.status_code == 200                                                     # GET 은 한 번 더
        r = await c.post("/api/competitor/v1/analyses", json={})
        assert r.status_code == 502 and json.loads(r.text)["error"]["code"] == "UPSTREAM_ERROR"   # POST 는 다시 안 보냄


async def test_session_revalidated_after_disable_or_password_reset(gw):
    main, calls, _ = gw
    async with await _client(main) as c:
        r = await c.post("/api/_auth/login", json={"username": "kim", "password": "pw-ok"})
        assert r.status_code == 200
        assert (await c.get("/api/_auth/me")).status_code == 200
        assert (await c.get("/api/competitor/v1/analyses")).json()["user"] == "u_kim"
        # 관리자가 사용 중지 → (캐시가 지나면) 401
        main.status_of["u_kim"] = {"exists": True, "disabled": True, "password_changed_at": None}
        main._status_cache.clear()
        assert (await c.get("/api/_auth/me")).status_code == 401
        assert (await c.get("/api/competitor/v1/analyses")).status_code == 401
        # 비밀번호 재설정(세션보다 나중) → 401, 다시 로그인하면 된다
        main.status_of["u_kim"] = {"exists": True, "disabled": False, "password_changed_at": "2999-01-01T00:00:00Z"}
        main._status_cache.clear()
        assert (await c.get("/api/_auth/me")).status_code == 401


async def test_login_rate_limit(gw):
    main, calls, _ = gw
    async with await _client(main) as c:
        for _ in range(5):
            assert (await c.post("/api/_auth/login", json={"username": "kim", "password": "bad"})).status_code == 401
        r = await c.post("/api/_auth/login", json={"username": "kim", "password": "pw-ok"})
        assert r.status_code == 429 and r.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"
        # 다른 아이디는 아직 된다(IP 상한 20 전)
        assert (await c.post("/api/_auth/login", json={"username": "lee", "password": "pw-ok"})).status_code == 200
