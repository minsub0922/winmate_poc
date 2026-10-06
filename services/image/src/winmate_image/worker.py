"""image 워커 — Redis 큐(wm:q:image) 소비. `python -m winmate_image.worker`.

잡 종류
- run: 생성 run 하나(payload {run_id}) — kind 에 따라 그래프 image.generate · image.edit · image.variants · image.renditions · image.render.
  사용자당 진행 run 은 IMAGE_MAX_RUNNING_PER_USER(1) — 차례가 올 때까지 run.status='queued'(「내 대기열」). 워커 전체 동시 생성은
  IMAGE_WORKER_CONCURRENCY(2), run 안 시안 동시 IMAGE_SHOT_CONCURRENCY(2).
- recognize_photo: 현장 사진 인식(payload {photo_id}) — 그래프 image.recognize_photo
- analyze_reference: 참조 이미지 분석(payload {ref_id})
"""
from __future__ import annotations

import logging
import os
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.graph import run_graph
from winmate_common.jobs import AwaitingInput, JobCanceled, JobContext, run_worker

from . import analysis, llm, notify, scheduler
from .graphs import edit, generate, recognize, render, renditions, variants
from .store import repo

log = logging.getLogger("winmate.image.worker")

GRAPHS = {"initial": generate, "composite": generate, "alternatives": generate, "edit": edit, "variants": variants,
          "renditions": renditions, "render_api": render}


async def _noop(ctx: JobContext) -> dict:
    await ctx.progress(100, "완료")
    return {"ok": True}


async def run_job(ctx: JobContext) -> dict[str, Any] | None:
    run_id = ctx.payload.get("run_id")
    run = await repo().get("runs", run_id)
    if run is None:
        raise ApiError(404, "NOT_FOUND", f"생성 run 을 찾을 수 없습니다: {run_id}")
    if run.get("status") in ("succeeded", "failed", "canceled"):
        return {"run_id": run_id, "status": run.get("status")}
    try:
        run = await scheduler.wait_turn(ctx, run_id)
        mod = GRAPHS.get(run.get("kind") or "initial", generate)
        async with scheduler.slot("heavy"):
            await run_graph(ctx, mod.build(), {"run_id": run_id}, step_labels=getattr(mod, "LABELS", None))
    except AwaitingInput:
        await notify.mark_awaiting(run_id)
        raise
    except JobCanceled:
        await notify.cancel_run(run_id)
        raise
    except llm.QuotaExceeded as exc:
        await notify.fail_run(run_id, "QUOTA_EXCEEDED", exc.message)
        raise ApiError(429, "QUOTA_EXCEEDED", exc.message) from exc
    except Exception as exc:  # noqa: BLE001
        log.exception("run %s 실패", run_id)
        msg = getattr(exc, "message", None) or "이미지 모델이 응답하지 않아요"
        if isinstance(exc, RuntimeError):
            msg = str(exc)
        await notify.fail_run(run_id, getattr(exc, "code", None) or "RUN_FAILED", msg)
        raise
    run = await repo().get("runs", run_id) or {}
    shots = await repo().all("images", where={"run_id": run_id})
    return {"run_id": run_id, "status": run.get("status"), "image_ids": [s["id"] for s in shots if s.get("status") == "done"]}


async def recognize_photo_job(ctx: JobContext) -> dict[str, Any] | None:
    pid = ctx.payload.get("photo_id")
    async with scheduler.slot("light"):
        try:
            await run_graph(ctx, recognize.build(), {"photo_id": pid})
        except JobCanceled:
            raise
        except Exception:
            await repo().patch("photos", pid, {"status": "failed", "message": "인식하지 못했어요 · 다시 인식"})
            raise
    p = await repo().get("photos", pid) or {}
    return {"photo_id": pid, "status": p.get("status")}


async def analyze_reference_job(ctx: JobContext) -> dict[str, Any] | None:
    rid = ctx.payload.get("ref_id")
    async with scheduler.slot("light"):
        ref = await analysis.analyze_reference(rid)
    return {"ref_id": rid, "send_mode": (ref or {}).get("send_mode")}


HANDLERS = {"noop": _noop, "run": run_job, "recognize_photo": recognize_photo_job, "analyze_reference": analyze_reference_job}


def main() -> None:
    # 기다리는 run 은 가벼운 task 라 워커 task 수는 넉넉히(실제 생성 동시 수는 scheduler 의 IMAGE_WORKER_CONCURRENCY)
    run_worker("image", HANDLERS, concurrency=int(os.environ.get("IMAGE_WORKER_TASKS", "12")))


if __name__ == "__main__":
    main()
