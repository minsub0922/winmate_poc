"""mi.revise (§7.9) — load_base → interpret → (targeted_gather + apply_ops) → diff(scope 강제) → save_proposal.

- 변경 안은 바로 반영하지 않는다. 변경(change)마다 화면 표시(before/after)와 적용용 묶음(payload: 칸 · 강점 · 주장 · 인용 · 출처)을 둔다.
- 라운드를 더하면 이전 안 상태(되돌리지 않은 변경) 위에서 다시 돌고, 변경 목록은 늘 기준 버전 대비 누적 차이다.
- `apply_changes` 는 기준 버전 + 되돌리지 않은 변경 → 새 버전 문서(적용 · 미리 보기 공용). 범위 밖 블록 · 주장 · 출처는 건드리지 않는다(AC-MI-52).
"""
from __future__ import annotations

import copy
import logging
import re
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.ids import now_iso
from winmate_common.jobs import JobCanceled, JobContext, current_job

from .. import aix, anonymize, claims as C, kbx, prompts, verify
from .. import store as R
from ..store import nid
from .common import Budget, evidence, ingest_claim, init_web, kb_search_evidence, known_names, memo_log, sensitive_texts, table_text, web_gather

log = logging.getLogger("winmate.mi.revise")

STEP_LABELS = {"load_base": "준비", "interpret": "요청 해석", "gather_apply": "다시 분석", "save_proposal": "변경 안 정리"}


# ── 적용(apply_changes) ──────────────────────────────────
def _table(v: dict[str, Any]) -> dict[str, Any]:
    cp = v.setdefault("document", {}).setdefault("competitor", {"table": {}, "strengths": [], "samsung_products": []})
    t = cp.setdefault("table", {})
    t.setdefault("criteria", [])
    t.setdefault("columns", [])
    t.setdefault("cells", {})
    t.setdefault("criteria_names", {})
    return t


def _merge(v: dict[str, Any], p: dict[str, Any]) -> list[str]:
    srcs = v.setdefault("sources", {})
    for sid, s in (p.get("sources") or {}).items():
        if sid not in srcs:
            srcs[sid] = copy.deepcopy(s)
    for cid, cl in (p.get("claims") or {}).items():
        v.setdefault("claims", {})[cid] = copy.deepcopy(cl)
    have = {(c.get("claim_id"), c.get("source_id"), c.get("quote")) for c in v.get("citations") or []}
    for c in p.get("citations") or []:
        key = (c.get("claim_id"), c.get("source_id"), c.get("quote"))
        if key not in have:
            v.setdefault("citations", []).append(copy.deepcopy(c))
            have.add(key)
    return list((p.get("claims") or {}).keys())


def _remove_claims(v: dict[str, Any], cids: list[str]) -> None:
    ids = set(cids or [])
    if not ids:
        return
    affected = {c["source_id"] for c in v.get("citations") or [] if c.get("claim_id") in ids}
    v["claims"] = {k: x for k, x in (v.get("claims") or {}).items() if k not in ids}
    v["citations"] = [c for c in v.get("citations") or [] if c.get("claim_id") not in ids]
    live = {c["source_id"] for c in v.get("citations") or [] if not c.get("dropped")}
    for sid in affected - live:
        s = (v.get("sources") or {}).get(sid)
        if s and s.get("kind") != "user":
            s["state"] = "excluded"
            s["excluded_reason"] = "irrelevant"


def _apply_one(v: dict[str, Any], ch: dict[str, Any]) -> list[str]:
    kind = ch.get("kind")
    t = ch.get("target") or {}
    p = ch.get("payload") or {}
    touched: list[str] = []
    if kind == "row_add":
        table = _table(v)
        crt = t["criterion_id"]
        if crt not in table["criteria"]:
            table["criteria"].append(crt)
        table["cells"][crt] = copy.deepcopy(p.get("cells") or {})
        table["criteria_names"][crt] = (p.get("criterion") or {}).get("name", "")
        touched += _merge(v, p)
    elif kind == "row_remove":
        table = _table(v)
        if t.get("criterion_id"):
            crt = t["criterion_id"]
            row = table["cells"].pop(crt, {}) or {}
            table["criteria"] = [c for c in table["criteria"] if c != crt]
            _remove_claims(v, [cid for cell in row.values() for cid in cell.get("claim_ids") or []])
        elif t.get("column"):
            col = t["column"]
            table["columns"] = [c for c in table["columns"] if c != col]
            gone: list[str] = []
            for row in table["cells"].values():
                cell = row.pop(col, None)
                if cell:
                    gone += cell.get("claim_ids") or []
            _remove_claims(v, gone)
    elif kind == "value_edit":
        if t.get("crt"):
            table = _table(v)
            row = table["cells"].setdefault(t["crt"], {})
            old = row.get(t["col"]) or {}
            _remove_claims(v, old.get("claim_ids") or [])
            row[t["col"]] = copy.deepcopy(p.get("cell") or {"text": "[확인 필요]", "claim_ids": [], "placeholder": True})
            touched += _merge(v, p)
        elif t.get("claim_id"):
            _remove_claims(v, [t["claim_id"]])
            touched += _merge(v, p)
    elif kind == "strength_edit":
        cp = v.setdefault("document", {}).setdefault("competitor", {"table": {}, "strengths": [], "samsung_products": []})
        strengths = cp.setdefault("strengths", [])
        idx = next((i for i, s in enumerate(strengths) if s.get("id") == t.get("strength_id")), None)
        new = copy.deepcopy(p.get("strength") or {})
        if idx is None:
            if new:
                strengths.append(new)
        else:
            old = strengths[idx]
            keep = set(new.get("claim_ids") or [])
            _remove_claims(v, [c for c in old.get("claim_ids") or [] if c not in keep and str((v.get("claims") or {}).get(c, {}).get("block_path", "")).startswith("strengths")])
            if new:
                strengths[idx] = new
            else:
                strengths.pop(idx)
        touched += _merge(v, p)
    elif kind == "text_edit":
        cid = t.get("claim_id")
        if cid and cid in (v.get("claims") or {}):
            v["claims"][cid] = {**v["claims"][cid], **copy.deepcopy((p.get("claim") or {}))}
            if p.get("citations") is not None:
                v["citations"] = [c for c in v.get("citations") or [] if c.get("claim_id") != cid]
                touched += _merge(v, {"citations": p["citations"], "sources": p.get("sources") or {}})
            touched.append(cid)
    elif kind == "source_add":
        cid = t.get("claim_id")
        touched += _merge(v, p)
        if cid:
            touched.append(cid)
    return touched


def apply_changes(doc: dict[str, Any], base: dict[str, Any], rev: dict[str, Any], *, only_live: bool = True) -> dict[str, Any]:
    """기준 버전 + (되돌리지 않은) 변경 → 새 버전 문서. 손댄 주장만 상태를 다시 모은다."""
    v = copy.deepcopy(base)
    v.pop("n", None)
    touched: list[str] = []
    for ch in rev.get("changes") or []:
        if only_live and ch.get("reverted"):
            continue
        touched += _apply_one(v, ch)
    for cid in dict.fromkeys(touched):
        if cid in (v.get("claims") or {}):
            C.recompute(v, cid)
    return v


# ── 그래프 ───────────────────────────────────────────────
class ReviseState(TypedDict, total=False):
    analysis_id: str
    revision_id: str
    ops: list[dict[str, Any]]
    quick: str | None
    t0: float


async def _load(aid: str, rev_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    doc = await R.call(R.get_analysis, aid)
    rev = await R.call(R.get_doc, R.REV, rev_id)
    if doc is None or rev is None:
        raise ApiError(404, "NOT_FOUND", "재분석 안을 찾을 수 없어요", {"revision_id": rev_id})
    base = await R.call(R.get_version, aid, int(rev.get("base_version") or 0))
    if base is None:
        raise ApiError(404, "NOT_FOUND", "기준 버전을 찾을 수 없어요", {"version": rev.get("base_version")})
    return doc, rev, base


async def load_base(state: ReviseState) -> dict[str, Any]:
    await R.call(R.update_doc, R.REV, state["revision_id"], lambda r: r.update(status="running", error=None))
    return {"t0": time.time()}


def _crit_by_name(doc: dict[str, Any], table: dict[str, Any], name: str) -> str | None:
    names = {**{c["id"]: c["name"] for c in doc.get("criteria") or []}, **(table.get("criteria_names") or {})}
    n = verify.N(name or "")
    if not n:
        return None
    for cid in table.get("criteria") or []:
        nm = verify.N(names.get(cid, ""))
        if nm and (nm in n or n in nm):
            return cid
    toks = set(re.findall(r"[가-힣A-Za-z0-9]{2,}", n))
    best, score = None, 0
    for cid in table.get("criteria") or []:
        t2 = set(re.findall(r"[가-힣A-Za-z0-9]{2,}", verify.N(names.get(cid, ""))))
        s = len(toks & t2)
        if s > score:
            best, score = cid, s
    return best


def _comp_by_target(doc: dict[str, Any], target: str) -> dict[str, Any] | None:
    m = re.search(r"경쟁사\s*([A-Z]{1,2})\b", target or "")
    for c in anonymize.live(doc.get("competitors") or []):
        if m and c.get("letter") == m.group(1):
            return c
        if c.get("real_name") and verify.N(c["real_name"]) in verify.N(target or ""):
            return c
    return None


def _rule_ops(instruction: str) -> list[dict[str, Any]]:
    """LLM 이 안 될 때 요청 문장에서 작업을 읽는 규칙(대표 표현만)."""
    ops: list[dict[str, Any]] = []
    for part in re.split(r"[,，]|\s그리고\s|하고\s|고,", instruction):
        p = part.strip()
        if not p:
            continue
        m = re.search(r"(경쟁사\s*[A-Z])\s*(?:를|을)?\s*빼", p)
        if m:
            ops.append({"op": "remove_competitor", "target": m.group(1), "detail": ""})
            continue
        if "간결" in p or "짧게" in p:
            ops.append({"op": "shorten", "target": "", "detail": p})
            continue
        if "사내 스펙" in p:
            m2 = re.match(r"(.+?)(?:은|는)\s*사내 스펙", p)
            ops.append({"op": "use_internal_spec", "target": (m2.group(1) if m2 else p).strip(), "detail": "사내 스펙 기준"})
            continue
        m3 = re.search(r"(?:비교에\s*)?(.+?)(?:를|을)\s*(?:넣|추가)", p)
        if m3:
            ops.append({"op": "add_row", "target": re.sub(r"^.*비교에\s*", "", m3.group(1)).strip(), "detail": ""})
            continue
        if "출처" in p and ("찾" in p or "채워" in p):
            ops.append({"op": "research_claim", "target": p, "detail": ""})
            continue
        ops.append({"op": "edit_text", "target": "", "detail": p})
    return ops


async def interpret(state: ReviseState) -> dict[str, Any]:
    doc, rev, base = await _load(state["analysis_id"], state["revision_id"])
    rnd = (rev.get("rounds") or [{}])[-1]
    instruction = rnd.get("instruction") or ""
    scope = rev.get("scope") or {}
    if scope.get("kind") == "claims":
        return {"ops": [{"op": "research_claim", "target": cid, "detail": instruction} for cid in scope.get("ids") or []], "quick": None}
    cur = apply_changes(doc, base, rev)
    ops: list[dict[str, Any]] = []
    quick = None
    try:
        res = await aix.llm("mi.revise_interpret", prompts.revise_interpret(instruction, scope, table_text(doc, cur)), prompts.Interpret, confidential=True)
        ops = [o.model_dump() for o in res.operations]
        quick = res.quick_suggestion
    except (aix.LLMFailed, ApiError) as exc:
        log.info("재분석 해석 LLM 실패 → 규칙: %s", exc)
    if not ops:
        ops = _rule_ops(instruction)
    if scope.get("kind") == "strengths":
        ops = [o for o in ops if o["op"] in ("edit_strength", "shorten")] or [{"op": "edit_strength", "target": "", "detail": instruction}]
    return {"ops": ops, "quick": quick}


def _keys(v: dict[str, Any]) -> tuple[set[str], int, set[str]]:
    return set((v.get("claims") or {}).keys()), len(v.get("citations") or []), set((v.get("sources") or {}).keys())


def _payload(v: dict[str, Any], before: tuple[set[str], int, set[str]], cids: list[str]) -> dict[str, Any]:
    """새로 만든 주장(cids) · 그 인용 · 새 출처만 묶는다."""
    ids = set(cids)
    cl = {k: copy.deepcopy(x) for k, x in (v.get("claims") or {}).items() if k in ids}
    cits = [copy.deepcopy(c) for c in (v.get("citations") or [])[before[1]:] if c.get("claim_id") in ids]
    sids = {c["source_id"] for c in cits}
    srcs = {k: copy.deepcopy(x) for k, x in (v.get("sources") or {}).items() if k in sids and k not in before[2]}
    return {"claims": cl, "citations": cits, "sources": srcs}


async def gather_apply(state: ReviseState) -> dict[str, Any]:
    from .analyze import Refs, comp_cell, samsung_cell, spec_row_for, _gather_samsung  # noqa: F401 — 같은 규칙(§7.7)

    ctx = current_job()
    aid, rev_id = state["analysis_id"], state["revision_id"]
    doc, rev, base = await _load(aid, rev_id)
    memos: list[str] = []
    await memo_log(ctx, memos)
    scope = rev.get("scope") or {}
    cur = apply_changes(doc, base, rev)
    budget = Budget(websearch=8, fetch=10, llm=16)
    await init_web(budget)
    sens = sensitive_texts(doc)
    known = known_names(doc)
    table = (((cur.get("document") or {}).get("competitor") or {}).get("table") or {})
    comps = {c["id"]: c for c in anonymize.live(doc.get("competitors") or [])}
    names = {**{c["id"]: c["name"] for c in doc.get("criteria") or []}, **(table.get("criteria_names") or {})}
    changes: list[dict[str, Any]] = []
    missing: list[str] = []
    rnd = len(rev.get("rounds") or [])
    samsung: dict[str, Any] | None = None

    async def samsung_side() -> dict[str, Any]:
        nonlocal samsung
        if samsung is None:
            ev0: list[dict[str, Any]] = []
            scratch = copy.deepcopy(cur)
            samsung = await _gather_samsung(doc, scratch, ev0, _NullTracker())
            samsung["_ev"] = ev0
            samsung["_scratch"] = scratch
        return samsung

    for op in state.get("ops") or []:
        kind = op.get("op")
        target = op.get("target") or ""
        if kind == "add_row":
            name = re.sub(r"\s+", " ", target).strip()[:24]
            if not name or _crit_by_name(doc, table, name) and verify.N(names.get(_crit_by_name(doc, table, name) or "", "")) == verify.N(name):
                continue
            crt = {"id": nid("crt"), "name": name, "source": "user", "weight": 3, "order": len(doc.get("criteria") or []), "enabled": True, "pinned": True}
            before = _keys(cur)
            ev: list[dict[str, Any]] = []
            for col in table.get("columns") or []:
                c = comps.get(col)
                if not c:
                    continue
                await web_gather(cur, ev, budget, None, task="mi.web_revise", query=f"{c['real_name']} {name}", area="competitor", sensitive=sens,
                                 competitor_id=col)
            sm = await samsung_side()
            sm_ev = sm["_ev"]
            # 삼성 칸은 KB 에서만 — 이 기준으로 메시지까지 다시
            msgs = [x for x in await kbx.messages(name, limit=3) if float(x.get("score") or 0) >= 0.45][:1]
            sam = {"spec": sm.get("spec"), "messages": {}}
            all_ev = ev + sm_ev
            for mm in msgs:
                from .common import add_source

                sid = add_source(cur, {"kind": "kb_official", "subtype": "메시지", "title": f"삼성 메시지 · {mm.get('about_name') or name}", "publisher": "samsung.com",
                                       "url": None, "published_at": None, "published_basis": "kb", "retrieved_at": now_iso(), "authority": 2,
                                       "classification": "public", "state": "used", "mode": "kb", "areas": ["competitor"], "kb_key": f"msg:{mm.get('id')}",
                                       "tier": "T2", "claim_flag": int(mm.get("claim_flag") or 0)})
                e = evidence(all_ev, source_id=sid, kind="kb_official", title="삼성 메시지", text=mm.get("text") or "")
                sam["messages"].setdefault(crt["id"], []).append({"text": mm.get("text") or "", "evidence_id": e["id"]})
            if sm.get("spec"):
                for sid, s in sm["_scratch"].get("sources", {}).items():
                    if s.get("kb_key", "").startswith("spec:") and sid not in cur.get("sources", {}):
                        cur["sources"][sid] = copy.deepcopy(s)
                spec_e = next((e for e in sm_ev if e["id"] == sm["spec"]["evidence_id"]), None)
                if spec_e:
                    e2 = evidence(all_ev, source_id=spec_e["source_id"], kind="kb_official", title=spec_e["title"], text=spec_e["text"], label="사내 스펙")
                    sam["spec"] = {**sm["spec"], "evidence_id": e2["id"]}
            cells: dict[str, Any] = {"samsung": samsung_cell(cur, all_ev, sam, crt, known)}
            live_cols = [c for c in table.get("columns") or [] if c in comps]
            if live_cols and budget.take("llm"):
                try:
                    res = await aix.llm("mi.compare_cells", prompts.compare_cells([crt], [comps[c] for c in live_cols], [e for e in all_ev if e["kind"] in ("web", "websearch_summary", "file")], memos),
                                        prompts.Cells, confidential=True)
                    refs = Refs([crt], [comps[c] for c in live_cols])
                    for cell in res.cells:
                        cc, pc = refs.crit(cell.criterion_id), refs.comp(cell.competitor_id)
                        if cc == crt["id"] and pc in live_cols and pc not in cells:
                            cell.criterion_id, cell.competitor_id = cc, pc
                            cells[pc] = comp_cell(cur, all_ev, cell, known)
                except (aix.LLMFailed, ApiError) as exc:
                    log.info("새 행 칸 LLM 실패: %s", exc)
            for col in live_cols:
                cells.setdefault(col, {"text": "[확인 필요]", "claim_ids": [], "placeholder": True})
                if cells[col].get("placeholder") and not cells[col].get("claim_ids"):
                    missing.append(f"{anonymize.workspace_label(comps[col])} {name}")
            cids = [cid for cell in cells.values() for cid in cell.get("claim_ids") or []]
            payload = _payload(cur, before, cids)
            payload.update(cells=cells, criterion=crt)
            changes.append({"kind": "row_add", "area": "competitor", "target": {"criterion_id": crt["id"]}, "before": None,
                            "after": {"name": name, "cells": {k: x.get("text", "") for k, x in cells.items()}}, "claim_ids": cids, "payload": payload})
        elif kind == "remove_row":
            crt = _crit_by_name(doc, table, target)
            if crt:
                changes.append({"kind": "row_remove", "area": "competitor", "target": {"criterion_id": crt}, "before": {"name": names.get(crt, "")},
                                "after": None, "claim_ids": [], "payload": {}})
        elif kind == "remove_competitor":
            c = _comp_by_target(doc, target)
            if c and c["id"] in (table.get("columns") or []):
                changes.append({"kind": "row_remove", "area": "competitor", "target": {"column": c["id"]}, "before": {"label": anonymize.workspace_label(c)},
                                "after": None, "claim_ids": [], "payload": {}})
        elif kind in ("use_internal_spec", "edit_cell"):
            crt = _crit_by_name(doc, table, target)
            if not crt:
                continue
            c = _comp_by_target(doc, target + " " + (op.get("detail") or ""))
            col = c["id"] if (c and kind == "edit_cell" and "사내 스펙" not in (op.get("detail") or "")) else "samsung"
            old = ((table.get("cells") or {}).get(crt) or {}).get(col) or {}
            before = _keys(cur)
            if col == "samsung":
                sm = await samsung_side()
                sam_ev = list(sm["_ev"])
                for sid, s in sm["_scratch"].get("sources", {}).items():
                    if sid not in cur.get("sources", {}):
                        cur["sources"][sid] = copy.deepcopy(s)
                cell = samsung_cell(cur, sam_ev, {"spec": sm.get("spec"), "messages": sm.get("messages") or {}}, {"id": crt, "name": names.get(crt, "")}, known)
            else:
                ev = []
                await web_gather(cur, ev, budget, None, task="mi.web_revise", query=f"{c['real_name']} {names.get(crt, '')}", area="competitor",
                                 sensitive=sens, competitor_id=col)
                cell = {"text": "[확인 필요]", "claim_ids": [], "placeholder": True}
                if ev and budget.take("llm"):
                    try:
                        res = await aix.llm("mi.compare_cells", prompts.compare_cells([{"id": crt, "name": names.get(crt, "")}], [c], ev, memos), prompts.Cells,
                                            confidential=True)
                        refs = Refs([{"id": crt, "name": names.get(crt, "")}], [c])
                        hit = next((x for x in res.cells if refs.crit(x.criterion_id) == crt and refs.comp(x.competitor_id) == col), None)
                        if hit:
                            hit.criterion_id, hit.competitor_id = crt, col
                            cell = comp_cell(cur, ev, hit, known)
                    except (aix.LLMFailed, ApiError):
                        pass
                if cell.get("placeholder") and not cell.get("claim_ids"):
                    missing.append(f"{anonymize.workspace_label(c)} {names.get(crt, '')}")
            if verify.N(cell.get("text", "")) == verify.N(old.get("text", "")):
                continue
            cell["verdict"] = old.get("verdict")
            payload = _payload(cur, before, cell.get("claim_ids") or [])
            payload["cell"] = cell
            changes.append({"kind": "value_edit", "area": "competitor", "target": {"crt": crt, "col": col}, "before": old.get("text", ""),
                            "after": cell.get("text", ""), "claim_ids": cell.get("claim_ids") or [], "payload": payload})
        elif kind in ("edit_strength", "shorten") and (scope.get("kind") in ("strengths", "rows") or scope.get("area") == "competitor"):
            cp = (cur.get("document") or {}).get("competitor") or {}
            olds = cp.get("strengths") or []
            if not olds:
                continue
            ev = _ev_for(cur, "competitor")
            picked = [{"criterion_id": (s.get("criterion_ids") or [""])[0], "name": names.get((s.get("criterion_ids") or [""])[0], ""), "title": s.get("title"),
                       "note": s.get("note")} for s in olds]
            if not budget.take("llm"):
                continue
            try:
                txt = table_text(doc, cur) + f"\n\n요청: {op.get('detail') or target or '더 간결하게'}"
                res = await aix.llm("mi.strengths", prompts.strengths(picked, txt, [e for e in ev if e["kind"] in ("kb_case", "kb_official")]),
                                    prompts.Strengths, confidential=True)
            except (aix.LLMFailed, ApiError):
                continue
            for s in res.strengths:
                old = next((o for o in olds if s.criterion_id in (o.get("criterion_ids") or [])), None)
                if old is None:
                    continue
                before = _keys(cur)
                cid = ingest_claim(cur, area="competitor", text=(s.note or "").strip()[:60] or "[확인 필요]", citations=[x.model_dump() for x in s.citations],
                                   ev_list=ev, block_path="strengths.r", known_names=known)
                note = cur["claims"][cid]["text"]
                title = (s.title or old.get("title") or "")[:12]
                if verify.N(note) == verify.N(old.get("note", "")) and verify.N(title) == verify.N(old.get("title", "")):
                    continue
                if not C.citations_of(cur, cid) and old.get("claim_ids"):
                    # 근거를 못 단 새 문장은 옛 근거 주장을 그대로 쓴다(문장만 짧게)
                    cur["claims"].pop(cid, None)
                    note = old.get("note", "") if any(n.kind != "year" for n in verify.parse_numbers(s.note or "")) else (s.note or "").strip()[:40]
                    new = {**old, "title": title, "note": note}
                    payload = {"strength": new, "claims": {}, "citations": [], "sources": {}}
                    cids: list[str] = list(old.get("claim_ids") or [])
                else:
                    new = {**old, "title": title, "note": note, "claim_ids": [cid]}
                    payload = _payload(cur, before, [cid])
                    payload["strength"] = new
                    cids = [cid]
                changes.append({"kind": "strength_edit", "area": "competitor", "target": {"strength_id": old.get("id")},
                                "before": {"title": old.get("title"), "note": old.get("note")}, "after": {"title": new["title"], "note": new["note"]},
                                "claim_ids": cids, "payload": payload})
        elif kind in ("shorten", "edit_text"):
            area = scope.get("area") if scope.get("kind") == "area" else None
            if not area or area == "competitor":
                continue
            items = [{"id": cid, "text": c.get("text", "")} for cid, c in (cur.get("claims") or {}).items() if c.get("area") == area][:20]
            if not items or not budget.take("llm"):
                continue
            try:
                res = await aix.llm("mi.revise_apply", prompts.revise_apply(op.get("detail") or "더 간결하게", items), prompts.Rewrites, confidential=True)
            except (aix.LLMFailed, ApiError):
                continue
            for it in res.items:
                old = (cur.get("claims") or {}).get(it.claim_id)
                if not old or not it.text.strip() or verify.N(it.text) == verify.N(old.get("text", "")):
                    continue
                cits = C.citations_of(cur, it.claim_id)
                masked, bad = verify.mask_unsupported(it.text.strip(), cits) if cits else verify.mask_unsupported(it.text.strip(), [])
                if old.get("status") == "confirmed":
                    masked = it.text.strip()
                new = {"text": masked, "numbers": [verify.num_to_dict(n) for n in verify.parse_numbers(masked)]}
                changes.append({"kind": "text_edit", "area": area, "target": {"claim_id": it.claim_id}, "before": old.get("text", ""), "after": masked,
                                "claim_ids": [it.claim_id], "payload": {"claim": new}})
        elif kind == "research_claim":
            cid = target if target in (cur.get("claims") or {}) else None
            if cid is None:
                continue
            cl = cur["claims"][cid]
            q = re.sub(r"\[[^\]]*\]|\d[\d,\.]*\s*(?:만|억|조)?\s*(?:%|원|억 원|곳|개|명)?", " ", cl.get("text", ""))
            q = re.sub(r"\s+", " ", q).strip()[:60]
            ev: list[dict[str, Any]] = []
            before = _keys(cur)
            await web_gather(cur, ev, budget, None, task="mi.web_revise", query=q, area=cl.get("area", "market"), sensitive=sens)
            await kb_search_evidence(cur, ev, None, text=q, area=cl.get("area", "market"), k=2)
            if not ev or not budget.take("llm"):
                missing.append(cl.get("metric_label") or cl.get("text", "")[:20])
                continue
            try:
                res = await aix.llm("mi.research_claim", prompts.research_claim(cl.get("text", ""), ev), prompts.ClaimCites, confidential=True)
            except (aix.LLMFailed, ApiError):
                continue
            scratch = copy.deepcopy(cur)
            tmp = ingest_claim(scratch, area=cl.get("area", "market"), text=cl.get("text", ""), citations=[x.model_dump() for x in res.citations], ev_list=ev,
                               block_path=cl.get("block_path", ""), metric_key=cl.get("metric_key"), known_names=known, claim_id=cid + "_tmp")
            new_cits = [{**c, "claim_id": cid} for c in C.citations_of(scratch, tmp)]
            if not new_cits:
                missing.append(cl.get("metric_label") or cl.get("text", "")[:20])
                continue
            sids = {c["source_id"] for c in new_cits}
            srcs = {k: copy.deepcopy(x) for k, x in (scratch.get("sources") or {}).items() if k in sids and k not in before[2]}
            changes.append({"kind": "source_add", "area": cl.get("area", "market"), "target": {"claim_id": cid}, "before": None,
                            "after": {"sources": len(new_cits)}, "claim_ids": [cid], "payload": {"citations": new_cits, "sources": srcs, "claims": {}}})
    # 범위 강제(diff) — 범위 밖 변경은 버린다
    changes = [c for c in changes if _in_scope(c, scope, cur)]
    prev = [c for c in rev.get("changes") or []]
    merged: list[dict[str, Any]] = []
    for c in prev:
        if any(_same_target(c, n) for n in changes):
            continue
        merged.append(c)
    for c in changes:
        old = next((p for p in prev if _same_target(p, c)), None)
        c["id"] = (old or {}).get("id") or nid("chg")
        if old is not None and old.get("before") is not None:
            c["before"] = old["before"]
        c["round"] = rnd
        c["reverted"] = False
        merged.append(c)
    live = [c for c in merged if not c.get("reverted")]
    sources_added = len({sid for c in live for sid in ((c.get("payload") or {}).get("sources") or {})})
    quick = ["더 간결하게"]
    q2 = state.get("quick")
    preview = apply_changes(doc, base, {"changes": merged})
    if not q2:
        ptable = (((preview.get("document") or {}).get("competitor") or {}).get("table") or {})
        worst = None
        best_n = 0
        for col in ptable.get("columns") or []:
            if col == "samsung" or col not in comps:
                continue
            n = sum(1 for row in (ptable.get("cells") or {}).values() if (row.get(col) or {}).get("placeholder"))
            if n > best_n:
                worst, best_n = col, n
        if worst:
            q2 = f"{anonymize.workspace_label(comps[worst])} 빼기"
    if q2 and q2 not in quick:
        quick.append(anonymize.scrub(q2, doc.get("competitors") or [], {}))
    dur = int(time.time() - float(state.get("t0") or time.time()))

    def upd(r: dict[str, Any]) -> None:
        r["changes"] = merged
        r["status"] = "proposed"
        r["duration_s"] = int(r.get("duration_s") or 0) + max(1, dur)
        r["sources_added"] = sources_added
        r["quick_suggestions"] = quick
        r["missing_sources"] = list(dict.fromkeys(missing))[:3]

    await R.call(R.update_doc, R.REV, rev_id, upd)
    return {}


class _NullTracker:
    """진행 화면이 없는 잡(재분석 · 레이아웃)에서 RunTracker 자리."""

    def add_source(self, *a: Any, **k: Any) -> None:
        return None

    def set_counts(self, *a: Any, **k: Any) -> None:
        return None


def _ev_for(v: dict[str, Any], area: str) -> list[dict[str, Any]]:
    from .analyze import _evidence_from_version

    return _evidence_from_version(v, area)


def _same_target(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return a.get("kind") == b.get("kind") and a.get("target") == b.get("target")


def _in_scope(ch: dict[str, Any], scope: dict[str, Any], cur: dict[str, Any]) -> bool:
    k = scope.get("kind")
    claims = cur.get("claims") or {}
    if k == "area":
        if ch.get("area") != scope.get("area"):
            return False
        return True
    if k == "rows":
        ids = set(scope.get("ids") or [])
        t = ch.get("target") or {}
        if ch["kind"] == "value_edit":
            return t.get("crt") in ids
        if ch["kind"] == "row_remove":
            return t.get("criterion_id") in ids
        if ch["kind"] in ("source_add", "text_edit"):
            cell = (claims.get(t.get("claim_id") or "") or {}).get("cell") or {}
            return cell.get("crt") in ids
        return False
    if k == "strengths":
        return ch["kind"] == "strength_edit"
    if k == "claims":
        return ch["kind"] in ("source_add", "text_edit") and (ch.get("target") or {}).get("claim_id") in set(scope.get("ids") or [])
    return False


async def save_proposal(state: ReviseState) -> dict[str, Any]:
    from .. import service as S

    doc = await R.call(R.get_analysis, state["analysis_id"])
    if doc:
        await S.register(doc)
    return {}


def build() -> StateGraph:
    g = StateGraph(ReviseState)
    g.add_node("load_base", load_base)
    g.add_node("interpret", interpret)
    g.add_node("gather_apply", gather_apply)
    g.add_node("save_proposal", save_proposal)
    g.add_edge(START, "load_base")
    g.add_edge("load_base", "interpret")
    g.add_edge("interpret", "gather_apply")
    g.add_edge("gather_apply", "save_proposal")
    g.add_edge("save_proposal", END)
    return g


async def handle(ctx: JobContext) -> dict[str, Any] | None:
    aid, rev_id = ctx.payload["analysis_id"], ctx.payload["revision_id"]
    try:
        await run_graph(ctx, build(), {"analysis_id": aid, "revision_id": rev_id}, step_labels=STEP_LABELS,
                        progress_map={"load_base": 10, "interpret": 30, "gather_apply": 90, "save_proposal": 100})
    except JobCanceled:
        await R.call(R.update_doc, R.REV, rev_id, lambda r: r.update(status="proposed" if r.get("changes") else "discarded"))
        raise
    except Exception as exc:
        err = {"code": str(getattr(exc, "code", type(exc).__name__)), "message": str(getattr(exc, "message", exc))[:300]}
        await R.call(R.update_doc, R.REV, rev_id, lambda r: r.update(status="failed", error=err))
        raise
    rev = await R.call(R.get_doc, R.REV, rev_id) or {}
    return {"analysis_id": aid, "revision_id": rev_id, "changes": len([c for c in rev.get("changes") or [] if not c.get("reverted")])}
