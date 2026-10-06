#!/usr/bin/env python3
"""OpenAPI 계약 내보내기·검사.

  uv run python scripts/contracts.py export [서비스 ...]   # contracts/<서비스>.json 갱신(깨지는 변경은 경고)
  uv run python scripts/contracts.py check  [서비스 ...]   # 코드와 계약 파일이 다르면 실패(CI 용)
  uv run python scripts/contracts.py diff <서비스>          # 이전 계약과 비교한 깨지는 변경 목록

계약은 코드(FastAPI)에서 만든다. 각 서비스는 별도 프로세스에서 불러온다(서비스끼리 import 섞임 방지).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def service_names() -> list[str]:
    reg = yaml.safe_load((ROOT / "config" / "services.yaml").read_text(encoding="utf-8"))["services"]
    return list(reg)


def dump_spec(service: str) -> dict[str, Any]:
    module = "winmate_" + service.replace("-", "_")
    code = (
        "import json,sys\n"
        f"from {module}.main import app\n"
        "spec = app.openapi()\n"
        "sys.stdout.write(json.dumps(spec, ensure_ascii=False))\n"
    )
    env = dict(os.environ, WINMATE_SERVICE=service, WINMATE_CONTRACT_EXPORT="1")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"[{service}] 앱을 불러오지 못했다:\n{out.stderr[-3000:]}")
    spec = json.loads(out.stdout)
    if service == "gateway":
        # 게이트웨이는 프록시 경로를 빼고 자기 API(/api/_auth, /api/_health …)만 싣는다
        spec["paths"] = {k: v for k, v in spec.get("paths", {}).items() if k.startswith("/api/_")}
        spec["servers"] = [{"url": "/"}]
    return spec


def render(spec: dict[str, Any]) -> str:
    return json.dumps(spec, ensure_ascii=False, indent=2) + "\n"


# ── 깨지는 변경 검사 ───────────────────────────────────────

def _resolve(spec: dict[str, Any], schema: dict[str, Any] | None, depth: int = 0) -> dict[str, Any]:
    if not schema or depth > 8:
        return schema or {}
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        return _resolve(spec, spec.get("components", {}).get("schemas", {}).get(name, {}), depth + 1)
    return schema


def _types(spec: dict[str, Any], schema: dict[str, Any]) -> set[str]:
    s = _resolve(spec, schema)
    if "type" in s:
        t = s["type"]
        return set(t) if isinstance(t, list) else {t}
    out: set[str] = set()
    for key in ("anyOf", "oneOf"):
        for sub in s.get(key, []):
            out |= _types(spec, sub)
    return out


def _compare_obj(old_spec, new_spec, old_s, new_s, where: str, direction: str, out: list[str], depth: int = 0) -> None:
    """direction=response: 기존 필드가 사라지거나 타입이 바뀌면 깨짐. request: 새 필수 필드가 생기면 깨짐."""
    if depth > 6:
        return
    o, n = _resolve(old_spec, old_s), _resolve(new_spec, new_s)
    ot, nt = _types(old_spec, o), _types(new_spec, n)
    if ot and nt and not (ot <= nt if direction == "response" else nt >= ot):
        out.append(f"{where}: 타입 {sorted(ot)} → {sorted(nt)}")
        return
    if "object" in (ot or {"object"}) and ("properties" in o or "properties" in n):
        op, np_ = o.get("properties", {}), n.get("properties", {})
        if direction == "response":
            for k in op:
                if k not in np_:
                    out.append(f"{where}.{k}: 응답 필드 삭제")
                else:
                    _compare_obj(old_spec, new_spec, op[k], np_[k], f"{where}.{k}", direction, out, depth + 1)
        else:
            newly_required = set(n.get("required", [])) - set(o.get("required", []))
            for k in sorted(newly_required):
                out.append(f"{where}.{k}: 새 필수 요청 필드")
            for k in op:
                if k in np_:
                    _compare_obj(old_spec, new_spec, op[k], np_[k], f"{where}.{k}", direction, out, depth + 1)
    if "array" in ot and "array" in nt:
        _compare_obj(old_spec, new_spec, o.get("items", {}), n.get("items", {}), f"{where}[]", direction, out, depth + 1)


def breaking_changes(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for path, item in (old.get("paths") or {}).items():
        new_item = (new.get("paths") or {}).get(path)
        for method, op in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            where = f"{method.upper()} {path}"
            if not new_item or method not in new_item:
                out.append(f"{where}: 작업 삭제")
                continue
            nop = new_item[method]
            old_params = {(p.get("name"), p.get("in")) for p in op.get("parameters", []) if "name" in p}
            for p in nop.get("parameters", []):
                if p.get("required") and (p.get("name"), p.get("in")) not in old_params:
                    out.append(f"{where}: 새 필수 파라미터 {p.get('name')}")
            ob = ((op.get("requestBody") or {}).get("content") or {}).get("application/json", {}).get("schema")
            nb = ((nop.get("requestBody") or {}).get("content") or {}).get("application/json", {}).get("schema")
            if ob and nb:
                _compare_obj(old, new, ob, nb, f"{where} 요청", "request", out)
            for status, resp in (op.get("responses") or {}).items():
                if not str(status).startswith("2"):
                    continue
                ors = ((resp.get("content") or {}).get("application/json") or {}).get("schema")
                nresp = (nop.get("responses") or {}).get(status)
                if ors and not nresp:
                    out.append(f"{where}: 응답 {status} 삭제")
                    continue
                nrs = (((nresp or {}).get("content") or {}).get("application/json") or {}).get("schema")
                if ors and nrs:
                    _compare_obj(old, new, ors, nrs, f"{where} 응답{status}", "response", out)
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, names = argv[0], argv[1:] or service_names()
    CONTRACTS.mkdir(exist_ok=True)
    failed = 0
    for name in names:
        path = CONTRACTS / f"{name}.json"
        new = dump_spec(name)
        text = render(new)
        old = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        if cmd == "export":
            if old is not None:
                br = breaking_changes(old, new)
                if br:
                    print(f"⚠ {name}: 깨지는 변경 {len(br)}건 — 소비 서비스에 알릴 것(docs/requests/)")
                    for b in br[:30]:
                        print("   -", b)
            path.write_text(text, encoding="utf-8")
            print(f"✓ contracts/{name}.json ({len(new.get('paths', {}))} paths)")
        elif cmd == "check":
            if old is None or render(old) != text:
                failed += 1
                print(f"✗ {name}: 계약 파일이 코드와 다르다 → make contracts SERVICE={name}")
                if old is not None:
                    for b in breaking_changes(old, new)[:20]:
                        print("   - 깨짐:", b)
            else:
                print(f"✓ {name}")
        elif cmd == "diff":
            for b in breaking_changes(old or {}, new):
                print(b)
        else:
            print(__doc__)
            return 2
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
