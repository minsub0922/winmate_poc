"""다른 서비스 호출(게이트웨이 경유 · 계약 검증). 실패해도 화면이 멈추지 않게 대부분 None/빈 값으로 내려간다.

- 계약에 그 경로가 있으면 기본 검증(dev = strict), 아직 계약이 없는 경로(만드는 중인 서비스)는 warn 으로 부른다.
- 다른 서비스 코드를 import 하지 않는다.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.contracts import ContractViolation, load_contract
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.proposal.clients")

_cache: dict[str, tuple[float, Any]] = {}


def _has_path(service: str, method: str, path: str) -> bool:
    try:
        c = load_contract(service)
    except Exception:  # noqa: BLE001
        return False
    return bool(c and c.find(method, path))


def client(service: str, method: str = "GET", path: str = "/", timeout: float = 120.0) -> ServiceClient:
    validation = None if _has_path(service, method, path) else "warn"
    return ServiceClient(service, timeout=timeout, validation=validation)


async def call(service: str, method: str, path: str, *, json: Any = None, params: dict[str, Any] | None = None,
               timeout: float = 120.0, quiet: bool = False, raise_errors: bool = False) -> Any:
    """호출 결과(dict) 또는 None. raise_errors=True 면 ApiError 를 그대로 올린다."""
    try:
        c = client(service, method, path, timeout)
        return await c.request(method, path, params=params, json_body=json)
    except ApiError as exc:
        if raise_errors:
            raise
        if not quiet:
            log.info("%s %s %s → %s %s", service, method, path, exc.status, exc.code)
        return None
    except ContractViolation as exc:
        if raise_errors:
            raise ApiError(502, "UPSTREAM_UNAVAILABLE", f"{service} 계약과 맞지 않아요", {"service": service, "error": str(exc)[:300]}) from exc
        log.warning("%s 계약 위반: %s", service, exc)
        return None
    except RuntimeError as exc:   # consumes 위반 등
        if raise_errors:
            raise
        log.warning("%s 호출 불가: %s", service, exc)
        return None
    except Exception as exc:  # noqa: BLE001 — 연결 실패
        if raise_errors:
            raise ApiError(502, "UPSTREAM_UNAVAILABLE", f"{service} 서비스에 연결하지 못했어요", {"service": service}) from exc
        if not quiet:
            log.info("%s %s %s 실패: %s", service, method, path, type(exc).__name__)
        return None


async def cached(key: str, ttl: float, fn: Any) -> Any:
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    val = await fn()
    if val is not None:
        _cache[key] = (time.time(), val)
    return val


def clear_cache() -> None:
    _cache.clear()


# ── kb ─────────────────────────────────────────────────────
async def kb_query(pattern: str, body: dict[str, Any]) -> dict[str, Any] | None:
    import json as _j
    key = f"kbq:{pattern}:{_j.dumps(body, sort_keys=True, ensure_ascii=False)}"
    return await cached(key, 600, lambda: call("kb", "POST", f"/v1/query/{pattern}", json=body, quiet=True))


async def kb_get(path: str, params: dict[str, Any] | None = None, ttl: float = 600) -> Any:
    import json as _j
    key = f"kbg:{path}:{_j.dumps(params or {}, sort_keys=True)}"
    return await cached(key, ttl, lambda: call("kb", "GET", path, params=params, quiet=True))


async def kb_post(path: str, body: dict[str, Any], ttl: float = 600) -> Any:
    import json as _j
    key = f"kbp:{path}:{_j.dumps(body, sort_keys=True, ensure_ascii=False)}"
    return await cached(key, ttl, lambda: call("kb", "POST", path, json=body, quiet=True))


# ── export ─────────────────────────────────────────────────
async def export_catalog() -> dict[str, dict[str, Any]]:
    """export 카탈로그 전체(칸 정의 없이) — 코드 · 표시 코드 → 요약. 1시간 캐시. 못 읽으면 빈 dict."""
    async def _load() -> dict[str, dict[str, Any]] | None:
        res = await call("export", "GET", "/v1/templates", params={"limit": 1000, "include_slots": "false"}, quiet=True)
        if not res:
            return None
        out: dict[str, dict[str, Any]] = {}
        for t in res.get("items") or []:
            out[t["code"]] = t
            if t.get("display_code"):
                out.setdefault(t["display_code"], t)
        # 별칭(VP-B → VP-B2/3/4, VP-F → VP-F2/3/4): 대표로 3
        for alias in ("VP-B", "VP-F"):
            if alias not in out and f"{alias}3" in out:
                out[alias] = {**out[f"{alias}3"], "code": alias, "display_code": alias, "alias_of": f"{alias}3"}
        return out

    res = await cached("tplcat", 3600, _load)
    return res or {}


async def export_templates(codes: list[str]) -> dict[str, dict[str, Any]]:
    cat = await export_catalog()
    if not cat:
        return {}
    return cat


async def export_template_detail(code: str, n: int | None = None) -> dict[str, Any] | None:
    """템플릿 상세(칸 정의). 상세 경로가 실패하면(export 일부 코드 500 — docs/requests/export.md) 목록 `include_slots=true` 로 대신."""
    async def _load() -> dict[str, Any] | None:
        res = await call("export", "GET", f"/v1/templates/{code}", params={"n": n} if n else None, quiet=True)
        if res:
            return res
        lst = await call("export", "GET", "/v1/templates", params={"codes": code, "include_slots": "true", "limit": 5}, quiet=True)
        for t in (lst or {}).get("items") or []:
            if t.get("code") == code or t.get("display_code") == code:
                return t
        return None
    return await cached(f"tpld:{code}:{n}", 3600, _load)


async def export_stats() -> dict[str, Any]:
    res = await cached("tplstats", 3600, lambda: call("export", "GET", "/v1/templates/stats", quiet=True))
    return res or {}


async def export_masters(project_id: str | None = None) -> list[dict[str, Any]]:
    res = await call("export", "GET", "/v1/masters", params={"project_id": project_id} if project_id else None, quiet=True)
    return list((res or {}).get("items") or [])


# ── workspace ──────────────────────────────────────────────
async def ws_items(*, feature: str | None = None, q: str | None = None, owner: str = "all", project_id: str | None = None,
                   limit: int = 100) -> list[dict[str, Any]]:
    params = {"feature": feature, "q": q, "owner": owner, "project_id": project_id, "limit": limit}
    res = await call("workspace", "GET", "/v1/items", params=params, quiet=True)
    return list((res or {}).get("items") or [])


async def ws_item(item_id: str) -> dict[str, Any] | None:
    return await call("workspace", "GET", f"/v1/items/{item_id}", quiet=True)


async def ws_users(q: str | None = None) -> list[dict[str, Any]]:
    res = await cached(f"users:{q}", 60, lambda: call("workspace", "GET", "/v1/users", params={"q": q} if q else None, quiet=True))
    return list((res or {}).get("items") or [])


# ── 파일 ───────────────────────────────────────────────────
async def file_meta(file_id: str) -> dict[str, Any] | None:
    return await call("files", "GET", f"/v1/files/{file_id}", quiet=True)


def is_contract_missing(service: str, method: str, path: str) -> bool:
    return not _has_path(service, method, path)
