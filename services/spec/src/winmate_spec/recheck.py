"""재확인(06-spec §3.8 · §4.17.4 · §7.7 `spec_recheck`) — 시트 값은 바꾸지 않고 경고만 만든다."""
from __future__ import annotations

import logging
from typing import Any

from . import config, ops, repo
from . import sheet as S
from .catalog import catalog
from .generate import lifecycle_warnings, merge_warnings, requirement_warnings
from .rules import warnings as W
from .rules.values import Fmt, catalog_candidate, render_text

log = logging.getLogger("winmate.spec.recheck")


async def detect_catalog_change() -> dict[str, Any]:
    """카탈로그 버전 감지(catalog_state). 바뀌었으면 previous_version · detected_at 를 남긴다."""
    cat = catalog()
    meta = await cat.meta()
    key = meta.get("adapter") or "kb"
    cur = await repo.aget("catalog_state", key)
    if cur is None:
        cur = await repo.aput("catalog_state", key, {"adapter": key, "version": meta["version"], "label": "사내 카탈로그",
                                                      "detected_at": None, "previous_version": None})
        cur["changed"] = False
        return cur
    if cur.get("version") != meta["version"]:
        cur = await repo.aput("catalog_state", key, {"adapter": key, "version": meta["version"], "label": "사내 카탈로그",
                                                      "detected_at": config.now_iso(), "previous_version": cur.get("version")})
        cur["changed"] = True
        return cur
    cur["changed"] = False
    return cur


async def recheck_sheet(sid: str, *, catalog_diff: bool = True, lifecycle: bool = True, requirements: bool = True) -> int:
    """시트 하나 재확인 → 열린 경고 수."""
    s = await repo.amust("sheets", sid)
    if s.get("archived_at") or not s.get("generated_at"):
        return 0
    cat = catalog()
    ver = await cat.version()
    ps = S.products_ordered(s)
    codes = [p["model_code"] for p in ps if p.get("model_code") and p.get("in_catalog", True)]
    specs = await cat.specs(codes) if codes else {}
    new_changed: list[dict[str, Any]] = []
    lc_updates: dict[str, dict[str, Any]] = {}
    if catalog_diff and ver != (s.get("catalog") or {}).get("version"):
        f = Fmt()
        cells = s.get("cells") or {}
        for r in S.rows_ordered(s):
            if r["row_key"].startswith(("derived:", "template:")):
                continue
            for p in ps:
                c = cells.get(S.ck(r["id"], p["id"])) or {}
                if c.get("state") in ("edited", "derived") or not any(x.get("kind") == "catalog" for x in c.get("sources") or []):
                    continue
                sp = specs.get(p.get("model_code") or "")
                if not sp:
                    continue
                cand = catalog_candidate(r["row_key"], sp, ver)
                new_text = render_text(r["row_key"], cand.value, f, "ko")[0] if cand.value else None
                old_text = c.get("catalog_text") or render_text(r["row_key"], c.get("value"), f, "ko")[0]
                if new_text and new_text != old_text:
                    new_changed.append(W.catalog_changed(r, p, old={"value": c.get("value"), "value_text": old_text, "sources": c.get("sources") or []},
                                                         new={"value": cand.value, "value_text": new_text, "sources": cand.sources},
                                                         new_version=ver))
    if lifecycle:
        for p in ps:
            lc = await ops.evaluate_lifecycle(p, specs.get(p.get("model_code") or ""))
            if lc.get("status") != (p.get("lifecycle") or {}).get("status"):
                rep = await ops.replacement_for(p, lc, s) if lc["status"] in ("discontinued", "eol_planned") else None
                lc_updates[p["id"]] = {"lifecycle": lc, "replacement": rep}
    req_ws = await requirement_warnings(s) if requirements else None

    def fn(x: dict[str, Any]) -> int:
        for p in x.get("products") or []:
            if p["id"] in lc_updates:
                p.update(lc_updates[p["id"]])
        if catalog_diff and new_changed:
            merge_warnings(x, new_changed, kinds={"catalog_changed"}, close_missing=False)
        if lifecycle:
            merge_warnings(x, lifecycle_warnings(x), kinds={"discontinued", "not_in_catalog"})
        if req_ws is not None:
            merge_warnings(x, req_ws, kinds={"requirement_unmet"})
        x["rechecked_at"] = config.now_iso()
        x["recheck_version"] = ver
        S.refresh_status(x, x["id"])
        return len([w for w in x.get("warnings") or [] if w.get("status") in ("open", "decided")])

    saved, n = await repo.amutate("sheets", sid, fn)
    from .links import mark_links_changed
    await mark_links_changed(saved)
    saved = await repo.amust("sheets", sid)
    await ops.publish(saved)
    return n


async def recheck_all(owner: str | None = None) -> dict[str, Any]:
    state = await detect_catalog_change()
    sheets = await repo.alist("sheets", {"owner_id": owner} if owner else None)
    n = 0
    changed = 0
    for s in sheets:
        if s.get("archived_at") or not s.get("generated_at"):
            continue
        n += 1
        await recheck_sheet(s["id"])
        cur = await repo.aget("sheets", s["id"])
        if cur and any(w["kind"] == "catalog_changed" and w.get("status") in ("open", "decided") for w in cur.get("warnings") or []):
            changed += 1
            if state.get("changed"):
                await ops.notify(cur.get("owner_id"), {"type": "spec_catalog_changed", "title": f"사내 카탈로그 갱신 — '{cur.get('title')}' 값 확인 필요",
                                                       "ref": cur["id"], "route": f"/spec/{cur['id']}/warnings"})
    return {"sheets": n, "changed_sheets": changed, "catalog_version": state.get("version"), "detected_at": state.get("detected_at")}
