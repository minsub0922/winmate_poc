"""모델 호출 — ai-tools 경유(`winmate_common.ai.ai()`)만. task = `ds.<동작>.v1`.

- 고객 요구 · Storyboard 요약이 프롬프트에 들어가므로 항상 `confidential=True`.
- 출력은 입력 안의 키(요구 R1 · 후보 제품 P1 · 솔루션 카탈로그 id)로만 사실을 가리킨다 → 서비스가 되짚어 검증한다.
- 기밀 차단(403)은 그대로 올리고, 그 밖의 실패는 None(결정적 KB 대체 경로로).
- mock 고정 응답: mocks/ai-tools/ds.<동작>.v1.json
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field
from winmate_common.ai import ai
from winmate_common.errors import ApiError

log = logging.getLogger("winmate.dss.llm")

SYSTEM = (
    "너는 삼성전자 B2B 영업의 공간별 제품 매칭(DSS)을 돕는 어시스턴트다. 한국어로 답한다.\n"
    "규칙: (1) 입력에 없는 사실 · 수치 · 고객명 · 제품명 · 모델명을 지어내지 않는다. 제품은 입력 후보의 키(P1 …)로만, 솔루션은 입력 카탈로그 id 로만 가리킨다. "
    "(2) 수량은 요구 문장에 있는 수치일 때만 쓰고, 모르면 null. (3) 근거는 입력 요구의 키(R1 …)로 가리킨다. "
    "(4) 짧게, 화면 한 줄에 들어갈 문장으로. (5) 요청한 JSON 스키마만 돌려준다."
)


def dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, default=str)


async def try_call(task: str, prompt: str, schema: type[BaseModel], *, temperature: float = 0.2) -> dict[str, Any] | None:
    try:
        return await ai().json(task, prompt, schema, system=SYSTEM, confidential=True, temperature=temperature)
    except ApiError as exc:
        if exc.code == "POLICY_CONFIDENTIAL" or exc.status == 403:
            raise ApiError(403, "POLICY_CONFIDENTIAL", "고객 자료는 지금 설정된 모델로 보낼 수 없어요. 사내 모델 설정을 확인해 주세요.", exc.details) from exc
        log.warning("LLM %s 실패: %s %s", task, exc.code, exc.message)
        return None
    except Exception as exc:  # noqa: BLE001 — 스키마 검증 실패 · 네트워크 등
        log.warning("LLM %s 실패: %s", task, exc)
        return None


def mockish(s: Any) -> bool:
    return not isinstance(s, str) or not s.strip() or s.startswith("[mock") or "[mock]" in s


# ── 스키마 ─────────────────────────────────────────────

class IndustryOut(BaseModel):
    value: str = Field(description="업종 — 입력 '업종 선택지' 중 하나")
    basis: list[str] = Field(default_factory=list, description="근거 요구 키(R1 …)")
    quote: list[str] = Field(default_factory=list, description="근거 요구에서 그대로 옮긴 짧은 구절(20자 이내) 1~2개")
    alt: str | None = Field(None, description="애매하면 다른 후보 업종(선택지 중 하나), 아니면 null")


class SpaceOut(BaseModel):
    name: str = Field(description="공간 이름(로비 · 공용 회의실 …)")
    basis: list[str] = Field(default_factory=list, description="근거 요구 키(R1 …) — 요구에 없으면 빈 목록")
    why: str = Field(description="추천 이유 한 줄(요구 구절 · 업종 기본 공간)")
    ext: bool = Field(False, description="요구에는 없지만 업종상 흔한 확장 공간이면 true")


class ProductPickOut(BaseModel):
    space: str = Field(description="입력 공간 이름 그대로")
    cand: str = Field(description="입력 후보 제품 키(P1 …)")
    why: str = Field(description="이 공간에 쓰는 용도 한 줄(예: 방문객 셀프 등록)")
    basis: list[str] = Field(default_factory=list, description="근거 요구 키(R1 …)")
    qty: str | None = Field(None, description="요구 문장에 수치가 있을 때만(예: 2대), 없으면 null")


class IndustrySpacesOut(BaseModel):
    industry: IndustryOut | None = None
    spaces: list[SpaceOut] = Field(default_factory=list)
    products: list[ProductPickOut] = Field(default_factory=list)


class SolutionPickOut(BaseModel):
    id: str = Field(description="입력 솔루션 카탈로그 id")
    why: str = Field(description="추천 이유 한 줄(요구 구절 · 함께 쓰는 제품)")
    basis: list[str] = Field(default_factory=list, description="근거 요구 키(R1 …)")


class SolutionsOut(BaseModel):
    items: list[SolutionPickOut] = Field(default_factory=list)
