"""편집 보조 그래프(§7.9) — sheet_rewrite · proposal_request · notes_generate."""
from __future__ import annotations

import re
from typing import Any

from winmate_common.jobs import JobContext

from .. import clients, content as C, core, defs, facts as F, inputs, prompts, repo, templates, validate as V
from . import common as G
from .section_fill import material, sheet_key

TEXT_TARGETS = {"/title": "title", "/subtitle": "subtitle", "/notes": "notes"}
UNKNOWN = ("", "[확인 필요]", "[확정 필요]")


def merge_table(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    """표 다듬기 — 같은 이름 행은 모델이 값을 준 칸만 바꾸고(「[확인 필요]」 · 빈 칸은 기존 값 유지), 새 이름 행은 뒤에 더한다.
    모델이 기존 행을 말없이 지우지 못하게(사실 보존)."""
    if not old or not old.get("rows"):
        return new
    cols = list(old.get("columns") or [])
    if len(new.get("columns") or []) > len(cols):
        cols = list(new["columns"])
    rows = [dict(r, cells=[dict(c) for c in r.get("cells") or []]) for r in old.get("rows") or []]
    by_label = {r.get("label"): r for r in rows}
    for nr in new.get("rows") or []:
        cur = by_label.get(nr.get("label"))
        if cur is None:
            rows.append({"label": nr.get("label") or "", "cells": [{"text": (c or {}).get("text") or "", "mark": (c or {}).get("mark")}
                                                                    for c in nr.get("cells") or []]})
            continue
        for i, c in enumerate(nr.get("cells") or []):
            text = (c or {}).get("text") or ""
            if text in UNKNOWN:
                continue
            while len(cur["cells"]) <= i:
                cur["cells"].append({"text": ""})
            cur["cells"][i] = {**cur["cells"][i], "text": text, **({"mark": c.get("mark")} if c.get("mark") else {})}
    return {"columns": cols, "rows": rows}


def target_label(content: dict[str, Any], path: str | None) -> str:
    if not path:
        return "시트 전체"
    from ..ops.sections import where_label
    try:
        return where_label(content, path)[0]
    except Exception:  # noqa: BLE001
        return path


async def rewrite_one(pid: str, sid: str, *, instruction: str, target_path: str | None, options: dict[str, Any], job: str | None,
                      memos: list[str], reason: str | None = None) -> dict[str, Any]:
    """시트 하나를 LLM 으로 다듬는다 → {changed, change_ids, reply}."""
    p = await core.load(pid)
    sh = await core.sheet_doc(pid, sid)
    body = dict(sh.get("draft") or {})
    if not body and sh.get("content"):
        body = {"title": (sh.get("content") or {}).get("title") or "", "subtitle": (sh.get("content") or {}).get("subtitle") or ""}
    opts = []
    if options.get("concise"):
        opts.append("더 간결하게")
    if options.get("emphasize_numbers"):
        opts.append("수치 강조")
    if options.get("same_template", True):
        opts.append("같은 템플릿")
    user = prompts.sheet_rewrite(sheet_key=sheet_key(sh), role=sh.get("role") or "", role_name=core.role_name(sh.get("role")),
                                 title=sh.get("title") or "", msg=(defs.ROLES.get(sh.get("role") or "") or {}).get("msg", ""),
                                 material=material(body, 2400), target=target_label(sh.get("content") or {}, target_path),
                                 instruction=instruction or "더 읽기 좋게 다듬어 줘", options=opts,
                                 customer=(p.get("customer") or {}).get("name") or "", memos=memos)
    res = await G.llm_json("pr.sheet_rewrite", system=prompts.RULES, user=user, schema=prompts.SHEET_REWRITE, confidential=G.customer_conf())
    if not res or not isinstance(res.get("sheet"), dict):
        return {"changed": False, "change_ids": [], "reply": "모델에 연결하지 못해 그대로 두었어요. 잠시 뒤 다시 시도해 주세요."}
    llm = res["sheet"]
    new = dict(body)
    field = TEXT_TARGETS.get(target_path or "")
    if field:
        if llm.get(field):
            new[field] = llm[field]
    else:
        for k in ("title", "subtitle", "message", "notes"):
            if llm.get(k):
                new[k] = llm[k]
        for k in ("points", "bullets", "steps", "kpis"):
            if llm.get(k):
                new[k] = llm[k]
        if isinstance(llm.get("table"), dict) and llm["table"].get("rows"):
            new["table"] = merge_table(body.get("table"), llm["table"])
    # 검사(V1 · V4 · V5 · V8) — 재료 = 지금 내용 + 값 + 요구사항
    facts_all = await F.facts_of(pid)
    allowed = inputs.allowed_from(p, [body], [list(facts_all.values()), C.display_content(sh.get("content") or {}, facts_all)])
    new, _m = C.ground_body(new, allowed)
    known = V.models_in([body, (p.get("ctx") or {}).get("products") or [], (p.get("ctx") or {}).get("rq") or {}])
    new, model_misses = V.check_models(new, known)
    lns = [ln for ln in await repo.alist("links", {"proposal_id": pid}) if (ln.get("status") or "linked") == "linked"]
    new, real_hits = V.anonymize(new, V.real_name_map([], lns))
    new, made = await F.tokenize(pid, new, sheet_title=sh.get("title") or "", origin="sheet_rewrite")
    t = dict(sh.get("template") or {})
    if not options.get("same_template", True) and t.get("mode") != "pinned":
        cat = await clients.export_catalog()
        probe = {**sh, "signals": {**(sh.get("signals") or {}), **(new.get("signals") or {})}, "template": t}
        templates.apply_recommendation(probe, templates.recommend(probe, p, cat))
        t = probe["template"]
    detail = await clients.export_template_detail(t["code"], t.get("product_count")) if t.get("code") else None
    new_for_slots = {**new, "source_list": [{"label": s.get("label"), "url": s.get("url")} for s in sh.get("sources") or [] if s.get("url")][:3]}
    content = C.fill_slots((detail or {}).get("slot_schema"), new_for_slots, section_key=sh["section_key"], sheet=sh, p=p,
                           section_no=core.section_no(p.get("type"), sh["section_key"]))
    old = sh.get("content") or {}
    # 사용자가 직접 고친 칸은 대상이 아니면 지킨다
    for k in ("title", "subtitle", "notes"):
        if k != field and any(x == f"/{k}" for x in sh.get("edited_paths") or []) and old.get(k):
            content[k] = old[k]
    if content == old:
        return {"changed": False, "change_ids": [], "reply": res.get("reply") or "바꿀 곳이 없었어요."}
    who = core.actor().get("name") or ""

    def save(x: dict[str, Any]) -> None:
        x["draft"] = new
        x["content"] = content
        x["template"] = t
        x["content_rev"] = int(x.get("content_rev") or 0) + 1
        if int(p.get("saved_version") or 0) > 0:
            x["edited_since_version"] = True
        x["status"] = "updated" if x.get("status") in ("ready", "updated") else (x.get("status") or "ready")
        if x.get("status") == "need":
            x["status"] = "ready"
    saved, _ = await repo.amutate("sheets", sid, save)
    where = target_label(old, target_path) if target_path else "시트 내용"
    cid = await core.record_change(pid, sheet=saved, where=where, kind="text", path=target_path or "/", from_=core.snippet(old.get("title")),
                                   to=core.snippet(content.get("title")), by_w=True, job_id=job,
                                   extra={"op": "content", "from_full": old, "to_full": content},
                                   reason=reason or f"W 다듬기 · {who} 요청",
                                   summary=f"{int(saved.get('sheet_no') or 0):02d} {where} · W 다듬기")
    await F.items_for_tokens(pid, saved, made, origin="sheet_rewrite", reason="공개 자료를 찾지 못했어요" if saved.get("section_key") == "why" else "입력에 근거가 없는 수치예요")
    for mm in model_misses:
        await F.add_item(pid, sheet=saved, tag="고객 확인", origin="sheet_rewrite", text=F.text_parts(mm["pre"], "[모델 확인 필요]", mm["post"]),
                         sub=f"{saved.get('title')} · 모델 {mm['code']} 을(를) 입력에서 찾지 못해 비워 두었어요")
    if real_hits:
        await F.add_item(pid, sheet=saved, tag="경쟁사 실명", origin="sheet_rewrite", category="review",
                         text={"pre": "", "mark": "경쟁사 A · B · C", "post": "로 바꿈"}, sub=f"{saved.get('title')} · 실명은 익명 라벨로 바꿨어요")
    return {"changed": True, "change_ids": [cid], "reply": res.get("reply") or "고쳤어요."}


async def handle_rewrite(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid, sid = pl["proposal_id"], pl["sheet_id"]

    async def node(s: dict[str, Any]) -> dict[str, Any]:
        out = await rewrite_one(pid, sid, instruction=pl.get("instruction") or "", target_path=pl.get("target_path"),
                                options=pl.get("options") or {}, job=ctx.job.id, memos=s.get("memos") or [])
        await G.save_message(pid, scope="sheet", scope_ref=sid, role="w", text=out["reply"], change_ids=out["change_ids"], job=ctx.job.id)
        if out["changed"]:
            await F.sync_items(pid)
            await core.touch(pid, user_edit=True)
            await core.index(pid)
        return {"result": {"proposal_id": pid, "sheet_id": sid, "changed": out["changed"], "change_ids": out["change_ids"], "reply": out["reply"]}}
    final = await G.run(ctx, G.single("rewrite", node), {"memos": []}, labels={"rewrite": "시트 다듬기"}, progress_map={"rewrite": 100})
    return (final or {}).get("result") or {}


# ── 제안서 전체 요청 ───────────────────────────────────────
NUM_RE = re.compile(r"(\d{1,2})\s*(?:번|번째|시트|p\b|쪽)")


def route_fallback(text: str, sheets: list[dict[str, Any]]) -> list[str]:
    """모델 없이 — 「18번」 「시트 21」 같은 번호, 섹션 · 역할 이름으로 고른다."""
    hits: list[str] = []
    nums = {int(m.group(1)) for m in NUM_RE.finditer(text)} | {int(m.group(1)) for m in re.finditer(r"시트\s*(\d{1,2})", text)}
    for s in sheets:
        if s["no"] in nums:
            hits.append(s["id"])
    if hits:
        return hits
    for s in sheets:
        sec = defs.SECTIONS.get(s["section_key"], {})
        names = [sec.get("name") or "", sec.get("short") or "", core.role_name(s["role"]), s["title"]]
        if any(n and n in text for n in names if len(n) >= 2):
            hits.append(s["id"])
    if not hits and any(w in text for w in ("비교표", "비교 항목")):
        hits = [s["id"] for s in sheets if s["role"] == "CM"]
    return hits


async def handle_request(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid, text = pl["proposal_id"], pl["text"]

    async def route(s: dict[str, Any]) -> dict[str, Any]:
        shs = await core.sheets_of(pid)
        rows = [{"id": x["id"], "key": f"{int(x.get('sheet_no') or 0):02d}:{x.get('role')}", "no": int(x.get("sheet_no") or 0),
                 "section": defs.SECTIONS.get(x["section_key"], {}).get("short", ""), "section_key": x["section_key"],
                 "title": x.get("title") or "", "role": x.get("role") or ""} for x in shs]
        res = await G.llm_json("pr.request_route", system=prompts.RULES, user=prompts.request_route(text=text, sheets=rows),
                               schema=prompts.REQUEST_ROUTE, confidential=G.customer_conf())
        picked: list[str] = []
        for k in (res or {}).get("sheet_keys") or []:
            k = str(k)
            hit = next((r["id"] for r in rows if r["key"] == k), None)
            if hit is None:   # 역할 코드만 왔으면 그 역할 시트
                role = k.split(":")[-1]
                hit = next((r["id"] for r in rows if r["role"] == role and r["id"] not in picked), None)
            if hit and hit not in picked:
                picked.append(hit)
        fb = route_fallback(text, rows)
        if fb and (not picked or not set(picked) & set(fb)):
            picked = fb if not picked else picked
        return {"targets": picked[:6], "instruction": (res or {}).get("instruction") or text}

    async def apply(s: dict[str, Any]) -> dict[str, Any]:
        changed: list[str] = []
        cids: list[str] = []
        replies: list[str] = []
        for sid in s.get("targets") or []:
            await G.check_cancel()
            out = await rewrite_one(pid, sid, instruction=s.get("instruction") or text, target_path=None, options={"same_template": True},
                                    job=ctx.job.id, memos=s.get("memos") or [], reason=f"W 다듬기 · {core.actor().get('name') or ''} 요청")
            if out["changed"]:
                changed.append(sid)
                cids += out["change_ids"]
                replies.append(out["reply"])
        if changed:
            await F.sync_items(pid)
            await core.touch(pid, user_edit=True)
            await core.index(pid)
        nos = []
        for sid in changed:
            sh = await repo.aget("sheets", sid) or {}
            nos.append(f"{int(sh.get('sheet_no') or 0):02d}")
        reply = (" ".join(replies) if len(replies) == 1 else f"시트 {len(changed)}장({', '.join(nos)})을 고쳤어요.") if changed else \
            "고칠 시트를 찾지 못했어요. 시트 번호(예: 18번)를 함께 알려 주세요."
        await G.save_message(pid, scope="proposal", scope_ref=None, role="w", text=reply, change_ids=cids, job=ctx.job.id)
        return {"result": {"proposal_id": pid, "changed_sheet_ids": changed, "change_ids": cids, "reply": reply}}

    final = await G.run(ctx, G.chain([("route", route), ("apply", apply)]), {"memos": []},
                        labels={"route": "고칠 시트 고르기", "apply": "시트 다듬기"}, progress_map={"route": 30, "apply": 100})
    return (final or {}).get("result") or {}


# ── 발표자 노트 ────────────────────────────────────────────
async def generate_notes(pid: str, *, only_empty: bool = True, sheet_ids: list[str] | None = None, job: str | None = None) -> list[str]:
    p = await core.load(pid)
    shs = [s for s in await core.sheets_of(pid) if s.get("draft") and (not sheet_ids or s["id"] in sheet_ids)]
    if only_empty:
        shs = [s for s in shs if not ((s.get("content") or {}).get("notes") or "").strip()]
    if not shs:
        return []
    rows = [{"key": f"{int(s.get('sheet_no') or 0):02d}:{s.get('role')}", "role": s.get("role"), "role_name": core.role_name(s.get("role")),
             "title": s.get("title") or "", "material": material(s.get("draft") or {}, 600)} for s in shs[:30]]
    res = await G.llm_json("pr.notes", system=prompts.RULES, user=prompts.notes(customer=(p.get("customer") or {}).get("name") or "", sheets=rows),
                           schema=prompts.NOTES, confidential=G.customer_conf())
    by_key = {str(n.get("sheet_key")): n.get("text") for n in (res or {}).get("notes") or [] if n.get("text")}
    by_role: dict[str, list[str]] = {}
    for n in (res or {}).get("notes") or []:
        if n.get("text"):
            by_role.setdefault(str(n.get("sheet_key")).split(":")[-1], []).append(n["text"])
    changed = []
    facts_all = await F.facts_of(pid)
    for s, r in zip(shs, rows):
        text = by_key.get(r["key"]) or (by_role.get(s.get("role") or "") or [None])[0]
        if not text:
            # 모델이 없으면 결정적 노트(시트 메시지 + 출처)
            msg = (defs.ROLES.get(s.get("role") or "") or {}).get("msg", "")
            src = ", ".join(x.get("label") for x in s.get("sources") or [] if x.get("label"))[:80]
            text = f"이 장의 메시지: {msg}." + (f" 근거: {src}." if src else "")
        allowed = inputs.allowed_from(p, [s.get("draft") or {}], [list(facts_all.values())])
        text, _ = C.ground_numbers(text, allowed)

        def fn(x: dict[str, Any], text: str = text) -> None:
            c = dict(x.get("content") or {})
            c["notes"] = text
            x["content"] = c
            d = dict(x.get("draft") or {})
            d["notes"] = text
            x["draft"] = d
            x["content_rev"] = int(x.get("content_rev") or 0) + 1
        saved, _ = await repo.amutate("sheets", s["id"], fn)
        await core.record_change(pid, sheet=saved, where="노트", kind="notes", path="/notes", from_="", to=core.snippet(text), by_w=True, job_id=job,
                                 summary=f"{int(saved.get('sheet_no') or 0):02d} 발표자 노트 추가")
        changed.append(s["id"])
    return changed


async def handle_notes(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid = pl["proposal_id"]

    async def node(_s: dict[str, Any]) -> dict[str, Any]:
        changed = await generate_notes(pid, only_empty=bool(pl.get("only_empty", True)), job=ctx.job.id)
        if changed:
            await core.touch(pid, user_edit=True)
        return {"result": {"proposal_id": pid, "changed_sheet_ids": changed, "count": len(changed)}}
    final = await G.run(ctx, G.single("notes", node), {}, labels={"notes": "발표자 노트 쓰기"}, progress_map={"notes": 100})
    return (final or {}).get("result") or {}
