"""00-shell §7.2 kb API — §8.14 A-KB-01 ~ A-KB-17 과 KB 확인 숫자(실제 winmate_kb.sqlite)."""
from __future__ import annotations

import datetime as dt
import re

CASE_URL = "https://www.samsung.com/sec/business/insights/case-study/"
QMC = "fam_G000182628"
QM55 = "LH55QMCEBGCXKR"


# ── §7.2.2 메타 ───────────────────────────────────────────

async def test_meta_counts(client, ok):  # A-KB-01
    m = ok(await client.get("/v1/meta"))
    c = m["counts"]
    assert c["case_pages"] == 198
    assert c["deployments"] == 218
    assert (c["families"], c["models"], c["image_assets"]) == (605, 1067, 10251)
    assert m["kb_version"] == "kb_v1"
    assert m["collected_at"].startswith("2026-10-04")
    assert m["catalog_version"] == "2026-10"
    assert c["thumbnails"] > 10000


# ── §7.2.3 분류 ───────────────────────────────────────────

async def test_categories_l1(client, ok):  # A-KB-02 · P-01
    items = ok(await client.get("/v1/categories"))["items"]
    assert len(items) == 9
    assert {"id": "top_display", "name": "사이니지", "level": 1} == {k: items[0][k] for k in ("id", "name", "level")}
    assert [i["name"] for i in items] == ["사이니지", "TV/음향", "IT·PC·프린팅", "모바일", "시스템에어컨·공조", "리빙가전", "주방가전", "솔루션", "서비스"]
    assert all(i["has_children"] for i in items)
    assert [i["order"] for i in items] == list(range(1, 10))


async def test_categories_children(client, ok):  # A-KB-03 · P-02
    items = ok(await client.get("/v1/categories", params={"parent_id": "top_display"}))["items"]
    assert [(i["id"], i["name"]) for i in items] == [("cat_led-signage", "스마트 LED 사이니지"), ("cat_smart-signage", "스마트 LCD 사이니지")]
    assert all(i["level"] == 2 and i["parent_id"] == "top_display" for i in items)
    r = await client.get("/v1/categories", params={"parent_id": "nope"})
    assert r.status_code == 404


# ── §7.2.4 시리즈 · 모델 표 ───────────────────────────────

async def test_families_in_category(client, ok):  # A-KB-04
    body = ok(await client.get("/v1/families", params={"category_id": "cat_smart-signage", "limit": 100}))
    fams = {f["id"]: f for f in body["items"]}
    assert len(fams) == 37
    f = fams[QMC]
    assert f["model_count"] == 7
    assert f["name"] == "단독형 UHD M 시리즈"
    assert f["series_label"] == "QMC Series"
    assert f["subcategory"] == {"id": "cat_smart-signage__standalone", "name": "단독형"}
    assert f["is_bundle"] is False
    assert f["thumb"]["kind"] == "product" and f["thumb"]["thumb_url"].startswith("/api/kb/v1/images/")
    assert fams["fam_G000183903"]["is_bundle"] is True        # '… + 단독형 스탠드 (중형)'
    assert fams["fam_G000183398"]["series_label"] == "단독형 UHD M 시리즈"   # 98형: marketing_model 이 모델코드


async def test_models_qmc_family(client, ok):  # A-KB-05 · P-04
    body = ok(await client.get("/v1/models", params={"family_id": QMC}))
    assert [c["key"] for c in body["columns"]] == ["size", "brightness", "resolution"]
    assert [c["label"] for c in body["columns"]] == ["크기", "밝기", "해상도"]
    rows = body["items"]
    assert len(rows) == 7
    assert [r["values"]["size"]["display"] for r in rows] == ['32"', '43"', '50"', '55"', '65"', '75"', '85"']
    r55 = next(r for r in rows if r["model_code"] == QM55)
    assert r55["values"]["size"]["inch"] == 55 and r55["values"]["size"]["cm"] == 138.7
    assert r55["values"]["brightness"]["nit"] == 500 and r55["values"]["brightness"]["display"] == "500nit"
    assert {k: r55["values"]["resolution"][k] for k in ("w", "h", "display")} == {"w": 3840, "h": 2160, "display": "4K UHD"}
    assert r55["is_family_default"] is True
    assert r55["display_name"] == "QM55C" and r55["display_name_basis"] == "code_rule"
    r32 = rows[0]
    assert r32["model_code"] == "LH32QMCEBGCXKR"
    assert r32["values"]["size"]["cm"] == 80.1
    assert r32["values"]["brightness"]["display"] == "400nit"
    assert r32["values"]["resolution"]["display"] == "FHD"
    assert all(r["thumb"]["id"] == rows[0]["thumb"]["id"] for r in rows)   # 시리즈 갤러리 첫 장


async def test_models_category_and_search(client, ok):  # P-03 · P-06
    body = ok(await client.get("/v1/models", params={"category_id": "cat_smart-signage", "limit": 100}))
    assert body["items"] and [c["key"] for c in body["columns"]] == ["size", "brightness", "resolution"]
    hit = ok(await client.get("/v1/models", params={"q": "LH55QMC"}))
    assert any(r["model_code"] == QM55 for r in hit["items"])
    empty = ok(await client.get("/v1/models", params={"q": "zzzz"}))
    assert empty["items"] == []
    led = ok(await client.get("/v1/models", params={"category_id": "cat_led-signage"}))
    assert [c["key"] for c in led["columns"]] == ["size", "brightness", "pixel_pitch"]
    assert (await client.get("/v1/models")).status_code == 400


async def test_size_rule_not_simple_rounding(client, ok):  # §9.2: 107.9 cm → 43", 125.7 cm → 50"
    rows = ok(await client.get("/v1/models", params={"family_id": QMC}))["items"]
    by = {r["values"]["size"]["cm"]: r["values"]["size"]["inch"] for r in rows}
    assert by[107.9] == 43 and by[125.7] == 50


# ── §7.2.5 제품 검색 ──────────────────────────────────────

async def test_products_search(client, ok):  # A-KB-06 · PI-01 · P-07
    items = ok(await client.get("/v1/products/search", params={"q": "QMC"}))["items"]
    assert items[0]["id"] == QMC and items[0]["kind"] == "family"
    assert "스마트 LCD 사이니지" in items[0]["meta_line"] and '55"' in items[0]["meta_line"]
    items = ok(await client.get("/v1/products/search", params={"q": "LH55QMC"}))["items"]
    assert "mdl_LH55QMCEBGCXKR" in [i["id"] for i in items]
    m = next(i for i in items if i["id"] == "mdl_LH55QMCEBGCXKR")
    assert m["display_name"] == "QM55C" and m["label"] == "Smart Signage QM55C" and m["model_code"] == QM55
    assert m["category_path"][:2] == ["사이니지", "스마트 LCD 사이니지"]
    items = ok(await client.get("/v1/products/search", params={"q": "the w"}))["items"]
    names = [i["display_name"] for i in items]
    assert "실내용 The Wall IWC" in names and "실내용 The Wall IWA" in names
    assert len(items) <= 5
    w = items[0]
    assert w["highlight"] and w["display_name"][w["highlight"][0][0]:w["highlight"][0][1]].lower() == "the w"
    assert ok(await client.get("/v1/products/search", params={"q": "zzzz"}))["items"] == []
    r = await client.get("/v1/products/search", params={"q": "QMC", "kinds": "model,nope"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "UNSUPPORTED_FILTER"


# ── §7.2.6 ~ §7.2.8 제품 상세 ─────────────────────────────

async def test_model_detail(client, ok):  # A-KB-07 · PD-02 · PD-03 · PD-05 · PD-07
    d = ok(await client.get(f"/v1/models/{QM55}"))
    assert d["id"] == "mdl_LH55QMCEBGCXKR" and d["model_code"] == QM55
    assert d["title_line"] == "단독형 UHD M 시리즈 138.7 cm (55형)"
    assert d["family"]["detail_url"] == "https://www.samsung.com/sec/business/smart-signage/qmc-series/LH55QMCEBGCXKR/"
    assert [c["name"] for c in d["category_path"]] == ["사이니지", "스마트 LCD 사이니지"]
    assert d["key_chips"] == ["4K UHD", "500 nit", "24/7", "두께 28.5 mm", "Tizen 7.0"]
    assert d["facts"] == [{"label": "출시", "value": "2024년 9월"}, {"label": "제조국", "value": "베트남"}, {"label": "동작", "value": "0~40 ℃"}]
    kb_ids = [s["kb_id"] for s in d["supported_solutions"]]
    assert "sol_magicinfo" in kb_ids and "sol_vxt" in kb_ids
    mi = next(s for s in d["supported_solutions"] if s["kb_id"] == "sol_magicinfo")
    assert mi["id"] == "magicinfo" and mi["kind_label"] == "CMS" and "MagicINFO와 VXT를 지원합니다" in mi["evidence"]["text"]
    assert [s["name"] for s in d["supported_solutions"]] == ["MagicINFO", "VXT"]       # `CMS — MagicINFO · VXT 지원`
    assert d["counts"]["images"] == 8 and d["counts"]["cases"] >= 1
    assert d["case_corpus"]["count"] == 198
    assert d["documents"] is None
    assert d["verified_at"].startswith("2026-10-04")
    spec = d["spec"]
    assert spec["profile"] == "signage" and spec["source_url"] == d["family"]["detail_url"]
    assert [g["name"] for g in spec["groups"]] == ["디스플레이", "전원", "크기 · 무게", "연결성", "운영 · 환경", "인증 · 액세서리"]
    assert [g["column"] for g in spec["groups"]] == ["left"] * 3 + ["right"] * 3
    rows = {r["label"]: r["value"] for g in spec["groups"] for r in g["rows"]}
    assert rows["밝기 (Typ)"] == "500 nit"
    assert rows["HDMI"] == "입력 3 · 버전 2 · HDCP 2.2"
    assert rows["소비전력"] == "154 W · 대기 0.5 W"
    assert rows["무게"] == "15.7 kg · 포장 19.9 kg"
    assert rows["KC 인증"] == "R-R-SEC-LH55QMCE"
    assert rows["대각선"] == "138.7 cm (55형)"
    assert rows["응답속도"] == "8 ms"
    assert rows["RS232"] == "입력 · 출력 있음"
    assert rows["네트워크"] == "RJ45 · Wi-Fi · Bluetooth"
    assert rows["오디오"] == "출력 Stereo Mini Jack"
    assert rows["해상도"] == "3,840 x 2,160"          # 원문 그대로(§9.6-10)
    assert [len(g["rows"]) for g in spec["groups"]] == [10, 2, 4, 6, 4, 5]


async def test_model_detail_other_ids_and_404(client, ok):  # A-KB-16
    assert ok(await client.get("/v1/models/mdl_LH55QMCEBGCXKR"))["model_code"] == QM55
    assert ok(await client.get(f"/v1/models/{QMC}"))["model_code"] == QM55          # 제품군 → 대표 모델
    r = await client.get("/v1/models/NOPE")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


async def test_model_detail_non_signage_falls_back_to_kb_groups(client, ok):
    rows = ok(await client.get("/v1/models", params={"category_id": "cat_hotel-tvs", "limit": 1}))["items"]
    d = ok(await client.get(f"/v1/models/{rows[0]['model_code']}"))
    assert d["spec"]["profile"] is None and d["spec"]["groups"]


async def test_model_images(client, ok):  # A-KB-08 · PD-10
    body = ok(await client.get(f"/v1/models/{QM55}/images"))
    items = body["items"]
    assert body["total"] == len(items) == 8
    assert all(i["rights"] == "official" and i["kind"] == "product" for i in items)
    assert all(i["source_page"]["url"] == "https://www.samsung.com/sec/business/smart-signage/qmc-series/LH55QMCEBGCXKR/" for i in items)
    assert all(i["original_url"].startswith("https://images.samsung.com/kdp/goods/2023/08/29/") for i in items)
    first = items[0]
    assert first["alt"] == "단독형 UHD M 시리즈 정면" and first["label"] == "정면"
    assert first["posted"] == {"date": "2023-08-29", "basis": "file_path"}
    assert first["source_type_label"] == "삼성전자 공식 · 제품 갤러리"
    assert first["source_page"]["label"] == "samsung.com · LH55QMCEBGCXKR"
    assert first["usage_note"] == "삼성전자 저작물 · 대외 사용 범위 확인 필요"
    assert first["collected_at"].startswith("2026-10-04")
    assert first["stored_url"] == f"/api/kb/v1/images/{first['id']}/file"
    assert first["stored"]["format"] == "WEBP"          # 로컬 원본 사본이 없으면 썸네일
    assert first["original"]["width"] == 900 and first["original"]["height"] == 600
    assert not any("images.samsung.com" in (i["stored_url"] + i["thumb_url"]) for i in items)


async def test_model_cases(client, ok):  # A-KB-09 · PD-12
    body = ok(await client.get(f"/v1/models/{QM55}/cases"))
    assert body["counts"]["model"] == 0 and body["counts"]["series"] == 0
    assert body["corpus"]["count"] == 198
    assert body["usage_label"]
    assert body["default_match"] == "usage"
    assert 1 <= len(body["items"]) <= 3
    for it in body["items"]:
        assert it["match_type"] == "usage"
        assert it["url"].startswith(CASE_URL)
        assert it["photos"]["count"] >= 3
        assert it["used_products_line"] == " · ".join(p["label"] for p in it["products"])
    assert ok(await client.get(f"/v1/models/{QM55}/cases", params={"match": "model"}))["items"] == []


async def test_model_cases_with_series_match(client, ok):
    """시리즈 일치가 있는 제품군이면 기본이 series(또는 model)다."""
    from winmate_kb.index import idx

    I = idx()
    fid = next(f for d, t in I.dep_targets.items() for k, f in t if k == "family" and I.deps[d]["document_id"] and f in I.fams)
    mid = I.default_model(fid)
    body = ok(await client.get(f"/v1/models/{I.models[mid]['model_code']}/cases"))
    assert body["counts"]["series"] >= 1 or body["counts"]["model"] >= 1
    assert body["default_match"] in ("model", "series")
    assert all(it["match_type"] == body["default_match"] for it in body["items"])


# ── §7.2.9 ~ §7.2.12 솔루션 ───────────────────────────────

SOL_ORDER = ["magicinfo", "vxt", "smartthings_pro", "biot", "lynk_cloud", "knox_suite", "knox_capture", "dex", "cold_chain",
             "hvac_integrated", "sac_control"]


async def test_solutions_list(client, ok):  # A-KB-10 · S-01 · S-03
    items = ok(await client.get("/v1/solutions"))["items"]
    assert [i["id"] for i in items] == SOL_ORDER
    by = {i["id"]: i for i in items}
    assert by["magicinfo"]["kb_id"] == "sol_magicinfo" and by["knox_capture"]["kb_id"] is None
    assert by["magicinfo"]["name"] == "MagicINFO"
    assert by["magicinfo"]["desc"] == "디스플레이 · 설치형 사이니지 CMS · 콘텐츠 · 스케줄 · 데이터 연동"
    assert by["cold_chain"]["desc"] == "공조 · 냉장 · 냉동 쇼케이스 · 저장고 + 에어컨 통합 관리"
    assert by["magicinfo"]["template_code"] == "MGI" and by["magicinfo"]["icon"].startswith("M3 4h18v12H3z")
    hosp = [i["id"] for i in ok(await client.get("/v1/solutions", params={"industry": "hospitality"}))["items"]]
    assert "lynk_cloud" in hosp and "knox_capture" not in hosp
    found = [i["id"] for i in ok(await client.get("/v1/solutions", params={"q": "매직인포"}))["items"]]
    assert found[0] == "magicinfo"
    assert (await client.get("/v1/solutions", params={"industry": "nope"})).status_code == 422


async def test_solution_cases_magicinfo(client, ok):  # A-KB-11 · SD-04
    body = ok(await client.get("/v1/solutions/magicinfo/cases"))
    assert body["total"] == 17
    assert sorted(c["id"] for c in body["title_explicit"]) == sorted(["dep_2549", "dep_2129", "dep_33"])
    assert len(body["body_mentions"]) == 14
    assert all(c["url"].startswith(CASE_URL) for c in body["title_explicit"] + body["body_mentions"])
    dates = [c["date"] for c in body["body_mentions"]]
    assert dates == sorted(dates, reverse=True)
    assert body["corpus"]["count"] == 198
    assert ok(await client.get("/v1/solutions/sol_magicinfo/cases"))["total"] == 17


async def test_solution_detail(client, ok):  # SD-01 · SD-02 · SD-03 · SD-07
    d = ok(await client.get("/v1/solutions/magicinfo"))
    assert d["name"] == "MagicINFO" and d["version_label"] == "MagicINFO™ 8"
    assert d["quote_url"] == "https://www.samsung.com/sec/business/display-solution/display-solution-bwmip70pa/BW-MIP70PA/"
    assert d["intro_url"] == "https://www.samsung.com/sec/business/display-solutions/magicinfo/"
    assert d["purchase"]["site_code"] == "BW-MIP70PA" and "[견적 확인]" in d["purchase"]["label"]
    assert d["supported_devices"]["label"] == "삼성 스마트 사이니지"
    assert d["supported_devices"]["example"]["family_id"] == QMC
    p = d["profile"]
    assert [x["name"] for x in p["pillars"]] == ["콘텐츠 관리", "디바이스 관리", "데이터 관리"]
    assert [x["name"] for x in p["parts"]] == ["MagicINFO Author", "MagicINFO Server", "MagicINFO Player", "MagicINFO Datalink"]
    assert len(p["deploy"]) == 2 and all(x["evidence"]["deployment_id"] for x in p["deploy"])
    assert len(p["device_functions"]) == 4 and p["source_note"]
    assert d["messages"] and d["counts"]["cases"] == 17
    kc = ok(await client.get("/v1/solutions/knox_capture"))
    assert kc["profile"] is None and kc["kb_id"] is None and kc["quote_url"] is None and "G-SOL-1" in kc["gaps"]
    kb_only = ok(await client.get("/v1/solutions/sol_samsung_health"))
    assert kb_only["kb_id"] == "sol_samsung_health"
    assert (await client.get("/v1/solutions/nope")).status_code == 404


async def test_solution_images(client, ok):  # SD-05
    body = ok(await client.get("/v1/solutions/magicinfo/images"))
    groups = {g["key"]: g for g in body["groups"]}
    assert set(groups) == {"official", "case"}
    assert groups["case"]["label"] == "도입사례 사진" and groups["case"]["source_label"] == "samsung.com 고객 도입사례"
    assert 1 <= len(groups["case"]["items"]) <= 4
    assert all(i["rights"] == "customer_case" for i in groups["case"]["items"])
    assert body["total"] == len(groups["official"]["items"]) + len(groups["case"]["items"])
    assert ok(await client.get("/v1/solutions/magicinfo"))["counts"]["images"] == body["total"]


# ── §7.2.13 · §7.2.14 이미지 ──────────────────────────────

async def test_images_search(client, ok):  # A-KB-12 · I-02 · I-09
    body = ok(await client.get("/v1/images/search", params={"q": "카페 메뉴보드"}))
    c = body["counts"]
    assert body["items"] and c["all"] == c["official"] + c["case"]
    assert len(body["items"]) <= 24
    for it in body["items"]:
        assert it["source_domain"] == "samsung.com"
        assert it["grade"] not in ("D", "E")
        assert it["kind"] in ("product", "case", "solution", "industry")
        assert it["original"] and it["original"]["width"] > 0       # 타일 메타 `{kind} · {W}×{H} · samsung.com`
        assert it["stored_url"].startswith("/api/kb/v1/images/") and it["thumb_url"].startswith("/api/kb/v1/images/")
    case = ok(await client.get("/v1/images/search", params={"q": "카페 메뉴보드", "source": "case"}))
    assert case["items"] and all(i["rights"] == "customer_case" and i["kind"] == "case" for i in case["items"])
    off = ok(await client.get("/v1/images/search", params={"q": "카페 메뉴보드", "source": "official"}))
    assert all(i["rights"] == "official" and i["kind"] != "case" for i in off["items"])
    browse = ok(await client.get("/v1/images/search"))
    assert browse["items"] and browse["counts"]["all"] > 0


async def test_image_meta_case_photo(client, ok):  # A-KB-13 · I-04 · I-10
    m = ok(await client.get("/v1/images/img_0b58832faefa0ff4"))
    assert m["rights"] == "customer_case" and m["kind"] == "case"
    assert m["source_page"]["url"] == "https://www.samsung.com/sec/business/insights/case-study/reference-MCDONALDSsamsong/"
    assert m["source_page"]["label"] == "맥도날드 고양삼송DT점 도입사례"
    assert "“도입사례 사진” 표기 필수" in m["usage_note"]
    assert m["usage_note_short"] == m["usage_note"]
    assert m["original"] == {"width": 1340, "height": 820, "format": "JPG", "bytes": 376429, "basis": "board_sample"}
    assert round(m["original"]["bytes"] / 1024) == 368
    assert m["posted"] == {"date": "2020-11-12", "basis": "case_page"}
    assert m["original_url"] == "https://images.samsung.com/kdp/editor/board/202011/3dbd0331-2a8e-4e5c-ae3a-de796dd5d93d.jpg"
    assert m["title"] == "맥도날드 매장 내부 메뉴보드"
    assert {"kind": "deployment", "id": "dep_1490"}.items() <= m["depicts"][0].items()
    assert (await client.get("/v1/images/img_nope")).status_code == 404


# ── §7.2.15 · §7.2.16 사례 · 업종 ─────────────────────────

async def test_cases_search(client, ok):  # A-KB-14 · C-02
    body = ok(await client.get("/v1/cases/search", params={"q": "프랜차이즈 메뉴보드", "vertical_id": "kr_retail_fnb"}))
    items = body["items"]
    assert items and len(items) <= 10
    scores = [i["match"]["score"] for i in items]
    assert scores == sorted(scores, reverse=True)
    for i in items:
        assert i["url"].startswith(CASE_URL) and i["url_display"].startswith("samsung.com/sec/business/insights/case-study/")
        assert i["photos"]["count"] >= 3 and len(i["photos"]["items"]) == 3
        assert i["vertical"]["name"] == "유통/요식"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", i["date"])
        assert set(i["match"]["breakdown"]) == {"vertical", "space", "product", "text"}
        assert len(i["match"]["terms"]) <= 2
    assert body["corpus"]["count"] == 198
    assert body["applied"]["vertical"] == {"id": "kr_retail_fnb", "name": "유통/요식", "from": "user"}
    assert any(i["match"]["terms"] for i in items)


async def test_cases_search_region_unsupported(client):  # A-KB-15
    r = await client.get("/v1/cases/search", params={"q": "x", "region": "seoul"})
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "UNSUPPORTED_FILTER" and "region" in err["details"]["filters"]


async def test_cases_search_period_and_infer(client, ok):  # C-05 · C-07
    body = ok(await client.get("/v1/cases/search", params={"period": "3y", "limit": 100}))
    assert 0 < body["corpus"]["count"] < 198 and body["total"] == body["corpus"]["count"]
    cut = (dt.date.today().replace(year=dt.date.today().year - 3)).isoformat()
    assert all(i["date"] >= cut for i in body["items"])
    inf = ok(await client.get("/v1/cases/search", params={"q": "호텔 객실 TV 통합 관리", "infer_vertical": "true"}))
    assert inf["applied"]["vertical"] == {"id": "kr_hotel", "name": "호텔", "from": "inferred"}
    assert all(i["vertical"]["id"] == "kr_hotel" for i in inf["items"])
    no = ok(await client.get("/v1/cases/search", params={"q": "호텔 객실 TV 통합 관리"}))
    assert no["applied"]["vertical"] is None
    tgt = ok(await client.get("/v1/cases/search", params={"target": "solution:magicinfo", "limit": 100}))
    assert tgt["total"] == 17
    assert (await client.get("/v1/cases/search", params={"target": "family:fam_nope"})).status_code == 404


async def test_case_detail(client, ok):  # §7.2.16
    d = ok(await client.get("/v1/cases/dep_1490"))
    assert d["title"] == "맥도날드 고양삼송DT점 – 삼성 스마트 사이니지"
    assert d["photos"]["count"] == len(d["photos"]["items"]) >= 3
    assert d["kpis"] and all("claim_flag" in k for k in d["kpis"])
    assert d["needs"] and d["tag_detail"] == "DT"
    assert d["summary"] is None
    labels = [p["label"] for p in d["products"]]
    assert "img" not in labels and "MagicINFO" in labels
    assert (await client.get("/v1/cases/dep_nope")).status_code == 404
    sim = ok(await client.get("/v1/cases/dep_1490/similar"))
    assert sim["items"] and all(i["id"] != "dep_1490" for i in sim["items"])


async def test_verticals(client, ok):  # §7.2.16 · 10-proposal K3
    items = ok(await client.get("/v1/verticals", params={"scheme": "kr_site"}))["items"]
    assert len(items) == 22
    assert sum(1 for v in items if v["parent_id"] is None) == 10
    assert {"id": "kr_retail_fnb", "name": "유통/요식", "parent_id": None}.items() <= next(v for v in items if v["id"] == "kr_retail_fnb").items()
    wm = ok(await client.get("/v1/verticals", params={"scheme": "winmate16"}))["items"]
    assert len(wm) == 16
    fb = wm[0]
    assert (fb["code"], fb["id"], fb["name"], fb["kr_vertical_ids"]) == ("FB", "wm_fnb_cafe", "외식 · 카페", ["kr_fnb"])
    sv = next(v for v in wm if v["code"] == "SV")
    assert sv["kr_vertical_ids"] == []              # <<FILL>> = 대응 없음
    assert len(ok(await client.get("/v1/verticals", params={"scheme": "us_site"}))["items"]) == 13


async def test_space_types(client, ok):
    items = ok(await client.get("/v1/space-types"))["items"]
    assert len(items) == 70
    hotel = ok(await client.get("/v1/space-types", params={"vertical_id": "kr_hotel"}))["items"]
    assert "guest_room" in [s["id"] for s in hotel]


# ── 목록 규약 ─────────────────────────────────────────────

async def test_pagination(client, ok):  # A-KB-17
    a = ok(await client.get("/v1/families", params={"category_id": "cat_smart-signage", "limit": 2}))
    assert len(a["items"]) == 2 and a["next_cursor"]
    b = ok(await client.get("/v1/families", params={"category_id": "cat_smart-signage", "limit": 2, "cursor": a["next_cursor"]}))
    assert len(b["items"]) == 2
    assert not ({i["id"] for i in a["items"]} & {i["id"] for i in b["items"]})
    c1 = ok(await client.get("/v1/categories", params={"limit": 2}))
    c2 = ok(await client.get("/v1/categories", params={"limit": 2, "cursor": c1["next_cursor"]}))
    assert [i["id"] for i in c1["items"] + c2["items"]] == ["top_display", "top_tv_audio", "top_it", "top_mobile"]
    s1 = ok(await client.get("/v1/cases/search", params={"q": "사이니지", "limit": 2}))
    s2 = ok(await client.get("/v1/cases/search", params={"q": "사이니지", "limit": 2, "cursor": s1["next_cursor"]}))
    assert len(s2["items"]) == 2 and not ({i["id"] for i in s1["items"]} & {i["id"] for i in s2["items"]})
    i1 = ok(await client.get("/v1/images/search", params={"q": "호텔 객실", "limit": 2}))
    i2 = ok(await client.get("/v1/images/search", params={"q": "호텔 객실", "limit": 2, "cursor": i1["next_cursor"]}))
    assert not ({i["id"] for i in i1["items"]} & {i["id"] for i in i2["items"]})
    last = ok(await client.get("/v1/families", params={"category_id": "cat_led-signage", "limit": 100}))
    assert last["next_cursor"] is None
    assert (await client.get("/v1/families", params={"category_id": "cat_smart-signage", "cursor": "x"})).status_code == 400
