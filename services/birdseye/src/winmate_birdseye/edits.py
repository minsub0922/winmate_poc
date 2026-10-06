"""BE5 수정 요청(08-birdseye §7.9 · R8) — 분류 → 렌더 수정(같은 컷의 새 버전) · 배치 수정(엔진 → 새 레이아웃 → 주 컷 재렌더) ·
시점 요청(새 컷) · 섞임(배치 먼저, 렌더 지시는 새 컷 프롬프트에).

분류는 요청 때 바로(LLM `be.result_classify` · 기밀 → 막히거나 실패하면 낱말 규칙). 배치 · 시점은 엔진/대기열이라 바로 처리하고
렌더 수정만 잡(`result_edit`)으로 image 편집 렌더를 따라간다. 모호하면 W 가 한 번 되묻는다(route_hint='ask').
"""
from __future__ import annotations

import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso
from winmate_common.jobs import JobCanceled, current_job, jobs

from . import config, llm
from . import cuts as C
from . import layouts as L
from . import service as svc
from .repo import repo

log = logging.getLogger("winmate.birdseye.edits")

ASK = "어떤 항목을 어떻게 바꿀지 한 번만 더 알려 주세요. 예) 관람 벤치를 2열로 줄여줘 · 조명을 더 따뜻하게"

LAYOUT_WORDS = ("옮겨", "옮기", "이동", "빼줘", "빼 줘", "없애", "치워", "추가해", "열로", "줄여", "늘려", "붙여", "배치", "자리", "개로", "대로",
                "가운데로", "돌려", "회전")
VIEW_WORDS = ("시점", "각도", "입구에서", "위에서", "내려다", "탑뷰", "정면에서", "앵글", "카메라", "컷도", "컷 추가", "버전도")
RENDER_WORDS = ("조명", "따뜻", "밝게", "밝은", "어둡", "어두운", "색감", "색을", "톤을", "사람", "실루엣", "분위기", "질감", "마감", "반사",
                "선명", "화사", "하늘", "노을")


class ViewReq(BaseModel):
    preset: Literal["aerial45", "entrance", "product_front", "top"] | None = None
    custom_text: str | None = None
    light: Literal["day", "evening", "night"] | None = None
    before: bool = False


class Classified(BaseModel):
    kind: Literal["render", "layout", "view", "mixed"] = "render"
    render_instruction: str | None = Field(None, description="렌더 수정 지시(한국어 한 문장)")
    layout_ops: list[L.LOp] = Field(default_factory=list)
    view: ViewReq | None = None
    ambiguous: bool = False


def rule_classify(text: str) -> dict[str, Any]:
    t = text.strip()
    lay = any(w in t for w in LAYOUT_WORDS) or bool(L.regex_layout_ops(t))
    view = any(w in t for w in VIEW_WORDS) or ("야간" in t and "컷" in t) or ("도입 전" in t) or ("전후" in t)
    rend = any(w in t for w in RENDER_WORDS)
    if lay and rend:
        kind = "mixed"
    elif lay:
        kind = "layout"
    elif view:
        kind = "view"
    else:
        kind = "render"
    return {"kind": kind, "render_instruction": t if kind in ("render", "mixed") else None, "layout_ops": L.regex_layout_ops(t),
            "view": view_from_text(t) if kind == "view" else None, "ambiguous": False, "path": "classify:rules"}


def view_from_text(t: str) -> dict[str, Any]:
    v: dict[str, Any] = {"preset": None, "custom_text": None, "light": None, "before": False}
    if "입구" in t:
        v["preset"] = "entrance"
    elif "탑뷰" in t or "위에서 본" in t or "평면" in t:
        v["preset"] = "top"
    elif "정면" in t:
        v["preset"] = "product_front"
    elif "조감" in t:
        v["preset"] = "aerial45"
    elif any(w in t for w in ("시점", "각도", "내려다", "앵글", "카메라")):
        v["custom_text"] = t
    if "야간" in t or "밤" in t:
        v["light"] = "night"
    elif "저녁" in t:
        v["light"] = "evening"
    elif "주간" in t or "낮" in t:
        v["light"] = "day"
    if "도입 전" in t or "전후" in t:
        v["before"] = True
    return v


async def classify(text: str) -> dict[str, Any]:
    prompt = (f"조감도 결과 화면의 수정 요청: {text}\n"
              "kind 를 고른다: render(조명 · 색 · 사람 · 분위기 등 그림만 다듬기) · layout(제품 · 가구 위치 · 수량 · 크기 바꾸기) · "
              "view(시점 · 조명 컷을 새로 만들기) · mixed(배치와 그림 수정이 함께). layout 이면 layout_ops(op, target, dx, dy, qty …), "
              "view 면 view(preset · custom_text · light · before), render · mixed 면 render_instruction. 모호하면 ambiguous=true.")
    try:
        res = await llm.json_task("be.result_classify", prompt, Classified, confidential=True, timeout=30)
    except llm.ModelBlocked:
        res = None
    if not res:
        return rule_classify(text)
    res["path"] = "classify:llm"
    if res.get("kind") in ("layout", "mixed") and not res.get("layout_ops"):
        res["layout_ops"] = L.regex_layout_ops(text)
    if res.get("kind") == "view" and not res.get("view"):
        res["view"] = view_from_text(text)
    if res.get("kind") in ("render", "mixed") and not res.get("render_instruction"):
        res["render_instruction"] = text
    return res


async def _primary(be_id: str, cut_id: str | None) -> dict[str, Any] | None:
    b = await svc.get(be_id)
    cs = await svc.cuts(be_id)
    if cut_id:
        c = next((x for x in cs if x["id"] == cut_id), None)
        if c is None:
            raise not_found("컷", cut_id)
        return c
    return next((x for x in cs if x["id"] == b.get("primary_cut_id")), None) or next(
        (x for x in cs if x["status"] in ("done", "check", "draft")), None)


async def request(be_id: str, text: str, cut_id: str | None) -> dict[str, Any]:
    b = await svc.get(be_id)
    cut = await _primary(be_id, cut_id)
    cls = await classify(text)
    kind = cls.get("kind") or "render"
    if cls.get("ambiguous"):
        return {"route_hint": "ask", "job_id": None, "cut_id": cut["id"] if cut else None, "route": None, "question": ASK, "cut_ids": []}
    if kind in ("layout", "mixed"):
        lay = await L.get_layout(be_id)
        model = await svc.space_model(be_id)
        if lay is None or model is None:
            raise ApiError(409, "LAYOUT_NOT_READY", "배치안이 아직 없어요")
        ops = L.to_engine_ops(lay, cls.get("layout_ops") or [], model)
        if not ops:
            ops, _path = await L.interpret_ops(be_id, text, lay, model)
        if not ops:
            return {"route_hint": "ask", "job_id": None, "cut_id": cut["id"] if cut else None, "route": None, "question": ASK, "cut_ids": []}
        await L.apply_and_save(be_id, ops, created_by="nl_edit", note=f"result_edit:{cls.get('path')}")
        view = (cut or {}).get("view") or {"preset": b.get("default_view") or "aerial45"}
        spec = {"preset": view.get("preset") or "aerial45", "target_item_id": view.get("target_item_id")} if view.get("preset") != "custom" \
            else {"custom_text": view.get("custom_text")}
        body: dict[str, Any] = {"views": [spec], "lights": [(cut or {}).get("light") or "day"], "before": False, "primary": True,
                                "tone": (cut or {}).get("tone") or b.get("tone")}
        if kind == "mixed" and cls.get("render_instruction"):
            body["prompt_extra"] = [cls["render_instruction"]]
        acc = await C.create_cuts(be_id, body)
        return {"route_hint": kind, "job_id": acc.get("job_id"), "cut_id": (acc.get("cut_ids") or [None])[0], "route": acc.get("route"),
                "question": None, "cut_ids": acc.get("cut_ids") or []}
    if kind == "view":
        v = cls.get("view") or view_from_text(text)
        spec: dict[str, Any] = {"custom_text": v["custom_text"]} if v.get("custom_text") else {"preset": v.get("preset") or (cut or {}).get("view", {}).get("preset") or "aerial45"}
        light = v.get("light") or (cut or {}).get("light") or "day"
        acc = await C.create_cuts(be_id, {"views": [spec], "lights": [light], "before": bool(v.get("before"))})
        if not acc.get("cut_ids"):
            return {"route_hint": "view", "job_id": None, "cut_id": None, "route": f"/birdseye/{be_id}/result", "question": None,
                    "cut_ids": [], "notice": "같은 컷이 이미 있어요"}
        return {"route_hint": "view", "job_id": acc.get("job_id"), "cut_id": acc["cut_ids"][0], "route": acc.get("route"), "question": None,
                "cut_ids": acc.get("cut_ids") or []}
    # render — 같은 컷의 새 버전
    if cut is None:
        raise ApiError(409, "CUT_NOT_READY", "고칠 조감도 컷이 아직 없어요")
    if cut["status"] in ("queued", "running"):
        raise ApiError(409, "CUT_RUNNING", "이 컷은 아직 만들고 있어요. 진행 중 요청 칸에 남겨 주세요.")
    job_id = new_id("job")
    await repo().patch("cuts", cut["id"], {"edit_job_id": job_id, "edit_pending_text": None, "notice": None})
    await jobs().enqueue("birdseye", "result_edit", {"birdseye_id": be_id, "cut_id": cut["id"], "text": text,
                                                     "instruction": cls.get("render_instruction") or text, "force_kind": "render"},
                         title=f"{b['title']} · 수정 요청", ref=be_id, project_id=b.get("project_id"), owner=b["owner"],
                         owner_name=b.get("owner_name") or "", job_id=job_id)
    return {"route_hint": "render", "job_id": job_id, "cut_id": cut["id"], "route": f"/birdseye/{be_id}/result?cut={cut['id']}",
            "question": None, "cut_ids": [cut["id"]]}


async def run_render_edit(payload: dict[str, Any]) -> dict[str, Any]:
    """image 편집 렌더(edit_of = 현재 컷) → 같은 컷의 새 버전. 이전 버전은 컷 이력에 남긴다."""
    from . import render as R

    be_id = payload["birdseye_id"]
    cut_id = payload["cut_id"]
    instruction = payload.get("instruction") or payload.get("text") or ""
    b = await svc.get(be_id)
    c = await C.get_cut(cut_id)
    src = c.get("image_file_id") or c.get("draft_v1_file_id")
    if not src:
        raise ApiError(409, "CUT_NOT_READY", "고칠 이미지가 아직 없어요")
    ctx = current_job()
    if ctx is not None:
        await ctx.progress(5, "수정 요청 반영 준비")
    caps = await llm.caps()
    t2i = caps.get("t2i") or {}
    sup = t2i.get("supports") or {}
    if (caps and not t2i.get("available", True)) or not sup.get("edit", True) or c.get("render_path") == "render:draft_only":
        await repo().patch("cuts", cut_id, {"edit_pending_text": instruction, "notice": "이미지 편집을 쓸 수 없어 요청을 수정 요청 칸에 남겼어요"})
        return {"cut_id": cut_id, "applied": False}
    model = await svc.space_model(be_id) or {}
    lay = await L.get_layout(be_id, int(c.get("layout_version") or 0) or None) or {"items": [], "groups": []}
    prompt = R.build_prompt(b, model, lay, c, [instruction])
    people = "silhouette" if any(w in instruction for w in R.PEOPLE_WORDS) else (c.get("allow_people") or "none")
    body: dict[str, Any] = {
        "origin": {"service": "birdseye", "ref": cut_id, "label": f"{b['title']} · {svc.cut_label(c)} · 수정"},
        "project_id": b.get("project_id"), "kind": "birdseye", "prompt": prompt, "aspect": config.rules()["render"]["aspect"],
        "target": config.render_target(), "edit_of": {"file_id": src, "instruction": instruction},
        "forbid": ["competitor_logo", "real_person_face", "gibberish_text"], "allow_people": people, "confidential": R._confidential(b),
        "label": f"{svc.cut_label(c)} · 수정",
    }
    try:
        acc = await ServiceClient("image", timeout=60).post("/v1/renders", json=body)
    except ApiError as exc:
        if exc.status in (403, 501, 503) or exc.code in ("T2I_UNAVAILABLE", "POLICY_CONFIDENTIAL", "CAPABILITY_UNSUPPORTED"):
            await repo().patch("cuts", cut_id, {"edit_pending_text": instruction, "notice": "이미지 모델을 쓸 수 없어 요청을 수정 요청 칸에 남겼어요"})
            return {"cut_id": cut_id, "applied": False}
        raise
    try:
        res = await R._follow(cut_id, acc["render_id"])
    except JobCanceled:
        raise
    if res.get("status") != "succeeded":
        err = res.get("error") or {}
        raise ApiError(502, err.get("code") or "RENDER_FAILED", err.get("message") or "수정 렌더를 만들지 못했어요")
    rend = res.get("renditions") or []
    best = next((r for r in rend if r.get("kind") == "uhd"), None) or next((r for r in rend if r.get("kind") == "fhd"), None) \
        or next((r for r in rend if r.get("kind") == "native"), None)
    thumb = next((r for r in rend if r.get("kind") == "thumb"), None)
    c2 = await C.get_cut(cut_id)
    hist = list(c2.get("history") or [])
    hist.append({"image_file_id": c2.get("image_file_id"), "version_id": c2.get("version_id"), "renditions": c2.get("renditions") or [],
                 "label": f"v{len(hist) + 1}", "at": c2.get("finished_at") or now_iso()})
    await repo().patch("cuts", cut_id, {
        "history": hist, "image_id": res.get("image_id") or c2.get("image_id"), "version_id": res.get("version_id"), "renditions": rend,
        "image_file_id": best["file_id"] if best else c2.get("image_file_id"), "thumb_file_id": (thumb or best or {}).get("file_id"),
        "resolution": f"{best['w']}×{best['h']}" if best else c2.get("resolution"), "qc": res.get("qc") or c2.get("qc") or {},
        "generation": res.get("generation") or {}, "finished_at": now_iso(), "edit_job_id": None, "notice": "수정 요청을 반영했어요",
        "status": "check" if R.qc_flag(res.get("qc") or {}, c2.get("render_path")) else "done",
        "edit_count": int(c2.get("edit_count") or 0) + 1,
    })
    await svc.index(be_id)
    if ctx is not None:
        await ctx.progress(100, "완료")
    return {"cut_id": cut_id, "applied": True, "version_id": res.get("version_id")}


_ = (re, log)
