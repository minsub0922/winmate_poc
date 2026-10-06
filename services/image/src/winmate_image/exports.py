"""내보내기(IMG4 · §4.11 · §6.7 · §7.7).

- PNG · JPG: 이미지 서비스가 바로 만든다(필요한 해상도 렌디션이 없으면 만들고). 「AI 생성 이미지」 표기는 체크한 내보내기만 픽셀에 굽고,
  메타데이터(PNG iTXt + XMP · JPEG XMP)는 늘 넣는다.
- 「수정 전 원본도 함께」(ZIP: PNG 2 + sources.json) · PDF · PPTX(이미지 1장 템플릿 BV-A) · 여러 장(ZIP): export 서비스 잡(202).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from winmate_common.client import ServiceClient
from winmate_common.errors import ApiError, not_found
from winmate_common.ids import new_id, now_iso

from . import imaging, texts, views
from .filestore import download_url, load_image, save_bytes
from .images import ensure_rendition, get_image
from .service import refresh_work
from .store import repo

log = logging.getLogger("winmate.image.exports")

PPTX_TEMPLATE = "BV-A"


def export_view(doc: dict[str, Any]) -> dict[str, Any]:
    return {"export_id": doc["id"], "status": doc.get("status") or "queued", "format": doc.get("format") or "png",
            "filename": doc.get("filename") or "", "file_id": doc.get("file_id"), "download_url": download_url(doc.get("file_id")),
            "job_id": doc.get("job_id"), "error": doc.get("error")}


def default_filename(img: dict[str, Any], work: dict[str, Any], ver: dict[str, Any], ext: str) -> str:
    return texts.filename(img.get("customer_short") or work.get("customer_short"), work.get("subject_short") or img.get("subject_short"),
                          img.get("label") or "시안", int(ver.get("n") or 1), ext)


def with_ext(name: str, ext: str) -> str:
    base = name.rsplit(".", 1)[0] if "." in name[-6:] else name
    return f"{base}.{ext}"


async def _render_file(img: dict[str, Any], ver: dict[str, Any], *, fmt: str, resolution: str, ai_label: bool,
                       filename: str, project_id: str | None) -> dict[str, Any]:
    rend = await ensure_rendition(ver, resolution if resolution != "fhd" else "fhd", img.get("aspect") or "16:9")
    im = await load_image(rend["file_id"])
    if ai_label:
        im = await asyncio.to_thread(imaging.bake_ai_label, im)
    gen = ver.get("generation") or {}
    embed = {"generated": True, "version_id": ver["id"], "model": gen.get("model"),
             "sources": [r.get("source_url") for r in gen.get("references") or [] if r.get("source_url")],
             "dc_source": views.route_result(img["work_id"], img["id"])}
    data, mime = await asyncio.to_thread(imaging.encode, im, "JPEG" if fmt == "jpg" else "PNG", meta=embed, quality=88)
    return await save_bytes(filename, data, mime, source="export", project_id=project_id, parent_id=ver["master_file_id"],
                            meta={"image_id": img["id"], "version_id": ver["id"], "ai_label": ai_label, "rights": "generated",
                                  "is_generated": True, "ai_generated": True, "resolution": resolution}, purpose="img.export")


async def _mark_exported(work_id: str, fmt: str, image_id: str) -> None:
    def fn(w: dict[str, Any]) -> None:
        w["last_export"] = {"format": fmt, "at": now_iso(), "image_id": image_id}

    await repo().mutate("works", work_id, fn, missing_ok=True)
    await refresh_work(work_id)


def sources_json(img: dict[str, Any], vers: list[dict[str, Any]]) -> dict[str, Any]:
    out = []
    for v in vers:
        g = v.get("generation") or {}
        out.append({"version_id": v["id"], "n": v.get("n"), "op": v.get("op"), "is_generated": True, "rights": "generated",
                    "model": g.get("model"), "provider": g.get("provider"), "call": g.get("call"), "prompt_ko": g.get("prompt_ko"),
                    "references": g.get("references") or [], "fallbacks": g.get("fallbacks") or [], "upscale": g.get("upscale"),
                    "created_at": v.get("created_at")})
    return {"image_id": img["id"], "label": img.get("label"), "caption_rule": "생성 이미지",
            "digital_source_type": imaging.TRAINED_MEDIA, "versions": out}


async def _export_job(body: dict[str, Any]) -> dict[str, Any]:
    body = {**body, "async": True}
    res = await ServiceClient("export").post("/v1/exports", json=body)
    return res


async def export_image(image_id: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    img = await get_image(image_id)
    if img.get("status") != "done":
        raise ApiError(409, "NOT_READY", "아직 만들어지지 않은 시안이에요")
    vid = body.get("version_id") or img.get("current_version_id")
    ver = await repo().get("versions", vid)
    if ver is None or ver.get("image_id") != image_id:
        raise not_found("버전", vid)
    work = await repo().get("works", img["work_id"]) or {}
    fmt = body.get("format") or "png"
    resolution = body.get("resolution") or "uhd"
    ext = {"png": "png", "jpg": "jpg", "pdf": "pdf", "pptx": "pptx"}[fmt]
    filename = with_ext(body.get("filename") or default_filename(img, work, ver, ext), ext)
    eid = new_id("ixp")
    doc = {"version_id": ver["id"], "image_id": image_id, "work_id": img["work_id"], "format": fmt, "resolution": resolution,
           "ai_label": bool(body.get("ai_label", True)), "include_original": bool(body.get("include_original")), "filename": filename,
           "file_id": None, "job_id": None, "upstream_export_id": None, "status": "queued", "error": None, "created_at": now_iso()}
    project_id = img.get("project_id")
    if fmt in ("png", "jpg") and not doc["include_original"]:
        fm = await _render_file(img, ver, fmt=fmt, resolution=resolution, ai_label=doc["ai_label"], filename=filename,
                                project_id=project_id)
        doc.update({"status": "done", "file_id": fm["id"]})
        await repo().put("exports", eid, doc)
        await _mark_exported(img["work_id"], fmt, image_id)
        return 200, export_view({**doc, "id": eid})
    if fmt in ("png", "jpg"):
        cur = await _render_file(img, ver, fmt=fmt, resolution=resolution, ai_label=doc["ai_label"], filename=filename,
                                 project_id=project_id)
        vers = sorted(await repo().all("versions", where={"image_id": image_id}), key=lambda v: int(v.get("n") or 0))
        orig = vers[0] if vers else ver
        oname = with_ext(filename.rsplit(".", 1)[0] + "_원본", ext)
        of = await _render_file(img, orig, fmt=fmt, resolution=resolution, ai_label=doc["ai_label"], filename=oname,
                                project_id=project_id)
        req = {"format": "zip", "filename": filename.rsplit(".", 1)[0],
               "document": {"entries": [{"file_id": cur["id"], "path": filename}, {"file_id": of["id"], "path": oname},
                                        {"path": "sources.json", "json": sources_json(img, [orig, ver] if orig["id"] != ver["id"] else [ver])}]},
               "project_id": project_id, "source_ref": f"image:{image_id}"}
    elif fmt == "pdf":
        rend = await ensure_rendition(ver, "fhd", img.get("aspect") or "16:9")
        title = texts.export_title(img.get("label") or "시안", int(ver.get("n") or 1), ver.get("op") or "generate", img.get("aspect"))
        caption = body.get("caption") or ("AI 생성 이미지" if doc["ai_label"] else None)
        req = {"format": "pdf", "filename": filename.rsplit(".", 1)[0],
               "document": {"title": work.get("title") or title, "sections": [{"heading": title, "images": [
                   {"file_id": rend["file_id"], **({"caption": caption} if caption else {})}]}]},
               "project_id": project_id, "source_ref": f"image:{image_id}"}
    else:
        rend = await ensure_rendition(ver, "uhd" if resolution == "uhd" else "fhd", img.get("aspect") or "16:9")
        title = texts.export_title(img.get("label") or "시안", int(ver.get("n") or 1), ver.get("op") or "generate", img.get("aspect"))
        slots: dict[str, Any] = {"title": work.get("title") or title,
                                 "image": {"file_id": rend["file_id"], "fit": "cover", "ai_generated": True}}
        if doc["ai_label"] or body.get("caption"):
            slots["caption"] = body.get("caption") or "AI 생성 이미지"
        req = {"format": "pptx", "filename": filename.rsplit(".", 1)[0],
               "document": {"title": work.get("title") or title, "slides": [{"template_code": PPTX_TEMPLATE, "slots": slots}]},
               "project_id": project_id, "source_ref": f"image:{image_id}"}
    try:
        res = await _export_job(req)
    except ApiError as exc:
        raise ApiError(exc.status if exc.status < 500 else 502, "EXPORT_FAILED", f"내보내기를 만들지 못했어요: {exc.message}",
                       {"upstream": exc.code}) from exc
    doc.update({"job_id": res.get("job_id"), "upstream_export_id": res.get("export_id"),
                "status": "queued" if res.get("job_id") else "done", "file_id": ((res.get("file") or {}).get("id"))})
    await repo().put("exports", eid, doc)
    await _mark_exported(img["work_id"], "zip" if fmt in ("png", "jpg") else fmt, image_id)
    return (202 if doc["job_id"] else 200), export_view({**doc, "id": eid})


async def bulk_export(body: dict[str, Any]) -> dict[str, Any]:
    entries = []
    names: set[str] = set()
    project_id = None
    for vid in body.get("version_ids") or []:
        ver = await repo().get("versions", vid)
        if ver is None:
            raise not_found("버전", vid)
        img = await get_image(ver["image_id"])
        work = await repo().get("works", img["work_id"]) or {}
        project_id = project_id or img.get("project_id")
        name = default_filename(img, work, ver, "png")
        if name in names:
            name = name.replace(".png", f"_{img['id'][-4:]}.png")
        names.add(name)
        fm = await _render_file(img, ver, fmt="png", resolution="fhd", ai_label=bool(body.get("ai_label", True)), filename=name,
                                project_id=project_id)
        entries.append({"file_id": fm["id"], "path": name})
    eid = new_id("ixp")
    req = {"format": "zip", "filename": "Winmate_이미지", "document": {"entries": entries}, "project_id": project_id,
           "source_ref": "image:bulk"}
    try:
        res = await _export_job(req)
    except ApiError as exc:
        raise ApiError(502, "EXPORT_FAILED", f"내보내기를 만들지 못했어요: {exc.message}", {"upstream": exc.code}) from exc
    doc = {"version_id": (body.get("version_ids") or [""])[0], "image_id": None, "format": "zip", "resolution": "fhd",
           "ai_label": bool(body.get("ai_label", True)), "include_original": False, "filename": "Winmate_이미지.zip",
           "file_id": (res.get("file") or {}).get("id"), "job_id": res.get("job_id"), "upstream_export_id": res.get("export_id"),
           "status": "queued" if res.get("job_id") else "done", "error": None, "created_at": now_iso()}
    await repo().put("exports", eid, doc)
    return export_view({**doc, "id": eid})


async def get_export(export_id: str) -> dict[str, Any]:
    doc = await repo().get("exports", export_id)
    if doc is None:
        raise not_found("내보내기", export_id)
    if doc.get("status") in ("queued", "running") and doc.get("upstream_export_id"):
        try:
            up = await ServiceClient("export").get(f"/v1/exports/{doc['upstream_export_id']}")
        except ApiError as exc:
            up = {"status": "failed", "error": {"code": exc.code, "message": exc.message}}
        st = up.get("status")
        if st == "done":
            f = up.get("file") or {}
            doc = await repo().patch("exports", export_id, {"status": "done", "file_id": f.get("id"),
                                                            "filename": f.get("name") or doc.get("filename")}) or doc
        elif st == "failed":
            err = up.get("error") or {"code": "EXPORT_FAILED", "message": "내보내기를 만들지 못했어요"}
            doc = await repo().patch("exports", export_id, {"status": "failed", "error": err}) or doc
        elif st == "running":
            doc = await repo().patch("exports", export_id, {"status": "running"}) or doc
    return export_view(doc)
