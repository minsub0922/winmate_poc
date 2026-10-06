"""경쟁사 표기(03-mi.md §5.6 display_name) · 내보내기 익명 처리."""
from __future__ import annotations

import re
from typing import Any

from . import rules


def live(competitors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted([c for c in competitors or [] if not c.get("removed")], key=lambda c: (c.get("order", 0), c.get("letter", "")))


def workspace_label(c: dict[str, Any]) -> str:
    return f"경쟁사 {c.get('letter', '')}"


def preview_label(c: dict[str, Any], anonymize: bool, naming_mode: str, all_live: list[dict[str, Any]] | None = None) -> tuple[str, str]:
    """MI2C 행 표기 규칙(보드 로직) → (표기, 설명)."""
    kind = c.get("kind_label") or "[확인 필요]"
    desc = c.get("desc") or ""
    if not anonymize:
        return f"{c.get('real_name', '')} · 사내용", f"{kind} · {desc}".strip(" ·")
    if naming_mode == "type":
        labels = export_map(all_live or [c], True, "type")
        return labels.get(c["id"], kind), desc
    return workspace_label(c), f"{kind} · {desc}".strip(" ·")


def export_map(competitors: list[dict[str, Any]], anonymize: bool, naming_mode: str,
               included_ids: list[str] | None = None) -> dict[str, str]:
    """export_customer 표기. 익명 + letter → 포함된 경쟁사끼리 A, B, C … 다시 붙임 / type → 유형(같으면 1 · 2) / 익명 꺼짐 → 실명."""
    comps = [c for c in live(competitors) if included_ids is None or c["id"] in included_ids]
    if not anonymize:
        return {c["id"]: c.get("real_name") or workspace_label(c) for c in comps}
    if naming_mode == "type":
        counts: dict[str, int] = {}
        for c in comps:
            k = c.get("kind_label") or "경쟁사"
            counts[k] = counts.get(k, 0) + 1
        seen: dict[str, int] = {}
        out = {}
        for c in comps:
            k = c.get("kind_label") or "경쟁사"
            if counts[k] > 1:
                seen[k] = seen.get(k, 0) + 1
                out[c["id"]] = f"{k} {seen[k]}"
            else:
                out[c["id"]] = k
        return out
    letters = rules.letters(len(comps))
    return {c["id"]: f"경쟁사 {letters[i]}" for i, c in enumerate(comps)}


def real_strings(competitors: list[dict[str, Any]]) -> list[str]:
    out = []
    for c in competitors or []:
        for s in [c.get("real_name"), *(c.get("aliases") or [])]:
            if s and len(s.strip()) >= 2:
                out.append(s.strip())
    return sorted(set(out), key=len, reverse=True)


def scrub(obj: Any, competitors: list[dict[str, Any]], mapping: dict[str, str]) -> Any:
    """묶음 · 내보내기 원본에서 실명 · 별칭 문자열을 표기로 바꾼다(안전망, AC-MI-67)."""
    repl: list[tuple[re.Pattern[str], str]] = []
    for c in competitors or []:
        label = mapping.get(c["id"]) or workspace_label(c)
        for s in [c.get("real_name"), *(c.get("aliases") or [])]:
            if s and len(s.strip()) >= 2:
                repl.append((re.compile(re.escape(s.strip()), re.IGNORECASE), label))
    repl.sort(key=lambda t: -len(t[0].pattern))

    def walk(x: Any) -> Any:
        if isinstance(x, str):
            for pat, lab in repl:
                x = pat.sub(lab, x)
            return x
        if isinstance(x, list):
            return [walk(i) for i in x]
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        return x

    return walk(obj)


def contains_real(obj: Any, competitors: list[dict[str, Any]]) -> bool:
    import json

    s = json.dumps(obj, ensure_ascii=False).lower()
    return any(r.lower() in s for r in real_strings(competitors))
