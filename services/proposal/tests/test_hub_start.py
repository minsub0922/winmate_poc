"""허브 Storyboard(SB-nn)에서 시작(2026-10-10) — flow.json stages → 고객 정보 · 연결 미리보기 · 섹션 재료 · 허브 ppt 칸.

허브는 실제 storyboard 앱(in-process, `/v1/flows*`), 나머지 기능은 pr_stubs 가짜 서비스. 이전 Storyboard(`sb_…`) 경로는 그대로인지도 본다.
값 모양은 docs/scenarios/11-content-flow.md §6(보드 webapp1 RQ1 · DS2 · MI · CA · VP · SP · SC 예시).
"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from conftest import FIXED_NOW, Ctx
from pr_stubs import Stubs
from winmate_common import testing

RQ = {
    "customer": "E 자산운용", "title": "용산 업무시설 재개발 AI Ready 오피스", "target": "대표이사",
    "keymen": [{"role": "대표이사", "weight": "50%", "needs": ["AI Ready 오피스"]}, {"role": "공간컨텐츠실장", "weight": "30%", "needs": ["업무환경 플랫폼"]}],
    "goals": ["최초 AI Ready 오피스"],
    "requirements": [{"id": "R1", "text": "사용자를 인식하고 반응하는 AI Ready 오피스", "status": "ok", "by": "manual"},
                     {"id": "R2", "text": "에너지 사용량 20% 절감 · 실측 증빙", "status": "ok", "by": "manual"},
                     {"id": "R3", "text": "오피스를 업무환경 플랫폼으로", "status": "check", "by": "manual"}],
    "counts": {"keymen": 2, "reqs": 3, "check": 1},
}
DSS = {
    "industry": {"value": "오피스 · 업무시설", "by": "manual", "basis": None},
    "spaces": [
        {"name": "로비", "by": "manual", "products": [
            {"name": "The Wall IAB 146\"", "kind": "product", "ref": None, "qty": "1식", "by": "manual"},
            {"name": "Smart Signage QM55C", "kind": "product", "ref": "kb:model:mdl_LH55QMCEBGCXKR", "model_code": "LH55QMCEBGCXKR", "qty": "2대", "by": "manual"}]},
        {"name": "회의실", "by": "manual", "products": [
            {"name": "Flip Pro WA75D", "kind": "product", "ref": None, "qty": None, "qtyStatus": "확인 필요", "by": "manual"}]},
    ],
    "solutions": [{"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo", "by": "manual", "links": ["로비 Smart Signage QM55C"],
                   "why": "로비 · 회의실 화면을 본사에서 한 번에 관리"},
                  {"name": "SmartThings Pro", "ref": None, "by": "manual", "links": [], "why": None}],
    "counts": {"spaces": 2, "products": 3, "solutions": 2},
}
MI = {
    "prevVer": None, "queries": {"market": ["프라임 오피스 스마트 빌딩"], "customer": ["E 자산운용 ESG"], "user": ["하이브리드 근무 회의실"]},
    "filters": {"period": "최근 1년", "sourceTypes": ["리포트", "공시 · IR"]}, "counts": {"found": 4, "kept": 3, "numberCheck": 1},
    "items": [
        {"id": "mi-1", "group": "시장", "summary": "프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석",
         "source": {"type": "리포트", "name": "부동산 리서치", "date": "2026-08", "url": "https://example.com/report"}, "kept": True, "addedIn": "v1", "numberCheck": None},
        {"id": "mi-2", "group": "고객", "summary": "E 자산운용은 운용 자산의 에너지 사용량을 30% 줄이겠다고 밝힘",
         "source": {"type": "공시 · IR", "name": "E 자산운용 ESG 보고서", "date": "2026-05", "url": "https://example.com/esg"}, "kept": True, "addedIn": "v1",
         "numberCheck": "수치 확인"},
        {"id": "mi-3", "group": "사용자", "summary": "하이브리드 근무로 회의실 예약이 오후에 몰림",
         "source": {"type": "뉴스", "name": "오피스 뉴스", "date": "2026-07", "url": "https://example.com/news"}, "kept": True, "addedIn": "v1", "numberCheck": None},
        {"id": "mi-4", "group": "시장", "summary": "빼 둔 정보 — 제안서에 들어가면 안 됨",
         "source": {"type": "뉴스", "name": "다른 뉴스", "date": "2026-01", "url": "https://example.com/x"}, "kept": False, "addedIn": "v1", "numberCheck": None},
    ],
}


def _dims(*vals: tuple[str, str]) -> dict[str, dict[str, str]]:
    return {k: {"verdict": v, "note": n} for k, (v, n) in zip(("spec", "price", "cases", "esg", "brand"), vals)}


CA = {
    "basis": {"from": "DSS-01", "categories": ["사이니지", "LED"]}, "dimensions": ["스펙", "가격", "유관 사례", "ESG", "브랜드 평판"],
    "competitors": [
        {"id": "A", "name": "LG전자", "by": "manual",
         "wiki": {"hq": "국내", "size": "대기업", "industry": "전자 · 디스플레이", "mainBusiness": "상업용 디스플레이 · LED 월", "source": {"type": "Wikipedia"}},
         "criteria": [{"k": "제품군", "v": "사이니지 · LED 월", "status": "ok"}],
         "matches": [{"space": "로비 미디어월", "ours": "The Wall IAB 146\"", "theirs": "올인원 LED 월",
                      "dims": _dims(("similar", "해상도 동급"), ("ours-worse", "초기가 높음"), ("ours-better", "국내 AI 오피스 로비 사례"),
                                    ("ours-better", "저전력"), ("similar", "비슷"))},
                     {"space": "콘텐츠 관리", "ours": "MagicINFO", "theirs": "자사 CMS",
                      "dims": _dims(("ours-better", "원격 일괄 배포"), ("similar", "비슷"), ("ours-better", "대형 오피스 사례"),
                                    ("no-data", "자료 없음"), ("similar", "비슷"))}],
         "pros": ["초기 도입가가 낮음"], "cons": ["사이니지 · IoT 가 따로 놀아 공간 통합이 약함"],
         "claims": [{"axis": "통합", "text": "MagicINFO · SmartThings Pro 하나의 플랫폼으로 공간을 묶음", "supports": ["RQ-01"]}]},
        {"id": "B", "name": "경쟁사 B", "by": "ai-web", "wiki": {"hq": "해외", "size": "[위키 값]"},
         "matches": [{"space": "회의실", "ours": "Flip Pro WA75D", "theirs": "전자칠판",
                      "dims": _dims(("similar", "판서 동급"), ("similar", "가격 비슷"), ("ours-worse", "회의실 단독 사례가 더 많음"),
                                    ("similar", "비슷"), ("similar", "비슷"))}],
         "pros": [], "cons": [], "claims": []},
    ],
    "counts": {"competitors": 2, "matches": 3, "verdicts": {"oursBetter": 4, "similar": 9, "oursWorse": 2, "noData": 1}},
}
VP = {
    "from": "DSS-01", "selection": {"fromDss": 3, "excluded": [], "addedOutsideDss": []},
    "items": [
        {"name": "The Wall IAB 146\"", "kind": "product", "ref": None, "spaces": ["로비"], "values": [
            {"id": "vp-1", "space": "로비", "message": "들어서는 순간 회사의 AI 비전을 보여 줌",
             "need": {"text": "방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요", "by": "manual"}, "req": "RQ-01 최초 AI Ready", "by": "manual"}]},
        {"name": "MagicINFO", "kind": "solution", "ref": "kb:solution:sol_magicinfo", "spaces": ["회의실"], "values": [
            {"id": "vp-2", "space": "회의실", "message": "회의실 화면을 본사에서 한 번에 관리", "need": None, "req": "", "by": "ai-accepted"}]},
    ],
    "importedFrom": [], "counts": {"items": 2, "values": 2, "needs": 1, "needsMissing": 1},
}
SP = {
    "from": "DSS-01", "format": "비교표", "lang": "ko", "unit": "mm",
    "columns": [{"key": "size_resolution", "label": "화면 크기 · 해상도"}, {"key": "brightness_contrast", "label": "밝기 · 명암비"}],
    "models": [
        {"space": "로비", "name": "Smart Signage QM55C", "model_code": "LH55QMCEBGCXKR", "ref": "kb:model:LH55QMCEBGCXKR", "qty": 2,
         "specs": {"size_resolution": "55\" · 3840×2160", "brightness_contrast": "500nit · 4000:1"}, "by": "manual"},
        {"space": "회의실", "name": "Flip Pro WA75D", "model_code": None, "ref": None, "qty": None,
         "specs": {"size_resolution": "[확인 필요]", "brightness_contrast": "[확인 필요]"}, "by": "manual"},
    ],
    "warnings": [{"model": "Flip Pro WA75D", "kind": "not_in_catalog", "text": "카탈로그에 없는 모델"}],
    "counts": {"models": 2, "columns": 2, "warnings": 1},
}
SC = {
    "from": "DSS-01",
    "spaces": [
        {"name": "로비", "products": ["The Wall IAB 146\"", "Smart Signage QM55C", "MagicINFO"], "scenarios": [
            {"id": "sc-1", "title": "방문객 첫 안내", "user": "방문객", "products": ["The Wall IAB 146\"", "MagicINFO"],
             "steps": [{"text": "로비에 들어서면 미디어월이 환영 영상을 보여 줌", "product": "The Wall IAB 146\""},
                       {"text": "안내 사이니지가 회의실 위치를 알려 줌", "product": "Smart Signage QM55C"}], "fields": [], "by": "manual"}]},
        {"name": "회의실", "products": ["Flip Pro WA75D"], "scenarios": [
            {"id": "sc-2", "title": "하이브리드 회의", "user": "직원", "products": ["Flip Pro WA75D"],
             "steps": [{"text": "회의 시작 전 자료를 화면에 띄움", "product": "Flip Pro WA75D"}], "fields": [], "by": "manual"}]},
    ],
    "rules": {"minProductsPerSpace": 1, "minProductsPerScenario": 1}, "counts": {"spaces": 2, "scenarios": 2},
}
KM = "AI Ready 오피스의 새로운 모델"
PILLARS = [{"text": "사람을 알아보는 공간", "evidence": ["RQ-01 대표이사 1"]}, {"text": "에너지 20% 절감을 숫자로", "evidence": ["RQ-01 대표이사 3"]}]


@pytest.fixture
async def hctx(tmp_path: Path, stubs: Stubs) -> AsyncIterator[Ctx]:
    """conftest ctx 와 같되 storyboard 는 실제 앱(허브 `/v1/flows*`)."""
    with testing.environment(tmp_path, service="proposal", PROPOSAL_FIXED_NOW=FIXED_NOW, PROPOSAL_PACE_S="0", KB_WARMUP="0",
                             PROPOSAL_EXPORT_WAIT_S="2", SOFFICE_PATH="off"):
        testing.use_fake_redis()
        from winmate_proposal import clients
        clients.clear_cache()
        apps = {**testing.platform_apps(), **stubs.apps(), "storyboard": testing.load_service_app("storyboard")}
        with testing.inprocess(apps):
            yield Ctx(tmp_path, apps, stubs)
        clients.clear_cache()


@pytest.fixture
async def hclient(hctx: Ctx) -> AsyncIterator[Any]:
    from winmate_proposal.main import app
    async with testing.api_client(app, user_id="u_choi", user_name="최민섭") as c:
        yield c


async def make_flow(hctx: Ctx, *, full: bool) -> str:
    async with testing.api_client(hctx.apps["storyboard"]) as sb:
        r = await sb.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용", "target": "대표이사",
                                              "rq": {"ref": "RQ-01", "ver": 1, "value": RQ, "md": "- 요구 3 · 확인 필요 1",
                                                     "card": {"title": RQ["title"], "facts": [], "groups": [], "line": "키맨 2 · 요구 3 · 확인 필요 1"}}})
        assert r.status_code in (200, 201), r.text
        sid = r.json()["id"]
        r = await sb.put(f"/v1/flows/{sid}/stages/dss", json={"ref": "DSS-01", "value": DSS, "md": "- 공간 2 · 제품 3",
                                                             "card": {"title": "용산 오피스 공간별 제품", "line": "공간 2 · 제품 3 · 솔루션 2"}})
        assert r.status_code == 200, r.text
        if full:
            r = await sb.patch(f"/v1/flows/{sid}", json={"key_message": KM, "key_pillars": PILLARS})
            assert r.status_code == 200, r.text
            for key, ref, val in (("mi", "MI-01", MI), ("ca", "CA-01", CA), ("vp", "VP-01", VP), ("sp", "SP-01", SP), ("sc", "SC-01", SC)):
                r = await sb.put(f"/v1/flows/{sid}/stages/{key}", json={"ref": ref, "value": val, "md": f"- {ref}", "card": {"title": f"{ref} 제목", "line": f"{ref} 한 줄"}})
                assert r.status_code == 200, r.text
    return sid


async def flow_of(hctx: Ctx, sid: str) -> dict[str, Any]:
    async with testing.api_client(hctx.apps["storyboard"]) as sb:
        return (await sb.get(f"/v1/flows/{sid}")).json()


async def draft_of(sheet_id: str) -> dict[str, Any]:
    from winmate_proposal import repo
    return (await repo.aget("sheets", sheet_id) or {}).get("draft") or {}


async def compose(client: Any, pid: str, type_: str = "standard") -> None:
    assert (await client.put(f"/v1/proposals/{pid}/type", json={"type": type_})).status_code == 200
    assert (await client.post(f"/v1/proposals/{pid}/composition:start")).status_code == 200


async def fill(client: Any, ctx: Ctx, pid: str, *keys: str) -> dict[str, dict[str, Any]]:
    out = {}
    for k in keys:
        sv = (await client.get(f"/v1/proposals/{pid}/sections/{k}")).json()
        assert sv["needs_fill"] is True, (k, sv["sources"])
        r = await client.post(f"/v1/proposals/{pid}/sections/{k}:fill", json={"reason": "enter"})
        assert r.status_code == 202, r.text
    await ctx.run_jobs()
    for k in keys:
        out[k] = (await client.get(f"/v1/proposals/{pid}/sections/{k}")).json()
        assert out[k]["status"] == "ready", (k, out[k]["status"])
    return out


def sheet(sv: dict[str, Any], role: str, ref: str | None = None) -> dict[str, Any]:
    return next(s for s in sv["sheets"] if s["role"] == role and (ref is None or ref in s["title"]))


async def test_start_from_hub_with_all_stages(hclient: Any, hctx: Ctx) -> None:
    sid = await make_flow(hctx, full=True)
    r = await hclient.post("/v1/proposals", json={"start_mode": "works", "links": [{"feature": "storyboard", "ref_id": sid}]})
    assert r.status_code == 201, r.text
    p = r.json()
    pid = p["id"]
    # 고객 정보는 stages.rq 에서
    assert p["customer"]["name"] == "E 자산운용"
    assert p["customer"]["decision_makers"] == "대표이사, 공간컨텐츠실장"
    assert p["title"] == "용산 업무시설 재개발 AI Ready 오피스"
    assert p["customer"]["industry_code"] == "OF"
    # PR1L 기존 작업 — 허브 Storyboard 줄 + 연결된 콘텐츠 · 넣을 곳
    rw = (await hclient.get(f"/v1/proposals/{pid}/related-works")).json()
    row = next(w for w in rw["works"] if w["ref_id"] == sid)
    assert row["on"] is True and row["feature"] == "storyboard" and row["tool_label"] == "Storyboard"
    assert row["meta"].startswith(f"{sid} · DSS + 콘텐츠 5/5")
    hub = row["hub"]
    assert [c["key"] for c in hub["contents"]] == ["rq", "dss", "km", "mi", "ca", "vp", "sp", "sc"]
    tl = {c["key"]: c["target_label"] for c in hub["contents"]}
    assert tl["rq"] == "고객 정보" and tl["km"] == "Value Props" and tl["ca"] == "Why Samsung"
    assert tl["dss"] in ("공간별 제품 · 솔루션 제안", "공간별 가치 시나리오")
    mi_row = next(c for c in hub["contents"] if c["key"] == "mi")
    assert mi_row["ref"] == "MI-01" and mi_row["title"] == "MI-01 제목" and mi_row["line"] == "MI-01 한 줄"
    pv = rw["preview"]
    assert pv["customer_from"]["label"] == "고객 · 프로젝트 · Storyboard에서"
    assert pv["customer_summary"].startswith("E 자산운용 · 오피스") and pv["customer_summary"].endswith("요구사항 3건")
    states = {s["key"]: (s["state"], s["source_label"]) for s in pv["sections"]}
    expect = {"mi": ("full", "MI-01"), "bigMi": ("full", "MI-01"), "vp": ("full", "VP-01"), "why": ("full", "CA-01"), "spec": ("full", "SP-01"),
              "spaceProducts": ("full", "DSS-01"), "solution": ("partial", "DSS-01"), "spaceScenario": ("full", "SC-01"),
              "cases": ("new", "새로 찾기"), "birdseye": ("new", "새로 작성")}
    for k, v in states.items():
        assert v == expect[k], (k, v)
    # 연결 · 다음 → links:apply — 허브 ppt 칸에 이 제안서
    assert (await hclient.post(f"/v1/proposals/{pid}/links:apply")).status_code == 202
    await hctx.run_jobs()
    pr = (await hclient.get(f"/v1/proposals/{pid}")).json()
    assert pr["stage"] == "type"
    flow = await flow_of(hctx, sid)
    ppt = flow["stages"]["ppt"]
    assert ppt["proposal_id"] == pid and ppt["ref"] == "PR-01" and ppt["customer"] == "E 자산운용"
    cell = next(c for c in flow["cells"] if c["key"] == "ppt")
    assert cell["state"] == "done" and cell["route"] == f"/proposal/{pid}"
    assert flow["cards"]["ppt"]["title"] == "용산 업무시설 재개발 AI Ready 오피스"
    # 표준 제안서 → 섹션마다 stage 값이 재료로
    await compose(hclient, pid)
    svs = await fill(hclient, hctx, pid, "mi", "vp", "spaceProducts", "solution", "why", "spec")
    assert [x["label"] for x in svs["mi"]["sources"]] == ["Storyboard · MI-01"]
    assert [x["label"] for x in svs["solution"]["sources"]] == ["Storyboard · DSS-01 · SC-01"]
    assert svs["mi"]["sources"][0]["route"] == f"/storyboard/flow/{sid}"
    # MI: 담은 정보만 · 출처 · 수치 확인은 확정 필요로
    ms = await draft_of(sheet(svs["mi"], "MS")["id"])
    assert [x["title"] for x in ms["points"]] == ["프라임 오피스에서 스마트 빌딩 설비 도입이 늘고 있다는 업계 분석"]
    assert ms["points"][0]["body"] == "부동산 리서치" and ms["points"][0]["tag"] == "리포트 · 2026-08"
    assert ms["footnotes"] == ["출처: 부동산 리서치 · 리포트 · 2026-08"]
    assert "빼 둔 정보" not in json.dumps([await draft_of(s["id"]) for s in svs["mi"]["sheets"]], ensure_ascii=False)
    cb_sheet = sheet(svs["mi"], "CB")
    cb = (await hclient.get(f"/v1/proposals/{pid}/sheets/{cb_sheet['id']}")).json()
    assert "30%" in json.dumps(cb["display"], ensure_ascii=False)
    assert cb["confirm_items"], cb["confirm_label"]                      # 수치 확인 표시 → 확정 필요
    cp = await draft_of(sheet(svs["mi"], "CP")["id"])
    assert cp["table"]["columns"] == ["비교 항목", "경쟁사 A", "경쟁사 B"]
    # Value Props: Key message + 받쳐 줄 메시지 · 고객 니즈
    vpd = await draft_of(sheet(svs["vp"], "VP")["id"])
    assert vpd["title"] == KM and vpd["message"] == KM
    assert [x["title"] for x in vpd["points"]] == ["사람을 알아보는 공간", "에너지 20% 절감을 숫자로"]
    ch = await draft_of(sheet(svs["vp"], "CH")["id"])
    assert ch["points"][0] == {"title": "로비", "body": "방문객에게 첫인상으로 우리 회사를 각인시키고 싶어요", "tag": "RQ-01 최초 AI Ready", "kpi": ""}
    # 공간별 제품: DSS 공간 · 제품 · 수량 문자열, 모르는 수량은 [확인 필요]
    sm = await draft_of(sheet(svs["spaceProducts"], "SM")["id"])
    assert sm["table"]["rows"][0]["label"] == "로비" and [c["text"] for c in sm["table"]["rows"][0]["cells"]] == ["The Wall IAB 146\"", "1식"]
    pis = [s for s in svs["spaceProducts"]["sheets"] if s["role"] == "PI"]
    assert [s["title"] for s in pis] == ["로비", "회의실"]
    lobby = await draft_of(pis[0]["id"])
    assert [(x["name"], x["qty"]) for x in lobby["products"]] == [("The Wall IAB 146\"", "1식"), ("Smart Signage QM55C", "2대")]
    meet = (await hclient.get(f"/v1/proposals/{pid}/sheets/{pis[1]['id']}")).json()
    assert "[확인 필요]" in json.dumps(meet["display"], ensure_ascii=False) or meet["confirm_items"]
    # 솔루션: DSS 솔루션(이유 · 함께 쓰는 제품) + 공간 시나리오
    sxi = await draft_of(sheet(svs["solution"], "SXI", "MagicINFO")["id"])
    assert sxi["message"] == "로비 · 회의실 화면을 본사에서 한 번에 관리"
    sxs = await draft_of(sheet(svs["solution"], "SXS", "MagicINFO")["id"])
    assert sxs["steps"][0]["title"] == "방문객 첫 안내" and sxs["steps"][0]["when"] == "방문객"
    assert "환영 영상" in sxs["steps"][0]["body"]
    # Why Samsung: 판정 · 메모 · 강점(claims) · 경쟁사 익명
    cm = await draft_of(sheet(svs["why"], "CM")["id"])
    assert cm["table"]["columns"] == ["비교 항목", "경쟁사 A", "경쟁사 B"]
    assert [r["label"] for r in cm["table"]["rows"]] == ["스펙", "가격", "유관 사례", "ESG", "브랜드 평판"]
    cases_row = cm["table"]["rows"][2]["cells"]
    assert cases_row[0]["text"].startswith("삼성 우위") and cases_row[0]["mark"] == "full"
    assert cases_row[1]["text"].startswith("삼성 열위") and cases_row[1]["mark"] == "none"
    st = await draft_of(sheet(svs["why"], "ST")["id"])
    assert st["points"][0]["title"] == "통합" and "하나의 플랫폼" in st["points"][0]["body"]
    why_all = json.dumps([await draft_of(s["id"]) for s in svs["why"]["sheets"]] + [cp], ensure_ascii=False)
    assert "LG전자" not in why_all                                         # V5 — 실명은 넣지 않는다
    # 제품 스펙: 모델 × 항목 · 경고
    sc = await draft_of(sheet(svs["spec"], "SC")["id"])
    assert sc["table"]["columns"] == ["항목", "Smart Signage QM55C", "Flip Pro WA75D"]
    assert sc["table"]["rows"][0]["label"] == "화면 크기 · 해상도"
    assert sc["table"]["rows"][0]["cells"][0]["text"] == "55\" · 3840×2160"
    assert sc["footnotes"] == ["확인: Flip Pro WA75D: 카탈로그에 없는 모델"]
    sds = [s for s in svs["spec"]["sheets"] if s["role"] == "SD"]
    assert [s["title"] for s in sds] == ["제품 상세 · LH55QMCEBGCXKR", "제품 상세 · Flip Pro WA75D"]
    assert (await draft_of(sds[0]["id"]))["table"]["rows"][1]["cells"][0]["text"] == "500nit · 4000:1"
    # 허브에 없는 섹션(조감도 · 유관 사례)은 연결 자료 없음
    be = (await hclient.get(f"/v1/proposals/{pid}/sections/birdseye")).json()
    assert be["sources"] == []
    # 표지 부제 = Key message
    from winmate_proposal import render_doc
    built = await render_doc.build(pid, include_toc=False, dividers=False)
    assert built["document"]["cover"]["subtitle"] == KM


async def test_start_from_hub_with_rq_dss_only(hclient: Any, hctx: Ctx) -> None:
    sid = await make_flow(hctx, full=False)
    p = (await hclient.post("/v1/proposals", json={"start_mode": "works", "links": [{"feature": "storyboard", "ref_id": sid}]})).json()
    pid = p["id"]
    assert p["customer"]["name"] == "E 자산운용"
    lo = (await hclient.get(f"/v1/proposals/{pid}/links")).json()
    assert [x["feature"] for x in lo["links"]] == ["storyboard"] and lo["links"][0]["label"] == "Storyboard · 용산 AI Ready 오피스"
    states = {s["key"]: (s["state"], s["source_label"]) for s in lo["preview"]["sections"]}
    for k, v in states.items():
        want = {"spaceProducts": ("full", "DSS-01"), "solution": ("partial", "DSS-01"), "spaceScenario": ("partial", "DSS-01"),
                "cases": ("new", "새로 찾기")}.get(k, ("new", "새로 작성"))
        assert v == want, (k, v)
    rw = (await hclient.get(f"/v1/proposals/{pid}/related-works")).json()
    row = next(w for w in rw["works"] if w["ref_id"] == sid)
    assert [c["key"] for c in row["hub"]["contents"]] == ["rq", "dss"] and row["meta"].startswith(f"{sid} · DSS까지")
    await compose(hclient, pid)
    for k in ("mi", "vp", "why"):
        sv = (await hclient.get(f"/v1/proposals/{pid}/sections/{k}")).json()
        assert sv["sources"] == [] and sv["needs_fill"] is False, k          # 「새로 작성」
        assert all(s["status"] == "need" for s in sv["sheets"]), k
    svs = await fill(hclient, hctx, pid, "spaceProducts")
    assert [x["label"] for x in svs["spaceProducts"]["sources"]] == ["Storyboard · DSS-01"]
    assert [s["title"] for s in svs["spaceProducts"]["sheets"] if s["role"] == "PI"] == ["로비", "회의실"]
    # 요구사항은 stages.rq 에서(R1…) — 섹션 초안 재료
    pr = (await hclient.get(f"/v1/proposals/{pid}")).json()
    assert pr["stage"] in ("customer", "type", "compose", "sections")
    from winmate_proposal import repo
    doc = await repo.aget("proposals", pid)
    assert [x["code"] for x in doc["ctx"]["rq"]["items"]] == ["R1", "R2", "R3"] and doc["ctx"]["rq"]["source"] == "storyboard"


async def test_old_storyboard_path_unchanged(client: Any, ctx: Any) -> None:
    """이전 Storyboard(sb_…)는 `…/proposal-handoff` 그대로 — Value Props 하나 · 고객 정보 · Key Message 기둥."""
    p = (await client.post("/v1/proposals", json={"start_mode": "handoff", "links": [{"feature": "storyboard", "ref_id": "sb_acoffee"}]})).json()
    pid = p["id"]
    assert p["customer"]["name"] == "A 커피 프랜차이즈" and p["customer"]["decision_makers"] == "운영본부장, 마케팅팀장, IT팀"
    assert any(c.get("op") == "handoff" and c.get("sb_id") == "sb_acoffee" for c in ctx.stubs.calls.get("storyboard", []))
    lo = (await client.get(f"/v1/proposals/{pid}/links")).json()
    assert lo["links"][0]["label"] == "Storyboard · A 커피 프랜차이즈 매장 리뉴얼"
    assert [(s["key"], s["source_label"]) for s in lo["preview"]["sections"] if s["state"] != "new"] == [("vp", "Storyboard")]
    await compose(client, pid)
    sv = (await client.get(f"/v1/proposals/{pid}/sections/vp")).json()
    assert [x["label"] for x in sv["sources"]] == ["Storyboard · A 커피 프랜차이즈 매장 리뉴얼"]
    mi = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    assert mi["sources"] == []
    await client.post(f"/v1/proposals/{pid}/sections/vp:fill", json={"reason": "enter"})
    await ctx.run_jobs()
    sv = (await client.get(f"/v1/proposals/{pid}/sections/vp")).json()
    vpd = await draft_of(sheet(sv, "VP")["id"])
    assert [x["title"] for x in vpd["points"]] == ["본사 통제", "가격 정확", "고객 경험"]
    doc = (await client.get(f"/v1/proposals/{pid}")).json()
    assert "hub" not in doc or not doc.get("hub")


def test_snapshot_by_type() -> None:
    """유형마다 stage → 섹션이 바뀐다(Solution형: 대규모 MI · 공간별 가치 시나리오 · 스펙 없음, 퀵윈: MI · Why 없음)."""
    from winmate_proposal import hub
    flow = {"id": "SB-09", "name": "용산", "version": 3, "customer": "E 자산운용", "key_message": {"text": KM, "pillars": PILLARS},
            "stages": {"rq": {"ref": "RQ-01", "ver": 1, **RQ}, "dss": {"ref": "DSS-01", "ver": 1, **DSS}, "mi": {"ref": "MI-01", "ver": 2, **MI},
                       "ca": {"ref": "CA-01", "ver": 1, **CA}, "vp": {"ref": "VP-01", "ver": 1, **VP}, "sp": {"ref": "SP-01", "ver": 1, **SP},
                       "sc": {"ref": "SC-01", "ver": 1, **SC}, "ppt": None}, "cards": {}, "cells": []}
    sol = hub.snapshot(flow, "solution")
    by = {}
    for it in sol["items"]:
        by.setdefault(it["target_section"], []).append(it["sheet_role"])
    assert set(by) == {"bigMi", "why", "vp", "spaceScenario"}
    assert by["spaceScenario"].count("SS") == 2 and "VM" in by["spaceScenario"]
    assert hub.sections_for(sol, "solution") == ["bigMi", "vp", "spaceScenario", "why"]
    qw = hub.snapshot(flow, "quickwin")
    assert {it["target_section"] for it in qw["items"]} == {"vp", "spaceProducts", "solution", "spec"}
    assert hub.sections_for(qw, "quickwin") == ["vp", "spaceProducts", "solution", "spec"]
    std = hub.snapshot(flow, "standard")
    assert std["customer"] == {"name": "E 자산운용", "decision_makers": "대표이사, 공간컨텐츠실장", "industry_code": "OF"}
    assert [x["code"] for x in std["rq_items"]] == ["R1", "R2", "R3"]
    assert std["source"]["updated_at"] == "" and std["source"]["version"] == 3
    prods = {(p["name"], p.get("space_key")): p for p in std["products"]}
    assert prods[("Flip Pro WA75D", "회의실")]["qty"] == "[확인 필요]" and prods[("Smart Signage QM55C", "로비")]["main"] is True
    assert [s["code"] for s in std["solutions"]] == ["MGI", "STP"]
    # 사전 작업만(rq + dss) — MI · VP · 경쟁사 · 스펙 항목은 만들지 않는다(지어내지 않음)
    bare = hub.snapshot({**flow, "key_message": None, "stages": {"rq": flow["stages"]["rq"], "dss": flow["stages"]["dss"]}}, "standard")
    assert {it["target_section"] for it in bare["items"]} == {"spaceProducts", "solution"}
    assert list(bare["stages"]) == ["rq", "dss"]
    assert hub.is_hub_id("SB-06") and not hub.is_hub_id("sb_acoffee")


async def test_delete_proposal_clears_hub_ppt_cell(hclient: Any, hctx: Ctx) -> None:
    """제안서를 지우면 허브 「PPT 제작 · B2B 제안서」 칸도 비운다(storyboard `DELETE …/stages/ppt?ref=`)."""
    sid = await make_flow(hctx, full=False)
    pid = (await hclient.post("/v1/proposals", json={"start_mode": "works", "links": [{"feature": "storyboard", "ref_id": sid}]})).json()["id"]
    flow = await flow_of(hctx, sid)
    assert flow["stages"]["ppt"]["proposal_id"] == pid
    assert (await hclient.delete(f"/v1/proposals/{pid}")).status_code == 204
    flow = await flow_of(hctx, sid)
    assert flow["stages"].get("ppt") is None and next(c for c in flow["cells"] if c["key"] == "ppt")["state"] == "none"


async def test_hub_stale_only_on_content_change(hclient: Any, hctx: Ctx) -> None:
    """「Storyboard 업데이트됨」은 콘텐츠 판(content_rev)으로 — 제안서가 ppt 칸에 자기를 적는 것으로는 뜨지 않는다."""
    from winmate_proposal import links
    sid = await make_flow(hctx, full=False)
    pid = (await hclient.post("/v1/proposals", json={"start_mode": "works", "links": [{"feature": "storyboard", "ref_id": sid}]})).json()["id"]
    assert (await flow_of(hctx, sid))["stages"]["ppt"]["proposal_id"] == pid
    assert await links.check_stale(pid) == []
    async with testing.api_client(hctx.apps["storyboard"]) as sb:
        r = await sb.put(f"/v1/flows/{sid}/stages/mi", json={"ref": "MI-01", "value": MI, "md": "- MI-01", "card": {"title": "MI-01 제목", "line": "한 줄"}})
        assert r.status_code == 200, r.text
    stale = await links.check_stale(pid)
    assert [x["ref_id"] for x in stale] == [sid]
