"""핵심 메시지 표현 검사(02-storyboard.md §4.9 · §7.3 check_expressions).

- 내부 목표(제작자 의견 구절 + 사전) → **자동으로** 문장에서 빼고 내부 메모로(`internal_goal`, auto_applied, `되돌리기` 가능)
- 검증 안 된 주장(최초 · 유일 · 1위 …, 사람이 쓴 문장은 출처 없는 수치도) → 대체안만 보여 주고 사람이 `바꾸기`(`unverified_claim`)
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import new_id

from . import guards, llm

log = logging.getLogger("winmate.storyboard.expr")


def _eun(word: str) -> str:
    ch = word.strip()[-1:] if word.strip() else ""
    if ch and 0xAC00 <= ord(ch) <= 0xD7A3:
        return "은" if (ord(ch) - 0xAC00) % 28 else "는"
    return "은" if ch in "0136781LMNRlmnr" else "는"


def _place_spans(text: str, flags: list[dict[str, Any]]) -> None:
    for f in flags:
        if f["kind"] == "internal_goal" and f["state"] == "applied":
            f["span"] = []
            continue
        probe = f.get("suggestion") if (f["kind"] == "unverified_claim" and f["state"] == "applied") else f["span_text"]
        i = text.find(probe or "") if probe else -1
        f["span"] = [i, i + len(probe)] if i >= 0 else []


async def _claim_fix(text: str, word: str, span_text: str) -> tuple[str, str, str]:
    """(구간, 대체안, 이유) — LLM 이 안 되면 결정적 대체안(주장 단어만 뺀 표현)."""
    note = f"'{word}'{_eun(word)} 아직 검증 전이에요"
    try:
        res = await llm.call("sb.claim_fix", llm.p_claim_fix(text, word), llm.SbClaimFix)
        span = (res.get("span_text") or "").strip()
        if not span or span not in text or word.replace(" ", "") not in span.replace(" ", ""):
            span = span_text
        sug = (res.get("suggestion") or "").strip() or guards.strip_claims(span)
        return span, sug, (res.get("note") or "").strip() or note
    except ApiError as exc:
        log.info("claim_fix 대체안 없음(%s) — 결정적 대체안", exc.code)
        return span_text, guards.strip_claims(span_text) or span_text, note


async def check(text: str, *, internal_phrases: list[str], prev_flags: list[dict[str, Any]] | None = None,
                allowed_numbers: set[str] | None = None, from_user: bool = False,
                use_llm: bool = True) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """→ (새 문장, 표시, 새 내부 메모)."""
    prev = prev_flags or []
    flags: list[dict[str, Any]] = []
    memos: list[dict[str, Any]] = []
    reverted_internal = {f["span_text"] for f in prev if f["kind"] == "internal_goal" and f["state"] == "reverted"}
    kept_internal = [f for f in prev if f["kind"] == "internal_goal" and f["state"] == "applied"]
    # 1) 내부 목표 — 사람이 되돌린 구간은 다시 빼지 않는다
    guard_round = 0
    while guard_round < 6:
        guard_round += 1
        hits = [h for h in guards.find_internal(text, internal_phrases) if h.span_text not in reverted_internal
                and not any(h.span_text == f["span_text"] for f in flags)]
        if not hits:
            break
        h = hits[0]
        new_text = guards.remove_span(text, h.start, h.end)
        if not new_text.strip():
            flags.append({"id": new_id("flg"), "kind": "internal_goal", "span": [h.start, h.end], "span_text": h.span_text,
                          "note": f"'{h.span_text}'{_eun(h.span_text)} 삼성 영업목표예요", "suggestion": None,
                          "auto_applied": False, "state": "reverted", "original_text": None})
            break
        fid = new_id("flg")
        flags.append({"id": fid, "kind": "internal_goal", "span": [], "span_text": h.span_text,
                      "note": f"'{h.span_text}'{_eun(h.span_text)} 삼성 영업목표라 고객 메시지에서 빼고 내부 메모로 옮겼어요",
                      "suggestion": None, "auto_applied": True, "state": "applied", "original_text": text})
        memos.append({"text": h.span_text, "from": "flag", "flag_id": fid})
        text = new_text
    # 이미 빠진 내부 목표 표시는 남긴다(되돌리기용) — 문장이 그 뒤 바뀌었으면 원문 대신 지금 문장에 구간을 붙여 되살린다
    for f in kept_internal:
        if not any(x["span_text"] == f["span_text"] for x in flags):
            flags.append(dict(f))
    for span in reverted_internal:
        i = text.find(span)
        if i >= 0 and not any(x["span_text"] == span for x in flags):
            old = next(f for f in prev if f["kind"] == "internal_goal" and f["span_text"] == span)
            flags.append({**old, "span": [i, i + len(span)], "note": f"'{span}'{_eun(span)} 삼성 영업목표예요"})
    # 2) 검증 안 된 주장
    for c in guards.find_claims(text):
        a, b = guards.claim_phrase(text, c)
        span_text = text[a:b]
        same = next((f for f in prev if f["kind"] == "unverified_claim" and f["state"] != "applied"
                     and f["span_text"] in text and c.word in f["span_text"]), None)
        if same:
            flags.append({**same, "state": "open"})
            continue
        if any(c.word in f["span_text"] for f in flags if f["kind"] == "unverified_claim"):
            continue
        if use_llm:
            span_text, sug, note = await _claim_fix(text, c.word, span_text)
        else:
            sug, note = guards.strip_claims(span_text), f"'{c.word}'{_eun(c.word)} 아직 검증 전이에요"
        flags.append({"id": new_id("flg"), "kind": "unverified_claim", "span": [], "span_text": span_text, "note": note,
                      "suggestion": sug, "auto_applied": False, "state": "open", "original_text": None})
    # 이미 바꾼 주장(되돌리기용)
    for f in prev:
        if f["kind"] == "unverified_claim" and f["state"] == "applied" and f.get("suggestion") and f["suggestion"] in text:
            flags.append(dict(f))
    # 3) 사람이 쓴 문장의 출처 없는 수치
    if from_user and allowed_numbers is not None:
        for a, b, raw in guards.unsourced_numbers(text, allowed_numbers):
            if any(raw in f["span_text"] for f in flags):
                continue
            unit = raw.lstrip("0123456789.,").strip()
            flags.append({"id": new_id("flg"), "kind": "unverified_claim", "span": [a, b], "span_text": raw,
                          "note": f"'{raw}'{_eun(raw)} 출처가 없는 수치예요", "suggestion": f"[00]{unit}",
                          "auto_applied": False, "state": "open", "original_text": None})
    _place_spans(text, flags)
    return text, flags, memos


def apply_flag(msg: dict[str, Any], flag_id: str, direction: dict[str, Any]) -> None:
    """`바꾸기`(주장 → 대체안) · `빼기`(되돌렸던 내부 목표를 다시 뺀다)."""
    f = next((x for x in msg.get("flags") or [] if x["id"] == flag_id), None)
    if f is None:
        raise ApiError(404, "NOT_FOUND", f"표시를 찾을 수 없어요: {flag_id}")
    text = msg["text"]
    if f["state"] == "applied":
        return
    i = text.find(f["span_text"])
    if i < 0:
        raise ApiError(409, "CONFLICT", "문장이 바뀌어 이 표시를 적용할 수 없어요")
    f["original_text"] = text
    if f["kind"] == "unverified_claim":
        msg["text"] = text[:i] + (f.get("suggestion") or "") + text[i + len(f["span_text"]):]
    else:
        msg["text"] = guards.remove_span(text, i, i + len(f["span_text"]))
        direction.setdefault("internal_memos", []).append({"text": f["span_text"], "from": "flag", "flag_id": f["id"]})
        f["note"] = f"'{f['span_text']}'{_eun(f['span_text'])} 삼성 영업목표라 고객 메시지에서 빼고 내부 메모로 옮겼어요"
    f["state"] = "applied"
    _place_spans(msg["text"], msg["flags"])


def revert_flag(msg: dict[str, Any], flag_id: str, direction: dict[str, Any]) -> None:
    """`되돌리기` — 바꾸기 · 자동 빼기 전 문장으로."""
    f = next((x for x in msg.get("flags") or [] if x["id"] == flag_id), None)
    if f is None:
        raise ApiError(404, "NOT_FOUND", f"표시를 찾을 수 없어요: {flag_id}")
    if f["state"] != "applied":
        return
    text = msg["text"]
    if f["kind"] == "unverified_claim":
        sug = f.get("suggestion") or ""
        i = text.find(sug) if sug else -1
        msg["text"] = text[:i] + f["span_text"] + text[i + len(sug):] if i >= 0 else (f.get("original_text") or text)
    else:
        orig = f.get("original_text") or ""
        i = orig.find(f["span_text"])
        if orig and i >= 0 and guards.remove_span(orig, i, i + len(f["span_text"])) == text:
            msg["text"] = orig
        else:  # 그 뒤 문장이 바뀌었으면 끝에 붙여 되살린다
            msg["text"] = f"{text.rstrip('.')} — {f['span_text']}."
        direction["internal_memos"] = [m for m in direction.get("internal_memos") or [] if m.get("flag_id") != f["id"]]
        f["note"] = f"'{f['span_text']}'{_eun(f['span_text'])} 삼성 영업목표예요"
    f["state"] = "reverted"
    _place_spans(msg["text"], msg["flags"])
