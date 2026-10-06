# 사내 모델 API 로 옮기기 (Gemini → 사내 LLM · I2T · T2I · 웹 검색)

외부 모델은 ai-tools 서비스(5010)만 부른다. 그래서 바꾸는 것은 **`.env` 의 ai-tools 키뿐**이고 기능 서비스 코드는 그대로다.
`.env` 는 프로세스가 시작할 때 읽으므로 바꾼 뒤에는 `make restart`(모델 키만 바꿨으면 `ops/node_modules/.bin/pm2 restart ai-tools` 로 충분 —
`T2I_MAX_SIDE_PX` 는 image 서비스도 읽는다). 키 하나하나의 뜻은 [`.env.example`](../.env.example),
설치 · 운영은 [OPERATIONS.md](OPERATIONS.md), ai-tools 내부는 [services/ai-tools/README.md](../services/ai-tools/README.md).

지금 설정 확인(어느 단계에서든):

```bash
curl -s -H "X-Internal-Token: $(cat data/.internal_token)" \
  http://127.0.0.1:5000/api/ai-tools/v1/capabilities | .venv/bin/python -m json.tool
# mode · 기능별 provider/model · supports · available · allow_confidential · 한도 · 오늘 사용량
```

## 0. 순서

- [ ] §1 사내 API 명세에서 확인할 것을 받는다
- [ ] §7-A **옮기기 전에** 맥에서 기준 카세트를 기록한다
- [ ] §2 기능마다 제공자를 고르고 §3 대로 `.env` 를 채운다(필요하면 §5 `internal` 어댑터)
- [ ] §6 기밀 정책 · 프록시 · 인증서
- [ ] §7-B replay 회귀 → §7-C live_check → §7-D 품질 비교 → §7-E 시나리오 E2E → §7-F 운영 전환

---

## 1. 사내 API 에서 확인할 것

- [ ] 기능별 엔드포인트 주소 · 인증 방식(`Authorization: Bearer <키>` 인가, 다른 헤더인가)
- [ ] OpenAI 호환인가: `POST <base>/chat/completions` · `/images/generations` · `/images/edits` · `/embeddings`
- [ ] 모델 이름(요청의 `model` 값)
- [ ] LLM: 컨텍스트 길이 · 출력 상한 · `response_format: json_schema` · `tools`/`tool_choice` · `stream` 지원, 이미지 입력 가능 여부
- [ ] I2T: 이미지 입력 방식(data URI `image_url`?) · 한 번에 몇 장 · 크기 상한 · 박스 좌표 규약(0–1000? 픽셀? `[y, x, …]` 순서?)
- [ ] T2I: 크기 · 비율 · 한 번에 장 수 · 참조 이미지 · 편집 · 마스크 규약(투명 = 수정?) · 응답이 base64 인가 URL 인가
- [ ] 웹 검색: 요청 · 응답 모양(요약만? 출처도?), 질의가 사외 검색 엔진으로 나가는가
- [ ] 한도(분당 · 하루) · 권장 제한 시간 · 동시 접속 수
- [ ] 기능별 기밀 데이터 허용 범위(보안 담당 확인)
- [ ] 프록시 · 사설 인증서가 필요한가

## 2. 제공자 고르기

모델 기능(`LLM` · `I2T` · `T2I` · `WEBSEARCH`)마다 따로 고른다. 검색 API · 임베딩은 제공자 목록이 달라 §3.5 · §3.6 에 따로 적었다.

| 사내 API 모양 | `<기능>_PROVIDER` | 코드 수정 |
|---|---|---|
| OpenAI 호환(vLLM · TGI · LiteLLM · Ollama 등) + 인증이 `Authorization: Bearer`(또는 없음) | `openai_compat`(별칭 `openai`) | 없음 |
| 사내 중계가 Gemini API 모양 그대로 받음 | `gemini`(웹 검색은 `gemini_grounding`) + `GEMINI_BASE_URL` | 없음 |
| 그 밖(전용 요청 · 응답, 다른 인증 헤더) | `internal` | [§5](#5-internal-어댑터-만들기) |
| 아직 없음 · 시험 | `mock`(그 기능만 가짜 응답) | 없음 |

- `openai_compat` 은 openai SDK 로 `<기능>_BASE_URL` 뒤에 경로를 붙인다 → 서버 경로가 `/v1/...` 이면 `BASE_URL` 에 `/v1` 까지 넣는다.
  `<기능>_API_KEY` 가 비면 `Bearer not-needed` 를 보낸다. 다른 인증 헤더는 설정으로 넣을 수 없다 → `internal`.
- `gemini` 의 키는 `<기능>_API_KEY` → 없으면 `GEMINI_API_KEY`, 주소는 언제나 `GEMINI_BASE_URL`(`<기능>_BASE_URL` 은 쓰지 않음).
- 모르는 값(예 `none`)은 501 `NOT_CONFIGURED` 이고 capabilities 에 `available: false` — 사실상 그 기능을 끈다
  (검색 API 는 `none` 이 정식 값이라 `available: false` 와 빈 결과(200), 임베딩은 `lsa` · `none` 이 501 `EMBEDDING_DISABLED`).

## 3. 기능별 `.env`

### 3.1 LLM

```dotenv
LLM_PROVIDER=openai_compat
LLM_BASE_URL=http://<사내 LLM 주소>/v1
LLM_API_KEY=<키>
LLM_MODEL=<서버의 모델 id>
LLM_MAX_INPUT_TOKENS=<컨텍스트 길이 - LLM_MAX_OUTPUT_TOKENS - 여유>
LLM_MAX_OUTPUT_TOKENS=4096
LLM_TEMPERATURE=0.2
LLM_SUPPORTS_JSON_SCHEMA=true
LLM_SUPPORTS_TOOLS=true
LLM_SUPPORTS_STREAMING=true
LLM_TIMEOUT_S=90
LLM_MAX_CONCURRENCY=4
LLM_RPM=<사내 분당 한도>
LLM_DAILY_LIMIT=<사내 하루 한도>
LLM_ALLOW_CONFIDENTIAL=true
```

`openai_compat` 이 보내고 받는 것:

| 경우 | 요청 |
|---|---|
| 기본 | `POST <BASE>/chat/completions` `{model, messages, temperature, max_tokens}` — 역할 `system` · `user` · `assistant`(+`tool_calls`) · `tool` |
| JSON 스키마 + `LLM_SUPPORTS_JSON_SCHEMA=true` | + `response_format: {type: "json_schema", json_schema: {name, schema, strict}}`(스키마가 strict 조건을 만족할 때만 `strict: true`) |
| 도구 + `LLM_SUPPORTS_TOOLS=true` | + `tools: [{type: "function", function: {name, description, parameters}}]` · `tool_choice`(auto · none · required · 함수 지정) |
| 텍스트 스트리밍 + `LLM_SUPPORTS_STREAMING=true` | `stream: true`(SSE). JSON 스키마 · 도구 요청은 언제나 한 번에 |
| 대화에 이미지 | user `content` 에 `{"type": "image_url", "image_url": {"url": "data:<mime>;base64,…"}}`(긴 변 `I2T_MAX_IMAGE_SIDE_PX` 로 줄임) |
| 받는 것 | `choices[0].message.content` · `tool_calls[].function.{name, arguments(JSON 문자열)}` · `finish_reason` · `usage.prompt_tokens` · `completion_tokens` |

- [ ] 서버가 `response_format` 을 400 으로 거부하거나 JSON 이 자주 깨지면 `LLM_SUPPORTS_JSON_SCHEMA=false` — 스키마를 시스템 지시에 넣고 본문에서 JSON 을 꺼내 검증, 최대 2번 수리.
- [ ] 함수 호출을 못 하면(예: vLLM 은 `--enable-auto-tool-choice` 없이 `tool_choice: auto` 를 거부) `LLM_SUPPORTS_TOOLS=false` — ReAct 텍스트 규약으로 같은 `tool_calls` 를 만든다.
- [ ] SSE 를 못 하면 `LLM_SUPPORTS_STREAMING=false`.
- [ ] `LLM_MAX_INPUT_TOKENS`: 입력 길이는 글자 수로 추정한다(한글 1.5자 · 그 밖 3.5자 = 1토큰) → 실제 컨텍스트보다 넉넉히 낮게.
- [ ] `LLM_TIMEOUT_S × 3 < 300`: JSON 수리로 모델을 최대 3번 부르고, 기능 서비스 → ai-tools 호출 제한이 300초다.
- [ ] 온도는 사내 모델 권장값으로(`GEMINI_THINKING_LEVEL` 은 gemini 제공자만 쓴다).
- [ ] 사내 LLM 이 이미지 입력을 못 받으면, 대화에 이미지를 넣는 기능 흐름은 제공자 오류가 난다 → 해당 기능 세션에 I2T 로 나누도록 요청.

### 3.2 I2T (이미지 → 글 · JSON · 박스)

```dotenv
I2T_PROVIDER=openai_compat
I2T_BASE_URL=http://<사내 VLM 주소>/v1
I2T_API_KEY=<키>
I2T_MODEL=<모델 id>
I2T_MAX_OUTPUT_TOKENS=4096
I2T_MAX_IMAGES_PER_CALL=<서버 상한>
I2T_MAX_IMAGE_SIDE_PX=1536
I2T_SUPPORTS_JSON_SCHEMA=true
I2T_SUPPORTS_BBOX=true
I2T_BBOX_FORMAT=xyxy_1000
I2T_TIMEOUT_S=90
I2T_ALLOW_CONFIDENTIAL=true
```

- 보내는 것: `chat/completions` 의 user 메시지 = 이미지들(`image_url` data URI) + 프롬프트(+ JSON 이면 `response_format`). 서버가 data URI 이미지를 받아야 한다.
- 이미지는 보내기 전에 HEIC → JPEG, 긴 변 `I2T_MAX_IMAGE_SIDE_PX` 로 줄인다. `I2T_MAX_IMAGES_PER_CALL` 을 넘으면 400 `TOO_MANY_IMAGES`.
- 박스: 결과 스키마를 `{result, boxes: [{label, box_2d, image_index?, score?}]}` 로 감싸 받고 `box_2d` 를 `[x0, y0, x1, y1]`(0..1)로 바꾼다.

| `I2T_BBOX_FORMAT` | 모델이 내는 `box_2d` |
|---|---|
| `gemini_yxyx_1000`(기본) | `[ymin, xmin, ymax, xmax]` 0–1000 |
| `xyxy_1000` | `[xmin, ymin, xmax, ymax]` 0–1000 |
| `xyxy_norm` | `[xmin, ymin, xmax, ymax]` 0–1 |
| `xyxy_px` | `[xmin, ymin, xmax, ymax]` 보낸(줄인) 이미지의 픽셀 |

- [ ] 모델 문서의 좌표 규약에 맞춘다. 박스를 못 내면 `I2T_SUPPORTS_BBOX=false`(→ `boxes: []` + `warnings`).
- [ ] JSON 이 자주 깨지면 `I2T_SUPPORTS_JSON_SCHEMA=false`(프롬프트 + 파싱 + 수리).

### 3.3 T2I (이미지 생성 · 편집)

```dotenv
T2I_PROVIDER=openai_compat
T2I_BASE_URL=http://<사내 T2I 주소>/v1
T2I_API_KEY=<키>
T2I_MODEL=<모델 id>
T2I_DEFAULT_ASPECT=16:9
T2I_MAX_SIDE_PX=1024
T2I_SIZE=
T2I_RESPONSE_FORMAT=b64_json
T2I_IMAGES_PER_CALL=1
T2I_SUPPORTS_REFERENCE_IMAGES=true
T2I_MAX_REFERENCE_IMAGES=4
T2I_SUPPORTS_EDIT=true
T2I_SUPPORTS_MASK=false
T2I_TIMEOUT_S=120
T2I_DAILY_LIMIT=<하루 장수>
T2I_ALLOW_CONFIDENTIAL=true
```

| 경우 | 요청(`openai_compat`) |
|---|---|
| 생성 | `POST <BASE>/images/generations` `{model, prompt, n, size, response_format}` |
| 생성 + 참조 이미지 | `POST <BASE>/images/edits`(multipart, `image` 여러 장) |
| 편집 | `POST <BASE>/images/edits` 원본(+ 참조) + 지시, `T2I_SUPPORTS_MASK=true` 면 `mask`(RGBA PNG, **투명 = 수정**) |
| 받는 것 | `data[].b64_json` 또는 `data[].url`(ai-tools 가 내려받음 — localhost · 루프백 주소는 막힌다 → `b64_json` 권장) |

- `size` = `T2I_SIZE` 또는 비율 × `T2I_MAX_SIDE_PX`(64 배수). 받은 그림은 요청 비율로 가운데를 잘라 정확히 맞춘다(3% 넘게 자르면 `aspect_cropped`).
- `n` = `T2I_IMAGES_PER_CALL` 까지, 넘는 장수는 반복 호출. 하루 한도는 장수로 센다.
- 결과는 files 서비스에 `source=generated` · 메타 `ai_generated: true` 로 저장된다.
- `T2I_MAX_SIDE_PX` 는 image 서비스의 기본 렌디션 크기로도 쓰인다.
- [ ] 서버가 `response_format` 인자를 거부하면 `T2I_RESPONSE_FORMAT=none`. 정해진 크기만 받으면 `T2I_SIZE=1024x1024` 처럼.
- [ ] 참조 이미지를 못 받으면 `T2I_SUPPORTS_REFERENCE_IMAGES=false`, 편집이 없으면 `T2I_SUPPORTS_EDIT=false`, 인페인팅을 잘하면 `T2I_SUPPORTS_MASK=true`.

### 3.4 웹 검색(요약형)

| 사내 검색 API | 설정 |
|---|---|
| OpenAI 호환 chat 모델(검색 후 요약) | `WEBSEARCH_PROVIDER=openai_compat` · `WEBSEARCH_BASE_URL` · `WEBSEARCH_API_KEY` · `WEBSEARCH_MODEL` — 시스템(한국어 사실 요약 지시) + 사용자(질의) → 요약 = `content`, 출처 = `message.annotations[].url_citation`(있으면) |
| 전용 API(요약만 줌) | `WEBSEARCH_PROVIDER=internal` + §5 의 `websearch()` → `WebSearchResult(summary=…, sources=[])` |
| 없음 | `WEBSEARCH_PROVIDER=none`(501, `available: false`) — 기능 서비스가 웹 검색 없이 가야 한다 |

- [ ] `WEBSEARCH_RETURN_SOURCES`: 사내 결과에 출처 URL 이 오면 `true`, 아니면 `false`(지금 맥 개발도 false 로 사내처럼 출처를 숨긴다).
- [ ] `WEBSEARCH_MAX_OUTPUT_TOKENS` · `WEBSEARCH_TIMEOUT_S` · `WEBSEARCH_DAILY_LIMIT` 를 사내 한도에 맞춘다.

### 3.5 검색 API(원문 URL, 나중에 · 선택) · 웹 수집

```dotenv
SEARCH_API_PROVIDER=internal
SEARCH_API_BASE_URL=http://<사내 검색>/search
SEARCH_API_KEY=<있으면 Bearer 로>
SEARCH_API_TIMEOUT_S=20
```

- `internal`: `POST <SEARCH_API_BASE_URL>`(전체 URL) `{query, locale, limit}` → `{results | items: [{url | link, title, snippet | content | description, published_at | date}]}`.
  모양이 다르면 `services/ai-tools/src/winmate_ai_tools/search.py` 의 `internal()` 만 고친다.
- brave · tavily · serper · google_cse · searxng 도 `SEARCH_API_BASE_URL` 로 사내 중계 주소를 줄 수 있다. 없으면 `none`(→ `available: false`, 200).
- [ ] 사내망에서 외부 웹이 막혀 있으면 `WEB_FETCH_ENABLED=false`(→ `allowed: false, reason: "disabled"`).
  일부만 열려 있으면 프록시(§6) + `WEB_FETCH_ALLOWED_DOMAINS=…`.

### 3.6 임베딩

- 지금 kb 서비스는 winmate-kb 자체 LSA 를 쓰고, ai-tools `/embed` 는 기본(`lsa`)에서 501 `EMBEDDING_DISABLED` 다.
- 사내 임베딩 API 가 OpenAI 호환이면: `EMBEDDING_PROVIDER=openai_compat` · `EMBEDDING_BASE_URL=http://<사내>/v1` · `EMBEDDING_API_KEY` · `EMBEDDING_MODEL` ·
  `EMBEDDING_DIM`(모르면 비움) → `POST <BASE>/embeddings {model, input, encoding_format: "float"}`.
- `internal` 은 자리만(501), `local` 은 sentence-transformers 가 설치되어 있지 않아 501.

### 3.7 한도 · 제한 시간 · 재시도(모든 기능 공통)

| 키 | 뜻 |
|---|---|
| `<기능>_RPM` · `<기능>_DAILY_LIMIT` | 분당 · 하루 상한(0 = 없음). live · record 에서만 Redis 로 센다. T2I 하루 한도는 장수. 실패한 호출은 하루 카운터에서 되돌린다 |
| `<기능>_MAX_CONCURRENCY` | ai-tools 안 동시 호출 수(기다리는 시간은 제한 시간에 넣지 않는다) |
| `<기능>_TIMEOUT_S` | 호출 1회 제한 → 504 `TIMEOUT` |
| (고정) 재시도 | 제공자 429 · 5xx · 연결 오류는 1초 · 2초 뒤 최대 2번 더 |

## 4. 지원 여부 플래그와 대체 경로

사내 모델이 못 하는 것은 플래그를 `false` 로 두면 ai-tools 가 **같은 응답 모양**으로 대신한다. 어느 길로 갔는지는 응답의
`fallback`(LLM · I2T) · `fallbacks` · `warnings`(T2I · I2T)와 호출 로그에 남는다.

| 조건 | ai-tools 가 하는 일 | 표시 |
|---|---|---|
| `LLM_SUPPORTS_JSON_SCHEMA=false`(I2T 도 같음) | 스키마를 시스템 지시에 넣고 본문에서 JSON 을 꺼낸다(코드 펜스 · 끝 쉼표 허용) | `fallback: json_parse` |
| JSON 이 스키마에 안 맞음(고유 모드 포함) | 오류 목록을 붙여 최대 2번 다시 받는다 → 그래도 실패면 422 `SCHEMA_MISMATCH` | `fallback: json_repair` |
| `LLM_SUPPORTS_TOOLS=false` | ReAct 텍스트 규약(`Action:` / `Action Input:` / `Final Answer:`)으로 `tool_calls` 를 만든다. 앞선 도구 결과는 `Observation` | `fallback: react` |
| `LLM_SUPPORTS_STREAMING=false` | 스트리밍 대신 `delta` 하나로 한 번에 | — |
| 입력이 `LLM_MAX_INPUT_TOKENS` 초과(추정) | 보내지 않고 413 `CONTEXT_TOO_LONG` | — |
| `I2T_SUPPORTS_BBOX=false` + 박스 요청 | 박스 없이 답한다 | `boxes: []` + `warnings` |
| 이미지가 `I2T_MAX_IMAGES_PER_CALL` 초과 | 400 `TOO_MANY_IMAGES` | — |
| `T2I_SUPPORTS_REFERENCE_IMAGES=false` + 참조 | 참조를 빼고 생성(호출한 쪽이 로컬 합성 가능) | `fallbacks: references_dropped` |
| 참조가 `T2I_MAX_REFERENCE_IMAGES` 초과 | 앞에서부터 그만큼 | `warnings: references_truncated…` |
| 받은 그림 비율이 다름 | 가운데를 잘라 정확히 맞춘다(1~3% 는 조용히) | `fallbacks: aspect_cropped`(3% 초과) |
| 편집 + 마스크 + (`T2I_SUPPORTS_MASK=false` 또는 고유 마스크 없는 제공자) | 마스크 상자 + 여백을 잘라 편집 → 원래 크기로 → 마스크 안쪽만 페더 합성(밖은 원본 픽셀 그대로) | `fallbacks: mask_crop_paste` |
| 편집 + 마스크 + `T2I_SUPPORTS_MASK=true`(openai_compat · 고유 마스크를 구현한 internal) | 전체 이미지 + 마스크로 편집 후 마스크 안쪽만 합성 | — |
| 편집 비율이 원본과 다름 | 캔버스를 넓혀(가장자리 반사 + 블러) "자연스럽게 확장" 지시로 편집, 원래 영역은 원본 | `fallbacks: outpaint_extend` |
| `T2I_SUPPORTS_EDIT=false` | 참조를 지원하면 원본을 참조(base)로 넣어 생성, 아니면 501 `EDIT_UNSUPPORTED` | `fallbacks: edit_as_generate` |
| 요청 장수 > `T2I_IMAGES_PER_CALL` | 나눠서 반복 호출(모자라면 `fewer_images` 경고) | — |

## 5. internal 어댑터 만들기

사내 API 가 OpenAI 호환이 아닐 때만. ai-tools 서비스 담당이 고친다(`services/ai-tools/**`). 계약(`contracts/ai-tools.json`)은 바뀌지 않는다.

- [ ] `services/ai-tools/src/winmate_ai_tools/providers/internal.py` 의 `InternalProvider` 를 채운다 — 레지스트리는 이미 `internal` 로 이어져 있다.
  입출력 데이터클래스는 `providers/base.py`, 예시는 `providers/openai_compat.py`.
- [ ] `available(cfg)` 가 설정이 있으면 `True` 를 돌려주게 한다(지금은 `False` → capabilities `available: false`).
- [ ] 필요한 메서드만 구현한다. 고유 JSON 모드 · 도구를 못 하면 `SUPPORTS_*=false` 로 두면 `call.json_schema` · `call.tools` 가 `None` 으로 와서 글만 주고받으면 된다.

| 메서드 | 받는 것 | 돌려줄 것 |
|---|---|---|
| `chat(cfg, call: LLMCall)` | `call.system` · `call.messages`(`Msg`: role user · assistant · tool, `parts` = 글 · `Img`, `tool_calls`, `tool_call_id`) · `temperature` · `max_tokens` · `json_schema` · `tools` · `tool_choice` | `LLMResult(text, tool_calls=[{id, name, arguments(dict)}], finish_reason, usage={input_tokens, output_tokens}, model)` |
| `stream(cfg, call)`(선택) | 같음 | 글 조각(`str`)을 차례로 yield, 마지막에 `LLMResult` 하나. 없으면 기본(한 번에) |
| `analyze(cfg, call: I2TCall)` | `call.images`(`Img.data` 바이트 · `mime` · `width` · `height`) · `prompt` · `system` · `turns`(수리용 추가 대화) · `json_schema` | `LLMResult(text=…)` |
| `generate(cfg, call: T2ICall)` | `prompt` · `aspect` · `size`(w, h) · `n` · `refs`(`Ref.img` · `role` · `strength`) · `seed` | `T2IResult(images=[GenImage(data, mime)], model)` |
| `edit(cfg, call: EditCall)` | `image` · `prompt` · `size` · `refs` · `n` · `mask`(L PNG, 255 = 수정 — `native_mask = True` 이고 `T2I_SUPPORTS_MASK=true` 일 때만) | `T2IResult(...)` |
| `websearch(cfg, call: WebSearchCall)` | `query` · `locale` · `max_sources` · `temperature` · `max_tokens` | `WebSearchResult(summary, sources=[], queries=[], usage, model)` |

- [ ] 주소 · 키 · 제한 시간은 `cfg.base_url` · `cfg.api_key` · `cfg.timeout_s`(`<기능>_BASE_URL` · `_API_KEY` · `_TIMEOUT_S`), 모델은 `cfg.model`.
- [ ] HTTP 는 `httpx.AsyncClient`, 오류는 `errors.provider_error(...)` 로 바꿔 던진다 — 429 → `RATE_LIMITED`(재시도), 5xx · 연결 오류 → `PROVIDER_ERROR`(재시도), 408 · 504 → `TIMEOUT`.
- [ ] 테스트: `tests/test_openai_compat.py` 처럼 respx 로 사내 응답을 흉내 → `make test SERVICE=ai-tools`. 실제 점검은 §7-C.

예시 — 사내 API 모양(`/generate` · `/search/summary` · `X-Api-Key`)은 **가정**이다. 명세에 맞게 바꾼다:

```python
import httpx

from ..config import CapConfig
from ..errors import ProviderError, provider_error
from .base import LLMCall, LLMResult, Provider, WebSearchCall, WebSearchResult


async def _post(cfg: CapConfig, path: str, body: dict) -> dict:
    headers = {"X-Api-Key": cfg.api_key} if cfg.api_key else {}
    try:
        async with httpx.AsyncClient(timeout=cfg.timeout_s) as c:
            r = await c.post((cfg.base_url or "").rstrip("/") + path, json=body, headers=headers)
    except httpx.TimeoutException as exc:
        raise ProviderError(504, "TIMEOUT", "사내 API 응답 시간 초과", {"provider": "internal"}) from exc
    except httpx.HTTPError as exc:
        raise provider_error("internal", f"연결 실패: {exc}", retryable=True) from exc
    if r.status_code >= 400:
        raise provider_error("internal", r.text[:300], status=r.status_code)
    try:
        return r.json()
    except ValueError as exc:
        raise provider_error("internal", "JSON 이 아닌 응답") from exc


class InternalProvider(Provider):
    name = "internal"
    native_mask = False

    def available(self, cfg: CapConfig) -> bool:
        return bool(cfg.base_url)

    async def chat(self, cfg: CapConfig, call: LLMCall) -> LLMResult:
        msgs = [{"role": "system", "content": call.system}] if call.system else []
        msgs += [{"role": m.role, "content": m.text()} for m in call.messages]
        data = await _post(cfg, "/generate", {"model": cfg.model, "messages": msgs,
                                              "temperature": call.temperature, "max_tokens": call.max_tokens})
        return LLMResult(text=data.get("text", ""), model=cfg.model,
                         usage={"input_tokens": int(data.get("prompt_tokens", 0)),
                                "output_tokens": int(data.get("completion_tokens", 0))})

    async def websearch(self, cfg: CapConfig, call: WebSearchCall) -> WebSearchResult:
        data = await _post(cfg, "/search/summary", {"query": call.query, "locale": call.locale})
        return WebSearchResult(summary=data.get("summary", ""), sources=[], model=cfg.model)
```

## 6. 기밀 정책 · 프록시 · 인증서

- [ ] 사내 모델로 바꾼 기능만 `<기능>_ALLOW_CONFIDENTIAL=true`(보안 승인 범위대로). Gemini 로 남은 기능은 `false`.
- [ ] `WEBSEARCH_ALLOW_CONFIDENTIAL`: 사내 검색 API 라도 질의가 사외 검색 엔진으로 나가면 `false` 유지.
- [ ] capabilities 의 `allow_confidential` 로 확인. `false` 인 기능에 `confidential: true` 호출이 오면 403 `POLICY_CONFIDENTIAL`
  (live · record · replay 모두. mock 은 `MOCK_ENFORCE_CONFIDENTIAL=true` 일 때만) — 기능 서비스는 한국어 메시지로 끝내거나 시나리오의 로컬 대체 경로로 간다.
- [ ] `MODEL_CALL_LOG=full` 이면 프롬프트 · 응답(기밀 포함)이 `data/ai-tools/calls.sqlite` 에 남는다 → 정책에 따라 `meta` · `off`, 보관 `MODEL_CALL_LOG_RETENTION_DAYS`.
- [ ] 프록시: `.env` 의 `HTTPS_PROXY` · `HTTP_PROXY` 는 모든 서비스의 HTTP 클라이언트(httpx · openai · google-genai)가 쓴다.
  **`NO_PROXY=localhost,127.0.0.1,::1` 을 꼭 함께** — 서비스끼리 `127.0.0.1:5000` 으로 부른다. 프록시를 거치지 않을 사내 API 호스트도 `NO_PROXY` 에.
- [ ] 사설 인증서: 시스템 묶음에 넣고 그 묶음을 가리킨다(`SSL_CERT_FILE` 은 기본 CA 묶음을 **대체**하므로 사내 CA 하나만 든 파일을 직접 가리키지 않는다).

  ```bash
  sudo cp corp-root-ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates
  # .env
  SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
  REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
  ```

- [ ] 프록시 · 인증서를 바꾼 뒤에는 `make restart`.

## 7. 검증 절차

### A. 맥(Gemini) — 기준 카세트 기록(옮기기 전에)

- [ ] `.env` `MODEL_MODE=record`(`MODEL_CASSETTE_DIR=./data/cassettes`) → `make restart`
- [ ] 시나리오([docs/scenarios](scenarios/))의 기능 흐름을 **공개 시험 자료**로 한 바퀴(기밀 해제 — Gemini 는 기밀 호출이 403 이라 기록되지 않는다).
  같은 입력 파일을 사내망에도 가져간다.
- [ ] `MODEL_MODE=record uv run python services/ai-tools/scripts/live_check.py`(task `live.*`)
- [ ] `COPYFILE_DISABLE=1 tar -czf cassettes.tar.gz data/cassettes` → 번들에(OPERATIONS.md 2.1). 시험 입력 파일도.
- [ ] `MODEL_MODE=live` 로 되돌린다.

카세트: `MODEL_CASSETTE_DIR/<기능>/<task>/<sha256(정규화 요청)>.json`(t2i 그림은 옆에 `<키>.<n>.png`).
키에는 결과에 영향을 주는 값만 넣는다 — 이미지는 file_id 대신 **내용 해시**, 제공자 · 모델 · 기밀 표시 · metadata 는 빼므로 같은 입력이면 맥과 사내망에서 같은 키다.

### B. 사내망 — 모델 없이 결정적 회귀(replay)

- [ ] `tar -xzf cassettes.tar.gz`(→ `data/cassettes`)
- [ ] `.env` `MODEL_MODE=replay`(빠진 카세트를 mock 으로 메우려면 `REPLAY_FALLBACK=mock`) → `make restart`
- [ ] A 와 같은 흐름 · 같은 입력 → 파싱 · 저장 · 내보내기 · 화면 결과가 맥과 같은지
- [ ] 404 `CASSETTE_MISS` 면 입력이 다르다(파일 내용, 날짜 · 시각이 든 프롬프트 등) — `details.path` 가 찾던 카세트 경로
- replay 도 기밀 정책을 적용한다. 재생한 t2i 그림은 사내 files 에 새로 저장되어 새 file_id 를 받는다.

### C. 사내 모델 연결(live_check)

- [ ] §3 대로 `.env` → `ops/node_modules/.bin/pm2 restart ai-tools`
- [ ] 점검:

  ```bash
  MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py                      # .env 그대로(--provider env)
  MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py --provider openai_compat   # 네 기능을 모두 openai_compat 로
  MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py --only llm_text,llm_json,llm_tools,i2t,t2i,t2i_edit
  LIVE_CHECK_TRACE=1 MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py      # 실패 원인
  ```

- [ ] 모두 PASS(또는 의도한 SKIP), 실패가 있으면 종료 코드 1. 비고의 `fallback=` · `fallbacks=` 가 의도한 대체 경로인지(예 `fallback=react`).
- [ ] capabilities: provider · model · `supports` · `available: true` · `allow_confidential`.
- live_check 는 게이트웨이를 거치지 않고 ai-tools 함수를 직접 부른다(Redis 가 없으면 메모리로 한도를 센다).

### D. 품질 비교(record + 카세트 비교)

- [ ] `.env` `MODEL_MODE=record` · `MODEL_CASSETTE_DIR=./data/cassettes-intranet` → `make restart`
- [ ] A 와 같은 흐름 · 같은 입력
- [ ] 비교:

  ```bash
  uv run python services/ai-tools/scripts/cassette_compare.py data/cassettes data/cassettes-intranet --show 50
  uv run python services/ai-tools/scripts/cassette_compare.py data/cassettes data/cassettes-intranet --task rq.extract_form
  ```

  같은 키끼리 짝지어 점수가 낮은 순으로 보여 준다 — JSON 은 값 일치율, 글은 같으면 1, 그림은 크기가 같으면 1. 끝에 평균 · 짝이 없는 수.
- [ ] 점수가 낮은 task 는 플래그(§4) · 출력 상한 · 온도를 조정하거나, 해당 기능 서비스에 프롬프트 개선을 요청한다(`docs/requests/<서비스>.md`).
- [ ] 끝나면 `MODEL_CASSETTE_DIR=./data/cassettes` 로 되돌린다.

### E. 시나리오 E2E

- [ ] `MODEL_MODE=live` 로 브라우저에서 [docs/scenarios](scenarios/) 01~10 의 수용 기준 흐름을 한 바퀴:
  RQ 파일로 채우기(I2T · LLM JSON) · MI 업종 판별 · 웹 검색 · CA · VP · SP · IMG 생성 · 참조 · 부분 수정 · BE 도면 인식(I2T 박스) · SC · PR 딸깍 · 내보내기(PPTX · PDF).
- [ ] 기밀 자료로 한 번 — 허용한 기능은 통과, 막은 기능은 한국어 오류 또는 로컬 대체.
- [ ] (선택) 사내망에 `web/node_modules` 와 Playwright 브라우저를 옮겼으면 `make e2e`.

### F. 운영 전환

- [ ] `MODEL_MODE=live` · `MODEL_CASSETTE_DIR=./data/cassettes` · 한도 · `*_ALLOW_CONFIDENTIAL` 최종값, `GEMINI_API_KEY` 비움 → `make restart` → `ops/node_modules/.bin/pm2 save`
- [ ] `make health` · capabilities 확인

## 8. 되돌리기

- 기능 하나가 문제면 그 기능의 `<기능>_PROVIDER` 만 이전 값이나 `mock` 으로 → `ops/node_modules/.bin/pm2 restart ai-tools`.
- 시연 · 점검용으로 모델 없이 돌리려면 `MODEL_MODE=replay` + `REPLAY_FALLBACK=mock`, 또는 `MODEL_MODE=mock`.

## 9. 자주 나는 오류

호출 로그로 원인을 본다(`fallback` · `attempts` · `error`, `MODEL_CALL_LOG=full` 이면 요청 · 응답 본문):

```bash
curl -s -H "X-Internal-Token: $(cat data/.internal_token)" \
  "http://127.0.0.1:5000/api/ai-tools/v1/calls?capability=llm&limit=20" | .venv/bin/python -m json.tool
```

| 상태 · 코드 | 뜻 | 조치 |
|---|---|---|
| 501 `NOT_CONFIGURED` | 키 · `BASE_URL` 없음, `internal` 미구현, 모르는 제공자 | `error.details`(`env` · `hint`)의 키를 채운다 · §5 |
| 501 `EDIT_UNSUPPORTED` | `T2I_SUPPORTS_EDIT=false` 이고 참조도 `false` | 편집 가능한 모델 · 참조 지원 확인 |
| 501 `EMBEDDING_DISABLED` | `EMBEDDING_PROVIDER=lsa` · `none` | §3.6 |
| 403 `POLICY_CONFIDENTIAL` | 기밀 호출인데 `<기능>_ALLOW_CONFIDENTIAL=false` | §6 — 정책상 막는 것이 맞으면 그대로 |
| 413 `CONTEXT_TOO_LONG` | 추정 입력 토큰 > `LLM_MAX_INPUT_TOKENS` | 자료를 나누거나 값을 모델에 맞춘다 |
| 422 `SCHEMA_MISMATCH` | 2번 수리해도 스키마에 안 맞음 | `details.raw` 확인 · `SUPPORTS_JSON_SCHEMA` 바꿔 보기 · 출력 상한(잘림) · 온도 |
| 429 `RATE_LIMITED` · `DAILY_LIMIT_EXCEEDED` | 우리 한도(`RPM` · `DAILY_LIMIT`) 또는 제공자 429(`details.upstream_status`) | 한도 조정 · `GET /api/ai-tools/v1/usage` |
| 502 `PROVIDER_ERROR` | 제공자 4xx · 5xx | `details.upstream_status` · 메시지. 400 이면 서버가 요청 모양을 거부 → 해당 `SUPPORTS_*=false` · `T2I_SIZE` · `T2I_RESPONSE_FORMAT` |
| 504 `TIMEOUT` | `<기능>_TIMEOUT_S` 초과 | 값 조정(§3.1 의 300초 조건) · 서버 부하 |
| 404 `CASSETTE_MISS` | replay 인데 카세트 없음 | §7-B · `REPLAY_FALLBACK=mock` |
| 400 `TOO_MANY_IMAGES` · `BAD_IMAGE` | 이미지 수 초과 · 읽을 수 없는 이미지 · 내부 주소 URL | `I2T_MAX_IMAGES_PER_CALL` · T2I 는 `b64_json` |
| 502 `FILES_UNAVAILABLE` | t2i 결과를 files 서비스에 못 저장 | `make health` 의 files |
| capabilities `available: false` | openai_compat 에 `BASE_URL` 없음 · gemini 키 없음 · internal 의 `available()` 이 `False` | 설정 · §5 |
