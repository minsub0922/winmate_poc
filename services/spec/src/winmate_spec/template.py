"""고객사 양식 올리기(06-spec §4.18 · §7.6 `spec_template`) — 양식 행 ↔ 시트 행 맞추기(LLM, confidential) + 결정적 검사."""
from __future__ import annotations

import json
import logging
from typing import Any

from winmate_common.ai import ai
from winmate_common.ids import new_id
from winmate_common.platform import file_meta, parsed_document

from . import ops, repo
from . import sheet as S
from .compliance import ai_error, ocr_pages

log = logging.getLogger("winmate.spec.template")

MAP_SCHEMA = {"type": "object", "properties": {
    "rows": {"type": "array", "items": {"type": "object", "properties": {"r": {"type": "integer"}, "row_key": {"type": ["string", "null"]}},
                                        "required": ["r"]}},
    "cols": {"type": "array", "items": {"type": "object", "properties": {"c": {"type": "integer"}, "product_id": {"type": ["string", "null"]},
                                                                         "role": {"type": "string", "enum": ["label", "product", "ignore"]}},
                                        "required": ["c", "role"]}},
    "title_cell": {"type": "string"}}, "required": ["rows"]}


async def read_template(file_id: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """양식 → (메타, 행[{r, label}], 열[{c, label}]). XLSX 는 첫 시트의 라벨 열 · 머리 행(결정적), 그 밖은 쪽 글 · 표."""
    meta = await file_meta(file_id)
    doc = await parsed_document(file_id)
    rows: list[dict[str, Any]] = []
    cols: list[dict[str, Any]] = []
    sheets = doc.get("sheets") or []
    if sheets:
        grid = sheets[0].get("rows") or []
        label_col = 0
        best = -1
        width = max((len(r) for r in grid), default=0)
        for c in range(width):
            n = sum(1 for r in grid if c < len(r) and isinstance(r[c], str) and r[c].strip())
            if n > best:
                best, label_col = n, c
        head = next((i for i, r in enumerate(grid) if sum(1 for x in r if x not in (None, "")) >= 2), 0)
        for c, x in enumerate(grid[head] if grid else []):
            if x not in (None, "") and c != label_col:
                cols.append({"c": c + 1, "label": str(x)})
        for i, r in enumerate(grid):
            if i == head:
                continue
            if label_col < len(r) and isinstance(r[label_col], str) and r[label_col].strip():
                rows.append({"r": i + 1, "label": r[label_col].strip()})
        return meta, rows, cols
    pages = [{"page": p.get("no"), "text": p.get("text") or ""} for p in doc.get("pages") or []]
    pages = await ocr_pages(file_id, pages)
    tables = [t for p in doc.get("pages") or [] for t in p.get("tables") or []]
    if tables:
        t = tables[0]
        for c, x in enumerate(t[0] if t else []):
            if x and c > 0:
                cols.append({"c": c + 1, "label": str(x)})
        for i, r in enumerate(t[1:], start=2):
            if r and r[0]:
                rows.append({"r": i, "label": str(r[0]).strip()})
    else:
        n = 0
        for p in pages:
            for line in (p.get("text") or "").splitlines():
                line = line.strip()
                if line and len(line) <= 40:
                    n += 1
                    rows.append({"r": n, "label": line})
    return meta, rows[:60], cols[:12]


async def run(sid: str, spt_id: str) -> dict[str, Any]:
    s = await repo.amust("sheets", sid)
    tpl = s.get("template") or {}
    if tpl.get("id") != spt_id:
        return {"sheet_id": sid, "skipped": True}
    meta, trows, tcols = await read_template(tpl["file_id"])
    S.sync_rows(s)        # 생성 전이면 체크된 항목의 행을 먼저 만든다(같은 규칙)
    srows = [{"row_key": r["row_key"], "label_ko": r.get("orig_label") or r["label_ko"], "label_en": " · ".join(r.get("en_lines") or [])}
             for r in S.rows_ordered(s) if not r["row_key"].startswith("template:")]
    payload = {"template_rows": trows, "template_cols": tcols, "rows": srows,
               "products": [{"id": p["id"], "label": p["display_name"]} for p in S.products_ordered(s)]}
    try:
        res = await ai().json("sp.template_map", json.dumps(payload, ensure_ascii=False), MAP_SCHEMA,
                              system="고객사 양식의 행 · 열을 시트 행 · 제품에 맞춘다. 맞는 것이 없으면 null.", confidential=True)
    except Exception as exc:  # noqa: BLE001
        raise ai_error(exc) from exc
    valid_r = {r["r"]: r for r in trows}
    known = {r["row_key"] for r in srows}
    used: set[str] = set()
    mapping: list[dict[str, Any]] = []
    for m in res.get("rows") or []:
        r = valid_r.get(m.get("r"))
        if r is None:
            continue
        rk = m.get("row_key")
        if rk not in known or rk in used:
            rk = None
        if rk:
            used.add(rk)
        mapping.append({"r": r["r"], "label": r["label"], "row_key": rk})
    seen_r = {m["r"] for m in mapping}
    for r in trows:
        if r["r"] not in seen_r:
            mapping.append({"r": r["r"], "label": r["label"], "row_key": None})
    mapping.sort(key=lambda m: m["r"])
    cols = [c for c in res.get("cols") or [] if any(t["c"] == c.get("c") for t in tcols)]

    def fn(x: dict[str, Any]) -> int:
        t = x.get("template") or {}
        if t.get("id") != spt_id:
            return 0
        S.sync_rows(x)
        rows = S.rows_ordered(x)
        by_key = {r["row_key"]: r for r in rows}
        out: list[dict[str, Any]] = []
        for m in mapping:
            if m["row_key"] and m["row_key"] in by_key:
                r = by_key.pop(m["row_key"])
                r["orig_label"] = r.get("orig_label") or r["label_ko"]
                r["label_ko"] = m["label"]
                r["template_r"] = m["r"]
                out.append(r)
            elif not m["row_key"]:
                key = f"template:{m['r']}"
                old = next((r for r in rows if r["row_key"] == key), None)
                nr = old or S.make_row(key, added_by="template", item_key=None, label=m["label"])
                nr["en_lines"] = [m["label"]]
                nr["template_r"] = m["r"]
                out.append(nr)
                for p in S.products_ordered(x):
                    x.setdefault("cells", {}).setdefault(S.ck(nr["id"], p["id"]), {"value": None, "state": "pending", "sources": []})
        for r in rows:
            if r["row_key"] in by_key and not r["row_key"].startswith("template:"):
                r["extra_section"] = True     # 시트에만 있는 행 → 양식 아래 `추가 항목`
                out.append(r)
        for i, r in enumerate(out):
            r["ord"] = i
        x["rows"] = out
        t.update({"status": "done", "mapping": mapping, "cols": cols, "name": meta.get("name") or t.get("name"), "format": (meta.get("kind") or "").upper()})
        x["template"] = t
        S.refresh_status(x, x["id"])
        return len([m for m in mapping if not m["row_key"]])

    saved, n_only = await repo.amutate("sheets", sid, fn)
    await ops.publish(saved)
    return {"sheet_id": sid, "template_id": spt_id, "rows": len(mapping), "template_only": n_only}


def remove(x: dict[str, Any]) -> None:
    """양식 해제 — 양식 행은 빼고 행 이름 · 순서는 원래대로."""
    rows = [r for r in S.rows_ordered(x) if not r["row_key"].startswith("template:")]
    for r in rows:
        if r.get("orig_label"):
            r["label_ko"] = r.pop("orig_label")
        r.pop("template_r", None)
        r.pop("extra_section", None)
    rows.sort(key=lambda r: (0 if r.get("item_key") else 1, r.get("ord", 0)))
    for i, r in enumerate(rows):
        r["ord"] = i
    ids = {r["id"] for r in rows}
    x["cells"] = {k: v for k, v in (x.get("cells") or {}).items() if k.split("|")[0] in ids}
    x["checks"] = [c for c in x.get("checks") or [] if not c.get("row_id") or c["row_id"] in ids]
    x["rows"] = rows
    x["template"] = None


def new_template(file_id: str, name: str) -> dict[str, Any]:
    return {"id": new_id("spt"), "file_id": file_id, "name": name, "format": None, "mapping": [], "status": "queued"}
