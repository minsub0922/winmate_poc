"""요구 추적 만들기(§7.4 ④ · §7.8) — LLM 결과를 결정적으로 검증한다(가드 5: 정의서 항목은 정확히 한 번씩, 하나도 버리지 않는다)."""
from __future__ import annotations

from typing import Any

from winmate_common.ids import new_id, now_iso

from . import rules
from .brief import resolve_place
from .rq import RqSnapshot, normalize_code

LINK_ORDER = ["direct", "interpreted", "extension", "reviewing", "unconfirmed", "deferred", "excluded"]


def _place(doc: dict[str, Any], key: str) -> dict[str, Any] | None:
    hit = resolve_place(doc, key)
    if not hit:
        return None
    kind, obj = hit
    if kind == "space":
        return {"kind": "space", "id": obj["id"], "label": rules.space_label(obj)}
    return {"kind": "section", "id": obj["id"], "label": rules.section_label(obj)}


def _target(doc: dict[str, Any], key: str | None) -> dict[str, Any] | None:
    if not key:
        return None
    p = _place(doc, key)
    return {"kind": p["kind"], "id": p["id"], "label": p["label"]} if p else None


def fixed_options(keep_first: bool) -> list[dict[str, Any]]:
    out = []
    if keep_first:
        out.append({"id": new_id("opt"), "label": "확인 필요로 유지", "hint": "추정하지 않아요", "kind": "keep_unconfirmed", "target": None})
    out.append({"id": new_id("opt"), "label": "본제안으로 미루기", "hint": "목록에는 남겨요", "kind": "defer_main", "target": None})
    out.append({"id": new_id("opt"), "label": "제외하고 사유 기록", "hint": "목록에는 남겨요", "kind": "exclude", "target": None})
    return out


def build_trace(doc: dict[str, Any], snap: RqSnapshot, out: dict[str, Any], prev: dict[str, Any] | None) -> dict[str, Any]:
    outline = doc.get("outline") or {}
    secs = {s["id"]: s for s in outline.get("sections") or []}
    spaces = {s["id"]: s for s in outline.get("spaces") or []}
    by_code: dict[str, dict[str, Any]] = {}
    for it in out.get("items") or []:
        code = normalize_code(it.get("code") or "")
        if code and code not in by_code:          # 같은 항목은 한 번만
            by_code[code] = it
    prev_items = {i["rq_item_id"]: i for i in (prev or {}).get("items") or []}
    asked = {q.get("target", {}).get("id") for q in snap.open_questions if isinstance(q.get("target"), dict)}
    items = []
    for idx, ri in enumerate(snap.items):
        old = prev_items.get(ri.id)
        if old and old.get("state") == "resolved":
            items.append({**old, "code": ri.code, "short": ri.short or old.get("short") or ri.text[:24], "text": ri.text,
                          "needs_confirmation": ri.needs_confirmation})
            continue
        llm_it = by_code.get(ri.code) or {}
        places = []
        for key in llm_it.get("places") or []:
            p = _place(doc, key)
            if p and not any(x["kind"] == p["kind"] and x["id"] == p["id"] for x in places):
                places.append(p)
        links = [lt for lt in LINK_ORDER if lt in set(llm_it.get("link_types") or [])]
        owner_note = (llm_it.get("owner_note") or "").strip() or None
        problem = llm_it.get("problem")
        if owner_note:
            state = "owner_check"
            places.append({"kind": "owner_check", "id": None, "label": "담당 확인 중"})
            if "unconfirmed" not in links:
                links.append("unconfirmed")
        elif problem or not [p for p in places if p["kind"] in ("section", "space")]:
            state = "to_resolve"
            problem = problem or "no_place"
            if not links:
                links = ["unconfirmed"]
        else:
            state = "ok"
            if not links:
                links = ["direct"]
        question = None
        if state == "to_resolve":
            q = llm_it.get("question") or {}
            opts = []
            for o in (q.get("options") or [])[:2]:
                tgt = _target(doc, o.get("target"))
                if tgt is None:
                    continue
                opts.append({"id": new_id("opt"), "label": o.get("label") or f"{tgt['label']}에 넣기", "hint": o.get("hint") or "",
                             "kind": "place", "target": tgt})
            keep_first = ri.needs_confirmation or ri.id in asked
            fixed = fixed_options(keep_first)
            options = ([fixed[0]] if keep_first else []) + opts + (fixed[1:] if keep_first else fixed)
            rec = None
            if keep_first:
                rec = options[0]["id"]
            elif opts and problem == "empty_content":
                rec = opts[0]["id"]
            question = {"text": q.get("text") or f"{ri.short or ri.text[:24]}{rules.eun(ri.short or ri.text[:24])} 어디에 넣을까요?",
                        "info": q.get("info") or "", "options": options, "recommended_option_id": rec}
        label = llm_it.get("places_label") or rules.places_label(places, secs, spaces) or None
        items.append({
            "rq_item_id": ri.id, "code": ri.code, "short": ri.short or ri.text[:24], "text": ri.text, "places": places,
            "places_label": label, "link_types": links, "state": state, "problem": problem if state == "to_resolve" else None,
            "owner_note": owner_note, "priority": int(llm_it.get("priority") or 0) or (100 + idx), "question": question,
            "resolution": None, "needs_confirmation": ri.needs_confirmation,
        })
    # 정리 순서: LLM 우선순위 → 코드
    order = sorted([i for i in items if i["state"] == "to_resolve"], key=lambda i: (i["priority"], i["code"]))
    for n, it in enumerate(order, 1):
        it["priority"] = n
    prev_ext = {e["name"]: e for e in (prev or {}).get("extensions") or []}
    extensions = []
    for e in out.get("extensions") or []:
        if not e.get("name"):
            continue
        places = [p for p in (_place(doc, k) for k in e.get("places") or []) if p]
        old = prev_ext.get(e["name"]) or {}
        extensions.append({"id": old.get("id") or new_id("ext"), "name": e["name"], "short": e.get("short") or e["name"],
                           "where_label": e.get("where_label") or rules.places_label(places, secs, spaces), "places": places,
                           "derived_from_codes": [normalize_code(c) for c in e.get("derived_from_codes") or []],
                           "status": e.get("status") or "extension", "acknowledged": bool(old.get("acknowledged"))})
    return {"total": len(items), "ok_count": sum(1 for i in items if i["state"] in ("ok", "resolved")), "items": items,
            "extensions": extensions, "computed_at": now_iso(), "stale": False,
            "extensions_acknowledged": bool((prev or {}).get("extensions_acknowledged")) and all(e["acknowledged"] for e in extensions),
            "unconfirmed_item_ids": [i.id for i in snap.items if i.needs_confirmation]}


def merge_discussions(doc: dict[str, Any], section_labels: dict[str, list[str]], llm_discussions: list[dict[str, Any]],
                      prev: list[dict[str, Any]] | None = None, limit: int = 7) -> list[dict[str, Any]]:
    """섹션별 추가 논의 + 추적의 추가 논의 → 번호 매긴 목록(≤ 7)."""
    prev_by_label = {d["label"]: d for d in prev or []}
    out: list[dict[str, Any]] = []

    def add(label: str, short: str | None, section_ids: list[str]) -> None:
        label = label.strip()
        if not label:
            return
        hit = next((d for d in out if d["label"] == label), None)
        if hit:
            for s in section_ids:
                if s not in hit["section_ids"]:
                    hit["section_ids"].append(s)
            if short and not hit.get("short"):
                hit["short"] = short
            return
        old = prev_by_label.get(label) or {}
        out.append({"id": old.get("id") or new_id("dsc"), "n": 0, "label": label, "short": short or old.get("short") or label,
                    "section_ids": list(section_ids), "trace_item_ids": list(old.get("trace_item_ids") or []),
                    "state": old.get("state") or "open"})

    for d in llm_discussions:
        ids = []
        for key in d.get("section_refs") or []:
            hit = resolve_place(doc, key)
            if hit and hit[0] == "section":
                ids.append(hit[1]["id"])
        add(d.get("label") or "", d.get("short"), ids)
    for sec_id, labels in section_labels.items():
        for lab in labels:
            add(lab, None, [sec_id])
    for i, d in enumerate(out[:limit], 1):
        d["n"] = i
    return out[:limit]


def depends_on(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """requirements 링크 `depends_on`(항목 → 스토리보드 위치) — RQ6 `쓰는 곳` · RQ7B `Storyboard {n}곳` 계산 근거."""
    out = []
    outline = doc.get("outline") or {}
    secs = {s["id"]: s for s in outline.get("sections") or []}
    spaces = {s["id"]: s for s in outline.get("spaces") or []}
    for it in (doc.get("trace") or {}).get("items") or []:
        places = []
        for p in it.get("places") or []:
            if p["kind"] == "section" and p.get("id") in secs:
                s = secs[p["id"]]
                places.append({"code": s.get("code") or s.get("key"), "label": rules.section_label(s)})
            elif p["kind"] == "space" and p.get("id") in spaces:
                sp = spaces[p["id"]]
                places.append({"code": f"space:{sp['key']}", "label": rules.space_label(sp)})
        if places:
            out.append({"target": {"kind": "item", "id": it["rq_item_id"]}, "places": places})
    return out
