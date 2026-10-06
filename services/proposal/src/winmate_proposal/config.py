"""설정 · 시계.

- PROPOSAL_FIXED_NOW      고정 시계(테스트 · 시연, ISO 8601). §9.0 은 2026-10-01T09:00+09:00
- PROPOSAL_MARK_CUSTOMER_TEXT_CONFIDENTIAL  고객 텍스트가 든 모델 호출을 기밀로(§10.13, 기본 true)
- PROPOSAL_PACE_S         mock 시연용 단계 사이 쉼(초). 실제 모델 · 테스트는 0
- PROPOSAL_EXPORT_WAIT_S  export 잡(PDF · 렌더)을 기다리는 최대 시간(초)
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from winmate_common import env
from winmate_common.env import settings

KST = timezone(timedelta(hours=9))


def now() -> datetime:
    fixed = env.get("PROPOSAL_FIXED_NOW")
    if fixed:
        try:
            dt = datetime.fromisoformat(fixed.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=KST)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now().astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def today_kst() -> date:
    return now().astimezone(KST).date()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def customer_text_confidential() -> bool:
    return env.get_bool("PROPOSAL_MARK_CUSTOMER_TEXT_CONFIDENTIAL", True)


def mock_mode() -> bool:
    return settings().model_mode == "mock"


def pace_s() -> float:
    default = 0.35 if mock_mode() and settings().winmate_env != "test" else 0.0
    return env.get_float("PROPOSAL_PACE_S", default)


async def pace() -> None:
    s = pace_s()
    if s > 0:
        await asyncio.sleep(s)


def export_wait_s() -> float:
    return env.get_float("PROPOSAL_EXPORT_WAIT_S", 90.0)


def time_label(iso: str | None) -> str:
    """「오늘 11:00」 · 「어제 18:30」 · 「10.05 14:20」"""
    dt = parse_iso(iso)
    if dt is None:
        return ""
    local = dt.astimezone(KST)
    today = today_kst()
    hm = local.strftime("%H:%M")
    if local.date() == today:
        return f"오늘 {hm}"
    if local.date() == today - timedelta(days=1):
        return f"어제 {hm}"
    return f"{local.month:02d}.{local.day:02d} {hm}"


def when_label(iso: str | None) -> str:
    """작업 목록의 「어제」 · 「3일 전」 · 「오늘」"""
    dt = parse_iso(iso)
    if dt is None:
        return ""
    d = (today_kst() - dt.astimezone(KST).date()).days
    if d <= 0:
        return "오늘"
    if d == 1:
        return "어제"
    if d < 7:
        return f"{d}일 전"
    return dt.astimezone(KST).strftime("%Y.%m.%d")


WEEKDAYS = "월화수목금토일"


def due_long_label(d: date | None) -> str:
    """「10월 8일 (수)」"""
    if d is None:
        return ""
    return f"{d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"
