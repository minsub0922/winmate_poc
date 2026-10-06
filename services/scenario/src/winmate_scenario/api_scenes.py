"""scenario API (/v1) — 장면(SC4 · SC4E): 목록 · 하나 · 직접 고치기(locked) · 다시 쓰기 · 버전 · 되돌리기 · 삭제 · 추가 ·
수정 요청 · 더 짧게 · 장면 이미지(요청 · 붙이기 · 일괄 렌더 · 충족 확인 · 넘어가는 것)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Response
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso

from . import imaging, repo, seed, service
from . import models as m
from . import timeline as tl

log = logging.getLogger("winmate.scenario.api")
router = APIRouter(prefix="/v1")
TAG = ["scenes"]


async def find_scene(scene_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    sc_id = await repo.scenario_of_scene(scene_id)
    doc = await repo.get_sc(sc_id) if sc_id else None
    sc = tl.scene_by_id(doc, scene_id) if doc and not doc.get("deleted_at") else None
    if doc is None or sc is None:
        raise ApiError(404, "NOT_FOUND", f"장면을 찾을 수 없어요: {scene_id}", {"resource": "장면", "id": scene_id})
    return doc, sc


async def _out(doc: dict[str, Any], sc: dict[str, Any], *, with_prev: bool = True) -> m.SceneOut:
    prev = await service.prev_snapshot(sc) if with_prev else None
    return m.SceneOut(**service.scene_out(doc, sc, prev))


@router.get("/scenarios/{sc_id}/scenes", response_model=m.SceneList, tags=TAG)
async def list_scenes(sc_id: str) -> m.SceneList:
    doc = await repo.require_sc(sc_id)
    items = [m.SceneOut(**service.scene_out(doc, s)) for s in tl.scenes(doc)]
    return m.SceneList(items=items, locked_nos=[s.no for s in items if s.locked])


@router.get("/scenes/{scene_id}", response_model=m.SceneOut, tags=TAG)
async def get_scene(scene_id: str) -> m.SceneOut:
    doc, sc = await find_scene(scene_id)
    return await _out(doc, sc)


@router.patch("/scenes/{scene_id}", response_model=m.SceneOut, tags=TAG)
async def patch_scene(scene_id: str, body: m.PatchScene) -> m.SceneOut:
    """「변경 저장」: 직접 고친 필드가 있으면 locked=true · 새 버전(「직접 수정」)."""
    doc, _ = await find_scene(scene_id)
    data = body.model_dump(exclude_unset=True)
    expected = data.pop("if_version", None)

    def fn(d: dict[str, Any]) -> dict[str, Any] | None:
        service.require_editable(d)
        s = tl.scene_by_id(d, scene_id)
        if s is None:
            raise ApiError(404, "NOT_FOUND", "장면을 찾을 수 없어요")
        if expected is not None and int(s.get("version") or 0) != int(expected):
            raise ApiError(409, "VERSION_CONFLICT", "다른 곳에서 이 장면을 먼저 고쳤어요. 새로 불러온 뒤 다시 저장해 주세요.",
                           {"version": s.get("version")})
        prev = service.scene_snapshot(s)
        changed = False
        if data.get("title") is not None and data["title"].strip() != (s.get("title") or ""):
            s["title"] = data["title"].strip()
            changed = True
        if data.get("story") is not None and data["story"].strip() != (s.get("story") or ""):
            s["story"] = data["story"].strip()
            changed = True
        if data.get("characters") is not None:
            ids = [rid for rid in data["characters"] if tl.role_by_id(d, rid)]
            if ids != [c.get("role_id") for c in s.get("characters") or []]:
                old = {c["role_id"]: c for c in s.get("characters") or []}
                s["characters"] = [old.get(rid) or {"role_id": rid, "is_new": True} for rid in ids]
                for rid in ids:
                    if not any(b.get("role_id") == rid for b in s.get("beats") or []):
                        s.setdefault("beats", []).append(tl.new_beat(rid, ""))
                s["beats"] = [b for b in s.get("beats") or [] if b.get("role_id") in ids or not b.get("role_id")] or s.get("beats") or []
                changed = True
        if data.get("solutions") is not None:
            sols = []
            for x in data["solutions"]:
                if seed.action(x["solution_id"], x["action_code"]):
                    sols.append({"solution_id": x["solution_id"], "action_code": x["action_code"],
                                 "label": seed.action_label(x["solution_id"], x["action_code"]), "is_new": False})
            if [service.sol_key(a) for a in sols] != [service.sol_key(a) for a in s.get("solutions") or []]:
                s["solutions"] = sols
                changed = True
        if data.get("products") is not None:
            prods = [{k: p.get(k) for k in ("ref", "family_id", "model_code", "short", "label", "qty")} | {"is_new": False}
                     for p in data["products"]]
            if [service.product_key(p) for p in prods] != [service.product_key(p) for p in s.get("products") or []]:
                s["products"] = prods
                changed = True
        if not changed:
            return None
        service.finalize_text(d, s)
        service.mark_new(s, prev)
        s["locked"] = True
        s["status"] = "done"
        service.bump_scene(s, "직접 수정")
        d["dirty"] = True
        return d
    doc = await repo.update(doc["id"], fn)
    sc = tl.scene_by_id(doc, scene_id)
    await service.commit_scene_versions(doc, [scene_id], "직접 수정")
    return await _out(doc, sc)  # type: ignore[arg-type]


@router.post("/scenes/{scene_id}:rewrite", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def rewrite_scene(scene_id: str, body: m.RewriteRequest) -> m.JobAccepted:
    """「이 장면만 다시 쓰기」 — 다른 장면은 그대로, 새 버전(v+1)."""
    doc, sc = await find_scene(scene_id)
    service.require_editable(doc)
    if body.preset == "pov" and not body.pov_role_id:
        raise ApiError(400, "POV_REQUIRED", "어느 역할 시점으로 쓸지 고르세요")
    reason = {"shorter": "더 짧게", "pov": "시점 바꿈", "solution_detail": "솔루션 동작 구체화"}.get(body.preset or "", "방금 수정 요청 반영")
    if body.preset == "pov":
        r = tl.role_by_id(doc, body.pov_role_id)
        reason = f"{r['name']} 시점으로" if r else reason
    job_id = await service.enqueue("sc.rewrite_scene", doc, {"scene_id": scene_id, "preset": body.preset, "pov_role_id": body.pov_role_id,
                                                              "instruction": body.instruction, "reason": reason},
                                   title=f"장면 {sc['no']} 다시 쓰기")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = tl.scene_by_id(d, scene_id)
        if s:
            s["rewriting"] = True
        service.set_active(d, job_id, "rewrite_scene", scene_id)
        return d
    await repo.update(doc["id"], fn)
    return m.JobAccepted(job_id=job_id)


@router.get("/scenes/{scene_id}/versions", response_model=m.SceneVersionList, tags=TAG)
async def scene_versions(scene_id: str) -> m.SceneVersionList:
    await find_scene(scene_id)
    items = await repo.list_scene_versions(scene_id)
    return m.SceneVersionList(items=[m.SceneVersion(n=v["n"], reason=v.get("reason") or "", created_at=v.get("created_at") or "",
                                                    title=(v.get("scene") or {}).get("title") or "") for v in items])


@router.post("/scenes/{scene_id}/versions/{n}/restore", response_model=m.SceneOut, tags=TAG)
async def restore_scene_version(scene_id: str, n: int) -> m.SceneOut:
    """「v{k-1}로 되돌리기」: v{n} 내용으로 새 버전(지난 버전은 남는다)."""
    doc, _ = await find_scene(scene_id)
    v = await repo.get_scene_version(scene_id, n)
    if v is None:
        raise ApiError(404, "NOT_FOUND", f"장면 버전 v{n}을(를) 찾을 수 없어요")
    snap = v.get("scene") or {}
    reason = f"v{n}로 되돌림"

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.require_editable(d)
        s = tl.scene_by_id(d, scene_id)
        if s is None:
            raise ApiError(404, "NOT_FOUND", "장면을 찾을 수 없어요")
        prev = service.scene_snapshot(s)
        for k in service.SNAP_KEYS:
            if k in snap:
                s[k] = snap[k]
        service.mark_new(s, prev)
        service.bump_scene(s, reason)
        d["dirty"] = True
        return d
    doc = await repo.update(doc["id"], fn)
    await service.commit_scene_versions(doc, [scene_id], reason)
    return await _out(doc, tl.scene_by_id(doc, scene_id))  # type: ignore[arg-type]


@router.delete("/scenes/{scene_id}", status_code=204, tags=TAG)
async def delete_scene(scene_id: str) -> Response:
    """장면 삭제 — 번호가 다시 매겨지고 시트 계획이 다시 계산된다(시트 계획은 읽을 때 계산)."""
    doc, sc = await find_scene(scene_id)
    if sc.get("image"):
        await imaging.remove_usage(sc)

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.require_editable(d)
        d["scenes"] = [s for s in d.get("scenes") or [] if s["id"] != scene_id]
        tl.normalize(d)
        d["dirty"] = True
        return d
    doc = await repo.update(doc["id"], fn)
    await service.register(doc)
    return Response(status_code=204)


@router.post("/scenarios/{sc_id}/scenes", response_model=m.SceneOut, status_code=201, tags=TAG)
async def add_scene(sc_id: str, body: m.AddSceneRequest) -> m.SceneOut:
    """SC4E 「장면 추가」: 현재 장면 다음 시간대에 빈 장면(다음 시간대가 없으면 새 시간대)."""
    created: list[str] = []

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.require_editable(d)
        created.clear()
        sl = tl.slots(d)
        after = tl.scene_by_id(d, body.after_scene_id) if body.after_scene_id else (tl.scenes(d)[-1] if d.get("scenes") else None)
        idx = next((i for i, s in enumerate(sl) if after and s["id"] == after["slot_id"]), len(sl) - 1)
        if idx + 1 < len(sl) and not any(s["slot_id"] == sl[idx + 1]["id"] for s in d.get("scenes") or []):
            slot = sl[idx + 1]
        else:
            slot = tl.new_slot("새 장면", None, is_new=True)
            sl.insert(idx + 1, slot)
            d["slots"] = sl
        sc = tl.new_scene(slot["id"], [], is_new=False)
        sc["title"] = body.title or f"{slot['label']} — 새 장면"
        d["scenes"].append(sc)
        tl.normalize(d)
        created.append(sc["id"])
        d["dirty"] = True
        return d
    doc = await repo.update(sc_id, fn)
    return await _out(doc, tl.scene_by_id(doc, created[0]), with_prev=False)  # type: ignore[arg-type]


@router.post("/scenarios/{sc_id}:edit", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def edit_request(sc_id: str, body: m.TextRequest) -> m.JobAccepted:
    """SC4 「수정 요청」 → LLM 시나리오 연산 → 영향 장면만 다시 쓰기(화면 이동 없음)."""
    doc = await repo.require_sc(sc_id)
    service.require_editable(doc)
    job_id = await service.enqueue("sc.edit", doc, {"text": body.text}, title="시나리오 수정 요청")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        service.set_active(d, job_id, "edit")
        return d
    await repo.update(sc_id, fn)
    return m.JobAccepted(job_id=job_id)


@router.post("/scenarios/{sc_id}:shorten", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def shorten(sc_id: str) -> m.JobAccepted:
    doc = await repo.require_sc(sc_id)
    service.require_editable(doc)
    job_id = await service.enqueue("sc.shorten", doc, {}, title="모든 장면 더 짧게")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        for s in d.get("scenes") or []:
            if s.get("story"):
                s["rewriting"] = True
        service.set_active(d, job_id, "shorten")
        return d
    await repo.update(sc_id, fn)
    return m.JobAccepted(job_id=job_id)


# ── 장면 이미지 ─────────────────────────────────────────────

@router.post("/scenes/{scene_id}/image-request", response_model=m.ImageRequestOut, status_code=201, tags=TAG)
async def image_request(scene_id: str) -> m.ImageRequestOut:
    """「이미지 생성」: image 요청 + :start(대리) → 웹이 IMG2(미리 채움)로 이동. 충족되면 SC4 · SC4E 를 열 때 붙는다."""
    doc, sc = await find_scene(scene_id)
    try:
        res = await imaging.create_request(doc, sc)
    except ApiError as exc:
        raise ApiError(exc.status if exc.status >= 400 else 502, "IMAGE_REQUEST_FAILED", "이미지 생성 요청을 만들지 못했어요. 잠시 후 다시 시도해 주세요.",
                       {"upstream": exc.code}) from exc

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = tl.scene_by_id(d, scene_id)
        if s:
            s["image_request_id"] = res["request_id"]
        return d
    await repo.update(doc["id"], fn)
    return m.ImageRequestOut(**res)


async def attach_version(doc: dict[str, Any], scene_id: str, version_id: str, source: str, request_id: str | None = None) -> dict[str, Any]:
    sc = tl.scene_by_id(doc, scene_id)
    if sc is None:
        raise ApiError(404, "NOT_FOUND", "장면을 찾을 수 없어요")
    if version_id.startswith("kb:image:"):
        block = imaging.kb_block(doc, sc, version_id.split(":", 2)[2])
    else:
        try:
            block = await imaging.image_block(doc, sc, version_id, source)
        except ApiError as exc:
            raise ApiError(404 if exc.status == 404 else 502, "IMAGE_VERSION_NOT_FOUND", "이미지 버전을 읽지 못했어요", {"upstream": exc.code}) from exc
    old_image = sc.get("image")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        s = tl.scene_by_id(d, scene_id)
        if s:
            s["image"] = block
            s["image_stale_forced"] = False
            s["image_job"] = None
            if request_id:
                s["image_request_id"] = request_id
        d["dirty"] = True
        return d
    doc = await repo.update(doc["id"], fn)
    if old_image and old_image.get("image_id") and old_image.get("image_id") != block.get("image_id"):
        await imaging.remove_usage({"id": scene_id, "image": old_image})
    await imaging.register_usage(doc, tl.scene_by_id(doc, scene_id) or sc, block.get("image_id"), version_id)
    return doc


@router.post("/scenes/{scene_id}/image:attach", response_model=m.SceneOut, tags=TAG)
async def image_attach(scene_id: str, body: m.AttachImage) -> m.SceneOut:
    """고르기 모드(사내 자산 · 내 이미지) · 요청 충족 결과를 장면에 붙인다(조건 스냅숏 저장 → stale 판정)."""
    doc, _ = await find_scene(scene_id)
    version_id = body.image_version_id
    ref = (body.image_ref or "").strip()
    if not version_id and ref.startswith("img:image:"):
        try:
            version_id = await imaging.current_version(ref.split(":", 2)[2])
        except ApiError as exc:
            raise ApiError(404 if exc.status == 404 else 502, "IMAGE_NOT_FOUND", "이미지를 읽지 못했어요", {"upstream": exc.code}) from exc
    elif not version_id and ref.startswith("kb:image:"):
        version_id = ref
    if not version_id:
        raise ApiError(400, "IMAGE_REQUIRED", "붙일 이미지를 고르세요")
    doc = await attach_version(doc, scene_id, version_id, body.source, body.request_id)
    return await _out(doc, tl.scene_by_id(doc, scene_id))  # type: ignore[arg-type]


@router.post("/scenarios/{sc_id}/images:sync", response_model=m.ImagesSync, tags=TAG)
async def images_sync(sc_id: str) -> m.ImagesSync:
    """SC4 · SC4E 를 열 때: 장면마다 image 요청이 충족(fulfilled)됐고 아직 안 붙었으면 붙인다."""
    doc = await repo.require_sc(sc_id)
    attached: list[str] = []
    for sc in tl.scenes(doc):
        if not sc.get("image_request_id"):
            continue
        reqs = await imaging.fulfilled_requests(sc["id"])
        if not reqs:
            continue
        last = reqs[-1]
        if (sc.get("image") or {}).get("version_id") == last["result_version_id"]:
            continue
        doc = await attach_version(doc, sc["id"], last["result_version_id"], "image_flow", last["id"])
        attached.append(sc["id"])
    return m.ImagesSync(attached=attached)


@router.post("/scenarios/{sc_id}/images:generate-missing", response_model=m.JobAccepted, status_code=202, tags=TAG)
async def images_generate_missing(sc_id: str) -> m.JobAccepted:
    """「장면별 이미지 모두 생성」: 이미지 없는 장면마다 렌더 API 로 1장씩(동시 1, 16:9 · fhd), 끝날 때마다 붙임."""
    doc = await repo.require_sc(sc_id)
    missing = [s for s in tl.scenes(doc) if not s.get("image") and s.get("story")]
    if not missing:
        raise ApiError(400, "NOTHING_TO_GENERATE", "이미지가 없는 장면이 없어요")
    aj = doc.get("images_job") or {}
    if aj.get("job_id"):
        from winmate_common.jobs import jobs
        job = await jobs().get(aj["job_id"])
        if job and job.status in ("queued", "running"):
            return m.JobAccepted(job_id=job.id, status=job.status)
    job_id = await service.enqueue("sc.images_batch", doc, {}, title="장면별 이미지 모두 생성")

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["images_job"] = {"job_id": job_id, "started_at": now_iso(), "scene_ids": [s["id"] for s in missing]}
        for s in d.get("scenes") or []:
            if s["id"] in {x["id"] for x in missing}:
                s["image_job"] = {"status": "queued", "render_id": None, "error": None}
        return d
    await repo.update(sc_id, fn)
    return m.JobAccepted(job_id=job_id)


@router.post("/image-returns", response_model=m.ImageReturnOut, tags=TAG)
async def image_return(body: m.ImageReturn) -> m.ImageReturnOut:
    """IMG4 「공간 시나리오 장면으로」 → `/scenario?image_version=imv_…&request=irq_…`: 그 요청을 낸 장면을 찾아 붙이고 SC4E 경로를 준다."""
    from winmate_common.context import current_user
    for doc in await repo.list_sc({"owner": current_user().id}):
        for sc in doc.get("scenes") or []:
            if sc.get("image_request_id") == body.request_id:
                doc = await attach_version(doc, sc["id"], body.image_version_id, "image_flow", body.request_id)
                return m.ImageReturnOut(scenario_id=doc["id"], scene_id=sc["id"], route=f"/scenario/{doc['id']}/scenes/{sc['id']}")
    raise ApiError(404, "NOT_FOUND", "이 이미지 요청을 낸 장면을 찾을 수 없어요")


@router.get("/scenes/{scene_id}/image-prefill", response_model=m.ImagePrefill, tags=TAG)
async def image_prefill(scene_id: str) -> m.ImagePrefill:
    doc, sc = await find_scene(scene_id)
    return m.ImagePrefill(**imaging.prefill(doc, sc))
