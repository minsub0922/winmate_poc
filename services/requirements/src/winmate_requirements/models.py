"""requirements API 모델 — 이 파일의 Pydantic 모델이 contracts/requirements.json 의 스키마가 된다.

문서: docs/scenarios/01-requirements.md §5(데이터 모델) · §6(API).
저장 문서(dict)는 이 모델보다 키가 더 많을 수 있다(rev · short_for 같은 내부 키). 응답은 이 모델로 거른다.
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic import Field as PField

# ── 공통 ─────────────────────────────────────────────────

FieldName = Literal["project_name", "customer_name", "final_audience", "author_note"]
FileLabel = Literal["PPTX", "PDF", "DOCX", "TXT", "메일"]
SourceKind = Literal["user", "file", "deep", "reply", "storyboard"]
ListState = Literal["input", "filling", "deepening", "editing", "saved"]
SessionStatus = Literal["analyzing", "ready", "asking", "finished", "canceled", "failed"]
DocKind = Literal["rfp", "meeting_memo", "mail", "other"]
ConsumerService = Literal["storyboard", "mi", "competitor", "vp", "spec", "proposal"]

FIELD_MAX = {"project_name": 120, "customer_name": 80, "final_audience": 80, "author_note": 2000}
FIELD_LABELS = {"project_name": "프로젝트명", "customer_name": "고객사", "final_audience": "최종 제안대상",
                "author_note": "제작자 의견"}


class Model(BaseModel):
    # 응답 스키마에서는 기본값이 있는 필드도 항상 오므로 required 로 싣는다(소비자 · 웹 타입이 정확해진다).
    model_config = ConfigDict(extra="ignore", json_schema_serialization_defaults_required=True)


class UserRef(Model):
    id: str
    name: str = ""


class ErrorInfo(Model):
    code: str
    message: str


class Source(Model):
    """값이 어디서 왔나(§5.1 Source)."""
    kind: SourceKind
    file_id: str | None = None
    file_label: str | None = PField(None, description="배지 글자: PPTX · PDF · DOCX · TXT · 메일")
    file_name: str | None = None
    locator: str | None = PField(None, description='"슬라이드 3" · "p.5" · "줄 12"')
    quote: str | None = PField(None, description="원문 근거 문장(≤ 200자)")
    session_id: str | None = None
    reply_id: str | None = None
    job_id: str | None = PField(None, description="채운 잡(이번 잡에서 막 채운 칸 강조)")
    service: str | None = None


class Alternative(Model):
    value: str
    source: Source | None = None


class FormField(Model):
    """§5.1 Field — 폼 칸 하나."""
    value: str | None = None
    source: Source | None = None
    derived_from: Source | None = None
    alternatives: list[Alternative] = PField(default_factory=list)
    updated_at: str | None = None
    rev: int = PField(0, description="이 칸을 마지막으로 쓴 작업본 revision")


class Evidence(Model):
    file_id: str
    name: str
    type_label: str | None = None


class Entity(Model):
    type: str = PField(description="space_type · category · solution · capability · model · vertical …(kb A1)")
    id: str
    name: str
    surface: str | None = None


class ReqItem(Model):
    """§5.3 요구사항 항목."""
    id: str = PField(description="ri_<ULID> — 버전을 넘어 유지")
    code: str = PField(description='"RQ-01" — 재사용하지 않음')
    text: str
    short: str | None = PField(None, description="≤ 24자 짧은 이름(LLM)")
    source: Source | None = None
    needs_confirmation: bool = False
    evidence: list[Evidence] = PField(default_factory=list)
    entities: list[Entity] = PField(default_factory=list)
    order: int = 0
    rev: int = 0
    updated_at: str | None = None


class Keyman(Model):
    """§5.2 키맨."""
    id: str = PField(description="km_<ULID>")
    name: str = ""
    weight: int | None = PField(None, description="키맨 ≥ 2: 합 100 · 각 ≥ 5 / 1명: 100 / 0명: 없음")
    color_index: int = 0
    order: int = 0
    source: Source | None = None
    items: list[ReqItem] = PField(default_factory=list)
    rev: int = 0


class Form(Model):
    project_name: FormField = PField(default_factory=FormField)
    customer_name: FormField = PField(default_factory=FormField)
    final_audience: FormField = PField(default_factory=FormField)
    author_note: FormField = PField(default_factory=FormField, description="제작자 의견 — 내부용, 고객 문서 제외")
    keymen: list[Keyman] = PField(default_factory=list)
    weights_mode: Literal["equal_default", "custom"] = "equal_default"


class SourceFile(Model):
    """§5.4 정의서에 넣은 파일."""
    file_id: str
    name: str
    type_label: str
    status: Literal["uploading", "reading", "done", "failed"] = "reading"
    filled_count: int = 0
    doc_kind: DocKind | None = None
    error: ErrorInfo | None = None
    job_id: str | None = None
    added_at: str | None = None


class VerticalCandidate(Model):
    id: str
    name: str
    score: float = 0


class Vertical(Model):
    top2: list[VerticalCandidate] = PField(default_factory=list)
    ask: bool = False


class ContextSpace(Model):
    id: str
    name: str
    item_ids: list[str] = PField(default_factory=list)


class ContextProduct(Model):
    type: str = PField(description="category · model · family …")
    id: str
    name: str
    item_ids: list[str] = PField(default_factory=list)


class ContextSolution(Model):
    id: str
    name: str
    item_ids: list[str] = PField(default_factory=list)


class RqContext(Model):
    """화면에 보이지 않는 파생 정보 — 소비자용(§8.3)."""
    vertical: Vertical | None = None
    spaces: list[ContextSpace] = PField(default_factory=list)
    products: list[ContextProduct] = PField(default_factory=list)
    solutions: list[ContextSolution] = PField(default_factory=list)
    scale_text: str | None = None
    deadline_text: str | None = None
    language: str | None = None


class ActiveJob(Model):
    job_id: str
    kind: str


class FillProgress(Model):
    job_id: str | None = None
    filled: int = 0
    total: int = 0


class ActiveDeep(Model):
    session_id: str
    status: SessionStatus
    current_index: int = 1
    total: int = 0


class SkippedOp(Model):
    index: int
    op: str
    reason: str


class Requirement(Model):
    """§5.1 요구사항 정의서(작업본 + 메타)."""
    id: str = PField(description="rq_<ULID>")
    owner: UserRef
    project_id: str | None = None
    title: str | None = PField(None, description="short_title ?? `${고객사} ${프로젝트명}` ?? null")
    short_title: str | None = None
    version: int = PField(0, description="최신 저장 버전, 0 = 없음")
    revision: int = PField(description="작업본 쓰기마다 +1")
    has_unsaved_changes: bool = False
    list_state: ListState
    state_label: str
    form: Form
    files: list[SourceFile] = PField(default_factory=list)
    context: RqContext = PField(default_factory=RqContext)
    open_question_count: int = 0
    item_count: int = 0
    keyman_count: int = 0
    active_job: ActiveJob | None = None
    queued_jobs: list[ActiveJob] = PField(default_factory=list)
    fill_progress: FillProgress | None = None
    active_deep_session_id: str | None = None
    active_deep: ActiveDeep | None = None
    last_deep_session_id: str | None = None
    route: str
    created_at: str
    updated_at: str
    saved_at: str | None = None
    skipped_ops: list[SkippedOp] | None = PField(None, description="PATCH draft 에서 대상이 사라져 무시한 op")


class RequirementListItem(Model):
    id: str
    title: str | None = None
    customer_name: str | None = None
    project_name: str | None = None
    project_id: str | None = None
    list_state: ListState
    state_label: str
    version: int = 0
    has_unsaved_changes: bool = False
    keyman_count: int = 0
    item_count: int = 0
    open_question_count: int = 0
    updated_at: str
    saved_at: str | None = None
    route: str
    active_deep: ActiveDeep | None = None
    owner: UserRef


class RequirementList(Model):
    items: list[RequirementListItem]
    next_cursor: str | None = None


class Counts(Model):
    all: int
    in_progress: int
    saved: int


class FormInit(Model):
    project_name: str | None = PField(None, max_length=120)
    customer_name: str | None = PField(None, max_length=80)
    final_audience: str | None = PField(None, max_length=80)
    author_note: str | None = PField(None, max_length=2000)


class CreateRequirement(Model):
    project_id: str | None = None
    form: FormInit | None = None


# ── 작업본 ops(§6.3) ─────────────────────────────────────

class SetFieldOp(Model):
    op: Literal["set_field"]
    field: FieldName
    value: str | None = PField(None, max_length=2000)


class AddKeymanOp(Model):
    op: Literal["add_keyman"]
    keyman_id: str | None = PField(None, description="클라이언트가 만든 km_<ULID> 허용")
    name: str = PField("", max_length=40)
    after_keyman_id: str | None = None


class UpdateKeymanOp(Model):
    op: Literal["update_keyman"]
    keyman_id: str
    name: str = PField(max_length=40)


class RemoveKeymanOp(Model):
    op: Literal["remove_keyman"]
    keyman_id: str


class SetWeightsOp(Model):
    op: Literal["set_weights"]
    weights: dict[str, int] = PField(description="{km_id: 정수} — 합 100, 각 ≥ 5")


class ResetWeightsEqualOp(Model):
    op: Literal["reset_weights_equal"]


class AddItemOp(Model):
    op: Literal["add_item"]
    keyman_id: str
    item_id: str | None = PField(None, description="클라이언트가 만든 ri_<ULID> 허용")
    text: str = PField("", max_length=200)
    after_item_id: str | None = None


class UpdateItemOp(Model):
    op: Literal["update_item"]
    item_id: str
    text: str = PField(max_length=200)


class RemoveItemOp(Model):
    op: Literal["remove_item"]
    item_id: str


class MoveItemOp(Model):
    op: Literal["move_item"]
    item_id: str
    keyman_id: str
    index: int = PField(ge=0)


DraftOp = Annotated[
    SetFieldOp | AddKeymanOp | UpdateKeymanOp | RemoveKeymanOp | SetWeightsOp | ResetWeightsEqualOp | AddItemOp
    | UpdateItemOp | RemoveItemOp | MoveItemOp,
    PField(discriminator="op"),
]


class PatchDraft(Model):
    base_revision: int | None = PField(None, description="클라이언트가 마지막으로 본 revision(없으면 충돌 검사 안 함)")
    ops: list[DraftOp] = PField(default_factory=list, max_length=200)


class SaveRequest(Model):
    reason: Literal["direct", "deep", "edit"] | None = None
    note: str | None = PField(None, max_length=200)


class SaveResult(Model):
    version: int
    created: bool
    requirement: Requirement | None = None


class ShareResult(Model):
    url: str
    token: str | None = None


# ── 파일로 채우기(§6.2) ───────────────────────────────────

class AddFiles(Model):
    file_ids: list[str] = PField(min_length=1, max_length=10)


class FromFiles(Model):
    """제안서(PR1F) 등이 파일로 바로 정의서를 만들 때 — 새 정의서 + rq.fill 잡."""
    file_ids: list[str] = PField(min_length=1, max_length=10)
    customer_hint: str | None = PField(None, max_length=80)
    project_id: str | None = None


class JobRef(Model):
    kind: str
    id: str


class JobAccepted(Model):
    job_id: str
    status: str = "queued"
    ref: JobRef


# ── 버전(§5.9 · §6.5) ─────────────────────────────────────

class InternalText(Model):
    value: str | None = None
    internal: bool = True


class SnapshotForm(Model):
    project_name: FormField = PField(default_factory=FormField)
    customer_name: FormField = PField(default_factory=FormField)
    final_audience: FormField = PField(default_factory=FormField)
    author_note: FormField = PField(default_factory=FormField,
                                    description="내부용(internal) — 소비자는 고객용 산출물에 넣지 않는다")
    author_note_internal: bool = True
    keymen: list[Keyman] = PField(default_factory=list)
    weights_mode: Literal["equal_default", "custom"] = "equal_default"


class FlatItem(Model):
    id: str
    code: str
    text: str
    short: str | None = None
    keyman_id: str | None = None
    keyman_name: str | None = None
    keyman_weight: int | None = None
    needs_confirmation: bool = False
    evidence: list[Evidence] = PField(default_factory=list)
    entities: list[Entity] = PField(default_factory=list)
    source: Source | None = PField(None, description="항목이 어디서 왔나(파일이면 file_id · locator(쪽) · quote)")


class SnapshotKeyman(Model):
    id: str
    name: str
    weight: int | None = None
    color_index: int = 0
    order: int = 0
    item_ids: list[str] = PField(default_factory=list)


class QuestionTarget(Model):
    kind: Literal["item", "field", "keyman"]
    id: str


class SnapshotQuestion(Model):
    id: str
    text: str
    short_label: str | None = None
    status: Literal["open", "answered", "dismissed"]
    keyman_id: str | None = None
    target: QuestionTarget | None = None


class SnapshotFile(Model):
    file_id: str
    name: str
    type_label: str | None = None


class Snapshot(Model):
    form: SnapshotForm
    context: RqContext = PField(default_factory=RqContext)
    keymen: list[SnapshotKeyman] = PField(default_factory=list)
    items_flat: list[FlatItem] = PField(default_factory=list)
    customer_questions: list[SnapshotQuestion] = PField(default_factory=list)
    source_files: list[SnapshotFile] = PField(default_factory=list)
    author_note: InternalText = PField(default_factory=InternalText, description="제작자 의견(internal: true)")


class RequirementVersion(Model):
    """불변 저장 스냅숏. 소비자(Storyboard · MI · 경쟁사 · VP · Spec · 제안서)가 읽는 기준."""
    requirement_id: str
    version: int
    created_at: str
    created_by: UserRef | None = None
    reason: Literal["direct", "deep", "edit", "reply", "restore"]
    note: str | None = None
    summary: str
    change_count: int = 0
    title: str | None = None
    project_id: str | None = None
    project_name: str | None = None
    customer_name: str | None = None
    final_audience: str | None = None
    item_count: int = 0
    keyman_count: int = 0
    open_question_count: int = 0
    latest_version: int = PField(0, description="지금 이 정의서의 최신 저장 버전")
    snapshot: Snapshot


class VersionSummary(Model):
    version: int
    created_at: str
    created_by: UserRef | None = None
    reason: str
    note: str | None = None
    summary: str
    change_count: int = 0


class VersionList(Model):
    items: list[VersionSummary]
    next_cursor: str | None = None


class RestoreResult(Model):
    version: int


class DiffTarget(Model):
    kind: Literal["item", "field", "keyman", "weights"]
    id: str


class DiffChange(Model):
    target: DiffTarget
    kind: Literal["added", "removed", "changed"]
    label: str | None = None
    before: Any = None
    after: Any = None
    keyman_id: str | None = None


class Diff(Model):
    from_version: int
    to_version: int
    changes: list[DiffChange]


# ── 심층 작성(§5.5 · §6.4) ────────────────────────────────

class GapTarget(Model):
    kind: Literal["field", "weights", "keyman", "item", "keymen"]
    field: FieldName | None = None
    keyman_id: str | None = None
    item_id: str | None = None


class GapOption(Model):
    id: str
    label: str
    value: str | None = None
    weights: dict[str, int] | None = None


class GapQuestion(Model):
    text: str
    options: list[GapOption] = PField(default_factory=list)
    allow_text: bool = True
    answer_type: Literal["value", "weights", "sentence"]


class GapAnswer(Model):
    kind: Literal["option", "text", "weights", "unknown", "skip"]
    option_id: str | None = None
    text: str | None = None
    weights: dict[str, int] | None = None


class GapChange(Model):
    label: str
    before_display: str | None = None
    after_display: str
    after_short: str | None = None
    is_addition: bool = False
    keyman_id: str | None = None


class Gap(Model):
    id: str = PField(description="gp_<ULID>")
    target: GapTarget
    kind: Literal["empty_field", "default_weights", "too_few_items", "no_keyman", "unquantified", "vague_scope",
                  "ambiguous", "missing_perspective", "conflict", "capability_unclear"]
    origin: Literal["rule", "llm", "kb_b2"]
    chip_label: str
    chip_keyman_id: str | None = PField(None, description="키맨 칩이면 색 점(키맨 색)")
    problem: str = PField(description="≤ 24자 문제 한 줄")
    priority: int
    impact: int = 1
    question: GapQuestion
    status: Literal["pending", "proposed", "applied", "deferred", "skipped", "resolved_by_form", "deselected"]
    answer: GapAnswer | None = None
    change: GapChange | None = None
    customer_question_ids: list[str] = PField(default_factory=list)
    needs_confirmation: bool = PField(False, description="KB 시드 초안 근거(B2)")


class LogEntry(Model):
    gap_id: str
    kind: Literal["applied", "deferred", "skipped", "resolved"]
    label: str
    value_display: str


class SideEffect(Model):
    id: str
    kind: Literal["add_customer_question"] = "add_customer_question"
    label: str
    question_text: str
    keyman_id: str | None = None
    checked: bool = True


class Proposal(Model):
    id: str = PField(description="pp_<ULID>")
    gap_id: str
    kind: Literal["replace_item", "add_item", "set_field"]
    target: GapTarget
    before_text: str | None = None
    after_text: str
    after_short: str | None = None
    side_effects: list[SideEffect] = PField(default_factory=list)
    revisions: int = 0
    answer_text: str | None = None
    keyman_id: str | None = None


class ResultQuestion(Model):
    id: str
    text: str
    short_label: str | None = None


class SessionResult(Model):
    reinforced_count: int
    changes: list[GapChange] = PField(default_factory=list)
    customer_question_ids: list[str] = PField(default_factory=list)
    customer_questions: list[ResultQuestion] = PField(default_factory=list)


class DeepSession(Model):
    id: str = PField(description="ds_<ULID>")
    requirement_id: str
    status: SessionStatus
    job_id: str | None = None
    base_revision: int = 0
    stale: bool = False
    completeness_before: int | None = None
    completeness: int | None = None
    completeness_after: int | None = None
    gaps: list[Gap] = PField(default_factory=list)
    selected_gap_ids: list[str] = PField(default_factory=list)
    current_gap_id: str | None = None
    current_index: int = 0
    total: int = 0
    log: list[LogEntry] = PField(default_factory=list)
    pending_proposal: Proposal | None = None
    result: SessionResult | None = None
    error: ErrorInfo | None = None
    created_at: str
    updated_at: str


class SelectGaps(Model):
    selected_gap_ids: list[str]


class AnswerRequest(Model):
    gap_id: str
    kind: Literal["option", "text", "weights", "unknown", "skip"]
    option_id: str | None = None
    text: str | None = PField(None, max_length=1000)
    weights: dict[str, int] | None = None


class CustomerQuestionOrigin(Model):
    kind: Literal["deep_unknown", "deep_side_effect", "storyboard", "manual", "proposal", "reply"]
    session_id: str | None = None
    service: str | None = None
    ref_id: str | None = None
    place_label: str | None = None
    confirm_item_id: str | None = None


class QuestionAnswer(Model):
    text: str | None = None
    reply_id: str | None = None
    answered_at: str


class CustomerQuestion(Model):
    """§5.6 고객에게 물을 것."""
    id: str = PField(description="cq_<ULID>")
    requirement_id: str
    text: str
    short_label: str | None = None
    keyman_id: str | None = None
    target: QuestionTarget | None = None
    origin: CustomerQuestionOrigin
    status: Literal["open", "answered", "dismissed"] = "open"
    include_in_mail: bool = True
    answer: QuestionAnswer | None = None
    created_at: str
    updated_at: str | None = None


class AnswerResult(Model):
    outcome: Literal["applied", "proposal", "deferred", "skipped"]
    log_entry: LogEntry | None = None
    proposal: Proposal | None = None
    customer_question: CustomerQuestion | None = None
    session: DeepSession
    requirement_revision: int


class SideEffectChoice(Model):
    id: str
    checked: bool


class AcceptProposal(Model):
    edited_text: str | None = PField(None, max_length=200)
    side_effects: list[SideEffectChoice] | None = None


class AcceptResult(Model):
    log_entry: LogEntry
    created_question_ids: list[str] = PField(default_factory=list)
    session: DeepSession
    requirement_revision: int


class ReviseProposal(Model):
    instruction: str = PField(min_length=1, max_length=500)


class ReviseResult(Model):
    proposal: Proposal
    session: DeepSession


# ── 고객 질문 · 메일(§6.6) ───────────────────────────────

class CustomerQuestionOriginIn(Model):
    kind: Literal["storyboard", "manual", "proposal"] | None = PField(
        None, description="없으면 service/feature 로 정함(SB → storyboard, PR → proposal, 그 밖 → manual)")
    service: str | None = None
    feature: str | None = PField(None, description="기능 코드(SB · PR …) — service 대신 써도 된다")
    ref_id: str | None = None
    place_label: str | None = PField(None, max_length=60)
    confirm_item_id: str | None = None


class CreateCustomerQuestion(Model):
    text: str = PField(min_length=1, max_length=120)
    short_label: str | None = PField(None, max_length=24)
    keyman_id: str | None = None
    target: QuestionTarget | None = None
    origin: CustomerQuestionOriginIn = PField(default_factory=CustomerQuestionOriginIn)


class PatchCustomerQuestion(Model):
    include_in_mail: bool | None = None
    status: Literal["dismissed", "open"] | None = None


class CustomerQuestionList(Model):
    items: list[CustomerQuestion]
    next_cursor: str | None = None


class MailDraftRequest(Model):
    question_ids: list[str] = PField(min_length=1)


class MailDraft(Model):
    subject: str
    body: str
    generated_by: Literal["llm", "template"]


# ── 고객 답변(§5.7 · §6.7) ────────────────────────────────

class ReplyTarget(Model):
    kind: Literal["item", "field", "keyman", "weights", "evidence", "new_item"]
    id: str | None = None


class ReplyChange(Model):
    id: str = PField(description="ch_<ULID>")
    target: ReplyTarget
    label: str
    before_display: str | None = None
    after_display: str
    ops: list[dict[str, Any]] = PField(default_factory=list)
    resolves_question_ids: list[str] = PField(default_factory=list)
    evidence_file_ids: list[str] = PField(default_factory=list)
    selected: bool = True


class ImpactPlace(Model):
    code: str | None = None
    label: str


class ImpactLink(Model):
    ref_id: str
    title: str | None = None
    route: str | None = None
    places: list[ImpactPlace] = PField(default_factory=list)


class StoryboardImpact(Model):
    count: int = 0
    links: list[ImpactLink] = PField(default_factory=list)


class ReplyFile(Model):
    file_id: str
    name: str
    type_label: str | None = None


class ReplyAnalysis(Model):
    id: str = PField(description="rp_<ULID>")
    requirement_id: str
    base_version: int
    status: Literal["analyzing", "ready", "applied", "failed"]
    text: str = ""
    file_ids: list[str] = PField(default_factory=list)
    files: list[ReplyFile] = PField(default_factory=list)
    changes: list[ReplyChange] = PField(default_factory=list)
    matches: list[dict[str, Any]] = PField(default_factory=list)
    version_note: str | None = None
    storyboard_impact: StoryboardImpact = PField(default_factory=StoryboardImpact)
    applied_version: int | None = None
    job_id: str | None = None
    error: ErrorInfo | None = None
    created_at: str
    updated_at: str


class CreateReply(Model):
    text: str = PField("", max_length=20000)
    file_ids: list[str] = PField(default_factory=list, max_length=10)


class PatchReply(Model):
    selected_change_ids: list[str]


class ApplyReply(Model):
    selected_change_ids: list[str]
    propagate: list[Literal["storyboard"]] = PField(default_factory=list)
    note: str | None = PField(None, max_length=200)


class SyncLinkRef(Model):
    service: str
    ref_id: str


class ApplyResult(Model):
    version: int
    pending_sync_links: list[SyncLinkRef] = PField(default_factory=list)


# ── 쓰는 곳(§5.8 · §6.8) ─────────────────────────────────

class LinkTarget(Model):
    kind: Literal["item", "field", "keyman", "weights"]
    id: str = PField(description="항목 ri_ · 키맨 km_ · 칸 이름 · weights")


class LinkPlace(Model):
    code: str | None = None
    label: str


class LinkDependency(Model):
    target: LinkTarget
    places: list[LinkPlace] = PField(default_factory=list)


class UsageLink(Model):
    requirement_id: str
    service: ConsumerService
    ref_id: str
    title: str | None = None
    route: str | None = None
    rq_version: int
    depends_on: list[LinkDependency] = PField(default_factory=list)
    sync_state: Literal["up_to_date", "pending"] = "up_to_date"
    pending_version: int | None = None
    created_at: str
    updated_at: str


class UpsertLink(Model):
    title: str | None = PField(None, max_length=200)
    route: str | None = PField(None, max_length=300)
    rq_version: int = PField(ge=0)
    depends_on: list[LinkDependency] = PField(default_factory=list)


class LinkList(Model):
    items: list[UsageLink]


# ── 내보내기(§6.9, 제안) ─────────────────────────────────

class ExportRequest(Model):
    format: Literal["docx", "pdf"] = "docx"
    version: int | None = None


class ExportRecord(Model):
    id: str
    requirement_id: str
    format: str
    version: int
    status: Literal["queued", "running", "done", "failed"]
    file_id: str | None = None
    file_name: str | None = None
    job_id: str | None = None
    error: ErrorInfo | None = None
    created_at: str
    updated_at: str


class ServiceInfo(Model):
    service: str
    title: str
    version: str
