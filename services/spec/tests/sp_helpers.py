"""spec 테스트 도우미(sp_helpers) — 06-spec §9 공통 전제.

- 고정 시계 `2026-10-06T01:00:00Z`(KST 10:00), DATA_DIR 임시 폴더, fakeredis, 계약 검증 strict.
- 플랫폼 실제 앱(in-process): kb(실데이터, 결정적) · files · jobs · workspace · export.
- ai-tools: 입력으로 고르는 스텁(`AIStub`) — task + 프롬프트 글자로 고정 응답, 호출 본문(confidential)을 기록.
  (ai-tools mock 고정 응답 파일은 입력과 무관하게 task 별 하나라서, 같은 task 에 입력별 응답이 필요한 수용 기준은 스텁으로.)
- requirements: 계약 모양 스텁(`RQStub`) — 실제 앱 통합은 test_integration_requirements.py.
- 카탈로그: 기본 `kb` 어댑터, `CAT_FIX` 는 fixture 어댑터(tests/fixtures/cat_fix.py 가 만든 JSON).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from winmate_common import testing

FIXED_NOW = "2026-10-06T01:00:00Z"
MOCKS = Path(__file__).resolve().parents[3] / "mocks" / "ai-tools"


# ── ai-tools 스텁 ─────────────────────────────────────────

class AIStub:
    """`on(task, response, when=글자)` — 프롬프트(메시지 전체 JSON)에 `when` 이 들어 있으면 그 응답. 나중에 넣은 규칙이 먼저."""

    def __init__(self) -> None:
        self.rules: list[tuple[str, str | None, dict[str, Any]]] = []
        self.calls: list[dict[str, Any]] = []
        self._seq: dict[str, int] = {}
        self.app = testing.stub_app("ai-tools")
        app = self.app

        @app.post("/v1/llm/chat")
        async def chat(request: Request) -> JSONResponse:
            body = await request.json()
            text = json.dumps(body.get("messages"), ensure_ascii=False)
            return self._answer(body, text, kind="chat")

        @app.post("/v1/i2t/analyze")
        async def i2t(request: Request) -> JSONResponse:
            body = await request.json()
            return self._answer(body, body.get("prompt") or "", kind="i2t")

    def _mock_file(self, task: str) -> dict[str, Any] | None:
        """규칙이 없으면 mock 고정 응답 파일(mocks/ai-tools/<task>.json — 시연과 같은 값). responses 는 task 별 호출 순서대로."""
        p = MOCKS / f"{task}.json"
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        if "responses" in data:
            n = self._seq.get(task, 0)
            self._seq[task] = n + 1
            return data["responses"][n % len(data["responses"])]
        return data

    def on(self, task: str, response: dict[str, Any], *, when: str | None = None) -> None:
        self.rules.insert(0, (task, when, response))

    def calls_of(self, task: str) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["task"] == task]

    def _answer(self, body: dict[str, Any], text: str, *, kind: str) -> JSONResponse:
        task = body.get("task") or ""
        self.calls.append({"task": task, "confidential": bool(body.get("confidential")), "text": text, "kind": kind})
        resp = next((r for t, w, r in self.rules if t == task and (w is None or w in text)), None)
        if resp is None:
            resp = self._mock_file(task)
        if resp is None:
            resp = {"json": {}}
        if "error" in resp:
            e = resp["error"]
            return JSONResponse({"error": {"code": e.get("code", "UPSTREAM_UNAVAILABLE"), "message": e.get("message", "오류"), "details": {}}},
                                status_code=int(e.get("status", 503)))
        out: dict[str, Any] = {"call_id": f"call_{len(self.calls)}", "provider": "stub", "model": "stub", "latency_ms": 1}
        if "json" in resp:
            out["json"] = resp["json"]
            out["content"] = json.dumps(resp["json"], ensure_ascii=False)
        else:
            out["content"] = resp.get("content", "")
        return JSONResponse(out)


# ── requirements 스텁(01-requirements §5.8 · §5.9 계약 모양) ─────────

class RQStub:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []        # [{id, code, text, short, entities}]
        self.project_id: str | None = None
        self.links: list[dict[str, Any]] = []
        self.app = testing.stub_app("requirements")
        app = self.app

        @app.get("/v1/requirements")
        async def list_rq(request: Request) -> JSONResponse:
            pid = request.query_params.get("project_id")
            items = []
            if self.items and (pid is None or pid == self.project_id):
                items = [{"id": "rq_01TEST", "title": "C 물류센터 요구사항", "customer_name": "C 물류센터", "project_name": None,
                          "project_id": self.project_id, "list_state": "saved", "state_label": "저장됨", "version": 1,
                          "has_unsaved_changes": False, "keyman_count": 0, "item_count": len(self.items), "open_question_count": 0,
                          "updated_at": FIXED_NOW, "saved_at": FIXED_NOW, "route": "/requirements/rq_01TEST", "active_deep": None,
                          "owner": {"id": "u_test", "name": "테스터"}}]
            return JSONResponse({"items": items, "next_cursor": None})

        @app.get("/v1/requirements/{rq_id}/versions/{n}")
        async def version(rq_id: str, n: str) -> JSONResponse:
            return JSONResponse(self.snapshot(rq_id))

        @app.put("/v1/requirements/{rq_id}/links/{service_name}/{ref_id}")
        async def put_link(rq_id: str, service_name: str, ref_id: str, request: Request) -> JSONResponse:
            body = await request.json()
            self.links.append({"rq_id": rq_id, "service": service_name, "ref_id": ref_id, **body})
            return JSONResponse({"requirement_id": rq_id, "service": service_name, "ref_id": ref_id, "title": body.get("title"),
                                 "route": body.get("route"), "rq_version": body.get("rq_version", 1),
                                 "depends_on": [{"target": d["target"], "places": [{"code": None, "label": p.get("label", "")}
                                                                                   for p in d.get("places") or []]}
                                                for d in body.get("depends_on") or []],
                                 "sync_state": "up_to_date", "pending_version": None, "created_at": FIXED_NOW, "updated_at": FIXED_NOW})

    def snapshot(self, rq_id: str) -> dict[str, Any]:
        field = {"value": None, "source": None, "derived_from": None, "alternatives": [], "updated_at": None, "rev": 0}
        flat = [{"id": it["id"], "code": it["code"], "text": it["text"], "short": it.get("short"), "keyman_id": None, "keyman_name": None,
                 "keyman_weight": None, "needs_confirmation": False, "evidence": [{"file_id": "file_rfp", "name": "RFP.pdf", "type_label": "PDF"}],
                 "entities": it.get("entities") or [],
                 "source": {"kind": "file", "file_id": "file_rfp", "file_label": "PDF", "file_name": "RFP.pdf", "locator": "p.3",
                            "quote": it["text"], "session_id": None, "reply_id": None, "job_id": None, "service": None}}
                for it in self.items]
        return {"requirement_id": rq_id, "version": 1, "created_at": FIXED_NOW, "created_by": {"id": "u_test", "name": "테스터"},
                "reason": "direct", "note": None, "summary": "", "change_count": 0, "title": "요구사항", "project_id": self.project_id,
                "project_name": None, "customer_name": "C 물류센터", "final_audience": None, "item_count": len(flat), "keyman_count": 0,
                "open_question_count": 0, "latest_version": 1,
                "snapshot": {"form": {"project_name": field, "customer_name": field, "final_audience": field, "author_note": field,
                                      "author_note_internal": True, "keymen": [], "weights_mode": "equal_default"},
                             "context": {"vertical": None, "spaces": [], "products": [], "solutions": [], "scale_text": None,
                                         "deadline_text": None, "language": None},
                             "keymen": [], "items_flat": flat, "customer_questions": [],
                             "source_files": [{"file_id": "file_rfp", "name": "RFP.pdf", "type_label": "PDF"}],
                             "author_note": {"value": None, "internal": True}}}


# ── CAT_FIX ──────────────────────────────────────────────

QM55C, QB55C, QH55C, QM65C = "LH55QMCEBGCXKR", "LH55QBCEBGCXKR", "LH55QHCEBGCXKR", "LH65QMCEBGCXKR"
QM55R = "LH55QMREBGCXKR"     # 테스트 전용 가짜 코드(KB 에 없음) — 06-spec §9 CAT_FIX


def cat_fix(version: str = "2026-09", *, qm55r_discontinued: bool | None = None, qb55c_brightness: str | None = None,
            detected_at: str | None = None) -> dict[str, Any]:
    """CAT_FIX(테스트 값 — 실제 스펙 아님). 2026-09 · 2026-10(QM55R 단종 표시) · 2026-11(QB55C 밝기 350 → 400)."""
    disc = version >= "2026-10" if qm55r_discontinued is None else qm55r_discontinued
    qb: dict[str, Any] = {"warranty_years": 3}
    if qb55c_brightness or version >= "2026-11":
        qb["set"] = {"디스플레이 › 밝기 (Typ)": qb55c_brightness or "400 nit"}
    qm55r: dict[str, Any] = {"base": QM55C, "display_name": "QM55R", "in_catalog": True,
                             "remove": ["전원 › 소비전력 (On Mode)", "전원 › 소비전력 (Sleep Mode)"]}
    if disc:
        qm55r["lifecycle"] = {"status": "discontinued", "successor_model_code": QM55C, "source_label": "사내 제품 카탈로그", "as_of": "2026-10-01"}
    return {"version": version, "detected_at": detected_at, "policy_label": "국내 보증 정책 문서", "policy_as_of": "2026-08-01",
            "policy_warranty": {QM55C: 2, QB55C: 3},
            "models": {QM55C: {"set": {"전원 › 소비전력 (Typical)": "120 W", "전원 › 소비전력 (Max)": "180 W"}, "warranty_years": 3},
                       QB55C: qb, QM55R: qm55r}}


async def upload(name: str, data: bytes, mime: str, *, confidential: bool = True) -> dict[str, Any]:
    """사용자 업로드 흉내(files 실제 앱) → FileMeta."""
    from winmate_common.platform import save_file
    return await save_file(name, data, mime, source="upload", confidential=confidential)


PDF = "application/pdf"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


FAM_QMC, FAM_QBC, FAM_QHC = "fam_G000182628", "fam_G000182632", "fam_G000182638"
KB_FIX_55_MODELS = {FAM_QHC: [QH55C], FAM_QMC: [QM55C, QM65C], FAM_QBC: [QB55C]}


def use_kb_fix_55(monkeypatch: Any) -> None:
    """KB_FIX_55(§9 전제) — C2 가 QHC · QMC · QBC 를 돌려주고, 제품군 모델은 보드 4모델, QHC 솔루션은 VXT 만."""
    from winmate_spec.catalog import catalog
    cat = catalog()

    async def c2(**body: Any) -> dict[str, Any]:
        return {"result": {"families": [{"id": FAM_QHC, "score": 0.62}, {"id": FAM_QMC, "score": 0.61}, {"id": FAM_QBC, "score": 0.55}]}}

    orig_family = cat.family
    orig_specs = cat.specs

    async def family(fid: str) -> dict[str, Any]:
        fe = dict(await orig_family(fid))
        keep = KB_FIX_55_MODELS.get(fid)
        if keep is not None:
            fe["models"] = [m for m in fe.get("models") or [] if m.get("model_code") in keep]
        return fe

    async def specs(codes: list[str]) -> dict[str, Any]:
        import copy
        out = copy.deepcopy(await orig_specs(codes))
        if QH55C in out:
            out[QH55C]["solutions"] = [s for s in out[QH55C].get("solutions") or [] if "vxt" in (s.get("name") or "").lower()]
            out[QH55C]["provides"] = [{**p, "evidence": (p.get("evidence") or "").replace("MagicINFO와 ", "").replace("MagicINFO", "")}
                                      for p in out[QH55C].get("provides") or []]
        return out

    monkeypatch.setattr(cat, "c2", c2)
    monkeypatch.setattr(cat, "family", family)
    monkeypatch.setattr(cat, "specs", specs)
