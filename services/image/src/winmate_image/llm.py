"""모델 호출(ai-tools 경유, task = `img.<동작>`) — 스키마 · 제한 시간 · 일시 오류 재시도 · 오류 구분.

- 고객 자료(업로드 · 현장 · 고객 사례 사진, 프로젝트 고객 정보가 든 프롬프트)는 `confidential=True`.
- 403 `POLICY_CONFIDENTIAL` → `ModelBlocked`(호출한 쪽이 §7.2 로컬 대체 경로로 내려간다. 다른 모델로 몰래 바꾸지 않는다).
- `DAILY_LIMIT_EXCEEDED` · `QUOTA_EXCEEDED` → `QuotaExceeded`(재시도하지 않음).
- 502 · 503 · 504 · 429 `RATE_LIMITED` · 연결 오류 → 2번 다시(2초, 6초 — IMAGE_RETRY_DELAYS).
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, Field

from winmate_common.ai import ai
from winmate_common.errors import ApiError

from . import config

log = logging.getLogger("winmate.image.llm")
T = TypeVar("T")


class ModelBlocked(Exception):
    """ai-tools 가 기밀 전송을 막았다(403 POLICY_CONFIDENTIAL)."""


class QuotaExceeded(Exception):
    def __init__(self, message: str = "오늘 쓸 수 있는 이미지 생성 횟수를 다 썼어요"):
        super().__init__(message)
        self.message = message


class ModelFailed(Exception):
    def __init__(self, code: str, message: str, status: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


TRANSIENT = {502, 503, 504}


def classify(exc: Exception) -> Exception:
    if isinstance(exc, ApiError):
        if exc.code == "POLICY_CONFIDENTIAL" or (exc.status == 403 and "CONFIDENTIAL" in exc.code):
            return ModelBlocked(exc.message)
        if exc.code in ("DAILY_LIMIT_EXCEEDED", "QUOTA_EXCEEDED"):
            return QuotaExceeded()
        return ModelFailed(exc.code, exc.message, exc.status)
    return exc


def _transient(exc: Exception) -> bool:
    if isinstance(exc, ApiError):
        return exc.status in TRANSIENT or exc.code == "RATE_LIMITED"
    return isinstance(exc, (OSError, asyncio.TimeoutError)) or type(exc).__name__ in ("ConnectError", "ReadTimeout", "RemoteProtocolError")


async def call(fn: Callable[[], Awaitable[T]], *, retries: bool = True) -> T:
    delays = config.retry_delays() if retries else []
    attempt = 0
    while True:
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001
            if _transient(exc) and attempt < len(delays):
                await asyncio.sleep(delays[attempt])
                attempt += 1
                continue
            raise classify(exc) from exc


async def json_task(task: str, prompt: str, schema: type[BaseModel], *, system: str | None = None, confidential: bool = False,
                    timeout: float | None = None) -> dict[str, Any] | None:
    """LLM JSON — 실패(시간 초과 · 스키마 · 제공자)면 None. 기밀 차단은 ModelBlocked 로 올린다."""
    async def run() -> dict[str, Any]:
        return await ai().json(task, prompt, schema, system=system, confidential=confidential)

    try:
        if timeout:
            return await asyncio.wait_for(call(run), timeout)
        return await call(run)
    except ModelBlocked:
        raise
    except QuotaExceeded:
        return None
    except Exception as exc:  # noqa: BLE001
        log.info("%s 실패: %s", task, exc)
        return None


async def vision_task(task: str, images: list[Any], prompt: str, schema: type[BaseModel], *, want_bbox: bool = False,
                      confidential: bool = False, timeout: float | None = None) -> dict[str, Any] | None:
    """I2T JSON(+박스) → {json, boxes, model, provider} 또는 None(JSON 실패). 기밀 차단은 ModelBlocked."""
    async def run() -> dict[str, Any]:
        return await ai().vision(task, images, prompt, schema=schema, want_bbox=want_bbox, confidential=confidential)

    try:
        res = await (asyncio.wait_for(call(run), timeout) if timeout else call(run))
    except ModelBlocked:
        raise
    except Exception as exc:  # noqa: BLE001
        log.info("%s 실패: %s", task, exc)
        return None
    data = res.get("json")
    if not isinstance(data, dict):
        return None
    try:
        data = schema.model_validate(data).model_dump()
    except Exception:  # noqa: BLE001
        return None
    return {"json": data, "boxes": res.get("boxes") or [], "model": res.get("model"), "provider": res.get("provider")}


# ── 스키마 ───────────────────────────────────────────────

class Mention(BaseModel):
    mention: str = Field(description="장면 설명에 나온 삼성 제품 · 모델명(원문 그대로, 예 QM55C · 메뉴보드)")
    qty: int = Field(1, ge=1, le=9, description="수량(“3연” → 3)")


class PrefillOut(BaseModel):
    title: str = Field(description="작업 제목(24자 이내, 유형 접미사 포함: 공간 「… 시안」 · 배경 「… 배경 이미지」 · 시나리오 「… 시나리오 컷」)")
    subject_short: str = Field(description="파일명용 주제 6자 이내(예 메뉴보드)")
    customer_name: str | None = Field(None, description="설명에 고객사가 있으면 그대로(없으면 null, 지어내지 않음)")
    products: list[Mention] = Field(default_factory=list)
    search_query: str = Field(description="참조 이미지 검색어(예 카페 메뉴보드)")
    industry: str | None = Field(None, description="업종(Winmate 16 업종 이름 중 하나, 예 외식 · 카페)")
    space_label: str | None = Field(None, description="공간 이름(예 카운터)")
    kind_suggestion: Literal["space", "background", "scenario"] | None = None


class NamedThing(BaseModel):
    name: str
    span: str | None = Field(None, description="원문에서 그 부분")


class PolicyOut(BaseModel):
    competitors: list[NamedThing] = Field(default_factory=list, description="삼성 외 회사 · 브랜드 · 로고 · 제품(“경쟁사 A” 같은 일반 표현 포함)")
    real_persons: list[NamedThing] = Field(default_factory=list, description="실존 인물(연예인 · 공인 · 특정 개인). name 은 “배우 ○○○” 처럼 역할 포함")
    unsafe: list[str] = Field(default_factory=list)


class ComposeShot(BaseModel):
    angle_ko: str = Field(description="시안별 구도 요약(카메라 높이 · 각도 · 시간대)")
    prompt_en: str = Field(description="최종 영문 프롬프트")


class ComposeOut(BaseModel):
    prompt_ko: str = Field(description="한국어 장면 요약")
    shots: list[ComposeShot]


class CustomAltOut(BaseModel):
    issue_type: Literal["competitor_brand", "real_person", "product_unrecognized", "none"]
    option_text: str = Field(description="대안 문장(짧게)")
    safe: bool = Field(description="대안이 정책(다른 회사 로고 · 실존 인물 · 삼성 외 제품 외형 금지)을 지키는가")


class EditIntentOut(BaseModel):
    action: Literal["region_edit", "global_edit", "variants", "ask"]
    instruction_ko: str
    instruction_en: str = ""
    region_hint: str | None = Field(None, description="바꿀 곳(예 가운데 메뉴보드 화면)")
    target_kind: Literal["screen", "text", "person", "object", "none"] = "none"
    question: str | None = None


class VariantItem(BaseModel):
    label: str = Field(description="8자 이내 변형 이름(예 오후 자연광)")
    instruction_en: str


class VariantPlanOut(BaseModel):
    variants: list[VariantItem]


class VariantRequestOut(BaseModel):
    action: Literal["aspect_instruction", "variants", "ask"]
    aspect: Literal["16:9", "4:3", "1:1", "9:16"] | None = None
    instruction: str = ""
    question: str | None = None


class ExportRequestOut(BaseModel):
    caption: bool = False
    english_filename: bool = False
    include_original: bool = False
    format: Literal["png", "jpg", "pdf", "pptx"] | None = None
    ai_label: bool | None = None
    other_drafts: bool = False
    question: str | None = None


class CaptionOut(BaseModel):
    caption: str


class FilenameOut(BaseModel):
    customer_en: str | None = None
    subject_en: str
    label_en: str


class ScreenContentOut(BaseModel):
    content_ko: str
    content_en: str


class DisplayGuess(BaseModel):
    box: list[float] | None = None
    visual_category: str | None = None
    size_hint: str | None = None
    model_guess: str | None = None
    confidence: float = 0.0


class RefAnalyzeOut(BaseModel):
    faces: list[list[float]] = Field(default_factory=list)
    logos: list[list[float]] = Field(default_factory=list)
    displays: list[DisplayGuess] = Field(default_factory=list)
    style: Literal["photo", "illustration"] = "photo"
    caption: str = ""
    color_light: str = ""
    composition: str = ""
    placement: str = ""
    material: str = ""


class QcProduct(BaseModel):
    box: list[float] | None = None
    kind: str = "display"


class QcOut(BaseModel):
    product_count: int = 0
    products: list[QcProduct] = Field(default_factory=list)
    logo_visible: bool = False
    brand_text: bool = False
    identifiable_faces: int = 0
    gibberish_text: bool = False
    notes: str = ""


class PhotoSurface(BaseModel):
    label: str
    kind: Literal["wall", "counter", "ceiling", "floor", "other"] = "wall"
    quad: list[list[float]] | None = None
    bbox: list[float] | None = None
    installable: bool = True


class PhotoObject(BaseModel):
    label: str
    bbox: list[float] | None = None


class PhotoOut(BaseModel):
    label: str = Field(description="사진 위치 이름(예 카운터 벽면 · 매장 안쪽)")
    surfaces: list[PhotoSurface] = Field(default_factory=list)
    objects: list[PhotoObject] = Field(default_factory=list)
    floor_line: float | None = None


class DetectItem(BaseModel):
    kind: Literal["object", "text", "person", "screen"]
    label: str
    box: list[float] | None = None


class DetectOut(BaseModel):
    items: list[DetectItem] = Field(default_factory=list)


class RegionNameOut(BaseModel):
    name: str = Field(description="“위치어 + 명사” 12자 이내(예 가운데 메뉴보드 화면)")


# ── 프롬프트 ─────────────────────────────────────────────

SYSTEM_KO = ("너는 삼성 B2B 제안서용 이미지 생성 도우미다. 사실(스펙 · 수치 · 모델명 · 고객명)을 지어내지 않는다. "
             "모르면 null 이나 빈 목록을 쓴다. 답은 JSON 스키마 그대로.")


def prefill_prompt(kind: str, description: str) -> str:
    return (f"이미지 유형: {kind}\n장면 설명: {description}\n\n"
            "장면에 나오는 삼성 제품(모델명 · 제품 이름)과 수량을 뽑고(“3연” = 3대), 작업 제목 · 파일명용 주제 · 참조 이미지 검색어 · 업종 · 공간을 정하라.")


def policy_prompt(text: str) -> str:
    return ("다음 이미지 요청에서 (1) 삼성 외 회사 · 브랜드 · 로고 · 제품(‘경쟁사 A’ 같은 일반 표현 포함), (2) 실존 인물(연예인 · 공인 · 특정 개인), "
            f"(3) 그 밖에 만들면 안 되는 요소를 찾아라.\n\n요청: {text}")


def compose_prompt(*, kind: str, description: str, n: int, products: str, style: str, extras: list[str]) -> str:
    lines = [f"유형: {kind}", f"장면 설명: {description}", f"제품: {products or '없음'}", f"스타일: {style}",
             f"시안 {n}장의 구도를 서로 겹치지 않게(카메라 높이 · 각도 · 시간대) 정하고, 시안마다 영문 최종 프롬프트를 써라."]
    lines += extras
    return "\n".join(lines)
