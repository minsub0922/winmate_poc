"""내보내기(06-spec §4.19 · §7.8 `spec_export`) — 렌더 모델을 만들어 export 서비스에 넘기고 file_id 를 받는다."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError
from winmate_common.ids import new_id

from . import config, repo
from .rules import text as T
from .rules.package import export_document

log = logging.getLogger("winmate.spec.export")
EXT = {"xlsx": ".xlsx", "pdf": ".pdf", "pptx": ".pptx"}


def new_record(sid: str, version: int, fmt: str, settings: dict[str, Any], filename: str) -> dict[str, Any]:
    return {"id": new_id("sex"), "sheet_id": sid, "sheet_version": version, "format": fmt, "settings": settings, "filename": filename,
            "file_id": None, "status": "queued", "job_id": None, "error": None, "warnings": [], "created_at": config.now_iso()}


def filename_for(sheet: dict[str, Any], fmt: str, given: str | None, overrides: dict[str, Any] | None) -> str:
    base = given or (sheet.get("format") or {}).get("filename_base") or T.default_filename(sheet, (overrides or {}).get("language"))
    for e in EXT.values():
        if base.endswith(e):
            base = base[: -len(e)]
    return base + EXT[fmt]


async def run(sid: str, export_id: str) -> dict[str, Any]:
    rec = await repo.amust("exports", export_id, "내보내기")
    sheet = await repo.amust("sheets", sid)
    st = rec.get("settings") or {}
    doc, summary = export_document(sheet, rec["format"], overrides=st.get("overrides"), options=st.get("options"))
    confidential = bool(sheet.get("kind") == "req" or sheet.get("template"))
    body: dict[str, Any] = {"format": rec["format"], "filename": rec["filename"].rsplit(".", 1)[0], "document": doc, "confidential": confidential,
                            "project_id": sheet.get("project_id"), "source_ref": f"spec:{sid}"}
    lang = (st.get("overrides") or {}).get("language") or (sheet.get("format") or {}).get("language", "ko")
    if rec["format"] == "pptx":
        body["language"] = "en" if lang == "en" else "ko"
        body["tbd_label"] = "[To be confirmed]"
    await repo.amutate("exports", export_id, lambda r: r.update({"status": "running", "summary": summary, "request": {k: v for k, v in body.items() if k != "document"}}),
                       what="내보내기")
    exp = ServiceClient("export", timeout=180)
    try:
        res = await exp.post("/v1/exports", json=body)
        if res.get("status") != "done":
            eid = res["export_id"]
            for _ in range(240):
                await asyncio.sleep(1)
                res = await exp.get(f"/v1/exports/{eid}")
                if res.get("status") in ("done", "failed"):
                    break
            if res.get("status") != "done":
                raise ApiError(502, "EXPORT_FAILED", (res.get("error") or {}).get("message") or "파일을 만들지 못했어요.")
    except ApiError as exc:
        await repo.amutate("exports", export_id, lambda r: r.update({"status": "failed", "error": exc.message}), what="내보내기")
        if exc.status == 501:
            raise ApiError(501, exc.code, "이 서버에는 PDF 변환기가 없어 이 형식을 만들 수 없어요. Excel 이나 PPT 로 받아 주세요.") from exc
        raise
    f = res.get("file") or {}
    warnings = res.get("warnings") or []

    def done(r: dict[str, Any]) -> None:
        r.update({"status": "done", "file_id": f.get("id"), "filename": f.get("name") or r["filename"], "warnings": warnings[:20],
                  "slide_count": res.get("slide_count"), "export_service_id": res.get("export_id")})

    await repo.amutate("exports", export_id, done, what="내보내기")
    return {"export_id": export_id, "file_id": f.get("id"), "filename": f.get("name") or rec["filename"], "format": rec["format"],
            "download_url": f"/api/files/v1/files/{f.get('id')}/content?download=1" if f.get("id") else None}


def public(rec: dict[str, Any]) -> dict[str, Any]:
    return {"id": rec["id"], "status": rec["status"], "format": rec["format"], "filename": rec["filename"], "file_id": rec.get("file_id"),
            "download_url": f"/api/files/v1/files/{rec['file_id']}/content?download=1" if rec.get("file_id") else None,
            "job_id": rec.get("job_id"), "error": rec.get("error"), "warnings": rec.get("warnings") or [], "slide_count": rec.get("slide_count")}
