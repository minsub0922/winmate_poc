"""모델 호출 — ai-tools 경유(`winmate_common.ai.ai()`)만. task 이름 = 스키마 이름(`vp.<동작>.v1`, 05-vp.md §7.6).

- 고객 자료(RFP · 견적 · 고객 사진 · 인터뷰 · 정의서 · Storyboard · MI 내용)가 프롬프트에 들어가므로 LLM · I2T 는 항상 `confidential=True`.
- 출력은 입력 안의 키(재료 키 · 수치 키 · 메시지 id)로만 사실을 가리킨다 → 서비스가 결정적으로 되짚고 검증한다(§7.7).
- 오류는 이 서비스 코드로: 403 POLICY_CONFIDENTIAL · 503 LLM_UNAVAILABLE · 504 LLM_TIMEOUT(한국어 메시지).
- mock 고정 응답: mocks/ai-tools/<task>.json (when.contains 로 입력에 따라 고른다).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, Field
from winmate_common.ai import ai
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.vp.llm")

SYSTEM = (
    "너는 삼성전자 B2B 영업의 가치 제안(Value Proposition) 시트를 돕는 어시스턴트다. 한국어로 답한다.\n"
    "규칙: (1) 입력에 없는 사실 · 수치 · 고객명 · 제품명 · 사례를 지어내지 않는다. 수치는 입력 수치의 키로만 가리키고, 모르면 [00](단위 유지), "
    "확인 전 문장은 [확인 필요]로 쓴다. (2) '최초' · '유일' · '1위' 같은 검증 안 된 주장을 만들지 않는다. (3) 경쟁사 이름을 쓰지 않는다. "
    "(4) 짧고 구체적으로, 제안서 시트에 바로 들어갈 문장으로 쓴다. (5) 요청한 JSON 스키마만 돌려준다."
)


def dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)


def map_error(exc: Exception) -> ApiError:
    if isinstance(exc, ApiError):
        if exc.code == "POLICY_CONFIDENTIAL" or exc.status == 403:
            return ApiError(403, "POLICY_CONFIDENTIAL", "고객 자료는 지금 설정된 모델로 보낼 수 없어요. 사내 모델 설정을 확인해 주세요.", exc.details)
        if exc.status == 504 or exc.code in ("TIMEOUT", "LLM_TIMEOUT"):
            return ApiError(504, "LLM_TIMEOUT", "AI 응답이 늦어져 멈췄어요. 잠시 후 다시 시도해 주세요.", exc.details)
        if exc.status in (413,):
            return ApiError(413, "CONTEXT_TOO_LONG", "자료가 너무 길어 한 번에 읽지 못했어요. 자료를 나눠 올려 주세요.", exc.details)
        if exc.status in (429, 500, 502, 503) or exc.code in ("UPSTREAM_UNAVAILABLE", "RATE_LIMITED", "PROVIDER_ERROR"):
            return ApiError(503, "LLM_UNAVAILABLE", "지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요.", {"upstream": exc.code})
        return exc
    return ApiError(503, "LLM_UNAVAILABLE", "지금은 AI를 쓸 수 없어요. 잠시 후 다시 시도해 주세요.", {"error": str(exc)[:200]})


async def call(task: str, prompt: str, schema: type[BaseModel], *, temperature: float | None = 0.2) -> dict[str, Any]:
    try:
        return await ai().json(task, prompt, schema, system=SYSTEM, confidential=True, temperature=temperature)
    except Exception as exc:  # noqa: BLE001
        err = map_error(exc)
        log.warning("LLM %s 실패: %s %s", task, err.code, err.message)
        raise err from exc


async def try_call(task: str, prompt: str, schema: type[BaseModel], **kw: Any) -> dict[str, Any] | None:
    """기밀 차단(403)은 그대로 올리고, 그 밖의 실패는 None(결정적 대체 경로로)."""
    try:
        return await call(task, prompt, schema, **kw)
    except ApiError as exc:
        if exc.code == "POLICY_CONFIDENTIAL":
            raise
        return None
    except Exception:  # noqa: BLE001 — 스키마 검증 실패 등
        return None


async def vision(task: str, images: list[Any], prompt: str, schema: type[BaseModel]) -> dict[str, Any] | None:
    try:
        res = await ai().vision(task, images, prompt, schema=schema, confidential=True)
        return res.get("json") or None
    except ApiError as exc:
        err = map_error(exc)
        if err.code == "POLICY_CONFIDENTIAL":
            raise err from exc
        log.warning("I2T %s 실패: %s", task, err.message)
        return None
    except Exception as exc:  # noqa: BLE001
        log.warning("I2T %s 실패: %s", task, exc)
        return None


# ── 스키마(§7.6) ───────────────────────────────────────────

class AttachmentKindOut(BaseModel):
    kind: Literal["rfp", "quote", "meeting_notes", "customer_photo", "other"]
    confidence: float = 0.5


class PageText(BaseModel):
    text: str = ""
    page: int | None = None
    quote: str | None = None


class Criterion(BaseModel):
    name: str
    points: int | None = None
    page: int | None = None


class DecisionMaker(BaseModel):
    role: str
    kpi: str | None = None
    page: int | None = None


class Mention(BaseModel):
    name: str
    page: int | None = None


class RfpExtract(BaseModel):
    customer: str | None = None
    challenges: list[PageText] = Field(default_factory=list)
    evaluation_criteria: list[Criterion] = Field(default_factory=list)
    decision_makers: list[DecisionMaker] = Field(default_factory=list)
    to_be: list[PageText] = Field(default_factory=list)
    competitor_mentions: list[Mention] = Field(default_factory=list)
    replacement: bool = False


class Money(BaseModel):
    value: float
    currency: str = "KRW"
    vat_included: bool | None = None


class QuoteItem(BaseModel):
    name: str
    qty: float | None = None
    amount: float | None = None


class QuoteExtract(BaseModel):
    version_label: str | None = None
    total_investment: Money | None = None
    items: list[QuoteItem] = Field(default_factory=list)
    page: int | None = None


class PageOcr(BaseModel):
    text: str = ""


class VisibleProduct(BaseModel):
    category: str
    confidence: float = 0.5


class PhotoClassify(BaseModel):
    space_type_guess: str = ""
    indoor_outdoor: Literal["indoor", "outdoor"] = "indoor"
    products_visible: list[VisibleProduct] = Field(default_factory=list)
    brand_visible: bool = False
    people_count: int = 0
    quality: Literal["ok", "low"] = "ok"


class SideValue(BaseModel):
    display: str = Field(description="'12초' · '3~5초' · '[00]시간' — 입력 수치 그대로, 모르면 [00]")
    status: Literal["secured", "estimated", "missing"] = "missing"
    source_label: str | None = None


class MetricOut(BaseModel):
    label: str
    before: SideValue | None = None
    after: SideValue | None = None


class MaterialOut(BaseModel):
    axis: Literal["challenge", "value", "evidence", "stakeholder", "product"]
    text: str = Field(description="짧은 재료 문장(시트 칩 한 줄)")
    source_tag: str = ""
    source_ref: str = Field(description="입력 후보 키(여러 개면 쉼표) — 키가 없는 재료는 만들지 않는다")
    locator: str | None = None
    number_ref: str | None = Field(None, description="수치는 입력 수치의 키로만")
    cost: bool | None = None
    approver: bool | None = None
    metric: MetricOut | None = None


class ExtractMaterials(BaseModel):
    title: str | None = Field(None, description="작업 주제 한 낱말(예: 메뉴보드)")
    items: list[MaterialOut] = Field(default_factory=list)


class MergeOut(BaseModel):
    item_ids: list[str]
    merged_text: str


class RewriteOut(BaseModel):
    item_ids: list[str]
    rewritten_text: str
    reason: str = ""


class ConflictOut(BaseModel):
    a_item_id: str
    b_item_id: str
    kind: Literal["priority", "contradiction"] = "priority"
    summary: str = ""


class ReconcileOut(BaseModel):
    merges: list[MergeOut] = Field(default_factory=list)
    rewrites: list[RewriteOut] = Field(default_factory=list)
    conflicts: list[ConflictOut] = Field(default_factory=list)


class ThemeOut(BaseModel):
    key: str
    label: str
    kind: Literal["gain", "cost"] = "gain"


class RelevanceOut(BaseModel):
    item_id: str
    theme_key: str
    value: float


class DirectionTags(BaseModel):
    themes: list[ThemeOut] = Field(default_factory=list)
    relevance: list[RelevanceOut] = Field(default_factory=list)
    summary: str | None = Field(None, description="'Storyboard는 …을, MI는 …를 가장 큰 과제로 봐요.' — 입력 근거에서만")


class DirectionOption(BaseModel):
    theme_key: str
    first_message: str
    products: list[str] = Field(default_factory=list)


class DirectionOptions(BaseModel):
    options: list[DirectionOption] = Field(default_factory=list)
    both: str | None = None


class KpiMatch(BaseModel):
    kpi_id: str
    metric_label: str
    before: float | None = None
    after: float | None = None
    unit: str = ""
    period: str | None = None


class KpiMetricExtract(BaseModel):
    matches: list[KpiMatch] = Field(default_factory=list)


class ChallengeOut(BaseModel):
    title: str
    body: str = ""
    impact_number_id: str | None = None


class PillarOut(BaseModel):
    title: str
    body: str = ""
    proof_ids: list[str] = Field(default_factory=list)
    product_ids: list[str] = Field(default_factory=list)
    km_ref: str | None = None


class OneLinerOut(BaseModel):
    statement: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)


class StakeholderOut(BaseModel):
    role: str
    kpi: str = ""
    value: str = ""
    product_ids: list[str] = Field(default_factory=list)


class PairOut(BaseModel):
    challenge: str
    product_id: str | None = None
    value: str = ""


class WriteSheet(BaseModel):
    title: str
    points: str = ""
    challenges: list[ChallengeOut] | None = None
    pillars: list[PillarOut] | None = None
    one_liner: OneLinerOut | None = None
    stakeholders: list[StakeholderOut] | None = None
    pairs: list[PairOut] | None = None
    metric_ids: list[str] | None = None
    qualitative: list[str] | None = None
    summary: str | None = None


class ShortenOut(BaseModel):
    text: str


class OpOut(BaseModel):
    op: Literal["rewrite_pillar", "set_pillars", "change_layout", "add_sheet", "move_to_notes", "set_metric", "tone",
                "image_request", "exclude_material", "add_note", "clarify"]
    sheet_role: str | None = None
    args: dict[str, Any] = Field(default_factory=dict)


class InterpretRequest(BaseModel):
    ops: list[OpOut] = Field(default_factory=list)
    needs_clarification: str | None = None
    reply: str | None = None


class LayoutOptionOut(BaseModel):
    key: Literal["A", "B", "C"]
    title: str
    desc_without_fit: str


class LayoutOptionsOut(BaseModel):
    intro: str = ""
    options: list[LayoutOptionOut] = Field(default_factory=list)


class ParsedAnswer(BaseModel):
    question_no: int
    keys: list[str] = Field(default_factory=list)


class ParseAnswer(BaseModel):
    answers: list[ParsedAnswer] = Field(default_factory=list)


class SideNumber(BaseModel):
    value: float
    unit: str = ""


class ParsedNumber(BaseModel):
    metric_label: str
    before: SideNumber | None = None
    after: SideNumber | None = None


class ParseNumbers(BaseModel):
    items: list[ParsedNumber] = Field(default_factory=list)
