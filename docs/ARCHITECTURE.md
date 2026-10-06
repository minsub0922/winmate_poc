# Winmate 아키텍처

삼성 B2B 제안서 제작 어시스턴트. 사내망 우분투 PC(RAM 16GB, GPU 2GB) 한 대에서 Docker 없이 pm2 로 돌리는
마이크로서비스 구조다. 개발은 맥에서 Gemini API 로 하고, 사내망에서는 `.env` 값만 바꿔 사내 LLM·I2T·T2I·웹 검색으로 갈아 끼운다.

## 1. 원칙

1. **서비스 = 독립 개발 단위.** 서비스마다 코드, 데이터(SQLite 파일), 계약(OpenAPI), 테스트, 에이전트 규칙(AGENTS.md)을 따로 가진다.
   코드 에이전트 세션 하나가 서비스 하나(+ 그 서비스의 웹 기능 모듈)만 고치고, 나머지는 계약 파일만 읽는다.
2. **게이트웨이 경유 + OpenAPI 계약.** 서비스끼리는 `http://127.0.0.1:5000/api/<service>/...` 로만 호출한다.
   다른 서비스의 포트에 직접 붙거나 코드를 import 하지 않는다. 호출 요청·응답은 `contracts/<service>.json` 으로 검증된다.
3. **외부 모델은 ai-tools 만 호출한다.** LLM · I2T · T2I · 웹 검색 · 웹 수집 · 임베딩은 전부 ai-tools API 를 거친다.
   제공자(gemini · openai_compat · internal · mock)는 `.env` 로 고른다.
4. **오래 걸리는 일은 Redis 큐.** 기능 서비스는 잡을 Redis Stream 에 넣고 같은 코드베이스의 워커가 LangGraph 워크플로로 처리한다.
   진행·결과 이벤트는 jobs 서비스가 SSE 로 내보낸다.
5. **포트는 5000번대만.** Redis 도 5379.
6. **오프라인 우선.** 프런트엔드 자산·폰트·API 문서 UI 를 모두 로컬에 번들한다(CDN 금지). 로컬 모델 가중치는 폴더째 옮긴다.

## 2. 서비스와 포트

단일 원천: [`config/services.yaml`](../config/services.yaml)

| 포트 | 서비스 | 역할 |
|---|---|---|
| 5000 | gateway | `/api/<service>/*` 라우팅, 인증·세션, 요청 ID, 계약 문서 집계(`/api/_docs`), 웹 빌드 서빙 |
| 5001 | web (개발) | Vite 개발 서버. 운영은 게이트웨이가 `web/dist` 서빙 |
| 5010 | ai-tools | LLM · I2T · T2I · 요약형 웹 검색 · 검색 API · 웹 수집 · 임베딩, 호출 한도·데이터 정책·호출 로그·기록/재생 |
| 5020 | kb | winmate-kb 질의: 제품·솔루션 탐색, 상세, 사례, 이미지, 메시지(E1~E3), 요구사항→추천(S1) 등 |
| 5030 | files | 업로드·저장·문서 파싱·미리보기·썸네일 |
| 5040 | jobs | 잡 상태·SSE·취소·입력(사람 확인)·조종 메모·예약 실행·완료 알림 |
| 5050 | workspace | 사용자·프로젝트·작업물 색인(홈 최근 작업, 사이드바 이력)·코멘트·검토/승인·공유 링크 |
| 5060 | export | PPTX·XLSX·DOCX·PDF·ZIP 생성, 시트 템플릿 카탈로그 |
| 5101 | requirements | 고객 요구사항(RQ) |
| 5102 | storyboard | 전략 수립 Storyboard(SB) |
| 5103 | mi | Market Intelligence(MI) |
| 5104 | competitor | 경쟁사 분석(CA) |
| 5105 | vp | Value Proposition(VP) |
| 5106 | spec | Spec 시트(SP) |
| 5107 | image | 이미지 생성(IMG) |
| 5108 | birdseye | 공간 조감도(BE) |
| 5109 | scenario | 공간 시나리오(SC) |
| 5110 | proposal | B2B 제안서(PR) + 기존 제안서 활용(PRU) + 딸깍 |
| 5379 | redis | 잡 큐(Stream)·이벤트·한도 카운터 |

## 3. API 규약 (모든 서비스 공통)

- **경로**: 서비스 내부 경로는 `/v1/...`. 게이트웨이 경로는 `/api/<service>/v1/...`. 상태 확인 `GET /healthz`(게이트웨이 노출 안 함).
- **ID**: `<접두사>_<ULID 26자>`. 접두사는 서비스별 자원 이름(예: `rq_`, `sb_`, `mi_`, `job_`, `file_`).
- **시간**: ISO 8601 UTC 문자열.
- **오류**: HTTP 상태 + `{"error": {"code": "UPPER_SNAKE", "message": "사람이 읽는 한국어", "details": {}}}`.
- **목록**: `?limit=&cursor=` → `{"items": [...], "next_cursor": null | "..."}`.
- **오래 걸리는 작업**: `POST` 가 `202 {"job_id": "job_...", "status": "queued"}` 를 돌려준다.
  화면은 `GET /api/jobs/v1/jobs/{job_id}/events`(SSE)로 진행을 받고, 결과는 해당 자원을 다시 읽는다.
- **버전**: 문서형 자원은 `version` 정수와 `GET /v1/<자원>/{id}/versions`, `POST /v1/<자원>/{id}/versions/{n}/restore` 를 가진다.
- **작업물 색인**: 기능 서비스는 자원을 만들거나 바꿀 때 workspace 에 요약을 올린다
  `PUT /api/workspace/v1/items/{item_id}` `{feature, title, status, summary, route, project_id}` — 홈 최근 작업과 사이드바 이력이 이걸 읽는다.
- **파일**: 사용자 업로드는 모두 files 서비스로 먼저 올리고(`POST /api/files/v1/files`), 기능 서비스는 `file_id` 만 저장한다.
- **기밀**: 고객 자료가 들어간 모델 호출에는 `confidential: true` 를 붙인다. ai-tools 가 `.env` 의 `*_ALLOW_CONFIDENTIAL=false` 면
  403 `POLICY_CONFIDENTIAL` 로 막는다(개발용 Gemini 는 전부 false, 사내 API 는 사내 정책대로). 기능 서비스는 이 오류를 받으면 잡을 한국어
  메시지로 끝내거나 시나리오에 적힌 로컬 대체 경로로 내려간다(다른 모델로 몰래 바꾸지 않는다). `MODEL_MODE=mock` 은 밖으로 나가는 것이 없어
  막지 않는다 — 차단 경로를 mock 으로 시험하려면 `MOCK_ENFORCE_CONFIDENTIAL=true`.
- **헤더**: 게이트웨이가 `X-Request-ID`, `X-User-Id`, `X-User-Name` 을 붙여 넘긴다. 서비스 간 호출은 공통 클라이언트가 `X-Internal-Token` 과 위 헤더를 전달한다.

## 4. 잡(Redis)과 워크플로(LangGraph)

```
화면 ─POST→ gateway ─→ 기능 서비스 API ─XADD→ redis  wm:q:<service>
                                                 │
                         기능 서비스 워커 ←XREADGROUP┘  (LangGraph 그래프 실행, SQLite 체크포인터)
                                │  진행 이벤트 XADD wm:ev:<job_id>
화면 ←SSE─ gateway ←─ jobs 서비스 ←XREAD──┘
```

- 잡 레코드: Redis 해시 `wm:job:<id>` — `service, kind, status(queued|running|awaiting_input|succeeded|failed|canceled), progress, message, ref(자원 id), owner, created_at, …`
- 이벤트: `{type: progress|step|log|awaiting_input|result|error|done, data, ts}` — Stream `wm:ev:<job_id>` (재접속 시 Last-Event-ID 로 이어 받기)
- 취소: jobs API → `wm:job:<id>:cancel` 플래그 → 워커가 노드 경계에서 확인
- 사람 확인(interrupt): 워커가 `awaiting_input` 이벤트를 내고 멈춘다 → jobs API 로 답을 넣으면 같은 `thread_id(=job_id)` 로 이어서 실행
- 조종 메모(딸깍): `wm:job:<id>:memos` 리스트 → 다음 노드에서 반영
- 예약 실행(30일 재확인 등): jobs 서비스의 정렬 집합 `wm:sched`

## 5. 저장

- 서비스마다 `${DATA_DIR}/<service>/` 아래 자기 SQLite 파일(+ LangGraph 체크포인트 파일). 다른 서비스 DB 를 직접 읽지 않는다.
- 파일 바이너리는 files 서비스만 `${DATA_DIR}/files/blobs/` 에 둔다.
- 지식 DB 는 `winmate-kb/kb/winmate_kb.sqlite`(읽기 전용) — kb 서비스만 연다.

## 6. 웹

- React + TypeScript + Vite, React Router, TanStack Query. 화면 디자인은 `docs/screens/` 의 아티팩트 보드를 그대로 따른다.
- 기능 모듈은 `web/src/features/<feature>/` 에 두고 `index.ts` 의 라우트·사이드바 정의를 셸이 자동으로 모은다(공유 파일 수정 불필요).
- API 타입은 `contracts/*.json` 에서 생성(`openapi-typescript`)하고 `openapi-fetch` 로 `/api/<service>` 를 호출한다.

## 7. 개발 세션 나누기

- 세션 시작: `services/<service>/AGENTS.md` 를 읽는다. 고칠 수 있는 경로는 `config/services.yaml` 의 `owns` 뿐이다.
- 다른 서비스가 필요하면 `contracts/<그 서비스>.json` 만 보고 공통 클라이언트로 호출한다. 계약에 없는 기능이 필요하면
  `docs/requests/<그 서비스>.md` 에 요청을 적고, 그 서비스 세션이 구현·계약 갱신을 한다.
- 계약 변경: 서비스 코드 수정 → `make contracts` 로 `contracts/<service>.json` 재생성 → `make contracts-check` 가 깨지는 변경(필드 삭제·타입 변경)을 알려 준다.
- 화면 수용 기준: `docs/scenarios/<feature>.md`.
