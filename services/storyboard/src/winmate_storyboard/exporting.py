"""내보내기 문서 만들기(SB4E) — export 서비스 `POST /v1/exports` 의 `document`.

- PPTX: 공통 템플릿(C03 표지 · CP-A 표)로 `섹션 표 그대로 · 편집할 수 있어요`. PDF: 보고서형(reportlab, LibreOffice 불필요).
- `[00]` · `[확인 필요]` · `TBD` 표시는 항상 남긴다(keep_markers 고정).
- 내부 메모(제작자 의견 · 옮겨진 영업목표 · 섹션 내부 메모)는 `internal_memo` 옵션이 켜졌을 때만 — 내부 검토용 파일(`_내부검토`).
"""
from __future__ import annotations

from typing import Any

from .rules import LANG_LABEL, SLOT_FULL, SLOT_KEYS, section_label, slot_text, two_digit

STATUS_TEXT = {"confirmed": "확정", "reviewing": "검토 중", "needs_confirmation": "확인 필요", "writing": "작성 중", "tbd": "TBD"}
LINK_TEXT = {"direct": "직접", "interpreted": "해석", "extension": "확장", "reviewing": "검토", "unconfirmed": "미확인",
             "deferred": "보류", "excluded": "제외"}


def file_name(doc: dict[str, Any], version: int, internal: bool) -> str:
    base = f"{doc.get('title') or '스토리보드'}_스토리보드_v{version}"
    return base + ("_내부검토" if internal else "")


def _products(sec: dict[str, Any]) -> str:
    names = [p["name"] for p in sec.get("products") or []]
    if not names:
        return "—"
    return " · ".join(names[:2]) + (" 외" if len(names) > 2 else "")


def _rows(doc: dict[str, Any]) -> list[list[str]]:
    outline = doc.get("outline") or {}
    rows = []
    for i, s in enumerate(outline.get("sections") or [], 1):
        g = s["group_key"]
        if g == "part1":
            comp = f"{s.get('code')} {s['name']}"
        elif g == "part2":
            comp = f"Part 2 {s['name']}"
        elif g == "part3":
            comp = f"Part 3 {s['name']}" if not (s.get("code") or "").startswith("Part") else f"{s['code']} {s['name']}"
        else:
            comp = s["name"]
        status = STATUS_TEXT.get(s.get("status", ""), "")
        direction = s.get("direction") or ""
        if s.get("tbd_reason"):
            direction = f"{direction} · {s['tbd_reason']}" if direction else s["tbd_reason"]
        rows.append([two_digit(i), comp, direction, _products(s), status])
    return rows


def _space_rows(doc: dict[str, Any]) -> list[list[str]]:
    out = []
    for sp in (doc.get("outline") or {}).get("spaces") or []:
        name = sp["name"] + (" (확장)" if sp.get("is_extension") else "")
        out.append([name] + [slot_text((sp.get("slots") or {}).get(k)) or "—" for k in SLOT_KEYS])
    return out


def _trace_rows(doc: dict[str, Any]) -> list[list[str]]:
    out = []
    for it in sorted((doc.get("trace") or {}).get("items") or [], key=lambda x: x["code"]):
        links = " · ".join(LINK_TEXT.get(lt, lt) for lt in it.get("link_types") or [])
        out.append([it["code"], it.get("short") or it.get("text", ""), it.get("places_label") or "—", links])
    return out


def _discussion_rows(doc: dict[str, Any]) -> list[list[str]]:
    outline = doc.get("outline") or {}
    secs = {s["id"]: s for s in outline.get("sections") or []}
    out = []
    for d in outline.get("discussions") or []:
        rel = " · ".join(section_label(secs[s]) for s in d.get("section_ids") or [] if s in secs)
        out.append([str(d["n"]), d["label"], rel or "—"])
    return out


def _messages_rows(doc: dict[str, Any]) -> list[list[str]]:
    return [[m["place_label"], m.get("audience") or "—", m["text"]] for m in (doc.get("direction") or {}).get("key_messages") or []]


def internal_memo_lines(doc: dict[str, Any], author_note: str | None) -> list[str]:
    lines = []
    if author_note:
        lines.append(f"제작자 의견: {author_note}")
    for m in (doc.get("direction") or {}).get("internal_memos") or []:
        if m.get("from") == "flag":
            lines.append(f"고객 메시지에서 뺀 내부 목표: {m['text']}")
    for s in (doc.get("outline") or {}).get("sections") or []:
        if s.get("internal_memo"):
            lines.append(f"{section_label(s)}: {s['internal_memo']}")
    return lines


def build(doc: dict[str, Any], *, fmt: str, options: dict[str, Any], version: int, author_note: str | None) -> dict[str, Any]:
    title = doc.get("title") or "스토리보드"
    dr = doc.get("direction") or {}
    opt = next((o for o in dr.get("options") or [] if o["id"] == dr.get("selected_option_id")), None) or {}
    subtitle = f"전략 수립 Storyboard · v{version}" + (f" · {opt['title']}" if opt.get("title") else "")
    internal = bool(options.get("internal_memo"))
    groups = (doc.get("outline") or {}).get("groups") or []
    tables: list[tuple[str, str, list[str], list[list[str]]]] = [
        ("핵심 메시지", " · ".join(m.get("axis_label") or "" for m in dr.get("key_messages") or []), ["자리", "청중", "메시지"],
         _messages_rows(doc)),
        ("목차 · 서사", " · ".join(f"{g['name']}" for g in groups), ["번호", "구성", "작성 방향", "제품 · 솔루션 후보", "상태"], _rows(doc)),
    ]
    secs = (doc.get("outline") or {}).get("sections") or []
    for g in groups:
        if g["key"] == "part2":
            tables.append(("Part 2 공간 시나리오", "행위 → 트리거 → 반응 → 예외 → 지표", ["공간"] + [SLOT_FULL[k] for k in SLOT_KEYS],
                           _space_rows(doc)))
            continue
        rows = [[section_label(s), " / ".join(ln["text"] for ln in s.get("lines") or []) or "—",
                 STATUS_TEXT.get(s.get("status", ""), "")] for s in secs if s["group_key"] == g["key"]]
        tables.append((f"{g['name']} · 본문", g.get("summary") or "", ["구성", "본문", "상태"], rows))
    if options.get("trace_appendix", True) and (doc.get("trace") or {}).get("items"):
        tables.append(("부록 · 요구 → 스토리보드 추적표", "직접 주제가 보임 · 해석 새 콘셉트로 · 확장 요구에 없던 해결안 · 검토 논의 중 · 미확인 담당 항목이 안 보임",
                       ["코드", "고객 요구", "스토리보드에 들어간 곳", "연결"], _trace_rows(doc)))
    if options.get("discussions", True) and (doc.get("outline") or {}).get("discussions"):
        tables.append(("추가 논의", "회의에서 정할 것", ["번호", "추가 논의", "관련 섹션"], _discussion_rows(doc)))
    memo = internal_memo_lines(doc, author_note) if internal else []
    if memo:
        tables.append(("내부 목표 메모 (내부 검토용)", "고객에게 보내지 않는 내용", ["내부 메모"], [[m] for m in memo]))
    if fmt == "pdf":
        sections = [{"heading": t, "paragraphs": [sub] if sub else [], "table": {"columns": cols, "rows": rows}}
                    for t, sub, cols, rows in tables if rows]
        return {"title": title, "subtitle": subtitle, "meta": {"언어": LANG_LABEL.get(((doc.get("settings") or {}).get("language")
                                                                                     or {}).get("value", "ko"), "한국어")},
                "sections": sections, "page_size": "A4", "orientation": "landscape"}
    slides: list[dict[str, Any]] = [{"template_code": "C03", "slots": {
        "title": title, "subtitle": subtitle, "customer": doc.get("customer_name") or "", "date": "",
        "presenter": (doc.get("owner") or {}).get("name") or ""}}]
    for t, sub, cols, rows in tables:
        if not rows:
            continue
        for k in range(0, len(rows), 12):     # 한 장에 12행까지
            part = rows[k:k + 12]
            slides.append({"template_code": "CP-A", "slots": {
                "title": t if k == 0 else f"{t} (이어서)", "subtitle": sub, "table": {"columns": cols, "rows": part}, "message": ""}})
    return {"title": title, "lang": "ko", "slides": slides, "tbd_label": "[확인 필요]"}
