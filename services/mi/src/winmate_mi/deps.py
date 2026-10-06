"""API 공용 도우미 — 작업 읽기 · 잡 넣기 · 실행 중 확인."""
from __future__ import annotations

from typing import Any

from winmate_common.errors import ApiError
from winmate_common.jobs import TERMINAL, jobs

from . import service
from . import store as R


async def load(aid: str) -> dict[str, Any]:
    doc = await R.call(R.get_analysis, aid)
    if doc is None:
        raise service.not_found("분석 작업", aid)
    return doc


async def load_version(doc: dict[str, Any], n: int | None = None) -> dict[str, Any]:
    n = int(n or doc.get("result_version") or 0)
    if not n:
        raise ApiError(404, "NOT_FOUND", "아직 분석 결과가 없어요", {"id": doc["id"]})
    v = await R.call(R.get_version, doc["id"], n)
    if v is None:
        raise ApiError(404, "NOT_FOUND", f"v{n} 결과를 찾을 수 없어요", {"id": doc["id"], "version": n})
    return v


async def enqueue(kind: str, payload: dict[str, Any], doc: dict[str, Any], title: str | None = None) -> str:
    job = await jobs().enqueue("mi", kind, payload, title=title or (doc.get("title") or service.default_title(doc) or "Market Intelligence"),
                               ref=doc["id"], project_id=doc.get("project_id"))
    return job.id


async def job_active(job_id: str | None) -> bool:
    if not job_id:
        return False
    j = await jobs().get(job_id)
    return bool(j and j.status not in TERMINAL)


async def job_status(job_id: str | None) -> str | None:
    if not job_id:
        return None
    j = await jobs().get(job_id)
    return j.status if j else None


async def start_run(doc: dict[str, Any], mode: str, areas: list[str] | None = None) -> str:
    """분석 잡(mi.analyze)을 넣고 작업을 queued 로. API · 설계 잡(start_analysis) · 재확인 화면이 함께 쓴다."""
    from winmate_common.ids import now_iso

    if doc.get("current_job_id") and await job_active(doc["current_job_id"]):
        raise ApiError(409, "RUN_IN_PROGRESS", "이미 분석하고 있어요", {"job_id": doc["current_job_id"]})
    if not service.areas_of(doc):
        raise ApiError(422, "VALIDATION_FAILED", "분석 범위를 하나 이상 골라 주세요")
    job_id = await enqueue("mi.analyze", {"analysis_id": doc["id"], "mode": mode, "areas": areas or []}, doc)
    doc["status"] = "queued"
    doc["current_job_id"] = job_id
    doc["run"] = {**(doc.get("run") or {}), "job_id": job_id, "mode": mode, "started_at": now_iso(), "stage": "search", "sources_total": 0}
    doc["last_screen"] = "run"
    await R.call(R.put_analysis, doc)
    await service.register(doc)
    return job_id


async def reconcile(doc: dict[str, Any]) -> dict[str, Any]:
    """대기 중에 취소 · 워커 유실로 잡이 끝났는데 작업 상태가 남아 있으면 맞춘다(queued/running → stopped/failed)."""
    st = doc.get("status")
    jid = doc.get("current_job_id")
    if st not in ("queued", "running") or not jid:
        return doc
    j = await jobs().get(jid)
    if j is None or j.status not in TERMINAL:
        return doc
    new = {"canceled": "stopped", "failed": "failed"}.get(j.status)
    if new is None:
        return doc
    doc = await R.call(R.patch_analysis, doc["id"], {"status": new, "current_job_id": None})
    await service.register(doc)
    return doc
