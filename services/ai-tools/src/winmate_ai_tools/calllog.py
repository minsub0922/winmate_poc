"""모델 호출 로그 — data/ai-tools/calls.sqlite.

- 한 번의 API 호출 = 한 줄(재시도 · 수리 호출은 attempts 로 센다).
- MODEL_CALL_LOG=full 이면 요청 · 응답 본문도 남긴다(base64 · 긴 문자열 · 긴 배열은 줄여서). meta 면 메타만, off 면 안 남긴다.
- MODEL_CALL_LOG_RETENTION_DAYS 보다 오래된 줄은 서비스 시작 때 지운다.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from winmate_common.env import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  capability TEXT NOT NULL,
  task TEXT,
  status TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_calls_ts ON calls(ts DESC, id DESC);
CREATE INDEX IF NOT EXISTS ix_calls_cap ON calls(capability, ts DESC);
CREATE INDEX IF NOT EXISTS ix_calls_task ON calls(task, ts DESC);
"""

_B64 = re.compile(r"^[A-Za-z0-9+/=_-]{200,}$")
MAX_STR = 20000
MAX_LIST = 100


class CallLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._conn().executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def put(self, rec: dict[str, Any]) -> None:
        self._conn().execute(
            "INSERT OR REPLACE INTO calls(id, ts, capability, task, status, data) VALUES (?,?,?,?,?,?)",
            (rec["id"], rec["ts"], rec["capability"], rec.get("task"), rec["status"],
             json.dumps(rec, ensure_ascii=False, default=str)),
        )

    def get(self, call_id: str) -> dict[str, Any] | None:
        row = self._conn().execute("SELECT data FROM calls WHERE id=?", (call_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list(self, *, capability: str | None = None, task: str | None = None, limit: int = 50,
             cursor: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
        clauses: list[str] = []
        args: list[Any] = []
        if capability:
            clauses.append("capability=?")
            args.append(capability)
        if task:
            clauses.append("task=?")
            args.append(task)
        if cursor:
            try:
                ts, cid = base64.urlsafe_b64decode(cursor.encode()).decode().split("|", 1)
                clauses.append("(ts < ? OR (ts = ? AND id < ?))")
                args.extend([ts, ts, cid])
            except Exception:  # noqa: BLE001 — 잘못된 커서는 처음부터
                pass
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._conn().execute(
            f"SELECT id, ts, data FROM calls {where} ORDER BY ts DESC, id DESC LIMIT ?", (*args, limit + 1)
        ).fetchall()
        items = [json.loads(r["data"]) for r in rows[:limit]]
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = base64.urlsafe_b64encode(f"{last['ts']}|{last['id']}".encode()).decode()
        return items, next_cursor

    def prune(self, days: int) -> int:
        if days <= 0:
            return 0
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        cur = self._conn().execute("DELETE FROM calls WHERE ts < ?", (cutoff,))
        return cur.rowcount


_logs: dict[str, CallLog] = {}


def store() -> CallLog:
    """DATA_DIR 별로 하나(테스트가 DATA_DIR 를 바꾸면 새 파일)."""
    path = settings().service_data_dir("ai-tools") / "calls.sqlite"
    key = str(path)
    log = _logs.get(key)
    if log is None:
        log = _logs[key] = CallLog(path)
    return log


def scrub(value: Any, *, key: str | None = None, depth: int = 0) -> Any:
    """로그용으로 줄인다: base64 · 큰 문자열 · 긴 배열(임베딩 벡터 등)."""
    if depth > 12:
        return "…"
    if isinstance(value, dict):
        return {k: scrub(v, key=k, depth=depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        items = [scrub(v, depth=depth + 1) for v in value[:MAX_LIST]]
        if len(value) > MAX_LIST:
            items.append(f"…(+{len(value) - MAX_LIST} items)")
        return items
    if isinstance(value, (bytes, bytearray)):
        return f"<bytes {len(value)} sha256:{hashlib.sha256(value).hexdigest()[:12]}>"
    if isinstance(value, str):
        if key in ("data_b64", "b64_json") or (len(value) >= 200 and _B64.match(value)) or value.startswith("data:image/"):
            return f"<base64 {len(value)} chars sha256:{hashlib.sha256(value.encode()).hexdigest()[:12]}>"
        if len(value) > MAX_STR:
            return value[:MAX_STR] + f"…(+{len(value) - MAX_STR} chars)"
    return value
