"""서비스 간 호출 클라이언트 — 반드시 게이트웨이(`/api/<target>`)를 거친다.

    from winmate_common.client import ServiceClient
    kb = ServiceClient("kb")
    res = await kb.get("/v1/products/search", params={"q": "QMC"})

- `config/services.yaml` 의 consumes 에 없는 서비스를 부르면 바로 예외(개발 중 의존 규칙 위반 발견)
- 요청·응답을 `contracts/<target>.json` 으로 검증(CONTRACT_VALIDATION=strict|warn|off)
- 오류 응답은 ApiError(status, code, message, details) 로 올라온다
- 요청 ID · 사용자 · 호출 서비스 · 내부 토큰 헤더를 붙인다
- 테스트에서는 `set_transport_factory()` 로 게이트웨이 대신 가짜 서비스로 보낼 수 있다(winmate_common.testing)
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Callable
from typing import Any
from urllib.parse import quote

import httpx

from . import context
from .contracts import ContractViolation, load_contract
from .env import settings
from .errors import ApiError
from .registry import can_call

log = logging.getLogger("winmate.client")

TransportFactory = Callable[[str], httpx.AsyncBaseTransport | None]
SyncTransportFactory = Callable[[str], httpx.BaseTransport | None]
_transport_factory: TransportFactory | None = None
_sync_transport_factory: SyncTransportFactory | None = None


def set_transport_factory(factory: TransportFactory | None, sync_factory: SyncTransportFactory | None = None) -> None:
    """테스트용: target 서비스 이름 → httpx 전송 계층. None 을 돌려주면 실제 게이트웨이로 보낸다."""
    global _transport_factory, _sync_transport_factory
    _transport_factory = factory
    _sync_transport_factory = sync_factory


def _caller() -> str | None:
    return settings().service


def _headers(target: str, extra: dict[str, str] | None) -> dict[str, str]:
    user = context.current_user()
    h = {
        "X-Internal-Token": settings().internal_token,
        "X-Request-ID": context.current_request_id(),
        "X-User-Id": user.id,
        "X-User-Name": quote(user.name),
    }
    caller = _caller()
    if caller:
        h["X-Caller-Service"] = caller
    if extra:
        h.update(extra)
    return h


def _raise_for_error(target: str, resp: httpx.Response) -> None:
    if resp.status_code < 400:
        return
    try:
        body = resp.json()
        err = body.get("error", {}) if isinstance(body, dict) else {}
        raise ApiError(resp.status_code, err.get("code", "ERROR"), err.get("message", resp.text[:200]), err.get("details") or {})
    except (ValueError, AttributeError):
        raise ApiError(resp.status_code, "UPSTREAM_ERROR", f"{target}: {resp.text[:200]}") from None


class ServiceClient:
    def __init__(self, target: str, *, timeout: float = 120.0, validation: str | None = None):
        caller = _caller()
        if not can_call(caller, target):
            raise RuntimeError(
                f"서비스 '{caller}' 는 '{target}' 을 호출할 수 없다. config/services.yaml 의 consumes 에 추가하거나 다른 경로를 쓰라."
            )
        self.target = target
        self.timeout = timeout
        self.validation = (validation or settings().contract_validation).lower()
        self.base_url = f"{settings().gateway_url}/api/{target}"

    # ── 검증 ───────────────────────────────────────────
    def _check(self, fn: Callable[[], None]) -> None:
        if self.validation == "off":
            return
        try:
            fn()
        except ContractViolation as exc:
            if self.validation == "strict":
                raise
            log.warning("%s", exc)

    def _validate_request(self, method: str, path: str, body: Any, is_json: bool) -> None:
        contract = load_contract(self.target)
        if contract is None:
            return
        self._check(lambda: contract.validate_request(method, path, body, is_json=is_json))

    def _validate_response(self, method: str, path: str, resp: httpx.Response) -> Any:
        ctype = resp.headers.get("content-type", "")
        data: Any = None
        if "application/json" in ctype and resp.content:
            data = resp.json()
        contract = load_contract(self.target)
        if contract is not None and data is not None:
            self._check(lambda: contract.validate_response(method, path, resp.status_code, data, ctype))
        return data

    # ── 비동기 ─────────────────────────────────────────
    def _async_client(self) -> httpx.AsyncClient:
        transport = _transport_factory(self.target) if _transport_factory else None
        base = self.base_url if transport is None else f"http://{self.target}.internal"
        return httpx.AsyncClient(base_url=base, timeout=self.timeout, transport=transport)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
        files: Any = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        raw: bool = False,
    ) -> Any:
        is_json = files is None and data is None
        self._validate_request(method, path, json_body, is_json)
        params = {k: v for k, v in (params or {}).items() if v is not None}
        async with self._async_client() as client:
            resp = await client.request(
                method.upper(), path, params=params, json=json_body if is_json else None,
                files=files, data=data, headers=_headers(self.target, headers),
            )
        _raise_for_error(self.target, resp)
        if raw:
            return resp
        return self._validate_response(method, path, resp)

    async def get(self, path: str, **kw: Any) -> Any:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, json: Any = None, **kw: Any) -> Any:  # noqa: A002
        return await self.request("POST", path, json_body=json, **kw)

    async def put(self, path: str, json: Any = None, **kw: Any) -> Any:  # noqa: A002
        return await self.request("PUT", path, json_body=json, **kw)

    async def patch(self, path: str, json: Any = None, **kw: Any) -> Any:  # noqa: A002
        return await self.request("PATCH", path, json_body=json, **kw)

    async def delete(self, path: str, **kw: Any) -> Any:
        return await self.request("DELETE", path, **kw)

    async def get_bytes(self, path: str, params: dict[str, Any] | None = None) -> tuple[bytes, str]:
        self._validate_request("GET", path, None, False)
        async with self._async_client() as client:
            resp = await client.get(path, params=params, headers=_headers(self.target, None))
        _raise_for_error(self.target, resp)
        return resp.content, resp.headers.get("content-type", "application/octet-stream")

    async def sse(self, path: str, params: dict[str, Any] | None = None) -> AsyncIterator[dict[str, Any]]:
        """SSE 이벤트를 {event, id, data} 로 넘긴다(data 는 JSON 이면 파싱)."""
        self._validate_request("GET", path, None, False)
        async with self._async_client() as client:
            async with client.stream("GET", path, params=params, headers=_headers(self.target, {"Accept": "text/event-stream"}), timeout=None) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    _raise_for_error(self.target, resp)
                event: dict[str, Any] = {}
                async for line in resp.aiter_lines():
                    if not line:
                        if event:
                            yield event
                            event = {}
                        continue
                    if line.startswith(":"):
                        continue
                    key, _, value = line.partition(":")
                    value = value[1:] if value.startswith(" ") else value
                    if key == "data":
                        try:
                            event["data"] = json.loads(value)
                        except ValueError:
                            event["data"] = value
                    elif key in ("event", "id"):
                        event[key] = value

    # ── 동기(스크립트·스레드용) ───────────────────────────
    def _sync_client(self) -> httpx.Client:
        transport = _sync_transport_factory(self.target) if _sync_transport_factory else None
        base = self.base_url if transport is None else f"http://{self.target}.internal"
        return httpx.Client(base_url=base, timeout=self.timeout, transport=transport)

    def request_sync(self, method: str, path: str, *, params: dict[str, Any] | None = None, json_body: Any = None) -> Any:
        self._validate_request(method, path, json_body, True)
        params = {k: v for k, v in (params or {}).items() if v is not None}
        with self._sync_client() as client:
            resp = client.request(method.upper(), path, params=params, json=json_body, headers=_headers(self.target, None))
        _raise_for_error(self.target, resp)
        return self._validate_response(method, path, resp)
