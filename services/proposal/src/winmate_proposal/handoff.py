"""다른 기능의 넘김 묶음 가져오기 · 정규화(§8.0 ProposalHandoff v1) · 넘김 확인(ack) · 사용 등록.

생산 기능마다 경로 · 모양이 조금씩 다르다. 모두 하나의 스냅숏 모양으로 바꾼다:
  {source, target, customer, rq_ref, items[], facts[], assets[], spaces[], solutions[], products[], key_messages[], strategy, live_link,
   handoff_id, kind}
- storyboard · mi · competitor · spec: `GET …/proposal-handoff`(v1) — 허브 Storyboard(`SB-nn`)는 `GET /v1/flows/{id}` → hub.snapshot
- vp: `GET /v1/handoffs/{vho}`(넘김 기록) 또는 `GET /v1/vps/{id}/package?proposal_type=` → Package(sheets)
- birdseye: `GET /v1/birdseyes/{id}/handoff`(cuts · zones · quantities · sheet_map)
- scenario: `GET /v1/scenarios/{id}/handoff`(scenes · solutions · sheet_plan)
- requirements: 저장 버전 스냅숏(고객 · 요구사항)
- image: `GET /v1/images/{id}` · `GET /v1/versions/{id}`
"""
from __future__ import annotations

import logging
import re
from typing import Any

from . import clients, defs, hub

log = logging.getLogger("winmate.proposal.handoff")


def _v1(raw: dict[str, Any], feature: str) -> dict[str, Any]:
    src = dict(raw.get("source") or {})
    src["feature"] = feature
    items = []
    for it in raw.get("items") or []:
        x = dict(it)
        x["sheet_role"] = (x.get("sheet_role") or "").upper()
        if x.get("solution_code"):
            x["solution_code"] = defs.solution_code_of(x["solution_code"]) or x["solution_code"]
        items.append(x)
    snap = {"kind": "v1", "source": src, "target": raw.get("target") or {}, "customer": raw.get("customer"), "rq_ref": raw.get("rq_ref"),
            "items": items, "facts": raw.get("facts") or [], "assets": raw.get("assets") or [], "live_link": bool(raw.get("live_link")),
            "key_messages": raw.get("key_messages") or [], "strategy": raw.get("strategy")}
    # 공간(스토리보드 Part 2 · 시나리오) · 제품(스펙 열)
    spaces = []
    for it in items:
        rk = it.get("repeat_key") or {}
        if rk.get("kind") == "space" and rk.get("label"):
            prods = [{"name": p, "model": p} if isinstance(p, str) else p for p in (it.get("content") or {}).get("products") or []]
            spaces.append({"key": rk.get("ref") or rk["label"], "name": rk["label"], "products": prods})
    if spaces and feature in ("scenario", "birdseye"):
        snap["spaces"] = spaces
    if feature == "spec":
        prods = []
        for it in items:
            for col in (it.get("content") or {}).get("columns") or []:
                if isinstance(col, dict) and col.get("role", "proposed") == "proposed":
                    prods.append({"name": col.get("label"), "model": col.get("label"), "ref": col.get("model_ref")})
        snap["products"] = prods
    return snap


def _vp_package(raw: dict[str, Any], ref_id: str, title: str = "") -> dict[str, Any]:
    pkg = raw.get("package") or raw
    items = []
    for i, sh in enumerate(pkg.get("sheets") or []):
        role = (sh.get("role") or "").upper()
        if role in ("", "REF"):
            continue
        lay = sh.get("layout") or {}
        code = lay.get("code") if isinstance(lay, dict) else str(lay)
        items.append({"key": f"vp:{i}:{role}", "label": sh.get("title") or defs.ROLES.get(role, {}).get("name", role), "from_label": "Value Props",
                      "sheet_role": role, "sheet_title": sh.get("title"), "template_hint": {"code": code, "name": (lay or {}).get("name", "")} if code else None,
                      "status": "ok", "status_label": "그대로 들어가요", "include_default": True, "content": sh.get("content") or {},
                      "sources": [{"kind": "vp", "ref": ref_id, "label": "Value Props"}], "speaker_notes": sh.get("speaker_notes"),
                      "pinned": bool(sh.get("pinned"))})
    src = {"feature": "vp", "ref_id": raw.get("vp_id") or ref_id, "version": raw.get("vp_version") or 0, "title": title or "Value Props",
           "updated_at": raw.get("updated_at") or "", "route": f"/vp/{raw.get('vp_id') or ref_id}"}
    return {"kind": "vp_package", "source": src, "target": {"proposal_type": pkg.get("proposal_type")}, "items": items, "facts": [],
            "assets": [], "customer": None, "rq_ref": None, "footer": pkg.get("sources_footer")}


def _birdseye(raw: dict[str, Any], ref_id: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    smap = {m.get("from"): m for m in raw.get("sheet_map") or [] if isinstance(m, dict)}
    cuts = raw.get("cuts") or []
    def img_of(cut: dict[str, Any] | None) -> dict[str, Any] | None:
        if not cut:
            return None
        rends = cut.get("renditions") or []
        fid = cut.get("file_id") or next((r.get("file_id") for r in rends if r.get("file_id")), None)
        return {"kind": "image_job", "id": cut.get("image_version_id") or cut.get("cut_id"), "file_id": fid, "rights": "generated",
                "caption_rule": "생성 이미지", "label": cut.get("label")}
    main = next((c for c in cuts if not c.get("before")), cuts[0] if cuts else None)
    if main:
        m = smap.get("cut") or smap.get(main.get("cut_id")) or {}
        items.append({"key": f"cut:{main.get('cut_id')}", "label": main.get("label") or "공간 전경", "sheet_role": "BV", "sheet_title": "공간 전경",
                      "template_hint": {"code": m.get("code") or "BV-A", "name": ""}, "status": "ok", "status_label": "그대로 들어가요",
                      "include_default": True, "content": {"title": raw.get("title"), "images": [img_of(main)],
                                                           "caption": main.get("label")}, "sources": []})
    for comp in raw.get("comparisons") or []:
        items.append({"key": f"cmp:{comp.get('kind')}", "label": "도입 전 / 후" if comp.get("kind") == "before_after" else "주간 / 야간",
                      "sheet_role": "BV", "sheet_title": "두 시점 비교", "template_hint": {"code": "BV-B", "name": "두 시점 비교"}, "status": "add",
                      "status_label": "섹션에 없는 시트 · 추가", "include_default": False,
                      "content": {"images": [x for x in (img_of(comp.get("left")), img_of(comp.get("right"))) if x]}, "sources": []})
    zones = raw.get("zones") or {}
    pts = zones.get("points") or []
    if pts:
        zcut = next((c for c in cuts if c.get("cut_id") == zones.get("cut_id")), main)
        items.append({"key": "zones", "label": f"존 포인트 {len(pts)}곳", "sheet_role": "ZP", "sheet_title": "존별 포인트",
                      "template_hint": {"code": zones.get("layout") or "ZP-A", "name": ""}, "status": "ok", "status_label": "그대로 들어가요",
                      "include_default": True,
                      "content": {"images": [img_of(zcut)] if zcut else [], "pins": [{"no": p.get("n"), "title": p.get("name"), "body": p.get("text"),
                                                                                      "x": p.get("u"), "y": p.get("v")} for p in pts]},
                      "sources": []})
    spaces: list[dict[str, Any]] = []
    products: list[dict[str, Any]] = []
    for q in raw.get("quantities") or []:
        space = q.get("at") or q.get("space") or q.get("zone") or q.get("space_name")
        model = q.get("model_code") or q.get("model") or q.get("label") or q.get("name")
        if space and not any(s["name"] == space for s in spaces):
            spaces.append({"key": q.get("space_key") or space, "name": space, "products": []})
        pr = {"name": q.get("name") or q.get("label") or model, "model": model, "qty": q.get("qty"), "family_id": q.get("family_id"),
              "qty_confirm": bool(q.get("confirm"))}
        products.append({**pr, "space_key": q.get("space_key") or space})
        for s in spaces:
            if s["name"] == space:
                s["products"].append(pr)
    if not spaces:
        for p in pts:
            prods = [{"name": x.get("label"), "model": x.get("model_code") or x.get("short") or x.get("label"), "qty": x.get("qty"),
                      "family_id": x.get("family_id")} for x in p.get("products") or []]
            spaces.append({"key": p.get("zone_id") or f"zone{p.get('n')}", "name": p.get("name") or f"존 {p.get('n')}", "products": prods})
            products += [{**x, "space_key": p.get("zone_id") or f"zone{p.get('n')}"} for x in prods]
    if raw.get("quantities"):
        cols = ["공간", "제품", "수량"]
        items.append({"key": "quantities", "label": "제품 수량표", "sheet_role": "SM", "sheet_title": "공간 맵",
                      "template_hint": {"code": "SM-B", "name": "공간 × 제품 수량표"}, "status": "ok", "status_label": "그대로 들어가요",
                      "include_default": True, "target_section": "spaceProducts",
                      "content": {"table": {"columns": cols, "rows": [[x.get("space_key") or "", x.get("name") or "",
                                                                       ("[확인 필요]" if x.get("qty_confirm") else str(x.get("qty") or ""))]
                                                                      for x in products]}},
                      "sources": []})
    src = {"feature": "birdseye", "ref_id": raw.get("birdseye_id") or ref_id, "version": raw.get("version") or 0,
           "title": raw.get("title") or "공간 조감도", "updated_at": raw.get("updated_at") or "",
           "route": raw.get("route") or f"/birdseye/{raw.get('birdseye_id') or ref_id}"}
    return {"kind": "birdseye_bundle", "source": src, "target": {}, "items": items, "facts": [], "assets": [], "spaces": spaces[:5],
            "products": products, "customer": {"name": raw["customer"]} if isinstance(raw.get("customer"), str) else raw.get("customer")}


def _scenario(raw: dict[str, Any], ref_id: str) -> dict[str, Any]:
    scenes = raw.get("scenes") or []
    sols = [{"id": s.get("id"), "name": s.get("name"), "code": defs.solution_code_of(s.get("id"), s.get("name"))} for s in raw.get("solutions") or []]
    by_space: dict[str, dict[str, Any]] = {}
    for sc in scenes:
        key = sc.get("space_key") or sc.get("place") or "space"
        sp = by_space.setdefault(key, {"key": key, "name": sc.get("place") or key, "scenes": [], "products": []})
        sp["scenes"].append(sc)
        for pr in sc.get("products") or []:
            name = pr.get("label") if isinstance(pr, dict) else pr
            if name and not any(x["name"] == name for x in sp["products"]):
                sp["products"].append({"name": name, "model": name})
    items: list[dict[str, Any]] = []
    spaces = list(by_space.values())
    if spaces and sols:
        cols = ["공간", *[s["name"] for s in sols]]
        rows = []
        for sp in spaces:
            cells = []
            for s in sols:
                acts = [a.get("action") or a.get("label") for sc in sp["scenes"] for a in sc.get("solutions") or [] if a.get("id") == s["id"]]
                cells.append(" · ".join(x for x in acts if x)[:40] or "—")
            rows.append([sp["name"], *cells])
        items.append({"key": "matrix", "label": f"공간 {len(spaces)} × 솔루션 {len(sols)}", "sheet_role": "VM", "sheet_title": "공간 × 솔루션 맵",
                      "template_hint": {"code": "VM-A", "name": ""}, "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
                      "content": {"table": {"columns": cols, "rows": rows}}, "sources": [], "target_section": "spaceScenario"})
    for sp in spaces:
        items.append({"key": f"space:{sp['key']}", "label": sp["name"], "sheet_role": "SS", "sheet_title": sp["name"],
                      "repeat_key": {"kind": "space", "ref": sp["key"], "label": sp["name"]}, "template_hint": None, "status": "ok",
                      "status_label": "그대로 들어가요", "include_default": True,
                      "content": {"scenes": [{"time": sc.get("time"), "title": sc.get("title"), "story": sc.get("story"),
                                              "image": (sc.get("image") or {})} for sc in sp["scenes"]]}, "sources": []})
    for s in sols:
        if not s.get("code"):
            continue
        scs = [sc for sc in scenes if any(a.get("id") == s["id"] for a in sc.get("solutions") or [])]
        items.append({"key": f"sol:{s['code']}", "label": f"{s['name']} 장면 {len(scs)}", "sheet_role": "SXS", "solution_code": s["code"],
                      "sheet_title": f"{s['name']} · 공간 시나리오", "template_hint": None, "status": "ok", "status_label": "그대로 들어가요",
                      "include_default": True, "target_section": "solution",
                      "content": {"scenes": [{"time": sc.get("time"), "title": sc.get("title"), "story": sc.get("story")} for sc in scs]},
                      "sources": []})
    src = {"feature": "scenario", "ref_id": raw.get("scenario_id") or ref_id, "version": raw.get("version") or 0,
           "title": raw.get("title") or "공간 시나리오", "updated_at": raw.get("updated_at") or "", "route": f"/scenario/{raw.get('scenario_id') or ref_id}"}
    facts = [{"key": f"sc:{c.get('token')}", "label": c.get("near_text") or "수치", "status": "placeholder", "placeholder": "[00]"}
             for c in raw.get("confirm_items") or [] if c.get("token")]
    return {"kind": "scenario_bundle", "source": src, "target": {}, "items": items, "facts": facts, "assets": [], "spaces": spaces[:5],
            "solutions": sols, "customer": {"name": raw["customer"]} if isinstance(raw.get("customer"), str) else raw.get("customer"),
            "sheet_plan": raw.get("sheet_plan")}


async def fetch(feature: str, ref_id: str | None, *, proposal_type: str | None, section: str | None = None,
                handoff_id: str | None = None, version: int | None = None) -> dict[str, Any] | None:
    """정규화한 스냅숏 또는 None(서비스가 없거나 실패)."""
    feature = defs.norm_feature(feature) or feature
    ptype = proposal_type or "standard"
    try:
        if feature == "storyboard" and hub.is_hub_id(ref_id):
            # 새 콘텐츠 흐름의 Storyboard 허브(SB-nn) — flow.json stages 를 스냅숏으로(hub.py)
            return await hub.fetch(str(ref_id).strip(), ptype)
        if feature == "storyboard":
            sec = {"spaceScenario": "space_scenario", "spaceProducts": "space_products"}.get(section or "", section)
            raw = await clients.call("storyboard", "GET", f"/v1/storyboards/{ref_id}/proposal-handoff",
                                     params={"type": ptype, "section": sec if sec in ("vp", "mi", "why", "space_scenario") else None})
            return _v1(raw, "storyboard") if raw else None
        if feature == "mi":
            sec = section if section in ("mi", "bigMi", "why") else ("bigMi" if ptype == "solution" else "mi")
            raw = await clients.call("mi", "GET", f"/v1/analyses/{ref_id}/proposal-handoff",
                                     params={"type": ptype, "section": sec, "handoff_id": handoff_id})
            return _v1(raw, "mi") if raw else None
        if feature == "competitor":
            raw = await clients.call("competitor", "GET", f"/v1/analyses/{ref_id}/proposal-handoff",
                                     params={"type": ptype, "section": "why", "handoff_id": handoff_id})
            return _v1(raw, "competitor") if raw else None
        if feature == "spec":
            sid = ref_id
            if handoff_id and (not sid or not str(sid).startswith("sp_")):
                h = await clients.call("spec", "GET", f"/v1/handoffs/{handoff_id}")
                sid = (h or {}).get("sheet_id") or sid
            if not sid:
                return None
            raw = await clients.call("spec", "GET", f"/v1/sheets/{sid}/proposal-handoff", params={"type": ptype, "section": "spec"})
            snap = _v1(raw, "spec") if raw else None
            if snap and handoff_id:
                snap["handoff_id"] = handoff_id
            return snap
        if feature == "vp":
            if handoff_id:
                raw = await clients.call("vp", "GET", f"/v1/handoffs/{handoff_id}")
                if raw:
                    vid = ref_id or raw.get("vp_id") or ""
                    # 넘김 기록에는 작업 제목이 없다 — 연결 자료 칩 「VP · {제목}」이 되도록 작업을 한 번 읽는다(통합)
                    doc = await clients.call("vp", "GET", f"/v1/vps/{vid}", quiet=True) if vid else None
                    snap = _vp_package(raw, vid, title=(doc or {}).get("title") or "")
                    if doc and doc.get("updated_at"):
                        snap["source"]["updated_at"] = doc["updated_at"]
                    snap["handoff_id"] = handoff_id
                    return snap
            if not ref_id:
                return None
            if clients._has_path("vp", "GET", f"/v1/vps/{ref_id}/proposal-handoff"):
                raw = await clients.call("vp", "GET", f"/v1/vps/{ref_id}/proposal-handoff", params={"type": ptype, "section": section or "vp"}, quiet=True)
                if raw and raw.get("items") is not None and raw.get("source"):
                    return _v1(raw, "vp")
            raw = await clients.call("vp", "GET", f"/v1/vps/{ref_id}/package", params={"proposal_type": ptype})
            if raw and raw.get("items") is not None and raw.get("source"):
                return _v1(raw, "vp")
            return _vp_package(raw, ref_id) if raw else None
        if feature == "birdseye":
            raw = await clients.call("birdseye", "GET", f"/v1/birdseyes/{ref_id}/handoff", params={"version": version})
            if raw and raw.get("items") is not None and raw.get("source"):
                return _v1(raw, "birdseye")
            snap = _birdseye(raw, ref_id or "") if raw else None
            # 섹션별 v1 반입(조감도가 매핑의 주인) — 있으면 그 섹션 항목을 v1 것으로(공간 · 수량은 묶음에서)
            if snap and clients._has_path("birdseye", "GET", f"/v1/birdseyes/{ref_id}/proposal-handoff"):
                secs = [x for x in (section,) if x] or (["spaceScenario"] if ptype == "solution" else
                                                        ["spaceProducts"] if ptype == "quickwin" else ["birdseye", "spaceProducts"])
                for sec in secs:
                    v1 = await clients.call("birdseye", "GET", f"/v1/birdseyes/{ref_id}/proposal-handoff",
                                            params={"type": ptype, "section": sec}, quiet=True)
                    if not v1 or not v1.get("items"):
                        continue
                    norm = _v1(v1, "birdseye")
                    keep = [it for it in snap["items"] if it.get("target_section") not in (sec, None)]
                    snap["items"] = keep + [{**it, "target_section": it.get("target_section") or sec} for it in norm.get("items") or []]
                    snap["facts"] = (snap.get("facts") or []) + (norm.get("facts") or [])
                    snap["assets"] = (snap.get("assets") or []) + (norm.get("assets") or [])
            return snap
        if feature == "scenario":
            raw = await clients.call("scenario", "GET", f"/v1/scenarios/{ref_id}/handoff", params={"version": version})
            if raw and raw.get("items") is not None and raw.get("source"):
                return _v1(raw, "scenario")
            snap = _scenario(raw, ref_id or "") if raw else None
            # 섹션별 v1 반입(시나리오가 매핑의 주인, §7.0-1) — 있으면 그 섹션 항목을 v1 것으로
            if snap and clients._has_path("scenario", "GET", f"/v1/scenarios/{ref_id}/proposal-handoff"):
                secs = [x for x in (section,) if x] or (["spaceScenario", "solution"] if ptype == "solution" else ["solution"])
                for sec in secs:
                    v1 = await clients.call("scenario", "GET", f"/v1/scenarios/{ref_id}/proposal-handoff",
                                            params={"type": ptype, "section": sec, "version": version}, quiet=True)
                    if not v1 or not v1.get("items"):
                        continue
                    norm = _v1(v1, "scenario")
                    keep = [it for it in snap["items"] if it.get("target_section") not in (sec, None)]
                    snap["items"] = keep + [{**it, "target_section": it.get("target_section") or sec} for it in norm.get("items") or []]
                    snap["facts"] = (snap.get("facts") or []) + (norm.get("facts") or [])
                    snap["assets"] = (snap.get("assets") or []) + (norm.get("assets") or [])
                    snap["target"] = norm.get("target") or snap.get("target")
            return snap
        if feature == "requirements":
            raw = await clients.call("requirements", "GET", f"/v1/requirements/{ref_id}/versions/{version or 'latest'}")
            if not raw:
                return None
            snap = raw.get("snapshot") or {}
            form = snap.get("form") or {}
            cust = {"name": raw.get("customer_name") or form.get("customer_name"), "decision_makers": raw.get("final_audience")}
            return {"kind": "requirements", "source": {"feature": "requirements", "ref_id": ref_id, "version": raw.get("version"),
                                                       "title": raw.get("title") or "고객 요구사항", "updated_at": raw.get("created_at") or "",
                                                       "route": f"/requirements/{ref_id}"},
                    "customer": cust, "rq_ref": {"rq_id": ref_id, "version": raw.get("version")}, "items": [], "facts": [], "assets": [],
                    "project_name": raw.get("project_name")}
        if feature == "image":
            img = await clients.call("image", "GET", f"/v1/images/{ref_id}") if ref_id else None
            if not img and version:
                ver = await clients.call("image", "GET", f"/v1/versions/{version}")
                if ver:
                    img = await clients.call("image", "GET", f"/v1/images/{ver.get('image_id')}")
            if not img:
                return None
            cur = img.get("current") or {}
            asset = {"kind": "image_job", "id": img["id"], "version_id": img.get("current_version_id"), "file_id": img.get("file_id"),
                     "rights": img.get("rights") or "generated", "caption_rule": img.get("caption_rule") or "생성 이미지", "label": img.get("title")}
            return {"kind": "image", "source": {"feature": "image", "ref_id": img["id"], "version": cur.get("n") or 1, "title": img.get("title") or "이미지",
                                                "updated_at": img.get("created_at") or "", "route": f"/image/w/{img.get('work_id')}/result"},
                    "items": [], "facts": [], "assets": [asset], "scene": img.get("scene") or {}, "customer": None}
    except Exception as exc:  # noqa: BLE001
        log.warning("handoff %s %s 실패: %s", feature, ref_id, exc)
        return None
    return None


async def ack(feature: str, handoff_id: str | None, *, result: str, proposal: dict[str, Any], sheet_ids: list[str],
              section_key: str | None) -> None:
    if not handoff_id:
        return
    feature = defs.norm_feature(feature) or feature
    if feature == "spec" and handoff_id.startswith("sho_"):
        keys = (defs.TYPES.get(proposal.get("type") or "standard") or {}).get("sections") or []
        await clients.call("spec", "POST", f"/v1/handoffs/{handoff_id}:ack", json={
            "result": result, "proposal_id": proposal["id"], "proposal_title": proposal.get("title") or "새 제안서",
            "section_no": f"{keys.index(section_key) + 1:02d}" if section_key in keys else None,
            "section_name": defs.SECTIONS.get(section_key or "", {}).get("name", ""), "proposal_sheet_ids": sheet_ids})
    elif feature == "vp" and handoff_id.startswith("vho_"):
        await clients.call("vp", "POST", f"/v1/handoffs/{handoff_id}:ack", json={
            "result": "applied" if result == "applied" else "needs_confirmation", "applied_sheet_ids": sheet_ids,
            "proposal_id": proposal["id"], "proposal_title": proposal.get("title") or "새 제안서"})


async def register_usage(feature: str, ref_id: str, *, proposal: dict[str, Any], label: str, version: Any = None,
                         sheet_ref: str | None = None) -> None:
    feature = defs.norm_feature(feature) or feature
    ref = sheet_ref or proposal["id"]
    title = proposal.get("title") or "새 제안서"
    if feature == "image":
        body = {"version_id": version or "", "service": "proposal", "ref": ref, "label": f"{title} › {label}"}
        if not body["version_id"]:
            img = await clients.call("image", "GET", f"/v1/images/{ref_id}", quiet=True)
            body["version_id"] = (img or {}).get("current_version_id") or ""
        if body["version_id"]:
            await clients.call("image", "POST", f"/v1/images/{ref_id}/usages", json=body, quiet=True)
    elif feature == "birdseye":
        await clients.call("birdseye", "POST", f"/v1/birdseyes/{ref_id}/usages",
                           json={"service": "proposal", "ref": ref, "label": f"{title} › {label}", "version": version}, quiet=True)
    elif feature == "scenario":
        await clients.call("scenario", "POST", f"/v1/scenarios/{ref_id}/usages",
                           json={"service": "proposal", "ref": ref, "label": f"{title} › {label}", "version": version}, quiet=True)
    elif feature == "requirements":
        await clients.call("requirements", "PUT", f"/v1/requirements/{ref_id}/links/proposal/{proposal['id']}",
                           json={"title": title, "route": f"{defs.ROUTE_BASE}/{proposal['id']}", "rq_version": int(version or 1)}, quiet=True)


async def unregister_usage(feature: str, ref_id: str, *, proposal_id: str, sheet_ref: str | None = None) -> None:
    feature = defs.norm_feature(feature) or feature
    ref = sheet_ref or proposal_id
    if feature == "image":
        await clients.call("image", "DELETE", f"/v1/images/{ref_id}/usages/proposal/{ref}", quiet=True)
    elif feature == "birdseye" and ref_id:
        await clients.call("birdseye", "DELETE", f"/v1/birdseyes/{ref_id}/usages/proposal/{ref}", quiet=True)
    elif feature == "scenario" and ref_id:
        await clients.call("scenario", "DELETE", f"/v1/scenarios/{ref_id}/usages/proposal/{ref}", quiet=True)
    elif feature == "requirements" and ref_id:
        await clients.call("requirements", "DELETE", f"/v1/requirements/{ref_id}/links/proposal/{proposal_id}", quiet=True)
    elif feature == "vp" and ref_id:
        await clients.call("vp", "POST", f"/v1/vps/{ref_id}:release-proposal", json={"proposal_id": proposal_id}, quiet=True)
    elif feature == "spec":
        # ref_id(시트)가 없으면 이 제안서와의 연결 전부(slk_) — 제안서 지우기, 있으면 그 시트만 — 반입 실행 취소
        await clients.call("spec", "DELETE", "/v1/links", params={"proposal_id": proposal_id, **({"sheet_id": ref_id} if ref_id else {})}, quiet=True)


def title_of(snap: dict[str, Any] | None, feature: str, fallback: str = "") -> str:
    t = ((snap or {}).get("source") or {}).get("title") or fallback
    short = defs.FEATURE_SHORT.get(feature, "")
    return f"{short} · {t}" if short and t and not t.startswith(short) else (t or short)


MODEL_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z]{1,2}\b")
