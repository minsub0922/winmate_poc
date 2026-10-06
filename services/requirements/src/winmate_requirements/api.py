"""requirements API (/v1). 이 파일의 엔드포인트가 contracts/requirements.json 이 된다(make contracts).

문서: docs/scenarios/01-requirements.md §6. 오래 걸리는 일(파일로 채우기 · 보강할 곳 찾기 · 답변 분석 · 내보내기)은
202 + 잡, 심층 작성 질의응답 · 메일 초안은 동기 REST(§6.4 결정).
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Path, Query, Response
from fastapi.responses import JSONResponse

from . import deep, exports, mail, replies, service
from .models import (
    AcceptProposal,
    AcceptResult,
    AddFiles,
    AnswerRequest,
    AnswerResult,
    ApplyReply,
    ApplyResult,
    ConsumerService,
    Counts,
    CreateCustomerQuestion,
    CreateReply,
    CreateRequirement,
    CustomerQuestion,
    CustomerQuestionList,
    DeepSession,
    Diff,
    ExportRecord,
    ExportRequest,
    FromFiles,
    JobAccepted,
    LinkList,
    MailDraft,
    MailDraftRequest,
    PatchCustomerQuestion,
    PatchDraft,
    PatchReply,
    ReplyAnalysis,
    Requirement,
    RequirementList,
    RequirementVersion,
    RestoreResult,
    ReviseProposal,
    ReviseResult,
    SaveRequest,
    SaveResult,
    SelectGaps,
    ServiceInfo,
    ShareResult,
    UpsertLink,
    UsageLink,
    VersionList,
)

router = APIRouter(prefix="/v1")
RQ = "requirements"

RqId = Path(description="정의서 id(rq_<ULID>)")
ServiceName = Path(description="쓰는 서비스(storyboard · mi · competitor · vp · spec · proposal)")
RefId = Path(description="그 서비스의 자원 id(예: sb_<ULID>)")


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="requirements", title="고객 요구사항 — 입력 폼 · 파일로 채우기 · 심층 작성 · 고객 질문 · 정의서 버전",
                       version="0.2.0")


# ── 정의서(§6.1) ─────────────────────────────────────────

@router.post("/requirements", response_model=Requirement, status_code=201, tags=[RQ],
             summary="정의서 만들기(RQ1 첫 입력 · 심층 작성 · 파일 놓기)")
async def create_requirement(body: CreateRequirement | None = None) -> dict:
    body = body or CreateRequirement()
    doc = await service.create(body.project_id, body.form.model_dump() if body.form else None)
    return await service.present_doc(doc)


@router.get("/requirements", response_model=RequirementList, tags=[RQ],
            summary="정의서 목록(RQ0 · Storyboard SB1 has_version=true · 경쟁사 CA1R · 제안서 R1)")
async def list_requirements(
    tab: Literal["all", "in_progress", "saved"] = Query("all", description="all | in_progress | saved"),
    q: str | None = Query(None, description="제목 · 고객사 · 프로젝트명 · 키맨 이름 부분 일치"),
    has_version: bool | None = Query(None, description="true 면 저장된 버전(v1 이상)이 있는 것만"),
    customer: str | None = Query(None, description="고객사 부분 일치(제안서 R1)"),
    project_id: str | None = Query(None),
    owner: str = Query("me", description="me | all | <user id>"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> dict:
    items, nxt = await service.list_requirements(tab=tab, q=q, has_version=has_version, customer=customer,
                                                 project_id=project_id, owner=owner, limit=limit, cursor=cursor)
    return {"items": items, "next_cursor": nxt}


@router.get("/requirements/counts", response_model=Counts, tags=[RQ], summary="RQ0 탭 개수")
async def requirement_counts(q: str | None = None, owner: str = Query("me")) -> dict:
    return await service.counts(q, owner)


@router.post("/requirements/from-files", response_model=JobAccepted, status_code=202, tags=[RQ],
             summary="파일로 새 정의서 만들기(제안서 PR1F R3) — 새 정의서 + rq.fill 잡")
async def create_from_files(body: FromFiles) -> dict:
    return await service.from_files(body.file_ids, body.customer_hint, body.project_id)


@router.get("/requirements/{rq_id}", response_model=Requirement, tags=[RQ], summary="정의서(작업본 + 메타)")
async def get_requirement(rq_id: str = RqId) -> dict:
    return await service.present_doc(await service.get(rq_id))


@router.patch("/requirements/{rq_id}/draft", response_model=Requirement, tags=[RQ],
              summary="작업본 편집(자동 저장 · 모든 폼 편집) — 409 REVISION_CONFLICT 면 다시 읽고 적용")
async def patch_draft(body: PatchDraft, rq_id: str = RqId) -> dict:
    return await service.patch_draft(rq_id, body.base_revision, [op.model_dump() for op in body.ops])


@router.post("/requirements/{rq_id}/save", response_model=SaveResult, status_code=201, tags=[RQ],
             summary="버전 저장 — 바뀐 것이 없으면 200 {created:false}",
             responses={200: {"model": SaveResult, "description": "작업본이 최신 버전과 같아 버전 그대로"}})
async def save_requirement(body: SaveRequest | None = None, rq_id: str = RqId):
    body = body or SaveRequest()
    n, created, doc = await service.save(rq_id, body.reason, body.note)
    if not created:
        return JSONResponse(SaveResult(version=n, created=False).model_dump(mode="json"), status_code=200)
    return {"version": n, "created": True, "requirement": await service.present_doc(doc)}


@router.post("/requirements/{rq_id}/share", response_model=ShareResult, tags=[RQ], summary="내부 공유 링크(RQ6 공유)")
async def share_requirement(rq_id: str = RqId) -> dict:
    return await service.share(rq_id)


# ── 파일로 채우기(§6.2) ───────────────────────────────────

@router.post("/requirements/{rq_id}/files", response_model=JobAccepted, status_code=202, tags=[RQ],
             summary="파일 넣기 → rq.fill 잡(채우는 중이면 뒤에 줄 선다)")
async def add_files(body: AddFiles, rq_id: str = RqId) -> dict:
    return await service.add_files(rq_id, body.file_ids)


@router.delete("/requirements/{rq_id}/files/{file_id}", response_model=Requirement, tags=[RQ],
               summary="파일 빼기 — rollback=true 면 그 파일에서 와서 사람이 안 고친 값 · 항목 · 키맨도 지운다")
async def remove_file(rq_id: str = RqId, file_id: str = Path(), rollback: bool = Query(True)) -> dict:
    return await service.present_doc(await service.remove_file(rq_id, file_id, rollback))


@router.post("/requirements/{rq_id}/files/{file_id}/restore", response_model=Requirement, tags=[RQ],
             summary="파일 빼기 되돌리기(재추출 없이 스냅숏 복원)")
async def restore_file(rq_id: str = RqId, file_id: str = Path()) -> dict:
    return await service.present_doc(await service.restore_file(rq_id, file_id))


# ── 버전(§6.5) ───────────────────────────────────────────

@router.get("/requirements/{rq_id}/versions", response_model=VersionList, tags=[RQ], summary="버전 목록(최신순)")
async def list_versions(rq_id: str = RqId) -> dict:
    return {"items": await service.list_versions(rq_id), "next_cursor": None}


@router.get("/requirements/{rq_id}/versions/{n}", response_model=RequirementVersion, tags=[RQ],
            summary="저장 스냅숏(불변) — n 은 숫자 또는 latest")
async def get_version(rq_id: str = RqId, n: str = Path(pattern=r"^(\d+|latest)$", description="버전 번호 또는 latest")) -> dict:
    return await service.get_version(rq_id, n)


@router.post("/requirements/{rq_id}/versions/{n}/restore", response_model=RestoreResult, status_code=201, tags=[RQ],
             summary="이 버전으로 되돌리기(새 버전 생성)")
async def restore_version(rq_id: str = RqId, n: int = Path(ge=1)) -> dict:
    return {"version": await service.restore(rq_id, n)}


@router.get("/requirements/{rq_id}/diff", response_model=Diff, tags=[RQ], summary="두 버전 비교(항목 id 기준)")
async def diff_versions(rq_id: str = RqId, from_: int = Query(alias="from", ge=1), to: int = Query(ge=1)) -> dict:
    return await service.diff(rq_id, from_, to)


# ── 심층 작성(§6.4) ──────────────────────────────────────

@router.post("/requirements/{rq_id}/deep-sessions", response_model=JobAccepted, status_code=202, tags=[RQ],
             summary="심층 작성 시작 → rq.deep.analyze 잡 · 진행 중 세션이 있으면 409 SESSION_ACTIVE")
async def create_deep_session(rq_id: str = RqId) -> dict:
    return await deep.create_session(rq_id)


@router.get("/requirements/{rq_id}/deep-sessions/{sid}", response_model=DeepSession, tags=[RQ],
            summary="세션(조회 때 규칙형 보강할 곳을 다시 평가)")
async def get_deep_session(rq_id: str = RqId, sid: str = Path()) -> dict:
    return await deep.get_session(rq_id, sid)


@router.patch("/requirements/{rq_id}/deep-sessions/{sid}", response_model=DeepSession, tags=[RQ],
              summary="다룰 곳 선택(ready 일 때만)")
async def select_deep_gaps(body: SelectGaps, rq_id: str = RqId, sid: str = Path()) -> dict:
    return await deep.select_gaps(rq_id, sid, body.selected_gap_ids)


@router.post("/requirements/{rq_id}/deep-sessions/{sid}/reanalyze", response_model=JobAccepted, status_code=202,
             tags=[RQ], summary="다시 분석(폼이 크게 바뀐 ready 세션 · 실패한 분석)")
async def reanalyze_deep_session(rq_id: str = RqId, sid: str = Path()) -> dict:
    return await deep.reanalyze(rq_id, sid)


@router.post("/requirements/{rq_id}/deep-sessions/{sid}/start", response_model=DeepSession, tags=[RQ],
             summary="질의 시작(asking) — 선택 0이면 422 NOTHING_SELECTED")
async def start_deep_session(rq_id: str = RqId, sid: str = Path()) -> dict:
    return await deep.start(rq_id, sid)


@router.post("/requirements/{rq_id}/deep-sessions/{sid}/answers", response_model=AnswerResult, tags=[RQ],
             summary="답 하나 처리(동기 LangGraph rq_deep_answer, 30초)")
async def answer_deep(body: AnswerRequest, rq_id: str = RqId, sid: str = Path()) -> dict:
    return await deep.answer(rq_id, sid, body.model_dump())


@router.post("/requirements/{rq_id}/deep-sessions/{sid}/proposals/{pid}/accept", response_model=AcceptResult,
             tags=[RQ], summary="반영 제안 반영(고친 문장 · 부수 효과 선택)")
async def accept_proposal(body: AcceptProposal | None = None, rq_id: str = RqId, sid: str = Path(), pid: str = Path()) -> dict:
    body = body or AcceptProposal()
    return await deep.accept(rq_id, sid, pid, body.edited_text,
                             [s.model_dump() for s in body.side_effects] if body.side_effects is not None else None)


@router.post("/requirements/{rq_id}/deep-sessions/{sid}/proposals/{pid}/revise", response_model=ReviseResult,
             tags=[RQ], summary="반영 제안 다시 쓰기(고칠 지시)")
async def revise_proposal(body: ReviseProposal, rq_id: str = RqId, sid: str = Path(), pid: str = Path()) -> dict:
    return await deep.revise(rq_id, sid, pid, body.instruction)


@router.post("/requirements/{rq_id}/deep-sessions/{sid}/finish", response_model=DeepSession, tags=[RQ],
             summary="끝내기 → finished(result · completeness_after)")
async def finish_deep_session(rq_id: str = RqId, sid: str = Path()) -> dict:
    return await deep.finish(rq_id, sid)


@router.delete("/requirements/{rq_id}/deep-sessions/{sid}", response_model=DeepSession, tags=[RQ],
               summary="세션 취소(canceled — 이미 반영한 값은 남음)")
async def cancel_deep_session(rq_id: str = RqId, sid: str = Path()) -> dict:
    return await deep.cancel(rq_id, sid)


# ── 고객 질문 · 메일(§6.6) ───────────────────────────────

@router.get("/requirements/{rq_id}/customer-questions", response_model=CustomerQuestionList, tags=[RQ],
            summary="고객에게 물을 것")
async def list_customer_questions(rq_id: str = RqId, status: Literal["open", "answered", "dismissed", "all"] = "open") -> dict:
    return {"items": await service.list_questions(rq_id, status), "next_cursor": None}


@router.post("/requirements/{rq_id}/customer-questions", response_model=CustomerQuestion, status_code=201, tags=[RQ],
             summary="고객 질문 추가(Storyboard · 제안서 · 수동) — 같은 origin.ref_id + text 면 200 기존 것",
             responses={200: {"model": CustomerQuestion, "description": "이미 있는 질문(멱등)"}})
async def create_customer_question(body: CreateCustomerQuestion, rq_id: str = RqId):
    q, created = await service.add_question(rq_id, body.model_dump())
    if not created:
        return JSONResponse(CustomerQuestion.model_validate(q).model_dump(mode="json"), status_code=200)
    return q


@router.patch("/requirements/{rq_id}/customer-questions/{qid}", response_model=CustomerQuestion, tags=[RQ],
              summary="메일에 넣기 체크 · 없애기(dismissed)")
async def patch_customer_question(body: PatchCustomerQuestion, rq_id: str = RqId, qid: str = Path()) -> dict:
    return await service.patch_question(rq_id, qid, body.model_dump(exclude_none=True))


@router.post("/requirements/{rq_id}/customer-questions/mail-draft", response_model=MailDraft, tags=[RQ],
             summary="메일 문구(체크한 질문만 · 내부 정보 제외, 15초 넘으면 템플릿)")
async def mail_draft(body: MailDraftRequest, rq_id: str = RqId) -> dict:
    return await mail.draft(rq_id, body.question_ids)


# ── 고객 답변(§6.7) ──────────────────────────────────────

@router.post("/requirements/{rq_id}/replies", response_model=JobAccepted, status_code=202, tags=[RQ],
             summary="고객 답변 붙여넣기 → rq.reply.analyze 잡 · 둘 다 비면 422 EMPTY_REPLY")
async def create_reply(body: CreateReply, rq_id: str = RqId) -> dict:
    return await replies.create(rq_id, body.text, body.file_ids)


@router.get("/requirements/{rq_id}/replies/{rid}", response_model=ReplyAnalysis, tags=[RQ],
            summary="답변 분석(Storyboard 미리 보기도 읽음)")
async def get_reply(rq_id: str = RqId, rid: str = Path()) -> dict:
    return await replies.get(rq_id, rid)


@router.patch("/requirements/{rq_id}/replies/{rid}", response_model=ReplyAnalysis, tags=[RQ],
              summary="바뀔 곳 선택(storyboard_impact 다시 계산)")
async def patch_reply(body: PatchReply, rq_id: str = RqId, rid: str = Path()) -> dict:
    return await replies.select(rq_id, rid, body.selected_change_ids)


@router.post("/requirements/{rq_id}/replies/{rid}/apply", response_model=ApplyResult, status_code=201, tags=[RQ],
             summary="선택한 변경 반영 → 새 버전(reason=reply), 링크 sync_state=pending")
async def apply_reply(body: ApplyReply, rq_id: str = RqId, rid: str = Path()) -> dict:
    return await replies.apply(rq_id, rid, body.selected_change_ids, list(body.propagate), body.note)


# ── 쓰는 곳 링크(§6.8) ───────────────────────────────────

@router.get("/requirements/{rq_id}/links", response_model=LinkList, tags=[RQ], summary="이 정의서를 쓰는 곳(RQ6 쓰는 곳)")
async def list_links(rq_id: str = RqId) -> dict:
    return {"items": await service.list_links(rq_id)}


@router.put("/requirements/{rq_id}/links/{service_name}/{ref_id}", response_model=UsageLink, tags=["internal"],
            summary="링크 등록 · 갱신(소비 서비스가 호출, 멱등)")
async def upsert_link(body: UpsertLink, rq_id: str = RqId, service_name: ConsumerService = ServiceName,
                      ref_id: str = RefId) -> dict:
    return await service.upsert_link(rq_id, service_name, ref_id, body.model_dump())


@router.delete("/requirements/{rq_id}/links/{service_name}/{ref_id}", status_code=204, tags=["internal"],
               summary="링크 지우기", response_class=Response)
async def delete_link(rq_id: str = RqId, service_name: ConsumerService = ServiceName, ref_id: str = RefId) -> Response:
    await service.delete_link(rq_id, service_name, ref_id)
    return Response(status_code=204)


# ── 내보내기(§6.9, 제안) ─────────────────────────────────

@router.post("/requirements/{rq_id}/exports", response_model=JobAccepted, status_code=202, tags=[RQ],
             summary="정의서 DOCX · PDF(제작자 의견 · 내부 메모 항상 제외)")
async def create_export(body: ExportRequest | None = None, rq_id: str = RqId) -> dict:
    body = body or ExportRequest()
    return await exports.create(rq_id, body.format, body.version)


@router.get("/requirements/{rq_id}/exports/{export_id}", response_model=ExportRecord, tags=[RQ], summary="내보내기 결과")
async def get_export(rq_id: str = RqId, export_id: str = Path()) -> dict:
    return await exports.get(rq_id, export_id)
