# ai-tools 서비스 — 개발 세션 규칙

AI Tools — LLM · I2T · T2I · 웹 검색 · 웹 수집 · 임베딩 (외부 모델 호출의 유일한 통로)

- 포트: **5010** · 게이트웨이 경로: `/api/ai-tools/v1/...` · 파이썬 모듈: `winmate_ai_tools`
- 고칠 수 있는 경로(owns): `services/ai-tools/**`
- 호출할 수 있는 서비스(consumes): `files`

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=ai-tools          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=ai-tools         # 이 서비스 테스트
make contracts SERVICE=ai-tools    # contracts/ai-tools.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("ai-tools", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("ai-tools")`(data/ai-tools/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=ai-tools` 를 돌리고 `contracts/ai-tools.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태
자세한 설명은 [README.md](README.md)(제공자 매트릭스 · 환경 변수 · 대체 경로 · 사내 어댑터 · 카세트).

**API** (`/v1`, 모델 호출 · 로그는 `tags=["internal"]`)
- `GET /capabilities` · `GET /usage` — 모드 · 기능별 제공자/모델/지원 여부/한도 · 오늘 사용량(웹도 읽음)
- `POST /llm/chat` · `POST /llm/stream`(SSE delta → done) — JSON 스키마(고유 모드 · 프롬프트+파싱 · 2회 수리) · 도구(고유 · ReAct)
- `POST /i2t/analyze` — file_id/url/data_b64, HEIC→JPEG, 축소, 장수 제한(400), JSON + 박스(감싼 스키마 → [x0,y0,x1,y1] 0..1)
- `POST /t2i/generate` · `POST /t2i/edit` — files 저장(meta: task · prompt · aspect · provider · model · references · ai_generated …),
  references_dropped · aspect_cropped · mask_crop_paste(마스크 밖 픽셀 동일) · outpaint_extend · edit_as_generate
- `POST /websearch`(RETURN_SOURCES=false 면 출처 숨김) · `POST /search`(none → available=false, brave/tavily/serper/google_cse/searxng/internal)
- `POST /fetch`(robots · 호스트별 속도 · 허용 도메인 · 디스크 캐시 · trafilatura · PDF pages) · `POST /embed`(lsa → 501, local · openai_compat)
- `GET /calls` · `GET /calls/{id}` — 호출 로그(data/ai-tools/calls.sqlite, MODEL_CALL_LOG=full 이면 본문, 시작 때 보관 기간 정리)

**제공자**: gemini(google-genai 2.28: response_json_schema · function_declarations + thought signature 왕복 · thinking_level ·
이미지 출력 · google_search) · openai_compat(openai 3.24 + httpx 클라이언트) · internal(501 자리, 구현 안내는 providers/internal.py) ·
mock(fixtures · faker). 모드 live/mock/record/replay, 카세트 키 = 정규화 요청(이미지 내용 해시).

**코드 지도**: `config.py`(env) · `runtime.py`(정책 · 모드 · 한도 · 재시도 · 카세트 · 로그) · `llm.py` · `i2t.py` · `t2i.py` ·
`websearch.py` · `search.py` · `fetch.py` · `embed.py` · `capabilities.py` · `providers/` · `faker.py` · `jsonfix.py` · `react.py` · `imaging.py`

**테스트**: `UV_SYSTEM_CERTS=1 uv run pytest services/ai-tools` (네트워크 없음 · 160개 안팎 · ~15초). Gemini 는 실제 SDK 요청을 respx 로,
openai_compat 은 respx, files 는 스텁 앱, 한도는 fakeredis. `test_basics.py::test_ai_client_contract_strict` 가 `winmate_common.ai`
전 메서드를 계약(strict)으로 검증한다.
**실제 점검(맥)**: `MODEL_MODE=live uv run python services/ai-tools/scripts/live_check.py [--provider openai_compat]`
**카세트 비교**: `scripts/cassette_compare.py <맥 카세트> <사내망 카세트>`

**알려진 한계**
- 실제 Gemini 검증(2026-10-06): 이 서비스가 만든 REST 본문을 맥에서 그대로 보내 LLM(텍스트 · JSON · 도구 + 서명 왕복 · 스트리밍) · I2T 박스 ·
  T2I(생성 · 편집 · 21:9) · 웹 검색(grounding) 모두 200. 그 요청 · 응답이 `tests/fixtures/gemini_live_*.json` 이고
  `test_gemini_live_fixtures.py` 가 같은 본문을 보내는지 · 실제 응답을 바르게 바꾸는지 고정한다(모양을 바꾸면 맥에서 live_check 로 다시 확인).
  Gemini 도 `call_44988` 꼴 함수 호출 id 를 준다 → 우리가 만든 `call_<ULID>` 만 빼고 돌려보낸다. 사내 API 는 아직 못 불러 봤다.
- Gemini thought signature 는 프로세스 메모리에 기억(재시작하면 대체 서명 사용).
- 스트리밍은 텍스트만 조각으로 보낸다(json_schema · tools 는 한 번에). mock 고정 응답의 차례 돌리기는 프로세스 안 호출 횟수 기준.
- 로컬 임베딩은 sentence-transformers 미설치라 501. PDF 수집은 같은 가상환경의 pypdfium2 가 있을 때만(선언된 의존성 아님).
- `docs/scenarios/07-image.md` 는 기밀 차단 코드를 `CONFIDENTIAL_BLOCKED`, 03-mi 는 검색 API none 을 501 로 가정했지만
  이 서비스는 지시대로 `POLICY_CONFIDENTIAL`(403) · `available=false`(200) 를 쓴다.
