"""LangGraph 워크플로(§7) — 워커가 `run_graph`(thread_id = job_id, SQLite 체크포인터)로 돌린다.

sc.parse_input · sc.skeleton(template | birdseye) · sc.timeline_edit · sc.lane_rewrite · sc.recommend · sc.generate ·
sc.rewrite_scene · sc.edit · sc.shorten · sc.images_batch · sc.export
노드는 문서(DB) 상태로 멱등하게 만든다 — 실패한 생성을 같은 thread 로 다시 돌리면 끝난 장면은 건너뛴다(§4.9 다시 시도).
"""
from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.jobs import current_job, jobs

from . import birdseye as be
from . import (
    compose,
    imaging,
    kbq,
    llm,
    policy,
    prompts,
    repo,
    seed,
    service,
    sheets,
    texts,
)
from . import timeline as tl

log = logging.getLogger("winmate.scenario.graphs")


class State(TypedDict, total=False):
    scenario_id: str
    payload: dict[str, Any]
    lines: list[dict[str, Any]]
    data: dict[str, Any] | None
    remaining: int
    result: dict[str, Any]


async def _emit(type_: str, data: dict[str, Any]) -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.jobs.emit(ctx.job.id, type_, data)


async def _progress(value: float, message: str, **data: Any) -> None:
    """진행률(이벤트 data.progress) + eta_s(남은 초)."""
    ctx = current_job()
    data.pop("pct", None)
    if ctx is not None:
        await ctx.progress(value, message, **data)


async def _stage(stage: str, name: str, note: str, state_: str, **extra: Any) -> None:
    await _emit("step", {"step": stage, "stage": stage, "name": name, "note": note, "status": state_, **extra})


def _job_id() -> str:
    ctx = current_job()
    return ctx.job.id if ctx else ""


# ═════════════ sc.parse_input (§7.3) ═════════════

async def p_regex_split(state: State) -> State:
    raw = state["payload"]["raw_text"]
    clean, n = policy.scrub_people(raw)
    return {"lines": compose.split_lines(clean), "data": {"clean_text": clean, "real_names": n > 0}}


async def p_llm(state: State) -> State:
    doc = await repo.require_sc(state["scenario_id"])
    clean = state["data"]["clean_text"]
    chars = [policy.scrub_people(c)[0] for c in state["payload"].get("characters") or []]
    vertical = doc.get("vertical_code") or await compose.guess_vertical(clean)
    ind = seed.industry(vertical)
    res = await llm.try_json("sc.parse_input", prompts.parse_input(clean, chars, state["lines"], ind["name"] if ind else "미정"),
                             prompts.ParseOut, customer=doc.get("customer_name"), timeout=90)
    data = dict(state["data"])
    data["llm"] = res.data if res is not None else None
    data["anonymized"] = bool(res and res.anonymized)
    data["vertical"] = vertical
    data["characters"] = chars
    return {"data": data}


async def p_build(state: State) -> State:
    data = dict(state["data"])
    parsed = data.get("llm")
    if not compose.usable_parse(parsed):
        parsed = compose.fallback_parse(state["lines"], data.get("characters") or [])
        data["fallback"] = True
    data["parsed"] = parsed
    return {"data": data}


async def p_save(state: State) -> State:
    data = state["data"]
    parsed = data["parsed"]
    raw = state["payload"]["raw_text"]

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["raw_text"] = raw
        d["characters"] = data.get("characters") or d.get("characters") or []
        if data.get("vertical") and not d.get("vertical_code"):
            d["vertical_code"] = data["vertical"]
        compose.build_from_parse(d, parsed)
        if not d["suggestions"].get("roles"):
            d["suggestions"]["roles"] = compose.fallback_suggested_roles(d)
        llm_out = data.get("llm") or {}
        if llm_out.get("customer_name") and llm_out["customer_name"] in raw and not d.get("customer_name"):
            d["customer_name"] = llm_out["customer_name"]
        if (d.get("title") or "새 시나리오") == "새 시나리오":
            title = (llm_out.get("title") or "").strip()
            d["title"] = title or (f"{d.get('space_label') or '공간'} 시나리오")
        if llm_out.get("space_label") and not d.get("space_label"):
            d["space_label"] = llm_out["space_label"]
        n = len(d["scenes"])
        c = tl.conflicts(d)
        reason = None
        if n > service.MAX_SCENES_AUTO:
            reason = "too_many"
        elif c["same_time"]:
            reason = "conflict"
        elif c["unassigned"]:
            reason = "unassigned"
        nxt = "SC2E" if reason else "SC3"
        d["parse"] = {"next": nxt, "reason": reason, "scene_count": n}
        d["notices"] = {"real_names": bool(data.get("real_names")), "too_many": n if reason == "too_many" else None}
        d["step"] = 3 if nxt == "SC3" else 2
        d["via_timeline"] = nxt == "SC2E"
        d["edit"] = {"undo": [], "redo": [], "changes": 0}
        d["recommendation"] = None
        d["status"] = "draft"
        d["dirty"] = True
        if data.get("anonymized"):
            d["anonymized"] = True
        service.set_active(d, None)
        return d
    doc = await repo.update(state["scenario_id"], fn)
    await service.register(doc)
    return {"result": {"next": doc["parse"]["next"], "reason": doc["parse"]["reason"], "scene_count": doc["parse"]["scene_count"]}}


def build_parse() -> StateGraph:
    g = StateGraph(State)
    g.add_node("regex_split", p_regex_split)
    g.add_node("llm_json", p_llm)
    g.add_node("validate", p_build)
    g.add_node("save", p_save)
    g.add_edge(START, "regex_split")
    g.add_edge("regex_split", "llm_json")
    g.add_edge("llm_json", "validate")
    g.add_edge("validate", "save")
    g.add_edge("save", END)
    return g


# ═════════════ sc.skeleton (§7.4) ═════════════

async def _resolve_used(used: list[str], with_solutions: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """업종 「자주 쓰인 것」 → KB A1 → (솔루션 칩, 제품 추천 칩)."""
    sols: list[dict[str, Any]] = []
    recs: list[dict[str, Any]] = []
    for term in used:
        links = await kbq.a1(term)
        sol_link = next((lk for lk in links if lk.get("type") == "solution"), None)
        if sol_link or seed.solution_by_name(term):
            s = seed.solution(sol_link.get("id")) if sol_link else seed.solution_by_name(term)
            s = s or seed.solution_by_name(term)
            if s and with_solutions and not any(x["solution_id"] == s["id"] for x in sols):
                sols.append({"solution_id": s["id"], "name": s["name"], "source": "template", "ord": len(sols)})
            continue
        cat = next((lk for lk in links if lk.get("type") in ("category", "family")), None)
        if cat and len(recs) < 3:
            recs.append({"ref": f"kb:category:{cat['id']}", "family_id": cat["id"] if cat.get("type") == "family" else None,
                         "model_code": None, "label": cat.get("name") or term, "short": term, "why": "업종 자주 쓰인 것"})
    return sols, recs


async def s_template(state: State) -> State:
    p = state["payload"]
    ind = seed.industry(p["industry"])
    if ind is None:
        raise ApiError(404, "NOT_FOUND", "업종 템플릿을 찾을 수 없어요")
    preset = ind["presets"][max(0, min(2, int(p.get("preset_index") or 1) - 1))]
    is_day = "하루" in preset["title"]
    res = await llm.try_json("sc.skeleton", prompts.skeleton_template(ind, preset, is_day), prompts.SkeletonOut, timeout=60,
                             confidential=False)
    out = res.data if res is not None else {}
    times = list(out.get("times") or [])
    slots = [{"time": (times[i] if is_day and i < len(times) else None), "label": step} for i, step in enumerate(preset["flow"])]
    roles = [{"name": r} for r in preset["roles"]]
    beats = [b for b in out.get("beats") or [] if isinstance(b.get("slot"), int) and 0 <= b["slot"] < len(slots)]
    if not beats:
        beats = []
        for i, step in enumerate(preset["flow"]):
            role = preset["roles"][i % len(preset["roles"])]
            place = ind["spaces"][i % len(ind["spaces"])]
            beats.append({"slot": i, "role": role, "text": f"{texts.with_josa(role, '이/가')} {place}에서 {step}", "place": place})
    sols, recs = await _resolve_used(ind["used"], p.get("type") == "with")
    data = {"slots": slots, "roles": roles, "beats": beats, "personas": out.get("personas") or [], "suggestion": None,
            "suggested_roles": out.get("suggested_roles") or []}
    ctx_ = await service.project_context(p.get("project_id"))

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        compose.build_from_parse(d, data, source="template")
        if not d["suggestions"].get("roles"):
            d["suggestions"]["roles"] = [r for r in compose.fallback_suggested_roles(d)]
        d["vertical_code"] = ind["code"]
        d["template"] = {"industry": ind["code"], "preset_index": int(p.get("preset_index") or 1), "preset_title": preset["title"]}
        d["needs"] = list(ind["needs"])
        d["spaces"] = list(ind["spaces"])
        d["space_label"] = d.get("space_label") or ind["spaces"][0]
        if ctx_.get("customer") and not d.get("customer_name"):
            d["customer_name"] = ctx_["customer"]
        d["title"] = f"{(d.get('customer_name') + ' ') if d.get('customer_name') else ''}{preset['title']} 시나리오"
        d["solution_picks"] = sols if d.get("type") == "with" else []
        d["related_products"] = recs
        d["related_for"] = None
        d["raw_text"] = tl.to_text(d)
        d["step"] = 2
        d["via_timeline"] = True
        d["parse"] = {"next": "SC2E", "reason": None, "scene_count": len(d["scenes"])}
        d["status"] = "draft"
        d["dirty"] = True
        service.set_active(d, None)
        return d
    doc = await repo.update(state["scenario_id"], fn)
    await service.register(doc)
    return {"result": {"next": "SC2E", "scene_count": len(doc["scenes"])}}


async def s_birdseye(state: State) -> State:
    p = state["payload"]
    be_id = p["birdseye_id"]
    h = await be.handoff(be_id)
    if not h:
        raise ApiError(503, "BIRDSEYE_UNAVAILABLE", "조감도를 읽지 못했어요. 잠시 후 다시 시도해 주세요.")
    zones = be.zones_of(h)
    by_id = {z["id"]: z for z in zones}
    order = [z for z in p.get("order") or [] if z in by_id and z in (p.get("zone_ids") or [])]
    for zid in p.get("zone_ids") or []:
        if zid in by_id and zid not in order:
            order.append(zid)
    chosen = [by_id[z] for z in order]
    if not chosen:
        raise ApiError(400, "NO_ZONES", "가져올 존을 하나 이상 고르세요")
    axis = p.get("axis") or "방문객 동선"
    visitor = axis == "방문객 동선"
    res = await llm.try_json("sc.skeleton", prompts.skeleton_birdseye(h.get("title") or "", axis, chosen, not visitor),
                             prompts.SkeletonOut, timeout=60, customer=h.get("customer"))
    out = res.data if res is not None else {}
    times = list(out.get("times") or [])
    slots = [{"time": (None if visitor else (times[i] if i < len(times) else None)), "label": z["short_name"]} for i, z in enumerate(chosen)]
    role_names = ["방문객", "매장 스태프"] if visitor else []
    for b in out.get("beats") or []:
        if b.get("role") and b["role"] not in role_names:
            role_names.append(b["role"])
    if not role_names:
        role_names = ["매장 스태프", "방문객"]
    beats = [b for b in out.get("beats") or [] if isinstance(b.get("slot"), int) and 0 <= b["slot"] < len(slots)]
    if not beats:
        for i, z in enumerate(chosen):
            prod = be.product_line(z["products"]) or "공간"
            beats.append({"slot": i, "role": role_names[0], "text": texts.clip(f"{z['short_name']}에서 {prod} 보기", tl.BEAT_MAX),
                          "place": z["name"]})
    for b in beats:
        b["place"] = chosen[b["slot"]]["name"]
    data = {"slots": slots, "roles": [{"name": r} for r in role_names], "beats": beats, "personas": out.get("personas") or [],
            "suggestion": None, "suggested_roles": out.get("suggested_roles") or []}
    version = h.get("version")
    zhash = be.zones_hash(zones)
    title = h.get("title") or "조감도"

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        compose.build_from_parse(d, data, source="birdseye")
        slot_ids = [s["id"] for s in tl.slots(d)]
        picks: list[dict[str, Any]] = []
        for sc in d["scenes"]:
            i = slot_ids.index(sc["slot_id"]) if sc["slot_id"] in slot_ids else -1
            if 0 <= i < len(chosen):
                z = chosen[i]
                sc["place"] = z["name"]
                sc["zone_ref"] = {"birdseye_id": be_id, "zone_id": z["id"], "n": z["n"], "name": z["name"], "u": z.get("u"), "v": z.get("v")}
                sc["products"] = [{"ref": (f"kb:family:{x['family_id']}" if x.get("family_id") else None), "family_id": x.get("family_id"),
                                   "model_code": x.get("model_code"), "short": x.get("short") or x.get("label"), "label": x.get("label"),
                                   "qty": x.get("qty"), "is_new": False} for x in z["products"]]
                for x in z["products"]:
                    key = x.get("family_id") or x.get("label")
                    if not any((pp.get("family_id") or pp.get("label")) == key for pp in picks):
                        picks.append({"ref": f"kb:family:{x['family_id']}" if x.get("family_id") else None, "family_id": x.get("family_id"),
                                      "model_code": x.get("model_code"), "label": x.get("label") or x.get("short"),
                                      "short": x.get("short") or x.get("label"), "qty": x.get("qty"), "source": "birdseye", "ord": len(picks)})
        d["product_picks"] = picks
        d["birdseye_link"] = {"birdseye_id": be_id, "title": title, "linked_version": version, "layout_version": h.get("layout_version"),
                              "zones_hash": zhash, "keep_link": bool(p.get("keep_link", True)), "changed": None, "axis": axis,
                              "zone_ids": order, "order": order, "zones": be.zone_snapshot(zones)}
        d["start_mode"] = "birdseye"
        if h.get("customer") and not d.get("customer_name"):
            d["customer_name"] = h["customer"] if isinstance(h["customer"], str) else (h["customer"] or {}).get("name")
        d["space_label"] = d.get("space_label") or (title.split(" ", 2)[-1] if " " in title else title)
        d["spaces"] = [z["name"] for z in chosen]
        d["title"] = f"{title} {axis} 시나리오"
        if not d["suggestions"].get("roles"):
            d["suggestions"]["roles"] = compose.fallback_suggested_roles(d)
        d["raw_text"] = tl.to_text(d)
        d["step"] = 2
        d["via_timeline"] = True
        d["parse"] = {"next": "SC2E", "reason": None, "scene_count": len(d["scenes"])}
        d["status"] = "draft"
        d["dirty"] = True
        service.set_active(d, None)
        return d
    doc = await repo.update(state["scenario_id"], fn)
    await be.register_usage(be_id, doc["id"], f"공간 시나리오 · {doc.get('title') or ''}", version)
    await service.register(doc)
    return {"result": {"next": "SC2E", "scene_count": len(doc["scenes"])}}


def build_skeleton_template() -> StateGraph:
    g = StateGraph(State)
    g.add_node("template_skeleton", s_template)
    g.add_edge(START, "template_skeleton")
    g.add_edge("template_skeleton", END)
    return g


def build_skeleton_birdseye() -> StateGraph:
    g = StateGraph(State)
    g.add_node("birdseye_skeleton", s_birdseye)
    g.add_edge(START, "birdseye_skeleton")
    g.add_edge("birdseye_skeleton", END)
    return g


# ═════════════ sc.timeline_edit · sc.lane_rewrite (SC2E) ═════════════

def _slot_for(doc: dict[str, Any], time_: str | None, label: str | None) -> dict[str, Any] | None:
    t = texts.norm_time(time_)
    for s in doc.get("slots") or []:
        if t and s.get("time") == t:
            return s
    for s in doc.get("slots") or []:
        if label and s.get("label") == label:
            return s
    return None


def translate_timeline_ops(doc: dict[str, Any], ops: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for op in ops:
        kind = op.get("op")
        role = tl.role_by_name(doc, op.get("role"))
        if kind == "add_slot":
            out.append({"op": "add_slot", "time": op.get("time"), "label": op.get("slot_label") or op.get("text") or "새 시간대"})
        elif kind == "add_role" and op.get("role"):
            if role is None:
                out.append({"op": "add_role", "name": op["role"]})
        elif kind == "add_beat":
            slot = _slot_for(doc, op.get("time"), op.get("slot_label"))
            if slot is None:
                # 없는 시각이면 새 시간대를 만들고 그 칸에(연산 순서대로 적용되므로 같은 묶음에서 찾는다)
                new_slot = tl.new_slot(op.get("slot_label") or "새 시간대", op.get("time"), is_new=True)
                out.append({"op": "add_slot", "time": op.get("time"), "label": new_slot["label"], "_slot_hint": True})
                out.append({"op": "add_beat", "_find_time": texts.norm_time(op.get("time")), "_find_label": new_slot["label"],
                            "role_id": role["id"] if role else None, "text": op.get("text") or "", "place": op.get("place") or ""})
            else:
                out.append({"op": "add_beat", "slot_id": slot["id"], "role_id": role["id"] if role else None, "text": op.get("text") or "",
                            "place": op.get("place") or ""})
        elif kind in ("set_beat", "shorten_role", "remove_beat"):
            for sc in tl.scenes(doc):
                if op.get("scene") and sc["no"] != op["scene"]:
                    continue
                for b in sc.get("beats") or []:
                    if role and b.get("role_id") != role["id"]:
                        continue
                    if kind == "remove_beat":
                        out.append({"op": "remove_beat", "beat_id": b["id"]})
                    else:
                        new_text = op.get("new_text") or op.get("text") or (texts.clip(b["text"], 16) if kind == "shorten_role" else None)
                        if new_text:
                            out.append({"op": "set_beat", "beat_id": b["id"], "text": new_text})
    return out


async def t_nl_edit(state: State) -> State:
    p = state["payload"]
    doc = await repo.require_sc(state["scenario_id"])
    try:
        res = await llm.json_call("sc.timeline_edit", prompts.timeline_edit(doc, p["text"]), prompts.TimelineEditOut,
                                  customer=doc.get("customer_name"), timeout=60)
    except llm.LlmError as exc:
        await service.clear_active(state["scenario_id"], _job_id())
        raise ApiError(exc.status, exc.code, exc.message) from exc
    raw_ops = res.data.get("ops") or []

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        ops = translate_timeline_ops(d, raw_ops)
        if not ops:
            service.set_active(d, None)
            return d
        tl.push_undo(d)
        for op in ops:
            if op.get("_find_time") is not None or op.get("_find_label"):
                slot = _slot_for(d, op.get("_find_time"), op.get("_find_label"))
                if slot is None:
                    continue
                op = {k: v for k, v in op.items() if not k.startswith("_")}
                op["slot_id"] = slot["id"]
            op = {k: v for k, v in op.items() if not k.startswith("_")}
            try:
                tl.apply_op(d, op)
            except ApiError as exc:
                log.info("편집 요청 연산 건너뜀 %s: %s", op, exc.message)
        tl.normalize(d)
        d["dirty"] = True
        service.set_active(d, None)
        return d
    doc = await repo.update(state["scenario_id"], fn)
    return {"result": {"applied": len(raw_ops), "changes_count": (doc.get("edit") or {}).get("changes", 0)}}


def build_timeline_edit() -> StateGraph:
    g = StateGraph(State)
    g.add_node("timeline_ops", t_nl_edit)
    g.add_edge(START, "timeline_ops")
    g.add_edge("timeline_ops", END)
    return g


async def t_lane_rewrite(state: State) -> State:
    p = state["payload"]
    rid = p["role_id"]
    doc = await repo.require_sc(state["scenario_id"])
    role = tl.role_by_id(doc, rid)

    async def unmark() -> None:
        def fn(d: dict[str, Any]) -> dict[str, Any]:
            r = tl.role_by_id(d, rid)
            if r:
                r["rewriting"] = False
            service.set_active(d, None)
            return d
        await repo.update(state["scenario_id"], fn)

    if role is None:
        await unmark()
        return {"result": {"changed": 0}}
    try:
        res = await llm.json_call("sc.lane_rewrite", prompts.lane_rewrite(doc, role), prompts.LaneRewriteOut,
                                  customer=doc.get("customer_name"), timeout=60)
    except llm.LlmError as exc:
        await unmark()
        raise ApiError(exc.status, exc.code, exc.message) from exc
    new = {int(b["scene"]): policy.clean(b["text"]) for b in res.data.get("beats") or [] if b.get("text")}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        changed = 0
        for sc in tl.scenes(d):
            if sc["no"] not in new:
                continue
            for b in sc.get("beats") or []:
                if b.get("role_id") == rid and b.get("text") != new[sc["no"]]:
                    b["text"] = texts.clip(new[sc["no"]], tl.BEAT_MAX)
                    changed += 1
        r = tl.role_by_id(d, rid)
        if r:
            r["rewriting"] = False
        d["dirty"] = True
        service.set_active(d, None)
        d["_lane_changed"] = changed
        return d
    doc = await repo.update(state["scenario_id"], fn)
    return {"result": {"changed": doc.get("_lane_changed", 0)}}


def build_lane_rewrite() -> StateGraph:
    g = StateGraph(State)
    g.add_node("lane_rewrite", t_lane_rewrite)
    g.add_edge(START, "lane_rewrite")
    g.add_edge("lane_rewrite", END)
    return g


# ═════════════ sc.recommend (§7.5) ═════════════

def _quote_ok(raw: str, quote: str) -> bool:
    import re as _re
    q = _re.sub(r"\s+", " ", (quote or "").strip().strip("‘’'\"“”"))
    r = _re.sub(r"\s+", " ", raw or "")
    return bool(q) and q in r


async def r_match(state: State) -> State:
    doc = await repo.require_sc(state["scenario_id"])
    cand = [s["id"] for s in seed.solutions()]
    if doc.get("solution_picks"):
        cand = list(dict.fromkeys([*(p["solution_id"] for p in doc["solution_picks"]), *cand]))
    res = await llm.try_json("sc.recommend", prompts.recommend(doc, cand), prompts.RecommendOut, customer=doc.get("customer_name"),
                             timeout=90)
    items: dict[int, dict[str, Any]] = {}
    if res is not None:
        for it in res.data.get("items") or []:
            s = seed.solution_by_name(it.get("solution"))
            if not s:
                continue
            a = seed.action_by_label(s["id"], it.get("action") or "")
            if not a:
                continue
            tag = it.get("tag") or "recommended"
            items[int(it["scene_no"])] = {"solution_id": s["id"], "action_code": a["code"], "tag": tag,
                                          "benefit": it.get("benefit") or a["benefit"], "product_only_text": it.get("product_only_text") or "",
                                          "title_line": texts.clip(it.get("title_line") or "", 40),
                                          "quote": it.get("evidence_quote") or "",
                                          "needs_solution": bool(it.get("needs_solution")) or tag == "required"}
    # 대체: 동작 사전 키워드 규칙
    for sc in tl.scenes(doc):
        if sc["no"] in items:
            continue
        line = prompts.line_for_slot(doc, tl.slot_by_id(doc, sc["slot_id"]))
        text = " ".join([line, *(b.get("text") or "" for b in sc.get("beats") or [])])
        m = seed.match_actions(text)
        if m:
            best = m[0]
            a = seed.action(best["solution_id"], best["action_code"]) or {}
            tag = "required" if best["required"] else ("optional" if best["optional"] else "recommended")
            kw = next((k for k in [*(a.get("required_keywords") or []), *(a.get("keywords") or [])] if k in line), "")
            items[sc["no"]] = {"solution_id": best["solution_id"], "action_code": best["action_code"], "tag": tag, "benefit": a.get("benefit") or "",
                               "product_only_text": "", "quote": kw and line[line.find(kw):][:40], "needs_solution": tag == "required"}
        else:
            a = seed.action("magicinfo", "daypart_layout") or {}
            items[sc["no"]] = {"solution_id": "magicinfo", "action_code": "daypart_layout", "tag": "optional", "benefit": a.get("benefit") or "",
                               "product_only_text": "", "quote": "", "needs_solution": False}
    return {"data": {"items": {str(k): v for k, v in items.items()}, "anonymized": bool(res and res.anonymized)}}


async def r_evidence(state: State) -> State:
    doc = await repo.require_sc(state["scenario_id"])
    raw = doc.get("raw_text") or ""
    ind = seed.industry(doc.get("vertical_code"))
    vertical = (ind or {}).get("kr_verticals") or []
    out = []
    for sc in tl.scenes(doc):
        it = state["data"]["items"].get(str(sc["no"]))
        if not it:
            continue
        ev: list[dict[str, Any]] = []
        if it["tag"] == "optional":
            ev.append({"kind": "product_only", "text": "제품만으로 장면이 완성돼요"})
        else:
            q = (it.get("quote") or "").strip().strip("‘’'\"“”")
            if q and _quote_ok(raw, q):
                e: dict[str, Any] = {"kind": "input_quote", "text": q}
                if it["tag"] == "required":
                    s = seed.solution(it["solution_id"]) or {}
                    n = await kbq.case_count(vertical[0] if vertical else None, s.get("kb_id"))
                    label = (ind or {}).get("case_label") or "업종"
                    e["case_count"] = n
                    e["case_text"] = f"· {label} 사례 {n if n else '[00]'}건"
                ev.append(e)
        if not ev:
            ev.append({"kind": "product_only", "text": "제품만으로 장면이 완성돼요"} if it["tag"] == "optional" else
                      {"kind": "input_quote", "text": ""})
            ev = [e for e in ev if e.get("text")]
        prod_text = it.get("product_only_text") or _product_only(doc, sc)
        out.append({"scene_id": sc["id"], "product_only_text": prod_text, "title_line": it.get("title_line") or "", "evidence": ev,
                    "solution_id": it["solution_id"],
                    "action_code": it["action_code"], "benefit": it["benefit"], "tag": it["tag"], "applied": it["tag"] != "optional",
                    "needs_solution": bool(it.get("needs_solution"))})
    return {"data": {**state["data"], "recs": out}}


def _product_only(doc: dict[str, Any], sc: dict[str, Any]) -> str:
    beats = sc.get("beats") or []
    chips = " + ".join(service.product_chip(p) for p in (doc.get("product_picks") or [])[:2])
    first = beats[0]["text"] if beats else ""
    return texts.clip(" · ".join(x for x in [first, chips] if x), 40)


async def r_save(state: State) -> State:
    recs = state["data"]["recs"]
    anonymized = state["data"].get("anonymized")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        prev = d.get("recommendation") or {}
        d["recommendation"] = {"status": "ready", "job_id": _job_id(), "items": recs, "entered_with_type": prev.get("entered_with_type") or d.get("type"),
                               "computed_at": now_iso()}
        if anonymized:
            d["anonymized"] = True
        service.set_active(d, None)
        return d
    await repo.update(state["scenario_id"], fn)
    return {"result": {"count": len(recs)}}


def build_recommend() -> StateGraph:
    g = StateGraph(State)
    g.add_node("match", r_match)
    g.add_node("evidence", r_evidence)
    g.add_node("save", r_save)
    g.add_edge(START, "match")
    g.add_edge("match", "evidence")
    g.add_edge("evidence", "save")
    g.add_edge("save", END)
    return g


# ═════════════ sc.generate (§7.6) ═════════════

STAGES = [("split", "장면 나누기"), ("write", "장면별 이야기 쓰기"), ("link", "솔루션 동작 · 제품 연결"), ("confirm", "확인 필요 표시")]
CONFIRM_NOTE = "근거 없는 수치는 [00]으로 두고 표시"


def _gen(d: dict[str, Any]) -> dict[str, Any]:
    return d.setdefault("generation", {}) or {}


async def g_load(state: State) -> State:
    jid = _job_id()

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        g = d.get("generation") or {}
        if g.get("job_id") != jid:
            g = {"job_id": jid, "scope": state["payload"].get("scope") or "all", "scene_ids": state["payload"].get("scene_ids"),
                 "prepared": False, "done": 0, "total": 0, "memos": [], "durations": [], "notes": {}}
        g["status"] = "running"
        g["failed_reason"] = None
        g["stage"] = g.get("stage") or "split"
        d["generation"] = g
        d["status"] = "generating"
        d["step"] = 4
        return d
    doc = await repo.update(state["scenario_id"], fn)
    await service.register(doc)
    return {}


async def g_split(state: State) -> State:
    """장면 나누기: 쓸 장면 목록 확정(잠긴 장면은 건너뜀 표시)."""

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        g = d["generation"]
        if g.get("prepared"):
            return d
        tl.settle(d)
        targets = []
        for sc in tl.scenes(d):
            if g.get("scene_ids") and sc["id"] not in g["scene_ids"]:
                continue
            if g.get("scope") == "unlocked" and sc.get("locked"):
                continue
            targets.append(sc["id"])
        for sc in d["scenes"]:
            if sc["id"] in targets:
                sc["status"] = "waiting"
                sc["partial_story"] = None
        g["targets"] = targets
        g["total"] = len(targets)
        g["done"] = 0
        g["prepared"] = True
        g["stage"] = "write"
        labels = [tl.scene_label(d, s) for s in tl.scenes(d) if s["id"] in targets]
        g.setdefault("notes", {})["split"] = texts.join(labels)
        return d
    doc = await repo.update(state["scenario_id"], fn)
    g = doc["generation"]
    await _stage("split", "장면 나누기", g["notes"]["split"], "done", total=g["total"], done=0)
    await _progress(10, "장면 나누기", pct=10, eta_s=None)
    remaining = sum(1 for sid in g.get("targets") or [] if (tl.scene_by_id(doc, sid) or {}).get("status") != "done")
    return {"remaining": remaining}


async def g_write(state: State) -> State:
    """다음 대기 장면 하나 쓰기(메모 반영 · 스트리밍 부분 글 → log 이벤트)."""
    ctx = current_job()
    sid = state["scenario_id"]
    doc = await repo.require_sc(sid)
    g = doc["generation"]
    targets = g.get("targets") or []
    nxt = next((x for x in targets if (tl.scene_by_id(doc, x) or {}).get("status") != "done"), None)
    if nxt is None:
        return {"remaining": 0}
    new_memos = [m.get("text") for m in (await ctx.new_memos() if ctx else []) if m.get("text")]
    done_before = sum(1 for x in targets if (tl.scene_by_id(doc, x) or {}).get("status") == "done")
    sc = tl.scene_by_id(doc, nxt)
    label = tl.scene_label(doc, sc)
    note = f"장면 {sc['no']} · {label} 작성 중 ({done_before} / {len(targets)} 완료)"

    def mark_writing(d: dict[str, Any]) -> dict[str, Any]:
        gg = d["generation"]
        if new_memos:
            gg["memos"] = [*(gg.get("memos") or []), *new_memos]
        gg["notes"]["write"] = note
        gg["stage"] = "write"
        s = tl.scene_by_id(d, nxt)
        if s:
            s["status"] = "writing"
        return d
    doc = await repo.update(sid, mark_writing)
    memos = list(doc["generation"].get("memos") or [])
    await _stage("write", "장면별 이야기 쓰기", note, "run", done=done_before, total=len(targets), scene_id=nxt)
    durs = doc["generation"].get("durations") or []
    avg = (sum(durs) / len(durs)) if durs else 8.0
    pct = 10 + 70 * done_before / max(1, len(targets))
    await _progress(pct, note, pct=int(pct), eta_s=avg * (len(targets) - done_before) + 4)
    stream = await llm.streaming_supported()
    last_write = [0.0]

    async def on_partial(text: str) -> None:
        await _emit("log", {"scene_id": nxt, "partial_story": text})
        now = time.monotonic()
        if now - last_write[0] > 1.0:
            last_write[0] = now

            def put_partial(d: dict[str, Any]) -> dict[str, Any] | None:
                s = tl.scene_by_id(d, nxt)
                if not s or s.get("status") != "writing":
                    return None
                s["partial_story"] = text
                return d
            try:
                await repo.update(sid, put_partial)
            except ApiError:
                pass

    t0 = time.monotonic()
    await compose.sleep_pace()
    try:
        new_scene, anonymized = await compose.compose_scene(doc, sc, memos=memos, stream=stream, on_partial=on_partial,
                                                            rewrite=bool(sc.get("story")) and g.get("scope") == "unlocked")
    except llm.LlmError as exc:
        def mark_failed(d: dict[str, Any]) -> dict[str, Any]:
            s = tl.scene_by_id(d, nxt)
            if s:
                s["status"] = "waiting" if not s.get("story") else "done"
                s["partial_story"] = None
            return d
        await repo.update(sid, mark_failed)
        raise ApiError(exc.status, exc.code, exc.message) from exc
    dt = time.monotonic() - t0
    reason = "다시 생성" if g.get("scope") == "unlocked" and sc.get("story") else "생성"

    def save(d: dict[str, Any]) -> dict[str, Any]:
        s = tl.scene_by_id(d, nxt)
        if s is None:
            return d
        prev = service.scene_snapshot(s) if s.get("version") else None
        for k in ("title", "story", "beats", "solutions", "products", "characters", "confirm_tokens", "evidence", "place", "status"):
            s[k] = new_scene[k]
        s["partial_story"] = None
        s["is_new"] = False
        s["story_check"] = False
        service.mark_new(s, prev)
        service.bump_scene(s, reason)
        gg = d["generation"]
        gg["done"] = sum(1 for x in gg.get("targets") or [] if (tl.scene_by_id(d, x) or {}).get("status") == "done")
        gg["durations"] = [*(gg.get("durations") or []), round(dt, 2)][-12:]
        if anonymized:
            d["anonymized"] = True
        d["dirty"] = True
        return d
    doc = await repo.update(sid, save)
    await service.commit_scene_versions(doc, [nxt], reason)
    s = tl.scene_by_id(doc, nxt)
    done = doc["generation"]["done"]
    await _emit("partial", {"scene_id": nxt, "status": "done", "title": s.get("title"), "chips": seed.chip_labels(s.get("solutions") or []),
                            "products": [service.product_chip(p) for p in s.get("products") or []]})
    pct = 10 + 70 * done / max(1, len(targets))
    durs = doc["generation"].get("durations") or []
    avg = (sum(durs) / len(durs)) if durs else 8.0
    await _progress(pct, f"장면 {done} / {len(targets)} 완료", pct=int(pct), eta_s=avg * (len(targets) - done) + 4)
    remaining = sum(1 for x in targets if (tl.scene_by_id(doc, x) or {}).get("status") != "done")
    await service.register(doc)
    return {"remaining": remaining}


def _after_write(state: State) -> str:
    return "write_scene" if (state.get("remaining") or 0) > 0 else "link"


async def g_link(state: State) -> State:
    doc = await repo.require_sc(state["scenario_id"])
    counts: dict[str, int] = {}
    for sc in tl.scenes(doc):
        for sid in {x["solution_id"] for x in sc.get("solutions") or []}:
            counts[sid] = counts.get(sid, 0) + 1
    note = texts.join([f"{(seed.solution(k) or {}).get('name', k)} {v}장면" for k, v in counts.items()]) or "제품 활용만"

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["generation"].setdefault("notes", {})["link"] = note
        d["generation"]["stage"] = "link"
        return d
    await repo.update(state["scenario_id"], fn)
    await _stage("write", "장면별 이야기 쓰기", f"{len(doc['generation'].get('targets') or [])}개 장면 완료", "done")
    await _stage("link", "솔루션 동작 · 제품 연결", note, "done")
    await _progress(90, "솔루션 동작 · 제품 연결", pct=90, eta_s=2)
    return {}


async def g_confirm(state: State) -> State:
    """확인 필요 표시: 숫자 토큰마다 근거 대조(멱등 — 이미 [00] 인 것은 그대로)."""
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for sc in d.get("scenes") or []:
            if sc.get("status") == "done" and sc["id"] in (d["generation"].get("targets") or []):
                service.finalize_text(d, sc)
        d["generation"].setdefault("notes", {})["confirm"] = CONFIRM_NOTE
        d["generation"]["stage"] = "confirm"
        return d
    await repo.update(state["scenario_id"], fn)
    await _stage("confirm", "확인 필요 표시", CONFIRM_NOTE, "done")
    await _progress(96, "확인 필요 표시", pct=96, eta_s=1)
    return {}


async def g_finalize(state: State) -> State:
    sid = state["scenario_id"]
    await sheets.ensure_space_keys(sid)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        g = d["generation"]
        g["status"] = "done"
        g["stage"] = "done"
        d["status"] = "done"
        d["step"] = 4
        d["saved_version"] = int(d.get("saved_version") or 0) + 1
        d["dirty"] = False
        d["last_saved_at"] = now_iso()
        service.set_active(d, None)
        return d
    doc = await repo.update(sid, fn)
    await repo.put_version(sid, int(doc["saved_version"]), _snapshot(doc), "시나리오 생성", doc.get("owner"))
    await service.register(doc)
    try:
        await jobs().push_notification(doc.get("owner") or "system", {
            "type": "scenario_done", "job_id": _job_id(), "service": "scenario", "title": f"{doc.get('title')} · 시나리오 완성",
            "ref": sid, "route": f"/scenario/{sid}/result", "status": "succeeded"})
    except Exception as exc:  # noqa: BLE001
        log.info("완료 알림 실패: %s", exc)
    return {"result": {"scenario_id": sid, "scene_ids": [s["id"] for s in tl.scenes(doc)], "version": doc["saved_version"]}}


def _snapshot(doc: dict[str, Any]) -> dict[str, Any]:
    import copy
    keep = {k: v for k, v in doc.items() if k not in ("edit",)}
    return copy.deepcopy(keep)


def build_generate() -> StateGraph:
    g = StateGraph(State)
    g.add_node("load", g_load)
    g.add_node("split_scenes", g_split)
    g.add_node("write_scene", g_write)
    g.add_node("link", g_link)
    g.add_node("mark_confirm", g_confirm)
    g.add_node("finalize", g_finalize)
    g.add_edge(START, "load")
    g.add_edge("load", "split_scenes")
    g.add_conditional_edges("split_scenes", _after_write, {"write_scene": "write_scene", "link": "link"})
    g.add_conditional_edges("write_scene", _after_write, {"write_scene": "write_scene", "link": "link"})
    g.add_edge("link", "mark_confirm")
    g.add_edge("mark_confirm", "finalize")
    g.add_edge("finalize", END)
    return g


async def mark_generation_stopped(sc_id: str, *, failed_reason: str | None = None, canceled: bool = False) -> None:
    """중지 · 실패: 끝난 장면은 done 으로 남기고 나머지는 waiting(§7.6)."""
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        g = d.get("generation") or {}
        for sc in d.get("scenes") or []:
            if sc.get("status") == "writing":
                sc["status"] = "done" if sc.get("version") and sc.get("story") else "waiting"
                sc["partial_story"] = None
        if canceled:
            g["status"] = "canceled"
            d["status"] = "draft"
            d["step"] = 3
        else:
            g["status"] = "failed"
            g["failed_reason"] = failed_reason or "알 수 없는 오류"
            d["status"] = "failed"
        d["generation"] = g
        service.set_active(d, None)
        return d
    doc = await repo.update(sc_id, fn)
    await service.register(doc)


# ═════════════ sc.rewrite_scene · sc.edit · sc.shorten (§7.7) ═════════════

async def rewrite_one(sc_id: str, scene_id: str, *, preset: str | None = None, pov_role_id: str | None = None,
                      instruction: str | None = None, reason: str = "방금 수정 요청 반영") -> dict[str, Any]:
    doc = await repo.require_sc(sc_id)
    sc = tl.scene_by_id(doc, scene_id)
    if sc is None:
        raise ApiError(404, "NOT_FOUND", "장면을 찾을 수 없어요")
    pov = tl.role_by_id(doc, pov_role_id)
    # 「새로」 기준 = 마지막으로 남긴 버전(수정 요청이 먼저 넣은 인물 · 제품도 새로 표시되게)
    committed = await repo.get_scene_version(scene_id, int(sc.get("version") or 0)) if sc.get("version") else None
    base = (committed or {}).get("scene") or (committed or {}).get("json")
    await compose.sleep_pace()
    try:
        new_scene, anonymized = await compose.compose_scene(doc, sc, preset=preset, pov_role=(pov or {}).get("name"),
                                                            instruction=instruction, rewrite=True)
    except llm.LlmError as exc:
        raise ApiError(exc.status, exc.code, exc.message) from exc
    if preset == "pov" and pov:
        new_scene["beats"] = sorted(new_scene["beats"], key=lambda b: 0 if b.get("role_id") == pov["id"] else 1)
        for i, b in enumerate(new_scene["beats"]):
            b["primary"] = i == 0

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = tl.scene_by_id(d, scene_id)
        if s is None:
            return d
        prev = base if isinstance(base, dict) else service.scene_snapshot(s)
        for k in ("title", "story", "beats", "solutions", "products", "characters", "confirm_tokens", "evidence", "place", "status"):
            s[k] = new_scene[k]
        s["rewriting"] = False
        s["story_check"] = False
        service.mark_new(s, prev)
        service.bump_scene(s, reason)
        if anonymized:
            d["anonymized"] = True
        d["dirty"] = True
        return d
    doc = await repo.update(sc_id, fn)
    await service.commit_scene_versions(doc, [scene_id], reason)
    return doc


async def w_rewrite(state: State) -> State:
    p = state["payload"]
    try:
        await rewrite_one(state["scenario_id"], p["scene_id"], preset=p.get("preset"), pov_role_id=p.get("pov_role_id"),
                          instruction=p.get("instruction"), reason=p.get("reason") or "방금 수정 요청 반영")
    finally:
        await _clear_rewriting(state["scenario_id"], [p["scene_id"]])
    return {"result": {"scene_id": p["scene_id"]}}


async def _clear_rewriting(sc_id: str, scene_ids: list[str]) -> None:
    jid = _job_id()

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for sid in scene_ids:
            s = tl.scene_by_id(d, sid)
            if s:
                s["rewriting"] = False
        if (d.get("active_job") or {}).get("job_id") == jid:
            d["active_job"] = None
        return d
    try:
        await repo.update(sc_id, fn)
    except ApiError:
        pass


def build_rewrite() -> StateGraph:
    g = StateGraph(State)
    g.add_node("rewrite_scene", w_rewrite)
    g.add_edge(START, "rewrite_scene")
    g.add_edge("rewrite_scene", END)
    return g


async def _resolve_product(doc: dict[str, Any], name: str) -> dict[str, Any] | None:
    hit = compose._find_pick(doc, name)
    if hit:
        return {**hit, "source": hit.get("source") or "user"}
    items = await kbq.products_search(name, limit=3)
    if items:
        it = items[0]
        # 칩은 요청에 나온 이름 그대로(「Galaxy Tab Active5」), KB 참조는 이미지 · 스펙용으로 붙인다
        return {"ref": f"kb:{it['kind']}:{it['id']}", "family_id": it.get("family_id"), "model_code": it.get("model_code"),
                "label": it.get("label") or it.get("display_name") or name, "short": name, "qty": None, "source": "user"}
    return {"ref": f"custom:{name}", "family_id": None, "model_code": None, "label": name, "short": name, "qty": None, "source": "user"}


async def e_edit(state: State) -> State:
    """SC4 수정 요청: LLM → 연산 → 적용 → 영향 장면만 다시 쓰기(순차)."""
    p = state["payload"]
    sid = state["scenario_id"]
    doc = await repo.require_sc(sid)
    import re as _re
    nos = [int(x) for x in _re.findall(r"장면\s*(\d+)", p["text"]) if tl.scene_by_no(doc, int(x))]
    try:
        res = await llm.json_call("sc.edit", prompts.edit(doc, p["text"]), prompts.EditOut, customer=doc.get("customer_name"), timeout=60)
        ops = res.data.get("ops") or []
    except llm.LlmError as exc:
        if not nos:
            await _clear_rewriting(sid, [])
            raise ApiError(exc.status, exc.code, exc.message) from exc
        ops = []
    if not ops:
        if not nos:
            await _clear_rewriting(sid, [])
            raise ApiError(400, "EDIT_UNCLEAR", "어느 장면을 고칠지 알 수 없어요. 「장면 2에 …」처럼 장면 번호를 적어 주세요.")
        ops = [{"op": "rewrite", "scene": n, "instruction": p["text"]} for n in nos]
    resolved: list[dict[str, Any]] = []
    for op in ops:
        if op.get("op") == "add_product" and op.get("product"):
            prod = await _resolve_product(doc, op["product"])
            resolved.append({**op, "_product": prod})
        else:
            resolved.append(op)
    affected: list[str] = []
    instructions: dict[str, list[str]] = {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        affected.clear()
        instructions.clear()
        for op in resolved:
            kind = op.get("op")
            sc = tl.scene_by_no(d, int(op["scene"])) if op.get("scene") else None
            if kind == "add_scene":
                after = tl.scene_by_no(d, int(op.get("after") or 0)) if op.get("after") else None
                slot = tl.new_slot(op.get("label") or "새 장면", op.get("time"), is_new=True)
                sl = tl.slots(d)
                idx = next((i for i, s in enumerate(sl) if after and s["id"] == after["slot_id"]), len(sl) - 1)
                sl.insert(idx + 1, slot)
                d["slots"] = sl
                role = tl.role_by_name(d, op.get("role")) or (tl.roles(d)[0] if d.get("roles") else None)
                beat = tl.new_beat(role["id"] if role else None, op.get("text") or op.get("label") or "새 장면", primary=True)
                ns = tl.new_scene(slot["id"], [beat], is_new=True)
                d["scenes"].append(ns)
                tl.normalize(d)
                affected.append(ns["id"])
                instructions.setdefault(ns["id"], []).append(p["text"])
                continue
            if sc is None:
                continue
            if kind == "add_beat":
                role = tl.role_by_name(d, op.get("role"))
                if role is None and op.get("role"):
                    role = tl.new_role(op["role"], ord_=len(d["roles"]), source="user")
                    d["roles"].append(role)
                if role and not any(b.get("role_id") == role["id"] for b in sc["beats"]):
                    sc["beats"].append(tl.new_beat(role["id"], op.get("text") or "", ""))
                elif role:
                    for b in sc["beats"]:
                        if b.get("role_id") == role["id"] and op.get("text"):
                            b["text"] = texts.clip(op["text"], tl.BEAT_MAX)
                if role and not any(c.get("role_id") == role["id"] for c in sc.get("characters") or []):
                    sc.setdefault("characters", []).append({"role_id": role["id"], "is_new": True})
            elif kind == "add_product" and op.get("_product"):
                prod = op["_product"]
                if not any(service.product_key(x) == service.product_key(prod) for x in sc.get("products") or []):
                    sc.setdefault("products", []).append({k: prod.get(k) for k in ("ref", "family_id", "model_code", "short", "label", "qty")} | {"is_new": True})
                if not any(service.product_key(x) == service.product_key(prod) for x in d.get("product_picks") or []):
                    d.setdefault("product_picks", []).append({**{k: prod.get(k) for k in ("ref", "family_id", "model_code", "label", "short", "qty")},
                                                              "source": "user", "ord": len(d.get("product_picks") or [])})
            elif kind == "add_solution" and op.get("solution"):
                s = seed.solution_by_name(op["solution"])
                a = seed.action_by_label(s["id"], op.get("action") or "") if s else None
                if s and a:
                    if not any(x["solution_id"] == s["id"] for x in d.get("solution_picks") or []) and d.get("type") == "with":
                        d.setdefault("solution_picks", []).append({"solution_id": s["id"], "name": s["name"], "source": "user",
                                                                   "ord": len(d.get("solution_picks") or [])})
                    sc.setdefault("solutions", []).append({"solution_id": s["id"], "action_code": a["code"], "label": seed.action_label(s["id"], a["code"]),
                                                           "is_new": True})
            if op.get("instruction") or op.get("text"):
                instructions.setdefault(sc["id"], []).append(op.get("instruction") or op.get("text"))
            if sc["id"] not in affected:
                affected.append(sc["id"])
        for x in affected:
            s = tl.scene_by_id(d, x)
            if s:
                s["rewriting"] = True
        d["dirty"] = True
        return d
    await repo.update(sid, fn)
    try:
        for x in affected:
            await rewrite_one(sid, x, instruction=" / ".join([p["text"], *instructions.get(x, [])][:2]), reason="방금 수정 요청 반영")
            await _clear_rewriting(sid, [x])
    finally:
        await _clear_rewriting(sid, list(affected))
    doc = await repo.require_sc(sid)
    await service.register(doc)
    return {"result": {"scene_ids": affected}}


def build_edit() -> StateGraph:
    g = StateGraph(State)
    g.add_node("edit_ops", e_edit)
    g.add_edge(START, "edit_ops")
    g.add_edge("edit_ops", END)
    return g


async def h_shorten(state: State) -> State:
    sid = state["scenario_id"]
    doc = await repo.require_sc(sid)
    ids = [s["id"] for s in tl.scenes(doc) if s.get("story")]
    try:
        for x in ids:
            try:
                await rewrite_one(sid, x, preset="shorter", reason="더 짧게")
            except ApiError as exc:
                if exc.status in (503, 504, 403):
                    raise
            await _clear_rewriting(sid, [x])
    finally:
        await _clear_rewriting(sid, ids)
    return {"result": {"scene_ids": ids}}


def build_shorten() -> StateGraph:
    g = StateGraph(State)
    g.add_node("shorten", h_shorten)
    g.add_edge(START, "shorten")
    g.add_edge("shorten", END)
    return g


# ═════════════ sc.images_batch (§7.8 일괄) ═════════════

async def i_batch(state: State) -> State:
    sid = state["scenario_id"]
    doc = await repo.require_sc(sid)
    targets = [s["id"] for s in tl.scenes(doc) if not s.get("image") and s.get("story")]
    made: list[str] = []
    for i, scene_id in enumerate(targets):
        ctx = current_job()
        if ctx:
            await ctx.check_cancel()
        doc = await repo.require_sc(sid)
        sc = tl.scene_by_id(doc, scene_id)
        if sc is None or sc.get("image"):
            continue

        async def set_job(status: str, render_id: str | None = None, error: str | None = None, _sid: str = scene_id) -> None:
            def fn(d: dict[str, Any]) -> dict[str, Any]:
                s = tl.scene_by_id(d, _sid)
                if s:
                    s["image_job"] = {"status": status, "render_id": render_id, "error": error} if status != "done" else None
                return d
            await repo.update(sid, fn)
        await set_job("running")
        await _progress(100 * i / max(1, len(targets)), f"장면 {sc['no']} 이미지 만드는 중")
        try:
            acc = await imaging.start_render(doc, sc)
            r = await imaging.wait_render(acc["render_id"])
            if r.get("status") != "succeeded" or not r.get("version_id"):
                raise RuntimeError(((r.get("error") or {}).get("message")) or "이미지를 만들지 못했어요")
            block = await imaging.image_block(doc, sc, r["version_id"], "image_render")
        except Exception as exc:  # noqa: BLE001
            log.info("장면 이미지 렌더 실패 %s: %s", scene_id, exc)
            await set_job("failed", error="이미지를 만들지 못했어요")
            continue

        def attach(d: dict[str, Any], _sid: str = scene_id, _block: dict[str, Any] = block) -> dict[str, Any]:
            s = tl.scene_by_id(d, _sid)
            if s:
                s["image"] = _block
                s["image_job"] = None
                s["image_stale_forced"] = False
            d["dirty"] = True
            return d
        doc = await repo.update(sid, attach)
        await imaging.register_usage(doc, tl.scene_by_id(doc, scene_id) or sc, block.get("image_id"), block["version_id"])
        made.append(scene_id)
        await _emit("partial", {"scene_id": scene_id, "image": True})

    def done(d: dict[str, Any]) -> dict[str, Any]:
        d["images_job"] = None
        service.set_active(d, None)
        return d
    await repo.update(sid, done)
    return {"result": {"scene_ids": made}}


def build_images() -> StateGraph:
    g = StateGraph(State)
    g.add_node("render_missing", i_batch)
    g.add_edge(START, "render_missing")
    g.add_edge("render_missing", END)
    return g


# ═════════════ sc.export (§7.10) ═════════════

async def x_export(state: State) -> State:
    p = state["payload"]
    sid = state["scenario_id"]
    export_id = p["export_id"]
    await sheets.ensure_space_keys(sid)
    doc = await repo.require_sc(sid)
    kind = p["kind"]
    plan_ = sheets.plan(doc)
    base = (doc.get("title") or "공간시나리오").replace(" ", "")
    ex = ServiceClient("export", timeout=300)
    rec = await repo.get_export(export_id) or {}
    await repo.put_export(export_id, {**rec, "status": "running"})
    try:
        if kind in ("pptx", "pdf"):
            body = {"format": "pptx", "filename": f"{base}_시트{len(plan_['sheets'])}장", "document": sheets.pptx_document(doc, plan_),
                    "confidential": bool(doc.get("customer_name")), "source_ref": f"scenario:{sid}", "tbd_label": "[확정 필요]",
                    **({"project_id": doc["project_id"]} if doc.get("project_id") else {})}
            res = await ex.post("/v1/exports", json=body)
            res = await _await_export(ex, res)
            if kind == "pdf":
                pdf = await ex.post("/v1/exports", json={"format": "pdf", "filename": f"{base}_시트{len(plan_['sheets'])}장",
                                                         "from_file_id": res["file"]["id"], "source_ref": f"scenario:{sid}",
                                                         "confidential": bool(doc.get("customer_name"))})
                res = await _await_export(ex, pdf)
        elif kind == "docx":
            res = await ex.post("/v1/exports", json={"format": "docx", "filename": f"{base}_장면스크립트", "document": sheets.docx_document(doc),
                                                     "source_ref": f"scenario:{sid}", "confidential": bool(doc.get("customer_name"))})
            res = await _await_export(ex, res)
        else:
            entries = sheets.zip_entries(doc)
            if len(entries) <= 1:
                raise ApiError(422, "NO_IMAGES", "장면 이미지가 없어요")
            res = await ex.post("/v1/exports", json={"format": "zip", "filename": f"{base}_장면이미지", "document": {"entries": entries},
                                                     "source_ref": f"scenario:{sid}"})
            res = await _await_export(ex, res)
    except Exception as exc:
        msg = exc.message if isinstance(exc, ApiError) else "파일을 만들지 못했어요"
        await repo.put_export(export_id, {**rec, "status": "failed", "error": msg})
        raise
    f = res.get("file") or {}
    await repo.put_export(export_id, {**rec, "status": "done", "file_id": f.get("id"), "file_name": f.get("name"), "url": f.get("url")})
    return {"result": {"export_id": export_id, "file_id": f.get("id"), "file_name": f.get("name")}}


async def _await_export(ex: ServiceClient, res: dict[str, Any]) -> dict[str, Any]:
    """export 가 202(잡)로 답하면 끝날 때까지 기다린다."""
    import asyncio
    if res.get("file"):
        return res
    eid = res.get("export_id") or res.get("id")
    for _ in range(300):
        await asyncio.sleep(1)
        cur = await ex.get(f"/v1/exports/{eid}")
        if cur.get("status") == "done" and (cur.get("file") or cur.get("files")):
            return {"file": cur.get("file") or (cur.get("files") or [None])[0]}
        if cur.get("status") in ("failed", "error"):
            raise ApiError(502, "EXPORT_FAILED", (cur.get("error") or {}).get("message") or "파일을 만들지 못했어요")
    raise ApiError(504, "EXPORT_TIMEOUT", "파일 만들기가 너무 오래 걸려요")


def build_export() -> StateGraph:
    g = StateGraph(State)
    g.add_node("export", x_export)
    g.add_edge(START, "export")
    g.add_edge("export", END)
    return g
