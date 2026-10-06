"""사내 제공자 자리(`<CAP>_PROVIDER=internal`) — 지금은 501 NOT_CONFIGURED.

사내망으로 옮길 때 여기만 채우면 된다(기능 서비스 · 오케스트레이터는 그대로).

1) 사내 API 가 OpenAI 호환이면 이 파일을 고칠 필요가 없다:
       LLM_PROVIDER=openai_compat  LLM_BASE_URL=http://<사내 LLM>/v1  LLM_API_KEY=…  LLM_MODEL=…
       I2T_PROVIDER=openai_compat  T2I_PROVIDER=openai_compat  (같은 방식)
   지원하지 않는 기능은 `LLM_SUPPORTS_JSON_SCHEMA=false` · `LLM_SUPPORTS_TOOLS=false` · `T2I_SUPPORTS_MASK=false` 처럼 끄면
   ai-tools 가 대체 경로(JSON 프롬프트 + 수리, ReAct, 잘라 붙이기)로 같은 응답 모양을 만든다.

2) 호환이 아니면 아래 메서드를 채운다. 입력 · 출력 형식은 providers/base.py 의 데이터클래스다.
   - chat(cfg, call: LLMCall) -> LLMResult
       call.system(시스템 지시) · call.messages(Msg: role user|assistant|tool, parts=[str | Img]) ·
       call.json_schema(제공자 JSON 모드에 넣을 스키마, None 이면 텍스트) · call.tools/tool_choice · temperature · max_tokens
       → LLMResult(text, tool_calls=[{id, name, arguments(dict)}], finish_reason, usage={input_tokens, output_tokens})
   - analyze(cfg, call: I2TCall) -> LLMResult      이미지(Img.data/mime) + prompt (+ turns: 수리용 추가 대화)
   - generate(cfg, call: T2ICall) -> T2IResult      prompt · aspect · size · n · refs(Ref.img/role/strength) → GenImage(bytes, mime)
   - edit(cfg, call: EditCall) -> T2IResult         image · prompt · mask(L PNG, 255=수정; native_mask=True 일 때만 옴) · refs
   - websearch(cfg, call: WebSearchCall) -> WebSearchResult   사내 검색 API 는 요약만 준다 → summary 만 채우고 sources=[]
   주소 · 키는 cfg.base_url · cfg.api_key(`<CAP>_BASE_URL` · `<CAP>_API_KEY`), 제한 시간은 cfg.timeout_s.
   HTTP 는 httpx.AsyncClient 로 부르고, 오류는 errors.provider_error(...) 로 바꿔 던진다(429 · 5xx 는 자동 재시도).
   테스트는 tests/test_openai_compat.py 처럼 respx 로 사내 API 응답을 흉내 낸다.
"""
from __future__ import annotations

from ..config import CapConfig
from ..errors import not_configured
from .base import EditCall, I2TCall, LLMCall, LLMResult, Provider, T2ICall, T2IResult, WebSearchCall, WebSearchResult


class InternalProvider(Provider):
    name = "internal"
    native_mask = False

    def available(self, cfg: CapConfig) -> bool:
        return False

    @staticmethod
    def _todo(cfg: CapConfig) -> Exception:
        return not_configured(
            f"사내 {cfg.cap} 제공자(internal)",
            capability=cfg.cap,
            hint="services/ai-tools/src/winmate_ai_tools/providers/internal.py 를 구현하거나, OpenAI 호환이면 "
                 f"{cfg.cap.upper()}_PROVIDER=openai_compat 로 설정하세요",
        )

    async def chat(self, cfg: CapConfig, call: LLMCall) -> LLMResult:
        raise self._todo(cfg)

    async def analyze(self, cfg: CapConfig, call: I2TCall) -> LLMResult:
        raise self._todo(cfg)

    async def generate(self, cfg: CapConfig, call: T2ICall) -> T2IResult:
        raise self._todo(cfg)

    async def edit(self, cfg: CapConfig, call: EditCall) -> T2IResult:
        raise self._todo(cfg)

    async def websearch(self, cfg: CapConfig, call: WebSearchCall) -> WebSearchResult:
        raise self._todo(cfg)
