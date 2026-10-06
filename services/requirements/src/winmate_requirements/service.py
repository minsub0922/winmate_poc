"""정의서 서비스 — 라우터와 워커가 함께 쓰는 동작(생성 · 편집 · 저장 · 버전 · 파일 · 고객 질문 · 링크)."""
from __future__ import annotations

import base64
import copy
import logging
from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import jobs

from . import domain, platform_calls, repo
from .domain import DraftConflict

log = logging.getLogger("winmate.requirements")


def _me() -> tuple[str, str]:
    u = current_user()
    return u.id, u.name


# ── 생성 · 읽기 ─────────────────────────────────────────

async def create(project_id: str | None, form: dict[str, Any] | None) -> dict[str, Any]:
    uid, uname = _me()
    rq_id = new_id("rq")
    doc = domain.new_doc(owner_id=uid, owner_name=uname, project_id=project_id)
    for f, v in (form or {}).items():
        if v is not None and f in domain.FIELDS:
            domain.set_field(doc, f, v, {"kind": "user"}, rev=1)
    doc["id"] = rq_id
    saved = await repo.create_doc(rq_id, doc)
    await platform_calls.sync_index(saved)
    return saved


async def refresh_jobs(doc: dict[str, Any]) -> dict[str, Any]:
    """끝났는데 지워지지 않은 잡(워커가 죽은 경우)을 정리한다."""
    pending = ([doc["active_job"]] if doc.get("active_job") else []) + list(doc.get("queued_jobs") or [])
    if not pending:
        return doc
    dead: set[str] = set()
    for j in pending:
        alive = await platform_calls.job_alive(j["job_id"])
        if alive is False:
            dead.add(j["job_id"])
    if not dead:
        return doc

    def fn(d: dict[str, Any], rev: int) -> None:
        if d.get("active_job") and d["active_job"]["job_id"] in dead:
            d["active_job"] = None
        d["queued_jobs"] = [j for j in d.get("queued_jobs") or [] if j["job_id"] not in dead]
        if not d.get("active_job") and d["queued_jobs"]:
            d["active_job"] = d["queued_jobs"].pop(0)
        for f in d.get("files") or []:
            if f.get("status") == "reading" and f.get("job_id") in dead:
                f["status"] = "failed"
                f["error"] = {"code": "JOB_LOST", "message": "읽지 못했어요"}
        if not d.get("active_job"):
            d["fill_progress"] = None

    doc, _ = await repo.mutate(doc["id"], fn)
    return doc


async def get(rq_id: str) -> dict[str, Any]:
    doc = await repo.require_doc(rq_id)
    return await refresh_jobs(doc)


async def present_doc(doc: dict[str, Any], **extra: Any) -> dict[str, Any]:
    """Requirement 응답 — 진행 중 심층 작성 세션의 질의 번호를 채워서."""
    from . import deep  # 늦은 import — 순환 방지

    return {**domain.present(await deep.enrich_doc(doc)), **extra}


async def list_requirements(*, tab: str, q: str | None, has_version: bool | None, customer: str | None,
                            project_id: str | None, owner: str, limit: int, cursor: str | None) -> tuple[list[dict[str, Any]], str | None]:
    docs = await _filtered(tab=tab, q=q, has_version=has_version, customer=customer, project_id=project_id, owner=owner)
    from . import deep

    offset = _decode_cursor(cursor)
    page = docs[offset: offset + limit]
    nxt = _encode_cursor(offset + limit) if offset + limit < len(docs) else None
    return [domain.present_list_item(await deep.enrich_doc(d)) for d in page], nxt


async def counts(q: str | None, owner: str) -> dict[str, int]:
    docs = await _filtered(tab="all", q=q, has_version=None, customer=None, project_id=None, owner=owner)
    saved = sum(1 for d in docs if domain.list_state(d) == "saved")
    return {"all": len(docs), "in_progress": len(docs) - saved, "saved": saved}


async def _filtered(*, tab: str, q: str | None, has_version: bool | None, customer: str | None,
                    project_id: str | None, owner: str) -> list[dict[str, Any]]:
    uid, _ = _me()
    owner_id = None if owner == "all" else (uid if owner in ("me", "", None) else owner)
    docs = await repo.list_docs(owner_id)
    out = []
    ql = (q or "").strip().lower()
    cl = (customer or "").strip().lower()
    for d in docs:
        state = domain.list_state(d)
        if tab == "in_progress" and state not in domain.IN_PROGRESS_STATES:
            continue
        if tab == "saved" and state != "saved":
            continue
        if has_version is True and d.get("saved_version", 0) < 1:
            continue
        if has_version is False and d.get("saved_version", 0) >= 1:
            continue
        if ql and ql not in domain.search_blob(d):
            continue
        if cl and cl not in (domain.field_value(d, "customer_name") or "").lower():
            continue
        if project_id and d.get("project_id") != project_id:
            continue
        out.append(d)
    out.sort(key=lambda d: (d.get("updated_at") or "", d["id"]), reverse=True)
    return out


def _encode_cursor(n: int) -> str:
    return base64.urlsafe_b64encode(str(n).encode()).decode()


def _decode_cursor(c: str | None) -> int:
    if not c:
        return 0
    try:
        return max(0, int(base64.urlsafe_b64decode(c.encode()).decode()))
    except Exception:  # noqa: BLE001
        return 0


# ── 작업본 편집 ─────────────────────────────────────────

async def patch_draft(rq_id: str, base_revision: int | None, ops: list[dict[str, Any]]) -> dict[str, Any]:
    if not ops:
        return await present_doc(await get(rq_id), skipped_ops=[])

    def fn(doc: dict[str, Any], rev: int) -> list[dict[str, Any]]:
        return domain.apply_ops(doc, ops, base_revision=base_revision, rev=rev)

    try:
        doc, skipped = await repo.mutate(rq_id, fn)
    except DraftConflict as exc:
        cur = await repo.require_doc(rq_id)
        raise ApiError(409, "REVISION_CONFLICT", "다른 곳에서 먼저 고친 칸이 있어요. 다시 읽고 적용해 주세요",
                       {"current": await present_doc(cur), "op_index": exc.index, "op": exc.op, "target": exc.target}) from exc
    await platform_calls.sync_index(doc)
    from . import shorts  # 늦은 import — 순환 방지

    await shorts.maybe_enqueue(doc)
    return await present_doc(doc, skipped_ops=skipped)


# ── 저장 · 버전 ─────────────────────────────────────────

async def _ensure_not_filling(doc: dict[str, Any]) -> dict[str, Any]:
    doc = await refresh_jobs(doc)
    aj = doc.get("active_job")
    if (aj and aj.get("kind") == "rq.fill") or doc.get("queued_jobs"):
        raise ApiError(409, "JOB_RUNNING", "파일로 폼을 채우는 중이에요. 끝난 뒤 다시 시도해 주세요",
                       {"job_id": (aj or {}).get("job_id")})
    return doc


async def save(rq_id: str, reason: str | None, note: str | None, *, check_job: bool = True) -> tuple[int, bool, dict[str, Any]]:
    doc = await repo.require_doc(rq_id)
    if check_job:
        doc = await _ensure_not_filling(doc)
    if domain.is_form_empty(doc):
        raise ApiError(422, "EMPTY_FORM", "폼이 비어 있어요. 한 칸 이상 채운 뒤 저장해 주세요")
    from . import shorts

    await shorts.ensure_shorts(rq_id, timeout=8.0)
    doc = await repo.require_doc(rq_id)
    if doc.get("saved_version", 0) == 0 and not doc.get("project_id"):
        name = domain.field_value(doc, "project_name") or domain.title_of(doc) or "새 요구사항"
        pid = await platform_calls.create_project(name, domain.field_value(doc, "customer_name"))
        if pid:
            def set_pid(d: dict[str, Any], rev: int) -> None:
                if not d.get("project_id"):
                    d["project_id"] = pid
            await repo.mutate(rq_id, set_pid)
    uid, uname = _me()
    reason = reason or ("direct" if doc.get("saved_version", 0) == 0 else "edit")
    prev_snapshot = None
    if doc.get("saved_version", 0) > 0:
        pv = await repo.get_version(rq_id, doc["saved_version"])
        prev_snapshot = (pv or {}).get("snapshot")

    def fn(d: dict[str, Any], rev: int) -> tuple[int, bool]:
        domain.cleanup_for_save(d)
        h = domain.content_hash(d)
        cur = d.get("saved_version", 0)
        if cur > 0 and h == d.get("saved_hash"):
            return cur, False
        n = cur + 1
        snap = domain.snapshot(d)
        repo.put_version_sync(rq_id, n, _version_body(d, n, snap, reason=reason, note=note, uid=uid, uname=uname,
                                                    prev=prev_snapshot))
        d["saved_version"] = n
        d["saved_hash"] = h
        d["saved_at"] = now_iso()
        return n, True

    doc, (n, created) = await repo.mutate(rq_id, fn)
    await platform_calls.sync_index(doc)
    return n, created, doc


def _version_body(d: dict[str, Any], n: int, snap: dict[str, Any], *, reason: str, note: str | None, uid: str,
                  uname: str, prev: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "version": n, "created_at": now_iso(), "created_by": {"id": uid, "name": uname}, "reason": reason, "note": note,
        "summary": domain.summary_of(d), "change_count": domain.snapshot_change_count(prev, snap),
        "title": domain.title_of(d), "project_id": d.get("project_id"),
        "project_name": domain.field_value(d, "project_name"), "customer_name": domain.field_value(d, "customer_name"),
        "final_audience": domain.field_value(d, "final_audience"), "item_count": domain.item_count(d),
        "keyman_count": domain.keyman_count(d), "open_question_count": len(domain.open_questions(d)), "snapshot": snap,
    }


async def get_version(rq_id: str, n: str | int) -> dict[str, Any]:
    doc = await repo.require_doc(rq_id)
    latest = doc.get("saved_version", 0)
    if isinstance(n, str):
        if n == "latest":
            num = latest
        else:
            try:
                num = int(n)
            except ValueError:
                raise ApiError(422, "VALIDATION_FAILED", "버전은 숫자 또는 latest 여야 해요") from None
    else:
        num = n
    if num < 1:
        raise ApiError(404, "VERSION_NOT_FOUND", "저장된 버전이 없어요", {"version": num})
    v = await repo.get_version(rq_id, num)
    if v is None:
        raise ApiError(404, "VERSION_NOT_FOUND", f"v{num}을(를) 찾을 수 없어요", {"version": num})
    return {**v, "requirement_id": rq_id, "version": v.get("n", num), "latest_version": latest}


async def list_versions(rq_id: str) -> list[dict[str, Any]]:
    await repo.require_doc(rq_id)
    items = await repo.list_versions(rq_id)
    return [{"version": v.get("n"), "created_at": v.get("created_at"), "created_by": v.get("created_by"),
             "reason": v.get("reason"), "note": v.get("note"), "summary": v.get("summary"),
             "change_count": v.get("change_count", 0)} for v in items]


async def restore(rq_id: str, n: int) -> int:
    doc = await _ensure_not_filling(await repo.require_doc(rq_id))
    v = await repo.get_version(rq_id, n)
    if v is None:
        raise ApiError(404, "VERSION_NOT_FOUND", f"v{n}을(를) 찾을 수 없어요", {"version": n})
    old_form = copy.deepcopy(v["snapshot"]["form"])
    old_form.pop("author_note_internal", None)
    uid, uname = _me()
    prev = None
    if doc.get("saved_version", 0) > 0:
        pv = await repo.get_version(rq_id, doc["saved_version"])
        prev = (pv or {}).get("snapshot")

    def fn(d: dict[str, Any], rev: int) -> int:
        form = copy.deepcopy(old_form)
        form["weights_rev"] = rev
        for f in domain.FIELDS:
            form[f]["rev"] = rev
        for k in form["keymen"]:
            k["rev"] = rev
            for it in k["items"]:
                it["rev"] = rev
                it.pop("needs_confirmation", None)
        d["form"] = form
        # 되살린 항목 code 가 이후 새 항목과 겹치지 않도록 순번은 그대로(재사용 안 함)
        n_new = d.get("saved_version", 0) + 1
        snap = domain.snapshot(d)
        repo.put_version_sync(rq_id, n_new, _version_body(d, n_new, snap, reason="restore", note=f"v{n} 되돌리기",
                                                        uid=uid, uname=uname, prev=prev))
        d["saved_version"] = n_new
        d["saved_hash"] = domain.content_hash(d)
        d["saved_at"] = now_iso()
        return n_new

    doc, n_new = await repo.mutate(rq_id, fn)
    await platform_calls.sync_index(doc)
    return n_new


async def diff(rq_id: str, a: int, b: int) -> dict[str, Any]:
    await repo.require_doc(rq_id)
    va = await repo.get_version(rq_id, a)
    vb = await repo.get_version(rq_id, b)
    if va is None or vb is None:
        raise ApiError(404, "VERSION_NOT_FOUND", "비교할 버전을 찾을 수 없어요", {"from": a, "to": b})
    return {"from_version": a, "to_version": b, "changes": domain.diff_snapshots(va["snapshot"], vb["snapshot"])}


async def share(rq_id: str) -> dict[str, Any]:
    doc = await repo.require_doc(rq_id)
    route = f"/requirements/{rq_id}"
    try:
        link = await platform_calls.create_share(rq_id, route, domain.title_of(doc) or "요구사항 정의서")
    except ApiError as exc:
        raise ApiError(503, "SHARE_UNAVAILABLE", "공유 링크를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요",
                       {"upstream": exc.code}) from exc
    return {"url": link.get("url") or f"/share/{link.get('token')}", "token": link.get("token")}


# ── 파일로 채우기(§6.2) ─────────────────────────────────

async def add_files(rq_id: str, file_ids: list[str]) -> dict[str, Any]:
    doc = await repo.require_doc(rq_id)
    metas = []
    for fid in dict.fromkeys(file_ids):
        meta = await platform_calls.file_meta(fid)
        label = domain.file_label_for(meta.get("name", ""), meta.get("kind"))
        if label is None or meta.get("kind") in ("xlsx", "image", "zip", "svg"):
            raise ApiError(422, "UNSUPPORTED_FILE_TYPE", "PPTX · PDF · DOCX · TXT · 메일만 넣을 수 있어요",
                           {"file_id": fid, "name": meta.get("name"), "kind": meta.get("kind")})
        metas.append((fid, meta, label))
    doc = await refresh_jobs(doc)
    job_id = new_id("job")
    now = now_iso()

    def fn(d: dict[str, Any], rev: int) -> None:
        existing = {f["file_id"] for f in d.get("files") or []}
        for fid, meta, label in metas:
            entry = {"file_id": fid, "name": meta.get("name") or fid, "type_label": label, "status": "reading",
                     "filled_count": 0, "doc_kind": None, "error": None, "job_id": job_id, "added_at": now}
            if fid in existing:
                d["files"] = [entry if f["file_id"] == fid else f for f in d["files"]]
            else:
                d["files"].append(entry)
        ref = {"job_id": job_id, "kind": "rq.fill"}
        if d.get("active_job"):
            d.setdefault("queued_jobs", []).append(ref)
        else:
            d["active_job"] = ref
            d["fill_progress"] = {"job_id": job_id, "filled": 0, "total": 0}

    doc, _ = await repo.mutate(rq_id, fn)
    await jobs().enqueue("requirements", "rq.fill", {"requirement_id": rq_id, "file_ids": [m[0] for m in metas]},
                         title=f"{domain.title_of(doc) or '새 요구사항'} · 파일로 채우기", ref=rq_id,
                         project_id=doc.get("project_id"), job_id=job_id)
    await platform_calls.sync_index(doc)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "requirement", "id": rq_id}}


async def from_files(file_ids: list[str], customer_hint: str | None, project_id: str | None) -> dict[str, Any]:
    form = {"customer_name": customer_hint} if customer_hint else None
    doc = await create(project_id, None)
    if form:
        # 힌트는 사람이 준 값이 아니므로 파일 값이 있으면 그쪽을 쓴다(대체 값으로 남김)
        def fn(d: dict[str, Any], rev: int) -> None:
            domain.set_field(d, "customer_name", customer_hint, {"kind": "file", "file_label": None, "quote": None,
                                                                 "service": "hint"}, rev=rev)
        await repo.mutate(doc["id"], fn)
    return await add_files(doc["id"], file_ids)


async def remove_file(rq_id: str, file_id: str, rollback: bool) -> dict[str, Any]:
    doc = await repo.require_doc(rq_id)
    if not any(f["file_id"] == file_id for f in doc.get("files") or []):
        raise ApiError(404, "FILE_NOT_FOUND", "이 정의서에 그 파일이 없어요", {"file_id": file_id})

    def fn(d: dict[str, Any], rev: int) -> None:
        snap: dict[str, Any] = {"file": next(f for f in d["files"] if f["file_id"] == file_id), "fields": {},
                                "keymen": [], "items": [], "at": now_iso()}
        d["files"] = [f for f in d["files"] if f["file_id"] != file_id]
        if rollback:
            _rollback_file(d, file_id, rev, snap)
        d.setdefault("file_snapshots", {})[file_id] = snap

    doc, _ = await repo.mutate(rq_id, fn)
    await platform_calls.sync_index(doc)
    return doc


def _from_file(src: dict[str, Any] | None, file_id: str) -> bool:
    return bool(src) and src.get("kind") == "file" and src.get("file_id") == file_id


def _rollback_file(d: dict[str, Any], file_id: str, rev: int, snap: dict[str, Any]) -> None:
    """그 파일에서 와서 아직 사람이 고치지 않은 값 · 항목 · 키맨을 지운다(§4.6 빼기)."""
    remaining = {f["file_id"] for f in d.get("files") or []}
    for f in domain.FIELDS:
        fld = d["form"][f]
        fld["alternatives"] = [a for a in fld.get("alternatives") or [] if not _from_file(a.get("source"), file_id)]
        if _from_file(fld.get("source"), file_id):
            snap["fields"][f] = copy.deepcopy(fld)
            alt = next((a for a in fld["alternatives"] if (a.get("source") or {}).get("file_id") in remaining), None)
            if alt:
                fld["alternatives"].remove(alt)
                fld["value"], fld["source"] = alt["value"], alt["source"]
            else:
                fld["value"], fld["source"] = None, None
            fld["rev"] = rev
            fld["updated_at"] = now_iso()
    removed_keymen = []
    for k in list(domain.keymen(d)):
        for idx, it in enumerate(list(k["items"])):
            if _from_file(it.get("source"), file_id):
                snap["items"].append({"keyman_id": k["id"], "index": idx, "item": copy.deepcopy(it)})
                k["items"].remove(it)
        for j, it in enumerate(k["items"]):
            it["order"] = j
        if _from_file(k.get("source"), file_id) and not k["items"]:
            removed_keymen.append(k)
    for k in removed_keymen:
        snap["keymen"].append(copy.deepcopy(k))
        domain.remove_keyman(d, k["id"])
    if removed_keymen:
        d["form"]["weights_rev"] = rev


async def restore_file(rq_id: str, file_id: str) -> dict[str, Any]:
    """'되돌리기' — 뺀 파일과 그 파일에서 지운 값을 재추출 없이 되살린다."""
    doc = await repo.require_doc(rq_id)
    if file_id not in (doc.get("file_snapshots") or {}):
        raise ApiError(404, "FILE_NOT_FOUND", "되돌릴 파일이 없어요", {"file_id": file_id})

    def fn(d: dict[str, Any], rev: int) -> None:
        snap = (d.get("file_snapshots") or {}).pop(file_id, None)
        if not snap:
            return
        if not any(f["file_id"] == file_id for f in d["files"]):
            d["files"].append(snap["file"])
        for f, fld in snap.get("fields", {}).items():
            cur = d["form"][f]
            if not cur.get("value") or (cur.get("source") or {}).get("kind") == "file":
                fld["rev"] = rev
                d["form"][f] = fld
        added = []
        for k in snap.get("keymen", []):
            if domain.find_keyman(d, k["id"]) is None:
                k = {**k, "items": [], "rev": rev}
                domain.keymen(d).append(k)
                added.append(k["id"])
        for i, k in enumerate(domain.keymen(d)):
            k["order"] = i
        for entry in snap.get("items", []):
            km = domain.find_keyman(d, entry["keyman_id"])
            if km is None or domain.find_item(d, entry["item"]["id"])[1] is not None:
                continue
            domain.insert_item(km, {**entry["item"], "rev": rev}, index=entry["index"])
        if added:
            domain.rebalance(d, added_ids=added)
            d["form"]["weights_rev"] = rev

    doc, _ = await repo.mutate(rq_id, fn)
    await platform_calls.sync_index(doc)
    return doc


# ── 고객 질문(§6.6) ─────────────────────────────────────

def new_question(rq_id: str, *, text: str, short_label: str | None, keyman_id: str | None,
                 target: dict[str, Any] | None, origin: dict[str, Any]) -> dict[str, Any]:
    now = now_iso()
    return {"id": new_id("cq"), "requirement_id": rq_id, "text": text.strip()[:120],
            "short_label": (short_label or "").strip()[:24] or None, "keyman_id": keyman_id, "target": target,
            "origin": origin, "status": "open", "include_in_mail": True, "answer": None, "created_at": now, "updated_at": now}


def _origin_in(o: dict[str, Any]) -> dict[str, Any]:
    kind = o.get("kind")
    svc = (o.get("service") or "").lower()
    feat = (o.get("feature") or "").upper()
    if not kind:
        if svc == "storyboard" or feat == "SB":
            kind = "storyboard"
        elif svc == "proposal" or feat == "PR":
            kind = "proposal"
        else:
            kind = "manual"
    service = o.get("service") or {"storyboard": "storyboard", "proposal": "proposal"}.get(kind)
    return {"kind": kind, "service": service, "ref_id": o.get("ref_id"), "place_label": o.get("place_label"),
            "confirm_item_id": o.get("confirm_item_id")}


async def add_question(rq_id: str, body: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Storyboard · 제안서 · 수동 질문 추가. 같은 origin.ref_id + 같은 text 는 기존 것(멱등)."""
    await repo.require_doc(rq_id)
    origin = _origin_in(body.get("origin") or {})
    text = body["text"].strip()

    def fn(d: dict[str, Any], rev: int) -> tuple[dict[str, Any], bool]:
        for q in d.get("questions") or []:
            if (q["text"].strip() == text and (q.get("origin") or {}).get("ref_id") == origin.get("ref_id")
                    and (q.get("origin") or {}).get("kind") == origin["kind"]):
                return q, False
        target = body.get("target")
        if target and target.get("kind") == "item" and domain.find_item(d, target["id"])[1] is None:
            target = None
        keyman_id = body.get("keyman_id")
        if keyman_id and domain.find_keyman(d, keyman_id) is None:
            keyman_id = None
        if not keyman_id and target and target.get("kind") == "item":
            km, _ = domain.find_item(d, target["id"])
            keyman_id = km["id"] if km else None
        q = new_question(rq_id, text=text, short_label=body.get("short_label"), keyman_id=keyman_id, target=target,
                         origin=origin)
        d.setdefault("questions", []).append(q)
        return q, True

    doc, (q, created) = await repo.mutate(rq_id, fn)
    if created:
        await platform_calls.sync_index(doc)
    return q, created


async def patch_question(rq_id: str, qid: str, body: dict[str, Any]) -> dict[str, Any]:
    def fn(d: dict[str, Any], rev: int) -> dict[str, Any]:
        q = next((q for q in d.get("questions") or [] if q["id"] == qid), None)
        if q is None:
            raise repo.not_found("고객 질문", qid)
        if body.get("include_in_mail") is not None:
            q["include_in_mail"] = bool(body["include_in_mail"])
        if body.get("status") == "dismissed" and q["status"] == "open":
            q["status"] = "dismissed"
        elif body.get("status") == "open" and q["status"] == "dismissed":
            q["status"] = "open"
        q["updated_at"] = now_iso()
        return q

    doc, q = await repo.mutate(rq_id, fn)
    await platform_calls.sync_index(doc)
    return q


async def list_questions(rq_id: str, status: str) -> list[dict[str, Any]]:
    doc = await repo.require_doc(rq_id)
    qs = doc.get("questions") or []
    if status != "all":
        qs = [q for q in qs if q["status"] == status]
    return sorted(qs, key=lambda q: q["created_at"])


# ── 쓰는 곳 링크(§6.8) ──────────────────────────────────

async def upsert_link(rq_id: str, service: str, ref_id: str, body: dict[str, Any]) -> dict[str, Any]:
    await repo.require_doc(rq_id)
    key = repo.link_key(rq_id, service, ref_id)
    cur = await repo.get("links", key)
    now = now_iso()
    link = {
        "requirement_id": rq_id, "service": service, "ref_id": ref_id,
        "title": body.get("title") if body.get("title") is not None else (cur or {}).get("title"),
        "route": body.get("route") if body.get("route") is not None else (cur or {}).get("route"),
        "rq_version": int(body["rq_version"]), "depends_on": body.get("depends_on") or [],
        "sync_state": (cur or {}).get("sync_state", "up_to_date"), "pending_version": (cur or {}).get("pending_version"),
        "created_at": (cur or {}).get("created_at") or now, "updated_at": now,
    }
    pv = link.get("pending_version")
    if link["sync_state"] == "pending" and (pv is None or link["rq_version"] >= pv):
        link["sync_state"] = "up_to_date"
        link["pending_version"] = None
    saved = await repo.put("links", key, link)
    return _link_out(saved)


def _link_out(d: dict[str, Any]) -> dict[str, Any]:
    return {k: d.get(k) for k in ("requirement_id", "service", "ref_id", "title", "route", "rq_version", "depends_on",
                                  "sync_state", "pending_version", "created_at", "updated_at")}


async def list_links(rq_id: str) -> list[dict[str, Any]]:
    await repo.require_doc(rq_id)
    items = await repo.find("links", {"requirement_id": rq_id})
    return [_link_out(x) for x in items]


async def delete_link(rq_id: str, service: str, ref_id: str) -> None:
    await repo.require_doc(rq_id)
    await repo.delete("links", repo.link_key(rq_id, service, ref_id))
