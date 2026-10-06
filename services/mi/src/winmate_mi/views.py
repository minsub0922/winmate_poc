"""화면 데이터 만들기 — MI0 행 · MI3 결과 · MI3S 주장 · 출처 카드 · 각주(03-mi.md §4)."""
from __future__ import annotations

from typing import Any

from . import anonymize, config, rules
from .verify import claim_label

KIND_GROUP = {"web": "public", "websearch_summary": "public", "kb_case": "kb_case", "kb_official": "kb_official", "file": "internal",
              "user": "user"}
GROUP_LABEL = {"public": "공개 자료", "kb_case": "사내 사례 DB", "kb_official": "사내 스펙", "internal": "사내 자료"}


def src_group(src: dict[str, Any]) -> str:
    kind = src.get("orig_kind") if src.get("kind") == "ca_import" else src.get("kind")
    return KIND_GROUP.get(kind or "", "public")


# ── 주장 순서 · 탭 안 번호 ───────────────────────────────
def claim_order(document: dict[str, Any], area: str) -> list[str]:
    blk = (document or {}).get(area) or {}
    out: list[str] = []

    def add(x: Any) -> None:
        if isinstance(x, str) and x.startswith("clm_") and x not in out:
            out.append(x)
        elif isinstance(x, list):
            for i in x:
                add(i)

    if area == "market":
        for p in blk.get("size_series") or []:
            add(p.get("claim"))
        add((blk.get("cagr") or {}).get("claim"))
        add(blk.get("kb_trend"))
        for t in blk.get("trends") or []:
            add(t.get("claim"))
        for r in blk.get("regulations") or []:
            add(r.get("claim"))
    elif area == "customer":
        add(blk.get("summary"))
        add(blk.get("strategy") or [])
        add(blk.get("expansion") or [])
        for s in blk.get("structure") or []:
            add(s.get("claim"))
        for o in blk.get("ops_challenges") or []:
            add(o.get("claim"))
    elif area == "user":
        for p in blk.get("personas") or []:
            add(p.get("claims") or [])
        for j in blk.get("journey") or []:
            add(j.get("claims") or [])
        for c in blk.get("composition") or []:
            add(c.get("claim"))
    elif area == "competitor":
        table = blk.get("table") or {}
        for crt in table.get("criteria") or []:
            for col in table.get("columns") or []:
                cell = ((table.get("cells") or {}).get(crt) or {}).get(col) or {}
                add(cell.get("claim_ids") or [])
        for s in blk.get("strengths") or []:
            add(s.get("claim_ids") or [])
    return out


def live_citations(version: dict[str, Any], claim_id: str) -> list[dict[str, Any]]:
    return [c for c in version.get("citations") or [] if c.get("claim_id") == claim_id and not c.get("dropped")]


def numbering(version: dict[str, Any], area: str) -> tuple[dict[str, list[int]], dict[str, int]]:
    """탭 안에서 첫 인용 순서로 1, 2, …. 같은 출처는 같은 번호(AC-MI-41)."""
    src_n: dict[str, int] = {}
    claim_ns: dict[str, list[int]] = {}
    order = claim_order(version.get("document") or {}, area)
    claims = version.get("claims") or {}
    for cid in order + [c for c, v in claims.items() if v.get("area") == area and c not in order]:
        ns = []
        for cit in live_citations(version, cid):
            sid = cit["source_id"]
            if sid not in src_n:
                src_n[sid] = len(src_n) + 1
            if src_n[sid] not in ns:
                ns.append(src_n[sid])
        claim_ns[cid] = ns
    return claim_ns, src_n


def claim_ref(claims: dict[str, Any], cid: str | None, ns: dict[str, list[int]]) -> dict[str, Any] | None:
    if not cid or cid not in claims:
        return None
    c = claims[cid]
    return {"id": cid, "text": c.get("text", ""), "status": c.get("status", "missing"), "label": c.get("label") or claim_label(c.get("status", "missing")),
            "ns": ns.get(cid, []), "inferred": bool(c.get("inferred")),
            "unverified_numbers": c.get("status") not in ("matched", "confirmed") and bool([n for n in c.get("numbers") or [] if n.get("kind") != "year"])}


# ── MI3 결과 ─────────────────────────────────────────────
def competitor_columns(analysis: dict[str, Any], table: dict[str, Any]) -> list[dict[str, Any]]:
    comps = {c["id"]: c for c in analysis.get("competitors") or []}
    cols = []
    for col in table.get("columns") or []:
        if col == "samsung":
            cols.append({"key": "samsung", "label": "삼성", "sub": "", "samsung": True})
        else:
            c = comps.get(col) or {"letter": "?", "real_name": ""}
            cols.append({"key": col, "label": anonymize.workspace_label(c), "sub": c.get("real_name", ""), "samsung": False})
    return cols


def tab_footer(version: dict[str, Any], area: str, src_n: dict[str, int]) -> dict[str, Any]:
    srcs = version.get("sources") or {}
    by: dict[str, int] = {}
    for sid in src_n:
        g = src_group(srcs.get(sid, {}))
        if g == "user":
            continue
        by[g] = by.get(g, 0) + 1
    total = sum(by.values())
    claims = [c for c in (version.get("claims") or {}).values() if c.get("area") == area]
    unverified = any(c.get("status") not in ("matched", "confirmed") and any(n.get("kind") != "year" for n in c.get("numbers") or [])
                     for c in claims) or any("[00]" in (c.get("text") or "") for c in claims)
    parts = [f"출처 {total}건"]
    if by.get("kb_case"):
        parts.append(f"사내 사례 DB {by['kb_case']}")
    if by.get("public"):
        parts.append(f"공개 자료 {by['public']}")
    if by.get("kb_official"):
        parts.append(f"사내 스펙 {by['kb_official']}")
    if by.get("internal"):
        parts.append(f"사내 자료 {by['internal']}")
    if unverified:
        parts.append("[수치는 검증 후 확정]")
    return {"sources": total, "by_kind": by, "unverified": unverified, "text": " · ".join(parts)}


def needs_check_count(version: dict[str, Any], area: str) -> int:
    return sum(1 for c in (version.get("claims") or {}).values()
               if c.get("area") == area and c.get("status") not in ("matched", "confirmed"))


def result_view(analysis: dict[str, Any], version: dict[str, Any], *, preview: bool = False, draft: dict[str, Any] | None = None,
                latest_n: int | None = None) -> dict[str, Any]:
    doc = version.get("document") or {}
    claims = version.get("claims") or {}
    areas = [a for a in rules.AREAS if a in ((analysis.get("scope") or {}).get("areas") or [])] or \
        [a for a in rules.AREAS if a in doc]
    area_status = dict(version.get("area_status") or {})
    if draft:
        for a in areas:
            if a not in area_status:
                area_status[a] = "running"
    tabs = []
    out: dict[str, Any] = {"analysis_id": analysis["id"], "version": int(version.get("n") or 0), "kind": version.get("kind", ""),
                           "created_at": version.get("created_at", ""), "stopped": bool(version.get("stopped")), "preview": preview,
                           "is_latest": latest_n is None or int(version.get("n") or 0) == latest_n,
                           "analysis_status": analysis.get("status", "done"), "footers": {}, "check_chips": [],
                           "web_unavailable": bool(version.get("web_unavailable")), "failed_areas": []}
    total_needs = 0
    for a in areas:
        st = area_status.get(a)
        if st in ("done", "reused"):
            tab_status = "done"
        elif st == "failed":
            tab_status = "failed"
            out["failed_areas"].append(a)
        elif preview or draft:
            tab_status = "running"
        else:
            tab_status = "wait"
        nc = needs_check_count(version, a) if tab_status == "done" else 0
        total_needs += nc
        tabs.append({"area": a, "label": rules.AREA_TAB[a], "status": tab_status, "needs_check": nc})
        if tab_status != "done":
            continue
        ns, src_n = numbering(version, a)
        out["footers"][a] = tab_footer(version, a, src_n)
        blk = doc.get(a) or {}
        cr = lambda cid: claim_ref(claims, cid, ns)  # noqa: E731
        if a == "market":
            out["market"] = {
                "size_series": [{"year": p.get("year"), "value": p.get("value"), "unit": p.get("unit", ""), "claim": cr(p.get("claim"))}
                                for p in blk.get("size_series") or []],
                "size_unit": blk.get("size_unit", ""), "size_label": blk.get("size_label", ""),
                "cagr": ({"value": (blk.get("cagr") or {}).get("value"), "period": (blk.get("cagr") or {}).get("period", ""),
                          "claim": cr((blk.get("cagr") or {}).get("claim"))} if blk.get("cagr") else None),
                "trends": [{"title": t.get("title", ""), "when": t.get("when"), "claim": cr(t.get("claim")), "implication": t.get("implication", "")}
                           for t in blk.get("trends") or []],
                "regulations": [{"title": r.get("title", ""), "claim": cr(r.get("claim"))} for r in blk.get("regulations") or []],
                "kb_trend": cr(blk.get("kb_trend")),
            }
        elif a == "customer":
            out["customer"] = {
                "summary": cr(blk.get("summary")),
                "strategy": [x for x in (cr(c) for c in blk.get("strategy") or []) if x],
                "expansion": [x for x in (cr(c) for c in blk.get("expansion") or []) if x],
                "structure": [{"label": s.get("label", ""), "value": s.get("value", ""), "claim": cr(s.get("claim"))} for s in blk.get("structure") or []],
                "ops_challenges": [{"stage": o.get("stage", ""), "claim": cr(o.get("claim"))} for o in blk.get("ops_challenges") or []],
                "reduced": bool(blk.get("reduced")),
            }
        elif a == "user":
            out["user"] = {
                "personas": [{"role": p.get("role", ""), "goal": p.get("goal", ""), "pain": p.get("pain", ""), "context": p.get("context", ""),
                              "claims": [x for x in (cr(c) for c in p.get("claims") or []) if x]} for p in blk.get("personas") or []],
                "journey": [{"stage": j.get("stage", ""), "touchpoint": j.get("touchpoint", ""), "pain": j.get("pain", ""),
                             "opportunity": j.get("opportunity", ""), "claims": [x for x in (cr(c) for c in j.get("claims") or []) if x]}
                            for j in blk.get("journey") or []],
                "composition": [{"label": c.get("label", ""), "value": c.get("value"), "unit": c.get("unit", "%"), "claim": cr(c.get("claim"))}
                                for c in blk.get("composition") or []],
            }
        elif a == "competitor":
            table = blk.get("table") or {}
            crit = {c["id"]: c for c in analysis.get("criteria") or []}
            rows = []
            for crt in table.get("criteria") or []:
                cells = {}
                for col in table.get("columns") or []:
                    cell = ((table.get("cells") or {}).get(crt) or {}).get(col) or {"text": "[확인 필요]", "placeholder": True}
                    cids = cell.get("claim_ids") or []
                    cns: list[int] = []
                    st_c = None
                    for cid in cids:
                        for n in ns.get(cid, []):
                            if n not in cns:
                                cns.append(n)
                        st_c = (claims.get(cid) or {}).get("status", st_c)
                    cells[col] = {"text": cell.get("text", ""), "claim_ids": cids, "ns": cns, "placeholder": bool(cell.get("placeholder")),
                                  "status": st_c, "verdict": cell.get("verdict")}
                c = crit.get(crt) or {"name": (table.get("criteria_names") or {}).get(crt, crt), "weight": 3}
                rows.append({"criterion_id": crt, "name": c.get("name", ""), "weight": int(c.get("weight", 3)), "cells": cells})
            out["competitor"] = {
                "table": {"columns": competitor_columns(analysis, table), "rows": rows} if table else None,
                "strengths": [{"id": s.get("id", ""), "title": s.get("title", ""), "note": s.get("note", ""), "criterion_ids": s.get("criterion_ids") or [],
                               "claims": [x for x in (cr(c) for c in s.get("claim_ids") or []) if x]} for s in blk.get("strengths") or []],
                "samsung_products": blk.get("samsung_products") or [],
            }
    out["tabs"] = tabs
    out["needs_check_total"] = total_needs
    out["implications"] = doc.get("implications")
    out["check_chips"] = check_chips(analysis, version)
    n_done = sum(1 for t in tabs if t["status"] == "done")
    if preview or draft:
        out["agent_text"] = "먼저 정리된 영역부터 보여 드려요. 나머지 탭은 정리 중이에요."
    else:
        out["agent_text"] = f"분석이 끝났습니다. {n_done}개 영역의 결과를 탭으로 정리했고, 각 항목은 출처와 함께 제안서에 인용할 수 있습니다."
    if analysis.get("status") == "upd" and out["is_latest"]:
        ch = analysis.get("upd_changes") or []
        out["upd"] = {"text": f"분석한 지 30일이 지났어요 · 바뀐 자료 {len(ch)}건", "count": len(ch)}
    return out


def check_chips(analysis: dict[str, Any], version: dict[str, Any]) -> list[dict[str, Any]]:
    chips: list[dict[str, Any]] = []
    seg = analysis.get("segment") or {}
    if seg.get("code"):
        s = config.segment(seg["code"])
        score = f" {rules.fmt2(seg.get('confidence'))}" if seg.get("confidence") is not None and seg.get("code") != "GEN" and seg.get("mode") != "pin" else ""
        chips.append({"kind": "segment", "label": f"업종 · {s['short']}{score}", "mode": seg.get("mode") or "auto"})
    cdec = (analysis.get("decisions") or {}).get("competitors") or {}
    if cdec.get("mode") == "check" and "competitor" in ((analysis.get("scope") or {}).get("areas") or []):
        chips.append({"kind": "competitors", "label": "경쟁사 자동 선정", "mode": "check"})
    n_conf = sum(1 for c in (version.get("claims") or {}).values() if c.get("status") == "conflict")
    if n_conf:
        chips.append({"kind": "conflict", "label": f"출처 간 값 다름 {n_conf}", "count": n_conf})
    n_inf = sum(1 for r in analysis.get("requirements") or [] if r.get("origin") == "inferred")
    if n_inf:
        chips.append({"kind": "inferred", "label": f"빈칸 추론 {n_inf}", "count": n_inf})
    return chips


# ── MI3S 주장 · 출처 카드 ────────────────────────────────
def claims_list(version: dict[str, Any], area: str, only_needs: bool = False) -> dict[str, Any]:
    claims = version.get("claims") or {}
    ns, src_n = numbering(version, area)
    order = claim_order(version.get("document") or {}, area)
    items = []
    for cid in order:
        c = claims.get(cid)
        if not c:
            continue
        if only_needs and c.get("status") in ("matched", "confirmed"):
            continue
        cits = []
        for cit in live_citations(version, cid):
            cits.append({"n": src_n[cit["source_id"]], "source_id": cit["source_id"], "status": cit.get("status", "needs_check")})
        items.append({"id": cid, "area": area, "text": c.get("text", ""), "status": c.get("status", "missing"),
                      "label": c.get("label") or claim_label(c.get("status", "missing")), "citations": cits,
                      "inferred": bool(c.get("inferred")), "block_path": c.get("block_path", "")})
    srcs = version.get("sources") or {}
    by: dict[str, int] = {"total": 0, "public": 0, "kb_case": 0, "kb_official": 0, "internal": 0, "needs_check": 0}
    for sid in src_n:
        g = src_group(srcs.get(sid, {}))
        if g == "user":
            continue
        by["total"] += 1
        by[g] = by.get(g, 0) + 1
    by["needs_check"] = sum(1 for sid in src_n if source_needs_check(version, sid, area))
    badges = {a: needs_check_count(version, a) for a in rules.AREAS if a in (version.get("area_status") or {})}
    parts = [f"이 탭 출처 {by['total']}건", f"공개 자료 {by['public']}", f"사내 사례 DB {by['kb_case']}"]
    if by.get("internal"):
        parts.append(f"사내 자료 {by['internal']}")
    if by.get("kb_official"):
        parts.append(f"사내 스펙 {by['kb_official']}")
    return {"items": items, "tab_sources": by, "badges": badges, "needs_check_total": sum(badges.values()), "summary_text": " · ".join(parts)}


def source_needs_check(version: dict[str, Any], sid: str, area: str | None = None) -> bool:
    claims = version.get("claims") or {}
    for c in version.get("citations") or []:
        if c.get("source_id") != sid or c.get("dropped"):
            continue
        if area and (claims.get(c["claim_id"]) or {}).get("area") != area:
            continue
        if c.get("status") != "matched":
            return True
    return False


SUBTYPE_DATE_WORD = {"기사": "게재"}


def _date_meta(src: dict[str, Any]) -> str:
    pub = src.get("published_at")
    d = rules.parse_iso(pub)
    if not d:
        return "[발행일 미상]"
    word = SUBTYPE_DATE_WORD.get(src.get("subtype") or "", "발행")
    return f"{d.year}년 {d.month}월 {word}"


def _checked_word(iso: str | None) -> str:
    d = rules.parse_iso(iso)
    if not d:
        return ""
    today = rules.now().astimezone(rules.KST).date()
    if d.astimezone(rules.KST).date() == today:
        return "오늘 확인"
    return f"{rules.month_day(iso)} 확인"


def kind_label(src: dict[str, Any]) -> str:
    kind = src.get("kind")
    base = kind if kind != "ca_import" else src.get("orig_kind")
    if base == "web":
        lab = f"공개 자료 · {src.get('subtype') or '기타'}"
    elif base == "websearch_summary":
        lab = "웹 검색 요약"
    elif base == "kb_case":
        lab = "사내 사례 DB"
    elif base == "kb_official":
        lab = "사내 스펙" if src.get("subtype") == "스펙" else "삼성 공식"
    elif base == "file":
        prefix = "고객 자료" if src.get("classification") == "customer" else "사내 자료"
        lab = f"{prefix} · {src.get('title') or '파일'}"
    elif base == "user":
        lab = "직접 입력"
    else:
        lab = "출처"
    if kind == "ca_import":
        lab += " · 경쟁사 분석에서"
    return lab


def footnote(src: dict[str, Any], cit: dict[str, Any] | None = None) -> str:
    """`{발행처}, 「{제목}」, {YYYY.MM}, p.{n}, {URL} (확인 {YYYY-MM-DD})` — 비는 칸은 뺀다. 요약은 `웹 검색 요약, "{검색어}", 검색 {YYYY-MM-DD} (원문 미확인)`."""
    if src.get("kind") == "websearch_summary":
        d = rules.parse_iso(src.get("retrieved_at"))
        day = d.strftime("%Y-%m-%d") if d else ""
        return f"웹 검색 요약, \"{src.get('query') or ''}\", 검색 {day} (원문 미확인)"
    parts = []
    if src.get("publisher"):
        parts.append(src["publisher"])
    if src.get("title"):
        parts.append(f"「{src['title']}」")
    pd = rules.parse_iso(src.get("published_at"))
    if pd:
        parts.append(f"{pd.year}.{pd.month:02d}")
    page = (cit or {}).get("page")
    if page:
        parts.append(f"p.{page}")
    if src.get("url"):
        parts.append(src["url"])
    rd = rules.parse_iso(src.get("retrieved_at"))
    s = ", ".join(parts)
    if rd:
        s += f" (확인 {rd.strftime('%Y-%m-%d')})"
    return s


def source_card(src: dict[str, Any], cit: dict[str, Any] | None, n: int, *, claim: dict[str, Any] | None = None,
                has_snapshot: bool = False) -> dict[str, Any]:
    kind = src.get("kind")
    base = kind if kind != "ca_import" else src.get("orig_kind")
    status = (cit or {}).get("status") or ("matched" if base == "user" else "needs_check")
    if base == "user":
        status = "confirmed"
    status_label = "원문 일치" if status == "matched" else ("확정" if status == "confirmed" else "확인 필요")
    reason = (cit or {}).get("reason_text") or ""
    code = (cit or {}).get("reason_code")
    quote = (cit or {}).get("quote") or ""
    style = "normal"
    if code == "QUOTE_NOT_FOUND":
        style = "model"
    elif base == "websearch_summary":
        style = "summary"
    elif code == "FETCH_FAILED":
        style = "snippet"
        quote = src.get("snippet") or quote
    elif base == "user":
        style = "value"
    hl = (cit or {}).get("highlight") or ""
    before = after = ""
    if hl and hl in quote and style == "normal":
        i = quote.find(hl)
        before, after = quote[:i], quote[i + len(hl):]
    # 메타
    if base in ("web", "ca_import"):
        meta = " · ".join(x for x in [_date_meta(src), f"p.{cit['page']}" if (cit or {}).get("page") else "", _checked_word((cit or {}).get("verified_at") or src.get("retrieved_at"))] if x)
    elif base == "websearch_summary":
        meta = f"원문 URL 없음 · {rules.month_day(src.get('retrieved_at'))} 검색"
    elif base == "kb_case":
        meta = " · ".join(x for x in [src.get("title"), (src.get("published_at") or "")[:10]] if x)
    elif base == "kb_official":
        meta = f"samsung.com · {(src.get('published_at') or src.get('retrieved_at') or '')[:10]}"
    elif base == "file":
        meta = " · ".join(x for x in [f"p.{cit['page']}" if (cit or {}).get("page") else "", (src.get("retrieved_at") or "")[:10]] if x)
    elif base == "user":
        meta = f"{src.get('publisher') or ''} · {rules.month_day(src.get('retrieved_at'))} 입력"
    else:
        meta = ""
    # 동작
    actions: list[str] = []
    cst = (claim or {}).get("status")
    if base == "user":
        actions = ["되돌리기"]
    elif base == "websearch_summary":
        actions = ["각주로 복사", "URL 붙여 확인", "다른 출처 찾기", "값 직접 확정", "이 출처 빼기"]
    elif base == "file":
        actions = ["파일 열기", "각주로 복사"] if status == "matched" else ["파일 열기", "다른 출처 찾기", "값 직접 확정", "이 출처 빼기"]
    elif status == "matched":
        actions = (["원문 열기"] if src.get("url") else []) + ["각주로 복사"]
    elif cst == "conflict":
        actions = (["원문 열기"] if src.get("url") else []) + ["값 직접 확정", "출처 비교"]
    elif status == "stale":
        actions = (["원문 열기"] if src.get("url") else []) + ["다른 출처 찾기", "값 직접 확정"]
    else:
        actions = (["원문 열기"] if src.get("url") and code == "FETCH_FAILED" else []) + ["다른 출처 찾기", "값 직접 확정", "이 출처 빼기"]
    if has_snapshot and src.get("url") and base in ("web",):
        actions.append("수집본 보기")
    flag = "대외 사용 전 확인" if src.get("claim_flag") else ""
    if base == "file" and src.get("method") == "i2t":
        reason = reason or "이미지에서 읽은 값이에요."
    return {"n": n, "source_id": src["id"], "kind": kind, "kind_label": kind_label(src), "status": status, "status_label": status_label,
            "title": src.get("title") or "", "meta": meta, "quote": quote, "quote_before": before, "quote_highlight": hl if before or after or hl == quote else "",
            "quote_after": after, "quote_style": style, "reason": reason if status != "matched" or base == "file" else "", "reason_code": code,
            "actions": actions, "url": src.get("url") if base not in ("websearch_summary",) else None, "file_id": src.get("file_id"),
            "page": (cit or {}).get("page"), "footnote": footnote(src, cit), "flag": flag, "has_snapshot": has_snapshot}


# ── MI0 행 ───────────────────────────────────────────────
DRAFT_STAGE = {"input": "고객 요구사항", "industry": "고객 요구사항", "scope": "분석 범위", "competitors": "분석 범위", "design": "분석 설계",
               "design/industry": "분석 설계"}
STAGE_NAME = {"search": "검색", "organize": "정리", "write": "작성"}
CHANGE_KIND_LABEL = {"competitor_new_product": "경쟁사 신제품 발표", "report_revised": "시장 리포트 개정", "source_changed": "출처 내용 변경",
                     "kb_updated": "지식 DB 갱신"}


def time_label(a: dict[str, Any]) -> str:
    st = a.get("status")
    if st in ("done", "upd"):
        if a.get("edit_after_analysis"):
            return f"{rules.relative(a.get('updated_at'))} 수정"
        return f"{rules.month_day(a.get('analyzed_at'))} 분석"
    if st in ("queued", "running"):
        started = (a.get("run") or {}).get("started_at") or a.get("updated_at")
        rel = rules.relative(started)
        return "방금 시작" if rel == "방금" else f"{rel} 시작"
    return f"{rules.relative(a.get('updated_at'))} 저장"


def note_for(a: dict[str, Any]) -> str:
    st = a.get("status")
    run = a.get("run") or {}
    if st == "done":
        s = f"출처 {int(run.get('sources_used') or 0)}곳"
        if int(run.get("fix_open") or 0):
            s += f" · 확정 필요 수치 {int(run['fix_open'])}"
        return s
    if st == "upd":
        ch = a.get("upd_changes") or []
        if ch and all(c.get("kind") == "competitor_new_product" for c in ch):
            return f"경쟁사 신제품 감지 {len(ch)}건"
        return f"분석 30일 경과 · 자료 갱신 {len(ch)}건"
    if st in ("queued", "running"):
        stage = STAGE_NAME.get(run.get("stage") or "search", "검색")
        return f"{stage} 중 · 출처 {int(run.get('sources_total') or 0)}곳 확인"
    if st == "failed":
        return "분석을 마치지 못했어요"
    stage = DRAFT_STAGE.get(a.get("last_screen") or "input", "고객 요구사항")
    if st in ("designed", "ask", "designing") and stage == "고객 요구사항":
        stage = "분석 설계"
    return f"{stage}까지 입력"


def changes_summary(changes: list[dict[str, Any]]) -> str:
    return " · ".join(c.get("title", "") for c in changes[:3])


def list_item(a: dict[str, Any], route: str) -> dict[str, Any]:
    aid = a["id"]
    st = a.get("status", "draft")
    run = a.get("run") or {}
    fix_open = int(run.get("fix_open") or 0)
    if st in ("queued", "running"):
        action = {"label": "진행 보기", "route": f"/mi/{aid}/run", "kind": "progress"}
    elif st == "done":
        action = {"label": "수치 확정", "route": f"/mi/{aid}/verify", "kind": "fix"} if fix_open else \
            {"label": "열기", "route": f"/mi/{aid}/result", "kind": "open"}
    elif st == "upd":
        action = {"label": "다시 분석", "route": f"/mi/{aid}/run", "kind": "rerun"}
    elif st == "failed":
        action = {"label": "다시 시도", "route": f"/mi/{aid}/run", "kind": "retry"}
    else:
        action = {"label": "이어서", "route": route, "kind": "continue"}
    seg = (a.get("segment") or {}).get("code")
    areas = [x for x in rules.AREAS if x in ((a.get("scope") or {}).get("areas") or [])]
    ver = int(a.get("result_version") or 0)
    menu: list[dict[str, Any]] = []
    head = None
    prop_short = ((a.get("latest_handoff") or {}).get("target_title") or (a.get("links") or {}).get("proposal_title") or "")
    if st == "upd":
        ch = a.get("upd_changes") or []
        affected = sorted({x for c in ch for x in c.get("affected_areas") or []}, key=lambda x: rules.AREAS.index(x))
        head = {"title": f"바뀐 자료 {len(ch)}건", "summary": changes_summary(ch)}
        menu = [
            {"key": "changed_only", "label": "바뀐 부분만 다시 분석", "hint": f"{rules.scope_label(affected) or '변경 영역'} · {rules.eta_label(rules.changed_eta_s(len(affected) or 1))}",
             "route": f"/mi/{aid}/run", "highlight": True},
            {"key": "full", "label": "전체 다시 분석", "hint": f"v{ver + 1}{rules.josa(str(ver + 1), '으로', '로')} 저장 · v{ver} 보관", "route": f"/mi/{aid}/run"},
            {"key": "open_last", "label": "지난 결과 열기", "hint": f"v{ver} · {rules.month_day(a.get('analyzed_at'))}", "route": f"/mi/{aid}/result?version={ver}"},
            {"key": "send", "label": "제안서 MI 섹션으로 보내기", "hint": prop_short or "보낼 제안서 고르기", "route": f"/mi/{aid}/export"},
            {"key": "duplicate", "label": "복제해서 새 분석", "hint": "범위 그대로", "route": None},
        ]
    elif st == "done":
        menu = [{"key": "full", "label": "전체 다시 분석", "hint": f"v{ver + 1}{rules.josa(str(ver + 1), '으로', '로')} 저장 · v{ver} 보관", "route": f"/mi/{aid}/run"}]
        if ver >= 2:
            menu.append({"key": "versions", "label": "지난 결과 열기", "hint": f"v{ver - 1} 이전 결과", "route": f"/mi/{aid}/result?versions=1"})
        menu += [{"key": "send", "label": "제안서 MI 섹션으로 보내기", "hint": prop_short or "보낼 제안서 고르기", "route": f"/mi/{aid}/export"},
                 {"key": "duplicate", "label": "복제해서 새 분석", "hint": "범위 그대로", "route": None}]
    elif st in ("queued", "running"):
        menu = [{"key": "stop", "label": "중지", "hint": "정리된 영역은 남겨요", "route": None},
                {"key": "duplicate", "label": "복제해서 새 분석", "hint": "범위 그대로", "route": None}]
    else:
        menu = [{"key": "duplicate", "label": "복제해서 새 분석", "hint": "범위 그대로", "route": None},
                {"key": "delete", "label": "삭제", "hint": "되돌릴 수 없어요", "route": None}]
    title = a.get("title") or ""
    if not title:
        from .service import default_title

        title = default_title(a) or "새 분석"
    title = anonymize.scrub(title, a.get("competitors") or [], {})
    return {
        "id": aid, "title": title, "version": ver, "owner_name": a.get("owner_name", ""), "time_label": time_label(a),
        "sub": f"{a.get('owner_name', '')} · {time_label(a)}", "segment": seg,
        "segment_label": config.segment(seg)["short"] if seg else "—", "scope_label": rules.scope_label(areas) if areas else "범위 선택 전",
        "scope_selected": bool(areas), "status": st, "status_label": rules.STATUS_LABEL.get(st, "작성 중"),
        "status_tone": rules.STATUS_TONE.get(st, "draft"), "note": anonymize.scrub(note_for(a), a.get("competitors") or [], {}),
        "proposal_title": (a.get("latest_handoff") or {}).get("target_title"), "action": action, "menu": menu,
        "changes_head": anonymize.scrub(head, a.get("competitors") or [], {}) if head else None, "route": route,
        "updated_at": a.get("updated_at", ""), "current_job_id": a.get("current_job_id"), "fix_open": fix_open,
        "has_competitors": bool(anonymize.live(a.get("competitors") or [])),
    }
