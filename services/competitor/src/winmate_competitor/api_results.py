"""competitor API (/v1) — 결과 · 상세 · 근거(§6.6) · 넘김 · 묶음 · 내보내기(§6.7 · §6.10) · ProposalHandoff(§6.11) · 재확인(§6.8)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, Response

from winmate_common.errors import ApiError
from winmate_common.ids import now_iso

from . import bundle, config, deps, results, service
from . import models as m
from . import store as R

log = logging.getLogger("winmate.competitor.api")
router = APIRouter(prefix="/v1")


async def _version(doc: dict[str, Any], version: int | None, *, allow_provisional: bool = True) -> dict[str, Any]:
    if version:
        v = await R.call(R.get_version, doc["id"], version)
        if not v:
            raise ApiError(404, "NOT_FOUND", f"v{version} 결과를 찾을 수 없어요", {"version": version})
        return v
    if allow_provisional and doc.get("status") == "analyzing":
        work = await R.call(R.get_work, doc["id"])
        return results.provisional(doc, work)
    v = await deps.load_version(doc)
    if not v:
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요", {"id": doc["id"]})
    return v


# ── 결과 · 상세(§6.6) ────────────────────────────────────
@router.get("/analyses/{aid}/result", response_model=m.ResultOut, tags=["results"])
async def get_result(aid: str, view: str = Query("overview", pattern="^(overview|table|strengths)$"), version: int | None = None) -> dict[str, Any]:
    doc = await deps.reconcile(await deps.load(aid))
    v = await _version(doc, version)
    return results.result_view(doc, v, view=view)


@router.get("/analyses/{aid}/competitors/{cmp}", response_model=m.CompetitorDetail, tags=["results"])
async def get_competitor(aid: str, cmp: str, version: int | None = None) -> dict[str, Any]:
    doc = await deps.load(aid)
    v = await _version(doc, version)
    if cmp not in (v.get("competitor_ids") or []):
        raise ApiError(404, "NOT_FOUND", "이 경쟁사는 아직 분석 결과가 없어요", {"competitor_id": cmp})
    return results.detail_view(doc, v, cmp)


@router.post("/analyses/{aid}/competitors/{cmp}/research", status_code=202, response_model=m.JobAccepted, tags=["results"])
async def research(aid: str, cmp: str, body: m.ResearchIn) -> dict[str, Any]:
    """이 경쟁사 더 찾기(ca.research) — 그 경쟁사 사실만 다시 모으고 판정 · 강점 · 주의할 점 다시 → 새 버전."""
    doc = await deps.load(aid)
    if not doc.get("result_version"):
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요")
    if await deps.job_active(doc.get("current_job_id")):
        raise ApiError(409, "RUN_IN_PROGRESS", "분석하는 중이에요")
    if (doc.get("research") or {}).get("job_id") and await deps.job_active(doc["research"]["job_id"]):
        raise ApiError(409, "RUN_IN_PROGRESS", "이미 더 찾고 있어요")
    if not any(c["id"] == cmp for c in doc.get("competitors") or []):
        raise service.not_found("경쟁사", cmp)
    job_id = deps.new_job_id()
    await R.call(R.update_analysis, aid, lambda d: d.update(research={"competitor_id": cmp, "job_id": job_id, "started_at": now_iso()}))
    try:
        await deps.enqueue("ca.research", {"competitor_id": cmp, "facts": list(body.facts or [])}, doc, job_id=job_id)
    except Exception:
        await R.call(R.update_analysis, aid, lambda d: d.update(research=None) if (d.get("research") or {}).get("job_id") == job_id else None)
        raise
    return {"job_id": job_id, "status": "queued", "analysis_id": aid}


# ── 주장 · 출처(§6.6 · 03-mi.md §6.5) ────────────────────
@router.get("/analyses/{aid}/claims", response_model=m.ClaimList, tags=["evidence"])
async def list_claims(aid: str, competitor: str | None = None, fact: str | None = None, status: str | None = None,
                      version: int | None = None) -> dict[str, Any]:
    doc = await deps.load(aid)
    return results.claims_view(doc, await _version(doc, version), competitor=competitor, fact=fact, status=status)


@router.get("/analyses/{aid}/claims/{clm}", response_model=m.ClaimDetail, tags=["evidence"])
async def get_claim(aid: str, clm: str, version: int | None = None) -> dict[str, Any]:
    doc = await deps.load(aid)
    out = results.claim_detail(doc, await _version(doc, version), clm)
    if out is None:
        raise service.not_found("주장", clm)
    return out


@router.get("/analyses/{aid}/sources", response_model=m.SourceList, tags=["evidence"])
async def list_sources(aid: str, competitor: str | None = None, kind: str | None = None, version: int | None = None) -> dict[str, Any]:
    doc = await deps.load(aid)
    v = await _version(doc, version)
    items = []
    for sid, s in (v.get("sources") or {}).items():
        if competitor and competitor not in (s.get("competitor_ids") or []):
            continue
        if kind and s.get("kind") != kind:
            continue
        items.append(results.source_out({**s, "id": sid}))
    return {"items": items}


@router.get("/analyses/{aid}/sources/{src}/snapshot", response_model=m.SnapshotOut, tags=["evidence"])
async def source_snapshot(aid: str, src: str) -> dict[str, Any]:
    await deps.load(aid)
    text, pages = R.load_snapshot(src)
    if text is None:
        raise service.not_found("수집본", src)
    return {"text": text, "pages": pages}


@router.post("/analyses/{aid}/sources", status_code=202, response_model=m.SourceAddOut, tags=["evidence"])
async def add_source(aid: str, body: m.SourceAddIn) -> dict[str, Any]:
    """출처 직접 추가 · URL 또는 사내 문서(ca.source_add) → 수집 · 대조 후 카드로 나타난다."""
    doc = await deps.load(aid)
    if not (body.url or body.file_id):
        raise ApiError(422, "VALIDATION_FAILED", "URL 이나 파일을 넣어 주세요")
    if not doc.get("result_version"):
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요")
    job_id = await deps.enqueue("ca.source_add", body.model_dump(), doc)
    return {"job_id": job_id, "source_id": None, "status": "queued"}


@router.delete("/analyses/{aid}/claims/{clm}/sources/{src}", response_model=m.ClaimItem, tags=["evidence"])
async def remove_source(aid: str, clm: str, src: str) -> dict[str, Any]:
    """이 출처 빼기 → 주장 상태 다시(마지막 출처를 빼면 그 사실은 `[확인 필요]`)."""
    doc = await deps.load(aid)
    n = int(doc.get("result_version") or 0)
    if not n:
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요")
    out: dict[str, Any] = {}

    def upd(v: dict[str, Any]) -> None:
        r = results.remove_citation(v, clm, src)
        if r:
            out.update(r)

    v = await R.call(R.update_version, aid, n, upd)
    if not out:
        raise service.not_found("인용", f"{clm}/{src}")
    nums = results.source_numbers(v, results._claim_order(v, list(v.get("competitor_ids") or [])))
    return results.claim_item(v, {**out, "id": clm}, nums)


# ── 넘김 · 묶음 · 내보내기(§6.7 · §6.10) ─────────────────
def _hof_view(h: dict[str, Any]) -> dict[str, Any]:
    return {"id": h["id"], "analysis_id": h.get("analysis_id") or "", "version": int(h.get("version") or 0), "target": h.get("target") or "mi",
            "target_id": h.get("target_id"), "target_title": h.get("target_title"), "status": h.get("status") or "prepared",
            "confirmations": h.get("confirmations") or {}, "anonymization_map": h.get("anonymization_map") or {},
            "served_named_at": h.get("served_named_at") or [], "created_at": h.get("created_at") or "", "updated_at": h.get("updated_at") or ""}


@router.post("/analyses/{aid}/handoffs", response_model=m.HandoffOut, tags=["handoffs"])
async def create_handoff(aid: str, body: m.HandoffIn) -> dict[str, Any]:
    """넘김 기록. 고객 제출물(제안서)인데 익명이 꺼져 있고 실명 확인이 없으면 409 ASK_REQUIRED(묻기 2)."""
    doc = await deps.load(aid)
    v = await deps.load_version(doc)
    if not v and body.target != "storyboard":
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요")
    named = False
    if body.target == "proposal_why":
        if not doc.get("anonymize", True):
            if body.confirm is None or body.confirm.real_names is None:
                raise ApiError(409, "ASK_REQUIRED", "경쟁사 실명을 고객 제출물에 넣을까요?",
                               {"kind": "real_names", "asks": [{"kind": "real_names", "default": "anonymize",
                                          "title": "경쟁사 실명을 고객 제출물에 넣을까요?",
                                          "body": "익명 표기가 꺼져 있어요. 이 제안서에 경쟁사 실명이 그대로 들어가요.",
                                          "options": ["익명으로 보내기", "실명으로 보내기"]}]})
            named = bool(body.confirm.real_names)
    elif body.target in ("mi", "report"):
        named = True
    comps = bundle.included(doc, v) if v else service.on_competitors(doc)
    amap = {} if named else bundle.anon_map(comps)
    out = {"handoff_id": None, "target": body.target, "status": "prepared", "named": named, "anonymization_map": amap,
           "letters": [amap[c["id"]].removeprefix("경쟁사 ") for c in comps if c["id"] in amap] if amap else [c.get("letter") for c in comps]}
    if body.dry_run:
        return out
    hof = R.nid("hof")
    await R.call(R.put_doc, R.HOF, hof, {"analysis_id": aid, "version": int(doc.get("result_version") or 0), "target": body.target,
                                         "target_id": body.target_id, "target_title": body.target_title, "status": "prepared",
                                         "confirmations": {"real_names": named} if body.target == "proposal_why" else {}, "anonymization_map": amap,
                                         "served_named_at": [], "created_at": now_iso()})
    out["handoff_id"] = hof
    return out


@router.patch("/analyses/{aid}/handoffs/{hof}", response_model=m.HandoffView, tags=["handoffs"])
async def patch_handoff(aid: str, hof: str, body: m.HandoffPatch) -> dict[str, Any]:
    await deps.load(aid)
    h = await R.call(R.get_doc, R.HOF, hof)
    if not h or h.get("analysis_id") != aid:
        raise service.not_found("넘김 기록", hof)

    def upd(x: dict[str, Any]) -> None:
        x["status"] = body.status
        if body.target_id:
            x["target_id"] = body.target_id
        if body.target_title:
            x["target_title"] = body.target_title
        x["updated_at"] = now_iso()

    h = await R.call(R.update_doc, R.HOF, hof, upd)
    doc = await deps.load(aid)
    await service.register(doc)
    return _hof_view(h)


@router.get("/analyses/{aid}/handoffs", response_model=m.HandoffList, tags=["handoffs"])
async def list_handoffs(aid: str) -> dict[str, Any]:
    await deps.load(aid)
    return {"items": [_hof_view(h) for h in await R.call(R.list_docs, R.HOF, aid)]}


async def _handoff(aid: str, hof: str | None) -> dict[str, Any] | None:
    if not hof:
        return None
    h = await R.call(R.get_doc, R.HOF, hof)
    if not h or h.get("analysis_id") != aid:
        raise service.not_found("넘김 기록", hof)
    return h


@router.get("/analyses/{aid}/bundle", response_model=m.Bundle, tags=["handoffs"])
async def get_bundle(aid: str, target: str = Query(..., pattern="^(mi|proposal_why|storyboard)$"), handoff_id: str | None = None) -> dict[str, Any]:
    """넘김 묶음 — mi 는 실명 포함(MI 가 자기 내보내기에서 익명 처리), proposal_why · storyboard 는 익명(기록에 실명 확인이 있을 때만 실명)."""
    doc = await deps.load(aid)
    h = await _handoff(aid, handoff_id)
    v = await deps.load_version(doc)
    if target == "storyboard":
        return bundle.bundle_storyboard(doc, v, handoff_id=handoff_id)
    if not v:
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요")
    if target == "mi":
        return bundle.bundle_mi(doc, v, handoff_id=handoff_id)
    named = bool(h and (h.get("confirmations") or {}).get("real_names") and not doc.get("anonymize", True))
    out, amap = bundle.bundle_proposal(doc, v, handoff_id=handoff_id, named=named)
    if h and not named and not h.get("anonymization_map"):
        await R.call(R.update_doc, R.HOF, h["id"], lambda x: x.update(anonymization_map=amap))
    return out


@router.get("/analyses/{aid}/proposal-handoff", response_model=m.ProposalHandoff, tags=["handoffs"])
async def proposal_handoff(aid: str, type: str = Query("standard", pattern="^(standard|quickwin|solution)$"),  # noqa: A002
                           section: str = Query("why"), handoff_id: str | None = None, named: bool = False) -> dict[str, Any]:
    """ProposalHandoff v1(§6.11 · 10-proposal §8.8 C1) — Why Samsung 경쟁 비교(CM) · 삼성 강점(ST). 기본 익명.
    named=true 는 넘김 기록에 실명 확인(CA5 묻기 2 `실명으로 보내기`)이 있을 때만 — 없으면 409 ASK_REQUIRED, 있으면 응답마다 served_named_at 기록."""
    doc = await deps.load(aid)
    h = await _handoff(aid, handoff_id)
    if named and not (h and (h.get("confirmations") or {}).get("real_names")):
        raise ApiError(409, "ASK_REQUIRED", "경쟁사 실명을 고객 제출물에 넣을까요?", {"kind": "real_names", "asks": [{"kind": "real_names", "default": "anonymize"}]})
    v = await deps.load_version(doc)
    if not v:
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요")
    out, amap = bundle.proposal_handoff(doc, v, ptype=type, section=section, handoff_id=handoff_id, named=named)
    if h:
        def upd(x: dict[str, Any]) -> None:
            if named:
                x.setdefault("served_named_at", []).append(now_iso())
            elif not x.get("anonymization_map"):
                x["anonymization_map"] = amap

        await R.call(R.update_doc, R.HOF, h["id"], upd)
    return out


@router.post("/analyses/{aid}/exports", status_code=202, response_model=m.JobAccepted, tags=["handoffs"])
async def create_export(aid: str, body: m.ExportIn) -> dict[str, Any]:
    """리포트 저장(ca.export) — `internal` = 실명 · 표지 `사내용 · 고객 제출 금지`, `customer` = 익명. 끝나면 result.file_id."""
    doc = await deps.load(aid)
    if not doc.get("result_version"):
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요")
    job_id = await deps.enqueue("ca.export", {"format": body.format, "audience": body.audience}, doc)
    return {"job_id": job_id, "status": "queued", "analysis_id": aid}


# ── 재확인(§6.8) ─────────────────────────────────────────
@router.post("/analyses/{aid}/recheck", status_code=202, response_model=m.JobAccepted, tags=["recheck"])
async def recheck(aid: str) -> dict[str, Any]:
    doc = await deps.load(aid)
    if not doc.get("result_version"):
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요")
    job_id = await deps.enqueue("ca.recheck", {}, doc)
    return {"job_id": job_id, "status": "queued", "analysis_id": aid}


@router.get("/analyses/{aid}/changes", response_model=m.ChangesOut, tags=["recheck"])
async def changes(aid: str) -> dict[str, Any]:
    doc = await deps.load(aid)
    items = list(doc.get("changes") or [])
    summary = ""
    if items:
        summary = service.banner_text(doc)
    return {"items": [{**c, "verification": c.get("verification") or "needs_check"} for c in items], "summary": summary,
            "checked_at": (doc.get("recheck") or {}).get("checked_at")}


def _unused() -> Response:  # pragma: no cover — 라우터 모듈 자리 표시
    return Response(status_code=204)


__all__ = ["router", "config"]
