"""주장 검증(03-mi.md §7.6) — 모델 판단 없이 문자열 · 숫자 비교로만 상태를 정한다.

N() 정규화 → 수치 해석 → 인용 하나 검사(구절 · 수치 · 개체 · 날짜 · 텍스트 있음) → 주장 상태 모으기 → 숫자 지어내기 검사.
"""
from __future__ import annotations

import difflib
import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from . import config, rules

# ── 7.6.1 정규화 ─────────────────────────────────────────
_QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "«": '"', "»": '"', "「": '"', "」": '"', "‘": "'", "’": "'", "‚": "'",
                         "–": "-", "—": "-", "―": "-", "‐": "-", "‑": "-", "−": "-", "～": "~", "〜": "~"})
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_WS = re.compile(r"\s+")


def N(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_QUOTES).replace("…", "...")
    s = _THOUSANDS.sub("", s)
    s = _WS.sub(" ", s).strip()
    return s.lower()


def strip_ellipsis(q: str) -> str:
    q = (q or "").strip()
    q = re.sub(r"^(\.{3}|…)\s*", "", q)
    q = re.sub(r"\s*(\.{3}|…)$", "", q)
    return q.strip().strip('"“”').strip()


# ── 7.6.2 수치 해석 ──────────────────────────────────────
_BIG = {"만": 1e4, "억": 1e8, "조": 1e12, "천": 1e3}
_UNIT_ALIASES = [
    ("%p", "%p"), ("%", "%"), ("퍼센트", "%"),
    ("원", "원"), ("달러", "USD"), ("usd", "USD"), ("$", "USD"),
    ("개월", "개월"), ("개국", "개국"), ("개소", "개"), ("개", "개"), ("곳", "개"), ("매장", "개"), ("점포", "개"),
    ("대", "대"), ("명", "명"), ("가구", "가구"), ("실", "실"), ("건", "건"), ("배", "배"),
    ("년간", "년"), ("년", "년"),
    ("nit", "nit"), ("kw", "kW"), ("w", "W"), ("인치", "inch"), ('"', "inch"), ("형", "inch"), ("mm", "mm"), ("㎡", "㎡"), ("m2", "㎡"),
    ("kg", "kg"), ("시간", "시간"), ("분", "분"), ("초", "초"),
]
_NUM_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)(?:\s*(?:~|-|∼)\s*(?P<num2>\d+(?:\.\d+)?))?\s*(?P<big>만|억|조|천)?\s*(?P<big2>억|만)?\s*"
    r"(?P<unit>%p|%|퍼센트|원|달러|usd|\$|개월|개국|개소|개|곳|매장|점포|대(?![가-힣])|명|가구|실(?![가-힣])|건|배(?![가-힣])|년간|년|nit|kw|w(?![a-z])|인치|\"|형|mm|㎡|m2|kg|시간|분(?![가-힣])|초(?![가-힣]))?",
    re.IGNORECASE,
)


@dataclass
class Num:
    raw: str
    value: float
    unit: str
    kind: str = "num"          # num | year
    decimals: int = 0
    mult: float = 1.0
    start: int = 0
    end: int = 0
    value2: float | None = None


def _unit_of(u: str | None) -> str:
    if not u:
        return ""
    ul = u.lower()
    for k, v in _UNIT_ALIASES:
        if ul == k.lower():
            return v
    return u


def parse_numbers(text: str | None) -> list[Num]:
    """'1.2조 원' → 1.2e12 원 · '1,234억 원' → 1.234e11 원 · '42%' → 42 % · '2025년' → year 2025 · '3~5' → 두 값.
    자리표시([00] · [0,000])는 수치가 아니다."""
    if not text:
        return []
    s = unicodedata.normalize("NFKC", text)
    s = _THOUSANDS.sub("", s)
    # 자리표시 지우기(같은 길이로 가려 위치 유지)
    s = re.sub(r"\[[0-9,\.]+\]", lambda m: " " * len(m.group(0)), s)
    out: list[Num] = []
    for m in _NUM_RE.finditer(s):
        num_s = m.group("num")
        if m.start() > 0 and (s[m.start() - 1].isalnum() and not ("가" <= s[m.start() - 1] <= "힣")):
            # 모델코드 속 숫자(QM55C) 같은 것은 건너뛴다
            if re.match(r"[A-Za-z]", s[m.start() - 1]):
                continue
        try:
            v = float(num_s)
        except ValueError:
            continue
        dec = len(num_s.split(".")[1]) if "." in num_s else 0
        mult = 1.0
        for b in (m.group("big"), m.group("big2")):
            if b:
                mult *= _BIG[b]
        unit_raw = m.group("unit")
        unit = _unit_of(unit_raw)
        raw = m.group(0).strip()
        if unit == "년" and unit_raw and unit_raw.startswith("년") and 1900 <= v <= 2100 and dec == 0 and "년간" not in (unit_raw or ""):
            out.append(Num(raw=raw, value=v, unit="year", kind="year", start=m.start(), end=m.end()))
            continue
        if not unit and mult == 1.0 and 1900 <= v <= 2100 and dec == 0 and len(num_s) == 4:
            # '2025 시장' 처럼 년 없이 쓴 연도
            nxt = s[m.end():m.end() + 2]
            if not re.match(r"\s*\d", nxt):
                out.append(Num(raw=raw, value=v, unit="year", kind="year", start=m.start(), end=m.end()))
                continue
        if unit == "kW":
            mult *= 1000
            unit = "W"
        n2 = m.group("num2")
        v2 = float(n2) * mult if n2 else None
        out.append(Num(raw=raw, value=v * mult, unit=unit, decimals=dec, mult=mult, start=m.start(), end=m.end(), value2=v2))
    return out


def tolerance(n: Num) -> float:
    """max(값의 0.5%, 주장 표기 마지막 자리의 절반)."""
    last = 10 ** (-n.decimals) * n.mult
    return max(abs(n.value) * float(config.th("number_tolerance_ratio", 0.005)), last / 2)


def same_value(claim_n: Num, other: Num) -> bool:
    if claim_n.kind == "year" or other.kind == "year":
        return claim_n.kind == other.kind and claim_n.value == other.value
    if claim_n.unit != other.unit:
        return False
    tol = tolerance(claim_n)
    if abs(claim_n.value - other.value) <= tol:
        return True
    if other.value2 is not None and abs(claim_n.value - other.value2) <= tol:
        return True
    if claim_n.value2 is not None and abs(claim_n.value2 - other.value) <= tol:
        return True
    return False


def fmt_value(value: float, unit: str) -> str:
    """정규 값 → 화면 표기(1.234e11 원 → '1,234억 원')."""
    if unit == "원":
        if abs(value) >= 1e12:
            v = value / 1e12
            return f"{_num(v)}조 원"
        if abs(value) >= 1e8:
            return f"{_num(value / 1e8)}억 원"
        if abs(value) >= 1e4:
            return f"{_num(value / 1e4)}만 원"
        return f"{_num(value)}원"
    u = {"year": "년", "inch": "인치"}.get(unit, unit)
    sep = " " if unit in ("W", "nit", "mm", "kg") else ""
    return f"{_num(value)}{sep}{u}"


def _num(v: float) -> str:
    if abs(v - round(v)) < 1e-9:
        return f"{int(round(v)):,}"
    return f"{v:,.2f}".rstrip("0").rstrip(".")


# ── 7.6.3 인용 하나 검사 ─────────────────────────────────
REASONS = {
    "QUOTE_NOT_FOUND": "원문에서 이 구절을 찾지 못했어요.",
    "NUMBER_MISSING": "수치 없이 흐름만 말해 {num}{josa} 뒷받침하지 못해요.",
    "NUMBER_MISMATCH": "원문 값은 {num}{josa}에요.",
    "ENTITY_MISMATCH": "원문에 {name}{josa} 나오지 않아요.",
    "STALE": "{year}년 자료예요 · 더 최근 자료를 찾지 못했어요.",
    "DATE_UNKNOWN": "발행 시점을 확인하지 못했어요.",
    "FETCH_FAILED": "원문을 열지 못해 확인하지 못했어요.",
    "SUMMARY_ONLY": "검색 요약에서 나온 내용이라 원문과 대조하지 못했어요.",
    "SUMMARY_CORROBORATED": "검색 요약 2건이 같은 값을 말해요 · 원문은 확인 전이에요.",
    "KPI_TEXT_MISMATCH": "사례 원문과 문장이 달라요.",
    "NUMBER_UNSUPPORTED": "근거 구절에 없는 수치라 [00]으로 남겼어요.",
}


def reason_text(code: str, **kw: Any) -> str:
    t = REASONS.get(code, "")
    if code == "NUMBER_MISSING":
        num = kw.get("num", "")
        return t.format(num=num, josa=rules.josa(num, "을", "를"))
    if code == "NUMBER_MISMATCH":
        num = kw.get("num", "")
        return t.format(num=num, josa="이" if rules.has_batchim(num) else "")
    if code == "ENTITY_MISMATCH":
        name = kw.get("name", "")
        return t.format(name=name, josa=rules.josa(name, "이", "가"))
    if code == "STALE":
        return t.format(year=kw.get("year", "[0000]"))
    return t


def quote_check(quote: str, text: str) -> tuple[str, tuple[int, int] | None]:
    """N(구절) 이 N(텍스트)에 있으면 ok, 최장 공통 부분 ≥ 90% 면 partial, 아니면 fail."""
    q = N(strip_ellipsis(quote))
    t = N(text)
    if not q:
        return "fail", None
    i = t.find(q)
    if i >= 0:
        return "ok", (i, i + len(q))
    sm = difflib.SequenceMatcher(None, t, q, autojunk=False)
    m = sm.find_longest_match(0, len(t), 0, len(q))
    if m.size >= math.ceil(len(q) * float(config.th("quote_partial_ratio", 0.90))):
        return "partial", (m.a, m.a + m.size)
    return "fail", None


_MODEL_RE = re.compile(r"\b[A-Z]{1,4}\d{2,}[A-Z0-9]*\b")


def claim_entities(text: str, known_names: list[str] | None = None) -> list[str]:
    ents = list(dict.fromkeys(_MODEL_RE.findall(text or "")))
    for n in known_names or []:
        if n and n in (text or ""):
            ents.append(n)
    return ents


@dataclass
class CheckResult:
    check: dict[str, str]
    status: str
    reason_code: str | None = None
    reason_text: str = ""
    highlight: str | None = None
    quote_span: tuple[int, int] | None = None
    value: Num | None = None          # 이 인용이 말하는 주 수치(충돌 판정용)
    drop: bool = False                # 요약에 없는 구절 → 인용 버림(§7.6.4)
    unsupported: list[Num] = field(default_factory=list)


_DURATION_UNITS = ("년", "개월", "시간", "분", "초")


def _primary_numbers(nums: list[Num]) -> list[Num]:
    """연도를 빼고, 지표 수치를 먼저 · 기간(3년간 · 6개월)을 뒤로."""
    prim = [n for n in nums if n.kind != "year"]
    return sorted(prim, key=lambda n: 1 if n.unit in _DURATION_UNITS else 0)


def highlight_for(quote: str, claim_nums: list[Num]) -> str | None:
    """주장 수치가 든 부분(수치 + 다음 낱말 하나, 예 '42% 증가')."""
    q = strip_ellipsis(quote)
    for cn in _primary_numbers(claim_nums):
        for qn in parse_numbers(q):
            if same_value(cn, qn):
                end = qn.end
                rest = q[end:]
                mm = re.match(r"\s*[가-힣A-Za-z]+", rest)
                if mm:
                    end += mm.end()
                return q[qn.start:end].strip()
    return None


def check_citation(*, claim_text: str, quote: str, source: dict[str, Any], source_text: str | None,
                   page_text: str | None = None, known_names: list[str] | None = None, ref: datetime | None = None) -> CheckResult:
    kind = source.get("kind")
    claim_nums = parse_numbers(claim_text)
    check = {"quote": "na", "numbers": "na", "entities": "na", "date": "unknown"}
    if kind == "user":
        return CheckResult(check={"quote": "na", "numbers": "na", "entities": "na", "date": "ok"}, status="matched")
    text = page_text if page_text else source_text
    if kind == "websearch_summary":
        qs, span = quote_check(quote, text or "")
        if qs == "fail":
            return CheckResult(check={**check, "quote": "fail"}, status="unverifiable", reason_code="QUOTE_NOT_FOUND",
                               reason_text=reason_text("QUOTE_NOT_FOUND"), drop=True)
        check["quote"] = qs
        qnums = parse_numbers(quote)
        unsupported = [n for n in _primary_numbers(claim_nums) if not any(same_value(n, q) for q in qnums)]
        check["numbers"] = "na" if not _primary_numbers(claim_nums) else ("ok" if not unsupported else "missing")
        pub = source.get("published_at")
        check["date"] = "unknown" if not pub else ("stale" if rules.is_stale(pub, ref) else "ok")
        val = _value_for(claim_nums, qnums)
        return CheckResult(check=check, status="unverifiable", reason_code="SUMMARY_ONLY", reason_text=reason_text("SUMMARY_ONLY"),
                           highlight=highlight_for(quote, claim_nums) if qs == "ok" else None, quote_span=span, value=val,
                           unsupported=unsupported)
    if not text:
        code = "SUMMARY_ONLY" if kind == "websearch_summary" else "FETCH_FAILED"
        qnums = parse_numbers(quote)
        return CheckResult(check={**check, "quote": "na"}, status="unverifiable", reason_code=code, reason_text=reason_text(code),
                           value=_value_for(claim_nums, qnums))
    qs, span = quote_check(quote, text)
    check["quote"] = qs
    qnums = parse_numbers(quote) if qs != "fail" else []
    reasons: list[tuple[str, str]] = []
    if qs == "fail":
        reasons.append(("QUOTE_NOT_FOUND", reason_text("QUOTE_NOT_FOUND")))
    prim = _primary_numbers(claim_nums)
    years = [n for n in claim_nums if n.kind == "year"]
    num_status = "na"
    if prim or years:
        missing: list[Num] = []
        mismatch: list[tuple[Num, Num]] = []
        for n in prim:
            if any(same_value(n, q) for q in qnums):
                continue
            same_unit = [q for q in qnums if q.unit == n.unit and q.kind != "year"]
            if same_unit:
                mismatch.append((n, min(same_unit, key=lambda q: abs(q.value - n.value))))
            else:
                missing.append(n)
        q_years = [q for q in qnums if q.kind == "year"]
        if q_years:
            for y in years:
                if not any(q.value == y.value for q in q_years):
                    mismatch.append((y, q_years[0]))
        if mismatch:
            num_status = "mismatch"
            q = mismatch[0][1]
            reasons.append(("NUMBER_MISMATCH", reason_text("NUMBER_MISMATCH", num=fmt_value(q.value, q.unit) if q.kind != "year" else q.raw)))
        elif missing:
            num_status = "missing"
            reasons.append(("NUMBER_MISSING", reason_text("NUMBER_MISSING", num=missing[0].raw)))
        else:
            num_status = "ok" if prim or q_years else "na"
    check["numbers"] = num_status
    ents = claim_entities(claim_text, known_names)
    if ents:
        hay = N(text)
        missing_ent = [e for e in ents if N(e) not in hay and not _alias_hit(e, source)]
        check["entities"] = "fail" if missing_ent else "ok"
        if missing_ent:
            reasons.append(("ENTITY_MISMATCH", reason_text("ENTITY_MISMATCH", name=missing_ent[0])))
    pub = source.get("published_at")
    if pub:
        if rules.is_stale(pub, ref):
            check["date"] = "stale"
        else:
            check["date"] = "ok"
    else:
        check["date"] = "unknown"
    date_reason: tuple[str, str] | None = None
    if check["date"] == "stale":
        y = (rules.parse_iso(pub) or datetime.now()).year
        date_reason = ("STALE", reason_text("STALE", year=y))
    elif check["date"] == "unknown" and prim and kind not in ("kb_official", "kb_case", "file"):
        date_reason = ("DATE_UNKNOWN", reason_text("DATE_UNKNOWN"))
    if kind == "kb_case" and source.get("tier") == "T5" and qs == "fail":
        reasons = [("KPI_TEXT_MISMATCH", reason_text("KPI_TEXT_MISMATCH"))]
    val = _value_for(claim_nums, qnums)
    hl = highlight_for(quote, claim_nums) if qs == "ok" else None
    if not reasons and date_reason is None:
        return CheckResult(check=check, status="matched", highlight=hl, quote_span=span, value=val)
    if not reasons and date_reason and date_reason[0] == "STALE":
        return CheckResult(check=check, status="stale", reason_code="STALE", reason_text=date_reason[1], highlight=hl,
                           quote_span=span, value=val)
    code, txt = reasons[0] if reasons else date_reason  # type: ignore[misc]
    unsupported = [n for n in prim if not any(same_value(n, q) for q in qnums)]
    return CheckResult(check=check, status="needs_check", reason_code=code, reason_text=txt, highlight=hl, quote_span=span,
                       value=val, unsupported=unsupported)


def _alias_hit(name: str, source: dict[str, Any]) -> bool:
    for a in source.get("aliases") or []:
        if N(a) == N(name):
            return True
    return False


def _value_for(claim_nums: list[Num], qnums: list[Num]) -> Num | None:
    prim = _primary_numbers(claim_nums)
    if not prim:
        return None
    target = prim[0]
    same = [q for q in qnums if q.unit == target.unit and q.kind != "year"]
    if not same:
        return None
    return min(same, key=lambda q: abs(q.value - target.value))


# ── 7.6.5 주장 상태 모으기 ───────────────────────────────
def diff_ratio(a: float, b: float) -> float:
    lo = min(abs(a), abs(b))
    if lo == 0:
        return math.inf if a != b else 0.0
    return abs(a - b) / lo


def pick_primary(values: list[dict[str, Any]]) -> dict[str, Any]:
    """주 값 = 발행일이 가장 최근(날짜 모름은 뒤로), 같으면 공신력 숫자가 작은 출처."""
    def key(v: dict[str, Any]) -> tuple[int, str, int]:
        pub = v.get("published_at") or ""
        return (0 if pub else 1, "".join(chr(255 - ord(c)) for c in pub) if pub else "", int(v.get("authority") or 9))
    return sorted(values, key=key)[0]


CLAIM_LABEL = {"matched": "원문 일치", "conflict": "출처 간 값 다름", "stale": "자료 연도 오래됨", "confirmed": "확정",
               "checking": "확인 중", "missing": "확인 필요"}


def claim_label(status: str, n_needs: int = 0) -> str:
    if status == "needs_check":
        return f"확인 필요 {max(1, n_needs)}"
    return CLAIM_LABEL.get(status, "확인 필요")


def aggregate(claim: dict[str, Any], citations: list[dict[str, Any]], sources: dict[str, dict[str, Any]], *,
              confirmed: bool = False, checking: bool = False) -> dict[str, Any]:
    """§7.6.5 — 위에서부터 먼저 걸리는 것. 돌려주는 값: {status, label, n_needs, conflict?}."""
    if confirmed:
        return {"status": "confirmed", "label": claim_label("confirmed"), "n_needs": 0, "conflict": None}
    if checking:
        return {"status": "checking", "label": claim_label("checking"), "n_needs": 0, "conflict": None}
    cits = [c for c in citations if not c.get("dropped")]
    if not cits:
        return {"status": "missing", "label": claim_label("missing"), "n_needs": 0, "conflict": None}
    # 충돌: 같은 지표 값끼리 차이 ≥ 20%
    vals = []
    for c in cits:
        v = c.get("value")
        if v is None:
            continue
        src = sources.get(c["source_id"], {})
        vals.append({"source_id": c["source_id"], "value": v["value"], "unit": v["unit"], "raw": v.get("raw"),
                     "published_at": src.get("published_at"), "authority": src.get("authority", 5)})
    conflict = None
    if len(vals) >= 2:
        by_src: dict[str, dict[str, Any]] = {}
        for v in vals:
            by_src.setdefault(v["source_id"], v)
        uniq = list(by_src.values())
        if len(uniq) >= 2:
            ratio = max(diff_ratio(a["value"], b["value"]) for i, a in enumerate(uniq) for b in uniq[i + 1:] if a["unit"] == b["unit"]) \
                if any(a["unit"] == b["unit"] for i, a in enumerate(uniq) for b in uniq[i + 1:]) else 0.0
            if ratio >= float(config.th("conflict_ratio", 0.20)) - 1e-9:
                primary = pick_primary(uniq)
                conflict = {"values": uniq, "primary_source_id": primary["source_id"], "diff_ratio": round(ratio, 2)}
    if conflict:
        return {"status": "conflict", "label": claim_label("conflict"), "n_needs": 0, "conflict": conflict}
    statuses = [c.get("status") for c in cits]
    if all(s == "stale" for s in statuses):
        return {"status": "stale", "label": claim_label("stale"), "n_needs": 0, "conflict": None}
    n_needs = sum(1 for s in statuses if s != "matched")
    if n_needs:
        return {"status": "needs_check", "label": claim_label("needs_check", n_needs), "n_needs": n_needs, "conflict": None}
    return {"status": "matched", "label": claim_label("matched"), "n_needs": 0, "conflict": None}


def prune_summary_citations(citations: list[dict[str, Any]], sources: dict[str, dict[str, Any]]) -> list[str]:
    """주장에 matched 인용이 있으면 같은 수치만 되풀이하는 websearch_summary 인용을 떼어 낸다. 떼어 낸 출처 id 를 돌려준다."""
    live = [c for c in citations if not c.get("dropped")]
    if not any(c.get("status") == "matched" for c in live):
        return []
    removed = []
    for c in live:
        src = sources.get(c["source_id"], {})
        if src.get("kind") == "websearch_summary":
            c["dropped"] = True
            c["dropped_reason"] = "superseded"
            removed.append(c["source_id"])
    return removed


# ── 7.6.6 숫자 지어내기 검사 ─────────────────────────────
def supported_by(n: Num, citations: list[dict[str, Any]]) -> bool:
    for c in citations:
        if c.get("dropped"):
            continue
        for q in parse_numbers(c.get("quote") or ""):
            if same_value(n, q):
                return True
    return False


def mask_unsupported(text: str, citations: list[dict[str, Any]], *, confirmed_values: list[str] | None = None) -> tuple[str, list[Num]]:
    """근거 구절에 없는 수치를 `[00]{단위}` 로 바꾼다(연도는 바꾸지 않는다). (새 문장, 바꾼 수치)."""
    nums = parse_numbers(text)
    bad: list[Num] = []
    for n in nums:
        if n.kind == "year":
            continue
        if confirmed_values and any(n.raw in cv for cv in confirmed_values):
            continue
        if not supported_by(n, citations):
            bad.append(n)
    if not bad:
        return text, []
    out = text
    for n in bad:
        out = _raw_regex(n.raw).sub(lambda _m, n=n: placeholder_for(n), out, count=1)
    return out, bad


def _raw_regex(raw: str) -> re.Pattern[str]:
    """정규화된 수치 표기(쉼표 없음) → 원문에서 찾는 정규식(숫자 사이 쉼표 · 공백 허용)."""
    parts = []
    for ch in raw:
        if ch.isdigit():
            parts.append(re.escape(ch) + ",?")
        elif ch.isspace():
            parts.append(r"\s*")
        else:
            parts.append(re.escape(ch))
    pat = "".join(parts).replace(",?" + r"\.", r"\.")
    return re.compile(r"(?<![\d,])" + pat)


def placeholder_for(n: Num) -> str:
    """수치 → 자리표시(단위 유지): '5,000억 원' → '[00]억 원', '42%' → '[00]%'."""
    raw = n.raw
    m = re.match(r"\d[\d\.,]*(?:\s*(?:~|-|∼)\s*\d[\d\.,]*)?", raw)
    rest = raw[m.end():] if m else ""
    return "[00]" + rest


def metric_value(claim: dict[str, Any]) -> tuple[float | None, str]:
    nums = [n for n in parse_numbers(claim.get("text", "")) if n.kind != "year"]
    if not nums:
        return None, ""
    return nums[0].value, nums[0].unit


def num_to_dict(n: Num | None) -> dict[str, Any] | None:
    if n is None:
        return None
    return {"raw": n.raw, "value": n.value, "unit": n.unit, "kind": n.kind}
