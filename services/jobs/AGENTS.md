# jobs 서비스 — 개발 세션 규칙

잡 — Redis 큐 잡 상태 · 진행 이벤트(SSE) · 취소 · 입력 · 예약 실행 · 완료 알림

- 포트: **5040** · 게이트웨이 경로: `/api/jobs/v1/...` · 파이썬 모듈: `winmate_jobs`
- 고칠 수 있는 경로(owns): `services/jobs/**`
- 호출할 수 있는 서비스(consumes): 없음

## 먼저 읽을 것
1. 저장소 루트 `AGENTS.md`(전체 규칙) · `docs/ARCHITECTURE.md`(규약)
2. 이 서비스가 호출하는 서비스의 계약: `contracts/<서비스>.json`(코드는 읽지 않는다)
3. 이 파일 아래 "현재 상태"

## 명령
```bash
make dev SERVICE=jobs          # 이 서비스만 리로드 모드로 실행(나머지는 pm2 스택)
make test SERVICE=jobs         # 이 서비스 테스트
make contracts SERVICE=jobs    # contracts/jobs.json 갱신 + 깨지는 변경 검사
```

## 지킬 것
- 다른 서비스는 `winmate_common.client.ServiceClient("<서비스>")` 로만 부른다(게이트웨이 경유, 계약 검증). 다른 서비스 코드를 import 하지 않는다.
- 외부 모델(LLM·I2T·T2I·웹 검색)은 `winmate_common.ai.ai()` 로만 부른다. task 이름은 `<기능코드 소문자>.<동작>`.
- 오래 걸리는 일은 `jobs().enqueue("jobs", kind, payload)` → `worker.py` 의 처리기(LangGraph 는 `winmate_common.graph.run_graph`).
- 데이터는 `DocStore.for_service("jobs")`(data/jobs/) 에만 둔다.
- 자원을 만들거나 바꾸면 `winmate_common.platform.register_item(...)` 으로 workspace 색인에 올린다.
- API 를 바꾸면 `make contracts SERVICE=jobs` 를 돌리고 `contracts/jobs.json` 변경을 함께 남긴다. 깨지는 변경이면 소비 서비스를 `docs/requests/` 에 알린다.
- 다른 서비스에 기능이 필요하면 `docs/requests/<그 서비스>.md` 에 적는다(직접 고치지 않는다).

## 현재 상태
- 골격만 있음(`GET /v1/info`).
