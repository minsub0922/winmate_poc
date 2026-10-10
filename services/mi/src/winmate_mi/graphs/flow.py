"""새 MI 흐름 잡(miflow) — mi.flow_analyze(Storyboard 읽기 → 고객사 · 업종 · 공간 · 요구 → 검색어) · mi.flow_search(그룹별 웹 검색 → 정리).

짧은 직선 그래프(run_graph)로 돈다 — 노드마다 step 이벤트 · 취소 확인 · 체크포인트. 화면은 MI 문서의 `progress.steps` 를 읽는다(폴링).
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from winmate_common.errors import ApiError
from winmate_common.flow import get_flow
from winmate_common.graph import run_graph
from winmate_common.ids import new_id
from winmate_common.jobs import JobCanceled, JobContext

from .. import aix
from .. import miflow as F

log = logging.getLogger("winmate.mi.flowjobs")


async def _deleted(fid: str) -> bool:
    """잡이 도는 사이 초안을 지웠는지(DELETE) — 그러면 문서를 되살리지 않고 잡을 취소로 끝낸다."""
    return await asyncio.to_thread(F.gone, fid)

ANALYZE_SYSTEM = (
    "너는 삼성 B2B 제안서용 시장 조사(Market Intelligence) 도우미다. 한국어로 쓴다. "
    "입력 Storyboard(고객 요구사항 · DSS · 요약본)에 있는 값만 쓴다. 고객사 · 업종 · 공간은 입력에 있는 문자열 그대로 옮긴다. "
    "검색어는 웹 검색에 넣을 짧은 키워드(8~24자)다. 고객 요구 원문 문장을 그대로 옮기지 않고, 고객의 계획 수치(예산 · 수량 · 목표 %)는 넣지 않는다."
)


class _Queries(BaseModel):
    market: list[str] = Field(default_factory=list, description="시장 · 업계 동향 검색어 3~4개")
    customer: list[str] = Field(default_factory=list, description="고객사 공개 정보(사업 · 공시 · ESG · 투자) 검색어 2~3개")
    user: list[str] = Field(default_factory=list, description="공간 사용자(직원 · 방문객 · 임차인 …) 경험 · 수요 검색어 2~3개")


class _AnalyzeOut(BaseModel):
    customer: str | None = Field(None, description="고객사 이름(입력에 있는 그대로)")
    industry: str | None = Field(None, description="업종(입력 DSS 업종 그대로)")
    spaces: list[str] = Field(default_factory=list, description="DSS 공간 이름들(입력 그대로)")
    needs: list[str] = Field(default_factory=list, description="핵심 요구 2~3개를 짧은 이름으로(예: 에너지 절감)")
    queries: _Queries = Field(default_factory=_Queries)


class S(TypedDict, total=False):
    flow_id: str
    data: dict[str, Any]


def _linear(steps: list[tuple[str, Any]]) -> StateGraph:
    g = StateGraph(S)
    prev = START
    for name, fn in steps:
        g.add_node(name, fn)
        g.add_edge(prev, name)
        prev = name
    g.add_edge(prev, END)
    return g


async def _set_step(fid: str, key: str, state: str, note: str | None = None, *, error: str | None = None) -> None:
    """단계 하나를 끝내고(done · error) 다음 대기 단계를 '하는 중'으로."""
    def fn(d: dict[str, Any]) -> None:
        p = d.get("progress") or {}
        steps = p.get("steps") or []
        for s in steps:
            if s["key"] == key:
                s["state"] = state
                if note is not None:
                    s["note"] = note
        if state in ("done", "error"):
            nxt = next((s for s in steps if s["state"] == "wait"), None)
            if nxt:
                nxt["state"] = "run"
        p["done"] = sum(1 for s in p.get("steps") or [] if s["state"] == "done")
        if error:
            p["error"] = error
        d["progress"] = p
    await F.update(fid, fn)


# ── 분석 ────────────────────────────────────────────────

async def _a_read(state: S) -> dict[str, Any]:
    fid = state["flow_id"]
    d = await F.load(fid)
    flow = await get_flow(d["sb_id"])
    snap = F.flow_snapshot(flow) if flow else (d.get("snapshot") or {})
    got = [x for x, ok in (("요구사항", (snap.get("rq") or {}).get("requirements") or snap.get("customer")),
                           ("DSS", (snap.get("dss") or {}).get("spaces")), ("요약본", snap.get("summary_md"))) if ok]

    def fn(doc: dict[str, Any]) -> None:
        doc["snapshot"] = snap
    await F.update(fid, fn)
    await _set_step(fid, "read", "done", " · ".join(got) or "읽을 값이 적어요")
    return {"data": {"snap": snap}}


def _prompt(snap: dict[str, Any]) -> str:
    return json.dumps({
        "요청": "Storyboard 에서 고객사 · 업종 · 공간 · 핵심 요구를 뽑고, 시장 · 고객사 · 사용자 세 묶음의 웹 검색어를 만든다.",
        "Storyboard": snap.get("name"),
        "고객사": snap.get("customer"),
        "요구사항": snap.get("rq"),
        "DSS": snap.get("dss"),
        "Key message": snap.get("key_message"),
        "요약본": (snap.get("summary_md") or "")[:2000],
    }, ensure_ascii=False, indent=1)


async def _a_extract(state: S) -> dict[str, Any]:
    fid = state["flow_id"]
    snap = state["data"]["snap"]
    an = None
    try:
        out = await aix.llm("mi.flow_analyze.v1", _prompt(snap), _AnalyzeOut, confidential=True, system=ANALYZE_SYSTEM)
        an = F.validate_analysis(out.model_dump(), snap)
    except aix.LLMFailed as exc:
        log.info("Storyboard 분석 모델 답이 맞지 않아 규칙으로: %s", exc)
    except ApiError as exc:
        log.info("Storyboard 분석 모델을 못 써 규칙으로: %s %s", exc.code, exc.message)
    if an is None:
        an = F.rule_analysis(snap)
    sp = an.get("spaces") or []
    note = " · ".join(x for x in [an.get("customer") or "", F.industry_short(an.get("industry")) if an.get("industry") else "", f"공간 {len(sp)}" if sp else ""] if x)
    await _set_step(fid, "extract", "done", note or "[확인 필요]")
    return {"data": {**state["data"], "an": an}}


async def _a_queries(state: S) -> dict[str, Any]:
    fid = state["flow_id"]
    an = state["data"]["an"]
    by = "ai" if an.get("mode") == "llm" else "rule"

    def fn(d: dict[str, Any]) -> None:
        prev = d.get("saved_queries") if d.get("editing") else None
        d["queries"] = F.merge_queries(an["queries"], prev, by)
        d["basis"] = F.basis_of(an)
        d["analysis_mode"] = an.get("mode")
        d["warnings"] = [] if an.get("mode") == "llm" else ["지금은 AI 분석을 쓸 수 없어 Storyboard 값으로 검색어를 만들었어요. 빼거나 더해 주세요."]
    saved = await F.update(fid, fn, "분석")
    n = sum(len(v) for v in F.active_queries(saved).values())
    await _set_step(fid, "queries", "done", f"검색어 {n}")

    def fin(d: dict[str, Any]) -> None:
        d["phase"] = "search"
    await F.update(fid, fin)
    return {"data": {"n": n}}


async def handle_analyze(ctx: JobContext) -> dict[str, Any]:
    fid = ctx.payload["flow_id"]
    try:
        await run_graph(ctx, _linear([("read", _a_read), ("extract", _a_extract), ("queries", _a_queries)]), {"flow_id": fid, "data": {}},
                        step_labels={"read": "Storyboard 읽기", "extract": "고객사 · 업종 · 공간 · 요구 뽑기", "queries": "검색어 만들기"})
    except Exception as exc:  # noqa: BLE001 — 실패해도 화면이 멈추지 않게: 검색 단계로 넘기고 알린다
        if await _deleted(fid):
            raise JobCanceled("초안이 지워졌어요") from exc
        log.exception("MI 흐름 분석 실패 %s", fid)

        def fn(d: dict[str, Any]) -> None:
            d["phase"] = "search"
            (d.get("progress") or {})["error"] = "Storyboard 분석을 마치지 못했어요"
            d.setdefault("warnings", []).append("Storyboard 분석을 마치지 못했어요. 검색어를 직접 넣어 주세요.")
        await F.update(fid, fn)
        if not isinstance(exc, ApiError):
            raise
    return {"flow_id": fid}


# ── 검색 ────────────────────────────────────────────────

_WEB_DOWN = ("UPSTREAM_UNAVAILABLE", "TIMEOUT", "RATE_LIMITED", "DAILY_LIMIT_EXCEEDED", "PROVIDER_ERROR", "NOT_CONFIGURED")


async def _search_one(q: str, group: str, mode: str, sens: list[str], sem: asyncio.Semaphore, down: dict[str, bool]) -> dict[str, Any]:
    rid = new_id("mfr")
    guarded = aix.query_guard(q, sens)
    if not guarded:
        return {"id": rid, "group": group, "query": q, "summary": "", "sources": [], "mode": mode, "error": "고객 원문 · 계획 수치가 들어 있어 검색하지 않았어요", "found": 0}
    if down.get("web"):
        return {"id": rid, "group": group, "query": guarded, "summary": "", "sources": [], "mode": mode, "error": "웹 검색을 쓸 수 없어요", "found": 0}
    async with sem:
        try:
            res = await aix.websearch("mi.flow_search.v1", guarded, max_sources=6)
        except ApiError as exc:
            if exc.status in (429, 502, 503, 504) or exc.code in _WEB_DOWN:
                down["web"] = True
            return {"id": rid, "group": group, "query": guarded, "summary": "", "sources": [], "mode": mode, "error": f"웹 검색 실패 · {exc.message or exc.code}", "found": 0}
    srcs = [{"url": s["url"], "title": s.get("title") or "", "snippet": s.get("snippet")} for s in res.get("sources") or [] if s.get("url")]
    return {"id": rid, "group": group, "query": guarded, "summary": res.get("summary") or "", "sources": srcs,
            "mode": "sources" if (mode == "sources" and srcs) else "summary_only", "error": None, "found": 0}


def _group_node(group: str):
    async def node(state: S) -> dict[str, Any]:
        fid = state["flow_id"]
        d = await F.load(fid)
        qs = F.active_queries(d)[group]
        caps = await aix.capabilities()
        mode = aix.web_mode(caps)
        ws = caps.get("websearch") or {}
        down = {"web": bool(caps and ws and ws.get("available") is False)}
        sem = asyncio.Semaphore(2)
        sens = F.sensitive_texts(d.get("snapshot") or {})
        results = await asyncio.gather(*[_search_one(q, group, mode, sens, sem, down) for q in qs])
        ver = F.target_ver(d)
        found: list[dict[str, Any]] = []
        for r in results:
            items = F.items_from_result(r, group=group, ver=ver)
            r["found"] = len(items)
            found += items
        errs = [r for r in results if r.get("error")]
        note = f"찾은 {len(found)}" + (f" · 실패 {len(errs)}" if errs else "")
        data = dict(state.get("data") or {})
        data.setdefault("results", []).extend(results)
        data.setdefault("found", []).extend(found)
        await _set_step(fid, group, "done" if len(errs) < max(1, len(results)) else "error", note)
        return {"data": data}
    return node


async def _s_organize(state: S) -> dict[str, Any]:
    fid = state["flow_id"]
    data = state.get("data") or {}
    results, found = data.get("results") or [], data.get("found") or []
    out: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> None:
        filters = d.get("filters") or {}
        ver = F.target_ver(d)
        # 고칠 때 담은 정보 유지 → 이전 판 담은 것 먼저(addedIn 그대로), 새로 찾은 것 중 겹치지 않는 것만 뒤에
        prev = [dict(x, kept=True) for x in (d.get("saved_items") or [])] if (d.get("editing") and d.get("keep_previous", True)) else []
        before = {F.norm_key(x["summary_orig"]): x for x in d.get("items") or []}
        seen = {F.norm_key(x["summary_orig"]) for x in prev}
        per_group: dict[str, int] = {}
        items: list[dict[str, Any]] = list(prev)
        dropped = 0
        for it in found:
            k = F.norm_key(it["summary_orig"])
            if not k or k in seen:
                continue
            if not F.passes_filters(it, filters):
                dropped += 1
                continue
            if per_group.get(it["group"], 0) >= F.MAX_ITEMS_PER_GROUP:
                continue
            seen.add(k)
            per_group[it["group"]] = per_group.get(it["group"], 0) + 1
            old = before.get(k)
            if old and old.get("addedIn") == f"v{ver}":       # 같은 판에서 다시 검색 — 담기/빼기 · 고친 문장을 잇는다
                it = {**it, "kept": old.get("kept", True), "summary": old.get("summary") or it["summary"], "edited": old.get("edited", False)}
            items.append(it)
        # 그룹 순서(시장 · 고객사 · 사용자) 안에서는 이번 검색에서 찾은 순서 — 이전 판에서 유지한 것도 다시 찾았으면 그 자리에(보드 MI3: v1에서 유지 · 새로 찾음이 섞여 보인다)
        order = {label: i for i, (_, label) in enumerate(F.GROUPS)}
        pos = {F.norm_key(it["summary_orig"]): i for i, it in enumerate(found)}
        ranked = sorted(enumerate(items), key=lambda p: (order.get(p[1]["group"], 9), pos.get(F.norm_key(p[1]["summary_orig"]), len(found) + p[0])))
        items = [x for _, x in ranked]
        d["items"] = items
        d["results"] = results
        d["phase"] = "refine"
        warns = []
        errs = [r for r in results if r.get("error")]
        if errs and len(errs) == len(results):
            warns.append("웹 검색을 쓸 수 없어 새로 찾은 정보가 없어요. 잠시 후 다시 검색해 주세요.")
        elif errs:
            warns.append(f"검색어 {len(errs)}개는 결과를 받지 못했어요.")
        if dropped:
            warns.append(f"기간 · 출처 조건에 맞지 않는 {dropped}개는 뺐어요.")
        if results and all(r.get("mode") == "summary_only" for r in results if not r.get("error")):
            warns.append("요약형 웹 검색이라 원문 링크가 없는 정보가 있어요 · 수치는 원문에서 확인해 주세요.")
        d["warnings"] = warns
        out["n"] = len(items)
        out["kept"] = sum(1 for x in items if x.get("kept"))
    await F.update(fid, fn, "검색")
    await _set_step(fid, "organize", "done", f"찾은 {out['n']}")
    return {"data": {"n": out["n"]}}


async def handle_search(ctx: JobContext) -> dict[str, Any]:
    fid = ctx.payload["flow_id"]
    if await _deleted(fid):
        raise JobCanceled("초안이 지워졌어요")
    d = await F.load(fid)
    groups = [g for g, _ in F.GROUPS if F.active_queries(d)[g]]
    steps = [(g, _group_node(g)) for g in groups] + [("organize", _s_organize)]
    try:
        await run_graph(ctx, _linear(steps), {"flow_id": fid, "data": {}},
                        step_labels={**{g: f"{F.GROUP_LABEL[g]} 검색" for g in groups}, "organize": "찾은 정보 정리"})
    except Exception as exc:
        if await _deleted(fid):
            raise JobCanceled("초안이 지워졌어요") from exc
        log.exception("MI 흐름 검색 실패 %s", fid)

        def fn(doc: dict[str, Any]) -> None:
            doc["phase"] = "refine" if doc.get("items") else "search"
            (doc.get("progress") or {})["error"] = "검색을 마치지 못했어요"
            doc.setdefault("warnings", []).append("검색을 마치지 못했어요. 다시 검색해 주세요.")
        await F.update(fid, fn)
        raise
    return {"flow_id": fid}
