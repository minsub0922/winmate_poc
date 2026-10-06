"""문장 규칙(09-scenario R6 · §7.1) — 결정적 후처리.

- 경쟁사 이름 → 「기존 시스템」(사전: config/content_policy.yaml `competitor_brands`, 플랫폼 소유 · 읽기만)
- 실존 인물(역할어 + 이름, `person_patterns`) → 역할어만 남김(「배우 ○○○가」 → 「배우가」)
- 숫자 토큰 근거 대조 → 근거 없는 수치는 「[00]」(단위는 남긴다) + confirm_tokens
- 최상급 · 인증 주장(최초 · 유일 · 1위 …) → 지운다
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

import yaml
from winmate_common.env import repo_root

from . import texts

GENERIC_COMPETITOR = "기존 시스템"
PLACEHOLDER = "[00]"


@lru_cache(maxsize=1)
def _policy() -> dict[str, Any]:
    p = repo_root() / "config" / "content_policy.yaml"
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}


def competitor_names() -> list[str]:
    out: list[str] = []
    for b in _policy().get("competitor_brands") or []:
        for n in [b.get("name"), *(b.get("aliases") or [])]:
            if n and len(str(n).strip()) >= 2:
                out.append(str(n).strip())
    return sorted(set(out), key=len, reverse=True)


@lru_cache(maxsize=1)
def _competitor_re() -> re.Pattern[str] | None:
    names = competitor_names()
    if not names:
        return None
    # 영문 이름은 낱말 경계(Apple ≠ Applepie), 한글은 그대로
    parts = []
    for n in names:
        esc = re.escape(n)
        parts.append(rf"(?<![A-Za-z]){esc}(?![A-Za-z])" if re.match(r"^[A-Za-z]", n) else esc)
    # 사전 밖 일반 표현 중 이름 자리표시(「경쟁사 A」 · 「경쟁사」)도 「기존 시스템」으로(「타사」는 허용 표현이라 둔다)
    for g in _policy().get("generic_competitor_patterns") or []:
        if str(g).startswith("경쟁사"):
            parts.append(f"(?:{g})")
    return re.compile("|".join(parts), re.IGNORECASE)


def _replace_with_josa(text: str, pattern: re.Pattern[str], repl_fn: Any) -> tuple[str, int]:
    out = []
    pos = 0
    n = 0
    for m in pattern.finditer(text):
        if m.start() < pos:
            continue
        rep = repl_fn(m)
        out.append(text[pos:m.start()])
        josa_, rest = texts.fix_following_josa(rep, text[m.end():])
        out.append(rep + josa_)
        consumed = len(text[m.end():]) - len(rest)
        pos = m.end() + consumed
        n += 1
    out.append(text[pos:])
    return "".join(out), n


def scrub_competitors(text: str) -> tuple[str, int]:
    pat = _competitor_re()
    if pat is None or not text:
        return text, 0
    return _replace_with_josa(text, pat, lambda m: GENERIC_COMPETITOR)


@lru_cache(maxsize=1)
def _person_re() -> re.Pattern[str]:
    pats = _policy().get("person_patterns") or [
        r"(?:배우|가수|모델|아나운서|선수|연예인|탤런트|아이돌|방송인|대통령|장관|회장)\s*[가-힣○OＯ]{2,4}"]
    return re.compile("|".join(f"(?:{p})" for p in pats))


_ROLE_WORD = re.compile(r"^(배우|가수|모델|아나운서|선수|연예인|탤런트|아이돌|방송인|대통령|장관|회장)")


_PARTICLE_TAIL = ("이", "가", "은", "는", "을", "를", "과", "와", "로", "도", "의")


def scrub_people(text: str) -> tuple[str, int]:
    """「배우 ○○○가 방문」 → 「배우가 방문」(이름은 지우고 역할어만, 뒤 조사는 역할어 발음에 맞춘다)."""
    if not text:
        return text, 0
    pat = _person_re()
    out: list[str] = []
    pos = 0
    n = 0
    for m in pat.finditer(text):
        if m.start() < pos:
            continue
        end = m.end()
        name_part = m.group(0)
        # 이름 패턴이 뒤 조사까지 삼켰으면(○○○가) 조사는 남긴다
        if len(name_part) >= 4 and name_part[-1] in _PARTICLE_TAIL:
            end -= 1
        role = _ROLE_WORD.match(name_part)
        rep = role.group(1) if role else "방문객"
        out.append(text[pos:m.start()])
        josa_, rest = texts.fix_following_josa(rep, text[end:])
        out.append(rep + josa_)
        pos = end + (len(text[end:]) - len(rest))
        n += 1
    out.append(text[pos:])
    return "".join(out), n


_CLAIMS = re.compile(r"(업계\s*최초|국내\s*최초|세계\s*최초|최초로|유일하게|유일한|업계\s*1위|국내\s*1위|세계\s*1위|No\.\s*1|넘버원)\s*")


def scrub_claims(text: str) -> str:
    return _CLAIMS.sub("", text or "")


def clean(text: str) -> str:
    """경쟁사 · 실존 인물 · 최상급 주장 후처리(생성 문장 공통)."""
    t, _ = scrub_competitors(text or "")
    t, _ = scrub_people(t)
    return scrub_claims(t)


# ── 숫자 토큰 근거 대조 ─────────────────────────────────────

_UNITS = ("개월", "시간", "가지", "단계", "인치", "개", "곳", "분", "초", "대", "명", "배", "원", "건", "회", "일", "주", "년",
          "층", "평", "번", "팀", "%", "퍼센트", "℃", "도", "m", "㎡", "kWh", "W")
_NUM = re.compile(r"(?<![A-Za-z0-9:.\[])(\d+(?:[.,]\d+)?)(\s?)(" + "|".join(re.escape(u) for u in _UNITS) + r")?(?![A-Za-z0-9:])")


def number_tokens(text: str) -> list[re.Match[str]]:
    out = []
    for m in _NUM.finditer(text or ""):
        # 시각(07:00) · 모델코드(QM55C) · 「×3」 수량 칩은 문장 수치가 아니다
        before = text[max(0, m.start() - 1):m.start()]
        if before in ("×", "x", "X", "v", "V"):
            continue
        out.append(m)
    return out


def _digits(s: str) -> str:
    return s.replace(",", "")


def evidence_numbers(corpus: str) -> set[str]:
    nums = set()
    for m in re.finditer(r"\d+(?:[.,]\d+)?", corpus or ""):
        nums.add(_digits(m.group(0)))
    return nums


def mark_unsupported(text: str, corpus: str) -> tuple[str, list[dict[str, Any]]]:
    """근거(corpus)에 없는 수치를 「[00]」으로 바꾼다 → (문장, confirm_tokens)."""
    if not text:
        return text, []
    allowed = evidence_numbers(corpus)
    replaced = 0
    out = []
    pos = 0
    for m in number_tokens(text):
        if _digits(m.group(1)) in allowed:
            continue
        out.append(text[pos:m.start()])
        out.append(PLACEHOLDER + (m.group(3) or ""))
        pos = m.end()
        replaced += 1
    out.append(text[pos:])
    result = "".join(out)
    return result, placeholder_tokens(result) if replaced else []


def placeholder_tokens(text: str) -> list[dict[str, Any]]:
    """문장 속 「[00]」마다 {text, near, kind} — near 는 앞뒤 조각(확정 필요 목록 · 시트 각주)."""
    tokens = []
    idx = 0
    while True:
        j = (text or "").find(PLACEHOLDER, idx)
        if j < 0:
            break
        tokens.append({"text": PLACEHOLDER, "near": texts.clip(text[max(0, j - 14): j + 18], 40), "kind": "number"})
        idx = j + len(PLACEHOLDER)
    return tokens


def count_placeholders(text: str) -> int:
    return (text or "").count(PLACEHOLDER)
