"""결정 규칙(모델 판단 없이 숫자 · 문자열로) — 04-competitor.md §3.3 · §7.4 · §7.5 · §7.7 · §10.

비교 정밀도: 확신도 · 신뢰는 소수 둘째 자리로 반올림(반올림 = 사사오입)한 뒤 100배 정수로 비교한다(03-mi.md §3.3).
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable

from . import config

SIGNALS = ("industry", "product", "place", "customer")
SIGNAL_CHIP = {"industry": "업종", "place": "장소", "product": "제품", "customer": "고객사"}
CHIP_ORDER = ("industry", "place", "product", "customer")
SLOT_LABEL = {"customer": "고객사", "industry": "업종", "place": "장소", "product": "제품"}
SLOT_ORDER = ("customer", "industry", "place", "product")
STATUS_LABEL = {"rec": "추천", "check": "확인 필요", "drop": "제외 제안", "user": "직접 추가"}
CHIP_LABEL = {
    "industry_basis": "업종 기준",
    "region_missing": "지역 미반영",
    "industry_inferred": "업종 추정",
    "place_inferred": "장소 추정",
    "industry_check": "업종 확인",
    "auto_confirmed": "후보 자동 확정",
}
CRITERION_SOURCE_LABEL = {"requirements": "요구", "industry_cases": "업종 사례", "default": "기본", "user": "직접"}


# ── 숫자 ─────────────────────────────────────────────────
def q2(x: float | int | str | Decimal) -> float:
    """소수 둘째 자리 사사오입(0.855 → 0.86)."""
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def to100(x: float | int | None) -> int:
    if x is None:
        return 0
    return int((Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100).to_integral_value())


def fmt_conf(x: float | None) -> str:
    """신뢰 표시 `0.91` 형식."""
    if x is None:
        return ""
    return f"{to100(x) / 100:.2f}"


# ── 후보 신뢰 · 상태(§7.4 · §10.1) ──────────────────────
def status_for(conf: float | None) -> str:
    c = to100(conf)
    if c >= to100(config.th("rec", 0.70)):
        return "rec"
    if c >= to100(config.th("check", 0.50)):
        return "check"
    return "drop"


def cap_signal(s: float, *, source_kinds: Iterable[str], partial: bool = False, key: str = "") -> float:
    """결정 규칙으로 덮기: 근거 없음 → 0 · 근거가 모두 웹 검색 요약 → ≤ 0.7 · 제품 일부 겹침 → ≤ 0.6."""
    kinds = [k for k in source_kinds if k]
    s = max(0.0, min(1.0, float(s or 0.0)))
    if not kinds:
        return 0.0
    if all(k == "websearch_summary" for k in kinds):
        s = min(s, config.th("summary_cap", 0.70))
    if key == "product" and partial:
        s = min(s, config.th("partial_product_cap", 0.60))
    return q2(s)


def confidence(signals: dict[str, dict[str, Any]], present: Iterable[str]) -> float:
    """신뢰 = round(Σ_{k∈A} w_k·s_k ÷ Σ_{k∈A} w_k, 2), A = 입력에 있는 칸(업종 · 제품은 늘 포함)."""
    w = config.weights()
    keys = set(present) | {"industry", "product"}
    num = Decimal("0")
    den = Decimal("0")
    for k in SIGNALS:
        if k not in keys:
            continue
        wk = Decimal(str(w.get(k, 0.0)))
        sk = Decimal(str(float((signals.get(k) or {}).get("s") or 0.0)))
        num += wk * sk
        den += wk
    if den == 0:
        return 0.0
    return float((num / den).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def evidence_chips(signals: dict[str, dict[str, Any]], present: Iterable[str] | None = None) -> list[str]:
    """근거 칩(신호 ≥ 0.5) — 입력에 없는 칸(예: 장소가 비었을 때 장소)의 신호는 칩으로 보이지 않는다."""
    t = to100(config.th("chip_signal", 0.5))
    keep = set(present) if present is not None else None
    return [SIGNAL_CHIP[k] for k in CHIP_ORDER if (keep is None or k in keep) and to100((signals.get(k) or {}).get("s") or 0) >= t]


def present_signals(slots: dict[str, Any]) -> list[str]:
    """신호로 쓸 칸(값이 있는 칸 — 답 · 추정 포함). 업종 · 제품은 늘 포함."""
    out = ["industry", "product"]
    for k in ("place", "customer"):
        v = (slots.get(k) or {})
        if v.get("value") and v.get("found") != "empty":
            out.append(k)
    return out


def cap_signals(slots: dict[str, Any]) -> list[str]:
    """후보 상한을 정하는 입력 신호(§10.2) — 업종 사례에서 채운 제품(origin=inferred)은 입력에 없던 것이라 빼고 센다(`업종만` 단)."""
    p = slots.get("product") or {}
    out = present_signals(slots)
    if not p.get("value") or p.get("origin") == "inferred":
        out = [k for k in out if k != "product"]
    return out


def cap_for(present: Iterable[str]) -> int:
    """추천 + 확인 필요 상한(§10.2) — 업종만 12 · + 제품 8 · + 장소 6 · + 고객사 5. 입력에 있는 가장 좁은 단."""
    caps = config.caps()
    p = set(present)
    out = caps.get("industry", 12)
    for k in ("product", "place", "customer"):
        if k in p:
            out = min(out, caps.get(k, out))
    return out


def letter_at(i: int) -> str:
    s = ""
    i += 1
    while i > 0:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def letters_seq(n: int) -> list[str]:
    return [letter_at(i) for i in range(n)]


def sort_key(c: dict[str, Any]) -> tuple[int, int]:
    order = {"rec": 0, "check": 1, "drop": 2, "user": 3}
    return (order.get(c.get("status") or "drop", 2), -to100(c.get("confidence")))


def select_auto(cands: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    """자동 후보 고르기: 추천 + 확인 필요는 신뢰 순 상한까지, 제외 제안은 상한 밖으로 최대 3곳 더(§10.2).
    하한보다 적어도 채우려고 지어내지 않는다."""
    ranked = sorted(cands, key=sort_key)
    keep = [c for c in ranked if c.get("status") in ("rec", "check")][:cap]
    drops = [c for c in ranked if c.get("status") == "drop"][: config.drop_extra()]
    return sorted(keep + drops, key=sort_key)


# ── 칸(§7.2 · §10.3) ─────────────────────────────────────
def slot_found(value: str | None, conf: float | None, partial: bool) -> str:
    if not value or not str(value).strip():
        return "empty"
    if partial:
        return "partial"
    if conf is not None and to100(conf) < to100(config.th("slot_found", 0.6)):
        return "partial"
    return "found"


def found_count(slots: dict[str, Any]) -> int:
    return sum(1 for k in SLOT_ORDER if (slots.get(k) or {}).get("found") in ("found", "partial"))


# ── 업종(03-mi.md §7.3 · §3.3, 경쟁사 분석은 칩 · 고정 없음) ──
def segment_conf(p: float | None, kb: float, clue: float) -> float:
    if p is None:
        return q2(0.6 * kb + 0.4 * clue)
    return q2(0.5 * p + 0.3 * kb + 0.2 * clue)


def segment_decision(cands: list[dict[str, Any]]) -> dict[str, Any]:
    """확신도 목록 → {code, confidence, ambiguous, gap, candidates}. 1위 < 0.50 → GEN. 1 · 2위 차이 < 0.10 → 두 갈래."""
    ranked = sorted(cands, key=lambda c: (-to100(c.get("confidence")), c.get("code") or ""))
    top = ranked[0] if ranked else {"code": "GEN", "confidence": 0.0}
    second = ranked[1] if len(ranked) > 1 else {"code": None, "confidence": 0.0}
    gap100 = to100(top.get("confidence")) - to100(second.get("confidence"))
    gen = to100(top.get("confidence")) < to100(config.th("segment_min", 0.50))
    ambiguous = (not gen) and second.get("code") is not None and gap100 < to100(config.th("ambiguous_gap", 0.10))
    return {
        "code": "GEN" if gen else top.get("code"),
        "confidence": q2(top.get("confidence") or 0.0),
        "ambiguous": bool(ambiguous),
        "gap": gap100 / 100,
        "candidates": [{"code": c.get("code"), "confidence": q2(c.get("confidence") or 0.0)} for c in ranked[:5]],
    }


def should_ask(slots: dict[str, Any], segment: dict[str, Any], *, require_ambiguous: bool | None = None) -> bool:
    """묻기 1(§3.3): 고객사 · 장소가 둘 다 비고 (기본) 업종이 두 갈래."""
    req = config.ask_requires_ambiguous() if require_ambiguous is None else require_ambiguous
    empty = all((slots.get(k) or {}).get("found", "empty") == "empty" for k in ("customer", "place"))
    if not empty:
        return False
    return bool(segment.get("ambiguous")) if req else True


# ── 비교 기준(§7.5) ──────────────────────────────────────
def compose_criteria(req_names: list[dict[str, Any]], industry: list[dict[str, Any]], *, eval_first: bool = True) -> list[dict[str, Any]]:
    """요구사항 3 + 업종 사례 1 + 기본 2 = 6. 요구가 3개 미만이면 업종 사례 기준으로 채워 합계 6.
    req_names: [{name, requirement_ref?}] (RFP 평가 기준 → 정의서 → 자유 양식 순으로 이미 정렬)
    industry: [{name, n}] (업종 인사이트 요구 유형 상위)"""
    rules = config.criteria_rules()
    n_req = int(rules.get("requirements", 3))
    n_ind = int(rules.get("industry", 1))
    total = int(rules.get("total", 6))
    imp_req = list(rules.get("req_importance") or [5, 4, 4])
    defaults = list(rules.get("defaults") or [])
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def norm(s: str) -> str:
        return re.sub(r"[\s·・,./()\-]+", "", s or "").lower()

    for d in defaults:
        seen.add(norm(d["name"]))
    for r in req_names:
        if len([c for c in out if c["source"] == "requirements"]) >= n_req:
            break
        k = norm(r["name"])
        if not k or k in seen:
            continue
        seen.add(k)
        i = len([c for c in out if c["source"] == "requirements"])
        out.append({"name": r["name"][: int(rules.get("name_max", 10))], "source": "requirements", "importance": imp_req[min(i, len(imp_req) - 1)],
                    "requirement_ref": r.get("requirement_ref"), "source_count": None})
    n_req_have = len(out)
    need_ind = n_ind + max(0, n_req - n_req_have)
    ind_added = 0
    for r in industry:
        if ind_added >= need_ind:
            break
        k = norm(r["name"])
        if not k or k in seen:
            continue
        seen.add(k)
        out.append({"name": r["name"][: int(rules.get("name_max", 10))], "source": "industry_cases",
                    "importance": int(rules.get("industry_importance", 3)), "source_count": int(r.get("n") or 0) or None, "requirement_ref": None})
        ind_added += 1
    for d in defaults:
        out.append({"name": d["name"], "source": "default", "importance": int(d.get("importance", 3)), "source_count": None, "requirement_ref": None})
    out = out[: max(total, len(out))]
    for i, c in enumerate(out):
        c["order"] = i
        c["enabled"] = True
        c["pinned"] = False
    return out


def criteria_suggestions(industry: list[dict[str, Any]], existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def norm(s: str) -> str:
        return re.sub(r"[\s·・,./()\-]+", "", s or "").lower()

    have = {norm(c.get("name", "")) for c in existing}
    out = []
    for r in industry:
        if norm(r["name"]) in have:
            continue
        out.append({"name": r["name"][:10], "n": int(r.get("n") or 0)})
        if len(out) >= int(config.criteria_rules().get("suggestions", 2)):
            break
    return out


def criteria_summary(criteria: list[dict[str, Any]]) -> dict[str, int]:
    on = [c for c in criteria if c.get("enabled", True)]
    return {"total": len(on), "requirements": sum(1 for c in on if c.get("source") == "requirements"),
            "industry_cases": sum(1 for c in on if c.get("source") == "industry_cases"),
            "default": sum(1 for c in on if c.get("source") == "default"), "user": sum(1 for c in on if c.get("source") == "user")}


# ── 강점 · 주의할 점(§7.7) ───────────────────────────────
def pick_strengths(criteria: list[dict[str, Any]], verdicts: list[dict[str, Any]], *, max_n: int = 3) -> list[dict[str, Any]]:
    """기준마다 점수 = 중요도 × (samsung_better 인 경쟁사 수), 상위 최대 3(점수 0 은 뺀다)."""
    rows = []
    for c in criteria:
        if not c.get("enabled", True):
            continue
        wins = [v["competitor_id"] for v in verdicts if v.get("criterion_id") == c["id"] and v.get("verdict") == "samsung_better"]
        if not wins:
            continue
        rows.append({"criterion": c, "score": int(c.get("importance") or 3) * len(wins), "competitor_ids": wins})
    rows.sort(key=lambda r: (-r["score"], r["criterion"].get("order", 0)))
    return rows[:max_n]


def pick_cautions(criteria: list[dict[str, Any]], verdicts: list[dict[str, Any]], competitors: list[dict[str, Any]], *, max_n: int = 2) -> list[dict[str, Any]]:
    """samsung_worse 인 (경쟁사, 기준) 쌍을 중요도 순 상위 최대 2(경쟁사 글자 순으로 동점 처리)."""
    crit = {c["id"]: c for c in criteria if c.get("enabled", True)}
    letter = {c["id"]: c.get("letter") or "" for c in competitors}
    pairs = []
    for v in verdicts:
        if v.get("verdict") != "samsung_worse" or v.get("criterion_id") not in crit:
            continue
        c = crit[v["criterion_id"]]
        pairs.append({"criterion": c, "competitor_id": v["competitor_id"], "importance": int(c.get("importance") or 3)})
    pairs.sort(key=lambda p: (-p["importance"], p["criterion"].get("order", 0), len(letter.get(p["competitor_id"], "")), letter.get(p["competitor_id"], "")))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in pairs:
        if p["competitor_id"] in seen:
            continue
        seen.add(p["competitor_id"])
        out.append(p)
        if len(out) >= max_n:
            break
    return out


# ── 시간 · 진행(§10.5) ───────────────────────────────────
def eta_find_label() -> str:
    return f"약 {config.eta().get('find_s', 30)}초"


def eta_analyze_s(n: int) -> int:
    e = config.eta()
    return int(e.get("analyze_base_s", 20) + e.get("analyze_per_s", 25) * max(1, n))


def eta_minutes(n: int) -> int:
    return max(1, int(Decimal(eta_analyze_s(n) / 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def eta_label_s(sec: int) -> str:
    if sec < 60:
        return f"약 {max(10, int(round(sec / 10.0)) * 10)}초"
    m = int(Decimal(sec / 60).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"약 {m}분"


def progress_pct(done_facts: int, n_competitors: int, finishing: float) -> int:
    """pct = round(90 × 끝난 사실 수 ÷ (경쟁사 수 × 5) + 10 × 마무리 단계 완료)."""
    total = max(1, n_competitors * 5)
    return int(round(90 * min(done_facts, total) / total + 10 * max(0.0, min(1.0, finishing))))


# ── 한국어 ───────────────────────────────────────────────
def has_batchim(word: str) -> bool:
    w = re.sub(r"[\s\)\]\}\"'”’]+$", "", word or "")
    if not w:
        return False
    ch = w[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return ch in "013678"
    if ch.isalpha():
        return ch.lower() in "lmnr"
    return False


def josa(word: str, with_batchim: str, without: str) -> str:
    return with_batchim if has_batchim(word) else without


def join_with_gwa(items: list[tuple[str, str]]) -> str:
    """[(항목, 표기)] → '업종(외식 · 카페)과 제품(메뉴보드 사이니지)'. 조사는 항목 이름(괄호 앞)으로 정한다."""
    parts = [f"{k}({v})" for k, v in items]
    if len(parts) <= 1:
        return parts[0] if parts else ""
    head = ", ".join(parts[:-2] + [parts[-2]]) if len(parts) > 2 else parts[0]
    last_key = items[-2][0]
    return f"{head}{josa(last_key, '과', '와')} {parts[-1]}"


def ym(d: str | date | None) -> str:
    if not d:
        return ""
    s = d.isoformat() if isinstance(d, date) else str(d)
    m = re.match(r"(\d{4})-(\d{2})", s)
    return f"{m.group(1)}.{m.group(2)}" if m else s


def _parse_iso(iso: str | None) -> datetime | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def md_label(iso: str | None) -> str:
    dt = _parse_iso(iso)
    if not dt:
        return ""
    k = dt.astimezone(config.KST)
    return f"{k.month}월 {k.day}일"


def rel_time(iso: str | None, now: datetime | None = None) -> str:
    """1분 미만 `방금`, 60분 미만 `{m}분 전`, 24시간 미만 `{h}시간 전`, 어제 `어제`, 그 이전 `{M}월 {D}일`."""
    dt = _parse_iso(iso)
    if not dt:
        return ""
    now = now or datetime.now(timezone.utc)
    sec = (now - dt).total_seconds()
    if sec < 60:
        return "방금"
    if sec < 3600:
        return f"{int(sec // 60)}분 전"
    if sec < 86400:
        return f"{int(sec // 3600)}시간 전"
    k_now = now.astimezone(config.KST).date()
    k_dt = dt.astimezone(config.KST).date()
    if k_now - k_dt == timedelta(days=1):
        return "어제"
    return md_label(iso)


def is_today(iso: str | None, now: datetime | None = None) -> bool:
    dt = _parse_iso(iso)
    if not dt:
        return False
    now = now or datetime.now(timezone.utc)
    return dt.astimezone(config.KST).date() == now.astimezone(config.KST).date()


def months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month) - (1 if b.day < a.day else 0)


def is_stale(published: str | None, today: date | None = None) -> bool:
    if not published:
        return False
    try:
        d = date.fromisoformat(published[:10])
    except ValueError:
        return False
    return months_between(d, today or config.today()) > int(config.th("stale_months", 24))


# ── 이름 정규화(§7.3 resolve_entities) ───────────────────
_CORP = re.compile(r"(주식회사|\(주\)|㈜|\(유\)|유한회사|co\.,?\s*ltd\.?|inc\.?|corp\.?|corporation|ltd\.?|limited|gmbh|llc|plc)", re.IGNORECASE)


def clean_name(name: str) -> str:
    n = _CORP.sub(" ", name or "")
    n = re.sub(r"[\"'“”‘’]", "", n)
    n = re.sub(r"\s+", " ", n).strip(" ,.-·")
    return n


def name_key(name: str) -> str:
    return re.sub(r"[^0-9a-z가-힣]", "", clean_name(name).lower())


def same_company(a: str, b_names: Iterable[str]) -> bool:
    ka = name_key(a)
    if not ka:
        return False
    for b in b_names:
        kb = name_key(b)
        if kb and (ka == kb or (min(len(ka), len(kb)) >= 3 and (ka in kb or kb in ka) and abs(len(ka) - len(kb)) <= 3)):
            return True
    return False


def is_self_entity(name: str) -> bool:
    k = name_key(name)
    for s in config.self_entities():
        ks = name_key(s)
        if ks and (k == ks or (k.startswith(ks) and len(ks) >= 2 and ks in ("삼성", "samsung"))):
            return True
    return False
