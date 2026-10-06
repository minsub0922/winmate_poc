"""spec API 모델(06-spec §5.2 · §5.3 · §6). 여기 모양이 contracts/spec.json 이 된다."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

UiStatus = Literal["draft", "run", "check", "warn", "done"]
Start = Literal["model", "explorer", "find", "requirements", "clone", "link"]
Kind = Literal["single", "compare", "req"]
Locale = Literal["ko", "en", "ko_en"]
Role = Literal["proposed", "existing", "alternative"]
CellState = Literal["ok", "checking", "flag", "pending", "sync_pending", "edited", "derived"]
Verdict = Literal["pass", "fail", "unknown"]
WarningKind = Literal["discontinued", "not_in_catalog", "value_mismatch_source", "value_mismatch_proposal",
                      "requirement_unmet", "catalog_changed"]
ExportFormat = Literal["xlsx", "pdf", "pptx"]
OriginFrom = Literal["home", "mi", "vp", "birdseye", "product_detail", "proposal", "clone"]


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
    sheet_id: str | None = None


class FormatSettings(_M):
    formats: list[ExportFormat] = Field(default_factory=lambda: ["xlsx"], min_length=1, description="최소 1")
    language: Locale = "ko"
    length_unit: Literal["mm", "inch", "both"] = "mm"
    weight_unit: Literal["kg", "lb", "both"] = "kg"
    paper: Literal["a4_landscape", "a4_portrait", "letter"] = "a4_landscape"
    number_format: Literal["1,234.5", "1.234,5"] = "1,234.5"
    filename_base: str | None = Field(None, description="null = 규칙 기본값(§4.16.6)")


class FormatSettingsPatch(_M):
    formats: list[ExportFormat] | None = Field(None, min_length=1)
    language: Locale | None = None
    length_unit: Literal["mm", "inch", "both"] | None = None
    weight_unit: Literal["kg", "lb", "both"] | None = None
    paper: Literal["a4_landscape", "a4_portrait", "letter"] | None = None
    number_format: Literal["1,234.5", "1.234,5"] | None = None
    filename_base: str | None = None


class CatalogLabel(_M):
    label: str = "사내 카탈로그"
    source_label: str = "사내 제품 카탈로그"
    version: str = ""


class Origin(_M):
    from_: OriginFrom | None = Field(None, alias="from")
    ref: str | None = None
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class TargetProposal(_M):
    id: str
    title: str
    type: Literal["standard", "quickwin", "solution"] = "standard"
    section_no: str = "08"
    subtitle: str | None = None


class Successor(_M):
    model_code: str
    display_name: str
    relation: str


class Lifecycle(_M):
    status: Literal["on_sale", "discontinued", "eol_planned", "unknown"] = "unknown"
    source: str = ""
    as_of: str | None = None
    successor: Successor | None = None
    sold_out: bool = False


class Product(_M):
    id: str
    ref: str
    model_code: str | None = None
    kb_model_id: str | None = None
    family_id: str | None = None
    display_name: str
    bubble_label: str = Field(description="'Smart Signage QM55C' — 계열명이 없으면 표시명")
    family_label_en: str | None = None
    series_code: str | None = None
    size_inch: int | None = None
    role: Role = "proposed"
    column_label: str | None = None
    custom: bool = False
    source: str = "input"
    lifecycle: Lifecycle = Field(default_factory=Lifecycle)
    warning_ns: list[int] = Field(default_factory=list, description="열 머리 경고 번호(단종 · 카탈로그 없음)")


class SheetItem(_M):
    key: str
    label: str
    checked: bool
    prechecked_by: Literal["default", "requirement", "user"] = "default"


class Options(_M):
    highlight_wins: bool = True


class Source(_M):
    kind: Literal["catalog", "datasheet", "policy_doc", "user", "derived"]
    label: str
    version_or_date: str = ""
    tier: str = ""
    ref: str = ""
    page: int | None = None
    quote: str | None = None


class CellPart(_M):
    label: str
    num: float | None = None
    unit: str | None = None
    text: str | None = None


class CellValue(_M):
    num: float | None = None
    num2: float | None = None
    unit: str | None = None
    parts: list[CellPart] | None = None


class Cell(_M):
    product_id: str
    text: str
    text_en: str | None = None
    value: CellValue | None = None
    state: CellState
    win: bool = False
    converted: bool = False
    original_text: str | None = None
    sources: list[Source] = Field(default_factory=list)
    warning_ns: list[int] = Field(default_factory=list)
    check_n: int | None = None
    flag_text: str | None = Field(None, description="SP3G 미리보기 flag 칸 글(`값 없음` · `출처 {n}곳 다름`)")


class Memo(_M):
    text: str
    mode: Literal["footnote", "internal"] = "footnote"


class RowLine(_M):
    """시트 언어로 그린 줄(영문 · 한/영에서 `화면 크기 · 해상도` · `밝기 · 명암비` 는 두 줄)."""
    label: str
    texts: list[str]
    converted: list[bool] = Field(default_factory=list)
    pending: list[bool] = Field(default_factory=list)


class Row(_M):
    id: str
    item_key: str | None = None
    row_key: str
    label: str
    label_en: str | None = None
    ord: int
    hidden: bool = False
    highlighted: bool = False
    memo: Memo | None = None
    added_by: Literal["items", "edit", "request", "template"] = "items"
    footnote_mark: str | None = None
    win: bool = False
    cells: list[Cell] = Field(default_factory=list)
    lines: list[RowLine] = Field(default_factory=list)


class Footnote(_M):
    mark: str
    text: str


class SheetTable(_M):
    title: str
    title_en: str
    rows: list[Row]
    footnotes: list[Footnote] = Field(default_factory=list)
    source_line: str
    win_rows: int = 0
    visible_rows: int = 0
    total_rows: int = 0
    hidden_rows: int = 0


class CheckOption(_M):
    key: str
    label: str
    value_text: str
    tier: str = ""
    source_ref: str = ""
    preselected: bool = False


class AltMeasure(_M):
    label: str
    value_text: str
    footnote: str


class CheckAnswer(_M):
    option_key: str | None = None
    value_text: str | None = None
    datasheet_id: str | None = None
    alt_measure: str | None = None


class ValueCheck(_M):
    id: str
    n: int
    kind: Literal["missing", "conflict", "missing_product"]
    title: str
    body: str
    row_id: str | None = None
    product_id: str
    unit: str | None = None
    input_label: str | None = None
    placeholder: str | None = None
    options: list[CheckOption] = Field(default_factory=list)
    alt_measures: list[AltMeasure] = Field(default_factory=list)
    status: Literal["open", "answered", "deferred"] = "open"
    answer: CheckAnswer | None = None


class Checks(_M):
    open: int = 0
    items: list[ValueCheck] = Field(default_factory=list)


class Replacement(_M):
    label: str
    relation_text: str
    already_in_sheet: bool = False
    model_code: str | None = None


class WarningOption(_M):
    key: str
    label: str
    kind: Literal["radio", "chip", "button"]
    navigates_to: Literal["SP1C", "SP4", "SP1R"] | None = None


class WarningDecision(_M):
    option_key: str
    at: str


class Warning(_M):
    id: str
    n: int
    kind: WarningKind
    tag: str
    title: str
    body: str
    row_id: str | None = None
    product_id: str | None = None
    link_id: str | None = None
    replacement: Replacement | None = None
    options: list[WarningOption] = Field(default_factory=list)
    decision: WarningDecision | None = None
    default_option: str | None = None
    status: Literal["open", "decided", "applied", "dismissed"] = "open"


class WarningCounts(_M):
    all: int = 0
    discontinued: int = 0
    mismatch: int = 0
    unmet: int = 0


class Warnings(_M):
    open: int = 0
    counts: WarningCounts = Field(default_factory=WarningCounts)
    items: list[Warning] = Field(default_factory=list)


class ComplianceDoc(_M):
    id: str
    name: str
    format: str
    pages: int = 0
    recognized: int = 0
    file_id: str | None = None
    status: str = "done"
    note: str | None = None


class Alternative(_M):
    product_ref: str
    label: str
    model_code: str | None = None


class ComplianceRow(_M):
    id: str
    item: str
    requirement: str
    value_text: str
    verdict: Verdict
    note: str | None = None
    page: int | None = None
    quote: str = ""
    kind: str = "text"
    doc_id: str | None = None
    alternative: Alternative | None = None
    overridden: bool = False


class ComplianceCounts(_M):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    pass_: int = Field(0, alias="pass")
    fail: int = 0
    unknown: int = 0


class ComplianceInclude(_M):
    table: bool = True
    spec: bool = True
    page_refs: bool = True
    alternative: bool = False


class Compliance(_M):
    docs: list[ComplianceDoc] = Field(default_factory=list)
    target_product_id: str | None = None
    target_label: str | None = None
    counts: ComplianceCounts = Field(default_factory=ComplianceCounts)
    rows: list[ComplianceRow] = Field(default_factory=list)
    include: ComplianceInclude = Field(default_factory=ComplianceInclude)
    alternative_label: str | None = None
    agent_text: str | None = None
    folded_line: str | None = Field(None, description="처음 8행 밖 요약 `4개 더 · 충족 3 · 확인 필요 1`")
    customer: str | None = None
    place: str | None = None
    note: str | None = None
    status: Literal["empty", "running", "done", "failed"] = "empty"
    error: str | None = None
    picked_by_finder: bool = False


class FinderConditions(_M):
    sizes: list[Literal["43", "50", "55", "65", "75+"]] = Field(default_factory=list)
    brightness: Literal["any", "desc", "outdoor"] = "any"
    usage: list[Literal["menu_board", "wayfinding", "monitoring", "meeting"]] = Field(default_factory=list)
    install: list[Literal["wall", "stand", "ceiling", "portrait"]] = Field(default_factory=list)
    required: list[str] = Field(default_factory=list, description="continuous_operation · wall · magicinfo · size · stand · …")
    off: list[str] = Field(default_factory=list, description="사용자가 끈 칩(문장 해석이 다시 켜지 않음) — 'size:55' · 'usage:monitoring' …")


class FinderExtra(_M):
    id: str
    label: str
    kind: Literal["filter", "sort"]
    key: str | None = None
    op: str | None = None
    value: float | str | None = None
    capability_id: str | None = None


class FinderCondRow(_M):
    key: str
    label: str
    value_text: str
    state: Literal["ok", "check", "no"]


class FinderCandidate(_M):
    ref: str
    model_code: str
    display_name: str
    series_label: str
    size_inch: int | None = None
    out: bool = False
    ok: int = 0
    total: int = 0
    rows: list[FinderCondRow] = Field(default_factory=list)
    c2_score: float = 0
    selected: bool = False
    brightness_nit: float | None = None
    operation: str | None = None
    power_text: str | None = None
    weight_text: str | None = None
    out_reason: str | None = None


class FinderState(_M):
    query_text: str | None = None
    conditions: FinderConditions = Field(default_factory=FinderConditions)
    extra: list[FinderExtra] = Field(default_factory=list)
    candidates: list[FinderCandidate] = Field(default_factory=list)
    hide_out: bool = False
    view: Literal["cards", "table"] = "cards"
    catalog_version: str = ""
    total_candidates: int = 0
    agent_text: str | None = None
    sort_label: str | None = None
    customer: str | None = None
    place: str | None = None
    status: Literal["idle", "running", "done", "failed"] = "idle"
    error: str | None = None
    selected: list[str] = Field(default_factory=list, description="고른 후보 ref(카드에서 사라져도 유지)")


class TemplateInfo(_M):
    id: str
    name: str
    status: str
    file_id: str | None = None
    format: str | None = None


class LinkInfo(_M):
    id: str
    proposal_id: str
    proposal_title: str
    section_no: str
    section_name: str
    sent_version: int
    status: Literal["in_sync", "sheet_changed"]


class ActiveJob(_M):
    id: str
    kind: str
    status: str
    progress: int = 0


class DatasheetInfo(_M):
    id: str
    product_id: str
    file_id: str
    name: str
    pages: int = 0
    status: str = "queued"


class SheetDoc(_M):
    id: str
    version: int
    title: str
    title_confirmed: bool
    suggested_title: str
    customer_name: str | None = None
    project_id: str | None = None
    start: Start
    kind: Kind
    layout: Literal["compare", "per_product"] = "compare"
    step: Literal[1, 2, 3]
    ui_status: UiStatus
    status_text: str
    resume_route: str
    catalog: CatalogLabel
    origin: Origin | None = None
    target_proposal: TargetProposal | None = None
    products: list[Product]
    items: list[SheetItem]
    options: Options
    format: FormatSettings
    format_confirmed: bool
    format_draft: FormatSettingsPatch | None = Field(None, description="말로 요청한 형식(SP2L 이 미리 고른 값, 저장 전)")
    table: SheetTable | None = None
    checks: Checks
    warnings: Warnings
    compliance: Compliance | None = None
    finder: FinderState | None = None
    template: TemplateInfo | None = None
    datasheets: list[DatasheetInfo] = Field(default_factory=list)
    links: list[LinkInfo] = Field(default_factory=list)
    generated_at: str | None = None
    saved_at: str | None = None
    updated_at: str
    created_at: str | None = None
    archived_at: str | None = None
    active_job: ActiveJob | None = None
    last_job_id: str | None = None
    last_error: str | None = Field(None, description="마지막 생성 잡 실패 원인(SP3G `시트를 만들지 못했어요. {원인}`)")
    owner_name: str | None = None
    product_limit: int = 8
    agent: dict[str, str | None] = Field(default_factory=dict, description="화면 에이전트 문장(sp2 · sp3 · sp3g · from_note …)")


# ── 목록 ─────────────────────────────────────────────────

class SheetListItem(_M):
    id: str
    title: str
    type_icon: Literal["compare", "single", "req", "find"]
    sub_line: str
    model_chips: list[str]
    more_models: int = 0
    output_label: str
    ui_status: UiStatus
    status_text: str
    proposal_label: str
    when_label: str
    resume_route: str
    updated_at: str


class TabCounts(_M):
    all: int = 0
    draft: int = 0
    check: int = 0
    done: int = 0


class Banner(_M):
    date: str
    sheets: int
    text: str
    route: str | None = None


class SheetList(_M):
    items: list[SheetListItem]
    next_cursor: str | None = None
    counts: TabCounts
    archived_count: int = 0
    total: int = 0
    banner: Banner | None = None


# ── 요청 본문 ─────────────────────────────────────────────

class CreateSheet(_M):
    start: Start = "model"
    products: list[str] | None = Field(None, description="ref · 모델코드 · mdl_ · fam_")
    models: list[str] | None = Field(None, description="products 와 같음(proposal P2 호환)")
    query_text: str | None = None
    project_id: str | None = None
    customer_name: str | None = None
    origin: Origin | None = None
    target_proposal: TargetProposal | None = None
    rq_ref: dict[str, Any] | None = Field(None, description="{rq_id, version} — 요구사항 정의서 연결(선택)")
    purpose: Literal["proposal"] | None = Field(None, description="proposal 딸깍: 기본 항목 + 생성(auto_answer)까지 바로 시작")
    role: Role | None = None


class PatchSheet(_M):
    title: str | None = None
    customer_name: str | None = None
    step: Literal[1, 2] | None = None
    target_proposal: TargetProposal | None = None
    clear_target_proposal: bool = False
    confirm_title: bool = False


class CloneBody(_M):
    customer_name: str | None = None


class VersionItem(_M):
    version: int
    reason: str
    created_at: str


class VersionList(_M):
    items: list[VersionItem]


class AddProducts(_M):
    refs: list[str]
    source: Literal["input", "explorer", "link", "request", "find", "requirements"] | None = None
    role: Role | None = None


class SkippedRef(_M):
    ref: str
    reason: Literal["duplicate", "limit", "unresolved"]


class AddProductsResult(_M):
    added: list[str]
    skipped: list[SkippedRef] = Field(default_factory=list)
    sheet: SheetDoc


class PatchProduct(_M):
    role: Role | None = None
    column_label: str | None = None
    ord: int | None = None
    model_ref: str | None = None


class ProductRefItem(_M):
    ref: str
    model_code: str | None = None
    kb_model_id: str | None = None
    family_id: str | None = None
    display_name: str
    role: Role


class ProductRefList(_M):
    items: list[ProductRefItem]


class Combo(_M):
    label: str
    model_codes: list[str]
    refs: list[str] = Field(default_factory=list)


class ComboList(_M):
    items: list[Combo]


class FinderPut(_M):
    conditions: FinderConditions | None = None
    extra: list[FinderExtra] | None = None
    hide_out: bool | None = None
    view: Literal["cards", "table"] | None = None
    selected: list[str] | None = None
    preset: str | None = Field(None, description="다른 화면에서 올 때 조건 미리 채우기: 'row:{srq}'(대안 보기) · 'alternatives'(대안 모델 찾기) · "
                                                 "'warning:{swn}'(다른 후보 찾기)")


class FinderParse(_M):
    text: str = Field(min_length=1)


class FinderCommit(_M):
    selected: list[str]
    to: Literal["items", "products"] = "items"


class RequirementDocBody(_M):
    file_id: str
    note: str | None = None


class CompliancePatch(_M):
    target_product_id: str | None = None
    target_ref: str | None = Field(None, description="시트에 없는 모델을 대응 모델로(제품으로 추가)")
    include: dict[str, bool] | None = None


class ComplianceRowPatch(_M):
    verdict_override: Verdict | None = None
    note: str | None = None


class AskDraft(_M):
    text: str
    mailto: str
    count: int = 0


class PageQuote(_M):
    row_id: str
    text: str
    bbox: list[float] | None = None


class PageView(_M):
    page: int
    image_file_id: str | None = None
    image_url: str | None = None
    text: str = ""
    quotes: list[PageQuote] = Field(default_factory=list)


class CatalogItem(_M):
    key: str
    label: str
    label_en_lines: list[str]
    default_checked: bool
    group: str
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ItemCatalog(_M):
    category: str
    items: list[CatalogItem]


class ItemsPut(_M):
    items: list[dict[str, Any]] | None = Field(None, description="[{key, checked}]")
    layout: Literal["compare", "per_product"] | None = None
    language: Locale | None = None
    highlight_wins: bool | None = None


class DiffItems(_M):
    different: list[str]


class FormatPreviewBody(FormatSettings):
    tab: ExportFormat = "xlsx"


class GridCell(_M):
    text: str
    converted: bool = False
    kind: Literal["title", "head", "cell", "label"] = "cell"
    win: bool = False
    pending: bool = False


class GridRow(_M):
    n: int
    cells: list[GridCell]


class Grid(_M):
    cols: list[str]
    rows: list[GridRow]


class FormatPreview(_M):
    grid: Grid
    sheet_tabs: list[str]
    converted_cells: int
    note_line: str | None = None
    filename_default: str
    ext_line: str
    chip_label: str
    tab_labels: dict[str, str]
    title: str
    footnotes: list[Footnote] = Field(default_factory=list)
    source_line: str = ""


class TemplateBody(_M):
    file_id: str


class Preferences(_M):
    format: FormatSettings
    highlight_wins: bool = True
    is_custom: bool = False


class GenerateBody(_M):
    mode: Literal["full", "rerender", "columns"] = "full"
    product_ids: list[str] | None = None
    auto_answer: bool = False


class CheckList(_M):
    items: list[ValueCheck]
    open: int


class CheckAnswerBody(_M):
    option_key: str | None = None
    value_text: str | None = None
    alt_measure: str | None = None


class ApplyAnswer(_M):
    check_id: str
    option_key: str | None = None
    value_text: str | None = None
    alt_measure: str | None = None


class ChecksApply(_M):
    answers: list[ApplyAnswer] = Field(default_factory=list)


class ChecksApplyResult(_M):
    sheet: SheetDoc
    next_route: str
    pending_until_job_done: bool = False


class DatasheetBody(_M):
    file_id: str
    product_id: str


class SourceList(_M):
    sources: list[Source]


class CellPatch(_M):
    value_text: str


class CellPatchResult(_M):
    cell: Cell
    win_rows: int


class MessageBody(_M):
    text: str = Field(min_length=1)
    context: Literal["generating", "result", "warnings", "export", "find", "requirements"] = "result"


class MessageQueued(_M):
    queued: bool = True
    job_id: str | None = None
    memo: bool = Field(False, description="true = 생성 중이라 조종 메모로 들어감(job_id = 생성 잡)")


class ExportOptions(_M):
    drop_hidden: bool = True
    memo_footnotes: bool = True
    keep_pending_marks: bool = True


class ExportBody(_M):
    format: ExportFormat
    overrides: FormatSettingsPatch | None = None
    options: ExportOptions | None = None
    filename: str | None = None


class ExportAccepted(_M):
    job_id: str
    status: Literal["queued"] = "queued"
    export_id: str


class ExportRecord(_M):
    id: str
    status: Literal["queued", "running", "done", "failed"]
    format: ExportFormat
    filename: str
    file_id: str | None = None
    download_url: str | None = None
    job_id: str | None = None
    error: str | None = None
    warnings: list[str] = Field(default_factory=list)
    slide_count: int | None = None


class ShareResult(_M):
    share_url: str


# ── 편집 세션 ─────────────────────────────────────────────

class EditOp(_M):
    op: Literal["move_row", "hide_row", "show_row", "highlight_row", "unhighlight_row", "set_memo", "delete_memo",
                "add_rows", "remove_row", "move_column"]
    row_id: str | None = None
    to_index: int | None = None
    text: str | None = None
    mode: Literal["footnote", "internal"] | None = None
    item_key: str | None = None
    row_keys: list[str] | None = None
    product_id: str | None = None


class EditOps(_M):
    ops: list[EditOp]


class EditRow(Row):
    tags: list[str] = Field(default_factory=list)
    moved: int = 0


class EditSummary(_M):
    total: int = 0
    move: int = 0
    highlight: int = 0
    memo: int = 0
    hide: int = 0
    add: int = 0
    remove: int = 0
    column: int = 0


class HistoryItem(_M):
    n: int
    text: str


class AddableRow(_M):
    row_key: str
    label: str
    item_key: str


class MissingItem(_M):
    key: str
    label: str


class EditColumn(_M):
    product_id: str
    label: str
    role: Role


class EditView(_M):
    session_id: str
    base_version: int
    current_version: int
    stale: bool = False
    title: str
    columns: list[EditColumn]
    rows: list[EditRow]
    hidden_count: int
    visible: int
    total: int
    missing_items: list[MissingItem]
    addable_rows: list[AddableRow]
    summary: EditSummary
    summary_text: str
    can_undo: bool
    can_redo: bool
    history: list[HistoryItem]
    status: Literal["open", "committed", "discarded"] = "open"


class EditSessionCreated(_M):
    id: str
    base_version: int
    view: EditView


class CommitBody(_M):
    rebase: bool = False


class EditMessage(_M):
    text: str = Field(min_length=1)


# ── 경고 ─────────────────────────────────────────────────

class WarningsView(_M):
    items: list[Warning]
    counts: WarningCounts
    decided: int
    total: int
    agent_text: str
    table_title: str
    footer: str
    user_text: str | None = None


class WarningPatch(_M):
    option_key: str


class CatalogStatus(_M):
    adapter: str
    label: str
    source_label: str
    version: str
    detected_at: str | None = None
    previous_version: str | None = None
    changed_sheets: int = 0


class LifecycleEntry(_M):
    model_key: str
    status: Literal["on_sale", "discontinued", "eol_planned", "unknown"]
    successor_model_code: str | None = None
    source_label: str = "사내 제품 카탈로그"
    as_of: str | None = None
    note: str | None = None


class LifecycleList(_M):
    items: list[LifecycleEntry]


class LifecycleCheckBody(_M):
    model_codes: list[str]
    locale: Locale = "ko"


class LifecycleSuccessor(_M):
    model_code: str
    display_name: str | None = None
    reason: str
    spec_diff_summary: str | None = None


class LifecycleCheckItem(_M):
    model_code: str
    display_name: str | None = None
    status: Literal["on_sale", "discontinued", "unknown"]
    successors: list[LifecycleSuccessor] = Field(default_factory=list)
    evidence: str


class LifecycleCheckResult(_M):
    items: list[LifecycleCheckItem]


# ── 넘김 · 연결 ───────────────────────────────────────────

class HandoffBody(_M):
    proposal_id: str | None = None
    proposal_type: Literal["standard", "quickwin", "solution"] = "standard"
    proposal_title: str | None = None
    section_no: str | None = None
    templates: list[Literal["SC-A", "SC-B", "SD-A"]] = Field(default_factory=lambda: ["SC-A"])
    mode: Literal["replace", "add"] = "replace"
    options: ExportOptions | None = None
    overrides: FormatSettingsPatch | None = None
    replace_proposal_sheet_ids: list[str] | None = None


class PackageSheet(_M):
    template: Literal["SC-A", "SC-B", "SD-A", "SD-B"]
    data: dict[str, Any]


class FactCheck(_M):
    sheet_index: int
    text: str
    placeholder: Literal["[확정 필요]"] = "[확정 필요]"
    reason: str


class Carry(_M):
    visible_rows: int = 0
    hidden_rows_dropped: int = 0
    win_cells: int = 0
    footnote_memos: int = 0
    pending_cells: int = 0


class Package(_M):
    sheet_id: str
    sheet_version: int
    title: str
    locale: Locale
    customer_name: str | None = None
    catalog: dict[str, str]
    sheets: list[PackageSheet]
    fact_check: list[FactCheck]
    carry: Carry
    mode: Literal["replace", "add"] = "replace"
    replace_proposal_sheet_ids: list[str] | None = None
    link_back: dict[str, str]
    lines: list[str] = Field(default_factory=list, description="SP4 넘어가는 것 4줄")


class HandoffCreated(_M):
    id: str
    status: Literal["ready", "acked", "failed"]
    open_route: str
    package: Package


class Handoff(_M):
    id: str
    sheet_id: str
    sheet_version: int
    proposal_id: str | None = None
    proposal_type: str | None = None
    templates: list[str]
    mode: str
    package: Package
    status: Literal["ready", "acked", "failed"]
    ack: dict[str, Any] | None = None
    created_at: str


class HandoffAck(_M):
    result: Literal["applied", "failed"]
    proposal_id: str | None = None
    proposal_title: str | None = None
    section_no: str | None = None
    section_name: str | None = None
    proposal_sheet_ids: list[str] = Field(default_factory=list)


class DiffCell(_M):
    row_label: str
    product_label: str
    sent_text: str
    current_text: str


class LinkItem(_M):
    link_id: str
    sheet_id: str
    sheet_title: str
    proposal_id: str
    sent_version: int
    current_version: int
    status: Literal["in_sync", "sheet_changed"]
    diff_cells: list[DiffCell]
    route: str


class LinkList(_M):
    items: list[LinkItem]


class LinksReleased(_M):
    """`DELETE /v1/links?proposal_id=`(internal) — 제안서를 지웠을 때 그 제안서와의 연결을 거둔 결과."""
    proposal_id: str
    deleted: int
    sheet_ids: list[str] = Field(default_factory=list)


# ── ProposalHandoff v1 (10-proposal §8.0 · P1) ────────────

class PHSource(_M):
    feature: str
    ref_id: str
    version: int
    title: str
    updated_at: str
    route: str


class PHTarget(_M):
    proposal_type: str
    section_key: str


class PHItem(_M):
    key: str
    label: str
    from_label: str | None = None
    sheet_role: str
    sheet_title: str | None = None
    template_hint: dict[str, str] | None = None
    status: Literal["ok", "warn", "add"]
    status_label: str
    include_default: bool
    repeat_key: dict[str, str] | None = None
    content: dict[str, Any]
    sources: list[dict[str, Any]]


class PHFact(_M):
    key: str
    label: str
    value: str | None = None
    unit: str | None = None
    status: Literal["confirmed", "unconfirmed", "placeholder"]
    placeholder: str | None = None
    source: dict[str, Any] | None = None


class ProposalHandoff(_M):
    source: PHSource
    target: PHTarget
    customer: dict[str, Any] | None = None
    rq_ref: dict[str, Any] | None = None
    items: list[PHItem]
    facts: list[PHFact] = Field(default_factory=list)
    live_link: bool = True
