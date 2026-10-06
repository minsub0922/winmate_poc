"""API 공용 도우미 — 시트 읽기(잡 상태 맞추기) · 화면 문서 · 잡 넣기 · 매일 재확인 예약."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from winmate_common.errors import ApiError
from winmate_common.jobs import jobs

from . import config, ops, repo
from . import sheet as S
from .links import links_of

log = logging.getLogger("winmate.spec.api")

RUN_KINDS = ("spec_generate", "spec_recheck")


async def load(sid: str) -> dict[str, Any]:
    s = await repo.aget("sheets", sid)
    if s is None:
        raise ApiError(404, "NOT_FOUND", f"Spec 시트를 찾을 수 없어요: {sid}", {"resource": "sheet", "id": sid})
    return await ops.reconcile_job(s)


async def doc(s: dict[str, Any]) -> dict[str, Any]:
    links = await repo.run(links_of, s["id"])
    return S.to_doc(s, links=links)


async def doc_of(sid: str) -> dict[str, Any]:
    return await doc(await load(sid))


def ensure_no_run(s: dict[str, Any]) -> None:
    aj = s.get("active_job") or {}
    if aj and aj.get("kind") in RUN_KINDS and aj.get("status") in ("queued", "running"):
        raise ApiError(409, "RUN_IN_PROGRESS", "이 시트에서 생성 · 재확인이 아직 진행 중이에요. 끝난 뒤 다시 시도해 주세요.", {"job_id": aj.get("id")})


async def enqueue(sid: str, kind: str, payload: dict[str, Any], *, title: str, set_active: bool = True,
                  before: Any = None) -> str:
    """잡을 넣고(시트 active_job 표시) job_id 를 돌려준다. before(fn) 은 같은 쓰기 안에서 시트를 고친다."""
    s = await repo.amust("sheets", sid)
    job = await jobs().enqueue("spec", kind, {"sheet_id": sid, **payload}, title=title, ref=sid, project_id=s.get("project_id"))
    if set_active or before:
        def fn(x: dict[str, Any]) -> None:
            if before:
                before(x)
            if set_active:
                x["active_job"] = {"id": job.id, "kind": kind, "status": "queued", "progress": 0}
                if kind in RUN_KINDS:
                    x["last_job_id"] = job.id
            S.refresh_status(x, x["id"])

        saved, _ = await repo.amutate("sheets", sid, fn)
        await ops.publish(saved)
    return job.id


def next_kst_6am(now: datetime | None = None) -> float:
    now = (now or config.now()).astimezone(config.KST)
    run = now.replace(hour=6, minute=0, second=0, microsecond=0)
    if run <= now:
        run += timedelta(days=1)
    return run.timestamp()


_scheduled = False


async def ensure_daily_schedule(force: bool = False) -> None:
    """매일 06:00 KST 카탈로그 재확인(jobs 예약 wm:sched, 같은 id 로 덮어써 하나만)."""
    global _scheduled
    if _scheduled and not force:
        return
    try:
        await jobs().schedule("spec", "spec_recheck", {"all": True, "reschedule": True}, next_kst_6am(), title="사내 카탈로그 재확인",
                              owner="system", schedule_id="sch_spec_catalog_daily")
        _scheduled = True
    except Exception as exc:  # noqa: BLE001
        log.info("재확인 예약 실패(나중에 다시): %s", exc)


async def preferences(user_id: str) -> dict[str, Any] | None:
    return await repo.aget("preferences", user_id)


def check_if_match(if_match: str | None, s: dict[str, Any]) -> None:
    """버전이 오르는 쓰기는 `If-Match: {version}` 을 받으면 검사한다(§6 공통 — 409 VERSION_CONFLICT)."""
    if not if_match:
        return
    v = if_match.strip()
    if v.startswith("W/"):
        v = v[2:]
    v = v.strip().strip('"')
    try:
        n = int(v)
    except ValueError:
        return
    cur = int(s.get("doc_version") or 0)
    if n != cur:
        raise ApiError(409, "VERSION_CONFLICT", "시트가 그사이 바뀌었어요. 새로 불러온 뒤 다시 시도해 주세요.", {"current_version": cur})


def generate_running(s: dict[str, Any]) -> dict[str, Any] | None:
    aj = s.get("active_job") or {}
    if aj and aj.get("kind") == "spec_generate" and aj.get("status") in ("queued", "running"):
        return aj
    return None
