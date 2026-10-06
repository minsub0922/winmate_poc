"""호출 한도 — Redis 카운터(분당 · 하루) + 기능별 동시 실행 세마포어.

- 분당: `wm:ai:rpm:<cap>:<epoch 분>` (INCR, 2분 뒤 만료). `<CAP>_RPM` 초과 → 429 RATE_LIMITED
- 하루: `wm:ai:day:<cap>:<YYYYMMDD 로컬 날짜>` (INCRBY 단위 수, 3일 뒤 만료). `<CAP>_DAILY_LIMIT` 초과 → 429 DAILY_LIMIT_EXCEEDED
  단위: llm · i2t · websearch = 호출 1회, t2i = 이미지 1장. 0 = 제한 없음.
- 실패한 호출은 하루 카운터에서 되돌린다(refund).
- 한도는 실제 제공자를 부르는 live · record 모드에서만 적용한다(mock · replay 는 Redis 를 건드리지 않는다).
- Redis 에 닿지 못하면 경고만 남기고 통과시킨다(카운터 장애가 모델 호출을 막지 않게).
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from winmate_common.errors import ApiError
from winmate_common.jobs import redis

from .config import CapConfig

log = logging.getLogger("winmate.ai_tools.limits")

_warned = False


def today() -> str:
    return time.strftime("%Y%m%d")


def _minute() -> int:
    return int(time.time() // 60)


def _rpm_key(cap: str, minute: int | None = None) -> str:
    return f"wm:ai:rpm:{cap}:{minute if minute is not None else _minute()}"


def _day_key(cap: str, day: str | None = None) -> str:
    return f"wm:ai:day:{cap}:{day or today()}"


def _redis_down(exc: Exception) -> None:
    global _warned
    if not _warned:
        log.warning("Redis 에 닿지 못해 한도 검사를 건너뜁니다: %s", exc)
        _warned = True


@dataclass
class Reservation:
    cap: str
    units: int
    day: str
    counted: bool

    async def refund(self) -> None:
        if not self.counted or self.units <= 0:
            return
        try:
            await redis().decrby(_day_key(self.cap, self.day), self.units)
        except Exception as exc:  # noqa: BLE001
            _redis_down(exc)
        self.counted = False


async def acquire(cfg: CapConfig, units: int = 1) -> Reservation:
    """분당 · 하루 한도를 검사하고 하루 카운터에 units 를 예약한다."""
    day = today()
    r = redis()
    try:
        if cfg.rpm > 0:
            key = _rpm_key(cfg.cap)
            n = await r.incr(key)
            if n == 1:
                await r.expire(key, 120)
            if n > cfg.rpm:
                await r.decr(key)
                retry_after = 60 - int(time.time() % 60)
                raise ApiError(429, "RATE_LIMITED", f"{cfg.cap} 분당 호출 한도({cfg.rpm}회)를 넘었습니다. 잠시 후 다시 시도하세요",
                               {"capability": cfg.cap, "limit": cfg.rpm, "window": "minute", "retry_after_s": retry_after})
        key = _day_key(cfg.cap, day)
        n = await r.incrby(key, units)
        if n == units:
            await r.expire(key, 3 * 24 * 3600)
        if cfg.daily_limit > 0 and n > cfg.daily_limit:
            await r.decrby(key, units)
            raise ApiError(429, "DAILY_LIMIT_EXCEEDED", f"{cfg.cap} 오늘 한도({cfg.daily_limit})를 넘었습니다",
                           {"capability": cfg.cap, "limit": cfg.daily_limit, "used": n - units, "requested": units})
        return Reservation(cfg.cap, units, day, True)
    except ApiError:
        raise
    except Exception as exc:  # noqa: BLE001 — Redis 장애
        _redis_down(exc)
        return Reservation(cfg.cap, units, day, False)


async def counts(cap: str) -> tuple[int, int]:
    """(오늘 사용량, 이번 분 사용량). Redis 가 없으면 (0, 0)."""
    try:
        r = redis()
        day_v, min_v = await asyncio.wait_for(
            asyncio.gather(r.get(_day_key(cap)), r.get(_rpm_key(cap))), timeout=2.0)
        return int(day_v or 0), int(min_v or 0)
    except Exception as exc:  # noqa: BLE001
        _redis_down(exc)
        return 0, 0


# ── 동시 실행 ──────────────────────────────────────────────
_sems: dict[tuple[int, str, int], asyncio.Semaphore] = {}


def semaphore(cfg: CapConfig) -> asyncio.Semaphore:
    """이벤트 루프 · 기능 · 크기별 세마포어(테스트마다 루프가 바뀌어도 안전)."""
    loop_id = id(asyncio.get_running_loop())
    key = (loop_id, cfg.cap, cfg.max_concurrency)
    sem = _sems.get(key)
    if sem is None:
        if len(_sems) > 256:
            _sems.clear()
        sem = _sems[key] = asyncio.Semaphore(cfg.max_concurrency)
    return sem
