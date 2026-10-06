"""제안서로 넘김 · 연결(06-spec §6.10 · §6.11) — spec 은 proposal 을 부르지 않는다. 넘김 기록을 만들고 proposal 이 당겨 간다.

proposal 계약(10-proposal §8.10): P1 `GET /v1/sheets/{id}/proposal-handoff` · P2 `POST /v1/sheets {models, purpose: proposal}` ·
P3 `POST /v1/lifecycle:check`.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from winmate_common.errors import ApiError
from winmate_common.ids import new_id

from .. import config, ops, repo
from .. import sheet as S
from ..api_support import load
from ..catalog import catalog
from ..links import cell_texts, link_item, mark_links_changed
from ..models import (
    Handoff, HandoffAck, HandoffBody, HandoffCreated, LifecycleCheckBody, LifecycleCheckResult, LinkList, LinksReleased, Package, ProposalHandoff,
)
from ..rules import items as itemcat
from ..rules import text as T
from ..rules.package import build_package
from ..rules.values import Fmt, catalog_candidate, diff_key, render_text

router = APIRouter(prefix="/v1", tags=["handoff"])

SECTION_NO = {"standard": "08", "quickwin": "05"}
TEMPLATES = ("SC-A", "SC-B", "SD-A", "SD-B")
TEMPLATE_NAME = {"SC-A": "사양 비교표 2~5개", "SC-B": "요구사항 대응표", "SD-A": "그룹별 상세 사양", "SD-B": "치수 · 설치 정보"}
SHEET_LABEL = {"SC-A": "사양 비교표", "SC-B": "요구사항 대응표", "SD-A": "제품별 상세", "SD-B": "치수 · 설치 정보"}
SHEET_TITLE = {"SC-A": "스펙 비교", "SC-B": "요구사항 대응표", "SD-A": "제품 상세", "SD-B": "치수 · 설치"}
NO_SPEC = "Solution형 제안서에는 '제품 스펙' 섹션이 없어요."


def default_templates(s: dict[str, Any]) -> list[str]:
    """SP4 시트 종류 기본: compare → 사양 비교표 · single → 제품별 상세 · req → 대응표(+ 스펙표가 켜져 있으면 비교표/상세)."""
    n = len(s.get("products") or [])
    spec_t = "SC-A" if n >= 2 else "SD-A"
    if s.get("kind") == "req" or (s.get("compliance") or {}).get("rows"):
        out = ["SC-B"]
        if ((s.get("compliance") or {}).get("include") or {}).get("spec", True) and n:
            out.append(spec_t)
        return out
    return [spec_t]


def _ensure_generated(s: dict[str, Any]) -> None:
    if not s.get("generated_at") or not s.get("cells"):
        raise ApiError(422, "NOT_GENERATED", "시트를 먼저 만들어 주세요.")


def _templates_of(s: dict[str, Any], templates: list[str] | None) -> list[str]:
    ts = list(dict.fromkeys(templates or default_templates(s)))
    bad = [t for t in ts if t not in TEMPLATES]
    if bad:
        raise ApiError(422, "VALIDATION_FAILED", f"알 수 없는 시트 템플릿이에요: {', '.join(bad)}")
    if "SC-B" in ts and not (s.get("compliance") or {}).get("rows"):
        raise ApiError(422, "VALIDATION_FAILED", "요구사항 대응표가 없어 '요구사항 대응표' 시트는 넘길 수 없어요.")
    return ts


@router.post("/sheets/{sheet_id}/handoffs", response_model=HandoffCreated, status_code=201)
async def create_handoff(sheet_id: str, body: HandoffBody) -> dict[str, Any]:
    """`제안서에 넣기`(SP4) · `새 제안서로 시작`(proposal_id null). Solution형은 422 NO_SPEC_SECTION."""
    s = await load(sheet_id)
    if body.proposal_type == "solution":
        raise ApiError(422, "NO_SPEC_SECTION", NO_SPEC)
    _ensure_generated(s)
    templates = _templates_of(s, body.templates)
    opts = body.options.model_dump() if body.options else None
    ov = body.overrides.model_dump(exclude_none=True) if body.overrides else None
    pkg = build_package(s, templates=templates, mode=body.mode, options=opts, overrides=ov, replace_ids=body.replace_proposal_sheet_ids)
    sho = new_id("sho")
    section_no = body.section_no or SECTION_NO.get(body.proposal_type, "08")
    uid, _ = ops.user()
    rec = {"sheet_id": sheet_id, "sheet_version": s.get("doc_version", 0), "proposal_id": body.proposal_id, "proposal_type": body.proposal_type,
           "proposal_title": body.proposal_title, "section_no": section_no, "templates": templates, "mode": body.mode, "package": pkg,
           "status": "ready", "ack": None, "options": opts, "overrides": ov, "sent_snapshot": cell_texts(s), "owner_id": uid}
    saved = await repo.aput("handoffs", sho, rec)
    if body.proposal_id:
        tp = {"id": body.proposal_id, "title": body.proposal_title or ((s.get("target_proposal") or {}).get("title") or "제안서"),
              "type": body.proposal_type, "section_no": section_no}
        await repo.amutate("sheets", sheet_id, lambda x: x.update({"target_proposal": {**(x.get("target_proposal") or {}), **tp}}))
    route = f"/proposal/{body.proposal_id}/sections/spec?handoff={sho}" if body.proposal_id else f"/proposal/new?handoff={sho}"
    return {"id": sho, "status": "ready", "open_route": route, "package": saved["package"]}


def _handoff_out(h: dict[str, Any]) -> dict[str, Any]:
    return {k: h.get(k) for k in ("id", "sheet_id", "sheet_version", "proposal_id", "proposal_type", "templates", "mode", "package", "status",
                                   "ack", "created_at")}


@router.get("/handoffs/{handoff_id}", response_model=Handoff)
async def get_handoff(handoff_id: str) -> dict[str, Any]:
    """proposal 이 넘김 묶음을 당겨 간다."""
    h = await repo.aget("handoffs", handoff_id)
    if h is None:
        raise ApiError(404, "NOT_FOUND", "넘김을 찾을 수 없어요.")
    return _handoff_out(h)


@router.post("/handoffs/{handoff_id}:ack", response_model=Handoff, tags=["internal"])
async def ack_handoff(handoff_id: str, body: HandoffAck) -> dict[str, Any]:
    """proposal 이 반영 결과를 알림 — applied 면 연결(slk_) 생성 · 갱신(보낸 스냅숏), 그 연결의 `제안서와 다름` 경고 해결."""
    h = await repo.aget("handoffs", handoff_id)
    if h is None:
        raise ApiError(404, "NOT_FOUND", "넘김을 찾을 수 없어요.")
    ack = body.model_dump()
    if body.result == "failed":
        saved = await repo.amutate("handoffs", handoff_id, lambda x: x.update({"status": "failed", "ack": ack}), what="넘김")
        return _handoff_out(saved[0])
    pid = body.proposal_id or h.get("proposal_id")
    if not pid:
        raise ApiError(422, "VALIDATION_FAILED", "어느 제안서에 반영했는지(proposal_id) 알려 주세요.")
    sid = h["sheet_id"]
    s = await repo.amust("sheets", sid)
    existing = next((lk for lk in await repo.alist("links", {"sheet_id": sid}) if lk.get("proposal_id") == pid), None)
    now = config.now_iso()
    link_id = existing["id"] if existing else new_id("slk")
    title = body.proposal_title or h.get("proposal_title") or ((s.get("target_proposal") or {}).get("title")) or "제안서"
    link = {"sheet_id": sid, "proposal_id": pid, "proposal_title": title, "section_no": body.section_no or h.get("section_no") or "08",
            "section_name": body.section_name or "제품 스펙", "sent_version": h.get("sheet_version", 0), "sent_snapshot": h.get("sent_snapshot") or {},
            "status": "in_sync", "proposal_sheet_ids": body.proposal_sheet_ids, "handoff_id": handoff_id, "acked_at": now}
    await repo.aput("links", link_id, link)

    def fn(x: dict[str, Any]) -> None:
        for w in x.get("warnings") or []:
            if w.get("kind") == "value_mismatch_proposal" and w.get("link_id") == link_id and w.get("status") in ("open", "decided"):
                w["status"] = "applied"
        x["target_proposal"] = {**(x.get("target_proposal") or {}), "id": pid, "title": title,
                                "type": h.get("proposal_type") or "standard", "section_no": link["section_no"]}
        S.refresh_status(x, x["id"])

    saved, _ = await repo.amutate("sheets", sid, fn)
    await mark_links_changed(saved)
    saved = await repo.amust("sheets", sid)
    await ops.publish(saved)
    hs, _ = await repo.amutate("handoffs", handoff_id, lambda x: x.update({"status": "acked", "ack": ack, "link_id": link_id}), what="넘김")
    return _handoff_out(hs)


@router.get("/links", response_model=LinkList)
async def list_links(proposal_id: str | None = None, sheet_id: str | None = None) -> dict[str, Any]:
    """제안서 PR7Q `값 불일치` · `Spec 시트에서 보기` — 연결마다 보낸 값과 지금 값의 차이."""
    if not proposal_id and not sheet_id:
        raise ApiError(422, "VALIDATION_FAILED", "proposal_id 나 sheet_id 중 하나가 필요해요.")
    where = {"proposal_id": proposal_id} if proposal_id else {"sheet_id": sheet_id}
    links = await repo.alist("links", where)
    if proposal_id and sheet_id:
        links = [lk for lk in links if lk.get("sheet_id") == sheet_id]
    out = []
    for lk in links:
        s = await repo.aget("sheets", lk["sheet_id"])
        if s is None or s.get("archived_at"):
            continue
        out.append(link_item(s, lk))
    return {"items": out}


@router.delete("/links", response_model=LinksReleased, tags=["internal"])
async def release_links(proposal_id: str = Query(..., min_length=1), sheet_id: str | None = None) -> dict[str, Any]:
    """proposal → spec: 제안서를 지웠다(또는 그 시트 반입을 실행 취소했다 — `sheet_id`) — 그 제안서와의 연결(slk_)을 지우고,
    그 연결의 `제안서와 다름` 경고를 닫고, 시트의 `보낼 제안서`(target_proposal)가 그 제안서면 비운다. 지운 제안서로 알림이 가지 않게(통합)."""
    links = await repo.alist("links", {"proposal_id": proposal_id})
    if sheet_id:
        links = [lk for lk in links if lk.get("sheet_id") == sheet_id]
    by_sheet: dict[str, set[str]] = {}
    for lk in links:
        await repo.run(repo.delete, "links", lk["id"])
        by_sheet.setdefault(lk["sheet_id"], set()).add(lk["id"])
    for sid, lids in by_sheet.items():
        if await repo.aget("sheets", sid) is None:
            continue

        def fn(x: dict[str, Any], lids: set[str] = lids) -> None:
            for w in x.get("warnings") or []:
                if w.get("kind") == "value_mismatch_proposal" and w.get("link_id") in lids and w.get("status") in ("open", "decided"):
                    w["status"] = "dismissed"
            if (x.get("target_proposal") or {}).get("id") == proposal_id:
                x["target_proposal"] = None
            S.refresh_status(x, x["id"])

        saved, _ = await repo.amutate("sheets", sid, fn)
        await ops.publish(saved)
    return {"proposal_id": proposal_id, "deleted": len(links), "sheet_ids": sorted(by_sheet)}


@router.get("/sheets/{sheet_id}/package", response_model=Package)
async def get_package(sheet_id: str, templates: str | None = Query(None, description="쉼표로 — SC-A,SD-B"),
                      locale: str | None = Query(None, pattern="^(ko|en|ko_en)$")) -> dict[str, Any]:
    """넘김 없이 묶음 미리보기(SP4 슬라이드 미리보기 · 제안서 딸깍)."""
    s = await load(sheet_id)
    _ensure_generated(s)
    ts = _templates_of(s, [t.strip() for t in templates.split(",") if t.strip()] if templates else None)
    return build_package(s, templates=ts, mode="replace", options=None, overrides={"language": locale} if locale else None)


@router.get("/sheets/{sheet_id}/proposal-handoff", response_model=ProposalHandoff)
async def proposal_handoff(sheet_id: str, type: str = Query("standard", pattern="^(standard|quickwin|solution)$"),  # noqa: A002
                           section: str = "spec") -> dict[str, Any]:
    """ProposalHandoff v1(10-proposal §8.0 · P1) — 보이는 행 · 강조 · 각주 · [확정 필요] 칸 · 모델 목록 · live_link."""
    s = await load(sheet_id)
    if type == "solution":
        raise ApiError(422, "NO_SPEC_SECTION", NO_SPEC)
    _ensure_generated(s)
    ts = default_templates(s)
    pkg = build_package(s, templates=ts, mode="replace", options=None)
    ver = (s.get("catalog") or {}).get("version") or ""
    src = [{"kind": "catalog", "ref": f"spec:{sheet_id}", "label": f"사내 제품 카탈로그 {ver}".strip(), "tier": "T2"}]
    items = []
    for i, sh in enumerate(pkg["sheets"]):
        t = sh["template"]
        data = sh["data"]
        pending = len([f for f in pkg["fact_check"] if f["sheet_index"] == i])
        items.append({
            "key": f"{t}:{i}", "label": data.get("title") or SHEET_LABEL[t], "from_label": "Spec 시트", "sheet_role": t.split("-")[0],
            "sheet_title": SHEET_TITLE[t] + (f" · {data.get('label')}" if t == "SD-A" and data.get("label") else ""),
            "template_hint": {"code": t, "name": TEMPLATE_NAME[t]}, "status": "warn" if pending else "ok",
            "status_label": f"[확정 필요] {pending}건" if pending else "그대로 들어가요", "include_default": True,
            "repeat_key": {"kind": "product", "ref": data.get("model_ref") or "", "label": data.get("label") or ""} if t in ("SD-A", "SD-B") else None,
            "content": data, "sources": src})
    facts = [{"key": f"spec_fact_{i + 1}", "label": f["text"].replace(" [확정 필요]", ""), "status": "placeholder", "placeholder": "[확정 필요]",
              "source": {"kind": "spec", "ref": sheet_id, "reason": f["reason"]}} for i, f in enumerate(pkg["fact_check"])]
    return {"source": {"feature": "SP", "ref_id": sheet_id, "version": s.get("doc_version", 0), "title": T.display_title(s),
                       "updated_at": S.touched(s), "route": f"/spec/{sheet_id}"},
            "target": {"proposal_type": type, "section_key": section or "spec"},
            "customer": {"name": s["customer_name"]} if s.get("customer_name") else None, "rq_ref": s.get("rq_ref"),
            "items": items, "facts": facts, "live_link": True}


def _diff_summary(old: dict[str, Any] | None, new: dict[str, Any] | None, version: str) -> str | None:
    if not old or not new:
        return None
    f = Fmt()
    parts = []
    for rk in ("size_resolution", "brightness_contrast", "operation_hours", "power", "warranty"):
        a = catalog_candidate(rk, old, version).value
        b = catalog_candidate(rk, new, version).value
        if a and b and diff_key(rk, a) != diff_key(rk, b):
            parts.append(f"{itemcat.ROW_SHORT.get(rk, rk)} {render_text(rk, a, f)[0]} → {render_text(rk, b, f)[0]}")
        if len(parts) == 3:
            break
    return " · ".join(parts) or None


@router.post("/lifecycle:check", response_model=LifecycleCheckResult)
async def lifecycle_check(body: LifecycleCheckBody) -> dict[str, Any]:
    """P3 — 모델마다 판매 상태 · 후속 후보 · 근거(사내 카탈로그 생애주기 → 생애주기 표 → KB 존재 여부, §4.17.2)."""
    cat = catalog()
    ver = await cat.version()
    out = []
    for raw in list(dict.fromkeys([m for m in body.model_codes if m and m.strip()]))[:50]:
        code = await cat.resolve(raw)
        spec = await cat.spec(code) if code else None
        p = {"id": "", "model_code": (spec or {}).get("model_code") or raw, "display_name": (spec or {}).get("display_name") or raw,
             "in_catalog": bool(spec and spec.get("in_catalog", True))}
        lc = await ops.evaluate_lifecycle(p, spec)
        status = {"on_sale": "on_sale", "eol_planned": "on_sale", "discontinued": "discontinued"}.get(lc["status"], "unknown")
        succs = []
        succ = lc.get("successor")
        rep = None
        if succ:
            rep = {"model_code": succ["model_code"], "display_name": succ.get("display_name"), "relation_text": succ.get("relation")}
        elif lc["status"] in ("discontinued", "eol_planned"):
            r = await ops.replacement_for(p, lc, {"products": []})
            if r:
                rep = {"model_code": r["model_code"], "display_name": r["label"], "relation_text": r["relation_text"]}
        if rep and rep.get("model_code"):
            nspec = await cat.spec(rep["model_code"]) if await cat.resolve(rep["model_code"]) else None
            succs.append({"model_code": rep["model_code"], "display_name": rep.get("display_name"), "reason": rep.get("relation_text") or "후속 모델",
                          "spec_diff_summary": _diff_summary(spec, nspec, ver)})
        ev = lc.get("source") or ""
        if lc["status"] == "eol_planned":
            ev = f"{ev} · 단종 예정".strip(" ·")
        if lc.get("as_of"):
            ev = f"{ev} · {lc['as_of']}"
        out.append({"model_code": p["model_code"], "display_name": p["display_name"] if spec or lc["status"] != "unknown" else None,
                    "status": status, "successors": succs, "evidence": ev or "사내 카탈로그에 없음"})
    return {"items": out}
