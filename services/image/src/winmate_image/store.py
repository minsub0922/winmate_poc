"""image 저장소 — `DocStore.for_service("image")` → `${DATA_DIR}/image/image.sqlite` (07-image §5).

컬렉션(문서 = JSON 하나):
  works(imw_) · refs(imr_) · photos(imp_) · runs(ign_) · images(img_) · versions(imv_) · regions(ire_) ·
  usages(<image>|<service>|<ref>) · requests(irq_) · exports(ixp_) · renders(irn_) · detections(<version_id>) ·
  kbfiles(<kb image id>) · stats(<지연 EMA 키>)

API 프로세스와 워커가 같은 SQLite 를 쓴다(WAL). 한 문서를 고칠 때는 `mutate()` 로 낙관적 잠금(버전 비교 + 재시도)을 건다.
"""
from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from winmate_common.env import settings
from winmate_common.errors import not_found
from winmate_common.store import DocStore, VersionConflict

INDEXES = {
    "works": ("owner", "status", "project_id"),
    "refs": ("work_id",),
    "photos": ("work_id",),
    "runs": ("work_id", "owner", "status"),
    "images": ("work_id", "run_id", "owner", "origin"),
    "versions": ("image_id",),
    "regions": ("image_id",),
    "usages": ("image_id",),
    "requests": ("status", "from_ref", "owner"),
    "exports": ("version_id",),
    "renders": ("owner",),
}

_lock = threading.Lock()
_repos: dict[Path, "Repo"] = {}


class Repo:
    """DocStore 동기 API 를 스레드에서 돌리는 얇은 async 래퍼."""

    def __init__(self, db: DocStore):
        self.db = db
        for coll, fields in INDEXES.items():
            for f in fields:
                db.index(coll, f)

    # ── 읽기 ─────────────────────────────────────────
    async def get(self, coll: str, doc_id: str | None) -> dict[str, Any] | None:
        if not doc_id:
            return None
        return await asyncio.to_thread(self.db.get, coll, doc_id)

    async def must(self, coll: str, doc_id: str | None, what: str) -> dict[str, Any]:
        doc = await self.get(coll, doc_id)
        if doc is None:
            raise not_found(what, doc_id)
        return doc

    async def list(self, coll: str, *, where: dict[str, Any] | None = None, order_by: str = "-updated_at",
                   limit: int = 500, cursor: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
        return await asyncio.to_thread(self.db.list, coll, where=where, order_by=order_by, limit=limit, cursor=cursor)

    async def all(self, coll: str, *, where: dict[str, Any] | None = None, order_by: str = "-updated_at",
                  limit: int = 2000) -> list[dict[str, Any]]:
        items, _ = await self.list(coll, where=where, order_by=order_by, limit=limit)
        return items

    async def count(self, coll: str, *, where: dict[str, Any] | None = None) -> int:
        return await asyncio.to_thread(self.db.count, coll, where=where)

    # ── 쓰기 ─────────────────────────────────────────
    async def put(self, coll: str, doc_id: str, data: dict[str, Any], *, history: bool = False) -> dict[str, Any]:
        return await asyncio.to_thread(self.db.put, coll, doc_id, data, keep_history=history)

    async def mutate(self, coll: str, doc_id: str, fn: Callable[[dict[str, Any]], dict[str, Any] | None], *,
                     history: bool = False, missing_ok: bool = False) -> dict[str, Any] | None:
        """문서를 읽어 fn(doc) 으로 고치고(같은 dict 를 고치거나 새 dict 를 돌려줌) 버전 비교로 저장한다. 충돌하면 다시."""

        def _run() -> dict[str, Any] | None:
            for _ in range(20):
                cur = self.db.get(coll, doc_id)
                if cur is None:
                    if missing_ok:
                        return None
                    raise KeyError(f"{coll}/{doc_id}")
                ver = cur["version"]
                res = fn(cur)
                new = res if isinstance(res, dict) else cur
                try:
                    return self.db.put(coll, doc_id, new, expected_version=ver, keep_history=history)
                except VersionConflict:
                    continue
            raise RuntimeError(f"저장 충돌이 계속됩니다: {coll}/{doc_id}")

        return await asyncio.to_thread(_run)

    async def patch(self, coll: str, doc_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
        def fn(doc: dict[str, Any]) -> None:
            doc.update(changes)

        return await self.mutate(coll, doc_id, fn, missing_ok=True)

    async def delete(self, coll: str, doc_id: str) -> bool:
        return await asyncio.to_thread(self.db.delete, coll, doc_id)


def repo() -> Repo:
    path = settings().service_data_dir("image") / "image.sqlite"
    r = _repos.get(path)
    if r is None:
        with _lock:
            r = _repos.get(path)
            if r is None:
                r = Repo(DocStore(path))
                _repos[path] = r
    return r
