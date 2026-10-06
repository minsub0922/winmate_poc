"""competitor 테스트 공용 — 임시 DATA_DIR · fakeredis · in-process 서비스.

- `env`  : 가짜 ai-tools(FakeAI — task 마다 응답 · 호출 기록) · files 스텁 · 실제 kb(+업종 판별 덮어쓰기) · 정의서 스텁 · 실제 workspace · export.
           수용 기준(AC-CA-*)을 정확한 값으로 시험한다.
- `demo` : 플랫폼 실제 앱 묶음(ai-tools mock = mocks/ai-tools/ca.*.json · kb 실데이터 · files · jobs · workspace · export) + 실제 requirements · mi.
           mock 데모 한 바퀴 · 다른 서비스와의 통합을 시험한다.
- 실행일 D = 2026-10-06(CA_TODAY).
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(__file__))

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from winmate_common import testing
from winmate_common.ids import new_id, now_iso


def _limits() -> dict[str, Any]:
    cl = {"rpm": 600, "daily": 100000, "max_concurrency": 8, "timeout_s": 60.0}
    return {"enforced": False, "llm": cl, "i2t": cl, "t2i": cl, "websearch": cl}


class FakeAI:
    """ai-tools 계약대로 응답하는 가짜. llm · web 표: task → dict | list(차례) | 함수(body) | {"error": {status, code}}."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.llm: dict[str, Any] = {}
        self.web: dict[str, Any] = {}
        self.pages: dict[str, dict[str, Any]] = {}
        self.return_sources = False
        self.websearch_available = True
        self.counters: dict[str, int] = {}
        app = testing.stub_app("ai-tools")
        self.app = app

        @app.get("/v1/capabilities")
        async def caps() -> dict[str, Any]:
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
                "search_api": {"provider": "none", "available": False},
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
            spec = self._pick(self.llm, task, {**body, "prompt": prompt})
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
            self.calls.append({"kind": "websearch", "task": task, "query": q})
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
            text = pg.get("text") or ""
            out = {"url": url, "final_url": pg.get("final_url") or url, "status": 200, "allowed": True, "title": pg.get("title") or url, "text": text,
                   "fetched_at": now_iso(), "content_type": "text/html", "content_hash": hashlib.sha256(text.encode()).hexdigest()[:16]}
            if pg.get("published_at"):
                out["published_at"] = pg["published_at"]
            return out

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

    def llm_calls(self, task: str | None = None) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["kind"] == "llm" and (task is None or c["task"] == task)]

    def web_calls(self, task: str | None = None) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["kind"] == "websearch" and (task is None or c["task"] == task)]

    def fetch_calls(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["kind"] == "fetch"]

    def reset_calls(self) -> None:
        self.calls.clear()


class FilesStub:
    def __init__(self) -> None:
        self.parsed: dict[str, dict[str, Any]] = {}
        self.metas: dict[str, dict[str, Any]] = {}
        app = testing.stub_app("files")
        self.app = app

        def nf() -> JSONResponse:
            return JSONResponse({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}, status_code=404)

        @app.get("/v1/files/{file_id}/parsed")
        async def parsed(file_id: str) -> Response:
            return JSONResponse(self.parsed[file_id]) if file_id in self.parsed else nf()

        @app.get("/v1/files/{file_id}")
        async def meta(file_id: str) -> Response:
            return JSONResponse(self.metas[file_id]) if file_id in self.metas else nf()

    def add(self, name: str, text: str) -> str:
        fid = new_id("file")
        self.metas[fid] = {"id": fid, "name": name, "mime": "application/pdf", "size": len(text), "sha256": "x", "kind": "pdf", "source": "upload",
                           "confidential": False, "owner": "u_test", "owner_name": "테스터", "project_id": None, "parent_id": None, "created_at": now_iso(),
                           "url": f"/api/files/v1/files/{fid}/content", "thumb_url": None, "pages": 1, "meta": {}}
        self.parsed[fid] = {"file_id": fid, "kind": "pdf", "title": name, "text": text, "page_count": 1, "pages": [{"no": 1, "text": text}],
                            "meta": {}, "warnings": [], "parser_version": "test"}
        return fid


class KbOverlay:
    """실제 kb 앱 + `POST /v1/segments/classify` 덮어쓰기(업종 확신도 조절)."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.classify: dict[str, tuple[float, float]] | None = None

    async def __call__(self, scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"] == "/v1/segments/classify" and self.classify is not None:
            while True:
                msg = await receive()
                if not msg.get("more_body"):
                    break
            items = [{"code": c, "id": f"wm_{c.lower()}", "name": c, "kb_score": k, "clue_score": cl, "clues": [], "similar_case_ids": [], "a2_match": None,
                      "case_ratio": 0.0, "has_kr_mapping": True} for c, (k, cl) in self.classify.items()]
            resp = JSONResponse({"items": items, "a2": {}, "similar_case_ids": [], "method": "test", "needs_confirmation": []})
            await resp(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def set_conf(self, conf: dict[str, float]) -> None:
        """kb · 단서 점수를 LLM p 와 같게 두면 확신도 = p 그대로(0.5p + 0.3p + 0.2p)."""
        self.classify = {c: (v, v) for c, v in conf.items()}


class RqStub:
    """requirements 스텁 — 정의서 스냅숏 · 사용 링크 기록."""

    def __init__(self) -> None:
        self.snaps: dict[str, dict[str, Any]] = {}
        self.links: list[dict[str, Any]] = []
        app = testing.stub_app("requirements")
        self.app = app

        @app.get("/v1/requirements/{rq_id}/versions/{n}")
        async def version(rq_id: str, n: str) -> Response:
            if rq_id not in self.snaps:
                return JSONResponse({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}, status_code=404)
            return JSONResponse(self.snaps[rq_id])

        @app.put("/v1/requirements/{rq_id}/links/{svc}/{ref_id}")
        async def link(rq_id: str, svc: str, ref_id: str, request: Request) -> dict[str, Any]:
            body = await request.json()
            self.links.append({"rq_id": rq_id, "service": svc, "ref_id": ref_id, **body})
            return {"requirement_id": rq_id, "service": svc, "ref_id": ref_id, "title": body.get("title"), "route": body.get("route"),
                    "rq_version": body.get("rq_version", 1), "depends_on": body.get("depends_on") or [], "sync_state": "up_to_date",
                    "pending_version": None, "created_at": now_iso(), "updated_at": now_iso()}

    def add(self, rq_id: str, *, customer: str | None, items: list[str], author_note: str | None = None, vertical: dict[str, Any] | None = None,
            spaces: list[str] | None = None, products: list[str] | None = None, solutions: list[str] | None = None, project_name: str = "A 커피 메뉴보드 교체") -> None:
        def fv(v: Any) -> dict[str, Any]:
            return {"value": v, "source": None, "derived_from": None, "alternatives": [], "updated_at": None, "rev": 1}

        self.snaps[rq_id] = {
            "requirement_id": rq_id, "version": 2, "created_at": now_iso(), "created_by": {"id": "u_test", "name": "테스터"}, "reason": "direct",
            "note": None, "summary": "", "change_count": 0, "title": project_name, "project_id": None, "project_name": project_name,
            "customer_name": customer, "final_audience": None, "item_count": len(items), "keyman_count": 1, "open_question_count": 0, "latest_version": 2,
            "snapshot": {
                "form": {"project_name": fv(project_name), "customer_name": fv(customer), "final_audience": fv(None), "author_note": fv(author_note),
                         "author_note_internal": True, "keymen": [], "weights_mode": "equal_default"},
                "context": {"vertical": vertical, "spaces": [{"id": f"sp{i}", "name": s, "item_ids": []} for i, s in enumerate(spaces or [])],
                            "products": [{"type": "category", "id": f"pr{i}", "name": s, "item_ids": []} for i, s in enumerate(products or [])],
                            "solutions": [{"id": f"so{i}", "name": s, "item_ids": []} for i, s in enumerate(solutions or [])],
                            "scale_text": None, "deadline_text": None, "language": "ko"},
                "keymen": [],
                "items_flat": [{"id": f"it{i}", "code": f"R{i + 1}", "text": t, "short": None, "keyman_id": None, "keyman_name": None,
                                "keyman_weight": 5 - i, "needs_confirmation": False, "evidence": [], "entities": [], "source": None}
                               for i, t in enumerate(items)],
                "customer_questions": [], "source_files": [], "author_note": {"value": author_note, "internal": True},
            },
        }


@dataclass
class Env:
    c: Any
    ai: FakeAI
    files: FilesStub
    kb: KbOverlay
    rq: RqStub
    apps: dict[str, Any] = field(default_factory=dict)

    async def drain(self, max_jobs: int = 50) -> int:
        from winmate_competitor.worker import HANDLERS

        return await testing.drain_jobs("competitor", HANDLERS, max_jobs=max_jobs)

    async def job(self, job_id: str) -> Any:
        from winmate_common.jobs import jobs

        return await jobs().get(job_id)

    async def events(self, job_id: str) -> list[dict[str, Any]]:
        from winmate_common.jobs import jobs

        return [e for _, e in await jobs().events(job_id, count=5000)]

    async def answer(self, job_id: str, value: Any) -> None:
        from winmate_common.jobs import jobs

        await jobs().provide_input(job_id, value)


@pytest.fixture
async def env(tmp_path):
    with testing.environment(tmp_path, service="competitor", CA_TODAY="2026-10-06", CA_ANALYZE_CONCURRENCY="2"):
        testing.use_fake_redis()
        from winmate_competitor import aix, kbx

        kbx.clear_cache()
        aix.reset_caps()
        fake = FakeAI()
        files = FilesStub()
        kb = KbOverlay(testing.load_service_app("kb"))
        rq = RqStub()
        apps = {"ai-tools": fake.app, "files": files.app, "kb": kb, "requirements": rq.app, **testing.platform_apps("workspace", "export")}
        with testing.inprocess(apps):
            from winmate_competitor.main import app

            async with testing.api_client(app) as c:
                yield Env(c=c, ai=fake, files=files, kb=kb, rq=rq, apps=apps)


@dataclass
class Demo:
    c: Any
    apps: dict[str, Any]

    async def drain(self, service: str = "competitor", max_jobs: int = 50) -> int:
        return await testing.drain_jobs(service, testing.load_service_worker(service), max_jobs=max_jobs)


@pytest.fixture
async def demo(tmp_path):
    with testing.environment(tmp_path, service="competitor", CA_TODAY="2026-10-06", WEB_FETCH_ENABLED="false"):
        testing.use_fake_redis()
        from winmate_competitor import aix, kbx

        kbx.clear_cache()
        aix.reset_caps()
        apps = {**testing.platform_apps(), "requirements": testing.load_service_app("requirements"), "mi": testing.load_service_app("mi")}
        with testing.inprocess(apps):
            from winmate_competitor.main import app

            async with testing.api_client(app) as c:
                yield Demo(c=c, apps=apps)
