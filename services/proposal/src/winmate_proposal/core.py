"""제안서 핵심 — 문서 만들기 · 읽기 · 리비전 · 라벨(§10.11) · 라우트 · 화면 모델 · workspace 색인(§5.17)."""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import timedelta
from typing import Any

from winmate_common.context import current_user
from winmate_common.ids import new_id
from winmate_common.platform import register_item

from . import config, defs, repo
from . import models as M
from .errors import proposal_not_found, rev_conflict, section_not_in_type, sheet_not_found

log = logging.getLogger("winmate.proposal.core")


# ── 라우트 ─────────────────────────────────────────────────
def route(pid: str, *parts: str) -> str:
    tail = "/".join(p for p in parts if p)
    return f"{defs.ROUTE_BASE}/{pid}" + (f"/{tail}" if tail else "")


def section_route(pid: str, key: str) -> str:
    return route(pid, "sections", key)


def stage_route(p: dict[str, Any]) -> str:
    pid = p["id"]
    stage = p.get("stage") or "customer"
    oc = p.get("one_click") or {}
    if oc.get("status") in ("running", "queued"):
        return route(pid, "one-click", oc["job_id"])
    if stage == "customer":
        mode = p.get("start_mode")
        if mode == "rfp":
            return route(pid, "rfp")
        if mode == "works":
            return route(pid, "works")
        if mode == "reuse":
            ru = p.get("reuse") or {}
            if ru.get("reuse_id"):
                st = ru.get("status")
                if st in ("awaiting_plan_confirm", "planning"):
                    return route(pid, "reuse", "plan") + f"?mode={ru.get('mode') or 'improve'}"
                return route(pid, "reuse", "analysis")
            return route(pid, "reuse")
        return route(pid, "customer")
    if stage == "type":
        return route(pid, "type")
    if stage == "compose":
        return route(pid, "compose")
    if stage == "industry":
        return route(pid, "industry")
    if stage == "sections":
        key = p.get("current_section_key") or (defs.TYPES.get(p.get("type") or "standard", {}).get("sections") or ["mi"])[0]
        return section_route(pid, key)
    if stage == "design":
        return route(pid, "design")
    if (p.get("derived_from") or {}).get("reuse_id") and p.get("saved_version"):
        return route(pid, "reuse", "summary")
    return route(pid, "result")


# ── 문서 ───────────────────────────────────────────────────
def default_design() -> dict[str, Any]:
    return M.Design().model_dump()


def default_industry_layout() -> dict[str, Any]:
    return M.IndustryLayout().model_dump()


def new_proposal_doc(*, start_mode: str, title: str = "", customer: dict[str, Any] | None = None, project_id: str | None = None,
                     language: str = "ko", schedule: dict[str, Any] | None = None) -> dict[str, Any]:
    user = current_user()
    now = config.now_iso()
    return {
        "id": new_id("pr"), "project_id": project_id, "owner_id": user.id, "owner_name": user.name,
        "title": title or "", "customer": {**M.Customer().model_dump(), **(customer or {})},
        "schedule": {**M.Schedule().model_dump(), **(schedule or {})}, "budget_text": None, "language": language or "ko",
        "rq_ref": None, "start_mode": start_mode, "start_files": [], "rfp": None, "type": None, "type_source": None,
        "stage": "customer", "current_section_key": None, "industry_layout": default_industry_layout(),
        "design": default_design(), "status": "draft", "submitted_at": None, "saved_version": 0, "rev": 1,
        "edits_since_version": 0, "files": {}, "derived_from": None, "reuse": None, "one_click": None, "review": None,
        "ctx": {}, "jobs": {}, "generate": None, "checks": {}, "comment_counts": {}, "created_iso": now,
    }


async def load(pid: str) -> dict[str, Any]:
    return await repo.amust("proposals", pid, proposal_not_found(pid))


def load_sync(pid: str) -> dict[str, Any]:
    return repo.must("proposals", pid, proposal_not_found(pid))


async def sections_of(pid: str, *, include_hidden: bool = False) -> list[dict[str, Any]]:
    secs = await repo.alist("sections", {"proposal_id": pid})
    if not include_hidden:
        secs = [s for s in secs if not s.get("hidden")]
    return sorted(secs, key=lambda s: s.get("order", 0))


async def sheets_of(pid: str, *, include_excluded: bool = False, section_key: str | None = None) -> list[dict[str, Any]]:
    where: dict[str, Any] = {"proposal_id": pid}
    if section_key:
        where["section_key"] = section_key
    shs = await repo.alist("sheets", where)
    if not include_excluded:
        shs = [s for s in shs if s.get("status") != "excluded" and not s.get("hidden")]
    return sorted(shs, key=lambda s: (s.get("sheet_no") or 9999, s.get("order") or 0))


async def section_doc(pid: str, key: str) -> dict[str, Any]:
    secs = await repo.alist("sections", {"proposal_id": pid, "key": key})
    if not secs:
        raise section_not_in_type(key)
    return secs[0]


async def sheet_doc(pid: str, sheet_id: str) -> dict[str, Any]:
    sh = await repo.aget("sheets", sheet_id)
    if sh is None or sh.get("proposal_id") != pid:
        raise sheet_not_found(sheet_id)
    return sh


def check_if_match(p: dict[str, Any], if_match: str | None) -> None:
    if if_match is None or if_match == "" or if_match == "*":
        return
    try:
        want = int(str(if_match).strip().strip('"').removeprefix("W/").strip('"'))
    except ValueError:
        return
    if want != int(p.get("rev") or 0):
        raise rev_conflict(int(p.get("rev") or 0))


async def touch(pid: str, *, user_edit: bool = False, fn: Any = None) -> dict[str, Any]:
    """제안서 rev +1(내용이 바뀐 모든 쓰기). user_edit 면 버전 이후 수정 수(edits_since_version)도 +1."""
    def _fn(p: dict[str, Any]) -> None:
        p["rev"] = int(p.get("rev") or 0) + 1
        if user_edit and int(p.get("saved_version") or 0) > 0:
            p["edits_since_version"] = int(p.get("edits_since_version") or 0) + 1
        if fn:
            fn(p)

    saved, _ = await repo.amutate("proposals", pid, _fn, err=proposal_not_found(pid))
    return saved


async def mutate(pid: str, fn: Any, *, bump: bool = True) -> dict[str, Any]:
    def _fn(p: dict[str, Any]) -> Any:
        res = fn(p)
        if bump:
            p["rev"] = int(p.get("rev") or 0) + 1
        return res

    saved, _ = await repo.amutate("proposals", pid, _fn, err=proposal_not_found(pid))
    return saved


STAGE_RANK = {s: i for i, s in enumerate(defs.STAGE_ORDER)}


def advance_stage(p: dict[str, Any], stage: str) -> None:
    """stage 는 앞으로만 움직인다(앞 단계 화면은 언제든 다시 열 수 있다)."""
    cur = p.get("stage") or "customer"
    if STAGE_RANK.get(stage, 0) > STAGE_RANK.get(cur, 0):
        p["stage"] = stage


def set_job(p: dict[str, Any], key: str, job_id: str | None) -> None:
    jobs = p.setdefault("jobs", {})
    if job_id:
        jobs[key] = job_id
    else:
        jobs.pop(key, None)


# ── 섹션 · 유형 ────────────────────────────────────────────
def type_sections(type_: str | None) -> list[str]:
    return list((defs.TYPES.get(type_ or "") or {}).get("sections") or [])


def is_optional(type_: str | None, key: str) -> bool:
    return key in ((defs.TYPES.get(type_ or "") or {}).get("optional") or [])


def section_no(type_: str | None, key: str) -> int:
    keys = type_sections(type_)
    return keys.index(key) + 1 if key in keys else 0


def section_status_label(sec: dict[str, Any]) -> str:
    if sec.get("status") == "filling":
        return "작성 중"
    if sec.get("confirmed"):
        return "확정"
    if sec.get("inferred"):
        return "추론 완료"
    return {"empty": "자료 필요", "ready": "초안 있음", "stale": "자료 바뀜"}.get(sec.get("status") or "empty", "")


# ── 라벨(§10.11) ───────────────────────────────────────────
def stage_no(p: dict[str, Any]) -> int:
    return defs.STAGE_NO.get(p.get("stage") or "customer", 1)


def steps(p: dict[str, Any]) -> tuple[int, int]:
    """(완료 칸 수, 현재 칸) — review · done 은 6칸 모두 채움 · 현재 0."""
    if p.get("status") in ("review", "done"):
        return 6, 0
    n = stage_no(p)
    if n == 6 and int(p.get("saved_version") or 0) > 0:
        return 5, 6
    return n - 1, n


def progress_label(p: dict[str, Any], *, open_confirm: int = 0, section_pos: tuple[int, int] | None = None) -> str:
    v = int(p.get("saved_version") or 0)
    status = p.get("status") or "draft"
    if status == "done":
        return f"PPTX v{v} · 제출 완료"
    if status == "review":
        rv = p.get("review") or {}
        a, m = int(rv.get("approvals") or 0), int(rv.get("reviewers_total") or 0)
        if a <= 0:
            return f"PPTX v{v} · 승인 대기"
        if a < m:
            return f"PPTX v{v} · 검토 요청 {a}/{m} 승인"
        return f"PPTX v{v} · 승인 완료"
    oc = p.get("one_click") or {}
    if oc.get("status") in ("running", "queued"):
        return f"딸깍 진행 중 · {int(oc.get('pct') or 0)}%"
    n = stage_no(p)
    if n == 1:
        return "고객 · 프로젝트 확인 중"
    if n == 2:
        return "제안서 유형 선택 중"
    if n == 3:
        return "시트 구성 중"
    if n == 4:
        cur, tot = section_pos or (1, len(type_sections(p.get("type"))) or 1)
        return f"섹션 작성 · {cur} / {tot} 섹션"
    if n == 5:
        return "디자인 템플릿 선택 중"
    if open_confirm > 0:
        return "PPTX 생성 · 사실 확인 중"
    if v > 0:
        return f"PPTX v{v} · 생성 완료"
    return "PPTX 생성 중"


def due_labels(p: dict[str, Any]) -> tuple[str, str, bool]:
    """(마감 「10.08」, 「D-7」, 강조) · 완료는 (「제출함」, 「2025.11.20」, False)."""
    if p.get("status") == "done":
        d = config.parse_date(p.get("submitted_at")) or config.parse_date((p.get("schedule") or {}).get("submit_due"))
        return "제출함", (d.strftime("%Y.%m.%d") if d else ""), False
    due = config.parse_date((p.get("schedule") or {}).get("submit_due"))
    if not due:
        return "", "", False
    n = (due - config.today_kst()).days
    label = f"{due.month:02d}.{due.day:02d}"
    if n >= 0:
        return label, f"D-{n}", n <= defs.DUE_URGENT_DAYS
    return label, f"D+{-n}", True


def initial(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""
    if name[0].isascii():
        parts = name.split()
        return "".join(x[0] for x in parts[:2]).upper()
    return name[-2:] if len(name) >= 3 else name[0]


def owner_of(p: dict[str, Any]) -> M.Owner:
    name = p.get("owner_name") or ""
    return M.Owner(user_id=p.get("owner_id") or "", name=name, initial=initial(name))


def industry_label(p: dict[str, Any]) -> str:
    c = p.get("customer") or {}
    code = c.get("industry_code")
    if c.get("industry_label"):
        return c["industry_label"]
    if code and code in defs.INDUSTRIES:
        return defs.INDUSTRIES[code]["name"]
    det = ((p.get("industry_layout") or {}).get("detected") or {})
    return det.get("label") or ""


def title_display(p: dict[str, Any]) -> str:
    return (p.get("title") or "").strip() or "새 제안서"


def type_label(t: str | None) -> str | None:
    return (defs.TYPES.get(t or "") or {}).get("label")


def type_name(t: str | None) -> str | None:
    return (defs.TYPES.get(t or "") or {}).get("name")


def sub_label(p: dict[str, Any], *, link_count: int) -> str:
    ind = industry_label(p)
    tail = ""
    v = int(p.get("saved_version") or 0)
    if p.get("status") == "done":
        d = config.parse_date(p.get("submitted_at"))
        tail = f"{d.strftime('%Y.%m.%d')} 제출" if d else "제출"
    elif (p.get("one_click") or {}).get("status") == "succeeded":
        tail = "딸깍으로 완성"
    elif p.get("status") == "review":
        tail = f"PPTX v{v}"
    elif p.get("start_mode") == "rfp" and stage_no(p) <= 1:
        tail = "RFP로 시작"
    elif link_count >= 1:
        tail = f"연결 작업 {link_count}"
    return " · ".join(x for x in (ind, tail) if x)


def row_action(p: dict[str, Any], *, me: str, open_confirm: int, my_pending: bool) -> M.ProposalAction:
    pid = p["id"]
    status = p.get("status") or "draft"
    if status == "review":
        if my_pending:
            return M.ProposalAction(label="검토 보기", route=route(pid, "review"))
        return M.ProposalAction(label="버전 보기", route=route(pid, "versions"))
    if status == "done":
        return M.ProposalAction(label="복제해서 시작", route=f"{defs.ROUTE_BASE}/new?reuse_from={pid}")
    if stage_no(p) == 6 and open_confirm > 0:
        return M.ProposalAction(label="확인할 곳", route=route(pid, "confirm"))
    return M.ProposalAction(label="이어서 작성", route=stage_route(p))


# ── 화면 모델 ──────────────────────────────────────────────
def tag_of(t: dict[str, Any]) -> str:
    code = t.get("code")
    if not code:
        return "템플릿 고르는 중"
    if t.get("mode") == "pinned":
        return f"{code} · 직접"
    return f"자동 · {code}"


def thumb_url(code: str | None) -> str | None:
    return f"/api/export/v1/templates/{code}/thumbnail.png" if code else None


def sheet_status_label(sh: dict[str, Any]) -> str:
    st = sh.get("status") or "need"
    if st == "need":
        return "자료 필요"
    if st == "filling":
        return "작성 중"
    if st == "updated":
        return "업데이트됨"
    if st == "excluded":
        return "빠짐"
    return role_name(sh.get("role"))


def role_name(code: str | None) -> str:
    return (defs.ROLES.get(code or "") or {}).get("name", code or "")


def sheet_thumb(sh: dict[str, Any]) -> str | None:
    r = sh.get("render") or {}
    if r.get("png_file_id") and r.get("rev") == sh.get("content_rev"):
        return f"/api/files/v1/files/{r['png_file_id']}/content"
    if r.get("png_file_id"):
        return f"/api/files/v1/files/{r['png_file_id']}/content"
    return thumb_url((sh.get("template") or {}).get("code"))


def section_summaries(p: dict[str, Any], secs: list[dict[str, Any]], sheets: list[dict[str, Any]]) -> list[M.SectionSummary]:
    out = []
    keys = type_sections(p.get("type"))
    for s in secs:
        if s["key"] not in keys:
            continue
        n = sum(1 for sh in sheets if sh["section_key"] == s["key"])
        out.append(M.SectionSummary(
            id=s["id"], key=s["key"], name=defs.SECTIONS[s["key"]]["name"], short=defs.SECTIONS[s["key"]]["short"],
            no=keys.index(s["key"]) + 1, optional=bool(s.get("optional")), enabled=bool(s.get("enabled", True)),
            hidden=bool(s.get("hidden")), status=s.get("status") or "empty", status_label=section_status_label(s),
            confirmed=bool(s.get("confirmed")), inferred=bool(s.get("inferred")), sheet_count=n if s.get("enabled", True) else 0,
            route=section_route(p["id"], s["key"])))
    return sorted(out, key=lambda x: x.no)


def sheet_summaries(sheets: list[dict[str, Any]], open_by_sheet: dict[str, int]) -> list[M.SheetSummary]:
    out = []
    for sh in sheets:
        t = sh.get("template") or {}
        out.append(M.SheetSummary(
            id=sh["id"], section_key=sh["section_key"], sheet_no=int(sh.get("sheet_no") or 0), title=sh.get("title") or "",
            role=sh.get("role") or "", role_name=role_name(sh.get("role")), template_code=t.get("code"),
            template_mode=t.get("mode") or "auto", tag=tag_of(t), status=sh.get("status") or "need",
            status_label=sheet_status_label(sh), inferred=bool(sh.get("inferred")),
            edited_since_version=bool(sh.get("edited_since_version")), open_confirm=open_by_sheet.get(sh["id"], 0),
            thumb_url=sheet_thumb(sh)))
    return out


def slides_total(p: dict[str, Any], n_sheets: int, n_sections: int) -> int:
    d = p.get("design") or {}
    total = 2 + n_sheets  # 표지 + 목차
    if d.get("section_dividers", True):
        total += n_sections
    return total


def stepper(p: dict[str, Any]) -> M.Stepper:
    n = stage_no(p)
    oc = p.get("one_click") or {}
    running = oc.get("status") in ("running", "queued")
    complete = p.get("status") in ("review", "done") or (oc.get("status") == "succeeded" and n == 6)
    auto_from = int(oc.get("auto_from_step") or 0) if oc.get("status") in ("running", "queued", "succeeded") else 0
    cur = 6 if running else n
    done_steps = list(range(1, cur))
    return M.Stepper(steps=list(defs.STEP_NAMES), current=cur, complete=bool(complete or (n == 6 and auto_from)),
                     one_click=(cur <= 5 and not running and not complete), auto_from=auto_from, done_steps=done_steps)


async def open_confirm_by_sheet(pid: str) -> dict[str, int]:
    items = await repo.alist("confirm_items", {"proposal_id": pid})
    out: dict[str, int] = {}
    for it in items:
        if it.get("status") == "open" and it.get("sheet_id"):
            out[it["sheet_id"]] = out.get(it["sheet_id"], 0) + 1
    return out


async def open_confirm_count(pid: str) -> int:
    items = await repo.alist("confirm_items", {"proposal_id": pid})
    return sum(1 for it in items if it.get("status") == "open")


async def link_count(pid: str) -> int:
    links = await repo.alist("links", {"proposal_id": pid})
    return sum(1 for ln in links if ln.get("status", "linked") == "linked" and ln.get("feature") in defs.WORK_FEATURES)


async def proposal_view(p: dict[str, Any] | str) -> M.Proposal:
    if isinstance(p, str):
        p = await load(p)
    pid = p["id"]
    secs = await sections_of(pid)
    keys = type_sections(p.get("type"))
    enabled_secs = [s for s in secs if s["key"] in keys and s.get("enabled", True)]
    sheets = [sh for sh in await sheets_of(pid) if sh["section_key"] in {s["key"] for s in enabled_secs}]
    by_sheet = await open_confirm_by_sheet(pid)
    open_n = await open_confirm_count(pid)
    n_links = await link_count(pid)
    cur_key = p.get("current_section_key")
    pos = (keys.index(cur_key) + 1, len(keys)) if cur_key in keys else (1, len(keys) or 1)
    sd, _cur = steps(p)
    cust = {**M.Customer().model_dump(), **(p.get("customer") or {})}
    if not cust.get("industry_label") and cust.get("industry_code") in defs.INDUSTRIES:
        cust["industry_label"] = defs.INDUSTRIES[cust["industry_code"]]["name"]
    oc = p.get("one_click") or {}
    rv = p.get("review") or None
    return M.Proposal(
        id=pid, project_id=p.get("project_id"), owner=owner_of(p), title=p.get("title") or "", title_display=title_display(p),
        customer=M.Customer(**cust), schedule=M.Schedule(**(p.get("schedule") or {})), budget_text=p.get("budget_text"),
        language=p.get("language") or "ko", rq_ref=M.RqRef(**p["rq_ref"]) if p.get("rq_ref") else None,
        start_mode=p.get("start_mode") or "blank", start_files=list(p.get("start_files") or []), type=p.get("type"),
        type_label=type_label(p.get("type")), type_name=type_name(p.get("type")), type_source=p.get("type_source"),
        stage=p.get("stage") or "customer", stage_no=stage_no(p), current_section_key=cur_key,
        industry_layout=M.IndustryLayout(**{**default_industry_layout(), **(p.get("industry_layout") or {})}),
        design=M.Design(**{**default_design(), **(p.get("design") or {})}), status=p.get("status") or "draft",
        status_label=defs.STATUS_LABEL.get(p.get("status") or "draft", ""), submitted_at=p.get("submitted_at"),
        version=int(p.get("saved_version") or 0), rev=int(p.get("rev") or 0), edits_since_version=int(p.get("edits_since_version") or 0),
        files=M.Files(**(p.get("files") or {})), derived_from=M.DerivedFrom(**p["derived_from"]) if p.get("derived_from") else None,
        reuse=M.ReuseRef(**{k: v for k, v in (p.get("reuse") or {}).items() if k in ("reuse_id", "mode")}) if (p.get("reuse") or {}).get("reuse_id") else None,
        one_click=M.OneClickBrief(job_id=oc["job_id"], status=oc.get("status") or "running", pct=int(oc.get("pct") or 0),
                                  auto_from_step=int(oc.get("auto_from_step") or 4), route=route(pid, "one-click", oc["job_id"]))
        if oc.get("job_id") else None,
        review=M.ReviewBrief(**{k: v for k, v in rv.items() if k in M.ReviewBrief.model_fields}) if rv and rv.get("review_id") else None,
        progress_label=progress_label(p, open_confirm=open_n, section_pos=pos), steps_done=sd, route=stage_route(p),
        stepper=stepper(p), sections=section_summaries(p, secs, sheets), sheets=sheet_summaries(sheets, by_sheet),
        sheet_total=len(sheets), slides_total=slides_total(p, len(sheets), len(enabled_secs)), open_confirm_count=open_n,
        link_count=n_links, created_at=p.get("created_iso") or p.get("created_at") or "", updated_at=p.get("touched_at") or p.get("updated_at") or "",
    )


# ── workspace 색인(§5.17) ──────────────────────────────────
def ws_status(p: dict[str, Any]) -> str:
    oc = p.get("one_click") or {}
    if oc.get("status") in ("running", "queued"):
        return "generating"
    return p.get("status") or "draft"


async def index(pid: str, *, force: bool = False) -> None:
    """만들 때 · 단계 이동 · 상태 변경 · 확인 항목 수 변경 · 버전 생성 때. 같은 내용이면 건너뛴다."""
    p = await repo.aget("proposals", pid)
    if p is None:
        return
    open_n = await open_confirm_count(pid)
    n_links = await link_count(pid)
    keys = type_sections(p.get("type"))
    cur_key = p.get("current_section_key")
    pos = (keys.index(cur_key) + 1, len(keys)) if cur_key in keys else (1, len(keys) or 1)
    badges = []
    cc = (p.get("comment_counts") or {}).get("open") or 0
    if cc:
        badges.append({"kind": "comments", "n": cc})
    if open_n:
        badges.append({"kind": "confirm_needed", "n": open_n})
    body = {
        "feature": defs.FEATURE, "item_id": pid, "title": title_display(p), "status": ws_status(p), "route": stage_route(p),
        "summary": progress_label(p, open_confirm=open_n, section_pos=pos), "project_id": p.get("project_id"),
        "meta": {"customer": (p.get("customer") or {}).get("name") or "", "type": p.get("type"), "proposal_type": p.get("type"),
                 "type_label": type_label(p.get("type")), "due_date": (p.get("schedule") or {}).get("submit_due"),
                 "badges": badges, "version": int(p.get("saved_version") or 0), "stage": p.get("stage"),
                 "industry_code": (p.get("customer") or {}).get("industry_code"), "links": n_links},
    }
    h = hashlib.sha1(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if not force and p.get("ws_hash") == h:
        return
    await register_item(feature=defs.FEATURE, item_id=pid, title=body["title"], status=body["status"], route=body["route"],
                        summary=body["summary"], project_id=body["project_id"], meta=body["meta"])
    try:
        await repo.amutate("proposals", pid, lambda x: x.update({"ws_hash": h}))
    except Exception:  # noqa: BLE001
        pass


# ── 변경 기록(§5.10) ───────────────────────────────────────
def actor() -> dict[str, Any]:
    u = current_user()
    return {"user_id": u.id, "name": u.name}


async def record_change(pid: str, *, sheet: dict[str, Any] | None, where: str, kind: str, path: str = "", from_: Any = None,
                        to: Any = None, summary: str = "", reason: str | None = None, by_w: bool = False,
                        job_id: str | None = None, import_id: str | None = None, comment_id: str | None = None,
                        bbox: dict[str, float] | None = None, extra: dict[str, Any] | None = None) -> str:
    p = await repo.aget("proposals", pid) or {}
    now = config.now()
    cid = new_id("chg")
    sheet_no = int((sheet or {}).get("sheet_no") or 0)
    doc = {
        "id": cid, "proposal_id": pid, "ts": config.now_iso(), "actor": "W" if by_w else actor(),
        "sheet_id": (sheet or {}).get("id"), "sheet_no": sheet_no, "where": where, "kind": kind, "path": path,
        "from": from_, "to": to, "summary": summary or (f"{sheet_no:02d} {where}" if sheet_no else where), "reason": reason,
        "comment_id": comment_id, "job_id": job_id, "import_id": import_id,
        "after_version": int(p.get("saved_version") or 0), "bbox": bbox, "reverted_by": None,
        "expires_at": (now + timedelta(days=defs.CHANGE_TTL_DAYS)).isoformat(), **(extra or {}),
    }
    await repo.aput("changes", cid, doc)
    return cid


def snippet(value: Any, n: int = 40) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        s = value
    elif isinstance(value, dict):
        s = value.get("text") or value.get("title") or value.get("label") or json.dumps(value, ensure_ascii=False)
    else:
        s = json.dumps(value, ensure_ascii=False)
    s = str(s).replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"
