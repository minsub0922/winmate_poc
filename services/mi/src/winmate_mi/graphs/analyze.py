"""mi.analyze (§7.5) — load → plan → gather(영역 동시) → organize(동시 2) → 작성(비교표 판정 · 삼성 강점 · 시사점 · 정리 · 시트) → finalize.

- 단계(MI3G): 검색 = plan · gather, 정리 = organize(시장 · 고객 · 사용자 주장 추출 + 경쟁 칸 채우기), 작성 = 판정 · 강점 · 시사점 · reconcile · 시트.
- 작업본(drafts[aid])에 영역 결과를 영역마다 저장한다 → 실행 중 미리 보기 · 중지 시 부분 버전(save_partial).
- 그래프 상태는 작게(id · 영역 · 계획) — 큰 데이터(버전 · 근거)는 작업본에 둔다.
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.ids import now_iso
from winmate_common.jobs import JobCanceled, JobContext, current_job, jobs

from .. import aix, anonymize, claims as C, config, kbx, layout, prompts, rules, service, verify, versions, views
from .. import store as R
from ..store import nid
from .common import (
    Budget, RunTracker, add_source, area_hashes, copy_area, drop_area, emit_partial, evidence, file_evidence, ingest_claim, init_web,
    kb_cases_evidence, kb_search_evidence, kb_segment_evidence, known_names, memo_log, refresh_numeric_fields, sensitive_texts, strip_urls,
    table_text, web_gather,
)
from .competitors import add_competitor, find_candidates

log = logging.getLogger("winmate.mi.analyze")

STEP_LABELS = {"load": "준비", "plan": "검색 계획", "gather": "검색", "organize": "정리", "build_comparison": "비교표",
               "derive_strengths": "삼성 강점", "implications": "시사점", "reconcile": "정리 검사", "compose_slides": "시트 구성", "finalize": "저장"}
WRITE_STEPS = ("build_comparison", "derive_strengths", "implications", "reconcile", "compose_slides")
_TRACKERS: dict[str, RunTracker] = {}


class AnalyzeState(TypedDict, total=False):
    analysis_id: str
    job_id: str
    mode: str
    req_areas: list[str]
    areas: list[str]
    todo: list[str]
    reused: list[str]
    write_only: bool
    base_n: int
    eta0: int
    header: dict[str, Any]
    plan: dict[str, Any]
    memos: list[str]


# ── 도우미 ───────────────────────────────────────────────
async def _doc(aid: str) -> dict[str, Any]:
    doc = await R.call(R.get_analysis, aid)
    if doc is None:
        raise ApiError(404, "NOT_FOUND", "분석 작업을 찾을 수 없어요", {"id": aid})
    return doc


async def _draft(aid: str) -> dict[str, Any]:
    return await R.call(R.get_draft, aid) or {}


async def _save_draft(aid: str, **fields: Any) -> None:
    await R.call(R.update_draft, aid, lambda d: d.update(fields))


def _budget(d: dict[str, Any] | None, depth: int) -> Budget:
    b = Budget.for_depth(depth)
    if d:
        b.used = {**b.used, **(d.get("used") or {})}
        b.web_unavailable = bool(d.get("web_unavailable"))
        b.mode = d.get("mode") or b.mode
        b.caps = d.get("caps") or {}
    return b


def _bdump(b: Budget) -> dict[str, Any]:
    return {"used": dict(b.used), "web_unavailable": b.web_unavailable, "mode": b.mode, "caps": b.caps}


def _depth(doc: dict[str, Any]) -> int:
    return int((doc.get("depth") or {}).get("target_sources") or rules.depth_for((doc.get("usage") or {}).get("value")))


def _seg(doc: dict[str, Any], which: str = "a") -> str:
    seg = doc.get("segment") or {}
    mix = seg.get("mix") or {}
    return mix.get(which) or seg.get("code") or "GEN"


def _req_text(doc: dict[str, Any], limit: int = 600) -> str:
    parts = [r.get("text", "") for r in doc.get("requirements") or []] + [doc.get("requirements_text") or ""]
    return " ".join(p for p in parts if p)[:limit]


def _tracker(state: AnalyzeState) -> RunTracker:
    jid = state.get("job_id") or ""
    t = _TRACKERS.get(jid)
    if t is None:
        t = RunTracker(current_job(), state["analysis_id"], list(state.get("areas") or []), list(state.get("reused") or []),
                       int(state.get("eta0") or 180), header=state.get("header") or {})
        t.write_total = len(WRITE_STEPS)
        _TRACKERS[jid] = t
    return t


def run_header(doc: dict[str, Any]) -> dict[str, Any]:
    """MI3G 머리 — `분석 시작 · 4개 영역 · 경쟁사 A · B · C · 비교 기준 5개` · `{주제} 분석 중` · `4개 영역 · 경쟁사 3`."""
    areas = service.areas_of(doc)
    live = anonymize.live(doc.get("competitors") or [])
    n_crit = sum(1 for c in doc.get("criteria") or [] if c.get("enabled", True))
    chip = ["분석 시작", f"{len(areas)}개 영역"]
    sub = [f"{len(areas)}개 영역"]
    if "competitor" in areas and live:
        chip.append("경쟁사 " + " · ".join(c["letter"] for c in live))
        sub.append(f"경쟁사 {len(live)}")
    if "competitor" in areas and n_crit:
        chip.append(f"비교 기준 {n_crit}개")
    topic = (doc.get("topic") or "").strip() or rules.scope_label(areas) or "시장"
    return {"summary_chip": " · ".join(chip), "card_title": f"{topic} 분석 중", "card_sub": " · ".join(sub)}


def _area_sources(version: dict[str, Any], area: str) -> int:
    return sum(1 for s in (version.get("sources") or {}).values() if area in (s.get("areas") or []) and s.get("state") != "excluded")


def _gathered_note(doc: dict[str, Any], area: str, version: dict[str, Any]) -> str:
    n = _area_sources(version, area)
    if area == "competitor":
        nc = len(anonymize.live(doc.get("competitors") or []))
        k = sum(1 for c in doc.get("criteria") or [] if c.get("enabled", True))
        return f"경쟁사 {nc} × 기준 {k} · 출처 {n}곳 확인됨"
    return f"출처 {n}곳 확인됨"


def _run_note(doc: dict[str, Any], area: str) -> str:
    if area == "market":
        return "시장 규모 · 트렌드 정리 중"
    if area == "customer":
        return "전략 · 운영 구조 정리 중"
    if area == "user":
        return f"{config.segment(_seg(doc, 'c'))['users']} 페르소나 정리 중"
    return "비교표 정리 중"


def _done_note(doc: dict[str, Any], area: str, version: dict[str, Any]) -> str:
    _, src_n = views.numbering(version, area)
    n = len(src_n)
    if area == "market":
        s = config.segment(_seg(doc))
        what = f"{s['market']} {s['product']} 도입 트렌드 · 규제" if s["code"] != "GEN" else "시장 규모 · 도입 트렌드"
    elif area == "customer":
        what = "전략 · 확장 계획 · 운영 구조"
    elif area == "user":
        what = f"{config.segment(_seg(doc, 'c'))['users']} 페르소나"
    else:
        nc = len(anonymize.live(doc.get("competitors") or []))
        k = len((((version.get("document") or {}).get("competitor") or {}).get("table") or {}).get("criteria") or [])
        what = f"경쟁사 {nc} × 기준 {k}"
    return f"출처 {n} · {what}"


# ── load ─────────────────────────────────────────────────
async def load(state: AnalyzeState) -> dict[str, Any]:
    aid = state["analysis_id"]
    ctx = current_job()
    doc = await _doc(aid)
    areas = service.areas_of(doc)
    if not areas:
        raise ApiError(422, "VALIDATION_FAILED", "분석 범위를 하나 이상 골라 주세요")
    base_n = int(doc.get("result_version") or 0)
    base = await R.call(R.get_version, aid, base_n) if base_n else None
    kb_ver = await kbx.kb_version()
    hashes = area_hashes(doc, kb_ver)
    mode = state.get("mode") or "auto"
    req = [a for a in state.get("req_areas") or [] if a in areas]

    def done_in_base(a: str) -> bool:
        return bool(base) and ((base or {}).get("area_status") or {}).get(a) in ("done", "reused")

    if not base or mode == "full":
        todo = list(areas)
    elif mode == "resume":
        todo = [a for a in areas if not done_in_base(a)] + [a for a in req if done_in_base(a)]
    else:
        todo = [a for a in areas if not done_in_base(a) or ((base or {}).get("area_hashes") or {}).get(a) != hashes[a] or a in req]
    todo = [a for a in rules.AREAS if a in todo]
    write_only = bool(base) and "competitor" in areas and "competitor" not in todo and \
        ((base or {}).get("area_hashes") or {}).get("competitor_write") != hashes["competitor_write"]
    reused = [a for a in areas if a not in todo]
    version: dict[str, Any] = {"document": {}, "claims": {}, "citations": [], "sources": {}, "area_status": {}, "area_hashes": {}, "kb_version": kb_ver}
    for a in reused:
        copy_area(version, base or {}, a)
    if base:
        version["fix_items"] = base.get("fix_items") or {}
        version["slides"] = base.get("slides") or []
        if (base.get("document") or {}).get("implications") and not todo and not write_only:
            version["document"]["implications"] = base["document"]["implications"]
    for a in todo:
        version["area_status"][a] = "wait"
    budget = Budget.for_depth(_depth(doc))
    await init_web(budget)
    eta0 = service.eta_for_run(doc, todo or areas, mode)
    header = run_header(doc)
    await R.call(R.put_draft, aid, {"work": version, "evidence": {}, "budget": _bdump(budget), "job_id": ctx.job.id if ctx else None,
                                    "base_n": base_n, "todo": todo, "hashes": hashes, "samsung": {}, "progress": {}})

    def mark(d: dict[str, Any]) -> None:
        d["status"] = "running"
        d["current_job_id"] = ctx.job.id if ctx else d.get("current_job_id")
        d["last_screen"] = "run"
        d.setdefault("run", {}).update(stage="search", sources_total=len(version["sources"]), started_at=d.get("run", {}).get("started_at") or now_iso(),
                                       mode=mode, todo=todo)

    saved = await R.call(R.update_analysis, aid, mark)
    await service.register(saved)
    st: AnalyzeState = {"areas": areas, "todo": todo, "reused": reused, "write_only": write_only, "base_n": base_n, "eta0": eta0,
                        "header": header, "memos": [m.get("text", "") for m in doc.get("memos") or [] if m.get("where") == "run"]}
    t = RunTracker(ctx, aid, areas, reused, eta0, header=header)
    t.write_total = len(WRITE_STEPS)
    t.set_counts(version)
    _TRACKERS[(ctx.job.id if ctx else state.get("job_id")) or ""] = t
    await t.set_stage("search")
    return st


# ── plan ─────────────────────────────────────────────────
def _template_queries(doc: dict[str, Any], area: str) -> list[dict[str, Any]]:
    s = config.segment(_seg(doc))
    region = ((doc.get("extracted") or {}).get("region") or "국내").strip()
    cust = (doc.get("customer_name") or "").strip()
    market = s["market"] if s["code"] != "GEN" else ""
    if area == "market":
        return [{"q": f"{region} {market} {s['product']} 시장 규모".strip(), "purpose": "시장 규모 · 성장률", "recency_months": 24},
                {"q": f"{market} {s['product']} 도입 트렌드".strip(), "purpose": "도입 트렌드", "recency_months": 24},
                {"q": f"{market} {s['product']} 규제".strip(), "purpose": "규제", "recency_months": 24}]
    if area == "customer":
        return [{"q": f"{cust} 사업보고서 매장 전략", "purpose": "전략", "recency_months": 24},
                {"q": f"{cust} 확장 계획 보도자료", "purpose": "확장 계획", "recency_months": 24}] if cust else []
    if area == "user":
        u = config.segment(_seg(doc, "c"))
        return [{"q": f"{u['market'] if u['code'] != 'GEN' else ''} {u['user']} 대기 동선 이용 행태".strip(), "purpose": "이용자 행동", "recency_months": 24}]
    return []


async def plan(state: AnalyzeState) -> dict[str, Any]:
    aid = state["analysis_id"]
    ctx = current_job()
    memos = list(state.get("memos") or [])
    await memo_log(ctx, memos)
    todo = [a for a in state.get("todo") or []]
    if not todo:
        return {"plan": {}, "memos": memos}
    doc = await _doc(aid)
    draft = await _draft(aid)
    budget = _budget(draft.get("budget"), _depth(doc))
    out: dict[str, Any] = {}
    if budget.take("llm"):
        try:
            res = await aix.llm("mi.plan", prompts.plan(doc, todo, memos), prompts.Plan, confidential=True)
            for ap in res.areas:
                if ap.area in todo:
                    out[ap.area] = {"questions": ap.questions[:6], "web_queries": [q.model_dump() for q in ap.web_queries[:4]], "file_terms": ap.file_terms[:8]}
        except (aix.LLMFailed, ApiError) as exc:
            log.info("계획 LLM 실패 → 템플릿 검색어: %s", exc)
    for a in todo:
        if a not in out or not out[a].get("web_queries"):
            out.setdefault(a, {"questions": [], "file_terms": []})["web_queries"] = _template_queries(doc, a)
    await _save_draft(aid, budget=_bdump(budget))
    return {"plan": out, "memos": memos}


# ── gather ───────────────────────────────────────────────
async def gather_query(version: dict[str, Any], ev: list[dict[str, Any]], budget: Budget, tracker: RunTracker | None, *, task: str, query: str,
                       area: str, sensitive: list[str], competitor_id: str | None = None, recency: int = 24) -> int:
    """웹 검색 1회 + 오래된 출처면 최근 기간 조건으로 1회 더(§7.5 날짜 행). 대체를 못 찾으면 오래된 출처를 다시 `사용`(인용 stale)."""
    before = set((version.get("sources") or {}).keys())
    n = await web_gather(version, ev, budget, tracker, task=task, query=query, area=area, sensitive=sensitive, competitor_id=competitor_id,
                         recency_months=recency)
    new = [s for sid, s in (version.get("sources") or {}).items() if sid not in before]
    stale = [s for s in new if s.get("excluded_reason") == "stale"]
    if stale:
        n2 = await web_gather(version, ev, budget, tracker, task=task, query=f"{query} 최근", area=area, sensitive=sensitive,
                              competitor_id=competitor_id, recency_months=recency)
        if n2 == 0:
            for s in stale:
                s["state"] = "used"
                s["excluded_reason"] = None
                s["stale_kept"] = True
                text, pages = R.load_snapshot(s["id"])
                if pages:
                    for i, ptxt in enumerate(pages[:20], start=1):
                        evidence(ev, source_id=s["id"], kind=s["kind"], title=s["title"], text=ptxt, page=i)
                elif text:
                    evidence(ev, source_id=s["id"], kind=s["kind"], title=s["title"], text=text)
            n += len(stale)
        if tracker:
            tracker.set_counts(version)
    return n


async def _gather_market(doc: dict[str, Any], version: dict[str, Any], ev: list[dict[str, Any]], budget: Budget, tracker: RunTracker,
                         plan_a: dict[str, Any], sens: list[str]) -> None:
    code = _seg(doc)
    s = config.segment(code)
    await kb_segment_evidence(version, ev, tracker, segment=code, area="market")
    await kb_search_evidence(version, ev, tracker, text=f"{s['market'] if code != 'GEN' else ''} {s['product']} 트렌드".strip(), area="market", k=3)
    await file_evidence(version, ev, tracker, analysis=doc, area="market", kinds=("internal_research", "deployment_report"))
    for q in (plan_a.get("web_queries") or [])[:3]:
        await gather_query(version, ev, budget, tracker, task="mi.web_market", query=q["q"], area="market", sensitive=sens,
                           recency=int(q.get("recency_months") or 24))


async def _gather_customer(doc: dict[str, Any], version: dict[str, Any], ev: list[dict[str, Any]], budget: Budget, tracker: RunTracker,
                           plan_a: dict[str, Any], sens: list[str]) -> None:
    await file_evidence(version, ev, tracker, analysis=doc, area="customer",
                        kinds=("rfp", "minutes", "ir", "customer_material", "internal_research", "deployment_report", "other"))
    kr = (config.segment(_seg(doc)).get("kr") or [None])[0]
    cases = await kbx.similar_cases(_req_text(doc), vertical=kr, limit=3)
    await kb_cases_evidence(version, ev, tracker, case_ids=[c["id"] for c in cases[:2]], area="customer")
    reduced = "customer" in ((doc.get("scope") or {}).get("reduced") or [])
    for q in (plan_a.get("web_queries") or [])[: (1 if reduced else 3)]:
        await gather_query(version, ev, budget, tracker, task="mi.web_customer", query=q["q"], area="customer", sensitive=sens,
                           recency=int(q.get("recency_months") or 24))


async def _gather_user(doc: dict[str, Any], version: dict[str, Any], ev: list[dict[str, Any]], budget: Budget, tracker: RunTracker,
                       plan_a: dict[str, Any], sens: list[str]) -> None:
    await file_evidence(version, ev, tracker, analysis=doc, area="user", kinds=("rfp", "minutes", "customer_material"))
    kr = (config.segment(_seg(doc, "c")).get("kr") or [None])[0]
    cases = await kbx.similar_cases(_req_text(doc), vertical=kr, limit=3)
    await kb_cases_evidence(version, ev, tracker, case_ids=[c["id"] for c in cases[:2]], area="user")
    for q in (plan_a.get("web_queries") or [])[:2]:
        await gather_query(version, ev, budget, tracker, task="mi.web_user", query=q["q"], area="user", sensitive=sens,
                           recency=int(q.get("recency_months") or 24))


SPEC_KEYS: list[tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = [
    (("전력", "전기료", "에너지", "절전"), ("power_consumption",), ("On Mode", "Typ")),
    (("밝기", "휘도", "야외", "가독"), ("brightness_nit",), ()),
    (("해상도", "화질", "선명"), ("resolution",), ()),
    (("크기", "사이즈", "인치"), ("screen_size_cm",), ()),
    (("24시간", "연속", "운영 시간", "상시"), ("operation_hours",), ()),
    (("온도", "동작 환경"), ("operating_temp_c",), ()),
    (("무게", "경량"), ("weight_kg",), ("제품",)),
    (("무선", "wifi", "와이파이"), ("wifi",), ()),
]


def spec_row_for(name: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    low = (name or "").lower()
    for words, keys, prefer in SPEC_KEYS:
        if not any(w.lower() in low for w in words):
            continue
        hits = [r for r in rows if r.get("norm_key") in keys]
        if not hits:
            continue
        for p in prefer:
            for r in hits:
                if p.lower() in (r.get("attr_name") or "").lower():
                    return r
        return hits[0]
    return None


async def resolve_products(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """삼성 비교 제품: TopBar 로 추가한 제품 → 요구 문장의 모델 → S1 공간별 추천 1순위 제품군 대표 모델(§7.7)."""
    prods = [dict(p) for p in doc.get("samsung_products") or []]
    text = _req_text(doc, 1200)
    if not prods:
        for tok in list(dict.fromkeys(verify._MODEL_RE.findall(text)))[:3]:
            hits = await kbx.product_search(tok, 1)
            if hits and hits[0].get("kind") == "model":
                h0 = hits[0]
                prods.append({"model_code": h0.get("model_code"), "family_id": h0.get("family_id"), "name": h0.get("display_name") or h0.get("model_code"),
                              "ref": f"kb:model:{h0.get('id')}", "kind": "model", "origin": "requirements"})
    if not prods:
        rec = await kbx.recommend(text or config.segment(_seg(doc))["product"])
        for sp in rec.get("by_space") or []:
            fams = sp.get("families") or []
            if fams and fams[0].get("model"):
                f = fams[0]
                prods.append({"model_code": f["model"], "family_id": f.get("id"), "name": f.get("name") or f["model"], "ref": f"kb:model:mdl_{f['model']}",
                              "kind": "model", "origin": "s1"})
                break
    return prods[:3]


async def _gather_samsung(doc: dict[str, Any], version: dict[str, Any], ev: list[dict[str, Any]], tracker: RunTracker) -> dict[str, Any]:
    prods = await resolve_products(doc)
    spec = None
    first = next((p for p in prods if p.get("model_code")), None)
    if first:
        t = await kbx.spec_table([first["model_code"]])
        if t and t.get("rows"):
            m = (t.get("models") or [{}])[0]
            display = m.get("display_name") or first["model_code"]
            rows = []
            for r in t["rows"]:
                vals = list((r.get("values") or {}).values())
                if vals and vals[0].get("raw"):
                    rows.append({"attr_name": r.get("attr_name") or "", "norm_key": r.get("norm_key"), "raw": vals[0]["raw"]})
            text = f"{display} ({first['model_code']}) 공식 스펙\n" + "\n".join(f"{r['attr_name']}: {r['raw']}" for r in rows)
            src = {"kind": "kb_official", "subtype": "스펙", "title": f"{display} 공식 스펙", "publisher": "samsung.com", "url": m.get("source_url"),
                   "published_at": None, "published_basis": "kb", "retrieved_at": now_iso(), "authority": 2, "classification": "public", "state": "used",
                   "mode": "kb", "areas": ["competitor"], "kb_key": f"spec:{first['model_code']}", "tier": "T2", "aliases": [display, first["model_code"]],
                   "kb_ref": {"pattern": "spec_table", "entity_kind": "model", "entity_id": m.get("id"), "document_url": m.get("source_url"), "tier": "T2"}}
            sid = add_source(version, src)
            tracker.add_source("kb_official", src["title"], "used")
            e = evidence(ev, source_id=sid, kind="kb_official", title=src["title"], text=text, label="사내 스펙")
            spec = {"display": display, "model_code": first["model_code"], "evidence_id": e["id"], "rows": rows}
            first["name"] = display
    msgs: dict[str, list[dict[str, Any]]] = {}
    for crt in service.ordered_criteria(doc.get("criteria") or []):
        if spec and spec_row_for(crt["name"], spec["rows"]):
            continue
        for mm in [x for x in await kbx.messages(crt["name"], limit=3) if float(x.get("score") or 0) >= 0.45][:2]:
            src = {"kind": "kb_official", "subtype": "메시지", "title": f"삼성 메시지 · {mm.get('about_name') or crt['name']}", "publisher": "samsung.com",
                   "url": None, "published_at": None, "published_basis": "kb", "retrieved_at": now_iso(), "authority": 2, "classification": "public",
                   "state": "used", "mode": "kb", "areas": ["competitor"], "kb_key": f"msg:{mm.get('id')}", "tier": "T2", "claim_flag": int(mm.get("claim_flag") or 0),
                   "kb_ref": {"pattern": "E2", "entity_kind": "message", "entity_id": mm.get("id"), "tier": "T2"}}
            sid = add_source(version, src)
            e = evidence(ev, source_id=sid, kind="kb_official", title=src["title"], text=mm.get("text") or "", label="삼성 공식")
            msgs.setdefault(crt["id"], []).append({"text": mm.get("text") or "", "evidence_id": e["id"], "claim_flag": int(mm.get("claim_flag") or 0)})
    kr = (config.segment(_seg(doc)).get("kr") or [None])[0]
    cases = await kbx.similar_cases(_req_text(doc), vertical=kr, limit=3)
    extra = list((doc.get("extracted") or {}).get("extra_cases") or [])
    await kb_cases_evidence(version, ev, tracker, case_ids=list(dict.fromkeys(extra + [c["id"] for c in cases]))[:4], area="competitor", with_kpi=True)
    tracker.set_counts(version)
    return {"products": prods, "spec": spec, "messages": msgs}


async def _gather_competitor(doc: dict[str, Any], version: dict[str, Any], ev: list[dict[str, Any]], budget: Budget, tracker: RunTracker,
                             plan_a: dict[str, Any], sens: list[str]) -> dict[str, Any]:
    aid = doc["id"]
    live = anonymize.live(doc.get("competitors") or [])
    if not live:
        cands, _ = await find_candidates(doc, budget, want=int(config.th("competitor_auto_top", 3)), exclude=doc.get("competitors") or [])
        if cands:
            def add(d: dict[str, Any]) -> None:
                for c in cands:
                    add_competitor(d, c.name, origin="auto", aliases=c.aliases, kind_label=c.kind_label, desc=c.desc, confidence=c.confidence)
                decs = d.setdefault("decisions", {})
                decs["competitors"] = {**(decs.get("competitors") or {}), "mode": "check",
                                       "reason": f"지정 없음 → {config.segment(_seg(d)).get('short', '업종')} 사례 빈도 상위 {len(cands)}"}
                service.refresh_decisions(d)

            doc = await R.call(R.update_analysis, aid, add)
            live = anonymize.live(doc.get("competitors") or [])
    s = config.segment(_seg(doc))
    planned = plan_a.get("web_queries") or []
    for c in live:
        qs = [q for q in planned if c.get("real_name") and c["real_name"] in q.get("q", "")] or \
             [{"q": f"{c['real_name']} {s['product']} 제품 라인업 CMS", "recency_months": 24}]
        for q in qs[:2]:
            await gather_query(version, ev, budget, tracker, task="mi.web_competitor", query=q["q"], area="competitor", sensitive=sens,
                               competitor_id=c["id"], recency=int(q.get("recency_months") or 24))
    # 사용자가 올린 경쟁사 자료(칸에는 공개 · 고객 분류만 쓴다 — ingest_claim 이 거른다)
    await file_evidence(version, ev, tracker, analysis=doc, area="competitor", allow_confidential=True)
    return await _gather_samsung(doc, version, ev, tracker)


async def gather(state: AnalyzeState) -> dict[str, Any]:
    aid = state["analysis_id"]
    ctx = current_job()
    tracker = _tracker(state)
    memos = list(state.get("memos") or [])
    await memo_log(ctx, memos)
    todo = list(state.get("todo") or [])
    doc = await _doc(aid)
    draft = await _draft(aid)
    version = draft.get("work") or {}
    budget = _budget(draft.get("budget"), _depth(doc))
    sens = sensitive_texts(doc)
    plans = state.get("plan") or {}
    evid: dict[str, list[dict[str, Any]]] = {}
    samsung: dict[str, Any] = {}

    async def one(area: str) -> None:
        nonlocal samsung
        ev: list[dict[str, Any]] = []
        tracker.area_status[area] = "run"
        tracker.area_note[area] = "자료 찾는 중"
        await tracker.emit("자료를 찾고 있어요")
        try:
            if area == "market":
                await _gather_market(doc, version, ev, budget, tracker, plans.get(area) or {}, sens)
            elif area == "customer":
                await _gather_customer(doc, version, ev, budget, tracker, plans.get(area) or {}, sens)
            elif area == "user":
                await _gather_user(doc, version, ev, budget, tracker, plans.get(area) or {}, sens)
            else:
                samsung = await _gather_competitor(doc, version, ev, budget, tracker, plans.get(area) or {}, sens)
        except ApiError as exc:
            log.warning("%s 근거 모으기 일부 실패: %s", area, exc)
        evid[area] = ev
        tracker.gathered.add(area)
        tracker.area_status[area] = "wait"
        tracker.area_note[area] = _gathered_note(await _doc(aid) if area == "competitor" else doc, area, version)
        tracker.set_counts(version)
        await tracker.emit()

    await asyncio.gather(*(one(a) for a in todo))
    if budget.web_unavailable:
        version["web_unavailable"] = True
    version["web_mode"] = budget.mode
    await _save_draft(aid, work=version, evidence=evid, budget=_bdump(budget), samsung=samsung)
    tracker.stage_status["search"] = "done"
    await memo_log(ctx, memos)
    return {"memos": memos}


# ── organize ─────────────────────────────────────────────
def _area_quotes(version: dict[str, Any], area: str) -> list[dict[str, Any]]:
    ids = {k for k, v in (version.get("claims") or {}).items() if v.get("area") == area}
    return [{"quote": c.get("quote") or ""} for c in version.get("citations") or [] if c.get("claim_id") in ids and not c.get("dropped")]


def _clean_free(text: str | None, quotes: list[dict[str, Any]], ev_text: str) -> str:
    """블록의 자유 글(트렌드 시사점 · 페르소나 등) — 근거에 없는 수치는 [00], 근거에 없는 모델코드는 [확인 필요](§7.6.6)."""
    t = strip_urls(text or "")
    if not t:
        return ""
    t, _ = verify.mask_unsupported(t, quotes)
    hay = verify.N(ev_text)
    for code in set(verify._MODEL_RE.findall(t)):
        if verify.N(code) not in hay:
            t = t.replace(code, "[확인 필요]")
    return t


def ingest_area(version: dict[str, Any], doc: dict[str, Any], area: str, res: Any, ev: list[dict[str, Any]]) -> None:
    drop_area(version, area)
    known = known_names(doc)
    cid_of: dict[str, str] = {}
    for c in res.claims:
        if not (c.text or "").strip():
            continue
        cid_of[c.local_id] = ingest_claim(version, area=area, text=c.text.strip(), citations=[x.model_dump() for x in c.citations], ev_list=ev,
                                          block_path=c.block_path, metric_key=c.metric_key, metric_label=c.metric_label, known_names=known)
    quotes = _area_quotes(version, area)
    ev_text = "\n".join(e.get("text", "") for e in ev)
    b = res.blocks
    f = lambda t: _clean_free(t, quotes, ev_text)  # noqa: E731
    if area == "market":
        series = {}
        for p in b.size_series:
            if p.claim in cid_of and p.year not in series:
                series[p.year] = {"year": int(p.year), "claim": cid_of[p.claim], "value": None, "unit": b.size_unit}
        out = {"size_label": f(b.size_label), "size_unit": b.size_unit, "size_series": [series[y] for y in sorted(series)],
               "cagr": ({"period": f(b.cagr.period), "claim": cid_of[b.cagr.claim], "value": None} if b.cagr and b.cagr.claim in cid_of else None),
               "trends": [{"title": f(t.title), "when": t.when, "claim": cid_of[t.claim], "implication": f(t.implication)} for t in b.trends if t.claim in cid_of],
               "regulations": [{"title": f(r.title), "claim": cid_of[r.claim]} for r in b.regulations if r.claim in cid_of],
               "kb_trend": cid_of.get(b.kb_trend or "")}
    elif area == "customer":
        out = {"summary": cid_of.get(b.summary or ""), "strategy": [cid_of[x] for x in b.strategy if x in cid_of],
               "expansion": [cid_of[x] for x in b.expansion if x in cid_of],
               "structure": [{"label": f(s.label), "value": f(s.value), "claim": cid_of.get(s.claim or "")} for s in b.structure],
               "ops_challenges": [{"stage": f(o.stage), "claim": cid_of[o.claim]} for o in b.ops_challenges if o.claim in cid_of],
               "reduced": "customer" in ((doc.get("scope") or {}).get("reduced") or [])}
    else:
        out = {"personas": [{"role": f(p.role), "goal": f(p.goal), "pain": f(p.pain), "context": f(p.context),
                             "claims": [cid_of[x] for x in p.claims if x in cid_of]} for p in b.personas[:3]],
               "journey": [{"stage": f(j.stage), "touchpoint": f(j.touchpoint), "pain": f(j.pain), "opportunity": f(j.opportunity),
                            "claims": [cid_of[x] for x in j.claims if x in cid_of]} for j in b.journey[:8]],
               "composition": [{"label": f(c.label), "claim": cid_of[c.claim], "value": None, "unit": "%"} for c in b.composition if c.claim in cid_of]}
    version.setdefault("document", {})[area] = out
    refresh_numeric_fields(version)


async def corroborate(doc: dict[str, Any], version: dict[str, Any], budget: Budget, sens: list[str]) -> int:
    """summary_only 모드 — 핵심 지표(연도별 규모 · 성장률)가 요약으로만 뒷받침되면 다르게 쓴 검색어로 1회 더(§7.6.5)."""
    if budget.mode != "summary_only" or budget.web_unavailable:
        return 0
    mk = (version.get("document") or {}).get("market") or {}
    keys = [p.get("claim") for p in (mk.get("size_series") or [])[-1:]] + [(mk.get("cagr") or {}).get("claim")]
    claims = version.get("claims") or {}
    srcs = version.get("sources") or {}
    s = config.segment(_seg(doc))
    done = 0
    for cid in [k for k in keys if k and k in claims][:2]:
        cl = claims[cid]
        cits = C.citations_of(version, cid)
        if not cits or not all(srcs.get(c["source_id"], {}).get("kind") == "websearch_summary" for c in cits):
            continue
        nums = [n for n in verify.parse_numbers(cl.get("text", "")) if n.kind != "year"]
        if not nums:
            continue
        target = nums[0]
        what = "성장률" if cid == (mk.get("cagr") or {}).get("claim") else "시장 규모"
        q = aix.query_guard(f"{s['market'] if s['code'] != 'GEN' else ''} {s['product']} {what} 전망 통계".strip(), sens)
        if not q or not budget.take("websearch"):
            continue
        try:
            res = await aix.websearch("mi.web_corroborate", q)
        except ApiError as exc:
            if exc.status in (429, 502, 503, 504):
                budget.web_unavailable = True
            break
        summary = strip_urls(res.get("summary") or "")
        cand = [n for n in verify.parse_numbers(summary) if n.kind != "year" and n.unit == target.unit]
        if not cand:
            continue
        best = min(cand, key=lambda n: abs(n.value - target.value))
        sent = next((x for x in re.split(r"(?<=[.!?。])\s+|\n", summary) if best.raw.replace(" ", "") in verify.N(x).replace(" ", "")), None) or summary[:200]
        src = {"kind": "websearch_summary", "subtype": "", "title": f"웹 검색 요약 · {q}", "publisher": "웹 검색 요약", "url": None,
               "published_at": None, "published_basis": "unknown", "retrieved_at": now_iso(), "authority": 6, "classification": "public",
               "state": "used", "mode": budget.mode, "areas": ["market"], "query": q, "summary": summary, "content_hash": verify.N(summary)[:64]}
        sid = add_source(version, src)
        if sid == src.get("id"):
            R.save_snapshot(sid, summary)
        chk = verify.check_citation(claim_text=cl.get("text", ""), quote=sent, source=srcs.get(sid) or src, source_text=summary)
        if chk.drop:
            continue
        ratio = verify.diff_ratio(target.value, best.value)
        code, txt = chk.reason_code, chk.reason_text
        if ratio < float(config.th("conflict_ratio", 0.2)):
            code, txt = "SUMMARY_CORROBORATED", verify.reason_text("SUMMARY_CORROBORATED")
        version.setdefault("citations", []).append({
            "claim_id": cid, "source_id": sid, "quote": verify.strip_ellipsis(sent), "highlight": None, "quote_span": None, "page": None,
            "check": chk.check, "status": "unverifiable", "reason_code": code, "reason_text": txt, "verified_at": now_iso(),
            "value": verify.num_to_dict(best), "corroboration": True})
        if code == "SUMMARY_CORROBORATED":
            for c in cits:
                c["reason_code"], c["reason_text"] = code, txt
        C.recompute(version, cid)
        done += 1
    return done


def _first_sentence(text: str, limit: int = 80) -> str:
    t = re.split(r"(?<=[.!?。])\s+", (text or "").strip())[0].strip()
    return t[:limit]


def samsung_cell(version: dict[str, Any], ev: list[dict[str, Any]], samsung: dict[str, Any], crt: dict[str, Any], known: list[str]) -> dict[str, Any]:
    """삼성 칸은 KB 에서만(§7.7) — 기준 이름 → 정규 스펙 키(같은 키 값이 여럿이면 속성 이름으로) → 없으면 E2 메시지 → 없으면 [확인 필요]."""
    spec = samsung.get("spec")
    if spec:
        r = spec_row_for(crt["name"], spec.get("rows") or [])
        if r:
            short = re.sub(r"\s*\(.*?\)", "", r["attr_name"]).strip()
            text = f"{spec['display']} {short} {r['raw']}"
            cid = ingest_claim(version, area="competitor", text=text, citations=[{"evidence_id": spec["evidence_id"], "quote": f"{r['attr_name']}: {r['raw']}"}],
                               ev_list=ev, block_path=f"table.{crt['id']}.samsung", known_names=known, cell={"crt": crt["id"], "col": "samsung"},
                               extra={"samsung_model": spec["model_code"]})
            return {"text": version["claims"][cid]["text"], "claim_ids": [cid], "placeholder": False}
    for m in (samsung.get("messages") or {}).get(crt["id"]) or []:
        sent = _first_sentence(m["text"])
        if not sent:
            continue
        cid = ingest_claim(version, area="competitor", text=sent, citations=[{"evidence_id": m["evidence_id"], "quote": sent}], ev_list=ev,
                           block_path=f"table.{crt['id']}.samsung", known_names=known, cell={"crt": crt["id"], "col": "samsung"})
        return {"text": version["claims"][cid]["text"], "claim_ids": [cid], "placeholder": False}
    return {"text": "[확인 필요]", "claim_ids": [], "placeholder": True}


class Refs:
    """LLM 이 id 대신 이름(기준 이름 · 경쟁사 실명 · `경쟁사 A` · 글자)으로 가리켜도 같은 행 · 열로 잇는다."""

    def __init__(self, crits: list[dict[str, Any]], comps: list[dict[str, Any]]):
        self.c: dict[str, str] = {}
        for c in crits:
            self.c[c["id"]] = c["id"]
            if c.get("name"):
                self.c[verify.N(c["name"])] = c["id"]
        self.p: dict[str, str] = {}
        for c in comps:
            for k in (c["id"], c.get("real_name"), anonymize.workspace_label(c), c.get("letter"), *(c.get("aliases") or [])):
                if k:
                    self.p[k] = c["id"]
                    self.p[verify.N(k)] = c["id"]

    def crit(self, x: str | None) -> str | None:
        return self.c.get(x or "") or self.c.get(verify.N(x or ""))

    def comp(self, x: str | None) -> str | None:
        return self.p.get(x or "") or self.p.get(verify.N(x or ""))


def comp_cell(version: dict[str, Any], ev: list[dict[str, Any]], cell: Any, known: list[str]) -> dict[str, Any]:
    text = (cell.text or "").strip()
    if not text or text in ("[확인 필요]", "[00]"):
        return {"text": "[확인 필요]", "claim_ids": [], "placeholder": True}
    cid = ingest_claim(version, area="competitor", text=text, citations=[c.model_dump() for c in cell.citations], ev_list=ev,
                       block_path=f"table.{cell.criterion_id}.{cell.competitor_id}", known_names=known,
                       cell={"crt": cell.criterion_id, "col": cell.competitor_id}, allow_kinds=("web", "websearch_summary", "file"),
                       extra={"competitor_id": cell.competitor_id})
    cl = version["claims"][cid]
    live = C.citations_of(version, cid)
    has_num = any(n.kind != "year" for n in verify.parse_numbers(text))
    if not live and not has_num:
        # 근거 없는 경쟁사 문장은 남기지 않는다(지어내기 금지)
        version["claims"].pop(cid, None)
        return {"text": "[확인 필요]", "claim_ids": [], "placeholder": True}
    ph = "[확인 필요]" in cl["text"] or "[00]" in cl["text"]
    return {"text": cl["text"], "claim_ids": [cid], "placeholder": ph}


async def organize_competitor(doc: dict[str, Any], version: dict[str, Any], ev: list[dict[str, Any]], samsung: dict[str, Any], memos: list[str],
                              budget: Budget) -> bool:
    drop_area(version, "competitor")
    known = known_names(doc)
    comps = anonymize.live(doc.get("competitors") or [])
    crits = service.ordered_criteria(doc.get("criteria") or [])
    cells: dict[str, dict[str, Any]] = {c["id"]: {} for c in crits}
    for crt in crits:
        cells[crt["id"]]["samsung"] = samsung_cell(version, ev, samsung, crt, known)
    ok = True
    if comps and crits:
        web_ev = [e for e in ev if e["kind"] in ("web", "websearch_summary", "file")]
        res = None
        if budget.take("llm"):
            try:
                res = await aix.llm("mi.compare_cells", prompts.compare_cells(crits, comps, web_ev, memos), prompts.Cells, confidential=True)
            except (aix.LLMFailed, ApiError) as exc:
                log.info("비교표 칸 LLM 실패: %s", exc)
                ok = False
        refs = Refs(crits, comps)
        for cell in (res.cells if res else []):
            crt, col = refs.crit(cell.criterion_id), refs.comp(cell.competitor_id)
            if crt in cells and col and col not in cells[crt]:
                cell.criterion_id, cell.competitor_id = crt, col
                cells[crt][col] = comp_cell(version, ev, cell, known)
        for crt in crits:
            for c in comps:
                cells[crt["id"]].setdefault(c["id"], {"text": "[확인 필요]", "claim_ids": [], "placeholder": True})
    table = {"criteria": [c["id"] for c in crits], "columns": [c["id"] for c in comps] + ["samsung"], "cells": cells,
             "criteria_names": {c["id"]: c["name"] for c in crits}}
    prods = [{k: p.get(k) for k in ("model_code", "family_id", "name", "ref", "kind", "origin")} for p in samsung.get("products") or []]
    version.setdefault("document", {})["competitor"] = {"table": table, "strengths": [], "samsung_products": prods}
    return ok


async def organize(state: AnalyzeState) -> dict[str, Any]:
    aid = state["analysis_id"]
    ctx = current_job()
    tracker = _tracker(state)
    memos = list(state.get("memos") or [])
    await memo_log(ctx, memos)
    todo = list(state.get("todo") or [])
    await tracker.set_stage("organize")
    doc = await _doc(aid)
    draft = await _draft(aid)
    version = draft.get("work") or {}
    evid = draft.get("evidence") or {}
    budget = _budget(draft.get("budget"), _depth(doc))
    samsung = draft.get("samsung") or {}
    sem = asyncio.Semaphore(config.organize_concurrency())

    async def call(area: str) -> tuple[Any, str | None]:
        async with sem:
            tracker.area_status[area] = "run"
            tracker.area_note[area] = _run_note(doc, area)
            await tracker.emit("영역별로 정리하고 있어요")
            if area == "competitor":
                return None, None
            if not budget.take("llm"):
                return None, "BUDGET"
            try:
                res = await aix.llm(f"mi.extract_claims_{area}", prompts.extract_claims(area, doc, (evid.get(area) or [])[:24], memos),
                                    prompts.EXTRACT_MODELS[area], confidential=True)
                return res, None
            except aix.LLMFailed:
                return None, "LLM_FAILED"
            except ApiError as exc:
                return None, exc.code

    tasks = {a: asyncio.create_task(call(a)) for a in todo}
    try:
        for a in todo:
            res, err = await tasks[a]
            if ctx is not None:
                await ctx.check_cancel()      # 중지 → 이 영역은 넣지 않고 정리된 영역만 남긴다
            ev = evid.get(a) or []
            if a == "competitor":
                ok = await organize_competitor(doc, version, ev, samsung, memos, budget)
                err = None if ok else "LLM_FAILED"
                if ok:
                    version["area_status"]["competitor"] = "wait"   # 작성 단계(판정 · 강점)가 끝나면 done
            elif res is None:
                drop_area(version, a)
            else:
                ingest_area(version, doc, a, res, ev)
                if a == "market":
                    await corroborate(doc, version, budget, sensitive_texts(doc))
            if err:
                version["area_status"][a] = "failed"
                version.setdefault("area_errors", {})[a] = err
                tracker.area_status[a] = "failed"
                tracker.area_note[a] = "정리하지 못했어요 · 다시 분석"
            else:
                if a != "competitor":
                    version["area_status"][a] = "done"
                tracker.area_status[a] = "done"
                tracker.area_note[a] = _done_note(doc, a, version)
            tracker.organized.add(a)
            tracker.set_counts(version)
            await _save_draft(aid, work=version, budget=_bdump(budget))
            await emit_partial(ctx, {"area": a, "status": version["area_status"].get(a)})
            await tracker.emit(f"{rules.AREA_TAB[a]} 정리를 마쳤어요" if not err else f"{rules.AREA_TAB[a]} 정리를 마치지 못했어요")
    finally:
        for t in tasks.values():
            if not t.done():
                t.cancel()
    tracker.stage_status["organize"] = "done"
    await memo_log(ctx, memos)
    return {"memos": memos}


# ── 작성 ─────────────────────────────────────────────────
async def _write_step(state: AnalyzeState, name: str) -> RunTracker:
    t = _tracker(state)
    if t.stage != "write":
        await t.set_stage("write")
    return t


async def build_comparison(state: AnalyzeState) -> dict[str, Any]:
    """판정(§7.7) — 기준 × 경쟁사마다 삼성 우위 · 비슷 · 열위 · 모름. 가중치만 바뀐 실행은 표 순서만 다시."""
    aid = state["analysis_id"]
    tracker = await _write_step(state, "build_comparison")
    todo = state.get("todo") or []
    draft = await _draft(aid)
    version = draft.get("work") or {}
    doc = await _doc(aid)
    cp = (version.get("document") or {}).get("competitor") or {}
    table = cp.get("table") or {}
    budget = _budget(draft.get("budget"), _depth(doc))
    if table and ("competitor" in todo or state.get("write_only")):
        order = [c["id"] for c in service.ordered_criteria(doc.get("criteria") or [])]
        table["criteria"] = [c for c in order if c in (table.get("cells") or {})] + [c for c in table.get("criteria") or [] if c not in order]
        names = {c["id"]: c["name"] for c in doc.get("criteria") or []}
        table.setdefault("criteria_names", {}).update({k: v for k, v in names.items() if k in table["criteria"]})
    if table and "competitor" in todo and version.get("area_status", {}).get("competitor") != "failed":
        rows = None
        if budget.take("llm"):
            try:
                rows = (await aix.llm("mi.verdicts", prompts.verdicts(table_text(doc, version)), prompts.Verdicts, confidential=True)).rows
            except (aix.LLMFailed, ApiError) as exc:
                log.info("판정 LLM 실패 → 모름: %s", exc)
        verdict: dict[tuple[str, str], str] = {}
        refs = Refs([{"id": k, "name": n} for k, n in (table.get("criteria_names") or {}).items()], anonymize.live(doc.get("competitors") or []))
        for r in rows or []:
            for v in r.verdicts:
                crt, col = refs.crit(r.criterion_id), refs.comp(v.competitor_id)
                if crt and col:
                    verdict[(crt, col)] = v.verdict
        for crt, row in (table.get("cells") or {}).items():
            for col, cell in row.items():
                if col == "samsung":
                    continue
                cell["verdict"] = "unknown" if cell.get("placeholder") or (row.get("samsung") or {}).get("placeholder") else verdict.get((crt, col), "unknown")
    await _save_draft(aid, work=version, budget=_bdump(budget))
    tracker.write_done += 1
    await tracker.emit("비교표를 쓰고 있어요")
    return {}


async def derive_strengths(state: AnalyzeState) -> dict[str, Any]:
    """삼성 강점 최대 3 — 점수 = 가중치 × 삼성 우위 경쟁사 수, 제목 ≤ 12자 · 근거 한 줄 ≤ 40자(수치는 사례 · KPI 인용 필수)."""
    aid = state["analysis_id"]
    tracker = await _write_step(state, "derive_strengths")
    todo = state.get("todo") or []
    draft = await _draft(aid)
    version = draft.get("work") or {}
    doc = await _doc(aid)
    budget = _budget(draft.get("budget"), _depth(doc))
    cp = (version.get("document") or {}).get("competitor") or {}
    table = cp.get("table") or {}
    if table and ("competitor" in todo or state.get("write_only")) and version.get("area_status", {}).get("competitor") != "failed":
        weights = {c["id"]: int(c.get("weight", 3)) for c in doc.get("criteria") or []}
        scored = []
        for i, crt in enumerate(table.get("criteria") or []):
            row = (table.get("cells") or {}).get(crt) or {}
            better = sum(1 for col, cell in row.items() if col != "samsung" and cell.get("verdict") == "samsung_better")
            if better:
                scored.append((weights.get(crt, 3) * better, -i, crt))
        scored.sort(reverse=True)
        picked = [crt for _, _, crt in scored[:3]]
        # 이전 강점 주장은 지우고 새로
        old = {cid for s in cp.get("strengths") or [] for cid in s.get("claim_ids") or [] if (version.get("claims") or {}).get(cid, {}).get("block_path", "").startswith("strengths")}
        version["claims"] = {k: v for k, v in (version.get("claims") or {}).items() if k not in old}
        version["citations"] = [c for c in version.get("citations") or [] if c.get("claim_id") not in old]
        strengths: list[dict[str, Any]] = []
        ev = list((draft.get("evidence") or {}).get("competitor") or [])
        if not ev:
            ev = _evidence_from_version(version, "competitor")
        if picked:
            names = (table.get("criteria_names") or {})
            pk = [{"criterion_id": c, "name": names.get(c, ""), "samsung": ((table.get("cells") or {}).get(c) or {}).get("samsung", {}).get("text", "")} for c in picked]
            ev_s = [e for e in ev if e["kind"] in ("kb_case", "kb_official")]
            res = None
            if budget.take("llm"):
                try:
                    res = await aix.llm("mi.strengths", prompts.strengths(pk, table_text(doc, version), ev_s), prompts.Strengths, confidential=True)
                except (aix.LLMFailed, ApiError) as exc:
                    log.info("강점 LLM 실패 → 삼성 칸으로: %s", exc)
            known = known_names(doc)
            used: set[str] = set()
            refs = Refs([{"id": k, "name": n} for k, n in names.items()], [])
            for s in res.strengths if res else []:
                crt = refs.crit(s.criterion_id)
                if crt not in picked or crt in used:
                    continue
                used.add(crt)
                title = _clean_free(s.title, _area_quotes(version, "competitor"), "\n".join(e.get("text", "") for e in ev))[:12] or names.get(crt, "")[:12]
                cid = ingest_claim(version, area="competitor", text=(s.note or "").strip()[:60] or "[확인 필요]",
                                   citations=[c.model_dump() for c in s.citations], ev_list=ev, block_path=f"strengths.{len(strengths)}", known_names=known)
                if not C.citations_of(version, cid):
                    # 근거를 못 단 강점 문장 → 삼성 칸(KB 근거)을 근거로 쓰고, 수치가 든 문장은 삼성 칸 문장으로 바꾼다(§7.6.6)
                    cl = version["claims"].pop(cid)
                    version["citations"] = [c for c in version.get("citations") or [] if c.get("claim_id") != cid]
                    cell = ((table.get("cells") or {}).get(crt) or {}).get("samsung") or {}
                    has_num = any(n.kind != "year" for n in verify.parse_numbers(s.note or ""))
                    note = cell.get("text", "")[:40] if has_num or "[00]" in cl.get("text", "") else (s.note or "").strip()[:40]
                    strengths.append({"id": nid("str"), "title": title, "note": note, "criterion_ids": [crt], "claim_ids": list(cell.get("claim_ids") or [])})
                    continue
                strengths.append({"id": nid("str"), "title": title, "note": version["claims"][cid]["text"], "criterion_ids": [crt], "claim_ids": [cid]})
            for crt in picked:
                if crt in used or len(strengths) >= 3:
                    continue
                cell = ((table.get("cells") or {}).get(crt) or {}).get("samsung") or {}
                if cell.get("placeholder"):
                    continue
                strengths.append({"id": nid("str"), "title": names.get(crt, "")[:12], "note": cell.get("text", "")[:40], "criterion_ids": [crt],
                                  "claim_ids": list(cell.get("claim_ids") or [])})
        cp["strengths"] = strengths[:3]
        version["area_status"]["competitor"] = "done"
        tracker.area_note["competitor"] = _done_note(doc, "competitor", version)
        await emit_partial(current_job(), {"area": "competitor", "status": "done"})
    await _save_draft(aid, work=version, budget=_bdump(budget))
    tracker.write_done += 1
    await tracker.emit("삼성 강점을 고르고 있어요")
    return {}


def _evidence_from_version(version: dict[str, Any], area: str) -> list[dict[str, Any]]:
    """작업본에 근거가 없을 때(가중치만 바뀐 실행) — 그 영역 출처 스냅숏 · 인용 구절로 근거를 다시 만든다."""
    ev: list[dict[str, Any]] = []
    for sid, s in (version.get("sources") or {}).items():
        if area not in (s.get("areas") or []) or s.get("state") == "excluded":
            continue
        text, _ = R.load_snapshot(sid)
        if not text:
            text = "\n".join(c.get("quote") or "" for c in version.get("citations") or [] if c.get("source_id") == sid)
        if text:
            evidence(ev, source_id=sid, kind=s.get("kind", "web"), title=s.get("title", ""), text=text[:4000])
    return ev


async def implications(state: AnalyzeState) -> dict[str, Any]:
    """쓰임이 solution · exec_onepager 일 때 IM 시트 내용 — 결과 문장 · 수치만(새 사실 없음, §7.6.6 검사)."""
    aid = state["analysis_id"]
    tracker = await _write_step(state, "implications")
    doc = await _doc(aid)
    usage = (doc.get("usage") or {}).get("value")
    draft = await _draft(aid)
    version = draft.get("work") or {}
    budget = _budget(draft.get("budget"), _depth(doc))
    if usage in ("solution", "exec_onepager") and (state.get("todo") or state.get("write_only")):
        lines = []
        for a in rules.AREAS:
            if (version.get("area_status") or {}).get(a) in ("done", "reused"):
                for cid in views.claim_order(version.get("document") or {}, a)[:8]:
                    c = (version.get("claims") or {}).get(cid) or {}
                    lines.append(f"[{rules.AREA_TAB[a]}] {c.get('text', '')}")
        quotes = [{"quote": c.get("text", "")} for c in (version.get("claims") or {}).values()]
        comps = doc.get("competitors") or []
        out: dict[str, Any] = {}
        if lines and budget.take("llm"):
            try:
                res = await aix.llm("mi.implications", prompts.implications("\n".join(lines)[:6000]), prompts.Implications, confidential=True)
                out = {"findings": [verify.mask_unsupported(x, quotes)[0] for x in res.findings[:4]],
                       "implications": [verify.mask_unsupported(x, quotes)[0] for x in res.implications[:4]],
                       "direction": verify.mask_unsupported(res.direction, quotes)[0]}
                if usage == "exec_onepager" and budget.take("llm"):
                    op = await aix.llm("mi.onepager", prompts.onepager("\n".join(lines)[:6000]), prompts.Onepager, confidential=True)
                    out["quadrants"] = {a: verify.mask_unsupported(getattr(op, a), quotes)[0] for a in rules.AREAS}
                    out["conclusion"] = verify.mask_unsupported(op.conclusion, quotes)[0]
            except (aix.LLMFailed, ApiError) as exc:
                log.info("시사점 LLM 실패: %s", exc)
        if out:
            # 시사점 문장은 작업 안 분석이라 실명이 들어갈 수 있다 — 내보내기에서 익명 처리(bundle scrub)
            version.setdefault("document", {})["implications"] = anonymize.scrub(out, comps, {}) if doc.get("anonymize", True) else out
    await _save_draft(aid, work=version, budget=_bdump(budget))
    tracker.write_done += 1
    await tracker.emit()
    return {}


async def reconcile(state: AnalyzeState) -> dict[str, Any]:
    """영역 사이 같은 지표(metric_key) 충돌 · 숫자 칸 다시 읽기 · 출처 정리(§7.5 reconcile)."""
    aid = state["analysis_id"]
    tracker = await _write_step(state, "reconcile")
    draft = await _draft(aid)
    version = draft.get("work") or {}
    claims = version.get("claims") or {}
    by_key: dict[str, list[tuple[str, verify.Num]]] = {}
    for cid, c in claims.items():
        mk = c.get("metric_key")
        if not mk or "[00]" in (c.get("text") or "") or c.get("status") in ("missing", "confirmed"):
            continue
        nums = [n for n in verify.parse_numbers(c.get("text", "")) if n.kind != "year"]
        if nums:
            by_key.setdefault(mk, []).append((cid, nums[0]))
    for mk, items in by_key.items():
        areas = {claims[cid].get("area") for cid, _ in items}
        if len(items) < 2 or len(areas) < 2:
            continue
        for i, (a_id, a_n) in enumerate(items):
            for b_id, b_n in items[i + 1:]:
                if a_n.unit == b_n.unit and verify.diff_ratio(a_n.value, b_n.value) >= float(config.th("conflict_ratio", 0.2)):
                    for cid, other in ((a_id, b_n), (b_id, a_n)):
                        cl = claims[cid]
                        if cl.get("status") == "conflict":
                            continue
                        cl["status"] = "conflict"
                        cl["label"] = verify.claim_label("conflict")
                        cl["conflict"] = {"values": [{"claim_id": cid, "value": verify.metric_value(cl)[0], "unit": a_n.unit},
                                                     {"value": other.value, "unit": other.unit}], "cross_area": True,
                                          "diff_ratio": round(verify.diff_ratio(a_n.value, b_n.value), 2), "primary_source_id": None}
    refresh_numeric_fields(version)
    await _save_draft(aid, work=version)
    tracker.write_done += 1
    await tracker.emit()
    return {}


INTENT_PICK = {"MS": {"why": "MS-E", "how_much": "MS-B", "who": "MS-D"}, "TR": {"why": "TR-B", "how_much": "TR-C", "who": "TR-B"},
               "CB": {"why": "CB-B", "how_much": "CB-A", "who": "CB-C"}, "US": {"why": "US-B", "how_much": "US-C", "who": "US-A"},
               "CP": {"why": "CP-A", "how_much": "CP-C", "who": "CP-B"}}


async def compose_slides(state: AnalyzeState) -> dict[str, Any]:
    """§7.8 — 시장 레이아웃에 필요한 값이 없으면 그 데이터만 1회 추가 검색 → 그래도 없으면 대체 템플릿 + 자리표시 주장(확정 필요)."""
    aid = state["analysis_id"]
    tracker = await _write_step(state, "compose_slides")
    doc = await _doc(aid)
    draft = await _draft(aid)
    version = draft.get("work") or {}
    budget = _budget(draft.get("budget"), _depth(doc))
    todo = state.get("todo") or []
    sens = sensitive_texts(doc)
    if "market" in todo and (version.get("area_status") or {}).get("market") == "done":
        m = layout.metrics(doc, version)
        if not (m["size_years"] >= 3 or (m["size_years"] >= 1 and m["cagr"] >= 1)):
            s = config.segment(_seg(doc))
            ev = list((draft.get("evidence") or {}).get("market") or [])
            q = f"{s['market'] if s['code'] != 'GEN' else ''} {s['product']} 시장 규모 연도별 추이".strip()
            added = await gather_query(version, ev, budget, tracker, task="mi.web_layout", query=q, area="market", sensitive=sens)
            if added and budget.take("llm"):
                try:
                    res = await aix.llm("mi.extract_claims_market", prompts.extract_claims("market", doc, ev[:24], state.get("memos") or []),
                                        prompts.MarketExtract, confidential=True)
                    ingest_area(version, doc, "market", res, ev)
                except (aix.LLMFailed, ApiError) as exc:
                    log.info("시장 다시 정리 실패: %s", exc)
            m = layout.metrics(doc, version)
            mk = (version.get("document") or {}).setdefault("market", {})
            if m["size_years"] == 0 and not any("[00]" in (version["claims"].get(p.get("claim") or "", {}).get("text") or "") for p in mk.get("size_series") or []):
                # 모자란 값 → 자리표시 주장 = 확정 필요 항목(MIC 6 · AC-MI-60)
                unit = mk.get("size_unit") or "억 원"
                label = f"{s['market'] + ' ' if s['code'] != 'GEN' else ''}{s['product']} 시장 규모"
                cid = ingest_claim(version, area="market", text=f"{label} [00]{unit}", citations=[], ev_list=ev, block_path="size_series.0",
                                   metric_key="market_size", metric_label=label)
                mk.setdefault("size_series", []).append({"year": rules.now().year, "claim": cid, "value": None, "unit": unit})
                mk.setdefault("size_unit", unit)
    # 대표 메시지(왜 · 얼마나 · 누구)로 비긴 시트 고르기
    plan_rows = layout.sheet_plan(doc, version, previous=version.get("slides") or [])
    intents: dict[str, str] = {}
    for r in plan_rows:
        if r["pinned"] or r["industry_layout"] or r["sheet_type"] not in INTENT_PICK:
            continue
        alts = [a for a in r.get("alternatives") or [] if a.get("fit", -1) >= 0]
        if not alts or r["fit"] - alts[0]["fit"] >= int(config.th("layout_tie", 5)):
            continue
        cids = views.claim_order(version.get("document") or {}, r["area"] or "market")[:1]
        text = ((version.get("claims") or {}).get(cids[0]) or {}).get("text") if cids else None
        if not text or not budget.take("llm"):
            continue
        try:
            it = await aix.llm("mi.message_intent", f"이 시트의 대표 주장이 '왜' · '얼마나' · '누구' 중 무엇을 말하는지 골라라.\n주장: {text}", prompts.MessageIntent,
                               confidential=True)
            intents[r["sheet_type"]] = INTENT_PICK[r["sheet_type"]][it.intent]
        except (aix.LLMFailed, ApiError):
            pass
    version["slides"] = layout.sheet_plan(doc, version, previous=version.get("slides") or [], intents=intents or None)
    await _save_draft(aid, work=version, budget=_bdump(budget))
    tracker.write_done += 1
    await tracker.emit("시트 구성을 고르고 있어요")
    return {}


async def schedule_recheck(doc: dict[str, Any], base_ts: float) -> str:
    """30일 재확인 예약(이전 예약 교체, AC-MI-76)."""
    days = int(config.th("recheck_days", 30))
    run_at = base_ts + days * 86400
    sid = f"sch_mi_recheck_{doc['id']}"
    try:
        await jobs().unschedule(sid)
        await jobs().schedule("mi", "mi.recheck", {"analysis_id": doc["id"]}, run_at, title="30일 재확인", ref=doc["id"],
                              owner=doc.get("owner_id"), schedule_id=sid)
    except Exception as exc:  # noqa: BLE001
        log.warning("재확인 예약 실패: %s", exc)
    return datetime.fromtimestamp(run_at, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def finalize(state: AnalyzeState) -> dict[str, Any]:
    aid = state["analysis_id"]
    ctx = current_job()
    doc = await _doc(aid)
    draft = await _draft(aid)
    version = draft.get("work") or {}
    hashes = draft.get("hashes") or {}
    budget = _budget(draft.get("budget"), _depth(doc))
    todo = state.get("todo") or []
    for a in todo:
        if (version.get("area_status") or {}).get(a) == "done":
            version.setdefault("area_hashes", {})[a] = hashes.get(a)
    if "competitor" in (state.get("areas") or []) and (version.get("area_status") or {}).get("competitor") in ("done", "reused"):
        version.setdefault("area_hashes", {})["competitor_write"] = hashes.get("competitor_write")
    version["web_unavailable"] = bool(budget.web_unavailable or version.get("web_unavailable"))
    version["web_mode"] = budget.mode
    version["budget_used"] = dict(budget.used)
    mode = state.get("mode") or "auto"
    kind = mode if mode in ("full", "changed_only", "resume") else "auto"
    failed = [a for a in todo if (version.get("area_status") or {}).get(a) == "failed"]
    summary = (f"{rules.scope_label(todo)} 분석" if todo else "작성만 다시") + (f" · 실패 {rules.scope_label(failed)}" if failed else "")
    n = await versions.save_new_version(doc, version, kind=kind, summary=summary, recompose_slides=False, status="done")
    t = time.time()
    analyzed = datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    nxt = await schedule_recheck(doc, t)

    def done(d: dict[str, Any]) -> None:
        d["analyzed_at"] = analyzed
        d["current_job_id"] = None
        d["last_screen"] = "result" if d.get("last_screen") in ("run", None, "") else d.get("last_screen")
        d["upd_changes"] = []
        d["next_recheck_at"] = nxt
        d["recheck_schedule_id"] = f"sch_mi_recheck_{aid}"
        d.setdefault("run", {}).update(stage="write", finished_at=analyzed, failed_areas=failed, web_unavailable=version["web_unavailable"])

    saved = await R.call(R.update_analysis, aid, done)
    await service.register(saved)
    await R.call(R.delete_draft, aid)
    if ctx is not None:
        await ctx.log(f"분석을 마쳤어요 · v{n}")
        await ctx.progress(100, "분석을 마쳤어요", eta_s=0, stage="write")
    return {}


# ── 중지 · 실패 ──────────────────────────────────────────
async def save_partial(aid: str, mode: str) -> int | None:
    """중지 — `정리 완료` 영역만으로 stopped 버전 저장, 상태 stopped(§7.5 save_partial · AC-MI-24)."""
    doc = await R.call(R.get_analysis, aid)
    if doc is None:
        return None
    draft = await _draft(aid)
    version = draft.get("work") or {}
    st = version.get("area_status") or {}
    done = [a for a in rules.AREAS if st.get(a) in ("done", "reused")]
    n = None
    if done and version:
        for a in rules.AREAS:
            if a in st and a not in done:
                drop_area(version, a)
                st.pop(a, None)
        hashes = draft.get("hashes") or {}
        for a in done:
            if st.get(a) == "done":
                version.setdefault("area_hashes", {})[a] = hashes.get(a)
        version["stopped"] = True
        n = await versions.save_new_version(doc, version, kind=mode if mode in ("full", "changed_only", "resume") else "auto",
                                            summary=f"중지 · 정리된 영역 {len(done)}개", stopped=True, status="stopped", recompose_slides=True)

    def upd(d: dict[str, Any]) -> None:
        d["status"] = "stopped"
        d["current_job_id"] = None
        d.setdefault("run", {}).update(stopped_at=now_iso())

    saved = await R.call(R.update_analysis, aid, upd)
    await service.register(saved)
    await R.call(R.delete_draft, aid)
    return n


async def _mark_failed(aid: str, exc: Exception) -> None:
    def upd(d: dict[str, Any]) -> None:
        d["status"] = "failed"
        d["current_job_id"] = None
        d.setdefault("run", {}).update(error={"code": str(getattr(exc, "code", type(exc).__name__)),
                                              "message": str(getattr(exc, "message", str(exc)))[:300]})

    try:
        saved = await R.call(R.update_analysis, aid, upd)
        await service.register(saved)
    except Exception:  # noqa: BLE001
        log.exception("실패 표시 실패")


# ── 그래프 ───────────────────────────────────────────────
def build() -> StateGraph:
    g = StateGraph(AnalyzeState)
    for name, fn in (("load", load), ("plan", plan), ("gather", gather), ("organize", organize), ("build_comparison", build_comparison),
                     ("derive_strengths", derive_strengths), ("implications", implications), ("reconcile", reconcile),
                     ("compose_slides", compose_slides), ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "load")
    g.add_edge("load", "plan")
    g.add_edge("plan", "gather")
    g.add_edge("gather", "organize")
    g.add_edge("organize", "build_comparison")
    g.add_edge("build_comparison", "derive_strengths")
    g.add_edge("derive_strengths", "implications")
    g.add_edge("implications", "reconcile")
    g.add_edge("reconcile", "compose_slides")
    g.add_edge("compose_slides", "finalize")
    g.add_edge("finalize", END)
    return g


async def handle(ctx: JobContext) -> dict[str, Any] | None:
    aid = ctx.payload["analysis_id"]
    mode = ctx.payload.get("mode") or "auto"
    init: AnalyzeState = {"analysis_id": aid, "job_id": ctx.job.id, "mode": mode, "req_areas": list(ctx.payload.get("areas") or [])}
    try:
        await run_graph(ctx, build(), dict(init), step_labels=STEP_LABELS)
    except JobCanceled:
        await save_partial(aid, mode)
        raise
    except Exception as exc:
        await _mark_failed(aid, exc)
        raise
    finally:
        _TRACKERS.pop(ctx.job.id, None)
    doc = await R.call(R.get_analysis, aid) or {}
    v = await R.call(R.get_version, aid, int(doc.get("result_version") or 0)) or {}
    return {"analysis_id": aid, "version": int(doc.get("result_version") or 0), "web_unavailable": bool(v.get("web_unavailable")),
            "failed_areas": (doc.get("run") or {}).get("failed_areas") or []}
