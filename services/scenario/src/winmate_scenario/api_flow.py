"""scenario API (/v1) — 입력 파싱 · 등장인물 · 타임라인 편집 · 솔루션/제품 · 연관 제품 추천(R5) · 장면별 추천(SC3R) · 생성(SC4G)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query
from winmate_common.errors import ApiError
from winmate_common.jobs import jobs

from . import birdseye as be
from . import compose, kbq, prompts, repo, seed, service, texts
from . import models as m
from . import timeline as tl

log = logging.getLogger("winmate.scenario.api")
router = APIRouter(prefix="/v1")
TAG = ["scenarios"]


async def _job_busy(doc: dict[str, Any], kinds: tuple[str, ...]) -> str | None:
    aj = doc.get("active_job") or {}
    if aj.get("job_id") and aj.get("kind") in kinds:
        job = await jobs().get(aj["job_id"])
        if job and job.status in ("queued", "running"):
            return aj["job_id"]
    return None


# ── 입력(SC2) ─────────────────────────────────────────────

@router.post("/scenarios/{sc_id}/input:parse", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def parse_input(sc_id: str, body: m.ParseRequest) -> m.JobAccepted:
    doc = await repo.require_sc(sc_id)
    service.require_editable(doc)
    busy = await _job_busy(doc, ("parse",))
    if busy:
        return m.JobAccepted(job_id=busy, status="running")
    job_id = await service.enqueue("sc.parse_input", doc, {"raw_text": body.raw_text, "characters": body.characters})

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["raw_text"] = body.raw_text
        d["characters"] = body.characters
        service.set_active(d, job_id, "parse")
        return d
    await repo.update(sc_id, fn)
    return m.JobAccepted(job_id=job_id)


@router.post("/scenarios/{sc_id}/characters:extract", response_model=m.Characters, tags=TAG)
async def extract_characters(sc_id: str, body: m.ExtractRequest) -> m.Characters:
    """입력이 멈추고 1초 뒤(웹) — LLM 이 문장에서 역할을 뽑는다(제한 5초, 실패하면 등장인물 사전). 사용자가 지운 역할은 빼고 준다."""
    doc = await repo.require_sc(sc_id)
    exclude = list(dict.fromkeys([*body.exclude, *(doc.get("removed_characters") or [])]))
    names, source = await compose.extract_characters(body.raw_text, customer=doc.get("customer_name"), exclude=exclude)
    return m.Characters(characters=names, source=source)  # type: ignore[arg-type]


# ── 타임라인(SC2E) ──────────────────────────────────────────

def _timeline(doc: dict[str, Any], job_id: str | None = None) -> m.Timeline:
    v = tl.view(doc)
    aj = doc.get("active_job") or {}
    return m.Timeline(**v, rewriting_role_ids=[r["id"] for r in doc.get("roles") or [] if r.get("rewriting")],
                      job_id=job_id or (aj.get("job_id") if aj.get("kind") in ("timeline_edit", "lane_rewrite") else None))


@router.get("/scenarios/{sc_id}/timeline", response_model=m.Timeline, tags=TAG)
async def get_timeline(sc_id: str) -> m.Timeline:
    return _timeline(await repo.require_sc(sc_id))


@router.post("/scenarios/{sc_id}/timeline/ops", response_model=m.Timeline, tags=TAG)
async def timeline_ops(sc_id: str, body: m.TimelineOpsRequest) -> m.Timeline:
    """편집 즉시 저장(되돌리기 50단계). undo · redo 는 ops 없이."""
    ops = [o.model_dump(exclude_none=True) for o in body.ops]

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        service.require_editable(d)
        if body.undo:
            if not tl.undo(d):
                return None
        elif body.redo:
            if not tl.redo(d):
                return None
        elif ops:
            tl.apply_ops(d, ops)
        else:
            return None
        tl.normalize(d)
        d["via_timeline"] = True
        if int(d.get("step") or 1) < 2:
            d["step"] = 2
        d["dirty"] = True
        return d
    doc = await repo.update(sc_id, fn)
    return _timeline(doc)


@router.post("/scenarios/{sc_id}/timeline:nl-edit", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def timeline_nl_edit(sc_id: str, body: m.TextRequest) -> m.JobAccepted:
    doc = await repo.require_sc(sc_id)
    service.require_editable(doc)
    job_id = await service.enqueue("sc.timeline_edit", doc, {"text": body.text})

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.set_active(d, job_id, "timeline_edit")
        return d
    await repo.update(sc_id, fn)
    return m.JobAccepted(job_id=job_id)


@router.patch("/scenarios/{sc_id}/roles/{role_id}", response_model=m.Timeline, tags=TAG)
async def patch_role(sc_id: str, role_id: str, body: m.PatchRole) -> m.Timeline:
    """페르소나 저장 — 소개 · 원하는 것 · 불편한 점이 바뀌면 그 레인 비트 문장 재작성 잡(응답 job_id)."""
    data = body.model_dump(exclude_unset=True)
    persona_changed = [False]

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.require_editable(d)
        r = tl.role_by_id(d, role_id)
        if r is None:
            raise ApiError(404, "NOT_FOUND", "역할을 찾을 수 없어요")
        persona_changed[0] = any(k in data and data[k] is not None and data[k] != r.get(k) for k in ("intro", "wants", "pains"))
        tl.apply_ops(d, [{"op": "set_role", "role_id": role_id, **data}])
        d["dirty"] = True
        return d
    doc = await repo.update(sc_id, fn)
    job_id = None
    has_beats = any(b.get("role_id") == role_id for s in doc.get("scenes") or [] for b in s.get("beats") or [])
    if persona_changed[0] and has_beats:
        job_id = await service.enqueue("sc.lane_rewrite", doc, {"role_id": role_id})

        def mark(d: dict[str, Any]) -> dict[str, Any]:
            r = tl.role_by_id(d, role_id)
            if r:
                r["rewriting"] = True
            service.set_active(d, job_id, "lane_rewrite")
            return d
        doc = await repo.update(sc_id, mark)
    return _timeline(doc, job_id)


@router.get("/scenarios/{sc_id}/timeline:text", response_model=m.TimelineText, tags=TAG)
async def timeline_text(sc_id: str) -> m.TimelineText:
    return m.TimelineText(raw_text=tl.to_text(await repo.require_sc(sc_id)))


# ── 솔루션 · 제품(SC3) ──────────────────────────────────────

async def compute_related(doc: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    """R5 연관 제품: KB D5(솔루션 공존, lift 순) ∩ C2(장면 공간 후보) + 시나리오 문장 언급(A1) → 최대 3, 이미 고른 것 제외."""
    if doc.get("type") != "with" or not doc.get("solution_picks"):
        return [], None
    first = doc["solution_picks"][0]
    sol = seed.solution(first["solution_id"]) or {}
    kb_ids = [(seed.solution(p["solution_id"]) or {}).get("kb_id") for p in doc["solution_picks"]]
    co = await kbq.d5([["solution", k] for k in kb_ids if k])
    co.sort(key=lambda x: -(x.get("lift") or 0))
    ind = seed.industry(doc.get("vertical_code"))
    vertical = ((ind or {}).get("kr_verticals") or [None])[0]
    place_text = " ".join([doc.get("space_label") or "", *(s.get("place") or "" for s in doc.get("scenes") or [])])
    space_links = await kbq.a1(place_text) if place_text.strip() else []
    space = next((lk.get("id") for lk in space_links if lk.get("type") == "space_type"), None)
    fams = await kbq.c2(space=space, vertical=vertical, limit=30)
    fam_ids = {f["id"]: f for f in fams}
    picked = {p.get("family_id") for p in doc.get("product_picks") or [] if p.get("family_id")}
    picked_labels = {(p.get("short") or "").lower() for p in doc.get("product_picks") or []} | \
                    {(p.get("label") or "").lower() for p in doc.get("product_picks") or []}
    out: list[dict[str, Any]] = []

    def add(fid: str | None, name: str, why: str, model: str | None = None) -> None:
        if len(out) >= 3:
            return
        if fid and (fid in picked or any(o.get("family_id") == fid for o in out)):
            return
        if name.lower() in picked_labels or any(o["label"] == name for o in out):
            return
        out.append({"ref": f"kb:family:{fid}" if fid else None, "family_id": fid, "model_code": model, "label": name, "short": name, "why": why})

    for item in co:
        if item.get("kind") == "family" and item.get("id") in fam_ids:
            add(item["id"], item.get("name") or fam_ids[item["id"]]["name"], f"{sol.get('name', '')} 함께 쓰인 제품 · 공간 후보")
        elif item.get("kind") == "category":
            hit = next((f for f in fams if f.get("category") == item.get("name") and f["id"] not in picked), None)
            if hit:
                add(hit["id"], hit["name"], f"{sol.get('name', '')} 함께 쓰인 {item.get('name')}")
    # 시나리오 문장 언급(「태블릿으로 재고 확인」 → 갤럭시 탭)
    text = " ".join([doc.get("raw_text") or "", *(b.get("text") or "" for s in doc.get("scenes") or [] for b in s.get("beats") or [])])
    for lk in await kbq.a1(text):
        if lk.get("type") not in ("category", "family"):
            continue
        if lk.get("type") == "family":
            add(lk["id"], lk.get("name") or lk.get("surface") or "", "시나리오 문장 언급")
            continue
        cands = await kbq.c2(category=lk["id"], vertical=vertical, text=lk.get("surface"), limit=3)
        if cands:
            add(cands[0]["id"], cands[0]["name"], f"시나리오 문장 언급 · {lk.get('surface')}")
    return out[:3], sol.get("name") if out else None


@router.put("/scenarios/{sc_id}/solutions", response_model=m.SolutionsResult, tags=TAG)
async def put_solutions(sc_id: str, body: m.PutSolutions) -> m.SolutionsResult:
    catalog = {s["id"]: s for s in await kbq.solutions_catalog()}
    picks = []
    for i, it in enumerate(body.items):
        s = seed.solution(it.solution_id) or seed.solution_by_name(it.name or it.solution_id)
        sid = (s or {}).get("id") or it.solution_id
        name = (s or {}).get("name") or (catalog.get(sid) or {}).get("name") or it.name or sid
        if not any(p["solution_id"] == sid for p in picks):
            picks.append({"solution_id": sid, "name": name, "source": "user", "ord": i})

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.require_editable(d)
        prev = {p["solution_id"]: p for p in d.get("solution_picks") or []}
        d["solution_picks"] = [{**p, "source": prev.get(p["solution_id"], {}).get("source") or p["source"]} for p in picks]
        d["dirty"] = True
        if int(d.get("step") or 1) < 3:
            d["step"] = 3
        return d
    doc = await repo.update(sc_id, fn)
    related, rel_for = await compute_related(doc)

    def fr(d: dict[str, Any]) -> dict[str, Any]:
        d["related_products"] = related
        d["related_for"] = rel_for
        return d
    doc = await repo.update(sc_id, fr)
    await service.register(doc)
    return m.SolutionsResult(solution_picks=doc["solution_picks"], related_products=related, related_for=rel_for)


@router.put("/scenarios/{sc_id}/products", response_model=m.ProductsResult, tags=TAG)
async def put_products(sc_id: str, body: m.PutProducts) -> m.ProductsResult:
    picks = []
    for i, it in enumerate(body.items):
        label, short, fam, code = (it.label or "").strip(), (it.short or "").strip(), it.family_id, it.model_code
        if not label and it.ref and it.ref.startswith("kb:"):
            # 셸 팝오버 「현재 작업에 추가」는 참조만 준다 → KB 에서 표시명 · 제품군을 찾는다
            kind, _, key = it.ref[3:].partition(":")
            det = await kbq.model_detail(key) or {}
            fam_ref = det.get("family") or {}
            if kind == "family":
                label = fam_ref.get("name") or det.get("display_name") or key
                fam = fam or key
            else:
                label = det.get("label_en") or det.get("display_name") or det.get("model_code") or key
                short = short or det.get("display_name") or ""
                code = code or det.get("model_code")
                fam = fam or fam_ref.get("id")
        if not label:
            label = (it.ref or "").split(":")[-1] or "제품"
        short = short or label
        picks.append({"ref": it.ref, "family_id": fam, "model_code": code, "label": label, "short": short,
                      "qty": it.qty, "source": it.source, "ord": i})

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.require_editable(d)
        d["product_picks"] = picks
        keys = {service.product_key(p) for p in picks} | {(p.get("label") or "").lower() for p in picks}
        d["related_products"] = [r for r in d.get("related_products") or []
                                 if service.product_key(r) not in keys and (r.get("label") or "").lower() not in keys]
        d["dirty"] = True
        if int(d.get("step") or 1) < 3:
            d["step"] = 3
        return d
    doc = await repo.update(sc_id, fn)
    return m.ProductsResult(product_picks=doc["product_picks"], related_products=doc.get("related_products") or [])


@router.get("/solution-search", response_model=m.SearchResult, tags=["catalog"])
async def solution_search(q: str = "", limit: int = Query(8, ge=1, le=20)) -> m.SearchResult:
    """「솔루션 입력」 자동완성: KB 솔루션 카탈로그(Winmate 솔루션 11개) + 동작 사전 솔루션."""
    ql = q.strip().lower()
    items: list[m.SearchHit] = []
    seen: set[str] = set()
    for s in await kbq.solutions_catalog():
        hay = f"{s.get('name')} {s.get('id')} {s.get('desc')}".lower()
        if ql and ql not in hay:
            continue
        local = seed.solution(s["id"])
        items.append(m.SearchHit(id=s["id"], ref=f"kb:solution:{s['id']}", label=(local or {}).get("name") or s["name"], short=(local or {}).get("name") or s["name"],
                                 sub=s.get("desc") or s.get("domain") or "", kind="solution"))
        seen.add(s["id"])
    for s in seed.solutions():
        if s["id"] in seen or (ql and ql not in s["name"].lower() and ql not in s["id"]):
            continue
        items.append(m.SearchHit(id=s["id"], ref=f"kb:solution:{s['id']}", label=s["name"], short=s["name"],
                                 sub=" · ".join(a["label"] for a in s["actions"]), kind="solution"))
    return m.SearchResult(items=items[:limit])


@router.get("/product-search", response_model=m.SearchResult, tags=["catalog"])
async def product_search(q: str = "", limit: int = Query(5, ge=1, le=20)) -> m.SearchResult:
    out = []
    for it in await kbq.products_search(q, limit=limit):
        out.append(m.SearchHit(id=it["id"], ref=f"kb:{it['kind']}:{it['id']}", label=it.get("label") or it.get("display_name"),
                               short=it.get("display_name") or it.get("label"), sub=it.get("meta_line") or "",
                               family_id=it.get("family_id"), model_code=it.get("model_code"), kind=it["kind"]))
    return m.SearchResult(items=out)


# ── 라우팅(R4) ─────────────────────────────────────────────

def _needs_solution_scenes(doc: dict[str, Any]) -> list[int]:
    nos = []
    for sc in tl.scenes(doc):
        line = prompts.line_for_slot(doc, tl.slot_by_id(doc, sc["slot_id"]))
        text = " ".join([line, *(b.get("text") or "" for b in sc.get("beats") or [])])
        hits = seed.match_actions(text)
        if hits and not hits[0]["optional"]:
            nos.append(sc["no"])
    return nos


async def ensure_aerial_draft(doc: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    """조감도 추가 「새로 만들기」: 공간 · 제품이 정해진 뒤 birdseye 에 조감도 초안을 한 번만 만든다(SC3 제출 · SC4 「조감도 연결」)."""
    sc_id = doc["id"]
    aerial = doc.get("aerial") or {}
    if not (aerial.get("enabled") and aerial.get("source") == "new" and not aerial.get("birdseye_id")):
        return None, doc
    desc = texts.join([doc.get("customer_name") or "", doc.get("space_label") or "", *(s.get("place") or "" for s in tl.scenes(doc))])
    created = await be.create(f"{doc.get('title') or '공간 시나리오'} 조감도", desc,
                              [p["family_id"] for p in doc.get("product_picks") or [] if p.get("family_id")], sc_id, doc.get("project_id"))
    if not (created and created.get("id")):
        return None, doc
    aerial_id = created["id"]

    def fa(d: dict[str, Any]) -> dict[str, Any]:
        a = d.get("aerial") or {}
        a.update({"birdseye_id": aerial_id, "created": True, "title": created.get("title") or a.get("title")})
        d["aerial"] = a
        return d
    return aerial_id, await repo.update(sc_id, fa)


@router.post("/scenarios/{sc_id}:route-generate", response_model=m.RouteResult, tags=TAG)
async def route_generate(sc_id: str) -> m.RouteResult:
    """SC3 「시나리오 생성」: WITHOUT 인데 솔루션이 필요한 장면이 있거나 WITH 인데 솔루션 0개 → SC3R, 그 밖 → SC4G.
    조감도 추가 「새로 만들기」면 이때 조감도 초안을 만든다(공간 · 제품이 정해진 뒤, 한 번만)."""
    doc = await repo.require_sc(sc_id)
    service.require_editable(doc)
    if not doc.get("scenes"):
        raise ApiError(400, "NO_SCENES", "장면이 없어요. 공간 시나리오를 먼저 입력해 주세요.")
    if not doc.get("product_picks") and not (doc.get("type") == "with" and doc.get("solution_picks")):
        raise ApiError(400, "NOTHING_SELECTED", "제품을 하나 이상 넣어 주세요" if doc.get("type") != "with" else "솔루션이나 제품을 넣어 주세요")
    aerial_id, doc = await ensure_aerial_draft(doc)

    def fs(d: dict[str, Any]) -> dict[str, Any]:
        tl.settle(d)
        d["step"] = 3
        return d
    doc = await repo.update(sc_id, fs)
    if doc.get("type") == "with" and not doc.get("solution_picks"):
        nxt, reason = "SC3R", "no_solution"
    elif doc.get("type") != "with" and _needs_solution_scenes(doc):
        nxt, reason = "SC3R", "solution_needed"
    else:
        nxt, reason = "SC4G", None
    if nxt == "SC3R":
        def fr(d: dict[str, Any]) -> dict[str, Any]:
            rec = d.get("recommendation") or {}
            rec["entered_with_type"] = d.get("type")
            rec.setdefault("status", "none")
            d["recommendation"] = rec
            return d
        await repo.update(sc_id, fr)
    return m.RouteResult(next=nxt, reason=reason, aerial_birdseye_id=aerial_id)  # type: ignore[arg-type]


# ── 장면별 추천(SC3R) ──────────────────────────────────────

def _recs(doc: dict[str, Any]) -> m.Recommendations:
    rec = doc.get("recommendation") or {}
    items = []
    needs: set[int] = set()
    for it in rec.get("items") or []:
        sc = tl.scene_by_id(doc, it["scene_id"])
        if sc is None:
            continue
        slot = tl.slot_by_id(doc, sc["slot_id"]) or {}
        label = slot.get("label") or ""
        first = it.get("title_line") or (sc["beats"][0]["text"] if sc.get("beats") else "")
        title = sc.get("title") or f"{label} — {first}"
        items.append(m.Recommendation(
            scene_id=sc["id"], no=sc["no"], time=slot.get("time"), label=label, title=title, product_only_text=it.get("product_only_text") or "",
            evidence=[m.Evidence(**e) for e in it.get("evidence") or []], solution_id=it["solution_id"], action_code=it["action_code"],
            solution_label=seed.action_label(it["solution_id"], it["action_code"]), benefit=it.get("benefit") or "", tag=it["tag"],
            tag_label=service.TAG_LABEL[it["tag"]], applied=bool(it.get("applied"))))
        if it.get("needs_solution") or it["tag"] == "required":
            needs.add(sc["no"])
    items.sort(key=lambda x: x.no)
    applied = [x for x in items if x.applied]
    sol_names = []
    for x in applied:
        nm = (seed.solution(x.solution_id) or {}).get("name") or x.solution_id
        if nm not in sol_names:
            sol_names.append(nm)
    ind = seed.industry(doc.get("vertical_code"))
    aj = doc.get("active_job") or {}
    status = rec.get("status") or "none"
    if aj.get("kind") == "recommend":
        status = "computing"
    return m.Recommendations(
        status=status, job_id=rec.get("job_id") or (aj.get("job_id") if aj.get("kind") == "recommend" else None), items=items,
        applied_count=len(applied), product_only_count=len(items) - len(applied),
        required_nos=sorted(needs), industry_name=ind["short"] if ind else None,
        entered_with_type=rec.get("entered_with_type"), applied_solutions=sol_names, off_nos=[x.no for x in items if not x.applied])


@router.post("/scenarios/{sc_id}/recommendations:compute", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def compute_recommendations(sc_id: str) -> m.JobAccepted:
    doc = await repo.require_sc(sc_id)
    busy = await _job_busy(doc, ("recommend",))
    if busy:
        return m.JobAccepted(job_id=busy, status="running")
    job_id = await service.enqueue("sc.recommend", doc, {})

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        rec = d.get("recommendation") or {}
        rec["status"] = "computing"
        rec["job_id"] = job_id
        rec.setdefault("entered_with_type", d.get("type"))
        d["recommendation"] = rec
        service.set_active(d, job_id, "recommend")
        return d
    await repo.update(sc_id, fn)
    return m.JobAccepted(job_id=job_id)


@router.get("/scenarios/{sc_id}/recommendations", response_model=m.Recommendations, tags=TAG)
async def get_recommendations(sc_id: str) -> m.Recommendations:
    return _recs(await repo.require_sc(sc_id))


@router.patch("/scenarios/{sc_id}/recommendations/{scene_id}", response_model=m.Recommendations, tags=TAG)
async def patch_recommendation(sc_id: str, scene_id: str, body: m.PatchRecommendation) -> m.Recommendations:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for it in (d.get("recommendation") or {}).get("items") or []:
            if it["scene_id"] == scene_id:
                it["applied"] = body.applied
                return d
        raise ApiError(404, "NOT_FOUND", "그 장면의 추천이 없어요")
    return _recs(await repo.update(sc_id, fn))


@router.post("/scenarios/{sc_id}/recommendations:apply-all", response_model=m.Recommendations, tags=TAG)
async def apply_all(sc_id: str) -> m.Recommendations:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for it in (d.get("recommendation") or {}).get("items") or []:
            it["applied"] = True
        return d
    return _recs(await repo.update(sc_id, fn))


@router.post("/scenarios/{sc_id}/recommendations:commit", response_model=m.Scenario, tags=TAG)
async def commit_recommendations(sc_id: str, body: m.CommitRecommendations) -> m.Scenario:
    """apply: 켠 추천 → 솔루션 칸 · 장면별 동작(끈 장면은 제품만), 적용 ≥ 1 이면 유형 with. products_only: 유형 WITHOUT · 솔루션 없음."""
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.require_editable(d)
        items = (d.get("recommendation") or {}).get("items") or []
        if body.mode == "products_only":
            d["type"] = "without"
            d["solution_picks"] = []
            for s in d.get("scenes") or []:
                s["plan_solutions"] = None
        else:
            applied = [it for it in items if it.get("applied")]
            picks = list(d.get("solution_picks") or [])
            for it in applied:
                s = seed.solution(it["solution_id"]) or {}
                if not any(p["solution_id"] == it["solution_id"] for p in picks):
                    picks.append({"solution_id": it["solution_id"], "name": s.get("name") or it["solution_id"], "source": "recommended",
                                  "ord": len(picks)})
            d["solution_picks"] = picks
            if applied:
                d["type"] = "with"
            by_scene = {it["scene_id"]: it for it in items}
            for s in d.get("scenes") or []:
                it = by_scene.get(s["id"])
                if it is None:
                    s["plan_solutions"] = None
                elif it.get("applied"):
                    s["plan_solutions"] = [{"solution_id": it["solution_id"], "action_code": it["action_code"]}]
                else:
                    s["plan_solutions"] = []
        d["step"] = 3
        d["dirty"] = True
        return d
    doc = await repo.update(sc_id, fn)
    await service.register(doc)
    return m.Scenario(**service.to_scenario(doc))


# ── 생성(SC4G) ─────────────────────────────────────────────

@router.post("/scenarios/{sc_id}/generate", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def generate(sc_id: str, body: m.GenerateRequest) -> m.JobAccepted:
    doc = await repo.require_sc(sc_id)
    if doc.get("status") == "generating":
        g = doc.get("generation") or {}
        job = await jobs().get(g.get("job_id") or "") if g.get("job_id") else None
        if job and job.status in ("queued", "running"):
            raise ApiError(409, "GENERATION_IN_PROGRESS", "이미 시나리오를 생성하고 있어요.", {"job_id": job.id})
    if not doc.get("scenes"):
        raise ApiError(400, "NO_SCENES", "장면이 없어요. 공간 시나리오를 먼저 입력해 주세요.")
    if body.scope == "unlocked" and not any(not s.get("locked") for s in doc["scenes"]):
        raise ApiError(400, "NOTHING_TO_GENERATE", "다시 생성할 장면이 없어요. 모든 장면을 직접 고쳤어요.")
    job_id = await service.enqueue("sc.generate", doc, {"scope": body.scope, "scene_ids": body.scene_ids},
                                   title=f"{doc.get('title') or '공간 시나리오'} · 시나리오 생성")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["status"] = "generating"
        d["step"] = 4
        d["generation"] = {"job_id": job_id, "status": "queued", "scope": body.scope, "scene_ids": body.scene_ids, "prepared": False,
                           "done": 0, "total": len(d.get("scenes") or []) if body.scope == "all" else
                           sum(1 for s in d.get("scenes") or [] if not s.get("locked")), "memos": [], "durations": [], "notes": {}}
        service.set_active(d, job_id, "generate")
        return d
    doc = await repo.update(sc_id, fn)
    await service.register(doc)
    return m.JobAccepted(job_id=job_id)


@router.post("/scenarios/{sc_id}/generate:resume", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def generate_resume(sc_id: str, body: m.ResumeRequest) -> m.JobAccepted:
    """실패한 생성 다시 시도 — 같은 thread(job_id)로 재개, 끝난 장면은 다시 쓰지 않는다."""
    doc = await repo.require_sc(sc_id)
    g = doc.get("generation") or {}
    if g.get("job_id") != body.job_id:
        raise ApiError(400, "JOB_MISMATCH", "이 시나리오의 생성 작업이 아니에요")
    job = await jobs().get(body.job_id)
    if job and job.status in ("queued", "running"):
        return m.JobAccepted(job_id=body.job_id, status=job.status)
    await service.enqueue("sc.generate", doc, {"scope": g.get("scope") or "all", "scene_ids": g.get("scene_ids"), "resume": True},
                          title=f"{doc.get('title') or '공간 시나리오'} · 시나리오 생성", job_id=body.job_id)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        gg = d.get("generation") or {}
        gg["status"] = "queued"
        gg["failed_reason"] = None
        d["generation"] = gg
        d["status"] = "generating"
        service.set_active(d, body.job_id, "generate")
        return d
    doc = await repo.update(sc_id, fn)
    await service.register(doc)
    return m.JobAccepted(job_id=body.job_id)


@router.post("/scenarios/{sc_id}/generate:cancel", response_model=m.Scenario, tags=TAG)
async def generate_cancel(sc_id: str) -> m.Scenario:
    """「중지 · 입력 고치기」: 잡 취소 → 끝난 장면은 done 으로 남기고 SC3 으로(status draft, step 3)."""
    from . import graphs
    doc = await repo.require_sc(sc_id)
    g = doc.get("generation") or {}
    if g.get("job_id"):
        try:
            await jobs().cancel(g["job_id"])
        except Exception as exc:  # noqa: BLE001
            log.info("잡 취소 실패: %s", exc)
    if doc.get("status") in ("generating", "failed"):
        await graphs.mark_generation_stopped(sc_id, canceled=True)
    return m.Scenario(**service.to_scenario(await repo.require_sc(sc_id)))


@router.get("/scenarios/{sc_id}/generation", response_model=m.GenerationView, tags=TAG)
async def generation_view(sc_id: str) -> m.GenerationView:
    from . import llm
    doc = await repo.require_sc(sc_id)
    g = doc.get("generation") or {}
    targets = g.get("targets") or [s["id"] for s in tl.scenes(doc)]
    notes = g.get("notes") or {}
    stage = g.get("stage") or ("split" if doc.get("status") == "generating" else "done")
    order = ["split", "write", "link", "confirm", "done"]
    cur = order.index(stage) if stage in order else 0
    names = {"split": "장면 나누기", "write": "장면별 이야기 쓰기", "link": "솔루션 동작 · 제품 연결", "confirm": "확인 필요 표시"}
    default_notes = {"split": texts.join([tl.scene_label(doc, s) for s in tl.scenes(doc) if s["id"] in targets]),
                     "write": "", "link": "", "confirm": "근거 없는 수치는 [00]으로 두고 표시"}
    stages = []
    for i, key in enumerate(order[:4]):
        st = "done" if i < cur or g.get("status") == "done" else ("run" if i == cur and g.get("status") in ("running", "queued") else "wait")
        if g.get("status") in ("failed", "canceled") and i == cur:
            st = "wait"
        stages.append(m.Stage(key=key, name=names[key], note=notes.get(key) or default_notes[key], state=st))  # type: ignore[arg-type]
    scenes = []
    for s in tl.scenes(doc):
        if s["id"] not in targets:
            continue
        slot = tl.slot_by_id(doc, s["slot_id"]) or {}
        scenes.append(m.PreviewScene(id=s["id"], no=s["no"], time=slot.get("time"), label=slot.get("label") or "", title=s.get("title") or "",
                                     status=s.get("status") or "waiting", partial_story=s.get("partial_story"),
                                     chips=seed.chip_labels(s.get("solutions") or []),
                                     product_chips=[service.product_chip(p) for p in s.get("products") or []],
                                     beat_text=" · ".join(b.get("text") or "" for b in s.get("beats") or [])))
    done = sum(1 for x in scenes if x.status == "done")
    total = len(scenes)
    durs = g.get("durations") or []
    avg = (sum(durs) / len(durs)) if durs else 8.0
    pct = 100 if g.get("status") == "done" else int(10 + 70 * done / max(1, total)) if g.get("prepared") else 3
    if stage == "link":
        pct = 90
    elif stage == "confirm":
        pct = 96
    eta = None if g.get("status") == "done" else avg * (total - done) + 4
    sols = [p["name"] for p in doc.get("solution_picks") or []] if doc.get("type") == "with" else []
    summary = texts.join([service.TYPE_LABEL[doc.get("type") or "with"], *sols,
                          *(service.product_chip(p) for p in doc.get("product_picks") or [])])
    return m.GenerationView(job_id=g.get("job_id"), status=g.get("status") or ("done" if doc.get("status") == "done" else "idle"),
                            summary=summary, stages=stages, pct=pct, eta_s=eta, eta_text=texts.eta_text(eta) if eta is not None else "",
                            done=done, total=total, scenes=scenes, failed_reason=g.get("failed_reason"), memos=g.get("memos") or [],
                            streaming=await llm.streaming_supported())
