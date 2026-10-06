"""`spec_revise` — 말로 수정(06-spec §7.5): interpret → validate → resolve → apply → recheck → finish."""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from winmate_common.jobs import current_job, jobs

from .. import config, exporting, generate, ops, repo, revise
from .. import sheet as S
from ..compliance import ai_error
from ..generate import Progress


class ReviseState(TypedDict, total=False):
    sheet_id: str
    text: str
    context: str
    session_id: str | None
    ops: list[dict[str, Any]]
    reply: str | None
    needs_clarification: str | None
    new_product_ids: list[str]
    navigate: str | None
    applied: list[str]
    extra: dict[str, Any]
    result: dict[str, Any]


async def _interpret(state: ReviseState) -> dict[str, Any]:
    s = await repo.amust("sheets", state["sheet_id"])
    try:
        res = await revise.interpret(s, state["text"], context=state.get("context") or "result")
    except Exception as exc:  # noqa: BLE001
        raise ai_error(exc) from exc
    return {"ops": res.get("ops") or [], "reply": res.get("reply"), "needs_clarification": res.get("needs_clarification")}


async def _resolve(state: ReviseState) -> dict[str, Any]:
    """add_product 의 모델 문자열 → KB 해소(검색 · 표시명) · 생애주기 표. 해소 안 되면 직접 입력(점선) 제품."""
    if state.get("context") == "edit":
        return {}
    new_ids: list[str] = []
    products: list[dict[str, Any]] = []
    s = await repo.amust("sheets", state["sheet_id"])
    for op in state.get("ops") or []:
        if op["op"] != "add_product":
            continue
        a = op.get("args") or {}
        q = a.get("query") or a.get("model") or a.get("name")
        role = a.get("role") if a.get("role") in ("proposed", "existing", "alternative") else "proposed"
        p = await ops.resolve_product(q, source="request", role=role)
        if p and not S.has_ref(s, p.get("ref"), p.get("model_code")):
            products.append(p)
            new_ids.append(p["id"])
    if products:
        def fn(x: dict[str, Any]) -> None:
            for p in products:
                p["ord"] = len(x.get("products") or [])
                x.setdefault("products", []).append(p)
            S.recompute_kind(x)

        await repo.amutate("sheets", state["sheet_id"], fn)
    return {"new_product_ids": new_ids}


async def _apply(state: ReviseState) -> dict[str, Any]:
    sid = state["sheet_id"]
    ctx_name = state.get("context") or "result"
    o = state.get("ops") or []
    navigate = None
    extra: dict[str, Any] = {}
    if ctx_name == "edit" and state.get("session_id"):
        from ..edit import add_llm_ops
        applied = await add_llm_ops(sid, state["session_id"], o)
        return {"applied": applied, "navigate": None}
    fmt_ops = [x for x in o if x["op"] == "set_format"]
    if fmt_ops:
        draft = {k: v for x in fmt_ops for k, v in (x.get("args") or {}).items()
                 if k in ("formats", "language", "length_unit", "weight_unit", "paper", "number_format")}
        await repo.amutate("sheets", sid, lambda x: x.update({"format_draft": draft, "user_text": state["text"]}))
        navigate = "SP2L"
    if any(x["op"] == "find_alternatives" for x in o):
        navigate = navigate or "SP1C"
    for x in o:
        if x["op"] == "export_also":
            a = x.get("args") or {}
            fmt = a.get("format") if a.get("format") in ("xlsx", "pdf", "pptx") else "pdf"
            s = await repo.amust("sheets", sid)
            ov = {"language": a.get("language")} if a.get("language") in ("ko", "en", "ko_en") else {}
            rec = exporting.new_record(sid, s.get("doc_version", 0), fmt, {"overrides": ov, "options": None},
                                       exporting.filename_for(s, fmt, None, ov))
            job = await jobs().enqueue("spec", "spec_export", {"sheet_id": sid, "export_id": rec["id"]}, title=f"{rec['filename']} 내보내기", ref=sid)
            rec["job_id"] = job.id
            await repo.aput("exports", rec["id"], rec)
            extra.setdefault("exports", []).append({"export_id": rec["id"], "job_id": job.id, "format": fmt})
    sheet_ops = [x for x in o if x["op"] not in ("add_product", "set_format", "export_also", "find_alternatives")]
    applied: list[str] = []

    def fn(x: dict[str, Any]) -> None:
        nonlocal applied
        generate.backup(x)
        applied = revise.apply_sheet_ops(x, sheet_ops)
        for r in S.rows_ordered(x):
            if r["row_key"] == "derived:annual_energy_cost":
                chk = generate._derive_row(x, r, (r.get("derived") or {}).get("price") or config.electricity_price())
                if chk:
                    chk["n"] = max([c.get("n", 0) for c in x.get("checks") or []] + [0]) + 1
                    x.setdefault("checks", []).append(chk)
        x.pop("gen_backup", None)

    await repo.amutate("sheets", sid, fn)
    new_ids = state.get("new_product_ids") or []
    if new_ids:
        prog = Progress(current_job(), sid)
        await generate.stage_resolve(sid, new_ids, prog)
        await generate.stage_fetch(sid, new_ids, prog)
        await generate.stage_verify(sid, new_ids, False, prog)
        applied.append("add_product")
    if any(x["op"] == "add_rows" for x in sheet_ops):
        s = await repo.amust("sheets", sid)
        new_rows = [r["id"] for r in S.rows_ordered(s) if not any(k.startswith(r["id"] + "|") for k in (s.get("cells") or {}))]
        if new_rows:
            prog = Progress(current_job(), sid)
            await generate.stage_fetch(sid, None, prog, row_ids=new_rows)
            await generate.stage_verify(sid, None, False, prog, row_ids=new_rows)
    return {"applied": applied, "navigate": navigate, "extra": extra}


async def _recheck_finish(state: ReviseState) -> dict[str, Any]:
    sid = state["sheet_id"]
    if state.get("context") == "edit":
        return {"result": {"applied_ops": state.get("applied") or [], "reply": state.get("reply"), "navigate": None,
                           "needs_clarification": state.get("needs_clarification")}}
    s = await repo.amust("sheets", sid)
    req_ws = await generate.requirement_warnings(s) if state.get("new_product_ids") else None
    applied = state.get("applied") or []

    def fn(x: dict[str, Any]) -> int:
        for c in (x.get("cells") or {}).values():
            if c.get("state") == "checking":
                c["state"] = "ok" if c.get("value") else "pending"
            if c.get("state") == "flag":
                c["state"] = "pending"
                c.pop("flag_text", None)
        if state.get("new_product_ids"):
            generate.merge_warnings(x, generate.lifecycle_warnings(x), kinds={"discontinued", "not_in_catalog"})
            if req_ws is not None:
                generate.merge_warnings(x, req_ws, kinds={"requirement_unmet"})
        x.pop("gen", None)
        x["user_text"] = state["text"]
        if applied:
            S.bump_version(x, "request")
        me = current_job()
        if me is None or (x.get("active_job") or {}).get("id") == me.job.id:
            x["active_job"] = None
        S.refresh_status(x, x["id"])
        return len([w for w in x.get("warnings") or [] if w.get("status") in ("open", "decided")])

    saved, n_warn = await repo.amutate("sheets", sid, fn)
    if applied:
        await repo.aput("snapshots", f"{sid}.v{saved['doc_version']}", S.snapshot_of(saved))
    from ..links import mark_links_changed
    await mark_links_changed(saved)
    saved = await repo.amust("sheets", sid)
    await ops.publish(saved)
    navigate = state.get("navigate")
    n_warn = len([w for w in saved.get("warnings") or [] if w.get("status") in ("open", "decided")])
    if state.get("new_product_ids") and n_warn:
        navigate = "SP3W"
    reply = state.get("reply")
    if navigate == "SP3W":
        from ..rules.warnings import agent_text
        ws = S.warning_numbers(saved)
        reply = agent_text(ws, {p["id"]: p for p in saved.get("products") or []})
    return {"result": {"sheet_id": sid, "applied_ops": applied, "reply": reply, "navigate": navigate,
                       "needs_clarification": state.get("needs_clarification") if not applied else None,
                       "version": saved.get("doc_version"), **(state.get("extra") or {})}}


def build_revise() -> StateGraph:
    g = StateGraph(ReviseState)
    g.add_node("g_interpret", _interpret)
    g.add_node("g_resolve", _resolve)
    g.add_node("g_apply", _apply)
    g.add_node("g_finish", _recheck_finish)
    g.add_edge(START, "g_interpret")
    g.add_edge("g_interpret", "g_resolve")
    g.add_edge("g_resolve", "g_apply")
    g.add_edge("g_apply", "g_finish")
    g.add_edge("g_finish", END)
    return g
