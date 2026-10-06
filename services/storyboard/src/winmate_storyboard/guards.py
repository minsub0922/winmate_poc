"""결정적 가드(02-storyboard.md §7.0) — 모든 고객용 문장 출력 뒤에 돈다.

1. 숫자 가드: 입력(정의서 · 기획 답 · 공간 답 · KB 근거)에 없는 수치 → `[00]`
2. 주장 가드: `최초` · `유일` · `1위` · `No.1` · `최고` · `최대` … → 메시지 `unverified_claim` / 섹션 `확인 필요`
3. 내부 목표 가드: 제작자 의견의 내부 목표 구절 + 사전(`스펙인` · `영업 목표` · `수주` · `매출 목표` · `점유율`) → 고객 문장에서 빼고 내부 메모로
4. 토큰 보존: 수정 · 동기화 전후로 `[00]` · `[확인 필요]` 수와 `검토 중` 줄이 줄면 원래 줄 유지
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .rules import tokens_of

# ── 1. 숫자 가드 ───────────────────────────────────────────

_UNITS = r"(%|％|배|만원|억원|원|억|만|천|시간|개월|분|초|kWh|MWh|kW|W|㎡|m²|평|명|대|년|℃|°C|dB)"
_NUM_RE = re.compile(r"(?<![A-Za-z0-9\-.\[/])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s?" + _UNITS)
_ANY_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def numbers_in(texts: Iterable[str | None]) -> set[str]:
    """입력 글에 나온 숫자(쉼표 없앤 형태) — 숫자 가드의 허용 목록."""
    out: set[str] = set()
    for t in texts:
        for m in _ANY_NUM.findall(t or ""):
            out.add(m.replace(",", ""))
            if "." in m:
                out.add(m.split(".")[0].replace(",", ""))
    return out


def number_guard(text: str, allowed: set[str]) -> tuple[str, bool]:
    """입력에 없는 수치(단위가 붙은 숫자)를 `[00]` 으로 바꾼다 → (새 문장, 바꿨는지)."""
    changed = False

    def repl(m: re.Match[str]) -> str:
        nonlocal changed
        num = (m.group(1) + (m.group(2) or "")).replace(",", "")
        if num in allowed:
            return m.group(0)
        changed = True
        unit = m.group(3)
        sep = " " if m.group(0)[len(m.group(1) + (m.group(2) or "")):].startswith(" ") else ""
        return f"[00]{sep}{unit}"

    return _NUM_RE.sub(repl, text or ""), changed


def unsourced_numbers(text: str, allowed: set[str]) -> list[tuple[int, int, str]]:
    """사람이 쓴 문장 속 근거 없는 수치 구간(메시지 표현 검사용)."""
    out = []
    for m in _NUM_RE.finditer(text or ""):
        num = (m.group(1) + (m.group(2) or "")).replace(",", "")
        if num not in allowed:
            out.append((m.start(), m.end(), m.group(0)))
    return out


# ── 2. 주장 가드 ───────────────────────────────────────────

_CLAIM_RE = re.compile(
    r"((?:국내|세계|업계|아시아|국내외)\s?)?(최초|유일(?:한)?|1위|No\.?\s?1|넘버\s?원|최고(?!\s?경영|경영|급)|최대(?!한|화)|최소(?!한|화)|최저(?!한)|최장)"
)


@dataclass
class Claim:
    start: int
    end: int
    word: str


def find_claims(text: str) -> list[Claim]:
    return [Claim(m.start(), m.end(), m.group(0)) for m in _CLAIM_RE.finditer(text or "")]


def claim_phrase(text: str, claim: Claim) -> tuple[int, int]:
    """주장 단어부터 이어지는 명사구(다음 구두점 · 조사 앞)까지 — 표시 구간 기본값."""
    end = claim.end
    rest = text[end:]
    m = re.match(r"(\s?[A-Za-z0-9가-힣·\-]+){0,3}", rest)
    if m:
        seg = m.group(0)
        # 조사로 끝나면 조사 앞까지
        seg = re.sub(r"(으로|로|을|를|이|가|은|는|의|에서|에|과|와|도)$", "", seg)
        end += len(seg)
    return claim.start, end


def strip_claims(text: str) -> str:
    """대체안을 못 받았을 때의 결정적 대체안 — 주장 단어만 뺀다."""
    out = _CLAIM_RE.sub("", text or "")
    return re.sub(r"\s{2,}", " ", out).strip()


# ── 3. 내부 목표 가드 ───────────────────────────────────────

INTERNAL_WORDS = ["스펙인", "영업 목표", "영업목표", "수주", "매출 목표", "점유율"]
_SEPS = [" — ", " – ", " - ", ", ", " · ", "—", ",", "·"]


@dataclass
class Internal:
    start: int
    end: int
    span_text: str


def _clause_bounds(text: str, idx: int) -> tuple[int, int]:
    """idx 를 포함하는 절(구분자 사이)의 경계."""
    start = 0
    for sep in _SEPS:
        p = text.rfind(sep, 0, idx)
        if p >= 0:
            start = max(start, p + len(sep))
    end = len(text)
    for sep in _SEPS + [".", "!", "?"]:
        p = text.find(sep, idx)
        if p >= 0:
            end = min(end, p)
    return start, end


def find_internal(text: str, phrases: Iterable[str] = ()) -> list[Internal]:
    found: list[Internal] = []
    taken: list[tuple[int, int]] = []
    for ph in sorted({p.strip() for p in phrases if p and p.strip()}, key=len, reverse=True):
        i = text.find(ph)
        if i >= 0 and not any(a <= i < b for a, b in taken):
            found.append(Internal(i, i + len(ph), ph))
            taken.append((i, i + len(ph)))
    for w in INTERNAL_WORDS:
        for m in re.finditer(re.escape(w), text):
            if any(a <= m.start() < b for a, b in taken):
                continue
            a, b = _clause_bounds(text, m.start())
            span = text[a:b].strip()
            a = text.find(span, a)
            # 조사 · 어미는 빼고(구간 끝에서) 보인다
            span = re.sub(r"(까지|으로|로|을|를|이|가|은|는|의|에서|에|도|이다|입니다)$", "", span).strip()
            if span:
                found.append(Internal(a, a + len(span), span))
                taken.append((a, a + len(span)))
    found.sort(key=lambda x: x.start)
    return found


def remove_span(text: str, start: int, end: int) -> str:
    """구간과 붙은 조사 · 앞 구분자를 함께 뺀다. 남는 문장의 끝 구두점은 지킨다."""
    # 붙은 조사(공백 전까지의 한글 1–3자 중 조사 · 어미)
    m = re.match(r"(까지|으로|로|을|를|이|가|은|는|의|에서|에|도)", text[end:])
    if m:
        end += len(m.group(0))
    before, after = text[:start], text[end:]
    stripped_before = before.rstrip()
    for sep in (" —", " –", " -", ",", " ·", "—", "·"):
        if stripped_before.endswith(sep.strip()) and stripped_before:
            stripped_before = stripped_before[: -len(sep.strip())].rstrip()
            break
    else:
        # 앞에 구분자가 없으면 뒤 구분자를 뺀다
        after = re.sub(r"^\s*(—|–|-|,|·)\s*", "", after)
    out = stripped_before + after
    out = re.sub(r"\s+([.,!?])", r"\1", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


# ── 4. 토큰 보존 ───────────────────────────────────────────

def token_count(text: str) -> int:
    return len(tokens_of(text))


def loses_tokens(before: str, after: str | None) -> bool:
    """수정 뒤 `[00]` · `[확인 필요]` 가 줄었는가(줄이 사라져도 줄어든 것)."""
    b = tokens_of(before or "")
    a = tokens_of(after or "")
    return any(a.count(t) < b.count(t) for t in set(b))
