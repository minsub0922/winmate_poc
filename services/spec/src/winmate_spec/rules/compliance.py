"""고객 요구 대응표(SP1R) — 인용 검증 · 정규 키 · 판정(06-spec §4.6.3 · §7.11, 결정적 우선)."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from .fmt import GRADE_ALIASES, fmt_num, grade_label, numbers
from .values import attr, attr_like, is_none_value

ALLOWED_KEYS = {"screen_size_inch", "screen_size_cm", "brightness_nit", "operation_hours", "weight_kg", "power_consumption",
                "operating_temp_c", "resolution", "warranty_years", "wifi", "bezel_mm"}
LOWER_IS_BETTER = {"power_consumption", "weight_kg", "bezel_mm"}


def norm_ws(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    return re.sub(r"\s+", "", s)


def quote_ok(quote: str, page_text: str) -> bool:
    """인용이 그 쪽 텍스트 안에 그대로 있는가(공백 정규화)."""
    q = norm_ws(quote)
    return bool(q) and q in norm_ws(page_text)


def numbers_ok(requirement: str, quote: str) -> bool:
    """요구 문장의 숫자가 인용의 숫자 집합 안에 있는가."""
    req = set(numbers(unicodedata.normalize("NFKC", requirement)))
    qs = set(numbers(unicodedata.normalize("NFKC", quote)))
    return req <= qs


def op_of(text: str, default: str = ">=") -> str:
    t = text or ""
    if re.search(r"이하|최대|넘지|under|max|≤", t, re.I):
        return "<="
    if re.search(r"이상|최소|넘는|over|min|≥", t, re.I):
        return ">="
    if re.search(r"미만", t):
        return "<"
    if re.search(r"초과", t):
        return ">"
    return default


def _cmp(a: float, op: str, b: float) -> bool:
    return {">=": a >= b, "<=": a <= b, ">": a > b, "<": a < b, "==": a == b}.get(op, a >= b)


def model_value(spec: dict[str, Any], key: str) -> tuple[float | None, str | None, dict[str, Any] | None]:
    """정규 키 → (비교 수치, 표시 글, 근거). 값이 여럿인 키는 속성 이름으로 고른다(§4.15.4)."""
    d = spec.get("derived") or {}
    if key in ("screen_size_inch", "screen_size_cm"):
        inch = spec.get("size_inch") or d.get("screen_size_inch")
        a = attr(spec, "디스플레이", "대각선 사이즈 (cm)")
        if key == "screen_size_cm":
            cm = d.get("screen_size_cm") or (a or {}).get("num")
            return (float(cm) if cm is not None else None), (f"{fmt_num(cm)} cm" if cm is not None else None), a
        return (float(inch) if inch else None), (f'{inch}"' if inch else None), a
    if key == "brightness_nit":
        nit = d.get("brightness_typ_nit")
        a = attr(spec, "디스플레이", "밝기 (Typ)")
        return (float(nit) if nit is not None else None), (f"{fmt_num(nit)} nit" if nit is not None else None), a
    if key == "operation_hours":
        a = attr(spec, "디스플레이", "제품 사용 시간")
        if not a:
            return None, None, None
        h = a.get("num") if a.get("num") is not None else (numbers(a.get("raw")) or [None])[0]
        return (float(h) if h is not None else None), a["raw"].strip(), a
    if key == "weight_kg":
        a = attr(spec, "무게", "제품 무게")
        s = d.get("weight_kg_set") if d.get("weight_kg_set") is not None else (a or {}).get("num")
        return (float(s) if s is not None else None), (f"{fmt_num(s)} kg" if s is not None else None), a
    if key == "power_consumption":
        for name, a in attr_like(spec, "전원", r"소비전력"):
            if re.search(r"Typical|Typ\b|일반|정격", name, re.I):
                return a.get("num"), f"{fmt_num(a.get('num'))} W", a
        return None, None, None
    if key == "bezel_mm":
        a = attr(spec, "기구사양", "베젤 두께")
        n = (numbers((a or {}).get("raw")) or [None])[0]
        return n, ((a or {}).get("raw") or None), a
    if key == "warranty_years":
        w = spec.get("warranty_catalog") or {}
        y = w.get("years")
        return (float(y) if y is not None else None), (f"{fmt_num(y)}년" if y is not None else None), None
    return None, None, None


def alt_power_note(spec: dict[str, Any]) -> str | None:
    for name, a in attr_like(spec, "전원", r"소비전력"):
        if re.search(r"On Mode", name, re.I):
            return f"On Mode {fmt_num(a.get('num'))} W만 있음"
    return None


def evaluate_row(req: dict[str, Any], spec: dict[str, Any] | None, *, warranty: dict[str, Any] | None = None) -> dict[str, Any]:
    """요구 행 하나 판정. req: {kind, key, op, value, value2, unit, capabilities, item, requirement}. 근거 없으면 unknown."""
    kind = req.get("kind") or "text"
    if kind == "procedural":
        return {"verdict": "unknown", "value_text": "—", "note": "담당 부서 확인"}
    if spec is None:
        return {"verdict": "unknown", "value_text": "—", "note": "카탈로그에 값 없음"}
    key = req.get("key")
    if kind == "grade" or key == "resolution":
        target = GRADE_ALIASES.get((req.get("grade") or "").upper())
        res = (spec.get("derived") or {}).get("resolution") or {}
        w, h = res.get("w"), res.get("h")
        if not w or not h:
            return {"verdict": "unknown", "value_text": "—", "note": "카탈로그에 값 없음"}
        label = grade_label(w, h) or f"{w}×{h}"
        if not target:
            return {"verdict": "unknown", "value_text": label, "note": "요구 수치 없음"}
        ok = w * h >= target[0] * target[1]
        return {"verdict": "pass" if ok else "fail", "value_text": label, "note": None}
    caps = req.get("capabilities") or []
    if kind == "capability" and caps:
        return _capability(caps, spec, req)
    if key == "wifi":
        a = attr(spec, "연결성", "WiFi")
        if not a:
            return {"verdict": "unknown", "value_text": "—", "note": "카탈로그에 값 없음"}
        return {"verdict": "fail" if is_none_value(a["raw"]) else "pass", "value_text": "Wi-Fi" if not is_none_value(a["raw"]) else "없음",
                "note": None, "evidence": a}
    if key == "operating_temp_c":
        a = attr(spec, "동작조건", "온도")
        if not a or a.get("num") is None or a.get("num2") is None:
            return {"verdict": "unknown", "value_text": "—", "note": "카탈로그에 값 없음"}
        lo, hi = float(a["num"]), float(a["num2"])
        rlo, rhi = req.get("value"), req.get("value2")
        if rlo is None or rhi is None:
            return {"verdict": "unknown", "value_text": a["raw"], "note": "요구 수치 없음"}
        ok = lo <= float(rlo) and hi >= float(rhi)
        return {"verdict": "pass" if ok else "fail", "value_text": a["raw"], "note": None, "evidence": a}
    if key == "warranty_years":
        y = (spec.get("warranty_catalog") or {}).get("years")
        if y is None and warranty:
            y = warranty.get("years")
        if y is None:
            return {"verdict": "unknown", "value_text": "—", "note": "카탈로그에 값 없음"}
        if req.get("value") is None:
            return {"verdict": "unknown", "value_text": f"{fmt_num(y)}년", "note": "요구 수치 없음"}
        ok = _cmp(float(y), req.get("op") or ">=", float(req["value"]))
        return {"verdict": "pass" if ok else "fail", "value_text": f"{fmt_num(y)}년", "note": None}
    if key in ALLOWED_KEYS:
        v, text, a = model_value(spec, key)
        if v is None:
            note = alt_power_note(spec) if key == "power_consumption" else None
            return {"verdict": "unknown", "value_text": "—", "note": note or "카탈로그에 값 없음"}
        if req.get("value") is None:
            return {"verdict": "unknown", "value_text": text or "—", "note": "요구 수치 없음"}
        op = req.get("op") or ("<=" if key in LOWER_IS_BETTER else ">=")
        ok = _cmp(float(v), op, float(req["value"]))
        return {"verdict": "pass" if ok else "fail", "value_text": text or "—", "note": None, "evidence": a}
    return {"verdict": "unknown", "value_text": "—", "note": None}


def _capability(caps: list[str], spec: dict[str, Any], req: dict[str, Any]) -> dict[str, Any]:
    for cap in caps:
        if cap == "cap_continuous_operation":
            a = attr(spec, "디스플레이", "제품 사용 시간")
            if not a:
                continue
            h = a.get("num") if a.get("num") is not None else (numbers(a.get("raw")) or [None])[0]
            if h is None:
                continue
            return {"verdict": "pass" if float(h) >= 24 else "fail", "value_text": a["raw"].strip(), "note": None, "evidence": a}
        if cap == "cap_remote_content_mgmt":
            for s in spec.get("solutions") or []:
                if (s.get("name") or "").lower() in ("magicinfo", "vxt") or "magicinfo" in (s.get("id") or ""):
                    return {"verdict": "pass", "value_text": s.get("name") or "MagicINFO", "note": None,
                            "evidence": {"raw": s.get("evidence_text"), "id": s.get("kb_id")}}
            for p in spec.get("provides") or []:
                if p.get("capability_id") == cap:
                    name = "MagicINFO" if "magicinfo" in (p.get("evidence") or "").lower() else ("VXT" if "vxt" in (p.get("evidence") or "").lower() else "원격 관리")
                    return {"verdict": "pass", "value_text": name, "note": None, "evidence": {"raw": p.get("evidence"), "id": cap}}
            continue
        if any(p.get("capability_id") == cap for p in spec.get("provides") or []):
            ev = next(p for p in spec.get("provides") or [] if p.get("capability_id") == cap)
            return {"verdict": "pass", "value_text": ev.get("evidence") or cap, "note": None, "evidence": {"raw": ev.get("evidence"), "id": cap}}
    return {"verdict": "unknown", "value_text": "—", "note": "카탈로그에 근거 없음"}


def counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {"pass": len([r for r in rows if r.get("verdict") == "pass"]), "fail": len([r for r in rows if r.get("verdict") == "fail"]),
            "unknown": len([r for r in rows if r.get("verdict") == "unknown"])}


def agent_text(n: int, model: str, c: dict[str, int], has_alt: bool) -> str:
    s = f"규격서에서 요구 항목 {n}개를 찾아 {model} 스펙과 맞춰 봤습니다. 충족 {c['pass']} · 미충족 {c['fail']} · 확인 필요 {c['unknown']}입니다."
    if c["fail"] >= 1 and has_alt:
        s += " 미충족 항목에는 대안 모델을 함께 붙였어요."
    return s


def folded_line(rows: list[dict[str, Any]], shown: int = 8) -> str | None:
    rest = rows[shown:]
    if not rest:
        return None
    c = counts(rest)
    parts = [f"{len(rest)}개 더"]
    for k, lab in (("pass", "충족"), ("fail", "미충족"), ("unknown", "확인 필요")):
        if c[k]:
            parts.append(f"{lab} {c[k]}")
    return " · ".join(parts)


def requirement_items_to_item_keys(rows: list[dict[str, Any]]) -> list[str]:
    from .items import REQ_KEY_TO_ITEM
    out: list[str] = []
    for r in rows:
        keys = [r.get("key")] + list(r.get("capabilities") or [])
        for k in keys:
            ik = REQ_KEY_TO_ITEM.get(k or "")
            if ik and ik not in out:
                out.append(ik)
    return out
