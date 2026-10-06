"""rq_fill — 파일 → 폼(§7.2). 잡 kind `rq.fill`, 워커가 LangGraph 로 실행한다.

노드: load_files → parse_blocks → classify_doc → plan_slots → extract_merge → kb_link → short_texts → finalize

SSE(§6.2)
- step  {key: "file:{file_id}", label: 파일 이름, state: reading|done|failed}
- progress {ratio, filled, total} — 칸 하나 쓸 때마다(받을 때마다 화면이 자원을 다시 읽는다)
병합 규칙(§7.2.1)은 결정적이다 — `merge_*` 함수.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.jobs import JobContext, current_job

from . import domain, llm, platform_calls, repo, shorts
from .textutil import clip, nfc, normalize_name, same_item

log = logging.getLogger("winmate.requirements.fill")

DOC_RANK = {"rfp": 3, "mail": 2, "meeting_memo": 1, "other": 0}
EXTRACT_TASK = {"rfp": "rq.extract_rfp", "meeting_memo": "rq.extract_memo", "mail": "rq.extract_mail",
                "other": "rq.extract_other"}
KIND_LABEL = {"rfp": "제안 요청 문서", "meeting_memo": "회의 · 미팅 메모", "mail": "메일", "other": "문서"}
MAX_TEXT = 40000


def slot_delay() -> float:
    try:
        return max(0.0, float(os.environ.get("RQ_FILL_SLOT_DELAY_MS", "150")) / 1000.0)
    except ValueError:
        return 0.15


class FillState(TypedDict, total=False):
    rq_id: str
    job_id: str
    file_ids: list[str]
    files: dict[str, dict[str, Any]]
    order: list[str]
    plans: dict[str, int]
    filled: int
    total: int
    notes: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    ok_files: int


# ── 문서 종류 ────────────────────────────────────────────

def classify_by_name(name: str, kind: str | None) -> str | None:
    n = nfc(name).lower()
    if kind == "email" or n.endswith((".eml", ".msg")):
        return "mail"
    if re.search(r"(요청서|rfp|제안요청|과업|공고|사업계획|입찰|제안\s*지원|제안의뢰)", n):
        return "rfp"
    if re.search(r"(회의록|미팅|메모|회의|memo|minutes|노트|면담|인터뷰|통화)", n):
        return "meeting_memo"
    return None


def locator_for(file: dict[str, Any], quote: str | None) -> str | None:
    if not quote:
        return None
    q = re.sub(r"\s+", " ", quote).strip()[:60]
    if not q:
        return None
    label = file.get("label")
    for page in file.get("pages") or []:
        text = re.sub(r"[ \t]+", " ", page.get("text") or "")
        idx = text.find(q)
        if idx < 0:
            idx = re.sub(r"\s+", " ", text).find(q)
            if idx < 0:
                continue
        if label == "PPTX":
            return f"슬라이드 {page['no']}"
        if label in ("PDF", "DOCX"):
            return f"p.{page['no']}"
        if label == "TXT":
            return f"줄 {text[:idx].count(chr(10)) + 1}"
        return "본문"
    return None


def file_source(file: dict[str, Any], fid: str, job_id: str, quote: str | None, locator: str | None) -> dict[str, Any]:
    loc = (locator or "").strip()[:30] or locator_for(file, quote)
    return {"kind": "file", "file_id": fid, "file_label": file.get("label"), "file_name": file.get("name"),
            "locator": loc or None, "quote": clip(quote, 200) or None, "job_id": job_id}


# ── 병합(§7.2.1, 결정적) ─────────────────────────────────

def _rank_of(doc: dict[str, Any], src: dict[str, Any] | None) -> int:
    if not src or not src.get("file_id"):
        return -1
    f = next((f for f in doc.get("files") or [] if f["file_id"] == src["file_id"]), None)
    return DOC_RANK.get((f or {}).get("doc_kind") or "other", 0) if f else -1


def _add_alt(fld: dict[str, Any], value: str, src: dict[str, Any] | None) -> None:
    alts = fld.setdefault("alternatives", [])
    if fld.get("value") == value or any(a.get("value") == value for a in alts):
        return
    alts.append({"value": value, "source": src})


def merge_field(doc: dict[str, Any], field: str, value: str, src: dict[str, Any], doc_kind: str, rev: int) -> bool:
    fld = doc["form"][field]
    value = domain.clean_text(value, 120 if field == "project_name" else 80) or ""
    if not value:
        return False
    cur = fld.get("value")
    if cur is None:
        domain.set_field(doc, field, value, src, rev=rev)
        return True
    if cur == value:
        return False
    cur_src = fld.get("source") or {}
    if cur_src.get("kind") in ("user", "deep", "reply", "storyboard"):
        _add_alt(fld, value, src)
        return False
    if DOC_RANK.get(doc_kind, 0) > _rank_of(doc, cur_src):
        _add_alt(fld, cur, cur_src)
        fld["alternatives"] = [a for a in fld["alternatives"] if a.get("value") != value]
        domain.set_field(doc, field, value, src, rev=rev)
        return True
    _add_alt(fld, value, src)
    return False


def find_keyman_by_name(doc: dict[str, Any], name: str, aliases: list[str] | None = None) -> dict[str, Any] | None:
    keys = {normalize_name(name)} | {normalize_name(a) for a in aliases or [] if a}
    keys.discard("")
    for k in domain.keymen(doc):
        own = {normalize_name(k.get("name"))} | {normalize_name(a) for a in k.get("aliases") or []}
        if keys & own:
            return k
    return None


def merge_keyman(doc: dict[str, Any], name: str, aliases: list[str], src: dict[str, Any], rev: int) -> tuple[str, bool]:
    km = find_keyman_by_name(doc, name, aliases)
    if km is not None:
        known = set(km.get("aliases") or [])
        km["aliases"] = sorted(known | {a for a in aliases if a and normalize_name(a) != normalize_name(km.get("name"))})
        return km["id"], False
    km = domain.new_keyman(doc, name=name, source=src, rev=rev)
    km["aliases"] = [a for a in aliases if a]
    domain.insert_keyman(doc, km)
    doc["form"]["weights_rev"] = rev
    return km["id"], True


def merge_item(doc: dict[str, Any], keyman_name: str, aliases: list[str], text: str, src: dict[str, Any], rev: int) -> bool:
    text = (text or "").strip()[:200]
    if not text:
        return False
    km = find_keyman_by_name(doc, keyman_name, aliases)
    if km is None:
        merge_keyman(doc, keyman_name, aliases, src, rev)
        km = find_keyman_by_name(doc, keyman_name, aliases)
    assert km is not None
    if any(same_item(it.get("text") or "", text) for it in km["items"]):
        return False
    item = domain.new_item(doc, text=text, source=src, rev=rev)
    domain.insert_item(km, item)
    return True


def normalize_extraction(ex: dict[str, Any], file: dict[str, Any], fid: str, job_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """LLM 추출 → 칸 슬롯 목록(쓰는 순서), 제작자 의견 후보, 맥락."""
    slots: list[dict[str, Any]] = []
    for f in ("project_name", "customer_name", "final_audience"):
        q = ex.get(f) or {}
        val = (q.get("value") or "").strip()
        if not val:
            continue
        if f == "final_audience" and not (q.get("quote") or "").strip():
            continue  # 명시된 경우만(추론 금지)
        slots.append({"type": "field", "field": f, "value": val,
                      "source": file_source(file, fid, job_id, q.get("quote"), q.get("locator"))})
    seen: dict[str, dict[str, Any]] = {}
    for km in ex.get("keymen") or []:
        name = re.sub(r"\s+", " ", (km.get("name") or "")).strip()[:40]
        if not name:
            continue
        aliases = [a.strip() for a in km.get("aliases") or [] if a and a.strip()]
        key = normalize_name(name)
        entry = seen.get(key)
        if entry is None:
            entry = {"type": "keyman", "name": name, "aliases": aliases,
                     "source": file_source(file, fid, job_id, None, None), "items": []}
            seen[key] = entry
            slots.append(entry)
        for it in km.get("items") or []:
            text = re.sub(r"\s+", " ", it.get("text") or "").strip()
            if not text or any(same_item(text, x["text"]) for x in entry["items"]):
                continue
            entry["items"].append({"type": "item", "keyman": name, "aliases": aliases, "text": text[:200],
                                   "source": file_source(file, fid, job_id, it.get("quote"), it.get("locator"))})
    flat: list[dict[str, Any]] = []
    for s in slots:
        flat.append(s)
        if s["type"] == "keyman":
            flat.extend(s.pop("items"))
    notes = [{"text": n["text"].strip(), "source": file_source(file, fid, job_id, n.get("quote"), n.get("locator"))}
             for n in ex.get("author_notes") or [] if (n.get("text") or "").strip()]
    ctx = ex.get("context") or {}
    extra = {"scale_text": (ctx.get("scale_text") or "").strip() or None,
             "deadline_text": (ctx.get("deadline_text") or "").strip() or None,
             "decision_bodies": [b.strip()[:40] for b in ex.get("decision_bodies") or [] if b and b.strip()]}
    return flat, notes, extra


def apply_slot(doc: dict[str, Any], slot: dict[str, Any], doc_kind: str, rev: int) -> bool:
    if slot["type"] == "field":
        return merge_field(doc, slot["field"], slot["value"], slot["source"], doc_kind, rev)
    if slot["type"] == "keyman":
        _, created = merge_keyman(doc, slot["name"], slot["aliases"], slot["source"], rev)
        return created
    if slot["type"] == "item":
        return merge_item(doc, slot["keyman"], slot["aliases"], slot["text"], slot["source"], rev)
    return False


def merge_author_note(doc: dict[str, Any], notes: list[dict[str, Any]], rev: int) -> bool:
    """제작자 의견: 비어 있을 때만, meeting_memo 후보 우선, 여러 문장은 한 문단."""
    if domain.field_value(doc, "author_note") or not notes:
        return False
    texts: list[str] = []
    for n in notes:
        t = n["text"].rstrip()
        if not any(same_item(t, x) for x in texts):
            texts.append(t if t.endswith((".", "다", "요", "!", "?")) else t + ".")
    para = " ".join(texts)[:2000]
    domain.set_field(doc, "author_note", para, notes[0]["source"], rev=rev)
    return True


# ── 그래프 노드 ──────────────────────────────────────────

def _ctx() -> JobContext:
    ctx = current_job()
    assert ctx is not None
    return ctx


async def _step(fid: str, name: str, state: str) -> None:
    await _ctx().step(f"file:{fid}", state, key=f"file:{fid}", label=name, state=state)


async def _progress(state: FillState, rq_id: str | None = None) -> None:
    filled, total = state.get("filled", 0), max(state.get("total", 0), state.get("filled", 0))
    ratio = round(filled / total, 3) if total else 0.0
    await _ctx().progress(min(99, int(ratio * 100)), "채우는 중", ratio=ratio, filled=filled, total=total)


async def _set_file(rq_id: str, fid: str, **fields: Any) -> None:
    def fn(d: dict[str, Any], rev: int) -> None:
        for f in d.get("files") or []:
            if f["file_id"] == fid:
                f.update(fields)

    await repo.mutate(rq_id, fn)


async def load_files(state: FillState) -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for fid in state["file_ids"]:
        try:
            meta = await platform_calls.file_meta(fid)
            name = meta.get("name") or fid
            files[fid] = {"name": name, "kind": meta.get("kind"), "label": domain.file_label_for(name, meta.get("kind")),
                          "pages": [], "text": "", "error": None}
        except ApiError as exc:
            files[fid] = {"name": fid, "kind": None, "label": None, "pages": [], "text": "",
                          "error": {"code": exc.code, "message": "읽지 못했어요"}}
        await _step(fid, files[fid]["name"], "reading")
    return {"files": files, "order": list(state["file_ids"]), "filled": 0, "total": 0, "notes": [], "errors": [],
            "plans": {}, "ok_files": 0}


async def parse_blocks(state: FillState) -> dict[str, Any]:
    files = dict(state["files"])
    order = list(state["order"])
    rq_id = state["rq_id"]
    for fid in list(order):
        f = files[fid]
        if f.get("error"):
            continue
        try:
            doc = await platform_calls.parsed(fid)
        except Exception as exc:  # noqa: BLE001
            f["error"] = {"code": getattr(exc, "code", "PARSE_FAILED"), "message": "읽지 못했어요"}
            continue
        pages = [{"no": p.get("no", i + 1), "text": (p.get("text") or "")[:8000],
                  "images": p.get("image_file_ids") or []} for i, p in enumerate(doc.get("pages") or [])]
        email = doc.get("email") or None
        if email:
            body = "\n".join(x for x in (f"제목: {email.get('subject') or ''}", email.get("body") or "") if x.strip())
            pages = [{"no": 1, "text": body[:20000], "images": []}]
            for att in (email.get("attachment_list") or []):
                afid = att.get("file_id")
                label = domain.file_label_for(att.get("name") or "", None)
                if not afid or att.get("inline") or label in (None, "메일") or afid in files:
                    continue
                files[afid] = {"name": att.get("name") or afid, "kind": None, "label": label, "pages": [], "text": "",
                               "error": None, "parent": fid}
                order.insert(order.index(fid) + 1, afid)
                await _attach_child(rq_id, afid, att.get("name") or afid, label, state["job_id"])
                await _step(afid, files[afid]["name"], "reading")
        # 글자 층이 없는 쪽(스캔) · 그림만 있는 쪽 → i2t
        scanned = [p for p in pages if not p["text"].strip() and p["images"]][:5]
        for p in scanned:
            try:
                p["text"] = await llm.call_vision(
                    "rq.i2t_page", p["images"][:3],
                    "이 쪽에 적힌 글자를 그대로 옮기고, 표 · 도식은 짧게 설명해 주세요. 없는 내용을 지어내지 마세요.")
            except ApiError as exc:
                log.info("i2t 건너뜀 %s p%s: %s", fid, p["no"], exc.code)
        f["pages"] = pages
        f["text"] = "\n".join(p["text"] for p in pages)[:MAX_TEXT]
        if not f["text"].strip():
            f["error"] = {"code": "EMPTY_DOCUMENT", "message": "읽을 글자가 없어요"}
    return {"files": files, "order": order}


async def _attach_child(rq_id: str, fid: str, name: str, label: str, job_id: str) -> None:
    def fn(d: dict[str, Any], rev: int) -> None:
        if any(f["file_id"] == fid for f in d["files"]):
            return
        from winmate_common.ids import now_iso

        d["files"].append({"file_id": fid, "name": name, "type_label": label, "status": "reading", "filled_count": 0,
                           "doc_kind": None, "error": None, "job_id": job_id, "added_at": now_iso()})

    await repo.mutate(rq_id, fn)


async def classify_doc(state: FillState) -> dict[str, Any]:
    files = dict(state["files"])
    for fid in state["order"]:
        f = files[fid]
        if f.get("error"):
            continue
        kind = classify_by_name(f["name"], f.get("kind")) or ("mail" if f.get("label") == "메일" else None)
        if kind is None:
            try:
                res = await llm.call_json("rq.classify_doc",
                                          f"다음 문서의 종류를 고르세요(rfp: 제안 요청 · 사업 계획 문서, meeting_memo: 회의 · 미팅 메모, "
                                          f"mail: 메일, other: 그 밖).\n파일 이름: {f['name']}\n\n{f['text'][:2500]}",
                                          llm.RqDocKind, timeout=60)
                kind = res.get("doc_kind") or "other"
                f["language"] = res.get("language")
            except ApiError:
                kind = "other"
        f["doc_kind"] = kind
        await _set_file(state["rq_id"], fid, doc_kind=kind)
    return {"files": files}


async def plan_slots(state: FillState) -> dict[str, Any]:
    plans: dict[str, int] = {}
    for fid in state["order"]:
        f = state["files"][fid]
        if f.get("error"):
            continue
        try:
            res = await llm.call_json("rq.plan_slots",
                                      "이 문서에서 요구사항 폼에 채울 수 있는 칸 후보를 세어 주세요(칸: field=프로젝트명 · 고객사 · 최종 제안대상, "
                                      "keyman=키맨, item=키맨별 요구사항, author_note=제작자 의견). 문서에 근거가 있는 것만.\n\n"
                                      + f["text"][:6000], llm.RqPlan, timeout=60)
            plans[fid] = max(1, min(40, len(res.get("slots") or [])))
        except ApiError:
            plans[fid] = 4
    total = sum(plans.values())
    upd = {"plans": plans, "total": total, "filled": 0}
    await _write_progress(state["rq_id"], state["job_id"], 0, total)
    await _progress({**state, **upd})
    return upd


async def _write_progress(rq_id: str, job_id: str, filled: int, total: int, *, extra: Any = None) -> None:
    def fn(d: dict[str, Any], rev: int) -> None:
        d["fill_progress"] = {"job_id": job_id, "filled": filled, "total": max(total, filled)}

    await repo.mutate(rq_id, fn)


async def extract_merge(state: FillState) -> dict[str, Any]:
    rq_id, job_id = state["rq_id"], state["job_id"]
    files = state["files"]
    plans = dict(state.get("plans") or {})
    filled = state.get("filled", 0)
    notes: list[dict[str, Any]] = []
    extras: dict[str, Any] = {"scale_text": None, "deadline_text": None, "decision_bodies": []}
    errors: list[dict[str, Any]] = []
    ok = 0
    delay = slot_delay()
    for idx, fid in enumerate(state["order"]):
        f = files[fid]
        await _ctx().check_cancel()
        if f.get("error"):
            errors.append({"file_id": fid, **f["error"]})
            await _set_file(rq_id, fid, status="failed", error=f["error"])
            await _step(fid, f["name"], "failed")
            continue
        kind = f.get("doc_kind") or "other"
        prompt = _extract_prompt(f, kind)
        try:
            ex = await llm.call_json(EXTRACT_TASK.get(kind, "rq.extract_other"), prompt, llm.RqExtraction, timeout=180)
        except ApiError as exc:
            err = {"code": exc.code, "message": exc.message}
            errors.append({"file_id": fid, **err})
            f["error"] = err
            await _set_file(rq_id, fid, status="failed", error={"code": exc.code, "message": "읽지 못했어요"})
            await _step(fid, f["name"], "failed")
            plans.pop(fid, None)
            continue
        slots, file_notes, extra = normalize_extraction(ex, f, fid, job_id)
        for n in file_notes:
            n["doc_kind"] = kind
        notes.extend(file_notes)
        for key in ("scale_text", "deadline_text"):
            extras[key] = extras[key] or extra[key]
        extras["decision_bodies"] += [b for b in extra["decision_bodies"] if b not in extras["decision_bodies"]]
        remaining_plan = sum(plans.get(x, 0) for x in state["order"][idx + 1:] if not files[x].get("error"))
        plans[fid] = len(slots)
        total = filled + len(slots) + remaining_plan + (1 if file_notes else 0)
        count = 0
        for slot in slots:
            written = await _apply(rq_id, slot, kind, job_id, filled + 1, total)
            if written:
                filled += 1
                count += 1
            else:
                total = max(filled, total - 1)
            await _progress({"filled": filled, "total": total})
            if written and delay:
                await asyncio.sleep(delay)
        ok += 1
        await _set_file(rq_id, fid, status="done", filled_count=count, error=None)
        await _step(fid, f["name"], "done")
        state_total = total
        state = {**state, "total": state_total}
    # 제작자 의견(메모 우선) · 맥락
    notes.sort(key=lambda n: 0 if n.get("doc_kind") == "meeting_memo" else 1)
    written = False

    def fn(d: dict[str, Any], rev: int) -> bool:
        w = merge_author_note(d, notes, rev)
        ctx = d.setdefault("context", {})
        for key in ("scale_text", "deadline_text"):
            if extras[key] and not ctx.get(key):
                ctx[key] = extras[key][:200]
        hints = d.setdefault("hints", {"decision_bodies": []})
        hints["decision_bodies"] = list(dict.fromkeys((hints.get("decision_bodies") or []) + extras["decision_bodies"]))[:6]
        return w

    _, written = await repo.mutate(rq_id, fn)
    if written:
        filled += 1
        await _progress({"filled": filled, "total": max(filled, state.get("total", 0))})
    return {"filled": filled, "total": max(filled, state.get("total", 0)), "notes": [], "errors": errors, "ok_files": ok,
            "plans": plans}


async def _apply(rq_id: str, slot: dict[str, Any], kind: str, job_id: str, filled_next: int, total: int) -> bool:
    def fn(d: dict[str, Any], rev: int) -> bool:
        w = apply_slot(d, slot, kind, rev)
        if w:
            d["fill_progress"] = {"job_id": job_id, "filled": filled_next, "total": max(total, filled_next)}
        return w

    _, written = await repo.mutate(rq_id, fn)
    return written


def _extract_prompt(f: dict[str, Any], kind: str) -> str:
    unit = {"PPTX": "슬라이드", "PDF": "p.", "DOCX": "p."}.get(f.get("label") or "", "쪽")
    body = "\n".join(f"--- {unit} {p['no']} ---\n{p['text']}" if f.get("label") in ("PPTX", "PDF", "DOCX") else p["text"]
                     for p in f.get("pages") or [])[:MAX_TEXT]
    return (
        f"다음은 고객에게서 받은 {KIND_LABEL.get(kind, '문서')}입니다(파일: {f['name']}).\n"
        "요구사항 정의서 폼을 채울 값을 뽑아 주세요.\n"
        "- project_name: 프로젝트(사업) 이름, 문서 표현 그대로(120자 이내)\n"
        "- customer_name: 고객사 이름(80자 이내)\n"
        "- final_audience: 최종 제안을 받는 사람 · 기구 — 문서에 명시된 경우만(추론 금지)\n"
        "- keymen: 고객 쪽 의사결정 관여자(직함 · 역할)와 그 사람이 바라는 것(items, 항목마다 200자 이내). 같은 사람의 다른 표기는 aliases\n"
        "- author_notes: 제작자(우리 영업)의 목표 · 내부 전략 · 강조점(예: 스펙인이 목표) — 고객 요구가 아니다\n"
        "- context.scale_text: 규모(연면적 · 매장 수 등), context.deadline_text: 제출일 · 일정\n"
        "- decision_bodies: 문서에 나온 의사결정 주체(위원회 · 이사회 등)\n"
        "값마다 원문 근거 문장(quote, 200자 이내)과 위치(locator: 예 '슬라이드 3', 'p.5', '줄 12')를 붙이세요. 문서에 없는 값은 비워 두세요.\n\n"
        f"[문서]\n{body}"
    )


async def kb_link(state: FillState) -> dict[str, Any]:
    rq_id = state["rq_id"]
    await link_entities(rq_id)
    return {}


async def link_entities(rq_id: str) -> None:
    """항목마다 kb A1 → entities, 전체 글 kb A2 → context.vertical, A1 공간 · 제품 · 솔루션 → context.*"""
    doc = await repo.require_doc(rq_id)
    results: dict[str, list[dict[str, Any]]] = {}
    for _, it in domain.all_items(doc):
        text = (it.get("text") or "").strip()
        if not text or it.get("entities_for") == domain._short_key(text):
            continue
        res = await platform_calls.kb_query("A1", {"text": text})
        if res is None:
            continue
        ents = []
        for ln in res.get("links") or []:
            if not ln.get("id") or not ln.get("type"):
                continue
            e = {"type": ln["type"], "id": ln["id"], "name": ln.get("name") or ln.get("surface") or ln["id"],
                 "surface": ln.get("surface")}
            if not any(x["type"] == e["type"] and x["id"] == e["id"] for x in ents):
                ents.append(e)
        results[it["id"]] = ents
    full = " ".join(filter(None, [domain.field_value(doc, "project_name"), domain.field_value(doc, "customer_name")]
                           + [it.get("text") for _, it in domain.all_items(doc)]))
    vertical = None
    if full.strip():
        a2 = await platform_calls.kb_query("A2", {"text": full[:4000]})
        if a2 is not None:
            vertical = {"top2": [{"id": c.get("id"), "name": c.get("name") or c.get("id"), "score": c.get("score") or 0}
                                 for c in (a2.get("top2") or []) if c.get("id")][:2],
                        "ask": bool(a2.get("ask"))}

    def fn(d: dict[str, Any], rev: int) -> None:
        for _, it in domain.all_items(d):
            if it["id"] in results:
                it["entities"] = results[it["id"]]
                it["entities_for"] = domain._short_key(it.get("text"))
        ctx = d.setdefault("context", {})
        if vertical is not None:
            ctx["vertical"] = vertical
        spaces: dict[str, dict[str, Any]] = {}
        products: dict[tuple[str, str], dict[str, Any]] = {}
        sols: dict[str, dict[str, Any]] = {}
        for _, it in domain.all_items(d):
            for e in it.get("entities") or []:
                if e["type"] == "space_type":
                    spaces.setdefault(e["id"], {"id": e["id"], "name": e["name"], "item_ids": []})["item_ids"].append(it["id"])
                elif e["type"] in ("category", "model", "family", "product"):
                    products.setdefault((e["type"], e["id"]), {"type": e["type"], "id": e["id"], "name": e["name"],
                                                               "item_ids": []})["item_ids"].append(it["id"])
                elif e["type"] == "solution":
                    sols.setdefault(e["id"], {"id": e["id"], "name": e["name"], "item_ids": []})["item_ids"].append(it["id"])
        ctx["spaces"] = list(spaces.values())
        ctx["products"] = list(products.values())
        ctx["solutions"] = list(sols.values())
        if not ctx.get("language"):
            ctx["language"] = "ko"

    await repo.mutate(rq_id, fn)


async def short_texts(state: FillState) -> dict[str, Any]:
    await shorts.ensure_shorts(state["rq_id"], timeout=90)
    return {}


async def finalize(state: FillState) -> dict[str, Any]:
    filled = state.get("filled", 0)
    await _ctx().progress(100, "다 채웠어요", ratio=1.0, filled=filled, total=filled)
    return {"total": filled}


def build() -> StateGraph:
    g = StateGraph(FillState)
    for name, fn in (("load_files", load_files), ("parse_blocks", parse_blocks), ("classify_doc", classify_doc),
                     ("plan_slots", plan_slots), ("extract_merge", extract_merge), ("kb_link", kb_link),
                     ("short_texts", short_texts), ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "load_files")
    g.add_edge("load_files", "parse_blocks")
    g.add_edge("parse_blocks", "classify_doc")
    g.add_edge("classify_doc", "plan_slots")
    g.add_edge("plan_slots", "extract_merge")
    g.add_edge("extract_merge", "kb_link")
    g.add_edge("kb_link", "short_texts")
    g.add_edge("short_texts", "finalize")
    g.add_edge("finalize", END)
    return g


STEP_LABELS = {"load_files": "파일 확인", "parse_blocks": "문서 읽기", "classify_doc": "문서 종류", "plan_slots": "채울 칸 세기",
               "extract_merge": "칸 채우기", "kb_link": "제품 · 공간 연결", "short_texts": "짧은 이름", "finalize": "마무리"}


# ── 잡 처리기 ────────────────────────────────────────────

async def _wait_turn(ctx: JobContext, rq_id: str) -> None:
    """같은 정의서의 앞 rq.fill 잡이 끝날 때까지 기다린다(순서대로 실행)."""
    me = ctx.job.id
    for _ in range(900):
        doc = await repo.get_doc(rq_id)
        if doc is None:
            raise ApiError(404, "NOT_FOUND", "요구사항 정의서를 찾을 수 없어요")
        aj = doc.get("active_job")
        if aj and aj.get("job_id") == me:
            return
        if not aj or await platform_calls.job_alive(aj["job_id"]) is False:
            def claim(d: dict[str, Any], rev: int, prev: dict[str, Any] | None = aj) -> bool:
                cur = d.get("active_job")
                if cur and cur.get("job_id") != me and cur.get("job_id") != (prev or {}).get("job_id"):
                    return False
                d["active_job"] = {"job_id": me, "kind": "rq.fill"}
                d["queued_jobs"] = [j for j in d.get("queued_jobs") or [] if j["job_id"] != me]
                d["fill_progress"] = {"job_id": me, "filled": 0, "total": 0}
                return True

            _, ok = await repo.mutate(rq_id, claim)
            if ok:
                return
        await ctx.check_cancel()
        await asyncio.sleep(1.0)
    raise ApiError(504, "JOB_WAIT_TIMEOUT", "앞선 파일 읽기가 끝나지 않아요")


async def _release(rq_id: str, job_id: str, *, failed: dict[str, Any] | None = None) -> dict[str, Any] | None:
    def fn(d: dict[str, Any], rev: int) -> None:
        if (d.get("active_job") or {}).get("job_id") == job_id:
            d["active_job"] = None
        d["queued_jobs"] = [j for j in d.get("queued_jobs") or [] if j["job_id"] != job_id]
        for f in d.get("files") or []:
            if f.get("job_id") == job_id and f.get("status") == "reading":
                f["status"] = "failed" if failed else "done"
                if failed:
                    f["error"] = {"code": failed.get("code", "FAILED"), "message": "읽지 못했어요"}
        if not d.get("active_job") and d.get("queued_jobs"):
            nxt = d["queued_jobs"].pop(0)
            d["active_job"] = nxt
            d["fill_progress"] = {"job_id": nxt["job_id"], "filled": 0, "total": 0}
        elif not d.get("active_job"):
            d["fill_progress"] = None

    try:
        doc, _ = await repo.mutate(rq_id, fn)
        return doc
    except ApiError:
        return None


async def handle_fill(ctx: JobContext) -> dict[str, Any]:
    rq_id = ctx.payload["requirement_id"]
    file_ids = list(ctx.payload.get("file_ids") or [])
    await _wait_turn(ctx, rq_id)
    try:
        final = await run_graph(ctx, build(), {"rq_id": rq_id, "job_id": ctx.job.id, "file_ids": file_ids},
                                step_labels=STEP_LABELS)
    except BaseException as exc:
        err = {"code": getattr(exc, "code", type(exc).__name__)}
        doc = await _release(rq_id, ctx.job.id, failed=err)
        if doc is not None:
            await platform_calls.sync_index(doc)
        raise
    final = final or {}
    doc = await _release(rq_id, ctx.job.id)
    if doc is not None:
        await platform_calls.sync_index(doc)
    errors = final.get("errors") or []
    if final.get("ok_files", 0) == 0 and errors:
        first = errors[0]
        raise ApiError(422 if first.get("code") not in ("POLICY_CONFIDENTIAL", "LLM_UNAVAILABLE", "LLM_TIMEOUT") else 503,
                       first.get("code", "FILL_FAILED"),
                       first.get("message") if first.get("code") in ("POLICY_CONFIDENTIAL", "LLM_UNAVAILABLE", "LLM_TIMEOUT")
                       else "파일을 읽지 못했어요", {"files": errors})
    return {"ref": {"kind": "requirement", "id": rq_id}, "filled": final.get("filled", 0),
            "failed_files": [e["file_id"] for e in errors]}
