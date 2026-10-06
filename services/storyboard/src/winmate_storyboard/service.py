"""스토리보드 문서 — 만들기 · 파생 값 · 응답 모양 · 작업물 색인 · 잡 넣기(REST 와 워커가 함께 쓴다)."""
from __future__ import annotations

import copy
import logging
from collections.abc import Callable
from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import TERMINAL, jobs
from winmate_common.platform import register_item

from . import repo, rules

log = logging.getLogger("winmate.storyboard")

# 사람에게 보이는 잡 제목
JOB_TITLES = {
    "sb.prepare": "정의서에서 설정 · 기획 질의 고르기", "sb.direction": "기획 방향 만들기", "sb.messages": "핵심 메시지 다시 쓰기",
    "sb.outline": "목차 · 서사 쓰기", "sb.space.questions": "공간 질문 만들기", "sb.space.compose": "공간 시나리오 다듬기",
    "sb.revise": "수정 요청 다시 쓰기", "sb.rq_sync": "정의서 새 버전 반영", "sb.trace.apply": "요구 정리 반영",
    "sb.trace.refresh": "요구 추적 다시 계산", "sb.export": "스토리보드 내보내기",
}
ACTIVE_KINDS = {"sb.prepare", "sb.direction", "sb.messages", "sb.outline", "sb.rq_sync"}
DRAFT_TTL_DAYS = 7


# ── 만들기 ─────────────────────────────────────────────────

def strip_customer(name: str, customer: str | None) -> str:
    """제목은 `{고객사} {이름}` — 이름이 고객사로 시작하면 고객사를 뺀 나머지를 이름으로."""
    if customer and name.startswith(customer):
        return name[len(customer):].strip() or name
    return name


def new_doc(sb_id: str, *, owner: dict[str, str], rq_ref: dict[str, Any] | None) -> dict[str, Any]:
    title = strip_customer((rq_ref or {}).get("title") or "새 스토리보드", (rq_ref or {}).get("customer_name"))
    return {
        "id": sb_id, "owner": owner, "owner_id": owner["id"], "project_id": (rq_ref or {}).get("project_id"),
        "name": title, "customer_name": (rq_ref or {}).get("customer_name"), "title": title,
        "started": False, "status": "in_progress", "step": 1, "route": f"/storyboard/{sb_id}/source", "sub_line": "",
        "requirement_ref": rq_ref, "requirement_id": (rq_ref or {}).get("requirement_id"),
        "settings": rules.finalize_settings({
            "stage": {"value": "concept", "source": "default", "evidence": None},
            "doc_type": {"value": "custom", "source": "default", "evidence": None},
            "volume": {"value": 20, "source": "default", "evidence": None},
            "language": {"value": "ko", "source": "default", "evidence": None},
            "ready": False,
        }),
        "planning": {"questions": [], "answers": []},
        "direction": None, "outline": None, "trace": None,
        "schedule": {"phases": [], "open_question_count": 0, "start_d": 21},
        "schedule_ids": [new_id("phs") for _ in range(6)],
        "saved_version": 0, "saved_hash": None, "revision": 0, "changes": [], "handoffs": [],
        "active_job": None, "prepare_job_id": None, "rq_update": None, "review_requested": False, "exported": False,
        "owners": None, "group_summaries": None, "internal_phrases": [], "item_classes": None,
    }


# ── 파생 값(§3.5 · §4.2 · §7.4.2–7.4.4) ─────────────────────────

def _unknown_sections(doc: dict[str, Any]) -> set[str]:
    qs = {q["id"]: q for q in (doc.get("planning") or {}).get("questions") or []}
    out: set[str] = set()
    for a in (doc.get("planning") or {}).get("answers") or []:
        if a.get("unknown") and a["question_id"] in qs:
            out.update(rules.UNKNOWN_AFFECTS.get(qs[a["question_id"]]["topic"], []))
    return out


def derive(doc: dict[str, Any]) -> dict[str, Any]:
    """저장 직전마다 파생 값을 다시 계산한다(상태 · 배지 · 문구 · 경로 · 초안 표시)."""
    settings = doc["settings"]
    outline = doc.get("outline")
    if outline:
        spaces = outline.setdefault("spaces", [])
        sections = outline.setdefault("sections", [])
        for i, sp in enumerate(spaces, 1):
            sp["order"] = i
            sp["filled_count"] = rules.space_filled(sp)
            sp["status"] = rules.space_status(sp)
        # 추가 논의 번호 · 섹션 연결
        discussions = outline.setdefault("discussions", [])
        for i, d in enumerate(discussions, 1):
            d["n"] = i
        for sec in sections:
            sec["discussion_ids"] = [d["id"] for d in discussions if sec["id"] in d.get("section_ids", [])]
        # Part 2 섹션 · Timeline 은 공간 · 일정에서 만든다
        p2 = next((s for s in sections if s["group_key"] == "part2"), None)
        if p2 is not None and spaces:
            p2["name"] = f"공간 시나리오 ({len(spaces)})"
            p2["direction"] = " · ".join(sp["name"] for sp in spaces)
            names: list[str] = []
            for sp in spaces:
                for p in sp.get("products") or []:
                    if p["name"] not in names:
                        names.append(p["name"])
            p2["products"] = [{"name": n, "is_extension": False} for n in names]
        unknown = _unknown_sections(doc)
        linked_unconfirmed: set[str] = set()
        rq_unconfirmed = set((doc.get("trace") or {}).get("unconfirmed_item_ids") or [])
        for it in (doc.get("trace") or {}).get("items") or []:
            if it.get("state") == "ok" and it["rq_item_id"] in rq_unconfirmed and "direct" in it.get("link_types", []):
                linked_unconfirmed.update(p.get("id") for p in it.get("places") or [] if p.get("kind") == "section" and p.get("id"))
        open_disc = {sid for d in discussions if d.get("state") == "open" for sid in d.get("section_ids", [])}
        for sec in sections:
            if not sec.get("written", True):
                sec["status"] = "writing"
                continue
            sec["status"] = rules.section_status(sec, spaces=spaces if sec["group_key"] == "part2" else [],
                                                 unknown_sections=unknown, linked_unconfirmed=linked_unconfirmed,
                                                 open_discussion_sections=open_disc)
        for g in outline.setdefault("groups", []):
            gsecs = [s for s in sections if s["group_key"] == g["key"]]
            g["section_ids"] = [s["id"] for s in gsecs]
            g["meta"] = rules.group_meta(g["key"], gsecs, spaces)
            g["badges"] = rules.group_badges(g["key"], [s for s in gsecs if s.get("written", True)], spaces)
            summaries = doc.get("group_summaries") or {}
            g["summary"] = summaries.get(g["key"]) or g.get("summary") or " · ".join(
                s.get("direction") or s["name"] for s in gsecs if s.get("written", True))[:120]
        # 분량 힌트는 목차가 생기면 실제 공간 수로
        hint = rules.volume_hint(len(spaces))
        if hint and settings["volume"].get("source") != "user":
            settings["volume"]["evidence"] = hint
    rules.finalize_settings(settings)
    # 요구 추적 집계
    trace = doc.get("trace")
    if trace:
        trace["total"] = len(trace.get("items") or [])
        trace["ok_count"] = sum(1 for i in trace.get("items") or [] if i.get("state") in ("ok", "resolved"))
    # 일정
    ref = doc.get("requirement_ref") or {}
    open_q = int(ref.get("open_question_count") or 0)
    phases = rules.schedule_phases(int(settings["volume"]["value"]), saved=doc.get("saved_version", 0) > 0,
                                   open_questions=open_q, owners=doc.get("owners"), ids=doc.get("schedule_ids"))
    doc["schedule"] = {"phases": phases, "open_question_count": open_q, "start_d": phases[0]["d_from"]}
    if outline:
        tl = next((s for s in outline.get("sections") or [] if s.get("key") == "timeline"), None)
        if tl is not None and tl.get("written", True):
            tl["direction"] = rules.timeline_direction(phases)
    # 집계 · 문구
    cust, name = doc.get("customer_name") or "", strip_customer(doc.get("name") or "", doc.get("customer_name"))
    doc["title"] = " ".join(x for x in (cust, name) if x).strip() or "새 스토리보드"
    doc["counts"] = counts_of(doc)
    h = rules.content_hash(doc)
    saved = int(doc.get("saved_version") or 0)
    doc["has_unsaved_changes"] = saved == 0 or h != doc.get("saved_hash")
    doc["draft_label"] = rules.draft_label(saved, doc["has_unsaved_changes"])
    doc["step_label"] = rules.step_label(int(doc.get("step") or 1), doc.get("status", "in_progress"))
    doc["sub_line"] = rules.sub_line(doc)
    doc["route"] = rules.route_for(doc)
    return doc


def counts_of(doc: dict[str, Any]) -> dict[str, int]:
    outline = doc.get("outline") or {}
    sections = [s for s in outline.get("sections") or [] if s.get("written", True)]
    nc_sections = sum(1 for s in sections if s.get("status") == "needs_confirmation")
    slot_marks = 0
    for sp in outline.get("spaces") or []:
        for sl in (sp.get("slots") or {}).values():
            if (sl or {}).get("state") == "unknown" or rules.tokens_of(rules.slot_text(sl)):
                slot_marks += 1
    unknown = sum(1 for a in (doc.get("planning") or {}).get("answers") or [] if a.get("unknown"))
    return {
        "sections": len(outline.get("sections") or []),
        "needs_confirmation": nc_sections + slot_marks + unknown,
        "tbd": sum(1 for s in sections if s.get("status") == "tbd"),
        "spaces": len(outline.get("spaces") or []),
        "spaces_empty": sum(1 for sp in outline.get("spaces") or [] if sp.get("filled_count", 0) == 0),
        "unknown_answers": unknown,
        "open_questions": int((doc.get("requirement_ref") or {}).get("open_question_count") or 0),
    }


def to_api(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out["version"] = int(doc.get("saved_version") or 0)
    out["owner"] = doc.get("owner") or {"id": doc.get("owner_id", "system"), "name": ""}
    return out


def list_item(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": doc["id"], "title": doc.get("title") or "", "customer_name": doc.get("customer_name"),
        "step": int(doc.get("step") or 1), "step_label": doc.get("step_label") or "", "status": doc.get("status", "in_progress"),
        "status_label": rules.status_label(doc.get("status", "in_progress")), "sub_line": doc.get("sub_line") or "",
        "updated_at": doc.get("updated_at") or "", "route": doc.get("route") or f"/storyboard/{doc['id']}",
        "cta": rules.cta_for(doc), "active_job": doc.get("active_job"), "requirement_id": doc.get("requirement_id"),
    }


# ── 쓰기 + 색인 ────────────────────────────────────────────

_ws_sig: dict[str, str] = {}


async def index(doc: dict[str, Any]) -> None:
    """시작된 스토리보드만 workspace 작업물 색인에 올린다(§4.0.5). 바뀐 것이 없으면 다시 보내지 않는다."""
    if not doc.get("started"):
        return
    body = (doc.get("title") or "새 스토리보드", doc.get("status", "in_progress"), doc.get("route") or "", doc.get("sub_line") or "",
            doc.get("project_id"))
    sig = rules.stable_hash(body)
    if _ws_sig.get(doc["id"]) == sig:
        return
    await register_item(feature="SB", item_id=doc["id"], title=body[0][:200], status=body[1], route=body[2], summary=body[3],
                        project_id=body[4], meta={"step": doc.get("step"), "version": doc.get("saved_version", 0)})
    _ws_sig[doc["id"]] = sig


async def mutate(sb_id: str, fn: Callable[[dict[str, Any]], dict[str, Any] | None], *, content: bool = True) -> dict[str, Any]:
    """작업본 고치기(낙관적 잠금) → 파생 값 → 색인. content=True 면 작업본 revision +1."""

    def wrapped(doc: dict[str, Any]) -> dict[str, Any] | None:
        res = fn(doc)
        if res is None:
            return None
        if content:
            res["revision"] = int(res.get("revision") or 0) + 1
        return derive(res)

    doc = await repo.update(sb_id, wrapped)
    await index(doc)
    return doc


async def load(sb_id: str) -> dict[str, Any]:
    """읽기 — 끝난 잡의 active_job 을 치운다."""
    doc = await repo.require_sb(sb_id)
    aj = doc.get("active_job")
    if aj:
        rec = await jobs().get(aj["job_id"])
        if rec is None or rec.status in TERMINAL:
            def clear(d: dict[str, Any]) -> dict[str, Any] | None:
                if (d.get("active_job") or {}).get("job_id") != aj["job_id"]:
                    return None
                d["active_job"] = None
                if d.get("outline") and d["outline"].get("writing") and aj["kind"] == "sb.outline":
                    d["outline"]["writing"] = None
                return d
            doc = await mutate(sb_id, clear, content=False)
    return doc


# ── 잡 ────────────────────────────────────────────────────

async def enqueue(sb_id: str, kind: str, payload: dict[str, Any] | None = None, *, active: bool | None = None,
                  doc: dict[str, Any] | None = None) -> str:
    """잡을 넣는다. active 면 먼저 `active_job` 을 걸고(잡이 바로 끝나도 어긋나지 않게) 넣는다."""
    job_id = new_id("job")
    is_active = kind in ACTIVE_KINDS if active is None else active
    if is_active:
        def mark(d: dict[str, Any]) -> dict[str, Any]:
            d["active_job"] = {"job_id": job_id, "kind": kind}
            if kind == "sb.prepare":
                d["prepare_job_id"] = job_id
            return d
        doc = await mutate(sb_id, mark, content=False)
    title = JOB_TITLES.get(kind, kind)
    if doc is not None and doc.get("title"):
        title = f"{title} · {doc['title']}"
    await jobs().enqueue("storyboard", kind, {"sb_id": sb_id, **(payload or {})}, title=title, ref=sb_id,
                         project_id=(doc or {}).get("project_id"), job_id=job_id)
    return job_id


async def finish_job(sb_id: str, job_id: str) -> dict[str, Any] | None:
    """잡이 끝날 때(성공 · 실패 모두) active_job 을 푼다."""
    def clear(d: dict[str, Any]) -> dict[str, Any] | None:
        if (d.get("active_job") or {}).get("job_id") != job_id:
            return None
        d["active_job"] = None
        if d.get("outline"):
            d["outline"]["writing"] = None
        return d
    try:
        return await mutate(sb_id, clear, content=False)
    except ApiError:
        return None


def ensure_not_running(doc: dict[str, Any], kinds: set[str]) -> None:
    aj = doc.get("active_job") or {}
    if aj.get("kind") in kinds:
        raise ApiError(409, "JOB_RUNNING", "이미 진행 중인 작업이 있어요. 끝난 뒤 다시 시도해 주세요.", {"job_id": aj.get("job_id"),
                                                                                       "kind": aj.get("kind")})


def owner_now() -> dict[str, str]:
    u = current_user()
    return {"id": u.id, "name": u.name}


def deep(obj: Any) -> Any:
    return copy.deepcopy(obj)


def stamp() -> str:
    return now_iso()
