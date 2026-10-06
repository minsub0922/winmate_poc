"""워크플로 프롬프트에 넣는 맥락 묶음(정의서 · 기획 답 · 방향 · 자리 목록)."""
from __future__ import annotations

from typing import Any

from .rq import RqSnapshot
from .rules import FOLLOWUP_LABELS, SLOT_KEYS, section_label, slot_text


def rq_brief(snap: RqSnapshot, *, internal: bool = False) -> dict[str, Any]:
    """정의서 요약. internal=True 일 때만 제작자 의견(내부용)을 넣는다(분류 · 질의 고르기용)."""
    out: dict[str, Any] = {
        "title": snap.title, "customer_name": snap.customer_name, "project_name": snap.project_name,
        "final_audience": snap.final_audience or None,
        "keymen": [{"name": k["name"], "weight": k.get("weight")} for k in snap.keymen],
        "items": [{"code": i.code, "text": i.text, "short": i.short, "keyman": i.keyman_name,
                   "needs_confirmation": i.needs_confirmation} for i in snap.items],
        "context": {k: snap.context.get(k) for k in ("vertical", "spaces", "products", "solutions", "scale_text", "deadline_text")
                    if snap.context.get(k)},
        "open_customer_questions": [q.get("text") for q in snap.open_questions][:10],
        "source_files": [f.get("name") for f in snap.source_files][:6],
    }
    if internal and snap.author_note:
        out["author_note_internal"] = snap.author_note
    return out


def answers_brief(doc: dict[str, Any]) -> list[dict[str, Any]]:
    qs = {q["id"]: q for q in (doc.get("planning") or {}).get("questions") or []}
    out = []
    for a in (doc.get("planning") or {}).get("answers") or []:
        q = qs.get(a["question_id"])
        if not q:
            continue
        opts = {o["id"]: o for o in q["options"]}
        labels = [opts[i]["label"] for i in a.get("selected_option_ids") or [] if i in opts]
        fu_label = None
        if a.get("follow_up_option_id") and labels:
            fu = (opts.get(a["selected_option_ids"][0]) or {}).get("follow_up") or {}
            hit = next((o for o in fu.get("options") or [] if o["id"] == a["follow_up_option_id"]), None)
            if hit:
                fu_label = f"{hit['label']} ({hit['effect']}: {FOLLOWUP_LABELS.get(hit['effect'], '')})"
        out.append({"topic": q["topic"], "question": q["text"], "answer_in_order": labels,
                    "roles": [q.get("order_roles", [])[i] for i in range(min(len(labels), len(q.get("order_roles") or [])))],
                    "unknown": bool(a.get("unknown")), "follow_up": fu_label})
    return out


def audience_order(doc: dict[str, Any]) -> list[str]:
    for a in answers_brief(doc):
        if a["topic"] == "audience" and not a["unknown"]:
            return a["answer_in_order"]
    return []


def selected_option(doc: dict[str, Any]) -> dict[str, Any] | None:
    dr = doc.get("direction") or {}
    return next((o for o in dr.get("options") or [] if o["id"] == dr.get("selected_option_id")), None)


def direction_brief(doc: dict[str, Any]) -> dict[str, Any]:
    dr = doc.get("direction") or {}
    opt = selected_option(doc) or {}
    return {"title": opt.get("title"), "one_liner": opt.get("one_liner"), "mapping": opt.get("mapping") or [],
            "axes": [{"key": o.get("key"), "title": o["title"], "one_liner": o.get("one_liner")} for o in dr.get("options") or []
                     if o["kind"] == "axis"],
            "key_messages": [{"place": m["place_label"], "audience": m.get("audience"), "text": m["text"]}
                             for m in dr.get("key_messages") or []],
            "extra_direction": dr.get("extra_direction")}


def place_catalog(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """LLM 이 가리킬 수 있는 자리(자리 키 · space:<키>)."""
    outline = doc.get("outline") or {}
    out = []
    for s in outline.get("sections") or []:
        if s["group_key"] == "part2":
            continue
        out.append({"place": s["key"], "label": section_label(s), "direction": s.get("direction")})
    for sp in outline.get("spaces") or []:
        out.append({"place": f"space:{sp['key']}", "label": f"Part 2 {sp['name']}", "purpose": sp.get("purpose"),
                    "slots": {k: slot_text((sp.get("slots") or {}).get(k)) for k in SLOT_KEYS
                              if ((sp.get("slots") or {}).get(k) or {}).get("state") != "empty"}})
    return out


def resolve_place(doc: dict[str, Any], key: str) -> tuple[str, dict[str, Any]] | None:
    """자리 키 → ("section"|"space", 객체)."""
    outline = doc.get("outline") or {}
    key = (key or "").strip()
    if key.startswith("space:"):
        k = key.split(":", 1)[1]
        sp = next((s for s in outline.get("spaces") or [] if s.get("key") == k or s["id"] == k or s["name"] == k), None)
        return ("space", sp) if sp else None
    sec = next((s for s in outline.get("sections") or [] if s.get("key") == key or s["id"] == key or s.get("code") == key),
               None)
    if sec is None and key.lower() in ("part2", "part 2"):
        sec = next((s for s in outline.get("sections") or [] if s["group_key"] == "part2"), None)
    return ("section", sec) if sec else None
