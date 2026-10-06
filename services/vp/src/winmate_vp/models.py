"""API 모델(05-vp.md §5 · §6) — 이 모델이 contracts/vp.json 이 된다."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Mode = Literal["auto", "check", "ask", "pin"]
VPStatus = Literal["draft", "collecting", "ask", "planned", "generating", "check", "done", "stopped", "failed"]
UiStatus = Literal["draft", "ask", "check", "run", "done"]
Axis = Literal["challenge", "value", "evidence", "stakeholder", "product"]
Role = Literal["CH", "VP", "EF"]
SheetRole = Literal["CH", "VP", "EF", "REF"]
ProposalType = Literal["standard", "quickwin", "solution"]
Start = Literal["direct", "storyboard", "mi", "clone", "proposal"]
SourceKind = Literal["storyboard", "mi", "requirements", "case", "vp"]
AttachmentKind = Literal["rfp", "quote", "meeting_notes", "customer_photo", "other"]


class M(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── 공통 조각 ──────────────────────────────────────────────

class Thumb(M):
    kind: str
    n: int = 3


class JobAccepted(M):
    job_id: str
    status: str = "queued"
    ref: dict[str, Any] | None = Field(None, description="만들어진 · 바뀌는 자원(편의)")


class LayoutPick(M):
    code: str = Field(description="정본 코드(VP-F3)")
    display: str = Field(description="화면 코드(VP-F·3)")
    name: str
    family: str
    thumb: Thumb
    industry_code: str | None = None
    pinned: bool = False
    chosen_by: Literal["agent", "user"] = "agent"
    fit: int | None = None
    why: str = ""


class IndustryPack(M):
    status: Literal["in_production", "ready"] = "in_production"
    label: str = "업종판 제작 중 → 범용"


class IndustryScore(M):
    code: str
    score: float


class Industry(M):
    code: str = Field(description="16 업종 코드 · GEN(범용)")
    name: str = Field(description="`외식 · 카페`")
    cell: str = ""
    source: Literal["mi", "storyboard", "proposal", "requirements", "classified", "user", "vp"] = "classified"
    mode: Mode = "auto"
    confidence: float | None = None
    top2: list[IndustryScore] | None = None
    kr_vertical_id: str | None = None
    pack: IndustryPack = Field(default_factory=IndustryPack)
    inherited_from: str | None = None
    caption: str = ""


class TargetProposal(M):
    proposal_id: str | None = None
    title: str = ""
    type: ProposalType = "standard"
    section_label: str = "Value Props"


class SourceGives(M):
    summary: str = ""
    counts: dict[str, int] = Field(default_factory=dict)
    axes: list[str] = Field(default_factory=list)


class Source(M):
    id: str
    kind: SourceKind
    ref_id: str
    title: str
    kind_label: str = ""
    connected: bool = True
    status: Literal["connected", "recommended"] = "connected"
    gives: SourceGives = Field(default_factory=SourceGives)
    fetched_version: int | None = None
    fetched_at: str | None = None


class SourceCandidate(Source):
    recommended: bool = False


class SourceCandidates(M):
    found_label: str
    items: list[SourceCandidate]


class Attachment(M):
    id: str
    file_id: str
    filename: str = ""
    kind: AttachmentKind = "other"
    detected_kind: str | None = None
    confidential: bool = True
    status: Literal["pending", "read", "failed"] = "pending"
    summary: str = ""


class CoverageAxis(M):
    axis: Literal["challenge", "value", "evidence", "stakeholder"]
    label: str
    percent: int
    summary: str
    level: Literal["충분", "보통", "부족"]
    todo: str


class SourceTag(M):
    tag: Literal["SB", "MI", "RFP", "CS", "RQ", "QT", "USER", "KB", "VP"]
    ref_id: str = ""
    locator: str | None = None
    as_of: str | None = None


class NumberSource(M):
    kind: Literal["customer", "rfp", "requirements", "interview", "case", "industry_avg", "mi", "web", "user", "quote", "kb", "storyboard"] = "customer"
    label: str = ""
    refs: list[str] = Field(default_factory=list)
    as_of: str | None = None
    tier: str | None = None


class NumberValue(M):
    display: str = Field(description="'12초' | '3~5초' | '[00]시간'")
    value: float | None = None
    value2: float | None = None
    unit: str | None = None
    status: Literal["secured", "estimated", "missing", "requested", "excluded"] = "missing"
    source: NumberSource | None = None
    estimate_basis: str | None = None


class KBRef(M):
    kind: Literal["family", "model", "solution", "category", "deployment"]
    id: str
    name: str


class MaterialMetric(M):
    label: str
    before: NumberValue
    after: NumberValue


class MaterialItem(M):
    id: str
    axis: Axis
    text: str
    sources: list[SourceTag] = Field(default_factory=list)
    state: Literal["new", "merged", "rewritten", "refetched", "inferred"] = "new"
    number: NumberValue | None = None
    metric: MaterialMetric | None = None
    product_refs: list[KBRef] = Field(default_factory=list)
    cost: bool = False
    approver: bool = False
    group: str | None = None
    excluded: bool = False
    flags: list[str] = Field(default_factory=list)


class Fix(M):
    id: str
    kind: Literal["merge", "rewrite", "refetch"]
    kind_label: str
    from_text: str
    to_text: str
    mode: Literal["auto", "check"]
    decision: Literal["pending", "accepted", "reverted"] = "pending"
    decided_by: Literal["user", "default"] | None = None
    item_ids: list[str] = Field(default_factory=list)


class QuestionPreview(M):
    code: str
    display: str
    thumb: Thumb
    effect: str


class QuestionOption(M):
    key: str
    label: str
    desc: str | None = None
    recommended: bool = False
    preview: QuestionPreview | None = None


class QuestionAnswer(M):
    keys: list[str] = Field(default_factory=list)
    text: str | None = None
    by: Literal["user", "default"] = "user"


class Question(M):
    id: str
    no: int
    kind: Literal["direction", "approver", "industry", "sb_mi_conflict", "investment", "interview_numbers"]
    mode: Literal["ask", "check"]
    title: str
    aside: str = ""
    context_text: str | None = None
    multi: bool = False
    options: list[QuestionOption] = Field(default_factory=list)
    default_keys: list[str] = Field(default_factory=list)
    hint: str | None = None
    selected_keys: list[str] = Field(default_factory=list, description="화면이 보여 줄 현재 선택(직접 답하기 해석 결과 포함)")
    answer: QuestionAnswer | None = None
    status: Literal["open", "answered", "defaulted"] = "open"


class Decision(M):
    id: str
    t: str = Field(description="HH:MM:SS")
    stage: int
    key: str = ""
    value: str = ""
    why: str = ""
    mode: Mode = "auto"
    text: str
    job_id: str | None = None


class PlanSheet(M):
    role: Role
    step_label: str
    layout: LayoutPick
    content_preview: str = ""
    mode: Mode = "auto"
    chip: str = ""


class PlanAlternative(M):
    code: str
    display: str
    label: str
    tip: str
    role: Role = "VP"
    prerequisite: Literal["quote", "stakeholders"] | None = None


class PlanOmitted(M):
    role: Role
    label: str
    why: str = ""


class PlanDecisionRow(M):
    key: str
    value: str
    why: str
    mode: Mode = "auto"


class LayoutChip(M):
    t: str
    kind: Literal["code", "pinned", "text", "pack"]


class Plan(M):
    flow: str
    flow_label: str
    reason: str
    sheets: list[PlanSheet]
    omitted: list[PlanOmitted] = Field(default_factory=list)
    alternatives: list[PlanAlternative] = Field(default_factory=list)
    cta_label: str
    decisions: list[PlanDecisionRow] = Field(default_factory=list, description="VP2 `그 밖에 정한 것` 7행(고정 순서)")
    chips: list[LayoutChip] = Field(default_factory=list)
    intro: str = ""
    overrides: dict[str, str] = Field(default_factory=dict)


# ── 시트 ──────────────────────────────────────────────────

class ChallengeItem(M):
    id: str
    title: str
    body: str = ""
    impact: NumberValue | None = None
    source_ids: list[str] = Field(default_factory=list)


class PillarItem(M):
    id: str
    title: str
    body: str = ""
    proof_ids: list[str] = Field(default_factory=list)
    product_refs: list[KBRef] = Field(default_factory=list)
    km_ref: str | None = None
    image_slot_id: str | None = None


class OneLinerContent(M):
    statement: str
    evidence: list[str] = Field(default_factory=list)
    image_slot_id: str | None = None


class StakeholderItem(M):
    id: str
    role: str
    kpi: str = ""
    value: str = ""
    product_refs: list[KBRef] = Field(default_factory=list)
    image_slot_id: str | None = None


class PairItem(M):
    challenge: str
    product: KBRef | None = None
    value: str = ""
    image_slot_id: str | None = None


class Metric(M):
    id: str
    label: str
    before: NumberValue
    after: NumberValue
    source_label: str = ""
    status: Literal["secured", "estimated", "ask", "requested", "excluded"] = "ask"
    status_label: str = ""
    handling: Literal["request", "industry_avg", "exclude", "direct"] | None = None
    how: str = ""
    options: list[str] = Field(default_factory=list)
    industry_avg_available: bool = False


class Roi(M):
    investment: NumberValue
    savings: list[NumberValue] = Field(default_factory=list)
    payback_months: list[float] = Field(default_factory=list)
    scenario_labels: list[str] = Field(default_factory=list)
    quote_file_id: str | None = None


class ReferenceContent(M):
    deployment_id: str
    title: str
    url: str = ""
    summary: str = ""


class SheetContent(M):
    challenges: list[ChallengeItem] | None = None
    pillars: list[PillarItem] | None = None
    one_liner: OneLinerContent | None = None
    stakeholders: list[StakeholderItem] | None = None
    pairs: list[PairItem] | None = None
    metrics: list[Metric] | None = None
    qualitative: list[str] | None = None
    roi: Roi | None = None
    reference: ReferenceContent | None = None


class Sheet(M):
    id: str
    role: SheetRole
    order: int
    kind: Literal["main", "one_liner", "reference", "summary"] = "main"
    variant_of: str | None = None
    step_label: str
    layout: LayoutPick
    title: str = ""
    points: str = ""
    meta_label: str = ""
    mode: Mode = "auto"
    status: Literal["waiting", "writing", "done"] = "waiting"
    pinned: bool = False
    speaker_notes: str = ""
    include_default: bool = True
    content: SheetContent = Field(default_factory=SheetContent)


# ── 이미지 칸 ─────────────────────────────────────────────

class AssetRef(M):
    source: Literal["kb", "file", "generated"]
    asset_id: str | None = None
    file_id: str | None = None
    std_url: str = ""
    thumb_url: str = ""


class ImageDims(M):
    w: int = 0
    h: int = 0
    format: str = ""
    bytes: int | None = None


class PageRef(M):
    title: str = ""
    url: str = ""


class UsageHistory(M):
    count: int = 0
    label: str = "Winmate 제안서 0건"


class ImageMeta(M):
    title: str = ""
    kind: Literal["제품", "도입사례", "솔루션", "고객 사진", "생성"] = "제품"
    source_page: PageRef | None = None
    original_file_url: str | None = None
    original: ImageDims | None = None
    stored: ImageDims = Field(default_factory=ImageDims)
    posted_at: str | None = None
    collected_at: str = ""
    method: str = ""
    rights: str = ""
    caption_rule: str = ""
    usage_history: UsageHistory = Field(default_factory=UsageHistory)
    alt_on_source: str | None = None
    grade_hint: str | None = None
    tier_source: Literal["T2_official", "T3_case", "T6_generated", "customer"] = "T2_official"


class SlotSubject(M):
    kind: Literal["product", "solution", "space", "case", "customer"]
    refs: list[KBRef] = Field(default_factory=list)
    space_type_id: str | None = None
    label: str = ""


class SlotFlags(M):
    not_real_data: bool | None = None
    other_brand_visible: bool | None = None
    case_caption_required: bool | None = None
    similar_model: bool | None = None
    customer_unconfirmed: bool | None = None
    generated: bool | None = None
    fallback_level: str | None = None


class ImageSlot(M):
    id: str
    sheet_id: str
    code: str = Field(description="'VP-F·3 · 기둥 1'")
    label: str
    subject: SlotSubject
    tier: Literal["customer", "cut", "case", "ui", "illust"]
    tier_label: str
    asset: AssetRef | None = None
    fit: Literal["cover", "contain"] = "cover"
    focal: str | None = None
    why: str = ""
    mode: Literal["auto", "check"] = "auto"
    flags: SlotFlags = Field(default_factory=SlotFlags)
    meta: ImageMeta | None = None
    request_draft: str | None = None
    extra: bool = Field(False, description="추가 제안 칸(VP-Q · 보낼 때 기본 미포함)")


class CheckItem(M):
    id: str
    tag: Literal["추정", "이미지", "알림", "요청", "업종판"]
    text: str
    action_label: str
    action_route: str
    strong: bool = False
    resolved: bool = False


class LayoutOptionEffect(M):
    add_sheet: str | None = None
    replace_layout: str | None = None
    move_to_notes: str | None = None
    keep: bool | None = None


class LayoutOption(M):
    key: Literal["A", "B", "C"]
    title: str
    desc: str
    fit: int
    recommended: bool = False
    effect: LayoutOptionEffect = Field(default_factory=LayoutOptionEffect)


class LayoutChoice(M):
    key: str | None = None
    layout_code: str | None = None
    pinned: bool = False


class LayoutRequest(M):
    id: str
    sheet_id: str
    request_text: str = ""
    intro: str = ""
    requested_code: str | None = None
    options: list[LayoutOption] = Field(default_factory=list)
    status: Literal["open", "applied", "canceled"] = "open"
    choice: LayoutChoice | None = None


class PackChange(M):
    sheet_id: str
    from_code: str
    to_code: str


class PackOffer(M):
    id: str
    industry_code: str
    changes: list[PackChange] = Field(default_factory=list)
    status: Literal["open", "applied", "dismissed"] = "open"


class ActiveJob(M):
    job_id: str
    graph: str
    kind: str = Field("", description="vp.materials · vp.generate · vp.revise · vp.images")
    status: str = "queued"
    progress: int = 0
    started_at: str | None = None


class Owner(M):
    user_id: str
    name: str


class VPDoc(M):
    id: str
    version: int = Field(description="저장 지점 수(재료 완료 · 플랜 변경 · 생성 완료 · 레이아웃 적용 · 수치 반영 · 이미지 변경 · 넘김)")
    title: str
    customer_name: str | None = None
    project_id: str | None = None
    owner: Owner
    start: Start = "direct"
    status: VPStatus = "draft"
    ui_status: UiStatus = "draft"
    status_text: str = ""
    action_label: str = "이어서"
    step: int = 1
    resume_route: str = ""
    industry: Industry | None = None
    target_proposal: TargetProposal | None = None
    note: str = ""
    auto_answer: bool = False
    sources: list[Source] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    coverage: list[CoverageAxis] = Field(default_factory=list)
    materials: list[MaterialItem] = Field(default_factory=list)
    fixes: list[Fix] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    plan: Plan | None = None
    sheets: list[Sheet] = Field(default_factory=list)
    variants: list[Sheet] = Field(default_factory=list)
    image_slots: list[ImageSlot] = Field(default_factory=list)
    checks: list[CheckItem] = Field(default_factory=list)
    layout_requests: list[LayoutRequest] = Field(default_factory=list)
    pack_offers: list[PackOffer] = Field(default_factory=list)
    active_job: ActiveJob | None = None
    last_job: ActiveJob | None = None
    last_error: dict[str, Any] | None = None
    linked_proposal: dict[str, Any] | None = None
    labels: dict[str, str] = Field(default_factory=dict, description="말풍선 · 요약(connect · questions · materials_footer · generate · head_codes)")
    intros: dict[str, str] = Field(default_factory=dict, description="에이전트 문장(materials_review · questions · questions_default · result · structure)")
    auto_chips: list[str] = Field(default_factory=list, description="VP1Q `자동으로 정한 것`")
    legend: list[dict[str, str]] = Field(default_factory=list, description="VP1A 출처 범례(쓰인 출처만)")
    materials_ready: bool = False
    generated: bool = False
    created_at: str
    updated_at: str


# ── 목록 ──────────────────────────────────────────────────

class VPListItem(M):
    id: str
    title: str
    owner_name: str
    updated_at: str
    when_label: str
    industry: dict[str, str] | None = None
    layout_chips: list[LayoutChip] = Field(default_factory=list)
    ui_status: UiStatus
    status_text: str
    linked_proposal: dict[str, Any] | None = None
    action_label: str
    resume_route: str


class VPCounts(M):
    all: int = 0
    ask: int = 0
    check: int = 0
    run: int = 0
    done: int = 0
    draft: int = 0


class VPList(M):
    items: list[VPListItem]
    next_cursor: str | None = None
    counts: VPCounts
    total_label: str = ""


class VersionItem(M):
    version: int
    reason: str
    created_at: str


class VersionList(M):
    items: list[VersionItem]


class SavePoint(M):
    reason: str = Field("저장", max_length=40)


# ── 요청 ──────────────────────────────────────────────────

class SourceRef(M):
    kind: SourceKind
    ref_id: str


class CreateVP(M):
    start: Start = "direct"
    title: str | None = None
    customer_name: str | None = None
    project_id: str | None = None
    source_refs: list[SourceRef] | None = None
    target_proposal: TargetProposal | None = None
    auto_answer: bool = False
    note: str | None = None


class IndustryCode(M):
    code: str


class PatchVP(M):
    title: str | None = None
    customer_name: str | None = None
    note: str | None = None
    industry: IndustryCode | None = None
    clear_industry: bool = Field(False, description="업종 고정 풀기(다시 판별)")
    target_proposal: TargetProposal | None = None
    auto_answer: bool | None = None


class CloneVP(M):
    customer_name: str = Field(min_length=1, max_length=60)
    industry: IndustryCode | None = None
    keep_pinned: bool = True


class SourceToggle(M):
    kind: SourceKind
    ref_id: str
    connected: bool
    title: str | None = None


class PutSources(M):
    sources: list[SourceToggle]


class AddAttachment(M):
    file_id: str
    kind: AttachmentKind | None = None


class CollectBody(M):
    note: str | None = None


class FixDecision(M):
    decision: Literal["accept", "revert"]


class AnswerItem(M):
    question_id: str
    keys: list[str] | None = None
    text: str | None = None


class AnswerQuestions(M):
    answers: list[AnswerItem] = Field(default_factory=list)
    proceed: bool = True


class PlanOverride(M):
    VP: str | None = None
    EF: str | None = None
    CH: str | None = None
    clear: bool = Field(False, description="대안 선택을 모두 풀기")


class PatchPlan(M):
    override: PlanOverride


class GenerateBody(M):
    sheet_roles: list[Role] | None = None
    retry: bool = False


class MessageBody(M):
    text: str = Field(min_length=1, max_length=1000)
    context: Literal["materials", "questions", "structure", "result", "layout", "numbers", "images", "export"]
    sheet_id: str | None = None


class ChooseLayout(M):
    option_key: Literal["A", "B", "C"] | None = None
    layout_code: str | None = None
    pillars: int | None = Field(None, ge=2, le=4)
    pin: bool = False
    note: str | None = None
    request_id: str | None = None


class PatchSheet(M):
    pinned: bool | None = None
    title: str | None = None
    points: str | None = None
    speaker_notes: str | None = None
    content: SheetContent | None = Field(None, description="보낸 필드만 바꾼다(예: pillars 만)")


class AddSheet(M):
    kind: Literal["one_liner", "reference"]
    layout_code: str | None = None
    deployment_id: str | None = None


class PatchMetric(M):
    handling: Literal["request", "industry_avg", "exclude", "direct"]
    before: NumberValue | None = None
    after: NumberValue | None = None


class PutImageSlot(M):
    asset: AssetRef


class Restyle(M):
    style: Literal["illustration"] = "illustration"


class ExportBody(M):
    format: Literal["pptx", "pdf_summary"]
    include_notes: bool = True
    proposal_type: ProposalType | None = None


class HandoffOptions(M):
    estimates_as_notes: bool = True
    sync_storyboard: bool = True
    ask_before_overwrite_pinned: bool = True


class HandoffBody(M):
    proposal_id: str | None = None
    proposal_type: ProposalType = "standard"
    proposal_title: str | None = None
    options: HandoffOptions = Field(default_factory=HandoffOptions)
    interview_numbers_confirmed: bool | None = None
    note: str | None = None


class HandoffAck(M):
    result: Literal["applied", "needs_confirmation", "failed"]
    applied_sheet_ids: list[str] = Field(default_factory=list)
    pinned_conflicts: list[dict[str, str]] | None = None
    proposal_id: str | None = None
    proposal_title: str | None = None


class ProposalReleaseIn(M):
    """`POST /v1/vps/{vp_id}:release-proposal`(internal) — proposal 이 제안서를 지웠을 때."""
    proposal_id: str = Field(min_length=1)


class ProposalRelease(M):
    vp_id: str
    proposal_id: str
    released: bool
    linked_proposal: dict[str, Any] | None = None


class PackDecide(M):
    decision: Literal["apply", "dismiss"]


class DraftRqRef(M):
    rq_id: str
    version: int | None = None


class DraftSource(M):
    feature: str
    ref_id: str


class DraftBody(M):
    rq_ref: DraftRqRef | None = None
    sources: list[DraftSource] = Field(default_factory=list)
    proposal_type: ProposalType = "standard"
    sheet_roles: list[Role] | None = None
    industry_code: str | None = None
    products: list[str] | None = None
    customer_name: str | None = None
    proposal_id: str | None = None
    proposal_title: str | None = None
    project_id: str | None = None


class DraftAccepted(M):
    value_prop_id: str
    job_id: str
    status: str = "queued"


# ── 응답 ──────────────────────────────────────────────────

class LayoutCandidate(M):
    code: str
    display: str
    thumb: Thumb
    fit: int = Field(description="0~100, 업종판 제작 중이면 −1")
    why: str
    state: Literal["cur", "req", "normal", "no"]
    family: str = ""


class LayoutHeader(M):
    image: int
    no_image: int
    industry: int


class LayoutOptions(M):
    sheet_id: str
    sheet_label: str
    header: LayoutHeader
    intro: str
    request_id: str | None = None
    options: list[LayoutOption] | None = None
    candidates: list[LayoutCandidate]
    pillars: int
    other_sheets_label: str
    pinned: bool = False


class MetricCounts(M):
    total: int
    secured: int
    estimated: int
    missing: int


class MetricRule(M):
    usable: int
    secured: int
    estimated: int
    current: str
    would_switch_to: str | None = None
    tail: str | None = None
    text: str


class MetricsView(M):
    sheet_id: str
    code: str
    intro: str
    metrics: list[Metric]
    counts: MetricCounts
    rule: MetricRule
    pending_ask: int = 0
    pending_check: int = 0


class DataRequestDraft(M):
    text: str
    to_hint: str
    mailto: str
    targets: list[str] = Field(default_factory=list)


class ImageSlotCounts(M):
    slots: int
    official: int
    illust: int
    checks: int


class ImageSlotsView(M):
    items: list[ImageSlot]
    counts: ImageSlotCounts
    intro: str
    actions: list[PlanAlternative] = Field(default_factory=list)


class SlotCandidate(M):
    asset: AssetRef | None = None
    name: str
    tier: Literal["customer", "cut", "case", "ui", "illust"]
    tier_label: str
    current: bool = False
    mode: Literal["auto", "check"] = "auto"
    meta: ImageMeta | None = None


class SlotCandidates(M):
    slot_id: str
    header: str
    right: str = ""
    items: list[SlotCandidate]


class PackageRow(M):
    code: str
    sheet_label: str
    treatment: str


class PackageSheet(M):
    role: SheetRole
    layout: LayoutPick
    title: str
    points: str = ""
    content: SheetContent
    image_slots: list[ImageSlot] = Field(default_factory=list)
    speaker_notes: str = ""
    pinned: bool = False
    sheet_id: str | None = None


class PackageCounts(M):
    send: int
    added_not_in_section: int
    estimates_as_notes: int


class Package(M):
    proposal_type: ProposalType
    type_label: str
    path_label: str
    rows: list[PackageRow]
    sheets: list[PackageSheet]
    counts: PackageCounts
    sources_footer: list[str] = Field(default_factory=list)
    needs_variant: bool = Field(False, description="퀵윈인데 VP-G 변형이 아직 없음(넘길 때 만든다)")
    interview_numbers: list[str] = Field(default_factory=list)


class PackageSet(M):
    selected: ProposalType
    types: list[Package]
    dock: str
    estimates_note: str | None = None


class CopyText(M):
    text: str


class ExportRecord(M):
    id: str
    format: str
    status: str
    job_id: str | None = None
    file_id: str | None = None
    filename: str | None = None


class HandoffCreated(M):
    id: str
    status: str = "ready"
    open_route: str
    package: Package
    storyboard_synced: int = 0


class Handoff(M):
    id: str
    vp_id: str
    vp_version: int
    proposal_id: str | None = None
    proposal_type: ProposalType
    options: HandoffOptions
    package: Package
    status: str
    open_route: str = ""
    created_at: str = ""
    acked_at: str | None = None


class RuleRow(M):
    c: str
    o: str
    mode: Mode


class RuleStage(M):
    no: int
    title: str
    sub: str
    rules: list[RuleRow]


class BandRule(M):
    c: str
    t: str


class BandRow(M):
    code: str
    name: str
    ind: str
    rules: list[BandRule]


class LegendRow(M):
    mode: Mode
    label: str
    desc: str


class PackCell(M):
    code: str
    name: str
    status: Literal["in_production", "ready"]


class RoutingRules(M):
    eyebrow: str = "ROUTING · VALUE PROPOSITION"
    title: str
    legend: list[LegendRow]
    stages: list[RuleStage]
    band_title: str
    band_sub: str
    band_head: list[str]
    band: list[BandRow]
    packs: dict[str, Any]
    gaps_title: str
    gaps_sub: str
    gaps: list[RuleRow]
    asks_title: str
    asks: list[dict[str, Any]]
    thresholds: dict[str, Any]


class ScenarioRow(M):
    no: int
    name: str
    input: str
    industry: str
    pack: str
    flow_label: str
    chips: list[LayoutChip]
    asked: str
    mode: str = ""
    scene: str = ""


class Scenarios(M):
    rows: list[ScenarioRow]
    stats: list[dict[str, str]]


class LayoutCatalogEntry(M):
    code: str
    display: str
    family: str
    board: str
    role: str
    name: str
    when: str = ""
    shape: str = ""
    thumb: Thumb
    industry_code: str | None = None
    pack_role: str | None = None
    status: Literal["ready", "in_production"] = "ready"
    has_images: bool = False


class LayoutCatalog(M):
    items: list[LayoutCatalogEntry]
    counts: dict[str, int]


class IndustryPackItem(M):
    code: str
    name: str
    cell: str
    status: Literal["in_production", "ready"]
    released_at: str | None = None


class IndustryPacks(M):
    ready: int
    total: int = 16
    items: list[IndustryPackItem]
    banner: str | None = None
    banner_sub: str | None = None


class AnswerResult(VPDoc):
    """`VPDoc` + 재개한 잡 · 다음 화면."""
    resumed_job_id: str | None = None
    next_route: str = ""


class ProposalHandoff(M):
    """10-proposal.md §8.0 ProposalHandoff v1."""
    source: dict[str, Any]
    target: dict[str, Any]
    customer: dict[str, Any] | None = None
    rq_ref: dict[str, Any] | None = None
    items: list[dict[str, Any]]
    facts: list[dict[str, Any]] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
    live_link: bool = False
