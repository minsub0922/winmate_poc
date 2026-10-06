"""ca.analyze(§7.6) — 켜진 경쟁사 분석.

load → plan_facts → samsung_side → gather(경쟁사마다, 동시 2곳: 사실 5항목 수집 → extract_fact_claims → verify → judge → positioning)
     → strengths_cautions → finalize        (취소: save_partial — 끝난 경쟁사만 stopped 버전)

모드: full = 모두 다시 수집 · changed_only = 지정(바뀐) 경쟁사만 수집 · resume = 끝나지 않은 경쟁사만 · rejudge = 사실 재사용(수집 0회), 판정부터.
진행(CA3): step `{competitors: [{id, letter, state, done_facts, current_fact, text}], criteria}` · progress `{progress, eta_s}`.
"""
from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import logging
import time
from datetime import timedelta
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.graph import run_graph
from winmate_common.ids import now_iso
from winmate_common.jobs import JobCanceled, JobContext, current_job, jobs

from .. import aix, config, judging, prompts, rules, service
from .. import evidence as E
from .. import store as R
from .common import check_cancel, doc_of, register, save, unwrap_cancel, wait_job_end

log = logging.getLogger("winmate.competitor.analyze")

FACT_QUERY = {
    "lineup": "{name} {product} 제품 라인업",
    "solution": "{name} {product} 솔루션 CMS",
    "references": "{name} {industry} 도입 사례{region}",
    "price": "{name} {product} 가격",
    "recent": "{name} 신제품 출시 {year}",
}
FACT_QUERY_ALT = {
    "lineup": "{name} official {product} lineup",
    "solution": "{name} 보도자료 {product} 솔루션",
    "references": "{name} 고객 사례 {industry}",
    "price": "{name} {product} 가격 견적 조달",
    "recent": "{name} 보도자료 신제품 {year}",
}


class AState(TypedDict, total=False):
    analysis_id: str
    job_id: str
    mode: str
    competitor_ids: list[str]
    prev_job_id: str | None
    targets: list[str]
    reuse: list[str]


# ── 진행 추적(CA3) ───────────────────────────────────────
class Tracker:
    def __init__(self, aid: str, comps: list[dict[str, Any]], targets: set[str], mode: str, crit: dict[str, int]):
        self.aid = aid
        self.order = [c["id"] for c in comps]
        self.letters = {c["id"]: c["letter"] for c in comps}
        self.state = {c["id"]: ("wait" if c["id"] in targets else "done") for c in comps}
        self.done_facts: dict[str, list[str]] = {c["id"]: ([] if c["id"] in targets else list(config.fact_order())) for c in comps}
        self.current: dict[str, str | None] = {c["id"]: None for c in comps}
        self.n_targets = max(1, len(targets))
        self.targets = targets
        self.mode = mode
        self.crit = crit
        self.finishing = 0.0
        self.eta0 = rules.eta_analyze_s(len(comps))
        self.t0 = time.time()
        self._lock = asyncio.Lock()

    def snapshot(self) -> dict[str, Any]:
        comps = [{"id": cid, "letter": self.letters[cid], "display": f"경쟁사 {self.letters[cid]}", "state": self.state[cid],
                  "done_facts": list(self.done_facts[cid]), "current_fact": self.current[cid],
                  "text": service.run_line(self.letters[cid], self.state[cid], self.done_facts[cid], self.current[cid])} for cid in self.order]
        done = sum(len(self.done_facts[c]) for c in self.targets)
        pct = rules.progress_pct(done, self.n_targets, self.finishing) if self.targets else int(round(90 + 10 * self.finishing))
        pct = min(99, pct) if self.finishing < 1 else 100
        eta = max(0, int(self.eta0 * (1 - pct / 100)))
        return {"competitors": comps, "criteria": self.crit, "pct": pct, "eta_s": eta, "eta_label": rules.eta_label_s(eta) if eta else "",
                "mode": self.mode, "title": f"{len(self.order)}곳을 분석하는 중"}

    async def emit(self) -> None:
        async with self._lock:
            snap = self.snapshot()
            await R.call(R.update_analysis, self.aid, lambda d: d.update(run=snap) if d.get("status") == "analyzing" else None)
            ctx = current_job()
            if ctx is not None:
                await ctx.step("competitors", "active", competitors=snap["competitors"], criteria=snap["criteria"])
                await ctx.progress(snap["pct"], snap["title"], eta_s=snap["eta_s"])

    async def set(self, cid: str, *, state: str | None = None, current: str | None = None, done_fact: str | None = None) -> None:
        if state:
            self.state[cid] = state
        self.current[cid] = current
        if done_fact and done_fact not in self.done_facts[cid]:
            self.done_facts[cid].append(done_fact)
        await self.emit()


_TRACKERS: dict[str, Tracker] = {}


def crit_hash(criteria: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps([(c["id"], c["name"], c.get("enabled", True)) for c in criteria], ensure_ascii=False).encode()).hexdigest()[:12]


# ── 노드 ─────────────────────────────────────────────────
async def load(state: AState) -> dict[str, Any]:
    aid = state["analysis_id"]
    await wait_job_end(state.get("prev_job_id"))
    doc = await doc_of(aid)
    on = service.on_competitors(doc)
    work = await R.call(R.get_work, aid)
    wc = work.get("competitors") or {}
    mode = state.get("mode") or "full"
    have = {cid for cid, w in wc.items() if w.get("state") in ("done", "partial") and w.get("facts")}
    if mode == "full":
        targets = [c["id"] for c in on]
    elif mode == "changed_only":
        want = set(state.get("competitor_ids") or []) or {ch.get("competitor_id") for ch in doc.get("changes") or [] if ch.get("competitor_id")}
        targets = [c["id"] for c in on if c["id"] in want or c["id"] not in have]
    else:  # resume · rejudge — 모은 사실은 재사용
        targets = [c["id"] for c in on if c["id"] not in have]
    reuse = [c["id"] for c in on if c["id"] not in targets]

    def reset(w: dict[str, Any]) -> None:
        for cid in targets:
            E.drop_competitor(w, cid)
            w.setdefault("competitors", {})[cid] = {"state": "wait", "facts": {}, "done_facts": []}
        w["job_id"] = state["job_id"]

    await R.call(R.update_work, aid, reset)
    crit = rules.criteria_summary(service.enabled_criteria(doc))
    tr = Tracker(aid, on, set(targets), mode, crit)
    _TRACKERS[state["job_id"]] = tr
    await tr.emit()
    return {"targets": targets, "reuse": reuse}


async def plan_facts(state: AState) -> dict[str, Any]:
    """경쟁사 × 사실 5항목 검색어(실명 · 별칭 · 제품군 · 업종 · 지역) — 고객 원문은 넣지 않는다(query_guard)."""
    aid = state["analysis_id"]
    doc = await doc_of(aid)
    plans = {}
    for c in service.on_competitors(doc):
        if c["id"] in (state.get("targets") or []):
            plans[c["id"]] = fact_queries(doc, c, FACT_QUERY)
    await R.call(R.update_work, aid, lambda w: w.update(plans=plans))
    return {}


def fact_queries(doc: dict[str, Any], c: dict[str, Any], table: dict[str, str]) -> dict[str, str]:
    slots = doc.get("slots") or {}
    from .find import region_of, short_product

    product = short_product((slots.get("product") or {}).get("value")) or "디스플레이"
    industry = config.segment((doc.get("segment") or {}).get("code")).get("short", "")
    place = slots.get("place") or {}
    region = region_of(place) if place.get("value") and place.get("found") != "empty" else None
    year = config.today().year
    return {k: table[k].format(name=c.get("real_name") or c["letter"], product=product, industry=industry, region=f" {region}" if region else "",
                               year=year).strip() for k in config.fact_order()}


async def samsung_side(state: AState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await doc_of(aid)
    crits = service.enabled_criteria(doc)
    work = await R.call(R.get_work, aid)
    bag = {"sources": dict(work.get("sources") or {}), "claims": dict(work.get("claims") or {}), "citations": list(work.get("citations") or [])}
    # 지난 삼성 칸 주장은 지우고 다시(기준 · 추가 제품이 바뀌었을 수 있다)
    old = {k for k, c in bag["claims"].items() if c.get("block") == "samsung"}
    bag["claims"] = {k: v for k, v in bag["claims"].items() if k not in old}
    bag["citations"] = [c for c in bag["citations"] if c.get("claim_id") not in old]
    cells = await judging.samsung_side(doc, bag, crits)

    def upd(w: dict[str, Any]) -> None:
        w["claims"] = {**{k: v for k, v in (w.get("claims") or {}).items() if k not in old}, **{k: v for k, v in bag["claims"].items()
                                                                                               if v.get("block") == "samsung"}}
        cits = [c for c in w.get("citations") or [] if c.get("claim_id") not in old]
        cits += [c for c in bag["citations"] if (bag["claims"].get(c.get("claim_id")) or {}).get("block") == "samsung"]
        w["citations"] = cits
        w.setdefault("sources", {}).update({k: v for k, v in bag["sources"].items() if v.get("kind") in E.KB_KINDS})
        w["samsung_cells"] = cells
        w["samsung_products"] = bag.get("samsung_products") or []
        w["crit_hash"] = crit_hash(crits)

    await R.call(R.update_work, aid, upd)
    return {}


async def gather_one(doc: dict[str, Any], c: dict[str, Any], tr: Tracker, *, queries: dict[str, str], keys: list[str] | None = None,
                     task: str = "ca.web_facts") -> None:
    """한 경쟁사: 사실 항목마다 검색 · 수집(진행 문장) → ca.extract_facts → 대조 → 작업본에 합치기."""
    aid = doc["id"]
    budget = await aix.init_budget("analyze")
    from .find import sensitive_texts

    sensitive = sensitive_texts(doc)
    local: dict[str, Any] = {"sources": {}, "claims": {}, "citations": []}
    ev: list[dict[str, Any]] = []
    keys = keys or list(config.fact_order())
    await tr.set(c["id"], state="run", current=keys[0])
    for i, key in enumerate(keys):
        await E.web_gather(local, ev, budget, task=task, query=queries.get(key) or "", sensitive=sensitive, competitor_id=c["id"], fact_key=key)
        await check_cancel()
        await tr.set(c["id"], state="run", current=keys[i + 1] if i + 1 < len(keys) else None, done_fact=key)
    if c.get("url_guess"):
        await E.fetch_into(local, ev, budget, c["url_guess"], title=f"{c.get('real_name')} 공식 사이트", competitor_id=c["id"])
    state = "done"
    facts: dict[str, Any] = {}
    if ev:
        try:
            out = await aix.llm("ca.extract_facts", prompts.extract_facts(c.get("real_name") or c["letter"], ev,
                                                                          recent_months=int(config.th("recent_months", 12))),
                                prompts.ExtractFactsOut, confidential=False, budget=budget)
            facts = judging.facts_from_llm(local, c["id"], out, ev, keys=keys)
        except aix.LLMFailed as exc:
            log.info("사실 뽑기 실패 %s: %s", c["letter"], exc.message)
            state = "partial"
    else:
        state = "partial"
    for k in keys:
        facts.setdefault(k, judging.fact_entry(local, k, None, []))
    await merge_local(aid, c["id"], local, facts, keys=keys, state=state, done_facts=keys)


async def merge_local(aid: str, cid: str, local: dict[str, Any], facts: dict[str, Any], *, keys: list[str], state: str, done_facts: list[str]) -> None:
    """경쟁사 하나의 결과를 작업본에 합친다(같은 출처는 하나로, 바꾼 항목의 옛 주장은 지운다)."""
    def upd(w: dict[str, Any]) -> None:
        wc = w.setdefault("competitors", {}).setdefault(cid, {"facts": {}})
        old_ids = {x for k in keys for x in ((wc.get("facts") or {}).get(k) or {}).get("claim_ids") or []}
        w["claims"] = {k: v for k, v in (w.get("claims") or {}).items() if k not in old_ids}
        w["citations"] = [x for x in w.get("citations") or [] if x.get("claim_id") not in old_ids]
        srcs = w.setdefault("sources", {})
        remap: dict[str, str] = {}
        for sid, s in local["sources"].items():
            key = s.get("url") or s.get("kb_key") or s.get("content_hash")
            hit = next((k for k, v in srcs.items() if (v.get("url") or v.get("kb_key") or v.get("content_hash")) == key and v.get("kind") == s.get("kind")), None)
            if hit:
                remap[sid] = hit
                for fld in ("competitor_ids", "fact_keys"):
                    srcs[hit][fld] = list(dict.fromkeys((srcs[hit].get(fld) or []) + (s.get(fld) or [])))
            else:
                srcs[sid] = s
        w["claims"].update(local["claims"])
        for x in local["citations"]:
            x = dict(x)
            x["source_id"] = remap.get(x["source_id"], x["source_id"])
            w["citations"].append(x)
        f = dict(wc.get("facts") or {})
        f.update({k: facts[k] for k in keys if k in facts})
        wc["facts"] = f
        wc["state"] = state
        wc["done_facts"] = list(dict.fromkeys((wc.get("done_facts") or []) + done_facts))
        wc["gathered_at"] = now_iso()

    await R.call(R.update_work, aid, upd)


async def judge_one(doc: dict[str, Any], c: dict[str, Any], crits: list[dict[str, Any]]) -> None:
    aid = doc["id"]
    work = await R.call(R.get_work, aid)
    wc = (work.get("competitors") or {}).get(c["id"]) or {}
    facts = wc.get("facts") or {}
    budget = await aix.init_budget("analyze")
    budget.llm = 2
    verdicts = await judging.judge(doc, work, c, facts, crits, work.get("samsung_cells") or {}, budget)
    pos = wc.get("positioning")
    if not pos or wc.get("positioning_for") != wc.get("gathered_at"):
        pos = await judging.positioning(work, c, facts, budget)

    def upd(w: dict[str, Any]) -> None:
        x = w.setdefault("competitors", {}).setdefault(c["id"], {})
        x["verdicts"] = verdicts
        x["positioning"] = pos
        x["positioning_for"] = x.get("gathered_at")
        x["crit_hash"] = crit_hash(crits)
        if x.get("state") not in ("partial",):
            x["state"] = "done"

    await R.call(R.update_work, aid, upd)


async def gather(state: AState) -> dict[str, Any]:
    aid = state["analysis_id"]
    tr = _TRACKERS[state["job_id"]]
    doc = await doc_of(aid)
    crits = service.enabled_criteria(doc)
    work = await R.call(R.get_work, aid)
    plans = work.get("plans") or {}
    targets = set(state.get("targets") or [])
    on = service.on_competitors(doc)
    ch = crit_hash(crits)
    sem = asyncio.Semaphore(config.concurrency())

    async def one(c: dict[str, Any]) -> None:
        async with sem:
            await check_cancel()
            if c["id"] in targets:
                await gather_one(doc, c, tr, queries=plans.get(c["id"]) or fact_queries(doc, c, FACT_QUERY))
                await judge_one(doc, c, crits)
            else:
                wc = ((await R.call(R.get_work, aid)).get("competitors") or {}).get(c["id"]) or {}
                if state.get("mode") == "rejudge" or wc.get("crit_hash") != ch or not wc.get("verdicts"):
                    await judge_one(doc, c, crits)
            w2 = ((await R.call(R.get_work, aid)).get("competitors") or {}).get(c["id"]) or {}
            await tr.set(c["id"], state="partial" if w2.get("state") == "partial" else "done", current=None)

    try:
        async with asyncio.TaskGroup() as tg:
            for c in on:
                tg.create_task(one(c))
    except BaseExceptionGroup as eg:  # noqa: F821 — 3.11+
        raise unwrap_cancel(eg) from None
    return {}


async def strengths_cautions(state: AState) -> dict[str, Any]:
    aid = state["analysis_id"]
    tr = _TRACKERS.get(state["job_id"])
    if tr:
        tr.finishing = 0.5
        await tr.emit()
    doc = await doc_of(aid)
    work = await R.call(R.get_work, aid)
    await _strengths_into_work(doc, work, [c["id"] for c in service.on_competitors(doc)], use_llm=True)
    return {}


async def _strengths_into_work(doc: dict[str, Any], work: dict[str, Any], cids: list[str], *, use_llm: bool) -> None:
    comps = [c for c in service.on_competitors(doc) if c["id"] in cids]
    crits = service.enabled_criteria(doc)
    wc = work.get("competitors") or {}
    verdicts = [v for cid in cids for v in (wc.get(cid) or {}).get("verdicts") or []]
    facts = {cid: (wc.get(cid) or {}).get("facts") or {} for cid in cids}
    st, ca = await judging.strengths_cautions(doc, work, comps, crits, verdicts, work.get("samsung_cells") or {}, facts, use_llm=use_llm)
    await R.call(R.update_work, doc["id"], lambda w: w.update(strengths=st, cautions=ca))


async def finalize(state: AState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await doc_of(aid)
    work = await R.call(R.get_work, aid)
    on = service.on_competitors(doc)
    wc = work.get("competitors") or {}
    cids = [c["id"] for c in on if (wc.get(c["id"]) or {}).get("facts")]
    mode = state.get("mode") or "full"
    n = await save_version(doc, work, cids, kind=mode, stopped=False)
    when = config.now()
    run_at = when + timedelta(days=config.recheck_days())
    sid = await schedule_recheck(doc, run_at.timestamp())

    def upd(d: dict[str, Any]) -> None:
        d["status"] = "done"
        d["result_version"] = n
        d["current_job_id"] = None
        d["current_job_kind"] = None
        d["analyzed_at"] = when.isoformat().replace("+00:00", "Z")
        d["next_recheck_at"] = run_at.isoformat().replace("+00:00", "Z")
        d["recheck"] = {**(d.get("recheck") or {}), "schedule_id": sid}
        d["run"] = None
        d["stopped"] = None
        d["needs_rejudge"] = False
        d["changes"] = []
        d["last_screen"] = "result"

    saved = await save(aid, upd)
    tr = _TRACKERS.get(state["job_id"])
    if tr:
        tr.finishing = 1.0
        ctx = current_job()
        if ctx is not None:
            snap = tr.snapshot()
            await ctx.step("competitors", "done", competitors=snap["competitors"], criteria=snap["criteria"])
    await register(saved)
    return {}


async def save_version(doc: dict[str, Any], work: dict[str, Any], cids: list[str], *, kind: str, stopped: bool) -> int:
    crits = service.enabled_criteria(doc)
    labels = {"full": "전체 분석", "changed_only": "바뀐 경쟁사만 다시", "rejudge": "기준 바꿔 판정", "resume": "이어서 분석", "research": "경쟁사 더 찾기"}
    v = judging.build_version(doc, work, competitor_ids=cids, criteria=crits, strengths=list(work.get("strengths") or []),
                              cautions=list(work.get("cautions") or []), kind=kind, stopped=stopped,
                              summary=f"{labels.get(kind, kind)} · 경쟁사 {len(cids)}곳" + (" · 중지" if stopped else ""))
    n = max([int(x.get("n") or 0) for x in await R.call(R.list_versions, doc["id"])] + [0]) + 1
    await R.call(R.put_version, doc["id"], n, v)
    return n


async def schedule_recheck(doc: dict[str, Any], run_at: float) -> str:
    sid = f"sch_ca_recheck_{doc['id']}"
    try:
        await jobs().unschedule(sid)
        await jobs().schedule(config.SERVICE, "ca.recheck", {"analysis_id": doc["id"]}, run_at, title="30일 재확인", ref=doc["id"],
                              owner=doc.get("owner_id"), schedule_id=sid)
    except Exception:  # noqa: BLE001
        log.exception("재확인 예약 실패")
    return sid


async def save_partial(aid: str, job_id: str, mode: str) -> None:
    """취소 — 끝난 경쟁사만으로 stopped 버전(§7.6 save_partial). 다른 잡이 이어받았으면(기준 바꾸기) 아무것도 하지 않는다."""
    doc = await R.call(R.get_analysis, aid)
    if not doc or doc.get("current_job_id") != job_id:
        return
    work = await R.call(R.get_work, aid)
    on = service.on_competitors(doc)
    wc = work.get("competitors") or {}
    done = [c["id"] for c in on if (wc.get(c["id"]) or {}).get("state") in ("done", "partial") and (wc.get(c["id"]) or {}).get("facts")
            and (wc.get(c["id"]) or {}).get("verdicts") is not None]
    n = None
    if done:
        await _strengths_into_work(doc, work, done, use_llm=False)
        work = await R.call(R.get_work, aid)
        n = await save_version(doc, work, done, kind=mode, stopped=True)

    def upd(d: dict[str, Any]) -> None:
        if d.get("current_job_id") != job_id:
            return
        d["current_job_id"] = None
        d["current_job_kind"] = None
        d["run"] = None
        if n:
            d["status"] = "stopped"
            d["result_version"] = n
            d["stopped"] = {"done": len(done), "total": len(on), "text": f"분석을 멈췄어요 · {len(done)}곳만 결과가 있어요"}
            d["last_screen"] = "result"
        else:
            d["status"] = "done" if d.get("result_version") else "confirming"
            d["last_screen"] = "result" if d.get("result_version") else "candidates"

    saved = await save(aid, upd)
    await register(saved)


async def mark_failed(aid: str, job_id: str, exc: BaseException) -> None:
    doc = await R.call(R.get_analysis, aid)
    if not doc or doc.get("current_job_id") != job_id:
        return

    def upd(d: dict[str, Any]) -> None:
        d["current_job_id"] = None
        d["current_job_kind"] = None
        d["run"] = None
        d["status"] = "done" if d.get("result_version") else "failed"
        d.setdefault("find", {})["error"] = getattr(exc, "message", None) or "분석을 마치지 못했어요"

    saved = await save(aid, upd)
    await register(saved)


def build() -> StateGraph:
    g = StateGraph(AState)
    for name, fn in (("load", load), ("plan_facts", plan_facts), ("samsung_side", samsung_side), ("gather", gather),
                     ("strengths_cautions", strengths_cautions), ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "load")
    g.add_edge("load", "plan_facts")
    g.add_edge("plan_facts", "samsung_side")
    g.add_edge("samsung_side", "gather")
    g.add_edge("gather", "strengths_cautions")
    g.add_edge("strengths_cautions", "finalize")
    g.add_edge("finalize", END)
    return g


STEP_LABELS = {"load": "준비", "plan_facts": "검색어", "samsung_side": "삼성 근거", "gather": "경쟁사 분석", "strengths_cautions": "강점 · 주의할 점",
               "finalize": "저장"}


async def handle(ctx: JobContext) -> dict[str, Any] | None:
    aid = ctx.payload["analysis_id"]
    mode = ctx.payload.get("mode") or "full"
    init: AState = {"analysis_id": aid, "job_id": ctx.job.id, "mode": mode, "competitor_ids": list(ctx.payload.get("competitor_ids") or []),
                    "prev_job_id": ctx.payload.get("prev_job_id")}
    try:
        await run_graph(ctx, build(), dict(init), step_labels=STEP_LABELS)
    except JobCanceled:
        await save_partial(aid, ctx.job.id, mode)
        raise
    except Exception as exc:
        exc2 = unwrap_cancel(exc)
        if isinstance(exc2, JobCanceled):
            await save_partial(aid, ctx.job.id, mode)
            raise exc2 from None
        await mark_failed(aid, ctx.job.id, exc2)
        raise
    finally:
        _TRACKERS.pop(ctx.job.id, None)
    doc = await R.call(R.get_analysis, aid) or {}
    return {"analysis_id": aid, "version": int(doc.get("result_version") or 0), "status": doc.get("status")}
