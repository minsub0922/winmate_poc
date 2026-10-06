"""시트 작업 · 제품 · 항목 · 형식 · 양식 · 기본값(06-spec §6.1 · §6.2 · §6.5)."""
from __future__ import annotations

import base64
import copy
from typing import Any, Literal

from fastapi import APIRouter, Query, Response
from winmate_common.errors import ApiError
from winmate_common.ids import new_id
from winmate_common.platform import file_meta

from .. import config, ops, repo
from .. import sheet as S
from .. import template as TPL
from ..api_support import doc, doc_of, enqueue, ensure_daily_schedule, ensure_no_run, load, preferences
from ..catalog import catalog
from ..models import (
    AddProducts, AddProductsResult, CloneBody, ComboList, CreateSheet, DiffItems, FormatPreview, FormatPreviewBody, FormatSettings,
    FormatSettingsPatch, ItemCatalog, ItemsPut, JobAccepted, PatchProduct, PatchSheet, Preferences, ProductRefList, SheetDoc, SheetList,
    TemplateBody, VersionList,
)
from ..rules import items as itemcat
from ..rules import text as T
from ..rules.package import display_table
from ..rules.values import Fmt

router = APIRouter(prefix="/v1", tags=["sheets"])

TAB_OF = {"draft": "draft", "run": "draft", "check": "check", "warn": "check", "done": "done"}
STATUS_ORDER = {"check": 0, "warn": 1, "run": 2, "draft": 3, "done": 4}


# ── 목록(SP0) ────────────────────────────────────────────

def _list_item(s: dict[str, Any], links: list[dict[str, Any]]) -> dict[str, Any]:
    sid = s["id"]
    ui, text, route = T.status_of(s, sid)
    ps = S.products_ordered(s)
    lk = sorted(links, key=S.touched, reverse=True)
    prop = lk[0]["proposal_title"] if lk else ((s.get("target_proposal") or {}).get("title") or "연결 안 됨")
    return {"id": sid, "title": T.display_title(s), "type_icon": T.type_icon(s), "sub_line": T.sub_line(s),
            "model_chips": [p["display_name"] for p in ps[:2]], "more_models": max(0, len(ps) - 2), "output_label": T.output_label(s),
            "ui_status": ui, "status_text": text, "proposal_label": prop, "when_label": T.when_label(S.touched(s)),
            "resume_route": route, "updated_at": S.touched(s)}


def _search_blob(s: dict[str, Any], item: dict[str, Any]) -> str:
    parts = [item["title"], s.get("customer_name") or "", item["proposal_label"]]
    for p in s.get("products") or []:
        parts += [p.get("display_name") or "", p.get("model_code") or "", p.get("bubble_label") or ""]
    return " ".join(parts).lower()


@router.get("/sheets", response_model=SheetList)
async def list_sheets(limit: int = Query(50, ge=1, le=200), cursor: str | None = None,
                      tab: Literal["all", "draft", "check", "done"] = "all", q: str | None = None, linked: bool = False,
                      sort: Literal["updated_desc", "title", "status"] = "updated_desc", since_days: int = Query(30, ge=0, le=3650),
                      archived: bool = False) -> dict[str, Any]:
    """작업 목록. 탭 숫자는 검색 · 거르기 전 기준. 기본 기간 최근 30일(검색하면 기간 무시)."""
    await ensure_daily_schedule()
    uid, _ = ops.user()
    sheets = await repo.alist("sheets", {"owner_id": uid})
    all_links = await repo.alist("links")
    by_sheet: dict[str, list[dict[str, Any]]] = {}
    for lk in all_links:
        by_sheet.setdefault(lk["sheet_id"], []).append(lk)
    archived_count = len([s for s in sheets if s.get("archived_at")])
    base = [s for s in sheets if bool(s.get("archived_at")) == archived]
    cutoff = config.now().timestamp() - since_days * 86400 if since_days else None
    if cutoff and not q and not archived:
        base = [s for s in base if (config.parse_iso(S.touched(s)) or config.now()).timestamp() >= cutoff]
    items = [(s, _list_item(s, by_sheet.get(s["id"], []))) for s in base]
    counts = {"all": len(items), "draft": 0, "check": 0, "done": 0}
    for _, it in items:
        counts[TAB_OF[it["ui_status"]]] += 1
    rows = items
    if tab != "all":
        rows = [(s, it) for s, it in rows if TAB_OF[it["ui_status"]] == tab]
    if linked:
        rows = [(s, it) for s, it in rows if it["proposal_label"] != "연결 안 됨"]
    if q:
        ql = q.strip().lower()
        rows = [(s, it) for s, it in rows if ql in _search_blob(s, it)]
    if sort == "title":
        rows.sort(key=lambda x: x[1]["title"])
    elif sort == "status":
        rows.sort(key=lambda x: (STATUS_ORDER.get(x[1]["ui_status"], 9), x[1]["updated_at"]), reverse=False)
    else:
        rows.sort(key=lambda x: x[1]["updated_at"], reverse=True)
    offset = 0
    if cursor:
        try:
            offset = int(base64.urlsafe_b64decode(cursor.encode()).decode())
        except Exception:  # noqa: BLE001
            offset = 0
    page = rows[offset: offset + limit]
    nxt = base64.urlsafe_b64encode(str(offset + limit).encode()).decode() if len(rows) > offset + limit else None
    # 카탈로그 갱신 배너(열린 catalog_changed 경고가 있는 시트 수)
    changed = [s for s in sheets if not s.get("archived_at") and any(w.get("kind") == "catalog_changed" and w.get("status") in ("open", "decided")
                                                                    for w in s.get("warnings") or [])]
    banner = None
    if changed:
        st = await repo.aget("catalog_state", catalog().adapter)
        dates = [w.get("detected_at") for s in changed for w in s.get("warnings") or [] if w.get("kind") == "catalog_changed"]
        det = (st or {}).get("detected_at") or (max(dates) if dates else None)
        latest = max(changed, key=S.touched)
        banner = {"date": T.kst_date(det), "sheets": len(changed), "text": T.banner_text(det, len(changed)),
                  "route": f"/spec/{latest['id']}/warnings"}
    return {"items": [it for _, it in page], "next_cursor": nxt, "counts": counts, "archived_count": archived_count, "total": len(rows),
            "banner": banner}


# ── 만들기 · 읽기 · 고치기 ─────────────────────────────────

async def _add_tokens(s: dict[str, Any], tokens: list[str], *, source: str, role: str | None) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    """토큰을 해소해 시트에 넣을 제품 목록. 돌려줌: (넣은 ref, 건너뜀, 새 제품)."""
    added, skipped, new = [], [], []
    existing = list(s.get("products") or [])
    for t in tokens:
        t = (t or "").strip()
        if not t:
            continue
        p = await ops.resolve_product(t, source=source, role=role or "proposed")
        if p is None:
            skipped.append({"ref": t, "reason": "unresolved"})
            continue
        if any(x.get("ref") == p["ref"] or (p.get("model_code") and x.get("model_code") == p["model_code"]) or
               (p.get("custom") and x.get("custom") and x.get("display_name") == p["display_name"]) for x in existing + new):
            skipped.append({"ref": t, "reason": "duplicate"})
            continue
        if len(existing) + len(new) >= config.PRODUCT_LIMIT:
            skipped.append({"ref": t, "reason": "limit"})
            continue
        new.append(p)
        added.append(t)
    return added, skipped, new


@router.post("/sheets", response_model=SheetDoc, status_code=201)
async def create_sheet(body: CreateSheet) -> dict[str, Any]:
    """새 작업. `purpose: proposal`(제안서 딸깍 P2)이면 기본 항목으로 바로 생성(auto_answer)까지 시작한다."""
    uid, uname = ops.user()
    prefs = await preferences(uid)
    origin = body.origin.model_dump(by_alias=True, exclude_none=True) if body.origin else None
    tp = body.target_proposal.model_dump() if body.target_proposal else None
    rq_ref = body.rq_ref
    start = body.start
    if body.purpose == "proposal":
        start = "link"
        origin = origin or {"from": "proposal", "ref": (tp or {}).get("id")}
    s = S.new_sheet(owner_id=uid, owner_name=uname, start=start, prefs=prefs, project_id=body.project_id, customer_name=body.customer_name,
                    origin=origin, target_proposal=tp, rq_ref=rq_ref)
    sid = new_id("sp")
    s["id"] = sid
    tokens = list(body.products or []) + list(body.models or [])
    source = {"explorer": "explorer", "link": "link", "find": "find", "requirements": "requirements"}.get(start, "input")
    if len(tokens) > config.PRODUCT_LIMIT:
        raise ApiError(422, "PRODUCT_LIMIT", "한 시트에 8개까지 비교할 수 있어요.", {"limit": config.PRODUCT_LIMIT})
    _, _, new = await _add_tokens(s, tokens, source=source, role=body.role)
    for i, p in enumerate(new):
        p["ord"] = i
    s["products"] = new
    S.recompute_kind(s)
    if start == "find":
        from ..finder import empty_state
        s["finder"] = empty_state(body.query_text)
    await ops.compute_preview(s)
    await _precheck_requirements(s)
    S.refresh_status(s, sid)
    saved = await repo.aput("sheets", sid, s)
    if body.purpose == "proposal" and new:
        def prep(x: dict[str, Any]) -> None:
            from ..generate import backup
            x["title"] = T.suggested_title(x)
            x["title_confirmed"] = True
            x["step"] = 2
            backup(x)
        await enqueue(sid, "spec_generate", {"mode": "full", "auto_answer": True}, title=f"{T.suggested_title(s)} 시트 생성", before=prep)
        saved = await repo.amust("sheets", sid)
    await ops.publish(saved)
    return await doc(saved)


async def _precheck_requirements(s: dict[str, Any]) -> None:
    """연결된 요구사항 정의서의 스펙성 요구 → 관련 항목 미리 체크(§4.7.2)."""
    if not s.get("project_id") and not s.get("rq_ref"):
        return
    items, ref = await ops.requirement_items(s)
    rules = await ops.requirement_rules_from_definition(items)
    from ..rules.compliance import requirement_items_to_item_keys
    keys = requirement_items_to_item_keys(rules)
    for it in s.get("items") or []:
        if it["key"] in keys and not it.get("checked"):
            it["checked"] = True
            it["prechecked_by"] = "requirement"
    if ref:
        s["rq_ref"] = ref


@router.get("/sheets/{sheet_id}", response_model=SheetDoc)
async def get_sheet(sheet_id: str) -> dict[str, Any]:
    return await doc_of(sheet_id)


@router.patch("/sheets/{sheet_id}", response_model=SheetDoc)
async def patch_sheet(sheet_id: str, body: PatchSheet) -> dict[str, Any]:
    """제목 · 고객사 · 단계(1 · 2) · 대상 제안서. step 2 로 넘어가면 제목을 확정한다(SP1 큰 버튼)."""
    await load(sheet_id)

    def fn(s: dict[str, Any]) -> None:
        if body.title is not None and body.title.strip():
            s["title"] = body.title.strip()
            s["title_confirmed"] = True
        if body.customer_name is not None:
            s["customer_name"] = body.customer_name.strip() or None
        if body.step is not None:
            if body.step == 2 and not s.get("products"):
                raise ApiError(422, "NO_PRODUCTS", "제품을 하나 이상 넣어 주세요.")
            if body.step == 2 and not s.get("title_confirmed"):
                s["title"] = T.suggested_title(s)
                s["title_confirmed"] = True
            s["step"] = body.step
        if body.confirm_title and not s.get("title_confirmed"):
            s["title"] = T.suggested_title(s)
            s["title_confirmed"] = True
        if body.target_proposal is not None:
            s["target_proposal"] = body.target_proposal.model_dump()
        if body.clear_target_proposal:
            s["target_proposal"] = None
        S.refresh_status(s, s["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await ops.publish(saved)
    return await doc(saved)


@router.post("/sheets/{sheet_id}:clone", response_model=SheetDoc, status_code=201)
async def clone_sheet(sheet_id: str, body: CloneBody | None = None) -> dict[str, Any]:
    """복제해서 새 버전 — 제품 · 항목 · 형식 · 행 편집(순서 · 강조 · 숨김 · 각주 메모)만. 고객사 · 연결 · 경고 · 값 확인 · 내부 메모는 비움."""
    src = await load(sheet_id)
    uid, uname = ops.user()
    s = S.new_sheet(owner_id=uid, owner_name=uname, start="clone", prefs=None, project_id=src.get("project_id"),
                    customer_name=(body.customer_name if body else None), origin={"from": "clone", "ref": sheet_id})
    sid = new_id("sp")
    s["id"] = sid
    pid_map = {}
    for p in S.products_ordered(src):
        np_ = copy.deepcopy(p)
        np_["id"] = new_id("spp")
        np_["source"] = "clone"
        pid_map[p["id"]] = np_["id"]
        s["products"].append(np_)
    s["items"] = copy.deepcopy(src.get("items") or [])
    s["format"] = copy.deepcopy(src.get("format") or S.SYSTEM_FORMAT)
    s["format_confirmed"] = bool(src.get("format_confirmed"))
    s["options"] = copy.deepcopy(src.get("options") or {"highlight_wins": True})
    s["layout"] = src.get("layout", "compare")
    for r in S.rows_ordered(src):
        nr = copy.deepcopy(r)
        nr["id"] = new_id("srw")
        if (nr.get("memo") or {}).get("mode") == "internal":
            nr["memo"] = None
        s["rows"].append(nr)
    s["clone_of_title"] = T.display_title(src)
    S.recompute_kind(s)
    await ops.compute_preview(s)
    S.refresh_status(s, sid)
    saved = await repo.aput("sheets", sid, s)
    await ops.publish(saved)
    return await doc(saved)


@router.post("/sheets/{sheet_id}:archive", status_code=204)
async def archive_sheet(sheet_id: str) -> Response:
    await load(sheet_id)
    saved, _ = await repo.amutate("sheets", sheet_id, lambda s: s.update({"archived_at": config.now_iso(), "archived": True}))
    await ops.publish(saved)
    return Response(status_code=204)


@router.post("/sheets/{sheet_id}:unarchive", status_code=204)
async def unarchive_sheet(sheet_id: str) -> Response:
    await load(sheet_id)
    saved, _ = await repo.amutate("sheets", sheet_id, lambda s: s.update({"archived_at": None, "archived": False}))
    await ops.publish(saved)
    return Response(status_code=204)


@router.post("/sheets/{sheet_id}:save", response_model=SheetDoc)
async def save_sheet(sheet_id: str) -> dict[str, Any]:
    """저장 — version +1 · saved_at · 상태 다시 계산 · workspace."""
    await load(sheet_id)

    def fn(s: dict[str, Any]) -> None:
        S.bump_version(s, "save")
        s["saved_at"] = config.now_iso()
        S.refresh_status(s, s["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await repo.aput("snapshots", f"{sheet_id}.v{saved['doc_version']}", S.snapshot_of(saved))
    from ..links import mark_links_changed
    await mark_links_changed(saved)
    saved = await repo.amust("sheets", sheet_id)
    await ops.publish(saved)
    return await doc(saved)


@router.get("/sheets/{sheet_id}/versions", response_model=VersionList)
async def list_versions(sheet_id: str) -> dict[str, Any]:
    s = await load(sheet_id)
    return {"items": [{"version": v["version"], "reason": v["reason"], "created_at": v["created_at"]} for v in reversed(s.get("versions") or [])]}


@router.post("/sheets/{sheet_id}/versions/{n}/restore", response_model=SheetDoc)
async def restore_version(sheet_id: str, n: int) -> dict[str, Any]:
    await load(sheet_id)
    snap = await repo.aget("snapshots", f"{sheet_id}.v{n}")
    if snap is None:
        raise ApiError(404, "VERSION_NOT_FOUND", f"{n}판을 찾을 수 없어요.")

    def fn(s: dict[str, Any]) -> None:
        for k, v in snap.items():
            if k not in ("id", "version", "created_at", "updated_at", "touched_at", "created_at_app"):
                s[k] = copy.deepcopy(v)
        S.bump_version(s, "restore")
        S.refresh_status(s, s["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await repo.aput("snapshots", f"{sheet_id}.v{saved['doc_version']}", S.snapshot_of(saved))
    await ops.publish(saved)
    return await doc(saved)


# ── 제품 ─────────────────────────────────────────────────

@router.post("/sheets/{sheet_id}/products", response_model=AddProductsResult)
async def add_products(sheet_id: str, body: AddProducts) -> dict[str, Any]:
    """제품 추가(제품 입력창 · 제품 탐색 팝오버 onAdd · 조합 칩). 같은 모델은 넣지 않는다. 8개 넘으면 422 PRODUCT_LIMIT."""
    s = await load(sheet_id)
    source = body.source or "input"
    added, skipped, new = await _add_tokens(s, body.refs, source=source, role=body.role)
    if any(x["reason"] == "limit" for x in skipped) and not new:
        raise ApiError(422, "PRODUCT_LIMIT", "한 시트에 8개까지 비교할 수 있어요.", {"limit": config.PRODUCT_LIMIT})
    if new:
        tmp = copy.deepcopy(s)
        for p in new:
            p["ord"] = len(tmp["products"])
            tmp["products"].append(p)
        await ops.compute_preview(tmp)

        def fn(x: dict[str, Any]) -> None:
            for p in new:
                if not S.has_ref(x, p["ref"], p.get("model_code")):
                    p["ord"] = len(x.get("products") or [])
                    x.setdefault("products", []).append(p)
            x["preview"] = {**(x.get("preview") or {}), **(tmp.get("preview") or {})}
            S.recompute_kind(x)
            S.refresh_status(x, x["id"])

        s, _ = await repo.amutate("sheets", sheet_id, fn)
        await ops.publish(s)
    if any(x["reason"] == "limit" for x in skipped):
        pass
    return {"added": added, "skipped": skipped, "sheet": await doc(s)}


@router.delete("/sheets/{sheet_id}/products/{product_id}", response_model=SheetDoc)
async def remove_product(sheet_id: str, product_id: str) -> dict[str, Any]:
    await load(sheet_id)

    def fn(s: dict[str, Any]) -> None:
        if not any(p["id"] == product_id for p in s.get("products") or []):
            raise ApiError(404, "NOT_FOUND", "시트에 없는 제품이에요.")
        s["products"] = [p for p in s.get("products") or [] if p["id"] != product_id]
        s["cells"] = {k: v for k, v in (s.get("cells") or {}).items() if not k.endswith("|" + product_id)}
        s["checks"] = [c for c in s.get("checks") or [] if c.get("product_id") != product_id]
        s["warnings"] = [w for w in s.get("warnings") or [] if w.get("product_id") != product_id]
        (s.get("preview") or {}).pop(product_id, None)
        S.renumber_products(s)
        S.recompute_kind(s)
        S.refresh_status(s, s["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await ops.publish(saved)
    return await doc(saved)


@router.patch("/sheets/{sheet_id}/products/{product_id}", response_model=SheetDoc)
async def patch_product(sheet_id: str, product_id: str, body: PatchProduct) -> dict[str, Any]:
    """역할 · 열 이름 · 순서 · 모델 바꾸기(대체 모델로 바꾸기 → 그 열만 다시 채움, 202 잡은 active_job 으로)."""
    s = await load(sheet_id)
    newp = None
    if body.model_ref:
        ensure_no_run(s)
        newp = await ops.resolve_product(body.model_ref, source="request")

    def fn(x: dict[str, Any]) -> None:
        p = next((p for p in x.get("products") or [] if p["id"] == product_id), None)
        if p is None:
            raise ApiError(404, "NOT_FOUND", "시트에 없는 제품이에요.")
        if body.role:
            p["role"] = body.role
        if body.column_label is not None:
            p["column_label"] = body.column_label.strip() or None
        if body.ord is not None:
            ps = [q for q in S.products_ordered(x) if q["id"] != product_id]
            ps.insert(max(0, min(body.ord, len(ps))), p)
            for i, q in enumerate(ps):
                q["ord"] = i
        if newp:
            keep = {k: p[k] for k in ("id", "ord", "role", "source")}
            p.clear()
            p.update({**newp, **keep, "role": "proposed" if keep["role"] == "existing" else keep["role"]})
            x["cells"] = {k: v for k, v in (x.get("cells") or {}).items() if not k.endswith("|" + product_id)}
            x["warnings"] = [w for w in x.get("warnings") or [] if w.get("product_id") != product_id]
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    if newp and saved.get("generated_at"):
        from ..generate import backup
        await enqueue(sheet_id, "spec_generate", {"mode": "columns", "product_ids": [product_id]}, title="열 다시 채우기", before=backup)
        saved = await repo.amust("sheets", sheet_id)
    await ops.publish(saved)
    return await doc(saved)


@router.get("/sheets/{sheet_id}/products", response_model=ProductRefList)
async def list_products(sheet_id: str) -> dict[str, Any]:
    """다른 기능으로 넘길 모델 ref(§3.7)."""
    s = await load(sheet_id)
    return {"items": [{k: p.get(k) for k in ("ref", "model_code", "kb_model_id", "family_id", "display_name", "role")} for p in S.products_ordered(s)]}


@router.get("/combos", response_model=ComboList)
async def list_combos(category: str = "signage") -> dict[str, Any]:
    """자주 비교하는 조합 — 모든 모델이 지금 카탈로그에서 해소될 때만(최대 3)."""
    cfg = config.combos_config()
    cat = catalog()
    out = []
    for c in cfg.get("combos") or []:
        codes = []
        ok = True
        for m in c.get("models") or []:
            code = await cat.resolve(m)
            if not code:
                ok = False
                break
            codes.append(code)
        if ok and codes:
            specs = await cat.specs(codes)
            refs = [f"kb:model:{specs[x]['kb_model_id']}" if specs.get(x, {}).get("kb_model_id") else x for x in codes]
            out.append({"label": c["label"], "model_codes": codes, "refs": refs})
        if len(out) >= 3:
            break
    return {"items": out}


# ── 항목 · 형식 ───────────────────────────────────────────

@router.get("/item-catalog", response_model=ItemCatalog)
async def item_catalog(category: str = "signage") -> dict[str, Any]:
    cfg = config.items_config(category)
    return {"category": cfg.get("category") or category,
            "items": [{"key": it["key"], "label": it["label"], "label_en_lines": [ln for r in it.get("rows") or [] for ln in r.get("en_lines") or []],
                       "default_checked": bool(it.get("default")), "group": it.get("group") or "", "rows": it.get("rows") or []}
                      for it in cfg.get("items") or []]}


@router.put("/sheets/{sheet_id}/items", response_model=SheetDoc)
async def put_items(sheet_id: str, body: ItemsPut) -> dict[str, Any]:
    await load(sheet_id)

    def fn(s: dict[str, Any]) -> None:
        if body.items is not None:
            want = {str(i.get("key")): bool(i.get("checked")) for i in body.items if i.get("key")}
            for it in s.get("items") or []:
                if it["key"] in want and want[it["key"]] != it.get("checked"):
                    it["checked"] = want[it["key"]]
                    it["prechecked_by"] = "user"
        if body.layout:
            s["layout"] = body.layout
        if body.language:
            s.setdefault("format", dict(S.SYSTEM_FORMAT))["language"] = body.language
        if body.highlight_wins is not None:
            s.setdefault("options", {})["highlight_wins"] = body.highlight_wins
        S.refresh_status(s, s["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    return await doc(saved)


@router.get("/sheets/{sheet_id}/diff-items", response_model=DiffItems)
async def diff_items(sheet_id: str) -> dict[str, Any]:
    s = await load(sheet_id)
    return {"different": S.diff_items(s)}


@router.put("/sheets/{sheet_id}/format", response_model=SheetDoc)
async def put_format(sheet_id: str, body: FormatSettings) -> dict[str, Any]:
    await load(sheet_id)

    def fn(s: dict[str, Any]) -> None:
        s["format"] = body.model_dump()
        s["format_confirmed"] = True
        s.pop("format_draft", None)
        S.refresh_status(s, s["id"])

    saved, _ = await repo.amutate("sheets", sheet_id, fn)
    await ops.publish(saved)
    return await doc(saved)


def preview_sheet(s: dict[str, Any]) -> dict[str, Any]:
    """생성 전이면 체크된 항목의 행 + 카탈로그 미리 값으로 임시 시트를 만든다(미리보기 · 형식 미리보기)."""
    if s.get("generated_at") and s.get("cells") and s.get("rows"):
        return s
    tmp = copy.deepcopy(s)
    S.sync_rows(tmp)
    cells = dict(tmp.get("cells") or {})
    for r in tmp["rows"]:
        for p in S.products_ordered(tmp):
            key = S.ck(r["id"], p["id"])
            if key in cells:
                continue
            v = ((tmp.get("preview") or {}).get(p["id"]) or {}).get(r["row_key"])
            cells[key] = {"value": v, "state": "ok" if v else "pending", "sources": []}
    tmp["cells"] = cells
    return tmp


@router.post("/sheets/{sheet_id}/format:preview", response_model=FormatPreview)
async def format_preview(sheet_id: str, body: FormatPreviewBody) -> dict[str, Any]:
    """SP2L 미리보기(결정적 · 동기): 격자 · 바뀐 셀 · 안내 줄 · 시트 탭 · 파일명 기본값."""
    s = preview_sheet(await load(sheet_id))
    fs = body.model_dump()
    f = Fmt.of(fs)
    dt = display_table(s, f, {"drop_hidden": True, "memo_footnotes": True, "keep_pending_marks": True})
    lang = f.language
    ncol = len(dt["columns"]) + 1
    letters = [chr(ord("A") + i) for i in range(ncol)]
    title = T.table_title(s, "en" if lang == "en" else "ko")
    head = {"ko": "항목", "en": "Item", "ko_en": "항목 / Item"}[lang]
    rows = [{"n": 1, "cells": [{"text": title, "kind": "title"}] + [{"text": "", "kind": "title"}] * (ncol - 1)},
            {"n": 2, "cells": [{"text": head, "kind": "head"}] + [{"text": c["label"], "kind": "head"} for c in dt["columns"]]}]
    conv = 0
    length_changed = weight_changed = False
    for i, ln in enumerate(dt["lines"]):
        cells = [{"text": ln["label"], "kind": "label"}]
        for c in ln["cells"]:
            cells.append({"text": c["text"], "converted": c["converted"], "kind": "cell", "win": c["win"], "pending": c["pending"]})
            if c["converted"]:
                conv += 1
                rk = next((r["row_key"] for r in s.get("rows") or [] if r["id"] == ln["row_id"]), "")
                if rk in ("dimensions", "bezel"):
                    length_changed = True
                if rk == "weight":
                    weight_changed = True
        rows.append({"n": i + 3, "cells": cells})
    orig = "mm" if length_changed else ("kg" if weight_changed else "mm")
    note = f"단위 바뀐 셀 {conv}개 · 소수점 첫째 자리 반올림 · {orig} 원래 값은 셀 메모에 보관" if conv else None
    tabs = {"en": ["Comparison", "Notes & Sources"]}.get(lang, ["비교표", "메모 · 출처"])
    if s.get("kind") == "req":
        tabs = (["Compliance Matrix"] if lang == "en" else ["요구사항 대응표"]) + tabs
    fmts = fs.get("formats") or ["xlsx"]
    ext = " · ".join({"xlsx": ".xlsx", "pdf": ".pdf", "pptx": ".pptx"}[x] for x in ["xlsx", "pdf", "pptx"] if x in fmts)
    paper = {"a4_landscape": "A4 가로", "a4_portrait": "A4 세로", "letter": "Letter"}[fs.get("paper") or "a4_landscape"]
    chip = " · ".join([T.LANG_LABEL[lang] if lang != "ko_en" else "한/영", {"mm": "mm", "inch": "inch", "both": "mm · inch"}[fs.get("length_unit") or "mm"],
                       {"kg": "kg", "lb": "lb", "both": "kg · lb"}[fs.get("weight_unit") or "kg"]])
    if lang == "en":
        chip = chip.replace("English", "English")
    return {"grid": {"cols": letters, "rows": rows}, "sheet_tabs": tabs, "converted_cells": conv, "note_line": note,
            "filename_default": fs.get("filename_base") or T.default_filename(s, lang), "ext_line": ext, "chip_label": chip,
            "tab_labels": {"xlsx": "Excel (.xlsx)", "pdf": f"PDF · {paper}", "pptx": "PPT 슬라이드"}, "title": title,
            "footnotes": dt["footnotes"], "source_line": T.source_line(s, s.get("cells") or {})}


@router.post("/sheets/{sheet_id}/templates", response_model=JobAccepted, status_code=202)
async def add_template(sheet_id: str, body: TemplateBody) -> dict[str, Any]:
    """고객사 양식 올리기(XLSX 권장 · PDF · DOCX · 이미지) → spec_template(confidential)."""
    await load(sheet_id)
    try:
        meta = await file_meta(body.file_id)
    except ApiError as exc:
        raise ApiError(404 if exc.status == 404 else 503, "FILE_NOT_FOUND" if exc.status == 404 else "UPSTREAM_UNAVAILABLE",
                       "파일을 찾지 못했어요." if exc.status == 404 else "파일 서비스에 연결하지 못했어요.") from exc
    if meta.get("kind") not in ("xlsx", "pdf", "docx", "image", "text"):
        raise ApiError(422, "UNSUPPORTED_FILE", "XLSX · PDF · DOCX · 이미지 양식만 받아요.", {"kind": meta.get("kind")})
    tpl = TPL.new_template(body.file_id, meta.get("name") or "고객사 양식")
    job_id = await enqueue(sheet_id, "spec_template", {"template_id": tpl["id"]}, title="고객사 양식 맞추기", set_active=False,
                           before=lambda x: x.update({"template": tpl}))
    return {"job_id": job_id, "status": "queued", "sheet_id": sheet_id}


@router.delete("/sheets/{sheet_id}/templates/{template_id}", status_code=204)
async def remove_template(sheet_id: str, template_id: str) -> Response:
    await load(sheet_id)

    def fn(s: dict[str, Any]) -> None:
        if (s.get("template") or {}).get("id") != template_id:
            raise ApiError(404, "NOT_FOUND", "양식을 찾을 수 없어요.")
        TPL.remove(s)
        S.refresh_status(s, s["id"])

    await repo.amutate("sheets", sheet_id, fn)
    return Response(status_code=204)


# ── 내 기본값 ─────────────────────────────────────────────

@router.get("/preferences", response_model=Preferences)
async def get_preferences() -> dict[str, Any]:
    uid, _ = ops.user()
    p = await preferences(uid)
    if not p:
        return {"format": S.SYSTEM_FORMAT, "highlight_wins": True, "is_custom": False}
    return {"format": {**S.SYSTEM_FORMAT, **(p.get("format") or {})}, "highlight_wins": bool(p.get("highlight_wins", True)), "is_custom": True}


@router.put("/preferences", response_model=Preferences)
async def put_preferences(body: FormatSettingsPatch) -> dict[str, Any]:
    """내 기본값으로 저장 — 새 작업의 SP2 · SP2L 기본값."""
    uid, _ = ops.user()
    cur = await preferences(uid) or {}
    fmt = {**S.SYSTEM_FORMAT, **(cur.get("format") or {}), **{k: v for k, v in body.model_dump().items() if v is not None}}
    fmt["filename_base"] = None
    await repo.aput("preferences", uid, {"format": fmt, "highlight_wins": cur.get("highlight_wins", True), "updated_at": config.now_iso()})
    return {"format": fmt, "highlight_wins": cur.get("highlight_wins", True), "is_custom": True}


_ = itemcat
