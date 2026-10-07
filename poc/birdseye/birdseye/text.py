"""한국어 표기 도우미 — 조사, 숫자 서식."""
from __future__ import annotations

_DIGIT_BATCHIM = set("013678")
_LETTER_BATCHIM = set("LMNRlmnr")


def has_batchim(word: str) -> bool:
    w = (word or "").rstrip(" )\"'”’")
    if not w:
        return False
    ch = w[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return ch in _DIGIT_BATCHIM
    if ch.isalpha():
        return ch in _LETTER_BATCHIM
    return False


def josa(word: str, pair: str) -> str:
    """josa('플랜터', '이/가') → '플랜터가'."""
    a, b = pair.split("/")
    return word + (a if has_batchim(word) else b)


def mm(v: float) -> str:
    return f"{v:,.0f}"


def m(v: float, nd: int = 1) -> str:
    return f"{v / 1000:.{nd}f}"
