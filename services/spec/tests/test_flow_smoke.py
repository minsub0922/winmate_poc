"""기본 흐름(SP1 → SP2 → SP3G → SP3) — 실제 kb 데이터(QM55C · QB55C)."""
from __future__ import annotations

from sp_helpers import QB55C, QM55C


async def test_basic_flow_real_kb(ctx, client):
    r = await client.post("/v1/sheets", json={"start": "model", "products": [QM55C]})
    assert r.status_code == 201, r.text
    s = r.json()
    sid = s["id"]
    assert s["kind"] == "single"
    assert s["products"][0]["bubble_label"] == "Smart Signage QM55C"
    r = await client.post(f"/v1/sheets/{sid}/products", json={"refs": [f"kb:model:mdl_{QB55C}"]})
    assert r.status_code == 200, r.text
    s = r.json()["sheet"]
    assert s["kind"] == "compare"
    r = await client.patch(f"/v1/sheets/{sid}", json={"step": 2})
    s = r.json()
    assert s["title"] == 'QMC vs QBC 55" 비교'
    assert s["step"] == 2
    assert s["agent"]["sp2"].startswith('두 모델은 같은 55" 4K 사이니지지만 밝기(500 vs 350nit)와 운영 시간(24/7 vs 16/7)이 다릅니다.')
    assert s["agent"]["sp2_user"] == "제품 2개 · Smart Signage QM55C / QB55C"
    assert [i["key"] for i in s["items"] if i["checked"]] == ["size_resolution", "brightness_contrast", "operation_hours", "power", "player_os",
                                                             "magicinfo", "warranty"]
    r = await client.post(f"/v1/sheets/{sid}/generate", json={})
    assert r.status_code == 202, r.text
    r2 = await client.post(f"/v1/sheets/{sid}/generate", json={})
    assert r2.status_code == 409 and r2.json()["error"]["code"] == "RUN_IN_PROGRESS"
    n = await ctx.run_jobs()
    assert n >= 1
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    assert s["step"] == 3
    t = s["table"]
    assert t["title"] == 'Smart Signage 55" 비교 — QM55C vs QB55C'
    labels = [r["label"] for r in t["rows"]]
    assert labels[:3] == ["화면 크기 · 해상도", "밝기 · 명암비", "운영 시간"]
    bright = t["rows"][1]["cells"]
    assert bright[0]["text"].startswith("500 nit") and bright[0]["win"] is True
    assert "4,000:1" in bright[0]["text"]
    # 실제 kb 에는 소비전력 Typical · Max 와 보증 연수가 없다 → 값 확인(지어내지 않음)
    assert s["checks"]["open"] >= 2
    kinds = {(c["title"]) for c in s["checks"]["items"]}
    assert "소비전력 (일반 · 최대) · QB55C" in kinds
    assert s["ui_status"] == "check"
