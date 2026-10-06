"""심층 작성(§6.4 · §7.3 · §7.4).

- 분석: `POST deep-sessions` → 202 잡 `rq.deep.analyze`(LangGraph rq_deep_analyze, 워커)
- 질의응답: 동기 REST. 답 하나는 API 프로세스 안에서 LangGraph `rq_deep_answer` 로 처리(30초)
세션은 collection `sessions`. 정의서 문서의 `deep` 에는 진행 중 세션의 id · 상태만 둔다(질의 번호는 세션에서 읽는다 —
건너뛰기 같은 답이 작업본 revision 을 올리지 않게).
"""
from __future__ import annotations

import asyncio
import copy
import itertools
import logging
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import JobContext, jobs

from . import domain, fill, llm, platform_calls, repo, service
from .models import FIELD_LABELS
from .textutil import (
    best_match,
    clip,
    foreign_numbers,
    josa,
    normalize_name,
    relevance,
    strip_numbers,
    topic_of,
)

log = logging.getLogger("winmate.requirements.deep")

MAX_GAPS = 7
KB_MAX = 2
ANSWER_TIMEOUT = 30.0
FIELD_ORDER = {"final_audience": 0, "customer_name": 1, "project_name": 2}
LLM_GAP_KINDS = ("unquantified", "vague_scope", "ambiguous", "missing_perspective", "conflict")
SENTENCE_KINDS = LLM_GAP_KINDS + ("too_few_items", "capability_unclear")
DONE_STATES = ("applied", "deferred", "skipped", "resolved_by_form")
ACTIVE = domain.ACTIVE_SESSION_STATES


# ── 세션 저장 ────────────────────────────────────────────

async def load(rq_id: str, sid: str) -> dict[str, Any]:
    s = await repo.get("sessions", sid)
    if s is None or s.get("requirement_id") != rq_id:
        raise repo.not_found("심층 작성 세션", sid)
    return s


async def save(s: dict[str, Any]) -> dict[str, Any]:
    s["updated_at"] = now_iso()
    saved = await repo.put("sessions", s["id"], s)
    return saved


def present(s: dict[str, Any]) -> dict[str, Any]:
    out = dict(s)
    out["created_at"] = s.get("created_at")
    out["updated_at"] = s.get("updated_at")
    return out


async def _set_doc_deep(rq_id: str, s: dict[str, Any] | None, *, clear: bool = False) -> dict[str, Any]:
    def fn(d: dict[str, Any], rev: int) -> None:
        if clear:
            if (d.get("deep") or {}).get("session_id") == (s or {}).get("id"):
                d["deep"] = None
            return
        assert s is not None
        d["deep"] = {"session_id": s["id"], "status": s["status"]}
        d["last_deep_session_id"] = s["id"]

    doc, _ = await repo.mutate(rq_id, fn)
    await platform_calls.sync_index(doc)
    return doc


async def enrich_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """정의서 문서(메모리)에 진행 중 세션의 질의 번호를 채운다(RQ0 `"심층 작성 {i} / {N}"`)."""
    d = doc.get("deep")
    if not d or d.get("status") not in ACTIVE:
        return doc
    s = await repo.get("sessions", d["session_id"])
    if s is None:
        return doc
    doc = {**doc, "deep": {**d, "status": s["status"], "current_index": max(1, s.get("current_index") or 1),
                            "total": s.get("total") or len(s.get("selected_gap_ids") or s.get("gaps") or [])}}
    return doc


# ── 만들기 · 다시 분석 ───────────────────────────────────

async def create_session(rq_id: str) -> dict[str, Any]:
    async with repo.lock_for(f"deep:{rq_id}"):
        doc = await service._ensure_not_filling(await repo.require_doc(rq_id))
        active = domain.deep_in_progress(doc)
        if active:
            s = await repo.get("sessions", active["session_id"])
            if s is not None and s.get("status") in ACTIVE:
                raise ApiError(409, "SESSION_ACTIVE", "진행 중인 심층 작성이 있어요", {"session_id": s["id"]})
        sid = new_id("ds")
        now = now_iso()
        s = {"id": sid, "requirement_id": rq_id, "status": "analyzing", "job_id": None, "base_revision": doc["version"],
             "stale": False, "completeness_before": None, "completeness": None, "completeness_after": None, "gaps": [],
             "selected_gap_ids": [], "current_gap_id": None, "current_index": 0, "total": 0, "log": [],
             "pending_proposal": None, "result": None, "error": None, "created_at": now, "updated_at": now,
             "created_question_ids": []}
        return await _enqueue_analysis(rq_id, s)


async def _enqueue_analysis(rq_id: str, s: dict[str, Any]) -> dict[str, Any]:
    job_id = new_id("job")
    s.update({"status": "analyzing", "job_id": job_id, "error": None, "stale": False})
    await save(s)
    doc = await _set_doc_deep(rq_id, s)
    await jobs().enqueue("requirements", "rq.deep.analyze", {"requirement_id": rq_id, "session_id": s["id"]},
                         title=f"{domain.title_of(doc) or '새 요구사항'} · 보강할 곳 찾기", ref=rq_id,
                         project_id=doc.get("project_id"), job_id=job_id)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "deep_session", "id": s["id"]}}


async def reanalyze(rq_id: str, sid: str) -> dict[str, Any]:
    async with repo.lock_for(f"deep:{rq_id}"):
        await service._ensure_not_filling(await repo.require_doc(rq_id))
        s = await load(rq_id, sid)
        if s["status"] not in ("ready", "failed"):
            raise ApiError(409, "SESSION_NOT_ACTIVE", "지금은 다시 분석할 수 없어요", {"status": s["status"]})
        s.update({"gaps": [], "selected_gap_ids": [], "log": [], "current_gap_id": None, "current_index": 0, "total": 0})
        return await _enqueue_analysis(rq_id, s)


# ── 규칙형 보강할 곳 · 질문 템플릿 ────────────────────────

def _gap(target: dict[str, Any], kind: str, origin: str, chip: str, problem: str, *, keyman_id: str | None = None,
         impact: int = 1, topic: str | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"id": new_id("gp"), "target": target, "kind": kind, "origin": origin, "chip_label": chip,
            "chip_keyman_id": keyman_id, "problem": clip(problem, 24), "priority": 0, "impact": impact,
            "question": None, "status": "pending", "answer": None, "change": None, "customer_question_ids": [],
            "needs_confirmation": False, "topic": topic, **(extra or {})}


def rule_gaps(doc: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for f in ("final_audience", "customer_name", "project_name"):
        if not domain.field_value(doc, f):
            out.append(_gap({"kind": "field", "field": f}, "empty_field", "rule", FIELD_LABELS[f], "비어 있음",
                            topic=FIELD_LABELS[f]))
    named = [k for k in domain.keymen(doc) if (k.get("name") or "").strip()]
    if not named:
        out.append(_gap({"kind": "keymen"}, "no_keyman", "rule", "키맨", "키맨 없음", topic="키맨"))
    if len(domain.keymen(doc)) >= 2 and doc["form"].get("weights_mode") != "custom":
        out.append(_gap({"kind": "weights"}, "default_weights", "rule", "가중치", "균등 기본값", topic="키맨 가중치"))
    for k in named:
        n = sum(1 for it in k["items"] if (it.get("text") or "").strip())
        if n <= 1:
            out.append(_gap({"kind": "keyman", "keyman_id": k["id"]}, "too_few_items", "rule", k["name"],
                            f"요구사항 {n}개" if n else "요구사항 없음", keyman_id=k["id"], impact=3,
                            topic=f"{k['name']} 요구사항"))
    return out


def _option(label: str, *, value: str | None = None, weights: dict[str, int] | None = None) -> dict[str, Any]:
    return {"id": new_id("op"), "label": label[:60], "value": value, "weights": weights}


def default_weight_options(doc: dict[str, Any]) -> list[dict[str, Any]]:
    ks = domain.keymen(doc)
    presets = {2: [[60, 40]], 3: [[50, 30, 20]], 4: [[40, 30, 20, 10]], 5: [[30, 25, 20, 15, 10]]}
    out = []
    for p in presets.get(len(ks), []):
        w = {k["id"]: v for k, v in zip(ks, p, strict=True)}
        out.append(_option(" · ".join(f"{k['name'] or '키맨'} {v}" for k, v in zip(ks, p, strict=True)), weights=w))
    return out


def equal_option(doc: dict[str, Any]) -> dict[str, Any]:
    ks = domain.keymen(doc)
    return _option("균등 유지", weights={k["id"]: w for k, w in zip(ks, domain.equal_weights(len(ks)), strict=True)})


def template_question(doc: dict[str, Any], g: dict[str, Any]) -> dict[str, Any]:
    kind = g["kind"]
    t = g["target"]
    topic = g.get("topic") or g["chip_label"]
    if kind == "empty_field":
        f = t["field"]
        if f == "final_audience":
            names = [k["name"] for k in domain.keymen(doc) if (k.get("name") or "").strip()]
            bodies = (doc.get("hints") or {}).get("decision_bodies") or []
            opts = list(dict.fromkeys(names + bodies))[:4]
            return {"text": "최종 제안은 누구에게 하나요?", "options": [_option(o, value=o) for o in opts], "allow_text": True,
                    "answer_type": "value"}
        if f == "customer_name":
            return {"text": "고객사는 어디인가요?", "options": [], "allow_text": True, "answer_type": "value"}
        return {"text": "프로젝트(사업) 이름은 무엇인가요?", "options": [], "allow_text": True, "answer_type": "value"}
    if kind == "no_keyman":
        bodies = (doc.get("hints") or {}).get("decision_bodies") or []
        return {"text": "누구의 요구가 가장 중요한가요?", "options": [_option(b, value=b) for b in bodies[:4]],
                "allow_text": True, "answer_type": "value"}
    if kind == "default_weights":
        return {"text": "키맨 중 누구의 요구를 더 무겁게 볼까요?", "options": default_weight_options(doc) + [equal_option(doc)],
                "allow_text": True, "answer_type": "weights"}
    if kind == "too_few_items":
        return {"text": f"{josa(g['chip_label'], '이/가')} 바라는 것이 더 있나요?", "options": [], "allow_text": True,
                "answer_type": "sentence"}
    texts = {
        "unquantified": f"'{topic}'의 목표 수치가 있나요?",
        "vague_scope": f"'{topic}'의 범위를 구체적으로 알려 주세요",
        "ambiguous": f"'{topic}'은(는) 어떤 뜻인가요?",
        "missing_perspective": f"{josa(g['chip_label'], '이/가')} 더 걱정하는 것이 있나요?",
        "conflict": f"'{topic}'과(와) 다른 요구 중 무엇이 먼저인가요?",
        "capability_unclear": g.get("kb_question") or f"'{topic}'이(가) 필요한가요?",
    }
    return {"text": clip(texts.get(kind, f"'{topic}'을(를) 더 알려 주세요"), 40), "options": [], "allow_text": True,
            "answer_type": "sentence"}


def _quoted(text: str | None) -> str | None:
    m = re.search(r"[‘'“\"]([^’'”\"]{2,24})[’'”\"]", text or "")
    return m.group(1) if m else None


# ── rq_deep_analyze(잡) ──────────────────────────────────

class AnalyzeState(TypedDict, total=False):
    rq_id: str
    session_id: str
    base_revision: int
    signature: str
    gaps: list[dict[str, Any]]
    kb_gaps: list[dict[str, Any]]
    llm_gaps: list[dict[str, Any]]
    spaces_sequence: list[str]
    completeness: int


async def a_snapshot(state: AnalyzeState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    return {"base_revision": doc["version"], "signature": domain.stale_signature(doc)}


async def a_rule_gaps(state: AnalyzeState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    return {"gaps": rule_gaps(doc)}


async def a_kb_context(state: AnalyzeState) -> dict[str, Any]:
    rq_id = state["rq_id"]
    doc = await repo.require_doc(rq_id)
    seq: list[str] = []
    if domain.item_count(doc):
        await fill.link_entities(rq_id)
        doc = await repo.require_doc(rq_id)
        v = (doc.get("context") or {}).get("vertical") or {}
        top = (v.get("top2") or [{}])[0]
        if top.get("id") and not v.get("ask"):
            b1 = await platform_calls.kb_query("B1", {"vertical_id": top["id"]})
            seq = [s.get("name") for s in (b1 or {}).get("space_sequence") or [] if s.get("name")][:6]
    return {"spaces_sequence": seq}


async def a_kb_gaps(state: AnalyzeState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    items = [(k, it) for k, it in domain.all_items(doc) if (it.get("text") or "").strip()]
    if not items:
        return {"kb_gaps": []}
    res = await platform_calls.kb_query("B2", {"text": " ".join(it["text"] for _, it in items)[:4000]})
    out: list[dict[str, Any]] = []
    for g in (res or {}).get("gaps") or []:
        space = g.get("space")
        target = next(((k, it) for k, it in items
                       if any(e.get("type") == "space_type" and e.get("id") == space for e in it.get("entities") or [])), None)
        if target is None:
            continue
        k, it = target
        cap = _quoted(g.get("question_ko")) or g.get("capability") or "역량"
        gap = _gap({"kind": "item", "item_id": it["id"], "keyman_id": k["id"]}, "capability_unclear", "kb_b2", k["name"] or "키맨",
                   f"'{clip(cap, 12)}' 필요 여부", keyman_id=k["id"], impact=1, topic=cap,
                   extra={"kb_question": clip(g.get("question_ko"), 40), "needs_confirmation": True})
        out.append(gap)
        if len(out) >= KB_MAX:
            break
    return {"kb_gaps": out}


async def a_llm_gaps(state: AnalyzeState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    named = [k for k in domain.keymen(doc) if k["items"]]
    if not any((it.get("text") or "").strip() for k in named for it in k["items"]):
        return {"llm_gaps": []}
    lines = []
    for k in named:
        w = f" ({k['weight']}%)" if len(domain.keymen(doc)) > 1 and k.get("weight") else ""
        lines.append(f"{k['name'] or '이름 없는 키맨'}{w}")
        lines += [f" - {it['text']}" for it in k["items"] if (it.get("text") or "").strip()]
    prompt = (
        "다음 요구사항 항목에서 보강할 곳을 찾아 주세요.\n"
        "종류: unquantified(목표 수치 없음), vague_scope(범위 불명확), ambiguous(뜻이 여럿), "
        "missing_perspective(키맨 관점이 빠짐 — target.kind=keyman), conflict(다른 요구와 충돌).\n"
        "problem 은 24자 이내 한 줄(핵심 낱말은 작은따옴표), impact 1~3(3이 영향 큼). item_text 는 원문 그대로.\n\n"
        f"프로젝트: {domain.field_value(doc, 'project_name') or '—'} / 고객사: {domain.field_value(doc, 'customer_name') or '—'}\n"
        "[키맨 · 항목]\n" + "\n".join(lines)
    )
    try:
        res = await llm.call_json("rq.gaps", prompt, llm.RqGaps, timeout=120)
    except ApiError as exc:
        log.info("LLM 보강할 곳 건너뜀: %s", exc.code)
        return {"llm_gaps": []}
    items = [(k, it) for k in named for it in k["items"] if (it.get("text") or "").strip()]
    cands = [(it["id"], it["text"]) for _, it in items]
    out = []
    for g in res.get("gaps") or []:
        t = g.get("target") or {}
        if t.get("kind") == "item":
            iid = best_match(t.get("item_text"), cands)
            if iid is None:
                continue
            k, it = next((k, it) for k, it in items if it["id"] == iid)
            topic = _quoted(g.get("problem")) or topic_of(it["text"])
            out.append(_gap({"kind": "item", "item_id": iid, "keyman_id": k["id"]}, g["kind"], "llm", k["name"] or "키맨",
                            g.get("problem") or "", keyman_id=k["id"], impact=int(g.get("impact") or 2), topic=topic))
        else:
            k = next((k for k in named if normalize_name(k.get("name")) == normalize_name(t.get("keyman_name"))), None)
            if k is None:
                continue
            out.append(_gap({"kind": "keyman", "keyman_id": k["id"]}, g["kind"], "llm", k["name"], g.get("problem") or "",
                            keyman_id=k["id"], impact=int(g.get("impact") or 2), topic=_quoted(g.get("problem")) or k["name"]))
    return {"llm_gaps": out}


def _sort_key(doc: dict[str, Any], g: dict[str, Any]) -> tuple[Any, ...]:
    kind = g["kind"]
    if kind == "empty_field":
        return (0, FIELD_ORDER.get(g["target"].get("field"), 9), 0, 0, 0)
    if kind == "no_keyman":
        return (1, 0, 0, 0, 0)
    if kind == "default_weights":
        return (2, 0, 0, 0, 0)
    km = domain.find_keyman(doc, g["target"].get("keyman_id") or g.get("chip_keyman_id") or "")
    kw = (km or {}).get("weight") or 0
    korder = (km or {}).get("order", 99)
    iorder = -1
    if g["target"].get("item_id"):
        _, it = domain.find_item(doc, g["target"]["item_id"])
        iorder = (it or {}).get("order", 99)
    group = 4 if g["origin"] == "kb_b2" else 3
    return (group, -int(g.get("impact") or 1), -kw, korder, iorder)


def rank_and_cap(doc: dict[str, Any], gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps = sorted(gaps, key=lambda g: _sort_key(doc, g))
    seen: set[tuple[str, str]] = set()
    out = []
    kb = 0
    for g in gaps:
        t = g["target"]
        key = (t["kind"], t.get("item_id") if t["kind"] == "item" else t.get("keyman_id") if t["kind"] == "keyman"
               else t.get("field") or t["kind"])
        if key in seen:
            continue
        if g["origin"] == "kb_b2":
            if kb >= KB_MAX:
                continue
            kb += 1
        seen.add(key)
        out.append(g)
        if len(out) >= MAX_GAPS:
            break
    for i, g in enumerate(out):
        g["priority"] = i + 1
    return out


async def a_rank(state: AnalyzeState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    gaps = rank_and_cap(doc, list(state.get("gaps") or []) + list(state.get("llm_gaps") or []) + list(state.get("kb_gaps") or []))
    return {"gaps": gaps}


async def a_questions(state: AnalyzeState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    gaps = copy.deepcopy(state.get("gaps") or [])
    for g in gaps:
        g["question"] = template_question(doc, g)
    need = [g for g in gaps if g["origin"] == "llm" or g["kind"] == "default_weights"]
    if need:
        lines = []
        for i, g in enumerate(need):
            if g["kind"] == "default_weights":
                ws = " · ".join(f"{k['name']} {k.get('weight')}" for k in domain.keymen(doc))
                lines.append(f"{i + 1}. [가중치] 키맨 가중치가 균등 기본값({ws}) — 배분안 선택지 2~3개(합 100, 각 5 이상, weights 에 키맨 이름별 값)")
            else:
                _, it = domain.find_item(doc, g["target"].get("item_id") or "")
                about = f"'{it['text']}'" if it else g["chip_label"]
                lines.append(f"{i + 1}. [{g['chip_label']}] {about} — {g['problem']} ({g['kind']})")
        prompt = ("보강할 곳마다 고객 쪽 담당자에게 물을 질문을 만들어 주세요. 질문은 40자 이내 존댓말 의문문, 선택지는 0~4개(근거 없는 수치 금지), "
                  "short_label 은 24자 이내. gap_no 와 target_label(대괄호 안 이름)을 그대로 돌려주세요.\n\n" + "\n".join(lines))
        try:
            res = await llm.call_json("rq.questions", prompt, llm.RqQuestions, timeout=90)
        except ApiError as exc:
            log.info("LLM 질문 건너뜀(템플릿): %s", exc.code)
            res = {"questions": []}
        ks = domain.keymen(doc)
        for q in res.get("questions") or []:
            no = int(q.get("gap_no") or 0)
            if not 1 <= no <= len(need):
                continue
            g = need[no - 1]
            if q.get("target_label") and normalize_name(q["target_label"]) != normalize_name(g["chip_label"]):
                continue
            if g["kind"] == "default_weights":
                opts = []
                for o in q.get("options") or []:
                    w = {}
                    for ow in o.get("weights") or []:
                        km = next((k for k in ks if normalize_name(k.get("name")) == normalize_name(ow.get("keyman_name"))), None)
                        if km:
                            w[km["id"]] = int(ow.get("weight") or 0)
                    if set(w) == {k["id"] for k in ks} and sum(w.values()) == 100 and min(w.values()) >= domain.WEIGHT_MIN:
                        opts.append(_option(" · ".join(f"{k['name']} {w[k['id']]}" for k in ks), weights=w))
                if opts:
                    g["question"]["options"] = opts[:3] + [equal_option(doc)]
                if q.get("text") and relevance(q["text"], "키맨 가중치 비중 요구 무겁게 중요") >= 0.1:
                    g["question"]["text"] = clip(q["text"], 40)
                continue
            text = clip(q.get("text"), 40)
            _, it = domain.find_item(doc, g["target"].get("item_id") or "")
            if text and relevance(text, g.get("topic"), g["problem"], (it or {}).get("text"), g["chip_label"]) >= 0.2:
                g["question"]["text"] = text
                g["question"]["options"] = [_option(clip(o.get("label"), 40), value=clip(o.get("label"), 200))
                                            for o in (q.get("options") or [])[:4] if (o.get("label") or "").strip()]
            if q.get("short_label"):
                g["short_label"] = clip(q["short_label"], 24)
    return {"gaps": gaps}


async def a_score(state: AnalyzeState) -> dict[str, Any]:
    doc = await repo.require_doc(state["rq_id"])
    return {"completeness": domain.completeness(doc, state.get("gaps") or [])}


async def a_save(state: AnalyzeState) -> dict[str, Any]:
    rq_id, sid = state["rq_id"], state["session_id"]
    s = await load(rq_id, sid)
    if s["status"] != "analyzing":
        return {}
    gaps = state.get("gaps") or []
    s.update({"status": "ready", "gaps": gaps, "selected_gap_ids": [g["id"] for g in gaps],
              "completeness_before": state.get("completeness"), "completeness": state.get("completeness"),
              "base_revision": state.get("base_revision"), "signature": state.get("signature"), "stale": False,
              "total": len(gaps), "current_index": 0, "spaces_sequence": state.get("spaces_sequence") or []})
    await save(s)
    await _set_doc_deep(rq_id, s)
    return {}


def build_analyze() -> StateGraph:
    g = StateGraph(AnalyzeState)
    nodes = [("snapshot_draft", a_snapshot), ("rule_gaps", a_rule_gaps), ("kb_context", a_kb_context), ("kb_gaps", a_kb_gaps),
             ("llm_gaps", a_llm_gaps), ("rank_and_cap", a_rank), ("make_questions", a_questions),
             ("score_completeness", a_score), ("save_session", a_save)]
    for name, fn in nodes:
        g.add_node(name, fn)
    g.add_edge(START, nodes[0][0])
    for (a, _), (b, _) in itertools.pairwise(nodes):
        g.add_edge(a, b)
    g.add_edge(nodes[-1][0], END)
    return g


ANALYZE_LABELS = {"snapshot_draft": "작업본 고정", "rule_gaps": "빈 곳 찾기", "kb_context": "제품 · 공간 연결", "kb_gaps": "필요 역량",
                  "llm_gaps": "문장 살피기", "rank_and_cap": "순서 정하기", "make_questions": "질문 만들기",
                  "score_completeness": "완성도", "save_session": "마무리"}
ANALYZE_PROGRESS = {"snapshot_draft": 5, "rule_gaps": 10, "kb_context": 25, "kb_gaps": 35, "llm_gaps": 65, "rank_and_cap": 70,
                    "make_questions": 90, "score_completeness": 95, "save_session": 99}


async def handle_analyze(ctx: JobContext) -> dict[str, Any]:
    rq_id, sid = ctx.payload["requirement_id"], ctx.payload["session_id"]
    try:
        await run_graph(ctx, build_analyze(), {"rq_id": rq_id, "session_id": sid}, step_labels=ANALYZE_LABELS,
                        progress_map=ANALYZE_PROGRESS)
    except BaseException as exc:
        s = await repo.get("sessions", sid)
        if s is not None and s.get("status") == "analyzing":
            s["status"] = "failed"
            s["error"] = {"code": getattr(exc, "code", "ANALYZE_FAILED"),
                          "message": getattr(exc, "message", None) or "보강할 곳을 찾지 못했어요"}
            await save(s)
            try:
                await _set_doc_deep(rq_id, s, clear=True)
            except ApiError:
                pass
        raise
    s = await load(rq_id, sid)
    return {"ref": {"kind": "deep_session", "id": sid}, "gaps": len(s.get("gaps") or []), "completeness": s.get("completeness")}


# ── 조회 · 선택 · 시작 ───────────────────────────────────

def _selected(s: dict[str, Any]) -> list[dict[str, Any]]:
    sel = set(s.get("selected_gap_ids") or [])
    return [g for g in s["gaps"] if g["id"] in sel and g["status"] != "deselected"]


def _advance(s: dict[str, Any]) -> None:
    sel = _selected(s)
    s["total"] = len(sel)
    done = sum(1 for g in sel if g["status"] in DONE_STATES)
    if s.get("pending_proposal"):
        s["current_index"] = min(done + 1, max(len(sel), 1))
        return
    pending = [g for g in sel if g["status"] == "pending"]
    s["current_gap_id"] = pending[0]["id"] if pending else None
    s["current_index"] = min(done + 1, max(len(sel), 1)) if pending else len(sel)


def _reevaluate(doc: dict[str, Any], s: dict[str, Any]) -> bool:
    """규칙형 보강할 곳을 폼으로 다시 평가(resolved_by_form). 바뀌면 True."""
    changed = False
    for g in s["gaps"]:
        if g["origin"] != "rule" or g["status"] not in ("pending", "deselected"):
            continue
        if domain.rule_gap_resolved(doc, g):
            g["status"] = "resolved_by_form"
            changed = True
            if g["id"] in (s.get("selected_gap_ids") or []) and s["status"] == "asking":
                value = _resolved_display(doc, g)
                s["log"].append({"gap_id": g["id"], "kind": "resolved", "label": g["chip_label"], "value_display": value})
    if changed:
        s["completeness"] = domain.completeness(doc, s["gaps"])
        if s["status"] == "asking":
            _advance(s)
    return changed


def _resolved_display(doc: dict[str, Any], g: dict[str, Any]) -> str:
    t = g["target"]
    if g["kind"] == "empty_field":
        return domain.field_value(doc, t["field"]) or "—"
    if g["kind"] == "default_weights":
        return domain.weights_display(doc)
    return "폼에서 채움"


async def get_session(rq_id: str, sid: str) -> dict[str, Any]:
    async with repo.lock_for(f"session:{sid}"):
        s = await load(rq_id, sid)
        if s["status"] in ("ready", "asking"):
            doc = await repo.require_doc(rq_id)
            changed = _reevaluate(doc, s)
            stale = s["status"] == "ready" and bool(s.get("signature")) and domain.stale_signature(doc) != s.get("signature")
            if stale != s.get("stale"):
                s["stale"] = stale
                changed = True
            if s["status"] == "asking" and not s.get("pending_proposal") and not s.get("current_gap_id"):
                await _finish(rq_id, s, doc)
                changed = False
            if changed:
                s = await save(s)
        return present(s)


async def select_gaps(rq_id: str, sid: str, ids: list[str]) -> dict[str, Any]:
    async with repo.lock_for(f"session:{sid}"):
        s = await load(rq_id, sid)
        if s["status"] != "ready":
            raise ApiError(409, "SESSION_NOT_ACTIVE", "지금은 다룰 곳을 바꿀 수 없어요", {"status": s["status"]})
        valid = {g["id"] for g in s["gaps"] if g["status"] in ("pending", "deselected")}
        unknown = [i for i in ids if i not in {g["id"] for g in s["gaps"]}]
        if unknown:
            raise ApiError(422, "VALIDATION_FAILED", "없는 보강할 곳이에요", {"gap_ids": unknown})
        s["selected_gap_ids"] = [g["id"] for g in s["gaps"] if g["id"] in set(ids) and g["id"] in valid]
        s["total"] = len(s["selected_gap_ids"])
        return present(await save(s))


async def start(rq_id: str, sid: str) -> dict[str, Any]:
    async with repo.lock_for(f"session:{sid}"):
        s = await load(rq_id, sid)
        if s["status"] == "asking":
            return present(s)
        if s["status"] != "ready":
            raise ApiError(409, "SESSION_NOT_ACTIVE", "지금은 시작할 수 없어요", {"status": s["status"]})
        doc = await repo.require_doc(rq_id)
        _reevaluate(doc, s)
        sel = set(s.get("selected_gap_ids") or [])
        chosen = [g for g in s["gaps"] if g["id"] in sel and g["status"] == "pending"]
        if not chosen:
            raise ApiError(422, "NOTHING_SELECTED", "다룰 곳을 하나 이상 골라 주세요")
        for g in s["gaps"]:
            if g["status"] == "pending" and g["id"] not in sel:
                g["status"] = "deselected"
        s["selected_gap_ids"] = [g["id"] for g in chosen]
        s["status"] = "asking"
        _advance(s)
        s = await save(s)
        await _set_doc_deep(rq_id, s)
        return present(s)


# ── 답 처리(rq_deep_answer, 동기 LangGraph) ───────────────

class AnswerState(TypedDict, total=False):
    rq_id: str
    sid: str
    body: dict[str, Any]
    session: dict[str, Any]
    gap: dict[str, Any]
    route: str
    outcome: str
    log_entry: dict[str, Any] | None
    proposal: dict[str, Any] | None
    question: dict[str, Any] | None
    revision: int


def _gap_by_id(s: dict[str, Any], gid: str) -> dict[str, Any]:
    g = next((g for g in s["gaps"] if g["id"] == gid), None)
    if g is None:
        raise repo.not_found("보강할 곳", gid)
    return g


def _sg(state: AnswerState) -> tuple[dict[str, Any], dict[str, Any]]:
    s = state["session"]
    return s, _gap_by_id(s, state["body"]["gap_id"])


async def n_route(state: AnswerState) -> dict[str, Any]:
    body = state["body"]
    _, g = _sg(state)
    kind = body["kind"]
    if kind == "skip":
        return {"route": "skip"}
    if kind == "unknown":
        return {"route": "unknown"}
    at = (g.get("question") or {}).get("answer_type") or ("sentence" if g["kind"] in SENTENCE_KINDS else "value")
    if at == "weights" or kind == "weights":
        return {"route": "weights"}
    if at == "value":
        return {"route": "value"}
    return {"route": "sentence"}


def _answer_text(g: dict[str, Any], body: dict[str, Any]) -> str:
    if body["kind"] == "option":
        opt = next((o for o in (g.get("question") or {}).get("options") or [] if o["id"] == body.get("option_id")
                    or o["label"] == body.get("option_id")), None)
        if opt is None:
            raise ApiError(422, "VALIDATION_FAILED", "없는 선택지예요", {"option_id": body.get("option_id")})
        return (opt.get("value") or opt["label"]).strip()
    text = (body.get("text") or "").strip()
    if not text:
        raise ApiError(422, "VALIDATION_FAILED", "답을 입력해 주세요")
    return text


async def n_apply_value(state: AnswerState) -> dict[str, Any]:
    rq_id, body = state["rq_id"], state["body"]
    s, g = _sg(state)
    if state["route"] == "weights":
        weights = _weights_answer(state)
        src = {"kind": "deep", "session_id": s["id"]}

        def fn(d: dict[str, Any], rev: int) -> str:
            before = domain.weights_display(d)
            domain.set_weights(d, weights, rev=rev)
            return before

        doc, before = await repo.mutate(rq_id, fn)
        after = domain.weights_display(doc)
        g["change"] = {"label": "가중치", "before_display": before, "after_display": after, "is_addition": False}
        entry = {"gap_id": g["id"], "kind": "applied", "label": "가중치", "value_display": after}
        _ = src
    else:
        value = _answer_text(g, body)
        t = g["target"]
        if g["kind"] == "no_keyman":
            def fn(d: dict[str, Any], rev: int) -> None:
                km = domain.new_keyman(d, name=value, source={"kind": "deep", "session_id": s["id"]}, rev=rev)
                domain.insert_keyman(d, km)
                d["form"]["weights_rev"] = rev

            doc, _ = await repo.mutate(rq_id, fn)
            g["change"] = {"label": "키맨", "before_display": None, "after_display": value[:40], "is_addition": True}
            entry = {"gap_id": g["id"], "kind": "applied", "label": "키맨", "value_display": value[:40]}
        else:
            field = t["field"]

            def fn(d: dict[str, Any], rev: int) -> str | None:
                before = domain.field_value(d, field)
                domain.set_field(d, field, value, {"kind": "deep", "session_id": s["id"]}, rev=rev)
                return before

            doc, before = await repo.mutate(rq_id, fn)
            shown = domain.field_value(doc, field) or value
            g["change"] = {"label": FIELD_LABELS[field], "before_display": before, "after_display": shown, "is_addition": False}
            entry = {"gap_id": g["id"], "kind": "applied", "label": FIELD_LABELS[field], "value_display": shown}
    g["status"] = "applied"
    g["answer"] = {k: body.get(k) for k in ("kind", "option_id", "text", "weights")}
    s["log"].append(entry)
    return {"outcome": "applied", "log_entry": entry, "revision": doc["version"], "session": s}


def _weights_answer(state: AnswerState) -> dict[str, int]:
    body = state["body"]
    _, g = _sg(state)
    if body["kind"] == "weights" and body.get("weights"):
        return {k: int(v) for k, v in body["weights"].items()}
    if body["kind"] == "option":
        opt = next((o for o in (g.get("question") or {}).get("options") or [] if o["id"] == body.get("option_id")
                    or o["label"] == body.get("option_id")), None)
        if opt is None or not opt.get("weights"):
            raise ApiError(422, "VALIDATION_FAILED", "없는 선택지예요", {"option_id": body.get("option_id")})
        return dict(opt["weights"])
    nums = [int(n) for n in re.findall(r"\d+", body.get("text") or "")]
    ks = state["session"].get("_keymen_ids") or []
    if len(nums) == len(ks) and ks:
        return dict(zip(ks, nums, strict=True))
    raise ApiError(422, "VALIDATION_FAILED", "가중치를 읽지 못했어요. 키맨 순서대로 숫자를 적어 주세요(예: 50 30 20)")


async def n_rewrite(state: AnswerState) -> dict[str, Any]:
    rq_id, body = state["rq_id"], state["body"]
    s, g = _sg(state)
    answer = _answer_text(g, body)
    doc = await repo.require_doc(rq_id)
    proposal = await make_proposal(doc, s, g, answer)
    g["status"] = "proposed"
    g["answer"] = {"kind": body["kind"], "option_id": body.get("option_id"), "text": answer}
    s["pending_proposal"] = proposal
    return {"outcome": "proposal", "proposal": proposal, "revision": doc["version"], "session": s}


async def make_proposal(doc: dict[str, Any], s: dict[str, Any], g: dict[str, Any], answer: str, *,
                        instruction: str | None = None, prev: dict[str, Any] | None = None) -> dict[str, Any]:
    """답 → 정의서 문장(rewrite_item + validate_rewrite). 사용자가 말하지 않은 수치 · 사실을 넣지 않는다."""
    t = g["target"]
    km = domain.find_keyman(doc, t.get("keyman_id") or g.get("chip_keyman_id") or "")
    item = None
    if t.get("item_id"):
        km2, item = domain.find_item(doc, t["item_id"])
        km = km2 or km
    kind = "replace_item" if item is not None and g["kind"] not in ("too_few_items", "missing_perspective") else "add_item"
    if g["kind"] == "capability_unclear":
        kind = "add_item"
    before = item["text"] if (item is not None and kind == "replace_item") else None
    task = "rq.rewrite_item" if kind == "replace_item" else "rq.rewrite_add"
    others = [it["text"] for it in (km or {}).get("items") or [] if not item or it["id"] != item["id"]]
    prompt = (
        "고객 쪽 답을 요구사항 정의서 문장으로 다듬어 주세요(200자 이내, 명사형 끝맺음). after_short 는 24자 이내.\n"
        "답에 없는 수치 · 사실 · 고객명은 넣지 마세요. 고객에게 따로 받아야 할 자료가 있으면 side_effects 에 확인 질문으로.\n"
        f"kind: {kind}\n키맨: {(km or {}).get('name') or '—'}\n"
        + (f"지금 문장: {before}\n" if before else f"같은 키맨의 다른 항목: {' / '.join(others[:5]) or '—'}\n")
        + f"질문: {(g.get('question') or {}).get('text') or ''}\n답: {answer}\n"
        + (f"이전 제안: {prev.get('after_text')}\n고칠 지시: {instruction}\n" if prev and instruction else "")
    )
    res = await llm.call_json(task, prompt, llm.RqRewrite, timeout=25)
    sources = [answer, before or "", instruction or "", *(others if kind == "add_item" else [])]
    after = (res.get("after_text") or "").strip()[:200]
    short = (res.get("after_short") or "").strip()
    bad = foreign_numbers(after, *sources)
    if bad:
        try:
            res2 = await llm.call_json(task, prompt + f"\n주의: 답에 없는 숫자({', '.join(sorted(bad))})를 넣지 마세요.",
                                       llm.RqRewrite, timeout=20)
            after2 = (res2.get("after_text") or "").strip()[:200]
            if after2:
                after, short, res = after2, (res2.get("after_short") or "").strip(), res2
        except ApiError:
            pass
        bad = foreign_numbers(after, *sources)
        if bad:
            after = strip_numbers(after, bad)
    if not after or relevance(after, answer, before, instruction) < 0.3:
        after = clip(re.sub(r"\s+", " ", (instruction and prev and prev.get("after_text")) or answer), 200)
        short = ""
    sbad = foreign_numbers(short, *sources)
    if sbad:
        short = strip_numbers(short, sbad)
    short = clip(short, 24) if short and relevance(short, after) >= 0.4 else None
    sides = []
    for se in res.get("side_effects") or []:
        qt = clip(se.get("question_text"), 120)
        if not qt or relevance(qt, answer, before, after) < 0.2:
            continue
        sides.append({"id": new_id("se"), "kind": "add_customer_question", "label": clip(se.get("label") or qt, 40),
                      "question_text": qt, "keyman_id": (km or {}).get("id"), "checked": True})
    return {"id": new_id("pp"), "gap_id": g["id"], "kind": kind, "target": t, "before_text": before, "after_text": after,
            "after_short": short, "side_effects": sides[:2], "revisions": (prev or {}).get("revisions", -1) + 1,
            "answer_text": answer, "keyman_id": (km or {}).get("id")}


async def n_unknown(state: AnswerState) -> dict[str, Any]:
    rq_id = state["rq_id"]
    s, g = _sg(state)
    doc = await repo.require_doc(rq_id)
    text, short, keyman_id, target = await phrase_question(doc, g)
    q = service.new_question(rq_id, text=text, short_label=short, keyman_id=keyman_id, target=target,
                             origin={"kind": "deep_unknown", "session_id": s["id"]})

    def fn(d: dict[str, Any], rev: int) -> None:
        d.setdefault("questions", []).append(q)

    doc, _ = await repo.mutate(rq_id, fn)
    g["status"] = "deferred"
    g["answer"] = {"kind": "unknown"}
    g["customer_question_ids"].append(q["id"])
    s.setdefault("created_question_ids", []).append(q["id"])
    entry = {"gap_id": g["id"], "kind": "deferred", "label": "고객 확인", "value_display": q.get("short_label") or q["text"]}
    s["log"].append(entry)
    return {"outcome": "deferred", "question": q, "log_entry": entry, "revision": doc["version"], "session": s}


def template_customer_question(g: dict[str, Any], topic: str, km: dict[str, Any] | None) -> tuple[str, str]:
    """LLM 없이 만드는 고객용 질문(정중한 한 문장) + 짧은 이름. 내부 말(가중치 · 전략)은 쓰지 않는다."""
    kind = g["kind"]
    name = ((km or {}).get("name") or "").strip()
    if kind == "empty_field":
        field = g["target"].get("field")
        if field == "final_audience":
            return "최종 제안은 어느 분께 드리면 될까요?", "최종 제안대상"
        label = FIELD_LABELS.get(field or "", topic)
        return f"{josa(label, '을/를')} 알려 주실 수 있을까요?", clip(label, 24)
    if kind in ("too_few_items", "missing_perspective") and name:
        return f"{name}님께서 이번 사업에 더 바라시는 점이 있을까요?", clip(f"{name} 요구사항", 24)
    if kind == "unquantified":
        return f"'{topic}'의 목표 수치가 있을까요?", clip(f"'{topic}' 목표 수치", 24)
    if kind in ("vague_scope", "ambiguous"):
        return f"'{topic}'에 어떤 내용이 들어가나요?", clip(f"'{topic}' 범위", 24)
    if kind == "default_weights":
        return "이번 사업에서 가장 중요하게 보시는 분은 어느 분일까요?", "주요 의사결정자"
    return f"'{topic}'에 대해 확인 부탁드립니다.", clip(g.get("short_label") or topic, 24)


async def phrase_question(doc: dict[str, Any], g: dict[str, Any]) -> tuple[str, str, str | None, dict[str, Any] | None]:
    """'모름' → 고객용 질문 문장 + 짧은 이름 + 키맨(실패하면 템플릿)."""
    t = g["target"]
    keyman_id = t.get("keyman_id") or g.get("chip_keyman_id")
    target = None
    item = None
    if t["kind"] == "item":
        km, item = domain.find_item(doc, t["item_id"])
        keyman_id = (km or {}).get("id") or keyman_id
        target = {"kind": "item", "id": t["item_id"]} if item else None
    elif t["kind"] == "field":
        target = {"kind": "field", "id": t["field"]}
    elif t["kind"] == "keyman":
        target = {"kind": "keyman", "id": t["keyman_id"]}
    topic = g.get("topic") or g["chip_label"]
    km = domain.find_keyman(doc, keyman_id or "")
    fallback = template_customer_question(g, topic, km)
    prompt = ("영업 담당자가 모르는 것을 고객에게 물을 질문으로 바꿔 주세요. 질문은 정중한 존댓말 한 문장(120자 이내), "
              "short_label 은 24자 이내 명사구. 내부 전략 · 가중치는 쓰지 마세요.\n"
              f"주제: {topic}\n문제: {g['problem']}\n원래 질문: {(g.get('question') or {}).get('text') or ''}\n"
              + (f"관련 항목: {item['text']}\n" if item else "") + (f"키맨: {km['name']}\n" if km else ""))
    try:
        res = await llm.call_json("rq.customer_question", prompt, llm.RqCustomerQuestion, timeout=20)
    except ApiError:
        return fallback[0], fallback[1], keyman_id, target
    text = clip(res.get("text"), 120)
    short = clip(res.get("short_label"), 24)
    srcs = (topic, g["problem"], (g.get("question") or {}).get("text"), (item or {}).get("text"))
    if not text or relevance(text, *srcs) < 0.3:
        return fallback[0], fallback[1], keyman_id, target
    if not short or relevance(short, *srcs, text) < 0.3:
        short = fallback[1]
    return text, short, keyman_id, target


async def n_skip(state: AnswerState) -> dict[str, Any]:
    s, g = _sg(state)
    g["status"] = "skipped"
    g["answer"] = {"kind": "skip"}
    entry = {"gap_id": g["id"], "kind": "skipped", "label": "건너뜀", "value_display": g.get("topic") or g["chip_label"]}
    s["log"].append(entry)
    doc = await repo.require_doc(state["rq_id"])
    return {"outcome": "skipped", "log_entry": entry, "revision": doc["version"], "session": s}


async def n_advance(state: AnswerState) -> dict[str, Any]:
    s = state["session"]
    doc = await repo.require_doc(state["rq_id"])
    s["completeness"] = domain.completeness(doc, s["gaps"])
    _advance(s)
    return {"session": s}


def _pick(state: AnswerState) -> str:
    return {"skip": "skip_gap", "unknown": "phrase_customer_question", "value": "apply_value", "weights": "apply_value",
            "sentence": "rewrite_item"}[state["route"]]


_answer_graph = None


def answer_graph() -> Any:
    global _answer_graph
    if _answer_graph is None:
        g = StateGraph(AnswerState)
        g.add_node("route_answer", n_route)
        g.add_node("apply_value", n_apply_value)
        g.add_node("rewrite_item", n_rewrite)
        g.add_node("phrase_customer_question", n_unknown)
        g.add_node("skip_gap", n_skip)
        g.add_node("advance", n_advance)
        g.add_edge(START, "route_answer")
        g.add_conditional_edges("route_answer", _pick, ["apply_value", "rewrite_item", "phrase_customer_question", "skip_gap"])
        for n in ("apply_value", "rewrite_item", "phrase_customer_question", "skip_gap"):
            g.add_edge(n, "advance")
        g.add_edge("advance", END)
        _answer_graph = g.compile()
    return _answer_graph


async def answer(rq_id: str, sid: str, body: dict[str, Any]) -> dict[str, Any]:
    async with repo.lock_for(f"session:{sid}"):
        s = await load(rq_id, sid)
        if s["status"] != "asking":
            raise ApiError(409, "SESSION_NOT_ACTIVE", "질의 중인 세션이 아니에요", {"status": s["status"]})
        doc = await repo.require_doc(rq_id)
        if _reevaluate(doc, s):
            await save(s)
        if s.get("pending_proposal"):
            raise ApiError(409, "PROPOSAL_PENDING", "먼저 '이렇게 바꿀까요?'에 답해 주세요",
                           {"proposal_id": s["pending_proposal"]["id"]})
        if body["gap_id"] != s.get("current_gap_id"):
            raise ApiError(409, "GAP_NOT_CURRENT", "지금 질문이 아니에요", {"current_gap_id": s.get("current_gap_id")})
        g = _gap_by_id(s, body["gap_id"])
        s["_keymen_ids"] = [k["id"] for k in domain.keymen(doc)]
        try:
            out = await asyncio.wait_for(answer_graph().ainvoke({"rq_id": rq_id, "sid": sid, "body": body, "session": s, "gap": g}),
                                         ANSWER_TIMEOUT)
        except asyncio.TimeoutError as exc:
            raise ApiError(504, "LLM_TIMEOUT", llm.TIMEOUT_MSG) from exc
        s = out["session"]
        s.pop("_keymen_ids", None)
        finished = False
        if s["status"] == "asking" and not s.get("pending_proposal") and not s.get("current_gap_id"):
            await _finish(rq_id, s, None)
            finished = True
        if not finished:
            s = await save(s)
        doc = await repo.require_doc(rq_id)
        return {"outcome": out["outcome"], "log_entry": out.get("log_entry"), "proposal": out.get("proposal"),
                "customer_question": out.get("question"), "session": present(s), "requirement_revision": doc["version"]}


# ── 반영 제안 ────────────────────────────────────────────

async def accept(rq_id: str, sid: str, pid: str, edited: str | None, side: list[dict[str, Any]] | None) -> dict[str, Any]:
    async with repo.lock_for(f"session:{sid}"):
        s = await load(rq_id, sid)
        p = s.get("pending_proposal")
        if s["status"] != "asking" or not p or p["id"] != pid:
            raise ApiError(409, "PROPOSAL_NOT_PENDING", "반영할 제안이 없어요", {"proposal_id": pid})
        g = _gap_by_id(s, p["gap_id"])
        text = (edited or "").strip()[:200] or p["after_text"]
        short = None if edited and edited.strip() != p["after_text"] else p.get("after_short")
        checked = {x["id"]: bool(x["checked"]) for x in side or []}
        sides = [se for se in p.get("side_effects") or [] if checked.get(se["id"], se.get("checked", True))]
        src = {"kind": "deep", "session_id": sid}

        def fn(d: dict[str, Any], rev: int) -> dict[str, Any]:
            info: dict[str, Any] = {"questions": []}
            km = domain.find_keyman(d, p.get("keyman_id") or "")
            item = None
            kind = p["kind"]
            if kind == "replace_item":
                km2, item = domain.find_item(d, p["target"].get("item_id") or "")
                if item is None:
                    kind = "add_item"
                else:
                    km = km2
            if kind == "replace_item":
                info["before"] = item["text"]
                domain.set_item_text(item, text, src, rev=rev, short=short)
                info["item_id"] = item["id"]
            elif kind == "set_field":
                f = p["target"]["field"]
                info["before"] = domain.field_value(d, f)
                domain.set_field(d, f, text, src, rev=rev)
            else:
                if km is None:
                    raise ApiError(409, "TARGET_GONE", "항목을 넣을 키맨이 없어요")
                it = domain.new_item(d, text=text, source=src, rev=rev, short=short)
                domain.insert_item(km, it)
                info["item_id"] = it["id"]
                info["before"] = None
            info["keyman"] = (km or {}).get("name") or "키맨"
            info["keyman_id"] = (km or {}).get("id")
            for se in sides:
                q = service.new_question(rq_id, text=se["question_text"], short_label=se.get("label"),
                                         keyman_id=se.get("keyman_id") or info["keyman_id"],
                                         target={"kind": "item", "id": info["item_id"]} if info.get("item_id") else None,
                                         origin={"kind": "deep_side_effect", "session_id": sid})
                d.setdefault("questions", []).append(q)
                info["questions"].append(q["id"])
            info["kind"] = kind
            return info

        doc, info = await repo.mutate(rq_id, fn)
        label = info["keyman"] if p["kind"] != "set_field" else FIELD_LABELS.get(p["target"].get("field") or "", "칸")
        g["status"] = "applied"
        g["change"] = {"label": label, "before_display": info.get("before"), "after_display": text,
                       "after_short": short, "is_addition": info["kind"] == "add_item", "keyman_id": info.get("keyman_id")}
        g["customer_question_ids"] += info["questions"]
        s.setdefault("created_question_ids", []).extend(info["questions"])
        entry = {"gap_id": g["id"], "kind": "applied", "label": label, "value_display": short or text}
        s["log"].append(entry)
        s["pending_proposal"] = None
        s["completeness"] = domain.completeness(doc, s["gaps"])
        _advance(s)
        if not s.get("current_gap_id"):
            await _finish(rq_id, s, doc)
        else:
            s = await save(s)
        await platform_calls.sync_index(doc)
        return {"log_entry": entry, "created_question_ids": info["questions"], "session": present(s),
                "requirement_revision": doc["version"]}


async def revise(rq_id: str, sid: str, pid: str, instruction: str) -> dict[str, Any]:
    async with repo.lock_for(f"session:{sid}"):
        s = await load(rq_id, sid)
        p = s.get("pending_proposal")
        if s["status"] != "asking" or not p or p["id"] != pid:
            raise ApiError(409, "PROPOSAL_NOT_PENDING", "고칠 제안이 없어요", {"proposal_id": pid})
        g = _gap_by_id(s, p["gap_id"])
        doc = await repo.require_doc(rq_id)
        try:
            newp = await asyncio.wait_for(make_proposal(doc, s, g, p.get("answer_text") or "", instruction=instruction, prev=p),
                                          ANSWER_TIMEOUT)
        except asyncio.TimeoutError as exc:
            raise ApiError(504, "LLM_TIMEOUT", llm.TIMEOUT_MSG) from exc
        s["pending_proposal"] = newp
        s = await save(s)
        return {"proposal": newp, "session": present(s)}


# ── 끝내기 · 취소 ────────────────────────────────────────

async def _finish(rq_id: str, s: dict[str, Any], doc: dict[str, Any] | None) -> dict[str, Any]:
    doc = doc or await repo.require_doc(rq_id)
    if s.get("pending_proposal"):
        g = next((g for g in s["gaps"] if g["id"] == s["pending_proposal"]["gap_id"]), None)
        if g and g["status"] == "proposed":
            g["status"] = "pending"
        s["pending_proposal"] = None
    s["status"] = "finished"
    s["current_gap_id"] = None
    s["completeness"] = domain.completeness(doc, s["gaps"])
    s["completeness_after"] = s["completeness"]
    applied = [g for g in s["gaps"] if g["status"] == "applied" and g.get("change")]
    qids = list(dict.fromkeys(s.get("created_question_ids") or []))
    qmap = {q["id"]: q for q in doc.get("questions") or []}
    s["result"] = {"reinforced_count": len(applied), "changes": [g["change"] for g in applied],
                   "customer_question_ids": qids,
                   "customer_questions": [{"id": q, "text": qmap[q]["text"], "short_label": qmap[q].get("short_label")}
                                          for q in qids if q in qmap]}
    saved = await save(s)
    s.update(saved)
    await _set_doc_deep(rq_id, s, clear=True)
    return s


async def finish(rq_id: str, sid: str) -> dict[str, Any]:
    async with repo.lock_for(f"session:{sid}"):
        s = await load(rq_id, sid)
        if s["status"] == "finished":
            return present(s)
        if s["status"] not in ("asking", "ready"):
            raise ApiError(409, "SESSION_NOT_ACTIVE", "끝낼 수 있는 세션이 아니에요", {"status": s["status"]})
        return present(await _finish(rq_id, s, None))


async def cancel(rq_id: str, sid: str) -> dict[str, Any]:
    async with repo.lock_for(f"session:{sid}"):
        s = await load(rq_id, sid)
        if s["status"] in ("finished", "canceled"):
            return present(s)
        if s["status"] == "analyzing" and s.get("job_id"):
            try:
                await jobs().cancel(s["job_id"])
            except Exception as exc:  # noqa: BLE001 — 잡이 이미 끝났으면 그대로 취소 처리
                log.info("분석 잡 취소 실패(무시): %s", exc)
        s["status"] = "canceled"
        s["pending_proposal"] = None
        s = await save(s)
        await _set_doc_deep(rq_id, s, clear=True)
        return present(s)
