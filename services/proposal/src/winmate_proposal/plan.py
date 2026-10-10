"""시트 구성 — 문맥(공간 · 사례 · 제품 · 솔루션 · 요구사항) · 구성 기본값(부록 E) · 반복 수(§3.4) · 시트 동기화 · 번호.

문맥 `p["ctx"]` 는 연결 자료 · 요구사항 · kb 에서 결정적으로 계산한다(사용자가 더한 공간 · 사례는 `ctx_user` 에 남긴다).
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any

from winmate_common.ids import new_id

from . import clients, config, core, defs, hub, repo, templates

log = logging.getLogger("winmate.proposal.plan")

MAX_SPACES = 5


# ── 요구사항 ───────────────────────────────────────────────
async def requirements(p: dict[str, Any]) -> dict[str, Any]:
    """rq_ref → {rq_id, version, items: [{id, code, text, short}], customer_name, project_name}. 못 읽으면 빈 목록."""
    ref = p.get("rq_ref") or {}
    rq_id = ref.get("rq_id")
    if not rq_id:
        return {"items": []}
    ver = ref.get("version")
    path = f"/v1/requirements/{rq_id}/versions/{ver or 'latest'}"
    res = await clients.call("requirements", "GET", path, quiet=True)
    if not res:
        return {"rq_id": rq_id, "version": ver, "items": []}
    snap = res.get("snapshot") or {}
    items = []
    for i, it in enumerate(snap.get("items_flat") or []):
        items.append({"id": it.get("id") or f"R{i + 1}", "code": f"R{i + 1}", "rq_code": it.get("code"), "text": it.get("text") or "",
                      "short": it.get("short") or it.get("text") or "", "source": it.get("source")})
    return {"rq_id": rq_id, "version": res.get("version") or ver, "items": items, "customer_name": res.get("customer_name"),
            "project_name": res.get("project_name"), "final_audience": res.get("final_audience")}


def rq_text(ctx: dict[str, Any]) -> str:
    return " ".join(it.get("text") or "" for it in (ctx.get("rq") or {}).get("items") or [])


# ── 숫자 · 규모 ────────────────────────────────────────────
STORE_RE = re.compile(r"([0-9][0-9,]*)\s*(개|곳)?\s*(매장|점포|지점|곳)")


def store_count(p: dict[str, Any], ctx: dict[str, Any]) -> str | None:
    for text in ((p.get("customer") or {}).get("scale_text") or "", rq_text(ctx), p.get("title") or ""):
        m = STORE_RE.search(text or "")
        if m:
            return m.group(1).replace(",", "")
    return None


# ── 문맥 계산 ──────────────────────────────────────────────
def _space_key(name: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]+", "_", name).strip("_").lower() or "space"


async def compute_context(p: dict[str, Any]) -> dict[str, Any]:
    pid = p["id"]
    links = [ln for ln in await repo.alist("links", {"proposal_id": pid}) if ln.get("status", "linked") == "linked"]
    user = p.get("ctx_user") or {}
    rq = await requirements(p)
    # 허브 Storyboard(SB-nn) 연결 — 정의서(rq_ref)가 없으면 stages.rq 요구사항을 쓴다(R1…)
    hubs = [ln.get("handoff") or {} for ln in links if hub.is_hub_link(ln) and (ln.get("handoff") or {}).get("kind") == "flow"]
    if not rq.get("items"):
        for snap in hubs:
            if snap.get("rq_items"):
                rq = {**rq, "items": snap["rq_items"], "customer_name": (snap.get("customer") or {}).get("name"),
                      "project_name": snap.get("project_name"), "source": "storyboard", "sb_id": (snap.get("source") or {}).get("ref_id")}
                break
    ctx: dict[str, Any] = {"rq": rq}
    text = " ".join([p.get("title") or "", (p.get("customer") or {}).get("name") or "", rq_text(ctx)])

    # 공간
    spaces: list[dict[str, Any]] = []
    space_source = None
    for ln in links:
        snap = ln.get("handoff") or {}
        if ln.get("feature") in ("birdseye", "scenario") and snap.get("spaces"):
            for s in snap["spaces"]:
                name = s.get("name") or s.get("label")
                if not name:
                    continue
                key = s.get("key") or _space_key(name)
                if not any(x["key"] == key for x in spaces):
                    spaces.append({"key": key, "name": name, "source": ln["feature"], "products": s.get("products") or [],
                                   "scenes": s.get("scenes") or []})
            space_source = space_source or ln["feature"]
    for snap in hubs:   # 허브 stages.dss(+ sc) 공간 · 공간 제품
        for s in snap.get("spaces") or []:
            if s.get("name") and not any(x["key"] == s["key"] for x in spaces):
                spaces.append({"key": s["key"], "name": s["name"], "source": "storyboard", "products": s.get("products") or [],
                               "scenes": s.get("scenes") or []})
        if snap.get("spaces"):
            space_source = space_source or "storyboard"
    for s in user.get("spaces_added") or []:
        if not any(x["key"] == s["key"] for x in spaces):
            spaces.append({**s, "source": "user"})
    if not spaces:
        a1 = await clients.kb_query("A1", {"text": text[:2000]}) if text.strip() else None
        for ln in ((a1 or {}).get("result") or {}).get("links") or []:
            if ln.get("type") == "space_type" and not any(x["key"] == ln["id"] for x in spaces):
                spaces.append({"key": ln["id"], "name": ln.get("name") or ln.get("surface"), "source": "requirements", "products": []})
        space_source = "requirements" if spaces else None
    if not spaces:
        ind = templates.industry_code(p)
        kr = (defs.INDUSTRIES.get(ind or "") or {}).get("kr") or []
        if kr:
            b1 = await clients.kb_query("B1", {"vertical_id": kr[0]})
            for s in ((b1 or {}).get("result") or {}).get("space_sequence") or []:
                if s.get("space_type") in ("back_of_house",):
                    continue
                spaces.append({"key": s["space_type"], "name": s.get("name") or s["space_type"], "source": "kb", "products": []})
                if len(spaces) >= 3:
                    break
            space_source = "kb" if spaces else None
    removed = set(user.get("spaces_removed") or [])
    spaces = [s for s in spaces if s["key"] not in removed][:MAX_SPACES]
    ctx["spaces"] = spaces
    ctx["space_source"] = space_source

    # 제품
    products: list[dict[str, Any]] = []
    for ln in links:
        if ln.get("feature") == "kb_product":
            it = ln.get("item") or {}
            products.append({"name": ln.get("title") or it.get("label"), "model": it.get("model") or ln.get("title"),
                             "ref": ln.get("ref_id"), "space_key": ln.get("space_key"), "link_id": ln["id"], "qty": ln.get("qty")})
        if ln.get("feature") in ("birdseye", "spec"):
            for pr in (ln.get("handoff") or {}).get("products") or []:
                if not any(x.get("model") == pr.get("model") for x in products):
                    products.append({**pr, "source": ln["feature"]})
    for snap in hubs:   # DSS 공간 제품(공간 키) + Spec 시트에만 있는 모델
        for pr in snap.get("products") or []:
            if not any(x.get("model") == pr.get("model") and x.get("space_key") == pr.get("space_key") for x in products):
                products.append({**pr, "source": pr.get("source") or "storyboard"})
    for s in spaces:
        for pr in s.get("products") or []:
            if not any(x.get("model") == pr.get("model") and x.get("space_key") == s["key"] for x in products):
                products.append({**pr, "space_key": s["key"]})
    ctx["products"] = products

    # 사례
    cases: list[dict[str, Any]] = []
    for ln in links:
        if ln.get("feature") == "kb_case":
            cases.append({"id": ln["ref_id"], "title": ln.get("title"), "source": "link", "link_id": ln["id"]})
    old_ctx = p.get("ctx") or {}
    vert = ((defs.INDUSTRIES.get(templates.industry_code(p) or "") or {}).get("kr") or [None])[0]
    rec_cases = old_ctx.get("rec_cases")
    if rec_cases is None or old_ctx.get("rec_cases_vertical") != vert:
        rec_cases = await recommend_cases(p, text)
    ctx["rec_cases"] = rec_cases
    ctx["rec_cases_vertical"] = vert
    for c in rec_cases:
        if c["id"] not in {x["id"] for x in cases} and c["id"] not in set(user.get("cases_removed") or []):
            cases.insert(len([x for x in cases if x.get("source") == "kb"]), {**c, "source": "kb"})
    ctx["cases"] = cases

    # 솔루션
    sols: dict[str, dict[str, Any]] = {}
    for ln in links:
        if ln.get("feature") == "kb_solution":
            code = defs.solution_code_of(ln.get("ref_id"), ln.get("title"))
            if code:
                sols[code] = {"state": "on", "why": defs.SOLUTION_SRC_ON, "link_id": ln["id"]}
        if ln.get("feature") == "scenario" or (hub.is_hub_link(ln) and (ln.get("handoff") or {}).get("kind") == "flow"):
            for s in (ln.get("handoff") or {}).get("solutions") or []:
                code = s.get("code") or defs.solution_code_of(s.get("id"), s.get("name"))
                if code and code not in sols:
                    sols[code] = {"state": "on", "why": defs.SOLUTION_SRC_ON}
    low = text.lower()
    for code, s in defs.SOLUTIONS.items():
        if code in sols:
            continue
        hit = next((kw for kw in s.get("kw") or [] if kw.lower() in low), None)
        if hit:
            why = "요구사항에 매장 태블릿" if code == "KNX" else f"요구사항에 {hit}"
            sols[code] = {"state": "rec", "why": why}
    ctx["solutions"] = sols
    ctx["store_count"] = store_count(p, ctx)
    ctx["has"] = {f: any(ln.get("feature") == f for ln in links) for f in defs.WORK_FEATURES}
    for snap in hubs:   # 허브 콘텐츠도 그 기능 작업이 연결된 것으로(추천 유형 · 템플릿 신호)
        for k in snap.get("stages") or {}:
            if hub.STAGE_FEATURE.get(k):
                ctx["has"][hub.STAGE_FEATURE[k]] = True
    ctx["hub"] = [{"sb_id": (s.get("source") or {}).get("ref_id"), "stages": list((s.get("stages") or {}).keys())} for s in hubs]
    ctx["text_hash"] = hash(text)
    return ctx


async def recommend_cases(p: dict[str, Any], text: str, limit: int = 2) -> list[dict[str, Any]]:
    """유사 사례 상위 2건 — kb E3(업종 · 고객 유형 · 요구사항 → 근거 사례)를 먼저, 없으면 D1(업종 · 문장)."""
    ind = templates.industry_code(p)
    kr = (defs.INDUSTRIES.get(ind or "") or {}).get("kr") or []
    out: list[dict[str, Any]] = []
    rq = " ".join(x.get("text") or "" for x in ((p.get("ctx") or {}).get("rq") or {}).get("items") or [])
    e3_body: dict[str, Any] = {"text": (" ".join(x for x in (p.get("title") or "", rq) if x) or text or "매장 디지털 사이니지")[:1500]}
    if kr:
        e3_body["vertical"] = kr[0]
    cust = (p.get("customer") or {}).get("name")
    if cust:
        e3_body["customer"] = cust
    e3 = await clients.kb_query("E3", e3_body)
    for c in ((e3 or {}).get("result") or {}).get("cases") or []:
        if (c.get("score") or 0) < 0.4 or not c.get("id"):
            continue
        out.append({"id": c["id"], "title": c.get("title") or c["id"], "url": c.get("url"), "score": c.get("score"), "kpis": 0, "photos": True,
                    "why": " · ".join(c.get("reasons") or [])[:80]})
        if len(out) >= limit:
            return out
    body: dict[str, Any] = {"text": (text or (p.get("title") or ""))[:800] or "매장 디지털 사이니지", "limit": limit + 2}
    if kr:
        body["vertical"] = kr[0]
    res = await clients.kb_query("D1", body)
    for d in ((res or {}).get("result") or {}).get("deployments") or []:
        if d["id"] in {x["id"] for x in out}:
            continue
        out.append({"id": d["id"], "title": d.get("title") or d["id"], "url": d.get("url"), "score": d.get("score"),
                    "kpis": d.get("kpis_count") or 0, "photos": bool(d.get("has_photos"))})
        if len(out) >= limit:
            break
    return out


async def refresh_context(pid: str) -> dict[str, Any]:
    p = await core.load(pid)
    ctx = await compute_context(p)
    await repo.amutate("proposals", pid, lambda x: x.update({"ctx": ctx}))
    return ctx


# ── 구성 기본값(부록 E) ─────────────────────────────────────
CASE_SPLIT = re.compile(r"\s+[-–—]\s+")


def case_customer(title: str) -> str:
    """사례 제목 「말리커피 - 삼성 스마트 사이니지(홍보용)」 → 「말리커피」."""
    return CASE_SPLIT.split((title or "").strip(), maxsplit=1)[0].strip()


def case_short(title: str) -> str:
    t = re.split(r"[,(（]", case_customer(title), maxsplit=1)[0].strip()
    return t[:18] or "사례"


def default_composition(key: str, ctx: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if key == "solution":
        # 보드 순서: 넣음 솔루션 → 통합 구성도 → 추천 솔루션 → 안 넣음 솔루션 1 → 통합 운영 시나리오
        sols = ctx.get("solutions") or {}
        on = [c for c in sols if sols[c]["state"] == "on"]
        rec = [c for c in sols if sols[c]["state"] == "rec"]
        rows += [{"code": c, "state": "on", "user_set": False} for c in on]
        rows.append({"code": "SA", "state": "on" if len(on) >= 2 else "off", "user_set": False, "auto": True})
        rows += [{"code": c, "state": "rec", "user_set": False} for c in rec]
        for c in ("VXT", "MGI", "STP", "KNX"):
            if c not in on and c not in rec:
                rows.append({"code": c, "state": "off", "user_set": False})
                break
        rows.append({"code": "OP", "state": "off", "user_set": False})
        return rows
    rq = rq_text(ctx)
    for code, state, _rep, _n, _src in defs.COMPOSITION.get(key, []):
        st = state
        if code == "SV":
            st = "rec" if any(w in rq for w in ("유지보수", "지원", "장애", "A/S", "AS ", "응답")) else "off"
        rows.append({"code": code, "state": st, "user_set": False})
    return rows


def merge_composition(existing: list[dict[str, Any]] | None, default: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """사용자가 바꾼 상태(user_set)는 지키고 나머지는 기본값으로."""
    ex = {r["code"]: r for r in existing or []}
    out = []
    for r in default:
        e = ex.get(r["code"])
        if e and e.get("user_set"):
            out.append({**r, **({"items": e["items"]} if e.get("items") else {}), "state": e["state"], "user_set": True})
        else:
            out.append(r)
    for code, e in ex.items():   # 기본에 없던 것(반입으로 더한 역할 · 솔루션)
        if code not in {r["code"] for r in out} and e.get("user_set"):
            out.append(e)
    # 통합 구성도: 솔루션 2개 이상일 때 자동(사용자가 정하지 않았으면)
    on = [r for r in out if r["code"] in defs.SOLUTIONS and r["state"] == "on"]
    for r in out:
        if r["code"] == "SA" and not r.get("user_set") and any(x["code"] in defs.SOLUTIONS for x in out):
            r["state"] = "on" if len(on) >= 2 else "off"
    return out


# ── 섹션 만들기 · 유형 바꾸기 ───────────────────────────────
async def ensure_sections(pid: str) -> None:
    p = await core.load(pid)
    type_ = p.get("type")
    keys = core.type_sections(type_)
    ctx = p.get("ctx") or await refresh_context(pid)
    existing = {s["key"]: s for s in await repo.alist("sections", {"proposal_id": pid})}
    for i, key in enumerate(keys):
        s = existing.get(key)
        default = default_composition(key, ctx)
        if s is None:
            doc = {"id": new_id("sec"), "proposal_id": pid, "key": key, "order": i, "optional": core.is_optional(type_, key),
                   "enabled": True, "hidden": False, "status": "empty", "confirmed": False, "inferred": False,
                   "composition": default}
            await repo.aput("sections", doc["id"], doc)
        else:
            def fn(x: dict[str, Any], i: int = i, key: str = key, default: list[dict[str, Any]] = default) -> None:
                x["order"] = i
                x["optional"] = core.is_optional(type_, key)
                if not x["optional"]:
                    x["enabled"] = True
                x["hidden"] = False
                x["composition"] = merge_composition(x.get("composition"), default)
            await repo.amutate("sections", s["id"], fn)
    for key, s in existing.items():
        if key not in keys and not s.get("hidden"):
            await repo.amutate("sections", s["id"], lambda x: x.update({"hidden": True}))
    # mi ↔ bigMi: 같은 MI 시트를 옮겨 쓴다(§3.3 제안)
    pair = {"bigMi": "mi", "mi": "bigMi"}
    for key in keys:
        other = pair.get(key)
        if other and other not in keys:
            mine = await repo.alist("sheets", {"proposal_id": pid, "section_key": key})
            theirs = await repo.alist("sheets", {"proposal_id": pid, "section_key": other})
            if not [x for x in mine if x.get("status") != "excluded"] and theirs:
                for sh in theirs:
                    await repo.amutate("sheets", sh["id"], lambda x, key=key: x.update(
                        {"section_key": key, "ident": x.get("ident", "").replace(f"{other}|", f"{key}|", 1)}))


# ── 원하는 시트 목록 ───────────────────────────────────────
def sheet_title(role: str, *, sol: str | None = None, repeat: dict[str, Any] | None = None) -> str:
    if role in ("SXI", "SXD", "SXS") and sol:
        name = (defs.SOLUTIONS.get(sol) or {}).get("name", sol)
        return f"{name} · " + {"SXI": "소개", "SXD": "구성도", "SXS": "공간 시나리오"}[role]
    if role == "SA":
        return "통합 구성도"
    if role == "OP":
        return (repeat or {}).get("label") or "통합 운영 시나리오" if (repeat or {}).get("kind") == "rq" else "통합 운영 시나리오"
    if role == "VM":
        return "공간 × 솔루션 맵"
    if role in ("PI", "SS") and repeat:
        return repeat.get("label") or "공간"
    if role == "CD" and repeat:
        return f"사례 · {repeat.get('label') or '사례'}"
    if role == "SD":
        return f"제품 상세 · {repeat.get('label')}" if repeat and repeat.get("label") else "제품 상세"
    return defs.ROLES.get(role, {}).get("name", role)


def desired_sheets(key: str, comp: list[dict[str, Any]], ctx: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    spaces = ctx.get("spaces") or [{"key": "main", "name": "주요 공간"}]
    cases = ctx.get("cases") or []
    products = ctx.get("products") or []
    sol_on = [r["code"] for r in comp if r["code"] in defs.SOLUTIONS and r["state"] == "on"]

    def add(role: str, *, sol: str | None = None, repeat: dict[str, Any] | None = None, part: int = 0) -> None:
        ident = f"{key}|{role}|{sol or ''}|{(repeat or {}).get('ref') or ''}" + (f"#{part}" if part else "")
        out.append({"ident": ident, "role": role, "solution_code": sol, "repeat_key": repeat,
                    "title": sheet_title(role, sol=sol, repeat=repeat), "part": part})

    for r in comp:
        if r["state"] != "on":
            continue
        code = r["code"]
        if key == "solution" and code in defs.SOLUTIONS:
            for role in ("SXI", "SXD", "SXS"):
                add(role, sol=code)
            continue
        if code == "SA" and key == "solution":
            if len(sol_on) >= 2:
                add("SA")
            continue
        if (code == "PI" and key == "spaceProducts") or (code == "SS" and key == "spaceScenario"):
            for s in spaces:
                prods = [x for x in products if x.get("space_key") == s["key"]]
                rk = {"kind": "space", "ref": s["key"], "label": s["name"]}
                n = len(prods)
                if code == "PI" and n > 5:
                    parts = 2 if n <= 10 else math.ceil(n / 5)
                    for k in range(parts):
                        add("PI", repeat=rk, part=k)
                else:
                    add(code, repeat=rk)
            continue
        if code == "CD":
            for c in cases or []:
                add("CD", repeat={"kind": "case", "ref": c["id"], "label": case_short(c.get("title") or "")})
            # 기존 제안서 활용(개선) — 원본에서 이어 쓰는 사례(추천 목록에 없던 것)
            extra = [it for it in r.get("items") or [] if it.get("ref") and it["ref"] not in {c["id"] for c in cases or []}]
            for it in extra:
                add("CD", repeat=it)
            if not cases and not extra:
                add("CD", repeat={"kind": "case", "ref": "", "label": "사례"})
            continue
        if r.get("items"):
            # 기존 제안서 활용 · 요구사항 갭 시트(§7.10 apply) — 항목마다 1장
            for it in r["items"]:
                add(code, repeat=it)
            continue
        if code == "SD":
            mains = [x for x in products if x.get("main")] or products[:1]
            if mains:
                for pr in mains[:3]:
                    add("SD", repeat={"kind": "product", "ref": pr.get("model") or pr.get("name"), "label": pr.get("model") or pr.get("name")})
            else:
                add("SD")
            continue
        add(code)
    return out


def split_counts(n: int) -> list[int]:
    """6개 이상이면 2장(7 → 4 + 3, 앞이 많게), 11개 이상은 ⌈n/5⌉장 고르게."""
    if n <= 5:
        return [n]
    parts = 2 if n <= 10 else math.ceil(n / 5)
    base, extra = divmod(n, parts)
    return [base + (1 if i < extra else 0) for i in range(parts)]


async def sync_sheets(pid: str, *, sections: list[str] | None = None) -> dict[str, list[str]]:
    """구성 · 문맥에 맞춰 시트를 만들고 숨기고 되살린다. 내용은 지우지 않는다. → {created, excluded, restored}."""
    p = await core.load(pid)
    ctx = p.get("ctx") or {}
    type_ = p.get("type")
    keys = core.type_sections(type_)
    secs = {s["key"]: s for s in await core.sections_of(pid)}
    cat = await clients.export_catalog()
    created: list[str] = []
    excluded: list[str] = []
    restored: list[str] = []
    for key in keys:
        if sections and key not in sections:
            continue
        sec = secs.get(key)
        if sec is None:
            continue
        want = desired_sheets(key, sec.get("composition") or [], ctx) if sec.get("enabled", True) else []
        have = {sh.get("ident"): sh for sh in await repo.alist("sheets", {"proposal_id": pid, "section_key": key})}
        want_idents = set()
        prev_code = None
        products = ctx.get("products") or []
        for order, w in enumerate(want):
            want_idents.add(w["ident"])
            sh = have.get(w["ident"])
            if sh is None:
                pc = None
                if w["role"] == "PI":
                    sk = (w.get("repeat_key") or {}).get("ref")
                    prods = [x for x in products if x.get("space_key") == sk]
                    counts = split_counts(len(prods)) if prods else [1]
                    pc = max(1, min(5, counts[w.get("part", 0)] if w.get("part", 0) < len(counts) else counts[-1]))
                doc = {
                    "id": new_id("sht"), "proposal_id": pid, "section_key": key, "ident": w["ident"], "order": order,
                    "sheet_no": 0, "role": w["role"], "solution_code": w.get("solution_code"), "repeat_key": w.get("repeat_key"),
                    "title": w["title"], "template": {"code": None, "mode": "auto", "source": None, "product_count": pc},
                    "content": {}, "draft": {}, "signals": {"products_n": pc} if pc else {}, "sources": [], "status": "need",
                    "origin": "auto_generated" if key in ("cases",) else "user", "inferred": False, "evidence_note": None,
                    "reuse": None, "split_of": None, "edited_since_version": False, "render": None, "content_rev": 0,
                }
                if w.get("part"):
                    first = have.get(w["ident"].rsplit("#", 1)[0])
                    doc["split_of"] = (first or {}).get("id")
                rec = templates.recommend(doc, p, cat, prev_code=prev_code, birdseye=bool((ctx.get("has") or {}).get("birdseye")))
                templates.apply_recommendation(doc, rec)
                await repo.aput("sheets", doc["id"], doc)
                created.append(doc["id"])
                prev_code = doc["template"].get("code")
            else:
                def fn(x: dict[str, Any], order: int = order, w: dict[str, Any] = w) -> bool:
                    x["order"] = order
                    was = x.get("status") == "excluded" or x.get("hidden")
                    x["hidden"] = False
                    if x.get("status") == "excluded":
                        x["status"] = x.pop("status_before_exclude", None) or ("ready" if x.get("content") else "need")
                    if not x.get("title_user_set"):
                        x["title"] = w["title"]
                    return was
                _, was = await repo.amutate("sheets", sh["id"], fn)
                if was:
                    restored.append(sh["id"])
                prev_code = (sh.get("template") or {}).get("code")
        for ident, sh in have.items():
            if ident not in want_idents and sh.get("status") != "excluded":
                def ex(x: dict[str, Any]) -> None:
                    x["status_before_exclude"] = x.get("status")
                    x["status"] = "excluded"
                await repo.amutate("sheets", sh["id"], ex)
                excluded.append(sh["id"])
    await renumber(pid)
    return {"created": created, "excluded": excluded, "restored": restored}


async def renumber(pid: str) -> int:
    p = await core.load(pid)
    keys = core.type_sections(p.get("type"))
    secs = {s["key"]: s for s in await core.sections_of(pid)}
    n = 0
    for key in keys:
        sec = secs.get(key)
        shs = await repo.alist("sheets", {"proposal_id": pid, "section_key": key})
        active = sorted([s for s in shs if s.get("status") != "excluded" and not s.get("hidden")], key=lambda s: s.get("order") or 0)
        for sh in active:
            if sec is None or not sec.get("enabled", True):
                continue
            n += 1
            if sh.get("sheet_no") != n:
                await repo.amutate("sheets", sh["id"], lambda x, n=n: x.update({"sheet_no": n}))
    return n


def sheet_count_for(key: str, comp: list[dict[str, Any]], ctx: dict[str, Any]) -> int:
    return len(desired_sheets(key, comp, ctx))


def repeat_info(key: str, code: str, ctx: dict[str, Any]) -> int:
    if code == "PI" and key == "spaceProducts" or code == "SS" and key == "spaceScenario":
        return max(1, len(ctx.get("spaces") or []))
    if code == "CD":
        return max(1, len(ctx.get("cases") or []))
    if code in defs.SOLUTIONS:
        return 3
    if code == "SD":
        return max(1, len([x for x in ctx.get("products") or [] if x.get("main")] or (ctx.get("products") or [])[:1]))
    return 1


def src_label(key: str, code: str, ctx: dict[str, Any], state: str) -> str:
    if code in defs.SOLUTIONS:
        sols = ctx.get("solutions") or {}
        if state == "on":
            return defs.SOLUTION_SRC_ON
        if code in sols and sols[code]["state"] == "rec":
            return sols[code]["why"]
        return defs.SOLUTION_SRC_OFF
    for c, _st, _rep, _n, src in defs.COMPOSITION.get(key, []):
        if c == code:
            n = repeat_info(key, code, ctx)
            if code == "PI":
                src = src.replace("배치안 {n}곳", f"배치안 {n}곳" if ctx.get("space_source") == "birdseye" else f"{n}곳")
            return src.replace("{n}", str(n))
    return ""


async def store_count_value(pid: str) -> str | None:
    p = await core.load(pid)
    return (p.get("ctx") or {}).get("store_count")


def now() -> str:
    return config.now_iso()
