"""kb 제품 해석 — 실제 KB(in-process)로: `/` 든 모델 코드 · LED 모듈 크기 · 일반 사이니지 크기 옵션."""
from __future__ import annotations


async def test_slash_model_code_and_led_module_sizes(platform):
    from winmate_birdseye import kbapi

    # 실내용 The Wall IWC — 모델 코드에 / 가 들어 있다(경로 조회 불가 → 목록 검색으로 대신)
    det = await kbapi.model_detail("LH012IWCMWS/XU")
    assert det is not None and det["model_code"] == "LH012IWCMWS/XU"
    assert (det.get("family") or {}).get("id") == "fam_G000182728"

    p = await kbapi.resolve_product({"ref": "kb:model:mdl_LH012IWCMWS/XU"}, 1)
    assert p["role"] == "led_wall"
    assert p["family_id"] == "fam_G000182728"
    # 12" 는 LED 모듈 크기 — 화면 크기 · 치수로 쓰지 않는다(지어내지 않음 → estimated)
    assert p["size_options"] == [] and p["diag_inch"] is None
    assert p["dims_m"] is None and p["dims_source"] == "estimated"

    fam = await kbapi.resolve_product({"family_id": "fam_G000182728"}, 2)
    assert fam["role"] == "led_wall" and fam["size_options"] == [] and fam["dims_source"] == "estimated"


async def test_signage_family_size_options_from_kb(platform):
    from winmate_birdseye import kbapi

    hits = await kbapi.search("Flip Pro", 1)
    assert hits, "실제 KB 에 Flip Pro 가 있어야 한다"
    p = await kbapi.resolve_product({"family_id": hits[0]["family_id"], "ref": hits[0]["ref"]}, 1)
    assert p["role"] == "interactive"
    assert p["size_options"], "제품군 크기 옵션(인치)"
    assert all(s.endswith('"') for s in p["size_options"])
    assert set(p["dims_by_size"]) == set(p["size_options"])
    assert p["dims_source"] in ("spec", "computed")
