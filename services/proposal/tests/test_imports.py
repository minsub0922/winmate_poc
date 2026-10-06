"""§4.15 드래그 앤 드롭 · §3.13 다른 기능에서 보내기 · 실행 취소 · IMG4 이미지 자리."""
from __future__ import annotations

from typing import Any


async def setup(client: Any, *, links: list[dict[str, Any]] | None = None, scale: str = "320개 매장") -> str:
    r = await client.post("/v1/proposals", json={"start_mode": "blank", "title": "전국 매장 디지털 메뉴보드 전환",
                                                  "customer": {"name": "A 커피 프랜차이즈", "scale_text": scale},
                                                  "rq_ref": {"rq_id": "rq_acoffee", "version": 1}, "links": links or []})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    await client.put(f"/v1/proposals/{pid}/type", json={"type": "standard"})
    await client.put(f"/v1/proposals/{pid}/industry", json={"keep_default": True})
    return pid


async def test_mi_sidebar_extract_apply(client: Any, ctx: Any) -> None:
    pid = await setup(client)
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "mi", "via": "drag_sidebar",
                                                               "source": {"feature": "MI", "ref_id": "mi_acoffee"}})
    assert r.status_code == 202, r.text
    imp_id = r.json()["import_id"]
    await ctx.run_jobs()
    imp = (await client.get(f"/v1/proposals/{pid}/imports/{imp_id}")).json()
    assert imp["status"] == "pending_confirm", imp
    assert imp["ex_count"] == 4
    assert [i["checked"] for i in imp["items"]] == [True, True, True, False]
    assert imp["items"][3]["line_label"] == "이 섹션엔 없는 시트 · 사용자 분석 시트로 추가 가능"
    assert imp["items"][0]["line_label"] == "→ 시장 규모 · 성장 · 성장 추이 템플릿"
    assert imp["intro"].startswith("MI 작업에서 이 섹션에 쓸 내용을 뽑았습니다.")
    # 페르소나까지 골라 반영 → 사용자 분석 시트가 구성에 추가(AC-093)
    keys = [i["key"] for i in imp["items"]]
    r = await client.post(f"/v1/proposals/{pid}/imports/{imp_id}:apply", json={"keys": keys})
    assert r.status_code == 202, r.text
    await ctx.run_jobs()
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    roles = [s["role"] for s in sv["sheets"]]
    assert "US" in roles, roles
    assert sv["sources"] and sv["sources"][0]["feature"] == "mi"
    assert all(s["status"] in ("ready", "updated") for s in sv["sheets"]), [s["status"] for s in sv["sheets"]]


async def test_handoff_include_keys_direct(client: Any, ctx: Any) -> None:
    pid = await setup(client)
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "mi", "via": "handoff",
                                                               "source": {"feature": "MI", "ref_id": "mi_acoffee", "handoff_id": "hof_1"},
                                                               "include_keys": ["mkt", "ops", "cmp"]})
    assert r.status_code == 202
    imp_id = r.json()["import_id"]
    await ctx.run_jobs()
    imp = (await client.get(f"/v1/proposals/{pid}/imports/{imp_id}")).json()
    assert imp["status"] == "applied", imp                                 # pending_confirm 없이(AC-098)
    sv = (await client.get(f"/v1/proposals/{pid}/sections/mi")).json()
    assert "US" not in [s["role"] for s in sv["sheets"]]


async def test_spec_handoff_ack_and_confirm_items(client: Any, ctx: Any) -> None:
    pid = await setup(client)
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "spec", "via": "handoff",
                                                               "source": {"feature": "spec", "ref_id": "sp_qmc", "handoff_id": "sho_1"}})
    assert r.status_code == 202, r.text
    await ctx.run_jobs()
    acks = [c for c in ctx.stubs.calls.get("spec", []) if c.get("op") == "ack"]
    assert acks and acks[0]["body"]["result"] == "applied"
    sv = (await client.get(f"/v1/proposals/{pid}/sections/spec")).json()
    sc = next(s for s in sv["sheets"] if s["role"] == "SC")
    sh = (await client.get(f"/v1/proposals/{pid}/sheets/{sc['id']}")).json()
    assert sh["confirm_items"], sh                                        # [확정 필요] 칸 → 확인 항목(AC-100)
    assert sh["confirm_items"][0]["tag"] == "수치"


async def test_product_case_solution_drop_and_undo(client: Any, ctx: Any) -> None:
    pid = await setup(client, links=[{"feature": "birdseye", "ref_id": "be_lobby"}])
    # 사례를 공간별 제품에 → 422(AC-097)
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "spaceProducts", "via": "drag_item",
                                                               "source": {"kind": "case", "ref": "dep_44", "label": "말리커피"}})
    assert r.status_code == 422 and r.json()["error"]["code"] == "DROP_NOT_ACCEPTED"
    await client.post(f"/v1/proposals/{pid}/sections/spaceProducts:fill", json={})
    await ctx.run_jobs()
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "spaceProducts", "via": "drag_item",
                                                               "source": {"kind": "product", "ref": {"kb_kind": "model", "id": "QM65C"},
                                                                          "label": "QM65C", "sub": "Smart Signage 65\""}})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["toast"] == "「QM65C」 추가됨 · \"카운터 · 메뉴보드\" 시트에 배치됨 · 수량 320", res   # AC-091
    assert res["source_chip"]["label"] == "QM65C"
    assert res["confirm_item_ids"]                                          # 수량 가정
    await ctx.run_jobs()
    sv = (await client.get(f"/v1/proposals/{pid}/sections/spaceProducts")).json()
    target = next(s for s in sv["sheets"] if s["id"] == res["affected_sheet_ids"][0])
    assert target["status_label"] == "업데이트됨"
    # 실행 취소(AC-092)
    r = await client.post(f"/v1/proposals/{pid}/imports/{res['import_id']}:undo")
    assert r.status_code == 200, r.text
    assert r.json()["removed_link_ids"]
    # 사례(AC-094)
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "cases", "via": "drag_item",
                                                               "source": {"kind": "case", "ref": "dep_44", "label": "말리커피 - 삼성 스마트 사이니지(홍보용)"}})
    assert r.status_code == 200, r.text
    assert r.json()["toast"].startswith("새 시트 \"사례 · 말리커피\"이 추가됨"), r.json()
    cs = (await client.get(f"/v1/proposals/{pid}/sections/cases")).json()
    assert any(x["ref"] == "kb:case:dep_44" for x in cs["sources"]), cs["sources"]          # 셸 참조(팝오버 「✓ 추가됨」)
    # 솔루션(AC-095)
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "solution", "via": "drag_item",
                                                               "source": {"kind": "solution", "ref": "sol_vxt", "label": "Samsung VXT"}})
    assert r.status_code == 200, r.text
    assert r.json()["toast"].endswith("VXT 전용 시트 3장(소개 · 구성도 · 공간 시나리오)이 추가됨") or "전용 시트 3장" in r.json()["toast"], r.json()
    await ctx.run_jobs()
    sol = (await client.get(f"/v1/proposals/{pid}/sections/solution")).json()
    assert any(s["template"] == "VXT-I" for s in sol["sheets"]), [s["template"] for s in sol["sheets"]]


async def test_delete_releases_spec_and_vp_links(client: Any, ctx: Any) -> None:
    """제안서를 지우면 Spec 연결(`DELETE /v1/links?proposal_id=`) · VP 「연결된 제안서」(`:release-proposal`)도 거둔다(통합)."""
    pid = await setup(client, links=[{"feature": "vp", "ref_id": "vp_1"}])
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "spec", "via": "handoff",
                                                               "source": {"feature": "spec", "ref_id": "sp_qmc", "handoff_id": "sho_1"}})
    assert r.status_code == 202, r.text
    await ctx.run_jobs()
    feats = {ln["feature"] for ln in (await client.get(f"/v1/proposals/{pid}/links")).json()["links"]}
    assert {"spec", "vp"} <= feats, feats
    r = await client.delete(f"/v1/proposals/{pid}")
    assert r.status_code in (200, 204), r.text
    rel = [c for c in ctx.stubs.calls.get("spec", []) if c.get("op") == "release_links"]
    assert [(c["proposal_id"], c["sheet_id"]) for c in rel] == [(pid, None)]
    vrel = [c for c in ctx.stubs.calls.get("vp", []) if c.get("op") == "release"]
    assert [(c["vp_id"], c["body"]["proposal_id"]) for c in vrel] == [("vp_1", pid)]


async def test_undo_spec_import_releases_that_sheet_link(client: Any, ctx: Any) -> None:
    """Spec 반입을 실행 취소하면 그 시트의 Spec 연결만 거둔다(`DELETE /v1/links?proposal_id=&sheet_id=`, 통합)."""
    pid = await setup(client)
    r = await client.post(f"/v1/proposals/{pid}/imports", json={"section_key": "spec", "via": "handoff",
                                                               "source": {"feature": "spec", "ref_id": "sp_qmc", "handoff_id": "sho_1"}})
    imp_id = r.json()["import_id"]
    await ctx.run_jobs()
    r = await client.post(f"/v1/proposals/{pid}/imports/{imp_id}:undo")
    assert r.status_code == 200, r.text
    rel = [c for c in ctx.stubs.calls.get("spec", []) if c.get("op") == "release_links"]
    assert [(c["proposal_id"], c["sheet_id"]) for c in rel] == [(pid, "sp_qmc")]
