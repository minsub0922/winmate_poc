"""§6.2 제안서 — 목록(PR0) · 만들기 · 읽기 · 고치기 · 지우기 · 제출 표시."""
from __future__ import annotations

import base64
import logging
from typing import Any

from winmate_common.context import current_user
from winmate_common.platform import unregister_item

from .. import clients, config, core, defs, industry, links as L, plan, repo
from .. import models as M
from ..errors import proposal_not_found

log = logging.getLogger("winmate.proposal.ops")


# ── 목록 ───────────────────────────────────────────────────
async def _my_pending_reviews() -> set[str]:
    me = current_user().id
    res = await clients.call("workspace", "GET", "/v1/reviews", params={"mine": "to_review", "status": "pending"}, quiet=True)
    out: set[str] = set()
    for rv in (res or {}).get("items") or []:
        tgt = rv.get("target") or ""
        if not tgt.startswith("proposal:"):
            continue
        mine = next((r for r in rv.get("reviewers") or [] if r.get("user_id") == me), None)
        if mine and (mine.get("decision") or "pending") == "pending" and rv.get("status") in ("pending", "changes_requested"):
            out.add(tgt.split(":")[1])
    return out


async def row_view(p: dict[str, Any], *, me: str, pending: set[str], ws_index: dict[str, dict[str, Any]] | None) -> M.ProposalRow:
    pid = p["id"]
    open_n = await core.open_confirm_count(pid)
    n_links = await core.link_count(pid)
    keys = core.type_sections(p.get("type"))
    cur = p.get("current_section_key")
    pos = (keys.index(cur) + 1, len(keys)) if cur in keys else (1, len(keys) or 1)
    sd, cs = core.steps(p)
    due, dday, urgent = core.due_labels(p)
    badge = None
    cc = int((p.get("comment_counts") or {}).get("open") or 0)
    stale = await L.check_stale(pid, ws_index) if ws_index is not None else []
    if cc:
        badge = M.RowBadge(kind="comments", label=f"코멘트 {cc}", n=cc)
    elif open_n:
        badge = M.RowBadge(kind="confirm_needed", label=f"확인 필요 {open_n}", n=open_n)
    elif stale:
        f = stale[0].get("feature") or ""
        badge = M.RowBadge(kind="source_updated", label=f"{defs.FEATURE_SHORT.get(f, f)} 작업 업데이트됨", n=len(stale))
    sub = core.sub_label(p, link_count=n_links)
    tname = core.type_name(p.get("type")) or "제안서"
    return M.ProposalRow(
        id=pid, title=core.title_display(p), short_title=(p.get("title") or "")[:24] or None, customer_name=(p.get("customer") or {}).get("name") or "",
        industry_label=core.industry_label(p), type=p.get("type"), type_label=core.type_label(p.get("type")), status=p.get("status") or "draft",
        status_label=defs.STATUS_LABEL.get(p.get("status") or "draft", ""), sub_label=sub, subtitle=sub,
        meta=f"{tname} · {defs.STATUS_LABEL.get(p.get('status') or 'draft', '')}", badge=badge, steps_done=sd, current_step=cs,
        progress_label=core.progress_label(p, open_confirm=open_n, section_pos=pos), due_date=(p.get("schedule") or {}).get("submit_due"),
        due_label=due, d_day_label=dday, urgent=urgent, owner=core.owner_of(p),
        action=core.row_action(p, me=me, open_confirm=open_n, my_pending=pid in pending), project_id=p.get("project_id"),
        version=int(p.get("saved_version") or 0), one_click_running=(p.get("one_click") or {}).get("status") in ("running", "queued"),
        updated_at=p.get("touched_at") or p.get("updated_at") or "", route=core.stage_route(p))


def _sort_key_due(p: dict[str, Any]) -> tuple[int, str, str]:
    if p.get("status") == "done":
        return (2, "", p.get("created_iso") or "")
    due = (p.get("schedule") or {}).get("submit_due")
    return (0, due, p.get("created_iso") or "") if due else (1, "", p.get("created_iso") or "")


async def list_proposals(*, tab: str, q: str | None, owner: str, type_: str | None, sort: str, project_id: str | None, limit: int,
                         cursor: str | None) -> M.ProposalList:
    me = current_user().id
    allp = [p for p in await repo.alist("proposals") if not p.get("deleted")]
    if owner == "me":
        allp = [p for p in allp if p.get("owner_id") == me]
    elif owner not in ("all", "", None):
        allp = [p for p in allp if p.get("owner_id") == owner]
    if project_id:
        allp = [p for p in allp if p.get("project_id") == project_id]
    if q:
        ql = q.strip().lower()
        allp = [p for p in allp if ql in (p.get("title") or "").lower() or ql in ((p.get("customer") or {}).get("name") or "").lower()]
    if type_:
        allp = [p for p in allp if p.get("type") in type_.split(",")]
    counts = M.ProposalCounts(all=len(allp), draft=sum(1 for p in allp if p.get("status", "draft") == "draft"),
                              review=sum(1 for p in allp if p.get("status") == "review"), done=sum(1 for p in allp if p.get("status") == "done"))
    tabs = [t.strip() for t in (tab or "all").split(",") if t.strip()]
    rows = allp if "all" in tabs else [p for p in allp if (p.get("status") or "draft") in tabs]
    if sort == "updated_desc":
        rows.sort(key=lambda p: p.get("touched_at") or "", reverse=True)
    else:
        rows.sort(key=_sort_key_due)
    today = config.today_kst()
    due14 = 0
    for p in allp:
        if p.get("status") == "done":
            continue
        d = config.parse_date((p.get("schedule") or {}).get("submit_due"))
        if d and 0 <= (d - today).days <= defs.DUE_SOON_DAYS:
            due14 += 1
    offset = 0
    if cursor:
        try:
            offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
        except Exception:  # noqa: BLE001
            offset = 0
    page = rows[offset:offset + limit]
    nxt = base64.urlsafe_b64encode(str(offset + limit).encode()).decode() if offset + limit < len(rows) else None
    pending = await _my_pending_reviews()
    my_turn = len([p for p in allp if p["id"] in pending and p.get("status") == "review"])
    ws_index = None
    if page:
        items = await clients.ws_items(owner="all", limit=100)
        ws_index = {i["item_id"]: i for i in items}
    out = [await row_view(p, me=me, pending=pending, ws_index=ws_index) for p in page]
    total = len(rows)
    return M.ProposalList(items=out, next_cursor=nxt, counts=counts, total=total, due_within_14d=due14, my_review_turn=my_turn,
                          summary_label=f"전체 {counts.all}건 · 2주 안에 마감 {due14}건 · 내 검토 차례 {my_turn}건",
                          range_label=f"{offset + 1 if page else 0}–{offset + len(page)} / {total}")


# ── 만들기 ─────────────────────────────────────────────────
def _customer_in(c: M.CustomerIn | None) -> dict[str, Any]:
    if not c:
        return {}
    out: dict[str, Any] = {}
    if c.name is not None:
        out["name"] = c.name.strip()
    if c.scale_text is not None:
        out["scale_text"] = c.scale_text
    if c.decision_makers is not None:
        out["decision_makers"] = c.decision_makers
    if c.industry_code:
        code = defs.industry_code_of(c.industry_code)
        if code:
            out["industry_code"] = code
            out["industry_label"] = defs.INDUSTRIES[code]["name"]
            out["industry_user_set"] = True
    if c.industry_label and not out.get("industry_code"):
        code = defs.industry_code_of(c.industry_label)
        if code:
            out["industry_code"] = code
            out["industry_label"] = defs.INDUSTRIES[code]["name"]
            out["industry_user_set"] = True
    return out


async def _apply_chip(pid: str, chip: str | None) -> None:
    codes = industry.chip_codes(chip)
    if not codes:
        return
    p = await core.load(pid)
    det = await industry.detect(p, p.get("ctx") or {}, chip_codes=codes)
    code = (det or {}).get("code") or codes[0]

    def fn(x: dict[str, Any]) -> None:
        c = x.setdefault("customer", {})
        c["industry_code"] = code
        c["industry_label"] = defs.INDUSTRIES[code]["name"]
        c["industry_user_set"] = True
        c["industry_chip"] = chip
    await core.mutate(pid, fn)


async def redetect_industry(pid: str) -> None:
    p = await core.load(pid)
    det = await industry.detect(p, p.get("ctx") or {})

    def fn(x: dict[str, Any]) -> None:
        il = x.setdefault("industry_layout", core.default_industry_layout())
        il["detected"] = det
        if not il.get("decided"):
            il["industry_code"] = (x.get("customer") or {}).get("industry_code") or (det or {}).get("code")
        c = x.setdefault("customer", {})
        if not c.get("industry_user_set") and det and det.get("mode") in ("auto", "check"):
            c["industry_code"] = det["code"]
            c["industry_label"] = defs.INDUSTRIES[det["code"]]["name"]
    await core.mutate(pid, fn, bump=False)


async def create_proposal(body: M.ProposalCreate) -> M.Proposal:
    cust = _customer_in(body.customer)
    doc = core.new_proposal_doc(start_mode=body.start_mode, title=(body.title or "").strip(), customer=cust, project_id=body.project_id,
                                language=body.language or "ko", schedule=body.schedule.model_dump() if body.schedule else None)
    if body.rq_ref:
        doc["rq_ref"] = body.rq_ref.model_dump()
    if body.source_proposal_id:
        doc["reuse_source_hint"] = body.source_proposal_id
        src = await repo.aget("proposals", body.source_proposal_id)
        if src and not cust.get("name"):
            doc["customer"] = {**doc["customer"], **{k: v for k, v in (src.get("customer") or {}).items() if k in ("name", "industry_code",
                                                                                                               "industry_label", "scale_text")}}
    await repo.aput("proposals", doc["id"], doc)
    pid = doc["id"]
    if body.customer and body.customer.industry_chip:
        await _apply_chip(pid, body.customer.industry_chip)
    work_refs: list[str] = [body.rq_ref.rq_id] if body.rq_ref else []
    for ln in body.links:
        link = await L.add_link(pid, feature=ln.feature, ref_id=ln.ref_id, section_key=ln.section_key, version=ln.version,
                                handoff_id=ln.handoff_id, title=ln.title, via="handoff" if body.start_mode == "handoff" else "start")
        await L.apply_customer(pid, link.get("handoff"))
        if link.get("ref_id"):
            work_refs.append(str(link["ref_id"]))
    if body.image_version:
        ver = await clients.call("image", "GET", f"/v1/versions/{body.image_version}", quiet=True)
        if ver and ver.get("image_id"):
            await L.add_link(pid, feature="image", ref_id=ver["image_id"], via="handoff", version=None)
            img = await clients.call("image", "GET", f"/v1/images/{ver['image_id']}", quiet=True)
            if (img or {}).get("work_id"):
                work_refs.append(str(img["work_id"]))   # 이미지 작업(imw_)이 workspace 항목
    if not body.project_id and work_refs:
        # 넘겨받은 작업(정의서 · Storyboard · MI …)의 workspace 프로젝트를 잇는다 — IMG4 · SC5 · BE6 의 「같은 프로젝트 제안서」 기본 선택(통합)
        for ref in work_refs:
            it = await clients.ws_item(ref)
            if it and it.get("project_id"):
                prj = it["project_id"]
                await core.mutate(pid, lambda x, prj=prj: x.update({"project_id": prj}))
                break
    if body.rq_ref:
        from .. import handoff as H
        # 정의서로 시작(RQ4 「B2B 제안서」 · RQ6 「쓰는 곳」 · SB4 ?rq=)이면 정의서의 고객 · 프로젝트명으로 빈 칸을 채운다(§7.3 —
        # Storyboard 연결이 먼저 채운 칸은 그대로). 이게 없으면 `/proposal/new?rq=` 의 PR1 고객사가 비어 있었다(통합).
        rq_snap = await H.fetch("requirements", body.rq_ref.rq_id, proposal_type=None, version=body.rq_ref.version)
        await L.apply_customer(pid, rq_snap)
        p = await core.load(pid)
        await H.register_usage("requirements", body.rq_ref.rq_id, proposal=p, label="고객 정보",
                               version=body.rq_ref.version or ((rq_snap or {}).get("rq_ref") or {}).get("version"))
    await plan.refresh_context(pid)
    await redetect_industry(pid)
    await core.index(pid, force=True)
    return await core.proposal_view(pid)


async def get_proposal(pid: str) -> M.Proposal:
    return await core.proposal_view(pid)


async def patch_proposal(pid: str, body: M.ProposalPatch, if_match: str | None) -> M.Proposal:
    p = await core.load(pid)
    core.check_if_match(p, if_match)
    cust = _customer_in(body.customer)
    chip = body.customer.industry_chip if body.customer else None
    old_name = (p.get("customer") or {}).get("name")
    name_changed = "name" in cust and cust["name"] != old_name
    industry_changed = "industry_code" in cust and cust["industry_code"] != (p.get("customer") or {}).get("industry_code")

    def fn(x: dict[str, Any]) -> None:
        if body.title is not None:
            x["title"] = body.title.strip()
        if cust:
            c = x.setdefault("customer", {})
            c.update(cust)
        if body.schedule is not None:
            sch = x.setdefault("schedule", {})
            for k, v in body.schedule.model_dump(exclude_unset=True).items():
                sch[k] = v
        if body.budget_text is not None:
            x["budget_text"] = body.budget_text
        if body.language is not None:
            x["language"] = body.language
        if body.project_id is not None:
            x["project_id"] = body.project_id
        if body.rq_ref is not None:
            x["rq_ref"] = body.rq_ref.model_dump()
        if body.stage is not None:
            core.advance_stage(x, body.stage)
        if body.current_section_key is not None and body.current_section_key in core.type_sections(x.get("type")):
            x["current_section_key"] = body.current_section_key
        if name_changed or industry_changed:
            il = x.setdefault("industry_layout", core.default_industry_layout())
            il["decided"] = False
            il["applied_codes"] = []
    await core.mutate(pid, fn)
    if chip:
        await _apply_chip(pid, chip)
    if name_changed or industry_changed or body.rq_ref is not None or chip:
        await plan.refresh_context(pid)
        await redetect_industry(pid)
    await core.index(pid)
    return await core.proposal_view(pid)


async def delete_proposal(pid: str) -> None:
    p = await core.load(pid)
    await _release_usages(pid, p)
    await repo.adelete("proposals", pid)
    await unregister_item(pid)


async def _release_usages(pid: str, p: dict[str, Any]) -> None:
    """제안서를 지우면 다른 기능에 남긴 「쓰는 곳」(조감도 · 시나리오 · 이미지 사용 등록, 정의서 링크, VP 「연결된 제안서」, Spec 연결)을 거둔다
    (통합 — 09-scenario 요청). 실패해도 지우기는 막지 않는다."""
    from .. import handoff as H
    try:
        done: set[tuple[str, str]] = set()
        for ln in await repo.alist("links", {"proposal_id": pid}):
            f, ref = defs.norm_feature(ln.get("feature") or "") or (ln.get("feature") or ""), ln.get("ref_id") or ""
            key = (f, "" if f == "spec" else ref)
            if f in ("birdseye", "scenario", "vp", "spec") and (ref or f == "spec") and key not in done:
                done.add(key)
                await H.unregister_usage(f, key[1], proposal_id=pid)
        for imp in await repo.alist("imports", {"proposal_id": pid}):
            src = imp.get("source") or {}
            if src.get("service") == "image" and imp.get("usage_ref") and imp.get("status") == "applied":
                await H.unregister_usage("image", src.get("image_id") or "", proposal_id=pid, sheet_ref=imp["usage_ref"])
        rq = (p.get("rq_ref") or {}).get("rq_id")
        if rq:
            await H.unregister_usage("requirements", rq, proposal_id=pid)
    except Exception as exc:  # noqa: BLE001
        log.warning("사용 등록 거두기 실패 %s: %s", pid, exc)


async def mark_submitted(pid: str, body: M.MarkSubmitted) -> M.Proposal:
    def fn(x: dict[str, Any]) -> None:
        x["status"] = "done"
        x["submitted_at"] = body.submitted_at or config.now_iso()
        core.advance_stage(x, "result")
    await core.mutate(pid, fn)
    await core.index(pid)
    return await core.proposal_view(pid)


async def must(pid: str) -> dict[str, Any]:
    p = await repo.aget("proposals", pid)
    if p is None:
        raise proposal_not_found(pid)
    return p
