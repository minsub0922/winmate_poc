"""ai-tools 호출(§7.1 · §8) — 모델 호출은 모두 `winmate_common.ai.ai()` 경유, task 이름은 `ca.<동작>`.

- LLM: JSON 스키마(Pydantic) · 스키마에 안 맞으면 오류를 붙여 1회 재시도 → 그래도 실패면 LLMFailed(호출한 쪽이 규칙 대체)
- 403 POLICY_CONFIDENTIAL · 503 · 504 도 LLMFailed 로 바꿔 올린다(code 보존) — 시나리오의 로컬 대체 경로로 내려가게
- 웹 검색어 보호(query_guard): 정의서 · RFP · 회의록 원문 20자 이상 부분 문자열 · 고객 계획 수치(예산 · 일정 · 매장 수)는 밖으로 내보내지 않는다
- 예산(Budget): 찾기 웹 검색 8 · 수집 12 · LLM 10 / 분석 경쟁사마다 웹 검색 5 · 수집 6 · LLM 4
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from winmate_common.ai import ai
from winmate_common.errors import ApiError

from . import config

log = logging.getLogger("winmate.competitor.ai")

M = TypeVar("M", bound=BaseModel)

SYSTEM = (
    "너는 삼성 B2B 제안서용 경쟁사 분석 에이전트다. 한국어로 쓴다. 받은 근거 묶음에 있는 문자열만 사실로 쓴다. "
    "수치 · 모델명 · 회사명 · 고객명을 지어내지 않는다. 모르는 글은 [확인 필요], 모르는 수치는 [00]으로 둔다. "
    "인용은 받은 근거 번호로만 하고, 구절은 근거 원문에서 그대로 옮긴다."
)

WEB_DOWN = {"UPSTREAM_UNAVAILABLE", "TIMEOUT", "RATE_LIMITED", "DAILY_LIMIT_EXCEEDED", "PROVIDER_ERROR", "NOT_CONFIGURED", "CASSETTE_MISS"}


class LLMFailed(Exception):
    def __init__(self, task: str, message: str, code: str = "LLM_FAILED"):
        super().__init__(f"{task}: {message}")
        self.task = task
        self.message = message
        self.code = code


async def llm(task: str, prompt: str, model: type[M], *, confidential: bool, system: str | None = SYSTEM, budget: "Budget | None" = None,
              max_tokens: int | None = None) -> M:
    """스키마 모드 LLM 호출 → 모델 인스턴스. 스키마 오류면 오류를 붙여 1회 재시도."""
    if budget is not None and not budget.take("llm"):
        raise LLMFailed(task, "LLM 예산을 다 썼어요", "BUDGET")
    last = ""
    for attempt in range(2):
        p = prompt if attempt == 0 else f"{prompt}\n\n[앞 응답 오류] {last}\n스키마에 맞는 JSON 만 다시 내라."
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": p}]
        try:
            res = await ai().chat(task, msgs, json_schema=model.model_json_schema(), schema_name=model.__name__,
                                  confidential=confidential, max_tokens=max_tokens)
            data = res.get("json")
            if data is None:
                raise ValueError("json 없음")
            return model.model_validate(data)
        except (ValidationError, ValueError) as exc:
            last = str(exc)[:500]
        except ApiError as exc:
            if exc.status == 422:
                last = exc.message
                continue
            raise LLMFailed(task, exc.message, exc.code) from exc
    raise LLMFailed(task, last or "스키마 오류", "SCHEMA_MISMATCH")


# ── 예산 ─────────────────────────────────────────────────
@dataclass
class Budget:
    websearch: int = 8
    fetch: int = 12
    llm: int = 10
    used: dict[str, int] = field(default_factory=lambda: {"websearch": 0, "fetch": 0, "llm": 0})
    web_unavailable: bool = False
    mode: str = "summary_only"
    caps: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def of(cls, kind: str) -> "Budget":
        b = config.budgets(kind)
        return cls(websearch=b.get("websearch", 8), fetch=b.get("fetch", 12), llm=b.get("llm", 10))

    def take(self, kind: str) -> bool:
        if self.used[kind] >= getattr(self, kind):
            return False
        self.used[kind] += 1
        return True


# ── 능력 · 웹 모드 ───────────────────────────────────────
_caps: tuple[float, dict[str, Any]] | None = None


async def capabilities() -> dict[str, Any]:
    global _caps
    if _caps and time.time() - _caps[0] < 30:
        return _caps[1]
    try:
        caps = await ai().c.get("/v1/capabilities")
    except ApiError:
        caps = {}
    _caps = (time.time(), caps)
    return caps


def reset_caps() -> None:
    global _caps
    _caps = None
    try:
        ai()._caps = None
    except Exception:  # noqa: BLE001
        pass


def web_mode(caps: dict[str, Any]) -> str:
    """`sources`: WEBSEARCH_RETURN_SOURCES=true 또는 검색 API 있음 · 그 밖 `summary_only`(03-mi.md §7.1 표)."""
    ws = caps.get("websearch") or {}
    sa = caps.get("search_api") or {}
    if ws.get("return_sources") or (sa.get("provider") not in (None, "", "none") and sa.get("available", True)):
        return "sources"
    return "summary_only"


async def init_budget(kind: str) -> Budget:
    b = Budget.of(kind)
    caps = await capabilities()
    b.caps = caps
    b.mode = web_mode(caps)
    ws = caps.get("websearch") or {}
    if caps and ws and ws.get("available") is False:
        b.web_unavailable = True
    return b


def public_caps(caps: dict[str, Any]) -> dict[str, Any]:
    ws = caps.get("websearch") or {}
    sa = caps.get("search_api") or {}
    return {"mode": web_mode(caps), "websearch_available": bool(ws.get("available", bool(ws))), "returns_sources": bool(ws.get("return_sources")),
            "search_api": sa.get("provider") or "none", "fetch": bool((caps.get("fetch") or {}).get("enabled"))}


# ── 검색어 보호(§7.1 query_guard) ────────────────────────
_PLAN_NUM = re.compile(r"\d[\d,\.]*\s*(?:만|억|조)?\s*(?:개|곳|매장|원|억 원|만 원|%|명|대|실|개월|주|일)")


def query_guard(query: str, sensitive: list[str]) -> str | None:
    """외부 검색어에서 고객 원문 20자 이상 부분 문자열 · 고객 계획 수치를 지운다. 남는 게 없으면 None(검색 건너뜀).
    고객사 · 경쟁사 이름 · 업종 · 지역 · 제품군은 그대로 둔다."""
    q = re.sub(r"\s+", " ", (query or "").strip())
    if not q:
        return None
    shingles: set[str] = set()
    plan: set[str] = set()
    for t in sensitive:
        t = re.sub(r"\s+", " ", t or "")
        for i in range(0, max(0, len(t) - 19)):
            shingles.add(t[i:i + 20])
        for m in _PLAN_NUM.finditer(t):
            plan.add(re.sub(r"\s+", "", m.group(0)))
    kill = [False] * len(q)
    for i in range(0, max(0, len(q) - 19)):
        if q[i:i + 20] in shingles:
            for j in range(i, i + 20):
                kill[j] = True
    out = "".join(ch for ch, k in zip(q, kill) if not k)
    for m in list(_PLAN_NUM.finditer(out)):
        if re.sub(r"\s+", "", m.group(0)) in plan:
            out = out.replace(m.group(0), " ")
    out = re.sub(r"\s+", " ", out).strip(" ,·-")
    return out if len(out) >= 2 else None


# ── 웹 ───────────────────────────────────────────────────
async def websearch(task: str, query: str, *, max_sources: int = 6) -> dict[str, Any]:
    return await ai().websearch(task, query, max_sources=max_sources, confidential=False)


async def search(query: str, limit: int = 3) -> dict[str, Any]:
    return await ai().search(query, limit=limit)


async def fetch(url: str, max_chars: int = 20000) -> dict[str, Any] | None:
    """수집 성공한 페이지만 돌려준다(차단 · 오류 · 빈 본문은 None — 그 URL 은 어디에도 보이지 않는다)."""
    try:
        res = await ai().fetch(url, max_chars=max_chars)
    except ApiError as exc:
        log.info("fetch 실패 %s: %s", url, exc)
        return None
    if not res.get("allowed", True) or not (res.get("text") or res.get("pages")) or int(res.get("status") or 200) >= 400:
        return None
    return res


def web_down(exc: ApiError) -> bool:
    return exc.status in (429, 502, 503, 504) or exc.code in WEB_DOWN
