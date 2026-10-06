"""모델 호출(ai-tools 경유, task = `sc.<동작>`) — 재시도 · 오류 구분 · 기밀 차단 시 익명화 대체 · 스트리밍.

- 고객 정보(고객사 · 시나리오 문장)가 든 프롬프트는 `confidential=True`.
- 403 `POLICY_CONFIDENTIAL` → **익명화 대체**(09 §7.1): 고객사명 · 지점명 → 「고객사」로 바꿔 `confidential=False` 로 다시 보내고,
  결과에서 「고객사」를 원래 이름으로 되돌린다(호출한 쪽이 시나리오에 `anonymized=true` 를 기록). 다른 모델로 몰래 바꾸지 않는다.
- 502 · 503 · 504 · 429 · 연결 오류 → `SC_LLM_RETRY_DELAYS`(기본 1초, 3초)만큼 다시. 소진되면 LlmError(한국어 메시지).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel
from winmate_common import env
from winmate_common.ai import ai
from winmate_common.client import ServiceClient, _headers
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.scenario.llm")

ANON = "고객사"

SYSTEM = (
    "너는 삼성전자 B2B 영업 제안서의 '공간 시나리오'를 돕는 작가다. 한국어로 답한다.\n"
    "규칙: (1) 입력 · KB 근거에 없는 사실 · 수치 · 고객명 · 제품 사양을 지어내지 않는다. 근거 없는 수치는 [00]으로 쓴다. "
    "(2) 고른 솔루션 · 제품만 등장시킨다. 솔루션 동작은 주어진 동작 사전 어휘로만 쓴다. "
    "(3) 실존 인물 이름을 쓰지 않고 역할명(점장 · 손님 …)으로 쓴다. (4) 경쟁사 이름 대신 '기존 시스템'이라고 쓴다. "
    "(5) '최초' · '유일' · '1위' 같은 최상급 · 인증 주장을 하지 않는다. (6) 요청한 형식만 돌려준다."
)


class LlmError(Exception):
    def __init__(self, code: str, message: str, status: int = 503):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


TRANSIENT = {429, 502, 503, 504}


def retry_delays() -> list[float]:
    raw = env.get("SC_LLM_RETRY_DELAYS", "1,3") or ""
    out = []
    for x in raw.split(","):
        try:
            out.append(float(x))
        except ValueError:
            continue
    return out


def _transient(exc: Exception) -> bool:
    if isinstance(exc, ApiError):
        return exc.status in TRANSIENT or exc.code in ("RATE_LIMITED", "UPSTREAM_UNAVAILABLE", "TIMEOUT")
    return isinstance(exc, (OSError, asyncio.TimeoutError)) or type(exc).__name__ in ("ConnectError", "ReadTimeout",
                                                                                         "RemoteProtocolError")


def _blocked(exc: Exception) -> bool:
    return isinstance(exc, ApiError) and (exc.code == "POLICY_CONFIDENTIAL" or (exc.status == 403 and "CONFIDENTIAL" in exc.code))


def to_error(exc: Exception) -> LlmError:
    if isinstance(exc, LlmError):
        return exc
    if _blocked(exc):
        return LlmError("POLICY_CONFIDENTIAL", "기밀 자료는 지금 설정된 모델로 보낼 수 없어요. 사내 모델 설정을 확인해 주세요.", 403)
    if isinstance(exc, ApiError):
        if exc.status == 504 or exc.code in ("TIMEOUT", "LLM_TIMEOUT"):
            return LlmError("LLM_TIMEOUT", "AI 응답이 늦어져 멈췄어요. 잠시 후 다시 시도해 주세요.", 504)
        if exc.code in ("DAILY_LIMIT_EXCEEDED", "QUOTA_EXCEEDED"):
            return LlmError("QUOTA_EXCEEDED", "오늘 쓸 수 있는 AI 호출 한도를 다 썼어요.", 429)
        return LlmError("LLM_UNAVAILABLE", "지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요.", 503)
    if isinstance(exc, asyncio.TimeoutError):
        return LlmError("LLM_TIMEOUT", "AI 응답이 늦어져 멈췄어요. 잠시 후 다시 시도해 주세요.", 504)
    return LlmError("LLM_UNAVAILABLE", "지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요.", 503)


async def _with_retry(fn: Callable[[], Awaitable[Any]], *, retries: bool = True) -> Any:
    delays = retry_delays() if retries else []
    attempt = 0
    while True:
        try:
            return await fn()
        except Exception as exc:
            if _transient(exc) and attempt < len(delays):
                await asyncio.sleep(delays[attempt])
                attempt += 1
                continue
            raise


# ── 익명화 ────────────────────────────────────────────────

def anon_names(customer: str | None, extra: list[str] | None = None) -> list[str]:
    """고객사명 변형(「A 커피 프랜차이즈」 → 「A 커피 프랜차이즈」 · 「A 커피」) + 지점명."""
    names: list[str] = []
    c = (customer or "").strip()
    if c:
        names.append(c)
        parts = c.split()
        if len(parts) >= 3:
            names.append(" ".join(parts[:2]))
    for x in extra or []:
        if x and len(x.strip()) >= 2:
            names.append(x.strip())
    return sorted(set(names), key=len, reverse=True)


def anonymize(text: str, names: list[str]) -> str:
    out = text
    for n in names:
        out = out.replace(n, ANON)
    return out


def restore(obj: Any, customer: str | None) -> Any:
    if not customer:
        return obj
    if isinstance(obj, str):
        return obj.replace(ANON, customer)
    if isinstance(obj, list):
        return [restore(x, customer) for x in obj]
    if isinstance(obj, dict):
        return {k: restore(v, customer) for k, v in obj.items()}
    return obj


class Result:
    def __init__(self, data: Any, anonymized: bool = False):
        self.data = data
        self.anonymized = anonymized


# ── JSON ──────────────────────────────────────────────────

async def json_call(task: str, prompt: str, schema: type[BaseModel], *, customer: str | None = None,
                    confidential: bool = True, timeout: float | None = None, retries: bool = True,
                    system: str = SYSTEM) -> Result:
    """JSON 결과. 실패하면 LlmError. 기밀 차단이면 익명화해 한 번 더(결과는 원래 이름으로)."""
    async def run(p: str, s: str, conf: bool) -> dict[str, Any]:
        async def one() -> dict[str, Any]:
            return await ai().json(task, p, schema, system=s, confidential=conf, temperature=0.3)
        coro = _with_retry(one, retries=retries)
        return await (asyncio.wait_for(coro, timeout) if timeout else coro)

    try:
        return Result(await run(prompt, system, confidential))
    except Exception as exc:
        if not _blocked(exc):
            log.info("%s 실패: %s", task, exc)
            raise to_error(exc) from exc
    names = anon_names(customer)
    try:
        data = await run(anonymize(prompt, names), anonymize(system, names), False)
    except Exception as exc:
        log.info("%s 익명화 재시도 실패: %s", task, exc)
        raise to_error(exc) from exc
    return Result(restore(data, customer), anonymized=True)


async def try_json(task: str, prompt: str, schema: type[BaseModel], **kw: Any) -> Result | None:
    """대체 경로가 있는 호출 — 실패면 None(로그만)."""
    try:
        return await json_call(task, prompt, schema, **kw)
    except LlmError as exc:
        log.info("%s → 대체 경로(%s)", task, exc.code)
        return None
    except Exception as exc:  # noqa: BLE001 — 스키마 검증 실패 등
        log.info("%s → 대체 경로(%s)", task, exc)
        return None


# ── 글(스트리밍) ───────────────────────────────────────────

_caps_cache: dict[str, Any] = {}


async def streaming_supported() -> bool:
    try:
        caps = await ai().capabilities()
        return bool(((caps.get("llm") or {}).get("supports") or {}).get("streaming"))
    except Exception:  # noqa: BLE001
        return False


async def _stream_once(task: str, prompt: str, system: str, confidential: bool,
                       on_delta: Callable[[str], Awaitable[None]] | None) -> str:
    c = ServiceClient("ai-tools", timeout=300)
    body = {"task": task, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "confidential": confidential, "temperature": 0.4}
    c._validate_request("POST", "/v1/llm/stream", body, True)
    acc = ""
    final: str | None = None
    async with c._async_client() as client, client.stream("POST", "/v1/llm/stream", json=body,
                                                          headers=_headers("ai-tools", {"Accept": "text/event-stream"})) as resp:
        if resp.status_code >= 400:
            raw = await resp.aread()
            try:
                err = json.loads(raw).get("error", {})
            except ValueError:
                err = {}
            raise ApiError(resp.status_code, err.get("code", "UPSTREAM_ERROR"), err.get("message", raw[:200].decode(errors="ignore")),
                           err.get("details") or {})
        event = ""
        async for line in resp.aiter_lines():
            if line.startswith("event:"):
                event = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            try:
                data = json.loads(payload)
            except ValueError:
                data = {"text": payload}
            if event == "delta":
                acc += data.get("text") or ""
                if on_delta:
                    await on_delta(acc)
            elif event == "done":
                final = data.get("content")
            elif event == "error":
                raise ApiError(int(data.get("status") or 503), data.get("code") or "UPSTREAM_UNAVAILABLE",
                               data.get("message") or "LLM 오류")
    return final if final is not None else acc


async def _chat_once(task: str, prompt: str, system: str, confidential: bool) -> str:
    return await ai().text(task, prompt, system=system, confidential=confidential, temperature=0.4)


async def text_call(task: str, prompt: str, *, customer: str | None = None, stream: bool = False,
                    on_delta: Callable[[str], Awaitable[None]] | None = None, confidential: bool = True,
                    system: str = SYSTEM, retries: bool = True) -> Result:
    """글 결과(스트리밍이면 부분 글마다 on_delta). 실패하면 LlmError. 기밀 차단이면 익명화 대체."""
    async def run(p: str, s: str, conf: bool, anon: bool) -> str:
        async def one() -> str:
            if stream:
                async def cb(acc: str) -> None:
                    if on_delta:
                        await on_delta(restore(acc, customer) if anon else acc)
                return await _stream_once(task, p, s, conf, cb if on_delta else None)
            return await _chat_once(task, p, s, conf)
        return await _with_retry(one, retries=retries)

    try:
        return Result(await run(prompt, system, confidential, False))
    except Exception as exc:
        if not _blocked(exc):
            log.info("%s 실패: %s", task, exc)
            raise to_error(exc) from exc
    names = anon_names(customer)
    try:
        out = await run(anonymize(prompt, names), anonymize(system, names), False, True)
    except Exception as exc:
        raise to_error(exc) from exc
    return Result(restore(out, customer), anonymized=True)


def strip_code_fence(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
    return re.sub(r"\s*```$", "", t)
