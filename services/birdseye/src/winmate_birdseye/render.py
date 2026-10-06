"""그래프 `be.render_cut`(08-birdseye §7.8) — 공간 구조 → 제품 배치(draft_v0, 미리보기) → 가구 · 마감재(draft_v1) → 조명 · 렌더링
(image 렌더 API, 자식 잡을 따라감) → 품질 확인 → 마무리.

- 모델 능력별 경로(§7.2): 참조 지원 → structure_ref = draft_v1(render:ref) · 참조 미지원 + 편집 → edit_of = draft_v1(render:edit) ·
  둘 다 없음 → 텍스트(render:text, 컷 check) · T2I 없음/막힘 → 초안을 톤 색으로 칠한 컷(render:draft_only, 「초안 렌더」).
- 조종 메모(진행 중 요청)는 다음 노드 시작 때 반영. 「조명 · 렌더링」 전 메모 → 프롬프트 · allow_people. 렌더 중 메모 → 끝난 뒤 edit_of 1회.
- 중지: 자식 잡 취소 → 마지막 초안을 컷 status=draft 로 남긴다.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import now_iso
from winmate_common.jobs import JobCanceled, current_job, jobs
from winmate_common.platform import save_file

from . import config, draft, llm
from . import service as svc
from . import space as S
from . import text as T
from .repo import repo

log = logging.getLogger("winmate.birdseye.render")

PEOPLE_WORDS = ("사람", "실루엣", "인물", "고객", "손님")


class CutState(TypedDict, total=False):
    cut_id: str
    birdseye_id: str
    notes: dict[str, str]
    prompt_extra: list[str]
    allow_people: str
    stage_t: dict[str, float]


LABELS = {"load": "준비", "structure": "공간 구조", "products": "제품 배치", "furniture": "가구 · 마감재", "render": "조명 · 렌더링",
          "qc": "품질 확인", "finalize": "마무리"}


# ── 진행 · ETA ───────────────────────────────────────────

async def _ema(stage: str) -> float:
    st = await repo().get("stats", f"stage:{stage}")
    if st and st.get("avg_s"):
        return float(st["avg_s"])
    return float(config.rules()["render"]["default_stage_s"].get(stage, 2))


async def _record(stage: str, secs: float) -> None:
    alpha = float(config.rules()["render"].get("eta_ema_alpha", 0.3))
    prev = await repo().get("stats", f"stage:{stage}")
    avg = float(prev["avg_s"]) if prev and prev.get("avg_s") else secs
    await repo().put("stats", f"stage:{stage}", {"avg_s": round(avg * (1 - alpha) + secs * alpha, 2)})


async def _eta(after: str | None) -> float:
    order = ["structure", "products", "furniture", "render", "qc"]
    idx = order.index(after) + 1 if after in order else 0
    return round(sum([await _ema(s) for s in order[idx:]]), 1)


async def _set_stage(cut_id: str, stage: str, state: str, note: str | None = None, progress: float | None = None,
                     eta_after: str | None = None) -> None:
    c = await repo().get("cuts", cut_id) or {}
    steps = c.get("steps") or []
    for s in steps:
        if s["stage"] == stage:
            s["state"] = "run" if state == "run" else ("done" if state == "done" else "wait")
            if note is not None:
                s["note"] = note
    changes: dict[str, Any] = {"steps": steps, "stage": stage}
    if progress is not None:
        changes["progress"] = round(progress, 1)
    changes["eta_s"] = await _eta(eta_after if eta_after else (stage if state == "done" else None))
    await repo().patch("cuts", cut_id, changes)
    ctx = current_job()
    if ctx is not None:
        await ctx.step(stage, state, stage=stage, state=state, note=note or "", label=dict(LABELS).get(stage, stage))
        if progress is not None:
            await ctx.progress(progress, dict(LABELS).get(stage, stage), eta_s=changes["eta_s"])


async def _memos() -> list[str]:
    ctx = current_job()
    if ctx is None:
        return []
    return [m.get("text", "") for m in await ctx.new_memos() if m.get("text")]


async def _check_cancel() -> None:
    ctx = current_job()
    if ctx is not None:
        await ctx.check_cancel()


# ── 노드 ─────────────────────────────────────────────────

async def n_load(state: CutState) -> dict[str, Any]:
    c = await repo().get("cuts", state["cut_id"])
    if c is None:
        raise ApiError(404, "NOT_FOUND", "컷을 찾을 수 없어요")
    await repo().patch("cuts", c["id"], {"status": "running", "progress": 1.0, "error": None})
    await svc.index(c["birdseye_id"])
    people = "silhouette" if any(any(w in m for w in PEOPLE_WORDS) for m in c.get("prompt_extra") or []) else "none"
    return {"birdseye_id": c["birdseye_id"], "notes": {}, "prompt_extra": list(c.get("prompt_extra") or []), "allow_people": people,
            "stage_t": {}}


async def _ctx_data(state: CutState) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    from .layouts import get_layout

    c = await repo().get("cuts", state["cut_id"]) or {}
    b = await svc.get(state["birdseye_id"])
    model = await svc.space_model(b["id"]) or {}
    lay = await get_layout(b["id"], int(c.get("layout_version") or 0) or None) or {"items": [], "groups": []}
    return c, b, model, lay


async def n_structure(state: CutState) -> dict[str, Any]:
    t0 = time.monotonic()
    c, b, model, lay = await _ctx_data(state)
    note = S.stage_note(model)
    await _set_stage(c["id"], "structure", "run", note, 4)
    # 시점 설명 → 카메라(LLM JSON + 엔진 범위 제한 · 대체 키워드 규칙)
    view = c["view"]
    if view.get("preset") == "custom" and not c.get("camera"):
        cam, path = await custom_camera(model, view.get("custom_text") or "")
        view = {**view, "camera": cam, "meta_path": path}
        await repo().patch("cuts", c["id"], {"view": view})
    extra = [m for m in await _memos()]
    people = state.get("allow_people", "none")
    if any(any(w in m for w in PEOPLE_WORDS) for m in extra):
        people = "silhouette"
    await _set_stage(c["id"], "structure", "done", note, 10)
    await _record("structure", time.monotonic() - t0)
    return {"prompt_extra": list(state.get("prompt_extra") or []) + extra, "allow_people": people}


class CameraOut(dict):
    pass


async def custom_camera(model: dict[str, Any], text: str) -> tuple[dict[str, Any], str]:
    from pydantic import BaseModel, Field

    class Cam(BaseModel):
        pos: list[float] = Field(description="[x, y, z] m")
        target: list[float] = Field(description="[x, y, z] m")
        fov_deg: float = 50

    minx, miny, maxx, maxy = S.bbox_of(model)
    h = (model.get("ceiling_h") or {}).get("value") or 3.0
    prompt = (f"평면 범위 x {minx:.1f}~{maxx:.1f} m, y {miny:.1f}~{maxy:.1f} m(y 가 클수록 뒤쪽), 층고 {h} m. 정면(주출입구)은 y = {miny:.1f} 쪽.\n"
              f"시점 설명: {text}\n카메라 위치 · 바라보는 점 · FOV 를 JSON 으로.")
    try:
        res = await llm.json_task("be.camera", prompt, Cam, confidential=True, timeout=30)
    except llm.ModelBlocked:
        res = None
    if res and res.get("pos") and len(res["pos"]) >= 3 and res.get("target") and len(res["target"]) >= 3:
        return draft.clamp_custom(model, res), "camera:llm"
    return draft.rules_camera(model, text), "camera:rules"


async def _save_png(b: dict[str, Any], png: bytes, name: str, purpose: str) -> str:
    parent = (b.get("inputs") or {}).get("plan_file_ids") or []
    meta = await save_file(name, png, "image/png", source="generated", confidential=_confidential(b), project_id=b.get("project_id"),
                           parent_id=parent[0] if parent else None, purpose=purpose)
    return meta["id"]


def _confidential(b: dict[str, Any]) -> bool:
    inputs = b.get("inputs") or {}
    return bool(inputs.get("plan_file_ids") or inputs.get("photo_count") or inputs.get("description"))


async def n_products(state: CutState) -> dict[str, Any]:
    t0 = time.monotonic()
    await _check_cancel()
    c, b, model, lay = await _ctx_data(state)
    note = " · ".join(g.get("label") or "" for g in lay.get("groups", []) if g.get("kind") == "product")
    await _set_stage(c["id"], "products", "run", note, 14)
    view = (await repo().get("cuts", c["id"]) or c)["view"]
    png, cam = await asyncio.to_thread(draft.render, model, lay, view=view, tone=c.get("tone"), light="day", stage="v0", before=bool(c.get("before")))
    fid = await _save_png(b, png, f"{b['id']}_{c['id']}_draft_v0.png", "birdseye.draft")
    await repo().patch("cuts", c["id"], {"draft_file_id": fid, "camera": cam})
    ctx = current_job()
    if ctx is not None:
        await ctx.partial({"kind": "preview", "draft_file_id": fid, "label": f"초안 · {c['view'].get('label')}"})
    await _set_stage(c["id"], "products", "done", note, 25)
    await _record("products", time.monotonic() - t0)
    return {}


async def n_furniture(state: CutState) -> dict[str, Any]:
    t0 = time.monotonic()
    await _check_cancel()
    c, b, model, lay = await _ctx_data(state)
    shorts = []
    for g in lay.get("groups", []):
        if g.get("kind") in ("furniture", "column_wrap"):
            nm = g.get("short") or g.get("label") or ""
            if nm and nm not in shorts:
                shorts.append(nm)
    note = " · ".join(shorts + [config.tone_info(c.get("tone"))["label"]])
    await _set_stage(c["id"], "furniture", "run", note, 30)
    view = (await repo().get("cuts", c["id"]) or c)["view"]
    png, cam = await asyncio.to_thread(draft.render, model, lay, view=view, tone=c.get("tone"), light=c.get("light") or "day",
                                       stage="v1", before=bool(c.get("before")))
    fid = await _save_png(b, png, f"{b['id']}_{c['id']}_draft_v1.png", "birdseye.draft")
    await repo().patch("cuts", c["id"], {"draft_v1_file_id": fid, "camera": cam})
    await _set_stage(c["id"], "furniture", "done", note, 38)
    await _record("furniture", time.monotonic() - t0)
    extra = await _memos()
    people = state.get("allow_people", "none")
    if any(any(w in m for w in PEOPLE_WORDS) for m in extra):
        people = "silhouette"
    return {"prompt_extra": list(state.get("prompt_extra") or []) + extra, "allow_people": people}


def build_prompt(b: dict[str, Any], model: dict[str, Any], lay: dict[str, Any], c: dict[str, Any], extra: list[str]) -> dict[str, Any]:
    tone = config.tone_info(c.get("tone"))
    light = config.light_info(c.get("light"))
    room = (model.get("rooms") or [{}])[0].get("label") or b.get("space_label") or "공간"
    details = [
        f"평면 약 {T.pyeong_label(model.get('area_m2'))}, 층고 {T.num((model.get('ceiling_h') or {}).get('value'))} m",
        f"인테리어 톤: {tone['label']} — {tone['material_ko']}",
        f"조명: {light['desc']}",
        f"시점: {c['view'].get('label')}",
        "참조 이미지의 모든 물체 위치 · 크기 · 개수를 그대로 따른다(구도 · 배치를 정확히 따름)",
        "디스플레이 화면은 로고 · 글자 없는 추상 콘텐츠",
    ]
    if not c.get("before"):
        for g in lay.get("groups", []):
            if g.get("kind") == "product":
                details.append(f"삼성 {g.get('label')} — {g.get('anchor_label') or '배치안 위치'}")
            elif g.get("kind") in ("furniture", "column_wrap"):
                details.append(f"{g.get('label')}")
    else:
        details.append("제품 · 가구를 모두 뺀 현재 공간(도입 전 비교용)")
    for f in model.get("features", []):
        if f.get("kind") != "night_visibility":
            details.append(f.get("label"))
    details += [e for e in extra if e]
    subject = f"{room} 3D 조감도 — {c['view'].get('label')} · {light['label']}"
    return {"subject_ko": subject, "details_ko": details, "negatives": ["경쟁사 로고", "읽을 수 없는 글자", "실존 인물 얼굴"]}


async def n_render(state: CutState) -> dict[str, Any]:
    t0 = time.monotonic()
    await _check_cancel()
    c, b, model, lay = await _ctx_data(state)
    light = config.light_info(c.get("light"))
    note = f"{light['desc']} · {c.get('resolution') or '3840×2160'}"
    await _set_stage(c["id"], "render", "run", note, 40)
    extra = list(state.get("prompt_extra") or []) + await _memos()
    people = state.get("allow_people", "none")
    if any(any(w in m for w in PEOPLE_WORDS) for m in extra):
        people = "silhouette"
    caps = await llm.caps()
    t2i = caps.get("t2i") or {}
    sup = t2i.get("supports") or {}
    available = t2i.get("available", True) if caps else True
    draft_fid = c.get("draft_v1_file_id") or c.get("draft_file_id")
    prompt = build_prompt(b, model, lay, c, extra)
    products = []
    seen = set()
    if not c.get("before"):
        for g in lay.get("groups", []):
            if g.get("kind") != "product":
                continue
            key = g.get("model_code") or g.get("family_id")
            if key in seen:
                continue
            seen.add(key)
            products.append({"family_id": g.get("family_id") or None, "model_code": g.get("model_code"), "qty": max(1, min(99, int(g.get("qty") or 1)))})
    boxes = draft.product_boxes(c.get("camera") or {}, lay) if c.get("camera") and not c.get("before") else []
    expect = {"products": [{"family_id": g.get("family_id"), "model_code": g.get("model_code"), "qty": int(g.get("qty") or 1),
                            "bbox_hint": next((bx["box"] for bx in boxes if bx["group_id"] == g["id"]), None)}
                           for g in lay.get("groups", []) if g.get("kind") == "product"]} if not c.get("before") else None
    body: dict[str, Any] = {
        "origin": {"service": "birdseye", "ref": c["id"], "label": f"{b['title']} · {svc.cut_label(c)}"},
        "project_id": b.get("project_id"), "kind": "birdseye", "prompt": prompt, "aspect": config.rules()["render"]["aspect"],
        "target": config.render_target(), "product_refs": products, "forbid": ["competitor_logo", "real_person_face", "gibberish_text"],
        "allow_people": people, "confidential": _confidential(b), "label": svc.cut_label(c),
    }
    if expect and expect["products"]:
        body["expect"] = expect
    if (b.get("reference_image") or {}).get("file_id"):
        body["reference_file_ids"] = [b["reference_image"]["file_id"]]
    path = "render:ref"
    if not available:
        path = "render:draft_only"
    elif sup.get("reference_images", True):
        body["structure_ref_file_id"] = draft_fid
    elif sup.get("edit", False):
        body["edit_of"] = {"file_id": draft_fid, "instruction": "이 구도 · 배치를 정확히 따르면서 사실적인 3D 조감도로 다듬어 주세요"}
        path = "render:edit"
    else:
        path = "render:text"
    result: dict[str, Any] = {}
    if path != "render:draft_only":
        try:
            acc = await ServiceClient("image", timeout=60).post("/v1/renders", json=body)
            await repo().patch("cuts", c["id"], {"render_id": acc["render_id"], "child_job_id": acc.get("job_id"), "render_path": path,
                                                 "prompt": prompt, "allow_people": people, "memos_used": len(extra)})
            result = await _follow(c["id"], acc["render_id"])
        except JobCanceled:
            raise
        except ApiError as exc:
            if exc.code in ("T2I_UNAVAILABLE", "POLICY_CONFIDENTIAL", "CAPABILITY_UNSUPPORTED") or exc.status in (403, 501, 503):
                path = "render:draft_only"
                result = {}
            else:
                raise
        if result.get("status") == "failed":
            err = (result.get("error") or {})
            if err.get("code") in ("T2I_UNAVAILABLE", "POLICY_CONFIDENTIAL", "QUOTA_EXCEEDED", "DAILY_LIMIT_EXCEEDED"):
                path = "render:draft_only"
            else:
                raise ApiError(502, err.get("code") or "RENDER_FAILED", err.get("message") or "이미지 모델이 응답하지 않아요")
    if path == "render:draft_only":
        src = draft_fid
        from winmate_common.platform import file_bytes

        png, _mime = await file_bytes(src)
        tinted = await asyncio.to_thread(draft.tint_png, png, c.get("tone"), c.get("light") or "day")
        fid = await _save_png(b, tinted, f"{b['id']}_{c['id']}_draft_render.png", "birdseye.cut")
        await repo().patch("cuts", c["id"], {"image_file_id": fid, "thumb_file_id": fid, "render_path": path, "badge": "초안 렌더",
                                             "resolution": "1024×576", "renditions": [], "prompt": prompt})
    else:
        rend = result.get("renditions") or []
        best = next((r for r in rend if r.get("kind") == "uhd"), None) or next((r for r in rend if r.get("kind") == "fhd"), None) \
            or next((r for r in rend if r.get("kind") == "native"), None)
        thumb = next((r for r in rend if r.get("kind") == "thumb"), None)
        res_label = f"{best['w']}×{best['h']}" if best else c.get("resolution")
        await repo().patch("cuts", c["id"], {
            "image_id": result.get("image_id"), "version_id": result.get("version_id"), "renditions": rend,
            "image_file_id": best["file_id"] if best else None, "thumb_file_id": (thumb or best or {}).get("file_id"),
            "resolution": res_label, "qc": result.get("qc") or {}, "generation": result.get("generation") or {}, "render_path": path,
        })
    await _set_stage(c["id"], "render", "done", note, 90)
    await _record("render", time.monotonic() - t0)
    return {"allow_people": people, "prompt_extra": extra}


async def _follow(cut_id: str, render_id: str) -> dict[str, Any]:
    """자식 렌더를 따라간다(진행 40 → 88). 취소면 자식 취소."""
    img = ServiceClient("image", timeout=30)
    deadline = time.monotonic() + config.render_timeout_s()
    poll = config.render_poll_s()
    last = 40.0
    while True:
        ctx = current_job()
        if ctx is not None and await ctx.jobs.is_canceled(ctx.job.id):
            try:
                await img.post(f"/v1/renders/{render_id}:cancel")
            except Exception as exc:  # noqa: BLE001
                log.warning("자식 렌더 취소 실패: %s", exc)
            raise JobCanceled()
        r = await img.get(f"/v1/renders/{render_id}")
        if r.get("status") in ("succeeded", "failed", "canceled"):
            return r
        child = r.get("job_id")
        pct = last
        if child:
            j = await jobs().get(child)
            if j is not None:
                pct = 40 + 48 * (j.progress / 100.0)
        if pct > last + 0.5:
            last = pct
            await repo().patch("cuts", cut_id, {"progress": round(pct, 1), "eta_s": round(max(0.0, (await _ema("render")) * (1 - (pct - 40) / 48)) + await _ema("qc"), 1)})
            if ctx is not None:
                await ctx.progress(pct, "조명 · 렌더링")
        if time.monotonic() > deadline:
            raise ApiError(504, "TIMEOUT", "이미지 생성이 너무 오래 걸려요")
        await asyncio.sleep(poll)


async def n_qc(state: CutState) -> dict[str, Any]:
    t0 = time.monotonic()
    await _check_cancel()
    c, b, model, lay = await _ctx_data(state)
    note = "제품 비율 · 겹침 · 로고 노출 점검"
    await _set_stage(c["id"], "qc", "run", note, 92)
    flag = qc_flag(c.get("qc") or {}, c.get("render_path"))
    await repo().patch("cuts", c["id"], {"qc_flag": flag})
    await _set_stage(c["id"], "qc", "done", note, 98)
    await _record("qc", time.monotonic() - t0)
    return {}


def qc_flag(qc: dict[str, Any], render_path: str | None) -> bool:
    """image 품질 확인(제품 수 · 비율 · 로고) 또는 텍스트만 렌더 → 컷 check."""
    return str(qc.get("status") or qc.get("verdict") or "").lower() in ("check", "fail", "failed", "warn") or qc.get("ok") is False \
        or bool(qc.get("flag")) or render_path == "render:text"


async def n_finalize(state: CutState) -> dict[str, Any]:
    c, b, model, lay = await _ctx_data(state)
    status = "check" if c.get("qc_flag") else "done"
    changes: dict[str, Any] = {"status": status, "progress": 100.0, "eta_s": 0, "finished_at": now_iso(), "stage": "qc"}
    pending = []
    ctx = current_job()
    if ctx is not None:
        pending = [m.get("text", "") for m in await ctx.new_memos() if m.get("text")]
    await repo().patch("cuts", c["id"], changes)
    if c.get("is_primary") or not b.get("primary_cut_id"):
        if not c.get("before"):
            for x in await svc.cuts(b["id"]):
                if x.get("is_primary") and x["id"] != c["id"]:
                    await repo().patch("cuts", x["id"], {"is_primary": False})
            await repo().patch("cuts", c["id"], {"is_primary": True})
            await svc.touch(b["id"], primary_cut_id=c["id"])
    if pending:
        await _after_memos(c, b, pending)
    await svc.index(b["id"])
    if ctx is not None:
        await ctx.jobs.push_notification(b["owner"], {"type": "be_cut_done", "job_id": ctx.job.id, "service": "birdseye", "kind": "render_cut",
                                                      "title": f"{b['title']} · 3D 조감도 완성", "ref": b["id"], "status": "succeeded",
                                                      "route": f"/birdseye/{b['id']}/result?cut={c['id']}"})
    return {}


async def _after_memos(c: dict[str, Any], b: dict[str, Any], memos: list[str]) -> None:
    """렌더 중 도착한 메모 — 편집 지원이면 edit_of 렌더 1회, 아니면 수정 요청 칸에 채움."""
    caps = await llm.caps()
    sup = ((caps.get("t2i") or {}).get("supports") or {})
    text = " / ".join(memos)
    c2 = await repo().get("cuts", c["id"]) or c
    if sup.get("edit", False) and c2.get("image_file_id") and c2.get("render_path") != "render:draft_only":
        from winmate_common.jobs import jobs as _jobs

        await _jobs().enqueue("birdseye", "result_edit", {"birdseye_id": b["id"], "cut_id": c["id"], "text": text, "force_kind": "render"},
                              title=f"{b['title']} · 진행 중 요청 반영", ref=b["id"], owner=b["owner"], owner_name=b.get("owner_name") or "")
        await repo().patch("cuts", c["id"], {"notice": "진행 중 요청을 완성 뒤 한 번 더 반영하고 있어요"})
    else:
        await repo().patch("cuts", c["id"], {"edit_pending_text": text, "notice": "진행 중 요청은 완성 후 수정 요청으로 남겼어요"})


def build() -> StateGraph:
    g = StateGraph(CutState)
    for name, fn in (("load", n_load), ("structure", n_structure), ("products", n_products), ("furniture", n_furniture),
                     ("render", n_render), ("qc", n_qc), ("finalize", n_finalize)):
        g.add_node(name, fn)
    g.add_edge(START, "load")
    g.add_edge("load", "structure")
    g.add_edge("structure", "products")
    g.add_edge("products", "furniture")
    g.add_edge("furniture", "render")
    g.add_edge("render", "qc")
    g.add_edge("qc", "finalize")
    g.add_edge("finalize", END)
    return g


async def on_cancel(cut_id: str) -> None:
    """중지 — 마지막 초안을 컷 draft 로 저장."""
    c = await repo().get("cuts", cut_id)
    if c is None:
        return
    has = c.get("draft_v1_file_id") or c.get("draft_file_id")
    await repo().patch("cuts", cut_id, {"status": "draft" if has else "canceled", "finished_at": now_iso(),
                                        "image_file_id": c.get("image_file_id") or (c.get("draft_v1_file_id") or c.get("draft_file_id")),
                                        "badge": c.get("badge") or ("초안" if has else None)})
    if not has:
        await repo().delete("cuts", cut_id)


async def on_fail(cut_id: str, message: str) -> None:
    await repo().patch("cuts", cut_id, {"status": "failed", "error": message, "finished_at": now_iso()})
