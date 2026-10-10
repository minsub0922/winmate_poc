"""연결 자료(linked_source, §5.4) — 만들기 · 섹션 소속 · 반입 스냅숏 · 「업데이트됨」 감지 · 고객 정보 채우기."""
from __future__ import annotations

from typing import Any

from winmate_common.ids import new_id

from . import clients, config, core, defs, handoff, hub, repo
from . import models as M


def sections_for(ln: dict[str, Any], type_: str | None) -> list[str]:
    """연결 자료가 들어가는 섹션 — 명시(section_key)가 있으면 그것, 없으면 기능별 「넣을 곳」(§10.7)."""
    if ln.get("section_key"):
        return [ln["section_key"]]
    if hub.is_hub_link(ln):
        # 허브 Storyboard — 저장된 콘텐츠(stage)마다 맞는 섹션(hub.STAGE_TARGETS)
        return hub.sections_for(ln.get("handoff"), type_)
    rule = defs.WORK_TARGETS.get(ln.get("feature") or "")
    if not rule:
        return []
    return list(rule.get(type_ or "standard") or [])


def link_label(ln: dict[str, Any]) -> str:
    f = ln.get("feature") or ""
    t = ln.get("title") or ""
    if f in ("kb_product", "kb_solution", "kb_case", "kb_image", "file"):
        return t
    short = defs.FEATURE_SHORT.get(f, "")
    return t if t.startswith(short) else f"{short} · {t}" if short else t


def view(ln: dict[str, Any]) -> M.LinkedSource:
    f = ln.get("feature") or ""
    return M.LinkedSource(
        id=ln["id"], section_key=ln.get("section_key"), feature=f, feature_label=defs.FEATURE_LABEL.get(f, f), ref_id=ln.get("ref_id") or "",
        title=ln.get("title") or "", label=link_label(ln), version_at_link=ln.get("version_at_link"), latest_version=ln.get("latest_version"),
        stale=bool(ln.get("stale")), via=ln.get("via") or "start", status=ln.get("status") or "linked",
        route=((ln.get("handoff") or {}).get("source") or {}).get("route") or ln.get("route"), created_at=ln.get("created_iso") or "")


async def links_of(pid: str, *, include_removed: bool = False, status: str | None = None) -> list[dict[str, Any]]:
    out = await repo.alist("links", {"proposal_id": pid})
    if status:
        return [x for x in out if (x.get("status") or "linked") == status]
    if not include_removed:
        out = [x for x in out if (x.get("status") or "linked") == "linked"]
    return out


async def section_links(pid: str, key: str, type_: str | None) -> list[dict[str, Any]]:
    return [ln for ln in await links_of(pid) if key in sections_for(ln, type_)]


async def add_link(pid: str, *, feature: str, ref_id: str, section_key: str | None = None, via: str = "start", version: int | None = None,
                   handoff_id: str | None = None, title: str | None = None, item: dict[str, Any] | None = None, fetch: bool = True,
                   status: str = "linked", qty: Any = None, space_key: str | None = None) -> dict[str, Any]:
    feature = defs.norm_feature(feature) or feature
    feature = defs.feature_for_ref(feature, ref_id) or feature
    p = await core.load(pid)
    snap = None
    if fetch and feature in defs.WORK_FEATURES:
        snap = await handoff.fetch(feature, ref_id, proposal_type=p.get("type"), section=section_key, handoff_id=handoff_id, version=version)
    src = (snap or {}).get("source") or {}
    if not ref_id and src.get("ref_id"):
        ref_id = str(src["ref_id"])      # 넘김 id 만 온 경우(SP4 sho_ · VP vho_) — 묶음의 원본 id
    existing = [x for x in await repo.alist("links", {"proposal_id": pid}) if x.get("feature") == feature and x.get("ref_id") == ref_id
                and (x.get("section_key") or None) == (section_key or None)]
    if existing:
        ln = existing[0]

        def fn(x: dict[str, Any]) -> None:
            x["status"] = status
            if snap:
                x["handoff"] = snap
                x["version_at_link"] = src.get("version")
                x["latest_version"] = src.get("version")
                x["source_updated_at"] = src.get("updated_at")
                x["stale"] = False
                x["title"] = src.get("title") or x.get("title")
            if handoff_id:
                x["handoff_id"] = handoff_id
        saved, _ = await repo.amutate("links", ln["id"], fn)
        return saved
    doc = {"id": new_id("lnk"), "proposal_id": pid, "section_key": section_key, "feature": feature, "ref_id": ref_id,
           "title": title or src.get("title") or ref_id, "version_at_link": src.get("version") or version, "latest_version": src.get("version") or version,
           "source_updated_at": src.get("updated_at"), "handoff": snap, "handoff_id": handoff_id, "via": via, "status": status, "stale": False,
           "item": item, "qty": qty, "space_key": space_key, "route": src.get("route"), "created_iso": config.now_iso()}
    return await repo.aput("links", doc["id"], doc)


async def refresh_snapshot(ln: dict[str, Any], p: dict[str, Any], section_key: str | None = None) -> dict[str, Any]:
    if ln.get("feature") not in defs.WORK_FEATURES:
        return ln
    snap = await handoff.fetch(ln["feature"], ln["ref_id"], proposal_type=p.get("type"), section=section_key or ln.get("section_key"),
                               handoff_id=ln.get("handoff_id"))
    if not snap:
        return ln
    src = snap.get("source") or {}

    def fn(x: dict[str, Any]) -> None:
        x["handoff"] = snap
        x["version_at_link"] = src.get("version")
        x["latest_version"] = src.get("version")
        x["source_updated_at"] = src.get("updated_at")
        x["stale"] = False
        x["title"] = src.get("title") or x.get("title")
    saved, _ = await repo.amutate("links", ln["id"], fn)
    return saved


async def apply_customer(pid: str, snap: dict[str, Any] | None, *, overwrite: bool = False) -> bool:
    """Storyboard 반입의 customer → 없으면 requirements → 그대로(§7.3). 빈 칸만 채운다."""
    if not snap:
        return False
    cust = snap.get("customer") or {}
    rq = snap.get("rq_ref")
    changed = {"v": False}

    def fn(p: dict[str, Any]) -> None:
        c = p.setdefault("customer", {})
        for k in ("name", "industry_code", "scale_text", "decision_makers"):
            v = cust.get(k)
            if v and (overwrite or not c.get(k)):
                if k == "industry_code" and v not in defs.INDUSTRIES:
                    continue
                c[k] = v
                changed["v"] = True
        if rq and rq.get("rq_id") and not p.get("rq_ref"):
            p["rq_ref"] = {"rq_id": rq["rq_id"], "version": rq.get("version")}
            changed["v"] = True
        if not p.get("title") and snap.get("project_name"):
            p["title"] = snap["project_name"]
            changed["v"] = True
    await core.mutate(pid, fn)
    return changed["v"]


async def check_stale(pid: str, ws_index: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """workspace 항목 updated_at · meta.version 으로 원 작업이 바뀌었는지(§8.0 버전 변경 감지). 바뀐 연결 목록."""
    lns = [x for x in await links_of(pid) if x.get("feature") in defs.WORK_FEATURES and x.get("feature") != "requirements"]
    if not lns:
        return []
    if ws_index is None:
        ws_index = {i["item_id"]: i for i in await clients.ws_items(owner="all", limit=100)}
    out = []
    for ln in lns:
        it = ws_index.get(ln.get("ref_id") or "")
        if not it:
            if ln.get("stale"):
                out.append(ln)
            continue
        ver = (it.get("meta") or {}).get("version")
        upd = it.get("updated_at")
        stale = False
        if isinstance(ver, int) and isinstance(ln.get("version_at_link"), int) and ver > ln["version_at_link"]:
            stale = True
        elif upd and ln.get("source_updated_at") and upd > ln["source_updated_at"] and isinstance(ver, int) is False:
            stale = bool(ln.get("handoff")) and upd[:19] > str(ln["source_updated_at"])[:19]
        if stale != bool(ln.get("stale")):
            await repo.amutate("links", ln["id"], lambda x, s=stale, v=ver: x.update({"stale": s, "latest_version": v if isinstance(v, int) else x.get("latest_version")}))
            if stale:
                p = await core.load(pid)
                for key in sections_for(ln, p.get("type")):
                    secs = await repo.alist("sections", {"proposal_id": pid, "key": key})
                    for s in secs:
                        if s.get("status") == "ready":
                            await repo.amutate("sections", s["id"], lambda x: x.update({"status": "stale"}))
        if stale:
            out.append({**ln, "stale": True})
    return out


SHELL_PREFIX = {"kb_product": "kb:model:", "kb_solution": "kb:solution:", "kb_case": "kb:case:", "kb_image": "kb:image:", "image": "img:image:"}


def shell_ref(ln: dict[str, Any]) -> str | None:
    """연결 → 셸 참조(SourceChip.ref). 반입 때 받은 참조가 있으면 그것, 없으면 기능 · id 로 만든다(작업은 workspace 항목)."""
    r = (ln.get("item") or {}).get("shell_ref")
    if r:
        return str(r)
    f, rid = ln.get("feature") or "", str(ln.get("ref_id") or "")
    if not rid or f == "file":
        return None
    if ":" in rid:
        return rid
    if f in SHELL_PREFIX:
        return SHELL_PREFIX[f] + rid
    return f"ws:item:{rid}"
