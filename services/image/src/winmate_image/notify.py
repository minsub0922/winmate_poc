"""run 마무리 · 실패 · 취소 · 입력 대기 표시와 완료 알림(§4.6 · AC17: notify=true 면 정확히 1번, 링크 = 결과 화면)."""
from __future__ import annotations

import logging
from typing import Any

from winmate_common.ids import now_iso
from winmate_common.jobs import jobs

from . import views
from .service import refresh_work
from .store import repo

log = logging.getLogger("winmate.image.notify")


def result_route(run: dict[str, Any], shots: list[dict[str, Any]]) -> str:
    wid = run["work_id"]
    k = run.get("kind")
    if k == "variants" and run.get("base_image_id"):
        return views.route_variants(wid, run["base_image_id"])
    if k == "edit" and run.get("base_image_id"):
        return views.route_edit(wid, run["base_image_id"])
    if k == "renditions":
        done = [s for s in shots if s.get("status") == "done"]
        return views.route_result(wid, done[0]["id"] if done else run.get("base_image_id"))
    return views.route_result(wid)


async def _notify_once(run: dict[str, Any], done: int, shots: list[dict[str, Any]]) -> None:
    if not run.get("notify", True) or run.get("notified"):
        return
    work = await repo().get("works", run["work_id"]) or {}
    if work.get("internal"):
        return
    title = work.get("title") or run.get("title") or "이미지"
    unit = "장" if run.get("kind") != "renditions" else "개 비율"
    data = {"type": "image_run_done", "job_id": run.get("job_id"), "service": "image", "kind": run.get("kind"),
            "title": f"{title} · {done}{unit} 생성 완료", "ref": run["id"], "status": "succeeded",
            "route": result_route(run, shots), "work_id": run["work_id"], "run_id": run["id"]}
    try:
        await jobs().push_notification(run.get("owner") or "system", data)
        await repo().patch("runs", run["id"], {"notified": True})
    except Exception as exc:  # noqa: BLE001
        log.warning("완료 알림 실패: %s", exc)


async def finish_run(run_id: str) -> dict[str, Any] | None:
    run = await repo().get("runs", run_id)
    if run is None:
        return None
    if run.get("status") == "canceled":
        await refresh_work(run["work_id"])
        return run
    shots = await repo().all("images", where={"run_id": run_id})
    done = sum(1 for s in shots if s.get("status") == "done")
    failed = [s for s in shots if s.get("status") == "failed"]
    if run.get("kind") == "edit":
        regions = [r for r in await repo().all("regions", where={"image_id": run.get("base_image_id") or ""}) if r.get("run_id") == run_id]
        ok = any(r.get("status") == "applied" for r in regions) or (not regions and run.get("edit_ok"))
        status = "succeeded" if ok else "failed"
        err = None if ok else {"code": "EDIT_FAILED", "message": next((r.get("error") for r in regions if r.get("error")),
                                                                        "수정을 적용하지 못했어요")}
        done = sum(1 for r in regions if r.get("status") == "applied") or (1 if ok else 0)
    elif shots and done == 0 and failed:
        status = "failed"
        err = {"code": (failed[0].get("fail_reason") or "model_error").upper(), "message": failed[0].get("error") or "이미지 모델이 응답하지 않아요"}
    else:
        status, err = "succeeded", None
    upd: dict[str, Any] = {"status": status, "phase": "done", "finished_at": now_iso(), "done": done}
    if err:
        upd["error"] = err
    saved = await repo().patch("runs", run_id, upd) or run
    if status == "succeeded":
        await _notify_once(saved, done, shots)
    await refresh_work(run["work_id"])
    return saved


async def fail_run(run_id: str, code: str, message: str) -> None:
    run = await repo().get("runs", run_id)
    if run is None:
        return
    for s in await repo().all("images", where={"run_id": run_id}):
        if s.get("status") in ("waiting", "composing", "rendering", "qc", "held"):
            await repo().patch("images", s["id"], {"status": "failed", "stage_label": "실패", "error": message})
    await repo().patch("runs", run_id, {"status": "failed", "phase": "done", "finished_at": now_iso(),
                                        "error": {"code": code, "message": message}})
    if run.get("kind") == "edit":
        for r in await repo().all("regions", where={"image_id": run.get("base_image_id") or ""}):
            if r.get("run_id") == run_id and r.get("status") == "applying":
                await repo().patch("regions", r["id"], {"status": "failed", "error": message})
    await refresh_work(run["work_id"])


async def cancel_run(run_id: str) -> None:
    run = await repo().get("runs", run_id)
    if run is None:
        return
    for s in await repo().all("images", where={"run_id": run_id}):
        if s.get("status") in ("waiting", "composing", "rendering", "qc", "held"):
            await repo().patch("images", s["id"], {"status": "canceled", "stage_label": "취소됨"})
    if run.get("kind") == "edit":
        for r in await repo().all("regions", where={"image_id": run.get("base_image_id") or ""}):
            if r.get("run_id") == run_id and r.get("status") == "applying":
                await repo().patch("regions", r["id"], {"status": "pending"})
    await repo().patch("runs", run_id, {"status": "canceled", "phase": "done", "finished_at": run.get("finished_at") or now_iso()})
    await refresh_work(run["work_id"])


async def mark_awaiting(run_id: str) -> None:
    run = await repo().get("runs", run_id)
    if run is None:
        return
    held = sum(1 for s in await repo().all("images", where={"run_id": run_id}) if s.get("status") == "held")
    await repo().patch("runs", run_id, {"status": "awaiting_input", "phase": "await", "held": held})
    await refresh_work(run["work_id"])
