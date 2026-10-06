"""버전(§5.10) — 스냅숏 만들기 · 읽기 · 되돌리기 도우미. 변경 기록(change)은 core.record_change."""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from . import config, core, repo

SHEET_KEYS = ("id", "section_key", "ident", "order", "sheet_no", "role", "solution_code", "repeat_key", "title", "template", "content",
              "draft", "signals", "sources", "status", "status_before_exclude", "origin", "inferred", "evidence_note", "reuse", "split_of",
              "hidden", "content_rev", "user_edited", "edited_paths", "title_user_set")
PROPOSAL_KEYS = ("title", "customer", "schedule", "budget_text", "language", "rq_ref", "type", "type_source", "stage", "current_section_key",
                 "industry_layout", "design", "status", "files", "derived_from")


def vid(pid: str, n: int) -> str:
    return f"{pid}_v{n}"


async def snapshot(pid: str) -> dict[str, Any]:
    p = await core.load(pid)
    secs = await repo.alist("sections", {"proposal_id": pid})
    shs = await repo.alist("sheets", {"proposal_id": pid})
    facts = await repo.alist("facts", {"proposal_id": pid})
    items = await repo.alist("confirm_items", {"proposal_id": pid})
    return {
        "proposal": {k: copy.deepcopy(p.get(k)) for k in PROPOSAL_KEYS},
        "sections": [{k: v for k, v in s.items() if k not in ("_cas",)} for s in secs],
        "sheets": [{k: copy.deepcopy(s.get(k)) for k in SHEET_KEYS} for s in shs],
        "facts": [{k: v for k, v in f.items() if k not in ("_cas",)} for f in facts],
        "confirm_items": [{k: v for k, v in it.items() if k not in ("_cas",)} for it in items],
    }


def snap_hash(snap: dict[str, Any]) -> str:
    return hashlib.sha1(json.dumps(snap.get("sheets") or [], sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


async def list_versions(pid: str) -> list[dict[str, Any]]:
    vs = await repo.alist("versions", {"proposal_id": pid})
    return sorted(vs, key=lambda v: int(v.get("n") or 0))


async def get_version(pid: str, n: int) -> dict[str, Any] | None:
    v = await repo.aget("versions", vid(pid, n))
    return v if v and v.get("proposal_id") == pid else None


async def create(pid: str, *, kind: str, desc: str, author: dict[str, Any] | str, pptx_file_id: str | None = None,
                 pdf_file_id: str | None = None, derived_from: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """새 버전 n = 지금 + 1 → 스냅숏 저장 · 제안서 saved_version · edits 초기화 · 시트 「수정됨」 초기화."""
    p = await core.load(pid)
    existing = await list_versions(pid)
    n = max([int(v.get("n") or 0) for v in existing] + [int(p.get("saved_version") or 0)]) + 1
    snap = await snapshot(pid)
    shs = [s for s in snap["sheets"] if s.get("status") != "excluded" and not s.get("hidden")]
    doc = {"id": vid(pid, n), "proposal_id": pid, "n": n, "kind": kind, "desc": desc, "author": author, "snapshot": snap,
           "hash": snap_hash(snap), "pptx_file_id": pptx_file_id, "pdf_file_id": pdf_file_id, "derived_from": derived_from,
           "sheet_count": len(shs), "created_iso": config.now_iso(), **(extra or {})}
    await repo.aput("versions", doc["id"], doc)

    def fn(x: dict[str, Any]) -> None:
        x["saved_version"] = n
        x["edits_since_version"] = 0
        files = dict(x.get("files") or {})
        if pptx_file_id:
            files["pptx_file_id"] = pptx_file_id
        if pdf_file_id:
            files["pdf_file_id"] = pdf_file_id
        x["files"] = files
    await core.mutate(pid, fn)
    for s in await repo.alist("sheets", {"proposal_id": pid}):
        if s.get("edited_since_version"):
            await repo.amutate("sheets", s["id"], lambda x: x.update({"edited_since_version": False}))
    return doc


def author_label(author: Any) -> str:
    if author == "W" or (isinstance(author, dict) and author.get("user_id") == "W"):
        return "W"
    if isinstance(author, dict):
        return author.get("name") or ""
    return str(author or "")
