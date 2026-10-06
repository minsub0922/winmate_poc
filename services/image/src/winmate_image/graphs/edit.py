"""그래프 `image.edit`(부분 · 전체 수정) — 07-image §7.4.

load → apply(영역마다 번호 순: build_mask → protect_products → t2i.edit(전체 + 마스크; ai-tools 가 네이티브 마스크 / 잘라 붙이기)
      → paste_feather(안쪽 FEATHER_PX) → seam_harmonize(링 16px) → verify_outside(마스크 ⊕ 8px 바깥 바이트 일치) → save_version)
→ finalize

편집 미지원 · 기밀 차단: 작은 영역(면적 ≤ 2%)은 로컬 인페인트(`edit:local_inpaint`), 그 밖은 영역 실패.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.jobs import JobCanceled, current_job

from .. import caps, config, imaging, llm, prompts, shots
from ..filestore import load_image
from ..images import create_version, region_mask
from ..store import repo

log = logging.getLogger("winmate.image.edit")

SCREEN_WORDS = ("화면", "메뉴", "콘텐츠", "screen", "content", "영상", "디스플레이 화면")


class EditState(TypedDict, total=False):
    run_id: str
    image_id: str
    params: dict[str, Any]
    results: list[dict[str, Any]]


class EditFailed(Exception):
    pass


async def load(state: EditState) -> dict[str, Any]:
    run = await repo().get("runs", state["run_id"]) or {}
    await shots.set_phase(state["run_id"], "render")
    return {"image_id": (run.get("params") or {}).get("image_id") or run.get("base_image_id"), "params": run.get("params") or {}}


async def _emit(region: dict[str, Any], label: str) -> None:
    job = current_job()
    if job is not None:
        await job.jobs.emit(job.job.id, "step", {"stage": "render", "label": label,
                                                 "region": {"id": region["id"], "n": region.get("n"), "status": region.get("status")}})


def _screen_target(instruction: str) -> bool:
    return any(w in (instruction or "") for w in SCREEN_WORDS)


async def edit_region(img: dict[str, Any], region: dict[str, Any], flags: caps.Flags) -> dict[str, Any]:
    ver = await repo().get("versions", img.get("current_version_id"))
    if ver is None:
        raise EditFailed("기준 버전이 없어요")
    base = await load_image(ver["master_file_id"])
    mask = await region_mask(region, base.size)
    fallbacks = list((ver.get("generation") or {}).get("fallbacks") or [])
    fallbacks = [f for f in fallbacks if not f.startswith(("mask:", "edit:", "lock:"))]
    products = [p for p in ((ver.get("qc") or {}).get("products") or []) if p.get("box")]
    instruction = region.get("instruction") or ""
    if region.get("protect_products", True):
        if products:
            mask = await asyncio.to_thread(imaging.protect_products, mask, products, screen_target=_screen_target(instruction))
        else:
            fallbacks.append("lock:instruction_only")
    if mask.getbbox() is None:
        raise EditFailed("제품 외형 고정 때문에 바꿀 영역이 없어요")
    text = prompts.edit_instruction(instruction, region.get("label"))
    if region.get("protect_products", True):
        text += " Do not change the products' shape, bezel or proportions."
    edited = None
    call, model, provider = "local", None, None
    confidential = bool(ver.get("confidential"))
    if flags.edit:
        data, mime = await asyncio.to_thread(imaging.encode, mask.convert("L"), "PNG")
        try:
            res = await shots.t2i_edit("img.edit", {"file_id": ver["master_file_id"]}, text,
                                       mask={"data_b64": base64.b64encode(data).decode(), "mime": mime}, confidential=confidential,
                                       metadata={"image_id": img["id"], "region_id": region["id"]})
            edited = await load_image(res["file_id"])
            fallbacks += shots.map_fallbacks(res.get("fallbacks") or [])
            call, model, provider = "t2i.edit", res.get("model"), res.get("provider")
        except llm.ModelBlocked:
            edited = None
        except (llm.QuotaExceeded, JobCanceled):
            raise
        except Exception as exc:  # noqa: BLE001
            raise EditFailed(shots.model_error(exc).message) from exc
    if edited is None:
        if imaging.mask_area_ratio(mask) <= 0.02:
            edited = await asyncio.to_thread(imaging.diffusion_inpaint, base, mask)
            fallbacks.append("edit:local_inpaint")
        else:
            raise EditFailed("지금 모델로는 이 영역을 고칠 수 없어요")
    pasted = await asyncio.to_thread(imaging.composite_inward, base, edited, mask, config.feather_px())
    final = await asyncio.to_thread(imaging.seam_harmonize, base, pasted, mask, config.ring_px())
    ok = await asyncio.to_thread(imaging.verify_outside, base, final, mask, config.feather_px())
    if not ok:
        raise RuntimeError("영역 밖 픽셀이 바뀌었습니다(버그) — 결과를 저장하지 않았습니다")
    gen = dict(ver.get("generation") or {})
    gen.update({"call": call, "fallbacks": list(dict.fromkeys(fallbacks)), "edit": {"instruction": instruction, "prompt_en": text,
                                                                                     "region_label": region.get("label")}})
    if model:
        gen["model"], gen["provider"] = model, provider
    return await create_version(img, op="edit_region", master=final, generation=gen, parent_version_id=ver["id"],
                                op_params={"region_id": region["id"], "region_n": region.get("n"), "rect": region.get("rect"),
                                           "instruction": instruction}, qc=ver.get("qc"), confidential=confidential)


async def edit_global(img: dict[str, Any], params: dict[str, Any], flags: caps.Flags) -> dict[str, Any]:
    ver = await repo().get("versions", img.get("current_version_id"))
    if ver is None:
        raise EditFailed("기준 버전이 없어요")
    if not flags.edit:
        raise EditFailed("지금 모델로는 전체 수정을 할 수 없어요")
    instruction = params.get("instruction") or ""
    protect = bool(params.get("protect_products", True))
    text = prompts.edit_instruction(instruction, None) + (" Do not change the products' shape, bezel or proportions." if protect else "")
    confidential = bool(ver.get("confidential"))
    base_boxes = [p["box"] for p in ((ver.get("qc") or {}).get("products") or []) if p.get("box")]
    fallbacks = [f for f in ((ver.get("generation") or {}).get("fallbacks") or []) if not f.startswith(("mask:", "edit:", "lock:"))]
    tries = 0
    qc: dict[str, Any] = dict(ver.get("qc") or {})
    while True:
        try:
            res = await shots.t2i_edit("img.edit", {"file_id": ver["master_file_id"]}, text, confidential=confidential,
                                       metadata={"image_id": img["id"], "mode": "global"})
        except llm.ModelBlocked as exc:
            raise EditFailed("기밀 자료라 이미지 모델로 보낼 수 없어요") from exc
        except (llm.QuotaExceeded, JobCanceled):
            raise
        except Exception as exc:  # noqa: BLE001
            raise EditFailed(shots.model_error(exc).message) from exc
        edited = await load_image(res["file_id"])
        if protect and base_boxes:
            f = await caps.flags()
            q = await shots.quality_check(res["file_id"], width=edited.width, height=edited.height, products=[], allow_faces=True,
                                          confidential=confidential, want_bbox=f.bbox)
            iou = imaging.boxes_iou(base_boxes, [p["box"] for p in q.get("products") or []]) if q.get("products") else 0.0
            if iou < config.global_edit_product_iou_min() and tries < 1:
                tries += 1
                continue
            qc = {**q, "status": "ok" if iou >= config.global_edit_product_iou_min() else "check",
                  "reason": None if iou >= config.global_edit_product_iou_min() else "제품 외형이 바뀌었을 수 있어요"}
        elif protect:
            fallbacks.append("lock:instruction_only")
        break
    master = edited.resize((ver["width"], ver["height"])) if edited.size != (ver["width"], ver["height"]) else edited
    gen = dict(ver.get("generation") or {})
    gen.update({"call": "t2i.edit", "model": res.get("model"), "provider": res.get("provider"),
                "fallbacks": list(dict.fromkeys(fallbacks + shots.map_fallbacks(res.get("fallbacks") or []))),
                "edit": {"instruction": instruction, "prompt_en": text}})
    v = await create_version(img, op="edit_global", master=master, generation=gen, parent_version_id=ver["id"],
                             op_params={"instruction": instruction}, qc={k: x for k, x in qc.items() if k != "fails"},
                             confidential=confidential)
    if qc.get("status") == "check":
        await repo().patch("images", img["id"], {"qc_flag": True, "qc_reason": qc.get("reason")})
    return v


async def apply(state: EditState) -> dict[str, Any]:
    params = state.get("params") or {}
    flags = await caps.flags()
    job = current_job()
    results: list[dict[str, Any]] = []
    if params.get("mode") == "global":
        img = await repo().get("images", state["image_id"])
        t0 = time.monotonic()
        try:
            v = await edit_global(img, params, flags)
            await repo().patch("runs", state["run_id"], {"edit_ok": True, "done": 1})
            results.append({"version_id": v["id"]})
        except EditFailed as exc:
            await repo().patch("runs", state["run_id"], {"edit_ok": False, "error": {"code": "EDIT_FAILED", "message": str(exc)}})
        _ = t0
        return {"results": results}
    region_ids = list(params.get("region_ids") or [])
    regions = [r for r in [await repo().get("regions", rid) for rid in region_ids] if r]
    regions.sort(key=lambda r: int(r.get("n") or 0))
    for k, region in enumerate(regions, 1):
        if job is not None:
            await job.check_cancel()
        run = await repo().get("runs", state["run_id"]) or {}
        if run.get("status") == "canceled":
            raise JobCanceled()
        img = await repo().get("images", state["image_id"])
        region = await repo().patch("regions", region["id"], {"status": "applying", "base_version_id": img.get("current_version_id")}) or region
        await _emit(region, f"영역 {region.get('n')} 적용 중")
        await shots.dev_delay()
        try:
            v = await edit_region(img, region, flags)
            region = await repo().patch("regions", region["id"], {"status": "applied", "result_version_id": v["id"], "error": None}) or region
            results.append({"region_id": region["id"], "version_id": v["id"]})
        except EditFailed as exc:
            region = await repo().patch("regions", region["id"], {"status": "failed", "error": str(exc)}) or region
        except llm.QuotaExceeded:
            await repo().patch("regions", region["id"], {"status": "failed", "error": "오늘 쓸 수 있는 이미지 생성 횟수를 다 썼어요"})
            raise
        await _emit(region, f"영역 {region.get('n')} {'적용됨' if region.get('status') == 'applied' else '실패'}")
        if job is not None:
            await job.progress(int(100 * k / max(1, len(regions))), f"영역 {k} / {len(regions)}")
        await repo().patch("runs", state["run_id"], {"done": sum(1 for r in results)})
    return {"results": results}


async def finalize(state: EditState) -> dict[str, Any]:
    from .. import notify

    await notify.finish_run(state["run_id"])
    return {}


def build() -> StateGraph:
    g = StateGraph(EditState)
    g.add_node("load", load)
    g.add_node("apply", apply)
    g.add_node("finalize", finalize)
    g.add_edge(START, "load")
    g.add_edge("load", "apply")
    g.add_edge("apply", "finalize")
    g.add_edge("finalize", END)
    return g
