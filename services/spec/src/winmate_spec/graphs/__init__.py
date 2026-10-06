"""spec 워크플로(LangGraph, 06-spec §7). 각 그래프는 `winmate_common.graph.run_graph` 로 잡 안에서 돈다(thread_id = job_id).

그래프 상태는 작은 값(시트 id · 모드 · 노드 사이 결과)만 담는다. 큰 중간 결과(칸 후보)는 시트 문서(gen)에 둔다.
`awaiting_input` 은 쓰지 않는다 — 묻는 것은 값 확인 · 경고 · 요구 행 자원으로 남는다(§3.5).
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from winmate_common.jobs import current_job

from .. import compliance as CP
from .. import config, datasheet, exporting, generate, ops, recheck, repo, template
from .. import finder as FS
from .. import sheet as S
from ..generate import Progress


# ── spec_generate ─────────────────────────────────────────

class GenState(TypedDict, total=False):
    sheet_id: str
    mode: str
    product_ids: list[str] | None
    auto_answer: bool
    notes: dict[str, str]
    result: dict[str, Any]


def _prog(state: dict[str, Any]) -> Progress:
    return Progress(current_job(), state["sheet_id"])


async def _resolve(state: GenState) -> dict[str, Any]:
    note = await generate.stage_resolve(state["sheet_id"], state.get("product_ids"), _prog(state))
    await _active_progress(state["sheet_id"], 10)
    return {"notes": {**(state.get("notes") or {}), "resolve_models": note}}


async def _fetch(state: GenState) -> dict[str, Any]:
    note = await generate.stage_fetch(state["sheet_id"], state.get("product_ids"), _prog(state))
    await _active_progress(state["sheet_id"], 40)
    return {"notes": {**(state.get("notes") or {}), "fetch_specs": note}}


async def _verify(state: GenState) -> dict[str, Any]:
    note = await generate.stage_verify(state["sheet_id"], state.get("product_ids"), bool(state.get("auto_answer")), _prog(state))
    await _active_progress(state["sheet_id"], 80)
    return {"notes": {**(state.get("notes") or {}), "verify": note}}


async def _wins(state: GenState) -> dict[str, Any]:
    p = _prog(state)
    s = await repo.amust("sheets", state["sheet_id"])
    single = len(S.compare_products(s)) < 2
    note = "단일 제품 — 건너뜀" if single else "모델 간 차이 비교"
    await p.step("mark_wins", "run", note)
    await p.step("mark_wins", "done", note)
    await p.progress(90, "우위 항목 표시")
    await _active_progress(state["sheet_id"], 90)
    return {"notes": {**(state.get("notes") or {}), "mark_wins": note}}


async def _compose(state: GenState) -> dict[str, Any]:
    res = await generate.stage_compose(state["sheet_id"], state.get("mode") or "full", _prog(state), current_job())
    return {"result": res}


async def _active_progress(sid: str, pct: int) -> None:
    def fn(s: dict[str, Any]) -> None:
        if s.get("active_job"):
            s["active_job"]["progress"] = pct
            s["active_job"]["status"] = "running"

    await repo.amutate("sheets", sid, fn)


def _gen_entry(state: GenState) -> str:
    return "g_compose" if state.get("mode") == "rerender" else "g_resolve"


def build_generate() -> StateGraph:
    g = StateGraph(GenState)
    g.add_node("g_resolve", _resolve)
    g.add_node("g_fetch", _fetch)
    g.add_node("g_verify", _verify)
    g.add_node("g_wins", _wins)
    g.add_node("g_compose", _compose)
    g.add_conditional_edges(START, _gen_entry, {"g_resolve": "g_resolve", "g_compose": "g_compose"})
    g.add_edge("g_resolve", "g_fetch")
    g.add_edge("g_fetch", "g_verify")
    g.add_edge("g_verify", "g_wins")
    g.add_edge("g_wins", "g_compose")
    g.add_edge("g_compose", END)
    return g


# ── spec_find ─────────────────────────────────────────────

class FindState(TypedDict, total=False):
    sheet_id: str
    text: str
    parsed: dict[str, Any]
    linked: dict[str, Any]
    result: dict[str, Any]


async def _f_parse(state: FindState) -> dict[str, Any]:
    ctx = current_job()
    if ctx:
        await ctx.step("parse_text", "run", note="문장을 조건으로 바꾸는 중")
    s = await repo.amust("sheets", state["sheet_id"])
    try:
        parsed = await FS.parse_text(s.get("finder") or FS.empty_state(), state["text"])
    except Exception as exc:  # noqa: BLE001
        raise CP.ai_error(exc) from exc
    return {"parsed": parsed}


async def _f_link(state: FindState) -> dict[str, Any]:
    return {"linked": await FS.link_entities(state["text"])}


async def _f_compute(state: FindState) -> dict[str, Any]:
    ctx = current_job()
    s = await repo.amust("sheets", state["sheet_id"])
    st = FS.merge_conditions(s.get("finder") or FS.empty_state(), state.get("parsed") or {}, state.get("linked") or {}, state["text"])
    if ctx:
        await ctx.step("pool", "run", note="후보 제품군 찾는 중")
    st = await FS.compute(st)

    def fn(x: dict[str, Any]) -> None:
        cur = x.get("finder") or {}
        x["finder"] = {**st, "selected": cur.get("selected") or st.get("selected") or [], "hide_out": cur.get("hide_out", False),
                       "view": cur.get("view", "cards")}
        x["user_text"] = state["text"]
        if not x.get("customer_name") and st.get("customer"):
            x["customer_name"] = st["customer"]
        x["active_job"] = None
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", state["sheet_id"], fn)
    await ops.publish(saved)
    return {"result": {"sheet_id": state["sheet_id"], "candidates": len(st.get("candidates") or [])}}


def build_find() -> StateGraph:
    g = StateGraph(FindState)
    g.add_node("g_parse_text", _f_parse)
    g.add_node("g_link_entities", _f_link)
    g.add_node("g_evaluate", _f_compute)
    g.add_edge(START, "g_parse_text")
    g.add_edge("g_parse_text", "g_link_entities")
    g.add_edge("g_link_entities", "g_evaluate")
    g.add_edge("g_evaluate", END)
    return g


# ── spec_compliance ───────────────────────────────────────

class CompState(TypedDict, total=False):
    sheet_id: str
    doc_id: str
    file_id: str
    note: str | None
    reevaluate: bool
    result: dict[str, Any]


async def _c_run(state: CompState) -> dict[str, Any]:
    ctx = current_job()

    async def prog(stage: str, status: str, note: str) -> None:
        if ctx:
            await ctx.step(stage, status, note=note)
            await ctx.progress(30 if stage == "load_doc" else 70, note)

    res = await CP.run(state["sheet_id"], doc_id=state.get("doc_id"), file_id=state.get("file_id"), note=state.get("note"), prog=prog,
                       reevaluate=bool(state.get("reevaluate")))
    return {"result": res}


def build_compliance() -> StateGraph:
    g = StateGraph(CompState)
    g.add_node("g_compliance", _c_run)
    g.add_edge(START, "g_compliance")
    g.add_edge("g_compliance", END)
    return g


# ── 단순 그래프(데이터시트 · 양식 · 재확인 · 내보내기) ──────────

class SimpleState(TypedDict, total=False):
    sheet_id: str | None
    ref: str | None
    all: bool
    owner: str | None
    result: dict[str, Any]


async def _ds(state: SimpleState) -> dict[str, Any]:
    return {"result": await datasheet.run(state["sheet_id"] or "", state["ref"] or "")}


async def _tpl(state: SimpleState) -> dict[str, Any]:
    return {"result": await template.run(state["sheet_id"] or "", state["ref"] or "")}


async def _recheck(state: SimpleState) -> dict[str, Any]:
    if state.get("all"):
        res = await recheck.recheck_all(state.get("owner"))
        return {"result": res}
    n = await recheck.recheck_sheet(state["sheet_id"] or "")

    def fn(x: dict[str, Any]) -> None:
        if (x.get("active_job") or {}).get("kind") == "spec_recheck":
            x["active_job"] = None
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", state["sheet_id"] or "", fn)
    await ops.publish(saved)
    return {"result": {"sheet_id": state["sheet_id"], "open_warnings": n}}


async def _export(state: SimpleState) -> dict[str, Any]:
    return {"result": await exporting.run(state["sheet_id"] or "", state["ref"] or "")}


def build_simple(node: str, fn: Any) -> StateGraph:
    g = StateGraph(SimpleState)
    g.add_node(node, fn)
    g.add_edge(START, node)
    g.add_edge(node, END)
    return g


def build_datasheet() -> StateGraph:
    return build_simple("g_datasheet", _ds)


def build_template() -> StateGraph:
    return build_simple("g_template", _tpl)


def build_recheck() -> StateGraph:
    return build_simple("g_recheck", _recheck)


def build_export() -> StateGraph:
    return build_simple("g_export", _export)


_ = config
