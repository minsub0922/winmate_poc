"""가치 제안 문서 — 만들기 · 파생 값(상태 · 칩 · 경로 · 커버리지) · 응답 모양 · 작업물 색인 · 저장 지점 · 잡 넣기.

REST 와 워커가 함께 쓴다. 쓰기는 `mutate(vp_id, fn)`(낙관적 잠금 → 파생 값 → 색인)로만 한다.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import TERMINAL, jobs
from winmate_common.platform import register_item

from . import catalog, decide, numbers, repo, signals, views
from .planner import plan_of

log = logging.getLogger("winmate.vp")
KST = ZoneInfo("Asia/Seoul")

JOB_TITLES = {"vp.materials": "재료 정리", "vp.generate": "가치 제안 만들기", "vp.revise": "가치 제안 다듬기",
              "vp.images": "이미지 칸 채우기", "vp.export": "가치 제안 내보내기", "vp.pack_offer": "업종판 교체 제안"}
GRAPH_OF = {"vp.materials": "vp_materials", "vp.generate": "vp_generate", "vp.revise": "vp_revise", "vp.images": "vp_images",
            "vp.export": "vp_export", "vp.pack_offer": "vp_pack_offer"}
ACTIVE_KINDS = {"vp.materials", "vp.generate", "vp.revise", "vp.images"}
ASK_TEXT = {"direction": "방향 선택", "industry": "업종 선택", "approver": "결재자 확인", "sb_mi_conflict": "방향 선택",
            "investment": "투자비 확인", "interview_numbers": "수치 확인"}


# ── 만들기 ─────────────────────────────────────────────────

def owner_now() -> dict[str, str]:
    u = current_user()
    return {"user_id": u.id, "name": u.name}


def default_title(customer: str | None, topic: str | None = None) -> str:
    c = (customer or "").strip()
    if not c:
        return "새 가치 제안"
    return f"{c} {topic} 가치 제안" if topic else f"{c} 가치 제안"


def new_doc(vp_id: str, *, start: str, owner: dict[str, str], customer_name: str | None = None, title: str | None = None,
            project_id: str | None = None, target: dict[str, Any] | None = None, auto_answer: bool = False,
            note: str | None = None) -> dict[str, Any]:
    return {
        "id": vp_id, "title": title or default_title(customer_name), "title_auto": not title, "customer_name": customer_name,
        "project_id": project_id, "owner": owner, "owner_id": owner["user_id"], "start": start, "status": "draft",
        "step": 1, "note": note or "", "auto_answer": auto_answer, "archived": False, "industry": None,
        "target_proposal": target, "sources": [], "attachments": [], "materials": [], "fixes": [], "questions": [],
        "decisions": [], "plan": None, "plan_overrides": {}, "sheets": [], "variants": [], "image_slots": [], "checks": [],
        "layout_requests": [], "pack_offers": [], "facts": {}, "active_job": None, "last_job": None, "last_error": None,
        "doc_version": 0, "materials_ready": False, "generated": False, "handoffs": [], "linked_proposal": None,
        "inherited_pins": {}, "last_action": "create",
    }


# ── 파생 값(§3.6) ──────────────────────────────────────────

def open_questions(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return [q for q in doc.get("questions") or [] if q.get("status") == "open"]


def metric_asks(doc: dict[str, Any]) -> list[dict[str, Any]]:
    if not doc.get("generated"):
        return []
    return [m for m in signals.ef_metrics(doc) if numbers.metric_status(m) == "ask"]


def ef_sheet(doc: dict[str, Any]) -> dict[str, Any] | None:
    return next((s for s in doc.get("sheets") or [] if s.get("role") == "EF" and s.get("kind", "main") == "main"), None)


def estimate_count(doc: dict[str, Any]) -> int:
    n = 0
    for s in doc.get("sheets") or []:
        for m in (s.get("content") or {}).get("metrics") or []:
            if numbers.metric_status(m) == "estimated":
                n += 1
        for c in (s.get("content") or {}).get("challenges") or []:
            if ((c.get("impact") or {}).get("status")) == "estimated":
                n += 1
    return n


def effective_status(doc: dict[str, Any]) -> str:
    aj = doc.get("active_job") or {}
    if aj and aj.get("status") not in TERMINAL:
        if aj.get("status") == "awaiting_input":
            return "ask"
        return "collecting" if aj.get("kind") == "vp.materials" else "generating"
    if open_questions(doc):
        return "ask"
    if doc.get("generated"):
        if metric_asks(doc):
            return "ask"
        if [r for r in doc.get("layout_requests") or [] if r.get("status") == "open"] or \
                [o for o in doc.get("pack_offers") or [] if o.get("status") == "open"] or doc.get("pending_confirmations"):
            return "check"
        if doc.get("status") in ("stopped", "failed"):
            return doc["status"]
        return "done"
    if doc.get("status") in ("stopped", "failed"):
        return doc["status"]
    if doc.get("plan"):
        return "planned"
    return "draft"


def derive(doc: dict[str, Any]) -> dict[str, Any]:
    """저장 직전마다 파생 값을 다시 계산한다."""
    st = effective_status(doc)
    vid = doc["id"]
    aj = doc.get("active_job") or {}
    oq = open_questions(doc)
    lrs = [r for r in doc.get("layout_requests") or [] if r.get("status") == "open"]
    pos = [o for o in doc.get("pack_offers") or [] if o.get("status") == "open"]
    ma = metric_asks(doc)
    ef = ef_sheet(doc)
    ui, text, action = "draft", "", "이어서"
    if st in ("collecting", "generating"):
        ui, text, action = "run", f"생성 중 {int(aj.get('progress') or 0)}%", "진행 보기"
        route = f"/vp/{vid}/generating?job={aj.get('job_id')}" if st == "generating" else f"/vp/{vid}/materials"
        step = 3 if st == "generating" else 1
    elif st == "ask":
        ui, action = "ask", "답하기"
        if oq:
            text = f"{ASK_TEXT.get(oq[0].get('kind', ''), '선택')} {len(oq)}"
            route, step = f"/vp/{vid}/questions", 2
        elif ma:
            text = f"수치 선택 {len(ma)}"
            route, step = f"/vp/{vid}/result/numbers?sheet={ef['id'] if ef else ''}", 3
        else:
            text, route, step = "답하기", f"/vp/{vid}/questions", 2
    elif st == "check":
        ui, action = "check", "확인"
        if lrs:
            text = f"레이아웃 요청 {len(lrs)}"
            route = f"/vp/{vid}/result/layout?sheet={lrs[0]['sheet_id']}&req={lrs[0]['id']}"
        elif pos:
            text, route = f"업종판 교체 {len(pos)}", f"/vp/{vid}/result"
        else:
            text, route = f"제안서 확인 {int(doc.get('pending_confirmations') or 0)}", f"/vp/{vid}/result"
        step = 3
    elif st == "done":
        ui, action = "done", "열기"
        n = estimate_count(doc)
        text = f"완료 · 추정 {n}" if n else "완료"
        route, step = f"/vp/{vid}/result", 3
    elif st == "failed":
        ui, action = "draft", "다시 시도"
        text = "만들기를 마치지 못했어요"
        lj = doc.get("last_job") or {}
        route = f"/vp/{vid}/generating?job={lj.get('job_id')}" if lj.get("kind") == "vp.generate" else f"/vp/{vid}/structure"
        step = 3 if lj.get("kind") == "vp.generate" else 2
    else:
        if doc.get("plan") or st == "stopped":
            step, route = 2, f"/vp/{vid}/structure"
        elif doc.get("materials_ready"):
            step = 1
            route = f"/vp/{vid}/materials/review" if doc.get("fixes") else f"/vp/{vid}/structure"
        else:
            step, route = 1, f"/vp/{vid}/materials"
        text = f"작성 중 {step}/3"
    doc["status_effective"] = st
    doc["ui_status"] = ui
    doc["status_text"] = text
    doc["action_label"] = action
    doc["step"] = step
    doc["resume_route"] = route
    doc["coverage"] = signals.coverage_of(doc)
    if doc.get("industry"):
        doc["industry"]["caption"] = decide.industry_caption(doc["industry"])
    if doc.get("title_auto", True) and doc.get("customer_name") and doc.get("title") in (None, "", "새 가치 제안"):
        doc["title"] = default_title(doc.get("customer_name"), (doc.get("facts") or {}).get("topic"))
    views.compute(doc)
    return doc


def layout_chips(doc: dict[str, Any]) -> list[dict[str, str]]:
    """VP0 레이아웃 칩(시트 순서 · 고정은 `{코드} 고정` · 코드 아닌 말은 회색 글자)."""
    if open_questions(doc) and not doc.get("generated"):
        return [{"t": "구조 정하기 전", "kind": "text"}]
    if doc.get("generated") and doc.get("sheets"):
        out = []
        omitted = (doc.get("plan") or {}).get("omitted") or []
        if any(o.get("role") == "CH" for o in omitted) and (doc.get("target_proposal") or {}).get("type") == "solution":
            out.append({"t": "고객 과제 생략", "kind": "text"})
        for s in sorted([s for s in doc["sheets"] if s.get("kind", "main") == "main"], key=lambda s: s.get("order", 0)):
            code = s["layout"]["code"]
            if s.get("pinned"):
                out.append({"t": f"{catalog.display(code)} 고정", "kind": "pinned"})
            else:
                out.append({"t": catalog.display(code), "kind": "pack" if catalog.is_pack(code) else "code"})
        return out
    plan = doc.get("plan")
    if plan and plan.get("chips"):
        return plan["chips"]
    return [{"t": "구조 정하기 전", "kind": "text"}]


def when_label(doc: dict[str, Any], now: datetime | None = None) -> str:
    """`방금 시작` · `오늘 HH:MM` · `어제`(마지막 동작이 저장이면 `어제 저장`) · `M월 D일`(제안)."""
    now = now or datetime.now(timezone.utc)
    try:
        t = datetime.fromisoformat(str(doc.get("updated_at")).replace("Z", "+00:00"))
    except ValueError:
        return ""
    aj = doc.get("active_job") or {}
    if aj and aj.get("status") not in TERMINAL and aj.get("started_at"):
        try:
            st = datetime.fromisoformat(str(aj["started_at"]).replace("Z", "+00:00"))
            if now - st < timedelta(minutes=1):
                return "방금 시작"
        except ValueError:
            pass
    lt, ln = t.astimezone(KST), now.astimezone(KST)
    if lt.date() == ln.date():
        return f"오늘 {lt:%H:%M}"
    if lt.date() == (ln - timedelta(days=1)).date():
        return "어제 저장" if doc.get("last_action") == "save" else "어제"
    return f"{lt.month}월 {lt.day}일"


def linked_proposal(doc: dict[str, Any]) -> dict[str, Any] | None:
    if doc.get("linked_proposal"):
        return doc["linked_proposal"]
    tp = doc.get("target_proposal") or {}
    if tp.get("title"):
        return {"id": tp.get("proposal_id"), "title": tp["title"]}
    return None


def list_item(doc: dict[str, Any]) -> dict[str, Any]:
    ind = doc.get("industry") or None
    return {
        "id": doc["id"], "title": doc.get("title") or "새 가치 제안", "owner_name": (doc.get("owner") or {}).get("name") or "",
        "updated_at": doc.get("updated_at") or "", "when_label": when_label(doc),
        "industry": {"code": ind["code"], "name": ind["name"]} if ind else None,
        "layout_chips": layout_chips(doc), "ui_status": doc.get("ui_status") or "draft", "status_text": doc.get("status_text") or "",
        "linked_proposal": linked_proposal(doc), "action_label": doc.get("action_label") or "이어서",
        "resume_route": doc.get("resume_route") or f"/vp/{doc['id']}",
    }


def to_api(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out["version"] = int(doc.get("doc_version") or 0)
    out["status"] = doc.get("status_effective") or doc.get("status") or "draft"
    out["linked_proposal"] = linked_proposal(doc)
    owner = doc.get("owner") or {}
    out["owner"] = {"user_id": owner.get("user_id") or doc.get("owner_id") or "system", "name": owner.get("name") or ""}
    return out


# ── 쓰기 + 색인 ────────────────────────────────────────────

_ws_sig: dict[str, str] = {}


def _sig(obj: Any) -> str:
    return hashlib.sha1(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


async def index(doc: dict[str, Any]) -> None:
    """workspace 작업물 색인 — `{feature:'VP', title, status: ui_status, summary: status_text, route: resume_route, project_id}`."""
    if doc.get("archived"):
        return
    body = (doc.get("title") or "새 가치 제안", doc.get("ui_status") or "draft", doc.get("resume_route") or f"/vp/{doc['id']}",
            doc.get("status_text") or "", doc.get("project_id"))
    meta = {"customer_name": doc.get("customer_name"), "industry": (doc.get("industry") or {}).get("code"),
            "layouts": [c["t"] for c in layout_chips(doc)], "version": int(doc.get("doc_version") or 0)}
    sig = _sig([body, meta])
    if _ws_sig.get(doc["id"]) == sig:
        return
    await register_item(feature="VP", item_id=doc["id"], title=body[0][:200], status=body[1], route=body[2], summary=body[3],
                        project_id=body[4], meta=meta)
    _ws_sig[doc["id"]] = sig


async def mutate(vp_id: str, fn: Callable[[dict[str, Any]], dict[str, Any] | None], *, touch: str | None = None) -> dict[str, Any]:
    def wrapped(doc: dict[str, Any]) -> dict[str, Any] | None:
        res = fn(doc)
        if res is None:
            return None
        if touch:
            res["last_action"] = touch
        return derive(res)

    doc = await repo.update(vp_id, wrapped)
    await index(doc)
    return doc


async def load(vp_id: str) -> dict[str, Any]:
    """읽기 — 끝난 잡의 active_job 을 치우고(중지 · 실패 반영) 파생 값을 다시 계산한다."""
    doc = await repo.require_vp(vp_id)
    aj = doc.get("active_job")
    if aj:
        rec = await jobs().get(aj["job_id"])
        if rec is None or rec.status in TERMINAL or rec.status != aj.get("status") or rec.progress != aj.get("progress"):
            status = rec.status if rec else "failed"
            progress = rec.progress if rec else 0

            def sync(d: dict[str, Any]) -> dict[str, Any] | None:
                cur = d.get("active_job") or {}
                if cur.get("job_id") != aj["job_id"]:
                    return None
                if status in TERMINAL:
                    finish_job_state(d, aj["job_id"], status, (rec.error if rec else None))
                else:
                    cur["status"] = status
                    cur["progress"] = progress
                return d
            doc = await mutate(vp_id, sync)
    return derive(doc)


def finish_job_state(d: dict[str, Any], job_id: str, status: str, error: dict[str, Any] | None = None) -> None:
    cur = d.get("active_job") or {}
    if cur.get("job_id") != job_id:
        return
    kind = cur.get("kind")
    d["last_job"] = {**cur, "status": status}
    d["active_job"] = None
    if status == "canceled" and kind == "vp.generate":
        d["status"] = "stopped"
        for s in d.get("sheets") or []:
            if s.get("status") == "writing":
                s["status"] = "waiting"
    elif status == "failed":
        d["last_error"] = {"code": (error or {}).get("code"), "message": (error or {}).get("message") or "만들기를 마치지 못했어요",
                           "kind": kind, "job_id": job_id}
        if kind == "vp.generate":
            d["status"] = "failed"
            for s in d.get("sheets") or []:
                if s.get("status") == "writing":
                    s["status"] = "waiting"


# ── 플랜 ──────────────────────────────────────────────────

def replan(doc: dict[str, Any], pack_status: dict[str, str] | None = None) -> dict[str, Any]:
    """플랜 다시 계산(결정적) — 질문 답 · 대안 · 고정 · 업종 · 재료가 바뀔 때."""
    p = signals.planner_input(doc, pack_status=pack_status)
    plan = plan_of(p)
    for ps in plan["sheets"]:
        ps["content_preview"] = content_preview(doc, ps["role"], ps["layout"]["code"])
    plan["decisions_log"] = plan.pop("decisions")
    plan["decisions"] = signals.decision_rows(doc, plan, p)
    plan["intro"] = signals.plan_intro(doc, plan)
    plan["overrides"] = dict(doc.get("plan_overrides") or {})
    doc["plan"] = plan
    return plan


def content_preview(doc: dict[str, Any], role: str, code: str) -> str:
    """VP2 척추 `들어갈 내용` — 재료 문장(짧게) · 지표 이름."""
    from .writer import Ctx, short_phrase
    act = [m for m in doc.get("materials") or [] if not m.get("excluded")]
    if role == "CH":
        chs = Ctx._order_ch([m for m in act if m.get("axis") == "challenge"])[:3]
        return " / ".join(short_phrase(m["text"], 14) for m in chs)
    if role == "EF":
        ms = [m["label"] for m in ((doc.get("facts") or {}).get("metrics") or [])][:4]
        return " · ".join(ms) or "수치 없음 → 업종 평균 범위"
    c = catalog.norm(code)
    if c in ("VP-H", "VP-D"):
        sk = [m["text"].split(" · ")[0] for m in act if m.get("axis") == "stakeholder"][:4]
        return " · ".join(sk)
    if c in ("VP-E", "VP-A", "VP-U"):
        chs = Ctx._order_ch([m for m in act if m.get("axis") == "challenge"])[:3]
        return " / ".join(short_phrase(m["text"], 12) for m in chs)
    n = catalog.pillars_of(c) or (1 if c in ("VP-G", "VP-C") else 3)
    vals = [m for m in act if m.get("axis") == "value"][:n]
    return " · ".join(short_phrase(m["text"], 16) for m in vals) or "가치 재료 없음 → 만들 때 삼성 메시지 DB에서 채워요"


def stamp_decision(stage: int, text: str, mode: str = "auto", *, key: str = "", value: str = "", why: str = "",
                   job_id: str | None = None, at: datetime | None = None) -> dict[str, Any]:
    t = (at or datetime.now(timezone.utc)).astimezone(KST)
    return {"id": new_id("vdc"), "t": f"{t:%H:%M:%S}", "stage": stage, "key": key, "value": value, "why": why, "mode": mode,
            "text": text, "job_id": job_id}


# ── 저장 지점(§9.13-70) ─────────────────────────────────────

SNAPSHOT_KEYS = ("title", "customer_name", "industry", "target_proposal", "note", "sources", "attachments", "materials", "fixes",
                 "questions", "decisions", "plan", "plan_overrides", "sheets", "variants", "image_slots", "checks",
                 "layout_requests", "pack_offers", "facts", "generated", "materials_ready", "status", "inherited_pins")


def snapshot_of(doc: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy({k: doc.get(k) for k in SNAPSHOT_KEYS})


async def save_point(vp_id: str, reason: str) -> dict[str, Any]:
    """version +1 · 그 시점 문서를 vp_versions 에 남긴다."""
    holder: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["doc_version"] = int(d.get("doc_version") or 0) + 1
        holder["n"] = d["doc_version"]
        holder["snap"] = snapshot_of(d)
        d.setdefault("version_log", []).append({"version": d["doc_version"], "reason": reason, "created_at": now_iso()})
        return d
    doc = await mutate(vp_id, fn, touch="save")
    await repo.put_version(vp_id, holder["n"], holder["snap"], reason)
    return doc


async def restore(vp_id: str, n: int) -> dict[str, Any]:
    ver = await repo.get_version(vp_id, n)
    if ver is None:
        raise ApiError(404, "NOT_FOUND", f"버전 {n}이(가) 없어요", {"version": n})
    snap = ver.get("doc") or {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if (d.get("active_job") or {}).get("status") not in (None, *TERMINAL):
            raise ApiError(409, "JOB_RUNNING", "진행 중인 작업이 끝난 뒤 되돌릴 수 있어요.")
        for k in SNAPSHOT_KEYS:
            if k in snap:
                d[k] = copy.deepcopy(snap[k])
        return d
    await mutate(vp_id, fn)
    return await save_point(vp_id, f"v{n} 복원")


# ── 잡 ────────────────────────────────────────────────────

async def enqueue(vp_id: str, kind: str, payload: dict[str, Any] | None = None, *, doc: dict[str, Any] | None = None,
                  active: bool | None = None) -> str:
    """잡을 넣는다. active 면 먼저 `active_job` 을 건다(잡이 바로 끝나도 어긋나지 않게)."""
    job_id = new_id("job")
    is_active = kind in ACTIVE_KINDS if active is None else active
    if is_active:
        def mark(d: dict[str, Any]) -> dict[str, Any]:
            cur = d.get("active_job") or {}
            if cur and cur.get("status") not in TERMINAL and cur.get("job_id") != job_id:
                raise ApiError(409, "JOB_RUNNING", "이미 진행 중인 작업이 있어요. 끝난 뒤 다시 시도해 주세요.",
                               {"job_id": cur.get("job_id"), "kind": cur.get("kind")})
            d["active_job"] = {"job_id": job_id, "graph": GRAPH_OF.get(kind, kind), "kind": kind, "status": "queued", "progress": 0,
                               "started_at": now_iso()}
            if kind == "vp.generate":
                d["status"] = "generating"
            elif kind == "vp.materials":
                d["status"] = "collecting"
            return d
        doc = await mutate(vp_id, mark)
    title = JOB_TITLES.get(kind, kind)
    if doc is not None and doc.get("title"):
        title = f"{title} · {doc['title']}"
    await jobs().enqueue("vp", kind, {"vp_id": vp_id, **(payload or {})}, title=title, ref=vp_id,
                         project_id=(doc or {}).get("project_id"), job_id=job_id)
    return job_id


async def set_job_progress(vp_id: str, job_id: str, progress: int, status: str = "running") -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        cur = d.get("active_job") or {}
        if cur.get("job_id") != job_id:
            return None
        if cur.get("progress") == progress and cur.get("status") == status:
            return None
        cur["progress"] = progress
        cur["status"] = status
        return d
    try:
        await mutate(vp_id, fn)
    except ApiError:
        pass


async def finish_job(vp_id: str, job_id: str, status: str = "succeeded", error: dict[str, Any] | None = None) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        if (d.get("active_job") or {}).get("job_id") != job_id:
            return None
        finish_job_state(d, job_id, status, error)
        return d
    try:
        await mutate(vp_id, fn)
    except ApiError:
        pass
