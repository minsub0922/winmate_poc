"""competitor API (/v1) — 이 파일과 api_results.py 의 엔드포인트가 contracts/competitor.json 이 된다(make contracts).

§6.1 입력 · 작업 · §6.2 찾기 · §6.3 후보 · §6.4 비교 기준 · §6.5 분석 실행 · §6.9 셸 추가 · 버전 · 라우팅 규칙.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from winmate_common import platform
from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.jobs import jobs

from . import aix, config, deps, kbx, reading, rqx, rules, service
from . import models as m
from . import store as R

log = logging.getLogger("winmate.competitor.api")
router = APIRouter(prefix="/v1")


@router.get("/info", response_model=m.ServiceInfo, tags=["meta"])
async def info() -> m.ServiceInfo:
    return m.ServiceInfo(service="competitor", title="경쟁사 분석 — 경쟁사 찾기 · 6개 비교 기준 · 신뢰도 · 익명화 · 30일 재확인", version="1.0.0")


@router.get("/routing-rules", response_model=m.RoutingRules, tags=["meta"])
async def routing_rules() -> dict[str, Any]:
    """CAR 보드 원문 + 규칙 임계값(서버 판단과 같은 설정 파일)."""
    rs = config.routing()
    modes = rs.get("modes") or {}
    return {
        "header": rs.get("header") or {},
        "legend": [{"key": k, "label": v["chip"], "mode": k} for k, v in modes.items()],
        "stages": [{"no": s["no"], "title": s["title"], "sub": s["sub"],
                    "rules": [{"signal": r[0], "decision": r[1], "mode": r[2], "mode_label": modes.get(r[2], {}).get("chip", "")} for r in s["rules"]]}
                   for s in rs.get("stages") or []],
        "ladder_title": (rs.get("ladder") or {}).get("title", ""), "ladder_sub": (rs.get("ladder") or {}).get("sub", ""),
        "ladder_example": (rs.get("ladder") or {}).get("example", ""), "ladder": (rs.get("ladder") or {}).get("rows") or [],
        "asks_title": (rs.get("asks") or {}).get("title", ""), "asks": (rs.get("asks") or {}).get("rows") or [],
        "asks_footer": (rs.get("asks") or {}).get("footer", ""),
        "thresholds": {k: float(v) for k, v in (rs.get("thresholds") or {}).items()},
        "ask_requires_ambiguous_industry": config.ask_requires_ambiguous(),
    }


@router.get("/capabilities", response_model=m.Capabilities, tags=["meta"])
async def capabilities() -> dict[str, Any]:
    """웹 검색 모드(sources · summary_only) — 화면이 `원문 열기` 같은 표시를 정할 때."""
    return aix.public_caps(await aix.capabilities())


# ── 입력 · 작업(§6.1) ────────────────────────────────────
@router.post("/parse", response_model=m.ParseOut, tags=["analyses"])
async def parse(body: m.ParseIn) -> dict[str, Any]:
    """CA1 · CA1R 칩 — 네 칸 읽기(≤ 3초 목표, 넘으면 KB 만으로)."""
    timeout = float(os.environ.get("CA_PARSE_TIMEOUT_S") or 8)
    kw = dict(text=body.text, file_ids=body.file_ids, requirements_id=body.requirements_id, rq_version=body.rq_version, extra_text=body.extra_text)
    try:
        res = await asyncio.wait_for(reading.read(**kw), timeout=timeout)
    except TimeoutError:
        res = await reading.read(**kw, budget=aix.Budget(websearch=0, fetch=0, llm=0))
        res["degraded"] = True
    slots = reading.author_note_free(res["slots"], res.get("author_note"))
    return {"slots": service.slots_view(slots), "found_count": rules.found_count(slots), "segment": service.segment_view(res.get("segment")),
            "rfp": res.get("rfp") or {}, "include_names": res.get("include_names") or [], "exclude_names": res.get("exclude_names") or [],
            "reading_files": bool(res.get("reading_files")), "degraded": bool(res.get("degraded"))}


@router.post("/analyses", status_code=201, response_model=m.Analysis, tags=["analyses"],
             responses={202: {"model": m.JobAccepted, "description": "auto_run — 찾기 → 분석을 사람 확인 없이 잇는다(§6.11 C2)"}})
async def create_analysis(body: m.AnalysisCreate) -> Any:
    rq_id = body.requirements_id or (body.rq_ref.rq_id if body.rq_ref else None)
    rq_ver = body.rq_version or (body.rq_ref.version if body.rq_ref else None)
    mode = body.input_mode
    if rq_id and mode == "free" and not body.text:
        mode = "requirements"
    if mode == "mi" and not body.mi_bundle:
        raise ApiError(422, "VALIDATION_FAILED", "MI 작업 묶음이 없어요", {"field": "mi_bundle"})
    cust = body.customer_name or (body.customer.get("name") if isinstance(body.customer, dict) else body.customer)
    text = body.text or ""
    if cust and not rq_id and cust not in text:
        text = f"{cust}\n{text}".strip()
    mi_ref = body.mi_ref.model_dump() if body.mi_ref else None
    if mode == "mi" and not mi_ref and body.mi_bundle and body.mi_bundle.get("analysis_id"):
        mi_ref = {"analysis_id": body.mi_bundle["analysis_id"], "version": body.mi_bundle.get("version")}
    doc = service.new_doc(input_mode=mode, text=text, extra_text=body.extra_text or "", file_ids=body.file_ids, requirements_id=rq_id,
                          rq_version=rq_ver, mi_ref=mi_ref, mi_bundle=body.mi_bundle if mode == "mi" else None, project_id=body.project_id,
                          purpose=body.purpose, auto_run=body.auto_run)
    if mode == "mi":
        doc["title"] = ""
    if body.auto_run and not (rq_id or text.strip() or body.file_ids or body.mi_bundle):
        raise ApiError(422, "EMPTY_INPUT", "고객 요구사항이나 설명이 있어야 찾을 수 있어요")
    doc = await R.call(R.put_analysis, doc)
    if rq_id:
        await rqx.register_link(rq_id, doc["id"], title="경쟁사 분석", route=service.route_for(doc), rq_version=int(rq_ver or 0), item_ids=[])
    if body.auto_run:
        job_id = await deps.start_find(doc, auto=True)
        return JSONResponse({"job_id": job_id, "status": "queued", "analysis_id": doc["id"]}, status_code=202)
    if mode == "mi":
        await deps.start_find(doc)
        doc = await deps.load(doc["id"])
    else:
        await service.register(doc)
    return service.analysis_view(doc)


def _status_bucket(st: str) -> str:
    return "done" if st in ("done", "upd") else "check"


@router.get("/analyses", response_model=m.AnalysisList, tags=["analyses"])
async def list_analyses(limit: int = Query(20, ge=1, le=100), cursor: str | None = None, status: str | None = Query(None, description="all|done|check"),
                        q: str | None = None, sort: str | None = Query(None, description="updated_desc(기본)|created_desc|title")) -> dict[str, Any]:
    user = current_user()
    docs = await R.call(R.list_analyses, user.id)
    out_docs = []
    for d in docs:
        if d.get("status") in ("finding", "ask", "analyzing") and d.get("current_job_id"):
            d = await deps.reconcile({**d, "id": d["id"]})
        out_docs.append(d)
    docs = out_docs
    if q:
        ql = q.strip().lower()

        def hit(d: dict[str, Any]) -> bool:
            seg = service.segment_view(d.get("segment"))
            hay = " ".join([service.display_title(d), ((d.get("slots") or {}).get("customer") or {}).get("value") or "", seg["name"], seg["full"],
                            ((d.get("slots") or {}).get("industry") or {}).get("value") or ""]).lower()
            return ql in hay

        docs = [d for d in docs if hit(d)]
    counts = {"all": len(docs), "done": sum(1 for d in docs if d.get("status") in ("done", "upd")),
              "check": sum(1 for d in docs if d.get("status") not in ("done", "upd")), "upd": sum(1 for d in docs if d.get("status") == "upd")}
    if status in ("done", "check"):
        docs = [d for d in docs if _status_bucket(d.get("status") or "draft") == status]
    if sort == "created_desc":
        docs.sort(key=lambda d: d.get("created_at") or "", reverse=True)
    elif sort == "title":
        docs.sort(key=lambda d: service.display_title(d))
    else:
        docs.sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    start = int(cursor) if cursor and cursor.isdigit() else 0
    page = docs[start:start + limit]
    now = datetime.now(timezone.utc)
    items = []
    for d in page:
        v = await R.call(R.get_version, d["id"], int(d.get("result_version") or 0)) if d.get("result_version") else None
        hofs = await R.call(R.list_docs, R.HOF, d["id"])
        items.append(service.list_item(d, v, hofs, now))
    upd = sorted([d for d in out_docs if d.get("status") == "upd"], key=lambda d: d.get("updated_at") or "", reverse=True)
    banner = None
    if upd:
        text = service.banner_text(upd[0]) + (f" 외 {len(upd) - 1}건" if len(upd) > 1 else "")
        banner = {"n": len(upd), "title": f"{len(upd)}건은 다시 분석을 권해요.", "text": text, "target_id": upd[0]["id"],
                  "competitor_ids": [c.get("competitor_id") for c in upd[0].get("changes") or [] if c.get("competitor_id")]}
    header = f"분석 {counts['all']}건 · 업데이트 필요 {counts['upd']}건 · 경쟁사는 실명 없이 A · B · C 로 표기해요"
    return {"items": items, "next_cursor": str(start + limit) if start + limit < len(docs) else None, "counts": counts, "banner": banner,
            "header": header}


@router.get("/analyses/{aid}", response_model=m.Analysis, tags=["analyses"])
async def get_analysis(aid: str) -> dict[str, Any]:
    doc = await deps.reconcile(await deps.load(aid))
    v = await deps.load_version(doc)
    return service.analysis_view(doc, version=v)


@router.patch("/analyses/{aid}", response_model=m.Analysis, tags=["analyses"])
async def patch_analysis(aid: str, body: m.AnalysisPatch) -> dict[str, Any]:
    doc = await deps.load(aid)
    ch = body.model_dump(exclude_unset=True)

    def upd(d: dict[str, Any]) -> None:
        for k in ("text", "extra_text", "file_ids", "requirements_id", "rq_version", "input_mode", "anonymize", "last_screen"):
            if k in ch and ch[k] is not None:
                d[k] = ch[k]
        if ch.get("title"):
            d["title"] = ch["title"].strip()[:40]
            d["title_auto"] = False
        if "requirements_id" in ch and ch["requirements_id"] and d.get("input_mode") == "free" and not d.get("text"):
            d["input_mode"] = "requirements"
        if d.get("status") in ("done", "upd") and any(k in ch for k in ("anonymize", "title")):
            d["edited_at"] = now_iso()

    doc = await R.call(R.update_analysis, aid, upd)
    if any(k in ch for k in ("text", "title", "last_screen", "anonymize", "requirements_id")):
        await service.register(doc)
    return service.analysis_view(doc, version=await deps.load_version(doc))


@router.delete("/analyses/{aid}", status_code=204, tags=["analyses"])
async def delete_analysis(aid: str) -> Response:
    doc = await deps.load(aid)
    await deps.cancel_job(doc.get("current_job_id"))
    try:
        await jobs().unschedule(f"sch_ca_recheck_{aid}")
    except Exception:  # noqa: BLE001
        pass
    await R.call(R.delete_analysis, aid)
    await platform.unregister_item(aid)
    return Response(status_code=204)


@router.get("/analyses/{aid}/progress", response_model=m.ProgressOut, tags=["analyses"])
async def get_progress(aid: str) -> dict[str, Any]:
    """CA1G · CA3 를 다시 열었을 때 그릴 진행 상태(잡 SSE 와 같은 내용)."""
    doc = await deps.reconcile(await deps.load(aid))
    j = await jobs().get(doc["current_job_id"]) if doc.get("current_job_id") else None
    return {"status": doc.get("status") or "draft", "job_id": doc.get("current_job_id"), "job_kind": doc.get("current_job_kind"),
            "job_status": j.status if j else None, "find": doc.get("find") or {}, "run": doc.get("run"), "ask": doc.get("ask")}


@router.get("/analyses/{aid}/versions", response_model=m.VersionList, tags=["analyses"])
async def list_versions(aid: str) -> dict[str, Any]:
    doc = await deps.load(aid)
    cur = int(doc.get("result_version") or 0)
    vs = await R.call(R.list_versions, aid)
    return {"items": [{"n": int(v.get("n") or 0), "kind": v.get("kind") or "", "created_at": v.get("created_at") or "", "summary": v.get("summary") or "",
                       "stopped": bool(v.get("stopped")), "current": int(v.get("n") or 0) == cur} for v in vs]}


@router.post("/analyses/{aid}/versions/{n}/restore", response_model=m.Analysis, tags=["analyses"])
async def restore_version(aid: str, n: int) -> dict[str, Any]:
    doc = await deps.load(aid)
    if await deps.job_active(doc.get("current_job_id")):
        raise ApiError(409, "RUN_IN_PROGRESS", "분석하는 중에는 되돌릴 수 없어요")
    old = await R.call(R.get_version, aid, n)
    if not old:
        raise ApiError(404, "NOT_FOUND", f"v{n} 결과를 찾을 수 없어요", {"version": n})
    new_n = max([int(x.get("n") or 0) for x in await R.call(R.list_versions, aid)] + [0]) + 1
    body = {**old, "kind": "restore", "created_at": now_iso(), "summary": f"v{n} 복원"}
    await R.call(R.put_version, aid, new_n, body)
    from .graphs.misc import _seed_work

    await R.call(R.update_work, aid, lambda w: _seed_work(w, body))

    def upd(d: dict[str, Any]) -> None:
        d["result_version"] = new_n
        d["status"] = "stopped" if body.get("stopped") else ("upd" if d.get("status") == "upd" else "done")

    doc = await R.call(R.update_analysis, aid, upd)
    await service.register(doc)
    return service.analysis_view(doc, version=body)


# ── 찾기(§6.2) ───────────────────────────────────────────
@router.post("/analyses/{aid}/find", status_code=202, response_model=m.JobAccepted, tags=["find"])
async def start_find(aid: str) -> dict[str, Any]:
    """ca.find — 이미 돌고 있으면 취소 후 새로. 사용자가 켜고 끈 · 추가한 후보는 그대로 두고 나머지만 다시 찾는다."""
    doc = await deps.load(aid)
    if doc.get("status") == "analyzing" and await deps.job_active(doc.get("current_job_id")):
        raise ApiError(409, "RUN_IN_PROGRESS", "분석하는 중이에요. 중지한 뒤 다시 찾아 주세요")
    if not ((doc.get("text") or "").strip() or doc.get("file_ids") or doc.get("requirements_id") or doc.get("mi_bundle")):
        raise ApiError(422, "EMPTY_INPUT", "고객 · 사업 설명을 적거나 정의서 · 파일을 골라 주세요")
    job_id = await deps.start_find(doc)
    return {"job_id": job_id, "status": "queued", "analysis_id": aid}


# ── 후보(§6.3) ───────────────────────────────────────────
def _candidates_out(doc: dict[str, Any]) -> dict[str, Any]:
    live = service.ordered(service.live_competitors(doc))
    cnt = service.candidate_counts(live)
    k = rules.found_count(doc.get("slots") or {})
    finding = doc.get("status") in ("finding", "ask")
    if live:
        desc = f"입력에서 읽은 {k}가지로 후보 {len(live)}곳을 찾았어요. 추천 {cnt['rec']}곳은 켜 두었고, 빼거나 더할 수 있어요."
    else:
        desc = "아직 후보가 없어요. 경쟁사를 직접 추가하거나 다시 찾아 주세요."
    return {"items": [service.competitor_view(c) for c in live], "counts": cnt, "read_count": k, "total": len(live), "page_size": config.page_size(),
            "finding": finding, "chips": service.chips_view(doc), "slots": service.slots_view(doc.get("slots") or {}),
            "header": {"kicker": "확인 1 / 1", "title": "이 경쟁사들로 분석할까요?", "desc": desc},
            "job_id": doc.get("current_job_id") if finding else None}


@router.get("/analyses/{aid}/candidates", response_model=m.CandidatesOut, tags=["candidates"])
async def get_candidates(aid: str) -> dict[str, Any]:
    doc = await deps.reconcile(await deps.load(aid))
    return _candidates_out(doc)


@router.patch("/analyses/{aid}/candidates/{cmp}", response_model=m.CompetitorView, tags=["candidates"])
async def patch_candidate(aid: str, cmp: str, body: m.CandidatePatch) -> dict[str, Any]:
    """켜기 · 끄기 → pinned=true(다시 찾기 · 다시 분석해도 유지)."""
    await deps.load(aid)
    found: dict[str, Any] = {}

    def upd(d: dict[str, Any]) -> None:
        for c in d.get("competitors") or []:
            if c["id"] == cmp and not c.get("removed"):
                c["on"] = bool(body.on)
                c["pinned"] = True
                found.update(c)
        if found and d.get("status") in ("done", "upd", "stopped"):
            d["edited_at"] = now_iso()

    await R.call(R.update_analysis, aid, upd)
    if not found:
        raise service.not_found("경쟁사", cmp)
    return service.competitor_view(found)


@router.post("/analyses/{aid}/candidates", status_code=202, response_model=m.CandidateAddOut, tags=["candidates"])
async def add_candidate(aid: str, body: m.CandidateAdd) -> dict[str, Any]:
    """경쟁사 직접 추가 → 켜짐 · 고정 · 다음 글자 · 배지 `직접 추가`. 같은 회사(별칭 포함)면 409 DUPLICATE_COMPETITOR."""
    doc = await deps.load(aid)
    name = rules.clean_name(body.name)
    if not name:
        raise ApiError(422, "VALIDATION_FAILED", "회사 이름을 적어 주세요")
    if rules.is_self_entity(name):
        raise ApiError(422, "SELF_ENTITY", "삼성 · 계열사는 경쟁사로 넣을 수 없어요")
    for c in service.live_competitors(doc):
        if rules.same_company(name, [c.get("real_name") or "", *(c.get("aliases") or [])]):
            raise ApiError(409, "DUPLICATE_COMPETITOR", "이미 있는 경쟁사예요", {"competitor_id": c["id"], "letter": c.get("letter")})
    from .graphs.find import free_letters

    cid = R.nid("cmp")

    def upd(d: dict[str, Any]) -> None:
        comps = d.setdefault("competitors", [])
        removed = next((c for c in comps if c.get("removed") and rules.same_company(name, [c.get("real_name") or "", *(c.get("aliases") or [])])), None)
        used = {c["letter"] for c in comps if c.get("letter")}
        letter = removed["letter"] if removed else free_letters(used, 1)[0]
        if removed:
            comps.remove(removed)
        comps.append({"id": cid, "letter": letter, "real_name": name, "aliases": [], "kind_label": "", "why": "", "signals": {}, "chips": [],
                      "confidence": None, "status": "user", "on": True, "pinned": True, "removed": False, "origin": "user",
                      "rank": len(comps), "add_state": "pending", "found_at": now_iso()})
        if d.get("status") in ("draft", "failed"):
            d["status"] = "confirming"
            d["last_screen"] = "candidates"
        if d.get("status") in ("done", "upd", "stopped"):
            d["edited_at"] = now_iso()

    doc = await R.call(R.update_analysis, aid, upd)
    job_id = await deps.enqueue("ca.candidate_add", {"competitor_id": cid, "name": name}, doc)
    await service.register(doc)
    return {"job_id": job_id, "competitor_id": cid, "status": "queued"}


# ── 비교 기준(§6.4) ──────────────────────────────────────
def _criteria_out(doc: dict[str, Any]) -> dict[str, Any]:
    items = [service.criterion_view(c) for c in service.criteria_sorted(doc)]
    summ = rules.criteria_summary(service.criteria_sorted(doc))
    return {"items": items, "summary": summ, "mode": doc.get("criteria_mode") or "auto", "suggestions": doc.get("criteria_suggestions") or [],
            "on": sum(1 for c in items if c["enabled"]), "total": len(items), "summary_text": service.criteria_summary_text(summ)}


@router.get("/analyses/{aid}/criteria", response_model=m.CriteriaOut, tags=["criteria"])
async def get_criteria(aid: str) -> dict[str, Any]:
    return _criteria_out(await deps.load(aid))


@router.put("/analyses/{aid}/criteria", response_model=m.CriteriaPutOut, tags=["criteria"],
            responses={202: {"model": m.CriteriaPutOut, "description": "분석 중 — 지금 잡을 끝내고 모은 사실을 재사용해 판정부터 다시"}})
async def put_criteria(aid: str, body: m.CriteriaPut) -> Any:
    """기준 바꾸기(CA3C) — 모두 pinned, 모드 `고정`. 분석 중이면 202(사실 재사용 · 판정부터), 아니면 200(웹이 runs{rejudge})."""
    doc = await deps.load(aid)
    if not body.items:
        raise ApiError(422, "VALIDATION_FAILED", "비교 기준이 하나는 있어야 해요")
    if not any(i.enabled for i in body.items):
        raise ApiError(422, "NO_CRITERIA", "켜진 비교 기준이 없어요")
    old = {c["id"]: c for c in doc.get("criteria") or []}
    items = []
    for i, it in enumerate(sorted(body.items, key=lambda x: x.order)):
        prev = old.get(it.id or "")
        items.append({"id": prev["id"] if prev else R.nid("crt"), "name": it.name.strip()[:20], "source": prev.get("source") if prev else it.source,
                      "source_count": prev.get("source_count") if prev else it.source_count, "importance": int(it.importance), "order": i,
                      "enabled": bool(it.enabled), "pinned": True, "requirement_ref": (prev or {}).get("requirement_ref")})

    def upd(d: dict[str, Any]) -> None:
        d["criteria"] = items
        d["criteria_mode"] = "pin"
        if d.get("status") in ("done", "upd", "stopped"):
            d["edited_at"] = now_iso()

    doc = await R.call(R.update_analysis, aid, upd)
    if doc.get("status") == "analyzing" and await deps.job_active(doc.get("current_job_id")):
        job_id = await deps.start_run(doc, "rejudge", supersede=True)
        doc = await deps.load(aid)
        return JSONResponse({**_criteria_out(doc), "job_id": job_id}, status_code=202)
    return {**_criteria_out(doc), "job_id": None}


# ── 분석 실행(§6.5) ──────────────────────────────────────
@router.post("/analyses/{aid}/runs", status_code=202, response_model=m.JobAccepted, tags=["runs"])
async def start_run(aid: str, body: m.RunIn) -> dict[str, Any]:
    """ca.analyze — full · changed_only · rejudge · resume. 실행 중 409 RUN_IN_PROGRESS · 켜진 경쟁사 0 → 422 NO_COMPETITORS."""
    doc = await deps.reconcile(await deps.load(aid))
    if doc.get("status") in ("finding", "ask") and await deps.job_active(doc.get("current_job_id")):
        raise ApiError(409, "RUN_IN_PROGRESS", "아직 경쟁사를 찾고 있어요")
    ids = body.competitor_ids
    if body.mode == "changed_only" and not ids:
        ids = [c.get("competitor_id") for c in doc.get("changes") or [] if c.get("competitor_id")]
    job_id = await deps.start_run(doc, body.mode, ids)
    return {"job_id": job_id, "status": "queued", "analysis_id": aid}


# ── 셸 추가(§6.9) ────────────────────────────────────────
@router.post("/analyses/{aid}/additions", response_model=m.AdditionsOut, tags=["analyses"])
async def add_refs(aid: str, body: m.AdditionsIn) -> dict[str, Any]:
    """TopBar `현재 작업에 추가` — 제품 · 솔루션 = 비교 `삼성` 쪽 제품, 사례 = 사내 사례 DB 근거. 다음 실행에서 판정부터 다시. image 는 받지 않는다."""
    if body.kind == "image":
        raise ApiError(422, "UNSUPPORTED_KIND", "이미지는 경쟁사 분석에 추가할 수 없어요")
    await deps.load(aid)
    added: list[str] = []
    entries: list[dict[str, Any]] = []
    for ref in body.ids:
        parts = ref.split(":")
        kind, ident = (parts[1], parts[2]) if len(parts) >= 3 and parts[0] == "kb" else (body.kind, parts[-1])
        if body.kind == "product":
            if kind == "model" or ident.startswith("mdl_") or ident.isupper():
                code = ident.removeprefix("mdl_")
                mdl = await kbx.model(code)
                entries.append({"kind": "model", "ref": ref, "model_code": (mdl or {}).get("model_code") or code,
                                "name": (mdl or {}).get("display_name") or code, "family_id": (mdl or {}).get("family_id")})
            else:
                mdl = await kbx.model(ident)
                if mdl and mdl.get("model_code"):
                    entries.append({"kind": "family", "ref": ref, "model_code": mdl["model_code"], "name": mdl.get("display_name") or mdl["model_code"],
                                    "family_id": ident})
                else:
                    continue
        elif body.kind == "solution":
            sol = await kbx.solution(ident)
            entries.append({"kind": "solution", "ref": ref, "solution_id": ident.removeprefix("sol_"), "name": (sol or {}).get("name") or ident})
        else:
            entries.append({"kind": "case", "ref": ref, "case_id": ident})
        added.append(ref)

    def upd(d: dict[str, Any]) -> None:
        have = {p.get("ref") for p in d.get("samsung_products") or []} | {p.get("ref") for p in d.get("kb_cases") or []}
        for e in entries:
            if e["ref"] in have:
                continue
            (d.setdefault("kb_cases", []) if e["kind"] == "case" else d.setdefault("samsung_products", [])).append(e)
        if d.get("result_version"):
            d["needs_rejudge"] = True

    await R.call(R.update_analysis, aid, upd)
    return {"added": added}
