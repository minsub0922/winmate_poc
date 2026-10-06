"""그래프 `image.generate` (run kind: initial · composite · alternatives) — 07-image §7.3.

START → load_context → policy_check → split_shots → product_fit → compose → render(시안 fan-out ≤ IMAGE_SHOT_CONCURRENCY,
시안마다 장면 구성 → 렌더링 → 품질 확인(실패 & 재시도 < QC_MAX_RETRY → 그 시안만 다시) → 후처리)
→ 보류 있음? → await_alternatives [interrupt: awaiting_input] → apply_answers → product_fit(보류 시안) …
→ finalize → END
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from winmate_common.ids import now_iso
from winmate_common.jobs import JobCanceled, current_job

from .. import analysis, caps, config, imaging, llm, policy, prompts, shots
from ..filestore import save_image
from ..store import repo
from . import common

log = logging.getLogger("winmate.image.generate")


class GenState(TypedDict, total=False):
    run_id: str
    work_id: str
    kind: str
    active: list[str]
    held: list[str]
    ctx: dict[str, Any]
    plan: dict[str, Any]
    shot_prompts: dict[str, dict[str, Any]]
    answers: dict[str, Any] | None
    quota_error: str | None


LABELS = {"load_context": "맥락 불러오기", "policy_check": "정책 사전 검사", "split_shots": "보류 나누기",
          "product_fit": "제품 외형 맞춤", "compose": "장면 구성", "render": "렌더링", "await_alternatives": "대안 기다림",
          "apply_answers": "대안 반영", "finalize": "마무리"}


async def load_context(state: GenState) -> dict[str, Any]:
    run = await repo().get("runs", state["run_id"]) or {}
    work = await repo().get("works", run["work_id"]) or {}
    f = await caps.flags()
    refs = await common.work_refs(work["id"])
    cond = (run.get("params") or {}).get("conditions") or work.get("conditions") or {}
    products = [] if cond.get("no_products") else list(cond.get("products") or [])
    if work.get("kind") == "composite":
        products = [{"family_id": g.get("family_id"), "model_code": g.get("model_code"), "name": g.get("name") or g.get("label"),
                     "short": g.get("label") or g.get("name"), "qty": int(g.get("qty") or 1), "arrangement": g.get("arrangement")}
                    for g in (work.get("composite") or {}).get("groups") or []]
    dims = await common.product_facts(products)
    confidential = work.get("kind") == "composite" or any(r.get("confidential") for r in refs)
    ctx = {"kind": work.get("kind") or "space", "description": work.get("description") or "", "style": cond.get("style") or "photo",
           "aspect": (run.get("params") or {}).get("aspect") or cond.get("aspect") or "16:9", "products": products, "dims": dims,
           "flags": common.flags_dict(f), "confidential": confidential, "text_area": ((work.get("origin") or {}).get("text_area")
                                                                                      or "left"),
           "composite": work.get("composite"), "project_id": work.get("project_id"),
           "origin": {"service": "image", "work_id": work["id"]}}
    images = [s for s in await repo().all("images", where={"run_id": state["run_id"]}) if s.get("status") == "waiting"]
    images.sort(key=lambda s: int(s.get("index") or 0))
    await shots.set_phase(state["run_id"], "product_fit")
    return {"work_id": work["id"], "ctx": ctx, "active": [s["id"] for s in images], "held": []}


async def policy_check(state: GenState) -> dict[str, Any]:
    run = await repo().get("runs", state["run_id"]) or {}
    pre = dict(run.get("precheck") or {})
    issues = list(pre.get("issues") or [])
    # 참조 분석이 아직이면 지금(정책 (2)(3))
    refs = await common.work_refs(state["work_id"])
    for r in refs:
        if r.get("analysis") is None and r.get("file_id"):
            try:
                await analysis.analyze_reference(r["id"])
            except Exception as exc:  # noqa: BLE001
                log.info("참조 분석 실패 %s: %s", r["id"], exc)
    if not any(i["type"] == "product_unrecognized" for i in issues):
        from ..runs import reference_product_issues

        prod = await reference_product_issues(state["work_id"])
        if prod:
            issues = prod + issues
            for k, it in enumerate(issues, 1):
                it["id"] = f"iss_{k}"
    pre.update({"issues": issues, "applied_note": policy.applied_note(issues) if issues else None})
    await repo().patch("runs", state["run_id"], {"precheck": pre})
    return {}


async def split_shots(state: GenState) -> dict[str, Any]:
    run = await repo().get("runs", state["run_id"]) or {}
    issues = (run.get("precheck") or {}).get("issues") or []
    active = list(state.get("active") or [])
    n = len(active)
    h = policy.held_count(n, issues)
    held = active[n - h:] if h else []
    for iid in held:
        await shots.set_shot(current_job(), iid, "held", label="보류 · 대안 필요")
    await repo().patch("runs", state["run_id"], {"held": len(held)})
    return {"active": active[: n - h] if h else active, "held": held}


async def product_fit(state: GenState) -> dict[str, Any]:
    await shots.set_phase(state["run_id"], "product_fit")
    ctx = state["ctx"]
    run = await repo().get("runs", state["run_id"]) or {}
    issues = (run.get("precheck") or {}).get("issues") or []
    eff = policy.effects(issues, kind=ctx["kind"], rules_only=(run.get("precheck") or {}).get("mode") == "rules")
    products = list(ctx["products"])
    identity = eff.get("identity")
    if identity and identity.get("mode") == "model" and identity.get("model_code"):
        if not any(p.get("model_code") == identity["model_code"] for p in products):
            extra = await common.product_facts([identity])
            ctx = {**ctx, "dims": {**ctx["dims"], **extra}}
    shots_map = await common.product_shots(products + ([identity] if identity and identity.get("mode") == "model" else []))
    refs = await common.work_refs(state["work_id"])
    plan = common.allocate_references(products=products, shots=shots_map, refs=refs, flags=ctx["flags"])
    plan["shots"] = shots_map
    plan["effects"] = eff
    plan["refs_meta"] = common.references_meta(plan, refs)
    plan["lines"] = common.ref_lines(plan, refs)
    plan["products_meta"] = common.products_meta(products, shots_map, identity)
    plan["identity_line"] = common.identity_line(identity)
    plan["send_confidential"] = any(s.get("confidential") for s in plan.get("send") or [])
    await shots.dev_delay()
    return {"plan": plan, "ctx": ctx}


async def compose(state: GenState) -> dict[str, Any]:
    await shots.set_phase(state["run_id"], "compose")
    ctx = dict(state["ctx"])
    run = await repo().get("runs", state["run_id"]) or {}
    issues = (run.get("precheck") or {}).get("issues") or []
    if issues:
        ctx["description"] = policy.sanitize_text(ctx["description"], issues)
    active = state.get("active") or []
    n = len(active)
    composed = None
    if n and ctx["kind"] != "composite":
        out = await llm.json_task("img.compose", llm.compose_prompt(
            kind=config.KIND_LABEL.get(ctx["kind"], ctx["kind"]), description=ctx["description"], n=n,
            products=", ".join(f"{p.get('short') or p.get('name')} ×{p.get('qty') or 1}" for p in ctx["products"]),
            style=config.STYLE_LABEL.get(ctx["style"], ctx["style"]), extras=[]), llm.ComposeOut, system=llm.SYSTEM_KO, timeout=30)
        composed = (out or {}).get("shots")
        prompt_ko = (out or {}).get("prompt_ko") or ctx["description"]
    else:
        prompt_ko = ctx["description"] or "현장 사진 제품 합성"
    plan_shots = prompts.shot_plan(n, composed)
    eff = state["plan"]["effects"]
    sp: dict[str, dict[str, Any]] = {}
    for iid, sh in zip(active, plan_shots):
        built = prompts.build(kind=ctx["kind"], description=ctx["description"], style=ctx["style"], aspect=ctx["aspect"],
                              products=ctx["products"], dims=ctx["dims"], shot_en=sh["prompt_en"], effects=eff,
                              ref_lines=state["plan"]["lines"], text_area=ctx.get("text_area"),
                              identity_line=state["plan"].get("identity_line"))
        sp[iid] = {**built, "angle_ko": sh["angle_ko"], "prompt_ko": f"{prompt_ko} · {sh['angle_ko']}"}
    return {"shot_prompts": {**(state.get("shot_prompts") or {}), **sp}}


_STOP: dict[str, str] = {}


async def _render_one(state: GenState, iid: str, idx: int) -> None:
    ctx = state["ctx"]
    job = current_job()
    if _STOP.get(state["run_id"]):
        raise llm.QuotaExceeded(_STOP[state["run_id"]])
    run = await repo().get("runs", state["run_id"]) or {}
    img = await repo().get("images", iid)
    if img is None:
        return
    await shots.check(job, iid, state["run_id"])
    flags = ctx["flags"]
    op = "composite" if ctx["kind"] == "composite" else "generate"
    ema = shots.ema_key(flags.get("provider"), flags.get("model"), "edit" if op == "composite" else "generate")
    exp = await shots.expected_s(ema)
    await shots.set_shot(job, iid, "composing", stage="compose", expected_s=exp)
    t0 = time.monotonic()
    sp = (state.get("shot_prompts") or {}).get(iid) or {}
    plan = state["plan"]
    fallbacks = list(plan.get("fallbacks") or [])
    policy_meta = {"issues": [i["type"] for i in ((run.get("precheck") or {}).get("issues") or [])],
                   "applied_options": plan["effects"].get("applied") or {}}
    if (run.get("precheck") or {}).get("mode") == "rules":
        fallbacks.append("policy:rules_only")
    if ctx["kind"] == "composite":
        await _render_composite(state, img, idx, ema=ema, t0=t0, fallbacks=fallbacks, policy_meta=policy_meta)
        return
    await shots.dev_delay()
    await shots.check(job, iid, state["run_id"])
    await shots.set_shot(job, iid, "rendering", stage="render")
    refs = common.t2i_refs(plan)
    confidential = bool(plan.get("send_confidential"))
    prompt = sp.get("prompt_en") or ctx["description"]
    attempts = 0
    res = None
    qc: dict[str, Any] = {}
    while True:
        try:
            res = await shots.t2i_generate("img.generate", prompt, aspect=ctx["aspect"], refs=refs, negative=sp.get("negative"),
                                           confidential=confidential, metadata={"run_id": state["run_id"], "image_id": iid})
        except llm.ModelBlocked:
            if refs and confidential:
                # 기밀 참조(업로드)는 이미지로 보내지 않고 로컬 분석 글로만(다른 모델로 몰래 바꾸지 않는다)
                refs = [r for r, s in zip(refs, plan.get("send") or []) if not s.get("confidential")]
                confidential = False
                fallbacks += ["reference:text_fallback", "confidential:local_analysis"]
                continue
            raise shots.ShotFailed("policy_confidential", "기밀 자료라 이미지 모델로 보낼 수 없어요")
        except llm.QuotaExceeded as exc:
            _STOP[state["run_id"]] = exc.message
            raise
        except (JobCanceled, shots.ShotCanceled):
            raise
        except Exception as exc:  # noqa: BLE001
            raise shots.model_error(exc) from exc
        fallbacks += shots.map_fallbacks(res.get("fallbacks") or [])
        if not flags.get("ref_images") and (ctx["products"] or plan.get("text_refs")):
            fallbacks.append("reference:text_fallback")
        await shots.check(job, iid, state["run_id"])
        await shots.set_shot(job, iid, "qc", stage="qc")
        await shots.dev_delay()
        allow_faces = ctx["kind"] == "scenario" and not any(
            i["type"] == "real_person" for i in ((run.get("precheck") or {}).get("issues") or []))
        qc = await shots.quality_check(res["file_id"], width=res["width"], height=res["height"], products=ctx["products"],
                                       allow_faces=allow_faces, confidential=confidential, want_bbox=bool(flags.get("bbox")))
        if qc["status"] == "check" and attempts < config.qc_max_retry():
            attempts += 1
            prompt = f"{sp.get('prompt_en') or ''}\n{prompts.qc_correction(qc.get('fails') or {}, ctx['products'])}"
            await shots.set_shot(job, iid, "rendering", stage="render", label="다시 렌더링 중")
            continue
        break
    native = await shots.load_native(res["file_id"])
    gen = shots.generation_meta(provider=res.get("provider"), model=res.get("model"), call="t2i.generate",
                                prompt_ko=sp.get("prompt_ko") or ctx["description"], prompt_en=prompt,
                                references=plan.get("refs_meta") or [], products=plan.get("products_meta") or [],
                                policy_meta=policy_meta, fallbacks=fallbacks, upscale=None, confidential=confidential,
                                origin=ctx["origin"], extra={"qc_attempts": attempts + 1})
    await shots.finish_shot(job, run, img, native_file_id=res["file_id"], native_im=native, op="generate", generation=gen,
                            qc=qc, confidential=confidential, started=t0, ema=ema,
                            op_params={"angle_ko": sp.get("angle_ko")})


async def _render_composite(state: GenState, img: dict[str, Any], idx: int, *, ema: str, t0: float, fallbacks: list[str],
                            policy_meta: dict[str, Any]) -> None:
    """현장 사진: 결정적 합성(원근 워프) → t2i.edit(원근 · 조명 맞춤, 기하 유지) → 가장자리 IoU < 0.9 · 기밀 차단 · 편집 미지원이면 로컬 조화."""
    ctx = state["ctx"]
    job = current_job()
    iid = img["id"]
    run = await repo().get("runs", state["run_id"]) or {}
    comp = ctx.get("composite") or {}
    photo = await repo().get("photos", comp.get("active_photo_id"))
    if photo is None:
        raise shots.ShotFailed("no_photo", "현장 사진이 없어요")
    base = await common.load_photo_working(photo["file_id"])
    opts = comp.get("options") or {}
    draft, mask, bbox = await asyncio.to_thread(common.build_composite, base, comp.get("groups") or [], ctx["dims"],
                                                screen_menu=bool(opts.get("screen_menu", True)), variant=idx)
    fm = await save_image(draft, f"{iid}_draft.png", parent_id=photo["file_id"], source="derived", confidential=True,
                          meta={"image_id": iid, "draft": True}, purpose="img.draft")
    await shots.set_shot(job, iid, "composing", stage="compose", preview_file_id=fm["id"])
    await shots.dev_delay()
    await shots.check(job, iid, state["run_id"])
    await shots.set_shot(job, iid, "rendering", stage="render")
    flags = ctx["flags"]
    result = None
    call = "local"
    model = None
    provider = None
    native_fid = None
    menu_word = " Fill each screen with a clean, logo-free menu layout with food photos." if opts.get("screen_menu", True) else ""
    if opts.get("perspective_light_match", True) and flags.get("edit"):
        light = ["Daytime light.", "Warm afternoon light.", "Soft evening light.", "Bright even light."][idx % 4]
        instr = ("Make the inserted Samsung displays look naturally installed in this photo: match perspective, lighting, shadows "
                 f"and reflections. Keep the geometry, size and position of the displays and everything else exactly. {light}{menu_word}")
        try:
            res = await shots.t2i_edit("img.composite", {"file_id": fm["id"]}, instr, confidential=True,
                                       metadata={"run_id": state["run_id"], "image_id": iid})
            edited = await shots.load_native(res["file_id"])
            box = None
            if bbox:
                w, h = draft.size
                box = (int(bbox[0] * w), int(bbox[1] * h), max(int(bbox[0] * w) + 2, int(bbox[2] * w)), max(int(bbox[1] * h) + 2, int(bbox[3] * h)))
            iou = imaging.edge_iou(draft, edited.resize(draft.size), box) if box else 1.0
            if iou >= config.composite_edge_iou_min():
                result = edited.resize(draft.size)
                call, model, provider, native_fid = "t2i.edit", res.get("model"), res.get("provider"), res["file_id"]
                if opts.get("screen_menu", True):
                    fallbacks.append("screen:edit")
            else:
                fallbacks.append("composite:local_only")
                fallbacks.append(f"composite:edge_iou={iou:.2f}")
        except llm.ModelBlocked:
            fallbacks.append("composite:local_only")
        except (llm.QuotaExceeded, JobCanceled, shots.ShotCanceled):
            raise
        except Exception as exc:  # noqa: BLE001
            log.info("합성 편집 실패 → 로컬: %s", exc)
            fallbacks.append("composite:local_only")
    else:
        fallbacks.append("composite:local_only")
    if result is None:
        result = await asyncio.to_thread(imaging.local_harmonize, base, draft, mask, variant=idx)
        if opts.get("screen_menu", True):
            fallbacks.append("screen:template")
    await shots.set_shot(job, iid, "qc", stage="qc")
    qc = await shots.quality_check(fm["id"] if call == "local" else native_fid, width=result.width, height=result.height,
                                   products=ctx["products"], allow_faces=True, confidential=True, want_bbox=bool(flags.get("bbox")))
    gen = shots.generation_meta(provider=provider, model=model or "local", call=call, prompt_ko=ctx["description"] or "현장 사진 합성",
                                prompt_en="composite", references=[], products=state["plan"].get("products_meta") or [],
                                policy_meta=policy_meta, fallbacks=fallbacks, upscale=None, confidential=True, origin=ctx["origin"],
                                extra={"photo_file_id": photo["file_id"], "draft_file_id": fm["id"]})
    await shots.finish_shot(job, run, img, native_file_id=native_fid, native_im=result, op="composite", generation=gen, qc=qc,
                            confidential=True, started=t0, ema=ema, op_params={"photo_id": photo["id"], "variant": idx})


async def render(state: GenState) -> dict[str, Any]:
    await shots.set_phase(state["run_id"], "render")
    active = state.get("active") or []
    coros = [_render_one(state, iid, i) for i, iid in enumerate(active)]
    results = await common.gather_limited(config.shot_concurrency(), coros)
    _STOP.pop(state["run_id"], None)
    quota = None
    for iid, res in zip(active, results):
        if isinstance(res, shots.ShotCanceled):
            continue
        if isinstance(res, JobCanceled):
            raise res
        if isinstance(res, llm.QuotaExceeded):
            quota = res.message
            await shots.set_shot(current_job(), iid, "failed", label="실패", error=res.message)
        elif isinstance(res, shots.ShotFailed):
            await shots.set_shot(current_job(), iid, "failed", label="실패", error=res.message, fail_reason=res.reason)
        elif isinstance(res, Exception):
            log.exception("시안 실패 %s", iid, exc_info=res)
            await shots.set_shot(current_job(), iid, "failed", label="실패", error="이미지 모델이 응답하지 않아요")
    if quota:
        raise llm.QuotaExceeded(quota)
    await shots.run_progress(current_job(), state["run_id"])
    await shots.set_phase(state["run_id"], "qc")
    return {"active": []}


def after_render(state: GenState) -> str:
    return "await_alternatives" if state.get("held") else "finalize"


async def await_alternatives(state: GenState) -> dict[str, Any]:
    run = await repo().get("runs", state["run_id"]) or {}
    issues = (run.get("precheck") or {}).get("issues") or []
    answer = interrupt({"kind": "image.alternatives", "run_id": state["run_id"], "issues": issues, "held": state.get("held") or []})
    return {"answers": answer if isinstance(answer, dict) else {"answers": []}}


async def apply_answers(state: GenState) -> dict[str, Any]:
    ans = state.get("answers") or {}
    held = list(state.get("held") or [])
    if ans.get("skip_held"):
        for iid in held:
            await shots.set_shot(current_job(), iid, "canceled", label="취소됨")
        return {"held": [], "active": []}
    run = await repo().get("runs", state["run_id"]) or {}
    pre = dict(run.get("precheck") or {})
    issues = pre.get("issues") or []
    # 답이 이미 run.precheck 에 반영돼 있다(runs.answer). 선택 필요 이슈는 기본 대안으로 확정
    for it in issues:
        if not it.get("selected"):
            it["selected"] = policy.effective_option(it)
            it["state_label"] = "대안 선택됨"
    pre.update({"issues": issues, "applied_note": policy.applied_note(issues)})
    await repo().patch("runs", state["run_id"], {"precheck": pre, "held": 0})
    active = []
    for iid in held:
        img = await repo().get("images", iid)
        if img and img.get("status") == "held":
            await shots.set_shot(current_job(), iid, "waiting", label="대기 중")
            active.append(iid)
    return {"held": [], "active": active}


def after_answers(state: GenState) -> str:
    return "product_fit" if state.get("active") else "finalize"


async def finalize(state: GenState) -> dict[str, Any]:
    from .. import notify

    await notify.finish_run(state["run_id"])
    return {}


def build() -> StateGraph:
    g = StateGraph(GenState)
    for name, fn in (("load_context", load_context), ("policy_check", policy_check), ("split_shots", split_shots),
                     ("product_fit", product_fit), ("compose", compose), ("render", render),
                     ("await_alternatives", await_alternatives), ("apply_answers", apply_answers), ("finalize", finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "load_context")
    g.add_edge("load_context", "policy_check")
    g.add_edge("policy_check", "split_shots")
    g.add_edge("split_shots", "product_fit")
    g.add_edge("product_fit", "compose")
    g.add_edge("compose", "render")
    g.add_conditional_edges("render", after_render, {"await_alternatives": "await_alternatives", "finalize": "finalize"})
    g.add_edge("await_alternatives", "apply_answers")
    g.add_conditional_edges("apply_answers", after_answers, {"product_fit": "product_fit", "finalize": "finalize"})
    g.add_edge("finalize", END)
    return g


_ = now_iso
