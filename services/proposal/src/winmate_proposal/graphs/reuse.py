"""reuse(§7.10) — 기존 제안서 분석(9기준) → 계획 → 적용. 한 thread(= job_id)에 사람 확인 두 번.

ingest(읽기 · 쪽 나누기) → analyze(9기준, LLM 은 모두 기밀) → **await_analysis**(interrupt `reuse_confirm_analysis`:
confirm → plan · reanalyze → analyze(고정 유지) · switch_mode → plan) → plan(개선 | 흐름 차용) → **await_plan**(interrupt
`reuse_confirm_plan`: apply → apply · switch_mode → plan) → apply(유형 · 구성 · 시트 reuse 메타 · derived_from · 섹션 작성 · 검토 항목).

큰 데이터(원본 쪽 · 분석 · 계획)는 `reuse` 문서(pru_)에 두고 그래프 상태는 작게 둔다. API 가 잡을 기다리지 못한 입력(경합)은
문서의 `requested` 로 넘긴다(대기 노드가 먼저 확인).
"""
from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from winmate_common.errors import ApiError
from winmate_common.jobs import AwaitingInput, JobCanceled, JobContext, jobs

from .. import config, core, defs, facts as F, plan as PL, repo, reuse_analysis as RA
from . import common as G
from . import reuse_fill as RF
from . import section_fill as SF

log = logging.getLogger("winmate.proposal.reuse_graph")

LABELS = {"ingest": "읽기 · 쪽 나누기", "analyze": "기준별 분석", "await_analysis": "분석 확인", "plan": "활용 계획",
          "await_plan": "계획 확정", "apply": "시트 구성 적용"}
PROGRESS = {"ingest": 25, "analyze": 60, "plan": 70, "apply": 100}
PHASE_KEYS = (("read", "읽기"), ("split", "쪽 나누기"), ("analyze", "기준별 분석"))


def phases(read: str, split: str, analyze: str) -> list[dict[str, Any]]:
    st = {"read": read, "split": split, "analyze": analyze}
    return [{"key": k, "label": lb, "status": st[k]} for k, lb in PHASE_KEYS]


async def own(rid: str, job: str | None) -> dict[str, Any]:
    """이 잡이 아직 이 분석의 주인인가(원본을 더해 다시 시작하면 옛 잡은 멈춘다)."""
    ru = await repo.aget("reuse", rid)
    if not ru:
        raise ApiError(404, "REUSE_NOT_FOUND", "기존 제안서 분석을 찾을 수 없어요", {"id": rid})
    if job and ru.get("job_id") and ru["job_id"] != job:
        raise JobCanceled()
    return ru


async def save(rid: str, **fields: Any) -> dict[str, Any]:
    saved, _ = await repo.amutate("reuse", rid, lambda d: d.update({**fields, "updated_iso": config.now_iso()}))
    return saved


async def set_pr(pid: str, **fields: Any) -> None:
    def fn(x: dict[str, Any]) -> None:
        r = dict(x.get("reuse") or {})
        r.update(fields)
        x["reuse"] = r
    await core.mutate(pid, fn, bump=False)
    await core.index(pid)


def plan_type(p: dict[str, Any], ru: dict[str, Any], mode: str) -> str:
    """개선 · 수정은 원본(Winmate) 유형, 흐름 차용은 이 제안서 유형(없으면 표준)."""
    if mode == "improve":
        t = next((m.get("type") for m in ru.get("sources") or [] if m.get("kind") == "proposal" and m.get("type")), None)
        if t in defs.TYPES:
            return t
    return p.get("type") if p.get("type") in defs.TYPES else "standard"


async def compute_plan(pid: str, rid: str, mode: str) -> dict[str, Any]:
    """활용 계획(결정적) — 잡의 plan 노드와 API(방식 바꾸기)가 같이 쓴다. 고친 판정(locks.rows)은 지킨다."""
    ru = await repo.amust("reuse", rid)
    p = await core.load(pid)
    if not p.get("ctx"):
        p["ctx"] = await PL.refresh_context(pid)
    a = ru["analysis"]
    type_ = plan_type(p, ru, mode)
    if mode == "improve":
        pl = RA.plan_improve(p, a, ru.get("src_pages") or [], locks=ru.get("locks") or {}, prev_plan=ru.get("plan_improve"), type_=type_)
        return await save(rid, plan_improve=pl, plan_type=type_, mode=mode)
    pl = RA.plan_borrow(p, a, type_=type_)
    return await save(rid, plan_borrow=pl, plan_type=type_, mode=mode)


async def inherit(pid: str, metas: list[dict[str, Any]]) -> None:
    """같은 고객 Winmate 원본 — 이 제안서에 고객이 비어 있으면 이어받고, 정의서가 없으면 원본의 정의서를 연결(§4.10)."""
    p = await core.load(pid)
    src = next((m for m in metas if m.get("kind") == "proposal"), None)
    if not src:
        return
    sp = await repo.aget("proposals", src["proposal_id"]) or {}
    cust = p.get("customer") or {}
    scust = sp.get("customer") or {}
    changed = False

    def fn(x: dict[str, Any]) -> None:
        nonlocal changed
        c = dict(x.get("customer") or {})
        if not c.get("name") and scust.get("name"):
            for k in ("name", "industry_code", "industry_label", "scale_text"):
                if scust.get(k) and not c.get(k):
                    c[k] = scust[k]
            x["customer"] = c
            changed = True
        same = RA.norm_name(c.get("name") or "") == RA.norm_name(scust.get("name") or "")
        if same and not x.get("rq_ref") and sp.get("rq_ref"):
            x["rq_ref"] = dict(sp["rq_ref"])
            changed = True
    if not cust.get("name") or not p.get("rq_ref"):
        await core.mutate(pid, fn)
    if changed:
        await PL.refresh_context(pid)


# ── 노드 ───────────────────────────────────────────────────
async def n_ingest(s: dict[str, Any]) -> dict[str, Any]:
    pid, rid, job = s["pid"], s["rid"], s.get("job")
    ru = await own(rid, job)
    await save(rid, status="analyzing", phases=phases("busy", "todo", "todo"), error=None)
    await set_pr(pid, status="analyzing")
    await G.progress(5, "원본 읽기")
    metas, pages = await RA.read_sources(ru.get("sources_in") or [])
    await G.check_cancel()
    if not pages:
        raise ApiError(422, "SOURCE_EMPTY", "원본에서 읽을 수 있는 쪽이 없어요")
    await inherit(pid, metas)
    await own(rid, job)
    await save(rid, sources=metas, src_pages=pages, phases=phases("done", "done", "busy"))
    await G.partial({"reuse_id": rid, "phase": "split", "pages": len(pages), "sources": len(metas)})
    return {"action": None}


async def n_analyze(s: dict[str, Any]) -> dict[str, Any]:
    pid, rid, job = s["pid"], s["rid"], s.get("job")
    ru = await own(rid, job)
    await save(rid, status="analyzing", phases=phases("done", "done", "busy"))
    await set_pr(pid, status="analyzing")
    p = await core.load(pid)
    if not p.get("ctx"):
        p["ctx"] = await PL.refresh_context(pid)
    a = await RA.analyze(p, ru.get("sources") or [], ru.get("src_pages") or [], locks=ru.get("locks") or {}, prev=ru.get("analysis"))
    await G.check_cancel()
    await own(rid, job)
    pref = ru.get("mode_pref") or "auto"
    await save(rid, analysis=a, status="awaiting_confirm", phases=phases("done", "done", "done"),
               mode=ru.get("mode") or (pref if pref in ("improve", "borrow") else None))
    await set_pr(pid, status="awaiting_confirm")
    await G.partial({"reuse_id": rid, "status": "awaiting_confirm", "recommendation": a.get("recommendation")})
    return {"action": None}


def _answer(ans: Any) -> dict[str, Any]:
    if isinstance(ans, dict):
        return ans
    return {"action": str(ans or "confirm")}


async def _requested(rid: str, stage: str) -> dict[str, Any] | None:
    ru = await repo.aget("reuse", rid) or {}
    req = ru.get("requested") or None
    if req and req.get("stage") == stage:
        await save(rid, requested=None)
        return req
    return None


async def n_await_analysis(s: dict[str, Any]) -> dict[str, Any]:
    ans = await _requested(s["rid"], "analysis")
    if ans is None:
        ans = _answer(interrupt({"kind": "reuse_confirm_analysis", "ref": s["rid"]}))
    action = ans.get("action") or "confirm"
    if action == "reanalyze":
        return {"action": "reanalyze"}
    return {"action": action, "mode": ans.get("mode")}


async def n_plan(s: dict[str, Any]) -> dict[str, Any]:
    pid, rid, job = s["pid"], s["rid"], s.get("job")
    ru = await own(rid, job)
    a = ru.get("analysis") or {}
    mode = s.get("mode") or ru.get("mode") or (a.get("recommendation") or {}).get("mode") or "borrow"
    await save(rid, status="planning", mode=mode)
    await set_pr(pid, status="planning", mode=mode)
    await compute_plan(pid, rid, mode)
    await own(rid, job)
    await save(rid, status="awaiting_plan_confirm")
    await set_pr(pid, status="awaiting_plan_confirm", mode=mode)
    await G.partial({"reuse_id": rid, "status": "awaiting_plan_confirm", "mode": mode})
    return {"mode": mode, "action": None}


async def n_await_plan(s: dict[str, Any]) -> dict[str, Any]:
    ans = await _requested(s["rid"], "plan")
    if ans is None:
        ans = _answer(interrupt({"kind": "reuse_confirm_plan", "ref": s["rid"]}))
    action = ans.get("action") or "apply"
    return {"action": action, "mode": ans.get("mode"), "then": ans.get("then")}


# ── 적용 ───────────────────────────────────────────────────
def match_improve(rows: list[dict[str, Any]], shs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """판정 행 → 새 시트(같은 자리 → 같은 섹션 · 역할 → 같은 섹션). 제외 행은 시트가 없다."""
    out: dict[str, dict[str, Any]] = {}
    used: set[str] = set()
    done: set[str] = set()
    for r in rows:
        if r.get("verdict") == "new" and r.get("rq"):
            sh = next((x for x in shs if x["id"] not in used and x.get("role") == "OP" and (x.get("repeat_key") or {}).get("ref") == r["rq"]["code"]), None)
            if sh:
                out[sh["id"]] = r
                used.add(sh["id"])
                done.add(r["row_id"])
    live = [r for r in rows if r.get("verdict") in ("keep", "update", "rewrite") and r.get("section_key")]

    def same_repeat(r: dict[str, Any], x: dict[str, Any]) -> bool:
        # 반복 시트(사례 · 공간 · 제품)는 같은 대상끼리만
        xr = (x.get("repeat_key") or {}).get("ref")
        return not (r.get("repeat_ref") and xr and xr != r["repeat_ref"])
    passes = [
        lambda r, x: bool(r.get("ident")) and x.get("ident") == r["ident"],
        lambda r, x: x.get("section_key") == r["section_key"] and bool(r.get("role")) and x.get("role") == r["role"] and same_repeat(r, x),
        lambda r, x: x.get("section_key") == r["section_key"] and same_repeat(r, x),
    ]
    for test in passes:
        for r in live:
            if r["row_id"] in done:
                continue
            sh = next((x for x in shs if x["id"] not in used and test(r, x)), None)
            if sh:
                out[sh["id"]] = r
                used.add(sh["id"])
                done.add(r["row_id"])
    return out


def guide_borrow(rows: list[dict[str, Any]], shs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """흐름 차용 — 시트마다 원본 흐름 단계(역할 · 근거 유형 · 이번엔 R)."""
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r.get("kind") == "drop":
            continue
        if r.get("rq"):
            sh = next((x for x in shs if x["id"] not in out and x.get("role") == "OP" and (x.get("repeat_key") or {}).get("ref") == r["rq"]["code"]), None)
            if sh:
                out[sh["id"]] = r
            continue
        for t in r.get("targets") or []:
            remaining = [x for x in shs if x.get("section_key") == t and x["id"] not in out]
            take = remaining[:1] if (r["src_step"] == "고객 과제" and str(r.get("new_label") or "").startswith("Value Props 안")) else remaining
            for x in take:
                out[x["id"]] = r
    return out


async def review_items(pid: str, ru: dict[str, Any], changes: dict[str, list[dict[str, Any]]], assigned: dict[str, dict[str, Any]]) -> list[str]:
    """PRU5 「검토 필요」 — 단종 치환 · 정책 · 수치 · 값 전파(category review, origin reuse)."""
    a = ru["analysis"]
    out: list[str] = []
    year_now = int(a.get("year_now") or config.today_kst().year)
    store_done = False
    for sid, chs in changes.items():
        sh = await repo.aget("sheets", sid)
        if not sh:
            continue
        title = sh.get("title") or core.role_name(sh.get("role"))
        act = {"kind": "button", "label": "바로 고치기", "target": {"route": core.route(pid, "preview", str(sh.get("sheet_no") or ""))}}
        for c in chs:
            if c["kind"] == "model":
                it = await F.add_item(pid, sheet=sh, tag="단종 치환", category="review", origin="reuse", action=act,
                                      text={"pre": f"{title} ", "mark": f"{c['from']} → {c['to']}", "post": " 치환 확인"},
                                      sub=f"{title} · {c['from']} 단종 — 후속 {c['to']}로 바꿨어요")
            elif c["kind"] == "solution":
                it = await F.add_item(pid, sheet=sh, tag="정책", category="review", origin="reuse", action=act,
                                      text={"pre": f"{c['name']} {c['to']} ", "mark": "가격 정책", "post": f" · 라이선스 단위가 {c['from']}과 달라요"},
                                      sub=f"{title} · 버전을 {c['from']} → {c['to']}로 바꿨어요")
            elif c["kind"] == "stale":
                it = await F.add_item(pid, sheet=sh, tag="수치", category="review", origin="reuse", action=act,
                                      text={"pre": f"{title} ", "mark": f"{year_now} 조사 반영", "post": f" · {c['year']} 수치 교체"},
                                      sub=f"{title} · 오래된 수치는 [00]으로 비워 두었어요")
            elif c["kind"] == "store" and not store_done:
                store_done = True
                it = await F.add_item(pid, sheet=sh, tag="값 전파", category="review", origin="reuse", action=act,
                                      text={"pre": "매장 수 ", "mark": f"{int(c['to']):,}", "post": f" 전 시트 반영 · 원본 {c['from']}"},
                                      sub="매장 수는 값 하나로 묶여 있어 고치면 모든 시트가 함께 바뀌어요")
            else:
                continue
            out.append(it["id"])
    for sid, r in assigned.items():
        sh = await repo.aget("sheets", sid)
        if not sh:
            continue
        title = sh.get("title") or core.role_name(sh.get("role"))
        act = {"kind": "button", "label": "바로 고치기", "target": {"route": core.route(pid, "preview", str(sh.get("sheet_no") or ""))}}
        if r.get("verdict") == "rewrite" and (r.get("change") or {}).get("kind") == "unsourced":
            it = await F.add_item(pid, sheet=sh, tag="수치", category="review", origin="reuse", action=act,
                                  text={"pre": f"{title} ", "mark": "효과 수치 출처", "post": " · 원본 수치는 출처가 없어 쓰지 않았어요"},
                                  sub=f"{title} · 이번 고객 기준 수치로 채워 주세요")
            out.append(it["id"])
        elif r.get("verdict") in ("keep", "update") and sh.get("role") in ("CD", "CL"):
            it = await F.add_item(pid, sheet=sh, tag="공개 여부", category="review", origin="reuse", action=act,
                                  text={"pre": f"{title} ", "mark": "사례 공개 범위", "post": " 확인"},
                                  sub=f"{title} · 원본에서 가져온 사례예요 — 이번 고객에게 공개해도 되는지 확인")
            out.append(it["id"])
    return out


async def n_apply(s: dict[str, Any]) -> dict[str, Any]:
    pid, rid, job = s["pid"], s["rid"], s.get("job")
    ru = await own(rid, job)
    a = ru["analysis"]
    mode = ru.get("mode") or (a.get("recommendation") or {}).get("mode") or "borrow"
    if not ru.get(f"plan_{mode}"):
        ru = await compute_plan(pid, rid, mode)
    pl = ru.get(f"plan_{mode}") or {}
    p = await core.load(pid)
    type_ = ru.get("plan_type") or plan_type(p, ru, mode)
    await save(rid, status="planning", applying=True)
    await set_pr(pid, status="planning", mode=mode)
    await G.progress(72, "유형 · 시트 구성 적용")
    # 1 유형 · 구성(원본 유형 또는 계획) — 기본 구성으로 시트를 만들고
    from ..ops.compose import set_type
    await set_type(pid, type_, source="reuse", advance=True)
    keys = core.type_sections(type_)
    # 2 요구사항 갭 → 신규 시트(운영 시나리오 자리 · 요구사항마다 1장)
    gaps = [r["rq"] for r in pl.get("rows") or [] if r.get("rq") and (r.get("verdict") == "new" or r.get("kind") == "new")]
    if gaps:
        gsec = "solution" if "solution" in keys else next((k for k in reversed(keys) if k not in ("why", "spec", "cases")), keys[-1])
        sec = await core.section_doc(pid, gsec)
        items = [{"kind": "rq", "ref": g["code"], "label": (g.get("name") or g["code"])[:30]} for g in gaps]

        def comp_fn(x: dict[str, Any]) -> None:
            comp = [r for r in x.get("composition") or [] if r["code"] != "OP"]
            comp.append({"code": "OP", "state": "on", "user_set": True, "items": items})
            x["composition"] = comp
            x["enabled"] = True
        await repo.amutate("sections", sec["id"], comp_fn)
        await PL.sync_sheets(pid)
    # 2b 원본에서 이어 쓰는 사례(이번 추천 목록에 없던 것) → 사례 시트를 더한다(개선)
    if mode == "improve" and "cases" in keys:
        have = {(x.get("repeat_key") or {}).get("ref") for x in await core.sheets_of(pid, section_key="cases")}
        extra = [{"kind": "case", "ref": r["repeat_ref"], "label": PL.case_short(r.get("sheet_name") or "")}
                 for r in pl.get("rows") or [] if r.get("verdict") in ("keep", "update", "rewrite") and r.get("section_key") == "cases"
                 and r.get("role") == "CD" and r.get("repeat_ref") and r["repeat_ref"] not in have]
        if extra:
            csec = await core.section_doc(pid, "cases")

            def case_fn(x: dict[str, Any]) -> None:
                for row in x.get("composition") or []:
                    if row["code"] == "CD":
                        row["items"] = [*(row.get("items") or []), *[e for e in extra if e["ref"] not in {i.get("ref") for i in row.get("items") or []}]]
                        row["state"] = "on"
                        row["user_set"] = True
            await repo.amutate("sections", csec["id"], case_fn)
            await PL.sync_sheets(pid, sections=["cases"])
    # 3 시트 ↔ 판정(개선) · 흐름 단계(차용)
    shs = await core.sheets_of(pid)
    assigned = match_improve(pl.get("rows") or [], shs) if mode == "improve" else guide_borrow(pl.get("rows") or [], shs)
    guide: dict[str, dict[str, Any]] = {}
    for sh in shs:
        r = assigned.get(sh["id"])
        if mode == "improve":
            meta = ({"source_page": r.get("page"), "verdict": r["verdict"], "flow_role": r.get("flow_role"), "lines": [], "note": r.get("note") or "",
                     "row_id": r["row_id"], "rq_ids": r.get("rq_ids") or [], "change": r.get("change")} if r else
                    {"source_page": None, "verdict": "auto", "flow_role": None, "lines": [], "note": "원본 대응 없음 · 새로 작성"})
        else:
            meta = ({"source_page": None, "verdict": "new" if r.get("kind") == "new" else "auto", "flow_role": r.get("src_step"), "lines": [],
                     "note": r.get("note") or "", "rq_ids": r.get("rq_ids") or [], "src_range": r.get("src_range") or ""} if r else
                    {"source_page": None, "verdict": "auto", "flow_role": None, "lines": [], "note": "이번 유형 기본"})
            guide[sh["id"]] = {"flow_role": meta["flow_role"], "rq_ids": meta["rq_ids"]}

        def fn(x: dict[str, Any], meta: dict[str, Any] = meta) -> None:
            x["reuse"] = meta
            x["origin"] = "reuse"
        await repo.amutate("sheets", sh["id"], fn)
    # 4 파생 표시 · 단계(원본은 바꾸지 않는다)
    srcs = ru.get("sources") or []
    s0 = srcs[0] if srcs else {}
    if s0.get("kind") == "proposal":
        label = f"{s0.get('name')} v{s0.get('version')}에서 파생" if s0.get("version") else f"{s0.get('name')}에서 파생"
        derived = {"kind": "proposal", "proposal_id": s0.get("proposal_id"), "version": s0.get("version"),
                   "file_ids": [m["file_id"] for m in srcs if m.get("kind") == "file"]}
    else:
        label = f"{s0.get('name') or '원본 파일'}에서 파생"
        derived = {"kind": "file", "proposal_id": None, "version": None, "file_ids": [m["file_id"] for m in srcs if m.get("kind") == "file"]}
    first = None
    for k in keys:
        if any((x.get("reuse") or {}).get("verdict") != "auto" for x in await core.sheets_of(pid, section_key=k)):
            first = k
            break
    first = first or (keys[0] if keys else None)
    derived.update({"reuse_id": rid, "label": label, "mode": mode, "sections": keys})

    def pfn(x: dict[str, Any]) -> None:
        x["derived_from"] = derived
        x["reuse"] = {"reuse_id": rid, "mode": mode, "status": "planning"}
        x["start_mode"] = "reuse"
        x["type_source"] = "reuse"
        core.advance_stage(x, "sections")
        if first:
            x["current_section_key"] = first
    await core.mutate(pid, pfn)
    # 5 섹션마다 작성(개선 = 원본 대조 초안, 차용 = 흐름 가이드 초안)
    enabled = [k for k in keys if (await core.section_doc(pid, k)).get("enabled", True)]
    for k in enabled:
        sec = await core.section_doc(pid, k)
        await repo.amutate("sections", sec["id"], lambda x: x.update({"status_before_fill": "empty" if x.get("status") in (None, "empty") else x.get("status"),
                                                                       "status": "filling", "fill_job_id": job}))
    changes: dict[str, list[dict[str, Any]]] = {}
    ru = await own(rid, job)
    for i, k in enumerate(enabled):
        await G.check_cancel()
        try:
            if mode == "improve":
                res = await RF.fill_improve(pid, k, ru, job=job, memos=s.get("memos") or [])
                changes.update({sid: c for sid, c in (res.get("changes") or {}).items() if c})
            else:
                await RF.fill_borrow(pid, k, ru, job=job, memos=s.get("memos") or [], guide=guide)
        except ApiError as exc:
            if exc.code == "POLICY_CONFIDENTIAL":
                raise
            log.warning("섹션 %s 작성 실패: %s", k, exc.code)
        finally:
            await SF.reset_section(pid, k, job)
        await G.progress(72 + int(26 * (i + 1) / max(1, len(enabled))), f"{defs.SECTIONS[k]['name']} 작성")
        await G.partial({"reuse_id": rid, "section_key": k, "status": "ready"})
    # 6 검토 항목(개선 · 수정)
    items = await review_items(pid, ru, changes, assigned) if mode == "improve" else []
    await F.sync_items(pid)
    n_sheets = len(await core.sheets_of(pid))
    await save(rid, status="applied", applying=False, applied={"at": config.now_iso(), "mode": mode, "type": type_, "sheets": n_sheets,
                                                              "review_item_ids": items, "first_section": first,
                                                              "unmatched_rows": [r["row_id"] for r in pl.get("rows") or []
                                                                                 if r.get("verdict") in ("keep", "update", "rewrite")
                                                                                 and r["row_id"] not in {x["row_id"] for x in assigned.values() if x.get("row_id")}]
                                                              if mode == "improve" else []})
    await set_pr(pid, status="applied", mode=mode)
    await core.index(pid, force=True)
    return {"result": {"proposal_id": pid, "reuse_id": rid, "mode": mode, "type": type_, "sheets": n_sheets, "first_section": first}}


# ── 그래프 ─────────────────────────────────────────────────
def build() -> StateGraph:
    g = StateGraph(dict)
    for name, fn in (("ingest", n_ingest), ("analyze", n_analyze), ("await_analysis", n_await_analysis), ("plan", n_plan),
                     ("await_plan", n_await_plan), ("apply", n_apply)):
        g.add_node(name, G.merging(fn))
    g.add_conditional_edges(START, lambda s: s.get("start") if s.get("start") in ("ingest", "analyze", "plan", "apply") else "ingest",
                            {"ingest": "ingest", "analyze": "analyze", "plan": "plan", "apply": "apply"})
    g.add_edge("ingest", "analyze")
    g.add_edge("analyze", "await_analysis")
    g.add_conditional_edges("await_analysis", lambda s: "analyze" if s.get("action") == "reanalyze" else "plan",
                            {"analyze": "analyze", "plan": "plan"})
    g.add_edge("plan", "await_plan")
    g.add_conditional_edges("await_plan", lambda s: {"switch_mode": "plan", "reanalyze": "analyze"}.get(s.get("action") or "", "apply"),
                            {"plan": "plan", "analyze": "analyze", "apply": "apply"})
    g.add_edge("apply", END)
    return g


async def mark_failed(pid: str, rid: str, job: str, exc: BaseException) -> None:
    err = {"code": getattr(exc, "code", None) or type(exc).__name__, "message": getattr(exc, "message", None) or str(exc) or "분석하지 못했어요"}
    try:
        ru = await repo.aget("reuse", rid)
        if not ru or (ru.get("job_id") and ru["job_id"] != job):
            return
        await save(rid, status="failed", error=err, applying=False,
                   phases=[{**ph, "status": "todo" if ph["status"] == "busy" else ph["status"]} for ph in ru.get("phases") or phases("todo", "todo", "todo")])
        await set_pr(pid, status="failed")
        for sec in await core.sections_of(pid):
            if sec.get("fill_job_id") == job:
                await SF.reset_section(pid, sec["key"], job)
    except Exception:  # noqa: BLE001
        log.warning("분석 실패 기록 못 함 %s", rid)


async def handle(ctx: JobContext) -> dict[str, Any] | None:
    pl = ctx.payload
    pid, rid = pl["proposal_id"], pl["reuse_id"]
    state = {"pid": pid, "rid": rid, "job": ctx.job.id, "start": pl.get("start") or "ingest", "memos": [], "action": None, "mode": pl.get("mode")}
    try:
        final = await G.run(ctx, build(), state, labels=LABELS, progress_map=PROGRESS)
    except AwaitingInput:
        raise
    except JobCanceled:
        # 계획 확정 때 「작성 중」으로 표시해 둔 섹션을 되돌린다(ops.reuse.confirm_plan)
        for sec in await core.sections_of(pid):
            if sec.get("fill_job_id") == ctx.job.id:
                await SF.reset_section(pid, sec["key"], ctx.job.id)
        raise
    except BaseException as exc:
        await mark_failed(pid, rid, ctx.job.id, exc)
        raise
    return (final or {}).get("result") or {"proposal_id": pid, "reuse_id": rid}


async def signal(pid: str, ru: dict[str, Any], answer: dict[str, Any], *, stage: str) -> str | None:
    """잡에 사람 확인 답을 넘긴다. 대기 중이면 입력(J3), 아직 앞 노드면 문서 `requested`, 끝났으면 그 단계부터 새 잡."""
    job_id = ru.get("job_id")
    j = await jobs().get(job_id) if job_id else None
    if j and j.status == "awaiting_input":
        try:
            await jobs().provide_input(job_id, answer)
            return job_id
        except ValueError:
            j = await jobs().get(job_id)
    if j and j.status in ("queued", "running", "awaiting_input"):
        await save(ru["id"], requested={**answer, "stage": stage})
        j = await jobs().get(job_id)
        if j and j.status == "awaiting_input":
            try:
                await jobs().provide_input(job_id, answer)
            except ValueError:
                pass
        return job_id
    # 잡이 끝났거나 없음 → 그 단계부터 새 잡(같은 분석 문서)
    start = {"analysis": "plan" if answer.get("action") != "reanalyze" else "analyze", "plan": "apply" if answer.get("action") == "apply" else "plan"}[stage]
    if answer.get("action") == "reanalyze" and not ru.get("src_pages"):
        start = "ingest"
    p = await core.load(pid)
    new_job = await G.enqueue("proposal.reuse", {"proposal_id": pid, "reuse_id": ru["id"], "start": start, "mode": answer.get("mode")},
                              title="기존 제안서 활용", ref=pid, project_id=p.get("project_id"))
    await save(ru["id"], job_id=new_job, requested=None)

    def fn(x: dict[str, Any]) -> None:
        core.set_job(x, "reuse", new_job)
    await core.mutate(pid, fn, bump=False)
    return new_job
