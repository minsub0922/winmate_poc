"""JSON 스키마 → 결정적 가짜 값(mock 모드).

- $ref/$defs(definitions) · object · array(prefixItems) · string · number · integer · boolean · null
- enum · const · anyOf · oneOf · allOf · type 배열 · min/maxItems · min/maxLength · minimum/maximum(exclusive) ·
  multipleOf · uniqueItems · min/maxProperties · format(date · date-time · time · uri · email · uuid …) · required
- 문자열은 속성 이름에서 만든 한국어 자리표시자("[mock] 고객사"). 배열 안 문자열에는 순번이 붙는다.
- 같은 스키마 → 항상 같은 값(입력 문장과 무관 — 기능 서비스 스냅숏 테스트가 프롬프트 수정에 흔들리지 않게).
"""
from __future__ import annotations

import copy
import math
import re
from typing import Any

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

_URI = "urn:winmate:faker"
MAX_DEPTH = 8

# 속성 이름 토큰 → 한국어
KO: dict[str, str] = {
    "customer": "고객사", "client": "고객사", "company": "회사", "org": "조직", "organization": "조직", "account": "고객 계정",
    "name": "이름", "title": "제목", "subtitle": "부제", "headline": "헤드라인", "summary": "요약", "description": "설명",
    "desc": "설명", "detail": "세부", "details": "세부", "text": "텍스트", "content": "내용", "body": "본문", "message": "메시지",
    "reason": "이유", "rationale": "근거", "evidence": "근거", "quote": "인용", "source": "출처", "sources": "출처",
    "question": "질문", "answer": "답변", "label": "라벨", "category": "분류", "type": "유형", "kind": "종류", "status": "상태",
    "industry": "업종", "sector": "업종", "product": "제품", "products": "제품", "model": "모델", "solution": "솔루션",
    "feature": "기능", "features": "기능", "spec": "스펙", "specs": "스펙", "requirement": "요구사항", "requirements": "요구사항",
    "need": "요구", "needs": "요구", "pain": "불편", "point": "포인트", "points": "포인트", "goal": "목표", "goals": "목표",
    "objective": "목표", "benefit": "효과", "benefits": "효과", "value": "가치", "risk": "리스크", "risks": "리스크",
    "issue": "이슈", "issues": "이슈", "insight": "인사이트", "insights": "인사이트", "recommendation": "추천",
    "recommendations": "추천", "action": "실행 항목", "actions": "실행 항목", "step": "단계", "steps": "단계",
    "location": "위치", "address": "주소", "region": "지역", "country": "국가", "city": "도시", "site": "현장", "space": "공간",
    "phone": "전화", "email": "이메일", "url": "URL", "link": "링크", "date": "날짜", "time": "시간", "year": "연도",
    "note": "메모", "notes": "메모", "comment": "코멘트", "keyword": "키워드", "keywords": "키워드", "tag": "태그", "tags": "태그",
    "price": "가격", "budget": "예산", "cost": "비용", "quantity": "수량", "qty": "수량", "unit": "단위", "size": "크기",
    "color": "색상", "style": "스타일", "scene": "장면", "prompt": "프롬프트", "caption": "캡션", "section": "섹션",
    "slide": "슬라이드", "page": "페이지", "owner": "담당자", "team": "팀", "project": "프로젝트", "language": "언어",
    "competitor": "경쟁사", "competitors": "경쟁사", "strength": "강점", "strengths": "강점", "weakness": "약점",
    "weaknesses": "약점", "opportunity": "기회", "threat": "위협", "metric": "지표", "metrics": "지표", "kpi": "KPI",
    "trend": "트렌드", "trends": "트렌드", "market": "시장", "segment": "세그먼트", "persona": "페르소나", "user": "사용자",
    "users": "사용자", "brand": "브랜드", "item": "항목", "items": "항목", "option": "옵션",
    "options": "옵션", "result": "결과", "results": "결과", "output": "결과", "claim": "주장", "claims": "주장",
    "fact": "사실", "facts": "사실", "object": "객체", "objects": "객체", "surface": "면", "surfaces": "면", "area": "영역",
    "areas": "영역", "role": "역할", "position": "직책", "department": "부서", "contact": "연락처", "schedule": "일정",
    "deadline": "마감", "version": "버전", "id": "ID", "code": "코드", "key": "키", "unit_price": "단가", "total": "합계",
    "first": "첫", "last": "마지막", "short": "짧은", "long": "긴", "main": "주요", "sub": "보조", "primary": "주",
    "secondary": "보조", "en": "영문", "ko": "국문", "korean": "국문", "english": "영문",
}
_SPLIT = re.compile(r"[_\-\s]+|(?<=[a-z0-9])(?=[A-Z])")
_HANGUL = re.compile(r"[가-힣]")


def _singular(name: str) -> str:
    if name.endswith("ies") and len(name) > 4:
        return name[:-3] + "y"
    if name.endswith("ses") or name.endswith("xes"):
        return name[:-2]
    if name.endswith("s") and not name.endswith("ss") and len(name) > 3:
        return name[:-1]
    return name


def ko_label(name: str, schema: dict[str, Any] | None = None) -> str:
    schema = schema or {}
    for key in ("title", "description"):
        v = schema.get(key)
        if isinstance(v, str) and _HANGUL.search(v) and len(v.strip()) <= 24:
            return v.strip().rstrip(".")
    if not name:
        return "값"
    tokens = [t for t in _SPLIT.split(name) if t]
    out = []
    for t in tokens:
        low = t.lower()
        out.append(KO.get(low) or KO.get(_singular(low)) or t)
    label = " ".join(out).strip()
    return label or name


def _esc(token: str) -> str:
    return str(token).replace("~", "~0").replace("/", "~1")


def from_regex(pattern: str, idx: int = 0) -> str | None:
    """정규식에 맞는 짧은 문자열(파서 트리를 따라 최소 반복으로). 못 만들면 None."""
    try:
        import re._parser as sre  # type: ignore[import-not-found]  # 3.11+
    except ImportError:  # pragma: no cover
        import sre_parse as sre  # type: ignore[no-redef]
    try:
        tree = sre.parse(pattern)
    except Exception:  # noqa: BLE001
        return None
    groups: dict[int, str] = {}
    try:
        from re import _constants as C  # type: ignore[attr-defined]  # 3.11+
    except ImportError:  # pragma: no cover
        import sre_constants as C  # type: ignore[no-redef]
    digit = str((idx + 1) % 10)

    def cls(items: list[tuple[Any, Any]]) -> str:
        negate = any(op is C.NEGATE for op, _ in items)
        allowed: list[str] = []
        banned: set[str] = set()
        ranges: list[tuple[int, int]] = []
        for op, av in items:
            if op is C.LITERAL:
                allowed.append(chr(av))
            elif op is C.RANGE:
                ranges.append(av)
                allowed.append(chr(av[0]))
            elif op is C.CATEGORY:
                allowed.append({C.CATEGORY_DIGIT: digit, C.CATEGORY_WORD: "a", C.CATEGORY_SPACE: " "}.get(av, "a"))
        if not negate:
            return allowed[0] if allowed else "a"
        banned = set(allowed)
        for cand in "aA0_ x-가":
            if cand in banned or any(lo <= ord(cand) <= hi for lo, hi in ranges):
                continue
            if any(op is C.CATEGORY and ((av == C.CATEGORY_DIGIT and cand.isdigit()) or (av == C.CATEGORY_WORD and (cand.isalnum() or cand == "_"))
                                         or (av == C.CATEGORY_SPACE and cand.isspace())) for op, av in items):
                continue
            return cand
        return "~"

    def gen(seq: Any) -> str:
        out = []
        for op, av in seq:
            if op is C.LITERAL:
                out.append(chr(av))
            elif op is C.NOT_LITERAL:
                out.append("a" if chr(av) != "a" else "b")
            elif op is C.ANY:
                out.append("a")
            elif op is C.IN:
                out.append(cls(av))
            elif op in (C.MAX_REPEAT, C.MIN_REPEAT, getattr(C, "POSSESSIVE_REPEAT", None)):
                lo, _hi, sub = av
                out.append(gen(sub) * max(lo, 0))
            elif op is C.SUBPATTERN:
                gid, sub = av[0], av[-1]
                text = gen(sub)
                if gid:
                    groups[gid] = text
                out.append(text)
            elif op is C.BRANCH:
                out.append(gen(av[1][0]))
            elif op is C.GROUPREF:
                out.append(groups.get(av, ""))
            elif op is C.CATEGORY:
                out.append({C.CATEGORY_DIGIT: digit, C.CATEGORY_WORD: "a", C.CATEGORY_SPACE: " "}.get(av, "a"))
            elif op in (C.AT, C.ASSERT, C.ASSERT_NOT):
                continue
            else:
                return out and "".join(out) or ""
        return "".join(out)

    try:
        return gen(tree)
    except Exception:  # noqa: BLE001
        return None


class Faker:
    def __init__(self, schema: dict[str, Any] | bool):
        self.root = schema if isinstance(schema, dict) else {}
        self.registry: Registry = Registry().with_resource(_URI, Resource.from_contents(self.root, default_specification=DRAFT202012))

    def make(self) -> Any:
        return self._gen(self.root, "", "", 0, 0)

    # ── 도우미 ─────────────────────────────────────────
    def _valid(self, value: Any, ptr: str | None) -> bool:
        if ptr is None:
            return True
        try:
            return Draft202012Validator({"$ref": f"{_URI}#{ptr}"}, registry=self.registry).is_valid(value)
        except Exception:  # noqa: BLE001
            return True

    def _resolve(self, ref: str) -> tuple[dict[str, Any], str | None]:
        if not ref.startswith("#"):
            return {}, None
        pointer = ref[1:]
        node: Any = self.root
        for raw in [p for p in pointer.split("/") if p != ""]:
            token = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and token in node:
                node = node[token]
            elif isinstance(node, list) and token.isdigit() and int(token) < len(node):
                node = node[int(token)]
            else:
                return {}, None
        return (node if isinstance(node, dict) else {}), pointer

    @staticmethod
    def _merge(parts: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for p in parts:
            for k, v in p.items():
                if k == "properties" and isinstance(v, dict):
                    out.setdefault("properties", {}).update(v)
                elif k == "required" and isinstance(v, list):
                    out["required"] = list(dict.fromkeys([*out.get("required", []), *v]))
                elif k in ("minimum", "minLength", "minItems", "exclusiveMinimum", "minProperties") and k in out:
                    out[k] = max(out[k], v)
                elif k in ("maximum", "maxLength", "maxItems", "exclusiveMaximum", "maxProperties") and k in out:
                    out[k] = min(out[k], v)
                else:
                    out[k] = v
        return out

    # ── 생성 ───────────────────────────────────────────
    def _gen(self, s: Any, name: str, ptr: str | None, depth: int, idx: int) -> Any:
        if s is True or s is None or s == {}:
            return self._string({}, name, idx)
        if s is False or not isinstance(s, dict):
            return None
        if depth > MAX_DEPTH + 6:
            return None
        if "$ref" in s:
            target, tptr = self._resolve(s["$ref"])
            siblings = {k: v for k, v in s.items() if k not in ("$ref", "description", "title", "default", "examples")}
            if siblings:
                return self._gen(self._merge([target, siblings]), name, None, depth + 1, idx)
            return self._gen(target, name, tptr, depth + 1, idx)
        if "const" in s:
            return copy.deepcopy(s["const"])
        if "enum" in s and isinstance(s["enum"], list) and s["enum"]:
            non_null = [v for v in s["enum"] if v is not None]
            return copy.deepcopy(non_null[0] if non_null else None)
        if "allOf" in s and isinstance(s["allOf"], list):
            parts = [{k: v for k, v in s.items() if k != "allOf"}]
            for sub in s["allOf"]:
                if isinstance(sub, dict) and "$ref" in sub:
                    target, _ = self._resolve(sub["$ref"])
                    parts.append({**target, **{k: v for k, v in sub.items() if k != "$ref"}})
                elif isinstance(sub, dict):
                    parts.append(sub)
            return self._gen(self._merge(parts), name, None, depth + 1, idx)
        for comb in ("anyOf", "oneOf"):
            if comb in s and isinstance(s[comb], list) and s[comb]:
                return self._combo(s, comb, name, ptr, depth, idx)
        t = s.get("type")
        if isinstance(t, list):
            non_null = [x for x in t if x != "null"]
            if not non_null:
                return None
            t = non_null[0]
        if t is None:
            if "properties" in s or "additionalProperties" in s or "required" in s:
                t = "object"
            elif "items" in s or "prefixItems" in s:
                t = "array"
            elif any(k in s for k in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf")):
                t = "number"
            else:
                t = "string"
        if t == "object":
            return self._object(s, name, ptr, depth, idx)
        if t == "array":
            return self._array(s, name, ptr, depth, idx)
        if t == "integer":
            return self._number(s, True, idx)
        if t == "number":
            return self._number(s, False, idx)
        if t == "boolean":
            return True
        if t == "null":
            return None
        return self._string(s, name, idx)

    def _combo(self, s: dict[str, Any], comb: str, name: str, ptr: str | None, depth: int, idx: int) -> Any:
        siblings = {k: v for k, v in s.items() if k not in (comb, "description", "title", "default", "examples")}
        branches = list(enumerate(s[comb]))
        # null 이 아닌 가지 먼저
        branches.sort(key=lambda b: 1 if isinstance(b[1], dict) and b[1].get("type") == "null" else 0)
        first: Any = None
        for i, br in branches:
            if not isinstance(br, dict):
                continue
            bptr = None if ptr is None or siblings else f"{ptr}/{comb}/{i}"
            sub = self._merge([siblings, br]) if siblings else br
            value = self._gen(sub, name, bptr, depth + 1, idx)
            if first is None:
                first = value
            if self._valid(value, ptr):
                return value
        return first

    def _object(self, s: dict[str, Any], name: str, ptr: str | None, depth: int, idx: int) -> dict[str, Any]:
        props = s.get("properties") or {}
        required = [r for r in (s.get("required") or []) if isinstance(r, str)]
        deep = depth >= MAX_DEPTH
        out: dict[str, Any] = {}
        for key, sub in props.items():
            if deep and key not in required:
                continue
            sptr = None if ptr is None else f"{ptr}/properties/{_esc(key)}"
            out[key] = self._gen(sub, key, sptr, depth + 1, idx)
        addl = s.get("additionalProperties")
        extra_schema: Any = addl if isinstance(addl, dict) else {"type": "string"}
        for key in required:
            if key not in out:
                out[key] = self._gen(extra_schema, key, None, depth + 1, idx)
        min_p = s.get("minProperties")
        if isinstance(min_p, int) and addl is not False:
            n = 1
            while len(out) < min_p:
                out[f"key{n}"] = self._gen(extra_schema, "key", None, depth + 1, n)
                n += 1
        max_p = s.get("maxProperties")
        if isinstance(max_p, int) and len(out) > max_p:
            for key in [k for k in list(out) if k not in required][::-1]:
                if len(out) <= max_p:
                    break
                out.pop(key)
        return out

    def _array(self, s: dict[str, Any], name: str, ptr: str | None, depth: int, idx: int) -> list[Any]:
        prefix = s.get("prefixItems")
        items = s.get("items")
        if isinstance(items, list):  # draft-07 튜플
            prefix, items = items, s.get("additionalItems", {})
        prefix = prefix if isinstance(prefix, list) else []
        min_n = int(s.get("minItems") or 0)
        max_n = s.get("maxItems")
        default_n = 2 if depth <= 4 else (1 if depth < MAX_DEPTH else 0)
        n = max(min_n, default_n, len(prefix))
        if items is False:
            n = min(n, len(prefix))
        if isinstance(max_n, int):
            n = min(n, max_n)
        item_name = _singular(name) if name else "item"
        out: list[Any] = []
        for i in range(n):
            if i < len(prefix):
                sptr = None if ptr is None else f"{ptr}/prefixItems/{i}"
                out.append(self._gen(prefix[i], item_name, sptr, depth + 1, i))
            else:
                sptr = None if ptr is None or not isinstance(items, dict) else f"{ptr}/items"
                out.append(self._gen(items if isinstance(items, dict) else {}, item_name, sptr, depth + 1, i))
        if s.get("uniqueItems"):
            out = self._uniq(out)
        return out

    @staticmethod
    def _uniq(values: list[Any]) -> list[Any]:
        import json

        seen: set[str] = set()
        result = []
        for i, v in enumerate(values):
            key = json.dumps(v, sort_keys=True, default=str)
            if key in seen:
                if isinstance(v, str):
                    v = f"{v} {i + 1}"
                elif isinstance(v, bool):
                    v = not v
                elif isinstance(v, (int, float)):
                    v = v + i
                key = json.dumps(v, sort_keys=True, default=str)
            seen.add(key)
            result.append(v)
        return result

    @staticmethod
    def _number(s: dict[str, Any], is_int: bool, idx: int) -> int | float:
        lo, hi = -math.inf, math.inf
        lo_ex = hi_ex = False
        if isinstance(s.get("minimum"), (int, float)):
            lo = float(s["minimum"])
            lo_ex = s.get("exclusiveMinimum") is True
        if isinstance(s.get("maximum"), (int, float)):
            hi = float(s["maximum"])
            hi_ex = s.get("exclusiveMaximum") is True
        em, eM = s.get("exclusiveMinimum"), s.get("exclusiveMaximum")
        if isinstance(em, (int, float)) and not isinstance(em, bool) and em >= lo:
            lo, lo_ex = float(em), True
        if isinstance(eM, (int, float)) and not isinstance(eM, bool) and eM <= hi:
            hi, hi_ex = float(eM), True
        mult = s.get("multipleOf")
        mult = float(mult) if isinstance(mult, (int, float)) and not isinstance(mult, bool) and mult > 0 else None

        def ok(v: float) -> bool:
            if v < lo or (lo_ex and v <= lo) or v > hi or (hi_ex and v >= hi):
                return False
            if mult is not None:
                q = v / mult
                if abs(q - round(q)) > 1e-9:
                    return False
            return True

        candidates: list[float] = []
        pref = [1.0 + idx, 0.0, 1.0] if is_int else [0.5 + idx, 0.0, 1.0]
        candidates += pref
        if math.isfinite(lo) and math.isfinite(hi):
            mid = (lo + hi) / 2
            candidates += [math.floor(mid), mid] if is_int else [mid]
        if math.isfinite(lo):
            candidates += [math.floor(lo) + 1, math.ceil(lo), lo + 1e-6 * max(1.0, abs(lo)), lo + 0.5]
        if math.isfinite(hi):
            candidates += [math.ceil(hi) - 1, math.floor(hi), hi - 1e-6 * max(1.0, abs(hi)), hi - 0.5]
        if mult is not None:
            base = math.ceil((lo if math.isfinite(lo) else 0.0) / mult) * mult
            candidates = [base + mult * idx, base, base + mult, *candidates]
        for c in candidates:
            v = float(round(c)) if is_int else float(c)
            if ok(v):
                return int(v) if is_int else (int(v) if v.is_integer() and mult is not None and float(mult).is_integer() else v)
        # 만족하는 값을 못 찾으면 하한(또는 0)
        if math.isfinite(lo):
            return int(math.ceil(lo)) if is_int else lo
        return 0 if is_int else 0.0

    @staticmethod
    def _string(s: dict[str, Any], name: str, idx: int) -> str:
        fmt = s.get("format")
        slug = re.sub(r"[^a-z0-9]+", "-", (name or "item").lower()).strip("-") or "item"
        suffix = f" {idx + 1}" if idx else ""
        formats = {
            "date": "2026-10-06", "date-time": "2026-10-06T09:00:00Z", "time": "09:00:00", "email": "mock@example.com",
            "idn-email": "mock@example.com", "uri": f"https://example.com/mock/{slug}{'-' + str(idx + 1) if idx else ''}",
            "url": f"https://example.com/mock/{slug}", "iri": f"https://example.com/mock/{slug}",
            "uri-reference": f"https://example.com/mock/{slug}", "iri-reference": f"https://example.com/mock/{slug}",
            "uuid": f"00000000-0000-4000-8000-{idx:012d}", "hostname": "example.com", "idn-hostname": "example.com",
            "ipv4": "192.0.2.1", "ipv6": "2001:db8::1", "duration": "P1D", "regex": ".*", "json-pointer": "/mock",
        }
        value = formats.get(fmt) if isinstance(fmt, str) else None
        if value is None:
            value = f"[mock] {ko_label(name, s)}{suffix}"
        pattern = s.get("pattern")
        if isinstance(pattern, str):
            try:
                rx = re.compile(pattern)
                if not rx.search(value):
                    gen = from_regex(pattern, idx)
                    if gen is not None and rx.search(gen):
                        value = gen
                    else:
                        for cand in (ko_label(name, s), slug, "mock", "MOCK", "A", "a", "0", "1", "2026-10-06", "KR"):
                            if rx.search(cand):
                                value = cand
                                break
            except re.error:
                pass
        min_len = s.get("minLength")
        max_len = s.get("maxLength")
        if isinstance(min_len, int) and len(value) < min_len:
            value = value + "가" * (min_len - len(value))
        if isinstance(max_len, int) and len(value) > max_len:
            value = value[:max_len]
        return value


def fake(schema: dict[str, Any] | bool) -> Any:
    """스키마에 맞는 결정적 가짜 값."""
    return Faker(schema).make()
