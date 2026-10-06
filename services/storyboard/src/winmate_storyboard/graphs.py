"""LangGraph 워크플로(02-storyboard.md §7) — 워커가 `run_graph` 로 돌린다(체크포인트 data/storyboard/checkpoints.sqlite).

사람 확인은 잡 밖(REST)에서 한다 — 그래프는 interrupt 를 쓰지 않는다(§7.0).
노드는 계산을 먼저 하고 작업본 쓰기는 `service.mutate`(낙관적 잠금)로 자기 부분만 고친다.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import JobContext, current_job

from . import brief, changes, expressions, guards, kbq, llm, repo, rq, rules, service, tracebuild
from .rq import RqSnapshot

log = logging.getLogger("winmate.storyboard.graphs")

PLACES = ["Part 1 서사", "Key considerations · 1-3", "Part 2 공간"]
P1_FALLBACK = ["시장 · 트렌드", "고객의 현재 성과", "이번 제안의 역할", "삼성의 역할", "기대 효과", "도입 로드맵"]
P3_FALLBACK = ["실행 역량", "지원 체계"]


# ── 공통 ──────────────────────────────────────────────────

def _ctx() -> JobContext:
    c = current_job()
    if c is None:  # pragma: no cover — 그래프는 잡 안에서만 돈다
        raise RuntimeError("잡 맥락 없음")
    return c


def pace_s() -> float:
    """시연 · e2e 용 속도(초): mock 모델은 너무 빨라 진행 화면(SB3G · 스켈레톤)이 안 보인다.
    `SB_PACE_S` 가 있으면 그 값(0 = 끔), 없으면 MODEL_MODE=mock 일 때 0.45초 · 실제 모델이면 0."""
    raw = os.environ.get("SB_PACE_S")
    if raw is not None:
        try:
            return max(0.0, min(5.0, float(raw)))
        except ValueError:
            return 0.0
    from winmate_common.env import settings as common_settings
    return 0.45 if common_settings().model_mode == "mock" else 0.0


async def pace(mult: float = 1.0) -> None:
    s = pace_s() * mult
    if s > 0:
        await asyncio.sleep(s)


async def prog(pct: float, message: str) -> None:
    pct = max(0, min(100, int(pct)))
    await _ctx().progress(pct, message, ratio=round(pct / 100, 3))


async def emit_step(key: str, label: str, state: str, done: int | None = None, total: int | None = None) -> None:
    data: dict[str, Any] = {"key": key, "label": label, "state": state}
    if done is not None:
        data["done"] = done
    if total is not None:
        data["total"] = total
    c = _ctx()
    await c.jobs.emit(c.job.id, "step", data)


async def snapshot_of(doc: dict[str, Any], version: int | None = None) -> RqSnapshot:
    ref = doc.get("requirement_ref") or {}
    if not ref.get("requirement_id"):
        raise ApiError(422, "RQ_NOT_SAVED", "요구사항 정의서가 없어요")
    return await rq.get_snapshot(ref["requirement_id"], int(version or ref["version"]))


def _slug(text: str, used: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_") or "space"
    key, n = base, 2
    while key in used:
        key, n = f"{base}_{n}", n + 1
    used.add(key)
    return key


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _evidence_names(snap: RqSnapshot) -> str:
    parts = snap.items_text() + [i.short for i in snap.items]
    for i in snap.items:
        for e in i.entities:
            parts += [str(e.get("name") or ""), str(e.get("surface") or "")]
    for k in ("products", "solutions"):
        for p in snap.context.get(k) or []:
            if isinstance(p, dict):
                parts.append(str(p.get("name") or ""))
    return _norm(" ".join(parts)).casefold()


_GENERIC = {"ai", "the", "스마트", "솔루션", "시스템", "서비스", "디지털", "플랫폼", "데이터", "pro", "plus"}


def is_extension_product(name: str, evidence: str) -> bool:
    """정의서 근거 없는 제품 후보 = 확장. 이름의 핵심 토큰(흔한 말 제외)이 정의서 글에 있으면 근거 있음."""
    toks = [t for t in re.split(r"[\s·/,()]+", name) if len(t) >= 2 and t.casefold() not in _GENERIC]
    if not toks:
        return _norm(name).casefold() not in evidence
    return not any(_norm(t).casefold() in evidence for t in toks)


def products_of(raw: list[dict[str, Any]], evidence: str, limit: int = 6) -> list[dict[str, Any]]:
    out, seen = [], set()
    for p in raw:
        name = (p.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "kb_ref": p.get("kb_ref"), "is_extension": is_extension_product(name, evidence)})
    return out[:limit]


def allowed_numbers(snap: RqSnapshot, doc: dict[str, Any], *extra: Any) -> set[str]:
    texts: list[str] = snap.customer_facing_text()
    for a in brief.answers_brief(doc):
        texts += a["answer_in_order"]
    for x in extra:
        if isinstance(x, str):
            texts.append(x)
        elif isinstance(x, (list, tuple)):
            texts += [str(v) for v in x]
        elif isinstance(x, dict):
            texts.append(str(x))
    nums = guards.numbers_in(texts)
    outline = doc.get("outline") or {}
    nums |= {str(len(snap.items)), str(len(outline.get("spaces") or [])), str(len(outline.get("sections") or []))}
    return nums


def guard_line(text: str, allowed: set[str]) -> dict[str, Any]:
    text, _ = guards.number_guard(text.strip(), allowed)
    return {"text": text, "tokens": rules.tokens_of(text), "claim": bool(guards.find_claims(text))}


# ── sb_prepare(§7.2) ───────────────────────────────────────

class PrepState(TypedDict, total=False):
    sb_id: str
    kb: dict[str, Any]
    settings: dict[str, Any]
    name: str
    topics: list[str]
    questions: list[dict[str, Any]]


async def p_load_rq(state: PrepState) -> PrepState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    await prog(15, f"정의서 v{snap.version} 읽는 중")
    await pace(3)
    return {}


async def p_kb_context(state: PrepState) -> PrepState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    vid, vname = snap.vertical_id(), None
    if not vid:
        vid, vname = await kbq.vertical_for(" ".join([snap.title, snap.project_name] + snap.items_text()))
    preset = await kbq.preset(vid) if vid else {}
    await prog(30, "업종 · 공간 맥락 찾는 중")
    return {"kb": {"vertical": vid, "vertical_name": vname, "spaces": kbq.preset_spaces(preset), "scenes": kbq.scene_lines(preset)}}


async def p_derive_settings(state: PrepState) -> PrepState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    out = await llm.call("sb.prepare_settings", llm.p_settings(brief.rq_brief(snap)), llm.SbSettings)
    s: dict[str, Any] = {}
    if out.get("stage"):
        s["stage"] = {"value": out["stage"], "source": "rq", "evidence": (out.get("stage_evidence") or "").strip() or None}
    else:
        s["stage"] = {"value": "concept", "source": "default", "evidence": None}
    if snap.customer_name:
        s["doc_type"] = {"value": "custom", "source": "rq", "evidence": f"고객사: {snap.customer_name}"}
    else:
        s["doc_type"] = {"value": "common_pitch", "source": "default", "evidence": "공통 Pitch deck은 여러 고객에게 쓸 때"}
    # 공간 수: 정의서 맥락의 공간 → 없으면 정의서 내용으로 고른 업종의 KB 공간(둘 다 정의서에서 읽은 값)
    n = len(snap.spaces()) or len((state.get("kb") or {}).get("spaces") or [])
    if n:
        s["volume"] = {"value": rules.volume_for_spaces(n), "source": "rq", "evidence": rules.volume_hint(n)}
    else:
        s["volume"] = {"value": 20, "source": "default", "evidence": None}
    has_ko = any(re.search(r"[가-힣]", t) for t in snap.items_text())
    lang = out.get("language") or ("ko" if has_ko else None)
    if lang:
        s["language"] = {"value": lang, "source": "rq", "evidence": out.get("language_hint") or "정의서 언어"}
    else:
        s["language"] = {"value": "ko", "source": "default", "evidence": None}
    short = (out.get("short_name") or "").strip()
    if short:
        name = f"{short} 제안 기획"
    else:
        name = snap.project_name or snap.title
    if snap.customer_name and name.startswith(snap.customer_name):
        name = name[len(snap.customer_name):].strip() or name
    await prog(50, "설정 읽음")
    return {"settings": s, "name": name}


async def p_pick_questions(state: PrepState) -> PrepState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    out = await llm.call("sb.pick_questions", llm.p_pick(brief.rq_brief(snap, internal=True)), llm.SbQuestionPick)
    cands = [c for c in out.get("candidates") or [] if not c.get("answerable_from_rq") and int(c.get("impact") or 0) >= 2
             and c.get("topic") in rules.QUESTION_ORDER]
    cands.sort(key=lambda c: (-int(c["impact"]), rules.QUESTION_ORDER.index(c["topic"])))
    topics: list[str] = []
    for c in cands:
        if c["topic"] not in topics:
            topics.append(c["topic"])
    topics = sorted(topics[:3], key=rules.QUESTION_ORDER.index)
    await prog(65, f"영향 큰 질의 {len(topics)}개")
    return {"topics": topics}


async def p_make_options(state: PrepState) -> PrepState:
    topics = state.get("topics") or []
    if not topics:
        return {"questions": []}
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    out = await llm.call("sb.planning_questions", llm.p_questions(brief.rq_brief(snap, internal=True), topics),
                         llm.SbPlanningQuestions)
    by_topic = {q.get("topic"): q for q in out.get("questions") or []}
    questions: list[dict[str, Any]] = []
    for topic in topics:
        copy_ = rules.QUESTION_COPY[topic]
        lq = by_topic.get(topic) or {}
        opts: list[dict[str, Any]] = []
        for o in lq.get("options") or []:
            label = (o.get("label") or "").strip()
            if not label or any(x["label"] == label for x in opts):
                continue
            fu = None
            if topic == "comparison" and o.get("follow_up"):
                f = o["follow_up"]
                fopts = [{"id": new_id("opt"), "label": (fo.get("label") or rules.FOLLOWUP_LABELS[fo["effect"]]),
                          "effect": fo["effect"]} for fo in f.get("options") or [] if fo.get("effect") in rules.FOLLOWUP_LABELS]
                if not fopts:
                    fopts = [{"id": new_id("opt"), "label": lab, "effect": eff} for eff, lab in rules.FOLLOWUP_LABELS.items()]
                fu = {"label": "이어서 하나만", "text": f.get("text") or "", "options": fopts}
            opts.append({"id": new_id("opt"), "label": label[:80], "hint": o.get("hint"), "badge": o.get("badge"), "follow_up": fu,
                         "recommended": bool(o.get("recommended")), "custom": False})
        if topic == "audience":
            if snap.final_audience:
                if not any(snap.final_audience in x["label"] for x in opts):
                    opts.append({"id": new_id("opt"), "label": snap.final_audience, "hint": "최종 제안대상", "badge": None,
                                 "follow_up": None, "recommended": False, "custom": False})
            elif not any("의사결정자" in x["label"] for x in opts):
                opts = opts[:3]
                opts.append({"id": new_id("opt"), "label": "최종 의사결정자", "hint": "누구인지 아직 몰라요", "badge": "확인 필요",
                             "follow_up": None, "recommended": False, "custom": False})
            else:
                for x in opts:
                    if "의사결정자" in x["label"]:
                        x.update(badge="확인 필요", hint="누구인지 아직 몰라요")
        opts = opts[:4]
        if not opts:
            continue
        questions.append({"id": new_id("pq"), "order": len(questions) + 1, "topic": topic, "topic_label": copy_["topic_label"],
                          "text": copy_["text"] if topic in ("decision", "audience", "comparison") else (lq.get("text") or copy_["text"]),
                          "info": copy_["info"] if topic in ("decision", "audience", "comparison") else (lq.get("info") or copy_["info"]),
                          "select": copy_["select"], "order_roles": list(copy_["order_roles"]),
                          "allow_custom": copy_["allow_custom"], "options": opts, "affects": list(copy_["affects"])})
    await prog(85, "선택지를 만들었어요")
    return {"questions": questions}


async def p_save(state: PrepState) -> PrepState:
    doc0 = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc0)
    version = snap.version

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        ref = d.get("requirement_ref") or {}
        if int(ref.get("version") or 0) != version or ref.get("requirement_id") != snap.requirement_id:
            return None   # 그 사이 정의서를 바꿨다 — 새 prepare 가 쓴다
        s = d["settings"]
        for key, val in (state.get("settings") or {}).items():
            if s.get(key, {}).get("source") != "user":
                s[key] = val
        s["ready"] = True
        d["planning"] = {"questions": state.get("questions") or [], "answers": []}
        d["name"] = state.get("name") or d.get("name")
        d["customer_name"] = snap.customer_name or d.get("customer_name")
        ref.update(item_count=len(snap.items), title=snap.title, customer_name=snap.customer_name or ref.get("customer_name"),
                   version_note=snap.note, saved_at=snap.saved_at or ref.get("saved_at"))
        d["requirement_ref"] = ref
        d["kb_context"] = state.get("kb") or {}
        return d

    doc = await service.mutate(state["sb_id"], fn)
    ref = doc.get("requirement_ref") or {}
    await rq.put_link(ref["requirement_id"], doc["id"], title=doc.get("title") or "", route=doc.get("route") or "",
                      rq_version=int(ref["version"]), depends_on=tracebuild.depends_on(doc))
    await prog(100, "준비됐어요")
    return {}


def build_prepare() -> StateGraph:
    g = StateGraph(PrepState)
    for name, fn in (("load_rq", p_load_rq), ("kb_context", p_kb_context), ("derive_settings", p_derive_settings),
                     ("pick_questions", p_pick_questions), ("make_options", p_make_options), ("save", p_save)):
        g.add_node(name, fn)
    g.add_edge(START, "load_rq")
    for a, b in (("load_rq", "kb_context"), ("kb_context", "derive_settings"), ("derive_settings", "pick_questions"),
                 ("pick_questions", "make_options"), ("make_options", "save")):
        g.add_edge(a, b)
    g.add_edge("save", END)
    return g


# ── sb_direction / sb_messages(§7.3) ─────────────────────────

class DirState(TypedDict, total=False):
    sb_id: str
    classes: dict[str, Any]
    axes: list[dict[str, Any]]
    kb_msgs: list[str]
    options: list[dict[str, Any]]
    recommended: str
    messages: list[dict[str, Any]]
    memos: list[dict[str, Any]]


async def d_classify(state: DirState) -> DirState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    out = await llm.call("sb.classify_items", llm.p_classify(brief.rq_brief(snap, internal=True)), llm.SbItemClasses)
    phrases = [p.strip() for p in out.get("internal_goal_phrases") or [] if p and p.strip()][:5]
    await prog(20, "요구를 주제로 묶었어요")
    await pace(3)
    return {"classes": {"items": out.get("items") or [], "phrases": phrases}}


async def d_axes(state: DirState) -> DirState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    out = await llm.call("sb.axes", llm.p_axes(brief.rq_brief(snap), state.get("classes") or {}, brief.answers_brief(doc)),
                         llm.SbAxes)
    axes = []
    for i, ax in enumerate((out.get("axes") or [])[:3]):
        axes.append({"key": "ABC"[i], "title": (ax.get("title") or "").strip(), "one_liner": (ax.get("one_liner") or "").strip(),
                     "codes": [rq.normalize_code(c) for c in ax.get("codes") or []]})
    if not axes:
        raise ApiError(503, "LLM_UNAVAILABLE", "기획 축을 만들지 못했어요. 잠시 후 다시 시도해 주세요.")
    await prog(40, "기획 축 3개")
    return {"axes": axes}


async def d_kb_messages(state: DirState) -> DirState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    msgs: list[str] = []
    for ax in state.get("axes") or []:
        msgs += await kbq.theme_messages(f"{ax['title']} {ax['one_liner']}", 3)
    kbc = doc.get("kb_context") or {}
    msgs += await kbq.messages_for(kbc.get("vertical") or snap.vertical_id(), [s["key"] for s in kbc.get("spaces") or [] if s.get("key")],
                                   " ".join(snap.items_text()))
    seen: list[str] = []
    for m in msgs:
        if m not in seen:
            seen.append(m)
    await prog(55, "KB 원문 메시지 후보")
    return {"kb_msgs": seen[:12]}


async def d_combo(state: DirState) -> DirState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    by_code = {i.code: i.id for i in snap.items}
    total = len(snap.items)
    axes = state.get("axes") or []
    options: list[dict[str, Any]] = []
    union: list[str] = []
    for ax in axes:
        ids = []
        for c in ax["codes"]:
            if c in by_code and by_code[c] not in ids:
                ids.append(by_code[c])
        for i in ids:
            if i not in union:
                union.append(i)
        label = f"{ax['key']} {ax['title']}"
        options.append({"id": new_id("dir"), "kind": "axis", "key": ax["key"], "title": ax["title"], "one_liner": ax["one_liner"],
                        "coverage": {"item_ids": ids, "codes": [c for c in ax["codes"] if c in by_code], "count": len(ids), "total": total},
                        "mapping": [{"place_label": p, "axis_key": ax["key"], "axis_label": label} for p in PLACES]})
    out = await llm.call("sb.combo", llm.p_combo(axes, brief.rq_brief(snap)), llm.SbCombo)
    code_of = {v: k for k, v in by_code.items()}
    combo = {"id": new_id("dir"), "kind": "combo", "key": None, "title": (out.get("title") or "추천 조합").strip(),
             "one_liner": (out.get("one_liner") or "세 축을 파트별로 나눠 써요").strip(),
             "coverage": {"item_ids": union, "codes": sorted(code_of[i] for i in union), "count": len(union), "total": total},
             "mapping": [{"place_label": PLACES[i], "axis_key": ax["key"], "axis_label": f"{ax['key']} {ax['title']}"}
                         for i, ax in enumerate(axes)]}
    single = next((o for o in options if total and o["coverage"]["count"] == total), None)
    rec = single["id"] if single else combo["id"]
    await prog(70, "추천 조합")
    return {"options": [combo, *options], "recommended": rec}


async def _draft_messages(doc: dict[str, Any], option: dict[str, Any], kb_msgs: list[str]) -> list[dict[str, Any]]:
    snap = await snapshot_of(doc)
    places = option.get("mapping") or []
    out = await llm.call("sb.key_messages", llm.p_messages(places, brief.rq_brief(snap), brief.answers_brief(doc), kb_msgs,
                                                           (doc.get("direction") or {}).get("extra_direction")), llm.SbKeyMessages)
    got = out.get("messages") or []
    audience = brief.audience_order(doc)
    fallback_aud = (audience[0] if audience else None) or snap.final_audience or "청중 확인 필요"
    msgs = []
    for i, place in enumerate(places):
        m = next((x for x in got if x.get("place_label") == place["place_label"]), None) or (got[i] if i < len(got) else None)
        if not m or not (m.get("text") or "").strip():
            continue
        msgs.append({"id": new_id("kmsg"), "place_label": place["place_label"], "axis_key": place["axis_key"],
                     "axis_label": place["axis_label"], "audience": (m.get("audience") or fallback_aud).strip(),
                     "text": m["text"].strip(), "flags": [], "evidence": [], "kb_refs": list(m.get("kb_refs") or []),
                     "updated_by": "llm"})
    return msgs


async def d_draft_messages(state: DirState) -> DirState:
    doc = await repo.require_sb(state["sb_id"])
    if state.get("options"):
        option = next(o for o in state["options"] if o["id"] == state["recommended"])
        kb_msgs = state.get("kb_msgs") or []
    else:   # sb_messages — 지금 고른 안으로
        option = brief.selected_option(doc) or {}
        kb_msgs = []
    msgs = await _draft_messages(doc, option, kb_msgs)
    await prog(85, f"핵심 메시지 {len(msgs)}문장")
    return {"messages": msgs}


async def d_check_expressions(state: DirState) -> DirState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    phrases = (state.get("classes") or {}).get("phrases") if state.get("classes") else doc.get("internal_phrases") or []
    allowed = allowed_numbers(snap, doc, state.get("kb_msgs") or [])
    msgs, memos = [], []
    for m in state.get("messages") or []:
        text, _ = guards.number_guard(m["text"], allowed)
        text, flags, new_memos = await expressions.check(text, internal_phrases=phrases or [], use_llm=True)
        msgs.append({**m, "text": text, "flags": flags})
        memos += new_memos
    await prog(95, "표현 검사")
    return {"messages": msgs, "memos": memos}


async def d_save(state: DirState) -> DirState:
    doc0 = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc0)
    classes = state.get("classes") or {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        old = d.get("direction") or {}
        memos = list(state.get("memos") or [])
        if snap.author_note:
            memos.insert(0, {"text": snap.author_note, "from": "rq_author_note", "flag_id": None})
        d["direction"] = {"options": state["options"], "recommended_option_id": state["recommended"],
                          "selected_option_id": state["recommended"], "key_messages": state.get("messages") or [],
                          "extra_direction": old.get("extra_direction"), "internal_memos": memos,
                          "internal_goal_count": len(classes.get("phrases") or []), "total": len(snap.items), "ready": True}
        d["item_classes"] = classes.get("items") or []
        d["internal_phrases"] = classes.get("phrases") or []
        return d

    await service.mutate(state["sb_id"], fn)
    await prog(100, "기획 방향을 만들었어요")
    return {}


async def m_save(state: DirState) -> DirState:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        dr = d["direction"]
        flag_memos = list(state.get("memos") or [])
        dr["key_messages"] = state.get("messages") or []
        dr["internal_memos"] = [m for m in dr.get("internal_memos") or [] if m.get("from") == "rq_author_note"] + flag_memos
        dr["ready"] = True
        return d

    await service.mutate(state["sb_id"], fn)
    await prog(100, "핵심 메시지를 다시 썼어요")
    return {}


def _chain(state_cls: type, nodes: list[tuple[str, Any]]) -> StateGraph:
    g = StateGraph(state_cls)
    for name, fn in nodes:
        g.add_node(name, fn)
    g.add_edge(START, nodes[0][0])
    for (a, _), (b, _) in zip(nodes, nodes[1:]):
        g.add_edge(a, b)
    g.add_edge(nodes[-1][0], END)
    return g


def build_direction() -> StateGraph:
    return _chain(DirState, [("classify_items", d_classify), ("propose_axes", d_axes), ("kb_messages", d_kb_messages),
                             ("build_combo", d_combo), ("draft_messages", d_draft_messages),
                             ("check_expressions", d_check_expressions), ("save", d_save)])


def build_messages() -> StateGraph:
    return _chain(DirState, [("draft_messages", d_draft_messages), ("check_expressions", d_check_expressions), ("save", m_save)])


# ── sb_outline(§7.4) ───────────────────────────────────────

class OutState(TypedDict, total=False):
    sb_id: str
    retry: bool
    plan: list[dict[str, Any]]
    section_labels: dict[str, list[str]]


def _writing(d: dict[str, Any], **kw: Any) -> None:
    ol = d.setdefault("outline", {"groups": [], "sections": [], "spaces": [], "discussions": [], "ready": False})
    w = ol.get("writing") or {"done": 0, "total": 0, "stage": None}
    w.update(kw)
    ol["writing"] = w


async def o_classify(state: OutState) -> OutState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    phrases = doc.get("internal_phrases") or []
    if not doc.get("item_classes"):
        out = await llm.call("sb.classify_items", llm.p_classify(brief.rq_brief(snap, internal=True)), llm.SbItemClasses)
        phrases = [p.strip() for p in out.get("internal_goal_phrases") or [] if p and p.strip()][:5]

        def keep(d: dict[str, Any]) -> dict[str, Any]:
            d["item_classes"] = out.get("items") or []
            d["internal_phrases"] = phrases
            return d

        await service.mutate(state["sb_id"], keep, content=False)
    label = f"요구 {len(snap.items)}개 분류 · 내부 목표 {len(phrases)}개 분리"
    await emit_step("classify", label, "running")
    await service.mutate(state["sb_id"], lambda d: (_writing(d, stage="map_axes"), d)[1], content=False)
    await emit_step("classify", label, "done")
    await prog(10, label)
    return {}


async def o_map_axes(state: OutState) -> OutState:
    label = "기획 축을 파트에 반영"
    await emit_step("map_axes", label, "running")
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    volume = int(doc["settings"]["volume"]["value"])
    counts = rules.SKELETON.get(volume, rules.SKELETON[20])
    out = await llm.call("sb.skeleton", llm.p_skeleton(volume, counts, brief.direction_brief(doc), brief.rq_brief(snap),
                                                       brief.answers_brief(doc)), llm.SbSkeleton)
    names = out.get("group_names") or {}
    p1 = [s["name"].strip() for s in out.get("sections") or [] if s.get("group_key") == "part1" and s.get("name")]
    p3 = [s["name"].strip() for s in out.get("sections") or [] if s.get("group_key") == "part3" and s.get("name")]
    p1 = (p1 + [n for n in P1_FALLBACK if n not in p1])[: counts["part1"]]
    p3 = (p3 + [n for n in P3_FALLBACK if n not in p3])[: counts["part3"]]
    plan: list[dict[str, Any]] = []
    for key, name in rules.START_SECTIONS:
        plan.append({"key": key, "group_key": "start", "code": None, "name": name})
    for i, name in enumerate(p1, 1):
        plan.append({"key": f"p1_{i}", "group_key": "part1", "code": f"1-{i}", "name": name})
    plan.append({"key": "part2", "group_key": "part2", "code": "Part 2", "name": "공간 시나리오"})
    for i, name in enumerate(p3, 1):
        plan.append({"key": f"p3_{i}", "group_key": "part3", "code": "Part 3" if len(p3) == 1 else f"3-{i}", "name": name})
    for key, name in rules.END_SECTIONS:
        plan.append({"key": key, "group_key": "end", "code": None, "name": name})
    for i, p in enumerate(plan, 1):
        p["order"] = i
    groups = [
        {"key": "start", "order": 1, "name": "시작"},
        {"key": "part1", "order": 2, "name": f"Part 1 {names.get('part1') or '사업 논리'}"},
        {"key": "part2", "order": 3, "name": f"Part 2 {names.get('part2') or '공간 시나리오'}"},
        {"key": "part3", "order": 4, "name": f"Part 3 {names.get('part3') or '실행 역량'}"},
        {"key": "end", "order": 5, "name": "마무리"},
    ]
    retry = bool(state.get("retry"))

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        ol = d.get("outline") or {}
        existing = {s["key"]: s for s in ol.get("sections") or []} if retry else {}
        sections = []
        for p in plan:
            old = existing.get(p["key"])
            if old and old.get("written") and old.get("name") == p["name"]:
                sections.append({**old, "order": p["order"]})
            else:
                sections.append({"id": (old or {}).get("id") or new_id("sec"), "key": p["key"], "group_key": p["group_key"],
                                 "order": p["order"], "code": p["code"], "name": p["name"], "direction": "", "lines": [],
                                 "products": [], "status": "writing", "tbd_reason": None, "internal_memo": None,
                                 "discussion_ids": [], "written": False})
        d["outline"] = {"groups": [{**g, "meta": "", "summary": "", "badges": [], "section_ids": []} for g in groups],
                        "sections": sections, "spaces": ol.get("spaces") if retry else [],
                        "discussions": ol.get("discussions") if retry else [],
                        "writing": {"done": sum(1 for s in sections if s.get("written")), "total": len(sections),
                                    "stage": "write_sections"}, "ready": False}
        d["group_summaries"] = out.get("group_summaries") or {}
        d["owners"] = out.get("owners") or None
        return d

    await service.mutate(state["sb_id"], fn)
    await emit_step("map_axes", label, "done")
    await prog(20, label)
    return {"plan": plan}


def _section_ctx(doc: dict[str, Any], snap: RqSnapshot, sec: dict[str, Any], reco: list[dict[str, Any]]) -> dict[str, Any]:
    answers = brief.answers_brief(doc)
    effects = [a for a in answers if any(sec["key"] in rules.UNKNOWN_AFFECTS.get(a["topic"], []) for _ in [0])]
    return {
        "rq": brief.rq_brief(snap), "answers": answers, "answers_for_this_section": effects,
        "direction": brief.direction_brief(doc), "settings": doc["settings"].get("summary"),
        "kb": {"vertical": (doc.get("kb_context") or {}).get("vertical"), "scenes": (doc.get("kb_context") or {}).get("scenes"),
               "product_candidates": reco[:6]},
        "rule": "Part 3 레퍼런스 후보는 사람이 고르기 전이면 tbd_reason 을 쓴다." if sec["group_key"] == "part3" else None,
    }


async def _write_spaces(doc: dict[str, Any], snap: RqSnapshot, reco: list[dict[str, Any]]) -> list[dict[str, Any]]:
    volume = int(doc["settings"]["volume"]["value"])
    cap = rules.SKELETON.get(volume, rules.SKELETON[20])["spaces"]
    kbc = doc.get("kb_context") or {}
    rq_spaces = snap.spaces()
    cands = [{"key": s.get("id") or "", "name": s["name"], "from": "rq"} for s in rq_spaces]
    cands += [{"key": s["key"], "name": s["name"], "from": "kb"} for s in kbc.get("spaces") or []
              if not any(s["name"] == c["name"] for c in cands)]
    axis_c = next((o for o in (doc.get("direction") or {}).get("options") or [] if o.get("key") == "C"), None)
    ctx = {"rq": brief.rq_brief(snap), "axis_C": axis_c and {"title": axis_c["title"], "one_liner": axis_c["one_liner"]},
           "answers": brief.answers_brief(doc), "kb_scenes": kbc.get("scenes"), "product_candidates": reco[:8]}
    out = await llm.call("sb.spaces", llm.p_spaces(cands, cap, ctx), llm.SbSpaces)
    evidence = _evidence_names(snap)
    allowed = allowed_numbers(snap, doc, reco, kbc.get("scenes") or [])
    rq_keys = {(s.get("id") or "").lower() for s in rq_spaces} | {_norm(s["name"]) for s in rq_spaces}
    used: set[str] = set()
    spaces = []
    for s in (out.get("spaces") or [])[:cap]:
        name = (s.get("name") or "").strip()
        if not name:
            continue
        key = _slug(s.get("key") or name, used)
        grounded = (key in rq_keys or _norm(name) in rq_keys or (s.get("key") or "").lower() in rq_keys) if rq_spaces \
            else bool(s.get("from_rq", True))
        slots: dict[str, Any] = {k: {"state": "empty", "segments": [], "source": None, "answer": None, "customer_question_id": None}
                                 for k in rules.SLOT_KEYS}
        for st in s.get("slots") or []:
            text = (st.get("text") or "").strip()
            if st.get("slot") in slots and text:
                g = guard_line(text, allowed)
                slots[st["slot"]] = {"state": "filled", "segments": [{"text": g["text"], "ai_added": False}], "source": "outline",
                                     "answer": None, "customer_question_id": None}
        spaces.append({"id": new_id("spc"), "key": key, "order": len(spaces) + 1, "name": name, "purpose": (s.get("purpose") or "").strip(),
                       "is_extension": not grounded, "status": "draft", "slots": slots, "filled_count": 0,
                       "products": products_of(s.get("products") or [], evidence), "questions": [], "customer_question_ids": [],
                       "added_questions": [], "composing": False})
    return spaces


async def o_write_sections(state: OutState) -> OutState:
    sb_id = state["sb_id"]
    doc = await repo.require_sb(sb_id)
    snap = await snapshot_of(doc)
    sections = doc["outline"]["sections"]
    total = len(sections)
    label = f"섹션 {total}개 작성 방향 쓰기"
    done = sum(1 for s in sections if s.get("written"))
    await emit_step("write_sections", label, "running", done, total)
    reco = await kbq.recommend(" ".join(snap.items_text())) if snap.items else []
    evidence = _evidence_names(snap)
    section_labels: dict[str, list[str]] = dict(state.get("section_labels") or {})
    for sec in sections:
        if sec.get("written"):
            continue
        await _ctx().check_cancel()
        doc = await repo.require_sb(sb_id)
        allowed = allowed_numbers(snap, doc, reco, (doc.get("kb_context") or {}).get("scenes") or [])
        update: dict[str, Any] = {}
        spaces: list[dict[str, Any]] | None = None
        if sec["key"] == "timeline":
            phases = doc["schedule"]["phases"]
            update = {"direction": rules.timeline_direction(phases),
                      "lines": [{"id": f"l{i}", "text": f"D-{p['d_from']} ~ D-{p['d_to']} {p['name']} — {p['owner']}", "tokens": [],
                                 "reviewing": False, "claim": False} for i, p in enumerate(phases, 1)],
                      "products": [], "tbd_reason": None}
        else:
            if sec["key"] == "part2":
                spaces = await _write_spaces(doc, snap, reco)
            out = await llm.call(f"sb.section.{sec['key']}", llm.p_section(
                {"key": sec["key"], "group": sec["group_key"], "code": sec.get("code"), "name": sec["name"]},
                _section_ctx(doc, snap, sec, reco)), llm.SbSection)
            lines = []
            for i, ln in enumerate(out.get("lines") or [], 1):
                if not (ln.get("text") or "").strip():
                    continue
                g = guard_line(ln["text"], allowed)
                lines.append({"id": f"l{len(lines) + 1}", "text": g["text"], "tokens": g["tokens"], "reviewing": bool(ln.get("reviewing")),
                              "claim": g["claim"]})
            direction, _ = guards.number_guard((out.get("direction") or "").strip(), allowed)
            update = {"direction": direction[:60], "lines": lines, "products": products_of(out.get("products") or [], evidence),
                      "tbd_reason": (out.get("tbd_reason") or "").strip() or None,
                      "internal_memo": (out.get("internal_memo") or "").strip() or None}
            labs = [x.strip() for x in out.get("discussion_labels") or [] if x and x.strip()]
            if labs:
                section_labels[sec["id"]] = labs

        def fn(d: dict[str, Any], sec_id: str = sec["id"], update: dict[str, Any] = update,
               spaces: list[dict[str, Any]] | None = spaces) -> dict[str, Any]:
            target = next((s for s in d["outline"]["sections"] if s["id"] == sec_id), None)
            if target is None:
                return d
            target.update(update)
            target["written"] = True
            if spaces is not None:
                d["outline"]["spaces"] = spaces
            _writing(d, done=sum(1 for s in d["outline"]["sections"] if s.get("written")), stage="write_sections")
            return d

        doc = await service.mutate(sb_id, fn)
        done = doc["outline"]["writing"]["done"]
        await emit_step("write_sections", label, "running", done, total)
        await pace()
        await prog(20 + 60 * done / max(1, total), f"섹션 {done} / {total}")
    await emit_step("write_sections", label, "done", total, total)
    return {"section_labels": section_labels}


async def _compute_trace(doc: dict[str, Any], snap: RqSnapshot, prev: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    items = [{"code": i.code, "text": i.text, "short": i.short, "keyman": i.keyman_name, "needs_confirmation": i.needs_confirmation}
             for i in snap.items]
    ctx = {"direction": brief.direction_brief(doc), "extensions_hint": "정의서에 없는 공간 · 제품은 extensions 로"}
    out = await llm.call("sb.trace", llm.p_trace(items, brief.place_catalog(doc), ctx), llm.SbTrace)
    return tracebuild.build_trace(doc, snap, out, prev), out


async def o_trace(state: OutState) -> OutState:
    label = "요구 → 섹션 연결"
    await emit_step("trace", label, "running")
    sb_id = state["sb_id"]
    doc = await repo.require_sb(sb_id)
    snap = await snapshot_of(doc)
    with_writing = doc
    trace, out = await _compute_trace(with_writing, snap, None)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["trace"] = trace
        d["outline"]["discussions"] = tracebuild.merge_discussions(d, state.get("section_labels") or {}, out.get("discussions") or [],
                                                                   d["outline"].get("discussions"))
        _writing(d, stage="trace")
        return d

    await service.mutate(sb_id, fn)
    await emit_step("trace", label, "done")
    await prog(95, label)
    return {}


async def o_finalize(state: OutState) -> OutState:
    sb_id = state["sb_id"]

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["outline"]["ready"] = True
        d["outline"]["writing"] = None
        if int(d.get("step") or 1) < 3:
            d["step"] = 3
        return d

    doc = await service.mutate(sb_id, fn)
    ref = doc["requirement_ref"]
    await rq.put_link(ref["requirement_id"], sb_id, title=doc.get("title") or "", route=doc.get("route") or "",
                      rq_version=int(ref["version"]), depends_on=tracebuild.depends_on(doc))
    await prog(100, "목차와 서사를 썼어요")
    return {}


def build_outline() -> StateGraph:
    return _chain(OutState, [("classify", o_classify), ("map_axes", o_map_axes), ("write_sections", o_write_sections),
                             ("trace", o_trace), ("finalize", o_finalize)])


# ── sb_space_questions / sb_space_compose(§7.5) ──────────────

class SpaceState(TypedDict, total=False):
    sb_id: str
    space_id: str
    ctx: dict[str, Any]
    composed: dict[str, Any]
    added: list[dict[str, Any]]


def _space_of(doc: dict[str, Any], spc: str) -> dict[str, Any]:
    sp = next((s for s in (doc.get("outline") or {}).get("spaces") or [] if s["id"] == spc), None)
    if sp is None:
        raise ApiError(404, "NOT_FOUND", f"공간을 찾을 수 없어요: {spc}")
    return sp


def _space_brief(sp: dict[str, Any]) -> dict[str, Any]:
    return {"name": sp["name"], "purpose": sp.get("purpose"), "is_extension": sp.get("is_extension"),
            "slots": {k: rules.slot_text((sp.get("slots") or {}).get(k)) for k in rules.SLOT_KEYS},
            "products": [p["name"] for p in sp.get("products") or []]}


async def s_scene_context(state: SpaceState) -> SpaceState:
    doc = await repo.require_sb(state["sb_id"])
    sp = _space_of(doc, state["space_id"])
    kbc = doc.get("kb_context") or {}
    scenes = await kbq.scene(kbc.get("vertical"), sp.get("key"))
    reco = await kbq.recommend(f"{sp['name']} {sp.get('purpose') or ''}", limit=4)
    await prog(35, f"{sp['name']} 장면 · 제품 맥락")
    return {"ctx": {"scenes": scenes, "product_candidates": reco}}


async def s_make_questions(state: SpaceState) -> SpaceState:
    doc = await repo.require_sb(state["sb_id"])
    sp = _space_of(doc, state["space_id"])
    empty = [k for k in rules.SLOT_KEYS if ((sp.get("slots") or {}).get(k) or {}).get("state", "empty") == "empty"]
    questions: list[dict[str, Any]] = []
    if empty:
        out = await llm.call(f"sb.slot_questions.{sp.get('key') or 'space'}", llm.p_slot_questions(_space_brief(sp), empty,
                                                                                                state.get("ctx") or {}),
                             llm.SbSlotQuestions)
        by_slot = {q.get("slot"): q for q in out.get("questions") or []}
        for k in empty:
            lq = by_slot.get(k) or {}
            opts = [{"id": new_id("opt"), "label": o.strip()[:80]} for o in (lq.get("options") or []) if o and o.strip()][:4]
            text = (lq.get("text") or f"{sp['name']}의 {rules.SLOT_SHORT[k]}{rules.eun(rules.SLOT_SHORT[k])} 어떻게 할까요?").strip()
            questions.append({"slot": k, "text": text[:60], "info": rules.SLOT_INFO[k], "options": opts, "select": "multi_ordered",
                              "allow_custom": True})

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = _space_of(d, state["space_id"])
        keep = [q for q in s.get("questions") or [] if q["slot"] not in {x["slot"] for x in questions}]
        s["questions"] = sorted(keep + questions, key=lambda q: rules.SLOT_KEYS.index(q["slot"]))
        s["questions_job"] = None
        return d

    await service.mutate(state["sb_id"], fn, content=False)
    await prog(100, f"질문 {len(questions)}개")
    return {}


def build_space_questions() -> StateGraph:
    return _chain(SpaceState, [("scene_context", s_scene_context), ("make_slot_questions", s_make_questions)])


async def c_compose_slots(state: SpaceState) -> SpaceState:
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    sp = _space_of(doc, state["space_id"])
    answers = {k: ((sp.get("slots") or {}).get(k) or {}).get("answer") for k in rules.SLOT_KEYS}
    answered = [k for k, a in answers.items() if a and ((sp["slots"].get(k) or {}).get("state") == "filled")]
    reco = await kbq.recommend(f"{sp['name']} {sp.get('purpose') or ''}", limit=4)
    await pace(3)
    out = await llm.call(f"sb.slot_compose.{sp.get('key') or 'space'}", llm.p_slot_compose(
        _space_brief(sp), {k: (answers[k] or {}).get("labels") for k in answered}, {"product_candidates": reco}), llm.SbSlotCompose)
    allowed = allowed_numbers(snap, doc, [l for k in answered for l in (answers[k] or {}).get("labels") or []])
    by_slot = {s.get("slot"): s.get("segments") or [] for s in out.get("slots") or []}
    composed: dict[str, list[dict[str, Any]]] = {}
    for k in answered:
        segs = []
        for seg in by_slot.get(k) or []:
            text, _ = guards.number_guard(seg.get("text") or "", allowed)
            if text:
                segs.append({"text": text, "ai_added": bool(seg.get("ai_added"))})
        if segs:
            composed[k] = segs
    await prog(50, f"{sp['name']} 시나리오 다듬는 중")
    return {"composed": {"slots": composed, "customer_questions": out.get("customer_questions") or [],
                         "products": out.get("products") or []}}


async def c_customer_questions(state: SpaceState) -> SpaceState:
    doc = await repo.require_sb(state["sb_id"])
    sp = _space_of(doc, state["space_id"])
    ref = doc.get("requirement_ref") or {}
    added = []
    for q in (state.get("composed") or {}).get("customer_questions") or []:
        text = (q.get("text") or "").strip()
        if not text or not ref.get("requirement_id"):
            continue
        res = await rq.add_customer_question(ref["requirement_id"], sb_id=state["sb_id"], text=text,
                                             short_label=(q.get("short_label") or text)[:24], place_label=rules.space_label(sp))
        added.append({"id": res.get("id"), "short_label": res.get("short_label") or q.get("short_label") or text[:24]})
    await prog(75, f"고객 질문 {len(added)}개")
    return {"added": added}


async def c_update(state: SpaceState) -> SpaceState:
    doc0 = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc0)
    evidence = _evidence_names(snap)
    composed = state.get("composed") or {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        sp = _space_of(d, state["space_id"])
        before = sp.pop("qa_base", None) or service.deep(sp)
        for k, segs in (composed.get("slots") or {}).items():
            cur = sp["slots"].get(k) or {}
            sp["slots"][k] = {**cur, "state": "filled", "segments": segs, "source": "compose"}
        if composed.get("products"):
            names = {p["name"] for p in sp.get("products") or []}
            merged = list(sp.get("products") or []) + [p for p in products_of(composed["products"], evidence) if p["name"] not in names]
            sp["products"] = merged[:6]
        for a in state.get("added") or []:
            if a.get("id") and a["id"] not in sp.setdefault("customer_question_ids", []):
                sp["customer_question_ids"].append(a["id"])
            if not any(x["id"] == a["id"] for x in sp.setdefault("added_questions", [])):
                sp["added_questions"].append(a)
        sp["status"] = "supplemented"
        sp["composing"] = False
        sp["compose_job"] = None
        tags = ["author_supplemented"] + (["extension"] if sp.get("is_extension") else [])
        changes.record(d, place_label=rules.space_label(sp, " · "), kind="changed", tags=tags,
                       cause={"kind": "space_questions", "ref": sp["id"], "label": "섹션 질의"},
                       before_summary=changes.summarize_space(before), after_summary=changes.summarize_space(sp),
                       target=("space", sp["id"]), before=before, after=service.deep(sp))
        if d.get("trace"):
            d["trace"]["stale"] = True
        return d

    doc = await service.mutate(state["sb_id"], fn)
    if doc.get("trace"):
        await service.enqueue(state["sb_id"], "sb.trace.refresh", {}, active=False, doc=doc)
    await prog(100, "시나리오를 채웠어요")
    return {}


def build_space_compose() -> StateGraph:
    return _chain(SpaceState, [("compose_slots", c_compose_slots), ("customer_questions", c_customer_questions),
                               ("update", c_update)])


# ── sb_revise(§7.6) ────────────────────────────────────────

class RevState(TypedDict, total=False):
    sb_id: str
    revision_id: str


def diff_lines(orig: list[dict[str, Any]], new: list[dict[str, Any]], kept: dict[str, str],
               allowed: set[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool]:
    """결정적 줄 정렬 — 같은 id → 바뀜/유지, 새 id → 새 줄, 없어진 id → 삭제. 가드 4 위반이면 원래 줄을 지키고 violated=True."""
    by_id = {ln["id"]: ln for ln in orig}
    nums = [int(m.group(1)) for ln in orig for m in [re.match(r"l(\d+)$", ln["id"])] if m]
    nxt = (max(nums) if nums else 0) + 1
    rows: list[dict[str, Any]] = []
    final: list[dict[str, Any]] = []
    seen: set[str] = set()
    violated = False
    for nl in new:
        text = (nl.get("text") or "").strip()
        oid = nl.get("id") if nl.get("id") in by_id and nl.get("id") not in seen else None
        if oid:
            seen.add(oid)
            ol = by_id[oid]
            if _norm(text) == _norm(ol["text"]) or not text:
                final.append(ol)
                if oid in kept:
                    rows.append({"kind": "kept", "before": ol["text"], "after": kept[oid], "reason": kept[oid], "line_id": oid})
                continue
            text, _ = guards.number_guard(text, allowed)
            if guards.loses_tokens(ol["text"], text) or ol.get("reviewing"):
                violated = True
                reason = kept.get(oid) or "그대로 — 추정값을 넣지 않아요"
                final.append(ol)
                rows.append({"kind": "kept", "before": ol["text"], "after": reason, "reason": reason, "line_id": oid})
                continue
            final.append({**ol, "text": text, "tokens": rules.tokens_of(text), "claim": bool(guards.find_claims(text))})
            rows.append({"kind": "changed", "before": ol["text"], "after": text, "line_id": oid})
        elif text:
            text, _ = guards.number_guard(text, allowed)
            lid = f"l{nxt}"
            nxt += 1
            final.append({"id": lid, "text": text, "tokens": rules.tokens_of(text), "reviewing": False,
                          "claim": bool(guards.find_claims(text))})
            rows.append({"kind": "added", "before": None, "after": text, "line_id": lid})
    for idx, ol in enumerate(orig):
        if ol["id"] in seen:
            continue
        if rules.tokens_of(ol["text"]) or ol.get("reviewing"):
            violated = True
            reason = kept.get(ol["id"]) or "그대로 — 추정값을 넣지 않아요"
            final.insert(min(idx, len(final)), ol)
            rows.append({"kind": "kept", "before": ol["text"], "after": reason, "reason": reason, "line_id": ol["id"]})
        elif ol["id"] in kept:
            final.insert(min(idx, len(final)), ol)
            rows.append({"kind": "kept", "before": ol["text"], "after": kept[ol["id"]], "reason": kept[ol["id"]], "line_id": ol["id"]})
        else:
            rows.append({"kind": "removed", "before": ol["text"], "after": None, "line_id": ol["id"]})
    return rows, final, violated


async def r_rewrite(state: RevState) -> RevState:
    rev = await repo.get_revision(state["revision_id"])
    if rev is None:
        raise ApiError(404, "NOT_FOUND", "수정 요청을 찾을 수 없어요")
    doc = await repo.require_sb(state["sb_id"])
    snap = await snapshot_of(doc)
    from .ops_outline import target_sections
    secs, spaces = target_sections(doc, rev["target"], rev["scope"])
    allowed = allowed_numbers(snap, doc)
    await pace(3)
    rows_all: list[dict[str, Any]] = []
    proposed: list[dict[str, Any]] = []
    await prog(20, "다시 쓰는 중")
    for sec in secs:
        if sec["group_key"] == "part2" and spaces:
            continue
        orig = sec.get("lines") or []
        allowed_s = allowed | guards.numbers_in([ln["text"] for ln in orig])
        tgt = {"key": sec["key"], "label": rules.section_label(sec), "direction": sec.get("direction"),
               "lines": [{"id": ln["id"], "text": ln["text"], "reviewing": ln.get("reviewing", False)} for ln in orig]}
        rows: list[dict[str, Any]] = []
        final: list[dict[str, Any]] = orig
        for attempt in range(2):     # 가드 4 위반이면 한 번 더
            out = await llm.call(f"sb.revise.{sec['key']}", llm.p_revise(tgt, rev["instruction"], rev["chips"],
                                                                        {"summary": doc["settings"].get("summary")}), llm.SbRevision)
            kept = {k.get("id"): k.get("reason") for k in out.get("kept") or [] if k.get("id")}
            rows, final, violated = diff_lines(orig, out.get("lines") or [], kept, allowed_s)
            if not violated:
                break
        label = rules.section_label(sec) if len(secs) > 1 else None
        rows_all += [{**r, "section_label": label} for r in rows]
        proposed.append({"kind": "section", "id": sec["id"], "lines": final})
    for sp in spaces:
        orig = [{"id": k, "text": rules.slot_text((sp.get("slots") or {}).get(k)), "reviewing": False}
                for k in rules.SLOT_KEYS if ((sp.get("slots") or {}).get(k) or {}).get("state") != "empty"]
        allowed_s = allowed | guards.numbers_in([ln["text"] for ln in orig])
        tgt = {"key": f"space:{sp['key']}", "label": rules.space_label(sp), "lines": orig}
        out = await llm.call(f"sb.revise.space.{sp.get('key') or 'space'}", llm.p_revise(tgt, rev["instruction"], rev["chips"],
                                                                                          {"summary": doc["settings"].get("summary")}),
                             llm.SbRevision)
        kept = {k.get("id"): k.get("reason") for k in out.get("kept") or [] if k.get("id")}
        new = [ln for ln in out.get("lines") or [] if ln.get("id") in rules.SLOT_KEYS]
        rows, final, _ = diff_lines(orig, new, kept, allowed_s)
        label = rules.space_label(sp) if len(spaces) > 1 else None
        rows_all += [{**r, "section_label": label, "kind": r["kind"] if r["kind"] != "added" else "changed"} for r in rows]
        proposed.append({"kind": "space", "id": sp["id"],
                         "slots": {ln["id"]: [{"text": ln["text"], "ai_added": False}] for ln in final if ln["id"] in rules.SLOT_KEYS}})
    rev.update(rows=rows_all, proposed=proposed, status="ready",
               changed_count=sum(1 for r in rows_all if r["kind"] != "kept"))
    await repo.put_revision(rev["id"], rev)
    await prog(100, f"{rev['changed_count']}줄이 바뀌어요")
    return {}


def build_revise() -> StateGraph:
    return _chain(RevState, [("rewrite", r_rewrite)])


# ── sb_rq_sync(§7.7) ───────────────────────────────────────

class SyncState(TypedDict, total=False):
    sb_id: str
    requirement_id: str
    to_version: int | None
    reply_id: str | None
    dry_run: bool
    preview_id: str | None
    changes: list[dict[str, Any]]
    note: str | None
    places: list[str]
    update: list[dict[str, Any]]


async def y_load_versions(state: SyncState) -> SyncState:
    await pace(3)
    doc = await repo.require_sb(state["sb_id"])
    ref = doc["requirement_ref"]
    rq_id = ref["requirement_id"]
    note = None
    if state.get("reply_id"):
        reply = await rq.get_reply(rq_id, state["reply_id"])
        chs = [{"target": c.get("target") or {}, "kind": "changed", "label": c.get("label"), "before": c.get("before_display"),
                "after": c.get("after_display")} for c in reply.get("changes") or [] if c.get("selected", True)]
        note = reply.get("version_note")
    else:
        to_v = int(state.get("to_version") or ref.get("latest_version") or ref["version"])
        if to_v <= int(ref["version"]):
            chs = []
        else:
            diff = await rq.get_diff(rq_id, int(ref["version"]), to_v)
            chs = list(diff.get("changes") or [])
            try:
                note = (await rq.get_snapshot(rq_id, to_v)).note
            except ApiError:
                note = None
    await prog(25, f"정의서 변경 {len(chs)}곳")
    return {"changes": chs, "note": note}


async def y_affected(state: SyncState) -> SyncState:
    doc = await repo.require_sb(state["sb_id"])
    outline = doc.get("outline") or {}
    if not outline.get("ready"):
        return {"places": []}
    by_item = {i["rq_item_id"]: i for i in (doc.get("trace") or {}).get("items") or []}
    secs = {s["id"]: s for s in outline.get("sections") or []}
    spaces = {s["id"]: s for s in outline.get("spaces") or []}
    keys: list[str] = []

    def add(k: str) -> None:
        if k and k not in keys:
            keys.append(k)

    for ch in state.get("changes") or []:
        tgt = ch.get("target") or {}
        kind = tgt.get("kind")
        if kind == "item":
            for p in (by_item.get(tgt.get("id")) or {}).get("places") or []:
                if p["kind"] == "section" and p.get("id") in secs:
                    add(secs[p["id"]]["key"])
                elif p["kind"] == "space" and p.get("id") in spaces:
                    add(f"space:{spaces[p['id']]['key']}")
        elif kind in ("field", "keyman", "weights"):
            add("overview")
            if tgt.get("id") in ("final_audience", "customer_name"):
                add("outro")
        elif kind in ("evidence",):
            add("p1_2")
    await prog(40, f"영향 자리 {len(keys)}곳")
    return {"places": keys}


async def y_update_places(state: SyncState) -> SyncState:
    places = state.get("places") or []
    chs = state.get("changes") or []
    if not chs:
        return {"update": []}
    doc = await repo.require_sb(state["sb_id"])
    if not (doc.get("outline") or {}).get("ready"):
        return {"update": []}
    snap = await snapshot_of(doc)
    catalog = [p for p in brief.place_catalog(doc) if p["place"] in places]
    out = await llm.call("sb.sync_update", llm.p_sync(chs, catalog), llm.SbSyncUpdate)
    allow_new_space = any((c.get("kind") in ("added",) or (c.get("target") or {}).get("kind") == "new_item") for c in chs)
    allowed = allowed_numbers(snap, doc, chs)
    updates = []
    for p in out.get("places") or []:
        pid = (p.get("place_id") or "").strip()
        hit = brief.resolve_place(doc, pid)
        if hit is None:
            if p.get("kind") == "added" and pid.startswith("space:") and (allow_new_space or not places):
                updates.append({**p, "new_space": True})
            continue
        if pid not in places and not (hit[0] == "section" and hit[1]["key"] in places) and \
                not (hit[0] == "space" and f"space:{hit[1]['key']}" in places):
            continue     # 영향 밖 자리는 건드리지 않는다
        if p.get("lines"):
            p["lines"] = [guards.number_guard(x, allowed)[0] for x in p["lines"] if x and x.strip()]
        updates.append({**p, "kind_obj": hit[0], "obj_id": hit[1]["id"]})
    await prog(70, f"{len(updates)}곳 다시 씀")
    return {"update": updates}


def _apply_sync_update(d: dict[str, Any], u: dict[str, Any], cause: dict[str, Any], record: bool) -> dict[str, Any] | None:
    """한 자리 갱신 → ChangeEntry(기록하면 작업본에도 남긴다). 미리 보기는 행만 만든다."""
    outline = d["outline"]
    kind = u.get("kind") or "changed"
    if u.get("new_space"):
        key = u["place_id"].split(":", 1)[1]
        name = (u.get("aspect") or key).strip()
        sp = {"id": new_id("spc"), "key": key, "order": len(outline["spaces"]) + 1, "name": name, "purpose": "",
              "is_extension": True, "status": "draft",
              "slots": {k: {"state": "empty", "segments": [], "source": None, "answer": None, "customer_question_id": None}
                        for k in rules.SLOT_KEYS},
              "filled_count": 0, "products": [], "questions": [], "customer_question_ids": [], "added_questions": [], "composing": False}
        for st in u.get("slots") or []:
            if st.get("slot") in sp["slots"] and st.get("text"):
                sp["slots"][st["slot"]] = {"state": "filled", "segments": [{"text": st["text"], "ai_added": False}], "source": "rq_sync",
                                           "answer": None, "customer_question_id": None}
        entry = {"place_label": f"Part 2 · {name}", "aspect": None, "kind": "added", "tags": ["extension"],
                 "before_summary": u.get("summary_before") or f"없음 · 공간 {len(outline['spaces'])}개",
                 "after_summary": u.get("summary_after") or changes.summarize_space(sp), "cause": cause}
        if record:
            outline["spaces"].append(sp)
            return changes.record(d, target=("space", sp["id"]), before=None, after=service.deep(sp), **entry)
        return {"id": new_id("chg"), **entry, "revertible": False}
    if u.get("kind_obj") == "section":
        sec = next(s for s in outline["sections"] if s["id"] == u["obj_id"])
        before = service.deep(sec)
        place_label = rules.section_label(sec) if sec["group_key"] != "part1" else f"Part {sec.get('code')}"
        if kind != "kept" and u.get("lines"):
            orig = sec.get("lines") or []
            new_lines = []
            for i, t in enumerate(u["lines"]):
                ol = orig[i] if i < len(orig) else None
                if ol and (guards.loses_tokens(ol["text"], t) or ol.get("reviewing")):
                    new_lines.append(ol)           # 가드 4 — 확인 전 표시 · 검토 중 줄은 지킨다
                else:
                    new_lines.append({"id": ol["id"] if ol else f"l{len(orig) + i + 1}", "text": t, "tokens": rules.tokens_of(t),
                                      "reviewing": False, "claim": bool(guards.find_claims(t))})
            for ol in orig[len(u["lines"]):]:
                if rules.tokens_of(ol["text"]) or ol.get("reviewing"):
                    new_lines.append(ol)
            if record:
                sec["lines"] = new_lines
        entry = {"place_label": place_label, "aspect": u.get("aspect"), "kind": kind, "tags": [],
                 "before_summary": u.get("summary_before") or changes.summarize_section(before),
                 "after_summary": u.get("summary_after") or changes.summarize_section(sec), "cause": cause}
        if record:
            if kind == "kept":
                return changes.record(d, revertible=False, **entry)
            return changes.record(d, target=("section", sec["id"]), before=before, after=service.deep(sec), **entry)
        return {"id": new_id("chg"), **entry, "revertible": False}
    sp = next(s for s in outline["spaces"] if s["id"] == u["obj_id"])
    before = service.deep(sp)
    if kind != "kept" and record:
        for st in u.get("slots") or []:
            if st.get("slot") not in rules.SLOT_KEYS or not st.get("text"):
                continue
            cur = sp["slots"].get(st["slot"]) or {}
            if guards.loses_tokens(rules.slot_text(cur), st["text"]):
                continue
            sp["slots"][st["slot"]] = {**cur, "state": "filled", "segments": [{"text": st["text"], "ai_added": False}],
                                       "source": "rq_sync"}
    entry = {"place_label": rules.space_label(sp, " · "), "aspect": u.get("aspect"), "kind": kind,
             "tags": ["extension"] if sp.get("is_extension") else [],
             "before_summary": u.get("summary_before") or changes.summarize_space(before),
             "after_summary": u.get("summary_after") or changes.summarize_space(sp), "cause": cause}
    if record:
        if kind == "kept":
            return changes.record(d, revertible=False, **entry)
        return changes.record(d, target=("space", sp["id"]), before=before, after=service.deep(sp), **entry)
    return {"id": new_id("chg"), **entry, "revertible": False}


async def y_record(state: SyncState) -> SyncState:
    sb_id = state["sb_id"]
    doc = await repo.require_sb(sb_id)
    ref = doc["requirement_ref"]
    to_v = state.get("to_version")
    label_v = int(to_v) if to_v else int(ref["version"]) + 1
    label = f"요구사항 정의서 v{label_v}" + (f" · {state['note']}" if state.get("note") else "")
    cause = {"kind": "rq_sync", "ref": f"{ref['requirement_id']}@{label_v}", "label": label}
    updates = state.get("update") or []
    if state.get("dry_run"):
        tmp = service.deep(doc)
        rows = [r for r in (_apply_sync_update(tmp, u, cause, record=False) for u in updates) if r]
        p = await repo.get_preview(state["preview_id"] or "")
        if p is not None:
            p.update(rows=rows, count=changes.changed_count(rows), causes=changes.cause_labels(rows) or [label], status="ready",
                     to_rq_version=label_v)
            await repo.put_preview(p["id"], p)
        await prog(100, "미리 보기를 만들었어요")
        return {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if d.get("outline"):
            for u in updates:
                try:
                    _apply_sync_update(d, u, cause, record=True)
                except StopIteration:
                    continue
            if d.get("trace"):
                d["trace"]["stale"] = True
        r = d["requirement_ref"]
        if to_v:
            r["version"] = int(to_v)
            r["latest_version"] = max(int(r.get("latest_version") or 0), int(to_v))
            r["version_note"] = state.get("note")
        d["rq_update"] = None
        return d

    doc = await service.mutate(sb_id, fn)
    await prog(90, "반영했어요")
    return {}


async def y_relink(state: SyncState) -> SyncState:
    if state.get("dry_run"):
        return {}
    doc = await repo.require_sb(state["sb_id"])
    ref = doc["requirement_ref"]
    if state.get("to_version"):
        try:   # 새 정의서 버전으로 항목 수 · 이름 갱신
            snap = await rq.get_snapshot(ref["requirement_id"], int(ref["version"]))

            def fn(d: dict[str, Any]) -> dict[str, Any]:
                d["requirement_ref"]["item_count"] = len(snap.items)
                return d

            doc = await service.mutate(state["sb_id"], fn, content=False)
        except ApiError:
            pass
    await rq.put_link(ref["requirement_id"], doc["id"], title=doc.get("title") or "", route=doc.get("route") or "",
                      rq_version=int(ref["version"]), depends_on=tracebuild.depends_on(doc))
    if doc.get("trace"):
        await service.enqueue(state["sb_id"], "sb.trace.refresh", {}, active=False, doc=doc)
    await prog(100, "정의서 새 버전을 반영했어요")
    return {}


def build_rq_sync() -> StateGraph:
    return _chain(SyncState, [("load_versions", y_load_versions), ("affected_places", y_affected),
                              ("update_places", y_update_places), ("record", y_record), ("relink", y_relink)])


# ── sb_trace_apply / sb_trace_refresh(§7.8) ──────────────────

class TraceState(TypedDict, total=False):
    sb_id: str
    rq_item_id: str
    option_id: str


def _significant(text: str) -> set[str]:
    return {t.casefold() for t in re.split(r"[\s·/,()'’]+", text or "") if len(t) >= 2}


async def t_place_item(state: TraceState) -> TraceState:
    sb_id = state["sb_id"]
    doc = await repo.require_sb(sb_id)
    snap = await snapshot_of(doc)
    item = next((i for i in (doc.get("trace") or {}).get("items") or [] if i["rq_item_id"] == state["rq_item_id"]), None)
    if item is None:
        raise ApiError(404, "NOT_FOUND", "추적 항목을 찾을 수 없어요")
    opt = next((o for o in ((item.get("question") or {}).get("options") or []) if o["id"] == state["option_id"]), None)
    if opt is None or not opt.get("target"):
        raise ApiError(422, "VALIDATION_FAILED", "놓을 곳이 없어요")
    tgt = opt["target"]
    if tgt["kind"] == "section":
        obj = next(s for s in doc["outline"]["sections"] if s["id"] == tgt["id"])
        tbrief = {"place": obj["key"], "label": rules.section_label(obj), "lines": [ln["text"] for ln in obj.get("lines") or []]}
    else:
        obj = next(s for s in doc["outline"]["spaces"] if s["id"] == tgt["id"])
        tbrief = {"place": f"space:{obj['key']}", "label": rules.space_label(obj), **_space_brief(obj)}
    out = await llm.call("sb.place_item", llm.p_place_item({"code": item["code"], "text": item["text"], "short": item["short"]}, tbrief),
                         llm.SbPlaceItem)
    allowed = allowed_numbers(snap, doc)
    result_label = (out.get("result_label") or "").strip()
    anchor = (obj["name"] if tgt["kind"] == "space" else " ".join(tgt["label"].split(" ")[:2]))
    if result_label and anchor not in result_label:
        result_label = ""      # 다른 자리 이야기면 결정적 문구를 쓴다
    item_tokens = _significant(item.get("short") or item.get("text") or "")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        it = next(i for i in d["trace"]["items"] if i["rq_item_id"] == state["rq_item_id"])
        cause = {"kind": "trace", "ref": it["code"], "label": "요구 정리"}
        if tgt["kind"] == "section":
            sec = next(s for s in d["outline"]["sections"] if s["id"] == tgt["id"])
            before = service.deep(sec)
            nums = [int(m.group(1)) for ln in sec.get("lines") or [] for m in [re.match(r"l(\d+)$", ln["id"])] if m]
            nxt = (max(nums) if nums else 0) + 1
            for t in (out.get("lines_add") or [])[:2]:
                if not t or not t.strip():
                    continue
                g = guard_line(t, allowed)
                sec.setdefault("lines", []).append({"id": f"l{nxt}", "text": g["text"], "tokens": g["tokens"], "reviewing": False,
                                                    "claim": g["claim"]})
                nxt += 1
            changes.record(d, place_label=rules.section_label(sec), kind="changed", cause=cause,
                           before_summary=changes.summarize_section(before), after_summary=(out.get("lines_add") or [""])[0],
                           target=("section", sec["id"]), before=before, after=service.deep(sec))
        else:
            sp = next(s for s in d["outline"]["spaces"] if s["id"] == tgt["id"])
            before = service.deep(sp)
            for st in out.get("slot_segments") or []:
                k = st.get("slot")
                if k not in rules.SLOT_KEYS or not (st.get("text") or "").strip():
                    continue
                text = guards.number_guard(st["text"].strip(), allowed)[0]
                cur = sp["slots"].get(k) or {}
                if cur.get("state") == "filled":
                    segs = list(cur.get("segments") or []) + [{"text": " / ", "ai_added": False}, {"text": text, "ai_added": True}]
                else:
                    segs = [{"text": text, "ai_added": True}]
                sp["slots"][k] = {**cur, "state": "filled", "segments": segs, "source": "trace"}
            changes.record(d, place_label=rules.space_label(sp, " · "), kind="changed", cause=cause,
                           before_summary=changes.summarize_space(before), after_summary=changes.summarize_space(sp),
                           target=("space", sp["id"]), before=before, after=service.deep(sp))
        if not any(p.get("id") == tgt["id"] for p in it["places"]):
            it["places"].append({"kind": tgt["kind"], "id": tgt["id"], "label": tgt["label"]})
        if "direct" not in it["link_types"]:
            it["link_types"].insert(0, "direct")
        if it.get("resolution") and result_label:
            it["resolution"]["result_label"] = result_label
        secs = {s["id"]: s for s in d["outline"]["sections"]}
        spaces = {s["id"]: s for s in d["outline"]["spaces"]}
        it["places_label"] = rules.places_label(it["places"], secs, spaces) or it.get("places_label")
        for disc in d["outline"].get("discussions") or []:
            if disc.get("state") == "open" and (it["rq_item_id"] in disc.get("trace_item_ids") or []
                                                or item_tokens & _significant(disc.get("label", ""))):
                disc["state"] = "resolved"
        return d

    await service.mutate(sb_id, fn)
    await prog(100, "요구를 넣었어요")
    return {}


def build_trace_apply() -> StateGraph:
    return _chain(TraceState, [("place_item", t_place_item)])


async def t_refresh(state: TraceState) -> TraceState:
    sb_id = state["sb_id"]
    doc = await repo.require_sb(sb_id)
    if not (doc.get("outline") or {}).get("ready"):
        return {}
    snap = await snapshot_of(doc)
    trace, out = await _compute_trace(doc, snap, doc.get("trace"))

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["trace"] = trace
        prev = d["outline"].get("discussions") or []
        merged = tracebuild.merge_discussions(d, {}, out.get("discussions") or [], prev)
        known = {x["label"] for x in merged}
        d["outline"]["discussions"] = (merged + [x for x in prev if x["label"] not in known])[:7]
        return d

    doc = await service.mutate(sb_id, fn)
    ref = doc["requirement_ref"]
    await rq.put_link(ref["requirement_id"], sb_id, title=doc.get("title") or "", route=doc.get("route") or "",
                      rq_version=int(ref["version"]), depends_on=tracebuild.depends_on(doc))
    await prog(100, "요구 추적을 다시 계산했어요")
    return {}


def build_trace_refresh() -> StateGraph:
    return _chain(TraceState, [("refresh", t_refresh)])


# ── 내보내기 ──────────────────────────────────────────────

class ExportState(TypedDict, total=False):
    sb_id: str
    format: str
    options: dict[str, Any]
    version: int
    result: dict[str, Any]


async def e_export(state: ExportState) -> ExportState:
    import asyncio

    from winmate_common.client import ServiceClient

    from . import exporting
    sb_id = state["sb_id"]
    doc = await repo.require_sb(sb_id)
    version = int(state.get("version") or doc.get("saved_version") or 0)
    opts = state.get("options") or {}
    author_note = None
    if opts.get("internal_memo"):
        try:
            author_note = (await snapshot_of(doc)).author_note or None
        except ApiError:
            author_note = None
    fmt = state.get("format") or "pptx"
    document = exporting.build(doc, fmt=fmt, options=opts, version=version, author_note=author_note)
    name = exporting.file_name(doc, version, bool(opts.get("internal_memo")))
    await prog(30, "파일을 만드는 중")
    lang = ((doc.get("settings") or {}).get("language") or {}).get("value", "ko")
    body = {"format": fmt, "filename": name, "document": document, "confidential": True, "project_id": doc.get("project_id"),
            "source_ref": f"storyboard:{sb_id}:v{version}", "language": lang if lang != "ko_en" else "ko_en", "async": False}
    if lang == "ko_en":
        body["bilingual"] = "inline"
    ex = ServiceClient("export", timeout=180)
    try:
        res = await ex.post("/v1/exports", json=body)
    except ApiError as exc:
        raise ApiError(502, "UPSTREAM_FAILED", f"파일을 만들지 못했어요: {exc.message}", {"upstream": exc.code}) from exc
    if res.get("status") != "done":
        export_id = res.get("export_id")
        for _ in range(120):
            await asyncio.sleep(1.5)
            res = await ex.get(f"/v1/exports/{export_id}")
            if res.get("status") in ("done", "failed"):
                break
        if res.get("status") != "done":
            raise ApiError(502, "UPSTREAM_FAILED", "파일을 만들지 못했어요", {"export": res.get("error")})
    file = res.get("file") or {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["exported"] = True
        d["status"] = "shared"
        d.setdefault("exports", []).append({"file_id": file.get("id"), "name": file.get("name"), "format": fmt, "version": version,
                                            "internal": bool(opts.get("internal_memo")), "at": now_iso()})
        return d

    await service.mutate(sb_id, fn, content=False)
    await prog(100, "내보냈어요")
    return {"result": {"file_id": file.get("id"), "name": file.get("name"), "url": file.get("url"), "format": fmt, "version": version}}


def build_export() -> StateGraph:
    return _chain(ExportState, [("export", e_export)])
