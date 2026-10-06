"""레이아웃 선택 · 데이터 적합도(03-mi.md §7.8 · §10.5). 결정적 — 데이터 모양만 보고 고른다."""
from __future__ import annotations

import ast
from typing import Any

from . import config, rules
from .store import nid

INDUSTRY_LETTER = {"MS": "A", "TR": "A", "MS+TR": "A", "CB": "B", "US": "C"}
AREA_OF_TYPE = {"MS": "market", "TR": "market", "MS+TR": "market", "CB": "customer", "US": "user", "CP": "competitor", "IM": None}
TYPE_OF_AREA = {"market": "MS", "customer": "CB", "user": "US", "competitor": "CP"}


# ── 템플릿 카탈로그 ──────────────────────────────────────
def template(code: str, segment: str | None = None) -> dict[str, Any]:
    cfg = config.templates_cfg().get("templates", {})
    if code.startswith("MI-") and code.count("-") == 2:
        _, seg, letter = code.split("-")
        base = dict(cfg[f"MI-XX-{letter}"])
        s = config.segment(seg)
        base["name"] = base["name"].format(short=s["short"], code=seg)
        base["code"] = code
        base["industry_code"] = seg
        return base
    base = dict(cfg.get(code) or {})
    base["code"] = code
    return base


def industry_code(seg: str | None, sheet_type: str) -> str | None:
    if not seg or seg == "GEN":
        return None
    letter = INDUSTRY_LETTER.get(sheet_type)
    return f"MI-{seg}-{letter}" if letter else None


def band(sheet_type: str) -> list[str]:
    order = config.templates_cfg().get("order", {})
    if sheet_type == "MS+TR":
        return list(order.get("MS", [])) + list(order.get("TR", []))
    return list(order.get(sheet_type, []))


def template_name(code: str) -> str:
    return template(code).get("name", code)


def thumb_kind(code: str) -> str:
    return template(code).get("thumb", "table")


# ── 안전한 식 계산 ───────────────────────────────────────
_ALLOWED = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.Compare, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
            ast.Eq, ast.NotEq, ast.Name, ast.Load, ast.Constant, ast.BinOp, ast.Div, ast.Mult, ast.Add, ast.Sub, ast.Call,
            ast.IfExp, ast.USub)


def safe_eval(expr: str, env: dict[str, float]) -> float:
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED):
            raise ValueError(f"허용하지 않는 식: {expr}")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in ("min", "max")):
            raise ValueError(f"허용하지 않는 함수: {expr}")
    return eval(compile(tree, "<fit>", "eval"), {"__builtins__": {}, "min": min, "max": max}, dict(env))  # noqa: S307


def _fmt_label(label: str, m: dict[str, float]) -> str:
    out = label
    for k, v in m.items():
        out = out.replace("{" + k + "}", str(int(v)) if isinstance(v, (int, float)) and float(v).is_integer() else str(v))
    return out


def fit(code: str, m: dict[str, float]) -> tuple[int, list[dict[str, Any]]]:
    """(fit, needs_report). 필수 하나라도 못 채우면 -1."""
    t = template(code)
    report: list[dict[str, Any]] = []
    ok_all = True
    for r in t.get("requires") or []:
        ok = bool(safe_eval(r["expr"], m))
        ok_all = ok_all and ok
        report.append({"need": _fmt_label(r["label"], m), "ok": ok, "detail": "필수"})
    opt = t.get("optional") or []
    num = den = 0.0
    for o in opt:
        s = float(max(0.0, min(1.0, safe_eval(str(o["score"]), m))))
        w = float(o.get("weight", 1))
        num += w * s
        den += w
        report.append({"need": _fmt_label(o["label"], m), "ok": s >= 0.999, "detail": f"{round(s * 100)}%"})
    if not ok_all:
        return -1, report
    if den == 0:
        return 100, report
    return rules.half_up(100 * num / den), report


# ── 결과 → 데이터 지표 ───────────────────────────────────
def metrics(analysis: dict[str, Any], version: dict[str, Any] | None) -> dict[str, float]:
    doc = (version or {}).get("document") or {}
    claims = (version or {}).get("claims") or {}
    mk = doc.get("market") or {}
    cu = doc.get("customer") or {}
    us = doc.get("user") or {}
    cp = doc.get("competitor") or {}
    size = [p for p in mk.get("size_series") or [] if p.get("value") is not None]
    trends = mk.get("trends") or []
    market_claims = [c for c in claims.values() if c.get("area") == "market"]
    numeric = [c for c in market_claims if any(n.get("kind") != "year" for n in c.get("numbers") or [])]
    verified = [c for c in numeric if c.get("status") in ("matched", "confirmed")]
    metric_keys = {c.get("metric_key") or c["id"] for c in numeric if "[00]" not in (c.get("text") or "")}
    table = cp.get("table") or {}
    cols = [c for c in table.get("columns") or [] if c != "samsung"]
    crit = table.get("criteria") or []
    cells = table.get("cells") or {}
    two_axis = 0
    for col in cols:
        known = sum(1 for crt in crit if not (cells.get(crt, {}).get(col) or {}).get("placeholder", True))
        if known >= 2:
            two_axis += 1
    area_status = (version or {}).get("area_status") or {}
    tabs_done = sum(1 for a in rules.AREAS if area_status.get(a) in ("done", "reused"))
    files = analysis.get("files") or []
    strategy_doc = 1 if any(f.get("doc_kind") in ("ir",) and f.get("include", True) for f in files) else 0
    public_docs = int(((analysis.get("extracted") or {}).get("customer_public_docs")) or 0)
    if not public_docs:
        srcs = (version or {}).get("sources") or {}
        public_docs = len({s["id"] for s in srcs.values() if "customer" in (s.get("areas") or []) and s.get("classification") == "public"
                           and s.get("state") != "excluded"})
    share = [c for c in claims.values() if c.get("metric_key") == "market_share"]
    return {
        "size_years": float(len(size)),
        "cagr": 1.0 if (mk.get("cagr") or {}).get("value") is not None else 0.0,
        "trends": float(len(trends)),
        "trends_dated": float(sum(1 for t in trends if t.get("when"))),
        "implications": float(sum(1 for t in trends if t.get("implication"))),
        "verified_ratio": (len(verified) / len(numeric)) if numeric else 0.0,
        "metrics": float(len(metric_keys)),
        "target_share": float(sum(1 for c in claims.values() if c.get("metric_key") == "target_share")),
        "segments_data": float(sum(1 for c in claims.values() if str(c.get("metric_key") or "").startswith("segment_"))),
        "structure": float(len(cu.get("structure") or [])),
        "ops_stages": float(len(cu.get("ops_challenges") or [])),
        "strategy_doc": float(strategy_doc),
        "swot_internal": 0.0,
        "swot_external": 0.0,
        "public_docs": float(public_docs),
        "user_types": float(len(us.get("personas") or [])),
        "journey_steps": float(len(us.get("journey") or [])),
        "composition": float(len(us.get("composition") or [])),
        "suppliers": float(len(cols)),
        "criteria": float(len(crit)),
        "two_axis": float(two_axis),
        "share_data": float(len(share)),
        "share_trend": float(len({(c.get("numbers") or [{}])[0].get("year") for c in share})) if share else 0.0,
        "tabs_done": float(tabs_done),
    }


# ── 문장 ─────────────────────────────────────────────────
def data_summary(sheet_type: str, m: dict[str, float], segment: str | None = None) -> str:
    i = lambda k: int(m.get(k, 0))  # noqa: E731
    if sheet_type == "MS+TR":
        return f"연도별 시장 규모 {i('size_years')}개년과 트렌드 {i('trends')}개"
    if sheet_type == "MS":
        return f"연도별 시장 규모 {i('size_years')}개년" if i("size_years") else f"성장 동인 {i('trends')}개"
    if sheet_type == "TR":
        return f"트렌드 {i('trends')}개"
    if sheet_type == "CB":
        return f"운영 단계별 과제 {i('ops_stages')}개" if i("ops_stages") else "고객사 공개 자료"
    if sheet_type == "US":
        who = config.segment(segment).get("user", "사용자") if segment else "사용자"
        if i("journey_steps"):
            return f"{who} 여정 {i('journey_steps')}단계"
        return f"사용자 유형 {i('user_types')}개"
    if sheet_type == "CP":
        return f"경쟁사 {i('suppliers')}곳 × 요구 기준 {i('criteria')}개"
    if sheet_type == "IM":
        return f"{i('tabs_done')}개 탭 결과"
    return ""


def item_label(sheet_type: str, code: str, m: dict[str, float]) -> str:
    i = lambda k: int(m.get(k, 0))  # noqa: E731
    if sheet_type == "MS+TR":
        return f"시장 규모 · 트렌드 {i('trends')}"
    if sheet_type == "MS":
        return "시장 규모 · 성장률" if code in ("MS-B", "MS-C", "MS-D") else ("핵심 시장 수치" if code == "MS-A" else "성장 동인 · 전망")
    if sheet_type == "TR":
        return f"산업 트렌드 {i('trends')}"
    if sheet_type == "CB":
        return "운영 구조 · 과제" if i("ops_stages") or i("structure") else "고객사 요약 · 전략"
    if sheet_type == "US":
        return f"사용자 페르소나 {i('user_types')}" if code in ("US-A",) else f"사용자 여정 {i('journey_steps')}단계"
    if sheet_type == "CP":
        return f"비교표 · {i('suppliers')}사 × {i('criteria')}항목"
    if sheet_type == "IM":
        return f"{i('tabs_done')}개 탭 종합"
    return ""


def why_for(kind: str, sheet_type: str, code: str, m: dict[str, float], segment: str | None, **kw: Any) -> str:
    summary = data_summary(sheet_type, m, segment)
    if kind == "pinned":
        return "고정한 시트라 다시 고르지 않았어요"
    if kind == "industry":
        return f"업종 레이아웃 우선 · {summary}{rules.josa(summary, '이', '가')} 이 틀에 그대로 들어가요"
    if kind == "reduced":
        n = int(m.get("public_docs", 0))
        return f"고객 공개 자료가 {n}건이라 {template_name('CB-A')}{rules.josa(template_name('CB-A'), '으로', '로')} 고정했어요"
    if kind == "cp":
        reason = {"CP-A": "표가 가장 정확해요", "CP-B": "포지셔닝 맵이 가장 잘 보여요", "CP-C": "점유율 + 추이가 가장 정확해요"}.get(code, "이 틀이 가장 잘 맞아요")
        return f"업종 틀엔 경쟁 장이 없어 범용 · {summary}라 {reason}"
    if kind == "extra":
        return f"섹션엔 없지만 {summary}{rules.josa(summary, '이', '가')} 있어요 · 넣으면 Value Props 근거가 강해져요"
    if kind == "im_excluded":
        return "표준은 3시트라 뺐어요 · Solution형이거나 경영진 보고면 자동으로 넣어요"
    if kind == "im":
        return "분석한 탭을 묶어 발견 → 시사점 → 방향으로 정리해요" if code == "IM-A" else "경영진 보고용 4분면 요약 + 결론이에요"
    if kind == "fallback":
        need = kw.get("need") or "필요한 값"
        return f"{need}{rules.josa(need, '이', '가')} 없어 {template_name(code)}{rules.josa(template_name(code), '으로', '로')} 바꿨어요 · 빈 값은 [확정 필요]"
    name = template_name(code)
    return f"데이터 모양 · {summary}라 {name}{rules.josa(name, '이', '가')} 가장 잘 맞아요"


# ── 시트 고르기 ──────────────────────────────────────────
def choose(sheet_type: str, m: dict[str, float], segment: str | None, *, reduced: bool = False, pinned_code: str | None = None,
           intent_pick: str | None = None, allow_industry: bool = True) -> dict[str, Any]:
    """시트 하나의 템플릿 고르기(§7.8 1~5). 돌려주는 값: {code, fit, needs, industry, why_kind, alternatives, need_missing}."""
    cands = band(sheet_type)
    if pinned_code:
        f, needs = fit(pinned_code, m)
        return {"code": pinned_code, "fit": f, "needs": needs, "industry": pinned_code.startswith("MI-"), "why_kind": "pinned",
                "alternatives": _alts(cands, pinned_code, m)}
    if sheet_type == "CB" and reduced:
        f, needs = fit("CB-A", m)
        return {"code": "CB-A", "fit": f, "needs": needs, "industry": False, "why_kind": "reduced", "alternatives": _alts(cands, "CB-A", m)}
    ind = industry_code(segment, sheet_type) if allow_industry else None
    if ind:
        f, needs = fit(ind, m)
        if f >= 0:
            return {"code": ind, "fit": f, "needs": needs, "industry": True, "why_kind": "industry", "alternatives": _alts(cands, ind, m)}
    scored = [(c, *fit(c, m)) for c in cands]
    ok = [s for s in scored if s[1] >= 0]
    if ok:
        best = max(s[1] for s in ok)
        tied = [s for s in ok if best - s[1] < int(config.th("layout_tie", 5))]
        pick = tied[0]
        if len(tied) > 1 and intent_pick and any(t[0] == intent_pick for t in tied):
            pick = next(t for t in tied if t[0] == intent_pick)
        kind = "cp" if sheet_type == "CP" else "generic"
        return {"code": pick[0], "fit": pick[1], "needs": pick[2], "industry": False, "why_kind": kind,
                "alternatives": _alts(cands, pick[0], m)}
    # 모두 불가 → 대체 템플릿(§7.8 4)
    first = cands[0] if cands else "CP-A"
    fb = config.templates_cfg().get("fallback", {}).get(first, cands[-1] if cands else first)
    f, needs = fit(fb, m)
    missing = next((n["need"] for n in fit(first, m)[1] if not n["ok"]), None)
    return {"code": fb, "fit": f, "needs": needs, "industry": False, "why_kind": "fallback", "alternatives": _alts(cands, fb, m),
            "need_missing": (missing or "").split(" · ")[0]}


def _alts(cands: list[str], chosen: str, m: dict[str, float], k: int = 2) -> list[dict[str, Any]]:
    out = [{"code": c, "fit": fit(c, m)[0]} for c in cands if c != chosen]
    out.sort(key=lambda a: (-a["fit"], cands.index(a["code"])))
    return out[:k]


def sheet_plan(analysis: dict[str, Any], version: dict[str, Any] | None, *, previous: list[dict[str, Any]] | None = None,
               usage: str | None = None, intents: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """쓰임 · 범위 · 데이터 → 시트 구성(§7.8 시트 묶음). previous 의 고정 · 포함 선택을 이어받는다."""
    usage = usage or (analysis.get("usage") or {}).get("value") or "none"
    seg = (analysis.get("segment") or {}).get("code")
    mix = (analysis.get("segment") or {}).get("mix")
    area_status = (version or {}).get("area_status") or {}
    scope = [a for a in rules.AREAS if a in ((analysis.get("scope") or {}).get("areas") or [])]
    analyzed = [a for a in scope if area_status.get(a) in ("done", "reused")] if version else scope
    reduced = "customer" in ((analysis.get("scope") or {}).get("reduced") or [])
    m = metrics(analysis, version)
    prev = {p["sheet_type"]: p for p in previous or []}
    rows: list[dict[str, Any]] = []

    def seg_for(sheet_type: str) -> str | None:
        if mix:
            return mix.get("c") if sheet_type == "US" else mix.get("a")
        return seg

    def add(sheet_type: str, included: bool, mode: str, *, extra: bool = False, allow_industry: bool = True, in_section: bool = True) -> None:
        p = prev.get(sheet_type)
        if p is None and sheet_type in ("MS", "MS+TR"):
            # 쓰임이 바뀌면(리포트 → 표준 제안서 넘김) 같은 시장 시트가 MS ↔ MS+TR 로 불린다 — 같은 시트(id)로 잇는다.
            # 못 이으면 넘길 때마다 id 가 새로 생겨 넘김 `sheets`(고른 id)와 맞지 않아 MS 가 빠졌다(통합).
            p = prev.get("MS+TR" if sheet_type == "MS" else "MS")
        pinned_code = p.get("template_code") if p and p.get("pinned") else None
        s = seg_for(sheet_type)
        pick = choose(sheet_type if sheet_type != "MS+TR" else "MS+TR", m, s, reduced=reduced, pinned_code=pinned_code,
                      intent_pick=(intents or {}).get(sheet_type), allow_industry=allow_industry)
        code = pick["code"]
        st = sheet_type
        if sheet_type == "MS+TR" and not pick["industry"] and not pinned_code:
            st = "MS"
        names = config.templates_cfg().get("sheet_names", {})
        if st == "MS+TR":
            sheet_name = names.get("MS+TR", "시장 · 트렌드")
        elif st == "US" and pick["industry"]:
            sheet_name = names.get("US_industry", "사용자 여정")
        else:
            sheet_name = names.get(st, st)
        if extra:
            why = why_for("extra", st, code, m, s)
        elif st == "IM" and not included:
            why = why_for("im_excluded", st, code, m, s)
        elif st == "IM":
            why = why_for("im", st, code, m, s)
        else:
            why = why_for(pick["why_kind"], st, code, m, s, need=pick.get("need_missing"))
        area = AREA_OF_TYPE.get(st)
        rows.append({
            "id": (p or {}).get("id") or nid("sht"),
            "sheet_type": st,
            "sheet_name": sheet_name,
            "source_label": f"MI 결과 · {rules.AREA_FIX_TAB[area]}" if area else f"{int(m['tabs_done'])}개 탭 종합",
            "item_label": item_label(st, code, m),
            "included": bool(p["included"]) if p and p.get("include_mode") == "pin" else included,
            "include_mode": "pin" if p and p.get("include_mode") == "pin" else mode,
            "template_code": code,
            "template_name": template_name(code) if not code.startswith("MI-") else template(code)["name"],
            "thumb_kind": thumb_kind(code),
            "industry_layout": bool(pick["industry"]),
            "why": why,
            "fit": int(pick["fit"]),
            "alternatives": pick["alternatives"],
            "needs_report": pick["needs"],
            "pinned": bool(pinned_code),
            "options": (p or {}).get("options") or {},
            "area": area,
            "in_section": in_section,
            "order": len(rows),
        })

    if usage == "quickwin":
        return []
    if usage == "standard":
        main = [a for a in ("market", "customer", "competitor") if a in analyzed]
        if mix and "user" in analyzed:
            # 섞어서 보기 = 사용자 여정을 다른 업종 틀로 보려는 것 → 사용자 시트가 섹션에 들어간다(MIC 5번)
            main = [a for a in ("market", "customer", "user") if a in analyzed]
        if len(main) < 3 and "user" in analyzed:
            main.append("user")
        main = [a for a in rules.AREAS if a in main]
        for a in main:
            add("MS+TR" if a == "market" else TYPE_OF_AREA[a], True, "auto")
        for a in analyzed:
            if a not in main:
                add("MS+TR" if a == "market" else TYPE_OF_AREA[a], False, "check", extra=True, in_section=False)
        if len(analyzed) >= 2:
            add("IM", False, "auto", in_section=False)
    elif usage == "solution":
        for a in analyzed:
            add("MS+TR" if a == "market" else TYPE_OF_AREA[a], True, "auto")
            if a == "market" and rows and rows[-1]["sheet_type"] == "MS" and m["trends"] >= 1:
                add("TR", True, "auto")
            if a == "market" and rows and rows[-1]["sheet_type"] == "MS+TR" and m["trends"] >= 5:
                add("TR", True, "auto")
        add("IM", True, "auto")
        for r in rows:
            if r["sheet_type"] == "IM" and r["template_code"] != "IM-A" and not r["pinned"]:
                f, needs = fit("IM-A", m)
                r.update(template_code="IM-A", template_name=template_name("IM-A"), thumb_kind=thumb_kind("IM-A"), fit=f, needs_report=needs,
                         why=why_for("im", "IM", "IM-A", m, seg))
    elif usage == "exec_onepager":
        add("IM", True, "auto")
        for r in rows:
            if r["sheet_type"] == "IM" and not r["pinned"]:
                f, needs = fit("IM-B", m)
                r.update(template_code="IM-B", template_name=template_name("IM-B"), thumb_kind=thumb_kind("IM-B"), fit=f, needs_report=needs,
                         why=why_for("im", "IM", "IM-B", m, seg))
        appendix = 0
        for a in ("market", "competitor"):
            if a in analyzed and appendix < 2:
                add("MS" if a == "market" else "CP", True, "auto", allow_industry=False)
                appendix += 1
        for a in analyzed:
            if a not in ("market", "competitor"):
                add(TYPE_OF_AREA[a], False, "check", extra=True, in_section=False)
    else:  # none — 리포트: 분석한 영역마다 한 장(보낼 때 다시 매핑)
        for a in analyzed:
            add("MS+TR" if a == "market" else TYPE_OF_AREA[a], True, "auto")
    for i, r in enumerate(rows):
        r["order"] = i
    return rows


def preview_sheets(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """설계 단계 시트 미리보기(§7.8 을 데이터 없이 — 업종 레이아웃 여부만)."""
    usage = (analysis.get("usage") or {}).get("value") or "none"
    seg = (analysis.get("segment") or {}).get("code")
    mix = (analysis.get("segment") or {}).get("mix")
    scope = [a for a in rules.AREAS if a in ((analysis.get("scope") or {}).get("areas") or [])]
    reduced = "customer" in ((analysis.get("scope") or {}).get("reduced") or [])
    n_comp = len([c for c in analysis.get("competitors") or [] if not c.get("removed")])
    n_crit = len([c for c in analysis.get("criteria") or [] if c.get("enabled", True)])
    names = config.templates_cfg().get("sheet_names", {})
    out: list[dict[str, Any]] = []

    def gen(sheet_type: str) -> dict[str, Any]:
        s = (mix.get("c") if sheet_type == "US" else mix.get("a")) if mix else seg
        if sheet_type == "CP":
            return {"sheet": names["CP"], "code": "CP-A", "thumb": thumb_kind("CP-A"), "note": f"범용 · {n_comp}사 × {n_crit}기준", "industry": False}
        if sheet_type == "CB" and reduced:
            return {"sheet": names["CB"], "code": "CB-A", "thumb": thumb_kind("CB-A"), "note": "범용 · 공개 자료 적음", "industry": False}
        if sheet_type == "IM":
            code = "IM-B" if usage == "exec_onepager" else "IM-A"
            return {"sheet": names["IM"], "code": code, "thumb": thumb_kind(code), "note": "범용", "industry": False}
        ind = industry_code(s, sheet_type)
        if ind and sheet_type in ("MS+TR", "CB", "US"):
            nm = names["MS+TR"] if sheet_type == "MS+TR" else (names["US_industry"] if sheet_type == "US" else names["CB"])
            return {"sheet": nm, "code": ind, "thumb": thumb_kind(ind), "note": "업종 레이아웃", "industry": True}
        st = "MS" if sheet_type == "MS+TR" else sheet_type
        code = {"MS": "MS-B", "TR": "TR-B", "CB": "CB-C", "US": "US-A"}.get(st, "MS-B")
        return {"sheet": names.get(st, st), "code": code, "thumb": thumb_kind(code), "note": "범용", "industry": False}

    if usage == "quickwin":
        return []
    if usage == "exec_onepager":
        out.append(gen("IM"))
        if "market" in scope:
            out.append({"sheet": names["MS"], "code": "MS-A", "thumb": thumb_kind("MS-A"), "note": "범용 · 부록", "industry": False})
        if "competitor" in scope:
            out.append(gen("CP"))
        return out
    main = [a for a in scope]
    if usage == "standard":
        main = [a for a in ("market", "customer", "competitor") if a in scope]
        if mix and "user" in scope:
            main = [a for a in ("market", "customer", "user") if a in scope]
        if len(main) < 3 and "user" in scope:
            main.append("user")
        main = [a for a in rules.AREAS if a in main]
    for a in main:
        out.append(gen("MS+TR" if a == "market" else TYPE_OF_AREA[a]))
    if usage == "solution":
        out.append(gen("IM"))
    return out


# ── MI3L 후보 · 선택지 ───────────────────────────────────
EXPLAIN = {
    "CP-B": "공급사마다 두 축의 값이 필요하고, 빈자리를 보이려면 5곳 이상이 좋아요",
    "CP-C": "공급사별 점유율과 연도별 추이 자료가 필요해요",
    "CP-A": "공급사 2~5곳과 비교 기준이 있으면 돼요",
    "MS-B": "연도별 시장 규모가 3개년 이상 필요하고, 6개년이면 가장 좋아요",
    "MS-A": "시장 수치 지표가 3개 이상 필요해요",
    "MS-C": "전체 규모와 노릴 몫(확장 목표) 자료가 필요해요",
    "MS-D": "세그먼트별 규모와 성장률이 3개 이상 필요해요",
    "MS-E": "성장 동인이 2개 이상 필요해요",
    "TR-A": "시점이 있는 트렌드가 3개 이상 필요해요",
    "TR-B": "트렌드 1~3개와 고객 시사점이 필요해요",
    "TR-C": "트렌드가 5개 이상 필요해요",
    "US-B": "여정 단계가 4개 이상 필요해요",
    "US-C": "사용자 구성 비율 자료가 필요해요",
    "CB-B": "IR · 전략 문서가 필요해요",
    "CB-D": "내부 · 외부 요인이 각각 2개 이상 필요해요",
}
SEARCHABLE = {"CP-B": "suppliers", "CP-A": "suppliers", "MS-B": "size_years", "MI-XX-A": "size_years", "MS-A": "metrics", "TR-C": "trends",
              "TR-A": "trends_dated"}


def predicted_metrics(code: str, m: dict[str, float]) -> dict[str, float] | None:
    """선택지 A — 모자란 데이터를 더 찾았다고 가정한 지표(예 CP-B 공급사 3 → 6)."""
    key = SEARCHABLE.get(code if not code.startswith("MI-") else "MI-XX-" + code.split("-")[-1])
    if not key:
        return None
    p = dict(m)
    if key == "suppliers":
        target = max(5, int(m["suppliers"]) * 2) if code == "CP-B" else max(2, int(m["suppliers"]))
        add = target - int(m["suppliers"])
        if add <= 0:
            return None
        p["suppliers"] = float(target)
        p["two_axis"] = float(target)
    elif key == "size_years":
        if m["size_years"] >= 6:
            return None
        p["size_years"] = 6.0
        p["verified_ratio"] = max(m["verified_ratio"], 0.5)
    elif key == "metrics":
        p["metrics"] = max(4.0, m["metrics"])
    elif key == "trends":
        p["trends"] = max(5.0, m["trends"])
    elif key == "trends_dated":
        p["trends_dated"] = max(3.0, m["trends_dated"])
    return p


def option_texts(sheet: dict[str, Any], requested: str, m: dict[str, float], segment: str | None) -> dict[str, Any]:
    cur = sheet["template_code"]
    req_fit, req_needs = fit(requested, m)
    cur_fit, _ = fit(cur, m)
    pm = predicted_metrics(requested, m)
    pred_fit = fit(requested, pm)[0] if pm else -1
    req_name = template(requested)["name"]
    cur_name = template(cur)["name"]
    n_sup = int(m["suppliers"])
    options: list[dict[str, Any]] = []
    eta = int(config.routing().get("time", {}).get("layout_s", 40))
    if pm and pred_fit > max(req_fit, -1):
        if requested.startswith("CP-"):
            target = int(pm["suppliers"])
            product = config.segment(segment).get("product", "") if segment else ""
            title = f"공급사 {target - n_sup}곳 더 찾아 {target}곳으로 → {requested}"
            desc = f"사례 DB · 공개 자료에서 {product + ' ' if product else ''}공급사 추가 · 적합도 {max(req_fit, 0)}% → {pred_fit}%"
        else:
            title = f"모자란 데이터를 더 찾아 → {requested}"
            desc = f"공개 자료에서 {data_summary_need(requested)} 추가 · 적합도 {max(req_fit, 0)}% → {pred_fit}%"
        options.append({"key": "A", "title": title, "desc": desc, "predicted_fit": pred_fit, "eta_s": eta, "template": requested})
    if req_fit >= 0 and requested != cur:
        if requested.startswith("CP-"):
            title = f"{n_sup}곳 그대로 {requested}"
            desc = f"구도는 보이지만 빈자리 메시지는 약해요 · 적합도 {req_fit}%" if requested == "CP-B" else f"지금 데이터로 바꿔요 · 적합도 {req_fit}%"
        else:
            title = f"지금 데이터로 {requested}"
            desc = f"지금 데이터로 바꿔요 · 적합도 {req_fit}%"
        options.append({"key": "B", "title": title, "desc": desc, "predicted_fit": req_fit, "template": requested})
    summary = data_summary(sheet["sheet_type"], m, segment)
    options.append({"key": "C", "title": f"{cur_name} {cur} 유지", "desc": f"{summary} 그대로 · 적합도 {max(cur_fit, 0)}%",
                    "predicted_fit": cur_fit, "template": cur})
    rec = "A" if any(o["key"] == "A" and o["predicted_fit"] >= int(config.th("fit_ok", 85)) for o in options) else "C"
    for o in options:
        o["recommended"] = o["key"] == rec
    # 해석 문장
    need = EXPLAIN.get(requested if not requested.startswith("MI-") else "MS-B", "필요한 데이터가 있어야 해요")
    if requested.startswith("CP-"):
        now_txt = f"{n_sup}곳"
    else:
        missing = [n["need"] for n in req_needs if not n["ok"]]
        now_txt = missing[0] if missing else data_summary(sheet["sheet_type"], m, segment)
    explanation = f"{req_name}({requested}){rules.josa(req_name + ')', '은', '는')} {need}. 지금은 {now_txt}{'이라' if rules.has_batchim(now_txt) else '라'} 이렇게 할 수 있어요."
    return {"options": options, "explanation": explanation}


def data_summary_need(code: str) -> str:
    return {"MS-B": "연도별 시장 규모", "MS-A": "시장 수치 지표", "TR-C": "트렌드", "TR-A": "시점 있는 트렌드"}.get(code, "필요한 데이터")


def candidates(sheet: dict[str, Any], m: dict[str, float], segment: str | None, requested: str | None) -> list[dict[str, Any]]:
    st = sheet["sheet_type"]
    codes = []
    ind = industry_code(segment, st) if st in ("MS+TR", "MS", "TR", "CB", "US") else None
    if ind:
        codes.append(ind)
    codes += band("MS+TR" if st in ("MS+TR",) else st)
    out = []
    for c in codes:
        f, needs = fit(c, m)
        tag = "사용 중" if c == sheet["template_code"] else ("요청" if c == requested else ("고를 수 없음" if f < 0 else ""))
        out.append({"code": c, "name": template(c)["name"], "thumb_kind": thumb_kind(c), "tag": tag, "needs": needs, "fit": f,
                    "fit_label": f"적합 {f}%" if f >= 0 else (template(c).get("unlock") or "고를 수 없음")})
    return out
