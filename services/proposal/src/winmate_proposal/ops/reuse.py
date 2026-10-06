"""§6.13 기존 제안서 활용(PR1C → PRU2 → PRU2F → PRU3A|PRU3B → PRU4|PRU4B → PRU5).

분석 · 계획 · 적용은 잡(`proposal.reuse`, graphs/reuse.py)이 하고, 여기는 화면 값(라벨 · 집계 · 대조 보기)과 사람 확인(고정 · 판정 ·
확정)을 맡는다. 흐름 차용 모드에서는 원본 글을 어떤 응답에도 싣지 않는다(원본 대조 · 줄 끌어오기 403).
"""
from __future__ import annotations

import copy
from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import new_id
from winmate_common.jobs import jobs

from .. import clients, config, content as C, core, defs, facts as F, repo, reuse_analysis as RA, versions as VER
from .. import models as M
from ..errors import borrow_hidden, file_too_large, must_confirm_pending, not_found, section_not_in_type, unprocessable, unsupported_file, version_not_found
from ..graphs import common as G
from ..graphs import reuse as RG
from ..graphs import reuse_fill as RF

STATUS_LABEL = {"analyzing": "기준별 분석 진행 중", "awaiting_confirm": "분석 완료", "planning": "활용 계획 만드는 중",
                "awaiting_plan_confirm": "활용 계획 확인", "applied": "적용 완료", "failed": "분석하지 못했어요"}
ROLE_STATE_LABEL = {"auto": "자동", "ok": "확인됨", "edited": "수정함", "need": "확인 필요"}
MODE_LABEL = {"improve": "기반으로 개선 · 수정", "borrow": "논리 흐름만 차용"}
LINE_MARK_LABEL = {"keep": "유지", "update": "갱신", "new": "신규", "drop": "제외"}
CRITERION_INTRO = {
    1: "원본을 쪽마다 나눠 섹션 경계 · 표지 · 목차 · 부록을 복원했어요. 견적처럼 따로 떼는 묶음은 분리했어요.",
    3: "원본이 반복해서 말한 핵심 메시지와 톤이에요. 흐름 차용이면 톤만 참고해요.",
    4: "원본 고객 · 규모 · 요구를 이번 요구사항과 대조했어요. 활용 방식 추천의 근거예요.",
    5: "원본의 모델 · 솔루션을 판매 상태와 대조했어요. 단종 모델은 후속 모델로 바꾸자고 제안해요.",
    6: "원본 수치마다 기준일 · 출처를 봤어요. 오래된 수치는 최신 조사로, 출처 없는 효과 수치는 쓰지 않아요.",
    7: "원본 이미지를 출처별로 나눴어요. 삼성 공식만 그대로 쓰고, 다른 고객 사진 · 출처 미상은 쓰지 않아요.",
    8: "원본 쪽을 Winmate 시트 유형 · 템플릿에 대응시켰어요. 대응하지 못한 쪽은 새로 만들어요.",
    9: "가격 · 견적 · 단가 · 일정 · 고객 내부 수치는 자동으로 뺐어요. 이 목록은 되살릴 수 없어요.",
}


# ── 공용 ───────────────────────────────────────────────────
def reuse_not_found(pid: str) -> ApiError:
    return not_found("기존 제안서 분석", pid, "REUSE_NOT_FOUND")


async def _doc(pid: str) -> tuple[dict[str, Any], dict[str, Any]]:
    p = await core.load(pid)
    rid = (p.get("reuse") or {}).get("reuse_id") or (p.get("derived_from") or {}).get("reuse_id")
    ru = await repo.aget("reuse", rid) if rid else None
    if not ru:
        raise reuse_not_found(pid)
    return p, ru


async def _status(ru: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str | None]:
    """문서 상태 + 잡 상태 맞추기(잡이 실패 · 취소됐는데 문서가 진행 중이면 실패로)."""
    st = ru.get("status") or "analyzing"
    err = ru.get("error")
    j = await jobs().get(ru["job_id"]) if ru.get("job_id") else None
    js = j.status if j else None
    if st in ("analyzing", "planning") and j and js in ("failed", "canceled"):
        st = "failed"
        err = err or (j.error if isinstance(j.error, dict) else {"code": "JOB_FAILED", "message": "분석하지 못했어요"})
    return st, err, js


def _meta_label(m: dict[str, Any], me: str) -> str:
    if m.get("kind") == "proposal":
        return " · ".join(x for x in ["Winmate", core.type_label(m.get("type")) or "", f"v{m['version']}" if m.get("version") else "",
                                      f"{m.get('pages') or 0}장", m.get("doc_date") or ""] if x)
    who = m.get("author") or ""
    if who and who != me:
        who = f"{who}(동료)"
    return " · ".join(x for x in [(m.get("format") or "").upper(), f"{m.get('pages') or 0}장", m.get("doc_date") or "", who] if x)


def _thumb(pg: dict[str, Any]) -> str | None:
    if pg.get("file_id"):
        return f"/api/files/v1/files/{pg['file_id']}/pages/{pg.get('file_page') or 1}/thumbnail"
    w = pg.get("winmate") or {}
    if w.get("role") == "COVER":
        return core.thumb_url("C03")
    return core.thumb_url(w.get("template"))


def _page_out(pg: dict[str, Any]) -> M.ReusePage:
    return M.ReusePage(no=pg["no"], source_idx=pg.get("source_idx") or 0, file_page=pg.get("file_page"), title=pg.get("title") or "",
                       text_excerpt=pg.get("text_excerpt") or "", thumb_url=_thumb(pg), section_name=pg.get("section_name") or "",
                       section_color=pg.get("section_color") or "", flow_role=pg.get("flow_role"), role_state=pg.get("role_state") or "auto",
                       role_state_label=ROLE_STATE_LABEL.get(pg.get("role_state") or "auto", ""), role_candidates=pg.get("role_candidates") or [],
                       evidence=pg.get("evidence") or "", evidence_warn=bool(pg.get("evidence_warn")), excluded=bool(pg.get("excluded")),
                       exclude_reason=pg.get("exclude_reason"), locked=bool(pg.get("locked")))


def _criterion_out(c: dict[str, Any]) -> M.ReuseCriterion:
    return M.ReuseCriterion(no=c["no"], key=c["key"], name=c["name"], must=bool(c["must"]), summary=c.get("summary") or "",
                            confidence=int(c.get("confidence") or 0), warn=int(c.get("confidence") or 0) < 80, state=c.get("state") or "need",
                            state_label=defs.CRITERION_STATE_LABEL.get(c.get("state") or "need", ""))


def _flow_out(fl: dict[str, Any] | None) -> M.ReuseFlow | None:
    if not fl:
        return None
    return M.ReuseFlow(steps=[M.FlowStep(**{k: v for k, v in s.items() if k in ("name", "count", "dashed", "excluded", "note", "range")})
                              for s in fl.get("steps") or []],
                       pattern={k: str(v) for k, v in (fl.get("pattern") or {}).items()},
                       claims={k: int(v) for k, v in (fl.get("claims") or {}).items() if isinstance(v, (int, float))},
                       broken=list(fl.get("broken") or []),
                       memos=[M.FlowMemo(no=int(m.get("no") or i + 1), text=m.get("text") or "", tag=m.get("tag") or "", action=m.get("action") or "")
                              for i, m in enumerate(fl.get("memos") or [])])


def _plan_improve_out(pl: dict[str, Any] | None) -> M.PlanImprove | None:
    if not pl:
        return None
    groups: list[dict[str, Any]] = []
    for r in pl.get("rows") or []:
        if not groups or groups[-1]["name"] != r["group"]:
            groups.append({"name": r["group"], "rows": [], "is_new": r.get("page") is None})
        groups[-1]["rows"].append(r)
    out_groups = []
    for g in groups:
        nos = [r["page"] for r in g["rows"] if r.get("page")]
        rng = (f"p.{min(nos)}–{max(nos)}" if len(set(nos)) > 1 else f"p.{nos[0]}") if nos else ""
        label = f"{len(g['rows'])}장 · {rng}" if rng else f"{len(g['rows'])}장 · 원본에 없음"
        rows = [M.ReusePlanRow(row_id=r["row_id"], group=r["group"], page=r.get("page"), page_label=f"p.{r['page']}" if r.get("page") else "신규",
                               thumb_kind=r.get("thumb_kind"), sheet_name=r.get("sheet_name") or "", verdict=r["verdict"],
                               verdict_label=defs.VERDICT_LABEL.get(r["verdict"], r["verdict"]), note=r.get("note") or "", rq_ids=r.get("rq_ids") or [],
                               locked=bool(r.get("locked")), noncopy=bool(r.get("noncopy"))) for r in g["rows"]]
        out_groups.append(M.ReusePlanGroup(name=g["name"], count=len(rows), range=rng, label=label + (" · 요구사항 갭" if g["is_new"] else ""),
                                           is_new=g["is_new"], rows=rows))
    n_rows = len(pl.get("rows") or [])
    cov = [M.Coverage(rq_id=str(c.get("rq_id") or c.get("code") or ""), code=str(c.get("code") or ""), name=c.get("name") or "", state=c["state"],
                      state_label=c.get("state_label") or "", where=c.get("where") or "") for c in pl.get("requirement_coverage") or []]
    return M.PlanImprove(groups=out_groups, requirement_coverage=cov,
                         only_in_source=[M.OnlyInSource(**x) for x in pl.get("only_in_source") or []], totals=pl.get("totals") or {},
                         source_total=int(pl.get("source_total") or 0), new_total=int(pl.get("new_total") or 0), summary_note=pl.get("summary_note") or "",
                         shown_label=f"12 / {n_rows}장 표시 · 나머지 {n_rows - 12}장 보기" if n_rows > 12 else "",
                         footer_label=f"활용 계획 · 원본 {pl.get('source_total') or 0}장 → 새 제안서 {pl.get('new_total') or 0}장 · 1 / 6")


def _plan_borrow_out(pl: dict[str, Any] | None) -> M.PlanBorrow | None:
    if not pl:
        return None
    return M.PlanBorrow(rows=[M.BorrowRow(**r) for r in pl.get("rows") or []], take=[M.TakeItem(**x) for x in pl.get("take") or []],
                        not_take=[M.TakeItem(**x) for x in pl.get("not_take") or []], sections=int(pl.get("sections") or 0),
                        sheets=int(pl.get("sheets") or 0), counts=pl.get("counts") or {},
                        footer_label=f"시트 구성 초안 · {pl.get('sections') or 0}섹션 · {pl.get('sheets') or 0}시트 · 원본 내용 0줄 사용 · 1 / 6")


def _src_name(ru: dict[str, Any]) -> str:
    srcs = ru.get("sources") or []
    if not srcs:
        return "원본"
    if len(srcs) == 1:
        return srcs[0].get("name") or "원본"
    return f"{srcs[0].get('name')} 외 {len(srcs) - 1}개"


def _intro(p: dict[str, Any], ru: dict[str, Any], st: str) -> str:
    a = ru.get("analysis") or {}
    n = len(ru.get("src_pages") or []) or sum(int(m.get("pages") or 0) for m in ru.get("sources") or [])
    name = _src_name(ru)
    mode = ru.get("mode")
    rec = (a.get("recommendation") or {}).get("mode")
    ctx = a.get("context") or {}
    if st == "analyzing":
        return f"{name}을(를) 읽고 있어요 — 읽기 → 쪽 나누기 → 기준별 분석 순서로 진행해요."
    if st == "failed":
        return ((ru.get("error") or {}).get("message")) or "분석하지 못했어요. 원본을 다시 올려 주세요."
    if st == "awaiting_confirm":
        return (f"{name} {n}장을 9가지 기준으로 분석했어요. 기준마다 결과를 확인해 주세요 — 필수 확인 3곳(논리 흐름 · 고객 맥락 · 비복제)을 "
                "확인하면 활용 방식을 추천해요.")
    if st == "applied":
        return "활용 계획을 시트 구성에 적용했어요. 섹션 작성에서 " + ("원본 시트와 새 시트를 나란히 놓고 고쳐요." if mode == "improve" else "원본 역할만 '흐름 가이드'로 보며 써요.")
    s0 = (ru.get("sources") or [{}])[0]
    if mode == "improve":
        meta = " · ".join(x for x in [core.type_name(s0.get("type")) or (s0.get("format") or "").upper(), f"{n}장",
                                      f"v{s0['version']}" if s0.get("version") else ""] if x)
        why = (f"같은 고객이고 요구사항이 {ctx.get('overlap_count') or 0}건 겹쳐 기반으로 개선 · 수정을 추천해요." if rec == "improve" and ctx.get("same_customer")
               else "기반으로 개선 · 수정하기로 했어요.")
        return (f"원본 {name} ({meta})은 {why} 시트마다 유지 · 갱신 · 재작성 · 신규 · 제외를 제안했고, 근거를 달아 두었어요. "
                "내용만 바꾸는 게 아니라 이번 요구사항에 없는 시트는 빼고 새 요구사항엔 시트를 더해요.")
    steps = [s for s in (a.get("flow") or {}).get("steps") or [] if not s.get("dashed") and not s.get("excluded")]
    lead = (f"분석 결과 활용 방식으로 논리 흐름만 차용을 추천해요 — 다른 고객({ctx.get('source_customer') or '원본 고객'}) 제안서라 "
            "내용은 쓰지 않고 설득 구조만 가져옵니다." if rec == "borrow" else "논리 흐름만 차용해요 — 내용은 쓰지 않고 설득 구조만 가져옵니다.")
    return f"{lead} 원본의 흐름 {len(steps)}단계를 이번 요구사항 {ctx.get('current_total') or 0}건에 맞춰 시트 구성으로 바꿨어요. 다르게 하려면 바꿔 주세요."


async def view(p: dict[str, Any], ru: dict[str, Any]) -> M.ReuseView:
    st, err, js = await _status(ru)
    a = ru.get("analysis") or {}
    me = current_user().name
    phs = [M.Phase(**ph) for ph in ru.get("phases") or RG.phases("busy", "todo", "todo")]
    sources = []
    for m in ru.get("sources") or ru.get("sources_in") or []:
        sources.append(M.ReuseSourceOut(kind=m.get("kind") or "file", proposal_id=m.get("proposal_id"), version=m.get("version"), file_id=m.get("file_id"),
                                        name=m.get("name") or m.get("file_id") or m.get("proposal_id") or "", format=m.get("format") or "",
                                        pages=int(m.get("pages") or 0), author=m.get("author"), doc_date=m.get("doc_date"), customer=m.get("customer"),
                                        meta_label=_meta_label(m, me) if m.get("name") else "", phases=phs))
    criteria = [_criterion_out(c) for c in a.get("criteria") or []]
    must_done = sum(1 for c in criteria if c.must and c.state != "need")
    confirmed = sum(1 for c in criteria if c.state in ("ok", "edited"))
    pages = [_page_out(pg) for pg in a.get("pages") or []]
    excl = sum(1 for pg in pages if pg.excluded)
    secs = [s for s in a.get("source_sections") or [] if not s.get("excluded") and s.get("name") != "표지"]
    srcs = ru.get("sources") or []
    n = len(pages)
    if len(srcs) == 1 and srcs[0].get("kind") == "proposal":
        band = f"원본 {n}장 · Winmate 제안서 · v{srcs[0].get('version') or 1} · 섹션 {len(secs)}개"
    elif len(srcs) == 1:
        band = f"원본 {n}장 · 외부 파일 · 섹션 {len(secs)}개"
    else:
        band = f"원본 {n}장 · 원본 {len(srcs)}개 · 섹션 {len(secs)}개"
    footer = ""
    if criteria:
        footer = f"분석 결과 확인 · 9개 기준 중 {confirmed}개 확인 · 필수 확인 {must_done} / 3 마침 · {3 - must_done}곳 남음"
    rec = a.get("recommendation")
    return M.ReuseView(id=ru["id"], proposal_id=p["id"], job_id=ru.get("job_id"), job_status=js, status=st, status_label=STATUS_LABEL.get(st, ""),
                       sources=sources, phases=phs, mode_pref=ru.get("mode_pref") or "auto", mode=ru.get("mode"),
                       recommendation=M.ReuseRecommendation(**rec) if rec else None, pages=pages,
                       source_sections=[M.ReuseSection(name=s["name"], count=int(s["count"]), color=s.get("color") or "", excluded=bool(s.get("excluded")))
                                        for s in a.get("source_sections") or []],
                       criteria=criteria, flow=_flow_out(a.get("flow")), context=a.get("context") or {},
                       plan_improve=_plan_improve_out(ru.get("plan_improve")), plan_borrow=_plan_borrow_out(ru.get("plan_borrow")),
                       must_done=must_done, must_total=3, confirmed_count=confirmed, can_confirm=bool(must_done == 3 and st == "awaiting_confirm"),
                       intro=_intro(p, ru, st), footer_label=footer, excluded_page_count=excl, band_label=band if n else "", error=err)


# ── PR1C 원본 고르기 ───────────────────────────────────────
def _sol_codes(x: dict[str, Any]) -> set[str]:
    sols = ((x.get("ctx") or {}).get("solutions") or {})
    return {c for c, v in sols.items() if isinstance(v, dict) and v.get("state") in ("on", "rec")}


async def candidates(pid: str) -> M.ReuseCandidates:
    """목록 추천 ≤ 2(§10.9) — 「같은 고객」 최근 제출본(또는 최신 버전) · 「같은 솔루션」 다른 고객 최근 것. 내 제안서만."""
    p = await core.load(pid)
    me = current_user().id
    cust = RA.norm_name((p.get("customer") or {}).get("name") or "")
    mine = [x for x in await repo.alist("proposals", {"owner_id": me}) if x["id"] != pid and int(x.get("saved_version") or 0) > 0]

    def recent(x: dict[str, Any]) -> tuple[int, str]:
        return (1 if x.get("status") == "done" else 0, x.get("submitted_at") or x.get("updated_at") or x.get("created_iso") or "")
    out: list[M.ReuseCandidate] = []
    same = sorted([x for x in mine if cust and RA.norm_name((x.get("customer") or {}).get("name") or "") == cust], key=recent, reverse=True)
    if same:
        x = same[0]
        out.append(M.ReuseCandidate(proposal_id=x["id"], name=core.title_display(x), why="같은 고객", version=int(x.get("saved_version") or 0) or None))
    sols = _sol_codes(p)
    other = sorted([x for x in mine if x["id"] not in {c.proposal_id for c in out} and sols & _sol_codes(x)
                    and RA.norm_name((x.get("customer") or {}).get("name") or "") != cust], key=recent, reverse=True)
    if other:
        x = other[0]
        out.append(M.ReuseCandidate(proposal_id=x["id"], name=core.title_display(x), why="같은 솔루션", version=int(x.get("saved_version") or 0) or None))
    return M.ReuseCandidates(items=out[:2], label=f"내 제안서 목록에서는 {len(out[:2])}개 추천" if out else "")


async def _check_source(pid: str, s: M.ReuseSourceIn) -> dict[str, Any]:
    if s.kind == "file":
        if not s.file_id:
            raise unprocessable("SOURCE_REQUIRED", "원본 파일을 골라 주세요")
        meta = await clients.file_meta(s.file_id)
        if not meta:
            raise not_found("파일", s.file_id, "FILE_NOT_FOUND")
        if int(meta.get("size") or 0) > defs.FILE_MAX_MB * 1024 * 1024:
            raise file_too_large()
        name = (meta.get("name") or "").lower()
        if (meta.get("kind") or "").lower() not in defs.REUSE_FORMATS and not name.endswith((".pptx", ".pdf")):
            raise unsupported_file()
        return {"kind": "file", "file_id": s.file_id}
    if not s.proposal_id:
        raise unprocessable("SOURCE_REQUIRED", "원본 제안서를 골라 주세요")
    if s.proposal_id == pid:
        raise unprocessable("SOURCE_IS_SELF", "이 제안서 자신은 원본으로 쓸 수 없어요")
    sp = await repo.aget("proposals", s.proposal_id)
    if not sp:
        raise not_found("제안서", s.proposal_id, "PROPOSAL_NOT_FOUND")
    if s.version and not await VER.get_version(s.proposal_id, s.version):
        raise version_not_found(s.version)
    return {"kind": "proposal", "proposal_id": s.proposal_id, "version": s.version or int(sp.get("saved_version") or 0) or None}


async def start(pid: str, body: M.ReuseStart) -> M.JobAccepted:
    p = await core.load(pid)
    srcs = [await _check_source(pid, s) for s in body.sources]
    old = None
    rid0 = (p.get("reuse") or {}).get("reuse_id")
    if rid0 and (p.get("reuse") or {}).get("status") not in ("applied",):
        old = await repo.aget("reuse", rid0)
    if old:
        # 이미 분석 중이면 원본을 더해 다시 시작(같은 분석 · 고정 유지). replace 면 이 목록으로 바꾼다(원본 빼기)
        if not body.replace:
            merged = list(old.get("sources_in") or [])
            for s in srcs:
                if s not in merged:
                    merged.append(s)
            srcs = merged
        if old.get("job_id"):
            try:
                await jobs().cancel(old["job_id"])
            except Exception:  # noqa: BLE001
                pass
        rid = old["id"]
    else:
        rid = new_id("pru")
        await repo.aput("reuse", rid, {"id": rid, "proposal_id": pid, "job_id": None, "sources_in": srcs, "sources": [], "src_pages": [],
                                       "phases": RG.phases("busy", "todo", "todo"), "mode_pref": body.mode_pref, "mode": None, "analysis": None,
                                       "plan_improve": None, "plan_borrow": None, "locks": {"pages": [], "rows": [], "criteria": []},
                                       "confidential": True, "status": "analyzing", "created_iso": config.now_iso()})
    job_id = await G.enqueue("proposal.reuse", {"proposal_id": pid, "reuse_id": rid, "start": "ingest"}, title="기존 제안서 분석", ref=pid,
                             project_id=p.get("project_id"))
    pref = body.mode_pref

    def rfn(d: dict[str, Any]) -> None:
        d.update({"job_id": job_id, "sources_in": srcs, "status": "analyzing", "phases": RG.phases("busy", "todo", "todo"), "error": None,
                  "mode_pref": pref, "mode": pref if pref in ("improve", "borrow") else d.get("mode"), "requested": None,
                  "updated_iso": config.now_iso()})
    await repo.amutate("reuse", rid, rfn)

    def pfn(x: dict[str, Any]) -> None:
        x["start_mode"] = "reuse"
        x["start_files"] = list(dict.fromkeys([*(x.get("start_files") or []), *[s["file_id"] for s in srcs if s.get("file_id")]]))
        x["reuse"] = {"reuse_id": rid, "mode": pref if pref in ("improve", "borrow") else None, "status": "analyzing"}
        if body.new_title and body.new_title.strip():
            x["title"] = body.new_title.strip()
        core.set_job(x, "reuse", job_id)
    await core.mutate(pid, pfn)
    await core.index(pid)
    return M.JobAccepted(job_id=job_id, kind="proposal.reuse", proposal_id=pid, reuse_id=rid)


async def get_view(pid: str) -> M.ReuseView:
    p, ru = await _doc(pid)
    return await view(p, ru)


# ── PRU2 · PRU2F 기준 · 역할 ───────────────────────────────
def _need_analysis(ru: dict[str, Any]) -> dict[str, Any]:
    a = ru.get("analysis")
    if not a:
        raise ApiError(409, "ANALYSIS_NOT_READY", "분석이 끝나면 확인할 수 있어요")
    return a


def _detail(no: int, a: dict[str, Any]) -> dict[str, Any]:
    ctx = a.get("context") or {}
    if no == 1:
        return {"sections": [{k: s.get(k) for k in ("name", "count", "color", "excluded", "from", "to")} for s in a.get("source_sections") or []],
                "has_cover": any(pg["flow_role"] == "표지" for pg in a.get("pages") or []), "has_toc": False, "has_appendix": False,
                "split": [f"p.{pg['no']} {pg['title'][:20]}" for pg in a.get("pages") or [] if pg.get("excluded")]}
    if no == 2:
        pages = a.get("pages") or []
        return {"counts": {"ok": sum(1 for pg in pages if pg.get("role_state") in ("auto", "ok")),
                           "edited": sum(1 for pg in pages if pg.get("role_state") == "edited"),
                           "need": sum(1 for pg in pages if pg.get("role_state") == "need")},
                "roles": defs.FLOW_ROLES}
    if no == 3:
        return {"km": a.get("km") or [], "tone": a.get("tone")}
    if no == 4:
        return {k: ctx.get(k) for k in ("same_customer", "source_customer", "current_customer", "source_industry", "source_scale", "coverage",
                                        "overlap_count", "current_total", "rq_linked")} | {
            "rq_link_hint": "" if ctx.get("rq_linked") else "이번 요구사항 정의서를 연결하면 겹침을 셀 수 있어요"}
    if no == 5:
        return {"products": a.get("products") or [], "sol_diff": a.get("sol_diff") or []}
    if no == 6:
        return {"numbers": [{**{k: x.get(k) for k in ("page", "value", "year", "sourced", "stale")},
                             "status_label": "오래됨" if x.get("stale") else ("출처 없음" if not x.get("sourced") else "확인됨")}
                            for x in (a.get("numbers") or [])[:80]]}
    if no == 7:
        imgs = a.get("images") or []
        return {"images": imgs, "counts": {c: sum(1 for i in imgs if i["class"] == c) for c in ("official", "generated", "customer", "unknown")}}
    if no == 8:
        return {"mapping": a.get("mapping") or []}
    return {"pages": [{"no": pg["no"], "title": pg["title"], "reason": pg.get("exclude_reason")} for pg in a.get("pages") or [] if pg.get("excluded")],
            "lines": [{"page": x["page"], "line_id": x["line_id"]} for x in a.get("noncopy_lines") or []],
            "note": "자동 제외 목록은 되살릴 수 없어요"}


async def get_criterion(pid: str, no: int) -> M.CriterionDetail:
    p, ru = await _doc(pid)
    a = _need_analysis(ru)
    if no < 1 or no > 9:
        raise not_found("기준", str(no), "CRITERION_NOT_FOUND")
    c = next(x for x in a["criteria"] if x["no"] == no)
    st = c.get("state") or "need"
    conf = int(c.get("confidence") or 0)
    tail = ("다음 단계로 가려면 확인이 필요해요" if c["must"] and st == "need" else "확인이 필요해요" if st == "need" else
            "직접 고친 결과예요 · 다시 분석해도 바뀌지 않아요" if st == "edited" else "확인됐어요")
    pages = a.get("pages") or []
    intro = (f"{len(pages)}장 각각이 설득 흐름에서 맡은 역할을 태그했어요. 역할이 틀리면 바꿔 주세요 — 유저가 고친 태그는 다시 분석해도 바뀌지 않아요. "
             "이 흐름이 이번 제안서 시트 구성의 뼈대가 돼요.") if no == 2 else CRITERION_INTRO.get(no, "")
    footer = ""
    if no == 2:
        ok = sum(1 for pg in pages if pg.get("role_state") in ("auto", "ok"))
        ed = sum(1 for pg in pages if pg.get("role_state") == "edited")
        left = sum(1 for pg in pages if pg.get("role_state") == "need")
        footer = f"논리 흐름 확인 · {len(pages)}장 중 태그 확인 {ok} · 수정 {ed} · 남음 {left}"
    chips = [{"no": x["no"], "name": x["name"], "label": f"{x['no']} · {x['name']}", "state": x.get("state"), "must": x["must"]} for x in a["criteria"]]
    return M.CriterionDetail(no=no, key=c["key"], name=c["name"], must=bool(c["must"]), state=st, state_label=defs.CRITERION_STATE_LABEL.get(st, ""),
                             confidence=conf, summary=c.get("summary") or "", header_label=f"신뢰도 {conf}% · {tail}", intro=intro,
                             detail=_detail(no, a), pages=[_page_out(pg) for pg in pages] if no in (1, 2, 8) else [],
                             flow=_flow_out(a.get("flow")) if no == 2 else None, footer_label=footer, chips=chips)


def _editable(ru: dict[str, Any]) -> None:
    if ru.get("status") == "applied":
        raise ApiError(409, "REUSE_APPLIED", "이미 시트 구성에 적용한 분석이에요")


async def put_criterion(pid: str, no: int, body: M.CriterionPut) -> M.ReuseView:
    p, ru = await _doc(pid)
    _need_analysis(ru)
    _editable(ru)
    if no < 1 or no > 9:
        raise not_found("기준", str(no), "CRITERION_NOT_FOUND")

    def fn(d: dict[str, Any]) -> None:
        a = d["analysis"]
        c = next(x for x in a["criteria"] if x["no"] == no)
        locks = d.setdefault("locks", {"pages": [], "rows": [], "criteria": []})
        if body.edits is not None:
            c["state"] = "edited"
            c["user_edits"] = {**(c.get("user_edits") or {}), **body.edits}
            locks["criteria"] = sorted({*locks.get("criteria", []), no})
            if no == 4 and "same_customer" in body.edits:
                a["context"]["same_customer"] = bool(body.edits["same_customer"])
                a["recommendation"] = RA.recommend(a["context"], len(d.get("sources") or []))
            if no == 5 and body.edits.get("reject_successors"):
                rej = set(body.edits["reject_successors"])
                for x in a.get("products") or []:
                    if x["model"] in rej:
                        x["successor"] = None
        elif body.state:
            c["state"] = body.state
            if body.state == "need":
                locks["criteria"] = [x for x in locks.get("criteria", []) if x != no]
                c.pop("user_edits", None)
            if no == 2 and body.state == "ok":
                # 「이 흐름으로 확인」 — 남은 「확인 필요」 쪽은 첫 후보로 확정(§4.26)
                for pg in a["pages"]:
                    if pg.get("role_state") == "need":
                        pg["flow_role"] = (pg.get("role_candidates") or [pg["flow_role"]])[0]
                        pg["role_state"] = "ok"
                RA.rebuild(a)
        d["updated_iso"] = config.now_iso()
    await repo.amutate("reuse", ru["id"], fn)
    p, ru = await _doc(pid)
    return await view(p, ru)


async def put_page_role(pid: str, no: int, body: M.RolePut) -> M.ReuseView:
    p, ru = await _doc(pid)
    a = _need_analysis(ru)
    _editable(ru)
    if body.role not in defs.FLOW_ROLES or body.role == "표지" and no != 1:
        raise unprocessable("INVALID_ROLE", "역할 태그를 목록에서 골라 주세요", role=body.role)
    pg = next((x for x in a.get("pages") or [] if x["no"] == no), None)
    if not pg:
        raise not_found("쪽", str(no), "PAGE_NOT_FOUND")
    if pg.get("excluded") and pg.get("exclude_reason"):
        raise unprocessable("VERDICT_LOCKED", "비복제로 자동 제외한 쪽은 바꿀 수 없어요", page=no)

    def fn(d: dict[str, Any]) -> None:
        aa = d["analysis"]
        x = next(y for y in aa["pages"] if y["no"] == no)
        x["flow_role"] = body.role
        x["role_state"] = "edited"
        x["locked"] = True
        if body.role not in x.get("role_candidates") or []:
            x["role_candidates"] = [body.role, *(x.get("role_candidates") or [])][:2]
        if body.role == "견적 · 일정":
            x["excluded"] = True
            x["exclude_reason"] = None
        locks = d.setdefault("locks", {"pages": [], "rows": [], "criteria": []})
        locks["pages"] = sorted({*locks.get("pages", []), no})
        RA.rebuild(aa)
        d["updated_iso"] = config.now_iso()
    await repo.amutate("reuse", ru["id"], fn)
    p, ru = await _doc(pid)
    return await view(p, ru)


async def reanalyze(pid: str) -> M.ReuseConfirmOut:
    p, ru = await _doc(pid)
    _editable(ru)
    st, _err, js = await _status(ru)
    if st == "analyzing" and js in ("queued", "running"):
        return M.ReuseConfirmOut(job_id=ru.get("job_id"), status="analyzing", route=core.route(pid, "reuse", "analysis"))
    job = await RG.signal(pid, ru, {"action": "reanalyze"}, stage="plan" if st in ("planning", "awaiting_plan_confirm") else "analysis")
    await RG.save(ru["id"], status="analyzing")
    await RG.set_pr(pid, status="analyzing")
    return M.ReuseConfirmOut(job_id=job, status="analyzing", route=core.route(pid, "reuse", "analysis"))


async def confirm_analysis(pid: str) -> M.ReuseConfirmOut:
    p, ru = await _doc(pid)
    _editable(ru)
    st, _err, _js = await _status(ru)
    a = ru.get("analysis")
    if st in ("analyzing", "failed") or not a:
        raise ApiError(409, "ANALYSIS_NOT_READY", "분석이 끝나면 확인할 수 있어요")
    missing = [c["no"] for c in a["criteria"] if c["no"] in defs.MUST_CRITERIA and c.get("state") == "need"]
    if missing:
        raise must_confirm_pending(missing)
    mode = ru.get("mode") or (a.get("recommendation") or {}).get("mode") or "borrow"
    if st == "awaiting_confirm":
        job = await RG.signal(pid, ru, {"action": "confirm", "mode": mode}, stage="analysis")
        await RG.save(ru["id"], status="planning", mode=mode)
        await RG.set_pr(pid, status="planning", mode=mode)
    else:
        job = ru.get("job_id")
    # 계획은 결정적 — 바로 계산해 두면 PRU3 가 기다리지 않는다(잡의 plan 노드도 같은 값을 다시 만든다)
    await RG.compute_plan(pid, ru["id"], mode)
    return M.ReuseConfirmOut(job_id=job, status="planning", route=core.route(pid, "reuse", "plan") + f"?mode={mode}")


# ── PRU3 계획 ──────────────────────────────────────────────
async def put_mode(pid: str, body: M.ModePut) -> M.ReuseView:
    p, ru = await _doc(pid)
    _editable(ru)
    if not body.mode and not body.mode_pref:
        raise unprocessable("MODE_REQUIRED", "활용 방식을 골라 주세요")
    st, _err, _js = await _status(ru)
    if body.mode_pref and not body.mode:
        # PR1C 라디오 — 저장만(분석은 그대로). 추천과 다르면 PRU3 를 그 방식으로 연다(§4.10)
        mode = body.mode_pref if body.mode_pref in ("improve", "borrow") else None
        await RG.save(ru["id"], mode_pref=body.mode_pref, mode=mode)
        await RG.set_pr(pid, mode=mode)
        if mode and st in ("planning", "awaiting_plan_confirm"):
            await RG.compute_plan(pid, ru["id"], mode)
    else:
        await RG.save(ru["id"], mode=body.mode)
        await RG.set_pr(pid, mode=body.mode)
        if st in ("planning", "awaiting_plan_confirm"):
            await RG.compute_plan(pid, ru["id"], body.mode)
    p, ru = await _doc(pid)
    return await view(p, ru)


async def delete_reuse(pid: str) -> M.Ok:
    """PR1C 마지막 원본까지 뺌 — 분석을 멈추고 지운다(원본 · 제안서 내용은 그대로)."""
    p = await core.load(pid)
    rid = (p.get("reuse") or {}).get("reuse_id")
    ru = await repo.aget("reuse", rid) if rid else None
    if ru and ru.get("status") == "applied":
        raise ApiError(409, "REUSE_APPLIED", "이미 시트 구성에 적용한 분석이에요")
    if ru:
        if ru.get("job_id"):
            try:
                await jobs().cancel(ru["job_id"])
            except Exception:  # noqa: BLE001
                pass
        await repo.adelete("reuse", ru["id"])
    files = {s.get("file_id") for s in (ru or {}).get("sources_in") or [] if s.get("file_id")}

    def fn(x: dict[str, Any]) -> None:
        x["reuse"] = None
        x["start_files"] = [f for f in x.get("start_files") or [] if f not in files]
        core.set_job(x, "reuse", None)
    await core.mutate(pid, fn)
    await core.index(pid)
    return M.Ok()


async def put_verdict(pid: str, row_id: str, body: M.VerdictPut) -> M.ReuseView:
    p, ru = await _doc(pid)
    _editable(ru)
    pl = ru.get("plan_improve")
    if not pl:
        raise ApiError(409, "PLAN_NOT_READY", "활용 계획이 아직 준비되지 않았어요")
    row = next((r for r in pl.get("rows") or [] if r["row_id"] == row_id), None)
    if not row:
        raise not_found("판정 행", row_id, "ROW_NOT_FOUND")
    if row.get("noncopy"):
        raise unprocessable("VERDICT_LOCKED", "비복제 시트는 판정을 바꿀 수 없어요", row_id=row_id)
    allowed = ("new", "drop") if row.get("page") is None else ("keep", "update", "rewrite", "drop")
    if body.verdict not in allowed:
        raise unprocessable("INVALID_VERDICT", "이 행에는 고를 수 없는 판정이에요", row_id=row_id, allowed=list(allowed))
    p2 = await core.load(pid)

    def fn(d: dict[str, Any]) -> None:
        plan = d["plan_improve"]
        r = next(x for x in plan["rows"] if x["row_id"] == row_id)
        r["verdict"] = body.verdict
        r["locked"] = True
        locks = d.setdefault("locks", {"pages": [], "rows": [], "criteria": []})
        locks["rows"] = sorted({*locks.get("rows", []), row_id})
        plan.update(RA.improve_totals(p2, d["analysis"], plan["rows"], d.get("plan_type") or p2.get("type") or "standard",
                                      int(plan.get("auto_source_pages") or 0)))
        d["updated_iso"] = config.now_iso()
    await repo.amutate("reuse", ru["id"], fn)
    p, ru = await _doc(pid)
    return await view(p, ru)


async def confirm_plan(pid: str, body: M.PlanConfirm) -> M.ReuseConfirmOut:
    p, ru = await _doc(pid)
    _editable(ru)
    st, _err, _js = await _status(ru)
    if st not in ("planning", "awaiting_plan_confirm"):
        raise ApiError(409, "PLAN_NOT_READY", "활용 계획이 아직 준비되지 않았어요")
    mode = ru.get("mode") or ((ru.get("analysis") or {}).get("recommendation") or {}).get("mode") or "borrow"
    if not ru.get(f"plan_{mode}"):
        ru = await RG.compute_plan(pid, ru["id"], mode)
    # 응답 route(첫 섹션 · 원본 대조)로 바로 가도 422 SECTION_NOT_IN_TYPE · 404 REUSE_NOT_FOUND 가 나지 않게, 잡이 하던 「유형 · 시트 구성」과
    # 파생 표시를 응답 전에 먼저 적용한다(잡은 같은 값을 다시 적용 — 멱등). 잡을 깨우기 전이라 섹션 만들기가 겹치지 않는다(통합 · proposal-web 요청).
    type_ = ru.get("plan_type") or RG.plan_type(p, ru, mode)
    from .compose import set_type
    await set_type(pid, type_, source="reuse", advance=True)
    keys = core.type_sections(type_)

    def pre(x: dict[str, Any]) -> None:
        df = dict(x.get("derived_from") or {})
        if df.get("reuse_id") != ru["id"]:
            df.update({"reuse_id": ru["id"], "mode": mode, "sections": keys})
            x["derived_from"] = df
        x["reuse"] = {**(x.get("reuse") or {}), "reuse_id": ru["id"], "mode": mode, "status": "planning"}
        x["type_source"] = "reuse"
    await core.mutate(pid, pre)
    job = await RG.signal(pid, ru, {"action": "apply", "then": body.then, "mode": mode}, stage="plan")
    await RG.save(ru["id"], then=body.then, status="planning")
    if job:
        # 잡이 섹션을 채울 때까지 섹션은 「작성 중」(섹션 화면이 따로 :fill 을 부르지 않게)
        for k in keys:
            sec = await core.section_doc(pid, k)
            if sec.get("status") != "filling" and sec.get("enabled", True):
                await repo.amutate("sections", sec["id"], lambda x: x.update({
                    "status_before_fill": "empty" if x.get("status") in (None, "empty") else x.get("status"), "status": "filling", "fill_job_id": job}))
    if body.then == "compose":
        route = core.route(pid, "compose")
    else:
        first = None
        if mode == "improve":
            first = next((r.get("section_key") for r in (ru.get("plan_improve") or {}).get("rows") or []
                          if r.get("verdict") in ("keep", "update", "rewrite") and r.get("section_key") in keys), None)
        first = first or (keys[0] if keys else "")
        route = core.section_route(pid, first) + f"?view={'compare' if mode == 'improve' else 'guide'}"
    return M.ReuseConfirmOut(job_id=job, status="applying", route=route)


# ── PRU4 · PRU4B 섹션 보기 ─────────────────────────────────
async def _derived(pid: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    p = await core.load(pid)
    df = p.get("derived_from") or {}
    if not df.get("reuse_id"):
        raise reuse_not_found(pid)
    ru = await repo.aget("reuse", df["reuse_id"])
    if not ru:
        raise reuse_not_found(pid)
    return p, ru, df.get("mode") or ru.get("mode") or "improve"


def _src_pages(ru: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {pg["no"]: pg for pg in ru.get("src_pages") or []}


def _nc_ids(ru: dict[str, Any]) -> set[str]:
    return {x["line_id"] for x in (ru.get("analysis") or {}).get("noncopy_lines") or []}


def _range(nos: list[int]) -> str:
    nos = sorted(set(n for n in nos if n))
    if not nos:
        return ""
    return f"{nos[0]}–{nos[-1]}" if len(nos) > 1 else str(nos[0])


def _badge(mark: str, sh: dict[str, Any], text: str) -> str:
    r = sh.get("reuse") or {}
    if mark == "update":
        ch = r.get("change") or {}
        return "갱신 · 모델" if ch.get("kind") == "model" or RA.MODEL_RE.search(text or "") else "갱신"
    if mark == "keep":
        return "유지"
    if mark == "new":
        rq = r.get("rq_ids") or ([(sh.get("repeat_key") or {}).get("ref")] if (sh.get("repeat_key") or {}).get("kind") == "rq" else [])
        return f"신규 · {rq[0]}" if rq and rq[0] else "신규"
    return "제외"


async def _new_side(pid: str, sh: dict[str, Any], facts: dict[str, dict[str, Any]], *, mode: str) -> M.ReuseSheetSide:
    r = sh.get("reuse") or {}
    disp = C.display_content(sh.get("content") or {}, facts) if sh.get("content") else {}
    lines = RF.content_lines(disp)
    marks = {x["line_id"]: x for x in r.get("lines") or []}
    drafts = r.get("draft_lines") or {}
    out = []
    for path, text in lines:
        mk = marks.get(path) or {}
        mark = mk.get("mark") or "new"
        d = drafts.get(path)
        out.append(M.ReuseLineView(id=path, text=text, mark=mark if mark in ("keep", "update", "new", "drop") else "new", draft_text=d,
                                   source_line_id=mk.get("source_line_id") if mode == "improve" else None,
                                   badge=_badge(mark, sh, text) if mode == "improve" else None,
                                   edited=bool(d is not None and d != text)))
    title = disp.get("title") or sh.get("title") or ""
    edited_title = bool(r.get("draft_title") and r.get("draft_title") != title)
    rq = r.get("rq_ids") or []
    title_label = "시트 제목" + (" · 원본 대비 모델명 갱신" if (r.get("change") or {}).get("kind") == "model" else "") + (" · 유저가 고침" if edited_title else "")
    return M.ReuseSheetSide(sheet_id=sh["id"], page=r.get("source_page"), title=title, thumb_url=core.sheet_thumb(sh),
                            kind_label=f"{int(sh.get('sheet_no') or 0):02d} {sh.get('title') or ''} · 편집 중", lines=out,
                            note=(sh.get("content") or {}).get("notes") or r.get("note") or "",
                            rq_label=f"요구사항 {' '.join(rq)} 반영" if rq else "", title_label=title_label)


def _source_side(ru: dict[str, Any], sh: dict[str, Any], new_lines: list[M.ReuseLineView]) -> M.ReuseSheetSide | None:
    r = sh.get("reuse") or {}
    pg = _src_pages(ru).get(r.get("source_page") or -1)
    if not pg:
        return None
    nc = _nc_ids(ru)
    used = {ln.source_line_id: ln.mark for ln in new_lines if ln.source_line_id}
    lines = []
    for x in pg.get("lines") or []:
        if x["id"] in nc:
            lines.append(M.ReuseLineView(id=x["id"], text=x["text"], mark="drop", badge="비복제"))
        else:
            mk = used.get(x["id"]) or "drop"
            lines.append(M.ReuseLineView(id=x["id"], text=x["text"], mark=mk if mk in ("keep", "update") else "drop", badge=LINE_MARK_LABEL.get(mk, "제외")))
    imgs = [i for i in (ru.get("analysis") or {}).get("images") or [] if i.get("page") == pg["no"]]
    note = ""
    if imgs:
        off = sum(1 for i in imgs if i["class"] in ("official", "generated"))
        cus = [i for i in imgs if i["class"] == "customer"]
        parts = [f"원본 이미지 {len(imgs)}개"]
        if off:
            parts.append(f"삼성 공식 {off}(재사용)")
        if cus:
            parts.append(f"매장 사진 {len(cus)}(" + ("재사용 가능" if all(i["reusable"] for i in cus) else "사용 불가") + ")")
        unk = sum(1 for i in imgs if i["class"] == "unknown")
        if unk:
            parts.append(f"출처 미상 {unk}(보류)")
        note = " · ".join(parts)
    w = pg.get("winmate") or {}
    s0 = next((m for m in ru.get("sources") or [] if m), {})
    ver = f" · v{s0.get('version')}" if s0.get("kind") == "proposal" and s0.get("version") else ""
    no = pg.get("no") if w else pg.get("file_page")
    kind = (f"{w.get('template')} · {core.role_name(w.get('role'))}" if w.get("template") else core.role_name(w.get("role"))) if w else \
        (f"{pg.get('layout')} · {pg.get('flow_role') or ''}".strip(" ·") if pg.get("layout") else "")
    return M.ReuseSheetSide(sheet_id=None, page=pg["no"], page_label=f"p.{no} {pg.get('title') or ''}{ver}", title=pg.get("title") or "",
                            thumb_url=_thumb({**pg, "file_id": pg.get("file_id")}), kind_label=kind, lines=lines, images_note=note,
                            note="읽기 전용")


async def section_view(pid: str, key: str, sheet_id: str | None, view_: str | None) -> M.ReuseSectionView:
    p, ru, mode = await _derived(pid)
    keys = core.type_sections(p.get("type"))
    if key not in keys:
        raise section_not_in_type(key)
    v = view_ or ("compare" if mode == "improve" else "guide")
    if mode == "borrow" and v == "compare":
        raise borrow_hidden()
    shs = await core.sheets_of(pid, section_key=key)
    if sheet_id and not any(s["id"] == sheet_id for s in shs):
        raise not_found("시트", sheet_id, "SHEET_NOT_FOUND")
    sel = next((s for s in shs if s["id"] == sheet_id), None) if sheet_id else None
    if sel is None:
        sel = next((s for s in shs if (s.get("reuse") or {}).get("source_page")), None) if mode == "improve" else None
        sel = sel or (shs[0] if shs else None)
    facts = await F.facts_of(pid)
    a = ru.get("analysis") or {}
    src = _src_pages(ru)
    sec_pages = [int((s.get("reuse") or {}).get("source_page") or 0) for s in shs]
    sec_name = defs.SECTIONS[key]["name"]
    n_keep = sum(1 for s in shs if (s.get("reuse") or {}).get("verdict") == "keep")
    n_upd = sum(1 for s in shs if (s.get("reuse") or {}).get("verdict") == "update")
    header = f"{core.type_label(p.get('type')) or ''} {core.section_no(p.get('type'), key)} / {len(keys)} · {sec_name} · 시트 {len(shs)}장"
    if mode == "improve":
        header += f" · 유지 {n_keep} · 갱신 {n_upd}"
    def file_no(n: int) -> int:
        pg = src.get(n) or {}
        return int((pg.get("no") if pg.get("winmate") else pg.get("file_page")) or n)
    rng = _range([file_no(n) for n in sec_pages if n])
    s0 = (ru.get("sources") or [{}])[0]
    short = (s0.get("name") or "원본")[:20]
    if mode == "improve":
        source_label = f"원본 · {short} p.{rng}" if rng else f"원본 · {short}"
    else:
        steps = [s for s in (a.get("flow") or {}).get("steps") or [] if s.get("name") in {(x.get("reuse") or {}).get("flow_role") for x in shs}]
        r2 = _range([y for s in steps for y in (s.get("from"), s.get("to")) if y])
        source_label = f"원본 · {(a.get('context') or {}).get('source_customer') or short} p.{r2} · 역할만 참고" if r2 else "원본 · 역할만 참고"
    section_sheets = []
    for s in shs:
        r = s.get("reuse") or {}
        pg = src.get(r.get("source_page") or -1)
        section_sheets.append({"sheet_id": s["id"], "sheet_no": int(s.get("sheet_no") or 0), "title": s.get("title") or "", "name": s.get("title") or "",
                               "template_code": (s.get("template") or {}).get("code"),
                               "status": "writing" if sel and s["id"] == sel["id"] else "waiting",
                               "page": r.get("source_page") if mode == "improve" else None,
                               "page_label": (f"p.{file_no(r['source_page'])}" if pg and mode == "improve" else ("신규" if r.get("verdict") == "new" else "")),
                               "verdict": r.get("verdict") or "auto", "verdict_label": defs.VERDICT_LABEL.get(r.get("verdict") or "auto", ""),
                               "role": s.get("role"), "role_name": core.role_name(s.get("role")), "flow_role": r.get("flow_role"),
                               "thumb_url": core.sheet_thumb(s), "selected": bool(sel and s["id"] == sel["id"]),
                               "status_label": "작성 중" if sel and s["id"] == sel["id"] else "대기"})
    if sel is None:
        return M.ReuseSectionView(view=v, mode=mode, header_label=header, section_key=key, source_label=source_label,
                                  new_sheet=M.ReuseSheetSide(), section_sheets=section_sheets,
                                  compare_disabled_reason=defs_borrow_reason() if mode == "borrow" else None)
    new_side = await _new_side(pid, sel, facts, mode=mode)
    src_side = _source_side(ru, sel, new_side.lines) if (mode == "improve" and v == "compare") else None
    tally = {k: sum(1 for ln in new_side.lines if ln.mark == k) for k in ("update", "keep", "new")}
    if src_side:
        tally["drop"] = sum(1 for ln in src_side.lines if ln.mark == "drop")
    changed = sum(1 for ln in new_side.lines if ln.mark in ("update", "new"))
    edited = sum(1 for ln in new_side.lines if ln.edited)
    open_items = [it for it in await repo.alist("confirm_items", {"proposal_id": pid}) if it.get("status") == "open" and it.get("sheet_id") in {s["id"] for s in shs}]
    ph_items = [it for it in open_items if it.get("fact_id")]
    guide: list[M.GuideStep] = []
    guide_label = ""
    if mode == "borrow" or v == "guide":
        tone = a.get("tone")
        from_src = 0
        for i, s in enumerate(shs):
            r = s.get("reuse") or {}
            fr = r.get("flow_role")
            if fr and fr not in ("이번 유형 기본",):
                from_src += 1
            n_ph = sum(1 for it in ph_items if it.get("sheet_id") == s["id"])
            chips = [*(r.get("rq_ids") or [])]
            if tone:
                chips.append(f"{tone} 톤")
            code = (s.get("template") or {}).get("code")
            if code:
                chips.append(code)
            if n_ph:
                chips.append(f"플레이스홀더 {n_ph}곳")
            step_src = next((st for st in (a.get("flow") or {}).get("steps") or [] if st.get("name") == fr), None)
            if mode == "borrow":
                from_source = (f"원본 {fr} {step_src.get('range') or ''} · 내용 안 가져옴".replace("  ", " ") if step_src else
                               ("원본에 없던 자리 · 새로 제안" if r.get("verdict") == "new" else "이번 유형 기본 자리"))
            else:
                pg = src.get(r.get("source_page") or -1)
                from_source = f"원본 p.{file_no(pg['no'])} {pg.get('title') or ''} · {defs.VERDICT_LABEL.get(r.get('verdict') or '', '')}" if pg else "원본 대응 없음"
            this_time = " · ".join(x for x in [" ".join(r.get("rq_ids") or []), f"톤 {tone}" if tone else "", "업종 레이아웃 추천" if code else "",
                                                "수치 비워 두고 [00] 플레이스홀더 · 확정 필요 등록" if n_ph else ""] if x)
            selected = bool(sel and s["id"] == sel["id"])
            guide.append(M.GuideStep(no=i + 1, title=s.get("title") or "", status="writing" if selected else "waiting",
                                     status_label="작성 중" if selected else "대기",
                                     role=(defs.ROLES.get(s.get("role") or "") or {}).get("msg", "") or core.role_name(s.get("role")),
                                     from_source=from_source, this_time=this_time or "이번 고객 자료로 새로 씀", chips=chips))
        guide_label = f"원본 역할 {from_src} / {len(shs)} 반영"
    placeholders = []
    if mode == "borrow" or v == "guide":
        for it in [x for x in ph_items if x.get("sheet_id") == sel["id"]]:
            t = it.get("text") or {}
            placeholders.append({"item_id": it["id"], "confirm_item_id": it["id"], "token": t.get("mark") or "[00]", "text": t.get("mark") or "[00]",
                                 "label": (t.get("pre") or "").strip()[-24:] or it.get("sub") or "", "tag": it.get("tag")})
    if mode == "borrow" or v == "guide":
        tally = {"writing": 1 if sel else 0, "waiting": max(0, len(shs) - 1), "confirm": len(ph_items)}
    if mode == "improve":
        footer = f"원본 대조 작성 · 바뀐 줄 {changed} · 유저가 고친 줄 {edited} · 4 / 6"
    else:
        footer = (f"흐름 가이드 작성 · {guide_label} · 수치 플레이스홀더 {len(ph_items)}곳 확정 필요 등록 · 4 / 6")
    return M.ReuseSectionView(view=v, mode=mode, header_label=header, section_key=key, sheet_id=sel["id"], source_label=source_label,
                              source_sheet=src_side, new_sheet=new_side, section_sheets=section_sheets, tally=tally, footer_label=footer,
                              guide=guide, guide_label=guide_label, placeholders=placeholders,
                              compare_disabled_reason=defs_borrow_reason() if mode == "borrow" else None)


def defs_borrow_reason() -> str:
    return "흐름 차용 모드에선 원본 내용을 보여주지 않아요"


def _append_lines(content: dict[str, Any], texts: list[str]) -> list[str]:
    """원본 줄을 새 시트 목록 칸 끝에 붙인다 → 붙인 줄 경로."""
    slots = content.setdefault("slots", {})
    target: tuple[str, str] | None = None
    for k, v in slots.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v) and any("text" in x for x in v):
            target = (k, "text")
            break
    if target is None:
        for k, v in slots.items():
            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v) and any(("body" in x or "title" in x) for x in v):
                target = (k, "body" if any("body" in x for x in v) else "title")
                break
    if target is None:
        slots.setdefault("bullets", [])
        target = ("bullets", "text")
    k, field = target
    paths = []
    for t in texts:
        slots[k].append({"id": C.lid("b"), field: t})
        paths.append(f"/slots/{k}/{len(slots[k]) - 1}/{field}")
    return paths


async def pull_lines(pid: str, sheet_id: str, body: M.PullLines) -> M.Sheet:
    """「원본 줄 끌어오기」 · 「원본 줄 전부 가져오기」(개선 · 수정만) — 비복제 줄은 가져오지 않는다(AC-189)."""
    p, ru, mode = await _derived(pid)
    if mode == "borrow":
        raise borrow_hidden()
    sh = await core.sheet_doc(pid, sheet_id)
    r = sh.get("reuse") or {}
    pg = _src_pages(ru).get(r.get("source_page") or -1)
    if not pg:
        raise unprocessable("NO_SOURCE_PAGE", "원본 쪽이 없는 시트예요")
    nc = _nc_ids(ru)
    pullable = [x for x in pg.get("lines") or [] if x["id"] not in nc]
    facts = await F.facts_of(pid)
    disp = C.display_content(sh.get("content") or {}, facts) if sh.get("content") else {}
    aligned = RF.align(RF.content_lines(disp), pullable)
    used = {x["source_line_id"] for x in aligned if x.get("source_line_id")}
    if body.line_ids:
        ids = {x["id"] for x in pullable}
        bad = [i for i in body.line_ids if i not in ids]
        if bad:
            raise unprocessable("LINE_NOT_AVAILABLE", "가져올 수 없는 원본 줄이에요(비복제 줄은 가져오지 않아요)", line_ids=bad)
        chosen = [x for x in pullable if x["id"] in set(body.line_ids)]
    elif body.all:
        chosen = [x for x in pullable if x["id"] not in used]
    else:
        raise unprocessable("LINES_REQUIRED", "가져올 원본 줄을 골라 주세요")
    if not chosen:
        from .sections import sheet_view
        return await sheet_view(sh)
    old = copy.deepcopy(sh.get("content") or {})
    new = copy.deepcopy(old)
    paths = _append_lines(new, [x["text"] for x in chosen])

    def fn(x: dict[str, Any]) -> None:
        x["content"] = new
        x["content_rev"] = int(x.get("content_rev") or 0) + 1
        x["user_edited"] = True
        if int(p.get("saved_version") or 0) > 0:
            x["edited_since_version"] = True
        rr = dict(x.get("reuse") or {})
        lines = list(rr.get("lines") or [])
        dl = dict(rr.get("draft_lines") or {})
        for path, src_line in zip(paths, chosen):
            lines.append({"line_id": path, "source_line_id": src_line["id"], "mark": "keep"})
            dl[path] = src_line["text"]
        rr["lines"] = lines
        rr["draft_lines"] = dl
        x["reuse"] = rr
        if x.get("status") == "need":
            x["status"] = "ready"
    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await core.record_change(pid, sheet=saved, where="원본 줄 가져오기", kind="content", path="/slots", from_=core.snippet(old.get("title")),
                             to=f"원본 줄 {len(chosen)}개", summary=f"{int(saved.get('sheet_no') or 0):02d} 원본 줄 {len(chosen)}개 가져옴",
                             extra={"op": "content", "from_full": old, "to_full": new})
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    from .sections import sheet_view
    return await sheet_view(saved)


# ── PRU5 요약 ──────────────────────────────────────────────
async def summary(pid: str) -> M.ReuseSummary:
    p, ru, mode = await _derived(pid)
    shs = await core.sheets_of(pid)
    keys = core.type_sections(p.get("type"))
    a = ru.get("analysis") or {}
    pl = ru.get(f"plan_{mode}") or {}
    src = _src_pages(ru)
    verdict_of = {s["id"]: (s.get("reuse") or {}).get("verdict") or "auto" for s in shs}
    rows = pl.get("rows") or []

    def names(v: str, n: int = 3) -> str:
        return " · ".join(dict.fromkeys(s.get("title") or "" for s in shs if verdict_of[s["id"]] == v))[:60] if n else ""
    drops = [r for r in rows if r.get("verdict") == "drop" or r.get("kind") == "drop"]
    n_drop = len(drops) if mode == "improve" else sum(int(r.get("src_count") or 0) for r in drops)
    counts = [
        M.SummaryCount(verdict="keep", label="유지", n=sum(1 for v in verdict_of.values() if v == "keep"), desc="원본 그대로" + (f" · {names('keep')}" if names("keep") else "")),
        M.SummaryCount(verdict="update", label="갱신", n=sum(1 for v in verdict_of.values() if v == "update"),
                       desc="모델 · 수치 현행화" + (f" · {names('update')}" if names("update") else "")),
        M.SummaryCount(verdict="rewrite", label="재작성", n=sum(1 for v in verdict_of.values() if v == "rewrite"),
                       desc="역할만 두고 다시 씀" + (f" · {names('rewrite')}" if names("rewrite") else "")),
        M.SummaryCount(verdict="new", label="신규", n=sum(1 for v in verdict_of.values() if v == "new"),
                       desc="요구사항 갭" + (f" · {names('new')}" if names("new") else "")),
        M.SummaryCount(verdict="drop", label="제외", n=n_drop,
                       desc=" · ".join(dict.fromkeys(str(r.get("sheet_name") or r.get("src_step") or "")[:12] for r in drops))[:60] or "없음"),
    ]
    mapping: list[M.SummaryMapRow] = []
    cover_n = sum(1 for pg in a.get("pages") or [] if pg.get("flow_role") == "표지")
    used_secs = [k for k in keys if any(s["section_key"] == k for s in shs)]
    struct = core.slides_total(p, 0, len(used_secs))
    mapping.append(M.SummaryMapRow(section="표지 · 목차 · 간지", src_count=cover_n, chips=[f"자동 {struct}"], new_count=struct,
                                   src_label=f"{cover_n}장" if cover_n else "—", new_label=f"{struct}장"))
    for k in keys:
        sec_sheets = [s for s in shs if s["section_key"] == k]
        if mode == "improve":
            src_rows = [r for r in rows if r.get("section_key") == k and r.get("page")]
        else:
            src_rows = [r for r in rows if k in (r.get("targets") or []) and r.get("kind") != "drop"]
        src_n = len(src_rows) if mode == "improve" else sum(int(r.get("src_count") or 0) for r in src_rows)
        if not sec_sheets and not src_n:
            continue
        tally: dict[str, int] = {}
        for s in sec_sheets:
            v = verdict_of[s["id"]]
            tally[v] = tally.get(v, 0) + 1
        if mode == "improve":
            dn = sum(1 for r in src_rows if r.get("verdict") == "drop")
            if dn:
                tally["drop"] = tally.get("drop", 0) + dn
        chips = [f"{defs.VERDICT_LABEL[v]} {n}" for v, n in sorted(tally.items(), key=lambda x: ["update", "keep", "rewrite", "new", "drop", "auto"].index(x[0]))]
        mapping.append(M.SummaryMapRow(section=defs.SECTIONS[k]["name"], src_count=src_n, chips=chips, new_count=len(sec_sheets),
                                       src_label=f"{src_n}장" if src_n else "—", new_label=f"{len(sec_sheets)}장"))
    gap = [s for s in shs if (s.get("repeat_key") or {}).get("kind") == "rq"]
    if gap:
        mapping.append(M.SummaryMapRow(section="요구사항 갭 · " + " · ".join((s.get("repeat_key") or {}).get("ref") or "" for s in gap), src_count=0,
                                       chips=[f"신규 {len(gap)}"], new_count=len(gap), src_label="—", new_label=f"{len(gap)}장"))
    nc_pages = [pg for pg in a.get("pages") or [] if pg.get("excluded")]
    if nc_pages:
        mapping.append(M.SummaryMapRow(section="견적 · 일정", src_count=len(nc_pages), chips=[f"제외 {len(nc_pages)}"], new_count=0,
                                       src_label=f"{len(nc_pages)}장", new_label="0장"))
    # 검토 필요(갱신한 수치 · 모델 · 원본과 달라진 곳)
    items = [it for it in await repo.alist("confirm_items", {"proposal_id": pid}) if it.get("status") == "open" and it.get("origin") == "reuse"]
    items.sort(key=lambda it: (0 if it.get("category") == "review" else 1, it.get("created_iso") or ""))
    from .confirm import views as item_views
    vis = await item_views(pid, items[:4])
    rest = items[4:]
    more = ""
    if rest:
        more = f"{len(rest)}곳 더 · " + " · ".join(dict.fromkeys((it.get("text") or {}).get("mark") or it.get("tag") or "" for it in rest[:2]))
    # 흔적
    srcs = ru.get("sources") or []
    s0 = srcs[0] if srcs else {}
    traced = [s for s in shs if (s.get("reuse") or {}).get("source_page")]
    v = int(p.get("saved_version") or 0)
    if s0.get("kind") == "proposal":
        sp = await repo.aget("proposals", s0.get("proposal_id") or "") or {}
        when = (sp.get("submitted_at") or "")[:10].replace("-", ".")
        orig = f"{s0.get('name')} v{s0.get('version') or ''} · " + (f"{when} 제출본 그대로" if when else "원본 그대로")
    else:
        orig = " · ".join(m.get("name") or "" for m in srcs[:2]) + " · 원본 파일 그대로"
    traces = [M.TraceRow(title="새 제안서 각 시트 노트에 '원본 p.N 기반 · 갱신' 기록" if mode == "improve" else "새 제안서 각 시트 노트에 '흐름 차용 · 역할' 기록",
                         sub=f"시트 {len(traced) if mode == 'improve' else len(shs)}장 · 되돌리기 가능"),
              M.TraceRow(title=f"버전 이력에 '{(p.get('derived_from') or {}).get('label') or '원본에서 파생'}' 표시",
                         sub=f"새 제안서 v{v or 1} · 파생 관계가 목록에도 보여요"),
              M.TraceRow(title="원본 제안서는 바뀌지 않음", sub=orig)]
    # 원본 대비 변경 = 갱신 + 재작성 + 신규 + 원본 시트가 모두 제외된 섹션의 자동 생성 장(구조 장 제외, §10.10)
    dropped_secs = {k for k in keys if mode == "improve" and any(r.get("section_key") == k for r in rows)
                    and all(r.get("verdict") == "drop" for r in rows if r.get("section_key") == k)}
    auto_in_dropped = sum(1 for s in shs if verdict_of[s["id"]] == "auto" and s["section_key"] in dropped_secs)
    changed = sum(1 for x in verdict_of.values() if x in ("update", "rewrite", "new")) + auto_in_dropped
    if mode == "borrow":
        changed = len(shs)
    gen = p.get("generate") or {}
    ver = await VER.get_version(pid, v) if v else None
    slides = int((ver or {}).get("slides") or gen.get("slides") or core.slides_total(p, len(shs), len(used_secs)))
    fname = (ver or {}).get("file_name") or gen.get("file_name") or ""
    master = (p.get("design") or {}).get("master_name") or next((m["name"] for m in defs.MASTERS if m["id"] == ((p.get("design") or {}).get("master_id") or defs.DEFAULT_MASTER)), "삼성 B2B 표준")
    src_total = len(a.get("pages") or [])
    short = (s0.get("name") or "원본")[:24]
    intro = (f"PPTX {slides}장을 만들었어요. 원본({short} · {src_total}장)과 비교해 무엇을 그대로 두고, 무엇을 바꾸고, 무엇을 새로 넣었는지 정리했어요. "
             "갱신한 수치 · 모델은 검토 필요 목록에 모았어요.") if v else \
        (f"원본({short} · {src_total}장)과 비교해 무엇을 그대로 두고, 무엇을 바꾸고, 무엇을 새로 넣었는지 정리했어요. PPTX를 만들면 이 요약이 완성돼요.")
    return M.ReuseSummary(intro=intro, counts=counts, mapping=mapping, mapping_label=f"원본 {src_total}장 · {short}", review_items=vis,
                          review_total=len(items), review_more_label=more, traces=traces, changed_count=changed,
                          footer_label=f"완료 · {slides}장 · 원본 대비 변경 {changed}장 · 6 / 6",
                          file_label=(f"{fname} · {slides}장 · 16:9 · {master} 템플릿 · 원본 제안서는 바뀌지 않았어요." if fname else
                                      "원본 제안서는 바뀌지 않았어요."))
