"""mi API 요청 · 응답 모델 — 이 모델들이 contracts/mi.json 이 된다(03-mi.md §5 · §6).

이름 규칙: `…In` = 요청 본문, 그 밖 = 응답. 시간은 ISO 8601 UTC 문자열, ID 는 `<접두사>_<ULID>`.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Mode = Literal["auto", "check", "ask", "pin"]
Area = Literal["market", "customer", "user", "competitor"]
Status = Literal["draft", "designing", "ask", "designed", "queued", "running", "stopped", "done", "upd", "failed"]
UsageValue = Literal["standard", "solution", "quickwin", "exec_onepager", "none"]
ProposalType = Literal["standard", "quickwin", "solution"]
ClaimStatus = Literal["matched", "needs_check", "conflict", "stale", "confirmed", "checking", "missing"]
CitationStatus = Literal["matched", "needs_check", "unverifiable", "stale"]
SourceKind = Literal["web", "websearch_summary", "kb_case", "kb_official", "file", "user", "ca_import"]
SourceState = Literal["used", "checking", "excluded"]
Classification = Literal["public", "internal", "confidential", "customer"]
FixStatus = Literal["warn", "ok", "wait"]
InputKind = Literal["number", "ratio", "text", "file_only"]


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── 공통 ─────────────────────────────────────────────────
class ServiceInfo(_M):
    service: str
    title: str
    version: str


class JobAccepted(_M):
    job_id: str
    status: Literal["queued"] = "queued"


class OkOut(_M):
    ok: bool = True


# ── 작업 ─────────────────────────────────────────────────
class Requirement(_M):
    id: str
    text: str
    weight: int | None = Field(None, description="키맨 가중치 등(정의서) — 없으면 null")
    origin: Literal["input", "definition", "storyboard", "preset", "rfp", "inferred", "extracted", "user"] = "input"
    label: str | None = None
    code: str | None = Field(None, description="정의서 항목 코드(RQ-01) · 프리셋 요구 태그(R08)")
    inferred: bool = Field(False, description="한 줄 메모라 사례 DB 로 채운 요구(빈칸 추론)")
    basis: str | None = Field(None, description="추론 근거(예 '외식 · 카페 사례 19건')")


class AnalysisFile(_M):
    file_id: str
    name: str = ""
    doc_kind: Literal["rfp", "minutes", "ir", "internal_research", "deployment_report", "price_list", "spec_sheet",
                      "customer_material", "other"] = "other"
    classification: Literal["public", "internal", "confidential"] = "internal"
    include: bool = True


class Links(_M):
    requirements_id: str | None = None
    rq_version: int | None = None
    storyboard_id: str | None = None
    storyboard_title: str | None = None
    proposal_id: str | None = None
    proposal_type: ProposalType | None = None
    proposal_title: str | None = None
    competitor_analysis_id: str | None = None


class SegmentCandidate(_M):
    code: str
    confidence: float
    llm: float | None = None
    kb: float | None = None
    clue: float | None = None


class Clue(_M):
    text: str
    code: str
    weight: float = 0.0


class SegmentMix(_M):
    a: str
    b: str
    c: str


class SegmentDecision(_M):
    code: str | None = None
    mode: Mode | None = None
    confidence: float | None = None
    candidates: list[SegmentCandidate] = []
    clues: list[Clue] = []
    mix: SegmentMix | None = None
    inherited_from: str | None = Field(None, description="상속했으면 원천(storyboard · requirements · proposal · mi)")
    llm_failed: bool = False


class UsageDecision(_M):
    value: UsageValue | None = None
    mode: Mode | None = None
    reason: str = ""


class ScopeDecision(_M):
    areas: list[Area] = []
    mode: Mode | None = None
    reasons: dict[str, str] = {}
    reduced: list[Area] = Field([], description="축소한 영역(고객 공개 자료 3건 미만 → customer)")


class InternalDecision(_M):
    kb_case_count: int = 0
    included_file_ids: list[str] = []
    excluded_file_ids: list[str] = []
    mode: Mode | None = None
    summary: str = ""


class Depth(_M):
    target_sources: int = 30
    eta_s: int = 180


class MemoItem(_M):
    text: str
    at: str
    where: Literal["design", "run", "recheck"] = "design"


class SamsungProduct(_M):
    model_code: str | None = None
    family_id: str | None = None
    name: str
    ref: str | None = Field(None, description="셸 참조(kb:model:mdl_… · kb:family:fam_… · kb:solution:…)")
    kind: Literal["model", "family", "solution"] = "model"
    origin: Literal["topbar", "requirement", "s1", "user"] = "s1"


class Competitor(_M):
    id: str
    letter: str
    real_name: str
    aliases: list[str] = []
    kind_label: str = ""
    desc: str = ""
    origin: Literal["auto", "user", "ca_import", "mi_rfp"] = "auto"
    confidence: float | None = None
    pinned: bool = False
    removed: bool = False
    evidence_source_ids: list[str] = []
    order: int = 0
    lookup: Literal["done", "pending", "failed"] = "done"
    display: str = Field("", description="작업 화면 표기(`경쟁사 {글자}`)")
    export_display: str = Field("", description="내보내기 표기 미리보기(익명 방식 · 켜짐 여부에 따라)")
    tag: str = Field("", description="`자동 추천` · `직접 추가` · `경쟁사 분석에서`")


class Criterion(_M):
    id: str
    name: str
    source: Literal["requirements", "industry_cases", "user", "preset"] = "requirements"
    source_count: int | None = None
    weight: int = 3
    order: int = 0
    enabled: bool = True
    pinned: bool = False
    requirement_id: str | None = None
    pct: int = 0
    source_label: str = Field("", description="`요구사항` · `업종 사례 {n}건` · `직접 추가`")


class Preset(_M):
    segment: str
    req_items: list[str] = []


class Analysis(_M):
    id: str
    owner_id: str
    owner_name: str = ""
    project_id: str | None = None
    title: str = ""
    topic: str = ""
    customer_name: str | None = None
    requirements_text: str = ""
    requirements: list[Requirement] = []
    files: list[AnalysisFile] = []
    links: Links = Links()
    segment: SegmentDecision = SegmentDecision()
    usage: UsageDecision = UsageDecision()
    scope: ScopeDecision = ScopeDecision()
    anonymize: bool = True
    naming_mode: Literal["letter", "type"] = "letter"
    internal: InternalDecision = InternalDecision()
    depth: Depth = Depth()
    status: Status = "draft"
    status_label: str = ""
    version: int = Field(0, description="마지막으로 완료된 결과 버전(0 = 결과 없음)")
    current_job_id: str | None = None
    design_job_id: str | None = None
    design_status: Literal["none", "running", "ask", "done", "failed"] = "none"
    last_screen: str | None = None
    memos: list[MemoItem] = []
    competitors: list[Competitor] = []
    criteria: list[Criterion] = []
    samsung_products: list[SamsungProduct] = []
    preset: Preset | None = None
    req_summary: str = ""
    scope_desc: dict[str, str] = {}
    input_kind: str = Field("", description="MI1Q `{입력 종류}` — 회의록 · RFP · 요구사항 · 메모")
    one_line_memo: bool = False
    route: str = ""
    eta_s: int = 180
    run_label: str = Field("", description="`분석 시작 (약 {m}분)`")
    created_at: str = ""
    updated_at: str = ""
    analyzed_at: str | None = None
    next_recheck_at: str | None = None
    edited_after_analysis: bool = False
    result: ResultView | None = None


class CreateAnalysisIn(_M):
    customer_name: str | None = Field(None, max_length=60)
    customer: dict[str, Any] | None = Field(None, description="제안서 M2 별칭 `{name}`")
    requirements_text: str | None = Field(None, max_length=4000)
    file_ids: list[str] = []
    links: Links | None = None
    segment_pin: str | None = None
    preset: Preset | None = None
    project_id: str | None = None
    rq_ref: dict[str, Any] | None = Field(None, description="`{rq_id, version}` (제안서 M2)")
    scope: list[str] | None = Field(None, description="고정할 범위(market · customer · user(users) · competitor)")
    purpose: Literal["proposal", "user"] | None = None
    proposal_type: ProposalType | None = None
    auto_run: bool = False


class AutoRunAccepted(_M):
    analysis_id: str
    job_id: str
    status: Literal["queued"] = "queued"


class SegmentPatch(_M):
    code: str
    mode: Literal["pin"] = "pin"
    mix: SegmentMix | None = None


class ScopePatch(_M):
    areas: list[Area]
    mode: Literal["pin"] = "pin"


class UsagePatch(_M):
    value: UsageValue
    mode: Literal["pin"] = "pin"
    proposal_id: str | None = None
    proposal_title: str | None = None


class InternalPatch(_M):
    included_file_ids: list[str] | None = None
    excluded_file_ids: list[str] | None = None


class RequirementIn(_M):
    id: str | None = None
    text: str
    weight: int | None = None
    origin: Literal["input", "definition", "storyboard", "preset", "rfp", "inferred"] = "input"
    label: str | None = None


class FileIn(_M):
    file_id: str
    name: str | None = None
    doc_kind: str | None = None
    classification: Literal["public", "internal", "confidential"] | None = None
    include: bool | None = None


class AnalysisPatch(_M):
    title: str | None = Field(None, max_length=30)
    customer_name: str | None = Field(None, max_length=60)
    requirements_text: str | None = Field(None, max_length=4000)
    requirements: list[RequirementIn] | None = None
    file_ids: list[str] | None = None
    files: list[FileIn] | None = None
    segment: SegmentPatch | None = None
    scope: ScopePatch | None = None
    anonymize: bool | None = None
    naming_mode: Literal["letter", "type"] | None = None
    internal: InternalPatch | None = None
    usage: UsagePatch | None = None
    last_screen: str | None = None
    preset: Preset | None = None
    links: Links | None = None


class DuplicateIn(_M):
    keep_scope: bool = True


class StoryboardImportIn(_M):
    storyboard_id: str
    title: str = ""
    customer_name: str | None = None
    requirements: list[RequirementIn] = []
    key_messages: list[str] = []
    segment: str | None = None
    research_topics: list[str] = []


class RequirementsImportIn(_M):
    requirements_id: str
    rq_version: int | None = None


class AdditionsIn(_M):
    kind: Literal["product", "solution", "case", "image"]
    ids: list[str]


class AdditionsOut(_M):
    added: list[str]


class AnalysisAction(_M):
    label: str
    route: str
    kind: Literal["fix", "rerun", "progress", "continue", "open", "retry"] = "open"


class MenuItem(_M):
    key: str
    label: str
    hint: str = ""
    route: str | None = None
    highlight: bool = False


class AnalysisListItem(_M):
    id: str
    title: str
    version: int = 0
    owner_name: str = ""
    time_label: str = ""
    sub: str = ""
    segment: str | None = None
    segment_label: str = "—"
    scope_label: str = ""
    scope_selected: bool = False
    status: Status
    status_label: str
    status_tone: Literal["done", "upd", "run", "draft"] = "draft"
    note: str = ""
    proposal_title: str | None = None
    action: AnalysisAction
    menu: list[MenuItem] = []
    changes_head: dict[str, Any] | None = Field(None, description="upd 행 메뉴 머리 상자 `{title, summary}`")
    route: str
    updated_at: str
    current_job_id: str | None = None
    fix_open: int = 0
    has_competitors: bool = False


class ListCounts(_M):
    all: int = 0
    run: int = 0
    done: int = 0
    upd: int = 0
    draft: int = 0


class UpdBanner(_M):
    n: int
    title: str
    text: str
    kinds: list[str] = []
    target_ids: list[str] = []


class AnalysisList(_M):
    items: list[AnalysisListItem]
    next_cursor: str | None = None
    counts: ListCounts
    upd_changes: dict[str, Any] = {}
    fix_open_works: int = 0
    banner: UpdBanner | None = None
    header: str = ""


class VersionSummary(_M):
    n: int
    kind: str
    created_at: str
    created_by: str = ""
    stopped: bool = False
    summary: str = ""
    current: bool = False


class VersionList(_M):
    items: list[VersionSummary]


class VersionOut(_M):
    version: int


# ── 업종 · 규칙 ──────────────────────────────────────────
class SegmentItem(_M):
    code: str
    full: str
    short: str
    case_count: int = 0
    has_layouts: bool = True
    aliases: list[str] = []
    mapping: bool = True
    kb_id: str | None = None


class SegmentList(_M):
    items: list[SegmentItem]
    case_total: int = 0
    method: str = ""
    needs_confirmation: list[str] = []
    home: list[dict[str, Any]] = Field([], description="MI0 업종 칩(최대 6) `{code, short, n}`")


class ReqTypeOut(_M):
    code: str
    label: str
    n: int
    examples: list[str] = []
    label_basis: Literal["kb", "example"] = "kb"


class NamedCount(_M):
    name: str
    n: int
    id: str | None = None
    kind: str | None = None


class SegmentInsights(_M):
    code: str
    full: str
    short: str
    cases: int
    req_types: list[ReqTypeOut]
    products: list[NamedCount]
    solutions: list[NamedCount]
    layouts: list[str]
    gaps: list[str] = []


class DetectIn(_M):
    text: str = ""
    analysis_id: str | None = None


class DetectOut(_M):
    candidates: list[SegmentCandidate]
    clues: list[Clue] = []
    top: str | None = None
    basis: str = Field("", description="`Storyboard '{SB 제목}' 기준` · `입력한 요구사항 기준` · `정의서 기준`")
    customer_name: str | None = None


class RuleRow(_M):
    c: str
    o: str
    mode: Mode
    mode_label: str


class RuleStage(_M):
    no: str
    title: str
    sub: str
    rules: list[RuleRow]


class LayoutBandRow(_M):
    code: str
    name: str
    ind: str
    has_industry: bool
    rules: list[list[str]]


class RoutingRules(_M):
    header: dict[str, str]
    modes: list[dict[str, str]]
    stages: list[RuleStage]
    layout: dict[str, Any]
    gaps: RuleStage
    asks: dict[str, Any]
    thresholds: dict[str, Any]


class Capabilities(_M):
    websearch: dict[str, Any]
    search_api: dict[str, Any]
    fetch: bool
    i2t: bool
    mode: str = ""


# ── 설계 ─────────────────────────────────────────────────
class Decision(_M):
    key: Literal["segment", "usage", "scope", "competitors", "naming", "internal", "depth"]
    label: str
    display_value: str
    reason: str
    mode: Mode
    change_route: str = ""
    depends_on: list[str] = []
    input_hash: str = ""
    updated_at: str = ""


class SheetPreview(_M):
    sheet: str
    code: str
    thumb: str
    note: str
    industry: bool = False


class DesignView(_M):
    status: Literal["none", "running", "ask", "done", "failed"]
    job_id: str | None = None
    decisions: list[Decision] = []
    tally: dict[str, int] = {}
    sheets_preview: list[SheetPreview] = []
    sheets_head: str = ""
    usage_label: str = ""
    ask: dict[str, Any] | None = Field(None, description="awaiting_input 데이터(업종 두 갈래)")
    run_label: str = ""
    error: dict[str, Any] | None = None


class MemoIn(_M):
    text: str = Field(..., min_length=1, max_length=2000)


# ── 경쟁사 · 기준 ────────────────────────────────────────
class CompetitorList(_M):
    items: list[Competitor]
    counts: dict[str, int]
    removed: list[Competitor] = []


class CompetitorAddIn(_M):
    name: str = Field(..., min_length=1, max_length=80)


class CompetitorAccepted(_M):
    job_id: str
    competitor_id: str
    status: Literal["queued"] = "queued"


class CompetitorPatch(_M):
    removed: bool | None = None
    order: int | None = None


class CriterionIn(_M):
    id: str | None = None
    name: str = Field(..., min_length=1, max_length=40)
    source: Literal["requirements", "industry_cases", "user", "preset"] = "user"
    source_count: int | None = None
    weight: int = Field(3, ge=1, le=5)
    order: int | None = None
    enabled: bool = True


class CriteriaPut(_M):
    items: list[CriterionIn]


class CriteriaList(_M):
    items: list[Criterion]
    suggestions: list[NamedCount] = []
    suggestion_head: str = ""


class CaImportIn(_M):
    analysis_id: str | None = None
    customer_name: str | None = None
    ca_bundle: dict[str, Any]


class CaImportAccepted(_M):
    job_id: str
    analysis_id: str
    revision_id: str | None = None
    status: Literal["queued"] = "queued"


# ── 실행 · 진행 ──────────────────────────────────────────
class RunIn(_M):
    mode: Literal["auto", "full", "changed_only", "resume"] = Field(
        "auto", description="auto(기본) = 의존 해시가 바뀐 영역만 · full = 전부 다시 · changed_only = 바뀐 영역 + areas · resume = 정리 못 한 영역")
    areas: list[Area] | None = None


class StageState(_M):
    stage: Literal["search", "organize", "write"]
    name: str
    status: Literal["wait", "run", "done"]
    note: str = ""


class AreaProgress(_M):
    area: Area
    name: str
    status: Literal["wait", "run", "done", "failed"]
    note: str = ""


class RecentSource(_M):
    kind: Literal["사내", "공개"]
    name: str
    state: str


class RunProgress(_M):
    job_id: str | None = None
    status: str = "none"
    pct: int = 0
    eta_s: int | None = None
    stage: str | None = None
    stages: list[StageState] = []
    areas: list[AreaProgress] = []
    sources: dict[str, int] = {}
    recent_sources: list[RecentSource] = []
    previewable: list[str] = []
    summary_chip: str = ""
    card_title: str = ""
    card_sub: str = ""
    error: dict[str, Any] | None = None
    memos: list[MemoItem] = []


# ── 결과 ─────────────────────────────────────────────────
class ClaimRef(_M):
    """블록 안 문장 — 화면 문장 + 탭 안 출처 번호."""
    id: str
    text: str
    status: ClaimStatus
    label: str
    ns: list[int] = []
    inferred: bool = False
    unverified_numbers: bool = False


class SizePoint(_M):
    year: int
    value: float | None = None
    unit: str = ""
    claim: ClaimRef | None = None


class Cagr(_M):
    value: float | None = None
    period: str = ""
    claim: ClaimRef | None = None


class Trend(_M):
    title: str
    when: str | None = None
    claim: ClaimRef | None = None
    implication: str = ""


class Regulation(_M):
    title: str
    claim: ClaimRef | None = None


class MarketBlock(_M):
    size_series: list[SizePoint] = []
    size_unit: str = ""
    size_label: str = ""
    cagr: Cagr | None = None
    trends: list[Trend] = []
    regulations: list[Regulation] = []
    kb_trend: ClaimRef | None = Field(None, description="사내 사례 DB 도입 경향(D2)")


class StructureItem(_M):
    label: str
    value: str = ""
    claim: ClaimRef | None = None


class OpsChallenge(_M):
    stage: str
    claim: ClaimRef | None = None


class CustomerBlock(_M):
    summary: ClaimRef | None = None
    strategy: list[ClaimRef] = []
    expansion: list[ClaimRef] = []
    structure: list[StructureItem] = []
    ops_challenges: list[OpsChallenge] = []
    reduced: bool = False


class Persona(_M):
    role: str
    goal: str = ""
    pain: str = ""
    context: str = ""
    claims: list[ClaimRef] = []


class JourneyStep(_M):
    stage: str
    touchpoint: str = ""
    pain: str = ""
    opportunity: str = ""
    claims: list[ClaimRef] = []


class CompositionItem(_M):
    label: str
    value: float | None = None
    unit: str = "%"
    claim: ClaimRef | None = None


class UserBlock(_M):
    personas: list[Persona] = []
    journey: list[JourneyStep] = []
    composition: list[CompositionItem] = []


class TableColumn(_M):
    key: str = Field(..., description="cmp_… 또는 samsung")
    label: str
    sub: str = Field("", description="작업 화면 보조 글자(실명)")
    samsung: bool = False


class TableCell(_M):
    text: str
    claim_ids: list[str] = []
    ns: list[int] = []
    placeholder: bool = False
    status: ClaimStatus | None = None
    verdict: Literal["samsung_better", "similar", "samsung_worse", "unknown"] | None = None


class TableRow(_M):
    criterion_id: str
    name: str
    weight: int = 3
    cells: dict[str, TableCell]


class CompareTable(_M):
    columns: list[TableColumn]
    rows: list[TableRow]


class Strength(_M):
    id: str
    title: str
    note: str
    criterion_ids: list[str] = []
    claims: list[ClaimRef] = []


class CompetitorBlock(_M):
    table: CompareTable | None = None
    strengths: list[Strength] = []
    samsung_products: list[SamsungProduct] = []


class TabInfo(_M):
    area: Area
    label: str
    status: Literal["done", "running", "wait", "failed", "reused", "preview"]
    needs_check: int = 0


class TabFooter(_M):
    sources: int = 0
    by_kind: dict[str, int] = {}
    unverified: bool = False
    text: str = ""


class CheckChip(_M):
    kind: Literal["segment", "competitors", "conflict", "inferred"]
    label: str
    mode: Mode | None = None
    count: int | None = None
    target: str | None = None


class ResultView(_M):
    analysis_id: str
    version: int
    kind: str = ""
    created_at: str = ""
    stopped: bool = False
    preview: bool = False
    is_latest: bool = True
    analysis_status: Status = "done"
    tabs: list[TabInfo] = []
    market: MarketBlock | None = None
    customer: CustomerBlock | None = None
    user: UserBlock | None = None
    competitor: CompetitorBlock | None = None
    footers: dict[str, TabFooter] = {}
    check_chips: list[CheckChip] = []
    web_unavailable: bool = False
    upd: dict[str, Any] | None = None
    agent_text: str = ""
    needs_check_total: int = 0
    failed_areas: list[Area] = []
    implications: dict[str, Any] | None = None


class CitationOut(_M):
    n: int
    source_id: str
    status: CitationStatus


class ClaimItem(_M):
    id: str
    area: Area
    text: str
    status: ClaimStatus
    label: str
    citations: list[CitationOut] = []
    inferred: bool = False
    block_path: str = ""


class ClaimList(_M):
    items: list[ClaimItem]
    tab_sources: dict[str, int] = {}
    badges: dict[str, int] = {}
    needs_check_total: int = 0
    summary_text: str = ""


class SourceCard(_M):
    n: int
    source_id: str
    kind: SourceKind
    kind_label: str
    status: CitationStatus | Literal["confirmed"]
    status_label: str
    title: str
    meta: str = ""
    quote: str = ""
    quote_before: str = ""
    quote_highlight: str = ""
    quote_after: str = ""
    quote_style: Literal["normal", "model", "snippet", "summary", "value"] = "normal"
    reason: str = ""
    reason_code: str | None = None
    actions: list[str] = []
    url: str | None = None
    file_id: str | None = None
    page: int | None = None
    footnote: str = ""
    flag: str = ""
    has_snapshot: bool = False


class ClaimDetail(_M):
    claim: ClaimItem
    tab: Area
    tab_label: str
    cards: list[SourceCard]
    counts: dict[str, int]
    conflict: dict[str, Any] | None = None
    fix_id: str | None = None


class SourceOut(_M):
    id: str
    kind: SourceKind
    subtype: str = ""
    title: str = ""
    publisher: str = ""
    url: str | None = None
    file_id: str | None = None
    published_at: str | None = None
    published_basis: str = "unknown"
    retrieved_at: str = ""
    authority: int = 5
    classification: str = "public"
    state: SourceState = "used"
    excluded_reason: str | None = None
    mode: str = "summary_only"
    areas: list[str] = []
    competitor_id: str | None = None
    query: str | None = None
    n: int | None = None
    card: SourceCard | None = None


class SourceList(_M):
    items: list[SourceOut]
    counts: dict[str, int] = {}


class SnapshotOut(_M):
    text: str
    pages: list[str] | None = None


class SourceAddIn(_M):
    url: str | None = None
    file_id: str | None = None
    classification: Literal["internal", "confidential", "customer", "public"] | None = None
    claim_id: str | None = None


class SourceAccepted(_M):
    job_id: str
    source_id: str
    status: Literal["queued"] = "queued"


class QuestionIn(_M):
    text: str = Field(..., min_length=1, max_length=2000)
    tab: Area | None = None
    claim_id: str | None = None


class AnswerCitation(_M):
    n: int
    source_id: str


class AnswerOut(_M):
    answer_md: str
    citations: list[AnswerCitation] = []
    answerable: bool = True


class FollowupIn(_M):
    text: str = Field(..., min_length=1, max_length=2000)
    tab: Area | None = None


class FollowupOut(_M):
    intent: Literal["question", "revision"]
    answer_md: str | None = None
    citations: list[AnswerCitation] = []
    revision_id: str | None = None
    job_id: str | None = None
    scope: dict[str, Any] | None = None
    instruction: str | None = None


class OnepagerOut(_M):
    status: Literal["none", "running", "done", "failed"]
    job_id: str | None = None
    quadrants: dict[str, str] = {}
    conclusion: str = ""
    claims: list[str] = []
    version: int | None = None


# ── 확정 필요 항목 ───────────────────────────────────────
class FixHistory(_M):
    at: str
    status: FixStatus
    value: str | None = None
    value_source: str | None = None
    sub_text: str = ""
    by: str = ""


class FixItem(_M):
    id: str
    claim_id: str | None = None
    cell_ref: str | None = None
    tab: Area
    tab_label: str
    title: str
    metric_key: str | None = None
    input_kind: InputKind = "number"
    unit: str | None = None
    status: FixStatus
    reason_code: str
    sub_text: str
    value: str | None = None
    value_source: Literal["user", "file", "kb"] | None = None
    note: str | None = None
    file_id: str | None = None
    file_name: str | None = None
    page: int | None = None
    job_id: str | None = None
    carry: bool = True
    confirmed_by: str | None = None
    confirmed_at: str | None = None
    history: list[FixHistory] = []
    actions: list[str] = []
    placeholder: str = "값 입력"
    suggestion: dict[str, Any] | None = None
    competitor: bool = False
    samsung_model: str | None = None


class FixList(_M):
    items: list[FixItem]
    counts: dict[str, int]
    version: int = 0


class FixPatch(_M):
    value: str = Field(..., max_length=200)
    unit: str | None = None
    note: str | None = None


class FixScanIn(_M):
    file_id: str
    classification: Literal["internal", "confidential", "customer", "public"] = "internal"
    fix_ids: list[str] | None = None


class FixParseIn(_M):
    text: str = Field(..., min_length=1, max_length=2000)


class FixSuggestion(_M):
    fix_id: str
    value: str
    unit: str | None = None
    basis: str = ""


class FixParseOut(_M):
    suggestions: list[FixSuggestion]


class FixApplyIn(_M):
    carry_remaining: bool = True


class CustomerQuestionOut(_M):
    question: str


# ── 부분 재분석 ──────────────────────────────────────────
class RevisionScope(_M):
    kind: Literal["area", "rows", "strengths", "claims"]
    area: Area | None = None
    ids: list[str] | None = None


class RevisionIn(_M):
    scope: RevisionScope
    instruction: str = Field("", max_length=2000)


class RevisionAccepted(_M):
    job_id: str
    revision_id: str
    status: Literal["queued"] = "queued"


class RoundIn(_M):
    instruction: str = Field(..., min_length=1, max_length=2000)
    scope: RevisionScope | None = None


class Change(_M):
    id: str
    revision_id: str
    kind: Literal["row_add", "row_remove", "value_edit", "strength_edit", "text_edit", "source_add"]
    target: dict[str, Any]
    before: Any = None
    after: Any = None
    claim_ids: list[str] = []
    reverted: bool = False
    label: str = ""


class ChangePatch(_M):
    reverted: bool


class Revision(_M):
    id: str
    analysis_id: str
    base_version: int
    scope: RevisionScope
    rounds: list[dict[str, Any]] = []
    origin: Literal["user", "followup", "segment_change", "ca_import", "claim_research"] = "user"
    status: Literal["running", "proposed", "applied", "discarded", "failed"]
    job_id: str | None = None
    duration_s: int = 0
    sources_added: int = 0
    applied_version: int | None = None
    error: dict[str, Any] | None = None
    created_at: str = ""


class RevisionView(_M):
    revision: Revision
    changes: list[Change]
    chips: dict[str, int]
    changed_count: int
    sources_added: int
    duration_s: int
    quick_suggestions: list[str]
    footer: str = ""
    agent_text: str = ""
    scope_label: str = ""
    preview: ResultView | None = Field(None, description="변경 안을 적용한 모습(되돌린 변경 제외)")
    eta_s: int = 20


# ── 시트 구성 · 레이아웃 ─────────────────────────────────
class Alternative(_M):
    code: str
    fit: int


class NeedReport(_M):
    need: str
    ok: bool
    detail: str = ""


class SlidePlan(_M):
    id: str
    analysis_id: str
    version: int
    sheet_type: str
    sheet_name: str
    source_label: str
    item_label: str = ""
    included: bool
    include_mode: Mode
    template_code: str
    template_name: str
    thumb_kind: str
    industry_layout: bool
    why: str
    fit: int
    alternatives: list[Alternative] = []
    needs_report: list[NeedReport] = []
    pinned: bool = False
    options: dict[str, Any] = {}
    area: Area | None = None
    in_section: bool = True
    fix_open: int = 0
    order: int = 0
    status: Literal["ok", "warn", "add"] | None = Field(None, description="MI4 매핑 상태(내보내기 화면만) — 그대로 들어가요 · [확정 필요] n건 · 섹션에 없는 시트")
    status_label: str = ""


class SlidesView(_M):
    usage: UsageValue | None
    usage_label: str
    header: dict[str, Any]
    rows: list[SlidePlan]
    order: list[str]
    footer: str = ""


class SlidePatch(_M):
    included: bool | None = None
    template_code: str | None = None
    pinned: bool | None = None


class LayoutOption(_M):
    key: Literal["A", "B", "C"]
    title: str
    desc: str
    recommended: bool = False
    predicted_fit: int = 0
    eta_s: int | None = None
    template: str = ""


class TemplateCandidate(_M):
    code: str
    name: str
    thumb_kind: str
    tag: Literal["사용 중", "요청", "고를 수 없음", ""] = ""
    needs: list[NeedReport] = []
    fit: int
    fit_label: str = ""


class CandidatesView(_M):
    sheet: SlidePlan
    request_text: str = ""
    requested: str | None = None
    explanation: str = ""
    options: list[LayoutOption] = []
    templates: list[TemplateCandidate] = []
    head: str = ""
    others: list[dict[str, Any]] = []


class LayoutIn(_M):
    option: Literal["A", "B", "C"]
    template: str
    axes: dict[str, str] | None = None
    pin: bool | None = None


class SlideRequestIn(_M):
    text: str = Field(..., min_length=1, max_length=2000)


class SlideRequestOut(_M):
    kind: Literal["layout", "include", "none"]
    sheet_id: str | None = None
    requested: str | None = None
    changed: list[str] = []
    message: str = ""


# ── 넘김 · 묶음 · 내보내기 ──────────────────────────────
class HandoffOptions(_M):
    cite_sources: bool = True
    fix_notes: bool = True
    link_why: bool = True


class HandoffConfirm(_M):
    real_names: bool | None = None
    confidential: Literal["exclude", "include"] | None = None
    overwrite_pinned: bool | None = None


class HandoffIn(_M):
    target: Literal["proposal_mi", "proposal_why", "vp", "storyboard", "scenario"]
    target_id: str | None = None
    target_title: str | None = None
    sheets: list[str] | None = None
    options: HandoffOptions | None = None
    confirm: HandoffConfirm | None = None
    dry_run: bool = False
    target_pinned_sheets: list[str] | None = Field(None, description="제안서에서 고정한 시트(시트 유형 · 템플릿 코드) — 웹이 알면 넘긴다")


class HandoffOut(_M):
    handoff_id: str | None = None
    bundle_url: str = ""
    sheets: list[str] = []
    status: Literal["ready", "prepared"] = "prepared"
    target_id: str | None = None
    section_key: str = "mi"


class Handoff(_M):
    id: str
    analysis_id: str
    version: int
    target: str
    target_id: str | None = None
    target_title: str | None = None
    sheets: list[str] = []
    options: HandoffOptions = HandoffOptions()
    confirmations: HandoffConfirm = HandoffConfirm()
    anonymization_map: dict[str, str] = {}
    status: Literal["prepared", "delivered", "failed"]
    served_named_at: list[str] = []
    created_at: str = ""
    updated_at: str = ""


class HandoffPatch(_M):
    status: Literal["delivered", "failed"]
    target_title: str | None = None
    target_id: str | None = None


class BundleSheet(_M):
    id: str
    sheet_type: str
    sheet_name: str
    template_code: str
    why: str = ""
    content: dict[str, Any] = {}
    fact_check: list[dict[str, Any]] = []
    footnotes: list[dict[str, Any]] = []


class Bundle(_M):
    analysis_id: str
    version: int
    handoff_id: str | None = None
    target: str
    customer: dict[str, Any] = {}
    usage: str | None = None
    sheets: list[BundleSheet] = []
    why_samsung: dict[str, Any] | None = None
    vp_materials: dict[str, Any] | None = None
    options: HandoffOptions = HandoffOptions()
    anonymization: dict[str, Any] = {}
    requirements: list[dict[str, Any]] | None = None
    competitors: list[dict[str, Any]] | None = None
    criteria: list[dict[str, Any]] | None = None
    segment: str | None = None


class EvidenceCitation(_M):
    title: str
    url: str | None = None


class EvidenceItem(_M):
    key: str = Field(..., description="`strength:{i}` · `number:{i}` · `challenge:{i}`")
    kind: Literal["strength", "number", "challenge"]
    kind_label: str
    text: str
    status: str = Field("", description="수치만 — `원문 일치` · `확인 필요`")
    default_on: bool = False
    citations: list[EvidenceCitation] = []


class EvidenceSnapshot(_M):
    """Storyboard Key Message 근거 스냅숏(02-storyboard §8.3) — 웹이 storyboard `key-messages/{kmsg}/evidence` 로 올린다. 익명 처리를 마친 값."""
    analysis_id: str
    version: int
    source: dict[str, Any] = Field(default_factory=dict, description="`{service:'mi', ref_id, title, route}` — PostEvidence.source 그대로")
    storyboard_id: str | None = None
    storyboard_title: str | None = None
    items: list[EvidenceItem] = []


class ExportIn(_M):
    format: Literal["pdf_report", "pptx_onepager", "xlsx_table"]
    audience: Literal["customer", "internal"] = "customer"


class ShareOut(_M):
    share_url: str
    token: str | None = None


class ExportView(_M):
    """MI4 화면 데이터(제안 — 문서 §4.14 표시 데이터를 한 번에)."""
    target: dict[str, Any] | None = None
    usage: UsageValue | None = None
    usage_label: str = ""
    mapping_head: str = ""
    rows: list[SlidePlan] = []
    options: dict[str, Any] = {}
    strengths_count: int = 0
    show_link_why: bool = False
    files: list[dict[str, str]] = []
    next_features: list[dict[str, Any]] = []
    footer: str = ""
    vp_card: dict[str, Any] | None = None
    proposals: list[dict[str, Any]] = []


class ProposalHandoffSource(_M):
    feature: str = "MI"
    ref_id: str
    version: int
    title: str
    updated_at: str
    route: str


class ProposalHandoffItem(_M):
    key: str
    label: str
    from_label: str | None = None
    sheet_role: str
    sheet_title: str | None = None
    template_hint: dict[str, str] | None = None
    status: Literal["ok", "warn", "add"]
    status_label: str
    include_default: bool
    content: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []


class ProposalFact(_M):
    key: str
    label: str
    value: str | None = None
    unit: str | None = None
    status: Literal["confirmed", "unconfirmed", "placeholder"]
    placeholder: str | None = None
    source: dict[str, Any] | None = None


class ProposalHandoff(_M):
    source: ProposalHandoffSource
    target: dict[str, str]
    customer: dict[str, Any] | None = None
    rq_ref: dict[str, Any] | None = None
    items: list[ProposalHandoffItem]
    facts: list[ProposalFact] = []
    assets: list[dict[str, Any]] = []


class FactQuestion(_M):
    key: str
    label: str
    context: str | None = None
    unit: str | None = None


class FactsLookupIn(_M):
    questions: list[FactQuestion]
    research: bool = False


class FactCandidate(_M):
    value: str
    unit: str | None = None
    status: ClaimStatus
    claim_id: str
    source: dict[str, Any] | None = None


class FactsLookupItem(_M):
    key: str
    candidates: list[FactCandidate]


class FactsLookupOut(_M):
    items: list[FactsLookupItem]


# ── 재확인 ───────────────────────────────────────────────
class RecheckChange(_M):
    kind: Literal["competitor_new_product", "report_revised", "source_changed", "kb_updated"]
    title: str
    summary: str = ""
    detected_at: str = ""
    evidence_source_id: str | None = None
    affected_areas: list[Area] = []
    verification: Literal["matched", "needs_check"] = "needs_check"


class ChangesView(_M):
    items: list[RecheckChange]
    summary: str = ""
    head: str = ""
    affected_areas: list[Area] = []
    eta_label: str = ""


Analysis.model_rebuild()


class TableText(_M):
    """`표 복사` — 탭으로 나눈 비교표 글."""
    text: str
    columns: list[str] = []
    rows: int = 0
