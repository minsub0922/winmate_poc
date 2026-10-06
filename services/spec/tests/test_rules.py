"""결정적 규칙(06-spec §7.9) — 숫자 · 단위 · 입력 파서 · 우위 · 출처 비교 · 문장 · 파일명 · 상태 · 열 나누기."""
from __future__ import annotations

import pytest
from winmate_spec.rules import compliance as C
from winmate_spec.rules import edit as E
from winmate_spec.rules import fmt as F
from winmate_spec.rules import text as T
from winmate_spec.rules import values as V
from winmate_spec.rules.package import split_columns


def test_numbers_and_units():
    assert F.fmt_num(4000) == "4,000" and F.fmt_num(500) == "500" and F.fmt_num(1237.9) == "1,237.9"
    assert F.fmt_num(1237.9, "1.234,5") == "1.237,9" and F.fmt_num(48.7, "1.234,5") == "48,7"
    assert str(F.mm_to_in(1237.9)) == "48.7" and str(F.mm_to_in(28.5)) == "1.1" and str(F.kg_to_lb(15.7)) == "34.6"
    assert str(F.kg_to_lb(19.9)) == "43.9"
    assert F.inch_from_code("LH55QMCEBGCXKR") == 55 and F.inch_from_code("LH115QHFEBGXKR") == 115
    assert F.inch_from_cm(138.7) == 55 and F.inch_from_cm(163.9) == 65
    assert F.grade_label(3840, 2160) == "UHD"
    assert F.parse_resolution("3,840 x 2,160") == (3840, 2160)


def test_render_text():
    f = V.Fmt()
    assert V.render_text("brightness_contrast", {"nit": 500.0, "ca": 4000.0, "cb": 1.0}, f)[0] == "500 nit · 4,000:1"
    assert V.render_text("power", {"typ": 100.0, "max": 150.0}, f)[0] == "100 W · 150 W"
    assert V.render_text("power", {"typ": 120.0, "max": None}, f)[0] == "120 W · [확정 필요]"
    assert V.render_text("power", None, f)[0] == "[확정 필요]"
    assert V.render_text("power", None, f, "en")[0] == "[To be confirmed]"
    en = V.Fmt(language="en", length_unit="inch", weight_unit="lb")
    text, conv, orig = V.render_text("dimensions", {"w": 1237.9, "h": 708.8, "d": 28.5}, en)
    assert (text, conv, orig) == ("48.7 × 27.9 × 1.1 in", True, "1237.9 x 708.8 x 28.5 mm")
    assert V.render_text("weight", {"set": 15.7, "pkg": 19.9}, en)[0] == "34.6 lb / 43.9 lb"
    assert V.render_text("warranty", {"years": 3}, V.Fmt(language="en"))[0] == "3 years"
    lines = V.render_lines("size_resolution", {"inch": 55, "w": 3840, "h": 2160}, V.Fmt(language="en"), "화면 크기 · 해상도",
                           ["Screen Size", "Resolution"])
    assert [(ln.label, ln.text) for ln in lines] == [("Screen Size", '55"'), ("Resolution", "UHD")]


def test_parse_input():
    assert V.parse_input("power", "100 / 150") == {"typ": 100.0, "max": 150.0}
    assert V.parse_input("power", "120 · 154") == {"typ": 120.0, "max": 154.0}
    assert V.parse_input("power", "120") == {"typ": 120.0, "max": None}
    with pytest.raises(V.InvalidValue) as e:
        V.parse_input("power", "100 kWh")
    assert e.value.expected_unit == "W" and e.value.message == "W 단위로 넣어 주세요."
    assert V.parse_input("brightness_contrast", "450 nit", {"nit": 500.0, "ca": 4000.0, "cb": 1.0}) == {"nit": 450.0, "ca": 4000.0, "cb": 1.0}
    assert V.parse_input("brightness_contrast", "450 cd/㎡")["nit"] == 450.0
    assert V.parse_input("warranty", "3년") == {"years": 3.0}
    assert V.parse_input("operation_hours", "24/7") == {"text": "24/7", "hours": 24.0}
    with pytest.raises(V.InvalidValue):
        V.parse_input("weight", "15 lb")


def test_wins():
    # 우위: 양쪽 숫자일 때만(§4.14.2) — [값] 끼리는 우위 없음
    b = [{"nit": 500.0, "ca": 4000.0, "cb": 1.0}, {"nit": 350.0, "ca": 4000.0, "cb": 1.0}]
    assert V.compute_wins("brightness_contrast", b) == [True, False]
    assert V.compute_wins("power", [{"typ": 120.0, "max": 180.0}, {"typ": 100.0, "max": 150.0}]) == [False, True]
    assert V.compute_wins("power", [{"typ": 120.0, "max": 180.0}, None]) == [False, False]
    assert V.compute_wins("size_resolution", [{"inch": 55, "w": 3840, "h": 2160}] * 2) == [False, False]


def test_source_compare_and_parts():
    a = {"nit": 350.0, "ca": 4000.0, "cb": 1.0}
    b = {"nit": 400.0, "ca": None, "cb": None}
    assert V.values_conflict("brightness_contrast", a, b) is True
    assert V.values_conflict("brightness_contrast", a, {"nit": 350.0, "ca": None, "cb": None}) is False
    assert V.diff_part("brightness_contrast", [a, b]) == ("밝기", ["350 nit", "400 nit"])
    assert V.merge_values({"nit": 350.0, "ca": None}, {"nit": 350.0, "ca": 4000.0}) == {"nit": 350.0, "ca": 4000.0}
    assert V.values_conflict("operation_hours", {"text": "24/7", "hours": 24.0}, {"text": "24시간", "hours": 24.0}) is False


def test_compliance_rules():
    assert C.quote_ok("2.3 밝기는 450 cd/㎡ 이상", "2. 성능\n2.3 밝기는 450 cd/m2 이상이어야 한다.")
    assert not C.quote_ok("2.3 밝기는 500 cd/㎡ 이상", "2.3 밝기는 450 cd/㎡ 이상")
    assert C.numbers_ok("대기실 2곳 65인치 이상", "3.2 대기실 2곳에는 65인치 이상 제품을 설치한다.")
    assert C.op_of("200 W 이하") == "<=" and C.op_of("55인치 이상") == ">="
    spec = {"attrs": {"전원 › 소비전력 (On Mode)": {"raw": "154 W", "num": 154.0}}, "derived": {}}
    r = C.evaluate_row({"kind": "numeric", "key": "power_consumption", "op": "<=", "value": 200}, spec)
    assert (r["verdict"], r["note"]) == ("unknown", "On Mode 154 W만 있음")
    assert C.evaluate_row({"kind": "procedural"}, spec)["note"] == "담당 부서 확인"
    assert C.folded_line([{"verdict": "pass"}] * 8 + [{"verdict": "pass"}] * 3 + [{"verdict": "unknown"}]) == "4개 더 · 충족 3 · 확인 필요 1"


def test_titles_and_filenames():
    ps = [{"id": "a", "display_name": "QM55C", "family_label_en": "Smart Signage", "size_inch": 55, "series_code": "QMC", "role": "proposed",
           "category_id": "top_display"},
          {"id": "b", "display_name": "QB55C", "family_label_en": "Smart Signage", "size_inch": 55, "series_code": "QBC", "role": "proposed",
           "category_id": "top_display"}]
    s = {"id": "sp_1", "products": ps, "kind": "compare", "customer_name": "A 커피 프랜차이즈", "format": {"language": "ko"}, "items": []}
    assert T.suggested_title(s) == 'QMC vs QBC 55" 비교'
    assert T.table_title(s) == 'Smart Signage 55" 비교 — QM55C vs QB55C'
    assert T.table_title(s, "en") == 'Samsung Smart Signage 55" Comparison'
    assert T.default_filename(s) == "A커피_QM55C-QB55C_스펙비교"
    assert T.default_filename({**s, "format": {"language": "en"}}) == "Samsung_Signage_55_Comparison_EN"
    assert F.josa("QM55R", "은", "는") == "은" and F.josa("밝기", "과", "와") == "와"


def test_status_rules():
    base = {"start": "model", "step": 3, "generated_at": "x", "checks": [], "warnings": [], "products": [{}]}
    assert T.status_of(base, "sp_1") == ("done", "완료", "/spec/sp_1")
    assert T.status_of({**base, "checks": [{"status": "open"}], "last_job_id": "job_1"}, "sp_1") == \
        ("check", "값 확인 필요 1", "/spec/sp_1/generating?job=job_1")
    assert T.status_of({**base, "warnings": [{"status": "open", "kind": "catalog_changed"}]}, "sp_1")[1] == "카탈로그 변경 1"
    assert T.status_of({**base, "active_job": {"id": "job_2", "kind": "spec_generate", "status": "running", "progress": 60}}, "sp_1") == \
        ("run", "생성 중 60%", "/spec/sp_1/generating?job=job_2")
    assert T.status_of({**base, "step": 1, "start": "find", "generated_at": None}, "sp_1") == ("draft", "작성 중 1/3", "/spec/sp_1/find")


def test_split_and_edit_summary():
    assert split_columns(5) == [(0, 5)] and split_columns(6) == [(0, 3), (3, 6)] and split_columns(7) == [(0, 4), (4, 7)]
    ops = [{"op": "move_row"}, {"op": "highlight_row"}, {"op": "set_memo"}, {"op": "hide_row"}, {"op": "add_rows"}]
    assert E.summary_text(E.summary(ops)) == "시트 편집 · 변경 5건 — 이동 1 · 강조 1 · 메모 1 · 숨김 1 · 추가 1"
    assert E.summary_text(E.summary([])) == "시트 편집 · 변경 없음"
