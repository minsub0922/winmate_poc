"""라우팅 시나리오 12(VPC 골든 · 05-vp.md §3.7 · §9.12) — 같은 재료 틀, 다른 결과."""
from __future__ import annotations

import pytest

from winmate_vp import scenarios

FIXTURES = scenarios.load_fixtures()


def test_twelve_fixtures_present():
    assert [f["no"] for f in FIXTURES] == list(range(1, 13))


@pytest.mark.parametrize("fx", FIXTURES, ids=[f"{f['no']}-{f['name']}" for f in FIXTURES])
def test_golden_case(fx):
    r = scenarios.run_case(fx)
    e = fx["expect"]
    assert r["flow_label"] == e["flow_label"]
    assert r["chips"] == e["chips"]
    assert r["industry"]["name"] == e["industry"] and r["industry"]["mode"] == e["industry_mode"]
    if e.get("asked") is None:
        assert r["asked"] is None or r["asked"]["mode"] == "pin", r["asks"]
    else:
        assert (r["asked"]["kind"], r["asked"]["mode"]) == (e["asked"]["kind"], e["asked"]["mode"]), r["asks"]
    if e.get("reason"):
        assert r["plan"]["reason"] == e["reason"]
    for text in e.get("decisions") or []:
        assert any(d["text"] == text for d in r["plan"]["decisions"]), [d["text"] for d in r["plan"]["decisions"]]


def test_stats_match_board():
    results = [scenarios.run_case(f) for f in FIXTURES]
    assert [s["n"] for s in scenarios.stats(results)] == ["5/12", "2/12", "17종", "0/16"]
