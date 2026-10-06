"""SSE 응답 도우미."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from sse_starlette.sse import EventSourceResponse


def sse_response(events: AsyncIterator[dict[str, Any]], *, ping_s: int = 15) -> EventSourceResponse:
    """events: {"event": str, "id": str|None, "data": dict|str} 를 내는 async 제너레이터."""

    async def gen() -> AsyncIterator[dict[str, Any]]:
        async for ev in events:
            data = ev.get("data")
            yield {
                "event": ev.get("event") or "message",
                "id": ev.get("id"),
                "data": data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, default=str),
            }

    return EventSourceResponse(gen(), ping=ping_s, headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
