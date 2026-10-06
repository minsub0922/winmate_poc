"""조감도 작업(08-birdseye §4.1 · §5.1 · §5.4 · §6.1) — 만들기 · 읽기 · 고치기 · 목록 행 · 경로 · 상태 · workspace 색인 ·
복제 · 저장(버전) · 되살리기 · 지우기 · 쓰인 곳(usages) · 변경 감지(version)."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import register_item, unregister_item

from . import config
from . import text as T
from .repo import repo

log = logging.getLogger("winmate.birdseye.service")

STEP_ROUTE = {1: "space", 2: "products", 3: "furniture", 4: "layout", 5: "result"}


def uid() -> str:
    return current_user().id


# ── 읽기 ─────────────────────────────────────────────────

async def get(be_id: str) -> dict[str, Any]:
    doc = await repo().get("birdseyes", be_id)
    if doc is None or doc.get("deleted_at"):
        raise not_found("조감도 작업", be_id)
    return doc


async def space_model(be_id: str) -> dict[str, Any] | None:
    doc = await repo().get("space", be_id)
    return doc.get("model") if doc else None


async def layout_doc(be_id: str, version: int | None = None) -> dict[str, Any] | None:
    b = await get(be_id)
    v = version or b.get("layout_version") or 0
    if not v:
        return None
    return await repo().get("layouts", f"{be_id}:{v}")


async def products(be_id: str) -> list[dict[str, Any]]:
    items = await repo().all("products", where={"birdseye_id": be_id}, order_by="created_at")
    return sorted(items, key=lambda p: (p.get("order", 0), p["created_at"]))


async def furniture(be_id: str, *, selected_only: bool = False) -> list[dict[str, Any]]:
    items = await repo().all("furniture", where={"birdseye_id": be_id}, order_by="created_at")
    items = sorted(items, key=lambda f: (f.get("order", 0), f["created_at"]))
    return [f for f in items if f.get("selected")] if selected_only else items


async def cuts(be_id: str) -> list[dict[str, Any]]:
    items = await repo().all("cuts", where={"birdseye_id": be_id}, order_by="created_at")
    return sorted(items, key=lambda c: (c.get("queue_order", 0), c["created_at"]))


async def zones(be_id: str, *, include_all: bool = False) -> list[dict[str, Any]]:
    items = await repo().all("zones", where={"birdseye_id": be_id}, order_by="created_at")
    items = sorted(items, key=lambda z: (z.get("n") or 999, z["created_at"]))
    return items if include_all else [z for z in items if z.get("status") == "active"]


async def usages(be_id: str) -> list[dict[str, Any]]:
    return await repo().all("usages", where={"birdseye_id": be_id}, order_by="created_at")


# ── 만들기 · 고치기 ──────────────────────────────────────

def default_title(chip: str | None, description: str | None) -> str:
    desc = (description or "").strip()
    if desc:
        first = desc.splitlines()[0]
        head = first.split(".")[0].split(",")[0].strip()
        if head:
            return T.clip(head, 40)
    return f"새 조감도 · {config.chip_info(chip)['space_label']}"


async def create(body: dict[str, Any]) -> dict[str, Any]:
    user = current_user()
    be_id = new_id("be")
    chip = body.get("space_chip") or "store_lobby"
    info = config.chip_info(chip)
    prefill = body.get("prefill") or {}
    pre_products = []
    for p in prefill.get("products") or []:
        if isinstance(p, str):
            pre_products.append({"family_id": p, "model_code": None, "label": None, "qty": None})
        elif isinstance(p, dict):
            pre_products.append({k: p.get(k) for k in ("family_id", "model_code", "label", "qty")})
    origin = body.get("origin")
    desc = body.get("description") or ""
    doc = {
        "owner": user.id, "owner_name": user.name, "project_id": body.get("project_id"),
        "customer_name": body.get("customer_name"), "title": body.get("title") or default_title(chip, desc),
        "space_label": info["space_label"], "space_chip": chip, "space_types": list(info["space_types"]),
        "description": desc, "area_input_pyeong": body.get("area_pyeong"), "ceiling_input_m": body.get("ceiling_m"),
        "inputs": {"description": bool(desc.strip()), "plan_file_ids": [], "photo_count": 0},
        "step": 1, "status": "in_progress", "status_reason": None, "check_route": None, "tone": "warm_wood",
        "default_view": "aerial45", "save_version": 1, "saved": False, "layout_version": 0, "primary_cut_id": None,
        "shared_scope": "private", "shared_label": None, "cloned_from": None, "origin": origin,
        "zone_layout": "ZP-A", "reference_image": None, "prefill_products": pre_products, "analyzing_job_id": None,
        "deleted_at": None, "recommendations": None, "furniture_none": False,
    }
    if prefill.get("reference_image_version"):
        doc["reference_image"] = {"version_id": prefill["reference_image_version"], "url": None, "thumb_url": None, "label": "참조 이미지"}
    saved = await repo().put("birdseyes", be_id, doc)
    if pre_products:
        from . import products as P

        try:
            await P.put_products(be_id, [{"family_id": p.get("family_id"), "model_code": p.get("model_code"), "label": p.get("label")}
                                         for p in pre_products if p.get("family_id") or p.get("model_code")])
        except Exception as exc:  # noqa: BLE001 — 미리 채우기 실패는 작업 생성을 막지 않는다
            log.warning("prefill products 실패: %s", exc)
    if doc["reference_image"]:
        await _fill_reference(be_id)
    await index(be_id)
    return await get(saved["id"])


async def _fill_reference(be_id: str) -> None:
    from winmate_common.client import ServiceClient

    b = await get(be_id)
    ref = b.get("reference_image") or {}
    try:
        v = await ServiceClient("image").get(f"/v1/versions/{ref['version_id']}")
    except Exception as exc:  # noqa: BLE001
        log.warning("참조 이미지 버전 읽기 실패: %s", exc)
        return
    ref.update({"url": v.get("url"), "thumb_url": v.get("thumb_url"), "label": v.get("title") or "참조 이미지",
                "file_id": v.get("master_file_id")})
    await repo().patch("birdseyes", be_id, {"reference_image": ref})
    try:
        await ServiceClient("image").post(f"/v1/images/{v['image_id']}/usages",
                                          json={"version_id": ref["version_id"], "service": "birdseye", "ref": be_id,
                                                "label": f"{b['title']} · 조감도 참조"})
    except Exception as exc:  # noqa: BLE001
        log.warning("image usages 등록 실패: %s", exc)


async def patch(be_id: str, body: dict[str, Any]) -> dict[str, Any]:
    b = await get(be_id)
    if body.get("if_version") is not None and int(body["if_version"]) != int(b["version"]):
        raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 먼저 고쳤어요. 새로 불러온 뒤 다시 해 주세요.",
                       {"rev": b["version"]})
    changes: dict[str, Any] = {}
    for k_in, k_doc in (("title", "title"), ("customer_name", "customer_name"), ("space_chip", "space_chip"),
                        ("description", "description"), ("tone", "tone"), ("default_view", "default_view"),
                        ("zone_layout", "zone_layout"), ("shared_scope", "shared_scope"), ("shared_label", "shared_label"),
                        ("step", "step")):
        if body.get(k_in) is not None:
            changes[k_doc] = body[k_in]
    if body.get("area_pyeong") is not None:
        changes["area_input_pyeong"] = body["area_pyeong"]
    if body.get("ceiling_m") is not None:
        lo, hi = config.rules()["ceiling_range_m"]
        if not (lo <= float(body["ceiling_m"]) <= hi):
            raise ApiError(400, "INVALID_ARGUMENT", f"층고는 {T.num(lo)}~{T.num(hi)} m 사이로 적어 주세요", {"field": "ceiling_m"})
        changes["ceiling_input_m"] = body["ceiling_m"]
    if body.get("clear_area"):
        changes["area_input_pyeong"] = None
    if body.get("clear_ceiling"):
        changes["ceiling_input_m"] = None
    if "space_chip" in changes:
        info = config.chip_info(changes["space_chip"])
        changes["space_label"] = info["space_label"]
        changes["space_types"] = list(info["space_types"])
    if "description" in changes:
        inputs = dict(b.get("inputs") or {})
        inputs["description"] = bool((changes["description"] or "").strip())
        changes["inputs"] = inputs
        if b.get("title", "").startswith("새 조감도") and changes["description"].strip():
            changes["title"] = default_title(changes.get("space_chip") or b.get("space_chip"), changes["description"])
    if changes:
        await repo().patch("birdseyes", be_id, changes)
    await index(be_id)
    return await get(be_id)


async def touch(be_id: str, **changes: Any) -> dict[str, Any]:
    if changes:
        await repo().patch("birdseyes", be_id, changes)
    return await get(be_id)


async def set_step(be_id: str, step: int) -> None:
    await repo().patch("birdseyes", be_id, {"step": step})


# ── 상태 · 경로 ─────────────────────────────────────────

def cut_label(cut: dict[str, Any], *, queue: bool = False) -> str:
    view = (cut.get("view") or {}).get("label") or "조감 45°"
    light = config.light_info(cut.get("light"))["label"]
    if cut.get("before"):
        return f"도입 전 · {view}" + (" (비교용)" if queue else "")
    return f"{view} · {light}"


def cut_short(cut: dict[str, Any], primary: dict[str, Any] | None) -> str:
    """BE5 썸네일 라벨: 주 시점과 다르면 시점, 조명만 다르면 조명."""
    view = (cut.get("view") or {}).get("label") or "조감 45°"
    if cut.get("before"):
        return "도입 전"
    if primary is None or cut["id"] == primary["id"]:
        return view
    pv = (primary.get("view") or {}).get("label")
    if view != pv:
        return view
    if cut.get("light") != primary.get("light"):
        return config.light_info(cut.get("light"))["label"]
    return view


def running_name(cut: dict[str, Any], primary: dict[str, Any] | None) -> str:
    """BE0 「{컷 이름} 추가 생성 중」 — 「야간 시점」 · 「입구 시점」 · 「도입 전 컷」."""
    if cut.get("before"):
        return "도입 전 컷"
    view = (cut.get("view") or {}).get("label") or "조감 45°"
    if primary and (primary.get("view") or {}).get("label") == view and cut.get("light") != primary.get("light"):
        return f"{config.light_info(cut.get('light'))['label']} 시점"
    return view if view.endswith("시점") else f"{view} 시점"


async def derive(be_id: str) -> dict[str, Any]:
    """상태 · 사유 · 경로를 다시 계산해 저장한다(단계 이동 · 컷 완료 · 사진 · 질문 때마다)."""
    b = await get(be_id)
    step = int(b.get("step") or 1)
    cs = await cuts(be_id)
    running = [c for c in cs if c["status"] in ("running", "queued") and c.get("job_id") and c["status"] == "running"]
    done = [c for c in cs if c["status"] in ("done", "check", "draft") and not c.get("stale")]
    primary = next((c for c in cs if c["id"] == b.get("primary_cut_id")), None)
    status = "in_progress"
    reason = None
    check_route = None
    photos = await repo().all("photos", where={"birdseye_id": be_id})
    bad_photos = [p for p in photos if p["status"] in ("backlit", "dark", "blurry")]
    plans_ = await repo().all("plans", where={"birdseye_id": be_id})
    open_q = 0
    for p in plans_:
        if p.get("finalized"):
            continue
        open_q += sum(1 for q in ((p.get("model") or {}).get("questions") or []) if not q.get("answered"))
    check_cuts = [c for c in cs if c["status"] == "check" and not c.get("stale")]
    if primary and primary["status"] in ("done", "check", "draft"):
        status = "done"
    if step <= 1 and bad_photos:
        status = "needs_check"
        reason = f"사진 {len(bad_photos)}장 다시 찍기 · 1/5 {config.STEPS[0]}"
        check_route = f"/birdseye/{be_id}/space/photos"
    elif step <= 1 and open_q:
        status = "needs_check"
        reason = f"도면 확인 {open_q}곳 · 1/5 {config.STEPS[0]}"
        pid = plans_[0]["id"] if plans_ else ""
        check_route = f"/birdseye/{be_id}/space/plan" + (f"?plan={pid}" if pid else "")
    elif check_cuts and status != "done":
        status = "needs_check"
        reason = f"품질 확인 필요 컷 {len(check_cuts)} · 5/5 {config.STEPS[4]}"
        check_route = f"/birdseye/{be_id}/result"
    failed = [c for c in cs if c["status"] == "failed"]
    if status == "in_progress" and step == 5 and failed and not done:
        status = "failed"
    # 경로
    if running:
        route = f"/birdseye/{be_id}/render/{running[0]['job_id']}"
    elif step >= 5 and (done or primary):
        route = f"/birdseye/{be_id}/result"
    else:
        route = f"/birdseye/{be_id}/{STEP_ROUTE.get(min(step, 4) if not done else 5, 'space')}"
    if step == 1:
        if photos and not plans_:
            route = f"/birdseye/{be_id}/space/photos"
        elif plans_ and not all(p.get("finalized") for p in plans_):
            route = f"/birdseye/{be_id}/space/plan"
    changes = {"status": status, "status_reason": reason, "check_route": check_route, "route": route}
    if any(b.get(k) != v for k, v in changes.items()):
        await repo().patch("birdseyes", be_id, changes)
    return {**b, **changes}


def status_label(b: dict[str, Any]) -> str:
    st = b.get("status")
    if st == "done":
        return "완료"
    if st == "needs_check":
        return "확인 필요"
    if st == "failed":
        return "실패"
    step = int(b.get("step") or 1)
    return f"{step}/5 {config.STEPS[step - 1]}"


async def index(be_id: str) -> None:
    """workspace 색인 — feature='BE', route = 현재 단계 화면(진행 중 렌더가 있으면 BE5G)."""
    try:
        b = await derive(be_id)
    except ApiError:
        return
    subtitle = " · ".join(x for x in (b.get("customer_name"), b.get("space_label")) if x)
    summary = " · ".join(x for x in (subtitle, status_label(b)) if x)
    await register_item(feature=config.FEATURE, item_id=be_id, title=b["title"], status=b["status"], route=b["route"],
                        summary=summary, project_id=b.get("project_id"),
                        meta={"step": b.get("step"), "status_label": status_label(b), "layout_version": b.get("layout_version"),
                              "version": b.get("save_version", 1)})


# ── 목록(BE0) ────────────────────────────────────────────

def _thumb_from_cut(c: dict[str, Any] | None) -> str | None:
    if not c:
        return None
    fid = c.get("thumb_file_id") or c.get("image_file_id") or c.get("draft_v1_file_id") or c.get("draft_file_id")
    return f"/api/files/v1/files/{fid}/thumbnail?w=320" if fid else None


async def row(b: dict[str, Any]) -> dict[str, Any]:
    be_id = b["id"]
    cs = await cuts(be_id)
    primary = next((c for c in cs if c["id"] == b.get("primary_cut_id")), None)
    done_cuts = [c for c in cs if c["status"] in ("done", "check", "draft") and not c.get("stale")]
    zs = await zones(be_id)
    furn = await furniture(be_id, selected_only=True)
    prods = await products(be_id)
    inputs = b.get("inputs") or {}
    chips = []
    if inputs.get("description"):
        chips.append("설명")
    if inputs.get("plan_file_ids"):
        chips.append("도면")
    if inputs.get("photo_count"):
        chips.append(f"사진 {inputs['photo_count']}장")
    st = b.get("status", "in_progress")
    step = int(b.get("step") or 1)
    running = None
    run_cut = next((c for c in cs if c["status"] == "running" and c.get("job_id")), None)
    if run_cut is not None and st == "done":
        running = {"cut_id": run_cut["id"], "label": f"{running_name(run_cut, primary)} 추가 생성 중",
                   "route": f"/birdseye/{be_id}/render/{run_cut['job_id']}", "progress": run_cut.get("progress", 0)}
    if st == "done":
        title = "완료"
        line = f"시점 {len(done_cuts)}" + (f" · 존 포인트 {len(zs)}" if zs else "")
        action = {"label": "열기", "route": f"/birdseye/{be_id}/result"}
    elif st == "needs_check":
        title = "확인 필요"
        line = b.get("status_reason") or ""
        action = {"label": "확인", "route": b.get("check_route") or b.get("route") or f"/birdseye/{be_id}/space"}
    elif st == "failed":
        title = "실패"
        line = "조감도를 만들지 못했어요"
        action = {"label": "이어서", "route": b.get("route") or f"/birdseye/{be_id}/layout"}
    else:
        title = f"{step}/5"
        line = config.STEPS[step - 1]
        action = {"label": "이어서", "route": b.get("route") or f"/birdseye/{be_id}/space"}
    us = await usages(be_id)
    thumb = _thumb_from_cut(primary)
    if not thumb:
        ph = await repo().all("photos", where={"birdseye_id": be_id}, order_by="created_at", limit=1)
        if ph:
            thumb = f"/api/files/v1/files/{ph[0]['file_id']}/thumbnail?w=320"
    prod_line = " · ".join(p.get("short") or p.get("display_name") for p in prods[:3])
    kinds = len({f.get("catalog_code") or f.get("name") for f in furn})
    products_line = " · ".join(x for x in (prod_line, f"가구 {kinds}종" if kinds else "") if x)
    team = f"{b.get('shared_label') or '팀'} 공유 · 시점 {len(done_cuts)}" + (f" · 존 포인트 {len(zs)}" if zs else "")
    return {
        "id": be_id, "title": b["title"], "subtitle": " · ".join(x for x in (b.get("customer_name"), b.get("space_label")) if x),
        "customer_name": b.get("customer_name"), "space_label": b.get("space_label", ""), "thumb_url": thumb, "input_chips": chips,
        "status": st, "step": step, "step_label": config.STEPS[step - 1], "status_title": title, "status_line": line,
        "running": running,
        "usages": [{"service": u["service"], "ref": u["ref"], "label": u.get("label", ""), "version": u.get("version"),
                    "route": u.get("route")} for u in us],
        "action": action, "route": b.get("route") or action["route"], "updated_at": b["updated_at"], "created_at": b["created_at"],
        "views_count": len(done_cuts), "zones_count": len(zs), "zone_count": len(zs), "version": int(b.get("save_version") or 1),
        "layout_version": int(b.get("layout_version") or 0), "furniture_kinds": kinds, "products_line": products_line,
        "shared_scope": b.get("shared_scope", "private"), "shared_label": b.get("shared_label"), "team_meta": team,
        "owner": b["owner"], "owner_name": b.get("owner_name", ""), "done": st == "done",
        "primary_cut_url": _full_from_cut(primary),
    }


def _full_from_cut(c: dict[str, Any] | None) -> str | None:
    if not c:
        return None
    fid = c.get("image_file_id") or c.get("draft_v1_file_id") or c.get("draft_file_id")
    return f"/api/files/v1/files/{fid}/content" if fid else None


async def list_rows(*, filter_: str, in_proposal: bool, q: str | None, scope: str, limit: int, cursor: str | None) -> dict[str, Any]:
    me = uid()
    if scope == "team":
        docs = await repo().all("birdseyes", where={"shared_scope": "team"})
    else:
        docs = await repo().all("birdseyes", where={"owner": me})
    docs = [d for d in docs if not d.get("deleted_at")]
    rows_all = []
    for d in docs:
        try:
            d = await derive(d["id"])
        except ApiError:
            continue
        rows_all.append(d)
    if q and q.strip():
        qs = q.strip().lower()
        rows_all = [d for d in rows_all if qs in (d.get("title") or "").lower() or qs in (d.get("customer_name") or "").lower()
                    or qs in (d.get("space_label") or "").lower() or qs in (d.get("description") or "").lower()]
    counts = {"all": len(rows_all), "in_progress": 0, "needs_check": 0, "done": 0}
    for d in rows_all:
        st = d.get("status")
        if st in ("in_progress", "failed"):
            counts["in_progress"] += 1
        elif st in counts:
            counts[st] += 1
    if filter_ and filter_ != "all":
        if filter_ == "in_progress":
            rows_all = [d for d in rows_all if d.get("status") in ("in_progress", "failed")]
        else:
            rows_all = [d for d in rows_all if d.get("status") == filter_]
    if in_proposal:
        keep = []
        for d in rows_all:
            us = await usages(d["id"])
            if any(u["service"] == "proposal" for u in us):
                keep.append(d)
        rows_all = keep
    rows_all.sort(key=lambda d: d["updated_at"], reverse=True)
    start = int(cursor) if cursor and cursor.isdigit() else 0
    page = rows_all[start:start + limit]
    nxt = str(start + limit) if start + limit < len(rows_all) else None
    return {"items": [await row(d) for d in page], "counts": counts, "next_cursor": nxt, "total": len(rows_all)}


def view(b: dict[str, Any]) -> dict[str, Any]:
    """Birdseye 응답(계약 모양)."""
    return {
        "id": b["id"], "owner": b["owner"], "owner_name": b.get("owner_name", ""), "project_id": b.get("project_id"),
        "customer_name": b.get("customer_name"), "title": b["title"], "space_label": b.get("space_label", ""),
        "space_chip": b.get("space_chip", "store_lobby"), "space_types": b.get("space_types", []), "description": b.get("description", ""),
        "area_input_pyeong": b.get("area_input_pyeong"), "ceiling_input_m": b.get("ceiling_input_m"), "inputs": b.get("inputs") or {},
        "step": int(b.get("step") or 1), "status": b.get("status", "in_progress"), "status_reason": b.get("status_reason"),
        "check_route": b.get("check_route"), "tone": b.get("tone", "warm_wood"), "default_view": b.get("default_view", "aerial45"),
        "version": int(b.get("save_version") or 1), "rev": int(b.get("version") or 1), "layout_version": int(b.get("layout_version") or 0),
        "primary_cut_id": b.get("primary_cut_id"), "shared_scope": b.get("shared_scope", "private"), "shared_label": b.get("shared_label"),
        "cloned_from": b.get("cloned_from"), "origin": b.get("origin"), "zone_layout": b.get("zone_layout", "ZP-A"),
        "route": b.get("route") or f"/birdseye/{b['id']}/space", "reference_image": b.get("reference_image"),
        "prefill_products": b.get("prefill_products") or [], "analyzing_job_id": b.get("analyzing_job_id"),
        "created_at": b["created_at"], "updated_at": b["updated_at"],
    }


# ── 변경 감지 · 저장 · 되살리기 · 복제 · 지우기 ──────────

async def zones_hash(be_id: str) -> str:
    zs = await zones(be_id)
    payload = [{"n": z.get("n"), "name": z.get("name"), "items": sorted(z.get("cluster_item_ids") or []),
                "products": [p.get("label") for p in z.get("products") or []]} for z in zs]
    return hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


async def version_info(be_id: str) -> dict[str, Any]:
    b = await get(be_id)
    return {"version": int(b.get("save_version") or 1), "layout_version": int(b.get("layout_version") or 0),
            "updated_at": b["updated_at"], "zones_hash": await zones_hash(be_id), "rev": int(b.get("version") or 1)}


async def _snapshot_payload(be_id: str) -> dict[str, Any]:
    b = await get(be_id)
    return {
        "birdseye": {k: b.get(k) for k in ("title", "customer_name", "space_chip", "description", "area_input_pyeong", "ceiling_input_m",
                                             "tone", "default_view", "zone_layout", "primary_cut_id", "layout_version")},
        "space": await space_model(be_id),
        "products": await products(be_id),
        "furniture": await furniture(be_id),
        "zones": await zones(be_id, include_all=True),
        "cut_ids": [c["id"] for c in await cuts(be_id)],
    }


async def save(be_id: str) -> dict[str, Any]:
    b = await get(be_id)
    payload = await _snapshot_payload(be_id)
    digest = hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()
    v = int(b.get("save_version") or 1)
    if b.get("saved"):
        if b.get("saved_digest") == digest:
            return {"version": v, "created": False}
        v += 1
    await repo().put("snapshots", f"{be_id}:{v}", {"birdseye_id": be_id, "n": v, "payload": payload, "digest": digest,
                                                   "layout_version": b.get("layout_version") or 0, "note": None})
    await repo().patch("birdseyes", be_id, {"save_version": v, "saved": True, "saved_digest": digest})
    await index(be_id)
    return {"version": v, "created": True}


async def saved_versions(be_id: str) -> list[dict[str, Any]]:
    await get(be_id)
    snaps = await repo().all("snapshots", where={"birdseye_id": be_id}, order_by="created_at")
    return [{"version": s["n"], "created_at": s["created_at"], "layout_version": s.get("layout_version", 0), "note": s.get("note")}
            for s in sorted(snaps, key=lambda s: s["n"], reverse=True)]


async def restore(be_id: str, n: int) -> dict[str, Any]:
    snap = await repo().get("snapshots", f"{be_id}:{n}")
    if snap is None:
        raise not_found("저장 버전", f"v{n}")
    p = snap["payload"]
    changes = dict(p.get("birdseye") or {})
    await repo().patch("birdseyes", be_id, changes)
    if p.get("space") is not None:
        await repo().put("space", be_id, {"birdseye_id": be_id, "model": p["space"], "source": p["space"].get("source", "description")},
                         history=True)
    for coll, items in (("products", p.get("products") or []), ("furniture", p.get("furniture") or [])):
        cur = await repo().all(coll, where={"birdseye_id": be_id})
        keep = {i["id"] for i in items}
        for c in cur:
            if c["id"] not in keep:
                await repo().delete(coll, c["id"])
        for i in items:
            await repo().put(coll, i["id"], i)
    await index(be_id)
    return await get(be_id)


async def clone(be_id: str, title: str | None) -> dict[str, Any]:
    """공간 모델 · 제품 · 가구 · 레이아웃 · 톤 · 시점은 복사, 컷 · 존 · 사용 이력은 복사하지 않는다. → BE4."""
    src = await repo().get("birdseyes", be_id)
    if src is None or src.get("deleted_at"):
        raise not_found("조감도 작업", be_id)
    user = current_user()
    nid = new_id("be")
    doc = {k: v for k, v in src.items() if k not in ("id", "version", "created_at", "updated_at")}
    doc.update({
        "owner": user.id, "owner_name": user.name, "title": title or f"{src['title']} 복제", "cloned_from": be_id,
        "primary_cut_id": None, "shared_scope": "private", "shared_label": None, "step": 4, "status": "in_progress",
        "status_reason": None, "check_route": None, "save_version": 1, "saved": False, "saved_digest": None,
        "analyzing_job_id": None, "deleted_at": None, "origin": {"service": "birdseye", "ref": be_id, "label": "복제"},
    })
    await repo().put("birdseyes", nid, doc)
    sm = await repo().get("space", be_id)
    if sm:
        await repo().put("space", nid, {"birdseye_id": nid, "model": sm["model"], "source": sm.get("source")}, history=True)
    id_map: dict[str, str] = {}
    for p in await products(be_id):
        pid = new_id("bpi")
        id_map[p["id"]] = pid
        await repo().put("products", pid, {**{k: v for k, v in p.items() if k not in ("id", "version", "created_at", "updated_at")},
                                           "birdseye_id": nid})
    for f in await furniture(be_id):
        fid = new_id("bfi")
        id_map[f["id"]] = fid
        await repo().put("furniture", fid, {**{k: v for k, v in f.items() if k not in ("id", "version", "created_at", "updated_at")},
                                            "birdseye_id": nid})
    lv = int(src.get("layout_version") or 0)
    if lv:
        lay = await repo().get("layouts", f"{be_id}:{lv}")
        if lay:
            body = json.loads(json.dumps({k: v for k, v in lay.items() if k not in ("id", "version", "created_at", "updated_at")}))
            layout = body.get("layout") or {}
            for it in layout.get("items", []):
                it["ref"] = id_map.get(it.get("ref"), it.get("ref"))
            for g in layout.get("groups", []):
                g["ref"] = id_map.get(g.get("ref"), g.get("ref"))
            layout["version"] = 1
            layout["created_by"] = "clone"
            layout["parent_version"] = None
            body.update({"birdseye_id": nid, "v": 1, "layout": layout})
            await repo().put("layouts", f"{nid}:1", body)
            await repo().patch("birdseyes", nid, {"layout_version": 1})
    await index(nid)
    return {"id": nid, "route": f"/birdseye/{nid}/layout"}


async def delete(be_id: str) -> None:
    await get(be_id)
    await repo().patch("birdseyes", be_id, {"deleted_at": now_iso()})   # 소프트 삭제(문서는 남는다)
    await unregister_item(be_id)


# ── 쓰인 곳 ──────────────────────────────────────────────

async def add_usage(be_id: str, body: dict[str, Any]) -> dict[str, Any]:
    await get(be_id)
    uid_ = f"{be_id}|{body['service']}|{body['ref']}"
    doc = {"birdseye_id": be_id, "service": body["service"], "ref": body["ref"], "label": body.get("label") or "",
           "version": body.get("version"), "route": body.get("route")}
    saved = await repo().put("usages", uid_, doc)
    await repo().patch("birdseyes", be_id, {"usage_count": len(await usages(be_id))})
    return {**doc, "created_at": saved["created_at"]}


async def remove_usage(be_id: str, service: str, ref: str) -> None:
    await get(be_id)
    await repo().delete("usages", f"{be_id}|{service}|{ref}")
