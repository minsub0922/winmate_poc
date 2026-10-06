"""다른 서비스 호출(계약 경유) — files · kb · workspace · jobs.

kb · workspace 실패는 본 작업을 막지 않는다(경고 로그 후 None). files 메타 실패는 FILE_NOT_FOUND 로 올린다.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.jobs import TERMINAL, jobs
from winmate_common.platform import register_item

from . import domain, repo

log = logging.getLogger("winmate.requirements.platform")


# ── files ───────────────────────────────────────────────

async def file_meta(file_id: str) -> dict[str, Any]:
    try:
        return await ServiceClient("files").get(f"/v1/files/{file_id}")
    except ApiError as exc:
        if exc.status in (404, 422):
            raise ApiError(404, "FILE_NOT_FOUND", f"파일을 찾을 수 없어요: {file_id}", {"file_id": file_id}) from exc
        raise


async def parsed(file_id: str, *, timeout: float = 120.0) -> dict[str, Any]:
    return await asyncio.wait_for(ServiceClient("files", timeout=timeout + 5).get(f"/v1/files/{file_id}/parsed"), timeout)


# ── kb ──────────────────────────────────────────────────

async def kb_query(code: str, body: dict[str, Any]) -> dict[str, Any] | None:
    """kb /v1/query/{code} 봉투의 result(실패 · 없음이면 None)."""
    try:
        env = await ServiceClient("kb", timeout=30).post(f"/v1/query/{code}", json=body)
    except Exception as exc:  # noqa: BLE001 — kb 는 보강 정보라 실패해도 계속
        log.warning("kb %s 실패: %s", code, exc)
        return None
    res = env.get("result") if isinstance(env, dict) else None
    if isinstance(res, dict):
        res = {**res, "_decision_hint": env.get("decision_hint"), "_needs_confirmation": env.get("needs_confirmation") or []}
    return res


# ── workspace ───────────────────────────────────────────

async def create_project(name: str, customer: str | None) -> str | None:
    try:
        body: dict[str, Any] = {"name": name[:120]}
        if customer:
            body["customer"] = customer
        proj = await ServiceClient("workspace").post("/v1/projects", json=body)
        return proj.get("id")
    except Exception as exc:  # noqa: BLE001
        log.warning("workspace 프로젝트 만들기 실패: %s", exc)
        return None


async def create_share(target: str, route: str, title: str) -> dict[str, Any]:
    return await ServiceClient("workspace").post("/v1/share-links", json={"target": target, "route": route, "title": title[:200]})


def index_payload(doc: dict[str, Any]) -> dict[str, Any]:
    state = domain.list_state(doc)
    return {"feature": "RQ", "title": domain.title_of(doc) or "새 요구사항", "status": state,
            "summary": domain.summary_of(doc), "route": domain.route_of(doc, state), "project_id": doc.get("project_id")}


async def sync_index(doc: dict[str, Any], *, force: bool = False) -> None:
    """workspace 작업물 색인(§4.0.4). 마지막으로 올린 값과 같으면 건너뛴다."""
    payload = index_payload(doc)
    digest = hashlib.sha1(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    cache = await repo.get("indexcache", doc["id"])
    if not force and cache and cache.get("digest") == digest:
        return
    await register_item(feature="RQ", item_id=doc["id"], title=payload["title"], status=payload["status"],
                        route=payload["route"], summary=payload["summary"], project_id=payload["project_id"],
                        meta={"version": doc.get("saved_version", 0), "state_label": domain.state_label(doc)})
    await repo.put("indexcache", doc["id"], {"digest": digest, "payload": payload})


# ── jobs ────────────────────────────────────────────────

async def job_alive(job_id: str) -> bool | None:
    """잡이 아직 끝나지 않았나(모르면 None)."""
    try:
        rec = await jobs().get(job_id)
    except Exception:  # noqa: BLE001 — Redis 없음
        return None
    if rec is None:
        return False
    return rec.status not in TERMINAL
