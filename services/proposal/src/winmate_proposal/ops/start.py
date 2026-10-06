"""§6.3 시작 방식 — RFP(PR1F) · 기존 작업(PR1L) · 연결 자료."""
from __future__ import annotations

import re
from typing import Any

from .. import clients, config, core, defs, handoff, industry, links as L, plan, repo
from .. import models as M
from ..errors import file_too_large, not_found, unprocessable, unsupported_file
from ..graphs import common as G
from ..graphs.start import RFP_FIELDS, STATE_LABEL

RFP_EXT = (".pdf", ".docx", ".pptx", ".txt", ".eml", ".hwp")
NUM = "①②③④⑤⑥⑦⑧⑨"


# ── RFP(PR1F) ──────────────────────────────────────────────
async def _check_file(fid: str, *, extra: bool = False) -> dict[str, Any]:
    meta = await clients.file_meta(fid)
    if not meta:
        raise not_found("파일", fid, "FILE_NOT_FOUND")
    if int(meta.get("size") or 0) > defs.FILE_MAX_MB * 1024 * 1024:
        raise file_too_large()
    name = (meta.get("name") or "").lower()
    ok_kinds = ("pdf", "docx", "pptx", "text", "email")
    if (meta.get("kind") not in ok_kinds) and not name.endswith(RFP_EXT):
        raise unsupported_file("PDF · DOCX · PPTX · TXT" + (" · 메일(.eml)" if extra else "") + "만 올릴 수 있어요")
    return meta


async def start_rfp(pid: str, body: M.RfpStart) -> M.JobAccepted:
    p = await core.load(pid)
    for fid in body.file_ids:
        await _check_file(fid)
    for fid in body.extra_file_ids:
        await _check_file(fid, extra=True)
    job_id = await G.enqueue("proposal.rfp_extract", {"proposal_id": pid, "file_ids": body.file_ids, "extra_file_ids": body.extra_file_ids},
                             title="RFP 읽기", ref=pid, project_id=p.get("project_id"))

    def fn(x: dict[str, Any]) -> None:
        x["start_mode"] = "rfp"
        x["start_files"] = list(dict.fromkeys([*body.file_ids, *body.extra_file_ids]))
        x["rfp"] = {"status": "running", "job_id": job_id, "file_ids": body.file_ids, "extra_file_ids": body.extra_file_ids,
                    "phases": [{"key": k, "label": lb, "status": "busy" if i == 0 else "todo"} for i, (k, lb) in
                               enumerate((("read", "읽기"), ("locate", "항목 찾기"), ("fill", "채우기")))],
                    "fields": [], "excerpts": [], "confirmed": False}
        core.set_job(x, "rfp", job_id)
    await core.mutate(pid, fn)
    await core.index(pid)
    return M.JobAccepted(job_id=job_id, kind="proposal.rfp_extract", proposal_id=pid)


def _kind_label(f: dict[str, Any]) -> str:
    kind = {"pdf": "PDF", "docx": "DOCX", "pptx": "PPTX", "text": "TXT", "email": "메일"}.get(f.get("kind") or "", (f.get("kind") or "").upper())
    n = f.get("pages")
    return " · ".join(x for x in (kind, f"{n}쪽" if n else "", "방금 올림") if x)


async def rfp_view(pid: str) -> M.RfpView:
    p = await core.load(pid)
    r = p.get("rfp") or {}
    st = r.get("status") or "none"
    if st == "running" and not await G.running(r.get("job_id")):
        st = "failed" if not r.get("fields") else "done"
    fields = []
    for f in r.get("fields") or []:
        src = f.get("source") or None
        fields.append(M.RfpField(no=f["no"], key=f["key"], label=f["label"], value=f.get("value") or "",
                                 source=M.RfpSource(**src) if src else None,
                                 source_label=f"p.{src['page']}" if (src or {}).get("page") else "—",
                                 state=f["state"], state_label=STATE_LABEL[f["state"]], edited=bool(f.get("edited"))))
    tally = M.RfpTally(found=sum(1 for f in fields if f.state == "found"), guess=sum(1 for f in fields if f.state == "guess"),
                       empty=sum(1 for f in fields if f.state == "empty"))
    found_count = tally.found + tally.guess
    intro = ""
    if st == "done":
        intro = ("RFP를 읽고 고객 · 프로젝트 정보를 채웠어요. 원문에서 찾은 곳에 번호를 달아 두었으니 맞는지 확인해 주세요."
                 + (f" 원문에 없는 {tally.empty}개 항목은 비워 두었어요." if tally.empty else ""))
    rq = next((f for f in r.get("fields") or [] if f["key"] == "requirements"), {}) or {}
    rq_n = len(rq.get("items") or [])
    files = []
    extra = []
    metas = {f["file_id"]: f for f in r.get("files") or []}
    for fid in r.get("file_ids") or []:
        f = metas.get(fid) or {"file_id": fid, "name": fid}
        files.append(M.RfpFile(file_id=fid, name=f.get("name") or fid, kind_label=_kind_label(f), pages=f.get("pages")))
    for fid in r.get("extra_file_ids") or []:
        f = metas.get(fid) or {"file_id": fid, "name": fid}
        extra.append(M.RfpFile(file_id=fid, name=f.get("name") or fid, kind_label=_kind_label(f), pages=f.get("pages")))
    return M.RfpView(status=st, job_id=r.get("job_id"), error=r.get("error"), files=files, extra_files=extra,
                     phases=[M.Phase(**ph) for ph in r.get("phases") or []],
                     excerpts=[M.RfpExcerpt(page=e.get("page"), page_label=e.get("page_label") or "", parts=[M.RfpExcerptPart(**x) for x in e.get("parts") or []])
                               for e in r.get("excerpts") or []],
                     fields=fields, tally=tally, found_count=found_count, intro=intro, rq_count=rq_n,
                     rq_label=f"요구사항 {rq_n}건은 시트 구성 추천과 섹션 작성에 그대로 쓰여요." if rq_n else "",
                     rq_ref=M.RqRef(**p["rq_ref"]) if p.get("rq_ref") else None, confirmed=bool(r.get("confirmed")))


async def get_rfp(pid: str) -> M.RfpView:
    return await rfp_view(pid)


async def put_rfp_field(pid: str, key: str, body: M.RfpFieldPut) -> M.RfpView:
    p = await core.load(pid)
    r = p.get("rfp") or {}
    if not any(f["key"] == key for f in r.get("fields") or []):
        raise not_found("RFP 항목", key, "RFP_FIELD_NOT_FOUND")

    def fn(x: dict[str, Any]) -> None:
        rr = dict(x.get("rfp") or {})
        out = []
        for f in rr.get("fields") or []:
            if f["key"] == key:
                f = {**f, "value": body.value.strip(), "edited": True}
                if f["state"] == "empty" and f["value"]:
                    f["state"] = "guess"
            out.append(f)
        rr["fields"] = out
        x["rfp"] = rr
    await core.mutate(pid, fn)
    return await rfp_view(pid)


def _date_of(v: str) -> str | None:
    m = re.search(r"(20\d{2})[-./년\s]+(\d{1,2})[-./월\s]+(\d{1,2})", v or "")
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else None


async def confirm_rfp(pid: str) -> M.Proposal:
    p = await core.load(pid)
    r = p.get("rfp") or {}
    if not r.get("fields"):
        raise unprocessable("RFP_NOT_READY", "RFP 읽기가 끝난 뒤 확인할 수 있어요")
    vals = {f["key"]: f for f in r["fields"] if f.get("state") != "empty" and f.get("value") and f.get("value") != "원문에 없음"}
    rq_ref = None
    if r.get("rq_id"):
        saved = await clients.call("requirements", "POST", f"/v1/requirements/{r['rq_id']}/save", json={}, quiet=True)
        rq_ref = {"rq_id": r["rq_id"], "version": (saved or {}).get("version") or (saved or {}).get("n")}

    def fn(x: dict[str, Any]) -> None:
        c = dict(x.get("customer") or {})
        if "customer" in vals:
            c["name"] = vals["customer"]["value"]
        if "scale" in vals:
            c["scale_text"] = vals["scale"]["value"]
        if "decision_makers" in vals:
            c["decision_makers"] = vals["decision_makers"]["value"]
        ind = vals.get("industry") or {}
        if ind.get("code") in defs.INDUSTRIES:
            c["industry_code"] = ind["code"]
            c["industry_label"] = defs.INDUSTRIES[ind["code"]]["name"]
        x["customer"] = c
        if "title" in vals:
            x["title"] = vals["title"]["value"]
        sch = dict(x.get("schedule") or {})
        if "submit_due" in vals:
            sch["submit_due"] = _date_of(vals["submit_due"]["value"]) or sch.get("submit_due")
        if "presentation" in vals:
            sch["presentation_text"] = vals["presentation"]["value"]
            sch["presentation"] = {"date": _date_of(vals["presentation"]["value"]), "text": vals["presentation"]["value"]}
        x["schedule"] = sch
        if "budget" in vals:
            x["budget_text"] = vals["budget"]["value"]
        if rq_ref:
            x["rq_ref"] = rq_ref
        rr = dict(x.get("rfp") or {})
        rr["confirmed"] = True
        x["rfp"] = rr
        core.advance_stage(x, "type")
    await core.mutate(pid, fn)
    if rq_ref:
        await L.add_link(pid, feature="requirements", ref_id=rq_ref["rq_id"], via="start", version=rq_ref.get("version"), fetch=False,
                         title="RFP 요구사항")
        await handoff.register_usage("requirements", rq_ref["rq_id"], proposal=await core.load(pid), label="RFP", version=rq_ref.get("version"))
    await plan.refresh_context(pid)
    from .proposals import redetect_industry
    await redetect_industry(pid)
    await core.index(pid, force=True)
    return await core.proposal_view(pid)


# ── 기존 작업(PR1L) ────────────────────────────────────────
FILL_SECTIONS: dict[str, list[tuple[str, str, str]]] = {
    # 기능 → (섹션, 상태, 출처 글자)
    "mi": [("mi", "full", "MI 작업"), ("bigMi", "full", "MI 작업"), ("why", "partial", "MI 경쟁사")],
    "storyboard": [("vp", "full", "Storyboard")],
    "vp": [("vp", "full", "Value Props")],
    "birdseye": [("birdseye", "full", "조감도"), ("spaceProducts", "partial", "조감도 배치안"), ("spaceScenario", "partial", "조감도")],
    "scenario": [("solution", "partial", "시나리오"), ("spaceScenario", "full", "시나리오")],
    "spec": [("spec", "full", "Spec 시트")],
    "image": [("spaceProducts", "partial", "이미지")],
    "competitor": [("why", "full", "경쟁사 분석")],
}
STATE_RANK = {"new": 0, "partial": 1, "full": 2}
FILL_LABEL = {"full": "채움", "partial": "일부", "new": "새로 작성"}


async def fill_preview(p: dict[str, Any], on_features: list[str], snaps: dict[str, dict[str, Any]] | None = None) -> M.FillPreview:
    has = {f: f in on_features for f in defs.WORK_FEATURES}
    ctx = {**(p.get("ctx") or {}), "has": has}
    rec = await industry.recommend_type({**p, "start_mode": "works"}, ctx)
    keys = core.type_sections(rec["type"])
    sections = []
    for k in keys:
        state, src = "new", ("새로 찾기" if k == "cases" else "새로 작성")
        for f in on_features:
            for key, st, label in FILL_SECTIONS.get(f, []):
                if key == k and STATE_RANK[st] > STATE_RANK[state]:
                    state, src = st, label
        sections.append(M.FillPreviewSection(key=k, name=defs.SECTIONS[k]["name"], state=state, state_label=FILL_LABEL[state], source_label=src))
    counts = M.FillCounts(full=sum(1 for s in sections if s.state == "full"), partial=sum(1 for s in sections if s.state == "partial"),
                          new=sum(1 for s in sections if s.state == "new"))
    cust_from = None
    c = dict(p.get("customer") or {})
    if "storyboard" in on_features:
        cust_from = M.CustomerFrom(feature="storyboard", label="고객 · 프로젝트 · Storyboard에서")
        sb = (snaps or {}).get("storyboard") or {}
        for k2, v in (sb.get("customer") or {}).items():
            if v and not c.get(k2):
                c[k2] = v
    elif "requirements" in on_features:
        cust_from = M.CustomerFrom(feature="requirements", label="고객 · 프로젝트 · 요구사항에서")
    ind = defs.INDUSTRIES.get(c.get("industry_code") or "", {}).get("name") or core.industry_label(p)
    rq_n = len(((p.get("ctx") or {}).get("rq") or {}).get("items") or [])
    summary = " · ".join(x for x in (c.get("name"), ind, c.get("scale_text"), f"요구사항 {rq_n}건" if rq_n else "") if x)
    return M.FillPreview(customer_from=cust_from, customer_summary=summary,
                         recommended_type=M.RecommendedType(type=rec["type"], name=defs.TYPES[rec["type"]]["name"], reason=rec["reason"]),
                         sections=sections, counts=counts,
                         counts_label=f"채움 {counts.full} · 일부 {counts.partial} · 새로 작성 {counts.new}")


def _customer_match(item: dict[str, Any], cust: str) -> bool:
    if not cust:
        return True
    meta = item.get("meta") or {}
    hay = " ".join(str(x) for x in (meta.get("customer"), meta.get("customer_name"), item.get("title"), item.get("summary")) if x)
    key = re.sub(r"\s+", "", cust.replace("프랜차이즈", ""))
    return bool(key) and key in re.sub(r"\s+", "", hay)


async def related_works(pid: str, *, scope: str = "customer", q: str | None = None) -> M.RelatedWorks:
    p = await core.load(pid)
    cust = ((p.get("customer") or {}).get("name") or "").strip()
    items = await clients.ws_items(owner="all", q=q, limit=100)
    links = {(ln.get("feature"), ln.get("ref_id")): ln for ln in await repo.alist("links", {"proposal_id": pid})}
    rec_type = ((p.get("recommended_type") or {}).get("type")) or p.get("type") or "standard"
    works = []
    for it in items:
        f = defs.CODE_FEATURE.get(it.get("feature") or "")
        if not f or f == "proposal" or f not in defs.WORK_TARGETS:
            continue
        match = _customer_match(it, cust)
        if scope == "customer" and not match:
            continue
        ln = links.get((f, it["item_id"]))
        tgt = defs.WORK_TARGETS[f]
        default_on = f in defs.WORK_DEFAULT_ON and match and (scope == "customer" or bool(cust))
        on = (ln.get("status") in ("candidate", "linked")) if ln else False
        when = config.when_label(it.get("updated_at"))
        works.append(M.RelatedWork(feature=f, ref_id=it["item_id"], title=it.get("title") or "", tool_label=defs.FEATURE_LABEL.get(f, f),
                                   meta=" · ".join(x for x in (it.get("summary") or "", when) if x), updated_at=it.get("updated_at"),
                                   version=(it.get("meta") or {}).get("version") if isinstance((it.get("meta") or {}).get("version"), int) else None,
                                   target_sections=list(tgt.get(rec_type) or []), target_label=tgt.get("label") or "",
                                   default_on=default_on, on=on if ln else default_on, customer_match=match, route=it.get("route")))
    works.sort(key=lambda w: (not w.customer_match, list(defs.WORK_TARGETS).index(w.feature) if w.feature in defs.WORK_TARGETS else 99))
    on_feats = [w.feature for w in works if w.on]
    preview = await fill_preview(p, on_feats)
    n_on = sum(1 for w in works if w.on)
    return M.RelatedWorks(scope=scope, customer_name=cust, works=works, work_count=len(works), on_count=n_on,
                          header_label=f"연결할 작업 {n_on} / {len(works)}",
                          intro=f"{cust or '이 고객'}와 이어진 작업 {len(works)}건을 찾았어요. 연결하면 고객 정보는 Storyboard에서 채우고, "
                                "각 작업 결과는 맞는 섹션에 미리 넣어 둡니다. 연결은 섹션 작성 중에도 바꿀 수 있어요.",
                          footer_label=f"기존 작업에서 시작 · 작업 {n_on}건 연결 · 1 / 6", preview=preview)


async def links_out(pid: str, *, section_key: str | None = None, with_preview: bool = False) -> M.LinksOut:
    p = await core.load(pid)
    lns = [ln for ln in await repo.alist("links", {"proposal_id": pid}) if (ln.get("status") or "linked") in ("candidate", "linked")]
    if section_key:
        lns = [ln for ln in lns if section_key in L.sections_for(ln, p.get("type"))]
    preview = None
    if with_preview:
        snaps = {ln["feature"]: ln.get("handoff") or {} for ln in lns if ln.get("handoff")}
        preview = await fill_preview(p, sorted({ln["feature"] for ln in lns}), snaps)
    return M.LinksOut(links=[L.view(ln) for ln in lns], preview=preview, on_count=len(lns))


async def list_links(pid: str, section_key: str | None) -> M.LinksOut:
    return await links_out(pid, section_key=section_key, with_preview=section_key is None)


async def put_links(pid: str, body: M.LinksPut) -> M.LinksOut:
    p = await core.load(pid)
    existing = {(ln.get("feature"), ln.get("ref_id")): ln for ln in await repo.alist("links", {"proposal_id": pid})}
    for t in body.links:
        f = defs.norm_feature(t.feature) or t.feature
        ln = existing.get((f, t.ref_id))
        if t.on:
            if ln is None:
                item = await clients.ws_item(t.ref_id)
                snap = None
                if f == "storyboard":   # 미리보기 고객 요약에 쓰려고 스냅숏을 먼저
                    snap = await handoff.fetch(f, t.ref_id, proposal_type=p.get("type"))
                await L.add_link(pid, feature=f, ref_id=t.ref_id, section_key=t.section_key, via="start", status="candidate", fetch=False,
                                 title=(item or {}).get("title") or t.ref_id)
                if snap:
                    lid = next(x["id"] for x in await repo.alist("links", {"proposal_id": pid}) if x.get("feature") == f and x.get("ref_id") == t.ref_id)
                    await repo.amutate("links", lid, lambda x, snap=snap: x.update({"handoff": snap}))
            elif ln.get("status") == "removed":
                await repo.amutate("links", ln["id"], lambda x: x.update({"status": "candidate" if not x.get("handoff") else "linked"}))
        elif ln is not None and ln.get("status") != "removed":
            await repo.amutate("links", ln["id"], lambda x: x.update({"status": "removed"}))
    await core.mutate(pid, lambda x: x.update({"start_mode": x.get("start_mode") if x.get("start_mode") != "blank" else "works"}), bump=False)
    return await links_out(pid, with_preview=True)


async def apply_links(pid: str) -> M.JobAccepted:
    p = await core.load(pid)
    job_id = await G.enqueue("proposal.links_apply", {"proposal_id": pid}, title="기존 작업 연결", ref=pid, project_id=p.get("project_id"))
    await core.mutate(pid, lambda x: core.set_job(x, "links_apply", job_id), bump=False)
    return M.JobAccepted(job_id=job_id, kind="proposal.links_apply", proposal_id=pid)


async def _mark_sections_stale(pid: str, ln: dict[str, Any]) -> list[str]:
    p = await core.load(pid)
    keys = L.sections_for(ln, p.get("type"))
    for key in keys:
        for s in await repo.alist("sections", {"proposal_id": pid, "key": key}):
            if s.get("status") in ("ready", "empty"):
                await repo.amutate("sections", s["id"], lambda x: x.update({"status": "stale" if x.get("status") == "ready" else x.get("status")}))
    return keys


async def delete_link(pid: str, link_id: str) -> M.LinkRemoved:
    await core.load(pid)
    ln = await repo.aget("links", link_id)
    if not ln or ln.get("proposal_id") != pid:
        raise not_found("연결 자료", link_id, "LINK_NOT_FOUND")
    await repo.amutate("links", link_id, lambda x: x.update({"status": "removed", "removed_iso": config.now_iso()}))
    keys = await _mark_sections_stale(pid, ln)
    await handoff.unregister_usage(ln.get("feature") or "", ln.get("ref_id") or "", proposal_id=pid)
    await core.record_change(pid, sheet=None, where="연결 자료", kind="source", path=f"/links/{link_id}", from_=L.link_label(ln), to=None,
                             summary=f"연결 해제 · {L.link_label(ln)}")
    if (ln.get("feature") or "").startswith("kb_") or ln.get("feature") in ("birdseye", "scenario", "spec"):
        await plan.refresh_context(pid)
        await plan.sync_sheets(pid)
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    return M.LinkRemoved(link_id=link_id, section_key=ln.get("section_key") or (keys[0] if keys else None), toast="연결 해제됨")


async def restore_link(pid: str, link_id: str) -> M.LinkedSource:
    await core.load(pid)
    ln = await repo.aget("links", link_id)
    if not ln or ln.get("proposal_id") != pid:
        raise not_found("연결 자료", link_id, "LINK_NOT_FOUND")
    saved, _ = await repo.amutate("links", link_id, lambda x: x.update({"status": "linked"}))
    await _mark_sections_stale(pid, saved)
    if (saved.get("feature") or "").startswith("kb_") or saved.get("feature") in ("birdseye", "scenario", "spec"):
        await plan.refresh_context(pid)
        await plan.sync_sheets(pid)
    await core.touch(pid, user_edit=True)
    return L.view(saved)


async def refresh_link(pid: str, link_id: str) -> M.JobAccepted:
    p = await core.load(pid)
    ln = await repo.aget("links", link_id)
    if not ln or ln.get("proposal_id") != pid:
        raise not_found("연결 자료", link_id, "LINK_NOT_FOUND")
    saved = await L.refresh_snapshot(ln, p)
    if saved.get("feature") in ("birdseye", "scenario", "spec"):
        await plan.refresh_context(pid)
        await plan.sync_sheets(pid)
    keys = [k for k in L.sections_for(saved, p.get("type")) if k in core.type_sections(p.get("type"))]
    from .sections import start_fill
    if not keys:
        job_id = await G.enqueue("noop", {}, title="연결 새로고침", ref=pid)
        return M.JobAccepted(job_id=job_id, kind="noop", proposal_id=pid)
    first = None
    for k in keys:
        acc = await start_fill(pid, k, mode="draft", origin="refresh")
        first = first or acc
    return first  # type: ignore[return-value]
