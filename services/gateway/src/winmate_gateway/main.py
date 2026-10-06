"""API 게이트웨이(5000).

- `/api/<service>/<path>` → 해당 서비스(`127.0.0.1:<port>/<path>`)로 스트리밍 프록시(SSE·업로드 포함)
- 브라우저 요청: 세션(AUTH_MODE=local) 또는 개발 사용자(AUTH_MODE=none)로 사용자 헤더를 붙인다.
  계약에서 `internal` 태그가 붙은 작업은 브라우저가 부를 수 없다.
- 서비스 간 요청: X-Internal-Token 이 맞아야 하고, X-Caller-Service 의 consumes 에 대상이 있어야 한다.
- `/api/_health` 전체 상태, `/api/_services` 레지스트리, `/api/_openapi/<service>.json` 계약, `/api/_docs` 문서 UI
- `/api/_auth/login|logout|me` — local 세션은 60초마다 workspace 로 다시 확인(사용 중지 · 비밀번호 재설정이면 401), 로그인 연속 실패는 429.
- 로그인 없는 휴대폰 업로드(AUTH_MODE=local): birdseye 업로드 토큰 경로 · `POST /api/files/v1/files`(X-Upload-Token)는
  birdseye 내부 확인(`/v1/upload-tokens/{token}/principal`)으로 토큰 주인 이름으로 통과시킨다.
- 업스트림의 닫힌 keep-alive 연결(RemoteProtocolError)·연결 실패는 GET/HEAD 만 한 번 더 보낸다(그 밖은 502/503).
- 그 밖의 GET 은 웹 빌드(web/dist) — SPA 라서 없는 경로는 index.html
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import quote, unquote

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel
from starlette.background import BackgroundTask

from winmate_common import env
from winmate_common.app import create_app
from winmate_common.contracts import load_contract
from winmate_common.errors import ApiError
from winmate_common.registry import can_call, redis_port, services

log = logging.getLogger("winmate.gateway")

SESSION_COOKIE = "wm_session"
SESSION_MAX_AGE = 14 * 24 * 3600
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
    "transfer-encoding", "upgrade", "host", "content-length",
}
SPOOFABLE = {"x-internal-token", "x-user-id", "x-user-name", "x-caller-service"}


def _secret_key() -> str:
    key = env.get("APP_SECRET_KEY")
    if key:
        return key
    path = env.settings().data_dir / ".secret_key"
    if path.is_file():
        return path.read_text().strip()
    path.write_text(secrets.token_urlsafe(48))
    return path.read_text().strip()


class State:
    client: httpx.AsyncClient
    serializer: URLSafeTimedSerializer
    web_dist: Path
    docs_assets: Path


state = State()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    state.client = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5.0, read=None, write=120.0, pool=30.0),
        # 업스트림 uvicorn keep-alive(5초)보다 먼저 연결을 버려 '닫힌 연결 재사용'(RemoteProtocolError)을 줄인다
        limits=httpx.Limits(max_connections=200, max_keepalive_connections=50, keepalive_expiry=4.0),
        follow_redirects=False,
    )
    state.serializer = URLSafeTimedSerializer(_secret_key(), salt="winmate-session")
    root = env.settings().root
    state.web_dist = root / "web" / "dist"
    state.docs_assets = root / "ops" / "node_modules" / "swagger-ui-dist"
    yield
    await state.client.aclose()


app = create_app("gateway", require_internal=False, lifespan=lifespan)


# ── 사용자 ────────────────────────────────────────────────

def auth_mode() -> str:
    return (env.get("AUTH_MODE", "none") or "none").lower()


def dev_user() -> dict[str, str]:
    return {"id": env.get("DEV_USER_ID", "u_dev") or "u_dev", "name": env.get("DEV_USER_NAME", "개발자") or "개발자"}


def session_user(request: Request) -> dict[str, str] | None:
    if auth_mode() == "none":
        return dev_user()
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    try:
        data = state.serializer.loads(raw, max_age=SESSION_MAX_AGE)
        return {"id": data["id"], "name": data["name"], "iat": str(data.get("iat") or 0)}
    except (BadSignature, KeyError):
        return None


# 세션 다시 확인(AUTH_MODE=local): 사용 중지 · 비밀번호 재설정 뒤 기존 세션을 끊는다. 사용자마다 60초 캐시,
# workspace 가 잠깐 안 되면 통과시킨다(사내망 가용성 우선 — 로그에 남김).
_STATUS_TTL_S = 60.0
_status_cache: dict[str, tuple[float, dict[str, Any] | None]] = {}


async def _user_status(uid: str) -> dict[str, Any] | None:
    hit = _status_cache.get(uid)
    now = time.monotonic()
    if hit and hit[0] > now:
        return hit[1]
    url = f"http://127.0.0.1:{services()['workspace'].port}/v1/users/{quote(uid, safe='')}/status"
    try:
        r = await state.client.get(url, headers={"x-internal-token": env.settings().internal_token,
                                                 "x-caller-service": "gateway"}, timeout=5.0)
        status = r.json() if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        log.warning("세션 확인: workspace 응답 없음 — 이번에는 통과(%s)", uid)
        return None
    _status_cache[uid] = (now + _STATUS_TTL_S, status)
    return status


def _iso_ts(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        from datetime import datetime
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


async def checked_user(request: Request) -> dict[str, str] | None:
    """세션 사용자(+ local 이면 사용 중지 · 비밀번호 재설정 확인)."""
    user = session_user(request)
    if user is None or auth_mode() == "none":
        return user
    status = await _user_status(user["id"])
    if status is None:
        return user
    if not status.get("exists") or status.get("disabled"):
        return None
    if _iso_ts(status.get("password_changed_at")) > float(user.get("iat") or 0) + 1:
        return None
    return user


# 로그인 시도 제한: 같은 IP · 아이디 연속 실패 5번(10분) → 429, IP 하나에서 실패 20번(10분) → 429
_LOGIN_WINDOW_S = 600.0
_login_failures: dict[str, list[float]] = {}


def _login_keys(request: Request, username: str) -> tuple[str, str]:
    ip = request.client.host if request.client else "-"
    return f"{ip}|{username.strip().lower()}", f"{ip}|*"


def _recent(key: str) -> list[float]:
    now = time.monotonic()
    items = [t for t in _login_failures.get(key, []) if now - t < _LOGIN_WINDOW_S]
    _login_failures[key] = items
    return items


def _check_login_rate(request: Request, username: str) -> None:
    pair, ip = _login_keys(request, username)
    if len(_recent(pair)) >= 5 or len(_recent(ip)) >= 20:
        oldest = min((_recent(pair) or _recent(ip)) or [time.monotonic()])
        retry = max(1, int(_LOGIN_WINDOW_S - (time.monotonic() - oldest)))
        raise ApiError(429, "TOO_MANY_ATTEMPTS", "로그인 시도가 너무 많아요. 잠시 뒤 다시 해 주세요.", {"retry_after_s": retry})


def _login_failed(request: Request, username: str) -> None:
    for key in _login_keys(request, username):
        _login_failures.setdefault(key, []).append(time.monotonic())


def _login_ok(request: Request, username: str) -> None:
    _login_failures.pop(_login_keys(request, username)[0], None)


def is_internal(request: Request) -> bool:
    token = request.headers.get("x-internal-token", "")
    return bool(token) and secrets.compare_digest(token, env.settings().internal_token)


class LoginBody(BaseModel):
    username: str
    password: str


class Me(BaseModel):
    id: str
    name: str
    auth_mode: str


@app.post("/api/_auth/login", response_model=Me, tags=["auth"])
async def login(body: LoginBody, request: Request, response: Response) -> Me:
    if auth_mode() == "none":
        u = dev_user()
        return Me(id=u["id"], name=u["name"], auth_mode="none")
    _check_login_rate(request, body.username)
    port = services()["workspace"].port
    resp = await state.client.post(
        f"http://127.0.0.1:{port}/v1/auth/verify",
        json={"username": body.username, "password": body.password},
        headers={"X-Internal-Token": env.settings().internal_token, "X-Caller-Service": "gateway"},
    )
    if resp.status_code != 200:
        _login_failed(request, body.username)
        raise ApiError(401, "INVALID_CREDENTIALS", "아이디 또는 비밀번호가 맞지 않습니다")
    _login_ok(request, body.username)
    user = resp.json()
    _status_cache.pop(user["id"], None)
    cookie = state.serializer.dumps({"id": user["id"], "name": user["name"], "iat": int(time.time())})
    response.set_cookie(SESSION_COOKIE, cookie, max_age=SESSION_MAX_AGE, httponly=True, samesite="lax")
    return Me(id=user["id"], name=user["name"], auth_mode="local")


@app.post("/api/_auth/logout", status_code=204, tags=["auth"])
async def logout() -> Response:
    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE)
    return resp


@app.get("/api/_auth/me", response_model=Me, tags=["auth"])
async def me(request: Request) -> Me:
    user = await checked_user(request)
    if user is None:
        raise ApiError(401, "UNAUTHENTICATED", "로그인이 필요합니다")
    return Me(id=user["id"], name=user["name"], auth_mode=auth_mode())


# ── 레지스트리 · 상태 · 문서 ──────────────────────────────

@app.get("/api/_services", tags=["meta"])
async def list_services() -> dict[str, Any]:
    return {
        "services": [
            {"name": s.name, "port": s.port, "title": s.title, "feature": s.feature, "worker": s.worker,
             "consumes": list(s.consumes)}
            for s in services().values()
        ],
        "redis_port": redis_port(),
    }


async def _probe(name: str, port: int) -> tuple[str, dict[str, Any]]:
    t0 = time.perf_counter()
    try:
        r = await state.client.get(f"http://127.0.0.1:{port}/healthz", timeout=3.0)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        return name, {"ok": r.status_code == 200 and body.get("status", "ok") == "ok", "status": body.get("status"),
                      "latency_ms": int((time.perf_counter() - t0) * 1000), "port": port, "checks": body.get("checks", {})}
    except httpx.HTTPError as exc:
        return name, {"ok": False, "status": "down", "error": type(exc).__name__, "port": port}


@app.get("/api/_health", tags=["meta"])
async def health() -> dict[str, Any]:
    probes = [
        _probe(name, info.port) for name, info in services().items() if name != "gateway"
    ]
    results = dict(await asyncio.gather(*probes))
    redis_ok: dict[str, Any]
    try:
        from winmate_common.jobs import redis as get_redis

        t0 = time.perf_counter()
        await get_redis().ping()
        redis_ok = {"ok": True, "latency_ms": int((time.perf_counter() - t0) * 1000), "port": redis_port()}
    except Exception as exc:  # noqa: BLE001
        redis_ok = {"ok": False, "error": str(exc), "port": redis_port()}
    all_ok = redis_ok["ok"] and all(v["ok"] for v in results.values())
    return {"ok": all_ok, "gateway": {"ok": True, "port": services()["gateway"].port}, "redis": redis_ok, "services": results}


@app.get("/api/_openapi/{service}.json", tags=["meta"])
async def openapi_for(service: str) -> JSONResponse:
    if service not in services():
        raise ApiError(404, "NOT_FOUND", f"서비스 없음: {service}")
    path = env.settings().root / "contracts" / f"{service}.json"
    if service == "gateway":
        spec = app.openapi()
    elif path.is_file():
        spec = json.loads(path.read_text(encoding="utf-8"))
    else:
        raise ApiError(404, "NOT_FOUND", f"계약 파일 없음: contracts/{service}.json")
    return JSONResponse(spec)


DOCS_HTML = """<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>Winmate API 계약</title>
<link rel="stylesheet" href="/api/_docs/assets/swagger-ui.css"></head><body><div id="ui"></div>
<script src="/api/_docs/assets/swagger-ui-bundle.js"></script><script src="/api/_docs/assets/swagger-ui-standalone-preset.js"></script>
<script>window.ui=SwaggerUIBundle({urls:__URLS__,dom_id:'#ui',presets:[SwaggerUIBundle.presets.apis,SwaggerUIStandalonePreset],layout:'StandaloneLayout',deepLinking:true});</script>
</body></html>"""


@app.get("/api/_docs", include_in_schema=False)
async def docs() -> HTMLResponse:
    urls = [{"name": n, "url": f"/api/_openapi/{n}.json"} for n in services()]
    return HTMLResponse(DOCS_HTML.replace("__URLS__", json.dumps(urls)))


@app.get("/api/_docs/assets/{name}", include_in_schema=False)
async def docs_assets(name: str) -> Response:
    p = (state.docs_assets / name).resolve()
    if not str(p).startswith(str(state.docs_assets.resolve())) or not p.is_file():
        raise ApiError(404, "NOT_FOUND", "문서 UI 파일이 없습니다(ops 에서 npm ci 필요)")
    return FileResponse(p)


# ── 프록시 ────────────────────────────────────────────────

# 로그인 없이(AUTH_MODE=local) 업로드 토큰으로만 통과시키는 경로 — 휴대폰 QR 사진 올리기(08-birdseye BE1P)
_TOKEN_PATHS = (
    ("GET", "birdseye", re.compile(r"^v1/upload-tokens/(?P<token>[A-Za-z0-9_-]{8,64})$")),
    ("POST", "birdseye", re.compile(r"^v1/upload-tokens/(?P<token>[A-Za-z0-9_-]{8,64})/photos$")),
    ("POST", "files", re.compile(r"^v1/files$")),          # 토큰은 X-Upload-Token 헤더
)


async def token_user(service: str, path: str, request: Request) -> dict[str, str] | None:
    """업로드 토큰 경로면 토큰 주인을 돌려준다(birdseye 내부 확인). 아니면 None."""
    for method, svc, rx in _TOKEN_PATHS:
        if request.method != method or service != svc:
            continue
        m = rx.match(path)
        if not m:
            continue
        token = m.groupdict().get("token") or request.headers.get("x-upload-token", "")
        if not token or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", token):
            return None
        url = f"http://127.0.0.1:{services()['birdseye'].port}/v1/upload-tokens/{token}/principal"
        try:
            r = await state.client.get(url, headers={"x-internal-token": env.settings().internal_token,
                                                     "x-caller-service": "gateway"}, timeout=5.0)
        except httpx.HTTPError:
            return None
        if r.status_code != 200:
            return None
        info = r.json()
        if not info.get("valid") or not info.get("owner"):
            return None
        return {"id": str(info["owner"]), "name": str(info.get("owner_name") or "")}
    return None


def _internal_only(service: str, method: str, path: str) -> bool:
    contract = load_contract(service)
    if contract is None:
        return False
    op = contract.find(method, path)
    return bool(op and "internal" in (op.op.get("tags") or []))


@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def proxy(service: str, path: str, request: Request) -> Response:
    reg = services()
    if service not in reg or service == "gateway":
        raise ApiError(404, "UNKNOWN_SERVICE", f"등록되지 않은 서비스: {service}")
    target = reg[service]
    internal = is_internal(request)

    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP}
    if internal:
        caller = request.headers.get("x-caller-service")
        if caller and not can_call(caller, service):
            raise ApiError(403, "DEPENDENCY_NOT_ALLOWED", f"'{caller}' 는 '{service}' 를 호출할 수 없습니다(config/services.yaml consumes)")
    else:
        for k in list(headers):
            if k.lower() in SPOOFABLE:
                headers.pop(k)
        user = await checked_user(request) or await token_user(service, path, request)
        if user is None:
            raise ApiError(401, "UNAUTHENTICATED", "로그인이 필요합니다")
        if _internal_only(service, request.method, "/" + path):
            raise ApiError(403, "INTERNAL_ONLY", "서비스 간 호출 전용 API 입니다")
        headers["x-user-id"] = user["id"]
        headers["x-user-name"] = quote(user["name"])
        headers["x-internal-token"] = env.settings().internal_token

    length = request.headers.get("content-length")
    limit = (env.settings().upload_max_mb + 5) * 1024 * 1024
    if length and length.isdigit() and int(length) > limit:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", f"요청이 너무 큽니다(최대 {env.settings().upload_max_mb}MB)")

    rid = request.headers.get("x-request-id") or secrets.token_hex(8)
    headers["x-request-id"] = rid
    client_host = request.client.host if request.client else ""
    headers["x-forwarded-for"] = client_host
    headers["x-forwarded-proto"] = request.url.scheme
    headers["x-forwarded-prefix"] = f"/api/{service}"

    url = f"http://127.0.0.1:{target.port}/{path}"
    if request.url.query:
        url += "?" + request.url.query
    body = request.stream() if request.method in ("POST", "PUT", "PATCH", "DELETE") else None
    idempotent = request.method in ("GET", "HEAD")
    attempts = 2 if idempotent else 1
    resp = None
    for attempt in range(attempts):
        req = state.client.build_request(request.method, url, headers=headers, content=body)
        try:
            resp = await state.client.send(req, stream=True)
            break
        except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
            # 닫힌 keep-alive 연결 재사용 · 막 다시 뜬 서비스: 멱등 요청만 한 번 더
            if attempt + 1 < attempts:
                await asyncio.sleep(0.2)
                continue
            if isinstance(exc, httpx.ConnectError):
                raise ApiError(503, "UPSTREAM_UNAVAILABLE", f"'{service}' 서비스에 연결할 수 없습니다",
                               {"service": service, "port": target.port}) from None
            raise ApiError(502, "UPSTREAM_ERROR", f"'{service}' 서비스 연결이 끊겼습니다 — 다시 시도해 주세요",
                           {"service": service, "type": type(exc).__name__}) from None
        except httpx.TimeoutException:
            raise ApiError(504, "TIMEOUT", f"'{service}' 응답 시간 초과", {"service": service}) from None
    assert resp is not None

    out_headers = {k: v for k, v in resp.headers.items() if k.lower() not in HOP_BY_HOP and k.lower() != "content-encoding"}
    out_headers["x-request-id"] = rid
    return StreamingResponse(
        resp.aiter_raw(), status_code=resp.status_code, headers=out_headers,
        background=BackgroundTask(resp.aclose),
    )


# ── 웹 정적 파일(SPA) ─────────────────────────────────────

@app.get("/{full_path:path}", include_in_schema=False)
async def web(full_path: str) -> Response:
    if full_path.startswith("api/"):
        raise ApiError(404, "NOT_FOUND", "없는 API 경로입니다")
    dist = state.web_dist
    if not dist.is_dir():
        return HTMLResponse(
            "<h1>Winmate</h1><p>웹 빌드가 없습니다. 개발 중이면 <code>http://localhost:5001</code>(Vite)을 쓰거나 "
            "<code>make web-build</code> 를 실행하세요.</p>", status_code=200)
    candidate = (dist / unquote(full_path)).resolve()
    if full_path and str(candidate).startswith(str(dist.resolve())) and candidate.is_file():
        cache = "public, max-age=31536000, immutable" if "/assets/" in f"/{full_path}" else "no-cache"
        return FileResponse(candidate, headers={"Cache-Control": cache})
    return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
