"""mi 테스트 공용 — 임시 DATA_DIR · fakeredis · in-process 서비스(가짜 ai-tools · files 스텁 · 실제 kb(+업종 판별 덮어쓰기) · workspace · export).

- FakeAI: ai-tools 계약대로 응답하는 가짜. task 마다 응답을 정하고(dict · list(차례) · 함수 · 오류) 모든 호출을 기록한다(confidential · 검색어 · 프롬프트).
- KbOverlay: 실제 kb 앱 앞에 붙여 `POST /v1/segments/classify` 만 정한 값으로(업종 확신도를 정확히 맞추려고).
- 실행일 D = 2026-10-06(MI_TODAY).
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(__file__))   # --import-mode=importlib → 시나리오 도우미(mi_scenario.py)를 import 할 수 있게

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from winmate_common import testing
from winmate_common.ids import new_id, now_iso


# ── 가짜 ai-tools ────────────────────────────────────────
def _limits() -> dict[str, Any]:
    cl = {"rpm": 600, "daily": 100000, "max_concurrency": 8, "timeout_s": 60.0}
    return {"enforced": False, "llm": cl, "i2t": cl, "t2i": cl, "websearch": cl}


class FakeAI:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.llm: dict[str, Any] = {}
        self.web: dict[str, Any] = {}
        self.pages: dict[str, dict[str, Any]] = {}
        self.i2t: dict[str, Any] = {}
        self.return_sources = False
        self.search_provider = "none"
        self.websearch_available = True
        self.counters: dict[str, int] = {}
        app = testing.stub_app("ai-tools")
        self.app = app

        @app.get("/v1/capabilities")
        async def caps() -> dict[str, Any]:
            self.calls.append({"kind": "caps"})
            return {
                "mode": "mock",
                "llm": {"provider": "fake", "model": "fake", "max_input_tokens": 200000, "max_output_tokens": 8000,
                        "supports": {"json_schema": True, "tools": True, "streaming": False}, "allow_confidential": True, "available": True},
                "i2t": {"provider": "fake", "model": "fake", "max_images_per_call": 4, "max_image_side_px": 2048,
                        "supports": {"json_schema": True, "bbox": True}, "allow_confidential": True, "available": True},
                "t2i": {"provider": "fake", "model": "fake", "max_side_px": 2048, "default_aspect": "16:9", "max_reference_images": 2, "images_per_call": 2,
                        "supports": {"reference_images": True, "edit": True, "mask": True}, "allow_confidential": True, "available": True},
                "websearch": {"provider": "fake", "model": "fake", "return_sources": self.return_sources, "allow_confidential": False,
                              "available": self.websearch_available},
                "search_api": {"provider": self.search_provider, "available": self.search_provider != "none"},
                "fetch": {"enabled": True},
                "embedding": {"provider": "none", "model": "", "available": False, "dim": None},
                "usage_today": {"llm": 0, "i2t": 0, "t2i": 0, "websearch": 0},
                "limits": _limits(),
            }

        @app.post("/v1/llm/chat")
        async def chat(request: Request) -> Response:
            body = await request.json()
            task = body["task"]
            prompt = "\n".join(m.get("content", "") if isinstance(m.get("content"), str) else json.dumps(m.get("content"), ensure_ascii=False)
                               for m in body.get("messages") or [])
            self.calls.append({"kind": "llm", "task": task, "confidential": bool(body.get("confidential")), "prompt": prompt})
            spec = self._pick(self.llm, task, body)
            if inspect.isawaitable(spec):
                spec = await spec
            if isinstance(spec, dict) and "error" in spec:
                e = spec["error"]
                return JSONResponse({"error": {"code": e["code"], "message": e.get("message", ""), "details": {}}}, status_code=e["status"])
            data = spec if spec is not None else {}
            return JSONResponse({"call_id": new_id("call"), "provider": "fake", "model": "fake", "json": data, "content": json.dumps(data, ensure_ascii=False)})

        @app.post("/v1/websearch")
        async def websearch(request: Request) -> Response:
            body = await request.json()
            task, q = body["task"], body["query"]
            self.calls.append({"kind": "websearch", "task": task, "query": q, "confidential": bool(body.get("confidential"))})
            spec = self._pick(self.web, task, body)
            if inspect.isawaitable(spec):
                spec = await spec
            if isinstance(spec, dict) and "error" in spec:
                e = spec["error"]
                return JSONResponse({"error": {"code": e["code"], "message": e.get("message", ""), "details": {}}}, status_code=e["status"])
            spec = spec or {"summary": ""}
            out = {"call_id": new_id("call"), "provider": "fake", "model": "fake", "summary": spec.get("summary", ""), "queries": [q],
                   "returned_sources": self.return_sources}
            if self.return_sources:
                out["sources"] = spec.get("sources") or []
            return JSONResponse(out)

        @app.post("/v1/search")
        async def search(request: Request) -> dict[str, Any]:
            body = await request.json()
            self.calls.append({"kind": "search", "query": body.get("query")})
            return {"available": False, "provider": "none", "results": []}

        @app.post("/v1/fetch")
        async def fetch(request: Request) -> dict[str, Any]:
            body = await request.json()
            url = body["url"]
            self.calls.append({"kind": "fetch", "url": url})
            pg = self.pages.get(url)
            if not pg:
                return {"url": url, "final_url": url, "status": 404, "allowed": True, "reason": "not found", "fetched_at": now_iso(), "text": ""}
            text = pg.get("text") or "\n".join(pg.get("pages") or [])
            out = {"url": url, "final_url": pg.get("final_url") or url, "status": 200, "allowed": True, "title": pg.get("title") or url, "text": text,
                   "fetched_at": now_iso(), "content_type": "text/html", "content_hash": hashlib.sha256(text.encode()).hexdigest()[:16]}
            if pg.get("pages"):
                out["pages"] = pg["pages"]
            if pg.get("published_at"):
                out["published_at"] = pg["published_at"]
            return out

        @app.post("/v1/i2t/analyze")
        async def i2t(request: Request) -> dict[str, Any]:
            body = await request.json()
            self.calls.append({"kind": "i2t", "task": body.get("task"), "confidential": bool(body.get("confidential"))})
            spec = self._pick(self.i2t, body.get("task", ""), body) or {}
            return {"call_id": new_id("call"), "provider": "fake", "model": "fake", "content": spec.get("content", "")}

    def _pick(self, table: dict[str, Any], task: str, body: dict[str, Any]) -> Any:
        spec = table.get(task)
        if spec is None:
            spec = next((v for k, v in table.items() if k.endswith("*") and task.startswith(k[:-1])), None)
        if callable(spec):
            spec = spec(body)
        if isinstance(spec, list):
            i = self.counters.get(task, 0)
            self.counters[task] = i + 1
            spec = spec[i] if i < len(spec) else spec[-1]
        return spec

    # 기록 조회
    def llm_calls(self, task: str | None = None) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["kind"] == "llm" and (task is None or c["task"] == task or (task.endswith("*") and c["task"].startswith(task[:-1])))]

    def web_calls(self, task: str | None = None) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["kind"] == "websearch" and (task is None or c["task"] == task)]

    def fetch_calls(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["kind"] == "fetch"]

    def reset_calls(self) -> None:
        self.calls.clear()


# ── files 스텁 ───────────────────────────────────────────
class FilesStub:
    def __init__(self) -> None:
        self.metas: dict[str, dict[str, Any]] = {}
        self.parsed: dict[str, dict[str, Any]] = {}
        self.blobs: dict[str, bytes] = {}
        app = testing.stub_app("files")
        self.app = app

        def nf() -> JSONResponse:
            return JSONResponse({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}, status_code=404)

        @app.get("/v1/files/{file_id}")
        async def meta(file_id: str) -> Response:
            return JSONResponse(self.metas[file_id]) if file_id in self.metas else nf()

        @app.get("/v1/files/{file_id}/parsed")
        async def parsed(file_id: str) -> Response:
            return JSONResponse(self.parsed[file_id]) if file_id in self.parsed else nf()

        @app.get("/v1/files/{file_id}/pages/{n}/image")
        async def page_image(file_id: str, n: int) -> Response:
            return Response(b"\x89PNG\r\n\x1a\nfake", media_type="image/png")

        @app.post("/v1/files/bytes", status_code=201)
        async def save_bytes(request: Request) -> JSONResponse:
            import base64

            body = await request.json()
            data = base64.b64decode(body["data_b64"])
            m = self._meta(body["name"], body.get("mime") or "application/octet-stream", len(data), bool(body.get("confidential")))
            self.blobs[m["id"]] = data
            return JSONResponse(m, status_code=201)

        @app.get("/v1/files/{file_id}/content")
        async def content(file_id: str) -> Response:
            return Response(self.blobs.get(file_id, b""), media_type=self.metas.get(file_id, {}).get("mime", "application/octet-stream"))

    def _meta(self, name: str, mime: str, size: int, confidential: bool) -> dict[str, Any]:
        fid = new_id("file")
        kind = "pdf" if name.endswith(".pdf") else ("xlsx" if name.endswith(".xlsx") else ("pptx" if name.endswith(".pptx") else "text"))
        m = {"id": fid, "name": name, "mime": mime, "size": size, "sha256": hashlib.sha256(name.encode()).hexdigest(), "kind": kind, "source": "upload",
             "confidential": confidential, "owner": "u_test", "owner_name": "테스터", "project_id": None, "parent_id": None, "created_at": now_iso(),
             "url": f"/api/files/v1/files/{fid}/content", "thumb_url": f"/api/files/v1/files/{fid}/thumbnail", "pages": None, "meta": {}}
        self.metas[fid] = m
        return m

    def add(self, name: str, pages: list[str], *, confidential: bool = False, scanned: list[int] | None = None) -> str:
        m = self._meta(name, "application/pdf", sum(len(p) for p in pages), confidential)
        m["pages"] = len(pages)
        self.parsed[m["id"]] = {"file_id": m["id"], "kind": "pdf", "title": name, "text": "\n".join(pages), "page_count": len(pages),
                                "pages": [{"no": i + 1, "text": t} for i, t in enumerate(pages)], "meta": {},
                                "warnings": [f"scanned_page:{n}" for n in scanned or []], "parser_version": "test"}
        return m["id"]


# ── kb 덮어쓰기 ──────────────────────────────────────────
class KbOverlay:
    """실제 kb 앱 + `POST /v1/segments/classify` 덮어쓰기(업종 확신도 조절)."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.classify: dict[str, tuple[float, float]] | None = None    # code → (kb_score, clue_score)
        self.clues: dict[str, list[str]] = {}

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"] == "/v1/segments/classify" and self.classify is not None:
            while True:
                msg = await receive()
                if not msg.get("more_body"):
                    break
            items = [{"code": c, "id": f"wm_{c.lower()}", "name": c, "kb_score": k, "clue_score": cl,
                      "clues": [{"text": t, "code": c, "weight": 0.5} for t in self.clues.get(c, [])], "similar_case_ids": [], "a2_match": None,
                      "case_ratio": 0.0, "has_kr_mapping": True} for c, (k, cl) in self.classify.items()]
            resp = JSONResponse({"items": items, "a2": {}, "similar_case_ids": [], "method": "test", "needs_confirmation": []})
            await resp(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def set_conf(self, conf: dict[str, float], clues: dict[str, list[str]] | None = None) -> None:
        """kb · 단서 점수를 LLM p 와 같게 두면 conf = p 그대로(0.5p + 0.3p + 0.2p)."""
        self.classify = {c: (v, v) for c, v in conf.items()}
        self.clues = clues or {}


# ── 환경 ─────────────────────────────────────────────────
@dataclass
class Env:
    c: Any
    ai: FakeAI
    files: FilesStub
    kb: KbOverlay
    apps: dict[str, Any] = field(default_factory=dict)

    async def drain(self, max_jobs: int = 50) -> int:
        from winmate_mi.worker import HANDLERS

        return await testing.drain_jobs("mi", HANDLERS, max_jobs=max_jobs)

    async def job(self, job_id: str) -> Any:
        from winmate_common.jobs import jobs

        return await jobs().get(job_id)

    async def events(self, job_id: str) -> list[dict[str, Any]]:
        from winmate_common.jobs import jobs

        return [e for _, e in await jobs().events(job_id, count=2000)]


@pytest.fixture
async def env(tmp_path):
    with testing.environment(tmp_path, service="mi", MI_TODAY="2026-10-06", MI_ORGANIZE_CONCURRENCY="2"):
        testing.use_fake_redis()
        from winmate_mi import aix, kbx

        kbx.clear_cache()
        aix.reset_caps()
        fake = FakeAI()
        files = FilesStub()
        kb = KbOverlay(testing.load_service_app("kb"))
        apps = {"ai-tools": fake.app, "files": files.app, "kb": kb, **testing.platform_apps("workspace", "export")}
        with testing.inprocess(apps):
            from winmate_mi.main import app

            async with testing.api_client(app) as c:
                yield Env(c=c, ai=fake, files=files, kb=kb, apps=apps)
