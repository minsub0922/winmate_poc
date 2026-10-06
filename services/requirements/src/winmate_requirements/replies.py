"""고객 답변 → 바뀔 곳 → 다음 버전(§6.7 · §7.5). 잡 `rq.reply.analyze`(LangGraph rq_reply_analyze).

바뀔 곳(change)의 ops 는 결정적으로 만든다(LLM 은 대상 · 전 · 후 문장만 고른다):
update_item · set_field · add_item · add_keyman · update_keyman · set_weights · add_evidence
"""
from __future__ import annotations

import copy
import itertools
import logging
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import JobContext, jobs

from . import domain, llm, platform_calls, repo, service
from .models import FIELD_LABELS
from .textutil import (
    best_match,
    clip,
    foreign_numbers,
    grounded,
    normalize_name,
    similar,
    strip_numbers,
)

log = logging.getLogger("winmate.requirements.replies")

FIELD_BY_LABEL = {v: k for k, v in FIELD_LABELS.items()}


async def load(rq_id: str, rid: str) -> dict[str, Any]:
    r = await repo.get("replies", rid)
    if r is None or r.get("requirement_id") != rq_id:
        raise repo.not_found("고객 답변", rid)
    return r


async def save(r: dict[str, Any]) -> dict[str, Any]:
    r["updated_at"] = now_iso()
    return await repo.put("replies", r["id"], r)


async def create(rq_id: str, text: str, file_ids: list[str]) -> dict[str, Any]:
    doc = await repo.require_doc(rq_id)
    text = (text or "").replace("\r\n", "\n").strip()
    file_ids = list(dict.fromkeys(file_ids or []))
    if not text and not file_ids:
        raise ApiError(422, "EMPTY_REPLY", "고객 답변을 붙여 넣거나 파일을 첨부해 주세요")
    files = []
    for fid in file_ids:
        meta = await platform_calls.file_meta(fid)
        files.append({"file_id": fid, "name": meta.get("name") or fid,
                      "type_label": domain.file_label_for(meta.get("name") or "", meta.get("kind")) or (meta.get("kind") or "").upper()})
    rid, job_id = new_id("rp"), new_id("job")
    now = now_iso()
    r = {"id": rid, "requirement_id": rq_id, "base_version": doc.get("saved_version", 0), "status": "analyzing",
         "text": text, "file_ids": file_ids, "files": files, "changes": [], "matches": [], "version_note": None,
         "storyboard_impact": {"count": 0, "links": []}, "applied_version": None, "job_id": job_id, "error": None,
         "created_at": now, "updated_at": now, "owner_id": current_user().id}
    await save(r)
    await jobs().enqueue("requirements", "rq.reply.analyze", {"requirement_id": rq_id, "reply_id": rid},
                         title=f"{domain.title_of(doc) or '요구사항'} · 바뀌는 곳 찾기", ref=rq_id,
                         project_id=doc.get("project_id"), job_id=job_id)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "reply", "id": rid}}


async def get(rq_id: str, rid: str) -> dict[str, Any]:
    return await load(rq_id, rid)


async def select(rq_id: str, rid: str, ids: list[str]) -> dict[str, Any]:
    r = await load(rq_id, rid)
    if r["status"] != "ready":
        raise ApiError(409, "REPLY_NOT_READY", "지금은 고를 수 없어요", {"status": r["status"]})
    sel = set(ids)
    for ch in r["changes"]:
        ch["selected"] = ch["id"] in sel
    r["storyboard_impact"] = await impact(rq_id, r["changes"])
    return await save(r)


# ── 영향(링크 레지스트리, §5.8) ──────────────────────────

def _target_keys(ch: dict[str, Any]) -> set[tuple[str, str]]:
    t = ch["target"]
    if t["kind"] in ("item", "evidence") and t.get("id"):
        return {("item", t["id"])}
    if t["kind"] == "field" and t.get("id"):
        return {("field", t["id"])}
    if t["kind"] == "keyman" and t.get("id"):
        return {("keyman", t["id"])}
    if t["kind"] == "weights":
        return {("weights", "weights")}
    return set()


async def impact(rq_id: str, changes: list[dict[str, Any]]) -> dict[str, Any]:
    keys: set[tuple[str, str]] = set()
    for ch in changes:
        if ch.get("selected"):
            keys |= _target_keys(ch)
    links = [lk for lk in await repo.find("links", {"requirement_id": rq_id}) if lk.get("service") == "storyboard"]
    out = []
    seen: set[tuple[str, str]] = set()
    for lk in links:
        places = []
        for dep in lk.get("depends_on") or []:
            t = dep.get("target") or {}
            k = (t.get("kind"), "weights" if t.get("kind") == "weights" else t.get("id"))
            if k not in keys:
                continue
            for p in dep.get("places") or []:
                pk = (lk["ref_id"], p.get("code") or p.get("label"))
                if pk in seen:
                    continue
                seen.add(pk)
                places.append({"code": p.get("code"), "label": p.get("label") or p.get("code") or ""})
        if places:
            out.append({"ref_id": lk["ref_id"], "title": lk.get("title"), "route": lk.get("route"), "places": places})
    return {"count": len(seen), "links": out}


# ── rq_reply_analyze ─────────────────────────────────────

class ReplyState(TypedDict, total=False):
    rq_id: str
    reply_id: str
    reply_text: str
    attachments: list[dict[str, Any]]
    matches: list[dict[str, Any]]
    raw_changes: list[dict[str, Any]]
    changes: list[dict[str, Any]]
    version_note: str | None
    impact: dict[str, Any]


async def r_load(state: ReplyState) -> dict[str, Any]:
    r = await load(state["rq_id"], state["reply_id"])
    text = r.get("text") or ""
    atts = []
    for f in r.get("files") or []:
        body = ""
        try:
            p = await platform_calls.parsed(f["file_id"], timeout=60)
            if p.get("email"):
                em = p["email"]
                body = f"{em.get('subject') or ''}\n{em.get('body') or ''}"
                if not text.strip():
                    text = body
            else:
                body = p.get("text") or ""
        except Exception as exc:  # noqa: BLE001
            log.info("첨부 읽기 건너뜀 %s: %s", f["file_id"], exc)
        atts.append({**f, "text": body[:8000]})
    return {"reply_text": text, "attachments": atts}


def _questions(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return domain.open_questions(doc)


async def r_match(state: ReplyState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    qs = _questions(doc)
    if not qs:
        return {"matches": []}
    lines = [f"{i + 1}. {q['text']}" for i, q in enumerate(qs)]
    prompt = ("고객 답장의 문단을 우리가 물었던 질문과 짝지어 주세요. 답이 있으면 answered=true, reply_span 에 답 부분(원문 그대로).\n"
              "[물었던 질문]\n" + "\n".join(lines) + f"\n\n[고객 답장]\n{state.get('reply_text') or ''}\n\n"
              f"[첨부] {', '.join(a['name'] for a in state.get('attachments') or []) or '없음'}")
    try:
        res = await llm.call_json("rq.reply_match", prompt, llm.RqReplyMatch, timeout=120)
    except ApiError as exc:
        log.info("답 짝 맞추기 건너뜀: %s", exc.code)
        return {"matches": []}
    out = []
    for m in res.get("matches") or []:
        q = None
        no = m.get("question_no")
        if isinstance(no, int) and 1 <= no <= len(qs) and (not m.get("question_text") or similar(m["question_text"], qs[no - 1]["text"]) >= 0.6):
            q = qs[no - 1]
        elif m.get("question_text"):
            qid = best_match(m["question_text"], [(x["id"], x["text"]) for x in qs], 0.7)
            q = next((x for x in qs if x["id"] == qid), None)
        if q is None:
            continue
        out.append({"question_id": q["id"], "reply_span": clip(m.get("reply_span"), 400), "answered": bool(m.get("answered"))})
    return {"matches": out}


async def r_detect(state: ReplyState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    lines = [f"- {f}: {domain.field_value(doc, f) or '(비어 있음)'}" for f in ("project_name", "customer_name", "final_audience")]
    for k in domain.keymen(doc):
        w = f" {k.get('weight')}%" if len(domain.keymen(doc)) > 1 else ""
        lines.append(f"[{k['name']}{w}]")
        for it in k["items"]:
            ev = ", ".join(e["name"] for e in it.get("evidence") or []) or "근거 자료 없음"
            lines.append(f"  · {it['text']} (근거: {ev})")
    qs = _questions(doc)
    prompt = (
        "고객 답장을 읽고 요구사항 정의서에서 바뀔 곳만 찾아 주세요.\n"
        "- target.kind: item(항목 문장 바꿈 — keyman_name · item_text 원문), evidence(첨부를 근거 자료로 붙임 — item_text, evidence_file_names), "
        "field(칸 값 — field: project_name · customer_name · final_audience), new_item(새 항목 — keyman_name), keyman, weights\n"
        "- label: 행 왼쪽(키맨 이름 또는 칸 이름), before_display · after_display: 짧게 보여 줄 전 · 후, new_text: 실제로 쓸 문장(200자 이내)\n"
        "- resolves_question_texts: 이 변경이 답하는 질문(아래 목록 문장 그대로)\n"
        "- 답장 · 첨부에 없는 수치 · 사실은 쓰지 마세요. 묻지 않았어도 답장에 새 사실이 있으면 포함(예: 최종 제안대상).\n"
        "- version_note: 새 버전 메모(20자 이내, 예 '11/11 회의 반영')\n\n"
        "[정의서]\n" + "\n".join(lines)
        + "\n\n[열린 고객 질문]\n" + ("\n".join(f"- {q['text']}" for q in qs) or "- 없음")
        + f"\n\n[고객 답장]\n{state.get('reply_text') or ''}\n\n[첨부]\n"
        + ("\n".join(f"- {a['name']}" for a in state.get("attachments") or []) or "- 없음")
    )
    res = await llm.call_json("rq.reply_changes", prompt, llm.RqReplyChanges, timeout=150)
    return {"raw_changes": res.get("changes") or [], "version_note": clip(res.get("version_note"), 40) or None}


def _resolve_item(doc: dict[str, Any], keyman_name: str | None, item_text: str | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    pairs = domain.all_items(doc)
    if keyman_name:
        own = [(k, it) for k, it in pairs if normalize_name(k.get("name")) == normalize_name(keyman_name)]
        iid = best_match(item_text, [(it["id"], it["text"]) for _, it in own], 0.6) if own else None
        if iid:
            return next((k, it) for k, it in own if it["id"] == iid)
    iid = best_match(item_text, [(it["id"], it["text"]) for _, it in pairs], 0.75)
    if iid:
        return next((k, it) for k, it in pairs if it["id"] == iid)
    return None, None


def build_changes(doc: dict[str, Any], raw: list[dict[str, Any]], attachments: list[dict[str, Any]], reply_text: str,
                  matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """LLM 변경 → 대상 확인 · ops · 숫자 가드(validate_ops). 대상을 못 찾은 것은 버린다."""
    qs = _questions(doc)
    sources = [reply_text] + [a.get("text") or "" for a in attachments] + [a["name"] for a in attachments]
    out: list[dict[str, Any]] = []
    used_targets: set[tuple[str, str]] = set()
    for c in raw:
        t = c.get("target") or {}
        kind = t.get("kind")
        after = (c.get("after_display") or "").strip()
        new_text = (c.get("new_text") or after).strip()
        if not after:
            continue
        ch: dict[str, Any] | None = None
        if kind in ("item", "evidence"):
            km, it = _resolve_item(doc, t.get("keyman_name"), t.get("item_text") or c.get("before_display"))
            if it is None:
                continue
            if kind == "evidence" or c.get("evidence_file_names"):
                files = []
                for n in c.get("evidence_file_names") or [after]:
                    a = next((a for a in attachments if similar(a["name"], n) >= 0.8), None)
                    if a and a not in files:
                        files.append(a)
                if not files and len(attachments) == 1:
                    files = attachments[:]
                if not files:
                    continue
                have = ", ".join(e["name"] for e in it.get("evidence") or []) or "근거 자료 없음"
                ch = {"target": {"kind": "evidence", "id": it["id"]}, "label": km["name"] or "키맨", "before_display": have,
                      "after_display": ", ".join(f["name"] for f in files),
                      "ops": [{"op": "add_evidence", "item_id": it["id"], "file_id": f["file_id"], "name": f["name"],
                               "type_label": f.get("type_label")} for f in files],
                      "evidence_file_ids": [f["file_id"] for f in files]}
            else:
                bad = foreign_numbers(new_text, *sources, it["text"])
                if bad:
                    new_text = strip_numbers(new_text, bad)
                    after = strip_numbers(after, foreign_numbers(after, *sources, it["text"])) or new_text
                if not new_text or " ".join(new_text.split()) == " ".join(it["text"].split()):
                    continue
                if not grounded(new_text, it["text"], *sources):
                    continue  # 답변에 없는 내용(정적 mock · 지어낸 변경)
                ch = {"target": {"kind": "item", "id": it["id"]}, "label": km["name"] or "키맨",
                      "before_display": clip(c.get("before_display") or it.get("short") or it["text"], 60),
                      "after_display": clip(after, 80), "ops": [{"op": "update_item", "item_id": it["id"], "text": new_text[:200]}]}
        elif kind == "field":
            f = t.get("field") if t.get("field") in domain.FIELDS else FIELD_BY_LABEL.get((c.get("label") or "").strip())
            if f not in ("project_name", "customer_name", "final_audience"):
                continue
            bad = foreign_numbers(new_text, *sources, domain.field_value(doc, f))
            if bad:
                new_text = strip_numbers(new_text, bad)
                after = new_text
            if not new_text or new_text == domain.field_value(doc, f) or not grounded(new_text, domain.field_value(doc, f), *sources):
                continue
            ch = {"target": {"kind": "field", "id": f}, "label": FIELD_LABELS[f],
                  "before_display": domain.field_value(doc, f) or "—", "after_display": clip(after, 80),
                  "ops": [{"op": "set_field", "field": f, "value": new_text[:80 if f != "project_name" else 120]}]}
        elif kind == "new_item":
            name = (t.get("keyman_name") or c.get("label") or "").strip()
            bad = foreign_numbers(new_text, *sources)
            if bad:
                new_text = strip_numbers(new_text, bad)
                after = new_text
            if not new_text or not name or not grounded(new_text, None, *sources):
                continue
            km = next((k for k in domain.keymen(doc) if normalize_name(k.get("name")) == normalize_name(name)), None)
            ops: list[dict[str, Any]] = []
            kid = km["id"] if km else new_id("km")
            if km is None:
                ops.append({"op": "add_keyman", "keyman_id": kid, "name": name[:40]})
            ops.append({"op": "add_item", "keyman_id": kid, "item_id": new_id("ri"), "text": new_text[:200]})
            ch = {"target": {"kind": "new_item", "id": None}, "label": (km or {}).get("name") or name[:40],
                  "before_display": None, "after_display": clip(after, 80), "ops": ops}
        elif kind == "keyman":
            name = (t.get("keyman_name") or "").strip()
            km = next((k for k in domain.keymen(doc) if normalize_name(k.get("name")) == normalize_name(name)), None)
            if km is None or not after or after == km["name"] or not grounded(after, km["name"], *sources):
                continue
            ch = {"target": {"kind": "keyman", "id": km["id"]}, "label": km["name"], "before_display": km["name"],
                  "after_display": clip(after, 40), "ops": [{"op": "update_keyman", "keyman_id": km["id"], "name": after[:40]}]}
        elif kind == "weights":
            ks = domain.keymen(doc)
            w = {}
            for ow in c.get("weights") or []:
                km = next((k for k in ks if normalize_name(k.get("name")) == normalize_name(ow.get("keyman_name"))), None)
                if km:
                    w[km["id"]] = int(ow.get("weight") or 0)
            if len(ks) < 2 or set(w) != {k["id"] for k in ks} or sum(w.values()) != 100 or min(w.values()) < domain.WEIGHT_MIN:
                continue
            if foreign_numbers(" ".join(str(v) for v in w.values()), *sources):
                continue
            ch = {"target": {"kind": "weights", "id": "weights"}, "label": "가중치", "before_display": domain.weights_display(doc),
                  "after_display": " · ".join(str(w[k["id"]]) for k in ks), "ops": [{"op": "set_weights", "weights": w}]}
        if ch is None:
            continue
        tk = (ch["target"]["kind"], str(ch["target"].get("id")))
        if ch["target"]["kind"] != "new_item" and tk in used_targets:
            continue
        used_targets.add(tk)
        resolves = []
        for qt in c.get("resolves_question_texts") or []:
            qid = best_match(qt, [(q["id"], q["text"]) for q in qs], 0.7)
            if qid and qid not in resolves:
                resolves.append(qid)
        ch.update({"id": new_id("ch"), "resolves_question_ids": resolves, "selected": True})
        ch.setdefault("evidence_file_ids", [])
        out.append(ch)
    # 질문 짝(answered)인데 어떤 변경에도 묶이지 않은 질문: 같은 대상을 바꾸는 변경에 붙인다
    for m in matches:
        if not m.get("answered") or any(m["question_id"] in ch["resolves_question_ids"] for ch in out):
            continue
        q = next((q for q in qs if q["id"] == m["question_id"]), None)
        tgt = (q or {}).get("target") or {}
        for ch in out:
            if tgt.get("kind") == "item" and ch["target"].get("id") == tgt.get("id"):
                ch["resolves_question_ids"].append(q["id"])
                break
    return out


async def r_validate(state: ReplyState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    changes = build_changes(doc, state.get("raw_changes") or [], state.get("attachments") or [], state.get("reply_text") or "",
                            state.get("matches") or [])
    return {"changes": changes}


async def r_impact(state: ReplyState) -> dict[str, Any]:
    return {"impact": await impact(state["rq_id"], state.get("changes") or [])}


async def r_save(state: ReplyState) -> dict[str, Any]:
    r = await load(state["rq_id"], state["reply_id"])
    r.update({"status": "ready", "changes": state.get("changes") or [], "matches": state.get("matches") or [],
              "version_note": state.get("version_note"), "storyboard_impact": state.get("impact") or {"count": 0, "links": []},
              "error": None})
    if not r.get("text") and state.get("reply_text"):
        r["text"] = state["reply_text"]
    await save(r)
    return {}


def build_graph() -> StateGraph:
    g = StateGraph(ReplyState)
    nodes = [("load", r_load), ("match_questions", r_match), ("detect_changes", r_detect), ("validate_ops", r_validate),
             ("impact", r_impact), ("save_reply", r_save)]
    for n, fn in nodes:
        g.add_node(n, fn)
    g.add_edge(START, "load")
    for (a, _), (b, _) in itertools.pairwise(nodes):
        g.add_edge(a, b)
    g.add_edge("save_reply", END)
    return g


LABELS = {"load": "답변 읽기", "match_questions": "질문과 짝 맞추기", "detect_changes": "바뀔 곳 찾기", "validate_ops": "확인",
          "impact": "Storyboard 영향", "save_reply": "마무리"}
PROGRESS = {"load": 10, "match_questions": 35, "detect_changes": 80, "validate_ops": 88, "impact": 95, "save_reply": 99}


async def handle_analyze(ctx: JobContext) -> dict[str, Any]:
    rq_id, rid = ctx.payload["requirement_id"], ctx.payload["reply_id"]
    try:
        await run_graph(ctx, build_graph(), {"rq_id": rq_id, "reply_id": rid}, step_labels=LABELS, progress_map=PROGRESS)
    except BaseException as exc:
        r = await repo.get("replies", rid)
        if r is not None and r.get("status") == "analyzing":
            r["status"] = "failed"
            r["error"] = {"code": getattr(exc, "code", "REPLY_FAILED"),
                          "message": getattr(exc, "message", None) or "바뀌는 곳을 찾지 못했어요"}
            await save(r)
        raise
    r = await load(rq_id, rid)
    return {"ref": {"kind": "reply", "id": rid}, "changes": len(r["changes"])}


# ── 반영(§6.7 apply — 한 트랜잭션) ───────────────────────

def apply_ops(d: dict[str, Any], ops: list[dict[str, Any]], src: dict[str, Any], rev: int) -> None:
    for op in ops:
        kind = op["op"]
        if kind == "update_item":
            _, it = domain.find_item(d, op["item_id"])
            if it is not None:
                domain.set_item_text(it, op["text"], src, rev=rev)
        elif kind == "set_field":
            domain.set_field(d, op["field"], op.get("value"), src, rev=rev)
        elif kind == "add_keyman":
            if domain.find_keyman(d, op["keyman_id"]) is None:
                km = domain.new_keyman(d, name=op.get("name") or "", source=src, rev=rev, keyman_id=op["keyman_id"])
                domain.insert_keyman(d, km)
                d["form"]["weights_rev"] = rev
        elif kind == "add_item":
            km = domain.find_keyman(d, op["keyman_id"])
            if km is not None and domain.find_item(d, op.get("item_id") or "")[1] is None:
                it = domain.new_item(d, text=op["text"], source=src, rev=rev, item_id=op.get("item_id"))
                domain.insert_item(km, it)
        elif kind == "update_keyman":
            km = domain.find_keyman(d, op["keyman_id"])
            if km is not None:
                km["name"] = op["name"][:40]
                km["rev"] = rev
        elif kind == "set_weights":
            ks = {k["id"] for k in domain.keymen(d)}
            if set(op["weights"]) == ks:
                domain.set_weights(d, op["weights"], rev=rev)
        elif kind == "add_evidence":
            _, it = domain.find_item(d, op["item_id"])
            if it is not None and not any(e["file_id"] == op["file_id"] for e in it.get("evidence") or []):
                it.setdefault("evidence", []).append({"file_id": op["file_id"], "name": op["name"],
                                                       "type_label": op.get("type_label")})
                it["rev"] = rev


async def apply(rq_id: str, rid: str, ids: list[str], propagate: list[str], note: str | None) -> dict[str, Any]:
    async with repo.lock_for(f"reply:{rid}"):
        r = await load(rq_id, rid)
        if r["status"] == "applied":
            raise ApiError(409, "ALREADY_APPLIED", "이미 반영한 답변이에요", {"version": r.get("applied_version")})
        if r["status"] != "ready":
            raise ApiError(409, "REPLY_NOT_READY", "아직 바뀌는 곳을 찾는 중이에요", {"status": r["status"]})
        sel = [ch for ch in r["changes"] if ch["id"] in set(ids)]
        if not sel:
            raise ApiError(422, "NOTHING_TO_APPLY", "반영할 곳을 하나 이상 골라 주세요")
        doc = await service._ensure_not_filling(await repo.require_doc(rq_id))
        resolved = {q for ch in sel for q in ch.get("resolves_question_ids") or []}
        spans = {m["question_id"]: m.get("reply_span") for m in r.get("matches") or []}
        src = {"kind": "reply", "reply_id": rid}
        u = current_user()
        prev = None
        if doc.get("saved_version", 0) > 0:
            pv = await repo.get_version(rq_id, doc["saved_version"])
            prev = (pv or {}).get("snapshot")
        vnote = (note or "").strip() or r.get("version_note") or "고객 답변 반영"

        def fn(d: dict[str, Any], rev: int) -> int:
            for ch in sel:
                apply_ops(d, copy.deepcopy(ch.get("ops") or []), src, rev)
            now = now_iso()
            for q in d.get("questions") or []:
                if q["id"] in resolved and q["status"] == "open":
                    q["status"] = "answered"
                    q["answer"] = {"text": clip(spans.get(q["id"]) or r.get("text"), 400) or None, "reply_id": rid,
                                   "answered_at": now}
                    q["updated_at"] = now
            domain.cleanup_for_save(d)
            n = d.get("saved_version", 0) + 1
            snap = domain.snapshot(d)
            repo.put_version_sync(rq_id, n, service._version_body(d, n, snap, reason="reply", note=vnote, uid=u.id,
                                                                  uname=u.name, prev=prev))
            d["saved_version"] = n
            d["saved_hash"] = domain.content_hash(d)
            d["saved_at"] = now
            return n

        doc, n = await repo.mutate(rq_id, fn)
        pending = []
        if "storyboard" in propagate:
            for lk in await repo.find("links", {"requirement_id": rq_id}):
                if lk.get("service") != "storyboard":
                    continue
                lk.update({"sync_state": "pending", "pending_version": n, "updated_at": now_iso()})
                await repo.put("links", repo.link_key(rq_id, lk["service"], lk["ref_id"]), lk)
                pending.append({"service": "storyboard", "ref_id": lk["ref_id"]})
        for ch in r["changes"]:
            ch["selected"] = ch["id"] in set(ids)
        r.update({"status": "applied", "applied_version": n})
        await save(r)
        await platform_calls.sync_index(doc)
        return {"version": n, "pending_sync_links": pending}
