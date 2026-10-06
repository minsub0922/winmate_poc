"""워크플로(05-vp.md §7) — LangGraph 그래프 + 잡 처리기.

- vp.materials  vp_materials  재료 수집 · 판별(12 노드, `ask` 에서 HITL interrupt)
- vp.generate   vp_generate   생성 5단계(재료 정리 · 구조 결정 · 시트 작성 · 레이아웃 맞춤 · 검토)
- vp.revise     vp_revise     지시 · 레이아웃 · 수치 반영 · 변형 시트 · 업종판 적용
- vp.images     vp_images     고객 사진 배치 · 일러스트 통일
- vp.export     vp_export     PPTX · PDF 한 장 요약
- vp.pack_offer vp_pack_offer 업종판 출시 → 교체 제안

그래프 상태는 vp_id 뿐이다(체크포인트가 가볍게). 노드는 문서를 읽고 → 계산하고(모델 · KB) → `service.mutate` 로 결과만 쓴다.
진행 이벤트: progress(% · eta_seconds) · step({step, status, stage, label, activity?, sheet_id?, sheet_status?}) · log({message, t, mode, stage}).
"""
from __future__ import annotations

import asyncio
import copy
import logging
import os
import re
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import AwaitingInput, JobCanceled, JobContext, current_job, jobs

from . import (catalog, collect, config, exporting, fit, guards, imagesel, kbx, llm, models, numbers, ops_result, ops_work, package,
               repo, service, signals, writer)

log = logging.getLogger("winmate.vp.workflows")


class S(TypedDict, total=False):
    vp_id: str
    result: dict[str, Any]


def pace() -> float:
    try:
        return float(os.environ.get("VP_PACE_S") or (config.routing().get("dev") or {}).get("pace_s") or 0)
    except ValueError:
        return 0.0


async def nap(k: float = 1.0) -> None:
    p = pace() * k
    if p > 0:
        await asyncio.sleep(p)


def ctx() -> JobContext:
    c = current_job()
    assert c is not None
    return c


async def load(vp_id: str) -> dict[str, Any]:
    return await repo.require_vp(vp_id)


async def decide_log(vp_id: str, stage: int, text: str, mode: str = "auto", *, key: str = "", value: str = "") -> None:
    """결정 기록 — 문서에 남기고 jobs `log` 이벤트로도 보낸다(VP3G)."""
    c = ctx()
    row = service.stamp_decision(stage, text, mode, key=key, value=value, job_id=c.job.id)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d.setdefault("decisions", []).append(row)
        return d
    await service.mutate(vp_id, fn)
    await c.log(text, t=row["t"], mode=mode, stage=stage, id=row["id"])


async def step(name: str, stage: int, label: str, activity: str | None = None, **data: Any) -> None:
    await ctx().step(name, "running", stage=stage, label=label, activity=activity, **data)


async def progress(vp_id: str, pct: int, message: str, *, n_sheets: int = 3) -> None:
    total = max(1, n_sheets) * int(config.th("seconds_per_sheet"))
    eta = max(0, round((100 - pct) / 100 * total))
    await ctx().progress(pct, message, eta_seconds=eta)
    await service.set_job_progress(vp_id, ctx().job.id, pct)


# ── vp_materials ───────────────────────────────────────────

M_LABELS = {"load_sources": "재료 정리", "read_attachments": "첨부 읽기", "classify_industry": "업종 판별", "extract_materials": "재료 뽑기",
            "reconcile": "정리", "infer_from_memo": "메모로 추론", "fill_numbers": "수치 찾기", "coverage": "커버리지",
            "detect_questions": "되물을 것", "plan": "구조 계산", "ask": "답 기다림", "finish": "마무리"}
M_PROGRESS = {"load_sources": 10, "read_attachments": 25, "classify_industry": 32, "extract_materials": 50, "reconcile": 62,
              "infer_from_memo": 66, "fill_numbers": 78, "coverage": 80, "detect_questions": 88, "plan": 92, "ask": 95, "finish": 100}


async def m_load_sources(state: S) -> S:
    vp_id = state["vp_id"]
    await step("load_sources", 1, "재료 정리", "연결한 자료를 지금 판으로 다시 읽어요")
    doc = await load(vp_id)
    srcs = await collect.refresh_sources(doc)
    pack = await repo.pack_status_map()

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if srcs:
            ops_work.apply_sources(d, srcs, pack)
        d.setdefault("facts", {})["keymen"] = collect.stakeholder_from_keymen(d)
        d["decisions"] = []
        return d
    await service.mutate(vp_id, fn)
    return {}


async def m_read_attachments(state: S) -> S:
    vp_id = state["vp_id"]
    doc = await load(vp_id)
    pend = [a for a in doc.get("attachments") or [] if a.get("status") != "read"]
    if pend:
        await step("read_attachments", 1, "첨부 읽기", f"첨부 {len(pend)}개 — 종류를 보고 평가 기준 · 결재 구조 · 견적을 읽어요")
    done = {}
    for a in pend:
        done[a["id"]] = await collect.read_attachment(a)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["attachments"] = [done.get(a["id"], a) for a in d.get("attachments") or []]
        collect.merge_attachment_facts(d)
        return d
    await service.mutate(vp_id, fn)
    return {}


def _industry_text(ind: dict[str, Any]) -> tuple[str, str]:
    name = ind.get("cell") or ind.get("name") or "범용"
    if ind.get("mode") == "pin":
        return f"업종 {name} — 직접 고름", "pin"
    if ind.get("source") in ("mi", "storyboard", "requirements", "vp", "proposal"):
        frm = ind.get("inherited_from") or {"mi": "MI", "storyboard": "Storyboard", "vp": "복제 원본"}.get(ind.get("source") or "", "연결 자료")
        return f"업종 {name} — {frm}에서 상속", "auto"
    if ind.get("code") == "GEN":
        return "업종 판별 확신이 낮아 범용으로", "auto"
    if ind.get("mode") == "ask":
        t = ind.get("top2") or []
        pair = " : ".join("{} {:.2f}".format(config.industry(x["code"])["cell"], float(x["score"])) for x in t[:2])
        return f"업종 두 갈래({pair}) → 한 번 묻기", "ask"
    return f"업종 {name} {float(ind.get('confidence') or 0):.2f} — 자동 판별", ind.get("mode") or "auto"


async def m_classify_industry(state: S) -> S:
    vp_id = state["vp_id"]
    await step("classify_industry", 2, "업종 판별", "MI와 같은 기준으로 업종을 판별해요")
    doc = await load(vp_id)
    pack = await repo.pack_status_map()
    ind = await collect.classify_industry(doc, pack)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if (d.get("industry") or {}).get("mode") != "pin" and ind:
            d["industry"] = ind
        return d
    doc = await service.mutate(vp_id, fn)
    if doc.get("industry"):
        text, mode = _industry_text(doc["industry"])
        await decide_log(vp_id, 2, text, mode, key="industry", value=doc["industry"].get("code") or "")
    return {}


async def m_extract_materials(state: S) -> S:
    vp_id = state["vp_id"]
    await step("extract_materials", 1, "재료 뽑기", "과제 · 가치 · 근거 · 이해관계자 · 제품 5축으로 뽑아요")
    doc = await load(vp_id)
    cands = collect.all_candidates(doc)
    items, topic = await collect.extract_materials(doc, cands)
    work = copy.deepcopy(doc)
    items = await collect.resolve_products(work, items)
    collect.group_fill(items)
    wf = work.get("facts") or {}
    pf = (doc.get("facts") or {}).get("preview_facts") or {}
    km = sum(1 for c in cands if c.get("km_id"))

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["materials"] = items
        f = d.setdefault("facts", {})
        f["products"] = wf.get("products") or []
        if wf.get("spaces"):
            f["spaces"] = wf["spaces"]
        f["km_count"] = km
        f["strengths"] = int(pf.get("strengths") or sum(1 for c in cands if c.get("strength")))
        f["mi_users"] = list(pf.get("mi_users") or [c["text"] for c in cands if c.get("mi_user")])
        f["candidates_n"] = len(cands)
        if topic:
            f["topic"] = topic
        return d
    await service.mutate(vp_id, fn)
    return {}


async def m_reconcile(state: S) -> S:
    vp_id = state["vp_id"]
    await step("reconcile", 1, "정리", "같은 말은 합치고, 부딪치는 말은 고쳐 쓰고, 오래된 출처는 다시 찾아요")
    doc = await load(vp_id)
    items, fixes, conflict = await collect.reconcile(doc, copy.deepcopy(doc.get("materials") or []))

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["materials"] = items
        d["fixes"] = fixes
        d.setdefault("facts", {})["conflict"] = conflict
        return d
    await service.mutate(vp_id, fn)
    n_auto = sum(1 for f in fixes if f["mode"] == "auto")
    n_chk = sum(1 for f in fixes if f["mode"] == "check")
    if fixes:
        await decide_log(vp_id, 1, f"재료 정리 — 자동 {n_auto} · 확인 권장 {n_chk}", "check" if n_chk else "auto")
    return {}


async def m_infer_from_memo(state: S) -> S:
    vp_id = state["vp_id"]
    doc = await load(vp_id)
    p = signals.planner_input(doc)
    if not p.memo_only and signals.active(doc, "challenge"):
        return {}
    if not p.memo_only:
        return {}
    await step("infer_from_memo", 1, "메모로 추론", "한 줄 메모뿐이라 사례 DB로 과제를 추론해요")
    items = await collect.infer_from_memo(doc, copy.deepcopy(doc.get("materials") or []))

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["materials"] = items
        return d
    await service.mutate(vp_id, fn)
    await decide_log(vp_id, 1, "한 줄 메모뿐 → 사례 DB로 과제 추론", "check", key="memo")
    return {}


async def m_fill_numbers(state: S) -> S:
    vp_id = state["vp_id"]
    await step("fill_numbers", 6, "수치 찾기", "고객 자료 → 유관 사례 → 업종 평균 순서로 전 → 후 수치를 찾아요")
    doc = await load(vp_id)
    work = copy.deepcopy(doc)
    metrics = await collect.fill_numbers(work, [m for m in work.get("materials") or [] if not m.get("excluded")])
    wf = work.get("facts") or {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        f = d.setdefault("facts", {})
        for k in ("metrics", "per_product_numbers", "same_vertical_case", "case_photo"):
            if k in wf:
                f[k] = wf[k]
        return d
    await service.mutate(vp_id, fn)
    est = [m for m in metrics if numbers.projected_usable(m) == "estimated"]
    if est:
        await decide_log(vp_id, 6, f"근거 수치 {len(est)}개는 사례 범위로 넣고 [추정] 표시", "check", key="estimate")
    return {}


async def m_coverage(state: S) -> S:
    return {}


async def m_detect_questions(state: S) -> S:
    vp_id = state["vp_id"]
    await step("detect_questions", 3, "되물을 것", "방향 · 결재자 · 업종 · 충돌 중 물어볼 것만 골라요")
    doc = await load(vp_id)
    work = copy.deepcopy(doc)
    items = [m for m in work.get("materials") or [] if not m.get("excluded")]
    qs = await collect.detect_questions(work, items, (work.get("facts") or {}).get("conflict"))
    wf = work.get("facts") or {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        f = d.setdefault("facts", {})
        f["themes"] = wf.get("themes") or []
        f["direction_summary"] = wf.get("direction_summary")
        if wf.get("direction_from_note"):
            f["direction_from_note"] = wf["direction_from_note"]
        else:
            f.pop("direction_from_note", None)
        d["questions"] = qs
        return d
    await service.mutate(vp_id, fn)
    if wf.get("direction_from_note"):
        lab = next((t["label"] for t in wf.get("themes") or [] if t["kind"] == wf["direction_from_note"]), "")
        await decide_log(vp_id, 3, f"메모에 우선순위가 있어요 → {lab} 먼저", "pin", key="direction", value=wf["direction_from_note"])
    for q in qs:
        await decide_log(vp_id, 3 if q["kind"] == "direction" else 2, f"{q['title'].split(' · ', 1)[-1]} → {'선택 필요' if q['mode'] == 'ask' else '확인 권장'}",
                         q["mode"], key=q["kind"])
    return {}


async def m_plan(state: S) -> S:
    vp_id = state["vp_id"]
    pack = await repo.pack_status_map()

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.replan(d, pack)
        return d
    await service.mutate(vp_id, fn)
    return {}


def apply_default_answers(d: dict[str, Any], pack: dict[str, str], answers: list[dict[str, Any]] | None = None) -> None:
    """답이 없는 열린 질문을 추천값(by default) 또는 주어진 답으로."""
    given = {a.get("question_id"): a for a in answers or []}
    for q in [x for x in d.get("questions") or [] if x.get("status") == "open"]:
        a = given.get(q["id"]) or {}
        keys = list(a.get("keys") or q.get("selected_keys") or q.get("default_keys") or [])
        by = "default" if sorted(keys) == sorted(q.get("default_keys") or []) and not a.get("text") else "user"
        q["answer"] = {"keys": keys, "text": a.get("text"), "by": by}
        q["status"] = "defaulted" if by == "default" else "answered"
        q["selected_keys"] = keys
        ops_work._answer_effects(d, q, keys, pack)
        label = " · ".join(o["label"] for o in q.get("options") or [] if o["key"] in keys) or ", ".join(keys)
        d.setdefault("decisions", []).append(service.stamp_decision(
            3 if q["kind"] == "direction" else 2, f"{q['title'].split(' · ', 1)[-1]} → {label}" + (" (추천값)" if by == "default" else ""),
            "check" if by == "default" else "pin", key=q["kind"], value=label))
    service.replan(d, pack)


async def m_ask(state: S) -> S:
    vp_id = state["vp_id"]
    doc = await load(vp_id)
    opened = service.open_questions(doc)
    if not opened:
        return {}
    pack = await repo.pack_status_map()
    if doc.get("auto_answer"):
        def auto(d: dict[str, Any]) -> dict[str, Any]:
            apply_default_answers(d, pack)
            return d
        await service.mutate(vp_id, auto)
        return {}
    job_id = ctx().job.id

    def wait(d: dict[str, Any]) -> dict[str, Any] | None:
        aj = d.get("active_job") or {}
        if aj.get("job_id") != job_id:
            return None
        aj["status"] = "awaiting_input"
        return d
    await service.mutate(vp_id, wait)
    answer = interrupt({"question_ids": [q["id"] for q in opened], "vp_id": vp_id, "route": f"/vp/{vp_id}/questions",
                        "kinds": [q["kind"] for q in opened]})
    answers = (answer or {}).get("answers") if isinstance(answer, dict) else None

    def resume(d: dict[str, Any]) -> dict[str, Any]:
        if service.open_questions(d):
            apply_default_answers(d, pack, answers)
        aj = d.get("active_job") or {}
        if aj.get("job_id") == job_id:
            aj["status"] = "running"
        return d
    await service.mutate(vp_id, resume)
    return {}


async def m_finish(state: S) -> S:
    vp_id = state["vp_id"]

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["materials_ready"] = True
        if d.get("status") in ("collecting", "draft", "failed", "stopped"):
            d["status"] = "planned"
        return d
    await service.mutate(vp_id, fn)
    doc = await service.save_point(vp_id, "재료 완료")
    route = next_route_after_materials(doc)
    return {"result": {"vp_id": vp_id, "next_route": route}}


def next_route_after_materials(doc: dict[str, Any]) -> str:
    vid = doc["id"]
    if doc.get("fixes") and any(f.get("mode") == "check" and f.get("decision") == "pending" for f in doc["fixes"]):
        return f"/vp/{vid}/materials/review"
    if service.open_questions(doc):
        return f"/vp/{vid}/questions"
    if doc.get("fixes"):
        return f"/vp/{vid}/materials/review"
    return f"/vp/{vid}/structure"


def build_materials() -> StateGraph:
    g = StateGraph(S)
    order = ["load_sources", "read_attachments", "classify_industry", "extract_materials", "reconcile", "infer_from_memo",
             "fill_numbers", "coverage", "detect_questions", "plan", "ask", "finish"]
    fns = {"load_sources": m_load_sources, "read_attachments": m_read_attachments, "classify_industry": m_classify_industry,
           "extract_materials": m_extract_materials, "reconcile": m_reconcile, "infer_from_memo": m_infer_from_memo,
           "fill_numbers": m_fill_numbers, "coverage": m_coverage, "detect_questions": m_detect_questions, "plan": m_plan,
           "ask": m_ask, "finish": m_finish}
    for n in order:
        g.add_node(n, fns[n])
    g.add_edge(START, order[0])
    for a, b in zip(order, order[1:]):
        g.add_edge(a, b)
    g.add_edge(order[-1], END)
    return g


# ── vp_generate ───────────────────────────────────────────

G_LABELS = {"prepare": "재료 정리", "decide": "구조 결정", "write_sheets": "시트 작성", "fit_layout": "레이아웃 맞춤", "review": "검토"}
G_STAGE = {"prepare": 1, "decide": 2, "write_sheets": 3, "fit_layout": 4, "review": 5}


def sheets_from_plan(d: dict[str, Any], *, keep_done: bool) -> list[dict[str, Any]]:
    """플랜 → 시트(역할별 하나). 고정 시트 · (재시도면) 끝난 같은 레이아웃 시트는 그대로 둔다."""
    plan = d.get("plan") or {}
    old = {s["role"]: s for s in d.get("sheets") or [] if s.get("kind", "main") == "main"}
    out = []
    for i, ps in enumerate(plan.get("sheets") or []):
        cur = old.get(ps["role"])
        same = cur and catalog.norm(cur["layout"]["code"]) == catalog.norm(ps["layout"]["code"])
        if cur and (cur.get("pinned") or (keep_done and same and cur.get("status") == "done")):
            cur = {**cur, "order": i}
            out.append(cur)
            continue
        out.append({"id": (cur or {}).get("id") or new_id("vsh"), "role": ps["role"], "order": i, "kind": "main", "variant_of": None,
                    "step_label": ps["step_label"], "layout": ps["layout"], "title": "", "points": "", "meta_label": "",
                    "mode": ps.get("mode") or "auto", "status": "waiting", "pinned": bool(ps["layout"].get("pinned")),
                    "speaker_notes": "", "include_default": True, "content": {}})
    summaries = [s for s in d.get("sheets") or [] if s.get("kind") == "summary"]
    return out + summaries


async def kb_context(doc: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """E3(업종 · 공간 · 제품 · 고객 · 문장) → (메시지[헤드라인 · 핵심 메시지 · 제품 근거 · 사례 인용], 업종 추천 제품)."""
    f = doc.get("facts") or {}
    ind = doc.get("industry") or {}
    prods = [{"kind": p["kind"], "id": p["id"]} for p in (f.get("products") or [])[:6] if p.get("kind") in ("family", "model", "solution", "category")]
    text = " ".join(m["text"] for m in signals.active(doc) if m["axis"] in ("challenge", "value"))[:1200]
    r = await kbx.messages(vertical=ind.get("kr_vertical_id"), products=prods or None, customer=None, text=text)
    raw: list[dict[str, Any]] = list(r.get("headline") or []) + list(r.get("key_messages") or [])
    for p in r.get("products") or []:
        raw += list(p.get("items") or [])[:3]
    for c in r.get("cases") or []:
        raw += list(c.get("quotes") or [])[:2]
    out = []
    seen: set[str] = set()
    for k in raw:
        if not k.get("id") or k["id"] in seen or not k.get("text"):
            continue
        seen.add(k["id"])
        about = k.get("about") or [None, None]
        out.append({"id": k["id"], "text": k["text"], "about_kind": about[0] if len(about) > 0 else None,
                    "about_id": about[1] if len(about) > 1 else None, "about_name": k.get("about_name"),
                    "claim_flag": int(k.get("claim_flag") or 0), "source_url": k.get("source_url"), "level": k.get("level") or ""})
    suggested = [{"kind": p["kind"], "id": p["id"], "name": p.get("name") or p["id"], "suggested": True}
                 for p in r.get("products") or [] if p.get("kind") in ("family", "model", "solution", "category") and p.get("id")][:3]
    return out[:30], suggested


async def g_prepare(state: S) -> S:
    vp_id = state["vp_id"]
    doc = await load(vp_id)
    c = ctx()
    retry = bool(c.payload.get("retry")) or doc.get("status") in ("stopped", "failed")
    await step("prepare", 1, "재료 정리", f"재료 정리 — {doc.get('labels', {}).get('materials_footer') or '연결한 자료'}")
    await progress(vp_id, 3, "재료 정리", n_sheets=len((doc.get("plan") or {}).get("sheets") or []))
    await nap()
    kbm, suggested = await kb_context(doc)
    use_suggested = not (doc.get("facts") or {}).get("products") and suggested

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d.setdefault("facts", {})["kb_messages"] = kbm
        if use_suggested:
            d["facts"]["products"] = suggested
            d["facts"]["products_suggested"] = True
        d["sheets"] = sheets_from_plan(d, keep_done=retry)
        d["status"] = "generating"
        return d
    await service.mutate(vp_id, fn)
    if use_suggested:
        await decide_log(vp_id, 1, "재료에 제안 제품이 없어 업종 사례 기준 제품으로 채움 — " + " · ".join(p["name"] for p in suggested), "check",
                         key="products")
    await progress(vp_id, 10, "재료 정리")
    return {}


async def g_decide(state: S) -> S:
    vp_id = state["vp_id"]
    await step("decide", 2, "구조 결정", "최종 답으로 구조와 레이아웃을 다시 확인해요")
    pack = await repo.pack_status_map()
    c = ctx()
    retry = bool(c.payload.get("retry"))

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.replan(d, pack)
        d["sheets"] = sheets_from_plan(d, keep_done=retry or any(s.get("status") == "done" for s in d.get("sheets") or []))
        return d
    doc = await service.mutate(vp_id, fn)
    ind = doc.get("industry") or {}
    if ind.get("code"):
        text, mode = _industry_text(ind)
        await decide_log(vp_id, 2, text, "auto" if mode == "ask" else mode, key="industry")
        await nap(0.2)
        if ind["code"] != "GEN":
            if (ind.get("pack") or {}).get("status") == "ready":
                await decide_log(vp_id, 2, f"VP-{ind['code']} 업종판 준비됨 → 업종 레이아웃으로", "auto", key="pack")
            else:
                await decide_log(vp_id, 2, f"VP-{ind['code']} 업종판 제작 중 → 범용 레이아웃으로", "auto", key="pack")
            await nap(0.2)
    plan = doc.get("plan") or {}
    for dl in plan.get("decisions_log") or []:
        if dl.get("key") == "업종 레이아웃":
            continue
        await decide_log(vp_id, int(dl.get("stage") or 3), dl["text"], dl.get("mode") or "auto", key=dl.get("key") or "")
        await nap(0.2)
    for s in plan.get("sheets") or []:
        await decide_log(vp_id, 5, f"{s['step_label']} {s['layout']['display']} — {s['layout'].get('why') or ''}".rstrip(" —"),
                         s.get("mode") if s.get("mode") in ("auto", "check", "pin") else "auto", key="layout", value=s["layout"]["code"])
    await progress(vp_id, 20, "구조 결정", n_sheets=len(plan.get("sheets") or []))
    return {}


def _activity(sheet: dict[str, Any], doc: dict[str, Any]) -> str:
    code = catalog.norm(sheet["layout"]["code"])
    if code == "EF-B":
        q = (doc.get("facts") or {}).get("quote") or {}
        return f"투자 회수 기간 계산 중 — {q.get('version_label') or '견적'} · 절감액 범위 3개 시나리오"
    e = catalog.entry(code) or {}
    return f"{sheet['step_label']} 쓰는 중 — {sheet['layout']['display']} {e.get('short') or e.get('name') or ''}".rstrip()


async def g_write_sheets(state: S) -> S:
    vp_id = state["vp_id"]
    c = ctx()
    doc = await load(vp_id)
    memos = [m.get("text") or "" for m in await c.new_memos() if (m.get("text") or "").strip()]
    if memos:
        await decide_log(vp_id, 3, "메모 반영 — " + writer.cut(" / ".join(memos), 60), "auto", key="memo")
    todo = [s for s in doc.get("sheets") or [] if s.get("status") != "done"]
    total = max(1, len(doc.get("sheets") or []))
    done_n = total - len(todo)
    for s in todo:
        await c.check_cancel()
        more = [m.get("text") or "" for m in await c.new_memos() if (m.get("text") or "").strip()]
        if more:
            memos += more
            await decide_log(vp_id, 3, "메모 반영 — " + writer.cut(" / ".join(more), 60), "auto", key="memo")
        await step("write_sheets", 3, "시트 작성", _activity(s, doc), sheet_id=s["id"], sheet_status="writing")
        sid = s["id"]

        def writing(d: dict[str, Any]) -> dict[str, Any]:
            for x in d.get("sheets") or []:
                if x["id"] == sid:
                    x["status"] = "writing"
            return d
        await service.mutate(vp_id, writing)
        await nap()
        new = await writer.write_sheet(doc, s, memos=memos)

        def wrote(d: dict[str, Any]) -> dict[str, Any]:
            d["sheets"] = [({**new, "pinned": x.get("pinned"), "layout": {**new["layout"], "pinned": x.get("pinned", False)}} if x["id"] == sid else x)
                           for x in d.get("sheets") or []]
            return d
        doc = await service.mutate(vp_id, wrote)
        done_n += 1
        await c.step("write_sheets", "running", stage=3, label="시트 작성", sheet_id=sid, sheet_status="done",
                     activity=f"{s['step_label']} 완료 — {s['layout']['display']}")
        await progress(vp_id, 20 + round(60 * done_n / total), f"시트 작성 {done_n} / {total}", n_sheets=total)
    return {}


def extra_spec(doc: dict[str, Any]) -> dict[str, Any] | None:
    cp = (doc.get("facts") or {}).get("case_photo")
    if not cp:
        return None
    return {"code": "추가 제안 · VP-Q", "label": "같은 문제를 먼저 푼 곳", "idx": 1,
            "subject": {"kind": "case", "refs": [], "label": cp.get("title") or "같은 업종 사례"}}


async def fill_slots(doc: dict[str, Any], sheets: list[dict[str, Any]], *, style: str | None = None,
                     keep_user: bool = True) -> list[dict[str, Any]]:
    """시트의 이미지 칸 다시 채우기(사용자가 고른 칸은 그대로) → 그 시트들의 칸 목록."""
    ictx = await ops_result.ctx_for(doc)
    old = {(x["sheet_id"], x["code"]): x for x in doc.get("image_slots") or []}
    out: list[dict[str, Any]] = []
    for s in sheets:
        for spec in imagesel.slot_specs(doc, s):
            prev = old.get((s["id"], spec["code"]))
            if prev and keep_user and prev.get("user_set") and not style:
                out.append(prev)
                continue
            slot = await imagesel.match(doc, s["id"], spec, ictx, style=style)
            if prev:
                slot["id"] = prev["id"]
            out.append(slot)
    return out


def link_slots(d: dict[str, Any]) -> None:
    """칸 id 를 시트 내용(기둥 · 이해관계자 · 짝 · 한 문장)에 잇는다."""
    by_sheet: dict[str, list[dict[str, Any]]] = {}
    for x in d.get("image_slots") or []:
        if not x.get("extra"):
            by_sheet.setdefault(x["sheet_id"], []).append(x)
    for s in (d.get("sheets") or []) + (d.get("variants") or []):
        slots = by_sheet.get(s["id"]) or []
        c = s.get("content") or {}
        for key in ("pillars", "stakeholders", "pairs"):
            for i, it in enumerate(c.get(key) or []):
                it["image_slot_id"] = slots[i]["id"] if i < len(slots) else None
        if c.get("one_liner"):
            c["one_liner"]["image_slot_id"] = slots[0]["id"] if slots else None


async def g_fit_layout(state: S) -> S:
    vp_id = state["vp_id"]
    doc = await load(vp_id)
    await step("fit_layout", 4, "레이아웃 맞춤", "이미지 칸을 채워요 — 제안 제품의 공식 실사 → 설치 사례 → 솔루션 화면 → 일러스트 순")
    await nap()
    sheets = [s for s in doc.get("sheets") or []] + list(doc.get("variants") or [])
    slots = await fill_slots(doc, sheets)
    ex = extra_spec(doc)
    vp_sheet = next((s for s in doc.get("sheets") or [] if s.get("role") == "VP"), None)
    if ex and vp_sheet:
        ictx = await ops_result.ctx_for(doc)
        old_extra = next((x for x in doc.get("image_slots") or [] if x.get("extra")), None)
        es = await imagesel.match(doc, vp_sheet["id"], ex, ictx, extra=True)
        if old_extra:
            es["id"] = old_extra["id"]
        slots.append(es)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["image_slots"] = slots
        link_slots(d)
        for s in d.get("sheets") or []:
            s["meta_label"] = writer.meta_label(d, s)
        return d
    await service.mutate(vp_id, fn)
    official = sum(1 for x in slots if x.get("tier") in ("cut", "ui", "case") and x.get("asset") and not x.get("extra"))
    illust = sum(1 for x in slots if x.get("tier") == "illust" and not x.get("extra"))
    if slots:
        await decide_log(vp_id, 5, f"이미지 칸 {len([x for x in slots if not x.get('extra')])}개 — 공식 실사 {official} · 일러스트 {illust}",
                         "check" if illust or any(x.get("mode") == "check" for x in slots) else "auto", key="images")
    await progress(vp_id, 90, "레이아웃 맞춤")
    return {}


def build_checks(d: dict[str, Any], reports: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """VP3 `확인할 것` — 추정(검정) · 이미지 · 알림 · 요청. 교체 제안(업종판) · 넘김 확인은 따로 붙는다."""
    vid = d["id"]
    out: list[dict[str, Any]] = []
    ef = service.ef_sheet(d)
    for m in ((ef or {}).get("content") or {}).get("metrics") or []:
        if numbers.metric_status(m) == "estimated":
            side = next((m.get(k) for k in ("after", "before") if (m.get(k) or {}).get("status") == "estimated"), {}) or {}
            basis = side.get("estimate_basis") or ((side.get("source") or {}).get("label")) or "유관 사례 범위"
            out.append({"id": new_id("vck"), "tag": "추정", "text": f"기대 효과 '{m['label']}' — {basis} {side.get('display') or ''}으로 넣고 [추정] 표시했어요".replace("  ", " "),
                        "action_label": "수치 보강", "action_route": f"/vp/{vid}/result/numbers?sheet={ef['id']}", "strong": True, "resolved": False})
    ask = [m for m in ((ef or {}).get("content") or {}).get("metrics") or [] if numbers.metric_status(m) in ("ask", "requested")]
    if ask and ef:
        out.append({"id": new_id("vck"), "tag": "요청", "text": f"기대 효과 수치 {len(ask)}개가 비어 있어요 — 고객 데이터 요청 초안을 준비했어요",
                    "action_label": "수치 보강", "action_route": f"/vp/{vid}/result/numbers?sheet={ef['id']}", "strong": False, "resolved": False})
    inferred = [m for m in signals.active(d, "challenge") if m.get("state") == "inferred"]
    if inferred:
        out.append({"id": new_id("vck"), "tag": "추정", "text": f"고객 과제 {len(inferred)}개는 메모와 사례 DB로 추론했어요 — 고객 확인 전 [확인 필요]",
                    "action_label": "재료 보기", "action_route": f"/vp/{vid}/materials/review", "strong": True, "resolved": False})
    slots = [x for x in d.get("image_slots") or [] if not x.get("extra")]
    if slots:
        official = [x for x in slots if x.get("tier") in ("cut", "ui", "case") and x.get("asset")]
        names = []
        for x in official:
            nm = (x.get("subject") or {}).get("label") or ""
            if nm and nm not in names:
                names.append(nm)
        illust = sum(1 for x in slots if x.get("tier") == "illust")
        txt = f"이미지 칸 {len(slots)}개 — 공식 실사 {len(official)}" + (f" ({' · '.join(names[:3])})" if names else "")
        if illust:
            no_photo = any((x.get("subject") or {}).get("kind") in ("space", "customer") for x in slots if x.get("tier") == "illust")
            txt += f" · {'고객 매장 사진 없어 ' if no_photo else ''}일러스트 {illust}"
        out.append({"id": new_id("vck"), "tag": "이미지", "text": txt, "action_label": "이미지 확인", "action_route": f"/vp/{vid}/result/images",
                    "strong": False, "resolved": False})
    ind = d.get("industry") or {}
    if ind.get("code") and ind["code"] != "GEN" and (ind.get("pack") or {}).get("status") != "ready":
        n = len([s for s in d.get("sheets") or [] if s.get("kind", "main") == "main"])
        out.append({"id": new_id("vck"), "tag": "알림", "text": f"Value Props {ind.get('cell') or ind.get('name')} 업종판이 나오면 {n}장을 업종 레이아웃으로 바꿀지 물어볼게요",
                    "action_label": "알림 보기", "action_route": "/vp?packs=1", "strong": False, "resolved": False})
    nums = sum(r.get("numbers", 0) for r in reports.values())
    if nums:
        out.append({"id": new_id("vck"), "tag": "요청", "text": f"근거를 찾지 못한 숫자 {nums}개를 [00]으로 바꿨어요 — 값을 확인해 주세요",
                    "action_label": "수치 보강", "action_route": f"/vp/{vid}/result/numbers" + (f"?sheet={ef['id']}" if ef else ""),
                    "strong": False, "resolved": False})
    claims = sum(r.get("claims", 0) for r in reports.values())
    kb_claim = any(k.get("claim_flag") for k in (d.get("facts") or {}).get("kb_messages") or []
                   if any(k.get("id") in (p.get("proof_ids") or []) for s in d.get("sheets") or [] for p in (s.get("content") or {}).get("pillars") or []))
    if claims or kb_claim:
        out.append({"id": new_id("vck"), "tag": "요청", "text": "claim(수치·최상급) 문구는 대외 사용 전 원문 확인",
                    "action_label": "결과 보기", "action_route": f"/vp/{vid}/result", "strong": False, "resolved": False})
    iv = package.interview_numbers([s for s in d.get("sheets") or [] if s.get("kind", "main") == "main"])
    if iv:
        out.append({"id": new_id("vck"), "tag": "요청", "text": f"고객 인터뷰 수치 {len(iv)}개 — 고객 제출물에 쓰기 전에 물어볼게요",
                    "action_label": "보내기 보기", "action_route": f"/vp/{vid}/export", "strong": False, "resolved": False})
    if (d.get("facts") or {}).get("products_suggested"):
        names = " · ".join(p.get("name") or "" for p in (d.get("facts") or {}).get("products") or [])
        out.append({"id": new_id("vck"), "tag": "요청", "text": f"재료에 제안 제품이 없어 업종 사례 기준 제품({names})으로 채웠어요 — 제안할 제품을 확인해 주세요",
                    "action_label": "재료 보기", "action_route": f"/vp/{vid}/materials", "strong": False, "resolved": False})
    keep = [c for c in d.get("checks") or [] if c.get("offer_id") or c.get("handoff_id")]
    return out + keep


async def review_doc(vp_id: str, *, reason: str = "생성 완료", only: set[str] | None = None) -> dict[str, Any]:
    """검토 노드 본체(생성 · 고침 공통) — 숫자 검증 · 경쟁사 · claim · 확인할 것 · 상태 · 저장 지점."""
    reports: dict[str, dict[str, Any]] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        allowed = guards.allowed_numbers(d)
        comp = guards.competitor_names(d)
        for s in (d.get("sheets") or []) + (d.get("variants") or []):
            if only is not None and s["id"] not in only:
                continue
            _, rep = guards.verify_sheet(d, s, allowed, competitors=comp)
            reports[s["id"]] = rep
            s["meta_label"] = writer.meta_label(d, s)
        d["checks"] = build_checks(d, reports)
        d["generated"] = True
        d["status"] = "done"
        d["last_error"] = None
        return d
    await service.mutate(vp_id, fn)
    return await service.save_point(vp_id, reason)


async def g_review(state: S) -> S:
    vp_id = state["vp_id"]
    await step("review", 5, "검토", "수치 근거 · 경쟁사 이름 · claim · 이미지 출처를 확인해요")
    await nap()
    doc = await review_doc(vp_id)
    n = len([c for c in doc.get("checks") or [] if not c.get("resolved")])
    await decide_log(vp_id, 5, f"검토 끝 — 확인할 것 {n}개", "check" if n else "auto", key="review")
    await progress(vp_id, 100, "완료")
    return {"result": {"vp_id": vp_id, "next_route": f"/vp/{vp_id}/result"}}


def build_generate() -> StateGraph:
    g = StateGraph(S)
    order = ["prepare", "decide", "write_sheets", "fit_layout", "review"]
    fns = {"prepare": g_prepare, "decide": g_decide, "write_sheets": g_write_sheets, "fit_layout": g_fit_layout, "review": g_review}
    for n in order:
        g.add_node(n, fns[n])
    g.add_edge(START, order[0])
    for a, b in zip(order, order[1:]):
        g.add_edge(a, b)
    g.add_edge(order[-1], END)
    return g


# ── vp_revise ─────────────────────────────────────────────

NTH = {"첫": 1, "첫 번째": 1, "두 번째": 2, "세 번째": 3, "네 번째": 4, "1": 1, "2": 2, "3": 3, "4": 4}


def parse_request(text: str, context: str) -> list[dict[str, Any]]:
    """LLM 을 못 쓸 때의 결정적 해석(자주 쓰는 지시만)."""
    t = text.strip()
    ops: list[dict[str, Any]] = []
    m = re.search(r"(첫|두|세|네|[1-4])\s*(?:번째)?\s*기둥[을은를]?\s*['\"‘“](.+?)['\"’”]\s*(?:으로|로)", t)
    if m:
        idx = {"첫": 1, "두": 2, "세": 3, "네": 4}.get(m.group(1), None) or int(m.group(1))
        ops.append({"op": "rewrite_pillar", "sheet_role": "VP", "args": {"index": idx, "text": m.group(2)}})
    code = re.search(r"\b((?:VP|CH|EF)-[A-Z](?:\s*·?\s*\d)?)\b", t.upper())
    if code:
        ops.append({"op": "change_layout", "sheet_role": code.group(1)[:2], "args": {"code": catalog.norm(code.group(1))}})
    m2 = re.search(r"(?:가치\s*)?기둥\s*([2-4])\s*개", t)
    if m2 and not code:
        ops.append({"op": "set_pillars", "sheet_role": "VP", "args": {"n": int(m2.group(1))}})
    if re.search(r"한\s*문장|한\s*장\s*요약|퀵윈\s*버전|요약\s*한\s*장", t):
        ops.append({"op": "add_sheet", "sheet_role": "VP", "args": {"kind": "one_liner"}})
    if re.search(r"투자\s*회수|ROI|회수\s*기간", t, re.I):
        ops.append({"op": "change_layout", "sheet_role": "EF", "args": {"code": "EF-B"}})
    if re.search(r"이미지\s*없이|글로만", t):
        ops.append({"op": "change_layout", "sheet_role": "VP", "args": {"no_image": True}})
    if re.search(r"경쟁사", t) and re.search(r"빼|없이|말고", t):
        ops.append({"op": "tone", "args": {"competitors": False}})
    m3 = re.search(r"(.+?)\s*(?:관점|이야기)?[은는을를]?\s*빼", t)
    if context == "materials" and m3 and not ops:
        ops.append({"op": "exclude_material", "args": {"match": m3.group(1).strip()}})
    if not ops:
        ops.append({"op": "add_note", "args": {"text": t}})
    return ops


async def interpret(doc: dict[str, Any], text: str, context: str, sheet_id: str | None) -> dict[str, Any]:
    sheets = "\n".join(f"- [{s['id']}] {s['role']} {s['layout']['code']} '{s.get('title')}' 기둥: {' · '.join(p['title'] for p in (s.get('content') or {}).get('pillars') or [])}"
                       for s in doc.get("sheets") or [])
    res = await llm.try_call("vp.interpret_request.v1",
                             f"화면: {context}\n시트:\n{sheets}\n\n요청: {text}\n\n요청을 ops 로 바꾼다(rewrite_pillar{{index,text}} · set_pillars{{n}} · "
                             "change_layout{code|no_image} · add_sheet{kind} · move_to_notes{text} · set_metric{label,before,after} · tone{competitors} · "
                             "image_request{slot,text} · exclude_material{match} · add_note{text} · clarify). 모르면 needs_clarification.",
                             llm.InterpretRequest)
    ops = [o for o in (res or {}).get("ops") or [] if o.get("op")]
    if not ops and not (res or {}).get("needs_clarification"):
        ops = parse_request(text, context)
    nc = (res or {}).get("needs_clarification")
    return {"ops": ops, "needs_clarification": nc if nc and not str(nc).startswith("[mock") else None,
            "reply": (res or {}).get("reply") if (res or {}).get("reply") and not str(res.get("reply")).startswith("[mock") else None}


def layout_loss(cur: str, tgt: str) -> str | None:
    c, t = catalog.norm(cur), catalog.norm(tgt)
    if c in ("VP-H", "VP-D") and t not in ("VP-H", "VP-D"):
        return "stakeholders"
    if c in ("VP-E", "VP-A") and t not in ("VP-E", "VP-A"):
        return "pairs"
    return None


async def make_layout_request(doc: dict[str, Any], sheet: dict[str, Any], tgt: str, request_text: str) -> dict[str, Any]:
    """§7.4 route_check — 정보를 잃거나 적합도가 낮아지면 선택지 A/B/C 를 만들어 묻는다(VP3L)."""
    f = signals.fit_features(doc)
    cur = catalog.norm(sheet["layout"]["code"])
    fc, ft = fit.score(cur, f), fit.score(tgt, f)
    cd, td = catalog.display(cur), catalog.display(tgt)
    loss = layout_loss(cur, tgt)
    ce, te = catalog.entry(cur) or {}, catalog.entry(tgt) or {}
    what = {"stakeholders": f"이해관계자 {len((sheet.get('content') or {}).get('stakeholders') or [])}명의 KPI를 각자 쓰는 제품과 함께 따로 보여 줘요",
            "pairs": "과제마다 제품을 1:1로 짝지어 보여 줘요"}.get(loss or "", f"{ce.get('name', '')} 구성이에요")
    intro_default = f"'{request_text}' — 가능해요. 다만 지금의 {ce.get('short') or ce.get('name')}({cd})은 {what}. 이렇게 할 수 있어요."
    opts = [
        {"key": "A", "title": f"둘 다 — {te.get('short') or td} 요약 + {ce.get('short') or cd}", "base": "요약으로 먼저 말하고 원래 시트로 증명 · 시트 +1",
         "fit": max(fc, ft), "effect": {"add_sheet": tgt}},
        {"key": "B", "title": f"{te.get('short') or td}로 바꾸기", "base": ("역할별 KPI는 발표자 노트로 옮겨요" if loss == "stakeholders" else
                                                                       "빠지는 내용은 발표자 노트로 옮겨요"),
         "fit": ft, "effect": {"replace_layout": tgt, "move_to_notes": loss or ""}},
        {"key": "C", "title": f"그대로 {cd}", "base": "지금 재료와 잘 맞아요", "fit": fc, "effect": {"keep": True}},
    ]
    res = await llm.try_call("vp.layout_options.v1",
                             f"요청: {request_text}\n지금: {cur} {ce.get('name')}\n후보: {tgt} {te.get('name')}\n잃는 정보: {what}\n"
                             "intro(한두 문장, 재료 근거로만)와 선택지 A(둘 다) · B(바꾸기) · C(그대로)의 title · desc_without_fit 를 쓴다. 적합도 숫자는 쓰지 않는다.",
                             llm.LayoutOptionsOut)
    lo = {o.get("key"): o for o in (res or {}).get("options") or []}
    intro = (res or {}).get("intro")
    intro = intro if intro and not intro.startswith("[mock") else intro_default
    rank = {"A": 0, "B": 1, "C": 2}
    best = sorted(opts, key=lambda o: (-o["fit"], rank[o["key"]]))[0]["key"]
    out = []
    for o in opts:
        llm_o = lo.get(o["key"]) or {}
        title = llm_o.get("title") if llm_o.get("title") and not str(llm_o["title"]).startswith("[mock") else o["title"]
        desc = llm_o.get("desc_without_fit") if llm_o.get("desc_without_fit") and not str(llm_o["desc_without_fit"]).startswith("[mock") else o["base"]
        out.append({"key": o["key"], "title": title, "desc": f"{desc} · 적합도 {o['fit']}%", "fit": o["fit"], "recommended": o["key"] == best,
                    "effect": o["effect"]})
    return {"id": new_id("vlr"), "sheet_id": sheet["id"], "request_text": request_text, "intro": intro, "requested_code": tgt,
            "options": out, "status": "open", "choice": None, "created_at": now_iso()}


async def rewrite_one(vp_id: str, sheet_id: str, *, new_code: str | None = None, pin: bool | None = None, notes_add: str = "",
                      variant: bool = False) -> dict[str, Any]:
    """시트 하나 다시 쓰기(레이아웃 바꾸면 내용 · 이미지 칸도) → 저장한 문서."""
    doc = await load(vp_id)
    pool = (doc.get("variants") or []) if variant else (doc.get("sheets") or [])
    s = next((x for x in pool if x["id"] == sheet_id), None)
    if s is None:
        raise ApiError(404, "NOT_FOUND", f"시트를 찾을 수 없어요: {sheet_id}")
    s = copy.deepcopy(s)
    if new_code:
        s["layout"] = catalog.pick(new_code, why="직접 고른 레이아웃이에요", chosen_by="user", pinned=bool(pin if pin is not None else s.get("pinned")),
                                   fit=fit.score(new_code, signals.fit_features(doc)))
        s["status"] = "waiting"
        if not variant and s.get("role") in ("CH", "VP", "EF") and s.get("kind", "main") == "main":
            doc.setdefault("plan_overrides", {})[s["role"]] = catalog.norm(new_code)
    await step("write_sheets", 3, "시트 작성", _activity(s, doc), sheet_id=sheet_id, sheet_status="writing")
    new = await writer.write_sheet(doc, s)
    if notes_add:
        new["speaker_notes"] = "\n".join(x for x in (new.get("speaker_notes"), notes_add) if x)
    if pin is not None:
        new["pinned"] = pin
        new["layout"]["pinned"] = pin
        if pin:
            new["mode"] = "pin"
    pack = await repo.pack_status_map()
    work = copy.deepcopy(doc)
    tgt_list = work["variants"] if variant else work["sheets"]
    for i, x in enumerate(tgt_list):
        if x["id"] == sheet_id:
            tgt_list[i] = new
    slots = await fill_slots(work, [new])

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        key = "variants" if variant else "sheets"
        d[key] = [new if x["id"] == sheet_id else x for x in d.get(key) or []]
        if new_code and not variant and new.get("role") in ("CH", "VP", "EF") and new.get("kind", "main") == "main":
            d.setdefault("plan_overrides", {})[new["role"]] = catalog.norm(new_code)
            service.replan(d, pack)
        d["image_slots"] = [x for x in d.get("image_slots") or [] if x["sheet_id"] != sheet_id or x.get("extra")] + slots
        link_slots(d)
        new_s = next(x for x in d[key] if x["id"] == sheet_id)
        new_s["meta_label"] = writer.meta_label(d, new_s)
        return d
    return await service.mutate(vp_id, fn)


async def add_variant(vp_id: str, kind: str, *, layout_code: str | None = None, deployment_id: str | None = None) -> str:
    doc = await load(vp_id)
    vp = next((s for s in doc.get("sheets") or [] if s.get("role") == "VP" and s.get("kind", "main") == "main"), None)
    if kind == "one_liner":
        code = catalog.norm(layout_code or "VP-G")
        s = {"id": new_id("vsh"), "role": "VP", "order": 90, "kind": "one_liner", "variant_of": (vp or {}).get("id"), "step_label": "한 문장 버전",
             "layout": catalog.pick(code, why="한 문장 버전 — 퀵윈 보내기 · PDF 한 장 요약에 써요", chosen_by="user"), "title": "", "points": "",
             "meta_label": "", "mode": "auto", "status": "waiting", "pinned": False, "speaker_notes": "", "include_default": False, "content": {}}
    else:
        cp = (doc.get("facts") or {}).get("case_photo") or {}
        dep = deployment_id or cp.get("deployment_id")
        det = await kbx.case_detail(dep) if dep else None
        ref = {"deployment_id": dep or "", "title": (det or {}).get("title") or cp.get("title") or "같은 업종 사례", "url": (det or {}).get("url") or "",
               "summary": writer.cut(" · ".join(str(x.get("text") if isinstance(x, dict) else x) for x in (det or {}).get("needs") or []) or "", 80)}
        s = {"id": new_id("vsh"), "role": "REF", "order": 91, "kind": "reference", "variant_of": (vp or {}).get("id"), "step_label": "레퍼런스",
             "layout": catalog.pick(layout_code or "VP-Q", why="같은 업종 사례 · 외부 제출 전 인용 확인", chosen_by="user"), "title": ref["title"],
             "points": "", "meta_label": "", "mode": "check", "status": "waiting", "pinned": False, "speaker_notes": "", "include_default": False,
             "content": {"reference": ref}}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if kind == "one_liner":
            d["variants"] = [v for v in d.get("variants") or [] if v.get("kind") != "one_liner"]
        d.setdefault("variants", []).append(s)
        return d
    await service.mutate(vp_id, fn)
    await rewrite_one(vp_id, s["id"], variant=True)
    return s["id"]


async def apply_option(vp_id: str, sheet_id: str, req: dict[str, Any], key: str, *, pin: bool, note: str | None) -> dict[str, Any]:
    opt = next((o for o in req.get("options") or [] if o["key"] == key), None)
    if opt is None:
        raise ApiError(422, "INVALID_OPTION", f"선택지 {key}가 없어요")
    eff = opt.get("effect") or {}
    doc = await load(vp_id)
    sheet = next((s for s in doc.get("sheets") or [] if s["id"] == sheet_id), None)
    if eff.get("add_sheet") and sheet:
        sid = new_id("vsh")
        code = catalog.norm(eff["add_sheet"])
        summ = {"id": sid, "role": sheet["role"], "order": sheet.get("order", 1), "kind": "summary", "variant_of": sheet["id"],
                "step_label": f"{sheet['step_label']} 요약", "layout": catalog.pick(code, why="요약으로 먼저 말하고 원래 시트로 증명", chosen_by="user"),
                "title": "", "points": "", "meta_label": "", "mode": "auto", "status": "waiting", "pinned": False,
                "speaker_notes": note or "", "include_default": True, "content": {}}

        def add(d: dict[str, Any]) -> dict[str, Any]:
            out = []
            for s in d.get("sheets") or []:
                if s["id"] == sheet_id:
                    out.append(summ)
                out.append(s)
            for i, s in enumerate(out):
                s["order"] = i
            d["sheets"] = out
            return d
        await service.mutate(vp_id, add)
        doc = await rewrite_one(vp_id, sid)
        if pin:
            doc = await rewrite_one(vp_id, sheet_id, pin=True)
    elif eff.get("replace_layout") and sheet:
        lost = ""
        if eff.get("move_to_notes") == "stakeholders":
            lost = "역할별 KPI — " + " · ".join(f"{s['role']}: {s.get('kpi') or s.get('value')}" for s in (sheet.get("content") or {}).get("stakeholders") or [])
        elif eff.get("move_to_notes") == "pairs":
            lost = "과제 ↔ 제품 — " + " · ".join(f"{p['challenge']} → {(p.get('product') or {}).get('name') or ''}" for p in (sheet.get("content") or {}).get("pairs") or [])
        doc = await rewrite_one(vp_id, sheet_id, new_code=eff["replace_layout"], pin=pin, notes_add=lost)
    elif pin:
        doc = await rewrite_one(vp_id, sheet_id, pin=True)

    def close(d: dict[str, Any]) -> dict[str, Any]:
        for r in d.get("layout_requests") or []:
            if r["id"] == req["id"]:
                r["status"] = "applied"
                r["choice"] = {"key": key, "layout_code": eff.get("replace_layout") or eff.get("add_sheet") or (sheet or {}).get("layout", {}).get("code"),
                               "pinned": pin}
        return d
    return await service.mutate(vp_id, close)


async def r_apply(state: S) -> S:
    """지시 · 레이아웃 · 수치 · 변형 · 업종판 — payload.op 로 나눈다."""
    vp_id = state["vp_id"]
    c = ctx()
    p = dict(c.payload)
    op = p.get("op")
    result: dict[str, Any] = {"vp_id": vp_id, "applied_ops": []}
    await step("apply", 3, "고치기", "요청을 해석해 바뀐 시트만 다시 써요")
    if op == "layout":
        doc = await load(vp_id)
        req = next((r for r in doc.get("layout_requests") or [] if r["id"] == p.get("request_id")), None) if p.get("request_id") else None
        if req is None and p.get("option_key"):
            req = next((r for r in doc.get("layout_requests") or [] if r.get("sheet_id") == p["sheet_id"] and r.get("status") == "open"), None)
        if p.get("option_key") and req:
            await apply_option(vp_id, p["sheet_id"], req, p["option_key"], pin=bool(p.get("pin")), note=p.get("note"))
            result["applied_ops"].append(f"option:{p['option_key']}")
        elif p.get("layout_code"):
            await rewrite_one(vp_id, p["sheet_id"], new_code=p["layout_code"], pin=bool(p.get("pin")), notes_add=p.get("note") or "")
            result["applied_ops"].append(f"layout:{p['layout_code']}")
            if req:
                await apply_close(vp_id, req["id"], p["layout_code"], bool(p.get("pin")))
        await decide_log(vp_id, 5, f"레이아웃 적용 — {catalog.display(p.get('layout_code') or '') or p.get('option_key')}", "pin" if p.get("pin") else "auto",
                         key="layout")
        result["reason"] = "레이아웃 적용"
    elif op == "add_sheet":
        if p.get("kind") == "one_liner" and not any(v.get("kind") == "one_liner" for v in (await load(vp_id)).get("variants") or []) or p.get("kind") == "reference":
            sid = await add_variant(vp_id, p.get("kind") or "one_liner", layout_code=p.get("layout_code"), deployment_id=p.get("deployment_id"))
            result["applied_ops"].append(f"add_sheet:{p.get('kind')}")
            result["sheet_id"] = sid
            await decide_log(vp_id, 4, "한 문장 버전(VP-G)을 만들었어요" if p.get("kind") == "one_liner" else "레퍼런스 시트(VP-Q)를 더했어요", "auto",
                             key="variant")
        result["reason"] = "변형 시트"
        if p.get("then_handoff"):
            ho = await ops_result.finalize_handoff(vp_id, p["then_handoff"])
            result["handoff"] = {"id": ho["id"], "open_route": ho["open_route"]}
    elif op == "ef_switch":
        await rewrite_one(vp_id, p["sheet_id"], new_code=p["layout_code"])
        await decide_log(vp_id, 6, f"쓸 수 있는 수치가 바뀌어 기대 효과를 {p['layout_code']}로 바꿨어요", "auto", key="ef_switch")
        result["applied_ops"].append(f"ef_switch:{p['layout_code']}")
        result["reason"] = "수치 반영"
    elif op == "pack_apply":
        doc = await load(vp_id)
        offer = next((o for o in doc.get("pack_offers") or [] if o["id"] == p.get("offer_id")), None)
        if offer:
            for ch in offer.get("changes") or []:
                if any(s["id"] == ch["sheet_id"] and not s.get("pinned") for s in doc.get("sheets") or []):
                    await rewrite_one(vp_id, ch["sheet_id"], new_code=ch["to_code"])

            def close(d: dict[str, Any]) -> dict[str, Any]:
                for o in d.get("pack_offers") or []:
                    if o["id"] == offer["id"]:
                        o["status"] = "applied"
                for ck in d.get("checks") or []:
                    if ck.get("offer_id") == offer["id"]:
                        ck["resolved"] = True
                return d
            await service.mutate(vp_id, close)
            await decide_log(vp_id, 2, f"업종판 VP-{offer['industry_code']}로 {len(offer.get('changes') or [])}장을 바꿨어요 (고정한 시트는 그대로)", "auto",
                             key="pack")
        result["reason"] = "업종판 적용"
    else:
        result.update(await apply_text(vp_id, p.get("text") or "", p.get("context") or "result", p.get("sheet_id")))
    return {"result": result}


async def apply_close(vp_id: str, req_id: str, code: str, pin: bool) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for r in d.get("layout_requests") or []:
            if r["id"] == req_id:
                r["status"] = "applied"
                r["choice"] = {"key": None, "layout_code": code, "pinned": pin}
        return d
    await service.mutate(vp_id, fn)


async def apply_text(vp_id: str, text: str, context: str, sheet_id: str | None) -> dict[str, Any]:
    doc = await load(vp_id)
    out: dict[str, Any] = {"applied_ops": [], "context": context}
    if context == "questions":
        qs = service.open_questions(doc)
        lines = "\n".join(f"{q['no']}. {q['title']} — " + " / ".join(f"{o['key']}={o['label']}" for o in q.get("options") or []) for q in qs)
        res = await llm.try_call("vp.parse_answer.v1", f"질문:\n{lines}\n\n직접 답: {text}\n\n질문 번호마다 고른 선택지 key 를 돌려준다.", llm.ParseAnswer)
        picks: dict[int, list[str]] = {}
        for a in (res or {}).get("answers") or []:
            picks[int(a.get("question_no") or 0)] = [k for k in a.get("keys") or []]
        if not picks:
            for q in qs:
                ks = [o["key"] for o in q.get("options") or [] if o["label"].split(" ", 1)[-1].replace(" 먼저", "") in text or o["label"] in text]
                if q["kind"] == "direction":
                    if re.search(r"매출|성장", text):
                        ks = ["gain"]
                    elif re.search(r"비용|인건비|절감", text):
                        ks = ["cost"]
                    if re.search(r"둘\s*다", text):
                        ks = ["both"]
                if ks:
                    picks[q["no"]] = ks

        def fn(d: dict[str, Any]) -> dict[str, Any]:
            for q in d.get("questions") or []:
                if q.get("status") == "open" and q["no"] in picks:
                    valid = [k for k in picks[q["no"]] if k in {o["key"] for o in q.get("options") or []}]
                    if valid:
                        q["selected_keys"] = valid if q.get("multi") else valid[:1]
            return d
        await service.mutate(vp_id, fn)
        out["applied_ops"] = [f"answer:{n}" for n in picks]
        out["reply"] = "답을 반영해 선택을 바꿔 두었어요. 맞으면 이대로 진행을 눌러 주세요." if picks else None
        out["needs_clarification"] = None if picks else "어느 질문에 대한 답인지 알아듣지 못했어요. 선택지를 직접 골라 주세요."
        return out
    if context == "numbers":
        ef = next((s for s in doc.get("sheets") or [] if s["id"] == sheet_id), None) or service.ef_sheet(doc)
        ms = ((ef or {}).get("content") or {}).get("metrics") or []
        res = await llm.try_call("vp.parse_numbers.v1", f"지표: {', '.join(m['label'] for m in ms)}\n입력: {text}\n지표마다 지금(before) · 도입 후(after) 값과 단위.",
                                 llm.ParseNumbers)
        items = [i for i in (res or {}).get("items") or [] if i.get("metric_label")]
        if not items:
            for m in ms:
                if m["label"] in text:
                    mm = re.search(re.escape(m["label"]) + r"[^\d]{0,12}(\d[\d,.]*)\s*([%가-힣A-Za-z]*)", text)
                    if mm:
                        side = "after" if re.search(r"도입\s*후|이후|목표", text) else "before"
                        items.append({"metric_label": m["label"], side: {"value": float(mm.group(1).replace(",", "")), "unit": mm.group(2) or ""}})
        applied = []

        def fn(d: dict[str, Any]) -> dict[str, Any]:
            for s in d.get("sheets") or []:
                for m in (s.get("content") or {}).get("metrics") or []:
                    it = next((i for i in items if i["metric_label"] == m["label"]), None)
                    if not it:
                        continue
                    for side in ("before", "after"):
                        v = it.get(side)
                        if v and v.get("value") is not None:
                            unit = v.get("unit") or (m.get(side) or {}).get("unit") or ""
                            m[side] = numbers.nv(f"{numbers.fmt_num(float(v['value']))}{unit}", "secured", value=float(v["value"]), unit=unit,
                                                 source={"kind": "user", "label": "사용자", "refs": []})
                    m["handling"] = "direct"
                    m["decided_by"] = "user"
                    m["source_label"] = "사용자"
                    m["how"] = "직접 입력"
                    numbers.decorate(m)
                    applied.append(m["label"])
            return d
        await service.mutate(vp_id, fn)
        out["applied_ops"] = [f"set_metric:{x}" for x in applied]
        out["needs_clarification"] = None if applied else "어느 지표의 값인지 알아듣지 못했어요. 예: 오출고율 지금 0.8%"
        return out
    parsed = await interpret(doc, text, context, sheet_id)
    if parsed.get("needs_clarification"):
        out["needs_clarification"] = parsed["needs_clarification"]
        return out
    pack = await repo.pack_status_map()
    changed: set[str] = set()
    for o in parsed["ops"]:
        kind = o.get("op")
        args = o.get("args") or {}
        role = o.get("sheet_role") or "VP"
        doc = await load(vp_id)
        target = next((s for s in doc.get("sheets") or [] if s["id"] == sheet_id), None) if sheet_id else None
        target = target or next((s for s in doc.get("sheets") or [] if s.get("role") == role and s.get("kind", "main") == "main"), None)
        if context in ("structure", "materials") and kind in ("change_layout", "set_pillars"):
            code = args.get("code")
            if args.get("no_image") or kind == "set_pillars":
                cur = ((doc.get("plan") or {}).get("sheets") or [{}])
                vpc = next((x["layout"]["code"] for x in cur if x.get("role") == "VP"), "VP-F3")
                code = catalog.no_image(vpc) if args.get("no_image") else catalog.with_pillars(vpc if vpc.startswith(("VP-F", "VP-B")) else "VP-F3", int(args.get("n") or 3))
            if code:
                try:
                    await ops_work.patch_plan(vp_id, models.PatchPlan(override=models.PlanOverride(**{role if role in ("CH", "VP", "EF") else "VP": code})))
                    out["applied_ops"].append(f"override:{code}")
                except ApiError as exc:
                    out["needs_clarification"] = exc.message
            continue
        if kind == "exclude_material":
            pat = (args.get("match") or "").strip()

            def ex(d: dict[str, Any]) -> dict[str, Any]:
                for m in d.get("materials") or []:
                    if pat and pat in m["text"] and not m.get("excluded"):
                        m["excluded"] = True
                        m.setdefault("flags", []).append("사용자가 뺌")
                service.replan(d, pack)
                return d
            await service.mutate(vp_id, ex)
            out["applied_ops"].append(f"exclude:{pat}")
            continue
        if kind == "add_note":
            def note(d: dict[str, Any]) -> dict[str, Any]:
                d["note"] = ((d.get("note") or "") + "\n" + (args.get("text") or "")).strip()
                return d
            await service.mutate(vp_id, note)
            out["applied_ops"].append("note")
            if context in ("result", "layout", "images", "export") and target:
                await rewrite_one(vp_id, target["id"])
                changed.add(target["id"])
            continue
        if kind == "tone":
            def tone(d: dict[str, Any]) -> dict[str, Any]:
                d["note"] = ((d.get("note") or "") + "\n경쟁사 이야기는 빼 주세요").strip()
                service.replan(d, pack)
                return d
            await service.mutate(vp_id, tone)
            out["applied_ops"].append("tone")
            continue
        if kind == "rewrite_pillar" and target:
            idx = int(args.get("index") or 1) - 1
            newt = writer.cut(str(args.get("text") or ""), writer.LIMITS["item_title"])

            def rp(d: dict[str, Any]) -> dict[str, Any]:
                for s in d.get("sheets") or []:
                    if s["id"] == target["id"]:
                        ps = (s.get("content") or {}).get("pillars") or []
                        if 0 <= idx < len(ps) and newt:
                            ps[idx]["title"] = newt
                            s["points"] = " · ".join(p["title"] for p in ps)
                return d
            await service.mutate(vp_id, rp)
            changed.add(target["id"])
            out["applied_ops"].append(f"rewrite_pillar:{idx + 1}")
            continue
        if kind in ("change_layout", "set_pillars") and target:
            cur = target["layout"]["code"]
            if args.get("no_image"):
                tgt = catalog.no_image(cur)
            elif kind == "set_pillars":
                n = int(args.get("n") or 3)
                tgt = catalog.with_pillars(cur, n) if cur.startswith(("VP-F", "VP-B")) else f"VP-F{n}"
            else:
                tgt = catalog.norm(args.get("code") or "")
            if not catalog.entry(tgt) or tgt == catalog.norm(cur):
                continue
            f = signals.fit_features(doc)
            if layout_loss(cur, tgt) or fit.score(tgt, f) < fit.score(cur, f) - int(config.th("fit_drop")):
                req = await make_layout_request(doc, target, tgt, text)

                def addreq(d: dict[str, Any]) -> dict[str, Any]:
                    for r in d.get("layout_requests") or []:
                        if r.get("sheet_id") == target["id"] and r.get("status") == "open":
                            r["status"] = "canceled"
                    d.setdefault("layout_requests", []).append(req)
                    return d
                await service.mutate(vp_id, addreq)
                await decide_log(vp_id, 5, f"'{writer.cut(text, 30)}' — {catalog.display(cur)}의 정보를 잃을 수 있어 선택지를 만들었어요", "check", key="layout_request")
                out["layout_request_id"] = req["id"]
                out["route"] = f"/vp/{vp_id}/result/layout?sheet={target['id']}&req={req['id']}"
                return out
            await rewrite_one(vp_id, target["id"], new_code=tgt)
            changed.add(target["id"])
            out["applied_ops"].append(f"layout:{tgt}")
            continue
        if kind == "add_sheet":
            sid = await add_variant(vp_id, args.get("kind") or "one_liner", layout_code=args.get("layout_code"))
            out["applied_ops"].append("add_sheet")
            out["sheet_id"] = sid
            continue
        if kind == "move_to_notes" and target:
            def mv(d: dict[str, Any]) -> dict[str, Any]:
                for s in d.get("sheets") or []:
                    if s["id"] == target["id"]:
                        s["speaker_notes"] = "\n".join(x for x in (s.get("speaker_notes"), args.get("text") or text) if x)
                return d
            await service.mutate(vp_id, mv)
            out["applied_ops"].append("move_to_notes")
            continue
        if kind == "image_request":
            doc = await load(vp_id)
            slot = next((x for x in doc.get("image_slots") or [] if x["id"] == args.get("slot")), None)
            if slot is None and doc.get("image_slots"):
                slot = doc["image_slots"][0]
            if slot:
                ictx = await ops_result.ctx_for(doc)
                spec = {"code": slot["code"], "label": slot["label"], "idx": 1, "subject": slot["subject"]}
                new = await imagesel.match(doc, slot["sheet_id"], spec, ictx, style="illustration" if re.search(r"일러스트|그림", text) else None,
                                           extra=bool(slot.get("extra")))
                new["id"] = slot["id"]

                def put(d: dict[str, Any]) -> dict[str, Any]:
                    d["image_slots"] = [new if x["id"] == slot["id"] else x for x in d.get("image_slots") or []]
                    return d
                await service.mutate(vp_id, put)
                out["applied_ops"].append("image_request")
            continue
    if parsed.get("reply"):
        out["reply"] = parsed["reply"]
    if changed or any(x.startswith(("layout", "add_sheet", "rewrite")) for x in out["applied_ops"]):
        await review_doc(vp_id, reason="고침", only=changed or None)
    elif context in ("structure", "materials"):
        await service.save_point(vp_id, "플랜 변경")
    return out


async def r_review(state: S) -> S:
    vp_id = state["vp_id"]
    res = dict(state.get("result") or {})
    doc = await load(vp_id)
    if doc.get("generated") and res.get("reason") in ("레이아웃 적용", "변형 시트", "수치 반영", "업종판 적용"):
        await review_doc(vp_id, reason=res["reason"])
    await progress(vp_id, 100, "완료")
    return {"result": res}


def build_revise() -> StateGraph:
    g = StateGraph(S)
    g.add_node("apply", r_apply)
    g.add_node("review", r_review)
    g.add_edge(START, "apply")
    g.add_edge("apply", "review")
    g.add_edge("review", END)
    return g


# ── vp_images · vp_export · vp_pack_offer ───────────────────

async def i_apply(state: S) -> S:
    vp_id = state["vp_id"]
    p = dict(ctx().payload)
    doc = await load(vp_id)
    out: dict[str, Any] = {"vp_id": vp_id, "changed": 0}
    if p.get("op") == "restyle":
        await step("images", 4, "일러스트로 통일", "실사를 모두 빼고 같은 톤의 일러스트로 다시 그려요")
        sheets = (doc.get("sheets") or []) + (doc.get("variants") or [])
        slots = await fill_slots(doc, sheets, style="illustration", keep_user=False)
        keep_extra = [x for x in doc.get("image_slots") or [] if x.get("extra")]

        def fn(d: dict[str, Any]) -> dict[str, Any]:
            d["image_slots"] = slots + keep_extra
            link_slots(d)
            return d
        await service.mutate(vp_id, fn)
        out["changed"] = len(slots)
        await decide_log(vp_id, 5, f"이미지 칸 {len(slots)}개를 일러스트로 통일했어요", "check", key="images")
    elif p.get("op") == "customer_photo":
        att = next((a for a in doc.get("attachments") or [] if a["id"] == p.get("attachment_id")), None)
        if att:
            await step("images", 4, "고객 사진 배치", "고객 사진을 공간 칸에 넣어요 — 고객 확인 전 외부 사용 불가")
            read = await collect.read_attachment(att)
            targets = [x for x in doc.get("image_slots") or [] if (x.get("subject") or {}).get("kind") in ("space", "customer")]
            news = {}
            for x in targets:
                new = await imagesel.replace(x, {"source": "file", "file_id": att["file_id"]})
                new["user_set"] = True
                news[x["id"]] = new

            def fn(d: dict[str, Any]) -> dict[str, Any]:
                d["attachments"] = [read if a["id"] == att["id"] else a for a in d.get("attachments") or []]
                d["image_slots"] = [news.get(x["id"], x) for x in d.get("image_slots") or []]
                return d
            await service.mutate(vp_id, fn)
            out["changed"] = len(news)
    await review_doc(vp_id, reason="이미지 변경")
    await progress(vp_id, 100, "완료")
    return {"result": out}


def build_images() -> StateGraph:
    g = StateGraph(S)
    g.add_node("images", i_apply)
    g.add_edge(START, "images")
    g.add_edge("images", END)
    return g


async def e_export(state: S) -> S:
    vp_id = state["vp_id"]
    p = dict(ctx().payload)
    vex = p["export_id"]
    doc = await load(vp_id)
    await step("export", 1, "내보내기", "PPTX를 만들고 있어요" if p.get("format") == "pptx" else "한 장 요약 PDF를 만들고 있어요")
    rec = await repo.get_export(vex) or {"id": vex, "vp_id": vp_id, "format": p.get("format")}
    rec["status"] = "running"
    await repo.put_export(vex, rec)
    pkg = package.build(doc, p.get("proposal_type") or "standard", estimates_as_notes=True)
    if p.get("format") == "pdf_summary" and not any(catalog.norm(s["layout"]["code"]) in ("VP-G", "VP-C") for s in pkg["sheets"]):
        ol = package.one_liner(doc)
        if ol is None:
            await add_variant(vp_id, "one_liner")
            doc = await load(vp_id)
            ol = package.one_liner(doc)
        if ol:
            pkg = {**pkg, "sheets": [package._pkg_sheet(doc, ol, notes_estimates=True)] + pkg["sheets"]}
    try:
        res = await exporting.run(doc, pkg, fmt=p.get("format") or "pptx", include_notes=bool(p.get("include_notes", True)))
    except Exception as exc:
        rec.update({"status": "failed", "error": str(getattr(exc, "message", exc))[:200]})
        await repo.put_export(vex, rec)
        raise
    rec.update({"status": "done", "file_id": res["file_id"], "filename": res["filename"], "finished_at": now_iso()})
    await repo.put_export(vex, rec)
    for s in pkg["sheets"]:
        for slot in s.get("image_slots") or []:
            key = imagesel.asset_key(slot.get("asset"))
            if key:
                await repo.add_usage(key, vp_id, vex)
    return {"result": {"vp_id": vp_id, "export_id": vex, "file_id": res["file_id"], "filename": res["filename"], "warnings": res.get("warnings") or []}}


def build_export() -> StateGraph:
    g = StateGraph(S)
    g.add_node("export", e_export)
    g.add_edge(START, "export")
    g.add_edge("export", END)
    return g


async def p_offer(state: S) -> S:
    code = ctx().payload["industry_code"]
    ind = config.industry(code)
    made = 0
    docs = await repo.list_vps({"archived": False}, limit=1000)
    for d in docs:
        if ((d.get("industry") or {}).get("code")) != code or not d.get("generated"):
            continue
        changes = []
        for s in d.get("sheets") or []:
            if s.get("kind", "main") != "main" or s.get("pinned") or catalog.is_pack(s["layout"]["code"]):
                continue
            changes.append({"sheet_id": s["id"], "from_code": s["layout"]["code"], "to_code": catalog.pack_code(code, s["role"])})
        if not changes or any(o.get("industry_code") == code and o.get("status") == "open" for o in d.get("pack_offers") or []):
            continue
        vpo = new_id("vpo")
        n = len(changes)

        def fn(x: dict[str, Any], vpo: str = vpo, changes: list[dict[str, Any]] = changes, n: int = n) -> dict[str, Any]:
            x.setdefault("pack_offers", []).append({"id": vpo, "industry_code": code, "changes": changes, "status": "open"})
            x.setdefault("checks", []).insert(0, {"id": new_id("vck"), "tag": "업종판", "text": f"{ind['cell']} 업종판이 나왔어요 — {n}장을 업종 레이아웃으로 바꿀까요?",
                                                  "action_label": "바꾸기", "action_route": f"/vp/{x['id']}/result", "strong": False, "resolved": False,
                                                  "offer_id": vpo})
            if x.get("industry"):
                x["industry"]["pack"] = {"status": "ready", "label": "업종판 준비됨"}
            return x
        await service.mutate(d["id"], fn)
        try:
            await jobs().push_notification((d.get("owner") or {}).get("user_id") or d.get("owner_id") or "", {
                "type": "vp_pack_offer", "service": "vp", "ref": d["id"], "title": f"{ind['cell']} 업종판이 나왔어요",
                "summary": f"{d.get('title')} — {n}장을 업종 레이아웃으로 바꿀지 확인해 주세요", "route": f"/vp/{d['id']}/result"})
        except Exception as exc:  # noqa: BLE001
            log.info("알림 실패: %s", exc)
        made += 1
    return {"result": {"industry_code": code, "offers": made}}


def build_pack_offer() -> StateGraph:
    g = StateGraph(S)
    g.add_node("offer", p_offer)
    g.add_edge(START, "offer")
    g.add_edge("offer", END)
    return g


# ── 처리기 ────────────────────────────────────────────────

async def _run(c: JobContext, builder: StateGraph, *, labels: dict[str, str] | None = None,
               progress_map: dict[str, int] | None = None, track: bool = True) -> dict[str, Any]:
    vp_id = c.payload.get("vp_id")
    if track and vp_id:
        await service.set_job_progress(vp_id, c.job.id, int(c.job.progress or 0), "running")
    try:
        final = await run_graph(c, builder, {"vp_id": vp_id or ""}, step_labels=labels, progress_map=progress_map)
    except AwaitingInput:
        if track and vp_id:
            await service.set_job_progress(vp_id, c.job.id, int(c.job.progress or 95), "awaiting_input")
        raise
    except JobCanceled:
        if track and vp_id:
            await service.finish_job(vp_id, c.job.id, "canceled")
        raise
    except Exception as exc:
        err = llm.map_error(exc) if not isinstance(exc, ApiError) else exc
        if track and vp_id:
            await service.finish_job(vp_id, c.job.id, "failed", {"code": err.code, "message": err.message})
        raise err from exc
    if track and vp_id:
        await service.finish_job(vp_id, c.job.id, "succeeded")
    return dict((final or {}).get("result") or {})


async def handle_materials(c: JobContext) -> dict[str, Any]:
    res = await _run(c, build_materials(), labels=M_LABELS, progress_map=M_PROGRESS)
    vp_id = c.payload["vp_id"]
    if c.payload.get("then_generate"):
        doc = await load(vp_id)
        if not service.open_questions(doc):
            job = await service.enqueue(vp_id, "vp.generate", {"sheet_roles": c.payload.get("sheet_roles")}, doc=doc)
            res["generate_job_id"] = job
            res["next_route"] = f"/vp/{vp_id}/generating?job={job}"
    return res


async def handle_generate(c: JobContext) -> dict[str, Any]:
    t0 = time.monotonic()
    res = await _run(c, build_generate(), labels=G_LABELS)
    res["seconds"] = round(time.monotonic() - t0, 1)
    return res


async def handle_revise(c: JobContext) -> dict[str, Any]:
    doc = await load(c.payload["vp_id"])
    track = (doc.get("active_job") or {}).get("job_id") == c.job.id
    return await _run(c, build_revise(), labels={"apply": "고치기", "review": "검토"}, track=track)


async def handle_images(c: JobContext) -> dict[str, Any]:
    return await _run(c, build_images(), labels={"images": "이미지"})


async def handle_export(c: JobContext) -> dict[str, Any]:
    return await _run(c, build_export(), labels={"export": "내보내기"}, track=False)


async def handle_pack_offer(c: JobContext) -> dict[str, Any]:
    return await _run(c, build_pack_offer(), labels={"offer": "교체 제안"}, track=False)


HANDLERS = {"vp.materials": handle_materials, "vp.generate": handle_generate, "vp.revise": handle_revise, "vp.images": handle_images,
            "vp.export": handle_export, "vp.pack_offer": handle_pack_offer}
