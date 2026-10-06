"""그 밖의 잡(§7.10 · §7.11 · §7.12) — fixscan · layout · source_add · competitor_add · onepager · export · recheck · import_ca · facts_research.

모두 짧은 직선 그래프(run_graph)로 돈다 — 노드마다 step 이벤트 · 취소 확인 · 체크포인트.
"""
from __future__ import annotations

import asyncio
import copy
import logging
import re
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.ids import now_iso
from winmate_common.jobs import JobCanceled, JobContext, current_job, jobs

from .. import aix, anonymize, bundle as B, claims as C, config, fixes, kbx, layout, prompts, rules, service, verify, versions, views
from .. import store as R
from ..store import nid
from .common import (
    Budget, add_source, h, init_web, known_names, pub_from_text, sensitive_texts, strip_urls, subtype_for, web_gather,
)

log = logging.getLogger("winmate.mi.misc")


class S(TypedDict, total=False):
    analysis_id: str
    p: dict[str, Any]
    data: dict[str, Any]
    result: dict[str, Any]


Node = Callable[[S], Awaitable[dict[str, Any]]]


def linear(steps: list[tuple[str, Node]]) -> StateGraph:
    g = StateGraph(S)
    prev = START
    for name, fn in steps:
        g.add_node(name, fn)
        g.add_edge(prev, name)
        prev = name
    g.add_edge(prev, END)
    return g


async def run_linear(ctx: JobContext, steps: list[tuple[str, Node]], labels: dict[str, str]) -> dict[str, Any]:
    final = await run_graph(ctx, linear(steps), {"analysis_id": ctx.payload["analysis_id"], "p": dict(ctx.payload), "data": {}, "result": {}},
                            step_labels=labels)
    return (final or {}).get("result") or {}


async def _doc(aid: str) -> dict[str, Any]:
    doc = await R.call(R.get_analysis, aid)
    if doc is None:
        raise ApiError(404, "NOT_FOUND", "분석 작업을 찾을 수 없어요", {"id": aid})
    return doc


async def _cur(doc: dict[str, Any]) -> dict[str, Any]:
    v = await R.call(R.get_version, doc["id"], int(doc.get("result_version") or 0))
    if v is None:
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요", {"id": doc["id"]})
    return v


def _sentences(text: str) -> list[str]:
    out = []
    for part in re.split(r"(?<=[.!?。])\s+|\n+", text or ""):
        p = part.strip()
        if 6 <= len(p) <= 400:
            out.append(p)
    return out


def best_quote(claim_text: str, text: str) -> str:
    """주장에 맞는 원문 문장(결정적) — 주장 수치가 든 문장 → 낱말이 가장 많이 겹치는 문장."""
    nums = [n for n in verify.parse_numbers(claim_text) if n.kind != "year"]
    sents = _sentences(text)
    for s in sents:
        if nums and any(verify.same_value(n, q) for n in nums for q in verify.parse_numbers(s)):
            return s
    toks = set(re.findall(r"[가-힣A-Za-z0-9]{2,}", verify.N(claim_text)))
    best, score = "", 0
    for s in sents:
        sc = len(toks & set(re.findall(r"[가-힣A-Za-z0-9]{2,}", verify.N(s))))
        if sc > score:
            best, score = s, sc
    return best if score >= 2 else ""


# ── mi.fixscan(§7.10) ────────────────────────────────────
async def _fix_read(state: S) -> dict[str, Any]:
    from winmate_common.platform import file_meta, parsed_document

    p = state["p"]
    fid = p["file_id"]
    try:
        meta = await file_meta(fid)
    except Exception:  # noqa: BLE001
        meta = {}
    parsed = await parsed_document(fid)
    pages = [{"no": int(pg.get("no") or i + 1), "text": pg.get("text") or ""} for i, pg in enumerate(parsed.get("pages") or [])]
    if not pages and parsed.get("text"):
        pages = [{"no": 1, "text": parsed["text"]}]
    scanned = [int(w.split(":", 1)[1]) for w in parsed.get("warnings") or [] if str(w).startswith("scanned_page:") and w.split(":", 1)[1].isdigit()]
    i2t = []
    for no in scanned[:20]:
        t = await aix.i2t_page("mi.i2t_page", fid, no)
        for pg in pages:
            if pg["no"] == no and t:
                pg["text"] = t
                i2t.append(no)
    for pg in pages:
        pg["text"] = pg["text"][:6000]
    return {"data": {"pages": pages[:60], "name": meta.get("name") or parsed.get("title") or "올린 자료", "i2t": i2t,
                     "confidential": bool(meta.get("confidential"))}}


async def _fix_match(state: S) -> dict[str, Any]:
    p = state["p"]
    doc = await _doc(state["analysis_id"])
    v = await _cur(doc)
    jid = current_job().job.id if current_job() else None
    items = [f for f in (v.get("fix_items") or {}).values() if f.get("status") == "wait" and (f.get("job_id") == jid or f["id"] in (p.get("fix_ids") or []))]
    pages = state["data"].get("pages") or []
    if not items or not pages:
        return {"data": {**state["data"], "matches": []}}
    words: set[str] = set()
    for it in items:
        words |= set(re.findall(r"[가-힣A-Za-z]{2,}", it.get("title") or ""))
        if it.get("unit"):
            words.add(str(it["unit"]))
    scored = sorted(pages, key=lambda pg: (-sum(1 for w in words if w in pg["text"]), pg["no"]))
    cand = sorted(scored[:6], key=lambda pg: pg["no"])
    try:
        res = await aix.llm("mi.fix_match", prompts.fix_match(items, cand), prompts.FixMatches, confidential=True)
        matches = [m.model_dump() for m in res.matches]
    except (aix.LLMFailed, ApiError) as exc:
        log.info("확정 스캔 LLM 실패: %s", exc)
        matches = []
    return {"data": {**state["data"], "matches": matches, "item_ids": [i["id"] for i in items]}}


def _value_in_quote(value: str, unit: str | None, quote: str) -> bool:
    raw = f"{value}{unit or ''}"
    vn = [n for n in verify.parse_numbers(raw) if n.kind != "year"]
    if not vn:
        return verify.N(value) in verify.N(quote)
    qn = verify.parse_numbers(quote)
    return any(verify.same_value(vn[0], q) or (q.value == vn[0].value) for q in qn)


async def _fix_apply(state: S) -> dict[str, Any]:
    p = state["p"]
    d = state["data"]
    doc = await _doc(state["analysis_id"])
    pages = {pg["no"]: pg["text"] for pg in d.get("pages") or []}
    matches = {m["fix_id"]: m for m in d.get("matches") or []}
    cls = p.get("classification") or ("confidential" if d.get("confidential") else "internal")
    ok_ids: list[str] = []

    def change(ver: dict[str, Any]) -> None:
        sid = None
        for fid in d.get("item_ids") or []:
            f = (ver.get("fix_items") or {}).get(fid)
            if not f or f.get("status") != "wait":
                continue
            m = matches.get(fid)
            good = False
            if m and m.get("page") in pages and m.get("quote"):
                qs, _ = verify.quote_check(m["quote"], pages[m["page"]])
                good = qs == "ok" and _value_in_quote(m.get("value") or "", m.get("unit") or f.get("unit"), m["quote"])
                if f.get("competitor") and cls == "confidential":
                    good = False   # 경쟁사 항목은 대외비 파일 값으로 채우지 않는다
            hist = f.get("history") or []
            if good:
                if sid is None:
                    src = {"kind": "file", "subtype": "확정 자료", "title": d.get("name") or "올린 자료", "publisher": doc.get("owner_name", ""), "url": None,
                           "file_id": p["file_id"], "published_at": None, "published_basis": "unknown", "retrieved_at": now_iso(), "authority": 2,
                           "classification": cls, "state": "used", "mode": "file", "areas": [f.get("tab")], "kb_key": f"file:{p['file_id']}",
                           "method": "i2t" if m.get("page") in (d.get("i2t") or []) else "text"}
                    sid = add_source(ver, src)
                    R.save_snapshot(sid, "\n".join(pages.values()), [pages[k] for k in sorted(pages)])
                val = re.sub(r"\s+", "", str(m.get("value") or "")).replace(",", "") if f.get("input_kind") != "text" else str(m.get("value") or "")
                f.update(status="ok", value=val, unit=m.get("unit") or f.get("unit"), value_source="file", source_id=sid, quote=m["quote"],
                         page=m["page"], file_id=p["file_id"], file_name=d.get("name"), reason_code="FILE",
                         sub_text=fixes.sub_text("FILE", page=m["page"]), confirmed_by=doc.get("owner_name", ""), confirmed_at=now_iso(), job_id=None,
                         applied=False)
                if f.get("claim_id") and f["claim_id"] in (ver.get("claims") or {}):
                    C.replace_citations(ver, f["claim_id"], sid, m["quote"], page=m["page"])
                    C.recompute(ver, f["claim_id"])
                ok_ids.append(fid)
            else:
                prev = hist.pop() if hist else {}
                f["history"] = hist
                f.update(status=prev.get("status", "warn"), reason_code="NOT_IN_FILE", sub_text=fixes.sub_text("NOT_IN_FILE"), job_id=None,
                         file_id=prev.get("file_id"), file_name=prev.get("file_name"))

    await versions.update_current(doc, change)
    return {"result": {"analysis_id": doc["id"], "matched": ok_ids, "not_found": [i for i in d.get("item_ids") or [] if i not in ok_ids]}}


async def _fix_restore(aid: str, job_id: str) -> None:
    doc = await R.call(R.get_analysis, aid)
    if not doc:
        return

    def change(ver: dict[str, Any]) -> None:
        for it in (ver.get("fix_items") or {}).values():
            if it.get("status") == "wait" and it.get("job_id") == job_id:
                hist = it.get("history") or []
                prev = hist.pop() if hist else {}
                it["history"] = hist
                it.update(status=prev.get("status", "warn"), sub_text=prev.get("sub_text") or it.get("sub_text"),
                          reason_code=prev.get("reason_code") or it.get("reason_code"), job_id=None, file_id=prev.get("file_id"), file_name=prev.get("file_name"))

    try:
        await versions.update_current(doc, change)
    except Exception:  # noqa: BLE001
        log.exception("확정 스캔 되돌리기 실패")


async def handle_fixscan(ctx: JobContext) -> dict[str, Any]:
    try:
        return await run_linear(ctx, [("read_file", _fix_read), ("match", _fix_match), ("apply", _fix_apply)],
                                {"read_file": "올린 자료 읽기", "match": "값 찾기", "apply": "확정"})
    except JobCanceled:
        await _fix_restore(ctx.payload["analysis_id"], ctx.job.id)
        raise
    except Exception:
        await _fix_restore(ctx.payload["analysis_id"], ctx.job.id)
        raise


# ── mi.source_add ────────────────────────────────────────
async def _src_collect(state: S) -> dict[str, Any]:
    from winmate_common.platform import file_meta, parsed_document

    p = state["p"]
    if p.get("url"):
        page = await aix.fetch(p["url"])
        if not page:
            return {"data": {"ok": False, "reason": "FETCH_FAILED"}}
        text = page.get("text") or "\n".join(page.get("pages") or [])
        return {"data": {"ok": True, "kind": "web", "text": text, "pages": page.get("pages") or [], "title": page.get("title") or p["url"],
                         "final_url": page.get("final_url") or p["url"], "published_at": page.get("published_at") or pub_from_text(text[:3000]),
                         "content_hash": page.get("content_hash") or h(text), "basis": "meta" if page.get("published_at") else "text"}}
    try:
        meta = await file_meta(p["file_id"])
    except Exception:  # noqa: BLE001
        meta = {}
    try:
        parsed = await parsed_document(p["file_id"])
    except Exception:  # noqa: BLE001
        return {"data": {"ok": False, "reason": "FETCH_FAILED"}}
    pages = [pg.get("text") or "" for pg in parsed.get("pages") or []]
    return {"data": {"ok": True, "kind": "file", "text": "\n".join(pages) or parsed.get("text") or "", "pages": pages,
                     "title": meta.get("name") or parsed.get("title") or "올린 자료", "confidential": bool(meta.get("confidential"))}}


async def _src_verify(state: S) -> dict[str, Any]:
    p = state["p"]
    d = state["data"]
    doc = await _doc(state["analysis_id"])
    sid = p["source_id"]
    cid = p.get("claim_id")

    def change(ver: dict[str, Any]) -> None:
        src = (ver.get("sources") or {}).get(sid)
        if src is None:
            return
        if d.get("ok"):
            if d["kind"] == "web":
                sub, auth = subtype_for(d["final_url"], d["title"])
                src.update(kind="web", subtype=sub, authority=auth, title=d["title"], url=d["final_url"], final_url=d["final_url"],
                           published_at=(d.get("published_at") or "")[:10] or None, published_basis=d.get("basis") or "unknown",
                           content_hash=d.get("content_hash"), state="used")
                if src.get("published_at") and rules.is_stale(src["published_at"]):
                    src["stale_kept"] = True
            else:
                src.update(kind="file", title=d["title"], state="used", subtype="사용자 자료",
                           classification=p.get("classification") or ("confidential" if d.get("confidential") else src.get("classification") or "internal"))
            R.save_snapshot(sid, d.get("text") or "", d.get("pages") or None)
        else:
            src.update(state="used", snippet=None)
        claim = (ver.get("claims") or {}).get(cid) if cid else None
        if claim is None:
            return
        pages = d.get("pages") or []
        quote, page_no, page_text = "", None, None
        if d.get("ok"):
            if pages:
                for i, ptxt in enumerate(pages, start=1):
                    q = best_quote(claim.get("text", ""), ptxt)
                    if q:
                        quote, page_no, page_text = q, i, ptxt
                        break
            else:
                quote = best_quote(claim.get("text", ""), d.get("text") or "")
        res = verify.check_citation(claim_text=claim.get("text", ""), quote=quote or claim.get("text", ""), source=src,
                                    source_text=(d.get("text") if d.get("ok") else None), page_text=page_text, known_names=known_names(doc))
        if not d.get("ok"):
            res.reason_code, res.reason_text, res.status = "FETCH_FAILED", verify.reason_text("FETCH_FAILED"), "unverifiable"
        for c in ver.get("citations") or []:
            if c.get("claim_id") == cid and c.get("source_id") == sid:
                c.update(quote=verify.strip_ellipsis(quote), highlight=res.highlight, quote_span=list(res.quote_span) if res.quote_span else None,
                         page=page_no, check=res.check, status=res.status, reason_code=res.reason_code, reason_text=res.reason_text,
                         verified_at=now_iso(), value=verify.num_to_dict(res.value), pending=False)
        C.recompute(ver, cid)

    v = await versions.update_current(doc, change)
    st = ((v.get("claims") or {}).get(cid) or {}).get("status") if cid else None
    return {"result": {"analysis_id": doc["id"], "source_id": sid, "claim_status": st, "fetched": bool(d.get("ok"))}}


async def handle_source_add(ctx: JobContext) -> dict[str, Any]:
    return await run_linear(ctx, [("collect", _src_collect), ("verify", _src_verify)], {"collect": "자료 읽기", "verify": "원문 대조"})


# ── mi.competitor_add ────────────────────────────────────
async def handle_competitor_add(ctx: JobContext) -> dict[str, Any]:
    from .competitors import profile

    async def look(state: S) -> dict[str, Any]:
        doc = await _doc(state["analysis_id"])
        cmp = next((c for c in doc.get("competitors") or [] if c["id"] == state["p"]["competitor_id"]), None)
        if cmp is None:
            return {"result": {}}
        b = Budget(websearch=2, fetch=0, llm=2)
        await init_web(b)
        info = await profile(doc, cmp, b)

        def upd(d: dict[str, Any]) -> None:
            for c in d.get("competitors") or []:
                if c["id"] == cmp["id"]:
                    if info.get("kind_label"):
                        c["kind_label"] = info["kind_label"]
                    if info.get("desc"):
                        c["desc"] = info["desc"]
                    c["aliases"] = list(dict.fromkeys((c.get("aliases") or []) + (info.get("aliases") or [])))[:6]
                    c["lookup"] = "done"

        saved = await R.call(R.update_analysis, doc["id"], upd)
        await service.register(saved)
        return {"result": {"analysis_id": doc["id"], "competitor_id": cmp["id"]}}

    return await run_linear(ctx, [("lookup", look)], {"lookup": "경쟁사 확인"})


# ── mi.onepager ──────────────────────────────────────────
async def make_onepager(doc: dict[str, Any], v: dict[str, Any]) -> dict[str, Any]:
    lines = []
    for a in rules.AREAS:
        if (v.get("area_status") or {}).get(a) in ("done", "reused"):
            for cid in views.claim_order(v.get("document") or {}, a)[:10]:
                c = (v.get("claims") or {}).get(cid) or {}
                lines.append(f"[{a}] {c.get('text', '')}")
    quotes = [{"quote": c.get("text", "")} for c in (v.get("claims") or {}).values()]
    res = await aix.llm("mi.onepager", prompts.onepager("\n".join(lines)[:6000]), prompts.Onepager, confidential=True)
    quads = {a: verify.mask_unsupported(getattr(res, a), quotes)[0] for a in rules.AREAS if (v.get("area_status") or {}).get(a) in ("done", "reused")}
    return {"quadrants": quads, "conclusion": verify.mask_unsupported(res.conclusion, quotes)[0]}


async def handle_onepager(ctx: JobContext) -> dict[str, Any]:
    async def write(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        doc = await _doc(aid)
        v = await _cur(doc)
        try:
            op = await make_onepager(doc, v)
        except (aix.LLMFailed, ApiError) as exc:
            await R.call(R.put_doc, R.ONE, aid, {"analysis_id": aid, "status": "failed", "error": str(exc)[:200], "version": int(v.get("n") or 0)})
            raise
        await R.call(R.put_doc, R.ONE, aid, {"analysis_id": aid, "status": "done", "job_id": ctx.job.id, "version": int(v.get("n") or 0), **op,
                                             "created_at": now_iso()})
        return {"result": {"analysis_id": aid, "version": int(v.get("n") or 0)}}

    return await run_linear(ctx, [("write", write)], {"write": "한 장 요약"})


# ── mi.export ────────────────────────────────────────────
FORMAT = {"pdf_report": ("pdf", "리포트"), "pptx_onepager": ("pptx", "한 장 요약"), "xlsx_table": ("xlsx", "비교표")}


async def handle_export(ctx: JobContext) -> dict[str, Any]:
    from winmate_common.client import ServiceClient

    async def render(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        p = state["p"]
        doc = await _doc(aid)
        v = await _cur(doc)
        fmt, label = FORMAT[p["format"]]
        op = None
        if p["format"] == "pptx_onepager":
            op = await R.call(R.get_doc, R.ONE, aid)
            if not op or op.get("status") != "done" or int(op.get("version") or 0) != int(v.get("n") or 0):
                try:
                    op = await make_onepager(doc, v)
                except (aix.LLMFailed, ApiError):
                    op = {}
        body = B.export_document(doc, v, p["format"], p.get("audience") or "customer", op)
        title = anonymize.scrub(doc.get("title") or "Market Intelligence", doc.get("competitors") or [], {}) \
            if (p.get("audience") != "internal" and doc.get("anonymize", True)) else (doc.get("title") or "Market Intelligence")
        ex = ServiceClient("export", timeout=180)
        res = await ex.post("/v1/exports", json={"format": fmt, "filename": f"{title} {label}"[:80], "document": body,
                                                  "confidential": p.get("audience") == "internal", "project_id": doc.get("project_id"),
                                                  "source_ref": f"mi:{aid}"})
        file = res.get("file")
        if not file and res.get("export_id"):
            for _ in range(240):
                await asyncio.sleep(0.5)
                if current_job():
                    await current_job().check_cancel()
                rec = await ex.get(f"/v1/exports/{res['export_id']}")
                if rec.get("status") == "done":
                    file = rec.get("file")
                    break
                if rec.get("status") == "failed":
                    raise ApiError(502, "EXPORT_FAILED", "파일을 만들지 못했어요", {"export_id": res["export_id"]})
        if not file:
            raise ApiError(504, "TIMEOUT", "파일 만들기가 오래 걸려요 · 잠시 후 다시 시도해 주세요")
        await R.call(R.put_doc, R.HOF, nid("hof"), {"analysis_id": aid, "version": int(v.get("n") or 0), "target": "file", "target_title": label,
                                                     "status": "delivered", "created_at": now_iso(), "format": p["format"], "audience": p.get("audience"),
                                                     "file_id": file.get("id")})
        return {"result": {"analysis_id": aid, "file_id": file.get("id"), "url": file.get("url"), "name": file.get("name"), "format": p["format"]}}

    return await run_linear(ctx, [("render", render)], {"render": "파일 만들기"})


# ── mi.recheck(§7.11) ────────────────────────────────────
async def _rc_news(state: S) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    v = await _cur(doc)
    b = Budget(websearch=8, fetch=10, llm=8)
    await init_web(b)
    since = (doc.get("analyzed_at") or v.get("created_at") or "")[:10]
    changes: list[dict[str, Any]] = []
    for c in anonymize.live(doc.get("competitors") or []):
        if b.web_unavailable or not b.take("websearch"):
            break
        q = aix.query_guard(f"{c['real_name']} 신제품 출시", sensitive_texts(doc))
        if not q:
            continue
        try:
            res = await aix.websearch("mi.web_recheck", q)
        except ApiError as exc:
            if exc.status in (429, 502, 503, 504):
                b.web_unavailable = True
                break
            raise
        summary = strip_urls(res.get("summary") or "")
        if not summary:
            continue
        try:
            news = await aix.llm("mi.recheck_news", prompts.recheck_news(c["real_name"], since, summary), prompts.News, confidential=False)
        except (aix.LLMFailed, ApiError):
            continue
        hay = verify.N(summary)
        for it in news.items:
            if not it.date or not since or it.date[:10] <= since or verify.N(it.product) not in hay:
                continue
            verified = "matched" if b.mode == "sources" and res.get("sources") else "needs_check"
            changes.append({"id": nid("chgu"), "kind": "competitor_new_product", "title": f"{anonymize.workspace_label(c)} 신제품 발표 · {it.product[:30]}",
                            "summary": strip_urls(it.summary)[:120], "date": it.date[:10], "competitor_id": c["id"], "affected_areas": ["competitor"],
                            "verified": verified, "at": now_iso()})
    return {"data": {"changes": changes, "budget": {"web_unavailable": b.web_unavailable, "mode": b.mode}}}


async def _rc_reports(state: S) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    v = await _cur(doc)
    d = dict(state["data"])
    changes = list(d.get("changes") or [])
    b = Budget(websearch=4, fetch=4, llm=0)
    b.web_unavailable = bool((d.get("budget") or {}).get("web_unavailable"))
    b.mode = (d.get("budget") or {}).get("mode") or "summary_only"
    for sid, s in (v.get("sources") or {}).items():
        if s.get("subtype") not in ("시장 보고서", "정부·통계") or s.get("state") == "excluded" or b.web_unavailable:
            continue
        pub = rules.parse_iso(s.get("published_at"))
        if not pub or not b.take("websearch"):
            continue
        q = aix.query_guard(f"{s.get('publisher') or ''} {re.sub(r'20[0-9]{2}', '', s.get('title') or '')} 최신판".strip(), sensitive_texts(doc))
        if not q:
            continue
        try:
            res = await aix.websearch("mi.web_report", q)
        except ApiError:
            break
        summary = strip_urls(res.get("summary") or "")
        newer = pub_from_text(summary)
        if newer and newer[:7] > (s.get("published_at") or "")[:7]:
            areas = [a for a in s.get("areas") or [] if a in rules.AREAS] or ["market"]
            changes.append({"id": nid("chgu"), "kind": "report_revised", "title": f"시장 리포트 개정 · {(s.get('title') or '')[:30]}",
                            "summary": f"{newer[:7]} 판 확인", "source_id": sid, "affected_areas": areas,
                            "verified": "matched" if b.mode == "sources" else "needs_check", "at": now_iso()})
    d["changes"] = changes
    return {"data": d}


async def _rc_refetch(state: S) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    v = await _cur(doc)
    d = dict(state["data"])
    changes = list(d.get("changes") or [])
    n = 0
    for sid, s in (v.get("sources") or {}).items():
        if s.get("kind") != "web" or not s.get("url") or s.get("state") == "excluded" or n >= 10:
            continue
        n += 1
        page = await aix.fetch(s["url"])
        if not page:
            continue
        text = page.get("text") or "\n".join(page.get("pages") or [])
        newhash = page.get("content_hash") or h(text)
        if newhash == s.get("content_hash"):
            continue
        quotes = [c.get("quote") for c in v.get("citations") or [] if c.get("source_id") == sid and not c.get("dropped") and c.get("quote")]
        if any(verify.quote_check(q, text)[0] == "fail" for q in quotes):
            areas = [a for a in s.get("areas") or [] if a in rules.AREAS]
            changes.append({"id": nid("chgu"), "kind": "source_changed", "title": f"출처 내용 변경 · {(s.get('title') or '')[:30]}", "summary": "인용 구절이 원문에서 사라졌어요",
                            "source_id": sid, "affected_areas": areas, "verified": "matched", "at": now_iso()})
    d["changes"] = changes
    return {"data": d}


async def _rc_kb(state: S) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    v = await _cur(doc)
    d = dict(state["data"])
    changes = list(d.get("changes") or [])
    kbx.clear_cache()
    now_ver = await kbx.kb_version()
    if now_ver and v.get("kb_version") and now_ver != v.get("kb_version"):
        areas = sorted({a for s in (v.get("sources") or {}).values() if s.get("kind") in ("kb_case", "kb_official") for a in s.get("areas") or []
                        if a in rules.AREAS}, key=rules.AREAS.index)
        changes.append({"id": nid("chgu"), "kind": "kb_updated", "title": f"지식 DB 갱신 · {now_ver}", "summary": "사내 사례 · 스펙 DB 가 새로 만들어졌어요",
                        "affected_areas": areas or ["competitor"], "verified": "matched", "at": now_iso()})
    d["changes"] = changes
    return {"data": d}


async def _rc_decide(state: S) -> dict[str, Any]:
    from .analyze import schedule_recheck

    aid = state["analysis_id"]
    doc = await _doc(aid)
    changes = list(state["data"].get("changes") or [])
    nxt = None
    if changes:
        def upd(d: dict[str, Any]) -> None:
            if d.get("status") in ("done", "upd"):
                d["status"] = "upd"
            d["upd_changes"] = changes
            d["rechecked_at"] = now_iso()

        saved = await R.call(R.update_analysis, aid, upd)
        await service.register(saved)
        try:
            await jobs().push_notification(doc["owner_id"], {"type": "mi_update", "service": "mi", "ref": aid,
                                                             "title": anonymize.scrub(f"{doc.get('title') or 'Market Intelligence'} · 바뀐 자료 {len(changes)}건",
                                                                                      doc.get("competitors") or [], {}),
                                                             "route": f"/mi/{aid}/result"})
        except Exception:  # noqa: BLE001
            pass
    else:
        nxt = await schedule_recheck(doc, time.time())

        def upd2(d: dict[str, Any]) -> None:
            d.setdefault("memos", []).append({"text": "30일 재확인 · 바뀐 자료 없음", "at": now_iso(), "where": "recheck"})
            d["next_recheck_at"] = nxt
            d["rechecked_at"] = now_iso()

        await R.call(R.update_analysis, aid, upd2)
    await R.call(R.put_doc, R.CHK, nid("chk"), {"analysis_id": aid, "created_at": now_iso(), "changes": changes, "next_recheck_at": nxt})
    return {"result": {"analysis_id": aid, "changes": len(changes), "status": "upd" if changes else "done"}}


async def handle_recheck(ctx: JobContext) -> dict[str, Any]:
    return await run_linear(ctx, [("competitor_news", _rc_news), ("report_revisions", _rc_reports), ("refetch", _rc_refetch), ("kb_version", _rc_kb),
                                  ("decide", _rc_decide)],
                            {"competitor_news": "경쟁사 신제품", "report_revisions": "보고서 개정", "refetch": "출처 다시 읽기", "kb_version": "지식 DB",
                             "decide": "판정"})


# ── mi.facts_research(제안서 PR7Q `다른 출처 찾기`) ─────
async def handle_facts_research(ctx: JobContext) -> dict[str, Any]:
    async def research(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        doc = await _doc(aid)
        b = Budget(websearch=6, fetch=6, llm=0)
        await init_web(b)
        cust = (doc.get("customer_name") or "").strip()
        items = []
        for q in (state["p"].get("questions") or [])[:6]:
            v: dict[str, Any] = {"sources": {}}
            ev: list[dict[str, Any]] = []
            query = f"{cust} {q.get('label') or ''}".strip()
            await web_gather(v, ev, b, None, task="mi.web_facts", query=query, area="customer", sensitive=sensitive_texts(doc))
            cands = []
            for e in ev:
                nums = [n for n in verify.parse_numbers(e["text"]) if n.kind != "year" and (not q.get("unit") or q["unit"] in n.raw)]
                for n in nums[:2]:
                    src = v["sources"].get(e["source_id"]) or {}
                    cands.append({"value": re.sub(r"[^\d\.]", "", n.raw.split(" ")[0]) or n.raw, "unit": q.get("unit"),
                                  "status": "unverifiable" if src.get("kind") == "websearch_summary" else "needs_check",
                                  "source": {"kind": src.get("kind"), "label": views.footnote(src), **({"url": src["url"]} if src.get("url") else {})}})
            items.append({"key": q.get("key"), "candidates": cands[:3]})
        return {"result": {"analysis_id": aid, "items": anonymize.scrub(items, doc.get("competitors") or [], {})}}

    return await run_linear(ctx, [("research", research)], {"research": "수치 다시 찾기"})


# ── mi.layout(§7.12 · MI3L 선택지 A) ─────────────────────
async def handle_layout(ctx: JobContext) -> dict[str, Any]:
    from .analyze import Refs, comp_cell, ingest_area, _evidence_from_version
    from .competitors import add_competitor, find_candidates

    async def enrich(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        p = state["p"]
        doc = await _doc(aid)
        v = copy.deepcopy(await _cur(doc))
        sheet = next((s for s in v.get("slides") or [] if s["id"] == p["sheet_id"]), None)
        if sheet is None:
            raise ApiError(404, "NOT_FOUND", "시트를 찾을 수 없어요", {"sheet_id": p["sheet_id"]})
        req = p.get("template") or sheet["template_code"]
        b = Budget(websearch=10, fetch=12, llm=8)
        await init_web(b)
        sens = sensitive_texts(doc)
        m = layout.metrics(doc, v)
        added_names: list[str] = []
        if req.startswith("CP-"):
            pm = layout.predicted_metrics(req, m) or {}
            want = max(0, int(pm.get("suppliers", m["suppliers"])) - int(m["suppliers"]))
            if want:
                cands, _ = await find_candidates(doc, b, want=want, exclude=doc.get("competitors") or [], task="mi.web_layout")
                if cands:
                    def add(d: dict[str, Any]) -> None:
                        for c in cands:
                            add_competitor(d, c.name, origin="auto", aliases=c.aliases, kind_label=c.kind_label, desc=c.desc, confidence=c.confidence)

                    doc = await R.call(R.update_analysis, aid, add)
                    new = [c for c in anonymize.live(doc.get("competitors") or []) if any(verify.N(c["real_name"]) == verify.N(x.name) for x in cands)]
                    added_names = [c["id"] for c in new]
                    ev: list[dict[str, Any]] = []
                    seg = config.segment(((doc.get("segment") or {}).get("mix") or {}).get("a") or (doc.get("segment") or {}).get("code") or "GEN")
                    for c in new:
                        await web_gather(v, ev, b, None, task="mi.web_competitor", query=f"{c['real_name']} {seg['product']} 제품 라인업 CMS",
                                         area="competitor", sensitive=sens, competitor_id=c["id"])
                    table = (((v.get("document") or {}).get("competitor") or {}).get("table") or {})
                    crit_ids = table.get("criteria") or []
                    names = {**{c["id"]: c["name"] for c in doc.get("criteria") or []}, **(table.get("criteria_names") or {})}
                    crits = [{"id": c, "name": names.get(c, "")} for c in crit_ids]
                    cells_new: dict[tuple[str, str], Any] = {}
                    if crits and b.take("llm"):
                        try:
                            res = await aix.llm("mi.compare_cells", prompts.compare_cells(crits, new, ev, []), prompts.Cells, confidential=True)
                            refs = Refs(crits, new)
                            for cell in res.cells:
                                cc, pc = refs.crit(cell.criterion_id), refs.comp(cell.competitor_id)
                                if cc in crit_ids and pc in added_names:
                                    cell.criterion_id, cell.competitor_id = cc, pc
                                    cells_new[(cc, pc)] = cell
                        except (aix.LLMFailed, ApiError) as exc:
                            log.info("레이아웃 보강 칸 실패: %s", exc)
                    known = known_names(doc)
                    cols = [c for c in table.get("columns") or [] if c != "samsung"] + added_names + ["samsung"]
                    table["columns"] = cols
                    for crt in crit_ids:
                        row = table.setdefault("cells", {}).setdefault(crt, {})
                        for cid_ in added_names:
                            cell = cells_new.get((crt, cid_))
                            row[cid_] = comp_cell(v, ev, cell, known) if cell else {"text": "[확인 필요]", "claim_ids": [], "placeholder": True}
                            row[cid_]["verdict"] = "unknown"
        elif req.startswith(("MS-", "TR-", "MI-")) and "market" in ((v.get("area_status") or {})):
            seg = config.segment(((doc.get("segment") or {}).get("mix") or {}).get("a") or (doc.get("segment") or {}).get("code") or "GEN")
            ev = _evidence_from_version(v, "market")
            what = "트렌드 전망" if req.startswith("TR-") else "시장 규모 연도별 추이"
            await web_gather(v, ev, b, None, task="mi.web_layout", query=f"{seg['market'] if seg['code'] != 'GEN' else ''} {seg['product']} {what}".strip(),
                             area="market", sensitive=sens)
            if b.take("llm"):
                try:
                    res = await aix.llm("mi.extract_claims_market", prompts.extract_claims("market", doc, ev[:24], []), prompts.MarketExtract, confidential=True)
                    ingest_area(v, doc, "market", res, ev)
                except (aix.LLMFailed, ApiError) as exc:
                    log.info("시장 보강 실패: %s", exc)
        m2 = layout.metrics(doc, v)
        f, needs = layout.fit(req, m2)
        for s in v.get("slides") or []:
            if s["id"] == p["sheet_id"]:
                seg_c = ((doc.get("segment") or {}).get("mix") or {}).get("c" if s["sheet_type"] == "US" else "a") or (doc.get("segment") or {}).get("code")
                if f >= 0:
                    s.update(template_code=req, template_name=layout.template(req)["name"], thumb_kind=layout.thumb_kind(req), fit=f, needs_report=needs,
                             industry_layout=req.startswith("MI-"), why=layout.why_for("cp" if s["sheet_type"] == "CP" else "generic", s["sheet_type"], req, m2, seg_c),
                             alternatives=layout._alts(layout.band(s["sheet_type"]), req, m2), item_label=layout.item_label(s["sheet_type"], req, m2))
                    s["pinned"] = bool(p.get("pin")) or s.get("pinned", False)
                if p.get("axes"):
                    s.setdefault("options", {})["axes"] = p["axes"]
                s.setdefault("options", {}).pop("requested", None)
        n = await versions.save_new_version(doc, v, kind="layout", summary=f"레이아웃 보강 · {req}", recompose_slides=False, status="done")

        def upd(d: dict[str, Any]) -> None:
            d["current_job_id"] = None
            d.setdefault("run", {}).update(stage="write", finished_at=now_iso())

        saved = await R.call(R.update_analysis, aid, upd)
        await service.register(saved)
        return {"result": {"analysis_id": aid, "version": n, "template": req, "fit": f, "added_competitors": len(added_names)}}

    try:
        return await run_linear(ctx, [("enrich", enrich)], {"enrich": "데이터 보강"})
    except BaseException:
        async def back() -> None:
            def upd(d: dict[str, Any]) -> None:
                if d.get("current_job_id") == ctx.job.id:
                    d["current_job_id"] = None
                    if d.get("status") == "running":
                        d["status"] = "done" if d.get("result_version") else "draft"

            try:
                await R.call(R.update_analysis, ctx.payload["analysis_id"], upd)
            except Exception:  # noqa: BLE001
                pass

        await back()
        raise


# ── mi.import_ca(§7.12) ──────────────────────────────────
def _ca_maps(doc: dict[str, Any], ca: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    """CA 묶음 → MI 경쟁사(글자 · 실명 유지) · 기준(중요도 → 가중치) 대응표 · (CA id → MI id)."""
    from .competitors import same_company

    comps = [dict(c) for c in doc.get("competitors") or []]
    cmap: dict[str, str] = {}
    used = {c.get("letter") for c in comps}
    for i, c in enumerate(ca.get("competitors") or []):
        key = c.get("id") or c.get("letter") or str(i)
        hit = next((x for x in comps if same_company(c.get("real_name") or "", x)), None)
        if hit is None:
            letter = c.get("letter") if c.get("letter") and c.get("letter") not in used else next(l for l in rules.letters(len(comps) + 27) if l not in used)
            used.add(letter)
            hit = {"id": nid("cmp"), "letter": letter, "real_name": c.get("real_name") or "", "aliases": list(c.get("aliases") or []),
                   "kind_label": c.get("kind_label") or "", "desc": c.get("why") or "", "origin": "ca_import", "confidence": c.get("confidence"),
                   "pinned": bool(c.get("pinned")), "removed": False, "evidence_source_ids": [], "order": len(comps), "lookup": "done"}
            comps.append(hit)
        else:
            hit["removed"] = False
        cmap[key] = hit["id"]
        if c.get("letter"):
            cmap.setdefault(c["letter"], hit["id"])
    crits = [dict(c) for c in doc.get("criteria") or []]
    kmap: dict[str, str] = {}
    for i, c in enumerate(ca.get("criteria") or []):
        if c.get("enabled") is False:
            continue
        key = c.get("id") or str(i)
        hit = next((x for x in crits if verify.N(x.get("name", "")) == verify.N(c.get("name", ""))), None)
        if hit is None:
            hit = {"id": nid("crt"), "name": (c.get("name") or "")[:24], "source": c.get("source") if c.get("source") in ("requirements", "industry_cases", "user") else "user",
                   "source_count": c.get("source_count"), "weight": max(1, min(5, int(c.get("importance") or 3))), "order": len(crits), "enabled": True, "pinned": True}
            crits.append(hit)
        kmap[key] = hit["id"]
        kmap.setdefault(c.get("name") or "", hit["id"])
    return {"competitors": comps, "criteria": crits}, cmap, kmap


def _ca_version(doc: dict[str, Any], ca: dict[str, Any], cmap: dict[str, str], kmap: dict[str, str], crits: list[dict[str, Any]]) -> dict[str, Any]:
    """CA 결과 → 경쟁 영역 문서 · 주장 · 인용 · 출처(검증 상태 유지, kind=ca_import)."""
    v: dict[str, Any] = {"document": {}, "claims": {}, "citations": [], "sources": {}}
    sid_map: dict[str, str] = {}
    for s in ca.get("sources") or []:
        sid = nid("src")
        sid_map[s.get("id") or sid] = sid
        v["sources"][sid] = {**{k: s.get(k) for k in ("title", "publisher", "url", "published_at", "published_basis", "retrieved_at", "authority",
                                                       "classification", "subtype", "query", "summary", "file_id")},
                             "id": sid, "kind": "ca_import", "orig_kind": s.get("kind") or "web", "state": s.get("state") or "used", "mode": "ca_import",
                             "areas": ["competitor"], "retrieved_at": s.get("retrieved_at") or now_iso()}
    cid_map: dict[str, str] = {}
    for cl in ca.get("claims") or []:
        cid = nid("clm")
        cid_map[cl.get("id") or cid] = cid
        v["claims"][cid] = {"id": cid, "area": "competitor", "block_path": "ca_import", "text": cl.get("text", ""), "numbers": [verify.num_to_dict(n) for n in verify.parse_numbers(cl.get("text", ""))],
                            "status": cl.get("status") or "needs_check", "label": verify.claim_label(cl.get("status") or "needs_check", 1),
                            "metric_key": cl.get("metric_key") or cl.get("fact_key"), "created_by": "ca_import", "inferred": False, "unsupported": []}
        for c in cl.get("citations") or []:
            sid = sid_map.get(c.get("source_id") or "")
            if sid:
                v["citations"].append({"claim_id": cid, "source_id": sid, "quote": c.get("quote") or "", "highlight": c.get("highlight"), "page": c.get("page"),
                                       "check": c.get("check") or {}, "status": c.get("status") or "needs_check", "reason_code": c.get("reason_code"),
                                       "reason_text": c.get("reason_text") or "", "verified_at": c.get("verified_at") or now_iso(), "value": c.get("value")})
    for c in ca.get("citations") or []:
        cid = cid_map.get(c.get("claim_id") or "")
        sid = sid_map.get(c.get("source_id") or "")
        if cid and sid:
            v["citations"].append({"claim_id": cid, "source_id": sid, "quote": c.get("quote") or "", "highlight": c.get("highlight"), "page": c.get("page"),
                                   "check": c.get("check") or {}, "status": c.get("status") or "needs_check", "reason_code": c.get("reason_code"),
                                   "reason_text": c.get("reason_text") or "", "verified_at": c.get("verified_at") or now_iso(), "value": c.get("value")})
    for cid in list(v["claims"].keys()):
        C.recompute(v, cid)
    crit_order = [c["id"] for c in sorted(crits, key=lambda c: (-int(c.get("weight", 3)), c.get("order", 0))) if c["id"] in set(kmap.values())]
    cols = list(dict.fromkeys(cmap.values()))
    cells: dict[str, dict[str, Any]] = {crt: {} for crt in crit_order}
    for vd in ca.get("verdicts") or []:
        crt = kmap.get(vd.get("criterion_id") or "")
        col = cmap.get(vd.get("competitor_id") or "")
        if not crt or not col or crt not in cells:
            continue
        ids = [cid_map[x] for x in vd.get("claim_ids") or [] if x in cid_map]
        text = vd.get("rationale") or (v["claims"][ids[0]]["text"] if ids else "[확인 필요]")
        cells[crt][col] = {"text": text, "claim_ids": ids, "placeholder": not ids or "[확인 필요]" in text, "verdict": vd.get("verdict") or "unknown"}
    for k, sc in (ca.get("samsung_cells") or {}).items():
        crt = kmap.get(k)
        if crt in cells:
            ids = [cid_map[x] for x in sc.get("claim_ids") or [] if x in cid_map]
            cells[crt]["samsung"] = {"text": sc.get("text") or "[확인 필요]", "claim_ids": ids, "placeholder": not ids}
    for crt in cells:
        for col in cols + ["samsung"]:
            cells[crt].setdefault(col, {"text": "[확인 필요]", "claim_ids": [], "placeholder": True})
    for cid, cl in v["claims"].items():
        for crt, row in cells.items():
            for col, cell in row.items():
                if cid in cell.get("claim_ids") or []:
                    cl["cell"] = {"crt": crt, "col": col}
    strengths = []
    for i, s in enumerate((ca.get("strengths") or [])[:3]):
        ids = [cid_map[x] for x in s.get("claim_ids") or [] if x in cid_map]
        strengths.append({"id": nid("str"), "title": (s.get("title") or "")[:12], "note": s.get("note") or "", "criterion_ids": [kmap[x] for x in s.get("criterion_ids") or [] if x in kmap],
                          "claim_ids": ids})
    names = {c["id"]: c["name"] for c in crits}
    v["document"]["competitor"] = {"table": {"criteria": crit_order, "columns": cols + ["samsung"], "cells": cells,
                                             "criteria_names": {k: names.get(k, "") for k in crit_order}}, "strengths": strengths, "samsung_products": []}
    return v


async def handle_import_ca(ctx: JobContext) -> dict[str, Any]:
    async def merge(state: S) -> dict[str, Any]:
        aid = state["analysis_id"]
        p = state["p"]
        ca = p.get("ca_bundle") or {}
        doc = await _doc(aid)
        upd_doc, cmap, kmap = _ca_maps(doc, ca)

        def save_maps(d: dict[str, Any]) -> None:
            d["competitors"] = upd_doc["competitors"]
            d["criteria"] = upd_doc["criteria"]
            if "competitor" not in ((d.get("scope") or {}).get("areas") or []):
                d.setdefault("scope", {}).setdefault("areas", []).append("competitor")
            if d.get("decisions"):
                service.refresh_decisions(d)

        doc = await R.call(R.update_analysis, aid, save_maps)
        part = _ca_version(doc, ca, cmap, kmap, doc["criteria"])
        rev_id = p.get("revision_id")
        if rev_id:
            base = await _cur(doc)
            btable = (((base.get("document") or {}).get("competitor") or {}).get("table") or {})
            ptable = part["document"]["competitor"]["table"]
            changes = []
            names = {c["id"]: c["name"] for c in doc.get("criteria") or []}
            for crt in ptable["criteria"]:
                row = ptable["cells"][crt]
                ids = [cid for cell in row.values() for cid in cell.get("claim_ids") or []]
                payload = {"claims": {k: part["claims"][k] for k in ids if k in part["claims"]},
                           "citations": [c for c in part["citations"] if c["claim_id"] in ids],
                           "sources": {s: part["sources"][s] for s in {c["source_id"] for c in part["citations"] if c["claim_id"] in ids}}}
                if crt not in (btable.get("cells") or {}):
                    changes.append({"id": nid("chg"), "kind": "row_add", "area": "competitor", "target": {"criterion_id": crt}, "before": None,
                                    "after": {"name": names.get(crt, ""), "cells": {k: c.get("text", "") for k, c in row.items()}}, "claim_ids": ids,
                                    "payload": {**payload, "cells": row, "criterion": next((c for c in doc["criteria"] if c["id"] == crt), {"id": crt, "name": names.get(crt, "")})},
                                    "reverted": False, "round": 1})
                    continue
                for col, cell in row.items():
                    old = (btable["cells"].get(crt) or {}).get(col)
                    if cell.get("placeholder") or (old and verify.N(old.get("text", "")) == verify.N(cell.get("text", ""))):
                        continue
                    cids = cell.get("claim_ids") or []
                    pl = {"claims": {k: part["claims"][k] for k in cids if k in part["claims"]}, "citations": [c for c in part["citations"] if c["claim_id"] in cids],
                          "sources": {s: part["sources"][s] for s in {c["source_id"] for c in part["citations"] if c["claim_id"] in cids}}, "cell": cell}
                    if old is None and col not in (btable.get("columns") or []):
                        continue
                    changes.append({"id": nid("chg"), "kind": "value_edit", "area": "competitor", "target": {"crt": crt, "col": col},
                                    "before": (old or {}).get("text", ""), "after": cell.get("text", ""), "claim_ids": cids, "payload": pl, "reverted": False, "round": 1})
            bstr = ((base.get("document") or {}).get("competitor") or {}).get("strengths") or []
            for i, s in enumerate(part["document"]["competitor"]["strengths"]):
                old = bstr[i] if i < len(bstr) else None
                if old and verify.N(old.get("note", "")) == verify.N(s.get("note", "")):
                    continue
                pl = {"strength": s, "claims": {k: part["claims"][k] for k in s.get("claim_ids") or [] if k in part["claims"]},
                      "citations": [c for c in part["citations"] if c["claim_id"] in (s.get("claim_ids") or [])],
                      "sources": {x: part["sources"][x] for x in {c["source_id"] for c in part["citations"] if c["claim_id"] in (s.get("claim_ids") or [])}}}
                changes.append({"id": nid("chg"), "kind": "strength_edit", "area": "competitor", "target": {"strength_id": (old or {}).get("id") or s["id"]},
                                "before": {"title": (old or {}).get("title"), "note": (old or {}).get("note")} if old else None,
                                "after": {"title": s.get("title"), "note": s.get("note")}, "claim_ids": s.get("claim_ids") or [], "payload": pl, "reverted": False, "round": 1})
            await R.call(R.update_doc, R.REV, rev_id, lambda r: r.update(changes=changes, status="proposed", sources_added=len(part["sources"]),
                                                                          quick_suggestions=["더 간결하게"]))
            return {"result": {"analysis_id": aid, "revision_id": rev_id, "changes": len(changes)}}
        # 경쟁 영역이 비어 있으면 바로 새 버전(kind=import)
        base = await R.call(R.get_version, aid, int(doc.get("result_version") or 0)) or {"document": {}, "claims": {}, "citations": [], "sources": {}, "area_status": {}}
        v = copy.deepcopy(base)
        v.pop("n", None)
        v.setdefault("document", {})["competitor"] = part["document"]["competitor"]
        v.setdefault("claims", {}).update(part["claims"])
        v.setdefault("citations", []).extend(part["citations"])
        v.setdefault("sources", {}).update(part["sources"])
        v.setdefault("area_status", {})["competitor"] = "done"
        n = await versions.save_new_version(doc, v, kind="import", summary="경쟁사 분석에서 가져옴", status="done")

        def upd(d: dict[str, Any]) -> None:
            d["analyzed_at"] = d.get("analyzed_at") or now_iso()
            d["last_screen"] = "result"

        saved = await R.call(R.update_analysis, aid, upd)
        await service.register(saved)
        return {"result": {"analysis_id": aid, "version": n}}

    return await run_linear(ctx, [("merge", merge)], {"merge": "경쟁사 분석 합치기"})
