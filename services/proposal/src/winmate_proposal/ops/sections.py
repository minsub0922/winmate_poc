"""§6.5 섹션(SectionStep) · 시트 · 템플릿 고르기 · 값(fact) · 수정 요청 · 대화."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from .. import clients, config, content as C, core, defs, facts as F, inputs, links as L, repo, templates
from .. import models as M
from ..errors import not_found, rev_conflict, section_not_in_type, sheet_not_found, unprocessable
from ..graphs import common as G


# ── 공용: 시트 화면 모델 ───────────────────────────────────
def template_state(t: dict[str, Any], cat: dict[str, dict[str, Any]] | None = None) -> M.TemplateState:
    code = t.get("code")
    name = None
    if code:
        name = (cat or {}).get(code, {}).get("name") or templates.local_name(code)[0]
    return M.TemplateState(code=code, mode=t.get("mode") or "auto", source=t.get("source"), recommended_code=t.get("recommended_code"),
                           reason=t.get("reason"), product_count=t.get("product_count"), name=name, tag=core.tag_of(t),
                           locked_manual=bool(t.get("locked_manual")))


def item_text(it: dict[str, Any]) -> str:
    t = it.get("text") or {}
    if isinstance(t, str):
        return t
    return " ".join(x for x in (t.get("pre"), t.get("mark"), t.get("post")) if x).strip()


async def sheet_view(sh: dict[str, Any], *, p: dict[str, Any] | None = None, facts_all: dict[str, dict[str, Any]] | None = None,
                     with_schema: bool = True) -> M.Sheet:
    pid = sh["proposal_id"]
    facts_all = facts_all if facts_all is not None else await F.facts_of(pid)
    content = sh.get("content") or {}
    display = C.display_content(content, facts_all) if content else {}
    items = [it for it in await repo.alist("confirm_items", {"proposal_id": pid})
             if it.get("status") == "open" and (it.get("sheet_id") == sh["id"] or sh["id"] in (it.get("linked_sheet_ids") or []))]
    briefs = [M.ConfirmBrief(id=it["id"], tag=it.get("tag") or "", text=item_text(it), status=it.get("status") or "open") for it in items]
    label = ""
    if items:
        label = f"이 시트에 확정 필요 {len(items)}곳 · " + " · ".join(item_text(it) for it in items[:2])
    by_key = {f.get("key"): f for f in facts_all.values()}
    used = []
    seen: set[str] = set()
    for fid, _path in C.tokens_in(content):
        if fid in seen or fid not in facts_all:
            continue
        seen.add(fid)
        f = facts_all[fid]
        used.append(M.FactBrief(id=fid, key=f.get("key") or "", label=f.get("label") or "", display=C.fact_display(f, by_key), status=f.get("status") or "placeholder"))
    t = sh.get("template") or {}
    cat = await clients.export_catalog()
    schema = None
    if with_schema and t.get("code"):
        detail = await clients.export_template_detail(t["code"], t.get("product_count"))
        schema = (detail or {}).get("slot_schema")
    r = sh.get("render") or None
    srcs = []
    for s in sh.get("sources") or []:
        srcs.append(M.SheetSourceRef(kind=s.get("kind") or "kb", ref=s.get("ref"), label=s.get("label") or "", tier=s.get("tier"), url=s.get("url"),
                                     page=s.get("page")))
    reuse = sh.get("reuse") or None
    return M.Sheet(
        id=sh["id"], proposal_id=pid, section_key=sh.get("section_key") or "", section_name=defs.SECTIONS.get(sh.get("section_key") or "", {}).get("name", ""),
        order=int(sh.get("order") or 0), sheet_no=int(sh.get("sheet_no") or 0), role=sh.get("role") or "", role_name=core.role_name(sh.get("role")),
        msg=(defs.ROLES.get(sh.get("role") or "") or {}).get("msg", ""), solution_code=sh.get("solution_code"), repeat_key=sh.get("repeat_key"),
        title=sh.get("title") or "", template=template_state(t, cat), content=content, display=display, sources=srcs, status=sh.get("status") or "need",
        status_label=core.sheet_status_label(sh), origin=sh.get("origin") or "user", inferred=bool(sh.get("inferred")),
        evidence_note=sh.get("evidence_note"), reuse=M.SheetReuse(**reuse) if reuse else None, split_of=sh.get("split_of"),
        edited_since_version=bool(sh.get("edited_since_version")),
        render=M.SheetRender(png_file_id=r.get("png_file_id"), url=(f"/api/files/v1/files/{r['png_file_id']}/content" if r.get("png_file_id") else None),
                             rev=r.get("rev"), status=r.get("status")) if r else None,
        thumb_url=core.sheet_thumb(sh), confirm_items=briefs, confirm_label=label, facts=used, slot_schema=schema,
        updated_at=sh.get("touched_at") or sh.get("updated_at") or "", rev=int(sh.get("content_rev") or 0) + 1)


# ── 섹션 화면 ──────────────────────────────────────────────
async def _ctx(pid: str, key: str) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    p = await core.load(pid)
    keys = core.type_sections(p.get("type"))
    if key not in keys or key not in defs.SECTIONS:
        raise section_not_in_type(key)
    sec = await core.section_doc(pid, key)
    return p, keys, sec


async def fill_signature(pid: str, key: str) -> str:
    """연결 자료 · 시트 목록이 바뀌었는지(섹션 진입 시 :fill 필요 여부)."""
    p = await core.load(pid)
    lns = await L.section_links(pid, key, p.get("type"))
    shs = await core.sheets_of(pid, section_key=key)
    raw = {"links": sorted(f"{ln['id']}:{ln.get('version_at_link')}:{ln.get('latest_version')}:{bool(ln.get('stale'))}:{len(ln.get('include_keys') or [])}"
                           for ln in lns),
           "sheets": sorted(s["id"] for s in shs), "type": p.get("type")}
    return hashlib.sha1(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:16]


def _enabled_keys(keys: list[str], secs: dict[str, dict[str, Any]]) -> list[str]:
    return [k for k in keys if secs.get(k, {}).get("enabled", True)]


def group_label(sh: dict[str, Any]) -> str | None:
    if sh.get("section_key") != "solution":
        return None
    sol = sh.get("solution_code")
    if sol:
        return (defs.SOLUTIONS.get(sol) or {}).get("name", sol)
    return "통합"


def sheet_from(sh: dict[str, Any], links_by_id: dict[str, dict[str, Any]]) -> M.SheetFrom | None:
    for s in sh.get("sources") or []:
        if s.get("kind") == "link" and s.get("ref") in links_by_id:
            ln = links_by_id[s["ref"]]
            f = ln.get("feature") or s.get("feature") or ""
            return M.SheetFrom(service=f, sheet_id=(ln.get("item_sheet_ids") or {}).get(sh["id"]) or ln.get("ref_id"), ref_id=ln.get("ref_id"))
    return None


async def section_view(pid: str, key: str) -> M.SectionView:
    p, keys, sec = await _ctx(pid, key)
    secs = {s["key"]: s for s in await core.sections_of(pid)}
    enabled = _enabled_keys(keys, secs)
    all_sheets = await core.sheets_of(pid)
    by_sec: dict[str, list[dict[str, Any]]] = {}
    for sh in all_sheets:
        by_sec.setdefault(sh["section_key"], []).append(sh)
    shs = by_sec.get(key, []) if sec.get("enabled", True) else []
    cur_no = keys.index(key) + 1
    name = defs.SECTIONS[key]["name"]
    rail = []
    for i, k in enumerate(keys):
        s = secs.get(k) or {}
        rail.append(M.RailItem(key=k, label=defs.SECTIONS[k]["short"], count=len(by_sec.get(k, [])) if s.get("enabled", True) else 0,
                               done=bool(s.get("confirmed")), optional=bool(s.get("optional")), current=(k == key), enabled=bool(s.get("enabled", True)),
                               title=f"{defs.SECTIONS[k]['name']} (선택 섹션)" if s.get("optional") else None, route=core.section_route(pid, k)))
    total_sheets = sum(len(by_sec.get(k, [])) for k in enabled)
    lns = await L.section_links(pid, key, p.get("type"))
    links_by_id = {ln["id"]: ln for ln in lns}
    sources = [M.SourceChip(id=ln["id"], feature=ln.get("feature") or "", feature_label=defs.FEATURE_LABEL.get(ln.get("feature") or "", ""),
                            label=L.link_label(ln), stale=bool(ln.get("stale")),
                            route=((ln.get("handoff") or {}).get("source") or {}).get("route") or ln.get("route"), ref=L.shell_ref(ln))
               for ln in lns if (ln.get("feature") or "") != "requirements"]
    open_by = await core.open_confirm_by_sheet(pid)
    cat = await clients.export_catalog()
    filling = sec.get("status") == "filling"
    sheets = []
    for sh in shs:
        t = sh.get("template") or {}
        st_label = "작성 중" if filling and sh.get("status") in ("need", "ready", "updated") else core.sheet_status_label(sh)
        sheets.append(M.SectionSheet(
            id=sh["id"], sheet_no=int(sh.get("sheet_no") or 0), title=sh.get("title") or "", role=sh.get("role") or "",
            role_name=core.role_name(sh.get("role")), thumb_url=core.sheet_thumb(sh), tag=core.tag_of(t), template=t.get("code"),
            template_info=template_state(t, cat), status="filling" if filling and sh.get("status") == "need" else (sh.get("status") or "need"),
            status_label=st_label, inferred=bool(sh.get("inferred")), evidence_note=sh.get("evidence_note"), open_confirm=open_by.get(sh["id"], 0),
            solution_code=sh.get("solution_code"), group_label=group_label(sh), **{"from": sheet_from(sh, links_by_id)},
            edited_since_version=bool(sh.get("edited_since_version"))))
    d = defs.SECTIONS[key]
    sidebar = list(d.get("sidebar") or [])
    items = list(d.get("items") or [])
    chips = ([f"{d['sidebar_label']} (사이드바)"] if d.get("sidebar_label") else []) + [
        {"product": "제품", "solution": "솔루션", "image": "이미지", "case": "유관 사례"}[x] for x in items]
    # 이전 · 다음
    pos = enabled.index(key) if key in enabled else keys.index(key)
    if pos <= 0:
        prev = M.RouteRef(label="이전", route=core.route(pid, "compose"))
    else:
        prev = M.RouteRef(label="이전", route=core.section_route(pid, enabled[pos - 1]))
    if pos + 1 < len(enabled):
        nk = enabled[pos + 1]
        nxt = M.RouteRef(label=f"다음: {defs.SECTIONS[nk]['short']}", route=core.section_route(pid, nk))
    else:
        nxt = M.RouteRef(label="다음: 디자인 템플릿", route=core.route(pid, "design"))
    has_input = inputs.section_has_input(key, lns, p)
    sig = await fill_signature(pid, key) if has_input else None
    status = sec.get("status") or "empty"
    needs_fill = bool(sec.get("enabled", True) and has_input and status != "filling" and shs
                      and (status in ("stale",) or sec.get("fill_sig") != sig))
    reuse_view = None
    df = p.get("derived_from") or {}
    if df.get("reuse_id") and key in (df.get("sections") or keys):
        reuse_view = "guide" if df.get("mode") == "borrow" else "compare"
    fill_job = sec.get("fill_job_id") if filling else None
    return M.SectionView(
        proposal_id=pid, type=p["type"], type_name=core.type_name(p.get("type")) or "", key=key, name=name, short=d["short"],
        no=cur_no, total=len(keys), section_no=cur_no, rail=rail, total_sheets=total_sheets, intro=d["intro"], sources=sources,
        sheets=sheets, sheet_label=f"시트 {len(sheets)}", header_label=f"{name} · 섹션 {cur_no} / {len(keys)} · 시트 {len(sheets)}",
        accepts=M.Accepts(sidebar=sidebar, items=items), accept_chips=chips,
        drop_hint=M.DropHint(sidebar=["놓으면 이 섹션에 필요한 내용만 추출합니다", f"추출 결과를 확인한 뒤 {name} 시트에 반영됩니다"],
                             item=["여기에 놓아 「{{항목}}」 추가", f"→ {name} · 관련 시트가 함께 업데이트됩니다"]),
        quick_actions=list(d.get("quick") or []), placeholder=f"{name} 수정 요청 (예: 시트 순서 바꾸기, 내용 보강)",
        prev=prev, next=nxt, status=status if status in ("empty", "filling", "ready", "stale") else "ready",
        status_label=core.section_status_label(sec), fill_job_id=fill_job, optional=bool(sec.get("optional")), enabled=bool(sec.get("enabled", True)),
        confirmed=bool(sec.get("confirmed")), inferred=bool(sec.get("inferred")), owner_name=p.get("owner_name") or "",
        reuse_view=reuse_view, needs_fill=needs_fill)


async def get_section(pid: str, key: str) -> M.SectionView:
    p, keys, _sec = await _ctx(pid, key)
    if p.get("current_section_key") != key or core.STAGE_RANK.get(p.get("stage") or "customer", 0) < core.STAGE_RANK["sections"]:
        def fn(x: dict[str, Any]) -> None:
            x["current_section_key"] = key
            core.advance_stage(x, "sections")
        await core.mutate(pid, fn, bump=False)
        await core.index(pid)
    await L.check_stale(pid)
    return await section_view(pid, key)


# ── 채우기 · 수정 요청 ─────────────────────────────────────
async def start_fill(pid: str, key: str, *, mode: str, request_text: str | None = None, quick_action: str | None = None,
                     sheet_ids: list[str] | None = None, origin: str = "section_fill", reuse_running: bool = True) -> M.JobAccepted:
    _p, _keys, sec = await _ctx(pid, key)
    if reuse_running and sec.get("status") == "filling" and await G.running(sec.get("fill_job_id")):
        return M.JobAccepted(job_id=sec["fill_job_id"], status="running", kind="proposal.section_fill", proposal_id=pid, section_key=key)
    p = await core.load(pid)
    payload = {"proposal_id": pid, "section_key": key, "mode": mode, "request_text": request_text, "quick_action": quick_action,
               "sheet_ids": sheet_ids, "origin": origin}
    title = f"{defs.SECTIONS[key]['name']} " + ("수정 요청" if mode == "request" else "작성")
    job_id = await G.enqueue("proposal.section_fill", payload, title=title, ref=pid, project_id=p.get("project_id"))

    def fn(s: dict[str, Any]) -> None:
        if s.get("status") != "filling":
            s["status_before_fill"] = s.get("status") or "empty"
        s["status"] = "filling"
        s["fill_job_id"] = job_id
    await repo.amutate("sections", sec["id"], fn)
    return M.JobAccepted(job_id=job_id, status="queued", kind="proposal.section_fill", proposal_id=pid, section_key=key)


async def fill_section(pid: str, key: str, body: M.SectionFill) -> M.JobAccepted:
    qa = body.quick_action
    if qa:
        d = defs.QUICK_ACTIONS.get(qa)
        if d is None or qa not in (defs.SECTIONS.get(key, {}).get("quick") or []):
            raise unprocessable("QUICK_ACTION_UNKNOWN", "이 섹션에 없는 빠른 요청이에요", quick_action=qa)
        if not d.get("job"):
            raise unprocessable("QUICK_ACTION_NO_JOB", "이 빠른 요청은 화면에서 처리해요", quick_action=qa, panel=d.get("panel"),
                                navigate=d.get("navigate"), prefill=d.get("prefill"))
        return await start_fill(pid, key, mode="request", request_text=d.get("text"), quick_action=qa, reuse_running=False)
    return await start_fill(pid, key, mode="draft")


async def section_request(pid: str, key: str, body: M.TextRequest) -> M.JobAccepted:
    return await start_fill(pid, key, mode="request", request_text=body.text.strip(), reuse_running=False)


async def confirm_section(pid: str, key: str) -> M.SectionConfirmResult:
    p, keys, sec = await _ctx(pid, key)
    await repo.amutate("sections", sec["id"], lambda s: s.update({"confirmed": True}))
    secs = {s["key"]: s for s in await core.sections_of(pid)}
    enabled = _enabled_keys(keys, secs)
    pos = enabled.index(key) if key in enabled else -1
    nk = enabled[pos + 1] if 0 <= pos < len(enabled) - 1 else None

    def fn(x: dict[str, Any]) -> None:
        if nk:
            x["current_section_key"] = nk
            core.advance_stage(x, "sections")
        else:
            core.advance_stage(x, "design")
    await core.mutate(pid, fn)
    await core.index(pid)
    nxt = (M.RouteRef(label=f"다음: {defs.SECTIONS[nk]['short']}", route=core.section_route(pid, nk)) if nk
           else M.RouteRef(label="다음: 디자인 템플릿", route=core.route(pid, "design")))
    return M.SectionConfirmResult(next=nxt, proposal=await core.proposal_view(pid))


# ── 템플릿 ─────────────────────────────────────────────────
async def refill_content(pid: str, sh: dict[str, Any], *, keep_user_text: bool = True) -> dict[str, Any]:
    """템플릿이 바뀐 시트 — 의미 본문(draft)을 새 칸 정의로 다시 채운다(사용자가 고친 제목 · 부제 · 노트는 지킨다)."""
    p = await core.load(pid)
    t = sh.get("template") or {}
    detail = await clients.export_template_detail(t["code"], t.get("product_count")) if t.get("code") else None
    schema = (detail or {}).get("slot_schema")
    body = dict(sh.get("draft") or {})
    if not body:
        return sh.get("content") or {}
    body["source_list"] = [{"label": s.get("label"), "url": s.get("url")} for s in sh.get("sources") or [] if s.get("url")][:3]
    new = C.fill_slots(schema, body, section_key=sh["section_key"], sheet=sh, p=p, section_no=core.section_no(p.get("type"), sh["section_key"]))
    old = sh.get("content") or {}
    if keep_user_text:
        for k in ("title", "subtitle", "notes"):
            if any(path == f"/{k}" or path.startswith(f"/{k}/") for path in sh.get("edited_paths") or []) and old.get(k):
                new[k] = old[k]
    return new


async def _apply_template(pid: str, sid: str, *, mode: str, code: str | None, product_count: int | None, by_user: bool = True) -> dict[str, Any]:
    p = await core.load(pid)
    sh = await core.sheet_doc(pid, sid)
    cat = await clients.export_catalog()
    old_code = (sh.get("template") or {}).get("code")
    sh_before_t = copy.deepcopy(sh.get("template") or {})
    sh_before_c = copy.deepcopy(sh.get("content") or {})
    t = dict(sh.get("template") or {})
    if product_count is not None and sh.get("role") == "PI":
        t["product_count"] = max(1, min(5, int(product_count)))
        sh["signals"] = {**(sh.get("signals") or {}), "products_n": t["product_count"]}
    sh["template"] = t
    rec = templates.recommend(sh, p, cat, birdseye=bool(((p.get("ctx") or {}).get("has") or {}).get("birdseye")))
    if mode == "auto":
        t["mode"] = "auto"
        t["locked_manual"] = False
        templates.apply_recommendation(sh, rec, force=True)
    else:
        if not code:
            raise unprocessable("TEMPLATE_REQUIRED", "고를 템플릿 코드를 알려 주세요")
        if cat and code not in cat:
            raise not_found("템플릿", code, "TEMPLATE_NOT_FOUND")
        if cat and not templates.available(cat, code):
            raise unprocessable("TEMPLATE_NOT_READY", "아직 제작 중인 템플릿이에요", code=code)
        t["recommended_code"] = rec.get("code")
        t["reason"] = rec.get("reason")
        t["code"] = code
        t["mode"] = "pinned"
        t["source"] = "user"
        if sh.get("role") == "PI" and re.fullmatch(r"P[1-5]-[A-D]", code):
            t["product_count"] = int(code[1])
    sh["template"] = t
    new_content = await refill_content(pid, sh)
    changed = new_content != (sh.get("content") or {})

    def save(x: dict[str, Any]) -> None:
        x["template"] = t
        x["signals"] = sh.get("signals") or x.get("signals")
        if changed:
            x["content"] = new_content
            x["content_rev"] = int(x.get("content_rev") or 0) + 1
        if by_user and int(p.get("saved_version") or 0) > 0:
            x["edited_since_version"] = True
    saved, _ = await repo.amutate("sheets", sid, save)
    if t.get("code") != old_code:
        await core.record_change(pid, sheet=saved, where="템플릿", kind="template", path="/template", from_=old_code, to=t.get("code"),
                                 by_w=not by_user, summary=f"{int(saved.get('sheet_no') or 0):02d} 템플릿 {old_code or '—'} → {t.get('code')}",
                                 extra={"op": "template", "from_full": {"template": sh_before_t, "content": sh_before_c}, "to_full": None})
    return saved


async def put_template(pid: str, sid: str, body: M.TemplatePut) -> M.TemplateApplyResult:
    p = await core.load(pid)
    sh = await core.sheet_doc(pid, sid)
    split = False
    if body.product_count is not None and sh.get("role") == "PI" and body.product_count > 5:
        raise unprocessable("PRODUCT_COUNT_RANGE", "시트 하나에는 제품을 5개까지 넣어요", product_count=body.product_count)
    saved = await _apply_template(pid, sid, mode=body.mode, code=body.code, product_count=body.product_count)
    await core.touch(pid, user_edit=int(p.get("saved_version") or 0) > 0)
    facts_all = await F.facts_of(pid)
    return M.TemplateApplyResult(sheets=[await sheet_view(saved, facts_all=facts_all)], split=split)


async def section_templates_auto(pid: str, key: str, body: M.TemplatesAuto) -> M.SectionView:
    _p, _keys, _sec = await _ctx(pid, key)
    for sh in await core.sheets_of(pid, section_key=key):
        t = sh.get("template") or {}
        if t.get("mode") == "pinned" and not body.include_pinned:
            continue
        await _apply_template(pid, sh["id"], mode="auto", code=None, product_count=None)
    await core.touch(pid)
    return await section_view(pid, key)


async def template_options(pid: str, sid: str, product_count: int | None) -> M.TemplateOptions:
    p = await core.load(pid)
    sh = await core.sheet_doc(pid, sid)
    cat = await clients.export_catalog()
    t = sh.get("template") or {}
    role = sh.get("role") or ""
    pc = product_count or t.get("product_count") or (sh.get("signals") or {}).get("products_n")
    probe = copy.deepcopy(sh)
    if product_count and role == "PI":
        probe.setdefault("template", {})["product_count"] = product_count
        probe["signals"] = {**(probe.get("signals") or {}), "products_n": product_count}
    rec = templates.recommend(probe, p, cat, birdseye=bool(((p.get("ctx") or {}).get("has") or {}).get("birdseye")))
    cands = templates.candidate_codes(sh, p, pc)
    cur = t.get("code")
    mode = t.get("mode") or "auto"
    variants = []
    for code, kind in cands:
        name, when = templates.local_name(code)
        ct = cat.get(code) or {}
        if kind == "industry" and code not in cat and cat:
            continue
        tag = None
        if code == cur:
            tag = "직접" if mode == "pinned" else "자동"
        elif code == rec.get("code"):
            tag = "추천"
        variants.append(M.TemplateVariant(code=code, name=ct.get("name") if (ct.get("name") and kind != "industry" and name == code) else name,
                                          when=when or ct.get("when") or ct.get("description") or "", thumb_url=core.thumb_url(code) or "",
                                          kind=kind, tag=tag, selected=(code == cur), available=templates.available(cat, code)))
    title = sh.get("title") or core.role_name(role)
    msg = (defs.ROLES.get(role) or {}).get("msg", "")
    shs = await core.sheets_of(pid, section_key=sh["section_key"])
    if len(shs) > 5 and sh["section_key"] == "solution":
        g = group_label(sh)
        grp = [x for x in shs if group_label(x) == g]
        k = next((i + 1 for i, x in enumerate(grp) if x["id"] == sid), 1)
        sheet_label = f"{g} 시트 {k} · 섹션 전체 {len(shs)}"
    else:
        k = next((i + 1 for i, x in enumerate(shs) if x["id"] == sid), 1)
        sheet_label = f"시트 {k}"
    products: list[str] = []
    split_note = None
    if role == "PI":
        body = sh.get("draft") or {}
        products = [x.get("model") or x.get("name") for x in body.get("products") or [] if x.get("model") or x.get("name")]
        split_note = "6개 이상이면 2장으로 나눠요 (7 → 4 + 3)"
    pinned = sum(1 for x in shs if (x.get("template") or {}).get("mode") == "pinned")
    return M.TemplateOptions(
        sheet=M.TemplateSheetInfo(id=sid, title=title, role=role, role_name=core.role_name(role), msg=msg),
        header_label=f"{title} · “{msg}”를 보여줄 템플릿 {len(variants)}종", sheet_label=sheet_label, mode=mode, current_code=cur,
        recommended={"code": rec.get("code"), "reason": rec.get("reason")},
        reason_line=f"{rec.get('code')} 추천 · {rec.get('reason')}" if rec.get("reason") else f"{rec.get('code') or ''} 추천".strip(),
        variants=variants, product_count=int(pc) if pc and role == "PI" else None, products=products,
        products_label=" · ".join(products), split_note=split_note, pinned_in_section=pinned,
        auto_all_confirm=f"직접 고른 {pinned}장도 자동으로 바꿔요" if pinned else None)


# ── 시트 읽기 · 고치기 ─────────────────────────────────────
async def get_sheet(pid: str, sid: str) -> M.Sheet:
    await core.load(pid)
    sh = await core.sheet_doc(pid, sid)
    return await sheet_view(sh)


def _unescape(part: str) -> str:
    return part.replace("~1", "/").replace("~0", "~")


def _parts(path: str) -> list[str]:
    if not path.startswith("/"):
        raise unprocessable("BAD_PATH", "경로는 /로 시작해요", path=path)
    return [_unescape(x) for x in path[1:].split("/")] if path != "/" else []


def _resolve(doc: Any, parts: list[str], *, create: bool = False) -> tuple[Any, str]:
    cur = doc
    for i, part in enumerate(parts[:-1]):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError) as exc:
                raise unprocessable("BAD_PATH", "그 위치를 찾지 못했어요", path="/" + "/".join(parts)) from exc
        elif isinstance(cur, dict):
            if part not in cur:
                if not create:
                    raise unprocessable("BAD_PATH", "그 위치를 찾지 못했어요", path="/" + "/".join(parts))
                nxt = parts[i + 1]
                cur[part] = [] if nxt.isdigit() or nxt == "-" else {}
            cur = cur[part]
        else:
            raise unprocessable("BAD_PATH", "그 위치를 찾지 못했어요", path="/" + "/".join(parts))
    return cur, parts[-1] if parts else ""


def _get(doc: Any, path: str) -> Any:
    parts = _parts(path)
    if not parts:
        return doc
    parent, last = _resolve(doc, parts)
    try:
        return parent[int(last)] if isinstance(parent, list) else parent.get(last)
    except (ValueError, IndexError):
        return None


def _with_ids(v: Any) -> Any:
    if isinstance(v, dict):
        out = {k: _with_ids(x) for k, x in v.items()}
        if "text" in out and "id" not in out:
            out["id"] = C.lid("l")
        return out
    if isinstance(v, list):
        return [_with_ids(x) for x in v]
    return v


def apply_op(doc: dict[str, Any], op: M.SheetOp) -> tuple[Any, Any]:
    """JSON pointer 연산 하나 → (전 값, 후 값)."""
    parts = _parts(op.path)
    if op.op == "set":
        if not parts:
            raise unprocessable("BAD_PATH", "시트 전체는 바꿀 수 없어요")
        parent, last = _resolve(doc, parts, create=True)
        val = _with_ids(op.value)
        if isinstance(parent, list):
            i = len(parent) if last == "-" else int(last)
            before = parent[i] if i < len(parent) else None
            if i >= len(parent):
                parent.append(val)
            else:
                parent[i] = val
        else:
            before = parent.get(last)
            parent[last] = val
        return before, val
    if op.op == "insert":
        parent, last = _resolve(doc, parts, create=True)
        val = _with_ids(op.value)
        if not isinstance(parent, list):
            parent[last] = val
            return None, val
        i = len(parent) if last == "-" else int(last)
        parent.insert(i, val)
        return None, val
    if op.op == "delete":
        parent, last = _resolve(doc, parts)
        if isinstance(parent, list):
            i = int(last)
            if i >= len(parent):
                raise unprocessable("BAD_PATH", "그 위치를 찾지 못했어요", path=op.path)
            return parent.pop(i), None
        if last not in parent:
            raise unprocessable("BAD_PATH", "그 위치를 찾지 못했어요", path=op.path)
        return parent.pop(last), None
    if op.op == "move":
        if not op.from_path:
            raise unprocessable("BAD_PATH", "move 에는 from 이 필요해요")
        val = copy.deepcopy(_get(doc, op.from_path))
        apply_op(doc, M.SheetOp(op="delete", path=op.from_path))
        apply_op(doc, M.SheetOp(op="insert", path=op.path, value=val))
        return op.from_path, op.path
    raise unprocessable("BAD_OP", "모르는 편집 연산이에요", op=op.op)


def where_label(content: dict[str, Any], path: str) -> tuple[str, str]:
    """(위치 라벨, 종류) — 「제목」 · 「6행 · 경쟁사 B」 · 「노트」."""
    parts = _parts(path) if path.startswith("/") else []
    if not parts:
        return "시트", "content"
    head = parts[0]
    if head == "title":
        return "제목", "text"
    if head == "subtitle":
        return "부제", "text"
    if head == "notes":
        return "노트", "notes"
    if head == "footnotes":
        return "각주", "text"
    if head == "slots" and len(parts) >= 2:
        slot = parts[1]
        v = (content.get("slots") or {}).get(slot)
        if isinstance(v, dict) and "rows" in v and len(parts) >= 4 and parts[2] == "rows":
            r = int(parts[3]) if parts[3].isdigit() else 0
            label = f"{r + 1}행"
            if len(parts) >= 6 and parts[4] == "cells" and parts[5].isdigit():
                cols = v.get("columns") or []
                ci = int(parts[5]) + 1
                if ci < len(cols):
                    label += f" · {cols[ci]}"
            return label, "text"
        if isinstance(v, dict) and len(parts) >= 3 and parts[2] == "columns":
            return "머리글", "format"
        if isinstance(v, list) and len(parts) >= 3 and parts[2].isdigit():
            return f"{slot} {int(parts[2]) + 1}", "text"
        return slot, "text"
    return head, "text"


async def patch_sheet(pid: str, sid: str, body: M.SheetPatch, if_match: str | None) -> M.SheetPatchResult:
    p = await core.load(pid)
    sh = await core.sheet_doc(pid, sid)
    cur_rev = int(sh.get("content_rev") or 0) + 1
    if if_match not in (None, "", "*"):
        try:
            want = int(str(if_match).strip().strip('"').removeprefix("W/").strip('"'))
        except ValueError:
            want = cur_rev
        if want != cur_rev:
            raise rev_conflict(cur_rev)
    before_open = {it["id"] for it in await repo.alist("confirm_items", {"proposal_id": pid}) if it.get("status") == "open"}
    records: list[tuple[str, str, str, Any, Any]] = []

    def fn(x: dict[str, Any]) -> None:
        content = copy.deepcopy(x.get("content") or {})
        records.clear()
        for op in body.ops:
            where, kind = where_label(content, op.path)
            b, a = apply_op(content, op)
            records.append((where, kind, op.path, b, a))
        x["content"] = content
        x["content_rev"] = int(x.get("content_rev") or 0) + 1
        x["user_edited"] = True
        x["edited_paths"] = list(dict.fromkeys([*(x.get("edited_paths") or []), *[op.path for op in body.ops]]))[-50:]
        if int(p.get("saved_version") or 0) > 0:
            x["edited_since_version"] = True
        if x.get("status") in ("need",):
            x["status"] = "ready"
    saved, _ = await repo.amutate("sheets", sid, fn)
    ids = []
    for (where, kind, path, b, a), op in zip(records, body.ops):
        ids.append(await core.record_change(pid, sheet=saved, where=where, kind=kind, path=path, from_=core.snippet(b, 60),
                                            to=core.snippet(a, 60), reason=body.reason,
                                            summary=f"{int(saved.get('sheet_no') or 0):02d} {where}",
                                            extra={"op": op.op, "from_full": b, "to_full": a, "move_from": op.from_path}))
    # 새로 쓴 플레이스홀더 → 값 + 확인 항목, 없어진 값 → 항목 닫기
    content = saved.get("content") or {}
    if any(C.placeholders_in(t) for t in [json.dumps(content, ensure_ascii=False)]):
        new_content, made = await F.tokenize(pid, content, sheet_title=saved.get("title") or "", origin="user_edit")
        if made:
            saved, _ = await repo.amutate("sheets", sid, lambda x: x.update({"content": new_content}))
            await F.items_for_tokens(pid, saved, made, origin="user_edit", reason="직접 넣은 자리표시예요")
    await F.sync_items(pid)
    after_open = {it["id"] for it in await repo.alist("confirm_items", {"proposal_id": pid}) if it.get("status") == "open"}
    p2 = await core.touch(pid, user_edit=True)
    await core.index(pid)
    view = await sheet_view(saved)
    return M.SheetPatchResult(sheet=view, change_ids=ids, rev=view.rev, resolved_item_ids=sorted(before_open - after_open),
                              edits_since_version=int(p2.get("edits_since_version") or 0))


# ── 다시 쓰기 · 전체 요청 · 노트 (잡) ──────────────────────
async def rewrite_sheet(pid: str, sid: str, body: M.SheetRewrite) -> M.JobAccepted:
    p = await core.load(pid)
    sh = await core.sheet_doc(pid, sid)
    payload = {"proposal_id": pid, "sheet_id": sid, "target_path": body.target_path, "instruction": body.instruction,
               "options": body.options.model_dump()}
    job_id = await G.enqueue("proposal.sheet_rewrite", payload, title=f"{int(sh.get('sheet_no') or 0):02d} {sh.get('title')} 다듬기", ref=pid,
                             project_id=p.get("project_id"))
    if body.instruction:
        await G.save_message(pid, scope="sheet", scope_ref=sid, role="user", text=body.instruction, job=job_id)
    return M.JobAccepted(job_id=job_id, kind="proposal.sheet_rewrite", proposal_id=pid, sheet_id=sid)


async def proposal_request(pid: str, body: M.TextRequest) -> M.JobAccepted:
    p = await core.load(pid)
    job_id = await G.enqueue("proposal.request", {"proposal_id": pid, "text": body.text.strip()}, title="제안서 수정 요청", ref=pid,
                             project_id=p.get("project_id"))
    await G.save_message(pid, scope="proposal", scope_ref=None, role="user", text=body.text.strip(), job=job_id)
    return M.JobAccepted(job_id=job_id, kind="proposal.request", proposal_id=pid)


async def notes_generate(pid: str, body: M.NotesGenerate) -> M.JobAccepted:
    p = await core.load(pid)
    job_id = await G.enqueue("proposal.notes_generate", {"proposal_id": pid, "only_empty": body.only_empty}, title="발표자 노트 만들기", ref=pid,
                             project_id=p.get("project_id"))
    return M.JobAccepted(job_id=job_id, kind="proposal.notes_generate", proposal_id=pid)


# ── 대화 ───────────────────────────────────────────────────
async def messages(pid: str, *, scope: str | None, scope_ref: str | None) -> M.MessageList:
    await core.load(pid)
    rows = await repo.alist("messages", {"proposal_id": pid})
    out = []
    for m in rows:
        if scope and m.get("scope") != scope:
            continue
        if scope_ref and m.get("scope_ref") != scope_ref:
            continue
        out.append(M.Message(id=m["id"], scope=m.get("scope") or "proposal", scope_ref=m.get("scope_ref"), role=m.get("role") or "w",
                             text=m.get("text") or "", change_ids=m.get("change_ids") or [], job_id=m.get("job_id"),
                             created_at=m.get("created_iso") or m.get("created_at") or ""))
    out.sort(key=lambda x: x.created_at)
    return M.MessageList(items=out)


# ── 값(fact) ───────────────────────────────────────────────
def fact_view(f: dict[str, Any], by_key: dict[str, dict[str, Any]], uses: list[dict[str, Any]]) -> M.Fact:
    ev = f.get("evidence") or None
    formula_label = None
    if f.get("formula"):
        m = re.fullmatch(r"\s*([a-z_][a-z0-9_]*)\s*([*+])\s*(\d+(?:\.\d+)?)\s*", f["formula"])
        if m:
            base = by_key.get(m.group(1)) or {}
            formula_label = f"{f.get('label')} = {base.get('label') or m.group(1)} {'×' if m.group(2) == '*' else '+'} {m.group(3).rstrip('0').rstrip('.') if '.' in m.group(3) else m.group(3)}{f.get('unit') or ''}"
    return M.Fact(id=f["id"], key=f.get("key") or "", label=f.get("label") or "", value=f.get("value"), unit=f.get("unit"),
                  kind=f.get("kind") or "input", formula=f.get("formula"), formula_label=formula_label, status=f.get("status") or "placeholder",
                  placeholder=f.get("placeholder") or "[00]", display=C.fact_display(f, by_key),
                  evidence=M.FactEvidence(**ev) if isinstance(ev, dict) and ev.get("kind") in ("url", "file", "work", "internal_doc", "customer", "user") else None,
                  origin=f.get("origin") or {}, used_in=[M.FactUse(**u) for u in uses], history=f.get("history") or [])


async def list_facts(pid: str) -> M.FactList:
    await core.load(pid)
    facts_all = await F.facts_of(pid)
    by_key = {f.get("key"): f for f in facts_all.values()}
    uses = await F.used_in(pid)
    items = [fact_view(f, by_key, uses.get(f["id"], [])) for f in facts_all.values()]
    items.sort(key=lambda x: (min([u.sheet_no or 999 for u in x.used_in] or [999]), x.label))
    return M.FactList(items=items)


async def set_fact(pid: str, fid: str, *, value: str | None, unit: str | None, evidence: dict[str, Any] | None, by: dict[str, Any],
                   reason: str = "값 확정") -> tuple[dict[str, Any], list[str], list[str], list[str]]:
    """값을 정하고 그 값을 쓰는 모든 시트에 전파(V3) → (fact, 바뀐 시트, 변경 id, 닫힌 항목)."""
    f = await repo.aget("facts", fid)
    if f is None or f.get("proposal_id") != pid:
        raise not_found("값", fid, "FACT_NOT_FOUND")
    old_display = C.fact_display(f, {x.get("key"): x for x in (await F.facts_of(pid)).values()})
    old_value, old_status = f.get("value"), f.get("status")

    def fn(x: dict[str, Any]) -> None:
        hist = list(x.get("history") or [])
        hist.append({"at": config.now_iso(), "by": by, "from": x.get("value"), "to": value, "evidence": evidence})
        x["history"] = hist[-20:]
        x["value"] = value if value not in ("",) else None
        if unit is not None:
            x["unit"] = unit or None
        if evidence:
            x["evidence"] = evidence
        x["status"] = "confirmed" if x["value"] not in (None, "") else "placeholder"
        x["moved_to_note"] = False
    saved, _ = await repo.amutate("facts", fid, fn)
    uses = (await F.used_in(pid)).get(fid, [])
    # 파생 값(합계 = 매장 수 × 3대)도 함께
    dependents = [d for d in (await F.facts_of(pid)).values() if d.get("formula") and (saved.get("key") or "") in (d.get("formula") or "")]
    for d in dependents:
        uses += (await F.used_in(pid)).get(d["id"], [])
    sheet_ids = list(dict.fromkeys(u["sheet_id"] for u in uses))
    change_ids = []
    new_display = C.fact_display(saved, {x.get("key"): x for x in (await F.facts_of(pid)).values()})
    for sid in sheet_ids:
        sh, _ = await repo.amutate("sheets", sid, lambda x: x.update({"content_rev": int(x.get("content_rev") or 0) + 1}))
        change_ids.append(await core.record_change(pid, sheet=sh, where=saved.get("label") or "값", kind="value", path=f"/facts/{fid}",
                                                   from_=old_display, to=new_display, reason=reason,
                                                   summary=f"{int(sh.get('sheet_no') or 0):02d} {saved.get('label')} 확정",
                                                   extra={"op": "fact", "fact_id": fid, "from_full": old_value, "to_full": saved.get("value"),
                                                          "from_status": old_status}))
    closed = []
    if saved.get("status") == "confirmed":
        closed = await F.close_items_for_fact(pid, fid, by=by, value=value, evidence=evidence)
        for d in dependents:
            closed += await F.close_items_for_fact(pid, d["id"], by=by, value=None, evidence=evidence)
    await F.sync_items(pid)
    return saved, sheet_ids, change_ids, closed


async def put_fact(pid: str, fid: str, body: M.FactPut) -> M.FactUpdateResult:
    await core.load(pid)
    saved, sheet_ids, change_ids, _closed = await set_fact(pid, fid, value=body.value, unit=body.unit,
                                                           evidence=body.evidence.model_dump() if body.evidence else None, by=core.actor())
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    facts_all = await F.facts_of(pid)
    by_key = {f.get("key"): f for f in facts_all.values()}
    uses = (await F.used_in(pid)).get(fid, [])
    return M.FactUpdateResult(fact=fact_view(saved, by_key, uses), changed_sheet_ids=sheet_ids, change_ids=change_ids)
