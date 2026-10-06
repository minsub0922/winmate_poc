"""files API (/v1). 이 파일의 엔드포인트가 contracts/files.json 이 된다(make contracts).

- 올리기: POST /v1/files (multipart, 브라우저) · POST /v1/files/bytes (JSON base64, 서비스 간 internal)
- 조회: GET /v1/files · /v1/files/{id} · /content · /thumbnail · /parsed · /pages/{n}/image · /pages/{n}/thumbnail
- 바꾸기: PATCH · DELETE(소프트 삭제) · POST /parse(다시 읽기) · POST /copy(폴더 · 프로젝트 사본)
"""
from __future__ import annotations

import asyncio
from typing import Any, Literal

from fastapi import APIRouter, File, Form, Path, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from winmate_common.context import current_user

from .models import BytesUpload, CopyRequest, FileList, FileMeta, FilePatch, ParseAccepted, ParsedDocument, Source
from .service import _too_large, b64decode_strict, service
from .settings import PARSER_VERSION

router = APIRouter(prefix="/v1")

_BINARY = {"content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}
_IMAGE = {"content": {"image/webp": {"schema": {"type": "string", "format": "binary"}},
                      "image/png": {"schema": {"type": "string", "format": "binary"}}}}
FileId = Path(..., description="file_<ULID>", pattern=r"^file_[0-9A-Za-z]{10,40}$")


class ServiceInfo(BaseModel):
    service: str
    title: str
    version: str


@router.get("/info", response_model=ServiceInfo, tags=["meta"])
async def info() -> ServiceInfo:
    return ServiceInfo(service="files", title="파일 — 업로드 · 저장 · 문서 파싱(PPTX·PDF·DOCX·XLSX·TXT·메일·HEIC) · 미리보기", version="0.1.0")


async def _read_upload(file: UploadFile, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1 << 20)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise _too_large(total, limit)
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/files", status_code=201, response_model=FileMeta, tags=["files"], summary="파일 올리기(multipart)")
async def upload_file(
    file: UploadFile = File(..., description="파일 하나(최대 UPLOAD_MAX_MB, 기본 50MB). HEIC/HEIF 는 JPEG 로 바꿔 저장"),
    confidential: bool = Form(False, description="고객 기밀 자료"),
    project_id: str | None = Form(None),
    purpose: str | None = Form(None, description="용도 태그(예 rq.source · logo · site_photo)"),
    source: Source = Form("upload"),
    parent_id: str | None = Form(None),
    folder: str | None = Form(None),
) -> dict[str, Any]:
    svc = service()
    data = await _read_upload(file, svc.cfg.upload_max_bytes)
    rec = await asyncio.to_thread(
        svc.ingest, data, file.filename, file.content_type, user=current_user(), source=source,
        confidential=confidential, project_id=project_id or None, parent_id=parent_id or None,
        purpose=purpose or None, folder=folder,
    )
    if rec["parse_status"] == "pending":
        svc.schedule_parse(rec)
    return svc.to_meta(rec)


@router.post("/files/bytes", status_code=201, response_model=FileMeta, tags=["internal"], summary="바이트 저장(서비스 간)")
async def save_bytes(body: BytesUpload) -> dict[str, Any]:
    svc = service()
    data = b64decode_strict(body.data_b64)
    mime = body.mime if body.mime and body.mime != "application/octet-stream" else None
    rec = await asyncio.to_thread(
        svc.ingest, data, body.name, mime, user=current_user(), source=body.source, confidential=body.confidential,
        project_id=body.project_id, parent_id=body.parent_id, purpose=body.purpose, folder=body.folder, meta_extra=body.meta,
    )
    if rec["parse_status"] == "pending":
        svc.schedule_parse(rec)
    return svc.to_meta(rec)


@router.get("/files", response_model=FileList, tags=["files"], summary="파일 목록(최신순)")
async def list_files(
    owner: str = Query("me", description="me | all | <user id>. 남의 기밀 파일은 project_id 로 거를 때만 보인다"),
    project_id: str | None = None,
    source: Source | None = None,
    kind: str | None = Query(None, description="pdf|pptx|docx|xlsx|image|text|email|svg|zip|other — 쉼표로 여러 개"),
    q: str | None = Query(None, description="이름 포함 검색"),
    parent_id: str | None = Query(None, description="이 파일의 자식(추출 이미지 · 첨부)"),
    purpose: str | None = None,
    folder: str | None = None,
    include_children: bool = Query(False, description="자식 파일도 함께(기본은 원본만)"),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
) -> dict[str, Any]:
    svc = service()
    items, nxt = await asyncio.to_thread(
        svc.list, user=current_user(), owner=owner, project_id=project_id, source=source, kind=kind, q=q,
        parent_id=parent_id, purpose=purpose, folder=folder, include_children=include_children, limit=limit, cursor=cursor,
    )
    return {"items": [svc.to_meta(r) for r in items], "next_cursor": nxt}


@router.get("/files/{file_id}", response_model=FileMeta, tags=["files"], summary="파일 메타")
async def get_file(file_id: str = FileId) -> dict[str, Any]:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    svc.maybe_resume(rec)
    return svc.to_meta(rec)


@router.patch("/files/{file_id}", response_model=FileMeta, tags=["files"], summary="이름 · 기밀 · 프로젝트 · 메타 바꾸기")
async def patch_file(body: FilePatch, file_id: str = FileId) -> dict[str, Any]:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    changes = {k: getattr(body, k) for k in body.model_fields_set}
    updated = await asyncio.to_thread(svc.patch, rec, changes, current_user())
    return svc.to_meta(updated)


@router.delete("/files/{file_id}", status_code=204, response_class=Response, tags=["files"],
               summary="지우기(소프트 삭제 — 같은 내용을 쓰는 다른 파일이 있으면 바이너리는 남긴다)")
async def delete_file(file_id: str = FileId) -> Response:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    await asyncio.to_thread(svc.delete, rec, current_user())
    return Response(status_code=204)


@router.get("/files/{file_id}/content", response_class=Response, responses={200: {"description": "파일 바이트", **_BINARY}},
            tags=["files"], summary="내용 내려받기(?download=1 이면 attachment)")
async def get_content(file_id: str = FileId, download: bool = Query(False)) -> Response:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    path, media, headers = svc.content_headers(rec, download)
    return FileResponse(path, media_type=media, headers=headers)


@router.get("/files/{file_id}/thumbnail", response_class=Response, responses={200: {"description": "썸네일", **_IMAGE}},
            tags=["files"], summary="썸네일(이미지 축소 · PDF/PPTX 첫 쪽 · 형식 아이콘)")
async def get_thumbnail(
    file_id: str = FileId,
    w: int = Query(320, ge=16, le=1024, description="가로 px"),
    format: Literal["webp", "png"] = Query("webp"),  # noqa: A002
) -> Response:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    data, media = await asyncio.to_thread(svc.thumbnail, rec, w, format)
    return Response(content=data, media_type=media, headers={"cache-control": "private, max-age=86400"})


@router.get("/files/{file_id}/parsed", response_model=ParsedDocument, tags=["files"],
            summary="문서 파싱 결과(쪽 · 블록 · 표 · 시트 · 메일). 처음이면 읽을 때까지 기다린다")
async def get_parsed(file_id: str = FileId) -> Response:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    body = await svc.parsed_json(rec)
    return Response(content=body, media_type="application/json")


@router.post("/files/{file_id}/parse", status_code=202, response_model=ParseAccepted, tags=["files"],
             summary="파싱 시작(백그라운드). force=true 면 캐시를 버리고 다시 읽는다")
async def start_parse(file_id: str = FileId, force: bool = Query(False)) -> dict[str, Any]:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    if not svc.can_parse(rec["kind"], rec.get("fmt") or ""):
        return {"file_id": file_id, "parse_status": "unsupported", "parser_version": PARSER_VERSION}
    if force:
        task = asyncio.get_running_loop().create_task(svc.parsed_json(rec, force=True))
        svc._bg.add(task)
        task.add_done_callback(lambda t: (svc._bg.discard(t), t.cancelled() or t.exception()))
        status = "parsing"
    elif rec.get("parse_status") == "done" and rec.get("parse_version") == PARSER_VERSION:
        status = "done"
    else:
        svc.schedule_parse(rec)
        status = "parsing" if rec.get("parse_status") in ("pending", "parsing", "none", None) else rec["parse_status"]
    return {"file_id": file_id, "parse_status": status, "parser_version": PARSER_VERSION}


@router.get("/files/{file_id}/pages/{n}/image", response_class=Response,
            responses={200: {"description": "쪽 그림(PNG 기본)", "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}}}},
            tags=["files"], summary="n 쪽 그림(PDF · LibreOffice 있으면 PPTX/DOCX/XLSX · 이미지는 1쪽)")
async def get_page_image(
    file_id: str = FileId,
    n: int = Path(..., ge=1, description="1부터"),
    w: int = Query(1280, ge=16, le=4096),
    format: Literal["png", "jpeg", "webp"] = Query("png"),  # noqa: A002
) -> Response:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    data, media = await asyncio.to_thread(svc.page_image, rec, n, w, format)
    return Response(content=data, media_type=media, headers={"cache-control": "private, max-age=86400"})


@router.get("/files/{file_id}/pages/{n}/thumbnail", response_class=Response, responses={200: {"description": "쪽 썸네일", **_IMAGE}},
            tags=["files"], summary="n 쪽 썸네일(렌더러가 없으면 PPTX 는 슬라이드 자리표시 카드)")
async def get_page_thumbnail(
    file_id: str = FileId,
    n: int = Path(..., ge=1),
    w: int = Query(320, ge=16, le=1024),
    format: Literal["webp", "png"] = Query("webp"),  # noqa: A002
) -> Response:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    data, media = await asyncio.to_thread(svc.page_image, rec, n, w, format, thumb=True)
    return Response(content=data, media_type=media, headers={"cache-control": "private, max-age=86400"})


@router.post("/files/{file_id}/copy", status_code=201, response_model=FileMeta, tags=["files"],
             summary="사본 만들기(같은 바이너리, 다른 폴더 · 프로젝트)")
async def copy_file(body: CopyRequest, file_id: str = FileId) -> dict[str, Any]:
    svc = service()
    rec = await asyncio.to_thread(svc.get, file_id)
    new = await asyncio.to_thread(svc.copy, rec, user=current_user(), folder=body.folder, project_id=body.project_id, name=body.name)
    return svc.to_meta(new)
