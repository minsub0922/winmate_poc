"""시트 내용 — 의미 본문(body) ↔ 템플릿 칸(slots) · 값 토큰 · 수치 검사(§10.12).

body(템플릿과 무관한 시트 내용, 시트 문서의 `draft` 에 둔다)
  {title, subtitle, message, points: [{title, body, kpi, tag, after}], bullets: [str], table: {columns, rows: [{label, cells: [{text, mark}]}]},
   kpis: [{label, value, unit, before, after}], series: {name, unit, categories, values, kind}, steps: [{when, title, body, tag}],
   images: [ImageRef], products: [{name, model, qty, body, tag}], spaces: [{name, body, chips}], headers: [str], notes, footnotes: [str]}
content(§5.3.1, 시트 문서의 `content`) = {eyebrow, title, subtitle, slots: {칸 id: 값(목록 항목마다 id)}, notes, footnotes}
칸 정의(slot_schema)는 export 카탈로그가 준다. 칸 이름 · 종류 · 개수(capacity.count) · 카드 필드(fields)로 결정적으로 채운다.
"""
from __future__ import annotations

import copy
import re
from typing import Any

from winmate_common.ids import new_id

from . import defs

NUM_RE = re.compile(r"(?<![A-Za-z0-9\[])(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(\s?(?:%|억\s?원|만\s?원|원|억|만|개|곳|대|명|일|시간|분|초|년|월|nit|인치|형|배|건|점|층|㎡|평|kWh|W|m))?")
SECTION_EYEBROW = {"mi": "MARKET INTELLIGENCE", "bigMi": "MARKET INTELLIGENCE", "vp": "VALUE PROPOSITION", "birdseye": "BIRD'S-EYE VIEW",
                   "spaceProducts": "SPACE × PRODUCTS", "solution": "SOLUTION", "cases": "REFERENCES", "why": "WHY SAMSUNG",
                   "spec": "SPECIFICATION", "spaceScenario": "SPACE SCENARIO"}


def lid(prefix: str = "l") -> str:
    return new_id(prefix)[-10:].lower().replace("_", "")


# ── 반입 내용 → body ───────────────────────────────────────
def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        return f"{v:,}" if isinstance(v, int) else (f"{v:,.0f}" if float(v).is_integer() else str(v))
    if isinstance(v, dict):
        return _s(v.get("text") or v.get("title") or v.get("label") or v.get("name") or v.get("value") or "")
    if isinstance(v, list):
        return " · ".join(_s(x) for x in v if _s(x))
    return str(v)


def body_from_content(role: str, item: dict[str, Any]) -> dict[str, Any]:
    """다른 기능의 반입 항목(content)을 body 로 — 모양을 몰라도 아는 키부터 읽는다."""
    c = item.get("content") or {}
    b: dict[str, Any] = {"title": _s(c.get("headline") or c.get("title") or item.get("sheet_title") or item.get("label")),
                         "subtitle": _s(c.get("subtitle") or c.get("size_label") or ""), "points": [], "bullets": [], "kpis": [],
                         "steps": [], "images": [], "products": [], "spaces": [], "footnotes": []}
    sig: dict[str, Any] = {}
    if c.get("message") or c.get("summary") or c.get("one_liner") or c.get("key_message"):
        b["message"] = _s(c.get("message") or c.get("summary") or c.get("one_liner") or c.get("key_message"))
    # 시장 규모 계열
    series = c.get("size_series") or c.get("series")
    if isinstance(series, list) and series and isinstance(series[0], dict) and ("year" in series[0] or "x" in series[0]):
        cats = [str(x.get("year") or x.get("x")) for x in series]
        vals = [x.get("value") for x in series]
        unit = series[0].get("unit") or ""
        b["series"] = {"name": c.get("size_label") or "시장 규모", "unit": unit, "categories": cats, "values": vals, "kind": "bar"}
        b["kpis"] = [{"label": f"{cats[i]}년", "value": _s(vals[i]), "unit": unit} for i in range(len(cats))][-3:]
        sig["years"] = [int(y) for y in cats if str(y).isdigit()]
    for key in ("pillars", "strengths", "values", "benefits", "insights", "drivers", "features"):
        for x in c.get(key) or []:
            if isinstance(x, dict):
                b["points"].append({"title": _s(x.get("title") or x.get("name") or x.get("label")),
                                    "body": _s(x.get("text") or x.get("body") or x.get("desc") or x.get("note") or x.get("description")),
                                    "tag": _s(x.get("audience") or x.get("tag") or ""), "kpi": _s(x.get("kpi") or "")})
            else:
                b["points"].append({"title": _s(x), "body": ""})
        if key == "pillars" and c.get(key):
            sig["km"] = len(c[key])
        if key == "strengths" and c.get(key):
            sig["strengths"] = len(c[key])
    for x in c.get("trends") or []:
        b["points"].append({"title": _s(x.get("title")), "body": _s(x.get("desc") or x.get("body")), "tag": _s(x.get("when")),
                            "after": _s(x.get("implication"))})
        sig["trends"] = len(c["trends"])
        sig["trends_linked"] = all(t.get("implication") for t in c["trends"])
    for x in c.get("ops_challenges") or []:
        b["steps"].append({"title": _s(x.get("stage")), "body": _s(x.get("problem"))})
    if c.get("ops_challenges"):
        sig["ops_steps"] = len(c["ops_challenges"])
        sig["ops_problems"] = [_s(x.get("stage")) for x in c["ops_challenges"]][:2]
    for key in ("strategy", "expansion", "lines", "bullets", "notes_list"):
        v = c.get(key)
        if isinstance(v, list):
            b["bullets"] += [_s(x) for x in v if _s(x)]
    if c.get("expansion"):
        sig["expansion"] = True
    for x in c.get("structure") or []:
        b["kpis"].append({"label": _s(x.get("label")), "value": _s(x.get("value")), "unit": _s(x.get("unit"))})
    for sec in c.get("sections") or []:
        b["points"].append({"title": _s(sec.get("name")), "body": _s(sec.get("direction")), "tag": _s(sec.get("code"))})
        b["bullets"] += [_s(x) for x in sec.get("lines") or [] if _s(x)]
    # 비교표(경쟁 · 스펙)
    if c.get("criteria") and c.get("columns") and c.get("cells"):
        cols = [_s(x) for x in c["columns"]]
        rows = []
        for i, crit in enumerate(c["criteria"]):
            cells = c["cells"][i] if i < len(c["cells"]) else []
            marks = (c.get("verdict_marks") or [[]] * len(c["criteria"]))[i] if c.get("verdict_marks") else []
            rows.append({"label": _s(crit), "cells": [{"text": _s(x), "mark": (marks[j] if j < len(marks) else None)} for j, x in enumerate(cells)]})
        b["table"] = {"columns": ["비교 항목", *cols], "rows": rows}
        sig["competitors"] = len([x for x in cols if x not in ("삼성", "삼성 제안", "Samsung")])
        sig["criteria"] = len(rows)
    elif c.get("rows") and c.get("columns"):
        cols = [_s(x.get("label") if isinstance(x, dict) else x) for x in c["columns"]]
        rows = []
        for r in c["rows"]:
            if r.get("hidden"):
                continue
            cells = [{"text": _s(x.get("text") if isinstance(x, dict) else x), "mark": None,
                      "pending": bool(isinstance(x, dict) and x.get("pending"))} for x in r.get("cells") or []]
            rows.append({"label": _s(r.get("label")), "cells": cells, "highlight": bool(r.get("highlighted"))})
        b["table"] = {"columns": ["항목", *cols], "rows": rows}
        sig["products"] = len(cols)
    elif isinstance(c.get("table"), dict):
        t = c["table"]
        b["table"] = {"columns": [_s(x) for x in t.get("columns") or []],
                      "rows": [{"label": _s((r or [""])[0]) if isinstance(r, list) else _s(r.get("label")),
                                "cells": [{"text": _s(x)} for x in ((r[1:] if isinstance(r, list) else r.get("cells")) or [])]}
                               for r in t.get("rows") or []]}
    for x in c.get("personas") or []:
        b["points"].append({"title": _s(x.get("role")), "body": _s(x.get("goal")), "after": _s(x.get("pain")), "tag": _s(x.get("context"))})
    for x in c.get("journey") or []:
        b["steps"].append({"title": _s(x.get("stage")), "body": _s(x.get("pain")), "tag": _s(x.get("touchpoint")),
                           "after": _s(x.get("opportunity"))})
    if c.get("journey"):
        sig["journey"] = True
    slots = c.get("slots")
    if isinstance(slots, dict) and any(k in slots for k in ("action", "trigger", "response")):
        for k, label in (("trigger", "계기"), ("action", "행동"), ("response", "반응"), ("exception", "예외"), ("metric", "지표")):
            v = slots.get(k)
            if v:
                b["steps"].append({"when": label, "title": _s(v), "body": ""})
        if c.get("purpose"):
            b["message"] = b.get("message") or _s(c.get("purpose"))
    for x in c.get("scenes") or []:
        b["steps"].append({"when": _s(x.get("time") or x.get("label")), "title": _s(x.get("title")), "body": _s(x.get("story") or x.get("text"))})
    if c.get("scenes"):
        sig["scenes"] = len(c["scenes"])
    prods = c.get("products")
    if isinstance(prods, list):
        for x in prods:
            if isinstance(x, dict):
                b["products"].append({"name": _s(x.get("name") or x.get("label")), "model": _s(x.get("model") or x.get("model_code")),
                                      "qty": x.get("qty"), "body": _s(x.get("body") or x.get("desc"))})
            elif _s(x):
                b["products"].append({"name": _s(x), "model": "", "qty": None, "body": ""})
    for key in ("image", "images", "photo", "photos"):
        v = c.get(key)
        for x in (v if isinstance(v, list) else [v] if v else []):
            if isinstance(x, dict):
                b["images"].append(image_ref(x))
    for f in c.get("footnotes") or []:
        b["footnotes"].append(_s(f))
    b["signals"] = sig
    return {k: v for k, v in b.items() if v not in (None, "", [], {})} | {"signals": sig}


def image_ref(x: dict[str, Any]) -> dict[str, Any]:
    kind = x.get("kind") or ("file" if x.get("file_id") else "kb_image" if str(x.get("id") or "").startswith("img_") else "image_job")
    return {"kind": kind, "id": x.get("id") or x.get("kb_image_id") or x.get("file_id") or x.get("image_version_id") or x.get("version_id"),
            "file_id": x.get("file_id"), "rights": x.get("rights") or ("official" if kind == "kb_image" else "unknown"),
            "caption_rule": x.get("caption_rule") or caption_for(x.get("rights")), "source_url": x.get("source_url") or x.get("url") or x.get("page_url"),
            "label": x.get("label") or x.get("title") or x.get("alt") or ""}


def caption_for(rights: str | None) -> str:
    return {"official": "예시 사진(삼성 공식 이미지)", "customer_case": "도입사례 사진", "generated": "생성 이미지",
            "customer": "고객 제공 사진"}.get(rights or "", "예시 사진(삼성 공식 이미지)")


def merge_body(base: dict[str, Any], llm: dict[str, Any] | None) -> dict[str, Any]:
    """LLM 본문을 기본 본문 위에 — 표 · 계열 · 이미지 · 제품은 기본(입력) 것을 지킨다."""
    if not llm:
        return copy.deepcopy(base)
    out = copy.deepcopy(base)
    for k in ("title", "subtitle", "message", "notes"):
        if llm.get(k):
            out[k] = llm[k]
    for k in ("points", "bullets", "steps", "headers"):
        if llm.get(k):
            out[k] = llm[k]
    if llm.get("kpis") and not base.get("series"):
        out["kpis"] = llm["kpis"]
    if llm.get("table") and not base.get("table"):
        out["table"] = llm["table"]
    if llm.get("products") and not base.get("products"):
        out["products"] = llm["products"]
    if llm.get("footnotes"):
        out["footnotes"] = list(dict.fromkeys((base.get("footnotes") or []) + llm["footnotes"]))
    sig = dict(base.get("signals") or {})
    sig.update({k: v for k, v in (llm.get("signals") or {}).items() if v not in (None, "", [], {})})
    out["signals"] = sig
    return out


# ── body → 칸(slots) ───────────────────────────────────────
TEXT_KEYS = {
    "title": ("title",), "subtitle": ("subtitle",), "message": ("message",), "message_sub": ("subtitle",), "conclusion": ("message",),
    "summary": ("message",), "one_liner": ("message",), "outlook_body": ("message",), "details": ("subtitle",), "chart_note": ("subtitle",),
    "quote": ("message",), "space": ("space_name",), "solution_name": ("solution_name",), "customer": ("customer",),
    "chart_title": ("chart_title",), "image_caption": ("image_caption",), "caption": ("image_caption",), "when": ("when",),
    "total": ("message",), "assumptions": ("notes_short",), "who": ("who",), "outlook_title": ("chart_title",),
}


def _count(slot: dict[str, Any]) -> int:
    cap = slot.get("capacity") or {}
    return int(cap.get("count") or slot.get("boxes") or 1)


def _fields(slot: dict[str, Any]) -> list[str]:
    return [f.get("key") for f in slot.get("fields") or [] if f.get("key")]


def _kpi(x: dict[str, Any] | str) -> dict[str, Any] | str:
    if isinstance(x, str):
        return x
    out = {"value": _s(x.get("value")) or "[00]", "label": _s(x.get("label"))}
    if x.get("unit"):
        out["unit"] = _s(x.get("unit"))
    if x.get("sub"):
        out["sub"] = _s(x.get("sub"))
    return out


def _card(fields: list[str], src: dict[str, Any], n: int, *, kind: str = "point") -> dict[str, Any]:
    card: dict[str, Any] = {"id": lid("c")}
    for f in fields:
        v: Any = None
        if f == "no":
            v = f"{n:02d}" if kind != "step" else str(n)
        elif f in ("title", "name"):
            v = src.get("title") or src.get("name")
        elif f in ("body", "text", "desc", "note", "story"):
            v = src.get("body") or src.get("desc")
        elif f in ("tag", "role"):
            v = src.get("tag") or (src.get("role") if f == "role" else None)
        elif f == "kpi":
            v = _kpi(src["kpi"]) if isinstance(src.get("kpi"), dict) else (src.get("kpi") or None)
        elif f in ("when", "time", "start"):
            v = src.get("when") or src.get("time")
        elif f in ("so", "opportunity", "right", "after"):
            v = src.get("after") or src.get("so")
        elif f in ("left", "before", "pain"):
            v = src.get("before") or (src.get("body") if f == "left" else src.get("after") if f == "pain" else None)
        elif f == "label":
            v = src.get("title") or src.get("label")
        elif f == "mid":
            v = src.get("mid") or src.get("body")
        elif f == "bullets":
            v = src.get("bullets") or None
        elif f == "model":
            v = src.get("model")
        elif f == "qty":
            v = src.get("qty")
        elif f == "chips":
            v = src.get("chips") or None
        elif f == "letter":
            v = chr(64 + n)
        elif f in ("x", "y"):
            v = src.get(f)
        elif f == "change":
            v = src.get("change")
        elif f == "action":
            v = src.get("title")
        elif f == "touchpoint":
            v = src.get("tag")
        elif f == "emotion":
            v = src.get("emotion")
        elif f == "share":
            v = src.get("share")
        elif f == "owner":
            v = src.get("owner") or src.get("tag")
        elif f == "days":
            v = src.get("days")
        elif f == "quote":
            v = src.get("quote")
        elif f == "who":
            v = src.get("who")
        elif f == "image":
            v = src.get("image")
        elif f == "end":
            v = src.get("end")
        if v not in (None, "", []):
            card[f] = v
    return card


def fill_slots(schema: dict[str, Any] | None, body: dict[str, Any], *, section_key: str, sheet: dict[str, Any],
               p: dict[str, Any], section_no: int = 0) -> dict[str, Any]:
    """칸 정의에 맞춰 content 를 만든다. 칸 정의가 없으면 범용 칸(title · subtitle · bullets · table)."""
    slots_def = list((schema or {}).get("slots") or [])
    if not slots_def:
        slots_def = [{"id": "title", "type": "text"}, {"id": "subtitle", "type": "text"}, {"id": "bullets", "type": "bullets", "capacity": {"count": 6}},
                     {"id": "table", "type": "table"}]
    used_points = 0
    used_steps = 0
    used_images = 0
    used_kpis = 0
    slots: dict[str, Any] = {}
    points = list(body.get("points") or [])
    steps = list(body.get("steps") or [])
    products = list(body.get("products") or [])
    spaces = list(body.get("spaces") or [])
    kpis = list(body.get("kpis") or [])
    images = list(body.get("images") or [])
    bullets = list(body.get("bullets") or [])
    extra = {"space_name": (sheet.get("repeat_key") or {}).get("label") or sheet.get("title"),
             "solution_name": (defs.SOLUTIONS.get(sheet.get("solution_code") or "") or {}).get("name"),
             "customer": body.get("customer") or (p.get("customer") or {}).get("name"),
             "chart_title": (body.get("series") or {}).get("name"), "image_caption": next((i.get("caption_rule") for i in images), None),
             "when": body.get("when"), "who": body.get("who"), "notes_short": body.get("notes")}
    for sd in slots_def:
        sid = sd.get("id")
        typ = sd.get("type")
        if sid in ("eyebrow",):
            slots[sid] = f"{section_no:02d} · {SECTION_EYEBROW.get(section_key, '')}" if section_no else SECTION_EYEBROW.get(section_key, "")
            continue
        if typ == "source" or sid == "sources":
            src = [x for x in body.get("source_list") or [] if x.get("label")]
            if src:
                slots[sid] = [{"id": lid("s"), "label": _s(x.get("label")), **({"url": x["url"]} if x.get("url") else {})} for x in src[:3]]
            continue
        if sid in ("footer", "logo") or typ == "logo":
            continue
        if typ in ("text", "caption", "number"):
            if sid in TEXT_KEYS:
                for k in TEXT_KEYS[sid]:
                    v = body.get(k) if k in body else extra.get(k)
                    if v:
                        slots[sid] = _s(v)
                        break
            elif sid in ("headers", "labels", "row_labels") and body.get("headers"):
                slots[sid] = [_s(x) for x in body["headers"]][:_count(sd)]
            continue
        if typ == "bullets":
            n = _count(sd)
            src = bullets or [pt.get("title") for pt in points if pt.get("title")]
            if src:
                slots[sid] = [{"id": lid("b"), "text": _s(x)} for x in src[:n]]
            continue
        if typ == "kpi":
            n = _count(sd)
            if kpis[used_kpis:]:
                vals = [dict(_kpi(k), id=lid("k")) if isinstance(_kpi(k), dict) else _kpi(k) for k in kpis[used_kpis:used_kpis + n]]
                slots[sid] = vals if n > 1 else vals[0]
                used_kpis += min(n, len(kpis) - used_kpis)
            continue
        if typ == "table":
            t = body.get("table")
            if t:
                slots[sid] = {"columns": list(t.get("columns") or []),
                              "rows": [{"id": r.get("id") or lid("r"), "label": _s(r.get("label")),
                                        "cells": [{"text": _s(c.get("text") if isinstance(c, dict) else c),
                                                   "mark": (c.get("mark") if isinstance(c, dict) else None)} for c in r.get("cells") or []],
                                        **({"highlight": True} if r.get("highlight") else {})}
                                       for r in t.get("rows") or []]}
            continue
        if typ == "chart":
            se = body.get("series")
            if se and se.get("categories"):
                slots[sid] = {"type": se.get("kind") or "bar", "categories": list(se["categories"]),
                              "series": [{"name": se.get("name") or "", "values": list(se.get("values") or [])}],
                              **({"unit": se["unit"]} if se.get("unit") else {})}
            continue
        if typ in ("image",):
            n = _count(sd)
            if images[used_images:]:
                chosen = images[used_images:used_images + n]
                used_images += len(chosen)
                vals = [{"id": lid("i"), **im} for im in chosen]
                slots[sid] = vals if n > 1 else vals[0]
            continue
        if typ == "card":
            n = _count(sd)
            fields = _fields(sd)
            fs = set(fields)
            if {"model", "qty"} & fs and products:
                src_list = [{"title": pr.get("name"), "model": pr.get("model"), "qty": pr.get("qty"), "body": pr.get("body"),
                             "tag": pr.get("tag"), "image": pr.get("image")} for pr in products]
                kind = "product"
            elif {"when", "time", "start", "days", "touchpoint", "action"} & fs and steps[used_steps:]:
                src_list = steps[used_steps:]
                used_steps += min(n, len(src_list))
                kind = "step"
            elif "chips" in fs and {"x", "y"} & fs and spaces:
                src_list = [{"title": s.get("name"), "body": s.get("body"), "chips": s.get("chips")} for s in spaces]
                kind = "space"
            elif {"before", "after", "change"} <= fs and kpis:
                src_list = [{"title": k.get("label"), "before": k.get("before"), "after": k.get("after") or k.get("value"),
                             "change": k.get("change")} for k in kpis]
                kind = "kpi"
            else:
                src_list = points[used_points:]
                if src_list:
                    used_points += min(n, len(src_list))
                elif steps[used_steps:]:
                    src_list = steps[used_steps:]
                    used_steps += min(n, len(src_list))
                elif {"title", "body"} <= fs and any(s.get("body") for s in steps):
                    src_list = [s for s in steps if s.get("body")]     # 단계별 문제(CB-C pains)
                kind = "point"
            if src_list:
                cards = [_card(fields, s, i + 1, kind=kind) for i, s in enumerate(src_list[:n])]
                slots[sid] = cards if (n > 1 or len(cards) > 1) else cards[0]
            continue
    return {"eyebrow": slots.pop("eyebrow", SECTION_EYEBROW.get(section_key, "")), "title": _s(body.get("title")) or sheet.get("title") or "",
            "subtitle": _s(body.get("subtitle") or ""), "slots": {k: v for k, v in slots.items() if k not in ("title", "subtitle")},
            "notes": _s(body.get("notes") or ""), "footnotes": [{"text": f} for f in body.get("footnotes") or []]}


# ── 값 토큰 ────────────────────────────────────────────────
def fact_display(f: dict[str, Any], facts_by_key: dict[str, dict[str, Any]] | None = None) -> str:
    if f.get("kind") == "derived" and f.get("formula"):
        v = eval_formula(f["formula"], facts_by_key or {})
        if v is not None:
            return f"{v}{f.get('unit') or ''}"
        return f.get("placeholder") or "[00]"
    if f.get("value") not in (None, ""):
        return f"{f['value']}{f.get('unit') or ''}"
    return f.get("placeholder") or "[00]"


def eval_formula(formula: str, facts_by_key: dict[str, dict[str, Any]]) -> str | None:
    m = re.fullmatch(r"\s*([a-z_][a-z0-9_]*)\s*([*+])\s*(\d+(?:\.\d+)?)\s*", formula or "")
    if not m:
        return None
    base = facts_by_key.get(m.group(1))
    if not base or base.get("value") in (None, "") or base.get("status") == "placeholder":
        return None
    try:
        a = float(str(base["value"]).replace(",", ""))
    except ValueError:
        return None
    b = float(m.group(3))
    v = a * b if m.group(2) == "*" else a + b
    return f"{int(v):,}" if float(v).is_integer() else f"{v:,.1f}"


def resolve_text(text: str, facts: dict[str, dict[str, Any]], *, mode: str = "show", by_key: dict[str, dict[str, Any]] | None = None) -> str:
    """mode: show(표시) · dash(노트로 옮긴 값은 「—」)."""
    def rep(m: re.Match[str]) -> str:
        f = facts.get(m.group(1))
        if not f:
            return "[00]"
        if mode == "dash" and f.get("status") != "confirmed" and f.get("moved_to_note"):
            return "—"
        return fact_display(f, by_key)
    return defs.FACT_TOKEN_RE.sub(rep, text or "")


def walk_strings(obj: Any, fn: Any, path: str = "") -> Any:
    """모든 문자열에 fn(text, path) 을 적용한 사본."""
    if isinstance(obj, str):
        return fn(obj, path)
    if isinstance(obj, list):
        return [walk_strings(x, fn, f"{path}/{i}") for i, x in enumerate(obj)]
    if isinstance(obj, dict):
        return {k: (v if k in ("id", "kind", "rights", "file_id", "mark") else walk_strings(v, fn, f"{path}/{k}")) for k, v in obj.items()}
    return obj


def display_content(content: dict[str, Any], facts: dict[str, dict[str, Any]], *, mode: str = "show") -> dict[str, Any]:
    by_key = {f.get("key"): f for f in facts.values()}
    return walk_strings(content, lambda t, _p: resolve_text(t, facts, mode=mode, by_key=by_key))


def tokens_in(obj: Any) -> list[tuple[str, str]]:
    """(fact_id, path) 목록."""
    out: list[tuple[str, str]] = []

    def fn(t: str, path: str) -> str:
        for m in defs.FACT_TOKEN_RE.finditer(t or ""):
            out.append((m.group(1), path))
        return t
    walk_strings(obj, fn)
    return out


# ── 수치 검사(§10.12 V1) ───────────────────────────────────
def norm_number(s: str) -> str:
    return s.replace(",", "").replace(" ", "").strip()


def numbers_of(text: str) -> set[str]:
    return {norm_number(m.group(1)) for m in NUM_RE.finditer(text or "")}


def allowed_numbers(*sources: Any) -> set[str]:
    out: set[str] = set()

    def fn(t: str, _p: str) -> str:
        out.update(numbers_of(t))
        return t
    for s in sources:
        if isinstance(s, (int, float)):
            out.add(norm_number(str(s)))
        else:
            walk_strings(s, fn)
    return out


def is_exempt(num: str, unit: str, text: str, start: int) -> bool:
    """목록 번호 · 시트 번호 · 연도(입력에 있을 때만 → 호출자가 확인) · 한 자리 서수는 예외."""
    if not unit and len(num) <= 1:
        return True
    if not unit and re.fullmatch(r"(19|20)\d{2}", num):
        return False
    if unit and unit.strip() in ("년", "월") and len(num) <= 2:
        return True
    pre = text[max(0, start - 2):start]
    if pre.endswith("R") or pre.endswith("p.") or pre.endswith("v"):
        return True
    return False


def placeholder_for(unit: str) -> str:
    u = (unit or "").strip()
    if u in ("일", "명"):
        return f"[0]{u}"
    if u in ("억원", "억 원"):
        return "[00]억 원"
    return f"[00]{u}" if u else "[00]"


def ground_numbers(text: str, allowed: set[str]) -> tuple[str, list[dict[str, Any]]]:
    """입력에 없는 수치는 플레이스홀더로. → (새 글, [{num, unit, placeholder, pre, post}])"""
    misses: list[dict[str, Any]] = []
    out: list[str] = []
    last = 0
    spans = [(t.start(), t.end()) for t in defs.FACT_TOKEN_RE.finditer(text or "")]
    for m in NUM_RE.finditer(text or ""):
        if any(a <= m.start() < b for a, b in spans):
            continue     # 값 토큰 안의 글자(fct_01…)
        num = norm_number(m.group(1))
        unit = (m.group(2) or "").strip()
        if num in allowed or is_exempt(num, unit, text, m.start()):
            continue
        ph = placeholder_for(unit)
        out.append(text[last:m.start()])
        out.append(ph)
        last = m.end()
        misses.append({"num": num, "unit": unit, "placeholder": ph, "pre": text[max(0, m.start() - 24):m.start()].strip(),
                       "post": text[m.end():m.end() + 16].strip()})
    out.append(text[last:])
    return "".join(out), misses


def ground_body(body: dict[str, Any], allowed: set[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    misses: list[dict[str, Any]] = []

    def fn(t: str, path: str) -> str:
        if path.startswith("/signals") or path.startswith("/images") or path.startswith("/series/categories"):
            return t
        new, m = ground_numbers(t, allowed)
        for x in m:
            x["path"] = path
        misses.extend(m)
        return new
    grounded = walk_strings({k: v for k, v in body.items() if k != "signals"}, fn)
    grounded["signals"] = body.get("signals") or {}
    if body.get("series"):
        grounded["series"] = body["series"]
    return grounded, misses


def placeholders_in(text: str) -> list[re.Match[str]]:
    return list(defs.PLACEHOLDER_RE.finditer(text or ""))


def label_near(pre: str) -> str:
    """플레이스홀더 앞 글에서 값 이름(「유지보수 응답 시간」)."""
    t = re.sub(r"[\[\]{}()·:|]", " ", pre or "").strip()
    t = re.sub(r"\s+", " ", t)
    words = t.split(" ")
    return " ".join(words[-3:]).strip() or "수치"


# ── 내보내기 칸 값 ─────────────────────────────────────────
def export_slots(content: dict[str, Any], facts: dict[str, dict[str, Any]], *, image_files: dict[str, str] | None = None,
                 tbd_mode: str = "keep_marks") -> tuple[dict[str, Any], list[str]]:
    """content.slots → export 칸 값(id 없이, 토큰 풀어서). → (slots, 노트로 옮길 문장)"""
    to_notes: list[str] = []
    by_key = {f.get("key"): f for f in facts.values()}

    def res(t: str) -> str:
        out = resolve_text(t, facts, by_key=by_key, mode="dash")
        if tbd_mode == "move_to_notes" and (defs.PLACEHOLDER_RE.search(out) or defs.CONFIRM_MARK_RE.search(out)):
            to_notes.append(f"[확정 필요] {out}")
            return "—"
        return out

    def val(v: Any) -> Any:
        if isinstance(v, str):
            return res(v)
        if isinstance(v, list):
            items = []
            for x in v:
                if isinstance(x, dict) and set(x) <= {"id", "text"} and "text" in x:
                    items.append(res(x["text"]))
                else:
                    items.append(val(x))
            return items
        if isinstance(v, dict):
            if "rows" in v and "columns" in v:
                rows = []
                for r in v.get("rows") or []:
                    if isinstance(r, dict):
                        rows.append([res(r.get("label") or "")] + [res(c.get("text") if isinstance(c, dict) else str(c)) for c in r.get("cells") or []])
                    else:
                        rows.append([val(c) for c in r])
                out = {"columns": [res(c) for c in v["columns"]], "rows": rows}
                hl = [i for i, r in enumerate(v.get("rows") or []) if isinstance(r, dict) and r.get("highlight")]
                if hl:
                    out["highlight_rows"] = hl
                if any(str(c).startswith("삼성") for c in v["columns"]):
                    out["highlight_col"] = next(i for i, c in enumerate(v["columns"]) if str(c).startswith("삼성"))
                return out
            if v.get("kind") in ("kb_image", "file", "image_job") or "rights" in v:
                fid = v.get("file_id") or (image_files or {}).get(v.get("id") or "")
                if not fid:
                    return None
                return {"file_id": fid, **({"caption": v.get("caption_rule")} if v.get("caption_rule") else {}),
                        **({"ai_generated": True} if v.get("rights") == "generated" else {})}
            return {k: val(x) for k, x in v.items() if k != "id" and val(x) is not None}
        return v

    out = {}
    for k, v in (content.get("slots") or {}).items():
        vv = val(v)
        if vv not in (None, [], {}):
            out[k] = vv
    for k in ("title", "subtitle", "eyebrow"):
        if content.get(k):
            out[k] = res(content[k])
    return out, to_notes


# ── 줄(기존 제안서 활용 · 원본 대조) ───────────────────────
LINE_SKIP_KEYS = {"id", "kind", "rights", "file_id", "url", "type", "unit", "mark", "no", "letter", "x", "y", "image", "caption_rule",
                  "highlight", "ref", "categories", "series", "columns", "chips", "image_id", "version_id"}


def content_lines(content: dict[str, Any]) -> list[tuple[str, str]]:
    """시트 칸 안 글을 줄로 — (JSON 포인터 경로, 글). 경로는 시트 PATCH 의 path 로 그대로 쓴다. 이미지 · 숫자뿐인 칸은 뺀다."""
    out: list[tuple[str, str]] = []

    def walk(v: Any, path: str) -> None:
        if isinstance(v, str):
            t = v.strip()
            if len(t) >= 2 and not re.fullmatch(r"[\[\]0-9,.%\s]*\S{0,2}", t):
                out.append((path, v))
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, f"{path}/{i}")
        elif isinstance(v, dict):
            if v.get("file_id") or v.get("kind") in ("kb_image", "image_job", "file", "image"):
                return
            for k, x in v.items():
                if k not in LINE_SKIP_KEYS:
                    walk(x, f"{path}/{k}")
    sub = (content or {}).get("subtitle")
    if isinstance(sub, str) and len(sub.strip()) >= 2:
        out.append(("/subtitle", sub))
    walk((content or {}).get("slots") or {}, "/slots")
    return out
