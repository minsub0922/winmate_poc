"""주장 검증(03-mi.md §7.6 을 같은 규칙으로 자체 구현) — 모델 판단 없이 문자열 · 숫자 비교로만 상태를 정한다.

N() 정규화 → 수치 해석 → 인용 하나 검사(구절 · 수치 · 날짜 · 텍스트 있음) → 주장 상태 모으기 → 숫자 지어내기 검사.
웹 검색 요약은 어떤 경우에도 `matched` 가 아니다(`unverifiable` · SUMMARY_ONLY).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any

from . import config, rules

_QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "「": '"', "」": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "―": "-",
                         "‐": "-", "‑": "-", "−": "-", "～": "~", "〜": "~"})
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


# ── 수치 ─────────────────────────────────────────────────
_BIG = {"천": 1e3, "만": 1e4, "억": 1e8, "조": 1e12}
_UNITS = [("%p", "%p"), ("%", "%"), ("퍼센트", "%"), ("원", "원"), ("달러", "USD"), ("usd", "USD"), ("개월", "개월"), ("개국", "개국"),
          ("개소", "개"), ("개", "개"), ("곳", "개"), ("매장", "개"), ("점포", "개"), ("대", "대"), ("명", "명"), ("건", "건"), ("배", "배"),
          ("년간", "년"), ("년", "년"), ("nit", "nit"), ("kw", "kW"), ("w", "W"), ("인치", "inch"), ('"', "inch"), ("형", "inch"),
          ("mm", "mm"), ("㎡", "㎡"), ("kg", "kg"), ("시간", "시간"), ("분", "분"), ("초", "초")]
_NUM_RE = re.compile(
    r"(?P<num>\d+(?:\.\d+)?)(?:\s*(?:~|∼)\s*(?P<num2>\d+(?:\.\d+)?))?\s*(?P<big>천|만|억|조)?\s*(?P<big2>억|만)?\s*"
    r"(?P<unit>%p|%|퍼센트|원|달러|usd|개월|개국|개소|개|곳|매장|점포|대(?![가-힣])|명|건|배(?![가-힣])|년간|년|nit|kw|w(?![a-z])|인치|\"|형|mm|㎡|kg|시간|분(?![가-힣])|초(?![가-힣]))?",
    re.IGNORECASE,
)


@dataclass
class Num:
    raw: str
    value: float
    unit: str
    kind: str = "num"
    decimals: int = 0
    mult: float = 1.0
    start: int = 0
    end: int = 0
    value2: float | None = None


def _unit(u: str | None) -> str:
    if not u:
        return ""
    for k, v in _UNITS:
        if u.lower() == k.lower():
            return v
    return u


def parse_numbers(text: str | None) -> list[Num]:
    """'1.2조 원' → 1.2e12 원, '월 3만 원' → 3e4 원, '2025년' → year, 모델코드 속 숫자(QM55C)는 건너뛴다. 자리표시([00])는 수치가 아니다."""
    if not text:
        return []
    s = unicodedata.normalize("NFKC", text)
    s = _THOUSANDS.sub("", s)
    s = re.sub(r"\[[0-9,\.]+\]", lambda m: " " * len(m.group(0)), s)
    out: list[Num] = []
    for m in _NUM_RE.finditer(s):
        if m.start() > 0 and re.match(r"[A-Za-z]", s[m.start() - 1]):
            continue
        num_s = m.group("num")
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
        unit = _unit(unit_raw)
        raw = m.group(0).strip()
        if unit == "년" and unit_raw and unit_raw.startswith("년") and unit_raw != "년간" and 1900 <= v <= 2100 and dec == 0:
            out.append(Num(raw=raw, value=v, unit="year", kind="year", start=m.start(), end=m.end()))
            continue
        if not unit and mult == 1.0 and 1900 <= v <= 2100 and dec == 0 and len(num_s) == 4:
            out.append(Num(raw=raw, value=v, unit="year", kind="year", start=m.start(), end=m.end()))
            continue
        if unit == "kW":
            mult *= 1000
            unit = "W"
        v2 = float(m.group("num2")) * mult if m.group("num2") else None
        out.append(Num(raw=raw, value=v * mult, unit=unit, decimals=dec, mult=mult, start=m.start(), end=m.end(), value2=v2))
    return out


def _tol(n: Num) -> float:
    last = 10 ** (-n.decimals) * n.mult
    return max(abs(n.value) * config.th("number_tolerance_ratio", 0.005), last / 2)


def same_value(a: Num, b: Num) -> bool:
    if a.kind == "year" or b.kind == "year":
        return a.kind == b.kind and a.value == b.value
    if a.unit and b.unit and a.unit != b.unit:
        return False
    if (a.unit or b.unit) and not (a.unit and b.unit) and a.mult == 1 and b.mult == 1:
        # 단위가 한쪽만 있는 작은 정수(예 '55' 와 '55인치')는 같은 값으로 본다
        pass
    tol = _tol(a)
    if abs(a.value - b.value) <= tol:
        return True
    if b.value2 is not None and abs(a.value - b.value2) <= tol:
        return True
    return False


def numbers_supported(claim_text: str, evidence_text: str) -> tuple[list[Num], list[Num]]:
    """주장 속 수치 중 근거 글에 있는 것 · 없는 것."""
    ev = parse_numbers(evidence_text)
    ok, bad = [], []
    for n in parse_numbers(claim_text):
        (ok if any(same_value(n, e) for e in ev) else bad).append(n)
    return ok, bad


# ── 인용 하나 검사(§7.6.3) ───────────────────────────────
REASONS = {
    "QUOTE_NOT_FOUND": "원문에서 이 구절을 찾지 못했어요.",
    "NUMBER_MISSING": "수치 없이 흐름만 말해 {num}{josa} 뒷받침하지 못해요.",
    "NUMBER_MISMATCH": "원문 값은 {num}{josa}에요.",
    "STALE": "{year}년 자료예요 · 더 최근 자료를 찾지 못했어요.",
    "DATE_UNKNOWN": "발행 시점을 확인하지 못했어요.",
    "FETCH_FAILED": "원문을 열지 못해 확인하지 못했어요.",
    "SUMMARY_ONLY": "검색 요약에서 나온 내용이라 원문과 대조하지 못했어요.",
    "NUMBER_UNSUPPORTED": "근거 구절에 없는 수치라 [00]으로 남겼어요.",
}


def reason_text(code: str | None, **kw: Any) -> str:
    if not code:
        return ""
    t = REASONS.get(code, "")
    if code == "NUMBER_MISSING":
        num = kw.get("num", "")
        return t.format(num=num, josa=rules.josa(num, "을", "를"))
    if code == "NUMBER_MISMATCH":
        num = kw.get("num", "")
        return t.format(num=num, josa="이" if rules.has_batchim(num) else "")
    if code == "STALE":
        return t.format(year=kw.get("year", "[0000]"))
    return t


def _quote_in(quote: str, text: str) -> str:
    """ok · partial(최장 공통 부분 ≥ 90%) · fail."""
    q = N(strip_ellipsis(quote))
    t = N(text)
    if not q or not t:
        return "fail"
    if q in t:
        return "ok"
    # 최장 공통 부분 문자열(짧은 구절만, 비용 제한)
    if len(q) <= 400:
        best = 0
        for i in range(len(q)):
            for j in range(len(q), i + best, -1):
                if q[i:j] in t:
                    best = max(best, j - i)
                    break
        if best >= 0.9 * len(q):
            return "partial"
    return "fail"


def check_citation(claim_text: str, quote: str, source: dict[str, Any], text: str | None, *, today: date | None = None) -> dict[str, Any]:
    """→ {status: matched|needs_check|unverifiable|stale|dropped, check{}, reason_code, reason_text, highlight}."""
    kind = source.get("kind")
    check: dict[str, str] = {"quote": "na", "numbers": "na", "entities": "na", "date": "unknown"}
    if text is None or not text.strip():
        return {"status": "unverifiable", "check": check, "reason_code": "FETCH_FAILED", "reason_text": reason_text("FETCH_FAILED"), "highlight": None}
    q = _quote_in(quote, text)
    check["quote"] = q
    if q == "fail":
        if kind == "websearch_summary":
            # 요약문에 없는 인용은 버린다(§7.6.4)
            return {"status": "dropped", "check": check, "reason_code": "QUOTE_NOT_FOUND", "reason_text": reason_text("QUOTE_NOT_FOUND"), "highlight": None}
        return {"status": "needs_check", "check": check, "reason_code": "QUOTE_NOT_FOUND", "reason_text": reason_text("QUOTE_NOT_FOUND"), "highlight": None}
    nums = parse_numbers(claim_text)
    reason = None
    rtext = ""
    highlight = None
    if nums:
        qn = parse_numbers(quote)
        missing = [n for n in nums if not any(same_value(n, x) for x in qn)]
        if not qn:
            check["numbers"] = "missing"
            reason = "NUMBER_MISSING"
            rtext = reason_text(reason, num=nums[0].raw)
        elif missing:
            check["numbers"] = "mismatch"
            reason = "NUMBER_MISMATCH"
            rtext = reason_text(reason, num=qn[0].raw)
        else:
            check["numbers"] = "ok"
            highlight = qn[0].raw
    pub = source.get("published_at")
    if pub:
        check["date"] = "stale" if rules.is_stale(pub, today) else "ok"
    elif nums and kind == "web":
        check["date"] = "unknown"
    if kind == "websearch_summary":
        return {"status": "unverifiable", "check": check, "reason_code": "SUMMARY_ONLY", "reason_text": reason_text("SUMMARY_ONLY"),
                "highlight": highlight}
    if reason:
        return {"status": "needs_check", "check": check, "reason_code": reason, "reason_text": rtext, "highlight": highlight}
    if check["date"] == "stale":
        year = (pub or "")[:4]
        return {"status": "stale", "check": check, "reason_code": "STALE", "reason_text": reason_text("STALE", year=year), "highlight": highlight}
    if nums and kind == "web" and not pub:
        return {"status": "needs_check", "check": check, "reason_code": "DATE_UNKNOWN", "reason_text": reason_text("DATE_UNKNOWN"), "highlight": highlight}
    if q == "partial":
        highlight = None
    return {"status": "matched", "check": check, "reason_code": None, "reason_text": "", "highlight": highlight}


def claim_status(citations: list[dict[str, Any]], *, confirmed: bool = False) -> str:
    """§7.6.5 — confirmed > missing(인용 없음) > stale(모두 오래됨) > needs_check(일치 아닌 인용 ≥ 1) > matched."""
    if confirmed:
        return "confirmed"
    live = [c for c in citations if c.get("status") != "dropped"]
    if not live:
        return "missing"
    if all(c.get("status") == "stale" for c in live):
        return "stale"
    if any(c.get("status") != "matched" for c in live):
        if any(c.get("status") == "matched" for c in live):
            # 일치 인용이 있으면 같은 수치를 되풀이하는 요약 인용은 떼어 낸다(§7.6.5 정리)
            non_summary_bad = [c for c in live if c.get("status") != "matched" and c.get("source_kind") != "websearch_summary"]
            if not non_summary_bad:
                return "matched"
        return "needs_check"
    return "matched"


CLAIM_LABEL = {"matched": "원문 일치", "needs_check": "확인 필요", "conflict": "출처 간 값 다름", "stale": "자료 연도 오래됨",
               "confirmed": "확정", "checking": "확인 중", "missing": "확인 필요"}


def claim_label(status: str, n_bad: int = 0) -> str:
    if status == "needs_check" and n_bad:
        return f"확인 필요 {n_bad}"
    return CLAIM_LABEL.get(status, "확인 필요")


# ── 숫자 · 이름 지어내기 검사(§7.6.6) ────────────────────
def scrub_numbers(text: str, evidence_texts: list[str]) -> tuple[str, list[str]]:
    """근거 글에 없는 수치를 `[00]`(단위 유지)로 바꾼다. → (새 글, 지운 수치 원문 목록)."""
    if not text:
        return text, []
    nums = parse_numbers(text)
    if not nums:
        return text, []
    ev: list[Num] = []
    for t in evidence_texts:
        ev.extend(parse_numbers(t))
    removed: list[str] = []
    # 수치 위치는 정규화 글 기준이므로 정규화 글을 바꾼다(뒤에서부터 바꿔 위치가 밀리지 않게)
    out = _THOUSANDS.sub("", unicodedata.normalize("NFKC", text))
    for n in sorted(nums, key=lambda n: -n.start):
        if n.kind == "year":
            if any(e.kind == "year" and e.value == n.value for e in ev):
                continue
        elif any(same_value(n, e) for e in ev):
            continue
        m = re.search(r"(\s*)(%p|%|원|달러|개월|개국|개소|개|곳|매장|점포|대|명|건|배|년간|년|nit|kw|w|인치|\"|형|mm|㎡|kg|시간|분|초)$", n.raw, re.IGNORECASE)
        rep = "[00]" + ((m.group(1) + m.group(2)) if m else "")
        tail = out[n.start: n.end]
        # 끝 공백은 그대로 둔다
        trail = tail[len(tail.rstrip()):]
        out = out[: n.start] + rep + trail + out[n.end:]
        removed.append(n.raw)
    return out, removed


def leaks(text: str | None, names: list[str]) -> bool:
    """글 속에 실명 · 별칭이 있는가(공백 · 구두점 · 대소문자 무시)."""
    if not text:
        return False
    t = re.sub(r"[^0-9a-z가-힣]", "", unicodedata.normalize("NFKC", text).lower())
    for n in names:
        k = re.sub(r"[^0-9a-z가-힣]", "", unicodedata.normalize("NFKC", n or "").lower())
        if len(k) >= 2 and k in t:
            return True
    return False


def replace_names(text: str | None, names: list[str], label: str) -> str:
    """실명 · 별칭을 익명 표기로 바꾼다(긴 이름부터)."""
    if not text:
        return text or ""
    out = text
    for n in sorted({x for x in names if x and len(x.strip()) >= 2}, key=len, reverse=True):
        out = re.sub(re.escape(n), label, out, flags=re.IGNORECASE)
        # 공백 없이 붙여 쓴 경우(가나디스플레이)
        compact = re.sub(r"\s+", "", n)
        if compact != n and len(compact) >= 2:
            out = re.sub(re.escape(compact), label, out, flags=re.IGNORECASE)
    return out
