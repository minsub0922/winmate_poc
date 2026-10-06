"""타임라인(시간대 × 역할 × 장면 · 비트) — 결정적 순수 함수(09-scenario §4.6 · §5.2).

- 장면은 시간대에 속하고 비트(역할별 관점)를 가진다. 장면 번호 = (시간대 순서, 시간대 안 순서)로 1부터.
- 첫 비트가 주 시점(primary) — 카드 라벨 「장면 {n}」, 다른 비트는 「장면 {n} · {역할} 시점」.
- 비트를 다른 시간대로 옮기면 그 시간대 첫 장면에 들어가고 번호가 다시 매겨진다(빈 장면은 지운다).
- 모든 편집은 되돌리기 스냅숏(50단계)을 남긴다. 변경 수 = 적용한 편집 묶음 수(되돌리면 줄고 다시 실행하면 는다).
"""
from __future__ import annotations

import copy
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.ids import new_id

from . import texts

UNDO_LIMIT = 50
STORY_MAX = 120
BEAT_MAX = 40
PLACE_MAX = 16


def bad(message: str, code: str = "INVALID_OP", **details: Any) -> ApiError:
    return ApiError(400, code, message, details)


# ── 만들기 ─────────────────────────────────────────────────

def new_slot(label: str, time: str | None = None, *, ord_: int = 0, is_new: bool = False) -> dict[str, Any]:
    return {"id": new_id("sct"), "ord": ord_, "time": texts.norm_time(time), "label": (label or "").strip() or "새 시간대",
            "is_new": is_new}


def new_role(name: str, *, ord_: int = 0, source: str = "parsed", suggested: bool = False, intro: str = "",
             wants: list[str] | None = None, pains: list[str] | None = None) -> dict[str, Any]:
    n = (name or "").strip()
    return {"id": new_id("scr"), "ord": ord_, "name": n, "initial": texts.initial(n), "intro": intro or "", "wants": list(wants or []),
            "pains": list(pains or []), "suggested": suggested, "source": source}


def new_beat(role_id: str | None, text: str, place: str = "", *, primary: bool = False) -> dict[str, Any]:
    return {"id": new_id("scb"), "role_id": role_id, "text": texts.clip(text, BEAT_MAX * 2), "place": texts.clip(place, PLACE_MAX * 2),
            "primary": primary}


def new_scene(slot_id: str, beats: list[dict[str, Any]], *, ord_in_slot: int = 0, place: str = "", is_new: bool = False,
              zone_ref: dict[str, Any] | None = None, products: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    first_place = place or next((b.get("place") for b in beats if b.get("place")), "")
    return {
        "id": new_id("scs"), "slot_id": slot_id, "ord_in_slot": ord_in_slot, "no": 0, "title": "", "place": first_place,
        "space_key": None, "story": "", "beats": beats, "solutions": [], "products": list(products or []), "characters": [],
        "confirm_tokens": [], "evidence": [], "image": None, "image_request_id": None, "image_stale": None, "image_job": None,
        "locked": False, "status": "waiting", "version": 0, "reason": "", "zone_ref": zone_ref, "is_new": is_new,
        "story_check": False, "plan_solutions": None, "rewriting": False,
    }


# ── 읽기 ──────────────────────────────────────────────────

def slots(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(doc.get("slots") or [], key=lambda s: s.get("ord", 0))


def roles(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(doc.get("roles") or [], key=lambda r: r.get("ord", 0))


def slot_by_id(doc: dict[str, Any], slot_id: str | None) -> dict[str, Any] | None:
    return next((s for s in doc.get("slots") or [] if s["id"] == slot_id), None)


def role_by_id(doc: dict[str, Any], role_id: str | None) -> dict[str, Any] | None:
    return next((r for r in doc.get("roles") or [] if r["id"] == role_id), None)


def role_by_name(doc: dict[str, Any], name: str | None) -> dict[str, Any] | None:
    n = (name or "").strip()
    if not n:
        return None
    hit = next((r for r in doc.get("roles") or [] if r["name"] == n), None)
    if hit:
        return hit
    return next((r for r in doc.get("roles") or [] if n in r["name"] or r["name"] in n), None)


def scene_by_id(doc: dict[str, Any], scene_id: str | None) -> dict[str, Any] | None:
    return next((s for s in doc.get("scenes") or [] if s["id"] == scene_id), None)


def scenes(doc: dict[str, Any]) -> list[dict[str, Any]]:
    order = {s["id"]: s.get("ord", 0) for s in doc.get("slots") or []}
    return sorted(doc.get("scenes") or [], key=lambda sc: (order.get(sc.get("slot_id"), 10_000), sc.get("ord_in_slot", 0)))


def scene_by_no(doc: dict[str, Any], no: int) -> dict[str, Any] | None:
    return next((s for s in doc.get("scenes") or [] if s.get("no") == no), None)


def beat_index(doc: dict[str, Any], beat_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    for sc in doc.get("scenes") or []:
        for b in sc.get("beats") or []:
            if b["id"] == beat_id:
                return sc, b
    return None


def slot_label(slot: dict[str, Any] | None) -> str:
    if not slot:
        return ""
    return texts.join([slot.get("time") or "", slot.get("label") or ""], " ")


def scene_label(doc: dict[str, Any], sc: dict[str, Any]) -> str:
    sl = slot_by_id(doc, sc.get("slot_id"))
    return (sl or {}).get("label") or ""


def scene_time(doc: dict[str, Any], sc: dict[str, Any]) -> str | None:
    sl = slot_by_id(doc, sc.get("slot_id"))
    return (sl or {}).get("time")


def role_scene_nos(doc: dict[str, Any], role_id: str) -> list[dict[str, Any]]:
    out = []
    for sc in scenes(doc):
        if any(b.get("role_id") == role_id for b in sc.get("beats") or []):
            out.append({"no": sc["no"], "is_new": bool(sc.get("is_new"))})
    return out


# ── 정리(번호 · 주 시점 · 빈 장면) ───────────────────────────────

def normalize(doc: dict[str, Any]) -> dict[str, Any]:
    """시간대 · 역할 순서를 0..n 으로, 빈 장면 삭제(생성된 장면은 남김), 장면 번호 · 시간대 안 순서 · 첫 비트 주 시점."""
    sl = slots(doc)
    for i, s in enumerate(sl):
        s["ord"] = i
    doc["slots"] = sl
    rl = roles(doc)
    for i, r in enumerate(rl):
        r["ord"] = i
        r["initial"] = texts.initial(r.get("name") or "")
    doc["roles"] = rl
    slot_ids = {s["id"] for s in sl}
    role_ids = {r["id"] for r in rl}
    kept = []
    for sc in doc.get("scenes") or []:
        if sc.get("slot_id") not in slot_ids:
            continue
        for b in sc.get("beats") or []:
            if b.get("role_id") not in role_ids:
                b["role_id"] = None
        if not sc.get("beats") and not sc.get("story") and not sc.get("title"):
            continue
        kept.append(sc)
    doc["scenes"] = kept
    ordered = scenes(doc)
    # 번호: 시간대 순서 → 시간대 안 순서. 편집 중 새로 만든 장면(「새 장면」)은 자리를 잡을 때까지(settle) 뒤 번호
    regular = [s for s in ordered if not s.get("is_new")]
    fresh = [s for s in ordered if s.get("is_new")]
    for n, sc in enumerate(regular + fresh, start=1):
        sc["no"] = n
    per_slot: dict[str, int] = {}
    for sc in ordered:
        k = per_slot.get(sc["slot_id"], 0)
        sc["ord_in_slot"] = k
        per_slot[sc["slot_id"]] = k + 1
        beats = sc.get("beats") or []
        if beats and not any(b.get("primary") for b in beats):
            beats[0]["primary"] = True
        seen_primary = False
        for b in beats:
            if b.get("primary") and not seen_primary:
                seen_primary = True
            else:
                b["primary"] = False
        if not sc.get("place"):
            sc["place"] = next((b.get("place") for b in beats if b.get("place")), "") or ""
    doc["scenes"] = ordered
    return doc


def settle(doc: dict[str, Any]) -> dict[str, Any]:
    """타임라인 편집을 마치면(SC3 · 생성) 「새 장면」 표시를 풀고 시간 순서대로 번호를 다시 매긴다."""
    for sc in doc.get("scenes") or []:
        sc["is_new"] = False
    return normalize(doc)


def conflicts(doc: dict[str, Any]) -> dict[str, Any]:
    """R2: 같은 시간 충돌(한 시간대에 장면 2개 이상) · 역할 미배정 비트."""
    per: dict[str, int] = {}
    for sc in doc.get("scenes") or []:
        per[sc["slot_id"]] = per.get(sc["slot_id"], 0) + 1
    same_time = sum(1 for v in per.values() if v > 1)
    unassigned = sum(1 for sc in doc.get("scenes") or [] for b in sc.get("beats") or [] if not b.get("role_id"))
    return {"same_time": same_time, "unassigned": unassigned}


# ── 되돌리기 ──────────────────────────────────────────────

_SNAP_KEYS = ("slots", "roles", "scenes", "suggestions")


def snapshot(doc: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy({k: doc.get(k) for k in _SNAP_KEYS})


def push_undo(doc: dict[str, Any]) -> None:
    ed = doc.setdefault("edit", {"undo": [], "redo": [], "changes": 0})
    ed["undo"] = (ed.get("undo") or [])[-(UNDO_LIMIT - 1):] + [snapshot(doc)]
    ed["redo"] = []
    ed["changes"] = int(ed.get("changes") or 0) + 1


def undo(doc: dict[str, Any]) -> bool:
    ed = doc.setdefault("edit", {"undo": [], "redo": [], "changes": 0})
    if not ed.get("undo"):
        return False
    prev = ed["undo"].pop()
    ed.setdefault("redo", []).append(snapshot(doc))
    for k in _SNAP_KEYS:
        doc[k] = prev.get(k)
    ed["changes"] = max(0, int(ed.get("changes") or 0) - 1)
    return True


def redo(doc: dict[str, Any]) -> bool:
    ed = doc.setdefault("edit", {"undo": [], "redo": [], "changes": 0})
    if not ed.get("redo"):
        return False
    nxt = ed["redo"].pop()
    ed.setdefault("undo", []).append(snapshot(doc))
    for k in _SNAP_KEYS:
        doc[k] = nxt.get(k)
    ed["changes"] = int(ed.get("changes") or 0) + 1
    return True


# ── 연산 ──────────────────────────────────────────────────

def _first_scene_in_slot(doc: dict[str, Any], slot_id: str) -> dict[str, Any] | None:
    cands = [s for s in doc.get("scenes") or [] if s["slot_id"] == slot_id]
    cands.sort(key=lambda s: s.get("ord_in_slot", 0))
    return cands[0] if cands else None


def _max_ord_in_slot(doc: dict[str, Any], slot_id: str) -> int:
    return max([s.get("ord_in_slot", 0) for s in doc.get("scenes") or [] if s["slot_id"] == slot_id] or [-1])


def add_beat_to_cell(doc: dict[str, Any], slot_id: str, role_id: str | None, text: str, place: str = "", *,
                     new_scene_: bool = True) -> dict[str, Any]:
    """빈 칸 「+」 · W 추천 「추가」: 새 장면(기본) 또는 그 시간대 첫 장면에 비트."""
    if slot_by_id(doc, slot_id) is None:
        raise bad("시간대를 찾을 수 없어요", slot_id=slot_id)
    beat = new_beat(role_id, text, place)
    target = None if new_scene_ else _first_scene_in_slot(doc, slot_id)
    if target is None:
        beat["primary"] = True
        sc = new_scene(slot_id, [beat], ord_in_slot=_max_ord_in_slot(doc, slot_id) + 1, place=place, is_new=True)
        doc.setdefault("scenes", []).append(sc)
        return sc
    target.setdefault("beats", []).append(beat)
    return target


def apply_op(doc: dict[str, Any], op: dict[str, Any]) -> None:
    kind = op.get("op")
    if kind == "add_slot":
        sl = slots(doc)
        after = op.get("after_slot_id")
        time = texts.norm_time(op.get("time"))
        slot = new_slot(op.get("label") or "새 시간대", time, is_new=True)
        if after:
            idx = next((i for i, s in enumerate(sl) if s["id"] == after), len(sl) - 1)
            sl.insert(idx + 1, slot)
        elif time:
            idx = next((i for i, s in enumerate(sl) if s.get("time") and texts.time_key(s["time"]) > texts.time_key(time)), len(sl))
            sl.insert(idx, slot)
        else:
            sl.append(slot)
        for i, s in enumerate(sl):
            s["ord"] = i
        doc["slots"] = sl
    elif kind == "set_slot":
        s = slot_by_id(doc, op.get("slot_id"))
        if s is None:
            raise bad("시간대를 찾을 수 없어요")
        if "label" in op and op["label"] is not None:
            s["label"] = str(op["label"]).strip() or s["label"]
        if "time" in op:
            s["time"] = texts.norm_time(op.get("time"))
    elif kind == "remove_slot":
        sid = op.get("slot_id")
        doc["slots"] = [s for s in doc.get("slots") or [] if s["id"] != sid]
        doc["scenes"] = [s for s in doc.get("scenes") or [] if s["slot_id"] != sid]
    elif kind == "move_beat":
        hit = beat_index(doc, op.get("beat_id") or "")
        if hit is None:
            raise bad("옮길 장면 카드를 찾을 수 없어요")
        src, beat = hit
        to_slot = op.get("to_slot_id") or src["slot_id"]
        if slot_by_id(doc, to_slot) is None:
            raise bad("놓을 시간대를 찾을 수 없어요")
        to_role = op.get("to_role_id", beat.get("role_id"))
        if to_role is not None and role_by_id(doc, to_role) is None:
            raise bad("놓을 역할을 찾을 수 없어요")
        beat["role_id"] = to_role
        if to_slot == src["slot_id"]:
            return
        src["beats"] = [b for b in src["beats"] if b["id"] != beat["id"]]
        if beat.get("primary") and src["beats"]:
            src["beats"][0]["primary"] = True
        beat["primary"] = False
        target = _first_scene_in_slot(doc, to_slot)
        if target is None:
            beat["primary"] = True
            doc["scenes"].append(new_scene(to_slot, [beat], ord_in_slot=0, place=beat.get("place") or "",
                                           is_new=bool(src.get("is_new"))))
        else:
            target["beats"].append(beat)
        if not src["beats"]:
            doc["scenes"] = [s for s in doc["scenes"] if s["id"] != src["id"]]
    elif kind == "add_beat":
        slot_id = op.get("slot_id")
        text = (op.get("text") or "").strip()
        if not text:
            raise bad("장면 내용을 적어 주세요")
        if op.get("scene_id"):
            sc = scene_by_id(doc, op["scene_id"])
            if sc is None:
                raise bad("장면을 찾을 수 없어요")
            sc["beats"].append(new_beat(op.get("role_id"), text, op.get("place") or ""))
        else:
            add_beat_to_cell(doc, slot_id or "", op.get("role_id"), text, op.get("place") or "",
                             new_scene_=op.get("new_scene", True) is not False)
    elif kind == "set_beat":
        hit = beat_index(doc, op.get("beat_id") or "")
        if hit is None:
            raise bad("장면 카드를 찾을 수 없어요")
        sc, beat = hit
        if op.get("text") is not None:
            beat["text"] = texts.clip(str(op["text"]), BEAT_MAX * 2)
        if op.get("place") is not None:
            beat["place"] = texts.clip(str(op["place"]), PLACE_MAX * 2)
            if beat.get("primary"):
                sc["place"] = beat["place"]
        if "role_id" in op and op["role_id"] is not None:
            if role_by_id(doc, op["role_id"]) is None:
                raise bad("역할을 찾을 수 없어요")
            beat["role_id"] = op["role_id"]
    elif kind == "remove_beat":
        hit = beat_index(doc, op.get("beat_id") or "")
        if hit is None:
            raise bad("장면 카드를 찾을 수 없어요")
        sc, beat = hit
        sc["beats"] = [b for b in sc["beats"] if b["id"] != beat["id"]]
        if not sc["beats"]:
            doc["scenes"] = [s for s in doc["scenes"] if s["id"] != sc["id"]]
    elif kind == "add_role":
        name = (op.get("name") or "").strip()
        if not name:
            raise bad("역할 이름을 적어 주세요")
        if role_by_name(doc, name) and role_by_name(doc, name)["name"] == name:  # type: ignore[index]
            raise ApiError(409, "ROLE_EXISTS", f"「{name}」 역할이 이미 있어요")
        rl = roles(doc)
        rl.append(new_role(name, ord_=len(rl), source=op.get("source") or "user", suggested=bool(op.get("suggested"))))
        doc["roles"] = rl
        sug = doc.setdefault("suggestions", {})
        sug["roles"] = [r for r in sug.get("roles") or [] if r != name]
    elif kind == "set_role":
        r = role_by_id(doc, op.get("role_id"))
        if r is None:
            raise bad("역할을 찾을 수 없어요")
        for k in ("name", "intro"):
            if op.get(k) is not None:
                r[k] = str(op[k]).strip()
        for k in ("wants", "pains"):
            if op.get(k) is not None:
                r[k] = [str(x).strip() for x in op[k] if str(x).strip()]
        r["initial"] = texts.initial(r["name"])
    elif kind == "remove_role":
        rid = op.get("role_id")
        doc["roles"] = [r for r in doc.get("roles") or [] if r["id"] != rid]
        for sc in doc.get("scenes") or []:
            sc["beats"] = [b for b in sc.get("beats") or [] if b.get("role_id") != rid]
    elif kind == "reorder_roles":
        order = list(op.get("role_ids") or [])
        rank = {rid: i for i, rid in enumerate(order)}
        rl = sorted(roles(doc), key=lambda r: (rank.get(r["id"], 10_000), r.get("ord", 0)))
        for i, r in enumerate(rl):
            r["ord"] = i
        doc["roles"] = rl
    elif kind == "split_scene":
        sc = scene_by_id(doc, op.get("scene_id"))
        if sc is None:
            raise bad("나눌 장면을 고르세요", code="SCENE_REQUIRED")
        beats = sc.get("beats") or []
        if len(beats) < 2:
            raise bad("비트가 하나뿐인 장면은 나눌 수 없어요", code="CANNOT_SPLIT")
        cut = (len(beats) + 1) // 2
        keep, move = beats[:cut], beats[cut:]
        sc["beats"] = keep
        for b in move:
            b["primary"] = False
        move[0]["primary"] = True
        for other in doc.get("scenes") or []:
            if other["slot_id"] == sc["slot_id"] and other.get("ord_in_slot", 0) > sc.get("ord_in_slot", 0):
                other["ord_in_slot"] = other.get("ord_in_slot", 0) + 1
        doc["scenes"].append(new_scene(sc["slot_id"], move, ord_in_slot=sc.get("ord_in_slot", 0) + 1, is_new=True))
    elif kind == "merge_same_time":
        by_slot: dict[str, list[dict[str, Any]]] = {}
        for sc in scenes(doc):
            by_slot.setdefault(sc["slot_id"], []).append(sc)
        keep_ids = set()
        for group in by_slot.values():
            head = group[0]
            keep_ids.add(head["id"])
            for other in group[1:]:
                for b in other.get("beats") or []:
                    b["primary"] = False
                    head["beats"].append(b)
                head["products"] = _merge_products(head.get("products") or [], other.get("products") or [])
        doc["scenes"] = [s for s in doc.get("scenes") or [] if s["id"] in keep_ids]
    elif kind == "prune_empty_slots":
        used = {s["slot_id"] for s in doc.get("scenes") or [] if s.get("beats")}
        doc["slots"] = [s for s in doc.get("slots") or [] if s["id"] in used]
    elif kind == "accept_suggestion":
        sug = (doc.get("suggestions") or {}).get("scene")
        if not sug:
            raise bad("추천 장면이 없어요")
        add_beat_to_cell(doc, sug["slot_id"], sug.get("role_id"), sug["text"], sug.get("place") or "")
        _dismiss(doc, sug)
    elif kind == "dismiss_suggestion":
        sug = (doc.get("suggestions") or {}).get("scene")
        if sug:
            _dismiss(doc, sug)
    else:
        raise bad(f"모르는 편집이에요: {kind}")


def _dismiss(doc: dict[str, Any], sug: dict[str, Any]) -> None:
    s = doc.setdefault("suggestions", {})
    s["dismissed"] = list(dict.fromkeys([*(s.get("dismissed") or []), sug.get("text") or ""]))
    s["scene"] = None


def _merge_products(a: list[dict[str, Any]], b: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {(p.get("family_id") or p.get("label")) for p in a}
    out = list(a)
    for p in b:
        k = p.get("family_id") or p.get("label")
        if k not in seen:
            out.append(p)
            seen.add(k)
    return out


def apply_ops(doc: dict[str, Any], ops: list[dict[str, Any]]) -> None:
    push_undo(doc)
    try:
        for op in ops:
            apply_op(doc, op)
    except ApiError:
        undo(doc)
        doc.setdefault("edit", {})["redo"] = []
        raise
    normalize(doc)


# ── 텍스트로 보기 ────────────────────────────────────────────

def to_text(doc: dict[str, Any]) -> str:
    """시간대마다 한 줄: 「07:00 오픈. 점장: 아침 메뉴로 켜진 메뉴보드 확인(카운터).」(시각 없으면 라벨부터)."""
    lines = []
    for sl in slots(doc):
        parts = []
        for sc in [s for s in scenes(doc) if s["slot_id"] == sl["id"]]:
            for b in sc.get("beats") or []:
                r = role_by_id(doc, b.get("role_id"))
                who = f"{r['name']}: " if r else ""
                place = f"({b['place']})" if b.get("place") else ""
                parts.append(f"{who}{b['text']}{place}.")
        head = texts.join([sl.get("time") or "", f"{sl['label']}."], " ")
        lines.append(texts.join([head, *parts], " "))
    return "\n".join(lines)


# ── 화면용 ────────────────────────────────────────────────

def view(doc: dict[str, Any]) -> dict[str, Any]:
    """SC2E 응답: 시간대 · 역할(장면 수 · 장면 목록) · 장면(비트 라벨) · 추천 · 변경 수."""
    sc_list = scenes(doc)
    role_list = []
    for r in roles(doc):
        nos = role_scene_nos(doc, r["id"])
        role_list.append({**{k: r.get(k) for k in ("id", "ord", "name", "initial", "intro", "wants", "pains", "suggested", "source")},
                          "scene_count": len(nos), "scene_refs": nos, "rewriting": bool(r.get("rewriting"))})
    scene_list = []
    for sc in sc_list:
        beats = []
        for b in sc.get("beats") or []:
            r = role_by_id(doc, b.get("role_id"))
            label = ("새 장면" if sc.get("is_new") else f"장면 {sc['no']}") if b.get("primary") else \
                f"{'새 장면' if sc.get('is_new') else '장면 ' + str(sc['no'])} · {texts.short_role(r['name']) if r else '역할 없음'} 시점"
            beats.append({**b, "label": label})
        scene_list.append({"id": sc["id"], "no": sc["no"], "slot_id": sc["slot_id"], "ord_in_slot": sc.get("ord_in_slot", 0),
                           "place": sc.get("place") or "", "is_new": bool(sc.get("is_new")), "beats": beats,
                           "title": sc.get("title") or "", "status": sc.get("status") or "waiting"})
    sug = doc.get("suggestions") or {}
    ed = doc.get("edit") or {}
    return {
        "slots": [{k: s.get(k) for k in ("id", "ord", "time", "label", "is_new")} for s in slots(doc)],
        "roles": role_list,
        "scenes": scene_list,
        "suggestions": {"scene": sug.get("scene"), "roles": list(sug.get("roles") or [])},
        "changes_count": int(ed.get("changes") or 0),
        "can_undo": bool(ed.get("undo")),
        "can_redo": bool(ed.get("redo")),
    }
