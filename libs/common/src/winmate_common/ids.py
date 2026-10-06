"""ID: `<접두사>_<ULID 26자>` (시간순 정렬 가능)."""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid() -> str:
    ms = int(time.time() * 1000)
    rnd = int.from_bytes(os.urandom(10), "big")
    value = (ms << 80) | rnd
    out = []
    for _ in range(26):
        value, r = divmod(value, 32)
        out.append(_CROCKFORD[r])
    return "".join(reversed(out))


def new_id(prefix: str) -> str:
    return f"{prefix}_{ulid()}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def now_ts() -> float:
    return time.time()
