"""REST 처리 1 — 스토리보드 · 정의서 · 설정 · 기획 질의 · 기획 방향 · 핵심 메시지(02-storyboard.md §6.1–6.2)."""
from __future__ import annotations

import base64
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso

from . import changes, expressions, guards, repo, rq, rules, service
from .models import CompetitorImport, CreateStoryboard, PatchDirection, PatchKeyMessage, PostDirection, PostEvidence, \
    PutPlanningAnswer, SettingsPatch

log = logging.getLogger("winmate.storyboard.ops")


def _req_customer(req: dict[str, Any]) -> str | None:
    if req.get("customer_name"):
        return req["customer_name"]
    form = req.get("form") or {}
    cn = form.get("customer_name")
    return (cn.get("value") if isinstance(cn, dict) else cn) or None


def rq_ref_from(req: dict[str, Any], version: int) -> dict[str, Any]:
    return {
        "requirement_id": req["id"], "version": version, "title": req.get("title") or "", "item_count": int(req.get("item_count") or 0),
        "latest_version": int(req.get("version") or version), "project_id": req.get("project_id"),
        "customer_name": _req_customer(req), "open_question_count": int(req.get("open_question_count") or 0),
        "saved_at": req.get("saved_at"), "version_note": None,
    }


async def _resolve_rq(requirement_id: str, version: int | None) -> dict[str, Any]:
    req = await rq.get_requirement(requirement_id)
    v = int(version or req.get("version") or 0)
    if v <= 0:
        raise ApiError(422, "RQ_NOT_SAVED", "저장된 버전이 없는 정의서예요. 정의서를 먼저 저장해 주세요.", {"requirement_id": requirement_id})
    if version and int(req.get("version") or 0) and version > int(req.get("version") or 0):
        raise ApiError(404, "VERSION_NOT_FOUND", f"정의서 v{version}을(를) 찾을 수 없어요")
    return rq_ref_from(req, v)


def _reset_for_rq(d: dict[str, Any], ref: dict[str, Any]) -> dict[str, Any]:
    fresh = service.new_doc(d["id"], owner=d["owner"], rq_ref=ref)
    for k in ("settings", "planning", "direction", "outline", "trace", "internal_phrases", "item_classes", "group_summaries",
              "owners"):
        d[k] = fresh[k]
    d["requirement_ref"] = ref
    d["requirement_id"] = ref["requirement_id"]
    d["project_id"] = ref.get("project_id")
    d["customer_name"] = ref.get("customer_name")
    d["name"] = service.strip_customer(ref.get("title") or d.get("name") or "", ref.get("customer_name")) or d.get("name")
    d["step"] = 1
    return d


# ── 만들기 · 읽기 · 목록 ────────────────────────────────────

async def create(body: CreateStoryboard) -> tuple[dict[str, Any], bool]:
    owner = service.owner_now()
    drafts = await repo.list_sb({"owner_id": owner["id"], "started": False}, limit=50)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=service.DRAFT_TTL_DAYS)).isoformat()
    live = []
    for d in drafts:
        if (d.get("updated_at") or "") < cutoff:
            await repo.delete_sb(d["id"])        # 시작 전 초안 7일 보관(제안)
        else:
            live.append(d)
    ref = await _resolve_rq(body.requirement_id, body.requirement_version) if body.requirement_id else None
    if live:
        draft = live[0]
        cur = draft.get("requirement_ref") or {}
        same = bool(ref) and cur.get("requirement_id") == ref["requirement_id"] and int(cur.get("version") or 0) == ref["version"]
        if ref and not same:
            doc = await service.mutate(draft["id"], lambda d: _reset_for_rq(d, ref))
            await service.enqueue(doc["id"], "sb.prepare", {}, doc=doc)
        elif ref and same and not draft["settings"].get("ready") and not draft.get("active_job"):
            await service.enqueue(draft["id"], "sb.prepare", {}, doc=draft)
        doc = await service.load(draft["id"])
        return doc, False
    sb_id = new_id("sb")
    doc = service.derive(service.new_doc(sb_id, owner=owner, rq_ref=ref))
    doc = await repo.create_sb(sb_id, doc)
    if ref:
        await service.enqueue(sb_id, "sb.prepare", {}, doc=doc)
        doc = await repo.require_sb(sb_id)
    return doc, True


_RQ_CHECK_S = 20.0


async def get(sb_id: str) -> dict[str, Any]:
    """읽기. 정의서 링크가 `pending` 이면 여기서 동기화 잡을 시작한다(§6.1). 정의서 새 버전 띠(Q-18)도 갱신."""
    doc = await service.load(sb_id)
    ref = doc.get("requirement_ref")
    if not ref or not doc.get("started") or doc.get("active_job"):
        return doc
    last = float(doc.get("rq_checked_ts") or 0)
    if time.time() - last < _RQ_CHECK_S:
        return doc
    try:
        links = await rq.get_links(ref["requirement_id"])
        req = await rq.get_requirement(ref["requirement_id"])
    except ApiError as exc:
        log.info("정의서 확인 건너뜀 %s: %s", sb_id, exc.code)
        return await service.mutate(sb_id, lambda d: {**d, "rq_checked_ts": time.time()}, content=False)
    mine = next((lk for lk in links if lk.get("service") == "storyboard" and lk.get("ref_id") == sb_id), None)
    latest = int(req.get("version") or 0)
    pending = bool(mine and mine.get("sync_state") == "pending")
    note = None
    if latest > int(ref.get("version") or 0) and not pending:
        try:   # 띠 한 줄: 변경 수 · 저장 메모(통합 — 늘 비어 있던 rq_update.note)
            note = rq.update_note(await rq.get_versions(ref["requirement_id"]), int(ref.get("version") or 0), latest)
        except ApiError as exc:
            log.info("정의서 버전 요약 건너뜀 %s: %s", sb_id, exc.code)

    def upd(d: dict[str, Any]) -> dict[str, Any]:
        d["rq_checked_ts"] = time.time()
        r = d.get("requirement_ref") or {}
        r["latest_version"] = latest
        r["open_question_count"] = int(req.get("open_question_count") or 0)
        d["requirement_ref"] = r
        d["rq_update"] = {"version": latest, "note": note} if (latest > int(r.get("version") or 0) and not pending) else None
        return d

    doc = await service.mutate(sb_id, upd, content=False)
    if pending:
        to_v = int((mine or {}).get("pending_version") or latest)
        if to_v > int(ref.get("version") or 0):
            await service.enqueue(sb_id, "sb.rq_sync", {"requirement_id": ref["requirement_id"], "to_version": to_v,
                                                        "dry_run": False}, doc=doc)
            doc = await repo.require_sb(sb_id)
    return doc


def _cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def _offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:  # noqa: BLE001
        return 0


async def list_(tab: str, q: str | None, customer: str | None, updated_after: str | None, limit: int,
                cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
    owner = service.owner_now()
    docs = await repo.list_sb({"owner_id": owner["id"], "started": True}, limit=2000)
    if tab == "in_progress":
        docs = [d for d in docs if d.get("status") == "in_progress"]
    elif tab == "done":
        docs = [d for d in docs if d.get("status") in ("done", "shared")]
    if q:
        ql = q.casefold()
        docs = [d for d in docs if ql in (d.get("title") or "").casefold() or ql in (d.get("customer_name") or "").casefold()]
    if customer:
        cl = customer.casefold()
        docs = [d for d in docs if cl in (d.get("customer_name") or "").casefold()]
    if updated_after:
        docs = [d for d in docs if (d.get("updated_at") or "") > updated_after]
    off = _offset(cursor)
    page = docs[off: off + limit]
    nxt = _cursor(off + limit) if len(docs) > off + limit else None
    return [service.list_item(d) for d in page], nxt


async def counts() -> dict[str, int]:
    owner = service.owner_now()
    docs = await repo.list_sb({"owner_id": owner["id"], "started": True}, limit=5000)
    return {"all": len(docs), "in_progress": sum(1 for d in docs if d.get("status") == "in_progress"),
            "done": sum(1 for d in docs if d.get("status") in ("done", "shared"))}


async def patch(sb_id: str, name: str | None, step: int | None) -> dict[str, Any]:
    await repo.require_sb(sb_id)

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        changed = False
        if name is not None and name.strip() and name.strip() != d.get("name"):
            d["name"] = name.strip()
            changed = True
        if step is not None and step != d.get("step"):
            if step >= 3 and not (d.get("outline") or {}).get("ready"):
                raise ApiError(409, "STAGE_LOCKED", "목차가 생긴 뒤에 넘어갈 수 있어요")
            if step <= 2 and d.get("started") and (d.get("outline") or {}).get("ready"):
                raise ApiError(409, "STAGE_LOCKED", "목차가 있는 스토리보드는 앞 단계로 돌아갈 수 없어요")
            d["step"] = int(step)
            changed = True
        return d if changed else None

    return await service.mutate(sb_id, fn, content=False)


# ── 정의서 · 설정 ──────────────────────────────────────────

async def put_requirement(sb_id: str, requirement_id: str, version: int | None) -> str:
    doc = await repo.require_sb(sb_id)
    if int(doc.get("step") or 1) >= 2 or doc.get("started"):
        raise ApiError(409, "STAGE_LOCKED", "정의서는 새 스토리보드에서 바꿀 수 있어요")
    ref = await _resolve_rq(requirement_id, version)
    doc = await service.mutate(sb_id, lambda d: _reset_for_rq(d, ref))
    return await service.enqueue(sb_id, "sb.prepare", {}, doc=doc)


async def prepare(sb_id: str) -> str:
    doc = await repo.require_sb(sb_id)
    if not doc.get("requirement_ref"):
        raise ApiError(422, "RQ_NOT_SAVED", "먼저 요구사항 정의서를 골라 주세요")
    service.ensure_not_running(doc, {"sb.prepare", "sb.direction", "sb.outline"})
    return await service.enqueue(sb_id, "sb.prepare", {}, doc=doc)


async def patch_settings(sb_id: str, body: SettingsPatch) -> dict[str, Any]:
    await repo.require_sb(sb_id)

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        s = d["settings"]
        changed = False
        for key in ("stage", "doc_type", "volume", "language"):
            val = getattr(body, key)
            if val is None:
                continue
            if s[key]["value"] != val or s[key]["source"] != "user":
                s[key]["value"] = val
                s[key]["source"] = "user"
                changed = True
        return d if changed else None

    doc = await service.mutate(sb_id, fn)
    return doc["settings"]


# ── 기획 질의 ──────────────────────────────────────────────

def roles_for(q: dict[str, Any], selected: list[str]) -> dict[str, str]:
    roles = q.get("order_roles") or []
    return {oid: roles[i] for i, oid in enumerate(selected) if i < len(roles)}


async def answer(sb_id: str, qid: str, body: PutPlanningAnswer) -> dict[str, Any]:
    if not body.unknown and not body.selected_option_ids and not (body.custom_text or "").strip() \
            and body.follow_up_option_id is None:
        raise ApiError(422, "NOTHING_SELECTED", "선택지를 하나 이상 고르거나 '모르겠어요'를 눌러 주세요")
    result: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        planning = d["planning"]
        q = next((x for x in planning["questions"] if x["id"] == qid), None)
        if q is None:
            raise ApiError(404, "NOT_FOUND", f"기획 질의를 찾을 수 없어요: {qid}")
        answers = planning.setdefault("answers", [])
        ans = next((a for a in answers if a["question_id"] == qid), None)
        if ans is None:
            ans = {"question_id": qid, "selected_option_ids": [], "custom_text": None, "unknown": False, "follow_up_option_id": None}
            answers.append(ans)
        if body.unknown:
            ans.update({"selected_option_ids": [], "unknown": True, "follow_up_option_id": None})
        else:
            sel = list(body.selected_option_ids if body.selected_option_ids is not None else ans.get("selected_option_ids") or [])
            if body.custom_text is not None and q.get("allow_custom", True):
                text = body.custom_text.strip()
                cust = next((o for o in q["options"] if o.get("custom")), None)
                if text:
                    if cust is None:
                        cust = {"id": new_id("opt"), "label": text[:80], "custom": True}
                        q["options"].append(cust)
                    else:
                        cust["label"] = text[:80]
                    if cust["id"] not in sel:
                        sel.append(cust["id"])
                    ans["custom_text"] = text[:80]
                else:
                    if cust is not None:
                        q["options"] = [o for o in q["options"] if o["id"] != cust["id"]]
                        sel = [s for s in sel if s != cust["id"]]
                    ans["custom_text"] = None
            valid = {o["id"] for o in q["options"]}
            bad = [s for s in sel if s not in valid]
            if bad:
                raise ApiError(422, "VALIDATION_FAILED", "없는 선택지예요", {"option_ids": bad})
            if len(sel) != len(set(sel)):
                raise ApiError(422, "VALIDATION_FAILED", "같은 선택지를 두 번 고를 수 없어요")
            if q.get("select") == "single" and len(sel) > 1:
                raise ApiError(422, "VALIDATION_FAILED", "하나만 고를 수 있어요")
            if not sel:
                raise ApiError(422, "NOTHING_SELECTED", "선택지를 하나 이상 고르거나 '모르겠어요'를 눌러 주세요")
            ans["selected_option_ids"] = sel
            ans["unknown"] = False
            chosen = next((o for o in q["options"] if o["id"] == sel[0]), None)
            fu = (chosen or {}).get("follow_up")
            if body.follow_up_option_id is not None:
                if not fu or body.follow_up_option_id not in {o["id"] for o in fu.get("options") or []}:
                    raise ApiError(422, "VALIDATION_FAILED", "이 선택지에는 그 꼬리 답이 없어요")
                ans["follow_up_option_id"] = body.follow_up_option_id
            elif not fu:
                ans["follow_up_option_id"] = None
            elif ans.get("follow_up_option_id") and ans["follow_up_option_id"] not in {o["id"] for o in fu.get("options") or []}:
                ans["follow_up_option_id"] = None
        ans["answered_at"] = now_iso()
        ans["roles"] = roles_for(q, ans["selected_option_ids"])
        result.update(ans)
        return d

    await service.mutate(sb_id, fn)
    return result


# ── 기획 방향 · 핵심 메시지 ──────────────────────────────────

async def start_direction(sb_id: str, body: PostDirection) -> str:
    doc = await repo.require_sb(sb_id)
    if not doc.get("requirement_ref"):
        raise ApiError(422, "RQ_NOT_SAVED", "먼저 요구사항 정의서를 골라 주세요")
    if not doc["settings"].get("ready"):
        raise ApiError(409, "PREPARE_NOT_READY", "정의서를 아직 읽는 중이에요. 잠시 후 다시 시도해 주세요.")
    service.ensure_not_running(doc, {"sb.prepare", "sb.direction", "sb.messages", "sb.outline"})

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        planning = d["planning"]
        if body.skip_planning:
            planning["answers"] = [{"question_id": q["id"], "selected_option_ids": [], "custom_text": None, "unknown": True,
                                    "follow_up_option_id": None, "answered_at": now_iso(), "roles": {}}
                                   for q in planning["questions"]]
        else:
            have = {a["question_id"] for a in planning.get("answers") or []}
            for q in planning["questions"]:   # 답하지 않은 질의는 확인 필요로 남긴다
                if q["id"] not in have:
                    planning.setdefault("answers", []).append({"question_id": q["id"], "selected_option_ids": [], "custom_text": None,
                                                               "unknown": True, "follow_up_option_id": None,
                                                               "answered_at": now_iso(), "roles": {}})
        d["started"] = True
        d["step"] = 2
        d["direction"] = {**(d.get("direction") or {}), "ready": False}
        return d

    doc = await service.mutate(sb_id, fn)
    return await service.enqueue(sb_id, "sb.direction", {}, doc=doc)


async def patch_direction(sb_id: str, body: PatchDirection) -> tuple[dict[str, Any], str | None]:
    doc = await repo.require_sb(sb_id)
    direction = doc.get("direction") or {}
    if not direction.get("options"):
        raise ApiError(409, "PREPARE_NOT_READY", "기획 방향을 아직 만드는 중이에요")
    changed_sel = body.selected_option_id is not None and body.selected_option_id != direction.get("selected_option_id")
    if body.selected_option_id is not None and body.selected_option_id not in {o["id"] for o in direction["options"]}:
        raise ApiError(422, "VALIDATION_FAILED", "없는 기획 방향이에요")
    if changed_sel:
        service.ensure_not_running(doc, {"sb.direction", "sb.messages", "sb.outline"})

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        dr = d["direction"]
        if body.selected_option_id is not None:
            dr["selected_option_id"] = body.selected_option_id
        if body.extra_direction is not None:
            dr["extra_direction"] = body.extra_direction.strip()[:400] or None
        return d

    doc = await service.mutate(sb_id, fn)
    job_id = None
    if changed_sel:
        job_id = await service.enqueue(sb_id, "sb.messages", {}, doc=doc)
        doc = await repo.require_sb(sb_id)
    return doc["direction"], job_id


async def allowed_numbers(doc: dict[str, Any]) -> set[str]:
    texts: list[str] = []
    ref = doc.get("requirement_ref") or {}
    if ref.get("requirement_id"):
        try:
            snap = await rq.get_snapshot(ref["requirement_id"], int(ref["version"]))
            texts += snap.customer_facing_text()
        except ApiError:
            pass
    for q in (doc.get("planning") or {}).get("questions") or []:
        texts += [o.get("label", "") for o in q.get("options") or []]
    return guards.numbers_in(texts)


def _msg(d: dict[str, Any], kmsg: str) -> dict[str, Any]:
    msg = next((m for m in (d.get("direction") or {}).get("key_messages") or [] if m["id"] == kmsg), None)
    if msg is None:
        raise ApiError(404, "NOT_FOUND", f"핵심 메시지를 찾을 수 없어요: {kmsg}")
    return msg


async def patch_key_message(sb_id: str, kmsg: str, body: PatchKeyMessage) -> dict[str, Any]:
    doc = await repo.require_sb(sb_id)
    cur = _msg(doc, kmsg)
    from_vp = bool(body.source and body.source.get("service") == "vp")
    text, flags, memos = await expressions.check(
        body.text.strip(), internal_phrases=doc.get("internal_phrases") or [], prev_flags=cur.get("flags") or [],
        allowed_numbers=await allowed_numbers(doc), from_user=True, use_llm=True)
    out: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        msg = _msg(d, kmsg)
        before = service.deep(msg)
        msg["text"] = text
        msg["flags"] = flags
        msg["updated_by"] = "vp" if from_vp else "user"
        if memos:
            d["direction"].setdefault("internal_memos", []).extend(memos)
        if before["text"] != text:
            cause = ({"kind": "vp", "ref": (body.source or {}).get("ref_id"), "label": "VP 문장 반영"} if from_vp
                     else {"kind": "user", "label": "직접 수정"})
            changes.record(d, place_label=f"Key Message · {msg['place_label']}", kind="changed", cause=cause,
                           before_summary=before["text"], after_summary=text, target=("key_message", kmsg),
                           before=before, after=service.deep(msg))
        out.update(msg)
        return d

    await service.mutate(sb_id, fn)
    return out


async def flag_action(sb_id: str, kmsg: str, flg: str, action: str) -> dict[str, Any]:
    await repo.require_sb(sb_id)
    out: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        msg = _msg(d, kmsg)
        before = service.deep(msg)
        if action == "apply":
            expressions.apply_flag(msg, flg, d["direction"])
        else:
            expressions.revert_flag(msg, flg, d["direction"])
        if before["text"] != msg["text"]:
            changes.record(d, place_label=f"Key Message · {msg['place_label']}", kind="changed",
                           cause={"kind": "user", "label": "직접 수정"}, before_summary=before["text"], after_summary=msg["text"],
                           target=("key_message", kmsg), before=before, after=service.deep(msg))
        out.update(msg)
        return d

    await service.mutate(sb_id, fn)
    return out


async def add_evidence(sb_id: str, kmsg: str, body: PostEvidence) -> dict[str, Any]:
    await repo.require_sb(sb_id)
    out: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        msg = _msg(d, kmsg)
        ev = {"id": new_id("evd"), "source": body.source.model_dump(), "text": body.text,
              "citations": [c.model_dump() for c in body.citations], "added_at": now_iso()}
        msg.setdefault("evidence", []).append(ev)
        out.update(msg)
        return d

    await service.mutate(sb_id, fn)
    return out


async def import_competitor(sb_id: str, body: CompetitorImport) -> dict[str, Any] | None:
    """경쟁사 분석의 비교 기준을 SB1Q3 `비교 기준` 질의에 붙인다(Q-3 제안: `경쟁사 제안` 선택지 근거)."""
    await repo.require_sb(sb_id)
    out: dict[str, Any] = {}
    names = [c.name for c in body.criteria if c.name][:6]
    comps = [c for c in body.competitors if c][:4]
    evidence = "비교 기준 " + " · ".join(names) + (f" ({' · '.join(comps)})" if comps else "") if names else (body.note or "")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["competitor_import"] = {**body.model_dump(), "at": now_iso()}
        q = next((x for x in d["planning"]["questions"] if x["topic"] == "comparison"), None)
        if q is None and int(d.get("step") or 1) == 1 and d["settings"].get("ready") and len(d["planning"]["questions"]) < 3:
            copy_ = rules.QUESTION_COPY["comparison"]
            q = {"id": new_id("pq"), "order": len(d["planning"]["questions"]) + 1, "topic": "comparison",
                 "topic_label": copy_["topic_label"], "text": copy_["text"], "info": copy_["info"], "select": "single",
                 "order_roles": [], "allow_custom": False, "options": [], "affects": copy_["affects"]}
            d["planning"]["questions"].append(q)
        if q is not None:
            opt = next((o for o in q["options"] if "경쟁사" in o["label"]), None)
            if opt is None:
                opt = {"id": new_id("opt"), "label": "경쟁사 제안", "custom": False}
                q["options"].append(opt)
            opt["hint"] = f"경쟁사 분석 · 기준 {len(names)}개" if names else "경쟁사 분석에서"
            opt["evidence"] = evidence
            opt["recommended"] = True
            out.update(q)
        return d

    await service.mutate(sb_id, fn)
    return out or None
