"""제안서 연결(06-spec §6.10) — 보낸 스냅숏 · 차이 · 상태(in_sync · sheet_changed) · 알림."""
from __future__ import annotations

import logging
from typing import Any

from . import ops, repo
from . import sheet as S
from .rules import warnings as W
from .rules.values import render_text

log = logging.getLogger("winmate.spec.links")


def cell_texts(s: dict[str, Any]) -> dict[str, str]:
    """보이는 칸의 지금 글(한국어 표시 — 비교 기준)."""
    from .rules.values import Fmt
    f = Fmt.of(s.get("format"))
    f.language = "ko"
    out = {}
    cells = s.get("cells") or {}
    for r in S.rows_ordered(s):
        if r.get("hidden"):
            continue
        for p in S.products_ordered(s):
            c = cells.get(S.ck(r["id"], p["id"])) or {}
            out[S.ck(r["id"], p["id"])] = render_text(r["row_key"], c.get("value"), f, "ko")[0] if c.get("state") != "flag" else "[확정 필요]"
    return out


def diff_cells(s: dict[str, Any], link: dict[str, Any]) -> list[dict[str, Any]]:
    sent = link.get("sent_snapshot") or {}
    cur = cell_texts(s)
    rows = {r["id"]: r for r in s.get("rows") or []}
    prods = {p["id"]: p for p in s.get("products") or []}
    out = []
    for key, text in sent.items():
        if key in cur and cur[key] != text:
            rid, pid = key.split("|")
            if rid in rows and pid in prods:
                out.append({"row_label": rows[rid]["label_ko"], "product_label": prods[pid]["display_name"], "sent_text": text,
                            "current_text": cur[key], "row_id": rid, "product_id": pid})
    return out


def links_of(sheet_id: str) -> list[dict[str, Any]]:
    return repo.list_all("links", {"sheet_id": sheet_id})


async def mark_links_changed(s: dict[str, Any]) -> int:
    """버전이 오른 시트의 연결마다 보낸 값과 비교 → 다르면 sheet_changed + `제안서와 다름` 경고 + 알림."""
    links = await repo.run(links_of, s["id"])
    if not links:
        return 0
    new_ws: list[dict[str, Any]] = []
    changed = 0
    for lk in links:
        diffs = diff_cells(s, lk)
        status = "sheet_changed" if diffs else "in_sync"
        if status != lk.get("status"):
            lk["status"] = status
            await repo.aput("links", lk["id"], lk)
            if status == "sheet_changed":
                changed += 1
                await ops.notify(s.get("owner_id"), {"type": "spec_link_changed", "title": f"'{lk.get('proposal_title')}' 제안서의 제품 스펙이 시트와 달라졌어요",
                                                     "ref": s["id"], "route": f"/proposal/{lk.get('proposal_id')}/sections/spec",
                                                     "proposal_id": lk.get("proposal_id")})
        rows = {r["id"]: r for r in s.get("rows") or []}
        prods = {p["id"]: p for p in s.get("products") or []}
        for d in diffs:
            new_ws.append(W.value_mismatch_proposal(rows[d["row_id"]], prods[d["product_id"]], link=lk, sent_text=d["sent_text"],
                                                    current_text=d["current_text"], version=(s.get("catalog") or {}).get("version") or ""))

    from .generate import merge_warnings

    def fn(x: dict[str, Any]) -> None:
        merge_warnings(x, new_ws, kinds={"value_mismatch_proposal"})
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", s["id"], fn)
    if new_ws:
        await ops.publish(saved)
    return changed


def link_item(s: dict[str, Any], lk: dict[str, Any]) -> dict[str, Any]:
    diffs = diff_cells(s, lk)
    w = next((w for w in s.get("warnings") or [] if w.get("link_id") == lk["id"] and w.get("status") in ("open", "decided")), None)
    return {"link_id": lk["id"], "sheet_id": s["id"], "sheet_title": s.get("title") or "", "proposal_id": lk["proposal_id"],
            "sent_version": lk.get("sent_version", 0), "current_version": s.get("doc_version", 0),
            "status": "sheet_changed" if diffs else "in_sync",
            "diff_cells": [{k: d[k] for k in ("row_label", "product_label", "sent_text", "current_text")} for d in diffs],
            "route": f"/spec/{s['id']}/warnings?w={w['id']}" if w else f"/spec/{s['id']}"}
