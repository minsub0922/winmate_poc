"""배치안(08-birdseye §4.7 · §4.8 · §6.4) — 생성(의도 LLM + 엔진 + 자동 조정) · 보기 · 동기 검증 · 편집 세션 · 말로 수정."""
from __future__ import annotations

import copy
import re
import time
from typing import Any

from pydantic import BaseModel, Field

from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso

from . import config, kbapi, llm
from . import furniture as F
from . import service as svc
from . import space as S
from . import text as T
from .engine import apply_ops, autofix, generate, merge_fixed, merged_params, validate
from .engine.validate import _assign_ids
from .repo import repo


class Intent(BaseModel):
    item: str = Field(description="p1 · p2 · f1 … (목록의 키)")
    anchor: str = Field(description="window:o1 · wall:w3 · column · faces:p2 · near:p1 · entrance · window_area · free")
    qty: int | None = None
    at_label: str | None = Field(None, description="수량표 위치 라벨(10자 이내, 「쇼윈도 창면」)")


class Intents(BaseModel):
    intents: list[Intent] = Field(default_factory=list)


class LOp(BaseModel):
    op: str = Field(description="move · set_qty · remove · rotate · set_size · center")
    target: str = Field(description="항목 이름(목록의 이름 그대로) 또는 키")
    dx: float | None = None
    dy: float | None = None
    qty: int | None = None
    deg: float | None = None
    size: str | None = None


class LOps(BaseModel):
    ops: list[LOp] = Field(default_factory=list)


async def params() -> dict[str, Any]:
    rules = await kbapi.placement_rules()
    return merged_params(config.rules(), rules)


def _engine_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for p in products:
        out.append({k: p.get(k) for k in ("id", "family_id", "model_code", "ref", "display_name", "short", "size_options", "chosen_size",
                                          "dims_m", "dims_by_size", "dims_source", "diag_inch", "category", "role", "mount_default",
                                          "order", "models_by_size", "qty_user")})
    return out


def _intent_prompt(model: dict[str, Any], products: list[dict[str, Any]], furniture: list[dict[str, Any]], description: str) -> str:
    walls = "; ".join(f"{w['id']}={w.get('label') or '벽'}" for w in model.get("walls", []))
    wins = "; ".join(f"{o['id']}={o.get('label') or '창'}" for o in model.get("openings", []) if o["kind"] == "window")
    cols = ", ".join(c["id"] for c in model.get("columns", []))
    items = [f"p{i}: {p.get('display_name')} ({p.get('role')})" for i, p in enumerate(products, start=1)]
    items += [f"f{i}: {f.get('name')}" for i, f in enumerate(furniture, start=1)]
    return (f"공간 설명: {description[:400]}\n벽: {walls}\n창: {wins or '없음'}\n기둥: {cols or '없음'}\n항목:\n" + "\n".join(items) +
            "\n각 항목(키 p1 · f1 … 또는 role:<역할>)의 앵커를 window:<창id> · wall:<벽id> · column · faces:<p키> · near:<p키> · entrance · window_area · free 중에서 고르고, "
            "제품 수량(qty)과 수량표 위치 라벨(at_label, 10자 이내)을 적는다. 좌표는 적지 않는다.")


async def generate_layout(be_id: str, *, none: bool = False) -> dict[str, Any]:
    b = await svc.get(be_id)
    model = await svc.space_model(be_id)
    if model is None:
        raise ApiError(409, "SPACE_NOT_READY", "공간 입력을 먼저 마쳐 주세요")
    products = _engine_products(await svc.products(be_id))
    furn = [] if none or b.get("furniture_none") else F.engine_furniture(await svc.furniture(be_id))
    prm = await params()
    intents = None
    path_note = "intent:rules"
    try:
        res = await llm.json_task("be.layout_intent", _intent_prompt(model, products, furn, b.get("description") or ""), Intents,
                                  confidential=True)
        if res and res.get("intents"):
            intents = res["intents"]
    except llm.ModelBlocked:
        intents = None
    layout = generate(model, products, furn, intents=intents, params=prm, version=0)
    if intents:
        path_note = (layout.get("meta_paths") or [path_note])[0]
    return await save_layout(be_id, layout, created_by="engine", note=path_note)


async def save_layout(be_id: str, layout: dict[str, Any], *, created_by: str, parent: int | None = None,
                      statuses: dict[str, str] | None = None, note: str | None = None) -> dict[str, Any]:
    b = await svc.get(be_id)
    prev = int(b.get("layout_version") or 0)
    v = prev + 1
    lay = copy.deepcopy(layout)
    lay["version"] = v
    lay["created_by"] = created_by
    lay["parent_version"] = parent if parent is not None else (prev or None)
    lay["created_at"] = now_iso()
    if note:
        lay.setdefault("meta_paths", [])
        if note not in lay["meta_paths"]:
            lay["meta_paths"].append(note)
    await repo().put("layouts", f"{be_id}:{v}", {"birdseye_id": be_id, "v": v, "layout": lay, "statuses": statuses or {}})
    changes: dict[str, Any] = {"layout_version": v}
    if int(b.get("step") or 1) < 4:
        changes["step"] = 4
    await svc.touch(be_id, **changes)
    if prev:
        # 레이아웃이 바뀌면 이전 레이아웃으로 만든 컷은 stale(「배치 변경 전」)
        for c in await svc.cuts(be_id):
            if int(c.get("layout_version") or 0) < v and not c.get("stale") and c["status"] in ("done", "check", "draft"):
                await repo().patch("cuts", c["id"], {"stale": True})
    # 수량표 메모(전원) — 레이아웃 메모를 memos 에 반영
    await svc.index(be_id)
    return lay


async def get_layout(be_id: str, version: int | None = None) -> dict[str, Any] | None:
    doc = await svc.layout_doc(be_id, version)
    return doc["layout"] if doc else None


def plan_geometry(model: dict[str, Any], layout: dict[str, Any] | None = None) -> dict[str, Any]:
    minx, miny, maxx, maxy = S.bbox_of(model)
    return {
        "width_m": round(maxx - minx, 2), "height_m": round(maxy - miny, 2), "rooms": model.get("rooms", []),
        "walls": model.get("walls", []), "openings": model.get("openings", []), "columns": model.get("columns", []),
        "cores": model.get("cores", []),
        "power_points": (layout or {}).get("power_points") if layout and layout.get("power_points") is not None else model.get("power_points", []),
        "area_label": S.area_label_short(model), "window_label": S.window_label(model),
    }


def _clean_warnings(ws: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for w in ws:
        x = {k: w.get(k) for k in ("id", "n", "kind", "title_ko", "rule_id", "expr", "params", "param_status", "tooltip", "message_ko",
                                   "subjects", "fixes", "actions", "status", "key", "marker", "value")}
        x["params"] = x.get("params") or {}
        x["fixes"] = x.get("fixes") or []
        x["subjects"] = x.get("subjects") or []
        x["actions"] = x.get("actions") or []
        out.append(x)
    return out


def clean_layout(lay: dict[str, Any]) -> dict[str, Any]:
    out = {k: lay.get(k) for k in ("version", "items", "groups", "warnings", "assumptions", "memos", "power_points", "engine_version",
                                   "created_by", "parent_version", "created_at")}
    out["items"] = [_clean_item(it) for it in lay.get("items", [])]
    out["groups"] = [_clean_group(g) for g in lay.get("groups", [])]
    out["warnings"] = _clean_warnings(lay.get("warnings", []))
    out["assumptions"] = lay.get("assumptions") or []
    out["memos"] = lay.get("memos") or []
    out["power_points"] = lay.get("power_points") or []
    out["engine_version"] = lay.get("engine_version") or "be-engine/1"
    out["created_by"] = lay.get("created_by") or "engine"
    return out


ITEM_KEYS = ("id", "kind", "ref", "group_id", "label", "short", "tiny", "x", "y", "rot_deg", "w", "d", "h", "z", "mount", "anchor",
             "qty_in_group", "qty_source", "rule_id", "faces", "seats", "seat_points", "locked", "unplaced", "role", "diag_inch", "parts")
GROUP_KEYS = ("id", "kind", "ref", "label", "plan_label", "at_label", "anchor_label", "family_id", "model_code", "qty", "qty_source",
              "rule_id", "item_ids", "short", "tiny", "size")


def _clean_item(it: dict[str, Any]) -> dict[str, Any]:
    x = {k: it.get(k) for k in ITEM_KEYS}
    x["anchor"] = x.get("anchor") or {"type": "free", "target": None, "label": ""}
    x["seat_points"] = x.get("seat_points") or []
    x["parts"] = x.get("parts") or []
    x["qty_source"] = x.get("qty_source") or "default"
    x["mount"] = x.get("mount") or "floor"
    x["short"] = x.get("short") or ""
    x["tiny"] = x.get("tiny") or ""
    x["seats"] = int(x.get("seats") or 0)
    x["qty_in_group"] = int(x.get("qty_in_group") or 1)
    x["locked"] = bool(x.get("locked"))
    x["unplaced"] = bool(x.get("unplaced"))
    return x


def _clean_group(g: dict[str, Any]) -> dict[str, Any]:
    x = {k: g.get(k) for k in GROUP_KEYS}
    x["plan_label"] = x.get("plan_label") or x.get("label") or ""
    x["at_label"] = x.get("at_label") or ""
    x["anchor_label"] = x.get("anchor_label") or ""
    x["qty_source"] = x.get("qty_source") or "default"
    x["item_ids"] = x.get("item_ids") or []
    x["short"] = x.get("short") or ""
    x["tiny"] = x.get("tiny") or ""
    x["qty"] = int(x.get("qty") or 1)
    return x


W_LAYOUT = "배치안입니다. 평면도 위의 제품·가구는 드래그해서 옮길 수 있고, 인테리어 톤을 고르면 3D 생성 시 마감재와 조명에 반영됩니다."
W_LAYOUT_RUNNING = "배치안을 만들고 있어요"
W_EDIT = "직접 수정 모드입니다. 제품과 가구를 끌어서 옮기면 시야각 · 동선 · 전원 위치를 바로 다시 확인하고, 문제가 생긴 곳을 번호로 표시합니다."


async def layout_view(be_id: str, version: int | None = None, *, running: bool = False, job_id: str | None = None) -> dict[str, Any]:
    b = await svc.get(be_id)
    model = await svc.space_model(be_id)
    lay = await get_layout(be_id, version)
    overlays: dict[str, Any] = {}
    if lay and model:
        res = validate(model, lay, params=await params(), statuses=_statuses(lay))
        overlays = res["overlays"]
    open_w = sum(1 for w in (lay or {}).get("warnings", []) if w.get("status") == "open")
    return {
        "layout": clean_layout(lay) if lay else None, "plan": plan_geometry(model, lay) if model else None, "overlays": overlays or {},
        "w_message": W_LAYOUT_RUNNING if running or not lay else W_LAYOUT, "open_warnings": open_w, "running": running, "job_id": job_id,
        "tone": b.get("tone", "warm_wood"), "default_view": b.get("default_view", "aerial45"),
    }


def _statuses(lay: dict[str, Any]) -> dict[str, str]:
    return {w["key"]: w["status"] for w in lay.get("warnings", []) if w.get("status") in ("ignored", "memo", "fixed")}


async def validate_ops(be_id: str, base_version: int | None, ops: list[dict[str, Any]]) -> dict[str, Any]:
    t0 = time.perf_counter()
    model = await svc.space_model(be_id)
    base = await get_layout(be_id, base_version)
    if model is None or base is None:
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
    prm = await params()
    cur = apply_ops(model, base, ops, params=prm) if ops else base
    res = validate(model, cur, params=prm, base=base, statuses=_statuses(base))
    return {"items": [_clean_item(it) for it in cur["items"]], "groups": [_clean_group(g) for g in cur["groups"]],
            "warnings": _clean_warnings(res["warnings"]), "assumptions": cur.get("assumptions") or [], "overlays": res["overlays"],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1)}


# ── 편집 세션(BE4E) ─────────────────────────────────────

async def create_session(be_id: str) -> dict[str, Any]:
    b = await svc.get(be_id)
    v = int(b.get("layout_version") or 0)
    if not v:
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
    base = await get_layout(be_id, v)
    sid = new_id("bes")
    await repo().put("sessions", sid, {"birdseye_id": be_id, "base_version": v, "actions": [], "cursor": 0, "status": "open",
                                       "statuses": _statuses(base or {}), "memos": list((base or {}).get("memos") or []),
                                       "extra_power": []})
    return {"session_id": sid, "base_version": v}


async def _session(sid: str) -> dict[str, Any]:
    s = await repo().get("sessions", sid)
    if s is None:
        raise not_found("편집 세션", sid)
    return s


def _flat(actions: list[list[dict[str, Any]]], cursor: int) -> list[dict[str, Any]]:
    out = []
    for a in actions[:cursor]:
        out.extend(a)
    return out


async def _current(s: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    model = await svc.space_model(s["birdseye_id"])
    base = await get_layout(s["birdseye_id"], s["base_version"])
    if model is None or base is None:
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
    prm = await params()
    cur = apply_ops(model, base, _flat(s["actions"], s["cursor"]), params=prm)
    cur["memos"] = list(s.get("memos") or [])
    return model, base, cur, prm


async def session_view(sid: str) -> dict[str, Any]:
    s = await _session(sid)
    model, base, cur, prm = await _current(s)
    res = validate(model, cur, params=prm, base=base, statuses=s.get("statuses") or {})
    warnings = merge_fixed(res["warnings"], s.get("fixed_warnings") or [], s.get("statuses") or {})
    moves = []
    base_by = {it["id"]: it for it in base["items"]}
    for it in cur["items"]:
        b0 = base_by.get(it["id"])
        if b0 is None:
            continue
        dx, dy = round(it["x"] - b0["x"], 2), round(it["y"] - b0["y"], 2)
        if abs(dx) >= 0.05 or abs(dy) >= 0.05:
            moves.append({"item_id": it["id"], "group_id": it["group_id"], "from_x": b0["x"], "from_y": b0["y"], "dx": dx, "dy": dy,
                          "label_ko": T.move_label(dx, dy), "w": b0["w"], "d": b0["d"], "rot_deg": b0["rot_deg"]})
    lay = clean_layout({**cur, "warnings": warnings})
    return {
        "session_id": sid, "birdseye_id": s["birdseye_id"], "base_version": s["base_version"], "status": s["status"], "layout": lay,
        "plan": plan_geometry(model, cur), "warnings": _clean_warnings(warnings),
        "open_warnings": sum(1 for w in warnings if w["status"] == "open"), "changes_count": int(s["cursor"]),
        "can_undo": s["cursor"] > 0, "can_redo": s["cursor"] < len(s["actions"]), "moves": moves, "overlays": res["overlays"],
    }


async def session_ops(sid: str, ops: list[dict[str, Any]], undo: bool = False, redo: bool = False) -> dict[str, Any]:
    s = await _session(sid)
    if s["status"] != "open":
        raise ApiError(409, "SESSION_CLOSED", "이미 끝난 편집 세션이에요")
    if undo and s["cursor"] > 0:
        s["cursor"] -= 1
    elif redo and s["cursor"] < len(s["actions"]):
        s["cursor"] += 1
    elif ops:
        s["actions"] = s["actions"][: s["cursor"]] + [ops]
        s["cursor"] = len(s["actions"])
    await repo().put("sessions", sid, s)
    return await session_view(sid)


async def warning_action(sid: str, wid: str, action: str, fix_id: str | None, pos: list[float] | None) -> dict[str, Any]:
    s = await _session(sid)
    view = await session_view(sid)
    w = next((x for x in view["warnings"] if x["id"] == wid or x["key"] == wid), None)
    if w is None:
        raise not_found("경고", wid)
    statuses = dict(s.get("statuses") or {})
    if action == "fix":
        fx = next((f for f in w["fixes"] if f["id"] == (fix_id or "f1")), None)
        if fx is None:
            raise ApiError(409, "NO_FIX", "이 경고에는 자동 수정안이 없어요")
        s["actions"] = s["actions"][: s["cursor"]] + [fx["ops"]]
        s["cursor"] = len(s["actions"])
        statuses[w["key"]] = "fixed"
        s["fixed_warnings"] = (s.get("fixed_warnings") or []) + [w]
    elif action == "ignore":
        statuses[w["key"]] = "ignored"
    elif action == "memo":
        statuses[w["key"]] = "memo"
        memo = _memo_text(w)
        s["memos"] = list(dict.fromkeys((s.get("memos") or []) + [memo]))
        await repo().put("memos", new_id("bem"), {"birdseye_id": s["birdseye_id"], "kind": "power", "text": memo, "ref": w["key"]})
    elif action == "add_power":
        if not pos or len(pos) != 2:
            raise ApiError(400, "INVALID_ARGUMENT", "콘센트 위치(pos)를 주세요")
        s["actions"] = s["actions"][: s["cursor"]] + [[{"op": "add_power", "pos": pos}]]
        s["cursor"] = len(s["actions"])
    s["statuses"] = statuses
    await repo().put("sessions", sid, s)
    return await session_view(sid)


def _memo_text(w: dict[str, Any]) -> str:
    msg = w.get("message_ko", "")
    subject = msg.split("에서 가까운")[0].split(" 근처 전원")[0]
    return f"{subject} · {config.rules()['power'].get('memo_text', '바닥 배선 필요')}"


async def session_autofix(sid: str) -> dict[str, Any]:
    """「경고 모두 자동 조정」 — 시야각 · 동선은 첫 수정안을 차례로(새 경고가 생기면 건너뜀), 전원은 「메모로 남기기」."""
    s = await _session(sid)
    if s["status"] != "open":
        raise ApiError(409, "SESSION_CLOSED", "이미 끝난 편집 세션이에요")
    model, base, cur, prm = await _current(s)
    view0 = await session_view(sid)
    fixed, statuses = autofix(model, {**cur, "warnings": view0["warnings"]}, params=prm, base=base, statuses=s.get("statuses") or {},
                              include_power=True)
    # 자동 조정으로 바뀐 좌표 → 한 번의 연산 묶음(되돌리기 단위)
    cur_by = {it["id"]: it for it in cur["items"]}
    ops: list[dict[str, Any]] = []
    for it in fixed["items"]:
        c0 = cur_by.get(it["id"])
        if c0 and (abs(it["x"] - c0["x"]) > 1e-6 or abs(it["y"] - c0["y"]) > 1e-6):
            ops.append({"op": "move", "item": it["id"], "dx": round(it["x"] - c0["x"], 2), "dy": round(it["y"] - c0["y"], 2)})
    if ops:
        s["actions"] = s["actions"][: s["cursor"]] + [ops]
        s["cursor"] = len(s["actions"])
    memos = list(s.get("memos") or [])
    for m in fixed.get("memos") or []:
        if m not in memos:
            memos.append(m)
            await repo().put("memos", new_id("bem"), {"birdseye_id": s["birdseye_id"], "kind": "power", "text": m, "ref": None})
    done_keys = {w.get("key") for w in s.get("fixed_warnings") or []}
    newly = [w for w in view0["warnings"] if statuses.get(w["key"]) == "fixed" and w["key"] not in done_keys]
    s["statuses"] = statuses
    s["memos"] = memos
    s["fixed_warnings"] = (s.get("fixed_warnings") or []) + newly
    await repo().put("sessions", sid, s)
    return await session_view(sid)


async def commit(sid: str) -> dict[str, Any]:
    s = await _session(sid)
    if s["status"] != "open":
        raise ApiError(409, "SESSION_CLOSED", "이미 끝난 편집 세션이에요")
    view = await session_view(sid)
    n = int(s["cursor"])
    b = await svc.get(s["birdseye_id"])
    if n == 0 and not (set((s.get("statuses") or {}).items()) - set(_statuses(await get_layout(s["birdseye_id"], s["base_version"]) or {}).items())):
        await repo().patch("sessions", sid, {"status": "committed"})
        return {"layout_version": int(b.get("layout_version") or 0), "changes_count": 0}
    _model, _base, cur, _prm = await _current(s)
    cur["warnings"] = view["warnings"]
    lay = await save_layout(s["birdseye_id"], cur, created_by="user", parent=s["base_version"], statuses=s.get("statuses") or {})
    await repo().patch("sessions", sid, {"status": "committed", "committed_version": lay["version"]})
    return {"layout_version": lay["version"], "changes_count": n}


async def discard(sid: str) -> dict[str, Any]:
    s = await _session(sid)
    await repo().patch("sessions", sid, {"status": "discarded"})
    b = await svc.get(s["birdseye_id"])
    return {"layout_version": int(b.get("layout_version") or 0), "changes_count": 0}


# ── 말로 수정 ───────────────────────────────────────────

def _targets_text(lay: dict[str, Any]) -> str:
    return "\n".join(f"- {g['id']}: {g.get('label')} ({g.get('kind')})" for g in lay.get("groups", []))


def resolve_target(lay: dict[str, Any], target: str) -> str | None:
    t = (target or "").strip()
    if not t:
        return None
    ids = {g["id"] for g in lay.get("groups", [])} | {it["id"] for it in lay.get("items", [])}
    if t in ids:
        return t
    tn = t.replace(" ", "").lower()
    best = None
    for g in lay.get("groups", []):
        for name in (g.get("label"), g.get("short"), g.get("tiny"), g.get("plan_label")):
            nn = (name or "").replace(" ", "").lower()
            if not nn:
                continue
            if nn == tn:
                return g["id"]
            if (tn in nn or nn in tn) and best is None:
                best = g["id"]
    return best


def to_engine_ops(lay: dict[str, Any], lops: list[dict[str, Any]], model: dict[str, Any]) -> list[dict[str, Any]]:
    ops = []
    minx, miny, maxx, maxy = S.bbox_of(model)
    for o in lops:
        gid = resolve_target(lay, o.get("target") or "")
        if not gid:
            continue
        kind = o.get("op")
        if kind == "move":
            ops.append({"op": "move", "item": gid, "dx": float(o.get("dx") or 0), "dy": float(o.get("dy") or 0)})
        elif kind == "set_qty" and o.get("qty"):
            ops.append({"op": "set_qty", "group": gid, "qty": int(o["qty"])})
        elif kind == "remove":
            ops.append({"op": "remove", "item": gid})
        elif kind == "rotate":
            ops.append({"op": "rotate", "item": gid, "deg": float(o.get("deg") or 90)})
        elif kind == "set_size" and o.get("size"):
            ops.append({"op": "set_size", "group": gid, "size": str(o["size"])})
        elif kind == "center":
            items = [it for it in lay["items"] if it["group_id"] == gid]
            if items:
                cx = sum(it["x"] for it in items) / len(items)
                ops.append({"op": "move", "item": gid, "dx": round((minx + maxx) / 2 - cx, 2), "dy": 0.0})
    return ops


_QTY_RE = re.compile(r"([가-힣A-Za-z0-9 ]+?)(?:를|을)?\s*(\d+)\s*(?:열|대|개)로")
_MOVE_RE = re.compile(r"([가-힣A-Za-z0-9 ]+?)(?:를|을)?\s*(위|아래|왼쪽|오른쪽)으?로\s*(\d+(?:\.\d+)?)\s*m")


def regex_layout_ops(text: str) -> list[dict[str, Any]]:
    out = []
    for m in _QTY_RE.finditer(text):
        out.append({"op": "set_qty", "target": m.group(1).strip(), "qty": int(m.group(2))})
    for m in _MOVE_RE.finditer(text):
        d = float(m.group(3))
        dx, dy = {"위": (0, -d), "아래": (0, d), "왼쪽": (-d, 0), "오른쪽": (d, 0)}[m.group(2)]
        out.append({"op": "move", "target": m.group(1).strip(), "dx": dx, "dy": dy})
    if "가운데" in text:
        m = re.search(r"([가-힣A-Za-z ]+?)(?:를|을)?\s*(?:다시\s*)?가운데", text)
        if m:
            out.append({"op": "center", "target": m.group(1).strip()})
    return out


async def interpret_ops(be_id: str, text: str, lay: dict[str, Any], model: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    prompt = (f"배치 항목:\n{_targets_text(lay)}\n요청: {text}\n"
              "요청을 연산 목록으로 바꾼다. op 는 move(dx, dy m · 화면 기준 위 = −y) · set_qty(qty) · remove · rotate(deg) · set_size(size) · "
              "center 중 하나, target 은 항목 이름 그대로.")
    path = "ops:llm"
    try:
        res = await llm.json_task("be.layout_ops", prompt, LOps, confidential=True)
    except llm.ModelBlocked:
        res = None
    lops = (res or {}).get("ops") or []
    if not lops:
        lops = regex_layout_ops(text)
        path = "ops:regex"
    return to_engine_ops(lay, lops, model), path


async def nl_edit(be_id: str, text: str, session_id: str | None) -> dict[str, Any]:
    model = await svc.space_model(be_id)
    if session_id:
        s = await _session(session_id)
        _m, _b, cur, _p = await _current(s)
        ops, path = await interpret_ops(be_id, text, cur, model or {})
        if ops:
            await session_ops(session_id, ops)
        return {"session_id": session_id, "ops": ops, "path": path}
    lay = await get_layout(be_id)
    if lay is None or model is None:
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
    ops, path = await interpret_ops(be_id, text, lay, model)
    if not ops:
        return {"layout_version": lay["version"], "ops": [], "path": path}
    saved = await apply_and_save(be_id, ops, created_by="nl_edit", note=path)
    return {"layout_version": saved["version"], "ops": ops, "path": path}


async def apply_and_save(be_id: str, ops: list[dict[str, Any]], *, created_by: str, note: str | None = None) -> dict[str, Any]:
    """현재 레이아웃에 연산을 적용 · 검증해 새 레이아웃 버전으로 저장(이전 컷은 stale)."""
    model = await svc.space_model(be_id)
    lay = await get_layout(be_id)
    if lay is None or model is None:
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
    prm = await params()
    new = apply_ops(model, lay, ops, params=prm)
    st = _statuses(lay)
    res = validate(model, new, params=prm, base=lay, statuses=st)
    new["warnings"] = merge_fixed(res["warnings"], lay.get("warnings") or [], st)
    _assign_ids(new["warnings"])
    return await save_layout(be_id, new, created_by=created_by, parent=lay["version"], statuses=st, note=note)
