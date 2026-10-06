"""워커 안 순서 · 동시성 — 사용자당 진행 run(IMAGE_MAX_RUNNING_PER_USER) · 워커 전체 동시 job(IMAGE_WORKER_CONCURRENCY).

jobs 워커는 잡을 바로 집어 오지만, run 은 차례가 올 때까지 status='queued'(「내 대기열」)로 기다린다.
차례 = 같은 사용자의 queued run 중 queued_at 이 가장 빠르고, 진행 중인 run 이 한도보다 적을 때.
기다리는 동안 취소(jobs 취소 플래그 · run.status='canceled')를 확인한다.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from winmate_common.ids import now_iso
from winmate_common.jobs import TERMINAL, JobCanceled, JobContext, jobs

from . import config
from .store import repo

log = logging.getLogger("winmate.image.scheduler")

_claim_lock: asyncio.Lock | None = None
_heavy: tuple[int, asyncio.Semaphore] | None = None
_light: tuple[int, asyncio.Semaphore] | None = None
WAIT_LIMIT_S = 30 * 60


def _lock() -> asyncio.Lock:
    global _claim_lock
    if _claim_lock is None:
        _claim_lock = asyncio.Lock()
    return _claim_lock


def _sem(kind: str) -> asyncio.Semaphore:
    global _heavy, _light
    if kind == "heavy":
        n = config.worker_concurrency()
        if _heavy is None or _heavy[0] != n:
            _heavy = (n, asyncio.Semaphore(n))
        return _heavy[1]
    n = config.light_concurrency()
    if _light is None or _light[0] != n:
        _light = (n, asyncio.Semaphore(n))
    return _light[1]


@asynccontextmanager
async def slot(kind: str = "heavy") -> AsyncIterator[None]:
    sem = _sem(kind)
    async with sem:
        yield


async def _alive(run: dict[str, Any]) -> bool:
    jid = run.get("job_id")
    if not jid:
        return False
    try:
        job = await jobs().get(jid)
    except Exception:  # noqa: BLE001
        return True
    return job is not None and job.status not in TERMINAL


async def wait_turn(ctx: JobContext, run_id: str, *, poll_s: float = 0.4) -> dict[str, Any]:
    """차례가 오면 run 을 running 으로 바꾸고 돌려준다."""
    waited = 0.0
    while True:
        if await jobs().is_canceled(ctx.job.id):
            raise JobCanceled()
        run = await repo().get("runs", run_id)
        if run is None:
            raise JobCanceled()
        if run.get("status") == "canceled":
            raise JobCanceled()
        async with _lock():
            mine = await repo().all("runs", where={"owner": run.get("owner"), "status": ["queued", "running"]})
            key = (run.get("queued_at") or "", run.get("created_at") or "")
            running = [r for r in mine if r["id"] != run_id and r.get("status") == "running" and await _alive(r)]
            ahead = [r for r in mine if r["id"] != run_id and r.get("status") == "queued"
                     and (r.get("queued_at") or "", r.get("created_at") or "") < key and await _alive(r)]
            if (len(running) < config.max_running_per_user() and not ahead) or waited > WAIT_LIMIT_S:
                def fn(doc: dict[str, Any]) -> None:
                    doc["status"] = "running"
                    doc["started_at"] = doc.get("started_at") or now_iso()
                    if doc.get("phase") in (None, "queued"):
                        doc["phase"] = "product_fit"

                claimed = await repo().mutate("runs", run_id, fn)
                return claimed or run
        await asyncio.sleep(poll_s)
        waited += poll_s
