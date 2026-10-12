"""winmate_common.edits — 저장한 판 · 고친 곳 수 · 되돌리기(웹앱 ① v63)."""
from winmate_common.edits import SNAPSHOT, changes_of, ensure_snapshot, restore_snapshot, snapshot_view, take_snapshot

KEYS = ("industry", "spaces", "solutions")


def _doc():
    return {"id": "d1", "code": "DSS-01", "ver": 1, "industry": {"value": "오피스", "by": "manual"},
            "spaces": [{"key": "s1", "name": "로비", "products": [{"id": "p1", "name": "QM55C", "qty": "2대"}]},
                       {"key": "s2", "name": "회의실", "products": []}],
            "solutions": [{"name": "MagicINFO"}]}


def test_no_change_is_zero():
    d = _doc()
    d[SNAPSHOT] = take_snapshot(d, KEYS)
    assert changes_of({k: d[k] for k in KEYS}, {k: d[SNAPSHOT][k] for k in KEYS}) == 0


def test_counts_leaf_add_remove():
    d = _doc()
    d[SNAPSHOT] = take_snapshot(d, KEYS)
    d["spaces"][0]["products"][0]["qty"] = "3대"                       # 1
    d["spaces"].insert(0, {"key": "s0", "name": "라운지", "products": []})  # +1 (앞에 끼워도 뒤를 다 세지 않음)
    d["solutions"] = []                                                 # -1
    cur = {k: d[k] for k in KEYS}
    old = {k: snapshot_view(d, KEYS)[k] for k in KEYS}
    assert changes_of(cur, old) == 3


def test_ignore_derived_and_empty():
    assert changes_of({"counts": {"a": 1}, "note": None}, {"counts": {"a": 2}}) == 0
    assert changes_of({"note": ""}, {"note": None}) == 0


def test_restore_and_ensure():
    d = _doc()
    assert restore_snapshot(d, KEYS) is False
    assert ensure_snapshot(d, KEYS, saved=True) is True
    assert ensure_snapshot(d, KEYS, saved=True) is False
    d["industry"] = {"value": "리테일", "by": "manual"}
    assert restore_snapshot(d, KEYS) is True
    assert d["industry"]["value"] == "오피스"
    assert ensure_snapshot({"x": 1}, KEYS, saved=False) is False
