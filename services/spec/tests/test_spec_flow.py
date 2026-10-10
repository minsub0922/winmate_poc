"""Spec 시트 새 흐름(2026-10-08 — 보드 webapp1 SP1 · SP2 · SP_Done, 11-content-flow §6 `sp`) — 허브(storyboard 실제 앱) 연동."""
from __future__ import annotations

import os
from typing import Any

import pytest
from sp_helpers import FIXED_NOW, AIStub, RQStub
from winmate_common import testing

DSS_VALUE = {
    "industry": {"value": "오피스 · 업무시설", "by": "manual"},
    "spaces": [
        {"name": "로비", "products": [{"name": "The Wall IAB 146\"", "kind": "product", "qty": 1},
                                     {"name": "Smart Signage QM55C", "kind": "product", "qty": 2}]},
        {"name": "라운지", "products": [{"name": "Smart Signage QM55C", "kind": "product", "qty": 1}]},
        {"name": "회의실", "products": [{"name": "Smart Signage QB43C", "kind": "product", "qty": 3, "by": "ai-accepted"}]},
    ],
    "solutions": [{"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo"}],
}


@pytest.fixture
async def env(tmp_path):
    with testing.environment(tmp_path, service="spec", SPEC_FIXED_NOW=FIXED_NOW, SPEC_CATALOG_ADAPTER="kb", SPEC_CATALOG_FIXTURE="",
                             KB_WARMUP="0", SPEC_ELECTRICITY_KRW_PER_KWH=""):
        testing.use_fake_redis()
        from winmate_spec import api_support, catalog
        catalog.reset_catalog()
        api_support._scheduled = False
        apps = {**testing.platform_apps("kb", "files", "jobs", "workspace", "export"), "ai-tools": AIStub().app, "requirements": RQStub().app,
                "storyboard": testing.load_service_app("storyboard")}
        with testing.inprocess(apps):
            yield apps
        catalog.reset_catalog()
        for k in ("SPEC_CATALOG_ADAPTER", "SPEC_CATALOG_FIXTURE"):
            os.environ.pop(k, None)


@pytest.fixture
async def client(env):
    from winmate_spec.main import app
    async with testing.api_client(app) as c:
        yield c


async def _sb(sb, *, dss: bool = True) -> dict[str, Any]:
    f = (await sb.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용",
                                           "rq": {"ref": "RQ-01", "ver": 1, "value": {}, "md": "- 요구 12"}})).json()
    if dss:
        r = await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-01", "value": DSS_VALUE, "md": "- 공간 3"})
        assert r.status_code == 200, r.text
    return f


async def test_spec_flow_from_dss_edit_and_finish_pushes_stage(client, env):
    async with testing.api_client(env["storyboard"]) as sb:
        bare = await _sb(sb, dss=False)
        r = await client.post("/v1/spec-flows", json={"sb_id": bare["id"]})
        assert r.status_code == 422 and r.json()["error"]["code"] == "PREREQUISITE_MISSING"
        assert (await client.post("/v1/spec-flows", json={"sb_id": "SB-404"})).status_code == 404

        f = await _sb(sb)
        r = await client.post("/v1/spec-flows", json={"sb_id": f["id"]})
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["code"] == "SP-01" and d["title"] == "용산 AI Ready 오피스" and d["dss_ref"] == "DSS-01"
        rows = {x["name"]: x for x in d["rows"]}
        # 제품 하나 = 행 하나(공간 모으고 수량 더함), 솔루션은 행이 아니다
        assert list(rows) == ["The Wall IAB 146\"", "Smart Signage QM55C", "Smart Signage QB43C"]
        qm = rows["Smart Signage QM55C"]
        assert qm["spaces"] == ["로비", "라운지"] and qm["qty"] == 3 and qm["match"] == "code"
        assert qm["display_name"] == "QM55C" and qm["model_code"].startswith("LH55QMC")
        # 값은 KB 원문에서만: 55" · 3840×2160 / 500 nit · 4,000:1
        assert qm["cells"]["size_resolution"] == '55" · 3840×2160'
        assert qm["cells"]["brightness_contrast"].startswith("500 nit")
        assert qm["cells"]["warranty"] == "[확인 필요]" and "warranty" not in qm["pending"]   # 보증은 기본 항목 밖(KB 에 원천 없음)
        assert rows["Smart Signage QB43C"]["by"] == "ai-accepted"
        # KB 에 없는 제품 → 값은 [확인 필요] + 경고
        wall = rows["The Wall IAB 146\""]
        assert wall["model_code"] is None and set(wall["cells"].values()) == {"[확인 필요]"}
        assert wall["warnings"][0]["kind"] == "not_in_catalog"
        assert d["items"] == ["size_resolution", "brightness_contrast", "io_ports", "power", "size_weight", "install"]
        assert [c["label"] for c in d["columns"]][:2] == ["화면 크기 · 해상도", "밝기 · 명암비"] and d["counts"]["models"] == 3

        # 형식 · 항목 · 표기(영문 · inch) — expected_version 409
        v = d["version"]
        r = await client.patch(f"/v1/spec-flows/{d['id']}", json={"notation": "en_inch", "items": ["warranty", "size_resolution", "size_weight"], "expected_version": v})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["items"] == ["size_resolution", "size_weight", "warranty"] and d["columns"][0]["label"] == "Screen Size · Resolution"
        qm = next(x for x in d["rows"] if x["key"] == qm["key"])
        assert " in" in qm["cells"]["size_weight"] and "lb" in qm["cells"]["size_weight"]
        assert qm["cells"]["warranty"] == "[To be confirmed]" and "warranty" in qm["pending"]
        r = await client.patch(f"/v1/spec-flows/{d['id']}", json={"format": "per_product", "expected_version": v})
        assert r.status_code == 409
        assert (await client.patch(f"/v1/spec-flows/{d['id']}", json={"items": ["nope"]})).status_code == 422

        # 행: 다른 모델(같은 제품군) · 수량 · 빼기
        opts = (await client.get(f"/v1/spec-flows/{d['id']}/rows/{qm['key']}/models")).json()
        assert opts["basis"] == "family" and any(o["current"] for o in opts["items"])
        other = (await client.get(f"/v1/spec-flows/{d['id']}/rows/{qm['key']}/models", params={"q": "QM65C"})).json()
        assert other["basis"] == "search" and other["items"]
        code65 = next(o["model_code"] for o in other["items"] if o["display_name"] == "QM65C")
        d = (await client.patch(f"/v1/spec-flows/{d['id']}/rows/{qm['key']}", json={"model_code": code65, "qty": 4})).json()
        qm = next(x for x in d["rows"] if x["key"] == qm["key"])
        assert qm["display_name"] == "QM65C" and qm["qty"] == 4 and qm["by"] == "manual" and qm["match"] == "manual"
        assert any(w["kind"] == "mismatch" for w in qm["warnings"])     # DSS 이름(QM55C)과 다름
        r = await client.patch(f"/v1/spec-flows/{d['id']}/rows/{qm['key']}", json={"model_code": "NOPE999"})
        assert r.status_code == 422 and r.json()["error"]["code"] == "MODEL_NOT_IN_CATALOG"
        wall_key = next(x["key"] for x in d["rows"] if x["model_code"] is None)
        d = (await client.patch(f"/v1/spec-flows/{d['id']}/rows/{wall_key}", json={"on": False})).json()
        d = (await client.patch(f"/v1/spec-flows/{d['id']}", json={"notation": "ko_mm"})).json()
        assert d["counts"]["models"] == 2 and d["counts"]["total"] == 3

        # 저장 → flow.json stages.sp · 요약본 · 카드 · 편집 경로
        out = (await client.post(f"/v1/spec-flows/{d['id']}:finish")).json()
        st = out["stage"]
        assert st["from"] == "DSS-01" and st["format"] == "비교표" and st["lang"] == "ko" and st["unit"] == "mm"
        assert st["counts"]["models"] == 2 and st["counts"]["columns"] == 3
        assert [c["key"] for c in st["columns"]] == ["size_resolution", "size_weight", "warranty"]
        m0 = st["models"][0]
        assert m0["space"] == "로비 · 라운지" and m0["model_code"] == code65 and m0["ref"] == f"kb:model:{code65}" and m0["qty"] == 4
        assert m0["specs"]["warranty"] == "[확인 필요]" and m0["by"] == "manual"
        assert any(w["kind"] == "mismatch" for w in st["warnings"])
        assert out["summary_md"].startswith("- 제품 2 · 항목 3 · 비교표 · 한국어 · mm")
        assert out["flow_sync"]["md_added"].startswith("## ") and "SP-01" in out["flow_sync"]["md_added"]
        flow = (await sb.get(f"/v1/flows/{f['id']}")).json()
        assert flow["stages"]["sp"]["models"][0]["model_code"] == code65 and flow["stages"]["sp"]["ref"] == "SP-01"
        cell = next(c for c in flow["cells"] if c["key"] == "sp")
        assert cell["state"] == "done" and cell["route"] == f"/spec/flow/{d['id']}"
        assert flow["cards"]["sp"]["facts"][0] == ["제품", "2"]
        got = (await client.get(f"/v1/spec-flows/{d['id']}")).json()
        assert got["ver"] == 1 and got["status"] == "done"
        # 다시 저장하면 판이 올라간다
        assert (await client.post(f"/v1/spec-flows/{d['id']}:finish")).json()["stage"]["ver"] == 2
        lst = (await client.get("/v1/spec-flows")).json()
        assert lst["items"][0]["id"] == d["id"] and lst["items"][0]["status"] == "done"


async def test_spec_flow_finish_needs_models_and_columns(client, env):
    async with testing.api_client(env["storyboard"]) as sb:
        f = await _sb(sb)
        d = (await client.post("/v1/spec-flows", json={"sb_id": f["id"]})).json()
        d = (await client.patch(f"/v1/spec-flows/{d['id']}", json={"items": []})).json()
        r = await client.post(f"/v1/spec-flows/{d['id']}:finish")
        assert r.status_code == 422 and r.json()["error"]["code"] == "NO_COLUMNS"
        d = (await client.patch(f"/v1/spec-flows/{d['id']}", json={"items": ["power"]})).json()
        for row in d["rows"]:
            d = (await client.patch(f"/v1/spec-flows/{d['id']}/rows/{row['key']}", json={"on": False})).json()
        r = await client.post(f"/v1/spec-flows/{d['id']}:finish")
        assert r.status_code == 422 and r.json()["error"]["code"] == "NO_MODELS"
        # 모델 비우기 → 카탈로그 밖 제품
        k = d["rows"][1]["key"]
        d = (await client.patch(f"/v1/spec-flows/{d['id']}/rows/{k}", json={"clear_model": True, "on": True})).json()
        row = next(x for x in d["rows"] if x["key"] == k)
        assert row["model_code"] is None and row["cells"]["power"] == "[확인 필요]" and row["pending"] == ["power"]


DSS_TEXT_QTY = {
    "industry": {"value": "오피스 · 업무시설", "by": "manual", "basis": None},
    "spaces": [
        {"name": "로비", "by": "manual", "products": [
            {"name": "The Wall IAB 146\"", "kind": "product", "ref": None, "qty": "1식", "by": "manual"},
            {"name": "Smart Signage QM55C", "kind": "product", "ref": "kb:model:mdl_LH55QMCEBGCXKR", "model_code": "LH55QMCEBGCXKR", "qty": "2대", "by": "manual"}]},
        {"name": "라운지", "by": "manual", "products": [{"name": "Smart Signage QM55C", "kind": "product", "ref": None, "qty": None, "by": "manual"}]},
        {"name": "회의실", "by": "manual", "products": [
            {"name": "Smart Signage QB55C", "kind": "product", "ref": None, "qty": "실당 1대", "by": "manual"},
            {"name": "Smart Signage QB43C", "kind": "product", "ref": None, "qty": "3 EA", "by": "ai-accepted"}]},
    ],
    "solutions": [{"name": "MagicINFO", "ref": "kb:solution:sol_magicinfo", "by": "manual", "links": [], "why": None}],
    "counts": {"spaces": 3, "products": 5, "solutions": 1},
}


def test_parse_qty_reads_only_counts():
    from winmate_spec.spec_flow import parse_qty
    assert [parse_qty(v) for v in (2, "2대", "1식", " 3 EA ", "10 pcs", 2.0)] == [2, 2, 1, 3, 10, 2]
    assert [parse_qty(v) for v in (None, "", "실당 1대", "층당 1대", "확인 필요", -1, True, 1.5)] == [None] * 8


async def test_spec_flow_dss_text_qty_and_xlsx_on_finish(client, env):
    """DSS 수량 원문(2대 · 1식 · 실당 1대 · null) → 개수가 분명한 것만, 모르면 null([확인 필요]) · 저장하면 XLSX(SP-01_v1.xlsx) + stages.sp.file."""
    async with testing.api_client(env["storyboard"]) as sb:
        f = (await sb.post("/v1/flows", json={"name": "용산 AI Ready 오피스", "customer": "E 자산운용",
                                               "rq": {"ref": "RQ-01", "ver": 1, "value": {}, "md": "- 요구 3"}})).json()
        assert (await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-01", "value": DSS_TEXT_QTY, "md": "- 공간 3"})).status_code == 200
        d = (await client.post("/v1/spec-flows", json={"sb_id": f["id"]})).json()
        rows = {x["name"]: x for x in d["rows"]}
        assert rows["The Wall IAB 146\""]["qty"] == 1 and rows["The Wall IAB 146\""]["qty_note"] == "로비 1식"
        qm = rows["Smart Signage QM55C"]
        assert qm["qty"] is None and qm["qty_note"] == "로비 2대 · 라운지 [확인 필요]" and qm["match"] == "ref"   # 하나라도 모르면 합을 지어내지 않는다
        assert rows["Smart Signage QB55C"]["qty"] is None and rows["Smart Signage QB55C"]["qty_note"] == "회의실 실당 1대"
        assert rows["Smart Signage QB43C"]["qty"] == 3
        # 사람이 수량을 정하면 그 값
        d = (await client.patch(f"/v1/spec-flows/{d['id']}/rows/{qm['key']}", json={"qty": 3})).json()
        assert next(x for x in d["rows"] if x["key"] == qm["key"])["qty"] == 3

        out = (await client.post(f"/v1/spec-flows/{d['id']}:finish")).json()
        assert out["file"]["name"] == "SP-01_v1.xlsx" and out["file"]["url"].endswith("/content")
        st = out["stage"]
        assert st["file"] == "SP-01_v1.xlsx" and st["fileId"] == out["file"]["id"] and st["valuesFrom"] == "공식 카탈로그"
        q = {m["name"]: m["qty"] for m in st["models"]}
        assert q == {"The Wall IAB 146\"": 1, "Smart Signage QM55C": 3, "Smart Signage QB55C": None, "Smart Signage QB43C": 3}
        flow = (await sb.get(f"/v1/flows/{f['id']}")).json()
        assert flow["stages"]["sp"]["file"] == "SP-01_v1.xlsx"
        assert (await client.get(f"/v1/spec-flows/{d['id']}/stage")).json()["file"]["id"] == out["file"]["id"]

    # XLSX 안: 비교표 시트 · 머리(항목 + DSS 제품 이름) · 모델 · 공간 · 수량 줄 다음 항목 · 카탈로그에 없는 칸은 [확인 필요]
    import io

    import openpyxl
    async with testing.api_client(env["files"]) as fc:
        r = await fc.get(f"/v1/files/{out['file']['id']}/content")
        assert r.status_code == 200, r.text
    ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
    vals = [[c for c in row] for row in ws.iter_rows(values_only=True)]
    flat = [v for row in vals for v in row if v is not None]
    head = next(row for row in vals if row and row[0] == "항목")
    assert list(head[:5]) == ["항목", "The Wall IAB 146\"", "Smart Signage QM55C", "Smart Signage QB55C", "Smart Signage QB43C"]
    assert "모델" in flat and "화면 크기 · 해상도" in flat and '55" · 3840×2160' in flat and "[확인 필요]" in flat
    # 두 번째 저장 → v2 파일
    out2 = (await client.post(f"/v1/spec-flows/{d['id']}:finish")).json()
    assert out2["file"]["name"] == "SP-01_v2.xlsx" and out2["stage"]["ver"] == 2


# ── DSS 다시 가져오기 · 초안 지우기 · 같은 Storyboard 초안 이어 쓰기(2026-10-10) ──

def _dss_v2() -> dict[str, Any]:
    """DSS_VALUE 에서 The Wall 을 빼고(로비) QH55C 를 더하고, QB43C 수량 3 → 4 · QM55C 로비 수량 2 → 3."""
    import copy
    v = copy.deepcopy(DSS_VALUE)
    lobby = v["spaces"][0]["products"]
    v["spaces"][0]["products"] = [p for p in lobby if not p["name"].startswith("The Wall")] + [{"name": "Smart Signage QH55C", "kind": "product", "qty": 2}]
    v["spaces"][0]["products"][0]["qty"] = 3
    v["spaces"][2]["products"][0]["qty"] = 4
    return v


async def test_spec_flow_resync_dss_merges_and_keeps_user_edits(client, env):
    async with testing.api_client(env["storyboard"]) as sb:
        f = await _sb(sb)
        d = (await client.post("/v1/spec-flows", json={"sb_id": f["id"]})).json()
        assert d["dss_ref"] == "DSS-01" and d["dss_ver"] == 1
        assert (await client.get(f"/v1/spec-flows/{d['id']}")).json()["dss_changed"] is None
        rows = {x["name"]: x for x in d["rows"]}
        # 사람이 QM55C 수량을 5 로 고침(→ 다시 가져와도 그대로) · QB43C 는 그대로(→ DSS 값 4)
        d = (await client.patch(f"/v1/spec-flows/{d['id']}/rows/{rows['Smart Signage QM55C']['key']}", json={"qty": 5})).json()
        assert next(x for x in d["rows"] if x["name"] == "Smart Signage QM55C")["qty_edited"] is True

        r = await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-01", "ver": 2, "value": _dss_v2(), "md": "- 공간 3"})
        assert r.status_code == 200, r.text
        g = (await client.get(f"/v1/spec-flows/{d['id']}")).json()
        ch = g["dss_changed"]
        assert ch == {"from": "DSS-01 v1", "to": "DSS-01 v2", "ref_changed": False, "added": 1, "removed": 1, "changed": 2,
                      "added_names": ["Smart Signage QH55C"], "removed_names": ["The Wall IAB 146\""]}
        # 다른 고침 응답은 차이를 계산하지 않는다(null) — 화면은 GET 값을 유지
        assert (await client.patch(f"/v1/spec-flows/{d['id']}", json={"title": "용산 시트"})).json()["dss_changed"] is None

        r = await client.post(f"/v1/spec-flows/{d['id']}:resync-dss")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["dss_changed"] is None and d["dss_ver"] == 2
        rows = {x["name"]: x for x in d["rows"]}
        assert list(rows) == ["The Wall IAB 146\"", "Smart Signage QM55C", "Smart Signage QB43C", "Smart Signage QH55C"]
        wall = rows["The Wall IAB 146\""]
        assert wall["dss_status"] == "removed" and wall["warnings"][0]["kind"] == "dss_removed" and wall["warnings"][0]["text"].startswith("DSS에서 빠짐")
        new = rows["Smart Signage QH55C"]
        assert new["by"] == "dss" and new["dss_status"] == "added" and new["qty"] == 2 and new["spaces"] == ["로비"]
        assert new["display_name"] == "QH55C" and new["match"] == "code" and new["cells"]["size_resolution"].startswith('55"')
        assert rows["Smart Signage QM55C"]["qty"] == 5 and rows["Smart Signage QM55C"]["qty_note"] == "로비 3 · 라운지 1"   # 원문은 DSS, 수량은 사람 값
        assert rows["Smart Signage QB43C"]["qty"] == 4 and rows["Smart Signage QB43C"]["by"] == "ai-accepted"
        lr = d["last_resync"]
        assert lr["from"] == "DSS-01 v1" and lr["to"] == "DSS-01 v2"
        assert lr["added"] == ["Smart Signage QH55C"] and lr["removed"] == ["The Wall IAB 146\""] and lr["kept_qty"] == ["Smart Signage QM55C"]
        assert "Smart Signage QB43C" in lr["updated"]
        assert d["counts"]["total"] == 4 and d["counts"]["warnings"] >= 2
        assert (await client.get(f"/v1/spec-flows/{d['id']}")).json()["dss_changed"] is None
        # 빠진 행만 지울 수 있다
        r = await client.delete(f"/v1/spec-flows/{d['id']}/rows/{rows['Smart Signage QM55C']['key']}")
        assert r.status_code == 422 and r.json()["error"]["code"] == "ROW_IN_DSS"
        d = (await client.delete(f"/v1/spec-flows/{d['id']}/rows/{wall['key']}")).json()
        assert [x["name"] for x in d["rows"]] == ["Smart Signage QM55C", "Smart Signage QB43C", "Smart Signage QH55C"]
        assert (await client.get(f"/v1/spec-flows/{d['id']}")).json()["dss_changed"] is None

        # DSS 자체가 바뀜(분기 등 다른 ref) — 내용이 같아도 알리고, 다시 가져오면 stages.sp.from 이 새 DSS
        await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-02", "ver": 1, "value": _dss_v2(), "md": "- 공간 3"})
        ch = (await client.get(f"/v1/spec-flows/{d['id']}")).json()["dss_changed"]
        assert ch["ref_changed"] is True and ch["from"] == "DSS-01 v2" and ch["to"] == "DSS-02 v1" and ch["added"] == ch["removed"] == 0
        d = (await client.post(f"/v1/spec-flows/{d['id']}:resync-dss")).json()
        assert d["dss_ref"] == "DSS-02" and d["last_resync"]["added"] == [] and d["dss_changed"] is None
        out = (await client.post(f"/v1/spec-flows/{d['id']}:finish")).json()
        assert out["stage"]["from"] == "DSS-02" and [m["name"] for m in out["stage"]["models"]][-1] == "Smart Signage QH55C"
        assert out["stage"]["models"][-1]["by"] == "dss"
        # 다시 가져온 DSS 에 빠졌던 제품이 돌아오면 표시가 added 로 바뀐다(경고 없음)
        await sb.put(f"/v1/flows/{f['id']}/stages/dss", json={"ref": "DSS-02", "ver": 2, "value": DSS_VALUE, "md": "- 공간 3"})
        d = (await client.post(f"/v1/spec-flows/{d['id']}:resync-dss")).json()
        rows = {x["name"]: x for x in d["rows"]}
        assert rows["The Wall IAB 146\""]["dss_status"] == "added" and rows["Smart Signage QH55C"]["dss_status"] == "removed"
        assert not any(w["kind"] == "dss_removed" for w in rows["The Wall IAB 146\""]["warnings"])


async def test_spec_flow_resync_needs_storyboard_dss(client, env):
    async with testing.api_client(env["storyboard"]) as sb:
        f = await _sb(sb)
        d = (await client.post("/v1/spec-flows", json={"sb_id": f["id"]})).json()
    r = await client.post("/v1/spec-flows/sfl_nope:resync-dss")
    assert r.status_code == 404
    assert (await client.get("/v1/spec-flows/sfl_nope")).status_code == 404
    assert d["id"]


async def test_spec_flow_draft_delete_and_dedupe(client, env):
    async with testing.api_client(env["storyboard"]) as sb, testing.api_client(env["workspace"]) as ws:
        f = await _sb(sb)
        r = await client.post("/v1/spec-flows", json={"sb_id": f["id"]})
        assert r.status_code == 201
        a = r.json()
        # 같은 Storyboard 로 다시 시작(Gate) → 저장 전 초안을 돌려준다(200, 같은 id)
        r = await client.post("/v1/spec-flows", json={"sb_id": f["id"]})
        assert r.status_code == 200 and r.json()["id"] == a["id"] and r.json()["code"] == a["code"]
        assert len((await client.get("/v1/spec-flows")).json()["items"]) == 1
        assert (await ws.get(f"/v1/items/{a['id']}")).status_code == 200
        # 초안 지우기 → 204 · 목록 · workspace 색인에서 빠짐 · 다시 지우면 404
        assert (await client.delete(f"/v1/spec-flows/{a['id']}")).status_code == 204
        assert (await client.get(f"/v1/spec-flows/{a['id']}")).status_code == 404
        assert (await client.delete(f"/v1/spec-flows/{a['id']}")).status_code == 404
        assert (await ws.get(f"/v1/items/{a['id']}")).status_code == 404
        assert (await client.get("/v1/spec-flows")).json()["items"] == []
        # 새 초안 → 저장 → 저장한 시트는 지울 수 없다(409 SAVED_CONTENT) · 다시 시작하면 새 초안(저장한 것은 Gate 가 「수정」으로 연다)
        b = (await client.post("/v1/spec-flows", json={"sb_id": f["id"]})).json()
        assert b["id"] != a["id"]
        assert (await client.post(f"/v1/spec-flows/{b['id']}:finish")).status_code == 200
        r = await client.delete(f"/v1/spec-flows/{b['id']}")
        assert r.status_code == 409 and r.json()["error"]["code"] == "SAVED_CONTENT"
        assert r.json()["error"]["message"] == "저장한 콘텐츠는 Storyboard에 연결돼 있어 지울 수 없어요"
        r = await client.post("/v1/spec-flows", json={"sb_id": f["id"]})
        assert r.status_code == 201 and r.json()["id"] != b["id"]
        c = r.json()
        # 지운 초안이 있어도 코드는 저장한 시트와 겹치지 않는다
        assert c["code"] != b["code"]
        # 복제본(분기 Storyboard)은 새 시트
        br = (await sb.post(f"/v1/flows/{f['id']}:branch", json={"stage": "sp"})).json()
        r = await client.post("/v1/spec-flows", json={"sb_id": br["id"]})
        assert r.status_code == 201 and r.json()["id"] not in (b["id"], c["id"])
