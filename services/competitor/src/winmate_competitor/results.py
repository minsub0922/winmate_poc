"""결과 화면 모양(CA4 · CA4D · 근거 패널) — 결과 버전(또는 분석 중이면 작업본) → 화면 데이터.

- 우위 · 비슷 · 열위는 삼성 쪽에서 본 판정. 판정 못 한 기준(`unknown`)은 세지 않는다(세 수의 합 ≤ 켜진 기준 수).
- 출처 요약: `출처 {n} · 공개 자료 {a} · 사내 사례 DB {b} · [수치는 확인 후 확정]`(확정 안 된 수치가 없으면 마지막 구절 생략).
- 근거 카드: 웹 검색 요약은 `원문 열기` 를 숨긴다(URL 없음). 수집에 실패한 URL 은 출처가 아니므로 카드가 없다.
"""
from __future__ import annotations

import copy
from typing import Any

from . import config, judging, rules, service, verify
from . import evidence as E

VERDICT_LABEL = {"samsung_better": "우위", "similar": "비슷", "samsung_worse": "열위", "unknown": "확인 필요"}
DETAIL_ORDER = ("lineup", "price", "solution", "references", "recent")


def provisional(doc: dict[str, Any], work: dict[str, Any]) -> dict[str, Any]:
    """분석 중 `지금까지 결과 보기` — 끝난 경쟁사만 담은 임시 버전(저장하지 않음)."""
    wc = work.get("competitors") or {}
    done = [c["id"] for c in service.on_competitors(doc) if (wc.get(c["id"]) or {}).get("verdicts") is not None
            and (wc.get(c["id"]) or {}).get("state") in ("done", "partial")]
    v = judging.build_version(doc, work, competitor_ids=done, criteria=service.enabled_criteria(doc), strengths=list(work.get("strengths") or []),
                              cautions=list(work.get("cautions") or []), kind="partial", stopped=False)
    v["n"] = int(doc.get("result_version") or 0)
    v["provisional"] = True
    return v


def _comp(doc: dict[str, Any], v: dict[str, Any], cid: str) -> dict[str, Any]:
    c = next((x for x in doc.get("competitors") or [] if x["id"] == cid), None)
    return {**((v.get("competitors") or {}).get(cid) or {}), **(c or {}), "id": cid}


def source_numbers(v: dict[str, Any], claim_order: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    by_claim: dict[str, list[str]] = {}
    for c in v.get("citations") or []:
        by_claim.setdefault(c["claim_id"], []).append(c["source_id"])
    for cid in claim_order:
        for sid in by_claim.get(cid, []):
            if sid not in out:
                out[sid] = len(out) + 1
    return out


def _claim_order(v: dict[str, Any], cids: list[str]) -> list[str]:
    order: list[str] = []
    for cid in cids:
        for k in config.fact_order():
            order.extend(((v.get("facts") or {}).get(cid) or {}).get(k, {}).get("claim_ids") or [])
    for crt in v.get("criteria") or []:
        order.extend(((v.get("samsung_cells") or {}).get(crt["id"]) or {}).get("claim_ids") or [])
    return order


def unknown_chip(v: dict[str, Any]) -> dict[str, Any] | None:
    n = sum(1 for x in v.get("verdicts") or [] if x.get("verdict") == "unknown")
    return {"key": "unknown_cells", "label": f"확인 필요 {n}", "mode": "check"} if n else None


def sources_label(v: dict[str, Any], claim_ids: list[str]) -> str:
    bag = {"sources": v.get("sources") or {}, "citations": v.get("citations") or []}
    sids = E.claim_sources(bag, claim_ids)
    kinds = [(bag["sources"].get(s) or {}).get("kind") for s in sids]
    if not sids:
        return ""
    return f"출처 {len(sids)}" + (" · 사내 사례 DB" if any(k in E.KB_KINDS for k in kinds) else "")


def result_view(doc: dict[str, Any], v: dict[str, Any] | None, *, view: str = "overview") -> dict[str, Any]:
    st = doc.get("status") or "draft"
    v = v or {"competitor_ids": [], "criteria": service.enabled_criteria(doc), "verdicts": [], "facts": {}, "counts": {}, "strengths": [], "cautions": [],
              "footer": {}, "citations": [], "sources": {}, "claims": {}}
    analyzed = list(v.get("competitor_ids") or [])
    rows = []
    for cid in analyzed:
        c = _comp(doc, v, cid)
        cnt = (v.get("counts") or {}).get(cid) or {}
        wst = ((v.get("competitors") or {}).get(cid) or {}).get("state") or "done"
        rows.append({"id": cid, "letter": c.get("letter") or "?", "display": f"경쟁사 {c.get('letter')}", "real_name": c.get("real_name") or "",
                     "kind": c.get("kind_label") or "", "positioning": ((v.get("positioning") or {}).get(cid) or {}).get("text") or "",
                     "up": int(cnt.get("up", 0)), "eq": int(cnt.get("eq", 0)), "dn": int(cnt.get("dn", 0)), "unknown": int(cnt.get("unknown", 0)),
                     "sources": int(cnt.get("sources", 0)), "state": "partial" if wst == "partial" else "done", "state_label": ""})
    total_on = service.on_competitors(doc)
    partial = {"analyzing": st == "analyzing", "stopped": st == "stopped", "done": len(analyzed), "total": len(total_on) if st in ("analyzing", "stopped") else len(analyzed), "text": ""}
    if st in ("analyzing", "stopped"):
        run = {c["id"]: c for c in ((doc.get("run") or {}).get("competitors") or [])}
        for c in service.on_competitors(doc):
            if c["id"] in analyzed:
                continue
            state = "skipped" if st == "stopped" else ("run" if (run.get(c["id"]) or {}).get("state") == "run" else "wait")
            rows.append({"id": c["id"], "letter": c["letter"], "display": f"경쟁사 {c['letter']}", "real_name": c.get("real_name") or "",
                         "kind": c.get("kind_label") or "", "positioning": "", "state": state,
                         "state_label": "분석 안 함" if state == "skipped" else "분석 중"})
        if st == "stopped":
            partial["text"] = f"분석을 멈췄어요 · {len(analyzed)}곳만 결과가 있어요"
        else:
            partial["text"] = f"아직 분석 중이에요 · {len(analyzed)} / {len(total_on)}곳 결과가 있어요"
    crit_names = {c["id"]: c["name"] for c in v.get("criteria") or []}
    letters = {cid: _comp(doc, v, cid).get("letter") for cid in analyzed}
    strengths = [{"title": s.get("title") or "", "note": s.get("note") or "", "criterion_ids": s.get("criterion_ids") or [],
                  "criterion_names": [crit_names.get(x, "") for x in s.get("criterion_ids") or []], "competitor_ids": s.get("competitor_ids") or [],
                  "competitor_letters": [letters.get(x) or "?" for x in s.get("competitor_ids") or []], "claim_ids": s.get("claim_ids") or [],
                  "sources_label": sources_label(v, s.get("claim_ids") or [])} for s in v.get("strengths") or []]
    cautions = [{"competitor_id": x["competitor_id"], "letter": letters.get(x["competitor_id"]) or "?", "display": f"경쟁사 {letters.get(x['competitor_id']) or '?'}",
                 "note": x.get("note") or "", "criterion_ids": x.get("criterion_ids") or [],
                 "criterion_names": [crit_names.get(i, "") for i in x.get("criterion_ids") or []], "claim_ids": x.get("claim_ids") or [],
                 "sources_label": sources_label(v, x.get("claim_ids") or [])} for x in v.get("cautions") or []]
    chips = service.chips_view(doc)
    uc = unknown_chip(v)
    if uc:
        chips.append(uc)
    f = dict(v.get("footer") or {})
    f["text"] = E.footer_text(f)
    out = {"version": int(v.get("n") or doc.get("result_version") or 0), "status": st, "view": view,
           "header": {"kicker": "결과", "title": f"경쟁사 {len(analyzed) if st != 'analyzing' else len(total_on)}곳, 한눈에",
                      "desc": "경쟁사마다 포지셔닝 한 줄과 삼성 대비 우위 · 비슷 · 열위를 세었어요. 누르면 상세로 가요."},
           "competitors": rows, "strengths": strengths, "cautions": cautions, "chips": chips, "footer": f, "table": None, "partial": partial,
           "can_send": st in ("done", "upd", "stopped") and bool(analyzed), "criteria_count": len(v.get("criteria") or [])}
    if view == "table":
        out["table"] = table_view(doc, v, analyzed)
    return out


def table_view(doc: dict[str, Any], v: dict[str, Any], cids: list[str]) -> dict[str, Any]:
    crits = [c for c in v.get("criteria") or [] if c.get("enabled", True)]
    nums = source_numbers(v, _claim_order(v, cids))
    by_claim: dict[str, list[str]] = {}
    for c in v.get("citations") or []:
        by_claim.setdefault(c["claim_id"], []).append(c["source_id"])
    verd = {(x["criterion_id"], x["competitor_id"]): x for x in v.get("verdicts") or []}
    cols = [{"id": cid, "label": f"경쟁사 {_comp(doc, v, cid).get('letter')}", "letter": _comp(doc, v, cid).get("letter"),
             "real_name": _comp(doc, v, cid).get("real_name"), "samsung": False} for cid in cids]
    cols.append({"id": "samsung", "label": "삼성", "letter": None, "real_name": None, "samsung": True})
    cells = []
    for crt in crits:
        row = []
        keys = judging.fact_keys_for(crt["name"])
        for cid in cids:
            f = (v.get("facts") or {}).get(cid) or {}
            fk = next((k for k in keys if not (f.get(k) or {}).get("tbd", True)), None)
            fact = f.get(fk) if fk else None
            text = fact["text"] if fact else "[확인 필요]"
            ids = list((fact or {}).get("claim_ids") or [])
            ns = sorted({nums[s] for i in ids for s in by_claim.get(i, []) if s in nums})
            vd = (verd.get((crt["id"], cid)) or {}).get("verdict") or "unknown"
            row.append({"text": text, "verdict": vd, "claim_ids": ids, "source_ns": ns, "tbd": fact is None or "[00]" in text})
        sc = (v.get("samsung_cells") or {}).get(crt["id"]) or {}
        ids = list(sc.get("claim_ids") or [])
        ns = sorted({nums[s] for i in ids for s in by_claim.get(i, []) if s in nums})
        row.append({"text": sc.get("text") or "[확인 필요]", "verdict": None, "claim_ids": ids, "source_ns": ns, "tbd": bool(sc.get("tbd", True))})
        cells.append(row)
    return {"criteria": [{"id": c["id"], "name": c["name"], "importance": int(c.get("importance") or 3), "source": c.get("source") or ""} for c in crits],
            "columns": cols, "cells": cells}


def detail_view(doc: dict[str, Any], v: dict[str, Any], cid: str) -> dict[str, Any]:
    c = _comp(doc, v, cid)
    facts = (v.get("facts") or {}).get(cid) or {}
    fviews = []
    for k in DETAIL_ORDER:                       # 화면 순서(§4.13) — 모으는 순서(제품 · 솔루션 · 레퍼런스 · 가격대 · 최근 동향)와 다르다
        f = facts.get(k) or {"text": "[확인 필요]", "tbd": True, "claim_ids": []}
        ids = list(f.get("claim_ids") or [])
        fviews.append({"key": k, "label": config.fact_label(k), "text": f.get("text") or "[확인 필요]", "tbd": bool(f.get("tbd")),
                       "sources": int(f.get("sources") or 0), "has_kb": bool(f.get("has_kb")), "sources_label": sources_label(v, ids),
                       "check": bool(f.get("check", f.get("tbd"))), "claim_ids": ids})
    crit_names = {x["id"]: x["name"] for x in v.get("criteria") or []}
    vs: dict[str, list[str]] = {"better": [], "similar": [], "worse": [], "unknown": []}
    key = {"samsung_better": "better", "similar": "similar", "samsung_worse": "worse", "unknown": "unknown"}
    for x in v.get("verdicts") or []:
        if x.get("competitor_id") == cid:
            vs[key.get(x.get("verdict") or "unknown", "unknown")].append(crit_names.get(x["criterion_id"], ""))
    labels = []
    for k, word in (("better", "우위"), ("similar", "비슷"), ("worse", "열위")):
        if vs[k]:
            labels.append({"key": k, "label": f"{word} {len(vs[k])} · " + " · ".join(vs[k]), "mode": "auto"})
    ids_all = [i for f in fviews for i in f["claim_ids"]]
    bag = {"sources": v.get("sources") or {}, "claims": v.get("claims") or {}, "citations": v.get("citations") or []}
    foot = E.footer(bag, ids_all)
    foot["text"] = E.footer_text(foot, detail=True)
    research = doc.get("research") or {}
    running = bool(research.get("job_id")) and research.get("competitor_id") == cid
    return {"version": int(v.get("n") or doc.get("result_version") or 0),
            "header": {"id": cid, "letter": c.get("letter") or "?", "display": f"경쟁사 {c.get('letter')}", "real_name": c.get("real_name") or "",
                       "kind": c.get("kind_label") or "", "aliases": list(c.get("aliases") or [])},
            "positioning": ((v.get("positioning") or {}).get(cid) or {}).get("text") or "", "facts": fviews, "vs_samsung": vs, "vs_labels": labels,
            "footer": foot, "others": [{"id": x, "letter": _comp(doc, v, x).get("letter") or "?", "current": x == cid} for x in v.get("competitor_ids") or []],
            "research": {"job_id": research.get("job_id") if running else None, "running": running,
                         "eta_label": f"약 {config.eta().get('research_s', 40)}초" if running else ""},
            "state": ((v.get("competitors") or {}).get(cid) or {}).get("state") or "done"}


# ── 주장 · 출처 카드(MI3S 와 같은 카드 규칙) ─────────────
def _kind_label(s: dict[str, Any]) -> str:
    k = s.get("kind")
    if k == "web":
        return f"공개 자료 · {s.get('subtype') or '기타'}"
    if k == "kb_official":
        return "사내 스펙" if s.get("subtype") == "스펙" else "삼성 공식"
    if k == "file":
        return f"사내 자료 · {s.get('title') or ''}".strip(" ·")
    return E.KIND_LABEL.get(k or "", k or "")


def _meta(s: dict[str, Any]) -> str:
    k = s.get("kind")
    checked = "오늘 확인" if (s.get("retrieved_at") or "")[:10] == config.today().isoformat() else f"{rules.md_label(s.get('retrieved_at'))} 확인"
    if k == "websearch_summary":
        return f"원문 URL 없음 · {rules.md_label(s.get('retrieved_at'))} 검색"
    if k == "web":
        pub = s.get("published_at")
        if pub:
            return f"{pub[:4]}년 {int(pub[5:7])}월 발행 · {checked}"
        return f"[발행일 미상] · {checked}"
    if k in E.KB_KINDS:
        return f"samsung.com · {s.get('title') or ''}" if s.get("url") else (s.get("title") or "사내 사례 DB")
    return s.get("title") or ""


def claim_item(v: dict[str, Any], cl: dict[str, Any], nums: dict[str, int]) -> dict[str, Any]:
    cits = [c for c in v.get("citations") or [] if c.get("claim_id") == cl["id"]]
    return {"id": cl["id"], "text": cl.get("text") or "", "status": cl.get("status") or "needs_check",
            "label": cl.get("label") or verify.claim_label(cl.get("status") or "needs_check"), "competitor_id": cl.get("competitor_id"),
            "fact_key": cl.get("fact_key"), "criterion_id": cl.get("criterion_id"), "block": cl.get("block") or "",
            "citations": [{"n": nums.get(c["source_id"], 0), "source_id": c["source_id"], "status": c.get("status") or ""} for c in cits]}


def claims_view(doc: dict[str, Any], v: dict[str, Any], *, competitor: str | None = None, fact: str | None = None, status: str | None = None) -> dict[str, Any]:
    cids = [competitor] if competitor else list(v.get("competitor_ids") or [])
    order = _claim_order(v, cids)
    nums = source_numbers(v, order)
    items = []
    for cid in order:
        cl = (v.get("claims") or {}).get(cid)
        if not cl:
            continue
        if competitor and cl.get("competitor_id") not in (competitor, None):
            continue
        if competitor and cl.get("block") == "samsung":
            continue
        if fact and cl.get("fact_key") != fact:
            continue
        if status == "needs_check" and cl.get("status") in ("matched", "confirmed"):
            continue
        items.append(claim_item(v, cl, nums))
    srcs = [v["sources"][s] for s in nums if s in (v.get("sources") or {})]
    return {"items": items, "counts": {"total": len(items), "matched": sum(1 for i in items if i["status"] == "matched"),
                                       "needs_check": sum(1 for i in items if i["status"] not in ("matched", "confirmed")),
                                       "public": sum(1 for s in srcs if s.get("kind") in E.PUBLIC_KINDS),
                                       "kb_case": sum(1 for s in srcs if s.get("kind") in E.KB_KINDS)}}


def source_card(v: dict[str, Any], cit: dict[str, Any], n: int) -> dict[str, Any]:
    s = (v.get("sources") or {}).get(cit["source_id"]) or {}
    k = s.get("kind")
    ok = cit.get("status") == "matched"
    url = s.get("url") if k in ("web", "kb_case", "kb_official") else None
    if k == "websearch_summary":
        actions = ["각주로 복사", "다른 출처 찾기", "이 출처 빼기"]
    elif k == "web":
        actions = ["원문 열기", "각주로 복사"] if ok else ["원문 열기", "다른 출처 찾기", "값 직접 확정", "이 출처 빼기"]
    elif k in E.KB_KINDS:
        actions = (["원문 열기"] if url else []) + ["각주로 복사"]
    else:
        actions = ["각주로 복사", "이 출처 빼기"]
    from .bundle import Scrubber, footnote_text

    foot, _ = footnote_text(s, Scrubber({}, {}, True))
    return {"source_id": cit["source_id"], "n": n, "kind": k or "", "kind_label": _kind_label(s), "status": cit.get("status") or "needs_check",
            "status_label": "원문 일치" if ok else "확인 필요", "title": s.get("title") or "", "meta": _meta(s), "quote": cit.get("quote") or "",
            "highlight": cit.get("highlight"), "reason": cit.get("reason_text") or "", "url": url, "actions": actions, "footnote": foot}


def claim_detail(doc: dict[str, Any], v: dict[str, Any], clm: str) -> dict[str, Any] | None:
    cl = (v.get("claims") or {}).get(clm)
    if not cl:
        return None
    cids = [cl["competitor_id"]] if cl.get("competitor_id") else list(v.get("competitor_ids") or [])
    nums = source_numbers(v, _claim_order(v, cids))
    cits = [c for c in v.get("citations") or [] if c.get("claim_id") == clm]
    return {"claim": claim_item(v, cl, nums), "cards": [source_card(v, c, nums.get(c["source_id"], 0)) for c in cits]}


def source_out(s: dict[str, Any]) -> dict[str, Any]:
    return {"id": s.get("id") or "", "kind": s.get("kind") or "", "kind_label": _kind_label(s), "subtype": s.get("subtype") or "",
            "title": s.get("title") or "", "publisher": s.get("publisher") or "", "url": s.get("url"), "published_at": s.get("published_at"),
            "retrieved_at": s.get("retrieved_at"), "state": s.get("state") or "used",
            "competitor_id": (s.get("competitor_ids") or [None])[0] if s.get("competitor_ids") else s.get("competitor_id"),
            "fact_key": (s.get("fact_keys") or [None])[0] if s.get("fact_keys") else s.get("fact_key"), "mode": s.get("mode") or "",
            "query": s.get("query")}


def remove_citation(v: dict[str, Any], clm: str, src: str) -> dict[str, Any] | None:
    """이 출처 빼기 → 주장 상태 다시(마지막 출처를 빼면 missing · 그 사실은 `[확인 필요]`)."""
    cl = (v.get("claims") or {}).get(clm)
    if not cl:
        return None
    before = len(v.get("citations") or [])
    v["citations"] = [c for c in v.get("citations") or [] if not (c.get("claim_id") == clm and c.get("source_id") == src)]
    if len(v["citations"]) == before:
        return None
    cits = [c for c in v["citations"] if c.get("claim_id") == clm]
    cl["status"] = verify.claim_status(cits)
    cl["label"] = verify.claim_label(cl["status"], sum(1 for c in cits if c.get("status") != "matched"))
    if cl["status"] == "missing" and cl.get("competitor_id") and cl.get("fact_key"):
        f = ((v.get("facts") or {}).get(cl["competitor_id"]) or {}).get(cl["fact_key"])
        if f:
            f["claim_ids"] = [x for x in f.get("claim_ids") or [] if x != clm]
            v["claims"].pop(clm, None)
            bag = {"sources": v.get("sources") or {}, "claims": v.get("claims") or {}, "citations": v["citations"]}
            new = judging.fact_entry(bag, cl["fact_key"], f.get("text") if f.get("claim_ids") else None, f.get("claim_ids") or [])
            f.update(new)
    used = {c["source_id"] for c in v["citations"]}
    if src not in used:
        (v.get("sources") or {}).pop(src, None)
    bag = {"sources": v.get("sources") or {}, "claims": v.get("claims") or {}, "citations": v["citations"]}
    v["footer"] = E.footer(bag)
    for cid in v.get("competitor_ids") or []:
        v.setdefault("counts", {})[cid] = judging.counts_for(bag, cid, v.get("verdicts") or [], (v.get("facts") or {}).get(cid) or {})
    return copy.deepcopy(cl)
