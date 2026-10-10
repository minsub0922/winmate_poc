"""서비스별 SQLite 문서 저장소(버전 기록 포함).

    store = DocStore.for_service("requirements")       # data/requirements/requirements.sqlite
    doc = store.put("specs", spec_id, {...}, author=user.id, note="v1 저장")
    items, cursor = store.list("specs", where={"project_id": pid}, limit=20)
    store.versions("specs", spec_id); store.restore("specs", spec_id, 2)

- 문서는 JSON 하나. 읽을 때 `id · version · created_at · updated_at` 가 붙는다.
- put 은 매번 version 을 올리고 이전 판을 doc_versions 에 남긴다(keep_history=False 면 남기지 않음).
- where 는 최상위 필드 같음 비교(json_extract). 자주 쓰는 필드는 index() 로 식 인덱스를 만든다.
- 동기 API 다. async 코드에서는 `await asyncio.to_thread(store.get, ...)` 또는 AsyncDocStore 를 쓴다.
"""
from __future__ import annotations

import asyncio
import base64
import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from .env import settings
from .ids import now_iso

_FIELD = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
  collection TEXT NOT NULL,
  id TEXT NOT NULL,
  version INTEGER NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (collection, id)
);
CREATE INDEX IF NOT EXISTS ix_docs_updated ON docs(collection, deleted, updated_at);
CREATE TABLE IF NOT EXISTS doc_versions (
  collection TEXT NOT NULL,
  id TEXT NOT NULL,
  version INTEGER NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  author TEXT,
  note TEXT,
  PRIMARY KEY (collection, id, version)
);
"""


class VersionConflict(Exception):
    pass


class DocStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        with self._conn() as c:
            c.executescript(_SCHEMA)

    @classmethod
    def for_service(cls, service: str, name: str | None = None) -> "DocStore":
        return cls(settings().service_data_dir(service) / f"{name or service}.sqlite")

    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def index(self, collection: str, field: str) -> None:
        if not _FIELD.match(field) or not _FIELD.match(collection):
            raise ValueError("field/collection 이름은 영문·숫자·_ 만")
        self._conn().execute(
            f"CREATE INDEX IF NOT EXISTS ix_{collection}_{field} ON docs(collection, json_extract(data, '$.{field}')) "
            f"WHERE collection = '{collection}'"
        )

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        data = json.loads(row["data"])
        data.update({"id": row["id"], "version": row["version"], "created_at": row["created_at"], "updated_at": row["updated_at"]})
        return data

    # ── 읽기 ───────────────────────────────────────────
    def get(self, collection: str, doc_id: str, *, include_deleted: bool = False) -> dict[str, Any] | None:
        sql = "SELECT * FROM docs WHERE collection=? AND id=?" + ("" if include_deleted else " AND deleted=0")
        return self._row(self._conn().execute(sql, (collection, doc_id)).fetchone())

    def list(
        self,
        collection: str,
        *,
        where: dict[str, Any] | None = None,
        order_by: str = "-updated_at",
        limit: int = 50,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        desc = order_by.startswith("-")
        field = order_by.lstrip("-")
        if field in ("updated_at", "created_at", "id"):
            order_expr = field
        elif _FIELD.match(field):
            order_expr = f"json_extract(data, '$.{field}')"
        else:
            raise ValueError("order_by")
        clauses = ["collection=?", "deleted=0"]
        args: list[Any] = [collection]
        for k, v in (where or {}).items():
            if not _FIELD.match(k):
                raise ValueError(f"where field {k}")
            if isinstance(v, (list, tuple, set)):
                vals = list(v)
                if not vals:
                    return [], None
                clauses.append(f"json_extract(data, '$.{k}') IN ({','.join('?' * len(vals))})")
                args.extend(vals)
            elif v is None:
                clauses.append(f"json_extract(data, '$.{k}') IS NULL")
            else:
                clauses.append(f"json_extract(data, '$.{k}') = ?")
                args.append(v if not isinstance(v, bool) else int(v))
        offset = 0
        if cursor:
            try:
                offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
            except Exception:  # noqa: BLE001
                offset = 0
        sql = (f"SELECT * FROM docs WHERE {' AND '.join(clauses)} ORDER BY {order_expr} {'DESC' if desc else 'ASC'}, id "
               f"{'DESC' if desc else 'ASC'} LIMIT ? OFFSET ?")
        rows = self._conn().execute(sql, (*args, limit + 1, offset)).fetchall()
        items = [self._row(r) for r in rows[:limit]]
        next_cursor = base64.urlsafe_b64encode(str(offset + limit).encode()).decode() if len(rows) > limit else None
        return [i for i in items if i is not None], next_cursor

    def count(self, collection: str, *, where: dict[str, Any] | None = None) -> int:
        clauses = ["collection=?", "deleted=0"]
        args: list[Any] = [collection]
        for k, v in (where or {}).items():
            if not _FIELD.match(k):
                raise ValueError(k)
            clauses.append(f"json_extract(data, '$.{k}') = ?")
            args.append(v)
        return int(self._conn().execute(f"SELECT COUNT(*) FROM docs WHERE {' AND '.join(clauses)}", args).fetchone()[0])

    # ── 쓰기 ───────────────────────────────────────────
    def put(
        self,
        collection: str,
        doc_id: str,
        data: dict[str, Any],
        *,
        author: str | None = None,
        note: str | None = None,
        expected_version: int | None = None,
        keep_history: bool = True,
    ) -> dict[str, Any]:
        body = {k: v for k, v in data.items() if k not in ("id", "version", "created_at", "updated_at")}
        payload = json.dumps(body, ensure_ascii=False, default=str)
        now = now_iso()
        conn = self._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT version, created_at, deleted FROM docs WHERE collection=? AND id=?", (collection, doc_id)).fetchone()
            if row is None:
                if expected_version not in (None, 0):
                    raise VersionConflict(f"{collection}/{doc_id} 없음")
                version, created = 1, now
                conn.execute("INSERT INTO docs(collection,id,version,data,created_at,updated_at,deleted) VALUES (?,?,?,?,?,?,0)",
                             (collection, doc_id, version, payload, created, now))
            else:
                if expected_version is not None and row["version"] != expected_version:
                    raise VersionConflict(f"{collection}/{doc_id} 버전 {row['version']} ≠ 기대 {expected_version}")
                version, created = row["version"] + 1, row["created_at"]
                conn.execute("UPDATE docs SET version=?, data=?, updated_at=?, deleted=0 WHERE collection=? AND id=?",
                             (version, payload, now, collection, doc_id))
            if keep_history:
                conn.execute("INSERT OR REPLACE INTO doc_versions(collection,id,version,data,created_at,author,note) VALUES (?,?,?,?,?,?,?)",
                             (collection, doc_id, version, payload, now, author, note))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        return {**body, "id": doc_id, "version": version, "created_at": created, "updated_at": now}

    def patch(self, collection: str, doc_id: str, changes: dict[str, Any], **kw: Any) -> dict[str, Any]:
        cur = self.get(collection, doc_id)
        if cur is None:
            raise KeyError(f"{collection}/{doc_id}")
        cur.update(changes)
        return self.put(collection, doc_id, cur, **kw)

    def delete(self, collection: str, doc_id: str, *, expected_version: int | None = None) -> bool:
        """소프트 삭제. `expected_version` 을 주면 같은 트랜잭션 안에서 판을 확인한다 — 다르면 VersionConflict
        (예: "저장 전 초안인지 확인 → 지우기" 사이에 다른 요청이 저장한 경우)."""
        if expected_version is None:
            cur = self._conn().execute("UPDATE docs SET deleted=1, updated_at=? WHERE collection=? AND id=? AND deleted=0",
                                       (now_iso(), collection, doc_id))
            return cur.rowcount > 0
        conn = self._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT version, deleted FROM docs WHERE collection=? AND id=?", (collection, doc_id)).fetchone()
            if row is None or row["deleted"]:
                conn.execute("COMMIT")
                return False
            if row["version"] != expected_version:
                raise VersionConflict(f"{collection}/{doc_id} 버전 {row['version']} ≠ 기대 {expected_version}")
            conn.execute("UPDATE docs SET deleted=1, updated_at=? WHERE collection=? AND id=?", (now_iso(), collection, doc_id))
            conn.execute("COMMIT")
            return True
        except Exception:
            conn.execute("ROLLBACK")
            raise

    # ── 버전 ───────────────────────────────────────────
    def versions(self, collection: str, doc_id: str) -> list[dict[str, Any]]:
        rows = self._conn().execute(
            "SELECT version, created_at, author, note FROM doc_versions WHERE collection=? AND id=? ORDER BY version DESC",
            (collection, doc_id)).fetchall()
        return [dict(r) for r in rows]

    def get_version(self, collection: str, doc_id: str, version: int) -> dict[str, Any] | None:
        row = self._conn().execute("SELECT * FROM doc_versions WHERE collection=? AND id=? AND version=?",
                                   (collection, doc_id, version)).fetchone()
        if row is None:
            return None
        data = json.loads(row["data"])
        data.update({"id": doc_id, "version": row["version"], "updated_at": row["created_at"]})
        return data

    def restore(self, collection: str, doc_id: str, version: int, *, author: str | None = None) -> dict[str, Any]:
        """과거 판을 새 판으로 되살린다(기록은 지우지 않는다)."""
        old = self.get_version(collection, doc_id, version)
        if old is None:
            raise KeyError(f"{collection}/{doc_id}@{version}")
        return self.put(collection, doc_id, old, author=author, note=f"v{version} 복원")


class AsyncDocStore:
    """DocStore 를 스레드에서 돌리는 async 래퍼."""

    def __init__(self, store: DocStore):
        self.sync = store

    def __getattr__(self, name: str) -> Any:
        fn = getattr(self.sync, name)
        if not callable(fn):
            return fn

        async def _call(*args: Any, **kwargs: Any) -> Any:
            return await asyncio.to_thread(fn, *args, **kwargs)

        return _call
