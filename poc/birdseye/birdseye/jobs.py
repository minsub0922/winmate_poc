"""백그라운드 작업(3D 렌더) — 스레드 풀 + 진행 상태."""
from __future__ import annotations

import concurrent.futures as cf
import datetime as dt
import secrets
import threading
import traceback

PIPELINE_STEPS = [
    ("요구사항 분석", "공간 · 분위기 · 제품을 읽어요"),
    ("참고 사례 찾기", "공간 제품 배치 이미지 DB"),
    ("공간 모델링", "Blender 씬 · 벽 · 바닥 · 창 · 기둥"),
    ("인테리어 · 가구 선정 · 배치", "마감 · 가구를 고르고 배치해요"),
    ("재질 · 조명 · 렌더링", "Cycles"),
    ("품질 확인", "제품 비율 · 노출 · 겹침 점검"),
]


class Job:
    def __init__(self, kind: str, project_id: str, title: str = ""):
        self.id = f"j{dt.datetime.now().strftime('%H%M%S')}{secrets.token_hex(2)}"
        self.kind = kind
        self.project_id = project_id
        self.title = title
        self.status = "queued"
        self.steps = [{"no": i + 1, "name": n, "note": note, "status": "wait"} for i, (n, note) in enumerate(PIPELINE_STEPS)]
        self.pct = 0
        self.preview = None
        self.result: dict = {}
        self.error = None
        self.log: list[str] = []
        self.cancel = threading.Event()
        self.created = dt.datetime.now().isoformat(timespec="seconds")
        self.finished = None
        self.cut_progress: dict = {}
        self.progress_estimated = False
        self.lock = threading.Lock()

    def step(self, no: int, status: str, note: str | None = None):
        with self.lock:
            s = self.steps[no - 1]
            s["status"] = status
            if note:
                s["note"] = note
            done = sum(1 for x in self.steps if x["status"] in ("done", "skip"))
            self.pct = max(self.pct, int(done / len(self.steps) * 100))

    def to_dict(self) -> dict:
        with self.lock:
            return {"id": self.id, "kind": self.kind, "project_id": self.project_id, "title": self.title, "status": self.status,
                    "steps": [dict(s) for s in self.steps], "pct": self.pct, "preview": self.preview, "result": self.result,
                    "error": self.error, "log": self.log[-30:], "created": self.created, "finished": self.finished,
                    "cuts": dict(self.cut_progress), "estimated": self.progress_estimated}


class JobManager:
    def __init__(self, workers: int = 1):
        self.pool = cf.ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="render")
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()

    def submit(self, job: Job, fn, *args, **kw) -> Job:
        with self.lock:
            self.jobs[job.id] = job

        def run():
            if job.cancel.is_set():
                job.status = "cancelled"
                return
            job.status = "running"
            try:
                fn(job, *args, **kw)
                if job.status == "running":
                    job.status = "done"
                    job.pct = 100
            except Exception as e:  # noqa: BLE001
                if job.cancel.is_set():
                    job.status = "cancelled"
                else:
                    job.status = "failed"
                    job.error = f"{type(e).__name__}: {e}"
                    job.log.append(traceback.format_exc()[-1500:])
            finally:
                job.finished = dt.datetime.now().isoformat(timespec="seconds")

        self.pool.submit(run)
        return job

    def get(self, jid: str) -> Job | None:
        return self.jobs.get(jid)

    def active_for(self, project_id: str) -> list[Job]:
        return [j for j in self.jobs.values() if j.project_id == project_id and j.status in ("queued", "running")]

    def cancel(self, jid: str) -> bool:
        j = self.jobs.get(jid)
        if not j:
            return False
        j.cancel.set()
        if j.status == "queued":
            j.status = "cancelled"
        return True
