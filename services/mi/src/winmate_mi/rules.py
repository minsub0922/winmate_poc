"""라우팅 판단 · 표기 규칙(03-mi.md §3.3 · §3.4 · §10). 모두 결정적(모델 없음)."""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable

from . import config

MODE_LABEL = {"auto": "자동", "check": "확인 권장", "ask": "선택 필요", "pin": "고정"}
AREAS = ("market", "customer", "user", "competitor")
AREA_TAB = {"market": "시장조사", "customer": "고객사 · 비즈니스", "user": "사용자", "competitor": "경쟁사 → 삼성 강점"}
AREA_SHORT = {"market": "시장", "customer": "고객사", "user": "사용자", "competitor": "경쟁"}
AREA_LIST_LABEL = {"market": "시장", "customer": "고객", "user": "사용자", "competitor": "경쟁"}
AREA_TITLE = {"market": "비즈니스 시장조사", "customer": "고객사 · 비즈니스 분석", "user": "비즈니스 사용자 분석",
              "competitor": "경쟁사 분석 → 삼성 강점"}
AREA_FIX_TAB = {"market": "시장조사", "customer": "고객사", "user": "사용자", "competitor": "경쟁사"}
STATUS_LABEL = {"draft": "작성 중", "designing": "작성 중", "ask": "작성 중", "designed": "작성 중", "stopped": "작성 중",
                "failed": "작성 중", "queued": "진행 중", "running": "진행 중", "done": "완료", "upd": "업데이트 필요"}
STATUS_TONE = {"draft": "draft", "designing": "draft", "ask": "draft", "designed": "draft", "stopped": "draft", "failed": "draft",
               "queued": "run", "running": "run", "done": "done", "upd": "upd"}
USAGE_LABEL = {"standard": "표준 MI 섹션 · 3시트", "solution": "Solution형 대규모 MI · {n}시트", "quickwin": "퀵윈 · MI 섹션 없음",
               "exec_onepager": "경영진 한 장 + 부록 2장", "none": "리포트 · 연결 없음"}
USAGE_TYPE_NAME = {"standard": "표준 제안서", "solution": "Solution형 제안서", "quickwin": "퀵윈 제안서",
                   "exec_onepager": "경영진 보고", "none": "리포트"}


# ── 숫자 ─────────────────────────────────────────────────
def round2(x: float | None) -> float | None:
    if x is None:
        return None
    return float(Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def to100(x: float | None) -> int:
    """확신도를 소수 둘째 자리로 반올림한 뒤 100배 한 정수(§3.3 비교 정밀도)."""
    if x is None:
        return 0
    return int(Decimal(str(round2(x))) * 100)


def half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def fmt2(x: float | None) -> str:
    return "" if x is None else f"{round2(x):.2f}"


# ── 업종 판별 ────────────────────────────────────────────
def decide_segment(candidates: list[tuple[str, float]], *, pinned: str | None = None, inherited: str | None = None,
                   llm_failed: bool = False) -> tuple[str, str]:
    """§3.3 단계 2 평가 순서 → (업종 코드, 모드)."""
    if pinned:
        return pinned, "pin"
    if inherited:
        return inherited, "auto"
    ordered = sorted(((c, round2(v) or 0.0) for c, v in candidates if c != "GEN"), key=lambda t: (-t[1], t[0]))
    if not ordered:
        return "GEN", "auto"
    top_code, top = ordered[0]
    second = ordered[1][1] if len(ordered) > 1 else 0.0
    auto = to100(config.th("segment_auto", 0.80))
    check_min = to100(config.th("segment_check_min", 0.50))
    gap = to100(config.th("segment_ask_gap", 0.10))
    t, s = to100(top), to100(second)
    if t < check_min:
        return "GEN", "auto"
    if t - s < gap:
        return top_code, "ask"
    if t >= auto:
        mode = "auto"
    else:
        mode = "check"
    if llm_failed and mode == "auto":
        mode = "check"
    return top_code, mode


def combine_confidence(p: float | None, kb_score: float, clue_score: float) -> float:
    """§7.3 4. 합치기. p 가 None(LLM 실패)이면 대체 식."""
    if p is None:
        return round2(config.th("fallback_kb_weight", 0.6) * kb_score + config.th("fallback_clue_weight", 0.4) * clue_score) or 0.0
    return round2(config.th("llm_weight", 0.5) * p + config.th("kb_weight", 0.3) * kb_score + config.th("clue_weight", 0.2) * clue_score) or 0.0


def mix_score(a: float, b: float) -> float:
    return round2((a + b) / 2) or 0.0


# ── 한국어 조사 ───────────────────────────────────────────
_DIGIT_JONG = {"0": True, "1": True, "2": False, "3": True, "4": False, "5": False, "6": True, "7": True, "8": True, "9": False}
_DIGIT_RIEUL = {"1", "7", "8"}


def _last_char(word: str) -> str:
    w = re.sub(r"[\s\)\]\}\"'”’·.]+$", "", word or "")
    return w[-1] if w else ""


def has_batchim(word: str) -> bool:
    ch = _last_char(word)
    if not ch:
        return False
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return _DIGIT_JONG.get(ch, False)
    if ch.isalpha():
        return ch.lower() in "lmnr"
    return False


def rieul_batchim(word: str) -> bool:
    ch = _last_char(word)
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 == 8
    if ch.isdigit():
        return ch in _DIGIT_RIEUL
    return ch.lower() == "l"


def josa(word: str, with_b: str, without_b: str) -> str:
    """josa('호텔 · 리조트', '으로', '로') → '로'. 로/으로 는 ㄹ 받침이면 '로'."""
    if with_b == "으로":
        return "로" if (not has_batchim(word) or rieul_batchim(word)) else "으로"
    return with_b if has_batchim(word) else without_b


def join_and(items: list[str]) -> str:
    """['경쟁사 신제품 발표', '시장 리포트 개정'] → '경쟁사 신제품 발표와 시장 리포트 개정'."""
    items = [i for i in items if i]
    if not items:
        return ""
    out = items[0]
    for it in items[1:]:
        out += josa(out, "과", "와") + " " + it
    return out


# ── 시간 ─────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))


def now() -> datetime:
    today = config.clock_today()
    if today:
        return datetime.fromisoformat(today + "T03:00:00+00:00") if len(today) == 10 else datetime.fromisoformat(today)
    return datetime.now(timezone.utc)


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = datetime.fromisoformat(s[:10])
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def month_day(iso: str | None) -> str:
    d = parse_iso(iso)
    if d is None:
        return ""
    d = d.astimezone(KST)
    return f"{d.month}월 {d.day}일"


def relative(iso: str | None, ref: datetime | None = None) -> str:
    """1분 미만 `방금`, 60분 미만 `{m}분 전`, 24시간 미만 `{h}시간 전`, 어제 `어제`, 그 이전 `{M}월 {D}일`."""
    d = parse_iso(iso)
    if d is None:
        return ""
    ref = ref or now()
    delta = (ref - d).total_seconds()
    if delta < 60:
        return "방금"
    if delta < 3600:
        return f"{int(delta // 60)}분 전"
    if delta < 86400:
        return f"{int(delta // 3600)}시간 전"
    if (ref.astimezone(KST).date() - d.astimezone(KST).date()).days == 1:
        return "어제"
    return month_day(iso)


def months_between(published: str | None, ref: datetime | None = None) -> int | None:
    d = parse_iso(published)
    if d is None:
        return None
    ref = ref or now()
    return (ref.year - d.year) * 12 + (ref.month - d.month) - (1 if ref.day < d.day else 0)


def is_stale(published: str | None, ref: datetime | None = None) -> bool:
    m = months_between(published, ref)
    return m is not None and m > int(config.th("stale_months", 24))


# ── 진행 · 시간 예상(§10.8) ──────────────────────────────
def run_eta_s(n_areas: int) -> int:
    t = config.routing().get("time", {})
    return int(t.get("base_s", 60)) + int(t.get("per_area_s", 30)) * max(1, n_areas)


def changed_eta_s(n_areas: int) -> int:
    t = config.routing().get("time", {})
    return int(t.get("changed_base_s", 20)) + int(t.get("changed_per_area_s", 20)) * max(1, n_areas)


def minutes_label(eta_s: int) -> str:
    m = max(1, half_up(eta_s / 60))
    return f"약 {m}분"


def run_label(n_areas: int) -> str:
    return f"분석 시작 ({minutes_label(run_eta_s(n_areas))})"


def eta_label(eta_s: int | None) -> str:
    """60초 미만 10초 단위 `약 {s}초`, 이상 30초 단위 `약 {m}분` / `약 {m}분 30초`."""
    if eta_s is None:
        return ""
    s = max(0, int(eta_s))
    if s < 60:
        return f"약 {max(10, half_up(s / 10) * 10)}초"
    half_minutes = half_up(s / 30)
    m, r = divmod(half_minutes, 2)
    return f"약 {m}분 30초" if r else f"약 {m}분"


def progress_pct(search: float, organize: float, write: float) -> int:
    return half_up(40 * search + 35 * organize + 25 * write)


# ── 범위 · 쓰임 · 표기 ───────────────────────────────────
def keyword_hits(text: str, words: Iterable[str]) -> list[str]:
    return [w for w in words if w and w in (text or "")]


_CLAUSE = re.compile(r"[,.\n…·;!?()\[\]、]+")


def phrase_around(text: str, word: str) -> str:
    """요구 문장에서 키워드가 든 짧은 구 — 같은 절 안에서 키워드 낱말 + 다음 낱말(없으면 앞 낱말).
    예 '…경쟁사 대비… 주문 대기…' → '경쟁사 대비' · '주문 대기'."""
    for clause in _CLAUSE.split(text or ""):
        if word not in clause:
            continue
        toks = clause.split()
        for i, t in enumerate(toks):
            if word in t:
                if i + 1 < len(toks):
                    return f"{t} {toks[i + 1]}"
                if i > 0:
                    return f"{toks[i - 1]} {t}"
                return t
    return word


def is_customer_facing(usage: str | None) -> bool:
    return usage in ("standard", "solution", "quickwin", "exec_onepager")


def depth_for(usage: str | None) -> int:
    return int(config.th("depth_large", 60) if usage == "solution" else config.th("depth_standard", 30))


def scope_label(areas: list[str]) -> str:
    return " · ".join(AREA_LIST_LABEL[a] for a in AREAS if a in areas)


def scope_decision_label(areas: list[str]) -> str:
    return " · ".join({"market": "시장", "customer": "고객사", "user": "사용자", "competitor": "경쟁"}[a] for a in AREAS if a in areas)


def letters(n: int) -> list[str]:
    out = []
    for i in range(n):
        s = ""
        k = i
        while True:
            s = chr(ord("A") + k % 26) + s
            k = k // 26 - 1
            if k < 0:
                break
        out.append(s)
    return out


def render_rules() -> dict[str, Any]:
    """GET /v1/routing-rules — 설정 문구의 임계값 자리를 채운다(AC-MI-01)."""
    cfg = config.routing()
    th = cfg.get("thresholds", {})
    auto = float(th.get("segment_auto", 0.80))
    vals = {
        "auto": f"{auto:.2f}", "check_min": f"{float(th.get('segment_check_min', 0.5)):.2f}",
        "check_max": f"{(to100(auto) - 1) / 100:.2f}", "ask_gap": f"{float(th.get('segment_ask_gap', 0.1)):.2f}",
    }

    def fill(s: str) -> str:
        for k, v in vals.items():
            s = s.replace("{" + k + "}", v)
        return s

    def rows(rules: list[list[str]]) -> list[dict[str, str]]:
        return [{"c": fill(c), "o": fill(o), "mode": m, "mode_label": MODE_LABEL[m]} for c, o, m in rules]

    stages = [{"no": s["no"], "title": s["title"], "sub": fill(s["sub"]), "rules": rows(s["rules"])} for s in cfg.get("stages", [])]
    gaps = cfg.get("gaps", {})
    asks = cfg.get("asks", {})
    return {
        "header": cfg.get("header", {}),
        "modes": [{"key": m["key"], "label": m["label"], "desc": m["desc"]} for m in cfg.get("modes", [])],
        "stages": stages,
        "layout": cfg.get("layout", {}),
        "gaps": {"no": gaps.get("no", "6"), "title": gaps.get("title", ""), "sub": gaps.get("sub", ""), "rules": rows(gaps.get("rules", []))},
        "asks": {"title": asks.get("title", ""), "items": [fill(t) for t in asks.get("items", [])], "footer": asks.get("footer", "")},
        "thresholds": th,
    }
