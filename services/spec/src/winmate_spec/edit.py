"""편집 세션(SP3E, 06-spec §4.12 · §6.8) — 서버가 세션을 보관(새로고침해도 유지), `편집 완료` 때 한 번에 반영(version +1)."""
from __future__ import annotations

import copy
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import new_id

from . import config, ops, repo
from . import sheet as S
from .catalog import catalog
from .rules import edit as E
from .rules import items as itemcat
from .rules.values import catalog_candidate, is_complete


def new_session(s: dict[str, Any]) -> dict[str, Any]:
    return {"sheet_id": s["id"], "base_version": s.get("doc_version", 0), "base_rows": copy.deepcopy(S.rows_ordered(s)),
            "base_products": copy.deepcopy(S.products_ordered(s)), "ops": [], "cursor": 0, "status": "open", "added_cells": {},
            "created_at": config.now_iso()}


def view(sess: dict[str, Any], sid: str, s: dict[str, Any]) -> dict[str, Any]:
    active = sess["ops"][: sess["cursor"]]
    rows, products, _ = E.apply_ops(sess["base_rows"], sess["base_products"], active)
    base_index = {r["id"]: i for i, r in enumerate(sorted(sess["base_rows"], key=lambda r: r.get("ord", 0)))}
    added_ids = {r["id"] for op in active if op.get("op") == "add_rows" for r in op.get("_rows") or []}
    moved_ids = {op.get("row_id") for op in active if op.get("op") == "move_row"}
    cells = {**(s.get("cells") or {}), **(sess.get("added_cells") or {})}
    tmp = {**s, "rows": rows, "products": products, "cells": cells}
    f = S.fmt_of(s)
    wmap, _ = S.cell_warning_map(s)
    out_rows = []
    for i, r in enumerate(rows):
        wins = S.row_wins(tmp, r)
        tags, moved = E.tags_for(r, base_index, added_ids, i, moved_ids)
        out_rows.append({
            "id": r["id"], "item_key": r.get("item_key"), "row_key": r["row_key"], "label": r["label_ko"],
            "label_en": " · ".join(r.get("en_lines") or []) or None, "ord": i, "hidden": bool(r.get("hidden")),
            "highlighted": bool(r.get("highlighted")), "memo": r.get("memo"), "added_by": r.get("added_by") or "items",
            "cells": [S.render_cell(tmp, r, p, f, win=wins.get(p["id"], False), wmap=wmap, checks_by_cell={}) for p in products],
            "tags": tags, "moved": moved,
        })
    summ = E.summary(active)
    labels = {r["id"]: r["label_ko"] for r in rows + sess["base_rows"]}
    cols = {p["id"]: p["display_name"] for p in products}
    hidden = len([r for r in rows if r.get("hidden")])
    return {"session_id": sess["id"], "base_version": sess["base_version"], "current_version": s.get("doc_version", 0),
            "stale": s.get("doc_version", 0) != sess["base_version"], "title": S.T.table_title(s, "ko"),
            "columns": [{"product_id": p["id"], "label": p.get("column_label") or p["display_name"], "role": p.get("role") or "proposed"}
                        for p in products],
            "rows": out_rows, "hidden_count": hidden, "visible": len(rows) - hidden, "total": len(rows),
            "missing_items": E.missing_items(rows), "addable_rows": E.addable_rows(rows), "summary": summ,
            "summary_text": E.summary_text(summ), "can_undo": sess["cursor"] > 0, "can_redo": sess["cursor"] < len(sess["ops"]),
            "history": E.history(active, labels, cols), "status": sess["status"]}


async def compute_rows(s: dict[str, Any], row_keys: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """추가할 행 + 그 칸 값(카탈로그에서 바로, 결정적 — LLM 없음). 값이 없으면 [확정 필요](커밋 때 값 확인)."""
    cat = catalog()
    ver = (s.get("catalog") or {}).get("version") or await cat.version()
    ps = S.products_ordered(s)
    codes = [p["model_code"] for p in ps if p.get("model_code") and p.get("in_catalog", True)]
    specs = await cat.specs(codes) if codes else {}
    rows, cells = [], {}
    for rk in row_keys:
        meta = itemcat.row_meta(rk)
        r = S.make_row(rk, added_by="edit", item_key=meta.get("item_key"))
        rows.append(r)
        for p in ps:
            sp = specs.get(p.get("model_code") or "")
            c = catalog_candidate(rk, sp, ver) if sp else None
            if c and is_complete(rk, c.value):
                cells[S.ck(r["id"], p["id"])] = {"value": c.value, "state": "ok", "sources": c.sources, "catalog_value": c.value}
            else:
                cells[S.ck(r["id"], p["id"])] = {"value": c.value if c else None, "state": "pending", "sources": c.sources if c else [],
                                                 "alt_measures": c.alt_measures if c else [], "needs_check": True}
    return rows, cells


async def add_ops(sid: str, ses: str, new_ops: list[dict[str, Any]]) -> dict[str, Any]:
    s = await repo.amust("sheets", sid)
    sess = await repo.amust("edit_sessions", ses, "편집 세션")
    if sess.get("sheet_id") != sid or sess.get("status") != "open":
        raise ApiError(409, "SESSION_CLOSED", "이미 끝난 편집 세션이에요.")
    prepared = []
    cur_rows, _, _ = E.apply_ops(sess["base_rows"], sess["base_products"], sess["ops"][: sess["cursor"]])
    present = {r["row_key"] for r in cur_rows}
    extra_cells: dict[str, Any] = {}
    for op in new_ops:
        op = {k: v for k, v in op.items() if v is not None}
        if op.get("op") == "add_rows":
            keys = list(op.get("row_keys") or [])
            if op.get("item_key"):
                keys += [r["row_key"] for r in itemcat.rows_of_item(op["item_key"])]
            keys = [k for k in dict.fromkeys(keys) if k in itemcat.all_row_keys() and k not in present]
            if not keys:
                continue
            rows, cells = await compute_rows(s, keys)
            op["_rows"] = rows
            op["row_keys"] = keys
            extra_cells.update(cells)
            present |= set(keys)
        prepared.append(op)

    def fn(x: dict[str, Any]) -> None:
        x["ops"] = x["ops"][: x["cursor"]] + prepared
        x["cursor"] = len(x["ops"])
        x["added_cells"] = {**(x.get("added_cells") or {}), **extra_cells}

    sess, _ = await repo.amutate("edit_sessions", ses, fn, what="편집 세션")
    return view(sess, sid, s)


async def add_llm_ops(sid: str, ses: str, llm_ops: list[dict[str, Any]]) -> list[str]:
    from .revise import edit_ops_from
    s = await repo.amust("sheets", sid)
    sess = await repo.amust("edit_sessions", ses, "편집 세션")
    rows, _, _ = E.apply_ops(sess["base_rows"], sess["base_products"], sess["ops"][: sess["cursor"]])
    eops = edit_ops_from(llm_ops, s, rows)
    if eops:
        await add_ops(sid, ses, eops)
    return [o["op"] for o in eops]


async def move_cursor(sid: str, ses: str, action: str) -> dict[str, Any]:
    s = await repo.amust("sheets", sid)

    def fn(x: dict[str, Any]) -> None:
        if x.get("status") != "open":
            raise ApiError(409, "SESSION_CLOSED", "이미 끝난 편집 세션이에요.")
        if action == "undo":
            x["cursor"] = max(0, x["cursor"] - 1)
        elif action == "redo":
            x["cursor"] = min(len(x["ops"]), x["cursor"] + 1)
        elif action == "reset":
            x["ops"] = []
            x["cursor"] = 0
            x["added_cells"] = {}

    sess, _ = await repo.amutate("edit_sessions", ses, fn, what="편집 세션")
    return view(sess, sid, s)


async def commit(sid: str, ses: str, rebase: bool, by: str) -> dict[str, Any]:
    sess = await repo.amust("edit_sessions", ses, "편집 세션")
    if sess.get("status") != "open":
        raise ApiError(409, "SESSION_CLOSED", "이미 끝난 편집 세션이에요.")
    active = sess["ops"][: sess["cursor"]]

    def fn(x: dict[str, Any]) -> dict[str, Any]:
        cur = x.get("doc_version", 0)
        if cur != sess["base_version"] and not rebase:
            raise ApiError(409, "VERSION_CONFLICT", "시트가 바뀌었어요. 최신 시트에 내 편집을 다시 얹을까요?",
                           {"current_version": cur, "base_version": sess["base_version"]})
        base_rows = S.rows_ordered(x) if rebase else sess["base_rows"]
        base_products = S.products_ordered(x) if rebase else sess["base_products"]
        rows, products, skipped = E.apply_ops(base_rows, base_products, active)
        if rebase:
            # 시트의 지금 칸 · 경고는 그대로, 조작만 다시 얹는다(대상이 없어진 조작은 버림)
            pass
        cells = x.setdefault("cells", {})
        row_ids = {r["id"] for r in rows}
        for k in list(cells):
            if k.split("|")[0] not in row_ids:
                cells.pop(k)
        new_checks = []
        for k, c in (sess.get("added_cells") or {}).items():
            rid, pid = k.split("|")
            if rid in row_ids and k not in cells:
                c = dict(c)
                needs = c.pop("needs_check", False)
                cells[k] = c
                if needs and any(p["id"] == pid for p in products):
                    r = next(r for r in rows if r["id"] == rid)
                    p = next(p for p in products if p["id"] == pid)
                    if p.get("in_catalog", True) and p.get("model_code") and (p.get("lifecycle") or {}).get("status") not in ("discontinued", "eol_planned"):
                        from .generate import _missing_check
                        chk = _missing_check(r, p, c.get("alt_measures") or [])
                        new_checks.append(chk)
        for i, chk in enumerate(new_checks):
            chk["n"] = max([c.get("n", 0) for c in x.get("checks") or []] + [0]) + 1
            x.setdefault("checks", []).append(chk)
        x["rows"] = rows
        x["products"] = products
        present_items = {r.get("item_key") for r in rows}
        for it in x.get("items") or []:
            if it["key"] in present_items and not it.get("checked"):
                it["checked"] = True
                it["prechecked_by"] = "user"
            elif it["key"] not in present_items and it.get("checked"):
                it["checked"] = False
        x["warnings"] = [w for w in x.get("warnings") or [] if not w.get("row_id") or w["row_id"] in row_ids]
        x["checks"] = [c for c in x.get("checks") or [] if not c.get("row_id") or c["row_id"] in row_ids]
        if active:
            S.bump_version(x, "edit")
        S.refresh_status(x, x["id"])
        return {"skipped": skipped}

    saved, info = await repo.amutate("sheets", sid, fn)
    await repo.amutate("edit_sessions", ses, lambda x: x.update({"status": "committed", "committed_at": config.now_iso(), "by": by}),
                       what="편집 세션")
    if active:
        await repo.aput("snapshots", f"{sid}.v{saved['doc_version']}", S.snapshot_of(saved))
        from .links import mark_links_changed
        await mark_links_changed(saved)
        saved = await repo.amust("sheets", sid)
    await ops.publish(saved)
    return saved


def new_id_ses() -> str:
    return new_id("ses")
