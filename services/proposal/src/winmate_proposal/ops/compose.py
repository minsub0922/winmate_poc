"""§6.4 유형(PR2) · 시트 구성(PR3) · 업종 레이아웃(PR3I)."""
from __future__ import annotations

from typing import Any

from .. import clients, core, defs, industry, plan, repo, templates
from .. import models as M
from ..errors import type_required


# ── 유형 ───────────────────────────────────────────────────
def customer_line(p: dict[str, Any]) -> str:
    c = p.get("customer") or {}
    code = c.get("industry_code")
    group = defs.INDUSTRY_GROUP_LABEL.get(code or "", defs.INDUSTRIES.get(code or "", {}).get("name", "")) if code else ""
    return " · ".join(x for x in (c.get("name"), p.get("title"), group, c.get("scale_text")) if x)


async def recommended_type(p: dict[str, Any]) -> dict[str, str]:
    ctx = p.get("ctx") or await plan.refresh_context(p["id"])
    rec = await industry.recommend_type(p, ctx)
    return rec


async def type_options(pid: str) -> M.TypeOptions:
    p = await core.load(pid)
    rec = await recommended_type(p)
    rname = defs.TYPES[rec["type"]]["name"]
    types = []
    for t, d in defs.TYPES.items():
        secs = [M.TypeSectionChip(no=i + 1, key=k, label=defs.SECTIONS[k]["name"], optional=k in d["optional"]) for i, k in enumerate(d["sections"])]
        types.append(M.TypeOption(type=t, name=d["name"], desc=d["desc"], rec=t == rec["type"], selected=p.get("type") == t, sections=secs,
                                  section_count=len(secs), footnote=f"섹션 {len(secs)} · 넣을 시트는 다음 단계에서 골라요",
                                  route=core.route(pid, "compose")))
    intro = ("어떤 형태의 제안서로 만들까요? 유형마다 섹션 구성이 다르고, 점선으로 표시된 섹션과 섹션마다 넣을 시트는 다음 단계에서 고릅니다. "
             f"{rec['reason']} {rname}를 추천합니다.")
    return M.TypeOptions(recommended=M.RecommendedType(type=rec["type"], name=rname, reason=rec["reason"]), customer_line=customer_line(p),
                         intro=intro, selected=p.get("type"), types=types)


async def set_type(pid: str, type_: str, *, source: str = "user", advance: bool = True) -> None:
    def fn(x: dict[str, Any]) -> None:
        x["type"] = type_
        x["type_source"] = source
        if advance:
            core.advance_stage(x, "compose")
        keys = core.type_sections(type_)
        if x.get("current_section_key") not in keys:
            x["current_section_key"] = keys[0] if keys else None
    await core.mutate(pid, fn)
    await plan.refresh_context(pid)
    await plan.ensure_sections(pid)
    await plan.sync_sheets(pid)


async def put_type(pid: str, body: M.TypePut) -> M.Proposal:
    await set_type(pid, body.type)
    await core.index(pid)
    return await core.proposal_view(pid)


# ── 시트 구성 ──────────────────────────────────────────────
def type_card(key: str, code: str, state: str, ctx: dict[str, Any], user_set: bool) -> M.CompType:
    repeat = plan.repeat_info(key, code, ctx)
    src = plan.src_label(key, code, ctx, state)
    if code in defs.SOLUTIONS:
        s = defs.SOLUTIONS[code]
        return M.CompType(code=code, name=s["name"], msg=s.get("desc") or s.get("I", ""), state=state,  # type: ignore[arg-type]
                          meta=f"전용 3장 · 소개 · 구성도 · 공간 시나리오 · {src}", src_label=src, template_count=3, dedicated=True, repeat=3,
                          user_set=user_set)
    r = defs.ROLES.get(code) or {}
    name = r.get("pr3_name") or r.get("name") or code
    msg = r.get("pr3_msg") or r.get("msg") or ""
    tc = defs.TEMPLATE_COUNT_PR3.get(code)
    nm = f"{name} ×{repeat}" if repeat > 1 and code in ("PI", "SS", "CD") else name
    return M.CompType(code=code, name=nm, msg=msg, state=state, meta=f"템플릿 {tc}종 · {src}" if tc else src, src_label=src,  # type: ignore[arg-type]
                      template_count=tc, repeat=repeat, user_set=user_set)


async def get_composition(pid: str, open_key: str | None = None) -> M.Composition:
    p = await core.load(pid)
    if not p.get("type"):
        raise type_required()
    ctx = p.get("ctx") or await plan.refresh_context(pid)
    type_ = p["type"]
    keys = core.type_sections(type_)
    secs = {s["key"]: s for s in await core.sections_of(pid)}
    if any(k not in secs for k in keys):
        await plan.ensure_sections(pid)
        await plan.sync_sheets(pid)
        secs = {s["key"]: s for s in await core.sections_of(pid)}
    sheets = await core.sheets_of(pid)
    rows = []
    total = 0
    n_enabled = 0
    open_key = open_key or defs.TYPES[type_]["open"]
    if open_key and open_key.isdigit():
        idx = int(open_key)
        open_key = keys[idx] if 0 <= idx < len(keys) else defs.TYPES[type_]["open"]
    for i, key in enumerate(keys):
        s = secs[key]
        comp = s.get("composition") or []
        enabled = bool(s.get("enabled", True))
        n = len([sh for sh in sheets if sh["section_key"] == key]) if enabled else 0
        total += n
        n_enabled += 1 if enabled else 0
        cards = [type_card(key, r["code"], r["state"], ctx, bool(r.get("user_set"))) for r in comp]
        chips = [M.CompChip(code=c.code, name=c.name.split(" ×")[0], repeat=c.repeat) for c in cards if c.state == "on"
                 and not (c.code == "SA" and len([x for x in comp if x["code"] in defs.SOLUTIONS and x["state"] == "on"]) < 2)]
        more = len([c for c in cards if c.state != "on"])
        opt = core.is_optional(type_, key)
        rows.append(M.CompSection(no=i + 1, no_label=f"{i + 1:02d}", key=key, name=defs.SECTIONS[key]["name"], optional=opt, enabled=enabled,
                                  tag="선택" if opt else "필수", switch_label=f"{defs.SECTIONS[key]['name']} 섹션 사용" if opt else None,
                                  chips=chips, more=more, more_label=f"+ {more}" if more else "", types=cards, sheet_count=n, open=key == open_key))
    tname = defs.TYPES[type_]["name"]
    nxt = await next_after_compose(p)
    return M.Composition(type=type_, type_name=tname, header_label=f"시트 구성 · {tname} · 섹션 {n_enabled} · 시트 {total} · 3 / 6",
                         intro=(f"{tname}에 넣을 시트를 고르세요. 시트마다 말하는 역할이 정해져 있고, 요구사항과 연결된 자료를 보고 "
                                "필요한 시트를 미리 골라 두었어요. 템플릿은 섹션 작성 때 내용에 맞춰 고릅니다."),
                         sections=rows, section_count=n_enabled, sheet_total=total, open_key=open_key, next=nxt)


async def put_composition(pid: str, body: M.CompositionPut) -> M.Composition:
    p = await core.load(pid)
    if not p.get("type"):
        raise type_required()
    touched: list[str] = []
    for sp in body.sections:
        secs = await repo.alist("sections", {"proposal_id": pid, "key": sp.key})
        if not secs:
            continue
        sec = secs[0]
        touched.append(sp.key)

        def fn(x: dict[str, Any], sp: M.CompSectionPut = sp) -> None:
            if sp.enabled is not None and x.get("optional"):
                x["enabled"] = sp.enabled
            comp = x.setdefault("composition", [])
            for t in sp.types:
                row = next((r for r in comp if r["code"] == t.code), None)
                if row is None:
                    comp.append({"code": t.code, "state": "on" if t.on else "off", "user_set": True})
                else:
                    row["state"] = "on" if t.on else "off"
                    row["user_set"] = True
            if any(t.code in defs.SOLUTIONS for t in sp.types):
                on = [r for r in comp if r["code"] in defs.SOLUTIONS and r["state"] == "on"]
                for r in comp:
                    if r["code"] == "SA" and not r.get("user_set"):
                        r["state"] = "on" if len(on) >= 2 else "off"
        await repo.amutate("sections", sec["id"], fn)
    await plan.sync_sheets(pid)
    await core.touch(pid)
    return await get_composition(pid, touched[0] if touched else None)


async def next_after_compose(p: dict[str, Any]) -> M.NextStep:
    pid = p["id"]
    il = p.get("industry_layout") or {}
    code = il.get("industry_code") or (il.get("detected") or {}).get("code") or (p.get("customer") or {}).get("industry_code")
    sheets = await core.sheets_of(pid)
    fam_roles = {"MS", "CB", "US", "VP", "EF", "SM", "VM", "SS", "OP"}
    has_family = any(sh.get("role") in fam_roles for sh in sheets)
    if not il.get("decided") and code and has_family:
        return M.NextStep(target="industry", route=core.route(pid, "industry"), label="섹션 작성 시작")
    first = await first_section(p)
    return M.NextStep(target="sections", route=core.section_route(pid, first), label="섹션 작성 시작")


async def first_section(p: dict[str, Any]) -> str:
    keys = core.type_sections(p.get("type"))
    secs = {s["key"]: s for s in await core.sections_of(p["id"])}
    for k in keys:
        if secs.get(k, {}).get("enabled", True):
            return k
    return keys[0] if keys else "mi"


async def start_sections(pid: str) -> M.StartSections:
    p = await core.load(pid)
    if not p.get("type"):
        raise type_required()
    nxt = await next_after_compose(p)
    if nxt.target == "industry":
        await core.mutate(pid, lambda x: core.advance_stage(x, "industry"))
    else:
        first = await first_section(p)

        def fn(x: dict[str, Any]) -> None:
            core.advance_stage(x, "sections")
            if not x.get("current_section_key") or x["current_section_key"] not in core.type_sections(x.get("type")):
                x["current_section_key"] = first
        await core.mutate(pid, fn)
    await core.index(pid)
    return M.StartSections(next=nxt, proposal=await core.proposal_view(pid))


# ── 업종 레이아웃(PR3I) ─────────────────────────────────────
MODE_LABEL = {"auto": "자동 감지", "check": "확인 권장", "ask": "선택 필요", "pinned": "직접 선택"}


def _req_label(rt: dict[str, Any], used: set[str]) -> str:
    if rt.get("label"):
        return rt["label"]
    for ex in rt.get("examples") or []:
        if ex not in used:
            used.add(ex)
            return ex
    return rt.get("code") or ""


async def industry_stats(code: str) -> M.IndustryStats:
    res = await clients.kb_get(f"/v1/segments/{code}/insights", {"top_req": 3, "top_items": 3})
    if not res:
        return M.IndustryStats()
    n = int(res.get("cases") or 0)
    used: set[str] = set()
    needs = [M.StatRow(label=_req_label(r, used), n=int(r.get("n") or 0), of=n) for r in (res.get("req_types") or [])[:3]]
    prods = [M.StatRow(label=x.get("name") or x.get("id"), n=int(x.get("n") or 0), of=n) for x in (res.get("products") or [])[:3]]
    sols = [M.StatRow(label=x.get("name") or x.get("id"), n=int(x.get("n") or 0), of=n) for x in (res.get("solutions") or [])[:3]]
    return M.IndustryStats(cases=n, needs=needs, products=prods, solutions=sols,
                           labels=[f"고객이 요구한 것 · 사례 {n}건 중", f"쓰인 제품 · 사례 {n}건 중", f"쓰인 솔루션 · 사례 {n}건 중"])


def _card(code: str, variant: str, fam: str, ind: str, state: str, cat: dict[str, Any]) -> M.FamilyCard:
    name, _thumb, desc = defs.IROLE[fam][variant]
    label = {"applied": "적용", "alt": "바꿔 쓰기", "add": "시트 추가 시"}[state]
    return M.FamilyCard(code=code, variant=variant, name=name, desc=f"{defs.INDUSTRIES[ind]['name']} 고객용 — {desc}",
                        thumb_url=core.thumb_url(code) or "", state=state, state_label=label,  # type: ignore[arg-type]
                        available=templates.available(cat, code))


async def industry_view(p: dict[str, Any], code: str | None = None) -> M.IndustryView:
    pid = p["id"]
    il = p.get("industry_layout") or {}
    det = il.get("detected") or {}
    chosen = code or il.get("industry_code") or det.get("code") or (p.get("customer") or {}).get("industry_code")
    mode = "pinned" if code else (det.get("mode") or ("pinned" if (p.get("customer") or {}).get("industry_user_set") else "auto"))
    if (p.get("customer") or {}).get("industry_user_set") and not code and chosen == (p.get("customer") or {}).get("industry_code"):
        mode = "pinned"
    evidence = ["직접 선택"] if mode == "pinned" else list(det.get("evidence") or [])
    cat = await clients.export_catalog()
    sheets = await core.sheets_of(pid)
    roles = {sh.get("role") for sh in sheets}
    type_ = p.get("type")
    families: list[M.IndustryFamily] = []
    applied = 0
    cards_state = il.get("cards") or {}
    fam_state = il.get("families") or {}
    if chosen and chosen in defs.INDUSTRIES:
        def on(f: str) -> bool:
            return fam_state.get(f, "on") == "on"
        # MI
        mi_cards = [_card(f"MI-{chosen}-A", "A", "MI", chosen, "applied" if "MS" in roles else "add", cat),
                    _card(f"MI-{chosen}-B", "B", "MI", chosen, "applied" if "CB" in roles else "add", cat),
                    _card(f"MI-{chosen}-C", "C", "MI", chosen, "applied" if "US" in roles else "add", cat)]
        mi_maps = [M.FamilyMap(text="시장 규모 · 성장 ← A", strong="MS" in roles), M.FamilyMap(text="고객사 비즈니스 ← B", strong="CB" in roles),
                   M.FamilyMap(text="경쟁 환경 · 기본 템플릿", strong=False)]
        # VP
        b_applied = cards_state.get(f"VP-{chosen}-B") == "applied"
        vp_cards = [_card(f"VP-{chosen}-A", "A", "VP", chosen, ("alt" if b_applied else "applied") if "VP" in roles else "add", cat),
                    _card(f"VP-{chosen}-B", "B", "VP", chosen, ("applied" if b_applied else "alt") if "VP" in roles else "add", cat),
                    _card(f"VP-{chosen}-C", "C", "VP", chosen, "applied" if "EF" in roles else "add", cat)]
        vp_maps = [M.FamilyMap(text="가치 제안 ← A", strong="VP" in roles and not b_applied), M.FamilyMap(text="B · 본사 · 점주 · 손님별", strong=b_applied),
                   M.FamilyMap(text="기대 효과 넣으면 ← C", strong="EF" in roles)]
        # SS
        if type_ == "solution":
            ss_cards = [_card(f"SS-{chosen}-A", "A", "SS", chosen, "applied" if "VM" in roles else "add", cat),
                        _card(f"SS-{chosen}-B", "B", "SS", chosen, "applied" if "SS" in roles else "add", cat),
                        _card(f"SS-{chosen}-C", "C", "SS", chosen, "applied" if "OP" in roles else "add", cat)]
            ss_maps = [M.FamilyMap(text="공간 × 솔루션 맵 ← A", strong="VM" in roles), M.FamilyMap(text="공간 시나리오 ← B", strong="SS" in roles),
                       M.FamilyMap(text="Solution형은 섹션 전체", strong=True)]
        else:
            ss_cards = [_card(f"SS-{chosen}-A", "A", "SS", chosen, "applied" if "SM" in roles else "add", cat),
                        _card(f"SS-{chosen}-B", "B", "SS", chosen, "add", cat), _card(f"SS-{chosen}-C", "C", "SS", chosen, "add", cat)]
            ss_maps = [M.FamilyMap(text="공간별 제품 · 공간 맵 ← A", strong="SM" in roles), M.FamilyMap(text="B · C는 시트 추가 시", strong=False),
                       M.FamilyMap(text="Solution형은 섹션 전체", strong=False)]
        for fam, cards, maps, rep_roles in (("MI", mi_cards, mi_maps, ("MS", "CB")), ("VP", vp_cards, vp_maps, ("VP",)),
                                            ("SS", ss_cards, ss_maps, ("VM", "SM"))):
            vis = [c for c in cards if c.available]
            avail = bool(vis)
            rep = next((sh for r in rep_roles for sh in sheets if sh.get("role") == r), None)
            families.append(M.IndustryFamily(role=fam, name=defs.FAMILY_NAME[fam], on=on(fam) and avail, available=avail,  # type: ignore[arg-type]
                                             switch_label=f"{defs.FAMILY_NAME[fam]} 업종 레이아웃 사용", maps=maps, cards=vis,
                                             pick_route=core.route(pid, "sections", rep["section_key"], "sheets", rep["id"], "template") if rep else None))
            if on(fam) and avail:
                for sh in sheets:
                    av = templates.applied_variant({**p, "industry_layout": {**il, "industry_code": chosen}}, sh.get("role") or "", type_)
                    if av and av[0] == fam and (sh.get("template") or {}).get("mode") != "pinned" \
                            and templates.available(cat, f"{fam}-{chosen}-{av[1]}"):
                        applied += 1
    stats = await industry_stats(chosen) if chosen else M.IndustryStats()
    label = defs.INDUSTRIES.get(chosen or "", {}).get("full", "") if chosen else ""
    tname = defs.TYPES.get(type_ or "", {}).get("name", "")
    ask = mode == "ask" and not code
    return M.IndustryView(
        detected=M.IndustryDetectedView(code=chosen, label=label, mode=mode, mode_label=MODE_LABEL.get(mode, ""), score=det.get("score"),  # type: ignore[arg-type]
                                        evidence=evidence, evidence_label="근거 · " + " · ".join(evidence) if evidence else ""),
        options=[M.IndustryOption(code=c, label=v["name"]) for c, v in defs.INDUSTRIES.items()], stats=stats, families=families,
        applied_count=applied, header_label=f"업종 레이아웃 추천 · {tname} · 시트 {applied}장에 적용 · 3 / 6",
        intro=(f"업종을 {label}로 판단했어요. 이 업종 도입사례 {stats.cases}건으로 만든 업종 레이아웃을 MI · Value Props · 공간 시나리오 시트에 "
               "먼저 추천할게요. 시트 구성은 그대로 두고 템플릿만 바꿔요.") if chosen else "고객 업종을 골라 주세요.",
        ask=ask, can_apply=bool(chosen) and not ask, decided=bool(il.get("decided")))


async def get_industry(pid: str, code: str | None = None) -> M.IndustryView:
    p = await core.load(pid)
    if not (p.get("industry_layout") or {}).get("detected"):
        from .proposals import redetect_industry
        await redetect_industry(pid)
        p = await core.load(pid)
    return await industry_view(p, code.upper() if code else None)


async def apply_industry_templates(pid: str) -> list[str]:
    """업종 레이아웃 결정에 맞춰 시트 템플릿을 다시 추천(고정 시트는 그대로). 바뀐 시트 id."""
    p = await core.load(pid)
    cat = await clients.export_catalog()
    changed = []
    prev = None
    for sh in await core.sheets_of(pid):
        rec = templates.recommend(sh, p, cat, prev_code=prev if sh.get("role") == "PI" else None,
                                  birdseye=bool(((p.get("ctx") or {}).get("has") or {}).get("birdseye")))
        holder: dict[str, Any] = {}

        def fn(x: dict[str, Any], rec: dict[str, Any] = rec) -> None:
            holder["c"] = templates.apply_recommendation(x, rec)
        await repo.amutate("sheets", sh["id"], fn)
        if holder.get("c"):
            changed.append(sh["id"])
        prev = rec.get("code")
    return changed


async def put_industry(pid: str, body: M.IndustryPut) -> M.IndustryView:
    p = await core.load(pid)
    code = (body.code or "").upper() or None
    if code and code not in defs.INDUSTRIES:
        code = defs.industry_code_of(code)

    def fn(x: dict[str, Any]) -> None:
        il = x.setdefault("industry_layout", core.default_industry_layout())
        if body.keep_default:
            il["families"] = {"MI": "off", "VP": "off", "SS": "off"}
            il["decided"] = True
            il["industry_code"] = il.get("industry_code") or code or (il.get("detected") or {}).get("code")
            return
        if code:
            il["industry_code"] = code
            det = il.get("detected") or {}
            if det.get("code") != code:
                il["detected"] = {**det, "code": code, "label": defs.INDUSTRIES[code]["full"], "mode": "pinned", "evidence": ["직접 선택"]}
            c = x.setdefault("customer", {})
            c["industry_code"] = code
            c["industry_label"] = defs.INDUSTRIES[code]["name"]
        elif not il.get("industry_code"):
            il["industry_code"] = (il.get("detected") or {}).get("code")
        fam = il.setdefault("families", {"MI": "on", "VP": "on", "SS": "on"})
        for k, v in body.families.items():
            if k in ("MI", "VP", "SS"):
                fam[k] = "on" if v else "off"
        cards = il.setdefault("cards", {})
        for k, v in body.cards.items():
            cards[k] = v
            if v == "applied" and k.endswith("-B") and k.startswith("VP-"):
                cards[k[:-1] + "A"] = "alt"
            if v == "applied" and k.endswith("-A") and k.startswith("VP-"):
                cards[k[:-1] + "B"] = "alt"
        il["decided"] = bool(body.decided)
        if body.decided:
            first = core.type_sections(x.get("type"))
            core.advance_stage(x, "sections")
            if not x.get("current_section_key") and first:
                x["current_section_key"] = first[0]
    await core.mutate(pid, fn)
    changed = await apply_industry_templates(pid)
    p = await core.load(pid)
    if changed:
        await repo.amutate("proposals", pid, lambda x: x["industry_layout"].update({"applied_codes": changed}))
    view = await industry_view(p)
    if body.keep_default:
        view.next = M.NextStep(target="compose", route=core.route(pid, "compose"), label="기본 템플릿 유지")
    else:
        first = await first_section(p)
        view.next = M.NextStep(target="sections", route=core.section_route(pid, first), label="적용 · 섹션 작성 시작")
    await core.index(pid)
    return view
