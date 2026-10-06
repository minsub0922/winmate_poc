"""mock 고정 응답 — `mocks/ai-tools/<task>.json` (형식은 mocks/ai-tools/README.md).

- `{"json": …}` · `{"content": "…"}` · `{"tool_calls": [{"name", "arguments"}]}` · i2t `{"json"|"content", "boxes"}` ·
  웹 검색 `{"summary", "sources", "queries"}` · 오류 흉내 `{"error": {"status", "code", "message"}}`
- `{"responses": [ … ]}` 는 task 별 호출 횟수로 차례대로 돌려 쓴다(끝나면 처음부터).
  항목에 `when: {"contains": "QM55R" | ["A", "B"], "not_contains": …}` 가 있으면 요청 글(프롬프트 · 질의)에 맞는 첫 항목을 쓰고,
  맞는 것이 없으면 `when` 없는 항목들을 차례로 돌린다(동시 호출 · 입력별 응답을 결정적으로).
- 파일은 호출 때마다 읽는다(고치면 바로 반영).
"""
from __future__ import annotations

import json
import logging
import re
import threading
from typing import Any

from winmate_common.errors import ApiError

from .config import mocks_dir

log = logging.getLogger("winmate.ai_tools.fixtures")

_TASK = re.compile(r"^[A-Za-z0-9._-]+$")
_counts: dict[str, int] = {}
_lock = threading.Lock()


def reset() -> None:
    """테스트용: task 별 호출 횟수를 0 으로."""
    with _lock:
        _counts.clear()


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def _matches(when: dict[str, Any], text: str) -> bool:
    return (all(w in text for w in _as_list(when.get("contains")))
            and not any(w in text for w in _as_list(when.get("not_contains"))))


def next_response(task: str, text: str | None = None) -> dict[str, Any] | None:
    """task 의 다음 고정 응답(없으면 None). 'error' 가 있으면 ApiError 를 던진다. text = 요청 글(`when` 고르기용)."""
    if not task or not _TASK.match(task):
        return None
    path = mocks_dir() / f"{task}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ApiError(500, "MOCK_FIXTURE_INVALID", f"mock 고정 응답 파일을 읽지 못했습니다: {path.name}: {exc}") from exc
    item: Any = data
    if isinstance(data, dict) and isinstance(data.get("responses"), list) and data["responses"]:
        items = data["responses"]
        conditional = [r for r in items if isinstance(r, dict) and isinstance(r.get("when"), dict)]
        hit = next((r for r in conditional if _matches(r["when"], text or "")), None)
        if hit is not None:
            item = hit
        else:
            pool = [r for r in items if not (isinstance(r, dict) and isinstance(r.get("when"), dict))] or items
            with _lock:
                n = _counts.get(task, 0)
                _counts[task] = n + 1
            item = pool[n % len(pool)]
    else:
        with _lock:
            _counts[task] = _counts.get(task, 0) + 1
    if not isinstance(item, dict):
        # 리스트 · 문자열 등은 그대로 JSON 값으로 본다
        item = {"json": item}
    err = item.get("error")
    if isinstance(err, dict):
        raise ApiError(int(err.get("status", 502)), str(err.get("code", "PROVIDER_ERROR")),
                       str(err.get("message", "mock 오류")), dict(err.get("details") or {}))
    return item
