"""글자 맞춤 — 상자에 들어가도록 글자 크기를 단계적으로 줄이고, 그래도 넘치면 말줄임(…)으로 자른다.

폭은 Pillow 로 실제 글꼴(Noto Sans CJK · 나눔고딕)을 재고, 글꼴 파일이 없으면 글자 종류별 너비 추정치를 쓴다.
PowerPoint 줄바꿈과 완전히 같지 않으므로 여유(SLACK)를 둔다. 단위는 1280 × 720 캔버스 px.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SLACK = 0.94                     # 폭의 94%만 쓴다고 보고 잰다
SCALES = (1.0, 0.92, 0.85, 0.78, 0.72, 0.66)
ELLIPSIS = "…"

FONT_CANDIDATES = {
    False: [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ],
    True: [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ],
}


@lru_cache(maxsize=4)
def _font_path(bold: bool) -> str | None:
    for p in FONT_CANDIDATES[bold]:
        if Path(p).is_file():
            return p
    return None


@lru_cache(maxsize=256)
def _font(bold: bool, size10: int):
    from PIL import ImageFont

    path = _font_path(bold)
    if not path:
        return None
    try:
        # .ttc 0번 = JP · 1번 = KR(한글 폭은 같다)
        return ImageFont.truetype(path, size=max(1, size10 // 10), index=1 if path.endswith(".ttc") else 0)
    except Exception:  # noqa: BLE001
        try:
            return ImageFont.truetype(path, size=max(1, size10 // 10))
        except Exception:  # noqa: BLE001
            return None


def _heuristic(ch: str) -> float:
    if ch == " ":
        return 0.28
    o = ord(ch)
    if 0xAC00 <= o <= 0xD7A3 or 0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF or unicodedata.east_asian_width(ch) in "WF":
        return 1.0
    if ch.isdigit():
        return 0.58
    if ch.isupper():
        return 0.68
    if ch.isalpha():
        return 0.54
    return 0.4


_CHAR_W: dict[bool, dict[str, float]] = {False: {}, True: {}}


def _char_width(ch: str, bold: bool) -> float:
    """100px 기준 글자 폭(글자별 캐시 — 커닝은 무시하므로 살짝 넉넉하게 잰다)."""
    table = _CHAR_W[bold]
    w = table.get(ch)
    if w is None:
        font = _font(bold, 1000)
        w = 0.0
        if font is not None:
            try:
                w = float(font.getlength(ch))
            except Exception:  # noqa: BLE001
                w = 0.0
        if w <= 0 and ch not in "\u200b\u200c\u200d":
            w = _heuristic(ch) * 100.0 * (1.04 if bold else 1.0)
        table[ch] = w
    return w


def text_width(text: str, size: float, bold: bool = False) -> float:
    """글자 크기 size(px)일 때 폭(px)."""
    if not text:
        return 0.0
    return sum(_char_width(ch, bold) for ch in text) * size / 100.0


def wrap(text: str, width: float, size: float, bold: bool = False) -> list[str]:
    """단어(공백) 단위 줄바꿈. 한 단어가 폭보다 길면 글자 단위로 나눈다."""
    out: list[str] = []
    for para in str(text).split("\n"):
        line = ""
        for word in re.split(r" +", para.strip()):
            if not word:
                continue
            cand = f"{line} {word}" if line else word
            if text_width(cand, size, bold) <= width:
                line = cand
                continue
            if line:
                out.append(line)
                line = ""
            if text_width(word, size, bold) <= width:
                line = word
                continue
            cur = ""
            for ch in word:
                if cur and text_width(cur + ch, size, bold) > width:
                    out.append(cur)
                    cur = ch
                else:
                    cur += ch
            line = cur
        out.append(line)
    return out


@dataclass
class Para:
    text: str
    size: float          # px
    bold: bool = False
    line: float = 1.3    # 줄 간격(배수)
    space_before: float = 0.0   # px
    shrink: bool = True  # 크기 줄이기 대상
    cut: bool = True     # 넘치면 자르기 대상
    color: str = "ink"   # 그리기용 꼬리표(맞춤 계산에는 쓰지 않음)
    number: bool = False
    align: str = "left"
    url: str | None = None


@dataclass
class Fitted:
    paras: list[Para]
    scale: float
    truncated: bool
    height: float


def measure(paras: list[Para], width: float, scale: float) -> float:
    h = 0.0
    for i, p in enumerate(paras):
        s = p.size * (scale if p.shrink else 1.0)
        n = max(1, len(wrap(p.text, width * SLACK, s, p.bold)))
        h += n * s * p.line + (p.space_before * scale if i else 0)
    return h


def truncate_to(p: Para, width: float, max_lines: int, scale: float) -> str:
    s = p.size * (scale if p.shrink else 1.0)
    lines = wrap(p.text, width * SLACK, s, p.bold)
    if len(lines) <= max_lines:
        return p.text
    keep = lines[:max(1, max_lines)]
    last = keep[-1]
    while last and text_width(last + ELLIPSIS, s, p.bold) > width * SLACK:
        last = last[:-1]
    keep[-1] = last.rstrip() + ELLIPSIS
    return " ".join(k for k in keep if k)


def fit(paras: list[Para], width: float, height: float, min_scale: float = 0.66) -> Fitted:
    """크기를 SCALES 순서로 줄여 보고, 그래도 넘치면 뒤 문단부터 잘라 맞춘다."""
    paras = [p for p in paras if p.text]
    if not paras or width <= 4 or height <= 4:
        return Fitted(paras, 1.0, False, 0.0)
    scale = 1.0
    for sc in SCALES:
        if sc < min_scale:
            break
        scale = sc
        h = measure(paras, width, sc)
        if h <= height:
            return Fitted(paras, sc, False, h)
    # 자르기 — 뒤에서부터(자르기 대상만) 줄 수를 줄인다
    out = [Para(**p.__dict__) for p in paras]
    for idx in range(len(out) - 1, -1, -1):
        p = out[idx]
        if not p.cut:
            continue
        others = measure(out[:idx] + out[idx + 1:], width, scale) if len(out) > 1 else 0.0
        s = p.size * (scale if p.shrink else 1.0)
        avail = height - others - (p.space_before * scale if idx else 0)
        lines = int(avail // (s * p.line))
        if lines <= 0:
            out.pop(idx)
            if measure(out, width, scale) <= height:
                return Fitted(out, scale, True, measure(out, width, scale))
            continue
        p.text = truncate_to(p, width, lines, scale)
        h = measure(out, width, scale)
        if h <= height:
            return Fitted(out, scale, True, h)
    # 마지막 수단: 첫 문단만 한 줄로
    if out:
        p = out[0]
        s = p.size * scale
        lines = max(1, int(height // (s * p.line)))
        p.text = truncate_to(p, width, lines, scale)
        return Fitted([p], scale, True, measure([p], width, scale))
    return Fitted([], scale, True, 0.0)


def clip_chars(text: str, max_chars: int | None, factor: float = 1.0) -> str:
    if not max_chars or not text:
        return text
    limit = int(max_chars * factor)
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + ELLIPSIS
