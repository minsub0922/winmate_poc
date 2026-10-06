"""mi.design (§7.4) — 입력 읽기 → 첨부 읽기 → 요구 추출 → 업종 판별 → 빈칸 추론 → 쓰임 · 범위 · 경쟁사 · 표기 · 사내 자료 · 깊이
→ (업종 두 갈래면 한 번 묻기 ⏸) → 제목 · 주제 → 설계 저장(start_analysis 면 mi.analyze 를 잇는다).

MI1Q 는 묻는 동안 `자동으로 정한 것`(쓰임 · 범위 · 경쟁사 · 사내 자료)을 보이므로, 묻기 전에 1위 업종으로 나머지 결정을 먼저 정한다.
답이 1위와 다르면 업종에 기대는 결정(범위 · 사내 자료)만 다시 정한다. 묻는 동안 `판단에 도움이 될 말`이 오면 업종 판별만 다시 돌고 다시 묻는다.
"""
from __future__ import annotations

import logging
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.jobs import JobCanceled, JobContext, current_job

from .. import aix, anonymize, config, kbx, prompts, rules, service, verify
from .. import store as R
from .common import Budget, init_web, sensitive_texts
from .competitors import add_competitor, find_candidates, norm_name, same_company

log = logging.getLogger("winmate.mi.design")

STEP_LABELS = {
    "load_inputs": "입력 읽기", "read_files": "첨부 읽기", "extract_requirements": "첨부 읽기", "classify_segment": "업종 판별",
    "infer_gaps": "업종 판별", "decide_usage": "쓰임 · 범위 정하기", "decide_scope": "쓰임 · 범위 정하기", "decide_competitors": "경쟁사 찾기",
    "decide_naming": "설계 정리", "decide_internal": "설계 정리", "decide_depth": "설계 정리", "ask_segment": "업종 판별",
    "after_choice": "설계 정리", "title_topic": "설계 정리", "save_design": "설계 정리",
}
PROGRESS = {"load_inputs": 8, "read_files": 20, "extract_requirements": 30, "classify_segment": 42, "infer_gaps": 48, "decide_usage": 54,
            "decide_scope": 64, "decide_competitors": 76, "decide_internal": 82, "decide_depth": 86, "title_topic": 94, "save_design": 100}
EXEC_PHRASES = ("경영진 한 장", "한 장으로", "1장 요약", "한 장 요약")
DOC_KIND_LABEL = {"rfp": "RFP", "minutes": "회의록", "ir": "IR", "internal_research": "내부 조사", "deployment_report": "도입 보고서",
                  "price_list": "단가표", "spec_sheet": "사양서", "customer_material": "고객 자료", "other": "첨부"}


class DesignState(TypedDict, total=False):
    analysis_id: str
    auto_run: bool
    start_analysis: bool
    hint: str | None
    hint_pending: bool
    asked: bool
    tentative: str | None
    llm_failed: bool
    next_job_id: str | None
    web_unavailable: bool


# ── 저장 도우미 ──────────────────────────────────────────
async def _doc(aid: str) -> dict[str, Any]:
    doc = await R.call(R.get_analysis, aid)
    if doc is None:
        raise ApiError(404, "NOT_FOUND", "분석 작업을 찾을 수 없어요", {"id": aid})
    return doc


async def _save(aid: str, changes: dict[str, Any]) -> dict[str, Any]:
    """바꾼 키만 덮어쓴다(설계가 도는 동안 API 가 다른 키를 바꿔도 지우지 않게)."""
    return await R.call(R.update_analysis, aid, lambda d: d.update(changes))


def _all_text(doc: dict[str, Any], hint: str | None = None, *, limit: int = 6000) -> str:
    ext = doc.get("extracted") or {}
    parts = [doc.get("customer_name") or "", doc.get("requirements_text") or ""]
    parts += [r.get("text", "") for r in doc.get("requirements") or [] if r.get("origin") != "inferred"]
    parts += [t[:4000] for t in (ext.get("file_texts") or [])[:3]]
    parts += list(ext.get("key_messages") or [])
    parts += [m.get("text", "") for m in doc.get("memos") or [] if m.get("where") == "design"]
    if hint:
        parts.append(hint)
    return "\n".join(p for p in parts if p).strip()[:limit]


def _budget(state: DesignState) -> Budget:
    b = Budget(websearch=4, fetch=4, llm=20)
    b.web_unavailable = bool(state.get("web_unavailable"))
    return b


# ── 노드 ─────────────────────────────────────────────────
async def load_inputs(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    changes: dict[str, Any] = {"design_status": "running", "design_error": None}
    if doc.get("status") in ("draft", "designed", "stopped", "failed", "ask", "designing"):
        changes["status"] = "designing"
    links = doc.get("links") or {}
    if links.get("requirements_id") and (doc.get("extracted") or {}).get("rq_pending"):
        from ..api import link_requirements

        await link_requirements(doc, links["requirements_id"], links.get("rq_version"))
        for k in ("customer_name", "requirements", "requirements_text", "extracted", "links", "segment", "project_id", "input_kind"):
            changes[k] = doc.get(k)
    await _save(aid, changes)
    b = Budget()
    await init_web(b)
    return {"web_unavailable": b.web_unavailable, "hint_pending": False}


async def read_files(state: DesignState) -> dict[str, Any]:
    from winmate_common.platform import file_meta, parsed_document

    aid = state["analysis_id"]
    doc = await _doc(aid)
    files = [dict(f) for f in doc.get("files") or []]
    ext = dict(doc.get("extracted") or {})
    texts: list[str] = []
    summaries: list[str] = []
    changed = False
    for f in files:
        if not f.get("include", True):
            continue
        fid = f["file_id"]
        if not f.get("read"):
            try:
                meta = await file_meta(fid)
            except Exception:  # noqa: BLE001
                meta = {}
            try:
                parsed = await parsed_document(fid)
            except Exception as exc:  # noqa: BLE001
                log.warning("첨부 읽기 실패 %s: %s", fid, exc)
                f["read"] = True
                f["read_error"] = True
                changed = True
                continue
            pages = [p.get("text") or "" for p in parsed.get("pages") or []]
            scanned = [int(w.split(":", 1)[1]) for w in parsed.get("warnings") or [] if str(w).startswith("scanned_page:") and w.split(":", 1)[1].isdigit()]
            for no in scanned[:10]:
                t = await aix.i2t_page("mi.i2t_page", fid, no)
                if t and 0 < no <= len(pages):
                    pages[no - 1] = t
                    f["i2t"] = True
            text = "\n".join(pages) if pages else (parsed.get("text") or "")
            name = f.get("name") or meta.get("name") or parsed.get("title") or "첨부"
            cls = _classify_by_name(name)
            try:
                res = await aix.llm("mi.classify_file", prompts.classify_file(name, text[:3000]), prompts.FileClass, confidential=True)
                cls = {"doc_kind": res.doc_kind, "classification": res.classification, "title": res.title, "date": res.date}
            except (aix.LLMFailed, ApiError) as exc:
                log.info("파일 분류 LLM 실패(이름 규칙 사용): %s", exc)
            if meta.get("confidential"):
                cls["classification"] = "confidential"
            f.update(name=name, doc_kind=cls.get("doc_kind") or f.get("doc_kind", "other"), title=cls.get("title") or name, date=cls.get("date"),
                     read=True, pages=parsed.get("page_count") or len(pages))
            if not f.get("classification_pinned"):
                f["classification"] = cls.get("classification") or f.get("classification", "internal")
            f["_text"] = text[:6000]
            changed = True
        if f.get("classification") != "confidential" and f.get("doc_kind") not in ("price_list",):
            t = f.get("_text") or ""
            if t:
                texts.append(t[:4000])
        summaries.append(f"{f.get('name') or '첨부'} · {DOC_KIND_LABEL.get(f.get('doc_kind', 'other'), '첨부')}")
    ext["file_texts"] = texts
    ext["file_summaries"] = summaries
    kinds = {f.get("doc_kind") for f in files if f.get("include", True)}
    if "minutes" in kinds:
        input_kind = "회의록"
    elif "rfp" in kinds:
        input_kind = "RFP"
    elif doc.get("requirements") or len((doc.get("requirements_text") or "").strip()) >= int(config.th("one_line_chars", 60)):
        input_kind = "요구사항"
    else:
        input_kind = "메모"
    changes: dict[str, Any] = {"extracted": ext, "input_kind": input_kind}
    if changed:
        changes["files"] = files
    await _save(aid, changes)
    return {}


def _classify_by_name(name: str) -> dict[str, Any]:
    n = name.lower()
    if any(k in name for k in ("단가", "견적", "원가", "가격표")):
        return {"doc_kind": "price_list", "classification": "confidential"}
    if "rfp" in n or "제안요청" in name:
        return {"doc_kind": "rfp", "classification": "internal"}
    if "회의록" in name or "미팅" in name:
        return {"doc_kind": "minutes", "classification": "internal"}
    if "사업보고서" in name or "ir" in n.split(".")[0].split("_") or "보도자료" in name:
        return {"doc_kind": "ir", "classification": "public"}
    if "사양" in name or "spec" in n:
        return {"doc_kind": "spec_sheet", "classification": "internal"}
    return {"doc_kind": "other", "classification": "internal"}


def _one_line(doc: dict[str, Any]) -> bool:
    links = doc.get("links") or {}
    if doc.get("files") or links.get("requirements_id") or links.get("storyboard_id") or links.get("proposal_id"):
        return False
    total = len((doc.get("customer_name") or "").strip()) + len((doc.get("requirements_text") or "").strip())
    total += sum(len(r.get("text") or "") for r in doc.get("requirements") or [] if r.get("origin") not in ("inferred", "extracted"))
    return total < int(config.th("one_line_chars", 60))


async def extract_requirements(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    ext = dict(doc.get("extracted") or {})
    ext["one_line"] = _one_line(doc)
    text = _all_text(doc)
    changes: dict[str, Any] = {"extracted": ext}
    if text.strip():
        try:
            res = await aix.llm("mi.extract_requirements", prompts.extract_requirements(doc), prompts.ExtractReq, confidential=True)
        except (aix.LLMFailed, ApiError) as exc:
            log.info("요구 추출 실패: %s", exc)
            res = None
        if res is not None:
            ext.update(eval_criteria=res.eval_criteria[:10], schedule=res.schedule[:10], keywords=res.keywords[:12],
                       region=(res.region or None))
            structured = [r for r in doc.get("requirements") or [] if r.get("origin") in ("definition", "storyboard", "preset", "user")]
            if not structured:
                keep = [r for r in doc.get("requirements") or [] if r.get("origin") not in ("extracted",)]
                seen = {verify.N(r.get("text", "")) for r in keep}
                for t in res.requirements[:8]:
                    t = (t or "").strip()
                    if t and verify.N(t) not in seen:
                        keep.append({"id": R.nid("req"), "text": t[:80], "label": t[:24], "origin": "extracted", "weight": None})
                        seen.add(verify.N(t))
                changes["requirements"] = keep
            # RFP · 요구 원문에 실제로 나온 경쟁사 이름만(지어내기 방지)
            hay = verify.N(text)
            comps = [dict(c) for c in doc.get("competitors") or []]
            added = False
            for name in res.competitor_mentions[:6]:
                nm = norm_name(name)
                if not nm or verify.N(nm) not in hay or "삼성" in nm or "samsung" in nm.lower():
                    continue
                if any(same_company(nm, c) for c in comps):
                    continue
                tmp = {"competitors": comps}
                add_competitor(tmp, nm, origin="mi_rfp", pinned=False)
                comps = tmp["competitors"]
                added = True
            if added:
                changes["competitors"] = comps
    await _save(aid, changes)
    return {}


async def classify_segment(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    seg = dict(doc.get("segment") or {})
    hint = state.get("hint") if state.get("hint_pending") else None
    if (seg.get("mode") == "pin" or seg.get("inherited_from")) and not hint:
        # 고정 · 상속 — LLM 호출 없이(AC-MI-07)
        return {"tentative": None, "llm_failed": False, "hint_pending": False}
    text = _all_text(doc, hint)
    kb_items: dict[str, dict[str, Any]] = {}
    similar: list[str] = []
    if text.strip():
        try:
            kb = await kbx.classify(text)
            kb_items = {i["code"]: i for i in kb.get("items") or []}
            similar = list(kb.get("similar_case_ids") or [])[:10]
        except ApiError as exc:
            log.info("kb 업종 근거 실패: %s", exc)
    llm_p: dict[str, float] = {}
    llm_clues: dict[str, list[str]] = {}
    failed = False
    try:
        out = await aix.llm("mi.classify_segment", prompts.classify_segment(doc, hint), prompts.SegClass, confidential=True)
        for s in out.segments:
            code = (s.code or "").upper()
            if code in config.SEGMENT_CODES:
                llm_p[code] = max(0.0, min(1.0, float(s.p)))
                llm_clues[code] = [c for c in s.clues if c and verify.N(c) in verify.N(text)]
    except (aix.LLMFailed, ApiError) as exc:
        log.info("업종 LLM 실패 → kb 식: %s", exc)
        failed = True
    cands = []
    for code in config.SEGMENT_CODES:
        k = kb_items.get(code) or {}
        kb_s = float(k.get("kb_score") or 0.0)
        cl_s = float(k.get("clue_score") or 0.0)
        conf = rules.combine_confidence(None if failed else llm_p.get(code, 0.0), kb_s, cl_s)
        cands.append({"code": code, "confidence": conf, "kb": kb_s, "clue": cl_s, "llm": None if failed else llm_p.get(code, 0.0)})
    cands.sort(key=lambda c: (-c["confidence"], config.SEGMENT_CODES.index(c["code"])))
    code, mode = rules.decide_segment([(c["code"], c["confidence"]) for c in cands], llm_failed=failed)
    if mode == "ask" and state.get("auto_run"):
        mode = "check"   # 제안서 자동 실행은 묻지 않고 1위(확인 권장)로(AC-MI-93)
    top = cands[:2]
    clues: list[dict[str, Any]] = []
    for c in top:
        kb_c = [x.get("text", "") for x in (kb_items.get(c["code"]) or {}).get("clues") or []]
        merged = list(dict.fromkeys(llm_clues.get(c["code"], []) + kb_c))[:3]
        clues += [{"text": t, "code": c["code"]} for t in merged if t]
    gap = (rules.to100(top[0]["confidence"]) - rules.to100(top[1]["confidence"])) / 100 if len(top) > 1 else 1.0
    seg.update(code=code, mode=mode, confidence=None if code == "GEN" else next(c["confidence"] for c in cands if c["code"] == code),
               candidates=cands[:5], clues=clues, llm_failed=failed, gap=round(gap, 2), similar_case_ids=similar, inherited_from=None,
               mix=None if mode != "pin" else seg.get("mix"))
    if hint:
        seg["hint"] = hint
    await _save(aid, {"segment": seg})
    return {"tentative": code if mode == "ask" else None, "llm_failed": failed, "hint_pending": False}


async def infer_gaps(state: DesignState) -> dict[str, Any]:
    """한 줄 메모뿐 → 업종 사례 공통 요구 · 유사 사례 요구로 요구 항목 최대 3개를 inferred 로(§7.4)."""
    aid = state["analysis_id"]
    doc = await _doc(aid)
    if not (doc.get("extracted") or {}).get("one_line"):
        return {}
    reqs = [r for r in doc.get("requirements") or [] if r.get("origin") != "inferred"]
    code = (doc.get("segment") or {}).get("code") or "GEN"
    picked: list[tuple[str, str]] = []
    if code != "GEN":
        ins = await kbx.insights_view(code)
        for rt in ins.get("req_types") or []:
            if rt.get("label"):
                picked.append((rt["label"], f"{ins['short']} 사례 {rt.get('n', 0)}건"))
    if len(picked) < int(config.th("inferred_max", 3)):
        for dep in await kbx.similar_cases(_all_text(doc), limit=5):
            case = await kbx.case(dep["id"])
            for n in (case or {}).get("needs") or []:
                if n.get("kind") == "needs" and n.get("text"):
                    picked.append((n["text"], f"유사 사례 · {(case or {}).get('title', '')[:30]}"))
                    break
    seen: set[str] = set()
    inferred = []
    for text, basis in picked:
        k = verify.N(text)
        if k in seen:
            continue
        seen.add(k)
        inferred.append({"id": R.nid("req"), "text": text[:80], "label": text[:24], "origin": "inferred", "inferred": True, "basis": basis})
        if len(inferred) >= int(config.th("inferred_max", 3)):
            break
    await _save(aid, {"requirements": reqs + inferred})
    return {}


async def decide_usage(state: DesignState) -> dict[str, Any]:
    from winmate_common.client import ServiceClient

    aid = state["analysis_id"]
    doc = await _doc(aid)
    u = dict(doc.get("usage") or {})
    links = dict(doc.get("links") or {})
    changes: dict[str, Any] = {}
    if u.get("mode") != "pin":
        text = " ".join([doc.get("requirements_text") or ""] + [r.get("text", "") for r in doc.get("requirements") or []]
                        + [m.get("text", "") for m in doc.get("memos") or []])
        phrase = next((p for p in EXEC_PHRASES if p in text), None)
        value, mode, reason = "none", "auto", "연결된 제안서가 없어 리포트로 정리해요"
        ptype = links.get("proposal_type")
        if phrase:
            value, reason = "exec_onepager", f"요구에 '{phrase}' 있음"
        elif ptype in ("standard", "solution", "quickwin"):
            value = ptype
            reason = _linked_reason(ptype, links.get("proposal_title"))
        else:
            found = await _find_proposal(ServiceClient, doc, links.get("proposal_id"))
            if found:
                value = found["proposal_type"]
                mode = "auto" if found["how"] in ("id", "project") else "check"
                reason = _linked_reason(value, found["title"])
                links.update(proposal_id=found["id"], proposal_title=found["title"], proposal_type=value)
                changes["links"] = links
        u = {"value": value, "mode": mode, "reason": reason}
        changes["usage"] = u
    if not doc.get("anonymize_pinned"):
        changes["anonymize"] = rules.is_customer_facing(u.get("value"))
    await _save(aid, changes)
    return {}


def _linked_reason(ptype: str, title: str | None) -> str:
    name = rules.USAGE_TYPE_NAME.get(ptype, "제안서")
    return f"{name} '{title}'에 연결됨" if title else f"{name}에 연결됨"


async def _find_proposal(client_cls: Any, doc: dict[str, Any], pid: str | None) -> dict[str, Any] | None:
    """연결 없으면 workspace 에서 같은 프로젝트 · 고객의 제안서(feature=PR) 유형을 읽는다(meta.proposal_type)."""
    try:
        c = client_cls("workspace", timeout=20)
        items: list[dict[str, Any]] = []
        if doc.get("project_id"):
            items = (await c.get("/v1/items", params={"feature": "PR", "project_id": doc["project_id"], "owner": "all", "limit": 20})).get("items") or []
            how = "project"
        if not items and (doc.get("customer_name") or "").strip():
            items = (await c.get("/v1/items", params={"feature": "PR", "q": doc["customer_name"].strip()[:30], "owner": "all", "limit": 20})).get("items") or []
            how = "customer"
    except ApiError:
        return None
    for it in items:
        if pid and it.get("item_id") != pid:
            continue
        ptype = (it.get("meta") or {}).get("proposal_type")
        if ptype in ("standard", "solution", "quickwin"):
            return {"id": it["item_id"], "title": it.get("title") or "", "proposal_type": ptype, "how": "id" if pid else how}
    return None


async def _public_doc_count(doc: dict[str, Any], budget: Budget) -> int:
    """고객 공개 자료 수(§7.4) — sources 모드: 서로 다른 고객 도메인 · 공시 URL 수, summary_only: 요약에서 뽑은 서로 다른 공개 문서 이름 수 + 첨부 ir."""
    n_ir = sum(1 for f in doc.get("files") or [] if f.get("doc_kind") == "ir" and f.get("include", True))
    cust = (doc.get("customer_name") or "").strip()
    if not cust or budget.web_unavailable:
        return n_ir
    q = aix.query_guard(f"{cust} 사업보고서 OR IR OR 보도자료", sensitive_texts(doc))
    if not q or not budget.take("websearch"):
        return n_ir
    try:
        res = await aix.websearch("mi.web_scope", q)
    except ApiError as exc:
        if exc.status in (429, 502, 503, 504):
            budget.web_unavailable = True
            return n_ir
        raise
    if budget.mode == "sources" and res.get("sources"):
        hosts = set()
        for s in res.get("sources") or []:
            m = re.match(r"https?://([^/]+)", s.get("url") or "")
            if m:
                hosts.add(m.group(1).removeprefix("www.") + ("/dart" if "dart" in (s.get("url") or "") else ""))
        return n_ir + len(hosts)
    summary = res.get("summary") or ""
    if not summary.strip():
        return n_ir
    try:
        out = await aix.llm("mi.public_docs", prompts.public_docs(cust, summary), prompts.PublicDocs, confidential=False)
    except (aix.LLMFailed, ApiError):
        return n_ir
    hay = verify.N(summary)
    names = {verify.N(d) for d in out.documents if d and verify.N(d) in hay}
    return n_ir + len(names)


async def _scope_for(doc: dict[str, Any], state: DesignState) -> dict[str, Any]:
    sc = dict(doc.get("scope") or {})
    seg = (doc.get("segment") or {}).get("code") or "GEN"
    if sc.get("mode") == "pin":
        areas = [a for a in rules.AREAS if a in (sc.get("areas") or [])]
        reasons = dict(sc.get("reasons") or {})
        reason_text = sc.get("reason_text") or "사람이 정한 범위"
        mode = "pin"
    else:
        areas: list[str] = []
        reasons: dict[str, str] = {}
        llm_reason = ""
        try:
            out = await aix.llm("mi.decide_scope", prompts.decide_scope(doc, seg), prompts.ScopeOut, confidential=True)
            for a in rules.AREAS:
                inc = getattr(out.areas, a)
                if inc.include:
                    areas.append(a)
                    reasons[a] = inc.reason or "요구사항 기준"
            llm_reason = " · ".join(reasons[a] for a in areas[:2] if reasons.get(a))
        except (aix.LLMFailed, ApiError) as exc:
            log.info("범위 LLM 실패 → 기본 범위: %s", exc)
            areas = ["market", "customer"]
            reasons = {"market": "기본 범위", "customer": "기본 범위"}
        text = " ".join([doc.get("requirements_text") or ""] + [r.get("text", "") for r in doc.get("requirements") or [] if r.get("origin") != "inferred"]
                        + [m.get("text", "") for m in doc.get("memos") or [] if m.get("where") == "design"])
        areas, reasons, phrases = service.apply_scope_keywords(text, areas, reasons)
        if anonymize.live(doc.get("competitors") or []) and "competitor" not in areas:
            areas = [a for a in rules.AREAS if a in areas + ["competitor"]]
            reasons["competitor"] = "지정한 경쟁사가 있음"
        if not areas:
            areas = ["market"]
            reasons["market"] = "기본 범위"
        if phrases:
            reason_text = "요구에 " + " · ".join(f"'{p}'" for p in dict.fromkeys(phrases)) + " 있음"
        else:
            reason_text = llm_reason or "요구사항 · 업종 기준"
        mode = "auto"
        if any(r.get("origin") == "inferred" for r in doc.get("requirements") or []):
            mode = "check"
            reason_text = f"한 줄 메모라 사례 DB로 요구 {sum(1 for r in doc.get('requirements') or [] if r.get('origin') == 'inferred')}개를 추론했어요"
    reduced: list[str] = []
    ext_changes: dict[str, Any] = {}
    if "customer" in areas:
        b = _budget(state)
        await init_web(b)
        n_pub = await _public_doc_count(doc, b)
        ext_changes["customer_public_docs"] = n_pub
        if n_pub < int(config.th("customer_public_min", 3)):
            reduced = ["customer"]
    return {"scope": {"areas": areas, "mode": mode, "reasons": reasons, "reason_text": reason_text, "reduced": reduced}, "ext": ext_changes}


async def decide_scope(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    res = await _scope_for(doc, state)
    ext = dict(doc.get("extracted") or {})
    ext.update(res["ext"])
    await _save(aid, {"scope": res["scope"], "extracted": ext})
    return {}


async def decide_competitors(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    areas = service.areas_of(doc)
    if "competitor" not in areas:
        return {}
    changes: dict[str, Any] = {}
    comps = [dict(c) for c in doc.get("competitors") or []]
    decisions = dict(doc.get("decisions") or {})
    seg = (doc.get("segment") or {}).get("code") or "GEN"
    short = config.segment(seg).get("short", "업종")
    if not anonymize.live(comps):
        b = _budget(state)
        await init_web(b)
        cands, _summary = await find_candidates(doc, b, want=int(config.th("competitor_auto_top", 3)), exclude=comps)
        tmp = {"competitors": comps}
        for c in cands:
            add_competitor(tmp, c.name, origin="auto", aliases=c.aliases, kind_label=c.kind_label, desc=c.desc, confidence=c.confidence)
        comps = tmp["competitors"]
        changes["competitors"] = comps
        reason = f"지정 없음 → {short} 사례 빈도 상위 {int(config.th('competitor_auto_top', 3))}"
        if not cands:
            reason = "지정 없음 · 공개 자료에서 후보를 찾지 못했어요"
        decisions["competitors"] = {**(decisions.get("competitors") or {}), "mode": "check", "reason": reason}
        changes["decisions"] = decisions
    else:
        origins = {c.get("origin") for c in anonymize.live(comps)}
        reason = "직접 지정한 경쟁사" if origins <= {"user"} else ("RFP 에 나온 경쟁사" if "mi_rfp" in origins else "지정한 경쟁사")
        mode = "pin" if origins <= {"user", "ca_import"} else ("check" if "auto" in origins else "auto")
        decisions["competitors"] = {**(decisions.get("competitors") or {}), "mode": mode, "reason": reason}
        changes["decisions"] = decisions
    if not any(c.get("pinned") for c in doc.get("criteria") or []):
        code = ((doc.get("segment") or {}).get("mix") or {}).get("a") or seg
        ins = await kbx.insights_view(code) if code and code != "GEN" else None
        changes["criteria"] = service.default_criteria({**doc, **changes}, ins)
    await _save(aid, changes)
    return {}


async def decide_naming(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    if doc.get("anonymize_pinned"):
        return {}
    await _save(aid, {"anonymize": rules.is_customer_facing((doc.get("usage") or {}).get("value"))})
    return {}


async def _internal(doc: dict[str, Any]) -> dict[str, Any]:
    seg = doc.get("segment") or {}
    codes: list[str] = []
    if seg.get("mix"):
        codes = [seg["mix"].get("a"), seg["mix"].get("c")]
    elif seg.get("mode") == "ask" and len(seg.get("candidates") or []) >= 2:
        codes = [seg["candidates"][0]["code"], seg["candidates"][1]["code"]]
    elif seg.get("code") and seg.get("code") != "GEN":
        codes = [seg["code"]]
    codes = [c for c in dict.fromkeys(codes) if c and c != "GEN"]
    counts = {}
    for c in codes:
        try:
            counts[c] = int((await kbx.insights(c)).get("cases") or 0)
        except ApiError:
            counts[c] = 0
    it = dict(doc.get("internal") or {})
    if it.get("mode") != "pin":
        it["excluded_file_ids"] = [f["file_id"] for f in doc.get("files") or [] if f.get("classification") == "confidential"]
    it["kb_case_count"] = sum(counts.values())
    if len(codes) == 2:
        a, b = codes
        it["summary_override"] = f"{config.segment(a)['nick']} {counts[a]} + {config.segment(b)['nick']} {counts[b]}건"
    else:
        it.pop("summary_override", None)
    return it


async def decide_internal(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    await _save(aid, {"internal": await _internal(doc)})
    return {}


async def decide_depth(state: DesignState) -> dict[str, Any]:
    """깊이 · 결정 7행(depends_on · input_hash · 바뀐 것만 updated_at) · 시트 미리보기."""
    aid = state["analysis_id"]
    doc = await _doc(aid)
    service.refresh_decisions(doc)
    await _save(aid, {"decisions": doc["decisions"], "depth": doc["depth"], "internal": doc["internal"]})
    return {}


def ask_request(doc: dict[str, Any]) -> dict[str, Any]:
    """MI1Q — awaiting_input 데이터(질문 · 단서 · 선택지 3 · 자동으로 정한 것)."""
    seg = doc.get("segment") or {}
    cands = seg.get("candidates") or []
    a = cands[0] if cands else {"code": seg.get("code") or "GEN", "confidence": 0.0}
    b = cands[1] if len(cands) > 1 else {"code": "GEN", "confidence": 0.0}
    sa, sb = config.segment(a["code"]), config.segment(b["code"])
    counts = {}
    it = doc.get("internal") or {}
    ov = it.get("summary_override") or ""
    for s in (sa, sb):
        m = re.search(re.escape(s["nick"]) + r" (\d+)", ov)
        counts[s["code"]] = int(m.group(1)) if m else None
    mix_conf = rules.mix_score(a["confidence"], b["confidence"])

    def desc(s: dict[str, Any]) -> str:
        n = counts.get(s["code"])
        return f"{s['perspective']}." + (f" 사례 {n}건" if n is not None else "")

    options = [
        {"key": a["code"], "segment": a["code"], "name": sa["short"], "desc": desc(sa), "score": a["confidence"], "codes": f"MI-{a['code']}-A · B · C",
         "recommended": True, "thumbs": ["barline", "process", "journey"]},
        {"key": b["code"], "segment": b["code"], "name": sb["short"], "desc": desc(sb), "score": b["confidence"], "codes": f"MI-{b['code']}-A · B · C",
         "recommended": False, "thumbs": ["barline", "process", "journey"]},
        {"key": "MIX", "segment": "MIX", "name": "섞어서 보기",
         "desc": f"시장 · 비즈니스는 {sa['nick']}{rules.josa(sa['nick'], '으로', '로')}, 사용자 여정은 {sb['user']}{rules.josa(sb['user'], '으로', '로')}",
         "score": mix_conf, "codes": f"MI-{a['code']}-A · B + MI-{b['code']}-C", "recommended": False, "mix": {"a": a["code"], "b": a["code"], "c": b["code"]},
         "thumbs": ["barline", "process", "journey"]},
    ]
    kind_word = doc.get("input_kind") or "요구사항"
    decs = doc.get("decisions") or {}
    done = []
    if decs.get("usage"):
        done.append(f"쓰임 · {decs['usage']['display_value']}")
    areas = service.areas_of(doc)
    done.append(f"범위 · {len(areas)}개 영역")
    live = anonymize.live(doc.get("competitors") or [])
    if "competitor" in areas:
        if live:
            how = "익명" if doc.get("anonymize", True) else "실명"
            done.append(f"경쟁사 · {how} {' · '.join(c['letter'] for c in live)}")
        else:
            done.append("경쟁사 · 분석할 때 찾아요")
    done.append(f"사내 자료 · {it.get('summary_override') or ('도입사례 ' + str(it.get('kb_case_count') or 0) + '건')}")
    others = sum(1 for k in decs if k != "segment")
    clues = [{"t": c["text"], "code": c["code"]} for c in seg.get("clues") or []][:6]
    return {
        "kind": "segment_choice",
        "question": "어느 업종 관점으로 분석할까요?",
        "agent_text": f"{kind_word}{rules.josa(kind_word, '을', '를')} 읽어 보니 업종이 두 갈래로 읽혀요. 업종에 따라 시장 · 비즈니스 · 사용자 레이아웃이 통째로 달라져서, 이것 하나만 여쭤볼게요.",
        "diff": round((rules.to100(a["confidence"]) - rules.to100(b["confidence"])) / 100, 2),
        "gap_rule": f"기준 {float(config.th('segment_ask_gap', 0.1)):.2f} 미만",
        "clues": clues,
        "options": options,
        "default": a["code"],
        "default_text": f"답이 없으면 추천({sa['short']}){rules.josa('추천', '으로', '로')} 진행하고, 결과 화면의 업종 칩에서 언제든 바꿀 수 있어요.",
        "done": done,
        "footer": f"업종 확인 · 선택 필요 1 · 나머지 {others}개는 자동으로 정했어요",
        "hint": seg.get("hint"),
    }


async def ask_segment(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    req = ask_request(doc)
    await _save(aid, {"design_ask": req, "design_status": "ask", "status": "ask"})
    await service.register(await _doc(aid))
    answer = interrupt(req)
    # ── 답을 받고 이어서 ──
    ans = answer if isinstance(answer, dict) else {"segment": answer}
    if ans.get("hint"):
        return {"hint": str(ans["hint"])[:500], "hint_pending": True, "asked": True}
    doc = await _doc(aid)
    seg = dict(doc.get("segment") or {})
    cands = seg.get("candidates") or []
    top1 = cands[0]["code"] if cands else seg.get("code")
    top2 = cands[1]["code"] if len(cands) > 1 else None
    pick = str(ans.get("segment") or top1 or "GEN").upper()
    conf_of = {c["code"]: c["confidence"] for c in cands}
    if pick == "MIX" and top2:
        mx = ans.get("mix") or {}
        a, c = (mx.get("a") or top1), (mx.get("c") or top2)
        seg.update(code=a, mode="pin", mix={"a": a, "b": a, "c": c}, confidence=rules.mix_score(conf_of.get(a, 0.0), conf_of.get(c, 0.0)))
    else:
        if pick not in config.SEGMENT_CODES and pick != "GEN":
            pick = top1 or "GEN"
        seg.update(code=pick, mode="pin", mix=None, confidence=conf_of.get(pick))
    seg["asked"] = True
    await _save(aid, {"segment": seg, "design_ask": None, "design_status": "running", "status": "designing"})
    start = ans.get("start_analysis")
    return {"hint_pending": False, "asked": True, "start_analysis": bool(start) if start is not None else bool(state.get("start_analysis"))}


async def after_choice(state: DesignState) -> dict[str, Any]:
    """답이 1위와 다르거나 섞어서 보기면 업종에 기대는 결정(범위 · 사내 자료 · 기준)만 다시."""
    aid = state["analysis_id"]
    doc = await _doc(aid)
    seg = doc.get("segment") or {}
    changes: dict[str, Any] = {}
    if seg.get("code") != state.get("tentative") or seg.get("mix"):
        if (doc.get("scope") or {}).get("mode") != "pin":
            res = await _scope_for(doc, state)
            changes["scope"] = res["scope"]
            ext = dict(doc.get("extracted") or {})
            ext.update(res["ext"])
            changes["extracted"] = ext
        if not any(c.get("pinned") for c in doc.get("criteria") or []):
            code = (seg.get("mix") or {}).get("a") or seg.get("code")
            ins = await kbx.insights_view(code) if code and code != "GEN" else None
            changes["criteria"] = service.default_criteria({**doc, **changes}, ins)
    merged = {**doc, **changes}
    changes["internal"] = await _internal(merged)
    merged["internal"] = changes["internal"]
    service.refresh_decisions(merged)
    changes.update(decisions=merged["decisions"], depth=merged["depth"], internal=merged["internal"])
    await _save(aid, changes)
    return {}


def _default_scope_desc(doc: dict[str, Any], labels: list[str]) -> dict[str, str]:
    seg = config.segment(((doc.get("segment") or {}).get("mix") or {}).get("a") or (doc.get("segment") or {}).get("code"))
    useg = config.segment(((doc.get("segment") or {}).get("mix") or {}).get("c") or (doc.get("segment") or {}).get("code"))
    region = ((doc.get("extracted") or {}).get("region") or "국내").strip()
    cust = (doc.get("customer_name") or "고객사").strip()
    return {
        "market": f"{region} {seg['market']} {seg['product']} 시장 규모·성장률, 도입 트렌드, 규제",
        "customer": f"{cust} 전략 · 확장 계획 · 운영 구조",
        "user": f"{useg['users']} 페르소나 · 여정",
        "competitor": f"{' · '.join(labels) or '경쟁사'} 비교 → 삼성 강점",
    }


async def title_topic(state: DesignState) -> dict[str, Any]:
    aid = state["analysis_id"]
    doc = await _doc(aid)
    seg = (doc.get("segment") or {}).get("code") or "GEN"
    areas = service.areas_of(doc)
    live = anonymize.live(doc.get("competitors") or [])
    labels = [anonymize.workspace_label(c) for c in live]
    desc = _default_scope_desc(doc, labels)
    changes: dict[str, Any] = {}
    try:
        out = await aix.llm("mi.title_topic", prompts.title_topic(doc, seg, areas, labels), prompts.TitleTopic, confidential=True)
        comps = doc.get("competitors") or []
        if out.title and not doc.get("title_pinned"):
            changes["title"] = anonymize.scrub(out.title.strip(), comps, {})[:30]
        if out.topic:
            changes["topic"] = anonymize.scrub(out.topic.strip(), comps, {})[:30]
        sd = out.scope_desc.model_dump()
        for a in rules.AREAS:
            if sd.get(a):
                desc[a] = anonymize.scrub(sd[a].strip(), comps, {})[:80]
        if out.req_summary:
            changes["req_summary"] = out.req_summary.strip()[:60]
    except (aix.LLMFailed, ApiError) as exc:
        log.info("제목 · 주제 LLM 실패 → 기본값: %s", exc)
    if not doc.get("title_pinned") and not changes.get("title") and not doc.get("title"):
        t = service.default_title({**doc, "topic": changes.get("topic") or doc.get("topic") or rules.scope_label(areas)})
        if t:
            changes["title"] = t
    if not changes.get("topic") and not doc.get("topic"):
        changes["topic"] = " · ".join(rules.AREA_SHORT[a] for a in areas[:2]) if areas else "시장"
    changes["scope_desc"] = desc
    await _save(aid, changes)
    return {}


async def save_design(state: DesignState) -> dict[str, Any]:
    from ..deps import start_run

    aid = state["analysis_id"]
    doc = await _doc(aid)
    service.refresh_decisions(doc)
    st = doc.get("status")
    status = "designed" if st in ("designing", "ask", "draft", "stopped", "failed", "designed") else st
    doc.update(design_status="done", design_ask=None, design_error=None, status=status)
    if doc.get("last_screen") in ("input", "design/industry", None, ""):
        doc["last_screen"] = "design"
    doc = await R.call(R.update_analysis, aid, lambda d: d.update({k: doc[k] for k in ("decisions", "depth", "internal", "design_status", "design_ask",
                                                                                       "design_error", "status", "last_screen")}))
    await service.register(doc)
    nxt = None
    if state.get("start_analysis") or state.get("auto_run"):
        nxt = await start_run(doc, "full")
    return {"next_job_id": nxt}


# ── 그래프 ───────────────────────────────────────────────
def _after_classify(state: DesignState) -> str:
    return "ask_segment" if state.get("asked") else "infer_gaps"


async def _seg_mode(aid: str) -> str:
    doc = await _doc(aid)
    return (doc.get("segment") or {}).get("mode") or "auto"


def build() -> StateGraph:
    g = StateGraph(DesignState)
    for name, fn in (("load_inputs", load_inputs), ("read_files", read_files), ("extract_requirements", extract_requirements),
                     ("classify_segment", classify_segment), ("infer_gaps", infer_gaps), ("decide_usage", decide_usage),
                     ("decide_scope", decide_scope), ("decide_competitors", decide_competitors), ("decide_naming", decide_naming),
                     ("decide_internal", decide_internal), ("decide_depth", decide_depth), ("ask_segment", ask_segment),
                     ("after_choice", after_choice), ("title_topic", title_topic), ("save_design", save_design)):
        g.add_node(name, fn)
    g.add_edge(START, "load_inputs")
    g.add_edge("load_inputs", "read_files")
    g.add_edge("read_files", "extract_requirements")
    g.add_edge("extract_requirements", "classify_segment")
    g.add_conditional_edges("classify_segment", _after_classify, ["ask_segment", "infer_gaps"])
    g.add_edge("infer_gaps", "decide_usage")
    g.add_edge("decide_usage", "decide_scope")
    g.add_edge("decide_scope", "decide_competitors")
    g.add_edge("decide_competitors", "decide_naming")
    g.add_edge("decide_naming", "decide_internal")
    g.add_edge("decide_internal", "decide_depth")

    async def route_depth(state: DesignState) -> str:
        return "ask_segment" if (await _seg_mode(state["analysis_id"])) == "ask" else "title_topic"

    g.add_conditional_edges("decide_depth", route_depth, ["ask_segment", "title_topic"])
    g.add_conditional_edges("ask_segment", lambda s: "classify_segment" if s.get("hint_pending") else "after_choice",
                            ["classify_segment", "after_choice"])
    g.add_edge("after_choice", "title_topic")
    g.add_edge("title_topic", "save_design")
    g.add_edge("save_design", END)
    return g


async def handle(ctx: JobContext) -> dict[str, Any] | None:
    aid = ctx.payload["analysis_id"]
    init: DesignState = {"analysis_id": aid, "auto_run": bool(ctx.payload.get("auto_run")),
                         "start_analysis": bool(ctx.payload.get("start_analysis")), "asked": False, "hint_pending": False}
    try:
        final = await run_graph(ctx, build(), dict(init), step_labels=STEP_LABELS, progress_map=PROGRESS)
    except JobCanceled:
        await _cleanup(aid, ctx, "none")
        raise
    except Exception as exc:  # noqa: BLE001 — AwaitingInput 은 그대로 위로
        from winmate_common.jobs import AwaitingInput

        if isinstance(exc, AwaitingInput):
            raise
        await _cleanup(aid, ctx, "failed", error={"code": getattr(exc, "code", type(exc).__name__),
                                                    "message": getattr(exc, "message", str(exc))[:300]})
        raise
    final = final or {}
    return {"analysis_id": aid, "next_job_id": final.get("next_job_id")}


async def _cleanup(aid: str, ctx: JobContext, status: str, error: dict[str, Any] | None = None) -> None:
    try:
        doc = await R.call(R.get_analysis, aid)
        if not doc or doc.get("design_job_id") not in (ctx.job.id, None):
            return
        changes: dict[str, Any] = {"design_status": status, "design_error": error, "design_ask": None}
        if doc.get("status") in ("designing", "ask"):
            changes["status"] = "draft" if not doc.get("decisions") else "designed"
        await _save(aid, changes)
    except Exception:  # noqa: BLE001
        log.exception("설계 정리 실패")


__all__ = ["handle", "build", "ask_request", "current_job"]
