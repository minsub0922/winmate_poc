"""section_fill(§7.4) — 섹션 초안 · 수정 요청 · 추론(딸깍) · 반입 반영.

load → sources(연결 자료 반입 스냅숏 · kb) → draft(LLM `pr.section_draft`) → persist(V1 · V4 · V5 · V8 검사 → 값 토큰 · 확인 항목 →
템플릿 추천 → 칸 채우기 → 저장 · 변경 기록). 다른 그래프(딸깍 · 반입 · 생성)는 `fill()` 을 바로 부른다.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from winmate_common.jobs import JobContext

from .. import clients, config, content as C, core, defs, facts as F, inputs, plan, prompts, repo, templates, validate as V
from . import common as G

log = logging.getLogger("winmate.proposal.section_fill")

DRAFT_MODES = ("draft", "request", "infer", "reuse_improve", "reuse_borrow")
INFER_MODES = ("request", "infer", "reuse_improve", "reuse_borrow")


def sheet_key(sh: dict[str, Any]) -> str:
    """LLM 이 돌려줄 시트 키 — 역할(+ 솔루션 · 반복 대상 · 나눔 번호). mock 고정 응답이 역할로 맞출 수 있게 짧게."""
    role = sh.get("role") or ""
    rk = sh.get("repeat_key") or {}
    ident = sh.get("ident") or ""
    part = ident.rsplit("#", 1)[-1] if "#" in ident else ""
    if sh.get("solution_code"):
        return f"{role}:{sh['solution_code']}"
    if rk.get("ref"):
        return f"{role}:{rk['ref']}" + (f"#{part}" if part else "")
    return role


def material(body: dict[str, Any], limit: int = 1400) -> str:
    """LLM 에 줄 재료(이미지 · 신호 빼고 짧게)."""
    keep: dict[str, Any] = {}
    for k in ("title", "subtitle", "message", "customer", "solution_name"):
        if body.get(k):
            keep[k] = body[k]
    for k in ("points", "steps"):
        if body.get(k):
            keep[k] = [{kk: vv for kk, vv in x.items() if vv not in (None, "") and kk in ("title", "body", "kpi", "tag", "after", "when")}
                       for x in body[k] if isinstance(x, dict)][:6]
    if body.get("bullets"):
        keep["bullets"] = body["bullets"][:8]
    if body.get("kpis"):
        keep["kpis"] = body["kpis"][:6]
    if body.get("series"):
        se = body["series"]
        keep["series"] = {"name": se.get("name"), "unit": se.get("unit"), "points": list(zip(se.get("categories") or [], se.get("values") or []))}
    if body.get("table"):
        t = body["table"]
        keep["table"] = {"columns": t.get("columns"), "rows": [[r.get("label"), *[c.get("text") if isinstance(c, dict) else c for c in r.get("cells") or []]]
                                                               for r in (t.get("rows") or [])[:10]]}
    if body.get("products"):
        keep["products"] = [{k: v for k, v in x.items() if k in ("name", "model", "qty") and v not in (None, "")} for x in body["products"][:8]]
    if body.get("spaces"):
        keep["spaces"] = [x.get("name") for x in body["spaces"]]
    return G.dumps(keep, limit) if keep else "(재료 없음 — 요구사항 · 고객 정보로만 쓰고 수치는 자리표시)"


# ── 1. 준비 ────────────────────────────────────────────────
async def add_role(pid: str, key: str, role: str) -> None:
    """빠른 요청 「통합 운영 시나리오 추가」(OP) · 「사례 한 장으로 모으기」(CL → CD 끔)."""
    sec = await core.section_doc(pid, key)

    def fn(s: dict[str, Any]) -> None:
        comp = s.get("composition") or []
        found = False
        for r in comp:
            if r["code"] == role:
                r["state"] = "on"
                r["user_set"] = True
                found = True
            if role == "CL" and r["code"] == "CD":
                r["state"] = "off"
                r["user_set"] = True
        if not found:
            comp.append({"code": role, "state": "on", "user_set": True})
        s["composition"] = comp
    await repo.amutate("sections", sec["id"], fn)
    await plan.sync_sheets(pid, sections=[key])


async def prepare(pid: str, key: str, *, mode: str = "draft", sheet_ids: list[str] | None = None,
                  quick_action: str | None = None) -> dict[str, Any]:
    qa = defs.QUICK_ACTIONS.get(quick_action or "") or {}
    if qa.get("add_role"):
        await add_role(pid, key, qa["add_role"])
    p = await core.load(pid)
    if not p.get("ctx"):
        p["ctx"] = await plan.refresh_context(pid)
    shs = await core.sheets_of(pid, section_key=key)
    if qa.get("add_role"):
        new_role = qa["add_role"]
        sheet_ids = [s["id"] for s in shs if s.get("role") == new_role] or sheet_ids
    targets = [s for s in shs if not sheet_ids or s["id"] in sheet_ids]
    bases = await inputs.base_bodies(p, key, targets, mode=mode)
    active_links = {ln["id"] for ln in bases["links"]}
    rows = []
    for sh in targets:
        b = bases["sheets"][sh["id"]]
        has_content = bool(sh.get("draft"))
        stale_link = any(s.get("kind") == "link" and s.get("ref") and s["ref"] not in active_links for s in sh.get("sources") or [])
        if mode == "draft":
            if sh.get("user_edited") and not sheet_ids:
                action = "keep"
            elif b["has_input"]:
                action = "draft"
            elif has_content and stale_link:
                action = "clear"            # 연결 해제된 자료에서 온 내용 → 다시 「자료 필요」
            else:
                action = "keep" if has_content else "need"
        elif mode == "infer":
            # 딸깍 · 생성 전 추론 — 이미 쓴(또는 사용자가 고친) 시트는 그대로, 빈 시트만 추론(§7.7 「입력한 내용 반영」)
            action = "keep" if (has_content or sh.get("user_edited")) else "draft"
        else:
            action = "draft"
        rows.append({"sheet_id": sh["id"], "key": sheet_key(sh), "role": sh.get("role"), "action": action, "has_input": b["has_input"]})
    return {"rows": rows, "bases": bases["sheets"], "items": bases["items"],
            "links": [{"id": ln["id"], "feature": ln.get("feature"), "handoff": {"items": [{"content": {"real_names": (it.get("content") or {}).get("real_names")}}
                                                                                      for it in (ln.get("handoff") or {}).get("items") or []
                                                                                      if (it.get("content") or {}).get("real_names")]}}
                      for ln in bases["links"]],
            "features": sorted({ln.get("feature") for ln in bases["links"] if ln.get("feature")})}


# ── 2. 초안(LLM) ───────────────────────────────────────────
def map_drafts(res: dict[str, Any] | None, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not res:
        return out
    by_key = {r["key"]: r["sheet_id"] for r in rows}
    used: set[str] = set()
    for d in res.get("sheets") or []:
        if not isinstance(d, dict):
            continue
        k = str(d.get("sheet_key") or "")
        sid = by_key.get(k)
        if sid is None or sid in used:
            role = k.split(":")[0]
            sid = next((r["sheet_id"] for r in rows if r["role"] == role and r["sheet_id"] not in used), None)
        if sid:
            out[sid] = d
            used.add(sid)
    return out


async def draft(pid: str, key: str, prep: dict[str, Any], *, mode: str, request: str | None, memos: list[str],
                extra_lines: list[str] | None = None) -> dict[str, dict[str, Any]]:
    todo = [r for r in prep["rows"] if r["action"] == "draft"]
    if not todo:
        return {}
    p = await core.load(pid)
    ctx = p.get("ctx") or {}
    shs = {s["id"]: s for s in await core.sheets_of(pid, section_key=key)}
    rq = [f"{x.get('code')} {x.get('text')}" for x in ((ctx.get("rq") or {}).get("items") or [])][:12]
    sheets_in = []
    for r in todo:
        sh = shs.get(r["sheet_id"])
        if not sh:
            continue
        base = prep["bases"][r["sheet_id"]]["body"]
        mat = sh.get("draft") if (mode == "request" and sh.get("draft")) else base
        sheets_in.append({"sheet_key": r["key"], "role": r["role"], "role_name": core.role_name(r["role"]), "title": sh.get("title") or "",
                          "msg": (defs.ROLES.get(r["role"] or "") or {}).get("msg", ""), "material": material(mat)})
    if not sheets_in:
        return {}
    extra = []
    if key == "why":
        extra.append("경쟁사는 익명 라벨(경쟁사 A · B · C)로만. 경쟁사 수치가 재료에 없으면 [00] 자리표시.")
    if mode in INFER_MODES and not any(r["has_input"] for r in todo):
        extra.append("연결 자료가 없는 시트는 요구사항 · 고객 정보로 방향만 쓰고 수치는 모두 자리표시로 둔다.")
    if mode == "reuse_borrow":
        extra.append("원본 문장 · 고유명사 · 수치를 쓰지 않는다(흐름만 차용). 수치는 이번 고객 자료에 없으면 [00] 자리표시.")
    extra += [x for x in extra_lines or [] if x]
    user = prompts.section_draft(section_key=key, section_name=defs.SECTIONS[key]["name"], mode=mode,
                                 customer=(p.get("customer") or {}).get("name") or "(고객 미정)", project=p.get("title") or "",
                                 type_name=core.type_name(p.get("type")) or "", requirements=rq, sheets=sheets_in, memos=memos,
                                 request=request, extra="\n".join(extra))
    # 기존 제안서 활용 흐름의 초안은 항상 기밀(§10.13 「원본 대조 초안」)
    conf = True if mode.startswith("reuse") else G.customer_conf()
    res = await G.llm_json("pr.section_draft", system=prompts.RULES, user=user, schema=prompts.SECTION_DRAFT, confidential=conf)
    return map_drafts(res, todo)


# ── 3. 검사 · 저장 ─────────────────────────────────────────
STORE_RE = re.compile(r"(?<![\d,])(\d{1,3}(?:,\d{3})+|\d+)\s?(개\s?매장|개\s?점포|곳)")


async def bind_known_facts(pid: str, body: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """V3 — 매장 수처럼 여러 시트가 함께 쓰는 값은 값 토큰으로 묶는다(값이 바뀌면 모든 시트가 함께 바뀜)."""
    n = (ctx.get("store_count") or "").replace(",", "")
    if not n:
        return body
    f = await F.fact_by_key(pid, "store_count")
    if f is None:
        f = await F.upsert_fact(pid, key="store_count", label="매장 수", value=f"{int(n):,}" if n.isdigit() else n, unit="개", status="unconfirmed",
                                placeholder="[00]개", origin={"by": "customer", "source_ref": "customer.scale_text"},
                                evidence={"kind": "customer", "ref": None, "note": "고객 정보 · 규모"})
    token = "{{fact:" + f["id"] + "}}"

    def fn(t: str, path: str) -> str:
        if path.startswith("/signals") or path.startswith("/images") or path.startswith("/series"):
            return t

        def rep(m: re.Match[str]) -> str:
            if m.group(1).replace(",", "") != n:
                return m.group(0)
            tail = m.group(2).replace("개", "").strip()
            return f"{token} {tail}" if tail and tail != "곳" else token
        return STORE_RE.sub(rep, t)
    new = C.walk_strings({k: v for k, v in body.items() if k not in ("signals", "images", "series")}, fn)
    for k in ("signals", "images", "series"):
        if k in body:
            new[k] = body[k]
    return new


def _reason(feature_set: list[str], key: str, has_input: bool) -> str:
    if key == "why":
        return "공개 자료를 찾지 못했어요"
    if "mi" in feature_set and key in ("mi", "bigMi"):
        return "MI 작업의 추정치 — 출처 확인 필요"
    if not has_input:
        return "연결 자료가 없어 추론한 자리예요"
    return "입력에 근거가 없는 수치예요"


async def persist(pid: str, key: str, prep: dict[str, Any], drafts: dict[str, dict[str, Any]], *, mode: str, origin: str,
                  job: str | None, request: str | None = None) -> dict[str, Any]:
    p = await core.load(pid)
    ctx = p.get("ctx") or {}
    cat = await clients.export_catalog()
    sec_no = core.section_no(p.get("type"), key)
    names = V.real_name_map(prep.get("items") or [], prep.get("links") or [])
    bodies = [prep["bases"][r["sheet_id"]]["body"] for r in prep["rows"]]
    allowed = inputs.allowed_from(p, bodies, [list((await F.facts_of(pid)).values())])
    allowed_text = V.text_of([bodies, p.get("customer") or {}, ctx.get("rq") or {}])
    known_models = V.models_in([bodies, ctx.get("products") or [], ctx.get("rq") or {}, p.get("title") or ""])
    known_models |= {str(x.get("model")) for x in ctx.get("products") or [] if x.get("model")}
    sec_def = defs.SECTIONS[key]
    changed: list[str] = []
    filled: list[str] = []
    cleared: list[str] = []
    prev_code: str | None = None
    for r in prep["rows"]:
        sid = r["sheet_id"]
        sh = await repo.aget("sheets", sid)
        if sh is None:
            continue
        if r["action"] in ("keep", "need"):
            prev_code = (sh.get("template") or {}).get("code")
            continue
        if r["action"] == "clear":
            old = sh.get("content")

            def clr(x: dict[str, Any]) -> None:
                x["prev_content"] = x.get("content")
                x["prev_draft"] = x.get("draft")
                x["content"] = {}
                x["draft"] = {}
                x["status"] = "need"
                x["sources"] = []
                x["content_rev"] = int(x.get("content_rev") or 0) + 1
            await repo.amutate("sheets", sid, clr)
            await core.record_change(pid, sheet=sh, where="시트 내용", kind="content", path="/", from_=old, to={}, by_w=True, job_id=job,
                                     summary=f"{int(sh.get('sheet_no') or 0):02d} {sh.get('title')} · 연결 해제로 비움")
            cleared.append(sid)
            continue
        base = prep["bases"][sid]
        llm = drafts.get(sid)
        if mode == "request" and not llm and sh.get("draft"):
            continue     # 모델이 고치지 않은 시트는 그대로
        body = C.merge_body(sh.get("draft") if (mode == "request" and sh.get("draft")) else base["body"], llm)
        if mode == "request" and llm:
            # 수정 요청: 표 · 계열 · 이미지는 재료(새 반입)가 있으면 그것으로
            for k in ("table", "series", "images", "products"):
                if base["body"].get(k) and not llm.get(k):
                    body[k] = base["body"][k]
        # V1 수치 · V4 모델코드 · V5 경쟁사 실명 · V8 주장
        body, _misses = C.ground_body(body, allowed)
        body, model_misses = V.check_models(body, known_models)
        body, real_hits = V.anonymize(body, names)
        claim_hits = V.claims(body, allowed_text)
        body = await bind_known_facts(pid, body, ctx)
        body, made = await F.tokenize(pid, body, sheet_title=sh.get("title") or "", origin=origin)
        # 템플릿(§7.5)
        sig = dict(body.get("signals") or {})
        t = dict(sh.get("template") or {})
        if sig.get("import_hint"):
            t["import_hint"] = sig["import_hint"]
        sh_for_rec = {**sh, "signals": {**(sh.get("signals") or {}), **sig}, "template": t}
        rec = templates.recommend(sh_for_rec, p, cat, prev_code=prev_code, birdseye=bool((ctx.get("has") or {}).get("birdseye")))
        templates.apply_recommendation(sh_for_rec, rec)
        t = sh_for_rec["template"]
        code = t.get("code")
        detail = await clients.export_template_detail(code, t.get("product_count")) if code else None
        schema = (detail or {}).get("slot_schema")
        body_for_slots = {**body, "source_list": [{"label": s.get("label"), "url": s.get("url")} for s in base["sources"] if s.get("url")][:3]}
        new_content = C.fill_slots(schema, body_for_slots, section_key=key, sheet=sh, p=p, section_no=sec_no)
        old_content = sh.get("content") or {}
        was_filled = bool(sh.get("draft"))
        inferred = mode in ("infer",) and not base["has_input"]
        note = None
        if mode == "infer":
            note = f"근거: {sec_def.get('infer') or '요구사항 · 고객 정보'}" + ("" if base["has_input"] else " · 연결 자료 없이 추론")

        def save(x: dict[str, Any], body: dict[str, Any] = body, content: dict[str, Any] = new_content, t: dict[str, Any] = t,
                 sig: dict[str, Any] = sig, base: dict[str, Any] = base, inferred: bool = inferred, note: str | None = note) -> None:
            x["draft"] = body
            x["content"] = content
            x["signals"] = {**(x.get("signals") or {}), **sig}
            x["template"] = {**(x.get("template") or {}), **t}
            x["sources"] = base["sources"]
            if content != old_content:
                x["content_rev"] = int(x.get("content_rev") or 0) + 1
            x["status"] = "updated" if was_filled and content != old_content else "ready"
            if mode == "infer":
                x["inferred"] = inferred or bool(x.get("inferred"))
                x["evidence_note"] = note
            elif mode in ("draft", "request") and base["has_input"]:
                x["inferred"] = False
                x["evidence_note"] = None
            x["origin"] = x.get("origin") or "user"
            x["filled_by"] = origin
            x["filled_at"] = config.now_iso()
        await repo.amutate("sheets", sid, save)
        prev_code = code
        fresh = await repo.aget("sheets", sid) or sh
        reason = _reason(prep.get("features") or [], key, base["has_input"])
        await F.items_for_tokens(pid, fresh, made, origin=origin, reason=reason)
        for mm in model_misses:
            await F.add_item(pid, sheet=fresh, tag="고객 확인", origin=origin, category="fact",
                             text=F.text_parts(mm["pre"], "[모델 확인 필요]", mm["post"]),
                             sub=f"{fresh.get('title')} · 모델 {mm['code']} 을(를) 입력에서 찾지 못해 비워 두었어요",
                             action={"kind": "button", "label": "시트에서 보기", "target": {"route": core.route(pid, "preview", str(fresh.get('sheet_no') or ''))}})
        for w in claim_hits:
            await F.add_item(pid, sheet=fresh, tag="claim", origin=origin, category="review",
                             text=F.text_parts(w["pre"], w["word"], w["post"]),
                             sub=f"{fresh.get('title')} · 「{w['word']}」 단정은 출처가 있을 때만 써요",
                             action={"kind": "button", "label": "시트에서 보기", "target": {"route": core.route(pid, "preview", str(fresh.get('sheet_no') or ''))}})
        if real_hits:
            await F.add_item(pid, sheet=fresh, tag="경쟁사 실명", origin=origin, category="review",
                             text={"pre": "", "mark": "경쟁사 A · B · C", "post": "로 바꿈"},
                             sub=f"{fresh.get('title')} · 실명으로 넣으려면 경쟁사 분석에서 실명 공개를 확인해야 해요")
        if new_content != old_content:
            if was_filled:
                changed.append(sid)
                await core.record_change(pid, sheet=fresh, where="시트 내용", kind="content", path="/", from_=core.snippet(old_content.get("title")),
                                         to=core.snippet(new_content.get("title")), by_w=True, job_id=job,
                                         extra={"op": "content", "from_full": old_content, "to_full": new_content},
                                         reason=("W 다듬기 · 요청" if mode == "request" else "W 초안"),
                                         summary=f"{int(fresh.get('sheet_no') or 0):02d} {fresh.get('title')} · "
                                                 + ("요청 반영" if mode == "request" else "자료 반영"))
            else:
                filled.append(sid)
        await G.partial({"sheet_id": sid, "status": fresh.get("status"), "template": code})
    # 섹션 상태
    shs = await core.sheets_of(pid, section_key=key)
    any_content = any(s.get("draft") for s in shs)
    sec = await core.section_doc(pid, key)

    from ..ops.sections import fill_signature
    sig = await fill_signature(pid, key)

    def sec_fn(s: dict[str, Any]) -> None:
        s["fill_sig"] = sig
        s["status"] = "ready" if any_content else "empty"
        s.pop("status_before_fill", None)
        s["filled_at"] = config.now_iso()
        if mode == "infer":
            s["inferred"] = True
        if s.get("fill_job_id") == job:
            s["fill_job_id"] = None
    await repo.amutate("sections", sec["id"], sec_fn)
    await F.sync_items(pid)
    await core.touch(pid)
    await core.index(pid)
    if mode == "request" and request:
        n = len(changed) + len(filled)
        reply = (f"시트 {n}장을 고쳤어요 — " + ", ".join(
            f"{int((await repo.aget('sheets', s) or {}).get('sheet_no') or 0):02d}" for s in (changed + filled)[:6])) if n else "바꿀 곳을 찾지 못했어요. 대상 시트를 알려 주세요."
        ids = [c["id"] for c in await repo.alist("changes", {"proposal_id": pid, "job_id": job})] if job else []
        await G.save_message(pid, scope="section", scope_ref=key, role="w", text=reply, change_ids=ids, job=job)
    return {"section_key": key, "changed": changed, "filled": filled, "cleared": cleared,
            "status": "ready" if any_content else "empty"}


# ── 함수 · 그래프 ──────────────────────────────────────────
async def fill(pid: str, key: str, *, mode: str = "draft", request: str | None = None, quick_action: str | None = None,
               sheet_ids: list[str] | None = None, origin: str = "section_fill", job: str | None = None,
               memos: list[str] | None = None) -> dict[str, Any]:
    prep = await prepare(pid, key, mode=mode, sheet_ids=sheet_ids, quick_action=quick_action)
    drafts = await draft(pid, key, prep, mode=mode, request=request, memos=memos or [])
    return await persist(pid, key, prep, drafts, mode=mode, origin=origin, job=job, request=request)


async def _n_load(s: dict[str, Any]) -> dict[str, Any]:
    await G.progress(5, "자료 확인")
    qa = defs.QUICK_ACTIONS.get(s.get("quick_action") or "") or {}
    req = s.get("request") or qa.get("text")
    return {"request": req}


async def _n_sources(s: dict[str, Any]) -> dict[str, Any]:
    prep = await prepare(s["pid"], s["key"], mode=s.get("mode") or "draft", sheet_ids=s.get("sheet_ids"), quick_action=s.get("quick_action"))
    await G.progress(30, "연결 자료 · kb 조회")
    return {"prep": prep}


async def _n_draft(s: dict[str, Any]) -> dict[str, Any]:
    drafts = await draft(s["pid"], s["key"], s["prep"], mode=s.get("mode") or "draft", request=s.get("request"), memos=s.get("memos") or [])
    await G.progress(70, "시트 작성")
    return {"drafts": drafts}


async def _n_persist(s: dict[str, Any]) -> dict[str, Any]:
    res = await persist(s["pid"], s["key"], s["prep"], s.get("drafts") or {}, mode=s.get("mode") or "draft",
                        origin=s.get("origin") or "section_fill", job=s.get("job"), request=s.get("request"))
    return {"result": res, "prep": None, "drafts": None}


LABELS = {"load": "자료 확인", "sources": "연결 자료 가져오기", "draft": "시트 작성", "persist": "검사 · 템플릿 · 저장"}


async def handle(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid, key = pl["proposal_id"], pl["section_key"]
    state = {"pid": pid, "key": key, "mode": pl.get("mode") or "draft", "request": pl.get("request_text"), "quick_action": pl.get("quick_action"),
             "sheet_ids": pl.get("sheet_ids"), "origin": pl.get("origin") or "section_fill", "job": ctx.job.id, "memos": []}
    if state["mode"] == "request" and state["request"]:
        await G.save_message(pid, scope="section", scope_ref=key, role="user", text=state["request"], job=ctx.job.id)
    try:
        final = await G.run(ctx, G.chain([("load", _n_load), ("sources", _n_sources), ("draft", _n_draft), ("persist", _n_persist)]), state,
                            labels=LABELS, progress_map={"persist": 100})
    except BaseException:
        await reset_section(pid, key, ctx.job.id)
        raise
    return {"proposal_id": pid, **((final or {}).get("result") or {})}


async def reset_section(pid: str, key: str, job: str | None) -> None:
    """실패 · 취소 — 「작성 중」 표시를 되돌린다."""
    try:
        sec = await core.section_doc(pid, key)

        def fn(s: dict[str, Any]) -> None:
            if s.get("status") == "filling":
                s["status"] = s.pop("status_before_fill", None) or "empty"
            if s.get("fill_job_id") == job:
                s["fill_job_id"] = None
        await repo.amutate("sections", sec["id"], fn)
    except Exception:  # noqa: BLE001
        log.warning("섹션 상태 되돌리기 실패 %s/%s", pid, key)
