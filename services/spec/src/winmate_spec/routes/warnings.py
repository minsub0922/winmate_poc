"""경고 · 재확인 · 카탈로그 · 생애주기 표(06-spec §6.9, 결정 반영 §4.17.3)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, Query, Response
from winmate_common.errors import ApiError

from .. import config, generate, ops, repo
from .. import sheet as S
from ..api_support import check_if_match, doc, enqueue, ensure_no_run, load
from ..catalog import catalog
from ..models import CatalogStatus, JobAccepted, LifecycleEntry, LifecycleList, SheetDoc, Warning, WarningPatch, WarningsView
from ..rules import text as T
from ..rules import warnings as W

router = APIRouter(prefix="/v1", tags=["warnings"])

NAV_ONLY = {"find_other", "upload_datasheet", "view"}


def _catalog_date(s: dict[str, Any], st: dict[str, Any] | None) -> str | None:
    det = (st or {}).get("detected_at")
    dt = config.parse_iso(det)
    if not dt:
        return None
    d = dt.astimezone(config.KST)
    return f"{d.month}월 {d.day}일"


@router.get("/sheets/{sheet_id}/warnings", response_model=WarningsView)
async def list_warnings(sheet_id: str, status: str = Query("open", description="open = 열린(결정 포함) 경고")) -> dict[str, Any]:
    """SP3W — 카드(번호 = 종류 → 행 → 열) · 필터 수 · 결정 수 · 에이전트 문장 · 표 제목 · 바닥."""
    s = await load(sheet_id)
    v = S.warnings_view(s)
    ws = S.warning_numbers(s)
    st = await repo.aget("catalog_state", catalog().adapter)
    products = {p["id"]: p for p in s.get("products") or []}
    agent = W.agent_text(ws, products, catalog_date=_catalog_date(s, st))
    decided = len([w for w in ws if w.get("decision")])
    ver = (s.get("catalog") or {}).get("version") or ""
    footer = f"출처: 사내 제품 카탈로그 {ver} 대조 · 시트 생성 {T.kst_date(s.get('generated_at'))}"
    return {"items": v["items"], "counts": v["counts"], "decided": decided, "total": len(ws), "agent_text": agent,
            "table_title": T.table_title(s, "ko"), "footer": footer, "user_text": s.get("user_text")}


@router.patch("/sheets/{sheet_id}/warnings/{warning_id}", response_model=Warning)
async def decide_warning(sheet_id: str, warning_id: str, body: WarningPatch) -> dict[str, Any]:
    """카드의 선택(라디오 · 칩 · 버튼)을 저장 — 반영은 `선택한 대로 반영`(warnings:apply). 이동만 하는 버튼은 저장하지 않는다."""
    await load(sheet_id)
    out: dict[str, Any] = {}

    def fn(x: dict[str, Any]) -> None:
        w = next((w for w in x.get("warnings") or [] if w["id"] == warning_id), None)
        if w is None or w.get("status") not in ("open", "decided"):
            raise ApiError(404, "NOT_FOUND", "열린 경고를 찾을 수 없어요.")
        if not any(o["key"] == body.option_key for o in w.get("options") or []):
            raise ApiError(422, "VALIDATION_FAILED", "고를 수 없는 선택이에요.", {"option_key": body.option_key})
        if body.option_key not in NAV_ONLY:
            w["decision"] = {"option_key": body.option_key, "at": config.now_iso()}
            w["status"] = "decided"
        S.refresh_status(x, x["id"])
        S.warning_numbers(x)
        out.update(w)

    await repo.amutate("sheets", sheet_id, fn)
    return {**out, "tag": S.WARNING_TAG.get(out["kind"], out["kind"])}


def _apply_one(x: dict[str, Any], w: dict[str, Any], replaced: list[str]) -> None:
    key = (w.get("decision") or {}).get("option_key")
    kind = w["kind"]
    pid = w.get("product_id")
    dismissed = x.setdefault("dismissed_fingerprints", [])
    if kind in ("discontinued", "not_in_catalog"):
        p = next((p for p in x.get("products") or [] if p["id"] == pid), None)
        if p is None:
            w["status"] = "applied"
            return
        if key == "keep_existing":
            p["role"] = "existing"
            w["status"] = "applied"
        elif key == "remove":
            x["products"] = [q for q in x.get("products") or [] if q["id"] != pid]
            x["cells"] = {k: v for k, v in (x.get("cells") or {}).items() if not k.endswith("|" + pid)}
            x["checks"] = [c for c in x.get("checks") or [] if c.get("product_id") != pid]
            for o in x.get("warnings") or []:
                if o.get("product_id") == pid and o is not w and o.get("status") in ("open", "decided"):
                    o["status"] = "applied"
            S.renumber_products(x)
            S.recompute_kind(x)
            w["status"] = "applied"
        elif key == "replace" and w.get("replacement"):
            replaced.append(pid or "")
            w["status"] = "applied"
        return
    if kind in ("value_mismatch_source", "catalog_changed"):
        choice = next((c for c in (w.get("data") or {}).get("choices") or [] if c.get("key") == key), None)
        cell_key = S.ck(w.get("row_id") or "", pid or "")
        c = (x.get("cells") or {}).get(cell_key)
        if choice is not None and c is not None:
            changed = S_diff(c.get("value"), choice.get("value"))
            if changed or kind == "catalog_changed" and key == "latest":
                c["value"] = choice.get("value")
                c["sources"] = choice.get("sources") or c.get("sources") or []
                c["state"] = "ok"
                if kind == "catalog_changed" and key == "latest":
                    c["catalog_value"] = choice.get("value")
                    c["catalog_text"] = choice.get("value_text")
        if kind == "catalog_changed" and key == "prev":
            dismissed.append(w["fingerprint"])    # 같은 바뀐 값으로 다시 묻지 않음(값이 또 바뀌면 새로)
        w["status"] = "applied"
        return
    if kind == "value_mismatch_proposal":
        if key == "keep":
            w["status"] = "dismissed"
            dismissed.append(w["fingerprint"])
        return   # `제안서에도 반영` 은 넘김 :ack 때 해결
    if kind == "requirement_unmet":
        if key == "ack":
            w["status"] = "dismissed"
            dismissed.append(w["fingerprint"])
        return


def S_diff(a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool:
    return (a or {}) != (b or {})


@router.post("/sheets/{sheet_id}/warnings:apply", response_model=SheetDoc,
             responses={202: {"model": SheetDoc, "description": "대체 모델로 바꾼 열을 다시 채우는 중(active_job)"}})
async def apply_warnings(sheet_id: str, response: Response, if_match: str | None = Header(None)) -> dict[str, Any]:
    """`선택한 대로 반영` — 결정이 있는 카드만 반영(한 번의 version +1). 대체 모델로 바꾸면 그 열만 다시 채움(202)."""
    s = await load(sheet_id)
    check_if_match(if_match, s)
    replaced: list[str] = []
    repl_targets: dict[str, str] = {}
    for w in S.warning_numbers(s):
        if (w.get("decision") or {}).get("option_key") == "replace" and w.get("replacement", {}).get("model_code"):
            repl_targets[w.get("product_id") or ""] = w["replacement"]["model_code"]
    if repl_targets:
        ensure_no_run(s)
    new_products: dict[str, dict[str, Any]] = {}
    for pid, code in repl_targets.items():
        np_ = await ops.resolve_product(code, source="request")
        if np_:
            new_products[pid] = np_

    def fn(x: dict[str, Any]) -> int:
        n = 0
        for w in list(x.get("warnings") or []):
            if w.get("status") != "decided" or not w.get("decision"):
                continue
            before = w["status"]
            _apply_one(x, w, replaced)
            if w["status"] != before:
                n += 1
        for pid in replaced:
            p = next((p for p in x.get("products") or [] if p["id"] == pid), None)
            np_ = new_products.get(pid)
            if p is None or np_ is None:
                continue
            if any(q.get("model_code") == np_.get("model_code") for q in x.get("products") or [] if q["id"] != pid):
                # 대체 모델이 이미 시트에 있으면 이 열은 뺀다(같은 모델 두 열 방지)
                x["products"] = [q for q in x["products"] if q["id"] != pid]
                x["cells"] = {k: v for k, v in (x.get("cells") or {}).items() if not k.endswith("|" + pid)}
                S.renumber_products(x)
                continue
            keep = {k: p[k] for k in ("id", "ord", "source")}
            p.clear()
            p.update({**np_, **keep, "role": "proposed"})
            x["cells"] = {k: v for k, v in (x.get("cells") or {}).items() if not k.endswith("|" + pid)}
            x["checks"] = [c for c in x.get("checks") or [] if c.get("product_id") != pid]
        if n:
            S.recompute_kind(x)
            S.bump_version(x, "warnings")
        S.refresh_status(x, x["id"])
        return n

    saved, n = await repo.amutate("sheets", sheet_id, fn)
    if n:
        await repo.aput("snapshots", f"{sheet_id}.v{saved['doc_version']}", S.snapshot_of(saved))
        from ..links import mark_links_changed
        await mark_links_changed(saved)
        saved = await repo.amust("sheets", sheet_id)
    fill = [pid for pid in replaced if any(p["id"] == pid for p in saved.get("products") or [])]
    if fill:
        await enqueue(sheet_id, "spec_generate", {"mode": "columns", "product_ids": fill}, title="대체 모델 열 다시 채우기",
                      before=generate.backup)
        saved = await repo.amust("sheets", sheet_id)
        response.status_code = 202
    await ops.publish(saved)
    return await doc(saved)


@router.post("/sheets/{sheet_id}/recheck", response_model=JobAccepted, status_code=202)
async def recheck(sheet_id: str) -> dict[str, Any]:
    """시트 하나 재확인(카탈로그 · 생애주기 · 연결 · 요구) — 값은 바꾸지 않고 경고만."""
    s = await load(sheet_id)
    ensure_no_run(s)
    if not s.get("generated_at"):
        raise ApiError(422, "NOT_GENERATED", "시트를 먼저 만들어 주세요.")
    job_id = await enqueue(sheet_id, "spec_recheck", {}, title="시트 재확인")
    return {"job_id": job_id, "status": "queued", "sheet_id": sheet_id}


@router.get("/catalog/status", response_model=CatalogStatus)
async def catalog_status() -> dict[str, Any]:
    cat = catalog()
    meta = await cat.meta()
    st = await repo.aget("catalog_state", cat.adapter) or {}
    sheets = await repo.alist("sheets")
    changed = len([s for s in sheets if not s.get("archived_at") and any(w.get("kind") == "catalog_changed" and w.get("status") in ("open", "decided")
                                                                         for w in s.get("warnings") or [])])
    return {"adapter": cat.adapter, "label": "사내 카탈로그", "source_label": "사내 제품 카탈로그", "version": meta.get("version") or "",
            "detected_at": st.get("detected_at"), "previous_version": st.get("previous_version"), "changed_sheets": changed}


@router.post("/catalog:recheck-all", response_model=JobAccepted, status_code=202)
async def recheck_all() -> dict[str, Any]:
    """전체 재확인(매일 06:00 KST 예약과 같은 일). 카탈로그 버전이 바뀌었으면 SP0 배너 · 알림."""
    from winmate_common.jobs import jobs
    job = await jobs().enqueue("spec", "spec_recheck", {"all": True}, title="사내 카탈로그 재확인", owner="system")
    return {"job_id": job.id, "status": "queued", "sheet_id": None}


@router.get("/lifecycle", response_model=LifecycleList, tags=["admin"])
async def list_lifecycle() -> dict[str, Any]:
    """생애주기 표(관리) — 단종 · 후속 모델(사내 카탈로그에 생애주기가 없을 때의 원천, §4.17.2)."""
    await repo.run(ops.seed_lifecycle)
    return {"items": sorted(await repo.alist("lifecycle"), key=lambda e: e.get("model_key") or "")}


@router.put("/lifecycle/{model_key}", response_model=LifecycleEntry, tags=["admin"])
async def put_lifecycle(model_key: str, body: LifecycleEntry) -> dict[str, Any]:
    await repo.run(ops.seed_lifecycle)
    data = body.model_dump()
    data["model_key"] = model_key
    saved = await repo.aput("lifecycle", model_key.upper(), data)
    return saved
