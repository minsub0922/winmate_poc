"""시험용 가짜 서비스(§9.0 보드 예시: A 커피 프랜차이즈) + ai-tools 기록 프록시.

- 완성된 서비스(requirements · storyboard · mi · spec · image) 가짜 응답은 그 계약으로 엄격 검증된다 → conform() 으로 빠진 필수 값을 채운다.
- 만드는 중인 서비스(competitor · vp · birdseye · scenario)는 시나리오 문서 §8 모양을 흉내 낸다(계약이 생기면 검증된다).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

ROOT = Path(__file__).resolve().parents[3]
_CONTRACTS: dict[str, dict[str, Any]] = {}


def _contract(svc: str) -> dict[str, Any]:
    if svc not in _CONTRACTS:
        p = ROOT / "contracts" / f"{svc}.json"
        _CONTRACTS[svc] = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _CONTRACTS[svc]


def _resolve(c: dict[str, Any], sch: dict[str, Any]) -> dict[str, Any]:
    while isinstance(sch, dict) and "$ref" in sch:
        sch = c.get("components", {}).get("schemas", {}).get(sch["$ref"].split("/")[-1], {})
    return sch or {}


def _default(c: dict[str, Any], sch: dict[str, Any]) -> Any:
    sch = _resolve(c, sch)
    if "anyOf" in sch:
        vs = [_resolve(c, v) for v in sch["anyOf"]]
        if any(v.get("type") == "null" for v in vs):
            return None
        return _default(c, vs[0])
    if "default" in sch:
        return copy.deepcopy(sch["default"])
    if "const" in sch:
        return sch["const"]
    if "enum" in sch:
        return sch["enum"][0]
    t = sch.get("type")
    if t == "object" or "properties" in sch:
        return _conform(c, sch, {})
    return {"array": [], "integer": 0, "number": 0, "boolean": False, "string": ""}.get(t or "", None)


def _conform(c: dict[str, Any], sch: dict[str, Any], data: Any) -> Any:
    sch = _resolve(c, sch)
    if data is None:
        return None
    if "anyOf" in sch:
        for v in (_resolve(c, x) for x in sch["anyOf"]):
            if v.get("type") == "null":
                continue
            if isinstance(data, dict) and (v.get("type") == "object" or "properties" in v):
                return _conform(c, v, data)
            if isinstance(data, list) and v.get("type") == "array":
                return _conform(c, v, data)
        return data
    if isinstance(data, dict) and "properties" in sch:
        out = dict(data)
        for k, ps in sch["properties"].items():
            if k in out:
                out[k] = _conform(c, ps, out[k])
            elif k in sch.get("required", []):
                out[k] = _default(c, ps)
        return out
    if isinstance(data, list) and sch.get("type") == "array" and "items" in sch:
        return [_conform(c, sch["items"], x) for x in data]
    return data


def conform(svc: str, path: str, method: str, status: int, data: Any) -> Any:
    c = _contract(svc)
    op = (c.get("paths") or {}).get(path, {}).get(method.lower(), {})
    resp = (op.get("responses") or {}).get(str(status)) or {}
    sch = ((resp.get("content") or {}).get("application/json") or {}).get("schema")
    return _conform(c, sch, data) if sch else data


def J(svc: str, path: str, method: str, data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(conform(svc, path, method, status, data), status_code=status)


# ── 보드 예시 데이터 ───────────────────────────────────────
RQ_ITEMS = [("R1", "본사 콘텐츠 일괄 배포"), ("R2", "프로모션 교체 주기 단축"), ("R3", "매장별 메뉴 가격 차등"),
            ("R4", "320개 매장 단계 도입"), ("R5", "기존 POS 연동")]
CUSTOMER = "A 커피 프랜차이즈"
PROJECT = "전국 매장 디지털 메뉴보드 전환"


def rq_version(rq_id: str = "rq_acoffee", n: int = 1, *, customer: str = CUSTOMER) -> dict[str, Any]:
    return {
        "requirement_id": rq_id, "version": n, "created_at": "2026-09-30T00:00:00Z", "created_by": None, "reason": "direct", "note": None,
        "summary": "요구사항 5건", "change_count": 0, "title": f"{customer} {PROJECT}", "project_id": None, "project_name": PROJECT,
        "customer_name": customer, "final_audience": "운영본부장, 마케팅팀장, IT팀", "item_count": 5, "keyman_count": 0,
        "open_question_count": 0, "latest_version": n,
        "snapshot": {"form": {}, "context": {}, "keymen": [], "customer_questions": [], "source_files": [], "author_note": {"text": "", "internal": True},
                     "items_flat": [{"id": f"it_{c}", "code": f"RQ-0{i + 1}", "text": t, "short": t, "keyman_id": None, "keyman_name": None,
                                     "keyman_weight": None, "needs_confirmation": False, "evidence": [], "entities": [],
                                     "source": None} for i, (c, t) in enumerate(RQ_ITEMS)]},
    }


SB_HANDOFF = {
    "source": {"feature": "storyboard", "ref_id": "sb_acoffee", "version": 3, "title": "A 커피 프랜차이즈 매장 리뉴얼", "updated_at": "2026-09-30T09:00:00Z",
               "route": "/storyboard/sb_acoffee"},
    "target": {"proposal_type": "standard", "section_key": "vp"},
    "customer": {"name": CUSTOMER, "industry_code": "FB", "scale_text": "320개 매장", "decision_makers": "운영본부장, 마케팅팀장, IT팀"},
    "rq_ref": {"rq_id": "rq_acoffee", "version": 1},
    "key_messages": [{"text": "본사가 하루에 바꾸는 320개 매장 메뉴보드", "place_label": "가치 1", "audience": "본사"},
                     {"text": "매장별 가격도 실수 없이", "place_label": "가치 2", "audience": "점주"},
                     {"text": "고객은 기다리는 동안 더 많이 본다", "place_label": "가치 3", "audience": "손님"}],
    "items": [
        {"key": "challenges", "label": "고객 과제", "sheet_role": "CH", "sheet_title": "고객 과제", "template_hint": None, "status": "ok",
         "status_label": "그대로 들어가요", "include_default": True,
         "content": {"pillars": [{"title": "메뉴 교체", "text": "프로모션 교체에 시간이 오래 걸려요"}, {"title": "가격 표기", "text": "매장마다 가격 안내가 달라요"},
                                 {"title": "승인 지연", "text": "본사-매장 콘텐츠 승인이 늦어요"}]}, "sources": []},
        {"key": "key_messages", "label": "Key Message 3", "sheet_role": "VP", "sheet_title": "가치 제안", "template_hint": {"code": "VP-B", "name": "가치 기둥"},
         "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
         "content": {"pillars": [{"title": "본사 통제", "text": "본사가 하루에 바꾸는 320개 매장 메뉴보드", "audience": "본사"},
                                 {"title": "가격 정확", "text": "매장별 가격도 실수 없이", "audience": "점주"},
                                 {"title": "고객 경험", "text": "고객은 기다리는 동안 더 많이 본다", "audience": "손님"}]}, "sources": []},
    ],
    "facts": [], "assets": [], "live_link": False,
}

MI_HANDOFF = {
    "source": {"feature": "MI", "ref_id": "mi_acoffee", "version": 2, "title": "A 커피 시장·경쟁사 분석", "updated_at": "2026-09-30T08:00:00Z",
               "route": "/mi/mi_acoffee/result"},
    "target": {"proposal_type": "standard", "section_key": "mi"}, "customer": {"name": CUSTOMER, "industry_code": "FB"}, "rq_ref": None,
    "items": [
        {"key": "mkt", "label": "시장 규모 · 성장률 (연도별)", "from_label": "시장조사", "sheet_role": "MS", "sheet_title": "시장 규모 · 성장",
         "template_hint": {"code": "MS-B", "name": "성장 추이"}, "status": "warn", "status_label": "[확정 필요] 1건", "include_default": True,
         "content": {"size_label": "국내 디지털 메뉴보드 시장", "size_series": [{"year": y, "value": v, "unit": "억 원"} for y, v in
                                                                         ((2020, 1200), (2022, 1650), (2024, 2300), (2026, 3100), (2028, 4200))],
                     "trends": [{"title": "디지털 메뉴보드 확산", "desc": "프랜차이즈 본사 주도 전환이 늘고 있어요", "implication": "전 매장 동시 전환이 유리해요"}]},
         "sources": [{"kind": "web", "ref": "src1", "label": "업계 리포트"}]},
        {"key": "ops", "label": "A 커피 매장 운영 프로세스", "from_label": "고객사", "sheet_role": "CB", "sheet_title": "고객사 비즈니스",
         "template_hint": {"code": "CB-C", "name": "운영 흐름 속 문제"}, "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
         "content": {"summary": "A 커피는 본사가 메뉴 · 가격을 정하고 매장이 직접 교체하는 구조예요.",
                     "ops_challenges": [{"stage": "메뉴 교체", "problem": "교체에 매장 인력이 들어요"}, {"stage": "가격 표기", "problem": "매장별 가격이 달라 오류가 나요"},
                                        {"stage": "프로모션", "problem": "본사 승인 뒤 반영이 늦어요"}]}, "sources": []},
        {"key": "cmp", "label": "경쟁사 비교표 (3사)", "from_label": "경쟁사", "sheet_role": "CP", "sheet_title": "경쟁 환경",
         "template_hint": {"code": "CP-A", "name": "비교표"}, "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
         "content": {"criteria": [t for _c, t in RQ_ITEMS], "columns": ["경쟁사 A", "경쟁사 B", "경쟁사 C", "삼성"],
                     "cells": [["지원", "일부", "지원", "지원"], ["일부", "지원", "[확인 필요]", "지원"], ["미지원", "일부", "지원", "지원"],
                               ["지원", "지원", "일부", "지원"], ["[확인 필요]", "일부", "미지원", "지원"]]}, "sources": []},
        {"key": "persona", "label": "사용자 페르소나", "from_label": "사용자", "sheet_role": "US", "sheet_title": "사용자 분석",
         "template_hint": {"code": "US-A", "name": "페르소나 3"}, "status": "add", "status_label": "섹션에 없는 시트 · 추가", "include_default": False,
         "content": {"personas": [{"role": "카페 손님", "goal": "빨리 주문하기", "pain": "메뉴 찾기"}, {"role": "점장", "goal": "교체 부담 줄이기", "pain": "시간대별 교체"},
                                  {"role": "본사 운영자", "goal": "일괄 관리", "pain": "매장마다 다른 화면"}]}, "sources": []},
    ],
    "facts": [{"key": "mkt2028", "label": "2028년 국내 디지털 메뉴보드 시장", "value": None, "unit": "억 원", "status": "placeholder", "placeholder": "[00]억 원"}],
    "assets": [],
}

SPEC_HANDOFF = {
    "source": {"feature": "SP", "ref_id": "sp_qmc", "version": 4, "title": "QM55C vs QB55C", "updated_at": "2026-09-30T07:00:00Z", "route": "/spec/sp_qmc"},
    "target": {"proposal_type": "standard", "section_key": "spec"}, "customer": None, "rq_ref": None, "live_link": True,
    "items": [{"key": "SC-A:0", "label": "QM55C vs QB55C 사양 비교", "from_label": "Spec 시트", "sheet_role": "SC", "sheet_title": "스펙 비교",
               "template_hint": {"code": "SC-A", "name": "사양 비교표 2~5개"}, "status": "warn", "status_label": "[확정 필요] 1건", "include_default": True,
               "repeat_key": None,
               "content": {"title": "QM55C vs QB55C 사양 비교", "columns": [{"label": "QM55C", "role": "proposed"}, {"label": "QB55C", "role": "proposed"}],
                           "rows": [{"label": "화면 크기 · 해상도", "cells": [{"text": "55\" · 3840×2160"}, {"text": "55\" · 3840×2160"}]},
                                    {"label": "밝기", "cells": [{"text": "500 nit"}, {"text": "350 nit"}]},
                                    {"label": "운영 시간", "cells": [{"text": "24/7"}, {"text": "[확정 필요]", "pending": True}]}]},
               "sources": [{"kind": "kb", "ref": "kb:model:QM55C", "label": "사내 카탈로그"}]}],
    "facts": [{"key": "qb_hours", "label": "QB55C 운영 시간", "value": None, "unit": None, "status": "placeholder", "placeholder": "[확정 필요]"}],
}

CA_HANDOFF = {
    "source": {"feature": "CA", "ref_id": "ca_acoffee", "version": 1, "title": "A 커피 경쟁사 분석", "updated_at": "2026-09-30T06:00:00Z", "route": "/competitor/ca_acoffee"},
    "target": {"proposal_type": "standard", "section_key": "why"}, "customer": None, "rq_ref": None,
    "items": [{"key": "cm", "label": "비교 6항목", "sheet_role": "CM", "sheet_title": "경쟁 비교", "template_hint": {"code": "CM-A", "name": "비교표"},
               "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
               "content": {"comparison": {"criteria": ["원격 콘텐츠 배포", "POS 가격 연동"], "columns": ["경쟁사 A", "경쟁사 B", "삼성"],
                                          "cells": [["일부", "지원", "지원"], ["미지원", "일부", "지원"]]},
                           "real_names": {"경쟁사 A": "LG전자", "경쟁사 B": "Sony"}}, "sources": []},
              {"key": "st", "label": "강점 3", "sheet_role": "ST", "sheet_title": "삼성 강점", "template_hint": {"code": "ST-A", "name": "강점 3"},
               "status": "ok", "status_label": "그대로 들어가요", "include_default": True,
               "content": {"strengths": [{"title": "원격 통합 관리", "note": "본사에서 전 매장 콘텐츠를 한 번에"}, {"title": "POS 연동", "note": "가격이 바뀌면 바로 반영"},
                                         {"title": "전국 A/S", "note": "전국 서비스망"}]}, "sources": []}],
    "facts": [],
}

BE_BUNDLE = {
    "birdseye_id": "be_lobby", "version": 2, "layout_version": 1, "title": "강남 플래그십 로비", "customer": CUSTOMER, "project_id": None,
    "route": "/birdseye/be_lobby", "updated_at": "2026-09-30T05:00:00Z",
    "space": {"label": "강남 플래그십 로비", "space_types": ["sales_floor"], "features": [], "estimated": False, "summary": "120평 · 층고 4.5m"},
    "cuts": [{"cut_id": "cut1", "label": "조감 45° · 주간", "view": "45", "light": "day", "before": False, "is_primary": True,
              "image_version_id": "imv_be1", "renditions": []}],
    "comparisons": [], "zones": {"layout": "ZP-A", "cut_id": "cut1", "points": [
        {"id": "bez_1", "zone_id": "z1", "n": 1, "name": "카운터 · 메뉴보드", "text": "메뉴보드 3면", "u": 0.3, "v": 0.4},
        {"id": "bez_2", "zone_id": "z2", "n": 2, "name": "쇼윈도 · 외부", "text": "옥외 사이니지", "u": 0.7, "v": 0.3},
        {"id": "bez_3", "zone_id": "z3", "n": 3, "name": "주문 · 대기 공간", "text": "대기 안내", "u": 0.5, "v": 0.7},
        {"id": "bez_4", "zone_id": "z4", "n": 4, "name": "픽업대", "text": "번호 안내", "u": 0.2, "v": 0.8}]},
    "quantities": [{"at": "카운터 · 메뉴보드", "model_code": "QM55C", "name": "Smart Signage QM55C", "qty": 2, "qty_source": "rule", "confirm": False},
                   {"at": "카운터 · 메뉴보드", "model_code": "KM24C", "name": "KM24C", "qty": 1, "qty_source": "rule", "confirm": False},
                   {"at": "카운터 · 메뉴보드", "model_code": "QM65C", "name": "QM65C", "qty": 1, "qty_source": "rule", "confirm": False},
                   {"at": "쇼윈도 · 외부", "model_code": "OH55C", "name": "Outdoor Signage OH55C", "qty": 1, "qty_source": "rule", "confirm": False},
                   {"at": "쇼윈도 · 외부", "model_code": "OM46C", "name": "OM46C", "qty": 1, "qty_source": "rule", "confirm": False},
                   {"at": "주문 · 대기 공간", "model_code": "QM55C", "name": "Smart Signage QM55C", "qty": 1, "qty_source": "suggested", "confirm": True}],
    "furniture": [], "memos": [], "products": [],
    "sheet_map": [{"from": "cut", "to": "birdseye", "code": "BV-A"}, {"from": "zones", "to": "birdseye", "code": "ZP-A"}],
}

SC_BUNDLE = {
    "scenario_id": "sc_day", "version": 1, "title": "A 커피 매장 하루", "customer": CUSTOMER, "type": "with",
    "roles": [], "slots": [], "sheet_plan": [], "confirm_items": [],
    "solutions": [{"id": "sol_magicinfo", "name": "MagicINFO"}, {"id": "sol_smartthings_pro", "name": "SmartThings Pro"}],
    "products": [{"family_id": "fam_qmc", "label": "QM55C"}],
    "scenes": [
        {"no": 1, "time": "07:00", "title": "본사가 아침 메뉴를 한 번에", "story": "본사가 전 매장 메뉴를 바꿔요", "place": "본사 운영실", "space_key": "hq",
         "solutions": [{"id": "sol_magicinfo", "action": "일괄 배포"}], "products": []},
        {"no": 2, "time": "12:00", "title": "점심 피크 가격 연동", "story": "POS 가격이 메뉴보드에 바로", "place": "매장 카운터", "space_key": "counter",
         "solutions": [{"id": "sol_magicinfo", "action": "POS 연동"}], "products": [{"label": "QM55C"}]},
        {"no": 3, "time": "15:00", "title": "한낮 에너지 절감", "story": "영업시간에 맞춰 공조 조절", "place": "매장 카운터", "space_key": "counter",
         "solutions": [{"id": "sol_smartthings_pro", "action": "에너지 자동화"}], "products": []},
        {"no": 4, "time": "21:00", "title": "마감 후 외부 사이니지", "story": "외부 화면 밝기 조절", "place": "매장 외부", "space_key": "outside",
         "solutions": [{"id": "sol_smartthings_pro", "action": "일정 관리"}], "products": [{"label": "OH55C"}]}],
    "sheet_plan": None, "confirm_items": [],
}


class Stubs:
    """가짜 서비스 묶음. calls[svc] 에 받은 요청을 쌓는다."""

    def __init__(self) -> None:
        self.calls: dict[str, list[dict[str, Any]]] = {}
        self.ai_calls: list[dict[str, Any]] = []
        self.rq_versions: dict[str, dict[str, Any]] = {"rq_acoffee": rq_version()}
        self.mi = copy.deepcopy(MI_HANDOFF)
        self.sb = copy.deepcopy(SB_HANDOFF)
        self.spec = copy.deepcopy(SPEC_HANDOFF)
        self.ca = copy.deepcopy(CA_HANDOFF)
        self.be = copy.deepcopy(BE_BUNDLE)
        self.sc = copy.deepcopy(SC_BUNDLE)
        self.lifecycle: dict[str, dict[str, Any]] = {"QM55B": {"model_code": "QM55B", "status": "discontinued",
                                                              "successors": [{"model_code": "QM55C", "reason": "후속 모델", "spec_diff_summary": "밝기 향상"}],
                                                              "evidence": "사내 제품 카탈로그 · 2026.09 단종"}}
        self.ai_overrides: dict[str, Any] = {}

    def log(self, svc: str, **kw: Any) -> None:
        self.calls.setdefault(svc, []).append(kw)

    # ── ai-tools 기록 프록시 ─────────────────────────────
    def ai_app(self, real: Any) -> FastAPI:
        app = FastAPI()
        stubs = self

        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
        async def proxy(path: str, request: Request) -> Response:
            body = await request.body()
            if request.method == "POST" and body:
                try:
                    data = json.loads(body)
                except ValueError:
                    data = None
                if isinstance(data, dict):
                    stubs.ai_calls.append({"path": "/" + path, **data})
                    task = data.get("task")
                    if task in stubs.ai_overrides:
                        ov = stubs.ai_overrides[task]
                        if isinstance(ov, dict) and "error" in ov:
                            e = ov["error"]
                            return JSONResponse({"error": {"code": e["code"], "message": e.get("message", ""), "details": {}}}, status_code=e["status"])
                        return J("ai-tools", "/v1/llm/chat", "post",
                                 {"call_id": "call_override", "content": json.dumps(ov.get("json"), ensure_ascii=False) if "json" in ov else ov.get("content", ""),
                                  "json": ov.get("json"), "provider": "mock", "model": "mock", "finish_reason": "stop", "tool_calls": []})
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=real), base_url="http://ai") as c:
                r = await c.request(request.method, "/" + path, content=body, headers={k: v for k, v in request.headers.items()
                                                                                       if k.lower() not in ("host", "content-length")},
                                    params=dict(request.query_params))
            return Response(r.content, status_code=r.status_code, headers={"content-type": r.headers.get("content-type", "application/json")})
        return app

    def ai(self, task: str) -> list[dict[str, Any]]:
        return [c for c in self.ai_calls if c.get("task") == task]

    # ── 가짜 서비스 ──────────────────────────────────────
    def apps(self) -> dict[str, Any]:
        from winmate_common import testing
        out = {"requirements": self._rq(), "storyboard": self._sb(), "mi": self._mi(), "spec": self._spec(), "image": self._image(),
               "competitor": self._ca(), "vp": self._vp(), "birdseye": self._be(), "scenario": self._sc()}
        out["ai-tools"] = self.ai_app(testing.load_service_app("ai-tools"))
        return out

    def _rq(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/requirements/{rq_id}/versions/{n}")
        async def version(rq_id: str, n: str) -> JSONResponse:
            s.log("requirements", op="version", rq_id=rq_id, n=n)
            v = s.rq_versions.get(rq_id)
            if not v:
                return JSONResponse({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}, status_code=404)
            return J("requirements", "/v1/requirements/{rq_id}/versions/{n}", "get", v)

        @app.get("/v1/requirements")
        async def lst(request: Request) -> JSONResponse:
            items = [{"id": k, "title": v["title"], "customer_name": v["customer_name"], "project_name": v["project_name"], "project_id": None,
                      "list_state": "saved", "state_label": "저장됨", "version": v["version"], "has_unsaved_changes": False, "keyman_count": 0,
                      "item_count": 5, "open_question_count": 0, "updated_at": "2026-09-30T00:00:00Z", "saved_at": "2026-09-30T00:00:00Z",
                      "route": f"/requirements/{k}", "active_deep": None, "owner": {"id": "u_choi", "name": "최민섭"}} for k, v in s.rq_versions.items()]
            return J("requirements", "/v1/requirements", "get", {"items": items, "next_cursor": None})

        @app.post("/v1/requirements/from-files")
        async def from_files(request: Request) -> JSONResponse:
            body = await request.json()
            s.log("requirements", op="from_files", body=body)
            s.rq_versions.setdefault("rq_rfp", rq_version("rq_rfp"))
            return J("requirements", "/v1/requirements/from-files", "post", {"job_id": "job_rqstub", "status": "queued",
                                                                              "ref": {"kind": "requirement", "id": "rq_rfp"}}, 202)

        @app.post("/v1/requirements/{rq_id}/save")
        async def save(rq_id: str) -> JSONResponse:
            s.log("requirements", op="save", rq_id=rq_id)
            return J("requirements", "/v1/requirements/{rq_id}/save", "post", {"requirement_id": rq_id, "version": 1, "created": True}, 201)

        @app.post("/v1/requirements/{rq_id}/customer-questions")
        async def cq(rq_id: str, request: Request) -> JSONResponse:
            body = await request.json()
            s.log("requirements", op="customer_question", rq_id=rq_id, body=body)
            return J("requirements", "/v1/requirements/{rq_id}/customer-questions", "post", {"id": "cq_1", "text": body.get("text")}, 201)

        @app.put("/v1/requirements/{rq_id}/links/{service_name}/{ref_id}")
        async def link(rq_id: str, service_name: str, ref_id: str, request: Request) -> JSONResponse:
            s.log("requirements", op="link", rq_id=rq_id, ref_id=ref_id)
            return J("requirements", "/v1/requirements/{rq_id}/links/{service_name}/{ref_id}", "put",
                     {"service": service_name, "ref_id": ref_id, "rq_version": 1})
        return app

    def _sb(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/storyboards/{sb_id}/proposal-handoff")
        async def ho(sb_id: str, request: Request) -> JSONResponse:
            s.log("storyboard", op="handoff", sb_id=sb_id, params=dict(request.query_params))
            if sb_id != "sb_acoffee":
                return JSONResponse({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}, status_code=404)
            d = copy.deepcopy(s.sb)
            d["target"]["proposal_type"] = request.query_params.get("type") or "standard"
            return J("storyboard", "/v1/storyboards/{sb_id}/proposal-handoff", "get", d)

        @app.get("/v1/storyboards")
        async def lst() -> JSONResponse:
            return J("storyboard", "/v1/storyboards", "get", {"items": [], "next_cursor": None})
        return app

    def _mi(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/analyses/{aid}/proposal-handoff")
        async def ho(aid: str, request: Request) -> JSONResponse:
            s.log("mi", op="handoff", aid=aid, params=dict(request.query_params))
            d = copy.deepcopy(s.mi)
            d["target"] = {"proposal_type": request.query_params.get("type") or "standard", "section_key": request.query_params.get("section") or "mi"}
            return J("mi", "/v1/analyses/{aid}/proposal-handoff", "get", d)

        @app.post("/v1/analyses/{aid}/facts:lookup")
        async def facts(aid: str, request: Request) -> JSONResponse:
            body = await request.json()
            s.log("mi", op="facts_lookup", body=body)
            return J("mi", "/v1/analyses/{aid}/facts:lookup", "post",
                     {"items": [{"key": q.get("key"), "candidates": [{"value": "1,234", "unit": "억 원", "source": {"label": "업계 리포트"}}]}
                                for q in body.get("questions") or []]})
        return app

    def _spec(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/sheets/{sheet_id}/proposal-handoff")
        async def ho(sheet_id: str) -> JSONResponse:
            s.log("spec", op="handoff", sheet_id=sheet_id)
            return J("spec", "/v1/sheets/{sheet_id}/proposal-handoff", "get", copy.deepcopy(s.spec))

        @app.get("/v1/handoffs/{hid}")
        async def get_h(hid: str) -> JSONResponse:
            return J("spec", "/v1/handoffs/{handoff_id}", "get", {"id": hid, "sheet_id": "sp_qmc", "status": "ready"})

        @app.post("/v1/handoffs/{hid}:ack")
        async def ack(hid: str, request: Request) -> JSONResponse:
            body = await request.json()
            s.log("spec", op="ack", hid=hid, body=body)
            return J("spec", "/v1/handoffs/{handoff_id}:ack", "post", {"id": hid, "sheet_id": "sp_qmc", "status": "acked"})

        @app.delete("/v1/links")
        async def release_links(request: Request) -> JSONResponse:
            pid = request.query_params.get("proposal_id")
            s.log("spec", op="release_links", proposal_id=pid, sheet_id=request.query_params.get("sheet_id"))
            return J("spec", "/v1/links", "delete", {"proposal_id": pid, "deleted": 1, "sheet_ids": ["sp_qmc"]})

        @app.post("/v1/lifecycle:check")
        async def lc(request: Request) -> JSONResponse:
            body = await request.json()
            s.log("spec", op="lifecycle", body=body)
            items = [s.lifecycle.get(m, {"model_code": m, "status": "on_sale", "successors": [], "evidence": "사내 제품 카탈로그"}) for m in body.get("model_codes") or []]
            return J("spec", "/v1/lifecycle:check", "post", {"items": items})
        return app

    def _image(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/images/{image_id}")
        async def img(image_id: str) -> JSONResponse:
            return J("image", "/v1/images/{image_id}", "get", {
                "id": image_id, "work_id": "imw_1", "label": "시안 1", "title": "카페 매장 메뉴보드 시안", "aspect": "16:9", "kind": "space",
                "status": "done", "rights": "generated", "caption_rule": "생성 이미지", "file_id": None, "current_version_id": "imv_1",
                "scene": {"space": "카운터 · 메뉴보드", "products": ["QM55C"]}, "work_title": "카페", "created_at": "2026-09-30T00:00:00Z"})

        @app.get("/v1/versions/{version_id}")
        async def ver(version_id: str) -> JSONResponse:
            return J("image", "/v1/versions/{version_id}", "get", {"id": version_id, "image_id": "img_cafe", "n": 1, "op": "generate", "label": "원본",
                                                                    "title": "시안 1", "master_file_id": "file_x", "url": "/x", "thumb_url": "/x",
                                                                    "width": 1920, "height": 1080, "created_at": "2026-09-30T00:00:00Z"})

        @app.post("/v1/images/{image_id}/usages")
        async def usage(image_id: str, request: Request) -> JSONResponse:
            body = await request.json()
            s.log("image", op="usage", image_id=image_id, body=body)
            return J("image", "/v1/images/{image_id}/usages", "post", {"service": "proposal", "ref": body.get("ref"), "label": body.get("label"),
                                                                        "version_id": body.get("version_id")}, 201)

        @app.delete("/v1/images/{image_id}/usages/{svc}/{ref}")
        async def unuse(image_id: str, svc: str, ref: str) -> Response:
            s.log("image", op="unusage", image_id=image_id, ref=ref)
            return Response(status_code=204)
        return app

    def _ca(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/analyses/{aid}/proposal-handoff")
        async def ho(aid: str, request: Request) -> JSONResponse:
            s.log("competitor", op="handoff", aid=aid, params=dict(request.query_params))
            return JSONResponse(copy.deepcopy(s.ca))
        return app

    def _vp(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/vps/{vp_id}/package")
        async def pkg(vp_id: str, request: Request) -> JSONResponse:
            t = request.query_params.get("proposal_type") or "standard"
            s.log("vp", op="package", vp_id=vp_id, type=t)
            if t == "quickwin":
                sheets = [{"role": "VP", "layout": {"code": "VP-G", "name": "한 문장 + 제품 히어로"}, "title": "가치 제안",
                           "content": {"message": "본사가 하루에 바꾸는 메뉴보드", "pillars": [{"title": "본사 통제", "text": "당일 교체"}]}, "pinned": False}]
            else:
                sheets = [{"role": "CH", "layout": {"code": "CH-A"}, "title": "고객 과제", "content": {"pillars": [{"title": "교체 지연", "text": "교체가 늦어요"}]}},
                          {"role": "VP", "layout": {"code": "VP-F3"}, "title": "가치 제안", "content": {"pillars": [{"title": "본사 통제", "text": "당일 교체"}]}},
                          {"role": "EF", "layout": {"code": "EF-A"}, "title": "기대 효과", "content": {}}]
            return JSONResponse({"proposal_type": t, "path_label": "Value Props", "rows": [], "sheets": sheets, "counts": {}, "sources_footer": []})

        @app.get("/v1/handoffs/{hid}")
        async def h(hid: str) -> JSONResponse:
            return JSONResponse({"id": hid, "vp_id": "vp_1", "vp_version": 1, "proposal_type": "standard", "options": {}, "status": "ready",
                                 "package": {"proposal_type": "standard", "sheets": [{"role": "VP", "layout": {"code": "VP-F3"}, "title": "가치 제안",
                                                                                      "content": {"pillars": [{"title": "본사 통제", "text": "당일 교체"}]}}]}})

        @app.post("/v1/handoffs/{hid}:ack")
        async def ack(hid: str, request: Request) -> JSONResponse:
            s.log("vp", op="ack", hid=hid, body=await request.json())
            return JSONResponse({"id": hid, "status": "applied"})

        @app.post("/v1/vps/{vp_id}:release-proposal")
        async def release(vp_id: str, request: Request) -> JSONResponse:
            body = await request.json()
            s.log("vp", op="release", vp_id=vp_id, body=body)
            return J("vp", "/v1/vps/{vp_id}:release-proposal", "post", {"vp_id": vp_id, "proposal_id": body.get("proposal_id") or "",
                                                                          "released": True, "linked_proposal": None})
        return app

    def _be(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/birdseyes/{bid}/handoff")
        async def ho(bid: str) -> JSONResponse:
            s.log("birdseye", op="handoff", bid=bid)
            return J("birdseye", "/v1/birdseyes/{be_id}/handoff", "get", copy.deepcopy(s.be))

        @app.post("/v1/birdseyes/{bid}/usages")
        async def usage(bid: str, request: Request) -> JSONResponse:
            body = await request.json()
            s.log("birdseye", op="usage", bid=bid, body=body)
            return J("birdseye", "/v1/birdseyes/{be_id}/usages", "post", {"birdseye_id": bid, "service": body.get("service") or "proposal",
                                                                           "ref": body.get("ref") or "", "label": body.get("label") or "",
                                                                           "version": body.get("version"), "route": None,
                                                                           "created_at": "2026-10-01T00:00:00Z"}, status=201)
        return app

    def _sc(self) -> FastAPI:
        app = FastAPI()
        s = self

        @app.get("/v1/scenarios/{sid}/handoff")
        async def ho(sid: str) -> JSONResponse:
            s.log("scenario", op="handoff", sid=sid)
            return J("scenario", "/v1/scenarios/{sc_id}/handoff", "get", copy.deepcopy(s.sc))

        @app.post("/v1/scenarios/{sid}/usages")
        async def usage(sid: str, request: Request) -> JSONResponse:
            body = await request.json()
            s.log("scenario", op="usage", sid=sid, body=body)
            return J("scenario", "/v1/scenarios/{sc_id}/usages", "post", {"service": body.get("service") or "proposal", "ref": body.get("ref") or "",
                                                                           "label": body.get("label") or "", "version": body.get("version"),
                                                                           "created_at": "2026-10-01T00:00:00Z"}, status=201)
        return app
