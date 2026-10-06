"""그래프 `image.renditions` — 07-image §7.5 · §7.2 비율 행.

비율마다 새 시안(`{원 라벨} · {비율}`, base_image_id):
- 기준과 같은 비율 → 업스케일만(T2I 0회)
- 잘라내기 → 로컬(제품 박스를 최대한 담는 창)
- 바깥 채우기 → 캔버스 확장(목표 비율 native 크기, 빈 곳 = 가장자리 거울 + 블러) → t2i.edit("빈 곳만 자연스럽게 확장") → 원래 영역은 원본 픽셀로
- 다시 구성 → t2i.generate(ref=기준, 목표 비율) + 제품 외형 고정 / 참조 미지원 + 편집 지원이면 바깥 채우기(`recompose:outpaint`)
그다음 목표 렌디션(×2 uhd · ×4 uhd8k)까지 업스케일.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import time
from typing import Any, TypedDict

import numpy as np
from langgraph.graph import END, START, StateGraph

from winmate_common.jobs import JobCanceled, current_job

from .. import caps, config, imaging, llm, shots
from ..filestore import load_image
from ..images import ensure_rendition
from ..store import repo
from . import common

log = logging.getLogger("winmate.image.renditions")
OUTPAINT_TEXT = ("Extend only the blurred empty border areas naturally so the scene continues seamlessly (same perspective, lighting "
                 "and style). Keep the sharp central image exactly as it is.")


class RenState(TypedDict, total=False):
    run_id: str
    params: dict[str, Any]
    base: dict[str, Any]
    shot_ids: list[str]


async def load_base(state: RenState) -> dict[str, Any]:
    run = await repo().get("runs", state["run_id"]) or {}
    params = run.get("params") or {}
    img = await repo().get("images", run.get("base_image_id")) or {}
    ver = await repo().get("versions", params.get("base_version_id") or img.get("current_version_id")) or {}
    gen = ver.get("generation") or {}
    shots_ = sorted([s for s in await repo().all("images", where={"run_id": state["run_id"]}) if s.get("status") == "waiting"],
                    key=lambda s: int(s.get("index") or 0))
    await shots.set_phase(state["run_id"], "render")
    base = {"image_id": img.get("id"), "version_id": ver.get("id"), "file_id": ver.get("master_file_id"),
            "aspect": img.get("aspect") or "16:9", "prompt_en": gen.get("prompt_en") or "", "prompt_ko": gen.get("prompt_ko") or "",
            "boxes": [p["box"] for p in ((ver.get("qc") or {}).get("products") or []) if p.get("box")],
            "confidential": bool(ver.get("confidential")), "gen": gen, "qc": ver.get("qc") or {}, "work_id": img.get("work_id")}
    return {"params": params, "base": base, "shot_ids": [s["id"] for s in shots_]}


def _mad(a: Any, b: Any) -> float:
    return float(np.abs(np.asarray(a).astype(np.float32) - np.asarray(b).astype(np.float32)).mean())


async def _one(state: RenState, iid: str) -> None:
    params = state["params"]
    base = state["base"]
    job = current_job()
    run = await repo().get("runs", state["run_id"]) or {}
    img = await repo().get("images", iid)
    if img is None:
        return
    target = img.get("aspect") or "16:9"
    fit = params.get("fit") or "recompose"
    f = await caps.flags()
    ema = shots.ema_key(f.t2i_provider, f.t2i_model, "rendition")
    await shots.set_shot(job, iid, "composing", stage="compose", expected_s=await shots.expected_s(ema))
    t0 = time.monotonic()
    base_im = await load_image(base["file_id"])
    fallbacks: list[str] = []
    call, model, provider, native_fid = "local", base["gen"].get("model"), base["gen"].get("provider"), None
    instr = (params.get("instructions") or {}).get(target) or ""
    await shots.check(job, iid, state["run_id"])
    await shots.set_shot(job, iid, "rendering", stage="render")
    qc = dict(base["qc"])
    if target == base["aspect"]:
        result = base_im
    elif fit == "crop":
        box = imaging.crop_window(base_im.width, base_im.height, config.ratio_of(target), base["boxes"])
        result = base_im.crop(box)
        fallbacks.append("aspect:crop")
        qc = {"status": "ok", "checks": [{"key": "crop_contains_products", "ok": True}], "products": []}
    else:
        use_outpaint = fit == "outpaint" or (fit == "recompose" and not f.ref_images and f.edit)
        try:
            if use_outpaint:
                size = config.size_for(target, "native")
                canvas, box = await asyncio.to_thread(imaging.extend_canvas, base_im, config.ratio_of(target), size)
                data, mime = await asyncio.to_thread(imaging.encode, canvas, "PNG")
                text = OUTPAINT_TEXT + (f" {instr}" if instr else "")
                res = await shots.t2i_edit("img.outpaint", {"data_b64": base64.b64encode(data).decode(), "mime": mime}, text,
                                           confidential=base["confidential"], metadata={"image_id": iid, "canvas": list(size)})
                edited = await load_image(res["file_id"])
                if edited.size != canvas.size:
                    edited = edited.resize(canvas.size)
                small = base_im.resize((box[2] - box[0], box[3] - box[1]))
                edited.paste(small, box[:2])
                mad = _mad(edited.crop(box), small)
                qc = {"status": "ok" if mad < 1.0 else "check", "checks": [{"key": "original_area_mad", "ok": mad < 1.0, "value": round(mad, 3)}],
                      "products": []}
                result = edited
                if fit == "recompose":
                    fallbacks.append("recompose:outpaint")
                call = "t2i.edit"
            else:
                prompt = (f"{base['prompt_en']}\nRecompose the same scene for a {target} frame. Keep the products' exact shape, "
                          f"proportions and placement relationships.{(' ' + instr) if instr else ''}")
                res = await shots.t2i_generate("img.recompose", prompt, aspect=target,
                                               refs=[{"file_id": base["file_id"], "role": "composition", "strength": "high"}],
                                               negative=None, confidential=base["confidential"], metadata={"image_id": iid})
                result = await load_image(res["file_id"])
                call = "t2i.generate"
            model, provider, native_fid = res.get("model"), res.get("provider"), res["file_id"]
            fallbacks += shots.map_fallbacks(res.get("fallbacks") or [])
        except llm.ModelBlocked as exc:
            raise shots.ShotFailed("policy_confidential", "기밀 자료라 이미지 모델로 보낼 수 없어요") from exc
        except (llm.QuotaExceeded, JobCanceled, shots.ShotCanceled):
            raise
        except Exception as exc:  # noqa: BLE001
            raise shots.model_error(exc) from exc
    await shots.set_shot(job, iid, "qc", stage="qc")
    gen = dict(base["gen"])
    gen.update({"call": call, "model": model, "provider": provider, "fallbacks": list(dict.fromkeys(list(gen.get("fallbacks") or []) + fallbacks)),
                "aspect_from": base["aspect"], "fit": fit, "aspect_instruction": instr or None, "base_version_id": base["version_id"]})
    ver = await shots.finish_shot(job, run, img, native_file_id=native_fid, native_im=result, op="aspect", generation=gen, qc=qc,
                                  confidential=base["confidential"], started=t0, ema=ema,
                                  op_params={"fit": fit, "from": base["aspect"], "to": target})
    kind = config.UPSCALE_KIND.get(params.get("upscale") or "1x", "fhd")
    if kind != "fhd":
        await ensure_rendition(ver, kind, target)


async def render(state: RenState) -> dict[str, Any]:
    ids = state.get("shot_ids") or []
    res = await common.gather_limited(config.shot_concurrency(), [_one(state, iid) for iid in ids])
    quota = None
    for iid, r in zip(ids, res):
        if isinstance(r, JobCanceled):
            raise r
        if isinstance(r, llm.QuotaExceeded):
            quota = r.message
        if isinstance(r, Exception) and not isinstance(r, shots.ShotCanceled):
            if not isinstance(r, (shots.ShotFailed, llm.QuotaExceeded)):
                log.exception("비율 시안 실패", exc_info=r)
            await shots.set_shot(current_job(), iid, "failed", label="실패", error=getattr(r, "message", None) or "이미지 모델이 응답하지 않아요")
    if quota:
        raise llm.QuotaExceeded(quota)
    return {}


async def finalize(state: RenState) -> dict[str, Any]:
    from .. import notify

    await notify.finish_run(state["run_id"])
    return {}


def build() -> StateGraph:
    g = StateGraph(RenState)
    g.add_node("load_base", load_base)
    g.add_node("render", render)
    g.add_node("finalize", finalize)
    g.add_edge(START, "load_base")
    g.add_edge("load_base", "render")
    g.add_edge("render", "finalize")
    g.add_edge("finalize", END)
    return g
