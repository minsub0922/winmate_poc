"""조건으로 찾기(SP1C, 06-spec §6.3). 칩 변경은 동기 · 결정적(LLM 0), 문장 해석만 잡(spec_find)."""
from __future__ import annotations

import copy
from typing import Any

from fastapi import APIRouter
from winmate_common.errors import ApiError

from .. import config, ops, repo
from .. import finder as FS
from .. import sheet as S
from ..api_support import doc, enqueue, load
from ..models import FinderCommit, FinderParse, FinderPut, FinderState, JobAccepted, SheetDoc
from ..rules import text as T

router = APIRouter(prefix="/v1", tags=["find"])


def _mark_selected(st: dict[str, Any]) -> None:
    sel = set(st.get("selected") or [])
    for c in st.get("candidates") or []:
        c["selected"] = c.get("ref") in sel or c.get("model_code") in sel


@router.put("/sheets/{sheet_id}/finder", response_model=FinderState)
async def put_finder(sheet_id: str, body: FinderPut) -> dict[str, Any]:
    """칩 · 필수 · 추가 조건 · 숨기기 · 보기 · 선택 → 후보 다시 계산(결정적). preset 은 다른 화면에서 올 때 조건을 미리 채운다."""
    s = await load(sheet_id)
    st = copy.deepcopy(s.get("finder") or FS.empty_state())
    recompute = False
    if body.preset:
        cond, sel = FS.preset_state(s, body.preset)
        st["conditions"] = cond
        st["extra"] = []
        st["extra_caps"] = []
        st["query_text"] = None
        st["selected"] = sel
        recompute = True
    if body.conditions is not None:
        st["conditions"] = body.conditions.model_dump()
        recompute = True
    if body.extra is not None:
        st["extra"] = [e.model_dump() for e in body.extra]
        recompute = True
    if body.hide_out is not None and body.hide_out != bool(st.get("hide_out")):
        st["hide_out"] = body.hide_out
        recompute = True
    if body.view:
        st["view"] = body.view
    if body.selected is not None:
        st["selected"] = list(dict.fromkeys(body.selected))
    if recompute:
        if FS.is_empty(st):
            st.update({"candidates": [], "total_candidates": 0, "agent_text": None, "sort_label": None, "status": "idle"})
        else:
            st = await FS.compute(st)
    _mark_selected(st)

    def fn(x: dict[str, Any]) -> None:
        x["finder"] = st
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    if recompute:
        await ops.publish(saved)
    return st


@router.post("/sheets/{sheet_id}/finder:parse", response_model=JobAccepted, status_code=202)
async def parse_finder(sheet_id: str, body: FinderParse) -> dict[str, Any]:
    """문장 → 칩 · 추가 조건 · 후보(spec_find, 고객사 이름이 있을 수 있어 confidential)."""
    await load(sheet_id)
    text = body.text.strip()

    def before(x: dict[str, Any]) -> None:
        st = x.get("finder") or FS.empty_state()
        st["status"] = "running"
        st["error"] = None
        x["finder"] = st
        x["user_text"] = text

    job_id = await enqueue(sheet_id, "spec_find", {"text": text}, title="조건으로 모델 찾기", before=before)
    return {"job_id": job_id, "status": "queued", "sheet_id": sheet_id}


@router.post("/sheets/{sheet_id}/finder:commit", response_model=SheetDoc)
async def commit_finder(sheet_id: str, body: FinderCommit) -> dict[str, Any]:
    """고른 후보 → 제품. `items` 면 제목 확정 · step 2(SP2), `products` 면 SP1 에 머문다(모델명으로 직접 입력)."""
    s = await load(sheet_id)
    refs = list(dict.fromkeys([r for r in body.selected if r and r.strip()]))
    if not refs:
        raise ApiError(422, "NO_PRODUCTS", "시트에 넣을 모델을 하나 이상 골라 주세요.")
    replace = s.get("start") == "find"
    existing = [] if replace else list(s.get("products") or [])
    new: list[dict[str, Any]] = []
    for ref in refs:
        keep = next((p for p in s.get("products") or [] if p.get("ref") == ref or p.get("model_code") == ref), None)
        if keep is not None and replace:
            new.append(keep)
            continue
        if keep is not None:
            continue
        p = await ops.resolve_product(ref, source="find")
        if p is None or any(x.get("model_code") and x.get("model_code") == p.get("model_code") for x in existing + new):
            continue
        new.append(p)
    if len(existing) + len(new) > config.PRODUCT_LIMIT:
        raise ApiError(422, "PRODUCT_LIMIT", "한 시트에 8개까지 비교할 수 있어요.", {"limit": config.PRODUCT_LIMIT})
    tmp = copy.deepcopy(s)
    tmp["products"] = existing + new
    for i, p in enumerate(tmp["products"]):
        p["ord"] = i
    await ops.compute_preview(tmp)

    def fn(x: dict[str, Any]) -> None:
        if replace:
            kept = {p["id"] for p in tmp["products"]}
            x["cells"] = {k: v for k, v in (x.get("cells") or {}).items() if k.split("|")[1] in kept}
        x["products"] = tmp["products"]
        x["preview"] = tmp.get("preview") or {}
        if x.get("finder"):
            x["finder"]["selected"] = refs
            _mark_selected(x["finder"])
        S.recompute_kind(x)
        if body.to == "items":
            if not x.get("title_confirmed"):
                x["title"] = T.suggested_title(x)
                x["title_confirmed"] = True
            x["step"] = 2
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await ops.publish(saved)
    return await doc(saved)
