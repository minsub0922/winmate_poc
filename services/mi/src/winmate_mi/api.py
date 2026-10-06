"""mi API (/v1) — 작업 · 설계 · 업종 · 규칙 · 경쟁사 · 기준 · 실행(03-mi.md §6.1~§6.4). 이 파일들의 엔드포인트가 contracts/mi.json 이 된다."""
from __future__ import annotations

import base64
from typing import Any

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.jobs import jobs

from . import aix, anonymize, config, kbx, rqx, rules, service, views
from . import store as R
from .deps import enqueue, job_active, load, load_version, reconcile, start_run
from .models import (
    AdditionsIn, AdditionsOut, Analysis, AnalysisList, AnalysisPatch, AutoRunAccepted, Capabilities, CompetitorAccepted,
    CompetitorAddIn, CompetitorList, CompetitorPatch, Competitor, CreateAnalysisIn, CriteriaList, CriteriaPut, DesignView, DetectIn,
    DetectOut, DuplicateIn, JobAccepted, MemoIn, RequirementsImportIn, RoutingRules, RunIn, RunProgress, SegmentInsights, SegmentList,
    ServiceInfo, StoryboardImportIn, VersionList,
)

router = APIRouter(prefix="/v1")

TITLE = "Market Intelligence — 업종 판별 · 4개 분석 영역 · 출처 검증 · 부분 재분석 · 보고서"


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="mi", title=TITLE, version="0.1.0")


# ── 규칙 · 능력 · 업종 ───────────────────────────────────
@router.get("/routing-rules", response_model=RoutingRules, tags=["meta"])
async def routing_rules() -> dict[str, Any]:
    """MIR 시트 — 서비스 설정(services/mi/config/routing.yaml)을 그대로 그린다. 서버 판단 코드도 같은 설정을 읽는다."""
    return rules.render_rules()


@router.get("/capabilities", response_model=Capabilities, tags=["meta"])
async def capabilities() -> dict[str, Any]:
    return aix.public_caps(await aix.capabilities())


async def _segment_list() -> dict[str, Any]:
    try:
        kb = await kbx.segments()
        kb_items = {i["code"]: i for i in kb.get("items") or []}
        method = kb.get("method", "")
        needs = kb.get("needs_confirmation") or []
    except ApiError:
        kb_items, method, needs = {}, "", ["kb 서비스에 닿지 못해 사례 수를 보이지 못해요"]
    items = []
    for s in config.segment_list():
        if s["code"] == "GEN":
            continue
        k = kb_items.get(s["code"]) or {}
        items.append({"code": s["code"], "full": s["full"], "short": s["short"], "case_count": int(k.get("case_count") or 0),
                      "has_layouts": True, "aliases": list(dict.fromkeys((s.get("aliases") or []) + (k.get("aliases") or []))),
                      "mapping": bool(s.get("kr")), "kb_id": s.get("kb_id")})
    return {"items": items, "case_total": sum(i["case_count"] for i in items), "method": method, "needs_confirmation": needs}


@router.get("/segments", response_model=SegmentList, tags=["segments"])
async def list_segments() -> dict[str, Any]:
    """16업종 · 사례 수(kb 프록시) + MI0 업종 칩(내 작업 업종 먼저, 남는 자리는 MI_HOME_SEGMENTS 순서)."""
    data = await _segment_list()
    by = {i["code"]: i for i in data["items"]}
    mine = await R.call(R.list_analyses, current_user().id)
    order: list[str] = []
    for a in sorted(mine, key=lambda x: x.get("updated_at", ""), reverse=True):
        c = (a.get("segment") or {}).get("code")
        if c and c in by and c not in order:
            order.append(c)
    for c in config.home_segments():
        if c in by and c not in order:
            order.append(c)
    data["home"] = [{"code": c, "short": by[c]["short"], "n": by[c]["case_count"]} for c in order[:6]]
    return data


async def insights_for(code: str) -> dict[str, Any]:
    out = await kbx.insights_view(code)
    out.pop("case_ids", None)
    return out


@router.get("/segments/{code}/insights", response_model=SegmentInsights, tags=["segments"])
async def segment_insights(code: str) -> dict[str, Any]:
    code = code.upper()
    if code not in config.SEGMENT_CODES:
        raise ApiError(404, "NOT_FOUND", f"모르는 업종 코드예요: {code}")
    return await insights_for(code)


@router.post("/segments/detect", response_model=DetectOut, tags=["segments"])
async def detect_segment(body: DetectIn) -> dict[str, Any]:
    """MI1I `업종 감지` — 빠른 경로: kb 근거만(LLM 없음) `0.6 × kb + 0.4 × 단서`."""
    text = body.text or ""
    basis = "입력한 요구사항 기준"
    cust = None
    if body.analysis_id:
        doc = await R.call(R.get_analysis, body.analysis_id)
        if doc:
            cust = doc.get("customer_name")
            text = " ".join([doc.get("customer_name") or "", doc.get("requirements_text") or "",
                             " ".join(r.get("text", "") for r in doc.get("requirements") or []), text]).strip()
            links = doc.get("links") or {}
            if links.get("storyboard_id"):
                basis = f"Storyboard '{links.get('storyboard_title') or ''}' 기준"
            elif links.get("requirements_id"):
                basis = "정의서 기준"
    if not text.strip():
        return {"candidates": [], "clues": [], "top": None, "basis": "", "customer_name": cust}
    try:
        res = await kbx.classify(text)
    except ApiError:
        return {"candidates": [], "clues": [], "top": None, "basis": basis, "customer_name": cust}
    cands = []
    clues = []
    for it in res.get("items") or []:
        conf = rules.combine_confidence(None, float(it.get("kb_score") or 0), float(it.get("clue_score") or 0))
        cands.append({"code": it["code"], "confidence": conf, "kb": it.get("kb_score"), "clue": it.get("clue_score")})
        clues += [{"text": c.get("text", ""), "code": c.get("code", it["code"]), "weight": float(c.get("weight") or 0)} for c in it.get("clues") or []]
    cands.sort(key=lambda c: (-c["confidence"], c["code"]))
    top = cands[0]["code"] if cands and rules.to100(cands[0]["confidence"]) >= rules.to100(config.th("segment_check_min", 0.5)) else None
    if top is None and cands:
        # 빠른 경로는 LLM 이 없어 낮게 나온다 — 단서가 있는 1위를 보인다(사람이 고르는 화면)
        top = cands[0]["code"] if cands[0]["confidence"] > 0 else None
    return {"candidates": cands[:5], "clues": clues[:8], "top": top, "basis": basis, "customer_name": cust}


# ── 작업 ─────────────────────────────────────────────────
def _req_items_from_preset(code: str, req_items: list[str], ins: dict[str, Any]) -> list[dict[str, Any]]:
    by_label = {r["label"]: r for r in ins.get("req_types") or []}
    out = []
    for label in req_items:
        rt = by_label.get(label) or {}
        out.append({"id": R.nid("req"), "text": label, "weight": rt.get("n"), "origin": "preset", "label": label, "code": rt.get("code")})
    return out


async def _apply_preset(doc: dict[str, Any], preset: dict[str, Any]) -> None:
    code = (preset.get("segment") or "").upper()
    if code not in config.SEGMENT_CODES:
        raise ApiError(422, "VALIDATION_FAILED", f"모르는 업종 코드예요: {code}")
    ins = await insights_for(code)
    reqs = [r for r in doc.get("requirements") or [] if r.get("origin") != "preset"]
    preset_reqs = _req_items_from_preset(code, list(preset.get("req_items") or []), ins)
    doc["requirements"] = reqs + preset_reqs
    doc["preset"] = {"segment": code, "req_items": list(preset.get("req_items") or [])}
    doc["segment"] = {**(doc.get("segment") or {}), "code": code, "mode": "pin", "confidence": None, "inherited_from": None, "mix": None}
    # 같은 항목을 비교 기준으로(출처 `업종 사례 {n}건`, 가중치 2)
    crit = [c for c in doc.get("criteria") or [] if c.get("source") != "preset"]
    names = {c["name"] for c in crit}
    for r in preset_reqs:
        if r["label"] in names:
            continue
        crit.append({"id": R.nid("crt"), "name": r["label"][:24], "source": "preset", "source_count": r.get("weight"), "weight": 2,
                     "order": len(crit), "enabled": True, "pinned": False, "requirement_id": r["id"]})
    doc["criteria"] = crit
    doc.setdefault("extracted", {})["layout_candidates"] = [f"MI-{code}-A", f"MI-{code}-B", f"MI-{code}-C"]


def _segment_from_rq_context(ctx: dict[str, Any], seg_items: list[dict[str, Any]]) -> str | None:
    """정의서 · Storyboard context.vertical(KR 업종) → ask=false 이고 Winmate 업종 하나에 대응하면 그 코드(§3.3 ②)."""
    v = (ctx or {}).get("vertical") or {}
    if not v or v.get("ask"):
        return None
    top = (v.get("top2") or [{}])[0].get("id")
    if not top:
        return None
    hits = [s["code"] for s in seg_items if top in (s.get("kr") or [])]
    return hits[0] if len(hits) == 1 else None


async def link_requirements(doc: dict[str, Any], rq_id: str, version: int | None = None) -> bool:
    snap = await rqx.snapshot(rq_id, version)
    links = doc.setdefault("links", {})
    links["requirements_id"] = rq_id
    if snap is None:
        doc.setdefault("extracted", {})["rq_pending"] = True
        return False
    rqx.fill_from_snapshot(doc, snap)
    doc.setdefault("extracted", {}).pop("rq_pending", None)
    inh = _segment_from_rq_context((snap.get("snapshot") or {}).get("context") or {}, config.segment_list())
    seg = doc.get("segment") or {}
    if inh and seg.get("mode") != "pin":
        doc["segment"] = {**seg, "code": inh, "mode": "auto", "inherited_from": "requirements", "confidence": None}
    doc["input_kind"] = doc.get("input_kind") or "요구사항"
    item_ids = [r["id"] for r in doc.get("requirements") or [] if r.get("origin") == "definition" and r.get("id")]
    await rqx.register_link(rq_id, doc["id"], title=doc.get("title") or service.default_title(doc) or "Market Intelligence",
                            route=service.route_for(doc), rq_version=int(snap.get("version") or 0), item_ids=item_ids)
    return True


@router.post("/analyses", status_code=201, response_model=Analysis, tags=["analyses"],
             responses={202: {"model": AutoRunAccepted, "description": "auto_run — 설계 → 분석 잡 사슬"}})
async def create_analysis(body: CreateAnalysisIn) -> Any:
    cust = body.customer_name or ((body.customer or {}).get("name") if body.customer else None)
    doc = service.new_doc(customer_name=(cust or None), requirements_text=body.requirements_text or "",
                          links=(body.links.model_dump(exclude_none=True) if body.links else {}), project_id=body.project_id)
    for fid in body.file_ids or []:
        doc["files"].append({"file_id": fid, "name": "", "doc_kind": "other", "classification": "internal", "include": True})
    if body.segment_pin:
        code = body.segment_pin.upper()
        if code not in config.SEGMENT_CODES and code != "GEN":
            raise ApiError(422, "VALIDATION_FAILED", f"모르는 업종 코드예요: {code}")
        doc["segment"] = {"code": code, "mode": "pin"}
    if body.preset:
        await _apply_preset(doc, body.preset.model_dump())
        doc["last_screen"] = "scope"
    if body.proposal_type:
        doc["links"]["proposal_type"] = body.proposal_type
    rq_ref = body.rq_ref or {}
    rq_id = (body.links.requirements_id if body.links else None) or rq_ref.get("rq_id")
    if body.scope:
        areas = [("user" if a == "users" else a) for a in body.scope]
        areas = [a for a in rules.AREAS if a in areas]
        doc["scope"] = {"areas": areas, "mode": "pin", "reasons": {a: "사람이 정한 범위" for a in areas}, "reduced": []}
    if body.purpose == "proposal":
        doc["extracted"]["purpose"] = "proposal"
    await R.call(R.put_analysis, doc)
    if rq_id:
        await link_requirements(doc, rq_id, rq_ref.get("version") or (body.links.rq_version if body.links else None))
        await R.call(R.put_analysis, doc)
    if body.auto_run:
        job_id = await enqueue("mi.design", {"analysis_id": doc["id"], "auto_run": True, "start_analysis": True}, doc)
        doc["status"] = "designing"
        doc["design_status"] = "running"
        doc["design_job_id"] = job_id
        await R.call(R.put_analysis, doc)
        await service.register(doc)
        return JSONResponse(status_code=202, content={"analysis_id": doc["id"], "job_id": job_id, "status": "queued"})
    await service.register(doc)
    return service.public(doc)


def _filter_status(a: dict[str, Any], status: str | None) -> bool:
    if not status or status == "all":
        return True
    st = a.get("status", "draft")
    if status == "run":
        return st in ("queued", "running")
    if status == "draft":
        return st in ("draft", "designing", "ask", "designed", "stopped", "failed")
    return st == status


def _matches_q(a: dict[str, Any], q: str | None) -> bool:
    if not q:
        return True
    ql = q.strip().lower()
    hay = [a.get("title") or "", a.get("customer_name") or ""]
    for c in a.get("competitors") or []:
        hay += [c.get("real_name") or "", c.get("letter") and f"경쟁사 {c['letter']}" or ""] + list(c.get("aliases") or [])
    return any(ql in (h or "").lower() for h in hay)


@router.get("/analyses", response_model=AnalysisList, tags=["analyses"])
async def list_analyses(limit: int = Query(20, ge=1, le=100), cursor: str | None = None, status: str | None = None,
                        segment: str | None = None, q: str | None = None, sort: str = "updated_desc",
                        has_competitors: bool | None = None) -> dict[str, Any]:
    """MI0 — 내 작업(상태 · 업종 · 검색 · 정렬) + 머리 집계 · 상태 필터 개수 · 업데이트 배너."""
    mine = await R.call(R.list_analyses, current_user().id)
    counts = {"all": len(mine), "run": 0, "done": 0, "upd": 0, "draft": 0}
    for a in mine:
        st = a.get("status", "draft")
        key = "run" if st in ("queued", "running") else ("done" if st == "done" else ("upd" if st == "upd" else "draft"))
        counts[key] += 1
    fix_open_works = sum(1 for a in mine if a.get("status") in ("done", "upd") and int((a.get("run") or {}).get("fix_open") or 0) > 0)
    items = [a for a in mine if _filter_status(a, status) and (not segment or (a.get("segment") or {}).get("code") == segment)
             and _matches_q(a, q) and (has_competitors is None or bool(anonymize.live(a.get("competitors") or [])) == has_competitors)]
    if sort == "title":
        items.sort(key=lambda a: a.get("title") or "")
    elif sort == "created_desc":
        items.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    else:
        items.sort(key=lambda a: a.get("updated_at", ""), reverse=True)
    offset = int(base64.urlsafe_b64decode(cursor.encode()).decode()) if cursor else 0
    page = items[offset:offset + limit]
    nxt = base64.urlsafe_b64encode(str(offset + limit).encode()).decode() if offset + limit < len(items) else None
    out_items = [views.list_item(a, service.route_for(a)) for a in page]
    upd = [a for a in sorted(mine, key=lambda x: x.get("updated_at", ""), reverse=True) if a.get("status") == "upd"]
    banner = None
    if upd:
        kinds = []
        for a in upd:
            for c in a.get("upd_changes") or []:
                lab = views.CHANGE_KIND_LABEL.get(c.get("kind"), "자료 변경")
                if lab not in kinds:
                    kinds.append(lab)
        canon = list(views.CHANGE_KIND_LABEL.values())
        kinds.sort(key=lambda k: canon.index(k) if k in canon else 99)
        joined = rules.join_and(kinds) or "자료 변경"
        banner = {"n": len(upd), "title": f"{len(upd)}건은 다시 분석을 권해요.",
                  "text": f"분석한 지 30일이 지났고, 그사이 {joined}{rules.josa(joined, '이', '가')} 확인됐어요.", "kinds": kinds,
                  "target_ids": [a["id"] for a in upd]}
    head = f"분석 {counts['all']}건 · 업데이트 필요 {counts['upd']}건"
    if fix_open_works:
        head += f" · 확정 필요 수치가 남은 작업 {fix_open_works}건"
    upd_changes = {a["id"]: {"title": f"바뀐 자료 {len(a.get('upd_changes') or [])}건", "summary": views.changes_summary(a.get("upd_changes") or [])}
                   for a in upd}
    return {"items": out_items, "next_cursor": nxt, "counts": counts, "upd_changes": anonymize.scrub(upd_changes, [c for a in upd for c in a.get("competitors") or []], {}),
            "fix_open_works": fix_open_works, "banner": banner, "header": head}


@router.get("/analyses/{aid}", response_model=Analysis, tags=["analyses"])
async def get_analysis(aid: str, version: int | None = None) -> dict[str, Any]:
    doc = await reconcile(await load(aid))
    out = service.public(doc)
    if version:
        v = await load_version(doc, version)
        out["result"] = views.result_view(doc, v, latest_n=int(doc.get("result_version") or 0))
    return out


async def _refresh_after_patch(doc: dict[str, Any], *, segment_changed: bool) -> None:
    if not doc.get("decisions"):
        return
    count = None
    if segment_changed:
        code = (doc.get("segment") or {}).get("code")
        if code and code != "GEN":
            try:
                count = int((await kbx.insights(code)).get("cases") or 0)
            except ApiError:
                count = None
        elif code == "GEN":
            count = 0
    service.refresh_decisions(doc, kb_case_count=count)


@router.patch("/analyses/{aid}", response_model=Analysis, tags=["analyses"])
async def patch_analysis(aid: str, body: AnalysisPatch) -> dict[str, Any]:
    doc = await load(aid)
    data = body.model_dump(exclude_unset=True)
    input_changed = False
    seg_changed = False
    if "title" in data and data["title"] is not None:
        doc["title"] = data["title"].strip()[:30]
        doc["title_pinned"] = True
    for k in ("customer_name", "requirements_text"):
        if k in data and data[k] is not None and data[k] != doc.get(k):
            doc[k] = data[k]
            input_changed = True
    if data.get("requirements") is not None:
        doc["requirements"] = [{**r, "id": r.get("id") or R.nid("req")} for r in data["requirements"]]
        input_changed = True
    if data.get("file_ids") is not None:
        keep = {f["file_id"]: f for f in doc.get("files") or []}
        doc["files"] = [keep.get(fid) or {"file_id": fid, "name": "", "doc_kind": "other", "classification": "internal", "include": True}
                        for fid in data["file_ids"]]
        input_changed = True
    if data.get("files") is not None:
        keep = {f["file_id"]: f for f in doc.get("files") or []}
        out = []
        for f in data["files"]:
            cur = dict(keep.get(f["file_id"]) or {"file_id": f["file_id"], "name": "", "doc_kind": "other", "classification": "internal", "include": True})
            cur.update({k: v for k, v in f.items() if v is not None})
            out.append(cur)
        doc["files"] = out
        input_changed = True
    if data.get("segment"):
        code = data["segment"]["code"].upper()
        if code not in config.SEGMENT_CODES and code != "GEN":
            raise ApiError(422, "VALIDATION_FAILED", f"모르는 업종 코드예요: {code}")
        seg = doc.get("segment") or {}
        cands = {c["code"]: c["confidence"] for c in seg.get("candidates") or []}
        doc["segment"] = {**seg, "code": code, "mode": "pin", "confidence": cands.get(code, seg.get("confidence") if seg.get("code") == code else None),
                          "inherited_from": None, "mix": data["segment"].get("mix")}
        seg_changed = True
    if data.get("scope"):
        areas = [a for a in rules.AREAS if a in data["scope"]["areas"]]
        sc = doc.get("scope") or {}
        doc["scope"] = {**sc, "areas": areas, "mode": "pin", "reasons": {a: "사람이 정한 범위" for a in areas},
                        "reason_text": "사람이 정한 범위", "reduced": [r for r in sc.get("reduced") or [] if r in areas]}
    if data.get("usage"):
        u = data["usage"]
        doc["usage"] = {"value": u["value"], "mode": "pin", "reason": "사람이 정한 쓰임"}
        if u.get("proposal_id"):
            doc.setdefault("links", {})["proposal_id"] = u["proposal_id"]
            doc["links"]["proposal_title"] = u.get("proposal_title")
            if u["value"] in ("standard", "solution", "quickwin"):
                doc["links"]["proposal_type"] = u["value"]
        if not doc.get("anonymize_pinned"):
            doc["anonymize"] = rules.is_customer_facing(u["value"])
    if "anonymize" in data and data["anonymize"] is not None:
        doc["anonymize"] = bool(data["anonymize"])
        doc["anonymize_pinned"] = True
    if data.get("naming_mode"):
        doc["naming_mode"] = data["naming_mode"]
        doc["anonymize_pinned"] = True
    if data.get("internal"):
        it = doc.get("internal") or {}
        for k in ("included_file_ids", "excluded_file_ids"):
            if data["internal"].get(k) is not None:
                it[k] = data["internal"][k]
        it["mode"] = "pin"
        doc["internal"] = it
    if data.get("last_screen"):
        doc["last_screen"] = data["last_screen"]
    if data.get("links"):
        doc["links"] = {**(doc.get("links") or {}), **{k: v for k, v in data["links"].items() if v is not None}}
    if data.get("preset"):
        await _apply_preset(doc, data["preset"])
        seg_changed = True
    if input_changed and doc.get("result_version"):
        doc["edit_after_analysis"] = True
    await _refresh_after_patch(doc, segment_changed=seg_changed)
    saved = await R.call(R.put_analysis, doc)
    await service.register(saved)
    return service.public(saved)


@router.delete("/analyses/{aid}", status_code=204, tags=["analyses"])
async def delete_analysis(aid: str) -> Response:
    doc = await load(aid)
    if doc.get("owner_id") != current_user().id and current_user().id != "system":
        raise ApiError(403, "FORBIDDEN", "내 작업만 지울 수 있어요")
    await R.call(R.delete_analysis, aid)
    from winmate_common.platform import unregister_item

    await unregister_item(aid)
    return Response(status_code=204)


@router.post("/analyses/{aid}/duplicate", status_code=201, response_model=Analysis, tags=["analyses"])
async def duplicate_analysis(aid: str, body: DuplicateIn) -> dict[str, Any]:
    """`복제해서 새 분석` — 범위 · 업종 · 경쟁사 · 기준이 같은 새 draft(결과 없음, AC-MI-81)."""
    src = await load(aid)
    doc = service.new_doc(customer_name=src.get("customer_name"), requirements_text=src.get("requirements_text") or "",
                          links={k: v for k, v in (src.get("links") or {}).items() if k in ("requirements_id", "rq_version", "storyboard_id", "storyboard_title")},
                          project_id=src.get("project_id"))
    for k in ("requirements", "files", "segment", "usage", "anonymize", "naming_mode", "internal", "preset", "input_kind", "extracted", "topic"):
        doc[k] = src.get(k)
    if body.keep_scope:
        doc["scope"] = src.get("scope") or doc["scope"]
    doc["competitors"] = [{**c, "id": R.nid("cmp")} for c in src.get("competitors") or []]
    doc["criteria"] = [{**c, "id": R.nid("crt")} for c in src.get("criteria") or []]
    doc["samsung_products"] = list(src.get("samsung_products") or [])
    t = src.get("title") or service.default_title(src)
    doc["title"] = (f"{t} (복제)" if t else "")[:30]
    doc["last_screen"] = "input"
    await R.call(R.put_analysis, doc)
    await service.register(doc)
    return service.public(doc)


@router.post("/analyses/{aid}/imports/storyboard", response_model=Analysis, tags=["analyses"])
async def import_storyboard(aid: str, body: StoryboardImportIn) -> dict[str, Any]:
    """웹이 Storyboard 계약으로 읽어 올린 요구사항 · Key Message · 고객 정보(mi 는 storyboard 를 부를 수 없음, §8)."""
    doc = await load(aid)
    links = doc.setdefault("links", {})
    links["storyboard_id"] = body.storyboard_id
    links["storyboard_title"] = body.title
    if body.customer_name and not doc.get("customer_name"):
        doc["customer_name"] = body.customer_name[:60]
    reqs = [r for r in doc.get("requirements") or [] if r.get("origin") != "storyboard"]
    for r in body.requirements:
        reqs.append({"id": r.id or R.nid("req"), "text": r.text, "weight": r.weight, "origin": "storyboard", "label": r.label})
    doc["requirements"] = reqs
    if not (doc.get("requirements_text") or "").strip():
        doc["requirements_text"] = "\n".join(r.text for r in body.requirements)[:4000]
    ext = doc.setdefault("extracted", {})
    ext["key_messages"] = body.key_messages
    ext["research_topics"] = body.research_topics
    if body.segment:
        code = body.segment.upper()
        seg = doc.get("segment") or {}
        if code in config.SEGMENT_CODES and seg.get("mode") != "pin":
            doc["segment"] = {**seg, "code": code, "mode": "auto", "inherited_from": "storyboard", "confidence": None}
    doc["input_kind"] = doc.get("input_kind") or "요구사항"
    if doc.get("result_version"):
        doc["edit_after_analysis"] = True
    saved = await R.call(R.put_analysis, doc)
    await service.register(saved)
    return service.public(saved)


@router.post("/analyses/{aid}/imports/requirements", response_model=Analysis, tags=["analyses"])
async def import_requirements(aid: str, body: RequirementsImportIn) -> dict[str, Any]:
    doc = await load(aid)
    ok = await link_requirements(doc, body.requirements_id, body.rq_version)
    saved = await R.call(R.put_analysis, doc)
    await service.register(saved)
    if not ok:
        out = service.public(saved)
        return out
    return service.public(saved)


@router.get("/analyses/{aid}/versions", response_model=VersionList, tags=["analyses"])
async def list_versions(aid: str) -> dict[str, Any]:
    doc = await load(aid)
    cur = int(doc.get("result_version") or 0)
    items = await R.call(R.list_versions, aid)
    return {"items": [{"n": int(v.get("n") or 0), "kind": v.get("kind", ""), "created_at": v.get("created_at", ""), "created_by": v.get("created_by", ""),
                       "stopped": bool(v.get("stopped")), "summary": v.get("summary", ""), "current": int(v.get("n") or 0) == cur} for v in items]}


@router.post("/analyses/{aid}/versions/{n}/restore", response_model=Analysis, tags=["analyses"])
async def restore_version(aid: str, n: int) -> dict[str, Any]:
    """되돌리기 = 내용이 v{n} 과 같은 새 버전(kind=restore, AC-MI-80)."""
    from . import versions

    doc = await load(aid)
    old = await load_version(doc, n)
    new_n = await versions.save_new_version(doc, old, kind="restore", summary=f"v{n} 되돌리기")
    doc = await load(aid)
    out = service.public(doc)
    out["version"] = new_n
    return out


@router.post("/analyses/{aid}/additions", response_model=AdditionsOut, tags=["analyses"])
async def add_from_topbar(aid: str, body: AdditionsIn) -> dict[str, Any]:
    """TopBar `현재 작업에 추가`(셸 onAdd) — 제품 · 솔루션은 비교표 `삼성` 쪽, 사례는 사내 사례 DB 출처 후보(§6.13)."""
    if body.kind == "image":
        raise ApiError(422, "UNSUPPORTED_KIND", "이미지는 Market Intelligence 작업에 넣지 않아요")
    doc = await load(aid)
    added: list[str] = []
    if body.kind in ("product", "solution"):
        prods = list(doc.get("samsung_products") or [])
        have = {p.get("ref") for p in prods}
        for ref in body.ids:
            if ref in have:
                added.append(ref)
                continue
            parts = ref.split(":")
            kind = parts[1] if len(parts) >= 3 else ("solution" if body.kind == "solution" else "model")
            ident = parts[-1]
            name = ident
            model_code = family_id = None
            if kind == "model":
                model_code = ident.removeprefix("mdl_")
                m = await kbx.model(model_code)
                name = (m or {}).get("display_name") or (m or {}).get("name") or model_code
                family_id = (m or {}).get("family_id")
            elif kind == "family":
                family_id = ident
                hits = await kbx.product_search(ident, 1)
                name = (hits[0].get("family_name") if hits else None) or ident
            elif kind == "solution":
                s = await kbx.solution(ident)
                name = (s or {}).get("name") or ident
            prods.append({"model_code": model_code, "family_id": family_id, "name": name, "ref": ref,
                          "kind": "solution" if kind == "solution" else ("family" if kind == "family" else "model"), "origin": "topbar"})
            added.append(ref)
        doc["samsung_products"] = prods
    else:
        cases = list((doc.get("extracted") or {}).get("extra_cases") or [])
        for ref in body.ids:
            cid = ref.split(":")[-1]
            if cid not in cases:
                cases.append(cid)
            added.append(ref)
        doc.setdefault("extracted", {})["extra_cases"] = cases
    if doc.get("result_version"):
        doc["edit_after_analysis"] = True
    await R.call(R.put_analysis, doc)
    return {"added": added}


# ── 설계 ─────────────────────────────────────────────────
async def start_design(doc: dict[str, Any], *, memo: str | None = None, start_analysis: bool = False) -> str:
    if doc.get("design_job_id") and await job_active(doc["design_job_id"]):
        try:
            await jobs().cancel(doc["design_job_id"])
        except Exception:  # noqa: BLE001
            pass
    job_id = await enqueue("mi.design", {"analysis_id": doc["id"], "memo": memo, "start_analysis": start_analysis}, doc)
    doc["design_job_id"] = job_id
    doc["design_status"] = "running"
    doc["design_ask"] = None
    doc["design_error"] = None
    if doc.get("status") in ("draft", "designed", "ask", "stopped", "failed", "designing"):
        doc["status"] = "designing"
    await R.call(R.put_analysis, doc)
    await service.register(doc)
    return job_id


@router.post("/analyses/{aid}/design", status_code=202, response_model=JobAccepted, tags=["design"])
async def run_design(aid: str) -> dict[str, Any]:
    """`다음 · 분석 설계` — 잡 mi.design. 이미 돌고 있으면 취소 후 새로."""
    doc = await load(aid)
    has_input = bool((doc.get("customer_name") or "").strip() or (doc.get("requirements_text") or "").strip() or doc.get("files")
                     or doc.get("requirements") or (doc.get("links") or {}).get("storyboard_id") or (doc.get("segment") or {}).get("mode") == "pin")
    if not has_input:
        raise ApiError(422, "VALIDATION_FAILED", "고객사 · 요구사항 · 파일 중 하나는 있어야 설계할 수 있어요")
    return {"job_id": await start_design(doc), "status": "queued"}


@router.get("/analyses/{aid}/design", response_model=DesignView, tags=["design"])
async def get_design(aid: str) -> dict[str, Any]:
    doc = await load(aid)
    return service.design_view(doc)


@router.post("/analyses/{aid}/design/memo", status_code=202, response_model=JobAccepted, tags=["design"])
async def design_memo(aid: str, body: MemoIn) -> dict[str, Any]:
    """설계에 덧붙일 말 · MI1Q `판단에 도움이 될 말` — 업종 두 갈래로 기다리는 중이면 같은 잡에 힌트로 넣어 업종 판별만 다시."""
    doc = await load(aid)
    doc.setdefault("memos", []).append({"text": body.text, "at": now_iso(), "where": "design"})
    await R.call(R.put_analysis, doc)
    jid = doc.get("design_job_id")
    if jid:
        j = await jobs().get(jid)
        if j and j.status == "awaiting_input":
            await jobs().add_memo(jid, body.text)
            await jobs().provide_input(jid, {"hint": body.text})
            await R.call(R.patch_analysis, aid, {"design_status": "running"})
            return {"job_id": jid, "status": "queued"}
    return {"job_id": await start_design(doc, memo=body.text), "status": "queued"}


# ── 경쟁사 · 기준 ────────────────────────────────────────
@router.get("/analyses/{aid}/competitors", response_model=CompetitorList, tags=["competitors"])
async def list_competitors(aid: str) -> dict[str, Any]:
    doc = await load(aid)
    pub = service.competitors_public(doc)
    live = [c for c in pub if not c.get("removed")]
    return {"items": live, "removed": [c for c in pub if c.get("removed")],
            "counts": {"auto": sum(1 for c in live if c.get("origin") in ("auto", "mi_rfp")), "user": sum(1 for c in live if c.get("origin") == "user"),
                       "total": len(live)}}


def _norm_name(name: str) -> str:
    import re

    n = re.sub(r"\(주\)|㈜|주식회사|\s*inc\.?$|\s*co\.,?\s*ltd\.?$", "", name.strip(), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", n).strip()


@router.post("/analyses/{aid}/competitors", status_code=202, response_model=CompetitorAccepted, tags=["competitors"])
async def add_competitor(aid: str, body: CompetitorAddIn) -> dict[str, Any]:
    """직접 추가 — 행을 바로 넣고(`직접 추가`, 고정) 짧은 잡이 이름 정규화 · 유형 · 한 줄 설명을 찾는다."""
    doc = await load(aid)
    name = _norm_name(body.name)
    for c in doc.get("competitors") or []:
        if _norm_name(c.get("real_name", "")).lower() == name.lower() or name.lower() in [a.lower() for a in c.get("aliases") or []]:
            if c.get("removed"):
                c["removed"] = False
                c["pinned"] = True
                await R.call(R.put_analysis, doc)
                return {"job_id": "", "competitor_id": c["id"], "status": "queued"}
            raise ApiError(409, "DUPLICATE_COMPETITOR", "이미 있는 경쟁사예요", {"competitor_id": c["id"]})
    comps = doc.setdefault("competitors", [])
    used = {c.get("letter") for c in comps}
    letter = next(l for l in rules.letters(len(comps) + 27) if l not in used)
    cmp_id = R.nid("cmp")
    comps.append({"id": cmp_id, "letter": letter, "real_name": name, "aliases": [], "kind_label": "", "desc": "", "origin": "user",
                  "confidence": None, "pinned": True, "removed": False, "evidence_source_ids": [], "order": len(comps), "lookup": "pending"})
    if doc.get("decisions"):
        service.refresh_decisions(doc)
    await R.call(R.put_analysis, doc)
    job_id = await enqueue("mi.competitor_add", {"analysis_id": aid, "competitor_id": cmp_id}, doc, title=f"경쟁사 확인 · {name}")
    return {"job_id": job_id, "competitor_id": cmp_id, "status": "queued"}


@router.patch("/analyses/{aid}/competitors/{cmp}", response_model=Competitor, tags=["competitors"])
async def patch_competitor(aid: str, cmp: str, body: CompetitorPatch) -> dict[str, Any]:
    doc = await load(aid)
    target = next((c for c in doc.get("competitors") or [] if c["id"] == cmp), None)
    if target is None:
        raise service.not_found("경쟁사", cmp)
    if body.removed is not None:
        target["removed"] = bool(body.removed)
    if body.order is not None:
        target["order"] = int(body.order)
    target["pinned"] = True
    if doc.get("decisions"):
        service.refresh_decisions(doc)
    await R.call(R.put_analysis, doc)
    return next(c for c in service.competitors_public(doc) if c["id"] == cmp)


async def _criteria_view(doc: dict[str, Any]) -> dict[str, Any]:
    seg = (doc.get("segment") or {}).get("code")
    items = service.criteria_with_pct(doc.get("criteria") or [])
    sugg: list[dict[str, Any]] = []
    head = ""
    if seg and seg != "GEN":
        ins = await insights_for(seg)
        names = {c["name"] for c in items}
        for rt in ins.get("req_types") or []:
            if rt["label"] not in names:
                sugg.append({"name": rt["label"], "n": rt["n"]})
            if len(sugg) >= 2:
                break
        head = f"{ins['short']} 도입사례 {ins['cases']}건에서 많이 요구된 기준"
    return {"items": items, "suggestions": sugg, "suggestion_head": head}


@router.get("/analyses/{aid}/criteria", response_model=CriteriaList, tags=["competitors"])
async def get_criteria(aid: str) -> dict[str, Any]:
    return await _criteria_view(await load(aid))


@router.put("/analyses/{aid}/criteria", response_model=CriteriaList, tags=["competitors"])
async def put_criteria(aid: str, body: CriteriaPut) -> dict[str, Any]:
    """비교 기준 · 가중치(1~5) · 순서 · 켜기. 비율은 서버가 다시 계산(합계 100%)."""
    doc = await load(aid)
    old = {c["id"]: c for c in doc.get("criteria") or []}
    out = []
    for i, it in enumerate(body.items):
        prev = old.get(it.id or "") or {}
        out.append({**prev, "id": it.id or R.nid("crt"), "name": it.name.strip(), "source": it.source if not prev else prev.get("source", it.source),
                    "source_count": it.source_count if it.source_count is not None else prev.get("source_count"), "weight": int(it.weight),
                    "order": it.order if it.order is not None else i, "enabled": it.enabled, "pinned": True})
    doc["criteria"] = out
    if doc.get("result_version"):
        doc["edit_after_analysis"] = True
    await R.call(R.put_analysis, doc)
    return await _criteria_view(doc)


# ── 실행 · 진행 ──────────────────────────────────────────
@router.post("/analyses/{aid}/runs", status_code=202, response_model=JobAccepted, tags=["runs"])
async def run_analysis(aid: str, body: RunIn | None = None) -> dict[str, Any]:
    """잡 mi.analyze. mode: full(전부 다시) · changed_only(바뀐 영역 + areas) · resume(정리 못 한 영역) · 생략 = 의존 해시로 바뀐 것만."""
    body = body or RunIn()
    doc = await load(aid)
    areas = list(body.areas or [])
    if body.mode == "changed_only" and not areas:
        # MI0 `{n}건 다시 분석` · 행 `다시 분석` — 재확인이 찾은 변경의 영향 영역(§4.2)
        hit = {x for c in doc.get("upd_changes") or [] for x in c.get("affected_areas") or []}
        areas = [a for a in rules.AREAS if a in hit]
    return {"job_id": await start_run(doc, body.mode, areas), "status": "queued"}


@router.get("/analyses/{aid}/progress", response_model=RunProgress, tags=["runs"])
async def get_progress(aid: str) -> dict[str, Any]:
    """MI3G 첫 그림 · 다시 들어올 때(제안) — 마지막 step/progress 스냅숏. 실시간은 jobs SSE."""
    doc = await reconcile(await load(aid))
    draft = await R.call(R.get_draft, aid) or {}
    prog = dict(draft.get("progress") or {})
    prog["job_id"] = doc.get("current_job_id") or prog.get("job_id")
    prog["status"] = doc.get("status", "draft")
    prog.setdefault("memos", [m for m in doc.get("memos") or [] if m.get("where") == "run"])
    if not prog.get("areas"):
        prog["areas"] = [{"area": a, "name": rules.AREA_TAB[a], "status": "wait", "note": ""} for a in service.areas_of(doc)]
    if not prog.get("stages"):
        prog["stages"] = [{"stage": s, "name": n, "status": "wait", "note": ""} for s, n in (("search", "검색"), ("organize", "정리"), ("write", "작성"))]
    from .graphs.analyze import run_header

    prog.update(run_header(doc))
    return prog
