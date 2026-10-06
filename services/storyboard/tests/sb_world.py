"""시험 세계 — requirements · kb · export 가짜 + 실제 ai-tools(mock) · workspace."""
from __future__ import annotations

import json
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from winmate_common import testing

from sb_rqdata import RqStub

RQ = "rq_01JTESTREQUIREMENTE0000001"


class Recorder:
    """ASGI 감싸기 — 들어온 요청(경로 · JSON 본문)을 남긴다(ai-tools 기밀 · 웹 검색 검사용)."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.requests: list[tuple[str, dict[str, Any] | None]] = []

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        msgs, body, more = [], b"", True
        while more:
            m = await receive()
            msgs.append(m)
            body += m.get("body", b"")
            more = m.get("more_body", False)
        try:
            parsed = json.loads(body) if body else None
        except ValueError:
            parsed = None
        self.requests.append((scope["path"], parsed))
        it = iter(msgs)

        async def rcv() -> dict[str, Any]:
            try:
                return next(it)
            except StopIteration:
                return {"type": "http.disconnect"}

        await self.app(scope, rcv, send)


def kb_stub() -> FastAPI:
    app = testing.stub_app("kb")

    @app.post("/v1/query/{code}")
    async def query(code: str, body: dict = Body(default={})):  # type: ignore[no-untyped-def]
        result: dict[str, Any] = {}
        if code == "B1":
            result = {"vertical": "kr_office", "space_sequence": [{"space_type": "lobby", "name": "로비"}], "scenes": []}
        return {"pattern": code, "result": result, "decision_hint": "auto", "evidence_paths": [], "candidates": []}

    return app


class ExportStub:
    def __init__(self) -> None:
        self.payloads: list[dict[str, Any]] = []
        app = testing.stub_app("export")

        @app.post("/v1/exports", status_code=201)
        async def create(body: dict = Body(...)):  # type: ignore[no-untyped-def]
            self.payloads.append(body)
            ext = body["format"]
            name = f"{body.get('filename') or 'file'}.{ext}"
            f = {"id": f"file_{len(self.payloads):026d}", "name": name, "mime": "application/octet-stream", "size": 1234,
                 "url": f"/api/files/v1/files/file_{len(self.payloads)}/content"}
            return JSONResponse({"export_id": f"exp_{len(self.payloads)}", "status": "done", "file": f, "files": [f],
                                 "template_codes": [], "slide_count": 3, "warnings": []}, status_code=201)

        self.app = app


class World:
    def __init__(self) -> None:
        self.rq = RqStub()
        self.rq.add(RQ, 2)
        self.ai = Recorder(testing.load_service_app("ai-tools"))
        self.export = ExportStub()
        self.apps: dict[str, Any] = {"ai-tools": self.ai, "kb": kb_stub(), "requirements": self.rq.app,
                                     "export": self.export.app, "workspace": testing.load_service_app("workspace")}


