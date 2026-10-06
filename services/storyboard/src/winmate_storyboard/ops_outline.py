"""REST 처리 2 — 목차 · 공간 · 수정 요청 · 저장 · 버전 · 비교 · 정의서 동기화(02-storyboard.md §6.3–6.4)."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso

from . import changes, repo, rq, rules, service
from .models import PostRevision, PutSlot, RequirementSyncRequest

log = logging.getLogger("winmate.storyboard.ops")


def _section(d: dict[str, Any], sec_id: str) -> dict[str, Any]:
    sec = next((s for s in (d.get("outline") or {}).get("sections") or [] if s["id"] == sec_id), None)
    if sec is None:
        raise ApiError(404, "NOT_FOUND", f"섹션을 찾을 수 없어요: {sec_id}")
    return sec


def _space(d: dict[str, Any], spc_id: str) -> dict[str, Any]:
    sp = next((s for s in (d.get("outline") or {}).get("spaces") or [] if s["id"] == spc_id), None)
    if sp is None:
        raise ApiError(404, "NOT_FOUND", f"공간을 찾을 수 없어요: {spc_id}")
    return sp


# ── 목차 ──────────────────────────────────────────────────

async def start_outline(sb_id: str, extra_direction: str | None, retry: bool = False) -> str:
    doc = await repo.require_sb(sb_id)
    direction = doc.get("direction") or {}
    if not direction.get("ready") or not direction.get("key_messages"):
        raise ApiError(409, "PREPARE_NOT_READY", "기획 방향을 먼저 골라 주세요")
    service.ensure_not_running(doc, {"sb.outline", "sb.direction", "sb.messages", "sb.prepare"})

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["step"] = 3
        d["started"] = True
        if extra_direction is not None:
            d["direction"]["extra_direction"] = extra_direction.strip()[:400] or None
        if not retry or not d.get("outline"):
            d["outline"] = {"groups": [], "sections": [], "spaces": [], "discussions": [], "writing": {"done": 0, "total": 0,
                                                                                               "stage": "classify"}, "ready": False}
            d["trace"] = None
        return d

    doc = await service.mutate(sb_id, fn)
    return await service.enqueue(sb_id, "sb.outline", {"retry": retry}, doc=doc)


def outline_of(doc: dict[str, Any]) -> dict[str, Any]:
    return doc.get("outline") or {"groups": [], "sections": [], "spaces": [], "discussions": [], "writing": None, "ready": False}


# ── 공간 ──────────────────────────────────────────────────

def empty_slots(space: dict[str, Any]) -> list[str]:
    return [k for k in rules.SLOT_KEYS if ((space.get("slots") or {}).get(k) or {}).get("state", "empty") == "empty"]


async def space_questions(sb_id: str, spc_id: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    """이미 있으면 (질문, None), 없으면 (None, 잡 id)."""
    doc = await repo.require_sb(sb_id)
    space = _space(doc, spc_id)
    todo = empty_slots(space)
    have = {q["slot"]: q for q in space.get("questions") or []}
    if all(s in have for s in todo):
        return [have[s] for s in rules.SLOT_KEYS if s in have and (s in todo or ((space.get("slots") or {}).get(s) or {}).get(
            "source") == "answer")], None
    if space.get("questions_job"):
        rec = await service.jobs().get(space["questions_job"])
        if rec is not None and rec.status not in service.TERMINAL:
            return None, space["questions_job"]
    job_id = await service.enqueue(sb_id, "sb.space.questions", {"space_id": spc_id}, active=False, doc=doc)

    def mark(d: dict[str, Any]) -> dict[str, Any]:
        _space(d, spc_id)["questions_job"] = job_id
        return d

    await service.mutate(sb_id, mark, content=False)
    return None, job_id


async def put_slot(sb_id: str, spc_id: str, slot: str, body: PutSlot) -> dict[str, Any]:
    if slot not in rules.SLOT_KEYS:
        raise ApiError(422, "VALIDATION_FAILED", f"칸 이름이 올바르지 않아요: {slot}", {"slot": slot})
    doc = await repo.require_sb(sb_id)
    space = _space(doc, spc_id)
    cq_id: str | None = None
    added: dict[str, Any] | None = None
    if body.unknown:
        cur = (space.get("slots") or {}).get(slot) or {}
        cq_id = cur.get("customer_question_id")
        ref = doc.get("requirement_ref") or {}
        if not cq_id and ref.get("requirement_id"):
            place = rules.space_label(space)
            text = rules.SLOT_CUSTOMER_Q[slot].format(space=space["name"])
            res = await rq.add_customer_question(ref["requirement_id"], sb_id=sb_id, text=text,
                                                 short_label=f"{space['name']} {rules.SLOT_SHORT[slot]}", place_label=place)
            cq_id = res.get("id")
            added = {"id": cq_id, "short_label": res.get("short_label") or f"{space['name']} {rules.SLOT_SHORT[slot]}"}
    else:
        if not body.selected_option_ids and not (body.custom_text or "").strip():
            raise ApiError(422, "NOTHING_SELECTED", "선택지를 하나 이상 고르거나 '모르겠어요'를 눌러 주세요")
    out: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        sp = _space(d, spc_id)
        if "qa_base" not in sp:     # 질의 전 모습(변경 기록 · 되돌리기의 '전')
            sp["qa_base"] = {k: service.deep(v) for k, v in sp.items() if k != "qa_base"}
        slots = sp.setdefault("slots", {})
        if body.unknown:
            slots[slot] = {"state": "unknown", "segments": [{"text": "[확인 필요]", "placeholder": "[확인 필요]", "ai_added": False}],
                           "source": "answer", "answer": None, "customer_question_id": cq_id}
            if cq_id and cq_id not in sp.setdefault("customer_question_ids", []):
                sp["customer_question_ids"].append(cq_id)
            if added and not any(a["id"] == added["id"] for a in sp.setdefault("added_questions", [])):
                sp["added_questions"].append(added)
        else:
            q = next((x for x in sp.get("questions") or [] if x["slot"] == slot), None)
            opts = {o["id"]: o["label"] for o in (q or {}).get("options") or []}
            sel = list(body.selected_option_ids or [])
            bad = [s for s in sel if s not in opts]
            if bad:
                raise ApiError(422, "VALIDATION_FAILED", "없는 선택지예요", {"option_ids": bad})
            labels = [opts[s] for s in sel]
            custom = (body.custom_text or "").strip()
            if custom:
                labels.append(custom[:120])
            slots[slot] = {"state": "filled", "segments": [{"text": " / ".join(labels), "ai_added": False}], "source": "answer",
                           "answer": {"selected_option_ids": sel, "custom_text": custom or None, "labels": labels},
                           "customer_question_id": None}
        out.update(sp)
        return d

    doc = await service.mutate(sb_id, fn)
    res = dict(_space(doc, spc_id))
    res["customer_question_id"] = cq_id
    return res


async def compose(sb_id: str, spc_id: str) -> str:
    doc = await repo.require_sb(sb_id)
    space = _space(doc, spc_id)
    if not any(((space.get("slots") or {}).get(k) or {}).get("source") == "answer" for k in rules.SLOT_KEYS) and \
            rules.space_filled(space) == 0:
        raise ApiError(422, "NOTHING_SELECTED", "질문에 먼저 답해 주세요")
    job_id = await service.enqueue(sb_id, "sb.space.compose", {"space_id": spc_id}, active=False, doc=doc)

    def mark(d: dict[str, Any]) -> dict[str, Any]:
        sp = _space(d, spc_id)
        sp["composing"] = True
        sp["compose_job"] = job_id
        return d

    await service.mutate(sb_id, mark, content=False)
    return job_id


async def agenda(sb_id: str) -> str:
    doc = await repo.require_sb(sb_id)
    outline = outline_of(doc)
    secs = {s["id"]: s for s in outline["sections"]}
    title = (doc.get("direction") or {}).get("options") and next(
        (o["title"] for o in doc["direction"]["options"] if o["id"] == doc["direction"].get("selected_option_id")), None)
    lines = [f"{doc.get('title') or '스토리보드'} 회의 안건", ""]
    if title:
        lines.insert(1, f"기획 방향: {title}")
    for d in outline.get("discussions") or []:
        rel = [rules.section_label(secs[s]) for s in d.get("section_ids") or [] if s in secs]
        lines.append(f"{d['n']}. {d['label']}" + (f" — 관련: {' · '.join(rel)}" if rel else ""))
    if not outline.get("discussions"):
        lines.append("추가 논의가 없어요.")
    return "\n".join(lines).strip()


# ── 수정 요청 ──────────────────────────────────────────────

def target_sections(d: dict[str, Any], target: dict[str, Any], scope: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(섹션들, 공간들) — 범위가 묶음이면 그 묶음 전체."""
    outline = outline_of(d)
    if target["kind"] == "space":
        sp = _space(d, target["id"])
        if scope == "group":
            return [s for s in outline["sections"] if s["group_key"] == "part2"], list(outline["spaces"])
        return [], [sp]
    sec = _section(d, target["id"])
    if scope == "group":
        if sec["group_key"] == "part2":
            return [sec], list(outline["spaces"])
        return [s for s in outline["sections"] if s["group_key"] == sec["group_key"]], []
    return [sec], []


def target_hash(sections: list[dict[str, Any]], spaces: list[dict[str, Any]]) -> str:
    return rules.stable_hash({
        "sections": [[s["id"], [ln.get("text") for ln in s.get("lines") or []]] for s in sections],
        "spaces": [[sp["id"], {k: rules.slot_text((sp.get("slots") or {}).get(k)) for k in rules.SLOT_KEYS}] for sp in spaces],
    })


GROUP_SCOPE_LABEL = {"start": "시작 전체", "part1": "Part 1 전체", "part2": "Part 2 전체", "part3": "Part 3 전체", "end": "마무리 전체"}


async def create_revision(sb_id: str, body: PostRevision) -> tuple[str, str]:
    doc = await repo.require_sb(sb_id)
    if not (doc.get("outline") or {}).get("ready"):
        raise ApiError(409, "PREPARE_NOT_READY", "목차가 다 만들어진 뒤에 수정 요청을 할 수 있어요")
    if not body.instruction.strip() and not body.chips:
        raise ApiError(422, "VALIDATION_FAILED", "어떻게 바꿀지 적거나 빠른 지시를 골라 주세요")
    target = body.target.model_dump()
    secs, spaces = target_sections(doc, target, body.scope)
    if target["kind"] == "section":
        sec = _section(doc, target["id"])
        target["label"] = rules.section_label(sec)
        group = sec["group_key"]
    else:
        target["label"] = rules.space_label(_space(doc, target["id"]))
        group = "part2"
    rev_id = new_id("rev")
    rev = {"id": rev_id, "storyboard_id": sb_id, "target": target, "scope": body.scope,
           "scope_label": GROUP_SCOPE_LABEL[group] if body.scope == "group" else target["label"],
           "instruction": body.instruction.strip(), "chips": list(body.chips), "status": "running",
           "base_hash": target_hash(secs, spaces), "rows": [], "changed_count": 0, "job_id": None, "proposed": []}
    await repo.put_revision(rev_id, rev)
    job_id = await service.enqueue(sb_id, "sb.revise", {"revision_id": rev_id}, active=False, doc=doc)
    rev["job_id"] = job_id
    await repo.put_revision(rev_id, rev)
    return job_id, rev_id


async def get_revision(sb_id: str, rev_id: str) -> dict[str, Any]:
    rev = await repo.get_revision(rev_id)
    if rev is None or rev.get("storyboard_id") != sb_id:
        raise ApiError(404, "NOT_FOUND", f"수정 요청을 찾을 수 없어요: {rev_id}")
    return rev


async def apply_revision(sb_id: str, rev_id: str) -> dict[str, Any]:
    rev = await get_revision(sb_id, rev_id)
    if rev["status"] == "applied":
        raise ApiError(409, "CONFLICT", "이미 적용한 수정이에요")
    if rev["status"] != "ready":
        raise ApiError(409, "CONFLICT", "수정안이 아직 준비되지 않았어요")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        secs, spaces = target_sections(d, rev["target"], rev["scope"])
        if target_hash(secs, spaces) != rev["base_hash"]:
            raise ApiError(409, "REVISION_STALE", "그 사이 이 섹션이 바뀌었어요. 수정 요청을 다시 해 주세요.")
        cause = {"kind": "revision", "ref": rev_id, "label": "수정 요청"}
        for prop in rev.get("proposed") or []:
            if prop["kind"] == "section":
                sec = _section(d, prop["id"])
                before = service.deep(sec)
                sec["lines"] = prop["lines"]
                kinds = {r["kind"] for r in rev["rows"] if r.get("section_label") in (None, rules.section_label(sec))}
                changes.record(d, place_label=rules.section_label(sec), kind="changed" if kinds - {"kept"} else "kept", cause=cause,
                               before_summary=changes.summarize_section(before), after_summary=changes.summarize_section(sec),
                               target=("section", sec["id"]), before=before, after=service.deep(sec))
            else:
                sp = _space(d, prop["id"])
                before = service.deep(sp)
                for k, segs in (prop.get("slots") or {}).items():
                    cur = sp.setdefault("slots", {}).get(k) or {}
                    sp["slots"][k] = {**cur, "state": "filled" if segs else cur.get("state", "empty"), "segments": segs,
                                      "source": "revision"}
                changes.record(d, place_label=rules.space_label(sp, " · "), kind="changed", cause=cause,
                               before_summary=changes.summarize_space(before), after_summary=changes.summarize_space(sp),
                               target=("space", sp["id"]), before=before, after=service.deep(sp))
        if d.get("trace"):
            d["trace"]["stale"] = True
        return d

    doc = await service.mutate(sb_id, fn)
    rev["status"] = "applied"
    await repo.put_revision(rev_id, rev)
    if doc.get("trace"):
        await service.enqueue(sb_id, "sb.trace.refresh", {}, active=False, doc=doc)
    return doc


async def discard_revision(sb_id: str, rev_id: str) -> dict[str, Any]:
    rev = await get_revision(sb_id, rev_id)
    if rev["status"] == "applied":
        raise ApiError(409, "CONFLICT", "이미 적용한 수정이에요")
    rev["status"] = "discarded"
    await repo.put_revision(rev_id, rev)
    return rev


# ── 저장 · 버전 ────────────────────────────────────────────

async def save(sb_id: str, note: str | None, *, reason: str = "save") -> tuple[int, bool]:
    await repo.require_sb(sb_id)
    result: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        service.derive(d)
        h = rules.content_hash(d)
        saved = int(d.get("saved_version") or 0)
        result.clear()
        if saved > 0 and h == d.get("saved_hash"):
            result.update(version=saved, created=False)
            if d.get("status") == "in_progress":
                d["status"] = "done"
                d["step"] = 5
                return d
            return None
        n = saved + 1
        result.update(version=n, created=True, record={
            "note": note, "created_at": now_iso(), "created_by": (d.get("owner") or {}).get("name") or "", "reason": reason,
            "snapshot": rules.content_snapshot(d), "causes": changes.cause_labels(d.get("changes") or []),
            "changes": d.get("changes") or [], "title": d.get("title"),
        })
        d["saved_version"] = n
        d["saved_hash"] = h
        d["changes"] = []
        d["started"] = True
        if d.get("status") == "in_progress":
            d["status"] = "done"
        d["step"] = 5
        return d

    await service.mutate(sb_id, fn, content=False)
    if result.get("created"):
        await repo.put_version(sb_id, result["version"], result["record"])
    return int(result["version"]), bool(result["created"])


async def versions(sb_id: str) -> list[dict[str, Any]]:
    await repo.require_sb(sb_id)
    out = []
    for v in reversed(await repo.list_versions(sb_id)):
        out.append({"version": v["n"], "note": v.get("note"), "created_at": v.get("created_at") or v.get("updated_at"),
                    "created_by": v.get("created_by"), "reason": v.get("reason", "save"), "causes": v.get("causes") or []})
    return out


async def version(sb_id: str, n: int) -> dict[str, Any]:
    await repo.require_sb(sb_id)
    v = await repo.get_version(sb_id, n)
    if v is None:
        raise ApiError(404, "VERSION_NOT_FOUND", f"v{n}을(를) 찾을 수 없어요")
    return {"version": n, "note": v.get("note"), "created_at": v.get("created_at") or v.get("updated_at"),
            "created_by": v.get("created_by"), "reason": v.get("reason", "save"), "snapshot": v.get("snapshot") or {},
            "causes": v.get("causes") or []}


async def restore(sb_id: str, n: int) -> int:
    v = await repo.get_version(sb_id, n)
    if v is None:
        raise ApiError(404, "VERSION_NOT_FOUND", f"v{n}을(를) 찾을 수 없어요")
    snap = v.get("snapshot") or {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for k in ("settings", "planning", "direction", "outline", "trace", "requirement_ref"):
            if k in snap:
                d[k] = service.deep(snap[k])
        changes.record(d, place_label="전체", kind="changed", cause={"kind": "restore", "label": f"v{n} 복원"},
                       before_summary=f"v{d.get('saved_version', 0)}", after_summary=f"v{n}", revertible=False)
        return d

    await service.mutate(sb_id, fn)
    ver, _ = await save(sb_id, f"v{n} 복원", reason="restore")
    return ver


# ── 비교 · 되돌리기 ─────────────────────────────────────────

def _public_row(r: dict[str, Any], revertible: bool) -> dict[str, Any]:
    out = {k: v for k, v in r.items() if k != "inverse_ops"}
    out["revertible"] = bool(revertible and r.get("revertible") and r.get("kind") != "kept")
    return out


async def compare(sb_id: str, frm: int | None, to: str | None) -> dict[str, Any]:
    doc = await repo.require_sb(sb_id)
    saved = int(doc.get("saved_version") or 0)
    vers = {v["n"]: v for v in await repo.list_versions(sb_id)}
    draft_rows = doc.get("changes") or []
    if to is None:
        # 기본: 최신 저장 버전 → 작업본. 작업본이 저장본과 같으면 직전 두 저장 버전(저장 버전이 하나뿐이면 v1 → 작업본, 바뀐 곳 0)
        if draft_rows or doc.get("has_unsaved_changes") or saved < 2:
            to = "draft"
            frm = saved if frm is None else frm
        else:
            to = str(saved)
            frm = saved - 1 if frm is None else frm
    frm = saved if frm is None else int(frm)
    if frm < 0 or (frm > 0 and frm not in vers):
        raise ApiError(404, "VERSION_NOT_FOUND", f"v{frm}을(를) 찾을 수 없어요")
    rows: list[dict[str, Any]] = []
    if to == "draft":
        for n in range(frm + 1, saved + 1):
            rows += [_public_row(r, False) for r in (vers.get(n) or {}).get("changes") or []]
        rows += [_public_row(r, True) for r in draft_rows]
        to_obj = {"version": saved + 1, "version_label": f"v{saved + 1}", "is_draft": True, "date": doc.get("updated_at")}
        revertible = True
    else:
        try:
            m = int(to)
        except ValueError as exc:
            raise ApiError(422, "VALIDATION_FAILED", "to 는 버전 번호 또는 draft 예요") from exc
        if m not in vers or m < frm:
            raise ApiError(404, "VERSION_NOT_FOUND", f"v{m}을(를) 찾을 수 없어요")
        for n in range(frm + 1, m + 1):
            rows += [_public_row(r, False) for r in (vers.get(n) or {}).get("changes") or []]
        to_obj = {"version": m, "version_label": f"v{m}", "is_draft": False,
                  "date": vers[m].get("created_at") or vers[m].get("updated_at")}
        revertible = False
    fv = vers.get(frm) or {}
    return {"from": {"version": frm, "note": fv.get("note"), "date": fv.get("created_at") or fv.get("updated_at")},
            "to": to_obj, "causes": changes.cause_labels(rows), "rows": rows, "count": changes.changed_count(rows),
            "revertible": revertible}


async def revert_change(sb_id: str, chg_id: str) -> dict[str, Any]:
    await repo.require_sb(sb_id)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        changes.revert(d, chg_id)
        if d.get("trace"):
            d["trace"]["stale"] = True
        return d

    return await service.mutate(sb_id, fn)


# ── 정의서 동기화 ──────────────────────────────────────────

async def requirement_sync(sb_id: str, body: RequirementSyncRequest) -> tuple[str, dict[str, str]]:
    doc = await repo.require_sb(sb_id)
    ref = doc.get("requirement_ref") or {}
    if ref.get("requirement_id") != body.requirement_id:
        raise ApiError(422, "VALIDATION_FAILED", "이 스토리보드가 쓰는 정의서가 아니에요", {"requirement_id": body.requirement_id})
    if body.dry_run:
        syp = new_id("syp")
        await repo.put_preview(syp, {"storyboard_id": sb_id, "requirement_id": body.requirement_id,
                                     "from_rq_version": int(ref.get("version") or 0), "to_rq_version": body.to_version,
                                     "reply_id": body.reply_id, "rows": [], "count": 0, "causes": [], "status": "running",
                                     "from_version": int(doc.get("saved_version") or 0)})
        job_id = await service.enqueue(sb_id, "sb.rq_sync", {"requirement_id": body.requirement_id, "to_version": body.to_version,
                                                             "reply_id": body.reply_id, "dry_run": True, "preview_id": syp},
                                       active=False, doc=doc)
        return job_id, {"kind": "sync_preview", "id": syp}
    to_version = body.to_version
    if not to_version and not body.reply_id:
        req = await rq.get_requirement(body.requirement_id)
        to_version = int(req.get("version") or 0)
    if to_version is not None and int(to_version) < int(ref.get("version") or 0):
        raise ApiError(422, "VALIDATION_FAILED", "지금 쓰는 정의서보다 앞선 버전으로는 반영할 수 없어요")
    service.ensure_not_running(doc, {"sb.rq_sync", "sb.outline", "sb.prepare", "sb.direction"})
    job_id = await service.enqueue(sb_id, "sb.rq_sync", {"requirement_id": body.requirement_id, "to_version": to_version,
                                                         "reply_id": body.reply_id, "dry_run": False}, doc=doc)
    return job_id, {"kind": "storyboard", "id": sb_id}


async def preview(sb_id: str, syp_id: str) -> dict[str, Any]:
    p = await repo.get_preview(syp_id)
    if p is None or p.get("storyboard_id") != sb_id:
        raise ApiError(404, "NOT_FOUND", f"미리 보기를 찾을 수 없어요: {syp_id}")
    return p
