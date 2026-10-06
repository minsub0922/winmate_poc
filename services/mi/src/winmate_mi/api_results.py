"""결과 · 출처 · 질문 · 한 장 요약 · 확정 필요 항목(03-mi.md §6.5 · §6.6)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.jobs import jobs

from . import aix, claims as C, fixes, prompts, rules, service, verify, versions, views
from . import store as R
from .deps import enqueue, load, load_version
from .models import (
    AnswerOut, ClaimDetail, ClaimList, CustomerQuestionOut, FixApplyIn, FixItem, FixList, FixParseIn, FixParseOut, FixPatch,
    FixScanIn, FollowupIn, FollowupOut, JobAccepted, OnepagerOut, QuestionIn, ResultView, SnapshotOut, SourceAccepted, SourceAddIn,
    SourceList, VersionOut,
)

router = APIRouter(prefix="/v1")


async def _current(doc: dict[str, Any], version: int | None = None) -> dict[str, Any]:
    return await load_version(doc, version)


@router.get("/analyses/{aid}/result", response_model=ResultView, tags=["results"])
async def get_result(aid: str, version: int | None = None, tab: str | None = None, preview: bool = False) -> dict[str, Any]:
    """MI3 — 분석한 영역 탭 · 블록 · 비교표 · 강점 · 출처 요약 · 확인 권장 칩. preview=true 면 실행 중 정리된 영역만(MI3G 미리 보기)."""
    doc = await load(aid)
    if preview and doc.get("status") in ("queued", "running"):
        draft = await R.call(R.get_draft, aid) or {}
        dv = draft.get("work")
        if dv:
            return views.result_view(doc, {**dv, "n": int(doc.get("result_version") or 0) + 1}, preview=True, draft=draft)
    v = await _current(doc, version)
    return views.result_view(doc, v, latest_n=int(doc.get("result_version") or 0))


@router.get("/analyses/{aid}/claims", response_model=ClaimList, tags=["results"])
async def list_claims(aid: str, tab: str = "market", status: str | None = None, version: int | None = None) -> dict[str, Any]:
    doc = await load(aid)
    v = await _current(doc, version)
    if tab not in rules.AREAS:
        raise ApiError(422, "VALIDATION_FAILED", f"모르는 탭이에요: {tab}")
    return views.claims_list(v, tab, only_needs=status == "needs_check")


def _detail(doc: dict[str, Any], v: dict[str, Any], clm: str) -> dict[str, Any]:
    claim = (v.get("claims") or {}).get(clm)
    if claim is None:
        raise service.not_found("주장", clm)
    area = claim.get("area", "market")
    ns, src_n = views.numbering(v, area)
    cards = []
    srcs = v.get("sources") or {}
    cits = C.citations_of(v, clm)
    for cit in sorted(cits, key=lambda c: src_n.get(c["source_id"], 99)):
        src = srcs.get(cit["source_id"])
        if not src:
            continue
        snap_text, _ = R.load_snapshot(src["id"])
        cards.append(views.source_card(src, cit, src_n.get(src["id"], 0), claim=claim, has_snapshot=bool(snap_text)))
    item = {"id": clm, "area": area, "text": claim.get("text", ""), "status": claim.get("status", "missing"),
            "label": claim.get("label") or verify.claim_label(claim.get("status", "missing")),
            "citations": [{"n": src_n.get(c["source_id"], 0), "source_id": c["source_id"], "status": c.get("status", "needs_check")} for c in cits],
            "inferred": bool(claim.get("inferred")), "block_path": claim.get("block_path", "")}
    fix_id = next((f["id"] for f in (v.get("fix_items") or {}).values() if f.get("claim_id") == clm), None)
    return {"claim": item, "tab": area, "tab_label": rules.AREA_TAB[area], "cards": cards,
            "counts": {"total": len(cards), "matched": sum(1 for c in cards if c["status"] == "matched"),
                       "needs_check": sum(1 for c in cards if c["status"] not in ("matched", "confirmed"))},
            "conflict": claim.get("conflict"), "fix_id": fix_id}


@router.get("/analyses/{aid}/claims/{clm}", response_model=ClaimDetail, tags=["results"])
async def get_claim(aid: str, clm: str, version: int | None = None) -> dict[str, Any]:
    doc = await load(aid)
    return _detail(doc, await _current(doc, version), clm)


@router.get("/analyses/{aid}/sources", response_model=SourceList, tags=["results"])
async def list_sources(aid: str, tab: str | None = None, kind: str | None = None, state: str | None = None,
                       version: int | None = None) -> dict[str, Any]:
    """출처 목록. tab 을 주면 그 탭 번호 · 카드(종류 필터: public · kb_case · needs_check · …)."""
    doc = await load(aid)
    v = await _current(doc, version)
    srcs = v.get("sources") or {}
    items = []
    src_n: dict[str, int] = {}
    if tab:
        _, src_n = views.numbering(v, tab)
        ids = list(src_n.keys())
    else:
        ids = list(srcs.keys())
    for sid in ids:
        s = srcs.get(sid)
        if not s:
            continue
        g = views.src_group(s)
        if kind == "needs_check" and not views.source_needs_check(v, sid, tab):
            continue
        if kind and kind != "needs_check" and kind not in (g, s.get("kind")):
            continue
        if state and s.get("state") != state:
            continue
        cit = next((c for c in v.get("citations") or [] if c.get("source_id") == sid and not c.get("dropped")
                    and (not tab or (v.get("claims") or {}).get(c["claim_id"], {}).get("area") == tab)), None)
        snap_text, _ = R.load_snapshot(sid)
        out = {k: s.get(k) for k in ("id", "kind", "subtype", "title", "publisher", "url", "file_id", "published_at", "published_basis", "retrieved_at",
                                     "authority", "classification", "state", "excluded_reason", "mode", "areas", "competitor_id", "query")}
        out = {k: v_ for k, v_ in out.items() if v_ is not None}
        out["n"] = src_n.get(sid)
        out["card"] = views.source_card(s, cit, src_n.get(sid, 0), claim=(v.get("claims") or {}).get((cit or {}).get("claim_id", "")),
                                        has_snapshot=bool(snap_text))
        items.append(out)
    c = {"total": len(items), "public": sum(1 for i in items if views.src_group(srcs[i["id"]]) == "public"),
         "kb_case": sum(1 for i in items if views.src_group(srcs[i["id"]]) == "kb_case"),
         "needs_check": sum(1 for i in items if views.source_needs_check(v, i["id"], tab))}
    return {"items": items, "counts": c}


@router.get("/analyses/{aid}/sources/{src}/snapshot", response_model=SnapshotOut, tags=["results"])
async def get_snapshot(aid: str, src: str) -> dict[str, Any]:
    await load(aid)
    text, pages = R.load_snapshot(src)
    if text is None:
        raise service.not_found("수집본", src)
    return {"text": text, "pages": pages}


@router.post("/analyses/{aid}/sources", status_code=202, response_model=SourceAccepted, tags=["results"])
async def add_source(aid: str, body: SourceAddIn) -> dict[str, Any]:
    """출처 직접 추가 — URL 수집 또는 파일 추출 → §7.6 대조 → 그 주장 인용(잡 mi.source_add)."""
    if not body.url and not body.file_id:
        raise ApiError(422, "VALIDATION_FAILED", "URL 이나 파일 중 하나를 주세요")
    doc = await load(aid)
    v = await _current(doc)
    if body.claim_id and body.claim_id not in (v.get("claims") or {}):
        raise service.not_found("주장", body.claim_id)
    sid = R.nid("src")

    def mark(ver: dict[str, Any]) -> None:
        ver.setdefault("sources", {})[sid] = {
            "id": sid, "kind": "file" if body.file_id else "web", "subtype": "기타", "title": body.url or "올린 자료", "publisher": "",
            "url": body.url, "file_id": body.file_id, "published_at": None, "published_basis": "unknown", "retrieved_at": now_iso(),
            "authority": 5, "classification": body.classification or ("public" if body.url else "internal"), "state": "checking",
            "mode": "user", "areas": [(v.get("claims") or {}).get(body.claim_id, {}).get("area")] if body.claim_id else [],
            "claim_id": body.claim_id}
        if body.claim_id:
            ver.setdefault("citations", []).append({"claim_id": body.claim_id, "source_id": sid, "quote": "", "status": "needs_check",
                                                    "check": {}, "reason_code": None, "reason_text": "", "verified_at": now_iso(), "pending": True})
            ver["claims"][body.claim_id]["status"] = "checking"
            ver["claims"][body.claim_id]["label"] = verify.claim_label("checking")

    await versions.update_current(doc, mark)
    job_id = await enqueue("mi.source_add", {"analysis_id": aid, "source_id": sid, "claim_id": body.claim_id, "url": body.url,
                                             "file_id": body.file_id, "classification": body.classification}, doc, title="출처 확인")
    return {"job_id": job_id, "source_id": sid, "status": "queued"}


@router.delete("/analyses/{aid}/claims/{clm}/sources/{src}", response_model=ClaimDetail, tags=["results"])
async def remove_claim_source(aid: str, clm: str, src: str) -> dict[str, Any]:
    """이 출처 빼기 → 주장 상태 다시 계산. 마지막 출처를 빼면 missing + 확정 필요 항목(AC-MI-40)."""
    doc = await load(aid)
    v = await _current(doc)
    if clm not in (v.get("claims") or {}):
        raise service.not_found("주장", clm)
    if not any(c.get("source_id") == src for c in C.citations_of(v, clm)):
        raise service.not_found("인용", src)
    v = await versions.update_current(doc, lambda ver: C.remove_citation(ver, clm, src))
    return _detail(doc, v, clm)


# ── 질문 · 후속 질문 ─────────────────────────────────────
async def _answer(doc: dict[str, Any], v: dict[str, Any], text: str, tab: str | None, claim_id: str | None) -> dict[str, Any]:
    """저장된 출처 스냅숏 · 결과 문장으로만 답한다(새 웹 검색 없음). 답 속 수치는 §7.6.6 검사."""
    areas = [tab] if tab in rules.AREAS else [a for a in rules.AREAS if a in (v.get("area_status") or {})]
    evidence = []
    num_of: dict[str, int] = {}
    for a in areas:
        _, src_n = views.numbering(v, a)
        for sid, n in src_n.items():
            s = (v.get("sources") or {}).get(sid) or {}
            snap, _ = R.load_snapshot(sid)
            quotes = [c.get("quote") for c in v.get("citations") or [] if c.get("source_id") == sid and not c.get("dropped") and c.get("quote")]
            body = (snap or s.get("summary") or " / ".join(quotes))[:1500]
            evidence.append({"n": n, "source_id": sid, "title": s.get("title", ""), "text": body})
            num_of[sid] = n
    claim_lines = [f"- {c['text']}" for c in (v.get("claims") or {}).values() if c.get("area") in areas][:40]
    if claim_id and claim_id in (v.get("claims") or {}):
        claim_lines.insert(0, f"(선택한 주장) {v['claims'][claim_id]['text']}")
    if not evidence:
        return {"answer_md": "저장된 출처로는 답할 수 없어요", "citations": [], "answerable": False}
    try:
        res = await aix.llm("mi.answer", prompts.answer(text, evidence, claim_lines, doc), prompts.AnswerOut, confidential=True)
    except (aix.LLMFailed, ApiError):
        return {"answer_md": "저장된 출처로는 답할 수 없어요", "citations": [], "answerable": False}
    if not res.answerable or not res.answer_md.strip():
        return {"answer_md": "저장된 출처로는 답할 수 없어요", "citations": [], "answerable": False}
    valid = {e["n"]: e for e in evidence}
    cits = [{"n": n, "source_id": valid[n]["source_id"]} for n in dict.fromkeys(res.citations) if n in valid]
    pseudo = [{"quote": valid[c["n"]]["text"]} for c in cits]
    masked, _ = verify.mask_unsupported(res.answer_md, pseudo)
    return {"answer_md": masked, "citations": cits, "answerable": True}


@router.post("/analyses/{aid}/questions", response_model=AnswerOut, tags=["results"])
async def ask_question(aid: str, body: QuestionIn) -> dict[str, Any]:
    doc = await load(aid)
    v = await _current(doc)
    return await _answer(doc, v, body.text, body.tab, body.claim_id)


@router.post("/analyses/{aid}/followups", response_model=FollowupOut, tags=["results"])
async def followup(aid: str, body: FollowupIn) -> dict[str, Any]:
    """후속 질문 → 의도 판별(§7.9). question 이면 저장된 출처로 답, revision 이면 재분석 안을 만들고 MI3R 로."""
    doc = await load(aid)
    v = await _current(doc)
    try:
        intent = await aix.llm("mi.followup_intent", prompts.followup_intent(body.text, body.tab, doc), prompts.FollowupIntent, confidential=True)
    except (aix.LLMFailed, ApiError):
        intent = prompts.FollowupIntent(intent="question")
    if intent.intent == "revision":
        from .api_more import create_revision

        area = intent.area or body.tab or "competitor"
        scope = {"kind": "area", "area": area if area in rules.AREAS else "competitor"}
        rev_id, job_id = await create_revision(doc, scope, intent.instruction or body.text, origin="followup")
        return {"intent": "revision", "revision_id": rev_id, "job_id": job_id, "scope": scope, "instruction": intent.instruction or body.text}
    ans = await _answer(doc, v, body.text, body.tab, None)
    return {"intent": "question", "answer_md": ans["answer_md"], "citations": ans["citations"]}


@router.post("/analyses/{aid}/onepager", status_code=202, response_model=JobAccepted, tags=["results"])
async def make_onepager(aid: str) -> dict[str, Any]:
    """`한 장 요약` — IM-B 형식(4분면 + 결론) 요약. 새 검색 없음(잡 mi.onepager)."""
    doc = await load(aid)
    await _current(doc)
    job_id = await enqueue("mi.onepager", {"analysis_id": aid}, doc, title="한 장 요약")
    await R.call(R.put_doc, R.ONE, aid, {"analysis_id": aid, "status": "running", "job_id": job_id, "created_at": now_iso()})
    return {"job_id": job_id, "status": "queued"}


@router.get("/analyses/{aid}/onepager", response_model=OnepagerOut, tags=["results"])
async def get_onepager(aid: str) -> dict[str, Any]:
    await load(aid)
    d = await R.call(R.get_doc, R.ONE, aid)
    if not d:
        return {"status": "none"}
    return {k: d.get(k) for k in ("status", "job_id", "quadrants", "conclusion", "claims", "version") if d.get(k) is not None}


# ── 확정 필요 항목 ───────────────────────────────────────
def _fix_list(doc: dict[str, Any], v: dict[str, Any], status: str = "all") -> dict[str, Any]:
    items = v.get("fix_items") or {}
    pub = [fixes.public(i, doc) for i in items.values()]
    if status == "open":
        pub = [i for i in pub if i["status"] in ("warn", "wait")]
    elif status == "ok":
        pub = [i for i in pub if i["status"] == "ok"]
    order = {"market": 0, "customer": 1, "user": 2, "competitor": 3}
    pub.sort(key=lambda i: (order.get(i["tab"], 9), i["title"]))
    return {"items": pub, "counts": fixes.counts(items), "version": int(v.get("n") or 0)}


@router.get("/analyses/{aid}/fix-items", response_model=FixList, tags=["fix"])
async def list_fix_items(aid: str, status: str = Query("all", pattern="^(open|ok|all)$")) -> dict[str, Any]:
    doc = await load(aid)
    return _fix_list(doc, await _current(doc), status)


@router.patch("/analyses/{aid}/fix-items/{fix}", response_model=FixItem, tags=["fix"])
async def patch_fix_item(aid: str, fix: str, body: FixPatch) -> dict[str, Any]:
    """값 입력 → 숫자 · 비율 검증 → ok · 출처 user(AC-MI-45 · 46)."""
    doc = await load(aid)
    v = await _current(doc)
    it = (v.get("fix_items") or {}).get(fix)
    if it is None:
        raise service.not_found("확정 필요 항목", fix)
    value = fixes.validate_value(it, body.value)
    name = current_user().name

    def change(ver: dict[str, Any]) -> None:
        f = ver["fix_items"][fix]
        f.setdefault("history", []).append(fixes.history_entry(f, name))
        f.update(status="ok", value=value, value_source="user", reason_code="USER", sub_text=fixes.sub_text("USER", name=name),
                 confirmed_by=name, confirmed_at=now_iso(), note=body.note, applied=False)
        if body.unit is not None:
            f["unit"] = body.unit
        if f.get("claim_id") and f["claim_id"] in ver.get("claims", {}):
            cl = ver["claims"][f["claim_id"]]
            cl.setdefault("status_before_fix", cl.get("status"))
            cl["status"] = "confirmed"
            cl["label"] = verify.claim_label("confirmed")

    v = await versions.update_current(doc, change)
    return fixes.public(v["fix_items"][fix], doc)


@router.post("/analyses/{aid}/fix-items/{fix}/revert", response_model=FixItem, tags=["fix"])
async def revert_fix_item(aid: str, fix: str) -> dict[str, Any]:
    doc = await load(aid)
    v = await _current(doc)
    if fix not in (v.get("fix_items") or {}):
        raise service.not_found("확정 필요 항목", fix)

    def change(ver: dict[str, Any]) -> None:
        f = ver["fix_items"][fix]
        hist = f.get("history") or []
        prev = hist.pop() if hist else {"status": "warn", "value": None, "value_source": None, "sub_text": f.get("sub_text", "")}
        f["history"] = hist
        f.update(status=prev.get("status", "warn"), value=prev.get("value"), value_source=prev.get("value_source"),
                 sub_text=prev.get("sub_text") or f.get("sub_text", ""), reason_code=prev.get("reason_code") or f.get("reason_code"),
                 confirmed_by=None, confirmed_at=None, applied=False)
        for k in ("file_id", "file_name", "page"):
            f[k] = prev.get(k)
        cid = f.get("claim_id")
        if cid and cid in ver.get("claims", {}) and f["status"] != "ok":
            cl = ver["claims"][cid]
            if cl.get("status") == "confirmed":
                cl["status"] = cl.pop("status_before_fix", None) or "needs_check"
            C.recompute(ver, cid)

    v = await versions.update_current(doc, change)
    return fixes.public(v["fix_items"][fix], doc)


@router.post("/analyses/{aid}/fix-items/scan", status_code=202, response_model=JobAccepted, tags=["fix"])
async def scan_fix_items(aid: str, body: FixScanIn) -> dict[str, Any]:
    """사내 자료 올리기 → 열린 항목 값 찾기(잡 mi.fixscan). 해당 행은 wait · `올린 … 에서 값을 찾는 중`."""
    doc = await load(aid)
    v = await _current(doc)
    targets = body.fix_ids or [f["id"] for f in (v.get("fix_items") or {}).values() if f.get("status") == "warn"]
    job_id = await enqueue("mi.fixscan", {"analysis_id": aid, "file_id": body.file_id, "classification": body.classification,
                                          "fix_ids": targets}, doc, title="사내 자료에서 값 찾기")
    is_spec = False
    try:
        from winmate_common.platform import file_meta

        meta = await file_meta(body.file_id)
        fname = meta.get("name") or ""
        is_spec = "사양" in fname or "spec" in fname.lower()
    except Exception:  # noqa: BLE001
        fname = ""

    def change(ver: dict[str, Any]) -> None:
        for fid in targets:
            f = (ver.get("fix_items") or {}).get(fid)
            if not f or f.get("status") != "warn":
                continue
            f.setdefault("history", []).append(fixes.history_entry(f, current_user().name))
            code = "READING_SPEC" if is_spec else "READING"
            f.update(status="wait", job_id=job_id, file_id=body.file_id, file_name=fname, reason_code=code, sub_text=fixes.sub_text(code))

    await versions.update_current(doc, change)
    return {"job_id": job_id, "status": "queued"}


@router.post("/analyses/{aid}/fix-items/parse", response_model=FixParseOut, tags=["fix"])
async def parse_fix_text(aid: str, body: FixParseIn) -> dict[str, Any]:
    """`값 알려주기` — 말에서 항목 · 값 · 근거를 짝지어 제안(자동 확정하지 않음, AC-MI-49)."""
    doc = await load(aid)
    v = await _current(doc)
    open_items = [f for f in (v.get("fix_items") or {}).values() if f.get("status") != "ok"]
    if not open_items:
        return {"suggestions": []}
    try:
        res = await aix.llm("mi.fix_parse", prompts.fix_parse(body.text, open_items), prompts.FixParseOut, confidential=True)
    except (aix.LLMFailed, ApiError):
        return {"suggestions": []}
    valid = {f["id"] for f in open_items}
    out = []
    for s in res.suggestions:
        if s.fix_id in valid:
            out.append({"fix_id": s.fix_id, "value": s.value, "unit": s.unit, "basis": s.basis})
    # 제안 값을 항목에 붙여 둔다(수락 전 ok 아님)
    if out:
        def change(ver: dict[str, Any]) -> None:
            for s in out:
                ver["fix_items"][s["fix_id"]]["suggestion"] = s

        await versions.update_current(doc, change)
    return {"suggestions": out}


@router.post("/analyses/{aid}/fix-items/{fix}/question", response_model=CustomerQuestionOut, tags=["fix"])
async def customer_question(aid: str, fix: str) -> dict[str, Any]:
    """`고객 질문 복사` — 고객에게 물을 문장(LLM, 실패하면 템플릿)."""
    doc = await load(aid)
    v = await _current(doc)
    f = (v.get("fix_items") or {}).get(fix)
    if f is None:
        raise service.not_found("확정 필요 항목", fix)
    cust = doc.get("customer_name") or "고객사"
    try:
        res = await aix.llm("mi.customer_question", prompts.customer_question(f, cust), prompts.QuestionOut, confidential=True)
        q = res.question.strip()
    except (aix.LLMFailed, ApiError):
        q = ""
    if not q:
        q = f"{cust}의 {f.get('title', '이 값')}{rules.josa(f.get('title', '이 값'), '을', '를')} 알려 주실 수 있을까요?"
    return {"question": q}


@router.post("/analyses/{aid}/fix-items/apply", response_model=VersionOut, tags=["fix"])
async def apply_fix_items(aid: str, body: FixApplyIn) -> dict[str, Any]:
    """확정값을 주장 문장 · 표 칸 · 시트에 반영하고 출처를 그 자료로 바꾼 새 버전(kind=fix, AC-MI-45 · 50)."""
    doc = await load(aid)
    v = await _current(doc)
    name = current_user().name
    oks = [f for f in (v.get("fix_items") or {}).values() if f.get("status") == "ok" and f.get("value_source") in ("user", "file")]

    def mutate(ver: dict[str, Any]) -> None:
        from .graphs.common import refresh_numeric_fields

        for f in oks:
            fv = ver["fix_items"][f["id"]]
            val_txt = fixes.value_text(fv)
            cid = fv.get("claim_id")
            if cid and cid in ver.get("claims", {}):
                cl = ver["claims"][cid]
                if not fv.get("applied"):
                    cl["text"] = fixes.apply_to_text(cl.get("text", ""), fv)
                cl["numbers"] = [verify.num_to_dict(n) for n in verify.parse_numbers(cl["text"])]
                if fv.get("value_source") == "file" and fv.get("source_id"):
                    sid = fv["source_id"]
                    C.replace_citations(ver, cid, sid, fv.get("quote") or val_txt, page=fv.get("page"))
                else:
                    sid = C.user_source(ver, name=fv.get("confirmed_by") or name, value=val_txt, note=fv.get("note"))
                    C.replace_citations(ver, cid, sid, val_txt)
                cl["status"] = "confirmed"
                cl["label"] = verify.claim_label("confirmed")
                cl["unsupported"] = []
            if fv.get("cell_ref"):
                crt, col = fv["cell_ref"].split(":", 1)
                table = ((ver.get("document") or {}).get("competitor") or {}).get("table") or {}
                cell = ((table.get("cells") or {}).get(crt) or {}).get(col)
                if cell is not None and not fv.get("applied"):
                    cell["text"] = fixes.apply_to_text(cell.get("text", ""), fv) if ("[00]" in cell.get("text", "") or "[확인 필요]" in cell.get("text", "")) else val_txt
                    cell["placeholder"] = False
            fv["applied"] = True
        for f in (ver.get("fix_items") or {}).values():
            if f.get("status") != "ok":
                f["carry"] = bool(body.carry_remaining)
        refresh_numeric_fields(ver)

    n = await versions.save_new_version(doc, v, kind="fix", summary=f"확정값 반영 · {len(oks)}건", mutate=mutate)
    return {"version": n}


@router.post("/analyses/{aid}/fix-items/{fix}/cancel", response_model=FixItem, tags=["fix"])
async def cancel_fix_scan(aid: str, fix: str) -> dict[str, Any]:
    """파일 읽는 중 `취소` — 잡 취소 + 항목은 이전 상태(AC-MI-48)."""
    doc = await load(aid)
    v = await _current(doc)
    f = (v.get("fix_items") or {}).get(fix)
    if f is None:
        raise service.not_found("확정 필요 항목", fix)
    if f.get("job_id"):
        try:
            await jobs().cancel(f["job_id"])
        except Exception:  # noqa: BLE001
            pass
    job_id = f.get("job_id")

    def change(ver: dict[str, Any]) -> None:
        for it in (ver.get("fix_items") or {}).values():
            if it.get("status") == "wait" and (it.get("job_id") == job_id or it["id"] == fix):
                hist = it.get("history") or []
                prev = hist.pop() if hist else {}
                it["history"] = hist
                it.update(status=prev.get("status", "warn"), sub_text=prev.get("sub_text") or it.get("sub_text"),
                          reason_code=prev.get("reason_code") or it.get("reason_code"), job_id=None, file_id=prev.get("file_id"),
                          file_name=prev.get("file_name"))

    v = await versions.update_current(doc, change)
    return fixes.public(v["fix_items"][fix], doc)
