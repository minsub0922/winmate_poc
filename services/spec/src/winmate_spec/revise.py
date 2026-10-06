"""말로 수정(06-spec §7.5 `spec_revise`) — LLM 은 조작만 고른다(값은 넣지 않음). 조작 검사 · 대상 해소 · 반영은 결정적.

task 이름(§7.10 `spec.interpret_request.v1`): 문맥마다 나눈다(mock 고정 응답이 문맥별로 결정적이도록)
  result → sp.interpret_request · generating → sp.interpret_request_memo · warnings → sp.interpret_request_warnings
  export → sp.interpret_request_export · edit → sp.interpret_request_edit · find/requirements → sp.interpret_request
"""
from __future__ import annotations

import json
import logging
from typing import Any

from rapidfuzz import fuzz
from winmate_common.ai import ai

from . import sheet as S
from .rules import items as itemcat

log = logging.getLogger("winmate.spec.revise")

ALLOWED = {"add_product", "remove_product", "set_role", "rename_column", "add_rows", "add_derived_row", "remove_row", "move_row", "hide_row",
           "show_row", "highlight_row", "unhighlight_row", "set_memo", "set_format", "export_also", "find_alternatives"}
EDIT_ALLOWED = {"move_row", "hide_row", "show_row", "highlight_row", "unhighlight_row", "set_memo", "add_rows", "remove_row"}
TASKS = {"result": "sp.interpret_request", "generating": "sp.interpret_request_memo", "warnings": "sp.interpret_request_warnings",
         "export": "sp.interpret_request_export", "edit": "sp.interpret_request_edit", "find": "sp.interpret_request",
         "requirements": "sp.interpret_request"}

SCHEMA = {
    "type": "object",
    "properties": {
        "ops": {"type": "array", "items": {"type": "object", "properties": {
            "op": {"type": "string", "enum": sorted(ALLOWED)},
            "args": {"type": "object"}}, "required": ["op"]}},
        "reply": {"type": "string"},
        "needs_clarification": {"type": "string"},
    },
    "required": ["ops"],
}

SYSTEM = ("당신은 Spec 시트 편집 도우미다. 사용자의 요청을 시트 조작 목록으로만 바꾼다. 셀 값(숫자 · 스펙)은 절대 정하지 않는다 — 값을 바꾸는 요청이면 "
          "ops 를 비우고 needs_clarification 에 '셀을 눌러 직접 고쳐 주세요' 라고 쓴다. 행은 row_id 나 행 이름(row), 열은 product_id 나 모델 이름(name)으로 가리킨다. "
          "허용 조작: " + ", ".join(sorted(ALLOWED)))


def sheet_summary(s: dict[str, Any]) -> dict[str, Any]:
    """LLM 입력 — 시트 요약만(값은 넣지 않는다, §7.5)."""
    return {"rows": [{"row_id": r["id"], "label": r["label_ko"]} for r in S.rows_ordered(s)],
            "products": [{"product_id": p["id"], "label": p["display_name"], "role": p.get("role", "proposed")} for p in S.products_ordered(s)],
            "settings": {k: (s.get("format") or {}).get(k) for k in ("formats", "language", "length_unit", "weight_unit")},
            "items": [{"key": it["key"], "label": it["label"]} for it in itemcat.item_list()]}


async def interpret(s: dict[str, Any], text: str, *, context: str) -> dict[str, Any]:
    payload = {"text": text, "context": context, "sheet": sheet_summary(s)}
    res = await ai().json(TASKS.get(context, "sp.interpret_request"), json.dumps(payload, ensure_ascii=False), SCHEMA, system=SYSTEM,
                          confidential=bool(s.get("customer_name")) or context in ("requirements",))
    return validate(s, res, context=context)


def validate(s: dict[str, Any], res: dict[str, Any], *, context: str) -> dict[str, Any]:
    """대상이 있는 허용 조작만 남기고, 나머지는 needs_clarification(§7.11-6). 값을 정하는 조작은 거절(§9.13-97)."""
    allowed = EDIT_ALLOWED if context == "edit" else ALLOWED
    ok: list[dict[str, Any]] = []
    rejected: list[str] = []
    for op in res.get("ops") or []:
        name = op.get("op") or ""
        args = dict(op.get("args") or {})
        if name not in allowed:
            rejected.append(name)
            continue
        if name in ("remove_row", "move_row", "hide_row", "show_row", "highlight_row", "unhighlight_row", "set_memo"):
            row = find_row(s, args.get("row_id") or args.get("row") or args.get("label"))
            if row is None:
                rejected.append(name)
                continue
            args["row_id"] = row["id"]
        if name in ("remove_product", "set_role", "rename_column"):
            p = find_product(s, args.get("product_id") or args.get("name") or args.get("model"))
            if p is None:
                rejected.append(name)
                continue
            args["product_id"] = p["id"]
        if name == "add_product" and not (args.get("query") or args.get("model") or args.get("name")):
            rejected.append(name)
            continue
        if name == "add_rows":
            keys = resolve_row_keys(args)
            if not keys:
                rejected.append(name)
                continue
            args["row_keys"] = keys
        ok.append({"op": name, "args": args})
    out: dict[str, Any] = {"ops": ok, "reply": res.get("reply")}
    if rejected or (not ok and not res.get("reply")):
        msg = res.get("needs_clarification")
        if any(x in ("set_value", "set_cell", "update_value", "set_cell_value") for x in rejected) or (rejected and not msg):
            msg = msg or "그 요청은 셀 값을 직접 정하는 것이라 반영하지 않았어요. 셀을 눌러 값을 고쳐 주세요."
        out["needs_clarification"] = msg or "어떤 행이나 열을 말씀하시는지 조금 더 알려 주세요."
    elif res.get("needs_clarification"):
        out["needs_clarification"] = res["needs_clarification"]
    return out


def find_row(s: dict[str, Any], ref: str | None) -> dict[str, Any] | None:
    if not ref:
        return None
    rows = S.rows_ordered(s)
    for r in rows:
        if r["id"] == ref or r["row_key"] == ref:
            return r
    best, score = None, 0.0
    for r in rows:
        sc = max(fuzz.partial_ratio(ref, r["label_ko"]), 100.0 if ref in r["label_ko"] else 0.0)
        if sc > score:
            best, score = r, sc
    return best if score >= 70 else None


def find_product(s: dict[str, Any], ref: str | None) -> dict[str, Any] | None:
    if not ref:
        return None
    for p in S.products_ordered(s):
        if ref in (p["id"], p.get("model_code"), p.get("display_name"), p.get("ref")):
            return p
    up = ref.upper()
    for p in S.products_ordered(s):
        if up in (p.get("display_name") or "").upper() or up in (p.get("bubble_label") or "").upper():
            return p
    return None


def resolve_row_keys(args: dict[str, Any]) -> list[str]:
    keys = [k for k in args.get("row_keys") or [] if k in itemcat.all_row_keys()]
    if args.get("item_key"):
        keys += [r["row_key"] for r in itemcat.rows_of_item(args["item_key"])]
    label = args.get("label") or args.get("item") or args.get("row")
    if label and not keys:
        for it in itemcat.item_list():
            if label in it["label"] or it["label"] in label:
                keys += [r["row_key"] for r in it.get("rows") or []]
                break
            for r in it.get("rows") or []:
                if label in r["label_ko"] or fuzz.partial_ratio(label, r["label_ko"]) >= 80:
                    keys.append(r["row_key"])
    return list(dict.fromkeys(keys))


def apply_sheet_ops(s: dict[str, Any], ops: list[dict[str, Any]]) -> list[str]:
    """시트에 바로 반영하는 조작(행 · 표시). 제품 추가 · 형식 · 내보내기는 호출 쪽이 처리한다. 돌려줌: 반영한 조작 이름."""
    applied: list[str] = []
    rows = S.rows_ordered(s)
    for op in ops:
        name, a = op["op"], op.get("args") or {}
        row = next((r for r in rows if r["id"] == a.get("row_id")), None)
        if name == "add_derived_row":
            if not any(r["row_key"] == "derived:annual_energy_cost" for r in rows):
                nr = S.make_row("derived:annual_energy_cost", added_by="request", item_key=None, ord_=len(rows))
                nr["derived"] = {"key": "annual_energy_cost", "price": None, "basis": None}
                rows.append(nr)
            applied.append(name)
        elif name == "add_rows":
            for rk in a.get("row_keys") or []:
                if not any(r["row_key"] == rk for r in rows):
                    meta = itemcat.row_meta(rk)
                    rows.append(S.make_row(rk, added_by="request", item_key=meta.get("item_key"), ord_=len(rows)))
                    for it in s.get("items") or []:
                        if it["key"] == meta.get("item_key"):
                            it["checked"] = True
            applied.append(name)
        elif name == "remove_row" and row:
            rows.remove(row)
            s["cells"] = {k: v for k, v in (s.get("cells") or {}).items() if not k.startswith(row["id"] + "|")}
            applied.append(name)
        elif name == "move_row" and row:
            rows.remove(row)
            pos = a.get("position") or a.get("to")
            if pos in ("bottom", "end", "맨 아래", "last"):
                idx = len(rows)
            elif pos in ("top", "first", "맨 위"):
                idx = 0
            else:
                idx = int(a.get("to_index") if a.get("to_index") is not None else len(rows))
            rows.insert(max(0, min(idx, len(rows))), row)
            applied.append(name)
        elif name in ("hide_row", "show_row") and row:
            row["hidden"] = name == "hide_row"
            applied.append(name)
        elif name in ("highlight_row", "unhighlight_row") and row:
            row["highlighted"] = name == "highlight_row"
            applied.append(name)
        elif name == "set_memo" and row:
            row["memo"] = {"text": a.get("text") or "", "mode": a.get("mode") or "footnote"}
            applied.append(name)
        elif name == "remove_product":
            pid = a.get("product_id")
            s["products"] = [p for p in s.get("products") or [] if p["id"] != pid]
            s["cells"] = {k: v for k, v in (s.get("cells") or {}).items() if not k.endswith("|" + pid)}
            S.renumber_products(s)
            S.recompute_kind(s)
            applied.append(name)
        elif name == "set_role":
            p = next((x for x in s.get("products") or [] if x["id"] == a.get("product_id")), None)
            if p and a.get("role") in ("proposed", "existing", "alternative"):
                p["role"] = a["role"]
                applied.append(name)
        elif name == "rename_column":
            p = next((x for x in s.get("products") or [] if x["id"] == a.get("product_id")), None)
            if p:
                p["column_label"] = (a.get("label") or a.get("column_label") or "").strip() or None
                applied.append(name)
    for i, r in enumerate(rows):
        r["ord"] = i
    s["rows"] = rows
    return applied


def edit_ops_from(ops: list[dict[str, Any]], s: dict[str, Any], view_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """편집 세션 문맥: LLM 조작 → 세션 조작(EditOp)."""
    out = []
    for op in ops:
        name, a = op["op"], op.get("args") or {}
        if name == "move_row":
            pos = a.get("position") or a.get("to")
            idx = len(view_rows) - 1 if pos in ("bottom", "end", "맨 아래", "last") else (0 if pos in ("top", "first", "맨 위") else int(a.get("to_index") or 0))
            out.append({"op": "move_row", "row_id": a["row_id"], "to_index": idx})
        elif name in ("hide_row", "show_row", "highlight_row", "unhighlight_row", "remove_row"):
            out.append({"op": name, "row_id": a["row_id"]})
        elif name == "set_memo":
            out.append({"op": "set_memo", "row_id": a["row_id"], "text": a.get("text") or "", "mode": a.get("mode") or "footnote"})
        elif name == "add_rows":
            out.append({"op": "add_rows", "row_keys": a.get("row_keys") or []})
    return out
