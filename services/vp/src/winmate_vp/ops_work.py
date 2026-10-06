"""작업 · 재료 · 되묻기 · 구조(05-vp.md §6.1 ~ §6.3) — REST 처리기 본체."""
from __future__ import annotations

import copy
import logging
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import TERMINAL, jobs

from . import catalog, config, decide, kbx, materials, models, repo, service, signals, sources

log = logging.getLogger("winmate.vp.ops")


# ── 목록 ──────────────────────────────────────────────────

async def list_vps(*, status: str | None, industry: str | None, q: str | None, since_days: int | None, archived: bool,
                   limit: int, cursor: str | None) -> dict[str, Any]:
    from datetime import datetime, timedelta, timezone
    owner = service.owner_now()["user_id"]
    docs = await repo.list_vps({"owner_id": owner, "archived": archived})
    since = None
    if since_days:
        since = datetime.now(timezone.utc) - timedelta(days=int(since_days))
    rows = []
    for d in docs:
        d = service.derive(d)
        if since:
            try:
                if datetime.fromisoformat(str(d.get("updated_at")).replace("Z", "+00:00")) < since:
                    continue
            except ValueError:
                pass
        rows.append(d)
    counts = {"all": len(rows), "ask": 0, "check": 0, "run": 0, "done": 0, "draft": 0}
    for d in rows:
        counts[d["ui_status"]] = counts.get(d["ui_status"], 0) + 1
    out = rows
    if industry:
        codes = {c.strip() for c in industry.split(",") if c.strip()}
        out = [d for d in out if ((d.get("industry") or {}).get("code") or "GEN") in codes]
    if q:
        qq = q.strip().lower()
        codes = catalog.search_codes(q)
        def hit(d: dict[str, Any]) -> bool:
            if qq in (d.get("title") or "").lower() or qq in (d.get("customer_name") or "").lower():
                return True
            chips = {catalog.norm(c["t"].split(" ")[0]) for c in service.layout_chips(d)}
            return bool(codes & chips)
        out = [d for d in out if hit(d)]
    if status:
        sts = {s.strip() for s in status.split(",") if s.strip()}
        out = [d for d in out if d["ui_status"] in sts]
    out.sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    start = int(cursor or 0) if (cursor or "").isdigit() else 0
    page = out[start:start + limit]
    nxt = str(start + limit) if start + limit < len(out) else None
    return {"items": [service.list_item(d) for d in page], "next_cursor": nxt, "counts": counts,
            "total_label": f"작업 {len(rows)}개 · 최근 {since_days or config.th('list_days')}일"}


# ── 만들기 · 고치기 ─────────────────────────────────────────

async def _resolve_sources(refs: list[dict[str, Any]], existing: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    out = []
    known = {(s["kind"], s["ref_id"]): s for s in existing or []}
    for i, r in enumerate(refs, 1):
        key = (r["kind"], r["ref_id"])
        if key in known and known[key].get("cand") is not None:
            s = dict(known[key])
            s["connected"] = bool(r.get("connected", True))
            s["status"] = "connected" if s["connected"] else "recommended"
            out.append(s)
            continue
        data = await sources.load(r["kind"], r["ref_id"], idx=i)
        out.append({
            "id": new_id("vsr"), "kind": r["kind"], "ref_id": r["ref_id"], "title": r.get("title") or data.get("title") or r["ref_id"],
            "kind_label": sources.KIND_LABEL.get(r["kind"], r["kind"]), "connected": bool(r.get("connected", True)),
            "status": "connected" if r.get("connected", True) else "recommended", "gives": data.get("gives") or {},
            "fetched_version": data.get("version"), "fetched_at": now_iso(), "cand": data.get("candidates") or [],
            "industry": data.get("industry"), "customer": data.get("customer"), "project_id": data.get("project_id"),
            "error": data.get("error"), "extra": _slim_extra(r["kind"], data.get("extra") or {}),
        })
    return out


def _slim_extra(kind: str, extra: dict[str, Any]) -> dict[str, Any]:
    if kind == "case":
        dep = extra.get("deployment") or {}
        return {"deployment": {k: dep.get(k) for k in ("id", "title", "url", "vertical", "products", "needs", "spaces", "quote", "date")},
                "kpis": extra.get("kpis") or []}
    if kind == "storyboard":
        return {"kms": extra.get("kms") or [], "rq_ref": extra.get("rq_ref")}
    return extra


def apply_sources(d: dict[str, Any], srcs: list[dict[str, Any]], pack_status: dict[str, str] | None = None) -> None:
    """연결 자료 반영 — 미리보기 재료(커버리지) · 업종 상속 · 고객사 · 프로젝트."""
    keep = {(s["kind"], s["ref_id"]) for s in srcs}
    d["sources"] = [s for s in d.get("sources") or [] if (s["kind"], s["ref_id"]) not in keep] + srcs
    conn = [s for s in d["sources"] if s.get("connected")]
    cands = [c for s in conn for c in s.get("cand") or []]
    f = d.setdefault("facts", {})
    f["preview_materials"] = materials.preview_items(cands)
    f["preview_facts"] = materials.preview_facts(cands)
    if not d.get("customer_name"):
        cust = next((s.get("customer") for s in conn if s.get("customer")), None)
        if cust:
            d["customer_name"] = cust
    if not d.get("project_id"):
        d["project_id"] = next((s.get("project_id") for s in conn if s.get("project_id")), None)
    ind = d.get("industry") or {}
    if ind.get("mode") != "pin":
        inh = next((s["industry"] for k in ("mi", "storyboard", "vp", "requirements") for s in conn
                    if s["kind"] == k and s.get("industry")), None)
        if inh:
            d["industry"] = decide.decide_industry(inherited=inh, pack_status=pack_status)
        elif ind.get("source") in ("mi", "storyboard", "vp", "requirements"):
            d["industry"] = None


async def create(body: models.CreateVP) -> dict[str, Any]:
    vp_id = new_id("vp")
    owner = service.owner_now()
    target = body.target_proposal.model_dump() if body.target_proposal else None
    doc = service.new_doc(vp_id, start=body.start, owner=owner, customer_name=(body.customer_name or "").strip() or None,
                          title=body.title, project_id=body.project_id, target=target, auto_answer=body.auto_answer, note=body.note)
    if target and target.get("title"):
        doc["linked_proposal"] = {"id": target.get("proposal_id"), "title": target["title"]}
    pack = await repo.pack_status_map()
    if body.source_refs:
        srcs = await _resolve_sources([{**r.model_dump(), "connected": True} for r in body.source_refs])
        apply_sources(doc, srcs, pack)
    elif doc.get("customer_name"):
        srcs = await _autolink_sources(doc)
        if srcs:
            apply_sources(doc, srcs, pack)
    doc = service.derive(doc)
    doc = await repo.create_vp(vp_id, doc)
    doc = service.derive(doc)
    await service.index(doc)
    return doc


async def _found(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """같은 고객사의 최근 작업(SB · MI · RQ · 이전 VP) + KB:D1 유관 사례 1."""
    cust = doc.get("customer_name") or ""
    q = sources.short_customer(cust)
    out: list[dict[str, Any]] = []
    if not q:
        return out
    for feat, kind in (("SB", "storyboard"), ("MI", "mi"), ("RQ", "requirements"), ("VP", "vp")):
        items = await sources.workspace_items(feat, q, limit=10)
        items = [i for i in items if i.get("item_id") != doc["id"]]
        if kind == "vp":  # 이전 가치 제안은 재료가 정리된 것만(빈 초안은 추천하지 않는다)
            ready = []
            for i in items:
                other = await repo.get_vp(i["item_id"])
                if other and other.get("status") != "archived" and (other.get("generated") or other.get("materials_ready")):
                    ready.append(i)
            items = ready
        if doc.get("project_id"):
            same = [i for i in items if i.get("project_id") == doc["project_id"]]
            items = same or items
        if not items:
            continue
        it = sorted(items, key=lambda x: x.get("updated_at") or "", reverse=True)[0]
        out.append({"kind": kind, "ref_id": it["item_id"], "title": it.get("title") or it["item_id"],
                    "connected": kind in ("storyboard", "mi", "requirements")})
    ind = doc.get("industry") or {}
    vertical = ind.get("kr_vertical_id")
    text = " ".join(x for x in (cust, doc.get("note") or "", " ".join(o["title"] for o in out)) if x)
    cases = await kbx.similar_cases(vertical=vertical, text=text, limit=3)
    if cases:
        c = cases[0]
        out.append({"kind": "case", "ref_id": c["id"], "title": c.get("title") or c["id"], "connected": False})
    return out


async def _autolink_sources(doc: dict[str, Any]) -> list[dict[str, Any]]:
    found = await _found(doc)
    doc.setdefault("facts", {})["autolinked"] = True
    return await _resolve_sources(found) if found else []


async def patch(vp_id: str, body: models.PatchVP) -> dict[str, Any]:
    pack = await repo.pack_status_map()
    cur = await repo.require_vp(vp_id)
    first_customer = bool(body.customer_name and not cur.get("customer_name") and not (cur.get("facts") or {}).get("autolinked"))
    srcs: list[dict[str, Any]] = []
    if first_customer:
        tmp = {**cur, "customer_name": body.customer_name}
        srcs = await _autolink_sources(tmp)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if body.title is not None:
            d["title"] = body.title.strip() or d["title"]
            d["title_auto"] = False
        if body.customer_name is not None:
            d["customer_name"] = body.customer_name.strip() or None
            if d.get("title_auto", True):
                d["title"] = service.default_title(d["customer_name"], (d.get("facts") or {}).get("topic"))
        if body.note is not None:
            d["note"] = body.note
        if body.auto_answer is not None:
            d["auto_answer"] = body.auto_answer
        if body.industry is not None:
            code = body.industry.code
            if code != "GEN" and code not in config.INDUSTRY_CODES:
                raise ApiError(422, "INVALID_INDUSTRY", f"모르는 업종 코드예요: {code}")
            d["industry"] = decide.decide_industry(pinned=code, pack_status=pack)
        elif body.clear_industry:
            d["industry"] = None
            apply_sources(d, [], pack)
        if body.target_proposal is not None:
            d["target_proposal"] = body.target_proposal.model_dump()
            if body.target_proposal.title:
                d["linked_proposal"] = {"id": body.target_proposal.proposal_id, "title": body.target_proposal.title}
        if first_customer:
            d.setdefault("facts", {})["autolinked"] = True
            if srcs:
                apply_sources(d, srcs, pack)
        if d.get("plan") and (body.industry is not None or body.target_proposal is not None or body.clear_industry):
            service.replan(d, pack)
        return d
    return await service.mutate(vp_id, fn)


async def clone(vp_id: str, body: models.CloneVP) -> dict[str, Any]:
    """복제 — 고정한 시트는 그대로 두고 나머지만 다시 고른다(VPC 11). 새 작업 → VP2."""
    src = await repo.require_vp(vp_id)
    pack = await repo.pack_status_map()
    new = service.new_doc(new_id("vp"), start="clone", owner=service.owner_now(), customer_name=body.customer_name.strip(),
                          project_id=src.get("project_id"), target=None, note=src.get("note"))
    orig = src.get("customer_name") or src.get("title") or ""
    orig_short = sources.short_customer(orig)
    new["title"] = f"{body.customer_name.strip()} ({orig_short} 복제)"
    new["title_auto"] = False
    new["clone_from"] = vp_id
    for k in ("materials", "facts", "attachments"):
        new[k] = copy.deepcopy(src.get(k) or ([] if k != "facts" else {}))
    new["materials_ready"] = bool(new["materials"])
    srcs = [{**s, "id": new_id("vsr")} for s in src.get("sources") or []]
    new["sources"] = srcs
    pins = {s["role"]: s["layout"]["code"] for s in src.get("sheets") or [] if s.get("pinned") and s.get("kind", "main") == "main"}
    if body.keep_pinned:
        new["inherited_pins"] = pins
    ind = src.get("industry") or {}
    if body.industry:
        new["industry"] = decide.decide_industry(pinned=body.industry.code, pack_status=pack)
    elif ind.get("code"):
        new["industry"] = decide.decide_industry(inherited={"code": ind["code"], "source": "vp", "label": "복제 원본"}, pack_status=pack)
    for q in new.get("questions") or []:
        q["status"] = "defaulted"
    new["decisions"] = [service.stamp_decision(4, f"복제 → 고정 {len(pins)}장은 그대로 · 나머지 다시 고름", "pin" if pins else "auto")]
    service.replan(new, pack)
    new = service.derive(new)
    doc = await repo.create_vp(new["id"], new)
    doc = service.derive(doc)
    await service.index(doc)
    return doc


async def archive(vp_id: str) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["archived"] = True
        return d
    await service.mutate(vp_id, fn)
    from winmate_common.platform import unregister_item
    await unregister_item(vp_id)


# ── 연결 자료 · 첨부 ────────────────────────────────────────

async def source_candidates(vp_id: str) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    have = {(s["kind"], s["ref_id"]): s for s in doc.get("sources") or []}
    found = await _found(doc) if doc.get("customer_name") else []
    items = []
    for s in doc.get("sources") or []:
        items.append({**s, "recommended": not s.get("connected")})
    extra = [f for f in found if (f["kind"], f["ref_id"]) not in have]
    if extra:
        resolved = await _resolve_sources([{**f, "connected": False} for f in extra])
        for r in resolved:
            items.append({**r, "status": "recommended", "connected": False, "recommended": True})
    n = len(items)
    label = f"같은 고객사의 최근 작업에서 {n}개 찾음" if n else "아직 없어요"
    order = {"storyboard": 0, "mi": 1, "requirements": 2, "vp": 3, "case": 4}
    items.sort(key=lambda s: (order.get(s["kind"], 9)))
    return {"found_label": label, "items": items}


async def put_sources(vp_id: str, body: models.PutSources) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    pack = await repo.pack_status_map()
    srcs = await _resolve_sources([s.model_dump() for s in body.sources], doc.get("sources"))

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        apply_sources(d, srcs, pack)
        return d
    return await service.mutate(vp_id, fn)


def guess_kind(filename: str, mime: str) -> str:
    n = (filename or "").lower()
    if (mime or "").startswith("image/") or n.endswith((".jpg", ".jpeg", ".png", ".heic", ".webp")):
        return "customer_photo"
    if "견적" in n or "quote" in n or "estimate" in n:
        return "quote"
    if "회의" in n or "meeting" in n or "minutes" in n or "메모" in n:
        return "meeting_notes"
    if "rfp" in n or "제안요청" in n or "요청서" in n or "과업" in n:
        return "rfp"
    return "other"


async def add_attachment(vp_id: str, body: models.AddAttachment) -> tuple[dict[str, Any], str | None]:
    await repo.require_vp(vp_id)
    try:
        meta = await ServiceClient("files").get(f"/v1/files/{body.file_id}")
    except ApiError as exc:
        if exc.status == 404:
            raise ApiError(404, "NOT_FOUND", f"파일을 찾을 수 없어요: {body.file_id}") from exc
        raise
    kind = body.kind or guess_kind(meta.get("name") or "", meta.get("mime") or "")
    att = {"id": new_id("vat"), "file_id": body.file_id, "filename": meta.get("name") or body.file_id, "kind": kind,
           "detected_kind": None, "confidential": True, "status": "pending", "summary": "", "mime": meta.get("mime"),
           "origin": "user", "created_at": now_iso()}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d.setdefault("attachments", []).append(att)
        if kind == "quote":
            d.setdefault("facts", {}).setdefault("quote", {}).update({"attached": True, "source": "attached", "file_id": body.file_id})
        return d
    doc = await service.mutate(vp_id, fn)
    job_id = None
    if kind == "customer_photo" and doc.get("generated"):
        job_id = await service.enqueue(vp_id, "vp.images", {"op": "customer_photo", "attachment_id": att["id"]}, doc=doc)
    return att, job_id


async def delete_attachment(vp_id: str, att_id: str) -> None:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        before = len(d.get("attachments") or [])
        d["attachments"] = [a for a in d.get("attachments") or [] if a["id"] != att_id]
        if len(d["attachments"]) == before:
            raise ApiError(404, "NOT_FOUND", f"첨부를 찾을 수 없어요: {att_id}")
        if not any(a.get("kind") == "quote" for a in d["attachments"]):
            (d.get("facts") or {}).pop("quote", None)
        return d
    await service.mutate(vp_id, fn)


# ── 재료 잡 · 정리 · 되묻기 ──────────────────────────────────

async def collect(vp_id: str, body: models.CollectBody | None) -> str:
    doc = await repo.require_vp(vp_id)
    aj = doc.get("active_job") or {}
    if aj and aj.get("status") == "awaiting_input" and aj.get("kind") == "vp.materials":
        # 되묻기에서 '이전'으로 돌아와 재료를 바꾼 경우 — 답을 기다리던 잡은 접고 새로 모은다
        from winmate_common.jobs import jobs
        await jobs().cancel(aj["job_id"])

        def drop(d: dict[str, Any]) -> dict[str, Any]:
            if (d.get("active_job") or {}).get("job_id") == aj["job_id"]:
                d["active_job"] = {**d["active_job"], "status": "canceled"}
            return d
        doc = await service.mutate(vp_id, drop)
        aj = {}
    if aj and aj.get("status") not in TERMINAL:
        raise ApiError(409, "JOB_RUNNING", "이미 진행 중인 작업이 있어요. 끝난 뒤 다시 시도해 주세요.", {"job_id": aj.get("job_id")})
    if body and body.note is not None:
        def fn(d: dict[str, Any]) -> dict[str, Any]:
            d["note"] = body.note or ""
            return d
        doc = await service.mutate(vp_id, fn)
    if not [s for s in doc.get("sources") or [] if s.get("connected")] and not doc.get("attachments") and not (doc.get("note") or "").strip() \
            and not doc.get("customer_name"):
        raise ApiError(422, "NOTHING_TO_COLLECT", "고객사 · 연결 자료 · 파일 · 덧붙일 내용 중 하나는 있어야 해요.")
    return await service.enqueue(vp_id, "vp.materials", {}, doc=doc)


async def decide_fix(vp_id: str, fx: str, decision: str) -> dict[str, Any]:
    pack = await repo.pack_status_map()

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        f = next((x for x in d.get("fixes") or [] if x["id"] == fx), None)
        if f is None:
            raise ApiError(404, "NOT_FOUND", f"정리 항목을 찾을 수 없어요: {fx}")
        apply_fix_decision(d, f, decision, by="user")
        if d.get("plan"):
            service.replan(d, pack)
        return d
    return await service.mutate(vp_id, fn)


def apply_fix_decision(d: dict[str, Any], f: dict[str, Any], decision: str, *, by: str) -> None:
    """수락(accepted) · 되돌리기(reverted) — 되돌리면 원문 재료를 되살리고 합친 · 고친 재료를 뺀다."""
    mats = {m["id"]: m for m in d.get("materials") or []}
    new_ids = set(f.get("result_ids") or [])
    old_ids = set(f.get("item_ids") or [])
    if decision == "revert":
        for i in new_ids:
            if i in mats:
                mats[i]["excluded"] = True
        for i in old_ids:
            if i in mats:
                mats[i]["excluded"] = False
        if f.get("kind") == "refetch":
            for i in old_ids:
                m = mats.get(i)
                if m and f.get("before_number"):
                    m["number"] = f["before_number"]
                    m["state"] = "new"
                    m["text"] = f.get("before_text") or m["text"]
        f["decision"] = "reverted"
    else:
        for i in new_ids:
            if i in mats:
                mats[i]["excluded"] = False
        for i in old_ids:
            if i in mats and f.get("kind") != "refetch":
                mats[i]["excluded"] = True
        f["decision"] = "accepted"
    f["decided_by"] = by


def _answer_effects(d: dict[str, Any], q: dict[str, Any], keys: list[str], pack: dict[str, str]) -> None:
    if q["kind"] == "industry" and keys:
        code = keys[0]
        ind = decide.decide_industry(pinned=code, pack_status=pack)
        ind["mode"] = "auto" if q["answer"]["by"] == "default" else "pin"
        ind["source"] = "classified" if q["answer"]["by"] == "default" else "user"
        d["industry"] = ind
    if q["kind"] == "approver":
        sk = [m for m in d.get("materials") or [] if m.get("axis") == "stakeholder" and m.get("from_question")]
        for m in sk:
            m["excluded"] = True
        for k in keys:
            d.setdefault("materials", []).append({
                "id": new_id("vmi"), "key": f"Q-{k}", "axis": "stakeholder", "text": f"{k} · 결재", "sources": [{"tag": "USER", "ref_id": ""}],
                "state": "new", "number": None, "metric": None, "product_refs": [], "cost": False, "approver": True,
                "group": "approver", "excluded": False, "flags": [], "origin_keys": [], "from_question": True})
    if q["kind"] == "sb_mi_conflict" and keys:
        d.setdefault("facts", {})["conflict_answer"] = keys[0]


async def answer_questions(vp_id: str, body: models.AnswerQuestions) -> dict[str, Any]:
    pack = await repo.pack_status_map()
    given = {a.question_id: a for a in body.answers}
    holder: dict[str, Any] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        qs = [q for q in d.get("questions") or [] if q.get("status") == "open"]
        for q in qs:
            a = given.get(q["id"])
            keys = list(a.keys) if a and a.keys is not None else None
            if body.proceed:
                if keys is None or (not keys and not q.get("multi")):
                    keys = list(q.get("selected_keys") or q.get("default_keys") or [])
                same = sorted(keys) == sorted(q.get("default_keys") or [])
                by = "default" if same and not (a and a.text) else "user"
                q["answer"] = {"keys": keys, "text": a.text if a else None, "by": by}
                q["status"] = "answered" if by == "user" else "defaulted"
                q["selected_keys"] = keys
                _answer_effects(d, q, keys, pack)
                label = " · ".join(o["label"] for o in q.get("options") or [] if o["key"] in keys) or ", ".join(keys)
                d.setdefault("decisions", []).append(service.stamp_decision(
                    3 if q["kind"] == "direction" else 2, f"{q['title'].split(' · ', 1)[-1]} → {label}" + (" (추천값)" if by == "default" else ""),
                    "check" if by == "default" else "pin", key=q["kind"], value=label))
            elif keys is not None:
                q["selected_keys"] = keys
        if body.proceed:
            service.replan(d, pack)
        aj = d.get("active_job") or {}
        holder["job_id"] = aj.get("job_id") if aj.get("status") == "awaiting_input" else None
        return d
    doc = await service.mutate(vp_id, fn)
    resumed = None
    if body.proceed and holder.get("job_id"):
        try:
            await jobs().provide_input(holder["job_id"], {"answered": True})
            resumed = holder["job_id"]

            def mark(d: dict[str, Any]) -> dict[str, Any] | None:
                aj = d.get("active_job") or {}
                if aj.get("job_id") != resumed:
                    return None
                aj["status"] = "queued"
                return d
            doc = await service.mutate(vp_id, mark)
        except (KeyError, ValueError) as exc:
            log.warning("재개 실패 %s: %s", holder["job_id"], exc)
    if service.open_questions(doc):
        nxt = f"/vp/{vp_id}/questions"
    elif resumed:
        nxt = f"/vp/{vp_id}/materials"
    else:
        nxt = f"/vp/{vp_id}/structure"
    return {**service.to_api(doc), "resumed_job_id": resumed, "next_route": nxt}


async def plan_refresh(vp_id: str) -> dict[str, Any]:
    """VP1A `가치 구조로` — 미결 확인 권장 정리는 수락(by default) → 플랜 다시 계산."""
    pack = await repo.pack_status_map()

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for f in d.get("fixes") or []:
            if f.get("decision") == "pending":
                apply_fix_decision(d, f, "accept", by="default")
        service.replan(d, pack)
        return d
    doc = await service.mutate(vp_id, fn)
    return doc["plan"]


async def get_plan(vp_id: str) -> dict[str, Any]:
    doc = await repo.require_vp(vp_id)
    if doc.get("plan") is None:
        pack = await repo.pack_status_map()

        def fn(d: dict[str, Any]) -> dict[str, Any]:
            service.replan(d, pack)
            return d
        doc = await service.mutate(vp_id, fn)
    return doc["plan"]


def prerequisite(d: dict[str, Any], role: str, code: str) -> str | None:
    c = catalog.norm(code)
    if c in ("VP-H", "VP-D") and len(signals.active(d, "stakeholder")) < 2:
        return "stakeholders"
    if c == "EF-B" and not (((d.get("facts") or {}).get("quote") or {}).get("total")
                            or any(a.get("kind") == "quote" for a in d.get("attachments") or [])):
        return "quote"
    return None


PREREQ_MSG = {"quote": "견적이 연결돼야 해요 — 연결하면 바로 바뀝니다", "stakeholders": "이해관계자가 둘 이상 있어야 해요"}


async def patch_plan(vp_id: str, body: models.PatchPlan) -> dict[str, Any]:
    pack = await repo.pack_status_map()
    ov = body.override

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        cur = dict(d.get("plan_overrides") or {})
        if ov.clear:
            cur = {}
        for role in ("CH", "VP", "EF"):
            code = getattr(ov, role)
            if not code:
                continue
            c = catalog.norm(code)
            if catalog.entry(c) is None:
                raise ApiError(422, "UNKNOWN_LAYOUT", f"모르는 레이아웃 코드예요: {code}")
            need = prerequisite(d, role, c)
            if need:
                raise ApiError(409, "PREREQUISITE_MISSING", PREREQ_MSG[need], {"missing": need, "code": c})
            if c.startswith("VP-B") or c in ("VP-A", "VP-C", "VP-D"):
                cur["no_image"] = "1"
            cur[role] = c
        d["plan_overrides"] = {k: v for k, v in cur.items() if k != "no_image"}
        service.replan(d, pack)
        return d
    await service.mutate(vp_id, fn)
    doc = await service.save_point(vp_id, "플랜 변경")
    return doc["plan"]
