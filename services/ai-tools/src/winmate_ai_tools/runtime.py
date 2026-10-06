"""호출 한 번의 공통 처리 — 정책 · 모드(live/mock/record/replay) · 한도 · 제한 시간 · 재시도 · 카세트 · 호출 로그.

    async with track("llm", req.task, request=body, confidential=req.confidential, cfg=cfg) as call:
        call.check_policy()
        hit = await call.replay(key_payload)          # replay 모드: 카세트가 있으면 그 응답
        await call.acquire()                          # live · record: Redis 한도
        res = await call.invoke(provider.chat, cfg, llm_call)   # 세마포어 + 제한 시간 + 재시도
        call.record(key_payload, response)            # record 모드: 카세트 저장
        return call.done(response)
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from winmate_common import context, env
from winmate_common.errors import ApiError
from winmate_common.ids import new_id, now_iso

from . import calllog, cassette, limits
from .config import CapConfig, call_log_mode, model_mode, replay_fallback
from .errors import ProviderError, policy_confidential, timeout

log = logging.getLogger("winmate.ai_tools")

T = TypeVar("T")
MAX_RETRIES = 2
RETRY_BASE_S = 1.0          # 테스트에서 0 으로 바꾼다
_FALLBACK_RANK = {None: -1, "none": 0, "json_parse": 1, "json_repair": 2, "react": 3}


class Call:
    def __init__(self, cap: str, task: str | None, *, request: dict[str, Any] | None, confidential: bool,
                 cfg: CapConfig | None, units: int):
        self.id = new_id("call")
        self.cap = cap
        self.task = task
        self.ts = now_iso()
        self.t0 = time.perf_counter()
        self.mode = model_mode()
        self.effective = self.mode            # replay 에서 mock 으로 내려가면 바뀐다
        self.cfg = cfg
        self.units = units
        self.confidential = confidential
        self.request = request
        self.response: Any = None
        self.provider_name: str | None = None
        self.model: str | None = cfg.model if cfg else None
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self.attempts = 0
        self.fallback: str | None = None
        self.cassette: str | None = None
        self.key: str | None = None
        self.reservation: limits.Reservation | None = None

    # ── 상태 ───────────────────────────────────────────
    @property
    def enforced(self) -> bool:
        """실제 제공자를 부르는가(live · record) — 한도는 이때만."""
        return self.effective in ("live", "record")

    def latency_ms(self) -> int:
        return int((time.perf_counter() - self.t0) * 1000)

    def add_usage(self, usage: dict[str, int] | None) -> None:
        if usage:
            self.usage["input_tokens"] += int(usage.get("input_tokens") or 0)
            self.usage["output_tokens"] += int(usage.get("output_tokens") or 0)

    def set_fallback(self, value: str) -> None:
        if _FALLBACK_RANK.get(value, 0) > _FALLBACK_RANK.get(self.fallback, -1):
            self.fallback = value

    # ── 단계 ───────────────────────────────────────────
    def check_policy(self) -> None:
        """기밀 호출 차단(*_ALLOW_CONFIDENTIAL=false). mock 은 밖으로 나가는 것이 없어 막지 않는다 —
        차단 경로를 mock 으로 시험하려면 MOCK_ENFORCE_CONFIDENTIAL=true."""
        if not self.confidential or self.cfg is None or self.cfg.allow_confidential:
            return
        if self.mode == "mock" and not env.get_bool("MOCK_ENFORCE_CONFIDENTIAL", False):
            return
        raise policy_confidential(self.cap)

    def provider(self) -> Any:
        from . import providers

        name = "mock" if self.effective == "mock" else (self.cfg.provider_key if self.cfg else "mock")
        prov = providers.get(name)
        self.provider_name = prov.name if name != "mock" else "mock"
        return prov

    async def replay(self, key_payload: dict[str, Any]) -> dict[str, Any] | None:
        """record · replay 모드에서 카세트 키를 정한다. replay 면 카세트를 읽는다(없으면 404 또는 mock)."""
        if self.mode not in ("record", "replay"):
            return None
        self.key = cassette.request_key(key_payload)
        if self.mode != "replay":
            return None
        data = cassette.load(self.cap, self.task or "_", self.key)
        if data is not None:
            self.cassette = "replay_hit"
            self.provider_name = data.get("provider") or "replay"
            self.model = data.get("model") or self.model
            return data
        self.cassette = "replay_miss"
        if replay_fallback() == "mock":
            self.effective = "mock"
            return None
        raise ApiError(404, "CASSETTE_MISS", "재생할 카세트가 없습니다(MODEL_MODE=replay)",
                       {"capability": self.cap, "task": self.task, "key": self.key,
                        "path": str(cassette.path_for(self.cap, self.task or "_", self.key))})

    def record(self, key_payload: dict[str, Any], response: dict[str, Any],
               blobs: list[tuple[bytes, str]] | None = None) -> None:
        if self.mode != "record" or self.key is None:
            return
        try:
            cassette.save(self.cap, self.task or "_", self.key, request=key_payload, response=response,
                          provider=self.provider_name, model=self.model, blobs=blobs)
            self.cassette = "recorded"
        except OSError as exc:
            log.warning("카세트 저장 실패 %s/%s: %s", self.cap, self.task, exc)

    async def acquire(self) -> None:
        if self.enforced and self.cfg is not None:
            self.reservation = await limits.acquire(self.cfg, self.units)

    async def invoke(self, fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        """제공자 호출 1회: 세마포어 + 제한 시간 + 재시도(429 · 5xx, 최대 2회, 지수 백오프)."""
        cfg = self.cfg
        assert cfg is not None
        return await with_retries(lambda: fn(*args, **kwargs), cap=cfg.cap, timeout_s=cfg.timeout_s, call=self,
                                  sem=limits.semaphore(cfg))

    def done(self, response: dict[str, Any]) -> dict[str, Any]:
        """모델 기능(llm · i2t · t2i · websearch) 응답에 call_id · latency_ms 를 채운다."""
        response["call_id"] = self.id
        response["latency_ms"] = self.latency_ms()
        self.response = response
        return response

    # ── 로그 ───────────────────────────────────────────
    def to_record(self, status: str, error: dict[str, Any] | None) -> dict[str, Any]:
        full = call_log_mode() == "full"
        return {
            "id": self.id, "ts": self.ts, "capability": self.cap, "task": self.task,
            "provider": self.provider_name, "model": self.model, "mode": self.effective if self.effective == self.mode else f"{self.mode}->{self.effective}",
            "status": status, "latency_ms": self.latency_ms(), "usage": dict(self.usage),
            "caller": context.caller_var.get(), "request_id": context.request_id_var.get(),
            "user_id": context.user_id_var.get(), "confidential": self.confidential,
            "fallback": self.fallback, "cassette": self.cassette, "attempts": self.attempts, "error": error,
            "request": calllog.scrub(self.request) if full else None,
            "response": calllog.scrub(self.response) if full else None,
        }


async def with_retries(fn: Callable[[], Awaitable[T]], *, cap: str, timeout_s: float, call: Call | None = None,
                       sem: asyncio.Semaphore | None = None) -> T:
    """제한 시간 안에 fn() — 재시도할 수 있는 제공자 오류(429 · 5xx · 연결)는 최대 2번 더(1s · 2s 백오프).

    세마포어(동시 실행 수)를 기다리는 시간은 제한 시간에 넣지 않는다."""
    for attempt in range(MAX_RETRIES + 1):
        if call is not None:
            call.attempts += 1
        try:
            if sem is None:
                return await asyncio.wait_for(fn(), timeout=timeout_s)
            async with sem:
                return await asyncio.wait_for(fn(), timeout=timeout_s)
        except TimeoutError:
            raise timeout(cap, timeout_s) from None
        except ProviderError as exc:
            if exc.retryable and attempt < MAX_RETRIES:
                delay = RETRY_BASE_S * (2 ** attempt) * (1 + random.random() * 0.25)
                log.info("%s 재시도 %d/%d (%s) %.1fs 뒤", cap, attempt + 1, MAX_RETRIES, exc.code, delay)
                await asyncio.sleep(delay)
                continue
            raise
    raise AssertionError("unreachable")


@asynccontextmanager
async def track(cap: str, task: str | None, *, request: dict[str, Any] | None = None, confidential: bool = False,
                cfg: CapConfig | None = None, units: int = 1) -> AsyncIterator[Call]:
    call = Call(cap, task, request=request, confidential=confidential, cfg=cfg, units=units)
    status, error = "ok", None
    try:
        yield call
    except ApiError as exc:
        status, error = "error", {"status": exc.status, "code": exc.code, "message": exc.message}
        raise
    except (asyncio.CancelledError, GeneratorExit):
        status, error = "canceled", None
        raise
    except Exception as exc:
        status, error = "error", {"status": 500, "code": "INTERNAL", "message": f"{type(exc).__name__}: {exc}"}
        raise
    finally:
        await finish_call(call, status, error)


async def finish_call(call: Call, status: str, error: dict[str, Any] | None) -> None:
    """실패면 하루 한도 예약을 되돌리고, 호출 로그를 남긴다."""
    if status != "ok" and call.reservation is not None:
        try:
            await asyncio.shield(call.reservation.refund())
        except BaseException:  # noqa: BLE001 — 취소 중에도 로그는 남긴다
            pass
    write_log(call, status, error)


def write_log(call: Call, status: str, error: dict[str, Any] | None) -> None:
    if call_log_mode() == "off":
        return
    try:
        calllog.store().put(call.to_record(status, error))
    except Exception as exc:  # noqa: BLE001 — 로그 실패가 호출을 막지 않는다
        log.warning("호출 로그 저장 실패: %s", exc)
