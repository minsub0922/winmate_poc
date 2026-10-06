"""competitor API 모델 — 이 파일의 모델이 `contracts/competitor.json` 의 스키마가 된다(make contracts SERVICE=competitor).

필드 이름은 04-competitor.md §5 · §6 을 따른다. 화면이 바로 그릴 수 있게 표시 문구(`*_label` · `display` · `text`)를 함께 낸다.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

InputMode = Literal["free", "requirements", "mi"]
Status = Literal["draft", "finding", "ask", "confirming", "analyzing", "stopped", "done", "upd", "failed"]
SlotKey = Literal["customer", "industry", "place", "product"]
Found = Literal["found", "partial", "empty"]
CandStatus = Literal["rec", "check", "drop", "user"]
CritSource = Literal["requirements", "industry_cases", "default", "user"]
Verdict = Literal["samsung_better", "similar", "samsung_worse", "unknown"]
FactKey = Literal["lineup", "price", "solution", "references", "recent"]
RunMode = Literal["full", "changed_only", "rejudge", "resume"]
HandoffTarget = Literal["mi", "proposal_why", "storyboard", "report"]


class M(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── 공통 ─────────────────────────────────────────────────
class ServiceInfo(M):
    service: str
    title: str
    version: str


class JobAccepted(M):
    job_id: str
    status: str = "queued"
    analysis_id: str | None = None


class ChipView(M):
    key: str = Field(description="industry_basis · region_missing · industry_inferred · place_inferred · industry_check · auto_confirmed · unknown_cells")
    label: str = Field(description="`업종 기준` · `지역 미반영` · `업종 추정` · `장소 추정` · `업종 확인` · `후보 자동 확정` · `확인 필요 {n}`")
    mode: Literal["auto", "check", "ask", "pin"] = "check"


class HeaderView(M):
    kicker: str = ""
    title: str = ""
    desc: str = ""


# ── 칸 · 업종 ────────────────────────────────────────────
class SlotView(M):
    key: SlotKey
    label: str = Field(description="고객사 · 업종 · 장소 · 제품")
    value: str | None = None
    found: Found = "empty"
    origin: str | None = Field(None, description="input · definition · answer · inferred · mi · rfp")
    confidence: float | None = None
    chip_text: str = Field("", description="`{항목} · {값}` 또는 `{항목} · 비어 있음`")
    partial: bool = False
    code: str | None = Field(None, description="업종 칸이면 업종 코드(FB …)")


class SlotsView(M):
    customer: SlotView
    industry: SlotView
    place: SlotView
    product: SlotView


class SegmentCandidate(M):
    code: str
    name: str = ""
    confidence: float = 0.0


class SegmentView(M):
    code: str = "GEN"
    name: str = Field("범용", description="업종 short 이름")
    full: str = ""
    confidence: float = 0.0
    ambiguous: bool = False
    gap: float | None = None
    candidates: list[SegmentCandidate] = Field(default_factory=list)


class RfpView(M):
    competitor_mentions: list[str] = Field(default_factory=list)
    eval_criteria: list[str] = Field(default_factory=list)


class ParseIn(M):
    text: str | None = Field(None, max_length=8000)
    file_ids: list[str] = Field(default_factory=list)
    requirements_id: str | None = None
    rq_version: int | None = None
    extra_text: str | None = Field(None, max_length=4000)


class ParseOut(M):
    slots: SlotsView
    found_count: int
    segment: SegmentView
    rfp: RfpView = Field(default_factory=RfpView)
    include_names: list[str] = Field(default_factory=list)
    exclude_names: list[str] = Field(default_factory=list)
    reading_files: bool = False
    degraded: bool = Field(False, description="LLM 없이 KB 만으로 읽음(§4.4 2)")


# ── 작업 ─────────────────────────────────────────────────
class MiRef(M):
    analysis_id: str
    version: int | None = None


class RqRef(M):
    rq_id: str
    version: int | None = None


class AnalysisCreate(M):
    input_mode: InputMode = "free"
    text: str | None = Field(None, max_length=8000)
    file_ids: list[str] = Field(default_factory=list)
    requirements_id: str | None = None
    rq_version: int | None = None
    rq_ref: RqRef | None = Field(None, description="제안서 딸깍(10-proposal §8.8 C2) 호환 — requirements_id 와 같음")
    extra_text: str | None = Field(None, max_length=4000)
    mi_bundle: dict[str, Any] | None = Field(None, description="MI `bundle?target=competitor` 응답(웹이 읽어 넣음)")
    mi_ref: MiRef | None = None
    project_id: str | None = None
    purpose: str | None = Field(None, description="proposal(제안서 딸깍)")
    auto_run: bool = False
    customer: Any = Field(None, description="제안서 딸깍 호환: 고객사 이름 또는 {name}")
    customer_name: str | None = None


class AnalysisPatch(M):
    text: str | None = Field(None, max_length=8000)
    extra_text: str | None = Field(None, max_length=4000)
    file_ids: list[str] | None = None
    requirements_id: str | None = None
    rq_version: int | None = None
    input_mode: InputMode | None = None
    anonymize: bool | None = None
    last_screen: str | None = Field(None, max_length=40)
    title: str | None = Field(None, max_length=40)


class FindLine(M):
    n: int
    text: str
    state: Literal["done", "active", "wait"]


class FindProgress(M):
    lines: list[FindLine] = Field(default_factory=list)
    candidates_so_far: int = 0
    eta_label: str = "약 30초"
    error: str | None = None


class AskRead(M):
    key: str
    label: str
    value: str
    partial: bool = False


class AskRequest(M):
    kind: str = "slots"
    missing: list[str] = Field(default_factory=list)
    read: list[AskRead] = Field(default_factory=list)
    industry: dict[str, Any] = Field(default_factory=dict)
    default: dict[str, Any] = Field(default_factory=dict)
    title: str = ""
    desc: str = ""


class RunCompetitor(M):
    id: str
    letter: str
    display: str = ""
    state: Literal["wait", "run", "done", "partial"] = "wait"
    done_facts: list[str] = Field(default_factory=list)
    current_fact: str | None = None
    text: str = Field("", description="CA3 문장(`경쟁사 A — 제품 · 솔루션 · 레퍼런스 완료, 가격대 찾는 중`)")


class RunProgress(M):
    competitors: list[RunCompetitor] = Field(default_factory=list)
    criteria: dict[str, int] = Field(default_factory=dict)
    pct: int = 0
    eta_s: int | None = None
    eta_label: str = ""
    mode: str = "full"
    title: str = ""


class StoppedInfo(M):
    done: int = 0
    total: int = 0
    text: str = ""


class Analysis(M):
    id: str
    title: str = ""
    input_mode: InputMode = "free"
    input_label: str = ""
    text: str = ""
    extra_text: str = ""
    file_ids: list[str] = Field(default_factory=list)
    requirements_id: str | None = None
    rq_version: int | None = None
    mi_ref: MiRef | None = None
    project_id: str | None = None
    purpose: str | None = None
    customer_name: str | None = None
    slots: SlotsView
    found_count: int = 0
    segment: SegmentView = Field(default_factory=SegmentView)
    chips: list[ChipView] = Field(default_factory=list)
    rfp: RfpView = Field(default_factory=RfpView)
    include_names: list[str] = Field(default_factory=list)
    exclude_names: list[str] = Field(default_factory=list)
    anonymize: bool = True
    naming_mode: str = "letter"
    status: Status = "draft"
    status_label: str = ""
    version: int = 0
    current_job_id: str | None = None
    current_job_kind: str | None = None
    last_screen: str | None = None
    route: str = ""
    competitor_count: int = 0
    on_count: int = 0
    analyzed_count: int = 0
    criteria_mode: Literal["auto", "pin"] = "auto"
    ask: AskRequest | None = None
    find: FindProgress = Field(default_factory=FindProgress)
    run: RunProgress | None = None
    stopped: StoppedInfo | None = None
    needs_rejudge: bool = False
    owner_name: str = ""
    created_at: str = ""
    updated_at: str = ""
    analyzed_at: str | None = None
    next_recheck_at: str | None = None
    letters_on: list[str] = Field(default_factory=list, description="켜진 경쟁사 글자(CA5 익명 표기 `경쟁사 A · B · C · D`)")
    added_refs: list[str] = Field(default_factory=list, description="셸 `현재 작업에 추가`로 넣은 참조(kb:model:… · kb:solution:… · kb:case:…) — 셸 `added`")


class ListAction(M):
    label: str
    route: str
    kind: Literal["result", "continue", "detail"] = "continue"


class ListItem(M):
    id: str
    title: str
    sub: str = Field(description="`{소유자} · {시점}`")
    owner_name: str = ""
    time_label: str = ""
    input_mode: InputMode = "free"
    input_label: str = ""
    count: int | None = None
    count_label: str = Field("—", description="숫자 또는 `—`")
    count_unit: str = Field("", description="`곳` · `후보`(회색)")
    status: Status
    status_label: str = Field(description="`완료` · `확인 중` · `업데이트 필요`")
    status_tone: Literal["done", "check", "upd"] = "check"
    note: str = ""
    sent_label: str | None = Field(None, description="`MI 작업 · 제안서` 처럼. 없으면 null(`아직 없음`)")
    action: ListAction
    route: str
    updated_at: str = ""
    current_job_id: str | None = None


class ListCounts(M):
    all: int = 0
    done: int = 0
    check: int = 0
    upd: int = 0


class ListBanner(M):
    n: int
    title: str = Field(description="`{n}건은 다시 분석을 권해요.`")
    text: str = Field(description="`경쟁사 {글자} 가 {YYYY.MM} 신제품을 냈어요 — {작업 제목} · 분석 30일 경과`")
    target_id: str
    competitor_ids: list[str] = Field(default_factory=list)


class AnalysisList(M):
    items: list[ListItem]
    next_cursor: str | None = None
    counts: ListCounts
    banner: ListBanner | None = None
    header: str = ""


# ── 후보 ─────────────────────────────────────────────────
class CompetitorView(M):
    id: str
    letter: str
    display: str = Field(description="`경쟁사 {글자}`")
    real_name: str = Field("", description="실명(작업 화면 안에서만 보조 글자로)")
    aliases: list[str] = Field(default_factory=list)
    kind_label: str = ""
    why: str = ""
    chips: list[str] = Field(default_factory=list)
    confidence: float | None = None
    confidence_label: str = ""
    status: CandStatus
    status_label: str
    on: bool
    pinned: bool = False
    removed: bool = False
    origin: str = "auto"
    rank: int = 0
    add_state: Literal["pending", "done", "failed"] | None = None
    switch_label: str = Field("", description="`경쟁사 {글자} 빼기` / `경쟁사 {글자} 넣기`")


class CandidateCounts(M):
    rec: int = 0
    check: int = 0
    drop: int = 0
    user: int = 0
    on: int = 0


class CandidatesOut(M):
    items: list[CompetitorView]
    counts: CandidateCounts
    read_count: int = 0
    total: int = 0
    page_size: int = 6
    finding: bool = False
    chips: list[ChipView] = Field(default_factory=list)
    slots: SlotsView | None = None
    header: HeaderView = Field(default_factory=HeaderView)
    job_id: str | None = None


class CandidatePatch(M):
    on: bool


class CandidateAdd(M):
    name: str = Field(min_length=1, max_length=80)


class CandidateAddOut(M):
    job_id: str
    competitor_id: str
    status: str = "queued"


# ── 기준 ─────────────────────────────────────────────────
class CriterionView(M):
    id: str
    name: str
    source: CritSource
    source_label: str = Field("", description="`요구` · `업종 사례 {n}건` · `기본` · `직접 추가`")
    source_count: int | None = None
    importance: int = 3
    order: int = 0
    enabled: bool = True
    pinned: bool = False
    requirement_ref: str | None = None


class CriteriaSummary(M):
    total: int = 0
    requirements: int = 0
    industry_cases: int = 0
    default: int = 0
    user: int = 0


class Suggestion(M):
    name: str
    n: int = 0


class CriteriaOut(M):
    items: list[CriterionView]
    summary: CriteriaSummary
    mode: Literal["auto", "pin"] = "auto"
    suggestions: list[Suggestion] = Field(default_factory=list)
    on: int = 0
    total: int = 0
    summary_text: str = Field("", description="`요구사항에서 3 · 업종 사례에서 1 · 기본 2`")


class CriterionIn(M):
    id: str | None = None
    name: str = Field(min_length=1, max_length=20)
    source: CritSource = "user"
    source_count: int | None = None
    importance: int = Field(3, ge=1, le=5)
    order: int = 0
    enabled: bool = True


class CriteriaPut(M):
    items: list[CriterionIn]


class CriteriaPutOut(CriteriaOut):
    job_id: str | None = None


# ── 실행 ─────────────────────────────────────────────────
class RunIn(M):
    mode: RunMode = "full"
    competitor_ids: list[str] | None = None


class ProgressOut(M):
    status: Status
    job_id: str | None = None
    job_kind: str | None = None
    job_status: str | None = None
    find: FindProgress = Field(default_factory=FindProgress)
    run: RunProgress | None = None
    ask: AskRequest | None = None


# ── 결과 ─────────────────────────────────────────────────
class FooterView(M):
    sources: int = 0
    public: int = 0
    kb_case: int = 0
    unverified: bool = False
    text: str = ""


class ResultRow(M):
    id: str
    letter: str
    display: str
    real_name: str = ""
    kind: str = ""
    positioning: str = ""
    up: int = 0
    eq: int = 0
    dn: int = 0
    unknown: int = 0
    sources: int = 0
    state: Literal["done", "partial", "run", "wait", "skipped"] = "done"
    state_label: str = ""


class StrengthView(M):
    title: str
    note: str
    criterion_ids: list[str] = Field(default_factory=list)
    criterion_names: list[str] = Field(default_factory=list)
    competitor_ids: list[str] = Field(default_factory=list)
    competitor_letters: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    sources_label: str = ""


class CautionView(M):
    competitor_id: str
    letter: str
    display: str
    note: str
    criterion_ids: list[str] = Field(default_factory=list)
    criterion_names: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    sources_label: str = ""


class TableCriterion(M):
    id: str
    name: str
    importance: int = 3
    source: str = ""


class TableColumn(M):
    id: str
    label: str
    letter: str | None = None
    real_name: str | None = None
    samsung: bool = False


class TableCell(M):
    text: str
    verdict: Verdict | None = None
    claim_ids: list[str] = Field(default_factory=list)
    source_ns: list[int] = Field(default_factory=list)
    tbd: bool = False


class TableView(M):
    criteria: list[TableCriterion]
    columns: list[TableColumn]
    cells: list[list[TableCell]]


class PartialInfo(M):
    analyzing: bool = False
    stopped: bool = False
    done: int = 0
    total: int = 0
    text: str = ""


class ResultOut(M):
    version: int = 0
    status: Status
    view: Literal["overview", "table", "strengths"] = "overview"
    header: HeaderView = Field(default_factory=HeaderView)
    competitors: list[ResultRow]
    strengths: list[StrengthView] = Field(default_factory=list)
    cautions: list[CautionView] = Field(default_factory=list)
    chips: list[ChipView] = Field(default_factory=list)
    footer: FooterView = Field(default_factory=FooterView)
    table: TableView | None = None
    partial: PartialInfo = Field(default_factory=PartialInfo)
    can_send: bool = False
    criteria_count: int = 0


class FactView(M):
    key: FactKey
    label: str
    text: str
    tbd: bool = False
    sources: int = 0
    has_kb: bool = False
    sources_label: str = ""
    check: bool = Field(False, description="칩 `확인 필요`(모르는 값 · 확인 안 된 값)")
    claim_ids: list[str] = Field(default_factory=list)


class VsSamsung(M):
    better: list[str] = Field(default_factory=list)
    similar: list[str] = Field(default_factory=list)
    worse: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)


class DetailHeader(M):
    id: str
    letter: str
    display: str
    real_name: str = ""
    kind: str = ""
    aliases: list[str] = Field(default_factory=list)


class OtherCompetitor(M):
    id: str
    letter: str
    current: bool = False


class ResearchState(M):
    job_id: str | None = None
    running: bool = False
    eta_label: str = ""


class CompetitorDetail(M):
    version: int = 0
    header: DetailHeader
    positioning: str = ""
    facts: list[FactView]
    vs_samsung: VsSamsung = Field(default_factory=VsSamsung)
    vs_labels: list[ChipView] = Field(default_factory=list, description="`우위 3 · 통합 관리 · 전력 · 배포` 칩(0 인 칩은 뺌)")
    footer: FooterView = Field(default_factory=FooterView)
    others: list[OtherCompetitor] = Field(default_factory=list)
    research: ResearchState = Field(default_factory=ResearchState)
    state: str = "done"


class ResearchIn(M):
    facts: list[FactKey] | None = None


# ── 주장 · 출처 ──────────────────────────────────────────
class CitationRef(M):
    n: int
    source_id: str
    status: str


class ClaimItem(M):
    id: str
    text: str
    status: str
    label: str
    competitor_id: str | None = None
    fact_key: str | None = None
    criterion_id: str | None = None
    block: str = ""
    citations: list[CitationRef] = Field(default_factory=list)


class ClaimCounts(M):
    total: int = 0
    matched: int = 0
    needs_check: int = 0
    public: int = 0
    kb_case: int = 0


class ClaimList(M):
    items: list[ClaimItem]
    counts: ClaimCounts = Field(default_factory=ClaimCounts)


class SourceCard(M):
    source_id: str
    n: int = 0
    kind: str
    kind_label: str
    status: str
    status_label: str = Field(description="`원문 일치` 또는 `확인 필요`")
    title: str = ""
    meta: str = ""
    quote: str = ""
    highlight: str | None = None
    reason: str = ""
    url: str | None = None
    actions: list[str] = Field(default_factory=list)
    footnote: str = ""


class ClaimDetail(M):
    claim: ClaimItem
    cards: list[SourceCard]


class SourceOut(M):
    id: str
    kind: str
    kind_label: str
    subtype: str = ""
    title: str = ""
    publisher: str = ""
    url: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
    state: str = "used"
    competitor_id: str | None = None
    fact_key: str | None = None
    mode: str = ""
    query: str | None = None


class SourceList(M):
    items: list[SourceOut]


class SnapshotOut(M):
    text: str
    pages: list[str] | None = None


class SourceAddIn(M):
    url: str | None = Field(None, max_length=2000)
    file_id: str | None = None
    claim_id: str | None = None
    competitor_id: str | None = None
    fact_key: FactKey | None = None
    classification: Literal["internal", "confidential", "customer", "public"] | None = None


class SourceAddOut(M):
    job_id: str
    source_id: str | None = None
    status: str = "queued"


# ── 넘김 · 내보내기 ──────────────────────────────────────
class HandoffConfirm(M):
    real_names: bool | None = None


class HandoffIn(M):
    target: HandoffTarget
    target_id: str | None = None
    target_title: str | None = None
    confirm: HandoffConfirm | None = None
    dry_run: bool = False


class HandoffOut(M):
    handoff_id: str | None = None
    target: HandoffTarget
    status: str = "prepared"
    named: bool = False
    anonymization_map: dict[str, str] = Field(default_factory=dict)
    letters: list[str] = Field(default_factory=list)


class HandoffPatch(M):
    status: Literal["prepared", "delivered", "failed"]
    target_id: str | None = None
    target_title: str | None = None


class HandoffView(M):
    id: str
    analysis_id: str
    version: int = 0
    target: HandoffTarget
    target_id: str | None = None
    target_title: str | None = None
    status: str
    confirmations: dict[str, Any] = Field(default_factory=dict)
    anonymization_map: dict[str, str] = Field(default_factory=dict)
    served_named_at: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class HandoffList(M):
    items: list[HandoffView]


class Bundle(M):
    """넘김 묶음(§6.10). target 마다 채우는 필드가 다르다 — mi(실명 포함) · proposal_why(익명) · storyboard(익명)."""
    target: str
    analysis_id: str
    version: int = 0
    handoff_id: str | None = None
    named: bool = False
    title: str = ""
    customer: dict[str, Any] | None = None
    segment: dict[str, Any] | None = None
    slots: dict[str, Any] | None = None
    competitors: list[Any] = Field(default_factory=list)
    criteria: list[dict[str, Any]] = Field(default_factory=list)
    facts: dict[str, Any] | None = None
    positioning: dict[str, Any] | None = None
    samsung_cells: dict[str, Any] | None = None
    verdicts: list[dict[str, Any]] | None = None
    strengths: list[dict[str, Any]] | None = None
    cautions: list[dict[str, Any]] | None = None
    claims: list[dict[str, Any]] | None = None
    citations: list[dict[str, Any]] | None = None
    sources: list[dict[str, Any]] | None = None
    comparison: dict[str, Any] | None = None
    footnotes: list[dict[str, Any]] | None = None
    fact_check: list[dict[str, Any]] | None = None
    note: str | None = None


class PHSource(M):
    feature: str = "CA"
    ref_id: str
    version: int
    title: str
    updated_at: str
    route: str


class PHTarget(M):
    proposal_type: Literal["standard", "quickwin", "solution"] = "standard"
    section_key: str = "why"


class PHItemSource(M):
    kind: str
    ref: str
    label: str
    url: str | None = None
    tier: str | None = None


class PHItem(M):
    key: str
    label: str
    from_label: str | None = None
    sheet_role: str
    sheet_title: str | None = None
    template_hint: dict[str, str] | None = None
    status: Literal["ok", "warn", "add"] = "ok"
    status_label: str = ""
    include_default: bool = True
    content: dict[str, Any] = Field(default_factory=dict)
    sources: list[PHItemSource] = Field(default_factory=list)


class PHFact(M):
    key: str
    label: str
    value: str | None = None
    unit: str | None = None
    status: Literal["confirmed", "unconfirmed", "placeholder"]
    placeholder: str | None = None
    source: dict[str, Any] | None = None


class ProposalHandoff(M):
    source: PHSource
    target: PHTarget
    customer: dict[str, Any] | None = None
    rq_ref: RqRef | None = None
    items: list[PHItem]
    facts: list[PHFact] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
    live_link: bool = False
    named: bool = False


class ExportIn(M):
    format: Literal["pdf"] = "pdf"
    audience: Literal["internal", "customer"] = "internal"


# ── 재확인 ───────────────────────────────────────────────
class ChangeView(M):
    id: str
    kind: Literal["competitor_new_product", "source_changed"]
    competitor_id: str | None = None
    letter: str | None = None
    title: str = Field(description="`경쟁사 {글자} 신제품 발표` 처럼(실명 없음)")
    summary: str = ""
    product: str | None = None
    date: str | None = None
    detected_at: str = ""
    verification: Literal["matched", "needs_check"] = "needs_check"


class ChangesOut(M):
    items: list[ChangeView]
    summary: str = ""
    checked_at: str | None = None


# ── 셸 추가 ──────────────────────────────────────────────
class AdditionsIn(M):
    kind: Literal["product", "solution", "case", "image"]
    ids: list[str] = Field(min_length=1, max_length=20)


class AdditionsOut(M):
    added: list[str]


# ── 버전 ─────────────────────────────────────────────────
class VersionSummary(M):
    n: int
    kind: str
    created_at: str = ""
    summary: str = ""
    stopped: bool = False
    current: bool = False


class VersionList(M):
    items: list[VersionSummary]


# ── 규칙 · 능력 ──────────────────────────────────────────
class RoutingRule(M):
    signal: str
    decision: str
    mode: Literal["auto", "check", "ask", "pin"]
    mode_label: str


class RoutingStage(M):
    no: str
    title: str
    sub: str
    rules: list[RoutingRule]


class LadderRow(M):
    signal: str
    how: str
    n: str
    tag: str
    o: str
    desc: str
    width: int


class AskRow(M):
    n: int
    t: str
    where: str
    default: str = ""


class RoutingRules(M):
    header: HeaderView
    legend: list[ChipView]
    stages: list[RoutingStage]
    ladder_title: str
    ladder_sub: str
    ladder_example: str
    ladder: list[LadderRow]
    asks_title: str
    asks: list[AskRow]
    asks_footer: str
    thresholds: dict[str, float] = Field(default_factory=dict)
    ask_requires_ambiguous_industry: bool = True


class Capabilities(M):
    mode: str = "summary_only"
    websearch_available: bool = True
    returns_sources: bool = False
    search_api: str = "none"
    fetch: bool = False
