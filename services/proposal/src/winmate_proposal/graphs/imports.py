"""drop_extract · import_apply(§7.6) — 사이드바 작업 드롭(추출 확인을 거침) · 다른 기능에서 보내기(바로 적용)."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.jobs import JobContext

from .. import clients, config, core, defs, handoff, links as L, plan, repo, templates
from . import common as G
from . import section_fill as SF

log = logging.getLogger("winmate.proposal.imports")


def section_roles(sec: dict[str, Any], sheets: list[dict[str, Any]]) -> set[str]:
    roles = {s.get("role") for s in sheets}
    for r in sec.get("composition") or []:
        if r.get("state") == "on":
            roles.add(r["code"])
    if sec.get("key") == "solution":
        roles |= {"SXI", "SXD", "SXS"}
    return {r for r in roles if r}


async def extract_items(pid: str, imp: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """반입 스냅숏 항목 → 섹션 시트 역할에 매핑(in_section) · 들어갈 시트 · 템플릿.

    보내기(via=handoff)는 보내는 화면이 이미 고른 것이라, 항목의 역할이 이 섹션엔 없고 같은 제안서의 다른 섹션에 있으면 그 섹션으로
    보낸다(예: 조감도 BE6 「제품 수량표 SM-B」 → 공간별 제품 섹션, 통합). 항목마다 `section_key` 를 단다.
    """
    p = await core.load(pid)
    key = imp["section_key"]
    src = imp["source"]
    direct = imp.get("via") == "handoff"
    snap = await handoff.fetch(src.get("feature") or "", src.get("ref_id"), proposal_type=p.get("type"), section=key,
                               handoff_id=src.get("handoff_id"), version=src.get("version"))
    if snap is None:
        from winmate_common.errors import ApiError
        raise ApiError(502, "UPSTREAM_UNAVAILABLE", f"{defs.FEATURE_LABEL.get(src.get('feature') or '', '원 작업')}에서 내용을 가져오지 못했어요",
                       {"service": src.get("feature")})
    type_keys = core.type_sections(p.get("type"))
    cache: dict[str, tuple[list[dict[str, Any]], set[str]] | None] = {}

    async def info(k: str) -> tuple[list[dict[str, Any]], set[str]] | None:
        if k not in cache:
            try:
                sd = await core.section_doc(pid, k)
            except Exception:  # noqa: BLE001 — 그 섹션이 아직 없으면 보내지 않는다
                cache[k] = None
                return None
            if k != key and not sd.get("enabled", True):
                cache[k] = None
                return None
            shs = await core.sheets_of(pid, section_key=k)
            cache[k] = (shs, section_roles(sd, shs))
        return cache[k]

    cat = await clients.export_catalog()
    out = []
    used: set[str] = set()
    for it in snap.get("items") or []:
        role = (it.get("sheet_role") or "").upper()
        if src.get("feature") == "mi" and key == "why" and role == "CP":
            role = "CM"
        sk = key
        tgt = it.get("target_section")
        if tgt and tgt != key:
            if not direct or tgt not in type_keys or await info(tgt) is None:
                continue
            sk = tgt
        here = await info(sk)
        if here is None:
            continue
        sheets, roles = here
        if direct and role and role not in roles:
            for k2 in type_keys:
                if k2 == sk:
                    continue
                other = await info(k2)
                if other and role in other[1]:
                    sk, (sheets, roles) = k2, other
                    break
        in_sec = role in roles
        target = next((s for s in sheets if s.get("role") == role and s["id"] not in used), None) if in_sec else None
        if target:
            used.add(target["id"])
        hint = (it.get("template_hint") or {}).get("code")
        code = hint if hint and templates.available(cat, hint) else (target or {}).get("template", {}).get("code")
        tname = templates.local_name(code)[0] if code else ""
        if code and cat.get(code, {}).get("name"):
            tname = cat[code]["name"] if tname == code else tname
        rname = core.role_name(role)
        where = f"{defs.SECTIONS.get(sk, {}).get('name', '')} · " if sk != key else ""
        line = (f"→ {where}{(target or {}).get('title') or rname} · {tname} 템플릿" if in_sec else f"이 섹션엔 없는 시트 · {rname} 시트로 추가 가능")
        default = bool(it.get("include_default", True)) and in_sec
        out.append({"key": it.get("key") or role, "what": it.get("label") or it.get("sheet_title") or rname, "from_label": it.get("from_label"),
                    "sheet_role": role, "role_name": rname, "target_sheet_id": (target or {}).get("id"), "template_code": code,
                    "template_name": tname, "in_section": in_sec, "checked": default, "status": it.get("status"),
                    "status_label": it.get("status_label"), "line_label": line, "section_key": sk,
                    "include_default": bool(it.get("include_default", True)), "solution_code": it.get("solution_code")})
    return out, snap


async def apply(pid: str, imp_id: str, keys: list[str], *, job: str | None) -> dict[str, Any]:
    """고른 항목만 섹션에 — 연결 자료(include_keys) · 섹션에 없는 역할은 시트 추가 · 그 시트들만 다시 채움.

    항목의 `section_key` 가 반입 섹션과 다르면(보내기 · 다른 섹션 역할) 그 섹션에도 연결 · 시트 채우기를 한다.
    """
    imp = await repo.amust("imports", imp_id)
    key = imp["section_key"]
    src = dict(imp["source"])
    if imp.get("source_title") and not src.get("title"):
        src["title"] = imp["source_title"]
    items = imp.get("items") or []
    chosen = [it for it in items if it["key"] in keys] if keys else [it for it in items if it.get("checked")]
    by_sec: dict[str, list[dict[str, Any]]] = {}
    for it in chosen:
        by_sec.setdefault(it.get("section_key") or key, []).append(it)
    sec_keys = [key] + [k for k in by_sec if k != key]
    before: dict[str, dict[str, Any]] = {}
    for k in sec_keys:
        before.update({s["id"]: {f: s.get(f) for f in ("content", "draft", "template", "status", "content_rev", "sources", "signals")}
                       for s in await core.sheets_of(pid, section_key=k)})
    links: dict[str, dict[str, Any]] = {}
    for k in sec_keys:
        if k != key and not by_sec.get(k):
            continue
        ln = await L.add_link(pid, feature=src["feature"], ref_id=src["ref_id"], section_key=k, via=imp.get("via") or "drag_sidebar",
                              version=src.get("version"), handoff_id=src.get("handoff_id"), title=src.get("title"))
        await repo.amutate("links", ln["id"], lambda x, k=k: x.update({"include_keys": [it["key"] for it in by_sec.get(k) or []]}))
        links[k] = ln
    # 솔루션 전용 시트(SXI · SXD · SXS)를 골랐으면 그 솔루션을 솔루션 섹션 구성에 켠다(시나리오 → 표준 · 퀵윈 「솔루션 공간 시나리오」, 통합)
    sol_codes = sorted({it["solution_code"] for it in chosen if it.get("solution_code") and it.get("sheet_role") in ("SXI", "SXD", "SXS")})
    if sol_codes and "solution" in by_sec:
        ssec = await core.section_doc(pid, "solution")

        def sol_fn(s: dict[str, Any]) -> None:
            comp = s.get("composition") or []
            for code in sol_codes:
                row = next((r for r in comp if r["code"] == code), None)
                if row:
                    row["state"] = "on"
                    row["user_set"] = True
                elif code in defs.SOLUTIONS:
                    comp.insert(0, {"code": code, "state": "on", "user_set": True})
            on = [r for r in comp if r["code"] in defs.SOLUTIONS and r["state"] == "on"]
            for r in comp:
                if r["code"] == "SA" and not r.get("user_set"):
                    r["state"] = "on" if len(on) >= 2 else "off"
            s["composition"] = comp
            s["enabled"] = True
        await repo.amutate("sections", ssec["id"], sol_fn)
    # 섹션에 없는 역할을 골랐으면 구성에 더한다(AC-093)
    for k, its in by_sec.items():
        add_roles = sorted({it["sheet_role"] for it in its if not it.get("in_section")})
        if not add_roles:
            continue
        sec = await core.section_doc(pid, k)

        def fn(s: dict[str, Any], add_roles: list[str] = add_roles) -> None:
            comp = s.get("composition") or []
            for role in add_roles:
                row = next((r for r in comp if r["code"] == role), None)
                if row:
                    row["state"] = "on"
                    row["user_set"] = True
                else:
                    comp.append({"code": role, "state": "on", "user_set": True})
            s["composition"] = comp
        await repo.amutate("sections", sec["id"], fn)
    await plan.refresh_context(pid)
    sync = await plan.sync_sheets(pid, sections=sec_keys)
    affected: list[str] = []
    titles: list[str] = []
    res = None
    for k in sec_keys:
        its = by_sec.get(k) or []
        if k != key and not its:
            continue
        sheets = await core.sheets_of(pid, section_key=k)
        roles = {it["sheet_role"] for it in its}
        mine = [s["id"] for s in sheets if s.get("role") in roles
                and (not s.get("solution_code") or not sol_codes or s.get("solution_code") in sol_codes)]
        titles += [s.get("title") for s in sheets if s["id"] in mine]
        affected += mine
        if k == key or mine:
            r = await SF.fill(pid, k, mode="draft", sheet_ids=mine or None, origin="import", job=job)
            res = res or r
    p = await core.load(pid)
    await handoff.register_usage(src["feature"], src["ref_id"], proposal=p, label=defs.SECTIONS[key]["name"], version=src.get("version"))
    if src.get("handoff_id"):
        await handoff.ack(src["feature"], src["handoff_id"], result="applied", proposal=p, sheet_ids=affected, section_key=key)
    titles = titles[:3]
    note = (f"\"{titles[0]}\" 시트에 반영됨" if len(affected) == 1 else f"시트 {len(affected)}장에 반영됨") if affected else "반영할 시트가 없었어요"
    others = [defs.SECTIONS[k]["name"] for k in sec_keys if k != key and by_sec.get(k)]
    if others:
        note += f" · {' · '.join(others)} 섹션에도"
    change_ids = [c["id"] for c in await repo.alist("changes", {"proposal_id": pid}) if c.get("job_id") == job] if job else []
    main = links.get(key) or next(iter(links.values()), None)

    def done(x: dict[str, Any]) -> None:
        x.update({"status": "applied", "applied_keys": [it["key"] for it in chosen], "link_id": (main or {}).get("id"),
                  "link_ids": [ln["id"] for ln in links.values()], "affected_sheet_ids": affected,
                  "new_sheet_ids": sync.get("created") or [], "before": before, "change_ids": change_ids, "note": note,
                  "toast": f"{defs.FEATURE_SHORT.get(src['feature'], '')} 작업 반영됨 · {note}", "fill_job_id": job, "applied_iso": config.now_iso()})
    await repo.amutate("imports", imp_id, done)
    await core.index(pid)
    return {"import_id": imp_id, "affected_sheet_ids": affected, "fill": res}


async def handle_extract(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid, imp_id = pl["proposal_id"], pl["import_id"]

    async def extract(_s: dict[str, Any]) -> dict[str, Any]:
        imp = await repo.amust("imports", imp_id)
        items, snap = await extract_items(pid, imp)
        direct = imp.get("via") == "handoff"
        if direct:
            # 보내는 화면이 고른 키(include_keys)를 그대로. 키가 이 섹션 항목과 하나도 맞지 않으면(섹션을 제안서가 바꿨을 때 등)
            # · 키 없이 보냈으면 보내는 쪽 기본 선택(include_default — 섹션에 없는 역할은 apply 가 구성에 더한다, AC-093)
            inc = imp.get("include_keys")
            if inc is not None and not any(it["key"] in inc for it in items):
                inc = None
            # 제안서가 섹션을 바꿔 받은 보내기(요청 섹션이 그 유형에 없음)는 그 섹션에 이미 있는 역할만 — 낯선 시트를 더하지 않는다
            moved = bool(imp.get("requested_section")) and imp.get("requested_section") != imp.get("section_key")
            for it in items:
                if inc is not None:
                    it["checked"] = it["key"] in inc
                else:
                    it["checked"] = bool(it.get("include_default", it["checked"])) and (it["in_section"] or not moved)

        def fn(x: dict[str, Any]) -> None:
            x["items"] = items
            x["status"] = "applying" if direct else "pending_confirm"
            x["source_title"] = ((snap or {}).get("source") or {}).get("title") or x["source"].get("title")
            x["source_route"] = ((snap or {}).get("source") or {}).get("route")
        await repo.amutate("imports", imp_id, fn)
        if direct:
            keys = [it["key"] for it in items if it["checked"]]
            await apply(pid, imp_id, keys, job=ctx.job.id)
        return {"result": {"proposal_id": pid, "import_id": imp_id, "items": len(items), "applied": direct}}

    try:
        final = await G.run(ctx, G.single("extract", extract), {}, labels={"extract": "필요한 내용 뽑기"}, progress_map={"extract": 100})
    except BaseException as exc:
        await _fail(imp_id, exc)
        raise
    return (final or {}).get("result") or {}


async def handle_apply(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid, imp_id = pl["proposal_id"], pl["import_id"]

    async def node(_s: dict[str, Any]) -> dict[str, Any]:
        return {"result": await apply(pid, imp_id, pl.get("keys") or [], job=ctx.job.id)}
    try:
        final = await G.run(ctx, G.single("apply", node), {}, labels={"apply": "시트에 반영"}, progress_map={"apply": 100})
    except BaseException as exc:
        await _fail(imp_id, exc)
        raise
    return (final or {}).get("result") or {}


async def _fail(imp_id: str, exc: BaseException) -> None:
    err = {"code": getattr(exc, "code", None) or type(exc).__name__, "message": getattr(exc, "message", None) or str(exc)}
    try:
        await repo.amutate("imports", imp_id, lambda x: x.update({"status": "failed", "error": err}))
    except Exception:  # noqa: BLE001
        pass
