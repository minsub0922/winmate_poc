"""kb API 응답 모델(00-shell §7.2 필드 이름 · 타입 그대로 + 덧붙인 필드는 설명에 '추가' 표시)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ImageKind = Literal["product", "case", "solution", "industry"]
Grade = Literal["A", "A?C", "C", "D", "E"]
Rights = Literal["official", "customer_case"]

SALE_STATUS_DESC = ("추가 — 사이트 판매상태코드(saleStatCd) 원값. 코드표(뜻)는 KB 에 없다. KB 수집본 값은 '17'(589 제품군) · '15'(16 제품군) 둘뿐이고 "
                    "둘 다 수집 시점(2026-10-04) 사이트 목록에 노출된 상품이라 DR09 기준 판매 중으로 본다(lifecycle.status=on_sale). "
                    "단종 · 단종 예정 코드는 수집본에 없다 — 목록에서 빠진 모델은 KB 에 없고 lifecycle.status=not_in_catalog 다")


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ── 공통 ─────────────────────────────────────────────────

class IdName(_M):
    id: str
    name: str


class ImageDims(_M):
    width: int
    height: int
    format: str | None = Field(None, description="JPG · PNG · WEBP … (모르면 null)")
    bytes: int | None = Field(None, description="파일 크기(바이트). 모르면 null(화면이 KB 로 포맷)")
    basis: str | None = Field(None, description="추가 — 값의 근거: download(내려받은 원본) · board_sample(보드 표본) · "
                                                 "browser_probe(썸네일 만들 때 잰 원본 크기, 용량 없음) · local_file · thumbnail")


class Focal(_M):
    x: float
    y: float


class ImageCard(_M):
    id: str
    kind: ImageKind
    title: str = Field(description="갭 G-IMG-3: 큐레이션 제목이 없으면 alt 앞 40자")
    alt: str
    stored_url: str = Field(description="로컬 저장본 주소(게이트웨이). 원본 사본이 없으면 썸네일을 준다")
    thumb_url: str
    original: ImageDims | None
    focal: Focal | None = Field(description="갭 G-IMG-4: 아직 없음(null) → 화면 기본 50%/50%")
    source_domain: str
    grade: Grade
    rights: Rights
    has_local: bool = Field(description="추가 — 썸네일이나 로컬 사본이 있으면 true(없으면 /thumb · /file 이 404)")


class SourcePage(_M):
    url: str
    title: str | None
    label: str


class Posted(_M):
    date: str
    basis: Literal["case_page", "file_path"]


class Depict(_M):
    kind: str
    id: str
    name: str
    level: str


class ImageContext(_M):
    space_type_id: str | None
    vertical_id: str | None


class ImageMeta(ImageCard):
    label: str
    source_page: SourcePage
    original_url: str
    stored: ImageDims | None = Field(description="갭 G-IMG-2: 실제로 주는 로컬 사본(없으면 썸네일)의 메타")
    posted: Posted | None
    collected_at: str | None
    source_type_label: str
    usage_note: str = Field(description="§9.6-6: 도입사례 `“도입사례 사진” 표기 필수 · 대외 사용 범위 확인 필요` · 공식 `삼성전자 저작물 · 대외 사용 범위 확인 필요`")
    usage_note_short: str = Field(description="추가 — 팝오버 표기(공식 이미지는 `대외 사용 범위 확인 필요`)")
    caption_rule: str = Field(description="추가 — 제안서 캡션 규칙(`도입사례 사진` · `예시 사진(삼성 공식 이미지)`)")
    page_note: str | None
    depicts: list[Depict]
    context: ImageContext


class ListPage(_M):
    next_cursor: str | None = None


# ── 메타 ─────────────────────────────────────────────────

class MetaCounts(_M):
    case_pages: int
    deployments: int
    families: int
    models: int
    image_assets: int
    thumbnails: int = Field(description="추가 — 썸네일이 있는 이미지 수")
    local_images: int = Field(description="추가 — 로컬 원본 사본 수(WKB_IMAGE_DIR)")


class MetaOut(_M):
    kb_version: str
    collected_at: str | None
    products_fetched_at: str | None = Field(None, description="추가 — kb_meta.products_fetched_at(카탈로그 버전 YYYY-MM 의 원천)")
    catalog_version: str | None = Field(None, description="추가 — products_fetched_at 의 YYYY-MM")
    counts: MetaCounts
    warm: bool = Field(description="추가 — 무거운 캐시(벡터 · 메시지)가 준비됐는지")


# ── 분류 · 제품 ───────────────────────────────────────────

class CategoryItem(_M):
    id: str
    name: str
    level: int
    parent_id: str | None
    order: int
    has_children: bool
    family_count: int


class CategoryList(ListPage):
    items: list[CategoryItem]


class FamilyItem(_M):
    id: str
    name: str
    series_label: str
    model_count: int
    subcategory: IdName | None
    is_bundle: bool
    detail_url: str | None
    thumb: ImageCard | None
    series_code: str | None = Field(None, description="추가 — marketing_model 이 짧은 코드면 그 코드(QMC)")
    sale_status_code: str | None = Field(None, description=SALE_STATUS_DESC)


class FamilyList(ListPage):
    items: list[FamilyItem]


class Column(_M):
    key: str
    label: str


class ModelValue(_M):
    display: str = Field(description="표시 문자열. 값이 없으면 `—`")
    cm: float | None = None
    inch: int | None = None
    nit: float | None = None
    w: int | None = None
    h: int | None = None
    value: float | None = Field(None, description="숫자 값(크기 · 밝기 · 해상도 밖의 열)")
    unit: str | None = None
    raw: str | None = Field(None, description="KB value_raw 원문")


class FamilyRef(_M):
    id: str
    name: str
    series_label: str


class ModelRow(_M):
    id: str
    model_code: str
    display_name: str
    display_name_basis: Literal["code_rule", "model_code"] = Field(description="추가 — G-PRD-1 표시명 근거")
    family: FamilyRef
    values: dict[str, ModelValue]
    thumb: ImageCard | None
    is_family_default: bool


class ModelList(ListPage):
    columns: list[Column]
    items: list[ModelRow]
    profile: str = Field(description="추가 — 열 프로필 id(00-shell §9.4)")


class ProductSearchItem(_M):
    kind: Literal["model", "family"]
    id: str
    display_name: str
    label: str = Field(description="버블 글: `{영문 계열명} {표시명}`(사이니지 모델) · 그 밖은 표시명")
    model_code: str | None
    family_id: str = Field(description="추가")
    family_name: str
    category_path: list[str]
    meta_line: str
    thumb: ImageCard | None
    highlight: list[list[int]] = Field(description="display_name 안에서 검색어와 맞은 [시작, 끝) 범위")
    score: float = Field(description="추가 — 정렬 점수")


class ProductSearchOut(_M):
    items: list[ProductSearchItem]


# ── 모델 상세 ─────────────────────────────────────────────

class FamilyDetailRef(FamilyRef):
    detail_url: str | None


class Fact(_M):
    label: str
    value: str


class Evidence(_M):
    text: str
    source_url: str | None


class SupportedSolution(_M):
    id: str = Field(description="솔루션 시트 id(카탈로그 id, 카탈로그에 없으면 KB id)")
    kb_id: str
    name: str = Field(description="제품 페이지 원문 표기(예 `VXT`)")
    catalog_name: str | None = Field(None, description="추가 — 카탈로그 이름(예 `Samsung VXT`)")
    kind_label: str
    evidence: Evidence


class SpecRow(_M):
    label: str
    value: str
    attrs: list[str] = Field(description="이 행을 만든 KB 속성 `그룹 › 속성`")


class SpecGroup(_M):
    name: str
    column: Literal["left", "right"] | None = Field(None, description="추가 — 프로필 2열 배치(없으면 null)")
    rows: list[SpecRow]


class SpecBlock(_M):
    profile: str | None = Field(description="프로필 id(사이니지 = `signage`). 프로필이 맞지 않으면 null → KB 원래 그룹 · 행 전체")
    source_url: str | None
    groups: list[SpecGroup]


class DetailCounts(_M):
    images: int
    cases: int


class Corpus(_M):
    count: int
    checked_at: str | None


DimsKind = Literal["body", "without_stand", "with_stand", "package", "active_area", "indoor_unit", "outdoor_unit", "panel", "other"]


class Dims(_M):
    """정규화한 치수(mm). 원문 수치를 속성 이름의 축 순서대로 옮긴 것(계산 없음 · 단위만 mm)."""

    w: float | None = Field(description="가로(mm)")
    h: float | None = Field(description="높이(mm)")
    d: float | None = Field(None, description="깊이 · 두께(mm). 원문에 없으면 null")
    unit: Literal["mm"] = "mm"
    raw: str = Field(description="KB value_raw 원문")
    attr: str = Field(description="원문 행 `그룹 › 속성`")
    kind: DimsKind = Field(description="body(제품 · 본체) · without_stand · with_stand · package · active_area(화면 발광부) · "
                                       "indoor_unit · outdoor_unit · panel · other")
    order: str = Field(description="원문의 축 순서(WxHxD · WxDxH · HxWxD · WxH …)")
    order_basis: Literal["attr", "group", "default"] = Field(description="축 순서를 정한 근거(속성 이름 · 그룹 이름 · 기본 W×H×D)")
    spec_value_id: str | None = None


class WarrantyClaim(_M):
    text: str = Field(description="PDP 특장점 원문 문장(부품 · 혜택 보증일 수 있어 연수로 읽지 않는다)")
    source_url: str | None


class Warranty(_M):
    """스펙 API 의 보증 행 원문(`품질보증기준` · `품질 보증 기간` · `보증기간`). KB 에 행이 없으면 객체 자체가 null."""

    status: Literal["stated", "statement_only"] = Field(description="stated = 원문에 기간 숫자가 있음 · statement_only = "
                                                                    "'소비자분쟁해결기준에 따라 보상' 같은 문구뿐(연수 없음 → 확인 필요)")
    years: float | None = Field(description="보증 연수(3개월 = 0.25). 원문에 숫자가 없으면 null")
    months: int | None
    parts_years: float | None = Field(description="부품보유년한(원문에 있을 때만)")
    text: str = Field(description="원문 값 그대로")
    attr: str = Field(description="원문 행 `그룹 › 속성`")
    source_ref: str | None = Field(description="KB occurrence id")
    source_url: str | None
    as_of: str | None = Field(description="원문 수집 시각")
    claims: list[WarrantyClaim] = Field(default_factory=list, description="PDP 특장점의 보증 문구(최대 3, 예 `모터와 컴프레서 10년 무상보증`)")


class LedPixels(_M):
    w: int
    h: int
    raw: str
    attr: str


class LedArea(_M):
    w: float
    h: float
    basis: str


class SizeMention(_M):
    inch: int
    qualifier: str | None = Field(description="원문의 `최대` · `최소`(없으면 null)")
    text: str = Field(description="PDP 원문 문장")
    source_url: str | None


class LedInfo(_M):
    """스마트 LED 사이니지만(그 밖은 null). 화면 구성 옵션(대각 · 가로×세로) 표는 KB 에 없다."""

    pixel_pitch_mm: float | None
    pitch_basis: Literal["spec", "option"] | None
    unit_pixels: LedPixels | None = Field(description="한 단위(캐비닛 또는 올인원 화면)의 픽셀 구성 원문(Pixel Configuration · LED 구성)")
    unit_active_mm: LedArea | None = Field(description="unit_pixels × pixel_pitch_mm(계산값, 발광 면적)")
    size_mentions: list[SizeMention] = Field(description="PDP 원문의 화면 크기 언급(예 IAC `최대 130인치 화면`)")
    note: str


class ModelDetail(_M):
    id: str
    model_code: str
    display_name: str
    display_name_basis: Literal["code_rule", "model_code"]
    family: FamilyDetailRef
    category_path: list[IdName]
    title_line: str
    key_chips: list[str]
    facts: list[Fact]
    supported_solutions: list[SupportedSolution]
    spec: SpecBlock
    documents: list[dict[str, Any]] | None = Field(description="갭 G-PRD-3: KB v1 에 매뉴얼 자료 없음 → null")
    verified_at: str | None
    counts: DetailCounts
    case_corpus: Corpus
    label_en: str | None = Field(None, description="추가 — 영문 계열명 + 표시명(`Smart Signage QM55C`), 없으면 null")
    sale_status_code: str | None = Field(None, description=SALE_STATUS_DESC)
    sold_out_flag: str | None = Field(None, description="추가 — 사이트 옵션 품절 표시 원값(Y · N · null)")
    warranty: Warranty | None = Field(None, description="추가(06-spec 요청 1) — 스펙 보증 행 원문. 행이 없으면 null")
    dims_mm: Dims | None = Field(None, description="추가(08-birdseye 요청 4) — 대표 본체 치수(mm): body → without_stand 순으로 처음 행. 없으면 null")
    dims_all: list[Dims] = Field(default_factory=list, description="추가 — 읽힌 치수 행 전부(스탠드 포함 · 포장 · 실내기 · 액티브 디스플레이 …)")
    led: LedInfo | None = Field(None, description="추가(08-birdseye 요청 2) — 스마트 LED 사이니지의 피치 · 픽셀 구성 · 발광 면적(그 밖은 null)")
    release_ym: str | None = Field(None, description="추가 — 스펙 '동일모델의 출시년월'(YYYY-MM), 없으면 null")


class ImageList(_M):
    items: list[ImageMeta]
    total: int


# ── 사례 ─────────────────────────────────────────────────

class CaseProduct(_M):
    label: str
    ref: str | None
    tier: str | None


class CasePhotos(_M):
    count: int
    items: list[ImageCard]


class MatchBreakdown(_M):
    vertical: float
    space: float
    product: float
    text: float


class CaseMatch(_M):
    score: float
    breakdown: MatchBreakdown
    terms: list[str]


class CaseCard(_M):
    id: str
    title: str
    date: str | None
    url: str | None
    url_display: str | None
    vertical: IdName | None
    tag_detail: str | None = Field(description="갭 G-CASE-2: 공간 유형 → 짧은 말 사전([제안])")
    summary: str | None = Field(description="갭 G-CASE-1: KB v1 에 요약 없음 → null")
    quote: str | None = Field(None, description="추가 — 사례 인용문(T5, 이전 세션 추출) — 요약 아님")
    products: list[CaseProduct]
    photos: CasePhotos
    match: CaseMatch | None
    source_tier: str | None
    format: str | None = Field(None, description="추가 — article · pdf · video")


class ModelCaseItem(CaseCard):
    match_type: Literal["model", "series", "usage"]
    used_products_line: str


class MatchCounts(_M):
    model: int
    series: int
    usage: int


class ModelCases(_M):
    corpus: Corpus
    counts: MatchCounts
    usage_label: str | None
    default_match: Literal["model", "series", "usage"] | None = Field(None, description="추가 — 기본 켜짐 칩(모델 → 시리즈 → 용도 중 처음 1건 이상)")
    items: list[ModelCaseItem]


class Kpi(_M):
    id: str
    text: str
    has_number: bool
    claim_flag: bool
    source_tier: str | None


class Need(_M):
    kind: str
    text: str


class CaseDetail(CaseCard):
    kpis: list[Kpi]
    needs: list[Need]
    spaces: list[IdName] = Field(default_factory=list, description="추가 — 사례 공간(deployment_space)")


class AppliedVertical(_M):
    id: str
    name: str
    from_: Literal["user", "task", "inferred"] = Field(alias="from")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Applied(_M):
    vertical: AppliedVertical | None


class CaseSearchOut(ListPage):
    corpus: Corpus
    applied: Applied
    items: list[CaseCard]
    total: int = Field(description="추가 — 조건에 맞는 전체 건수")


class BodyMention(_M):
    id: str
    title: str
    date: str | None
    url: str | None


class SolutionCases(_M):
    corpus: Corpus
    total: int
    title_explicit: list[CaseCard]
    body_mentions: list[BodyMention]


# ── 솔루션 ────────────────────────────────────────────────

class SolutionItem(_M):
    id: str
    name: str
    domain: str
    desc: str
    icon: str
    template_code: str | None
    kb_id: str | None
    industries: list[str]
    kb_ids: list[str] = Field(default_factory=list, description="추가 — 대응하는 KB 솔루션 전부(SAC 제어 = 3개)")
    kb_match: str | None = Field(None, description="추가 — full · partial · none")


class SolutionList(ListPage):
    items: list[SolutionItem]


class Purchase(_M):
    site_code: str | None
    label: str


class DeviceExample(_M):
    family_id: str
    series_label: str
    model_code: str
    display_name: str


class SupportedDevices(_M):
    label: str
    example: DeviceExample | None
    family_ids: list[str] = Field(default_factory=list, description="추가 — 이 솔루션을 제품 페이지에서 언급한 제품군 전부")


class Pillar(_M):
    name: str
    items: list[str]


class Part(_M):
    name: str
    does: str


class DeployEvidence(_M):
    deployment_id: str
    title: str | None
    date: str | None


class Deploy(_M):
    name: str
    desc: str
    evidence: DeployEvidence | None


class SolutionProfile(_M):
    intro: str
    pillars: list[Pillar]
    parts: list[Part]
    deploy: list[Deploy]
    device_functions: list[str]
    source_note: str


class Message(_M):
    level: str
    text: str
    children: list[str]
    source_url: str | None = None
    claim_flag: bool = False
    basis: str | None = Field(None, description="추가 — text_match 면 KB 에 솔루션 id 가 없어 이름 글자 일치로 찾은 문장(확인 필요)")


class SolutionDetail(_M):
    id: str
    name: str
    version_label: str | None
    category_path: list[str]
    subtitle: str | None
    key_chips: list[str]
    purchase: Purchase | None
    quote_url: str | None
    intro_url: str | None
    supported_devices: SupportedDevices | None
    profile: SolutionProfile | None
    messages: list[Message]
    verified_at: str | None
    counts: DetailCounts
    kb_id: str | None = None
    kb_ids: list[str] = Field(default_factory=list)
    template_code: str | None = None
    proposal_templates: dict[str, Any] | None = Field(None, description="추가 — 10-proposal 부록 B(전용 템플릿 설명 · 업종 버전)")
    gaps: list[str] = Field(default_factory=list, description="추가 — 이 솔루션에 비어 있는 데이터(갭 코드)")


class ImageGroup(_M):
    key: Literal["official", "context", "case"] = Field(description="official 솔루션 페이지 · context(추가) 공간 · 업종 페이지에서 솔루션이 나오는 이미지 · case 도입사례 사진")
    label: str
    source_label: str
    items: list[ImageMeta]


class SolutionImages(_M):
    groups: list[ImageGroup]
    total: int


class ImageSearchCounts(_M):
    all: int
    official: int
    case: int


class ImageSearchOut(ListPage):
    counts: ImageSearchCounts
    items: list[ImageCard]


# ── 업종 ─────────────────────────────────────────────────

class VerticalItem(_M):
    id: str
    name: str
    parent_id: str | None
    scheme: str = Field(description="추가 — kr_site · us_site · winmate16")
    code: str | None = Field(None, description="추가 — winmate16: 16업종 코드(FB …)")
    full: str | None = None
    short: str | None = None
    kb_name: str | None = Field(None, description="추가 — winmate16: KB 이름(name 은 SectionStep 이름)")
    kr_vertical_ids: list[str] = Field(default_factory=list)
    us_vertical_ids: list[str] = Field(default_factory=list)
    mapping_status: str | None = None
    url: str | None = None


class VerticalList(ListPage):
    items: list[VerticalItem]
