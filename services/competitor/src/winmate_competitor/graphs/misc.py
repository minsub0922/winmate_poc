"""짧은 잡(§7.8) — 모두 직선 그래프(run_graph: 노드마다 step 이벤트 · 취소 확인 · 체크포인트).

- ca.candidate_add: 이름 → 1회 검색으로 유형 · 근거 한 줄(신호 점수는 표시 안 함) → 켜짐 · 고정 · 다음 글자(행은 API 가 먼저 만든다)
- ca.research: 한 경쟁사의 지정 사실(없으면 `[확인 필요]` 항목)을 다른 검색어로 다시 → 그 경쟁사 판정 · 강점 다시 → 새 버전(kind=research)
- ca.recheck: 30일 뒤 신제품 · 출처 변경 → `upd` + 배너 · 알림 / 없으면 그대로 · 30일 뒤 다시 예약
- ca.export: PDF 리포트(사내용 = 실명, 표지 `사내용 · 고객 제출 금지`) → export 서비스 → file_id
- ca.source_add: 출처 직접 추가(URL · 사내 문서) → 대조 → 주장 인용 추가
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
from datetime import date, timedelta
from typing import Any

from winmate_common import platform
from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.jobs import JobContext, jobs

from .. import aix, bundle, config, judging, prompts, rules, service, verify
from .. import evidence as E
from .. import store as R
from . import analyze as A
from .common import S, doc_of, register, run_linear, save

log = logging.getLogger("winmate.competitor.misc")


def _cmp(doc: dict[str, Any], cid: str) -> dict[str, Any]:
    c = next((x for x in doc.get("competitors") or [] if x["id"] == cid), None)
    if c is None:
        raise RuntimeError(f"경쟁사가 없어요: {cid}")
    return c


# ── ca.candidate_add ─────────────────────────────────────
async def handle_candidate_add(ctx: JobContext) -> dict[str, Any]:
    async def profile(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        p = state["p"]
        doc = await doc_of(aid)
        c = _cmp(doc, p["competitor_id"])
        from .find import sensitive_texts, short_product

        product = short_product(((doc.get("slots") or {}).get("product") or {}).get("value")) or ""
        budget = await aix.init_budget("find")
        budget.websearch, budget.llm = 1, 1
        bag: dict[str, Any] = {"sources": {}, "claims": {}, "citations": []}
        ev: list[dict[str, Any]] = []
        await E.web_gather(bag, ev, budget, task="ca.web_profile", query=f"{c['real_name']} {product}".strip(), sensitive=sensitive_texts(doc),
                           competitor_id=c["id"])
        kind, why, url = "", "", None
        aliases: list[str] = []
        if ev:
            texts = [e["text"] for e in ev]
            try:
                out = await aix.llm("ca.candidate_profile", prompts.candidate_profile(c["real_name"], ev, product), prompts.CandidateProfileOut,
                                    confidential=False, budget=budget)
                kind = out.kind_label[:30]
                why, _ = verify.scrub_numbers(out.why or "", texts)
                url = out.url_guess
                # 근거 글에 실제로 나온 다른 표기만 별칭으로(같은 회사 다시 추가 → 409)
                for a in out.aliases[:5]:
                    a = rules.clean_name(a)
                    if a and a != c["real_name"] and any(verify.leaks(t, [a]) for t in texts) and not rules.is_self_entity(a):
                        aliases.append(a[:60])
            except aix.LLMFailed:
                pass

        def upd(d: dict[str, Any]) -> None:
            for x in d.get("competitors") or []:
                if x["id"] == c["id"]:
                    x["kind_label"] = x.get("kind_label") or kind
                    x["why"] = x.get("why") or why[:60]
                    x["url_guess"] = x.get("url_guess") or url
                    x["aliases"] = list(dict.fromkeys([*(x.get("aliases") or []), *aliases]))
                    x["add_state"] = "done"
                    x["evidence_source_ids"] = list(bag["sources"].keys())

        await save(aid, upd)
        return {"result": {"analysis_id": aid, "competitor_id": c["id"]}}

    try:
        return await run_linear(ctx, [("profile", profile)], {"profile": "경쟁사 유형 찾기"})
    except Exception:
        aid = ctx.payload["analysis_id"]
        cid = ctx.payload.get("competitor_id")
        await save(aid, lambda d: [x.update(add_state="failed") for x in d.get("competitors") or [] if x["id"] == cid])
        raise


# ── ca.research ──────────────────────────────────────────
async def handle_research(ctx: JobContext) -> dict[str, Any]:
    async def research(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        p = state["p"]
        doc = await doc_of(aid)
        c = _cmp(doc, p["competitor_id"])
        v = await R.call(R.get_version, aid, int(doc.get("result_version") or 0)) or {}
        work = await R.call(R.get_work, aid)
        facts_now = ((work.get("competitors") or {}).get(c["id"]) or {}).get("facts") or (v.get("facts") or {}).get(c["id"]) or {}
        keys = [k for k in (p.get("facts") or []) if k in config.fact_order()]
        if not keys:
            keys = [k for k in config.fact_order() if (facts_now.get(k) or {}).get("tbd", True)] or list(config.fact_order())
        queries = A.fact_queries(doc, c, A.FACT_QUERY_ALT)
        budget = await aix.init_budget("analyze")
        from .find import sensitive_texts

        local: dict[str, Any] = {"sources": {}, "claims": {}, "citations": []}
        ev: list[dict[str, Any]] = []
        for key in keys:
            await E.web_gather(local, ev, budget, task="ca.web_research", query=queries[key], sensitive=sensitive_texts(doc),
                               competitor_id=c["id"], fact_key=key)
            await ctx.check_cancel()
        new: dict[str, Any] = {}
        if ev:
            try:
                out = await aix.llm("ca.extract_facts", prompts.extract_facts(c["real_name"], ev, recent_months=int(config.th("recent_months", 12))),
                                    prompts.ExtractFactsOut, confidential=False, budget=budget)
                new = judging.facts_from_llm(local, c["id"], out, ev, keys=keys)
            except aix.LLMFailed:
                new = {}
        replace = [k for k in keys if k in new and not new[k].get("tbd")]
        if not (work.get("competitors") or {}).get(c["id"]) and (v.get("facts") or {}).get(c["id"]):
            # 작업본이 비었으면(복원 등) 현재 버전을 작업본으로 되살린다
            await R.call(R.update_work, aid, lambda w: _seed_work(w, v))
        await A.merge_local(aid, c["id"], local, new, keys=replace, state="done", done_facts=[])
        crits = service.enabled_criteria(doc)
        await A.judge_one(doc, c, crits)
        work = await R.call(R.get_work, aid)
        cids = [x for x in (v.get("competitor_ids") or []) if (work.get("competitors") or {}).get(x, {}).get("facts")] or [c["id"]]
        await A._strengths_into_work(doc, work, cids, use_llm=True)
        work = await R.call(R.get_work, aid)
        n = await A.save_version(doc, work, cids, kind="research", stopped=bool(v.get("stopped")))

        def upd(d: dict[str, Any]) -> None:
            d["result_version"] = n
            d["research"] = None
            d["edited_at"] = now_iso()

        saved = await save(aid, upd)
        await register(saved)
        return {"result": {"analysis_id": aid, "version": n, "competitor_id": c["id"], "facts": replace}}

    try:
        return await run_linear(ctx, [("research", research)], {"research": "경쟁사 더 찾기"})
    finally:
        await save(ctx.payload["analysis_id"], lambda d: d.update(research=None) if (d.get("research") or {}).get("job_id") == ctx.job.id else None)


def _seed_work(w: dict[str, Any], v: dict[str, Any]) -> None:
    w["claims"] = copy.deepcopy(v.get("claims") or {})
    w["citations"] = copy.deepcopy(v.get("citations") or [])
    w["sources"] = copy.deepcopy(v.get("sources") or {})
    w["samsung_cells"] = copy.deepcopy(v.get("samsung_cells") or {})
    w["samsung_products"] = copy.deepcopy(v.get("samsung_products") or [])
    comps = {}
    for cid in v.get("competitor_ids") or []:
        comps[cid] = {"state": "done", "facts": copy.deepcopy((v.get("facts") or {}).get(cid) or {}),
                      "positioning": copy.deepcopy((v.get("positioning") or {}).get(cid) or {}),
                      "verdicts": [x for x in v.get("verdicts") or [] if x.get("competitor_id") == cid], "done_facts": list(config.fact_order())}
    w["competitors"] = comps


# ── ca.recheck ───────────────────────────────────────────
async def handle_recheck(ctx: JobContext) -> dict[str, Any]:
    async def recheck(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        doc = await R.call(R.get_analysis, aid)
        if not doc:
            return {"result": {"analysis_id": aid, "skipped": "deleted"}}
        v = await R.call(R.get_version, aid, int(doc.get("result_version") or 0))
        if not v or doc.get("status") not in ("done", "upd", "stopped"):
            return {"result": {"analysis_id": aid, "skipped": doc.get("status")}}
        since = (doc.get("analyzed_at") or now_iso())[:10]
        budget = await aix.init_budget("analyze")
        budget.websearch = max(1, len(v.get("competitor_ids") or []))
        changes: list[dict[str, Any]] = []
        from .find import sensitive_texts

        for cid in v.get("competitor_ids") or []:
            c = next((x for x in doc.get("competitors") or [] if x["id"] == cid), None) or (v.get("competitors") or {}).get(cid) or {}
            name = c.get("real_name")
            if not name:
                continue
            letter = c.get("letter") or (v.get("competitors") or {}).get(cid, {}).get("letter")
            bag: dict[str, Any] = {"sources": {}, "claims": {}, "citations": []}
            ev: list[dict[str, Any]] = []
            await E.web_gather(bag, ev, budget, task="ca.web_recheck", query=f"{name} 신제품 출시", sensitive=sensitive_texts(doc), competitor_id=cid)
            if not ev:
                continue
            try:
                out = await aix.llm("ca.recheck_news", prompts.recheck_news(name, since, ev), prompts.RecheckNewsOut, confidential=False)
            except aix.LLMFailed:
                continue
            web = any(s.get("kind") == "web" for s in bag["sources"].values())
            for it in out.items:
                d = _date(it.date)
                if not d or d.isoformat() <= since:
                    continue
                if it.quote and not any(verify.leaks(e["text"], [it.quote[:30]]) for e in ev):
                    continue
                names = [name, *(c.get("aliases") or [])]
                changes.append({"id": R.nid("chg"), "kind": "competitor_new_product", "competitor_id": cid, "letter": letter,
                                "title": f"경쟁사 {letter} 신제품 발표", "summary": verify.replace_names(it.summary, names, f"경쟁사 {letter}")[:120],
                                "product": verify.replace_names(it.product, names, f"경쟁사 {letter}")[:60], "date": d.isoformat(),
                                "detected_at": now_iso(), "verification": "matched" if web else "needs_check"})
                break
        # URL 있는 출처 다시 수집 → 인용 구절이 사라졌으면 source_changed
        for sid, s in (v.get("sources") or {}).items():
            if s.get("kind") != "web" or not s.get("url"):
                continue
            if not budget.take("fetch"):
                break
            page = await aix.fetch(s["url"])
            if not page:
                continue
            text = verify.N(page.get("text") or "\n".join(page.get("pages") or []))
            quotes = [c["quote"] for c in v.get("citations") or [] if c.get("source_id") == sid and c.get("quote")]
            if quotes and not any(verify.N(q) in text for q in quotes):
                cid = next(iter(s.get("competitor_ids") or []), None)
                letter = ((v.get("competitors") or {}).get(cid) or {}).get("letter") if cid else None
                changes.append({"id": R.nid("chg"), "kind": "source_changed", "competitor_id": cid, "letter": letter,
                                "title": f"경쟁사 {letter} 출처 내용 변경" if letter else "출처 내용 변경", "summary": "인용한 구절이 원문에서 사라졌어요",
                                "product": None, "date": None, "detected_at": now_iso(), "verification": "matched"})
        chk = {"id": R.nid("chk"), "analysis_id": aid, "scheduled_for": doc.get("next_recheck_at"), "ran_at": now_iso(), "job_id": ctx.job.id,
               "result": "changes" if changes else "no_change", "changes": changes}
        await R.call(R.put_doc, R.CHK, chk["id"], chk)
        if changes:
            def upd(d: dict[str, Any]) -> None:
                d["status"] = "upd"
                d["changes"] = changes
                d["recheck"] = {**(d.get("recheck") or {}), "checked_at": now_iso(), "last": chk["id"]}

            saved = await save(aid, upd)
            await register(saved)
            await jobs().push_notification(doc.get("owner_id") or "system", {
                "type": "ca_update", "service": config.SERVICE, "ref": aid, "title": service.display_title(saved),
                "message": service.banner_text(saved), "route": service.route_for(saved)})
        else:
            run_at = config.now() + timedelta(days=config.recheck_days())
            await A.schedule_recheck(doc, run_at.timestamp())

            def upd2(d: dict[str, Any]) -> None:
                d["next_recheck_at"] = run_at.isoformat().replace("+00:00", "Z")
                d["recheck"] = {**(d.get("recheck") or {}), "checked_at": now_iso(), "last": chk["id"]}

            await save(aid, upd2)
        return {"result": {"analysis_id": aid, "changes": len(changes)}}

    return await run_linear(ctx, [("recheck", recheck)], {"recheck": "30일 재확인"})


def _date(s: str | None) -> date | None:
    if not s:
        return None
    m = re.match(r"(\d{4})[-.](\d{1,2})(?:[-.](\d{1,2}))?", s.strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 28))
    except ValueError:
        return None


# ── ca.export ────────────────────────────────────────────
async def handle_export(ctx: JobContext) -> dict[str, Any]:
    async def export(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        p = state["p"]
        doc = await doc_of(aid)
        v = await R.call(R.get_version, aid, int(doc.get("result_version") or 0))
        if not v:
            raise ApiError(422, "NO_RESULT", "아직 분석 결과가 없어요")
        audience = p.get("audience") or "internal"
        report = bundle.report_document(doc, v, audience=audience)
        fname = f"{service.display_title(doc)}_{'사내용' if audience == 'internal' else '고객용'}.pdf"
        res = await ServiceClient("export", timeout=180).post("/v1/exports", json={
            "format": "pdf", "filename": fname, "document": {"report": report}, "confidential": audience == "internal",
            "project_id": doc.get("project_id"), "source_ref": aid})
        file = res.get("file") if isinstance(res, dict) else None
        if not file and res.get("export_id"):
            for _ in range(240):
                await asyncio.sleep(0.5)
                rec = await ServiceClient("export").get(f"/v1/exports/{res['export_id']}")
                if rec.get("status") == "done" and rec.get("file"):
                    file = rec["file"]
                    break
                if rec.get("status") == "failed":
                    raise ApiError(502, "EXPORT_FAILED", "리포트를 만들지 못했어요")
        if not file:
            raise ApiError(502, "EXPORT_FAILED", "리포트를 만들지 못했어요")
        if audience == "internal":
            hof = R.nid("hof")
            await R.call(R.put_doc, R.HOF, hof, {"analysis_id": aid, "version": int(doc.get("result_version") or 0), "target": "report",
                                                 "target_id": file["id"], "target_title": fname, "status": "delivered", "confirmations": {},
                                                 "anonymization_map": {}, "served_named_at": [now_iso()], "created_at": now_iso()})
            saved = await R.call(R.get_analysis, aid)
            if saved:
                await register(saved)
        return {"result": {"analysis_id": aid, "file_id": file["id"], "url": file.get("url"), "name": file.get("name"), "export_id": res.get("export_id")}}

    return await run_linear(ctx, [("export", export)], {"export": "리포트 만들기"})


# ── ca.source_add ────────────────────────────────────────
async def handle_source_add(ctx: JobContext) -> dict[str, Any]:
    async def add(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        p = state["p"]
        doc = await doc_of(aid)
        n = int(doc.get("result_version") or 0)
        v = await R.call(R.get_version, aid, n)
        if not v:
            raise ApiError(422, "NO_RESULT", "아직 분석 결과가 없어요")
        bag = {"sources": v.get("sources") or {}, "claims": v.get("claims") or {}, "citations": v.get("citations") or []}
        budget = aix.Budget(websearch=0, fetch=1, llm=0)
        caps = await aix.capabilities()
        budget.mode = aix.web_mode(caps)
        ev: list[dict[str, Any]] = []
        sid = None
        if p.get("url"):
            sid = await E.fetch_into(bag, ev, budget, p["url"], competitor_id=p.get("competitor_id"), fact_key=p.get("fact_key"))
            if not sid:
                raise ApiError(422, "FETCH_FAILED", "원문을 열지 못했어요")
        elif p.get("file_id"):
            doc_f = await platform.parsed_document(p["file_id"])
            text = doc_f.get("text") or "\n".join(x.get("text") or "" for x in doc_f.get("pages") or [])
            cls = p.get("classification") or "internal"
            sid = E.add_source(bag, {"kind": "file", "subtype": "", "title": doc_f.get("title") or p["file_id"], "publisher": "사내 자료",
                                     "file_id": p["file_id"], "classification": cls, "authority": 2, "mode": "file",
                                     "competitor_id": p.get("competitor_id"), "fact_key": p.get("fact_key")}, text)
            E.evidence(ev, source_id=sid, kind="file", title=doc_f.get("title") or "", text=text)
        claim = (bag["claims"] or {}).get(p.get("claim_id") or "")
        if claim and ev and sid:
            text = "\n".join(e["text"] for e in ev)
            quote = _best_quote(claim["text"], text)
            if quote:
                src = bag["sources"][sid]
                res = verify.check_citation(claim["text"], quote, src, text)
                if res["status"] != "dropped":
                    bag["citations"].append({"claim_id": claim["id"], "source_id": sid, "quote": quote, "page": None, "check": res["check"],
                                             "status": res["status"], "reason_code": res["reason_code"], "reason_text": res["reason_text"],
                                             "highlight": res["highlight"], "verified_at": now_iso(), "source_kind": src.get("kind")})
                    cits = [c for c in bag["citations"] if c.get("claim_id") == claim["id"]]
                    claim["status"] = verify.claim_status(cits)
                    claim["label"] = verify.claim_label(claim["status"], sum(1 for c in cits if c["status"] != "matched"))

        def upd(x: dict[str, Any]) -> None:
            x["sources"] = bag["sources"]
            x["claims"] = bag["claims"]
            x["citations"] = bag["citations"]
            x["footer"] = E.footer(bag)

        await R.call(R.update_version, aid, n, upd)
        return {"result": {"analysis_id": aid, "source_id": sid}}

    return await run_linear(ctx, [("add", add)], {"add": "출처 추가"})


def _best_quote(claim_text: str, text: str) -> str | None:
    sents = [s.strip() for s in re.split(r"(?<=[.!?。])\s+|\n+", text or "") if len(s.strip()) >= 8]
    nums = verify.parse_numbers(claim_text)
    words = {w for w in re.split(r"[\s·,]+", claim_text) if len(w) >= 2}
    best, score = None, 0.0
    for s in sents:
        sc = sum(1 for w in words if w in s)
        if nums:
            sn = verify.parse_numbers(s)
            sc += 3 * sum(1 for n in nums if any(verify.same_value(n, x) for x in sn))
        if sc > score:
            best, score = s, sc
    return best[:300] if best and score > 0 else None
