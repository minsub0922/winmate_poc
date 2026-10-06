"""넘김 묶음 · ProposalHandoff · 리포트(§6.10 · §6.11 · §7.8 ca.export) — 같은 코드 경로에서 만든다.

경쟁사 표기(03-mi.md §5.6 display_name 과 같은 규칙):
- mi(작업 안 분석) · 사내용 리포트: 실명
- proposal_why · storyboard · 고객용: 익명 — 포함된 경쟁사끼리 A, B, C … 다시 붙이고(대응표는 넘김 기록에), 실명 · 별칭은 글에서도 지운다.
  로고 · 제품 사진은 넣지 않는다. 주의할 점(cautions)은 내부용이라 고객 제출 묶음에 넣지 않는다. 사용자가 끈 경쟁사는 넣지 않는다.
"""
from __future__ import annotations

import copy
from typing import Any

from . import config, rules, service, verify
from . import evidence as E

VMARK = {"samsung_better": "better", "similar": "similar", "samsung_worse": "worse", "unknown": "unknown"}


def included(doc: dict[str, Any], v: dict[str, Any]) -> list[dict[str, Any]]:
    """넘김에 넣을 경쟁사 = 이 버전에서 분석했고 지금 켜져 있는 곳(글자 순)."""
    on = {c["id"] for c in service.on_competitors(doc)}
    comps = []
    for cid in v.get("competitor_ids") or []:
        if cid not in on:
            continue
        base = next((c for c in doc.get("competitors") or [] if c["id"] == cid), None) or {**(v.get("competitors") or {}).get(cid, {}), "id": cid}
        comps.append(base)
    return service.ordered(comps)


def anon_map(comps: list[dict[str, Any]]) -> dict[str, str]:
    return {c["id"]: f"경쟁사 {rules.letter_at(i)}" for i, c in enumerate(comps)}


def all_names(doc: dict[str, Any], v: dict[str, Any] | None = None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for c in doc.get("competitors") or []:
        out[c["id"]] = [n for n in [c.get("real_name"), *(c.get("aliases") or [])] if n]
    for cid, c in ((v or {}).get("competitors") or {}).items():
        out.setdefault(cid, [n for n in [c.get("real_name"), *(c.get("aliases") or [])] if n])
    return out


class Scrubber:
    """실명 · 별칭 → 익명 표기(포함된 곳은 새 글자, 빠진 곳은 `다른 경쟁사`)."""

    def __init__(self, names: dict[str, list[str]], amap: dict[str, str], named: bool):
        self.names = names
        self.amap = amap
        self.named = named

    def __call__(self, text: str | None) -> str:
        if not text or self.named:
            return text or ""
        out = text
        for cid, ns in sorted(self.names.items(), key=lambda kv: -max((len(n) for n in kv[1]), default=0)):
            out = verify.replace_names(out, ns, self.amap.get(cid, "다른 경쟁사"))
        return out

    def leaks(self, text: str | None) -> bool:
        return (not self.named) and verify.leaks(text, [n for ns in self.names.values() for n in ns])


def _label(doc: dict[str, Any], c: dict[str, Any], amap: dict[str, str], named: bool) -> str:
    return (c.get("real_name") or amap.get(c["id"], "")) if named else amap.get(c["id"], f"경쟁사 {c.get('letter')}")


def footnote_text(s: dict[str, Any], scrub: Scrubber) -> tuple[str, str | None]:
    """각주 형식: `{발행처}, 「{제목}」, {YYYY.MM}, {URL} (확인 {YYYY-MM-DD})` · 웹 검색 요약은 `웹 검색 요약, "{검색어}", 검색 {날짜} (원문 미확인)`."""
    checked = (s.get("retrieved_at") or "")[:10]
    if s.get("kind") == "websearch_summary":
        return scrub(f"웹 검색 요약, \"{s.get('query') or ''}\", 검색 {checked} (원문 미확인)"), None
    parts = [s.get("publisher") or E.KIND_LABEL.get(s.get("kind") or "", ""), f"「{s.get('title') or ''}」"]
    if s.get("published_at"):
        parts.append(rules.ym(s["published_at"]))
    url = s.get("url")
    if url and scrub.leaks(url):
        url = None          # 실명이 든 주소(도메인 · 경로)는 익명 묶음에 넣지 않는다
    if url:
        parts.append(url)
    txt = ", ".join(p for p in parts if p) + (f" (확인 {checked})" if checked else "")
    return scrub(txt), url


def table_for(doc: dict[str, Any], v: dict[str, Any], comps: list[dict[str, Any]], *, labels: dict[str, str], scrub: Scrubber,
              samsung_label: str = "삼성") -> dict[str, Any]:
    """비교표(행 = 켜진 기준 · CA3C 순서, 열 = 경쟁사 + 삼성)."""
    from .judging import fact_keys_for

    crits = [c for c in v.get("criteria") or [] if c.get("enabled", True)]
    verd = {(x["criterion_id"], x["competitor_id"]): x for x in v.get("verdicts") or []}
    cells: list[list[str]] = []
    marks: list[list[str]] = []
    tbd_count = 0
    for crt in crits:
        row: list[str] = []
        mrow: list[str] = []
        keys = fact_keys_for(crt["name"])
        for c in comps:
            f = (v.get("facts") or {}).get(c["id"]) or {}
            txt = next((f[k]["text"] for k in keys if not (f.get(k) or {}).get("tbd", True)), "[확인 필요]")
            vd = verd.get((crt["id"], c["id"])) or {}
            mark = VMARK.get(vd.get("verdict") or "unknown", "unknown")
            if mark == "unknown" or "[확인 필요]" in txt or "[00]" in txt:
                tbd_count += 1
            row.append(scrub(txt))
            mrow.append(mark)
        sc = (v.get("samsung_cells") or {}).get(crt["id"]) or {}
        row.append(sc.get("text") or "[확인 필요]")
        if sc.get("tbd"):
            tbd_count += 1
        mrow.append("samsung")
        cells.append(row)
        marks.append(mrow)
    return {"criteria": [c["name"] for c in crits], "columns": [labels[c["id"]] for c in comps] + [samsung_label], "cells": cells,
            "verdict_marks": marks, "tbd": tbd_count}


def _sources_used(v: dict[str, Any], claim_ids: set[str]) -> list[dict[str, Any]]:
    sids: list[str] = []
    for c in v.get("citations") or []:
        if c.get("claim_id") in claim_ids and c["source_id"] not in sids:
            sids.append(c["source_id"])
    return [v["sources"][s] for s in sids if s in (v.get("sources") or {})]


def _comp_claims(v: dict[str, Any], comps: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for c in comps:
        for f in ((v.get("facts") or {}).get(c["id"]) or {}).values():
            ids.update(f.get("claim_ids") or [])
    for cell in (v.get("samsung_cells") or {}).values():
        ids.update(cell.get("claim_ids") or [])
    return ids


def fact_status(cl: dict[str, Any]) -> str:
    if cl.get("status") in ("matched", "confirmed"):
        return "confirmed"
    return "unconfirmed"


def facts_list(v: dict[str, Any], claim_ids: set[str], scrub: Scrubber) -> list[dict[str, Any]]:
    """칸 · 강점 문장 속 수치마다(03-mi.md §6.14): matched · confirmed → confirmed, 그 밖 → unconfirmed, [00] → placeholder."""
    out = []
    for cid in sorted(claim_ids):
        cl = (v.get("claims") or {}).get(cid)
        if not cl:
            continue
        text = scrub(cl.get("text") or "")
        for n in verify.parse_numbers(text):
            if n.kind == "year":
                continue
            out.append({"key": f"{cid}:{n.raw}", "label": text[:60], "value": n.raw, "unit": n.unit or None, "status": fact_status(cl),
                        "source": {"kind": "claim", "ref": cid, "label": cl.get("label") or ""}})
        if "[00]" in text:
            out.append({"key": f"{cid}:placeholder", "label": text[:60], "value": None, "unit": None, "status": "placeholder", "placeholder": "[00]",
                        "source": {"kind": "claim", "ref": cid, "label": cl.get("label") or ""}})
    return out


# ── 묶음(§6.10) ──────────────────────────────────────────
def bundle_mi(doc: dict[str, Any], v: dict[str, Any], *, handoff_id: str | None) -> dict[str, Any]:
    comps = included(doc, v)
    seg = service.segment_view(doc.get("segment"))
    ids = {c["id"] for c in comps}
    claims_keep = _comp_claims(v, comps)
    cits = [c for c in v.get("citations") or [] if c.get("claim_id") in claims_keep]
    sids = {c["source_id"] for c in cits}
    return {
        "target": "mi", "analysis_id": doc["id"], "version": int(v.get("n") or doc.get("result_version") or 0), "handoff_id": handoff_id, "named": True,
        "title": service.display_title(doc),
        "customer": {"name": ((doc.get("slots") or {}).get("customer") or {}).get("value"), "segment": seg["code"], "segment_name": seg["name"]},
        "segment": seg, "slots": {k: (doc.get("slots") or {}).get(k, {}).get("value") for k in rules.SLOT_ORDER},
        "competitors": [{"id": c["id"], "letter": c.get("letter"), "real_name": c.get("real_name"), "aliases": c.get("aliases") or [],
                         "kind_label": c.get("kind_label") or "", "why": c.get("why") or "", "confidence": c.get("confidence"),
                         "origin": c.get("origin"), "pinned": bool(c.get("pinned"))} for c in comps],
        "criteria": [{"id": c["id"], "name": c["name"], "source": c.get("source"), "source_count": c.get("source_count"),
                      "importance": c.get("importance"), "order": c.get("order"), "enabled": c.get("enabled", True)} for c in v.get("criteria") or []],
        "facts": {k: x for k, x in (v.get("facts") or {}).items() if k in ids},
        "positioning": {k: x for k, x in (v.get("positioning") or {}).items() if k in ids},
        "samsung_cells": copy.deepcopy(v.get("samsung_cells") or {}),
        "verdicts": [x for x in v.get("verdicts") or [] if x.get("competitor_id") in ids],
        "strengths": copy.deepcopy(v.get("strengths") or []), "cautions": [x for x in v.get("cautions") or [] if x.get("competitor_id") in ids],
        "claims": [{"id": k, "text": x.get("text"), "status": x.get("status"), "fact_key": x.get("fact_key"), "competitor_id": x.get("competitor_id"),
                    "criterion_id": x.get("criterion_id")} for k, x in (v.get("claims") or {}).items() if k in claims_keep],
        "citations": [{k: c.get(k) for k in ("claim_id", "source_id", "quote", "highlight", "page", "check", "status", "reason_code", "reason_text",
                                             "verified_at")} for c in cits],
        "sources": [{**{k: s.get(k) for k in ("kind", "title", "publisher", "url", "published_at", "published_basis", "retrieved_at", "authority",
                                              "classification", "subtype", "query", "summary", "state")}, "id": sid}
                    for sid, s in (v.get("sources") or {}).items() if sid in sids],
    }


def bundle_proposal(doc: dict[str, Any], v: dict[str, Any], *, handoff_id: str | None, named: bool) -> tuple[dict[str, Any], dict[str, str]]:
    comps = included(doc, v)
    amap = anon_map(comps)
    scrub = Scrubber(all_names(doc, v), amap, named)
    labels = {c["id"]: _label(doc, c, amap, named) for c in comps}
    table = table_for(doc, v, comps, labels=labels, scrub=scrub)
    crit_names = {c["id"]: c["name"] for c in v.get("criteria") or []}
    strengths = [{"title": scrub(s.get("title")), "note": scrub(s.get("note")), "criterion_names": [crit_names.get(x, "") for x in s.get("criterion_ids") or []]}
                 for s in v.get("strengths") or []]
    claims = _comp_claims(v, comps) | {cid for s in v.get("strengths") or [] for cid in s.get("claim_ids") or []}
    foot = []
    for i, s in enumerate(_sources_used(v, claims), start=1):
        t, url = footnote_text(s, scrub)
        foot.append({"n": i, "text": t, **({"url": url} if url else {})})
    fact_check = [{"text": f["label"], "placeholder": f.get("placeholder") or f.get("value"), "reason": "출처 확인 전"} for f in facts_list(v, claims, scrub)
                  if f["status"] != "confirmed"]
    return {
        "target": "proposal_why", "analysis_id": doc["id"], "version": int(v.get("n") or doc.get("result_version") or 0), "handoff_id": handoff_id,
        "named": named, "title": service.display_title(doc),
        "comparison": {k: table[k] for k in ("criteria", "columns", "cells", "verdict_marks")}, "strengths": strengths, "footnotes": foot,
        "fact_check": fact_check,
    }, amap


def bundle_storyboard(doc: dict[str, Any], v: dict[str, Any] | None, *, handoff_id: str | None) -> dict[str, Any]:
    comps = included(doc, v) if v else service.on_competitors(doc)
    amap = anon_map(comps)
    crits = (v or {}).get("criteria") or service.enabled_criteria(doc)
    return {"target": "storyboard", "analysis_id": doc["id"], "version": int((v or {}).get("n") or doc.get("result_version") or 0),
            "handoff_id": handoff_id, "named": False, "title": service.display_title(doc),
            "criteria": [{"name": c["name"], "importance": int(c.get("importance") or 3), "source": c.get("source")} for c in crits if c.get("enabled", True)],
            "competitors": [amap[c["id"]] for c in comps],
            "note": f"경쟁사 분석 · {service.display_title(doc)} · 비교 기준 {sum(1 for c in crits if c.get('enabled', True))}개"}


# ── ProposalHandoff v1(§6.11) ────────────────────────────
def proposal_handoff(doc: dict[str, Any], v: dict[str, Any], *, ptype: str, section: str, handoff_id: str | None, named: bool) -> dict[str, Any]:
    comps = included(doc, v)
    amap = anon_map(comps)
    scrub = Scrubber(all_names(doc, v), amap, named)
    labels = {c["id"]: _label(doc, c, amap, named) for c in comps}
    table = table_for(doc, v, comps, labels=labels, scrub=scrub)
    crit_names = {c["id"]: c["name"] for c in v.get("criteria") or []}
    claims = _comp_claims(v, comps)
    s_claims = {cid for s in v.get("strengths") or [] for cid in s.get("claim_ids") or []}

    def srcs(ids: set[str]) -> list[dict[str, Any]]:
        out = []
        for s in _sources_used(v, ids):
            label, url = footnote_text(s, scrub)
            out.append({"kind": s.get("kind") or "", "ref": s.get("id") or "", "label": label, **({"url": url} if url and s.get("kind") == "web" else {}),
                        **({"tier": "T2"} if s.get("kind") in E.KB_KINDS else {})})
        return out

    cm_warn = table["tbd"]
    st_unconf = sum(1 for f in facts_list(v, s_claims, scrub) if f["status"] != "confirmed")
    route = f"/competitor/{doc['id']}/result"
    items = [
        {"key": "CM", "label": "경쟁 비교", "from_label": "경쟁사 분석", "sheet_role": "CM", "sheet_title": "경쟁 비교",
         "template_hint": {"code": "CM-A", "name": "경쟁 비교표"}, "status": "warn" if cm_warn else "ok",
         "status_label": f"[확정 필요] {cm_warn}건" if cm_warn else "그대로 들어가요", "include_default": True,
         "content": {"criteria": table["criteria"], "columns": table["columns"], "cells": table["cells"], "verdict_marks": table["verdict_marks"],
                     "confidence": {labels[c["id"]]: c.get("confidence") for c in comps if c.get("confidence") is not None}},
         "sources": srcs(claims)},
        {"key": "ST", "label": "삼성 강점", "from_label": "경쟁사 분석", "sheet_role": "ST", "sheet_title": "삼성 강점",
         "template_hint": {"code": "ST-A", "name": "삼성 강점"}, "status": "warn" if st_unconf else "ok",
         "status_label": f"[확정 필요] {st_unconf}건" if st_unconf else "그대로 들어가요", "include_default": True,
         "content": {"strengths": [{"title": scrub(s.get("title")), "note": scrub(s.get("note")),
                                    "criterion_names": [crit_names.get(x, "") for x in s.get("criterion_ids") or []]} for s in v.get("strengths") or []]},
         "sources": srcs(s_claims)},
    ]
    seg = service.segment_view(doc.get("segment"))
    customer = {"name": ((doc.get("slots") or {}).get("customer") or {}).get("value")}
    if seg["code"] != "GEN":
        customer["industry_code"] = seg["code"]
    rq_ref = {"rq_id": doc["requirements_id"], "version": int(doc.get("rq_version") or 0)} if doc.get("requirements_id") else None
    return {
        "source": {"feature": "CA", "ref_id": doc["id"], "version": int(v.get("n") or doc.get("result_version") or 0), "title": service.display_title(doc),
                   "updated_at": doc.get("updated_at") or "", "route": route},
        "target": {"proposal_type": ptype, "section_key": section}, "customer": customer, "rq_ref": rq_ref, "items": items,
        "facts": facts_list(v, claims | s_claims, scrub), "assets": [], "live_link": False, "named": named,
    }, amap


# ── PDF 리포트(ca.export) ────────────────────────────────
def report_document(doc: dict[str, Any], v: dict[str, Any], *, audience: str) -> dict[str, Any]:
    internal = audience == "internal"
    comps = included(doc, v)
    amap = anon_map(comps)
    scrub = Scrubber(all_names(doc, v), amap, internal)
    labels = {c["id"]: (f"경쟁사 {c.get('letter')} · {c.get('real_name')}" if internal else amap[c["id"]]) for c in comps}
    table = table_for(doc, v, comps, labels=labels, scrub=scrub)
    seg = service.segment_view(doc.get("segment"))
    counts = v.get("counts") or {}
    f = v.get("footer") or {}
    sections: list[dict[str, Any]] = [
        {"heading": "한눈에", "paragraphs": [f"경쟁사 {len(comps)}곳 · 비교 기준 {len(table['criteria'])}개 · {E.footer_text(f)}"],
         "table": {"columns": ["경쟁사", "포지셔닝", "우위", "비슷", "열위"],
                   "rows": [[labels[c["id"]], scrub(((v.get("positioning") or {}).get(c["id"]) or {}).get("text") or "[확인 필요]"),
                             str((counts.get(c["id"]) or {}).get("up", 0)), str((counts.get(c["id"]) or {}).get("eq", 0)),
                             str((counts.get(c["id"]) or {}).get("dn", 0))] for c in comps]}},
        {"heading": "비교표", "table": {"columns": ["기준", *table["columns"]],
                                       "rows": [[table["criteria"][i], *row] for i, row in enumerate(table["cells"])]}},
    ]
    for c in comps:
        fx = (v.get("facts") or {}).get(c["id"]) or {}
        sections.append({"heading": labels[c["id"]], "level": 2,
                         "bullets": [f"{config.fact_label(k)} — {scrub((fx.get(k) or {}).get('text') or '[확인 필요]')}" for k in config.fact_order()]})
    if v.get("strengths"):
        sections.append({"heading": "삼성 강점", "bullets": [f"{scrub(s['title'])} — {scrub(s['note'])}" for s in v["strengths"]]})
    if internal and v.get("cautions"):
        sections.append({"heading": "주의할 점(사내용)", "bullets": [f"{labels.get(x['competitor_id'], '')} — {scrub(x['note'])}" for x in v["cautions"]]})
    claims = _comp_claims(v, comps)
    foot = []
    for s in _sources_used(v, claims):
        t, url = footnote_text(s, scrub)
        foot.append({"label": t, **({"url": url} if url else {})})
    sections.append({"heading": "출처", "sources": foot or [{"label": "출처 없음"}]})
    meta = [f"업종 {seg['name']}", f"분석 {rules.md_label(doc.get('analyzed_at'))}" if doc.get("analyzed_at") else "", f"v{int(v.get('n') or 0)}"]
    return {"title": f"{service.display_title(doc)} — 경쟁사 분석", "subtitle": "사내용 · 고객 제출 금지" if internal else "고객 제출용 · 경쟁사 익명 표기",
            "meta": [m for m in meta if m], "sections": sections, "page_size": "A4"}
