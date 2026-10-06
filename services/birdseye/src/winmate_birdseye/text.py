"""표기 규칙 — 조사 · 단위 · 방향어 · 숫자 가리기(08-birdseye §1 화면 원칙 · §10.2).

- 조사(을/를 · 이/가 · 은/는 · 으로/로 · 와/과)는 앞말 발음으로 고른다: 한글은 받침, 숫자는 읽는 소리
  (1·3·6·7·8·0 → 받침 있음, 그중 1·7·8 은 ㄹ), 영문은 마지막 글자 발음(대문자 = 알파벳 이름, 소문자 = 끝소리).
- 1평 = 400/121 ㎡. 평은 정수 반올림 「약 {n}평」, ㎡ 는 정수, 길이 0.1 m.
"""
from __future__ import annotations

import math
import re

PYEONG_M2 = 400.0 / 121.0

# 알파벳 이름의 받침: L(엘) R(알) → ㄹ, M(엠) → ㅁ, N(엔) → ㄴ
_UPPER_FINAL = {"L": "l", "R": "l", "M": "m", "N": "n"}
_DIGIT_FINAL = {"0": "ng", "1": "l", "3": "m", "6": "k", "7": "l", "8": "l"}


def _final(word: str) -> str | None:
    """마지막 소리의 받침 종류: None(없음) · 'l'(ㄹ) · 그 밖 문자열(ㄹ 아닌 받침)."""
    w = (word or "").rstrip()
    w = re.sub(r"[\s\"'”’)\]」』.,·×:%]+$", "", w)
    if not w:
        return None
    ch = w[-1]
    if "가" <= ch <= "힣":
        jong = (ord(ch) - 0xAC00) % 28
        if jong == 0:
            return None
        return "l" if jong == 8 else "x"
    if ch.isdigit():
        return _DIGIT_FINAL.get(ch)
    if ch.isupper():
        return _UPPER_FINAL.get(ch)
    if ch.isalpha():
        low = w.lower()
        if low.endswith("ng"):
            return "ng"
        return {"l": "l", "m": "m", "n": "n"}.get(ch.lower())
    return None


def josa(word: str, pair: str) -> str:
    """josa('The Wall', '을/를') → '을'. pair: 을/를 · 이/가 · 은/는 · 으로/로 · 과/와 · 이라/라."""
    with_final, without = pair.split("/")
    fin = _final(word)
    if pair == "으로/로":
        return "로" if fin in (None, "l") else "으로"
    return with_final if fin else without


def jo(word: str, pair: str) -> str:
    """단어 + 조사."""
    return f"{word}{josa(word, pair)}"


def m(v: float | None, digits: int = 1) -> str:
    """길이 표기 — 0.1 m 단위(소수 첫째 자리)."""
    if v is None:
        return "[확인 필요]"
    return f"{v:.{digits}f}"


def num(v: float | None) -> str:
    """정수면 정수로, 아니면 소수 한 자리."""
    if v is None:
        return "[확인 필요]"
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.1f}".rstrip("0").rstrip(".")


def pyeong_to_m2(p: float) -> float:
    return round(p * PYEONG_M2, 2)


def m2_to_pyeong(a: float) -> float:
    return a / PYEONG_M2


def pyeong_label(area_m2: float | None) -> str:
    if not area_m2:
        return "[확인 필요]"
    return f"{int(round(m2_to_pyeong(area_m2)))}평"


def area_label(area_m2: float | None) -> str:
    """「396 ㎡ (약 120평)」"""
    if not area_m2:
        return "[확인 필요]"
    return f"{int(round(area_m2))} ㎡ (약 {int(round(m2_to_pyeong(area_m2)))}평)"


DIRECTION = {"up": "위로", "down": "아래로", "left": "왼쪽으로", "right": "오른쪽으로"}
DIRECTION_SHORT = {"up": "위", "down": "아래", "left": "왼쪽", "right": "오른쪽"}


def move_label(dx: float, dy: float) -> str:
    """이동 라벨 — 「오른쪽으로 3.0 m」, 두 축 모두 0.3 m 이상이면 「오른쪽 2.0 m · 위 1.0 m」(화면 기준, 위 = −y)."""
    ax, ay = abs(dx), abs(dy)
    hx = "right" if dx > 0 else "left"
    hy = "down" if dy > 0 else "up"
    if ax >= 0.3 and ay >= 0.3:
        return f"{DIRECTION_SHORT[hx]} {m(ax)} m · {DIRECTION_SHORT[hy]} {m(ay)} m"
    if ax >= ay:
        return f"{DIRECTION[hx]} {m(ax)} m"
    return f"{DIRECTION[hy]} {m(ay)} m"


def dir_word(dx: float, dy: float) -> str:
    """주된 축의 방향어(위로 · 아래로 · 왼쪽으로 · 오른쪽으로)."""
    if abs(dx) >= abs(dy):
        return DIRECTION["right" if dx > 0 else "left"]
    return DIRECTION["down" if dy > 0 else "up"]


def ceil_step(v: float, step: float) -> float:
    return round(math.ceil(round(v / step, 6)) * step, 4)


# 수치(단위 포함)만 — 모델코드(OH55A · QM55C: 영문 · 숫자에 붙은 숫자) · 화면 크기(85" · 85인치 · 85형) · 배치 수량(×3)은 둔다
_NUM_RE = re.compile(r'(?<![A-Za-z0-9.,×])\d+(?:[.,]\d+)*'
                     r'(?:\s?(?:%|배|명|개|곳|m|㎡|평|분|초|시간|년|원|만|억|천)(?![A-Za-z])|(?![A-Za-z0-9"”]|인치|형))')


def mask_numbers(text: str) -> str:
    """존 문구 — 근거 없는 수치는 「[00]」 로만(§7.10 · AC 55). 모델코드(QM55C · OH55A) · 화면 크기 · ×수량은 둔다."""
    return _NUM_RE.sub("[00]", text or "")


def clip(text: str, n: int) -> str:
    t = (text or "").strip()
    return t if len(t) <= n else t[:n].rstrip()


def time_label_hint() -> str:
    """시각 표기(「오늘 HH:mm」 · 「어제 HH:mm」 · 「M월 D일」)는 웹이 사용자 시간대로 만든다."""
    return "web"
