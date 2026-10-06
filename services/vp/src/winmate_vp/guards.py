"""결정적 검증(05-vp.md §7.7 · 검토 노드) — 시트 문장 속 숫자 · 경쟁사 이름 · claim · 이미지 메타.

1. 숫자 토큰마다 근거(재료 · 수치 · KB 메시지 · 견적 · 계산값)에 같은 수가 있어야 한다. 없으면 `[00]`(단위 유지).
2. 경쟁사 이름: 결정이 `경쟁사 언급 없음`이면 그 문장을 뺀다.
3. claim(최초 · 유일 · 1위 · 최고 …) 문구는 확인할 것(요청)으로 남긴다.
"""
from __future__ import annotations

import re
from typing import Any

from . import imagesel, numbers

NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
COUNT_WORDS = ("가지", "개", "장", "단계", "곳", "명", "종", "건", "배", "년", "월", "분기", "층", "위")
CLAIM_RE = re.compile(r"최초|유일|1위|최고|최대|업계 최|No\.?\s?1", re.I)


def _norm(tok: str) -> str:
    t = tok.replace(",", "")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t


def allowed_numbers(doc: dict[str, Any]) -> set[str]:
    """근거로 쓸 수 있는 수(정규화 문자열)."""
    texts: list[str] = [doc.get("customer_name") or "", doc.get("title") or "", (doc.get("industry") or {}).get("name") or ""]
    f = doc.get("facts") or {}
    for m in doc.get("materials") or []:
        texts.append(m.get("text") or "")
        if m.get("number"):
            texts.append(str((m["number"] or {}).get("display") or ""))
            for k in ("value", "value2"):
                if (m["number"] or {}).get(k) is not None:
                    texts.append(numbers.fmt_num(float(m["number"][k])))
    for mt in f.get("metrics") or []:
        for side in ("before", "after"):
            v = mt.get(side) or {}
            texts.append(str(v.get("display") or ""))
    for s in doc.get("sheets") or []:
        for mt in (s.get("content") or {}).get("metrics") or []:
            for side in ("before", "after"):
                texts.append(str((mt.get(side) or {}).get("display") or ""))
        roi = (s.get("content") or {}).get("roi") or {}
        for p in roi.get("payback_months") or []:
            texts.append(numbers.fmt_num(float(p)))
        texts.append(str((roi.get("investment") or {}).get("display") or ""))
        for sv in roi.get("savings") or []:
            texts.append(str(sv.get("display") or ""))
    for k in f.get("kb_messages") or []:
        texts.append(k.get("text") or "")
    q = f.get("quote") or {}
    if q.get("total"):
        texts.append(numbers.money_ko(q["total"]))
        texts.append(numbers.fmt_num(q["total"]))
    for c in ((f.get("rfp") or {}).get("evaluation_criteria") or []):
        texts.append(f"{c.get('name')} {c.get('points')}")
    for p in f.get("products") or []:
        texts.append(p.get("name") or "")
    out: set[str] = set()
    for t in texts:
        for tok in NUM.findall(t or ""):
            out.add(_norm(tok))
    return out


def scrub(text: str, allowed: set[str]) -> tuple[str, int]:
    """근거 없는 숫자 → `[00]`(뒤의 단위는 그대로). 작은 개수(10 이하 + 가지 · 개 · 장 …)와 제품 코드 속 숫자는 둔다."""
    if not text or "[" in text and not NUM.search(re.sub(r"\[[^\]]*\]", "", text)):
        return text, 0
    n = 0
    out = []
    pos = 0
    for m in NUM.finditer(text):
        tok = m.group(0)
        start, end = m.span()
        prev = text[start - 1] if start > 0 else " "
        nxt = text[end:end + 3]
        inside_code = prev.isalpha() and prev.isascii() or (nxt[:1].isalpha() and nxt[:1].isascii()) or text[max(0, start - 2):start] == "p."
        in_bracket = text.rfind("[", 0, start) > text.rfind("]", 0, start)
        small_count = tok.isdigit() and int(tok) <= 10 and any(nxt.strip().startswith(w) for w in COUNT_WORDS)
        if inside_code or in_bracket or small_count or _norm(tok) in allowed:
            continue
        out.append(text[pos:start])
        out.append("[00]")
        pos = end
        n += 1
    out.append(text[pos:])
    return "".join(out), n


def _walk(content: dict[str, Any]) -> list[tuple[dict[str, Any], str]]:
    """검사할 (객체, 필드) 목록."""
    out: list[tuple[dict[str, Any], str]] = []
    for ch in content.get("challenges") or []:
        out += [(ch, "title"), (ch, "body")]
    for p in content.get("pillars") or []:
        out += [(p, "title"), (p, "body")]
    if content.get("one_liner"):
        out.append((content["one_liner"], "statement"))
    for s in content.get("stakeholders") or []:
        out += [(s, "value"), (s, "kpi")]
    for p in content.get("pairs") or []:
        out += [(p, "value"), (p, "challenge")]
    return out


def verify_sheet(doc: dict[str, Any], sheet: dict[str, Any], allowed: set[str] | None = None,
                 *, competitors: list[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """→ (고친 시트, 보고{numbers, competitor, claims})."""
    allowed = allowed if allowed is not None else allowed_numbers(doc)
    rep = {"numbers": 0, "competitor": 0, "claims": 0}
    for fld in ("title", "points"):
        sheet[fld], k = scrub(sheet.get(fld) or "", allowed)
        rep["numbers"] += k
    c = sheet.get("content") or {}
    for obj, fld in _walk(c):
        if isinstance(obj.get(fld), str):
            obj[fld], k = scrub(obj[fld], allowed)
            rep["numbers"] += k
    if c.get("one_liner"):
        ev = []
        for e in c["one_liner"].get("evidence") or []:
            e2, k = scrub(e, allowed)
            rep["numbers"] += k
            ev.append(e2)
        c["one_liner"]["evidence"] = ev
    if c.get("qualitative"):
        q = []
        for e in c["qualitative"]:
            e2, k = scrub(e, allowed)
            rep["numbers"] += k
            q.append(e2)
        c["qualitative"] = q
    names = [n for n in (competitors or []) if n and len(n) >= 2]
    if names:
        for obj, fld in _walk(c) + [(sheet, "title"), (sheet, "points")]:
            v = obj.get(fld)
            if isinstance(v, str) and any(n in v for n in names):
                parts = [p for p in re.split(r"(?<=[.·])\s+", v) if not any(n in p for n in names)]
                obj[fld] = " ".join(parts).strip() or "[확인 필요]"
                rep["competitor"] += 1
    for obj, fld in _walk(c) + [(sheet, "title")]:
        if isinstance(obj.get(fld), str) and CLAIM_RE.search(obj[fld]):
            rep["claims"] += 1
    return sheet, rep


def competitor_names(doc: dict[str, Any]) -> list[str]:
    """`톤 · 경쟁사 언급 없음` 결정일 때 막을 이름(RFP 에서 언급된 경쟁사)."""
    rows = (doc.get("plan") or {}).get("decisions") or []
    tone = next((r for r in rows if r.get("key") == "톤"), None)
    if tone and "언급 없음" not in (tone.get("value") or ""):
        return []
    return [m.get("name") for m in ((doc.get("facts") or {}).get("rfp") or {}).get("competitor_mentions") or [] if m.get("name")]


def images_ok(doc: dict[str, Any]) -> list[str]:
    """§7.7-5 — 메타가 빠진 이미지 칸 id."""
    return [s["id"] for s in doc.get("image_slots") or [] if not imagesel.meta_complete(s)]
