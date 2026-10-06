"""§9.2 제품 입력(SP1 · SP1Product) · §9.3 조건으로 찾기(SP1C)."""
from __future__ import annotations

import time

from sp_helpers import QB55C, QH55C, QM55C, QM65C, use_kb_fix_55

SENTENCE = 'C 물류센터 관제실에 24시간 켜 둘 55" 전후 벽걸이 디스플레이가 필요해요'


async def test_products_input(ctx, client):
    # 13: 첫 제품 → POST /v1/sheets(single), 둘째 → compare
    r = await client.post("/v1/sheets", json={"start": "model", "products": [QM55C]})
    s = r.json()
    sid = s["id"]
    assert s["kind"] == "single" and s["resume_route"] == f"/spec/{sid}/products"
    r = await client.post(f"/v1/sheets/{sid}/products", json={"refs": [QB55C]})
    assert r.json()["added"] == [QB55C] and r.json()["sheet"]["kind"] == "compare"
    # 14: 같은 모델 다시 → 그대로, 9번째 → 422 PRODUCT_LIMIT
    r = await client.post(f"/v1/sheets/{sid}/products", json={"refs": [f"kb:model:mdl_{QM55C}"]})
    assert r.json()["added"] == [] and r.json()["skipped"] == [{"ref": f"kb:model:mdl_{QM55C}", "reason": "duplicate"}]
    assert len(r.json()["sheet"]["products"]) == 2
    more = ["LH43QMCEBGCXKR", "LH50QMCEBGCXKR", QM65C, QH55C, "LH75QMCEBGCXKR", "LH85QMCEBGCXKR"]
    r = await client.post(f"/v1/sheets/{sid}/products", json={"refs": more})
    assert len(r.json()["sheet"]["products"]) == 8
    r = await client.post(f"/v1/sheets/{sid}/products", json={"refs": ["LH32QMCEBGCXKR"]})
    assert r.status_code == 422 and r.json()["error"] == {"code": "PRODUCT_LIMIT", "message": "한 시트에 8개까지 비교할 수 있어요.",
                                                          "details": {"limit": 8}}
    # 15: 그대로 추가 → 점선(custom) 버블
    r = await client.post("/v1/sheets", json={"start": "model", "products": ["custom:고객사 자체 POS 단말"]})
    p = r.json()["products"][0]
    assert (p["ref"], p["custom"], p["bubble_label"]) == ("custom:고객사 자체 POS 단말", True, "고객사 자체 POS 단말")
    # 20: 버블 제거 → kind 재계산
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    for p in s["products"][1:]:
        r = await client.delete(f"/v1/sheets/{sid}/products/{p['id']}")
    assert r.json()["kind"] == "single"


async def test_combos_and_explorer(ctx, client):
    # 16: 실제 kb + combos.yaml → QMC 43 / 50 / 55 만
    combos = (await client.get("/v1/combos")).json()["items"]
    assert [c["label"] for c in combos] == ["QMC 43 / 50 / 55"]
    assert combos[0]["model_codes"] == ["LH43QMCEBGCXKR", "LH50QMCEBGCXKR", QM55C]
    # 19: 작업 없이 팝오버에서 추가 → start explorer
    r = await client.post("/v1/sheets", json={"start": "explorer", "products": [QM55C]})
    sid = r.json()["id"]
    assert r.json()["start"] == "explorer"
    # 16: 칩 → 없는 것만 추가
    r = await client.post(f"/v1/sheets/{sid}/products", json={"refs": combos[0]["refs"], "source": "input"})
    assert len(r.json()["added"]) == 2 and len(r.json()["sheet"]["products"]) == 3
    # 18: 팝오버 `현재 작업에 추가` — QM65C
    r = await client.post(f"/v1/sheets/{sid}/products", json={"refs": [f"kb:model:mdl_{QM65C}"], "source": "explorer"})
    assert r.json()["added"] == [f"kb:model:mdl_{QM65C}"]
    refs = (await client.get(f"/v1/sheets/{sid}/products")).json()["items"]
    assert refs[-1]["ref"] == f"kb:model:mdl_{QM65C}" and refs[-1]["model_code"] == QM65C


async def test_find_parse(ctx, client):
    r = await client.post("/v1/sheets", json={"start": "find"})
    sid = r.json()["id"]
    assert r.json()["finder"]["conditions"]["brightness"] == "desc"
    r = await client.post(f"/v1/sheets/{sid}/finder:parse", json={"text": SENTENCE})
    assert r.status_code == 202
    await ctx.run_jobs()
    s = (await client.get(f"/v1/sheets/{sid}")).json()
    st = s["finder"]
    # 21: 칩 · 필수 · 제목 · 사용자 말풍선
    c = st["conditions"]
    assert (c["sizes"], c["brightness"], c["usage"], c["install"]) == (["55"], "desc", ["monitoring"], ["wall"])
    assert c["required"] == ["continuous_operation", "wall"]
    assert s["suggested_title"] == "C 물류센터 관제실 후보 비교" and s["customer_name"] == "C 물류센터"
    assert s["agent"]["user_text"] == SENTENCE
    calls = ctx.ai.calls_of("sp.parse_conditions")
    assert len(calls) == 1 and calls[0]["confidential"] is True


async def test_find_cards_kb_fix(ctx, client, monkeypatch):
    use_kb_fix_55(monkeypatch)
    r = await client.post("/v1/sheets", json={"start": "find"})
    sid = r.json()["id"]
    cond = {"sizes": ["55"], "brightness": "desc", "usage": ["monitoring"], "install": ["wall"], "required": ["continuous_operation", "wall"]}
    n_ai = len(ctx.ai.calls)
    t0 = time.perf_counter()
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"conditions": cond})).json()
    dt = time.perf_counter() - t0
    # 22: 카드 순서 · 점수 · 값
    cards = [(x["display_name"], x["ok"], x["total"], x["out"]) for x in st["candidates"]]
    assert cards == [("QH55C", 4, 4, False), ("QM55C", 4, 4, False), ("QM65C", 3, 4, True), ("QB55C", 3, 4, True)]
    rows = {x["display_name"]: {r["key"]: r for r in x["rows"]} for x in st["candidates"]}
    assert rows["QH55C"]["brightness"]["value_text"] == "700 nit · 고휘도" and rows["QM55C"]["brightness"]["value_text"] == "500 nit"
    assert rows["QM65C"]["size"]["value_text"] == '65" · 조건 밖'
    assert (rows["QB55C"]["operation"]["value_text"], rows["QB55C"]["operation"]["state"]) == ("16시간 · 조건 밖", "no")
    assert st["catalog_version"] == "2026-10" and st["total_candidates"] == 4
    assert next(x for x in st["candidates"] if x["display_name"] == "QH55C")["series_label"] == "스마트 사이니지 QHC"
    # 23: 에이전트
    assert st["agent_text"] == ("조건에 맞는 후보 4개를 찾았습니다. 필수 조건(24시간 운영 · 벽걸이)을 먼저 맞추고 밝기가 높은 순으로 정렬했어요. "
                                "시트에 넣을 모델을 고르면 비교표로 만듭니다.")
    # 101: LLM 0 · 1초 안(제안 목표)
    assert len(ctx.ai.calls) == n_ai and dt < 3.0
    # 24: 조건 밖 숨기기 → 2장
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"hide_out": True})).json()
    assert [x["display_name"] for x in st["candidates"]] == ["QH55C", "QM55C"]
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"hide_out": False})).json()
    # 26: 필수 24시간 운영 끔 → 운영 행 사라짐, QB55C 조건 3/3
    cond2 = {**cond, "required": ["wall"], "off": ["required:continuous_operation"]}
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"conditions": cond2})).json()
    qb = next(x for x in st["candidates"] if x["display_name"] == "QB55C")
    assert (qb["ok"], qb["total"], qb["out"]) == (3, 3, False) and all(r["key"] != "operation" for r in qb["rows"])
    # 27: MagicINFO 필수 → CMS 행, QH55C 확인 필요(VXT 만) · QM55C ok, `+ 필수로 지정 → 55"`
    cond3 = {**cond, "required": ["continuous_operation", "wall", "magicinfo", "size:55"]}
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"conditions": cond3})).json()
    cms = {x["display_name"]: next(r for r in x["rows"] if r["key"] == "cms") for x in st["candidates"]}
    assert cms["QH55C"]["state"] == "check" and cms["QH55C"]["value_text"] == "확인 필요"
    assert cms["QM55C"]["state"] == "ok" and cms["QM55C"]["value_text"] == "MagicINFO"
    assert st["agent_text"].startswith("조건에 맞는 후보") and '55"' in st["agent_text"]
    # 25: 담기 2개 → `2개로 비교표 만들기` → 제품 QH55C · QM55C(source find) · step 2
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"conditions": cond})).json()
    refs = [x["ref"] for x in st["candidates"] if x["display_name"] in ("QH55C", "QM55C")]
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"selected": refs})).json()
    assert [x["display_name"] for x in st["candidates"] if x["selected"]] == ["QH55C", "QM55C"]
    r = await client.post(f"/v1/sheets/{sid}/finder:commit", json={"selected": refs, "to": "items"})
    s = r.json()
    assert [(p["display_name"], p["source"]) for p in s["products"]] == [("QH55C", "find"), ("QM55C", "find")]
    assert s["step"] == 2 and s["resume_route"] == f"/spec/{sid}/items"


async def test_find_direct_input(ctx, client, monkeypatch):
    use_kb_fix_55(monkeypatch)
    r = await client.post("/v1/sheets", json={"start": "find"})
    sid = r.json()["id"]
    st = (await client.put(f"/v1/sheets/{sid}/finder", json={"conditions": {"sizes": ["55"], "brightness": "desc"}})).json()
    ref = st["candidates"][0]["ref"]
    # 28: 모델명으로 직접 입력 → 선택 모델이 버블로 들어간 SP1
    s = (await client.post(f"/v1/sheets/{sid}/finder:commit", json={"selected": [ref], "to": "products"})).json()
    assert s["step"] == 1 and [p["ref"] for p in s["products"]] == [ref]
    r = await client.post(f"/v1/sheets/{sid}/finder:commit", json={"selected": [], "to": "items"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "NO_PRODUCTS"
