"""storyboard API (/v1). 이 파일의 엔드포인트가 contracts/storyboard.json 이 된다(make contracts).

docs/scenarios/02-storyboard.md §6 — 스토리보드 · 설정 · 기획 질의 · 기획 방향 · 핵심 메시지 · 목차 · 공간 · 수정 요청 · 버전 · 비교 ·
정의서 동기화 · 요구 추적 · 일정 · 내보내기 · 공유 · 넘기기. 202 응답에는 편의상 `ref`(만들어진 자원)를 함께 준다.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import ops_after, ops_core, ops_outline, repo, service
from .models import (
    Compare, CompetitorImport, CreateStoryboard, Direction, ExportRequest, HandoffList, HandoffResult, JobAccepted, KeyMessage,
    KeyMessageList, Outline, PatchDirection, PatchDirectionResult, PatchKeyMessage, Planning, PlanningAnswer, PlanningQuestion,
    PostDirection, PostEvidence, PostRevision, ProposalHandoff, PutPlanningAnswer, PutRequirement, PutResolution, PutSlot,
    RequirementSyncRequest, ResolutionResult, RestoreResult, ReviewRequestBody, ReviewRequestResult, Revision, SaveRequest,
    SaveResult, Schedule, SettingsPatch, SettingsResult, ShareResult, Space, SpaceQuestions, SpaceSlotResult, Storyboard,
    StoryboardCounts, StoryboardList, StoryboardVersion, SyncPreview, Trace, VersionList,
)

router = APIRouter(prefix="/v1")
SB = ["storyboards"]


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="storyboard", title="전략 수립 Storyboard — 기획 질문 · 5단 목차 · 요구사항 추적 · 버전 비교 · 일정",
                       version="1.0.0")


def _json(model: type[BaseModel], data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(model.model_validate(data).model_dump(mode="json", by_alias=True), status_code=status)


def _accepted(job_id: str, ref: dict[str, str] | None = None) -> JSONResponse:
    return _json(JobAccepted, {"job_id": job_id, "status": "queued", "ref": ref}, 202)


SbId = Annotated[str, Path(description="스토리보드 id(sb_…)")]
ACCEPTED = {202: {"model": JobAccepted, "description": "잡을 큐에 넣었다 — 진행은 jobs SSE"}}


# ── 스토리보드 · 설정(§6.1) ─────────────────────────────────

@router.get("/storyboards", response_model=StoryboardList, tags=SB)
async def list_storyboards(
    tab: Literal["all", "in_progress", "done"] = "all", q: str | None = None,
    customer: str | None = Query(None, description="고객사 부분 일치(제안서 PR1 `최근 Storyboard` 카드)"),
    updated_after: str | None = Query(None, description="ISO 시각 이후 수정된 것만"),
    limit: int = Query(20, ge=1, le=100), cursor: str | None = None,
) -> dict[str, Any]:
    """작업 목록(SB0) — 시작된 내 스토리보드만, 수정 시각 내림차순."""
    items, nxt = await ops_core.list_(tab, q, customer, updated_after, limit, cursor)
    return {"items": items, "next_cursor": nxt}


@router.get("/storyboards/counts", response_model=StoryboardCounts, tags=SB)
async def storyboard_counts() -> dict[str, int]:
    """SB0 탭 숫자(`완료` = done + shared)."""
    return await ops_core.counts()


@router.post("/storyboards", response_model=Storyboard, status_code=201, tags=SB,
             responses={200: {"model": Storyboard, "description": "내 시작 전 초안을 다시 씀"}})
async def create_storyboard(body: CreateStoryboard) -> JSONResponse:
    """SB1 진입 — 정의서로 스토리보드를 만들고 `sb.prepare` 를 시작한다(`prepare_job_id`). 시작 전 초안이 있으면 재사용(200)."""
    doc, created = await ops_core.create(body)
    return _json(Storyboard, service.to_api(doc), 201 if created else 200)


@router.get("/storyboards/{sb_id}", response_model=Storyboard, tags=SB)
async def get_storyboard(sb_id: SbId) -> dict[str, Any]:
    """작업본 전체. 정의서 링크가 `pending` 이면 이때 `sb.rq_sync` 를 시작하고 `active_job` 으로 알린다."""
    return service.to_api(await ops_core.get(sb_id))


class PatchStoryboardBody(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=60)
    step: int | None = Field(None, ge=1, le=5, description="(제안) 사람이 다음 단계로 넘어갈 때 — `요구 추적 확인` → 4, `일정 · 분담으로` → 5")


@router.patch("/storyboards/{sb_id}", response_model=Storyboard, tags=SB)
async def patch_storyboard(body: PatchStoryboardBody, sb_id: SbId) -> dict[str, Any]:
    return service.to_api(await ops_core.patch(sb_id, body.name, body.step))


@router.put("/storyboards/{sb_id}/requirement", status_code=202, response_model=JobAccepted, tags=SB)
async def put_requirement(body: PutRequirement, sb_id: SbId) -> JSONResponse:
    """SB1 다른 정의서 고르기 — `sb.prepare` 다시. step ≥ 2 면 409 STAGE_LOCKED."""
    return _accepted(await ops_core.put_requirement(sb_id, body.requirement_id, body.version), {"kind": "storyboard", "id": sb_id})


@router.post("/storyboards/{sb_id}/prepare", status_code=202, response_model=JobAccepted, tags=SB)
async def prepare(sb_id: SbId) -> JSONResponse:
    """정의서 다시 읽기(설정 · 기획 질의)."""
    return _accepted(await ops_core.prepare(sb_id), {"kind": "storyboard", "id": sb_id})


@router.patch("/storyboards/{sb_id}/settings", response_model=SettingsResult, tags=SB)
async def patch_settings(body: SettingsPatch, sb_id: SbId) -> dict[str, Any]:
    """SB1S — 바꾼 값은 `source=user`. 목차가 있으면 이후 생성부터 적용(Q-6)."""
    return {"settings": await ops_core.patch_settings(sb_id, body)}


# ── 기획 질의 · 방향 · 메시지(§6.2) ───────────────────────────

@router.get("/storyboards/{sb_id}/planning", response_model=Planning, tags=SB)
async def get_planning(sb_id: SbId) -> dict[str, Any]:
    return (await ops_core.get(sb_id))["planning"]


@router.put("/storyboards/{sb_id}/planning/{qid}", response_model=PlanningAnswer, tags=SB)
async def answer_planning(body: PutPlanningAnswer, sb_id: SbId, qid: str = Path(...)) -> dict[str, Any]:
    """답 저장(클릭마다). 순서 있는 복수 선택은 고른 순서대로. 비면 422 NOTHING_SELECTED."""
    return await ops_core.answer(sb_id, qid, body)


@router.post("/storyboards/{sb_id}/direction", status_code=202, response_model=JobAccepted, tags=SB)
async def start_direction(sb_id: SbId, body: PostDirection | None = None) -> JSONResponse:
    """`sb.direction` — `started=true`, step 2. `skip_planning` 이면 모든 질의 `unknown`."""
    return _accepted(await ops_core.start_direction(sb_id, body or PostDirection()), {"kind": "storyboard", "id": sb_id})


@router.get("/storyboards/{sb_id}/direction", response_model=Direction, tags=SB)
async def get_direction(sb_id: SbId) -> dict[str, Any]:
    return (await service.load(sb_id)).get("direction") or {}


@router.patch("/storyboards/{sb_id}/direction", response_model=PatchDirectionResult, tags=SB)
async def patch_direction(body: PatchDirection, sb_id: SbId) -> dict[str, Any]:
    """기획 방향 선택 · 방향 덧붙이기. 선택이 바뀌면 `sb.messages` 잡(`messages_job_id`)."""
    direction, job_id = await ops_core.patch_direction(sb_id, body)
    return {"direction": direction, "messages_job_id": job_id}


@router.get("/storyboards/{sb_id}/key-messages", response_model=KeyMessageList, tags=SB)
async def list_key_messages(sb_id: SbId) -> dict[str, Any]:
    """핵심 메시지(Key Message) — VP · 제안서 · MI 가 읽는다."""
    return {"items": ((await repo_doc(sb_id)).get("direction") or {}).get("key_messages") or []}


async def repo_doc(sb_id: str) -> dict[str, Any]:
    return await repo.require_sb(sb_id)


@router.patch("/storyboards/{sb_id}/key-messages/{kmsg}", response_model=KeyMessage, tags=SB)
async def patch_key_message(body: PatchKeyMessage, sb_id: SbId, kmsg: str = Path(...)) -> dict[str, Any]:
    """문장 고치기 — 표현 검사 다시 · 변경 기록. VP 가 다듬은 문장은 `source: {service: 'vp', ref_id}`."""
    return await ops_core.patch_key_message(sb_id, kmsg, body)


@router.post("/storyboards/{sb_id}/key-messages/{kmsg}/flags/{flg}/apply", response_model=KeyMessage, tags=SB)
async def apply_flag(sb_id: SbId, kmsg: str = Path(...), flg: str = Path(...)) -> dict[str, Any]:
    """`바꾸기`(검증 안 된 주장 → 대체안) · `빼기`(되돌렸던 내부 목표를 다시 뺀다)."""
    return await ops_core.flag_action(sb_id, kmsg, flg, "apply")


@router.post("/storyboards/{sb_id}/key-messages/{kmsg}/flags/{flg}/revert", response_model=KeyMessage, tags=SB)
async def revert_flag(sb_id: SbId, kmsg: str = Path(...), flg: str = Path(...)) -> dict[str, Any]:
    """`되돌리기` — 바꾸기 · 자동으로 뺀 내부 목표를 원래대로."""
    return await ops_core.flag_action(sb_id, kmsg, flg, "revert")


@router.post("/storyboards/{sb_id}/key-messages/{kmsg}/evidence", response_model=KeyMessage, status_code=201, tags=SB)
async def add_evidence(body: PostEvidence, sb_id: SbId, kmsg: str = Path(...)) -> dict[str, Any]:
    """MI4 `Key Message에 근거로 붙이기` — 웹이 근거 스냅숏을 올린다(SB 가 MI 를 부르지 않음, Q-2)."""
    return await ops_core.add_evidence(sb_id, kmsg, body)


class CompetitorImportResult(BaseModel):
    question: PlanningQuestion | None = None
    stored: bool = True


@router.post("/storyboards/{sb_id}/imports/competitor", response_model=CompetitorImportResult, tags=SB)
async def import_competitor(body: CompetitorImport, sb_id: SbId) -> dict[str, Any]:
    """경쟁사 분석 CA5 `Storyboard 비교 기준으로`(익명 묶음) → SB1Q3 `비교 기준` 질의의 `경쟁사 제안` 선택지 근거(Q-3)."""
    return {"question": await ops_core.import_competitor(sb_id, body), "stored": True}


# ── 목차 · 공간 · 논의(§6.3) ─────────────────────────────────

class PostOutlineBody(BaseModel):
    extra_direction: str | None = Field(None, max_length=400)
    retry: bool = Field(False, description="실패한 목차 잡 다시 시도 — 이미 쓴 섹션은 건너뛴다")


@router.post("/storyboards/{sb_id}/outline", status_code=202, response_model=JobAccepted, tags=SB)
async def start_outline(sb_id: SbId, body: PostOutlineBody | None = None) -> JSONResponse:
    """`sb.outline`(step 3). 실행 중이면 409 JOB_RUNNING."""
    b = body or PostOutlineBody()
    return _accepted(await ops_outline.start_outline(sb_id, b.extra_direction, b.retry), {"kind": "storyboard", "id": sb_id})


@router.get("/storyboards/{sb_id}/outline", response_model=Outline, tags=SB)
async def get_outline(sb_id: SbId) -> dict[str, Any]:
    """목차(잡 중이면 지금까지 쓴 것 + `writing`)."""
    return ops_outline.outline_of(await service.load(sb_id))


@router.get("/storyboards/{sb_id}/spaces/{spc}", response_model=Space, tags=SB)
async def get_space(sb_id: SbId, spc: str = Path(...)) -> dict[str, Any]:
    return ops_outline._space(await service.load(sb_id), spc)


@router.post("/storyboards/{sb_id}/spaces/{spc}/questions", response_model=SpaceQuestions, tags=SB, responses=ACCEPTED)
async def space_questions(sb_id: SbId, spc: str = Path(...)) -> Any:
    """빈 칸 질문 — 이미 있으면 200 `{questions}`, 없으면 202 `sb.space.questions`."""
    questions, job_id = await ops_outline.space_questions(sb_id, spc)
    if job_id:
        return _accepted(job_id, {"kind": "space", "id": spc})
    return {"questions": questions or []}


@router.put("/storyboards/{sb_id}/spaces/{spc}/slots/{slot}", response_model=SpaceSlotResult, tags=SB)
async def put_slot(body: PutSlot, sb_id: SbId, spc: str = Path(...),
                   slot: str = Path(..., description="action · trigger · response · exception · metric")) -> dict[str, Any]:
    """칸 답. `unknown` 이면 `[확인 필요]` + 정의서 고객 질문 추가(`customer_question_id`, 멱등)."""
    return await ops_outline.put_slot(sb_id, spc, slot, body)


@router.post("/storyboards/{sb_id}/spaces/{spc}/compose", status_code=202, response_model=JobAccepted, tags=SB)
async def compose_space(sb_id: SbId, spc: str = Path(...)) -> JSONResponse:
    """`sb.space.compose` — 답을 칸 문장으로 다듬기(AI 보탠 구간 표시 · `[00]` · 고객 질문 · 제품 후보)."""
    return _accepted(await ops_outline.compose(sb_id, spc), {"kind": "space", "id": spc})


class AgendaText(BaseModel):
    text: str


@router.post("/storyboards/{sb_id}/discussions/agenda", response_model=AgendaText, tags=SB)
async def discussions_agenda(sb_id: SbId) -> dict[str, Any]:
    """`회의 안건에 넣기` — 추가 논의를 안건 글로(웹이 클립보드에 복사, Q-8)."""
    return {"text": await ops_outline.agenda(sb_id)}


# ── 수정 요청 · 버전 · 변경 · 동기화(§6.4) ──────────────────────

@router.post("/storyboards/{sb_id}/revisions", status_code=202, response_model=JobAccepted, tags=SB)
async def create_revision(body: PostRevision, sb_id: SbId) -> JSONResponse:
    job_id, rev_id = await ops_outline.create_revision(sb_id, body)
    return _accepted(job_id, {"kind": "revision", "id": rev_id})


@router.get("/storyboards/{sb_id}/revisions/{rev}", response_model=Revision, tags=SB)
async def get_revision(sb_id: SbId, rev: str = Path(...)) -> dict[str, Any]:
    return await ops_outline.get_revision(sb_id, rev)


@router.post("/storyboards/{sb_id}/revisions/{rev}/apply", response_model=Storyboard, tags=SB)
async def apply_revision(sb_id: SbId, rev: str = Path(...)) -> dict[str, Any]:
    """`적용` — 작업본 반영 · 변경 기록(cause=revision) · 추적 다시 계산(백그라운드). 그 사이 대상이 바뀌었으면 409 REVISION_STALE."""
    return service.to_api(await ops_outline.apply_revision(sb_id, rev))


@router.post("/storyboards/{sb_id}/revisions/{rev}/discard", response_model=Revision, tags=SB)
async def discard_revision(sb_id: SbId, rev: str = Path(...)) -> dict[str, Any]:
    return await ops_outline.discard_revision(sb_id, rev)


@router.post("/storyboards/{sb_id}/save", response_model=SaveResult, status_code=201, tags=SB,
             responses={200: {"model": SaveResult, "description": "바뀐 것이 없어 버전 그대로(created=false)"}})
async def save(sb_id: SbId, body: SaveRequest | None = None) -> JSONResponse:
    """SB5 `저장하고 공유` — 버전 저장 · `status=done` · step 5."""
    version, created = await ops_outline.save(sb_id, (body or SaveRequest()).note)
    return _json(SaveResult, {"version": version, "created": created}, 201 if created else 200)


@router.get("/storyboards/{sb_id}/versions", response_model=VersionList, tags=SB)
async def list_versions(sb_id: SbId) -> dict[str, Any]:
    return {"items": await ops_outline.versions(sb_id), "next_cursor": None}


@router.get("/storyboards/{sb_id}/versions/{n}", response_model=StoryboardVersion, tags=SB)
async def get_version(sb_id: SbId, n: int = Path(..., ge=1)) -> dict[str, Any]:
    return await ops_outline.version(sb_id, n)


@router.post("/storyboards/{sb_id}/versions/{n}/restore", response_model=RestoreResult, status_code=201, tags=SB)
async def restore_version(sb_id: SbId, n: int = Path(..., ge=1)) -> dict[str, Any]:
    """옛 버전을 **새 버전**으로 되살린다(역사는 다시 쓰지 않음)."""
    return {"version": await ops_outline.restore(sb_id, n)}


@router.get("/storyboards/{sb_id}/compare", response_model=Compare, tags=SB)
async def compare(sb_id: SbId, frm: int | None = Query(None, alias="from", ge=0),
                  to: str | None = Query(None, description="버전 번호 또는 draft(작업본)")) -> JSONResponse:
    """SB3V — 기본 from = 최신 저장 버전, to = 작업본. `count` = 변경 + 추가 + 삭제(유지 제외, Q-1)."""
    return _json(Compare, await ops_outline.compare(sb_id, frm, to))


@router.post("/storyboards/{sb_id}/changes/{chg}/revert", response_model=Storyboard, tags=SB)
async def revert_change(sb_id: SbId, chg: str = Path(...)) -> dict[str, Any]:
    """행별 `되돌리기` — 되돌릴 수 없으면 409 NOT_REVERTIBLE."""
    return service.to_api(await ops_outline.revert_change(sb_id, chg))


@router.post("/storyboards/{sb_id}/requirement-sync", status_code=202, response_model=JobAccepted, tags=SB)
async def requirement_sync(body: RequirementSyncRequest, sb_id: SbId) -> JSONResponse:
    """정의서 새 버전 반영(`sb.rq_sync`). `dry_run` 이면 미리 보기(`ref.kind=sync_preview`) — 작업본 · 링크 불변. RQ7B 웹이 부른다."""
    job_id, ref = await ops_outline.requirement_sync(sb_id, body)
    return _accepted(job_id, ref)


@router.get("/storyboards/{sb_id}/sync-previews/{syp}", response_model=SyncPreview, tags=SB)
async def get_sync_preview(sb_id: SbId, syp: str = Path(...)) -> dict[str, Any]:
    return await ops_outline.preview(sb_id, syp)


# ── 요구 추적 · 일정 · 저장 이후(§6.5) ─────────────────────────

@router.get("/storyboards/{sb_id}/trace", response_model=Trace, tags=SB)
async def get_trace(sb_id: SbId) -> dict[str, Any]:
    """요구 추적(`to_resolve` 는 `priority` 순으로 정리)."""
    tr = (await service.load(sb_id)).get("trace") or {}
    items = sorted(tr.get("items") or [], key=lambda i: i.get("code", ""))
    return {**tr, "items": items}


@router.put("/storyboards/{sb_id}/trace/items/{rq_item_id}/resolution", response_model=ResolutionResult, tags=SB)
async def put_resolution(body: PutResolution, sb_id: SbId, rq_item_id: str = Path(...)) -> dict[str, Any]:
    """SB4U — 놓기(`sb.trace.apply` 잡) · 확인 필요로 유지 · 본제안으로 미루기 · 제외(사유 필수) · 고객에게 묻기. 버리는 요구는 없다."""
    item, job_id = await ops_after.resolve(sb_id, rq_item_id, body)
    return {"item": item, "apply_job_id": job_id}


class Ok(BaseModel):
    ok: bool = True


@router.post("/storyboards/{sb_id}/trace/extensions/acknowledge", response_model=Ok, tags=SB)
async def acknowledge_extensions(sb_id: SbId) -> dict[str, Any]:
    """SB4X `확인했어요` — 확장은 고객 요구(정의서)로 쓰지 않는다."""
    await ops_after.ack_extensions(sb_id)
    return {"ok": True}


@router.get("/storyboards/{sb_id}/schedule", response_model=Schedule, tags=SB)
async def get_schedule(sb_id: SbId) -> dict[str, Any]:
    """SB5 — 6단계 · 담당 · D-범위 · 현재 단계."""
    return (await service.load(sb_id))["schedule"]


@router.post("/storyboards/{sb_id}/exports", status_code=202, response_model=JobAccepted, tags=SB)
async def start_export(body: ExportRequest, sb_id: SbId) -> JSONResponse:
    """SB4E — 작업본 ≠ 최신 버전이면 먼저 저장 → `sb.export` 잡(결과 `{file_id, name, url}`). 표시 유지는 항상 켬."""
    return _accepted(await ops_after.start_export(sb_id, body), {"kind": "storyboard", "id": sb_id})


@router.post("/storyboards/{sb_id}/share", response_model=ShareResult, tags=SB)
async def share(sb_id: SbId) -> dict[str, Any]:
    """SB3D `공유` — 내부 공유 링크(workspace)."""
    return {"url": await ops_after.share(sb_id)}


class ReviewBody(ReviewRequestBody):
    reviewers: list[str] | None = Field(None, description="검토자 user id(없으면 workspace 사용자 중 한 명)")


@router.post("/storyboards/{sb_id}/review-requests", response_model=ReviewRequestResult, status_code=201, tags=SB)
async def review_request(sb_id: SbId, body: ReviewBody | None = None) -> dict[str, Any]:
    """SB4 `내부 검토 요청` — workspace 검토 요청 · `status=shared`."""
    b = body or ReviewBody()
    return await ops_after.review_request(sb_id, b.note, b.reviewers)


@router.get("/storyboards/{sb_id}/handoffs", response_model=HandoffList, tags=SB)
async def list_handoffs(sb_id: SbId) -> dict[str, Any]:
    """SB4 `다음에 할 일` 3 — 제안서 · MI · 공간 시나리오."""
    return {"items": await ops_after.handoff_cards(sb_id)}


@router.post("/storyboards/{sb_id}/handoffs/{target}", response_model=HandoffResult, tags=SB)
async def record_handoff(sb_id: SbId, target: Literal["proposal", "mi", "scenario"] = Path(...)) -> dict[str, Any]:
    """넘김 기록(→ `status=shared`, SB0 `… 넘겼어요`) — 응답 `route` 로 이동."""
    return {"route": await ops_after.handoff(sb_id, target)}


@router.get("/storyboards/{sb_id}/proposal-handoff", response_model=ProposalHandoff, tags=SB)
async def proposal_handoff(sb_id: SbId, type: str = Query("standard", description="standard · quickwin · solution"),  # noqa: A002
                           section: str | None = Query(None, description="vp · mi · why · space_scenario …(없으면 전부)")) -> dict[str, Any]:
    """ProposalHandoff v1(10-proposal.md §8.0 S1) — 고객 · Key Message · 제안 전략 · 목차 · 공간 · 자리표시 수치."""
    return await ops_after.proposal_handoff(sb_id, type, section)
