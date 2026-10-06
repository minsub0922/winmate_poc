"""넘김 묶음(Package · 05-vp.md §4.14 · §5.3) — 제안서 유형별 시트 맞춤(결정적).

- 표준: 시트 그대로. 섹션 기본 시트(고객 과제 · 가치 제안)에 없는 시트는 `섹션에 없는 시트 · 추가해요`.
- 퀵윈: VP-G 변형 1장(없으면 넘길 때 만든다). 고객 과제는 뺌, 기대 효과는 VP-G 근거 칸 한 줄.
- Solution형: 고객 과제 뺌. 기대 효과는 견적이 있으면 `견적이 있으면 EF-B 추천`(이미 EF-B 면 `그대로 들어가요`).
- 고정 시트(pinned)는 코드 그대로 보낸다.
"""
from __future__ import annotations

import copy
from typing import Any

from . import catalog, numbers

TYPE_LABEL = {"standard": "표준 제안서", "quickwin": "퀵윈 제안서", "solution": "Solution형"}
TYPE_SHORT = {"standard": "표준", "quickwin": "퀵윈", "solution": "Solution형"}
PATH_LABEL = {"standard": "PRS2 · Value Props", "quickwin": "PRQ1 · Value Props", "solution": "PRX2 · Value Props (선택)"}
SECTION_DEFAULT = {"standard": {"CH", "VP"}, "quickwin": {"VP"}, "solution": {"VP", "EF"}}


def main_sheets(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted([s for s in doc.get("sheets") or [] if s.get("kind", "main") == "main"], key=lambda s: s.get("order", 0))


def one_liner(doc: dict[str, Any]) -> dict[str, Any] | None:
    vp = next((s for s in main_sheets(doc) if s["role"] == "VP" and s["layout"]["code"] in ("VP-G", "VP-C")), None)
    if vp:
        return vp
    return next((v for v in doc.get("variants") or [] if v.get("kind") == "one_liner"), None)


def has_quote(doc: dict[str, Any]) -> bool:
    return bool(((doc.get("facts") or {}).get("quote") or {}).get("total")) or any(a.get("kind") == "quote" for a in doc.get("attachments") or [])


def interview_numbers(sheets: list[dict[str, Any]]) -> list[str]:
    out = []
    for s in sheets:
        c = s.get("content") or {}
        for m in c.get("metrics") or []:
            for side in ("before", "after"):
                if ((m.get(side) or {}).get("source") or {}).get("kind") == "interview" and m.get(side, {}).get("status") in numbers.USABLE:
                    out.append(f"{m['label']} {m[side]['display']}")
        for ch in c.get("challenges") or []:
            if ((ch.get("impact") or {}).get("source") or {}).get("kind") == "interview":
                out.append(f"{ch['title']} {ch['impact']['display']}")
    return out


def estimate_notes(sheet: dict[str, Any]) -> list[str]:
    out = []
    for m in (sheet.get("content") or {}).get("metrics") or []:
        if numbers.metric_status(m) != "estimated":
            continue
        basis = None
        for side in ("after", "before"):
            v = m.get(side) or {}
            if v.get("status") == "estimated":
                basis = v.get("estimate_basis") or ((v.get("source") or {}).get("label"))
                break
        out.append(f"'{m['label']}' — {basis or '유관 사례 범위'}로 넣고 [추정] 표시했어요")
    return out


def sources_footer(doc: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for s in doc.get("sources") or []:
        if s.get("connected"):
            out.append(f"{s.get('kind_label') or s['kind']} · {s.get('title') or s['ref_id']}")
    for a in doc.get("attachments") or []:
        if a.get("kind") in ("rfp", "quote", "meeting_notes"):
            out.append(f"{ {'rfp': 'RFP', 'quote': '견적', 'meeting_notes': '회의록'}[a['kind']] } · {a.get('filename')}")
    return out


def _pkg_sheet(doc: dict[str, Any], s: dict[str, Any], *, notes_estimates: bool) -> dict[str, Any]:
    slots = [x for x in doc.get("image_slots") or [] if x.get("sheet_id") == s["id"] and not x.get("extra")]
    notes = [s.get("speaker_notes") or ""] + (estimate_notes(s) if notes_estimates else [])
    return {"role": s["role"], "layout": s["layout"], "title": s.get("title") or "", "points": s.get("points") or "",
            "content": copy.deepcopy(s.get("content") or {}), "image_slots": copy.deepcopy(slots),
            "speaker_notes": "\n".join(n for n in notes if n).strip(), "pinned": bool(s.get("pinned")), "sheet_id": s["id"]}


def build(doc: dict[str, Any], proposal_type: str, *, estimates_as_notes: bool = True) -> dict[str, Any]:
    sheets = main_sheets(doc)
    by_role = {s["role"]: s for s in sheets}
    rows: list[dict[str, Any]] = []
    send: list[dict[str, Any]] = []
    added = 0
    needs_variant = False
    n_all = len(sheets)
    if proposal_type == "quickwin":
        ol = one_liner(doc)
        if ol is None:
            needs_variant = True
            rows.append({"code": "VP-G", "sheet_label": "가치 제안 1장", "treatment": f"{n_all}장 → 한 문장 + 제품 사진 + 근거 3"})
        else:
            rows.append({"code": catalog.display(ol["layout"]["code"]), "sheet_label": "가치 제안 1장",
                         "treatment": f"{n_all}장 → 한 문장 + 제품 사진 + 근거 3" if ol.get("kind") == "one_liner" else "그대로 들어가요"})
            send.append(_pkg_sheet(doc, ol, notes_estimates=estimates_as_notes))
        rows.append({"code": "—", "sheet_label": "고객 과제", "treatment": "퀵윈엔 빼요"})
        rows.append({"code": "—", "sheet_label": "기대 효과", "treatment": "VP-G 근거 칸에 한 줄로"})
    else:
        for role, label in (("CH", "고객 과제"), ("VP", "가치 제안"), ("EF", "기대 효과")):
            s = by_role.get(role)
            if proposal_type == "solution" and role == "CH":
                rows.append({"code": "—", "sheet_label": label, "treatment": "대규모 MI가 이미 말해 빼요"})
                continue
            if s is None:
                why = "재료에 과제가 없어 빼요" if role == "CH" else "이번엔 만들지 않았어요"
                rows.append({"code": "—", "sheet_label": label, "treatment": why})
                continue
            code = catalog.display(s["layout"]["code"])
            if s.get("pinned"):
                treat = "고정 · 그대로 들어가요"
            elif proposal_type == "solution" and role == "EF" and s["layout"]["code"] != "EF-B":
                treat = "견적이 있으면 EF-B 추천"
            elif role not in SECTION_DEFAULT.get(proposal_type, set()):
                treat = "섹션에 없는 시트 · 추가해요"
                added += 1
            else:
                treat = "그대로 들어가요"
            rows.append({"code": code, "sheet_label": label, "treatment": treat})
            send.append(_pkg_sheet(doc, s, notes_estimates=estimates_as_notes))
    est = sum(len(estimate_notes(s)) for s in [x for x in sheets if any(p["sheet_id"] == x["id"] for p in send)])
    return {
        "proposal_type": proposal_type, "type_label": TYPE_LABEL[proposal_type], "path_label": PATH_LABEL[proposal_type],
        "rows": rows, "sheets": send,
        "counts": {"send": len(send) if not needs_variant else 1, "added_not_in_section": added, "estimates_as_notes": est},
        "sources_footer": sources_footer(doc), "needs_variant": needs_variant,
        "interview_numbers": interview_numbers([x for x in sheets if any(p["sheet_id"] == x["id"] for p in send)]),
    }


def dock_text(pkg: dict[str, Any]) -> str:
    c = pkg["counts"]
    s = f"{TYPE_SHORT[pkg['proposal_type']]} · 보낼 시트 {c['send']}"
    if c["added_not_in_section"]:
        s += f" · 섹션에 없는 시트 {c['added_not_in_section']} 추가"
    return s


def mask_interview(pkg: dict[str, Any]) -> dict[str, Any]:
    """§3.4-4 답 없이 진행 — 고객 인터뷰 수치는 `[00]` + 노트 `[확인 필요]`."""
    for s in pkg["sheets"]:
        notes = []
        for m in (s.get("content") or {}).get("metrics") or []:
            for side in ("before", "after"):
                v = m.get(side) or {}
                if ((v.get("source") or {}).get("kind")) == "interview":
                    notes.append(f"'{m['label']}' {v.get('display')} — 고객 인터뷰 수치 [확인 필요]")
                    m[side] = numbers.missing(v.get("unit"))
        if notes:
            s["speaker_notes"] = "\n".join([s.get("speaker_notes") or ""] + notes).strip()
    pkg["interview_numbers"] = []
    return pkg
