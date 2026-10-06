"""문장 도우미 — 이름 정규화 · 중복 판정 · 조사 · 숫자 가드 · 관련성 검사(모두 결정적)."""
from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

_HONORIFIC = re.compile(r"(님|께서|께|씨)$")
_SPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[\s\-_·•・,.()\[\]{}'\"“”‘’/|:;!?~]+")


def nfc(text: str | None) -> str:
    return unicodedata.normalize("NFC", text or "")


def normalize_name(name: str | None) -> str:
    """키맨 이름 정규화: 공백 · 존칭 · 콘텐츠/컨텐츠 표기 차이."""
    n = _SPACE.sub("", nfc(name)).strip()
    n = _HONORIFIC.sub("", n)
    n = n.replace("콘텐츠", "컨텐츠").replace("콘텐트", "컨텐츠")
    return n.lower()


def _grams(text: str, n: int = 3) -> set[str]:
    t = _PUNCT.sub("", nfc(text).lower())
    if len(t) < n:
        return {t} if t else set()
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def trigram_jaccard(a: str, b: str) -> float:
    ga, gb = _grams(a), _grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def same_item(a: str, b: str) -> bool:
    """§7.2 normalize: 문자 3-gram 자카드 ≥ 0.85 면 같은 항목."""
    return trigram_jaccard(a, b) >= 0.85


def similar(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    na, nb = _PUNCT.sub(" ", nfc(a)).strip(), _PUNCT.sub(" ", nfc(b)).strip()
    return max(fuzz.ratio(na, nb), fuzz.token_set_ratio(na, nb)) / 100.0


def best_match(text: str | None, candidates: list[tuple[str, str]], threshold: float = 0.82) -> str | None:
    """(id, 문장) 후보 중 text 와 가장 비슷한 id(문턱 미만이면 None)."""
    if not text:
        return None
    best: tuple[float, str | None] = (0.0, None)
    for cid, ctext in candidates:
        s = similar(text, ctext)
        if s > best[0]:
            best = (s, cid)
    return best[1] if best[0] >= threshold else None


# ── 조사 ─────────────────────────────────────────────────

def _has_batchim(word: str) -> bool | None:
    w = nfc(word).strip()
    if not w:
        return None
    ch = w[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return ch in "013678"
    return None


def _rieul(word: str) -> bool:
    w = nfc(word).strip()
    if not w:
        return False
    ch = w[-1]
    if "가" <= ch <= "힣":
        return (ord(ch) - 0xAC00) % 28 == 8
    return ch in "178"


def josa(word: str, pair: str) -> str:
    """josa("대표이사", "이/가") → "대표이사가". 받침을 모르면 "이(가)" 꼴."""
    a, b = pair.split("/")
    has = _has_batchim(word)
    if pair in ("으로/로", "로/으로"):
        if has is None:
            return f"{word}(으)로"
        return word + ("로" if (not has or _rieul(word)) else "으로")
    if has is None:
        return f"{word}{a}({b})"
    return word + (a if has else b)


# ── 숫자 가드(§7.4 validate_rewrite · §7.5 validate_ops) ───

_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_NUM_WITH_UNIT = re.compile(
    r"\s*\d+(?:[.,]\d+)?\s*(?:%|퍼센트|배|개|명|원|만원|억원|만|억|년|개월|월|일|시간|분|초|㎡|m2|평|대|곳|층|석|kW|kWh|MW)?")


def numbers_in(text: str | None) -> set[str]:
    return {n.replace(",", "") for n in _NUM.findall(nfc(text))}


def foreign_numbers(candidate: str, *sources: str | None) -> set[str]:
    allowed: set[str] = set()
    for s in sources:
        allowed |= numbers_in(s)
    return {n for n in numbers_in(candidate) if n not in allowed}


def strip_numbers(text: str, numbers: set[str]) -> str:
    """근거 없는 숫자(+단위)를 문장에서 지운다."""
    out = text

    def repl(m: re.Match[str]) -> str:
        num = _NUM.search(m.group(0))
        if num and num.group(0).replace(",", "") in numbers:
            return " "
        return m.group(0)

    out = _NUM_WITH_UNIT.sub(repl, out)
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"\s+([·,.)])", r" \1", out)
    out = re.sub(r"\s{2,}", " ", out).strip(" ·,")
    return out.strip()


# ── 관련성(정적 mock · 엉뚱한 출력 거르기) ──────────────────

def _bigrams(text: str) -> set[str]:
    t = re.sub(r"[^0-9A-Za-z가-힣]", "", nfc(text).lower())
    return {t[i:i + 2] for i in range(len(t) - 1)}


def relevance(candidate: str | None, *sources: str | None) -> float:
    """candidate 의 글자 2-gram 중 sources 에 있는 비율."""
    c = _bigrams(candidate or "")
    if not c:
        return 0.0
    s: set[str] = set()
    for src in sources:
        s |= _bigrams(src or "")
    return len(c & s) / len(c)


def grounded(new: str | None, old: str | None, *sources: str | None, threshold: float = 0.4) -> bool:
    """new 에서 old 에 없던 부분(글자 2-gram)이 sources 에 threshold 이상 있으면 True — 답에 없는 내용을 지어낸 변경 거르기."""
    fresh = _bigrams(new or "") - _bigrams(old or "")
    if not fresh:
        return True
    s: set[str] = set()
    for src in sources:
        s |= _bigrams(src or "")
    return len(fresh & s) / len(fresh) >= threshold


def clip(text: str | None, n: int) -> str:
    t = (text or "").strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def topic_of(text: str | None, n: int = 12) -> str:
    """항목 문장에서 주제 구절(첫 ' · ' 앞, 따옴표 안) — 템플릿 질문용."""
    t = (text or "").strip()
    m = re.search(r"[‘'“\"]([^’'”\"]{2,20})[’'”\"]", t)
    if m:
        return m.group(1)
    head = re.split(r"\s*[·,(]\s*", t)[0]
    return clip(head, n)
