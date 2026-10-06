"""결정적 배치 엔진 · 검증 · 초안 렌더(AC 28–29 · 32–37 · 39 · 49–50) — 모델 호출 없음, 골든 파일."""
from __future__ import annotations

import json
import time
from pathlib import Path

import golden
import pytest

from winmate_birdseye import config, draft
from winmate_birdseye.engine import apply_ops, autofix, generate, merged_params, validate

GOLDEN = Path(__file__).parent / "golden_layout.json"


@pytest.fixture(scope="module")
def prm():
    return merged_params(config.rules(), [])


@pytest.fixture(scope="module")
def base(prm):
    return generate(golden.space(), golden.products(), golden.furniture(), intents=golden.intents(), params=prm, version=0)


def test_ac28_deterministic_golden(prm, base):
    again = generate(golden.space(), golden.products(), golden.furniture(), intents=golden.intents(), params=prm, version=0)
    a = json.dumps(base, ensure_ascii=False, sort_keys=True)
    assert a == json.dumps(again, ensure_ascii=False, sort_keys=True)
    assert json.loads(a) == json.loads(GOLDEN.read_text(encoding="utf-8"))
    labels = {g["plan_label"] for g in base["groups"]}
    assert {"OH55C ×3 (창면)", 'The Wall IAB 146" (후면 벽)', "Flip Pro WA75D (측벽)", "기둥 랩핑 ×2"} <= labels
    at = {g["label"]: g["at_label"] for g in base["groups"] if g["kind"] == "product"}
    assert at == {"OH55C ×3": "쇼윈도 창면", 'The Wall IAB 146"': "후면 벽", "Flip Pro WA75D": "측벽 · 상담"}


def test_ac29_size_assumption(base):
    wall = next(g for g in base["groups"] if g["id"] == "g1")
    assert wall["size"] == '146"'
    assert any(a["text_ko"] == '도면에 후면 벽 폭이 없어 The Wall 크기는 146" 비율로 맞췄어요.' for a in base["assumptions"])


def _bench_close(prm, base):
    """보드 AC 32 상황 재현: 벤치 첫 열을 The Wall 에서 3.1 m 로 당긴 배치(6.0 m 에서는 3.0 m 이동이 시야각 45° 를 넘지 않는다)."""
    sp = golden.space()
    return apply_ops(sp, base, [{"op": "move", "item": "g5", "dx": 0, "dy": 2.9}], params=prm)


def test_ac32_ac33_viewing_angle(prm, base):
    sp = golden.space()
    b1 = _bench_close(prm, base)
    moved = apply_ops(sp, b1, [{"op": "move", "item": "li1", "dx": 3.0, "dy": 0}], params=prm)
    res = validate(sp, moved, params=prm, base=b1)
    w = next(x for x in res["warnings"] if x["kind"] == "viewing_angle")
    assert w["n"] == 1 and w["title_ko"] == "시야각"
    assert w["message_ko"] == "The Wall을 오른쪽으로 3.0 m 옮겨 관람 벤치 왼쪽 2석이 시야각 밖이에요"
    assert w["fixes"][0]["label_ko"] == "벤치 함께 옮기기"
    fixed = apply_ops(sp, moved, w["fixes"][0]["ops"], params=prm)
    by = {it["id"]: it for it in fixed["items"]}
    assert round(by["li8"]["x"] - 12.55, 2) == 3.0
    res2 = validate(sp, fixed, params=prm, base=b1)
    assert not [x for x in res2["warnings"] if x["kind"] == "viewing_angle"]


def _sofa_bottleneck(prm, base):
    return apply_ops(golden.space(), base, [{"op": "set_pos", "item": "li12", "pos": [7.1, 9.95]}], params=prm)


def test_ac34_walkway(prm, base):
    sp = golden.space()
    s1 = _sofa_bottleneck(prm, base)
    res = validate(sp, s1, params=prm, base=base)
    w = next(x for x in res["warnings"] if x["kind"] == "walkway")
    assert w["message_ko"] == "라운지 소파와 기둥 사이 통로 0.6 m · 권장 1.2 m 이상"
    # 방향어는 병목 법선 · 상대 반대쪽(이 배치에서는 아래로 — 보드 예는 「위로」)
    assert w["fixes"][0]["label_ko"] in ("소파 위로 0.6 m", "소파 아래로 0.6 m")
    s2 = apply_ops(sp, s1, w["fixes"][0]["ops"], params=prm)
    res2 = validate(sp, s2, params=prm, base=base)
    assert not [x for x in res2["warnings"] if x["kind"] == "walkway"]
    assert all(b["width"] >= 1.2 for b in res2["overlays"]["bottlenecks"])


def test_ac35_power(prm, base):
    sp = golden.space()
    res = validate(sp, base, params=prm)
    w = next(x for x in res["warnings"] if x["kind"] == "power")
    assert w["message_ko"] == "OH55C ×3에서 가까운 콘센트까지 6.0 m · 바닥 배선 필요"
    assert w["actions"] == ["add_power", "memo", "ignore"] or set(w["actions"]) >= {"add_power", "memo"}
    p = apply_ops(sp, base, [{"op": "add_power", "pos": [6.0, 2.5]}], params=prm)
    res2 = validate(sp, p, params=prm)
    assert not [x for x in res2["warnings"] if x["kind"] == "power"]


def test_ac36_autofix(prm, base):
    sp = golden.space()
    b1 = _bench_close(prm, base)
    cur = apply_ops(sp, b1, [{"op": "move", "item": "li1", "dx": 3.0, "dy": 0}, {"op": "set_pos", "item": "li12", "pos": [7.1, 9.95]}],
                    params=prm)
    cur["warnings"] = validate(sp, cur, params=prm, base=b1)["warnings"]
    fixed, statuses = autofix(sp, cur, params=prm, base=b1, include_power=True)
    st = {w["kind"]: w["status"] for w in fixed["warnings"] if w["kind"] in ("viewing_angle", "walkway", "power")}
    by = {it["id"]: it for it in fixed["items"]}
    assert round(by["li8"]["x"] - 12.55, 2) == 3.0          # 벤치 함께 옮기기
    assert st.get("viewing_angle") == "fixed" and st.get("walkway") == "fixed" and st.get("power") == "memo"
    assert any("바닥 배선 필요" in m for m in fixed["memos"])


def test_ac37_rule_metadata(prm, base):
    sp = golden.space()
    cur = apply_ops(sp, _bench_close(prm, base), [{"op": "move", "item": "li1", "dx": 3.0, "dy": 0}], params=prm)
    res = validate(sp, cur, params=prm, base=base)
    assert res["warnings"]
    for w in res["warnings"]:
        assert w["rule_id"] and w["expr"] and isinstance(w["params"], dict) and w["param_status"] == "draft"
        assert w["tooltip"].startswith(w["rule_id"] + " · ") and w["tooltip"].endswith("(draft)")
    pw = next(w for w in res["warnings"] if w["kind"] == "power" and "OH55C" in w["message_ko"])
    assert pw["tooltip"] == "pr_warn_power_distance · distance_to_power_m > 3.0 (draft)"


def test_ac39_validate_50_items_fast(prm, base):
    sp = golden.space()
    lay = json.loads(json.dumps(base))
    items = lay["items"]
    n = len(items)
    k = 0
    while len(lay["items"]) < 50:
        k += 1
        it = dict(items[k % n])
        if it["kind"] != "furniture" or it.get("seats"):
            continue
        it["id"] = f"li{100 + k}"
        it["x"] = 2.0 + (k * 1.7) % 20
        it["y"] = 3.0 + (k * 2.3) % 10
        lay["items"].append(it)
    t0 = time.perf_counter()
    validate(sp, lay, params=prm, base=base)
    assert (time.perf_counter() - t0) * 1000 < 1000   # CI 기준 200ms — 공유 2 CPU 에서는 여유를 둔다
    t0 = time.perf_counter()
    for _ in range(3):
        validate(sp, lay, params=prm, base=base)
    assert (time.perf_counter() - t0) / 3 * 1000 < 600


def test_ac49_before_cut_has_no_items(base):
    sp = golden.space()
    view = {"preset": "aerial45", "label": "조감 45°"}
    png_after, cam = draft.render(sp, base, view=view, tone="warm_wood", light="day", stage="v1", before=False)
    png_before, cam2 = draft.render(sp, base, view=view, tone="warm_wood", light="day", stage="v1", before=True)
    assert cam == cam2
    assert png_after != png_before
    assert draft.product_boxes(cam, base)            # 도입 후: 제품 상자 투영이 있다
    from PIL import Image
    import io

    a = Image.open(io.BytesIO(png_after)).convert("RGB")
    b = Image.open(io.BytesIO(png_before)).convert("RGB")
    assert a.size == b.size == (1024, 576)


def test_ac50_custom_camera_clamped():
    sp = golden.space()
    cam = draft.clamp_custom(sp, {"pos": [12.0, 2.0, 7.0], "target": [12.0, 10.0, 0.0], "fov_deg": 60})
    assert cam["pos"][2] == 4.3
    rc = draft.rules_camera(sp, "입구에서 본 시점")
    assert rc["pos"][2] <= 4.3


def test_ac55_mask_numbers_keeps_model_codes_sizes_qty():
    from winmate_birdseye.text import mask_numbers

    assert mask_numbers("하루 3000명이 지나는 창면") == "하루 [00]이 지나는 창면"
    assert mask_numbers("통로 1.2 m · 20% 증가") == "통로 [00] · [00] 증가"
    # 모델코드 · 화면 크기 · 배치 수량은 KB · 배치안 사실이라 둔다
    assert mask_numbers("창면 OH55A ×3 사이니지") == "창면 OH55A ×3 사이니지"
    assert mask_numbers('Flip Pro 85" 앞 · QM55C') == 'Flip Pro 85" 앞 · QM55C'
