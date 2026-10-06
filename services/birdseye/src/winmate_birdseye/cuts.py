"""컷(렌더) 기록 · 대기열(08-birdseye §4.9~§4.11 · §6.5 · §7.8).

- 컷마다 job, 같은 조감도의 컷은 순차(대기열): 잡 id 를 미리 만들어 두고 앞 컷이 끝나면 다음 컷 잡을 넣는다(pump).
- 같은 컷(같은 레이아웃 버전 · 시점 · 조명 · 전후 · 톤)은 다시 만들지 않는다.
- 추가 컷 자동 예약(BE4 → 첫 렌더 때만, 최대 2): 야간(외부 노출 · 저녁 · 밖을 향한 창) · 도입 전(제안서 연결 · 「전후」).
"""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import jobs

from . import config
from . import service as svc
from .engine import tiny_of
from .repo import repo

log = logging.getLogger("winmate.birdseye.cuts")

STAGES = [("structure", "공간 구조"), ("products", "제품 배치"), ("furniture", "가구 · 마감재"), ("render", "조명 · 렌더링"),
          ("qc", "품질 확인")]


def view_label(preset: str, target_name: str | None = None, custom_text: str | None = None) -> str:
    if preset == "product_front":
        return f"{target_name or '제품'} 정면"
    if preset == "custom":
        t = (custom_text or "사용자 시점").strip()
        return t if len(t) <= 14 else t[:14].rstrip()
    return config.rules()["views"].get(preset, {}).get("label") or "조감 45°"


def view_key(view: dict[str, Any]) -> str:
    if view.get("preset") == "custom":
        return f"custom:{view.get('custom_text') or ''}"
    if view.get("preset") == "product_front":
        return f"product_front:{view.get('target_item_id') or ''}"
    return view.get("preset") or "aerial45"


async def _largest_display(be_id: str) -> dict[str, Any] | None:
    from .layouts import get_layout

    lay = await get_layout(be_id)
    if not lay:
        return None
    disp = [it for it in lay.get("items", []) if it["kind"] == "product" and it.get("mount") != "window_facing"]
    if not disp:
        disp = [it for it in lay.get("items", []) if it["kind"] == "product"]
    if not disp:
        return None
    return max(disp, key=lambda it: (it["w"] * it["h"], -int(it["id"][2:]) if it["id"][2:].isdigit() else 0))


def steps_init() -> list[dict[str, Any]]:
    return [{"stage": s, "label": lab, "note": "", "state": "wait"} for s, lab in STAGES]


async def create_cuts(be_id: str, body: dict[str, Any]) -> dict[str, Any]:
    b = await svc.get(be_id)
    lv = int(b.get("layout_version") or 0)
    if not lv:
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안을 먼저 확인해 주세요")
    tone = body.get("tone") or b.get("tone") or "warm_wood"
    if body.get("tone") and body["tone"] != b.get("tone") and body.get("primary"):
        await svc.touch(be_id, tone=body["tone"])
    views = []
    big = None
    for v in body.get("views") or []:
        if v.get("custom_text"):
            views.append({"preset": "custom", "target_item_id": None, "camera": None, "custom_text": v["custom_text"].strip(),
                          "label": view_label("custom", custom_text=v["custom_text"]), "meta_path": None})
            continue
        preset = v.get("preset") or b.get("default_view") or "aerial45"
        tgt = v.get("target_item_id")
        name = None
        if preset == "product_front":
            if big is None:
                big = await _largest_display(be_id)
            if not tgt and big:
                tgt = big["id"]
            from .layouts import get_layout

            lay = await get_layout(be_id)
            it = next((x for x in (lay or {}).get("items", []) if x["id"] == tgt), None)
            name = tiny_of((it or {}).get("short") or (it or {}).get("label") or "제품")
        views.append({"preset": preset, "target_item_id": tgt, "camera": None, "custom_text": None,
                      "label": view_label(preset, name), "meta_path": None})
    lights = body.get("lights") or ["day"]
    befores = [False, True] if body.get("before") else [False]
    existing = await svc.cuts(be_id)
    same = {(int(c.get("layout_version") or 0), view_key(c["view"]), c.get("light"), bool(c.get("before")), c.get("tone"))
            for c in existing if c["status"] not in ("failed", "canceled") and not c.get("stale")}
    order0 = max([int(c.get("queue_order") or 0) for c in existing] + [0])
    created: list[dict[str, Any]] = []
    skipped = 0
    specs = [(v, light, bf, False) for v in views for light in lights for bf in befores]
    if body.get("primary") and body.get("auto_extra") and config.auto_extra_cuts() and not any(c.get("is_primary") for c in existing):
        specs += await _auto_extra(b, views[0] if views else None)
    for v, light, bf, auto in specs:
        key = (lv, view_key(v), light, bf, tone)
        if key in same:
            skipped += 1
            continue
        same.add(key)
        order0 += 1
        cid = new_id("bec")
        doc = {
            "birdseye_id": be_id, "layout_version": lv, "view": v, "light": light, "before": bf, "tone": tone, "status": "queued",
            "stale": False, "progress": 0.0, "eta_s": None, "stage": None, "steps": steps_init(), "job_id": new_id("job"),
            "job_enqueued": False, "render_id": None, "image_id": None, "version_id": None, "draft_file_id": None,
            "draft_v1_file_id": None, "image_file_id": None, "thumb_file_id": None, "renditions": [], "resolution": config.rules()["render"]["resolution"],
            "auto_queued": auto, "is_primary": bool(body.get("primary")) and not created and not auto and not bf,
            "queue_order": order0, "render_path": None, "badge": None, "qc": {}, "error": None, "edit_pending_text": None,
            "notice": None, "finished_at": None, "camera": None, "history": [], "memos_used": 0,
            "prompt_extra": list(body.get("prompt_extra") or []),
        }
        saved = await repo().put("cuts", cid, doc)
        created.append(saved)
    if created and int(b.get("step") or 1) < 5:
        await svc.set_step(be_id, 5)
    await pump(be_id)
    await svc.index(be_id)
    first = created[0] if created else None
    return {"cut_ids": [c["id"] for c in created], "job_ids": [c["job_id"] for c in created],
            "job_id": first["job_id"] if first else None,
            "route": f"/birdseye/{be_id}/render/{first['job_id']}" if first else None, "skipped": skipped}


async def _auto_extra(b: dict[str, Any], main_view: dict[str, Any] | None) -> list[tuple[dict[str, Any], str, bool, bool]]:
    model = await svc.space_model(b["id"]) or {}
    cfg = config.rules()["auto_extra_cuts"]
    desc = b.get("description") or ""
    out: list[tuple[dict[str, Any], str, bool, bool]] = []
    v = main_view or {"preset": "aerial45", "target_item_id": None, "camera": None, "custom_text": None, "label": "조감 45°"}
    night = any(w in desc for w in cfg["night_words"]) or any(f.get("kind") == "night_visibility" for f in model.get("features", [])) \
        or any(o.get("kind") == "window" and o.get("faces_outdoor") for o in model.get("openings", []))
    if night:
        out.append((v, "night", False, True))
    us = await svc.usages(b["id"])
    linked = any(u["service"] == "proposal" for u in us) or ((b.get("origin") or {}).get("service") == "proposal")
    if linked or any(w in desc for w in cfg["before_words"]):
        out.append((v, "day", True, True))
    return out[: int(cfg.get("max", 2))]


async def pump(be_id: str) -> str | None:
    """앞 컷이 없으면 다음 대기 컷의 잡을 넣는다(미리 만든 잡 id)."""
    cs = await svc.cuts(be_id)
    active = [c for c in cs if c.get("job_enqueued") and c["status"] in ("queued", "running")]
    if active:
        return None
    nxt = next((c for c in cs if c["status"] == "queued" and not c.get("job_enqueued")), None)
    if nxt is None:
        return None
    claimed = {"ok": False}

    def fn(doc: dict[str, Any]) -> None:
        if doc.get("job_enqueued") or doc.get("status") != "queued":
            return None
        doc["job_enqueued"] = True
        claimed["ok"] = True
        return None

    await repo().mutate("cuts", nxt["id"], fn, missing_ok=True)
    if not claimed["ok"]:
        return None
    b = await svc.get(be_id)
    await jobs().enqueue("birdseye", "render_cut", {"cut_id": nxt["id"], "birdseye_id": be_id},
                         title=f"{b['title']} · {svc.cut_label(nxt)}", ref=be_id, project_id=b.get("project_id"),
                         owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=nxt["job_id"])
    return nxt["job_id"]


async def get_cut(cut_id: str) -> dict[str, Any]:
    c = await repo().get("cuts", cut_id)
    if c is None:
        raise not_found("컷", cut_id)
    return c


async def cancel(cut_id: str) -> dict[str, Any]:
    """대기 컷은 즉시 삭제, 진행 컷은 초안 저장 후 중지(워커가 처리)."""
    c = await get_cut(cut_id)
    if c["status"] == "queued" and not c.get("job_enqueued"):
        await repo().patch("cuts", cut_id, {"status": "canceled", "finished_at": now_iso()})
        await repo().delete("cuts", cut_id)
        out = {**c, "status": "canceled"}
    else:
        if c.get("job_id"):
            await jobs().cancel(c["job_id"])
        if c.get("render_id"):
            from winmate_common.client import ServiceClient

            try:
                await ServiceClient("image").post(f"/v1/renders/{c['render_id']}:cancel")
            except Exception as exc:  # noqa: BLE001
                log.warning("image 렌더 취소 실패: %s", exc)
        job = await jobs().get(c["job_id"]) if c.get("job_id") else None
        if job is not None and job.status == "canceled":
            # 워커가 잡지 않은 잡 — 초안이 있으면 draft 로
            st = "draft" if (c.get("draft_v1_file_id") or c.get("draft_file_id")) else "canceled"
            await repo().patch("cuts", cut_id, {"status": st, "finished_at": now_iso()})
            if st == "canceled":
                await repo().delete("cuts", cut_id)
        out = await repo().get("cuts", cut_id, include_deleted=True) or c
    await pump(c["birdseye_id"])
    await svc.index(c["birdseye_id"])
    return out


async def set_primary(cut_id: str) -> dict[str, Any]:
    c = await get_cut(cut_id)
    for x in await svc.cuts(c["birdseye_id"]):
        if x.get("is_primary") and x["id"] != cut_id:
            await repo().patch("cuts", x["id"], {"is_primary": False})
    await repo().patch("cuts", cut_id, {"is_primary": True})
    await svc.touch(c["birdseye_id"], primary_cut_id=cut_id)
    await svc.index(c["birdseye_id"])
    return await get_cut(cut_id)


def file_url(fid: str | None) -> str | None:
    return f"/api/files/v1/files/{fid}/content" if fid else None


def thumb_url(fid: str | None, w: int = 480) -> str | None:
    return f"/api/files/v1/files/{fid}/thumbnail?w={w}" if fid else None


def display_file_id(c: dict[str, Any]) -> str | None:
    """화면 표시용 파일 — 완성 컷의 FHD 렌디션(3840×2160 원본은 내려받기 · 내보내기에만)."""
    if c.get("status") not in ("done", "check") or not c.get("image_file_id"):
        return None
    fhd = next((r for r in (c.get("renditions") or []) if r.get("kind") == "fhd" and r.get("file_id")), None)
    return fhd["file_id"] if fhd else None


async def cut_view(c: dict[str, Any], *, primary: dict[str, Any] | None = None, queue_pos: int | None = None) -> dict[str, Any]:
    img_fid = c.get("image_file_id") or (c.get("draft_v1_file_id") if c["status"] == "draft" else None)
    draft_fid = c.get("draft_v1_file_id") or c.get("draft_file_id")
    show_fid = display_file_id(c) or img_fid
    return {
        "id": c["id"], "birdseye_id": c["birdseye_id"], "layout_version": int(c.get("layout_version") or 0),
        "view": {"preset": c["view"].get("preset") or "aerial45", "target_item_id": c["view"].get("target_item_id"),
                 "camera": c.get("camera"), "label": c["view"].get("label") or "조감 45°", "custom_text": c["view"].get("custom_text"),
                 "meta_path": c["view"].get("meta_path")},
        "light": c.get("light") or "day", "before": bool(c.get("before")), "tone": c.get("tone") or "warm_wood", "status": c["status"],
        "stale": bool(c.get("stale")), "progress": float(c.get("progress") or 0), "eta_s": c.get("eta_s"), "stage": c.get("stage"),
        "steps": c.get("steps") or steps_init(), "job_id": c.get("job_id"), "render_id": c.get("render_id"), "image_id": c.get("image_id"),
        "version_id": c.get("version_id"), "draft_file_id": c.get("draft_file_id"), "draft_v1_file_id": c.get("draft_v1_file_id"),
        "draft_url": file_url(draft_fid), "image_url": file_url(img_fid), "display_url": file_url(show_fid), "thumb_url": thumb_url(img_fid or draft_fid),
        "renditions": c.get("renditions") or [], "resolution": c.get("resolution") or "3840×2160", "auto_queued": bool(c.get("auto_queued")),
        "is_primary": bool(c.get("is_primary")), "queue_pos": queue_pos, "label": svc.cut_label(c, queue=bool(c.get("before"))),
        "thumb_label": svc.cut_short(c, primary), "render_path": c.get("render_path"), "badge": c.get("badge"), "qc": c.get("qc") or {},
        "error": c.get("error"), "edit_pending_text": c.get("edit_pending_text"), "notice": c.get("notice"),
        "created_at": c["created_at"], "finished_at": c.get("finished_at"),
    }


async def list_cuts(be_id: str) -> list[dict[str, Any]]:
    await pump(be_id)
    b = await svc.get(be_id)
    cs = await svc.cuts(be_id)
    primary = next((c for c in cs if c["id"] == b.get("primary_cut_id")), None)
    queued = [c for c in cs if c["status"] == "queued"]
    pos = {c["id"]: i + 1 for i, c in enumerate(queued)}
    return [await cut_view(c, primary=primary, queue_pos=pos.get(c["id"])) for c in cs]
