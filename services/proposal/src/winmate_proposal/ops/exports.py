"""§6.12 내보내기(PR7X) — 옵션 · 내보내기 잡(형식 × 언어) · 기록 · 고객사 마스터(.potx)."""
from __future__ import annotations

import re
from typing import Any

from winmate_common.ids import new_id

from .. import clients, config, core, defs, render_doc as R, repo, versions as VER
from .. import models as M
from ..errors import not_found, unprocessable
from ..graphs import common as G

RANGE_RE = re.compile(r"^\s*(\d{1,3})\s*(?:[-–~]\s*(\d{1,3}))?\s*$")


def parse_range(text: str, max_no: int) -> list[int]:
    """「01–07, 21」 → [1..7, 21]. 거꾸로 · 범위 밖 · 모양이 틀리면 422 INVALID_SHEET_RANGE."""
    out: list[int] = []
    for part in [x for x in re.split(r"[,，]", text or "") if x.strip()]:
        m = RANGE_RE.match(part)
        if not m:
            raise unprocessable("INVALID_SHEET_RANGE", "시트 범위는 「01–07, 21」처럼 넣어 주세요", range=text)
        a = int(m.group(1))
        b = int(m.group(2) or a)
        if a < 1 or b < a or b > max_no:
            raise unprocessable("INVALID_SHEET_RANGE", "시트 범위를 다시 확인해 주세요", range=text)
        out += [n for n in range(a, b + 1) if n not in out]
    if not out:
        raise unprocessable("INVALID_SHEET_RANGE", "시트 범위를 넣어 주세요", range=text)
    return out


def team_path(p: dict[str, Any]) -> str:
    return f"B2B 제안서/{(p.get('customer') or {}).get('name') or core.title_display(p)}"


def file_names(base: str, formats: list[str], lang: str) -> list[str]:
    langs = ["KO", "EN"] if lang == "ko_en" else [lang.upper()]
    out = []
    for lg in langs:
        for f in formats:
            suffix = f"_{lg}" if lang == "ko_en" else ""
            out.append(f"{base}{suffix}.{f}")
    return out


async def export_options(pid: str, version: int | None, lang: str | None) -> M.ExportOptions:
    p = await core.load(pid)
    v = version or int(p.get("saved_version") or 0)
    shs = await core.sheets_of(pid)
    open_n = await core.open_confirm_count(pid)
    masters = []
    d = p.get("design") or {}
    from .design import _masters
    for m in await _masters(p):
        mid = m.get("master_id") or m.get("id")
        masters.append(M.MasterOut(id=mid, name=m.get("name") or mid, desc=(m.get("description") or "") or "16:9", builtin=bool(m.get("builtin", True)),
                                   selected=mid == (d.get("master_id") or defs.DEFAULT_MASTER),
                                   preview_url=f"/api/export/v1/templates/{m.get('cover_template') or 'C01'}/thumbnail.png"))
    base = R.file_base(p, v or 1)
    lg = lang if lang in ("ko", "en", "ko_en") else ("en" if p.get("language") == "en" else "ko")
    defaults = M.ExportRequest(version=v or None, formats=["pptx", "pdf"], lang=lg, master_id=d.get("master_id") or defs.DEFAULT_MASTER,
                               include=M.ExportInclude(speaker_notes=True, footnotes=True, appendix=bool(d.get("appendix"))), tbd_mode="keep_marks",
                               filename_base=base, team_folder=M.TeamFolder(enabled=True, path=team_path(p)))
    keys = core.type_sections(p.get("type"))
    n_files = len(file_names(base, ["pptx", "pdf"], lg))
    return M.ExportOptions(version=v, version_label=f"v{v}", header_label=f"{core.title_display(p)} · v{v} · 시트 {len(shs)} + 표지 · 목차",
                           intro=(f"검토 코멘트를 반영한 v{v}를 내보낼 준비가 됐어요. 형식과 언어, 마스터 템플릿을 고르면 파일로 만들어 드릴게요."
                                  if (p.get("review") or {}).get("review_id") else
                                  f"v{v}를 내보낼 준비가 됐어요. 형식과 언어, 마스터 템플릿을 고르면 파일로 만들어 드릴게요."),
                           sheets_total=len(shs), sections=[M.RouteRef(label=defs.SECTIONS[k]["name"], route=k) for k in keys], masters=masters,
                           defaults=defaults, open_confirm=open_n, open_confirm_label=f"확정 필요 {open_n}곳이 남아 있어요" if open_n else "",
                           preview_files=file_names(base, ["pptx", "pdf"], lg),
                           eta_label=f"파일 {n_files}개" + (" · 영문 변환을 포함해 약 1–2분" if lg != "ko" else " · 약 1분"),
                           team_folder_path=team_path(p).replace("/", " / "))


async def create_export(pid: str, body: M.ExportRequest) -> M.JobAccepted:
    p = await core.load(pid)
    if not body.formats:
        raise unprocessable("FORMAT_REQUIRED", "형식을 하나 이상 골라 주세요")
    v = body.version
    if v and not await VER.get_version(pid, v):
        from ..errors import version_not_found
        raise version_not_found(v)
    shs = await core.sheets_of(pid)
    if body.scope.kind == "sheets":
        parse_range(body.scope.range or "", max((int(s.get("sheet_no") or 0) for s in shs), default=0))
    if body.scope.kind == "sections":
        keys = core.type_sections(p.get("type"))
        bad = [k for k in body.scope.section_keys or [] if k not in keys]
        if bad or not body.scope.section_keys:
            raise unprocessable("INVALID_SECTIONS", "내보낼 섹션을 다시 골라 주세요", section_keys=bad)
    xid = new_id("xpt")
    base = (body.filename_base or "").strip() or R.file_base(p, v or int(p.get("saved_version") or 1))
    base = re.sub(r"\.(pptx|pdf)$", "", base)
    tf = body.team_folder.model_dump()
    if tf.get("enabled") and not tf.get("path"):
        tf["path"] = team_path(p)
    # 저장소가 최상위 `version` 키를 내부 CAS 로 쓰므로 버전 번호는 `pr_version` 에 둔다
    doc = {"id": xid, "proposal_id": pid, "pr_version": v, "formats": list(body.formats), "lang": body.lang, "master_id": body.master_id,
           "scope": body.scope.model_dump(), "include": body.include.model_dump(), "tbd_mode": body.tbd_mode, "filename_base": base,
           "team_folder": tf, "status": "queued", "files": [], "warnings": [], "created_iso": config.now_iso()}
    await repo.aput("exports", xid, doc)
    job_id = await G.enqueue("proposal.export", {"proposal_id": pid, "export_id": xid}, title=f"내보내기 · {base}", ref=pid, project_id=p.get("project_id"))
    await repo.amutate("exports", xid, lambda x: x.update({"job_id": job_id}))
    return M.JobAccepted(job_id=job_id, kind="proposal.export", proposal_id=pid, export_id=xid)


async def get_export(pid: str, xid: str) -> M.ExportRecord:
    await core.load(pid)
    x = await repo.aget("exports", xid)
    if not x or x.get("proposal_id") != pid:
        raise not_found("내보내기", xid, "EXPORT_NOT_FOUND")
    st = x.get("status") or "queued"
    if st in ("queued", "running") and x.get("job_id") and not await G.running(x["job_id"]):
        st = "failed" if not x.get("files") else "done"
    return M.ExportRecord(id=xid, proposal_id=pid, version=x.get("pr_version"), formats=x.get("formats") or [], lang=x.get("lang") or "ko",
                          master_id=x.get("master_id"), scope=M.ExportScope(**(x.get("scope") or {})), include=M.ExportInclude(**(x.get("include") or {})),
                          tbd_mode=x.get("tbd_mode") or "keep_marks", filename_base=x.get("filename_base") or "", team_folder=M.TeamFolder(**(x.get("team_folder") or {})),
                          job_id=x.get("job_id"), files=[M.ExportFileOut(**f) for f in x.get("files") or []], team_folder_files=x.get("team_folder_files") or [],
                          status=st, error=x.get("error"), warnings=x.get("warnings") or [], created_at=x.get("created_iso") or "")


async def upload_master(pid: str, body: M.MasterUpload) -> M.MasterCreated:
    p = await core.load(pid)
    meta = await clients.file_meta(body.file_id)
    if not meta:
        raise not_found("파일", body.file_id, "FILE_NOT_FOUND")
    name = (meta.get("name") or "").lower()
    if not name.endswith((".potx", ".pptx")):
        raise unprocessable("UNSUPPORTED_FILE_TYPE", ".potx(또는 .pptx) 파일만 올릴 수 있어요")
    res = await clients.call("export", "POST", "/v1/masters", json={"file_id": body.file_id, "name": body.name or meta.get("name"),
                                                                  "project_id": p.get("project_id")}, raise_errors=True)
    mid = (res or {}).get("master_id")
    nm = (res or {}).get("name") or body.name or meta.get("name") or "고객사 템플릿"

    def fn(x: dict[str, Any]) -> None:
        d = {**core.default_design(), **(x.get("design") or {})}
        d.update({"master_id": mid, "master_name": nm, "master_file_id": body.file_id, "chosen": True})
        x["design"] = d
    await core.mutate(pid, fn)
    return M.MasterCreated(master_id=mid or "", name=nm)
