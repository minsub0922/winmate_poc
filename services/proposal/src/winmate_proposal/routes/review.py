"""§6.10 검토(workspace 파사드) · 코멘트 수정안 · 공유 링크. 코멘트 본문 · 답글 · 해결은 웹이 workspace 를 직접 쓴다."""
from __future__ import annotations

from fastapi import APIRouter

from .. import models as M
from ..ops import review as R

router = APIRouter(prefix="/v1", tags=["review"])


@router.post("/proposals/{proposal_id}/review-requests", response_model=M.ReviewView, status_code=201)
async def request_review(proposal_id: str, body: M.ReviewRequestIn) -> M.ReviewView:
    return await R.request_review(proposal_id, body)


@router.post("/proposals/{proposal_id}/review-requests/{review_id}:resubmit", response_model=M.ReviewView)
async def resubmit(proposal_id: str, review_id: str, body: M.ResubmitIn | None = None) -> M.ReviewView:
    return await R.resubmit(proposal_id, review_id, body or M.ResubmitIn())


@router.get("/proposals/{proposal_id}/review", response_model=M.ReviewView)
async def get_review(proposal_id: str) -> M.ReviewView:
    return await R.get_review(proposal_id)


@router.post("/proposals/{proposal_id}/review/decision", response_model=M.ReviewView)
async def decide(proposal_id: str, body: M.DecisionIn) -> M.ReviewView:
    return await R.decide(proposal_id, body)


@router.put("/proposals/{proposal_id}/review/checks/{sheet_id}", response_model=M.ReviewView)
async def put_check(proposal_id: str, sheet_id: str, body: M.CheckPut) -> M.ReviewView:
    return await R.put_check(proposal_id, sheet_id, body)


@router.post("/proposals/{proposal_id}/review:apply-comments", response_model=M.JobAccepted, status_code=202)
async def apply_comments(proposal_id: str, body: M.ApplyCommentsIn | None = None) -> M.JobAccepted:
    return await R.apply_comments(proposal_id, body or M.ApplyCommentsIn())


@router.post("/proposals/{proposal_id}/comments/{comment_id}:suggest", response_model=M.JobAccepted, status_code=202)
async def suggest(proposal_id: str, comment_id: str) -> M.JobAccepted:
    return await R.suggest(proposal_id, comment_id)


@router.get("/proposals/{proposal_id}/comments/{comment_id}/suggestion", response_model=M.Suggestion)
async def get_suggestion(proposal_id: str, comment_id: str) -> M.Suggestion:
    return await R.get_suggestion(proposal_id, comment_id)


@router.post("/proposals/{proposal_id}/comments/{comment_id}:apply-suggestion", response_model=M.ApplySuggestionResult)
async def apply_suggestion(proposal_id: str, comment_id: str) -> M.ApplySuggestionResult:
    return await R.apply_suggestion(proposal_id, comment_id)


@router.post("/proposals/{proposal_id}/share-link", response_model=M.ShareLinkOut)
async def share_link(proposal_id: str, body: M.ShareLinkIn | None = None) -> M.ShareLinkOut:
    return await R.share_link(proposal_id, body or M.ShareLinkIn())
