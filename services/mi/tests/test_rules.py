"""규칙 · 검증 단위 테스트(모델 없음) — AC-MI-01 · 05 · 20 · 21 · 22 · 29 · 33 · 34 · 37 · 39 · 40 · 85 · 88."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from winmate_mi import claims as C, config, rules, service, verify


def test_ac01_routing_rules_follow_config(tmp_path, monkeypatch):
    from winmate_mi.rules import render_rules

    out = render_rules()
    texts = " ".join(r["c"] + " " + r["o"] for s in out["stages"] for r in s["rules"]) + " ".join(s["sub"] for s in out["stages"])
    assert "0.80" in texts and "0.10" in texts
    assert len(out["stages"]) == 4 and out["layout"] and out["gaps"]["no"] == "6" and len(out["asks"]["items"]) == 4
    # 임계값을 0.85 로 바꾸면 화면 설명과 서버 판정이 함께 바뀐다
    cfg = tmp_path / "cfg"
    shutil.copytree(config.config_dir(), cfg)
    p = cfg / "routing.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace("segment_auto: 0.80", "segment_auto: 0.85"), encoding="utf-8")
    monkeypatch.setenv("MI_CONFIG_DIR", str(cfg))
    out2 = render_rules()
    texts2 = " ".join(r["c"] + " " + r["o"] for s in out2["stages"] for r in s["rules"]) + " ".join(s["sub"] for s in out2["stages"])
    assert "0.85" in texts2 and "0.84" in texts2
    assert rules.decide_segment([("FB", 0.82), ("RT", 0.30)]) == ("FB", "check")
    monkeypatch.delenv("MI_CONFIG_DIR")
    assert rules.decide_segment([("FB", 0.82), ("RT", 0.30)]) == ("FB", "auto")


@pytest.mark.parametrize("a,b,expect", [
    (0.85, 0.76, ("FB", "ask")), (0.85, 0.75, ("FB", "auto")), (0.80, 0.30, ("FB", "auto")), (0.79, 0.30, ("FB", "check")),
    (0.50, 0.20, ("FB", "check")), (0.49, 0.20, ("GEN", "auto")), (0.58, 0.55, ("FB", "ask")),
])
def test_ac05_segment_decision_order(a, b, expect):
    assert rules.decide_segment([("FB", a), ("HT", b)]) == expect


# MIC 라우팅 시나리오 12(§9.3) — 업종 판별 열. 4번은 두 벌(0.74/0.62 → check, 0.71/0.62 → ask · §11 Q1 은 MIR 규칙을 따른다)
MIC = [
    ("1", [("FB", 0.94), ("RT", 0.30)], {}, ("FB", "auto")),
    ("2", [("MD", 0.88), ("PB", 0.40)], {}, ("MD", "auto")),
    ("3", [("MF", 0.91), ("OF", 0.30)], {}, ("MF", "auto")),
    ("4a", [("RT", 0.74), ("FB", 0.62)], {}, ("RT", "check")),
    ("4b", [("RT", 0.71), ("FB", 0.62)], {}, ("RT", "ask")),
    ("5", [("HT", 0.58), ("FB", 0.55)], {}, ("HT", "ask")),
    ("6", [("VN", 0.31), ("RT", 0.22)], {}, ("GEN", "auto")),
    ("7", [("MD", 0.90), ("PB", 0.35)], {}, ("MD", "auto")),
    ("8", [("ED", 0.93), ("OF", 0.40)], {}, ("ED", "auto")),
    ("9", [("FN", 0.89), ("OF", 0.30)], {}, ("FN", "auto")),
    ("10", [("OE", 0.86), ("RT", 0.30)], {}, ("OE", "auto")),
    ("11", [("FB", 0.40)], {"inherited": "MD"}, ("MD", "auto")),
    ("12", [("AD", 0.95), ("PB", 0.30)], {}, ("AD", "auto")),
]


@pytest.mark.parametrize("no,cands,kw,expect", MIC, ids=[m[0] for m in MIC])
def test_mic_segment_routing(no, cands, kw, expect):
    assert rules.decide_segment(cands, **kw) == expect


def test_mic_stats():
    """보드 통계: 선택 필요 2/12(4번 보드값) — 4번을 규칙대로 두면 3/12."""
    modes = {no: rules.decide_segment(c, **kw)[1] for no, c, kw, _ in MIC}
    board = [m for no, m in modes.items() if no != "4b"]
    rule = [m for no, m in modes.items() if no != "4a"]
    assert board.count("ask") == 1 and rule.count("ask") == 2  # 업종 묻기는 5번(+4번) — 2/12 의 나머지 하나는 7번 대외비 묻기(넘김 시점)


def test_segment_pin_inherit_and_llm_fail():
    assert rules.decide_segment([("FB", 0.9)], pinned="HT") == ("HT", "pin")
    assert rules.decide_segment([("FB", 0.9)], inherited="MD") == ("MD", "auto")
    assert rules.decide_segment([("FB", 0.9), ("RT", 0.1)], llm_failed=True) == ("FB", "check")
    assert rules.combine_confidence(0.94, 0.94, 0.94) == 0.94
    assert rules.combine_confidence(None, 0.5, 1.0) == 0.7
    assert rules.mix_score(0.58, 0.55) == 0.57


def test_ac20_progress_formula():
    assert rules.progress_pct(1.0, 0.5, 0.0) == 58


def test_ac21_eta_labels():
    assert rules.eta_label(90) == "약 1분 30초"
    assert rules.eta_label(40) == "약 40초"
    assert rules.run_label(4) == "분석 시작 (약 3분)"


def test_ac22_tracker_previewable_and_pct():
    from winmate_mi.graphs.common import RunTracker

    t = RunTracker(None, "mi_x", ["market", "customer", "user", "competitor"], [], 180)
    t.gathered = {"market", "customer", "user", "competitor"}
    t.organized = {"market", "customer"}
    t.area_status.update(market="done", customer="done", user="run")
    snap = t.snapshot()
    assert snap["previewable"] == ["market", "customer"]
    assert snap["pct"] == 58


def test_ac85_weight_percent():
    crit = [{"id": f"c{i}", "name": str(i), "weight": w, "order": i, "enabled": True} for i, w in enumerate([5, 4, 3, 2, 1])]
    pct = [c["pct"] for c in service.criteria_with_pct(crit)]
    assert pct == [33, 27, 20, 13, 7] and sum(pct) == 100


# ── 검증(§7.6) ───────────────────────────────────────────
WEB = {"kind": "web", "published_at": "2026-03-10", "authority": 3}


def _claim(v, cid, text, cits, sources):
    v.setdefault("claims", {})[cid] = {"id": cid, "area": "market", "text": text, "numbers": []}
    v.setdefault("sources", {}).update(sources)
    v.setdefault("citations", []).extend(cits)
    return C.recompute(v, cid)


def test_ac28_ac29_quote_number_checks():
    claim = "디지털 메뉴보드를 쓰는 매장이 최근 3년간 42% 늘었습니다."
    page = "디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가했다."
    r1 = verify.check_citation(claim_text=claim, quote="디지털 메뉴보드를 쓰는 매장이 3년간 42% 증가", source=WEB, source_text=page)
    assert r1.status == "matched" and "42% 증가" in (r1.highlight or "")
    r2 = verify.check_citation(claim_text=claim, quote="메뉴보드 도입이 늘고 있다", source=WEB, source_text="메뉴보드 도입이 늘고 있다.")
    assert r2.status == "needs_check" and r2.reason_text == "수치 없이 흐름만 말해 42%를 뒷받침하지 못해요."
    v: dict = {}
    c = _claim(v, "clm_1", claim, [
        {"claim_id": "clm_1", "source_id": "s1", "status": r1.status, "value": verify.num_to_dict(r1.value)},
        {"claim_id": "clm_1", "source_id": "s2", "status": r2.status, "value": None, "reason_code": r2.reason_code, "check": r2.check}],
        {"s1": {**WEB, "id": "s1"}, "s2": {**WEB, "id": "s2"}})
    assert c["status"] == "needs_check" and c["label"] == "확인 필요 1"


def test_ac33_ac88_number_unsupported_masking():
    masked, bad = verify.mask_unsupported("시장 규모는 5,000억 원이에요.", [{"quote": "시장 규모가 커지고 있다"}])
    assert masked == "시장 규모는 [00]억 원이에요." and bad
    # 요약에 없는 구절 → 인용 버림
    summ = {"kind": "websearch_summary"}
    r = verify.check_citation(claim_text="시장 규모는 5,000억 원", quote="없는 구절", source=summ, source_text="시장 규모는 커지고 있다.")
    assert r.drop and r.reason_code == "QUOTE_NOT_FOUND"


def test_ac34_conflict_and_primary():
    v: dict = {}
    srcs = {"a": {"id": "a", "kind": "web", "published_at": "2026-03-01", "authority": 3}, "b": {"id": "b", "kind": "web", "published_at": "2025-06-01", "authority": 3}}
    na = verify.parse_numbers("5,000억 원")[0]
    nb = verify.parse_numbers("6,700억 원")[0]
    c = _claim(v, "c1", "시장 규모는 5,000억 원", [
        {"claim_id": "c1", "source_id": "a", "status": "matched", "value": verify.num_to_dict(na)},
        {"claim_id": "c1", "source_id": "b", "status": "needs_check", "value": verify.num_to_dict(nb)}], srcs)
    assert c["status"] == "conflict" and c["label"] == "출처 간 값 다름"
    assert c["conflict"]["primary_source_id"] == "a" and c["conflict"]["diff_ratio"] == 0.34
    v2: dict = {}
    n2 = verify.parse_numbers("5,900억 원")[0]
    c2 = _claim(v2, "c1", "시장 규모는 5,000억 원", [
        {"claim_id": "c1", "source_id": "a", "status": "matched", "value": verify.num_to_dict(na)},
        {"claim_id": "c1", "source_id": "b", "status": "matched", "value": verify.num_to_dict(n2)}], srcs)
    assert c2["status"] == "matched"


def test_ac37_kpi_text_mismatch():
    src = {"kind": "kb_case", "tier": "T5"}
    r = verify.check_citation(claim_text="매장 매출 12% 상승", quote="매출이 12% 올랐다", source=src, source_text="사례 원문에는 다른 문장만 있다.")
    assert r.status == "needs_check" and r.reason_text == "사례 원문과 문장이 달라요."


def test_ac39_ac40_prune_and_remove():
    v: dict = {"sources": {"w": {"id": "w", "kind": "web", "state": "used"}, "s": {"id": "s", "kind": "websearch_summary", "state": "used"},
                           "n": {"id": "n", "kind": "web", "state": "used"}}}
    cits = [{"claim_id": "c", "source_id": "w", "status": "matched"}, {"claim_id": "c", "source_id": "s", "status": "unverifiable"}]
    removed = verify.prune_summary_citations(cits, v["sources"])
    assert removed == ["s"]
    v["claims"] = {"c": {"id": "c", "area": "market", "text": "42% 증가"}}
    v["citations"] = cits + [{"claim_id": "c", "source_id": "n", "status": "needs_check"}]
    C.refresh_source_states(v)
    assert v["sources"]["s"]["state"] == "excluded" and v["sources"]["s"]["excluded_reason"] == "superseded"
    C.recompute(v, "c")
    assert v["claims"]["c"]["status"] == "needs_check"
    C.remove_citation(v, "c", "n")
    assert v["claims"]["c"]["status"] == "matched"
    C.remove_citation(v, "c", "w")
    assert v["claims"]["c"]["status"] == "missing"


def test_korean_numbers_and_tolerance():
    n = verify.parse_numbers("1.2조 원")[0]
    assert n.value == pytest.approx(1.2e12) and n.unit == "원"
    assert verify.parse_numbers("1,234억 원")[0].value == pytest.approx(1.234e11)
    assert verify.parse_numbers("2025년")[0].kind == "year"
    a, b = verify.parse_numbers("42%")[0], verify.parse_numbers("42.1%")[0]
    assert verify.same_value(a, b)          # 마지막 자리 절반(0.5) 안
    assert not verify.same_value(verify.parse_numbers("42%")[0], verify.parse_numbers("42%p")[0])
    assert verify.fmt_value(6.7e11, "원") == "6,700억 원"


def test_phrase_around_and_scope_keywords():
    areas, reasons, phrases = service.apply_scope_keywords("…경쟁사 대비… 주문 대기…", ["market"], {})
    assert areas == ["market", "user", "competitor"]
    assert phrases == ["경쟁사 대비", "주문 대기"]


def test_layout_fit_cp_and_unlock():
    from winmate_mi import layout

    m = {k: 0.0 for k in ("size_years", "cagr", "trends", "trends_dated", "implications", "verified_ratio", "metrics", "target_share", "segments_data",
                          "structure", "ops_stages", "strategy_doc", "swot_internal", "swot_external", "public_docs", "user_types", "journey_steps",
                          "composition", "share_data", "share_trend", "tabs_done")}
    m.update(suppliers=3.0, criteria=5.0, two_axis=3.0)
    assert layout.fit("CP-A", m)[0] >= 85
    assert 0 <= layout.fit("CP-B", m)[0] < 85
    assert layout.fit("CP-C", m)[0] == -1
    sheet = {"template_code": "CP-A", "sheet_type": "CP"}
    opt = layout.option_texts(sheet, "CP-B", m, "FB")
    a = next(o for o in opt["options"] if o["key"] == "A")
    assert a["predicted_fit"] >= 85 and a["recommended"]
    cands = layout.candidates(sheet, m, "FB", "CP-B")
    cpc = next(c for c in cands if c["code"] == "CP-C")
    assert cpc["fit"] == -1 and cpc["fit_label"] == "점유율 자료가 있으면 열려요"


def test_config_dir_exists():
    assert Path(config.config_dir(), "routing.yaml").is_file()
