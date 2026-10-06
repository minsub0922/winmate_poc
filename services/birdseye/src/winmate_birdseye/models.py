"""birdseye 요청 · 응답 모델 = contracts/birdseye.json (08-birdseye §5 · §6).

좌표: 단위 m, 평면 x → 오른쪽, y → 아래(화면 기준, 위 = 정면 쪽), 원점 = 외곽 bbox 왼쪽 위(§5.2).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SpaceChip = Literal["store_lobby", "meeting_office", "classroom", "hospital_waiting", "hotel_room", "control_room"]
WorkStatus = Literal["in_progress", "needs_check", "done", "failed"]
Tone = Literal["warm_wood", "modern_white", "dark_metal"]
DefaultView = Literal["aerial45", "entrance"]
ViewPreset = Literal["aerial45", "entrance", "product_front", "top", "custom"]
Light = Literal["day", "evening", "night"]
ZoneLayout = Literal["ZP-A", "ZP-B", "ZP-C"]
CutStatus = Literal["queued", "running", "draft", "done", "check", "failed", "canceled"]


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


class JobAccepted(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"


class Chip(BaseModel):
    label: str
    kind: Literal["area", "feature", "column", "fact", "estimate", "file"] = "feature"
    estimated: bool = False


# ── 공간 모델(§5.2) ──────────────────────────────────────

class Room(BaseModel):
    id: str
    label: str = ""
    space_types: list[str] = Field(default_factory=list)
    outline: list[list[float]] = Field(description="[[x, y], …] 시계 방향(화면 기준)")


class Wall(BaseModel):
    id: str
    a: list[float]
    b: list[float]
    thickness: float = 0.2
    kind: Literal["exterior", "interior"] = "exterior"
    label: str = Field("", description="정면 · 후면 · 왼쪽 · 오른쪽 · 상황판 벽 …")
    dim_known: bool = Field(False, description="도면 치수 · 사용자 값으로 폭을 안다(모르면 크기 옵션은 가장 큰 것 + 가정)")
    room_id: str | None = None


class Opening(BaseModel):
    id: str
    kind: Literal["window", "door", "opening"]
    wall_id: str
    offset: float = Field(description="벽 a 점에서 개구부 시작까지(m)")
    width: float
    label: str = ""
    faces_outdoor: bool = False
    door_type: Literal["main", "emergency", "backoffice", "normal", "unknown"] | None = None
    confidence: float | None = None
    is_main: bool = False
    assumed: bool = Field(False, description="되묻기에 답하지 않아 안전 기본값(출입 가능한 문)으로 처리")


class Column(BaseModel):
    id: str
    center: list[float]
    w: float = 0.6
    d: float = 0.6
    label: str = ""


class Core(BaseModel):
    id: str
    polygon: list[list[float]]
    kinds: list[str] = Field(default_factory=list, description="ev · stairs · toilet · shaft")


class PowerPoint(BaseModel):
    id: str
    pos: list[float]
    source: Literal["plan", "user", "default"] = "user"


class CeilingH(BaseModel):
    value: float
    estimated: bool = True


class Scale(BaseModel):
    ratio: float | None = None
    source: Literal["pdf_text", "dimension", "photo_estimate", "default", "description", "user"] = "default"
    correction: float = 1.0


class Dim(BaseModel):
    id: str
    label: str
    wall_id: str | None = None
    annotated_m: float | None = None
    computed_m: float | None = None
    choice: Literal["annotated", "computed", "manual"] = "annotated"
    manual_m: float | None = None
    answered: bool = False
    asked: bool = Field(False, description="표기 · 환산 차가 1% 를 넘어 되묻는 항목")


class Feature(BaseModel):
    kind: str = Field(description="storefront_window · columns · glass_wall · stage · counter · …")
    label: str
    count: int | None = None
    hint_cap: str | None = Field(None, description="KB C1 역량 id(cap_sunlight_readable …)")
    cap_label: str | None = Field(None, description="W 권장 문구(「고휘도 권장」)")


class Assumption(BaseModel):
    kind: str = Field(description="dims_missing · door_unknown · dim_default · area_estimate · ceiling_estimate · photo_estimate")
    ref: str | None = None
    text_ko: str
    action: str | None = Field(None, description="되돌아갈 화면(BE1D · BE1P)")


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: str
    n: int
    kind: Literal["dim", "door"]
    ref: str
    title: str = Field(description="「치수 보정 · 정면 폭」 · 「뒤쪽 문은 어떤 문인가요?」")
    sub: str | None = Field(None, description="「도면 표기 24.0 m · 축척 1:100 환산 23.6 m」")
    options: list[QuestionOption] = Field(default_factory=list)
    answered: bool = False
    answer: str | None = None
    manual_m: float | None = None


class SpaceModel(BaseModel):
    rooms: list[Room] = Field(default_factory=list)
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    columns: list[Column] = Field(default_factory=list)
    cores: list[Core] = Field(default_factory=list)
    power_points: list[PowerPoint] = Field(default_factory=list)
    ceiling_h: CeilingH = Field(default_factory=lambda: CeilingH(value=3.0, estimated=True))
    scale: Scale = Field(default_factory=Scale)
    dims: list[Dim] = Field(default_factory=list)
    area_m2: float = 0.0
    features: list[Feature] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    facts: list[str] = Field(default_factory=list, description="사진 · 설명에서 뽑은 사실 칩(「상황판 벽 폭 약 9 m」)")
    estimated: bool = True
    source: Literal["description", "plan", "photos", "mixed"] = "description"
    meta_paths: list[str] = Field(default_factory=list, description="쓴 대체 경로(space:regex · plan:vector_only …)")


# ── 작업(§5.1) ───────────────────────────────────────────

class Origin(BaseModel):
    service: str = "birdseye"
    ref: str | None = None
    label: str | None = None
    return_to: str | None = Field(None, description="돌아갈 웹 경로(제안서 PRS3 · 시나리오)")


class Inputs(BaseModel):
    description: bool = False
    plan_file_ids: list[str] = Field(default_factory=list)
    photo_count: int = 0


class PrefillProduct(BaseModel):
    family_id: str | None = None
    model_code: str | None = None
    label: str | None = None
    qty: int | None = None


class Prefill(BaseModel):
    products: list[str | PrefillProduct] = Field(default_factory=list, description="family_id 문자열 또는 {family_id, model_code, label, qty}")
    reference_image_version: str | None = Field(None, description="image 버전 id(imv_…) — 렌더 분위기 참조")


class ReferenceImage(BaseModel):
    version_id: str
    url: str | None = None
    thumb_url: str | None = None
    label: str = "참조 이미지"


class Birdseye(BaseModel):
    id: str
    owner: str
    owner_name: str = ""
    project_id: str | None = None
    customer_name: str | None = None
    title: str
    space_label: str = ""
    space_chip: SpaceChip = "store_lobby"
    space_types: list[str] = Field(default_factory=list)
    description: str = ""
    area_input_pyeong: float | None = None
    ceiling_input_m: float | None = None
    inputs: Inputs = Field(default_factory=Inputs)
    step: int = Field(1, ge=1, le=5)
    status: WorkStatus = "in_progress"
    status_reason: str | None = Field(None, description="확인 필요 사유 줄(「사진 1장 다시 찍기 · 1/5 공간 입력」)")
    check_route: str | None = None
    tone: Tone = "warm_wood"
    default_view: DefaultView = "aerial45"
    version: int = Field(1, description="저장 버전(「저장」 v{n} · 내보내기 파일 이름)")
    rev: int = Field(1, description="문서 수정 번호 — PATCH if_version 비교")
    layout_version: int = 0
    primary_cut_id: str | None = None
    shared_scope: Literal["private", "team"] = "private"
    shared_label: str | None = None
    cloned_from: str | None = None
    origin: Origin | None = None
    zone_layout: ZoneLayout = "ZP-A"
    route: str
    reference_image: ReferenceImage | None = None
    prefill_products: list[PrefillProduct] = Field(default_factory=list)
    analyzing_job_id: str | None = None
    created_at: str
    updated_at: str


class BirdseyeCreate(BaseModel):
    title: str | None = None
    space_chip: SpaceChip | None = None
    description: str | None = Field(None, max_length=1000)
    area_pyeong: float | None = Field(None, gt=0)
    ceiling_m: float | None = None
    project_id: str | None = None
    customer_name: str | None = None
    origin: Origin | None = None
    prefill: Prefill | None = None


class BirdseyePatch(BaseModel):
    title: str | None = None
    customer_name: str | None = None
    space_chip: SpaceChip | None = None
    description: str | None = Field(None, max_length=1000)
    area_pyeong: float | None = None
    ceiling_m: float | None = None
    tone: Tone | None = None
    default_view: DefaultView | None = None
    zone_layout: ZoneLayout | None = None
    shared_scope: Literal["private", "team"] | None = None
    shared_label: str | None = None
    step: int | None = Field(None, ge=1, le=5)
    clear_area: bool = Field(False, description="면적 칸 비우기")
    clear_ceiling: bool = Field(False, description="층고 칸 비우기")
    if_version: int | None = Field(None, description="rev 와 다르면 409 VERSION_CONFLICT")


class UsageRef(BaseModel):
    service: Literal["proposal", "scenario"]
    ref: str
    label: str = ""
    version: int | None = None
    route: str | None = None


class RowAction(BaseModel):
    label: Literal["열기", "이어서", "확인"]
    route: str


class RunningCut(BaseModel):
    cut_id: str
    label: str = Field(description="「야간 시점 추가 생성 중」")
    route: str
    progress: float = 0


class BirdseyeRow(BaseModel):
    id: str
    title: str
    subtitle: str = Field(description="「{고객사} · {공간 라벨}」")
    customer_name: str | None = None
    space_label: str = ""
    thumb_url: str | None = None
    input_chips: list[str] = Field(default_factory=list, description="「설명」 「도면」 「사진 {n}장」")
    status: WorkStatus
    step: int
    step_label: str
    status_title: str = Field(description="「완료」 · 「4/5」 · 「확인 필요」 · 「실패」")
    status_line: str = Field("", description="「시점 3 · 존 포인트 4」 · 「배치 · 인테리어 컨펌」 · 사유 줄")
    running: RunningCut | None = None
    usages: list[UsageRef] = Field(default_factory=list)
    action: RowAction
    route: str
    updated_at: str
    created_at: str
    views_count: int = 0
    zones_count: int = 0
    zone_count: int = Field(0, description="= zones_count(시나리오 SC1 · SC1B 「존 {n}」)")
    version: int = Field(1, description="저장 버전")
    layout_version: int = 0
    furniture_kinds: int = 0
    products_line: str = Field("", description="「{제품 요약} · 가구 {k}종」")
    shared_scope: Literal["private", "team"] = "private"
    shared_label: str | None = None
    team_meta: str = Field("", description="「{팀} 공유 · 시점 {v} · 존 포인트 {z}」")
    owner: str
    owner_name: str = ""
    done: bool = False
    primary_cut_url: str | None = None


class Counts(BaseModel):
    all: int = 0
    in_progress: int = 0
    needs_check: int = 0
    done: int = 0


class BirdseyeList(BaseModel):
    items: list[BirdseyeRow]
    counts: Counts
    next_cursor: str | None = None
    total: int = 0


class VersionInfo(BaseModel):
    version: int
    layout_version: int
    updated_at: str
    zones_hash: str
    rev: int = 1


class CloneIn(BaseModel):
    title: str | None = None


class CloneOut(BaseModel):
    id: str
    route: str


class SaveOut(BaseModel):
    version: int
    created: bool = True


class SavedVersion(BaseModel):
    version: int
    created_at: str
    layout_version: int = 0
    note: str | None = None


class SavedVersionList(BaseModel):
    items: list[SavedVersion]


# ── 공간 입력(§6.2) ──────────────────────────────────────

class InputFile(BaseModel):
    file_id: str
    name: str
    kind: Literal["plan", "photo"]
    route: str | None = None


class SpaceView(BaseModel):
    model: SpaceModel | None = None
    summary_chips: list[Chip] = Field(default_factory=list)
    w_message: str
    features_text: str = ""
    space_name: str = Field("", description="W 문장의 공간 이름(「로비」 「관제실」)")
    analyzing: bool = False
    job_id: str | None = None
    version: int = 0
    echo: str = ""
    files: list[InputFile] = Field(default_factory=list)


class AttachIn(BaseModel):
    file_ids: list[str] = Field(min_length=1, max_length=20)


class AttachItem(BaseModel):
    file_id: str
    name: str = ""
    kind: Literal["plan", "photo"]
    plan_id: str | None = None
    photo_id: str | None = None
    job_id: str


class AttachOut(BaseModel):
    items: list[AttachItem]
    route: str = Field(description="도면이 있으면 BE1D(먼저), 사진만 있으면 BE1P")


class PlanAdd(BaseModel):
    file_id: str
    page: int = Field(1, ge=1)


class PlanRecognizeIn(BaseModel):
    page: int | None = Field(None, ge=1, description="쪽 바꾸기(없으면 같은 쪽 다시 인식)")


class NlEditAccepted(BaseModel):
    job_id: str
    status: Literal["queued"] = "queued"


class PlanAccepted(BaseModel):
    job_id: str
    plan_id: str
    status: Literal["queued"] = "queued"


class PlanElement(BaseModel):
    key: Literal["wall", "window", "door", "column", "core"]
    label: str
    summary: str
    question_n: int | None = None


class PlanView(BaseModel):
    id: str
    birdseye_id: str
    file_id: str
    file_name: str = ""
    file_meta: str = Field("", description="「1쪽 · 2.4 MB」")
    page: int = 1
    pages: int = 1
    kind: Literal["vector_pdf", "raster"] | None = None
    status: Literal["recognizing", "recognized", "failed"]
    stage_label: str = ""
    job_id: str | None = None
    scale_label: str = Field("", description="「축척 1:100 감지 · 면적 396 ㎡ (약 120평)」")
    area_m2: float = 0
    elements: list[PlanElement] = Field(default_factory=list)
    head: str = Field("", description="「5종 · 확인 2」")
    questions: list[Question] = Field(default_factory=list)
    check_count: int = 0
    w_message: str = ""
    notices: list[str] = Field(default_factory=list)
    meta_paths: list[str] = Field(default_factory=list)
    page_image_url: str | None = None
    page_box: list[float] | None = Field(None, description="원본 쪽 그림에서 공간 외곽이 차지하는 범위 [x0, y0, x1, y1] 0..1 (겹쳐 보기)")
    error: str | None = None
    model: SpaceModel | None = None


class PlanList(BaseModel):
    items: list[PlanView]


class AnswerIn(BaseModel):
    question_id: str | None = None
    option: Literal["emergency", "backoffice", "wall", "main", "normal"] | None = None
    dim_id: str | None = None
    choice: Literal["annotated", "computed", "manual"] | None = None
    manual_m: float | None = Field(None, gt=0)


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class PhotoAdd(BaseModel):
    file_id: str
    replace_photo_id: str | None = None
    is_ceiling: bool = False


class PhotoAccepted(BaseModel):
    job_id: str
    photo_id: str
    status: Literal["queued"] = "queued"


class PhotoQuality(BaseModel):
    mean: float = 0
    bright_ratio: float = 0
    rest_mean: float = 0
    lap_var: float = 0


class Photo(BaseModel):
    id: str
    birdseye_id: str
    file_id: str
    n: int
    wall_label: str | None = None
    dir_slot: str | None = Field(None, description="1..4 · ceiling")
    status: Literal["recognizing", "recognized", "backlit", "dark", "blurry", "failed", "accepted"]
    status_label: str = Field(description="「인식 완료 · 벽 · 상황판」 · 「역광 · 창 위치가 흐려요」 …")
    needs_check: bool = False
    stage_label: str | None = None
    quality: PhotoQuality = Field(default_factory=PhotoQuality)
    found: list[str] = Field(default_factory=list)
    is_ceiling: bool = False
    ceiling_h_m: float | None = None
    job_id: str | None = None
    url: str
    thumb_url: str
    created_at: str


class PhotoCounts(BaseModel):
    total: int = 0
    recognized: int = 0
    check: int = 0
    recognizing: int = 0
    failed: int = 0


class PhotoSet(BaseModel):
    items: list[Photo]
    counts: PhotoCounts
    head: str = Field("", description="「인식 완료 2 · 확인 필요 1 · 인식 중 1」")
    dir_count: int = 0
    dir_label: str = Field("", description="「4 / 4」")
    has_ceiling: bool = False
    ceiling_label: str = Field("", description="「없음 · 층고는 추정값」 · 「있음 · 층고 3.2 m」")
    basis_count: int = 0
    summary_chips: list[Chip] = Field(default_factory=list)
    w_message: str = ""
    echo: str = ""
    can_continue: bool = False
    max_photos: int = 12


class PhotoPatch(BaseModel):
    accept: bool = True


class FactsOut(BaseModel):
    facts: list[str]
    model: SpaceModel


class UploadToken(BaseModel):
    token: str
    url: str
    path: str
    expires_at: str
    qr: list[str] | None = Field(None, description="QR 모듈 행(\"0101…\") — 없으면 주소만")


class UploadTokenInfo(BaseModel):
    token: str
    valid: bool
    expires_at: str
    title: str = ""
    photo_count: int = 0


class TokenPhotoIn(BaseModel):
    file_id: str


class UploadTokenPrincipal(BaseModel):
    """게이트웨이 전용(internal) — valid=false 면 나머지는 비어 있다."""
    valid: bool
    owner: str | None = None
    owner_name: str | None = None
    birdseye_id: str | None = None
    expires_at: str | None = None


# ── 제품 · 가구(§6.3) ────────────────────────────────────

class ProductSearchItem(BaseModel):
    family_id: str
    model_code: str | None = None
    ref: str = Field(description="kb:family:fam_… · kb:model:mdl_…")
    kind: Literal["model", "family"] = "family"
    name: str
    name_match: list[int] | None = Field(None, description="name 안에서 검색어와 맞은 [시작, 끝)")
    subline: str = Field(description="「{카테고리} · {크기 옵션 ' / '} · {핵심 특징}」")
    size_options: list[str] = Field(default_factory=list)
    thumb_url: str | None = None


class ProductSearch(BaseModel):
    items: list[ProductSearchItem]


class ProductPick(BaseModel):
    family_id: str | None = None
    model_code: str | None = None
    ref: str | None = None
    label: str | None = None


class ProductsPut(BaseModel):
    items: list[ProductPick]


class Dims3(BaseModel):
    w: float
    h: float
    d: float


class ProductItem(BaseModel):
    id: str
    birdseye_id: str
    family_id: str
    model_code: str | None = None
    ref: str
    display_name: str = Field(description="정식 표시명(「Outdoor Signage OH55C」)")
    short: str = Field(description="약칭(「OH55C」 · 「The Wall IAB」)")
    size_options: list[str] = Field(default_factory=list)
    chosen_size: str | None = None
    dims_m: Dims3 | None = None
    dims_source: Literal["spec", "computed", "estimated"] = "estimated"
    diag_inch: float | None = None
    category: str = ""
    role: Literal["window_signage", "led_wall", "display", "interactive", "kiosk", "other"] = "display"
    mount_default: Literal["wall", "floor", "ceiling", "column", "window_facing"] = "wall"
    order: int = 0
    models_by_size: dict[str, str] = Field(default_factory=dict)
    dims_by_size: dict[str, Dims3] = Field(default_factory=dict)


class ProductsView(BaseModel):
    items: list[ProductItem]
    w_message: str = ""
    chips: list[Chip] = Field(default_factory=list)
    echo: str = ""
    files: list[InputFile] = Field(default_factory=list)
    analyzing: bool = False


class FurnitureItem(BaseModel):
    id: str
    birdseye_id: str
    catalog_code: str | None = None
    name: str
    short: str = ""
    tiny: str = ""
    qty: int = 1
    rows: int | None = None
    reason: str = ""
    source: Literal["recommended", "user", "custom"] = "recommended"
    dims_m: Dims3
    dims_estimated: bool = False
    selected: bool = True
    rec_rank: int | None = None
    chip_label: str = Field("", description="「기둥 랩핑 프레임 ×2」 · 「안내 로봇 · 치수 추정」")


class FurnitureCard(BaseModel):
    code: str
    name: str
    reason: str
    rank: int
    selected: bool = False
    qty: int = 1
    rows: int | None = None
    item_id: str | None = None


class FurnitureView(BaseModel):
    cards: list[FurnitureCard] = Field(default_factory=list)
    selected: list[FurnitureItem] = Field(default_factory=list)
    shown_codes: list[str] = Field(default_factory=list)
    w_message: str = ""
    echo: str = ""
    running: bool = False
    job_id: str | None = None
    none: bool = Field(False, description="가구 없이 진행을 골랐다")
    more_available: bool = True


class FurnitureRecommendIn(BaseModel):
    exclude: list[str] = Field(default_factory=list)


class FurniturePick(BaseModel):
    id: str | None = None
    catalog_code: str | None = None
    name: str | None = None
    qty: int | None = Field(None, ge=1, le=99)
    rows: int | None = Field(None, ge=1, le=10)
    selected: bool = True


class FurniturePut(BaseModel):
    items: list[FurniturePick] = Field(default_factory=list)
    none: bool = False
    replace: bool = Field(True, description="true 면 목록을 통째로(빠진 항목은 선택 해제), false 면 더하기")


# ── 레이아웃(§5.3 · §6.4) ────────────────────────────────

class Anchor(BaseModel):
    type: str = Field(description="wall · window · column · faces · near · entrance · area · free")
    target: str | None = None
    label: str = ""


class LayoutItem(BaseModel):
    id: str
    kind: Literal["product", "furniture", "column_wrap"]
    ref: str = Field(description="bpi_… · bfi_…")
    group_id: str
    label: str
    short: str = ""
    tiny: str = ""
    x: float
    y: float
    rot_deg: float = 0
    w: float
    d: float
    h: float
    z: float = 0
    mount: Literal["wall", "floor", "ceiling", "column", "window_facing"] = "floor"
    anchor: Anchor = Field(default_factory=lambda: Anchor(type="free"))
    qty_in_group: int = 1
    qty_source: Literal["rule", "user", "suggested", "default"] = "default"
    rule_id: str | None = None
    faces: str | None = None
    seats: int = 0
    seat_points: list[list[float]] = Field(default_factory=list)
    locked: bool = False
    unplaced: bool = False
    role: str | None = None
    diag_inch: float | None = None
    parts: list[dict[str, Any]] = Field(default_factory=list)


class LayoutGroup(BaseModel):
    id: str
    kind: Literal["product", "furniture", "column_wrap"]
    ref: str
    label: str = Field(description="「OH55C ×3」 · 「관람 벤치 3열」 · 「기둥 랩핑 ×2」")
    plan_label: str = Field("", description="배치안 라벨(「OH55C ×3 (창면)」 「The Wall IAB 146\" (후면 벽)」)")
    at_label: str = Field("", description="수량표 위치(「쇼윈도 창면」)")
    anchor_label: str = ""
    family_id: str | None = None
    model_code: str | None = None
    qty: int = 1
    qty_source: Literal["rule", "user", "suggested", "default"] = "default"
    rule_id: str | None = None
    item_ids: list[str] = Field(default_factory=list)
    short: str = ""
    tiny: str = ""
    size: str | None = None


class WarningFix(BaseModel):
    id: str
    label_ko: str
    ops: list[dict[str, Any]]


class LayoutWarning(BaseModel):
    id: str
    n: int
    kind: Literal["viewing_angle", "viewing_distance", "walkway", "power", "mount_height", "unplaced"]
    title_ko: str
    rule_id: str
    expr: str
    params: dict[str, Any] = Field(default_factory=dict)
    param_status: str = "draft"
    tooltip: str = Field("", description="「pr_warn_power_distance · distance_to_power_m > 3.0 (draft)」")
    message_ko: str
    subjects: list[str] = Field(default_factory=list)
    fixes: list[WarningFix] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list, description="fix · ignore · memo · add_power")
    status: Literal["open", "fixed", "ignored", "memo"] = "open"
    key: str = Field("", description="같은 경고를 다시 알아보는 키(종류 + 대상)")
    marker: list[float] | None = Field(None, description="배치안 위 번호 표식 위치[x, y]")
    value: float | None = None


class Layout(BaseModel):
    version: int
    items: list[LayoutItem] = Field(default_factory=list)
    groups: list[LayoutGroup] = Field(default_factory=list)
    warnings: list[LayoutWarning] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    memos: list[str] = Field(default_factory=list)
    power_points: list[PowerPoint] = Field(default_factory=list)
    engine_version: str = "be-engine/1"
    created_by: Literal["engine", "user", "nl_edit", "clone", "restore"] = "engine"
    parent_version: int | None = None
    created_at: str | None = None


class ViewFan(BaseModel):
    item_id: str
    apex: list[float]
    dir_deg: float
    half_angle_deg: float
    min_d: float
    max_d: float


class WalkPath(BaseModel):
    target: str
    points: list[list[float]]


class Bottleneck(BaseModel):
    pos: list[float]
    width: float
    a: str
    b: str


class PowerLink(BaseModel):
    group_id: str
    a: list[float]
    b: list[float] | None = None
    d: float | None = None


class Overlays(BaseModel):
    fans: list[ViewFan] = Field(default_factory=list)
    paths: list[WalkPath] = Field(default_factory=list)
    bottlenecks: list[Bottleneck] = Field(default_factory=list)
    power_links: list[PowerLink] = Field(default_factory=list)
    entrance: list[float] | None = None


class PlanGeometry(BaseModel):
    width_m: float
    height_m: float
    rooms: list[Room] = Field(default_factory=list)
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    columns: list[Column] = Field(default_factory=list)
    cores: list[Core] = Field(default_factory=list)
    power_points: list[PowerPoint] = Field(default_factory=list)
    area_label: str = Field("", description="「120평 · 4.5m」")
    window_label: str | None = None


class LayoutView(BaseModel):
    layout: Layout | None = None
    plan: PlanGeometry | None = None
    overlays: Overlays = Field(default_factory=Overlays)
    w_message: str = ""
    open_warnings: int = 0
    running: bool = False
    job_id: str | None = None
    tone: Tone = "warm_wood"
    default_view: DefaultView = "aerial45"


class Op(BaseModel):
    model_config = ConfigDict(extra="allow")
    op: Literal["move", "rotate", "add", "remove", "set_qty", "add_power", "set_size", "set_pos"]
    item: str | None = None
    group: str | None = None
    product: str | None = None
    dx: float | None = None
    dy: float | None = None
    deg: float | None = None
    qty: int | None = None
    pos: list[float] | None = None
    size: str | None = None
    spec: dict[str, Any] | None = Field(None, description="add — {kind, ref, w, d, h, x, y, rot_deg, label}")


class ValidateIn(BaseModel):
    base_version: int | None = None
    ops: list[Op] = Field(default_factory=list)


class ValidateOut(BaseModel):
    items: list[LayoutItem]
    groups: list[LayoutGroup] = Field(default_factory=list)
    warnings: list[LayoutWarning]
    assumptions: list[Assumption] = Field(default_factory=list)
    overlays: Overlays = Field(default_factory=Overlays)
    elapsed_ms: float = 0


class SessionCreated(BaseModel):
    session_id: str
    base_version: int


class MoveMark(BaseModel):
    item_id: str
    group_id: str
    from_x: float
    from_y: float
    dx: float
    dy: float
    label_ko: str
    w: float = 0
    d: float = 0
    rot_deg: float = 0


class SessionView(BaseModel):
    session_id: str
    birdseye_id: str
    base_version: int
    status: Literal["open", "committed", "discarded"]
    layout: Layout
    plan: PlanGeometry | None = None
    warnings: list[LayoutWarning]
    open_warnings: int = 0
    changes_count: int = 0
    can_undo: bool = False
    can_redo: bool = False
    moves: list[MoveMark] = Field(default_factory=list)
    overlays: Overlays = Field(default_factory=Overlays)


class OpsIn(BaseModel):
    ops: list[Op] = Field(default_factory=list)
    undo: bool = False
    redo: bool = False


class WarningActionIn(BaseModel):
    action: Literal["fix", "ignore", "memo", "add_power"]
    fix_id: str | None = None
    pos: list[float] | None = None


class CommitOut(BaseModel):
    layout_version: int
    changes_count: int = 0


class LayoutNlEditIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    session_id: str | None = None


class LayoutGenerateIn(BaseModel):
    none: bool = Field(False, description="가구 없이 진행")


# ── 컷(§6.5) ─────────────────────────────────────────────

class Camera(BaseModel):
    pos: list[float]
    target: list[float]
    fov_deg: float = 40
    ortho: bool = False
    ortho_w: float | None = None


class ViewSpec(BaseModel):
    preset: ViewPreset | None = None
    target_item_id: str | None = None
    custom_text: str | None = Field(None, max_length=300)


class CutView(BaseModel):
    preset: ViewPreset
    target_item_id: str | None = None
    camera: Camera | None = None
    label: str
    custom_text: str | None = None
    meta_path: str | None = Field(None, description="camera:rules · camera:llm")


class CutsCreate(BaseModel):
    views: list[ViewSpec] = Field(min_length=1)
    lights: list[Light] = Field(default_factory=lambda: ["day"])
    before: bool = False
    tone: Tone | None = None
    primary: bool = Field(False, description="BE4 「이 배치로 3D 생성」 — 주 컷")
    auto_extra: bool = Field(False, description="첫 렌더 때 야간 · 도입 전 컷 자동 예약(§7.8)")


class CutsAccepted(BaseModel):
    cut_ids: list[str]
    job_ids: list[str]
    job_id: str | None = None
    route: str | None = None
    skipped: int = 0


class CutStep(BaseModel):
    stage: Literal["structure", "products", "furniture", "render", "qc"]
    label: str
    note: str = ""
    state: Literal["done", "run", "wait"] = "wait"


class Cut(BaseModel):
    id: str
    birdseye_id: str
    layout_version: int
    view: CutView
    light: Light = "day"
    before: bool = False
    tone: Tone = "warm_wood"
    status: CutStatus
    stale: bool = False
    progress: float = 0
    eta_s: float | None = None
    stage: str | None = None
    steps: list[CutStep] = Field(default_factory=list)
    job_id: str | None = None
    render_id: str | None = None
    image_id: str | None = None
    version_id: str | None = None
    draft_file_id: str | None = Field(None, description="draft_v0(마감재 적용 전)")
    draft_v1_file_id: str | None = None
    draft_url: str | None = None
    image_url: str | None = None
    display_url: str | None = Field(None, description="화면 표시용(FHD 렌디션 — 없으면 image_url). 내려받기는 image_url(원본)")
    thumb_url: str | None = None
    renditions: list[dict[str, Any]] = Field(default_factory=list)
    resolution: str = "3840×2160"
    auto_queued: bool = False
    is_primary: bool = False
    queue_pos: int | None = None
    label: str = Field(description="「조감 45° · 야간」 · 「도입 전 · 조감 45° (비교용)」")
    thumb_label: str = Field("", description="썸네일 라벨(주 시점과 다르면 시점, 조명만 다르면 조명)")
    render_path: str | None = Field(None, description="render:ref|edit|text|draft_only")
    badge: str | None = Field(None, description="「초안 렌더」")
    qc: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    edit_pending_text: str | None = Field(None, description="진행 중 요청을 편집으로 못 반영했을 때 수정 요청 칸에 채울 글")
    notice: str | None = None
    created_at: str
    finished_at: str | None = None


class CutPatch(BaseModel):
    is_primary: bool = True


class ResultEditIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    cut_id: str | None = None


class ResultEditOut(BaseModel):
    route_hint: Literal["render", "layout", "view", "mixed", "ask"]
    job_id: str | None = None
    cut_id: str | None = None
    route: str | None = None
    question: str | None = Field(None, description="모호할 때 W 가 한 번 되묻는 말(route_hint='ask')")
    cut_ids: list[str] = Field(default_factory=list)
    notice: str | None = None


# ── 존 포인트(§6.6) ──────────────────────────────────────

class ZoneLink(BaseModel):
    kind: Literal["product", "feature", "need", "scene"]
    label: str
    ref: str | None = None


class ZoneProduct(BaseModel):
    family_id: str | None = None
    model_code: str | None = None
    label: str = Field(description="정식 표시명(「Outdoor Signage OH55C」)")
    short: str = Field("", description="약칭(「OH55C」)")
    qty: int = 1
    group_label: str = Field("", description="배치안 묶음 라벨(「OH55C ×3」)")


class ZoneFurniture(BaseModel):
    name: str
    qty: int = 1


class ZonePoint(BaseModel):
    id: str
    birdseye_id: str
    n: int
    name: str
    text: str
    links: list[ZoneLink] = Field(default_factory=list)
    anchor_m: list[float]
    cluster_item_ids: list[str] = Field(default_factory=list)
    positions: dict[str, list[float]] = Field(default_factory=dict, description="{cut_id: [u, v]} 0..1")
    u: float | None = None
    v: float | None = None
    status: Literal["active", "suggested", "dismissed"] = "active"
    path_order: int | None = None
    kind: Literal["product", "furniture", "empty"] = "product"
    products: list[ZoneProduct] = Field(default_factory=list)
    short_name: str = ""
    meta_path: str | None = None


class ZoneSuggestion(BaseModel):
    id: str
    title: str = Field(description="「W 제안 · 기둥 랩핑 길 안내」")
    question: str = Field(description="「기둥 2개를 5번 포인트로 넣을까요?」")
    add_label: str = Field(description="「5번으로 추가」")
    n: int


class ZonePreview(BaseModel):
    code: ZoneLayout
    layout_label: str = Field(description="「번호 콜아웃」")
    count: int
    line: str = Field(description="「ZP-A 번호 콜아웃 · 포인트 4곳」")


class ZonesView(BaseModel):
    points: list[ZonePoint]
    suggestions: list[ZoneSuggestion] = Field(default_factory=list)
    preview: ZonePreview
    cut_id: str | None = None
    cut_label: str = ""
    cut_url: str | None = None
    w_message: str = ""
    running: bool = False
    job_id: str | None = None
    proposal_label: str | None = Field(None, description="연결된 제안서 제목(없으면 「연결된 제안서 없음」)")


class ZonesAutoIn(BaseModel):
    cut_id: str | None = None


class ZoneCreate(BaseModel):
    cut_id: str | None = None
    u: float | None = Field(None, ge=0, le=1)
    v: float | None = Field(None, ge=0, le=1)
    from_suggestion: str | None = None


class ZonePatch(BaseModel):
    name: str | None = Field(None, max_length=14)
    text: str | None = Field(None, max_length=60)
    links: list[ZoneLink] | None = None
    u: float | None = Field(None, ge=0, le=1)
    v: float | None = Field(None, ge=0, le=1)
    cut_id: str | None = None
    status: Literal["active", "suggested", "dismissed"] | None = None


class ZonesRewriteIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    zone_ids: list[str] | None = None


# ── 내보내기 · 넘기기(§6.7 · §8) ─────────────────────────

class ExportItemRef(BaseModel):
    kind: Literal["cut", "before_after", "zones_callout"]
    ref: str | None = None


class ExportCreate(BaseModel):
    items: list[ExportItemRef] | None = Field(None, description="없으면 기본 선택(BE6), [] 이면 수량표만")
    format: Literal["png", "jpg", "pdf"] = "png"
    size: Literal["original", "fhd"] = "original"
    include_furniture: bool = True
    filename: str | None = Field(None, max_length=120)


class ExportAccepted(BaseModel):
    job_id: str
    export_id: str
    status: Literal["queued"] = "queued"


class ExportRecord(BaseModel):
    id: str
    birdseye_id: str
    status: Literal["queued", "running", "done", "failed"]
    format: str
    size: str
    filename: str
    include_furniture: bool = True
    items: list[ExportItemRef] = Field(default_factory=list)
    job_id: str | None = None
    file_id: str | None = None
    url: str | None = None
    download_url: str | None = None
    error: str | None = None
    created_at: str


class ExportImageOption(BaseModel):
    kind: Literal["cut", "before_after", "zones_callout"]
    ref: str | None = None
    name: str
    sub: str
    selected: bool = False
    thumb_url: str | None = None


class SheetMapRow(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    from_: str = Field(alias="from")
    to: str
    code: str
    ref: str | None = None
    kind: str = ""


class ExportOptions(BaseModel):
    images: list[ExportImageOption]
    filename_default: str
    mapping: list[SheetMapRow]
    products_count: int = 0
    zones_count: int = 0
    title: str = ""
    version: int = 1
    family_ids: list[str] = Field(default_factory=list)
    spec_products: list[ProductPick] = Field(default_factory=list)


class QuantityRow(BaseModel):
    family_id: str | None = None
    model_code: str | None = None
    name: str
    at: str
    qty: int
    qty_source: str = "default"
    rule_id: str | None = None
    memo: str | None = None
    confirm: bool = Field(False, description="수량 근거가 추정(suggested) → 「확인 필요」")
    source_url: str | None = None


class FurnitureRow(BaseModel):
    label: str = Field(description="「가구 4종 (참고)」")
    at: str = Field(description="「라운지 · 관람 · 안내」")
    qty: int


class FurnitureDetailRow(BaseModel):
    name: str
    at: str
    qty: int
    dims: str = ""
    estimated: bool = False


class Quantities(BaseModel):
    rows: list[QuantityRow]
    furniture_row: FurnitureRow | None = None
    furniture: list[FurnitureDetailRow] = Field(default_factory=list)
    memos: list[str] = Field(default_factory=list)


class HandoffSpace(BaseModel):
    label: str = ""
    space_types: list[str] = Field(default_factory=list)
    area_m2: float | None = None
    area_pyeong: float | None = None
    ceiling_h_m: float | None = None
    features: list[Feature] = Field(default_factory=list)
    estimated: bool = True
    summary: str = Field("", description="「120평 · 층고 4.5m」")


class HandoffCut(BaseModel):
    cut_id: str
    label: str
    view: str
    light: Light
    before: bool = False
    is_primary: bool = False
    stale: bool = False
    image_id: str | None = None
    image_version_id: str | None = None
    renditions: list[dict[str, Any]] = Field(default_factory=list)
    generation: dict[str, Any] = Field(default_factory=dict)
    file_id: str | None = None
    url: str | None = None
    draft_only: bool = False


class HandoffComparison(BaseModel):
    kind: Literal["before_after", "day_night"]
    left: str
    right: str
    composite_file_id: str | None = None


class HandoffZonePoint(BaseModel):
    id: str = Field(description="bez_…")
    zone_id: str
    n: int
    name: str
    short_name: str = ""
    text: str
    links: list[ZoneLink] = Field(default_factory=list)
    u: float | None = None
    v: float | None = None
    x: float | None = None
    y: float | None = None
    kind: Literal["product", "furniture", "empty"] = "product"
    products: list[ZoneProduct] = Field(default_factory=list)
    furniture: list[ZoneFurniture] = Field(default_factory=list)
    subtitle: str = Field("", description="SC1B 부제 「OH55C ×3 · 거리에서 보이는 첫인상」")
    path_order: int | None = None


class HandoffZones(BaseModel):
    layout: ZoneLayout = "ZP-A"
    cut_id: str | None = None
    points: list[HandoffZonePoint] = Field(default_factory=list)


class PlanPreviewItem(BaseModel):
    kind: Literal["product", "furniture", "column_wrap"]
    label: str
    x: float
    y: float
    w: float
    d: float
    rot_deg: float = 0


class PlanPreviewZone(BaseModel):
    id: str
    n: int
    x: float
    y: float
    name: str = ""


class PlanPreview(BaseModel):
    width_m: float
    height_m: float
    outline: list[list[float]] = Field(default_factory=list)
    rooms: list[Room] = Field(default_factory=list)
    walls: list[Wall] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)
    columns: list[Column] = Field(default_factory=list)
    items: list[PlanPreviewItem] = Field(default_factory=list)
    zones: list[PlanPreviewZone] = Field(default_factory=list)
    zone_count: int = 0
    area_pyeong: float | None = None
    ceiling_h_m: float | None = None
    area_label: str = Field("", description="「120평 · 층고 4.5m」")
    window_label: str | None = None
    file_id: str | None = Field(None, description="평면 미리보기 PNG(있으면)")


class Handoff(BaseModel):
    birdseye_id: str
    version: int
    layout_version: int
    title: str
    customer: str | None = None
    project_id: str | None = None
    route: str
    updated_at: str
    space: HandoffSpace
    plan_preview: PlanPreview | None = None
    cuts: list[HandoffCut] = Field(default_factory=list)
    comparisons: list[HandoffComparison] = Field(default_factory=list)
    zones: HandoffZones = Field(default_factory=HandoffZones)
    quantities: list[QuantityRow] = Field(default_factory=list)
    furniture: list[FurnitureDetailRow] = Field(default_factory=list)
    memos: list[str] = Field(default_factory=list)
    sheet_map: list[SheetMapRow] = Field(default_factory=list)
    products: list[ZoneProduct] = Field(default_factory=list)


class PHSource(BaseModel):
    feature: str = "birdseye"
    ref_id: str
    version: int
    title: str
    updated_at: str
    route: str


class PHTarget(BaseModel):
    proposal_type: Literal["standard", "quickwin", "solution"] = "standard"
    section_key: str = "birdseye"


class PHTemplateHint(BaseModel):
    code: str
    name: str


class PHRepeatKey(BaseModel):
    kind: Literal["space", "case", "product", "solution"]
    ref: str
    label: str


class PHSourceRef(BaseModel):
    kind: str
    ref: str
    label: str
    url: str | None = None
    tier: str | None = None


class PHItem(BaseModel):
    key: str
    label: str
    from_label: str | None = None
    sheet_role: str
    solution_code: str | None = None
    sheet_title: str | None = None
    template_hint: PHTemplateHint | None = None
    status: Literal["ok", "warn", "add"] = "ok"
    status_label: str = "그대로 들어가요"
    include_default: bool = True
    repeat_key: PHRepeatKey | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    sources: list[PHSourceRef] = Field(default_factory=list)


class PHFact(BaseModel):
    key: str
    label: str
    value: str | None = None
    unit: str | None = None
    status: Literal["confirmed", "unconfirmed", "placeholder"] = "confirmed"
    placeholder: str | None = None
    source: dict[str, Any] | None = None


class PHAsset(BaseModel):
    kind: Literal["image"] = "image"
    file_id: str | None = None
    kb_image_id: str | None = None
    rights: str = "generated"
    caption_rule: str = "생성 이미지"
    source_url: str | None = None
    image_version_id: str | None = None


class ProposalHandoff(BaseModel):
    source: PHSource
    target: PHTarget
    customer: dict[str, Any] | None = None
    items: list[PHItem] = Field(default_factory=list)
    facts: list[PHFact] = Field(default_factory=list)
    assets: list[PHAsset] = Field(default_factory=list)
    live_link: bool = False


class UsageIn(BaseModel):
    service: Literal["proposal", "scenario"]
    ref: str
    label: str = ""
    version: int | None = None
    route: str | None = None


class Usage(BaseModel):
    birdseye_id: str
    service: Literal["proposal", "scenario"]
    ref: str
    label: str = ""
    version: int | None = None
    route: str | None = None
    created_at: str


class FurnitureCatalogItem(BaseModel):
    code: str
    name: str
    short: str
    aliases: list[str] = Field(default_factory=list)
    w: float
    d: float
    h: float


class CatalogOut(BaseModel):
    furniture: list[FurnitureCatalogItem]
    tones: list[dict[str, Any]]
    lights: list[dict[str, Any]]
