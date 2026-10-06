"""편집 세션(SP3E, 06-spec §6.8) — 조작은 서버 세션에 쌓이고(새로고침해도 유지) `편집 완료` 때 한 번에 반영(version +1)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response
from winmate_common.errors import ApiError
from winmate_common.jobs import jobs

from .. import edit as ED
from .. import ops, repo
from ..api_support import doc, load
from ..models import CommitBody, EditMessage, EditOps, EditSessionCreated, EditView, JobAccepted, SheetDoc

router = APIRouter(prefix="/v1", tags=["edit"])


async def _session(sheet_id: str, session_id: str) -> dict[str, Any]:
    sess = await repo.aget("edit_sessions", session_id)
    if sess is None or sess.get("sheet_id") != sheet_id:
        raise ApiError(404, "NOT_FOUND", "편집 세션을 찾을 수 없어요.")
    return sess


@router.post("/sheets/{sheet_id}/edit-sessions", response_model=EditSessionCreated, status_code=201)
async def create_session(sheet_id: str) -> dict[str, Any]:
    s = await load(sheet_id)
    if not s.get("generated_at") or not s.get("rows"):
        raise ApiError(422, "NOT_GENERATED", "시트를 먼저 만들어 주세요.")
    sid = ED.new_id_ses()
    sess = ED.new_session(s)
    sess["id"] = sid
    uid, _ = ops.user()
    sess["owner_id"] = uid
    await repo.aput("edit_sessions", sid, sess)
    sess["id"] = sid
    return {"id": sid, "base_version": sess["base_version"], "view": ED.view(sess, sheet_id, s)}


@router.get("/sheets/{sheet_id}/edit-sessions/{session_id}", response_model=EditView)
async def get_session(sheet_id: str, session_id: str) -> dict[str, Any]:
    s = await load(sheet_id)
    sess = await _session(sheet_id, session_id)
    return ED.view(sess, sheet_id, s)


@router.post("/sheets/{sheet_id}/edit-sessions/{session_id}/ops", response_model=EditView)
async def add_ops(sheet_id: str, session_id: str, body: EditOps) -> dict[str, Any]:
    """조작 더하기(행 이동 · 숨김 · 강조 · 메모 · 항목 추가 · 행 삭제 · 열 이동). 추가 행 값은 카탈로그에서 바로(결정적)."""
    await load(sheet_id)
    await _session(sheet_id, session_id)
    for op in body.ops:
        if op.op in ("move_row", "move_column") and op.to_index is None:
            raise ApiError(422, "VALIDATION_FAILED", "옮길 위치(to_index)가 필요해요.")
        if op.op == "set_memo" and not (op.text or "").strip():
            raise ApiError(422, "VALIDATION_FAILED", "메모 글을 넣어 주세요.")
    return await ED.add_ops(sheet_id, session_id, [o.model_dump(exclude_none=True) for o in body.ops])


@router.post("/sheets/{sheet_id}/edit-sessions/{session_id}:undo", response_model=EditView)
async def undo(sheet_id: str, session_id: str) -> dict[str, Any]:
    await _session(sheet_id, session_id)
    return await ED.move_cursor(sheet_id, session_id, "undo")


@router.post("/sheets/{sheet_id}/edit-sessions/{session_id}:redo", response_model=EditView)
async def redo(sheet_id: str, session_id: str) -> dict[str, Any]:
    await _session(sheet_id, session_id)
    return await ED.move_cursor(sheet_id, session_id, "redo")


@router.post("/sheets/{sheet_id}/edit-sessions/{session_id}:reset", response_model=EditView)
async def reset(sheet_id: str, session_id: str) -> dict[str, Any]:
    """`모두 되돌리기` — 세션 조작 비움."""
    await _session(sheet_id, session_id)
    return await ED.move_cursor(sheet_id, session_id, "reset")


@router.post("/sheets/{sheet_id}/edit-sessions/{session_id}/messages", response_model=JobAccepted, status_code=202)
async def edit_message(sheet_id: str, session_id: str, body: EditMessage) -> dict[str, Any]:
    """`말로 고치기` — LLM 조작을 세션에 더함(바로 커밋하지 않음, spec_revise context=edit)."""
    s = await load(sheet_id)
    sess = await _session(sheet_id, session_id)
    if sess.get("status") != "open":
        raise ApiError(409, "SESSION_CLOSED", "이미 끝난 편집 세션이에요.")
    job = await jobs().enqueue("spec", "spec_revise", {"sheet_id": sheet_id, "text": body.text.strip(), "context": "edit",
                                                       "session_id": session_id}, title="말로 고치기", ref=sheet_id, project_id=s.get("project_id"))
    return {"job_id": job.id, "status": "queued", "sheet_id": sheet_id}


@router.post("/sheets/{sheet_id}/edit-sessions/{session_id}:commit", response_model=SheetDoc)
async def commit(sheet_id: str, session_id: str, body: CommitBody | None = None) -> dict[str, Any]:
    """`편집 완료` — 한 번에 반영(version +1). 그사이 시트가 바뀌었으면 409 VERSION_CONFLICT(rebase=true 면 최신 시트에 다시 얹음)."""
    await load(sheet_id)
    await _session(sheet_id, session_id)
    uid, _ = ops.user()
    saved = await ED.commit(sheet_id, session_id, bool(body and body.rebase), uid)
    return await doc(saved)


@router.delete("/sheets/{sheet_id}/edit-sessions/{session_id}", status_code=204)
async def discard(sheet_id: str, session_id: str) -> Response:
    """`취소` — 세션 버림(시트 그대로)."""
    await _session(sheet_id, session_id)
    await repo.amutate("edit_sessions", session_id, lambda x: x.update({"status": "discarded"}), what="편집 세션")
    return Response(status_code=204)
