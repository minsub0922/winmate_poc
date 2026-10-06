"""넘김 묶음(§6.12) · ProposalHandoff v1(§6.14) · 내보내기 원본 — 같은 코드 경로에서 익명 · 대외비 · 검증 규칙을 적용한다."""
from __future__ import annotations

import copy
import re
from typing import Any

from winmate_common.ids import now_iso

from . import anonymize, config, layout, rules, verify, views

ROLE = {"MS+TR": "MS", "MS": "MS", "TR": "TR", "CB": "CB", "US": "US", "CP": "CP", "IM": "IM"}


def section_rows(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """MI4 매핑 행 = 포함 시트 + 섹션에 없는 시트(추가 후보). 표준에서 규칙으로 뺀 MI 시사점은 숨긴다."""
    return [s for s in slides if s.get("included") or (not s.get("in_section", True) and s.get("sheet_type") != "IM")]


def row_status(s: dict[str, Any]) -> tuple[str, str]:
    if not s.get("in_section", True) and not s.get("included"):
        return "add", "섹션에 없는 시트 · 추가"
    n = int(s.get("fix_open") or 0)
    if n:
        return "warn", f"[확정 필요] {n}건"
    return "ok", "그대로 들어가요"


class Ctx:
    """묶음 한 번 만들 때의 맥락 — 표기 · 대외비 · 옵션."""

    def __init__(self, analysis: dict[str, Any], version: dict[str, Any], *, target: str, options: dict[str, Any] | None = None,
                 confirmations: dict[str, Any] | None = None, named: bool = False, included_cmp: list[str] | None = None):
        self.a = analysis
        self.v = version
        self.target = target
        self.options = {"cite_sources": True, "fix_notes": True, "link_why": True, **(options or {})}
        self.conf = confirmations or {}
        self.named = named
        comps = anonymize.live(analysis.get("competitors") or [])
        table = ((version.get("document") or {}).get("competitor") or {}).get("table") or {}
        in_table = [c for c in table.get("columns") or [] if c != "samsung"]
        ids = included_cmp or [c["id"] for c in comps if c["id"] in in_table] or [c["id"] for c in comps]
        anon = analysis.get("anonymize", True)
        real = target in ("competitor", "export_internal") or named or (not anon and self.conf.get("real_names") is True)
        if real:
            self.names = {c["id"]: c.get("real_name") or anonymize.workspace_label(c) for c in comps}
            self.scrub = False
        else:
            # 익명(켜짐) 또는 익명 꺼짐인데 실명 확인이 없을 때(묻기 2 기본값 = 익명)
            self.names = anonymize.export_map(comps, True, analysis.get("naming_mode", "letter") if anon else "letter", ids)
            self.scrub = True
        self.included_ids = ids
        self.exclude_conf = self.conf.get("confidential") != "include"
        self.srcs = version.get("sources") or {}
        self.claims = version.get("claims") or {}

    def clean(self, obj: Any) -> Any:
        if not self.scrub:
            return obj
        # 넣지 않은(삭제 · 표 밖) 경쟁사 이름은 글자 대신 '다른 경쟁사' — 다시 붙인 글자와 겹치지 않게
        full = {c["id"]: self.names.get(c["id"]) or "다른 경쟁사" for c in self.a.get("competitors") or []}
        return anonymize.scrub(obj, self.a.get("competitors") or [], full)

    def confidential_claim(self, cid: str | None) -> bool:
        if not cid:
            return False
        for c in self.v.get("citations") or []:
            if c.get("claim_id") == cid and not c.get("dropped"):
                if (self.srcs.get(c["source_id"]) or {}).get("classification") == "confidential":
                    return True
        return False


def _footnotes(ctx: Ctx, claim_ids: list[str]) -> tuple[list[dict[str, Any]], dict[str, int], list[dict[str, Any]]]:
    nums: dict[str, int] = {}
    notes: list[dict[str, Any]] = []
    srcs_out: list[dict[str, Any]] = []
    for cid in claim_ids:
        for cit in ctx.v.get("citations") or []:
            if cit.get("claim_id") != cid or cit.get("dropped"):
                continue
            sid = cit["source_id"]
            if sid in nums:
                continue
            src = ctx.srcs.get(sid) or {}
            if src.get("kind") == "user":
                continue
            nums[sid] = len(nums) + 1
            st = "원문 일치" if cit.get("status") == "matched" else "확인 필요"
            notes.append({"n": nums[sid], "text": views.footnote(src, cit), "status": st})
            out = {"kind": src.get("kind"), "ref": sid, "label": views.footnote(src, cit)}
            if src.get("url") and src.get("kind") in ("web", "kb_case", "kb_official"):
                out["url"] = src["url"]
            if src.get("tier"):
                out["tier"] = src["tier"]
            srcs_out.append(out)
    return notes, nums, srcs_out


def _fns(ctx: Ctx, cid: str | None, nums: dict[str, int]) -> list[int]:
    if not cid:
        return []
    return sorted({nums[c["source_id"]] for c in ctx.v.get("citations") or [] if c.get("claim_id") == cid and not c.get("dropped") and c["source_id"] in nums})


def _status(ctx: Ctx, cid: str | None) -> str:
    return (ctx.claims.get(cid or "") or {}).get("status", "missing")


def _text(ctx: Ctx, cid: str | None, fact_check: list[dict[str, Any]]) -> str:
    c = ctx.claims.get(cid or "") or {}
    t = c.get("text", "")
    if ctx.confidential_claim(cid) and ctx.exclude_conf and ctx.target not in ("competitor", "export_internal"):
        masked, nums = verify.mask_unsupported(t, [])
        if nums:
            fact_check.append({"text": c.get("metric_label") or t[:40], "placeholder": verify.placeholder_for(nums[0]), "reason": "대외비 자료라 뺐어요",
                               "claim_id": cid})
            return masked
    return t


def sheet_claims(ctx: Ctx, sheet_type: str) -> list[str]:
    area = layout.AREA_OF_TYPE.get(sheet_type)
    if not area:
        return [cid for a in rules.AREAS for cid in views.claim_order(ctx.v.get("document") or {}, a)][:12]
    order = views.claim_order(ctx.v.get("document") or {}, area)
    if sheet_type == "TR":
        blk = (ctx.v.get("document") or {}).get("market") or {}
        return [t.get("claim") for t in blk.get("trends") or [] if t.get("claim")]
    if sheet_type == "MS":
        blk = (ctx.v.get("document") or {}).get("market") or {}
        ids = [p.get("claim") for p in blk.get("size_series") or []] + [(blk.get("cagr") or {}).get("claim")]
        return [i for i in ids if i] or order
    return order


def sheet_content(ctx: Ctx, sheet: dict[str, Any], nums: dict[str, int], fact_check: list[dict[str, Any]]) -> dict[str, Any]:
    st = sheet.get("sheet_type")
    doc = ctx.v.get("document") or {}
    if st in ("MS", "MS+TR", "TR"):
        mk = doc.get("market") or {}
        out: dict[str, Any] = {}
        if st in ("MS", "MS+TR"):
            out["size_label"] = mk.get("size_label", "")
            out["size_series"] = [{"year": p.get("year"), "value": p.get("value"), "unit": p.get("unit") or mk.get("size_unit", ""),
                                   "status": _status(ctx, p.get("claim")), "footnote_n": (_fns(ctx, p.get("claim"), nums) or [None])[0],
                                   "text": _text(ctx, p.get("claim"), fact_check)} for p in mk.get("size_series") or []]
            if mk.get("cagr"):
                cg = mk["cagr"]
                out["cagr"] = {"value": cg.get("value"), "period": cg.get("period", ""), "status": _status(ctx, cg.get("claim")),
                               "footnote_ns": _fns(ctx, cg.get("claim"), nums), "text": _text(ctx, cg.get("claim"), fact_check)}
        if st in ("TR", "MS+TR"):
            out["trends"] = [{"title": t.get("title", ""), "when": t.get("when"), "desc": _text(ctx, t.get("claim"), fact_check),
                              "implication": t.get("implication", ""), "footnote_ns": _fns(ctx, t.get("claim"), nums)} for t in mk.get("trends") or []]
            out["regulations"] = [{"title": r.get("title", ""), "desc": _text(ctx, r.get("claim"), fact_check), "footnote_ns": _fns(ctx, r.get("claim"), nums)}
                                  for r in mk.get("regulations") or []]
        return out
    if st == "CB":
        cu = doc.get("customer") or {}
        return {"summary": _text(ctx, cu.get("summary"), fact_check),
                "strategy": [_text(ctx, c, fact_check) for c in cu.get("strategy") or []],
                "expansion": [_text(ctx, c, fact_check) for c in cu.get("expansion") or []],
                "structure": [{"label": s.get("label", ""), "value": s.get("value", ""), "text": _text(ctx, s.get("claim"), fact_check)} for s in cu.get("structure") or []],
                "ops_challenges": [{"stage": o.get("stage", ""), "problem": _text(ctx, o.get("claim"), fact_check), "footnote_ns": _fns(ctx, o.get("claim"), nums)}
                                   for o in cu.get("ops_challenges") or []]}
    if st == "US":
        us = doc.get("user") or {}
        return {"personas": [{k: p.get(k, "") for k in ("role", "goal", "pain", "context")} for p in us.get("personas") or []],
                "journey": [{k: j.get(k, "") for k in ("stage", "touchpoint", "pain", "opportunity")} for j in us.get("journey") or []],
                "composition": [{"label": c.get("label", ""), "value": c.get("value"), "unit": c.get("unit", "%")} for c in us.get("composition") or []]}
    if st == "CP":
        return comparison(ctx, nums, fact_check)
    if st == "IM":
        im = doc.get("implications") or {}
        return {k: im.get(k) for k in ("findings", "implications", "direction", "quadrants", "conclusion") if im.get(k) is not None}
    return {}


def comparison(ctx: Ctx, nums: dict[str, int] | None = None, fact_check: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    cp = (ctx.v.get("document") or {}).get("competitor") or {}
    table = cp.get("table") or {}
    crit = {c["id"]: c for c in ctx.a.get("criteria") or []}
    cols = [c for c in table.get("columns") or [] if c == "samsung" or c in ctx.names]
    labels = [("삼성" if c == "samsung" else ctx.names.get(c, "경쟁사")) for c in cols]
    rows = []
    criteria = []
    for crt in table.get("criteria") or []:
        criteria.append((crit.get(crt) or {}).get("name") or (table.get("criteria_names") or {}).get(crt, ""))
        row = []
        for col in cols:
            cell = ((table.get("cells") or {}).get(crt) or {}).get(col) or {"text": "[확인 필요]"}
            text = cell.get("text", "")
            if fact_check is not None and any(ctx.confidential_claim(c) for c in cell.get("claim_ids") or []) and ctx.exclude_conf \
                    and ctx.target not in ("competitor", "export_internal"):
                masked, ns = verify.mask_unsupported(text, [])
                if ns:
                    fact_check.append({"text": f"{labels[cols.index(col)]} {criteria[-1]}", "placeholder": verify.placeholder_for(ns[0]),
                                       "reason": "대외비 자료라 뺐어요"})
                    text = masked
            row.append(text)
        rows.append(row)
    out = {"criteria": criteria, "columns": labels, "cells": rows}
    if cp.get("strengths"):
        out["strengths"] = [{"title": s.get("title", ""), "note": s.get("note", "")} for s in cp["strengths"]]
    return out


def sheet_fact_check(ctx: Ctx, sheet: dict[str, Any], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not ctx.options.get("fix_notes", True):
        return []
    area = sheet.get("area")
    out = []
    for f in (ctx.v.get("fix_items") or {}).values():
        if f.get("status") != "warn" or not f.get("carry", True):
            continue
        if area and f.get("tab") != area:
            continue
        if not area:
            continue
        claim = ctx.claims.get(f.get("claim_id") or "") or {}
        ph = "[00]"
        m = re.search(r"\[0+[0-9,\.]*\]\s*\S*", claim.get("text", ""))
        if m:
            ph = m.group(0)
        elif f.get("unit"):
            ph = f"[00]{f['unit']}" if not str(f["unit"])[0].isalpha() else f"[00] {f['unit']}"
        out.append({"text": f.get("title", ""), "placeholder": ph, "reason": f.get("sub_text", ""), "fix_id": f["id"]})
    return out + extra


def build_sheets(ctx: Ctx, slides: list[dict[str, Any]], *, only: list[str] | None = None) -> list[dict[str, Any]]:
    out = []
    for s in slides:
        if only is not None and s["id"] not in only:
            continue
        cids = sheet_claims(ctx, s.get("sheet_type", ""))
        notes, nums, _ = _footnotes(ctx, cids)
        extra_fc: list[dict[str, Any]] = []
        content = sheet_content(ctx, s, nums, extra_fc)
        out.append({"id": s["id"], "sheet_type": s.get("sheet_type"), "sheet_name": s.get("sheet_name"), "template_code": s.get("template_code"),
                    "why": s.get("why", ""), "content": content, "fact_check": sheet_fact_check(ctx, s, extra_fc if ctx.options.get("fix_notes", True) or extra_fc else []),
                    "footnotes": notes if ctx.options.get("cite_sources", True) else []})
    return out


def _source_age(pub: str | None) -> int | None:
    return rules.months_between(pub)


def vp_materials(ctx: Ctx) -> dict[str, Any]:
    doc = ctx.v.get("document") or {}
    cu = doc.get("customer") or {}
    us = doc.get("user") or {}
    cp = doc.get("competitor") or {}
    fc: list[dict[str, Any]] = []
    challenges = [{"text": f"{o.get('stage', '')} — {_text(ctx, o.get('claim'), fc)}"} for o in cu.get("ops_challenges") or []]
    users = [{"role": p.get("role", ""), "goal": p.get("goal", ""), "pain": p.get("pain", "")} for p in us.get("personas") or []]
    strengths = [{"title": s.get("title", ""), "note": s.get("note", "")} for s in cp.get("strengths") or []]
    numbers = []
    for cid, c in ctx.claims.items():
        nums = [n for n in c.get("numbers") or [] if n.get("kind") != "year"]
        if not nums and "[00]" not in c.get("text", ""):
            continue
        cits = [x for x in ctx.v.get("citations") or [] if x.get("claim_id") == cid and not x.get("dropped")]
        primary = None
        if c.get("conflict"):
            primary = (c["conflict"] or {}).get("primary_source_id")
        if not primary and cits:
            primary = sorted(cits, key=lambda x: (ctx.srcs.get(x["source_id"], {}).get("published_at") or ""), reverse=True)[0]["source_id"]
        src = ctx.srcs.get(primary or "") or {}
        pub = src.get("published_at")
        as_of = pub[:7] if pub else None
        numbers.append({"text": _text(ctx, cid, fc), "value": nums[0]["raw"] if nums else None, "as_of": as_of,
                        "source_age_months": _source_age(pub) if pub else None, "status": c.get("status", "missing"),
                        "footnote": views.footnote(src, cits[0] if cits else None) if src else "", "area": c.get("area")})
    return {"challenges": challenges, "users": users, "strengths": strengths, "numbers": numbers}


def why_samsung(ctx: Ctx) -> dict[str, Any] | None:
    cp = (ctx.v.get("document") or {}).get("competitor") or {}
    if not cp:
        return None
    cids = views.claim_order(ctx.v.get("document") or {}, "competitor")
    notes, nums, _ = _footnotes(ctx, cids)
    strengths = [{"title": s.get("title", ""), "note": s.get("note", ""),
                  "footnote_ns": sorted({n for c in s.get("claim_ids") or [] for n in _fns(ctx, c, nums)})} for s in cp.get("strengths") or []]
    comp = comparison(ctx, nums, [])
    comp.pop("strengths", None)
    return {"strengths": strengths, "comparison": comp, "footnotes": notes if ctx.options.get("cite_sources", True) else []}


def bundle(analysis: dict[str, Any], version: dict[str, Any], *, target: str, handoff: dict[str, Any] | None = None) -> dict[str, Any]:
    conf = (handoff or {}).get("confirmations") or {}
    opts = (handoff or {}).get("options") or {}
    seg = (analysis.get("segment") or {}).get("code")
    if target == "competitor":
        comps = anonymize.live(analysis.get("competitors") or [])
        return {"analysis_id": analysis["id"], "version": int(version.get("n") or 0), "target": "competitor",
                "customer": {"name": analysis.get("customer_name"), "segment": seg, "segment_name": config.segment(seg)["short"] if seg else None},
                "segment": seg,
                "requirements": [{"text": r.get("text", ""), "weight": r.get("weight"), "origin": r.get("origin")} for r in analysis.get("requirements") or []],
                "competitors": [{"letter": c["letter"], "real_name": c.get("real_name", ""), "aliases": c.get("aliases") or [], "kind_label": c.get("kind_label", ""),
                                 "desc": c.get("desc", "")} for c in comps],
                "criteria": [{"name": c["name"], "weight": c.get("weight", 3), "source": c.get("source"), "enabled": c.get("enabled", True)}
                             for c in service_criteria(analysis)],
                "options": {"cite_sources": True, "fix_notes": True, "link_why": True}}
    ctx = Ctx(analysis, version, target=target, options=opts, confirmations=conf)
    slides = version.get("slides") or []
    sel = (handoff or {}).get("sheets") or [s["id"] for s in slides if s.get("included")]
    out: dict[str, Any] = {
        "analysis_id": analysis["id"], "version": int(version.get("n") or 0), "handoff_id": (handoff or {}).get("id"), "target": target,
        "customer": {"name": analysis.get("customer_name"), "segment": seg if seg != "GEN" else seg, "segment_name": config.segment(seg)["short"] if seg else None},
        "usage": (analysis.get("usage") or {}).get("value"),
        "sheets": build_sheets(ctx, slides, only=sel) if target in ("proposal_mi", "proposal_why", "storyboard", "export_customer", "export_internal") else [],
        "why_samsung": why_samsung(ctx),
        "vp_materials": vp_materials(ctx) if target in ("vp", "proposal_mi", "storyboard", "scenario") else None,
        "options": ctx.options,
        "anonymization": {"mode": analysis.get("naming_mode", "letter") if analysis.get("anonymize", True) else "named", "map_ref": (handoff or {}).get("id")},
    }
    return ctx.clean(out)


def evidence_snapshot(analysis: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """storyboard 묶음(익명 처리 끝) → Key Message 근거 후보. 자리표시([00]) 수치는 근거가 될 수 없어 뺀다."""
    ws = b.get("why_samsung") or {}
    notes = {f.get("n"): f for f in ws.get("footnotes") or []}
    items: list[dict[str, Any]] = []
    for i, s in enumerate(ws.get("strengths") or []):
        text = " — ".join(x for x in (s.get("title", ""), s.get("note", "")) if x)
        if not text:
            continue
        cits = [{"title": notes[n]["text"], "url": None} for n in s.get("footnote_ns") or [] if n in notes and notes[n].get("text")]
        items.append({"key": f"strength:{i}", "kind": "strength", "kind_label": "삼성 강점", "text": text[:2000], "default_on": True, "citations": cits})
    vm = b.get("vp_materials") or {}
    for i, n in enumerate(vm.get("numbers") or []):
        text = n.get("text") or ""
        if not text or "[00]" in text:
            continue
        ok = n.get("status") in ("matched", "confirmed")
        items.append({"key": f"number:{i}", "kind": "number", "kind_label": "수치", "text": text[:2000], "status": "원문 일치" if ok else "확인 필요",
                      "default_on": False, "citations": [{"title": n["footnote"], "url": None}] if n.get("footnote") else []})
    for i, c in enumerate(vm.get("challenges") or []):
        text = (c.get("text") or "").strip(" —")
        if text and "[00]" not in text:
            items.append({"key": f"challenge:{i}", "kind": "challenge", "kind_label": "고객 과제", "text": text[:2000], "default_on": False, "citations": []})
    links = analysis.get("links") or {}
    title = analysis.get("title") or "Market Intelligence"
    return {"analysis_id": analysis["id"], "version": int(b.get("version") or 0),
            "source": {"service": "mi", "ref_id": analysis["id"], "title": title, "route": f"/mi/{analysis['id']}/result"},
            "storyboard_id": links.get("storyboard_id"), "storyboard_title": links.get("storyboard_title"), "items": items}


def service_criteria(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    from .service import ordered_criteria

    return ordered_criteria(analysis.get("criteria") or [])


# ── ProposalHandoff v1 ───────────────────────────────────
def proposal_handoff(analysis: dict[str, Any], version: dict[str, Any], *, ptype: str | None, section: str, handoff: dict[str, Any] | None,
                     named: bool) -> dict[str, Any]:
    conf = dict((handoff or {}).get("confirmations") or {})
    if not named:
        conf["real_names"] = None        # named 없이 부르면 늘 익명(§6.14 · AC-MI-92)
    opts = {"cite_sources": True, "fix_notes": True, "link_why": True, **((handoff or {}).get("options") or {})}
    ctx = Ctx(analysis, version, target="proposal_mi", options=opts, confirmations=conf, named=named)
    usage = (analysis.get("usage") or {}).get("value")
    ptype = ptype or (usage if usage in ("standard", "quickwin", "solution") else "standard")
    slides = version.get("slides") or []
    if ptype != usage:
        a2 = copy.deepcopy(analysis)
        a2["usage"] = {**(analysis.get("usage") or {}), "value": ptype}
        slides = layout.sheet_plan(a2, version, previous=slides, usage=ptype)
        fix_by_area: dict[str, int] = {}
        for f in (version.get("fix_items") or {}).values():
            if f.get("status") == "warn":
                fix_by_area[f.get("tab", "")] = fix_by_area.get(f.get("tab", ""), 0) + 1
        for s in slides:
            s["fix_open"] = fix_by_area.get(s.get("area") or "", 0)
    selected = (handoff or {}).get("sheets")
    items: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    if section == "why":
        w = why_samsung(ctx) or {}
        cids = views.claim_order(version.get("document") or {}, "competitor")
        notes, nums, srcs = _footnotes(ctx, cids)
        items.append({"key": "CM", "label": "경쟁 비교표", "from_label": rules.AREA_TAB["competitor"], "sheet_role": "CM", "sheet_title": "경쟁 비교",
                      "template_hint": None, "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
                      "content": w.get("comparison") or {}, "sources": srcs if opts.get("cite_sources", True) else []})
        items.append({"key": "ST", "label": f"삼성 강점 {len(w.get('strengths') or [])}", "from_label": rules.AREA_TAB["competitor"], "sheet_role": "ST",
                      "sheet_title": "삼성 강점", "template_hint": None, "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
                      "content": {"strengths": w.get("strengths") or []}, "sources": srcs if opts.get("cite_sources", True) else []})
        facts = _facts(ctx, cids)
    else:
        for s in bundle_rows(slides):
            if selected is not None and s["id"] not in selected and s.get("included"):
                continue
            cids = sheet_claims(ctx, s.get("sheet_type", ""))
            notes, nums, srcs = _footnotes(ctx, cids)
            st, label = row_status(s)
            content = sheet_content(ctx, s, nums, [])
            items.append({"key": s["id"], "label": s.get("item_label") or s.get("sheet_name"), "from_label": rules.AREA_TAB.get(s.get("area") or "", "종합"),
                          "sheet_role": ROLE.get(s.get("sheet_type", ""), s.get("sheet_type", "")), "sheet_title": s.get("sheet_name"),
                          "template_hint": {"code": s.get("template_code"), "name": s.get("template_name")}, "status": st, "status_label": label,
                          "include_default": st != "add", "content": content, "sources": srcs if opts.get("cite_sources", True) else []})
            facts += _facts(ctx, cids)
    seg = (analysis.get("segment") or {}).get("code")
    links = analysis.get("links") or {}
    out = {
        "source": {"feature": "MI", "ref_id": analysis["id"], "version": int(version.get("n") or 0),
                   "title": analysis.get("title") or analysis.get("customer_name") or "Market Intelligence", "updated_at": analysis.get("updated_at", now_iso()),
                   "route": f"/mi/{analysis['id']}/result"},
        "target": {"proposal_type": ptype, "section_key": section},
        "customer": {k: v for k, v in {"name": analysis.get("customer_name"), "industry_code": seg if seg and seg != "GEN" else None}.items() if v},
        "rq_ref": {"rq_id": links["requirements_id"], "version": links.get("rq_version") or 0} if links.get("requirements_id") else None,
        "items": items,
        "facts": facts,
        "assets": [],
    }
    return ctx.clean(out)


def bundle_rows(slides: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return section_rows(slides)


def _facts(ctx: Ctx, claim_ids: list[str]) -> list[dict[str, Any]]:
    """시트 content 안 수치마다 1개 — 검증 상태는 옵션과 관계없이 그대로(§6.14)."""
    out = []
    for cid in claim_ids:
        c = ctx.claims.get(cid) or {}
        nums = [n for n in c.get("numbers") or [] if n.get("kind") != "year"]
        text = c.get("text", "")
        if "[00]" in text:
            m = re.search(r"\[0+[0-9,\.]*\]\s*\S*", text)
            out.append({"key": cid, "label": c.get("metric_label") or text[:40], "status": "placeholder", "placeholder": m.group(0) if m else "[00]",
                        "source": None})
            continue
        if not nums:
            continue
        st = c.get("status")
        status = "confirmed" if st in ("matched", "confirmed") else "unconfirmed"
        cits = [x for x in ctx.v.get("citations") or [] if x.get("claim_id") == cid and not x.get("dropped")]
        src = ctx.srcs.get(cits[0]["source_id"]) if cits else None
        n0 = nums[0]
        unit = re.sub(r"^[\d,\.\s~\-]+", "", n0.get("raw", "")).strip()
        value = re.match(r"[\d,\.]+", n0.get("raw", ""))
        out.append({"key": cid, "label": c.get("metric_label") or text[:40], "value": value.group(0) if value else n0.get("raw"), "unit": unit or None,
                    "status": status, "source": {"kind": src.get("kind"), "ref": src["id"], "label": views.footnote(src, cits[0])} if src else None})
    return out


# ── 사람에게 물을 것(묻기 2~4) ───────────────────────────
def asks_for(analysis: dict[str, Any], version: dict[str, Any], *, target: str, sheets: list[str], confirm: dict[str, Any],
             target_pinned: list[str] | None) -> list[dict[str, Any]]:
    asks: list[dict[str, Any]] = []
    customer_facing = target in ("proposal_mi", "proposal_why", "vp", "scenario")
    if customer_facing and not analysis.get("anonymize", True) and confirm.get("real_names") is None and anonymize.live(analysis.get("competitors") or []):
        asks.append({"kind": "real_names", "items": [anonymize.workspace_label(c) for c in anonymize.live(analysis.get("competitors") or [])],
                     "default": "anonymize"})
    if customer_facing and confirm.get("confidential") is None:
        ctx = Ctx(analysis, version, target=target)
        slides = {s["id"]: s for s in version.get("slides") or []}
        items = []
        for sid in sheets:
            s = slides.get(sid)
            if not s:
                continue
            for cid in sheet_claims(ctx, s.get("sheet_type", "")):
                if ctx.confidential_claim(cid):
                    c = ctx.claims.get(cid) or {}
                    items.append(c.get("metric_label") or c.get("text", "")[:30])
            if s.get("sheet_type") == "CP":
                table = ((version.get("document") or {}).get("competitor") or {}).get("table") or {}
                for crt, row in (table.get("cells") or {}).items():
                    for col, cell in row.items():
                        if any(ctx.confidential_claim(c) for c in cell.get("claim_ids") or []):
                            items.append(cell.get("text", "")[:30])
        if items:
            asks.append({"kind": "confidential", "items": list(dict.fromkeys(items))[:10], "default": "exclude"})
    if target_pinned and confirm.get("overwrite_pinned") is None:
        slides = {s["id"]: s for s in version.get("slides") or []}
        hit = []
        for sid in sheets:
            s = slides.get(sid) or {}
            if s.get("sheet_type") in target_pinned or s.get("template_code") in target_pinned or ROLE.get(s.get("sheet_type", "")) in target_pinned:
                hit.append(s.get("sheet_name"))
        if hit:
            asks.append({"kind": "overwrite_pinned", "items": hit, "default": "keep"})
    return asks


# ── 내보내기 원본 ───────────────────────────────────────
def export_document(analysis: dict[str, Any], version: dict[str, Any], fmt: str, audience: str, onepager: dict[str, Any] | None = None) -> dict[str, Any]:
    target = "export_internal" if audience == "internal" else "export_customer"
    ctx = Ctx(analysis, version, target=target, confirmations={"real_names": None} if analysis.get("anonymize", True) else {"real_names": True})
    if audience == "customer" and analysis.get("anonymize", True):
        ctx.scrub = True
    title = analysis.get("title") or f"{analysis.get('customer_name') or ''} 시장 분석".strip()
    if fmt == "pdf_report":
        sections = []
        for a in rules.AREAS:
            if a not in (version.get("area_status") or {}) or (version.get("area_status") or {}).get(a) not in ("done", "reused"):
                continue
            ns, src_n = views.numbering(version, a)
            paras = []
            for cid in views.claim_order(version.get("document") or {}, a):
                c = (version.get("claims") or {}).get(cid) or {}
                mark = "" if c.get("status") in ("matched", "confirmed") else " [확인 필요]"
                refs = "".join(f"[{n}]" for n in ns.get(cid, []))
                paras.append(f"{c.get('text', '')}{refs}{mark}")
            sec: dict[str, Any] = {"heading": rules.AREA_TAB[a], "paragraphs": paras[:40]}
            if a == "competitor":
                comp = comparison(ctx)
                if comp.get("columns"):
                    sec["table"] = {"columns": ["요구사항 항목", *comp["columns"]], "rows": [[comp["criteria"][i], *r] for i, r in enumerate(comp["cells"])],
                                    "highlight_col": len(comp["columns"])}
            srcs = version.get("sources") or {}
            sec["sources"] = [{"label": f"[{n}] {views.footnote(srcs[sid])}", **({"url": srcs[sid]['url']} if srcs[sid].get("url") else {})}
                              for sid, n in sorted(src_n.items(), key=lambda t: t[1]) if sid in srcs]
            sections.append(sec)
        fc = [f for f in (version.get("fix_items") or {}).values() if f.get("status") == "warn"]
        if fc:
            sections.append({"heading": "확정 필요 수치", "bullets": [f"{f.get('title')} — {f.get('sub_text')}" for f in fc]})
        doc = {"report": {"title": title, "subtitle": "Market Intelligence 리포트" + (" · 사내용" if audience == "internal" else ""),
                          "meta": f"v{int(version.get('n') or 0)} · {rules.month_day(version.get('created_at'))} 분석", "sections": sections}}
    elif fmt == "xlsx_table":
        comp = comparison(ctx)
        cols = [{"key": "criterion", "label": "요구사항 항목", "width": 24}] + [{"key": f"c{i}", "label": lab, "width": 28} for i, lab in enumerate(comp.get("columns") or [])]
        rows = []
        for i, r in enumerate(comp.get("cells") or []):
            row = {"criterion": comp["criteria"][i]}
            for j, v in enumerate(r):
                row[f"c{j}"] = v
            rows.append(row)
        src_rows = []
        for a in rules.AREAS:
            _, src_n = views.numbering(version, a)
            for sid, n in sorted(src_n.items(), key=lambda t: t[1]):
                s = (version.get("sources") or {}).get(sid) or {}
                if s.get("kind") == "user":
                    continue
                st = "확인 필요" if views.source_needs_check(version, sid, a) else "원문 일치"
                src_rows.append({"tab": rules.AREA_TAB[a], "n": n, "kind": views.kind_label(s), "title": s.get("title", ""), "url": s.get("url") or "",
                                 "published": (s.get("published_at") or "")[:10], "checked": (s.get("retrieved_at") or "")[:10], "status": st})
        doc = {"sheets": [
            {"name": "경쟁사 비교표", "columns": cols, "rows": rows},
            {"name": "출처 목록", "columns": [{"key": "tab", "label": "탭"}, {"key": "n", "label": "번호"}, {"key": "kind", "label": "종류"},
                                           {"key": "title", "label": "제목", "width": 40}, {"key": "url", "label": "URL", "width": 40},
                                           {"key": "published", "label": "발행"}, {"key": "checked", "label": "확인"}, {"key": "status", "label": "상태"}],
             "rows": src_rows},
        ]}
    else:
        op = onepager or {}
        quads = op.get("quadrants") or {}
        tags = {"market": "시장", "customer": "고객사", "user": "사용자", "competitor": "경쟁 · 삼성"}
        doc = {"title": title, "slides": [{"template_code": "IM-B", "slots": {
            "eyebrow": "MARKET INTELLIGENCE", "title": (op.get("conclusion") or title)[:46],
            "quadrants": [{"tag": tags[k], "title": rules.AREA_TAB[k][:24], "body": (quads.get(k) or "[확인 필요]")[:70]} for k in rules.AREAS],
            "conclusion": (op.get("conclusion") or "[확인 필요]")[:40]}}]}
    return ctx.clean(doc)
