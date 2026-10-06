"""시험 세계 — 실제 ai-tools(mock) · workspace · files · jobs · export · image · storyboard + kb · birdseye 가짜.

- kb 가짜: 계약(`contracts/kb.json`, additionalProperties false)에 맞춘 고정 값 — R5 픽스처(D5 · C2 · A1): MagicINFO 연관 제품
  「Outdoor OH55C」(D5 ∩ C2) · 「Galaxy Tab Active5」(문장 속 「태블릿」 A1 → C2 category).
- birdseye 가짜: 08-birdseye §6.1 · §6.7 · §8 handoff 모양(보드 SC1B 예: 강남 플래그십 1층 로비 · 존 5 = 제품 3 · 가구만 1 · 빈 1).
- Recorder: ai-tools 에 들어온 요청(task · 본문)을 남기고, 필요하면 응답을 바꿔 끼운다(장면 3 장애 · 메모 넣기).
"""
from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from winmate_common import testing

SIGNAGE_IMG = None


class Recorder:
    """ASGI 감싸기 — 들어온 요청(경로 · JSON 본문)을 남긴다. before(path, body) 가 응답(dict)을 돌려주면 그걸로 답한다."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.requests: list[tuple[str, dict[str, Any] | None]] = []
        self.before: Callable[[str, dict[str, Any] | None], Awaitable[dict[str, Any] | None]] | None = None

    def calls(self, task: str) -> list[dict[str, Any]]:
        return [b for p, b in self.requests if b and b.get("task") == task]

    def prompts(self, task: str) -> list[str]:
        out = []
        for b in self.calls(task):
            out.append("\n".join(m.get("content") or "" for m in b.get("messages") or [] if isinstance(m.get("content"), str)))
        return out

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
        if self.before is not None:
            res = await self.before(scope["path"], parsed)
            if res is not None:
                resp = JSONResponse(res.get("body"), status_code=res.get("status", 200))
                await resp(scope, receive, send)
                return
        it = iter(msgs)

        async def rcv() -> dict[str, Any]:
            try:
                return next(it)
            except StopIteration:
                return {"type": "http.disconnect"}

        await self.app(scope, rcv, send)


def _env(code: str, result: dict[str, Any] | None) -> dict[str, Any]:
    return {"pattern": code, "result": result, "evidence_paths": [], "tier_min": None, "candidates": [], "decision_hint": "auto",
            "decision_reasons": [], "needs_confirmation": [], "fallback_level": None, "modes_used": ["stub"], "timings_ms": {}, "kb_version": "stub"}


SOLUTIONS = [
    {"id": "magicinfo", "name": "MagicINFO", "domain": "디스플레이", "desc": "설치형 사이니지 CMS", "icon": "M3 4h18v12H3z", "template_code": "MGI",
     "kb_id": "sol_magicinfo", "industries": ["retail"], "kb_ids": ["sol_magicinfo"], "kb_match": "full"},
    {"id": "smartthings_pro", "name": "SmartThings Pro", "domain": "공간 · 에너지", "desc": "여러 사업장 IoT · 에너지 대시보드", "icon": "M12 9a3 3 0 1 0 0 6",
     "template_code": "STP", "kb_id": "sol_smartthings_pro", "industries": ["retail"], "kb_ids": ["sol_smartthings_pro"], "kb_match": "full"},
    {"id": "vxt", "name": "Samsung VXT", "domain": "디스플레이", "desc": "클라우드 사이니지 CMS", "icon": "M4 16a4 4 0 0 1 1-7.9", "template_code": "VXT",
     "kb_id": "sol_vxt", "industries": ["retail"], "kb_ids": ["sol_vxt"], "kb_match": "full"},
]


def _product(kind: str, pid: str, display: str, label: str, family_id: str, model: str | None, path: list[str]) -> dict[str, Any]:
    return {"kind": kind, "id": pid, "display_name": display, "label": label, "model_code": model, "family_id": family_id,
            "family_name": display, "category_path": path, "meta_line": " · ".join(path[1:]), "thumb": None, "highlight": [], "score": 90.0}


PRODUCTS = {
    "QM55C": _product("model", "mdl_LH55QMCEBGCXKR", "QM55C", "Smart Signage QM55C", "fam_G000182628", "LH55QMCEBGCXKR", ["사이니지", "스마트 LCD 사이니지", "단독형"]),
    "Galaxy Tab Active5": _product("family", "fam_tab_active5", "Galaxy Tab Active5", "Galaxy Tab Active5", "fam_tab_active5", None,
                                   ["모바일", "갤럭시 탭", "갤럭시 탭 액티브"]),
}


def kb_stub() -> FastAPI:
    app = testing.stub_app("kb")

    @app.post("/v1/query/{code}")
    async def query(code: str, body: dict = Body(default={})):  # type: ignore[no-untyped-def]  # noqa: B008
        text = str(body.get("text") or "")
        if code == "A1":
            links: list[dict[str, Any]] = []
            if "MagicINFO" in text:
                links.append({"surface": "MagicINFO", "type": "solution", "id": "sol_magicinfo", "name": "Magic INFO", "conf": 0.6})
            if "SmartThings" in text:
                links.append({"surface": "SmartThings", "type": "solution", "id": "sol_smartthings_pro", "name": "스마트싱스 프로", "conf": 0.6})
            for word, cid, name in (("태블릿", "cat_tablets", "갤럭시 탭"), ("갤럭시 탭", "cat_tablets", "갤럭시 탭"),
                                    ("LCD 사이니지", "cat_smart-signage", "스마트 LCD 사이니지"), ("시스템에어컨", "top_hvac", "시스템에어컨·공조")):
                if word in text and not any(lk["id"] == cid for lk in links):
                    links.append({"surface": word, "type": "category", "id": cid, "name": name, "conf": 0.9})
            for word, sid, name in (("카운터", "order_counter", "주문·계산 카운터"), ("매장", "sales_floor", "매장 플로어")):
                if word in text:
                    links.append({"surface": word, "type": "space_type", "id": sid, "name": name, "conf": 0.8})
            return _env(code, {"links": links})
        if code == "C2":
            if body.get("category") == "cat_tablets":
                fams = [{"id": "fam_tab_active5", "name": "Galaxy Tab Active5", "model": None, "category": "갤럭시 탭", "score": 0.7}]
            else:
                fams = [{"id": "fam_oh55c", "name": "Outdoor OH55C", "model": "LH55OHCEBGCXKR", "category": "스마트 LCD 사이니지", "score": 0.6},
                        {"id": "fam_G000182628", "name": "단독형 UHD M 시리즈", "model": "LH55QMCEBGCXKR", "category": "스마트 LCD 사이니지", "score": 0.55}]
            return _env(code, {"families": fams, "solutions": []})
        if code == "D5":
            return _env(code, {"base_count": 15, "co_items": [
                {"kind": "family", "id": "fam_oh55c", "name": "Outdoor OH55C", "support": 2, "confidence": 0.13, "lift": 6.6},
                {"kind": "category", "id": "cat_smart-signage", "name": "스마트 LCD 사이니지", "support": 10, "confidence": 0.66, "lift": 2.87}]})
        if code == "D1":
            return _env(code, {"deployments": []})
        if code == "E1":
            return _env(code, {"tree": {"taglines": [], "key_messages": [
                {"id": "vp_magic_remote", "text": "기기와 콘텐츠 모두 원격으로 손쉽게 관리", "about": ["solution", "sol_magicinfo"], "claim_flag": 0,
                 "source_url": "https://www.samsung.com/sec/business/display-solution/", "tier": "T2_official", "proof_points": []}]}})
        if code == "A2":
            return _env(code, {"top2": [], "ask": True})
        return _env(code, {})

    @app.get("/v1/solutions")
    async def solutions(q: str | None = None, limit: int = 20):  # type: ignore[no-untyped-def]
        return {"items": SOLUTIONS, "next_cursor": None}

    @app.get("/v1/products/search")
    async def products_search(q: str = "", limit: int = 5, kinds: str = "model,family"):  # type: ignore[no-untyped-def]
        out = [v for k, v in PRODUCTS.items() if q and (q.lower() in k.lower() or k.lower() in q.lower())]
        return {"items": out[:limit]}

    return app


# ── birdseye 가짜(08-birdseye 문서 모양) ─────────────────────────

GANGNAM = "be_01JTESTBIRDSEYEGANGNAM0001"
LOGISTICS = "be_01JTESTBIRDSEYELOGISTIC001"


def gangnam_zones(changed: bool = False) -> list[dict[str, Any]]:
    oh = {"family_id": "fam_oh55c", "model_code": "LH55OHCEBGCXKR", "label": "Outdoor Signage OH55C", "short": "OH55C",
          "qty": 4 if changed else 3}
    pts = [
        {"id": "bez_1", "n": 1, "name": "쇼윈도 · 전면 유리창", "short_name": "쇼윈도", "text": "거리에서 보이는 첫인상", "products": [oh],
         "furniture": [], "path_order": 1, "u": 0.2, "v": 0.15, "links": [{"kind": "product", "label": "OH55C ×3"}], "kind": "product"},
        {"id": "bez_2", "n": 2, "name": "후면 미디어월", "short_name": "미디어월", "text": "입장 후 시선이 닿는 곳",
         "products": [{"family_id": "fam_G000182728", "model_code": None, "label": "The Wall All-in-One IAB 146\"", "short": "The Wall IAB 146\"", "qty": 1}],
         "furniture": [], "path_order": 2, "u": 0.5, "v": 0.8, "links": [], "kind": "product"},
        {"id": "bez_3", "n": 3, "name": "체험 · 시연 존", "short_name": "체험 · 시연 존", "text": "직원이 설명하는 자리",
         "products": [{"family_id": "fam_flip_pro", "model_code": "WA75D", "label": "Flip Pro WA75D", "short": "Flip Pro WA75D", "qty": 1}],
         "furniture": [], "path_order": 3, "u": 0.8, "v": 0.5, "links": [], "kind": "product"},
        {"id": "bez_4", "n": 4, "name": "라운지 · 안내 데스크", "short_name": "라운지 · 상담", "text": "", "products": [],
         "furniture": [{"name": "라운지 소파", "qty": 2}], "path_order": 4, "u": 0.3, "v": 0.6, "links": [], "kind": "furniture"},
        {"id": "bez_5", "n": 5, "name": "중앙 기둥 ×2", "short_name": "중앙 기둥", "text": "", "products": [], "furniture": [],
         "path_order": None, "u": 0.5, "v": 0.45, "links": [], "kind": "empty"},
    ]
    for p in pts:
        p["zone_id"] = p["id"]  # 계약: id = 포인트(bez_…) · zone_id = 존 — 가짜는 같게 둔다
    return pts


class BirdseyeStub:
    def __init__(self) -> None:
        self.versions: dict[str, int] = {GANGNAM: 3, LOGISTICS: 2}
        self.updated: dict[str, str] = {GANGNAM: "2026-09-20T01:00:00Z", LOGISTICS: "2026-09-20T01:00:00Z"}
        self.changed: set[str] = set()
        self.created: list[dict[str, Any]] = []
        self.usages: list[tuple[str, dict[str, Any]]] = []
        self.handoff_reads: list[str] = []
        app = testing.stub_app("birdseye")
        titles = {GANGNAM: "강남 플래그십 1층 로비", LOGISTICS: "C 물류센터 관제실"}

        def row(k: str) -> dict[str, Any]:
            return {"id": k, "title": titles[k], "subtitle": titles[k], "status": "done", "step": 5, "step_label": "3D 조감도 생성",
                    "status_title": "완료", "action": {"label": "열기", "route": f"/birdseye/{k}/result"}, "route": f"/birdseye/{k}/result",
                    "updated_at": self.updated[k], "created_at": "2026-09-01T00:00:00Z", "owner": "u_test",
                    "zone_count": 5 if k == GANGNAM else 2, "zones_count": 5 if k == GANGNAM else 2, "version": self.versions[k]}

        @app.get("/v1/birdseyes")
        async def list_():  # type: ignore[no-untyped-def]
            return {"items": [row(k) for k in titles], "counts": {"all": 2, "in_progress": 0, "needs_check": 0, "done": 2},
                    "next_cursor": None, "total": 2}

        @app.get("/v1/birdseyes/{bid}/version")
        async def version(bid: str):  # type: ignore[no-untyped-def]
            return {"version": self.versions.get(bid, 1), "layout_version": self.versions.get(bid, 1),
                    "updated_at": self.updated.get(bid) or "2026-09-20T01:00:00Z", "zones_hash": "x"}

        @app.get("/v1/birdseyes/{bid}/handoff")
        async def handoff(bid: str):  # type: ignore[no-untyped-def]
            self.handoff_reads.append(bid)
            zones = gangnam_zones(bid in self.changed) if bid == GANGNAM else [
                {"id": "bez_l1", "n": 1, "name": "관제 데스크", "short_name": "관제 데스크", "text": "", "products": [
                    {"family_id": "fam_vw", "model_code": None, "label": "비디오월 VM55C", "short": "VM55C", "qty": 4}], "furniture": [], "path_order": 1},
                {"id": "bez_l2", "n": 2, "name": "상황 공유 회의실", "short_name": "회의실", "text": "", "products": [], "furniture": [{"name": "회의 테이블"}],
                 "path_order": 2}]
            for z in zones:
                z.setdefault("zone_id", z["id"])
                z.setdefault("kind", "product" if z.get("products") else ("furniture" if z.get("furniture") else "empty"))
            return {"birdseye_id": bid, "version": self.versions.get(bid, 1), "layout_version": self.versions.get(bid, 1),
                    "title": titles.get(bid, "조감도"), "customer": "강남 플래그십", "route": f"/birdseye/{bid}/result",
                    "updated_at": self.updated.get(bid) or "2026-09-20T01:00:00Z",
                    "space": {"area_m2": 396.0, "area_pyeong": 120, "ceiling_h_m": 4.5, "features": [{"kind": "storefront_window", "label": "전면 유리창 (도로측)"}]},
                    "cuts": [], "comparisons": [], "zones": {"layout": "ZP-A", "cut_id": None, "points": zones},
                    "plan_preview": {"width_m": 20.0, "height_m": 12.0, "zone_count": len(zones), "area_pyeong": 120, "ceiling_h_m": 4.5,
                                     "area_label": "120평 · 층고 4.5m", "window_label": "전면 유리창 (도로측)",
                                     "zones": [{"id": z["zone_id"], "n": z["n"], "x": z.get("u"), "y": z.get("v"), "name": z["name"]} for z in zones]},
                    "quantities": [], "furniture": [], "memos": [], "sheet_map": [], "products": []}

        @app.post("/v1/birdseyes", status_code=201)
        async def create(body: dict = Body(...)):  # type: ignore[no-untyped-def]  # noqa: B008
            self.created.append(body)
            bid = f"be_01JTESTCREATED{len(self.created):012d}"
            return {"id": bid, "owner": "u_test", "title": body.get("title") or "조감도", "version": 1, "route": f"/birdseye/{bid}/space",
                    "created_at": "2026-10-01T00:00:00Z", "updated_at": "2026-10-01T00:00:00Z"}

        @app.post("/v1/birdseyes/{bid}/usages", status_code=201)
        async def usages(bid: str, body: dict = Body(...)):  # type: ignore[no-untyped-def]  # noqa: B008
            self.usages.append((bid, body))
            return {"birdseye_id": bid, "created_at": "2026-10-01T00:00:00Z", **body}

        self.app = app

    def bump(self, bid: str, at: str = "2026-09-30T02:00:00Z") -> None:
        self.versions[bid] += 1
        self.updated[bid] = at
        self.changed.add(bid)


SB_ID = "sb_01JTESTSTORYBOARD000000001"


def storyboard_stub() -> FastAPI:
    """Storyboard 가짜 — 계약(`contracts/storyboard.json` Storyboard) 모양의 Part 2 공간 2개(SB4 → `/scenario/new?sb=`)."""
    app = testing.stub_app("storyboard")

    @app.get("/v1/storyboards/{sb_id}")
    async def get_sb(sb_id: str):  # type: ignore[no-untyped-def]
        if sb_id != SB_ID:
            return JSONResponse({"error": {"code": "NOT_FOUND", "message": "없음", "details": {}}}, status_code=404)
        seg = {"state": "filled", "segments": [{"text": "출근 시간 주문이 몰린다", "ai_added": False}]}
        return {"id": SB_ID, "owner": {"id": "u_test", "name": "테스터"}, "project_id": None, "name": "A 커피 제안 스토리보드",
                "title": "A 커피 제안 스토리보드", "customer_name": "A 커피", "status": "in_progress", "step": 4,
                "outline": {"spaces": [
                    {"id": "spc_1", "key": "order_counter", "order": 1, "name": "매장 카운터", "purpose": "주문 · 픽업 대기 줄이기",
                     "status": "supplemented", "slots": {"action": seg}, "products": [{"name": "Kiosk KM24C", "is_extension": False}]},
                    {"id": "spc_2", "key": "hq_office", "order": 2, "name": "본사 운영실", "purpose": "전국 매장 콘텐츠 배포", "status": "draft"},
                ]},
                "created_at": "2026-10-01T00:00:00Z", "updated_at": "2026-10-05T00:00:00Z"}

    return app


class World:
    def __init__(self, *, real_image: bool = True, real_storyboard: bool = False, real_birdseye: bool = False) -> None:
        self.ai = Recorder(testing.load_service_app("ai-tools"))
        self.kb = Recorder(kb_stub())
        self.be = BirdseyeStub()
        self.apps: dict[str, Any] = {
            **testing.platform_apps("files", "jobs", "workspace", "export"),
            "ai-tools": self.ai, "kb": self.kb, "birdseye": self.be.app, "storyboard": storyboard_stub(),
        }
        if real_birdseye:  # 실제 birdseye 앱(계약 엄격 검증 · 저장소 공유 DATA_DIR)
            self.birdseye = Recorder(testing.load_service_app("birdseye"))
            self.apps["birdseye"] = self.birdseye
        if real_image:
            self.image = Recorder(testing.load_service_app("image"))
            self.apps["image"] = self.image
        if real_storyboard:
            self.apps["storyboard"] = testing.load_service_app("storyboard")
