"""고객 요구 대응표(SP1R, 06-spec §6.4). 규격서 분석은 잡(spec_compliance, confidential), 나머지는 동기."""
from __future__ import annotations

import copy
from typing import Any

from fastapi import APIRouter, Response
from winmate_common.errors import ApiError
from winmate_common.ids import new_id
from winmate_common.platform import file_meta

from .. import compliance as CP
from .. import ops, repo
from .. import sheet as S
from ..api_support import doc, enqueue, load
from ..models import AskDraft, Compliance, CompliancePatch, ComplianceRow, ComplianceRowPatch, JobAccepted, PageView, RequirementDocBody, SheetDoc
from ..rules import compliance as C
from ..rules import text as T

router = APIRouter(prefix="/v1", tags=["compliance"])

DOC_KINDS = ("pdf", "docx", "xlsx", "pptx", "image", "text")


async def _meta_or_error(file_id: str) -> dict[str, Any]:
    try:
        return await file_meta(file_id)
    except ApiError as exc:
        if exc.status == 404:
            raise ApiError(404, "NOT_FOUND", "파일을 찾지 못했어요.", {"file_id": file_id}) from exc
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", "파일 서비스에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.") from exc


def _view(s: dict[str, Any]) -> dict[str, Any]:
    v = S.compliance_view(s)
    if v is None:
        return {"status": "empty", "docs": [], "rows": [], "counts": {"pass": 0, "fail": 0, "unknown": 0}}
    rows = []
    for r in v.get("rows") or []:
        rows.append({**r, "value_text": r.get("value_text") or "—", "verdict": r.get("verdict") or "unknown", "overridden": bool(r.get("user_override"))})
    return {**v, "rows": rows, "folded_line": C.folded_line(rows)}


@router.post("/sheets/{sheet_id}/requirement-docs", response_model=JobAccepted, status_code=202)
async def add_requirement_doc(sheet_id: str, body: RequirementDocBody) -> dict[str, Any]:
    """규격서 올리기(PDF · DOCX · XLSX · 이미지) → spec_compliance. 다른 규격서를 더 올리면 행이 합쳐진다."""
    await load(sheet_id)
    meta = await _meta_or_error(body.file_id)
    if meta.get("kind") not in DOC_KINDS:
        raise ApiError(422, "UNSUPPORTED_FILE", "PDF · DOCX · XLSX · 이미지 규격서만 읽을 수 있어요. HWP 는 PDF 로 저장해 올려 주세요.",
                       {"kind": meta.get("kind")})
    doc_id = new_id("srd")
    entry = {"id": doc_id, "file_id": body.file_id, "name": meta.get("name") or "규격서", "format": CP.FORMAT_LABEL.get(meta.get("kind") or "", "파일"),
             "pages": meta.get("pages") or 0, "recognized": 0, "status": "running", "note": body.note}

    def before(x: dict[str, Any]) -> None:
        comp = x.get("compliance") or {"docs": [], "rows": [], "include": {"table": True, "spec": True, "page_refs": True, "alternative": False}}
        comp["docs"] = [d for d in comp.get("docs") or [] if d["id"] != doc_id] + [entry]
        comp["status"] = "running"
        comp["error"] = None
        comp["note"] = body.note
        x["compliance"] = comp
        if body.note:
            x["user_text"] = body.note

    job_id = await enqueue(sheet_id, "spec_compliance", {"doc_id": doc_id, "file_id": body.file_id, "note": body.note},
                           title="요구 규격서 분석", before=before)
    return {"job_id": job_id, "status": "queued", "sheet_id": sheet_id}


@router.get("/sheets/{sheet_id}/compliance", response_model=Compliance)
async def get_compliance(sheet_id: str) -> dict[str, Any]:
    return _view(await load(sheet_id))


@router.patch("/sheets/{sheet_id}/compliance", response_model=Compliance, responses={202: {"model": Compliance, "description": "대응 모델이 바뀌어 다시 판정 중"}})
async def patch_compliance(sheet_id: str, body: CompliancePatch, response: Response) -> dict[str, Any]:
    """대응 모델 · 시트에 넣기 칩. 대응 모델이 바뀌면 다시 판정(202, spec_compliance reevaluate)."""
    s = await load(sheet_id)
    if not s.get("compliance"):
        raise ApiError(404, "NOT_FOUND", "아직 대응표가 없어요. 규격서를 먼저 올려 주세요.")
    new_target: dict[str, Any] | None = None
    if body.target_ref:
        new_target = await ops.resolve_product(body.target_ref, source="requirements")
        if new_target is None:
            raise ApiError(422, "VALIDATION_FAILED", "모델을 찾지 못했어요.")
    elif body.target_product_id:
        if not any(p["id"] == body.target_product_id for p in s.get("products") or []):
            raise ApiError(404, "NOT_FOUND", "시트에 없는 제품이에요.")
    if body.include is not None:
        inc = {**((s.get("compliance") or {}).get("include") or {}), **{k: bool(v) for k, v in body.include.items()
                                                                       if k in ("table", "spec", "page_refs", "alternative")}}
        if not inc.get("table") and not inc.get("spec"):
            raise ApiError(422, "VALIDATION_FAILED", "요구사항 대응표와 스펙표 중 하나는 켜 두어야 해요.")
    changed = {"target": False}

    def fn(x: dict[str, Any]) -> None:
        comp = x["compliance"]
        if new_target is not None:
            exist = next((p for p in x.get("products") or [] if p.get("model_code") and p.get("model_code") == new_target.get("model_code")), None)
            if exist is None:
                if len(x.get("products") or []) >= 8:
                    raise ApiError(422, "PRODUCT_LIMIT", "한 시트에 8개까지 비교할 수 있어요.", {"limit": 8})
                new_target["ord"] = len(x.get("products") or [])
                x.setdefault("products", []).append(new_target)
                exist = new_target
            if comp.get("target_product_id") != exist["id"]:
                comp["target_product_id"] = exist["id"]
                changed["target"] = True
        elif body.target_product_id and comp.get("target_product_id") != body.target_product_id:
            comp["target_product_id"] = body.target_product_id
            changed["target"] = True
        if body.include is not None:
            comp["include"] = {**(comp.get("include") or {}), **{k: bool(v) for k, v in body.include.items()
                                                                 if k in ("table", "spec", "page_refs", "alternative")}}
        if changed["target"]:
            comp["status"] = "running"
            comp["picked_by_finder"] = False
        S.recompute_kind(x)
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    if changed["target"]:
        await enqueue(sheet_id, "spec_compliance", {"reevaluate": True}, title="대응 모델 다시 판정")
        saved = await repo.amust("sheets", sheet_id)
        response.status_code = 202
    await ops.publish(saved)
    return _view(saved)


@router.patch("/sheets/{sheet_id}/compliance/rows/{row_id}", response_model=ComplianceRow)
async def patch_compliance_row(sheet_id: str, row_id: str, body: ComplianceRowPatch) -> dict[str, Any]:
    """판정 고치기(사람이 확인한 결과) · 메모."""
    await load(sheet_id)
    out: dict[str, Any] = {}

    def fn(x: dict[str, Any]) -> None:
        comp = x.get("compliance") or {}
        r = next((r for r in comp.get("rows") or [] if r["id"] == row_id), None)
        if r is None:
            raise ApiError(404, "NOT_FOUND", "요구 행을 찾을 수 없어요.")
        if body.verdict_override is not None:
            r.setdefault("verdict_auto", r.get("verdict"))
            r["verdict"] = body.verdict_override
            r["user_override"] = True
            if body.verdict_override == "pass" and r.get("alternative"):
                r.pop("alternative", None)
        if body.note is not None:
            r["note"] = body.note.strip() or None
        CP.agent_and_title(x)
        S.refresh_status(x, x["id"])
        out.update(r)

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await ops.publish(saved)
    return {**out, "value_text": out.get("value_text") or "—", "overridden": bool(out.get("user_override"))}


@router.get("/sheets/{sheet_id}/compliance/ask-draft", response_model=AskDraft)
async def ask_draft(sheet_id: str) -> dict[str, Any]:
    """`확인 필요 {n}건 담당자에게 묻기` 초안(복사 · mailto)."""
    return CP.ask_draft(await load(sheet_id))


@router.get("/sheets/{sheet_id}/requirement-docs/{doc_id}/pages/{n}", response_model=PageView)
async def requirement_page(sheet_id: str, doc_id: str, n: int) -> dict[str, Any]:
    """원문 쪽(이미지는 files 쪽 렌더) + 그 쪽의 인용들."""
    return CP.page_view(await load(sheet_id), doc_id, n)


@router.post("/sheets/{sheet_id}/compliance:to-items", response_model=SheetDoc)
async def compliance_to_items(sheet_id: str) -> dict[str, Any]:
    """`대응표로 시트 만들기` — 제목 확정 · 제품(대응 모델 + 켰으면 대안) · 요구 관련 항목 미리 체크 · step 2."""
    s = await load(sheet_id)
    comp = s.get("compliance") or {}
    if comp.get("status") != "done" or not comp.get("rows"):
        raise ApiError(422, "NO_COMPLIANCE", "규격서 분석이 끝난 뒤에 시트를 만들 수 있어요.")
    target = next((p for p in s.get("products") or [] if p["id"] == comp.get("target_product_id")), None)
    if target is None:
        raise ApiError(422, "NO_PRODUCTS", "대응 모델을 먼저 골라 주세요.")
    alt_products: list[dict[str, Any]] = []
    if (comp.get("include") or {}).get("alternative"):
        seen: set[str] = set()
        for r in comp.get("rows") or []:
            alt = r.get("alternative")
            if not alt or alt.get("model_code") in seen or S.has_ref(s, alt.get("product_ref"), alt.get("model_code")):
                continue
            seen.add(alt.get("model_code") or "")
            p = await ops.resolve_product(alt.get("product_ref") or alt.get("model_code") or "", source="requirements", role="alternative")
            if p:
                alt_products.append(p)
    rules = [{**(r.get("parsed") or {})} for r in comp.get("rows") or [] if r.get("kind") != "procedural"]
    keys = set(C.requirement_items_to_item_keys(rules))
    tmp = copy.deepcopy(s)
    for p in alt_products:
        p["ord"] = len(tmp.get("products") or [])
        tmp.setdefault("products", []).append(p)
    await ops.compute_preview(tmp)

    def fn(x: dict[str, Any]) -> None:
        for p in alt_products:
            if not S.has_ref(x, p.get("ref"), p.get("model_code")):
                p["ord"] = len(x.get("products") or [])
                x.setdefault("products", []).append(p)
        x["preview"] = {**(x.get("preview") or {}), **(tmp.get("preview") or {})}
        for it in x.get("items") or []:
            if it["key"] in keys and not it.get("checked"):
                it["checked"] = True
                it["prechecked_by"] = "requirement"
        if not x.get("title_confirmed"):
            x["title"] = T.suggested_title(x)
            x["title_confirmed"] = True
        x["step"] = 2
        S.recompute_kind(x)
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await ops.publish(saved)
    return await doc(saved)
