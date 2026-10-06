"""이미지 바이너리(썸네일 · 로컬 사본 · 사이드카) · 업종 세그먼트 · 스펙 표 · 생애주기 · 성능 · 동시성."""
from __future__ import annotations

import asyncio
import io
import json
import time

QM55_FRONT = "img_9ec6148d2e4d9c18"


def _is_webp(b: bytes) -> bool:
    return len(b) > 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"


async def test_thumb_served_as_webp(client):
    r = await client.get(f"/v1/images/{QM55_FRONT}/thumb")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    assert _is_webp(r.content)
    from PIL import Image

    with Image.open(io.BytesIO(r.content)) as im:
        assert im.format == "WEBP" and max(im.size) <= 176
    f = await client.get(f"/v1/images/{QM55_FRONT}/file")      # 로컬 사본 없음 → 썸네일
    assert f.status_code == 200 and f.headers["x-kb-image-source"] == "thumbnail" and f.content == r.content


async def test_thumb_404(client):
    r = await client.get("/v1/images/img_nope/thumb")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    from winmate_kb.images import thumbs
    from winmate_kb.index import idx

    missing = next(a for a in idx().assets if thumbs().get(a) is None)          # 썸네일이 없는 자산(US CDN 등)
    r = await client.get(f"/v1/images/{missing}/thumb")
    assert r.status_code == 404
    card = (await client.get(f"/v1/images/{missing}")).json()
    assert card["has_local"] is False


async def test_local_file_and_sidecar(client, env, ok):
    from PIL import Image

    d = env / "images"
    d.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (1600, 1067), (20, 40, 160)).save(d / f"{QM55_FRONT}.webp", "WEBP", quality=80)
    (d / "_originals.json").write_text(json.dumps({"images": {QM55_FRONT: {
        "original": {"width": 900, "height": 600, "format": "PNG", "bytes": 739867}}}}), encoding="utf-8")
    r = await client.get(f"/v1/images/{QM55_FRONT}/file")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp" and r.headers["x-kb-image-source"] == "local"
    m = ok(await client.get(f"/v1/images/{QM55_FRONT}"))
    assert m["stored"]["width"] == 1600 and m["stored"]["format"] == "WEBP" and m["stored"]["basis"] == "local_file"
    assert m["original"] == {"width": 900, "height": 600, "format": "PNG", "bytes": 739867, "basis": "download"}
    meta = ok(await client.get("/v1/meta"))
    assert meta["counts"]["local_images"] == 1


async def test_segments(client, ok):
    body = ok(await client.get("/v1/segments"))
    assert [s["code"] for s in body["items"]] == ["FB", "RT", "SV", "HT", "TP", "VN", "AD", "OF", "RS", "ID", "ED", "PB", "MD", "MF", "FN", "OE"]
    assert body["total_cases"] == 198
    assert sum(s["case_count"] for s in body["items"]) + body["unclassified_cases"] == 198
    assert body["tier"] == "T5_rule_draft"
    fb = ok(await client.get("/v1/segments/FB/insights"))
    assert fb["cases"] > 0 and len(fb["req_types"]) <= 6 and len(fb["products"]) <= 4 and len(fb["solutions"]) <= 4
    assert all(t["label"] is None and t["code"].startswith("R") for t in fb["req_types"])
    assert ok(await client.get("/v1/segments/wm_hotel_resort/insights"))["code"] == "HT"
    assert (await client.get("/v1/segments/XX/insights")).status_code == 404
    cl = ok(await client.post("/v1/segments/classify", json={"text": "A 커피 프랜차이즈 매장 메뉴보드를 디지털로 바꾸고 음료 피크타임에 대응"}), "POST")
    assert len(cl["items"]) == 16
    fbc = next(i for i in cl["items"] if i["code"] == "FB")
    assert fbc["clue_score"] > 0.5 and {"text": "프랜차이즈", "code": "FB", "weight": 0.3} in fbc["clues"]
    ht = ok(await client.post("/v1/segments/classify", json={"text": "호텔 객실 TV 통합 관리"}), "POST")
    hti = next(i for i in ht["items"] if i["code"] == "HT")
    assert hti["a2_match"] == 1.0 and hti["kb_score"] >= 0.5


async def test_spec_table_and_attributes(client, ok):
    t = ok(await client.post("/v1/spec/table", json={"models": ["LH55QMCEBGCXKR", "mdl_LH55QBCEBGCXKR", "QM55R"]}), "POST")
    assert [m["model_code"] for m in t["models"]] == ["LH55QMCEBGCXKR", "LH55QBCEBGCXKR"] and t["unresolved"] == ["QM55R"]
    rows = {(r["group"], r["attr_name"]): r for r in t["rows"]}
    br = rows[("디스플레이", "밝기 (Typ)")]["values"]
    assert br["LH55QMCEBGCXKR"]["raw"] == "500 nit" and br["LH55QBCEBGCXKR"]["raw"] == "350 nit"
    assert rows[("디스플레이", "제품 사용 시간")]["values"]["LH55QBCEBGCXKR"]["raw"] == "16/7"
    dv = t["derived"]["LH55QMCEBGCXKR"]
    assert dv["screen_size_inch"] == 55 and dv["screen_size_cm"] == 138.7
    assert dv["dimensions_mm"] == {"w": 1237.9, "h": 708.8, "d": 28.5, "unit": "mm", "raw": "1237.9 x 708.8 x 28.5 mm"}
    assert dv["brightness_typ_nit"] == 500 and dv["weight_kg_set"] == 15.7 and dv["weight_kg_package"] == 19.9
    assert dv["resolution"] == {"w": 3840, "h": 2160, "label": "4K UHD"}
    only = ok(await client.post("/v1/spec/table", json={"models": ["LH55QMCEBGCXKR"], "keys": ["brightness_nit"]}), "POST")
    assert {r["norm_key"] for r in only["rows"]} == {"brightness_nit"}
    attrs = ok(await client.get("/v1/spec/attributes", params={"category_id": "cat_smart-signage"}))["items"]
    assert any(a["name"] == "밝기 (Typ)" and a["norm_key"] == "brightness_nit" for a in attrs)
    assert all(a["category_id"] == "cat_smart-signage" for a in attrs)


async def test_lifecycle_and_placement(client, ok):
    lc = ok(await client.get("/v1/models/LH55QMCEBGCXKR/lifecycle"))
    assert lc["status"] == "on_sale" and lc["successor"] is None and lc["sale_status_code"] == "17"
    assert ok(await client.get("/v1/models/QM55R/lifecycle"))["status"] == "not_in_catalog"
    pr = ok(await client.get("/v1/placement-rules", params={"category": "signage"}))
    assert pr["items"] and all(not r["active"] for r in pr["items"])


async def test_performance_warm(client):
    """검색은 데운 뒤 1초 안(성능 확인)."""
    for path, params in (("/v1/products/search", {"q": "사이니지"}), ("/v1/images/search", {"q": "호텔 객실"}),
                         ("/v1/cases/search", {"q": "카페 메뉴보드"})):
        await client.get(path, params=params)                    # 데우기
        t = time.perf_counter()
        r = await client.get(path, params={**params, "q": params["q"] + " 매장"})
        assert r.status_code == 200
        assert time.perf_counter() - t < 1.0, path
    await client.post("/v1/query/search", json={"text": "호텔 객실 TV"})
    t = time.perf_counter()
    r = await client.post("/v1/query/search", json={"text": "병상 태블릿 환자 소통"})
    assert r.status_code == 200 and time.perf_counter() - t < 1.0


async def test_concurrent_requests(client):
    """동기 엔드포인트가 스레드 풀에서 동시에 돌아도 연결 · 캐시가 깨지지 않는다(스레드마다 sqlite 연결)."""
    calls = [client.get("/v1/models", params={"family_id": "fam_G000182628"}),
             client.get("/v1/products/search", params={"q": "QMC"}),
             client.post("/v1/query/E3", json={"text": "호텔 객실 TV 통합 관리"}),
             client.post("/v1/query/S1", json={"text": "매장 입구 쇼윈도에 햇빛에서도 잘 보이는 사이니지"}),
             client.get("/v1/cases/search", params={"q": "프랜차이즈"}),
             client.get("/v1/images/search", params={"q": "로비 비디오월"}),
             client.get("/v1/solutions/magicinfo"),
             client.get("/v1/models/LH55QMCEBGCXKR")] * 3
    rs = await asyncio.gather(*calls)
    assert all(r.status_code == 200 for r in rs), [r.text[:200] for r in rs if r.status_code != 200]
    a = [r.json() for r in rs[:8]]
    b = [r.json() for r in rs[8:16]]
    assert a[0] == b[0] and a[1] == b[1] and a[7] == b[7]


async def test_info_and_auth(client):
    r = await client.get("/v1/info")
    assert r.status_code == 200 and r.json()["service"] == "kb"
