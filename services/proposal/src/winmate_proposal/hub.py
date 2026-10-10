"""Storyboard 허브에서 시작(2026-10-10) — 새 콘텐츠 흐름(docs/scenarios/11-content-flow.md §6)의 flow.json 을 제안서 넘김 스냅숏으로.

허브 Storyboard(`SB-nn`)는 연결 자료 하나(feature=storyboard, ref_id=SB-nn)로 붙는다. `stages.<콘텐츠>` 실제 값을 섹션 항목
(`target_section` 이 달린 반입 항목)과 문맥 재료(고객 · 요구사항 · 공간 · 제품 · 솔루션)로 바꿔 두면, 나머지 — 시트 구성 · 섹션 초안 ·
사실 검사 · 생성 · 내보내기 — 는 기존 반입(handoff) 경로를 그대로 탄다. 이전 Storyboard(`sb_…`)의 `…/proposal-handoff` 는 handoff.py 그대로.

stage → 섹션(유형별 「넣을 곳」, 표 `STAGE_TARGETS`)
  rq  → 고객 정보(고객사 · 의사결정자 · 프로젝트명) + 요구사항(R1…) — 섹션 초안의 요구사항 재료
  dss → 공간별 제품(공간 · 제품 · 수량 문자열, 모르는 수량은 [확인 필요]) · 솔루션 제안(SXI) · Solution형은 공간별 가치 시나리오
  mi  → Market Intelligence(담은 정보만, 출처 종류 · 이름 · 날짜 · URL, 수치 확인 표시는 [수치 확정 필요]로 남김)
  ca  → Why Samsung(경쟁 비교 CM · 삼성 강점 ST, 경쟁사는 익명 라벨 + 실명 표)
  vp  → Value Props(가치 메시지 · 고객 니즈 · 공간 · 연결 요구) — Key message(+ 받쳐 줄 메시지)가 있으면 가치 제안 시트 머리
  sp  → 제품 스펙(모델 · 항목 · 값 · 경고)
  sc  → 솔루션 제안(SXS · OP) · Solution형은 공간별 가치 시나리오(SS · VM)
근거 없는 값은 만들지 않는다 — 비어 있으면 항목을 만들지 않고 섹션은 「새로 작성」으로 남는다.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.flow import get_flow, push_stage

from . import clients, defs

log = logging.getLogger("winmate.proposal.hub")

HUB_ID_RE = re.compile(r"^SB-\d+$")
ORDER = ("rq", "dss", "mi", "ca", "vp", "sp", "sc")
# 허브 짧은 이름(SB1 진행 칸 · 요약본 머리와 같은 말) · 콘텐츠 이름
SHORT = {"rq": "요구사항", "dss": "DSS", "km": "Key message", "mi": "MI", "ca": "경쟁사", "vp": "VP", "sp": "Spec", "sc": "시나리오"}
NAME = {"rq": "고객 요구사항", "dss": "DSS", "km": "Key message", "mi": "Market Intelligence", "ca": "경쟁사 분석", "vp": "Value Proposition",
        "sp": "Spec 시트", "sc": "공간 시나리오"}
# 기존 작업 기능(사이드바 · 추천 유형 has 규칙)과 짝
STAGE_FEATURE = {"rq": "requirements", "mi": "mi", "ca": "competitor", "vp": "vp", "sp": "spec", "sc": "scenario"}
# stage → 유형별 섹션(「넣을 곳」) — km = Storyboard Key message(전략 수립)
STAGE_TARGETS: dict[str, dict[str, list[str]]] = {
    "rq": {"standard": [], "quickwin": [], "solution": []},
    "dss": {"standard": ["spaceProducts", "solution"], "quickwin": ["spaceProducts", "solution"], "solution": ["spaceScenario"]},
    "km": {"standard": ["vp"], "quickwin": ["vp"], "solution": ["vp"]},
    "mi": {"standard": ["mi"], "quickwin": [], "solution": ["bigMi"]},
    "ca": {"standard": ["why"], "quickwin": [], "solution": ["why"]},
    "vp": {"standard": ["vp"], "quickwin": ["vp"], "solution": ["vp"]},
    "sp": {"standard": ["spec"], "quickwin": ["spec"], "solution": []},
    "sc": {"standard": ["solution"], "quickwin": ["solution"], "solution": ["spaceScenario"]},
}
# PR1L 「연결하면 채워지는 것」 — stage → (섹션, 채움 상태)
STAGE_FILL: dict[str, list[tuple[str, str]]] = {
    "dss": [("spaceProducts", "full"), ("solution", "partial"), ("spaceScenario", "partial")],
    "km": [("vp", "partial")],
    "mi": [("mi", "full"), ("bigMi", "full")],
    "ca": [("why", "full")],
    "vp": [("vp", "full")],
    "sp": [("spec", "full")],
    "sc": [("solution", "partial"), ("spaceScenario", "full")],
}
MI_GROUP_ROLE = {"market": "MS", "시장": "MS", "customer": "CB", "고객": "CB", "user": "US", "사용자": "US"}
MI_ROLE_TITLE = {"MS": "시장 규모 · 성장", "CB": "고객사 비즈니스", "US": "사용자 분석", "TR": "산업 트렌드"}
DIM_LABEL = {"spec": "스펙", "price": "가격", "cases": "유관 사례", "esg": "ESG", "brand": "브랜드 평판"}
VERDICT = {"ours-better": "삼성 우위", "oursbetter": "삼성 우위", "better": "삼성 우위", "similar": "비슷", "ours-worse": "삼성 열위",
           "oursworse": "삼성 열위", "worse": "삼성 열위", "no-data": "[확인 필요]", "nodata": "[확인 필요]", "none": "[확인 필요]"}
VERDICT_MARK = {"삼성 우위": "full", "비슷": "half", "삼성 열위": "none"}
CHECK = "[확인 필요]"
NUM_CHECK = "[수치 확정 필요]"


# ── 판별 ───────────────────────────────────────────────────
def is_hub_id(ref: Any) -> bool:
    return isinstance(ref, str) and bool(HUB_ID_RE.match(ref.strip()))


def is_hub_link(ln: dict[str, Any]) -> bool:
    return (ln.get("feature") or "") == "storyboard" and is_hub_id(ln.get("ref_id"))


def space_key(name: str) -> str:
    """plan._space_key 와 같은 규칙(공간 이름 → 키)."""
    return re.sub(r"[^0-9A-Za-z가-힣]+", "_", name).strip("_").lower() or "space"


def _s(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, bool):
        return ""
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, dict):
        return _s(v.get("text") or v.get("name") or v.get("label") or v.get("title"))
    return str(v)


def _type(ptype: str | None) -> str:
    return ptype if ptype in defs.TYPES else "standard"


def stage_keys(flow: dict[str, Any]) -> list[str]:
    """허브에 저장된 콘텐츠(+ Key message 가 있으면 km)."""
    st = flow.get("stages") or {}
    keys = [k for k in ORDER if st.get(k)]
    if _s((flow.get("key_message") or {}).get("text")):
        after = "dss" if "dss" in keys else "rq" if "rq" in keys else None
        keys.insert(keys.index(after) + 1 if after else 0, "km")
    return keys


def targets(stage: str, ptype: str | None) -> list[str]:
    return list((STAGE_TARGETS.get(stage) or {}).get(_type(ptype)) or [])


def target_label(stage: str, ptype: str | None) -> str:
    if stage == "rq":
        return "고객 정보"
    keys = targets(stage, ptype)
    return " · ".join(defs.SECTIONS[k]["short"] for k in keys) if keys else "이 유형엔 없음"


def sections_for(snap: dict[str, Any] | None, ptype: str | None) -> list[str]:
    """허브 연결 자료가 들어가는 섹션(유형 순서) — 스냅숏의 stage 목록으로."""
    stages = list(((snap or {}).get("stages") or {}).keys())
    if not stages:
        return list((defs.WORK_TARGETS.get("storyboard") or {}).get(_type(ptype)) or [])
    want = {k for st in stages for k in targets(st, ptype)}
    return [k for k in defs.TYPES[_type(ptype)]["sections"] if k in want]


def stage_refs_for(snap: dict[str, Any] | None, section_key: str, ptype: str | None) -> list[str]:
    """섹션 칩 이름에 쓸 stage 코드(MI-01 · DSS-01 …)."""
    out = []
    for k, s in ((snap or {}).get("stages") or {}).items():
        if section_key in targets(k, ptype):
            out.append(s.get("ref") or SHORT.get(k, k))
    return out


# ── flow.json → 스냅숏 ─────────────────────────────────────
def _product(p: Any) -> dict[str, Any] | None:
    if isinstance(p, str):
        return {"name": p, "model": p, "qty": CHECK, "qty_confirm": True, "kind": "product"} if p.strip() else None
    if not isinstance(p, dict):
        return None
    name = _s(p.get("name") or p.get("label"))
    if not name:
        return None
    qty = p.get("qty")
    unknown = qty in (None, "") or bool(p.get("qtyStatus"))
    return {"name": name, "model": _s(p.get("model_code")) or name, "model_code": _s(p.get("model_code")) or None, "ref": p.get("ref"),
            "kind": p.get("kind") or "product", "qty": CHECK if unknown else (qty if isinstance(qty, str) else _s(qty)), "qty_confirm": unknown}


def _anon_names(comps: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    """경쟁사 익명 라벨(경쟁사 A · B …)과 실명 표 {익명: 실명} — 실명은 제안서에 넣지 않는다(V5)."""
    labels: list[str] = []
    real: dict[str, str] = {}
    for i, c in enumerate(comps):
        cid = _s(c.get("id"))
        letter = cid if re.fullmatch(r"[A-Z]", cid or "") else chr(ord("A") + i)
        anon = f"경쟁사 {letter}"
        labels.append(anon)
        name = _s(c.get("name"))
        if name and name != anon and not name.startswith("경쟁사 "):
            real[anon] = name
    return labels, real


def _verdict_cell(vals: list[tuple[str, str]]) -> tuple[str, str | None]:
    """한 경쟁사 · 한 항목의 비교 쌍 판정들 → (칸 글, 표시)."""
    def lab(v: str) -> str:
        k = v.lower().replace("_", "-")
        return VERDICT.get(k) or VERDICT.get(k.replace("-", "")) or ""
    labs = [(lab(v), n) for v, n in vals]
    labs = [(lb, n) for lb, n in labs if lb]
    if not labs:
        return "—", None
    counts: dict[str, int] = {}
    for lb, _n in labs:
        counts[lb] = counts.get(lb, 0) + 1
    top = max(counts, key=lambda k: (counts[k], k == "비슷"))
    if len(counts) == 1:
        note = next((n for lb, n in labs if n and n not in ("비슷", "자료 없음")), "")
        text = f"{top} · {note}" if note and top != CHECK else top
    else:
        text = " · ".join(f"{k.replace('삼성 ', '')} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1]))
    return text, VERDICT_MARK.get(top)


def _scenario_scenes(scs: list[dict[str, Any]], space: str = "") -> list[dict[str, Any]]:
    out = []
    for sc in scs:
        steps = [_s(x.get("text") if isinstance(x, dict) else x) for x in sc.get("steps") or []]
        steps = [x for x in steps if x]
        out.append({"time": _s(sc.get("user")) or space, "title": _s(sc.get("title")), "story": " → ".join(steps),
                    "products": [_s(x) for x in sc.get("products") or [] if _s(x)]})
    return out


def snapshot(flow: dict[str, Any], proposal_type: str | None = None) -> dict[str, Any]:
    """허브 FlowDoc(GET /v1/flows/{id}) → handoff.fetch 스냅숏(kind=flow). 순수 함수(호출 없음)."""
    ptype = _type(proposal_type)
    secs = set(defs.TYPES[ptype]["sections"])
    st = flow.get("stages") or {}
    cards = flow.get("cards") or {}
    sb_id = flow.get("id") or ""
    rq = st.get("rq") or {}
    dss = st.get("dss") or {}
    km = flow.get("key_message") or {}
    km_text = _s(km.get("text"))
    pillars = [{"text": _s(x.get("text") if isinstance(x, dict) else x),
                "evidence": [_s(e) for e in (x.get("evidence") if isinstance(x, dict) else []) or [] if _s(e)]}
               for x in km.get("pillars") or []]
    pillars = [x for x in pillars if x["text"]]
    items: list[dict[str, Any]] = []

    def src(stage: str) -> dict[str, Any]:
        s = st.get(stage) or {}
        ref = s.get("ref") or SHORT[stage]
        return {"kind": "storyboard", "ref": f"{sb_id}:{stage}", "label": f"{ref} · {NAME[stage]}", "stage": stage, "stage_ref": s.get("ref")}

    def add(stage: str, section: str, role: str, key: str, label: str, content: dict[str, Any], *, repeat: dict[str, Any] | None = None,
            sol: str | None = None, hint: str | None = None, sources: list[dict[str, Any]] | None = None, title: str | None = None) -> None:
        if section not in secs:
            return
        s = st.get(stage) or {}
        items.append({"key": f"{stage}:{key}", "label": label, "from_label": f"{SHORT.get(stage, stage)} · {s.get('ref') or ''}".strip(" ·"),
                      "sheet_role": role, "sheet_title": title or defs.ROLES.get(role, {}).get("name", role), "solution_code": sol,
                      "repeat_key": repeat, "template_hint": {"code": hint, "name": ""} if hint else None, "status": "ok",
                      "status_label": "그대로 들어가요", "include_default": True, "target_section": section, "content": content,
                      "sources": [src(stage) if stage in st else {"kind": "storyboard", "ref": f"{sb_id}:km", "label": "Key message"},
                                  *(sources or [])], "stage": stage})

    # ── rq: 고객 · 요구사항 ──
    keymen = [_s(k.get("role") or k.get("name")) for k in rq.get("keymen") or [] if isinstance(k, dict)]
    target = _s(rq.get("target") or flow.get("target"))
    dms = list(dict.fromkeys(x for x in [target, *keymen] if x))
    ind_value = _s((dss.get("industry") or {}).get("value") if isinstance(dss.get("industry"), dict) else dss.get("industry"))
    customer = {"name": _s(rq.get("customer") or flow.get("customer")) or None, "decision_makers": ", ".join(dms) or None,
                "industry_code": defs.industry_code_of(ind_value) if ind_value else None}
    rq_items = []
    for i, r in enumerate(rq.get("requirements") or []):
        text = _s(r.get("text") if isinstance(r, dict) else r)
        if not text:
            continue
        rid = _s(r.get("id")) if isinstance(r, dict) else ""
        code = rid if re.fullmatch(r"R\d+", rid or "") else f"R{i + 1}"
        rq_items.append({"id": rid or code, "code": code, "rq_code": rid or None, "text": text, "short": text,
                         "status": (r.get("status") if isinstance(r, dict) else None) or "ok", "source": "storyboard"})

    # ── dss: 공간 · 제품 · 솔루션 ──
    spaces: list[dict[str, Any]] = []
    for sp in dss.get("spaces") or []:
        name = _s(sp.get("name") if isinstance(sp, dict) else sp)
        if not name:
            continue
        prods = [x for x in (_product(p) for p in (sp.get("products") if isinstance(sp, dict) else []) or []) if x]
        spaces.append({"key": space_key(name), "name": name, "products": prods, "scenes": [], "source": "storyboard"})
    solutions: list[dict[str, Any]] = []
    for so in dss.get("solutions") or []:
        name = _s(so.get("name") if isinstance(so, dict) else so)
        if not name:
            continue
        ref = so.get("ref") if isinstance(so, dict) else None
        code = defs.solution_code_of(str(ref).split(":")[-1] if ref else None, name)
        solutions.append({"id": ref or name, "name": name, "code": code, "why": _s(so.get("why")) if isinstance(so, dict) else "",
                          "links": [_s(x) for x in (so.get("links") if isinstance(so, dict) else []) or [] if _s(x)]})
    products = [{**p, "space_key": s["key"]} for s in spaces for p in s["products"]]
    if spaces:
        rows = [[s["name"], p["name"], p["qty"]] for s in spaces for p in s["products"]]
        if rows:
            add("dss", "spaceProducts", "SM", "map", f"공간 {len(spaces)} · 제품 {len(rows)}",
                {"title": f"공간 {len(spaces)}곳 · 어디에 무엇을", "table": {"columns": ["공간", "제품", "수량"], "rows": rows}})
    for so in solutions:
        if so["code"] and (so["why"] or so["links"]):
            c: dict[str, Any] = {"products": so["links"]}
            if so["why"]:
                c["message"] = so["why"]
            add("dss", "solution", "SXI", f"sol:{so['code']}", f"{so['name']} · 함께 쓰는 제품 {len(so['links'])}", c, sol=so["code"])

    # ── sc: 공간 시나리오 ──
    sc = st.get("sc") or {}
    sc_spaces = [x for x in sc.get("spaces") or [] if isinstance(x, dict) and _s(x.get("name"))]
    all_scs: list[tuple[str, dict[str, Any]]] = [(_s(x["name"]), s) for x in sc_spaces for s in x.get("scenarios") or [] if isinstance(s, dict)]
    for x in sc_spaces:
        name = _s(x["name"])
        key = space_key(name)
        scenes = _scenario_scenes([s for s in x.get("scenarios") or [] if isinstance(s, dict)], name)
        sol_names = {so["name"] for so in solutions}
        sp_prods = [y for y in (_product(p) for p in x.get("products") or []) if y and y["name"] not in sol_names and y.get("kind") != "solution"]
        found = next((s for s in spaces if s["key"] == key), None)
        if found is None:
            found = {"key": key, "name": name, "products": [], "scenes": [], "source": "storyboard"}
            spaces.append(found)
        found["scenes"] = scenes
        for p in sp_prods:
            if not any(q["name"] == p["name"] for q in found["products"]):
                found["products"].append(p)
                products.append({**p, "space_key": key})
    if all_scs:
        for so in solutions:
            if not so["code"]:
                continue
            mine = [(sp, s) for sp, s in all_scs if so["name"] in [_s(v) for v in s.get("products") or []]
                    or any(so["name"] == _s(v.get("product") if isinstance(v, dict) else "") for v in s.get("steps") or [])]
            if mine:
                scenes = [{**sn, "time": sn["time"] or sp} for sp, s in mine for sn in _scenario_scenes([s], sp)]
                add("sc", "solution", "SXS", f"sol:{so['code']}", f"{so['name']} · 시나리오 {len(mine)}", {"scenes": scenes}, sol=so["code"],
                    title=f"{so['name']} · 공간 시나리오")
        ops = [sn for sp, s in all_scs for sn in _scenario_scenes([s], sp)][:6]
        add("sc", "solution", "OP", "ops", f"시나리오 {len(all_scs)}", {"title": "공간마다 이렇게 쓰여요", "scenes": ops})
        # Solution형: 공간 × 솔루션 맵 · 공간별 시나리오
        sol_list = [so["name"] for so in solutions]
        if sol_list:
            vm_rows = []
            for s in spaces:
                cells = []
                for so in solutions:
                    used = [_s(x.get("title")) for x in s["scenes"] if so["name"] in (x.get("products") or [])]
                    linked = any(s["name"] in ln for ln in so["links"])
                    cells.append(" · ".join(u for u in used if u)[:40] or ("연결" if linked else "—"))
                vm_rows.append([s["name"], *cells])
            add("sc", "spaceScenario", "VM", "matrix", f"공간 {len(spaces)} × 솔루션 {len(sol_list)}",
                {"table": {"columns": ["공간", *sol_list], "rows": vm_rows}}, title="공간 × 솔루션 맵")
    for s in spaces:
        if "spaceScenario" not in secs:
            break
        rk = {"kind": "space", "ref": s["key"], "label": s["name"]}
        linked_sols = [so["name"] for so in solutions if any(s["name"] in ln for ln in so["links"])]
        if s["scenes"]:
            add("sc", "spaceScenario", "SS", f"space:{s['key']}", s["name"],
                {"title": s["name"], "scenes": s["scenes"], "products": [p["name"] for p in s["products"]], "lines": linked_sols}, repeat=rk,
                title=s["name"])
        elif s["products"] and "dss" in st:
            add("dss", "spaceScenario", "SS", f"space:{s['key']}", s["name"],
                {"title": s["name"], "products": [{"name": p["name"], "qty": p["qty"]} for p in s["products"]], "lines": linked_sols},
                repeat=rk, title=s["name"])

    # ── mi: 담은 정보 ──
    mi = st.get("mi") or {}
    mi_sec = "bigMi" if ptype == "solution" else "mi"
    kept = [x for x in mi.get("items") or [] if isinstance(x, dict) and x.get("kept", True) is not False and _s(x.get("summary"))]
    by_role: dict[str, list[dict[str, Any]]] = {}
    for x in kept:
        by_role.setdefault(MI_GROUP_ROLE.get(_s(x.get("group")).lower(), MI_GROUP_ROLE.get(_s(x.get("group")), "TR")), []).append(x)
    for role in ("MS", "CB", "US", "TR"):
        xs = by_role.get(role) or []
        if not xs:
            continue
        ins, foot, srcs = [], [], []
        for x in xs:
            so = x.get("source") or {}
            text = _s(x.get("summary")) + (f" {NUM_CHECK}" if x.get("numberCheck") else "")
            tag = " · ".join(v for v in (_s(so.get("type")), _s(so.get("date"))) if v)
            # 카드 머리(title)는 어느 템플릿에서나 보이므로 찾은 내용을 머리에, 출처 이름은 본문 · 종류 · 날짜는 꼬리표로
            ins.append({"title": text, "text": _s(so.get("name")), "tag": tag})
            foot.append("출처: " + " · ".join(v for v in (_s(so.get("name")), _s(so.get("type")), _s(so.get("date"))) if v))
            srcs.append({"kind": "web", "ref": x.get("id"), "label": _s(so.get("name")) or "출처", "url": so.get("url"), "type": so.get("type"),
                         "date": so.get("date"), "number_check": bool(x.get("numberCheck"))})
        add("mi", mi_sec, role, role.lower(), f"{MI_ROLE_TITLE[role]} · 정보 {len(xs)}",
            {"title": MI_ROLE_TITLE[role], "insights": ins, "footnotes": list(dict.fromkeys(foot))[:6]}, sources=srcs)

    # ── ca: 경쟁 비교 · 삼성 강점 ──
    ca = st.get("ca") or {}
    comps = [c for c in ca.get("competitors") or [] if isinstance(c, dict)]
    if comps:
        anon, real = _anon_names(comps)
        dims = [d for d in DIM_LABEL if any(d in (m.get("dims") or {}) for c in comps for m in c.get("matches") or [] if isinstance(m, dict))]
        cells, marks = [], []
        for d in dims:
            row, mrow = [], []
            for c in comps:
                vals = [(_s(((m.get("dims") or {}).get(d) or {}).get("verdict")), _s(((m.get("dims") or {}).get(d) or {}).get("note")))
                        for m in c.get("matches") or [] if isinstance(m, dict) and (m.get("dims") or {}).get(d)]
                t, mk = _verdict_cell(vals)
                row.append(t)
                mrow.append(mk)
            cells.append(row)
            marks.append(mrow)
        lines = []
        for a, c in zip(anon, comps):
            if c.get("pros"):
                lines.append(f"{a} 강점: " + " · ".join(_s(x) for x in c["pros"] if _s(x)))
            if c.get("cons"):
                lines.append(f"{a} 약점: " + " · ".join(_s(x) for x in c["cons"] if _s(x)))
        n_pairs = sum(len(c.get("matches") or []) for c in comps)
        if dims:
            add("ca", "why", "CM", "compare", f"경쟁사 {len(comps)} · 비교 쌍 {n_pairs}",
                {"title": "경쟁사보다 나은 점", "criteria": [DIM_LABEL[d] for d in dims], "columns": anon, "cells": cells, "verdict_marks": marks,
                 "lines": lines, "real_names": real}, hint="CM-A")
        strengths: list[dict[str, Any]] = []
        for c in comps:
            for cl in c.get("claims") or []:
                if not isinstance(cl, dict) or not _s(cl.get("text")):
                    continue
                if any(x["note"] == _s(cl.get("text")) for x in strengths):
                    continue
                strengths.append({"title": _s(cl.get("axis")) or "강점", "note": _s(cl.get("text"))})
        if not strengths:
            for c in comps:
                for m in c.get("matches") or []:
                    for d, v in ((m.get("dims") or {}) if isinstance(m, dict) else {}).items():
                        note = _s((v or {}).get("note"))
                        if VERDICT.get(_s((v or {}).get("verdict")).lower()) == "삼성 우위" and note and not any(x["note"] == note for x in strengths):
                            strengths.append({"title": DIM_LABEL.get(d, d), "note": note})
        if strengths:
            add("ca", "why", "ST", "strengths", f"삼성 강점 {min(4, len(strengths))}",
                {"title": "삼성이어야 하는 이유", "strengths": strengths[:4], "real_names": real})
        if "mi" in st:
            wk = ("hq", "size", "industry", "mainBusiness", "b2bOffice")
            wl = {"hq": "본사", "size": "규모", "industry": "업종", "mainBusiness": "주력 사업", "b2bOffice": "B2B 오피스"}
            have = [k for k in wk if any(_s((c.get("wiki") or {}).get(k)) for c in comps)]
            if have:
                add("ca", mi_sec, "CP", "landscape", f"경쟁사 {len(comps)} 개요",
                    {"title": "시장 판도", "criteria": [wl[k] for k in have], "columns": anon,
                     "cells": [[_s((c.get("wiki") or {}).get(k)) or CHECK for c in comps] for k in have], "real_names": real})

    # ── vp · Key message: 가치 제안 · 고객 과제 ──
    vp = st.get("vp") or {}
    values = [(it, v) for it in vp.get("items") or [] if isinstance(it, dict) for v in it.get("values") or [] if isinstance(v, dict) and _s(v.get("message"))]
    if pillars or values or km_text:
        if pillars:
            pts = [{"title": p["text"], "text": " · ".join(p["evidence"])} for p in pillars]
        else:
            pts = [{"title": _s(v.get("message")), "text": _s((v.get("need") or {}).get("text")) if isinstance(v.get("need"), dict) else "",
                    "tag": _s(v.get("space")) or _s(it.get("name"))} for it, v in values][:4]
        c = {"title": km_text or "우리는 이런 가치를 준다", "pillars": pts}
        if km_text:
            c["key_message"] = km_text
        add("vp" if values else "km", "vp", "VP", "values", f"가치 {len(pts)}" + (" · Key message" if km_text else ""), c, hint=None)
    needs = []
    for it, v in values:
        need = v.get("need") if isinstance(v.get("need"), dict) else None
        t = _s((need or {}).get("text"))
        if t and not any(n["text"] == t for n in needs):
            needs.append({"title": _s(v.get("space")) or _s(it.get("name")), "text": t, "tag": _s(v.get("req"))})
    if needs:
        add("vp", "vp", "CH", "needs", f"고객 니즈 {min(4, len(needs))}", {"title": "고객이 바라는 것", "pillars": needs[:4]})

    # ── sp: 스펙 비교 · 제품 상세 ──
    sp = st.get("sp") or {}
    models = [m for m in sp.get("models") or [] if isinstance(m, dict) and _s(m.get("name"))]
    cols = [c for c in sp.get("columns") or [] if isinstance(c, dict) and c.get("key")]
    warns = [f"{_s(w.get('model'))}: {_s(w.get('text')) or _s(w.get('kind'))}" for w in sp.get("warnings") or [] if isinstance(w, dict)]
    if models and cols:
        shown = models[:5]
        add("sp", "spec", "SC", "compare", f"제품 {len(models)} · 항목 {len(cols)}",
            {"title": f"제품 {len(shown)}종 사양 비교", "columns": [_s(m["name"]) for m in shown],
             "rows": [{"label": _s(c.get("label")) or c["key"], "cells": [_s((m.get("specs") or {}).get(c["key"])) or CHECK for m in shown]} for c in cols],
             "footnotes": [f"확인: {w}" for w in warns][:4]})
        for m in models:
            ref = _s(m.get("model_code")) or _s(m["name"])
            add("sp", "spec", "SD", f"model:{ref}", _s(m["name"]),
                {"title": f"{_s(m['name'])} 상세 사양", "columns": [_s(m["name"])],
                 "rows": [{"label": _s(c.get("label")) or c["key"], "cells": [_s((m.get("specs") or {}).get(c["key"])) or CHECK]} for c in cols]},
                repeat={"kind": "product", "ref": ref, "label": ref}, title=f"제품 상세 · {ref}")
    sp_products = []
    sp_refs = [_s(m.get("model_code")) or _s(m["name"]) for m in models]
    seen_main: set[str] = set()
    for p in products:   # Spec 시트에 담은 모델 = 주력 제품(제품 상세 SD 시트) — 같은 모델은 한 번만
        if p["model"] in sp_refs and p["model"] not in seen_main and len(seen_main) < 3:
            p["main"] = True
            seen_main.add(p["model"])
    for m in models:
        nm = _s(m["name"])
        if any(p["name"] == nm for p in products):
            continue
        sk = space_key(_s(m.get("space"))) if _s(m.get("space")) else None
        qty = m.get("qty")
        sp_products.append({"name": nm, "model": _s(m.get("model_code")) or nm, "model_code": _s(m.get("model_code")) or None, "ref": m.get("ref"),
                            "qty": CHECK if qty in (None, "") else (qty if isinstance(qty, str) else _s(qty)), "qty_confirm": qty in (None, ""),
                            "space_key": sk if any(s["key"] == sk for s in spaces) else None, "source": "spec",
                            "main": len(seen_main) < 3 and (_s(m.get("model_code")) or nm) not in seen_main})
        if sp_products[-1]["main"]:
            seen_main.add(sp_products[-1]["model"])

    stages: dict[str, dict[str, Any]] = {}
    cells = {c.get("key"): c for c in flow.get("cells") or [] if isinstance(c, dict)}
    for k in stage_keys(flow):
        if k == "km":
            stages["km"] = {"ref": None, "ver": None, "title": km_text, "line": " · ".join(p["text"] for p in pillars)[:80],
                            "route": f"/storyboard/flow/{sb_id}"}
            continue
        s = st.get(k) or {}
        card = cards.get(k) or {}
        stages[k] = {"ref": s.get("ref"), "ver": s.get("ver"), "title": _s(card.get("title")) or NAME[k], "line": _s(card.get("line")),
                     "route": (cells.get(k) or {}).get("route")}
    return {
        "kind": "flow",
        "source": {"feature": "storyboard", "ref_id": sb_id, "title": flow.get("name") or sb_id,
                   # 콘텐츠 판(ppt 칸 제외) = 허브 색인 meta.version — 제안서 ppt 칸 기록으로는 「업데이트됨」이 뜨지 않는다
                   "version": flow.get("content_rev") or flow.get("version") or 0,
                   # updated_at 을 비워 둔다 — workspace 색인 시각과 허브 시각은 형식이 달라 「업데이트됨」 오판정이 난다(허브 버전으로 비교)
                   "updated_at": "", "flow_updated_at": flow.get("updated_at"), "route": f"/storyboard/flow/{sb_id}"},
        "target": {"proposal_type": ptype},
        "customer": customer, "project_name": _s(rq.get("title")) or None, "rq_ref": None, "rq_items": rq_items,
        "key_message": {"text": km_text, "pillars": pillars} if km_text else None,
        "key_messages": [{"place_label": f"가치 {i + 1}", "text": p["text"]} for i, p in enumerate(pillars)],
        "stages": stages, "items": items, "facts": [], "assets": [], "live_link": False,
        "spaces": spaces[:5], "products": products + sp_products, "solutions": solutions,
        "industry_value": ind_value or None,
    }


async def fetch(sb_id: str, proposal_type: str | None) -> dict[str, Any] | None:
    """스냅숏 전체(섹션으로 거르지 않는다 — 반입 · 섹션 재료가 항목의 target_section 으로 거른다)."""
    flow = await get_flow(sb_id)
    if not flow:
        return None
    return snapshot(flow, proposal_type)


# ── 기존 작업(PR1L) 목록 ───────────────────────────────────
async def list_flows(q: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    res = await clients.call("storyboard", "GET", "/v1/flows", params={"limit": limit, **({"q": q} if q else {})}, quiet=True)
    return [x for x in (res or {}).get("items") or [] if is_hub_id(x.get("id"))]


def contents(snap: dict[str, Any], ptype: str | None) -> list[dict[str, Any]]:
    """PR1L Storyboard 줄 아래 「연결된 콘텐츠」 — stage 마다 넣을 곳."""
    return [{"key": k, "label": SHORT[k], "tool_label": "전략 수립" if k == "km" else NAME[k], "ref": s.get("ref"), "ver": s.get("ver"),
             "title": s.get("title") or NAME[k], "line": s.get("line") or "", "target_sections": targets(k, ptype),
             "target_label": target_label(k, ptype), "route": s.get("route")}
            for k, s in (snap.get("stages") or {}).items()]


def fill_states(stage_map: dict[str, dict[str, Any]]) -> dict[str, tuple[str, str]]:
    """stage 목록 → {섹션: (채움 상태, 출처 글자)} — 상태가 센 쪽(채움 > 일부)."""
    rank = {"new": 0, "partial": 1, "full": 2}
    out: dict[str, tuple[str, str]] = {}
    for k, s in stage_map.items():
        for sec, state in STAGE_FILL.get(k, []):
            label = (s or {}).get("ref") or SHORT.get(k, k)
            if sec not in out or rank[state] > rank[out[sec][0]]:
                out[sec] = (state, label)
    return out


# ── 연결 뒤 ────────────────────────────────────────────────
async def on_linked(pid: str, ln: dict[str, Any]) -> None:
    """허브 Storyboard 를 연결(linked)했을 때 — 제안서에 Storyboard · Key message 를 남기고(표지 부제), 허브 ppt 칸에 이 제안서를 기록."""
    from . import core
    snap = ln.get("handoff") or {}
    if not is_hub_link(ln) or snap.get("kind") != "flow":
        return
    info = {"sb_id": ln["ref_id"], "title": (snap.get("source") or {}).get("title") or ln["ref_id"],
            "key_message": snap.get("key_message"), "stages": list((snap.get("stages") or {}).keys())}
    await core.mutate(pid, lambda x: x.update({"hub": info}), bump=False)
    await record_ppt(ln["ref_id"], await core.load(pid))


# ── 허브 「제안서」 칸(ppt) ─────────────────────────────────
async def _next_code() -> str:
    from . import repo

    def bump(x: dict[str, Any]) -> int:
        x["n"] = int(x.get("n") or 0) + 1
        return x["n"]
    if await repo.aget("meta", "hub_seq") is None:
        try:
            await repo.aput("meta", "hub_seq", {"id": "hub_seq", "n": 0})
        except Exception as exc:  # noqa: BLE001 — 동시에 만들었으면 그대로
            log.debug("hub_seq 만들기 겹침: %s", exc)
    _, n = await repo.amutate("meta", "hub_seq", bump)
    return f"PR-{n:02d}"


async def record_ppt(sb_id: str, p: dict[str, Any]) -> dict[str, Any] | None:
    """허브 Storyboard 의 「PPT 제작 · B2B 제안서」 칸에 이 제안서를 남긴다(stages.ppt). 허브가 안 되면 None(제안서는 계속)."""
    from . import core
    code = p.get("hub_ref") or await _next_code()
    if not p.get("hub_ref"):
        await core.mutate(p["id"], lambda x: x.update({"hub_ref": x.get("hub_ref") or code}), bump=False)
    tname = core.type_name(p.get("type")) or ""
    title = core.title_display(p)
    cust = (p.get("customer") or {}).get("name") or ""
    secs = core.type_sections(p.get("type")) if p.get("type") else []
    value = {"proposal_id": p["id"], "title": title, "customer": cust or None, "type": p.get("type"), "type_name": tname or None,
             "status": p.get("status") or "draft", "sections": secs, "route": f"{defs.ROUTE_BASE}/{p['id']}"}
    line = " · ".join(x for x in (code, tname or "유형 미정", f"섹션 {len(secs)}" if secs else "") if x)
    card = {"title": title, "facts": [["고객사", cust or "—"], ["유형", tname or "미정"], ["상태", defs.STATUS_LABEL.get(p.get("status") or "draft", "작성 중")]],
            "groups": [], "line": line}
    try:
        return await push_stage(sb_id, "ppt", ref=code, ver=max(1, int(p.get("saved_version") or 0)), res_id=p["id"], title=title, value=value,
                                md=f"- {title} · {tname or '유형 미정'}", card=card)
    except Exception as exc:  # noqa: BLE001
        log.warning("허브 %s ppt 칸 반영 실패: %s", sb_id, exc)
        return None


async def clear_ppt(p: dict[str, Any]) -> None:
    """제안서를 지우면 허브 「PPT 제작 · B2B 제안서」 칸을 비운다(그 칸이 이 제안서를 가리킬 때만 — `?ref=`). 실패해도 지우기는 계속."""
    sb = (p.get("hub") or {}).get("sb_id")
    ref = p.get("hub_ref")
    if not sb or not ref:
        return
    await clients.call("storyboard", "DELETE", f"/v1/flows/{sb}/stages/ppt", params={"ref": ref}, quiet=True)
