"""템플릿 카탈로그 — 원본(docs/templates/source)에서 다시 만든 결과와 같은지, 구조가 맞는지, 문서가 부르는 코드가 다 있는지."""
from __future__ import annotations

import io
import re

import pytest
from PIL import Image
from winmate_common.env import repo_root
from winmate_export.render.thumbs import render_thumbnail, thumb_size
from winmate_export.templates import build
from winmate_export.templates.catalog import catalog, normalize_code

SLOT_TYPES = {"text", "bullets", "number", "kpi", "image", "table", "chart", "logo", "caption", "source", "card"}


def test_catalog_is_up_to_date():
    assert build.main(["--check"]) == 0


def test_catalog_loads_and_counts():
    cat = catalog()
    st = cat.stats()
    assert st["total"] == len(cat.templates) >= 400
    assert st["by_status"]["ready"] >= 380
    assert sum(st["by_role"].values()) == st["total"]
    assert sum(st["by_section"].values()) == st["total"]
    codes = [normalize_code(t["code"]) for t in cat.templates]
    assert len(codes) == len(set(codes)), "코드 중복"
    for code in ("C01", "C04", "C05", "C07", "MS-B", "VP-F3", "P3-C", "MGI-D", "MI-FB-B", "SS-FB-D", "VM-A", "AX-A"):
        assert cat.get(code) is not None, code


def test_template_structure():
    for t in catalog().templates:
        keys = {s["key"] for s in t["slots"]}
        assert "title" in keys or t["sheet_role"] in ("DIVIDER",), t["code"]
        for s in t["slots"]:
            assert s["type"] in SLOT_TYPES, (t["code"], s)
            assert isinstance(s["required"], bool)
            if s["type"] == "card":
                assert s.get("fields"), (t["code"], s["key"])
        assert t["boxes"], t["code"]
        for b in t["boxes"]:
            assert b["slot"] is None or b["slot"] in keys, (t["code"], b)
            assert 0 <= b["x"] <= 1 and 0 <= b["y"] <= 1, (t["code"], b)
            assert b["x"] + b["w"] <= 1.001 and b["y"] + b["h"] <= 1.001, (t["code"], b)
            assert b["w"] > 0 and b["h"] > 0, (t["code"], b)


def test_display_codes_and_aliases():
    cat = catalog()
    assert cat.get("VP-F·3")["code"] == "VP-F3"
    assert cat.get("vp-f3")["code"] == "VP-F3"
    assert cat.get("VP-F")["code"] == "VP-F3"                                  # 기본
    assert cat.get("VP-F", {"pillars": [1, 2]})["code"] == "VP-F2"            # 기둥 수로
    assert cat.get("NOPE-1") is None


def test_search_filters():
    cat = catalog()
    ms = cat.search(role="MS")
    assert ms and all(t["sheet_role"] == "MS" for t in ms)
    fb = cat.search(role="MS", industry="FB")
    assert fb[0]["industry"] == "FB" and any(not t.get("industry") for t in fb)
    assert all(t.get("industry") in (None, "FB") for t in fb)
    assert all("quickwin" in t["proposal_types"] for t in cat.search(proposal_type="quickwin"))
    assert any(t["code"] == "C07" for t in cat.search(q="연락처"))


@pytest.mark.parametrize("doc", ["docs/scenarios/05-vp.md", "docs/scenarios/09-scenario.md", "docs/scenarios/10-proposal.md"])
def test_codes_referenced_in_scenarios_exist(doc):
    cat = catalog()
    prefixes = sorted(set(cat.data["roles"]) | {"VC", "P1", "P2", "P3", "P4", "P5"} | set(cat.data["solutions"]), key=len, reverse=True)
    rx = re.compile(r"(?<![A-Za-z0-9_\-])(?:" + "|".join(map(re.escape, prefixes)) + r")-[A-Z0-9]{1,3}(?:[-·][A-Z0-9]{1,3})?(?![A-Za-z0-9_])"
                    r"|(?<![A-Za-z0-9_\-])C(?:0[1-9]|1[0-2])(?![A-Za-z0-9_\-])")
    text = (repo_root() / doc).read_text(encoding="utf-8")
    industries = set(cat.data["industries"])
    missing = []
    for code in sorted({m.group(0) for m in rx.finditer(text)}):
        if "-XX" in code or (code.startswith("VP-") and code[3:] in industries):   # 업종판 묶음 이름 · 자리표시
            continue
        if cat.get(code) is None:
            missing.append(code)
    assert not missing, missing


@pytest.mark.parametrize("w", [None, 120, 240, 480])
def test_thumbnail_sizes(w):
    t = catalog().get("MS-B")
    png = render_thumbnail(t, w)
    im = Image.open(io.BytesIO(png))
    assert im.format == "PNG"
    assert im.size == thumb_size(w)
    if w in (None, 120):
        assert im.size == (120, 68)


def test_every_template_has_thumbnail():
    for t in catalog().templates:
        png = render_thumbnail(t, 120)
        assert png[:8] == b"\x89PNG\r\n\x1a\n", t["code"]
