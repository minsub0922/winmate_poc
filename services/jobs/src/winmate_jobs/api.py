"""jobs API — Redis 잡 상태 · 진행 이벤트(SSE) · 취소 · 사람 입력 · 조종 메모 · 알림 · 예약 실행.

잡은 기능 서비스가 `winmate_common.jobs.jobs().enqueue()` 로 Redis 에 직접 넣는다(메시지 큐).
이 서비스는 그 잡을 읽고 제어하는 공개 API 와 예약 실행 루프를 맡는다.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Literal

from fastapi import APIRouter, Header, Query, Request
from pydantic import BaseModel, Field

from winmate_common.context import current_user
from winmate_common.errors import ApiError, not_found
from winmate_common.jobs import TERMINAL, JobRecord, jobs
from winmate_common.sse import sse_response

router = APIRouter(prefix="/v1")

JobStatus = Literal["queued", "running", "awaiting_input", "succeeded", "failed", "canceled"]


class JobError(BaseModel):
    code: str
    message: str


class Job(BaseModel):
    id: str
    service: str
    kind: str
    status: JobStatus
    progress: int = Field(ge=0, le=100)
    message: str = ""
    title: str = ""
    ref: str | None = None
    owner: str
    project_id: str | None = None
    result: dict[str, Any] | None = None
    error: JobError | None = None
    input_request: dict[str, Any] | None = None
    attempts: int = 0
    created_at: str
    updated_at: str
    started_at: str | None = None
    finished_at: str | None = None
    queue_position: int | None = Field(default=None, description="대기 중이면 서비스 큐 안 순서(1부터)")


class JobList(BaseModel):
    items: list[Job]
    next_cursor: str | None = None


class JobEvent(BaseModel):
    id: str
    type: str
    data: dict[str, Any]
    ts: str | None = None


class JobEventList(BaseModel):
    items: list[JobEvent]


class InputBody(BaseModel):
    answer: Any = Field(description="awaiting_input 에 대한 답(질문 형식에 맞는 값)")


class MemoBody(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class Memo(BaseModel):
    text: str
    author: str
    at: str


class MemoList(BaseModel):
    items: list[Memo]


class Notification(BaseModel):
    id: str
    type: str
    job_id: str | None = None
    service: str | None = None
    kind: str | None = None
    title: str | None = None
    ref: str | None = None
    status: str | None = None
    at: str
    read: bool = False
    data: dict[str, Any] = Field(default_factory=dict)


class NotificationList(BaseModel):
    items: list[Notification]
    unread: int


class ReadBody(BaseModel):
    up_to_id: str | None = Field(default=None, description="이 알림까지 읽음(없으면 전부)")


class ScheduleBody(BaseModel):
    service: str
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    run_at: str | None = Field(default=None, description="ISO 8601 실행 시각")
    delay_s: float | None = Field(default=None, ge=0, description="지금부터 몇 초 뒤(run_at 대신)")
    title: str = ""
    ref: str | None = None


class Schedule(BaseModel):
    id: str
    service: str
    kind: str
    payload: dict[str, Any]
    title: str = ""
    ref: str | None = None
    owner: str
    run_at: float
    run_at_iso: str
    created_at: str


class ScheduleList(BaseModel):
    items: list[Schedule]


def _job_out(j: JobRecord, queue_position: int | None = None) -> Job:
    d = j.public()
    err = d.get("error")
    if err:
        d["error"] = {"code": str(err.get("code", "ERROR")), "message": str(err.get("message", ""))}
    return Job(**d, queue_position=queue_position)


async def _get_or_404(job_id: str) -> JobRecord:
    j = await jobs().get(job_id)
    if j is None:
        raise not_found("잡", job_id)
    return j


@router.get("/jobs", response_model=JobList, tags=["jobs"])
async def list_jobs(
    owner: str = Query("me", description="me | all | <user id>"),
    service: str | None = None,
    status: JobStatus | None = None,
    limit: int = Query(30, ge=1, le=200),
    cursor: str | None = Query(None, description="이전 응답의 next_cursor"),
) -> JobList:
    who = current_user().id if owner == "me" else (None if owner == "all" else owner)
    before = float(cursor) if cursor else None
    items = await jobs().list(owner=who, service=service, status=status, limit=limit + 1, before=before)
    nxt = None
    if len(items) > limit:
        items = items[:limit]
        last = items[-1]
        score = await jobs().r.zscore("wm:jobs:all", last.id)
        nxt = str(score) if score is not None else None
    out = []
    for j in items:
        out.append(_job_out(j, await jobs().queue_position(j) if j.status == "queued" else None))
    return JobList(items=out, next_cursor=nxt)


@router.get("/jobs/{job_id}", response_model=Job, tags=["jobs"])
async def get_job(job_id: str) -> Job:
    j = await _get_or_404(job_id)
    return _job_out(j, await jobs().queue_position(j) if j.status == "queued" else None)


@router.get("/jobs/{job_id}/events/list", response_model=JobEventList, tags=["jobs"])
async def list_events(job_id: str, after: str = "0") -> JobEventList:
    await _get_or_404(job_id)
    evs = await jobs().events(job_id, after=after)
    return JobEventList(items=[JobEvent(id=eid, **e) for eid, e in evs])


@router.get(
    "/jobs/{job_id}/events",
    tags=["jobs"],
    responses={200: {"content": {"text/event-stream": {}}, "description": "SSE: event=<type>, id=<stream id>, data=<JSON>"}},
)
async def stream_events(
    job_id: str,
    request: Request,
    after: str | None = Query(None, description="이 이벤트 다음부터(없으면 처음부터)"),
    last_event_id: str | None = Header(None, alias="Last-Event-ID"),
):
    await _get_or_404(job_id)
    start = last_event_id or after or "0"

    async def gen() -> AsyncIterator[dict[str, Any]]:
        cursor = start
        # 이미 쌓인 이벤트 먼저
        for eid, e in await jobs().events(job_id, after=cursor):
            cursor = eid
            yield {"event": e["type"], "id": eid, "data": {**e["data"], "_ts": e.get("ts")}}
            if e["type"] == "done":
                return
        while True:
            if await request.is_disconnected():
                return
            evs = await jobs().events(job_id, after=cursor, block_ms=10000)
            if not evs:
                j = await jobs().get(job_id)
                if j is None:
                    return
                if j.status in TERMINAL:
                    # done 이벤트를 놓쳤으면(만료 등) 상태로 마무리
                    yield {"event": "done", "id": cursor, "data": {"status": j.status}}
                    return
                continue
            for eid, e in evs:
                cursor = eid
                yield {"event": e["type"], "id": eid, "data": {**e["data"], "_ts": e.get("ts")}}
                if e["type"] == "done":
                    return

    return sse_response(gen())


@router.post("/jobs/{job_id}/cancel", response_model=Job, tags=["jobs"])
async def cancel_job(job_id: str) -> Job:
    await _get_or_404(job_id)
    j = await jobs().cancel(job_id)
    return _job_out(j)  # type: ignore[arg-type]


@router.post("/jobs/{job_id}/input", response_model=Job, tags=["jobs"])
async def provide_input(job_id: str, body: InputBody) -> Job:
    await _get_or_404(job_id)
    try:
        j = await jobs().provide_input(job_id, body.answer)
    except ValueError as exc:
        raise ApiError(409, "NOT_AWAITING_INPUT", str(exc)) from None
    return _job_out(j)


@router.post("/jobs/{job_id}/memos", response_model=Memo, status_code=201, tags=["jobs"])
async def add_memo(job_id: str, body: MemoBody) -> Memo:
    j = await _get_or_404(job_id)
    if j.status in TERMINAL:
        raise ApiError(409, "JOB_FINISHED", "이미 끝난 작업입니다")
    m = await jobs().add_memo(job_id, body.text)
    return Memo(**m)


@router.get("/jobs/{job_id}/memos", response_model=MemoList, tags=["jobs"])
async def list_memos(job_id: str) -> MemoList:
    await _get_or_404(job_id)
    return MemoList(items=[Memo(**m) for m in await jobs().memos(job_id)])


# ── 알림 ─────────────────────────────────────────────────

def _read_key(user: str) -> str:
    return f"wm:notify:read:{user}"


def _id_gt(a: str, b: str) -> bool:
    pa, pb = (tuple(int(x) for x in s.split("-")) for s in (a, b))
    return pa > pb


@router.get("/notifications", response_model=NotificationList, tags=["notifications"])
async def list_notifications(limit: int = Query(30, ge=1, le=200)) -> NotificationList:
    user = current_user().id
    last_read = await jobs().r.get(_read_key(user)) or "0-0"
    rows = await jobs().notifications(user, limit=limit)
    items = []
    unread = 0
    for eid, d in rows:
        read = not _id_gt(eid, last_read)
        if not read:
            unread += 1
        known = {k: d.get(k) for k in ("type", "job_id", "service", "kind", "title", "ref", "status")}
        extra = {k: v for k, v in d.items() if k not in known and k != "at"}
        items.append(Notification(id=eid, at=d.get("at") or "", read=read, data=extra,
                                  **{k: (str(v) if v is not None else None) for k, v in known.items() if k != "type"},
                                  type=str(d.get("type") or "info")))
    return NotificationList(items=items, unread=unread)


@router.post("/notifications/read", status_code=204, tags=["notifications"])
async def mark_read(body: ReadBody) -> None:
    user = current_user().id
    up_to = body.up_to_id
    if not up_to:
        rows = await jobs().notifications(user, limit=1)
        up_to = rows[0][0] if rows else "0-0"
    await jobs().r.set(_read_key(user), up_to)


# ── 예약 실행(서비스 간 호출 전용) ───────────────────────

def _sched_out(e: dict[str, Any]) -> Schedule:
    run_at = float(e.get("run_at", 0))
    return Schedule(
        id=e["id"], service=e["service"], kind=e["kind"], payload=e.get("payload") or {}, title=e.get("title") or "",
        ref=e.get("ref"), owner=e.get("owner") or "system", run_at=run_at,
        run_at_iso=datetime.fromtimestamp(run_at, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        created_at=e.get("created_at") or "",
    )


@router.post("/schedules", response_model=Schedule, status_code=201, tags=["internal"])
async def create_schedule(body: ScheduleBody) -> Schedule:
    if body.run_at:
        try:
            run_at = datetime.fromisoformat(body.run_at.replace("Z", "+00:00")).timestamp()
        except ValueError:
            raise ApiError(400, "INVALID_ARGUMENT", "run_at 형식이 올바르지 않습니다") from None
    elif body.delay_s is not None:
        run_at = time.time() + body.delay_s
    else:
        raise ApiError(400, "INVALID_ARGUMENT", "run_at 또는 delay_s 가 필요합니다")
    sid = await jobs().schedule(body.service, body.kind, body.payload, run_at, title=body.title, ref=body.ref)
    e = next(s for s in await jobs().schedules() if s["id"] == sid)
    return _sched_out(e)


@router.get("/schedules", response_model=ScheduleList, tags=["internal"])
async def list_schedules(service: str | None = None, ref: str | None = None) -> ScheduleList:
    return ScheduleList(items=[_sched_out(e) for e in await jobs().schedules(service=service, ref=ref)])


@router.delete("/schedules/{schedule_id}", status_code=204, tags=["internal"])
async def delete_schedule(schedule_id: str) -> None:
    if not await jobs().unschedule(schedule_id):
        raise not_found("예약", schedule_id)


async def scheduler_loop(stop: asyncio.Event, interval_s: float = 5.0) -> None:
    import logging

    log = logging.getLogger("winmate.jobs.scheduler")
    while not stop.is_set():
        try:
            started = await jobs().run_due_schedules()
            if started:
                log.info("예약 실행 %d건: %s", len(started), started)
        except Exception as exc:  # noqa: BLE001
            log.warning("scheduler: %s", exc)
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
        except asyncio.TimeoutError:
            pass
