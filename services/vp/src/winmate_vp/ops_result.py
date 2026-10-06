"""결과 · 레이아웃 · 수치 · 이미지 · 내보내기 · 넘김 · 업종판(05-vp.md §6.4 ~ §6.10) — REST 처리기 본체."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import TERMINAL

from . import catalog, config, decide, fit, imagesel, kbx, models, numbers, ops_work, package, repo, scenarios, service, signals

log = logging.getLogger("winmate.vp.ops")


def _sheet(doc: dict[str, Any], sh: str) -> dict[str, Any]:
    s = next((x for x in (doc.get("sheets") or []) + (doc.get("variants") or []) if x["id"] == sh), None)
    if s is None:
        raise ApiError(404, "NOT_FOUND", f"시트를 찾을 수 없어요: {sh}", {"resource": "sheet", "id": sh})
    return s


def _plan_sheet(doc: dict[str, Any], role: str) -> dict[str, Any] | None:
    return next((s for s in (doc.get("plan") or {}).get("sheets") or [] if s["role"] == role), None)


def _ensure_idle(doc: dict[str, Any]) -> None:
    aj = doc.get("active_job") or {}
    if aj and aj.get("status") not in TERMINAL:
        raise ApiError(409, "JOB_RUNNING", "이미 진행 중인 작업이 있어요. 끝난 뒤 다시 시도해 주세요.", {"job_id": aj.get("job_id"), "kind": aj.get("kind")})


# ── 생성 · 지시 ────────────────────────────────────────────

async def generate(vp_id: str, body: models.GenerateBody) -> str:
    doc = await repo.require_vp(vp_id)
    _ensure_idle(doc)
    asks = [q for q in service.open_questions(doc) if q.get("mode") == "ask"]
    if asks:
        raise ApiError(409, "QUESTION_REQUIRED", "답이 필요한 질문이 남아 있어요.", {"question_ids": [q["id"] for q in asks]})
    if not doc.get("materials_ready") and not doc.get("materials"):
        raise ApiError(409, "MATERIALS_REQUIRED", "재료를 먼저 정리해 주세요.")
    return await service.enqueue(vp_id, "vp.generate", {"sheet_roles": body.sheet_roles, "retry": body.retry}, doc=doc)


async def message(vp_id: str, body: models.MessageBody) -> str:
    doc = await repo.require_vp(vp_id)
    if body.context not in ("questions", "numbers"):
        _ensure_idle(doc)
    active = body.context not in ("questions", "numbers", "materials")
    return await service.enqueue(vp_id, "vp.revise", {"text": body.text, "context": body.context, "sheet_id": body.sheet_id},
                                 doc=doc, active=active and doc.get("generated", False))


# ── 레이아웃(VP3L) ─────────────────────────────────────────

def other_sheets_label(doc: dict[str, Any], sheet: dict[str, Any]) -> str:
    others = [s for s in package.main_sheets(doc) if s["id"] != sheet["id"]]
    parts = [f"{s['step_label']} {s['layout']['display']}" for s in others]
    return f"· {sheet['step_label']} · " + " · ".join(parts) + "는 그대로" if parts else f"· {sheet['step_label']}"


async def layout_options(vp_id: str, sh: str, *, pillars: int | None, request_id: str | None) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    pack = await repo.pack_status_map()
    if sh.startswith("plan:"):
        role = sh.split(":", 1)[1]
        ps = _plan_sheet(doc, role)
        if ps is None:
            raise ApiError(404, "NOT_FOUND", f"플랜에 {role} 시트가 없어요")
        sheet = {"id": sh, "role": role, "step_label": ps["step_label"], "layout": ps["layout"], "pinned": False}
    else:
        sheet = _sheet(doc, sh)
    req = next((r for r in doc.get("layout_requests") or [] if r["id"] == request_id), None) if request_id else \
        next((r for r in doc.get("layout_requests") or [] if r.get("sheet_id") == sh and r.get("status") == "open"), None)
    f = signals.fit_features(doc)
    ind = (doc.get("industry") or {}).get("code")
    res = fit.candidates(sheet["role"], f, current=sheet["layout"]["code"], requested=(req or {}).get("requested_code"), pillars=pillars,
                         industry_code=ind, pack_status=pack)
    name = sheet["step_label"]
    if req:
        intro = req.get("intro") or ""
    else:
        intro = f"{name} 시트에 쓸 수 있는 레이아웃이에요. 재료와 잘 맞는 순서로 보여 드려요."
    return {"sheet_id": sheet["id"], "sheet_label": name, "header": res["header"], "intro": intro,
            "request_id": (req or {}).get("id"), "options": (req or {}).get("options") if req else None, "candidates": res["candidates"],
            "pillars": res["pillars"], "other_sheets_label": other_sheets_label(doc, sheet), "pinned": bool(sheet.get("pinned"))}


async def choose_layout(vp_id: str, sh: str, body: models.ChooseLayout) -> tuple[dict[str, Any] | None, str | None]:
    """(Sheet, None) — 고정만 바뀜 / (None, job_id) — 레이아웃 변경(revise 잡)."""
    doc = await repo.require_vp(vp_id)
    sheet = _sheet(doc, sh)
    cur = sheet["layout"]["code"]
    target = catalog.norm(body.layout_code) if body.layout_code else None
    if body.pillars and target:
        target = catalog.with_pillars(target, body.pillars)
    if target:
        e = catalog.entry(target)
        if e is None:
            raise ApiError(422, "UNKNOWN_LAYOUT", f"모르는 레이아웃 코드예요: {body.layout_code}")
        if e.get("industry_code") and (await repo.pack_status_map()).get(e["industry_code"]) != "ready":
            raise ApiError(409, "PACK_IN_PRODUCTION", "업종판 제작 중이라 고를 수 없어요 · 출시 알림이 켜져 있어요.", {"code": target})
    only_pin = not body.option_key and (target is None or target == cur)
    if only_pin:
        def fn(d: dict[str, Any]) -> dict[str, Any]:
            s = _sheet(d, sh)
            s["pinned"] = bool(body.pin)
            s["layout"]["pinned"] = bool(body.pin)
            if body.pin:
                s["mode"] = "pin"
            for r in d.get("layout_requests") or []:
                if r.get("sheet_id") == sh and r.get("status") == "open" and (body.request_id in (None, r["id"])):
                    r["status"] = "applied"
                    r["choice"] = {"key": "C", "layout_code": cur, "pinned": bool(body.pin)}
            return d
        doc = await service.mutate(vp_id, fn)
        return _sheet(doc, sh), None
    _ensure_idle(doc)
    job = await service.enqueue(vp_id, "vp.revise", {"op": "layout", "sheet_id": sh, "option_key": body.option_key,
                                                     "layout_code": target, "pin": body.pin, "note": body.note,
                                                     "request_id": body.request_id}, doc=doc)
    return None, job


async def patch_sheet(vp_id: str, sh: str, body: models.PatchSheet) -> dict[str, Any]:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = _sheet(d, sh)
        if body.pinned is not None:
            s["pinned"] = body.pinned
            s["layout"]["pinned"] = body.pinned
            if body.pinned:
                s["mode"] = "pin"
        if body.title is not None:
            s["title"] = body.title
        if body.points is not None:
            s["points"] = body.points
        if body.speaker_notes is not None:
            s["speaker_notes"] = body.speaker_notes
        if body.content is not None:
            s.setdefault("content", {}).update(body.content.model_dump(exclude_unset=True))
        return d
    doc = await service.mutate(vp_id, fn)
    return _sheet(doc, sh)


async def cancel_layout_request(vp_id: str, vlr: str) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        r = next((x for x in d.get("layout_requests") or [] if x["id"] == vlr), None)
        if r is None:
            raise ApiError(404, "NOT_FOUND", f"레이아웃 요청을 찾을 수 없어요: {vlr}")
        r["status"] = "canceled"
        return d
    await service.mutate(vp_id, fn)


async def add_sheet(vp_id: str, body: models.AddSheet) -> str:
    doc = await repo.require_vp(vp_id)
    _ensure_idle(doc)
    if not doc.get("generated"):
        raise ApiError(409, "NOT_GENERATED", "시트를 먼저 만들어 주세요.")
    return await service.enqueue(vp_id, "vp.revise", {"op": "add_sheet", "kind": body.kind, "layout_code": body.layout_code,
                                                      "deployment_id": body.deployment_id}, doc=doc)


# ── 수치(VP3N) ─────────────────────────────────────────────

def _ef(doc: dict[str, Any], sh: str | None) -> dict[str, Any]:
    if sh:
        return _sheet(doc, sh)
    s = service.ef_sheet(doc)
    if s is None:
        raise ApiError(404, "NOT_FOUND", "기대 효과 시트가 없어요")
    return s


def metrics_view(doc: dict[str, Any], sheet: dict[str, Any]) -> dict[str, Any]:
    ms = [numbers.decorate(m) for m in (sheet.get("content") or {}).get("metrics") or []]
    for m in ms:
        m["industry_avg_available"] = bool(m.get("industry_avg"))
    code = sheet["layout"]["code"]
    rule = numbers.rule(ms, code)
    c = numbers.counts(ms)
    ask = sum(1 for m in ms if m.get("status") == "ask")
    chk = sum(1 for m in ms if m.get("status") == "estimated")
    have = c["secured"]
    empty = sum(1 for m in ms if m.get("status") in ("ask", "requested"))
    intro = (f"기대 효과({catalog.display(code)})는 전 → 후 수치가 3개 이상 있어야 힘이 있어요. "
             f"{c['total']}개 중 {have}개는 확보했고" + (f", 비어 있는 {c['total'] - have}개는 처리 방법을 골라 두었어요." if c['total'] - have
                                                       else ", 모두 채웠어요."))
    return {"sheet_id": sheet["id"], "code": code, "intro": intro, "metrics": ms, "counts": c, "rule": rule,
            "pending_ask": ask, "pending_check": chk if not empty else chk}


async def get_metrics(vp_id: str, sh: str) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    return metrics_view(doc, _ef(doc, sh))


async def patch_metric(vp_id: str, vmt: str, body: models.PatchMetric) -> dict[str, Any]:
    holder: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for s in d.get("sheets") or []:
            for m in (s.get("content") or {}).get("metrics") or []:
                if m["id"] != vmt:
                    continue
                m["handling"] = body.handling
                m["decided_by"] = "user"
                if body.handling == "industry_avg":
                    if m.get("industry_avg"):
                        numbers.use_industry_avg(m)
                elif body.handling == "direct":
                    for side in ("before", "after"):
                        v = getattr(body, side)
                        if v is not None:
                            m[side] = {**v.model_dump(), "status": "secured",
                                       "source": {"kind": "user", "label": "사용자", "refs": []}}
                    m["source_label"] = "사용자"
                    m["how"] = "직접 입력"
                elif body.handling == "request":
                    m["how"] = "고객에게 요청 · 답이 오면 바꿔요"
                numbers.decorate(m)
                holder["sheet"] = s
                return d
        raise ApiError(404, "NOT_FOUND", f"지표를 찾을 수 없어요: {vmt}")
    doc = await service.mutate(vp_id, fn)
    return metrics_view(doc, _sheet(doc, holder["sheet"]["id"]))


async def apply_metrics(vp_id: str, sh: str) -> tuple[dict[str, Any] | None, str | None]:
    doc = await repo.require_vp(vp_id)
    sheet = _ef(doc, sh)
    holder: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = _sheet(d, sheet["id"])
        ms = (s.get("content") or {}).get("metrics") or []
        numbers.apply_defaults(ms)
        r = numbers.rule(ms, s["layout"]["code"])
        holder["switch"] = r["would_switch_to"]
        return d
    await service.mutate(vp_id, fn)
    if holder.get("switch"):
        doc = await repo.require_vp(vp_id)
        job = await service.enqueue(vp_id, "vp.revise", {"op": "ef_switch", "sheet_id": sheet["id"], "layout_code": holder["switch"]}, doc=doc)
        return None, job
    doc = await service.save_point(vp_id, "수치 반영")
    return doc, None


async def data_request_draft(vp_id: str, sh: str | None) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    sheet = _ef(doc, sh)
    team = None
    for m in signals.active(doc, "stakeholder"):
        if (m.get("group") or "") == "operator" and ("팀" in m["text"] or "운영" in m["text"]):
            team = m["text"].split(" · ")[0]
            break
    return numbers.data_request((sheet.get("content") or {}).get("metrics") or [], team)


# ── 이미지(VPI) ───────────────────────────────────────────

async def ctx_for(doc: dict[str, Any]) -> dict[str, Any]:
    ind = doc.get("industry") or {}
    return {"solutions": await kbx.solutions_index(), "vertical": ind.get("kr_vertical_id"),
            "industry_cell": ind.get("cell") or ind.get("name"),
            "customer_photos": [a for a in doc.get("attachments") or [] if a.get("kind") == "customer_photo"],
            "case_photo": (doc.get("facts") or {}).get("case_photo")}


def slots_view(doc: dict[str, Any]) -> dict[str, Any]:
    order = {s["id"]: i for i, s in enumerate(package.main_sheets(doc) + list(doc.get("variants") or []))}
    role_rank = {"VP": 0, "CH": 1, "EF": 2, "REF": 3}
    sheets = {s["id"]: s for s in (doc.get("sheets") or []) + (doc.get("variants") or [])}
    items = sorted(doc.get("image_slots") or [], key=lambda x: (x.get("extra", False), role_rank.get((sheets.get(x["sheet_id"]) or {}).get("role", "VP"), 9),
                                                               order.get(x["sheet_id"], 99), x.get("code")))
    official = sum(1 for x in items if x.get("tier") in ("cut", "ui", "case") and x.get("asset"))
    illust = sum(1 for x in items if x.get("tier") == "illust")
    checks = sum(1 for x in items if x.get("mode") == "check")
    intro = f"이미지 칸 {len(items)}개를 채웠어요. 공식 실사 {official} · 일러스트 {illust}이고, 확인할 것은 {checks}개예요." if items else \
        "이 시트들에는 이미지 칸이 없어요."
    acts = []
    if official:
        acts.append({"code": "VP-N", "display": "VP-N", "label": "실사 히어로로", "tip": "설치 사례 사진을 왼쪽에 크게 · 가치 3개는 오른쪽", "role": "VP"})
    cp = (doc.get("facts") or {}).get("case_photo")
    if cp:
        acts.append({"code": "VP-Q", "display": "VP-Q", "label": "레퍼런스 1장 추가",
                     "tip": f"{cp.get('title') or '같은 업종'} 사례 · 외부 제출 전 인용 확인", "role": "VP"})
    acts.append({"code": "Prod", "display": "Prod", "label": "일러스트로 통일", "tip": "실사를 모두 빼고 같은 톤의 일러스트로", "role": "VP"})
    return {"items": items, "counts": {"slots": len(items), "official": official, "illust": illust, "checks": checks}, "intro": intro,
            "actions": acts}


async def get_slots(vp_id: str) -> dict[str, Any]:
    return slots_view(await repo.require_vp(vp_id))


async def slot_candidates(vp_id: str, vis: str) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    slot = next((x for x in doc.get("image_slots") or [] if x["id"] == vis), None)
    if slot is None:
        raise ApiError(404, "NOT_FOUND", f"이미지 칸을 찾을 수 없어요: {vis}")
    items = await imagesel.candidates(doc, slot, await ctx_for(doc))
    nm = (slot.get("subject") or {}).get("label") or slot["label"]
    head_code = slot["code"].split(" · ", 1)[-1]
    right = f"모두 {nm}{decide.josa(nm, '이', '가')} 만드는 가치에 맞는 이미지" if (slot.get("subject") or {}).get("refs") else "칸에 맞는 이미지"
    return {"slot_id": vis, "header": f"{head_code} · {slot['label']}", "right": right, "items": items}


async def put_slot(vp_id: str, vis: str, body: models.PutImageSlot) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    slot = next((x for x in doc.get("image_slots") or [] if x["id"] == vis), None)
    if slot is None:
        raise ApiError(404, "NOT_FOUND", f"이미지 칸을 찾을 수 없어요: {vis}")
    new = await imagesel.replace(slot, body.asset.model_dump())

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["image_slots"] = [new if x["id"] == vis else x for x in d.get("image_slots") or []]
        return d
    await service.mutate(vp_id, fn)
    await service.save_point(vp_id, "이미지 변경")
    return new


async def restyle(vp_id: str) -> str:
    doc = await repo.require_vp(vp_id)
    _ensure_idle(doc)
    return await service.enqueue(vp_id, "vp.images", {"op": "restyle", "style": "illustration"}, doc=doc)


# ── 내보내기 · 묶음 ─────────────────────────────────────────

def target_type(doc: dict[str, Any]) -> str:
    return ((doc.get("target_proposal") or {}).get("type")) or "standard"


async def get_package(vp_id: str, proposal_type: str | None) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    return package.build(doc, proposal_type or target_type(doc))


async def get_packages(vp_id: str, selected: str | None, estimates_as_notes: bool = True) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    sel = selected or target_type(doc)
    types = [package.build(doc, t, estimates_as_notes=estimates_as_notes) for t in ("standard", "quickwin", "solution")]
    pk = next(p for p in types if p["proposal_type"] == sel)
    m = pk["counts"]["estimates_as_notes"]
    return {"selected": sel, "types": types, "dock": package.dock_text(pk),
            "estimates_note": f"[추정] {m}건은 노트로" if (m and estimates_as_notes) else None}


async def copy_text(vp_id: str) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    vp = next((s for s in package.main_sheets(doc) if s["role"] == "VP"), None)
    if vp is None:
        raise ApiError(409, "NOT_GENERATED", "가치 제안 시트를 먼저 만들어 주세요.")
    c = vp.get("content") or {}
    lines = [vp.get("title") or ""]
    for i, p in enumerate(c.get("pillars") or [], 1):
        lines.append(f"{i}. {p.get('title')}" + (f" — {p['body']}" if p.get("body") else ""))
    for s in c.get("stakeholders") or []:
        lines.append(f"· {s.get('role')}: {s.get('value')}" + (f" (KPI {s['kpi']})" if s.get("kpi") else ""))
    if c.get("one_liner"):
        lines.append(c["one_liner"].get("statement") or "")
        for e in c["one_liner"].get("evidence") or []:
            lines.append(f"· {e}")
    ev = [m["text"] for m in signals.active(doc, "evidence")][:3]
    if ev:
        lines.append("근거: " + " · ".join(ev))
    return {"text": "\n".join(x for x in lines if x).strip()}


async def start_export(vp_id: str, body: models.ExportBody) -> tuple[str, str]:
    doc = await repo.require_vp(vp_id)
    if not doc.get("generated"):
        raise ApiError(409, "NOT_GENERATED", "시트를 먼저 만들어 주세요.")
    vex = new_id("vex")
    await repo.put_export(vex, {"id": vex, "vp_id": vp_id, "format": body.format, "status": "queued", "file_id": None,
                                "created_at": now_iso()})
    job = await service.enqueue(vp_id, "vp.export", {"export_id": vex, "format": body.format, "include_notes": body.include_notes,
                                                     "proposal_type": body.proposal_type or target_type(doc)}, doc=doc, active=False)
    rec = await repo.get_export(vex) or {}
    rec["job_id"] = job
    await repo.put_export(vex, rec)
    return vex, job


# ── 넘김(§6.9) ─────────────────────────────────────────────

INTERVIEW_Q = {"kind": "interview_numbers", "mode": "ask", "title": "4 · 고객 내부 인터뷰 수치를 제안서에 쓸까요?",
               "aside": "고객 내부 인터뷰 수치를 고객 제출물에 쓸 때"}


def open_route(proposal_id: str | None, vho: str) -> str:
    return f"/proposal/{proposal_id}/sections/vp?handoff={vho}" if proposal_id else f"/proposal/new?handoff={vho}"


async def create_handoff(vp_id: str, body: models.HandoffBody) -> tuple[int, dict[str, Any]]:
    doc = await repo.require_vp(vp_id)
    if not doc.get("generated"):
        raise ApiError(409, "NOT_GENERATED", "시트를 먼저 만들어 주세요.")
    pkg = package.build(doc, body.proposal_type, estimates_as_notes=body.options.estimates_as_notes)
    if pkg["interview_numbers"] and body.interview_numbers_confirmed is None:
        q = {**INTERVIEW_Q, "id": new_id("vqn"), "no": 4, "context_text": " · ".join(pkg["interview_numbers"][:4]), "multi": False,
             "options": [{"key": "use", "label": "그대로 쓰기", "recommended": False},
                         {"key": "mask", "label": "[00]으로 바꾸고 노트에 남기기", "recommended": True}],
             "default_keys": ["mask"], "hint": None, "selected_keys": ["mask"], "answer": None, "status": "open"}
        raise ApiError(409, "QUESTION_REQUIRED", "고객 내부 인터뷰 수치를 제안서에 쓸지 정해 주세요.", {"question": q})
    if body.interview_numbers_confirmed is False:
        pkg = package.mask_interview(pkg)
    if pkg["needs_variant"]:
        _ensure_idle(doc)
        job = await service.enqueue(vp_id, "vp.revise", {"op": "add_sheet", "kind": "one_liner", "then_handoff": body.model_dump()}, doc=doc)
        return 202, {"job_id": job, "status": "queued", "ref": {"kind": "handoff_pending", "id": vp_id}}
    return 201, await finalize_handoff(vp_id, body.model_dump(), pkg)


async def finalize_handoff(vp_id: str, body: dict[str, Any], pkg: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    opts = body.get("options") or {}
    if pkg is None:
        pkg = package.build(doc, body.get("proposal_type") or "standard", estimates_as_notes=opts.get("estimates_as_notes", True))
        if body.get("interview_numbers_confirmed") is False:
            pkg = package.mask_interview(pkg)
    vho = new_id("vho")
    pid = body.get("proposal_id")
    route = open_route(pid, vho)
    synced = 0
    if opts.get("sync_storyboard", True):
        synced = await sync_storyboard(doc)
    for s in pkg["sheets"]:
        for slot in s.get("image_slots") or []:
            key = imagesel.asset_key(slot.get("asset"))
            if key:
                n = await repo.add_usage(key, vp_id, vho)
                if slot.get("meta"):
                    slot["meta"]["usage_history"] = {"count": n, "label": f"Winmate 제안서 {n}건"}
                if pid:
                    try:
                        await ServiceClient("workspace").put(f"/v1/asset-usage/{key}", json={"proposal_id": pid, "sheet_id": s.get("sheet_id")})
                    except Exception as exc:  # noqa: BLE001
                        log.info("workspace 사용 기록 실패 %s: %s", key, exc)
    rec = {"id": vho, "vp_id": vp_id, "vp_version": int(doc.get("doc_version") or 0) + 1, "proposal_id": pid,
           "proposal_type": pkg["proposal_type"], "options": {"estimates_as_notes": opts.get("estimates_as_notes", True),
                                                              "sync_storyboard": opts.get("sync_storyboard", True),
                                                              "ask_before_overwrite_pinned": opts.get("ask_before_overwrite_pinned", True)},
           "package": pkg, "status": "ready", "open_route": route, "created_at": now_iso(), "acked_at": None,
           "proposal_title": body.get("proposal_title"), "note": body.get("note"), "storyboard_synced": synced}
    await repo.put_handoff(vho, rec)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d.setdefault("handoffs", []).append({"id": vho, "proposal_id": pid, "proposal_type": pkg["proposal_type"], "created_at": rec["created_at"]})
        if body.get("proposal_title") or pid:
            d["linked_proposal"] = {"id": pid, "title": body.get("proposal_title") or (d.get("linked_proposal") or {}).get("title") or "새 제안서"}
        return d
    await service.mutate(vp_id, fn)
    await service.save_point(vp_id, "넘김")
    return {"id": vho, "status": "ready", "open_route": route, "package": pkg, "storyboard_synced": synced}


async def sync_storyboard(doc: dict[str, Any]) -> int:
    """다듬은 Key Message 를 Storyboard 에 되돌려 쓰기 — 바뀐 KM 수만큼 PATCH(§6.9 · docs/requests/vp.md)."""
    sb_src = [s for s in doc.get("sources") or [] if s.get("kind") == "storyboard" and s.get("connected")]
    if not sb_src:
        return 0
    kms = {k.get("id"): k for s in sb_src for k in ((s.get("extra") or {}).get("kms") or [])}
    vp = next((s for s in package.main_sheets(doc) if s["role"] == "VP"), None)
    if not vp:
        return 0
    n = 0
    sb = ServiceClient("storyboard")
    for p in (vp.get("content") or {}).get("pillars") or []:
        km = kms.get(p.get("km_ref"))
        if not km or not p.get("title") or p["title"].strip() == (km.get("text") or "").strip():
            continue
        sb_id = next((s["ref_id"] for s in sb_src if any(k.get("id") == km["id"] for k in (s.get("extra") or {}).get("kms") or [])), None)
        try:
            await sb.patch(f"/v1/storyboards/{sb_id}/key-messages/{km['id']}", json={"text": p["title"], "source": {"service": "vp", "ref_id": doc["id"]}})
            n += 1
        except Exception as exc:  # noqa: BLE001
            log.warning("Storyboard KM 되돌려 쓰기 실패 %s: %s", km.get("id"), exc)
    return n


async def get_handoff(vho: str) -> dict[str, Any]:
    rec = await repo.get_handoff(vho)
    if rec is None:
        raise ApiError(404, "NOT_FOUND", f"넘김을 찾을 수 없어요: {vho}")
    return rec


async def ack_handoff(vho: str, body: models.HandoffAck) -> dict[str, Any]:
    rec = await get_handoff(vho)
    rec["status"] = body.result
    rec["acked_at"] = now_iso()
    rec["applied_sheet_ids"] = body.applied_sheet_ids
    rec["pinned_conflicts"] = body.pinned_conflicts or []
    if body.proposal_id:
        rec["proposal_id"] = body.proposal_id
    await repo.put_handoff(vho, rec)
    vp_id = rec["vp_id"]

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if body.result == "applied":
            d["linked_proposal"] = {"id": body.proposal_id or rec.get("proposal_id"),
                                    "title": body.proposal_title or rec.get("proposal_title") or (d.get("linked_proposal") or {}).get("title") or "제안서"}
        elif body.result == "needs_confirmation":
            labels = " · ".join(f"{c.get('sheet_label', '')} {c.get('code', '')}".strip() for c in body.pinned_conflicts or []) or "고정한 시트"
            d.setdefault("checks", []).append({"id": new_id("vck"), "tag": "요청", "text": f"제안서에 고정한 시트가 있어 확인이 필요해요 — {labels}",
                                               "action_label": "확인", "action_route": f"/vp/{vp_id}/export", "strong": False,
                                               "resolved": False, "handoff_id": vho})
            d["pending_confirmations"] = int(d.get("pending_confirmations") or 0) + 1
        return d
    await service.mutate(vp_id, fn)
    return rec


async def release_proposal(vp_id: str, pid: str) -> dict[str, Any]:
    """proposal → vp: 제안서를 지웠다 — VP0 「연결된 제안서」 · 보낼 제안서가 그 제안서면 비운다(다른 제안서로 넘긴 적이 있으면 가장 최근 것으로).
    그 제안서로 간 넘김 기록에는 `released_at`(통합)."""
    await repo.require_vp(vp_id)
    hs = await repo.list_handoffs(vp_id)
    for h in hs:
        if h.get("proposal_id") == pid and not h.get("released_at"):
            await repo.put_handoff(h["id"], {**h, "released_at": now_iso()})
    others = sorted((h for h in hs if h.get("proposal_id") and h.get("proposal_id") != pid and h.get("status") == "applied" and not h.get("released_at")),
                    key=lambda h: h.get("acked_at") or h.get("created_at") or "")
    released = False

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal released
        changed = False
        if (d.get("linked_proposal") or {}).get("id") == pid:
            last = others[-1] if others else None
            d["linked_proposal"] = {"id": last["proposal_id"], "title": last.get("proposal_title") or "제안서"} if last else None
            changed = True
        if (d.get("target_proposal") or {}).get("proposal_id") == pid:
            d["target_proposal"] = None
            changed = True
        released = changed
        return d if changed else None
    doc = await service.mutate(vp_id, fn)
    return {"vp_id": vp_id, "proposal_id": pid, "released": released, "linked_proposal": service.linked_proposal(doc)}


# ── ProposalHandoff v1(10-proposal §8.0 · V1) ───────────────

def _facts_of(pkg: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for s in pkg["sheets"]:
        c = s.get("content") or {}
        for m in c.get("metrics") or []:
            for side, lab in (("before", "지금"), ("after", "도입 후")):
                v = m.get(side) or {}
                st = v.get("status")
                status = "confirmed" if st == "secured" else ("unconfirmed" if st == "estimated" else "placeholder")
                out.append({"key": f"{m['id']}.{side}", "label": f"{m['label']} · {lab}", "value": v.get("display") if st in numbers.USABLE else None,
                            "unit": v.get("unit"), "status": status, "placeholder": v.get("display") if status == "placeholder" else None,
                            "source": v.get("source")})
        for ch in c.get("challenges") or []:
            v = ch.get("impact") or {}
            if not v:
                continue
            st = v.get("status")
            status = "confirmed" if st == "secured" else ("unconfirmed" if st == "estimated" else "placeholder")
            out.append({"key": f"{ch['id']}.impact", "label": ch["title"], "value": v.get("display") if st in numbers.USABLE else None,
                        "unit": v.get("unit"), "status": status, "placeholder": v.get("display") if status == "placeholder" else None,
                        "source": v.get("source")})
    return out


async def proposal_handoff(vp_id: str, ptype: str | None, section: str | None) -> dict[str, Any]:
    doc = service.derive(await repo.require_vp(vp_id))
    pkg = package.build(doc, ptype or target_type(doc))
    items = []
    for row, s in zip([r for r in pkg["rows"] if r["code"] != "—"], pkg["sheets"]):
        st = "add" if "추가" in row["treatment"] else ("warn" if ("[00]" in (s.get("points") or "") or "[추정]" in (s.get("points") or "")) else "ok")
        e = catalog.entry(s["layout"]["code"]) or {}
        items.append({"key": s.get("sheet_id"), "label": f"{row['sheet_label']} · {s['layout']['display']}", "from_label": "가치 제안 결과",
                      "sheet_role": s["role"], "sheet_title": s["title"], "template_hint": {"code": s["layout"]["code"], "name": e.get("name", "")},
                      "status": st, "status_label": row["treatment"], "include_default": st != "add",
                      "content": {**(s.get("content") or {}), "points": s.get("points"), "pinned": s.get("pinned"),
                                  "speaker_notes": s.get("speaker_notes"), "image_slots": s.get("image_slots")},
                      "sources": [{"kind": "vp", "ref": vp_id, "label": x} for x in pkg["sources_footer"][:6]]})
    assets = []
    for s in pkg["sheets"]:
        for slot in s.get("image_slots") or []:
            a = slot.get("asset") or {}
            if not a:
                continue
            m = slot.get("meta") or {}
            assets.append({"kind": "image", "file_id": a.get("file_id"), "kb_image_id": a.get("asset_id"), "rights": m.get("rights") or "",
                           "caption_rule": m.get("caption_rule") or "", "source_url": (m.get("source_page") or {}).get("url")})
    ind = doc.get("industry") or {}
    rq = next((s for s in doc.get("sources") or [] if s.get("kind") == "requirements" and s.get("connected")), None)
    return {
        "source": {"feature": "VP", "ref_id": vp_id, "version": int(doc.get("doc_version") or 0), "title": doc.get("title") or "",
                   "updated_at": doc.get("updated_at") or "", "route": f"/vp/{vp_id}/result"},
        "target": {"proposal_type": pkg["proposal_type"], "section_key": section or "vp"},
        "customer": {"name": doc.get("customer_name"), "industry_code": ind.get("code") if ind.get("code") != "GEN" else None},
        "rq_ref": {"rq_id": rq["ref_id"], "version": int(rq.get("fetched_version") or 0)} if rq else None,
        "items": items, "facts": _facts_of(pkg), "assets": assets, "live_link": False,
    }


async def draft(body: models.DraftBody) -> dict[str, Any]:
    """V2 — 제안서가 VP 작업 없이 Value Props 초안을 요청(재료 = SB · MI · RQ) → 재료 → 생성까지 자동(auto_answer)."""
    refs = []
    kinds = {"SB": "storyboard", "MI": "mi", "RQ": "requirements", "VP": "vp", "storyboard": "storyboard", "mi": "mi",
             "requirements": "requirements", "case": "case"}
    for s in body.sources:
        k = kinds.get(s.feature) or kinds.get(s.feature.upper())
        if k:
            refs.append(models.SourceRef(kind=k, ref_id=s.ref_id))
    if body.rq_ref and not any(r.kind == "requirements" and r.ref_id == body.rq_ref.rq_id for r in refs):
        refs.append(models.SourceRef(kind="requirements", ref_id=body.rq_ref.rq_id))
    target = models.TargetProposal(proposal_id=body.proposal_id, title=body.proposal_title or "", type=body.proposal_type)
    doc = await ops_work.create(models.CreateVP(start="proposal", customer_name=body.customer_name, project_id=body.project_id,
                                                source_refs=refs or None, target_proposal=target, auto_answer=True))
    if body.industry_code:
        await ops_work.patch(doc["id"], models.PatchVP(industry=models.IndustryCode(code=body.industry_code)))
    job = await service.enqueue(doc["id"], "vp.materials", {"then_generate": True, "sheet_roles": body.sheet_roles,
                                                             "products": body.products or []}, doc=doc)
    return {"value_prop_id": doc["id"], "job_id": job, "status": "queued"}


# ── 규칙 · 카탈로그 · 업종판(§6.10) ──────────────────────────

LEGEND_LABEL = {"auto": "자동", "check": "확인 권장", "ask": "선택 필요", "pin": "고정"}


async def routing_rules() -> dict[str, Any]:
    r = config.routing()
    packs = await packs_view()
    return {
        "title": "구조와 레이아웃은 스스로 고르고, 다섯 경우만 묻습니다",
        "legend": [{"mode": x["mode"], "label": LEGEND_LABEL[x["mode"]], "desc": x["desc"]} for x in r["legend"]],
        "stages": r["stages"], "band_title": r["band_title"], "band_sub": r["band_sub"], "band_head": r["band_head"],
        "band": [{"code": b["code"], "name": b["name"], "ind": b["ind"], "rules": [{"c": c, "t": t} for c, t in b["rules"]]} for b in r["band"]],
        "packs": {"title": r["packs_title"], "sub": r["packs_sub"], "ready": packs["ready"], "total": 16,
                  "cells": [{"code": i["code"], "name": i["cell"], "status": i["status"]} for i in packs["items"]],
                  "line": f"{packs['ready']} / 16 — 지금은 모든 업종을 범용으로 만들고, 업종판이 나오면 작업마다 바꿀지 물어봐요 (고정한 시트는 그대로)"
                  if packs["ready"] < 16 else "16 / 16 — 모든 업종판이 준비됐어요"},
        "gaps_title": r["gaps_title"], "gaps_sub": r["gaps_sub"], "gaps": r["gaps"], "asks_title": r["asks_title"],
        "asks": [{"n": i + 1, "t": t} for i, t in enumerate(r["asks"])], "thresholds": r["thresholds"],
    }


async def scenario_rows() -> dict[str, Any]:
    res = [scenarios.run_case(fx) for fx in scenarios.load_fixtures()]
    rows = []
    for r, fx in zip(res, scenarios.load_fixtures()):
        ind = r["industry"]
        ind_label = ind["name"] + (f" ({(fx.get('industry') or {}).get('inherited', {}).get('label', '').split(' ')[0]} 상속)"
                                   if ind.get("source") in ("mi",) else "")
        if ind.get("confidence") and ind.get("source") == "classified" and fx["no"] == 8:
            ind_label = f"{ind['name']} {ind['confidence']:.2f}"
        rows.append({"no": fx["no"], "name": fx["name"], "input": fx["input"], "industry": ind_label, "pack": r["pack"],
                     "flow_label": r["flow_label"], "chips": [{"t": t, "kind": k} for t, k in zip(r["chips"], r["chip_kinds"])],
                     "asked": (r["asked"] or {}).get("label") or "없음", "mode": (r["asked"] or {}).get("mode") or "",
                     "scene": (fx.get("expect") or {}).get("scene", "")})
    return {"rows": rows, "stats": scenarios.stats(res)}


async def layouts(role: str | None, family: str | None, industry: str | None) -> dict[str, Any]:
    pack = await repo.pack_status_map()
    items = []
    for e in catalog.all_entries(pack):
        if role and e["role"] != role:
            continue
        if family and e["family"] != family:
            continue
        if industry and e.get("industry_code") not in (None, industry):
            continue
        if not industry and e.get("industry_code"):
            pass
        items.append({**e, "has_images": bool(e.get("slots"))})
    counts: dict[str, int] = {}
    for e in items:
        counts[e["family"]] = counts.get(e["family"], 0) + 1
    return {"items": items, "counts": counts}


async def packs_view() -> dict[str, Any]:
    st = await repo.pack_state()
    items = []
    for ind in config.industries():
        s = st.get(ind["code"]) or {}
        items.append({"code": ind["code"], "name": ind["name"], "cell": ind["cell"], "status": s.get("status", "in_production"),
                      "released_at": s.get("released_at")})
    ready = sum(1 for i in items if i["status"] == "ready")
    banner = sub = None
    if ready < 16:
        if ready == 0:
            banner = "Value Props 업종 레이아웃 16종은 제작 중이에요."
            sub = "지금은 범용 35종(이미지판 기본 · 공식 실사 우선)으로 만들고, 업종판이 나오면 작업마다 바꿀지 물어볼게요."
        else:
            names = " · ".join(i["cell"] for i in items if i["status"] == "ready")
            banner = f"Value Props 업종 레이아웃 {ready}종이 나왔어요({names}) · 나머지 {16 - ready}종은 제작 중이에요."
            sub = "준비된 업종은 업종판으로, 나머지는 범용 35종으로 만들고 업종판이 나오면 바꿀지 물어볼게요."
    return {"ready": ready, "total": 16, "items": items, "banner": banner, "banner_sub": sub}


async def release_pack(code: str) -> str:
    if code not in config.INDUSTRY_CODES:
        raise ApiError(422, "INVALID_INDUSTRY", f"모르는 업종 코드예요: {code}")
    await repo.set_pack(code, "ready")
    from winmate_common.jobs import jobs as _jobs
    job = await _jobs().enqueue("vp", "vp.pack_offer", {"industry_code": code}, title=f"업종판 교체 제안 · {code}")
    return job.id


async def decide_pack_offer(vp_id: str, vpo: str, decision: str) -> tuple[dict[str, Any] | None, str | None]:
    doc = await repo.require_vp(vp_id)
    offer = next((o for o in doc.get("pack_offers") or [] if o["id"] == vpo), None)
    if offer is None:
        raise ApiError(404, "NOT_FOUND", f"업종판 교체 제안을 찾을 수 없어요: {vpo}")
    if decision == "dismiss":
        def fn(d: dict[str, Any]) -> dict[str, Any]:
            for o in d.get("pack_offers") or []:
                if o["id"] == vpo:
                    o["status"] = "dismissed"
            for c in d.get("checks") or []:
                if c.get("offer_id") == vpo:
                    c["resolved"] = True
            return d
        return await service.mutate(vp_id, fn), None
    _ensure_idle(doc)
    job = await service.enqueue(vp_id, "vp.revise", {"op": "pack_apply", "offer_id": vpo}, doc=doc)
    return None, job


# ── 버전 ──────────────────────────────────────────────────

async def versions(vp_id: str) -> dict[str, Any]:
    await repo.require_vp(vp_id)
    items = [{"version": int(v.get("n") or 0), "reason": v.get("reason") or "", "created_at": v.get("saved_at") or v.get("created_at") or ""}
             for v in await repo.list_versions(vp_id)]
    return {"items": sorted(items, key=lambda x: -x["version"])}
