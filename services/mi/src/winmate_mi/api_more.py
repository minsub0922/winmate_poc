"""부분 재분석 · 시트 구성 · 넘김 · 묶음 · 내보내기 · 공유 · 재확인 · 가져오기(03-mi.md §6.7~§6.10 · §6.12 · §6.14)."""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from winmate_common.client import ServiceClient
from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso

from . import aix, anonymize, bundle as B, config, layout, prompts, rules, service, versions, views
from . import store as R
from .deps import enqueue, job_active, load, load_version
from .models import (
    Bundle, CaImportAccepted, CaImportIn, CandidatesView, Change, ChangePatch, ChangesView, EvidenceSnapshot, ExportIn, ExportView, FactsLookupIn,
    FactsLookupOut, Handoff, HandoffIn, HandoffOut, HandoffPatch, JobAccepted, LayoutIn, ProposalHandoff, RevisionAccepted, RevisionIn,
    ResultView, RevisionView, RoundIn, ShareOut, SlidePatch, SlidePlan, SlideRequestIn, SlideRequestOut, SlidesView, TableText, VersionOut,
)

router = APIRouter(prefix="/v1")

CHIP_LABEL = {"row_add": "행 추가", "value_edit": "값 수정", "strength_edit": "강점 수정", "row_remove": "행 삭제", "text_edit": "문장 수정", "source_add": "출처 추가"}


# ── 부분 재분석 ──────────────────────────────────────────
async def create_revision(doc: dict[str, Any], scope: dict[str, Any], instruction: str, *, origin: str = "user",
                          extra: dict[str, Any] | None = None) -> tuple[str, str]:
    base = int(doc.get("result_version") or 0)
    if not base:
        raise ApiError(422, "VALIDATION_FAILED", "분석 결과가 있어야 다시 분석할 수 있어요")
    rev_id = R.nid("rev")
    rev = {"analysis_id": doc["id"], "base_version": base, "scope": scope, "rounds": [{"instruction": instruction, "scope": scope, "at": now_iso()}],
           "origin": origin, "status": "running", "job_id": None, "duration_s": 0, "sources_added": 0, "applied_version": None,
           "changes": [], "created_at": now_iso(), **(extra or {})}
    await R.call(R.put_doc, R.REV, rev_id, rev)
    job_id = await enqueue("mi.revise", {"analysis_id": doc["id"], "revision_id": rev_id}, doc, title="부분 재분석")
    await R.call(R.update_doc, R.REV, rev_id, lambda r: r.update(job_id=job_id))
    return rev_id, job_id


async def _rev(doc: dict[str, Any], rev: str) -> dict[str, Any]:
    r = await R.call(R.get_doc, R.REV, rev)
    if r is None or r.get("analysis_id") != doc["id"]:
        raise service.not_found("재분석 안", rev)
    return r


def _scope_label(scope: dict[str, Any]) -> str:
    k = scope.get("kind")
    if k == "area":
        return f"{rules.AREA_TAB.get(scope.get('area') or '', '')} 탭".replace("경쟁사 → 삼성 강점 탭", "경쟁사 탭")
    if k == "rows":
        return f"선택한 행 {len(scope.get('ids') or [])}"
    if k == "strengths":
        return "강점 문장만"
    if k == "claims":
        return "선택한 주장"
    return ""


def _agent_text(rev: dict[str, Any], analysis: dict[str, Any]) -> str:
    sc = rev.get("scope") or {}
    k = sc.get("kind")
    if k == "area":
        tab = _scope_label(sc).removesuffix(" 탭")
        others = len(service.areas_of(analysis)) - 1
        return f"{tab} 탭만 다시 분석했습니다. 다른 {max(0, others)}개 탭은 그대로이고, 바뀐 곳은 파란 표시로 남겨 두었어요."
    if k == "rows":
        return f"선택한 행 {len(sc.get('ids') or [])}개만 다시 분석했습니다. 바뀐 곳은 파란 표시로 남겨 두었어요."
    if k == "strengths":
        return "강점 문장만 다시 썼습니다. 바뀐 곳은 파란 표시로 남겨 두었어요."
    return "이 주장의 출처를 다시 찾았습니다."


async def revision_view(doc: dict[str, Any], rev: dict[str, Any]) -> dict[str, Any]:
    from .graphs.revise import apply_changes

    changes = rev.get("changes") or []
    live = [c for c in changes if not c.get("reverted")]
    chips: dict[str, int] = {}
    for c in live:
        chips[c["kind"]] = chips.get(c["kind"], 0) + 1
    preview = None
    base = await R.call(R.get_version, doc["id"], int(rev.get("base_version") or 0))
    footer = ""
    if base is not None and rev.get("status") in ("proposed", "applied"):
        pv = apply_changes(doc, base, rev, only_live=True)
        preview = views.result_view(doc, {**pv, "n": int(rev.get("base_version") or 0)})
        area = (rev.get("scope") or {}).get("area") or "competitor"
        ft = (preview.get("footers") or {}).get(area) or {}
        by = ft.get("by_kind") or {}
        parts = [f"출처 {ft.get('sources', 0)}건 (+{rev.get('sources_added', 0)})"]
        if by.get("kb_official"):
            parts.append(f"사내 스펙 {by['kb_official']}")
        if by.get("public"):
            parts.append(f"공개 자료 {by['public']}")
        if by.get("kb_case"):
            parts.append(f"사내 사례 DB {by['kb_case']}")
        for miss in rev.get("missing_sources") or []:
            parts.append(f"{miss}{rules.josa(miss, '은', '는')} 출처 없음")
        footer = " · ".join(parts)
    out_changes = [{**c, "revision_id": rev["id"], "label": CHIP_LABEL.get(c["kind"], "")} for c in changes]
    return {"revision": {k: rev.get(k) for k in ("id", "analysis_id", "base_version", "scope", "rounds", "origin", "status", "job_id",
                                                  "duration_s", "sources_added", "applied_version", "error", "created_at")},
            "changes": out_changes, "chips": chips, "changed_count": len(live), "sources_added": int(rev.get("sources_added") or 0),
            "duration_s": int(rev.get("duration_s") or 0), "quick_suggestions": rev.get("quick_suggestions") or ["더 간결하게"],
            "footer": anonymize.scrub(footer, doc.get("competitors") or [], {c["id"]: anonymize.workspace_label(c) for c in doc.get("competitors") or []}),
            "agent_text": _agent_text(rev, doc), "scope_label": _scope_label(rev.get("scope") or {}), "preview": preview,
            "eta_s": 20 if (rev.get("scope") or {}).get("kind") != "area" else 40}


@router.post("/analyses/{aid}/revisions", status_code=202, response_model=RevisionAccepted, tags=["revisions"])
async def post_revision(aid: str, body: RevisionIn) -> dict[str, Any]:
    """영역 · 행 · 강점 · 주장만 다시 분석하는 변경 안(잡 mi.revise) — 바로 반영하지 않는다."""
    doc = await load(aid)
    scope = body.scope.model_dump(exclude_none=True)
    if scope["kind"] == "area" and scope.get("area") not in rules.AREAS:
        raise ApiError(422, "VALIDATION_FAILED", "다시 분석할 탭을 골라 주세요")
    origin = "claim_research" if scope["kind"] == "claims" else "user"
    rev_id, job_id = await create_revision(doc, scope, body.instruction, origin=origin)
    return {"job_id": job_id, "revision_id": rev_id, "status": "queued"}


@router.get("/analyses/{aid}/revisions/{rev}", response_model=RevisionView, tags=["revisions"])
async def get_revision(aid: str, rev: str) -> dict[str, Any]:
    doc = await load(aid)
    return await revision_view(doc, await _rev(doc, rev))


@router.post("/analyses/{aid}/revisions/{rev}/rounds", status_code=202, response_model=JobAccepted, tags=["revisions"])
async def add_round(aid: str, rev: str, body: RoundIn) -> dict[str, Any]:
    """수정 요청 · 빠른 요청 — 같은 안에 라운드를 더한다(변경 목록은 늘 기준 버전 대비 누적 차이)."""
    doc = await load(aid)
    r = await _rev(doc, rev)
    if r.get("status") in ("applied", "discarded"):
        raise ApiError(409, "CONFLICT", "이미 끝난 재분석 안이에요")
    if r.get("job_id") and await job_active(r["job_id"]):
        raise ApiError(409, "RUN_IN_PROGRESS", "다시 분석하는 중이에요")
    scope = body.scope.model_dump(exclude_none=True) if body.scope else r.get("scope")

    def upd(x: dict[str, Any]) -> None:
        x.setdefault("rounds", []).append({"instruction": body.instruction, "scope": scope, "at": now_iso()})
        x["scope"] = scope
        x["status"] = "running"

    await R.call(R.update_doc, R.REV, rev, upd)
    job_id = await enqueue("mi.revise", {"analysis_id": aid, "revision_id": rev}, doc, title="부분 재분석")
    await R.call(R.update_doc, R.REV, rev, lambda x: x.update(job_id=job_id))
    return {"job_id": job_id, "status": "queued"}


@router.patch("/analyses/{aid}/revisions/{rev}/changes/{chg}", response_model=Change, tags=["revisions"])
async def patch_change(aid: str, rev: str, chg: str, body: ChangePatch) -> dict[str, Any]:
    doc = await load(aid)
    r = await _rev(doc, rev)
    hit = next((c for c in r.get("changes") or [] if c["id"] == chg), None)
    if hit is None:
        raise service.not_found("변경", chg)

    def upd(x: dict[str, Any]) -> None:
        for c in x.get("changes") or []:
            if c["id"] == chg:
                c["reverted"] = bool(body.reverted)

    r = await R.call(R.update_doc, R.REV, rev, upd)
    c = next(c for c in r["changes"] if c["id"] == chg)
    return {**c, "revision_id": rev, "label": CHIP_LABEL.get(c["kind"], "")}


@router.post("/analyses/{aid}/revisions/{rev}/revert-all", response_model=RevisionView, tags=["revisions"])
async def revert_all(aid: str, rev: str) -> dict[str, Any]:
    doc = await load(aid)
    await _rev(doc, rev)

    def upd(x: dict[str, Any]) -> None:
        for c in x.get("changes") or []:
            c["reverted"] = True

    r = await R.call(R.update_doc, R.REV, rev, upd)
    return await revision_view(doc, r)


@router.post("/analyses/{aid}/revisions/{rev}/apply", response_model=VersionOut, tags=["revisions"])
async def apply_revision(aid: str, rev: str) -> dict[str, Any]:
    """되돌리지 않은 변경만 반영한 새 버전(kind=revision). 기준 버전이 그새 바뀌었으면 409 VERSION_CONFLICT(AC-MI-57)."""
    from .graphs.revise import apply_changes

    doc = await load(aid)
    r = await _rev(doc, rev)
    if r.get("status") != "proposed":
        raise ApiError(409, "CONFLICT", "적용할 수 있는 재분석 안이 아니에요", {"status": r.get("status")})
    if int(doc.get("result_version") or 0) != int(r.get("base_version") or 0):
        raise ApiError(409, "VERSION_CONFLICT", "그사이 결과가 바뀌었어요. 다시 분석해 주세요",
                       {"base_version": r.get("base_version"), "current_version": doc.get("result_version")})
    live = [c for c in r.get("changes") or [] if not c.get("reverted")]
    if not live:
        raise ApiError(422, "VALIDATION_FAILED", "적용할 변경이 없어요")
    base = await load_version(doc, int(r["base_version"]))
    new_doc = apply_changes(doc, base, r, only_live=True)
    # 행 추가로 생긴 기준을 작업에 더한다
    for c in live:
        crit = (c.get("payload") or {}).get("criterion") or (c.get("after") or {}).get("criterion")
        if c["kind"] == "row_add" and crit:
            if not any(x["id"] == crit["id"] for x in doc.get("criteria") or []):
                doc.setdefault("criteria", []).append({**crit, "order": len(doc.get("criteria") or [])})
        if c["kind"] == "row_remove" and (c.get("target") or {}).get("column"):
            for comp in doc.get("competitors") or []:
                if comp["id"] == c["target"]["column"]:
                    comp["removed"] = True
                    comp["pinned"] = True
    await R.call(R.put_analysis, doc)
    chips = {}
    for c in live:
        chips[c["kind"]] = chips.get(c["kind"], 0) + 1
    summary = f"{_scope_label(r.get('scope') or {})} 재분석 · 변경 {len(live)}건"
    n = await versions.save_new_version(doc, new_doc, kind="revision", summary=summary)
    await R.call(R.update_doc, R.REV, rev, lambda x: x.update(status="applied", applied_version=n))
    return {"version": n}


@router.post("/analyses/{aid}/revisions/{rev}/discard", status_code=204, tags=["revisions"])
async def discard_revision(aid: str, rev: str) -> Response:
    doc = await load(aid)
    await _rev(doc, rev)
    await R.call(R.update_doc, R.REV, rev, lambda x: x.update(status="discarded"))
    return Response(status_code=204)


# ── 시트 구성 · 레이아웃 ─────────────────────────────────
def slides_view(doc: dict[str, Any], v: dict[str, Any]) -> dict[str, Any]:
    rows = v.get("slides") or []
    u = (doc.get("usage") or {}).get("value") or "none"
    in_sec = [r for r in rows if r.get("in_section", True)]
    extra = [r for r in rows if not r.get("in_section", True) and r.get("sheet_type") != "IM"]
    ind = sum(1 for r in in_sec if r.get("industry_layout"))
    type_name = rules.USAGE_TYPE_NAME.get(u, "리포트")
    if u == "quickwin":
        title = "퀵윈 · MI 섹션 없음 · VP 재료로 넘겨요"
    elif u == "none":
        title = f"리포트 · {len(in_sec)}시트 · 보낼 때 다시 매핑"
    else:
        title = f"{type_name.replace(' 제안서', '')} MI 섹션 {len(in_sec)}시트 + 넣으면 좋은 시트 {len(extra)}"
    n_auto = sum(1 for r in rows if r.get("include_mode") == "auto")
    n_check = sum(1 for r in rows if r.get("include_mode") == "check")
    footer = f"슬라이드 구성 · {len([r for r in rows if r.get('included')])}시트 · 넣으면 좋은 시트 {len(extra)} · 자동 {n_auto} · 확인 권장 {n_check}"
    return {"usage": u, "usage_label": rules.USAGE_LABEL.get(u, "").format(n=len(in_sec)),
            "header": {"title": title, "industry": ind, "generic": len(in_sec) - ind, "sheets": len(in_sec), "extra": len(extra)},
            "rows": [{**r, "analysis_id": doc["id"], "version": int(v.get("n") or 0)} for r in rows], "order": [r["id"] for r in rows], "footer": footer}


@router.get("/analyses/{aid}/slides", response_model=SlidesView, tags=["slides"])
async def get_slides(aid: str) -> dict[str, Any]:
    doc = await load(aid)
    return slides_view(doc, await load_version(doc))


def _find_sheet(v: dict[str, Any], sht: str) -> dict[str, Any]:
    s = next((s for s in v.get("slides") or [] if s["id"] == sht), None)
    if s is None:
        raise service.not_found("시트", sht)
    return s


@router.patch("/analyses/{aid}/slides/{sht}", response_model=SlidePlan, tags=["slides"])
async def patch_slide(aid: str, sht: str, body: SlidePatch) -> dict[str, Any]:
    """포함 체크 → included · 고정. 대안 코드 → 그 템플릿으로 바꾸고 고정."""
    doc = await load(aid)
    v = await load_version(doc)
    _find_sheet(v, sht)
    m = layout.metrics(doc, v)
    seg = (doc.get("segment") or {}).get("code")

    def change(ver: dict[str, Any]) -> None:
        s = next(s for s in ver["slides"] if s["id"] == sht)
        if body.included is not None:
            s["included"] = bool(body.included)
            s["include_mode"] = "pin"
        if body.template_code:
            code = body.template_code
            f, needs = layout.fit(code, m)
            if f < 0:
                raise ApiError(422, "VALIDATION_FAILED", "이 레이아웃에 필요한 데이터가 없어 고를 수 없어요", {"template": code})
            s.update(template_code=code, template_name=layout.template(code)["name"], thumb_kind=layout.thumb_kind(code), fit=f, needs_report=needs,
                     industry_layout=code.startswith("MI-"), pinned=True, why=layout.why_for("pinned", s["sheet_type"], code, m, seg))
            s["item_label"] = layout.item_label(s["sheet_type"], code, m)
        if body.pinned is not None:
            s["pinned"] = bool(body.pinned)

    v = await versions.update_current(doc, change)
    s = _find_sheet(v, sht)
    return {**s, "analysis_id": aid, "version": int(v.get("n") or 0)}


REQUEST_HINTS = [("포지셔닝", "CP-B"), ("점유율", "CP-C"), ("비교표", "CP-A"), ("타임라인", "TR-A"), ("영향도", "TR-C"), ("swot", "CB-D"),
                 ("전략 목표", "CB-B"), ("운영 흐름", "CB-C"), ("여정", "US-B"), ("페르소나", "US-A"), ("구성 비율", "US-C"), ("tam", "MS-C"),
                 ("성장 추이", "MS-B"), ("핵심 수치", "MS-A"), ("동인", "MS-E")]


@router.get("/analyses/{aid}/slides/{sht}/candidates", response_model=CandidatesView, tags=["slides"])
async def slide_candidates(aid: str, sht: str, requested: str | None = None, text: str | None = None) -> dict[str, Any]:
    """MI3L — 요청 해석 · 선택지 A/B/C · 고를 수 있는 레이아웃 · 적합도(§7.8)."""
    doc = await load(aid)
    v = await load_version(doc)
    sheet = _find_sheet(v, sht)
    m = layout.metrics(doc, v)
    seg = (doc.get("segment") or {}).get("code")
    sheet_seg = ((doc.get("segment") or {}).get("mix") or {}).get("c" if sheet["sheet_type"] == "US" else "a") or seg
    req = requested or (sheet.get("options") or {}).get("requested") or None
    if req is None:
        alts = [a for a in sheet.get("alternatives") or [] if a.get("fit", -1) >= 0]
        req = alts[0]["code"] if alts else sheet["template_code"]
    opt = layout.option_texts(sheet, req, m, sheet_seg)
    tpls = layout.candidates(sheet, m, sheet_seg, req)
    n = len(tpls)
    if sheet["sheet_type"] == "CP":
        head = f"{sheet['sheet_name']} · 고를 수 있는 레이아웃 · 업종 틀엔 경쟁 장이 없어 범용 {n}종"
    elif any(t["code"].startswith("MI-") for t in tpls):
        head = f"{sheet['sheet_name']} · 고를 수 있는 레이아웃 · 업종 레이아웃 1종 + 범용 {n - 1}종"
    else:
        head = f"{sheet['sheet_name']} · 고를 수 있는 레이아웃 · 범용 {n}종"
    others = []
    for s in v.get("slides") or []:
        if s["id"] == sht or not s.get("included"):
            continue
        s_seg = ((doc.get("segment") or {}).get("mix") or {}).get("c" if s["sheet_type"] == "US" else "a") or seg
        others.append({"id": s["id"], "sheet_name": s["sheet_name"], "count": len(layout.candidates(s, m, s_seg, None))})
    return {"sheet": {**sheet, "analysis_id": aid, "version": int(v.get("n") or 0)}, "request_text": text or (sheet.get("options") or {}).get("request_text", ""),
            "requested": req, "explanation": opt["explanation"], "options": opt["options"], "templates": tpls, "head": head, "others": others}


@router.post("/analyses/{aid}/slides/{sht}/layout", response_model=SlidePlan, tags=["slides"],
             responses={202: {"model": JobAccepted, "description": "선택지 A — 모자란 데이터 추가 수집(mi.layout)"}})
async def choose_layout(aid: str, sht: str, body: LayoutIn) -> Any:
    doc = await load(aid)
    v = await load_version(doc)
    sheet = _find_sheet(v, sht)
    if body.option == "A":
        if doc.get("current_job_id") and await job_active(doc["current_job_id"]):
            raise ApiError(409, "RUN_IN_PROGRESS", "이미 분석하고 있어요")
        job_id = await enqueue("mi.layout", {"analysis_id": aid, "sheet_id": sht, "template": body.template, "axes": body.axes, "pin": bool(body.pin)}, doc,
                               title="레이아웃 데이터 보강")
        await R.call(R.patch_analysis, aid, {"current_job_id": job_id, "status": "running",
                                             "run": {**(doc.get("run") or {}), "job_id": job_id, "mode": "layout", "started_at": now_iso(), "stage": "search"}})
        return JSONResponse(status_code=202, content={"job_id": job_id, "status": "queued"})
    m = layout.metrics(doc, v)
    seg = (doc.get("segment") or {}).get("code")
    code = body.template if body.option == "B" else sheet["template_code"]

    def change(ver: dict[str, Any]) -> None:
        s = next(s for s in ver["slides"] if s["id"] == sht)
        if body.option == "B":
            f, needs = layout.fit(code, m)
            if f < 0:
                raise ApiError(422, "VALIDATION_FAILED", "이 레이아웃에 필요한 데이터가 없어 고를 수 없어요", {"template": code})
            s.update(template_code=code, template_name=layout.template(code)["name"], thumb_kind=layout.thumb_kind(code), fit=f, needs_report=needs,
                     industry_layout=code.startswith("MI-"), why=layout.why_for("generic" if s["sheet_type"] != "CP" else "cp", s["sheet_type"], code, m, seg),
                     alternatives=layout._alts(layout.band(s["sheet_type"]), code, m), item_label=layout.item_label(s["sheet_type"], code, m))
            s["pinned"] = True
        if body.pin is not None:
            s["pinned"] = bool(body.pin) or s.get("pinned", False) if body.option == "B" else bool(body.pin)
        if body.axes:
            s.setdefault("options", {})["axes"] = body.axes

    v = await versions.update_current(doc, change)
    s = _find_sheet(v, sht)
    return {**s, "analysis_id": aid, "version": int(v.get("n") or 0)}


@router.post("/analyses/{aid}/slides/requests", response_model=SlideRequestOut, tags=["slides"])
async def slide_request(aid: str, body: SlideRequestIn) -> dict[str, Any]:
    """구성 요청 · 보내기 전 요청 → 레이아웃 요청이면 MI3L(그 시트), 포함 · 제외 요청이면 바로 반영."""
    doc = await load(aid)
    v = await load_version(doc)
    rows = v.get("slides") or []
    try:
        res = await aix.llm("mi.slide_request", prompts.slide_request(body.text, rows), prompts.SlideRequest, confidential=False)
    except (aix.LLMFailed, ApiError):
        res = prompts.SlideRequest()
    low = body.text.lower()
    if res.kind == "none" or (res.kind == "layout" and not res.template):
        hint = next((code for word, code in REQUEST_HINTS if word in low), None)
        if hint:
            res = prompts.SlideRequest(kind="layout", template=hint, sheet_type=hint.split("-")[0])
        elif any(w in body.text for w in ("넣어", "추가", "빼", "제외")):
            res = prompts.SlideRequest(kind="include")
    if res.kind == "layout" and res.template:
        st = res.sheet_type or res.template.split("-")[0]
        target = next((r for r in rows if r["sheet_type"] == st or (st in ("MS", "TR") and r["sheet_type"] == "MS+TR")), None) or \
            next((r for r in rows if r["template_code"].split("-")[0] == st), None)
        if target is None:
            return {"kind": "none", "message": "그 레이아웃을 쓸 시트가 없어요"}

        def remember(ver: dict[str, Any]) -> None:
            s = next(s for s in ver["slides"] if s["id"] == target["id"])
            s.setdefault("options", {}).update({"requested": res.template, "request_text": body.text})
            if res.axes_x and res.axes_y:
                s["options"]["axes"] = {"x": res.axes_x, "y": res.axes_y}

        await versions.update_current(doc, remember)
        return {"kind": "layout", "sheet_id": target["id"], "requested": res.template, "message": ""}
    if res.kind == "include":
        changed = []

        def inc(ver: dict[str, Any]) -> None:
            for s in ver["slides"]:
                names = (s["sheet_type"], s["sheet_name"])
                if any(x in names or x in s["sheet_name"] for x in res.include) or any(w in body.text and "넣" in body.text for w in (s["sheet_name"],)):
                    if not s["included"]:
                        s["included"] = True
                        s["include_mode"] = "pin"
                        changed.append(s["id"])
                if any(x in names or x in s["sheet_name"] for x in res.exclude) or (s["sheet_name"] in body.text and ("빼" in body.text or "제외" in body.text)):
                    if s["included"]:
                        s["included"] = False
                        s["include_mode"] = "pin"
                        changed.append(s["id"])

        await versions.update_current(doc, inc)
        return {"kind": "include", "changed": changed, "message": f"시트 {len(changed)}개를 바꿨어요" if changed else "바꿀 시트를 찾지 못했어요"}
    return {"kind": "none", "message": "요청을 이해하지 못했어요 · 레이아웃이나 넣고 뺄 시트를 말해 주세요"}


# ── 넘김 · 묶음 · 내보내기 ──────────────────────────────
def _default_sheets(v: dict[str, Any]) -> list[str]:
    return [s["id"] for s in v.get("slides") or [] if s.get("included")]


@router.post("/analyses/{aid}/handoffs", response_model=HandoffOut, tags=["handoffs"])
async def create_handoff(aid: str, body: HandoffIn) -> dict[str, Any]:
    """넘기기 준비 — 묻기 2~4 가 남으면 409 ASK_REQUIRED, 연결된 제안서가 없으면 422 NO_TARGET(§6.9)."""
    doc = await load(aid)
    v = await load_version(doc)
    target_id = body.target_id or ((doc.get("links") or {}).get("proposal_id") if body.target.startswith("proposal") else None)
    usage = (doc.get("usage") or {}).get("value")
    if body.target.startswith("proposal") and not target_id:
        raise ApiError(422, "NO_TARGET", "넘길 제안서가 없어요 · 보낼 제안서를 골라 주세요")
    if body.target == "proposal_mi" and body.dry_run and usage in ("none", "quickwin", None) and not body.target_id:
        raise ApiError(422, "NO_TARGET", "이 분석은 제안서 MI 섹션과 연결돼 있지 않아요")
    sheets = body.sheets if body.sheets is not None else _default_sheets(v)
    confirm = body.confirm.model_dump(exclude_none=True) if body.confirm else {}
    asks = B.asks_for(doc, v, target=body.target, sheets=sheets, confirm=confirm, target_pinned=body.target_pinned_sheets)
    if asks:
        raise ApiError(409, "ASK_REQUIRED", "넘기기 전에 확인이 필요해요", {"asks": asks})
    section = "why" if body.target == "proposal_why" else ("bigMi" if usage == "solution" else "mi")
    if body.dry_run:
        return {"handoff_id": None, "bundle_url": "", "sheets": sheets, "status": "ready", "target_id": target_id, "section_key": section}
    comps = anonymize.live(doc.get("competitors") or [])
    table = ((v.get("document") or {}).get("competitor") or {}).get("table") or {}
    in_table = [c for c in table.get("columns") or [] if c != "samsung"]
    amap = anonymize.export_map(comps, True, doc.get("naming_mode", "letter") if doc.get("anonymize", True) else "letter",
                                [c["id"] for c in comps if c["id"] in in_table] or None)
    if not doc.get("anonymize", True) and confirm.get("real_names"):
        amap = {}
    hof_id = R.nid("hof")
    rec = {"analysis_id": aid, "version": int(v.get("n") or 0), "target": body.target, "target_id": target_id,
           "target_title": body.target_title or ((doc.get("links") or {}).get("proposal_title") if body.target.startswith("proposal") else None),
           "sheets": sheets, "options": (body.options.model_dump() if body.options else {"cite_sources": True, "fix_notes": True, "link_why": True}),
           "confirmations": confirm, "anonymization_map": amap, "status": "prepared", "served_named_at": [], "created_at": now_iso(),
           "target_pinned_sheets": body.target_pinned_sheets or []}
    await R.call(R.put_doc, R.HOF, hof_id, rec)
    tgt = "proposal_mi" if body.target == "proposal_mi" else body.target
    return {"handoff_id": hof_id, "bundle_url": f"/api/mi/v1/analyses/{aid}/bundle?target={tgt}&handoff_id={hof_id}", "sheets": sheets,
            "status": "prepared", "target_id": target_id, "section_key": section}


@router.patch("/analyses/{aid}/handoffs/{hof}", response_model=Handoff, tags=["handoffs"])
async def patch_handoff(aid: str, hof: str, body: HandoffPatch) -> dict[str, Any]:
    doc = await load(aid)
    rec = await R.call(R.get_doc, R.HOF, hof)
    if rec is None or rec.get("analysis_id") != aid:
        raise service.not_found("넘김 기록", hof)

    def upd(x: dict[str, Any]) -> None:
        x["status"] = body.status
        if body.target_title:
            x["target_title"] = body.target_title
        if body.target_id:
            x["target_id"] = body.target_id

    rec = await R.call(R.update_doc, R.HOF, hof, upd)
    if body.status == "delivered" and str(rec.get("target", "")).startswith("proposal"):
        doc["latest_handoff"] = {"target_title": rec.get("target_title"), "target_id": rec.get("target_id"), "at": now_iso(), "handoff_id": hof}
        if rec.get("target_id") and not (doc.get("links") or {}).get("proposal_id"):
            doc.setdefault("links", {})["proposal_id"] = rec.get("target_id")
            doc["links"]["proposal_title"] = rec.get("target_title")
        await R.call(R.put_analysis, doc)
        await service.register(doc)
    return _hof_public(rec)


def _hof_public(rec: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "analysis_id", "version", "target", "target_id", "target_title", "sheets", "options", "confirmations", "anonymization_map", "status",
            "served_named_at", "created_at", "updated_at")
    return {k: rec.get(k) for k in keys if rec.get(k) is not None}


@router.get("/analyses/{aid}/bundle", response_model=Bundle, tags=["handoffs"])
async def get_bundle(aid: str, target: str = "proposal_mi", handoff_id: str | None = None) -> dict[str, Any]:
    """읽기 전용 묶음(vp · 웹). 대상에 맞게 익명 처리를 마친 상태로 나간다. target=competitor 만 실명(작업 소유자만)."""
    doc = await load(aid)
    if target not in ("proposal_mi", "proposal_why", "vp", "storyboard", "scenario", "competitor"):
        raise ApiError(422, "VALIDATION_FAILED", f"모르는 대상이에요: {target}")
    if target == "competitor" and doc.get("owner_id") != current_user().id:
        raise ApiError(403, "FORBIDDEN", "작업 소유자만 실명 묶음을 읽을 수 있어요")
    v = await load_version(doc) if target != "competitor" or doc.get("result_version") else {"n": 0}
    hof = await R.call(R.get_doc, R.HOF, handoff_id) if handoff_id else None
    if hof is not None and hof.get("analysis_id") != aid:
        hof = None
    return B.bundle(doc, v, target=target, handoff=hof)


@router.get("/analyses/{aid}/evidence", response_model=EvidenceSnapshot, tags=["handoffs"])
async def evidence(aid: str) -> dict[str, Any]:
    """Storyboard Key Message 근거 스냅숏(MI4 `Key Message에 근거로 붙이기`) — storyboard 묶음과 같은 익명 · 대외비 규칙.
    mi 는 storyboard 를 부르지 않는다: 웹이 이 값을 `POST /api/storyboard/v1/storyboards/{sb}/key-messages/{kmsg}/evidence` 로 올린다."""
    doc = await load(aid)
    v = await load_version(doc)
    return B.evidence_snapshot(doc, B.bundle(doc, v, target="storyboard"))


@router.get("/analyses/{aid}/proposal-handoff", response_model=ProposalHandoff, tags=["handoffs"])
async def proposal_handoff(aid: str, type: str | None = None, section: str = "mi", handoff_id: str | None = None,  # noqa: A002
                           named: bool = False) -> dict[str, Any]:
    """ProposalHandoff v1(§6.14) — MI4 매핑과 같은 데이터. named=true 는 실명 확인 기록이 있을 때만(아니면 409 ASK_REQUIRED)."""
    doc = await load(aid)
    v = await load_version(doc)
    hof = await R.call(R.get_doc, R.HOF, handoff_id) if handoff_id else None
    if hof is not None and hof.get("analysis_id") != aid:
        hof = None
    if named:
        if not hof or not (hof.get("confirmations") or {}).get("real_names"):
            raise ApiError(409, "ASK_REQUIRED", "경쟁사 실명을 내려면 확인이 필요해요", {"asks": [{"kind": "real_names", "default": "anonymize"}]})
        await R.call(R.update_doc, R.HOF, hof["id"], lambda x: x.setdefault("served_named_at", []).append(now_iso()))
    if type is not None and type not in ("standard", "quickwin", "solution"):
        raise ApiError(422, "VALIDATION_FAILED", "type 은 standard · quickwin · solution 중 하나예요")
    if section not in ("mi", "bigMi", "why"):
        raise ApiError(422, "VALIDATION_FAILED", "section 은 mi · bigMi · why 중 하나예요")
    return B.proposal_handoff(doc, v, ptype=type, section=section, handoff=hof, named=named)


@router.post("/analyses/{aid}/facts:lookup", response_model=FactsLookupOut, tags=["handoffs"],
             responses={202: {"model": JobAccepted, "description": "research=true — 다른 출처 찾기와 같은 검색(결과는 후보로만)"}})
async def facts_lookup(aid: str, body: FactsLookupIn) -> Any:
    """제안서 PR7Q `MI에서 확인` — 저장된 주장 중 지표 · 이름 · 단위가 맞는 것을 결정적으로(새 검색 없음, AC-MI-94)."""
    doc = await load(aid)
    v = await load_version(doc)
    if body.research:
        job_id = await enqueue("mi.facts_research", {"analysis_id": aid, "questions": [q.model_dump() for q in body.questions]}, doc, title="수치 다시 찾기")
        return JSONResponse(status_code=202, content={"job_id": job_id, "status": "queued"})
    items = []
    claims = v.get("claims") or {}
    srcs = v.get("sources") or {}
    for q in body.questions:
        cands = []
        label = (q.label or "").replace(" ", "")
        key = (q.key or "").lower()
        for cid, c in claims.items():
            nums = [n for n in c.get("numbers") or [] if n.get("kind") != "year"]
            if not nums:
                continue
            mk = str(c.get("metric_key") or "").lower()
            ml = (c.get("metric_label") or "").replace(" ", "")
            text = (c.get("text") or "").replace(" ", "")
            hit = (mk and (mk == key or (q.context and mk in q.context.lower()))) or (label and (label in ml or label in text))
            if not hit:
                continue
            raw = nums[0]["raw"]
            unit = re.sub(r"^[\d,\.\s~\-]+", "", raw).strip() or None
            if q.unit and unit and q.unit.strip() not in unit and unit not in q.unit:
                continue
            val = re.match(r"[\d,\.]+", raw)
            cit = next((x for x in v.get("citations") or [] if x.get("claim_id") == cid and not x.get("dropped")), None)
            src = srcs.get((cit or {}).get("source_id", "")) or {}
            cands.append({"value": val.group(0).replace(",", "") if val else raw, "unit": unit, "status": c.get("status", "missing"), "claim_id": cid,
                          "source": {"kind": src.get("kind"), "ref": src.get("id"), "label": views.footnote(src, cit), **({"url": src["url"]} if src.get("url") else {})}
                          if src else None})
        items.append({"key": q.key, "candidates": cands})
    return B.Ctx(doc, v, target="proposal_mi").clean({"items": items})


@router.post("/analyses/{aid}/exports", status_code=202, response_model=JobAccepted, tags=["handoffs"])
async def create_export(aid: str, body: ExportIn) -> dict[str, Any]:
    """PDF 리포트 · PPTX 한 장 요약 · Excel 표(잡 mi.export → export 서비스) — 완료 이벤트의 file_id 로 내려받기."""
    doc = await load(aid)
    await load_version(doc)
    job_id = await enqueue("mi.export", {"analysis_id": aid, "format": body.format, "audience": body.audience}, doc,
                           title={"pdf_report": "PDF 리포트", "pptx_onepager": "PPTX 한 장 요약", "xlsx_table": "Excel 표"}[body.format])
    return {"job_id": job_id, "status": "queued"}


@router.post("/analyses/{aid}/share", response_model=ShareOut, tags=["handoffs"])
async def share(aid: str) -> dict[str, Any]:
    """링크 공유 — workspace 공유 링크(보기 · 코멘트). 공유 화면은 익명 표기."""
    doc = await load(aid)
    await load_version(doc)
    title = anonymize.scrub(doc.get("title") or "Market Intelligence", doc.get("competitors") or [], {})
    try:
        res = await ServiceClient("workspace").post("/v1/share-links", json={"target": aid, "route": f"/mi/{aid}/shared", "title": title})
    except ApiError as exc:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", "공유 링크를 만들지 못했어요 · 잠시 후 다시 시도해 주세요", {"cause": exc.code}) from exc
    await R.call(R.put_doc, R.HOF, R.nid("hof"), {"analysis_id": aid, "version": int(doc.get("result_version") or 0), "target": "share",
                                                   "status": "delivered", "created_at": now_iso(), "target_title": "링크 공유"})
    return {"share_url": res.get("url") or f"/share/{res.get('token')}", "token": res.get("token")}


@router.get("/analyses/{aid}/export-view", response_model=ExportView, tags=["handoffs"])
async def export_view(aid: str, target_id: str | None = None) -> dict[str, Any]:
    """MI4 화면 데이터(제안) — 보낼 제안서 · 시트 매핑 · 옵션 · 파일 · 다른 기능."""
    doc = await load(aid)
    v = await load_version(doc)
    u = (doc.get("usage") or {}).get("value") or "none"
    links = doc.get("links") or {}
    proposals = []
    try:
        res = await ServiceClient("workspace").get("/v1/items", params={"feature": "PR", "limit": 20})
        for it in res.get("items") or []:
            proposals.append({"id": it["item_id"], "title": it["title"], "status": it.get("status", ""), "route": it.get("route", ""),
                              "proposal_type": (it.get("meta") or {}).get("proposal_type"), "updated_at": it.get("updated_at")})
    except ApiError:
        pass
    tid = target_id or links.get("proposal_id")
    target = None
    if tid:
        hit = next((p for p in proposals if p["id"] == tid), None)
        target = {"id": tid, "title": (hit or {}).get("title") or links.get("proposal_title") or "제안서", "status": (hit or {}).get("status", ""),
                  "proposal_type": (hit or {}).get("proposal_type") or links.get("proposal_type")}
    rows = [{**r, "analysis_id": aid, "version": int(v.get("n") or 0)} for r in B.section_rows(v.get("slides") or [])]
    for r in rows:
        st, label = B.row_status(r)
        r["status"] = st
        r["status_label"] = label
    in_rows = [r for r in rows if r.get("included")]
    type_name = rules.USAGE_TYPE_NAME.get(u, "리포트")
    head = f"{type_name} MI 섹션 · 보낼 시트 {len(in_rows)}" if u in ("standard", "solution") else f"{type_name} · 보낼 시트 {len(in_rows)}"
    cp = (v.get("document") or {}).get("competitor") or {}
    n_str = len(cp.get("strengths") or [])
    fix_open = sum(int(r.get("fix_open") or 0) for r in in_rows)
    footer_parts = [f"보낼 시트 {len(in_rows)}", "출처 표기"]
    if fix_open:
        footer_parts.append(f"[확정 필요] {fix_open}건은 노트로")
    n_tabs = sum(1 for a, s in (v.get("area_status") or {}).items() if s in ("done", "reused"))
    files = [{"key": "pdf_report", "label": "PDF 리포트", "sub": f"{n_tabs}개 탭 전체 · 출처 목록 포함"},
             {"key": "pptx_onepager", "label": "PPTX 한 장 요약", "sub": "경영진 보고용 1장"},
             {"key": "xlsx_table", "label": "Excel 표", "sub": "경쟁사 비교표 · 출처 목록"},
             {"key": "share", "label": "링크 공유", "sub": "팀원 보기 · 코멘트"}]
    nxt = []
    if links.get("storyboard_id") or v.get("document"):
        nxt.append({"key": "storyboard", "tool": "Storyboard", "what": "Key Message에 근거로 붙이기", "route": f"/storyboard/new?mi={aid}"})
    prods = cp.get("samsung_products") or []
    if prods:
        names = " · ".join(p.get("name", "") for p in prods[:2])
        models = ",".join(p.get("model_code") or "" for p in prods if p.get("model_code"))
        nxt.append({"key": "spec", "tool": "Spec 시트", "what": f"비교한 {names} 스펙 시트 만들기", "route": f"/spec/new?models={models}&from=mi:{aid}"})
    personas = ((v.get("document") or {}).get("user") or {}).get("personas") or []
    if personas:
        nxt.append({"key": "scenario", "tool": "공간 시나리오", "what": f"페르소나 {len(personas)}{rules.josa(str(len(personas)), '을', '를')} 시나리오 인물로",
                    "route": f"/scenario/new?mi={aid}&personas={len(personas)}"})
    vp_card = None
    if u == "quickwin":
        mats = B.vp_materials(B.Ctx(doc, v, target="vp"))
        vp_card = {"title": "VP 재료로 넘기기", "text": f"과제 {len(mats['challenges'])} · 사용자 {len(mats['users'])} · 삼성 강점 {len(mats['strengths'])} · 수치 {len(mats['numbers'])}"}
    return {"target": target, "usage": u, "usage_label": rules.USAGE_LABEL.get(u, "").format(n=len(in_rows)), "mapping_head": head, "rows": rows,
            "options": {"cite_sources": True, "fix_notes": True, "link_why": True}, "strengths_count": n_str,
            "show_link_why": bool(cp) and u in ("standard", "solution"), "files": files, "next_features": nxt, "footer": " · ".join(footer_parts),
            "vp_card": vp_card, "proposals": proposals}


@router.get("/analyses/{aid}/shared-view", response_model=ResultView, tags=["handoffs"])
async def shared_view(aid: str) -> dict[str, Any]:
    """링크 공유 화면(`/mi/:id/shared`) 데이터 — MI3 결과와 같은 모양, 경쟁사는 내보내기 표기(실명 · 별칭 없음, AC-MI-67)."""
    doc = await load(aid)
    v = await load_version(doc)
    out = views.result_view(doc, v, latest_n=int(doc.get("result_version") or 0))
    ctx = B.Ctx(doc, v, target="export_customer")
    cp = out.get("competitor") or {}
    if cp.get("table"):
        cols = [c for c in cp["table"]["columns"] if c["samsung"] or c["key"] in ctx.names]
        for c in cols:
            if not c["samsung"]:
                c["label"] = ctx.names[c["key"]]
                c["sub"] = ""
        keep = {c["key"] for c in cols}
        cp["table"]["columns"] = cols
        for row in cp["table"]["rows"]:
            row["cells"] = {k: x for k, x in row["cells"].items() if k in keep}
    ctx.scrub = True
    return ctx.clean(out)


@router.get("/analyses/{aid}/table-text", response_model=TableText, tags=["handoffs"])
async def table_text(aid: str, audience: str = "customer") -> dict[str, Any]:
    """MI3 `표 복사` — 비교표를 탭으로 나눈 글(고객용이면 익명 표기)."""
    doc = await load(aid)
    v = await load_version(doc)
    ctx = B.Ctx(doc, v, target="export_internal" if audience == "internal" else "export_customer")
    comp = B.comparison(ctx)
    lines = ["\t".join(["요구사항 항목", *comp.get("columns", [])])]
    for i, row in enumerate(comp.get("cells") or []):
        lines.append("\t".join([comp["criteria"][i], *row]))
    return ctx.clean({"text": "\n".join(lines), "columns": comp.get("columns", []), "rows": len(comp.get("cells") or [])})


# ── 재확인 ───────────────────────────────────────────────
@router.post("/analyses/{aid}/recheck", status_code=202, response_model=JobAccepted, tags=["recheck"])
async def recheck(aid: str) -> dict[str, Any]:
    doc = await load(aid)
    await load_version(doc)
    job_id = await enqueue("mi.recheck", {"analysis_id": aid}, doc, title="30일 재확인")
    return {"job_id": job_id, "status": "queued"}


@router.get("/analyses/{aid}/changes", response_model=ChangesView, tags=["recheck"])
async def get_changes(aid: str) -> dict[str, Any]:
    doc = await load(aid)
    ch = doc.get("upd_changes") or []
    affected = sorted({a for c in ch for a in c.get("affected_areas") or []}, key=lambda x: rules.AREAS.index(x))
    out = {"items": ch, "summary": views.changes_summary(ch), "head": f"바뀐 자료 {len(ch)}건", "affected_areas": affected,
           "eta_label": rules.eta_label(rules.changed_eta_s(len(affected) or 1))}
    return anonymize.scrub(out, doc.get("competitors") or [], {})


# ── 경쟁사 분석에서 합치기 ───────────────────────────────
@router.post("/imports/competitor", status_code=202, response_model=CaImportAccepted, tags=["imports"])
async def import_competitor(body: CaImportIn) -> dict[str, Any]:
    """CA5 `Market Intelligence 작업에 합치기` — 경쟁 영역에 내용이 있으면 재분석 안(MI3R), 없으면 바로 새 버전(kind=import)."""
    if body.analysis_id:
        doc = await load(body.analysis_id)
    else:
        doc = service.new_doc(customer_name=body.customer_name or (body.ca_bundle.get("customer") or {}).get("name"))
        seg = (body.ca_bundle.get("segment") or "").upper() if isinstance(body.ca_bundle.get("segment"), str) else None
        if seg in config.SEGMENT_CODES:
            doc["segment"] = {"code": seg, "mode": "auto", "inherited_from": "competitor"}
        doc["scope"] = {"areas": ["competitor"], "mode": "auto", "reasons": {"competitor": "경쟁사 분석에서 가져옴"}, "reduced": []}
        doc.setdefault("links", {})["competitor_analysis_id"] = body.ca_bundle.get("analysis_id")
        await R.call(R.put_analysis, doc)
    v = await R.call(R.get_version, doc["id"], int(doc.get("result_version") or 0))
    has_comp = bool(v and ((v.get("document") or {}).get("competitor") or {}).get("table"))
    rev_id = None
    if has_comp:
        rev_id = R.nid("rev")
        await R.call(R.put_doc, R.REV, rev_id, {"analysis_id": doc["id"], "base_version": int(doc.get("result_version") or 0),
                                                 "scope": {"kind": "area", "area": "competitor"},
                                                 "rounds": [{"instruction": "경쟁사 분석 결과 합치기", "at": now_iso()}], "origin": "ca_import",
                                                 "status": "running", "changes": [], "created_at": now_iso(), "sources_added": 0, "duration_s": 0})
    job_id = await enqueue("mi.import_ca", {"analysis_id": doc["id"], "ca_bundle": body.ca_bundle, "revision_id": rev_id}, doc, title="경쟁사 분석 합치기")
    if rev_id:
        await R.call(R.update_doc, R.REV, rev_id, lambda x: x.update(job_id=job_id))
    if "competitor" not in service.areas_of(doc):
        doc = await load(doc["id"])
        doc.setdefault("scope", {}).setdefault("areas", []).append("competitor")
        await R.call(R.put_analysis, doc)
    return {"job_id": job_id, "analysis_id": doc["id"], "revision_id": rev_id, "status": "queued"}
