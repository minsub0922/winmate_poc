"""workspace 저장소(data/workspace/workspace.sqlite)와 공용 상수."""
from __future__ import annotations

from typing import Literal

from winmate_common import env
from winmate_common.store import DocStore

FEATURES = ("RQ", "SB", "DS", "IMG", "BE", "SC", "MI", "CA", "VP", "SP", "PR")
Feature = Literal["RQ", "SB", "DS", "IMG", "BE", "SC", "MI", "CA", "VP", "SP", "PR"]

_store: DocStore | None = None

_INDEXES = (
    ("items", "feature"), ("items", "owner"), ("items", "project_id"), ("comments", "target"), ("reviews", "target"),
    ("reviews", "item_id"), ("users", "username"), ("users", "role"), ("share_links", "token"), ("asset_usage", "ref"),
    ("notifications", "recipient"), ("notifications", "item_id"),
)


def store() -> DocStore:
    global _store
    if _store is None:
        _store = DocStore.for_service("workspace")
        for coll, field in _INDEXES:
            _store.index(coll, field)
    return _store


def reset_store() -> None:
    """테스트용 — 다음 store() 가 지금 DATA_DIR 로 새로 연다."""
    global _store
    _store = None


def auth_mode() -> str:
    return (env.get("AUTH_MODE", "none") or "none").lower()
