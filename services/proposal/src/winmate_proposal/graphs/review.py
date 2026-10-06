"""comment_suggest · review_apply(§7.9) — 코멘트 → 한 시트 안에서 끝나는 패치(LLM `pr.comment_patch`) → 적용 → (전부 반영이면) 새 버전."""
from __future__ import annotations

import copy
import logging
from typing import Any

from winmate_common.jobs import JobContext

from .. import clients, config, content as C, core, facts as F, prompts, repo, versions as VER
from .. import models as M
from . import common as G

log = logging.getLogger("winmate.proposal.review")


async def _comment(pid: str, comment_id: str) -> dict[str, Any] | None:
    res = await clients.call("workspace", "GET", "/v1/comments", params={"target": f"proposal:{pid}*"}, quiet=True)
    return next((c for c in (res or {}).get("items") or [] if c.get("id") == comment_id), None)


def _sheet_id(c: dict[str, Any]) -> str | None:
    from ..ops.review import _sheet_of_comment
    return _sheet_of_comment(c)


async def apply_patch(pid: str, sid: str, patch: list[dict[str, Any]], *, reason: str, comment_id: str | None = None,
                      job: str | None = None) -> tuple[dict[str, Any], list[str]]:
    """패치(set · insert · delete) → 시트 content. 값 토큰 · id 는 지킨다."""
    from ..ops.sections import apply_op, where_label
    p = await core.load(pid)
    recs: list[tuple[str, str, str, Any, Any, dict[str, Any]]] = []

    def fn(x: dict[str, Any]) -> None:
        content = copy.deepcopy(x.get("content") or {})
        recs.clear()
        for op in patch:
            try:
                o = M.SheetOp(**op)
                where, kind = where_label(content, o.path)
                b, a = apply_op(content, o)
                recs.append((where, kind, o.path, b, a, op))
            except Exception as exc:  # noqa: BLE001
                log.info("패치 건너뜀 %s: %s", op, exc)
        x["content"] = content
        x["content_rev"] = int(x.get("content_rev") or 0) + 1
        if int(p.get("saved_version") or 0) > 0:
            x["edited_since_version"] = True
    saved, _ = await repo.amutate("sheets", sid, fn)
    cids = []
    for where, kind, path, b, a, op in recs:
        cids.append(await core.record_change(pid, sheet=saved, where=where, kind=kind, path=path, from_=core.snippet(b, 60), to=core.snippet(a, 60),
                                             reason=reason, comment_id=comment_id, job_id=job, by_w=True,
                                             summary=f"{int(saved.get('sheet_no') or 0):02d} {where} · {reason}",
                                             extra={"op": op.get("op"), "from_full": b, "to_full": a}))
    await core.touch(pid, user_edit=True)
    return saved, cids


async def suggest_for(pid: str, c: dict[str, Any]) -> dict[str, Any]:
    sid = _sheet_id(c)
    if not sid:
        return {"applicable": False, "suggestion_text": "어느 시트의 코멘트인지 알 수 없어요."}
    sh = await core.sheet_doc(pid, sid)
    facts_all = await F.facts_of(pid)
    shown = C.display_content(sh.get("content") or {}, facts_all)
    user = (f"코멘트 수정안 · 시트 {int(sh.get('sheet_no') or 0):02d} 「{sh.get('title')}」\n코멘트({c.get('author_name') or ''}): {c.get('body')}\n"
            f"앵커: {G.dumps(c.get('anchor') or {}, 400)}\n지금 시트 내용(JSON pointer 로 고칠 곳을 고른다):\n{G.dumps(shown, 5000)}\n"
            "한 시트 안에서 끝나면 applicable=true 와 ops(set · insert · delete, path 는 content 기준), 아니면 false 와 안내 문장.")
    res = await G.llm_json("pr.comment_patch", system=prompts.RULES, user=user, schema=prompts.COMMENT_PATCH, confidential=G.customer_conf())
    if not res:
        return {"applicable": False, "suggestion_text": "수정안을 만들지 못했어요. 「수정안 만들기」로 전체 반영을 해 보세요."}
    ops = [o for o in res.get("ops") or [] if isinstance(o, dict) and str(o.get("path") or "").startswith("/")]
    return {"applicable": bool(res.get("applicable")) and bool(ops), "suggestion_text": res.get("suggestion_text") or "", "ops": ops,
            "sheet_id": sid, "target": c.get("target")}


async def handle_suggest(ctx: JobContext) -> dict[str, Any]:
    pl = ctx.payload
    pid, cid = pl["proposal_id"], pl["comment_id"]

    async def node(_s: dict[str, Any]) -> dict[str, Any]:
        c = await _comment(pid, cid)
        if not c:
            await repo.amutate("suggestions", f"{pid}:{cid}", lambda x: x.update({"status": "failed", "suggestion_text": "코멘트를 찾지 못했어요."}))
            return {"result": {"comment_id": cid, "status": "failed"}}
        out = await suggest_for(pid, c)
        st = "done" if out.get("applicable") else "not_applicable"
        reason = f"{c.get('author_name') or ''} 코멘트 반영".strip()
        await repo.amutate("suggestions", f"{pid}:{cid}", lambda x: x.update({
            "status": st, "suggestion_text": out.get("suggestion_text"), "patch": out.get("ops") or [], "sheet_id": out.get("sheet_id"),
            "target": out.get("target"), "reason": reason}))
        return {"result": {"comment_id": cid, "status": st, "suggestion_text": out.get("suggestion_text")}}
    final = await G.run(ctx, G.single("suggest", node), {}, labels={"suggest": "코멘트 수정안"}, progress_map={"suggest": 100})
    return (final or {}).get("result") or {}


async def handle_apply(ctx: JobContext) -> dict[str, Any]:
    """열린 코멘트 전부(또는 고른 것) → 시트별 패치 → 새 버전(kind comments_applied, 「검토 코멘트 반영」) → 코멘트마다 「반영됨」 답글."""
    pl = ctx.payload
    pid = pl["proposal_id"]

    async def node(_s: dict[str, Any]) -> dict[str, Any]:
        p = await core.load(pid)
        req_v = int((p.get("review") or {}).get("version") or p.get("saved_version") or 0)
        res = await clients.call("workspace", "GET", "/v1/comments", params={"target": f"proposal:{pid}*"}, quiet=True)
        comments = [c for c in (res or {}).get("items") or [] if not c.get("parent_id") and not c.get("resolved")]
        if pl.get("comment_ids"):
            comments = [c for c in comments if c["id"] in pl["comment_ids"]]
        applied, skipped, changes = [], [], []
        for c in comments:
            await G.check_cancel()
            out = await suggest_for(pid, c)
            if not out.get("applicable"):
                skipped.append(c["id"])
                continue
            _sh, cids = await apply_patch(pid, out["sheet_id"], out["ops"], reason=f"{c.get('author_name') or ''} 코멘트 반영".strip(),
                                          comment_id=c["id"], job=ctx.job.id)
            changes += cids
            applied.append(c["id"])
        v = None
        if applied:
            doc = await VER.create(pid, kind="comments_applied", desc="검토 코멘트 반영", author=core.actor(),
                                   pptx_file_id=(p.get("files") or {}).get("pptx_file_id"), extra={"from_version": req_v, "comment_ids": applied})
            v = doc["n"]
            for c in comments:
                if c["id"] in applied:
                    await clients.call("workspace", "POST", "/v1/comments", json={"target": c.get("target"), "body": f"반영됨 · v{v}",
                                                                                 "parent_id": c["id"]}, quiet=True)
        await core.mutate(pid, lambda x: core.set_job(x, "review_apply", None), bump=False)
        await core.index(pid, force=True)
        return {"result": {"proposal_id": pid, "applied": applied, "skipped": skipped, "version": v, "from_version": req_v,
                           "compare_route": core.route(pid, "versions") + (f"?a={req_v}&b={v}" if v else ""), "change_ids": changes}}
    final = await G.run(ctx, G.single("apply", node), {}, labels={"apply": "검토 코멘트 반영"}, progress_map={"apply": 100})
    return (final or {}).get("result") or {}
