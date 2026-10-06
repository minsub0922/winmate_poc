"""시험용 요구사항 정의서(보드 예시: E 자산운용 용산 AI Ready 오피스) + requirements 가짜 서비스.

가짜 서비스 응답은 contracts/requirements.json 으로 엄격 검증된다(CONTRACT_VALIDATION=strict) — 실제 계약과 같은 모양.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Request
from fastapi.responses import JSONResponse

NOW = "2026-10-06T04:40:00.000Z"

# ── 계약 맞추기: requirements 계약이 자라도(필수 필드 추가) 가짜 응답이 엄격 검증을 통과하게 빠진 필수 값을 채운다 ──
_CONTRACT = json.loads((Path(__file__).resolve().parents[3] / "contracts" / "requirements.json").read_text(encoding="utf-8"))
_S = _CONTRACT["components"]["schemas"]


def _resolve(sch: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in sch:
        sch = _S[sch["$ref"].split("/")[-1]]
    return sch


def _default(sch: dict[str, Any]) -> Any:
    sch = _resolve(sch)
    if "anyOf" in sch:
        variants = [_resolve(v) for v in sch["anyOf"]]
        if any(v.get("type") == "null" for v in variants):
            return None
        return _default(variants[0])
    if "default" in sch:
        return copy.deepcopy(sch["default"])
    if "const" in sch:
        return sch["const"]
    if "enum" in sch:
        return sch["enum"][0]
    t = sch.get("type")
    if t == "object" or "properties" in sch:
        return conform(sch, {})
    return {"array": [], "integer": 0, "number": 0, "boolean": False, "string": ""}.get(t or "", None)


def conform(sch: dict[str, Any], data: Any) -> Any:
    sch = _resolve(sch)
    if data is None:
        return None
    if "anyOf" in sch:
        for v in (_resolve(x) for x in sch["anyOf"]):
            if v.get("type") == "null":
                continue
            if isinstance(data, dict) and (v.get("type") == "object" or "properties" in v):
                return conform(v, data)
            if isinstance(data, list) and v.get("type") == "array":
                return conform(v, data)
        return data
    if isinstance(data, dict) and "properties" in sch:
        out = dict(data)
        for k, ps in sch["properties"].items():
            if k in out:
                out[k] = conform(ps, out[k])
            elif k in sch.get("required", []):
                out[k] = _default(ps)
        return out
    if isinstance(data, list) and sch.get("type") == "array" and "items" in sch:
        return [conform(sch["items"], x) for x in data]
    return data


def conform_response(path: str, method: str, status: int, data: Any) -> Any:
    op = _CONTRACT["paths"].get(path, {}).get(method.lower(), {})
    resp = (op.get("responses") or {}).get(str(status)) or {}
    sch = ((resp.get("content") or {}).get("application/json") or {}).get("schema")
    return conform(sch, data) if sch else data
KEYMEN = [
    {"id": "km_A", "name": "대표이사", "weight": 50},
    {"id": "km_B", "name": "공간컨텐츠실장", "weight": 30},
    {"id": "km_C", "name": "개발사업팀장", "weight": 20},
]
ITEMS = [
    ("RQ-01", "km_A", "사용자를 인식하고 반응하는 'AI Ready' 프라임 스마트 오피스", "AI Ready 프라임 스마트 오피스", False),
    ("RQ-02", "km_B", "오피스를 업무환경 플랫폼으로 — 입주사 서비스까지", "오피스 = 업무환경 플랫폼", False),
    ("RQ-03", "km_C", "AI 인프라를 설계 단계에 미리 반영하고 예산에 선반영", "AI 인프라 설계 · 예산 선반영", False),
    ("RQ-04", "km_B", "예측 · 반응형 공간(Connecting-AI)", "Connecting-AI 예측 · 반응형 공간", False),
    ("RQ-05", "km_A", "에너지 사용량 20% 절감(유사 건물 대비) · 실제 정량 데이터로 증빙", "에너지 절감 · 정량 데이터", True),
    ("RQ-06", "km_A", "건물 가치 · 임대 선호도 제고", "건물 가치 · 임대 선호도 제고", False),
    ("RQ-07", "km_C", "ICT 지구 테마 · 용적률 인센티브 연계", "ICT 지구 · 용적률 인센티브", False),
    ("RQ-08", "km_A", "성수 오피스보다 발전한 '최초 AI Ready' 공간으로 알리기", "성수보다 발전 · '최초 AI Ready'", False),
    ("RQ-09", "km_B", "공간별 SAC · 사이니지 · Harman 오디오 구성", "SAC · 사이니지 · Harman", False),
    ("RQ-10", "km_C", "SmartThings Pro · b.IoT · VXT 통합 운영", "SmartThings Pro · b.IoT · VXT", False),
    ("RQ-11", "km_B", "로비 안내 로봇 · Digital Twin · BLE 위치 · 안면인식 출입", "로봇 · Digital Twin · BLE · 안면인식", False),
    ("RQ-12", "km_B", "컨셉 구상과 공간 구성 지원", "컨셉 구상 · 공간 구성 지원", False),
]
SPACES = [("open_office", "사무실"), ("lobby", "로비"), ("meeting_room", "회의실"), ("lounge", "라운지"),
          ("control_room", "중앙관제실"), ("common_area", "공용공간")]
QUESTIONS = [
    ("cq_1", "'업무환경 플랫폼'에 어떤 서비스가 들어가나요?", "업무환경 플랫폼 범위", "km_B", "ri_02"),
    ("cq_2", "유사 건물 에너지 사용량 자료를 받을 수 있을까요?", "유사 건물 사용량 자료", "km_A", "ri_05"),
    ("cq_3", "최종 의사결정자는 누구인가요?", "최종 의사결정자", None, None),
    ("cq_4", "용적률 인센티브 조건을 공유해 주실 수 있을까요?", "용적률 인센티브 조건", "km_C", None),
]
AUTHOR_NOTE = "설계 단계 삼성 스펙인이 목표. 성수 Tech Ready 오피스 운영 성과를 비교 기준으로 쓰고 싶어 함."


def _field(value: str | None) -> dict[str, Any]:
    return {"value": value, "source": {"kind": "user"} if value else None, "alternatives": []}


def flat_items(changed: dict[str, str] | None = None) -> list[dict[str, Any]]:
    out = []
    names = {k["id"]: k["name"] for k in KEYMEN}
    for code, km, text, short, nc in ITEMS:
        rid = "ri_" + code[-2:]
        out.append({"id": rid, "code": code, "text": (changed or {}).get(rid, text), "short": short, "keyman_id": km,
                    "keyman_name": names[km], "needs_confirmation": nc, "evidence": [], "entities": []})
    return out


def snapshot(rq_id: str, version: int, *, final_audience: str | None = None, changed: dict[str, str] | None = None,
             note: str | None = None, open_questions: int = 4) -> dict[str, Any]:
    items = flat_items(changed)
    keymen = [{**k, "color_index": i, "order": i, "item_ids": [it["id"] for it in items if it["keyman_id"] == k["id"]]}
              for i, k in enumerate(KEYMEN)]
    qs = [{"id": q, "text": t, "short_label": s, "status": "open", "keyman_id": km,
           "target": {"kind": "item", "id": tgt} if tgt else None} for q, t, s, km, tgt in QUESTIONS[:open_questions]]
    return {
        "requirement_id": rq_id, "version": version, "created_at": NOW, "created_by": {"id": "u_test", "name": "테스터"},
        "reason": "direct", "note": note, "summary": "키맨 3 · 요구사항 12", "change_count": 0,
        "title": "E 자산운용 용산 AI Ready 오피스", "project_id": None, "project_name": "용산 업무시설 재개발 AI Ready 오피스",
        "customer_name": "E 자산운용", "final_audience": final_audience, "item_count": len(items), "keyman_count": 3,
        "open_question_count": len(qs), "latest_version": version,
        "snapshot": {
            "form": {"project_name": _field("용산 업무시설 재개발 AI Ready 오피스"), "customer_name": _field("E 자산운용"),
                     "final_audience": _field(final_audience), "author_note": _field(AUTHOR_NOTE), "author_note_internal": True,
                     "keymen": [], "weights_mode": "custom"},
            "context": {"vertical": {"top2": [{"id": "kr_office", "name": "오피스", "score": 1.0}], "ask": False},
                        "spaces": [{"id": sid, "name": name, "item_ids": []} for sid, name in SPACES],
                        "products": [], "solutions": [], "scale_text": None, "deadline_text": None, "language": "ko"},
            "keymen": keymen, "items_flat": items, "customer_questions": qs,
            "source_files": [{"file_id": "file_rfp", "name": "E자산운용_용산_RFP.pdf", "type_label": "PDF"}],
            "author_note": {"value": AUTHOR_NOTE, "internal": True},
        },
    }


def requirement(rq_id: str, version: int, *, open_questions: int = 4) -> dict[str, Any]:
    return {
        "id": rq_id, "owner": {"id": "u_test", "name": "테스터"}, "project_id": None, "title": "E 자산운용 용산 AI Ready 오피스",
        "short_title": "E 자산운용 용산 AI Ready 오피스", "version": version, "revision": 10 + version, "has_unsaved_changes": False,
        "list_state": "saved" if version else "input", "state_label": "저장됨" if version else "입력 중",
        "form": {"project_name": _field("용산 업무시설 재개발 AI Ready 오피스"), "customer_name": _field("E 자산운용"),
                 "final_audience": _field(None), "author_note": _field(AUTHOR_NOTE), "keymen": [], "weights_mode": "custom"},
        "files": [], "context": {"spaces": [], "products": [], "solutions": []}, "open_question_count": open_questions,
        "item_count": len(ITEMS), "keyman_count": 3, "active_job": None, "queued_jobs": [], "route": f"/requirements/{rq_id}",
        "created_at": NOW, "updated_at": NOW, "saved_at": NOW if version else None,
    }


class RqStub:
    """requirements 가짜 — 호출 기록(calls) · 링크 · 고객 질문(멱등)."""

    def __init__(self) -> None:
        self.versions: dict[str, dict[int, dict[str, Any]]] = {}
        self.latest: dict[str, int] = {}
        self.calls: list[tuple[str, str, Any]] = []
        self.links: dict[tuple[str, str], dict[str, Any]] = {}
        self.questions: list[dict[str, Any]] = []
        self.replies: dict[str, dict[str, Any]] = {}
        self.diffs: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
        self.version_meta: dict[tuple[str, int], dict[str, Any]] = {}   # 버전 목록의 note · change_count
        self.app = self._build()

    def add(self, rq_id: str, version: int = 2, **kw: Any) -> None:
        self.versions.setdefault(rq_id, {})
        for v in range(1, version + 1):
            self.versions[rq_id].setdefault(v, snapshot(rq_id, v, **kw))
        self.latest[rq_id] = version
        if version == 0:
            self.latest[rq_id] = 0

    def add_version(self, rq_id: str, version: int, diff: list[dict[str, Any]], **kw: Any) -> None:
        prev = self.latest[rq_id]
        self.versions[rq_id][version] = snapshot(rq_id, version, **kw)
        self.latest[rq_id] = version
        self.diffs[(rq_id, prev, version)] = diff

    def calls_of(self, method: str, prefix: str) -> list[tuple[str, str, Any]]:
        return [c for c in self.calls if c[0] == method and prefix in c[1]]

    def _build(self) -> FastAPI:
        app = FastAPI(title="stub requirements")
        stub = self

        @app.get("/v1/requirements/{rq_id}")
        async def get_rq(rq_id: str):  # type: ignore[no-untyped-def]
            stub.calls.append(("GET", f"/v1/requirements/{rq_id}", None))
            if rq_id not in stub.latest:
                return JSONResponse({"error": {"code": "NOT_FOUND", "message": "정의서 없음", "details": {}}}, status_code=404)
            return conform_response("/v1/requirements/{rq_id}", "GET", 200,
                                    requirement(rq_id, stub.latest[rq_id], open_questions=4 + len(stub.questions)))

        @app.get("/v1/requirements/{rq_id}/versions/{n}")
        async def get_version(rq_id: str, n: int):  # type: ignore[no-untyped-def]
            stub.calls.append(("GET", f"/v1/requirements/{rq_id}/versions/{n}", None))
            v = stub.versions.get(rq_id, {}).get(n)
            if v is None:
                return JSONResponse({"error": {"code": "VERSION_NOT_FOUND", "message": "버전 없음", "details": {}}}, status_code=404)
            return conform_response("/v1/requirements/{rq_id}/versions/{n}", "GET", 200, v)

        @app.get("/v1/requirements/{rq_id}/versions")
        async def list_versions(rq_id: str):  # type: ignore[no-untyped-def]
            stub.calls.append(("GET", f"/v1/requirements/{rq_id}/versions", None))
            items = []
            for n in sorted(stub.versions.get(rq_id, {}), reverse=True):
                meta = stub.version_meta.get((rq_id, n)) or {}
                items.append({"version": n, "created_at": NOW, "created_by": {"id": "u_test", "name": "테스터"}, "reason": "edit",
                              "note": meta.get("note"), "summary": "키맨 3 · 요구사항 12", "change_count": int(meta.get("change_count") or 0)})
            return conform_response("/v1/requirements/{rq_id}/versions", "GET", 200, {"items": items, "next_cursor": None})

        @app.get("/v1/requirements/{rq_id}/diff")
        async def diff(rq_id: str, request: Request):  # type: ignore[no-untyped-def]
            # 'from' 은 파이썬 예약어라 쿼리를 직접 읽는다
            frm = int(request.query_params.get("from", "0"))
            to = int(request.query_params.get("to", "0"))
            stub.calls.append(("GET", f"/v1/requirements/{rq_id}/diff", {"from": frm, "to": to}))
            return conform_response("/v1/requirements/{rq_id}/diff", "GET", 200,
                                    {"from_version": frm, "to_version": to, "changes": stub.diffs.get((rq_id, frm, to), [])})

        @app.get("/v1/requirements/{rq_id}/links")
        async def links(rq_id: str):  # type: ignore[no-untyped-def]
            stub.calls.append(("GET", f"/v1/requirements/{rq_id}/links", None))
            return conform_response("/v1/requirements/{rq_id}/links", "GET", 200,
                                    {"items": [lk for (r, _), lk in stub.links.items() if r == rq_id]})

        @app.put("/v1/requirements/{rq_id}/links/{service_name}/{ref_id}")
        async def put_link(rq_id: str, service_name: str, ref_id: str, body: dict = Body(...)):  # type: ignore[no-untyped-def]
            stub.calls.append(("PUT", f"/v1/requirements/{rq_id}/links/{service_name}/{ref_id}", copy.deepcopy(body)))
            old = stub.links.get((rq_id, ref_id)) or {}
            pending = old.get("pending_version")
            state = "up_to_date" if not pending or body["rq_version"] >= pending else "pending"
            link = {"requirement_id": rq_id, "service": service_name, "ref_id": ref_id, "title": body.get("title"),
                    "route": body.get("route"), "rq_version": body["rq_version"], "depends_on": body.get("depends_on") or [],
                    "sync_state": state, "pending_version": None if state == "up_to_date" else pending,
                    "created_at": NOW, "updated_at": NOW}
            stub.links[(rq_id, ref_id)] = link
            return conform_response("/v1/requirements/{rq_id}/links/{service_name}/{ref_id}", "PUT", 200, link)

        @app.post("/v1/requirements/{rq_id}/customer-questions", status_code=201)
        async def add_q(rq_id: str, body: dict = Body(...)):  # type: ignore[no-untyped-def]
            stub.calls.append(("POST", f"/v1/requirements/{rq_id}/customer-questions", copy.deepcopy(body)))
            origin = body.get("origin") or {}
            same = next((q for q in stub.questions if q["text"] == body["text"] and q["origin"].get("ref_id") == origin.get("ref_id")),
                        None)
            if same:
                return JSONResponse(conform_response("/v1/requirements/{rq_id}/customer-questions", "POST", 201, same), status_code=200)
            q = {"id": f"cq_sb{len(stub.questions) + 1}", "requirement_id": rq_id, "text": body["text"],
                 "short_label": body.get("short_label"), "keyman_id": body.get("keyman_id"), "target": body.get("target"),
                 "origin": {"kind": origin.get("kind") or "storyboard", "service": origin.get("service"), "ref_id": origin.get("ref_id"),
                            "place_label": origin.get("place_label")},
                 "status": "open", "include_in_mail": True, "answer": None, "created_at": NOW, "updated_at": None}
            stub.questions.append(q)
            return conform_response("/v1/requirements/{rq_id}/customer-questions", "POST", 201, q)

        @app.get("/v1/requirements/{rq_id}/replies/{rid}")
        async def reply(rq_id: str, rid: str):  # type: ignore[no-untyped-def]
            stub.calls.append(("GET", f"/v1/requirements/{rq_id}/replies/{rid}", None))
            return conform_response("/v1/requirements/{rq_id}/replies/{rid}", "GET", 200, stub.replies[rid])

        return app

    def mark_pending(self, rq_id: str, sb_id: str, version: int) -> None:
        lk = self.links[(rq_id, sb_id)]
        lk["sync_state"] = "pending"
        lk["pending_version"] = version


def reply(rq_id: str, rid: str) -> dict[str, Any]:
    return {"id": rid, "requirement_id": rq_id, "base_version": 2, "status": "ready", "text": "안녕하세요, E 자산운용 공간컨텐츠실입니다.",
            "file_ids": [], "files": [], "matches": [], "version_note": "11/11 회의 반영",
            "changes": [
                {"id": "ch_1", "target": {"kind": "item", "id": "ri_02"}, "label": "공간컨텐츠실장", "before_display": "업무환경 플랫폼",
                 "after_display": "입주사 앱 · 공용 공간 예약 · 방문객 안내", "ops": [], "resolves_question_ids": ["cq_1"],
                 "evidence_file_ids": [], "selected": True},
                {"id": "ch_2", "target": {"kind": "field", "id": "final_audience"}, "label": "최종 제안대상", "before_display": None,
                 "after_display": "대표이사 · 투자심의위원 2", "ops": [], "resolves_question_ids": ["cq_3"], "evidence_file_ids": [],
                 "selected": True},
            ],
            "storyboard_impact": {"count": 2, "links": []}, "applied_version": None, "job_id": None, "error": None,
            "created_at": NOW, "updated_at": NOW}
