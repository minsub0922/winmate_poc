"""export 테스트 공용 — files 서비스 스텁(in-process) · fakeredis · 임시 DATA_DIR · 견본 문서."""
from __future__ import annotations

import base64
import hashlib
import io
from typing import Any

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from PIL import Image, ImageDraw
from winmate_common import testing
from winmate_common.ids import new_id, now_iso

KINDS = {
    "application/pdf": "pdf", "application/zip": "zip", "image/png": "image", "image/jpeg": "image", "image/svg+xml": "svg",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.presentationml.template": "pptx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/json": "text", "text/plain": "text",
}


class FilesStub:
    """files 계약(POST /v1/files/bytes · GET /v1/files/{id} · GET /v1/files/{id}/content)만 흉내 낸다."""

    def __init__(self) -> None:
        self.blobs: dict[str, bytes] = {}
        self.metas: dict[str, dict[str, Any]] = {}
        self.saved: list[dict[str, Any]] = []      # export 가 저장한 것(요청 본문)
        self.app = testing.stub_app("files")
        app = self.app

        @app.post("/v1/files/bytes", status_code=201)
        async def save_bytes(request: Request) -> JSONResponse:
            body = await request.json()
            data = base64.b64decode(body["data_b64"])
            meta = self.put(body["name"], data, body.get("mime") or "application/octet-stream", meta=body.get("meta") or {},
                            source=body.get("source", "generated"), confidential=bool(body.get("confidential")),
                            project_id=body.get("project_id"))
            self.saved.append({**{k: v for k, v in body.items() if k != "data_b64"}, "id": meta["id"]})
            return JSONResponse(meta, status_code=201)

        @app.get("/v1/files/{file_id}")
        async def get_file(file_id: str) -> JSONResponse:
            if file_id not in self.metas:
                return JSONResponse({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}, status_code=404)
            return JSONResponse(self.metas[file_id])

        @app.get("/v1/files/{file_id}/content")
        async def get_content(file_id: str) -> Response:
            if file_id not in self.blobs:
                return JSONResponse({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}, status_code=404)
            return Response(self.blobs[file_id], media_type=self.metas[file_id]["mime"])

    def put(self, name: str, data: bytes, mime: str, *, meta: dict[str, Any] | None = None, source: str = "upload",
            confidential: bool = False, project_id: str | None = None) -> dict[str, Any]:
        fid = new_id("file")
        fm = {
            "id": fid, "name": name, "mime": mime, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "kind": KINDS.get(mime, "other"), "source": source, "confidential": confidential, "owner": "u_test",
            "owner_name": "테스터", "project_id": project_id, "parent_id": None, "meta": meta or {}, "created_at": now_iso(),
            "url": f"/api/files/v1/files/{fid}/content", "thumb_url": f"/api/files/v1/files/{fid}/thumbnail",
        }
        self.blobs[fid] = data
        self.metas[fid] = fm
        return fm

    def by_id(self, fid: str) -> bytes:
        return self.blobs[fid]


def png_bytes(w: int = 640, h: int = 400, color: tuple[int, int, int] = (40, 80, 200)) -> bytes:
    im = Image.new("RGB", (w, h), color)
    ImageDraw.Draw(im).rectangle([w // 4, h // 4, 3 * w // 4, 3 * h // 4], fill=(240, 200, 60))
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def files(tmp_path):
    """임시 환경 + fakeredis + files 스텁."""
    with testing.environment(tmp_path, service="export"):
        testing.use_fake_redis()
        stub = FilesStub()
        with testing.inprocess({"files": stub.app}):
            yield stub


@pytest.fixture
def app(files):
    from winmate_export.main import app as export_app

    return export_app



@pytest.fixture
def png():
    return png_bytes


@pytest.fixture
def no_soffice(monkeypatch):
    """LibreOffice 를 쓰지 않는 환경(SOFFICE_PATH=off — .env 에 경로가 있어도 끈다)."""
    monkeypatch.setenv("SOFFICE_PATH", "off")
