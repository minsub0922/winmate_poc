"""시트 구성(§7.9, 결정적) · 제안서 묶음(§8 handoff · ProposalHandoff v1) · 내보내기 문서(§7.10).

1. 장면을 space_key 로 묶는다(LLM 이 장소를 시나리오 공간 목록에 정규화 — 결과는 저장해 재사용, 실패하면 KB A1 공간 유형 · 장소 그대로).
2. 공간 ≥ 2 이면 맵 시트 1장: 조감도 연결 + 존 위치 → VM-C, WITH → VM-A, WITHOUT + 시각 있는 시간대 → VM-D, 그 밖 → VM-B(공간 ≤ 3).
3. 공간마다: 장면 ≥ 2 → SS-A(3장면씩), 장면 1 + 솔루션 → SS-B, 장면 1 + 전후 이미지 → SS-C, 그 밖 → SS-A.
4. 번호 = 맵 → 공간(첫 장면 순서). 시트별 images {have, total} · confirm_count([00] 수).
"""
from __future__ import annotations

import logging
from typing import Any

from . import kbq, llm, prompts, repo, seed, service, texts
from . import timeline as tl

log = logging.getLogger("winmate.scenario.sheets")

MAP_TITLES = {"VM-A": "공간 × 솔루션 맵", "VM-B": "공간 3개 한 장", "VM-C": "조감도 위 솔루션 핀", "VM-D": "하루 타임라인 × 공간"}
CODE_NAMES = {**MAP_TITLES, "SS-A": "한 공간의 장면 3", "SS-B": "솔루션 → 제품 → 가치", "SS-C": "이 공간 전 → 후"}
SS_A_PER_SHEET = 3


# ── 공간 정규화 ────────────────────────────────────────────

def _fallback_space(doc: dict[str, Any], place: str) -> str:
    p = (place or "").strip()
    if not p:
        return doc.get("space_label") or "공간"
    if "본사" in p:
        return "본사 운영실"
    return p


async def ensure_space_keys(sc_id: str) -> dict[str, Any]:
    """장면마다 space_key 가 없으면 장소를 공간 목록으로 묶는다(sc.space_keys, 실패하면 결정적 대체)."""
    doc = await repo.require_sc(sc_id)
    todo = [s for s in doc.get("scenes") or [] if not s.get("space_key")]
    if not todo:
        return doc
    mapping: dict[str, str] = dict(doc.get("space_keys") or {})
    places = sorted({(s.get("place") or "").strip() for s in todo if (s.get("place") or "").strip() not in mapping})
    zone_names = {s["id"]: (s.get("zone_ref") or {}).get("name") for s in todo if (s.get("zone_ref") or {}).get("name")}
    candidates = list(dict.fromkeys([*(doc.get("spaces") or []), *(seed.industry(doc.get("vertical_code")) or {}).get("spaces", [])]))
    if places:
        res = await llm.try_json("sc.space_keys", prompts.space_keys(doc, places, candidates), prompts.SpaceKeysOut,
                                 customer=doc.get("customer_name"), timeout=20)
        if res is not None:
            for m in res.data.get("mapping") or []:
                if m.get("place") in places and (m.get("space") or "").strip():
                    mapping[m["place"]] = m["space"].strip()
        for p in places:
            if p not in mapping:
                links = await kbq.a1(p)
                space = next((lk.get("name") for lk in links if lk.get("type") == "space_type"), None)
                mapping[p] = _fallback_space(doc, p) if not space or "본사" in p else space

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["space_keys"] = {**(d.get("space_keys") or {}), **mapping}
        spaces = list(d.get("spaces") or [])
        for s in d.get("scenes") or []:
            if s.get("space_key"):
                continue
            key = zone_names.get(s["id"]) or mapping.get((s.get("place") or "").strip()) or _fallback_space(d, s.get("place") or "")
            s["space_key"] = key
            if key not in spaces:
                spaces.append(key)
        d["spaces"] = spaces
        return d
    return await repo.update(sc_id, fn)


# ── 시트 구성 ──────────────────────────────────────────────

def _images(scenes: list[dict[str, Any]]) -> dict[str, int]:
    return {"have": sum(1 for s in scenes if s.get("image")), "total": len(scenes)}


def _confirm(scenes: list[dict[str, Any]]) -> int:
    return sum(len(s.get("confirm_tokens") or []) for s in scenes)


def _solutions_used(doc: dict[str, Any], scenes: list[dict[str, Any]] | None = None) -> list[str]:
    out: list[str] = []
    for s in scenes if scenes is not None else tl.scenes(doc):
        for so in s.get("solutions") or []:
            if so.get("solution_id") and so["solution_id"] not in out:
                out.append(so["solution_id"])
    return out


def _sol_name(sid: str) -> str:
    s = seed.solution(sid)
    return s["name"] if s else sid


def _has_zone_positions(doc: dict[str, Any]) -> bool:
    link = doc.get("birdseye_link") or {}
    if not link.get("birdseye_id"):
        return False
    return any((s.get("zone_ref") or {}).get("u") is not None for s in doc.get("scenes") or [])


def plan(doc: dict[str, Any]) -> dict[str, Any]:
    scenes = [s for s in tl.scenes(doc) if s.get("status") == "done" or s.get("story")]
    groups: dict[str, list[dict[str, Any]]] = {}
    for s in scenes:
        groups.setdefault(s.get("space_key") or _fallback_space(doc, s.get("place") or ""), []).append(s)
    space_order = sorted(groups, key=lambda k: groups[k][0].get("no", 0))
    sheets: list[dict[str, Any]] = []
    sols = _solutions_used(doc, scenes)
    if len(space_order) >= 2:
        timed = any(sl.get("time") for sl in doc.get("slots") or [])
        code: str | None
        if _has_zone_positions(doc):
            code = "VM-C"
        elif doc.get("type") == "with" and sols:
            code = "VM-A"
        elif doc.get("type") != "with" and timed:
            code = "VM-D"
        elif len(space_order) <= 3:
            code = "VM-B"
        else:
            code = None
        if code:
            nos = [s["no"] for s in scenes]
            detail: dict[str, Any] = {"rows": space_order}
            if code == "VM-A":
                detail["cols"] = [_sol_name(x) for x in sols]
                detail["cells"] = [[[tl.scene_time(doc, s) or f"장면 {s['no']}" for s in groups[sp]
                                     if any(so.get("solution_id") == sid for so in s.get("solutions") or [])]
                                    for sid in sols] for sp in space_order]
                detail["grid"] = f"공간 {len(space_order)} × 솔루션 {len(sols)} 격자"
            elif code == "VM-D":
                used = {s.get("slot_id") for s in scenes}  # 장면이 있는 시간대만 열로(빈 시간대는 「—」 줄만 남긴다)
                times = [sl.get("time") or sl["label"] for sl in tl.slots(doc) if sl.get("id") in used]
                detail["cols"] = times
                detail["grid"] = f"공간 {len(space_order)} × 시간대 {len(times)}"
            sheets.append({"code": code, "kind": "map", "title": MAP_TITLES[code], "space_key": None,
                           "scene_ids": [s["id"] for s in scenes], "scene_nos": nos, "images": _images(scenes),
                           "confirm_count": _confirm(scenes),
                           "summary": f"장면 {nos[0]}–{nos[-1]} 요약" if len(nos) > 1 else f"장면 {nos[0]} 요약",
                           "detail": detail})
    for sp in space_order:
        group = groups[sp]
        if len(group) >= 2:
            chunks = [group[i:i + SS_A_PER_SHEET] for i in range(0, len(group), SS_A_PER_SHEET)]
            for ch in chunks:
                sheets.append(_ss_sheet(doc, "SS-A", sp, ch))
        else:
            one = group[0]
            if one.get("solutions"):
                sheets.append(_ss_sheet(doc, "SS-B", sp, group))
            elif (one.get("image") or {}).get("before_after"):
                sheets.append(_ss_sheet(doc, "SS-C", sp, group))
            else:
                sheets.append(_ss_sheet(doc, "SS-A", sp, group))
    for i, sh in enumerate(sheets, start=1):
        sh["n"] = i
    missing = [s for s in scenes if not s.get("image")]
    return {
        "sheets": sheets, "carry": carry(doc, scenes), "images_missing": len(missing),
        "first_missing_scene_id": missing[0]["id"] if missing else None, "spaces": space_order,
        "version": int(doc.get("saved_version") or 0), "last_saved_at": doc.get("last_saved_at"),
    }


def _ss_sheet(doc: dict[str, Any], code: str, space: str, group: list[dict[str, Any]]) -> dict[str, Any]:
    first = group[0]
    sol_ids = _solutions_used(doc, group)
    chips = [*(_sol_name(x) for x in sol_ids[:1]), *([service.product_chip(p) for p in (first.get("products") or [])[:1]]), "가치"]
    if any(s.get("confirm_tokens") for s in group) or code in ("SS-A", "SS-B"):
        chips.append("[00]")
    detail: dict[str, Any] = {"chips": chips}
    if code == "SS-A":
        detail["line"] = f"시간대 장면 {len(group)}개 · 이미지 {_images(group)['have']} / {len(group)}"
        detail["sub"] = "이야기 · 솔루션 동작 · 제품"
    elif code == "SS-B":
        sol = (first.get("solutions") or [{}])[0]
        act = seed.action(sol.get("solution_id") or "", sol.get("action_code") or "") or {}
        prod = (first.get("products") or [{}])[0]
        chain = [x for x in [_sol_name(sol.get("solution_id") or "") if sol else "", prod.get("short") or "", act.get("value") or "가치"] if x]
        detail["chain"] = " → ".join(chain)
        detail["sub"] = "가치 수치는 [확정 필요]로 표시"
    return {"code": code, "kind": "space", "title": space, "space_key": space, "scene_ids": [s["id"] for s in group],
            "scene_nos": [s["no"] for s in group], "images": _images(group), "confirm_count": _confirm(group),
            "summary": " ".join(f"장면 {s['no']}" for s in group), "detail": detail}


def carry(doc: dict[str, Any], scenes: list[dict[str, Any]] | None = None) -> dict[str, int]:
    scenes = scenes if scenes is not None else [s for s in tl.scenes(doc) if s.get("story")]
    products: set[str] = set()
    for s in scenes:
        for p in s.get("products") or []:
            products.add(service.product_key(p))
    if not products:
        products = {service.product_key(p) for p in doc.get("product_picks") or []}
    return {"scenes": len(scenes), "solutions": len(_solutions_used(doc, scenes)), "products": len(products),
            "images": sum(1 for s in scenes if s.get("image")), "confirm": _confirm(scenes)}


# ── handoff(§8) ──────────────────────────────────────────

def handoff(doc: dict[str, Any], plan_: dict[str, Any], version: int) -> dict[str, Any]:
    scenes_out = []
    confirm_items = []
    for s in tl.scenes(doc):
        if not s.get("story"):
            continue
        img = s.get("image")
        scenes_out.append({
            "no": s["no"], "id": s["id"], "time": tl.scene_time(doc, s), "label": tl.scene_label(doc, s), "title": s.get("title") or "",
            "story": s.get("story") or "",
            "beats": [{"role": (tl.role_by_id(doc, b.get("role_id")) or {}).get("name") or "", "text": b["text"], "place": b.get("place") or ""}
                      for b in s.get("beats") or []],
            "place": s.get("place") or "", "space_key": s.get("space_key"),
            "solutions": [{"id": x.get("solution_id"), "action": x.get("action_code"), "label": x.get("label") or seed.action_label(
                x.get("solution_id") or "", x.get("action_code") or "")} for x in s.get("solutions") or []],
            "products": [{"family_id": p.get("family_id"), "model_code": p.get("model_code"), "label": p.get("label") or p.get("short"),
                          "short": p.get("short"), "qty": p.get("qty")} for p in s.get("products") or []],
            "image": ({"version_id": img.get("version_id"), "image_id": img.get("image_id"), "file_id": img.get("file_id"),
                       "renditions": img.get("renditions") or [], "generation": img.get("generation") or {}} if img else None),
            "confirm_tokens": s.get("confirm_tokens") or [], "evidence": s.get("evidence") or [],
        })
        for t in s.get("confirm_tokens") or []:
            confirm_items.append({"scene_no": s["no"], "token": t.get("text") or "[00]", "near_text": t.get("near") or ""})
    return {
        "scenario_id": doc["id"], "version": version, "title": doc.get("title") or "", "customer": doc.get("customer_name"),
        "type": doc.get("type") or "with",
        "solutions": [{"id": p["solution_id"], "name": p["name"]} for p in doc.get("solution_picks") or []],
        "products": [{"family_id": p.get("family_id"), "model_code": p.get("model_code"), "label": p.get("label"), "short": p.get("short"),
                      "qty": p.get("qty")} for p in doc.get("product_picks") or []],
        "roles": [{"name": r["name"], "intro": r.get("intro") or "", "wants": r.get("wants") or [], "pains": r.get("pains") or []}
                  for r in tl.roles(doc)],
        "slots": [{"time": s.get("time"), "label": s["label"]} for s in tl.slots(doc)],
        "scenes": scenes_out, "sheet_plan": plan_["sheets"], "birdseye_link": doc.get("birdseye_link"), "confirm_items": confirm_items,
    }


def proposal_handoff(doc: dict[str, Any], plan_: dict[str, Any], version: int, proposal_type: str, section: str) -> dict[str, Any]:
    """10-proposal §8.0 ProposalHandoff v1 — section=spaceScenario(VM · SS 시트) · solution(솔루션마다 SXS)."""
    ho = handoff(doc, plan_, version)
    by_id = {s["id"]: s for s in ho["scenes"]}
    items: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    if section in ("solution", "sxs"):
        for sid in _solutions_used(doc):
            s = seed.solution(sid) or {}
            sc_list = [x for x in ho["scenes"] if any(so.get("id") == sid for so in x["solutions"])]
            conf = sum(len(x["confirm_tokens"]) for x in sc_list)
            items.append({
                "key": f"sxs:{sid}", "label": f"{s.get('name', sid)} · 공간 시나리오", "from_label": "공간 시나리오", "sheet_role": "SXS",
                "solution_code": s.get("template_code"), "sheet_title": f"{s.get('name', sid)} 공간 시나리오",
                "template_hint": {"code": f"{s.get('template_code')}-S", "name": f"{s.get('name', sid)} 전용 공간 시나리오"} if s.get("template_code") else None,
                "status": "warn" if conf else "ok", "status_label": f"[확정 필요] {conf}건" if conf else "그대로 들어가요",
                "include_default": True, "repeat_key": {"kind": "solution", "ref": sid, "label": s.get("name", sid)},
                "content": {"scenes": sc_list}, "sources": _sources(sc_list),
            })
    else:
        for sh in plan_["sheets"]:
            sc_list = [by_id[i] for i in sh["scene_ids"] if i in by_id]
            conf = sh["confirm_count"]
            item = {
                "key": f"{sh['code']}:{sh['n']}", "label": f"시트 {sh['n']} · {sh['title']}", "from_label": "공간 시나리오",
                "sheet_role": sh["code"].split("-")[0], "sheet_title": sh["title"],
                "template_hint": {"code": sh["code"], "name": CODE_NAMES[sh["code"]]},
                "status": "warn" if conf else "ok", "status_label": f"[확정 필요] {conf}건" if conf else "그대로 들어가요",
                "include_default": True, "content": {"sheet": sh, "scenes": sc_list}, "sources": _sources(sc_list),
            }
            if sh["kind"] == "space":
                item["repeat_key"] = {"kind": "space", "ref": sh["space_key"], "label": sh["title"]}
            items.append(item)
    for s in ho["scenes"]:
        for i, t in enumerate(s["confirm_tokens"], start=1):
            facts.append({"key": f"scene{s['no']}_{i}", "label": f"장면 {s['no']} · {t.get('near') or ''}".strip(), "status": "placeholder",
                          "placeholder": "[00]", "source": {"kind": "scenario", "scene_no": s["no"]}})
        img = s.get("image")
        if img and img.get("file_id"):
            assets.append({"kind": "image", "file_id": img["file_id"], "rights": "generated", "caption_rule": "생성 이미지",
                           "scene_no": s["no"], "version_id": img.get("version_id")})
    ind = seed.industry(doc.get("vertical_code"))
    return {
        "source": {"feature": "scenario", "ref_id": doc["id"], "version": version, "title": doc.get("title") or "",
                   "updated_at": doc.get("updated_at") or "", "route": f"/scenario/{doc['id']}/result"},
        "target": {"proposal_type": proposal_type, "section_key": "solution" if section in ("solution", "sxs") else "spaceScenario"},
        "customer": {"name": doc.get("customer_name"), "industry_code": ind["code"] if ind else None},
        "items": items, "facts": facts, "assets": assets, "live_link": False,
    }


def _sources(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen = set()
    for s in scenes:
        for e in s.get("evidence") or []:
            key = (e.get("kind"), e.get("text"))
            if key in seen:
                continue
            seen.add(key)
            out.append({"kind": e.get("kind"), "ref": e.get("ref") or "", "label": texts.clip(e.get("text") or "", 60),
                        **({"url": e["source_url"]} if e.get("source_url") else {})})
    return out


# ── 내보내기 문서 ──────────────────────────────────────────

def _img_slot(scene: dict[str, Any]) -> dict[str, Any] | None:
    img = scene.get("image") or {}
    if not img.get("file_id"):
        return None
    return {"file_id": img["file_id"], "caption": "AI 생성 이미지", "ai_generated": True}


def pptx_document(doc: dict[str, Any], plan_: dict[str, Any]) -> dict[str, Any]:
    by_id = {s["id"]: s for s in doc.get("scenes") or []}
    footer = texts.join([doc.get("customer_name") or "", doc.get("title") or ""])
    slides = []
    for sh in plan_["sheets"]:
        scs = [by_id[i] for i in sh["scene_ids"] if i in by_id]
        eyebrow = "공간별 가치 제공 시나리오"
        slots: dict[str, Any] = {"eyebrow": eyebrow, "footer": footer}
        if sh["code"] == "VM-A":
            d = sh["detail"]
            rows = [[sp, *[" · ".join(cell) if cell else "—" for cell in d.get("cells", [[]])[i]]] for i, sp in enumerate(d.get("rows") or [])]
            slots.update({"title": f"{doc.get('title') or ''} — 공간 × 솔루션", "subtitle": sh["summary"],
                          "table": {"columns": ["공간", *d.get("cols", [])], "rows": rows}})
        elif sh["code"] == "VM-D":
            d = sh["detail"]
            times = d.get("cols") or []
            rows = []
            for sp in d.get("rows") or []:
                row = [sp]
                for t in times:
                    hit = [s for s in scs if s.get("space_key") == sp and (tl.scene_time(doc, s) or tl.scene_label(doc, s)) == t]
                    row.append(" · ".join(texts.clip(s.get("title") or "", 18) for s in hit) or "—")
                rows.append(row)
            slots.update({"title": f"{doc.get('title') or ''} — 하루 타임라인", "subtitle": sh["summary"],
                          "lanes": {"columns": ["공간", *times], "rows": rows}})
        elif sh["code"] == "VM-B":
            pillars = []
            for i, sp in enumerate((sh["detail"].get("rows") or [])[:3], start=1):
                first = next((s for s in scs if s.get("space_key") == sp), None) or {}
                pillars.append({"no": f"{i:02d}", "tag": sp, "title": texts.clip(first.get("title") or sp, 24),
                                "body": texts.clip(first.get("story") or "", 90), "kpi": "[확정 필요]", **({"image": _img_slot(first)} if _img_slot(first) else {})})
            slots.update({"title": doc.get("title") or "공간 시나리오", "pillars": pillars})
        elif sh["code"] == "VM-C":
            pins = []
            for s in scs[:5]:
                z = s.get("zone_ref") or {}
                pins.append({"no": str(s["no"]), "title": texts.clip(s.get("title") or "", 22), "body": texts.clip(s.get("story") or "", 70),
                             "tag": (seed.chip_labels(s.get("solutions") or []) or [""])[0][:14], "x": round(float(z.get("u") or 0.5) * 100),
                             "y": round(float(z.get("v") or 0.5) * 100)})
            slots.update({"title": f"{doc.get('title') or ''} — 조감도 위 솔루션", "subtitle": sh["summary"], "pins": pins,
                          "legend": [{"letter": chr(65 + i), "title": _sol_name(x), "body": ""} for i, x in enumerate(_solutions_used(doc)[:2])]})
        elif sh["code"] == "SS-A":
            items = []
            for s in scs[:3]:
                it = {"no": f"{s['no']:02d}", "tag": tl.scene_time(doc, s) or tl.scene_label(doc, s), "title": texts.clip(s.get("title") or "", 24),
                      "body": texts.clip(s.get("story") or "", 80), "kpi": "[00]" if s.get("confirm_tokens") else ""}
                if _img_slot(s):
                    it["image"] = _img_slot(s)
                items.append(it)
            first_img = next((_img_slot(s) for s in scs if _img_slot(s)), None)
            slots.update({"title": f"{sh['title']} — {texts.clip(scs[0].get('title') or '', 30)}", "items": items,
                          "image_caption": "AI 생성 이미지" if first_img else "장면 이미지 자리"})
            if first_img:
                slots["image"] = first_img
        elif sh["code"] == "SS-B":
            s = scs[0]
            sols = s.get("solutions") or []
            slots.update({
                "title": texts.clip(s.get("title") or sh["title"], 46), "space": texts.clip(sh["title"], 16),
                "headers": ["무엇이", "무엇으로", "어떤 가치를"],
                "solutions": [{"letter": chr(65 + i), "title": texts.clip(x.get("label") or "", 18),
                               "body": texts.clip((seed.action(x.get("solution_id") or "", x.get("action_code") or "") or {}).get("benefit") or "", 50)}
                              for i, x in enumerate(sols[:2])],
                "products": [{"title": texts.clip(p.get("short") or "", 16), "body": texts.clip(p.get("label") or "", 20)}
                             for p in (s.get("products") or [])[:3]],
                "values": [{"no": f"{i + 1:02d}", "title": texts.clip((seed.action(x.get("solution_id") or "", x.get("action_code") or "") or {}).get("value") or "가치", 26),
                            "kpi": "[확정 필요]"} for i, x in enumerate(sols[:2])],
            })
            if _img_slot(s):
                slots["image"] = _img_slot(s)
        elif sh["code"] == "SS-C":
            s = scs[0]
            slots.update({"title": texts.clip(s.get("title") or sh["title"], 46), "labels": ["도입 전", "도입 후"],
                          "sides": [{"tag": "도입 전", "title": "", "body": ""}, {"tag": "도입 후", "title": texts.clip(s.get("title") or "", 30),
                                                                                 "body": texts.clip(s.get("story") or "", 80)}],
                          "message": texts.clip(s.get("story") or "", 70)})
        slides.append({"template_code": sh["code"], "slots": slots, "sheet_id": f"{sh['code']}:{sh['n']}",
                       "confirm": [t.get("near") or "" for s in scs for t in s.get("confirm_tokens") or []]})
    return {"title": doc.get("title") or "공간 시나리오", "footer": footer, "tbd_label": "[확정 필요]", "slides": slides}


def docx_document(doc: dict[str, Any]) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    for s in tl.scenes(doc):
        if not s.get("story"):
            continue
        bullets = []
        for b in s.get("beats") or []:
            r = tl.role_by_id(doc, b.get("role_id"))
            bullets.append(f"{(r or {}).get('name') or '역할'}: {b['text']}" + (f" ({b['place']})" if b.get("place") else ""))
        rows = [["시각", tl.scene_time(doc, s) or tl.scene_label(doc, s)], ["장소", s.get("place") or ""],
                ["솔루션 동작", " · ".join(seed.chip_labels(s.get("solutions") or [])) or "—"],
                ["제품", " · ".join(service.product_chip(p) for p in s.get("products") or []) or "—"]]
        for e in s.get("evidence") or []:
            rows.append(["근거", texts.join([e.get("text") or "", e.get("source_url") or ""])])
        if s.get("confirm_tokens"):
            rows.append(["확정 필요", " / ".join(t.get("near") or "[00]" for t in s["confirm_tokens"])])
        sections.append({"heading": f"장면 {s['no']} · {s.get('title') or ''}", "level": 1, "paragraphs": [s.get("story") or ""],
                         "bullets": bullets, "table": {"columns": ["항목", "내용"], "rows": rows}})
    persona_rows = [[r["name"], r.get("intro") or "", " · ".join(r.get("wants") or []), " · ".join(r.get("pains") or [])]
                    for r in tl.roles(doc)]
    sections.append({"heading": "등장인물 · 페르소나", "level": 1,
                     "table": {"columns": ["역할", "한 줄 소개", "원하는 것", "불편한 점"], "rows": persona_rows}})
    return {"title": f"{doc.get('title') or '공간 시나리오'} — 장면 스크립트",
            "subtitle": texts.join([doc.get("customer_name") or "", service.TYPE_LABEL[doc.get("type") or "with"],
                                    f"장면 {len([x for x in doc.get('scenes') or [] if x.get('story')])}"]),
            "sections": sections}


def zip_entries(doc: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    meta = []
    for s in tl.scenes(doc):
        img = s.get("image") or {}
        if not img.get("file_id"):
            continue
        label = tl.scene_label(doc, s).replace(" ", "")
        path = f"장면{s['no']}_{label or 'scene'}.png"
        entries.append({"file_id": img["file_id"], "path": path})
        meta.append({"path": path, "scene_no": s["no"], "title": s.get("title") or "", "image_id": img.get("image_id"),
                     "version_id": img.get("version_id"), "source": img.get("source"), "generation": img.get("generation") or {},
                     "ai_generated": True})
    entries.append({"path": "sources.json", "json": {"scenario_id": doc["id"], "title": doc.get("title"), "images": meta}})
    return entries
