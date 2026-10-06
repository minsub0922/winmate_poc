"""변경 기록(ChangeEntry) · 되돌리기 · 버전 비교(02-storyboard.md §4.18 · §5.7).

변경마다 대상(섹션 · 공간 · 핵심 메시지 · 추적 항목)의 전 · 후 상태를 `inverse_ops` 로 남긴다(API 에는 내지 않음).
되돌리기는 대상의 지금 상태가 그 변경 직후 상태와 같을 때만 된다(그 뒤 또 바뀌었으면 409 NOT_REVERTIBLE).
"""
from __future__ import annotations

import copy
import json
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso

from .rules import SLOT_KEYS, SLOT_SHORT, space_filled

TARGET_PATHS = {"section": ("outline", "sections"), "space": ("outline", "spaces"),
                "key_message": ("direction", "key_messages"), "trace_item": ("trace", "items")}
_ID_KEY = {"trace_item": "rq_item_id"}


def _list(doc: dict[str, Any], kind: str) -> list[dict[str, Any]] | None:
    a, b = TARGET_PATHS[kind]
    parent = doc.get(a)
    if not isinstance(parent, dict):
        return None
    return parent.setdefault(b, [])


def find_target(doc: dict[str, Any], kind: str, ident: str) -> tuple[dict[str, Any] | None, int]:
    lst = _list(doc, kind) or []
    key = _ID_KEY.get(kind, "id")
    for i, obj in enumerate(lst):
        if obj.get(key) == ident:
            return obj, i
    return None, -1


def _comparable(kind: str, obj: dict[str, Any] | None) -> str:
    if obj is None:
        return "null"
    if kind == "section":
        view = {"lines": [ln.get("text") for ln in obj.get("lines") or []], "direction": obj.get("direction"),
                "products": [p.get("name") for p in obj.get("products") or []], "tbd": obj.get("tbd_reason")}
    elif kind == "space":
        view = {"slots": {k: [s.get("text") for s in ((obj.get("slots") or {}).get(k) or {}).get("segments") or []]
                          for k in SLOT_KEYS}, "name": obj.get("name"), "products": [p.get("name") for p in obj.get("products") or []]}
    elif kind == "key_message":
        view = {"text": obj.get("text")}
    else:
        view = {"places": obj.get("places"), "resolution": obj.get("resolution"), "state": obj.get("state")}
    return json.dumps(view, ensure_ascii=False, sort_keys=True)


def record(doc: dict[str, Any], *, place_label: str, kind: str, cause: dict[str, Any], before_summary: str = "",
           after_summary: str = "", aspect: str | None = None, tags: list[str] | None = None,
           target: tuple[str, str] | None = None, before: dict[str, Any] | None = None, after: dict[str, Any] | None = None,
           index: int | None = None, revertible: bool | None = None) -> dict[str, Any]:
    """작업본에 변경 하나를 남긴다(최신 저장 버전 이후 목록)."""
    entry = {
        "id": new_id("chg"), "place_label": place_label, "aspect": aspect, "kind": kind, "tags": list(tags or []),
        "before_summary": before_summary, "after_summary": after_summary, "cause": cause,
        "revertible": bool(revertible if revertible is not None else (kind != "kept" and target is not None)),
        "at": now_iso(),
    }
    if target is not None:
        entry["inverse_ops"] = [{"kind": target[0], "id": target[1], "before": copy.deepcopy(before),
                                 "after": copy.deepcopy(after), "index": index}]
    doc.setdefault("changes", []).append(entry)
    return entry


def revert(doc: dict[str, Any], chg_id: str) -> dict[str, Any]:
    changes = doc.get("changes") or []
    entry = next((c for c in changes if c["id"] == chg_id), None)
    if entry is None:
        raise ApiError(404, "NOT_FOUND", f"변경 기록을 찾을 수 없어요: {chg_id}")
    if not entry.get("revertible") or not entry.get("inverse_ops"):
        raise ApiError(409, "NOT_REVERTIBLE", "이 변경은 되돌릴 수 없어요")
    for op in entry["inverse_ops"]:
        kind, ident = op["kind"], op["id"]
        lst = _list(doc, kind)
        if lst is None:
            raise ApiError(409, "NOT_REVERTIBLE", "되돌릴 자리가 없어요")
        cur, idx = find_target(doc, kind, ident)
        if _comparable(kind, cur) != _comparable(kind, op.get("after")):
            raise ApiError(409, "NOT_REVERTIBLE", "그 뒤에 다시 바뀌어 이 변경만 되돌릴 수 없어요")
        before = op.get("before")
        if before is None:          # 추가된 것 → 뺀다
            if idx >= 0:
                lst.pop(idx)
        elif cur is None:           # 지워진 것 → 원래 자리에 넣는다
            at = op.get("index")
            lst.insert(at if isinstance(at, int) and 0 <= at <= len(lst) else len(lst), copy.deepcopy(before))
        else:
            lst[idx] = copy.deepcopy(before)
    doc["changes"] = [c for c in changes if c["id"] != chg_id]
    return entry


# ── 요약 문구 ──────────────────────────────────────────────

def summarize_section(sec: dict[str, Any] | None) -> str:
    if not sec:
        return "없음"
    lines = [ln.get("text", "") for ln in sec.get("lines") or [] if ln.get("text")]
    return lines[0] if lines else (sec.get("direction") or sec.get("name") or "")


def summarize_space(sp: dict[str, Any] | None, *, count: int | None = None) -> str:
    if not sp:
        return "없음" if count is None else f"없음 · 공간 {count}개"
    k = space_filled(sp)
    if k == 0:
        return "배경 + 기술 후보"
    if k == 5:
        return "시나리오 5칸 — 행위 → 트리거 → 반응 → 예외 → 지표"
    names = [SLOT_SHORT[s] for s in SLOT_KEYS if ((sp.get("slots") or {}).get(s) or {}).get("state") in ("filled", "unknown")]
    return f"시나리오 {k}칸 — {' → '.join(names)}"


# ── 비교 원인 문구(§4.18) ──────────────────────────────────

def cause_labels(rows: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    counts: dict[str, int] = {}
    for r in rows:
        c = r.get("cause") or {}
        k = c.get("kind")
        if k in ("rq_sync", "restore"):
            if c.get("label") and c["label"] not in out:
                out.append(c["label"])
        else:
            counts[k] = counts.get(k, 0) + 1
    names = {"revision": "수정 요청 {k}건", "space_questions": "섹션 질의 {k}건", "trace": "요구 정리 {k}건",
             "vp": "VP 문장 반영", "user": "직접 수정 {k}건"}
    for k in ("space_questions", "revision", "trace", "vp", "user"):
        if counts.get(k):
            out.append(names[k].format(k=counts[k]))
    return out


def changed_count(rows: list[dict[str, Any]]) -> int:
    return sum(1 for r in rows if r.get("kind") != "kept")
