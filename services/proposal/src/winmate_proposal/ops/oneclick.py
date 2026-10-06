"""§6.7 딸깍 — 계획(팝오버 OneClickEarly · OneClickConfirm) · 시작 · 실행 보기(OneClickGen · OneClickDone)."""
from __future__ import annotations

from typing import Any

from .. import config, core, defs, industry, plan as PL, repo
from .. import models as M
from ..errors import not_found
from ..graphs import common as G
from ..graphs.one_click import memo_list

STATUS_LABEL = {"confirmed": "확정", "inferred_done": "추론 완료", "running": "생성 중", "waiting": "대기", "skipped": "건너뜀", "canceled": "중지됨"}


def _master_label(p: dict[str, Any]) -> str:
    d = p.get("design") or {}
    name = d.get("master_name") or "삼성 B2B 표준"
    return name if d.get("chosen") else f"{name} (기본값)"


async def _est_sheets(p: dict[str, Any], type_: str) -> int:
    ctx = p.get("ctx") or {}
    n = 0
    for key in core.type_sections(type_):
        comp = PL.default_composition(key, ctx)
        n += PL.sheet_count_for(key, comp, ctx)
    return n


async def build_plan(pid: str, *, from_stage: str | None, section_key: str | None) -> dict[str, Any]:
    p = await core.load(pid)
    fs = from_stage or p.get("stage") or "customer"
    fsec = section_key or (p.get("current_section_key") if fs == "sections" else None)
    confirmed = ["고객 · 프로젝트"]
    rows: list[dict[str, str]] = []
    steps: list[dict[str, Any]] = []
    confirmed_sections: list[str] = []
    type_ = p.get("type")
    n_links = await core.link_count(pid)
    if not type_ or core.STAGE_RANK.get(fs, 0) <= core.STAGE_RANK["type"]:
        rec = await industry.recommend_type(p, p.get("ctx") or {})
        rname = defs.TYPES[rec["type"]]["name"]
        est = await _est_sheets(p, rec["type"])
        n_sec = len(core.type_sections(rec["type"]))
        rows += [{"key": "type", "label": "제안서 유형", "note": f"{rname} (요구사항 기반 추천)"},
                 {"key": "compose", "label": "시트 구성", "note": f"{n_sec}섹션 · 요구사항 기반 추천 시트"},
                 {"key": "sections", "label": "섹션 작성", "note": f"연결된 작업 {n_links}건 + 추론 · 시트마다 템플릿 자동 추천"},
                 {"key": "design", "label": "디자인 템플릿", "note": _master_label(p)},
                 {"key": "assemble", "label": "PPTX 생성", "note": "표지 · 목차 포함"}]
        steps += [{"key": "type", "label": "제안서 유형", "note": f"{rname} (요구사항 기반 추천)", "status": "waiting"},
                  {"key": "compose", "label": "시트 구성", "note": f"{n_sec}섹션 · 요구사항 기반 추천 시트", "status": "waiting"}]
        for k in core.type_sections(rec["type"]):
            steps.append({"key": k, "label": defs.SECTIONS[k]["short"], "note": defs.SECTIONS[k].get("infer") or "", "status": "waiting"})
        summary = f"남은 {7 - defs.STAGE_NO.get(fs, 1)}단계 · 약 {est}시트"
    else:
        confirmed.append(defs.TYPES[type_]["name"])
        if core.STAGE_RANK.get(fs, 0) > core.STAGE_RANK["compose"]:
            confirmed.append("시트 구성")
        keys = core.type_sections(type_)
        secs = {s["key"]: s for s in await core.sections_of(pid)}
        shs = await core.sheets_of(pid)
        todo = []
        for k in keys:
            sec = secs.get(k) or {}
            if not sec.get("enabled", True):
                continue
            n = sum(1 for s in shs if s["section_key"] == k)
            if sec.get("confirmed"):
                confirmed.append(defs.SECTIONS[k]["short"])
                confirmed_sections.append(k)
                steps.append({"key": k, "label": defs.SECTIONS[k]["short"], "note": f"직접 작성 · {n}시트", "status": "confirmed"})
                continue
            todo.append((k, n))
            note = defs.SECTIONS[k].get("infer") or ""
            if k == fsec and fs == "sections":
                rows.append({"key": k, "label": f"{defs.SECTIONS[k]['short']} (작성 중)", "note": f"입력한 내용 반영 · {note}"})
                steps.append({"key": k, "label": defs.SECTIONS[k]["short"], "note": f"작성 중이던 내용 + {note}", "status": "waiting"})
            else:
                rows.append({"key": k, "label": defs.SECTIONS[k]["short"], "note": note})
                steps.append({"key": k, "label": defs.SECTIONS[k]["short"], "note": note, "status": "waiting"})
        if core.STAGE_RANK.get(fs, 0) <= core.STAGE_RANK["compose"]:
            rows.insert(0, {"key": "compose", "label": "시트 구성", "note": f"{len(keys)}섹션 · 요구사항 기반 추천 시트"})
        rows += [{"key": "design", "label": "디자인 템플릿", "note": _master_label(p)},
                 {"key": "assemble", "label": "PPTX 생성", "note": "표지 · 목차 포함"}]
        summary = f"섹션 {len(todo)} · 시트 {sum(n for _k, n in todo)}"
    steps += [{"key": "design", "label": "디자인 템플릿", "note": _master_label(p), "status": "confirmed" if (p.get("design") or {}).get("chosen") else "waiting"},
              {"key": "assemble", "label": "PPTX 조립", "note": "표지 · 목차 · 섹션 구분 포함", "status": "waiting"}]
    return {"from_stage": fs, "from_section_key": fsec, "confirmed": confirmed, "rows": rows, "summary": summary, "steps": steps,
            "confirmed_sections": confirmed_sections}


async def plan(pid: str, *, from_stage: str | None, section_key: str | None) -> M.OneClickPlan:
    p = await core.load(pid)
    d = await build_plan(pid, from_stage=from_stage, section_key=section_key)
    oc = p.get("one_click") or {}
    running = oc.get("job_id") if oc.get("status") in ("running", "queued") and await G.running(oc.get("job_id")) else None
    return M.OneClickPlan(from_stage=d["from_stage"], from_section_key=d["from_section_key"], confirmed=d["confirmed"],
                          rows=[M.PlanRow(**r) for r in d["rows"]], summary=d["summary"], eta_label=defs.ONE_CLICK_ETA,
                          footer_label=f"{defs.ONE_CLICK_ETA} · 진행 중에도 다른 작업 가능", running_job_id=running)


async def start(pid: str, body: M.OneClickStart) -> M.JobAccepted:
    p = await core.load(pid)
    oc = p.get("one_click") or {}
    if oc.get("status") in ("running", "queued") and await G.running(oc.get("job_id")):
        return M.JobAccepted(job_id=oc["job_id"], status="running", kind="proposal.one_click", proposal_id=pid)
    d = await build_plan(pid, from_stage=body.from_stage, section_key=body.from_section_key)
    job_id = await G.enqueue("proposal.one_click", {"proposal_id": pid, "options": body.options.model_dump(), "from_stage": d["from_stage"],
                                                    "from_section_key": d["from_section_key"]},
                             title=f"딸깍 · {core.title_display(p)}", ref=pid, project_id=p.get("project_id"))
    run = {"job_id": job_id, "status": "running", "pct": 0, "from_stage": d["from_stage"], "from_section_key": d["from_section_key"],
           "options": body.options.model_dump(), "plan": {"confirmed": d["confirmed"], "rows": d["rows"], "summary": d["summary"]},
           "steps": d["steps"], "confirmed_sections": d["confirmed_sections"], "memos": [],
           "auto_from_step": defs.STAGE_NO.get(d["from_stage"], 1), "started_iso": config.now_iso()}
    await core.mutate(pid, lambda x: x.update({"one_click": run}))
    await core.index(pid, force=True)
    return M.JobAccepted(job_id=job_id, kind="proposal.one_click", proposal_id=pid)


async def view(pid: str, job_id: str) -> M.OneClickView:
    p = await core.load(pid)
    oc = p.get("one_click") or {}
    if oc.get("job_id") != job_id:
        raise not_found("딸깍 실행", job_id, "ONE_CLICK_NOT_FOUND")
    st = oc.get("status") or "running"
    if st == "running" and not await G.running(job_id):
        from winmate_common.jobs import jobs
        j = await jobs().get(job_id)
        st = {"succeeded": "succeeded", "canceled": "canceled", "failed": "failed"}.get((j.status if j else "failed"), "failed")
    steps = [M.OneClickStep(key=s["key"], label=s["label"], note=s.get("note") or "", status=s["status"], status_label=STATUS_LABEL.get(s["status"], ""))
             for s in oc.get("steps") or []]
    from_key = oc.get("from_section_key")
    first = next((s for s in steps if s.status != "confirmed"), None)
    start_label = defs.SECTIONS.get(from_key or "", {}).get("short") or (first.label if first else "")
    confirmed_names = [s.label for s in steps if s.status == "confirmed" and s.key in defs.SECTIONS]
    todo = [s for s in steps if s.key in defs.SECTIONS and s.status != "confirmed"]
    pct = int(oc.get("pct") or 0)
    remaining_s = max(0, int((100 - pct) * 1.2))
    eta = "곧 끝나요" if remaining_s < 15 else (f"약 {remaining_s // 60}분 남음" if remaining_s >= 60 else f"약 {remaining_s}초 남음")
    tl = core.type_name(p.get("type")) or ""
    n_slides = core.slides_total(p, len(await core.sheets_of(pid)), len([k for k in core.type_sections(p.get("type"))]))
    jm = await memo_list(job_id)
    applied = {m.get("text"): m for m in oc.get("memos") or []}
    memos = []
    for m in jm:
        a = applied.get(m.get("text")) or {}
        sec = a.get("applied_section")
        memos.append(M.OneClickMemo(text=m.get("text") or "", at=m.get("at") or m.get("created_at") or "", applied_at=a.get("applied_at"),
                                    status_label=(f"반영됨 · {defs.SECTIONS[sec]['short']}" if sec in defs.SECTIONS else "메모 반영 예정 · 다음 섹션부터")))
    out = M.OneClickView(job_id=job_id, status=st if st in ("running", "succeeded", "canceled", "failed", "queued") else "running",
                         from_stage=oc.get("from_stage") or "sections", from_section_key=from_key,
                         options=M.OneClickOptions(**(oc.get("options") or {})),
                         plan=M.OneClickPlan(from_stage=oc.get("from_stage") or "sections", from_section_key=from_key,
                                             confirmed=(oc.get("plan") or {}).get("confirmed") or [],
                                             rows=[M.PlanRow(**r) for r in (oc.get("plan") or {}).get("rows") or []],
                                             summary=(oc.get("plan") or {}).get("summary") or ""),
                         steps=steps, memos=memos, auto_from_step=int(oc.get("auto_from_step") or 4),
                         header=f"· {start_label}부터 나머지 자동 완성" if start_label else "· 나머지 자동 완성",
                         intro=(f"남은 {len(todo)}개 섹션과 템플릿을 추론해 제안서를 만들고 있어요. "
                                + (f"확정해 두신 {' · '.join(confirmed_names)}는 그대로 쓰고, " if confirmed_names else "")
                                + "추론으로 채운 시트에는 표시와 근거 노트를 남깁니다."),
                         pct=pct, eta_label=eta, progress_label=f"{pct}% · {eta}", type_label=tl, slides_label=f"{tl} · {n_slides}장",
                         error=oc.get("error"))
    if st == "succeeded":
        res = oc.get("result") or {}
        from .confirm import views as cviews
        from .design import get_result
        rv = await get_result(pid)
        review_items = [it for it in await repo.alist("confirm_items", {"proposal_id": pid}) if it["id"] in (res.get("review_item_ids") or [])
                        and it.get("status") == "open"]
        items = await cviews(pid, review_items)
        total = int(res.get("slides_total") or (rv.file.slides if rv.file else 0))
        inferred = int(res.get("inferred_slides") or 0)
        out.done_intro = (f"딸깍으로 제안서를 완성했습니다. {total}장 중 {inferred}장을 추론으로 채웠고, 그 시트에는 추론 표시와 근거 노트를 남겼어요. "
                          f"먼저 확인이 필요한 {len(items)}곳을 모았습니다.")
        if rv.file:
            out.file = M.OneClickFile(name=rv.file.name, meta=f"{tl} · {total}장", pptx_file_id=rv.file.pptx_file_id, pdf_file_id=rv.file.pdf_file_id,
                                      pptx_url=rv.file.pptx_url)
        out.counts = {"confirmed": int(res.get("confirmed_slides") or 0), "inferred": inferred, "review": len(items)}
        out.counts_label = [f"확정 {out.counts['confirmed']}", f"추론 {inferred}", f"검토 필요 {len(items)}"]
        out.thumbs = rv.thumbs[:8]
        if total > 8:
            rest = []
            shs = await core.sheets_of(pid)
            for k in core.type_sections(p.get("type")):
                n = sum(1 for s in shs if s["section_key"] == k and int(s.get("sheet_no") or 0) + 2 > 8)
                if n:
                    rest.append(f"{defs.SECTIONS[k]['short']} {n}")
            all_inf = all(s.get("inferred") for s in shs if int(s.get("sheet_no") or 0) + 2 > 8)
            out.rest_label = f"09–{total:02d} " + " · ".join(rest) + (" — 모두 추론" if all_inf else "")
        out.review_items = items
        out.review_header = f"검토가 필요한 곳 {len(items)}"
        out.next_route = core.route(pid, "one-click", job_id) if (oc.get("options") or {}).get("collect_reviews", True) else core.route(pid, "result")
    elif st in ("canceled", "failed"):
        fs = oc.get("from_stage") or "sections"
        out.next_route = core.section_route(pid, from_key) if fs == "sections" and from_key else core.stage_route({**p, "stage": fs, "one_click": None})
    return out
