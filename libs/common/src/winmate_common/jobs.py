"""Redis 잡 큐 · 진행 이벤트 · 취소 · 사람 입력 · 조종 메모 · 예약 실행.

기능 서비스 API 가 `await jobs().enqueue(...)` 로 잡을 넣고, 같은 서비스의 워커(`run_worker`)가 처리한다.
화면은 jobs 서비스의 SSE(`/api/jobs/v1/jobs/{id}/events`)로 진행을 받는다.

Redis 키
  wm:job:<id>            해시 — 잡 레코드
  wm:q:<service>         스트림 — 처리 대기(소비 그룹 workers)
  wm:ev:<id>             스트림 — 이벤트(progress|step|log|awaiting_input|result|error|done|memo|status)
  wm:job:<id>:cancel     취소 플래그
  wm:job:<id>:memos      리스트 — 조종 메모(딸깍)
  wm:job:<id>:input      문자열(JSON) — awaiting_input 에 대한 답
  wm:jobs:all|svc:<s>|user:<u>   정렬 집합 — 목록
  wm:notify:<user>       스트림 — 완료 알림
  wm:sched               정렬 집합 — 예약 실행(점수 = 실행 시각)
"""
from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import signal
import socket
import time
import traceback
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import redis.asyncio as aioredis

from .context import current_user, request_id_var, set_user
from .env import settings
from .ids import new_id, now_iso

log = logging.getLogger("winmate.jobs")

JobStatus = Literal["queued", "running", "awaiting_input", "succeeded", "failed", "canceled"]
TERMINAL = {"succeeded", "failed", "canceled"}
EVENT_TTL_S = 7 * 24 * 3600
_redis_factory: Callable[[], aioredis.Redis] | None = None
_redis_singleton: aioredis.Redis | None = None


def set_redis_factory(factory: Callable[[], aioredis.Redis] | None) -> None:
    """테스트용(fakeredis)."""
    global _redis_factory, _redis_singleton
    _redis_factory = factory
    _redis_singleton = None


def redis() -> aioredis.Redis:
    global _redis_singleton
    if _redis_singleton is None:
        _redis_singleton = _redis_factory() if _redis_factory else aioredis.from_url(settings().redis_url, decode_responses=True)
    return _redis_singleton


def _dumps(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


def _loads(v: str | None, default: Any = None) -> Any:
    if v is None or v == "":
        return default
    try:
        return json.loads(v)
    except ValueError:
        return default


@dataclass
class JobRecord:
    id: str
    service: str
    kind: str
    status: JobStatus = "queued"
    progress: int = 0
    message: str = ""
    title: str = ""
    ref: str | None = None
    owner: str = "system"
    owner_name: str = ""
    project_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    input_request: dict[str, Any] | None = None
    attempts: int = 0
    created_at: str = ""
    updated_at: str = ""
    started_at: str | None = None
    finished_at: str | None = None

    def to_redis(self) -> dict[str, str]:
        d = {
            "id": self.id, "service": self.service, "kind": self.kind, "status": self.status,
            "progress": str(self.progress), "message": self.message, "title": self.title,
            "ref": self.ref or "", "owner": self.owner, "owner_name": self.owner_name,
            "project_id": self.project_id or "", "payload": _dumps(self.payload),
            "result": _dumps(self.result) if self.result is not None else "",
            "error": _dumps(self.error) if self.error is not None else "",
            "input_request": _dumps(self.input_request) if self.input_request is not None else "",
            "attempts": str(self.attempts), "created_at": self.created_at, "updated_at": self.updated_at,
            "started_at": self.started_at or "", "finished_at": self.finished_at or "",
        }
        return d

    @classmethod
    def from_redis(cls, h: dict[str, str]) -> "JobRecord":
        return cls(
            id=h["id"], service=h.get("service", ""), kind=h.get("kind", ""),
            status=h.get("status", "queued"),  # type: ignore[arg-type]
            progress=int(h.get("progress") or 0), message=h.get("message", ""), title=h.get("title", ""),
            ref=h.get("ref") or None, owner=h.get("owner") or "system", owner_name=h.get("owner_name", ""),
            project_id=h.get("project_id") or None, payload=_loads(h.get("payload"), {}) or {},
            result=_loads(h.get("result")), error=_loads(h.get("error")), input_request=_loads(h.get("input_request")),
            attempts=int(h.get("attempts") or 0), created_at=h.get("created_at", ""), updated_at=h.get("updated_at", ""),
            started_at=h.get("started_at") or None, finished_at=h.get("finished_at") or None,
        )

    def public(self) -> dict[str, Any]:
        """API 응답용(페이로드는 뺀다)."""
        return {
            "id": self.id, "service": self.service, "kind": self.kind, "status": self.status,
            "progress": self.progress, "message": self.message, "title": self.title, "ref": self.ref,
            "owner": self.owner, "project_id": self.project_id, "result": self.result, "error": self.error,
            "input_request": self.input_request, "attempts": self.attempts, "created_at": self.created_at,
            "updated_at": self.updated_at, "started_at": self.started_at, "finished_at": self.finished_at,
        }


class JobCanceled(Exception):
    pass


class Jobs:
    """잡 레코드·큐·이벤트 조작(서비스 API, 워커, jobs 서비스가 함께 쓴다)."""

    def __init__(self, r: aioredis.Redis | None = None):
        self._r = r

    @property
    def r(self) -> aioredis.Redis:
        return self._r or redis()

    # ── 만들기 ─────────────────────────────────────────
    async def enqueue(
        self,
        service: str,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        title: str = "",
        ref: str | None = None,
        project_id: str | None = None,
        owner: str | None = None,
        owner_name: str | None = None,
        job_id: str | None = None,
    ) -> JobRecord:
        user = current_user()
        now = now_iso()
        job = JobRecord(
            id=job_id or new_id("job"), service=service, kind=kind, title=title, ref=ref, project_id=project_id,
            owner=owner or user.id, owner_name=owner_name or user.name, payload=payload or {},
            created_at=now, updated_at=now, message="대기 중",
        )
        job.payload.setdefault("_request_id", request_id_var.get())
        ts = time.time()
        pipe = self.r.pipeline()
        pipe.hset(f"wm:job:{job.id}", mapping=job.to_redis())
        pipe.zadd("wm:jobs:all", {job.id: ts})
        pipe.zadd(f"wm:jobs:svc:{service}", {job.id: ts})
        pipe.zadd(f"wm:jobs:user:{job.owner}", {job.id: ts})
        await pipe.execute()
        await self.emit(job.id, "status", {"status": "queued", "message": "대기 중"})
        await self.r.xadd(f"wm:q:{service}", {"job_id": job.id, "kind": kind})
        return job

    # ── 읽기 ───────────────────────────────────────────
    async def get(self, job_id: str) -> JobRecord | None:
        h = await self.r.hgetall(f"wm:job:{job_id}")
        return JobRecord.from_redis(h) if h else None

    async def list(
        self, *, owner: str | None = None, service: str | None = None, status: str | None = None,
        limit: int = 50, before: float | None = None,
    ) -> list[JobRecord]:
        key = f"wm:jobs:user:{owner}" if owner else (f"wm:jobs:svc:{service}" if service else "wm:jobs:all")
        maxscore = f"({before}" if before else "+inf"
        ids = await self.r.zrevrangebyscore(key, maxscore, "-inf", start=0, num=max(limit * 4, 50))
        out: list[JobRecord] = []
        for jid in ids:
            j = await self.get(jid)
            if j is None:
                continue
            if service and j.service != service:
                continue
            if status and j.status != status:
                continue
            out.append(j)
            if len(out) >= limit:
                break
        return out

    async def queue_position(self, job: JobRecord) -> int | None:
        """대기 중인 잡의 서비스 큐 안 순서(1부터)."""
        if job.status != "queued":
            return None
        ids = await self.r.zrangebyscore(f"wm:jobs:svc:{job.service}", "-inf", "+inf")
        pos = 0
        for jid in ids:
            st = await self.r.hget(f"wm:job:{jid}", "status")
            if st == "queued":
                pos += 1
            if jid == job.id:
                return pos
        return None

    # ── 갱신·이벤트 ─────────────────────────────────────
    async def update(self, job_id: str, **fields: Any) -> None:
        mapping: dict[str, str] = {"updated_at": now_iso()}
        for k, v in fields.items():
            if k in {"result", "error", "input_request", "payload"}:
                mapping[k] = _dumps(v) if v is not None else ""
            elif v is None:
                mapping[k] = ""
            else:
                mapping[k] = str(v)
        await self.r.hset(f"wm:job:{job_id}", mapping=mapping)

    async def emit(self, job_id: str, type_: str, data: dict[str, Any] | None = None) -> str:
        key = f"wm:ev:{job_id}"
        eid = await self.r.xadd(key, {"type": type_, "data": _dumps(data or {}), "ts": now_iso()}, maxlen=2000, approximate=True)
        await self.r.expire(key, EVENT_TTL_S)
        return eid

    async def events(self, job_id: str, after: str = "0", block_ms: int | None = None, count: int = 200) -> list[tuple[str, dict[str, Any]]]:
        key = f"wm:ev:{job_id}"
        if block_ms is None:
            rows = await self.r.xrange(key, min=f"({after}" if after != "0" else "-", max="+", count=count)
        else:
            res = await self.r.xread({key: after}, block=block_ms, count=count)
            rows = res[0][1] if res else []
        return [(eid, {"type": f.get("type"), "data": _loads(f.get("data"), {}), "ts": f.get("ts")}) for eid, f in rows]

    # ── 제어 ───────────────────────────────────────────
    async def cancel(self, job_id: str) -> JobRecord | None:
        job = await self.get(job_id)
        if job is None or job.status in TERMINAL:
            return job
        await self.r.set(f"wm:job:{job_id}:cancel", "1", ex=EVENT_TTL_S)
        if job.status in ("queued", "awaiting_input"):
            # 워커가 잡고 있지 않으므로 바로 취소 처리
            await self.update(job_id, status="canceled", finished_at=now_iso(), message="취소됨")
            await self.emit(job_id, "status", {"status": "canceled", "message": "취소됨"})
            await self.emit(job_id, "done", {"status": "canceled"})
            await self._notify(await self.get(job_id))  # type: ignore[arg-type]
        else:
            await self.emit(job_id, "log", {"message": "취소 요청을 받았습니다"})
        return await self.get(job_id)

    async def is_canceled(self, job_id: str) -> bool:
        return bool(await self.r.exists(f"wm:job:{job_id}:cancel"))

    async def add_memo(self, job_id: str, text: str, author: str | None = None) -> dict[str, Any]:
        memo = {"text": text, "author": author or current_user().name, "at": now_iso()}
        await self.r.rpush(f"wm:job:{job_id}:memos", _dumps(memo))
        await self.r.expire(f"wm:job:{job_id}:memos", EVENT_TTL_S)
        await self.emit(job_id, "memo", memo)
        return memo

    async def memos(self, job_id: str, start: int = 0) -> list[dict[str, Any]]:
        raw = await self.r.lrange(f"wm:job:{job_id}:memos", start, -1)
        return [_loads(x, {}) for x in raw]

    async def provide_input(self, job_id: str, answer: Any) -> JobRecord:
        job = await self.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.status != "awaiting_input":
            raise ValueError(f"입력을 기다리는 잡이 아닙니다(status={job.status})")
        await self.r.set(f"wm:job:{job_id}:input", _dumps({"answer": answer}), ex=EVENT_TTL_S)
        await self.update(job_id, status="queued", input_request=None, message="입력 받음 · 다시 실행 대기")
        await self.emit(job_id, "status", {"status": "queued", "message": "입력 받음"})
        await self.r.xadd(f"wm:q:{job.service}", {"job_id": job_id, "kind": job.kind, "resume": "1"})
        return await self.get(job_id)  # type: ignore[return-value]

    async def take_input(self, job_id: str) -> tuple[bool, Any]:
        raw = await self.r.getdel(f"wm:job:{job_id}:input")
        if raw is None:
            return False, None
        return True, (_loads(raw, {}) or {}).get("answer")

    # ── 알림 ───────────────────────────────────────────
    async def _notify(self, job: JobRecord) -> None:
        if not job or not job.owner:
            return
        key = f"wm:notify:{job.owner}"
        await self.r.xadd(key, {"data": _dumps({
            "type": "job_" + job.status, "job_id": job.id, "service": job.service, "kind": job.kind,
            "title": job.title, "ref": job.ref, "status": job.status, "at": now_iso(),
        })}, maxlen=500, approximate=True)

    async def notifications(self, owner: str, limit: int = 30) -> list[tuple[str, dict[str, Any]]]:
        rows = await self.r.xrevrange(f"wm:notify:{owner}", count=limit)
        return [(eid, _loads(f.get("data"), {})) for eid, f in rows]

    async def push_notification(self, owner: str, data: dict[str, Any]) -> None:
        await self.r.xadd(f"wm:notify:{owner}", {"data": _dumps({**data, "at": data.get("at") or now_iso()})}, maxlen=500, approximate=True)

    # ── 예약 ───────────────────────────────────────────
    async def schedule(
        self, service: str, kind: str, payload: dict[str, Any], run_at: float, *, title: str = "",
        ref: str | None = None, owner: str | None = None, schedule_id: str | None = None,
    ) -> str:
        sid = schedule_id or new_id("sch")
        entry = {"id": sid, "service": service, "kind": kind, "payload": payload, "title": title, "ref": ref,
                 "owner": owner or current_user().id, "run_at": run_at, "created_at": now_iso()}
        await self.r.hset("wm:sched:items", sid, _dumps(entry))
        await self.r.zadd("wm:sched", {sid: run_at})
        return sid

    async def unschedule(self, schedule_id: str) -> bool:
        removed = await self.r.zrem("wm:sched", schedule_id)
        await self.r.hdel("wm:sched:items", schedule_id)
        return bool(removed)

    async def schedules(self, *, service: str | None = None, ref: str | None = None) -> list[dict[str, Any]]:
        out = []
        for sid, raw in (await self.r.hgetall("wm:sched:items")).items():
            e = _loads(raw, {})
            if service and e.get("service") != service:
                continue
            if ref and e.get("ref") != ref:
                continue
            out.append(e)
        return sorted(out, key=lambda e: e.get("run_at", 0))

    async def run_due_schedules(self, now: float | None = None) -> list[str]:
        now = now or time.time()
        due = await self.r.zrangebyscore("wm:sched", "-inf", now)
        started = []
        for sid in due:
            if not await self.r.zrem("wm:sched", sid):
                continue  # 다른 프로세스가 가져감
            e = _loads(await self.r.hget("wm:sched:items", sid), {})
            await self.r.hdel("wm:sched:items", sid)
            if not e:
                continue
            job = await self.enqueue(e["service"], e["kind"], e.get("payload") or {}, title=e.get("title", ""),
                                     ref=e.get("ref"), owner=e.get("owner"))
            started.append(job.id)
        return started


_jobs: Jobs | None = None


def jobs() -> Jobs:
    global _jobs
    if _jobs is None:
        _jobs = Jobs()
    return _jobs


# ── 워커 ─────────────────────────────────────────────────

_current_job: contextvars.ContextVar["JobContext | None"] = contextvars.ContextVar("current_job", default=None)


def current_job() -> "JobContext | None":
    """LangGraph 노드 안에서 지금 처리 중인 잡 맥락을 얻는다."""
    return _current_job.get()


class AwaitingInput(Exception):
    def __init__(self, request: dict[str, Any]):
        super().__init__("awaiting input")
        self.request = request


class JobContext:
    def __init__(self, job: JobRecord, jobs_: Jobs, *, resume: bool = False, resume_value: Any = None):
        self.job = job
        self.jobs = jobs_
        self.payload = job.payload
        self.is_resume = resume
        self.resume_value = resume_value
        self._memo_cursor = 0
        self._result: dict[str, Any] | None = None

    async def progress(self, pct: int | float, message: str | None = None, **data: Any) -> None:
        pct = max(0, min(100, int(pct)))
        fields: dict[str, Any] = {"progress": pct}
        if message is not None:
            fields["message"] = message
        await self.jobs.update(self.job.id, **fields)
        await self.jobs.emit(self.job.id, "progress", {"progress": pct, "message": message, **data})

    async def step(self, name: str, status: str = "done", **data: Any) -> None:
        await self.jobs.emit(self.job.id, "step", {"step": name, "status": status, **data})

    async def log(self, message: str, **data: Any) -> None:
        await self.jobs.emit(self.job.id, "log", {"message": message, **data})

    async def partial(self, data: dict[str, Any]) -> None:
        """중간 결과(화면이 바로 그릴 수 있는 조각)."""
        await self.jobs.emit(self.job.id, "partial", data)

    async def check_cancel(self) -> None:
        if await self.jobs.is_canceled(self.job.id):
            raise JobCanceled()

    async def new_memos(self) -> list[dict[str, Any]]:
        memos = await self.jobs.memos(self.job.id, self._memo_cursor)
        self._memo_cursor += len(memos)
        return memos

    async def await_input(self, request: dict[str, Any]) -> None:
        """사람 입력을 기다린다고 표시한다(핸들러는 이후 바로 return 해야 한다)."""
        raise AwaitingInput(request)

    def set_result(self, result: dict[str, Any]) -> None:
        self._result = result


Handler = Callable[[JobContext], Awaitable[dict[str, Any] | None]]


class Worker:
    """서비스 하나의 큐를 소비한다. handlers: kind → async 함수(ctx) → 결과 dict."""

    def __init__(self, service: str, handlers: dict[str, Handler], *, concurrency: int | None = None,
                 reclaim_idle_ms: int = 15 * 60 * 1000, max_attempts: int = 2):
        self.service = service
        self.handlers = handlers
        self.concurrency = concurrency or int(os.environ.get("JOB_CONCURRENCY", "2"))
        self.reclaim_idle_ms = reclaim_idle_ms
        self.max_attempts = max_attempts
        self.stream = f"wm:q:{service}"
        self.group = "workers"
        self.consumer = f"{socket.gethostname()}-{os.getpid()}"
        self.jobs = jobs()
        self._stop = asyncio.Event()
        self._tasks: set[asyncio.Task[None]] = set()

    async def _ensure_group(self) -> None:
        try:
            await self.jobs.r.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except Exception as exc:  # noqa: BLE001
            if "BUSYGROUP" not in str(exc):
                raise

    async def process(self, entry_id: str, fields: dict[str, str]) -> None:
        job_id = fields.get("job_id", "")
        resume = fields.get("resume") == "1"
        try:
            await self._run_job(job_id, resume)
        finally:
            await self.jobs.r.xack(self.stream, self.group, entry_id)

    async def _run_job(self, job_id: str, resume: bool) -> None:
        job = await self.jobs.get(job_id)
        if job is None:
            log.warning("unknown job %s", job_id)
            return
        if job.status in TERMINAL:
            return
        if await self.jobs.is_canceled(job_id):
            await self._finish(job, "canceled", message="취소됨")
            return
        handler = self.handlers.get(job.kind)
        if handler is None:
            await self._finish(job, "failed", error={"code": "UNKNOWN_KIND", "message": f"처리기가 없는 잡 종류: {job.kind}"})
            return
        resume_value = None
        if resume:
            _, resume_value = await self.jobs.take_input(job_id)
        attempts = job.attempts + (0 if resume else 1)
        await self.jobs.update(job_id, status="running", started_at=job.started_at or now_iso(), attempts=attempts,
                               message="진행 중", input_request=None)
        await self.jobs.emit(job_id, "status", {"status": "running", "message": "진행 중", "resume": resume})
        ctx = JobContext(job, self.jobs, resume=resume, resume_value=resume_value)
        token = _current_job.set(ctx)
        set_user(job.owner, job.owner_name)
        request_id_var.set(job.payload.get("_request_id") or job.id)
        try:
            result = await handler(ctx)
            if result is None:
                result = ctx._result
            await self._finish(job, "succeeded", result=result or {})
        except AwaitingInput as wait:
            await self.jobs.update(job_id, status="awaiting_input", input_request=wait.request, message="입력 대기")
            await self.jobs.emit(job_id, "awaiting_input", wait.request)
            await self.jobs.push_notification(job.owner, {
                "type": "job_awaiting_input", "job_id": job.id, "service": job.service, "kind": job.kind,
                "title": job.title, "ref": job.ref, "status": "awaiting_input"})
        except JobCanceled:
            await self._finish(job, "canceled", message="취소됨")
        except Exception as exc:  # noqa: BLE001
            log.exception("job %s failed", job_id)
            code = getattr(exc, "code", None) or type(exc).__name__
            message = getattr(exc, "message", None) or str(exc) or type(exc).__name__
            await self._finish(job, "failed", error={"code": str(code), "message": str(message),
                                                     "trace": traceback.format_exc(limit=5)})
        finally:
            _current_job.reset(token)

    async def _finish(self, job: JobRecord, status: str, *, result: dict[str, Any] | None = None,
                      error: dict[str, Any] | None = None, message: str | None = None) -> None:
        msg = message or {"succeeded": "완료", "failed": "실패", "canceled": "취소됨"}.get(status, status)
        fields: dict[str, Any] = {"status": status, "finished_at": now_iso(), "message": msg}
        if status == "succeeded":
            fields["progress"] = 100
        if result is not None:
            fields["result"] = result
        if error is not None:
            fields["error"] = error
        await self.jobs.update(job.id, **fields)
        if result is not None:
            await self.jobs.emit(job.id, "result", result)
        if error is not None:
            await self.jobs.emit(job.id, "error", {k: v for k, v in error.items() if k != "trace"})
        await self.jobs.emit(job.id, "status", {"status": status, "message": msg})
        await self.jobs.emit(job.id, "done", {"status": status})
        await self.jobs._notify(await self.jobs.get(job.id))  # type: ignore[arg-type]

    async def _reclaim(self) -> None:
        """오래 처리되지 않은(워커가 죽은) 항목을 다시 가져온다."""
        try:
            res = await self.jobs.r.xautoclaim(self.stream, self.group, self.consumer, min_idle_time=self.reclaim_idle_ms, start_id="0-0", count=10)
        except Exception:  # noqa: BLE001
            return
        claimed = res[1] if isinstance(res, (list, tuple)) and len(res) > 1 else []
        for entry_id, fields in claimed:
            job = await self.jobs.get(fields.get("job_id", ""))
            if job and job.status == "running" and job.attempts >= self.max_attempts:
                await self._finish(job, "failed", error={"code": "WORKER_LOST", "message": "처리 중 워커가 멈췄습니다"})
                await self.jobs.r.xack(self.stream, self.group, entry_id)
                continue
            if job and job.status == "running":
                await self.jobs.update(job.id, status="queued")
            self._spawn(entry_id, fields)

    def _spawn(self, entry_id: str, fields: dict[str, str]) -> None:
        task = asyncio.create_task(self.process(entry_id, fields))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def run(self) -> None:
        await self._ensure_group()
        log.info("worker %s started (concurrency=%s, kinds=%s)", self.service, self.concurrency, sorted(self.handlers))
        last_reclaim = 0.0
        while not self._stop.is_set():
            if time.time() - last_reclaim > 60:
                await self._reclaim()
                last_reclaim = time.time()
            free = self.concurrency - len(self._tasks)
            if free <= 0:
                await asyncio.sleep(0.2)
                continue
            try:
                res = await self.jobs.r.xreadgroup(self.group, self.consumer, {self.stream: ">"}, count=free, block=2000)
            except Exception as exc:  # noqa: BLE001
                log.warning("redis read failed: %s", exc)
                await asyncio.sleep(2)
                continue
            for _stream, entries in res or []:
                for entry_id, fields in entries:
                    self._spawn(entry_id, fields)
        if self._tasks:
            await asyncio.wait(self._tasks, timeout=30)

    def stop(self) -> None:
        self._stop.set()


def run_worker(service: str, handlers: dict[str, Handler], **kw: Any) -> None:
    """워커 프로세스 진입점: `python -m winmate_<svc>.worker`."""
    from .app import setup_logging

    os.environ.setdefault("WINMATE_SERVICE", service)
    setup_logging(f"{service}-worker")
    worker = Worker(service, handlers, **kw)

    async def main() -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, worker.stop)
            except NotImplementedError:  # pragma: no cover
                pass
        await worker.run()

    asyncio.run(main())
