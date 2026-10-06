"""storyboard 자원 · 요청 · 응답 모델(docs/scenarios/02-storyboard.md §5 · §6).

이 모델들이 contracts/storyboard.json 의 스키마가 된다. 저장은 dict(JSON) 그대로 하고, 응답 때 이 모델로 검증한다.
- ID 접두사: sb_ pq_ opt_ dir_ kmsg_ flg_ sec_ spc_ dsc_ ext_ rev_ chg_ syp_ phs_ (`<접두사>_<ULID>`)
- 저장 버전 번호는 내부 필드 `saved_version` 으로 두고(DocStore 의 version 과 겹치지 않게) 응답의 `version` 으로 낸다.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# ── 공통 값 ────────────────────────────────────────────────

SettingSource = Literal["rq", "user", "default"]
Stage = Literal["concept", "main"]
DocType = Literal["common_pitch", "custom"]
Language = Literal["ko", "en", "ko_en"]
SbStatus = Literal["in_progress", "done", "shared"]
SectionStatus = Literal["confirmed", "reviewing", "needs_confirmation", "writing", "tbd"]
SpaceStatus = Literal["empty", "draft", "supplemented"]
SlotKey = Literal["action", "trigger", "response", "exception", "metric"]
SlotState = Literal["empty", "filled", "unknown"]
TraceState = Literal["ok", "to_resolve", "owner_check", "resolved"]
LinkType = Literal["direct", "interpreted", "extension", "reviewing", "unconfirmed", "deferred", "excluded"]
ResolutionKind = Literal["place", "keep_unconfirmed", "defer_main", "exclude", "ask_customer"]
ChangeKind = Literal["changed", "added", "removed", "kept"]
CauseKind = Literal["rq_sync", "revision", "space_questions", "trace", "vp", "user", "restore"]
HandoffTarget = Literal["proposal", "mi", "scenario"]


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Owner(_M):
    id: str
    name: str = ""


class ActiveJob(_M):
    job_id: str
    kind: str


class JobAccepted(_M):
    """202 — 잡을 큐에 넣었다. 진행은 jobs SSE, 결과는 자원을 다시 읽는다."""
    job_id: str
    status: Literal["queued"] = "queued"
    ref: dict[str, str] | None = Field(None, description="만들어진 자원 {kind, id}")


# ── 정의서 참조 · 설정 ──────────────────────────────────────

class RequirementRef(_M):
    requirement_id: str
    version: int = Field(description="이 스토리보드가 근거로 쓰는 정의서 버전")
    title: str = ""
    item_count: int = 0
    latest_version: int = Field(0, description="정의서의 최신 저장 버전(새 버전 띠 판단)")
    project_id: str | None = None
    customer_name: str | None = None
    open_question_count: int = 0
    saved_at: str | None = None
    version_note: str | None = None


class StageSetting(_M):
    value: Stage = "concept"
    source: SettingSource = "default"
    evidence: str | None = None


class DocTypeSetting(_M):
    value: DocType = "custom"
    source: SettingSource = "default"
    evidence: str | None = None


class VolumeSetting(_M):
    value: Literal[12, 20, 30] = 20
    source: SettingSource = "default"
    evidence: str | None = Field(None, description="분량 힌트(공간 수 규칙) — 예 `7개 공간을 담으려면 20장 이상`")


class LanguageSetting(_M):
    value: Language = "ko"
    source: SettingSource = "default"
    evidence: str | None = None


class Settings(_M):
    stage: StageSetting = Field(default_factory=StageSetting)
    doc_type: DocTypeSetting = Field(default_factory=DocTypeSetting)
    volume: VolumeSetting = Field(default_factory=VolumeSetting)
    language: LanguageSetting = Field(default_factory=LanguageSetting)
    summary: str = Field("", description="SB1 설정 줄 — 4값을 ` · ` 로")
    all_from_rq: bool = Field(False, description="4값이 모두 정의서에서 왔다 → `정의서에서 읽었어요`")
    ready: bool = Field(False, description="prepare 가 끝나 값이 채워졌다")


# ── 기획 질의 ──────────────────────────────────────────────

class FollowUpOption(_M):
    id: str
    label: str
    effect: Literal["use_public", "internal_only", "placeholder"]


class FollowUp(_M):
    label: str = "이어서 하나만"
    text: str
    options: list[FollowUpOption]


class PlanningOption(_M):
    id: str
    label: str
    hint: str | None = None
    badge: str | None = None
    follow_up: FollowUp | None = None
    recommended: bool = False
    custom: bool = Field(False, description="직접 입력으로 더한 선택지")
    evidence: str | None = Field(None, description="다른 기능에서 받은 근거(예 경쟁사 비교 기준)")


class PlanningQuestion(_M):
    id: str
    order: int
    topic: str = Field(description="decision | audience | comparison | budget_scope | timeline")
    topic_label: str
    text: str
    info: str
    select: Literal["multi_ordered", "single"]
    order_roles: list[str] = Field(default_factory=list)
    allow_custom: bool = True
    options: list[PlanningOption]
    affects: list[str] = Field(default_factory=list)


class PlanningAnswer(_M):
    question_id: str
    selected_option_ids: list[str] = Field(default_factory=list, description="고른 순서")
    custom_text: str | None = None
    unknown: bool = False
    follow_up_option_id: str | None = None
    answered_at: str | None = None
    roles: dict[str, str] = Field(default_factory=dict, description="고른 선택지 → 순서 역할(`Overview 목적` · `Outro 다음 단계`)")


class Planning(_M):
    questions: list[PlanningQuestion] = Field(default_factory=list)
    answers: list[PlanningAnswer] = Field(default_factory=list)


class PutPlanningAnswer(_M):
    selected_option_ids: list[str] | None = None
    custom_text: str | None = Field(None, description="직접 입력 — 선택지로 더해지고 마지막 순서로 고른다(빈 글이면 뺀다)")
    unknown: bool | None = None
    follow_up_option_id: str | None = None


# ── 기획 방향 · 핵심 메시지 ──────────────────────────────────

class Coverage(_M):
    item_ids: list[str] = Field(default_factory=list)
    codes: list[str] = Field(default_factory=list)
    count: int = 0
    total: int = 0


class MappingRow(_M):
    place_label: str
    axis_key: str
    axis_label: str = ""


class DirectionOption(_M):
    id: str
    kind: Literal["combo", "axis"]
    key: str | None = None
    title: str
    one_liner: str = ""
    coverage: Coverage = Field(default_factory=Coverage)
    mapping: list[MappingRow] = Field(default_factory=list)


class Flag(_M):
    id: str
    kind: Literal["unverified_claim", "internal_goal"]
    span: list[int] = Field(default_factory=list, description="[start, end] — 지금 문장 기준(빠진 구간이면 빈 배열)")
    span_text: str
    note: str
    suggestion: str | None = None
    auto_applied: bool = False
    state: Literal["open", "applied", "reverted"] = "open"
    original_text: str | None = None


class EvidenceSource(_M):
    service: str
    ref_id: str
    title: str = ""
    route: str | None = None


class Citation(_M):
    title: str
    url: str | None = None


class Evidence(_M):
    id: str | None = None
    source: EvidenceSource
    text: str
    citations: list[Citation] = Field(default_factory=list)
    added_at: str | None = None


class KeyMessage(_M):
    id: str
    place_label: str
    axis_key: str | None = None
    axis_label: str = ""
    audience: str = ""
    text: str
    flags: list[Flag] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    kb_refs: list[str] = Field(default_factory=list)
    updated_by: Literal["llm", "user", "vp"] = "llm"


class InternalMemo(_M):
    text: str
    from_: Literal["flag", "rq_author_note"] = Field("flag", alias="from")
    flag_id: str | None = None


class Direction(_M):
    options: list[DirectionOption] = Field(default_factory=list)
    recommended_option_id: str | None = None
    selected_option_id: str | None = None
    key_messages: list[KeyMessage] = Field(default_factory=list)
    extra_direction: str | None = None
    internal_memos: list[InternalMemo] = Field(default_factory=list)
    internal_goal_count: int = 0
    total: int = Field(0, description="정의서 항목 수 N")
    ready: bool = False


class PostDirection(_M):
    skip_planning: bool = False


class PatchDirection(_M):
    selected_option_id: str | None = None
    extra_direction: str | None = None


class PatchDirectionResult(_M):
    direction: Direction
    messages_job_id: str | None = None


class KeyMessageList(_M):
    items: list[KeyMessage]


class PatchKeyMessage(_M):
    text: str = Field(min_length=1, max_length=400)
    source: dict[str, str] | None = Field(None, description="{service: 'vp', ref_id} — VP 가 다듬은 문장을 되돌려 쓸 때")


class PostEvidence(_M):
    source: EvidenceSource
    text: str = Field(min_length=1, max_length=2000)
    citations: list[Citation] = Field(default_factory=list)


# ── 목차 ──────────────────────────────────────────────────

class Badge(_M):
    label: str
    style: Literal["fill", "soft", "line", "dashed", "draft", "muted", "tbd", "ext"]


class Group(_M):
    key: Literal["start", "part1", "part2", "part3", "end"]
    order: int
    name: str
    meta: str = ""
    summary: str = ""
    badges: list[Badge] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)


class Line(_M):
    id: str
    text: str
    tokens: list[str] = Field(default_factory=list)
    reviewing: bool = False
    claim: bool = Field(False, description="출처 없는 주장 표현(최초 · 1위 …) — 섹션 확인 필요")


class KbRef(_M):
    kind: str
    id: str


class ProductRef(_M):
    name: str
    kb_ref: KbRef | None = None
    is_extension: bool = False


class Section(_M):
    id: str
    key: str = Field(description="자리 키(overview · key_considerations · intro · p1_1 … · part2 · p3_1 … · outro · timeline)")
    group_key: Literal["start", "part1", "part2", "part3", "end"]
    order: int
    code: str | None = None
    name: str
    direction: str = ""
    lines: list[Line] = Field(default_factory=list)
    products: list[ProductRef] = Field(default_factory=list)
    status: SectionStatus = "writing"
    tbd_reason: str | None = None
    internal_memo: str | None = None
    discussion_ids: list[str] = Field(default_factory=list)
    written: bool = True


class Segment(_M):
    text: str
    ai_added: bool = False
    placeholder: Literal["[00]", "[확인 필요]"] | None = None


class SlotAnswer(_M):
    selected_option_ids: list[str] = Field(default_factory=list)
    custom_text: str | None = None
    labels: list[str] = Field(default_factory=list)


class Slot(_M):
    state: SlotState = "empty"
    segments: list[Segment] = Field(default_factory=list)
    source: Literal["outline", "answer", "compose", "revision", "rq_sync", "trace"] | None = None
    answer: SlotAnswer | None = None
    customer_question_id: str | None = None


class SlotQuestionOption(_M):
    id: str
    label: str


class SlotQuestion(_M):
    slot: SlotKey
    text: str
    info: str
    options: list[SlotQuestionOption]
    select: Literal["multi_ordered"] = "multi_ordered"
    allow_custom: bool = True


class AddedQuestion(_M):
    id: str
    short_label: str


class Space(_M):
    id: str
    key: str = Field("", description="공간 유형(kb space_type 또는 슬러그)")
    order: int
    name: str
    purpose: str = ""
    is_extension: bool = False
    status: SpaceStatus = "draft"
    slots: dict[str, Slot] = Field(default_factory=dict, description="action · trigger · response · exception · metric")
    filled_count: int = 0
    products: list[ProductRef] = Field(default_factory=list)
    questions: list[SlotQuestion] = Field(default_factory=list)
    customer_question_ids: list[str] = Field(default_factory=list)
    added_questions: list[AddedQuestion] = Field(default_factory=list, description="이번 질의 · 다듬기로 정의서에 더한 고객 질문")
    composing: bool = False


class Discussion(_M):
    id: str
    n: int
    label: str
    short: str = ""
    section_ids: list[str] = Field(default_factory=list)
    trace_item_ids: list[str] = Field(default_factory=list)
    state: Literal["open", "resolved"] = "open"


class Writing(_M):
    done: int = 0
    total: int = 0
    stage: str | None = None


class Outline(_M):
    groups: list[Group] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    spaces: list[Space] = Field(default_factory=list)
    discussions: list[Discussion] = Field(default_factory=list)
    writing: Writing | None = None
    ready: bool = False


class PostOutline(_M):
    extra_direction: str | None = None


class SpaceQuestions(_M):
    questions: list[SlotQuestion]


class PutSlot(_M):
    selected_option_ids: list[str] | None = None
    custom_text: str | None = None
    unknown: bool | None = None


class SpaceSlotResult(Space):
    customer_question_id: str | None = Field(None, description="`unknown` 이면 정의서에 더한 고객 질문 id")


class AgendaText(_M):
    text: str


# ── 요구 추적 ──────────────────────────────────────────────

class Place(_M):
    kind: Literal["section", "space", "customer_question", "owner_check"]
    id: str | None = None
    label: str


class PlaceTarget(_M):
    kind: Literal["section", "space"]
    id: str
    label: str = ""


class TraceOption(_M):
    id: str
    label: str
    hint: str = ""
    kind: Literal["place", "keep_unconfirmed", "defer_main", "exclude"]
    target: PlaceTarget | None = None


class TraceQuestion(_M):
    text: str
    info: str = ""
    options: list[TraceOption]
    recommended_option_id: str | None = None


class Resolution(_M):
    kind: ResolutionKind
    option_id: str | None = None
    reason: str | None = None
    result_label: str
    badge: str = ""
    at: str | None = None


class TraceItem(_M):
    rq_item_id: str
    code: str
    short: str = ""
    text: str = ""
    places: list[Place] = Field(default_factory=list)
    places_label: str | None = None
    link_types: list[LinkType] = Field(default_factory=list)
    state: TraceState
    problem: Literal["no_place", "empty_content"] | None = None
    owner_note: str | None = None
    priority: int = 0
    question: TraceQuestion | None = None
    resolution: Resolution | None = None
    needs_confirmation: bool = False


class Extension(_M):
    id: str
    name: str
    short: str = ""
    where_label: str = ""
    places: list[Place] = Field(default_factory=list)
    derived_from_codes: list[str] = Field(default_factory=list)
    status: Literal["extension", "reviewing"] = "extension"
    acknowledged: bool = False


class Trace(_M):
    total: int = 0
    ok_count: int = 0
    items: list[TraceItem] = Field(default_factory=list)
    extensions: list[Extension] = Field(default_factory=list)
    computed_at: str | None = None
    stale: bool = False
    extensions_acknowledged: bool = False


class PutResolution(_M):
    kind: ResolutionKind
    option_id: str | None = None
    reason: str | None = None


class ResolutionResult(_M):
    item: TraceItem
    apply_job_id: str | None = None


# ── 일정 ──────────────────────────────────────────────────

class SchedulePhase(_M):
    id: str
    n: int
    name: str
    short: str
    owner: str
    d_from: int
    d_to: int
    badges: list[str] = Field(default_factory=list)
    current: bool = False


class Schedule(_M):
    phases: list[SchedulePhase] = Field(default_factory=list)
    open_question_count: int = 0
    start_d: int = 21


# ── 수정 요청 · 변경 · 버전 · 동기화 ───────────────────────────

class ChangeCause(_M):
    kind: CauseKind
    ref: str | None = None
    label: str = ""


class ChangeEntry(_M):
    id: str
    place_label: str
    aspect: str | None = None
    kind: ChangeKind
    tags: list[Literal["extension", "author_supplemented"]] = Field(default_factory=list)
    before_summary: str = ""
    after_summary: str = ""
    cause: ChangeCause
    revertible: bool = True
    at: str | None = None


class RevisionTarget(_M):
    kind: Literal["section", "space"]
    id: str
    label: str = ""


class RevisionRow(_M):
    kind: ChangeKind
    before: str | None = None
    after: str | None = None
    reason: str | None = None
    line_id: str | None = None
    section_label: str | None = None


class Revision(_M):
    id: str
    target: RevisionTarget
    scope: Literal["target", "group"] = "target"
    scope_label: str = ""
    instruction: str = ""
    chips: list[str] = Field(default_factory=list)
    status: Literal["running", "ready", "applied", "discarded", "failed"] = "running"
    base_hash: str = ""
    rows: list[RevisionRow] = Field(default_factory=list)
    changed_count: int = 0
    job_id: str | None = None
    error: dict[str, Any] | None = None


class PostRevision(_M):
    target: RevisionTarget
    scope: Literal["target", "group"] = "target"
    instruction: str = Field("", max_length=1000)
    chips: list[str] = Field(default_factory=list)


class SaveRequest(_M):
    note: str | None = Field(None, max_length=60)


class SaveResult(_M):
    version: int
    created: bool


class VersionSummary(_M):
    version: int
    note: str | None = None
    created_at: str
    created_by: str | None = None
    reason: Literal["save", "restore"] = "save"
    causes: list[str] = Field(default_factory=list)


class VersionList(_M):
    items: list[VersionSummary]
    next_cursor: str | None = None


class StoryboardVersion(_M):
    version: int
    note: str | None = None
    created_at: str
    created_by: str | None = None
    reason: Literal["save", "restore"] = "save"
    snapshot: dict[str, Any]
    causes: list[str] = Field(default_factory=list)


class RestoreResult(_M):
    version: int


class CompareFrom(_M):
    version: int
    note: str | None = None
    date: str | None = None


class CompareTo(_M):
    version: int
    version_label: str
    is_draft: bool = False
    date: str | None = None


class Compare(_M):
    from_: CompareFrom = Field(alias="from")
    to: CompareTo
    causes: list[str] = Field(default_factory=list)
    rows: list[ChangeEntry] = Field(default_factory=list)
    count: int = Field(0, description="바뀐 곳 수 = 변경 + 추가 + 삭제(유지 제외)")
    revertible: bool = Field(False, description="to 가 작업본이라 행별 되돌리기가 된다")


class RequirementSyncRequest(_M):
    requirement_id: str
    to_version: int | None = None
    reply_id: str | None = None
    dry_run: bool = False


class SyncPreview(_M):
    id: str
    requirement_id: str
    from_rq_version: int
    to_rq_version: int | None = None
    reply_id: str | None = None
    rows: list[ChangeEntry] = Field(default_factory=list)
    count: int = 0
    causes: list[str] = Field(default_factory=list)
    status: Literal["running", "ready", "failed"] = "running"
    from_version: int = Field(0, description="미리 보기의 기준 스토리보드 버전(v{a})")
    error: dict[str, Any] | None = None


# ── 저장 이후 ──────────────────────────────────────────────

class ExportOptions(_M):
    trace_appendix: bool = True
    discussions: bool = True
    internal_memo: bool = False


class ExportRequest(_M):
    format: Literal["pptx", "pdf"] = "pptx"
    options: ExportOptions = Field(default_factory=ExportOptions)


class ShareResult(_M):
    url: str


class ReviewRequestBody(_M):
    note: str | None = Field(None, max_length=500)


class ReviewRequestResult(_M):
    review_id: str | None = None
    status: str = "requested"


class HandoffCard(_M):
    target: HandoffTarget
    title: str
    description: str
    route: str
    emphasized: bool = False
    done: bool = False


class HandoffList(_M):
    items: list[HandoffCard]


class HandoffResult(_M):
    route: str


class Handoff(_M):
    target: str
    at: str


class CompetitorCriterion(_M):
    name: str
    importance: str | None = None
    source: str | None = None


class CompetitorImport(_M):
    """경쟁사 분석 CA5 `Storyboard 비교 기준으로` — 웹이 묶음(bundle?target=storyboard)을 옮겨 올린다(익명)."""
    analysis_id: str | None = None
    title: str | None = None
    criteria: list[CompetitorCriterion] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    note: str | None = None


# ── 스토리보드 ─────────────────────────────────────────────

class RqUpdate(_M):
    version: int
    note: str | None = None


class Storyboard(_M):
    id: str
    owner: Owner
    project_id: str | None = None
    name: str
    customer_name: str | None = None
    title: str
    started: bool = False
    status: SbStatus = "in_progress"
    step: int = Field(1, ge=1, le=5)
    step_label: str = ""
    route: str = ""
    sub_line: str = ""
    requirement_ref: RequirementRef | None = None
    settings: Settings = Field(default_factory=Settings)
    planning: Planning = Field(default_factory=Planning)
    direction: Direction | None = None
    outline: Outline | None = None
    trace: Trace | None = None
    schedule: Schedule = Field(default_factory=Schedule)
    version: int = Field(0, description="저장한 스토리보드 버전(0 = 아직 없음)")
    revision: int = Field(0, description="작업본 내용이 바뀔 때마다 +1")
    has_unsaved_changes: bool = True
    draft_label: str = ""
    changes: list[ChangeEntry] = Field(default_factory=list, description="최신 저장 버전 이후 변경")
    handoffs: list[Handoff] = Field(default_factory=list)
    active_job: ActiveJob | None = None
    prepare_job_id: str | None = None
    rq_update: RqUpdate | None = Field(None, description="반영 요청 없이 저장된 정의서 새 버전(SB3 띠)")
    review_requested: bool = False
    exported: bool = False
    counts: dict[str, int] = Field(default_factory=dict, description="needs_confirmation · tbd · sections · spaces_empty · unknown_answers")
    created_at: str
    updated_at: str


class PatchStoryboard(_M):
    name: str | None = Field(None, min_length=1, max_length=60)


class CreateStoryboard(_M):
    requirement_id: str | None = None
    requirement_version: int | None = None


class PutRequirement(_M):
    requirement_id: str
    version: int | None = None


class SettingsPatch(_M):
    stage: Stage | None = None
    doc_type: DocType | None = None
    volume: Literal[12, 20, 30] | None = None
    language: Language | None = None


class SettingsResult(_M):
    settings: Settings


class StoryboardListItem(_M):
    id: str
    title: str
    customer_name: str | None = None
    step: int
    step_label: str
    status: SbStatus
    status_label: str
    sub_line: str
    updated_at: str
    route: str
    cta: Literal["continue", "view", "open"]
    active_job: ActiveJob | None = None
    requirement_id: str | None = None


class StoryboardList(_M):
    items: list[StoryboardListItem]
    next_cursor: str | None = None


class StoryboardCounts(_M):
    all: int
    in_progress: int
    done: int


# ── 제안서 넘김(ProposalHandoff v1 — 10-proposal.md §8.0) ─────────

class HandoffSource(_M):
    feature: str = "storyboard"
    ref_id: str
    version: int
    title: str
    updated_at: str
    route: str


class HandoffTargetRef(_M):
    proposal_type: str
    section_key: str


class HandoffCustomer(_M):
    name: str | None = None
    industry_code: str | None = None
    scale_text: str | None = None
    decision_makers: str | None = None


class HandoffRqRef(_M):
    rq_id: str
    version: int


class HandoffItem(_M):
    key: str
    label: str
    from_label: str | None = None
    sheet_role: str
    sheet_title: str | None = None
    template_hint: dict[str, str] | None = None
    status: Literal["ok", "warn", "add"] = "ok"
    status_label: str = ""
    include_default: bool = True
    repeat_key: dict[str, str] | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)


class HandoffFact(_M):
    key: str
    label: str
    value: str | None = None
    unit: str | None = None
    status: Literal["confirmed", "unconfirmed", "placeholder"] = "placeholder"
    placeholder: str | None = None
    source: dict[str, Any] | None = None


class ProposalHandoff(_M):
    source: HandoffSource
    target: HandoffTargetRef
    customer: HandoffCustomer | None = None
    rq_ref: HandoffRqRef | None = None
    key_messages: list[dict[str, Any]] = Field(default_factory=list, description="Key Message 목록(text · place_label · audience)")
    strategy: dict[str, Any] | None = Field(None, description="제안 전략(방향 제목 · 한 줄 · 청중)")
    items: list[HandoffItem] = Field(default_factory=list)
    facts: list[HandoffFact] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
    live_link: bool = False
