"""그래프 `image.variants` — 07-image §7.5.

load_base → plan_axes(llm.json: 4개 {label≤8자, instruction}, 축 = 시간대 · 조명 · 시점 · 근접 중 겹치지 않게;
'조명만 바꾸기'면 조명 축만, '손님 넣기'면 가상 인물 추가) → render(edit | ref | text) ×4 → qc(제품 박스 IoU vs 기준 ≥ 0.5 →
'제품 배치 유지') → postprocess(새 시안 「A · 오후 자연광」, base_image_id)
"""
from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from winmate_common.jobs import JobCanceled, current_job

from .. import caps, config, llm, prompts, shots
from ..store import repo
from . import common

log = logging.getLogger("winmate.image.variants")
LAYOUT_NOTE = "배치가 조금 달라질 수 있어요"


class VarState(TypedDict, total=False):
    run_id: str
    base: dict[str, Any]
    items: list[dict[str, Any]]
    shot_ids: list[str]


async def load_base(state: VarState) -> dict[str, Any]:
    run = await repo().get("runs", state["run_id"]) or {}
    params = run.get("params") or {}
    img = await repo().get("images", run.get("base_image_id")) or {}
    ver = await repo().get("versions", params.get("base_version_id") or img.get("current_version_id")) or {}
    shots_ = sorted([s for s in await repo().all("images", where={"run_id": state["run_id"]}) if s.get("status") == "waiting"],
                    key=lambda s: int(s.get("index") or 0))
    await shots.set_phase(state["run_id"], "compose")
    gen = ver.get("generation") or {}
    base = {"image_id": img.get("id"), "label": img.get("label"), "version_id": ver.get("id"), "file_id": ver.get("master_file_id"),
            "aspect": img.get("aspect") or "16:9", "prompt_en": gen.get("prompt_en") or "", "prompt_ko": gen.get("prompt_ko") or "",
            "boxes": [p["box"] for p in ((ver.get("qc") or {}).get("products") or []) if p.get("box")],
            "confidential": bool(ver.get("confidential")), "references": gen.get("references") or [], "products": gen.get("products") or [],
            "policy": gen.get("policy") or {}, "axis": params.get("axis") or "any", "instruction": params.get("instruction"),
            "mode": params.get("mode") or "edit", "work_id": img.get("work_id")}
    return {"base": base, "shot_ids": [s["id"] for s in shots_]}


class _Plan(BaseModel):
    variants: list[llm.VariantItem]


async def plan_axes(state: VarState) -> dict[str, Any]:
    base = state["base"]
    n = len(state.get("shot_ids") or [])
    axis = base["axis"]
    axis_ko = {"any": "시간대 · 조명 · 시점 · 근접 중 겹치지 않게", "lighting": "조명 축만", "people": "가상 인물(실존 인물 아님) 추가"}[axis]
    extra = f"\n추가 요청: {base['instruction']}" if base.get("instruction") else ""
    out = await llm.json_task("img.variant_plan", f"기준 시안: {base['prompt_ko']}\n변형 {n}개를 {axis_ko} 정하라. 제품 배치는 유지한다. "
                              f"label 은 8자 이내 한국어.{extra}", llm.VariantPlanOut, system=llm.SYSTEM_KO, timeout=20)
    items = [dict(v) for v in (out or {}).get("variants") or []]
    default = prompts.VARIANT_DEFAULT[axis]
    while len(items) < n:
        items.append(dict(default[len(items) % len(default)]))
    items = items[:n]
    for it in items:
        it["label"] = (it.get("label") or "변형").strip()[:8]
        if base.get("instruction"):
            it["instruction_en"] = f"{it.get('instruction_en') or ''}. Also: {base['instruction']}"
    return {"items": items}


async def _one(state: VarState, iid: str, item: dict[str, Any]) -> None:
    base = state["base"]
    job = current_job()
    run = await repo().get("runs", state["run_id"]) or {}
    img = await repo().get("images", iid)
    if img is None:
        return
    letter = img.get("letter") or "A"
    label = f"{letter} · {item['label']}"
    await repo().patch("images", iid, {"label": label, "variant_name": item["label"]})
    f = await caps.flags()
    mode = "edit" if f.edit else ("ref" if f.ref_images else "text")
    ema = shots.ema_key(f.t2i_provider, f.t2i_model, "variant")
    await shots.set_shot(job, iid, "composing", stage="compose", expected_s=await shots.expected_s(ema))
    t0 = time.monotonic()
    await shots.dev_delay()
    await shots.check(job, iid, state["run_id"])
    await shots.set_shot(job, iid, "rendering", stage="render")
    keep = mode != "text"
    instr = prompts.variant_instruction(item, keep_layout=keep)
    fallbacks: list[str] = []
    try:
        if mode == "edit":
            res = await shots.t2i_edit("img.variant", {"file_id": base["file_id"]}, instr, confidential=base["confidential"],
                                       metadata={"image_id": iid, "base": base["image_id"]})
        elif mode == "ref":
            res = await shots.t2i_generate("img.variant", f"{base['prompt_en']}\n{instr}", aspect=base["aspect"],
                                           refs=[{"file_id": base["file_id"], "role": "base", "strength": "high"}], negative=None,
                                           confidential=base["confidential"], metadata={"image_id": iid})
            fallbacks.append("variant:ref")
        else:
            res = await shots.t2i_generate("img.variant", f"{base['prompt_en']}\n{instr}", aspect=base["aspect"], refs=None,
                                           negative=None, confidential=base["confidential"], metadata={"image_id": iid})
            fallbacks.append("variant:text")
    except llm.ModelBlocked as exc:
        raise shots.ShotFailed("policy_confidential", "기밀 자료라 이미지 모델로 보낼 수 없어요") from exc
    except (llm.QuotaExceeded, JobCanceled, shots.ShotCanceled):
        raise
    except Exception as exc:  # noqa: BLE001
        raise shots.model_error(exc) from exc
    fallbacks += shots.map_fallbacks(res.get("fallbacks") or [])
    await shots.set_shot(job, iid, "qc", stage="qc")
    qc = await shots.quality_check(res["file_id"], width=res["width"], height=res["height"], products=[], allow_faces=base["axis"] == "people",
                                   confidential=base["confidential"], want_bbox=f.bbox, expect_boxes=base["boxes"] or None)
    layout_note = None
    if mode == "text":
        layout_note = LAYOUT_NOTE
    elif base["boxes"]:
        from ..imaging import boxes_iou

        iou = boxes_iou(base["boxes"], [p["box"] for p in qc.get("products") or []]) if qc.get("products") else None
        if iou is not None and iou < config.variant_layout_iou_min():
            layout_note = LAYOUT_NOTE
    native = await shots.load_native(res["file_id"])
    gen = shots.generation_meta(provider=res.get("provider"), model=res.get("model"), call=res["call"],
                                prompt_ko=f"{base['prompt_ko']} · {item['label']}", prompt_en=instr, references=base["references"],
                                products=base["products"], policy_meta=base["policy"], fallbacks=fallbacks, upscale=None,
                                confidential=base["confidential"], origin={"service": "image", "work_id": base["work_id"]},
                                extra={"variant_of": base["version_id"], "variant": item})
    await shots.finish_shot(job, run, img, native_file_id=res["file_id"], native_im=native, op="variant", generation=gen, qc=qc,
                            confidential=base["confidential"], started=t0, ema=ema, op_params={"axis": base["axis"], "label": item["label"]},
                            label=label, extra_img={"layout_note": layout_note})


async def render(state: VarState) -> dict[str, Any]:
    await shots.set_phase(state["run_id"], "render")
    ids = state.get("shot_ids") or []
    items = state.get("items") or []
    res = await common.gather_limited(config.shot_concurrency(), [_one(state, iid, it) for iid, it in zip(ids, items)])
    quota = None
    for iid, r in zip(ids, res):
        if isinstance(r, JobCanceled):
            raise r
        if isinstance(r, llm.QuotaExceeded):
            quota = r.message
        if isinstance(r, (shots.ShotFailed, llm.QuotaExceeded)) or (isinstance(r, Exception) and not isinstance(r, shots.ShotCanceled)):
            msg = getattr(r, "message", None) or "이미지 모델이 응답하지 않아요"
            await shots.set_shot(current_job(), iid, "failed", label="실패", error=msg)
    if quota:
        raise llm.QuotaExceeded(quota)
    return {}


async def finalize(state: VarState) -> dict[str, Any]:
    from .. import notify

    await notify.finish_run(state["run_id"])
    return {}


def build() -> StateGraph:
    g = StateGraph(VarState)
    g.add_node("load_base", load_base)
    g.add_node("plan_axes", plan_axes)
    g.add_node("render", render)
    g.add_node("finalize", finalize)
    g.add_edge(START, "load_base")
    g.add_edge("load_base", "plan_axes")
    g.add_edge("plan_axes", "render")
    g.add_edge("render", "finalize")
    g.add_edge("finalize", END)
    return g
