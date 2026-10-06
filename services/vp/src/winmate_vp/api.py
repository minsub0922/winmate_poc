"""vp API (/v1). 이 파일의 엔드포인트가 contracts/vp.json 이 된다(make contracts).

05-vp.md §6 — 목록 · 작업 · 재료 · 구조 · 지시 · 레이아웃 · 수치 · 이미지 · 내보내기 · 넘김 · 규칙 · 업종판 · 버전.
처리기 본체는 ops_work(작업 · 재료 · 되묻기 · 구조) · ops_result(결과 이후)에 있다.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import models as m
from . import ops_result, ops_work, repo, service

router = APIRouter(prefix="/v1")

INTERNAL = ["internal"]


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="vp", title="Value Proposition — 재료 수집 · 메시지 · 레이아웃 · 이미지 슬롯 · 수치", version="0.1.0")


def _doc(doc: dict[str, Any]) -> dict[str, Any]:
    return service.to_api(service.derive(doc))


def _accepted(job_id: str, ref: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(status_code=202, content=m.JobAccepted(job_id=job_id, status="queued", ref=ref).model_dump())


JOB_202 = {202: {"model": m.JobAccepted, "description": "잡 시작(jobs SSE 로 진행)"}}


# ── 6.1 목록 · 작업 ─────────────────────────────────────────

@router.get("/vps", response_model=m.VPList, tags=["vps"])
async def list_vps(limit: int = Query(50, ge=1, le=200), cursor: str | None = None,
                   status: str | None = Query(None, description="draft,ask,check,run,done (쉼표)"),
                   industry: str | None = Query(None, description="업종 코드(쉼표) · GEN"),
                   q: str | None = Query(None, description="고객사 · 작업명 · 레이아웃 코드"),
                   since_days: int | None = Query(None, ge=1, le=3650), archived: bool = False) -> dict[str, Any]:
    return await ops_work.list_vps(status=status, industry=industry, q=q, since_days=since_days, archived=archived,
                                   limit=limit, cursor=cursor)


@router.post("/vps", response_model=m.VPDoc, status_code=201, tags=["vps"])
async def create_vp(body: m.CreateVP) -> dict[str, Any]:
    return _doc(await ops_work.create(body))


@router.get("/vps/{vp_id}", response_model=m.VPDoc, tags=["vps"])
async def get_vp(vp_id: str) -> dict[str, Any]:
    return service.to_api(await service.load(vp_id))


@router.patch("/vps/{vp_id}", response_model=m.VPDoc, tags=["vps"])
async def patch_vp(vp_id: str, body: m.PatchVP) -> dict[str, Any]:
    return _doc(await ops_work.patch(vp_id, body))


@router.post("/vps/{vp_id}:clone", response_model=m.VPDoc, status_code=201, tags=["vps"])
async def clone_vp(vp_id: str, body: m.CloneVP) -> dict[str, Any]:
    return _doc(await ops_work.clone(vp_id, body))


@router.post("/vps/{vp_id}:archive", status_code=204, tags=["vps"])
async def archive_vp(vp_id: str) -> Response:
    await ops_work.archive(vp_id)
    return Response(status_code=204)


@router.get("/vps/{vp_id}/versions", response_model=m.VersionList, tags=["vps"])
async def list_vp_versions(vp_id: str) -> dict[str, Any]:
    return await ops_result.versions(vp_id)


@router.post("/vps/{vp_id}/versions", response_model=m.VPDoc, status_code=201, tags=["vps"])
async def save_vp_version(vp_id: str, body: m.SavePoint | None = None) -> dict[str, Any]:
    """저장 지점(version +1) — VP3 `저장 · 내보내기`."""
    await repo.require_vp(vp_id)
    return _doc(await service.save_point(vp_id, (body.reason if body else None) or "저장"))


@router.post("/vps/{vp_id}/versions/{n}/restore", response_model=m.VPDoc, tags=["vps"])
async def restore_vp_version(vp_id: str, n: int) -> dict[str, Any]:
    return _doc(await service.restore(vp_id, n))


# ── 6.2 재료 ───────────────────────────────────────────────

@router.get("/vps/{vp_id}/source-candidates", response_model=m.SourceCandidates, tags=["materials"])
async def list_source_candidates(vp_id: str) -> dict[str, Any]:
    return await ops_work.source_candidates(vp_id)


@router.put("/vps/{vp_id}/sources", response_model=m.VPDoc, tags=["materials"])
async def put_vp_sources(vp_id: str, body: m.PutSources) -> dict[str, Any]:
    return _doc(await ops_work.put_sources(vp_id, body))


@router.post("/vps/{vp_id}/attachments", response_model=m.Attachment, status_code=201, tags=["materials"],
             responses={202: {"model": m.JobAccepted, "description": "고객 사진 — 이미지 칸 다시 맞추기 잡"}})
async def add_vp_attachment(vp_id: str, body: m.AddAttachment) -> Any:
    att, job_id = await ops_work.add_attachment(vp_id, body)
    if job_id:
        return _accepted(job_id, {"kind": "attachment", "id": att["id"]})
    return att


@router.delete("/vps/{vp_id}/attachments/{att_id}", status_code=204, tags=["materials"])
async def delete_vp_attachment(vp_id: str, att_id: str) -> Response:
    await ops_work.delete_attachment(vp_id, att_id)
    return Response(status_code=204)


@router.post("/vps/{vp_id}/materials:collect", response_model=m.JobAccepted, status_code=202, tags=["materials"])
async def collect_materials(vp_id: str, body: m.CollectBody | None = None) -> dict[str, Any]:
    job_id = await ops_work.collect(vp_id, body)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "vp", "id": vp_id}}


@router.post("/vps/{vp_id}/fixes/{fx}:decide", response_model=m.VPDoc, tags=["materials"])
async def decide_fix(vp_id: str, fx: str, body: m.FixDecision) -> dict[str, Any]:
    return _doc(await ops_work.decide_fix(vp_id, fx, body.decision))


@router.post("/vps/{vp_id}/questions:answer", response_model=m.AnswerResult, tags=["questions"])
async def answer_questions(vp_id: str, body: m.AnswerQuestions) -> dict[str, Any]:
    return await ops_work.answer_questions(vp_id, body)


@router.post("/vps/{vp_id}/plan:refresh", response_model=m.Plan, tags=["structure"])
async def refresh_plan(vp_id: str) -> dict[str, Any]:
    return await ops_work.plan_refresh(vp_id)


# ── 6.3 구조 ───────────────────────────────────────────────

@router.get("/vps/{vp_id}/plan", response_model=m.Plan, tags=["structure"])
async def get_vp_plan(vp_id: str) -> dict[str, Any]:
    return await ops_work.get_plan(vp_id)


@router.patch("/vps/{vp_id}/plan", response_model=m.Plan, tags=["structure"])
async def patch_vp_plan(vp_id: str, body: m.PatchPlan) -> dict[str, Any]:
    return await ops_work.patch_plan(vp_id, body)


@router.post("/vps/{vp_id}/generate", response_model=m.JobAccepted, status_code=202, tags=["structure"])
async def generate_vp(vp_id: str, body: m.GenerateBody | None = None) -> dict[str, Any]:
    job_id = await ops_result.generate(vp_id, body or m.GenerateBody())
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "vp", "id": vp_id}}


# ── 6.4 지시(입력창) ────────────────────────────────────────

@router.post("/vps/{vp_id}/messages", response_model=m.JobAccepted, status_code=202, tags=["result"])
async def post_vp_message(vp_id: str, body: m.MessageBody) -> dict[str, Any]:
    job_id = await ops_result.message(vp_id, body)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "vp", "id": vp_id}}


# ── 6.5 레이아웃 ───────────────────────────────────────────

@router.get("/vps/{vp_id}/sheets/{sh}/layout-options", response_model=m.LayoutOptions, tags=["layout"])
async def get_layout_options(vp_id: str, sh: str, pillars: int | None = Query(None, ge=2, le=4),
                             request_id: str | None = None) -> dict[str, Any]:
    return await ops_result.layout_options(vp_id, sh, pillars=pillars, request_id=request_id)


@router.post("/vps/{vp_id}/sheets/{sh}/layout", response_model=m.Sheet, tags=["layout"], responses=JOB_202)
async def choose_sheet_layout(vp_id: str, sh: str, body: m.ChooseLayout) -> Any:
    sheet, job_id = await ops_result.choose_layout(vp_id, sh, body)
    if job_id:
        return _accepted(job_id, {"kind": "sheet", "id": sh})
    return sheet


@router.patch("/vps/{vp_id}/sheets/{sh}", response_model=m.Sheet, tags=["layout"])
async def patch_vp_sheet(vp_id: str, sh: str, body: m.PatchSheet) -> dict[str, Any]:
    return await ops_result.patch_sheet(vp_id, sh, body)


@router.post("/vps/{vp_id}/layout-requests/{vlr}:cancel", status_code=204, tags=["layout"])
async def cancel_layout_request(vp_id: str, vlr: str) -> Response:
    await ops_result.cancel_layout_request(vp_id, vlr)
    return Response(status_code=204)


@router.post("/vps/{vp_id}/sheets", response_model=m.JobAccepted, status_code=202, tags=["layout"])
async def add_vp_sheet(vp_id: str, body: m.AddSheet) -> dict[str, Any]:
    job_id = await ops_result.add_sheet(vp_id, body)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "vp", "id": vp_id}}


# ── 6.6 수치 ───────────────────────────────────────────────

@router.get("/vps/{vp_id}/sheets/{sh}/metrics", response_model=m.MetricsView, tags=["numbers"])
async def get_sheet_metrics(vp_id: str, sh: str) -> dict[str, Any]:
    return await ops_result.get_metrics(vp_id, sh)


@router.patch("/vps/{vp_id}/metrics/{vmt}", response_model=m.MetricsView, tags=["numbers"])
async def patch_vp_metric(vp_id: str, vmt: str, body: m.PatchMetric) -> dict[str, Any]:
    return await ops_result.patch_metric(vp_id, vmt, body)


@router.post("/vps/{vp_id}/sheets/{sh}/metrics:apply", response_model=m.VPDoc, tags=["numbers"], responses=JOB_202)
async def apply_sheet_metrics(vp_id: str, sh: str) -> Any:
    doc, job_id = await ops_result.apply_metrics(vp_id, sh)
    if job_id:
        return _accepted(job_id, {"kind": "sheet", "id": sh})
    return _doc(doc or {})


@router.get("/vps/{vp_id}/data-request-draft", response_model=m.DataRequestDraft, tags=["numbers"])
async def get_data_request_draft(vp_id: str, sheet: str | None = None) -> dict[str, Any]:
    return await ops_result.data_request_draft(vp_id, sheet)


# ── 6.7 이미지 ─────────────────────────────────────────────

@router.get("/vps/{vp_id}/image-slots", response_model=m.ImageSlotsView, tags=["images"])
async def list_image_slots(vp_id: str) -> dict[str, Any]:
    return await ops_result.get_slots(vp_id)


@router.get("/vps/{vp_id}/image-slots/{vis}/candidates", response_model=m.SlotCandidates, tags=["images"])
async def list_slot_candidates(vp_id: str, vis: str) -> dict[str, Any]:
    return await ops_result.slot_candidates(vp_id, vis)


@router.put("/vps/{vp_id}/image-slots/{vis}", response_model=m.ImageSlot, tags=["images"])
async def put_image_slot(vp_id: str, vis: str, body: m.PutImageSlot) -> dict[str, Any]:
    return await ops_result.put_slot(vp_id, vis, body)


@router.post("/vps/{vp_id}/images:restyle", response_model=m.JobAccepted, status_code=202, tags=["images"])
async def restyle_images(vp_id: str, body: m.Restyle | None = None) -> dict[str, Any]:
    job_id = await ops_result.restyle(vp_id)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "vp", "id": vp_id}}


# ── 6.8 내보내기 ───────────────────────────────────────────

@router.get("/vps/{vp_id}/package", response_model=m.Package, tags=["export"])
async def get_vp_package(vp_id: str, proposal_type: m.ProposalType | None = None) -> dict[str, Any]:
    return await ops_result.get_package(vp_id, proposal_type)


@router.get("/vps/{vp_id}/packages", response_model=m.PackageSet, tags=["export"])
async def get_vp_packages(vp_id: str, selected: m.ProposalType | None = None, estimates_as_notes: bool = True) -> dict[str, Any]:
    """VP4 — 세 유형을 한 번에(유형 열 · 독 문구)."""
    return await ops_result.get_packages(vp_id, selected, estimates_as_notes)


@router.post("/vps/{vp_id}/exports", response_model=m.JobAccepted, status_code=202, tags=["export"])
async def create_vp_export(vp_id: str, body: m.ExportBody) -> dict[str, Any]:
    vex, job_id = await ops_result.start_export(vp_id, body)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "export", "id": vex}}


@router.get("/vps/{vp_id}/exports/{vex}", response_model=m.ExportRecord, tags=["export"])
async def get_vp_export(vp_id: str, vex: str) -> dict[str, Any]:
    rec = await repo.get_export(vex)
    if rec is None or rec.get("vp_id") != vp_id:
        raise repo.not_found("내보내기", vex)
    return rec


@router.get("/vps/{vp_id}/copy-text", response_model=m.CopyText, tags=["export"])
async def get_copy_text(vp_id: str) -> dict[str, Any]:
    return await ops_result.copy_text(vp_id)


# ── 6.9 넘김 ───────────────────────────────────────────────

@router.post("/vps/{vp_id}/handoffs", response_model=m.HandoffCreated, status_code=201, tags=["handoff"],
             responses={202: {"model": m.JobAccepted, "description": "퀵윈 VP-G 변형을 만든 뒤 넘김"}})
async def create_vp_handoff(vp_id: str, body: m.HandoffBody) -> Any:
    status, res = await ops_result.create_handoff(vp_id, body)
    if status == 202:
        return JSONResponse(status_code=202, content=res)
    return res


@router.get("/handoffs/{vho}", response_model=m.Handoff, tags=["handoff"])
async def get_vp_handoff(vho: str) -> dict[str, Any]:
    """proposal 이 당겨 간다(웹 VP4 도 읽는다)."""
    return await ops_result.get_handoff(vho)


@router.post("/handoffs/{vho}:ack", response_model=m.Handoff, tags=INTERNAL)
async def ack_vp_handoff(vho: str, body: m.HandoffAck) -> dict[str, Any]:
    """proposal → vp: 받아 넣은 결과. needs_confirmation 이면 VP 작업에 확인할 것(요청)을 남긴다."""
    return await ops_result.ack_handoff(vho, body)


@router.post("/vps/{vp_id}:release-proposal", response_model=m.ProposalRelease, tags=INTERNAL)
async def release_vp_proposal(vp_id: str, body: m.ProposalReleaseIn) -> dict[str, Any]:
    """proposal → vp: 제안서를 지웠다 — 「연결된 제안서」 · 보낼 제안서를 거둔다(통합)."""
    return await ops_result.release_proposal(vp_id, body.proposal_id)


@router.get("/vps/{vp_id}/proposal-handoff", response_model=m.ProposalHandoff, tags=["handoff"])
async def get_proposal_handoff(vp_id: str, type: m.ProposalType | None = None, section: str | None = None) -> dict[str, Any]:  # noqa: A002
    """10-proposal §8.9 V1 — ProposalHandoff v1(유형별 시트 · 수치 사실 · 이미지 자산)."""
    return await ops_result.proposal_handoff(vp_id, type, section)


@router.get("/value-props/{vp_id}/proposal-handoff", response_model=m.ProposalHandoff, tags=["handoff"])
async def get_value_prop_proposal_handoff(vp_id: str, type: m.ProposalType | None = None, section: str | None = None) -> dict[str, Any]:  # noqa: A002
    """`/v1/vps/{id}/proposal-handoff` 와 같다(10-proposal §8.9 의 경로 이름)."""
    return await ops_result.proposal_handoff(vp_id, type, section)


@router.post("/value-props:draft", response_model=m.DraftAccepted, status_code=202, tags=INTERNAL)
async def draft_value_prop(body: m.DraftBody) -> dict[str, Any]:
    """10-proposal §8.9 V2 — VP 작업 없이 Value Props 초안(재료 → 생성까지 기본값으로)."""
    return await ops_result.draft(body)


# ── 6.10 규칙 · 카탈로그 · 업종판 ────────────────────────────

@router.get("/routing-rules", response_model=m.RoutingRules, tags=["rules"])
async def get_routing_rules() -> dict[str, Any]:
    return await ops_result.routing_rules()


@router.get("/routing-rules/scenarios", response_model=m.Scenarios, tags=["rules"])
async def get_routing_scenarios() -> dict[str, Any]:
    return await ops_result.scenario_rows()


@router.get("/layouts", response_model=m.LayoutCatalog, tags=["rules"])
async def list_layouts(role: str | None = None, family: str | None = None, industry: str | None = None) -> dict[str, Any]:
    return await ops_result.layouts(role, family, industry)


@router.get("/industry-packs", response_model=m.IndustryPacks, tags=["rules"])
async def list_industry_packs() -> dict[str, Any]:
    return await ops_result.packs_view()


@router.post("/industry-packs/{code}:release", response_model=m.JobAccepted, status_code=202, tags=["rules"])
async def release_industry_pack(code: str) -> dict[str, Any]:
    job_id = await ops_result.release_pack(code)
    return {"job_id": job_id, "status": "queued", "ref": {"kind": "industry_pack", "id": code}}


@router.post("/vps/{vp_id}/pack-offers/{vpo}:decide", response_model=m.VPDoc, tags=["rules"], responses=JOB_202)
async def decide_pack_offer(vp_id: str, vpo: str, body: m.PackDecide) -> Any:
    doc, job_id = await ops_result.decide_pack_offer(vp_id, vpo, body.decision)
    if job_id:
        return _accepted(job_id, {"kind": "pack_offer", "id": vpo})
    return _doc(doc or {})
