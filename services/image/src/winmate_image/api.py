"""image API (/v1). 이 파일의 엔드포인트가 contracts/image.json 이 된다(make contracts). 07-image §6."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse

from winmate_common.context import current_user
from winmate_common.errors import ApiError

from . import caps, exports, images, photos, refs, renders, requests_, runs, service
from .models import (
    AdjustIn, AlternativeIn, AlternativeResult, AnswersAccepted, AnswersIn, BulkExportIn, Capabilities, CaptionResult, DetectIn,
    Detections, EditIn, EditRegion, ExportIn, ExportOut, FilenameIn, FilenameResult, FulfillIn, ImageDetail, ImageInfo, ImageList,
    ImageRequest, InterpretIn, InterpretResult, JobAccepted, PlacementResult, PlacementsIn, Prefill, ProductsAdd, ProductsAdded,
    QueueList, Reference,
    ReferenceIn, ReferenceList, ReferencePatch, ReferenceSet, RefSearch, RegionCreated, RegionIn, RegionList, RegionPatch,
    RenderAccepted, RenderIn, RenderOut, RenditionsIn, RequestIn, RequestList, RequestStarted, RevertResult, RunAccepted,
    RunCancelResult, RunCreate, RunDetail, RunList, RunPatch, SaveResult, ServiceInfo, ShotCancelResult, SitePhoto,
    SitePhotoAccepted, SitePhotoIn, SitePhotoList, Usage, UsageIn, VariantsIn, Version, VersionList, Work, WorkCreate, WorkList,
    WorkPatch,
)
from .store import repo

router = APIRouter(prefix="/v1")
TITLE = "이미지 생성 — 유형 · 상세 조건 · 참조 이미지 · 현장 합성 · 부분 수정 · 변형 · 업스케일"


def _uid() -> str:
    return current_user().id


# ── 메타 · 능력 ──────────────────────────────────────────

@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="image", title=TITLE, version="0.1.0")


@router.get("/capabilities", response_model=Capabilities, tags=["meta"], summary="모델 능력 → 기능 플래그(60초 캐시)")
async def get_capabilities() -> dict:
    return await caps.capabilities()


# ── 작업 ─────────────────────────────────────────────────

@router.get("/works", response_model=WorkList, tags=["works"], summary="IMG0 작업 목록(최근 수정순)")
async def list_works(q: str | None = None, sort: Literal["updated_desc"] = "updated_desc", limit: int = Query(20, ge=1, le=100),
                     cursor: str | None = None) -> dict:
    uid = _uid()
    items = [w for w in await repo().all("works", where={"owner": uid}, order_by="-updated_at")
             if not w.get("deleted_at") and not w.get("internal")]
    if q and q.strip():
        qs = q.strip()
        items = [w for w in items if qs in (w.get("title") or "") or qs in (w.get("customer_name") or "")
                 or qs in (w.get("description") or "")]
    from .refs import _paginate

    page, nxt = _paginate(items, limit, cursor)
    gal = await images.list_images(owner=uid, origins=["image", "scenario"], kind=None, customer=None, aspect=None,
                                   in_proposal=None, q=None, work_id=None, saved=None, limit=1, cursor=None, include_running=True)
    n_images = gal["total"]
    return {"items": [await service.work_row(w) for w in page], "next_cursor": nxt,
            "totals": {"works": len(items), "images": n_images}}


@router.post("/works", response_model=Work, status_code=201, tags=["works"], summary="새 작업(IMG1 · 참조로 시작 · 현장 사진 합성)")
async def create_work(body: WorkCreate) -> dict:
    work = await service.create_work(kind=body.kind, description=body.description, project_id=body.project_id,
                                     customer_name=body.customer_name, request_id=body.request_id, start=body.start, title=body.title)
    for it in body.reference_items or []:
        await refs.add_reference(work["id"], it.model_dump(exclude_none=True))
    return await service.work_view(await service.get_work(work["id"]))


@router.get("/works/{work_id}", response_model=Work, tags=["works"])
async def get_work(work_id: str) -> dict:
    return await service.work_view(await service.get_work(work_id))


@router.patch("/works/{work_id}", response_model=Work, tags=["works"], summary="유형 · 설명 · 제목 · 조건 · 선택 시안(if_version → 409)")
async def patch_work(work_id: str, body: WorkPatch) -> dict:
    changes = body.model_dump(exclude_unset=True)
    changes.pop("if_version", None)
    if "conditions" in changes and body.conditions is not None:
        changes["conditions"] = body.conditions.model_dump()
    work = await service.patch_work(work_id, changes, body.if_version)
    return await service.work_view(work)


@router.post("/works/{work_id}:prefill", response_model=Prefill, tags=["works"], summary="R1 — 제품 · 수량 · 제목 · 검색어(동기, 10초)")
async def prefill_work(work_id: str) -> dict:
    res = await service.run_prefill(work_id)
    work = res.pop("work_doc")
    return {**res, "work": await service.work_view(work)}


@router.post("/works/{work_id}/products", response_model=ProductsAdded, tags=["works"],
             summary="셸 「현재 작업에 추가」 · 끌어 놓기(제품 참조 → KB 제품, 합성이면 배치 그룹)")
async def add_products(work_id: str, body: ProductsAdd) -> dict:
    res = await service.add_products(work_id, body.refs, body.qty)
    return {"added": res["added"], "work": await service.work_view(res["work"])}


@router.delete("/works/{work_id}", status_code=204, tags=["works"])
async def delete_work(work_id: str) -> Response:
    await service.delete_work(work_id)
    return Response(status_code=204)


# ── 참조 ─────────────────────────────────────────────────

@router.get("/reference-search", response_model=RefSearch, tags=["references"], summary="IMG2R 탭(kb · mine · cases) 검색")
async def reference_search(tab: Literal["kb", "mine", "cases"] = "kb", q: str | None = None, industry: str | None = None,
                           style: Literal["all", "photo", "illustration"] = "all", work_id: str | None = None,
                           limit: int = Query(8, ge=1, le=48), cursor: str | None = None) -> dict:
    return await refs.search(tab=tab, q=q, industry=industry, style=style, work_id=work_id, limit=limit, cursor=cursor, owner=_uid())


@router.get("/works/{work_id}/references", response_model=ReferenceList, tags=["references"])
async def list_references(work_id: str) -> dict:
    work = await service.get_work(work_id)
    view = await service.work_view(work)
    return {"items": view["references"], "notice": view["ref_notice"]}


@router.post("/works/{work_id}/references", response_model=Reference, status_code=201, tags=["references"],
             summary="참조 추가(최대 3 → 422 REFERENCE_LIMIT) · 분석은 비동기")
async def add_reference(work_id: str, body: ReferenceIn) -> dict:
    from .views import reference_view

    return reference_view(await refs.add_reference(work_id, body.model_dump(exclude_none=True)))


@router.put("/works/{work_id}/references", response_model=ReferenceList, tags=["references"], summary="IMG2R 「참조 n장 적용」(묶음 교체)")
async def set_references(work_id: str, body: ReferenceSet) -> dict:
    await refs.set_references(work_id, [i.model_dump(exclude_none=True) for i in body.items], body.via)
    view = await service.work_view(await service.get_work(work_id))
    return {"items": view["references"], "notice": view["ref_notice"]}


@router.patch("/works/{work_id}/references/{ref_id}", response_model=Reference, tags=["references"],
              summary="따를 요소 · 강도 · 순서(업로드 + 강 → 422 STRENGTH_NOT_ALLOWED)")
async def patch_reference(work_id: str, ref_id: str, body: ReferencePatch) -> dict:
    from .views import reference_view

    return reference_view(await refs.patch_reference(work_id, ref_id, body.model_dump(exclude_none=True)))


@router.delete("/works/{work_id}/references/{ref_id}", status_code=204, tags=["references"])
async def delete_reference(work_id: str, ref_id: str) -> Response:
    await refs.delete_reference(work_id, ref_id)
    return Response(status_code=204)


# ── 현장 사진 합성 ───────────────────────────────────────

@router.post("/works/{work_id}/site-photos", response_model=SitePhotoAccepted, status_code=202, tags=["composite"],
             summary="현장 사진 등록 → 인식 잡(202)")
async def add_site_photo(work_id: str, body: SitePhotoIn) -> dict:
    res = await photos.add_photo(work_id, body.file_id)
    return {"job_id": res["job_id"], "photo_id": res["photo"]["id"], "status": "queued", "photo": photos.photo_view(res["photo"])}


@router.get("/works/{work_id}/site-photos", response_model=SitePhotoList, tags=["composite"])
async def list_site_photos(work_id: str) -> dict:
    await service.get_work(work_id)
    items = await repo().all("photos", where={"work_id": work_id}, order_by="created_at")
    return {"items": [photos.photo_view(p) for p in items]}


@router.post("/works/{work_id}/site-photos/{photo_id}:recognize", response_model=SitePhotoAccepted, status_code=202,
             tags=["composite"], summary="다시 인식")
async def recognize_site_photo(work_id: str, photo_id: str) -> dict:
    res = await photos.recognize_again(work_id, photo_id)
    return {"job_id": res["job_id"], "photo_id": photo_id, "status": "queued", "photo": photos.photo_view(res["photo"])}


@router.delete("/works/{work_id}/site-photos/{photo_id}", status_code=204, tags=["composite"])
async def delete_site_photo(work_id: str, photo_id: str) -> Response:
    await photos.delete_photo(work_id, photo_id)
    return Response(status_code=204)


@router.put("/works/{work_id}/placements", response_model=PlacementResult, tags=["composite"],
            summary="배치 저장(300ms 디바운스) → 축척 · 실제 크기(가로 · 바닥에서) 계산")
async def put_placements(work_id: str, body: PlacementsIn) -> dict:
    return await photos.save_placements(work_id, body.model_dump())


# ── 생성 run · 대기열 ───────────────────────────────────

@router.post("/works/{work_id}/runs", response_model=RunAccepted, status_code=202, tags=["runs"],
             summary="생성 run(initial · composite · alternatives) — 사전 검사 포함 · 409 RUN_IN_PROGRESS")
async def create_run(work_id: str, body: RunCreate) -> dict:
    run = await runs.create_run(work_id, kind=body.kind, count=body.count, notify=body.notify)
    return {"job_id": run["job_id"], "run_id": run["id"], "status": run["status"], "precheck": run.get("precheck") or {}}


@router.get("/works/{work_id}/runs", response_model=RunList, tags=["runs"], summary="작업의 run(최근 순)")
async def list_runs(work_id: str, kind: str | None = None, active: bool = False) -> dict:
    await service.get_work(work_id)
    items = await repo().all("runs", where={"work_id": work_id}, order_by="-created_at", limit=100)
    if kind:
        kinds = set(kind.split(","))
        items = [r for r in items if r.get("kind") in kinds]
    if active:
        items = [r for r in items if r.get("status") in ("queued", "running", "awaiting_input")]
    return {"items": [await runs.run_detail(r) for r in items[:20]]}


@router.get("/runs/{run_id}", response_model=RunDetail, tags=["runs"])
async def get_run(run_id: str) -> dict:
    return await runs.run_detail(await runs.get_run(run_id))


@router.patch("/runs/{run_id}", response_model=RunDetail, tags=["runs"], summary="「완료되면 알림」")
async def patch_run(run_id: str, body: RunPatch) -> dict:
    return await runs.run_detail(await runs.set_notify(run_id, body.notify))


@router.post("/runs/{run_id}:cancel", response_model=RunCancelResult, status_code=202, tags=["runs"],
             summary="전체 취소(끝난 시안은 남긴다)")
async def cancel_run(run_id: str) -> dict:
    run = await runs.cancel_run(run_id)
    return {"run_id": run_id, "status": run.get("status") or "canceled"}


@router.post("/runs/{run_id}/shots/{image_id}:cancel", response_model=ShotCancelResult, tags=["runs"],
             summary="「이 장 취소」(대기 시안은 바로, 진행 시안은 결과 폐기)")
async def cancel_shot(run_id: str, image_id: str) -> dict:
    img = await runs.cancel_shot(run_id, image_id)
    return {"image_id": image_id, "status": img.get("status") or "canceled"}


@router.post("/runs/{run_id}/answers", response_model=AnswersAccepted, status_code=202, tags=["runs"],
             summary="IMG3X 대안 → jobs 입력(같은 thread 재개)")
async def answer_run(run_id: str, body: AnswersIn) -> dict:
    run = await runs.answer(run_id, body.model_dump())
    return {"run_id": run_id, "job_id": run.get("job_id"), "status": run.get("status") or "queued"}


@router.post("/runs/{run_id}/alternatives", response_model=AlternativeResult, tags=["runs"],
             summary="「다른 대안 입력」 — LLM 이 사유를 판정, 정책 재검사 통과 시 custom 대안으로 저장")
async def custom_alternative(run_id: str, body: AlternativeIn) -> dict:
    res = await runs.custom_alternative(run_id, body.text)
    return {**res, "run": await runs.run_detail(res["run"])}


@router.get("/queue", response_model=QueueList, tags=["runs"], summary="내 대기열(다음 차례 · k번째)")
async def get_queue(mine: bool = True) -> dict:
    return await runs.queue_for(_uid())


# ── 시안 · 버전 · 편집 ──────────────────────────────────

@router.get("/images", response_model=ImageList, tags=["images"],
            summary="내 생성 이미지(IMG0 갤러리 · 셸 「내 생성 이미지」 탭 · IMG2R)")
async def list_images(owner: str | None = Query(None, description="me = 내 이미지"), mine: bool = True,
                      origin: str = Query("image,scenario"), kind: str | None = None, customer: str | None = None,
                      aspect: str | None = None, in_proposal: bool | None = None, q: str | None = None, work_id: str | None = None,
                      saved: bool | None = None, running: bool | None = Query(None, description="생성 중 타일 포함(기본: owner=me 면 제외)"),
                      sort: Literal["created_desc"] = "created_desc",
                      limit: int = Query(24, ge=1, le=100), cursor: str | None = None) -> dict:
    if running is None:
        running = owner != "me"
    return await images.list_images(owner=_uid(), origins=[o for o in origin.split(",") if o], kind=kind, customer=customer,
                                    aspect=aspect, in_proposal=in_proposal, q=q, work_id=work_id, saved=saved, limit=limit,
                                    cursor=cursor, include_running=running)


@router.post("/images:bulk-export", response_model=ExportOut, status_code=202, tags=["exports"], summary="선택 시안 ZIP(export 잡)")
async def bulk_export(body: BulkExportIn) -> dict:
    return await exports.bulk_export(body.model_dump())


@router.get("/images/{image_id}", response_model=ImageDetail, tags=["images"],
            summary="시안 + 버전(제안서 I1: file_id · rights · caption_rule · scene · prompt)")
async def get_image(image_id: str) -> dict:
    return await images.image_detail(await images.get_image(image_id))


@router.get("/images/{image_id}/info", response_model=ImageInfo, tags=["images"], summary="상단바 이미지 정보 행(§5.2)")
async def get_image_info(image_id: str, version_id: str | None = None) -> dict:
    return await images.image_info(await images.get_image(image_id), version_id)


@router.post("/images/{image_id}:save", response_model=SaveResult, tags=["images"], summary="「내 이미지에 저장」")
async def save_image(image_id: str) -> dict:
    return await images.save_image_flag(image_id)


@router.get("/images/{image_id}/versions", response_model=VersionList, tags=["images"])
async def list_versions(image_id: str) -> dict:
    img = await images.get_image(image_id)
    from .views import version_view

    return {"items": [version_view(v, image=img) for v in await images.versions_of(image_id)]}


@router.post("/images/{image_id}/versions/{n}/restore", response_model=Version, tags=["images"],
             summary="그 버전 내용으로 새 현재 버전(이전 버전은 남는다)")
async def restore_version(image_id: str, n: int) -> dict:
    img = await images.get_image(image_id)
    v = await images.restore_version(image_id, n)
    from .views import version_view

    return version_view(v, image=await images.get_image(img["id"]))


@router.get("/versions/{version_id}", response_model=Version, tags=["images"],
            summary="버전 하나(렌디션 · 생성 메타) — 제안서 · 시나리오 · 조감도가 읽는다")
async def get_version(version_id: str) -> dict:
    v = await repo().get("versions", version_id)
    if v is None:
        raise ApiError(404, "NOT_FOUND", f"버전을 찾을 수 없습니다: {version_id}", {"resource": "버전", "id": version_id})
    from .views import version_view

    return version_view(v, image=await repo().get("images", v["image_id"]))


@router.post("/images/{image_id}/detections", response_model=Detections, tags=["edit"],
             summary="객체 · 글자 · 사람 · 화면 감지(캐시) — bbox 미지원이면 422 CAPABILITY_UNSUPPORTED")
async def detect(image_id: str, body: DetectIn) -> dict:
    return await images.detections(await images.get_image(image_id), list(body.kinds), body.version_id)


@router.get("/images/{image_id}/regions", response_model=RegionList, tags=["edit"])
async def list_regions(image_id: str) -> dict:
    await images.get_image(image_id)
    return {"items": [images.region_view(r) for r in await images.regions_of(image_id)]}


@router.post("/images/{image_id}/regions", response_model=RegionCreated, status_code=201, tags=["edit"],
             summary="수정 영역(사각형 · 브러시 · 객체) · 칩(글자 지우기 · 사람 지우기 · 제품 화면에 콘텐츠)")
async def create_region(image_id: str, body: RegionIn) -> dict:
    return await images.create_region(image_id, body.model_dump(exclude_none=True))


@router.patch("/images/{image_id}/regions/{region_id}", response_model=EditRegion, tags=["edit"])
async def patch_region(image_id: str, region_id: str, body: RegionPatch) -> dict:
    return images.region_view(await images.patch_region(image_id, region_id, body.model_dump(exclude_none=True)))


@router.delete("/images/{image_id}/regions/{region_id}", status_code=204, tags=["edit"])
async def delete_region(image_id: str, region_id: str) -> Response:
    await images.delete_region(image_id, region_id)
    return Response(status_code=204)


@router.post("/images/{image_id}/regions/{region_id}:revert", response_model=RevertResult, tags=["edit"],
             summary="영역 되돌리기 — 현재 버전을 그 영역의 기준 버전으로(버전은 남는다)")
async def revert_region(image_id: str, region_id: str) -> dict:
    return await images.revert_region(image_id, region_id)


@router.post("/images/{image_id}/edits", response_model=JobAccepted, status_code=202, tags=["edit"],
             summary="부분 · 전체 수정 run(영역마다 번호 순 새 버전)")
async def start_edit(image_id: str, body: EditIn) -> dict:
    return await images.start_edit(image_id, body.model_dump())


@router.post("/images/{image_id}/adjust", response_model=Version, tags=["edit"],
             summary="동기 로컬 보정(밝기 올리기 · 주변과 밝기 맞추기) — 모델 호출 없음")
async def adjust_image(image_id: str, body: AdjustIn) -> dict:
    v = await images.adjust(image_id, body.model_dump())
    from .views import version_view

    return version_view(v, image=await images.get_image(image_id))


@router.post("/images/{image_id}/variants", response_model=JobAccepted, status_code=202, tags=["edit"],
             summary="변형 run(4장 · 조명만 · 손님 넣기)")
async def start_variants(image_id: str, body: VariantsIn) -> dict:
    return await images.start_variants(image_id, body.model_dump())


@router.post("/images/{image_id}/renditions", response_model=JobAccepted, status_code=202, tags=["edit"],
             summary="비율 · 해상도 run(새 시안) — 능력 부족이면 422 CAPABILITY_UNSUPPORTED")
async def start_renditions(image_id: str, body: RenditionsIn) -> dict:
    return await images.start_renditions(image_id, body.model_dump())


@router.post("/images/{image_id}:interpret", response_model=InterpretResult, tags=["edit"],
             summary="R6 자유 입력(수정 요청 · 변형 요청 · 내보내기 요청) → 구조화 동작")
async def interpret(image_id: str, body: InterpretIn) -> dict:
    return await images.interpret(image_id, body.text, body.screen)


@router.post("/images/{image_id}/caption", response_model=CaptionResult, tags=["exports"], summary="「캡션 자동 작성」")
async def make_caption(image_id: str) -> dict:
    return {"caption": await images.caption(image_id)}


@router.post("/images/{image_id}/filename", response_model=FilenameResult, tags=["exports"], summary="「영문 파일명」")
async def make_filename(image_id: str, body: FilenameIn) -> dict:
    if body.lang == "en":
        return {"filename": await images.english_filename(image_id, body.ext, body.version_id)}
    img = await images.get_image(image_id)
    work = await repo().get("works", img["work_id"]) or {}
    ver = await repo().get("versions", body.version_id or img.get("current_version_id")) or {}
    return {"filename": exports.default_filename(img, work, ver, body.ext)}


@router.post("/images/{image_id}/usages", response_model=Usage, status_code=201, tags=["internal"],
             summary="사용 등록 — 제안서 · 시나리오 · 조감도가 호출")
async def add_usage(image_id: str, body: UsageIn) -> dict:
    return await images.add_usage(image_id, body.model_dump())


@router.delete("/images/{image_id}/usages/{service_name}/{ref}", status_code=204, tags=["internal"])
async def delete_usage(image_id: str, service_name: str, ref: str) -> Response:
    await images.delete_usage(image_id, service_name, ref)
    return Response(status_code=204)


# ── 내보내기 ─────────────────────────────────────────────

@router.post("/images/{image_id}/exports", response_model=ExportOut, tags=["exports"],
             responses={202: {"model": ExportOut, "description": "export 서비스 잡(PDF · PPTX · ZIP)"}},
             summary="PNG · JPG 는 바로(200), PDF · PPTX · 원본 함께(ZIP)는 export 잡(202)")
async def export_image(image_id: str, body: ExportIn) -> JSONResponse:
    status, out = await exports.export_image(image_id, body.model_dump())
    return JSONResponse(ExportOut(**out).model_dump(), status_code=status)


@router.get("/exports/{export_id}", response_model=ExportOut, tags=["exports"])
async def get_export(export_id: str) -> dict:
    return await exports.get_export(export_id)


# ── 다른 기능의 요청 ─────────────────────────────────────

@router.post("/requests", response_model=ImageRequest, status_code=201, tags=["internal"],
             summary="다른 기능의 이미지 요청(서비스 간 — scenario · proposal)")
async def create_request(body: RequestIn) -> dict:
    return requests_.request_view(await requests_.create_request(body.model_dump()))


@router.get("/requests", response_model=RequestList, tags=["requests"],
            summary="IMG0 「다른 기능에서 요청한 이미지」(status=open,in_progress) · 요청자 조회(from_service · from_ref)")
async def list_requests(status: str | None = None, from_service: str | None = None, from_ref: str | None = None) -> dict:
    statuses = [s for s in (status or "").split(",") if s] or None
    items = await requests_.list_requests(owner=_uid(), statuses=statuses, from_service=from_service, from_ref=from_ref)
    return {"items": [requests_.request_view(r) for r in items]}


@router.get("/requests/{request_id}", response_model=ImageRequest, tags=["requests"])
async def get_request(request_id: str) -> dict:
    return requests_.request_view(await requests_.get_request(request_id))


@router.post("/requests/{request_id}:start", response_model=RequestStarted, tags=["requests"],
             summary="「만들기」 — 작업을 만들고 경로(IMG1 route · IMG2 conditions_route)를 준다")
async def start_request(request_id: str) -> dict:
    return await requests_.start_request(request_id)


@router.post("/requests/{request_id}:fulfill", response_model=ImageRequest, tags=["requests"],
             summary="요청을 이 버전으로 충족(IMG4 「공간 시나리오 장면으로」)")
async def fulfill_request(request_id: str, body: FulfillIn) -> dict:
    return requests_.request_view(await requests_.fulfill_request(request_id, body.version_id))


@router.post("/requests/{request_id}:dismiss", response_model=ImageRequest, tags=["requests"])
async def dismiss_request(request_id: str) -> dict:
    return requests_.request_view(await requests_.dismiss_request(request_id))


# ── 렌더 API(birdseye · scenario) ───────────────────────

@router.post("/renders", response_model=RenderAccepted, status_code=202, tags=["internal"],
             summary="렌더 API — 생성 · 편집(edit_of) · 구조 참조 · 업스케일 · 품질 확인 · AI 메타")
async def create_render(body: RenderIn) -> dict:
    return await renders.create_render(body.model_dump())


@router.get("/renders/{render_id}", response_model=RenderOut, tags=["internal"])
async def get_render(render_id: str) -> dict:
    return await renders.get_render(render_id)


@router.post("/renders/{render_id}:cancel", response_model=RenderOut, status_code=202, tags=["internal"])
async def cancel_render(render_id: str) -> dict:
    return await renders.cancel_render(render_id)
