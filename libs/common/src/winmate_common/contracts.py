"""OpenAPI 계약(contracts/<service>.json) 로 서비스 간 요청·응답을 검증한다.

- 경로 매칭: `/v1/items/{item_id}` 같은 템플릿 → 정규식
- JSON 본문만 검증한다(multipart·바이너리·SSE 는 경로·메서드 존재만 확인)
- 스키마 `$ref` 는 계약 문서 전체를 리소스로 등록해 해석한다(JSON Schema 2020-12)
"""
from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .env import repo_root

_METHODS = ("get", "post", "put", "patch", "delete")


class ContractViolation(Exception):
    def __init__(self, service: str, where: str, errors: list[str]):
        super().__init__(f"[contract:{service}] {where}: " + "; ".join(errors[:5]))
        self.service = service
        self.where = where
        self.errors = errors


@dataclass
class Operation:
    method: str
    template: str
    pointer: str            # JSON pointer to the operation object
    op: dict[str, Any]


def _escape_pointer(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


class Contract:
    def __init__(self, service: str, spec: dict[str, Any]):
        self.service = service
        self.spec = spec
        self.uri = f"urn:winmate:contract:{service}"
        resource = Resource.from_contents(spec, default_specification=DRAFT202012)
        self.registry: Registry = Registry().with_resource(self.uri, resource)
        self._routes: list[tuple[re.Pattern[str], Operation]] = []
        for template, item in (spec.get("paths") or {}).items():
            regex = "^" + re.sub(r"\\\{[^}]+\\\}", r"([^/]+)", re.escape(template)) + "$"
            for method in _METHODS:
                if method in item:
                    pointer = f"/paths/{_escape_pointer(template)}/{method}"
                    self._routes.append((re.compile(regex), Operation(method, template, pointer, item[method])))
        # 고정 경로가 템플릿 경로보다 먼저 매칭되도록(파라미터 수가 적은 순)
        self._routes.sort(key=lambda r: r[1].template.count("{"))

    def find(self, method: str, path: str) -> Operation | None:
        method = method.lower()
        path = path.split("?", 1)[0]
        for regex, op in self._routes:
            if op.method == method and regex.match(path):
                return op
        return None

    def _validator(self, pointer: str) -> Draft202012Validator:
        return Draft202012Validator({"$ref": f"{self.uri}#{pointer}"}, registry=self.registry)

    def validate_request(self, method: str, path: str, body: Any, *, is_json: bool) -> None:
        op = self.find(method, path)
        if op is None:
            raise ContractViolation(self.service, f"{method.upper()} {path}", ["계약에 없는 경로·메서드"])
        if not is_json:
            return
        content = ((op.op.get("requestBody") or {}).get("content") or {})
        if "application/json" not in content:
            if body is not None:
                raise ContractViolation(self.service, f"{method.upper()} {op.template}", ["JSON 본문을 받지 않는 작업"])
            return
        if body is None:
            if (op.op.get("requestBody") or {}).get("required"):
                raise ContractViolation(self.service, f"{method.upper()} {op.template}", ["본문 필요"])
            return
        pointer = f"{op.pointer}/requestBody/content/application~1json/schema"
        errors = [f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in self._validator(pointer).iter_errors(body)]
        if errors:
            raise ContractViolation(self.service, f"요청 {method.upper()} {op.template}", errors)

    def validate_response(self, method: str, path: str, status: int, body: Any, content_type: str) -> None:
        op = self.find(method, path)
        if op is None:
            return
        if "application/json" not in content_type:
            return
        responses = op.op.get("responses") or {}
        key = str(status)
        if key not in responses:
            key = f"{str(status)[0]}XX"
            if key not in responses:
                key = "default" if "default" in responses else ""
        if not key:
            if 200 <= status < 300:
                raise ContractViolation(self.service, f"응답 {method.upper()} {op.template}", [f"계약에 없는 상태 {status}"])
            return
        content = (responses[key].get("content") or {})
        if "application/json" not in content or "schema" not in content["application/json"]:
            return
        pointer = f"{op.pointer}/responses/{_escape_pointer(key)}/content/application~1json/schema"
        errors = [f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in self._validator(pointer).iter_errors(body)]
        if errors:
            raise ContractViolation(self.service, f"응답 {status} {method.upper()} {op.template}", errors)


def contract_path(service: str) -> Path:
    return repo_root() / "contracts" / f"{service}.json"


_cache: dict[str, tuple[int, Contract]] = {}
_lock = threading.Lock()


def load_contract(service: str) -> Contract | None:
    """contracts/<service>.json — 파일 수정 시각(mtime)이 바뀌면 다시 읽는다(`make contracts` 뒤 재시작 없이 반영)."""
    p = contract_path(service)
    try:
        mtime = p.stat().st_mtime_ns
    except FileNotFoundError:
        _cache.pop(service, None)
        return None
    hit = _cache.get(service)
    if hit is not None and hit[0] == mtime:
        return hit[1]
    with _lock:
        hit = _cache.get(service)
        if hit is not None and hit[0] == mtime:
            return hit[1]
        contract = Contract(service, json.loads(p.read_text(encoding="utf-8")))
        _cache[service] = (mtime, contract)
        return contract


def reload_contracts() -> None:
    _cache.clear()
