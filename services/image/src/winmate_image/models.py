"""image API 모델 — 이 파일의 요청 · 응답 모델이 `contracts/image.json` 이 된다(07-image §5 · §6)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Kind = Literal["space", "background", "scenario", "composite"]
Style = Literal["photo", "minimal_3d", "illustration"]
GenAspect = Literal["16:9", "4:3", "1:1"]
Aspect = Literal["16:9", "4:3", "1:1", "9:16"]
WorkStatus = Literal["draft", "queued", "running", "awaiting_input", "done", "failed", "canceled"]
RunKind = Literal["initial", "composite", "alternatives", "variants", "edit", "adjust", "renditions", "render_api"]
RunStatus = Literal["queued", "running", "awaiting_input", "succeeded", "failed", "canceled"]
ShotState = Literal["waiting", "composing", "rendering", "qc", "done", "held", "canceled", "failed"]
SourceKind = Literal["kb_asset", "my_image", "case_photo", "upload", "topbar"]
Rights = Literal["official", "customer_case", "generated", "customer", "unknown"]
AspectKey = Literal["color_light", "composition", "placement", "material"]
Strength = Literal["low", "mid", "high"]
VersionOp = Literal["generate", "composite", "edit_region", "edit_global", "adjust", "variant", "aspect", "upscale", "restore"]


class Badge(BaseModel):
    code: str = Field(description="상태 코드(running · awaiting_input · placing · in_proposal · exported · done · failed · draft)")
    label: str = Field(description="배지 문구(예 「생성 중 3 / 4」)")
    tone: Literal["brand", "ink", "gray"] = "gray"
    icon: Literal["clock", "info", "edit", "check", "download", "none"] = "none"


# ── 조건 · 작업 ──────────────────────────────────────────

class ProductCond(BaseModel):
    family_id: str | None = None
    model_code: str | None = None
    name: str = Field(description="표시명(예 Smart Signage QM55C)")
    short: str = Field(description="약칭(예 QM55C)")
    qty: int = Field(1, ge=1, le=9)
    source: Literal["prefill", "user", "request"] = "user"


class Conditions(BaseModel):
    products: list[ProductCond] = Field(default_factory=list)
    style: Style = "photo"
    aspect: GenAspect = "16:9"
    count: Literal[2, 4] = 4
    no_products: bool = Field(False, description="배경 유형의 「제품 없이」")


class PlacementGroup(BaseModel):
    id: str
    family_id: str | None = None
    model_code: str | None = None
    label: str = Field("", description="약칭(예 QM55C)")
    name: str = ""
    qty: int = Field(1, ge=1, le=9)
    arrangement: Literal["row3", "col3", "separate", "single"] = "row3"
    mount: Literal["wall", "ceiling"] = "wall"
    quad: list[list[float]] = Field(default_factory=list, description="사진 좌표(0..1) [[x,y]×4] 왼쪽 위부터 시계 방향")
    gap_mm: int = 10


class RefDims(BaseModel):
    counter_width_mm: float | None = None
    install_height_mm: float | None = None


class CompositeOptions(BaseModel):
    perspective_light_match: bool = True
    screen_menu: bool = True


class GroupMeasure(BaseModel):
    id: str
    width_mm: int | None = None
    height_mm: int | None = None
    bottom_mm: int | None = None
    estimated: bool = False
    label_text: str = Field("", description="「가로 약 3,730 mm · 바닥에서 1,800 mm」 — 모르면 [00]")
    fit_quad: list[list[float]] | None = Field(None, description="축척이 있으면 실제 크기로 맞춘 그룹 쿼드(사진 0..1)")


class Scale(BaseModel):
    mm_per_px: float | None = None
    method: Literal["ref_dim", "std_object", "none"] = "none"


class CompositeState(BaseModel):
    active_photo_id: str | None = None
    groups: list[PlacementGroup] = Field(default_factory=list)
    ref_dims: RefDims = Field(default_factory=RefDims)
    options: CompositeOptions = Field(default_factory=CompositeOptions)
    scale: Scale = Field(default_factory=Scale)
    measures: list[GroupMeasure] = Field(default_factory=list)


class Origin(BaseModel):
    service: str = "image"
    ref: str | None = None
    request_id: str | None = None
    label: str | None = None


class PrefillState(BaseModel):
    done: bool = False
    search_query: str | None = None
    industry: str | None = None
    industry_chips: list[str] = Field(default_factory=list)
    space_label: str | None = None
    kind_suggestion: Kind | None = None
    message: str | None = Field(None, description="prefill 실패 안내(「제품을 찾지 못했어요. 제품명을 입력해 주세요」)")
    timed_out: bool = False


class RunBrief(BaseModel):
    id: str
    kind: RunKind
    status: RunStatus
    job_id: str | None = None
    done: int = 0
    total: int = 0
    held: int = 0
    route: str = ""


class Work(BaseModel):
    id: str
    owner: str
    project_id: str | None = None
    customer_name: str | None = None
    customer_short: str | None = None
    title: str
    subject_short: str | None = None
    kind: Kind
    kind_label: str
    description: str = ""
    echo: str = Field("", description="사용자 입력 메아리 「공간 · 카페 카운터 …」")
    conditions: Conditions
    composite: CompositeState | None = None
    origin: Origin | None = None
    start: Literal["type", "references", "composite"] = "type"
    status: WorkStatus
    badge: Badge
    route: str
    selected_image_id: str | None = None
    last_export: dict[str, Any] | None = None
    prefill: PrefillState | None = None
    references: list["Reference"] = Field(default_factory=list)
    ref_notice: str | None = Field(None, description="「이미지 검색에서 선택한 2장이 참조로 들어갔습니다」")
    latest_run: RunBrief | None = None
    active_runs: list[RunBrief] = Field(default_factory=list)
    image_count: int = 0
    version: int = Field(description="사용자 편집 판(PATCH if_version)")
    created_at: str
    updated_at: str


class WorkCreate(BaseModel):
    kind: Kind | None = None
    description: str | None = Field(None, max_length=500)
    project_id: str | None = None
    customer_name: str | None = None
    request_id: str | None = None
    start: Literal["type", "references", "composite"] = "type"
    reference_items: list["ReferenceIn"] | None = None
    title: str | None = None


class WorkPatch(BaseModel):
    kind: Kind | None = None
    description: str | None = Field(None, max_length=500)
    title: str | None = Field(None, max_length=60)
    customer_name: str | None = None
    conditions: Conditions | None = None
    selected_image_id: str | None = None
    if_version: int | None = None


class ProductsAdd(BaseModel):
    refs: list[str] = Field(min_length=1, max_length=9, description="셸 참조 kb:model:mdl_… · kb:family:fam_… · custom:<글>")
    qty: int = Field(1, ge=1, le=9)


class ProductsAdded(BaseModel):
    added: list[str] = Field(description="풀어서 더한 참조(셸 「✓ 추가됨」)")
    work: Work


class WorkRow(BaseModel):
    id: str
    title: str
    meta: str = Field(description="`{고객사} · {유형} · {장수}`")
    time: str = Field(description="상대 시각(방금 · N분 전 …)")
    updated_at: str
    status: Badge
    thumb_url: str | None = None
    route: str
    kind: Kind
    customer_short: str | None = None
    run: RunBrief | None = None


class Totals(BaseModel):
    works: int
    images: int


class WorkList(BaseModel):
    items: list[WorkRow]
    next_cursor: str | None = None
    totals: Totals


class PrefillProduct(BaseModel):
    family_id: str | None = None
    model_code: str | None = None
    name: str
    short: str
    qty: int = 1


class Prefill(BaseModel):
    title: str
    subject_short: str | None = None
    products: list[PrefillProduct] = Field(default_factory=list)
    search_query: str | None = None
    industry_chips: list[str] = Field(default_factory=list)
    kind_suggestion: Kind | None = None
    customer_name: str | None = None
    timed_out: bool = False
    message: str | None = None
    work: Work


# ── 참조 ─────────────────────────────────────────────────

class RefAnalysis(BaseModel):
    faces: list[list[float]] = Field(default_factory=list)
    logos: list[list[float]] = Field(default_factory=list)
    displays: list[dict[str, Any]] = Field(default_factory=list)
    style: str | None = None
    palette: list[str] = Field(default_factory=list)
    caption: str | None = None
    elements: dict[str, str] = Field(default_factory=dict, description="따를 요소별 묘사(color_light · composition · placement · material)")


class Reference(BaseModel):
    id: str
    work_id: str
    order: int
    source_kind: SourceKind
    source_ref: str | None = None
    origin_kind: Literal["kb_asset", "my_image", "case_photo", "upload"] = "kb_asset"
    file_id: str | None = None
    thumb_url: str | None = None
    label: str
    source_label: str
    source_url: str | None = None
    rights: Rights
    aspects: list[AspectKey]
    strength: Strength
    role_label: str = Field("", description="「구도」 · 「색감 · 조명 · 소재」")
    analysis: RefAnalysis | None = None
    sanitized_file_id: str | None = None
    send_mode: Literal["image", "text_fallback"] | None = None
    via: Literal["picker", "topbar", "drop", "upload"] = "picker"
    strong_allowed: bool = True
    created_at: str


class ReferenceIn(BaseModel):
    source_kind: SourceKind
    source_ref: str | None = Field(None, description="KB 이미지 id · img_(내 생성) · dep_ 사례 사진 id · 셸 ref(kb:image:… · img:image:…)")
    file_id: str | None = None
    aspects: list[AspectKey] | None = None
    strength: Strength | None = None
    label: str | None = None
    via: Literal["picker", "topbar", "drop", "upload"] | None = None


class ReferencePatch(BaseModel):
    aspects: list[AspectKey] | None = None
    strength: Strength | None = None
    order: int | None = None


class ReferenceSet(BaseModel):
    items: list[ReferenceIn] = Field(default_factory=list, max_length=3)
    via: Literal["picker", "topbar", "drop", "upload"] = "picker"


class ReferenceList(BaseModel):
    items: list[Reference]
    notice: str | None = None


class RefSearchItem(BaseModel):
    source_kind: SourceKind
    source_ref: str
    thumb_url: str | None = None
    label: str
    alt: str | None = None
    source_label: str
    source_url: str | None = None
    rights: Rights
    verified: bool = False
    visual_style: Literal["photo", "illustration"] = "photo"
    file_id: str | None = None


class RefSearch(BaseModel):
    items: list[RefSearchItem]
    total: int
    next_cursor: str | None = None
    head: str = Field(description="「8 개 · 검수 완료」 · 「3 개」")
    query: str = ""
    industry_chips: list[str] = Field(default_factory=list)


# ── 현장 사진 ────────────────────────────────────────────

class Surface(BaseModel):
    label: str
    kind: Literal["wall", "counter", "ceiling", "floor", "other"] = "wall"
    quad: list[list[float]]
    installable: bool = True


class SceneObject(BaseModel):
    label: str
    bbox: list[float]


class PhotoQuality(BaseModel):
    luma_mean: float
    laplacian_var: float
    clipped_ratio: float


class SitePhoto(BaseModel):
    id: str
    work_id: str
    file_id: str
    url: str
    thumb_url: str
    label: str
    status: Literal["recognizing", "recognized", "low_light", "failed", "manual"]
    status_label: str
    quality: PhotoQuality | None = None
    surfaces: list[Surface] = Field(default_factory=list)
    objects: list[SceneObject] = Field(default_factory=list)
    floor_line: float | None = None
    width: int | None = None
    height: int | None = None
    job_id: str | None = None
    message: str | None = Field(None, description="W 문구(인식 결과)")
    created_at: str


class SitePhotoIn(BaseModel):
    file_id: str


class SitePhotoAccepted(BaseModel):
    job_id: str
    photo_id: str
    status: Literal["queued"] = "queued"
    photo: SitePhoto


class SitePhotoList(BaseModel):
    items: list[SitePhoto]


class PlacementsIn(BaseModel):
    photo_id: str
    groups: list[PlacementGroup] = Field(default_factory=list)
    ref_dims: RefDims = Field(default_factory=RefDims)
    options: CompositeOptions = Field(default_factory=CompositeOptions)


class PlacementResult(BaseModel):
    groups: list[GroupMeasure]
    scale: Scale
    composite: CompositeState


# ── run · 대기열 ─────────────────────────────────────────

class IssueOption(BaseModel):
    id: str
    label: str
    recommended: bool = False
    default: bool = False
    action: Literal["choose", "pick_product", "link"] = "choose"


class PolicyIssue(BaseModel):
    id: str
    type: Literal["product_unrecognized", "competitor_brand", "real_person", "unsafe"]
    title: str
    status: Literal["auto", "needs_choice"]
    state_label: str = Field(description="「대안 선택됨」 · 「선택 필요」")
    description: str
    options: list[IssueOption]
    selected: str | None = Field(None, description="고른 option id · 'custom'")
    custom_text: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class Precheck(BaseModel):
    issues: list[PolicyIssue] = Field(default_factory=list)
    mode: Literal["llm", "rules"] = "rules"
    applied_note: str | None = Field(None, description="「경쟁사 · 인물 요소 없이 만들었어요」")


class RunCreate(BaseModel):
    kind: Literal["initial", "composite", "alternatives"] = "initial"
    count: Literal[2, 4] | None = None
    notify: bool = True


class RunAccepted(BaseModel):
    job_id: str
    run_id: str
    status: RunStatus
    precheck: Precheck


class Stage(BaseModel):
    key: Literal["product_fit", "compose", "render", "qc"]
    label: str
    state: Literal["done", "now", "todo"]


class Shot(BaseModel):
    image_id: str
    index: int
    label: str
    letter: str | None = None
    state: ShotState
    stage_label: str = ""
    progress: int = Field(0, description="0..100(추정)")
    eta_s: int | None = None
    started_at: str | None = None
    expected_s: float | None = None
    preview_url: str | None = None
    thumb_url: str | None = None
    url: str | None = None
    aspect: str
    width: int | None = None
    height: int | None = None
    qc_flag: bool = False
    qc_reason: str | None = None
    layout_note: str | None = None
    wait_for: str | None = Field(None, description="대기 카드 「시안 {j}가 끝나면 시작해요」")
    error: str | None = None


class RunDetail(BaseModel):
    id: str
    work_id: str
    kind: RunKind
    status: RunStatus
    job_id: str | None = None
    notify: bool = True
    title: str
    stages: list[Stage]
    shots: list[Shot]
    done: int
    total: int
    held: int = 0
    eta_s: int | None = None
    eta_label: str = ""
    summary_line: str = ""
    head: str = Field("", description="「생성 중 · 1 / 4 완료」 · 「대기 중 · 앞에 1건」")
    issues: list[PolicyIssue] = Field(default_factory=list)
    applied_note: str | None = None
    change_note: str | None = Field(None, description="보류 없이 바꿔 만든 경우 IMG3 띠 「요청 중 {k}가지를 바꿔서 만들었어요」")
    error: dict[str, Any] | None = None
    queue_ahead: int | None = None
    base_image_id: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    route: str = ""
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


class RunList(BaseModel):
    items: list[RunDetail]


class RunPatch(BaseModel):
    notify: bool


class RunCancelResult(BaseModel):
    run_id: str
    status: RunStatus


class ShotCancelResult(BaseModel):
    image_id: str
    status: ShotState


class Answer(BaseModel):
    issue_id: str
    option: str | None = None
    custom_text: str | None = None
    product: dict[str, Any] | None = Field(None, description="「제품 탐색에서 고르기」로 고른 제품 {model_code, family_id, name, short}")


class AnswersIn(BaseModel):
    answers: list[Answer] = Field(default_factory=list)
    skip_held: bool = False
    all_recommended: bool = False


class AnswersAccepted(BaseModel):
    run_id: str
    job_id: str | None = None
    status: RunStatus


class AlternativeIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class AlternativeResult(BaseModel):
    accepted: bool
    issue_id: str | None = None
    message: str
    run: RunDetail


class QueueItem(BaseModel):
    run_id: str
    work_id: str
    title: str
    meta: str
    position: int
    state_label: str
    note: str | None = None
    note_route: str | None = None


class QueueList(BaseModel):
    items: list[QueueItem]
    running: RunBrief | None = None


# ── 시안 · 버전 ──────────────────────────────────────────

class Rendition(BaseModel):
    kind: Literal["native", "fhd", "uhd", "uhd8k", "thumb"]
    w: int
    h: int
    file_id: str
    method: str = ""
    url: str


class Version(BaseModel):
    id: str
    image_id: str
    n: int
    parent_version_id: str | None = None
    op: VersionOp
    op_params: dict[str, Any] = Field(default_factory=dict)
    label: str = Field(description="수정 기록 라벨(원본 · 수정 1 · 영역 1 · 보정 1 …)")
    short_label: str = Field("", description="전/후 비교 라벨(원본 · 수정 1 · 보정 1)")
    title: str = Field(description="IMG4 제목(시안 1 · 부분 수정본 v2)")
    master_file_id: str
    url: str
    thumb_url: str
    width: int
    height: int
    native: dict[str, Any] = Field(default_factory=dict)
    renditions: list[Rendition] = Field(default_factory=list)
    generation: dict[str, Any] = Field(default_factory=dict)
    qc: dict[str, Any] = Field(default_factory=dict)
    is_current: bool = False
    created_at: str


class VersionList(BaseModel):
    items: list[Version]


class Usage(BaseModel):
    image_id: str
    version_id: str
    service: Literal["proposal", "scenario", "birdseye"]
    ref: str
    label: str = ""
    created_at: str


class UsageIn(BaseModel):
    version_id: str
    service: Literal["proposal", "scenario", "birdseye"]
    ref: str
    label: str = ""


class Scene(BaseModel):
    space: str | None = None
    products: list[str] = Field(default_factory=list)


class ImageTile(BaseModel):
    id: str
    title: str
    label: str
    width: int | None = None
    height: int | None = None
    format: str | None = None
    bytes: int | None = None
    created_at: str
    file_id: str | None = None
    thumb_url: str | None = None
    kind: Kind
    aspect: str
    customer_short: str | None = None
    status: ShotState
    used_in_count: int = 0
    origin: str = "image"
    meta: str = Field("", description="「A 커피 · 공간 · 16:9」 · 생성 중이면 「… · 생성 중」")
    work_id: str
    run_id: str | None = None
    current_version_id: str | None = None
    progress_done: int | None = None
    progress_total: int | None = None
    route: str = ""
    run_route: str | None = None
    saved: bool = False


class ImageList(BaseModel):
    items: list[ImageTile]
    total: int
    next_cursor: str | None = None


class ImageDetail(BaseModel):
    id: str
    work_id: str
    run_id: str | None = None
    label: str
    title: str
    letter: str | None = None
    variant_name: str | None = None
    aspect: str
    style: Style = "photo"
    kind: Kind
    status: ShotState
    origin: str = "image"
    saved: bool = False
    hidden: bool = False
    base_image_id: str | None = None
    current_version_id: str | None = None
    current: Version | None = None
    versions: list[Version] = Field(default_factory=list)
    file_id: str | None = Field(None, description="현재 버전의 기준 렌디션(fhd) 파일")
    url: str | None = None
    thumb_url: str | None = None
    width: int | None = None
    height: int | None = None
    rights: Literal["generated"] = "generated"
    caption_rule: str = "생성 이미지"
    scene: Scene = Field(default_factory=Scene)
    prompt: str | None = None
    qc_flag: bool = False
    qc_reason: str | None = None
    layout_note: str | None = None
    used_in: list[Usage] = Field(default_factory=list)
    customer_short: str | None = None
    subject_short: str | None = None
    work_title: str = ""
    products: list[ProductCond] = Field(default_factory=list)
    project_id: str | None = None
    created_at: str


class InfoRow(BaseModel):
    k: str
    v: str
    href: str | None = None


class ImageInfo(BaseModel):
    image_id: str
    version_id: str
    title: str
    rows: list[InfoRow]


class SaveResult(BaseModel):
    image_id: str
    saved: bool


class DetectIn(BaseModel):
    kinds: list[Literal["object", "text", "person", "screen"]] = Field(default_factory=lambda: ["object", "text", "person", "screen"])
    version_id: str | None = None


class Detection(BaseModel):
    id: str
    kind: Literal["object", "text", "person", "screen", "product"]
    label: str
    box: list[float]


class Detections(BaseModel):
    version_id: str
    supported: bool
    boxes: list[Detection]


class EditRegion(BaseModel):
    id: str
    image_id: str
    base_version_id: str | None = None
    n: int
    shape: Literal["rect", "brush", "object"]
    rect: list[float] | None = Field(None, description="[x0,y0,x1,y1] 0..1")
    mask_file_id: str | None = None
    detection_id: str | None = None
    label: str
    instruction: str = ""
    status: Literal["pending", "applying", "applied", "reverted", "failed"]
    status_label: str
    result_version_id: str | None = None
    protect_products: bool = True
    run_id: str | None = None
    error: str | None = None
    created_at: str


class RegionIn(BaseModel):
    shape: Literal["rect", "brush", "object"] = "rect"
    rect: list[float] | None = None
    mask_file_id: str | None = None
    detection_id: str | None = None
    instruction: str | None = None
    label: str | None = None
    preset: Literal["erase_text", "erase_people", "screen_content"] | None = None


class RegionPatch(BaseModel):
    rect: list[float] | None = None
    mask_file_id: str | None = None
    instruction: str | None = None
    label: str | None = None
    protect_products: bool | None = None


class RegionList(BaseModel):
    items: list[EditRegion]


class RegionCreated(BaseModel):
    region: EditRegion | None = Field(None, description="첫 영역(칩으로 여러 개가 생기면 regions 에 모두)")
    regions: list[EditRegion] = Field(default_factory=list)
    note: str | None = Field(None, description="「자동 영역 인식이 없어 전체 이미지에 적용해요」 — 이때 region 은 없고 global_instruction 으로 전체 편집")
    global_instruction: str | None = None


class RevertResult(BaseModel):
    current_version_id: str
    region: EditRegion


class EditIn(BaseModel):
    base_version_id: str | None = None
    region_ids: list[str] | None = None
    mode: Literal["region", "global"] = "region"
    instruction: str | None = None
    protect_products: bool = True


class JobAccepted(BaseModel):
    job_id: str
    run_id: str
    status: RunStatus = "queued"


class AdjustIn(BaseModel):
    base_version_id: str | None = None
    brightness: float | None = Field(None, ge=-0.3, le=0.3)
    harmonize_region_id: str | None = None
    preset: Literal["brighten"] | None = None


class VariantsIn(BaseModel):
    count: int = Field(4, ge=1, le=4)
    axis: Literal["any", "lighting", "people"] = "any"
    instruction: str | None = None


class RenditionsIn(BaseModel):
    aspects: list[Aspect] = Field(min_length=1)
    fit: Literal["recompose", "crop", "outpaint"] = "recompose"
    upscale: Literal["1x", "2x", "4x"] = "2x"
    instructions: dict[str, str] | None = None


class InterpretIn(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    screen: Literal["result", "variants", "export", "edit"] = "result"


class InterpretResult(BaseModel):
    action: Literal["region_edit", "global_edit", "variants", "aspect_instruction", "export_options", "ask"]
    instruction: str = ""
    region: dict[str, Any] | None = Field(None, description="{rect, label} — region_edit")
    aspect: str | None = None
    options: dict[str, Any] = Field(default_factory=dict, description="내보내기 옵션(caption · english_filename · format · include_original …)")
    question: str | None = Field(None, description="해석이 모호할 때 W 가 한 번 되묻는 문장")


class CaptionResult(BaseModel):
    caption: str


class FilenameIn(BaseModel):
    lang: Literal["en", "ko"] = "en"
    ext: str = "png"
    version_id: str | None = None


class FilenameResult(BaseModel):
    filename: str


# ── 내보내기 ─────────────────────────────────────────────

class ExportIn(BaseModel):
    version_id: str | None = None
    format: Literal["png", "jpg", "pdf", "pptx"] = "png"
    resolution: Literal["fhd", "uhd"] = "uhd"
    ai_label: bool = True
    include_original: bool = False
    filename: str | None = None
    caption: str | None = None


class ExportOut(BaseModel):
    export_id: str
    status: Literal["queued", "running", "done", "failed"]
    format: str
    filename: str
    file_id: str | None = None
    download_url: str | None = None
    job_id: str | None = None
    error: dict[str, Any] | None = None


class BulkExportIn(BaseModel):
    version_ids: list[str] = Field(min_length=1, max_length=50)
    format: Literal["png"] = "png"
    ai_label: bool = True


# ── 다른 기능의 요청 ─────────────────────────────────────

class RequestPrefill(BaseModel):
    model_config = ConfigDict(extra="allow")
    kind: Kind | None = None
    description: str | None = None
    products: list[Any] = Field(default_factory=list, description="모델코드 · 제품 이름 문자열 또는 {model_code, family_id, name, short, qty}")
    aspect: GenAspect | None = None
    style: Style | None = None
    space_label: str | None = None


class RequestIn(BaseModel):
    from_service: str
    from_ref: str
    from_label: str
    title: str
    prefill: RequestPrefill = Field(default_factory=RequestPrefill)
    project_id: str | None = None


class ImageRequest(BaseModel):
    id: str
    from_service: str
    from_ref: str
    from_label: str
    title: str
    prefill: RequestPrefill
    status: Literal["open", "in_progress", "fulfilled", "dismissed"]
    work_id: str | None = None
    result_version_id: str | None = None
    result_image_id: str | None = None
    project_id: str | None = None
    created_by: str
    created_at: str
    updated_at: str


class RequestList(BaseModel):
    items: list[ImageRequest]


class RequestStarted(BaseModel):
    work_id: str
    route: str = Field(description="IMG1(미리 채움) 경로 /image/new?work=…")
    conditions_route: str = Field(description="IMG2 경로 /image/w/{id}/conditions(장면 설명 · 제품 · 비율 미리 채움)")
    request: ImageRequest


class FulfillIn(BaseModel):
    version_id: str


# ── 렌더 API(birdseye · scenario) ────────────────────────

class RenderPrompt(BaseModel):
    subject_ko: str
    details_ko: list[str] = Field(default_factory=list)
    negatives: list[str] = Field(default_factory=list)


class EditOf(BaseModel):
    file_id: str
    instruction: str


class ProductRef(BaseModel):
    family_id: str | None = None
    model_code: str | None = None
    qty: int = Field(1, ge=1, le=99)


class ExpectProduct(BaseModel):
    family_id: str | None = None
    model_code: str | None = None
    qty: int = 1
    bbox_hint: list[float] | None = None


class RenderExpect(BaseModel):
    products: list[ExpectProduct] = Field(default_factory=list)


class RenderIn(BaseModel):
    origin: Origin
    project_id: str | None = None
    kind: str = Field("scene", description="birdseye · scene · …")
    prompt: RenderPrompt
    aspect: str = "16:9"
    target: Literal["fhd", "uhd"] = "fhd"
    structure_ref_file_id: str | None = None
    edit_of: EditOf | None = None
    reference_file_ids: list[str] = Field(default_factory=list)
    product_refs: list[ProductRef] = Field(default_factory=list)
    expect: RenderExpect | None = None
    forbid: list[Literal["competitor_logo", "real_person_face", "gibberish_text"]] = Field(default_factory=list)
    allow_people: Literal["none", "silhouette", "generic"] = "none"
    confidential: bool = False
    label: str | None = None
    style: Style = "photo"


class RenderAccepted(BaseModel):
    job_id: str
    render_id: str
    status: Literal["queued"] = "queued"


class RenderOut(BaseModel):
    id: str
    status: Literal["queued", "running", "succeeded", "failed", "canceled"]
    origin: Origin
    kind: str
    image_id: str | None = None
    version_id: str | None = None
    renditions: list[Rendition] = Field(default_factory=list)
    generation: dict[str, Any] = Field(default_factory=dict)
    qc: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] | None = None
    job_id: str | None = None
    created_at: str


# ── 능력 ─────────────────────────────────────────────────

class T2ICapFlags(BaseModel):
    supports_reference_images: bool
    supports_edit: bool
    supports_mask: bool
    max_side_px: int
    images_per_call: int
    max_reference_images: int
    available: bool = True


class I2TCapFlags(BaseModel):
    supports_json: bool
    supports_bbox: bool
    available: bool = True


class FeatureFlags(BaseModel):
    object_select: bool
    mask_native: bool
    outpaint: bool
    recompose: bool
    upscale_4x: bool
    region_edit: bool
    reference_images: bool


class Capabilities(BaseModel):
    mode: str
    t2i: T2ICapFlags
    i2t: I2TCapFlags
    upscaler: Literal["none", "realesrgan_x4v3"]
    features: FeatureFlags
    available: bool = True


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


Work.model_rebuild()
WorkCreate.model_rebuild()
ProductsAdded.model_rebuild()
