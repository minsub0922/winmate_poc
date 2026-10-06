"""시트 편집 세션(SP3E, 06-spec §4.12 · §6.8) — 조작을 세션에 쌓고(실행 취소 · 다시 실행) 커밋 때 한 번에 반영."""
from __future__ import annotations

import copy
from typing import Any

from . import items as itemcat

KIND_OF = {"move_row": "move", "hide_row": "hide", "show_row": "hide", "highlight_row": "highlight", "unhighlight_row": "highlight",
           "set_memo": "memo", "delete_memo": "memo", "add_rows": "add", "remove_row": "remove", "move_column": "column"}
KIND_LABEL = [("move", "이동"), ("highlight", "강조"), ("memo", "메모"), ("hide", "숨김"), ("add", "추가"), ("remove", "삭제"), ("column", "열 이동")]


def apply_ops(rows: list[dict[str, Any]], products: list[dict[str, Any]], ops: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """rows · products(복사본)에 조작을 차례로 적용. 대상이 없는 조작은 건너뛴다. 돌려줌: (rows, products, 건너뛴 조작 설명)."""
    rows = copy.deepcopy(sorted(rows, key=lambda r: r.get("ord", 0)))
    products = copy.deepcopy(sorted(products, key=lambda p: p.get("ord", 0)))
    skipped: list[str] = []
    for op in ops:
        kind = op.get("op")
        rid = op.get("row_id")
        target = next((r for r in rows if r["id"] == rid), None) if rid else None
        if kind in ("move_row", "hide_row", "show_row", "highlight_row", "unhighlight_row", "set_memo", "delete_memo", "remove_row") and target is None:
            skipped.append(f"{kind}:{rid}")
            continue
        if kind == "move_row":
            rows.remove(target)
            idx = max(0, min(int(op.get("to_index") or 0), len(rows)))
            rows.insert(idx, target)
        elif kind == "hide_row":
            target["hidden"] = True
        elif kind == "show_row":
            target["hidden"] = False
        elif kind == "highlight_row":
            target["highlighted"] = True
        elif kind == "unhighlight_row":
            target["highlighted"] = False
        elif kind == "set_memo":
            target["memo"] = {"text": (op.get("text") or "").strip(), "mode": op.get("mode") or "footnote"}
        elif kind == "delete_memo":
            target["memo"] = None
        elif kind == "remove_row":
            rows.remove(target)
        elif kind == "add_rows":
            for nr in op.get("_rows") or []:
                if not any(r["row_key"] == nr["row_key"] for r in rows):
                    rows.append(copy.deepcopy(nr))
        elif kind == "move_column":
            p = next((x for x in products if x["id"] == op.get("product_id")), None)
            if p is None:
                skipped.append(f"move_column:{op.get('product_id')}")
                continue
            products.remove(p)
            idx = max(0, min(int(op.get("to_index") or 0), len(products)))
            products.insert(idx, p)
    for i, r in enumerate(rows):
        r["ord"] = i
    for i, p in enumerate(products):
        p["ord"] = i
    return rows, products, skipped


def summary(ops: list[dict[str, Any]]) -> dict[str, int]:
    out = {"total": len(ops), "move": 0, "highlight": 0, "memo": 0, "hide": 0, "add": 0, "remove": 0, "column": 0}
    for op in ops:
        out[KIND_OF.get(op.get("op") or "", "move")] += 1
    return out


def summary_text(s: dict[str, int]) -> str:
    if not s["total"]:
        return "시트 편집 · 변경 없음"
    parts = [f"{lab} {s[k]}" for k, lab in KIND_LABEL if s.get(k)]
    return f"시트 편집 · 변경 {s['total']}건 — {' · '.join(parts)}"


def history(ops: list[dict[str, Any]], labels: dict[str, str], col_labels: dict[str, str]) -> list[dict[str, Any]]:
    out = []
    for i, op in enumerate(ops):
        k = op.get("op")
        lab = labels.get(op.get("row_id") or "", "")
        text = {
            "move_row": f"{lab} 순서 바꿈", "hide_row": f"{lab} 숨김", "show_row": f"{lab} 다시 보이기", "highlight_row": f"{lab} 강조",
            "unhighlight_row": f"{lab} 강조 해제", "set_memo": f"{lab} 메모", "delete_memo": f"{lab} 메모 삭제", "remove_row": f"{lab} 삭제",
            "add_rows": " · ".join(r["label_ko"] for r in op.get("_rows") or []) + " 추가",
            "move_column": f"{col_labels.get(op.get('product_id') or '', '열')} 열 이동",
        }.get(k or "", k or "")
        out.append({"n": i + 1, "text": text})
    return out


def tags_for(row: dict[str, Any], base_index: dict[str, int], added_ids: set[str], cur_index: int,
             moved_ids: set[str] | None = None) -> tuple[list[str], int]:
    """태그: 강조 · ↑/↓ n칸(직접 옮긴 행만, 세션 시작 위치 대비) · 숨김 · 추가됨."""
    tags: list[str] = []
    moved = 0
    if row.get("highlighted"):
        tags.append("강조")
    if row["id"] in base_index and (moved_ids is None or row["id"] in moved_ids):
        moved = base_index[row["id"]] - cur_index
        if moved > 0:
            tags.append(f"↑ {moved}칸")
        elif moved < 0:
            tags.append(f"↓ {-moved}칸")
    if row.get("hidden"):
        tags.append("숨김")
    if row["id"] in added_ids:
        tags.append("추가됨")
    return tags, moved


def missing_items(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    present = {r.get("item_key") for r in rows}
    return [{"key": it["key"], "label": it["label"]} for it in itemcat.item_list() if it["key"] not in present]


def addable_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    present = {r["row_key"] for r in rows}
    out = []
    for it in itemcat.item_list():
        for r in it.get("rows") or []:
            if r["row_key"] not in present:
                out.append({"row_key": r["row_key"], "label": r["label_ko"], "item_key": it["key"]})
    return out
