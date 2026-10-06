"""시트 작업 문서 — 만들기 · 제품 · 항목 ↔ 행 · 칸 · 화면 문서(SheetDoc) 그리기 · 번호 매기기.

저장 모양은 repo.py 머리말. 칸 키 = f"{row_id}|{product_id}".
"""
from __future__ import annotations

import copy
from typing import Any

from winmate_common.ids import new_id

from . import config
from .rules import items as itemcat
from .rules import text as T
from .rules.fmt import PENDING_EN, PENDING_KO, inch_from_code
from .rules.values import Fmt, compute_wins, render_lines, render_text

SYSTEM_FORMAT = {"formats": ["xlsx"], "language": "ko", "length_unit": "mm", "weight_unit": "kg", "paper": "a4_landscape",
                 "number_format": "1,234.5", "filename_base": None}

WARNING_ORDER = ["discontinued", "not_in_catalog", "value_mismatch_source", "catalog_changed", "value_mismatch_proposal", "requirement_unmet"]
WARNING_TAG = {"discontinued": "단종", "not_in_catalog": "카탈로그 없음", "value_mismatch_source": "값 불일치", "catalog_changed": "카탈로그 변경",
               "value_mismatch_proposal": "값 불일치", "requirement_unmet": "요구 미충족"}
WARNING_GROUP = {"discontinued": "discontinued", "not_in_catalog": "discontinued", "value_mismatch_source": "mismatch",
                 "catalog_changed": "mismatch", "value_mismatch_proposal": "mismatch", "requirement_unmet": "unmet"}
ROLE_LABEL = {"proposed": "제안 모델", "existing": "고객 기존 장비", "alternative": "대안 모델"}


def ck(row_id: str, product_id: str) -> str:
    return f"{row_id}|{product_id}"


# ── 만들기 ───────────────────────────────────────────────

def new_sheet(*, owner_id: str, owner_name: str, start: str, prefs: dict[str, Any] | None = None, project_id: str | None = None,
              customer_name: str | None = None, origin: dict[str, Any] | None = None, target_proposal: dict[str, Any] | None = None,
              rq_ref: dict[str, Any] | None = None) -> dict[str, Any]:
    fmt = copy.deepcopy((prefs or {}).get("format") or SYSTEM_FORMAT)
    s: dict[str, Any] = {
        "owner_id": owner_id, "owner_name": owner_name, "title": "", "title_confirmed": False, "customer_name": customer_name,
        "project_id": project_id, "start": start, "kind": "req" if start == "requirements" else "single", "layout": "compare", "step": 1,
        "doc_version": 0, "versions": [], "catalog": {"adapter": config.catalog_adapter_name(), "version": "", "label": "사내 카탈로그"},
        "origin": origin, "target_proposal": target_proposal, "rq_ref": rq_ref,
        "options": {"highlight_wins": bool((prefs or {}).get("highlight_wins", True))},
        "format": fmt, "format_confirmed": False, "products": [], "items": [], "rows": [], "cells": {}, "checks": [], "warnings": [],
        "finder": None, "compliance": None, "datasheets": [], "template": None, "preview": {}, "generated_at": None, "saved_at": None,
        "archived_at": None, "archived": False, "active_job": None, "last_job_id": None, "pending_answers": None, "user_text": None,
        "ui_status": "draft", "status_text": "작성 중 1/3", "resume_route": "", "dismissed_fingerprints": [],
    }
    init_items(s)
    return s


def init_items(sheet: dict[str, Any]) -> None:
    if sheet.get("items"):
        return
    sheet["items"] = [{"key": it["key"], "checked": bool(it.get("default")), "prechecked_by": "default"} for it in itemcat.item_list()]


def recompute_kind(sheet: dict[str, Any]) -> None:
    """제품 수로 다시 정한다(§3.3). 규격서로 시작한 작업은 `대응표` 칩이 켜져 있는 한 `req`."""
    if sheet.get("start") == "requirements" and ((sheet.get("compliance") or {}).get("include") or {}).get("table", True):
        sheet["kind"] = "req"
        return
    sheet["kind"] = "compare" if len(sheet.get("products") or []) >= 2 else "single"


# ── 제품 ─────────────────────────────────────────────────

def product_from_spec(spec: dict[str, Any], *, source: str, role: str = "proposed", ref: str | None = None) -> dict[str, Any]:
    dn = spec.get("display_name") or spec.get("model_code")
    fam_en = spec.get("family_label_en")
    return {
        "id": new_id("spp"), "ref": ref or (f"kb:model:{spec['kb_model_id']}" if spec.get("kb_model_id") else f"custom:{dn}"),
        "model_code": spec.get("model_code"), "kb_model_id": spec.get("kb_model_id"), "family_id": spec.get("family_id"),
        "display_name": dn, "bubble_label": f"{fam_en} {dn}" if fam_en else dn, "family_label_en": fam_en,
        "series_code": spec.get("series_code"), "size_inch": spec.get("size_inch") or inch_from_code(spec.get("model_code")),
        "category_id": spec.get("category_id"), "role": role, "column_label": None, "ord": 0, "source": source,
        "custom": not spec.get("in_catalog", True), "in_catalog": bool(spec.get("in_catalog", True)),
        "lifecycle": {"status": "on_sale" if spec.get("in_catalog", True) else "unknown", "source": "KB(samsung.com 수집) — 목록 노출 = 판매 중(DR09)",
                      "sold_out": bool(spec.get("sold_out"))},
    }


def custom_product(name: str, *, source: str, role: str = "proposed") -> dict[str, Any]:
    return {
        "id": new_id("spp"), "ref": f"custom:{name}", "model_code": None, "kb_model_id": None, "family_id": None, "display_name": name,
        "bubble_label": name, "family_label_en": None, "series_code": None, "size_inch": None, "category_id": None, "role": role,
        "column_label": None, "ord": 0, "source": source, "custom": True, "in_catalog": False,
        "lifecycle": {"status": "unknown", "source": "사내 카탈로그에 없음"},
    }


def has_ref(sheet: dict[str, Any], ref: str | None, model_code: str | None = None) -> bool:
    for p in sheet.get("products") or []:
        if ref and p.get("ref") == ref:
            return True
        if model_code and p.get("model_code") == model_code:
            return True
    return False


def renumber_products(sheet: dict[str, Any]) -> None:
    for i, p in enumerate(sorted(sheet.get("products") or [], key=lambda p: p.get("ord", 0))):
        p["ord"] = i


def products_ordered(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(sheet.get("products") or [], key=lambda p: p.get("ord", 0))


# ── 항목 ↔ 행 ────────────────────────────────────────────

def checked_keys(sheet: dict[str, Any]) -> list[str]:
    order = itemcat.item_keys()
    on = {i["key"] for i in sheet.get("items") or [] if i.get("checked")}
    return [k for k in order if k in on]


def rows_ordered(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(sheet.get("rows") or [], key=lambda r: r.get("ord", 0))


def make_row(row_key: str, *, added_by: str = "items", item_key: str | None = None, label: str | None = None, ord_: int = 0,
             derived: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = itemcat.row_meta(row_key)
    return {"id": new_id("srw"), "item_key": item_key if item_key is not None else meta.get("item_key"), "row_key": row_key,
            "label_ko": label or meta["label_ko"], "en_lines": meta.get("en_lines") or [], "ord": ord_, "hidden": False, "highlighted": False,
            "memo": None, "added_by": added_by, "derived": derived}


def sync_rows(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    """체크된 항목의 행이 있게, 꺼진 항목의 행은 빼게. 새로 생긴 행 목록을 돌려준다(파생 · 양식 행은 그대로)."""
    keys = checked_keys(sheet)
    rows = rows_ordered(sheet)
    present = {r["row_key"] for r in rows}
    keep = [r for r in rows if r.get("item_key") is None or r["item_key"] in keys or r["row_key"].startswith(("derived:", "template:"))]
    removed_ids = {r["id"] for r in rows} - {r["id"] for r in keep}
    if removed_ids:
        sheet["cells"] = {k: v for k, v in (sheet.get("cells") or {}).items() if k.split("|")[0] not in removed_ids}
    new_rows: list[dict[str, Any]] = []
    if not rows:
        # 처음: 항목 카탈로그 순서
        for k in keys:
            for r in itemcat.rows_of_item(k):
                new_rows.append(make_row(r["row_key"], item_key=k))
        keep = new_rows
    else:
        for k in keys:
            for r in itemcat.rows_of_item(k):
                if r["row_key"] not in present:
                    nr = make_row(r["row_key"], item_key=k)
                    new_rows.append(nr)
                    keep.append(nr)
    for i, r in enumerate(keep):
        r["ord"] = i
    sheet["rows"] = keep
    return new_rows


# ── 화면 문서 ────────────────────────────────────────────

def fmt_of(sheet: dict[str, Any], overrides: dict[str, Any] | None = None) -> Fmt:
    f = dict(sheet.get("format") or SYSTEM_FORMAT)
    for k, v in (overrides or {}).items():
        if v is not None:
            f[k] = v
    return Fmt.of(f)


def compare_products(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    """우위 계산에 들어가는 열(고객 기존 장비 · 단종 열 제외 — Q-SP-29)."""
    return [p for p in products_ordered(sheet) if p.get("role") != "existing"]


def row_wins(sheet: dict[str, Any], row: dict[str, Any]) -> dict[str, bool]:
    out: dict[str, bool] = {}
    ps = compare_products(sheet)
    if not (sheet.get("options") or {}).get("highlight_wins", True) or len(ps) < 2:
        return out
    cells = sheet.get("cells") or {}
    vals = []
    for p in ps:
        c = cells.get(ck(row["id"], p["id"])) or {}
        v = c.get("value") if c.get("state") not in ("flag", "checking", "pending", "sync_pending") or _partial_ok(c) else None
        vals.append(v)
    wins = compute_wins(row["row_key"], vals)
    for p, w in zip(ps, wins):
        out[p["id"]] = w
    return out


def _partial_ok(c: dict[str, Any]) -> bool:
    return c.get("state") == "pending" and bool(c.get("value"))


def footnotes(sheet: dict[str, Any], *, include_internal: bool = False, rows: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, str]], dict[str, str]]:
    """각주 목록과 행 → 표시. 행 메모(각주) → 파생 행 계산 기준 → 칸 각주(On Mode 기준) 순."""
    marks: dict[str, str] = {}
    notes: list[dict[str, str]] = []
    k = 0
    for r in rows if rows is not None else rows_ordered(sheet):
        memo = r.get("memo")
        if memo and (memo.get("mode") == "footnote" or include_internal):
            k += 1
            mk = "*" * k
            marks[r["id"]] = mk
            notes.append({"mark": mk, "text": f"{r['label_ko']} — {memo['text']}", "row_id": r["id"]})
    for r in rows if rows is not None else rows_ordered(sheet):
        if (r.get("derived") or {}).get("basis"):
            k += 1
            mk = "*" * k
            marks.setdefault(r["id"], mk)
            notes.append({"mark": mk, "text": f"계산 기준: {r['derived']['basis']}", "row_id": r["id"]})
    cells = sheet.get("cells") or {}
    for key, c in cells.items():
        if c.get("footnote"):
            rid, pid = key.split("|")
            p = next((x for x in sheet.get("products") or [] if x["id"] == pid), None)
            r = next((x for x in sheet.get("rows") or [] if x["id"] == rid), None)
            if p and r and (rows is None or r in rows):
                k += 1
                notes.append({"mark": "*" * k, "text": f"{r['label_ko']} · {p['display_name']} — {c['footnote']}", "row_id": rid})
    return notes, marks


def warning_numbers(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    """열린(open · decided) 경고에 번호를 매긴다: 종류 순서 → 행 순 → 열 순."""
    row_ord = {r["id"]: i for i, r in enumerate(rows_ordered(sheet))}
    col_ord = {p["id"]: i for i, p in enumerate(products_ordered(sheet))}
    ws = [w for w in sheet.get("warnings") or [] if w.get("status") in ("open", "decided")]
    ws.sort(key=lambda w: (WARNING_ORDER.index(w["kind"]) if w["kind"] in WARNING_ORDER else 99,
                           row_ord.get(w.get("row_id") or "", -1), col_ord.get(w.get("product_id") or "", -1), w.get("detected_at") or ""))
    for i, w in enumerate(ws):
        w["n"] = i + 1
    return ws


def cell_warning_map(sheet: dict[str, Any]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    """칸 → 경고 번호, 열(제품) → 경고 번호(단종 · 카탈로그 없음)."""
    per_cell: dict[str, list[int]] = {}
    per_col: dict[str, list[int]] = {}
    cells = sheet.get("cells") or {}
    for w in warning_numbers(sheet):
        if w["kind"] in ("discontinued", "not_in_catalog") and w.get("product_id"):
            per_col.setdefault(w["product_id"], []).append(w["n"])
            for r in sheet.get("rows") or []:
                c = cells.get(ck(r["id"], w["product_id"])) or {}
                if c.get("state") in ("pending", "flag") or c.get("value") is None:
                    per_cell.setdefault(ck(r["id"], w["product_id"]), []).append(w["n"])
        elif w.get("row_id") and w.get("product_id"):
            per_cell.setdefault(ck(w["row_id"], w["product_id"]), []).append(w["n"])
    return per_cell, per_col


def render_cell(sheet: dict[str, Any], row: dict[str, Any], p: dict[str, Any], f: Fmt, *, win: bool, wmap: dict[str, list[int]],
                checks_by_cell: dict[str, dict[str, Any]]) -> dict[str, Any]:
    c = (sheet.get("cells") or {}).get(ck(row["id"], p["id"]))
    lang = f.language
    if c is None:
        return {"product_id": p["id"], "text": "", "state": "checking", "win": False, "sources": [], "warning_ns": []}
    state = c.get("state", "ok")
    value = c.get("value")
    conv: bool = False
    orig: str | None = None
    if state == "flag":
        text = c.get("flag_text") or "값 없음"
        en_text = text
    elif state == "sync_pending":
        text = en_text = "[값]"
    else:
        text, conv, orig = render_text(row["row_key"], value, f, lang)
        en_text = render_text(row["row_key"], value, f, "en")[0]
    chk = checks_by_cell.get(ck(row["id"], p["id"]))
    return {
        "product_id": p["id"], "text": text, "text_en": en_text, "value": _value_model(row["row_key"], value), "state": state,
        "win": win, "converted": conv, "original_text": orig, "sources": c.get("sources") or [],
        "warning_ns": wmap.get(ck(row["id"], p["id"]), []), "check_n": chk["n"] if chk else None,
        "flag_text": c.get("flag_text") if state == "flag" else None,
    }


def _value_model(row_key: str, v: dict[str, Any] | None) -> dict[str, Any] | None:
    """계약의 Cell.value({num, num2, unit, parts})로 줄인다."""
    if not v:
        return None
    if row_key == "power":
        return {"num": v.get("typ"), "num2": v.get("max"), "unit": "W"}
    if row_key == "brightness_contrast":
        return {"num": v.get("nit"), "unit": "nit", "parts": [{"label": "contrast", "num": v.get("ca"), "unit": ":1"}] if v.get("ca") else None}
    if row_key == "size_resolution":
        return {"num": v.get("inch"), "unit": "inch", "parts": [{"label": "resolution", "text": f"{v.get('w')}x{v.get('h')}"}] if v.get("w") else None}
    if row_key == "operation_hours":
        return {"num": v.get("hours"), "unit": "h/day"}
    if row_key == "warranty":
        return {"num": v.get("years"), "unit": "year"}
    if row_key == "weight":
        return {"num": v.get("set"), "num2": v.get("pkg"), "unit": "kg"}
    if row_key == "dimensions":
        return {"parts": [{"label": k, "num": v.get(k), "unit": "mm"} for k in ("w", "h", "d") if v.get(k) is not None]}
    if row_key == "bezel":
        return {"num": v.get("mm"), "unit": "mm"}
    if row_key == "derived:annual_energy_cost":
        return {"num": v.get("krw"), "num2": v.get("kwh"), "unit": "KRW"}
    parts = [{"label": k, "text": str(x)} for k, x in v.items() if x not in (None, False) and not isinstance(x, (dict, list))]
    return {"parts": parts} if parts else None


def build_table(sheet: dict[str, Any], *, f: Fmt | None = None, include_hidden: bool = True) -> dict[str, Any] | None:
    rows = rows_ordered(sheet)
    if not rows or not sheet.get("cells"):
        return None
    f = f or fmt_of(sheet)
    ps = products_ordered(sheet)
    wmap, _ = cell_warning_map(sheet)
    checks_by_cell = {ck(c["row_id"], c["product_id"]): c for c in sheet.get("checks") or [] if c.get("row_id") and c.get("status") == "open"}
    notes, marks = footnotes(sheet)
    out_rows = []
    win_rows = 0
    for r in rows:
        wins = row_wins(sheet, r)
        cells = [render_cell(sheet, r, p, f, win=wins.get(p["id"], False), wmap=wmap, checks_by_cell=checks_by_cell) for p in ps]
        any_win = any(c["win"] for c in cells)
        if any_win and not r.get("hidden"):
            win_rows += 1
        lines = []
        if f.language != "ko":
            per_p = [render_lines(r["row_key"], ((sheet.get("cells") or {}).get(ck(r["id"], p["id"])) or {}).get("value"), f, r["label_ko"],
                                  r.get("en_lines") or [r["label_ko"]]) for p in ps]
            if per_p and per_p[0]:
                for li, ln in enumerate(per_p[0]):
                    lines.append({"label": ln.label, "texts": [pp[li].text if li < len(pp) else "" for pp in per_p],
                                  "converted": [pp[li].converted if li < len(pp) else False for pp in per_p],
                                  "pending": [pp[li].pending if li < len(pp) else False for pp in per_p]})
        if not include_hidden and r.get("hidden"):
            continue
        out_rows.append({
            "id": r["id"], "item_key": r.get("item_key"), "row_key": r["row_key"], "label": r["label_ko"],
            "label_en": " · ".join(r.get("en_lines") or []) or None, "ord": r["ord"], "hidden": bool(r.get("hidden")),
            "highlighted": bool(r.get("highlighted")), "memo": r.get("memo"), "added_by": r.get("added_by") or "items",
            "footnote_mark": marks.get(r["id"]), "win": any_win, "cells": cells, "lines": lines,
        })
    visible = len([r for r in rows if not r.get("hidden")])
    return {
        "title": T.table_title(sheet, "ko"), "title_en": T.table_title(sheet, "en"), "rows": out_rows,
        "footnotes": [{"mark": n["mark"], "text": n["text"]} for n in notes], "source_line": T.source_line(sheet, sheet.get("cells") or {}),
        "win_rows": win_rows, "visible_rows": visible, "total_rows": len(rows), "hidden_rows": len(rows) - visible,
    }


def warnings_view(sheet: dict[str, Any]) -> dict[str, Any]:
    ws = warning_numbers(sheet)
    counts = {"all": len(ws), "discontinued": 0, "mismatch": 0, "unmet": 0}
    for w in ws:
        counts[WARNING_GROUP.get(w["kind"], "mismatch")] += 1
    items = []
    for w in ws:
        items.append({k: w.get(k) for k in ("id", "n", "kind", "title", "body", "row_id", "product_id", "link_id", "replacement", "options",
                                            "decision", "default_option", "status")} | {"tag": WARNING_TAG.get(w["kind"], w["kind"])})
    return {"open": len(ws), "counts": counts, "items": items}


def compliance_view(sheet: dict[str, Any]) -> dict[str, Any] | None:
    comp = sheet.get("compliance")
    if not comp:
        return None
    rows = comp.get("rows") or []
    counts = {"pass": len([r for r in rows if r.get("verdict") == "pass"]), "fail": len([r for r in rows if r.get("verdict") == "fail"]),
              "unknown": len([r for r in rows if r.get("verdict") == "unknown"])}
    tp = next((p for p in sheet.get("products") or [] if p["id"] == comp.get("target_product_id")), None)
    alt = next((r.get("alternative") for r in rows if r.get("alternative")), None)
    return {**comp, "counts": counts, "target_label": tp["display_name"] if tp else comp.get("target_label"),
            "alternative_label": (alt or {}).get("label")}


def preview_values(sheet: dict[str, Any]) -> dict[str, list[dict[str, Any] | None]]:
    """SP2 차이 문장용: 항목 → 제품 순서대로 대표 값(생성 전이면 제품 추가 때 미리 계산한 카탈로그 값)."""
    out: dict[str, list[dict[str, Any] | None]] = {}
    ps = products_ordered(sheet)
    prev = sheet.get("preview") or {}
    rows_by_key = {r["row_key"]: r for r in sheet.get("rows") or []}
    cells = sheet.get("cells") or {}
    for it in itemcat.item_list():
        rk = itemcat.rows_of_item(it["key"])[0]["row_key"]
        vals = []
        for p in ps:
            r = rows_by_key.get(rk)
            c = cells.get(ck(r["id"], p["id"])) if r else None
            v = (c or {}).get("value") if c and c.get("state") not in ("flag",) else None
            if v is None:
                v = (prev.get(p["id"]) or {}).get(rk)
            vals.append(v)
        out[it["key"]] = vals
    return out


def diff_items(sheet: dict[str, Any]) -> list[str]:
    """모델 간 표시값(정규화 뒤)이 다른 항목(식별 코드 항목 제외, §4.7.2)."""
    ps = products_ordered(sheet)
    if len(ps) < 2:
        return []
    from .rules.values import DIFF_EXCLUDED, diff_key
    prev = sheet.get("preview") or {}
    cells = sheet.get("cells") or {}
    rows_by_key = {r["row_key"]: r for r in sheet.get("rows") or []}
    out = []
    for it in itemcat.item_list():
        if it["key"] in DIFF_EXCLUDED:
            continue
        diff = False
        for rdef in it.get("rows") or []:
            rk = rdef["row_key"]
            vals = []
            for p in ps:
                r = rows_by_key.get(rk)
                c = cells.get(ck(r["id"], p["id"])) if r else None
                v = (c or {}).get("value") if c else None
                if v is None:
                    v = (prev.get(p["id"]) or {}).get(rk)
                vals.append(diff_key(rk, v) if v else "")
            if all(x == "" for x in vals):
                continue
            if len(set(vals)) > 1:
                diff = True
        if diff:
            out.append(it["key"])
    return out


def agent_texts(sheet: dict[str, Any]) -> dict[str, str | None]:
    return {
        "from_note": T.from_note(sheet),
        "sp2": T.diff_sentence(sheet, preview_values(sheet)),
        "sp2_user": T.sp2_user_line(sheet),
        "sp3g_user": T.sp3g_user_line(sheet),
        "sp3g": T.sp3g_agent(sheet),
        "sp3g_sub": T.sp3g_subtitle(sheet),
        "sp3": T.sp3_agent(sheet),
        "filename_default": T.default_filename(sheet),
        "saved_label": T.saved_label(sheet.get("saved_at")),
        "user_text": sheet.get("user_text"),
        "kind_name": T.kind_name(sheet),
    }


def refresh_status(sheet: dict[str, Any], sid: str) -> None:
    ui, text, route = T.status_of(sheet, sid)
    sheet["ui_status"], sheet["status_text"], sheet["resume_route"] = ui, text, route


def to_doc(sheet: dict[str, Any], *, links: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    sid = sheet["id"]
    ui, text, route = T.status_of(sheet, sid)
    cat_ver = (sheet.get("catalog") or {}).get("version") or ""
    ps = products_ordered(sheet)
    _, col_w = cell_warning_map(sheet)
    products = []
    for p in ps:
        lc = p.get("lifecycle") or {}
        products.append({**{k: p.get(k) for k in ("id", "ref", "model_code", "kb_model_id", "family_id", "display_name", "bubble_label",
                                                     "family_label_en", "series_code", "size_inch", "role", "column_label", "custom", "source")},
                         "lifecycle": {"status": lc.get("status", "unknown"), "source": lc.get("source", ""), "as_of": lc.get("as_of"),
                                       "successor": lc.get("successor"), "sold_out": bool(lc.get("sold_out"))},
                         "warning_ns": col_w.get(p["id"], [])})
    items = []
    by_key = {i["key"]: i for i in sheet.get("items") or []}
    for it in itemcat.item_list():
        si = by_key.get(it["key"]) or {"checked": False, "prechecked_by": "default"}
        items.append({"key": it["key"], "label": it["label"], "checked": bool(si.get("checked")), "prechecked_by": si.get("prechecked_by", "default")})
    checks = sorted([c for c in sheet.get("checks") or []], key=lambda c: c.get("n", 0))
    tpl = sheet.get("template")
    doc = {
        "id": sid, "version": sheet.get("doc_version", 0), "title": T.display_title(sheet), "title_confirmed": bool(sheet.get("title_confirmed")),
        "suggested_title": T.suggested_title(sheet), "customer_name": sheet.get("customer_name"), "project_id": sheet.get("project_id"),
        "start": sheet.get("start", "model"), "kind": sheet.get("kind", "single"), "layout": sheet.get("layout", "compare"),
        "step": sheet.get("step", 1), "ui_status": ui, "status_text": text, "resume_route": route,
        "catalog": {"label": "사내 카탈로그", "source_label": "사내 제품 카탈로그", "version": cat_ver},
        "origin": sheet.get("origin"), "target_proposal": sheet.get("target_proposal"), "products": products, "items": items,
        "options": sheet.get("options") or {"highlight_wins": True}, "format": sheet.get("format") or SYSTEM_FORMAT,
        "format_confirmed": bool(sheet.get("format_confirmed")), "format_draft": sheet.get("format_draft"), "table": build_table(sheet),
        "checks": {"open": len([c for c in checks if c.get("status") == "open"]), "items": checks},
        "warnings": warnings_view(sheet), "compliance": compliance_view(sheet), "finder": sheet.get("finder"),
        "template": {"id": tpl["id"], "name": tpl.get("name", ""), "status": tpl.get("status", ""), "file_id": tpl.get("file_id"),
                     "format": tpl.get("format")} if tpl else None,
        "datasheets": [{k: d.get(k) for k in ("id", "product_id", "file_id", "name", "pages", "status")} for d in sheet.get("datasheets") or []],
        "links": [{k: lk.get(k) for k in ("id", "proposal_id", "proposal_title", "section_no", "section_name", "sent_version", "status")}
                  for lk in links or []],
        "generated_at": sheet.get("generated_at"), "saved_at": sheet.get("saved_at"), "updated_at": touched(sheet),
        "created_at": sheet.get("created_at_app") or sheet.get("created_at"), "archived_at": sheet.get("archived_at"), "active_job": sheet.get("active_job"),
        "last_job_id": sheet.get("last_job_id"), "last_error": sheet.get("last_error"), "owner_name": sheet.get("owner_name"), "product_limit": config.PRODUCT_LIMIT,
        "agent": agent_texts(sheet),
    }
    return doc


def touched(doc: dict[str, Any]) -> str:
    """마지막 변경 시각(앱 시계) — 없으면 저장소 시각."""
    return doc.get("touched_at") or doc.get("updated_at") or ""


def snapshot_of(sheet: dict[str, Any]) -> dict[str, Any]:
    keep = ("title", "title_confirmed", "customer_name", "kind", "layout", "step", "catalog", "options", "format", "format_confirmed",
            "products", "items", "rows", "cells", "checks", "warnings", "compliance", "template", "generated_at", "preview", "datasheets")
    return copy.deepcopy({k: sheet.get(k) for k in keep})


def bump_version(sheet: dict[str, Any], reason: str) -> int:
    sheet["doc_version"] = int(sheet.get("doc_version") or 0) + 1
    sheet.setdefault("versions", []).append({"version": sheet["doc_version"], "reason": reason, "created_at": config.now_iso()})
    sheet["versions"] = sheet["versions"][-100:]
    return sheet["doc_version"]


def pending_text(lang: str) -> str:
    return PENDING_KO if lang == "ko" else PENDING_EN
