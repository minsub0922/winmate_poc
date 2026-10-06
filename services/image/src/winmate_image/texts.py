"""화면 문구 템플릿 도우미 — W 말풍선 · 배지 · 시각 · 버전 라벨 · 파일명(07-image §1 화면 원칙, §4, §5.3, §10.5).

LLM 이 쓰지 않고 상태 값으로 채운다. 조사(을/를 · 이/가 · 은/는 · 으로/로)는 앞말 발음으로 고른다.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# 숫자 읽는 소리: 1(일) 3(삼) 6(육) 7(칠) 8(팔) 0(영) → 받침 / 2 4 5 9 → 받침 없음. ㄹ 받침: 1 7 8
_DIGIT_BATCHIM = {"0": True, "1": True, "2": False, "3": True, "4": False, "5": False, "6": True, "7": True, "8": True, "9": False}
_DIGIT_RIEUL = {"1", "7", "8"}
# 영문 글자 이름: L(엘) M(엠) N(엔) R(알) 은 받침, R·L 은 ㄹ
_LETTER_BATCHIM = {"l": True, "m": True, "n": True, "r": True}
_LETTER_RIEUL = {"l", "r"}


def _final(word: str) -> tuple[bool, bool]:
    """(받침 있음, ㄹ 받침)"""
    s = re.sub(r"[\s\)\]」』'\"’”.,!?·]+$", "", word or "")
    if not s:
        return False, False
    ch = s[-1]
    if "가" <= ch <= "힣":
        jong = (ord(ch) - 0xAC00) % 28
        return jong != 0, jong == 8
    if ch.isdigit():
        return _DIGIT_BATCHIM[ch], ch in _DIGIT_RIEUL
    if ch.isalpha() and ch.isascii():
        low = ch.lower()
        if ch.isupper() and (len(s) == 1 or not s[-2].islower()):
            return _LETTER_BATCHIM.get(low, False), low in _LETTER_RIEUL
        # 소문자로 끝나는 영어 낱말: l · m · n · ng 은 받침(Wall → 을)
        if s.lower().endswith("ng"):
            return True, False
        return low in ("l", "m", "n"), low == "l"
    return False, False


def josa(word: str, pair: str) -> str:
    """josa('시안 1', '을/를') → '을'. pair = '을/를' | '이/가' | '은/는' | '와/과' | '으로/로'."""
    has, rieul = _final(word)
    if pair in ("으로/로", "로/으로"):
        return "로" if (not has or rieul) else "으로"
    a, b = pair.split("/")
    # 첫째 = 받침 있을 때 형태(을·이·은·과), 둘째 = 없을 때(를·가·는·와)
    if a in ("를", "가", "는", "와"):
        a, b = b, a
    return a if has else b


def with_josa(word: str, pair: str) -> str:
    return f"{word}{josa(word, pair)}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def relative_time(iso: str | None, now: datetime | None = None) -> str:
    """「방금」/「N분 전」/「N시간 전」/「어제」/「N일 전」(2~6)/「지난주」(7~13)/「M월 D일」"""
    t = parse_iso(iso)
    if t is None:
        return ""
    now = now or now_utc()
    sec = (now - t).total_seconds()
    if sec < 60:
        return "방금"
    if sec < 3600:
        return f"{int(sec // 60)}분 전"
    lt, ln = t.astimezone(KST), now.astimezone(KST)
    days = (ln.date() - lt.date()).days
    if days <= 0:
        return f"{int(sec // 3600)}시간 전"
    if days == 1:
        return "어제"
    if days <= 6:
        return f"{days}일 전"
    if days <= 13:
        return "지난주"
    return f"{lt.month}월 {lt.day}일"


def remaining(seconds: float | None) -> str:
    """≥ 60초 「약 {ceil(s/60)}분 남음」, < 60초 「약 {round10(s)}초 남음」"""
    if seconds is None:
        return ""
    s = max(0.0, float(seconds))
    if s >= 60:
        return f"약 {math.ceil(s / 60)}분 남음"
    r = int(round(s / 10.0) * 10)
    return f"약 {max(10, r)}초 남음"


def queue_label(position: int) -> str:
    return "다음 차례" if position <= 1 else f"{position}번째"


def customer_short(name: str | None, short: str | None = None) -> str | None:
    """workspace 의 customer_short, 없으면 고객사명 앞 두 어절."""
    if short:
        return short
    if not name:
        return None
    parts = name.split()
    return " ".join(parts[:2]) if parts else None


def version_label(n: int, op: str, *, op_index: int | None = None, region_n: int | None = None, aspect: str | None = None) -> str:
    """IMG3E 수정 기록 라벨(§5.3): n=1 「원본」, edit_region 「수정 {n-1} · 영역 {k}」, edit_global 「수정 {n-1} · 전체」, adjust 「보정 {n-1}」."""
    if n <= 1:
        return "원본"
    k = op_index if op_index is not None else n - 1
    if op == "edit_region":
        return f"수정 {k} · 영역 {region_n or 1}"
    if op == "edit_global":
        return f"수정 {k} · 전체"
    if op == "adjust":
        return f"보정 {k}"
    if op == "restore":
        return f"되돌림 {k}"
    if op in ("variant", "generate", "composite"):
        return f"버전 {n}"
    if op == "aspect":
        return f"{aspect or ''} 버전".strip()
    if op == "upscale":
        return f"업스케일 {k}"
    return f"버전 {n}"


def export_title(image_label: str, n: int, op: str, aspect: str | None = None) -> str:
    """IMG4 제목: n=1 이면 시안 라벨만, 그 외 `{시안 라벨} · {부분 수정본|수정본|보정본|{비율} 버전} v{n}`."""
    if n <= 1:
        return image_label
    kind = {"edit_region": "부분 수정본", "edit_global": "수정본", "adjust": "보정본", "restore": "복원본"}.get(op)
    if kind is None:
        kind = f"{aspect} 버전" if op == "aspect" and aspect else "수정본"
    return f"{image_label} · {kind} v{n}"


def export_kind_word(n: int, op: str) -> str:
    """IMG4 W: 「{시안 라벨} {수정본|''}을 내보냅니다」"""
    if n <= 1:
        return ""
    return {"adjust": "보정본"}.get(op, "수정본")


_BAD_FILE = re.compile(r"[\\/:*?\"<>|\s]+")


def filename(customer_short_: str | None, subject_short: str | None, image_label: str, n: int, ext: str) -> str:
    """`{고객사 약칭 공백 제거}_{subject_short}_{시안 라벨 공백 제거}_v{n}.{ext}` (예 A커피_메뉴보드_시안1_v2.png)"""
    parts = []
    if customer_short_:
        parts.append(_BAD_FILE.sub("", customer_short_))
    if subject_short:
        parts.append(_BAD_FILE.sub("", subject_short))
    parts.append(_BAD_FILE.sub("", image_label.replace("·", "")) or "이미지")
    return "_".join(p for p in parts if p) + f"_v{n}.{ext}"


def products_summary(products: list[dict]) -> str:
    """「QM55C ×3 · KM24C」"""
    out = []
    for p in products:
        name = p.get("short") or p.get("name") or ""
        qty = int(p.get("qty") or 1)
        out.append(f"{name} ×{qty}" if qty > 1 else name)
    return " · ".join(x for x in out if x)


def run_summary_line(products: list[dict], ref_count: int) -> str:
    """IMG3G 요약 줄 「{제품 요약} · 참조 {r}장 반영」(참조 0이면 뒷부분 생략)."""
    parts = []
    ps = products_summary(products)
    if ps:
        parts.append(ps)
    if ref_count:
        parts.append(f"참조 {ref_count}장 반영")
    return " · ".join(parts)


def shot_label(i: int) -> str:
    return f"시안 {i}"
