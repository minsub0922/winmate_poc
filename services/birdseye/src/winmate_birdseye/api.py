"""birdseye API (/v1) — 08-birdseye §6. 이 파일의 엔드포인트가 contracts/birdseye.json 이 된다(make contracts).

다른 기능이 쓰는 경로(생산자 계약 — 모양을 지킨다):
  scenario(서버): GET /v1/birdseyes · GET /v1/birdseyes/{id}/version · GET /v1/birdseyes/{id}/handoff · POST /v1/birdseyes ·
                  POST /v1/birdseyes/{id}/usages
  proposal(서버 · 웹): GET /v1/birdseyes/{id}/proposal-handoff?type=&section= (별칭 GET /v1/layouts/{id}/proposal-handoff) ·
                  GET /v1/birdseyes/{id}/handoff · POST · DELETE /v1/birdseyes/{id}/usages
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, Query, Response

from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id
from winmate_common.jobs import jobs

from . import config, edits, exporting, furniture, inputs, layouts, products, zones
from . import cuts as C
from . import service as svc
from .models import (
    AnswerIn, AttachIn, AttachOut, Birdseye, BirdseyeCreate, BirdseyeList, BirdseyePatch, CatalogOut, CloneIn, CloneOut, CommitOut,
    Cut, CutPatch, CutsAccepted, CutsCreate, ExportAccepted, ExportCreate, ExportOptions, ExportRecord, FactsOut, FurnitureItem,
    FurniturePut, FurnitureRecommendIn, FurnitureView, Handoff, JobAccepted, LayoutGenerateIn, LayoutNlEditIn, LayoutView,
    NlEditAccepted, OpsIn, Photo, PhotoAccepted, PhotoAdd, PhotoPatch, PhotoSet, PlanAccepted, PlanAdd, PlanList, PlanRecognizeIn,
    PlanView, ProductItem, ProductSearch, ProductsPut, ProductsView, ProposalHandoff, Quantities, ResultEditIn, ResultEditOut,
    SavedVersionList, SaveOut, ServiceInfo, SessionCreated, SessionView, SpaceModel, SpaceView, TextIn, TokenPhotoIn, UploadToken,
    UploadTokenInfo, UploadTokenPrincipal, Usage, UsageIn, ValidateIn, ValidateOut, VersionInfo, WarningActionIn, ZoneCreate, ZonePatch, ZonePoint,
    ZonesAutoIn, ZonesRewriteIn, ZonesView,
)
from .repo import repo

router = APIRouter(prefix="/v1")

INTERNAL = ["internal"]


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="birdseye", title="공간 조감도 — 공간 입력 · 도면 인식 · 제품 배치 · 가구 추천 · 배치 검증 · 3D 조감도", version="0.1.0")


@router.get("/catalog", response_model=CatalogOut, tags=["meta"], summary="가구 카탈로그 · 인테리어 톤 · 조명(화면 칩)")
async def catalog() -> dict[str, Any]:
    items = [{"code": it["code"], "name": it["name"], "short": it.get("short") or it["name"], "aliases": it.get("aliases") or [],
              "w": float(it["w"]), "d": float(it["d"]), "h": float(it["h"])} for it in config.catalog()["items"]]
    tones = [{"code": k, **v} for k, v in config.rules()["tones"].items()]
    lights = [{"code": k, **v} for k, v in config.rules()["lights"].items()]
    return {"furniture": items, "tones": tones, "lights": lights}


async def _job_running(job_id: str | None) -> bool:
    if not job_id:
        return False
    j = await jobs().get(job_id)
    return j is not None and j.status in ("queued", "running")


# ── 작업(§6.1) ───────────────────────────────────────────

@router.get("/birdseyes", response_model=BirdseyeList, tags=["birdseyes"], summary="조감도 작업 목록(BE0 · 시나리오 SC1 · SC1B)")
async def list_birdseyes(
    filter_: Literal["all", "in_progress", "needs_check", "done"] = Query("all", alias="filter"),
    in_proposal: bool = False, q: str | None = None, scope: Literal["mine", "team"] = "mine",
    sort: Literal["updated"] = "updated", limit: int = Query(50, ge=1, le=200), cursor: str | None = None,
) -> dict[str, Any]:
    _ = sort
    return await svc.list_rows(filter_=filter_, in_proposal=in_proposal, q=q, scope=scope, limit=limit, cursor=cursor)


@router.post("/birdseyes", response_model=Birdseye, status_code=201, tags=["birdseyes"], summary="새 조감도 작업(BE1 · 시나리오 · 이미지 참조)")
async def create_birdseye(body: BirdseyeCreate) -> dict[str, Any]:
    if body.ceiling_m is not None:
        lo, hi = config.rules()["ceiling_range_m"]
        if not (lo <= body.ceiling_m <= hi):
            raise ApiError(400, "INVALID_ARGUMENT", f"층고는 {lo:g}~{hi:g} m 사이로 적어 주세요", {"field": "ceiling_m"})
    b = await svc.create(body.model_dump(exclude_none=True))
    return svc.view(b)


@router.get("/birdseyes/{be_id}", response_model=Birdseye, tags=["birdseyes"])
async def get_birdseye(be_id: str) -> dict[str, Any]:
    await svc.derive(be_id)
    return svc.view(await svc.get(be_id))


@router.patch("/birdseyes/{be_id}", response_model=Birdseye, tags=["birdseyes"], summary="칸 값 · 톤 · 시점 · 존 레이아웃 · 공유(409 if_version)")
async def patch_birdseye(be_id: str, body: BirdseyePatch) -> dict[str, Any]:
    b = await svc.patch(be_id, body.model_dump(exclude_none=True))
    if body.ceiling_m is not None or body.clear_ceiling or body.area_pyeong is not None or body.clear_area:
        await inputs.refresh_space(be_id)
    return svc.view(b)


@router.delete("/birdseyes/{be_id}", status_code=204, tags=["birdseyes"], summary="지우기(소프트 삭제)")
async def delete_birdseye(be_id: str) -> Response:
    await svc.delete(be_id)
    return Response(status_code=204)


@router.get("/birdseyes/{be_id}/version", response_model=VersionInfo, tags=["birdseyes"], summary="변경 감지(시나리오 · 가벼움)")
async def get_version(be_id: str) -> dict[str, Any]:
    return await svc.version_info(be_id)


@router.post("/birdseyes/{be_id}:clone", response_model=CloneOut, status_code=201, tags=["birdseyes"], summary="복제해서 새 시안(→ BE4)")
async def clone_birdseye(be_id: str, body: CloneIn = Body(default_factory=CloneIn)) -> dict[str, Any]:
    return await svc.clone(be_id, body.title)


@router.post("/birdseyes/{be_id}:save", response_model=SaveOut, tags=["birdseyes"], summary="버전 저장(「저장했어요 · v{n}」)")
async def save_birdseye(be_id: str) -> dict[str, Any]:
    return await svc.save(be_id)


@router.get("/birdseyes/{be_id}/versions", response_model=SavedVersionList, tags=["birdseyes"])
async def list_versions(be_id: str) -> dict[str, Any]:
    return {"items": await svc.saved_versions(be_id)}


@router.post("/birdseyes/{be_id}/versions/{n}/restore", response_model=Birdseye, tags=["birdseyes"])
async def restore_version(be_id: str, n: int) -> dict[str, Any]:
    return svc.view(await svc.restore(be_id, n))


# ── 공간 입력(§6.2) ──────────────────────────────────────

@router.post("/birdseyes/{be_id}/space:analyze", response_model=JobAccepted, status_code=202, tags=["space"],
             summary="설명 · 도면 · 사진 → 공간 모델(→ BE2)")
async def analyze_space(be_id: str) -> dict[str, Any]:
    return await inputs.start_analyze(be_id)


@router.get("/birdseyes/{be_id}/space", response_model=SpaceView, tags=["space"])
async def get_space(be_id: str) -> dict[str, Any]:
    return await inputs.space_view(be_id)


@router.post("/birdseyes/{be_id}/attachments", response_model=AttachOut, tags=["space"],
             summary="BE1 파일 첨부 분류(R1): PDF → 도면, 이미지 → i2t 「평면도인가?」 → 도면/현장 사진 · 415")
async def attach(be_id: str, body: AttachIn) -> dict[str, Any]:
    return await inputs.attach(be_id, body.file_ids)


@router.post("/birdseyes/{be_id}/plans", response_model=PlanAccepted, status_code=202, tags=["space"], summary="도면 올리기 → 인식 잡 · 415")
async def add_plan(be_id: str, body: PlanAdd) -> dict[str, Any]:
    return await inputs.add_plan(be_id, body.file_id, body.page)


@router.get("/birdseyes/{be_id}/plans", response_model=PlanList, tags=["space"])
async def list_plans(be_id: str) -> dict[str, Any]:
    return {"items": await inputs.list_plans(be_id)}


@router.get("/birdseyes/{be_id}/plans/{plan_id}", response_model=PlanView, tags=["space"])
async def get_plan(be_id: str, plan_id: str) -> dict[str, Any]:
    return await inputs.get_plan(be_id, plan_id)


@router.post("/birdseyes/{be_id}/plans/{plan_id}:recognize", response_model=PlanAccepted, status_code=202, tags=["space"],
             summary="다시 인식(같은 파일) · 쪽 바꾸기")
async def recognize_plan(be_id: str, plan_id: str, body: PlanRecognizeIn = Body(default_factory=PlanRecognizeIn)) -> dict[str, Any]:
    return await inputs.recognize_again(be_id, plan_id, body.page)


@router.post("/birdseyes/{be_id}/space/answers", response_model=SpaceModel, tags=["space"], summary="되묻기 답 · 치수 보정")
async def answer_space(be_id: str, body: AnswerIn, plan_id: str | None = None) -> dict[str, Any]:
    data = body.model_dump()
    data["plan_id"] = plan_id
    return await inputs.answer(be_id, data)


@router.post("/birdseyes/{be_id}/space:nl-edit", response_model=NlEditAccepted, status_code=202, tags=["space"],
             summary="말로 고치기(LLM 공간 연산)")
async def nl_edit_space(be_id: str, body: TextIn) -> dict[str, Any]:
    b = await svc.get(be_id)
    job_id = new_id("job")
    await jobs().enqueue("birdseye", "space_nl_edit", {"birdseye_id": be_id, "text": body.text}, title=f"{b['title']} · 말로 고치기",
                         ref=be_id, project_id=b.get("project_id"), owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"job_id": job_id, "status": "queued"}


@router.post("/birdseyes/{be_id}/photos", response_model=PhotoAccepted, status_code=202, tags=["space"],
             summary="현장 사진 올리기 · 다시 찍기(replace) · 천장 사진 · 415 FILE_TYPE_UNSUPPORTED")
async def add_photo(be_id: str, body: PhotoAdd) -> dict[str, Any]:
    return await inputs.add_photo(be_id, body.file_id, replace_photo_id=body.replace_photo_id, is_ceiling=body.is_ceiling)


@router.get("/birdseyes/{be_id}/photos", response_model=PhotoSet, tags=["space"])
async def list_photos(be_id: str) -> dict[str, Any]:
    return await inputs.photo_set(be_id)


@router.patch("/birdseyes/{be_id}/photos/{photo_id}", response_model=Photo, tags=["space"], summary="「그대로 사용」")
async def patch_photo(be_id: str, photo_id: str, body: PhotoPatch) -> dict[str, Any]:
    return await inputs.accept_photo(be_id, photo_id, body.accept)


@router.delete("/birdseyes/{be_id}/photos/{photo_id}", status_code=204, tags=["space"])
async def delete_photo(be_id: str, photo_id: str) -> Response:
    await inputs.delete_photo(be_id, photo_id)
    return Response(status_code=204)


@router.post("/birdseyes/{be_id}/photos/{photo_id}:recognize", response_model=PhotoAccepted, status_code=202, tags=["space"],
             summary="「다시 인식」")
async def recognize_photo(be_id: str, photo_id: str) -> dict[str, Any]:
    return await inputs.recognize_photo_again(be_id, photo_id)


@router.post("/birdseyes/{be_id}/space/facts", response_model=FactsOut, tags=["space"], summary="사진에 없는 정보 → 사실 칩 · 모델")
async def add_facts(be_id: str, body: TextIn) -> dict[str, Any]:
    return await inputs.add_facts(be_id, body.text)


@router.post("/birdseyes/{be_id}/upload-tokens", response_model=UploadToken, status_code=201, tags=["space"],
             summary="휴대폰 QR 업로드 토큰(30분)")
async def create_upload_token(be_id: str) -> dict[str, Any]:
    return await inputs.create_token(be_id)


@router.get("/upload-tokens/{token}", response_model=UploadTokenInfo, tags=["upload"], summary="모바일 업로드 페이지 정보 · 404")
async def get_upload_token(token: str) -> dict[str, Any]:
    return await inputs.token_info(token)


@router.get("/upload-tokens/{token}/principal", response_model=UploadTokenPrincipal, tags=["internal"],
            summary="게이트웨이 전용 — 업로드 토큰의 주인(로그인 없는 휴대폰 업로드 통과용)")
async def get_upload_token_principal(token: str) -> dict[str, Any]:
    return await inputs.token_principal(token)


@router.post("/upload-tokens/{token}/photos", response_model=PhotoAccepted, status_code=202, tags=["upload"],
             summary="휴대폰에서 올린 사진(토큰 인증) · 410 TOKEN_EXPIRED")
async def upload_token_photo(token: str, body: TokenPhotoIn) -> dict[str, Any]:
    return await inputs.token_photo(token, body.file_id)


# ── 제품 · 가구(§6.3) ────────────────────────────────────

@router.get("/product-search", response_model=ProductSearch, tags=["products"], summary="제품 검색(kb 결과를 표시용으로)")
async def product_search(q: str = "", limit: int = Query(5, ge=1, le=20)) -> dict[str, Any]:
    return {"items": await products.search(q, limit)}


@router.get("/birdseyes/{be_id}/products", response_model=ProductsView, tags=["products"])
async def get_products(be_id: str) -> dict[str, Any]:
    return await products.products_view(be_id)


@router.put("/birdseyes/{be_id}/products", response_model=list[ProductItem], tags=["products"])
async def put_products(be_id: str, body: ProductsPut) -> list[dict[str, Any]]:
    return await products.put_products(be_id, [p.model_dump() for p in body.items])


@router.post("/birdseyes/{be_id}/furniture:recommend", response_model=JobAccepted, status_code=202, tags=["furniture"],
             summary="가구 추천(다음 4개 · 보인 것 제외)")
async def recommend_furniture(be_id: str, body: FurnitureRecommendIn = Body(default_factory=FurnitureRecommendIn)) -> dict[str, Any]:
    b = await svc.get(be_id)
    if not await svc.products(be_id):
        raise ApiError(409, "PRODUCTS_REQUIRED", "배치할 제품을 먼저 추가해 주세요")
    job_id = new_id("job")
    await repo().patch("birdseyes", be_id, {"furniture_job_id": job_id})
    await jobs().enqueue("birdseye", "furniture_recommend", {"birdseye_id": be_id, "exclude": body.exclude}, title=f"{b['title']} · 가구 추천",
                         ref=be_id, project_id=b.get("project_id"), owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"job_id": job_id, "status": "queued"}


@router.get("/birdseyes/{be_id}/furniture", response_model=FurnitureView, tags=["furniture"])
async def get_furniture(be_id: str) -> dict[str, Any]:
    b = await svc.get(be_id)
    running = await _job_running(b.get("furniture_job_id"))
    return await furniture.furniture_view(be_id, b.get("furniture_job_id") if running else None, running)


@router.put("/birdseyes/{be_id}/furniture", response_model=list[FurnitureItem], tags=["furniture"],
            summary="선택 · 수량 · 직접 입력(카탈로그 일치 → 없으면 치수 추정) · 가구 없이")
async def put_furniture(be_id: str, body: FurniturePut) -> list[dict[str, Any]]:
    return await furniture.put(be_id, [i.model_dump() for i in body.items], body.none, body.replace)


# ── 레이아웃(§6.4) ───────────────────────────────────────

@router.post("/birdseyes/{be_id}/layout:generate", response_model=JobAccepted, status_code=202, tags=["layout"],
             summary="배치 의도(LLM) + 엔진 + 자동 조정 → 새 레이아웃(→ BE4)")
async def generate_layout(be_id: str, body: LayoutGenerateIn = Body(default_factory=LayoutGenerateIn)) -> dict[str, Any]:
    b = await svc.get(be_id)
    if await svc.space_model(be_id) is None:
        raise ApiError(409, "SPACE_NOT_READY", "공간 입력을 먼저 마쳐 주세요")
    if body.none:
        await furniture.put(be_id, [], True)
    job_id = new_id("job")
    await repo().patch("birdseyes", be_id, {"layout_job_id": job_id})
    await jobs().enqueue("birdseye", "layout_generate", {"birdseye_id": be_id, "none": body.none}, title=f"{b['title']} · 배치안",
                         ref=be_id, project_id=b.get("project_id"), owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"job_id": job_id, "status": "queued"}


@router.get("/birdseyes/{be_id}/layout", response_model=LayoutView, tags=["layout"], summary="배치안(레이아웃 + 평면 + 표시 겹)")
async def get_layout(be_id: str, version: int | None = None) -> dict[str, Any]:
    b = await svc.get(be_id)
    running = await _job_running(b.get("layout_job_id"))
    return await layouts.layout_view(be_id, version, running=running, job_id=b.get("layout_job_id") if running else None)


@router.post("/birdseyes/{be_id}/layout:validate", response_model=ValidateOut, tags=["layout"], summary="동기 검증(저장 안 함, ≤ 200ms)")
async def validate_layout(be_id: str, body: ValidateIn) -> dict[str, Any]:
    return await layouts.validate_ops(be_id, body.base_version, [o.model_dump(exclude_none=True) for o in body.ops])


@router.post("/birdseyes/{be_id}/layout-sessions", response_model=SessionCreated, status_code=201, tags=["layout"], summary="BE4E 편집 세션")
async def create_session(be_id: str) -> dict[str, Any]:
    return await layouts.create_session(be_id)


@router.get("/layout-sessions/{session_id}", response_model=SessionView, tags=["layout"])
async def get_session(session_id: str) -> dict[str, Any]:
    return await layouts.session_view(session_id)


@router.post("/layout-sessions/{session_id}/ops", response_model=SessionView, tags=["layout"], summary="연산 · 되돌리기 · 다시 실행")
async def session_ops(session_id: str, body: OpsIn) -> dict[str, Any]:
    return await layouts.session_ops(session_id, [o.model_dump(exclude_none=True) for o in body.ops], undo=body.undo, redo=body.redo)


@router.post("/layout-sessions/{session_id}/warnings/{warning_id}", response_model=SessionView, tags=["layout"],
             summary="경고 수정안 · 무시 · 메모 · 전원 위치 추가")
async def warning_action(session_id: str, warning_id: str, body: WarningActionIn) -> dict[str, Any]:
    return await layouts.warning_action(session_id, warning_id, body.action, body.fix_id, body.pos)


@router.post("/layout-sessions/{session_id}:autofix", response_model=SessionView, tags=["layout"], summary="경고 모두 자동 조정")
async def session_autofix(session_id: str) -> dict[str, Any]:
    return await layouts.session_autofix(session_id)


@router.post("/layout-sessions/{session_id}:commit", response_model=CommitOut, tags=["layout"], summary="수정 적용 → 새 레이아웃 버전")
async def session_commit(session_id: str) -> dict[str, Any]:
    return await layouts.commit(session_id)


@router.post("/layout-sessions/{session_id}:discard", response_model=CommitOut, tags=["layout"], summary="취소(세션 버림)")
async def session_discard(session_id: str) -> dict[str, Any]:
    return await layouts.discard(session_id)


@router.post("/birdseyes/{be_id}/layout:nl-edit", response_model=NlEditAccepted, status_code=202, tags=["layout"],
             summary="배치 수정 요청 · 말로 수정(LLM → 연산 → 엔진)")
async def nl_edit_layout(be_id: str, body: LayoutNlEditIn) -> dict[str, Any]:
    b = await svc.get(be_id)
    if not b.get("layout_version"):
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
    job_id = new_id("job")
    await jobs().enqueue("birdseye", "layout_nl_edit", {"birdseye_id": be_id, "text": body.text, "session_id": body.session_id},
                         title=f"{b['title']} · 배치 수정 요청", ref=be_id, project_id=b.get("project_id"), owner=b["owner"],
                         owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"job_id": job_id, "status": "queued"}


# ── 컷(§6.5) ─────────────────────────────────────────────

@router.post("/birdseyes/{be_id}/cuts", response_model=CutsAccepted, status_code=202, tags=["cuts"],
             summary="컷 만들기(컷마다 잡, 작업당 순차 · 같은 컷은 건너뜀)")
async def create_cuts(be_id: str, body: CutsCreate) -> dict[str, Any]:
    return await C.create_cuts(be_id, body.model_dump(exclude_none=True))


@router.get("/birdseyes/{be_id}/cuts", response_model=list[Cut], tags=["cuts"], summary="컷 목록(진행률 · 대기 순번)")
async def list_cuts(be_id: str) -> list[dict[str, Any]]:
    return await C.list_cuts(be_id)


@router.get("/cuts/{cut_id}", response_model=Cut, tags=["cuts"])
async def get_cut(cut_id: str) -> dict[str, Any]:
    c = await C.get_cut(cut_id)
    b = await svc.get(c["birdseye_id"])
    primary = await repo().get("cuts", b.get("primary_cut_id")) if b.get("primary_cut_id") else None
    return await C.cut_view(c, primary=primary)


@router.post("/cuts/{cut_id}:cancel", response_model=Cut, status_code=202, tags=["cuts"],
             summary="대기 컷은 즉시 빼기, 진행 컷은 초안 저장 후 중지")
async def cancel_cut(cut_id: str) -> dict[str, Any]:
    c = await C.cancel(cut_id)
    return await C.cut_view(c)


@router.patch("/cuts/{cut_id}", response_model=Cut, tags=["cuts"], summary="주 컷 지정")
async def patch_cut(cut_id: str, body: CutPatch) -> dict[str, Any]:
    if not body.is_primary:
        raise ApiError(400, "INVALID_ARGUMENT", "주 컷 지정만 할 수 있어요")
    c = await C.set_primary(cut_id)
    return await C.cut_view(c, primary=c)


@router.post("/birdseyes/{be_id}/result:edit", response_model=ResultEditOut, status_code=202, tags=["cuts"],
             summary="BE5 수정 요청(R8: 렌더 수정 · 배치 수정 → 재렌더 · 시점 컷)")
async def result_edit(be_id: str, body: ResultEditIn) -> dict[str, Any]:
    return await edits.request(be_id, body.text, body.cut_id)


# ── 존 포인트(§6.6) ──────────────────────────────────────

@router.post("/birdseyes/{be_id}/zones:auto", response_model=JobAccepted, status_code=202, tags=["zones"],
             summary="존 포인트 자동(군집 · 투영 · 문구)")
async def zones_auto(be_id: str, body: ZonesAutoIn = Body(default_factory=ZonesAutoIn)) -> dict[str, Any]:
    b = await svc.get(be_id)
    if not b.get("layout_version"):
        raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
    job_id = new_id("job")
    await repo().patch("birdseyes", be_id, {"zones_job_id": job_id})
    await jobs().enqueue("birdseye", "zones_auto", {"birdseye_id": be_id, "cut_id": body.cut_id}, title=f"{b['title']} · 존 포인트",
                         ref=be_id, project_id=b.get("project_id"), owner=b["owner"], owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"job_id": job_id, "status": "queued"}


@router.get("/birdseyes/{be_id}/zones", response_model=ZonesView, tags=["zones"])
async def get_zones(be_id: str, cut_id: str | None = None) -> dict[str, Any]:
    b = await svc.get(be_id)
    running = await _job_running(b.get("zones_job_id"))
    return await zones.zones_view(be_id, cut_id, running=running, job_id=b.get("zones_job_id") if running else None)


@router.post("/birdseyes/{be_id}/zones", response_model=ZonePoint, status_code=201, tags=["zones"], summary="빈 곳 클릭 · W 제안 수락")
async def add_zone(be_id: str, body: ZoneCreate) -> dict[str, Any]:
    return await zones.add_point(be_id, body.cut_id, body.u, body.v, body.from_suggestion)


@router.patch("/zones/{zone_id}", response_model=ZonePoint, tags=["zones"])
async def patch_zone(zone_id: str, body: ZonePatch) -> dict[str, Any]:
    return await zones.patch_zone(zone_id, body.model_dump(exclude_none=True))


@router.delete("/zones/{zone_id}", status_code=204, tags=["zones"])
async def delete_zone(zone_id: str) -> Response:
    await zones.delete_zone(zone_id)
    return Response(status_code=204)


@router.post("/birdseyes/{be_id}/zones:renumber-by-path", response_model=ZonesView, tags=["zones"], summary="동선 순서로 번호")
async def renumber_zones(be_id: str, cut_id: str | None = None) -> dict[str, Any]:
    await zones.renumber_by_path(be_id)
    return await zones.zones_view(be_id, cut_id)


@router.post("/birdseyes/{be_id}/zones:rewrite", response_model=NlEditAccepted, status_code=202, tags=["zones"],
             summary="포인트 문구 수정 요청(선택 존 또는 전체)")
async def rewrite_zones(be_id: str, body: ZonesRewriteIn) -> dict[str, Any]:
    b = await svc.get(be_id)
    job_id = new_id("job")
    await jobs().enqueue("birdseye", "zones_rewrite", {"birdseye_id": be_id, "text": body.text, "zone_ids": body.zone_ids},
                         title=f"{b['title']} · 존 문구 다듬기", ref=be_id, project_id=b.get("project_id"), owner=b["owner"],
                         owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"job_id": job_id, "status": "queued"}


# ── 내보내기 · 넘기기(§6.7 · §8) ─────────────────────────

@router.post("/birdseyes/{be_id}/exports", response_model=ExportAccepted, status_code=202, tags=["exports"],
             summary="ZIP(이미지 + 수량표.xlsx + sources.json) · PDF")
async def create_export(be_id: str, body: ExportCreate) -> dict[str, Any]:
    return await exporting.create_export(be_id, body.model_dump())


@router.get("/exports/{export_id}", response_model=ExportRecord, tags=["exports"])
async def get_export(export_id: str) -> dict[str, Any]:
    x = await repo().get("exports", export_id)
    if x is None:
        raise not_found("내보내기", export_id)
    return exporting.export_view(x)


@router.get("/birdseyes/{be_id}/export-options", response_model=ExportOptions, tags=["exports"], summary="BE6 이미지 목록 · 파일 이름 · 제안서 매핑")
async def export_options(be_id: str) -> dict[str, Any]:
    return await exporting.export_options(be_id)


@router.get("/birdseyes/{be_id}/quantities", response_model=Quantities, tags=["exports"], summary="제품 수량표(배치안 기준)")
async def quantities(be_id: str) -> dict[str, Any]:
    return await exporting.quantities(be_id)


@router.get("/birdseyes/{be_id}/handoff", response_model=Handoff, tags=["exports"], summary="제안서 · 시나리오용 묶음(§8)")
async def handoff(be_id: str, version: int | None = None) -> dict[str, Any]:
    return await exporting.handoff(be_id, version)


@router.get("/birdseyes/{be_id}/proposal-handoff", response_model=ProposalHandoff, tags=["exports"],
            summary="ProposalHandoff v1(10-proposal §8 · B1) — BV-A · BV-B · ZP · SM-B")
async def proposal_handoff(be_id: str, type_: Literal["standard", "quickwin", "solution"] = Query("standard", alias="type"),
                           section: str = "birdseye") -> dict[str, Any]:
    return await exporting.proposal_handoff(be_id, type_, section)


@router.get("/layouts/{be_id}/proposal-handoff", response_model=ProposalHandoff, tags=["exports"],
            summary="별칭(10-proposal §8.14 B1 경로) — /v1/birdseyes/{id}/proposal-handoff 와 같음")
async def proposal_handoff_alias(be_id: str, type_: Literal["standard", "quickwin", "solution"] = Query("standard", alias="type"),
                                 section: str = "birdseye") -> dict[str, Any]:
    return await exporting.proposal_handoff(be_id, type_, section)


@router.post("/birdseyes/{be_id}/usages", response_model=Usage, status_code=201, tags=INTERNAL, summary="쓰인 곳 등록(제안서 · 시나리오)")
async def add_usage(be_id: str, body: UsageIn) -> dict[str, Any]:
    return await svc.add_usage(be_id, body.model_dump())


@router.delete("/birdseyes/{be_id}/usages/{service_name}/{ref}", status_code=204, tags=INTERNAL)
async def remove_usage(be_id: str, service_name: str, ref: str) -> Response:
    await svc.remove_usage(be_id, service_name, ref)
    return Response(status_code=204)
