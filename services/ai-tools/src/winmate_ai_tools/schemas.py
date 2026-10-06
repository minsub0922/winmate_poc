"""ai-tools API 요청 · 응답 모델 — `winmate_common.ai` 클라이언트가 보내고 받는 모양 그대로.

이 모델들이 contracts/ai-tools.json 이 되고, 기능 서비스의 ServiceClient 가 이 계약으로 요청·응답을 검증한다.
필드를 지우거나 타입을 바꾸면 깨지는 변경이다(추가는 괜찮다).
"""
from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ── 공통 ───────────────────────────────────────────────────


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class ImageRef(BaseModel):
    """이미지 하나: file_id(files 서비스) · url(http(s) 또는 data:) · data_b64(+mime) 중 하나."""

    file_id: str | None = None
    url: str | None = None
    data_b64: str | None = None
    mime: str | None = None

    @model_validator(mode="after")
    def _one_source(self) -> ImageRef:
        if not (self.file_id or self.url or self.data_b64):
            raise ValueError("file_id · url · data_b64 중 하나가 필요합니다")
        return self


# ── LLM ───────────────────────────────────────────────────


class TextPart(BaseModel):
    type: Literal["text"]
    text: str


class ImagePart(BaseModel):
    type: Literal["image"]
    file_id: str | None = None
    url: str | None = None
    data_b64: str | None = None
    mime: str | None = None

    @model_validator(mode="after")
    def _one_source(self) -> ImagePart:
        if not (self.file_id or self.url or self.data_b64):
            raise ValueError("이미지 조각에는 file_id · url · data_b64 중 하나가 필요합니다")
        return self


Part = Annotated[TextPart | ImagePart, Field(discriminator="type")]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[Part] = ""
    name: str | None = Field(default=None, description="tool 메시지: 호출된 도구 이름")
    tool_call_id: str | None = Field(default=None, description="tool 메시지: 어떤 tool_call 에 대한 결과인지")
    tool_calls: list[ToolCall] | None = Field(default=None, description="assistant 메시지: 앞서 받은 tool_calls 를 그대로")


class ToolSpec(BaseModel):
    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


class ChatRequest(BaseModel):
    task: str = Field(description="<기능 코드 소문자>.<동작> (예: rq.extract_form)")
    messages: list[ChatMessage] = Field(min_length=1)
    json_schema: dict[str, Any] | None = Field(default=None, description="이 JSON 스키마에 맞는 결과를 json 으로 받는다")
    schema_name: str | None = None
    tools: list[ToolSpec] | None = None
    tool_choice: str | None = Field(default=None, description="auto | none | required | <도구 이름>")
    temperature: float | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    confidential: bool = False


Fallback = Literal["none", "json_parse", "json_repair", "react"]


class ChatResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    call_id: str
    provider: str
    model: str
    content: str = ""
    json_: Any = Field(default=None, alias="json", description="json_schema 를 줬을 때 스키마에 맞는 값")
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str = "stop"
    usage: Usage = Field(default_factory=Usage)
    latency_ms: int = 0
    fallback: Fallback = "none"


# ── I2T ───────────────────────────────────────────────────


class I2TRequest(BaseModel):
    task: str
    images: list[ImageRef] = Field(min_length=1)
    prompt: str
    json_schema: dict[str, Any] | None = None
    want_bbox: bool = False
    confidential: bool = False
    max_tokens: int | None = Field(default=None, ge=1)


class Box(BaseModel):
    label: str
    box: list[float] = Field(min_length=4, max_length=4, description="[x0, y0, x1, y1] 0..1 정규화")
    score: float | None = None
    image_index: int = Field(default=0, description="몇 번째 입력 이미지의 박스인지(0부터)")


class I2TResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    call_id: str
    provider: str
    model: str
    content: str = ""
    json_: Any = Field(default=None, alias="json")
    boxes: list[Box] = Field(default_factory=list)
    usage: Usage = Field(default_factory=Usage)
    latency_ms: int = 0
    warnings: list[str] = Field(default_factory=list)
    fallback: Fallback = "none"


# ── T2I ───────────────────────────────────────────────────

RefRole = Literal["product", "style", "composition", "subject", "base"]
Strength = Literal["low", "mid", "high"]


class ReferenceImage(BaseModel):
    file_id: str | None = None
    url: str | None = None
    data_b64: str | None = None
    mime: str | None = None
    role: RefRole = "subject"
    strength: Strength = "mid"

    @model_validator(mode="after")
    def _one_source(self) -> ReferenceImage:
        if not (self.file_id or self.url or self.data_b64):
            raise ValueError("참조 이미지에는 file_id · url · data_b64 중 하나가 필요합니다")
        return self


class T2IGenerateRequest(BaseModel):
    task: str
    prompt: str
    negative_prompt: str | None = None
    aspect: str | None = Field(default=None, description='예: "16:9" "4:3" "1:1" "9:16" "21:9" (기본 T2I_DEFAULT_ASPECT)')
    n: int = Field(default=1, ge=1, le=4)
    reference_images: list[ReferenceImage] | None = None
    style: str | None = None
    seed: int | None = None
    confidential: bool = False
    metadata: dict[str, Any] | None = None


class MaskRef(BaseModel):
    """수정할 영역: 마스크 이미지(file_id · data_b64 · url; 흰색=수정, 알파가 있으면 투명=수정) 또는 box(0..1 정규화)."""

    file_id: str | None = None
    url: str | None = None
    data_b64: str | None = None
    mime: str | None = None
    box: list[float] | None = Field(default=None, min_length=4, max_length=4, description="[x0, y0, x1, y1] 0..1")

    @model_validator(mode="after")
    def _one_source(self) -> MaskRef:
        if not (self.file_id or self.url or self.data_b64 or self.box):
            raise ValueError("mask 에는 file_id · data_b64 · url · box 중 하나가 필요합니다")
        return self


class T2IEditRequest(BaseModel):
    task: str
    image: ImageRef
    prompt: str
    mask: MaskRef | None = None
    reference_images: list[ReferenceImage] | None = None
    aspect: str | None = Field(default=None, description="원본과 다르면 캔버스를 넓혀 바깥을 채운다(outpaint)")
    n: int = Field(default=1, ge=1, le=4)
    confidential: bool = False
    metadata: dict[str, Any] | None = None


class GeneratedImage(BaseModel):
    file_id: str
    width: int
    height: int
    mime: str


class T2IResponse(BaseModel):
    call_id: str
    provider: str
    model: str
    images: list[GeneratedImage] = Field(default_factory=list)
    fallbacks: list[str] = Field(default_factory=list, description="references_dropped · mask_crop_paste · outpaint_extend · edit_as_generate · aspect_cropped")
    warnings: list[str] = Field(default_factory=list)
    latency_ms: int = 0


# ── 웹 검색 · 검색 API · 수집 ──────────────────────────────


class WebSearchRequest(BaseModel):
    task: str
    query: str = Field(min_length=1)
    locale: str = "ko-KR"
    max_sources: int = Field(default=8, ge=0, le=50)
    confidential: bool = False


class Source(BaseModel):
    url: str
    title: str = ""
    snippet: str | None = None


class WebSearchResponse(BaseModel):
    call_id: str
    provider: str
    model: str
    summary: str = ""
    sources: list[Source] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    returned_sources: bool = False
    latency_ms: int = 0


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    locale: str = "ko-KR"
    limit: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""
    published_at: str | None = None


class SearchResponse(BaseModel):
    available: bool
    provider: str
    results: list[SearchResult] = Field(default_factory=list)


class FetchRequest(BaseModel):
    url: str = Field(min_length=1)
    max_chars: int = Field(default=20000, ge=1, le=500000)


class FetchResponse(BaseModel):
    url: str
    final_url: str | None = None
    status: int = 0
    allowed: bool = True
    reason: str | None = Field(default=None, description="disabled · invalid_url · domain_not_allowed · robots_disallow · http_error · unsupported_content_type …")
    title: str = ""
    text: str = ""
    published_at: str | None = None
    fetched_at: str
    from_cache: bool = False
    content_type: str | None = None
    content_hash: str | None = Field(default=None, description="본문 텍스트 sha256")
    truncated: bool = False
    pages: list[str] | None = Field(default=None, description="PDF 면 페이지별 텍스트")


# ── 임베딩 ─────────────────────────────────────────────────


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=1024)
    kind: Literal["query", "passage"] = "passage"


class EmbedResponse(BaseModel):
    provider: str
    model: str
    dim: int
    vectors: list[list[float]]


# ── 기능 · 사용량 · 호출 로그 ──────────────────────────────


class LLMSupports(BaseModel):
    json_schema: bool
    tools: bool
    streaming: bool


class LLMCaps(BaseModel):
    provider: str
    model: str
    max_input_tokens: int
    max_output_tokens: int
    supports: LLMSupports
    allow_confidential: bool
    available: bool = True


class I2TSupports(BaseModel):
    json_schema: bool
    bbox: bool


class I2TCaps(BaseModel):
    provider: str
    model: str
    max_images_per_call: int
    max_image_side_px: int
    supports: I2TSupports
    allow_confidential: bool
    available: bool = True


class T2ISupports(BaseModel):
    reference_images: bool
    edit: bool
    mask: bool


class T2ICaps(BaseModel):
    provider: str
    model: str
    max_side_px: int
    default_aspect: str
    max_reference_images: int
    images_per_call: int
    supports: T2ISupports
    allow_confidential: bool
    available: bool = True


class WebSearchCaps(BaseModel):
    provider: str
    model: str
    return_sources: bool
    allow_confidential: bool
    available: bool = True


class SearchApiCaps(BaseModel):
    provider: str
    available: bool


class FetchCaps(BaseModel):
    enabled: bool


class EmbeddingCaps(BaseModel):
    provider: str
    model: str
    available: bool
    dim: int | None = None


class UsageToday(BaseModel):
    llm: int = 0
    i2t: int = 0
    t2i: int = 0
    websearch: int = 0


class CapLimits(BaseModel):
    rpm: int = Field(description="분당 호출 수(0 = 제한 없음)")
    daily: int = Field(description="하루 한도(0 = 제한 없음). t2i 는 이미지 장수 기준")
    max_concurrency: int
    timeout_s: float


class Limits(BaseModel):
    enforced: bool = Field(description="live · record 모드에서만 한도를 적용한다")
    llm: CapLimits
    i2t: CapLimits
    t2i: CapLimits
    websearch: CapLimits


class Capabilities(BaseModel):
    mode: str
    llm: LLMCaps
    i2t: I2TCaps
    t2i: T2ICaps
    websearch: WebSearchCaps
    search_api: SearchApiCaps
    fetch: FetchCaps
    embedding: EmbeddingCaps
    usage_today: UsageToday
    limits: Limits


class CapUsage(BaseModel):
    today: int
    daily_limit: int
    remaining: int | None = Field(description="daily_limit 이 0(무제한)이면 null")
    this_minute: int
    rpm: int


class UsageResponse(BaseModel):
    date: str
    mode: str
    enforced: bool
    usage: dict[str, CapUsage]


class CallRecord(BaseModel):
    id: str
    ts: str
    capability: str
    task: str | None = None
    provider: str | None = None
    model: str | None = None
    mode: str
    status: Literal["ok", "error", "canceled"]
    latency_ms: int = 0
    usage: Usage = Field(default_factory=Usage)
    caller: str | None = Field(default=None, description="호출한 서비스(X-Caller-Service)")
    request_id: str | None = None
    user_id: str | None = None
    confidential: bool = False
    fallback: str | None = None
    cassette: str | None = Field(default=None, description="replay_hit · replay_miss · recorded")
    attempts: int = 0
    error: dict[str, Any] | None = None
    request: Any = None
    response: Any = None


class CallList(BaseModel):
    items: list[CallRecord]
    next_cursor: str | None = None
