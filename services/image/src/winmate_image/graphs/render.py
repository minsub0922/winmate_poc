"""렌더 API 그래프 `image.render` — 07-image §7.9 (birdseye · scenario 전용).

load → policy_check(텍스트만) → product_fit → render(structure_ref 가 있으면 참조 1순위로 '이 구도 · 배치를 정확히 따름';
참조 미지원이면 edit_of=structure_ref 로 t2i.edit; edit_of 가 있으면 그 이미지 편집; 둘 다 없으면 텍스트) →
quality_check(expect · forbid) → postprocess(target 렌디션까지) → END
"""
from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.jobs import JobCanceled, current_job

from .. import caps, config, kbapi, llm, policy, prompts, shots
from ..images import ensure_rendition
from ..store import repo
from . import common

log = logging.getLogger("winmate.image.render")


class RenderState(TypedDict, total=False):
    run_id: str
    render_id: str
    ctx: dict[str, Any]
    plan: dict[str, Any]


async def load(state: RenderState) -> dict[str, Any]:
    run = await repo().get("runs", state["run_id"]) or {}
    rid = (run.get("params") or {}).get("render_id")
    r = await repo().get("renders", rid) or {}
    await repo().patch("renders", rid, {"status": "running"})
    prods = []
    for p in r.get("product_refs") or []:
        hit = None
        if p.get("model_code"):
            hit = await kbapi.resolve_product(p["model_code"])
        if hit:
            prods.append(kbapi.product_from_search(hit, p.get("qty") or 1))
        elif p.get("family_id"):
            shot = await kbapi.product_front_shot(p["family_id"])
            prods.append({"family_id": p["family_id"], "model_code": None, "name": (shot or {}).get("alt") or p["family_id"],
                          "short": (shot or {}).get("alt") or p["family_id"], "qty": int(p.get("qty") or 1)})
    f = await caps.flags()
    dims = await common.product_facts(prods)
    ctx = {"render": r, "products": prods, "dims": dims, "flags": common.flags_dict(f), "aspect": r.get("aspect") or "16:9",
           "confidential": bool(r.get("confidential")), "origin": {"service": (r.get("origin") or {}).get("service") or "image",
                                                                    "ref": (r.get("origin") or {}).get("ref"), "work_id": run["work_id"],
                                                                    "render_id": rid}}
    await shots.set_phase(state["run_id"], "product_fit")
    return {"render_id": rid, "ctx": ctx}


async def policy_check(state: RenderState) -> dict[str, Any]:
    r = state["ctx"]["render"]
    p = r.get("prompt") or {}
    text = " ".join([p.get("subject_ko") or "", *(p.get("details_ko") or [])])
    cls, mode = await policy.classify_with_timeout(text, confidential=bool(r.get("confidential")))
    issues = policy.build_issues(cls)
    for it in issues:   # 렌더 API 는 사람에게 묻지 않는다 — 기본 대안으로
        it["selected"] = policy.effective_option(it)
    await repo().patch("runs", state["run_id"], {"precheck": {"issues": issues, "mode": mode, "applied_note": policy.applied_note(issues)}})
    return {}


async def product_fit(state: RenderState) -> dict[str, Any]:
    ctx = state["ctx"]
    r = ctx["render"]
    shots_map = await common.product_shots(ctx["products"])
    structure = {"file_id": r["structure_ref_file_id"]} if r.get("structure_ref_file_id") else None
    plan = common.allocate_references(products=ctx["products"], shots=shots_map, refs=[], flags=ctx["flags"], structure=structure)
    for i, fid in enumerate(r.get("reference_file_ids") or []):
        if ctx["flags"].get("ref_images") and len(plan["send"]) < int(ctx["flags"].get("max_refs") or 3):
            plan["send"].append({"kind": "user", "file_id": fid, "role": "style", "strength": "mid", "ref_id": f"rf_{i}"})
    plan["shots"] = shots_map
    plan["products_meta"] = common.products_meta(ctx["products"], shots_map, None)
    await shots.set_phase(state["run_id"], "compose")
    return {"plan": plan}


def _people(allow: str) -> str:
    return {"none": "none", "silhouette": "silhouette", "generic": "generic"}.get(allow, "none")


async def render(state: RenderState) -> dict[str, Any]:
    ctx = state["ctx"]
    r = ctx["render"]
    plan = state["plan"]
    job = current_job()
    await shots.set_phase(state["run_id"], "render")
    run = await repo().get("runs", state["run_id"]) or {}
    imgs = [s for s in await repo().all("images", where={"run_id": state["run_id"]})]
    if not imgs:
        raise shots.ShotFailed("no_shot", "렌더 시안이 없어요")
    img = imgs[0]
    issues = (run.get("precheck") or {}).get("issues") or []
    eff = policy.effects(issues, kind="scenario" if r.get("kind") == "scene" else "space", rules_only=False)
    eff["people"] = _people(r.get("allow_people") or "none")
    forbid = set(r.get("forbid") or [])
    if "competitor_logo" in forbid:
        eff["negatives"] = list(dict.fromkeys(eff["negatives"] + ["other companies' logos"]))
    if "gibberish_text" in forbid:
        eff["negatives"] = list(dict.fromkeys(eff["negatives"] + ["gibberish or unreadable text"]))
    p = r.get("prompt") or {}
    desc = " ".join([p.get("subject_ko") or "", *(p.get("details_ko") or [])]).strip()
    built = prompts.build(kind="scenario" if r.get("kind") == "scene" else "space", description=desc, style=r.get("style") or "photo",
                          aspect=ctx["aspect"], products=ctx["products"], dims=ctx["dims"], shot_en=None, effects=eff,
                          ref_lines=common.ref_lines(plan, []), extra=[f"Avoid: {', '.join(p.get('negatives') or [])}"] if p.get("negatives") else None)
    flags = ctx["flags"]
    ema = shots.ema_key(flags.get("provider"), flags.get("model"), "render")
    await shots.set_shot(job, img["id"], "composing", stage="compose", expected_s=await shots.expected_s(ema))
    t0 = time.monotonic()
    await shots.set_shot(job, img["id"], "rendering", stage="render")
    fallbacks: list[str] = []
    structure = r.get("structure_ref_file_id")
    edit_of = r.get("edit_of")
    try:
        if edit_of:
            res = await shots.t2i_edit("img.render", {"file_id": edit_of["file_id"]}, prompts.edit_instruction(edit_of["instruction"], None),
                                       aspect=ctx["aspect"], confidential=ctx["confidential"], metadata={"render_id": state["render_id"]})
            fallbacks.append("render:edit")
        elif structure and flags.get("ref_images"):
            res = await shots.t2i_generate("img.render", built["prompt_en"], aspect=ctx["aspect"], refs=common.t2i_refs(plan),
                                           negative=built["negative"], confidential=ctx["confidential"],
                                           metadata={"render_id": state["render_id"]})
            fallbacks.append("render:ref")
        elif structure and flags.get("edit"):
            res = await shots.t2i_edit("img.render", {"file_id": structure},
                                       built["prompt_en"] + "\nRender this draft as a finished, photoreal image. Keep the layout, camera and "
                                       "product positions exactly.", aspect=ctx["aspect"], confidential=ctx["confidential"],
                                       metadata={"render_id": state["render_id"]})
            fallbacks.append("render:edit")
        else:
            res = await shots.t2i_generate("img.render", built["prompt_en"], aspect=ctx["aspect"], refs=common.t2i_refs(plan),
                                           negative=built["negative"], confidential=ctx["confidential"],
                                           metadata={"render_id": state["render_id"]})
            fallbacks.append("render:text" if not plan.get("send") else "render:ref")
    except llm.ModelBlocked as exc:
        raise shots.ShotFailed("policy_confidential", "기밀 자료라 이미지 모델로 보낼 수 없어요") from exc
    except (llm.QuotaExceeded, JobCanceled):
        raise
    except Exception as exc:  # noqa: BLE001
        raise shots.model_error(exc) from exc
    fallbacks += shots.map_fallbacks(res.get("fallbacks") or [])
    await shots.set_shot(job, img["id"], "qc", stage="qc")
    expect = (r.get("expect") or {}).get("products") or []
    exp_products = [{"short": e.get("model_code") or e.get("family_id"), "qty": e.get("qty") or 1} for e in expect]
    exp_boxes = [e["bbox_hint"] for e in expect if e.get("bbox_hint")]
    qc = await shots.quality_check(res["file_id"], width=res["width"], height=res["height"], products=exp_products,
                                   allow_faces=r.get("allow_people") == "generic" and "real_person_face" not in forbid,
                                   confidential=ctx["confidential"], want_bbox=bool(flags.get("bbox")), expect_boxes=exp_boxes or None)
    native = await shots.load_native(res["file_id"])
    gen = shots.generation_meta(provider=res.get("provider"), model=res.get("model"), call=res["call"], prompt_ko=desc,
                                prompt_en=built["prompt_en"], references=[], products=plan.get("products_meta") or [],
                                policy_meta={"issues": [i["type"] for i in issues], "applied_options": eff.get("applied") or {}},
                                fallbacks=fallbacks, upscale=None, confidential=ctx["confidential"], origin=ctx["origin"],
                                extra={"render": {"kind": r.get("kind"), "target": r.get("target"), "structure_ref_file_id": structure}})
    ver = await shots.finish_shot(job, run, img, native_file_id=res["file_id"], native_im=native, op="generate", generation=gen, qc=qc,
                                  confidential=ctx["confidential"], started=t0, ema=ema)
    if (r.get("target") or "fhd") == "uhd":
        await ensure_rendition(ver, "uhd", ctx["aspect"])
    await repo().patch("renders", state["render_id"], {"status": "succeeded", "version_id": ver["id"], "image_id": img["id"]})
    return {}


async def finalize(state: RenderState) -> dict[str, Any]:
    from .. import notify

    await notify.finish_run(state["run_id"])
    return {}


def build() -> StateGraph:
    g = StateGraph(RenderState)
    for name, fn in (("load", load), ("policy_check", policy_check), ("product_fit", product_fit), ("render", render),
                     ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "load")
    g.add_edge("load", "policy_check")
    g.add_edge("policy_check", "product_fit")
    g.add_edge("product_fit", "render")
    g.add_edge("render", "finalize")
    g.add_edge("finalize", END)
    return g


_ = config
