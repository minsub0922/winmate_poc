"""넘김 묶음(06-spec §5.3 · §4.13.5 · §4.20) · 내보내기 렌더 모델(§4.19).

둘 다 '보이는 행(편집 순서) · 시트 언어 · 단위 · 숫자 형식'으로 그린 같은 표에서 만든다.
숨긴 행 · 내부 메모는 언제나 빠진다(drop_hidden=False 면 숨긴 행만 남김).
"""
from __future__ import annotations

import math
from typing import Any

from .. import sheet as S
from . import items as itemcat
from . import text as T
from .fmt import PENDING_EN, PENDING_KO
from .values import Fmt, render_lines

TAB = {"ko": ("비교표", "메모 · 출처", "요구사항 대응표"), "en": ("Comparison", "Notes & Sources", "Compliance Matrix"),
       "ko_en": ("비교표", "메모 · 출처", "요구사항 대응표")}
HEAD_ITEM = {"ko": "항목", "en": "Item", "ko_en": "항목 / Item"}
VERDICT_KO = {"pass": "충족", "fail": "미충족", "unknown": "확인 필요"}
VERDICT_EN = {"pass": "Compliant", "fail": "Not compliant", "unknown": "To be confirmed"}


def _opts(options: dict[str, Any] | None) -> dict[str, bool]:
    o = {"drop_hidden": True, "memo_footnotes": True, "keep_pending_marks": True}
    o.update({k: bool(v) for k, v in (options or {}).items() if v is not None})
    return o


def display_table(sheet: dict[str, Any], f: Fmt, options: dict[str, Any] | None = None,
                  products: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """언어 · 단위대로 펼친 표: columns · lines(행 줄) · footnotes · counts."""
    o = _opts(options)
    ps = products if products is not None else S.products_ordered(sheet)
    rows = S.rows_ordered(sheet)
    vis_rows = [r for r in rows if not (o["drop_hidden"] and r.get("hidden"))]
    notes, marks = S.footnotes(sheet, rows=vis_rows)
    if not o["memo_footnotes"]:
        notes = [n for n in notes if not any(r["id"] == n.get("row_id") and r.get("memo") for r in vis_rows)]
        marks = {k: v for k, v in marks.items() if not any(r["id"] == k and r.get("memo") for r in vis_rows)}
    cells = sheet.get("cells") or {}
    lang = f.language
    pend = PENDING_KO if lang == "ko" else (PENDING_EN if lang == "en" else f"{PENDING_KO} / {PENDING_EN}")
    lines: list[dict[str, Any]] = []
    win_cells = pending_cells = converted = 0
    pending_list: list[dict[str, str]] = []
    originals: list[dict[str, str]] = []
    for r in vis_rows:
        wins = S.row_wins(sheet, r)
        per_p = []
        for p in ps:
            c = cells.get(S.ck(r["id"], p["id"])) or {}
            v = c.get("value") if c.get("state") != "flag" else None
            per_p.append((p, c, render_lines(r["row_key"], v, f, r["label_ko"], r.get("en_lines") or [r["label_ko"]])))
        n_lines = max((len(x[2]) for x in per_p), default=1)
        for li in range(n_lines):
            label = per_p[0][2][li].label if per_p and li < len(per_p[0][2]) else r["label_ko"]
            mark = marks.get(r["id"]) if li == 0 else None
            row_cells = []
            for p, c, lns in per_p:
                ln = lns[li] if li < len(lns) else lns[-1]
                text = ln.text
                is_pend = (c.get("state") in ("pending", "flag", None) and not c.get("value")) or text == pend or pend in text
                if is_pend:
                    pending_cells += 1 if li == 0 else 0
                    pending_list.append({"row": r["label_ko"], "product": p["display_name"], "text": text})
                    if not o["keep_pending_marks"]:
                        text = text.replace(pend, "").strip(" ·/") or ""
                win = bool(wins.get(p["id"])) and not is_pend
                if win and li == 0:
                    win_cells += 1
                if ln.converted:
                    converted += 1
                    if ln.original_text:
                        originals.append({"row": label, "product": p["display_name"], "original": ln.original_text})
                row_cells.append({"text": text, "win": win, "pending": is_pend, "converted": ln.converted, "original": ln.original_text,
                                  "product_id": p["id"]})
            lines.append({"row_id": r["id"], "label": label + (f" {mark}" if mark else ""), "base_label": label,
                          "highlighted": bool(r.get("highlighted")), "footnote_mark": mark, "cells": row_cells})
    columns = [{"product_id": p["id"], "model_ref": p.get("ref"), "label": p.get("column_label") or p["display_name"], "role": p.get("role") or "proposed"}
               for p in ps]
    memo_n = len([n for n in notes if any(r["id"] == n.get("row_id") and r.get("memo") for r in vis_rows)])
    return {"columns": columns, "lines": lines, "footnotes": [{"mark": n["mark"], "text": n["text"]} for n in notes],
            "visible_rows": len(vis_rows), "hidden_rows": len(rows) - len([r for r in rows if not r.get("hidden")]),
            "win_cells": win_cells, "pending_cells": pending_cells, "footnote_memos": memo_n, "converted": converted,
            "pending_list": pending_list, "originals": originals}


def split_columns(n: int, per: int = 5) -> list[tuple[int, int]]:
    """6 → 3 + 3, 7 → 4 + 3(고르게)."""
    if n <= per:
        return [(0, n)]
    k = math.ceil(n / per)
    base, extra = divmod(n, k)
    out, start = [], 0
    for i in range(k):
        size = base + (1 if i < extra else 0)
        out.append((start, start + size))
        start += size
    return out


def sca_sheets(sheet: dict[str, Any], f: Fmt, options: dict[str, Any] | None) -> list[dict[str, Any]]:
    ps = [p for p in S.products_ordered(sheet)]
    chunks = split_columns(len(ps))
    out = []
    for i, (a, b) in enumerate(chunks):
        sub = ps[a:b]
        dt = display_table(sheet, f, options, products=sub)
        title = f"{' vs '.join(p['display_name'] for p in sub)} 사양 비교" if f.language != "en" else f"{' vs '.join(p['display_name'] for p in sub)} Specifications"
        if len(chunks) > 1:
            title += f" ({i + 1}/{len(chunks)})"
        out.append({"template": "SC-A", "data": {
            "title": title, "columns": dt["columns"],
            "rows": [{"row_id": ln["row_id"], "label": ln["label"], "highlighted": ln["highlighted"], "footnote_mark": ln["footnote_mark"],
                      "cells": [{"text": c["text"], "win": c["win"], "pending": c["pending"]} for c in ln["cells"]]} for ln in dt["lines"]],
            "footnotes": dt["footnotes"], "source_line": T.source_line(sheet, sheet.get("cells") or {})}, "_dt": dt})
    return out


def sda_sheets(sheet: dict[str, Any], f: Fmt, options: dict[str, Any] | None) -> list[dict[str, Any]]:
    out = []
    for p in S.products_ordered(sheet):
        dt = display_table(sheet, f, options, products=[p])
        groups: dict[str, list[dict[str, Any]]] = {}
        order = itemcat.groups()
        rows_by_id = {r["id"]: r for r in sheet.get("rows") or []}
        for ln in dt["lines"]:
            r = rows_by_id.get(ln["row_id"]) or {}
            g = itemcat.group_of(r.get("item_key")) if r.get("item_key") else "기타"
            groups.setdefault(g, []).append({"label": ln["label"], "value": ln["cells"][0]["text"], "pending": ln["cells"][0]["pending"]})
        gl = [{"name": g, "rows": groups[g]} for g in order if g in groups] + [{"name": g, "rows": v} for g, v in groups.items() if g not in order]
        out.append({"template": "SD-A", "data": {
            "title": f"{p['display_name']} 상세 사양" if f.language != "en" else f"{p['display_name']} Specifications",
            "model_ref": p.get("ref"), "label": p.get("bubble_label") or p["display_name"], "groups": gl, "footnotes": dt["footnotes"],
            "source_line": T.source_line(sheet, sheet.get("cells") or {})}, "_dt": dt})
    return out


def scb_sheet(sheet: dict[str, Any], options: dict[str, Any] | None, lang: str = "ko") -> dict[str, Any] | None:
    comp = sheet.get("compliance") or {}
    rows = comp.get("rows") or []
    if not rows:
        return None
    tp = next((p for p in sheet.get("products") or [] if p["id"] == comp.get("target_product_id")), None)
    label = tp["display_name"] if tp else (comp.get("target_label") or "모델")
    inc = comp.get("include") or {}
    page_refs = inc.get("page_refs", True)
    cols = ["요구 항목", "고객 요구", label, "판정"] + (["원문"] if page_refs else [])
    c = {"pass": 0, "fail": 0, "unknown": 0}
    out_rows = []
    for r in rows:
        c[r.get("verdict", "unknown")] = c.get(r.get("verdict", "unknown"), 0) + 1
        row = {"item": r["item"], "requirement": r["requirement"], "value": r.get("value_text") or "—", "verdict": r.get("verdict", "unknown"),
               "note": r.get("note")}
        if page_refs and r.get("page"):
            row["page"] = r["page"]
        out_rows.append(row)
    return {"template": "SC-B", "data": {"title": "요구사항 대응표" if lang != "en" else "Compliance Matrix", "model_label": label,
                                         "columns": cols, "rows": out_rows, "counts": c}}


def build_package(sheet: dict[str, Any], *, templates: list[str], mode: str, options: dict[str, Any] | None,
                  overrides: dict[str, Any] | None = None, replace_ids: list[str] | None = None) -> dict[str, Any]:
    f = S.fmt_of(sheet, overrides)
    sheets: list[dict[str, Any]] = []
    for t in templates:
        if t == "SC-A":
            sheets += sca_sheets(sheet, f, options)
        elif t == "SD-A":
            sheets += sda_sheets(sheet, f, options)
        elif t == "SC-B":
            s = scb_sheet(sheet, options, f.language)
            if s:
                sheets.append(s)
        elif t == "SD-B":
            sheets += sdb_sheets(sheet)
    main_dt = next((s["_dt"] for s in sheets if s.get("_dt")), None) or display_table(sheet, f, options)
    fact = []
    for i, s in enumerate(sheets):
        dt = s.get("_dt")
        if not dt:
            continue
        for pl in dt["pending_list"]:
            fact.append({"sheet_index": i, "text": f"{pl['product']} {pl['row']} [확정 필요]", "placeholder": "[확정 필요]",
                         "reason": "사내 카탈로그 · 출처에 값이 없거나 확인 중인 값"})
    seen = set()
    fact_u = []
    for x in fact:
        k = (x["text"])
        if k not in seen:
            seen.add(k)
            fact_u.append(x)
    for s in sheets:
        s.pop("_dt", None)
    carry = {"visible_rows": main_dt["visible_rows"], "hidden_rows_dropped": main_dt["hidden_rows"] if _opts(options)["drop_hidden"] else 0,
             "win_cells": main_dt["win_cells"], "footnote_memos": main_dt["footnote_memos"], "pending_cells": main_dt["pending_cells"]}
    return {
        "sheet_id": sheet["id"], "sheet_version": sheet.get("doc_version", 0), "title": T.display_title(sheet), "locale": f.language,
        "customer_name": sheet.get("customer_name"),
        "catalog": {"label": "사내 제품 카탈로그", "version": (sheet.get("catalog") or {}).get("version") or ""},
        "sheets": sheets, "fact_check": fact_u, "carry": carry, "mode": mode, "replace_proposal_sheet_ids": replace_ids,
        "link_back": {"route": f"/spec/{sheet['id']}"}, "lines": carry_lines(carry),
    }


def sdb_sheets(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    """SD-B(제안) — 치수 · 설치: 도면 이미지 원천 없음(값만)."""
    out = []
    cells = sheet.get("cells") or {}
    rows = {r["row_key"]: r for r in sheet.get("rows") or []}
    for p in S.products_ordered(sheet):
        dims = (cells.get(S.ck(rows["dimensions"]["id"], p["id"])) or {}).get("value") if "dimensions" in rows else None
        wt = (cells.get(S.ck(rows["weight"]["id"], p["id"])) or {}).get("value") if "weight" in rows else None
        acc = (cells.get(S.ck(rows["accessories"]["id"], p["id"])) or {}).get("value") if "accessories" in rows else None
        out.append({"template": "SD-B", "data": {"model_ref": p.get("ref"), "dims_mm": dims, "vesa": None, "weight_kg": (wt or {}).get("set"),
                                                 "mounts": [x for x in ((acc or {}).get("mount"), (acc or {}).get("stand")) if x]}})
    return out


def carry_lines(carry: dict[str, int]) -> list[str]:
    out = []
    v, h = carry["visible_rows"], carry["hidden_rows_dropped"]
    out.append(f"보이는 행 {v}개 — 숨긴 {h}행은 빠져요" if h else f"보이는 행 {v}개")
    parts = []
    if carry["win_cells"]:
        parts.append(f"우위 강조 {carry['win_cells']}칸")
    if carry["footnote_memos"]:
        parts.append(f"각주 메모 {carry['footnote_memos']}건")
    if parts:
        out.append(" · ".join(parts) + " 그대로")
    if carry["pending_cells"]:
        out.append(f"[확정 필요] {carry['pending_cells']}칸 → 제안서 '사실 확인 필요'로")
    out.append("시트와 연결 유지 — 값이 바뀌면 제안서에 알림")
    return out


# ── 내보내기 문서(export 계약 document) ──────────────────

WIN_FILL = "#EAEEFB"
WIN_COLOR = "#1428A0"
HL_FILL = "#F5F7FD"


def _pdf_size(paper: str) -> tuple[str, str]:
    return {"a4_landscape": ("A4", "landscape"), "a4_portrait": ("A4", "portrait"), "letter": ("Letter", "landscape")}.get(paper, ("A4", "landscape"))


def export_document(sheet: dict[str, Any], fmt: str, *, overrides: dict[str, Any] | None, options: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """export 서비스로 보낼 document 와 요약(줄 수 · 각주 · [확정 필요] 칸 · 슬라이드 수 · 쪽 크기)."""
    f = S.fmt_of(sheet, overrides)
    fs = dict(sheet.get("format") or {})
    fs.update({k: v for k, v in (overrides or {}).items() if v is not None})
    lang = f.language
    dt = display_table(sheet, f, options)
    title = T.table_title(sheet, "en" if lang == "en" else "ko")
    src = T.source_line(sheet, sheet.get("cells") or {})
    head_item = HEAD_ITEM.get(lang, "항목")
    tabs = TAB.get(lang, TAB["ko"])
    comp = scb_sheet(sheet, options, lang) if sheet.get("kind") == "req" else None
    summary = {"rows": len(dt["lines"]), "visible_rows": dt["visible_rows"], "footnotes": dt["footnotes"], "pending_cells": dt["pending_cells"],
               "row_labels": [ln["label"] for ln in dt["lines"]], "language": lang}
    if fmt == "xlsx":
        cols = [{"key": "item", "label": head_item, "width": 28}] + [{"key": c["product_id"], "label": c["label"], "width": 26} for c in dt["columns"]]
        rows = []
        for ln in dt["lines"]:
            row: dict[str, Any] = {"item": {"value": ln["label"], "bold": True} if ln["highlighted"] else ln["label"]}
            for c in ln["cells"]:
                cell: dict[str, Any] = {"value": c["text"]}
                if c["win"]:
                    cell.update({"fill": WIN_FILL, "color": WIN_COLOR, "bold": True})
                if ln["highlighted"]:
                    cell["bold"] = True
                if c.get("original"):
                    cell["comment"] = f"원래 값: {c['original']}" if lang != "en" else f"Original: {c['original']}"
                row[c["product_id"]] = cell
            rows.append(row)
        notes = [f"{n['mark']} {n['text']}" for n in dt["footnotes"]] + [src]
        sheets = []
        if comp:
            d = comp["data"]
            ccols = [{"key": f"c{i}", "label": h, "width": 22 if i != 1 else 30} for i, h in enumerate(d["columns"])]
            crow = []
            for r in d["rows"]:
                vals = [r["item"], r["requirement"], r["value"], (VERDICT_KO if lang != "en" else VERDICT_EN)[r["verdict"]] + (f" · {r['note']}" if r.get("note") else "")]
                if "원문" in d["columns"]:
                    vals.append(f"p.{r['page']}" if r.get("page") else "")
                crow.append({f"c{i}": v for i, v in enumerate(vals)})
            sheets.append({"name": tabs[2], "title": d["title"], "columns": ccols, "rows": crow})
        sheets.append({"name": tabs[0], "title": title, "subtitle": None, "columns": cols, "rows": rows, "notes": notes})
        ns_rows = []
        for key, c in (sheet.get("cells") or {}).items():
            rid, pid = key.split("|")
            r = next((x for x in sheet.get("rows") or [] if x["id"] == rid), None)
            p = next((x for x in sheet.get("products") or [] if x["id"] == pid), None)
            if not r or not p or (r.get("hidden") and _opts(options)["drop_hidden"]):
                continue
            for s in c.get("sources") or []:
                ns_rows.append({"row": r["label_ko"], "col": p["display_name"], "src": s.get("label") or s.get("kind"), "tier": s.get("tier") or "",
                                "ver": s.get("version_or_date") or "", "quote": (s.get("quote") or "")[:200]})
        for o in dt["originals"]:
            ns_rows.append({"row": o["row"], "col": o["product"], "src": "원래 값" if lang != "en" else "Original value", "tier": "", "ver": "", "quote": o["original"]})
        for pl in dt["pending_list"]:
            ns_rows.append({"row": pl["row"], "col": pl["product"], "src": "확인 중인 값" if lang != "en" else "To be confirmed", "tier": "", "ver": "", "quote": ""})
        for r in sheet.get("rows") or []:
            if (r.get("derived") or {}).get("basis"):
                ns_rows.append({"row": r["label_ko"], "col": "", "src": "계산 기준", "tier": "T6", "ver": "", "quote": r["derived"]["basis"]})
        sheets.append({"name": tabs[1], "title": tabs[1], "columns": [
            {"key": "row", "label": "행" if lang != "en" else "Row", "width": 22}, {"key": "col", "label": "열" if lang != "en" else "Column", "width": 16},
            {"key": "src", "label": "출처" if lang != "en" else "Source", "width": 22}, {"key": "tier", "label": "등급" if lang != "en" else "Tier", "width": 8},
            {"key": "ver", "label": "버전" if lang != "en" else "Version", "width": 12}, {"key": "quote", "label": "인용" if lang != "en" else "Quote", "width": 60}],
            "rows": ns_rows})
        return {"sheets": sheets}, summary
    if fmt == "pdf":
        size, orient = _pdf_size(fs.get("paper") or "a4_landscape")
        cols = [head_item] + [c["label"] for c in dt["columns"]]
        trows = []
        for ln in dt["lines"]:
            row = [{"text": ln["label"], "bold": True} if ln["highlighted"] else ln["label"]]
            for c in ln["cells"]:
                cell: dict[str, Any] = {"text": c["text"]}
                if c["win"]:
                    cell.update({"fill": WIN_FILL, "bold": True})
                row.append(cell if len(cell) > 1 else c["text"])
            trows.append(row)
        sections = []
        if comp:
            d = comp["data"]
            sections.append({"heading": d["title"], "table": {"columns": d["columns"], "rows": [
                [r["item"], r["requirement"], r["value"], (VERDICT_KO if lang != "en" else VERDICT_EN)[r["verdict"]] + (f" · {r['note']}" if r.get("note") else "")]
                + ([f"p.{r['page']}" if r.get("page") else ""] if "원문" in d["columns"] else []) for r in d["rows"]]}})
        sections.append({"heading": title, "table": {"columns": cols, "rows": trows},
                         "paragraphs": [f"{n['mark']} {n['text']}" for n in dt["footnotes"]], "sources": [src]})
        summary.update({"page_size": size, "orientation": orient})
        return {"title": title, "subtitle": sheet.get("customer_name") or None, "sections": sections, "page_size": size, "orientation": orient}, summary
    # pptx: 1장 · 행 12 초과면 2장(제안)
    cols = [head_item] + [c["label"] for c in dt["columns"]]
    lines = dt["lines"]
    per = 12
    chunks = [lines[i:i + per] for i in range(0, max(len(lines), 1), per)] or [[]]
    slides = []
    tpl = "SC-A" if len(dt["columns"]) >= 2 else "SD-A"
    for i, ch in enumerate(chunks):
        trows = []
        hl = []
        for j, ln in enumerate(ch):
            row = [ln["label"]] + [({"text": c["text"], "bold": True, "fill": WIN_FILL} if c["win"] else c["text"]) for c in ln["cells"]]
            trows.append(row)
            if ln["highlighted"]:
                hl.append(j)
        t = title + (f" ({i + 1}/{len(chunks)})" if len(chunks) > 1 else "")
        slots: dict[str, Any] = {"title": t, "subtitle": src, "table": {"columns": cols, "rows": trows, "highlight_rows": hl}}
        if tpl == "SD-A":
            p = S.products_ordered(sheet)[0] if sheet.get("products") else None
            slots["product"] = {"title": (p or {}).get("display_name") or "", "body": (p or {}).get("bubble_label") or "", "tag": "", "image": None}
        slides.append({"template_code": tpl, "slots": slots, "footnotes": [{"label": f"{n['mark']} {n['text']}"} for n in dt["footnotes"]],
                       "sources": [{"label": src}]})
    if comp:
        d = comp["data"]
        slides.insert(0, {"template_code": "SC-B", "slots": {"title": d["title"], "subtitle": f"{d['model_label']}", "table": {
            "columns": d["columns"], "rows": [[r["item"], r["requirement"], r["value"], (VERDICT_KO if lang != "en" else VERDICT_EN)[r["verdict"]]]
                                             + ([f"p.{r['page']}" if r.get("page") else ""] if "원문" in d["columns"] else []) for r in d["rows"]]}}})
    summary["slide_count"] = len(slides)
    return {"title": title, "lang": "en" if lang == "en" else "ko", "slides": slides}, summary
