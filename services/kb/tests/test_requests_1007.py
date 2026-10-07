"""docs/requests/kb.md 2026-10-06 ~ 10-07 요청: spec(보증 · 생애주기 · A3 단위 · 소비전력) · mi/competitor(R 태그 · 6업종 대응) ·
birdseye(/ 든 모델코드 · LED 크기 · 배치 규칙 파라미터 · 치수 정규화). 실제 KB 파일로 돈다."""
from __future__ import annotations

import pytest

QM55 = "LH55QMCEBGCXKR"
IWC12 = "LH012IWCMWS/XU"
IWC12_ENC = "LH012IWCMWS%2FXU"


@pytest.fixture
def okp(contract):
    """경로에 / 가 든 요청은 계약 경로 매칭(`[^/]+`)이 안 되므로 템플릿에 맞는 대표 경로로 검증한다."""

    def _okp(r, contract_path: str, method: str = "GET") -> dict:
        assert r.status_code == 200, r.text[:800]
        body = r.json()
        assert contract.find(method, contract_path) is not None, contract_path
        contract.validate_response(method, contract_path, r.status_code, body, r.headers.get("content-type", ""))
        return body

    return _okp


# ── birdseye 1: / 가 든 모델코드 ───────────────────────────

async def test_slash_model_code_detail_and_subresources(client, okp, contract):
    raw = okp(await client.get(f"/v1/models/{IWC12}"), "/v1/models/X")
    enc = okp(await client.get(f"/v1/models/{IWC12_ENC}"), "/v1/models/X")
    assert raw == enc
    assert raw["model_code"] == IWC12 and raw["id"] == f"mdl_{IWC12}" and raw["display_name"] == "IW012C"
    imgs = okp(await client.get(f"/v1/models/{IWC12_ENC}/images"), "/v1/models/X/images")
    assert imgs["total"] == len(imgs["items"]) > 0
    cs = okp(await client.get(f"/v1/models/{IWC12}/cases"), "/v1/models/X/cases")
    assert set(cs["counts"]) == {"model", "series", "usage"}
    lc = okp(await client.get(f"/v1/models/{IWC12}/lifecycle"), "/v1/models/X/lifecycle")
    assert lc["status"] == "on_sale" and lc["model_code"] == IWC12
    # 서비스 클라이언트는 %2F 로 부른다 — 계약 경로 매칭이 된다
    assert contract.find("get", f"/v1/models/{IWC12_ENC}").template == "/v1/models/{model_code}"
    assert contract.find("get", f"/v1/models/{IWC12_ENC}/lifecycle").template == "/v1/models/{model_code}/lifecycle"
    # 슬래시 없는 코드 · 끝 슬래시 · 없는 코드
    assert (await client.get(f"/v1/models/{QM55}/")).json()["model_code"] == QM55
    r = await client.get("/v1/models/LH012IWCMWS/ZZ")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    # 프린터 소모품 · 노트북처럼 다른 / 코드도
    assert (await client.get("/v1/models/SL-C2410ND/KRM")).json()["model_code"] == "SL-C2410ND/KRM"


async def test_slash_code_search_and_spec_table(client, ok):
    hit = ok(await client.get("/v1/models", params={"q": IWC12}))
    assert [r["model_code"] for r in hit["items"]][:1] == [IWC12]
    items = ok(await client.get("/v1/products/search", params={"q": IWC12, "kinds": "model"}))["items"]
    assert items and items[0]["model_code"] == IWC12
    t = ok(await client.post("/v1/spec/table", json={"models": [IWC12, "LH012IWAMWS/XU"]}), "POST")
    assert [m["model_code"] for m in t["models"]] == [IWC12, "LH012IWAMWS/XU"] and t["unresolved"] == []


# ── birdseye 2: LED 크기 · 픽셀 피치 ───────────────────────

async def test_led_size_is_not_pitch_code(client, ok, okp):
    rows = ok(await client.get("/v1/models", params={"category_id": "cat_led-signage", "limit": 100}))["items"]
    assert len(rows) == 10
    by = {r["model_code"]: r["values"] for r in rows}
    # 예전에는 LH012 · LH016 의 코드 숫자를 12" · 16" 로 읽었다(실제는 픽셀 피치 1.26 · 1.68 mm 코드)
    assert all(v["size"]["display"] == "—" and v["size"].get("inch") is None for v in by.values())
    assert by[IWC12]["pixel_pitch"]["display"] == "1.26 mm" and by[IWC12]["pixel_pitch"]["value"] == 1.26
    assert by[IWC12]["brightness"]["nit"] == 1000
    assert by["LH015IEACLS/KR"]["pixel_pitch"]["value"] == 1.5           # 정규 키(pixel_pitch_mm)가 있는 모델은 그대로
    d = okp(await client.get(f"/v1/models/{IWC12_ENC}"), "/v1/models/X")
    led = d["led"]
    assert led["pixel_pitch_mm"] == 1.26 and led["pitch_basis"] == "spec"
    assert led["unit_pixels"]["w"] == 640 and led["unit_pixels"]["h"] == 360
    assert led["unit_active_mm"] == {"w": 806.4, "h": 453.6, "basis": "unit_pixels × pixel_pitch_mm"}
    assert led["size_mentions"] == [] and d["dims_mm"] is None             # The Wall: 치수 · 화면 구성 원천 없음
    assert "1.26 mm" in d["title_line"] and '12"' not in d["title_line"]
    iac = okp(await client.get("/v1/models/LH015IACCHS%2FKR"), "/v1/models/X")
    assert iac["led"]["size_mentions"][0]["inch"] == 130 and iac["led"]["size_mentions"][0]["qualifier"] == "최대"
    assert "130인치" in iac["led"]["size_mentions"][0]["text"]
    assert iac["dims_mm"]["w"] == 2888.5 and iac["dims_mm"]["h"] == 1628.5 and iac["dims_mm"]["kind"] == "body"
    t = ok(await client.post("/v1/spec/table", json={"models": [IWC12]}), "POST")
    assert t["derived"][IWC12]["screen_size_inch"] is None
    assert ok(await client.get(f"/v1/models/{QM55}"))["led"] is None
    # LCD 사이니지 크기 규칙은 그대로(§9.2)
    qm = ok(await client.get("/v1/models", params={"q": "LH55QMC"}))["items"]
    assert next(r for r in qm if r["model_code"] == QM55)["values"]["size"]["display"] == '55"'


# ── birdseye 4 · spec: 치수 정규화 ─────────────────────────

async def test_dims_normalized(client, ok):
    d = ok(await client.get(f"/v1/models/{QM55}"))
    assert {k: d["dims_mm"][k] for k in ("w", "h", "d", "unit", "kind", "order")} == \
        {"w": 1237.9, "h": 708.8, "d": 28.5, "unit": "mm", "kind": "body", "order": "WxHxD"}
    assert d["dims_mm"]["attr"] == "크기 › 제품(가로x높이x깊이)" and d["dims_mm"]["raw"] == "1237.9 x 708.8 x 28.5 mm"
    assert {x["kind"] for x in d["dims_all"]} >= {"body", "package"}
    pr = ok(await client.get("/v1/models/SL-C2410ND%2FKRM"))              # 프린터: 가로x세로x높이 = W×D×H
    assert pr["dims_mm"]["order"] == "WxDxH" and pr["dims_mm"]["raw"] == "420 x 452.5 x 311.3 mm"
    assert (pr["dims_mm"]["w"], pr["dims_mm"]["h"], pr["dims_mm"]["d"]) == (420.0, 311.3, 452.5)
    t = ok(await client.post("/v1/spec/table", json={"models": [QM55, "SL-C2410ND/KRM"]}), "POST")
    assert t["derived"][QM55]["dims_mm"]["w"] == 1237.9
    assert t["derived"][QM55]["dimensions_mm"] == {"w": 1237.9, "h": 708.8, "d": 28.5, "unit": "mm", "raw": "1237.9 x 708.8 x 28.5 mm"}
    assert t["derived"]["SL-C2410ND/KRM"]["dims_mm"]["h"] == 311.3


def test_dims_parser_cases():
    from winmate_kb import dims as D

    p = D.parse_value("1,090 x 73 x 525 mm", "제품 치수 (WxHxD)", "본체 치수")
    assert (p["w"], p["h"], p["d"]) == (1090.0, 73.0, 525.0)
    p = D.parse_value("166.9 x 75.4 x 6.1", "크기(세로x가로x두께, mm)", "외관 사양")        # 휴대폰: H×W×D
    assert (p["w"], p["h"], p["d"], p["order"]) == (75.4, 166.9, 6.1, "HxWxD")
    p = D.parse_value("314.2 x 220.6 x 11.6", "크기 (가로x세로x두께)(mm)", "외관 사양")       # 태블릿: 세로 = 높이
    assert (p["w"], p["h"], p["d"]) == (314.2, 220.6, 11.6)
    p = D.parse_value("1191.936 (H) x 335.232 (V)", "엑티브 디스플레이 사이즈 (H x V) (mm)", "디스플레이")
    assert (p["w"], p["h"], p["d"]) == (1191.94, 335.23, None) and D.kind_of("디스플레이", "엑티브 디스플레이 사이즈 (H x V) (mm)") == "active_area"
    p = D.parse_value("13.1 cm x 20 cm", "가로 x 세로", "외관")
    assert (p["w"], p["h"]) == (131.0, 200.0)
    p = D.parse_value("898 x 500 x 405~755 mm", "외부 치수", "크기(가로 × 세로 × 높이)")      # 범위 축은 비운다 · 그룹 이름의 축 순서
    assert (p["w"], p["d"], p["h"], p["order_basis"]) == (898.0, 500.0, None, "group")
    assert D.parse_value("Φ175 x H:88 mm", "크기", "외관치수") is None
    assert not D.is_dim_label("기구사양", "VESA 마운트") and not D.is_dim_label("디스플레이", "픽셀 피치")
    assert not D.is_dim_label("인증정보", "안전 규격") and D.is_dim_label("치수 (가로 × 높이 × 깊이)", "외관")
    assert D.kind_of("크기", "스탠드제외(가로x높이x깊이)") == "without_stand" and D.kind_of("크기", "포장(가로x높이x깊이)") == "package"
    assert D.kind_of("실외기", "제품 치수 (W×H×D)") == "outdoor_unit" and D.kind_of("판넬", "제품 치수 (WxHxD)") == "panel"


# ── spec 1: 보증 ───────────────────────────────────────────

async def test_warranty(client, ok):
    w = ok(await client.get(f"/v1/models/{QM55}"))["warranty"]
    assert w["status"] == "statement_only" and w["years"] is None and w["months"] is None
    assert "소비자분쟁해결기준" in w["text"] and w["attr"] == "상품 기본정보 › 품질보증기준"
    assert w["source_ref"].startswith("occ_doc_spec_") and w["source_url"].endswith("#spec") and w["as_of"].startswith("2026-10-04")
    pr = ok(await client.post("/v1/spec/table", json={"models": ["SL-C2410ND/KRM", "mdl_SI-GFTQ40B1A1D"]}), "POST")["derived"]
    assert pr["SL-C2410ND/KRM"]["warranty"]["years"] == 1 and pr["SL-C2410ND/KRM"]["warranty"]["months"] == 12
    led_light = pr["SI-GFTQ40B1A1D"]["warranty"]
    assert led_light["status"] == "stated" and led_light["years"] == 2 and led_light["parts_years"] == 3
    lc = ok(await client.get("/v1/models/SL-C2410ND%2FKRM/lifecycle"))
    assert lc["warranty"]["years"] == 1
    from winmate_kb import specs
    from winmate_kb.index import idx

    I = idx()
    ac = next(mid for mid, m in I.models.items() if I.fam_l2(m["family_id"]) == "cat_ac-clean" and (specs.warranty(mid) or {}).get("text") == "3개월")
    assert specs.warranty(ac)["months"] == 3 and specs.warranty(ac)["years"] == 0.25
    fridge = idx().default_model("fam_G000183669")                        # PDP '10년 보증' 문구는 claims 로만(연수 아님)
    fw = specs.warranty(fridge)
    assert fw["years"] is None and fw["claims"] and "10년" in fw["claims"][0]["text"]


# ── spec 2: 생애주기 · 같은 계열 다른 세대 ──────────────────

async def test_lifecycle_successors(client, ok):
    lc = ok(await client.get("/v1/models/LH55WMBWBGCXKR/lifecycle"))
    assert lc["successor"] is None and lc["release_ym"] == "2022-10"
    assert [(s["model_code"], s["relation"], s["newer"], s["release_ym"]) for s in lc["successors"]] == \
        [("LH55WMFWBGCXKR", "similar", True, "2026-03")]
    assert "같은 계열(WM)" in lc["successors"][0]["reason"] and '같은 크기(55")' in lc["successors"][0]["reason"]
    newest = ok(await client.get("/v1/models/LH55WMFWBGCXKR/lifecycle"))
    assert newest["release_ym"] == "2026-03" and newest["successors"] == []                 # 더 오래된 세대는 주지 않는다
    gone = ok(await client.get("/v1/models/QM55R/lifecycle"))
    assert gone["status"] == "not_in_catalog" and gone["successor"] is None
    assert [(s["model_code"], s["newer"]) for s in gone["successors"]] == [(QM55, None)]
    full = ok(await client.get("/v1/models/LH55QMREBGCXKR/lifecycle"))
    assert [s["model_code"] for s in full["successors"]] == [QM55]
    led = ok(await client.get("/v1/models/LH008IWAMWS%2FXU/lifecycle"))
    assert [(s["model_code"], s["newer"]) for s in led["successors"]] == [("LH008IWCMWS/XU", True)]
    assert "픽셀 피치 코드(008 = 0.84 mm)" in led["successors"][0]["reason"]
    assert ok(await client.get("/v1/models/SL-C2410ND%2FKRM/lifecycle"))["successors"] == []   # 사이니지 밖은 규칙 없음
    assert ok(await client.get(f"/v1/models/{QM55}/lifecycle"))["sale_status_code"] == "17"


def test_sale_status_code_documented(env):
    """06-spec 요청 2: sale_status_code 값 표(관측값 · 뜻 미확인)를 계약 설명에."""
    from winmate_kb.main import app

    schemas = app.openapi()["components"]["schemas"]
    for name in ("ModelDetail", "FamilyItem", "Lifecycle"):
        desc = schemas[name]["properties"]["sale_status_code"].get("description", "")
        assert "'17'" in desc and "'15'" in desc and "코드표" in desc, name
    paths = app.openapi()["paths"]
    assert "/v1/models/{model_code}" in paths and "/v1/models/{model_code}/lifecycle" in paths   # 계약 경로는 그대로


def test_parse_ym():
    from winmate_kb.specs import parse_ym

    assert parse_ym("2024년 3월") == "2024-03" and parse_ym("26년 3월") == "2026-03" and parse_ym("2024.10") == "2024-10"
    assert parse_ym("미정") is None and parse_ym(None) is None


# ── spec 3: A3 화면 크기 단위 ──────────────────────────────

async def test_a3_screen_size_units(client, ok):
    async def a3(items):
        return ok(await client.post("/v1/query/A3", json={"items": items}), "POST")

    for val in ("55인치 이상", "55형이상", '55" 이상', "55”", "55'' 이상", "55 inch"):
        m = (await a3([{"name_raw": "화면 크기", "value_raw": val}]))["result"]["mapped"][0]
        assert (m["attr"], m["unit"], m["value"], m["value_cm"], m["unit_basis"]) == ("screen_size_inch", "inch", 55, 139.7, "value"), val
    env = await a3([{"name_raw": "화면 크기", "value_raw": "139.7cm 이상"}])
    m = env["result"]["mapped"][0]
    assert (m["attr"], m["value"], m["value_inch"], m["unit_basis"]) == ("screen_size_cm", 139.7, 55.0, "value")
    env = await a3([{"name_raw": "화면 크기(인치)", "value_raw": "139.7cm"}])
    assert env["result"]["mapped"][0]["attr"] == "screen_size_cm" and any("값이 cm" in x for x in env["needs_confirmation"])
    env = await a3([{"name_raw": "화면 크기", "value_raw": "55 이상"}])                     # 단위 없음 → KB 기본 cm + 확인 필요
    m = env["result"]["mapped"][0]
    assert m["attr"] == "screen_size_cm" and m["unit_basis"] == "default" and any("단위가 없어" in x for x in env["needs_confirmation"])
    env = await a3([{"name_raw": "화면 크기", "value_raw": "65”"}, {"name_raw": "화면 크기", "value_raw": "139.7cm 이상"}])  # 같은 이름 둘
    assert [(m["attr"], m["value"]) for m in env["result"]["mapped"]] == [("screen_size_inch", 65), ("screen_size_cm", 139.7)]
    env = await a3([{"name_raw": "크기", "value_raw": "55인치 이상"}, {"name_raw": "", "value_raw": "75'' 이상"},
                    {"name_raw": "밝기", "value_raw": "55인치"}])
    mapped = env["result"]["mapped"]
    assert [(m["name_raw"], m["attr"], m["value"], m["mapped_by"]) for m in mapped] == \
        [("크기", "screen_size_inch", 55, "inch_expression"), ("", "screen_size_inch", 75, "inch_expression")]
    assert env["result"]["unmapped"] == [{"name_raw": "밝기", "value_raw": "55인치"}]   # 이름이 다른 뜻이면 바꾸지 않는다


# ── spec 4: 소비전력 Typical · Max ─────────────────────────

async def test_power_modes(client, ok):
    t = ok(await client.post("/v1/spec/table", json={"models": ["LH55BEHHLBFXKR", QM55, IWC12, "LH015IEACLS/KR"]}), "POST")["derived"]
    beh = t["LH55BEHHLBFXKR"]["power"]
    assert beh["typical"]["value"] == 67.9 and beh["typical"]["unit"] == "W" and beh["typical"]["attr"] == "전원 › 소비전력 (Typical)"
    assert beh["max"] is None and {v["mode"] for v in beh["values"]} == {"typical", "on", "standby"}
    qm = t[QM55]["power"]
    assert qm["typical"] is None and qm["max"] is None
    assert [(v["mode"], v["raw"]) for v in qm["values"]] == [("on", "154 W"), ("sleep", "0.5 W")]
    iwc = t[IWC12]["power"]["max"]
    assert (iwc["value"], iwc["unit"], iwc["per_m2"], iwc["attr"]) == (410, "W/㎡", True, "Electrical Parameter › Power Consumption (Max)")
    iea = t["LH015IEACLS/KR"]["power"]["max"]
    assert iea["unit"] == "W/㎡" and iea["per_m2"] is True and iea["value"] == 367


# ── birdseye 3: 배치 규칙 ──────────────────────────────────

async def test_placement_rules_params(client, ok):
    sig = ok(await client.get("/v1/placement-rules", params={"category": "signage"}))
    ids = [r["id"] for r in sig["items"]]
    assert "pr_signage_size_by_distance" in ids and "pr_warn_power_distance" in ids and "pr_hvac_capacity_by_area" not in ids
    by_cat = ok(await client.get("/v1/placement-rules", params={"category": "cat_smart-signage"}))
    assert [r["id"] for r in by_cat["items"]] == ids                         # KB 분류 id 로도
    assert [r["id"] for r in ok(await client.get("/v1/placement-rules", params={"category": "cat_smart-signage__videowall"}))["items"]] == ids
    assert [r["id"] for r in ok(await client.get("/v1/placement-rules", params={"category": "signage_lcd"}))["items"]] == ids
    hv = ok(await client.get("/v1/placement-rules", params={"category": "cat_dvms"}))
    assert [r["id"] for r in hv["items"]] == ["pr_hvac_capacity_by_area", "pr_warn_power_distance"]
    for r in sig["items"]:
        assert r["param_status"] == "unfilled" and not r["active"] and r["source_tier"] == "T5_seed_draft"
        assert set(r["param_values"]) == set(r["params"]) and all(v is None for v in r["param_values"].values())
        assert r["missing_params"] == list(r["params"])
    size = next(r for r in sig["items"] if r["id"] == "pr_signage_size_by_distance")
    assert size["explanation_ko"] == "시청거리로 권장 화면 크기 범위 산정" and size["category_ids"] == ["cat_led-signage", "cat_smart-signage"]
    hvac = hv["items"][0]
    assert hvac["param_notes"] == {"kw_per_m2": "용도별 단위면적당 부하"}
    assert "param_status=approved" in sig["note"]
    lobby = ok(await client.get("/v1/placement-rules", params={"space": "menu_board_zone"}))
    assert "pr_menuboard_qty_by_counter" in [r["id"] for r in lobby["items"]]


# ── mi · competitor: 6업종 대응 · R 태그 ────────────────────

async def test_segments_mapping_observed(client, ok):
    body = ok(await client.get("/v1/segments"))
    by = {s["code"]: s for s in body["items"]}
    for code in ("FB", "RT", "HT", "OF", "RS", "ED", "PB", "MD", "MF", "FN"):
        assert by[code]["mapping"] is True and by[code]["mapping_basis"] == "seed" and by[code]["kr_vertical_ids"]
    expect = {"SV": ["kr_retail_fnb"], "TP": ["kr_hotel"], "VN": ["kr_hotel"], "ID": ["kr_construction"], "OE": ["kr_telecom"]}
    for code, obs in expect.items():
        s = by[code]
        assert s["kr_vertical_ids"] == [] and s["mapping"] is True and s["mapping_basis"] == "observed_cases", code
        assert s["kr_vertical_ids_observed"] == obs and s["case_basis"]["prior"] == 0 and s["case_basis"]["clue_only"] == s["case_count"]
    ad = by["AD"]                                                           # 사례 2건이 업종 둘로 갈림 → 대응 없음
    assert ad["mapping"] is False and ad["mapping_basis"] is None and ad["kr_vertical_ids_observed"] == []
    assert sum(v["n"] for v in by["TP"]["observed_kr_verticals"]) >= by["TP"]["case_count"] - 1
    for s in body["items"]:
        assert s["case_basis"]["prior"] + s["case_basis"]["clue_only"] == s["case_count"]
    # 분류 · 판별은 시드 대응만 쓴다(관측 대응으로 되먹이지 않음)
    cl = ok(await client.post("/v1/segments/classify", json={"text": "테마파크 어트랙션 대형 LED"}), "POST")
    tp = next(i for i in cl["items"] if i["code"] == "TP")
    assert tp["has_kr_mapping"] is False and tp["a2_match"] is None


async def test_req_types_specific_examples(client, ok):
    fb = ok(await client.get("/v1/segments/FB/insights"))
    assert fb["req_types"] and all(t["label"] for t in fb["req_types"])
    seen: set[str] = set()
    for t in fb["req_types"]:
        assert len(t["examples_specific"]) <= 3 and len(t["hint_terms"]) <= 5
        assert not (set(t["examples_specific"]) & seen)                      # 앞 태그가 쓴 문장은 다시 안 쓴다
        seen |= set(t["examples_specific"])
    assert any(t["examples_specific"] for t in fb["req_types"]) and any(t["hint_terms"] for t in fb["req_types"])
    assert "코드표" in fb["gaps"][0]
    from winmate_kb.segments import _strip_particle, _tokens

    assert _strip_particle("인테리어와") == "인테리어" and _strip_particle("높이는") == "높이" and _strip_particle("회의") == "회의"
    assert _tokens("매장 인테리어와 어울리는 디자인") == {"매장", "인테리어", "어울리", "디자인"}
