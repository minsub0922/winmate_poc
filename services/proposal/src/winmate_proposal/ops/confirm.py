"""§6.9 확인 항목(PR7Q 확정 필요 · 검토 필요) — 값 확정 · 전파 · 노트로 옮기기 · 익명 · 고객 질문 · 근거 · 다시 찾기."""
from __future__ import annotations

import re
from typing import Any

from .. import clients, config, content as C, core, defs, facts as F, repo
from .. import models as M
from ..errors import not_found, unprocessable
from ..graphs import common as G
from .sections import fact_view, item_text, set_fact

STATUS_LABEL = defs.CONFIRM_STATUS_LABEL


async def _sheets(pid: str) -> dict[str, dict[str, Any]]:
    return {s["id"]: s for s in await core.sheets_of(pid, include_excluded=True)}


def item_view(it: dict[str, Any], sheets: dict[str, dict[str, Any]], facts_all: dict[str, dict[str, Any]],
              uses: dict[str, list[dict[str, Any]]]) -> M.ConfirmItem:
    pid = it["proposal_id"]
    sh = sheets.get(it.get("sheet_id") or "") or {}
    no = int(sh.get("sheet_no") or 0) or None
    by_key = {f.get("key"): f for f in facts_all.values()}
    fix = None
    fx = it.get("fix") or None
    f = facts_all.get(it.get("fact_id") or "")
    if fx or f:
        sentence = []
        for part in (fx or {}).get("sentence") or ([{"text": (it.get("text") or {}).get("pre")}, {"input": f.get("key") if f else None, "label": (f or {}).get("label")},
                                                     {"text": (it.get("text") or {}).get("post")}]):
            pf = dict(part)
            if pf.get("input") and pf["input"] in by_key:
                pf["value"] = by_key[pf["input"]].get("value")
                pf["label"] = pf.get("label") or by_key[pf["input"]].get("label")
            sentence.append(M.FixPart(**{k: v for k, v in pf.items() if k in ("text", "input", "label", "value")}))
        formula = (fx or {}).get("formula")
        if not formula and f:
            dep = next((d for d in facts_all.values() if d.get("formula") and (f.get("key") or "") in (d.get("formula") or "")), None)
            if dep:
                fv = fact_view(dep, by_key, [])
                formula = fv.formula_label
        linked = []
        sids = list(dict.fromkeys([u["sheet_id"] for u in uses.get(it.get("fact_id") or "", [])] + list(it.get("linked_sheet_ids") or [])))
        for d in facts_all.values():
            if f and d.get("formula") and (f.get("key") or "") in (d.get("formula") or ""):
                sids += [u["sheet_id"] for u in uses.get(d["id"], []) if u["sheet_id"] not in sids]
        for sid in sids:
            s2 = sheets.get(sid)
            if s2:
                linked.append(M.FixSheet(sheet_id=sid, sheet_no=int(s2.get("sheet_no") or 0), name=s2.get("title") or ""))
        fix = M.ConfirmFix(sentence=sentence, formula=formula, linked_sheets=sorted(linked, key=lambda x: x.sheet_no))
    act = it.get("action") or None
    route = ((act or {}).get("target") or {}).get("route") or (core.section_route(pid, it["section_key"]) if it.get("section_key") else core.route(pid, "confirm"))
    ev = it.get("evidence") or None
    cands = [M.Candidate(**c) for c in it.get("candidates") or [] if isinstance(c, dict) and c.get("value")]
    return M.ConfirmItem(
        id=it["id"], proposal_id=pid, category=it.get("category") or "fact", tag=it.get("tag") or "수치", sheet_id=it.get("sheet_id"),
        sheet_no=no, sheet_no_label=f"{no:02d}" if no else "", section_key=it.get("section_key") or sh.get("section_key"), fact_id=it.get("fact_id"),
        text=M.ConfirmText(**{"pre": (it.get("text") or {}).get("pre") or "", "mark": (it.get("text") or {}).get("mark") or "",
                              "post": (it.get("text") or {}).get("post") or ""}),
        sub=it.get("sub") or "", action=M.ConfirmAction(**act) if act else None, fix=fix, linked_sheet_ids=list(it.get("linked_sheet_ids") or []),
        where=it.get("where"), why=it.get("why"), status=it.get("status") or "open", status_label=STATUS_LABEL.get(it.get("status") or "open", ""),
        resolution=it.get("resolution"),
        evidence=M.FactEvidence(**ev) if isinstance(ev, dict) and ev.get("kind") in ("url", "file", "work", "internal_doc", "customer", "user") else None,
        candidates=cands, candidates_label=f"후보 {len(cands)}" if cands else None, origin=it.get("origin") or "user", route=route,
        created_at=it.get("created_iso") or it.get("created_at") or "")


async def views(pid: str, items: list[dict[str, Any]]) -> list[M.ConfirmItem]:
    sheets = await _sheets(pid)
    facts_all = await F.facts_of(pid)
    uses = await F.used_in(pid)
    out = [item_view(it, sheets, facts_all, uses) for it in items]
    out.sort(key=lambda x: (x.sheet_no or 999, x.created_at))
    return out


async def list_items(pid: str, *, status: str = "all", sheet_id: str | None = None, category: str | None = None) -> M.ConfirmList:
    await core.load(pid)
    await F.sync_items(pid)
    all_items = [it for it in await repo.alist("confirm_items", {"proposal_id": pid}) if it.get("status") != "dismissed"]
    if sheet_id:
        all_items = [it for it in all_items if it.get("sheet_id") == sheet_id or sheet_id in (it.get("linked_sheet_ids") or [])]
    if category:
        all_items = [it for it in all_items if (it.get("category") or "fact") == category]
    open_n = sum(1 for it in all_items if it.get("status") == "open")
    done = [it for it in all_items if it.get("status") in ("confirmed", "moved_to_note")]
    total = open_n + len(done)
    if status == "open":
        sel = [it for it in all_items if it.get("status") == "open"]
    elif status == "confirmed":
        sel = done
    else:
        sel = all_items
    vs = await views(pid, sel)
    sheets = await _sheets(pid)
    summ = []
    for it in done[:6]:
        sh = sheets.get(it.get("sheet_id") or "") or {}
        res = it.get("resolution") or {}
        how = "노트로 옮김" if it.get("status") == "moved_to_note" else (
            "공개 자료 링크 첨부" if (res.get("evidence") or {}).get("kind") == "url" else
            "사내 자료로 확정" if (res.get("evidence") or {}).get("kind") == "internal_doc" else "값 확정")
        summ.append(f"{int(sh.get('sheet_no') or 0):02d} {sh.get('title') or ''} · {how}")
    n_sheets = len([s for s in sheets.values() if s.get("status") != "excluded" and not s.get("hidden")])
    return M.ConfirmList(items=vs, counts=M.ConfirmCounts(open=open_n, confirmed=len(done), total=total),
                         header_label=f"확정 필요 {total}곳", progress_label=f"{len(done)}곳 확정 · {open_n}곳 남음",
                         intro=(f"제안서 {n_sheets}시트에서 사실 확인이 필요한 곳 {total}곳을 모았어요. 값을 넣거나 근거를 붙이면 그 값이 쓰인 시트에 모두 반영되고, "
                                "확정하지 않은 곳은 내보낼 때 표시를 남길 수 있어요."),
                         confirmed_summary=" · ".join(summ), footer_label=f"확정 필요 · {open_n}곳 남음 · 확정한 값은 버전 기록에 남아요",
                         sheets_total=n_sheets)


async def _item(pid: str, item_id: str) -> dict[str, Any]:
    it = await repo.aget("confirm_items", item_id)
    if not it or it.get("proposal_id") != pid:
        raise not_found("확인 항목", item_id, "CONFIRM_ITEM_NOT_FOUND")
    return it


async def _one(pid: str, item_id: str) -> M.ConfirmItem:
    return (await views(pid, [await _item(pid, item_id)]))[0]


async def create_item(pid: str, body: M.ConfirmCreate) -> M.ConfirmItem:
    await core.load(pid)
    sh = await core.sheet_doc(pid, body.sheet_id)
    text = body.text.strip()
    if not text:
        raise unprocessable("TEXT_REQUIRED", "확인할 내용을 적어 주세요")
    it = await F.add_item(pid, sheet=sh, tag=body.tag or ("검토 코멘트" if body.from_comment_id else "수치"), category="fact",
                          origin="comment" if body.from_comment_id else "user", text={"pre": "", "mark": text[:60], "post": ""},
                          sub=f"{sh.get('title')} · " + ("검토 코멘트에서 보냈어요" if body.from_comment_id else "직접 등록했어요"),
                          action={"kind": "button", "label": "시트에서 보기", "target": {"route": core.route(pid, "preview", str(sh.get("sheet_no") or ""))}},
                          dedupe=False)
    if body.from_comment_id:
        await repo.amutate("confirm_items", it["id"], lambda x: x.update({"comment_id": body.from_comment_id}))
    await core.index(pid)
    return await _one(pid, it["id"])


async def resolve_item(pid: str, item_id: str, body: M.ConfirmResolve) -> M.ConfirmResolveResult:
    await core.load(pid)
    it = await _item(pid, item_id)
    by = core.actor()
    ev = body.evidence.model_dump() if body.evidence else None
    changed: list[str] = []
    cids: list[str] = []
    touched_facts: list[str] = []
    facts_all = await F.facts_of(pid)
    by_key = {f.get("key"): f for f in facts_all.values()}
    values = dict(body.values or {})
    if body.value is not None and it.get("fact_id"):
        values.setdefault((facts_all.get(it["fact_id"]) or {}).get("key") or "", body.value)
    for key, val in values.items():
        f = by_key.get(key)
        if not f:
            continue
        v = re.sub(r"\s+", "", str(val)) if re.fullmatch(r"[\d,\s.]+", str(val or "")) else str(val)
        _saved, sids, ch, _closed = await set_fact(pid, f["id"], value=v, unit=None, evidence=ev, by=by)
        changed += [s for s in sids if s not in changed]
        cids += ch
        touched_facts.append(f["id"])
    if it.get("status") == "open":
        await repo.amutate("confirm_items", item_id, lambda x: x.update({
            "status": "confirmed", "resolution": {"value": body.value, "values": values or None, "evidence": ev, "by": by, "at": config.now_iso()},
            **({"evidence": ev} if ev else {})}))
    # 수동 확인 항목(값 없음)의 시트 「[확정 필요]」 표시는 그대로 — 사람이 인정한 것
    await F.sync_items(pid)
    await core.touch(pid, user_edit=bool(changed))
    await core.index(pid)
    facts_all = await F.facts_of(pid)
    by_key = {f.get("key"): f for f in facts_all.values()}
    uses = await F.used_in(pid)
    return M.ConfirmResolveResult(item=await _one(pid, item_id), changed_sheet_ids=changed, change_ids=cids,
                                  facts=[fact_view(facts_all[f], by_key, uses.get(f, [])) for f in touched_facts if f in facts_all])


async def _note_fact(pid: str, fid: str | None) -> list[str]:
    if not fid:
        return []
    f, _ = await repo.amutate("facts", fid, lambda x: x.update({"moved_to_note": True}))
    sids = [u["sheet_id"] for u in (await F.used_in(pid)).get(fid, [])]
    for sid in dict.fromkeys(sids):
        await repo.amutate("sheets", sid, lambda x: x.update({"content_rev": int(x.get("content_rev") or 0) + 1}))
    return sids


async def move_to_note(pid: str, item_id: str) -> M.ConfirmItem:
    await core.load(pid)
    it = await _item(pid, item_id)
    if it.get("status") != "open":
        raise unprocessable("ITEM_NOT_OPEN", "이미 처리한 항목이에요", status=it.get("status"))
    await _note_fact(pid, it.get("fact_id"))
    await repo.amutate("confirm_items", item_id, lambda x: x.update({"status": "moved_to_note",
                                                                      "resolution": {"by": core.actor(), "at": config.now_iso(), "moved_to_note": True}}))
    await core.record_change(pid, sheet=await repo.aget("sheets", it.get("sheet_id") or "") if it.get("sheet_id") else None, where="노트",
                             kind="notes", path="/notes", from_=item_text(it), to="—", summary=f"{item_text(it)[:30]} → 노트로")
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    return await _one(pid, item_id)


async def move_all_to_note(pid: str, body: M.BulkIds) -> M.ConfirmList:
    await core.load(pid)
    for it in await repo.alist("confirm_items", {"proposal_id": pid}):
        if it.get("status") != "open" or (it.get("category") or "fact") != "fact":
            continue
        if body.ids and it["id"] not in body.ids:
            continue
        await _note_fact(pid, it.get("fact_id"))
        await repo.amutate("confirm_items", it["id"], lambda x: x.update({"status": "moved_to_note",
                                                                          "resolution": {"by": core.actor(), "at": config.now_iso(), "moved_to_note": True}}))
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    return await list_items(pid)


ANON_DEFAULT = {"FB": "국내 커피 프랜차이즈", "RT": "국내 리테일 체인", "CV": "국내 편의점 체인", "HT": "국내 호텔 체인", "ED": "국내 대학교",
                "MD": "국내 종합병원", "OF": "국내 대기업 사옥"}


async def anonymize(pid: str, item_id: str) -> M.ConfirmResolveResult:
    """「익명으로 바꾸기」 — 사례 고객사명 → 업종 표현(LLM `pr.anonymize_case`, 실패하면 업종 기본 표현)."""
    p = await core.load(pid)
    it = await _item(pid, item_id)
    sh = await core.sheet_doc(pid, it.get("sheet_id") or "") if it.get("sheet_id") else None
    if not sh:
        raise unprocessable("SHEET_REQUIRED", "시트가 있는 항목만 익명으로 바꿀 수 있어요")
    draft = dict(sh.get("draft") or {})
    name = draft.get("customer") or (sh.get("repeat_key") or {}).get("label") or ""
    if not name:
        raise unprocessable("NOTHING_TO_ANONYMIZE", "바꿀 고객사명을 찾지 못했어요")
    res = await G.llm_json("pr.anonymize_case", system="고객사명을 업종 표현으로만 바꾼다. 실명 · 지명 · 수치를 넣지 않는다.",
                           user=f"사례 고객사: {name}\n사례 제목: {sh.get('title')}\n업종 표현 하나(예 국내 커피 프랜차이즈)",
                           schema={"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]}, confidential=False)
    label = ((res or {}).get("label") or "").strip()
    ind = (p.get("customer") or {}).get("industry_code") or ""
    if not label or name in label:
        label = ANON_DEFAULT.get(ind, "국내 고객사")
    from .sections import refill_content

    def rep(t: str, _p: str) -> str:
        return t.replace(name, label)
    new_draft = C.walk_strings(draft, rep)
    new_draft["customer"] = label
    probe = {**sh, "draft": new_draft, "title": (sh.get("title") or "").replace(name, label)}
    content = await refill_content(pid, probe)
    content = C.walk_strings(content, rep)

    def fn(x: dict[str, Any]) -> None:
        x["draft"] = new_draft
        x["content"] = content
        x["title"] = probe["title"]
        x["title_user_set"] = True
        x["content_rev"] = int(x.get("content_rev") or 0) + 1
        x["anonymized"] = {"from": name, "to": label}
    saved, _ = await repo.amutate("sheets", sh["id"], fn)
    cid = await core.record_change(pid, sheet=saved, where="고객사명", kind="text", path="/customer", from_=name, to=label, reason="익명으로 바꾸기",
                                   summary=f"{int(saved.get('sheet_no') or 0):02d} 고객사명 → {label}")
    await repo.amutate("confirm_items", item_id, lambda x: x.update({"status": "confirmed", "resolution": {
        "value": label, "by": core.actor(), "at": config.now_iso(), "anonymized": True}}))
    await core.touch(pid, user_edit=True)
    await core.index(pid)
    return M.ConfirmResolveResult(item=await _one(pid, item_id), changed_sheet_ids=[sh["id"]], change_ids=[cid])


async def question(pid: str, item_id: str, body: M.QuestionIn) -> M.QuestionOut:
    p = await core.load(pid)
    it = await _item(pid, item_id)
    f = await repo.aget("facts", it["fact_id"]) if it.get("fact_id") else None
    label = (f or {}).get("label") or item_text(it)
    res = await G.llm_json("pr.customer_question", system="고객에게 보낼 정중한 질문 한 문장. 내부 수치 · 추정치는 쓰지 않는다.",
                           user=f"확인할 값: {label}\n문장: {item_text(it)}\n시트: {it.get('sub')}", schema={"type": "object", "properties": {
                               "text": {"type": "string"}}, "required": ["text"]}, confidential=G.customer_conf())
    text = ((res or {}).get("text") or "").strip()
    if not text:
        text = f"{label}을(를) 알려주실 수 있을까요?" if not label.endswith("?") else label
    pushed = False
    qid = None
    rq = p.get("rq_ref") or {}
    if body.push_to_rq and rq.get("rq_id"):
        out = await clients.call("requirements", "POST", f"/v1/requirements/{rq['rq_id']}/customer-questions",
                                 json={"text": text, "origin": {"kind": "proposal", "feature": "PR", "ref_id": pid, "confirm_item_id": item_id}}, quiet=True)
        if out:
            pushed = True
            qid = out.get("id") or out.get("question_id")
    await repo.amutate("confirm_items", item_id, lambda x: x.update({"question": {"text": text, "pushed": pushed, "id": qid}}))
    return M.QuestionOut(text=text, pushed=pushed, question_id=qid)


async def attach_evidence(pid: str, item_id: str, body: M.EvidenceIn) -> M.ConfirmItem:
    await core.load(pid)
    it = await _item(pid, item_id)
    ev = body.evidence.model_dump()
    await repo.amutate("confirm_items", item_id, lambda x: x.update({"evidence": ev}))
    if it.get("fact_id"):
        await repo.amutate("facts", it["fact_id"], lambda x: x.update({"evidence": ev}))
    return await _one(pid, item_id)


async def research(pid: str, body: M.ResearchIn) -> M.JobAccepted:
    p = await core.load(pid)
    ids = body.ids or [it["id"] for it in await repo.alist("confirm_items", {"proposal_id": pid})
                       if it.get("status") == "open" and (it.get("category") or "fact") == "fact"]
    job_id = await G.enqueue("proposal.confirm_research", {"proposal_id": pid, "ids": ids, "instruction": body.instruction},
                             title="남은 수치 다시 찾기", ref=pid, project_id=p.get("project_id"))
    return M.JobAccepted(job_id=job_id, kind="proposal.confirm_research", proposal_id=pid)
