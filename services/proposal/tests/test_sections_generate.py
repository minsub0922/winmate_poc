"""PRS(섹션 작성) · 템플릿 고르기 · 시트 편집 · 값 · PR6 · PR7(PPTX 생성 → v1)."""
from __future__ import annotations

from typing import Any


async def make(client: Any, **body: Any) -> dict[str, Any]:
    r = await client.post("/v1/proposals", json={"start_mode": "blank", **body})
    assert r.status_code == 201, r.text
    return r.json()


async def standard_with_mi(client: Any, *, industry: bool = False) -> str:
    p = await make(client, title="전국 매장 디지털 메뉴보드 전환", customer={"name": "A 커피 프랜차이즈", "scale_text": "320개 매장"},
                   rq_ref={"rq_id": "rq_acoffee", "version": 1}, links=[{"feature": "mi", "ref_id": "mi_acoffee"}])
    pid = p["id"]
    assert (await client.put(f"/v1/proposals/{pid}/type", json={"type": "standard"})).status_code == 200
    assert (await client.post(f"/v1/proposals/{pid}/composition:start")).status_code == 200
    r = await client.put(f"/v1/proposals/{pid}/industry", json={"decided": True} if industry else {"keep_default": True})
    assert r.status_code == 200, r.text
    return pid


async def test_mi_section_fill(client: Any, ctx: Any) -> None:
    pid = await standard_with_mi(client)
    r = await client.get(f"/v1/proposals/{pid}/sections/mi")
    assert r.status_code == 200, r.text
    sv = r.json()
    assert sv["needs_fill"] is True
    assert sv["accept_chips"] == ["MI 작업 (사이드바)", "유관 사례"]
    assert sv["quick_actions"] == ["수치 근거 보강", "더 간결하게", "템플릿 바꾸기"]
    assert sv["placeholder"] == "Market Intelligence 수정 요청 (예: 시트 순서 바꾸기, 내용 보강)"
    assert sv["next"]["label"] == "다음: Value Props"
    assert sv["prev"]["route"].endswith("/compose")
    assert [s["status_label"] for s in sv["sheets"]] == ["자료 필요"] * 3
    r = await client.post(f"/v1/proposals/{pid}/sections/mi:fill", json={"reason": "enter"})
    assert r.status_code == 202, r.text
    job = r.json()["job_id"]
    # 진행 중 다시 불러도 같은 잡
    r2 = await client.post(f"/v1/proposals/{pid}/sections/mi:fill", json={"reason": "enter"})
    assert r2.json()["job_id"] == job
    assert (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()["status"] == "filling"
    await ctx.run_jobs()
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    assert sv["status"] == "ready", sv
    assert sv["needs_fill"] is False
    tags = {s["role"]: s["tag"] for s in sv["sheets"]}
    assert tags == {"MS": "자동 · MS-B", "CB": "자동 · CB-C", "CP": "자동 · CP-A"}, tags
    assert [x["label"] for x in sv["sources"]][0].startswith("MI · ")
    ms = next(s for s in sv["sheets"] if s["role"] == "MS")
    sh = (await client.get(f"/v1/proposals/{pid}/sheets/{ms['id']}")).json()
    assert sh["content"]["title"]
    assert "chart" in sh["content"]["slots"], sh["content"]
    assert sh["slot_schema"]["slots"]
    assert sh["template"]["reason"].startswith("연결된 MI에 연도별 시장 규모")
    # 잡 이벤트: step · progress · done
    from winmate_common.jobs import jobs
    kinds = {e.get("type") for _, e in await jobs().events(job)}
    assert {"step", "progress", "done"} <= kinds, kinds          # AC-201
    # 편집 · If-Match
    r = await client.patch(f"/v1/proposals/{pid}/sheets/{ms['id']}", json={"ops": [{"op": "set", "path": "/title", "value": "시장은 크고 빠르게 큽니다"}]},
                           headers={"If-Match": str(sh["rev"])})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["sheet"]["content"]["title"] == "시장은 크고 빠르게 큽니다"
    assert res["change_ids"]
    r = await client.patch(f"/v1/proposals/{pid}/sheets/{ms['id']}", json={"ops": [{"op": "set", "path": "/title", "value": "x"}]},
                           headers={"If-Match": str(sh["rev"])})
    assert r.status_code == 409 and r.json()["error"]["code"] == "REV_CONFLICT"


async def test_template_pick_and_auto(client: Any, ctx: Any) -> None:
    pid = await standard_with_mi(client, industry=True)
    await client.post(f"/v1/proposals/{pid}/sections/mi:fill", json={})
    await ctx.run_jobs()
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    ms = next(s for s in sv["sheets"] if s["role"] == "MS")
    assert ms["tag"] == "자동 · MI-FB-A"
    r = await client.get(f"/v1/proposals/{pid}/sheets/{ms['id']}/template-options")
    assert r.status_code == 200, r.text
    to = r.json()
    codes = [v["code"] for v in to["variants"]]
    assert codes == ["MI-FB-A", "MS-A", "MS-B", "MS-C", "MS-D"], codes
    assert to["header_label"] == "시장 규모 · 성장 · “이 시장은 크고, 커지고 있다”를 보여줄 템플릿 5종"
    r = await client.put(f"/v1/proposals/{pid}/sheets/{ms['id']}/template", json={"mode": "pinned", "code": "MS-C"})
    assert r.status_code == 200, r.text
    assert r.json()["sheets"][0]["template"]["tag"] == "MS-C · 직접"
    # 섹션 재생성 뒤에도 고정 유지(AC-081)
    await client.post(f"/v1/proposals/{pid}/sections/mi:fill", json={"reason": "regen"})
    await ctx.run_jobs()
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    assert next(s for s in sv["sheets"] if s["role"] == "MS")["tag"] == "MS-C · 직접"
    # 섹션 전체 자동으로(AC-087)
    r = await client.post(f"/v1/proposals/{pid}/sections/mi/templates:auto", json={"include_pinned": True})
    assert r.status_code == 200, r.text
    assert next(s for s in r.json()["sheets"] if s["role"] == "MS")["tag"] == "자동 · MI-FB-A"


async def test_empty_section_and_cases(client: Any, ctx: Any) -> None:
    p = await make(client, title="전국 매장 디지털 메뉴보드 전환", customer={"name": "A 커피 프랜차이즈"}, rq_ref={"rq_id": "rq_acoffee", "version": 1})
    pid = p["id"]
    await client.put(f"/v1/proposals/{pid}/type", json={"type": "standard"})
    await client.put(f"/v1/proposals/{pid}/industry", json={"keep_default": True})
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    assert sv["needs_fill"] is False                        # AC-061
    assert sv["sources"] == []
    assert sv["empty_sources_label"] == "아직 연결된 자료가 없어요 — 아래 영역에 끌어다 놓으세요"
    cv = (await client.get(f"/v1/proposals/{pid}/sections/cases")).json()
    assert cv["needs_fill"] is True                         # AC-062: 연결 없이도 kb 사례
    await client.post(f"/v1/proposals/{pid}/sections/cases:fill", json={})
    await ctx.run_jobs()
    cv = (await client.get(f"/v1/proposals/{pid}/sections/cases")).json()
    assert cv["status"] == "ready", cv
    assert all(s["role"] == "CD" for s in cv["sheets"])


async def test_generate_v1_pptx(client: Any, ctx: Any) -> None:
    pid = await standard_with_mi(client)
    await client.post(f"/v1/proposals/{pid}/sections/mi:fill", json={})
    await ctx.run_jobs()
    r = await client.get(f"/v1/proposals/{pid}/design")
    assert r.status_code == 200, r.text
    dv = r.json()
    assert dv["design"]["master_id"] == "samsung_b2b"
    assert [m["id"] for m in dv["masters"]][:3] == ["samsung_b2b", "retail_fnb", "simple_white"]
    assert dv["sheet_templates"]["label"].startswith("미리 만든 템플릿 ")
    r = await client.put(f"/v1/proposals/{pid}/design", json={"brand_hex": "#00704"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_HEX"
    r = await client.put(f"/v1/proposals/{pid}/design", json={"brand_hex": "#00704A", "cover": {"enabled": False}})
    assert r.status_code == 200, r.text
    r = await client.post(f"/v1/proposals/{pid}:generate", json={"scope": "all", "infer_empty": False})
    assert r.status_code == 202, r.text
    assert (await client.get(f"/v1/proposals/{pid}/result")).json()["status"] == "running"
    await ctx.run_jobs()
    rv = (await client.get(f"/v1/proposals/{pid}/result")).json()
    assert rv["status"] == "done", rv
    f = rv["file"]
    assert f["version"] == 1 and f["pptx_file_id"]
    assert f["name"].startswith("A커피_디지털메뉴보드_제안서_v1")
    assert rv["message"].startswith("표준 제안서 ")
    assert rv["thumbs"][0]["label"] == "01 표지"
    assert rv["thumbs"][1]["label"] == "02 목차"
    p = (await client.get(f"/v1/proposals/{pid}")).json()
    assert p["version"] == 1 and p["stage"] == "result"
    assert p["progress_label"] in ("PPTX v1 · 생성 완료", "PPTX 생성 · 사실 확인 중")
    sl = (await client.get(f"/v1/proposals/{pid}/slides")).json()
    assert sl["version_label"] == "v1 · 수정 0"
    # 파일이 진짜 PPTX
    from winmate_common.platform import file_bytes
    data, _mime = await file_bytes(f["pptx_file_id"])
    assert data[:2] == b"PK"
