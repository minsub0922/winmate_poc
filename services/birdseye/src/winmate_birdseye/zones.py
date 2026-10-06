"""존 포인트(08-birdseye §4.12 · §6.6 · §7.10) — 군집(결정적) → 분류(제품 · 가구 = 존, 랩핑만 = 제안) → 앵커 → 컷 투영 →
문구(LLM + KB E3 근거, 수치는 [00]) → 주출입구 경로 거리 순 번호."""
from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, Field
from shapely.ops import unary_union

from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id

from . import config, draft, kbapi, llm
from . import service as svc
from . import text as T
from .engine.geometry import item_poly
from .engine.validate import GRID, Scene, _bfs, _nearest_free, _raster
from .repo import repo

LAYOUT_LABEL = {"ZP-A": "번호 콜아웃", "ZP-B": "존 확대 컷", "ZP-C": "고객 동선 따라가기"}
W_ZONES = ("조감도 위에 존 포인트 {n}곳을 찍어 두었어요. 번호를 끌어 위치를 옮기고, 빈 곳을 누르면 포인트가 추가됩니다. "
           "여기 적은 문구가 제안서 '존별 포인트' 시트에 그대로 들어가요.")


class ZoneText(BaseModel):
    cluster: str
    name: str = Field(description="존 이름 14자 이내(「쇼윈도 · 외부 노출」)")
    text: str = Field(description="포인트 문구 60자 이내, 고객 관점 한 문장, 수치는 [00]")
    needs: list[str] = Field(default_factory=list, description="요구 태그(「외부 유입」) — 입력 문장에서만")


class ZoneTexts(BaseModel):
    zones: list[ZoneText] = Field(default_factory=list)


class Rewrite(BaseModel):
    zones: list[ZoneText] = Field(default_factory=list)


# ── 군집 ─────────────────────────────────────────────────

def clusters(layout: dict[str, Any], radius: float) -> list[dict[str, Any]]:
    """묶음 → 군집: 좌석은 바라보는 디스플레이와, 근접 가구는 대상과 같이(앵커 같은 것), 랩핑은 따로, 나머지는 2.5 m 이내 병합."""
    items = [it for it in layout.get("items", []) if not it.get("unplaced")]
    by_id = {it["id"]: it for it in items}
    groups: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        groups.setdefault(it["group_id"], []).append(it)
    parent = {g: g for g in groups}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb, key=_gnum)] = min(ra, rb, key=_gnum)

    wraps = {g for g, its in groups.items() if its[0]["kind"] == "column_wrap"}
    for g, its in groups.items():
        for it in its:
            tgt = it.get("faces") or ((it.get("anchor") or {}).get("target") if (it.get("anchor") or {}).get("type") == "near" else None)
            if tgt and tgt in by_id:
                union(g, by_id[tgt]["group_id"])
            elif tgt:
                # near:<product id> — 그 제품의 묶음
                for g2, its2 in groups.items():
                    if any(x.get("ref") == tgt for x in its2):
                        union(g, g2)
    polys = {g: unary_union([item_poly(it) for it in its]) for g, its in groups.items()}
    keys = sorted([g for g in groups if g not in wraps], key=_gnum)
    changed = True
    while changed:
        changed = False
        roots: dict[str, list[str]] = {}
        for g in keys:
            roots.setdefault(find(g), []).append(g)
        rk = sorted(roots, key=_gnum)
        for i in range(len(rk)):
            for j in range(i + 1, len(rk)):
                a = unary_union([polys[g] for g in roots[rk[i]]])
                b = unary_union([polys[g] for g in roots[rk[j]]])
                if a.distance(b) <= radius + 1e-9:
                    union(rk[i], rk[j])
                    changed = True
                    break
            if changed:
                break
    out: dict[str, dict[str, Any]] = {}
    for g in sorted(groups, key=_gnum):
        r = find(g) if g not in wraps else g
        c = out.setdefault(r, {"key": r, "groups": [], "items": []})
        c["groups"].append(g)
        c["items"] += groups[g]
    res = []
    for k in sorted(out, key=_gnum):
        c = out[k]
        kinds = {it["kind"] for it in c["items"]}
        c["kind"] = "product" if "product" in kinds else ("furniture" if "furniture" in kinds else "wrap")
        xs = [it["x"] for it in c["items"]]
        ys = [it["y"] for it in c["items"]]
        zs = [float(it.get("z") or 0) + float(it.get("h") or 0) / 2 for it in c["items"]]
        c["anchor"] = [round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2), round(sum(zs) / len(zs) / 2 + 0.6, 2)]
        res.append(c)
    return res


def _gnum(g: str) -> int:
    return int(g[1:]) if g[1:].isdigit() else 10 ** 6


def path_order(space: dict[str, Any], layout: dict[str, Any], points: list[tuple[str, float, float]],
               items: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, float]:
    """주출입구 → 군집 접근점(항목 둘레 0.8 m 안의 갈 수 있는 칸 중 가장 가까운 곳) 경로 거리(m). 항목이 없으면 기준점."""
    import numpy as np
    import shapely

    sc = Scene(space, layout, config.rules())
    if sc.entrance is None:
        return {k: math.hypot(x, y) for k, x, y in points}
    free, minx, miny, W, H = _raster(sc, 0.25)
    ex, ey = sc.entrance["inside"]
    st = _nearest_free(free, int(round((ex - minx) / GRID)), int(round((ey - miny) / GRID)))
    out: dict[str, float] = {}
    if st is None:
        return {k: math.hypot(x - ex, y - ey) for k, x, y in points}
    dist, _ = _bfs(free, st)
    for k, x, y in points:
        best = None
        its = (items or {}).get(k) or []
        if its:
            region = unary_union([item_poly(it) for it in its]).buffer(0.8)
            x0, y0, x1, y1 = region.bounds
            cx0, cx1 = max(0, int((x0 - minx) / GRID)), min(W - 1, int(math.ceil((x1 - minx) / GRID)))
            cy0, cy1 = max(0, int((y0 - miny) / GRID)), min(H - 1, int(math.ceil((y1 - miny) / GRID)))
            if cx1 >= cx0 and cy1 >= cy0:
                gx, gy = np.meshgrid(np.arange(cx0, cx1 + 1), np.arange(cy0, cy1 + 1))
                inside = shapely.contains_xy(region, minx + gx * GRID, miny + gy * GRID)
                sub = dist[cy0:cy1 + 1, cx0:cx1 + 1]
                ok = inside & (sub >= 0)
                if ok.any():
                    best = float(sub[ok].min()) * GRID
        if best is None:
            cell = _nearest_free(free, int(round((x - minx) / GRID)), int(round((y - miny) / GRID)), max_r=25)
            if cell is None or dist[cell[1], cell[0]] < 0:
                best = 1e6 + math.hypot(x - ex, y - ey)
            else:
                best = float(dist[cell[1], cell[0]]) * GRID
        out[k] = round(best, 2)
    return out


# ── 문구 ─────────────────────────────────────────────────

def _role_of(c: dict[str, Any]) -> str:
    roles = [it.get("role") for it in c["items"] if it["kind"] == "product"]
    if "window_signage" in roles:
        return "window"
    if any(it.get("faces") for it in c["items"]) or "led_wall" in roles:
        return "media"
    if "interactive" in roles or any(it.get("role") == "experience_counter" for it in c["items"]):
        return "demo"
    if roles:
        return "display"
    codes = {it.get("role") for it in c["items"]}
    if "lounge_sofa_set" in codes or "table_set" in codes:
        return "lounge"
    if "info_desk" in codes:
        return "info"
    return "furniture"


def template_text(c: dict[str, Any], groups: dict[str, dict[str, Any]]) -> tuple[str, str, str]:
    """(이름, 문구, 짧은 이름) — text:template."""
    prod = next((groups[g] for g in c["groups"] if groups[g].get("kind") == "product"), None)
    tiny = (prod or {}).get("tiny") or (prod or {}).get("short") or ""
    role = _role_of(c)
    if role == "window":
        return "쇼윈도 · 외부 노출", f"창면 {tiny} 사이니지로 지나가는 고객의 시선을 매장 안으로 끌어들입니다", "쇼윈도"
    if role == "media":
        return "미디어 월 · 관람", f"{tiny} 앞에서 브랜드 영상에 몰입하는 관람 공간", "미디어월"
    if role == "demo":
        return "상담 · 시연", f"{tiny}에 상담 내용을 바로 그려 보이는 시연 공간", "상담 · 시연"
    if role == "display":
        return T.clip(f"{tiny} 존", 14), f"{tiny}로 공간의 핵심 메시지를 전하는 자리", T.clip(tiny, 8)
    if role == "lounge":
        return "라운지 · 체류", "창가 라운지에서 머무는 시간을 늘려 브랜드 경험으로", "라운지"
    if role == "info":
        return "안내 · 맞이", "입구에서 방문객을 맞이하고 동선을 안내하는 자리", "안내"
    f0 = next((groups[g] for g in c["groups"]), {})
    nm = f0.get("short") or "가구"
    return T.clip(f"{nm} 존", 14), f"{nm} 주변에서 고객이 머무는 공간", T.clip(nm, 8)


def _clean(name: str, text: str) -> tuple[str, str]:
    rules = config.rules()["zones"]
    return T.clip(T.mask_numbers(name), int(rules["name_max"])), T.clip(T.mask_numbers(text), int(rules["text_max"]))


async def _texts(b: dict[str, Any], model: dict[str, Any], cl: list[dict[str, Any]], groups: dict[str, dict[str, Any]]
                 ) -> tuple[dict[str, dict[str, Any]], str]:
    lines = []
    fam = []
    for c in cl:
        labels = " · ".join(groups[g].get("label") or "" for g in c["groups"])
        lines.append(f"{c['key']}: {labels}")
        fam += [groups[g].get("family_id") for g in c["groups"] if groups[g].get("family_id")]
    msgs = await kbapi.messages_for(b.get("space_types") or [], list(dict.fromkeys(fam)), limit=6)
    ctx = "\n".join(f"- {m['text']}" for m in msgs if m.get("text"))
    prompt = (f"공간: {b.get('description') or b.get('space_label')}\n군집(존 후보):\n" + "\n".join(lines) +
              f"\n근거 메시지(KB):\n{ctx or '- 없음'}\n존마다 이름(14자 이내)과 고객 관점 포인트 문구(60자 이내)를 쓰고, 입력 문장에 있는 요구만 needs 로. "
              "숫자는 쓰지 말고 [00] 으로.")
    path = "text:llm"
    try:
        res = await llm.json_task("be.zone_texts", prompt, ZoneTexts, confidential=True)
    except llm.ModelBlocked:
        res = None
    out: dict[str, dict[str, Any]] = {}
    keys = {c["key"] for c in cl}
    for z in (res or {}).get("zones") or []:
        if z.get("cluster") in keys and z.get("name") and z.get("text"):
            n, t = _clean(z["name"], z["text"])
            out[z["cluster"]] = {"name": n, "text": t, "needs": [T.clip(x, 12) for x in z.get("needs") or []][:2]}
    if len(out) < len(cl):
        path = "text:template" if not out else "text:mixed"
    for c in cl:
        if c["key"] not in out:
            n, t, _s = template_text(c, groups)
            n, t = _clean(n, t)
            out[c["key"]] = {"name": n, "text": t, "needs": []}
        out[c["key"]]["short"] = template_text(c, groups)[2]
        out[c["key"]]["sources"] = [{"kind": "kb", "ref": m.get("about_name") or "", "label": m.get("text", "")[:40], "url": m.get("source_url")}
                                    for m in msgs[:2]]
    return out, path


def _links(c: dict[str, Any], groups: dict[str, dict[str, Any]], model: dict[str, Any], needs: list[str]) -> list[dict[str, Any]]:
    out = []
    for g in c["groups"]:
        gr = groups[g]
        if gr.get("kind") == "product":
            out.append({"kind": "product", "label": gr.get("label") or "", "ref": gr.get("family_id")})
    if any((it.get("anchor") or {}).get("type") == "window" for it in c["items"]):
        win = next((o for o in model.get("openings", []) if o["kind"] == "window"), None)
        if win:
            out.append({"kind": "feature", "label": (win.get("label") or "창").split(" (")[0], "ref": win["id"]})
    for nd in needs:
        out.append({"kind": "need", "label": f"요구: {nd}", "ref": None})
    return out


def _zone_products(c: dict[str, Any], groups: dict[str, dict[str, Any]], prods: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for g in c["groups"]:
        gr = groups[g]
        if gr.get("kind") != "product":
            continue
        p = prods.get(gr.get("ref") or "", {})
        out.append({"family_id": gr.get("family_id"), "model_code": gr.get("model_code"), "label": p.get("display_name") or gr.get("label"),
                    "short": p.get("short") or gr.get("short") or "", "qty": int(gr.get("qty") or 1), "group_label": gr.get("label") or ""})
    return out


def _zone_furniture(c: dict[str, Any], groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for g in c["groups"]:
        gr = groups[g]
        if gr.get("kind") in ("furniture", "column_wrap"):
            out.append({"name": gr.get("short") or gr.get("label") or "", "qty": int(gr.get("qty") or 1)})
    return out


async def _cut_for(be_id: str, cut_id: str | None) -> dict[str, Any] | None:
    b = await svc.get(be_id)
    cs = await svc.cuts(be_id)
    if cut_id:
        c = next((x for x in cs if x["id"] == cut_id), None)
        if c is None:
            raise not_found("컷", cut_id)
        return c
    return next((x for x in cs if x["id"] == b.get("primary_cut_id")), None) or next(
        (x for x in cs if x["status"] in ("done", "check", "draft") and not x.get("before")), None)


async def auto(be_id: str, cut_id: str | None) -> dict[str, Any]:
    from .layouts import get_layout

    b = await svc.get(be_id)
    model = await svc.space_model(be_id) or {}
    lay = await get_layout(be_id)
    if lay is None:
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
    cut = await _cut_for(be_id, cut_id)
    groups = {g["id"]: g for g in lay.get("groups", [])}
    prods = {p["id"]: p for p in await svc.products(be_id)}
    cl = clusters(lay, float(config.rules().get("cluster_radius_m", 2.5)))
    zone_cl = [c for c in cl if c["kind"] in ("product", "furniture")]
    sugg_cl = [c for c in cl if c["kind"] == "wrap"]
    texts, path = await _texts(b, model, zone_cl, groups)
    dist = path_order(model, lay, [(c["key"], c["anchor"][0], c["anchor"][1]) for c in zone_cl], {c["key"]: c["items"] for c in zone_cl})
    zone_cl.sort(key=lambda c: (round(dist.get(c["key"], 1e9), 3), _gnum(c["key"])))
    for z in await svc.zones(be_id, include_all=True):
        await repo().delete("zones", z["id"])
    cam = (cut or {}).get("camera")
    n = 0
    for c in zone_cl:
        n += 1
        tx = texts[c["key"]]
        uv = draft.project_norm(cam, *c["anchor"]) if cam else None
        doc = {"birdseye_id": be_id, "n": n, "name": tx["name"], "text": tx["text"], "short_name": tx.get("short") or "",
               "links": _links(c, groups, model, tx.get("needs") or []), "anchor_m": c["anchor"], "cluster_item_ids": [it["id"] for it in c["items"]],
               "positions": {cut["id"]: uv} if (cut and uv) else {}, "status": "active", "path_order": n, "kind": c["kind"],
               "products": _zone_products(c, groups, prods), "furniture": _zone_furniture(c, groups), "meta_path": path,
               "sources": tx.get("sources") or [], "cluster_groups": c["groups"]}
        await repo().put("zones", new_id("bez"), doc)
    for c in sugg_cl:
        n += 1
        cols = len(c["items"])
        uv = draft.project_norm(cam, *c["anchor"]) if cam else None
        doc = {"birdseye_id": be_id, "n": n, "name": "기둥 랩핑 길 안내", "text": "기둥 랩핑 화면으로 매장 안 동선을 자연스럽게 안내합니다",
               "short_name": "기둥 랩핑", "links": [{"kind": "feature", "label": f"기둥 {cols}개", "ref": None}], "anchor_m": c["anchor"],
               "cluster_item_ids": [it["id"] for it in c["items"]], "positions": {cut["id"]: uv} if (cut and uv) else {},
               "status": "suggested", "path_order": None, "kind": "empty", "products": [], "furniture": _zone_furniture(c, groups),
               "meta_path": "text:template", "suggest_target": f"기둥 {cols}개", "sources": [], "cluster_groups": c["groups"]}
        await repo().put("zones", new_id("bez"), doc)
    await svc.index(be_id)
    return await zones_view(be_id, cut["id"] if cut else None)


def _uv(z: dict[str, Any], cut: dict[str, Any] | None) -> tuple[float | None, float | None]:
    if cut is None:
        return None, None
    pos = (z.get("positions") or {}).get(cut["id"])
    if pos:
        return pos[0], pos[1]
    cam = cut.get("camera")
    if cam and z.get("anchor_m"):
        uv = draft.project_norm(cam, *z["anchor_m"])
        if uv:
            return uv[0], uv[1]
    return None, None


def zone_view(z: dict[str, Any], cut: dict[str, Any] | None) -> dict[str, Any]:
    u, v = _uv(z, cut)
    return {
        "id": z["id"], "birdseye_id": z["birdseye_id"], "n": int(z.get("n") or 0), "name": z.get("name") or "", "text": z.get("text") or "",
        "links": z.get("links") or [], "anchor_m": z.get("anchor_m") or [0, 0, 0], "cluster_item_ids": z.get("cluster_item_ids") or [],
        "positions": {k: v2 for k, v2 in (z.get("positions") or {}).items() if v2}, "u": u, "v": v, "status": z.get("status") or "active",
        "path_order": z.get("path_order"), "kind": z.get("kind") or "product", "products": z.get("products") or [],
        "short_name": z.get("short_name") or "", "meta_path": z.get("meta_path"),
    }


async def zones_view(be_id: str, cut_id: str | None, *, running: bool = False, job_id: str | None = None) -> dict[str, Any]:
    b = await svc.get(be_id)
    cut = await _cut_for(be_id, cut_id)
    allz = await svc.zones(be_id, include_all=True)
    active = sorted([z for z in allz if z.get("status") == "active"], key=lambda z: z.get("n") or 0)
    sugg = [z for z in allz if z.get("status") == "suggested"]
    n = len(active)
    code = b.get("zone_layout") or "ZP-A"
    suggestions = []
    for i, z in enumerate(sugg, start=1):
        k = n + i
        target = z.get("suggest_target") or z.get("name")
        suggestions.append({"id": z["id"], "title": f"W 제안 · {z.get('name')}", "question": f"{T.jo(target, '을/를')} {k}번 포인트로 넣을까요?",
                            "add_label": f"{k}번으로 추가", "n": k})
    return {
        "points": [zone_view(z, cut) for z in active], "suggestions": suggestions,
        "preview": {"code": code, "layout_label": LAYOUT_LABEL.get(code, "번호 콜아웃"), "count": n,
                    "line": f"{code} {LAYOUT_LABEL.get(code, '번호 콜아웃')} · 포인트 {n}곳"},
        "cut_id": cut["id"] if cut else None, "cut_label": svc.cut_label(cut) if cut else "",
        "cut_url": _cut_display_url(cut),
        "w_message": W_ZONES.format(n=n), "running": running, "job_id": job_id,
        "proposal_label": next((u.get("label") or None for u in await svc.usages(be_id) if u.get("service") == "proposal"), None),
    }


def _cut_display_url(cut: dict[str, Any] | None) -> str | None:
    if not cut:
        return None
    from .cuts import display_file_id
    fid = display_file_id(cut) or cut.get("image_file_id") or cut.get("draft_v1_file_id")
    return f"/api/files/v1/files/{fid}/content" if fid else None


async def renumber(be_id: str) -> None:
    zs = sorted(await svc.zones(be_id), key=lambda z: (z.get("n") or 0))
    for i, z in enumerate(zs, start=1):
        if z.get("n") != i:
            await repo().patch("zones", z["id"], {"n": i})
    sugg = [z for z in await svc.zones(be_id, include_all=True) if z.get("status") == "suggested"]
    for j, z in enumerate(sugg, start=len(zs) + 1):
        await repo().patch("zones", z["id"], {"n": j})


async def renumber_by_path(be_id: str) -> None:
    from .layouts import get_layout

    model = await svc.space_model(be_id) or {}
    lay = await get_layout(be_id) or {"items": [], "groups": []}
    zs = await svc.zones(be_id)
    by_id = {it["id"]: it for it in lay.get("items", [])}
    its = {z["id"]: [by_id[i] for i in z.get("cluster_item_ids") or [] if i in by_id] for z in zs}
    dist = path_order(model, lay, [(z["id"], z["anchor_m"][0], z["anchor_m"][1]) for z in zs], its)
    zs.sort(key=lambda z: (round(dist.get(z["id"], 1e9), 3), z.get("n") or 0))
    for i, z in enumerate(zs, start=1):
        await repo().patch("zones", z["id"], {"n": i, "path_order": i})
    await renumber(be_id)
    await svc.index(be_id)


async def add_point(be_id: str, cut_id: str | None, u: float | None, v: float | None, from_suggestion: str | None) -> dict[str, Any]:
    from .layouts import get_layout

    zs = await svc.zones(be_id)
    n = len(zs) + 1
    cut = await _cut_for(be_id, cut_id)
    if from_suggestion:
        z = await repo().get("zones", from_suggestion)
        if z is None or z.get("birdseye_id") != be_id:
            raise not_found("제안", from_suggestion)
        await repo().patch("zones", z["id"], {"status": "active", "n": n, "path_order": n})
        await renumber(be_id)
        await svc.index(be_id)
        return zone_view(await repo().get("zones", z["id"]), cut)
    if u is None or v is None:
        u, v = 0.5, 0.5
    lay = await get_layout(be_id) or {"items": [], "groups": []}
    floor = draft.unproject_norm(cut["camera"], u, v) if cut and cut.get("camera") else None
    x, y = floor if floor else (0.0, 0.0)
    near = sorted([it for it in lay.get("items", []) if not it.get("unplaced")],
                  key=lambda it: (round(math.hypot(it["x"] - x, it["y"] - y), 3), it["id"]))[:1]
    groups = {g["id"]: g for g in lay.get("groups", [])}
    name, text = "새 포인트", "이 자리에서 보여 줄 포인트를 적어 주세요"
    products = []
    if near and math.hypot(near[0]["x"] - x, near[0]["y"] - y) <= 3.0:
        g = groups.get(near[0]["group_id"], {})
        c = {"key": g.get("id"), "groups": [g.get("id")], "items": [near[0]]}
        nm, tx, _s = template_text(c, groups)
        name, text = _clean(nm, tx)
        if g.get("kind") == "product":
            products = [{"family_id": g.get("family_id"), "model_code": g.get("model_code"), "label": g.get("label") or "",
                         "short": g.get("short") or "", "qty": int(g.get("qty") or 1), "group_label": g.get("label") or ""}]
    doc = {"birdseye_id": be_id, "n": n, "name": name, "text": text, "short_name": T.clip(name.split(" · ")[0], 8), "links": [],
           "anchor_m": [round(x, 2), round(y, 2), 1.0], "cluster_item_ids": [it["id"] for it in near],
           "positions": {cut["id"]: [round(u, 4), round(v, 4)]} if cut else {}, "status": "active", "path_order": n,
           "kind": "product" if products else ("furniture" if near else "empty"), "products": products, "furniture": [],
           "meta_path": "zones:click", "sources": []}
    saved = await repo().put("zones", new_id("bez"), doc)
    await renumber(be_id)
    await svc.index(be_id)
    return zone_view(await repo().get("zones", saved["id"]), cut)


async def patch_zone(zid: str, body: dict[str, Any]) -> dict[str, Any]:
    z = await repo().get("zones", zid)
    if z is None:
        raise not_found("존 포인트", zid)
    changes: dict[str, Any] = {}
    if body.get("name") is not None:
        changes["name"] = T.clip(body["name"], int(config.rules()["zones"]["name_max"]))
    if body.get("text") is not None:
        changes["text"] = T.clip(body["text"], int(config.rules()["zones"]["text_max"]))
    if body.get("links") is not None:
        changes["links"] = body["links"]
    if body.get("status") is not None:
        changes["status"] = body["status"]
    cut = await _cut_for(z["birdseye_id"], body.get("cut_id"))
    if body.get("u") is not None and body.get("v") is not None and cut is not None:
        pos = dict(z.get("positions") or {})
        pos[cut["id"]] = [round(float(body["u"]), 4), round(float(body["v"]), 4)]
        changes["positions"] = pos
        floor = draft.unproject_norm(cut["camera"], float(body["u"]), float(body["v"])) if cut.get("camera") else None
        if floor:
            changes["anchor_m"] = [round(floor[0], 2), round(floor[1], 2), (z.get("anchor_m") or [0, 0, 1.0])[2]]
    await repo().patch("zones", zid, changes)
    if body.get("status") in ("dismissed", "active"):
        await renumber(z["birdseye_id"])
    await svc.index(z["birdseye_id"])
    return zone_view(await repo().get("zones", zid), cut)


async def delete_zone(zid: str) -> None:
    z = await repo().get("zones", zid)
    if z is None:
        raise not_found("존 포인트", zid)
    await repo().delete("zones", zid)
    await renumber(z["birdseye_id"])
    await svc.index(z["birdseye_id"])


async def rewrite(be_id: str, text: str, zone_ids: list[str] | None) -> int:
    b = await svc.get(be_id)
    zs = [z for z in await svc.zones(be_id) if not zone_ids or z["id"] in zone_ids]
    if not zs:
        return 0
    prompt = (f"공간: {b.get('description') or b.get('space_label')}\n요청: {text}\n존:\n" +
              "\n".join(f"{z.get('n')}. {z['id']}: {z.get('name')} — {z.get('text')}" for z in zs) +
              "\n요청대로 존 이름(14자 이내)과 포인트 문구(60자 이내)를 다시 쓴다. cluster 에 존 번호 또는 id. 숫자는 [00].")
    try:
        res = await llm.json_task("be.zone_rewrite", prompt, Rewrite, confidential=True)
    except llm.ModelBlocked:
        res = None
    n = 0
    by = {z["id"]: z for z in zs}
    by_n = {str(z.get("n")): z for z in zs}
    for r in (res or {}).get("zones") or []:
        key = str(r.get("cluster") or "").strip()
        z = by.get(key) or by_n.get(key.rstrip("번"))
        if not z or not r.get("text"):
            continue
        name, tx = _clean(r.get("name") or z.get("name") or "", r["text"])
        await repo().patch("zones", z["id"], {"name": name, "text": tx})
        n += 1
    await svc.index(be_id)
    return n
