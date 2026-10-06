"""API · 그래프 공용 — 작업 읽기 · 잡 넣기(찾기 · 분석) · 잡 상태와 작업 상태 맞추기."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.context import current_user
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import TERMINAL, jobs

from . import config, rules, service
from . import store as R

log = logging.getLogger("winmate.competitor.deps")
SERVICE = config.SERVICE


async def load(aid: str, *, owner_check: bool = True) -> dict[str, Any]:
    doc = await R.call(R.get_analysis, aid)
    if doc is None:
        raise service.not_found("경쟁사 분석 작업", aid)
    if owner_check:
        user = current_user()
        if user.id not in ("system",) and doc.get("owner_id") not in (user.id, "system") and not _internal_caller():
            raise ApiError(404, "NOT_FOUND", "경쟁사 분석 작업을 찾을 수 없어요", {"id": aid})
    return doc


def _internal_caller() -> bool:
    from winmate_common import context

    return bool(context.caller_var.get())


async def load_version(doc: dict[str, Any], n: int | None = None) -> dict[str, Any] | None:
    n = int(n or doc.get("result_version") or 0)
    if not n:
        return None
    return await R.call(R.get_version, doc["id"], n)


def new_job_id() -> str:
    """잡 id 를 먼저 만들어 작업 문서에 적은 뒤 잡을 넣는다 — 워커가 먼저 끝내도 상태가 거꾸로 덮이지 않게."""
    return new_id("job")


async def enqueue(kind: str, payload: dict[str, Any], doc: dict[str, Any], *, job_id: str | None = None) -> str:
    job = await jobs().enqueue(SERVICE, kind, {"analysis_id": doc["id"], **payload}, title=service.display_title(doc), ref=doc["id"],
                               project_id=doc.get("project_id"), job_id=job_id)
    return job.id


async def job_active(job_id: str | None) -> bool:
    if not job_id:
        return False
    j = await jobs().get(job_id)
    return bool(j and j.status not in TERMINAL)


async def cancel_job(job_id: str | None) -> None:
    if job_id and await job_active(job_id):
        await jobs().cancel(job_id)


async def start_find(doc: dict[str, Any], *, auto: bool = False) -> str:
    """찾기 잡(이미 돌고 있으면 취소 후 새로)."""
    await cancel_job(doc.get("current_job_id"))
    job_id = new_job_id()
    from .graphs.find import lines

    def upd(d: dict[str, Any]) -> None:
        d["status"] = "finding"
        d["current_job_id"] = job_id
        d["current_job_kind"] = "ca.find"
        d["last_screen"] = "finding"
        d["ask"] = None
        f = d.setdefault("find", {})
        f.update(error=None, candidates_so_far=0, started_at=now_iso(), line2=None, line3=None)
        f["lines"] = lines(d, 1)

    saved = await R.call(R.update_analysis, doc["id"], upd)
    try:
        await enqueue("ca.find", {"auto": auto}, saved, job_id=job_id)
    except Exception:
        await R.call(R.update_analysis, doc["id"], lambda d: d.update(status="draft", current_job_id=None, current_job_kind=None)
                     if d.get("current_job_id") == job_id else None)
        raise
    await service.register(saved)
    return job_id


def initial_run(doc: dict[str, Any], mode: str, targets: list[dict[str, Any]]) -> dict[str, Any]:
    crit = rules.criteria_summary(service.enabled_criteria(doc))
    comps = [{"id": c["id"], "letter": c["letter"], "display": f"경쟁사 {c['letter']}", "state": "wait", "done_facts": [], "current_fact": None,
              "text": service.run_line(c["letter"], "wait", [], None)} for c in targets]
    eta = rules.eta_analyze_s(len(targets))
    return {"competitors": comps, "criteria": crit, "pct": 0, "eta_s": eta, "eta_label": f"약 {rules.eta_minutes(len(targets))}분",
            "mode": mode, "title": f"{len(targets)}곳을 분석하는 중"}


async def start_run(doc: dict[str, Any], mode: str, competitor_ids: list[str] | None = None, *, supersede: bool = False) -> str:
    """분석 잡(ca.analyze). 실행 중이면 409 RUN_IN_PROGRESS(기준 바꾸기는 supersede — 지금 잡을 끝내고 사실을 재사용해 다시)."""
    prev = doc.get("current_job_id")
    if prev and await job_active(prev):
        if not supersede:
            raise ApiError(409, "RUN_IN_PROGRESS", "이미 분석하고 있어요", {"job_id": prev})
        await jobs().cancel(prev)
    on = service.on_competitors(doc)
    if not on:
        raise ApiError(422, "NO_COMPETITORS", "켜진 경쟁사가 없어요. 한 곳 이상 켜 주세요")
    if not service.enabled_criteria(doc):
        raise ApiError(422, "NO_CRITERIA", "켜진 비교 기준이 없어요")
    job_id = new_job_id()
    before = {k: doc.get(k) for k in ("status", "current_job_id", "current_job_kind", "last_screen", "stopped", "run")}

    def upd(d: dict[str, Any]) -> None:
        d["status"] = "analyzing"
        d["current_job_id"] = job_id
        d["current_job_kind"] = "ca.analyze"
        d["last_screen"] = "run"
        d["stopped"] = None
        d["run"] = initial_run(d, mode, service.on_competitors(d))

    saved = await R.call(R.update_analysis, doc["id"], upd)
    try:
        await enqueue("ca.analyze", {"mode": mode, "competitor_ids": list(competitor_ids or []), "prev_job_id": prev if supersede else None}, saved,
                      job_id=job_id)
    except Exception:
        await R.call(R.update_analysis, doc["id"], lambda d: d.update(before) if d.get("current_job_id") == job_id else None)
        raise
    await service.register(saved)
    return job_id


async def reconcile(doc: dict[str, Any]) -> dict[str, Any]:
    """잡이 대기 중 취소 · 워커 유실 등으로 끝났는데 작업 상태가 남아 있으면 맞춘다."""
    st = doc.get("status")
    jid = doc.get("current_job_id")
    if st not in ("finding", "ask", "analyzing") or not jid:
        return doc
    j = await jobs().get(jid)
    if j is None or j.status not in TERMINAL:
        return doc
    if j.status == "succeeded":
        return doc
    if st in ("finding", "ask"):
        new = "draft" if j.status == "canceled" else "failed"
    else:
        new = "stopped" if (j.status == "canceled" and doc.get("result_version")) else ("confirming" if j.status == "canceled" else "failed")

    def upd(d: dict[str, Any]) -> None:
        if d.get("current_job_id") != jid:
            return
        d["status"] = new
        d["current_job_id"] = None
        d["current_job_kind"] = None
        d["ask"] = None
        if new == "failed":
            d.setdefault("find", {})["error"] = (j.error or {}).get("message") or "경쟁사를 찾지 못했어요"

    doc = await R.call(R.update_analysis, doc["id"], upd)
    await service.register(doc)
    return doc
