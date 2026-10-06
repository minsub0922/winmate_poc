"""생성 · 값 확인 · 데이터시트 · 셀 · 말로 수정 · 내보내기 · 공유(06-spec §6.6 · §6.7)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Response
from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import new_id
from winmate_common.jobs import jobs
from winmate_common.platform import file_meta

from .. import config, exporting, generate, ops, repo
from .. import sheet as S
from ..api_support import check_if_match, doc, enqueue, ensure_no_run, generate_running, load
from ..models import (
    CellPatch, CellPatchResult, CheckAnswerBody, CheckList, ChecksApply, ChecksApplyResult, DatasheetBody, ExportAccepted, ExportBody,
    ExportRecord, GenerateBody, JobAccepted, MessageBody, MessageQueued, ShareResult, SourceList, ValueCheck,
)
from ..rules import text as T
from ..rules.values import InvalidValue, parse_input

router = APIRouter(prefix="/v1", tags=["generate"])

DATASHEET_KINDS = ("pdf", "image", "docx", "xlsx", "text")


def _rows_would_change(s: dict[str, Any]) -> bool:
    import copy
    tmp = copy.deepcopy(s)
    before = {r["row_key"] for r in tmp.get("rows") or []}
    S.sync_rows(tmp)
    return before != {r["row_key"] for r in tmp.get("rows") or []}


# ── 생성 ─────────────────────────────────────────────────

@router.post("/sheets/{sheet_id}/generate", response_model=JobAccepted, status_code=202)
async def generate_sheet(sheet_id: str, body: GenerateBody | None = None) -> dict[str, Any]:
    """시트 생성(5단계 잡). rerender = 형식만 바뀜(kb 다시 읽지 않음) · columns = 바뀐 열만."""
    body = body or GenerateBody()
    s = await load(sheet_id)
    ensure_no_run(s)
    if not s.get("products"):
        raise ApiError(422, "NO_PRODUCTS", "제품을 하나 이상 넣어 주세요.")
    if not S.checked_keys(s) and not any(r["row_key"].startswith(("derived:", "template:")) for r in s.get("rows") or []):
        raise ApiError(422, "NO_ITEMS", "시트에 넣을 항목을 하나 이상 골라 주세요.")
    mode = body.mode
    pids = body.product_ids
    if mode in ("rerender", "columns") and not s.get("generated_at"):
        mode, pids = "full", None
    if mode == "rerender" and _rows_would_change(s):
        mode = "full"
    if mode == "columns":
        have = {k.split("|")[1] for k in (s.get("cells") or {})}
        pids = [p for p in (pids or [p["id"] for p in S.products_ordered(s) if p["id"] not in have])
                if any(x["id"] == p for x in s.get("products") or [])]
        if not pids:
            mode = "rerender"
    if mode == "full":
        pids = None

    def before(x: dict[str, Any]) -> None:
        generate.backup(x)
        x["pending_answers"] = None
        x.pop("gen_auto_defer", None)
        x["last_error"] = None
        if not x.get("title_confirmed"):
            x["title"] = T.suggested_title(x)
            x["title_confirmed"] = True
        if x.get("step", 1) < 2:
            x["step"] = 2

    title = f"{T.display_title(s)} 시트 생성"
    job_id = await enqueue(sheet_id, "spec_generate", {"mode": mode, "product_ids": pids, "auto_answer": bool(body.auto_answer)},
                           title=title, before=before)
    return {"job_id": job_id, "status": "queued", "sheet_id": sheet_id}


# ── 값 확인 ──────────────────────────────────────────────

def _check_out(chk: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in chk.items() if k not in ("data", "job_id")}


@router.get("/sheets/{sheet_id}/checks", response_model=CheckList)
async def list_checks(sheet_id: str) -> dict[str, Any]:
    s = await load(sheet_id)
    items = sorted(s.get("checks") or [], key=lambda c: c.get("n", 0))
    return {"items": [_check_out(c) for c in items], "open": len([c for c in items if c.get("status") == "open"])}


def _invalid(exc: InvalidValue, check_id: str | None = None) -> ApiError:
    details: dict[str, Any] = {"expected_unit": exc.expected_unit}
    if check_id:
        details["check_id"] = check_id
    return ApiError(422, "INVALID_VALUE", exc.message, details)


@router.post("/sheets/{sheet_id}/checks/{check_id}:answer", response_model=ValueCheck)
async def answer_check(sheet_id: str, check_id: str, body: CheckAnswerBody) -> dict[str, Any]:
    """답(칩 · 입력 · 다른 측정값)을 미리 저장 — 적용은 `답 반영하고 완성`(checks:apply). 숫자 · 단위가 틀리면 422 INVALID_VALUE."""
    s = await load(sheet_id)
    chk = next((c for c in s.get("checks") or [] if c["id"] == check_id), None)
    if chk is None:
        raise ApiError(404, "NOT_FOUND", "값 확인을 찾을 수 없어요.")
    if chk.get("status") == "answered":
        raise ApiError(409, "CHECK_CLOSED", "이미 반영한 값 확인이에요.")
    try:
        cleaned = generate.validate_answer(s, chk, body.model_dump(exclude_none=True))
    except InvalidValue as exc:
        raise _invalid(exc, check_id) from exc
    out: dict[str, Any] = {}

    def fn(x: dict[str, Any]) -> None:
        c = next((c for c in x.get("checks") or [] if c["id"] == check_id), None)
        if c is None:
            raise ApiError(404, "NOT_FOUND", "값 확인을 찾을 수 없어요.")
        c["answer"] = {k: v for k, v in cleaned.items() if k in ("option_key", "value_text", "alt_measure")} or None
        if cleaned.get("price") is not None:
            c.setdefault("data", {})["price_draft"] = cleaned["price"]
        out.update(c)

    await repo.amutate("sheets", sheet_id, fn)
    return _check_out(out)


def _after_route(sid: str, s: dict[str, Any]) -> str:
    if any(c.get("status") == "open" for c in s.get("checks") or []):
        return f"/spec/{sid}/generating" + (f"?job={s['last_job_id']}" if s.get("last_job_id") else "")
    if T.open_warnings(s):
        return f"/spec/{sid}/warnings"
    return f"/spec/{sid}"


@router.post("/sheets/{sheet_id}/checks:apply", response_model=ChecksApplyResult)
async def apply_checks(sheet_id: str, body: ChecksApply, if_match: str | None = Header(None)) -> dict[str, Any]:
    """`답 반영하고 완성` — 답은 반영, 답 없는 확인은 [확정 필요](눌린 칩이 있으면 그 값). 잡이 아직이면 저장해 두고 끝날 때 반영."""
    s = await load(sheet_id)
    running = generate_running(s)
    if not running:
        check_if_match(if_match, s)
    by_id = {c["id"]: c for c in s.get("checks") or []}
    cleaned: list[dict[str, Any]] = []
    for a in body.answers:
        chk = by_id.get(a.check_id)
        if chk is None:
            raise ApiError(404, "NOT_FOUND", f"값 확인을 찾을 수 없어요: {a.check_id}")
        if chk.get("status") != "open":
            continue
        ans = {k: v for k, v in a.model_dump(exclude_none=True).items() if k in ("option_key", "value_text", "alt_measure") and v}
        if not ans:
            continue
        try:
            c = generate.validate_answer(s, chk, ans)
        except InvalidValue as exc:
            raise _invalid(exc, a.check_id) from exc
        if c:
            cleaned.append({"check_id": a.check_id, **c})
    uid, _ = ops.user()
    if running:
        def hold(x: dict[str, Any]) -> None:
            x["pending_answers"] = cleaned
            for a in cleaned:
                c = next((c for c in x.get("checks") or [] if c["id"] == a["check_id"]), None)
                if c is not None:
                    c["answer"] = {k: v for k, v in a.items() if k in ("option_key", "value_text", "alt_measure")}

        saved, _ = await repo.amutate("sheets", sheet_id, hold)
        return {"sheet": await doc(saved), "next_route": f"/spec/{sheet_id}/generating?job={running['id']}", "pending_until_job_done": True}

    def fn(x: dict[str, Any]) -> bool:
        had_open = any(c.get("status") == "open" for c in x.get("checks") or [])
        generate.apply_answers(x, cleaned, by=uid, complete=True)
        if had_open:
            S.bump_version(x, "answers")
        S.refresh_status(x, x["id"])
        return had_open

    saved, changed = await repo.amutate("sheets", sheet_id, fn)
    if changed:
        await repo.aput("snapshots", f"{sheet_id}.v{saved['doc_version']}", S.snapshot_of(saved))
        from ..links import mark_links_changed
        await mark_links_changed(saved)
        saved = await repo.amust("sheets", sheet_id)
    await ops.publish(saved)
    return {"sheet": await doc(saved), "next_route": _after_route(sheet_id, saved), "pending_until_job_done": False}


@router.post("/sheets/{sheet_id}/checks:defer-all", response_model=ChecksApplyResult)
async def defer_all_checks(sheet_id: str) -> dict[str, Any]:
    """`모두 [확정 필요]로 두기` — 열린 확인 전부 deferred(셀 [확정 필요]). 생성 중이면 이후 생기는 확인도 미룬다."""
    s = await load(sheet_id)
    running = generate_running(s)
    uid, _ = ops.user()

    def fn(x: dict[str, Any]) -> None:
        for chk in x.get("checks") or []:
            if chk.get("status") == "open":
                generate.apply_answer(x, chk, {}, by=uid)
        if running:
            x["gen_auto_defer"] = True
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await ops.publish(saved)
    route = f"/spec/{sheet_id}/generating?job={running['id']}" if running else _after_route(sheet_id, saved)
    return {"sheet": await doc(saved), "next_route": route, "pending_until_job_done": bool(running)}


# ── 데이터시트 · 출처 ────────────────────────────────────

@router.post("/sheets/{sheet_id}/datasheets", response_model=JobAccepted, status_code=202)
async def add_datasheet(sheet_id: str, body: DatasheetBody) -> dict[str, Any]:
    """제품 데이터시트(사용자 자료 — confidential) → 빈 칸 채우기 · 다른 값은 확인/경고."""
    s = await load(sheet_id)
    p = next((x for x in s.get("products") or [] if x["id"] == body.product_id), None)
    if p is None:
        raise ApiError(404, "NOT_FOUND", "시트에 없는 제품이에요.")
    try:
        meta = await file_meta(body.file_id)
    except ApiError as exc:
        if exc.status == 404:
            raise ApiError(404, "NOT_FOUND", "파일을 찾지 못했어요.", {"file_id": body.file_id}) from exc
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", "파일 서비스에 연결하지 못했어요. 잠시 뒤 다시 시도해 주세요.") from exc
    if meta.get("kind") not in DATASHEET_KINDS:
        raise ApiError(422, "UNSUPPORTED_FILE", "PDF · 이미지 · DOCX · XLSX 데이터시트만 읽을 수 있어요.", {"kind": meta.get("kind")})
    ds = {"id": new_id("sds"), "product_id": p["id"], "file_id": body.file_id, "name": meta.get("name") or "데이터시트",
          "pages": meta.get("pages") or 0, "status": "queued", "created_at": config.now_iso()}
    job_id = await enqueue(sheet_id, "spec_datasheet", {"datasheet_id": ds["id"]}, title=f"{p['display_name']} 데이터시트 읽기",
                           set_active=False, before=lambda x: x.setdefault("datasheets", []).append(ds))
    return {"job_id": job_id, "status": "queued", "sheet_id": sheet_id}


@router.get("/sheets/{sheet_id}/cells/{row_id}/{product_id}/sources", response_model=SourceList)
async def cell_sources(sheet_id: str, row_id: str, product_id: str) -> dict[str, Any]:
    """`출처 보기` — 칸의 출처(출처끼리 다른 칸이면 후보 출처 전부)."""
    s = await load(sheet_id)
    c = (s.get("cells") or {}).get(S.ck(row_id, product_id))
    if c is None:
        raise ApiError(404, "NOT_FOUND", "칸을 찾을 수 없어요.")
    sources = list(c.get("sources") or [])
    chk = next((x for x in s.get("checks") or [] if x.get("row_id") == row_id and x.get("product_id") == product_id
                and x.get("kind") == "conflict"), None)
    if chk:
        for v in ((chk.get("data") or {}).get("values") or {}).values():
            for src in v.get("sources") or []:
                if src not in sources:
                    sources.append(src)
    return {"sources": sources}


# ── 셀 · 말로 수정 ───────────────────────────────────────

@router.patch("/sheets/{sheet_id}/cells/{row_id}/{product_id}", response_model=CellPatchResult)
async def patch_cell(sheet_id: str, row_id: str, product_id: str, body: CellPatch) -> dict[str, Any]:
    """셀 직접 고치기 → `edited`(출처 직접 입력, 고정) · 우위 다시 계산. 숫자 · 단위가 틀리면 422 INVALID_VALUE."""
    s = await load(sheet_id)
    row = next((r for r in s.get("rows") or [] if r["id"] == row_id), None)
    prod = next((p for p in s.get("products") or [] if p["id"] == product_id), None)
    if row is None or prod is None:
        raise ApiError(404, "NOT_FOUND", "칸을 찾을 수 없어요.")
    text = body.value_text.strip()
    if row["row_key"].startswith("derived:"):
        raise ApiError(422, "INVALID_VALUE", "계산한 행은 직접 고칠 수 없어요. 소비전력 · 운영 시간을 고치면 다시 계산돼요.", {"expected_unit": None})
    cur = ((s.get("cells") or {}).get(S.ck(row_id, product_id)) or {}).get("value")
    try:
        val = {"text": text} if row["row_key"].startswith("template:") else parse_input(row["row_key"], text, cur)
        if not text:
            raise InvalidValue(None, "값을 넣어 주세요.")
    except InvalidValue as exc:
        raise _invalid(exc) from exc
    uid, _ = ops.user()
    now = config.now_iso()

    def fn(x: dict[str, Any]) -> None:
        cells = x.setdefault("cells", {})
        key = S.ck(row_id, product_id)
        old = cells.get(key) or {}
        cells[key] = {**old, "value": val, "state": "edited", "edited_by": uid, "edited_at": now,
                      "sources": [{"kind": "user", "label": "직접 입력", "version_or_date": now[:10], "tier": "고정", "ref": uid}]}
        cells[key].pop("flag_text", None)
        for chk in x.get("checks") or []:
            if chk.get("row_id") == row_id and chk.get("product_id") == product_id and chk.get("status") in ("open", "deferred"):
                chk["status"] = "answered"
                chk["answer"] = {"value_text": text}
        for r in x.get("rows") or []:
            if r["row_key"] == "derived:annual_energy_cost" and row["row_key"] in ("power", "operation_hours"):
                generate._derive_row(x, r, (r.get("derived") or {}).get("price") or config.electricity_price())
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    from ..links import mark_links_changed
    await mark_links_changed(saved)
    saved = await repo.amust("sheets", sheet_id)
    await ops.publish(saved)
    f = S.fmt_of(saved)
    r = next(r for r in saved["rows"] if r["id"] == row_id)
    p = next(p for p in saved["products"] if p["id"] == product_id)
    wmap, _ = S.cell_warning_map(saved)
    cell = S.render_cell(saved, r, p, f, win=S.row_wins(saved, r).get(product_id, False), wmap=wmap, checks_by_cell={})
    table = S.build_table(saved) or {}
    return {"cell": cell, "win_rows": table.get("win_rows", 0)}


@router.post("/sheets/{sheet_id}/messages", response_model=MessageQueued, status_code=202,
             responses={200: {"model": MessageQueued, "description": "생성 중 — 조종 메모로 들어감"}})
async def post_message(sheet_id: str, body: MessageBody, response: Response) -> dict[str, Any]:
    """말로 수정(spec_revise). 생성 중이면 조종 메모(`시트 구성` 전에 반영, 200). 결과는 잡 result 의 applied_ops · reply · navigate."""
    s = await load(sheet_id)
    text = body.text.strip()
    running = generate_running(s)
    if running:
        await jobs().add_memo(running["id"], text)
        await repo.amutate("sheets", sheet_id, lambda x: x.update({"user_text": text}))
        response.status_code = 200
        return {"queued": True, "job_id": running["id"], "memo": True}
    if body.context == "find":
        def before(x: dict[str, Any]) -> None:
            from ..finder import empty_state
            st = x.get("finder") or empty_state()
            st["status"] = "running"
            x["finder"] = st
            x["user_text"] = text

        job_id = await enqueue(sheet_id, "spec_find", {"text": text}, title="조건으로 모델 찾기", before=before)
        return {"queued": True, "job_id": job_id, "memo": False}
    ensure_no_run(s)
    ctx = "result" if body.context == "requirements" else body.context
    job_id = await enqueue(sheet_id, "spec_revise", {"text": text, "context": ctx}, title="말로 수정",
                           before=lambda x: x.update({"user_text": text}))
    return {"queued": True, "job_id": job_id, "memo": False}


# ── 내보내기 · 공유 ──────────────────────────────────────

@router.post("/sheets/{sheet_id}/exports", response_model=ExportAccepted, status_code=202)
async def create_export(sheet_id: str, body: ExportBody) -> dict[str, Any]:
    """XLSX · PDF · PPT(export 서비스가 만듦). overrides 는 이 내보내기에만."""
    s = await load(sheet_id)
    if not s.get("generated_at") or not s.get("cells"):
        raise ApiError(422, "NOT_GENERATED", "시트를 먼저 만들어 주세요.")
    ov = body.overrides.model_dump(exclude_none=True) if body.overrides else {}
    opts = body.options.model_dump() if body.options else None
    filename = exporting.filename_for(s, body.format, body.filename or ov.get("filename_base"), ov)
    rec = exporting.new_record(sheet_id, s.get("doc_version", 0), body.format, {"overrides": ov, "options": opts}, filename)
    await repo.aput("exports", rec["id"], rec)
    job = await jobs().enqueue("spec", "spec_export", {"sheet_id": sheet_id, "export_id": rec["id"]}, title=f"{filename} 내보내기",
                               ref=sheet_id, project_id=s.get("project_id"))
    await repo.amutate("exports", rec["id"], lambda r: r.update({"job_id": job.id}), what="내보내기")
    return {"job_id": job.id, "status": "queued", "export_id": rec["id"]}


@router.get("/sheets/{sheet_id}/exports/{export_id}", response_model=ExportRecord)
async def get_export(sheet_id: str, export_id: str) -> dict[str, Any]:
    rec = await repo.aget("exports", export_id)
    if rec is None or rec.get("sheet_id") != sheet_id:
        raise ApiError(404, "NOT_FOUND", "내보내기를 찾을 수 없어요.")
    return exporting.public(rec)


@router.post("/sheets/{sheet_id}/share", response_model=ShareResult)
async def share_sheet(sheet_id: str) -> dict[str, Any]:
    """`링크로 공유` — workspace 공유 링크(보기 전용)."""
    s = await load(sheet_id)
    try:
        res = await ServiceClient("workspace").post("/v1/share-links", json={"target": sheet_id, "route": f"/spec/{sheet_id}",
                                                                          "title": T.display_title(s)})
    except ApiError as exc:
        raise ApiError(503, "UPSTREAM_UNAVAILABLE", "공유 링크를 만들지 못했어요. 잠시 뒤 다시 시도해 주세요.") from exc
    return {"share_url": res.get("url") or ""}
