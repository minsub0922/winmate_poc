"""scenario API (/v1) — 시나리오 목록 · 만들기 · 고치기 · 저장 · 조감도 연결 · 시드. 이 파일들의 엔드포인트가 contracts/scenario.json 이 된다.

다른 라우터: api_flow(입력 · 타임라인 · 솔루션 · 추천 · 생성), api_scenes(장면 · 이미지 · 수정 요청), api_send(시트 · 넘기기 · 내보내기).
"""
from __future__ import annotations

import base64
import copy
from typing import Any, Literal

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel
from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.platform import unregister_item

from . import birdseye as be
from . import llm, prompts, repo, seed, service, texts
from . import models as m
from . import timeline as tl

router = APIRouter(prefix="/v1")
TAG = ["scenarios"]


@router.get("/info", response_model=m.Info, tags=["meta"])
async def info() -> m.Info:
    return m.Info(service="scenario", title="공간 시나리오 — 업종 템플릿 · 장면 작성 · 장면별 솔루션 · 장면 이미지 · 내보내기", version="0.2.0")


# ── 목록(SC0) ─────────────────────────────────────────────

async def _check_birdseye_changes(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """연결 유지한 조감도 버전이 연결 시점보다 크면 changed 를 남긴다(60초 캐시, R10)."""
    out = []
    for d in docs:
        link = d.get("birdseye_link") or {}
        if not link.get("keep_link") or not link.get("birdseye_id"):
            out.append(d)
            continue
        v = await be.version(link["birdseye_id"])
        cur = (v or {}).get("version")
        if cur is None or link.get("linked_version") is None or int(cur) <= int(link["linked_version"]):
            out.append(d)
            continue
        changed = link.get("changed") or {}
        if changed.get("version") == cur:
            out.append(d)
            continue

        def fn(doc: dict[str, Any], cur_: int = int(cur), at: str = (v or {}).get("updated_at") or now_iso()) -> dict[str, Any]:
            lk = doc.get("birdseye_link") or {}
            lk["changed"] = {"at": at, "version": cur_}
            doc["birdseye_link"] = lk
            return doc
        out.append(await repo.update(d["id"], fn))
    return out


def _alert(docs: list[dict[str, Any]]) -> dict[str, Any] | None:
    changed = []
    for d in docs:
        link = d.get("birdseye_link") or {}
        ch = link.get("changed")
        if not (link.get("keep_link") and ch):
            continue
        key = f"{link['birdseye_id']}@{ch.get('version')}"
        if key in (d.get("dismissed_alerts") or []):
            continue
        changed.append((ch.get("at") or "", link, d))
    if not changed:
        return None
    changed.sort(key=lambda x: x[0], reverse=True)
    at, link, _ = changed[0]
    ids = [d["id"] for _, lk, d in changed if lk["birdseye_id"] == link["birdseye_id"]]
    return {"birdseye_id": link["birdseye_id"], "title": link.get("title") or "조감도", "changed_at": at,
            "changed_label": texts.month_day(at), "version": (link.get("changed") or {}).get("version"), "scenario_ids": ids}


@router.get("/scenarios", response_model=m.ScenarioList, tags=TAG)
async def list_scenarios(status: Literal["all", "draft", "generating", "done", "failed"] = "all",
                         start_mode: Literal["all", "blank", "template", "birdseye"] = "all", q: str | None = None,
                         sort: Literal["updated", "created", "title"] = "updated", limit: int = Query(20, ge=1, le=100),
                         cursor: str | None = None) -> m.ScenarioList:
    docs = await repo.list_sc({"owner": current_user().id})
    docs = await _check_birdseye_changes(docs)
    alert = _alert(docs)
    if start_mode != "all":
        docs = [d for d in docs if (d.get("start_mode") or "blank") == start_mode]
    if q:
        ql = q.strip().lower()
        docs = [d for d in docs if ql in " ".join([d.get("title") or "", d.get("customer_name") or "", d.get("space_label") or ""]).lower()]
    counts = {"all": len(docs), "draft": 0, "generating": 0, "done": 0, "failed": 0}
    for d in docs:
        st = d.get("status") or "draft"
        counts[st] = counts.get(st, 0) + 1
    counts["draft"] += counts["failed"]
    if status == "draft":
        docs = [d for d in docs if d.get("status") in ("draft", "failed")]
    elif status != "all":
        docs = [d for d in docs if d.get("status") == status]
    if sort == "created":
        docs.sort(key=lambda d: d.get("created_at") or "", reverse=True)
    elif sort == "title":
        docs.sort(key=lambda d: d.get("title") or "")
    else:
        docs.sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    offset = 0
    if cursor:
        try:
            offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
        except Exception:  # noqa: BLE001
            offset = 0
    page = docs[offset:offset + limit]
    nxt = base64.urlsafe_b64encode(str(offset + limit).encode()).decode() if offset + limit < len(docs) else None
    return m.ScenarioList(items=[m.ScenarioRow(**service.row_out(d)) for d in page], counts=m.ListCounts(**counts), total=len(docs),
                          alert=m.BirdseyeAlert(**alert) if alert else None, next_cursor=nxt)


@router.post("/scenarios/{sc_id}/alerts:dismiss", status_code=204, tags=TAG)
async def dismiss_alert(sc_id: str) -> Response:
    """SC0 조감도 변경 알림 닫기 — 같은 변경(조감도 · 버전)은 다시 보이지 않는다(연결된 시나리오 모두)."""
    doc = await repo.require_sc(sc_id)
    link = doc.get("birdseye_link") or {}
    ch = link.get("changed") or {}
    if not link.get("birdseye_id"):
        return Response(status_code=204)
    key = f"{link['birdseye_id']}@{ch.get('version')}"
    for d in await repo.list_sc({"owner": current_user().id}):
        lk = d.get("birdseye_link") or {}
        if lk.get("birdseye_id") != link["birdseye_id"]:
            continue

        def fn(x: dict[str, Any]) -> dict[str, Any]:
            x["dismissed_alerts"] = list(dict.fromkeys([*(x.get("dismissed_alerts") or []), key]))
            return x
        await repo.update(d["id"], fn)
    return Response(status_code=204)


# ── 만들기 ─────────────────────────────────────────────────

async def _apply_aerial(doc: dict[str, Any], aerial: m.Aerial | None) -> None:
    if aerial is None:
        return
    a = aerial.model_dump()
    doc["aerial"] = {**(doc.get("aerial") or {}), **a, "enabled": bool(a.get("enabled"))}
    if a.get("enabled") and a.get("source") == "existing" and a.get("birdseye_id"):
        items, _ = await be.list_birdseyes()
        hit = next((x for x in items if x["id"] == a["birdseye_id"]), None)
        doc["aerial"]["title"] = (hit or {}).get("title") or a.get("title")
        if not (doc.get("birdseye_link") or {}).get("keep_link"):
            doc["birdseye_link"] = {"birdseye_id": a["birdseye_id"], "title": doc["aerial"]["title"] or "", "linked_version": (hit or {}).get("version"),
                                    "keep_link": False, "changed": None, "zone_ids": [], "order": []}


@router.post("/scenarios", response_model=m.Scenario, status_code=201, tags=TAG)
async def create_scenario(body: m.CreateScenario) -> m.Scenario:
    sb = await service.storyboard_context(body.storyboard_id)
    project_id = body.project_id or sb.get("project_id")
    pc = await service.project_context(project_id)
    doc = service.new_doc(type_=body.type, start_mode="blank", title=body.title, project_id=project_id)
    doc["customer_name"] = pc.get("customer") or sb.get("customer") or (body.customer_name or "").strip() or None
    doc["vertical_code"] = pc.get("industry_code")
    if sb.get("space_lines"):
        doc["raw_text"] = "\n".join(sb["space_lines"])
        doc["space_label"] = sb.get("space_label") or ""
        doc["storyboard_id"] = body.storyboard_id
    await _apply_aerial(doc, body.aerial)
    sc_id = service.new_scenario_id()
    stored = await repo.create_sc(sc_id, doc)
    await service.register(stored)
    return m.Scenario(**service.to_scenario(stored))


@router.post("/scenarios:from-template", response_model=m.JobAcceptedWithScenario, status_code=202, tags=TAG)
async def from_template(body: m.FromTemplate) -> m.JobAcceptedWithScenario:
    ind = seed.industry(body.industry)
    if ind is None:
        raise ApiError(404, "NOT_FOUND", f"업종 템플릿을 찾을 수 없어요: {body.industry}")
    preset = ind["presets"][body.preset_index - 1]
    pc = await service.project_context(body.project_id)
    doc = service.new_doc(type_=body.type, start_mode="template", project_id=body.project_id,
                          title=f"{(pc.get('customer') + ' ') if pc.get('customer') else ''}{preset['title']} 시나리오")
    doc["customer_name"] = pc.get("customer")
    doc["vertical_code"] = ind["code"]
    doc["template"] = {"industry": ind["code"], "preset_index": body.preset_index, "preset_title": preset["title"]}
    doc["step"] = 2
    doc["via_timeline"] = True
    payload = {"mode": "template", "industry": ind["code"], "preset_index": body.preset_index, "type": body.type,
               "project_id": body.project_id}
    return await _create_and_enqueue(doc, payload)


async def _create_and_enqueue(doc: dict[str, Any], payload: dict[str, Any]) -> m.JobAcceptedWithScenario:
    """문서를 먼저 저장하고(워커가 바로 읽을 수 있게) 골격 잡을 넣는다."""
    sc_id = service.new_scenario_id()
    stored = await repo.create_sc(sc_id, doc)
    job_id = await service.enqueue("sc.skeleton", stored, payload, title=stored["title"])

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        if d.get("parse"):
            return None  # 워커가 이미 끝냈다
        service.set_active(d, job_id, "skeleton")
        return d
    stored = await repo.update(sc_id, fn)
    await service.register(stored)
    return m.JobAcceptedWithScenario(job_id=job_id, scenario_id=sc_id)


@router.post("/scenarios:from-birdseye", response_model=m.JobAcceptedWithScenario, status_code=202, tags=TAG)
async def from_birdseye(body: m.FromBirdseye) -> m.JobAcceptedWithScenario:
    if not body.zone_ids:
        raise ApiError(400, "NO_ZONES", "가져올 존을 하나 이상 고르세요")
    project_id = body.project_id
    be_customer = None
    if not project_id:
        # 조감도의 프로젝트 · 고객을 잇는다(제안서 「같은 프로젝트」 기본 선택 · 고객 칩, 통합) — handoff 읽기 실패면 비운 채로
        h = await be.handoff(body.birdseye_id) or {}
        project_id = h.get("project_id") or None
        cust = h.get("customer")
        be_customer = (cust.get("name") if isinstance(cust, dict) else cust) or None
    pc = await service.project_context(project_id)
    items, _ = await be.list_birdseyes()
    hit = next((x for x in items if x["id"] == body.birdseye_id), None)
    title = (hit or {}).get("title") or "조감도"
    doc = service.new_doc(type_=body.type, start_mode="birdseye", project_id=project_id, title=f"{title} {body.axis} 시나리오")
    doc["customer_name"] = pc.get("customer") or be_customer
    doc["vertical_code"] = pc.get("industry_code")
    doc["birdseye_link"] = {"birdseye_id": body.birdseye_id, "title": title, "linked_version": (hit or {}).get("version"),
                            "keep_link": body.keep_link, "changed": None, "axis": body.axis, "zone_ids": body.zone_ids,
                            "order": body.order or body.zone_ids}
    doc["step"] = 2
    doc["via_timeline"] = True
    return await _create_and_enqueue(doc, {"mode": "birdseye", **body.model_dump()})


# ── 읽기 · 고치기 ───────────────────────────────────────────

@router.get("/scenarios/{sc_id}", response_model=m.Scenario, tags=TAG)
async def get_scenario(sc_id: str) -> m.Scenario:
    return m.Scenario(**service.to_scenario(await repo.require_sc(sc_id)))


@router.patch("/scenarios/{sc_id}", response_model=m.Scenario, tags=TAG)
async def patch_scenario(sc_id: str, body: m.PatchScenario) -> m.Scenario:
    data = body.model_dump(exclude_unset=True)
    if_rev = data.pop("if_rev", None)
    aerial = body.aerial

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if data.get("type"):
            d["type"] = data["type"]
        if data.get("title"):
            d["title"] = data["title"].strip()[:80]
        if "raw_text" in data and data["raw_text"] is not None:
            d["raw_text"] = data["raw_text"]
            d["dirty"] = True
        if data.get("characters") is not None:
            d["characters"] = [c.strip() for c in data["characters"] if c.strip()][:12]
        if data.get("removed_characters") is not None:
            d["removed_characters"] = list(dict.fromkeys(c.strip() for c in data["removed_characters"] if c.strip()))
        if data.get("step"):
            d["step"] = int(data["step"])
            if d["step"] >= 3:
                tl.settle(d)
        return d
    doc = await repo.update(sc_id, fn, expected_rev=if_rev)
    if aerial is not None:
        d2 = copy.deepcopy(doc)
        await _apply_aerial(d2, aerial)

        def fa(d: dict[str, Any]) -> dict[str, Any]:
            d["aerial"] = d2["aerial"]
            d["birdseye_link"] = d2.get("birdseye_link")
            return d
        doc = await repo.update(sc_id, fa)
        if doc.get("status") == "done":
            # SC4 「조감도 연결」 → 「새로 만들기」: 장면 · 제품이 이미 있으니 바로 초안을 만든다
            from .api_flow import ensure_aerial_draft
            _, doc = await ensure_aerial_draft(doc)
    await service.register(doc)
    return m.Scenario(**service.to_scenario(doc))


@router.delete("/scenarios/{sc_id}", status_code=204, tags=TAG)
async def delete_scenario(sc_id: str) -> Response:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["deleted_at"] = now_iso()
        return d
    await repo.update(sc_id, fn)
    await unregister_item(sc_id)
    return Response(status_code=204)


@router.post("/scenarios/{sc_id}:clone", response_model=m.CloneResult, status_code=201, tags=TAG)
async def clone_scenario(sc_id: str) -> m.CloneResult:
    src = await repo.require_sc(sc_id)
    doc = copy.deepcopy({k: v for k, v in src.items() if k not in ("id", "version", "created_at", "updated_at")})
    user = current_user()
    doc.update({"owner": user.id, "owner_name": user.name, "title": f"{src.get('title') or '시나리오'} 사본", "usages": [],
                "generation": None, "active_job": None, "images_job": None, "edit": {"undo": [], "redo": [], "changes": 0},
                "saved_version": 0, "dirty": True, "created_at": now_iso()})
    if doc.get("status") in ("generating", "failed"):
        doc["status"] = "draft"
        doc["step"] = 3
    idmap: dict[str, str] = {}
    for s in doc.get("scenes") or []:
        new = new_id("scs")
        idmap[s["id"]] = new
        s["id"] = new
        s["image_request_id"] = None
        s["image_job"] = None
    new_sc = service.new_scenario_id()
    stored = await repo.create_sc(new_sc, doc)
    await service.register(stored)
    return m.CloneResult(id=new_sc, route=service.route_of(stored))


# ── 저장 · 버전 ─────────────────────────────────────────────

@router.post("/scenarios/{sc_id}:save", response_model=m.SaveResult, tags=TAG)
async def save_scenario(sc_id: str) -> m.SaveResult:
    doc = await repo.require_sc(sc_id)
    if not doc.get("dirty") and doc.get("saved_version"):
        return m.SaveResult(version=int(doc["saved_version"]), created=False)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["saved_version"] = int(d.get("saved_version") or 0) + 1
        d["dirty"] = False
        d["last_saved_at"] = now_iso()
        return d
    doc = await repo.update(sc_id, fn)
    snap = {k: v for k, v in doc.items() if k != "edit"}
    await repo.put_version(sc_id, int(doc["saved_version"]), snap, "저장", current_user().id)
    await service.register(doc)
    return m.SaveResult(version=int(doc["saved_version"]), created=True)


@router.get("/scenarios/{sc_id}/versions", response_model=m.VersionList, tags=TAG)
async def list_versions(sc_id: str) -> m.VersionList:
    await repo.require_sc(sc_id)
    items = await repo.list_versions(sc_id)
    return m.VersionList(items=[m.SavedVersion(n=v["n"], note=v.get("note") or "", created_at=v.get("created_at") or "",
                                               author=v.get("author")) for v in items])


@router.post("/scenarios/{sc_id}/versions/{n}/restore", response_model=m.Scenario, tags=TAG)
async def restore_version(sc_id: str, n: int) -> m.Scenario:
    v = await repo.get_version(sc_id, n)
    if v is None:
        raise ApiError(404, "NOT_FOUND", f"저장 버전 v{n}을(를) 찾을 수 없어요")
    snap = v.get("snapshot") or {}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.require_editable(d)
        for k in ("title", "type", "slots", "roles", "scenes", "solution_picks", "product_picks", "raw_text", "characters", "needs",
                  "space_keys", "spaces", "birdseye_link"):
            if k in snap:
                d[k] = copy.deepcopy(snap[k])
        d["status"] = snap.get("status") or d.get("status")
        d["step"] = snap.get("step") or d.get("step")
        d["dirty"] = True
        return d
    doc = await repo.update(sc_id, fn)
    await service.register(doc)
    return m.Scenario(**service.to_scenario(doc))


# ── 조감도 변경 반영(SC1B 변경 반영 모드) ──────────────────────────

async def _resync(doc: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """연결 시점 존 스냅숏(birdseye_link.zones) ↔ 지금 handoff. 스냅숏이 없으면(옛 문서) 장면 제품과 비교한다."""
    link = doc.get("birdseye_link") or {}
    if not link.get("birdseye_id"):
        raise ApiError(400, "NO_BIRDSEYE_LINK", "연결된 조감도가 없어요")
    h = await be.handoff(link["birdseye_id"])
    if not h:
        raise ApiError(503, "BIRDSEYE_UNAVAILABLE", "조감도를 읽지 못했어요. 잠시 후 다시 시도해 주세요.")
    zones = be.zones_of(h)
    by_id = {z["id"]: z for z in zones}
    linked = list(link.get("zone_ids") or [])
    snap = link.get("zones") or {}
    diffs: list[dict[str, Any]] = []
    scene_by_zone = {(s.get("zone_ref") or {}).get("zone_id"): s for s in doc.get("scenes") or [] if s.get("zone_ref")}
    zones_changed = 0
    products_changed = 0
    for zid in linked:
        z = by_id.get(zid)
        sc = scene_by_zone.get(zid)
        old_z = snap.get(zid)
        if z is None:
            diffs.append({"zone_id": zid, "n": (old_z or {}).get("n") or ((sc or {}).get("zone_ref") or {}).get("n"),
                          "name": (old_z or {}).get("name") or ((sc or {}).get("zone_ref") or {}).get("name") or "", "change": "removed",
                          "products_changed": False})
            zones_changed += 1
            continue
        new = sorted(be.product_sig(p) for p in z["products"])
        if old_z is not None:
            old = sorted(old_z.get("products") or [])
            place_changed = (old_z.get("name") or "") != z["name"]
        else:
            old = sorted(be.product_sig(p) for p in (sc or {}).get("products") or [])
            place_changed = bool(sc) and (sc.get("place") or "") != z["name"]
        p_changed = old != new
        if p_changed:
            products_changed += 1
        if p_changed or place_changed:
            zones_changed += 1
        diffs.append({"zone_id": zid, "n": z["n"], "name": z["name"], "change": "changed" if (p_changed or place_changed) else "same",
                      "products_changed": p_changed})
    for z in zones:
        if z["id"] not in linked and be.zone_state(z) != "empty":
            diffs.append({"zone_id": z["id"], "n": z["n"], "name": z["name"], "change": "new", "products_changed": False})
            zones_changed += 1
    return h, zones, diffs + [{"_summary": {"zones_changed": zones_changed, "products_changed": products_changed}}]


@router.post("/scenarios/{sc_id}/birdseye:resync", response_model=m.ResyncResult, tags=TAG)
async def birdseye_resync(sc_id: str, body: m.ResyncRequest) -> m.ResyncResult:
    doc = await repo.require_sc(sc_id)
    h, zones, raw = await _resync(doc)
    summary = raw[-1]["_summary"]
    diffs = raw[:-1]
    text = f"존 {summary['zones_changed']}개 바뀜 · 제품 {summary['products_changed']}개 바뀜"
    if not body.apply:
        return m.ResyncResult(diff=summary, zones=[m.ZoneDiff(**x) for x in diffs], summary=text, applied=False)
    by_id = {z["id"]: z for z in zones}
    changed_zones = {x["zone_id"] for x in diffs if x["change"] == "changed"}
    updated: list[str] = []

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        updated.clear()
        lk = d.get("birdseye_link") or {}
        snap = lk.get("zones") or {}
        for s in d.get("scenes") or []:
            zr = s.get("zone_ref") or {}
            z = by_id.get(zr.get("zone_id"))
            if not z or zr.get("zone_id") not in changed_zones:
                continue
            new_products = [{"ref": (f"kb:family:{x['family_id']}" if x.get("family_id") else None), "family_id": x.get("family_id"),
                             "model_code": x.get("model_code"), "short": x.get("short") or x.get("label"), "label": x.get("label"),
                             "qty": x.get("qty"), "is_new": False} for x in z["products"]]
            old_sigs = set((snap.get(z["id"]) or {}).get("products") or [])
            # 존에서 온 제품만 바꾸고 사용자가 장면에 더한 제품은 둔다(스냅숏이 없으면 통째로)
            kept = [p for p in s.get("products") or [] if snap and be.product_sig(p) not in old_sigs
                    and not any(be.product_sig(p).split("×")[0] == be.product_sig(n).split("×")[0] for n in new_products)]
            changed = sorted(be.product_sig(p) for p in s.get("products") or []) != sorted(be.product_sig(p) for p in [*new_products, *kept])
            s["place"] = z["name"]
            zr.update({"name": z["name"], "n": z["n"], "u": z.get("u"), "v": z.get("v")})
            s["zone_ref"] = zr
            if changed:
                s["products"] = [*new_products, *kept]
                s["story_check"] = True
                if s.get("image"):
                    s["image_stale_forced"] = True
            updated.append(s["id"])
        lk["linked_version"] = h.get("version")
        lk["zones_hash"] = be.zones_hash(zones)
        lk["zones"] = be.zone_snapshot(zones)
        lk["changed"] = None
        d["birdseye_link"] = lk
        d["dirty"] = True
        return d
    doc = await repo.update(sc_id, fn)
    be.clear_cache()
    await service.register(doc)
    return m.ResyncResult(diff=summary, zones=[m.ZoneDiff(**x) for x in diffs], summary=text, applied=True, updated_scene_ids=list(updated))


# ── 시드 · 사전 ─────────────────────────────────────────────

@router.get("/industries", response_model=m.IndustryList, tags=["catalog"])
async def industries(project_id: str | None = None) -> m.IndustryList:
    items = []
    for d in seed.industries():
        presets = [m.Preset(t=p["title"], f=" → ".join(p["flow"]), r=" · ".join(p["roles"]), flow=p["flow"], roles=p["roles"])
                   for p in d["presets"]]
        items.append(m.IndustryTemplate(code=d["code"], name=d["name"], short=d["short"], spaces=d["spaces"], presets=presets,
                                        needs=d["needs"], used=d["used"], space_line=" · ".join(d["spaces"]),
                                        preset_line=" · ".join(p["title"] for p in d["presets"]), used_line=" · ".join(d["used"])))
    default = "FB"
    if project_id:
        pc = await service.project_context(project_id)
        default = pc.get("industry_code") or "FB"
    return m.IndustryList(items=items, default_code=default)


@router.get("/skeletons", response_model=m.SkeletonList, tags=["catalog"])
async def skeletons(industry: str | None = None) -> m.SkeletonList:
    return m.SkeletonList(items=[m.Skeleton(**x) for x in seed.skeletons(industry)])


@router.get("/solution-actions", response_model=m.ActionList, tags=["catalog"])
async def solution_actions(solution_ids: str | None = None) -> m.ActionList:
    ids = [x for x in (solution_ids or "").split(",") if x]
    out = []
    for s in seed.solutions():
        if ids and s["id"] not in ids:
            continue
        for a in s["actions"]:
            out.append(m.ActionItem(solution_id=s["id"], solution_name=s["name"], action_code=a["code"], label=a["label"], benefit=a["benefit"]))
    return m.ActionList(items=out)


@router.get("/birdseye-options", response_model=m.BirdseyeOptions, tags=["birdseye"])
async def birdseye_options() -> m.BirdseyeOptions:
    """SC1 「조감도 작업 {n}개에서 고르기」 · SC1B 「조감도 작업」 목록(조감도 서비스 목록을 칩 표시용으로)."""
    items, ok = await be.list_birdseyes()
    out = [m.BirdseyeOption(id=x["id"], title=x["title"], zone_count=x["zone_count"], label=f"{x['title']} · 존 {x['zone_count']}")
           for x in items]
    return m.BirdseyeOptions(items=out, count=len(out), available=ok)


DEFAULT_AXES = ["방문객 동선", "매장 하루", "런칭 이벤트 당일"]


@router.get("/birdseye-options/{be_id}", response_model=m.BirdseyePreview, tags=["birdseye"])
async def birdseye_preview(be_id: str, scenario_id: str | None = None) -> m.BirdseyePreview:
    """SC1B: 존 행(제품 · 가구만 · 없음 → 기본 포함/제외) · 평면 미리보기 · 시나리오 축 3(LLM, 첫째 기본) · 동선 순서."""
    h = await be.handoff(be_id)
    if not h:
        raise ApiError(503, "BIRDSEYE_UNAVAILABLE", "조감도를 읽지 못했어요. 잠시 후 다시 시도해 주세요.")
    zones = be.zones_of(h)
    resync = None
    change: dict[str, str] = {}
    if scenario_id:
        doc = await repo.require_sc(scenario_id)
        _, _, raw = await _resync(doc)
        summary = raw[-1]["_summary"]
        diffs = raw[:-1]
        change = {x["zone_id"]: x["change"] for x in diffs}
        resync = m.ResyncResult(diff=summary, zones=[m.ZoneDiff(**x) for x in diffs],
                                summary=f"존 {summary['zones_changed']}개 바뀜 · 제품 {summary['products_changed']}개 바뀜")
    rows = []
    for z in zones:
        st = be.zone_state(z)
        rows.append(m.ZoneRow(id=z["id"], n=z["n"], name=z["name"], short_name=z["short_name"], sub=be.zone_sub(z), state=st,  # type: ignore[arg-type]
                              included=st != "empty", products=z["products"], change=change.get(z["id"]), u=z.get("u"), v=z.get("v")))
    order = [z["id"] for z in sorted(zones, key=lambda z: (z.get("path_order") or z["n"], z["n"])) if be.zone_state(z) != "empty"]
    ind = seed.industry_by_name((h.get("customer") or {}).get("industry") if isinstance(h.get("customer"), dict) else None)
    res = await llm.try_json("sc.axes", prompts.axes(h.get("title") or "", zones, ind["name"] if ind else "미정"), prompts.AxesOut,
                             timeout=8, confidential=False)
    axes = [a.strip() for a in (res.data.get("axes") if res else []) or [] if a and a.strip()][:3]
    for a in DEFAULT_AXES:
        if len(axes) >= 3:
            break
        if a not in axes:
            axes.append(a)
    return m.BirdseyePreview(birdseye_id=be_id, title=h.get("title") or "조감도", version=h.get("version"), zones=rows, axes=axes,
                             plan=be.plan_preview(h, zones), order=order, resync=resync)


# ── 끌어오기(SC2 드롭) ──────────────────────────────────────

class ImportRequest(BaseModel):
    feature: Literal["birdseye", "storyboard", "BE", "SB"]
    ref: str


class ImportResult(BaseModel):
    append_text: str
    customer_name: str | None = None
    birdseye_link: m.BirdseyeLink | None = None


@router.post("/scenarios/{sc_id}/imports", response_model=ImportResult, tags=TAG)
async def import_work(sc_id: str, body: ImportRequest) -> ImportResult:
    """사이드바 작업 항목 끌어오기: 조감도 → handoff 공간 · 제품 「[공간] …」 줄 + birdseye_link(연결 유지 끔), Storyboard → 고객 · 공간 줄."""
    ref = body.ref.split(":")[-1]
    doc = await repo.require_sc(sc_id)
    lines: list[str] = []
    customer = None
    link = None
    if body.feature in ("birdseye", "BE"):
        h = await be.handoff(ref)
        if not h:
            raise ApiError(503, "BIRDSEYE_UNAVAILABLE", "조감도를 읽지 못했어요. 잠시 후 다시 시도해 주세요.")
        zones = be.zones_of(h)
        for z in zones:
            prod = be.product_line(z["products"])
            lines.append(f"[공간] {z['name']}" + (f" — {prod}" if prod else ""))
        customer = h.get("customer") if isinstance(h.get("customer"), str) else (h.get("customer") or {}).get("name")
        link = {"birdseye_id": ref, "title": h.get("title") or "조감도", "linked_version": h.get("version"), "keep_link": False,
                "changed": None, "zone_ids": [], "order": []}
    else:
        sb = await service.storyboard_context(ref)
        lines = sb.get("space_lines") or []
        customer = sb.get("customer")
        if customer:
            lines.insert(0, f"[고객] {customer}")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        if customer and not d.get("customer_name"):
            d["customer_name"] = customer
        if link and not (d.get("birdseye_link") or {}).get("keep_link"):
            d["birdseye_link"] = link
        return d
    await repo.update(doc["id"], fn)
    return ImportResult(append_text="\n".join(lines), customer_name=customer, birdseye_link=m.BirdseyeLink(**link) if link else None)
