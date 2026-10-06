"""API 요청 · 응답 모델 — contracts/proposal.json 의 원천(10-proposal.md §5 · §6).

규칙
- 응답의 화면 문구(…_label · intro · header)는 서버가 계산한 원문 그대로다(웹은 그대로 그린다).
- 라우트(route)는 웹 기능 경로 `/proposal/...` 기준.
- 시각은 ISO 8601 UTC 문자열.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ProposalType = Literal["standard", "quickwin", "solution"]
StartMode = Literal["blank", "rfp", "works", "reuse", "handoff"]
Stage = Literal["customer", "type", "compose", "industry", "sections", "design", "result"]
SectionKey = Literal["mi", "bigMi", "vp", "birdseye", "spaceProducts", "solution", "cases", "why", "spec", "spaceScenario"]


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore")


# ── 공통 ───────────────────────────────────────────────────
class JobAccepted(_M):
    job_id: str
    status: str = "queued"
    kind: str = Field(description="잡 종류(proposal.section_fill 등)")
    proposal_id: str | None = None
    import_id: str | None = None
    export_id: str | None = None
    reuse_id: str | None = None
    section_key: str | None = None
    sheet_id: str | None = None


class Ok(_M):
    ok: bool = True


class RouteRef(_M):
    label: str
    route: str


class Owner(_M):
    user_id: str
    name: str
    initial: str = ""


# ── 제안서(§5.1) ───────────────────────────────────────────
class Customer(_M):
    name: str = ""
    industry_code: str | None = Field(None, description="16업종 코드(부록 C, 예 FB)")
    industry_label: str | None = None
    kr_vertical_id: str | None = None
    scale_text: str | None = None
    decision_makers: str | None = Field(None, description="「고객 측 의사결정자 · 청중」")
    industry_user_set: bool = Field(False, description="사용자가 업종 칩을 직접 고름(고정)")


class CustomerIn(_M):
    name: str | None = None
    industry_code: str | None = None
    industry_label: str | None = None
    industry_chip: str | None = Field(None, description="PR1 업종 칩(「리테일 · F&B」 등). 주면 묶음 안 1위 업종으로")
    scale_text: str | None = None
    decision_makers: str | None = None


class Presentation(_M):
    date: str | None = None
    duration_min: int | None = None
    label: str | None = Field(None, description="「2026-10-22 · 발표 20분」")


class Schedule(_M):
    submit_due: str | None = Field(None, description="제안 제출일 YYYY-MM-DD(PR0 마감)")
    presentation: Presentation | None = None


class RqRef(_M):
    rq_id: str
    version: int | None = None


class IndustryDetected(_M):
    code: str
    label: str
    score: float | None = None
    mode: Literal["auto", "check", "ask", "pinned"] = "auto"
    evidence: list[str] = Field(default_factory=list)


class IndustryLayout(_M):
    decided: bool = False
    industry_code: str | None = None
    detected: IndustryDetected | None = None
    families: dict[str, Literal["on", "off"]] = Field(default_factory=lambda: {"MI": "on", "VP": "on", "SS": "on"})
    cards: dict[str, str] = Field(default_factory=dict, description="카드 코드 → applied|alt")
    applied_codes: list[str] = Field(default_factory=list)


class CoverImageRef(_M):
    kind: str = Field(description="file · kb_image · image_job")
    id: str
    file_id: str | None = None
    label: str | None = None


class Cover(_M):
    enabled: bool = True
    image_ref: CoverImageRef | None = None


class Design(_M):
    master_id: str = "samsung_b2b"
    master_name: str = "삼성 B2B 표준"
    logo_file_id: str | None = None
    brand_hex: str | None = None
    color_candidates: list[str] = Field(default_factory=lambda: ["#1428A0", "#121417"])
    cover: Cover = Field(default_factory=Cover)
    page_numbers: bool = True
    appendix: bool = False
    section_dividers: bool = True
    layout_mode: Literal["auto", "manual"] = "auto"
    chosen: bool = Field(False, description="사용자가 PR6 에서 고른 적 있음(딸깍 「디자인 템플릿」 행)")


class DerivedFrom(_M):
    kind: Literal["proposal", "file"]
    proposal_id: str | None = None
    version: int | None = None
    file_ids: list[str] = Field(default_factory=list)
    reuse_id: str | None = None
    label: str | None = Field(None, description="「2025 제안서 v4에서 파생」")


class ReuseRef(_M):
    reuse_id: str
    mode: Literal["improve", "borrow"] | None = None


class OneClickBrief(_M):
    job_id: str
    status: str
    pct: int = 0
    auto_from_step: int = 4
    route: str


class ReviewBrief(_M):
    review_id: str
    version: int
    requested_at: str | None = None
    due_date: str | None = None
    reviewers_total: int = 0
    approvals: int = 0
    changes_requested: int = 0
    my_turn_user_ids: list[str] = Field(default_factory=list)
    status: str = "pending"


class Files(_M):
    pptx_file_id: str | None = None
    pdf_file_id: str | None = None


class Stepper(_M):
    steps: list[str]
    current: int = Field(description="1–6")
    complete: bool = False
    one_click: bool = Field(description="딸깍 버튼 표시(1–5단계 · 딸깍 실행 중 아님)")
    auto_from: int = Field(0, description="딸깍이 채운 첫 단계(검은 번개 아이콘), 0 = 없음")
    done_steps: list[int] = Field(default_factory=list)


class SectionSummary(_M):
    id: str
    key: str
    name: str
    short: str
    no: int
    optional: bool
    enabled: bool
    hidden: bool = False
    status: str
    status_label: str
    confirmed: bool
    inferred: bool
    sheet_count: int
    route: str


class SheetSummary(_M):
    id: str
    section_key: str
    sheet_no: int
    title: str
    role: str
    role_name: str
    template_code: str | None = None
    template_mode: str = "auto"
    tag: str = Field(description="「자동 · MS-B」 또는 「MS-C · 직접」")
    status: str
    status_label: str
    inferred: bool = False
    edited_since_version: bool = False
    open_confirm: int = 0
    thumb_url: str | None = None


class Proposal(_M):
    id: str
    project_id: str | None = None
    owner: Owner
    title: str
    title_display: str = Field(description="빈 제목이면 「새 제안서」")
    customer: Customer
    schedule: Schedule
    budget_text: str | None = None
    language: Literal["ko", "en"] = "ko"
    rq_ref: RqRef | None = None
    start_mode: str
    start_files: list[str] = Field(default_factory=list)
    type: ProposalType | None = None
    type_label: str | None = None
    type_name: str | None = None
    type_source: str | None = None
    stage: str
    stage_no: int
    current_section_key: str | None = None
    industry_layout: IndustryLayout
    design: Design
    status: Literal["draft", "review", "done"]
    status_label: str
    submitted_at: str | None = None
    version: int = Field(0, description="저장된 최신 버전 번호(첫 PPTX 생성 전 0)")
    rev: int = Field(description="자동 저장 리비전 — If-Match 로 보낸다")
    edits_since_version: int = 0
    files: Files = Field(default_factory=Files)
    derived_from: DerivedFrom | None = None
    reuse: ReuseRef | None = None
    one_click: OneClickBrief | None = None
    review: ReviewBrief | None = None
    progress_label: str
    steps_done: int
    route: str = Field(description="지금 단계 화면(「이어서 작성」)")
    stepper: Stepper
    sections: list[SectionSummary] = Field(default_factory=list)
    sheets: list[SheetSummary] = Field(default_factory=list)
    sheet_total: int = 0
    slides_total: int = 0
    open_confirm_count: int = 0
    link_count: int = 0
    created_at: str
    updated_at: str


class ProposalAction(_M):
    label: str = Field(description="검토 보기 · 버전 보기 · 확인할 곳 · 이어서 작성 · 복제해서 시작")
    route: str


class RowBadge(_M):
    kind: Literal["comments", "source_updated", "confirm_needed"]
    label: str
    n: int = 0


class ProposalRow(_M):
    id: str
    title: str
    short_title: str | None = None
    customer_name: str = ""
    industry_label: str = ""
    type: ProposalType | None = None
    type_label: str | None = None
    status: Literal["draft", "review", "done"]
    status_label: str
    sub_label: str = Field("", description="「의료 · 요양 · PPTX v2」")
    subtitle: str = Field("", description="sub_label 과 같다(Spec SP4 · 이미지 IMG4 목록용)")
    meta: str = Field("", description="「표준 제안서 · 작성 중」(IMG4 보낼 제안서)")
    badge: RowBadge | None = None
    steps_done: int
    current_step: int
    progress_label: str
    due_date: str | None = None
    due_label: str = ""
    d_day_label: str = ""
    urgent: bool = False
    owner: Owner
    action: ProposalAction
    project_id: str | None = None
    version: int = 0
    one_click_running: bool = False
    updated_at: str
    route: str


class ProposalCounts(_M):
    all: int = 0
    draft: int = 0
    review: int = 0
    done: int = 0


class ProposalList(_M):
    items: list[ProposalRow]
    next_cursor: str | None = None
    counts: ProposalCounts
    total: int
    due_within_14d: int
    my_review_turn: int
    summary_label: str = Field(description="「전체 6건 · 2주 안에 마감 3건 · 내 검토 차례 1건」")
    range_label: str = Field("", description="「1–6 / 6」")


class LinkIn(_M):
    feature: str = Field(description="기능(서비스 이름 mi · storyboard … 또는 코드 MI · SB …, kb_product · kb_solution · kb_case · kb_image · file)")
    ref_id: str
    section_key: str | None = None
    version: int | None = None
    handoff_id: str | None = Field(None, description="넘김 기록 id(mi hof_ · spec sho_)")
    title: str | None = None


class ProposalCreate(_M):
    start_mode: StartMode = "blank"
    title: str | None = None
    customer: CustomerIn | None = None
    project_id: str | None = None
    links: list[LinkIn] = Field(default_factory=list)
    source_proposal_id: str | None = Field(None, description="복제해서 시작(PR1C 원본)")
    rq_ref: RqRef | None = None
    schedule: Schedule | None = None
    language: Literal["ko", "en"] | None = None
    image_version: str | None = Field(None, description="IMG4 「새 제안서로 시작」 이미지 버전(imv_…)")


class ProposalPatch(_M):
    title: str | None = None
    customer: CustomerIn | None = None
    schedule: Schedule | None = None
    budget_text: str | None = None
    language: Literal["ko", "en"] | None = None
    stage: Stage | None = None
    current_section_key: str | None = None
    project_id: str | None = None
    rq_ref: RqRef | None = None


class MarkSubmitted(_M):
    submitted_at: str | None = None


# ── 시작 방식(§6.3) ────────────────────────────────────────
class RfpStart(_M):
    file_ids: list[str] = Field(min_length=1)
    extra_file_ids: list[str] = Field(default_factory=list, description="회의록")


class RfpSource(_M):
    file_id: str | None = None
    page: int | None = None
    page_label: str | None = None
    quote: str | None = None


class RfpField(_M):
    no: int
    key: str
    label: str
    value: str = ""
    source: RfpSource | None = None
    source_label: str = Field("—", description="「p.11」, 없으면 「—」")
    state: Literal["found", "guess", "empty"]
    state_label: str
    edited: bool = False


class RfpExcerptPart(_M):
    text: str
    field_no: int | None = None


class RfpExcerpt(_M):
    page: int | None = None
    page_label: str
    parts: list[RfpExcerptPart]


class Phase(_M):
    key: str
    label: str
    status: Literal["done", "busy", "todo"]


class RfpFile(_M):
    file_id: str
    name: str
    kind_label: str = Field("", description="「PDF · 24쪽 · 방금 올림」")
    pages: int | None = None


class RfpTally(_M):
    found: int = 0
    guess: int = 0
    empty: int = 0


class RfpView(_M):
    status: Literal["none", "running", "done", "failed"]
    job_id: str | None = None
    error: dict[str, Any] | None = None
    files: list[RfpFile] = Field(default_factory=list)
    extra_files: list[RfpFile] = Field(default_factory=list)
    phases: list[Phase] = Field(default_factory=list)
    excerpts: list[RfpExcerpt] = Field(default_factory=list)
    fields: list[RfpField] = Field(default_factory=list)
    tally: RfpTally = Field(default_factory=RfpTally)
    found_count: int = 0
    intro: str = ""
    rq_count: int = 0
    rq_label: str = ""
    rq_ref: RqRef | None = None
    confirmed: bool = False


class RfpFieldPut(_M):
    value: str


class RelatedWork(_M):
    feature: str
    ref_id: str
    title: str
    tool_label: str
    meta: str = ""
    updated_at: str | None = None
    version: int | None = None
    target_sections: list[str] = Field(default_factory=list)
    target_label: str = ""
    default_on: bool = False
    on: bool = False
    customer_match: bool = True
    route: str | None = None


class FillPreviewSection(_M):
    key: str
    name: str
    state: Literal["full", "partial", "new"]
    state_label: str
    source_label: str


class RecommendedType(_M):
    type: ProposalType
    name: str
    reason: str


class FillCounts(_M):
    full: int = 0
    partial: int = 0
    new: int = 0


class CustomerFrom(_M):
    feature: str
    label: str


class FillPreview(_M):
    customer_from: CustomerFrom | None = None
    customer_summary: str = ""
    recommended_type: RecommendedType
    sections: list[FillPreviewSection]
    counts: FillCounts
    counts_label: str = Field("", description="「채움 3 · 일부 3 · 새로 작성 2」")


class RelatedWorks(_M):
    scope: Literal["customer", "all"]
    customer_name: str = ""
    works: list[RelatedWork]
    work_count: int
    on_count: int
    header_label: str = Field("", description="「연결할 작업 4 / 6」")
    intro: str = ""
    footer_label: str = ""
    preview: FillPreview


class LinkToggle(_M):
    feature: str
    ref_id: str
    on: bool
    section_key: str | None = None


class LinksPut(_M):
    links: list[LinkToggle]


class LinkedSource(_M):
    id: str
    section_key: str | None = None
    feature: str
    feature_label: str
    ref_id: str
    title: str
    label: str = Field(description="칩 이름(「MI · A 커피 시장·경쟁사 분석」)")
    version_at_link: int | None = None
    latest_version: int | None = None
    stale: bool = False
    via: str
    status: Literal["candidate", "linked", "removed"] = "linked"
    route: str | None = None
    created_at: str


class LinksOut(_M):
    links: list[LinkedSource]
    preview: FillPreview | None = None
    on_count: int = 0


class LinkRemoved(_M):
    link_id: str
    section_key: str | None = None
    toast: str = "연결 해제됨"


# ── 유형 · 구성 · 업종(§6.4) ───────────────────────────────
class TypeSectionChip(_M):
    no: int
    key: str
    label: str
    optional: bool


class TypeOption(_M):
    type: ProposalType
    name: str
    desc: str
    rec: bool
    selected: bool = False
    sections: list[TypeSectionChip]
    section_count: int
    footnote: str = Field(description="「섹션 8 · 넣을 시트는 다음 단계에서 골라요」")
    route: str


class TypeOptions(_M):
    recommended: RecommendedType
    customer_line: str = Field(description="「A 커피 프랜차이즈 · 전국 매장 디지털 메뉴보드 전환 · 리테일/F&B · 320개 매장」")
    intro: str
    header_label: str = "제안서 유형 · 하나 선택 · 2 / 6"
    selected: ProposalType | None = None
    types: list[TypeOption]
    footer_note: str = "유형은 섹션 작성 중에도 바꿀 수 있고, 이미 작성한 섹션은 유지됩니다."


class TypePut(_M):
    type: ProposalType


class CompChip(_M):
    code: str
    name: str
    repeat: int = 1


class CompType(_M):
    code: str
    name: str
    msg: str
    state: Literal["on", "rec", "off"]
    meta: str
    src_label: str
    template_count: int | None = None
    dedicated: bool = False
    repeat: int = 1
    user_set: bool = False


class CompSection(_M):
    no: int
    no_label: str
    key: str
    name: str
    optional: bool
    enabled: bool
    tag: str = Field(description="「필수」 · 「선택」")
    switch_label: str | None = Field(None, description="선택 섹션 스위치 aria 「{{섹션}} 섹션 사용」")
    chips: list[CompChip]
    more: int
    more_label: str = ""
    types: list[CompType]
    sheet_count: int
    open: bool = False


class NextStep(_M):
    target: Literal["industry", "sections", "compose", "type", "design", "result"]
    route: str
    label: str = ""


class Composition(_M):
    type: ProposalType
    type_name: str
    intro: str
    header_label: str = Field(description="「시트 구성 · 표준 제안서 · 섹션 8 · 시트 24 · 3 / 6」")
    sections: list[CompSection]
    section_count: int
    sheet_total: int
    open_key: str | None = None
    footer_note: str = "시트 수는 따로 정하지 않아요. 공간 · 사례처럼 반복되는 시트는 연결된 항목 수만큼 생깁니다."
    next: NextStep


class CompTypeToggle(_M):
    code: str
    on: bool


class CompSectionPut(_M):
    key: str
    enabled: bool | None = None
    types: list[CompTypeToggle] = Field(default_factory=list)


class CompositionPut(_M):
    sections: list[CompSectionPut]


class StartSections(_M):
    """「섹션 작성 시작」 결과"""
    next: NextStep
    proposal: Proposal


class IndustryOption(_M):
    code: str
    label: str


class StatRow(_M):
    label: str
    n: int
    of: int


class IndustryStats(_M):
    cases: int = 0
    needs: list[StatRow] = Field(default_factory=list)
    products: list[StatRow] = Field(default_factory=list)
    solutions: list[StatRow] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list, description="3열 머리 「고객이 요구한 것 · 사례 23건 중」 …")


class FamilyMap(_M):
    text: str
    strong: bool = False


class FamilyCard(_M):
    code: str
    variant: str
    name: str
    desc: str = ""
    thumb_url: str
    state: Literal["applied", "alt", "add"]
    state_label: str
    available: bool = True


class IndustryFamily(_M):
    role: Literal["MI", "VP", "SS"]
    name: str
    on: bool
    available: bool = True
    switch_label: str
    maps: list[FamilyMap]
    cards: list[FamilyCard]
    pick_route: str | None = Field(None, description="「시트별로 바꾸기」 → 대표 시트 템플릿 고르기")


class IndustryDetectedView(_M):
    code: str | None = None
    label: str = ""
    mode: Literal["auto", "check", "ask", "pinned"] = "auto"
    mode_label: str = ""
    score: float | None = None
    evidence: list[str] = Field(default_factory=list)
    evidence_label: str = ""


class IndustryView(_M):
    detected: IndustryDetectedView
    options: list[IndustryOption]
    stats: IndustryStats
    families: list[IndustryFamily]
    applied_count: int
    header_label: str
    intro: str
    ask: bool = Field(False, description="선택 필요 — 업종 바꾸기 목록을 연 채로 시작")
    can_apply: bool = True
    decided: bool = False
    footer_note: str = "업종 레이아웃은 섹션 작성의 템플릿 고르기 맨 앞에도 나와요."
    next: NextStep | None = None


class IndustryPut(_M):
    code: str | None = None
    families: dict[str, bool] = Field(default_factory=dict, description="{MI, VP, SS}: 켬/끔")
    cards: dict[str, Literal["applied", "alt"]] = Field(default_factory=dict)
    decided: bool = True
    keep_default: bool = Field(False, description="「기본 템플릿 유지」 — 세 계열 끔 · 결정함 · PR3")


# ── 섹션 · 시트 · 값(§6.5) ─────────────────────────────────
class RailItem(_M):
    key: str
    label: str
    count: int
    done: bool
    optional: bool
    current: bool
    enabled: bool = True
    title: str | None = Field(None, description="선택 섹션 title 「{{이름}} (선택 섹션)」")
    route: str


class SourceChip(_M):
    id: str
    feature: str
    feature_label: str
    label: str
    stale: bool = False
    route: str | None = None
    ref: str | None = Field(None, description="셸 참조(「kb:model:mdl_…」 · 「kb:case:…」 · 「img:image:img_…」 · 「ws:item:<id>」) — 팝오버 「✓ 추가됨」 표시용")


class SheetFrom(_M):
    service: str
    sheet_id: str | None = None
    ref_id: str | None = None


class TemplateState(_M):
    code: str | None = None
    mode: Literal["auto", "pinned"] = "auto"
    source: str | None = Field(None, description="industry · dedicated · data_shape · message · user · import")
    recommended_code: str | None = None
    reason: str | None = None
    product_count: int | None = None
    name: str | None = None
    tag: str = ""
    locked_manual: bool = Field(False, description="PR6 「시트마다 직접」 — 자동 재추천 끔")


class SectionSheet(_M):
    id: str
    sheet_no: int
    title: str
    role: str
    role_name: str
    thumb_url: str | None = None
    tag: str
    template: str | None = Field(None, description="템플릿 코드(SP4 알림용)")
    template_info: TemplateState
    status: str
    status_label: str
    inferred: bool = False
    evidence_note: str | None = None
    open_confirm: int = 0
    solution_code: str | None = None
    group_label: str | None = Field(None, description="솔루션 그룹(「MagicINFO」 · 「통합」)")
    from_: SheetFrom | None = Field(None, alias="from", serialization_alias="from")
    edited_since_version: bool = False

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Accepts(_M):
    sidebar: list[str] = Field(description="받는 사이드바 기능(서비스 이름)")
    items: list[Literal["product", "solution", "image", "case"]]


class DropHint(_M):
    idle: str = "여기에 끌어 놓기"
    sidebar: list[str] = Field(default_factory=list, description="사이드바 작업 드래그 중 두 줄")
    item: list[str] = Field(default_factory=list, description="팝업 항목 드래그 중 두 줄(「{{항목}}」 자리 표시)")


class SectionView(_M):
    proposal_id: str
    type: ProposalType
    type_name: str
    key: str
    name: str
    short: str
    no: int
    total: int
    section_no: int
    rail: list[RailItem]
    total_sheets: int
    intro: str
    sources: list[SourceChip]
    empty_sources_label: str = "아직 연결된 자료가 없어요 — 아래 영역에 끌어다 놓으세요"
    sheets: list[SectionSheet]
    sheet_label: str
    header_label: str = Field(description="「Market Intelligence · 섹션 1 / 8 · 시트 3」")
    accepts: Accepts
    accept_chips: list[str]
    drop_hint: DropHint
    quick_actions: list[str]
    placeholder: str
    request_label: str = "섹션 수정 요청"
    prev: RouteRef
    next: RouteRef
    status: Literal["empty", "filling", "ready", "stale"]
    status_label: str
    fill_job_id: str | None = None
    optional: bool = False
    enabled: bool = True
    confirmed: bool = False
    inferred: bool = False
    owner_name: str = ""
    reuse_view: Literal["compare", "guide"] | None = None
    needs_fill: bool = Field(False, description="진입 시 :fill 을 불러야 함(연결 자료가 있고 초안이 없거나 stale)")


class SectionConfirmResult(_M):
    next: RouteRef
    proposal: Proposal


class TemplatesAuto(_M):
    include_pinned: bool = True


class SheetSourceRef(_M):
    kind: str
    ref: str | None = None
    label: str
    tier: str | None = None
    url: str | None = None
    page: int | None = None


class ReuseLine(_M):
    line_id: str
    source_line_id: str | None = None
    mark: Literal["keep", "update", "new", "drop"]


class SheetReuse(_M):
    source_page: int | None = None
    verdict: Literal["keep", "update", "rewrite", "new", "drop", "auto"]
    flow_role: str | None = None
    lines: list[ReuseLine] = Field(default_factory=list)
    note: str = ""


class SheetRender(_M):
    png_file_id: str | None = None
    url: str | None = None
    rev: int | None = None
    status: str | None = None


class ConfirmBrief(_M):
    id: str
    tag: str
    text: str
    status: str


class FactBrief(_M):
    id: str
    key: str
    label: str
    display: str
    status: str


class Sheet(_M):
    id: str
    proposal_id: str
    section_key: str
    section_name: str
    order: int
    sheet_no: int
    role: str
    role_name: str
    msg: str = ""
    solution_code: str | None = None
    repeat_key: dict[str, Any] | None = None
    title: str
    template: TemplateState
    content: dict[str, Any] = Field(description="SheetContent(§5.3.1) — eyebrow · title · subtitle · slots · notes · footnotes. 값 토큰 {{fact:id}} 포함")
    display: dict[str, Any] = Field(default_factory=dict, description="값 토큰을 표시 문자열로 바꾼 content(미리보기 · 편집 표시용)")
    sources: list[SheetSourceRef] = Field(default_factory=list)
    status: str
    status_label: str
    origin: str = "user"
    inferred: bool = False
    evidence_note: str | None = None
    reuse: SheetReuse | None = None
    split_of: str | None = None
    edited_since_version: bool = False
    render: SheetRender | None = None
    thumb_url: str | None = None
    confirm_items: list[ConfirmBrief] = Field(default_factory=list)
    confirm_label: str = Field("", description="「이 시트에 확정 필요 1곳 · …」")
    facts: list[FactBrief] = Field(default_factory=list)
    slot_schema: dict[str, Any] | None = Field(None, description="export 템플릿 칸 정의(slots[] — id · type · box · capacity · fields)")
    updated_at: str
    rev: int


class SheetOp(_M):
    op: Literal["set", "insert", "delete", "move"]
    path: str = Field(description="content 안 JSON pointer(예 /slots/table/rows/5/cells/1/text, /title)")
    value: Any = None
    from_path: str | None = Field(None, alias="from", description="move 의 출발 경로")

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class SheetPatch(_M):
    ops: list[SheetOp] = Field(min_length=1)
    reason: str | None = None


class SheetPatchResult(_M):
    sheet: Sheet
    change_ids: list[str]
    rev: int
    resolved_item_ids: list[str] = Field(default_factory=list)
    edits_since_version: int = 0


class TemplateVariant(_M):
    code: str
    name: str
    when: str
    thumb_url: str
    kind: Literal["industry", "dedicated", "industry_solution", "generic", "product"]
    tag: str | None = Field(None, description="「자동」 · 「추천」 · 「직접」")
    selected: bool = False
    available: bool = True


class TemplateSheetInfo(_M):
    id: str
    title: str
    role: str
    role_name: str
    msg: str


class TemplateOptions(_M):
    sheet: TemplateSheetInfo
    header_label: str = Field(description="「시장 규모 · 성장 · “이 시장은 크고, 커지고 있다”를 보여줄 템플릿 5종」")
    sheet_label: str = Field("", description="「시트 2」 또는 「MagicINFO 시트 3 · 섹션 전체 7」")
    mode: Literal["auto", "pinned"]
    current_code: str | None = None
    recommended: dict[str, str | None]
    reason_line: str = Field(description="「MS-B 추천 · …」")
    variants: list[TemplateVariant]
    product_count: int | None = None
    products: list[str] = Field(default_factory=list)
    products_label: str = ""
    split_note: str | None = None
    pinned_in_section: int = 0
    auto_all_confirm: str | None = Field(None, description="「직접 고른 {{n}}장도 자동으로 바꿔요」")


class TemplatePut(_M):
    mode: Literal["auto", "pinned"]
    code: str | None = None
    product_count: int | None = Field(None, description="공간 제품 소개 시트만 1–5")


class TemplateApplyResult(_M):
    sheets: list[Sheet]
    split: bool = False


class RewriteOptions(_M):
    same_template: bool = True
    concise: bool = False
    emphasize_numbers: bool = False


class SheetRewrite(_M):
    target_path: str | None = None
    instruction: str | None = None
    options: RewriteOptions = Field(default_factory=RewriteOptions)


class Message(_M):
    id: str
    scope: Literal["proposal", "section", "sheet", "comment"]
    scope_ref: str | None = None
    role: Literal["user", "w"]
    text: str
    change_ids: list[str] = Field(default_factory=list)
    job_id: str | None = None
    created_at: str


class MessageList(_M):
    items: list[Message]


class FactUse(_M):
    sheet_id: str
    sheet_no: int | None = None
    path: str


class FactEvidence(_M):
    kind: Literal["url", "file", "work", "internal_doc", "customer", "user"]
    ref: str | None = None
    note: str | None = None


class Fact(_M):
    id: str
    key: str
    label: str
    value: str | None = None
    unit: str | None = None
    kind: Literal["input", "derived"] = "input"
    formula: str | None = None
    formula_label: str | None = Field(None, description="「합계 = 매장 수 × 3대」")
    status: Literal["placeholder", "unconfirmed", "confirmed"]
    placeholder: str
    display: str
    evidence: FactEvidence | None = None
    origin: dict[str, Any] = Field(default_factory=dict)
    used_in: list[FactUse] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)


class FactList(_M):
    items: list[Fact]


class FactPut(_M):
    value: str | None = None
    unit: str | None = None
    evidence: FactEvidence | None = None


class FactUpdateResult(_M):
    fact: Fact
    changed_sheet_ids: list[str]
    change_ids: list[str]


class TextRequest(_M):
    text: str = Field(min_length=1)


class SectionFill(_M):
    reason: Literal["enter", "sources_changed", "regen"] = "enter"
    quick_action: str | None = None


class NotesGenerate(_M):
    only_empty: bool = True


# ── 반입(§6.6) ─────────────────────────────────────────────
class ImportSource(_M):
    feature: str | None = Field(None, description="사이드바 작업 · 보내기: 기능(mi · storyboard … 또는 MI · SB …)")
    ref_id: str | None = None
    version: int | None = None
    handoff_id: str | None = None
    title: str | None = None
    kind: Literal["product", "solution", "image", "case"] | None = Field(None, description="팝업 항목 종류")
    ref: dict[str, Any] | str | None = Field(None, description="{kb_kind, id} · {file_id} · {image_job_id} 또는 id 문자열")
    label: str | None = None
    sub: str | None = None
    service: str | None = Field(None, description="IMG4: 'image'")
    image_id: str | None = None
    version_id: str | None = None


class ImportTarget(_M):
    sheet_id: str | None = None
    mode: Literal["replace_slot", "new_sheet"] | None = None


class ImportRequest(_M):
    section_key: str | None = Field(None, description="없으면 유형별 기본 섹션(§10.7)")
    via: Literal["drag_sidebar", "drag_item", "button", "handoff"] = "drag_item"
    source: ImportSource
    target_sheet_id: str | None = None
    slot: str | None = None
    include_keys: list[str] | None = Field(None, description="보내기 화면에서 고른 항목 키(handoff)")
    target: ImportTarget | None = None
    caption: str | None = None


class SourceChipOut(_M):
    id: str
    label: str
    feature: str


class ImportItem(_M):
    key: str
    what: str
    from_label: str | None = None
    sheet_role: str
    role_name: str = ""
    target_sheet_id: str | None = None
    template_code: str | None = None
    template_name: str | None = None
    in_section: bool
    checked: bool
    status: str | None = None
    status_label: str | None = None
    line_label: str = Field(description="「→ 시장 규모 · 성장 · 성장 추이 템플릿」 / 「이 섹션엔 없는 시트 · 사용자 분석 시트로 추가 가능」")
    section_key: str | None = Field(None, description="이 항목이 들어갈 섹션(보내기에서 역할이 다른 섹션에 있으면 그 섹션, 없으면 반입 섹션)")


class Import(_M):
    id: str
    proposal_id: str
    section_key: str
    via: str
    source: dict[str, Any]
    status: Literal["extracting", "pending_confirm", "applying", "applied", "undone", "failed"]
    items: list[ImportItem] = Field(default_factory=list)
    ex_count: int = 0
    panel_title: str = ""
    intro: str = "MI 작업에서 이 섹션에 쓸 내용을 뽑았습니다. 어느 시트에, 어떤 템플릿으로 들어갈지 함께 표시했어요."
    question: str = "이 섹션의 시트에 이렇게 넣을까요? 필요한 것만 남겨 주세요."
    label: str = ""
    note: str = ""
    toast: str = ""
    affected_sheet_ids: list[str] = Field(default_factory=list)
    new_sheet_ids: list[str] = Field(default_factory=list)
    change_ids: list[str] = Field(default_factory=list)
    link_id: str | None = None
    source_route: str | None = Field(None, description="「원본 채팅 보기」 원 작업 화면")
    job_id: str | None = None
    error: dict[str, Any] | None = None
    can_undo: bool = False
    created_by: str | None = None
    created_at: str


class ImportResult(_M):
    import_id: str
    status: str
    section_key: str
    label: str
    note: str
    toast: str = Field(description='「「QM65C」 추가됨 · "카운터 · 메뉴보드" 시트에 배치됨 · 수량 320」')
    affected_sheet_ids: list[str] = Field(default_factory=list)
    new_sheet_ids: list[str] = Field(default_factory=list)
    source_chip: SourceChipOut | None = None
    job_id: str | None = Field(None, description="관련 시트 내용 갱신 잡(카드 「업데이트됨」 → 끝나면 내용 반영)")
    confirm_item_ids: list[str] = Field(default_factory=list)
    route: str


class ImportApply(_M):
    keys: list[str]


class UndoResult(_M):
    import_id: str
    status: str
    removed_link_ids: list[str] = Field(default_factory=list)
    restored_sheet_ids: list[str] = Field(default_factory=list)
    removed_sheet_ids: list[str] = Field(default_factory=list)


class ImageSlot(_M):
    sheet_id: str
    sheet_no: int
    name: str
    sheet_title: str
    section: str
    section_name: str
    section_key: str
    slot: str
    slots: int
    recommended: bool
    preview_url: str | None = None


class ImageSlots(_M):
    proposal_id: str
    proposal_title: str
    image_ref: str | None = None
    sheets: list[ImageSlot]
    slots: list[ImageSlot]


# ── 딸깍(§6.7) ─────────────────────────────────────────────
class PlanRow(_M):
    key: str
    label: str
    note: str


class OneClickOptions(_M):
    mark_inferred: bool = True
    collect_reviews: bool = True


class OneClickPlan(_M):
    title: str = "딸깍으로 나머지를 완성할까요?"
    desc: str = "지금까지 확정한 내용은 그대로 두고, 남은 단계는 AI가 추론해 채운 뒤 최종 PPTX까지 만듭니다."
    from_stage: str
    from_section_key: str | None = None
    confirmed: list[str]
    rows: list[PlanRow]
    summary: str = Field(description="「섹션 6 · 시트 19」 / 「남은 5단계 · 약 24시트」")
    options: OneClickOptions = Field(default_factory=OneClickOptions)
    eta_label: str = "약 1–2분"
    footer_label: str = "약 1–2분 · 진행 중에도 다른 작업 가능"
    running_job_id: str | None = None


class OneClickStart(_M):
    options: OneClickOptions = Field(default_factory=OneClickOptions)
    from_stage: str | None = None
    from_section_key: str | None = None


class OneClickStep(_M):
    key: str
    label: str
    note: str
    status: Literal["confirmed", "inferred_done", "running", "waiting", "skipped", "canceled"]
    status_label: str


class OneClickMemo(_M):
    text: str
    at: str
    applied_at: str | None = None
    status_label: str = ""


class OneClickFile(_M):
    name: str
    meta: str
    pptx_file_id: str | None = None
    pdf_file_id: str | None = None
    pptx_url: str | None = None


class SlideThumb(_M):
    slide_no: int
    label: str
    thumb_url: str | None = None
    inferred: bool = False
    sheet_id: str | None = None
    kind: str = "sheet"


class OneClickView(_M):
    job_id: str
    status: Literal["running", "succeeded", "canceled", "failed", "queued"]
    from_stage: str
    from_section_key: str | None = None
    options: OneClickOptions
    plan: OneClickPlan | None = None
    steps: list[OneClickStep]
    memos: list[OneClickMemo] = Field(default_factory=list)
    auto_from_step: int
    header: str = Field(description="「· 조감도부터 나머지 자동 완성」")
    intro: str
    pct: int = 0
    eta_label: str = ""
    progress_label: str = Field("", description="「45% · 약 1분 남음」")
    type_label: str = ""
    slides_label: str = Field("", description="「표준 제안서 · 21장」")
    done_intro: str | None = None
    file: OneClickFile | None = None
    counts: dict[str, int] = Field(default_factory=dict, description="{confirmed, inferred, review}")
    counts_label: list[str] = Field(default_factory=list, description="「확정 5」 「추론 16」 「검토 필요 3」")
    thumbs: list[SlideThumb] = Field(default_factory=list)
    rest_label: str = ""
    review_items: list["ConfirmItem"] = Field(default_factory=list)
    review_header: str = ""
    next_route: str | None = Field(None, description="완료 → OneClickDone 또는 PR7(검토 모아 보기 끔), 중지 → 누른 단계 화면")
    error: dict[str, Any] | None = None


# ── 디자인 · 생성 · 미리보기(§6.8) ──────────────────────────
class MasterOut(_M):
    id: str
    name: str
    desc: str = ""
    preview_url: str | None = None
    recommended: bool = False
    builtin: bool = True
    selected: bool = False


class PinnedSheet(_M):
    sheet_no: int
    code: str


class SheetTemplatesSummary(_M):
    catalog_total: int
    industry: int
    dedicated: int
    sheets_total: int
    pinned: list[PinnedSheet]
    label: str = Field(description="「미리 만든 템플릿 234종 (업종별 75 · 솔루션 전용 54) · 시트 24장 중 직접 고른 2장 (P3-C · CM-B) · 나머지 자동 추천」")


class PreGenerate(_M):
    empty_sections: list[RouteRef] = Field(default_factory=list)
    empty_sheet_count: int = 0
    notice: str | None = Field(None, description="「자료 없는 시트 {{n}}장 · 딸깍으로 채우기」")


class DesignView(_M):
    intro: str
    header_label: str = "디자인 템플릿 · 하나 선택 · 5 / 6"
    masters: list[MasterOut]
    design: Design
    sheet_templates: SheetTemplatesSummary
    pre_generate: PreGenerate
    generate_job_id: str | None = None


class CoverIn(_M):
    enabled: bool | None = None
    image_ref: CoverImageRef | None = None


class DesignPatch(_M):
    master_id: str | None = None
    logo_file_id: str | None = None
    brand_hex: str | None = None
    cover: CoverIn | None = None
    page_numbers: bool | None = None
    appendix: bool | None = None
    section_dividers: bool | None = None
    layout_mode: Literal["auto", "manual"] | None = None


class LogoIn(_M):
    file_id: str


class GenerateIn(_M):
    scope: Literal["all", "section"] = "all"
    section_key: str | None = None
    infer_empty: bool = Field(True, description="자료 없는 섹션을 추론으로 채우고 검토 필요로(AC-134)")


class ResultFile(_M):
    name: str
    slides: int
    sheets: int
    type_label: str
    sections: int
    notes_count: int
    created_at: str | None = None
    created_label: str = "방금 생성"
    version: int
    pptx_file_id: str | None = None
    pdf_file_id: str | None = None
    pptx_url: str | None = None
    pdf_url: str | None = None
    meta: str = Field("", description="「24 슬라이드 · 표준 제안서 8섹션 · 방금 생성 · 노트 3건」")


class SlideRange(_M):
    from_: int = Field(alias="from", serialization_alias="from")
    to: int
    label: str
    flag: str | None = None

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class ResultView(_M):
    status: Literal["none", "running", "done", "failed"]
    job_id: str | None = None
    error: dict[str, Any] | None = None
    file: ResultFile | None = None
    message: str = ""
    thumbs: list[SlideThumb] = Field(default_factory=list)
    ranges: list[SlideRange] = Field(default_factory=list)
    ranges_label: str = ""
    regen_section: RouteRef | None = Field(None, description="「{{섹션}} 섹션만 재생성」 칩(label · section_key 는 route 마지막)")
    regen_section_key: str | None = None
    footer_label: str = "PPTX 생성 · 6 / 6 · 완료"
    derived: bool = Field(False, description="파생 제안서(PRU5 자리)")
    summary_route: str | None = None


class RailSheet(_M):
    sheet_no: int
    sheet_id: str
    title: str
    thumb_url: str | None = None
    edited: bool = False
    confirm: bool = False
    inferred: bool = False
    aria_label: str = ""


class RailSection(_M):
    no: int
    key: str
    name: str
    label: str = Field(description="「06 유관 사례」")
    sheets: list[RailSheet]


class SlidesView(_M):
    version: int
    edits_since_version: int
    version_label: str = Field(description="「v1 · 수정 2」")
    file_name: str = ""
    sheets_total: int
    slides_total: int
    toolbar_label: str = Field("", description="「시트 24 + 표지 · 목차 · 자동 저장됨」")
    rail_label: str = Field("", description="「표지 · 목차 포함 26장」")
    open_confirm: int = 0
    sections: list[RailSection]
    filter: str | None = None
    rev: int = 0


class RenderIn(_M):
    sheet_ids: list[str] | None = None


# ── 확인 항목(§6.9) ────────────────────────────────────────
class ConfirmText(_M):
    pre: str = ""
    mark: str
    post: str = ""


class ConfirmActionTarget(_M):
    route: str | None = None
    feature: str | None = None
    ref_id: str | None = None
    op: str | None = None


class ConfirmAction(_M):
    kind: Literal["link", "button"]
    label: str
    target: ConfirmActionTarget


class FixPart(_M):
    text: str | None = None
    input: str | None = Field(None, description="fact key")
    label: str | None = None
    value: str | None = None


class FixSheet(_M):
    sheet_id: str
    sheet_no: int
    name: str


class ConfirmFix(_M):
    sentence: list[FixPart]
    formula: str | None = None
    linked_sheets: list[FixSheet] = Field(default_factory=list)


class Candidate(_M):
    value: str
    source: dict[str, Any] = Field(default_factory=dict)


class ConfirmItem(_M):
    id: str
    proposal_id: str
    category: Literal["fact", "review"]
    tag: str
    sheet_id: str | None = None
    sheet_no: int | None = None
    sheet_no_label: str = ""
    section_key: str | None = None
    fact_id: str | None = None
    text: ConfirmText
    sub: str = ""
    action: ConfirmAction | None = None
    fix: ConfirmFix | None = None
    linked_sheet_ids: list[str] = Field(default_factory=list)
    where: str | None = None
    why: str | None = None
    status: Literal["open", "confirmed", "moved_to_note", "dismissed"]
    status_label: str
    resolution: dict[str, Any] | None = None
    evidence: FactEvidence | None = None
    candidates: list[Candidate] = Field(default_factory=list)
    candidates_label: str | None = Field(None, description="「후보 2」")
    origin: str
    route: str = Field(description="「섹션 열기」 · 「바로 고치기」 이동")
    created_at: str


class ConfirmCounts(_M):
    open: int = 0
    confirmed: int = 0
    total: int = 0


class ConfirmList(_M):
    items: list[ConfirmItem]
    counts: ConfirmCounts
    header_label: str = Field(description="「확정 필요 7곳」")
    progress_label: str = Field(description="「2곳 확정 · 5곳 남음」")
    intro: str
    confirmed_summary: str = ""
    footer_label: str = ""
    sheets_total: int = 0


class ConfirmCreate(_M):
    sheet_id: str
    text: str
    from_comment_id: str | None = None
    tag: str | None = None


class ConfirmResolve(_M):
    value: str | None = None
    values: dict[str, str] = Field(default_factory=dict, description="fact key → 값")
    evidence: FactEvidence | None = None


class ConfirmResolveResult(_M):
    item: ConfirmItem
    changed_sheet_ids: list[str] = Field(default_factory=list)
    change_ids: list[str] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)


class QuestionIn(_M):
    push_to_rq: bool = True


class QuestionOut(_M):
    text: str
    pushed: bool = False
    question_id: str | None = None


class EvidenceIn(_M):
    evidence: FactEvidence


class BulkIds(_M):
    ids: list[str] | None = None


class ResearchIn(_M):
    ids: list[str] | None = None
    instruction: str | None = None


# ── 검토(파사드) · 코멘트 제안(§6.10) ───────────────────────
class ReviewRequestIn(_M):
    reviewer_ids: list[str] = Field(min_length=1)
    due_date: str | None = None
    message: str | None = None


class ResubmitIn(_M):
    message: str | None = None


class Reviewer(_M):
    user_id: str
    name: str
    initial: str
    role: str = ""
    status: Literal["approved", "changes_requested", "pending"]
    status_label: str
    me: bool = False


class ReviewInfo(_M):
    id: str
    version: int
    status: str
    status_label: str
    message: str | None = None
    due_date: str | None = None
    requested_at: str | None = None
    sent_label: str = Field("", description="「오늘 11:00 보냄 · 마감 10월 8일 (수)」")
    requester_name: str = ""


class Approvals(_M):
    done: int
    total: int
    label: str


class CommentSheet(_M):
    sheet_no: int
    sheet_id: str
    name: str
    open: int
    resolved: int
    label: str = ""


class CheckCell(_M):
    sheet_no: int
    sheet_id: str
    state: Literal["ok", "open", "todo"]
    title: str


class ReviewView(_M):
    review: ReviewInfo | None = None
    reviewers: list[Reviewer] = Field(default_factory=list)
    approvals: Approvals
    comment_sheets: list[CommentSheet] = Field(default_factory=list)
    comments_open: int = 0
    comments_resolved: int = 0
    check_grid: list[CheckCell] = Field(default_factory=list)
    check_label: str = ""
    my_turn: bool = False
    can_decide: bool = False
    suggest_text: str | None = Field(None, description="「열린 코멘트 {{n}}건을 반영한 수정안을 만들 수 있어요. …」")
    version_label: str = ""
    comment_target: str = Field(description="workspace 코멘트 target 접두(proposal:pr_…)")
    share_permission_label: str = "팀 내부 · 코멘트 가능"


class DecisionIn(_M):
    decision: Literal["approve", "request_changes"]
    comment: str | None = None


class CheckPut(_M):
    state: Literal["ok", "todo"]


class ApplyCommentsIn(_M):
    comment_ids: list[str] | None = None


class Suggestion(_M):
    comment_id: str
    status: Literal["none", "running", "done", "failed", "not_applicable"]
    suggestion_text: str | None = None
    patch: list[dict[str, Any]] = Field(default_factory=list)
    sheet_id: str | None = None
    job_id: str | None = None


class ApplySuggestionResult(_M):
    comment_id: str
    sheet: Sheet | None = None
    change_ids: list[str] = Field(default_factory=list)


class ShareLinkIn(_M):
    permission: Literal["team_comment", "team_view"] = "team_comment"


class ShareLinkOut(_M):
    url: str
    token: str | None = None
    permission: str
    permission_label: str


# ── 버전 · 변경(§6.11) ─────────────────────────────────────
class VersionChange(_M):
    change_id: str
    t: str
    text: str


class VersionItem(_M):
    n: int
    label: str = Field(description="「v3」")
    kind: str
    desc: str
    author_label: str
    created_at: str
    time_label: str = Field("", description="「오늘 14:20 · 최민섭」")
    current: bool = False
    derived_label: str | None = None
    changes: list[VersionChange] = Field(default_factory=list)


class VersionEvent(_M):
    at: str
    text: str
    kind: str = "review_request"


class TimelineEntry(_M):
    kind: Literal["version", "event", "changes"]
    n: int | None = None
    at: str
    text: str


class VersionsView(_M):
    current: int
    current_label: str = ""
    versions: list[VersionItem]
    events: list[VersionEvent]
    change_count: int
    pending_changes: list[VersionChange] = Field(default_factory=list, description="마지막 버전 이후 변경")
    header_label: str = Field(description="「버전 3 · 변경 기록 12」")
    next_save_label: str = Field(description="「지금 상태를 v4로 저장」")
    retention_note: str = "자동 저장 기록은 30일 동안 남아요"


class VersionCreate(_M):
    desc: str | None = None


class VersionCreated(_M):
    n: int


class CompareSide(_M):
    n: int
    label: str
    meta: str = ""
    png_url: str | None = None
    sheet_id: str | None = None
    display: dict[str, Any] | None = Field(None, description="그 버전의 그 시트 display(§5.3.1) — PNG 가 없을 때 웹이 슬라이드를 직접 그린다")


class CompareSheet(_M):
    sheet_no: int
    sheet_id: str
    name: str
    count: int


class DiffItem(_M):
    n: int
    change_id: str | None = None
    sheet_id: str
    sheet_no: int | None = None
    where: str
    kind: str
    from_: Any = Field(None, alias="from", serialization_alias="from")
    to: Any = None
    from_swatch: str | None = None
    to_swatch: str | None = None
    why: str = ""
    bbox: dict[str, float] | None = None
    revertable: bool = True

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class CompareView(_M):
    a: CompareSide
    b: CompareSide
    changed_sheets: list[CompareSheet]
    diffs: list[DiffItem]
    header_label: str = Field(description="「바뀐 시트 4 · 바뀐 곳 6」")
    sheet_id: str | None = None
    footer_note: str = ""


class RestoreIn(_M):
    scope: Literal["all", "sheet"] = "all"
    sheet_id: str | None = None


class RestoreResult(_M):
    scope: str
    new_version: int | None = None
    change_ids: list[str] = Field(default_factory=list)


class RevertResult(_M):
    change_id: str = Field(description="새로 기록한 반대 변경")
    reverted_change_id: str
    sheet_id: str | None = None


# ── 내보내기(§6.12) ────────────────────────────────────────
class ExportScope(_M):
    kind: Literal["all", "sections", "sheets"] = "all"
    section_keys: list[str] | None = None
    range: str | None = Field(None, description="「01–07, 21」")


class ExportInclude(_M):
    speaker_notes: bool = True
    footnotes: bool = True
    appendix: bool = False


class TeamFolder(_M):
    enabled: bool = True
    path: str | None = None


class ExportRequest(_M):
    version: int | None = Field(None, description="없으면 현재 상태")
    formats: list[Literal["pptx", "pdf"]] = Field(default_factory=lambda: ["pptx"])
    lang: Literal["ko", "en", "ko_en"] = "ko"
    master_id: str | None = None
    scope: ExportScope = Field(default_factory=ExportScope)
    include: ExportInclude = Field(default_factory=ExportInclude)
    tbd_mode: Literal["keep_marks", "move_to_notes"] = "keep_marks"
    filename_base: str | None = None
    team_folder: TeamFolder = Field(default_factory=lambda: TeamFolder(enabled=False))


class ExportOptions(_M):
    version: int
    version_label: str
    header_label: str
    intro: str
    sheets_total: int
    sections: list[RouteRef] = Field(default_factory=list)
    masters: list[MasterOut]
    defaults: ExportRequest
    open_confirm: int
    open_confirm_label: str = ""
    filename_tokens: list[str] = Field(default_factory=lambda: ["고객사", "제안명", "버전", "날짜"])
    preview_files: list[str]
    eta_label: str
    team_folder_path: str
    tbd_note: str = "영문은 번역 후 넘치는 문장을 줄이고, [확정 필요] 표시는 [TBD]로 바꿔요."
    include_note: str = "검토 코멘트와 '추론' 표시는 파일에 넣지 않아요."


class ExportFileOut(_M):
    lang: str
    format: str
    name: str
    file_id: str
    size: int | None = None
    url: str


class ExportRecord(_M):
    id: str
    proposal_id: str
    version: int | None = None
    formats: list[str]
    lang: str
    master_id: str | None = None
    scope: ExportScope
    include: ExportInclude
    tbd_mode: str
    filename_base: str
    team_folder: TeamFolder
    job_id: str | None = None
    files: list[ExportFileOut] = Field(default_factory=list)
    team_folder_files: list[str] = Field(default_factory=list)
    status: Literal["queued", "running", "done", "failed"]
    error: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)
    created_at: str


class MasterUpload(_M):
    file_id: str
    name: str | None = None


class MasterCreated(_M):
    master_id: str
    name: str


# ── 기존 제안서 활용(§6.13) ─────────────────────────────────
class ReuseCandidate(_M):
    proposal_id: str
    name: str
    why: Literal["같은 고객", "같은 솔루션"]
    version: int | None = None


class ReuseCandidates(_M):
    items: list[ReuseCandidate]
    label: str = Field("", description="「내 제안서 목록에서는 2개 추천」")


class ReuseSourceIn(_M):
    kind: Literal["proposal", "file"]
    proposal_id: str | None = None
    version: int | None = None
    file_id: str | None = None


class ReuseStart(_M):
    sources: list[ReuseSourceIn] = Field(min_length=1)
    mode_pref: Literal["improve", "borrow", "auto"] = "auto"
    new_title: str | None = None
    replace: bool = Field(False, description="false = 분석 중인 원본에 더함(파일 더 놓기), true = 이 목록으로 바꿈(원본 빼기)")


class ReuseSourceOut(_M):
    kind: Literal["proposal", "file"]
    proposal_id: str | None = None
    version: int | None = None
    file_id: str | None = None
    name: str
    format: str
    pages: int = 0
    author: str | None = None
    doc_date: str | None = None
    customer: str | None = None
    meta_label: str = Field("", description="「PPTX · 24장 · 2024.09 · 김하늘(동료)」")
    phases: list[Phase] = Field(default_factory=list)


class ReusePage(_M):
    no: int
    source_idx: int = 0
    file_page: int | None = None
    title: str
    text_excerpt: str = ""
    thumb_url: str | None = None
    section_name: str = ""
    section_color: str = ""
    flow_role: str | None = None
    role_state: Literal["auto", "ok", "edited", "need"] = "auto"
    role_state_label: str = ""
    role_candidates: list[str] = Field(default_factory=list)
    evidence: str = ""
    evidence_warn: bool = False
    excluded: bool = False
    exclude_reason: str | None = None
    locked: bool = False


class ReuseSection(_M):
    name: str
    count: int
    color: str
    excluded: bool = False


class ReuseCriterion(_M):
    no: int
    key: str
    name: str
    must: bool
    summary: str
    confidence: int
    warn: bool
    state: Literal["ok", "need", "edited"]
    state_label: str


class FlowStep(_M):
    name: str
    count: int
    dashed: bool = False
    excluded: bool = False
    note: str = ""
    range: str = ""


class FlowMemo(_M):
    no: int
    text: str
    tag: str
    action: str


class ReuseFlow(_M):
    steps: list[FlowStep]
    pattern: dict[str, str] = Field(default_factory=dict)
    claims: dict[str, int] = Field(default_factory=dict)
    broken: list[str] = Field(default_factory=list)
    memos: list[FlowMemo] = Field(default_factory=list)


class ReuseRecommendation(_M):
    mode: Literal["improve", "borrow"]
    reason: str
    badge: str


class ReusePlanRow(_M):
    row_id: str
    group: str
    page: int | None = None
    page_label: str = ""
    thumb_kind: str | None = None
    sheet_name: str
    verdict: Literal["keep", "update", "rewrite", "new", "drop"]
    verdict_label: str
    note: str
    rq_ids: list[str] = Field(default_factory=list)
    locked: bool = False
    noncopy: bool = False


class ReusePlanGroup(_M):
    name: str
    count: int
    range: str = ""
    label: str = ""
    is_new: bool = False
    rows: list[ReusePlanRow]


class Coverage(_M):
    rq_id: str
    code: str
    name: str
    state: Literal["has", "part", "none"]
    state_label: str
    where: str


class OnlyInSource(_M):
    label: str
    tag: Literal["제외 제안", "비복제"]


class PlanImprove(_M):
    groups: list[ReusePlanGroup]
    requirement_coverage: list[Coverage]
    only_in_source: list[OnlyInSource]
    totals: dict[str, int]
    source_total: int
    new_total: int
    summary_note: str = ""
    shown_label: str = Field("", description="「12 / 21장 표시 · 나머지 9장 보기」")
    footer_label: str = ""


class BorrowRow(_M):
    src_step: str
    src_count: int
    src_range: str = ""
    kind: Literal["flow", "new", "drop"]
    new_label: str
    note: str
    rq_ids: list[str] = Field(default_factory=list)
    new_count: int


class TakeItem(_M):
    label: str
    sub: str


class PlanBorrow(_M):
    rows: list[BorrowRow]
    take: list[TakeItem]
    not_take: list[TakeItem]
    sections: int
    sheets: int
    counts: dict[str, int]
    footer_label: str = ""


class ReuseView(_M):
    id: str
    proposal_id: str
    job_id: str | None = None
    job_status: str | None = None
    status: Literal["analyzing", "awaiting_confirm", "planning", "awaiting_plan_confirm", "applied", "failed"]
    status_label: str
    sources: list[ReuseSourceOut]
    phases: list[Phase]
    mode_pref: Literal["improve", "borrow", "auto"]
    mode: Literal["improve", "borrow"] | None = None
    recommendation: ReuseRecommendation | None = None
    pages: list[ReusePage] = Field(default_factory=list)
    source_sections: list[ReuseSection] = Field(default_factory=list)
    criteria: list[ReuseCriterion] = Field(default_factory=list)
    flow: ReuseFlow | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    plan_improve: PlanImprove | None = None
    plan_borrow: PlanBorrow | None = None
    must_done: int = 0
    must_total: int = 3
    confirmed_count: int = 0
    can_confirm: bool = False
    intro: str = ""
    footer_label: str = ""
    excluded_page_count: int = 0
    band_label: str = Field("", description="「원본 24장 · 외부 파일 · 섹션 8개」")
    error: dict[str, Any] | None = None


class CriterionDetail(_M):
    no: int
    key: str
    name: str
    must: bool
    state: Literal["ok", "need", "edited"]
    state_label: str
    confidence: int
    summary: str
    header_label: str = ""
    intro: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)
    pages: list[ReusePage] = Field(default_factory=list)
    flow: ReuseFlow | None = None
    footer_label: str = ""
    chips: list[dict[str, Any]] = Field(default_factory=list, description="기준 전환 칩 1–9")


class CriterionPut(_M):
    state: Literal["ok", "need"] | None = None
    edits: dict[str, Any] | None = None


class RolePut(_M):
    role: str


class ModePut(_M):
    mode: Literal["improve", "borrow"] | None = Field(None, description="PRU3 활용 방식 전환(계획을 그 방식으로)")
    mode_pref: Literal["improve", "borrow", "auto"] | None = Field(None, description="PR1C 라디오 — 저장만(분석은 그대로)")


class VerdictPut(_M):
    verdict: Literal["keep", "update", "rewrite", "new", "drop"]


class PlanConfirm(_M):
    then: Literal["sections", "compose"] = "sections"


class ReuseConfirmOut(_M):
    job_id: str | None = None
    status: str
    route: str | None = None


class ReuseLineView(_M):
    id: str
    text: str
    mark: Literal["keep", "update", "new", "drop"]
    draft_text: str | None = None
    source_line_id: str | None = None
    badge: str | None = None
    edited: bool = False


class ReuseSheetSide(_M):
    sheet_id: str | None = None
    page: int | None = None
    page_label: str = ""
    title: str = ""
    thumb_url: str | None = None
    kind_label: str = ""
    lines: list[ReuseLineView] = Field(default_factory=list)
    images_note: str = ""
    note: str = ""
    rq_label: str = ""
    title_label: str = ""


class GuideStep(_M):
    no: int
    title: str
    status: Literal["writing", "waiting"]
    status_label: str
    role: str
    from_source: str
    this_time: str
    chips: list[str] = Field(default_factory=list)


class ReuseSectionView(_M):
    view: Literal["compare", "guide", "new_only"]
    mode: Literal["improve", "borrow"]
    header_label: str
    section_key: str
    sheet_id: str | None = None
    source_label: str = ""
    source_sheet: ReuseSheetSide | None = None
    new_sheet: ReuseSheetSide
    section_sheets: list[dict[str, Any]] = Field(default_factory=list)
    tally: dict[str, int] = Field(default_factory=dict)
    footer_label: str = ""
    guide: list[GuideStep] = Field(default_factory=list)
    guide_label: str = ""
    placeholders: list[dict[str, Any]] = Field(default_factory=list)
    compare_disabled_reason: str | None = None


class PullLines(_M):
    line_ids: list[str] | None = None
    all: bool = False


class SummaryCount(_M):
    verdict: str
    label: str
    n: int
    desc: str


class SummaryMapRow(_M):
    section: str
    src_count: int
    chips: list[str]
    new_count: int
    src_label: str = ""
    new_label: str = ""


class TraceRow(_M):
    title: str
    sub: str


class ReuseSummary(_M):
    intro: str
    counts: list[SummaryCount]
    mapping: list[SummaryMapRow]
    mapping_label: str
    review_items: list[ConfirmItem]
    review_total: int
    review_more_label: str = ""
    traces: list[TraceRow]
    changed_count: int
    footer_label: str
    file_label: str = ""


OneClickView.model_rebuild()
