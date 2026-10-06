"""문구 도우미 — 조사 · 목록 잇기 · 시각 · 남은 시간 · 상대 시각(09-scenario §1 화면 원칙, 07 §1 · §10.5 규칙).

W 말풍선과 배지 문구는 LLM 이 쓰지 않고 이 템플릿으로 채운다. 조사(을/를 · 이/가 · 은/는 · 와/과 · 으로/로)는 앞말 발음으로 고른다
— 한글은 받침, 숫자는 읽는 소리(1 · 3 · 6 · 7 · 8 · 0 → 받침), 영문은 마지막 글자 발음.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
SEP = " · "

_DIGIT_BATCHIM = {"0": True, "1": True, "2": False, "3": True, "4": False, "5": False, "6": True, "7": True, "8": True, "9": False}
_DIGIT_RIEUL = {"1", "7", "8"}
_LETTER_BATCHIM = {"l": True, "m": True, "n": True, "r": True}
_LETTER_RIEUL = {"l", "r"}


def final_sound(word: str) -> tuple[bool, bool]:
    """(받침 있음, ㄹ 받침)."""
    s = re.sub(r"[\s\)\]」』'\"’”.,!?·×]+$", "", word or "")
    if not s:
        return False, False
    ch = s[-1]
    if "가" <= ch <= "힣":
        jong = (ord(ch) - 0xAC00) % 28
        return jong != 0, jong == 8
    if ch.isdigit():
        return _DIGIT_BATCHIM[ch], ch in _DIGIT_RIEUL
    if ch.isascii() and ch.isalpha():
        low = ch.lower()
        if ch.isupper() and (len(s) == 1 or not s[-2].islower()):
            return _LETTER_BATCHIM.get(low, False), low in _LETTER_RIEUL
        if s.lower().endswith("ng"):
            return True, False
        return low in ("l", "m", "n"), low == "l"
    return False, False


_PAIRS = {
    "을/를": ("을", "를"), "를/을": ("을", "를"),
    "이/가": ("이", "가"), "가/이": ("이", "가"),
    "은/는": ("은", "는"), "는/은": ("은", "는"),
    "과/와": ("과", "와"), "와/과": ("과", "와"),
}


def josa(word: str, pair: str) -> str:
    """josa('장면 2', '은/는') → '는'. pair = 을/를 · 이/가 · 은/는 · 와/과 · 으로/로."""
    has, rieul = final_sound(word)
    if pair in ("으로/로", "로/으로"):
        return "로" if (not has or rieul) else "으로"
    with_batchim, without = _PAIRS[pair]
    return with_batchim if has else without


def with_josa(word: str, pair: str) -> str:
    return f"{word}{josa(word, pair)}"


# 낱말을 바꾼 뒤 뒤따르는 조사를 다시 고른다(실존 인물 · 경쟁사 치환)
_FOLLOW = re.compile(r"^(이|가|을|를|은|는|과|와|으로|로)(?![가-힣])")
_FOLLOW_PAIR = {"이": "이/가", "가": "이/가", "을": "을/를", "를": "을/를", "은": "은/는", "는": "은/는",
                "과": "와/과", "와": "와/과", "으로": "으로/로", "로": "으로/로"}


def fix_following_josa(replacement: str, rest: str) -> tuple[str, str]:
    """rest 앞의 조사를 replacement 발음에 맞춰 바꾼다 → (조사, 나머지)."""
    m = _FOLLOW.match(rest)
    if not m:
        return "", rest
    return josa(replacement, _FOLLOW_PAIR[m.group(1)]), rest[m.end():]


def join(items: list[str] | tuple[str, ...], sep: str = SEP) -> str:
    return sep.join(x for x in items if x)


def scene_list(nos: list[int]) -> str:
    """[3, 4] → 「장면 3 · 4」."""
    return "장면 " + SEP.join(str(n) for n in nos) if nos else ""


# ── 시각 ──────────────────────────────────────────────────

_TIME = re.compile(r"^\s*(\d{1,2})[:시]\s*(\d{2})?")


def norm_time(value: str | None) -> str | None:
    """'7:00' · '07:00' · '7시' → '07:00'. 아니면 None."""
    if not value:
        return None
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", value) or re.match(r"^\s*(\d{1,2})\s*시\s*(?:(\d{1,2})\s*분)?\s*$", value)
    if not m:
        return None
    h = int(m.group(1))
    mi = int(m.group(2) or 0)
    if h > 24 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


def time_key(value: str | None) -> int:
    t = norm_time(value)
    if not t:
        return 10_000
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def eta_text(seconds: float | None) -> str:
    """07 §10.5: ≥ 60초 「약 {ceil(s/60)}분 남음」, < 60초 「약 {round10(s)}초 남음」."""
    if seconds is None:
        return ""
    s = max(0.0, float(seconds))
    if s >= 60:
        return f"약 {math.ceil(s / 60)}분 남음"
    r = int(round(s / 10.0) * 10)
    return f"약 {max(10, r)}초 남음"


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def month_day(iso: str | None) -> str:
    """「9월 30일」(KST)."""
    t = parse_iso(iso)
    if t is None:
        return ""
    k = t.astimezone(KST)
    return f"{k.month}월 {k.day}일"


def relative_label(iso: str | None, now: datetime | None = None) -> str:
    """「방금」(1분 안) · 「N분 전」 · 「N시간 전」 · 「어제」 · 「M월 D일」 — 장면 이미지 「v1 · 이미지 생성 · 어제」."""
    t = parse_iso(iso)
    if t is None:
        return ""
    now = now or datetime.now(timezone.utc)
    sec = (now - t).total_seconds()
    if sec < 60:
        return "방금"
    if sec < 3600:
        return f"{int(sec // 60)}분 전"
    kt, kn = t.astimezone(KST), now.astimezone(KST)
    if kt.date() == kn.date():
        return f"{int(sec // 3600)}시간 전"
    if (kn.date() - kt.date()).days == 1:
        return "어제"
    return f"{kt.month}월 {kt.day}일"


def clip(text: str | None, n: int) -> str:
    s = re.sub(r"\s+", " ", (text or "")).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def initial(name: str) -> str:
    s = (name or "").strip()
    return s[0] if s else "?"


def short_role(name: str) -> str:
    """「본사 마케팅 담당자」 → 「본사」(장면 카드 「장면 4 · 본사 시점」)."""
    s = (name or "").strip()
    return s.split(" ")[0] if s else s
