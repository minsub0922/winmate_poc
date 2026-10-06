"""ai-tools 호출(§7.1 · §8) — 모델 호출은 모두 `winmate_common.ai.ai()` 경유.

- LLM: JSON 스키마(Pydantic) · 스키마에 안 맞으면 오류를 붙여 1회 재시도 → 그래도 실패면 LLMFailed
- 웹 검색어 보호(query_guard): 요구사항 · 첨부 원문 20자 이상 부분 문자열 · 고객 계획 수치는 밖으로 내보내지 않는다
- 기밀 차단(403 POLICY_CONFIDENTIAL) · 장애(503 · 504)는 ApiError 그대로 올린다(호출한 쪽이 시나리오대로 처리)
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from winmate_common.ai import ai
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.mi.ai")

M = TypeVar("M", bound=BaseModel)

SYSTEM = (
    "너는 삼성 B2B 제안서용 시장 분석(Market Intelligence) 에이전트다. 한국어로 쓴다. "
    "근거 묶음에 있는 문자열만 사실로 쓴다. 수치 · 모델코드 · 고객명 · 회사명을 지어내지 않는다. "
    "모르는 수치는 [00], 모르는 글은 [확인 필요]로 둔다. 인용은 받은 근거 번호로만 하고, 구절은 근거 원문에서 그대로 옮긴다. "
    "경쟁사 실명은 분석 안에서만 쓰고 내보내기 문장은 받은 표기만 쓴다."
)


class LLMFailed(Exception):
    def __init__(self, task: str, message: str):
        super().__init__(f"{task}: {message}")
        self.task = task
        self.message = message


async def llm(task: str, prompt: str, model: type[M], *, confidential: bool, system: str | None = SYSTEM,
              max_tokens: int | None = None) -> M:
    """스키마 모드 LLM 호출 → 모델 인스턴스. 스키마 오류면 오류를 붙여 1회 재시도."""
    last_err = ""
    for attempt in range(2):
        p = prompt if attempt == 0 else f"{prompt}\n\n[앞 응답 오류] {last_err}\n스키마에 맞는 JSON 만 다시 내라."
        try:
            res = await ai().chat(task, ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": p}],
                                  json_schema=model.model_json_schema(), schema_name=model.__name__, confidential=confidential,
                                  max_tokens=max_tokens)
            data = res.get("json")
            if data is None:
                raise ValueError("json 없음")
            return model.model_validate(data)
        except ValidationError as exc:
            last_err = str(exc)[:500]
        except ValueError as exc:
            last_err = str(exc)[:500]
        except ApiError as exc:
            if exc.status == 422:
                last_err = exc.message
                continue
            raise
    raise LLMFailed(task, last_err or "스키마 오류")


# ── 웹 ───────────────────────────────────────────────────
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
    ws = caps.get("websearch") or {}
    sa = caps.get("search_api") or {}
    if ws.get("return_sources") or (sa.get("provider") not in (None, "", "none") and sa.get("available", True)):
        return "sources"
    return "summary_only"


def public_caps(caps: dict[str, Any]) -> dict[str, Any]:
    ws = caps.get("websearch") or {}
    sa = caps.get("search_api") or {}
    return {
        "websearch": {"available": bool(ws.get("available", bool(ws))), "returns_sources": bool(ws.get("return_sources"))},
        "search_api": {"provider": sa.get("provider") or "none", "available": bool(sa.get("available"))},
        "fetch": bool((caps.get("fetch") or {}).get("enabled")),
        "i2t": bool((caps.get("i2t") or {}).get("available", bool(caps.get("i2t")))),
        "mode": caps.get("mode") or "",
    }


_NUM_TOKEN = re.compile(r"\d[\d,\.]*\s*(?:만|억|조)?\s*(?:개|곳|매장|원|억 원|%|명|대|실)?")


def query_guard(query: str, sensitive: list[str], *, allow_numbers: set[str] | None = None) -> str | None:
    """외부 검색어에서 고객 원문 20자 이상 부분 문자열 · 고객 계획 수치를 지운다. 남는 게 없으면 None(검색 건너뜀)."""
    q = (query or "").strip()
    if not q:
        return None
    shingles: set[str] = set()
    plan_nums: set[str] = set()
    for t in sensitive:
        t = re.sub(r"\s+", " ", t or "")
        for i in range(0, max(0, len(t) - 19)):
            shingles.add(t[i:i + 20])
        for m in _NUM_TOKEN.finditer(t):
            tok = m.group(0).strip()
            if re.search(r"\d", tok):
                plan_nums.add(re.sub(r"\s+", "", tok))
    norm = re.sub(r"\s+", " ", q)
    kill = [False] * len(norm)
    for i in range(0, max(0, len(norm) - 19)):
        if norm[i:i + 20] in shingles:
            for j in range(i, i + 20):
                kill[j] = True
    out = "".join(ch for ch, k in zip(norm, kill) if not k)
    for m in list(_NUM_TOKEN.finditer(out)):
        tok = re.sub(r"\s+", "", m.group(0).strip())
        if tok and tok in plan_nums and not (allow_numbers and tok in allow_numbers):
            out = out.replace(m.group(0).strip(), " ")
    out = re.sub(r"\s+", " ", out).strip(" ,·-")
    if len(out) < 2:
        return None
    return out


async def websearch(task: str, query: str, *, max_sources: int = 6) -> dict[str, Any]:
    return await ai().websearch(task, query, max_sources=max_sources, confidential=False)


async def search(query: str, limit: int = 5) -> dict[str, Any]:
    return await ai().search(query, limit=limit)


async def fetch(url: str, max_chars: int = 20000) -> dict[str, Any] | None:
    try:
        res = await ai().fetch(url, max_chars=max_chars)
    except ApiError as exc:
        log.info("fetch 실패 %s: %s", url, exc)
        return None
    if not res.get("allowed", True) or not (res.get("text") or res.get("pages")) or int(res.get("status") or 200) >= 400:
        return None
    return res


async def i2t_page(task: str, file_id: str, page: int) -> str:
    """글자 층 없는 쪽을 받아쓰기(파일 쪽 그림 → i2t). 실패하면 빈 문자열."""
    import base64

    from winmate_common.client import ServiceClient

    try:
        data, mime = await ServiceClient("files").get_bytes(f"/v1/files/{file_id}/pages/{page}/image")
        res = await ai().vision(task, [{"data_b64": base64.b64encode(data).decode(), "mime": mime or "image/png"}],
                                "이 쪽의 글자를 그대로 받아쓴다. 표는 줄마다 칸을 ' | ' 로 나눈다.", confidential=True)
        return res.get("content") or ""
    except ApiError:
        return ""
