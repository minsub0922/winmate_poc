"""섹션 초안 재료 — 연결 자료 반입 항목 · kb 조회(§7.4 섹션별 출처 표 · §7.14)를 시트마다 기본 본문(body)으로.

연결 작업이 있으면 그 기능의 반입 내용을 그대로 쓰고(다시 계산하지 않는다), 없으면 kb 를 직접 부른다.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from . import clients, content as C, defs, links as L, templates

log = logging.getLogger("winmate.proposal.inputs")

SELF_FILL = {"cases", "spaceProducts", "spec", "solution"}   # 연결 없이도 kb 로 채울 수 있는 섹션


def _match_item(sheet: dict[str, Any], items: list[dict[str, Any]], used: set[int]) -> dict[str, Any] | None:
    role = sheet.get("role")
    rk = sheet.get("repeat_key") or {}
    sol = sheet.get("solution_code")
    best = None
    for i, it in enumerate(items):
        if i in used or (it.get("sheet_role") or "").upper() != role:
            continue
        if sol and (it.get("solution_code") or "") and it.get("solution_code") != sol:
            continue
        irk = it.get("repeat_key") or {}
        if rk and irk:
            if irk.get("ref") == rk.get("ref") or irk.get("label") == rk.get("label"):
                used.add(i)
                return it
            continue
        if best is None:
            best = i
    if best is not None:
        used.add(best)
        return items[best]
    return None


async def section_items(p: dict[str, Any], key: str, *, refresh: bool = False) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(반입 항목[], 연결 자료[]) — 스냅숏이 없거나 유형이 다르면 다시 가져온다."""
    lns = await L.section_links(p["id"], key, p.get("type"))
    items: list[dict[str, Any]] = []
    for ln in lns:
        snap = ln.get("handoff")
        if ln.get("feature") in defs.WORK_FEATURES and (refresh or not snap or ln.get("stale")
                                                       or ((snap.get("target") or {}).get("proposal_type") not in (None, p.get("type")))):
            ln = await L.refresh_snapshot(ln, p, key)
            snap = ln.get("handoff")
        for it in (snap or {}).get("items") or []:
            tgt = it.get("target_section")
            if tgt and tgt != key:
                continue
            if ln.get("feature") == "mi" and key == "why" and it.get("sheet_role") not in ("CP", "CM", "ST"):
                continue
            if ln.get("feature") == "mi" and key in ("mi", "bigMi") and it.get("sheet_role") in ("CM", "ST"):
                continue
            if ln.get("include_keys") is not None and it.get("key") not in ln["include_keys"]:
                continue
            x = dict(it)
            x["_link_id"] = ln["id"]
            x["_feature"] = ln.get("feature")
            x["_ref"] = ln.get("ref_id")
            if ln.get("feature") == "mi" and key == "why" and x.get("sheet_role") == "CP":
                x["sheet_role"] = "CM"
            items.append(x)
    return items, lns


def _kpis_from_text(text: str) -> list[dict[str, Any]]:
    out = []
    for m in C.NUM_RE.finditer(text or ""):
        if m.group(2):
            out.append({"label": text[max(0, m.start() - 12):m.start()].strip(" ·,") or "성과", "value": m.group(1), "unit": (m.group(2) or "").strip()})
    return out[:3]


async def case_body(case_id: str, p: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """사례 상세(D1 · G5 · D3) → (body, sources)"""
    if not case_id:
        return {"title": "비슷한 고객의 도입 사례", "points": []}, []
    d = await clients.kb_get(f"/v1/cases/{case_id}") or {}
    title = d.get("title") or case_id
    from .plan import case_customer
    cust = case_customer(title)
    prods = [x.get("label") for x in d.get("products") or [] if x.get("label")]
    body: dict[str, Any] = {"title": f"{cust} — {', '.join(prods[:2]) or '삼성 솔루션'} 도입", "subtitle": d.get("tag_detail") or "",
                            "customer": cust, "points": [], "kpis": [], "images": [], "bullets": [], "signals": {}}
    quote = d.get("quote") or ""
    if d.get("summary"):
        body["points"].append({"title": "과제", "body": d["summary"]})
    if quote:
        body["message"] = quote
        body["points"].append({"title": "해결", "body": quote})
    if prods:
        body["points"].append({"title": "도입 제품", "body": " · ".join(prods[:4])})
    photos = ((d.get("photos") or {}).get("items")) or []
    for ph in photos[:2]:
        body["images"].append({"kind": "kb_image", "id": ph["id"], "rights": ph.get("rights") or "customer_case", "caption_rule": "도입사례 사진",
                               "source_url": d.get("url"), "label": ph.get("title") or ""})
    kp = await clients.kb_query("D3", {"deployment_ids": [case_id]})
    kpis = []
    for k in ((kp or {}).get("result") or {}).get("kpis") or []:
        if isinstance(k, dict):
            kpis.append({"label": k.get("metric") or k.get("label") or "성과", "value": k.get("value") or k.get("text") or "", "unit": k.get("unit") or "",
                         "claim": k.get("claim_flag") or k.get("tier") == "T5"})
    body["kpis"] = [k for k in kpis if k.get("value")][:3]
    sig = {"story": bool(quote or d.get("summary")), "public_kpis": len(body["kpis"]), "before_after_photos": False, "photos": len(photos)}
    body["signals"] = sig
    body["footnotes"] = [f"출처: {d.get('url_display') or d.get('url') or 'samsung.com'}"]
    return body, [{"kind": "kb", "ref": case_id, "label": title, "url": d.get("url"), "tier": "T2"}]


async def space_products(p: dict[str, Any], ctx: dict[str, Any], space: dict[str, Any]) -> list[dict[str, Any]]:
    prods = [x for x in ctx.get("products") or [] if x.get("space_key") == space.get("key")]
    if prods:
        return prods
    text = " ".join([space.get("name") or "", " ".join(it.get("text") or "" for it in ((ctx.get("rq") or {}).get("items") or []))])
    s1 = await clients.kb_query("S1", {"text": text[:1500] or space.get("name") or "매장", "limit": 3})
    for bs in ((s1 or {}).get("result") or {}).get("by_space") or []:
        if bs.get("space") == space.get("key") or bs.get("space_name") == space.get("name"):
            return [{"name": f.get("name"), "model": f.get("model"), "family_id": f.get("id"), "qty": None, "kb": True} for f in (bs.get("families") or [])[:3]]
    return []


async def space_image(p: dict[str, Any], space_key: str) -> dict[str, Any] | None:
    ind = templates.industry_code(p)
    kr = (defs.INDUSTRIES.get(ind or "") or {}).get("kr") or []
    body: dict[str, Any] = {"space": space_key, "limit": 1}
    if kr:
        body["vertical"] = kr[0]
    g1 = await clients.kb_query("G1", body)
    for im in ((g1 or {}).get("result") or {}).get("images") or []:
        return {"kind": "kb_image", "id": im["id"], "rights": im.get("rights") or "official", "caption_rule": im.get("caption_rule") or "예시 사진(삼성 공식 이미지)",
                "source_url": im.get("page_url") or im.get("url"), "label": im.get("alt") or im.get("title") or ""}
    return None


async def solution_detail(code: str) -> dict[str, Any]:
    kbid = (defs.SOLUTIONS.get(code) or {}).get("kb")
    if not kbid:
        return {}
    return await clients.kb_get(f"/v1/solutions/{kbid}") or {}


async def strengths(rq_texts: list[str], p: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """삼성 강점 — kb E3(업종 · 요구사항 문장 → 공식 핵심 메시지 + 근거) 상위 3. 없으면 E2(테마)로."""
    out: list[dict[str, Any]] = []
    if p is not None:
        ind = templates.industry_code(p)
        body: dict[str, Any] = {"text": " ".join(rq_texts)[:1500] or (p.get("title") or "매장")}
        kr = (defs.INDUSTRIES.get(ind or "") or {}).get("kr") or []
        if kr:
            body["vertical"] = kr[0]
        e3 = await clients.kb_query("E3", body)
        for m in ((e3 or {}).get("result") or {}).get("key_messages") or []:
            if (m.get("score") or 0) < 0.4 or not m.get("text"):
                continue
            proof = next((x.get("text") for x in m.get("proof_points") or [] if x.get("text")), "")
            out.append({"title": m["text"][:24], "body": (proof or "")[:80], "src": m.get("source_url"), "claim": bool(m.get("claim_flag"))})
            if len(out) >= 3:
                return out
    if out:
        return out
    for t in rq_texts[:3]:
        e2 = await clients.kb_query("E2", {"theme": t, "limit": 1})
        for m in ((e2 or {}).get("result") or {}).get("messages") or ((e2 or {}).get("result") or {}).get("items") or []:
            text = m.get("text") or m.get("message") or ""
            if text:
                out.append({"title": t[:16], "body": text[:80], "src": m.get("source_url") or m.get("url")})
                break
    return out


async def spec_table(models: list[str]) -> dict[str, Any] | None:
    models = [m for m in models if m][:4]
    if len(models) < 1:
        return None
    res = await clients.kb_post("/v1/spec/table", {"models": models})
    if not res:
        return None
    cols = [c.get("label") or c.get("model_code") or c.get("model") for c in res.get("columns") or res.get("models") or []]
    rows = []
    for r in (res.get("rows") or [])[:8]:
        cells = [{"text": C._s(v.get("text") if isinstance(v, dict) else v)} for v in (r.get("values") or r.get("cells") or [])]
        rows.append({"label": r.get("label") or r.get("attr") or "", "cells": cells})
    if not cols or not rows:
        return None
    return {"columns": ["항목", *cols], "rows": rows}


async def base_bodies(p: dict[str, Any], key: str, sheets: list[dict[str, Any]], *, mode: str = "draft") -> dict[str, Any]:
    """시트마다 기본 본문 · 출처 · 근거. → {sheet_id: {body, sources, origin_item, has_input}} + 연결 자료 목록."""
    ctx = p.get("ctx") or {}
    items, lns = await section_items(p, key)
    from . import repo
    facts_by_key = {f.get("key"): f for f in await repo.alist("facts", {"proposal_id": p["id"]})}
    used: set[int] = set()
    out: dict[str, Any] = {}
    rq_items = (ctx.get("rq") or {}).get("items") or []
    spaces = ctx.get("spaces") or []
    sols_on = [sh.get("solution_code") for sh in sheets if sh.get("role") == "SXI" and sh.get("solution_code")]
    for sh in sheets:
        role = sh.get("role") or ""
        it = _match_item(sh, items, used)
        body: dict[str, Any] = C.body_from_content(role, it) if it else {"title": "", "points": [], "bullets": []}
        sources: list[dict[str, Any]] = list((it or {}).get("sources") or [])
        if it:
            sources.insert(0, {"kind": "link", "ref": it.get("_link_id"), "label": it.get("label") or "", "feature": it.get("_feature")})
            th = it.get("template_hint") or {}
            if th.get("code"):
                body.setdefault("signals", {})["import_hint"] = th["code"]
        has_input = bool(it)
        rk = sh.get("repeat_key") or {}
        # kb 로 채우는 역할들
        if role == "CD":
            b, src = await case_body(rk.get("ref") or "", p)
            body = C.merge_body(b, body if it else None)
            sources += src
            has_input = has_input or bool(rk.get("ref"))
        elif role == "PI":
            sp = next((s for s in spaces if s["key"] == rk.get("ref")), {"key": rk.get("ref"), "name": rk.get("label")})
            prods = await space_products(p, ctx, sp)
            if sh.get("split_of") is not None or "#" in (sh.get("ident") or ""):
                part = int((sh.get("ident") or "#0").rsplit("#", 1)[-1] or 0) if "#" in (sh.get("ident") or "") else 0
                from .plan import split_counts
                counts = split_counts(len(prods))
                start = sum(counts[:part])
                prods = prods[start:start + counts[part] if part < len(counts) else None]
            def qty_of(x: dict[str, Any]) -> Any:
                fk = "qty_" + re.sub(r"[^0-9a-z]+", "_", str(x.get("model") or x.get("name") or "").lower())
                f = facts_by_key.get(fk)
                return "{{fact:" + f["id"] + "}}" if f else x.get("qty")
            body["products"] = [{"name": x.get("name"), "model": x.get("model") or x.get("name"), "qty": qty_of(x),
                                 "body": "", "tag": rk.get("label")} for x in prods[:5]]
            body["title"] = body.get("title") or f"{rk.get('label') or '공간'}에는 이 제품"
            img = await space_image(p, sp.get("key") or "")
            if img:
                body.setdefault("images", []).append(img)
            body.setdefault("signals", {})["products_n"] = max(1, min(5, len(prods) or 1))
            body["signals"]["birdseye"] = bool((ctx.get("has") or {}).get("birdseye"))
            has_input = has_input or bool(prods)
            if prods:
                sources.append({"kind": "kb" if prods[0].get("kb") else "link", "ref": sp.get("key"), "label": f"{sp.get('name')} 제품"})
        elif role == "SM":
            body["spaces"] = [{"name": s["name"], "body": " · ".join(x.get("model") or x.get("name") or "" for x in
                                                                     [y for y in ctx.get("products") or [] if y.get("space_key") == s["key"]][:3]),
                               "chips": [x.get("model") or x.get("name") for x in ctx.get("products") or [] if x.get("space_key") == s["key"]][:3]}
                              for s in spaces]
            body["title"] = body.get("title") or f"공간 {len(spaces)}곳 · 어디에 무엇을"
            body.setdefault("signals", {})["spaces"] = len(spaces)
            if any(x.get("qty") for x in ctx.get("products") or []):
                body["signals"]["qty_table"] = bool(it and (it.get("template_hint") or {}).get("code") == "SM-B")
            has_input = has_input or bool(spaces and (ctx.get("space_source") in ("birdseye", "scenario", "requirements")))
        elif role in ("SXI", "SXD", "SXS"):
            code = sh.get("solution_code") or ""
            s = defs.SOLUTIONS.get(code) or {}
            det = await solution_detail(code)
            body["solution_name"] = s.get("name")
            if role == "SXI":
                feats = det.get("features") or det.get("capabilities") or []
                body["points"] = body.get("points") or [{"title": C._s(f.get("name") if isinstance(f, dict) else f),
                                                         "body": C._s(f.get("desc") if isinstance(f, dict) else "")} for f in feats[:4]]
                body["message"] = body.get("message") or det.get("summary") or s.get("desc") or ""
                body["title"] = body.get("title") or f"{s.get('name')} — {s.get('I', '')}"
            elif role == "SXD":
                body["title"] = body.get("title") or f"{s.get('name')} 구성 — {s.get('D', '')}"
                body["points"] = body.get("points") or [{"title": "본사", "body": "콘텐츠 · 정책 관리"}, {"title": s.get("name", ""), "body": s.get("D", "")},
                                                        {"title": "매장", "body": "디스플레이 · 기기"}]
                rqt = " ".join(x.get("text") or "" for x in rq_items)
                body.setdefault("signals", {})["reason"] = ("요구사항에 사내 서버 · 보안 조건이 있어요" if any(w in rqt for w in ("서버", "보안", "POS", "연동"))
                                                            else None)
            else:
                body["title"] = body.get("title") or f"{s.get('name')} — {s.get('S', '')}"
                if not body.get("steps"):
                    body["steps"] = [{"when": "오전", "title": s.get("S", ""), "body": ""}]
            if det:
                sources.append({"kind": "kb", "ref": det.get("id") or s.get("kb"), "label": s.get("name", ""), "url": det.get("url")})
            has_input = True
        elif role == "SA":
            names = [defs.SOLUTIONS.get(c, {}).get("name", c) for c in sols_on]
            body["title"] = body.get("title") or f"{' + '.join(names)} 통합 구성"
            body["points"] = [{"title": "본사", "body": "콘텐츠 · 정책 · 에너지 기준을 한 곳에서"}, {"title": "클라우드 · 서버", "body": " · ".join(names)},
                              {"title": "매장", "body": "사이니지 · IoT 기기"}]
            body.setdefault("signals", {})["solutions"] = len(sols_on)
            has_input = len(sols_on) >= 2
        elif role == "VM":
            if not body.get("table") and spaces:
                cols = ["공간", *[defs.SOLUTIONS.get(c, {}).get("name", c) for c in sols_on or []]]
                body["table"] = {"columns": cols, "rows": [{"label": s["name"], "cells": [{"text": "—"} for _ in sols_on]} for s in spaces]}
            body.setdefault("signals", {}).update({"spaces": len(spaces), "solutions": len(sols_on) or len((ctx.get("solutions") or {}))})
        elif role == "ST" and not body.get("points"):
            st = await strengths([x.get("text") or "" for x in rq_items], p)
            body["points"] = [{"title": x["title"], "body": x["body"]} for x in st]
            sources += [{"kind": "kb", "ref": None, "label": "삼성 공식 메시지", "url": x.get("src"), "tier": "T2"} for x in st if x.get("src")][:2]
            body["title"] = body.get("title") or "삼성이어야 하는 이유"
            body.setdefault("signals", {})["strengths"] = len(st)
            has_input = has_input or bool(st)
        elif role == "SC" and not body.get("table"):
            models = [x.get("model") for x in ctx.get("products") or [] if x.get("model")]
            models = list(dict.fromkeys(models))
            t = await spec_table(models)
            if t:
                body["table"] = t
                body["title"] = body.get("title") or f"제품 {len(t['columns']) - 1}종 사양 비교"
                body.setdefault("signals", {})["products"] = len(t["columns"]) - 1
                sources.append({"kind": "kb", "ref": ",".join(models), "label": "사내 카탈로그 스펙"})
                has_input = True
        elif role == "SD":
            model = rk.get("ref") or next((x.get("model") for x in ctx.get("products") or [] if x.get("model")), None)
            if model and not body.get("table"):
                t = await spec_table([model])
                if t:
                    body["table"] = t
                    body["title"] = body.get("title") or f"{model} 상세 사양"
                    has_input = True
        elif role == "CM" and body.get("table"):
            body.setdefault("signals", {})["competitors"] = len([c for c in body["table"]["columns"][1:] if not str(c).startswith("삼성")])
            body["signals"]["criteria"] = len(body["table"]["rows"])
            rq_texts = [x.get("text") or "" for x in rq_items]
            labels = [r.get("label") or "" for r in body["table"]["rows"]]
            hits = sum(1 for lb in labels if lb and any(lb in t or t in lb for t in rq_texts if t))
            body["signals"]["criteria_are_rq"] = bool(labels) and hits / len(labels) >= 0.6
        elif role == "BV" and not it:
            sp = spaces[0] if spaces else {"key": "sales_floor"}
            img = await space_image(p, sp.get("key") or "")
            if img:
                body["images"] = [img]
                body["title"] = "완성된 공간을 미리 본다"
        elif role == "IM":
            body["title"] = body.get("title") or "그래서 이번 제안은"
        if role in ("VP",) and not body.get("points"):
            kms = []
            for ln in lns:
                kms += [{"title": k.get("place_label") or "", "body": k.get("text")} for k in (ln.get("handoff") or {}).get("key_messages") or []]
            if kms:
                body["points"] = kms[:4]
                body.setdefault("signals", {})["km"] = len(kms[:4])
                has_input = True
        if role == "CH" and rq_items and not body.get("points"):
            body["points"] = [{"title": x.get("code"), "body": x.get("text")} for x in rq_items[:3]]
            body.setdefault("signals", {})["desired_state"] = True
            has_input = has_input or bool(lns)
        out[sh["id"]] = {"body": body, "sources": sources, "item": it, "has_input": has_input}
    return {"sheets": out, "links": lns, "items": items}


def section_has_input(key: str, lns: list[dict[str, Any]], p: dict[str, Any]) -> bool:
    if lns:
        return True
    ctx = p.get("ctx") or {}
    if key == "cases":
        return True
    if key == "spaceProducts":
        return bool(ctx.get("spaces")) and ctx.get("space_source") in ("birdseye", "scenario", "requirements", "user")
    if key == "spec":
        return bool([x for x in ctx.get("products") or [] if x.get("model")])
    if key == "solution":
        return any(v.get("state") == "on" for v in (ctx.get("solutions") or {}).values())
    return False


def allowed_from(p: dict[str, Any], bodies: list[dict[str, Any]], extra: list[Any]) -> set[str]:
    ctx = p.get("ctx") or {}
    srcs: list[Any] = [*bodies, (p.get("customer") or {}), p.get("title") or "", ctx.get("rq") or {}, ctx.get("products") or [],
                       ctx.get("spaces") or [], *extra]
    return C.allowed_numbers(*srcs)


RQ_RE = re.compile(r"\bR\d+\b")
