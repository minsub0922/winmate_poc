# Winmate — 코드 에이전트 공통 규칙

삼성 B2B 제안서 제작 어시스턴트. 사내망 우분투 PC(RAM 16GB · GPU 2GB) 한 대에서 **Docker 없이 pm2** 로 도는 마이크로서비스.
개발은 맥에서 Gemini API 로, 사내망에서는 `.env` 값만 바꿔 사내 LLM · I2T · T2I · 웹 검색으로 갈아 끼운다.

## 1. 세션 = 서비스 하나

- 작업을 시작하면 **`services/<서비스>/AGENTS.md`** 를 먼저 읽는다. 고칠 수 있는 경로는 `config/services.yaml` 의 `owns` 뿐이다.
- 다른 서비스가 필요하면 그 서비스의 **계약(`contracts/<서비스>.json`)만** 본다. 코드는 읽지도 고치지도 않는다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 요청을 남긴다(무엇이 · 왜 · 원하는 요청/응답 모양).
- 공용 경로(`libs/common`, `config/`, `ops/`, `scripts/`, `web/src/ui`, `web/src/shell`, `web/src/api/client.ts`)는 플랫폼 담당만 고친다.
  필요하면 `docs/requests/platform.md` 에 적는다.
- 의존성(파이썬·npm)을 새로 넣어야 하면 `docs/requests/platform.md` 에 적는다(공유 잠금 파일 충돌 방지).

## 2. 통신 규칙(엄격)

| 하는 일 | 방법 |
|---|---|
| 다른 서비스 호출 | `winmate_common.client.ServiceClient("<서비스>")` — 게이트웨이(5000) 경유, `consumes` 검사, 계약 검증 |
| 외부 모델(LLM · I2T · T2I · 웹 검색 · 수집 · 임베딩) | `winmate_common.ai.ai()` — ai-tools 서비스만 외부 API 를 부른다 |
| 오래 걸리는 일 | `winmate_common.jobs.jobs().enqueue(...)` → 같은 서비스 `worker.py` → LangGraph(`winmate_common.graph.run_graph`) |
| 진행 상황 | 워커가 `ctx.progress()/step()/partial()` → 화면은 jobs SSE(`/api/jobs/v1/jobs/{id}/events`) |
| 사람 확인 | LangGraph `interrupt({...})` → 잡이 `awaiting_input` → `/api/jobs/v1/jobs/{id}/input` 으로 답 |
| 파일 | 업로드·저장·파싱은 files 서비스(`winmate_common.platform.save_file` · `parsed_document`) |
| 작업물 색인 | 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` |
| 데이터 | 서비스마다 `DocStore.for_service("<서비스>")` → `data/<서비스>/` (다른 서비스 DB 직접 접근 금지) |

- 포트는 5000번대만(`config/services.yaml`). Redis 5379.
- API 규약(경로 `/v1`, 오류 형식, 목록, 202 잡, 버전)은 `docs/ARCHITECTURE.md` §3.
- 서비스 간 호출 전용 API 는 FastAPI `tags=["internal"]` 을 붙인다(게이트웨이가 브라우저 호출을 막는다).
- 기밀 데이터가 들어간 모델 호출에는 `confidential=True`. 개발용 Gemini 는 기밀 전송이 막혀 있다(`*_ALLOW_CONFIDENTIAL=false`).
- 사실(스펙·수치·모델명·고객명·문구)을 지어내지 않는다. KB·파일·검색 근거가 없는 값은 `[확인 필요]` 또는 `[00]` 으로 남긴다.

## 3. 명령

```bash
make setup                         # 처음 한 번(uv · npm · 계약 · 웹 빌드)
make up / make down / make status  # pm2 전체 스택(redis + 서비스 + 워커)
make dev SERVICE=<x>               # x 만 리로드 모드(나머지는 pm2)
make dev-worker SERVICE=<x>        # x 워커만 포그라운드
make dev-bg SERVICE=<x>            # x API(리로드) + 워커를 백그라운드로 · 끄기 make dev-stop SERVICE=<x>
make test SERVICE=<x>              # x 테스트(외부 네트워크 없이, MODEL_MODE=mock)
make typecheck SERVICE=<x>         # 웹 타입 검사(x 기능 폴더 오류만 실패로)
make e2e-feature SERVICE=<x>       # x 기능 e2e(web/e2e/<x>) — Vite 개발 서버(서비스 포트+100) · /api 는 게이트웨이
make contracts SERVICE=<x>         # 계약 갱신 + 깨지는 변경 경고 + 웹 API 타입 생성
make contracts-check               # 코드 ↔ 계약 일치 검사
make web-dev                       # Vite(5001) — /api 는 게이트웨이(5000)로
make health                        # 전체 상태
```

- 테스트 도우미: `winmate_common.testing`(임시 DATA_DIR · fakeredis · in-process 서비스 · 내부 토큰 클라이언트 · `drain_jobs`).
  플랫폼 실제 앱 묶음은 `testing.platform_apps()`(ai-tools mock · kb 실데이터 · files · jobs · workspace · export), 워커 처리기는 `testing.load_service_worker(x)`.
- mock 모델 응답 고정: `mocks/ai-tools/<task>.json` (기능 세션이 자기 task 접두사 파일만 만든다. 예: `rq.extract_form.json`).

## 4. 웹

- 기능 화면은 `web/src/features/<서비스>/` 에만 둔다. `index.tsx` 에서 `export default feature({...})` — 셸이 자동 등록.
- 화면은 `useShellPage({...})` 로 상단바 제목·스텝바·딸깍·추가 핸들러를 셸에 넘긴다(`web/src/shell/types.ts`).
- UI 는 `@/ui` 키트와 `var(--wm-*)` 토큰만 쓴다. 디자인 원본: `docs/screens/` (INDEX.md), 수용 기준: `docs/scenarios/`.
- API 는 `@/api/client` 의 `api.<서비스>`(contracts 에서 생성한 타입) 또는 fetch(`/api/<서비스>/...`). 잡 진행은 `@/api/jobs` 의 `useJob`.

## 5. 완료의 정의

- 코드 + 테스트(`make test SERVICE=x` 통과) + 계약 갱신(`make contracts SERVICE=x`) + 화면(해당 시나리오 수용 기준) + `services/<x>/AGENTS.md` "현재 상태" 갱신.
