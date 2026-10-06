"""모델 호출 — ai-tools 만 거친다(`winmate_common.ai.ai()`), task 이름 `rq.<동작>`, 고객 자료라 항상 confidential=True.

오류 대응(§4.0.5 · §6.10)
- 403 POLICY_CONFIDENTIAL → 그대로(한국어 메시지). 다른 모델로 몰래 바꾸지 않는다.
- 429 · 5xx · 연결 실패 · 잘못된 출력 → 503 LLM_UNAVAILABLE
- 시간 초과 → 504 LLM_TIMEOUT
호출하는 쪽이 대체 경로(템플릿 · 규칙)를 정한다.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError
from winmate_common.ai import ai
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.requirements.llm")

AI_UNAVAILABLE_MSG = "지금은 AI를 쓸 수 없어요. 직접 입력은 계속할 수 있어요."
CONFIDENTIAL_MSG = "기밀 자료라 지금 AI에 보낼 수 없어요. 직접 입력은 계속할 수 있어요."
TIMEOUT_MSG = "AI 응답이 늦어요. 잠시 뒤 다시 시도해 주세요."

SYSTEM = """너는 삼성 B2B 영업 담당자를 돕는 요구사항 정리 도우미다.
규칙:
- 한국어로 답한다.
- 고객 원문에 없는 사실 · 수치 · 고객명 · 모델명을 지어내지 않는다. 모르면 비워 둔다.
- 원문에 없는 숫자를 쓰지 않는다.
- 고객의 요구와 제작자(삼성 영업)의 내부 목표(스펙인 · 수주 · 매출 목표 · 강조 전략)를 구분한다. 내부 목표는 고객 요구 항목이 아니다.
- 칸 · 문장 길이 상한을 지킨다.
- 반드시 주어진 JSON 스키마로만 답한다."""


class LlmError(ApiError):
    pass


def _map_error(exc: BaseException) -> ApiError:
    if isinstance(exc, ApiError):
        if exc.code == "POLICY_CONFIDENTIAL" or exc.status == 403:
            return ApiError(403, "POLICY_CONFIDENTIAL", CONFIDENTIAL_MSG, {"upstream": exc.code})
        if exc.status == 504 or exc.code in ("TIMEOUT", "LLM_TIMEOUT"):
            return ApiError(504, "LLM_TIMEOUT", TIMEOUT_MSG, {"upstream": exc.code})
        return ApiError(503, "LLM_UNAVAILABLE", AI_UNAVAILABLE_MSG, {"upstream": exc.code, "status": exc.status})
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, httpx.TimeoutException)):
        return ApiError(504, "LLM_TIMEOUT", TIMEOUT_MSG)
    return ApiError(503, "LLM_UNAVAILABLE", AI_UNAVAILABLE_MSG, {"error": type(exc).__name__})


async def call_json(task: str, prompt: str, schema: type[BaseModel], *, timeout: float = 120.0,
                    temperature: float | None = 0.2) -> dict[str, Any]:
    """JSON 스키마 응답. 실패는 ApiError(POLICY_CONFIDENTIAL | LLM_UNAVAILABLE | LLM_TIMEOUT)."""
    try:
        return await asyncio.wait_for(
            ai().json(task, prompt, schema, system=SYSTEM, confidential=True, temperature=temperature), timeout)
    except ValidationError as exc:
        log.warning("%s: 출력 형식 오류 %s", task, exc.errors()[:3])
        raise ApiError(503, "LLM_UNAVAILABLE", AI_UNAVAILABLE_MSG, {"reason": "bad_output"}) from exc
    except (ApiError, asyncio.TimeoutError, TimeoutError, httpx.HTTPError) as exc:
        raise _map_error(exc) from exc


async def call_vision(task: str, file_ids: list[str], prompt: str, *, timeout: float = 90.0) -> str:
    try:
        res = await asyncio.wait_for(ai().vision(task, list(file_ids), prompt, confidential=True), timeout)
        return (res.get("content") or "").strip()
    except (ApiError, asyncio.TimeoutError, TimeoutError, httpx.HTTPError) as exc:
        raise _map_error(exc) from exc


# ── 출력 스키마(§7.7) ────────────────────────────────────

class RqDocKind(BaseModel):
    doc_kind: Literal["rfp", "meeting_memo", "mail", "other"]
    language: str = "ko"


class PlanSlot(BaseModel):
    kind: Literal["field", "keyman", "item", "author_note"]
    hint: str = ""


class RqPlan(BaseModel):
    slots: list[PlanSlot] = Field(default_factory=list)


class Quoted(BaseModel):
    value: str | None = None
    quote: str | None = None
    locator: str | None = None


class QuotedText(BaseModel):
    text: str
    quote: str | None = None
    locator: str | None = None


class ExtractedKeyman(BaseModel):
    name: str = Field(description="키맨 직함 또는 이름(예: 대표이사)")
    aliases: list[str] = Field(default_factory=list)
    items: list[QuotedText] = Field(default_factory=list)


class ExtractedContext(BaseModel):
    scale_text: str | None = None
    deadline_text: str | None = None


class RqExtraction(BaseModel):
    project_name: Quoted | None = None
    customer_name: Quoted | None = None
    final_audience: Quoted | None = Field(None, description="문서에 명시된 경우만")
    author_notes: list[QuotedText] = Field(default_factory=list, description="영업 목표 · 내부 전략 문장")
    keymen: list[ExtractedKeyman] = Field(default_factory=list)
    context: ExtractedContext | None = None
    decision_bodies: list[str] = Field(default_factory=list, description="문서에 나온 의사결정 주체(예: 투자심의위원회)")


class ShortItem(BaseModel):
    code: str | None = None
    text: str
    short: str = Field(max_length=40)


class RqShort(BaseModel):
    items: list[ShortItem] = Field(default_factory=list)
    short_title: str | None = None


class GapTargetOut(BaseModel):
    kind: Literal["item", "keyman"]
    keyman_name: str | None = None
    item_text: str | None = None


class GapOut(BaseModel):
    target: GapTargetOut
    kind: Literal["unquantified", "vague_scope", "ambiguous", "missing_perspective", "conflict"]
    problem: str
    impact: int = Field(2, ge=1, le=3)
    why: str | None = None


class RqGaps(BaseModel):
    gaps: list[GapOut] = Field(default_factory=list)


class OptionWeight(BaseModel):
    keyman_name: str
    weight: int


class QuestionOption(BaseModel):
    label: str
    weights: list[OptionWeight] | None = None


class QuestionOut(BaseModel):
    gap_no: int
    target_label: str | None = None
    text: str
    options: list[QuestionOption] = Field(default_factory=list)
    short_label: str | None = None


class RqQuestions(BaseModel):
    questions: list[QuestionOut] = Field(default_factory=list)


class SideEffectOut(BaseModel):
    label: str
    question_text: str
    keyman_name: str | None = None


class RqRewrite(BaseModel):
    kind: Literal["replace_item", "add_item", "set_field"]
    after_text: str
    after_short: str | None = None
    side_effects: list[SideEffectOut] = Field(default_factory=list)


class RqCustomerQuestion(BaseModel):
    text: str
    short_label: str
    keyman_name: str | None = None


class ReplyMatchOut(BaseModel):
    question_no: int | None = None
    question_text: str | None = None
    reply_span: str | None = None
    answered: bool = False


class RqReplyMatch(BaseModel):
    matches: list[ReplyMatchOut] = Field(default_factory=list)


class ReplyTargetOut(BaseModel):
    kind: Literal["item", "field", "keyman", "weights", "evidence", "new_item"]
    keyman_name: str | None = None
    item_text: str | None = None
    field: str | None = None


class ReplyChangeOut(BaseModel):
    target: ReplyTargetOut
    label: str
    before_display: str | None = None
    after_display: str
    new_text: str | None = Field(None, description="항목 · 칸에 실제로 쓸 문장(없으면 after_display)")
    resolves_question_texts: list[str] = Field(default_factory=list)
    evidence_file_names: list[str] = Field(default_factory=list)
    weights: list[OptionWeight] | None = None


class RqReplyChanges(BaseModel):
    changes: list[ReplyChangeOut] = Field(default_factory=list)
    version_note: str | None = None


class RqMailDraft(BaseModel):
    subject: str
    body: str
