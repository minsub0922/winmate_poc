# ai-tools — 외부 모델 호출의 유일한 통로

LLM · I2T(이미지 → 글) · T2I(이미지 생성 · 편집) · 요약형 웹 검색 · 검색 API · 웹 수집 · 임베딩을 한곳에서 부른다.
기능 서비스는 `winmate_common.ai.ai()` 로만 부르고, 제공자는 `.env` 로 고른다(개발: Gemini 최저 등급, 사내망: 사내 API).

```python
from winmate_common.ai import ai
data = await ai().json("rq.extract_form", prompt, schema=Form, confidential=True)
img  = await ai().generate_image("img.generate", prompt, aspect="16:9", n=2)
```

## 1. API (`/api/ai-tools/v1/...`)

| 메서드 · 경로 | 하는 일 | 게이트웨이 |
|---|---|---|
| `GET /capabilities` | 모드 · 기능별 제공자/모델 · 지원 여부 · 한도 · 오늘 사용량 | 웹도 읽음 |
| `GET /usage` | 오늘 사용량 대 한도 | 웹도 읽음 |
| `POST /llm/chat` | 대화 · JSON 스키마 · 도구 호출 | 서비스 전용(`internal`) |
| `POST /llm/stream` | SSE `delta {text}` … `done {content, usage, call_id}` (오류는 `error`) | 서비스 전용 |
| `POST /i2t/analyze` | 이미지 → 글 · JSON · 박스(`[x0,y0,x1,y1]` 0..1) | 서비스 전용 |
| `POST /t2i/generate` | 이미지 생성 → files 저장(`source=generated`, 메타 `ai_generated`) | 서비스 전용 |
| `POST /t2i/edit` | 편집(마스크 · 바깥 채우기 · 참조) → files 저장 | 서비스 전용 |
| `POST /websearch` | 요약형 웹 검색(사내 검색 API 흉내 — 기본 출처 숨김) | 서비스 전용 |
| `POST /search` | 검색 API(원문 URL 목록) | 서비스 전용 |
| `POST /fetch` | 웹 페이지 수집(robots · 속도 제한 · 캐시 · PDF 페이지) | 서비스 전용 |
| `POST /embed` | 임베딩 | 서비스 전용 |
| `GET /calls` · `GET /calls/{id}` | 호출 로그(요청 · 응답 본문 포함 가능) | 서비스 전용 |

요청 · 응답 모양은 `contracts/ai-tools.json`(코드: `src/winmate_ai_tools/schemas.py`). task 이름은 `<기능 코드>.<동작>` — 호출 로그 ·
카세트 · mock 고정 응답의 키다.

## 2. 제공자 매트릭스

| 기능 | gemini | openai_compat | internal | mock |
|---|---|---|---|---|
| LLM | generate_content · JSON 스키마(부분 집합으로 다듬음) · 함수 호출(thought signature 왕복) · 스트리밍 · thinking_level | chat.completions · response_format json_schema(strict 가능하면) · tools · 스트리밍 | 501(자리) | 고정 응답 · 스키마 가짜 값 · `[mock:<task>] …` |
| I2T | inline 이미지 + JSON · 박스(0–1000 yxyx) | image_url(data URI) | 501 | 가짜 값 · 박스 2개 |
| T2I 생성 | 이미지 출력 · aspect_ratio · 참조 이미지(inline) | images.generate(b64) · 참조가 있으면 images.edit | 501 | Pillow 그라데이션 PNG(정확한 비율) |
| T2I 편집 | 이미지 + 지시(마스크 없음 → 잘라 붙이기) | images.edit(+mask: 투명=수정) | 501 | 색 반전 + 지시문 |
| 웹 검색 | `google_search` grounding(요약 · 출처 · 검색어) | chat 요약(+url_citation) | 501(사내 요약 API 자리) | 질의를 담은 요약 + example.com 출처 |
| 임베딩 | — | /embeddings | 501 | 글자 n-gram 해시 벡터 |

- `<CAP>_PROVIDER` 는 기능마다 따로: `LLM_PROVIDER` · `I2T_PROVIDER` · `T2I_PROVIDER` · `WEBSEARCH_PROVIDER`(`gemini_grounding` = gemini).
- `MODEL_MODE=mock` 이면 설정된 제공자와 상관없이 mock 이 답한다(지원 여부 · 정책 · 대체 경로는 설정 그대로 적용 →
  기능 서비스가 사내망과 같은 분기를 탄다).

## 3. 모드 · 카세트

| MODEL_MODE | 동작 | 한도(Redis) |
|---|---|---|
| `live` | 제공자 호출 | 적용 |
| `mock` | 네트워크 없이 결정적 응답(`mocks/ai-tools/<task>.json` → 없으면 가짜 값) | 없음(Redis 안 씀) |
| `record` | live + 카세트 저장 | 적용 |
| `replay` | 카세트만. 없으면 404 `CASSETTE_MISS`(단 `REPLAY_FALLBACK=mock` 이면 mock) | 없음 |

카세트: `MODEL_CASSETTE_DIR/<기능>/<task>/<sha256(정규화 요청)>.json` (t2i 이미지는 옆에 `<키>.<n>.png`).
정규화 요청 = 결과에 영향을 주는 값만(기밀 표시 · metadata 제외), **이미지는 file_id 대신 내용 해시**, tool_call id 는 순번,
제공자 · 모델은 키에 넣지 않는다 → 맥과 사내망의 files id · 모델이 달라도 같은 입력이면 같은 키.

**맥 → 사내망 회귀 비교**
1. 맥: `MODEL_MODE=record` 로 기능 흐름(또는 기능 서비스 테스트 · `live_check.py`)을 돌려 `data/cassettes/` 를 채운다.
2. 폴더째 사내망으로 옮긴다.
3. 사내망 결정적 회귀: `MODEL_MODE=replay`(필요하면 `REPLAY_FALLBACK=mock`) — 모델 없이 맥에서 받은 답으로 기능 서비스 결과를 비교.
   재생한 t2i 이미지는 사내 files 에 새로 저장되고 새 file_id 를 받는다.
4. 사내 모델 품질 비교: `MODEL_MODE=record MODEL_CASSETTE_DIR=./data/cassettes-intranet` 으로 같은 흐름을 돌린 뒤
   `uv run python services/ai-tools/scripts/cassette_compare.py data/cassettes data/cassettes-intranet`.

## 4. 환경 변수(기본값 = `.env.example`)

| 묶음 | 키 |
|---|---|
| 공통 | `MODEL_MODE=live` · `MODEL_CASSETTE_DIR=./data/cassettes` · `REPLAY_FALLBACK=`(mock) · `MODEL_CALL_LOG=full`(full · meta · off) · `MODEL_CALL_LOG_RETENTION_DAYS=30` · `CACHE_DIR=./data/cache` |
| Gemini | `GEMINI_API_KEY` · `GEMINI_BASE_URL=https://generativelanguage.googleapis.com` · `GEMINI_THINKING_LEVEL=low`(minimal · low · medium · high, 비우면 안 보냄) |
| LLM | `LLM_PROVIDER=gemini` · `LLM_BASE_URL` · `LLM_API_KEY` · `LLM_MODEL=gemini-3.1-flash-lite` · `LLM_MAX_INPUT_TOKENS=32000` · `LLM_MAX_OUTPUT_TOKENS=4096` · `LLM_TEMPERATURE=0.2` · `LLM_SUPPORTS_JSON_SCHEMA/TOOLS/STREAMING=true` · `LLM_TIMEOUT_S=90` · `LLM_MAX_CONCURRENCY=4` · `LLM_RPM=30` · `LLM_DAILY_LIMIT=2000` |
| I2T | `I2T_PROVIDER=gemini` · `I2T_MODEL=gemini-3.1-flash-lite` · `I2T_MAX_IMAGES_PER_CALL=4` · `I2T_MAX_IMAGE_SIDE_PX=1536` · `I2T_SUPPORTS_JSON_SCHEMA=true` · `I2T_SUPPORTS_BBOX=true` · `I2T_TIMEOUT_S=90` · `I2T_MAX_CONCURRENCY=4` · `I2T_RPM=30` · `I2T_DAILY_LIMIT=3000` · (추가) `I2T_BBOX_FORMAT=gemini_yxyx_1000`(xyxy_1000 · xyxy_norm · xyxy_px) |
| T2I | `T2I_PROVIDER=gemini` · `T2I_MODEL=gemini-3.1-flash-lite-image` · `T2I_DEFAULT_ASPECT=16:9` · `T2I_MAX_SIDE_PX=1024` · `T2I_SUPPORTS_REFERENCE_IMAGES=true` · `T2I_MAX_REFERENCE_IMAGES=4` · `T2I_SUPPORTS_EDIT=true` · `T2I_SUPPORTS_MASK=false` · `T2I_IMAGES_PER_CALL=1` · `T2I_TIMEOUT_S=120` · `T2I_MAX_CONCURRENCY=2` · `T2I_DAILY_LIMIT=100`(이미지 장수) · (추가) `T2I_RPM=0` · `T2I_RESPONSE_FORMAT=b64_json`(openai_compat, `none` 이면 안 보냄) · `T2I_SIZE`(openai_compat 크기 고정) |
| 웹 검색 | `WEBSEARCH_PROVIDER=gemini_grounding` · `WEBSEARCH_MODEL=gemini-3.5-flash-lite` · `WEBSEARCH_RETURN_SOURCES=false` · `WEBSEARCH_TIMEOUT_S=60` · `WEBSEARCH_DAILY_LIMIT=150` · (추가) `WEBSEARCH_RPM=0` · `WEBSEARCH_MAX_CONCURRENCY=2` |
| 검색 API · 수집 | `SEARCH_API_PROVIDER=none`(brave · tavily · serper · google_cse · searxng · internal · mock) · `SEARCH_API_BASE_URL` · `SEARCH_API_KEY` · (추가) `SEARCH_API_CX`(google_cse) · `WEB_FETCH_ENABLED=true` · `WEB_FETCH_USER_AGENT=WinmateBot/0.1` · `WEB_FETCH_RESPECT_ROBOTS=true` · `WEB_FETCH_RATE_LIMIT_RPS=0.5` · `WEB_FETCH_TIMEOUT_S=20` · `WEB_FETCH_CACHE_TTL_HOURS=168` · `WEB_FETCH_ALLOWED_DOMAINS=`(쉼표, 비우면 전부) |
| 임베딩 | `EMBEDDING_PROVIDER=lsa`(none · local · openai_compat · internal) · `EMBEDDING_MODEL=BAAI/bge-m3` · `EMBEDDING_MODEL_PATH=./models/bge-m3` · `LOCAL_MODEL_DEVICE=cpu` · `HF_HOME` · `HF_HUB_OFFLINE` · (추가) `EMBEDDING_BASE_URL` · `EMBEDDING_API_KEY` · `EMBEDDING_DIM` |
| 정책 | `LLM/I2T/T2I/WEBSEARCH_ALLOW_CONFIDENTIAL=false` |

`<CAP>_API_KEY` 가 있으면 GEMINI_API_KEY 대신 쓴다(기능마다 다른 키). openai_compat 는 `<CAP>_BASE_URL` 이 있어야 한다.

## 5. 대체 경로(제공자가 못 하는 것을 같은 응답 모양으로)

| 조건 | 처리 | 응답 표시 |
|---|---|---|
| `LLM_SUPPORTS_JSON_SCHEMA=false` | 스키마를 시스템 지시에 넣고 본문에서 JSON 을 꺼냄(코드 펜스 · 끝 쉼표 허용) | `fallback: json_parse` |
| JSON 이 스키마에 안 맞음(고유 모드 포함) | 오류 목록을 붙여 최대 2번 다시 받음 → 그래도 실패면 422 `SCHEMA_MISMATCH` | `fallback: json_repair` |
| `LLM_SUPPORTS_TOOLS=false` | ReAct 텍스트 규약(`Action:` / `Action Input:` / `Final Answer:`)으로 tool_calls 생성, 앞선 도구 결과는 `Observation` 으로 | `fallback: react` |
| `LLM_SUPPORTS_STREAMING=false` · json_schema · tools | 스트리밍 대신 한 번에 `delta` 1개 | — |
| `I2T_SUPPORTS_BBOX=false` + want_bbox | 박스 없이 | `boxes: []` + `warnings` |
| `T2I_SUPPORTS_REFERENCE_IMAGES=false` + 참조 | 참조를 빼고 생성(호출한 쪽이 로컬 합성 가능) | `fallbacks: references_dropped` |
| 참조가 `T2I_MAX_REFERENCE_IMAGES` 초과 | 앞에서부터 그만큼 | `warnings: references_truncated…` |
| 제공자가 다른 비율로 줌 / Gemini 가 받지 않는 비율 | 가까운 비율로 만들고 가운데를 잘라 정확히 맞춤(1~3% 오차는 조용히) | `fallbacks: aspect_cropped`(3% 넘을 때) |
| 편집 + mask + `T2I_SUPPORTS_MASK=false` | 마스크 상자 + 여백(max(64px, 짧은 변 25%)) → 가까운 비율로 넓혀 자름 → 512~1024 로 맞춰 편집 → 원래 크기 → **마스크 안쪽만** 페더 합성. 마스크 밖 픽셀은 원본과 같다(PNG) | `fallbacks: mask_crop_paste` |
| 편집 + mask + `T2I_SUPPORTS_MASK=true` | 전체 이미지 + 마스크로 편집 후, 역시 마스크 안쪽만 합성 | — |
| 편집 + 원본과 다른 aspect | 캔버스 확장(가장자리 거울 반사 + 블러) → "자연스럽게 확장" 지시로 편집 → 원래 영역은 원본 픽셀로 | `fallbacks: outpaint_extend` |
| `T2I_SUPPORTS_EDIT=false` | 참조를 지원하면 원본을 참조(base)로 넣어 생성, 아니면 501 `EDIT_UNSUPPORTED` | `fallbacks: edit_as_generate` |

마스크: `{box:[x0,y0,x1,y1]}`(0..1) 또는 마스크 이미지(`file_id` · `data_b64`) — 흰색(밝기 ≥128) = 수정. 투명 픽셀이 있으면 투명 = 수정(OpenAI 방식).

## 6. 정책 · 한도 · 오류

- 기밀: `confidential=true` 인데 `<CAP>_ALLOW_CONFIDENTIAL=false` → 403 `POLICY_CONFIDENTIAL`(live · record · replay).
  `MODEL_MODE=mock` 은 밖으로 나가는 것이 없어 막지 않는다 — 차단 분기를 mock 으로 시험하려면 `MOCK_ENFORCE_CONFIDENTIAL=true`
  (이 서비스 테스트는 그렇게 돈다). 사내 모델로 바꾸면 사내 정책대로 `*_ALLOW_CONFIDENTIAL=true`.
- 문맥 길이: 메시지 글자로 `estimate_tokens` 추정 > `LLM_MAX_INPUT_TOKENS` → 413 `CONTEXT_TOO_LONG`.
- 한도(live · record 만): Redis `wm:ai:rpm:<cap>:<분>` · `wm:ai:day:<cap>:<YYYYMMDD 로컬>` → 429 `RATE_LIMITED` · `DAILY_LIMIT_EXCEEDED`.
  0 = 제한 없음, t2i 하루 한도는 이미지 장수. 실패한 호출은 하루 카운터에서 되돌린다. Redis 가 죽으면 경고만 남기고 통과.
- 동시 실행 `<CAP>_MAX_CONCURRENCY`(대기 시간은 제한 시간에 넣지 않음) · 제한 시간 `<CAP>_TIMEOUT_S` → 504 `TIMEOUT`.
- 제공자 429 · 5xx · 연결 오류 → 1초 · 2초 백오프로 최대 2번 재시도. 그래도 실패 → 429 `RATE_LIMITED` / 502 `PROVIDER_ERROR`.
- 그 밖: 400 `TOO_MANY_IMAGES` · `BAD_IMAGE` · `EMPTY_MASK` · `INVALID_ARGUMENT`, 404 `CASSETTE_MISS` · `NOT_FOUND`(file_id),
  501 `NOT_CONFIGURED` · `EDIT_UNSUPPORTED` · `EMBEDDING_DISABLED`, 502 `FILES_UNAVAILABLE`.

## 7. 사내망: `internal` 어댑터 만들기

1. 사내 API 가 **OpenAI 호환**(vLLM · TGI · LiteLLM · Ollama …)이면 코드를 고치지 않는다:
   ```
   LLM_PROVIDER=openai_compat  LLM_BASE_URL=http://<사내 LLM>/v1  LLM_API_KEY=…  LLM_MODEL=…
   LLM_ALLOW_CONFIDENTIAL=true            # 사내 모델이면 기밀 허용
   LLM_SUPPORTS_JSON_SCHEMA=false         # 서버가 json_schema 를 못 받으면 → 프롬프트 + 수리
   LLM_SUPPORTS_TOOLS=false               # 함수 호출이 없으면 → ReAct
   I2T_PROVIDER=openai_compat  I2T_BASE_URL=…  I2T_BBOX_FORMAT=xyxy_px   # 모델의 박스 좌표 규약
   T2I_PROVIDER=openai_compat  T2I_BASE_URL=…  T2I_SUPPORTS_MASK=true/false  T2I_RESPONSE_FORMAT=b64_json
   ```
   점검: `MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py --provider openai_compat`
2. 호환이 아니면 `src/winmate_ai_tools/providers/internal.py` 의 `chat` · `analyze` · `generate` · `edit` · `websearch` 를 채운다
   (입출력 데이터클래스는 `providers/base.py`, 예시는 `openai_compat.py`). 오류는 `errors.provider_error(...)` 로 바꿔 던지면
   429 · 5xx 재시도와 오류 형식이 그대로 적용된다. 테스트는 `tests/test_openai_compat.py` 처럼 respx 로.
3. 사내 요약형 검색 API(요약만 돌려줌)는 `internal.websearch` 에서 `WebSearchResult(summary=…, sources=[])` 로 돌려준다.
   사내 원문 검색 API 는 `search.py` 의 `internal()` 모양만 맞춘다.

## 8. mock 고정 응답

`mocks/ai-tools/<task>.json` — 형식은 [mocks/ai-tools/README.md](../../mocks/ai-tools/README.md).
없으면 JSON 스키마 가짜 값(`$ref` · anyOf · oneOf · allOf · enum · 길이 · 범위 · format · pattern 지원, 항상 스키마 통과,
같은 스키마 → 같은 값, 문자열은 `"[mock] 고객사"` 처럼 속성 이름의 한국어).

## 9. 실제 점검 · 테스트

```bash
MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py            # 맥 · 실제 Gemini
UV_SYSTEM_CERTS=1 uv run pytest services/ai-tools                                  # 네트워크 없음
```
live_check: llm 텍스트 · JSON 스키마 · 도구 2턴(thought signature 왕복) · i2t(만든 그림 + 박스) · t2i 1장 · t2i 편집(잘라 붙이기) ·
웹 검색 → 표(결과 · ms · 제공자/모델 · 비고), 실패가 있으면 종료 코드 1. files 서비스가 없으면 이미지를 `data/ai-tools/live_check/` 에 저장.

문제 해결
- `GEMINI_THINKING_LEVEL` 을 받지 않는 모델이면 400 → 값을 비운다. Gemini 3 은 temperature 1.0 을 권장한다(`LLM_TEMPERATURE`).
- 함수 호출 2턴째 400(thought signature): ai-tools 를 재시작해 서명 기억이 사라진 경우 대체 서명을 붙이므로 보통 통과한다.
- 호출 기록은 `GET /api/ai-tools/v1/calls?task=…`(내부 토큰 필요) 또는 `data/ai-tools/calls.sqlite`.
