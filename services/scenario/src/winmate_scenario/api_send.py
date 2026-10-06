"""scenario API (/v1) — 보내기 · 내보내기(SC5): 시트 구성 · 제안서 묶음(handoff · ProposalHandoff v1) · 사용 등록 · 파일(PPTX · PDF ·
DOCX · ZIP) · 팀에 공유."""
from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Response
from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso

from . import models as m
from . import repo, service, sheets

log = logging.getLogger("winmate.scenario.api")
router = APIRouter(prefix="/v1")
TAG = ["send"]


@router.get("/scenarios/{sc_id}/sheet-plan", response_model=m.SheetPlan, tags=TAG)
async def sheet_plan(sc_id: str) -> m.SheetPlan:
    """§7.9 시트 구성(결정적) — 장면을 공간 기준으로 묶어 맵 시트 + 공간 시트."""
    await repo.require_sc(sc_id)
    doc = await sheets.ensure_space_keys(sc_id)
    return m.SheetPlan(**sheets.plan(doc))


async def _versioned(sc_id: str, version: int | None) -> tuple[dict[str, Any], int]:
    doc = await repo.require_sc(sc_id)
    if version is None:
        if doc.get("dirty") or not doc.get("saved_version"):
            return doc, int(doc.get("saved_version") or 0)
        version = int(doc["saved_version"])
    v = await repo.get_version(sc_id, version)
    if v is None:
        if version == int(doc.get("saved_version") or 0):
            return doc, version
        raise ApiError(404, "NOT_FOUND", f"저장 버전 v{version}을(를) 찾을 수 없어요")
    snap = dict(v.get("snapshot") or {})
    snap["id"] = sc_id
    snap["updated_at"] = v.get("created_at") or doc.get("updated_at")
    return snap, version


@router.get("/scenarios/{sc_id}/handoff", response_model=m.Handoff, tags=["internal"])
async def handoff(sc_id: str, version: int | None = None) -> m.Handoff:
    """제안서용 묶음(§8) — version 을 주면 그 저장 버전, 없으면 최신(저장 안 한 변경이 있으면 작업본)."""
    if version is None:
        await sheets.ensure_space_keys(sc_id)
    doc, v = await _versioned(sc_id, version)
    return m.Handoff(**sheets.handoff(doc, sheets.plan(doc), v))


@router.get("/scenarios/{sc_id}/proposal-handoff", response_model=m.ProposalHandoff, tags=["internal"])
async def proposal_handoff(sc_id: str, type: Literal["standard", "quickwin", "solution"] = "solution",
                           section: Literal["spaceScenario", "space_scenario", "solution", "sxs"] = "spaceScenario",
                           version: int | None = None) -> m.ProposalHandoff:
    """10-proposal §8.0 ProposalHandoff v1(N1) — 공간별 장면(시간 · 문장 · 이미지) · 장면별 솔루션 · 제품 · 공간 × 솔루션 표."""
    if version is None:
        await sheets.ensure_space_keys(sc_id)
    doc, v = await _versioned(sc_id, version)
    return m.ProposalHandoff(**sheets.proposal_handoff(doc, sheets.plan(doc), v, type, section))


@router.post("/scenarios/{sc_id}/usages", response_model=m.UsageRec, status_code=201, tags=["internal"])
async def add_usage(sc_id: str, body: m.UsageIn) -> m.UsageRec:
    """제안서가 묶음을 읽어 넣은 뒤 등록 → SC0 「제안서에 사용 중」."""
    rec = {"service": body.service, "ref": body.ref, "label": body.label, "version": body.version, "created_at": now_iso()}

    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["usages"] = [u for u in d.get("usages") or [] if not (u.get("service") == body.service and u.get("ref") == body.ref)] + [rec]
        return d
    doc = await repo.update(sc_id, fn)
    await service.register(doc)
    return m.UsageRec(**rec)


@router.delete("/scenarios/{sc_id}/usages/{service_name}/{ref}", status_code=204, tags=["internal"])
async def delete_usage(sc_id: str, service_name: str, ref: str) -> Response:
    def fn(d: dict[str, Any]) -> dict[str, Any]:
        d["usages"] = [u for u in d.get("usages") or [] if not (u.get("service") == service_name and u.get("ref") == ref)]
        return d
    doc = await repo.update(sc_id, fn)
    await service.register(doc)
    return Response(status_code=204)


# ── 파일로 받기 ─────────────────────────────────────────────

def _export_out(rec: dict[str, Any]) -> m.ExportOut:
    return m.ExportOut(id=rec["id"], kind=rec.get("kind") or "pptx", status=rec.get("status") or "queued", job_id=rec.get("job_id"),
                       file_id=rec.get("file_id"), file_name=rec.get("file_name"),
                       url=(f"/api/files/v1/files/{rec['file_id']}/content?download=1" if rec.get("file_id") else None),
                       error=rec.get("error"), created_at=rec.get("created_at") or "")


@router.post("/scenarios/{sc_id}/exports", response_model=m.ExportAccepted, status_code=202, tags=TAG)
async def create_export(sc_id: str, body: m.ExportRequest) -> m.ExportAccepted:
    doc = await repo.require_sc(sc_id)
    if not any(s.get("story") for s in doc.get("scenes") or []):
        raise ApiError(400, "NOT_GENERATED", "시나리오를 먼저 생성해 주세요")
    if body.kind == "zip" and not any(s.get("image") for s in doc.get("scenes") or []):
        raise ApiError(422, "NO_IMAGES", "장면 이미지가 없어요. 장면 이미지를 먼저 만들어 주세요.")
    export_id = new_id("sce")
    job_id = await service.enqueue("sc.export", doc, {"kind": body.kind, "export_id": export_id}, title=f"{doc.get('title')} · {body.kind.upper()}")
    await repo.put_export(export_id, {"scenario_id": sc_id, "kind": body.kind, "job_id": job_id, "status": "queued", "file_id": None})
    return m.ExportAccepted(job_id=job_id, export_id=export_id)


@router.get("/scenarios/{sc_id}/exports/{export_id}", response_model=m.ExportOut, tags=TAG)
async def get_export(sc_id: str, export_id: str) -> m.ExportOut:
    rec = await repo.get_export(export_id)
    if rec is None or rec.get("scenario_id") != sc_id:
        raise ApiError(404, "NOT_FOUND", "내보내기를 찾을 수 없어요")
    return _export_out(rec)


@router.post("/scenarios/{sc_id}/share", response_model=m.ShareOut, tags=TAG)
async def share(sc_id: str) -> m.ShareOut:
    """「팀에 공유」 — workspace 보기 링크."""
    doc = await repo.require_sc(sc_id)
    try:
        res = await ServiceClient("workspace").post("/v1/share-links", json={"target": f"scenario:{sc_id}", "route": f"/scenario/{sc_id}/result",
                                                                             "title": doc.get("title") or "공간 시나리오"})
    except ApiError as exc:
        raise ApiError(502, "SHARE_FAILED", "공유 링크를 만들지 못했어요. 잠시 후 다시 시도해 주세요.", {"upstream": exc.code}) from exc
    return m.ShareOut(url=res.get("url") or "", token=res.get("token"))
