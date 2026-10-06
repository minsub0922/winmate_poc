"""§6.10 검토(workspace 파사드) · 코멘트 수정안 · 공유 링크.

검토 · 결정 · 코멘트 · 공유는 workspace 에 저장한다(§5.11). proposal 은 요약(`review`)만 캐시하고,
workspace 에 없는 것(마감일 · 시트 확인 격자 · 다시 요청)은 제안서 문서에 둔다(요청: docs/requests/workspace.md).
대상 표기: 검토 `proposal:{pid}:v{n}` · 코멘트 `proposal:{pid}:sheet:{sheetId}`(앵커 {proposal_id, version, sheet_id, sheet_no, element_ref, point: {x, y}}).
"""
from __future__ import annotations

from typing import Any

from winmate_common.context import current_user

from .. import clients, config, core, defs, repo, versions as VER
from .. import models as M
from ..errors import not_found, unprocessable
from ..graphs import common as G

DECISION_LABEL = {"approve": ("approved", "승인"), "request_changes": ("changes_requested", "수정 요청"), "pending": ("pending", "대기 중")}
REVIEW_STATUS_LABEL = {"pending": "진행 중", "approved": "승인 완료", "changes_requested": "수정 요청", "canceled": "취소됨"}


def comment_prefix(pid: str) -> str:
    return f"proposal:{pid}"


async def _users() -> dict[str, dict[str, Any]]:
    return {u["id"]: u for u in await clients.ws_users()}


async def _comments(pid: str) -> list[dict[str, Any]]:
    res = await clients.call("workspace", "GET", "/v1/comments", params={"target": comment_prefix(pid) + "*"}, quiet=True)
    return list((res or {}).get("items") or [])


def _sheet_of_comment(c: dict[str, Any]) -> str | None:
    a = c.get("anchor") or {}
    if a.get("sheet_id"):
        return a["sheet_id"]
    parts = (c.get("target") or "").split(":")
    return parts[parts.index("sheet") + 1] if "sheet" in parts and parts.index("sheet") + 1 < len(parts) else None


async def _save_version_if_needed(pid: str, *, desc: str, kind: str = "review_request") -> int:
    p = await core.load(pid)
    v = int(p.get("saved_version") or 0)
    if v == 0 or int(p.get("edits_since_version") or 0) > 0:
        doc = await VER.create(pid, kind=kind, desc=desc, author=core.actor(), pptx_file_id=(p.get("files") or {}).get("pptx_file_id"))
        return int(doc["n"])
    return v


async def request_review(pid: str, body: M.ReviewRequestIn) -> M.ReviewView:
    p = await core.load(pid)
    if not p.get("type"):
        from ..errors import type_required
        raise type_required()
    if body.due_date and not config.parse_date(body.due_date):
        raise unprocessable("INVALID_DATE", "마감일은 YYYY-MM-DD 로 넣어 주세요", due_date=body.due_date)
    v = await _save_version_if_needed(pid, desc="검토 요청")
    rv = await clients.call("workspace", "POST", "/v1/reviews", json={
        "target": f"proposal:{pid}:v{v}", "title": f"{core.title_display(p)} v{v}", "route": core.route(pid, "review"),
        "reviewers": body.reviewer_ids, "required_approvals": len(body.reviewer_ids), "message": body.message}, raise_errors=True)
    await _cache(pid, rv, version=v, due_date=body.due_date, message=body.message, n_reviewers=len(body.reviewer_ids), event="request")
    await core.index(pid, force=True)
    return await review_view(pid)


async def _cache(pid: str, rv: dict[str, Any], *, version: int | None = None, due_date: str | None = None, message: str | None = None,
                 n_reviewers: int | None = None, event: str | None = None) -> None:
    approvals = sum(1 for r in rv.get("reviewers") or [] if r.get("decision") == "approve")
    total = len(rv.get("reviewers") or []) or int(n_reviewers or 0)

    def fn(x: dict[str, Any]) -> None:
        cur = dict(x.get("review") or {})
        cur.update({"review_id": rv["id"], "status": rv.get("status"), "approvals": approvals, "reviewers_total": total,
                    "requested_at": cur.get("requested_at") if cur.get("review_id") == rv["id"] else (rv.get("created_at") or config.now_iso())})
        if version is not None:
            cur["version"] = version
        if due_date is not None:
            cur["due_date"] = due_date
        if message is not None:
            cur["message"] = message
        x["review"] = cur
        if rv.get("status") in ("pending", "approved", "changes_requested"):
            x["status"] = "review"
        if event:
            evs = list(x.get("review_events") or [])
            evs.append({"kind": event, "at": config.now_iso(), "reviewers": total, "version": version, "review_id": rv["id"]})
            x["review_events"] = evs[-20:]
    await core.mutate(pid, fn)


async def _current(pid: str) -> dict[str, Any] | None:
    p = await core.load(pid)
    rid = (p.get("review") or {}).get("review_id")
    if not rid:
        return None
    rv = await clients.call("workspace", "GET", f"/v1/reviews/{rid}", quiet=True)
    if rv:
        r = p.get("review") or {}
        if rv.get("status") != r.get("status") or sum(1 for x in rv.get("reviewers") or [] if x.get("decision") == "approve") != r.get("approvals"):
            await _cache(pid, rv)
    return rv


async def review_view(pid: str) -> M.ReviewView:
    p = await core.load(pid)
    me = current_user().id
    rv = await _current(pid)
    p = await core.load(pid)
    users = await _users() if rv else {}
    reviewers = []
    for r in (rv or {}).get("reviewers") or []:
        u = users.get(r["user_id"]) or {}
        st, label = DECISION_LABEL.get(r.get("decision") or "pending", ("pending", "대기 중"))
        name = r.get("name") or u.get("name") or r["user_id"]
        reviewers.append(M.Reviewer(user_id=r["user_id"], name=name, initial=core.initial(name), role=u.get("role") or "", status=st,
                                    status_label=label, me=r["user_id"] == me))
    total = len(reviewers)
    done = sum(1 for r in reviewers if r.status == "approved")
    comments = await _comments(pid)
    shs = await core.sheets_of(pid)
    by_id = {s["id"]: s for s in shs}
    per: dict[str, dict[str, int]] = {}
    for c in comments:
        if c.get("parent_id"):
            continue
        sid = _sheet_of_comment(c)
        if not sid:
            continue
        d = per.setdefault(sid, {"open": 0, "resolved": 0})
        d["resolved" if c.get("resolved") else "open"] += 1
    sheets = [M.CommentSheet(sheet_no=int(by_id[s].get("sheet_no") or 0), sheet_id=s, name=by_id[s].get("title") or "", open=d["open"],
                             resolved=d["resolved"], label=(f"열린 {d['open']}" if d["open"] else f"해결 {d['resolved']}"))
              for s, d in per.items() if s in by_id]
    sheets.sort(key=lambda x: x.sheet_no)
    n_open = sum(d["open"] for d in per.values())
    n_res = sum(d["resolved"] for d in per.values())
    checks = p.get("checks") or {}
    grid = []
    rids = [r.user_id for r in reviewers]
    for s in shs:
        if per.get(s["id"], {}).get("open"):
            state = "open"
        else:
            marks = checks.get(s["id"]) or {}
            if me in rids:
                state = "ok" if marks.get(me) == "ok" else "todo"
            else:
                state = "ok" if rids and all(marks.get(u) == "ok" for u in rids) else "todo"
        grid.append(M.CheckCell(sheet_no=int(s.get("sheet_no") or 0), sheet_id=s["id"], state=state,
                                title=f"{int(s.get('sheet_no') or 0):02d} · " + {"ok": "확인됨", "open": "열린 코멘트", "todo": "아직 확인 전"}[state]))
    k = sum(1 for g in grid if g.state == "ok")
    info = None
    r = p.get("review") or {}
    if rv:
        sent = config.time_label(r.get("requested_at") or rv.get("created_at"))
        due = config.parse_date(r.get("due_date"))
        info = M.ReviewInfo(id=rv["id"], version=int(r.get("version") or p.get("saved_version") or 0), status=rv.get("status") or "pending",
                            status_label=REVIEW_STATUS_LABEL.get(rv.get("status") or "pending", ""), message=rv.get("message"), due_date=r.get("due_date"),
                            requested_at=r.get("requested_at"), sent_label=f"{sent} 보냄" + (f" · 마감 {config.due_long_label(due)}" if due else ""),
                            requester_name=rv.get("requester_name") or "")
    my = next((x for x in reviewers if x.me), None)
    v = int(p.get("saved_version") or 0)
    return M.ReviewView(review=info, reviewers=reviewers, approvals=M.Approvals(done=done, total=total, label=f"승인 {done} / {total}"),
                        comment_sheets=sheets, comments_open=n_open, comments_resolved=n_res, check_grid=grid,
                        check_label=f"시트 확인 {k} / {len(grid)}", my_turn=bool(my and my.status == "pending" and (rv or {}).get("status") != "canceled"),
                        can_decide=bool(my and (rv or {}).get("status") in ("pending", "changes_requested")),
                        suggest_text=(f"열린 코멘트 {n_open}건을 반영한 수정안을 만들 수 있어요. 새 버전으로 저장하고 바뀐 곳을 비교해 드릴게요."
                                      if n_open else None),
                        version_label=f"v{v} · " + (REVIEW_STATUS_LABEL.get((rv or {}).get("status") or "", "검토 중") if rv else "검토 전") if v else "",
                        comment_target=comment_prefix(pid))


async def get_review(pid: str) -> M.ReviewView:
    return await review_view(pid)


async def resubmit(pid: str, review_id: str, body: M.ResubmitIn) -> M.ReviewView:
    p = await core.load(pid)
    r = p.get("review") or {}
    if r.get("review_id") != review_id:
        raise not_found("검토 요청", review_id, "REVIEW_NOT_FOUND")
    old = await clients.call("workspace", "GET", f"/v1/reviews/{review_id}", quiet=True) or {}
    reviewers = [x["user_id"] for x in old.get("reviewers") or []]
    if not reviewers:
        raise unprocessable("NO_REVIEWERS", "검토자가 없어요")
    v = await _save_version_if_needed(pid, desc="코멘트 반영 후 다시 검토 요청")
    await clients.call("workspace", "POST", f"/v1/reviews/{review_id}/cancel", quiet=True)
    rv = await clients.call("workspace", "POST", "/v1/reviews", json={
        "target": f"proposal:{pid}:v{v}", "title": f"{core.title_display(p)} v{v}", "route": core.route(pid, "review"), "reviewers": reviewers,
        "required_approvals": len(reviewers), "message": body.message or old.get("message")}, raise_errors=True)
    await _cache(pid, rv, version=v, message=body.message or old.get("message"), event="resubmit")
    await core.index(pid, force=True)
    return await review_view(pid)


async def decide(pid: str, body: M.DecisionIn) -> M.ReviewView:
    p = await core.load(pid)
    rid = (p.get("review") or {}).get("review_id")
    if not rid:
        raise unprocessable("NO_REVIEW", "진행 중인 검토 요청이 없어요")
    rv = await clients.call("workspace", "POST", f"/v1/reviews/{rid}/decision", json={"decision": body.decision, "comment": body.comment},
                            raise_errors=True)
    await _cache(pid, rv, event=f"decision:{body.decision}")
    await core.index(pid, force=True)
    return await review_view(pid)


async def put_check(pid: str, sheet_id: str, body: M.CheckPut) -> M.ReviewView:
    await core.load(pid)
    await core.sheet_doc(pid, sheet_id)
    me = current_user().id

    def fn(x: dict[str, Any]) -> None:
        ch = dict(x.get("checks") or {})
        marks = dict(ch.get(sheet_id) or {})
        marks[me] = body.state
        ch[sheet_id] = marks
        x["checks"] = ch
    await core.mutate(pid, fn, bump=False)
    return await review_view(pid)


async def apply_comments(pid: str, body: M.ApplyCommentsIn) -> M.JobAccepted:
    p = await core.load(pid)
    job_id = await G.enqueue("proposal.review_apply", {"proposal_id": pid, "comment_ids": body.comment_ids}, title="검토 코멘트 반영",
                             ref=pid, project_id=p.get("project_id"))
    await core.mutate(pid, lambda x: core.set_job(x, "review_apply", job_id), bump=False)
    return M.JobAccepted(job_id=job_id, kind="proposal.review_apply", proposal_id=pid)


async def suggest(pid: str, comment_id: str) -> M.JobAccepted:
    p = await core.load(pid)
    job_id = await G.enqueue("proposal.comment_suggest", {"proposal_id": pid, "comment_id": comment_id}, title="코멘트 수정안", ref=pid,
                             project_id=p.get("project_id"))
    await repo.aput("suggestions", f"{pid}:{comment_id}", {"id": f"{pid}:{comment_id}", "proposal_id": pid, "comment_id": comment_id,
                                                          "status": "running", "job_id": job_id, "created_iso": config.now_iso()})
    return M.JobAccepted(job_id=job_id, kind="proposal.comment_suggest", proposal_id=pid)


async def get_suggestion(pid: str, comment_id: str) -> M.Suggestion:
    await core.load(pid)
    s = await repo.aget("suggestions", f"{pid}:{comment_id}")
    if not s:
        return M.Suggestion(comment_id=comment_id, status="none")
    st = s.get("status") or "none"
    if st == "running" and not await G.running(s.get("job_id")):
        st = "failed"
    return M.Suggestion(comment_id=comment_id, status=st, suggestion_text=s.get("suggestion_text"), patch=s.get("patch") or [],
                        sheet_id=s.get("sheet_id"), job_id=s.get("job_id"))


async def apply_suggestion(pid: str, comment_id: str) -> M.ApplySuggestionResult:
    await core.load(pid)
    s = await repo.aget("suggestions", f"{pid}:{comment_id}")
    if not s or s.get("status") != "done" or not s.get("patch") or not s.get("sheet_id"):
        raise unprocessable("NO_SUGGESTION", "적용할 수정안이 없어요")
    from ..graphs.review import apply_patch
    sheet, cids = await apply_patch(pid, s["sheet_id"], s["patch"], reason=s.get("reason") or "코멘트 반영", comment_id=comment_id)
    await clients.call("workspace", "POST", "/v1/comments", json={"target": s.get("target") or f"{comment_prefix(pid)}:sheet:{s['sheet_id']}",
                                                                 "body": "적용됨 · W 수정안", "parent_id": comment_id}, quiet=True)
    await repo.amutate("suggestions", f"{pid}:{comment_id}", lambda x: x.update({"status": "applied"}))
    from .sections import sheet_view
    return M.ApplySuggestionResult(comment_id=comment_id, sheet=await sheet_view(sheet), change_ids=cids)


async def share_link(pid: str, body: M.ShareLinkIn) -> M.ShareLinkOut:
    p = await core.load(pid)
    res = await clients.call("workspace", "POST", "/v1/share-links", json={
        "target": f"proposal:{pid}", "route": core.route(pid, "review" if body.permission == "team_comment" else "preview"),
        "title": core.title_display(p)}, raise_errors=True)
    label = "팀 내부 · 코멘트 가능" if body.permission == "team_comment" else "팀 내부 · 보기만"
    return M.ShareLinkOut(url=(res or {}).get("url") or "", token=(res or {}).get("token"), permission=body.permission, permission_label=label)
