"""사실 검사 · 누출 검사(§10.12, 결정적 — 모델을 부르지 않는다).

V1 수치(content.ground_body) · V4 모델코드 · V5 경쟁사 실명 · V8 주장(claim) · V10 비복제 줄. V9 는 facts.sync_items.
"""
from __future__ import annotations

import re
from typing import Any

from . import content as C, defs

MODEL_RE = re.compile(r"\b([A-Z]{2}\d{2}[A-Z]{1,2}\d?[A-Z]{0,3})\b")
ANON = ("경쟁사 A", "경쟁사 B", "경쟁사 C", "경쟁사 D", "경쟁사 E", "경쟁사 F")


def text_of(obj: Any) -> str:
    out: list[str] = []

    def fn(t: str, _p: str) -> str:
        out.append(t)
        return t
    C.walk_strings(obj, fn)
    return "\n".join(out)


# ── V4 모델코드 ────────────────────────────────────────────
def models_in(obj: Any) -> set[str]:
    return {m.group(1) for m in MODEL_RE.finditer(text_of(obj))}


def check_models(body: dict[str, Any], known: set[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """입력에 없는 모델코드는 지우고(「[확인 필요]」) 기록한다."""
    misses: list[dict[str, Any]] = []
    if not known:
        known = set()

    def ok(code: str) -> bool:
        return code in known or any(k.startswith(code) or code.startswith(k) for k in known if len(k) >= 5)

    def fn(t: str, path: str) -> str:
        if path.startswith("/signals") or path.startswith("/images"):
            return t

        def rep(m: re.Match[str]) -> str:
            if ok(m.group(1)):
                return m.group(0)
            misses.append({"code": m.group(1), "path": path, "pre": t[max(0, m.start() - 20):m.start()], "post": t[m.end():m.end() + 16]})
            return "[모델 확인 필요]"
        return MODEL_RE.sub(rep, t)
    new = C.walk_strings({k: v for k, v in body.items() if k not in ("signals", "images", "series")}, fn)
    for k in ("signals", "images", "series"):
        if k in body:
            new[k] = body[k]
    return new, misses


# ── V5 경쟁사 실명 ─────────────────────────────────────────
def real_name_map(items: list[dict[str, Any]], links: list[dict[str, Any]]) -> dict[str, str]:
    """반입 내용의 실명 표(익명 라벨 → 실명)를 뒤집는다 → {실명: 익명 라벨}."""
    out: dict[str, str] = {}
    for it in items:
        c = it.get("content") or {}
        for anon, real in (c.get("real_names") or {}).items():
            if real and isinstance(real, str):
                out[real] = anon
    for ln in links:
        snap = ln.get("handoff") or {}
        for it in snap.get("items") or []:
            for anon, real in ((it.get("content") or {}).get("real_names") or {}).items():
                if real and isinstance(real, str):
                    out.setdefault(real, anon)
    return out


def anonymize(body: dict[str, Any], names: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    if not names:
        return body, []
    hit: list[str] = []
    order = sorted(names, key=len, reverse=True)
    pat = re.compile("|".join(re.escape(n) for n in order))

    def fn(t: str, _path: str) -> str:
        def rep(m: re.Match[str]) -> str:
            hit.append(m.group(0))
            return names[m.group(0)]
        return pat.sub(rep, t)
    new = C.walk_strings({k: v for k, v in body.items() if k != "signals"}, fn)
    new["signals"] = body.get("signals") or {}
    return new, sorted(set(hit))


# ── V8 주장 ───────────────────────────────────────────────
def claims(body: dict[str, Any], allowed_text: str) -> list[dict[str, Any]]:
    """입력 원문에 없는 단정 표현 → 확인 항목 후보(문장은 그대로 둔다)."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def fn(t: str, path: str) -> str:
        if path.startswith("/signals"):
            return t
        for w in defs.CLAIM_WORDS:
            i = t.find(w)
            if i >= 0 and w not in allowed_text and (path, w) not in seen:
                seen.add((path, w))
                out.append({"word": w, "path": path, "pre": t[max(0, i - 24):i], "post": t[i + len(w):i + len(w) + 16]})
        return t
    C.walk_strings({k: v for k, v in body.items() if k not in ("signals", "images")}, fn)
    return out


# ── V10 비복제 줄(기존 제안서 활용) ─────────────────────────
def strip_noncopy(lines: list[str]) -> list[str]:
    return [x for x in lines if not any(k in x for k in defs.NONCOPY_KEYWORDS)]
