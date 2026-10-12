"""저장된 콘텐츠를 최종본에서 바로 고칠 때(웹앱 ① v63 · docs/scenarios/11-content-flow.md §7) — 마지막 저장 판과 지금 판의 차이 · 되돌리기.

콘텐츠 문서는 칸을 고칠 때마다 바로 저장된다(작성 중 자동 저장). 저장(:finish)은 Storyboard 에 반영하는 「판」을 만든다.
저장한 뒤 다시 고치면 화면 머리에 「고친 곳 n · 되돌리기 · 저장 · vN+1」이 뜬다 — n 과 되돌리기를 여기서 계산한다.

    from winmate_common.edits import SNAPSHOT, take_snapshot, ensure_snapshot, changes_of, restore_snapshot, snapshot_view

    EDIT_KEYS = ("industry", "spaces", "solutions")          # 사람이 고치는 값(메타 · 판 번호 · AI 후보 목록은 빼도 된다)

    # :finish(저장) 안에서 — 저장한 판을 문서에 남긴다
    doc[SNAPSHOT] = take_snapshot(doc, EDIT_KEYS)

    # 응답에 고친 곳 수 — stage(…) 는 그 서비스의 flow.json stages.<key> 값 만드는 함수
    changes = changes_of(stage(doc), stage(snapshot_view(doc, EDIT_KEYS)))

    # :revert — 저장한 판으로
    restore_snapshot(doc, EDIT_KEYS)          # 저장한 판이 없으면 False

차이 세기(changes_of): 값이 다른 잎 하나 = 1. 목록은 항목의 id(없으면 name · key · ref)로 맞춰 보고, 더해진 항목 · 빠진 항목은 각각 1로 센다
(앞에 하나 끼워도 뒤 항목이 다 바뀐 것으로 세지 않는다). counts · progress · updated_at 같은 파생 값은 세지 않는다.
"""
from __future__ import annotations

import copy
from typing import Any, Iterable

SNAPSHOT = "saved_snapshot"
IGNORE = frozenset({"counts", "progress", "updated_at", "updatedAt", "ver", "ref", "prevVer", "saved_at", "version"})
_ID_KEYS = ("id", "name", "key", "ref", "title")


def take_snapshot(doc: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    """저장한 판 — 사람이 고치는 값만 깊은 복사."""
    return {k: copy.deepcopy(doc.get(k)) for k in keys}


def has_snapshot(doc: dict[str, Any]) -> bool:
    return isinstance(doc.get(SNAPSHOT), dict)


def ensure_snapshot(doc: dict[str, Any], keys: Iterable[str], saved: bool) -> bool:
    """예전에 저장한 문서(판을 남기기 전)는 지금 값을 저장한 판으로 본다. 새로 남겼으면 True(호출 쪽이 문서를 다시 쓴다)."""
    if saved and not has_snapshot(doc):
        doc[SNAPSHOT] = take_snapshot(doc, keys)
        return True
    return False


def snapshot_view(doc: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    """저장한 판으로 본 문서(메타는 지금 문서 그대로) — stage(…) 로 저장한 판의 값을 만들 때."""
    snap = doc.get(SNAPSHOT)
    if not isinstance(snap, dict):
        return doc
    view = dict(doc)
    for k in keys:
        if k in snap:
            view[k] = copy.deepcopy(snap[k])
    return view


def restore_snapshot(doc: dict[str, Any], keys: Iterable[str]) -> bool:
    """저장한 판으로 되돌린다(문서를 바꾼다). 저장한 판이 없으면 False."""
    snap = doc.get(SNAPSHOT)
    if not isinstance(snap, dict):
        return False
    for k in keys:
        if k in snap:
            doc[k] = copy.deepcopy(snap[k])
    return True


def _ident(x: Any) -> Any:
    if isinstance(x, dict):
        for k in _ID_KEYS:
            v = x.get(k)
            if isinstance(v, (str, int)) and v != "":
                return (k, v)
    return None


def changes_of(a: Any, b: Any, ignore: frozenset[str] = IGNORE) -> int:
    """a(지금) 와 b(저장한 판) 의 다른 곳 수."""
    if isinstance(a, dict) and isinstance(b, dict):
        n = 0
        for k in set(a) | set(b):
            if k in ignore:
                continue
            if k not in a or k not in b:
                # 한쪽에만 있는 키 — 값이 비어 있지 않을 때만 센다(None · 빈 목록 · 빈 글은 같은 것으로)
                v = a.get(k, b.get(k))
                n += 0 if v in (None, "", [], {}) else 1
                continue
            n += changes_of(a[k], b[k], ignore)
        return n
    if isinstance(a, list) and isinstance(b, list):
        ida = [_ident(x) for x in a]
        idb = [_ident(x) for x in b]
        if a and b and all(ida) and all(idb) and len(set(ida)) == len(ida) and len(set(idb)) == len(idb):
            mb = dict(zip(idb, b))
            n = 0
            for i, x in zip(ida, a):
                n += changes_of(x, mb[i], ignore) if i in mb else 1
            sa = set(ida)
            n += sum(1 for i in idb if i not in sa)
            return n
        # 같은 자리끼리 · 길이 차이는 하나씩
        n = sum(changes_of(x, y, ignore) for x, y in zip(a, b))
        return n + abs(len(a) - len(b))
    if (a in (None, "") and b in (None, "")):
        return 0
    return 0 if a == b else 1
