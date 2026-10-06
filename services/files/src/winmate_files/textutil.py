"""글자 인코딩 판별과 텍스트 정리."""
from __future__ import annotations

import re
import unicodedata

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​﻿]")
_MULTI_BLANK = re.compile(r"\n{3,}")
_TRAIL_WS = re.compile(r"[ \t　]+\n")


def _hangul_ratio(s: str) -> float:
    if not s:
        return 0.0
    letters = [ch for ch in s if not ch.isspace() and not ch.isascii()]
    if not letters:
        return 1.0
    good = sum(1 for ch in letters if "가" <= ch <= "힣" or "㄰" <= ch <= "㆏"
               or unicodedata.category(ch).startswith("P") or " " <= ch <= "⯿" or "一" <= ch <= "鿿")
    return good / len(letters)


def decode_text(data: bytes) -> tuple[str, str]:
    """(문자열, 인코딩). BOM → utf-8 → cp949(euc-kr 상위) → utf-16 추정 → latin-1."""
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", "replace"), "utf-8-sig"
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", "replace"), "utf-16"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError as exc:
        if exc.start >= len(data) - 3:  # 끝에서 잘린 멀티바이트 문자
            return data.decode("utf-8", "replace"), "utf-8"
    try:
        s = data.decode("cp949")
        if _hangul_ratio(s) >= 0.6:
            return s, "cp949"
    except UnicodeDecodeError:
        pass
    sample = data[:4000]
    if sample and sample.count(b"\x00") > len(sample) // 4:
        enc = "utf-16-le" if sample[1::2].count(b"\x00") > sample[0::2].count(b"\x00") else "utf-16-be"
        return data.decode(enc, "replace"), enc
    try:
        return data.decode("cp949"), "cp949"
    except UnicodeDecodeError:
        pass
    return data.decode("latin-1"), "latin-1"


def http_charset(encoding: str | None) -> str | None:
    if not encoding:
        return None
    e = encoding.lower()
    if e.startswith("utf-8"):
        return "utf-8"
    if e in ("cp949", "euc-kr", "uhc", "ks_c_5601-1987"):
        return "euc-kr"  # 브라우저(WHATWG)는 euc-kr 라벨로 cp949 를 읽는다
    if e.startswith("utf-16"):
        return "utf-16"
    if e == "latin-1":
        return "iso-8859-1"
    return e


def clean(s: str | None) -> str:
    """NFC · 줄바꿈 통일 · 제어 문자 제거 · 줄 끝 공백 · 빈 줄 3개 이상 줄임."""
    if not s:
        return ""
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n").replace("\x0b", "\n").replace("\x0c", "\n")
    s = s.replace(" ", " ").replace(" ", "\n").replace(" ", "\n")
    s = _CTRL.sub("", s)
    s = _TRAIL_WS.sub("\n", s)
    s = _MULTI_BLANK.sub("\n\n", s)
    return s.strip()


def one_line(s: str | None, limit: int = 200) -> str:
    t = re.sub(r"\s+", " ", clean(s)).strip()
    return t[:limit]


_BULLET = re.compile(
    r"^\s*(?:[•◦▪▫‣⁃∙·○●◎□■◇◆▶▷►▸➢➤✓✔※\-\*–—ㅇ]|"
    r"\(?\d{1,3}[\.\)]|[①-⑳]|\(?[가-하][\.\)]|\(?[a-zA-Z][\.\)]|[ⅰ-ⅹⅠ-Ⅹ][\.\)]?)\s+"
)
_CAPTION = re.compile(r"^\s*[<\[(]?\s*(그림|표|사진|도표|figure|fig\.|table|chart)\s*[\d\-.]+", re.I)


def is_bullet(line: str) -> bool:
    return bool(_BULLET.match(line))


def is_caption(text: str) -> bool:
    return bool(_CAPTION.match(text)) and len(text) <= 160


def first_line(s: str, limit: int = 120) -> str | None:
    for line in (s or "").split("\n"):
        t = line.strip()
        if t:
            return t[:limit]
    return None
