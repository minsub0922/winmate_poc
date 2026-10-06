"""요청 · 응답 모델(= contracts/scenario.json). 09-scenario §5 데이터 모델 · §6 API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ScenarioType = Literal["with", "without"]
StartMode = Literal["blank", "template", "birdseye"]
ScenarioStatus = Literal["draft", "generating", "done", "failed"]
SceneStatus = Literal["waiting", "writing", "done", "failed"]
Tag = Literal["required", "recommended", "optional"]


# ── 공통 조각 ─────────────────────────────────────────────

class JobAccepted(BaseModel):
    job_id: str
    status: str = "queued"


class JobAcceptedWithScenario(JobAccepted):
    scenario_id: str


class Industry(BaseModel):
    code: str
    name: str
    short: str
    case_label: str = ""


class Aerial(BaseModel):
    enabled: bool = False
    source: Literal["new", "existing"] = "new"
    birdseye_id: str | None = None
    title: str | None = None
    created: bool = False


class BirdseyeLink(BaseModel):
    birdseye_id: str
    title: str = ""
    linked_version: int | None = None
    layout_version: int | None = None
    zones_hash: str | None = None
    keep_link: bool = False
    changed: dict[str, Any] | None = Field(None, description="{at, version} — 연결 유지한 조감도가 바뀌었을 때")
    axis: str | None = None
    zone_ids: list[str] = Field(default_factory=list)
    order: list[str] = Field(default_factory=list)


class SolutionPick(BaseModel):
    solution_id: str
    name: str
    source: Literal["user", "template", "recommended"] = "user"
    ord: int = 0


class ProductPick(BaseModel):
    ref: str | None = Field(None, description="셸 참조(kb:model:mdl_… · kb:family:fam_… · custom:글)")
    family_id: str | None = None
    model_code: str | None = None
    label: str = Field(description="표시명(Smart Signage QM55C)")
    short: str = Field(description="칩 약칭(QM55C)")
    qty: int | None = None
    source: Literal["user", "template", "birdseye", "recommended"] = "user"
    ord: int = 0


class RelatedProduct(BaseModel):
    ref: str | None = None
    family_id: str | None = None
    model_code: str | None = None
    label: str
    short: str
    why: str = Field("", description="추천 근거(D5 공존 · C2 공간 후보 · 문장 언급)")


class Notices(BaseModel):
    real_names: bool = False
    too_many: int | None = None


class ParseResult(BaseModel):
    next: Literal["SC3", "SC2E"]
    reason: str | None = None
    scene_count: int = 0


class Generation(BaseModel):
    job_id: str | None = None
    status: str = "idle"
    scope: str = "all"
    done: int = 0
    total: int = 0
    failed_reason: str | None = None


class ActiveJob(BaseModel):
    job_id: str
    kind: str
    scene_id: str | None = None


class UsageRec(BaseModel):
    service: str
    ref: str
    label: str = ""
    version: int | None = None
    created_at: str | None = None


class Scenario(BaseModel):
    id: str
    title: str
    customer_name: str | None = None
    space_label: str = ""
    project_id: str | None = None
    vertical_code: str | None = None
    industry: Industry | None = None
    type: ScenarioType
    type_label: str = Field(description="「with 솔루션」 · 「without 솔루션」")
    type_sub: str = Field(description="「솔루션 + 연관 제품 활용」 · 「제품 활용만」")
    start_mode: StartMode
    template: dict[str, Any] | None = None
    birdseye_link: BirdseyeLink | None = None
    aerial: Aerial
    raw_text: str = ""
    characters: list[str] = Field(default_factory=list)
    removed_characters: list[str] = Field(default_factory=list)
    needs: list[str] = Field(default_factory=list)
    status: ScenarioStatus
    step: int
    route: str
    version: int = Field(0, description="저장 버전(v{n}) — :save · 생성 완료 때 오른다")
    rev: int = Field(description="작업본 수정 번호(PATCH if_rev 로 겹침 확인)")
    dirty: bool = False
    via_timeline: bool = False
    solution_picks: list[SolutionPick] = Field(default_factory=list)
    product_picks: list[ProductPick] = Field(default_factory=list)
    related_products: list[RelatedProduct] = Field(default_factory=list)
    related_for: str | None = Field(None, description="추천 근거 솔루션 이름(「· MagicINFO 연관 제품 추천됨」)")
    scene_count: int = 0
    slot_count: int = 0
    role_count: int = 0
    generation: Generation | None = None
    active_job: ActiveJob | None = None
    parse: ParseResult | None = None
    notices: Notices = Field(default_factory=Notices)
    usages: list[UsageRec] = Field(default_factory=list)
    in_proposal: bool = False
    images_job: dict[str, Any] | None = None
    anonymized: bool = Field(False, description="기밀 차단으로 익명화 대체 경로를 탔다(고객사 → 「고객사」로 보내고 결과에서 되돌림)")
    last_saved_at: str | None = None
    created_at: str
    updated_at: str


class ScenarioRow(BaseModel):
    id: str
    title: str
    customer_line: str = Field(description="「{고객} · {공간}」")
    start_mode: StartMode
    start_label: str = Field(description="「직접 입력」 · 「업종 템플릿 · 의료」 · 「조감도 · {조감도 제목}」")
    type: ScenarioType
    type_label: str = Field(description="「with 솔루션」 · 「without」")
    scene_count: int
    status: ScenarioStatus
    status_label: str
    status_sub: str
    status_action: str | None = Field(None, description="실패 행 「다시 시도」")
    birdseye_changed: bool = False
    in_proposal: bool = False
    route: str
    updated_at: str


class ListCounts(BaseModel):
    all: int = 0
    draft: int = 0
    generating: int = 0
    done: int = 0
    failed: int = 0


class BirdseyeAlert(BaseModel):
    birdseye_id: str
    title: str
    changed_at: str
    changed_label: str = Field(description="「9월 30일」")
    version: int | None = None
    scenario_ids: list[str]


class ScenarioList(BaseModel):
    items: list[ScenarioRow]
    counts: ListCounts
    total: int = 0
    alert: BirdseyeAlert | None = None
    next_cursor: str | None = None


class CreateScenario(BaseModel):
    type: ScenarioType = "with"
    aerial: Aerial | None = None
    project_id: str | None = None
    title: str | None = None
    storyboard_id: str | None = Field(None, description="SB4 「공간 시나리오」 카드에서 넘어온 Storyboard(?sb=) — 공간 · 고객을 미리 채운다")
    customer_name: str | None = Field(None, max_length=200,
                                      description="다른 기능(MI4 `?mi=` · VP4 `?from=vp:`)에서 넘어온 고객사 — 프로젝트 · Storyboard 고객이 없을 때만 쓴다")


class FromTemplate(BaseModel):
    industry: str
    preset_index: int = Field(1, ge=1, le=3, description="1부터")
    type: ScenarioType = "with"
    project_id: str | None = None


class FromBirdseye(BaseModel):
    birdseye_id: str
    zone_ids: list[str]
    axis: str
    order: list[str] = Field(default_factory=list)
    keep_link: bool = True
    type: ScenarioType = "with"
    project_id: str | None = None


class PatchScenario(BaseModel):
    type: ScenarioType | None = None
    aerial: Aerial | None = None
    title: str | None = None
    raw_text: str | None = Field(None, max_length=3000)
    characters: list[str] | None = None
    removed_characters: list[str] | None = None
    step: int | None = Field(None, ge=1, le=4)
    if_rev: int | None = Field(None, description="작업본 수정 번호 — 다르면 409 VERSION_CONFLICT")


class ResyncRequest(BaseModel):
    apply: bool = False


class ZoneDiff(BaseModel):
    zone_id: str
    n: int | None = None
    name: str = ""
    change: Literal["new", "changed", "removed", "same"]
    products_changed: bool = False


class ResyncResult(BaseModel):
    diff: dict[str, Any] = Field(description="{zones_changed, products_changed}")
    zones: list[ZoneDiff] = Field(default_factory=list)
    summary: str = Field("", description="「존 {a}개 바뀜 · 제품 {b}개 바뀜」")
    applied: bool = False
    updated_scene_ids: list[str] = Field(default_factory=list)


class SavedVersion(BaseModel):
    n: int
    note: str = ""
    created_at: str
    author: str | None = None


class SaveResult(BaseModel):
    version: int
    created: bool = True


class VersionList(BaseModel):
    items: list[SavedVersion]


class CloneResult(BaseModel):
    id: str
    route: str


# ── 입력 · 타임라인 ─────────────────────────────────────────

class ParseRequest(BaseModel):
    raw_text: str = Field(min_length=10, max_length=3000)
    characters: list[str] = Field(default_factory=list)


class ExtractRequest(BaseModel):
    raw_text: str = Field(max_length=3000)
    exclude: list[str] = Field(default_factory=list, description="사용자가 지운 역할(다시 넣지 않음)")


class Characters(BaseModel):
    characters: list[str]
    source: Literal["llm", "dictionary"] = "llm"


class Beat(BaseModel):
    id: str
    role_id: str | None = None
    text: str
    place: str = ""
    primary: bool = False
    label: str = Field("", description="「장면 {n}」 · 「장면 {n} · {역할} 시점」 · 「새 장면」")


class Slot(BaseModel):
    id: str
    ord: int
    time: str | None = None
    label: str
    is_new: bool = False


class SceneRef(BaseModel):
    no: int
    is_new: bool = False


class Role(BaseModel):
    id: str
    ord: int
    name: str
    initial: str
    intro: str = ""
    wants: list[str] = Field(default_factory=list)
    pains: list[str] = Field(default_factory=list)
    suggested: bool = False
    source: str = "parsed"
    scene_count: int = 0
    scene_refs: list[SceneRef] = Field(default_factory=list)
    rewriting: bool = False


class TimelineScene(BaseModel):
    id: str
    no: int
    slot_id: str
    ord_in_slot: int = 0
    place: str = ""
    is_new: bool = False
    beats: list[Beat]
    title: str = ""
    status: str = "waiting"


class SuggestedScene(BaseModel):
    slot_id: str
    role_id: str | None = None
    text: str
    place: str = ""


class Suggestions(BaseModel):
    scene: SuggestedScene | None = None
    roles: list[str] = Field(default_factory=list)


class Timeline(BaseModel):
    slots: list[Slot]
    roles: list[Role]
    scenes: list[TimelineScene]
    suggestions: Suggestions
    changes_count: int = 0
    can_undo: bool = False
    can_redo: bool = False
    rewriting_role_ids: list[str] = Field(default_factory=list)
    job_id: str | None = Field(None, description="레인 문장 재작성 · 편집 요청 잡")


class TimelineOp(BaseModel):
    op: Literal["add_slot", "set_slot", "remove_slot", "move_beat", "add_beat", "set_beat", "remove_beat", "add_role",
                "set_role", "remove_role", "reorder_roles", "split_scene", "merge_same_time", "prune_empty_slots",
                "accept_suggestion", "dismiss_suggestion"]
    slot_id: str | None = None
    after_slot_id: str | None = None
    time: str | None = None
    label: str | None = None
    beat_id: str | None = None
    to_slot_id: str | None = None
    to_role_id: str | None = None
    role_id: str | None = None
    scene_id: str | None = None
    text: str | None = None
    place: str | None = None
    name: str | None = None
    intro: str | None = None
    wants: list[str] | None = None
    pains: list[str] | None = None
    role_ids: list[str] | None = None
    new_scene: bool | None = None
    suggested: bool | None = None


class TimelineOpsRequest(BaseModel):
    ops: list[TimelineOp] = Field(default_factory=list)
    undo: bool = False
    redo: bool = False


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class PatchRole(BaseModel):
    name: str | None = None
    intro: str | None = None
    wants: list[str] | None = None
    pains: list[str] | None = None


class TimelineText(BaseModel):
    raw_text: str


# ── 솔루션 · 제품 · 추천 ─────────────────────────────────────

class SolutionItem(BaseModel):
    solution_id: str
    name: str | None = None


class PutSolutions(BaseModel):
    items: list[SolutionItem]


class SolutionsResult(BaseModel):
    solution_picks: list[SolutionPick]
    related_products: list[RelatedProduct]
    related_for: str | None = None


class ProductItem(BaseModel):
    ref: str | None = None
    family_id: str | None = None
    model_code: str | None = None
    label: str | None = Field(None, description="없으면 셸 참조(kb:model:… · kb:family:…)로 KB 에서 이름을 찾는다(팝오버 「현재 작업에 추가」)")
    short: str | None = None
    qty: int | None = Field(None, ge=1, le=99)
    source: Literal["user", "template", "birdseye", "recommended"] = "user"


class PutProducts(BaseModel):
    items: list[ProductItem]


class ProductsResult(BaseModel):
    product_picks: list[ProductPick]
    related_products: list[RelatedProduct]


class SearchHit(BaseModel):
    id: str
    ref: str
    label: str
    short: str
    sub: str = ""
    family_id: str | None = None
    model_code: str | None = None
    kind: str = "solution"


class SearchResult(BaseModel):
    items: list[SearchHit]


class RouteResult(BaseModel):
    next: Literal["SC3R", "SC4G"]
    reason: str | None = None
    aerial_birdseye_id: str | None = None


class Evidence(BaseModel):
    kind: Literal["input_quote", "kb_message", "kb_case", "product_only"]
    ref: str | None = None
    text: str = ""
    source_url: str | None = None
    case_count: int | None = None
    case_text: str | None = Field(None, description="「· 카페 사례 [00]건」")


class Recommendation(BaseModel):
    scene_id: str
    no: int
    time: str | None = None
    label: str
    title: str = Field(description="「{라벨} — {한 줄}」")
    product_only_text: str
    evidence: list[Evidence]
    solution_id: str
    action_code: str
    solution_label: str = Field(description="「MagicINFO · 전원 스케줄」")
    benefit: str
    tag: Tag
    tag_label: str
    applied: bool


class Recommendations(BaseModel):
    status: Literal["none", "computing", "ready", "failed"] = "none"
    job_id: str | None = None
    items: list[Recommendation] = Field(default_factory=list)
    applied_count: int = 0
    product_only_count: int = 0
    required_nos: list[int] = Field(default_factory=list)
    industry_name: str | None = None
    entered_with_type: ScenarioType | None = None
    applied_solutions: list[str] = Field(default_factory=list)
    off_nos: list[int] = Field(default_factory=list)


class PatchRecommendation(BaseModel):
    applied: bool


class CommitRecommendations(BaseModel):
    mode: Literal["apply", "products_only"]


# ── 생성 · 장면 ────────────────────────────────────────────

class GenerateRequest(BaseModel):
    scope: Literal["all", "unlocked"] = "all"
    scene_ids: list[str] | None = None


class ResumeRequest(BaseModel):
    job_id: str


class SceneSolution(BaseModel):
    solution_id: str
    action_code: str
    label: str = ""
    is_new: bool = False


class SceneProduct(BaseModel):
    ref: str | None = None
    family_id: str | None = None
    model_code: str | None = None
    short: str
    label: str = ""
    qty: int | None = None
    is_new: bool = False


class SceneCharacter(BaseModel):
    role_id: str
    name: str = ""
    is_new: bool = False


class ConfirmToken(BaseModel):
    text: str = "[00]"
    near: str = ""
    kind: str = "number"


class SceneImage(BaseModel):
    image_id: str | None = None
    version_id: str
    aspect: str = "16:9"
    created_at: str | None = None
    source: Literal["image_render", "image_flow", "picked"] = "image_flow"
    url: str | None = None
    thumb_url: str | None = None
    file_id: str | None = None
    n: int | None = Field(None, description="이미지 버전 번호(v1)")
    snapshot: dict[str, Any] = Field(default_factory=dict)
    label: str = Field("", description="「v1 · 이미지 생성 · 어제」")


class ImageJob(BaseModel):
    status: Literal["queued", "running", "failed", "done"]
    render_id: str | None = None
    error: str | None = None


class SceneOut(BaseModel):
    id: str
    no: int
    slot_id: str
    time: str | None = None
    label: str
    title: str = ""
    short_title: str = ""
    place: str = ""
    space_key: str | None = None
    story: str = ""
    beats: list[Beat] = Field(default_factory=list)
    solutions: list[SceneSolution] = Field(default_factory=list)
    solution_chips: list[str] = Field(default_factory=list)
    products: list[SceneProduct] = Field(default_factory=list)
    characters: list[SceneCharacter] = Field(default_factory=list)
    confirm_tokens: list[ConfirmToken] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    image: SceneImage | None = None
    image_request_id: str | None = None
    image_stale: dict[str, Any] | None = Field(None, description="{missing:['태블릿']} — 이미지 뒤 이야기가 바뀜")
    image_job: ImageJob | None = None
    locked: bool = False
    status: SceneStatus = "waiting"
    version: int = 0
    reason: str = ""
    zone_ref: dict[str, Any] | None = None
    story_check: bool = False
    rewriting: bool = False
    is_new: bool = False
    partial_story: str | None = None
    changed_sentences: list[str] = Field(default_factory=list, description="직전 버전 대비 새 문장(「바뀐 곳 {k}」)")
    pov_role_ids: list[str] = Field(default_factory=list, description="「{역할} 시점으로」 후보(주 시점 아닌 역할)")


class SceneList(BaseModel):
    items: list[SceneOut]
    locked_nos: list[int] = Field(default_factory=list)


class PatchScene(BaseModel):
    title: str | None = Field(None, max_length=80)
    story: str | None = Field(None, max_length=400)
    characters: list[str] | None = Field(None, description="역할 id 목록")
    solutions: list[SceneSolution] | None = None
    products: list[SceneProduct] | None = None
    if_version: int | None = None


class RewriteRequest(BaseModel):
    preset: Literal["shorter", "pov", "solution_detail"] | None = None
    pov_role_id: str | None = None
    instruction: str | None = Field(None, max_length=500)


class AddSceneRequest(BaseModel):
    after_scene_id: str | None = None
    title: str | None = None


class SceneVersion(BaseModel):
    n: int
    reason: str = ""
    created_at: str
    title: str = ""


class SceneVersionList(BaseModel):
    items: list[SceneVersion]


class Stage(BaseModel):
    key: Literal["split", "write", "link", "confirm"]
    name: str
    note: str = ""
    state: Literal["done", "run", "wait"]


class PreviewScene(BaseModel):
    id: str
    no: int
    time: str | None = None
    label: str
    title: str = ""
    status: SceneStatus
    partial_story: str | None = None
    chips: list[str] = Field(default_factory=list)
    product_chips: list[str] = Field(default_factory=list)
    beat_text: str = ""


class GenerationView(BaseModel):
    job_id: str | None = None
    status: str
    summary: str = Field(description="「with 솔루션 · MagicINFO · SmartThings Pro · QM55C ×3 · KM24C」")
    stages: list[Stage]
    pct: int = 0
    eta_s: float | None = None
    eta_text: str = ""
    done: int = 0
    total: int = 0
    scenes: list[PreviewScene]
    failed_reason: str | None = None
    memos: list[str] = Field(default_factory=list)
    streaming: bool = True


# ── 이미지 ────────────────────────────────────────────────

class ImageRequestOut(BaseModel):
    request_id: str
    image_route: str
    work_id: str | None = None


class AttachImage(BaseModel):
    image_version_id: str | None = Field(None, description="image 서비스 버전(imv_…) — 없으면 image_ref 로")
    image_ref: str | None = Field(None, description="셸 이미지 참조 — img:image:<id>(내 이미지 · 현재 버전) · kb:image:<id>(사내 자산)")
    request_id: str | None = None
    source: Literal["image_render", "image_flow", "picked"] = "picked"


class ImagePrefill(BaseModel):
    space: str
    scene: str
    products: list[str]
    product_line: str
    aspect: str = "16:9"
    aspect_label: str = "16:9 · 제안서 시트용"
    kind: str = "scenario"


class ImagesSync(BaseModel):
    attached: list[str] = Field(default_factory=list)


class ImageReturn(BaseModel):
    request_id: str
    image_version_id: str


class ImageReturnOut(BaseModel):
    scenario_id: str
    scene_id: str
    route: str


# ── 보내기 · 내보내기 ────────────────────────────────────────

class Sheet(BaseModel):
    n: int
    code: Literal["VM-A", "VM-B", "VM-C", "VM-D", "SS-A", "SS-B", "SS-C"]
    kind: Literal["map", "space"]
    title: str
    space_key: str | None = None
    scene_ids: list[str]
    scene_nos: list[int]
    images: dict[str, int] = Field(description="{have, total}")
    confirm_count: int = 0
    summary: str = ""
    detail: dict[str, Any] = Field(default_factory=dict, description="미리보기 칩 · 격자(맵 시트 rows × cols)")


class SheetPlan(BaseModel):
    sheets: list[Sheet]
    carry: dict[str, int] = Field(description="{scenes, solutions, products, images, confirm}")
    images_missing: int
    first_missing_scene_id: str | None = None
    spaces: list[str] = Field(default_factory=list)
    version: int = 0
    last_saved_at: str | None = None


class UsageIn(BaseModel):
    service: Literal["proposal"] = "proposal"
    ref: str
    label: str = ""
    version: int | None = None


class ExportRequest(BaseModel):
    kind: Literal["pptx", "pdf", "docx", "zip"]


class ExportAccepted(BaseModel):
    job_id: str
    export_id: str
    status: str = "queued"


class ExportOut(BaseModel):
    id: str
    kind: str
    status: Literal["queued", "running", "done", "failed"]
    job_id: str | None = None
    file_id: str | None = None
    file_name: str | None = None
    url: str | None = None
    error: str | None = None
    created_at: str


class ShareOut(BaseModel):
    url: str
    token: str | None = None


# ── 시드 · 사전 ─────────────────────────────────────────────

class Preset(BaseModel):
    t: str
    f: str
    r: str
    n: str = "장면 4"
    flow: list[str]
    roles: list[str]


class IndustryTemplate(BaseModel):
    code: str
    name: str
    short: str
    spaces: list[str]
    presets: list[Preset]
    needs: list[str]
    used: list[str]
    space_line: str
    preset_line: str
    used_line: str


class IndustryList(BaseModel):
    items: list[IndustryTemplate]
    default_code: str = "FB"


class Skeleton(BaseModel):
    title: str
    text: str


class SkeletonList(BaseModel):
    items: list[Skeleton]


class ActionItem(BaseModel):
    solution_id: str
    solution_name: str
    action_code: str
    label: str
    benefit: str


class ActionList(BaseModel):
    items: list[ActionItem]


class BirdseyeOption(BaseModel):
    id: str
    title: str
    zone_count: int = 0
    label: str = Field(description="「{제목} · 존 {k}」")


class BirdseyeOptions(BaseModel):
    items: list[BirdseyeOption]
    count: int = 0
    available: bool = True


class ZoneRow(BaseModel):
    id: str
    n: int
    name: str
    short_name: str
    sub: str
    state: Literal["products", "furniture", "empty"]
    included: bool
    products: list[dict[str, Any]] = Field(default_factory=list)
    change: Literal["new", "changed", "removed", "same"] | None = None
    u: float | None = None
    v: float | None = None


class BirdseyePreview(BaseModel):
    birdseye_id: str
    title: str
    version: int | None = None
    zones: list[ZoneRow]
    axes: list[str]
    plan: dict[str, Any] = Field(default_factory=dict, description="plan_preview — 존 포인트 n · 평 · 층고 · 창 라벨 · 존 위치")
    order: list[str] = Field(default_factory=list)
    resync: ResyncResult | None = None


class Info(BaseModel):
    service: str
    title: str
    version: str


# ── 제안서 묶음 ─────────────────────────────────────────────

class Handoff(BaseModel):
    scenario_id: str
    version: int
    title: str
    customer: str | None = None
    type: ScenarioType
    solutions: list[dict[str, Any]]
    products: list[dict[str, Any]]
    roles: list[dict[str, Any]]
    slots: list[dict[str, Any]]
    scenes: list[dict[str, Any]]
    sheet_plan: list[dict[str, Any]]
    birdseye_link: dict[str, Any] | None = None
    confirm_items: list[dict[str, Any]]


class ProposalHandoff(BaseModel):
    source: dict[str, Any]
    target: dict[str, Any]
    customer: dict[str, Any] | None = None
    items: list[dict[str, Any]]
    facts: list[dict[str, Any]] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
    live_link: bool = False
