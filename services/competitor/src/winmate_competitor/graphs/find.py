"""ca.find(§7.3) — 넣기 → 후보 찾기.

read_input → check_slots ─(묻기 1)→ ask_slots ⏸ ─┐
                         └──────────────────────────┤
     fill_gaps → gather_candidates(업종 · 제품 · 장소 · 고객사 · 명시) → resolve_entities → score → select → make_criteria → title → save

CA1G 작업 줄 4(`step {lines, candidates_so_far}`): 1 입력 읽기 · 2 업종 사례 제품군 · 3 공개 자료 검색 · 4 후보 정리.
사람 확인(interrupt)은 ask_slots 한 곳뿐 — 답 `{customer, place}` 또는 `{skip: true}`(jobs `input.answer`, `{value: …}` 도 받는다).
"""
from __future__ import annotations

import logging
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.ids import now_iso
from winmate_common.jobs import AwaitingInput, JobCanceled, JobContext, jobs

from .. import aix, config, kbx, prompts, reading, rqx, rules, service, verify
from .. import evidence as E
from .. import store as R
from .common import doc_of, register, save, step

log = logging.getLogger("winmate.competitor.find")

LINE1 = "입력 읽기 — 고객사 · 업종 · 장소 · 제품"
LINE4 = "후보 정리 · 근거 붙이기"
_BUDGETS: dict[str, aix.Budget] = {}


class FindState(TypedDict, total=False):
    analysis_id: str
    job_id: str
    auto: bool
    asked: bool
    ask: bool
    skipped: bool
    next_job: str | None


async def _budget(job_id: str) -> aix.Budget:
    b = _BUDGETS.get(job_id)
    if b is None:
        b = await aix.init_budget("find")
        _BUDGETS[job_id] = b
    return b


# ── 작업 줄 ──────────────────────────────────────────────
def short_product(value: str | None) -> str:
    v = (value or "").split(" + ")[0].strip()
    return v or (value or "")


def region_of(slot: dict[str, Any]) -> str | None:
    if slot.get("region"):
        return str(slot["region"])
    v = (slot.get("value") or "").strip()
    if not v:
        return None
    return v.split()[0]


def line_texts(doc: dict[str, Any]) -> list[str]:
    f = doc.get("find") or {}
    slots = doc.get("slots") or {}
    n = int(doc.get("industry_cases") or 0)
    line2 = f.get("line2") or (f"같은 업종 도입사례 {n}건의 제품군으로 후보 찾기" if n else "같은 업종 공개 자료로 후보 찾기")
    prod = short_product((slots.get("product") or {}).get("value")) or "제품"
    region = region_of(slots.get("place") or {}) if (slots.get("place") or {}).get("value") else None
    line3 = f.get("line3") or (f"{region} · {prod} 공개 자료 검색" if region else f"{prod} 공개 자료 검색")
    return [LINE1, line2, line3, LINE4]


def lines(doc: dict[str, Any], active: int) -> list[dict[str, Any]]:
    out = []
    for i, t in enumerate(line_texts(doc), start=1):
        out.append({"n": i, "text": t, "state": "done" if i < active else ("active" if i == active else "wait")})
    return out


async def set_lines(aid: str, active: int, *, cands: int | None = None, **extra: Any) -> dict[str, Any]:
    def upd(d: dict[str, Any]) -> None:
        f = d.setdefault("find", {})
        f.update(extra)
        if cands is not None:
            f["candidates_so_far"] = cands
        f["lines"] = lines(d, active)
        f["active"] = active

    doc = await save(aid, upd)
    f = doc.get("find") or {}
    await step("lines", "active" if active <= 4 else "done", lines=f["lines"], candidates_so_far=int(f.get("candidates_so_far") or 0))
    return doc


# ── 노드 ─────────────────────────────────────────────────
async def read_input(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    budget = await _budget(state["job_id"])
    doc = await doc_of(aid)
    prev = doc.get("slots") or {}
    await set_lines(aid, 1, cands=0, error=None, line2=None, line3=None)
    res = await reading.read(text=doc.get("text"), file_ids=doc.get("file_ids"), requirements_id=doc.get("requirements_id"),
                             rq_version=doc.get("rq_version"), extra_text=doc.get("extra_text"),
                             mi_bundle=doc.get("mi_bundle") if doc.get("input_mode") == "mi" else None, budget=budget)
    slots = reading.author_note_free(res["slots"], res.get("author_note"))
    for k in ("customer", "place"):
        p = prev.get(k) or {}
        if p.get("origin") == "answer" and p.get("value") and not (slots.get(k) or {}).get("value"):
            slots[k] = p
    reqs = list(res.get("requirements") or [])
    if doc.get("text") and doc.get("input_mode") == "free":
        reqs.append({"id": None, "text": doc["text"][:1500], "weight": None, "origin": "input"})

    def upd(d: dict[str, Any]) -> None:
        d["slots"] = slots
        d["segment"] = res["segment"]
        d["rfp"] = res["rfp"]
        d["include_names"] = res["include_names"]
        d["exclude_names"] = res["exclude_names"]
        d["notes"] = res.get("notes") or ""
        d["requirements"] = reqs
        d["files_text"] = (res.get("files_text") or "")[:8000]
        d["chips"] = []
        d["ask"] = None
        if res.get("definition"):
            d["definition"] = res["definition"]
            if res["definition"].get("project_id") and not d.get("project_id"):
                d["project_id"] = res["definition"]["project_id"]
            if res["definition"].get("version") and not d.get("rq_version"):
                d["rq_version"] = res["definition"]["version"]

    await save(aid, upd)
    return {}


async def check_slots(state: FindState) -> dict[str, Any]:
    doc = await doc_of(state["analysis_id"])
    if state.get("auto") or state.get("asked") or doc.get("input_mode") == "mi":
        return {"ask": False}
    return {"ask": rules.should_ask(doc.get("slots") or {}, doc.get("segment") or {})}


def ask_request(doc: dict[str, Any]) -> dict[str, Any]:
    slots = doc.get("slots") or {}
    seg = doc.get("segment") or {}
    read = []
    for k in ("industry", "product", "customer", "place"):
        s = slots.get(k) or {}
        if s.get("value") and s.get("found") != "empty":
            read.append({"key": k, "label": rules.SLOT_LABEL[k], "value": s["value"], "partial": s.get("found") == "partial"})
    missing = [k for k in ("customer", "place") if (slots.get(k) or {}).get("found", "empty") == "empty"]
    read_txt = rules.join_with_gwa([(r["label"], r["value"]) for r in read])
    miss_txt = "와 ".join(rules.SLOT_LABEL[k] for k in missing) if len(missing) == 2 else (rules.SLOT_LABEL[missing[0]] if missing else "")
    if read_txt:
        last = read[-1]["label"]
        desc = f"입력에서 {read_txt}{rules.josa(last, '은', '는')} 읽었지만 {miss_txt}{rules.josa(miss_txt, '이', '가')} 없어요. 알려 주면 지역 경쟁사까지 찾아요."
    else:
        desc = f"입력에서 {miss_txt}{rules.josa(miss_txt, '을', '를')} 읽지 못했어요. 알려 주면 지역 경쟁사까지 찾아요."
    top = [{"code": c["code"], "confidence": c["confidence"]} for c in (seg.get("candidates") or [])[:2]]
    return {"kind": "slots", "missing": missing, "read": read, "industry": {"top": top, "ambiguous": bool(seg.get("ambiguous"))},
            "default": {"skip": True}, "title": "어느 고객사, 어느 지역인가요?", "desc": desc}


def _answer(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict) and isinstance(raw.get("value"), dict):
        raw = raw["value"]
    return raw if isinstance(raw, dict) else {"skip": True}


async def ask_slots(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await doc_of(aid)
    req = ask_request(doc)

    def mark(d: dict[str, Any]) -> None:
        d["status"] = "ask"
        d["ask"] = req
        d["last_screen"] = "ask"

    doc = await save(aid, mark)
    await register(doc)
    ans = _answer(interrupt(req))
    # ── 답을 받고 이어서 ──
    customer = str(ans.get("customer") or "").strip()[:60]
    place = str(ans.get("place") or "").strip()[:40]
    if ans.get("skip") or not (customer or place):
        def skip(d: dict[str, Any]) -> None:
            chips = [c for c in d.get("chips") or [] if c not in ("industry_basis", "industry_check")]
            chips.append("industry_basis")
            if (d.get("segment") or {}).get("ambiguous"):
                chips.append("industry_check")
            d["chips"] = chips
            d["status"] = "finding"
            d["ask"] = None
            d["last_screen"] = "finding"

        await save(aid, skip)
        return {"asked": True, "skipped": True}
    budget = await _budget(state["job_id"])
    doc = await doc_of(aid)
    slots = dict(doc.get("slots") or {})
    if customer:
        reading.set_slot(slots, "customer", customer, origin="answer", confidence=1.0)
    if place:
        reading.set_slot(slots, "place", place, origin="answer", confidence=1.0, region=place.split()[0])
    text = "\n".join(filter(None, [doc.get("text"), doc.get("extra_text"), customer, place,
                                   "\n".join(r.get("text") or "" for r in doc.get("requirements") or [] if r.get("origin") != "input")]))
    seg = await reading.classify(text or "-", budget=budget)
    reading.industry_slot(slots, seg, origin=(slots.get("industry") or {}).get("origin") or "input")

    def upd(d: dict[str, Any]) -> None:
        d["slots"] = slots
        d["segment"] = seg
        d["status"] = "finding"
        d["ask"] = None
        d["last_screen"] = "finding"

    await save(aid, upd)
    return {"asked": True, "skipped": False}


async def fill_gaps(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    budget = await _budget(state["job_id"])
    doc = await doc_of(aid)
    slots = dict(doc.get("slots") or {})
    chips = list(doc.get("chips") or [])
    seg = dict(doc.get("segment") or {})
    has = {k: bool((slots.get(k) or {}).get("value")) and (slots.get(k) or {}).get("found") != "empty" for k in rules.SLOT_ORDER}
    sensitive = sensitive_texts(doc)
    # 고객사만 있음 → 공개 자료로 업종 · 장소 추정 + 칩(확인 권장)
    industry_weak = (seg.get("code") in (None, "GEN")) or not has["industry"]
    if has["customer"] and not has["place"] and industry_weak and not has["product"]:
        bag = {"sources": {}, "claims": {}, "citations": []}
        ev: list[dict[str, Any]] = []
        await E.web_gather(bag, ev, budget, task="ca.web_customer", query=f"{slots['customer']['value']} 업종 매장 지역", sensitive=sensitive)
        if ev:
            txt = "\n".join(e["text"] for e in ev)
            try:
                got = await aix.llm("ca.extract_slots", prompts.extract_slots(txt, only=["place", "product"]), prompts.ExtractSlotsOut,
                                    confidential=True, budget=budget)
                if got.place.value:
                    reading.set_slot(slots, "place", got.place.value[:40], origin="inferred", confidence=0.6, region=got.place.region,
                                     evidence_source_ids=[e["source_id"] for e in ev])
                    chips.append("place_inferred")
            except aix.LLMFailed:
                pass
            seg2 = await reading.classify(f"{slots['customer']['value']}\n{txt}", budget=budget)
            if seg2.get("code") not in (None, "GEN"):
                seg = seg2
                reading.industry_slot(slots, seg, origin="inferred")
                slots["industry"]["origin"] = "inferred"
                chips.append("industry_inferred")
            await R.call(R.update_work, aid, lambda w: w.setdefault("find", {}).update(customer_sources=list(bag["sources"].values())))
    ins = await kbx.insights(seg.get("code") or "GEN")
    # 제품 없음 → 업종 사례 상위 제품군(자동 · 칩 없음)
    if not (slots.get("product") or {}).get("value"):
        top = next((p for p in ins.get("products") or [] if p.get("name")), None)
        if top:
            reading.set_slot(slots, "product", top["name"], origin="inferred", confidence=0.6, partial=True, categories=[top["name"]])
    has_customer = bool((slots.get("customer") or {}).get("value"))
    has_place = bool((slots.get("place") or {}).get("value"))
    if has_customer and not has_place and "region_missing" not in chips:
        chips.append("region_missing")                     # 장소만 없음 → 전국 기준
    if not has_customer and not has_place and "industry_basis" not in chips:
        chips.append("industry_basis")                     # 업종 · 제품만 있음 → 업종 기준

    def upd(d: dict[str, Any]) -> None:
        d["slots"] = slots
        d["segment"] = seg
        d["chips"] = list(dict.fromkeys(chips))
        d["industry_cases"] = int(ins.get("cases") or 0)

    await save(aid, upd)
    await set_lines(aid, 2)
    return {}


def sensitive_texts(doc: dict[str, Any]) -> list[str]:
    """검색어에 20자 이상 그대로 쓰면 안 되는 고객 원문(정의서 · RFP · 회의록 · 자유 양식 · 덧붙일 내용)."""
    out = [doc.get("text") or "", doc.get("extra_text") or "", doc.get("files_text") or ""]
    out.extend(r.get("text") or "" for r in doc.get("requirements") or [])
    return [t for t in out if t]


async def gather_candidates(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    budget = await _budget(state["job_id"])
    doc = await doc_of(aid)
    slots = doc.get("slots") or {}
    seg = config.segment((doc.get("segment") or {}).get("code"))
    ins = await kbx.insights(seg.get("code", "GEN"))
    sensitive = sensitive_texts(doc)
    bag: dict[str, Any] = {"sources": {}, "claims": {}, "citations": []}
    ev: list[dict[str, Any]] = []
    product = (slots.get("product") or {}).get("value") or ""
    prod_s = short_product(product)
    groups = [p["name"] for p in ins.get("products") or [] if p.get("name")][:2]
    queries: list[str] = []
    # 업종 신호 — 사내 사례 DB 의 업종 제품군(K1) + 그 제품군 공급사 검색
    if ins.get("cases") and groups:
        k_text = f"{seg['full']} 도입사례 {ins['cases']}건의 제품군: " + ", ".join(f"{p['name']}({p.get('n', 0)}건)" for p in (ins.get("products") or [])[:4])
        sid = E.add_source(bag, {"kind": "kb_case", "subtype": "사례", "title": f"사내 사례 DB · {seg['full']} 제품군", "publisher": "사내 사례 DB",
                                 "url": None, "authority": 2, "mode": "kb", "kb_key": f"insights:{seg['code']}"}, k_text)
        E.evidence(ev, source_id=sid, kind="kb_case", title=f"사내 사례 DB · {seg['full']}", text=k_text, prefix="K")
    if seg.get("code") != "GEN":
        await E.web_gather(bag, ev, budget, task="ca.web_candidates", query=f"{seg['short']} {groups[0] if groups else prod_s} 공급 업체",
                           sensitive=sensitive, queries_log=queries)
    await set_lines(aid, 3, cands=0)
    # 제품 신호
    await E.web_gather(bag, ev, budget, task="ca.web_candidates", query=f"{prod_s} 제조사", sensitive=sensitive, queries_log=queries)
    if groups and groups[0] not in prod_s:
        await E.web_gather(bag, ev, budget, task="ca.web_candidates", query=f"{groups[0]} 솔루션 업체 비교", sensitive=sensitive, queries_log=queries)
    # 장소 신호(장소가 없으면 검색하지 않는다)
    place = slots.get("place") or {}
    if place.get("value") and place.get("found") != "empty":
        region = region_of(place)
        await E.web_gather(bag, ev, budget, task="ca.web_candidates", query=f"{region} {prod_s} 설치 업체", sensitive=sensitive, queries_log=queries)
    # 고객사 신호
    cust = (slots.get("customer") or {}).get("value")
    if cust:
        await E.web_gather(bag, ev, budget, task="ca.web_candidates", query=f"{cust} {prod_s} 도입", sensitive=sensitive, queries_log=queries)
    mentions: list[dict[str, Any]] = []
    web_ev = [e for e in ev if e["id"].startswith("E")]
    if web_ev:
        try:
            out = await aix.llm("ca.candidates_from_text", prompts.candidates_from_text(ev, industry=seg.get("short", ""), product=product),
                                prompts.CandidatesOut, confidential=False, budget=budget)
            texts = [e["text"] for e in web_ev]
            for m in out.candidates:
                name = rules.clean_name(m.name)
                if not name:
                    continue
                # 웹 근거 글 어디에도 이름이 없으면 버린다(지어낸 회사 방지)
                if not any(verify.leaks(t, [name]) for t in texts):
                    continue
                mentions.append({"name": name, "kind_label": m.kind_label[:30], "evidence_id": m.evidence_id, "quote": m.evidence_quote[:200],
                                 "url_guess": m.url_guess})
        except aix.LLMFailed as exc:
            log.info("후보 뽑기 실패: %s", exc.message)
    names = list(dict.fromkeys(m["name"] for m in mentions))

    def wupd(w: dict[str, Any]) -> None:
        w["find"] = {"sources": bag["sources"], "evidence": [{**e, "text": e["text"][:1500]} for e in ev], "mentions": mentions, "queries": queries}

    await R.call(R.update_work, aid, wupd)
    await set_lines(aid, 4, cands=len(names), line2=line_texts(doc)[1], line3=line_texts(doc)[2])
    return {}


def _explicit(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for n in (doc.get("rfp") or {}).get("competitor_mentions") or []:
        out.append({"name": rules.clean_name(n), "origin": "rfp"})
    for n in doc.get("include_names") or []:
        out.append({"name": rules.clean_name(n), "origin": "include"})
    if doc.get("input_mode") == "mi":
        for c in (doc.get("mi_bundle") or {}).get("competitors") or []:
            nm = c.get("real_name") if isinstance(c, dict) else str(c)
            if nm:
                out.append({"name": rules.clean_name(nm), "origin": "mi", "aliases": list(c.get("aliases") or []) if isinstance(c, dict) else [],
                            "kind_label": (c.get("kind_label") or "") if isinstance(c, dict) else "", "why": (c.get("desc") or "") if isinstance(c, dict) else ""})
    return [x for x in out if x["name"]]


async def resolve_entities(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    budget = await _budget(state["job_id"])
    doc = await doc_of(aid)
    work = await R.call(R.get_work, aid)
    f = work.get("find") or {}
    mentions = f.get("mentions") or []
    explicit = _explicit(doc)
    names = list(dict.fromkeys([m["name"] for m in mentions] + [x["name"] for x in explicit]))
    groups: list[dict[str, Any]] = []
    if len(names) >= 2:
        try:
            out = await aix.llm("ca.resolve_entities", prompts.resolve_entities(names), prompts.ResolveOut, confidential=False, budget=budget)
            for g in out.groups:
                members = [rules.clean_name(x) for x in [g.canonical, *g.aliases] if x]
                if any(rules.same_company(n, members) for n in names):
                    groups.append({"canonical": rules.clean_name(g.canonical), "aliases": [a for a in members if a != rules.clean_name(g.canonical)]})
        except aix.LLMFailed:
            pass
    entities: list[dict[str, Any]] = []

    def find_entity(name: str) -> dict[str, Any] | None:
        for e in entities:
            if rules.same_company(name, [e["name"], *e["aliases"]]):
                return e
        return None

    for n in names:
        g = next((g for g in groups if rules.same_company(n, [g["canonical"], *g["aliases"]])), None)
        canon = g["canonical"] if g else n
        aliases = list(g["aliases"]) if g else []
        e = find_entity(canon) or find_entity(n)
        if e is None:
            e = {"name": canon, "aliases": [a for a in aliases if a != canon], "mentions": [], "origin": "auto", "kind_label": "", "why": ""}
            entities.append(e)
        if n != e["name"] and n not in e["aliases"]:
            e["aliases"].append(n)
        for m in mentions:
            if rules.same_company(m["name"], [n]):
                e["mentions"].append(m)
                e["kind_label"] = e["kind_label"] or m.get("kind_label") or ""
        for x in explicit:
            if rules.same_company(x["name"], [n]):
                if e["origin"] == "auto" or x["origin"] == "mi":
                    e["origin"] = x["origin"]
                e["aliases"] = list(dict.fromkeys(e["aliases"] + [a for a in x.get("aliases") or [] if a != e["name"]]))
                e["kind_label"] = e["kind_label"] or x.get("kind_label") or ""
                e["why"] = e["why"] or x.get("why") or ""
    # 자기 회사 · 고객사 · 뺄 곳 제외
    customer = (doc.get("slots") or {}).get("customer", {}).get("value") or ""
    excl = [rules.clean_name(x) for x in doc.get("exclude_names") or []]
    kept = []
    for e in entities:
        all_names = [e["name"], *e["aliases"]]
        if any(rules.is_self_entity(n) for n in all_names):
            continue
        if customer and any(rules.same_company(n, [customer]) for n in all_names):
            continue
        if excl and any(rules.same_company(n, excl) for n in all_names):
            continue
        kept.append(e)
    await R.call(R.update_work, aid, lambda w: w.setdefault("find", {}).update(entities=kept))
    return {}


async def score(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    budget = await _budget(state["job_id"])
    doc = await doc_of(aid)
    work = await R.call(R.get_work, aid)
    f = work.get("find") or {}
    entities = f.get("entities") or []
    ev = f.get("evidence") or []
    kind_of = {e["id"]: (f.get("sources") or {}).get(e["source_id"], {}).get("kind") or e.get("kind") for e in ev}
    slots = doc.get("slots") or {}
    slot_txt = {k: (slots.get(k) or {}).get("value") or "" for k in rules.SLOT_ORDER}
    present = rules.present_signals(slots)
    scored: dict[str, Any] = {}
    if entities:
        try:
            out = await aix.llm("ca.score_signals", prompts.score_signals([e["name"] for e in entities], ev, slot_txt), prompts.ScoreOut,
                                confidential=True, budget=budget)
            for sc in out.candidates:
                e = next((x for x in entities if rules.same_company(sc.name, [x["name"], *x["aliases"]])), None)
                if e is not None and e["name"] not in scored:
                    scored[e["name"]] = sc
        except aix.LLMFailed as exc:
            log.info("신호 점수 실패: %s", exc.message)
    ev_texts = [e["text"] for e in ev]
    for e in entities:
        sc: prompts.ScoredCandidate | None = scored.get(e["name"])
        sig: dict[str, Any] = {}
        for k in rules.SIGNALS:
            raw = getattr(sc.signals, k) if sc else prompts.SignalScore()
            ids = [i for i in raw.source_ids if i in kind_of]
            s = rules.cap_signal(raw.s, source_kinds=[kind_of[i] for i in ids], partial=bool(raw.partial), key=k)
            sig[k] = {"s": s, "partial": bool(raw.partial) if k == "product" else False,
                      "evidence_source_ids": list(dict.fromkeys(next((x["source_id"] for x in ev if x["id"] == i), "") for i in ids))}
        e["signals"] = sig
        e["confidence"] = rules.confidence(sig, present) if sc or e["origin"] == "auto" else None
        e["chips"] = rules.evidence_chips(sig, present)
        why = (sc.why if sc else "") or e.get("why") or ""
        why, _ = verify.scrub_numbers(why, ev_texts)
        if sig["product"]["partial"] and "제품 일부 겹침" not in why:
            why = (why + " (제품 일부 겹침)").strip()
        e["why"] = why[:60]
        e["kind_label"] = ((sc.kind_label if sc else "") or e.get("kind_label") or "")[:30]
        e["evidence_source_ids"] = list(dict.fromkeys(x["source_id"] for x in ev for m in e["mentions"] if x["id"] == m.get("evidence_id")))
        e["url_guess"] = next((m.get("url_guess") for m in e["mentions"] if m.get("url_guess")), None)
    await R.call(R.update_work, aid, lambda w: w.setdefault("find", {}).update(entities=entities))
    return {}


def free_letters(used: set[str], n: int) -> list[str]:
    out, i = [], 0
    while len(out) < n:
        L = rules.letter_at(i)
        if L not in used:
            out.append(L)
        i += 1
    return out


async def select(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await doc_of(aid)
    work = await R.call(R.get_work, aid)
    entities = (work.get("find") or {}).get("entities") or []
    cap = rules.cap_for(rules.cap_signals(doc.get("slots") or {}))
    existing = list(doc.get("competitors") or [])
    excl = [rules.clean_name(x) for x in doc.get("exclude_names") or []]
    kept: list[dict[str, Any]] = []
    matched: set[str] = set()
    # 사용자가 넣고 뺀 곳(고정)은 그대로
    for c in existing:
        names = [c.get("real_name") or "", *(c.get("aliases") or [])]
        e = next((x for x in entities if rules.same_company(x["name"], names)), None)
        if c.get("pinned") or c.get("origin") in ("user", "rfp", "include", "mi"):
            if excl and any(rules.same_company(n, excl) for n in names) and c.get("origin") != "user":
                c.update(removed=True, on=False, pinned=True)
            if e:
                matched.add(e["name"])
                c["kind_label"] = c.get("kind_label") or e.get("kind_label") or ""
                c["why"] = c.get("why") or e.get("why") or ""
            kept.append(c)
    auto_new: list[dict[str, Any]] = []
    prev_auto = [c for c in existing if c not in kept]
    for e in entities:
        if e["name"] in matched:
            continue
        status = rules.status_for(e.get("confidence")) if e.get("confidence") is not None else "rec"
        explicit = e.get("origin") in ("rfp", "include", "mi")
        prev = next((c for c in prev_auto if rules.same_company(e["name"], [c.get("real_name") or "", *(c.get("aliases") or [])])), None)
        cand = {
            "id": prev["id"] if prev else R.nid("cmp"), "letter": prev.get("letter") if prev else None, "real_name": e["name"],
            "aliases": e.get("aliases") or [], "kind_label": e.get("kind_label") or "", "why": e.get("why") or "", "signals": e.get("signals") or {},
            "chips": e.get("chips") or [], "confidence": e.get("confidence"), "status": status, "on": True if explicit else status == "rec",
            "pinned": explicit, "removed": False, "origin": e.get("origin") or "auto", "evidence_source_ids": e.get("evidence_source_ids") or [],
            "url_guess": e.get("url_guess"), "found_at": now_iso(),
        }
        (kept if explicit else auto_new).append(cand)
    chosen = rules.select_auto(auto_new, cap)
    final = kept + chosen
    used = {c["letter"] for c in final if c.get("letter")}
    need = [c for c in sorted(final, key=rules.sort_key) if not c.get("letter")]
    for c, L in zip(need, free_letters(used, len(need))):
        c["letter"] = L
    final = service.ordered(final)
    for i, c in enumerate(final):
        c["rank"] = i
    # 사라진 자동 후보는 지운다(고정 · 직접 추가는 위에서 남김)
    removed_auto = [c for c in existing if c not in kept and c["id"] not in {x["id"] for x in final}]

    def upd(d: dict[str, Any]) -> None:
        d["competitors"] = final

    await save(aid, upd)
    await set_lines(aid, 4, cands=sum(1 for c in final if not c.get("removed")))
    log.info("후보 %d곳(자동 %d · 고정 %d · 지운 자동 %d)", len(final), len(chosen), len(kept), len(removed_auto))
    return {}


def _short_name(text: str, n: int = 10) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    t = re.sub(r"(을|를|이|가|은|는|에서|으로|로|의|와|과)\b", "", t)
    words = t.split()
    out = ""
    for w in words:
        if len((out + " " + w).strip()) > n:
            break
        out = (out + " " + w).strip()
    return out or t[:n]


async def make_criteria(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    budget = await _budget(state["job_id"])
    doc = await doc_of(aid)
    seg = config.segment((doc.get("segment") or {}).get("code"))
    ins = await kbx.insights(seg.get("code", "GEN"))
    reqs: list[dict[str, Any]] = []
    for t in (doc.get("rfp") or {}).get("eval_criteria") or []:
        reqs.append({"text": t, "source": "rfp", "ref": None})
    defs = [r for r in doc.get("requirements") or [] if r.get("origin") in ("definition", "mi")]
    defs.sort(key=lambda r: -(r.get("weight") or 0))
    for r in defs[:12]:
        reqs.append({"text": r["text"], "source": "requirements", "ref": r.get("id")})
    for r in doc.get("requirements") or []:
        if r.get("origin") == "input":
            reqs.append({"text": r["text"], "source": "free", "ref": None})
    used: set[str] = set()
    industry = []
    for rt in ins.get("req_types") or []:
        nm = kbx.req_type_name(rt, used)
        used.add(nm)
        industry.append({"code": rt.get("code"), "example": nm, "n": int(rt.get("n") or 0)})
    names: list[dict[str, Any]] = []
    ind_names: dict[str, str] = {}
    if reqs or industry:
        try:
            out = await aix.llm("ca.make_criteria", make_criteria_prompt(reqs, industry), MakeCriteriaOutX, confidential=True, budget=budget)
            # RFP 평가 기준 → 정의서 → 자유 양식(모델이 순서를 바꿔도 RFP 평가 기준이 앞자리)
            rank = {"rfp": 0, "requirements": 1, "free": 2}
            got = sorted((c for c in out.criteria if c.name.strip()), key=lambda c: rank.get(c.source, 1))
            names = [{"name": c.name.strip()[:10], "requirement_ref": c.requirement_ref} for c in got][:3]
            ind_names = {i.code: i.name.strip()[:10] for i in out.industry if i.name.strip()}
        except aix.LLMFailed:
            names = [{"name": _short_name(r["text"]), "requirement_ref": r.get("ref")} for r in reqs[:3] if r.get("text")]
    ind = [{"name": ind_names.get(i["code"]) or _short_name(i["example"]), "n": i["n"]} for i in industry]
    if doc.get("criteria_mode") == "pin" and doc.get("criteria"):
        crits = doc["criteria"]
    else:
        crits = rules.compose_criteria(names, ind)
        for c in crits:
            c["id"] = R.nid("crt")
    sugg = rules.criteria_suggestions(ind, crits)

    def upd(d: dict[str, Any]) -> None:
        d["criteria"] = crits
        d["criteria_suggestions"] = sugg
        d["industry_cases"] = int(ins.get("cases") or 0)
        if d.get("criteria_mode") != "pin":
            d["criteria_mode"] = "auto"

    await save(aid, upd)
    return {}


class IndustryName(BaseModel):
    code: str
    name: str = Field(description="10자 이내 비교 기준 이름")


class MakeCriteriaOutX(prompts.MakeCriteriaOut):
    industry: list[IndustryName] = Field(default_factory=list)


def make_criteria_prompt(reqs: list[dict[str, Any]], industry: list[dict[str, Any]]) -> str:
    base = prompts.make_criteria(reqs)
    ind = "\n".join(f"- [{i['code']}] {i['example']} (사례 {i['n']}건)" for i in industry)
    return base + ("\n\n업종 사례 요구 유형도 각각 10자 이내 비교 기준 이름으로 바꿔 industry 에 넣어라(code 그대로).\n" + ind if ind else "")


async def title_node(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    budget = await _budget(state["job_id"])
    doc = await doc_of(aid)
    if not doc.get("title_auto", True) and doc.get("title"):
        return {}
    slots = doc.get("slots") or {}
    cust = (slots.get("customer") or {}).get("value")
    ind = (slots.get("industry") or {}).get("value") or config.segment((doc.get("segment") or {}).get("code")).get("short", "")
    prod = short_product((slots.get("product") or {}).get("value")) or "제품"
    rule_title = f"{cust or ind} {prod} 경쟁사 분석"
    title = rule_title
    try:
        out = await aix.llm("ca.title", prompts.title(cust, ind, prod), prompts.TitleOut, confidential=True, budget=budget)
        t = re.sub(r"\s+", " ", out.title).strip()
        names = [n for c in doc.get("competitors") or [] for n in [c.get("real_name") or "", *(c.get("aliases") or [])] if n]
        if t and not verify.leaks(t, names):                 # 제목에 경쟁사 실명 금지(AC-CA-47)
            title = t
    except aix.LLMFailed:
        pass
    if len(title) > 24:
        title = title.removesuffix(" 분석") if len(title.removesuffix(" 분석")) <= 24 else title[:24]
    await save(aid, lambda d: d.update(title=title.strip(), title_auto=True))
    return {}


async def save_node(state: FindState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await doc_of(aid)
    live = service.live_competitors(doc)
    if not live:
        raise FindFailed("경쟁사를 찾지 못했어요")
    auto = bool(state.get("auto"))

    def upd(d: dict[str, Any]) -> None:
        d["status"] = "confirming"
        d["current_job_id"] = None
        d["current_job_kind"] = None
        d["last_screen"] = "candidates"
        f = d.setdefault("find", {})
        f["lines"] = lines(d, 5)
        f["active"] = 5
        f["finished_at"] = now_iso()
        if auto:
            comps = d.get("competitors") or []
            rec = [c for c in comps if c.get("status") == "rec" and not c.get("removed")]
            if rec:
                for c in comps:
                    if not c.get("pinned"):
                        c["on"] = c in rec
            else:
                checks = sorted([c for c in comps if c.get("status") == "check" and not c.get("removed")], key=rules.sort_key)[:2]
                for c in comps:
                    if not c.get("pinned"):
                        c["on"] = c in checks
            if "auto_confirmed" not in (d.get("chips") or []):
                d.setdefault("chips", []).append("auto_confirmed")

    doc = await save(aid, upd)
    await step("lines", "done", lines=(doc.get("find") or {}).get("lines") or [], candidates_so_far=len(live))
    if doc.get("requirements_id"):
        await rqx.register_link(doc["requirements_id"], aid, title=doc.get("title") or "경쟁사 분석", route=service.route_for(doc),
                                rq_version=int(doc.get("rq_version") or 0),
                                item_ids=[r["id"] for r in doc.get("requirements") or [] if r.get("origin") == "definition" and r.get("id")])
    next_job = None
    if auto:
        from ..deps import start_run

        next_job = await start_run(doc, "full")
    else:
        await register(doc)
    return {"next_job": next_job}


class FindFailed(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.code = "NOT_FOUND_COMPETITORS"
        self.message = message


def build() -> StateGraph:
    g = StateGraph(FindState)
    for name, fn in (("read_input", read_input), ("check_slots", check_slots), ("ask_slots", ask_slots), ("fill_gaps", fill_gaps),
                     ("gather_candidates", gather_candidates), ("resolve_entities", resolve_entities), ("score", score), ("select", select),
                     ("make_criteria", make_criteria), ("title", title_node), ("save", save_node)):
        g.add_node(name, fn)
    g.add_edge(START, "read_input")
    g.add_edge("read_input", "check_slots")
    g.add_conditional_edges("check_slots", lambda s: "ask_slots" if s.get("ask") else "fill_gaps", ["ask_slots", "fill_gaps"])
    g.add_edge("ask_slots", "fill_gaps")
    g.add_edge("fill_gaps", "gather_candidates")
    g.add_edge("gather_candidates", "resolve_entities")
    g.add_edge("resolve_entities", "score")
    g.add_edge("score", "select")
    g.add_edge("select", "make_criteria")
    g.add_edge("make_criteria", "title")
    g.add_edge("title", "save")
    g.add_edge("save", END)
    return g


STEP_LABELS = {"read_input": "입력 읽기", "check_slots": "빈 칸 판정", "ask_slots": "고객사 · 장소 묻기", "fill_gaps": "빈 칸 채우기",
               "gather_candidates": "후보 찾기", "resolve_entities": "이름 합치기", "score": "신뢰 점수", "select": "후보 고르기",
               "make_criteria": "비교 기준", "title": "제목", "save": "저장"}


async def handle(ctx: JobContext) -> dict[str, Any] | None:
    aid = ctx.payload["analysis_id"]
    init: FindState = {"analysis_id": aid, "job_id": ctx.job.id, "auto": bool(ctx.payload.get("auto")), "asked": False}
    try:
        final = await run_graph(ctx, build(), dict(init), step_labels=STEP_LABELS)
    except AwaitingInput:
        raise
    except JobCanceled:
        await _cleanup(aid, ctx, "draft")
        _BUDGETS.pop(ctx.job.id, None)
        raise
    except Exception as exc:
        msg = getattr(exc, "message", None) or "경쟁사를 찾지 못했어요"
        if isinstance(exc, ApiError) and exc.code == "POLICY_CONFIDENTIAL":
            msg = "고객 자료를 보낼 수 없는 모델이라 찾지 못했어요"
        await _cleanup(aid, ctx, "failed", error=msg)
        _BUDGETS.pop(ctx.job.id, None)
        raise
    _BUDGETS.pop(ctx.job.id, None)
    doc = await R.call(R.get_analysis, aid) or {}
    return {"analysis_id": aid, "status": doc.get("status"), "next_job_id": (final or {}).get("next_job")}


async def _cleanup(aid: str, ctx: JobContext, status: str, error: str | None = None) -> None:
    try:
        doc = await R.call(R.get_analysis, aid)
        if not doc or doc.get("current_job_id") not in (ctx.job.id, None):
            return

        def upd(d: dict[str, Any]) -> None:
            d["status"] = status
            d["current_job_id"] = None
            d["current_job_kind"] = None
            d["ask"] = None
            if error:
                d.setdefault("find", {})["error"] = error
            d["last_screen"] = "finding" if status == "failed" else "input"

        saved = await save(aid, upd)
        await register(saved)
    except Exception:  # noqa: BLE001
        log.exception("찾기 정리 실패")


__all__ = ["handle", "build", "ask_request", "jobs"]
