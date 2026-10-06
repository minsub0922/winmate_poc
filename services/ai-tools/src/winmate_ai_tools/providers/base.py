"""제공자 공통 형식 — 오케스트레이터(llm · i2t · t2i · websearch)가 만든 '제공자 호출'과 그 결과.

제공자는 API 요청을 직접 보지 않는다. 대체 경로(JSON 프롬프트 · ReAct · 잘라 붙이기 · 캔버스 확장)는
오케스트레이터가 처리하고, 제공자는 여기 정의된 호출만 실행한다.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from ..config import CapConfig
from ..errors import unsupported
from ..imaging import Img

NOTSET: Any = ...


@dataclass
class Msg:
    """시스템이 아닌 대화 메시지(이미지는 이미 불러와 Img 로)."""

    role: str                                   # user | assistant | tool
    parts: list[str | Img] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None

    def text(self) -> str:
        return "\n".join(p for p in self.parts if isinstance(p, str))

    def images(self) -> list[Img]:
        return [p for p in self.parts if isinstance(p, Img)]


@dataclass
class LLMCall:
    task: str
    system: str | None
    messages: list[Msg]
    temperature: float
    max_tokens: int
    json_schema: dict[str, Any] | None = None   # 제공자 고유 JSON 모드로 보낼 스키마(없으면 텍스트)
    schema_name: str = "Output"
    tools: list[dict[str, Any]] | None = None   # 제공자 고유 도구 호출로 보낼 도구
    tool_choice: str | None = None
    # mock 용 단서
    want_json: bool = False
    user_schema: dict[str, Any] | None = None
    react_tools: list[dict[str, Any]] | None = None


@dataclass
class LLMResult:
    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    model: str | None = None
    json_value: Any = NOTSET          # 이미 파싱한 값(mock)
    authoritative: bool = False       # mock 고정 응답: 수리 재시도 안 함
    boxes: list[dict[str, Any]] | None = None   # i2t: 이미 API 형식으로 바꾼 박스(mock)


@dataclass
class I2TCall:
    task: str
    images: list[Img]
    prompt: str
    system: str | None
    temperature: float
    max_tokens: int
    json_schema: dict[str, Any] | None = None
    schema_name: str = "Output"
    turns: list[tuple[str, str]] = field(default_factory=list)   # 수리용 추가 턴 (assistant|user, text)
    want_json: bool = False
    user_schema: dict[str, Any] | None = None
    want_bbox: bool = False
    user_prompt: str | None = None    # 박스 지시를 붙이기 전 원래 프롬프트(mock 용)


@dataclass
class Ref:
    img: Img
    role: str = "subject"
    strength: str = "mid"


@dataclass
class T2ICall:
    task: str
    prompt: str
    aspect: str                       # 제공자에 보낼 비율 문자열(지원 목록 안)
    ratio: float                      # 요청한 정확한 비율
    size: tuple[int, int]             # 목표 픽셀 크기(openai_compat · mock)
    n: int = 1
    refs: list[Ref] = field(default_factory=list)
    seed: int | None = None


@dataclass
class EditCall:
    task: str
    image: Img
    prompt: str
    aspect: str
    size: tuple[int, int]
    mask: Img | None = None           # L PNG(255=수정) — 고유 마스크를 지원하는 제공자에게만
    refs: list[Ref] = field(default_factory=list)
    n: int = 1


@dataclass
class GenImage:
    data: bytes
    mime: str = "image/png"


@dataclass
class T2IResult:
    images: list[GenImage]
    text: str = ""
    model: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class WebSearchCall:
    task: str
    query: str
    locale: str
    max_sources: int
    temperature: float
    max_tokens: int


@dataclass
class WebSearchResult:
    summary: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0})
    model: str | None = None


class Provider:
    """제공자 기본형. 지원하지 않는 기능은 501."""

    name = "base"
    native_mask = False   # 마스크 인페인팅을 직접 지원하는가(T2I_SUPPORTS_MASK=true 일 때만 쓴다)

    def available(self, cfg: CapConfig) -> bool:
        return True

    async def chat(self, cfg: CapConfig, call: LLMCall) -> LLMResult:
        raise unsupported("LLM_UNSUPPORTED", f"{self.name} 제공자는 LLM 을 지원하지 않습니다")

    async def stream(self, cfg: CapConfig, call: LLMCall) -> AsyncIterator[str | LLMResult]:
        """텍스트 조각(str)들을 내고 마지막에 LLMResult 하나. 기본: chat 결과를 한 번에."""
        res = await self.chat(cfg, call)
        if res.text:
            yield res.text
        yield res

    async def analyze(self, cfg: CapConfig, call: I2TCall) -> LLMResult:
        raise unsupported("I2T_UNSUPPORTED", f"{self.name} 제공자는 I2T 를 지원하지 않습니다")

    async def generate(self, cfg: CapConfig, call: T2ICall) -> T2IResult:
        raise unsupported("T2I_UNSUPPORTED", f"{self.name} 제공자는 이미지 생성을 지원하지 않습니다")

    async def edit(self, cfg: CapConfig, call: EditCall) -> T2IResult:
        raise unsupported("EDIT_UNSUPPORTED", f"{self.name} 제공자는 이미지 편집을 지원하지 않습니다")

    async def websearch(self, cfg: CapConfig, call: WebSearchCall) -> WebSearchResult:
        raise unsupported("WEBSEARCH_UNSUPPORTED", f"{self.name} 제공자는 웹 검색을 지원하지 않습니다")
