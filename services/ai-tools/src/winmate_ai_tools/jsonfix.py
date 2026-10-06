"""JSON 출력 다루기 — 본문에서 JSON 꺼내기 · 스키마 검증 · 수리 지시 · 제공자별 스키마 다듬기."""
from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

log = logging.getLogger("winmate.ai_tools.json")

_FENCE = re.compile(r"```(?:json|JSON)?\s*\n?(.*?)```", re.S)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


class NoJson(ValueError):
    pass


def extract_json(text: str, prefer: str | None = None) -> Any:
    """모델 출력에서 JSON 값 하나를 꺼낸다(코드 펜스 · 앞뒤 설명 · 끝 쉼표 허용). 없으면 NoJson.

    prefer: "object" | "array" — 본문에 여러 JSON 조각이 있을 때 이 모양을 먼저 고른다.
    """
    if text is None:
        raise NoJson("빈 출력")
    s = text.strip().lstrip("﻿")
    if not s:
        raise NoJson("빈 출력")
    candidates = [s] + [m.group(1).strip() for m in _FENCE.finditer(s)]
    for c in candidates:
        for variant in (c, _TRAILING_COMMA.sub(r"\1", c)):
            try:
                return json.loads(variant)
            except ValueError:
                pass
    # 본문 속 { · [ 위치마다 raw_decode — 원하는 모양을 먼저
    dec = json.JSONDecoder()
    found: list[Any] = []
    for c in candidates:
        for start, ch in enumerate(c):
            if ch not in "{[":
                continue
            for variant in (c[start:], _TRAILING_COMMA.sub(r"\1", c[start:])):
                try:
                    value, _ = dec.raw_decode(variant)
                except ValueError:
                    continue
                found.append(value)
                break
            if found and (prefer is None or (prefer == "object") == isinstance(found[-1], dict)):
                return found[-1]
    if found:
        return found[0]
    raise NoJson("JSON 을 찾지 못했습니다")


def validator(schema: dict[str, Any]) -> Draft202012Validator:
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError:
        pass  # 느슨하게: 검사기는 만들 수 있으면 쓴다
    return Draft202012Validator(schema)


def validate(value: Any, schema: dict[str, Any]) -> list[str]:
    """스키마 위반 목록("경로: 메시지"). 빈 목록이면 통과. 스키마 자체를 못 쓰면 검증을 건너뛴다."""
    try:
        errs = sorted(validator(schema).iter_errors(value), key=lambda e: [str(p) for p in e.absolute_path])
    except Exception as exc:  # noqa: BLE001
        log.warning("JSON 스키마로 검증할 수 없어 건너뜁니다: %s", exc)
        return []
    out = []
    for e in errs[:30]:
        path = "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in e.absolute_path)
        out.append(f"{path}: {e.message[:300]}")
    return out


def top_type(schema: dict[str, Any] | None) -> str | None:
    if not isinstance(schema, dict):
        return None
    t = schema.get("type")
    if t in ("object", "array"):
        return t
    if "properties" in schema:
        return "object"
    if "items" in schema:
        return "array"
    return None


def parse_and_validate(text: str, schema: dict[str, Any], pre: Any = ...) -> tuple[Any, list[str]]:
    """(값, 오류). pre 가 주어지면(이미 파싱된 값) 그것을 검증한다."""
    if pre is not ...:
        value = pre
    else:
        try:
            value = extract_json(text, prefer=top_type(schema))
        except NoJson as exc:
            return None, [f"$: JSON 이 아닙니다 ({exc})"]
    return value, validate(value, schema)


def schema_text(schema: dict[str, Any]) -> str:
    return json.dumps(schema, ensure_ascii=False, separators=(",", ":"))


def schema_instruction(schema: dict[str, Any], name: str | None = None) -> str:
    """LLM_SUPPORTS_JSON_SCHEMA=false 일 때 시스템 지시에 붙이는 문장."""
    return (
        "Return ONLY one JSON value that is valid against the JSON Schema below. "
        "No explanations, no markdown, no code fences. Use Korean for free-text values unless the schema says otherwise.\n"
        f"JSON Schema ({name or 'Output'}):\n{schema_text(schema)}"
    )


def repair_message(errors: list[str]) -> str:
    lines = "\n".join(f"- {e}" for e in errors[:15])
    return (
        "Your previous output is not valid against the required JSON Schema.\n"
        f"Problems:\n{lines}\n"
        "Return ONLY the corrected JSON value (no explanations, no code fences)."
    )


# ── Gemini response_json_schema 다듬기 ─────────────────────
# Gemini 가 받는 키(그 밖은 버린다 — 결과는 원래 스키마로 다시 검증 · 수리하므로 제약이 빠져도 안전)
_GEMINI_KEYS = {
    "$id", "$defs", "$ref", "$anchor", "type", "format", "title", "description", "enum", "items", "prefixItems",
    "minItems", "maxItems", "minimum", "maximum", "anyOf", "oneOf", "properties", "additionalProperties", "required",
    "propertyOrdering",
}
_GEMINI_FORMATS = {"date-time", "date", "time"}


def gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Gemini 의 JSON Schema 부분 집합으로 다듬는다($ref 옆 키 제거, const→enum, allOf 펼침, 지원 안 하는 키 제거)."""
    return _gem(copy.deepcopy(schema), top=True)


def _gem(node: Any, top: bool = False) -> Any:
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        out = {k: v for k, v in node.items() if k.startswith("$")}
        if "$defs" in out:
            out["$defs"] = {k: _gem(v) for k, v in out["$defs"].items()}
        return out
    n = dict(node)
    if "definitions" in n and "$defs" not in n:
        n["$defs"] = n.pop("definitions")
    if "const" in n:
        c = n.pop("const")
        if isinstance(c, (str, int, float)) and not isinstance(c, bool):
            n["enum"] = [c]
    if "allOf" in n and isinstance(n["allOf"], list):
        subs = n.pop("allOf")
        if len(subs) == 1:
            n.setdefault("anyOf", [subs[0]])
        else:
            merged_props: dict[str, Any] = {}
            required: list[str] = []
            for sub in subs:
                if isinstance(sub, dict):
                    merged_props.update(sub.get("properties") or {})
                    required += list(sub.get("required") or [])
                    for k, v in sub.items():
                        if k not in ("properties", "required"):
                            n.setdefault(k, v)
            if merged_props:
                n.setdefault("properties", {}).update(merged_props)
                n["required"] = list(dict.fromkeys([*n.get("required", []), *required]))
    if isinstance(n.get("exclusiveMinimum"), (int, float)) and not isinstance(n.get("exclusiveMinimum"), bool):
        n.setdefault("minimum", n["exclusiveMinimum"])
    if isinstance(n.get("exclusiveMaximum"), (int, float)) and not isinstance(n.get("exclusiveMaximum"), bool):
        n.setdefault("maximum", n["exclusiveMaximum"])
    t = n.get("type")
    if isinstance(t, list):
        non_null = [x for x in t if x != "null"]
        if len(t) > 1 and "null" in t and len(non_null) == 1:
            rest = {k: v for k, v in n.items() if k not in ("type", "title", "description")}
            base = {"type": non_null[0], **rest}
            n = {k: v for k, v in n.items() if k in ("title", "description")}
            n["anyOf"] = [base, {"type": "null"}]
        elif non_null:
            n["type"] = non_null[0]
    if "enum" in n:
        vals = [v for v in n["enum"] if isinstance(v, (str, int, float)) and not isinstance(v, bool)]
        if vals:
            n["enum"] = vals
        else:
            n.pop("enum")
    if "format" in n and n["format"] not in _GEMINI_FORMATS:
        n.pop("format")
    out: dict[str, Any] = {}
    for k, v in n.items():
        if k not in _GEMINI_KEYS:
            continue
        if k in ("properties", "$defs") and isinstance(v, dict):
            out[k] = {pk: _gem(pv) for pk, pv in v.items()}
        elif k in ("items", "additionalProperties") and isinstance(v, dict):
            out[k] = _gem(v)
        elif k in ("anyOf", "oneOf", "prefixItems") and isinstance(v, list):
            out[k] = [_gem(x) for x in v]
        elif k == "required" and isinstance(v, list):
            props = n.get("properties")
            out[k] = [r for r in v if not isinstance(props, dict) or r in props]
        else:
            out[k] = v
    return out


# ── OpenAI strict 가능 여부 ────────────────────────────────

def openai_strict_ok(schema: Any) -> bool:
    """OpenAI strict 모드 조건: 모든 object 가 additionalProperties=false 이고 모든 속성이 required."""
    if isinstance(schema, list):
        return all(openai_strict_ok(x) for x in schema)
    if not isinstance(schema, dict):
        return True
    is_obj = schema.get("type") == "object" or "properties" in schema
    if is_obj:
        props = schema.get("properties") or {}
        if schema.get("additionalProperties") is not False:
            return False
        if set(schema.get("required") or []) != set(props):
            return False
    for k, v in schema.items():
        if k in ("properties", "$defs", "definitions") and isinstance(v, dict):
            if not all(openai_strict_ok(x) for x in v.values()):
                return False
        elif k in ("items", "anyOf", "oneOf", "allOf", "prefixItems", "additionalProperties"):
            if not openai_strict_ok(v):
                return False
    return True


def schema_name(name: str | None) -> str:
    """OpenAI json_schema.name 규칙(영문 · 숫자 · _ · -, 64자)."""
    n = re.sub(r"[^A-Za-z0-9_-]+", "_", name or "Output").strip("_") or "Output"
    return n[:64]
